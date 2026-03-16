import streamlit as st
import pandas as pd
from binance.client import Client
import requests
import time
import os

# --- Configurations ---
TOKEN = "8522666956:AAEkx4BjHjYg84le_uqJqnAofx8moPDo9io" # သင့် Bot Token
CHAT_ID = "5075268865" # သင့် Chat ID

# Page Config
st.set_page_config(page_title="CryptoIntel Pro", layout="wide")
st.title("🚀 CryptoIntel Professional Advisor")

# --- Helper Functions ---
def send_telegram_alert(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram Error: {e}")

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
        
        # Strategy Logic
        is_buy = (c['RSI'] < 35) and (c['SMA50'] > c['SMA200']) and (c['Volume'] > c['Vol_SMA'])
        is_sell = (c['RSI'] > 65) and (c['SMA50'] < c['SMA200'])
        
        action = "🔥 BUY" if is_buy else ("⚠️ SELL" if is_sell else "Wait")
        
        # Entry, SL, TP Calculation
        price = c['Close']
        sl = price * 0.95 if is_buy else price * 1.05
        tp1 = price * 1.02 if is_buy else price * 0.98
        tp2 = price * 1.05 if is_buy else price * 0.95
        tp3 = price * 1.08 if is_buy else price * 0.92
        
        return price, c['RSI'], action, sl, tp1, tp2, tp3
    except:
        return None, None, "Error", 0, 0, 0, 0

# --- Automatic Scanning Logic (Cron-job က ခေါက်တိုင်း အလုပ်လုပ်မည်) ---
if 'last_scan' not in st.session_state:
    st.session_state.last_scan = 0

current_time = time.time()
# ၅ မိနစ် (၃၀၀ စက္ကန့်) တစ်ခါ Scan ဖတ်မည်
if current_time - st.session_state.last_scan > 300:
    st.session_state.last_scan = current_time
    client = Client()
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT'] # အဓိက Coin များ
    
    for s in symbols:
        price, rsi, action, sl, tp1, tp2, tp3 = analyze_coin(s)
        if action != "Wait" and action != "Error":
            msg = (f"🎯 <b>Signal: {s}</b>\n"
                   f"Action: {action}\n"
                   f"Entry: {price:.4f}\n"
                   f"RSI: {rsi:.2f}\n"
                   f"➖➖➖➖➖➖\n"
                   f"🚫 SL: {sl:.4f}\n"
                   f"✅ TP1: {tp1:.4f}\n"
                   f"✅ TP2: {tp2:.4f}\n"
                   f"✅ TP3: {tp3:.4f}")
            send_telegram_alert(msg)

# --- UI Layout ---
if 'df' not in st.session_state: st.session_state.df = pd.DataFrame()

if st.sidebar.button("🚀 Manual Scan (20 Coins)"):
    with st.spinner('Scanning...'):
        client = Client()
        symbols = [s['symbol'] for s in client.get_exchange_info()['symbols'] if s['symbol'].endswith('USDT')][:20]
        results = []
        for s in symbols:
            pr, rsi, act, sl, t1, t2, t3 = analyze_coin(s)
            if pr:
                results.append({"Symbol": s, "Price": pr, "RSI": rsi, "Action": act, "SL": sl, "TP1": t1, "TP2": t2, "TP3": t3})
        st.session_state.df = pd.DataFrame(results)
        st.rerun()

st.subheader("Market Signals")
st.dataframe(st.session_state.df, use_container_width=True)
