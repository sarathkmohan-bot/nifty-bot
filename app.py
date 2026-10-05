from flask import Flask
import os, time, requests, threading, json, datetime
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPRegressor
from telegram import Bot
import asyncio
import yfinance as yf

app = Flask(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
PAPER_FILE = "/tmp/paper.json"

def load_paper():
    try:
        with open(PAPER_FILE,'r') as f: return json.load(f)
    except:
        return {"holding":False,"entry":0,"pnl":0,"trades":0,"wins":0,"last_price":0}

def save_paper(d):
    with open(PAPER_FILE,'w') as f: json.dump(f,d)
    with open(PAPER_FILE,'w') as f: json.dump(d,f)

paper = load_paper()

@app.route('/')
def home():
    return f"PnL: {paper['pnl']:.2f} | Trades: {paper['trades']}"

def get_real_nifty_live():
    try:
        s = requests.Session()
        h = {"User-Agent":"Mozilla/5.0","Referer":"https://www.nseindia.com/"}
        s.get("https://www.nseindia.com", headers=h, timeout=10)
        r = s.get("https://www.nseindia.com/api/allIndices", headers=h, timeout=10).json()
        for i in r['data']:
            if i['index']=='NIFTY 50':
                return float(i['last']), float(i['previousClose']), float(i['variation']), float(i['percentChange'])
    except Exception as e:
        print(f"NSE fail {e}")
    return None

def get_history_for_lstm(live_price):
    try:
        df = yf.download("^NSEI", period="3mo", interval="1d", progress=False, auto_adjust=True)
        closes = df['Close'].values.flatten()
        # override last candle with real live price
        closes[-1] = live_price
        return closes
    except:
        return np.array([live_price]*80)

async def send(text):
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=text, parse
