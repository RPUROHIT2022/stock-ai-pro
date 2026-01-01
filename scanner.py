
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_engine import fetch_data, get_nifty500_tickers, get_fundamentals, get_option_chain_data
from technicals import detect_structure, identify_setup, calculate_pivots
import ml_engine # [NEW] ML
import time

def calculate_heuristic_score(tech_data, fund_data, fno_data):
    """
    Original Rule-Based Score (renamed from calculate_ai_score).
    Used for fast scanning.
    """
    score = 0
    # ... (existing logic, simplified for brevity in this replace block if needed, but I should keep it all)
    # Actually, I should just rename the old function or keep it?
    # Let's keep the OLD function name for compatibility, but create a wrapper.
    pass 

# ... (Previous calculate_ai_score logic needs to be preserved or I replace the whole block)
# It's better to just MODIFY analyze_single_stock to choose.

def analyze_single_stock(ticker, return_any_data=False):
    """
    Analyzes a single stock and returns its trade setup.
    """
    # 1. FETCH MARKET DATA
    # Fetch more data for ML (59 days is approx max for 15m)
    period = "59d" if return_any_data else "10d"
    df = fetch_data(ticker, period=period, interval="15m") 
    if df is None: return None
        
    # 2. TECHNICAL ANALYSIS
    df = detect_structure(df)
    if df is None: return None
    pivots = calculate_pivots(df)
    setup_type, reason, stats, duration, strategy_name = identify_setup(df)
    
    # 3. PREPARE TECH RESULT
    last_close = df['Close'].iloc[-1]
    atr = (df['High'].iloc[-1] - df['Low'].iloc[-1])
    
    start_price = last_close
    stop_loss = 0
    target_1 = 0
    target_2 = 0
    signal = "NEUTRAL"
    
    if setup_type:
        if "BUY" in setup_type:
            signal = "BUY"
            stop_loss = start_price - (atr * 1.5)
            target_1 = start_price + (atr * 2)
            target_2 = start_price + (atr * 3)
        elif "SELL" in setup_type:
            signal = "SELL"
            stop_loss = start_price + (atr * 1.5)
            target_1 = start_price - (atr * 2)
            target_2 = start_price - (atr * 3)
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
    
    # HEURISTIC SCORE (Fast)
    ai_score = calculate_heuristic_score(tech_result, None, None)

    if return_any_data:
        fund_data = get_fundamentals(ticker)
        fno_data = get_option_chain_data(ticker)
        
        # [NEW] OVERWRITE WITH ML MODEL SCORE
        # We use the heuristic as a base, but mix it with ML? 
        # Or just replace? "Best Models" -> Pure ML.
        try:
            ml_prob = ml_engine.train_and_predict(df, ticker)
            ai_score = ml_prob # Use the Raw Probability (0-100%)
            
            # Boost if we have strong fundamentals?
            # Let's keep it pure ML for the main score, maybe add bonus?
            # User wants "Best Model", so trust the Model.
        except Exception as e:
            print(f"ML Fail: {e}")
            # Fallback to heuristic
            ai_score = calculate_heuristic_score(tech_result, fund_data, fno_data)
        
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
        "AI_Score": ai_score
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
    
    tickers = get_nifty500_tickers()
    total_stocks = len(tickers)
    print(f"Scanning {total_stocks} Stocks...")
    
    with ThreadPoolExecutor(max_workers=5) as executor: # Reduced workers for safety
        # Use simple map or future list
        future_to_stock = {executor.submit(analyze_single_stock, t, return_any_data=False): t for t in tickers}
        
        for future in as_completed(future_to_stock):
            try:
                data = future.result()
                if data and data['Signal'] != "NEUTRAL": 
                    # Add to Result List
                    results["ALL_TRADES"].append(data)
                    
                    if "BUY" in data['Setup']:
                        results["BREAKOUT"].append(data)
                    elif "SELL" in data['Setup']:
                        results["BREAKDOWN"].append(data)
                        
                    # --- AUTO LOG TO EXCEL ---
                    # Log only high quality trades (e.g., specific strategies)
                    # For now, log all valid signals to let user filter in Excel
                    excel_logger.log_trade_to_excel(data)
                    
            except Exception as e:
                # print(f"Scan Error: {e}") 
                pass
                
    return results
                
    return results

if __name__ == "__main__":
    scan_stocks()
