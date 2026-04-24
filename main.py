import os
import sqlite3
import requests
import random
import time
import asyncio
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, timedelta

app = FastAPI()

# --- 1. CẤU HÌNH CORS (Cho phép tradezenith.live truy cập) ---
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

# --- 4. MODELS ---
class UserAuth(BaseModel):
    email: str
    password: str

# --- 5. LOGIC NGƯỜI DÙNG ---
@app.post("/register")
async def register(user: UserAuth):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("SELECT email FROM users WHERE email=?", (user.email,))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="Email đã tồn tại")
        
        # Mặc định dùng thử 7 ngày theo ảnh giao diện mới của bạn
        expire = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user.email, user.password, 'free', expire))
        conn.commit()
        
        msg = f"🔔 USER MỚI: {user.email}\n🎁 Tặng 7 ngày dùng thử đến: {expire}"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
        
        return {"status": "success", "message": "Đăng ký thành công! Bạn có 7 ngày dùng thử."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

@app.post("/login")
def login(user: UserAuth):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT email, role, expire_date FROM users WHERE email=? AND password=?", (user.email, user.password))
    row = c.fetchone()
    conn.close()
    if row:
        return {"email": row[0], "role": row[1], "expire": row[2]}
    raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")

# --- 6. TRANG ADMIN (Thêm nút cấp 1 tháng và 1 năm) ---
@app.get("/binh-gold-admin-portal", response_class=HTMLResponse)
def admin_page():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT email, role, expire_date FROM users")
    users = c.fetchall()
    conn.close()
    
    html_content = f"""
    <html>
        <head><title>Admin Binh Gold</title><meta charset="UTF-8">
        <style>
            body{{font-family:sans-serif; background:#0f172a; color:white; padding:40px;}}
            h2{{color:#38bdf8; border-bottom: 2px solid #38bdf8; padding-bottom:10px;}}
            table{{width:100%; border-collapse:collapse; margin-top:20px; background:#1e293b;}} 
            th,td{{border:1px solid #334155; padding:12px; text-align:left;}}
            th{{background:#334155; color:#38bdf8;}}
            .btn{{color:white; border:none; padding:8px 12px; cursor:pointer; border-radius:6px; font-weight:bold; margin-right:5px;}}
            .btn-30{{background:#3b82f6;}}
            .btn-365{{background:#f59e0b;}}
        </style>
        </head>
        <body>
            <h2>💎 Quản Lý User VIP - PulseSignal ({len(users)})</h2>
            <table>
                <tr><th>Email</th><th>Quyền</th><th>Hết hạn</th><th>Hành động</th></tr>
    """
    for u in users:
        html_content += f"""
        <tr>
            <td>{u[0]}</td><td>{u[1].upper()}</td><td>{u[2]}</td>
            <td>
                <button class='btn btn-30' onclick="activateVIP('{u[0]}', 30)">+30 Ngày</button>
                <button class='btn btn-365' onclick="activateVIP('{u[0]}', 365)">+1 Năm VIP</button>
            </td>
        </tr>"""
    
    html_content += """
            </table>
            <script>
                function activateVIP(email, days) {
                    if(confirm('Kích hoạt ' + days + ' ngày VIP cho ' + email + '?')) {
                        fetch('/activate-vip?email=' + email + '&days=' + days).then(() => {
                            alert('Thành công!');
                            location.reload();
                        });
                    }
                }
            </script>
        </body></html>"""
    return html_content

@app.get("/activate-vip")
def activate_vip(email: str, days: int = 30):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    new_expire = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    c.execute("UPDATE users SET role='vip', expire_date=? WHERE email=?", (new_expire, email))
    conn.commit()
    conn.close()
    
    label = "1 NĂM" if days == 365 else "30 NGÀY"
    msg = f"✅ ĐÃ KÍCH HOẠT VIP ({label})\n📧 User: {email}\n📅 Hết hạn: {new_expire}"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
    return {"status": "success"}

# --- 7. DỮ LIỆU TÍN HIỆU ---
@app.get("/prices")
def get_prices():
    try:
        res = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=5).json()
        return [{"symbol": "XAUUSD" if i['symbol']=="PAXGUSDT" else i['symbol'], "price": float(i['lastPrice'])} 
                for i in res if i['symbol'] in COINS]
    except: return []

@app.get("/signals/vip")
def vip_signals(email: str = "guest"):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()

    signals = []
    try:
        res = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=5).json()
        for item in res:
            if item['symbol'] in COINS:
                symbol = item['symbol']
                price = float(item['lastPrice'])
                change = float(item['priceChangePercent'])
                conf = random.randint(88, 98) if (user and user[0] == 'vip') else random.randint(50, 70)
                signals.append({
                    "pair": "XAUUSD" if symbol == "PAXGUSDT" else symbol,
                    "type": "LONG" if change < 0 else "SHORT",
                    "entry": price,
                    "confidence": conf,
                    "timestamp": int(time.time())
                })
    except: pass
    return signals

@app.get("/")
def home():
    return {"status": "PulseSignal Online", "admin": "/binh-gold-admin-portal"}
