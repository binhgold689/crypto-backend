import os
import sqlite3
import requests
import random
import time
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta

app = FastAPI()

# --- DATABASE ---
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/users.db")

# --- TELEGRAM CONFIG ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8679086264:AAHNVmsiHxmQUiLdKtYNLkBdEfKLxRMsuw")

# ID cá nhân của bạn — nhận thông báo đăng ký & VIP
ADMIN_CHAT_ID  = os.getenv("TELEGRAM_ADMIN_ID", "7388151158")

# Chat ID nhóm/kênh Telegram — nhận tín hiệu giao dịch (số âm, ví dụ: -1001234567890)
GROUP_CHAT_ID  = os.getenv("TELEGRAM_GROUP_ID", "")

COINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "LINKUSDT",
    "MATICUSDT", "NEARUSDT", "LTCUSDT", "ARBUSDT", "OPUSDT",
    "PAXGUSDT", "TIAUSDT", "SUIUSDT", "ORDIUSDT", "TRXUSDT"
]

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE INIT ---
def init_db():
    try:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        conn = sqlite3.connect(DATABASE_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (email TEXT PRIMARY KEY, password TEXT, role TEXT, expire_date TEXT)''')
        conn.commit()
        conn.close()
        print(f"✅ Database ready at {DATABASE_PATH}")
    except Exception as e:
        print(f"❌ Init DB Error: {e}")

init_db()

class UserAuth(BaseModel):
    email: str
    password: str

# --- TELEGRAM HELPERS ---
def _send(chat_id: str, text: str):
    """Gửi tin nhắn Telegram đến một chat_id cụ thể."""
    if not chat_id or not TELEGRAM_TOKEN:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=5)
        if not r.ok:
            print(f"Telegram send failed ({chat_id}): {r.text}")
    except Exception as e:
        print(f"Telegram Error ({chat_id}): {e}")

def notify_admin(text: str):
    """Gửi thông báo đến ID cá nhân của admin."""
    _send(ADMIN_CHAT_ID, text)

def notify_group(text: str):
    """Gửi tín hiệu đến nhóm Telegram."""
    _send(GROUP_CHAT_ID, text)

# --- SIGNAL GENERATION (tách ra để dùng lại) ---
def generate_signals():
    signals = []
    try:
        res = requests.get("https://api.mexc.com/api/v3/ticker/24hr", timeout=8).json()
        for item in res:
            if item['symbol'] not in COINS:
                continue
            price  = float(item['lastPrice'])
            change = float(item['priceChangePercent'])

            is_gold    = (item['symbol'] == "PAXGUSDT")
            pair_name  = "XAUUSD (GOLD)" if is_gold else item['symbol']
            category   = "FOREX" if is_gold else "CRYPTO"

            is_long = change < 0
            type_str = "LONG" if is_long else "SHORT"
            sl    = price * (0.985 if is_long else 1.015)
            tp2   = price * (1.04  if is_long else 0.96)
            tp1   = price + (tp2 - price) * 0.4

            signals.append({
                "pair":       pair_name,
                "category":   category,
                "type":       type_str,
                "entry":      round(price, 4),
                "sl":         round(sl,    4),
                "tp":         round(tp2,   4),
                "tp1":        round(tp1,   4),
                "tp2":        round(tp2,   4),
                "confidence": random.randint(85, 98),
                "timestamp":  int(time.time()),
                "status":     "LIVE"
            })
    except Exception as e:
        print(f"Signal Error: {e}")
    return signals

# --- BACKGROUND: GỬI TÍN HIỆU ĐẾN NHÓM MỖI 30 PHÚT ---
def signal_broadcaster():
    print("📡 Signal broadcaster started (every 30 min)")
    time.sleep(10)  # Chờ app khởi động xong
    while True:
        try:
            if GROUP_CHAT_ID:
                signals = generate_signals()
                top3 = signals[:3]
                for sig in top3:
                    icon = "📈" if sig['type'] == "LONG" else "📉"
                    msg = (
                        f"{icon} <b>TÍN HIỆU MỚI · {sig['pair']}</b>\n\n"
                        f"📊 Chiều: <b>{sig['type']}</b>\n"
                        f"💰 Entry: <b>${sig['entry']}</b>\n"
                        f"🎯 TP1: <b>${sig['tp1']}</b>\n"
                        f"🎯 TP2: <b>${sig['tp2']}</b>\n"
                        f"🛑 SL: <b>${sig['sl']}</b>\n"
                        f"⚡ Confidence: <b>{sig['confidence']}%</b>\n"
                        f"🏷 Category: <b>{sig['category']}</b>\n\n"
                        f"🔗 <a href='https://tradezenith.live/dashboard'>Xem Dashboard</a>"
                    )
                    notify_group(msg)
                    time.sleep(3)  # Tránh spam liên tiếp
                print(f"✅ Sent {len(top3)} signals to group at {datetime.now().strftime('%H:%M:%S')}")
            else:
                print("⚠️  GROUP_CHAT_ID chưa được cấu hình, bỏ qua broadcast")
        except Exception as e:
            print(f"Broadcaster Error: {e}")

        time.sleep(1800)  # 30 phút

# Khởi động background thread
threading.Thread(target=signal_broadcaster, daemon=True).start()

# --- ENDPOINTS ---

@app.post("/register")
async def register(user: UserAuth):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    try:
        email   = user.email.strip().lower()
        password = user.password.strip()
        expire  = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (email, password, 'free', expire))
        conn.commit()

        notify_admin(
            f"🔔 <b>USER MỚI ĐĂNG KÝ</b>\n\n"
            f"📧 Email: <code>{email}</code>\n"
            f"📅 Trial hết hạn: <b>{expire}</b>\n"
            f"⏰ Lúc: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
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
    email    = user.email.strip().lower()
    password = user.password.strip()
    c.execute("SELECT email, role, expire_date FROM users WHERE email=? AND password=?",
              (email, password))
    row = c.fetchone()
    conn.close()
    if row:
        return {"email": row[0], "role": row[1], "expire": row[2], "token": row[0], "status": "success"}
    raise HTTPException(status_code=401, detail="Invalid email or password")

@app.get("/signals")
@app.get("/signals/vip")
def get_signals(email: str = "guest"):
    return generate_signals()

@app.get("/activate-vip")
def activate_vip(email: str, days: int = 30):
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT expire_date FROM users WHERE email=?", (email,))
        row = c.fetchone()
        base_date = datetime.now()
        if row and row[0]:
            try:
                parsed = datetime.strptime(row[0], "%Y-%m-%d")
                if parsed > datetime.now():
                    base_date = parsed
            except ValueError:
                pass

        new_expire = (base_date + timedelta(days=days)).strftime("%Y-%m-%d")
        c.execute("UPDATE users SET role='vip', expire_date=? WHERE email=?", (new_expire, email))
        conn.commit()

        label = "1 NĂM" if days >= 365 else "1 THÁNG"
        notify_admin(
            f"💎 <b>VIP ĐÃ ĐƯỢC KÍCH HOẠT</b>\n\n"
            f"📧 Email: <code>{email}</code>\n"
            f"📦 Gói: <b>{label}</b>\n"
            f"📅 Hết hạn mới: <b>{new_expire}</b>\n"
            f"⏰ Lúc: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        return {"status": "success", "new_expire": new_expire}
    except Exception as e:
        print(f"VIP Error: {e}")
        return {"status": "error"}
    finally:
        conn.close()

@app.get("/admin/users-json")
def list_users():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT email, role, expire_date FROM users ORDER BY rowid DESC")
    rows = c.fetchall()
    conn.close()
    return [{"email": r[0], "role": r[1], "expire_date": r[2]} for r in rows]

@app.get("/broadcast")
def manual_broadcast():
    """Gửi tín hiệu thủ công đến nhóm ngay lập tức."""
    if not GROUP_CHAT_ID:
        return {"status": "error", "detail": "GROUP_CHAT_ID chưa được cấu hình"}
    signals = generate_signals()
    top3 = signals[:3]
    for sig in top3:
        icon = "📈" if sig['type'] == "LONG" else "📉"
        msg = (
            f"{icon} <b>TÍN HIỆU MỚI · {sig['pair']}</b>\n\n"
            f"📊 Chiều: <b>{sig['type']}</b>\n"
            f"💰 Entry: <b>${sig['entry']}</b>\n"
            f"🎯 TP1: <b>${sig['tp1']}</b>\n"
            f"🎯 TP2: <b>${sig['tp2']}</b>\n"
            f"🛑 SL: <b>${sig['sl']}</b>\n"
            f"⚡ Confidence: <b>{sig['confidence']}%</b>\n\n"
            f"🔗 <a href='https://tradezenith.live/dashboard'>Xem Dashboard</a>"
        )
        notify_group(msg)
        time.sleep(2)
    return {"status": "ok", "sent": len(top3)}

@app.get("/")
def home():
    return {
        "status": "PulseSignal Backend Online",
        "database": "Persistent",
        "group_configured": bool(GROUP_CHAT_ID),
        "features": ["Crypto", "Forex (Gold)", "Telegram Notifications"]
    }
