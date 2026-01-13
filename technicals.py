
import pandas as pd
import numpy as np

def calculate_ema(df, period=20):
    return df['Close'].ewm(span=period, adjust=False).mean()

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(0)

def calculate_macd(df, fast=12, slow=26, signal=9):
    exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line

def calculate_bollinger_bands(df, window=20):
    sma = df['Close'].rolling(window).mean()
    std = df['Close'].rolling(window).std()
    upper = sma + (2 * std)
    lower = sma - (2 * std)
    return upper, lower

def calculate_vwap(df):
    v = df['Volume']
    p = df['Close']
    return (p * v).rolling(window=50).sum() / v.rolling(window=50).sum()

def calculate_adx(df, period=14):
    df = df.copy()
    df['H-L'] = df['High'] - df['Low']
    df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
    df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    df['UpMove'] = df['High'] - df['High'].shift(1)
    df['DownMove'] = df['Low'].shift(1) - df['Low']
    df['+DM'] = np.where((df['UpMove'] > df['DownMove']) & (df['UpMove'] > 0), df['UpMove'], 0)
    df['-DM'] = np.where((df['DownMove'] > df['UpMove']) & (df['DownMove'] > 0), df['DownMove'], 0)
    df['+DI'] = 100 * (df['+DM'].ewm(span=period).mean() / df['TR'].ewm(span=period).mean())
    df['-DI'] = 100 * (df['-DM'].ewm(span=period).mean() / df['TR'].ewm(span=period).mean())
    df['DX'] = 100 * abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI'])
    df['ADX'] = df['DX'].ewm(span=period).mean()
    return df['ADX'].fillna(0)

def calculate_stoch_rsi(df, period=14, smoothK=3, smoothD=3):
    # Relies on RSI already being calculated
    rsi = df['RSI']
    stoch_rsi = (rsi - rsi.rolling(period).min()) / (rsi.rolling(period).max() - rsi.rolling(period).min())
    stoch_rsi = stoch_rsi.fillna(0)
    
    # Stochastic K & D
    k = stoch_rsi.rolling(smoothK).mean() * 100
    d = k.rolling(smoothD).mean()
    return k, d

def calculate_atr(df, period=14):
    """
    Calculates Average True Range (ATR) for volatility-based targets.
    """
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # TR1: High - Low
    tr1 = high - low
    # TR2: |High - PrevClose|
    tr2 = abs(high - close.shift(1))
    # TR3: |Low - PrevClose|
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(span=period, adjust=False).mean()
    return atr.fillna(0)

def calculate_supertrend(df, period=10, multiplier=3.0):
    # Returns the SuperTrend Line and a 'Direction' column (1=Up, -1=Down)
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    # Calculate ATR
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    frames = [tr1, tr2, tr3]
    tr = pd.concat(frames, axis=1, join='outer').max(axis=1)
    atr = tr.ewm(alpha=1/period).mean()
    
    # Basic UPPER/LOWER bands
    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    
    # Final Bands
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    trend = np.zeros(len(df))
    
    # Logic loop (iterative b/c SuperTrend depends on previous value)
    # Using numpy arrays for speed
    bu = basic_upper.values
    bl = basic_lower.values
    fu = final_upper.values
    fl = final_lower.values
    c = close.values
    
    for i in range(1, len(df)):
        # Final Upper
        if bu[i] < fu[i-1] or c[i-1] > fu[i-1]:
            fu[i] = bu[i]
        else:
            fu[i] = fu[i-1]
            
        # Final Lower
        if bl[i] > fl[i-1] or c[i-1] < fl[i-1]:
            fl[i] = bl[i]
        else:
            fl[i] = fl[i-1]
            
        # Trend
        if c[i] > fu[i-1]:
            trend[i] = 1 # Uptrend
        elif c[i] < fl[i-1]:
            trend[i] = -1 # Downtrend
        else:
            trend[i] = trend[i-1]
            
            # Logic adjustment: if trend matches prev, keep lines consistent
            if trend[i] == 1 and fl[i] < fl[i-1]: fl[i] = fl[i-1]
            if trend[i] == -1 and fu[i] > fu[i-1]: fu[i] = fu[i-1]
            
    return pd.Series(trend, index=df.index)

def detect_structure(df):
    if len(df) < 50: return None
    df['EMA_20'] = calculate_ema(df, 20)
    df['EMA_50'] = calculate_ema(df, 50)
    df['EMA_200'] = calculate_ema(df, 200) 
    df['RSI'] = calculate_rsi(df, 14)
    df['Vol_MA'] = df['Volume'].rolling(20).mean()
    df['MACD'], df['Signal_Line'] = calculate_macd(df)
    df['BB_Upper'], df['BB_Lower'] = calculate_bollinger_bands(df)
    df['VWAP'] = calculate_vwap(df)
    df['ADX'] = calculate_adx(df)
    
    # NEW PRO INDICATORS
    df['StochRSI_K'], df['StochRSI_D'] = calculate_stoch_rsi(df)
    df['SuperTrend'] = calculate_supertrend(df, 10, 3) # Standard setting
    
    # BB Squeeze (Band Width)
    df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['EMA_20']
    
    # ATR (Avg True Range) - For Targets
    df['ATR'] = calculate_atr(df, 14)
    
    return df

