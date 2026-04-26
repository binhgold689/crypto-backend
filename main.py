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

# --- 1. DATABASE PATH (Sử dụng Persistent Volume đã cấu hình) ---
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/users.db")

# --- 2. CONFIG (Lấy từ Variables để bảo mật và dễ thay đổi) ---
# Nếu chưa có biến trên Railway, nó sẽ dùng giá trị mặc định bên dưới
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8679086264:AAHNVmsiHxmQUiLdKtYNLkBdEfKLxRMsuw")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "7388151158")

# Danh sách COINS (Đã thêm BTCUSDT và PAXGUSDT để làm Vàng)
COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT",
    "MATICUSDT", "NEARUSDT", "LTCUSDT", "ARBUSDT", "OPUSDT",
    "PAXGUSDT", "TIAUSDT", "SUIUSDT", "ORDIUSDT", "TRXUSDT"
]

# --- 3. CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4. INIT DATABASE ---
def init_db():
    try:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (email TEXT PRIMARY KEY, password TEXT, role TEXT, expire_date TEXT)''')
        conn.commit()
        conn.close()
        print(f"Database initialized at {DATABASE_PATH}")
    except Exception as e:
        print(f"Init DB Error: {e}")

init_db()

class UserAuth(BaseModel):
    email: str
    password: str

# --- 5. HÀM GỬI TELEGRAM (Tách riêng để dễ quản lý) ---
def send_tele_msg(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=5)
    except Exception as e:
        print(f"Telegram Error: {e}")

# --- 6. API ENDPOINTS ---

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
        
        msg = f"🔔 NEW USER REGISTERED\nEmail: {email}\nExpire: {expire}"
        send_tele_msg(msg)
        
        return {"status": "success", "expire": expire}
    except Exception as e:
        print(f"Register Error: {e}")
        raise HTTPException(status_code=400, detail="Email already exists or DB error")
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

@app.get("/signals")
@app.get("/signals/vip")
def get_signals(email: str = "guest"):
    signals = []
    try:
        # Lấy dữ liệu từ MEXC
        res = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=5).json()
        for item in res:
            if item['symbol'] in COINS:
                price = float(item['lastPrice'])
                change = float(item['priceChangePercent'])
                
                # Logic phân loại Tab Forex (Vàng) hoặc Crypto
                is_gold = (item['symbol'] == "PAXGUSDT")
                pair_name = "XAUUSD (GOLD)" if is_gold else item['symbol']
                category = "FOREX" if is_gold else "CRYPTO"

                # Logic tạo tín hiệu ngẫu nhiên dựa trên biến động
                is_long = change < 0 # Giả lập bắt đáy
                entry = price
                
                if is_long:
                    sl = price * 0.985
                    tp_val = price * 1.04 # Chốt lời 4%
                    type_str = "LONG"
                else:
                    sl = price * 1.015
                    tp_val = price * 0.96 # Chốt lời 4%
                    type_str = "SHORT"

                signals.append({
                    "pair": pair_name,
                    "category": category,
                    "type": type_str,
                    "entry": round(entry, 4),
                    "sl": round(sl, 4),
                    "tp": round(tp_val, 4), # FIX LỖI TRÙNG ENTRY
                    "tp1": round(entry + (tp_val - entry) * 0.4, 4),
                    "tp2": round(tp_val, 4),
                    "confidence": random.randint(85, 98),
                    "timestamp": int(time.time()),
                    "status": "LIVE"
                })
        return signals
    except Exception as e:
        print(f"Signal Error: {e}")
        return []

@app.get("/activate-vip")
def activate_vip(email: str, days: int = 30):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT expire_date FROM users WHERE email=?", (email,))
        row = c.fetchone()
        base_date = datetime.now()
        if row and datetime.strptime(row[0], "%Y-%m-%d") > datetime.now():
            base_date = datetime.strptime(row[0], "%Y-%m-%d")
        
        new_expire = (base_date + timedelta(days=days)).strftime("%Y-%m-%d")
        c.execute("UPDATE users SET role='vip', expire_date=? WHERE email=?", (new_expire, email))
        conn.commit()
        
        label = "1 YEAR" if days >= 365 else "1 MONTH"
        msg = f"💎 VIP ACTIVATED\nUser: {email}\nDuration: {label}\nNew Expire: {new_expire}"
        send_tele_msg(msg)
        
        return {"status": "success", "new_expire": new_expire}
    except Exception as e:
        print(f"VIP Error: {e}")
        return {"status": "error"}
    finally:
        conn.close()

@app.get("/")
def home():
    return {
        "status": "PulseSignal Backend Online",
        "database": "Persistent",
        "features": ["Crypto", "Forex (Gold)", "Telegram Notifications"]
    }
