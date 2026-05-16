import os
import random
import sqlite3
import time
import logging
import asyncio
import json
import secrets
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from threading import Lock

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, PreCheckoutQueryHandler,
    ContextTypes
)

# ───────────────────────────────────────────────────
# ЛОГИРОВАНИЕ
# ───────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────
# КОНФИГУРАЦИЯ
# ───────────────────────────────────────────────────
TOKEN = "8682746743:AAG0aFUE3meEvV6yb7Qql29TmkxZWO-nv3Y"
OWNER_ID = 5194912200
IMAGES_DIR = "animals"

CARD_COOLDOWN_HOURS = 2
CASINO_DICE_PRICE = 0
CASINO_BET_COOLDOWN = 3
MIN_BET = 50
MAX_BET_BALLS = 5000
BET_GOLD_MULTIPLIER = 5
BET_BLACK_WHITE_MULTIPLIER = 1.8
MAX_SINGLE_WIN = 10000
CASE_PRICE = 225
CASE_VIP_PRICE = 200
PRIME_CASE_PRICE = 1

# ───────────────────────────────────────────────────
# ЛОТЕРЕЯ
# ───────────────────────────────────────────────────
LOTTERIES = {}

# ───────────────────────────────────────────────────
# ШАНСЫ ДЛЯ DICE
# ───────────────────────────────────────────────────
DICE_WINS = {1: 250, 2: 150, 3: 75, 4: -75, 5: -125, 6: -200}
DICE_MIN_BALANCE = 250

# ───────────────────────────────────────────────────
# РЕДКОСТИ И ШАНСЫ
# ───────────────────────────────────────────────────
RARITIES = {
    "Редкая": {"price": 25, "chance": 40, "emoji": "🟢", "label": "🟢 Редкая"},
    "Эпическая": {"price": 50, "chance": 30, "emoji": "🟣", "label": "🟣 Эпическая"},
    "Мифическая": {"price": 100, "chance": 15, "emoji": "🔴", "label": "🔴 Мифическая"},
    "Легендарная": {"price": 300, "chance": 10, "emoji": "🟡", "label": "🟡 Легендарная"},
    "Ультралегендарная": {"price": 600, "chance": 4, "emoji": "💎", "label": "💎 Ультралегендарная"},
    "Кроссовская": {"price": 1500, "chance": 1, "emoji": "⚫", "label": "⚫ Кроссовская"},
}

VIP_RARITIES = {
    "Редкая": {"price": 25, "chance": 35, "emoji": "🟢", "label": "🟢 Редкая"},
    "Эпическая": {"price": 50, "chance": 25, "emoji": "🟣", "label": "🟣 Эпическая"},
    "Мифическая": {"price": 100, "chance": 15, "emoji": "🔴", "label": "🔴 Мифическая"},
    "Легендарная": {"price": 300, "chance": 15, "emoji": "🟡", "label": "🟡 Легендарная"},
    "Ультралегендарная": {"price": 600, "chance": 7, "emoji": "💎", "label": "💎 Ультралегендарная"},
    "Кроссовская": {"price": 1500, "chance": 3, "emoji": "⚫", "label": "⚫ Кроссовская"},
}

PRIME_CASE_DROPS = [
    ("200 монет", "coins", 200, 30),
    ("400 монет", "coins", 400, 25),
    ("600 монет", "coins", 600, 15),
    ("VIP на 2 дня", "vip", 2, 10),
    ("VIP на 7 дней", "vip", 7, 8),
    ("VIP на 10 дней", "vip", 10, 6),
    ("VIP на 20 дней", "vip", 20, 3),
    ("1500 монет", "coins", 1500, 2),
    ("3000 монет", "coins", 3000, 1),
]

CASE_POOL = [
    ("Барсодьяк \"Свин\"", "Редкая", 25, 45.0),
    ("Барсосвинопард \"Свин\"", "Редкая", 25, 45.0),
    ("БарсоСвинОлень с тату \"Свин\"", "Редкая", 25, 45.0),
    ("БарсоСамурай \"Свин\"", "Эпическая", 50, 25.0),
    ("БарсоБармен \"Свин\"", "Эпическая", 50, 25.0),
    ("БарсоЗолото \"Свин\"", "Легендарная", 300, 16.0),
    ("МультиБарс \"Свин\"", "Ультралегендарная", 600, 12.5),
    ("БарсоЛепрекон \"Свин\"", "Кроссовская", 1500, 1.5),
]
CASE_POOL_WEIGHTS = [45.0, 45.0, 45.0, 25.0, 25.0, 16.0, 12.5, 1.5]

CASE_IMAGES = {
    "Барсодьяк \"Свин\"": "barsodyak.jpg",
    "Барсосвинопард \"Свин\"": "barsosvinopard.jpg",
    "БарсоСвинОлень с тату \"Свин\"": "barsosvinolen.jpg",
    "БарсоСамурай \"Свин\"": "barsosamurai.jpg",
    "БарсоБармен \"Свин\"": "barsosvinbarmen.jpg",
    "БарсоЗолото \"Свин\"": "barsozoloto.jpg",
    "МультиБарс \"Свин\"": "multibars.jpg",
    "БарсоЛепрекон \"Свин\"": "basroleprekon.mp4",
}

RARITY_EMOJI = {
    "Редкая": "🟢", "Эпическая": "🟣", "Мифическая": "🔴",
    "Легендарная": "🟡", "Ультралегендарная": "💎", "Кроссовская": "⚫",
}

