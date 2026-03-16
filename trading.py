import streamlit as st
import pandas as pd
from binance.client import Client
import requests
import time
import os

# --- ၁။ Configurations ---
TOKEN = "8522666956:AAEkx4BjHjYg84le_uqJqnAofx8moPDo9io"
CHAT_ID = "5075268865"

# Page Config (ဒါက အပေါ်ဆုံးမှာ ရှိရပါမယ်)
st.set_page_config(page_title="CryptoIntel Pro", layout="wide")

# --- ၂။ Initialize Session State (Error မတက်အောင် အရင်ဆုံး သတ်မှတ်ခြင်း) ---
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["Symbol", "Price", "RSI", "Action", "SL", "TP1", "TP2", "TP3"])

if 'last_scan' not in st.session_state:
    st.session_state.last_scan = 0

# --- ၃။ Helper Functions ---
def send_telegram_alert(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}
        requests.post(url, data=data)
    except Exception as e:
        st.error(f"Telegram Error: {e}")

def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_coin(symbol):
    try:
        client = Client()
        klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1HOUR, "150 hours ago UTC")
        df = pd.DataFrame(klines).iloc[:, :6]
        df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        
        # Indicators
        df['RSI'] = calculate_rsi(df['Close'])
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        df['Vol_SMA'] = df['Volume'].rolling(window=20).mean()
        
        c = df.iloc[-1]
        
        # Strategy Logic (Trend Following + RSI)
        is_buy = (c['RSI'] < 40) and (c['SMA50'] > c['SMA200']) and (c['Volume'] > c['Vol_SMA'])
        is_sell = (c['RSI'] > 60) and (c['SMA50'] < c['SMA200'])
        
        action = "🔥 BUY" if is_buy else ("⚠️ SELL" if is_sell else "Wait")
        
        price = c['Close']
        sl = round(price * 0.95 if is_buy else price * 1.05, 4)
        tp1 = round(price * 1.02 if is_buy else price * 0.98, 4)
        tp2 = round(price * 1.05 if is_buy else price * 0.95, 4)
        tp3 = round(price * 1.08 if is_buy else price * 0.92, 4)
        
        return price, round(c['RSI'], 2), action, sl, tp1, tp2, tp3
    except:
        return None, None, "Error", 0, 0, 0, 0

# --- ၄။ Automatic Scanning (Background Check) ---
current_time = time.time()
if current_time - st.session_state.last_scan > 300: # ၅ မိနစ်တစ်ခါ
    st.session_state.last_scan = current_time
    # စမ်းသပ်ရန် အဓိက Coin (၅) ခု
    auto_symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT']
    for s in auto_symbols:
        price, rsi, action, sl, tp1, tp2, tp3 = analyze_coin(s)
        if action != "Wait" and action != "Error":
            msg = (f"🚀 <b>{action} Signal: {s}</b>\n"
                   f"Entry: {price}\n"
                   f"RSI: {rsi}\n"
                   f"➖➖➖➖➖➖\n"
                   f"🚫 SL: {sl}\n"
                   f"✅ TP1: {tp1}\n"
                   f"✅ TP2: {tp2}\n"
                   f"✅ TP3: {tp3}")
            send_telegram_alert(msg)

# --- ၅။ UI Main Layout ---
st.title("🚀 CryptoIntel Professional Advisor")

# Sidebar for manual actions
st.sidebar.header("Control Panel")
if st.sidebar.button("🚀 Manual Scan All USDT"):
    with st.spinner('Analyzing Top 20 USDT Pairs...'):
        client = Client()
        symbols = [s['symbol'] for s in client.get_exchange_info()['symbols'] if s['symbol'].endswith('USDT')][:20]
        results = []
        for s in symbols:
            pr, rsi, act, sl, t1, t2, t3 = analyze_coin(s)
            if pr:
                results.append({
                    "Symbol": s, "Price": pr, "RSI": rsi, 
                    "Action": act, "SL": sl, "TP1": t1, "TP2": t2, "TP3": t3
                })
        st.session_state.df = pd.DataFrame(results)
        st.rerun()

# --- ၆။ UI Tabs ---
tab1, tab2, tab3 = st.tabs(["🏠 All Symbols", "🎯 Spot Signals", "⚡ Future Signals"])

with tab1:
    st.subheader("Market Overview (Live)")
    if not st.session_state.df.empty:
        # အရောင်အဆင်းနဲ့ ပြသခြင်း
        def color_action(val):
            color = 'green' if 'BUY' in str(val) else 'red' if 'SELL' in str(val) else 'gray'
            return f'color: {color}'
        
        st.dataframe(st.session_state.df.style.applymap(color_action, subset=['Action']), use_container_width=True)
    else:
        st.info("No data available. Please press 'Manual Scan' on the sidebar.")

with tab2:
    st.subheader("🎯 Spot Signals (BUY Only)")
    if not st.session_state.df.empty:
        spot_df = st.session_state.df[st.session_state.df['Action'] == "🔥 BUY"]
        if not spot_df.empty:
            st.success(f"Found {len(spot_df)} Buy Opportunities!")
            st.table(spot_df[['Symbol', 'Price', 'RSI', 'SL', 'TP1', 'TP2']])
        else:
            st.write("No BUY signals at the moment.")

with tab3:
    st.subheader("⚡ Future Signals (Long/Short)")
    if not st.session_state.df.empty:
        future_df = st.session_state.df[st.session_state.df['Action'] != "Wait"]
        if not future_df.empty:
            st.table(future_df)
        else:
            st.write("No active signals for Futures.")
