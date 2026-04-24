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

# --- 2. CẤU HÌNH HỆ THỐNG & DANH SÁCH COIN ĐẦY ĐỦ ---
TELEGRAM_TOKEN = "8679086264:AAHNVmsiHxmQUiLdKtYNLkBdEfKLxRMsuw"
CHAT_ID = "-1003101971466" 

# Danh sách 20 đồng coin bạn yêu cầu (đã thêm PAXG để làm Gold)
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

# --- 4. API NGƯỜI DÙNG (Fix lỗi xác thực & khoảng trắng) ---

@app.post("/register")
async def register(user: UserAuth):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        clean_email = user.email.strip().lower()
        clean_pass = user.password.strip()
        expire = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (clean_email, clean_pass, 'free', expire))
        conn.commit()
        
        msg = f"🔔 USER MỚI: {clean_email}\n🎁 Tặng 3 ngày dùng thử đến: {expire}"
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
    clean_email = user.email.strip().lower()
    clean_pass = user.password.strip()
    
    c.execute("SELECT email, role, expire_date FROM users WHERE email=? AND password=?", (clean_email, clean_pass))
    row = c.fetchone()
    conn.close()
    
    if row:
        return {"email": row[0], "role": row[1], "expire": row[2]}
    raise HTTPException(status_code=401, detail="Invalid login credentials")

# --- 5. API ADMIN (Gói 30 ngày và 365 ngày) ---

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
    
    c.execute("SELECT expire_date FROM users WHERE email=?", (email,))
    row = c.fetchone()
    
    base_date = datetime.now()
    if row and datetime.strptime(row[0], "%Y-%m-%d") > datetime.now():
        base_date = datetime.strptime(row[0], "%Y-%m-%d")
        
    new_expire = (base_date + timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("UPDATE users SET role='vip', expire_date=? WHERE email=?", (new_expire, email))
    conn.commit()
    conn.close()
    
    label = "1 NĂM" if days >= 365 else f"{days} NGÀY"
    msg = f"💎 VIP UPDATED ({label})\n📧 {email}\n📅 Hết hạn: {new_expire}"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
    return {"status": "success", "new_expire": new_expire}

# --- 6. API DỮ LIỆU TÍN HIỆU & GIÁ REALTIME (Đã bù phần thiếu) ---

@app.get("/prices")
def get_prices():
    try:
        res = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=5).json()
        data = []
        for i in res:
            if i['symbol'] in COINS:
                # Đổi tên PAXG thành XAUUSD cho người dùng dễ hiểu
                symbol = "XAUUSD" if i['symbol'] == "PAXGUSDT" else i['symbol']
                data.append({"symbol": symbol, "price": float(i['lastPrice'])})
        return data
    except:
        return []

@app.get("/signals/vip")
@app.get("/signals")
def vip_signals(email: str = "guest"):
    # Kiểm tra quyền VIP từ database
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE email=?", (email.strip().lower(),))
    user = c.fetchone()
    conn.close()

    signals = []
    try:
        res = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=5).json()
        for item in res:
            if item['symbol'] in COINS:
                # VIP: độ tin cậy 88-98%, Free: 50-70%
                conf = random.randint(88, 98) if (user and user[0] == 'vip') else random.randint(50, 70)
                
                # Logic đơn giản: giá giảm -> LONG, giá tăng -> SHORT
                change = float(item['priceChangePercent'])
                signals.append({
                    "pair": "XAUUSD" if item['symbol'] == "PAXGUSDT" else item['symbol'],
                    "type": "LONG" if change < 0 else "SHORT",
                    "entry": float(item['lastPrice']),
                    "confidence": conf,
                    "timestamp": int(time.time())
                })
    except:
        pass
    return signals

@app.get("/")
def home():
    return {"status": "PulseSignal Backend is Online", "coins_tracked": len(COINS)}
