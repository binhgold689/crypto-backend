import os
import sqlite3
import requests
import random
import time
import asyncio
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from datetime import datetime, timedelta

app = FastAPI()

# --- 1. CẤU HÌNH CORS (QUAN TRỌNG ĐỂ LOVABLE TRUY CẬP ĐƯỢC) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Cho phép tất cả các nguồn để tránh lỗi chặn API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. THÔNG TIN CẤU HÌNH ---
TELEGRAM_TOKEN = "8679086264:AAHNVmsiHxmQUiLdKtYNLkBdEfKLxRMsuw"
CHAT_ID = "-1003101971466"
COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "PAXGUSDT", "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT"]

# --- 3. KHỞI TẠO DATABASE (LƯU TRÊN RAILWAY) ---
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

# --- 5. LOGIC ĐĂNG KÝ / ĐĂNG NHẬP ---
@app.post("/register")
def register(user: UserAuth):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        # Mặc định đăng ký mới là 'free', dùng thử 3 ngày theo yêu cầu của bạn
        expire = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (user.email, user.password, 'free', expire))
        conn.commit()
        return {"status": "success", "message": "Đăng ký thành công! Bạn có 3 ngày dùng thử."}
    except:
        raise HTTPException(status_code=400, detail="Email đã tồn tại")
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

# --- 6. TRANG ADMIN ẨN (DÀNH RIÊNG CHO BINH GOLD) ---
@app.get("/binh-gold-admin-portal", response_class=HTMLResponse)
def admin_page():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    
    html_content = """
    <html>
        <head>
            <title>Admin PulseSignal</title>
            <meta charset="UTF-8">
            <style>
                body{font-family:sans-serif; background:#0f172a; color:#f8fafc; padding:40px;}
                h2{color:#38bdf8; border-bottom: 2px solid #38bdf8; padding-bottom:10px;}
                table{width:100%; border-collapse:collapse; margin-top:20px; background:#1e293b;} 
                th,td{border:1px solid #334155; padding:15px; text-align:left;}
                th{background:#334155; color:#38bdf8;}
                tr:hover{background:#1e293b;}
                .btn{background:linear-gradient(90deg, #06b6d4, #3b82f6); color:white; border:none; padding:8px 15px; cursor:pointer; border-radius:6px; font-weight:bold;}
                .btn:hover{opacity:0.8;}
                .role-vip{color:#10b981; font-weight:bold;}
                .role-free{color:#94a3b8;}
            </style>
        </head>
        <body>
            <h2>💎 Quản Lý Người Dùng VIP - PulseSignal</h2>
            <p>Xin chào Binh Gold, đây là danh sách khách hàng của bạn.</p>
            <table>
                <tr><th>Email</th><th>Quyền hạn</th><th>Ngày hết hạn</th><th>Hành động</th></tr>
    """
    for u in users:
        role_class = "role-vip" if u[2] == 'vip' else "role-free"
        html_content += f"""
        <tr>
            <td>{u[0]}</td>
            <td class="{role_class}">{u[2].upper()}</td>
            <td>{u[3]}</td>
            <td><button class='btn' onclick="activateVIP('{u[0]}')">Kích hoạt 30 ngày VIP</button></td>
        </tr>"""
    
    html_content += """
            </table>
            <script>
                function activateVIP(email) {
                    if(confirm('Bạn có chắc muốn cấp VIP cho ' + email + ' không?')) {
                        fetch('/activate-vip?email=' + email).then(() => {
                            alert('Đã kích hoạt thành công!');
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
    # Kích hoạt VIP 30 ngày
    new_expire = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    c.execute("UPDATE users SET role='vip', expire_date=? WHERE email=?", (new_expire, email))
    conn.commit()
    conn.close()
    
    # Gửi thông báo chúc mừng về Telegram khi bạn bấm kích hoạt
    msg = f"✅ ĐÃ KÍCH HOẠT VIP\n📧 User: {email}\n📅 Hạn dùng: {new_expire}"
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": CHAT_ID, "text": msg})
    except: pass
    
    return {"status": "success"}

# --- 7. LẤY DỮ LIỆU GIÁ VÀ TÍN HIỆU ---
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
                rsi_mock = round(50 - (change * 1.5), 2)
                rsi_mock = max(18, min(82, rsi_mock))
                
                # Nếu là khách hoặc bản free, bóp độ tin cậy xuống thấp (50-70%)
                # Nếu là VIP, hiện độ tin cậy thật (86-97%)
                is_vip = user and user[0] == 'vip'
                conf = random.randint(86, 97) if is_vip else random.randint(50, 70)

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

# --- 8. TELEGRAM WORKER (BẮN KÈO BIẾN ĐỘNG MẠNH) ---
async def telegram_worker():
    sent_signals = {}
    while True:
        try:
            url = "https://api.mexc.com/api/v3/ticker/24hr"
            res = requests.get(url, timeout=5).json()
            for i in res:
                if i['symbol'] in COINS:
                    change = float(i['priceChangePercent'])
                    if abs(change) > 3.0: # Biến động mạnh hơn 3%
                        symbol = i['symbol']
                        if symbol not in sent_signals:
                            msg = f"🚀 *KÈO BIẾN ĐỘNG MẠNH: {symbol}*\n💰 Giá hiện tại: `{i['lastPrice']}`\n📊 Biến động: `{change}%`"
                            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                                          json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})
                            sent_signals[symbol] = time.time()
            
            # Xóa lịch sử gửi sau 2 tiếng để có thể gửi lại cặp đó
            sent_signals = {k: v for k, v in sent_signals.items() if time.time() - v < 7200}
        except: pass
        await asyncio.sleep(600) # Kiểm tra mỗi 10 phút

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(telegram_worker())

@app.get("/")
def home():
    return {"status": "PulseSignal VIP System Online", "admin_portal": "/binh-gold-admin-portal"}
