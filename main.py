from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
import random
import time
import asyncio
import sqlite3
from datetime import datetime, timedelta

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CẤU HÌNH ---
TELEGRAM_TOKEN = "8679086264:AAHNVmsiHxmQUiLdKtYNLkBdEfKLxRMsuw"
CHAT_ID = "-1003101971466"
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "PAXGUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT"]

# --- KHỞI TẠO DATABASE ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (email TEXT PRIMARY KEY, password TEXT, role TEXT, expire_date TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- MODELS ---
class UserAuth(BaseModel):
    email: str
    password: str

# --- LOGIC NGƯỜI DÙNG ---
@app.post("/register")
def register(user: UserAuth):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        # Mặc định đăng ký mới là 'free', dùng thử 7 ngày
        expire = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user.email, user.password, 'free', expire))
        conn.commit()
        return {"message": "Đăng ký thành công! Bạn có 7 ngày dùng thử."}
    except:
        raise HTTPException(status_code=400, detail="Email đã tồn tại")
    finally: conn.close()

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

# --- TRANG ADMIN ẨN (DÀNH RIÊNG CHO BINH GOLD) ---
@app.get("/binh-gold-admin-portal", response_class=HTMLResponse)
def admin_page():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    
    html_content = """
    <html>
        <head><title>Admin Binh Gold</title><meta charset="UTF-8">
        <style>body{font-family:sans-serif; background:#121212; color:white; padding:20px;}
        table{width:100%; border-collapse:collapse;} th,td{border:1px solid #333; padding:10px; text-align:left;}
        th{background:#1f1f1f;} .btn{background:#e91e63; color:white; border:none; padding:5px 10px; cursor:pointer; border-radius:3px;}</style>
        </head>
        <body>
            <h2>Quản Lý User VIP - PulseSignal</h2>
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
                    fetch('/activate-vip?email=' + email).then(() => location.reload());
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
    return {"status": "success"}

# --- LẤY DỮ LIỆU TÍN HIỆU (VẪN GIỮ LOGIC CHỐNG CHẶN) ---
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
    # Kiểm tra quyền VIP (Chỉ VIP mới thấy kèo chuẩn)
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
                rsi_mock = round(50 - (change * 1.5), 2)
                rsi_mock = max(18, min(82, rsi_mock))
                
                # Nếu là khách hoặc bản free, bóp độ tin cậy xuống thấp để kích thích mua VIP
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

# --- TELEGRAM WORKER ---
async def telegram_worker():
    sent_signals = {}
    while True:
        try:
            # Bot chỉ bắn kèo từ sàn (không cần check user)
            url = "https://api.mexc.com/api/v3/ticker/24hr"
            res = requests.get(url, timeout=5).json()
            for i in res:
                if i['symbol'] in COINS and abs(float(i['priceChangePercent'])) > 3: # Biến động > 3%
                    symbol = i['symbol']
                    if symbol not in sent_signals:
                        msg = f"🚀 *KÈO BIẾN ĐỘNG MẠNH: {symbol}*\nGiá: `{i['lastPrice']}`\nBiến động: `{i['priceChangePercent']}%`"
                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                                      json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
                        sent_signals[symbol] = time.time()
            sent_signals = {k: v for k, v in sent_signals.items() if time.time() - v < 7200}
        except: pass
        await asyncio.sleep(600)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(telegram_worker())

@app.get("/")
def home():
    return {"status": "PulseSignal Auth System Online"}
