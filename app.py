import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, send_file
import os
import json
import datetime
import requests

app = Flask(__name__)

BALANCE_FILE = "balance.json"
INITIAL_BALANCE = 100000
TELE_TOKEN = os.getenv("8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk")
CHAT_ID = os.getenv("5444253276")

def get_balance():
    if not os.path.exists(BALANCE_FILE):
        return {"balance": INITIAL_BALANCE, "qty": 0, "trades": []}
    try:
        with open(BALANCE_FILE) as f:
            return json.load(f)
    except:
        return {"balance": INITIAL_BALANCE, "qty": 0, "trades": []}

def save_balance(data):
    with open(BALANCE_FILE, "w") as f:
        json.dump(data, f)

def get_nifty():
    df = yf.download("^NSEI", period="5d", interval="15m", progress=False, auto_adjust=False)
    df.dropna(inplace=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df['EMA9'] = df['Close'].ewm(span=9).mean()
    df['EMA21'] = df['Close'].ewm(span=21).mean()
    df = df.tail(80)
    return df

def generate_signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    if prev['EMA9'] < prev['EMA21'] and last['EMA9'] > last['EMA21']:
        return "BUY"
    elif prev['EMA9'] > prev['EMA21'] and last['EMA9'] < last['EMA21']:
        return "SELL"
    else:
        return "HOLD"

def plot_chart(df):
    plt.figure(figsize=(10,4))
    x = range(len(df))
    plt.plot(x, df['Close'], label="NIFTY")
    plt.plot(x, df['EMA9'], label="EMA9")
    plt.plot(x, df['EMA21'], label="EMA21")
    labels = [d.strftime("%d %H:%M") for d in df.index]
    plt.xticks(x[::10], labels[::10], rotation=30, fontsize=7)
    plt.legend(fontsize=8)
    plt.title(f"NIFTY 15m - {datetime.datetime.now().strftime('%d %I:%M %p')}")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("chart.png")
    plt.close()
    return "chart.png"

@app.route("/")
def home():
    df = get_nifty()
    port = get_balance()
    live = round(float(df['Close'].iloc[-1]), 2)
    pnl = 0
    if port['qty'] > 0:
        pnl = live * port['qty'] + port['balance'] - INITIAL_BALANCE
    else:
        pnl = port['balance'] - INITIAL_BALANCE
    return f"<h2>NIFTY: {live}</h2><h3>Balance: {port['balance']:.0f} Qty:{port['qty']} P&L:{pnl:.0f}</h3><img src='/chart' width='100%'><br><a href='/telegram'>Test Telegram</a>"

@app.route("/chart")
def chart_route():
    df = get_nifty()
    f = plot_chart(df)
    return send_file(f, mimetype='image/png')

@app.route("/telegram")
def telegram_route():
    df = get_nifty()
    signal = generate_signal(df)
    port = get_balance()
    live = float(df['Close'].iloc[-1])
    chart = plot_chart(df)
    
    if port['qty'] > 0:
        pnl = live * port['qty'] + port['balance'] - INITIAL_BALANCE
    else:
        pnl = port['balance'] - INITIAL_BALANCE
        
    now = datetime.datetime.now().strftime("%I:%M %p")
    msg = ""

    if signal == "BUY" and port['qty'] == 0:
        qty = int(port['balance'] // live)
        if qty > 0:
            port['balance'] = port['balance'] - qty * live
            port['qty'] = qty
            port['trades'].append({"type": "BUY", "price": live, "time": str(datetime.datetime.now())})
            msg = f"AUTO BUY {qty} @ {live:.2f}"
            save_balance(port)
    elif signal == "SELL" and port['qty'] > 0:
        port['balance'] = port['balance'] + port['qty'] * live
        port['trades'].append({"type": "SELL", "price": live, "time": str(datetime.datetime.now())})
        msg = f"AUTO SELL {port['qty']} @ {live:.2f}"
        port['qty'] = 0
        save_balance(port)

    caption = f"NIFTY 15m\nLive: {live:.1f}\nSignal: {signal}\nTime: {now}\n\nPaper: Rs.{port['balance']:.0f}\nQty: {port['qty']} | P&L: Rs.{pnl:.0f