REGULAR_CARDS = [
    ("Грустный Барсопад", "Редкая", 25, "squirrel.jpg"),
    ("Весёлый Барсопад", "Редкая", 25, "fox.jpg"),
    ("Барсопад Лимерт", "Редкая", 25, "raccoon.jpg"),
    ("Барсопад и Хомокот", "Редкая", 25, "cat.jpg"),
    ("Барсопад с бананом", "Эпическая", 50, "wolf.jpg"),
    ("Барсопад пок", "Эпическая", 50, "panda.jpg"),
    ("Барсопад пр", "Эпическая", 50, "deer.jpg"),
    ("Удивленный Барсопад", "Эпическая", 50, "owl.jpg"),
    ("Барсопад с сердцем", "Эпическая", 50, "basilisk.jpg"),
    ("Барсопад с лайком", "Эпическая", 50, "griffin.jpg"),
    ("Барсопад Иглобрюх", "Мифическая", 100, "dragon.jpg"),
    ("Барсопад на Вилле", "Мифическая", 100, "phoenix.jpg"),
    ("Барсопад Шейх", "Мифическая", 100, "chimera.png"),
    ("Барсопад с рыбой", "Мифическая", 100, "manticore.jpg"),
    ("Барсопад Уборщик", "Легендарная", 300, "leviatan_ultra.jpg"),
    ("Барсопад в Офисе", "Легендарная", 300, "unicorn.jpg"),
    ("Барсопад на работе", "Легендарная", 300, "typhon.jpg"),
    ("Барсопад в Ресторане", "Ультралегендарная", 600, "cerberus.jpg"),
    ("Барсопад депает", "Ультралегендарная", 600, "pegasus.jpg"),
    ("Барсопад на Самолете", "Ультралегендарная", 600, "kraken.jpg"),
    ("Барспопад Геймер", "Ультралегендарная", 600, "golden_phoenix.jpg"),
    ("Куки", "Кроссовская", 1500, "softlight.png"),
    ("Леопард", "Редкая", 25, "leo1.jpg"),
    ("Флаг леопардов", "Редкая", 25, "leo2.jpg"),
    ("Демон", "Эпическая", 50, "leo3.jpg"),
    ("Леопард с маской", "Редкая", 25, "leo4.jpg"),
    ("Новогодний леопард", "Эпическая", 50, "leo5.jpg"),
    ("Новогодняя такса", "Эпическая", 50, "leo6.jpg"),
    ("Леопард пират", "Мифическая", 100, "leo7.jpg"),
    ("Леопард с сердцем", "Эпическая", 50, "leo8.jpg"),
    ("Злой леопард", "Эпическая", 50, "leo9.jpg"),
    ("Леопард с короной", "Легендарная", 300, "leo10.jpg"),
    ("Леопард в болоте с животными", "Ультралегендарная", 600, "leo11.jpg"),
    ("Леопард с Русским медведем", "Ультралегендарная", 600, "leo12.jpg"),
    ("Леопард на математике", "Мифическая", 100, "leo13.jpg"),
    ("Леопард ругается у доски", "Эпическая", 50, "leo14.jpg"),
    ("Леопард леон", "Легендарная", 300, "leo15.jpg"),
    ("Леопард около дворца", "Эпическая", 50, "leo16.jpg"),
    ("Истрибитель свинок", "Легендарная", 300, "leo17.jpg"),
    ("Леорыба", "Ультралегендарная", 600, "leo18.jpg"),
    ("Леопард в горах", "Легендарная", 300, "leo19.jpg"),
    ("Леопард анонимус", "Ультралегендарная", 600, "leo20.jpg"),
    ("Леопард краш", "Легендарная", 300, "leo21.jpg"),
    ("Леопард девушка", "Редкая", 25, "leo22.jpg"),
    ("Леопард в ванне", "Мифическая", 100, "leo23.jpg"),
    ("свинопард с леденцом", "Кроссовская", 1500, "leo24.jpg"),
    ("свинопард", "Эпическая", 50, "leo25.jpg"),
    ("свинопард на летучем корабле", "Редкая", 25, "leo26.jpg"),
    ("свинопард пират", "Мифическая", 100, "leo27.jpg"),
    ("свинопард в банке", "Редкая", 25, "leo28.jpg"),
    ("свинопард в телеке", "Эпическая", 50, "leo29.jpg"),
    ("леопард в банке", "Редкая", 25, "leo30.jpg"),
    ("леопард с бицепсом", "Легендарная", 300, "leo31.jpg"),
    ("форфор", "Ультралегендарная", 600, "leo32.jpg"),
    ("леопарсд с арбузом", "Редкая", 25, "leo33.jpg"),
    ("свинопард в баре", "Эпическая", 50, "leo34.jpg"),
]

# ───────────────────────────────────────────────────
# БАЗА ДАННЫХ
# ───────────────────────────────────────────────────
class Database:
    def __init__(self, path: str = "animal_cards.db") -> None:
        self.path = path
        self._lock = Lock()

    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=20, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-2000")
        return conn

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(sql, params)
                conn.commit()
                return cur.rowcount
            finally:
                conn.close()

    def one(self, sql: str, params: tuple = ()) -> Optional[dict]:
        with self._lock:
            conn = self._conn()
            try:
                row = conn.execute(sql, params).fetchone()
                return dict(row) if row else None
            finally:
                conn.close()

    def all(self, sql: str, params: tuple = ()) -> List[dict]:
        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute(sql, params).fetchall()
                return [dict(r) for r in rows]
            finally:
                conn.close()

    def transfer_coins(self, user_id: int, delta: int) -> bool:
        with self._lock:
            conn = self._conn()
            try:
                if delta >= 0:
                    conn.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (delta, user_id))
                else:
                    cur = conn.execute("UPDATE users SET coins=coins+? WHERE user_id=? AND coins+?>=0", (delta, user_id, delta))
                    if cur.rowcount == 0:
                        return False
                conn.commit()
                return True
            finally:
                conn.close()

    def get_all_users(self) -> List[dict]:
        return self.all("SELECT user_id FROM users")

db = Database()

# ───────────────────────────────────────────────────
# ИНИЦИАЛИЗАЦИЯ
# ───────────────────────────────────────────────────
def init_db() -> None:
    stmts = [
        """CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, coins INTEGER DEFAULT 0,
            last_card_time REAL DEFAULT 0, vip INTEGER DEFAULT 0, vip_until INTEGER DEFAULT 0,
            last_daily INTEGER DEFAULT 0, tasks_date TEXT DEFAULT '', cards_opened INTEGER DEFAULT 0,
            legendaries_earned INTEGER DEFAULT 0, cases_opened INTEGER DEFAULT 0,
            ultra_cases_opened INTEGER DEFAULT 0, epic_streak INTEGER DEFAULT 0,
            tasks_claimed TEXT DEFAULT '00000'
        )""",
        """CREATE TABLE IF NOT EXISTS cards (
            card_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
            rarity TEXT, base_price INTEGER, image_file TEXT, is_case INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS user_cards (
            user_id INTEGER, card_id INTEGER, quantity INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, card_id)
        )""",
        """CREATE TABLE IF NOT EXISTS user_collection (
            user_id INTEGER, card_id INTEGER, PRIMARY KEY (user_id, card_id)
        )""",
        """CREATE TABLE IF NOT EXISTS cooldowns (
            user_id INTEGER, key TEXT, timestamp REAL, PRIMARY KEY (user_id, key)
        )""",
        """CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)""",
        """CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY, reason TEXT, banned_at INTEGER
        )""",
        "CREATE INDEX IF NOT EXISTS idx_uc_user ON user_cards(user_id)",
    ]
    for s in stmts:
        db.execute(s)

    try:
        db.execute("ALTER TABLE cards ADD COLUMN is_case INTEGER DEFAULT 0")
    except:
        pass

    for name, rarity, price, img in REGULAR_CARDS:
        db.execute("INSERT OR IGNORE INTO cards (name, rarity, base_price, image_file, is_case) VALUES (?,?,?,?,0)", (name, rarity, price, img))
    
    case_cards = [
        ("Барсодьяк \"Свин\"", "Редкая", 25, "barsodyak.jpg"),
        ("Барсосвинопард \"Свин\"", "Редкая", 25, "barsosvinopard.jpg"),
        ("БарсоСвинОлень с тату \"Свин\"", "Редкая", 25, "barsosvinolen.jpg"),
        ("БарсоСамурай \"Свин\"", "Эпическая", 50, "barsosamurai.jpg"),
        ("БарсоБармен \"Свин\"", "Эпическая", 50, "barsosvinbarmen.jpg"),
        ("БарсоЗолото \"Свин\"", "Легендарная", 300, "barsozoloto.jpg"),
        ("МультиБарс \"Свин\"", "Ультралегендарная", 600, "multibars.jpg"),
        ("БарсоЛепрекон \"Свин\"", "Кроссовская", 1500, "basroleprekon.mp4"),
    ]
    for name, rarity, price, img in case_cards:
        db.execute("INSERT OR IGNORE INTO cards (name, rarity, base_price, image_file, is_case) VALUES (?,?,?,?,1)", (name, rarity, price, img))
    
    logger.info("✅ База данных готова")

