import os, requests, datetime, pytz
from flask import Flask
import time

app = Flask(__name__)

# strip() add cheythu - space issue fix
BOT_TOKEN = os.environ.get("8963319163:AAF5pnWLdDB5eEX-7EZ4Vvk-mhZu4rixzDk","").strip()
CHAT_ID = os.environ.get("5444253276","").strip()

last_sent = 0

def send_tg(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return {"ok":False, "error":"Token/ID missing in Render"}
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
        return r.json()
    except Exception as e:
        return {"ok":False, "error":str(e)}

def get_price():
    try:
        s=requests.Session()
        h={'User-Agent':'Mozilla/5.0','Referer':'https://www.nseindia.com/'}
        s.get("https://www.nseindia.com", headers=h, timeout=10)
        r=s.get("https://www.nseindia.com/api/allIndices", headers=h, timeout=10)
        if r.status_code==200:
            for x in r.json()['data']:
                if x['index']=='NIFTY 50':
                    return float(x['last']), "NSE"
    except: pass
    return 22555.75, "Fallback"

@app.route('/')
def home():
    price, src = get_price()
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.datetime.now(ist).strftime('%H:%M:%S %d-%b %Y')
    token_ok = "YES" if BOT_TOKEN else "NO"
    return f"Bot LIVE - Price: {price} ({src}) Time: {now} | Token Loaded: {token_ok} ID Loaded: {'YES' if CHAT_ID else 'NO'}"

@app.route('/telegram')
def test_tg():
    result = send_tg("✅ Test - Token ok aanu!")
    return f"Telegram status: {result} <br><br> Token len: {len(BOT_TOKEN)} | Chat ID: {CHAT_ID[:3]}***"

@app.route('/debug')
def debug():
    return f"Token exists: {bool(BOT_TOKEN)} len={len(BOT_TOKEN)} <br> ChatID exists: {bool(CHAT_ID)} val={CHAT_ID[:2]}***"
