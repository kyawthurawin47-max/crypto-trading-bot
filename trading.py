import streamlit as st
import pandas as pd
from binance.client import Client
import requests
import time

# Page Config
st.set_page_config(page_title="CryptoIntel Pro", layout="wide")
st.title("🚀 CryptoIntel Professional Advisor")

# Helper functions for Indicators (Without pandas-ta)
def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data, fast=12, slow=26, signal=9):
    ema_fast = data.ewm(span=fast, adjust=False).mean()
    ema_slow = data.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    macd_signal = macd.ewm(span=signal, adjust=False).mean()
    return macd, macd_signal

# API Setup
client = Client()

def analyze_coin(symbol):
    try:
        klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1HOUR, "200 hours ago UTC")
        df = pd.DataFrame(klines).iloc[:, :6]
        df.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        
        # Calculate Indicators
        df['RSI'] = calculate_rsi(df['Close'])
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        df['Vol_SMA'] = df['Volume'].rolling(window=20).mean()
        macd, macd_signal = calculate_macd(df['Close'])
        df['MACD'] = macd
        
        c = df.iloc[-1]
        
        # Strategy
        is_buy = (c['RSI'] < 35) and (c['SMA50'] > c['SMA200']) and (c['Volume'] > c['Vol_SMA'])
        is_sell = (c['RSI'] > 65) and (c['SMA50'] < c['SMA200'])
        
        action = "🔥 BUY" if is_buy else ("⚠️ SELL" if is_sell else "Wait")
        return c['Close'], c['RSI'], action
    except: return None, None, "Error"

# UI
if 'df' not in st.session_state: st.session_state.df = pd.DataFrame()

if st.sidebar.button("🚀 Scan All USDT"):
    with st.spinner('Analyzing...'):
        symbols = [s['symbol'] for s in client.get_exchange_info()['symbols'] if s['symbol'].endswith('USDT')][:20]
        results = []
        for s in symbols:
            pr, rsi, act = analyze_coin(s)
            if pr: results.append({"Symbol": s, "Price": round(pr, 4), "RSI": round(rsi, 2), "Action": act})
        st.session_state.df = pd.DataFrame(results)
        st.rerun()

st.dataframe(st.session_state.df, use_container_width=True)
