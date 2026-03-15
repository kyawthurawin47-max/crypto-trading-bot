import streamlit as st
import pandas as pd
import pandas_ta as ta
from binance.client import Client
import requests
import time
import threading # Background မှာ Telegram Alert ပို့ဖို့ လိုအပ်ပါတယ်
import streamlit as st
# Page Config
st.set_page_config(page_title="CryptoIntel Pro", layout="wide")
st.title("🚀 CryptoIntel Professional Advisor")

# Initialize Session State
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Symbol", "Price", "RSI", "Action", "SL", "TP1", "TP2", "TP3", "Pos Size"])

# API Setup
TOKEN, CHAT_ID = "8522666956:AAEkx4BjHjYg84le_uqJqnAofx8moPDo9io", "5075268865"
client = Client()

def send_telegram_alert(msg):
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'})
    except: pass

def analyze_coin(symbol, risk_amount):
    try:
        klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1HOUR, "150 hours ago UTC")
        df = pd.DataFrame(klines).iloc[:, :6]
        df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        
        # Indicators
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['SMA50'] = ta.sma(df['Close'], length=50)
        df['SMA200'] = ta.sma(df['Close'], length=200)
        df['Vol_SMA'] = df['Volume'].rolling(window=20).mean()
        macd = ta.macd(df['Close'])
        df = pd.concat([df, macd], axis=1)
        
        c = df.iloc[-1]
        
        # Confluence Strategy
        is_buy = (c['RSI'] < 35) and (c['SMA50'] > c['SMA200']) and (c['MACDh_12_26_9'] > 0) and (c['Volume'] > c['Vol_SMA'])
        is_sell = (c['RSI'] > 65) and (c['SMA50'] < c['SMA200']) and (c['MACDh_12_26_9'] < 0)
        
        action = "🔥 BUY" if is_buy else ("⚠️ SELL" if is_sell else "Wait")
        sl = c['Close'] * 0.95 if is_buy else c['Close'] * 1.05
        tp1, tp2, tp3 = (c['Close']*1.02, c['Close']*1.05, c['Close']*1.08) if is_buy else (c['Close']*0.98, c['Close']*0.95, c['Close']*0.92)
        
        return c['Close'], c['RSI'], action, sl, tp1, tp2, tp3, is_buy, is_sell
    except: return None, None, "Wait", 0, 0, 0, 0, False, False

# --- Sidebar ---
st.sidebar.header("⚙️ Risk Management")
capital = st.sidebar.number_input("Total Capital (USDT):", value=1000)
risk_pct = st.sidebar.slider("Risk per Trade (%):", 0.1, 5.0, 1.0)
risk_amount = (capital * (risk_pct / 100))

# --- Manual Scan Button ---
if st.sidebar.button("🚀 Scan All USDT"):
    with st.spinner('Analyzing Markets...'):
        symbols = [s['symbol'] for s in client.get_exchange_info()['symbols'] if s['symbol'].endswith('USDT')][:50]
        results = []
        for s in symbols:
            pr, rsi, act, sl, tp1, tp2, tp3, _, _ = analyze_coin(s, risk_amount)
            if pr:
                results.append({"Symbol": s, "Price": round(pr, 4), "RSI": round(rsi, 2), "Action": act, "SL": round(sl, 2), "TP1": round(tp1, 2), "TP2": round(tp2, 2), "TP3": round(tp3, 2), "Pos Size": round(risk_amount, 2)})
        st.session_state.df = pd.DataFrame(results)
        st.rerun()

# --- Telegram Auto-Monitor (Background Thread) ---
def monitor_market():
    while True:
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'] # စမ်းသပ်ရန်အတွက် အဓိက Coin များ
        for s in symbols:
            pr, rsi, act, sl, tp1, tp2, tp3, is_buy, is_sell = analyze_coin(s, risk_amount)
            if is_buy or is_sell:
                send_telegram_alert(f"{'🔥 BUY' if is_buy else '⚠️ SELL'} signal for {s}! Price: {pr:.2f}")
        time.sleep(300) # 5 မိနစ်တိုင်း စစ်ဆေးရန်

# Thread စတင်ခြင်း (App စဖွင့်ရင် တစ်ခါပဲ run ပါမယ်)
if 'thread_started' not in st.session_state:
    threading.Thread(target=monitor_market, daemon=True).start()
    st.session_state.thread_started = True

# --- UI Tabs ---
# --- UI Tabs တွေကို တစ်ခါတည်း စနစ်တကျ သတ်မှတ်ပါ ---
t1, t2, t3, t4, t5 = st.tabs(["🏠 Home", "🎯 Spot Signals", "⚡ Future Signals", "💡 Advice", "📈 Charts"])

# 1. Home Tab - အချက်အလက်အားလုံးပြမယ်
with t1: 
    st.subheader("Market Overview")
    st.dataframe(st.session_state.df, use_container_width=True)

# 2. Spot Signals Tab - BUY signal တွေပဲပြမယ်
with t2: 
    st.subheader("🎯 Spot Signals (BUY)")
    if not st.session_state.df.empty: 
        buy_df = st.session_state.df[st.session_state.df['Action'] == "🔥 BUY"]
        st.dataframe(buy_df, use_container_width=True)
    else:
        st.write("No signals yet. Press Scan!")

# 3. Future Signals Tab - Wait မဟုတ်တာတွေပြမယ်
with t3:
    st.subheader("⚡ Future Signals")
    if not st.session_state.df.empty: 
        signal_df = st.session_state.df[st.session_state.df['Action'] != "Wait"]
        st.dataframe(signal_df, use_container_width=True)

# 4. Advice Tab - Sentiment ပြမယ်
with t4:
    if not st.session_state.df.empty: 
        st.info(f"Market Sentiment: {'Oversold' if st.session_state.df['RSI'].mean() < 35 else 'Overbought' if st.session_state.df['RSI'].mean() > 65 else 'Neutral'}")

# 5. Charts Tab - RSI Chart ပြမယ်
with t5: 
    st.subheader("📈 Technical Chart (RSI)")
    if not st.session_state.df.empty:
        selected_symbol = st.selectbox("Select Coin to view RSI:", st.session_state.df['Symbol'].tolist())
        
        if selected_symbol:
            klines = client.get_historical_klines(selected_symbol, Client.KLINE_INTERVAL_1HOUR, "50 hours ago UTC")
            df_chart = pd.DataFrame(klines).iloc[:, :6]
            df_chart.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            df_chart['Close'] = df_chart['Close'].astype(float)
            df_chart['RSI'] = ta.rsi(df_chart['Close'], length=14)
            
            st.line_chart(df_chart['RSI'])
            st.write(f"Current RSI for {selected_symbol}: {round(df_chart['RSI'].iloc[-1], 2)}")