# ───────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ───────────────────────────────────────────────────
def is_banned(user_id: int) -> bool:
    return db.one("SELECT 1 FROM banned_users WHERE user_id=?", (user_id,)) is not None

def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    return db.one("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) is not None

def is_vip(user_id: int) -> bool:
    r = db.one("SELECT vip, vip_until FROM users WHERE user_id=?", (user_id,))
    return bool(r and r["vip"] == 1 and r["vip_until"] > int(time.time()))

def fmt_time(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}ч {m}м {s}с"

def get_rarities(user_id: int) -> dict:
    return VIP_RARITIES if is_vip(user_id) else RARITIES

def ensure_user(user_id: int, username: str) -> Tuple[int, float]:
    db.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", (user_id, username or str(user_id)))
    r = db.one("SELECT coins, last_card_time FROM users WHERE user_id=?", (user_id,))
    return (r["coins"] or 0, r["last_card_time"] or 0.0) if r else (0, 0.0)

def add_vip_days(user_id: int, days: int) -> None:
    now = int(time.time())
    r = db.one("SELECT vip_until FROM users WHERE user_id=?", (user_id,))
    new = (r["vip_until"] + days * 86400) if (r and r["vip_until"] > now) else (now + days * 86400)
    db.execute("UPDATE users SET vip=1, vip_until=? WHERE user_id=?", (new, user_id))

def add_card(user_id: int, card_id: int) -> None:
    db.execute("INSERT INTO user_cards (user_id,card_id,quantity) VALUES (?,?,1) ON CONFLICT(user_id,card_id) DO UPDATE SET quantity=quantity+1", (user_id, card_id))
    db.execute("INSERT OR IGNORE INTO user_collection (user_id,card_id) VALUES (?,?)", (user_id, card_id))

def get_user_cards(user_id: int) -> List[dict]:
    return db.all("""SELECT c.card_id, c.name, c.rarity, c.image_file, uc.quantity, c.base_price
                     FROM user_cards uc JOIN cards c ON uc.card_id=c.card_id
                     WHERE uc.user_id=? ORDER BY c.card_id""", (user_id,))

def collection_progress(user_id: int) -> Tuple[int, int, int]:
    total = db.one("SELECT COUNT(DISTINCT name) AS n FROM cards WHERE is_case=0")["n"]
    done = db.one("""SELECT COUNT(DISTINCT c.name) AS n FROM user_collection uc JOIN cards c ON uc.card_id=c.card_id WHERE uc.user_id=? AND c.is_case=0""", (user_id,))["n"]
    pct = int(done / total * 100) if total else 0
    return done, total, pct

def check_cooldown(user_id: int, key: str, seconds: int) -> bool:
    now = time.time()
    r = db.one("SELECT timestamp FROM cooldowns WHERE user_id=? AND key=?", (user_id, key))
    if r and now - r["timestamp"] < seconds:
        return False
    db.execute("INSERT OR REPLACE INTO cooldowns (user_id,key,timestamp) VALUES (?,?,?)", (user_id, key, now))
    return True

def reset_tasks(user_id: int) -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    r = db.one("SELECT tasks_date FROM users WHERE user_id=?", (user_id,))
    if not r or r["tasks_date"] != today:
        db.execute("UPDATE users SET tasks_date=?,cards_opened=0,legendaries_earned=0,cases_opened=0,ultra_cases_opened=0,epic_streak=0,tasks_claimed='00000' WHERE user_id=?", (today, user_id))

def award_tasks(user_id: int) -> None:
    reset_tasks(user_id)
    r = db.one("SELECT cards_opened,legendaries_earned,cases_opened,ultra_cases_opened,epic_streak,tasks_claimed FROM users WHERE user_id=?", (user_id,))
    if not r:
        return
    claimed = list(r["tasks_claimed"] or "00000")
    checks = [
        (r["cards_opened"] >= 5, 120),
        (r["legendaries_earned"] >= 2, 150),
        (r["cases_opened"] >= 3, 100),
        (r["ultra_cases_opened"] >= 1, 50),
        (r["epic_streak"] >= 2, 150),
    ]
    changed = False
    for i, (done, reward) in enumerate(checks):
        if done and claimed[i] == "0":
            db.transfer_coins(user_id, reward)
            claimed[i] = "1"
            changed = True
    if changed:
        db.execute("UPDATE users SET tasks_claimed=? WHERE user_id=?", ("".join(claimed), user_id))

def random_card(user_id: int) -> Optional[dict]:
    rd = get_rarities(user_id)
    keys = list(rd.keys())
    rarity = random.choices(keys, weights=[rd[k]["chance"] for k in keys])[0]
    return db.one("SELECT card_id,name,rarity,base_price,image_file FROM cards WHERE rarity=? AND is_case=0 ORDER BY RANDOM() LIMIT 1", (rarity,))

def random_case_card():
    return random.choices(CASE_POOL, weights=CASE_POOL_WEIGHTS, k=1)[0]

async def send_photo_or_text(ctx, chat_id: int, image_file: Optional[str], caption: str) -> None:
    if image_file:
        path = os.path.join(IMAGES_DIR, image_file)
        if os.path.exists(path):
            try:
                if image_file.lower().endswith(('.mp4', '.webm', '.mov', '.avi')):
                    with open(path, "rb") as f:
                        await ctx.bot.send_video(chat_id=chat_id, video=f, caption=caption, parse_mode="Markdown")
                elif image_file.lower().endswith('.gif'):
                    with open(path, "rb") as f:
                        await ctx.bot.send_animation(chat_id=chat_id, animation=f, caption=caption, parse_mode="Markdown")
                else:
                    with open(path, "rb") as f:
                        await ctx.bot.send_photo(chat_id=chat_id, photo=f, caption=caption, parse_mode="Markdown")
                return
            except Exception as e:
                logger.warning(f"Не удалось отправить файл {path}: {e}")
    await ctx.bot.send_message(chat_id=chat_id, text=caption, parse_mode="Markdown")

async def guard(update: Update, _ctx) -> bool:
    u = update.effective_user
    if not u:
        return False
    if is_banned(u.id):
        target = update.message or (update.callback_query and update.callback_query.message)
        if target:
            await target.reply_text("🚫 Вы заблокированы в боте.")
        return False
    return True

# ───────────────────────────────────────────────────
# ОСНОВНЫЕ КОМАНДЫ
# ───────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    u = update.effective_user
    ensure_user(u.id, u.username)
    reset_tasks(u.id)
    await update.message.reply_text(
        "🐾 *Добро пожаловать в Kros Cards Bot!*\n\n"
        "🎴 Здесь ты можешь собирать уникальные карты с животными!\n\n"
        "*Основные команды:*\n"
        "🎴 /card — открыть карту\n"
        "📦 /case — открыть кейс\n"
        "💰 /balance — баланс\n"
        "📚 /mycards — коллекция\n"
        "👤 /profile — профиль\n"
        "🏆 /top — рейтинг\n"
        "🎲 /dice — игра в кости\n"
        "🎨 /bet — ставка на цвет\n"
        "🎰 /lottery <ставка> <победителей> — создать лотерею\n"
        "🌟 /vip — купить VIP\n"
        "🎁 /daily — бонус VIP\n"
        "⭐ /primecase — кейс за звезду\n"
        "💸 /sell — продать карты\n"
        "📋 /tasks — задания\n"
        "📖 /collection — прогресс\n"
        "❓ /help — помощь",
        parse_mode="Markdown"
    )

async def card_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    u = update.effective_user
    ensure_user(u.id, u.username)
    row = db.one("SELECT last_card_time FROM users WHERE user_id=?", (u.id,))
    last = row["last_card_time"] if row else 0.0
    left = CARD_COOLDOWN_HOURS * 3600 - (time.time() - last)
    if left > 0:
        await update.message.reply_text(f"⏳ Следующая карта через: {fmt_time(left)}")
        return
    rd = get_rarities(u.id)
    chances_text = "\n".join([f"{rd[r]['emoji']} {r}: {rd[r]['chance']}%" for r in rd.keys()])
    msg = await update.message.reply_text(
        f"🎴 *ОТКРЫТИЕ КАРТЫ*\n\n📊 *ТВОИ ШАНСЫ:*\n{chances_text}\n\n┌─────────────┐\n│  ❓ ❓ ❓   │\n│   ?? ??    │\n└─────────────┘",
        parse_mode="Markdown"
    )
    await asyncio.sleep(0.8)
    frames = [
        "┌─────────────┐\n│  🟨 ⬜ ⬜   │\n│   ?? ??    │\n└─────────────┘",
        "┌─────────────┐\n│  🟨 🟨 ⬜   │\n│   ?? ??    │\n└─────────────┘",
        "┌─────────────┐\n│  🟨 🟨 🟨   │\n│   ?? ??    │\n└─────────────┘",
        "┌─────────────┐\n│ 🟨 🟨 🟨 🟨 │\n│   ?? ??    │\n└─────────────┘",
    ]
    for frame in frames:
        await asyncio.sleep(0.3)
        await msg.edit_text(f"🎴 *ОТКРЫТИЕ КАРТЫ*\n\n📊 *ТВОИ ШАНСЫ:*\n{chances_text}\n\n{frame}", parse_mode="Markdown")
    c = random_card(u.id)
    if not c:
        await msg.edit_text("❌ Ошибка получения карты")
        return
    add_card(u.id, c["card_id"])
    db.execute("UPDATE users SET last_card_time=?, cards_opened=cards_opened+1 WHERE user_id=?", (time.time(), u.id))
    if c["rarity"] == "Легендарная":
        db.execute("UPDATE users SET legendaries_earned=legendaries_earned+1 WHERE user_id=?", (u.id,))
    if c["rarity"] in ("Эпическая", "Мифическая"):
        db.execute("UPDATE users SET epic_streak=epic_streak+1 WHERE user_id=?", (u.id,))
    else:
        db.execute("UPDATE users SET epic_streak=0 WHERE user_id=?", (u.id,))
    award_tasks(u.id)
    label = rd.get(c["rarity"], {}).get("label", c["rarity"])
    rarity_emoji = rd.get(c["rarity"], {}).get("emoji", "⭐")
    await msg.delete()
    final_text = f"{rarity_emoji} *ВЫПАЛА КАРТА!*\n\n┌─────────────────────┐\n│                     │\n│  ✨ *{c['name']}* ✨  │\n│                     │\n│  {label}  │\n│  💰 {c['base_price']} 💎      │\n│                     │\n└─────────────────────┘"
    await send_photo_or_text(ctx, update.effective_chat.id, c.get("image_file"), final_text)

async def dice_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    uid = update.effective_user.id
    ensure_user(uid, update.effective_user.username)
    if not check_cooldown(uid, "dice", 3):
        await update.message.reply_text("⏳ Подожди 3 секунды")
        return
    user = db.one("SELECT coins FROM users WHERE user_id=?", (uid,))
    if not user or user["coins"] < DICE_MIN_BALANCE:
        await update.message.reply_text(f"❌ Для игры в кости нужно минимум {DICE_MIN_BALANCE} 💎")
        return
    msg = await update.message.reply_text("🎲 *БРОСОК КУБИКА*\n\n⚀⚁⚂⚃⚄⚅\n🌀 Крутим...", parse_mode="Markdown")
    await asyncio.sleep(1)
    d = random.randint(1, 6)
    dice_faces = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
    result = DICE_WINS[d]
    if result > 0:
        db.transfer_coins(uid, result)
        await msg.edit_text(f"🎲 *РЕЗУЛЬТАТ*\n\n{dice_faces[d]} Выпало *{d}*\n✅ ВЫИГРЫШ: +{result} 💎", parse_mode="Markdown")
    else:
        db.transfer_coins(uid, result)
        await msg.edit_text(f"🎲 *РЕЗУЛЬТАТ*\n\n{dice_faces[d]} Выпало *{d}*\n❌ ПРОИГРЫШ: {result} 💎", parse_mode="Markdown")

async def balance_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    u = update.effective_user
    coins, _ = ensure_user(u.id, u.username)
    await update.message.reply_text(f"💰 *Баланс:* {coins} 💎", parse_mode="Markdown")

async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📖 *Команды бота:*\n\n"
        "🎴 /card — открыть карту\n"
        "📦 /case — открыть кейс\n"
        "💰 /balance — баланс\n"
        "📚 /mycards — коллекция\n"
        "👤 /profile — профиль\n"
        "🏆 /top — топ игроков\n"
        "🎲 /dice — кости\n"
        "🎨 /bet black/white/gold сумма\n"
        "🎰 /lottery <ставка> <победителей>\n"
        "🌟 /vip — купить VIP\n"
        "🎁 /daily — бонус VIP\n"
        "⭐ /primecase — кейс за звезду\n"
        "💸 /sell — продать карты\n"
        "📋 /tasks — задания\n"
        "📖 /collection — прогресс",
        parse_mode="Markdown"
    )

