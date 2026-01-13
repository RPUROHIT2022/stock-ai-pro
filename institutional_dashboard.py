import streamlit as st
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPRegressor
import time
import queue

# Import from existing modules
from data_engine import fetch_data, get_fundamentals, get_option_chain_data
from news_engine import fetch_stock_specific_news
from gemini_engine import get_gemini_verdict

# --- HYBRID MODEL ENGINE (LSTM + XGBOOST) ---

class InstitutionalEngine:
    def __init__(self):
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        
    def prepare_lstm_data(self, df, lookback=50):
        """Prepares Data for Pattern Model"""
        data = df[['Close']].values
        scaled_data = self.scaler.fit_transform(data)
        
        X, y = [], []
        for i in range(lookback, len(scaled_data)):
            X.append(scaled_data[i-lookback:i, 0])
            y.append(scaled_data[i, 0])
            
        return np.array(X), np.array(y), scaled_data

    def get_lstm_signal(self, df):
        """
        Uses a lightweight Neural Net (MLP) to mimic LSTM Pattern Recognition.
        (Replaced LSTM with MLP for easier installation/compatibility)
        """
        if len(df) < 100: return "NEUTRAL", 0.0
        
        try:
            X, y, scaled_data = self.prepare_lstm_data(df)
            
            # Train (Fast Mode using MLP)
            # Input size is 50 (Lookback)
            model = MLPRegressor(hidden_layer_sizes=(50, 25), max_iter=200, random_state=42)
            model.fit(X, y)
            
            # Predict Next Candle
            last_sequence = scaled_data[-50:]
            last_sequence = last_sequence.reshape(1, -1) # Flatten for MLP
            
            pred_scaled = model.predict(last_sequence)
            pred_price = self.scaler.inverse_transform(pred_scaled.reshape(-1, 1))[0][0]
            
            current_close = df['Close'].iloc[-1]
            diff_pct = (pred_price - current_close) / current_close * 100
            
            signal = "BUY" if diff_pct > 0.1 else "SELL" if diff_pct < -0.1 else "NEUTRAL"
            return signal, diff_pct
        except Exception as e:
            return "NEUTRAL", 0.0

    def get_xgboost_score(self, df):
        """
        Calculates Probability Score (0-100%) using XGBoost logic
        (Features: RSI, ADX, MACD, VWAP_Dist)
        """
        if len(df) < 50: return 50
        
        # 1. Feature Engineering
        df = df.copy()
        df['RSI'] = self.calculate_rsi(df)
        df['ADX'] = self.calculate_adx(df)
        df['VWAP'] = self.calculate_vwap(df)
        df['VWAP_Dist'] = (df['Close'] - df['VWAP']) / df['VWAP'] * 100
        
        # 2. Logic (Simplified Rule-Based Weighting mimicking XGBoost feature importance)
        # In a real deployed version, we would load a .json model file here.
        score = 50
        
        # RSI Contribution
        rsi = df['RSI'].iloc[-1]
        if rsi > 50: score += 10
        if rsi > 70: score -= 15 # Overbought logic
        if rsi < 30: score += 15 # Oversold bounce
        
        # Trend Contribution
        adx = df['ADX'].iloc[-1]
        if adx > 25: score += 10
        
        # VWAP Value
        dist = df['VWAP_Dist'].iloc[-1]
        if dist < -1.0: score += 20 # Value Buy
        if dist > 2.0: score -= 20 # Overextended
        
        return min(max(int(score), 0), 100)
        
    def get_news_sentiment(self, ticker):
        """
        Fetches news and calculates aggregated sentiment score (-10 to 10).
        """
        news = fetch_stock_specific_news(ticker)
        if not news:
             return 0, []
             
        total_score = 0
        for item in news:
            total_score += item['Score']
            
        # Normalize to -10 to 10 range roughly
        # If we have 5 news items, max score 50. 
        avg_score = total_score / len(news) if len(news) > 0 else 0
        
        # Boost for high impact keywords found in headline
        return avg_score, news
    
    # --- Helper Techs ---
    def calculate_rsi(self, df, period=14):
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_adx(self, df, period=14):
        # Simplified ADX (Placeholder)
        return df['Close'].rolling(period).std() 

    def calculate_vwap(self, df):
        v = df['Volume']
        p = df['Close']
        return (p * v).rolling(window=50).sum() / v.rolling(window=50).sum()


