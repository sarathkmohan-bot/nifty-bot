import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from flask import Flask, send_file
import os, json, datetime, requests

app = Flask(__name__)

BALANCE_FILE = "balance.json"
INITIAL_BALANCE = 100000
TELE_TOKEN = "8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk"
CHAT_ID = "5444253276"

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
    df["EMA9"] = df["Close"].ewm(span=9).mean()
    df["EMA21"] = df["Close"].ewm(span=21).mean()
    df = df.tail(80)
    return df

def generate_signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    if prev["EMA9"] < prev["EMA21"] and last["EMA9"] > last["EMA21"]:
        return "BUY"
    elif prev["EMA9"] > prev["EMA21"] and last["EMA9"] < last["EMA21"]:
        return "SELL"
    else:
        return "HOLD"

def plot_chart(df):
    plt.figure(figsize=(10,4))
    x = range(len(df))
    plt.plot(x, df["Close"], label="NIFTY")
    plt.plot(x, df["EMA9"], label="EMA9")
    plt.plot(x, df["EMA21"], label="EMA21")
    labels = [d.strftime("%d %H:%M") for d in df.index]
    plt.xticks(x[::10], labels[::10], rotation=30, fontsize=7)
    plt.legend(fontsize=8)
    plt.title("NIFTY 15m")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig("chart.png")
    plt.close()
    return "chart.png"

@app.route("/")
def home():
    df = get_nifty()
    port = get_balance()
    live = round(float(df["Close"].iloc[-1]), 2)
    bal = int(port["balance"])
    qty = int(port["qty"])
    if qty > 0:
        pnl = int(live * qty + port["balance"] - INITIAL_BALANCE)
    else:
        pnl = int(port["balance"] - INITIAL_BALANCE)
    return f"<h2>NIFTY: {live}</h2><h3>Bal:{bal} Qty:{qty} P&L:{pnl}</h3><img src='/chart' width='100%'><br><a href='/telegram'>Test Telegram</a>"

@app.route("/chart")
def chart_route():
    df = get_nifty()
    f = plot_chart(df)
    return send_file(f, mimetype="image/png")

@app.route("/telegram")
def telegram_route():
    df = get_nifty()
    signal = generate_signal(df)
    port = get_balance()
    live = float(df["Close"].iloc[-1])
    chart = plot_chart(df)
    
    bal = int(port["balance"])
    qty = int(port["qty"])
    if qty > 0:
        pnl = int(live * qty + port["balance"] - INITIAL_BALANCE)
    else:
        pnl = int(port["balance"] - INITIAL_BALANCE)
    
    now = datetime.datetime.now().strftime("%I:%M %p")
    msg = ""

    if signal == "BUY" and port["qty"] == 0:
        buy_qty = int(port["balance"] // live)
        if buy_qty > 0:
            port["balance"] = port["balance"] - buy_qty * live
            port["qty"] = buy_qty
            port["trades"].append({"type": "BUY", "price": live})
            msg = f"AUTO BUY {buy_qty}"
            save_balance(port)
            qty = buy_qty
            bal = int(port["balance"])
    elif signal == "SELL" and port["qty"] > 0:
        port["balance"] = port["balance"] + port["qty"] * live
        port["trades"].append({"type": "SELL", "price": live})
        msg = f"AUTO SELL {port['qty']}"
        port["qty"] = 0
        save_balance(port)
        qty = 0
        bal = int(port["balance"])

    caption = "NIFTY 15m\nLive: " + str(round(live,1)) + "\nSignal: " + signal + "\nTime: " + now + "\n\nPaper: Rs." + str(bal) + "\nQty: " + str(qty) + " | P&L: Rs." + str(pnl)
    if msg:
        caption = caption + "\n" + msg

    if TELE_TOKEN and CHAT_ID:
        url = "https://api.telegram.org/bot" + TELE_TOKEN + "/sendPhoto"
        try:
            with open(chart, "rb") as photo:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": caption}, files={"photo": photo}, timeout=15)
        except Exception as e:
            print("Telegram Error", e)

    return caption.replace("\n", "<br>")

if __name__ == "__main__":
    port_num = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port_num)