async def vip_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    uid = update.effective_user.id
    if is_vip(uid):
        r = db.one("SELECT vip_until FROM users WHERE user_id=?", (uid,))
        days = (r["vip_until"] - int(time.time())) // 86400 if r else 0
        await update.message.reply_text(f"🌟 Ты уже VIP! Осталось {days} дн.", parse_mode="Markdown")
        return
    normal_chances = "\n".join([f"{RARITIES[r]['emoji']} {r}: {RARITIES[r]['chance']}%" for r in RARITIES.keys()])
    vip_chances = "\n".join([f"{VIP_RARITIES[r]['emoji']} {r}: {VIP_RARITIES[r]['chance']}%" for r in VIP_RARITIES.keys()])
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ 1 месяц — 15 Stars", callback_data="vip_1")],
        [InlineKeyboardButton("⭐ 3 месяца — 25 Stars", callback_data="vip_3")],
    ])
    await update.message.reply_text(
        f"🌟 *VIP СТАТУС*\n\n*Твои шансы:*\n{normal_chances}\n\n*VIP шансы:*\n{vip_chances}\n\nВыбери план:",
        reply_markup=kb,
        parse_mode="Markdown"
    )

async def vip_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if is_banned(q.from_user.id):
        await q.answer("🚫 Вы заблокированы.", show_alert=True)
        return
    await q.answer()
    months = 1 if q.data == "vip_1" else 3
    stars = 15 if months == 1 else 25
    await ctx.bot.send_invoice(
        chat_id=q.from_user.id,
        title=f"VIP на {months} мес.",
        description="Ежедневный бонус, повышенные шансы карт, скидка на кейсы",
        payload=f"vip_{months}",
        provider_token="",
        currency="XTR",
        prices=[{"label": f"VIP {months} мес.", "amount": stars}],
        start_parameter=f"vip_{months}",
    )

