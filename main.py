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
    # Thêm IF NOT EXISTS để không lỗi khi khởi chạy lại
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, expire_date TEXT)''')
    conn.commit()
    conn.close()

init_db()

class UserAuth(BaseModel):
    email: str
    password: str

# --- 4. API ĐĂNG KÝ & ĐĂNG NHẬP (Sửa lỗi Hình 1) ---

@app.post("/register")
async def register(user: UserAuth):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        # Làm sạch email và password để tránh lỗi khoảng trắng
        clean_email = user.email.strip().lower()
        clean_pass = user.password.strip()
        
        expire = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (clean_email, clean_pass, 'free', expire))
        conn.commit()
        
        msg = f"🔔 USER MỚI: {clean_email}\n🎁 Dùng thử 3 ngày đến: {expire}"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
        
        return {"status": "success", "expire": expire}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Email đã tồn tại hoặc lỗi hệ thống")
    finally:
        conn.close()

@app.post("/login")
def login(user: UserAuth):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    # Kiểm tra với email viết thường và password sạch
    clean_email = user.email.strip().lower()
    clean_pass = user.password.strip()
    
    c.execute("SELECT email, role, expire_date FROM users WHERE email=? AND password=?", (clean_email, clean_pass))
    row = c.fetchone()
    conn.close()
    if row:
        return {"email": row[0], "role": row[1], "expire": row[2]}
    raise HTTPException(status_code=401, detail="Invalid login credentials")

# --- 5. API QUẢN TRỊ (Sửa lỗi Hình 2) ---

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
    
    # Cộng dồn ngày nếu đã là VIP
    c.execute("SELECT expire_date FROM users WHERE email=?", (email,))
    row = c.fetchone()
    
    base_date = datetime.now()
    if row and datetime.strptime(row[0], "%Y-%m-%d") > datetime.now():
        base_date = datetime.strptime(row[0], "%Y-%m-%d")
        
    new_expire = (base_date + timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("UPDATE users SET role='vip', expire_date=? WHERE email=?", (new_expire, email))
    conn.commit()
    conn.close()
    
    # Gửi Telegram
    msg = f"💎 VIP UPDATED\n📧 {email}\n📅 Hạn mới: {new_expire}\n⏱ +{days} ngày"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
    
    return {"status": "success", "new_expire": new_expire}

@app.get("/signals/vip")
@app.get("/signals")
def vip_signals(email: str = "guest"):
    # ... (Giữ nguyên phần logic tín hiệu như bản trước)
    return [{"pair": "BTCUSDT", "type": "LONG", "entry": 65000, "confidence": 92, "timestamp": int(time.time())}]

@app.get("/")
def home():
    return {"status": "PulseSignal Backend Ready"}