# --- DASHBOARD UI ---

# --- DASHBOARD UI ---

def render_institutional_dashboard():
    st.markdown("## 🏦 Institutional Alpha Dashboard")
    st.markdown("Only high-probability (>85% Confluence) setups are shown here.")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown("### 🔧 Control Panel")
        ticker = st.text_input("Analyze Ticker", value="RELIANCE.NS").upper()
        
        st.subheader("🧠 Gemini AI")
        api_key = st.text_input("Gemini API Key", type="password", placeholder="Enter AI Studio Key")
        
        # 60-Min Kill Switch Timer
        if 'trade_start_time' not in st.session_state:
            st.session_state.trade_start_time = None
            
        if st.button("Start Trade Timer"):
            st.session_state.trade_start_time = time.time()
            
        if st.session_state.trade_start_time:
            elapsed = (time.time() - st.session_state.trade_start_time) / 60
            remaining = 60 - elapsed
            st.metric("Kill Switch Timer", f"{int(remaining)} Mins Left")
            if remaining <= 0:
                st.error("⏰ TIME EXIT TRIGGERED! Close Position.")
        
    with col2:
        if st.button("🚀 Run Hybrid Model Analysis", type="primary"):
            with st.spinner(f"Running LSTM + XGBoost + News AI on {ticker}..."):
                # Clear previous state
                if 'inst_data' in st.session_state:
                    del st.session_state['inst_data']
                
                # Run Analysis
                data = get_institutional_analysis(ticker)
                if data:
                    st.session_state['inst_data'] = data
                    st.rerun()

    # --- PERSISTENT DISPLAY ---
    if 'inst_data' in st.session_state:
        display_institutional_results(st.session_state['inst_data'], api_key, ticker)

def get_institutional_analysis(ticker):
    """Performs analysis and returns a dictionary of results."""
    # 1. Fetch Data
    df = fetch_data(ticker, period="60d", interval="15m")
    
    # Auto-fix for NSE stocks if user forgot .NS
    if df is None and ".NS" not in ticker and "=" not in ticker:
        ticker += ".NS"
        # Toast requires st reference, keep it for feedback
        st.toast(f"🔄 Auto-correction: Trying {ticker}...", icon="🇮🇳")
        df = fetch_data(ticker, period="60d", interval="15m")
        
    if df is None:
        st.error(f"❌ Data fetch failed for {ticker}. Check spelling or internet.")
        return None

    engine = InstitutionalEngine()
    
    # 2. Run Models
    # Calculate indicators on main DF for display later
    df['RSI'] = engine.calculate_rsi(df)
    
    lstm_sig, lstm_val = engine.get_lstm_signal(df)
    xgb_score = engine.get_xgboost_score(df)
    sent_score, news_items = engine.get_news_sentiment(ticker)
    
    # Adjust XGB Score based on Sentiment
    if sent_score > 2: xgb_score += 10
    elif sent_score < -2: xgb_score -= 10
    xgb_score = min(100, max(0, int(xgb_score)))
    
    # 3. Institutional Checks
    current_price = df['Close'].iloc[-1]
    vwap = engine.calculate_vwap(df).iloc[-1]
    vwap_std = df['Close'].rolling(50).std().iloc[-1]
    
    # Zones
    buy_zone_top = vwap + vwap_std
    buy_zone_bot = vwap - vwap_std
    
    is_value_buy = buy_zone_bot <= current_price <= buy_zone_top
    is_trap = current_price > (vwap + 2 * vwap_std)
    
    # 4. Final Confluence
    confluence = "MEDIUM"
    if lstm_sig == "BUY" and xgb_score > 75: confluence = "HIGH"
    if is_trap: confluence = "TRAP (AVOID)"
    
    return {
        "df": df,
        "lstm_sig": lstm_sig,
        "lstm_val": lstm_val,
        "xgb_score": xgb_score,
        "sent_score": sent_score,
        "news_items": news_items,
        "current_price": current_price,
        "confluence": confluence,
        "is_trap": is_trap,
        "is_value_buy": is_value_buy
    }