async def pre_checkout(update: Update, _ctx) -> None:
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id
    ensure_user(uid, update.effective_user.username)
    payload = update.message.successful_payment.invoice_payload
    if payload.startswith("vip_"):
        months = int(payload.split("_")[1])
        until = int(time.time()) + months * 30 * 86400
        db.execute("UPDATE users SET vip=1, vip_until=? WHERE user_id=?", (until, uid))
        await update.message.reply_text(f"🌟 Ты стал VIP на {months} мес.!")
    elif payload == "primecase":
        weights = [d[3] for d in PRIME_CASE_DROPS]
        name, typ, value, _ = random.choices(PRIME_CASE_DROPS, weights=weights, k=1)[0]
        if typ == "coins":
            db.transfer_coins(uid, value)
            await update.message.reply_text(f"🎉 Prime Case!\n💰 Выпало: {name}")
        else:
            add_vip_days(uid, value)
            await update.message.reply_text(f"🎉 Prime Case!\n🌟 Выпало: {name}")

async def mycards_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    u = update.effective_user
    cards = get_user_cards(u.id)
    if not cards:
        await update.message.reply_text("📭 Нет карточек! Используй /card")
        return
    total = sum(c["quantity"] for c in cards)
    lines = [f"📚 *Коллекция* @{u.username or u.id}\n📊 Всего: {total} карт\n"]
    for c in cards[:30]:
        lines.append(f"{RARITY_EMOJI.get(c['rarity'], '⚪')} {c['name']} — {c['quantity']} шт.")
    await update.message.reply_text("\n".join(lines)[:4096], parse_mode="Markdown")

async def profile_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    u = update.effective_user
    coins, last = ensure_user(u.id, u.username)
    cards = get_user_cards(u.id)
    total = sum(c["quantity"] for c in cards)
    unique = len(cards)
    vip_status = "🌟 VIP" if is_vip(u.id) else "⬜ Обычный"
    left = CARD_COOLDOWN_HOURS * 3600 - (time.time() - last)
    timer = f"⏳ {fmt_time(left)}" if left > 0 else "✅ Готово!"
    done, total_c, pct = collection_progress(u.id)
    await update.message.reply_text(
        f"👤 *ПРОФИЛЬ* @{u.username or u.id}\n\n🛡 Статус: {vip_status}\n💰 Монеты: {coins} 💎\n📚 Карт: {total} (уник. {unique})\n📖 Коллекция: {done}/{total_c} ({pct}%)\n🕐 До карты: {timer}",
        parse_mode="Markdown",
    )

async def collection_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    done, total, pct = collection_progress(update.effective_user.id)
    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
    await update.message.reply_text(f"📖 *ПРОГРЕСС КОЛЛЕКЦИИ*\n\n🎴 Собрано: {done}/{total}\n📊 [{bar}] {pct}%", parse_mode="Markdown")

async def tasks_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    uid = update.effective_user.id
    reset_tasks(uid)
    r = db.one("SELECT cards_opened,legendaries_earned,cases_opened,ultra_cases_opened,epic_streak,tasks_claimed FROM users WHERE user_id=?", (uid,))
    if not r:
        return
    claimed = r["tasks_claimed"] or "00000"
    tasks_list = [
        ("📦 Открой 5 карт", r["cards_opened"], 5, 120),
        ("⭐ 2 легендарные карты", r["legendaries_earned"], 2, 150),
        ("🧰 Открой 3 кейса", r["cases_opened"], 3, 100),
        ("💎 Открой 1 ультра-кейс", r["ultra_cases_opened"], 1, 50),
        ("⚡ 2 эпик карты подряд", r["epic_streak"], 2, 150),
    ]
    lines = ["📋 *ДНЕВНЫЕ ЗАДАНИЯ*\n"]
    for i, (desc, cur, need, reward) in enumerate(tasks_list):
        if claimed[i] == "1":
            st = "✅"
        elif cur >= need:
            st = "🎁"
        else:
            st = "⬜"
        lines.append(f"{st} {desc} — {cur}/{need} (+{reward}💎)")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def daily_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    uid = update.effective_user.id
    ensure_user(uid, update.effective_user.username)
    if not is_vip(uid):
        await update.message.reply_text("❌ Бонус только для VIP! /vip")
        return
    today = int(time.time() // 86400)
    r = db.one("SELECT last_daily FROM users WHERE user_id=?", (uid,))
    if r and r["last_daily"] == today:
        await update.message.reply_text("⏳ Бонус уже получен сегодня!")
        return
    db.transfer_coins(uid, 50)
    db.execute("UPDATE users SET last_daily=? WHERE user_id=?", (today, uid))
    coins = db.one("SELECT coins FROM users WHERE user_id=?", (uid,))["coins"]
    await update.message.reply_text(f"🎁 *VIP БОНУС!* +50 💎\n💰 Баланс: {coins} 💎", parse_mode="Markdown")

async def case_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    uid = update.effective_user.id
    coins, _ = ensure_user(uid, update.effective_user.username)
    price = CASE_VIP_PRICE if is_vip(uid) else CASE_PRICE
    if coins < price:
        await update.message.reply_text(f"❌ Нужно {price} 💎, у тебя {coins} 💎")
        return
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Открыть кейс", callback_data="open_case")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_case")]
    ])
    await update.message.reply_text(
        f"📦 *КЕЙС БАРСОСВИНЬИ*\n\n📊 *ШАНСЫ:*\n🟢 Редкая 45%\n🟣 Эпическая 25%\n🟡 Легендарная 16%\n💎 Ультра 12.5%\n⚫ Кроссовская 1.5%\n\n💰 Цена: {price} 💎",
        reply_markup=kb,
        parse_mode="Markdown"
    )

