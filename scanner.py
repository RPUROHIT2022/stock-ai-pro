
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_engine import fetch_data, get_nifty500_tickers, get_fundamentals, get_option_chain_data
from technicals import detect_structure, identify_setup, calculate_pivots
import ml_engine # [NEW] ML
import time


def calculate_heuristic_score(tech_data, fund_data, fno_data):
    """
    Calculates a 0-100 Score based on Technicals, Fundamentals, and F&O.
    """
    score = 50 # Base Score
    
    try:
        # 1. TECHNICALS (Max +50)
        signal = tech_data.get('Signal', 'NEUTRAL')
        stats = tech_data.get('Stats', {})
        
        if signal != "NEUTRAL":
            score += 20 # [UPDATED] Stronger Base Signal
            
        # Trend Strength
        if stats.get('Trend') == "Bullish" and signal == "BUY": score += 10
        elif stats.get('Trend') == "Bearish" and signal == "SELL": score += 10
        
        # ADX (Strong Trend)
        if stats.get('ADX', 0) > 25: score += 5
        if stats.get('ADX', 0) > 40: score += 5
        
        # Volume
        if stats.get('Volume Status') == "High": score += 5
        
        # Squeeze (Explosive Potential)
        if stats.get('Squeeze') == "Yes": score += 5

        # 2. FUNDAMENTALS (Max +10) - Bonus for quality
        if fund_data:
            if fund_data.get('Recommendation') in ['BUY', 'STRONG_BUY']: score += 5
            if fund_data.get('Profit Margins %', 0) > 10: score += 5
            
        # 3. F&O SENTIMENT (Max +10)
        if fno_data:
            pcr = fno_data.get('PCR', 1)
            if signal == "BUY" and pcr > 0.7: score += 5 # Healthy PCR for buying
            if signal == "SELL" and pcr < 1.0: score += 5 
            
    except Exception as e:
        print(f"Scoring Error: {e}")
        
    return min(max(score, 0), 100) # Clamp 0-100

def analyze_single_stock(ticker, return_any_data=False):
    """
    Analyzes a single stock and returns its trade setup.
    """
    # 1. FETCH MARKET DATA
    # User requested 15m data. Max is ~60d. 
    # We use 59d to be safe and maximize history for the model.
    period = "59d" 
    df = fetch_data(ticker, period=period, interval="15m") 
    if df is None: return None
        
    # 2. TECHNICAL ANALYSIS
    df = detect_structure(df)
    if df is None: return None
    pivots = calculate_pivots(df)
    setup_type, reason, stats, duration, strategy_name = identify_setup(df)
    
    # 3. PREPARE TECH RESULT
    last_close = df['Close'].iloc[-1]
    # [UPDATED] Use ATR for Start/Stop instead of single candle range
    atr = df['ATR'].iloc[-1]
    
    # Fallback if ATR is 0 (rare)
    if atr == 0: atr = last_close * 0.01 
    
    start_price = last_close
    stop_loss = 0
    target_1 = 0
    target_2 = 0
    signal = "NEUTRAL"
    
    if setup_type:
        if "BUY" in setup_type:
            signal = "BUY"
            # Dynamic Risk Reward 1:2 and 1:3
            stop_loss = start_price - (atr * 1.5)
            target_1 = start_price + (atr * 2.5) # Bigger Target
            target_2 = start_price + (atr * 4.0)
        elif "SELL" in setup_type:
            signal = "SELL"
            stop_loss = start_price + (atr * 1.5)
            target_1 = start_price - (atr * 2.5)
            target_2 = start_price - (atr * 4.0)
    else:
         setup_type = "NO_CLEAR_SETUP"
    
    tech_result = {
        "Signal": signal,
        "Stats": stats,
        "Setup": setup_type
    }

    # 4. FETCH EXTRA DATA (Fundamentals & F&O)
    fund_data = None
    fno_data = None
    ai_score = 0
    
    # Get Fundamentals (Cached internally eventually)
    if return_any_data:
        fund_data = get_fundamentals(ticker)
        fno_data = get_option_chain_data(ticker)

    # 5. CALCULATE SCORE
    # Heuristic Base
    heuristic_score = calculate_heuristic_score(tech_result, fund_data, fno_data)
    ai_score = heuristic_score
    
    # ML Boost (If scanning or deep analysis)
    # We always run ML now for better scoring
    try:
        # Use the same 15m dataframe
        ml_prob = ml_engine.train_and_predict(df, ticker)
        
        # [UPDATED] Additive Logic instead of Weighted Average
        # If Technicals say BUY (Score ~70-80) and ML agrees, we boost.
        # If ML is Neutral (50), we don't punish Technicals.
        
        # ML Impact (-15 to +20)
        ml_bonus = 0
        if ml_prob > 60: ml_bonus = 10
        if ml_prob > 75: ml_bonus = 20
        
        if ml_prob < 40: ml_bonus = -10
        if ml_prob < 30: ml_bonus = -20
        
        # Align Direction
        if signal == "BUY":
            ai_score += ml_bonus
        elif signal == "SELL":
             # For SELL, Low ML Prob (Bearish) is good?
             # Wait, ml_engine 'Target' is "Price UP".
             # So Low ML Prob means Price NOT UP (Bearish).
             # So if ML < 40, meaningful for Short.
             if ml_prob < 40: ai_score += 10 # Confirm Short
             if ml_prob < 25: ai_score += 20
             
             if ml_prob > 60: ai_score -= 15 # ML says Up, Tech says Sell -> Conflict
        else:
            # Neutral Signal
            if ml_prob > 70: ai_score += 10
            
        # Refine
        # ai_score = (heuristic_score * 0.4) + (ml_prob * 0.6) # OLD
        
    except Exception as e:
        # print(f"ML Fail: {e}")
        pass
        
    # [FIX] Clamp Score to 0-100
    ai_score = min(max(ai_score, 0), 100)
        
    return {
        "Stock": ticker.replace(".NS", ""),
        "CMP": round(last_close, 2),

        "Signal": signal,
        "Setup": setup_type,
        "Strategy": strategy_name,
        "Duration": duration,
        "Reason": reason,
        "Stats": stats,
        "Levels": pivots,
        # History is usually not needed for basic scan result to save memory
        # "History": df[['Open', 'High', 'Low', 'Close', 'EMA_20', 'EMA_50', 'EMA_200']].tail(100),
        "Entry": round(start_price, 2),
        "Stop Loss": round(stop_loss, 2) if stop_loss else 0,
        "Target 1": round(target_1, 2) if target_1 else 0,
        "Target 2": round(target_2, 2) if target_2 else 0,
        # fallback for UI if neutral
        "KeyLevel_P": pivots['Pivot'],
        "KeyLevel_S1": pivots['S1'],
        "KeyLevel_R1": pivots['R1'],
        "RR Ratio": "1:2" if signal != "NEUTRAL" else "N/A",
        # New Pro Fields
        "Fundamentals": fund_data,
        "FnO": fno_data,
        "AI_Score": int(ai_score)
    }

