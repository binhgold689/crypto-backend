import os
import sqlite3
import requests
import random
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta

app = FastAPI()

# --- DATABASE PATH (Persistent Volume) ---
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/users.db")

# --- 1. CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. CONFIG ---
TELEGRAM_TOKEN = "8679086264:AAHNVmsiHxmQUiLdKtYNLkBdEfKLxRMsuw"
CHAT_ID = "7388151158"

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT",
    "MATICUSDT", "NEARUSDT", "LTCUSDT", "ARBUSDT", "OPUSDT",
    "PAXGUSDT", "TIAUSDT", "SUIUSDT", "ORDIUSDT", "TRXUSDT"
]

# --- 3. INIT DATABASE ---
def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, expire_date TEXT)''')
    conn.commit()
    conn.close()

init_db()

class UserAuth(BaseModel):
    email: str
    password: str

# --- 4. API ---
@app.post("/register")
async def register(user: UserAuth):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    try:
        email = user.email.strip().lower()
        password = user.password.strip()
        expire = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (email, password, 'free', expire))
        conn.commit()
        msg = f"NEW USER: {email}, expire: {expire}"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                      json={"chat_id": CHAT_ID, "text": msg})
        return {"status": "success", "expire": expire}
    except:
        raise HTTPException(status_code=400, detail="Email already exists")
    finally:
        conn.close()

@app.post("/login")
def login(user: UserAuth):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    email = user.email.strip().lower()
    password = user.password.strip()
    c.execute("SELECT email, role, expire_date FROM users WHERE email=? AND password=?", (email, password))
    row = c.fetchone()
    conn.close()
    if row:
        return {"email": row[0], "role": row[1], "expire": row[2], "status": "success"}
    raise HTTPException(status_code=401, detail="Invalid email or password")

@app.get("/binh-gold-admin-portal")
@app.get("/admin/users-json")
def get_users_admin():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT email, role, expire_date FROM users")
    rows = c.fetchall()
    conn.close()
    return [{"email": r[0], "role": r[1], "expire_date": r[2]} for r in rows]

@app.get("/activate-vip")
def activate_vip(email: str, days: int = 30):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT expire_date FROM users WHERE email=?", (email,))
    row = c.fetchone()
    base_date = datetime.now()
    if row and datetime.strptime(row[0], "%Y-%m-%d") > datetime.now():
        base_date = datetime.strptime(row[0], "%Y-%m-%d")
    new_expire = (base_date + timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("UPDATE users SET role='vip', expire_date=? WHERE email=?", (new_expire, email))
    conn.commit()
    conn.close()
    label = "1 YEAR" if days >= 365 else "1 MONTH"
    msg = f"VIP ({label}): {email}, expire: {new_expire}"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                  json={"chat_id": CHAT_ID, "text": msg})
    return {"status": "success", "new_expire": new_expire}

@app.get("/prices")
def get_prices():
    try:
        res = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=5).json()
        return [{"symbol": "XAUUSD" if i['symbol'] == "PAXGUSDT" else i['symbol'],
                 "price": float(i['lastPrice'])} for i in res if i['symbol'] in COINS]
    except:
        return []

@app.get("/signals")
@app.get("/signals/vip")
def get_signals(email: str = "guest"):
    signals = []
    try:
        res = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=5).json()
        for item in res:
            if item['symbol'] in COINS:
                price = float(item['lastPrice'])
                change = float(item['priceChangePercent'])
                is_long = change < 0
                entry = price
                if is_long:
                    sl = price * 0.982
                    tp = price * 1.045
                    type_str = "LONG"
                else:
                    sl = price * 1.018
                    tp = price * 0.955
                    type_str = "SHORT"
                signals.append({
                    "pair": "XAUUSD" if item['symbol'] == "PAXGUSDT" else item['symbol'],
                    "type": type_str,
                    "entry": round(entry, 4),
                    "sl": round(sl, 4),
                    "tp1": round(entry + (tp - entry) * 0.5, 4),
                    "tp2": round(tp, 4),
                    "confidence": random.randint(88, 98),
                    "timestamp": int(time.time()),
                    "status": "LIVE"
                })
        return signals
    except:
        return []

@app.get("/")
def home():
    return {"status": "PulseSignal Backend Online", "linked_id": "7388151158"}