async def case_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()
    if q.data == "cancel_case":
        await q.edit_message_text("❌ Отменено")
        return
    user = db.one("SELECT coins FROM users WHERE user_id=?", (uid,))
    price = CASE_VIP_PRICE if is_vip(uid) else CASE_PRICE
    if not user or user["coins"] < price:
        await q.edit_message_text("❌ Недостаточно монет")
        return
    await q.edit_message_text("📦 *ОТКРЫТИЕ КЕЙСА*\n\n┌─────────────┐\n│  🔒 🔒 🔒   │\n│   ??? ???   │\n└─────────────┘", parse_mode="Markdown")
    await asyncio.sleep(0.5)
    frames = [
        "┌─────────────┐\n│  🟨 ⬜ ⬜   │\n│   ??? ???   │\n└─────────────┘",
        "┌─────────────┐\n│  🟨 🟨 ⬜   │\n│   ??? ???   │\n└─────────────┘",
        "┌─────────────┐\n│  🟨 🟨 🟨   │\n│   ??? ???   │\n└─────────────┘",
        "┌─────────────┐\n│ 🟨 🟨 🟨 🟨 │\n│   ??? ???   │\n└─────────────┘",
    ]
    for frame in frames:
        await asyncio.sleep(0.3)
        await q.edit_message_text(f"📦 *ОТКРЫТИЕ КЕЙСА*\n\n{frame}", parse_mode="Markdown")
    name, rarity, base_price, _ = random_case_card()
    card = db.one("SELECT card_id FROM cards WHERE name=?", (name,))
    db.transfer_coins(uid, -price)
    add_card(uid, card["card_id"])
    profit = base_price - price
    profit_emoji = "📈 +" if profit > 0 else "📉 "
    rarity_emojis = {"Редкая": "🟢", "Эпическая": "🟣", "Мифическая": "🔴", "Легендарная": "🟡", "Ультралегендарная": "💎", "Кроссовская": "⚫"}
    emoji = rarity_emojis.get(rarity, "⭐")
    await q.message.delete()
    caption = f"{emoji} *КЕЙС ОТКРЫТ!*\n\n┌─────────────────────┐\n│  ✨ *{name}* ✨  │\n│  {rarity}           │\n│  💰 {base_price} 💎      │\n│  {profit_emoji}{profit} 💎    │\n└─────────────────────┘"
    await send_photo_or_text(ctx, q.message.chat.id, CASE_IMAGES.get(name), caption)

async def prime_case_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    uid = update.effective_user.id
    ensure_user(uid, update.effective_user.username)
    await ctx.bot.send_invoice(
        chat_id=uid,
        title="⭐ Prime Case",
        description="Монеты или VIP-дни!",
        payload="primecase",
        provider_token="",
        currency="XTR",
        prices=[{"label": "Открыть кейс", "amount": PRIME_CASE_PRICE}],
        start_parameter="primecase",
    )

async def sell_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    uid = update.effective_user.id
    cards = get_user_cards(uid)
    if not cards:
        await update.message.reply_text("📭 Нет карт для продажи")
        return
    kb = []
    for c in cards[:15]:
        multiplier = max(0.35, 1 / (1 + (c["quantity"] - 1) * 0.2))
        price = int(c["base_price"] * multiplier)
        kb.append([InlineKeyboardButton(f"{c['name']} ({c['quantity']} шт.) ~ {price}💎", callback_data=f"sell_{c['card_id']}_{uid}")])
    kb.append([InlineKeyboardButton("❌ Отмена", callback_data="sell_cancel")])
    await update.message.reply_text("💰 *ПРОДАЖА КАРТ*\nВыбери карту:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def sell_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    uid = q.from_user.id
    if is_banned(uid):
        await q.answer("🚫 Вы заблокированы.", show_alert=True)
        return
    await q.answer()
    if q.data == "sell_cancel":
        await q.edit_message_text("❌ Отменено")
        return
    parts = q.data.split("_")
    if len(parts) != 3:
        await q.edit_message_text("❌ Ошибка")
        return
    card_id, owner = int(parts[1]), int(parts[2])
    if owner != uid:
        await q.answer("⚠️ Кнопка не для вас!", show_alert=True)
        return
    card = db.one("SELECT name, base_price FROM cards WHERE card_id=?", (card_id,))
    user_card = db.one("SELECT quantity FROM user_cards WHERE user_id=? AND card_id=?", (uid, card_id))
    if not card or not user_card:
        await q.edit_message_text("❌ Карта не найдена")
        return
    qty = user_card["quantity"]
    multiplier = max(0.35, 1 / (1 + (qty - 1) * 0.2))
    price_per = int(card["base_price"] * multiplier)
    total = price_per * qty
    db.execute("DELETE FROM user_cards WHERE user_id=? AND card_id=?", (uid, card_id))
    db.transfer_coins(uid, total)
    await q.edit_message_text(f"✅ *ПРОДАНО!*\n\n{card['name']} x{qty}\n💰 Получено: {total} 💎", parse_mode="Markdown")

async def top_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    kb = [
        [InlineKeyboardButton("🏆 По монетам", callback_data="top_coins")],
        [InlineKeyboardButton("🎴 По карточкам", callback_data="top_cards")],
    ]
    await update.message.reply_text("📊 *РЕЙТИНГ*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def top_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if is_banned(q.from_user.id):
        await q.answer("🚫 Вы заблокированы.", show_alert=True)
        return
    await q.answer()
    medals = ["🥇", "🥈", "🥉"]
    now = int(time.time())
    if q.data == "top_coins":
        rows = db.all("SELECT user_id, username, coins, vip, vip_until FROM users ORDER BY coins DESC LIMIT 10")
        text = "🏆 <b>ТОП ПО МОНЕТАМ</b>\n\n"
        for i, r in enumerate(rows):
            medal = medals[i] if i < 3 else f"{i+1}."
            icon = "👑" if r["user_id"] == OWNER_ID else ("🌟" if r.get("vip") == 1 and r.get("vip_until", 0) > now else "")
            username = r['username'] or str(r['user_id'])
            text += f"{medal} {icon} {username} — {r['coins']} 💎\n"
    else:
        rows = db.all("""SELECT u.user_id, u.username, u.vip, u.vip_until, SUM(uc.quantity) as total_cards
                         FROM user_cards uc JOIN users u ON uc.user_id = u.user_id
                         GROUP BY u.user_id ORDER BY total_cards DESC LIMIT 10""")
        text = "🎴 <b>ТОП ПО КАРТОЧКАМ</b>\n\n"
        for i, r in enumerate(rows):
            medal = medals[i] if i < 3 else f"{i+1}."
            icon = "👑" if r["user_id"] == OWNER_ID else ("🌟" if r.get("vip") == 1 and r.get("vip_until", 0) > now else "")
            username = r['username'] or str(r['user_id'])
            text += f"{medal} {icon} {username} — {r['total_cards']} карт\n"
    await q.edit_message_text(text, parse_mode="HTML")

async def bet_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await guard(update, ctx):
        return
    uid = update.effective_user.id
    args = ctx.args
    if len(args) < 2 or args[0].lower() not in ("black", "white", "gold") or not args[1].isdigit():
        await update.message.reply_text("❌ /bet black/white/gold сумма")
        return
    amount = int(args[1])
    if not (MIN_BET <= amount <= MAX_BET_BALLS):
        await update.message.reply_text(f"❌ Ставка от {MIN_BET} до {MAX_BET_BALLS} 💎")
        return
    ensure_user(uid, update.effective_user.username)
    if not check_cooldown(uid, "bet", CASINO_BET_COOLDOWN):
        await update.message.reply_text(f"⏳ Подожди {CASINO_BET_COOLDOWN} сек.")
        return
    coins_row = db.one("SELECT coins FROM users WHERE user_id=?", (uid,))
    if not coins_row or coins_row["coins"] < amount:
        await update.message.reply_text("❌ Не хватает монет")
        return
    msg = await update.message.reply_text(f"🎯 *СТАВКА НА {args[0].upper()}*\n\n💰 Сумма: {amount} 💎\n🟡⚪⚫ Крутим...", parse_mode="Markdown")
    await asyncio.sleep(1)
    ball = random.choices(["black", "white", "gold"], weights=[46.7, 46.7, 6.6])[0]
    ball_emoji = {"black": "⚫", "white": "⚪", "gold": "🟡"}
    if args[0].lower() == ball:
        mult = BET_GOLD_MULTIPLIER if ball == "gold" else BET_BLACK_WHITE_MULTIPLIER
        win = min(int(amount * mult), MAX_SINGLE_WIN)
        db.transfer_coins(uid, win - amount)
        await msg.edit_text(f"🎯 *РЕЗУЛЬТАТ*\n\n{ball_emoji[ball]} Выпал: *{ball.upper()}!*\n✅ ВЫИГРЫШ: +{win} 💎 (x{mult})", parse_mode="Markdown")
    else:
        db.transfer_coins(uid, -amount)
        await msg.edit_text(f"🎯 *РЕЗУЛЬТАТ*\n\n{ball_emoji[ball]} Выпал: *{ball.upper()}*\n❌ ПРОИГРЫШ: -{amount} 💎", parse_mode="Markdown")

async def lottery_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Лотерея работает только в группах")
        return
    if not await guard(update, ctx):
        return
    uid = update.effective_user.id
    if len(ctx.args) < 2:
        await update.message.reply_text("❌ /lottery <ставка> <победителей>\nПример: /lottery 100 3")
        return
    try:
        bet = int(ctx.args[0])
        winners_count = int(ctx.args[1])
    except:
        await update.message.reply_text("❌ Введите числа")
        return
    if bet < 50 or bet > 5000:
        return await update.message.reply_text("❌ Ставка от 50 до 5000 💎")
    if winners_count < 1 or winners_count > 10:
        return await update.message.reply_text("❌ Победителей от 1 до 10")
    user = db.one("SELECT coins FROM users WHERE user_id=?", (uid,))
    if not user or user["coins"] < bet:
        return await update.message.reply_text(f"❌ Нужно {bet} 💎")
    db.transfer_coins(uid, -bet)
    lottery_id = secrets.token_hex(4)
    LOTTERIES[lottery_id] = {"creator": uid, "bet": bet, "winners": winners_count, "players": [uid], "chat_id": update.effective_chat.id}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🎰 Участвовать ({bet} 💎)", callback_data=f"lottery_join_{lottery_id}")],
        [InlineKeyboardButton("🏆 Завершить", callback_data=f"lottery_finish_{lottery_id}")]
    ])
    await update.message.reply_text(
        f"🎰 *ЛОТЕРЕЯ СОЗДАНА*\n\n💰 Ставка: {bet} 💎\n🏆 Победителей: {winners_count}\n👥 Игроков: 1\n💰 Призовой фонд: {bet} 💎",
        reply_markup=kb,
        parse_mode="Markdown"
    )