def scan_stocks():
    """
    Scans the entire Nifty 500 list.
    """
    import excel_logger # Lazy import
    
    results = {
        "SUPPORT_ZONE": [],
        "BREAKOUT": [],
        "BREAKDOWN": [],
        "ALL_TRADES": [] 
    }
    
    import logging
    # System errors
    logging.basicConfig(filename='system_error.log', level=logging.ERROR, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    
    # [DEBUG] Audit Log for Scores
    audit_logger = logging.getLogger('audit')
    audit_logger.setLevel(logging.INFO)
    fh = logging.FileHandler('scan_results.log')
    fh.setFormatter(logging.Formatter('%(message)s'))
    audit_logger.addHandler(fh)

    tickers = get_nifty500_tickers()
    total_stocks = len(tickers)
    print(f"Scanning {total_stocks} Stocks (Turbo Mode)...")
    
    with ThreadPoolExecutor(max_workers=30) as executor: # TURBO MODE
        future_to_stock = {executor.submit(analyze_single_stock, t, return_any_data=False): t for t in tickers}
        
        for future in as_completed(future_to_stock):
            stock_name = future_to_stock[future]
            try:
                data = future.result()
                if data:
                    # [DEBUG] Log the score
                    audit_logger.info(f"{stock_name}: Score={data['AI_Score']} Signal={data['Signal']}")

                    if data['Signal'] != "NEUTRAL" or data['AI_Score'] > 70:
                        # Add to Result List
                        results["ALL_TRADES"].append(data)
                        
                        if "BUY" in data['Setup']:
                            results["BREAKOUT"].append(data)
                        elif "SELL" in data['Setup']:
                            results["BREAKDOWN"].append(data)
                            
                        # --- AUTO LOG TO EXCEL ---
                        if data['Signal'] != "NEUTRAL":
                            excel_logger.log_trade_to_excel(data)
                    
            except Exception as e:
                logging.error(f"Failed to scan {stock_name}: {str(e)}")
                pass
                
    return results

if __name__ == "__main__":
    scan_stocks()

if __name__ == "__main__":
    scan_stocks()
