import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, send_file
import os, json, datetime
import requests

app = Flask(__name__)

BALANCE_FILE = "balance.json"
INITIAL_BALANCE = 100000
TELE_TOKEN = os.getenv("8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk")
CHAT_ID = os.getenv("5444253276")

def get_balance():
    if not os.path.exists(BALANCE_FILE):
        return {"balance": INITIAL_BALANCE, "qty": 0, "trades": []}
    with open(BALANCE_FILE) as f:
        return json.load(f)

def save_balance(data):
    with open(BALANCE_FILE, "w") as f:
        json.dump(data, f)

def get_nifty():
    # FIX: period 5d, interval 15m - 1970 bug varilla
    df = yf.download("^NSEI", period="5d", interval="15m", progress=False)
    df.dropna(inplace=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    # EMA strategy
    df['EMA9'] = df['Close'].ewm(span=9).mean()
    df['EMA21'] = df['Close'].ewm(span=21).mean()
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
    plt.plot(df['Close'][-100:], label="NIFTY")
    plt.plot(df['EMA9'][-100:], label="EMA9")
    plt.plot(df['EMA21'][-100:], label="EMA21")
    plt.legend()
    plt.title(f"NIFTY {datetime.datetime.now().strftime('%d-%b %I:%M %p')}")
    plt.tight_layout()
    plt.savefig("chart.png")
    plt.close()
    return "chart.png"

@app.route("/")
def home():
    df = get_nifty()
    port = get_balance()
    live = round(float(df['Close'].iloc[-1]), 2)
    pnl = (live * port['qty'] + port['balance'] - INITIAL_BALANCE) if port['qty']>0 else (port['balance']-INITIAL_BALANCE)
    
    html = f"""
    <h2>Bot LIVE ✅ NIFTY: {live}</h2>
    <h3>💰 Paper Balance: ₹{port['balance']:.2f}</h3>
    <h3>📦 Qty: {port['qty']} | P&L: ₹{pnl:.2f}</h3>
    <img src='/chart' style='width:100%'>
    <h3>Trades:</h3>
    <pre>{json.dumps(port['trades'][-10:], indent=2)}</pre>
    <a href='/telegram'>Test Telegram</a> | <a href='/debug'>Debug</a>
    """
    return html

@app.route("/chart")
def chart_route():
    df = get_nifty()
    f = plot_chart(df)
    return send_file(f, mimetype='image/png')

@app.route("/telegram")
def telegram():
    df = get_nifty()
    signal = generate_signal(df)
    port = get_balance()
    live = float(df['Close'].iloc[-1])
    chart = plot_chart(df)
    
    # Paper trading execution
    msg = ""
    if signal == "BUY" and port['qty']==0:
        qty = int(port['balance'] // live)
        if qty>0:
            port['balance'] -= qty*live
            port['qty'] = qty
            port['trades'].append({"type":"BUY","price":live,"time":str(datetime.datetime.now())})
            msg = f"🟢 AUTO BUY {qty} @ {live}"
            save_balance(port)
    elif signal == "SELL" and port['qty']>0:
        port['balance'] += port['qty']*live
        port['trades'].append({"type":"SELL","price":live,"time":str(datetime.datetime.now()),"qty":port['qty']})
        msg = f"🔴 AUTO SELL {port['qty']} @ {live}"
        port['qty']=0
        save_balance(port)
    
    caption = f"Bot LIVE ✅\nNIFTY: {live}\nSignal: {signal}\n{msg}\nBalance: ₹{port['balance']:.0f} | Qty: {port['qty']}"
    
    if TELE_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELE_TOKEN}/sendPhoto"
        with open(chart, 'rb') as photo:
            requests.post(url, data={"chat_id":CHAT_ID,"caption":caption}, files={"photo":photo})
    
    return caption

@app.route("/debug")
def debug():
    df = get_nifty()
    return f"Rows: {len(df)} Last: {df.index[-1]} Close: {df['Close'].iloc[-1]}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