async def lottery_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data.split("_")
    if len(data) < 3:
        await q.edit_message_text("❌ Ошибка")
        return
    action = data[1]
    lottery_id = data[2]
    lottery = LOTTERIES.get(lottery_id)
    if not lottery:
        await q.edit_message_text("❌ Лотерея не найдена")
        return
    uid = q.from_user.id
    if action == "join":
        if uid in lottery["players"]:
            await q.answer("❌ Ты уже участвуешь", show_alert=True)
            return
        user = db.one("SELECT coins FROM users WHERE user_id=?", (uid,))
        if not user or user["coins"] < lottery["bet"]:
            await q.answer("❌ Недостаточно монет", show_alert=True)
            return
        db.transfer_coins(uid, -lottery["bet"])
        lottery["players"].append(uid)
        pool = len(lottery["players"]) * lottery["bet"]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🎰 Участвовать ({lottery['bet']} 💎)", callback_data=f"lottery_join_{lottery_id}")],
            [InlineKeyboardButton("🏆 Завершить", callback_data=f"lottery_finish_{lottery_id}")]
        ])
        await q.edit_message_text(
            f"🎰 *ЛОТЕРЕЯ*\n\n💰 Ставка: {lottery['bet']} 💎\n🏆 Победителей: {lottery['winners']}\n👥 Игроков: {len(lottery['players'])}\n💰 Призовой фонд: {pool} 💎",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    elif action == "finish":
        if uid != lottery["creator"]:
            await q.answer("❌ Только создатель", show_alert=True)
            return
        if len(lottery["players"]) < lottery["winners"]:
            await q.answer("❌ Недостаточно игроков", show_alert=True)
            return
        winners = random.sample(lottery["players"], lottery["winners"])
        pool = len(lottery["players"]) * lottery["bet"]
        reward = int(pool / lottery["winners"])
        text = f"🏆 *ЛОТЕРЕЯ ЗАВЕРШЕНА*\n\n💰 Банк: {pool} 💎\n👥 Игроков: {len(lottery['players'])}\n\n*Победители:*\n"
        for w in winners:
            db.transfer_coins(w, reward)
            try:
                user = await ctx.bot.get_chat(w)
                name = user.username or user.first_name or str(w)
                text += f"👑 @{name} +{reward} 💎\n"
            except:
                text += f"👑 {w} +{reward} 💎\n"
        del LOTTERIES[lottery_id]
        await q.edit_message_text(text, parse_mode="Markdown")

# ───────────────────────────────────────────────────
# АДМИН-КОМАНДЫ
# ───────────────────────────────────────────────────
async def give_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    if len(ctx.args) < 2:
        await update.message.reply_text("❌ /give @username сумма")
        return
    target = ctx.args[0].lstrip("@")
    try:
        amount = int(ctx.args[1])
    except:
        await update.message.reply_text("❌ Сумма должна быть числом")
        return
    user = db.one("SELECT user_id FROM users WHERE username=?", (target,))
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    db.transfer_coins(user["user_id"], amount)
    await update.message.reply_text(f"✅ Выдано {amount} монет @{target}")

async def stats_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    total_users = db.one("SELECT COUNT(*) FROM users")["COUNT(*)"]
    total_cards = db.one("SELECT SUM(quantity) FROM user_cards")["SUM(quantity)"] or 0
    total_vip = db.one("SELECT COUNT(*) FROM users WHERE vip=1 AND vip_until>?", (int(time.time()),))["COUNT(*)"]
    await update.message.reply_text(f"📊 *СТАТИСТИКА*\n\n👥 Игроков: {total_users}\n🎴 Карт: {total_cards}\n🌟 VIP: {total_vip}", parse_mode="Markdown")

async def ban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    if not ctx.args:
        await update.message.reply_text("❌ /ban @username")
        return
    target = ctx.args[0].lstrip("@")
    user = db.one("SELECT user_id FROM users WHERE username=?", (target,))
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    db.execute("INSERT OR REPLACE INTO banned_users (user_id, reason, banned_at) VALUES (?, ?, ?)", (user["user_id"], " ", int(time.time())))
    await update.message.reply_text(f"🚫 Пользователь @{target} заблокирован")

async def unban_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    if not ctx.args:
        await update.message.reply_text("❌ /unban @username")
        return
    target = ctx.args[0].lstrip("@")
    user = db.one("SELECT user_id FROM users WHERE username=?", (target,))
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    db.execute("DELETE FROM banned_users WHERE user_id=?", (user["user_id"],))
    await update.message.reply_text(f"✅ Пользователь @{target} разблокирован")

async def addadmin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Только владелец")
        return
    if not ctx.args:
        await update.message.reply_text("❌ /addadmin @username")
        return
    target = ctx.args[0].lstrip("@")
    user = db.one("SELECT user_id FROM users WHERE username=?", (target,))
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user["user_id"],))
    await update.message.reply_text(f"✅ @{target} добавлен в администраторы")

