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

# --- 2. THÔNG TIN CẤU HÌNH ---
TELEGRAM_TOKEN = "8679086264:AAHNVmsiHxmQUiLdKtYNLkBdEfKLxRMsuw"
CHAT_ID = "-1003101971466"
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "PAXGUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT"]

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

# --- 4. API ĐĂNG KÝ & ĐĂNG NHẬP (Fix lỗi Hình 1) ---

@app.post("/register")
async def register(user: UserAuth):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        expire = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        # Lưu mật khẩu dạng text thuần để khớp 100% với login
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user.email.strip(), user.password.strip(), 'free', expire))
        conn.commit()
        
        # Gửi Telegram thông báo có User mới
        msg = f"🔔 USER MỚI: {user.email}\n🎁 Dùng thử 3 ngày đến: {expire}"
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
    # Dùng strip() để tránh lỗi thừa dấu cách khi copy-paste (Hình 1)
    c.execute("SELECT email, role, expire_date FROM users WHERE email=? AND password=?", (user.email.strip(), user.password.strip()))
    row = c.fetchone()
    conn.close()
    if row:
        return {"email": row[0], "role": row[1], "expire": row[2]}
    raise HTTPException(status_code=401, detail="Invalid login credentials")

# --- 5. API QUẢN TRỊ & KÍCH HOẠT VIP (Fix lỗi Hình 2 & 3) ---

@app.get("/binh-gold-admin-portal")
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
    # Cộng dồn ngày hết hạn
    c.execute("SELECT expire_date FROM users WHERE email=?", (email,))
    current_expire = c.fetchone()
    
    start_date = datetime.now()
    if current_expire and datetime.strptime(current_expire[0], "%Y-%m-%d") > datetime.now():
        start_date = datetime.strptime(current_expire[0], "%Y-%m-%d")
        
    new_expire = (start_date + timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("UPDATE users SET role='vip', expire_date=? WHERE email=?", (new_expire, email))
    conn.commit()
    conn.close()
    
    # Gửi Telegram thông báo kích hoạt thành công (Hình 3)
    msg = f"💎 KÍCH HOẠT VIP THÀNH CÔNG\n📧 Email: {email}\n📅 Hạn mới: {new_expire}\n⏱ Gói: {days} ngày"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
    
    return {"status": "success", "new_expire": new_expire}

# --- 6. DỮ LIỆU GIÁ & TÍN HIỆU ---

@app.get("/prices")
def get_prices():
    try:
        res = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=5).json()
        return [{"symbol": "XAUUSD" if i['symbol']=="PAXGUSDT" else i['symbol'], "price": float(i['lastPrice'])} 
                for i in res if i['symbol'] in COINS]
    except: return []

@app.get("/")
def home():
    return {"status": "Backend PulseSignal Online"}
