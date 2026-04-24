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

# --- 1. CẤU HÌNH CORS (Sửa lỗi không nhận được dữ liệu từ Lovable/Domain) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Mở rộng để đảm bảo tradezenith.live và các sub-domain Lovable không bị chặn
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

# --- 5. LOGIC NGƯỜI DÙNG (Register/Login) ---
@app.post("/register")
async def register(user: UserAuth):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        # Kiểm tra email tồn tại
        c.execute("SELECT email FROM users WHERE email=?", (user.email,))
        if c.fetchone():
            raise HTTPException(status_code=400, detail="Email đã tồn tại")
        
        # Mặc định đăng ký mới là 'free', dùng thử 3 ngày
        expire = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user.email, user.password, 'free', expire))
        conn.commit()
        
        # Gửi thông báo Telegram
        msg = f"🔔 CÓ USER MỚI: {user.email}\n🎁 Tặng 3 ngày dùng thử đến: {expire}"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
        
        return {"status": "success", "message": "Đăng ký thành công! Bạn có 3 ngày dùng thử."}
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

# --- 6. TRANG ADMIN PORTAL (Quản lý User & Kích hoạt VIP) ---
@app.get("/binh-gold-admin-portal", response_class=HTMLResponse)
def admin_page():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
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
            .btn{{background:linear-gradient(90deg, #06b6d4, #3b82f6); color:white; border:none; padding:8px 15px; cursor:pointer; border-radius:6px; font-weight:bold;}}
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
            <td>{u[0]}</td><td>{u[2].upper()}</td><td>{u[3]}</td>
            <td><button class='btn' onclick="activateVIP('{u[0]}')">Kích hoạt 30 ngày VIP</button></td>
        </tr>"""
    
    html_content += """
            </table>
            <script>
                function activateVIP(email) {
                    if(confirm('Kích hoạt VIP cho ' + email + '?')) {
                        fetch('/activate-vip?email=' + email).then(() => {
                            alert('Thành công!');
                            location.reload();
                        });
                    }
                }
            </script>
        </body></html>"""
    return html_content

@app.get("/activate-vip")
def activate_vip(email: str):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    new_expire = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    c.execute("UPDATE users SET role='vip', expire_date=? WHERE email=?", (new_expire, email))
    conn.commit()
    conn.close()
    
    msg = f"✅ ĐÃ KÍCH HOẠT VIP\n📧 User: {email}\n📅 Hết hạn: {new_expire}"
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
    return {"status": "success"}

# --- 7. DỮ LIỆU TÍN HIỆU & GIÁ (MEXC API) ---
@app.get("/prices")
def get_prices():
    try:
        url = "https://api.mexc.com/api/v3/ticker/24hr"
        res = requests.get(url, timeout=5).json()
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
        url = "https://api.mexc.com/api/v3/ticker/24hr"
        res = requests.get(url, timeout=5).json()
        for item in res:
            if item['symbol'] in COINS:
                symbol = item['symbol']
                price = float(item['lastPrice'])
                change = float(item['priceChangePercent'])
                side = "LONG" if change < 0 else "SHORT"
                rsi_mock = max(18, min(82, round(50 - (change * 1.5), 2)))
                conf = random.randint(86, 97) if (user and user[0] == 'vip') else random.randint(50, 70)

                signals.append({
                    "pair": "XAUUSD" if symbol == "PAXGUSDT" else symbol,
                    "type": side, "entry": price,
                    "sl": round(price * 0.982, 4) if side == "LONG" else round(price * 1.018, 4),
                    "tp": round(price * 1.05, 4) if side == "LONG" else round(price * 0.95, 4),
                    "confidence": conf, "rsi": rsi_mock, "timestamp": int(time.time())
                })
    except: pass
    signals.sort(key=lambda x: x["confidence"], reverse=True)
    return signals

# --- 8. TELEGRAM WORKER ---
async def telegram_worker():
    sent_signals = {}
    while True:
        try:
            url = "https://api.mexc.com/api/v3/ticker/24hr"
            res = requests.get(url, timeout=5).json()
            for i in res:
                if i['symbol'] in COINS and abs(float(i['priceChangePercent'])) > 3:
                    symbol = i['symbol']
                    if symbol not in sent_signals or time.time() - sent_signals[symbol] > 7200:
                        msg = f"🚀 *BIẾN ĐỘNG MẠNH: {symbol}*\nGiá: `{i['lastPrice']}`\nThay đổi: `{i['priceChangePercent']}%`"
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                                      json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
                        sent_signals[symbol] = time.time()
        except: pass
        await asyncio.sleep(600)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(telegram_worker())

@app.get("/")
def home():
    return {"status": "PulseSignal System Online", "admin": "/binh-gold-admin-portal"}