async def removeadmin_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ Только владелец")
        return
    if not ctx.args:
        await update.message.reply_text("❌ /removeadmin @username")
        return
    target = ctx.args[0].lstrip("@")
    user = db.one("SELECT user_id FROM users WHERE username=?", (target,))
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    db.execute("DELETE FROM admins WHERE user_id=?", (user["user_id"],))
    await update.message.reply_text(f"✅ @{target} удалён из администраторов")

async def restore_vip_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    kb = [
        [InlineKeyboardButton("⭐ 1 месяц", callback_data="restore_vip_1")],
        [InlineKeyboardButton("⭐ 3 месяца", callback_data="restore_vip_3")],
        [InlineKeyboardButton("⭐ 6 месяцев", callback_data="restore_vip_6")],
        [InlineKeyboardButton("⭐ 12 месяцев", callback_data="restore_vip_12")],
    ]
    await update.message.reply_text("🌟 *ВЫДАТЬ VIP*\n\nВыберите срок:", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def restore_vip_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("❌ Нет прав", show_alert=True)
        return
    await q.answer()
    months = int(q.data.split("_")[2])
    ctx.user_data["vip_months"] = months
    await q.edit_message_text(f"✅ Выбран срок: {months} мес.\n\nТеперь отправьте @username.")

async def handle_vip_username(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        return
    if "vip_months" not in ctx.user_data:
        return
    months = ctx.user_data.pop("vip_months")
    username = update.message.text.strip().lstrip("@")
    user = db.one("SELECT user_id FROM users WHERE username=?", (username,))
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    add_vip_days(user["user_id"], months * 30)
    await update.message.reply_text(f"✅ @{username} выдан VIP на {months} мес.!")

async def sendpost_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    if not ctx.args:
        await update.message.reply_text("❌ /sendpost текст")
        return
    text = " ".join(ctx.args)
    users = db.get_all_users()
    success = 0
    fail = 0
    status_msg = await update.message.reply_text(f"📨 Рассылка {len(users)} пользователям...")
    for user in users:
        try:
            await ctx.bot.send_message(chat_id=user["user_id"], text=f"📢 *ОБЪЯВЛЕНИЕ:*\n\n{text}", parse_mode="Markdown")
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    await status_msg.edit_text(f"✅ Рассылка: {success} доставлено, {fail} ошибок")

async def banned_list_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Нет прав")
        return
    banned = db.all("SELECT user_id, banned_at FROM banned_users")
    if not banned:
        await update.message.reply_text("📭 В бане никого нет")
        return
    text = "🚫 *ЗАБЛОКИРОВАННЫЕ:*\n\n"
    for b in banned:
        user = db.one("SELECT username FROM users WHERE user_id=?", (b["user_id"],))
        name = user["username"] if user else str(b["user_id"])
        date = datetime.fromtimestamp(b["banned_at"]).strftime("%d.%m.%Y")
        text += f"• @{name} — с {date}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def text_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    if "vip_months" in ctx.user_data:
        await handle_vip_username(update, ctx)
        return
    text = update.message.text.strip().lower()
    synonyms = {
        "крос": card_cmd, "кросс": card_cmd, "кейс": case_cmd, "case": case_cmd,
        "баланс": balance_cmd, "карты": mycards_cmd, "продать": sell_cmd,
        "топ": top_cmd, "рейтинг": top_cmd, "профиль": profile_cmd,
    }
    if text in synonyms:
        if is_banned(update.effective_user.id):
            await update.message.reply_text("🚫 Вы заблокированы")
            return
        await synonyms[text](update, ctx)

# ───────────────────────────────────────────────────
# ЗАПУСК
# ───────────────────────────────────────────────────
def main() -> None:
    os.makedirs(IMAGES_DIR, exist_ok=True)
    init_db()
    app = Application.builder().token(TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("card", card_cmd))
    app.add_handler(CommandHandler("mycards", mycards_cmd))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CommandHandler("collection", collection_cmd))
    app.add_handler(CommandHandler("tasks", tasks_cmd))
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler("vip", vip_command))
    app.add_handler(CommandHandler("primecase", prime_case_cmd))
    app.add_handler(CommandHandler("case", case_cmd))
    app.add_handler(CommandHandler("sell", sell_cmd))
    app.add_handler(CommandHandler("top", top_cmd))
    app.add_handler(CommandHandler("dice", dice_cmd))
    app.add_handler(CommandHandler("bet", bet_cmd))
    app.add_handler(CommandHandler("lottery", lottery_cmd))
    
    # Админ команды
    app.add_handler(CommandHandler("give", give_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("addadmin", addadmin_cmd))
    app.add_handler(CommandHandler("removeadmin", removeadmin_cmd))
    app.add_handler(CommandHandler("restore_vip", restore_vip_cmd))
    app.add_handler(CommandHandler("sendpost", sendpost_cmd))
    app.add_handler(CommandHandler("banned_list", banned_list_cmd))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(vip_callback, pattern="^vip_"))
    app.add_handler(CallbackQueryHandler(top_callback, pattern="^top_"))
    app.add_handler(CallbackQueryHandler(sell_callback, pattern="^sell_"))
    app.add_handler(CallbackQueryHandler(restore_vip_callback, pattern="^restore_vip_"))
    app.add_handler(CallbackQueryHandler(case_callback, pattern="^(open_case|cancel_case)$"))
    app.add_handler(CallbackQueryHandler(lottery_callback, pattern="^lottery_"))
    
    # Платежи
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # Текст
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    logger.info("🚀 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
