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

# --- 1. CẤU HÌNH CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. THÔNG TIN CẤU HÌNH (Đã gắn ID của bạn) ---
TELEGRAM_TOKEN = "8679086264:AAHNVmsiHxmQUiLdKtYNLkBdEfKLxRMsuw"
CHAT_ID = "7388151158" 

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", 
    "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT",
    "MATICUSDT", "NEARUSDT", "LTCUSDT", "ARBUSDT", "OPUSDT",
    "PAXGUSDT", "TIAUSDT", "SUIUSDT", "ORDIUSDT", "TRXUSDT"
]

# --- 3. KHỞI TẠO DATABASE ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, expire_date TEXT)''')
    conn.commit()
    conn.close()

init_db()

class UserAuth(BaseModel):
    email: str
    password: str

# --- 4. API NGƯỜI DÙNG (Fix lỗi Login & Đăng ký) ---

@app.post("/register")
async def register(user: UserAuth):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        email = user.email.strip().lower()
        password = user.password.strip()
        expire = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (email, password, 'free', expire))
        conn.commit()
        
        # Báo về Telegram cá nhân của bạn
        msg = f"🔔 USER MỚI ĐĂNG KÝ\n📧 Email: {email}\n🎁 Hạn dùng thử: {expire}"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
        
        return {"status": "success", "expire": expire}
    except:
        raise HTTPException(status_code=400, detail="Email đã tồn tại")
    finally:
        conn.close()

@app.post("/login")
def login(user: UserAuth):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    email = user.email.strip().lower()
    password = user.password.strip()
    
    c.execute("SELECT email, role, expire_date FROM users WHERE email=? AND password=?", (email, password))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {"email": row[0], "role": row[1], "expire": row[2], "status": "success"}
    raise HTTPException(status_code=401, detail="Invalid email or password")

# --- 5. API ADMIN (Kích hoạt VIP 1 tháng & 1 năm) ---

@app.get("/binh-gold-admin-portal")
@app.get("/admin/users-json")
def get_users_admin():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT email, role, expire_date FROM users")
    rows = c.fetchall()
    conn.close()
    return [{"email": r[0], "role": r[1], "expire_date": r[2]} for r in rows]

@app.get("/activate-vip")
def activate_vip(email: str, days: int = 30):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # Tính ngày hết hạn mới (cộng dồn nếu đang VIP)
    c.execute("SELECT expire_date FROM users WHERE email=?", (email,))
    row = c.fetchone()
    base_date = datetime.now()
    if row and datetime.strptime(row[0], "%Y-%m-%d") > datetime.now():
        base_date = datetime.strptime(row[0], "%Y-%m-%d")
        
    new_expire = (base_date + timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("UPDATE users SET role='vip', expire_date=? WHERE email=?", (new_expire, email))
    conn.commit()
    conn.close()
    
    # Báo về Telegram cá nhân
    label = "1 NĂM" if days >= 365 else "1 THÁNG"
    msg = f"💎 KÍCH HOẠT VIP THÀNH CÔNG ({label})\n📧 User: {email}\n📅 Hạn mới: {new_expire}"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
    
    return {"status": "success", "new_expire": new_expire}

# --- 6. API GIÁ & TÍN HIỆU ---

@app.get("/prices")
def get_prices():
    try:
        res = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=5).json()
        return [{"symbol": "XAUUSD" if i['symbol']=="PAXGUSDT" else i['symbol'], "price": float(i['lastPrice'])} 
                for i in res if i['symbol'] in COINS]
    except: return []

@app.get("/signals")
def get_signals(email: str = "guest"):
    # Logic tạo tín hiệu dựa trên data thật
    signals = []
    try:
        res = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=5).json()
        for item in res:
            if item['symbol'] in COINS:
                signals.append({
                    "pair": "XAUUSD" if item['symbol'] == "PAXGUSDT" else item['symbol'],
                    "type": "LONG" if float(item['priceChangePercent']) < 0 else "SHORT",
                    "entry": float(item['lastPrice']),
                    "confidence": random.randint(85, 98),
                    "timestamp": int(time.time())
                })
    except: pass
    return signals

@app.get("/")
def home():
    return {"status": "PulseSignal Backend Online", "linked_id": "7388151158"}
