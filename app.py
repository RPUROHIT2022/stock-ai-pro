
import streamlit as st
import pandas as pd
import time
from data_engine import fetch_global_sentiment, get_market_status
from news_engine import fetch_market_news, fetch_stock_specific_news
from scanner import scan_stocks, analyze_single_stock

# --- CONFIGURATION & ASSETS ---
st.set_page_config(
    page_title="Intraday AI Agent Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --- SECURITY: PASSWORD CHECK ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets.get("PASSWORD", "7@2362"):  # Default is 1234
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Enter Password", type="password", on_change=password_entered, key="password"
        )
        st.info("Default Password: 1234")
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Enter Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()

# --- PREMIUM STYLING (GLASSMORPHISM + NEON) ---
st.markdown("""
    <style>
    /* Global Reset & Dark Theme Base */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a1a2e 0%, #050505 70%);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #000; }
    ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #555; }

    /* Glassmorphism Cards */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .glass-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
        border-color: rgba(255, 255, 255, 0.2);
    }

    /* Metric Containers */
    .metric-container {
        text-align: center;
        padding: 10px;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #fff;
    }
    .metric-delta-pos { color: #00e676; font-size: 0.9rem; }
    .metric-delta-neg { color: #ff1744; font-size: 0.9rem; }

    /* Headers & Titles */
    h1, h2, h3 {
        color: #fff;
        font-weight: 600;
        letter-spacing: -0.5px;
    }
    .neon-text {
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0a0a0a;
        border-right: 1px solid #222;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);
    }
    
    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid #222;
        border-radius: 10px;
        overflow: hidden;
    }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER SECTION ---
c1, c2 = st.columns([1, 6])
with c1:
    st.image("https://cdn-icons-png.flaticon.com/512/3281/3281329.png", width=80) 
with c2:
    st.markdown("<h1 style='margin-top: 0;'>Intraday AI Agent <span style='color: #2196F3; font-size: 0.6em; vertical-align: top;'>PRO</span></h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: #888; margin-top: -15px;'>Real-time AI Market Scanner & Analysis System</p>", unsafe_allow_html=True)

st.divider()

# --- SESSION STATE ---
if 'watchlist' not in st.session_state:
    # UPDATED DEFAULT WATCHLIST with TATASTEEL
    st.session_state.watchlist = ["RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TATASTEEL.NS"] 

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 🎮 Control Center")
    mode = st.radio("Select Mode", 
        ["Live Watchlist Monitor", "Deep Analysis (Single Stock)", "Dashboard & News", "Full Nifty 500 Scan"],
        label_visibility="collapsed"
    )
    
    st.divider()
    
    st.markdown("### 📋 Watchlist Manager")
    
    # 1. Single Add
    with st.expander("Add Single Stock", expanded=True):
        new_stock = st.text_input("Symbol", placeholder="e.g. SBIN").upper()
        if st.button("Add Stock", type="primary", use_container_width=True):
            if new_stock:
                symbol = new_stock if new_stock.endswith(".NS") else f"{new_stock}.NS"
                if symbol not in st.session_state.watchlist:
                    st.session_state.watchlist.append(symbol)
                    st.toast(f"✅ Added {symbol}")
                else: 
                    st.toast("⚠️ Already in watchlist")

    # 2. Bulk Add (New Feature)
    with st.expander("Bulk Import"):
        bulk_input = st.text_area("Paste Symbols (comma separated)", placeholder="TCS, WIPRO, TECHM")
        if st.button("Import Batch", use_container_width=True):
            if bulk_input:
                info_count = 0
                for s in bulk_input.split(','):
                    clean_s = s.strip().upper()
                    if not clean_s: continue
                    sym = clean_s if clean_s.endswith(".NS") else f"{clean_s}.NS"
                    if sym not in st.session_state.watchlist:
                        st.session_state.watchlist.append(sym)
                        info_count += 1
                st.success(f"Added {info_count} stocks!")
                st.rerun()

    # 3. Remove
    to_remove = st.selectbox("Remove Stock", ["Select to Remove..."] + st.session_state.watchlist)
    if to_remove != "Select to Remove...":
        st.session_state.watchlist.remove(to_remove)
        st.rerun()
        
    st.info(f"Tracking **{len(st.session_state.watchlist)}** Stocks")

# --- HELPER: CUSTOM METRIC CARD ---
def render_metric_card(label, value, delta=None, color=None):
    delta_html = ""
    if delta:
        d_color = "#00e676" if "Buy" in str(delta) or "Strong" in str(delta) or (isinstance(delta, (int, float)) and delta > 0) else "#ff1744"
        delta_html = f"<div style='color: {d_color}; font-size: 0.9em; margin-top: 5px;'>{delta}</div>"
    
    st.markdown(f"""
    <div class="glass-card metric-container">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color: {color if color else '#fff'}">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

# --- MODE 1: LIVE WATCHLIST ---
if mode == "Live Watchlist Monitor":
    st.markdown("### 🔴 Live Portfolio Monitor")
    
    col_act, _ = st.columns([2, 8])
    if col_act.button("🔄 Refresh Data", type="primary"): 
        st.rerun()
    
    live_data = []
    
    # helper for threading
    def fetch_live_stock(t):
        return analyze_single_stock(t, return_any_data=False)

    import concurrent.futures
    
    progress_text = "Scanning Watchlist..."
    my_bar = st.progress(0, text=progress_text)
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_stock = {executor.submit(fetch_live_stock, t): t for t in st.session_state.watchlist}
        
        completed = 0
        total = len(st.session_state.watchlist)
        
        for future in concurrent.futures.as_completed(future_to_stock):
            res = future.result()
            completed += 1
            my_bar.progress(completed / total, text=f"Scanning {completed}/{total}...")
            
            if res:
                live_data.append({
                    "Stock": res['Stock'], 
                    "Price": res['CMP'], 
                    "Signal": res['Signal'], 
                    "Reason": res['Reason'],
                    "ADX": res['Stats']['ADX'], 
                    "Action": "WAIT" if res['Signal'] == "NEUTRAL" else res['Signal']
                })
    
    my_bar.empty()

    if live_data:
        df = pd.DataFrame(live_data)
        # Sort by Signal importance
        df.sort_values(by="Action", ascending=False, key=lambda col: col != "WAIT", inplace=True)
        
        def color_action_col(val):
            color = 'gray'
            if 'BUY' in str(val): color = '#00e676' 
            elif 'SELL' in str(val): color = '#ff1744'
            return f'color: {color}; font-weight: bold;'
            
        st.dataframe(
            df.style.map(color_action_col, subset=['Signal', 'Action']),
            use_container_width=True,
            column_config={
                "Price": st.column_config.NumberColumn("CMP (₹)", format="₹ %.2f"),
                "ADX": st.column_config.NumberColumn("Trend (ADX)", format="%.1f")
            },
            height=500
        )
    else:
        st.info("Watchlist is empty or data is loading...")

# --- MODE 2: DEEP ANALYSIS (FUNDAMENTAL + F&O) ---
elif mode == "Deep Analysis (Single Stock)":
    st.markdown("### 🔍 Deep Dive Analysis")
    
    c1, c2 = st.columns([3, 1])
    with c1:
        ticker_input = st.text_input("Enter Symbol", placeholder="RELIANCE, SBIN...").upper()
    with c2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        run_btn = st.button("🚀 Analyze", type="primary", use_container_width=True)
    
    if run_btn and ticker_input:
        ticker = ticker_input if ticker_input.endswith(".NS") else f"{ticker_input}.NS"
        
        with st.spinner(f"Running 360° Analysis on {ticker}..."):
            result = analyze_single_stock(ticker, return_any_data=True)
        
        if result:
            # --- COMPACT DASHBOARD HEADER ---
            score = result.get('AI_Score', 0)
            score_color = "#00e676" if score > 50 else "#ff9100" if score > 30 else "#ff1744"
            
            # Top Stats Row
            st.markdown(f"""
            <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                <div class="glass-card" style="flex: 1; text-align: center; border-left: 5px solid {score_color};">
                    <div class="metric-label">AI Score</div>
                    <div style="font-size: 2.5rem; font-weight: bold; color: {score_color};">{score}%</div>
                    <div style="font-size: 0.8rem; opacity: 0.7;">Winning Probability</div>
                </div>
                <div class="glass-card" style="flex: 1; text-align: center;">
                    <div class="metric-label">Signal</div>
                    <div style="font-size: 1.8rem; font-weight: bold; color: #fff;">{result['Signal']}</div>
                </div>
                <div class="glass-card" style="flex: 1; text-align: center;">
                    <div class="metric-label">Strategy</div>
                    <div style="font-size: 1.2rem; font-weight: bold; color: #2196F3;">{result['Strategy']}</div>
                </div>
                <div class="glass-card" style="flex: 1; text-align: center;">
                    <div class="metric-label">CMP</div>
                    <div style="font-size: 1.8rem; font-weight: bold; color: #fff;">₹{result['CMP']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # --- ALERTS ---
            if result['Stats'].get('Squeeze') == "Yes":
                 st.warning("🔥 **VOLATILITY SQUEEZE DETECTED**: Market is coiling up for a massive move! Watch closely.", icon="🔥")

            # --- DETAILED ANALYSIS ---
            c_left, c_right = st.columns([2, 1])
            
            with c_left:
                st.markdown("#### 📉 Price Action & Levels")
                
                # Execution Plan using Cards
                if result['Signal'] != "NEUTRAL":
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1: render_metric_card("ENTRY", f"₹{result['Entry']}", color="#2196F3")
                    with ec2: render_metric_card("STOP LOSS", f"₹{result['Stop Loss']}", color="#ff1744")
                    with ec3: render_metric_card("TARGET", f"₹{result['Target 1']}", color="#00e676")
                else:
                    # Show Watch Levels for Neutral
                    st.info("⚠️ Neutral Signal. Watch these Key Levels:")
                    nc1, nc2, nc3 = st.columns(3)
                    with nc1: render_metric_card("SUPPORT (S1)", f"₹{result['KeyLevel_S1']}", color="#ff1744")
                    with nc2: render_metric_card("PIVOT", f"₹{result['KeyLevel_P']}", color="#2196F3")
                    with nc3: render_metric_card("RESIST (R1)", f"₹{result['KeyLevel_R1']}", color="#00e676")

                # Chart
                if 'History' in result:
                    import plotly.graph_objects as go
                    hist = result['History']
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name='Price'))
                    
                    # Add simple Moving Averages
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA_20'], line=dict(color='orange', width=1), name='EMA 20'))
                    fig.add_trace(go.Scatter(x=hist.index, y=hist['EMA_200'], line=dict(color='purple', width=2), name='EMA 200'))
                    
                    fig.update_layout(
                        height=400, 
                        template="plotly_dark", 
                        margin=dict(l=0, r=0, t=0, b=0),
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                # --- NEW: STOCK SPECIFIC NEWS ---
                st.markdown("### 📰 Related News")
                from news_engine import fetch_stock_specific_news
                stock_news = fetch_stock_specific_news(ticker)
                
                if stock_news:
                    for item in stock_news[:3]: # Show top 3
                        st.markdown(f"""
                        <div style="padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px;">
                            <a href="{item['Link']}" target="_blank" style="text-decoration:none; color: #fff; font-weight: bold;">{item['Headline']}</a>
                            <div style="font-size: 0.8rem; color: #aaa; margin_top: 4px;">{item['Time']} | Source: {item['Source']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No recent specific news found.")

            with c_right:
                st.markdown("#### 📊 Tech Vitals")
                stats = result['Stats']
                
                # Compact Technical Table
                tech_df = pd.DataFrame([
                    {"Metric": "Trend", "Value": stats.get('Trend', '-')},
                    {"Metric": "RSI (14)", "Value": stats['RSI']},
                    {"Metric": "ADX Strength", "Value": stats['ADX']},
                    {"Metric": "Volume", "Value": stats.get('Volume Status', '-')},
                    {"Metric": "PCR (Sentiment)", "Value": result.get('FnO', {}).get('PCR', 'N/A') if result.get('FnO') else '-'}
                ])
                st.dataframe(tech_df, hide_index=True, use_container_width=True)
                
                # Fundamentals Mini-View
                fund = result.get('Fundamentals')
                if fund:
                    st.markdown("#### 🏢 Fundamentals")
                    f_df = pd.DataFrame([
                        {"Metric": "ROE", "Value": f"{fund['ROE %']}%"},
                        {"Metric": "Debt/Eq", "Value": fund['Debt/Equity']},
                        {"Metric": "Margins", "Value": f"{fund['Profit Margins %']}%"}
                    ])
                    st.dataframe(f_df, hide_index=True, use_container_width=True)

# --- MODE 3: DASHBOARD & NEWS ---
elif mode == "Dashboard & News":
    st.markdown("### 📰 Intelligent Market Pulse")
    
    with st.spinner("Analyzing Global Sentiments..."):
        news_groups = fetch_market_news()
        
    # Grid Layout for News
    num_cols = 2
    cols = st.columns(num_cols)
    
    for idx, group in enumerate(news_groups):
        score = group.get('Score', 0)
        card_color = "rgba(0, 230, 118, 0.1)" if score >= 2 else "rgba(255, 23, 68, 0.1)" if score <= -2 else "rgba(255, 255, 255, 0.05)"
        border_color = "#00e676" if score >= 2 else "#ff1744" if score <= -2 else "rgba(255, 255, 255, 0.2)"
        
        with cols[idx % num_cols]:
            st.markdown(f"""
            <div class="glass-card" style="background: {card_color}; border-color: {border_color};">
                <h4 style="margin-bottom: 5px;">{group['Headline']}</h4>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="font-size: 0.8em; color: #aaa;">{group['Time']}</span>
                    <span style="font-weight: bold; color: {border_color};">Score: {score}</span>
                </div>
                <p style="font-size: 0.9em; color: #ddd;">{group['Impact']}</p>
                <a href="{group['Link']}" target="_blank" style="color: #2196F3; text-decoration: none; font-size: 0.9em;">Read Source →</a>
            </div>
            """, unsafe_allow_html=True)

# --- MODE 4: FULL SCAN ---
elif mode == "Full Nifty 500 Scan":
    st.markdown("### 🚀 Nifty 500 Turbo Scanner")
    st.info("This scans 500 stocks. Be patient.")
    
    if st.button("Start Scan", type="primary"):
        with st.spinner("Scanning Market..."):
            res = scan_stocks()
            if res['ALL_TRADES']:
                st.success(f"Found {len(res['ALL_TRADES'])} opportunities!")
                st.dataframe(pd.DataFrame(res['ALL_TRADES']))
            else:
                st.warning("No clear setups found right now.")

