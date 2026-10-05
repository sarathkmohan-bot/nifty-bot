import os
from flask import Flask
import requests
import datetime, pytz

app = Flask(__name__)

BOT_TOKEN = os.environ.get("8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk","").strip()
CHAT_ID = os.environ.get("5444253276","").strip()

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

@app.route('/')
def home():
    ist = datetime.datetime.now(pytz.timezone('Asia/Kolkata')).strftime('%d-%b %I:%M %p IST')
    price = get_nifty()
    return f"Bot LIVE ✅<br>NIFTY: {price}<br>{ist}<br><br><a href='/telegram'>Test Telegram</a> | <a href='/debug'>Debug</a>"

@app.route('/debug')
def debug():
    all_keys = list(os.environ.keys())
    return f"BOT exists: {bool(BOT_TOKEN)} len={len(BOT_TOKEN)}<br>CHAT exists: {bool(CHAT_ID)} val={CHAT_ID[:3] if CHAT_ID else 'empty'}***<br>ENV keys: {all_keys[:20]}"

@app.route('/telegram')
def test_tg():
    if not BOT_TOKEN or not CHAT_ID:
        return f"FAILED: Token exists={bool(BOT_TOKEN)} Chat exists={bool(CHAT_ID)} - Check Render Environment Save"
    ok = send_telegram(f"✅ Test OK - NIFTY: {get_nifty()} - Bot is working!")
    return f"Sent={ok} - Check Telegram" if ok else "Telegram API failed - check BOT_TOKEN"

# Auto send on startup once
try:
    send_telegram(f"🚀 Bot deployed - NIFTY: {get_nifty()}")
except:
    pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
