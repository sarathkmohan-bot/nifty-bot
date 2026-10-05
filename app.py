import os
from flask import Flask
import requests
import datetime, pytz
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io, base64, threading, time

app = Flask(__name__)

BOT_TOKEN = "8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk"
CHAT_ID = "5444253276"
PAPER_CAPITAL = 100000

trade_state = {"position": None, "entry": 0, "pnl": 0, "capital": PAPER_CAPITAL}

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: 
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def send_telegram_with_chart(caption, df):
    try:
        plt.figure(figsize=(10,5))
        last = df.tail(80)
        plt.plot(last.index, last['Close'], label='NIFTY')
        plt.plot(last.index, last['EMA9'], label='EMA9')
        plt.plot(last.index, last['EMA21'], label='EMA21')
        plt.legend(); plt.grid(alpha=0.3); plt.xticks(rotation=20)
        plt.title(f"NIFTY 15min - {caption[:40]}")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=130)
        buf.seek(0); plt.close()
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        files = {'photo': ('chart.png', buf, 'image/png')}
        data = {'chat_id': CHAT_ID, 'caption': caption}
        r = requests.post(url, files=files, data=data, timeout=20)
        return r.status_code == 200
    except Exception as e:
        print(f"Chart error: {e}")
        return send_telegram(caption)

def get_nifty():
    try:
        s = requests.Session()
        headers = {'User-Agent': 'Mozilla/5.0','Referer':'https://www.nseindia.com/'}
        s.get("https://www.nseindia.com", headers=headers, timeout=8)
        r = s.get("https://www.nseindia.com/api/allIndices", headers=headers, timeout=8)
        for d in r.json()['data']:
            if d['index'] == 'NIFTY 50':
                return str(d['last'])
    except:
        pass
    return "Market Closed"

def get_nifty_15min():
    try:
        df = yf.download("^NSEI", period="5d", interval="15m", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df.dropna(inplace=True)
        return df
    except:
        return None

def get_signal(df):
    if df is None or len(df) < 2: return "WAIT"
    if df['EMA9'].iloc[-2] <= df['EMA21'].iloc[-2] and df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1]:
        return "BUY 🔼"
    if df['EMA9'].iloc[-2] >= df['EMA21'].iloc[-2] and df['EMA9'].iloc[-1] < df['EMA21'].iloc[-1]:
        return "SELL 🔽"
    return "HOLD" if df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1] else "WAIT"

def paper_trade(price, signal):
    global trade_state
    if "BUY" in signal and trade_state["position"] != "LONG":
        if trade_state["position"] == "SHORT":
            trade_state["pnl"] += trade_state["entry"] - price
        trade_state["position"] = "LONG"; trade_state["entry"] = price
    elif "SELL" in signal and trade_state["position"] != "SHORT":
        if trade_state["position"] == "LONG":
            trade_state["pnl"] += price