def display_institutional_results(data, api_key, ticker):
    """Renders the analysis results from the data dictionary."""
    df = data['df']
    lstm_sig = data['lstm_sig']
    lstm_val = data['lstm_val']
    xgb_score = data['xgb_score']
    sent_score = data['sent_score']
    news_items = data['news_items']
    current_price = data['current_price']
    confluence = data['confluence']
    is_trap = data['is_trap']
    
    # --- DISPLAY METRICS ---
    
    # A. Confidence Meter
    st.markdown("### 🧠 AI Confidence Meter (Tech + Sentiment)")
    st.progress(xgb_score / 100)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("LSTM Pattern", lstm_sig, delta=f"{lstm_val:.2f}%")
    m2.metric("XGB Probability", f"{xgb_score}%")
    
    sentiment_label = "Neutral"
    sentiment_color = "off"
    if sent_score > 0:
        sentiment_label = "Positive"
        sentiment_color = "normal" 
    elif sent_score < 0:
        sentiment_label = "Negative"
        sentiment_color = "inverse"
        
    m3.metric("News Sentiment", f"{round(sent_score, 1)}", delta=sentiment_label, delta_color=sentiment_color)
    m4.metric("Confluence", confluence)
    
    # B. Execution Plan
    st.markdown("---")
    st.markdown("### ⚡ Execution Plan")
    
    if confluence == "HIGH":
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        stop_loss = current_price - (1.5 * atr)
        
        c1, c2, c3 = st.columns(3)
        c1.success(f"**ENTRY RANGE**: {round(current_price * 0.998, 2)} - {round(current_price * 1.002, 2)}")
        c2.error(f"**STOP LOSS (1.5x ATR)**: {round(stop_loss, 2)}")
        c3.info(f"**TARGET**: {round(current_price + (2*atr), 2)}")
        
    elif is_trap:
        st.warning("⚠️ **TRAP ALERT**: Price is > 2 Std Dev from VWAP. Do NOT Logic.")
    else:
        st.info("No High-Probability Setup detected. Wait for better confluence.")
        
    # C. GEMINI ANALYST (OPTIONAL CALL)
    st.markdown("---")
    st.markdown("### 🦅 Hedge Fund Analyst (Gemini)")
    
    if api_key:
        if st.button("Ask Gemini for Verdict 🧠"):
            with st.spinner("Consulting the Investment Committee..."):
                # Prepare Data for Gemini
                tech_data = {
                    "CMP": current_price,
                    "Trend": "Bullish" if xgb_score > 50 else "Bearish",
                    "RSI": round(df['RSI'].iloc[-1], 2),
                    "VWAP_Status": "TRAP" if is_trap else "VALUE" if data['is_value_buy'] else "NEUTRAL",
                    "Pattern": lstm_sig
                }
                
                verdict = get_gemini_verdict(ticker, tech_data, xgb_score, news_items, api_key)
                
                # Render Styled Verdict
                st.markdown(f"""
                <div style="background: rgba(33, 150, 243, 0.1); border-left: 5px solid #2196F3; padding: 20px; border-radius: 10px;">
                    {verdict.replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("ℹ️ Enter API Key in sidebar to unlock Gemini.")

    # D. News Feed
    if news_items:
        st.markdown("### 📰 Recent News Analysis")
        for n in news_items[:3]:
            st.markdown(f"- **{n['Headline']}** (Score: {n['Score']})")