def calculate_pivots(df):
    recent_high = df['High'].iloc[-20:].max()
    recent_low = df['Low'].iloc[-20:].min()
    close = df['Close'].iloc[-1]
    pivot = (recent_high + recent_low + close) / 3
    r1 = (2 * pivot) - recent_low
    s1 = (2 * pivot) - recent_high
    return {"Recent High": round(recent_high, 2), "Recent Low": round(recent_low, 2), "Pivot": round(pivot, 2), "R1": round(r1, 2), "S1": round(s1, 2)}

def identify_setup(df):
    if df is None or len(df) < 200: return None, None, None, None, None 

    close = df['Close'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    stoch_k = df['StochRSI_K'].iloc[-1]
    stoch_d = df['StochRSI_D'].iloc[-1]
    
    macd = df['MACD'].iloc[-1]
    sig = df['Signal_Line'].iloc[-1]
    
    vwap = df['VWAP'].iloc[-1]
    ema_20 = df['EMA_20'].iloc[-1]
    ema_200 = df['EMA_200'].iloc[-1]
    adx = df['ADX'].iloc[-1]
    
    bb_lower = df['BB_Lower'].iloc[-1]
    bb_upper = df['BB_Upper'].iloc[-1]
    bb_width = df['BB_Width'].iloc[-1]
    
    supertrend = df['SuperTrend'].iloc[-1]
    
    stats = {
        "RSI": round(rsi, 2),
        "StochRSI": f"{round(stoch_k,0)}/{round(stoch_d,0)}",
        "Trend": "Bullish" if supertrend == 1 else "Bearish",
        "EMA_20": round(ema_20, 2),
        "EMA_200": round(ema_200, 2),
        "VWAP": round(vwap, 2) if not pd.isna(vwap) else 0,
        "ADX": round(adx, 2),
        "Squeeze": "Yes" if bb_width < 0.05 else "No", # Tighter bands = Squeeze
        "Volume Status": "High" if df['Volume'].iloc[-1] > 1.5 * df['Vol_MA'].iloc[-1] else "Normal",
        "Last Signal": "Buy" if supertrend == 1 else "Sell"
    }

    setup_type = None
    reason = "Neutral"
    strategy_name = "Wait & Watch"
    duration = "N/A"

    # --- PRO STRATEGIES ---
    
    # 1. BB SQUEEZE BREAKOUT (Explosive)
    # Low Volatility (Squeeze) + Volume Spike + Breakout
    if bb_width < 0.08 and stats['Volume Status'] == "High":
        if close > bb_upper and supertrend == 1:
             setup_type = "SQUEEZE_BUY"
             strategy_name = "Volatility Squeeze Breakout"
             reason = f"Expansion from Squeeze + Vol Spike"
             duration = "1 - 4 Hours"
        elif close < bb_lower and supertrend == -1:
             setup_type = "SQUEEZE_SELL"
             strategy_name = "Volatility Squeeze Breakdown"
             reason = f"Expansion from Squeeze + Vol Spike"
             duration = "1 - 4 Hours"

    # 2. SUPERTREND PULLBACK (Trend Continuation)
    # Price is in trend (Supertrend Green), Pulls back to EMA20/VWAP, then StochRSI crosses up
    if setup_type is None:
        if supertrend == 1 and close > ema_200:
            if stoch_k < 20 and stoch_k > stoch_d: # Oversold crossover in Uptrend
                setup_type = "PULLBACK_BUY"
                strategy_name = "SuperTrend Pullback (Long)"
                reason = "Trend Pullback + StochRSI Cross"
                duration = "1 - 2 Hours"
        
        elif supertrend == -1 and close < ema_200:
            if stoch_k > 80 and stoch_k < stoch_d: # Overbought crossover in Downtrend
                setup_type = "PULLBACK_SELL"
                strategy_name = "SuperTrend Pullback (Short)"
                reason = "Trend Pullback + StochRSI Cross"
                duration = "1 - 2 Hours"

    # 3. CLASSIC TREND (ADX + EMA)
    if setup_type is None:
        if adx > 25:
            if supertrend == 1 and close > ema_20 and macd > sig:
                setup_type = "TREND_BUY"
                strategy_name = "Momentum Trend (Long)"
                reason = "Strong ADX + SuperTrend + MACD"
                duration = "Day Trade"
            elif supertrend == -1 and close < ema_20 and macd < sig:
                setup_type = "TREND_SELL"
                strategy_name = "Momentum Trend (Short)"
                reason = "Strong ADX + SuperTrend + MACD"
                duration = "Day Trade"
    
    # 4. MEAN REVERSION (Extreme Scalps)
    if setup_type is None:
        if rsi < 30 and close < bb_lower and stoch_k < 20: 
             # Only catch knife if SuperTrend is becoming unstable? No, risky. 
             # Just pure technical bounce.
             setup_type = "SCALP_BUY"
             strategy_name = "Oversold Reversion"
             reason = "RSI < 30 + Stoch < 20 + BB Lower"
             duration = "15 - 30 Mins"
        elif rsi > 70 and close > bb_upper and stoch_k > 80:
             setup_type = "SCALP_SELL"
             strategy_name = "Overbought Reversion"
             reason = "RSI > 70 + Stoch > 80 + BB Upper"
             duration = "15 - 30 Mins"

    # Fallback / General Bias
    if setup_type is None:
         if supertrend == 1: reason = "Bullish (SuperTrend)"
         else: reason = "Bearish (SuperTrend)"

    return setup_type, reason, stats, duration, strategy_name
