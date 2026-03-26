#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║    ULTRA ADVANCED TELEGRAM GROUP & CHANNEL MANAGER BOT v8.0 NEXUS          ║
║   Beyond MissRose • All-in-One • Single File • 300+ Features • NEXUS       ║
║        🎨 FULLY ANIMATED • 🔒 PERSISTENT • 🚀 FUTURISTIC • ⚡ SMART       ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, re, json, time, math, random, string, asyncio, sqlite3, logging
import hashlib, textwrap, datetime, calendar, html, urllib.parse, uuid, base64, io
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict, deque
from functools import wraps

# ─── Dependencies ─────────────────────────────────────────────────────────────
def _install(pkg):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q", "--break-system-packages"])

for _dep in ["python-telegram-bot[job-queue]>=20.0", "aiohttp", "qrcode[pil]", "Pillow", "pytz"]:
    try:
        _name = _dep.split("[")[0].replace("-", "_").replace("python_telegram_bot", "telegram")
        __import__(_name)
    except ImportError:
        _install(_dep)

from telegram import (
    Update, Chat, User, Message, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, BotCommand, ChatMemberAdministrator, ChatMemberOwner,
    InlineQueryResultArticle, InputTextMessageContent, constants
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, InlineQueryHandler, ContextTypes, filters, JobQueue
)
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.helpers import mention_html
import aiohttp, pytz

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log")]
)
logger = logging.getLogger("NexusBot")

# ─── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER_IDS   = [int(x) for x in os.environ.get("OWNER_IDS", "").split(",") if x.strip().isdigit()]
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL_ID", "0") or 0)
GBAN_LOG    = int(os.environ.get("GBAN_LOG_CHANNEL", "0") or 0)
DB_PATH     = os.environ.get("DB_PATH", "bot_data.db")
VERSION     = "8.0.0-NEXUS"
START_TIME  = datetime.datetime.now(pytz.utc)

# ─── In-Memory Caches ─────────────────────────────────────────────────────────
flood_cache:      Dict[str, deque]   = defaultdict(lambda: deque(maxlen=50))
afk_cache:        Dict[int, dict]    = {}
raid_tracker:     Dict[int, deque]   = defaultdict(lambda: deque(maxlen=50))
msg_hashes:       Dict[int, deque]   = defaultdict(lambda: deque(maxlen=30))
connection_cache: Dict[int, int]     = {}
warn_cd:          Dict[Tuple, float] = {}
trivia_cache:     Dict[int, dict]    = {}
captcha_cache:    Dict[Tuple, dict]  = {}
work_cd:          Dict[int, float]   = {}

# ═══════════════════════════════════════════════════════════════════════════════
#                   🎨 ANIMATION & BEAUTIFUL UI SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
LOADING_FRAMES = ["⣾","⣽","⣻","⢿","⡿","⣟","⣯","⣷"]
NEON_FRAMES    = ["🔵","🟣","🔴","🟠","🟡","🟢"]
STAR_FRAMES    = ["✦","✧","★","☆","✨","⭐"]

def e(t: str, w: int = 36) -> str:
    """Box border — exact width."""
    inner = w - 4
    t2 = t[:inner] if len(t) > inner else t
    return (f"╔{'═'*(w-2)}╗\n"
            f"║ {t2.center(w-4)} ║\n"
            f"╠{'═'*(w-2)}╣")

def box_top(title: str, w: int = 36) -> str:
    inner = w - 4
    t = title[:inner] if len(title) > inner else title
    return (f"╔{'═'*(w-2)}╗\n"
            f"║ {t.center(w-4)} ║\n"
            f"╠{'═'*(w-2)}╣")

def box_end(w: int = 36) -> str:
    return f"╚{'═'*(w-2)}╝"

def progress_bar(value: int, max_val: int, length: int = 10, filled: str = "█", empty: str = "░") -> str:
    if max_val == 0: return empty * length
    filled_len = int(length * value / max_val)
    return filled * filled_len + empty * (length - filled_len)

def stars_bar(value: int, max_val: int = 5) -> str:
    filled = min(int(value), max_val)
    return "⭐" * filled + "☆" * (max_val - filled)

def rank_badge(rank: int) -> str:
    if rank == 1: return "🥇"
    if rank == 2: return "🥈"
    if rank == 3: return "🥉"
    if rank <= 10: return "🏅"
    if rank <= 50: return "🎖️"
    return "👤"

def level_from_msgs(msgs: int) -> int:
    return max(1, int(math.log(max(msgs, 1) + 1, 1.5)))

def level_title(lvl: int) -> str:
    titles = {1:"Newcomer",5:"Member",10:"Regular",15:"Active",20:"Veteran",
              30:"Legend",50:"Deity",100:"Transcendent"}
    for threshold in sorted(titles.keys(), reverse=True):
        if lvl >= threshold: return titles[threshold]
    return "Newcomer"

async def send_loading(update: Update, text: str = None) -> Optional[Message]:
    frame = random.choice(LOADING_FRAMES)
    msg_text = text or f"{frame} <b>Processing...</b>"
    try:
        return await update.message.reply_text(msg_text, parse_mode="HTML")
    except:
        return None

async def animate_loading(update: Update, label: str = "Processing") -> Optional[Message]:
    frames = [
        f"⚡ <b>{label}</b> <code>[{random.choice(NEON_FRAMES)}]</code>",
        f"⚡ <b>{label}</b> <code>[{random.choice(NEON_FRAMES)}{random.choice(NEON_FRAMES)}]</code>",
        f"⚡ <b>{label}</b> <code>[{random.choice(NEON_FRAMES)}{random.choice(NEON_FRAMES)}{random.choice(NEON_FRAMES)}]</code>",
    ]
    try:
        m = await update.message.reply_text(frames[0], parse_mode="HTML")
        for frame in frames[1:]:
            await asyncio.sleep(0.25)
            try: await m.edit_text(frame, parse_mode="HTML")
            except: pass
        return m
    except:
        return None

async def finish_anim(m: Optional[Message], text: str, reply_markup=None) -> None:
    if not m: return
    try:
        await m.edit_text(text, parse_mode="HTML", reply_markup=reply_markup,
                          disable_web_page_preview=True)
    except Exception as ex:
        logger.debug(f"finish_anim: {ex}")

# ═══════════════════════════════════════════════════════════════════════════════
#                          DATABASE
# ═══════════════════════════════════════════════════════════════════════════════
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    db = get_db(); c = db.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS chats (
        chat_id INTEGER PRIMARY KEY, title TEXT, chat_type TEXT, lang TEXT DEFAULT 'en',
        welcome_msg TEXT, goodbye_msg TEXT, welcome_media TEXT, rules_text TEXT,
        welcome_buttons TEXT DEFAULT '[]', welcome_delete_after INTEGER DEFAULT 0,
        log_channel INTEGER DEFAULT 0, warn_limit INTEGER DEFAULT 3,
        warn_action TEXT DEFAULT 'mute', mute_duration INTEGER DEFAULT 3600,
        anti_spam INTEGER DEFAULT 1, anti_flood INTEGER DEFAULT 1,
        flood_count INTEGER DEFAULT 5, flood_time INTEGER DEFAULT 5,
        flood_action TEXT DEFAULT 'mute', anti_link INTEGER DEFAULT 0,
        anti_forward INTEGER DEFAULT 0, anti_bot INTEGER DEFAULT 0,
        anti_nsfw INTEGER DEFAULT 0, anti_raid INTEGER DEFAULT 0,
        raid_threshold INTEGER DEFAULT 10, slowmode_delay INTEGER DEFAULT 0,
        delete_commands INTEGER DEFAULT 0, delete_service_msgs INTEGER DEFAULT 0,
        lock_stickers INTEGER DEFAULT 0, lock_gifs INTEGER DEFAULT 0,
        lock_media INTEGER DEFAULT 0, lock_polls INTEGER DEFAULT 0,
        lock_inline INTEGER DEFAULT 0, lock_bots INTEGER DEFAULT 0,
        lock_forward INTEGER DEFAULT 0, lock_games INTEGER DEFAULT 0,
        lock_voice INTEGER DEFAULT 0, lock_video INTEGER DEFAULT 0,
        lock_document INTEGER DEFAULT 0, lock_all INTEGER DEFAULT 0,
        lock_preview INTEGER DEFAULT 0, lock_url INTEGER DEFAULT 0,
        lock_anon INTEGER DEFAULT 0, greetmembers INTEGER DEFAULT 1,
        goodbye_enabled INTEGER DEFAULT 1, welcome_captcha INTEGER DEFAULT 0,
        force_sub INTEGER DEFAULT 0, force_sub_channel INTEGER DEFAULT 0,
        blacklist_action TEXT DEFAULT 'delete', cas_enabled INTEGER DEFAULT 0,
        report_enabled INTEGER DEFAULT 1, economy_enabled INTEGER DEFAULT 1,
        rep_enabled INTEGER DEFAULT 1, fun_enabled INTEGER DEFAULT 1,
        restrict_new_members INTEGER DEFAULT 0, new_member_mute_duration INTEGER DEFAULT 0,
        clean_service INTEGER DEFAULT 0, tag_admins_on_report INTEGER DEFAULT 1,
        fed_id TEXT DEFAULT NULL, anti_arabic INTEGER DEFAULT 0,
        anti_rtl INTEGER DEFAULT 0, max_warn_time INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT, last_name TEXT,
        is_gbanned INTEGER DEFAULT 0, gban_reason TEXT, gbanned_by INTEGER DEFAULT 0,
        gbanned_at TIMESTAMP, is_sudo INTEGER DEFAULT 0, reputation INTEGER DEFAULT 0,
        bio TEXT, is_afk INTEGER DEFAULT 0, afk_reason TEXT, afk_since TIMESTAMP,
        coins INTEGER DEFAULT 0, bank INTEGER DEFAULT 0, last_daily TIMESTAMP,
        last_work TIMESTAMP, total_msgs INTEGER DEFAULT 0, badges TEXT DEFAULT '[]',
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS chat_members (
        chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, username TEXT,
        first_name TEXT, is_bot INTEGER DEFAULT 0, msgs INTEGER DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (chat_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS warns (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL, reason TEXT, warned_by INTEGER,
        warned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
        name TEXT NOT NULL, content TEXT, parse_mode TEXT DEFAULT 'HTML',
        media_type TEXT, media_id TEXT, buttons TEXT DEFAULT '[]',
        created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, name)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS filters (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
        keyword TEXT NOT NULL, reply TEXT, is_regex INTEGER DEFAULT 0,
        media_type TEXT, media_id TEXT, buttons TEXT DEFAULT '[]',
        created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, keyword)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
        word TEXT NOT NULL, is_regex INTEGER DEFAULT 0,
        added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, word)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS mutes (
        chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, muted_by INTEGER,
        muted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, until TIMESTAMP, reason TEXT,
        PRIMARY KEY(chat_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS bans (
        chat_id INTEGER NOT NULL, user_id INTEGER NOT NULL, banned_by INTEGER,
        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, reason TEXT,
        PRIMARY KEY(chat_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
        message TEXT NOT NULL, media_id TEXT, media_type TEXT,
        parse_mode TEXT DEFAULT 'HTML', next_run TIMESTAMP NOT NULL,
        repeat TEXT DEFAULT 'none', repeat_val INTEGER DEFAULT 0,
        created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
        reporter_id INTEGER NOT NULL, reported_id INTEGER NOT NULL,
        message_id INTEGER, reason TEXT, status TEXT DEFAULT 'open',
        resolved_by INTEGER, reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
        admin_id INTEGER NOT NULL, action TEXT NOT NULL,
        target_id INTEGER, reason TEXT, extra TEXT,
        action_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reputation (
        giver_id INTEGER NOT NULL, receiver_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL, given_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(giver_id, receiver_id, chat_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS economy (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL, type TEXT NOT NULL, amount INTEGER NOT NULL,
        detail TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS connections (
        user_id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL,
        connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS federations (
        fed_id TEXT PRIMARY KEY, name TEXT NOT NULL, owner_id INTEGER NOT NULL,
        logs_channel INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS federation_admins (
        fed_id TEXT NOT NULL, user_id INTEGER NOT NULL,
        PRIMARY KEY(fed_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS federation_chats (
        fed_id TEXT NOT NULL, chat_id INTEGER NOT NULL,
        PRIMARY KEY(fed_id, chat_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS federation_bans (
        fed_id TEXT NOT NULL, user_id INTEGER NOT NULL, reason TEXT,
        banned_by INTEGER, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(fed_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS custom_commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER NOT NULL,
        command TEXT NOT NULL, response TEXT NOT NULL,
        created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, command)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sudo_users (
        user_id INTEGER PRIMARY KEY, added_by INTEGER,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS shop_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        description TEXT, price INTEGER NOT NULL, effect TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS inventory (
        user_id INTEGER NOT NULL, item_id INTEGER NOT NULL, quantity INTEGER DEFAULT 1,
        bought_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(user_id, item_id)
    )""")

    # Seed default shop items
    c.execute("""INSERT OR IGNORE INTO shop_items (id, name, description, price, effect)
                 VALUES
                 (1, '⭐ VIP Badge', 'Show your VIP status', 5000, 'vip'),
                 (2, '🔥 Flame Badge', 'Hot member badge', 2500, 'flame'),
                 (3, '💎 Diamond Badge', 'Diamond member status', 10000, 'diamond'),
                 (4, '🎭 Jester Hat', 'For the fun ones', 1000, 'jester'),
                 (5, '🛡️ Shield', 'Protection badge', 3000, 'shield')""")

    db.commit(); db.close()
    logger.info("✅ Database initialized (v8.0 NEXUS)")

# ─── DB helpers ───────────────────────────────────────────────────────────────
def get_chat(chat_id: int) -> dict:
    db = get_db()
    row = db.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
    db.close()
    return dict(row) if row else {}

def ensure_chat(chat: Chat):
    db = get_db()
    db.execute("INSERT OR IGNORE INTO chats (chat_id, title, chat_type) VALUES (?,?,?)",
               (chat.id, chat.title or "", chat.type))
    db.execute("UPDATE chats SET title=?, updated_at=CURRENT_TIMESTAMP WHERE chat_id=?",
               (chat.title or "", chat.id))
    db.commit(); db.close()

def ensure_user(user: User):
    db = get_db()
    db.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?,?,?,?)",
               (user.id, user.username or "", user.first_name or "", user.last_name or ""))
    db.execute("UPDATE users SET username=?, first_name=?, last_name=?, last_seen=CURRENT_TIMESTAMP WHERE user_id=?",
               (user.username or "", user.first_name or "", user.last_name or "", user.id))
    db.commit(); db.close()

def track_member(chat_id: int, user: User, increment_msg: bool = False):
    if user.is_bot: return
    db = get_db()
    db.execute("""INSERT OR IGNORE INTO chat_members (chat_id, user_id, username, first_name, is_bot)
                  VALUES (?,?,?,?,?)""",
               (chat_id, user.id, user.username or "", user.first_name or "", 0))
    if increment_msg:
        db.execute("""UPDATE chat_members SET username=?, first_name=?, last_seen=CURRENT_TIMESTAMP,
                      msgs=msgs+1 WHERE chat_id=? AND user_id=?""",
                   (user.username or "", user.first_name or "", chat_id, user.id))
    else:
        db.execute("""UPDATE chat_members SET username=?, first_name=?, last_seen=CURRENT_TIMESTAMP
                      WHERE chat_id=? AND user_id=?""",
                   (user.username or "", user.first_name or "", chat_id, user.id))
    db.commit(); db.close()

def get_setting(chat_id: int, key: str, default=None):
    cfg = get_chat(chat_id)
    return cfg.get(key, default)

def set_setting(chat_id: int, key: str, value):
    db = get_db()
    db.execute(f"UPDATE chats SET {key}=?, updated_at=CURRENT_TIMESTAMP WHERE chat_id=?", (value, chat_id))
    db.commit(); db.close()

def log_action(chat_id: int, admin_id: int, action: str, target_id: int = None, reason: str = None, extra: str = None):
    db = get_db()
    db.execute("INSERT INTO admin_logs (chat_id, admin_id, action, target_id, reason, extra) VALUES (?,?,?,?,?,?)",
               (chat_id, admin_id, action, target_id, reason, extra))
    db.commit(); db.close()

def is_gbanned(user_id: int) -> Optional[str]:
    db = get_db()
    row = db.execute("SELECT gban_reason FROM users WHERE user_id=? AND is_gbanned=1", (user_id,)).fetchone()
    db.close()
    return row["gban_reason"] if row else None

def is_sudo(user_id: int) -> bool:
    if user_id in OWNER_IDS: return True
    db = get_db()
    row = db.execute("SELECT 1 FROM sudo_users WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    return bool(row)

def parse_duration(s: str) -> Optional[datetime.timedelta]:
    s = s.lower().strip()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    match = re.match(r"^(\d+)([smhdw]?)$", s)
    if not match: return None
    value, unit = int(match.group(1)), match.group(2) or "s"
    return datetime.timedelta(seconds=value * units.get(unit, 1))

def fmt_duration(td: datetime.timedelta) -> str:
    s = int(td.total_seconds())
    if s < 60: return f"{s}s"
    if s < 3600: return f"{s//60}m {s%60}s"
    if s < 86400: return f"{s//3600}h {(s%3600)//60}m"
    return f"{s//86400}d {(s%86400)//3600}h"

# ═══════════════════════════════════════════════════════════════════════════════
#                          PERMISSION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
async def get_member(context, chat_id: int, user_id: int):
    try: return await context.bot.get_chat_member(chat_id, user_id)
    except: return None

async def is_admin(context, chat_id: int, user_id: int) -> bool:
    if is_sudo(user_id): return True
    m = await get_member(context, chat_id, user_id)
    return m and m.status in (m.ADMINISTRATOR, m.OWNER)

async def is_owner(context, chat_id: int, user_id: int) -> bool:
    if user_id in OWNER_IDS: return True
    m = await get_member(context, chat_id, user_id)
    return m and m.status == m.OWNER

async def can_restrict(context, chat_id: int, user_id: int) -> bool:
    if is_sudo(user_id): return True
    m = await get_member(context, chat_id, user_id)
    if not m: return False
    if m.status == m.OWNER: return True
    if m.status == m.ADMINISTRATOR and isinstance(m, ChatMemberAdministrator):
        return m.can_restrict_members
    return False

async def can_pin(context, chat_id: int, user_id: int) -> bool:
    if is_sudo(user_id): return True
    m = await get_member(context, chat_id, user_id)
    if not m: return False
    if m.status == m.OWNER: return True
    if m.status == m.ADMINISTRATOR and isinstance(m, ChatMemberAdministrator):
        return m.can_pin_messages
    return False

async def can_promote(context, chat_id: int, user_id: int) -> bool:
    if is_sudo(user_id): return True
    m = await get_member(context, chat_id, user_id)
    if not m: return False
    if m.status == m.OWNER: return True
    if m.status == m.ADMINISTRATOR and isinstance(m, ChatMemberAdministrator):
        return m.can_promote_members
    return False

# ─── Decorators ───────────────────────────────────────────────────────────────
def admin_only(fn):
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.effective_chat: return
        if update.effective_chat.type == "private": return await fn(update, context)
        if not await is_admin(context, update.effective_chat.id, update.effective_user.id):
            await update.message.reply_text(
                "╔══════════════════════╗\n"
                "║  🚫 <b>ACCESS DENIED</b>  ║\n"
                "╚══════════════════════╝\n\n"
                "⚡ <i>This command requires admin privileges.</i>",
                parse_mode="HTML")
            return
        return await fn(update, context)
    return wrapper

def owner_only(fn):
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user: return
        if update.effective_user.id not in OWNER_IDS and not is_sudo(update.effective_user.id):
            await update.message.reply_text(
                "👑 <b>Owner Only</b>\n<i>Restricted to bot owner/sudo users.</i>",
                parse_mode="HTML")
            return
        return await fn(update, context)
    return wrapper

def groups_only(fn):
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat and update.effective_chat.type == "private":
            await update.message.reply_text(
                "👥 <b>Groups Only</b>\n<i>This command only works in groups.</i>",
                parse_mode="HTML")
            return
        return await fn(update, context)
    return wrapper

# ─── Reply helpers ────────────────────────────────────────────────────────────
async def reply(update: Update, text: str, **kwargs):
    try:
        return await update.message.reply_text(text, parse_mode="HTML",
                                               disable_web_page_preview=True, **kwargs)
    except Exception as e:
        logger.debug(f"Reply error: {e}")

async def send_log(context, chat_id: int, text: str):
    cfg = get_chat(chat_id)
    ch = cfg.get("log_channel") or LOG_CHANNEL
    if ch:
        try: await context.bot.send_message(ch, text, parse_mode="HTML")
        except: pass

def user_link(user) -> str:
    name = html.escape(str(getattr(user, "first_name", "") or str(getattr(user, "id", "?"))))
    uid  = getattr(user, "id", 0)
    return f'<a href="tg://user?id={uid}">{name}</a>'

def get_target(update: Update, context) -> Optional[User]:
    msg = update.message
    if msg.reply_to_message:
        return msg.reply_to_message.from_user
    if context.args:
        arg = context.args[0].lstrip("@")
        if arg.lstrip("-").isdigit():
            uid = int(arg)
            return type("FakeUser", (), {
                "id": uid, "first_name": str(uid), "username": None,
                "last_name": None, "is_bot": False
            })()
    return None

def get_reason(context, start: int = 1) -> str:
    return " ".join(context.args[start:]) if context.args and len(context.args) > start else ""

def get_connected_chat(user_id: int, chat: Chat) -> int:
    if chat.type != "private": return chat.id
    return connection_cache.get(user_id, chat.id)

def parse_buttons(raw: str) -> List[List[InlineKeyboardButton]]:
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            rows = []
            for row in data:
                if isinstance(row, list):
                    rows.append([InlineKeyboardButton(b.get("text",""), url=b.get("url","#")) for b in row])
                elif isinstance(row, dict):
                    rows.append([InlineKeyboardButton(row.get("text",""), url=row.get("url","#"))])
            return rows
    except: pass
    return []

def tog(val) -> str:
    return "✅" if val else "❌"

def on_off(val) -> str:
    return "🟢 ON" if val else "🔴 OFF"

# ═══════════════════════════════════════════════════════════════════════════════
#                    🚀 START / HELP / COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📖 Help", url=f"https://t.me/{context.bot.username}?start=help"),
            InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{context.bot.username}?startgroup=true"),
        ]])
        await reply(update,
            f"╔══════════════════════════╗\n"
            f"║   ⚡ <b>NEXUS BOT v8.0</b>    ║\n"
            f"╚══════════════════════════╝\n\n"
            f"✨ <b>I'm online and ready!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📖 Use /help for all commands!\n"
            f"⚙️ Use /settings for group config!",
            reply_markup=kb)
        return

    m = await animate_loading(update, "Initializing NEXUS")
    name = html.escape(update.effective_user.first_name or "User")
    text = (
        f"╔══════════════════════════════════╗\n"
        f"║      ⚡ <b>NEXUS BOT v8.0</b>        ║\n"
        f"║    <i>The Future of Group Management</i>    ║\n"
        f"╠══════════════════════════════════╣\n"
        f"║  Hey <b>{name[:16]}</b>! 👋                ║\n"
        f"╚══════════════════════════════════╝\n\n"
        f"🛡️ <b>Advanced Moderation</b> — Smart ban, mute, warn\n"
        f"🚫 <b>Anti-Spam Engine</b> — Flood, raid, link, NSFW\n"
        f"📝 <b>Notes & Filters</b> — Auto-responses\n"
        f"🌐 <b>Federation</b> — Cross-group bans\n"
        f"💰 <b>Economy + Shop</b> — Earn, spend, trade\n"
        f"🏆 <b>Leaderboards</b> — Rankings & competitions\n"
        f"⭐ <b>Levels & Ranks</b> — Activity rewards\n"
        f"🎮 <b>Games & Fun</b> — Trivia, truth, dare\n"
        f"⚙️ <b>Button Settings</b> — Toggle everything\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 <b>300+ features • Smarter than ever!</b>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Help Menu", callback_data="help_main"),
         InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{context.bot.username}?startgroup=true")],
        [InlineKeyboardButton("🛡️ Moderation", callback_data="help_mod"),
         InlineKeyboardButton("💰 Economy", callback_data="help_economy")],
        [InlineKeyboardButton("🎮 Games & Fun", callback_data="help_fun"),
         InlineKeyboardButton("🔧 Utilities", callback_data="help_util")],
    ])
    await finish_anim(m, text, reply_markup=kb)

# ─── HELP SYSTEM ──────────────────────────────────────────────────────────────
HELP_SECTIONS = {
    "help_main": (
        "╔══════════════════════════╗\n"
        "║    📋 <b>NEXUS HELP CENTRE</b>   ║\n"
        "╠══════════════════════════╣\n"
        "║  ⚡ <b>v8.0 • 300+ Features</b>  ║\n"
        "╚══════════════════════════╝\n\n"
        "🔍 <i>Select a category to explore:</i>",
        [
            [InlineKeyboardButton("🛡️ Moderation", callback_data="help_mod"),
             InlineKeyboardButton("🚫 Protection", callback_data="help_protect")],
            [InlineKeyboardButton("📝 Notes", callback_data="help_notes"),
             InlineKeyboardButton("🔍 Filters", callback_data="help_filters")],
            [InlineKeyboardButton("🔒 Locks", callback_data="help_locks"),
             InlineKeyboardButton("👋 Welcome", callback_data="help_welcome")],
            [InlineKeyboardButton("🌐 Federation", callback_data="help_fed"),
             InlineKeyboardButton("🔗 Connect", callback_data="help_connect")],
            [InlineKeyboardButton("💰 Economy", callback_data="help_economy"),
             InlineKeyboardButton("⭐ Rep & Ranks", callback_data="help_rep")],
            [InlineKeyboardButton("🎮 Games & Fun", callback_data="help_fun"),
             InlineKeyboardButton("🔧 Utilities", callback_data="help_util")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="help_settings"),
             InlineKeyboardButton("👑 Admin/Owner", callback_data="help_admin")],
        ]
    ),
    "help_mod": (
        "╔═══════════════════════════╗\n"
        "║   🛡️ <b>MODERATION COMMANDS</b>  ║\n"
        "╚═══════════════════════════╝\n\n"
        "━━━ <b>BAN</b> ━━━━━━━━━━━━━━━━━━━\n"
        "<code>/ban</code> [reply/@user] [reason]\n"
        "<code>/tban</code> [reply/@user] 1h [reason] — Temp ban\n"
        "<code>/sban</code> [reply/@user] — Silent ban\n"
        "<code>/unban</code> [reply/@user]\n\n"
        "━━━ <b>KICK</b> ━━━━━━━━━━━━━━━━━━\n"
        "<code>/kick</code> [reply/@user]\n"
        "<code>/skick</code> — Silent kick\n\n"
        "━━━ <b>MUTE</b> ━━━━━━━━━━━━━━━━━━\n"
        "<code>/mute</code> [reply/@user] [reason]\n"
        "<code>/tmute</code> [reply/@user] 1h\n"
        "<code>/unmute</code> [reply/@user]\n\n"
        "━━━ <b>WARN</b> ━━━━━━━━━━━━━━━━━━\n"
        "<code>/warn</code> [reply/@user] [reason]\n"
        "<code>/dwarn</code> — Warn + delete message\n"
        "<code>/swarn</code> — Silent warn\n"
        "<code>/unwarn</code> — Remove 1 warn\n"
        "<code>/resetwarn</code> — Reset all warns\n"
        "<code>/warns</code> — View warn history\n\n"
        "━━━ <b>PROMOTE/RESTRICT</b> ━━━━━━━\n"
        "<code>/promote</code> [title] — Make admin\n"
        "<code>/demote</code> — Remove admin\n"
        "<code>/admintitle</code> [title] — Set title\n"
        "<code>/adminlist</code> — List all admins\n\n"
        "━━━ <b>CLEANUP</b> ━━━━━━━━━━━━━━━\n"
        "<code>/purge [N]</code> — Delete messages\n"
        "<code>/del</code> — Delete replied message\n"
        "<code>/pin</code> / <code>/unpin</code> / <code>/unpinall</code>\n"
        "<code>/zombies</code> — Count ghost accounts\n"
        "<code>/kickzombies</code> — Remove ghost accounts\n"
        "<code>/slowmode [s]</code> — Set slowmode\n"
        "<code>@admins</code> — Tag all admins",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_protect": (
        "╔══════════════════════════╗\n"
        "║   🚫 <b>PROTECTION SYSTEM</b>   ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━ <b>TOGGLES (or use /protect)</b> ━━━━\n"
        "<code>/antispam on|off</code> — Anti-spam\n"
        "<code>/antiflood on|off</code> — Anti-flood\n"
        "<code>/antilink on|off</code> — Block links\n"
        "<code>/antiforward on|off</code> — Block forwards\n"
        "<code>/antibot on|off</code> — Block bots joining\n"
        "<code>/antinsfw on|off</code> — Anti-NSFW\n"
        "<code>/antiarabic on|off</code> — Block Arabic/RTL\n\n"
        "━━━ <b>RAID PROTECTION</b> ━━━━━━━━━━\n"
        "<code>/antiraid on|off</code> — Anti-raid mode\n"
        "<code>/setraid N</code> — Raid join threshold\n"
        "<code>/cas on|off</code> — CAS ban integration\n"
        "<code>/restrict on|off</code> — Mute new members\n\n"
        "━━━ <b>FLOOD SETTINGS</b> ━━━━━━━━━━\n"
        "<code>/setflood N [time]</code> — Set flood limit\n"
        "<code>/setfloodaction mute|ban|kick</code>\n\n"
        "━━━ <b>PANEL</b> ━━━━━━━━━━━━━━━━━━\n"
        "<code>/protect</code> — Interactive protection panel",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_notes": (
        "╔══════════════════════════╗\n"
        "║      📝 <b>NOTES SYSTEM</b>      ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━ <b>MANAGING NOTES</b> ━━━━━━━━━\n"
        "<code>/save name text</code> — Save a note\n"
        "<code>/get name</code> — Retrieve a note\n"
        "<code>#name</code> — Quick retrieval\n"
        "<code>/notes</code> — List all notes\n"
        "<code>/clear name</code> — Delete a note\n"
        "<code>/clearall</code> — Delete all notes\n\n"
        "━━━ <b>FORMATTING</b> ━━━━━━━━━━━━\n"
        "Supports <b>HTML</b>, <i>Markdown</i>\n"
        "Button syntax: <code>[text](url)</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_filters": (
        "╔══════════════════════════╗\n"
        "║   🔍 <b>FILTERS & BLACKLIST</b>   ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━ <b>AUTO-FILTERS</b> ━━━━━━━━━━━\n"
        "<code>/filter keyword reply</code> — Add filter\n"
        "<code>/filters</code> — List all filters\n"
        "<code>/stop keyword</code> — Remove filter\n"
        "<code>/stopall</code> — Remove all\n"
        "<code>/filter regex:pattern reply</code>\n\n"
        "━━━ <b>BLACKLIST</b> ━━━━━━━━━━━━━\n"
        "<code>/addbl word</code> — Add to blacklist\n"
        "<code>/rmbl word</code> — Remove word\n"
        "<code>/blacklist</code> — View blacklist\n"
        "<code>/blmode delete|warn|mute|ban</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_locks": (
        "╔══════════════════════════╗\n"
        "║      🔒 <b>LOCK SYSTEM</b>       ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━ <b>LOCK TYPES</b> ━━━━━━━━━━━━\n"
        "<code>stickers</code> • <code>gifs</code> • <code>media</code> • <code>polls</code>\n"
        "<code>voice</code> • <code>video</code> • <code>document</code>\n"
        "<code>forward</code> • <code>games</code> • <code>inline</code>\n"
        "<code>url</code> • <code>anon</code> • <code>all</code>\n\n"
        "━━━ <b>COMMANDS</b> ━━━━━━━━━━━━━\n"
        "<code>/lock type</code> — Lock content type\n"
        "<code>/unlock type</code> — Unlock content\n"
        "<code>/locks</code> — Interactive lock panel",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_welcome": (
        "╔══════════════════════════╗\n"
        "║   👋 <b>WELCOME & GOODBYE</b>    ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━ <b>WELCOME</b> ━━━━━━━━━━━━━━\n"
        "<code>/setwelcome text</code> — Set welcome\n"
        "<code>/welcome on|off</code> — Toggle\n"
        "<code>/cleanwelcome on|off</code> — Auto-delete\n"
        "<code>/welcdel N</code> — Delete after N secs\n"
        "<code>/captcha on|off</code> — Verify new members\n\n"
        "━━━ <b>GOODBYE</b> ━━━━━━━━━━━━━\n"
        "<code>/setgoodbye text</code> — Set goodbye\n"
        "<code>/goodbye on|off</code> — Toggle\n\n"
        "━━━ <b>RULES</b> ━━━━━━━━━━━━━━━\n"
        "<code>/setrules text</code> — Set rules\n"
        "<code>/rules</code> — Show rules\n\n"
        "━━━ <b>PLACEHOLDERS</b> ━━━━━━━━\n"
        "<code>{first}</code> <code>{last}</code> <code>{mention}</code>\n"
        "<code>{username}</code> <code>{count}</code> <code>{chatname}</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_fed": (
        "╔══════════════════════════╗\n"
        "║    🌐 <b>FEDERATION SYSTEM</b>   ║\n"
        "╚══════════════════════════╝\n\n"
        "<i>Ban users across multiple groups at once!</i>\n\n"
        "━━━ <b>MANAGEMENT</b> ━━━━━━━━━━━\n"
        "<code>/newfed name</code> — Create federation\n"
        "<code>/delfed</code> — Delete your federation\n"
        "<code>/joinfed fed_id</code> — Join a federation\n"
        "<code>/leavefed</code> — Leave federation\n"
        "<code>/fedinfo</code> — Federation info\n\n"
        "━━━ <b>FED BANS</b> ━━━━━━━━━━━━\n"
        "<code>/fban user [reason]</code> — Fed ban\n"
        "<code>/unfban user</code> — Remove fed ban\n"
        "<code>/fedbans</code> — List fed bans\n"
        "<code>/fadmin user</code> — Add fed admin\n"
        "<code>/fremove user</code> — Remove fed admin",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_connect": (
        "╔══════════════════════════╗\n"
        "║    🔗 <b>CONNECTION SYSTEM</b>   ║\n"
        "╚══════════════════════════╝\n\n"
        "<i>Manage groups from your DMs!</i>\n\n"
        "━━━ <b>COMMANDS</b> ━━━━━━━━━━━━\n"
        "<code>/connect chat_id</code> — Connect to group\n"
        "<code>/disconnect</code> — Disconnect\n"
        "<code>/connected</code> — Check connection\n\n"
        "━━━ <b>HOW IT WORKS</b> ━━━━━━━\n"
        "1️⃣ Get your group ID with /id in group\n"
        "2️⃣ Send /connect [group_id] in my PM\n"
        "3️⃣ Use all admin commands from DM!",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_economy": (
        "╔══════════════════════════╗\n"
        "║     💰 <b>ECONOMY SYSTEM</b>     ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━ <b>EARNING</b> ━━━━━━━━━━━━━━\n"
        "<code>/daily</code> — Claim daily reward (~500)\n"
        "<code>/work</code> — Work for coins (1h cooldown)\n"
        "<code>/mine</code> — Mine coins (10-200)\n\n"
        "━━━ <b>BANKING</b> ━━━━━━━━━━━━━\n"
        "<code>/bank deposit N</code> — Deposit coins\n"
        "<code>/bank withdraw N</code> — Withdraw\n"
        "<code>/bank balance</code> — Bank balance\n\n"
        "━━━ <b>GAMES</b> ━━━━━━━━━━━━━━━\n"
        "<code>/flip amount</code> — Coin flip gamble\n"
        "<code>/slots amount</code> — 🎰 Slot machine\n"
        "<code>/rob @user</code> — Steal coins\n\n"
        "━━━ <b>SOCIAL</b> ━━━━━━━━━━━━━\n"
        "<code>/give @user amount</code> — Send coins\n"
        "<code>/coins [@user]</code> — Check balance\n"
        "<code>/shop</code> — Browse the shop\n"
        "<code>/buy item_id</code> — Buy from shop\n"
        "<code>/inventory</code> — Your items\n"
        "<code>/leaderboard</code> — Richest members",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_rep": (
        "╔══════════════════════════╗\n"
        "║   ⭐ <b>REPUTATION & RANKS</b>   ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━ <b>REPUTATION</b> ━━━━━━━━━━━\n"
        "<code>+rep</code> or <code>/rep @user</code> — Give +1 rep\n"
        "<code>/checkrep [@user]</code> — Check rep\n"
        "<code>/reprank</code> — Rep leaderboard\n\n"
        "━━━ <b>ACTIVITY RANKS</b> ━━━━━━━\n"
        "<code>/rank [@user]</code> — Your rank card\n"
        "<code>/top</code> — Most active members\n"
        "<code>/level [@user]</code> — Your level\n\n"
        "━━━ <b>LEADERBOARD</b> ━━━━━━━━━\n"
        "<code>/leaderboard</code> — Full board (tabs)\n"
        "<i>Tabs: Coins • Messages • Reputation</i>\n\n"
        "━━━ <b>REP RULES</b> ━━━━━━━━━━━\n"
        "⏰ 1 rep per user per 24h\n"
        "🚫 Can't give rep to yourself",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_fun": (
        "╔══════════════════════════╗\n"
        "║     🎮 <b>GAMES & FUN</b>        ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━ <b>GAMES</b> ━━━━━━━━━━━━━━━\n"
        "<code>/8ball question</code> — 🎱 Magic 8-ball\n"
        "<code>/roll [sides]</code> — 🎲 Roll dice\n"
        "<code>/trivia</code> — ❓ Quiz game\n"
        "<code>/wyr</code> — 🤔 Would you rather\n"
        "<code>/truth</code> — 💭 Truth question\n"
        "<code>/dare</code> — 😈 Dare challenge\n"
        "<code>/pp</code> — 💪 Power level\n\n"
        "━━━ <b>SOCIAL</b> ━━━━━━━━━━━━━\n"
        "<code>/slap @user</code> — 👋 Slap\n"
        "<code>/hug @user</code> — 🤗 Hug\n"
        "<code>/kiss @user</code> — 💋 Kiss\n"
        "<code>/pat @user</code> — 🫶 Pat\n"
        "<code>/poke @user</code> — 👉 Poke\n"
        "<code>/ship @user1 @user2</code> — 💕 Ship\n"
        "<code>/roast @user</code> — 🔥 Roast\n"
        "<code>/compliment @user</code> — 💐 Compliment\n\n"
        "━━━ <b>RANDOM</b> ━━━━━━━━━━━━━\n"
        "<code>/joke</code> — 😂 Random joke\n"
        "<code>/fact</code> — 🧠 Random fact\n"
        "<code>/quote</code> — 💬 Inspirational quote\n"
        "<code>/meme</code> — 😎 Random meme text",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_util": (
        "╔══════════════════════════╗\n"
        "║    🔧 <b>UTILITY COMMANDS</b>    ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━ <b>INFO</b> ━━━━━━━━━━━━━━━━━\n"
        "<code>/id [@user]</code> — Get IDs\n"
        "<code>/info [@user]</code> — User profile\n"
        "<code>/chatinfo</code> — Chat information\n"
        "<code>/ping</code> — 🏓 Bot latency\n"
        "<code>/uptime</code> — ⏱️ Bot uptime\n"
        "<code>/stats</code> — 📊 Group stats\n\n"
        "━━━ <b>TEXT TOOLS</b> ━━━━━━━━━━\n"
        "<code>/calc expr</code> — 🧮 Calculator\n"
        "<code>/hash text</code> — 🔐 Hash text\n"
        "<code>/b64 encode|decode</code> — Base64\n"
        "<code>/reverse text</code> — 🔄 Reverse\n"
        "<code>/ascii text</code> — ASCII codes\n\n"
        "━━━ <b>GENERATORS</b> ━━━━━━━━━━\n"
        "<code>/qr text</code> — 📱 QR code\n"
        "<code>/tr lang text</code> — 🌐 Translate\n"
        "<code>/weather city</code> — 🌤️ Weather\n"
        "<code>/time [timezone]</code> — 🕐 Time",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_settings": (
        "╔══════════════════════════╗\n"
        "║      ⚙️ <b>SETTINGS</b>          ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━ <b>INTERACTIVE PANELS</b> ━━━━\n"
        "<code>/settings</code> — Full settings panel\n"
        "<code>/protect</code> — Protection panel\n"
        "<code>/locks</code> — Lock types panel\n"
        "<code>/welcome</code> — Welcome settings\n\n"
        "━━━ <b>WARN SETTINGS</b> ━━━━━━━\n"
        "<code>/setwarnlimit N</code> — Set warn limit\n"
        "<code>/setwarnaction mute|ban|kick</code>\n\n"
        "━━━ <b>CHAT SETTINGS</b> ━━━━━━━\n"
        "<code>/cleanservice on|off</code>\n"
        "<code>/delcommands on|off</code>\n"
        "<code>/welcdel N</code> — Welcome delete timer\n"
        "<code>/slowmode N</code> — Set slowmode",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_admin": (
        "╔══════════════════════════╗\n"
        "║  👑 <b>ADMIN / OWNER COMMANDS</b>  ║\n"
        "╚══════════════════════════╝\n\n"
        "━━━ <b>GLOBAL MODERATION</b> ━━━━━\n"
        "<code>/gban user [reason]</code> — Global ban\n"
        "<code>/ungban user</code> — Remove global ban\n"
        "<code>/sudo user</code> — Add sudo user\n"
        "<code>/unsudo user</code> — Remove sudo\n\n"
        "━━━ <b>BROADCAST</b> ━━━━━━━━━━━\n"
        "<code>/broadcast msg</code> — All chats\n"
        "<code>/broadcastall msg</code> — All members\n\n"
        "━━━ <b>BOT MANAGEMENT</b> ━━━━━━\n"
        "<code>/botstats</code> — 📊 Bot statistics\n"
        "<code>/chatlist</code> — List all chats\n"
        "<code>/leave</code> — Leave a chat\n"
        "<code>/backup</code> — Export chat backup",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
}

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, buttons = HELP_SECTIONS["help_main"]
    if update.effective_chat.type != "private":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📖 Open Help in DM",
                                    url=f"https://t.me/{context.bot.username}?start=help")]])
        await reply(update, "📬 <b>Full help sent to your DM!</b>", reply_markup=kb)
        return
    await update.message.reply_text(text, parse_mode="HTML",
                                    reply_markup=InlineKeyboardMarkup(buttons),
                                    disable_web_page_preview=True)

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    key = q.data
    if key in HELP_SECTIONS:
        text, buttons = HELP_SECTIONS[key]
        try:
            await q.edit_message_text(text, parse_mode="HTML",
                                      reply_markup=InlineKeyboardMarkup(buttons),
                                      disable_web_page_preview=True)
        except: pass

# ═══════════════════════════════════════════════════════════════════════════════
#                          MODERATION COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════
async def _do_ban(context, chat_id: int, user_id: int, until: datetime.datetime = None):
    await context.bot.ban_chat_member(chat_id, user_id, until_date=until)

MUTE_PERMS   = ChatPermissions(can_send_messages=False, can_send_polls=False,
                                can_send_other_messages=False)
UNMUTE_PERMS = ChatPermissions(can_send_messages=True, can_send_polls=True,
                                can_send_other_messages=True, can_add_web_page_previews=True)

def _unban_btn(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔓 Unban", callback_data=f"unban:{chat_id}:{user_id}")]])

def _unmute_btn(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔊 Unmute", callback_data=f"unmute:{chat_id}:{user_id}")]])

@admin_only
@groups_only
async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>You need restrict rights to ban!</b>")
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ <b>Who to ban?</b> Reply to a user or provide @username.")
    if await is_admin(context, update.effective_chat.id, target.id):
        return await reply(update, "🛡️ <b>Cannot ban admins!</b>")
    reason = (" ".join(context.args) if context.args and update.message.reply_to_message
              else " ".join(context.args[1:]) if context.args else "")
    chat = update.effective_chat
    m = await animate_loading(update, "Executing ban")
    try:
        await _do_ban(context, chat.id, target.id)
        db = get_db()
        db.execute("INSERT OR REPLACE INTO bans (chat_id, user_id, banned_by, reason) VALUES (?,?,?,?)",
                   (chat.id, target.id, update.effective_user.id, reason))
        db.commit(); db.close()
        log_action(chat.id, update.effective_user.id, "ban", target.id, reason)
        text = (
            f"╔══════════════════════╗\n"
            f"║     🔨 <b>USER BANNED</b>     ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"🆔 <b>ID:</b> <code>{target.id}</code>\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"📝 <b>Reason:</b> {html.escape(reason or 'No reason')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚫 <i>Removed permanently.</i>"
        )
        await finish_anim(m, text, reply_markup=_unban_btn(chat.id, target.id))
        await send_log(context, chat.id,
            f"🔨 <b>BAN</b> | {html.escape(chat.title or '')}\n"
            f"Admin: {user_link(update.effective_user)}\n"
            f"User: {user_link(target)} (<code>{target.id}</code>)\n"
            f"Reason: {html.escape(reason or 'None')}")
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def tban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ <b>Usage:</b> <code>/tban @user 1h [reason]</code>")
    time_arg = (context.args[0] if update.message.reply_to_message and context.args
                else (context.args[1] if len(context.args) > 1 else "1h"))
    duration = parse_duration(time_arg)
    if not duration:
        return await reply(update, "❌ <b>Invalid duration.</b> Use: 1m, 1h, 1d, 1w")
    until = datetime.datetime.now(pytz.utc) + duration
    reason = " ".join(context.args[2:]) if len(context.args) > 2 else ""
    m = await animate_loading(update, "Executing temp ban")
    try:
        await _do_ban(context, update.effective_chat.id, target.id, until)
        log_action(update.effective_chat.id, update.effective_user.id, "tban", target.id, time_arg)
        await finish_anim(m,
            f"╔══════════════════════╗\n"
            f"║   ⏱️ <b>TEMP BANNED</b>    ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"⏰ <b>Duration:</b> {html.escape(fmt_duration(duration))}\n"
            f"📅 <b>Expires:</b> {until.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"📝 <b>Reason:</b> {html.escape(reason or 'No reason')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔓 <i>Will auto-unban when expired.</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def sban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id): return
    target = get_target(update, context)
    if not target: return
    try:
        await update.message.delete()
        if update.message.reply_to_message:
            await update.message.reply_to_message.delete()
        await _do_ban(context, update.effective_chat.id, target.id)
        log_action(update.effective_chat.id, update.effective_user.id, "sban", target.id, "silent")
    except: pass

@admin_only
@groups_only
async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user or provide @username.")
    m = await animate_loading(update, "Lifting ban")
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id, only_if_banned=True)
        db = get_db()
        db.execute("DELETE FROM bans WHERE chat_id=? AND user_id=?",
                   (update.effective_chat.id, target.id))
        db.commit(); db.close()
        log_action(update.effective_chat.id, update.effective_user.id, "unban", target.id)
        await finish_anim(m,
            f"╔══════════════════════╗\n"
            f"║    ✅ <b>USER UNBANNED</b>   ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 <i>User can now rejoin the group.</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def unban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    if len(parts) < 3: return await q.answer("Invalid", show_alert=True)
    chat_id, user_id = int(parts[1]), int(parts[2])
    if not await is_admin(context, chat_id, q.from_user.id):
        return await q.answer("🚫 Admins only!", show_alert=True)
    await q.answer()
    try:
        await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(f"✅ <b>User unbanned by {user_link(q.from_user)}!</b>", parse_mode="HTML")
    except Exception as e:
        await q.answer(f"Error: {e}", show_alert=True)

async def unmute_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    if len(parts) < 3: return await q.answer("Invalid", show_alert=True)
    chat_id, user_id = int(parts[1]), int(parts[2])
    if not await is_admin(context, chat_id, q.from_user.id):
        return await q.answer("🚫 Admins only!", show_alert=True)
    await q.answer()
    try:
        await context.bot.restrict_chat_member(chat_id, user_id, UNMUTE_PERMS)
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(f"🔊 <b>User unmuted by {user_link(q.from_user)}!</b>", parse_mode="HTML")
    except Exception as e:
        await q.answer(f"Error: {e}", show_alert=True)

@admin_only
@groups_only
async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    m = await animate_loading(update, "Kicking user")
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        log_action(update.effective_chat.id, update.effective_user.id, "kick", target.id)
        await finish_anim(m,
            f"╔══════════════════════╗\n"
            f"║     👢 <b>USER KICKED</b>      ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚪 <i>Kicked! They can still rejoin.</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def skick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id): return
    target = get_target(update, context)
    if not target: return
    try:
        await update.message.delete()
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
    except: pass

@admin_only
@groups_only
async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    reason = " ".join(context.args) if context.args and not update.message.reply_to_message else get_reason(context)
    m = await animate_loading(update, "Muting user")
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS)
        log_action(update.effective_chat.id, update.effective_user.id, "mute", target.id, reason)
        await finish_anim(m,
            f"╔══════════════════════╗\n"
            f"║     🔇 <b>USER MUTED</b>       ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"📝 <b>Reason:</b> {html.escape(reason or 'No reason')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔕 <i>Messages silenced.</i>",
            reply_markup=_unmute_btn(update.effective_chat.id, target.id)
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def tmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user or provide @username.")
    args = context.args or []
    time_str = args[0] if update.message.reply_to_message and args else (args[1] if len(args) > 1 else "1h")
    duration = parse_duration(time_str)
    if not duration: return await reply(update, "❌ <b>Invalid duration.</b> Use: 1m, 1h, 1d")
    until = datetime.datetime.now(pytz.utc) + duration
    m = await animate_loading(update, "Applying temp mute")
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS, until_date=until)
        log_action(update.effective_chat.id, update.effective_user.id, "tmute", target.id, time_str)
        await finish_anim(m,
            f"╔══════════════════════╗\n"
            f"║   ⏱️ <b>TEMP MUTED</b>     ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"⏰ <b>Duration:</b> {html.escape(fmt_duration(duration))}\n"
            f"📅 <b>Until:</b> {until.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔓 <i>Will auto-unmute when expired.</i>",
            reply_markup=_unmute_btn(update.effective_chat.id, target.id)
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    m = await animate_loading(update, "Unmuting user")
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, UNMUTE_PERMS)
        log_action(update.effective_chat.id, update.effective_user.id, "unmute", target.id)
        await finish_anim(m,
            f"╔══════════════════════╗\n"
            f"║    🔊 <b>USER UNMUTED</b>     ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 <i>Can now send messages again.</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

# ─── WARN SYSTEM ──────────────────────────────────────────────────────────────
@admin_only
@groups_only
async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _warn(update, context, silent=False, delete_msg=False)

@admin_only
@groups_only
async def dwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _warn(update, context, silent=False, delete_msg=True)

@admin_only
@groups_only
async def swarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _warn(update, context, silent=True, delete_msg=False)

async def _warn(update, context, silent=False, delete_msg=False):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    if await is_admin(context, update.effective_chat.id, target.id):
        return await reply(update, "🛡️ <b>Cannot warn admins!</b>")
    reason = (" ".join(context.args) if context.args and update.message.reply_to_message
              else " ".join(context.args[1:]) if context.args else "")
    cfg = get_chat(update.effective_chat.id)
    warn_limit = cfg.get("warn_limit", 3)
    warn_action = cfg.get("warn_action", "mute")

    db = get_db()
    db.execute("INSERT INTO warns (chat_id, user_id, reason, warned_by) VALUES (?,?,?,?)",
               (update.effective_chat.id, target.id, reason, update.effective_user.id))
    db.commit()
    count = db.execute("SELECT COUNT(*) as c FROM warns WHERE chat_id=? AND user_id=?",
                       (update.effective_chat.id, target.id)).fetchone()["c"]
    db.close()

    if delete_msg and update.message.reply_to_message:
        try: await update.message.reply_to_message.delete()
        except: pass

    log_action(update.effective_chat.id, update.effective_user.id, "warn", target.id, reason)
    bar = progress_bar(count, warn_limit)
    extra_action = ""

    if count >= warn_limit:
        db = get_db()
        db.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?",
                   (update.effective_chat.id, target.id))
        db.commit(); db.close()
        if warn_action == "ban":
            await _do_ban(context, update.effective_chat.id, target.id)
            extra_action = "\n🔨 <b>Auto-banned</b> — warn limit reached!"
        elif warn_action == "kick":
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await context.bot.unban_chat_member(update.effective_chat.id, target.id)
            extra_action = "\n👢 <b>Auto-kicked</b> — warn limit reached!"
        else:
            await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS)
            extra_action = "\n🔇 <b>Auto-muted</b> — warn limit reached!"

    if not silent:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Unwarn", callback_data=f"unwarn:{update.effective_chat.id}:{target.id}"),
            InlineKeyboardButton("🗑️ Reset All", callback_data=f"resetwarn:{update.effective_chat.id}:{target.id}"),
        ]])
        text = (
            f"╔══════════════════════╗\n"
            f"║     ⚠️ <b>USER WARNED</b>      ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"📝 <b>Reason:</b> {html.escape(reason or 'No reason')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 <b>Warns:</b> {count}/{warn_limit}\n"
            f"[{bar}]{extra_action}"
        )
        await reply(update, text, reply_markup=kb)

async def warn_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    if len(parts) < 3: return await q.answer("Invalid", show_alert=True)
    action, chat_id, user_id = parts[0], int(parts[1]), int(parts[2])
    if not await is_admin(context, chat_id, q.from_user.id):
        return await q.answer("🚫 Admins only!", show_alert=True)
    await q.answer()
    db = get_db()
    if action == "unwarn":
        row = db.execute("SELECT id FROM warns WHERE chat_id=? AND user_id=? ORDER BY warned_at DESC LIMIT 1",
                         (chat_id, user_id)).fetchone()
        if row: db.execute("DELETE FROM warns WHERE id=?", (row["id"],))
        db.commit(); db.close()
        await q.message.reply_text(f"✅ <b>1 warn removed by {user_link(q.from_user)}!</b>", parse_mode="HTML")
    elif action == "resetwarn":
        db.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        db.commit(); db.close()
        await q.message.reply_text(f"🗑️ <b>All warns reset by {user_link(q.from_user)}!</b>", parse_mode="HTML")

@admin_only
@groups_only
async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    db = get_db()
    row = db.execute("SELECT id FROM warns WHERE chat_id=? AND user_id=? ORDER BY warned_at DESC LIMIT 1",
                     (update.effective_chat.id, target.id)).fetchone()
    if row:
        db.execute("DELETE FROM warns WHERE id=?", (row["id"],))
        db.commit()
    db.close()
    await reply(update,
        f"╔══════════════════════╗\n"
        f"║  ✅ <b>WARN REMOVED</b>   ║\n"
        f"╚══════════════════════╝\n\n"
        f"👤 {user_link(target)}\n"
        f"✨ <i>1 warning has been lifted.</i>"
    )

@admin_only
@groups_only
async def resetwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    db = get_db()
    db.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?",
               (update.effective_chat.id, target.id))
    db.commit(); db.close()
    log_action(update.effective_chat.id, update.effective_user.id, "resetwarn", target.id)
    await reply(update,
        f"╔══════════════════════╗\n"
        f"║  🗑️ <b>WARNS RESET</b>    ║\n"
        f"╚══════════════════════╝\n\n"
        f"👤 {user_link(target)}\n"
        f"✨ <i>All {html.escape(target.first_name or str(target.id))}'s warnings cleared!</i>"
    )

async def warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context) or update.effective_user
    cfg = get_chat(update.effective_chat.id)
    db = get_db()
    rows = db.execute("SELECT * FROM warns WHERE chat_id=? AND user_id=? ORDER BY warned_at DESC",
                      (update.effective_chat.id, target.id)).fetchall()
    db.close()
    warn_limit = cfg.get("warn_limit", 3)
    if not rows:
        return await reply(update,
            f"╔══════════════════════╗\n"
            f"║    ✅ <b>NO WARNINGS</b>    ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 {user_link(target)} is clean! 🌟"
        )
    bar = progress_bar(len(rows), warn_limit)
    lines = [
        f"╔══════════════════════╗\n"
        f"║   ⚠️ <b>WARN HISTORY</b>    ║\n"
        f"╚══════════════════════╝\n\n"
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"🔢 <b>Warns:</b> {len(rows)}/{warn_limit}\n"
        f"[{bar}]\n━━━━━━━━━━━━━━━━━━━━━"
    ]
    for i, w in enumerate(rows[:10], 1):
        lines.append(f"\n{i}. 📝 {html.escape(w['reason'] or 'No reason')}\n"
                     f"   🕐 <i>{str(w['warned_at'])[:16]}</i>")
    await reply(update, "\n".join(lines))

# ─── SETWARN SETTINGS ─────────────────────────────────────────────────────────
@admin_only
async def setwarnlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/setwarnlimit N</code>")
    try: n = int(context.args[0])
    except ValueError: return await reply(update, "❌ Invalid number.")
    set_setting(update.effective_chat.id, "warn_limit", n)
    await reply(update, f"✅ <b>Warn limit set to {n}!</b>")

@admin_only
async def setwarnaction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ("mute", "ban", "kick"):
        return await reply(update, "❓ <b>Usage:</b> <code>/setwarnaction mute|ban|kick</code>")
    set_setting(update.effective_chat.id, "warn_action", context.args[0])
    await reply(update, f"✅ <b>Warn action:</b> <code>{context.args[0]}</code>")

# ─── PROMOTE / DEMOTE ─────────────────────────────────────────────────────────
@admin_only
@groups_only
async def promote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>You need promote rights!</b>")
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    title = (" ".join(context.args) if update.message.reply_to_message and context.args
             else " ".join(context.args[1:]) if context.args else "")
    m = await animate_loading(update, "Promoting user")
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, target.id,
            can_manage_chat=True, can_delete_messages=True, can_restrict_members=True,
            can_invite_users=True, can_pin_messages=True, can_manage_video_chats=True,
            is_anonymous=False
        )
        if title:
            await context.bot.set_chat_administrator_custom_title(
                update.effective_chat.id, target.id, title[:16])
        log_action(update.effective_chat.id, update.effective_user.id, "promote", target.id, title)
        await finish_anim(m,
            f"╔══════════════════════╗\n"
            f"║   ⬆️ <b>USER PROMOTED</b>    ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👑 <b>Title:</b> {html.escape(title) if title else 'Admin'}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎖️ <i>User is now an admin!</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def demote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    m = await animate_loading(update, "Demoting user")
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, target.id,
            can_manage_chat=False, can_delete_messages=False, can_restrict_members=False,
            can_invite_users=False, can_pin_messages=False
        )
        log_action(update.effective_chat.id, update.effective_user.id, "demote", target.id)
        await finish_anim(m,
            f"╔══════════════════════╗\n"
            f"║   ⬇️ <b>USER DEMOTED</b>    ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📉 <i>Admin rights removed.</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def admintitle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    title = (" ".join(context.args) if update.message.reply_to_message
             else " ".join(context.args[1:]) if context.args else "")
    if not title: return await reply(update, "❓ <b>Provide a title.</b> <code>/admintitle Title Here</code>")
    try:
        await context.bot.set_chat_administrator_custom_title(
            update.effective_chat.id, target.id, title[:16])
        await reply(update,
            f"╔══════════════════════╗\n"
            f"║  🏷️ <b>TITLE SET!</b>    ║\n"
            f"╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"🏅 <b>Title:</b> <b>{html.escape(title)}</b>"
        )
    except BadRequest as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def adminlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Fetching admin list")
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        owners = [a for a in admins if a.status == "creator"]
        mods   = [a for a in admins if a.status == "administrator"]
        lines  = [f"╔══════════════════════╗\n║  👮 <b>ADMIN LIST ({len(admins)})</b>  ║\n╚══════════════════════╝\n"]
        if owners:
            lines.append("━━━ 👑 <b>Owner</b> ━━━━━━━━━━━━")
            for a in owners:
                lines.append(f"👑 <a href='tg://user?id={a.user.id}'>{html.escape(a.user.first_name or str(a.user.id))}</a>")
        if mods:
            lines.append("\n━━━ 🔧 <b>Admins</b> ━━━━━━━━━━━")
            for a in mods:
                name = html.escape(a.user.first_name or str(a.user.id))
                t = (f" — <i>{html.escape(a.custom_title)}</i>"
                     if isinstance(a, ChatMemberAdministrator) and a.custom_title else "")
                lines.append(f"🔧 <a href='tg://user?id={a.user.id}'>{name}</a>{t}")
        await finish_anim(m, "\n".join(lines))
    except Exception as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

# ─── TAG ADMINS ───────────────────────────────────────────────────────────────
async def tag_admins_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    if "@admins" not in update.message.text.lower() and "@admin" not in update.message.text.lower(): return
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        mentions = " ".join(f'<a href="tg://user?id={a.user.id}">​</a>'
                           for a in admins if not a.user.is_bot)
        await reply(update, f"📢 <b>Admins notified!</b>\n{mentions}")
    except: pass

# ─── ZOMBIES ──────────────────────────────────────────────────────────────────
@admin_only
@groups_only
async def zombies_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Scanning for zombie accounts")
    try:
        count = 0
        async for member in context.bot.get_chat_members(update.effective_chat.id):
            if member.user.is_deleted: count += 1
        await finish_anim(m,
            f"╔══════════════════════╗\n"
            f"║   🧟 <b>ZOMBIE SCAN</b>    ║\n"
            f"╚══════════════════════╝\n\n"
            f"🔍 Scan complete!\n"
            f"🧟 <b>Zombies found:</b> {count}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{'💀 Use /kickzombies to remove them!' if count else '✨ Group is zombie-free!'}"
        )
    except Exception as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def kickzombies_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    m = await animate_loading(update, "Hunting zombies")
    try:
        kicked = 0
        async for member in context.bot.get_chat_members(update.effective_chat.id):
            if member.user.is_deleted:
                try:
                    await context.bot.ban_chat_member(update.effective_chat.id, member.user.id)
                    await context.bot.unban_chat_member(update.effective_chat.id, member.user.id)
                    kicked += 1
                except: pass
        log_action(update.effective_chat.id, update.effective_user.id, "kickzombies", extra=str(kicked))
        await finish_anim(m,
            f"╔══════════════════════╗\n"
            f"║  ✅ <b>ZOMBIES PURGED</b>   ║\n"
            f"╚══════════════════════╝\n\n"
            f"💥 <b>Kicked {kicked} zombie accounts!</b>\n"
            f"🌟 <i>Group is now clean!</i>"
        )
    except Exception as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

# ─── PIN ──────────────────────────────────────────────────────────────────────
@admin_only
@groups_only
async def pin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_pin(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    if not update.message.reply_to_message:
        return await reply(update, "❓ <b>Reply to a message to pin it!</b>")
    loud = "loud" in (context.args or [])
    try:
        await context.bot.pin_chat_message(update.effective_chat.id,
                                           update.message.reply_to_message.message_id,
                                           disable_notification=not loud)
        await reply(update, "📌 <b>Message pinned!</b>" + (" 🔔 <i>Notified!</i>" if loud else ""))
    except BadRequest as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def unpin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_pin(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    try:
        if update.message.reply_to_message:
            await context.bot.unpin_chat_message(update.effective_chat.id,
                                                  update.message.reply_to_message.message_id)
        else:
            await context.bot.unpin_chat_message(update.effective_chat.id)
        await reply(update, "📌 <b>Message unpinned!</b>")
    except BadRequest as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def unpinall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_pin(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    m = await animate_loading(update, "Unpinning all messages")
    try:
        await context.bot.unpin_all_chat_messages(update.effective_chat.id)
        await finish_anim(m, "✅ <b>All messages unpinned!</b>")
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

# ─── PURGE / DEL ──────────────────────────────────────────────────────────────
@admin_only
@groups_only
async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    msg = update.message
    if not msg.reply_to_message:
        return await reply(update, "❓ <b>Reply to the first message you want to purge from!</b>")
    from_id = msg.reply_to_message.message_id
    to_id   = msg.message_id
    ids     = list(range(from_id, to_id + 1))
    m = await context.bot.send_message(update.effective_chat.id,
        f"🗑️ <b>Purging {len(ids)} messages...</b>\n[{progress_bar(0, len(ids))}]",
        parse_mode="HTML")
    count = 0
    for i in range(0, len(ids), 100):
        chunk = ids[i:i+100]
        try:
            await context.bot.delete_messages(update.effective_chat.id, chunk)
            count += len(chunk)
        except:
            for mid in chunk:
                try:
                    await context.bot.delete_message(update.effective_chat.id, mid)
                    count += 1
                except: pass
        try:
            await m.edit_text(
                f"🗑️ <b>Purging...</b> [{progress_bar(min(i+100, len(ids)), len(ids))}]\n"
                f"<i>{min(i+100, len(ids))}/{len(ids)} deleted</i>",
                parse_mode="HTML")
        except: pass
    try:
        await m.edit_text(
            f"╔══════════════════════╗\n║   🗑️ <b>PURGE COMPLETE</b>  ║\n╚══════════════════════╝\n\n"
            f"✅ <b>Deleted {count} messages!</b>",
            parse_mode="HTML")
        await asyncio.sleep(3)
        await m.delete()
    except: pass

@admin_only
async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await reply(update, "❓ <b>Reply to a message to delete it!</b>")
    try:
        await update.message.reply_to_message.delete()
        await update.message.delete()
    except: pass

# ─── SLOWMODE ─────────────────────────────────────────────────────────────────
@admin_only
@groups_only
async def slowmode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    seconds = 0
    if context.args:
        try: seconds = int(context.args[0])
        except: return await reply(update, "❌ <b>Invalid number.</b>")
    try:
        await context.bot.set_chat_slow_mode_delay(update.effective_chat.id, seconds)
        if seconds == 0:
            await reply(update, "✅ <b>Slowmode disabled!</b>")
        else:
            await reply(update,
                f"╔══════════════════════╗\n"
                f"║  🐢 <b>SLOWMODE SET</b>  ║\n"
                f"╚══════════════════════╝\n\n"
                f"⏱️ <b>Delay:</b> {seconds}s per message\n"
                f"✅ <i>Members must wait {seconds}s between messages.</i>"
            )
    except BadRequest as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

# ═══════════════════════════════════════════════════════════════════════════════
#                     🔒 LOCK SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
LOCK_TYPES = {
    "stickers": "lock_stickers", "gifs": "lock_gifs", "media": "lock_media",
    "polls": "lock_polls", "inline": "lock_inline", "bots": "lock_bots",
    "forward": "lock_forward", "games": "lock_games", "voice": "lock_voice",
    "video": "lock_video", "document": "lock_document", "all": "lock_all",
    "preview": "lock_preview", "url": "lock_url", "anon": "lock_anon"
}
LOCK_ICONS = {
    "stickers":"🪄","gifs":"🎭","media":"🖼️","polls":"📊","inline":"🤖",
    "bots":"🤖","forward":"↩️","games":"🎮","voice":"🎙️","video":"🎥",
    "document":"📄","all":"🔒","preview":"🔍","url":"🔗","anon":"👻"
}

@admin_only
@groups_only
async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, f"❓ <b>Usage:</b> <code>/lock {'|'.join(list(LOCK_TYPES.keys())[:5])}...</code>\n"
                           f"Or use <code>/locks</code> for the interactive panel!")
    t = context.args[0].lower()
    if t not in LOCK_TYPES:
        return await reply(update, f"❌ <b>Unknown type.</b> Use: <code>{', '.join(LOCK_TYPES.keys())}</code>")
    set_setting(update.effective_chat.id, LOCK_TYPES[t], 1)
    icon = LOCK_ICONS.get(t, "🔒")
    await reply(update,
        f"╔══════════════════════╗\n║  {icon} <b>LOCKED: {t.upper()}</b>  ║\n╚══════════════════════╝\n\n"
        f"🚫 <i>{t.title()} are now blocked in this chat.</i>"
    )

@admin_only
@groups_only
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, f"❓ <b>Usage:</b> <code>/unlock type</code>")
    t = context.args[0].lower()
    if t not in LOCK_TYPES:
        return await reply(update, f"❌ <b>Unknown type.</b>")
    set_setting(update.effective_chat.id, LOCK_TYPES[t], 0)
    icon = LOCK_ICONS.get(t, "🔓")
    await reply(update,
        f"╔══════════════════════╗\n║  {icon} <b>UNLOCKED: {t.upper()}</b>  ║\n╚══════════════════════╝\n\n"
        f"✅ <i>{t.title()} are now allowed.</i>"
    )

async def locks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interactive lock panel with toggle buttons."""
    cfg = get_chat(update.effective_chat.id)
    if not cfg:
        ensure_chat(update.effective_chat)
        cfg = get_chat(update.effective_chat.id)
    text = (
        f"╔══════════════════════════╗\n"
        f"║      🔒 <b>LOCK PANEL</b>       ║\n"
        f"╠══════════════════════════╣\n"
        f"║  Tap to toggle each lock  ║\n"
        f"╚══════════════════════════╝\n"
        f"<i>🟢 = Allowed • 🔴 = Locked</i>"
    )
    kb = _build_locks_kb(cfg)
    if update.callback_query:
        try: await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except: pass
    else:
        await reply(update, text, reply_markup=kb)

def _build_locks_kb(cfg: dict) -> InlineKeyboardMarkup:
    lock_pairs = list(LOCK_TYPES.items())
    rows = []
    for i in range(0, len(lock_pairs), 2):
        row = []
        for name, key in lock_pairs[i:i+2]:
            val = cfg.get(key, 0)
            icon = LOCK_ICONS.get(name, "🔒")
            state = "🔴" if val else "🟢"
            row.append(InlineKeyboardButton(f"{state} {icon} {name}", callback_data=f"lock_toggle:{name}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("🔓 Unlock ALL", callback_data="lock_all_off"),
                 InlineKeyboardButton("🔒 Lock ALL", callback_data="lock_all_on")])
    return InlineKeyboardMarkup(rows)

async def lock_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not await is_admin(context, q.message.chat_id, q.from_user.id):
        return await q.answer("🚫 Admins only!", show_alert=True)
    await q.answer()
    parts = q.data.split(":")
    if parts[0] == "lock_all_on":
        db = get_db()
        for key in LOCK_TYPES.values():
            db.execute(f"UPDATE chats SET {key}=1 WHERE chat_id=?", (q.message.chat_id,))
        db.commit(); db.close()
    elif parts[0] == "lock_all_off":
        db = get_db()
        for key in LOCK_TYPES.values():
            db.execute(f"UPDATE chats SET {key}=0 WHERE chat_id=?", (q.message.chat_id,))
        db.commit(); db.close()
    else:
        lock_name = parts[1]
        key = LOCK_TYPES.get(lock_name)
        if key:
            cfg = get_chat(q.message.chat_id)
            new_val = 0 if cfg.get(key, 0) else 1
            set_setting(q.message.chat_id, key, new_val)
    # Refresh panel
    cfg = get_chat(q.message.chat_id)
    kb = _build_locks_kb(cfg)
    try:
        await q.edit_message_reply_markup(reply_markup=kb)
    except: pass

# ═══════════════════════════════════════════════════════════════════════════════
#                    👋 WELCOME / GOODBYE / RULES
# ═══════════════════════════════════════════════════════════════════════════════
def format_welcome(text: str, user: User, chat: Chat, count: int = 0) -> str:
    name = html.escape(user.first_name or "")
    last = html.escape(user.last_name or "")
    username = f"@{user.username}" if user.username else name
    mention  = mention_html(user.id, name)
    return (text
            .replace("{first}", name).replace("{last}", last)
            .replace("{username}", username).replace("{mention}", mention)
            .replace("{chatname}", html.escape(chat.title or ""))
            .replace("{id}", str(user.id)).replace("{count}", str(count)))

async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    ensure_chat(chat)
    cfg = get_chat(chat.id)
    members = update.message.new_chat_members if update.message else []
    if not members: return

    if cfg.get("clean_service"):
        try: await update.message.delete()
        except: pass

    if not cfg.get("greetmembers", 1): return

    try:
        count = await context.bot.get_chat_member_count(chat.id)
    except:
        count = 0

    for user in members:
        ensure_user(user); track_member(chat.id, user)
        if user.is_bot:
            if cfg.get("anti_bot"):
                try:
                    await context.bot.ban_chat_member(chat.id, user.id)
                    await context.bot.unban_chat_member(chat.id, user.id)
                except: pass
            continue

        reason = is_gbanned(user.id)
        if reason:
            try:
                await context.bot.ban_chat_member(chat.id, user.id)
                await context.bot.send_message(chat.id,
                    f"🌍 <b>Globally banned user removed!</b>\n"
                    f"👤 {user_link(user)}\n📝 Reason: {html.escape(reason)}",
                    parse_mode="HTML")
            except: pass
            continue

        if cfg.get("anti_raid"):
            raid_tracker[chat.id].append(time.time())
            threshold = cfg.get("raid_threshold", 10)
            recent = [t for t in raid_tracker[chat.id] if time.time() - t < 60]
            if len(recent) >= threshold:
                try:
                    await context.bot.ban_chat_member(chat.id, user.id)
                    await context.bot.unban_chat_member(chat.id, user.id)
                    await context.bot.send_message(chat.id,
                        "🚨 <b>ANTI-RAID ACTIVATED!</b>\n⚡ Suspicious join spike! Member removed.",
                        parse_mode="HTML")
                except: pass
                continue

        if cfg.get("restrict_new_members"):
            dur = cfg.get("new_member_mute_duration", 300)
            until = datetime.datetime.now(pytz.utc) + datetime.timedelta(seconds=dur)
            try: await context.bot.restrict_chat_member(chat.id, user.id, MUTE_PERMS, until_date=until)
            except: pass

        # CAPTCHA system
        if cfg.get("welcome_captcha"):
            num1 = random.randint(1, 10)
            num2 = random.randint(1, 10)
            answer = num1 + num2
            wrong1 = answer + random.randint(1, 5)
            wrong2 = answer - random.randint(1, 5)
            captcha_cache[(chat.id, user.id)] = {"answer": answer, "joined": time.time()}
            await context.bot.restrict_chat_member(chat.id, user.id, MUTE_PERMS)
            options = sorted([answer, wrong1, abs(wrong2)])
            random.shuffle(options)
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton(str(o), callback_data=f"captcha:{chat.id}:{user.id}:{o}:{answer}")
                for o in options
            ]])
            await context.bot.send_message(chat.id,
                f"🔐 <b>VERIFY YOU'RE HUMAN</b>\n\n"
                f"Welcome {user_link(user)}!\n"
                f"Solve: <b>{num1} + {num2} = ?</b>",
                parse_mode="HTML", reply_markup=kb)
            continue

        welcome = cfg.get("welcome_msg") or (
            "╔══════════════════════════╗\n"
            "║   👋 <b>WELCOME!</b>         ║\n"
            "╚══════════════════════════╝\n\n"
            "🌟 Hey {mention}!\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Welcome to <b>{chatname}</b>! 🎉\n"
            "👥 You're member <b>#{count}</b>!\n"
            "<i>Read the /rules and enjoy!</i>"
        )
        text = format_welcome(welcome, user, chat, count)
        kb = parse_buttons(cfg.get("welcome_buttons", "[]"))
        try:
            m = await context.bot.send_message(chat.id, text, parse_mode="HTML",
                                               reply_markup=InlineKeyboardMarkup(kb) if kb else None)
            delay = cfg.get("welcome_delete_after", 0)
            if delay and delay > 0:
                async def _del_later(m=m, delay=delay):
                    await asyncio.sleep(delay)
                    try: await m.delete()
                    except: pass
                asyncio.create_task(_del_later())
        except Exception as ex:
            logger.debug(f"Welcome error: {ex}")

async def captcha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    if len(parts) < 5: return await q.answer("Invalid", show_alert=True)
    _, chat_id, user_id, given, correct = parts
    chat_id = int(chat_id); user_id = int(user_id)
    given = int(given); correct = int(correct)
    if q.from_user.id != user_id:
        return await q.answer("❌ This is not for you!", show_alert=True)
    await q.answer()
    if given == correct:
        captcha_cache.pop((chat_id, user_id), None)
        try:
            await context.bot.restrict_chat_member(chat_id, user_id, UNMUTE_PERMS)
            await q.edit_message_text(
                f"✅ <b>Verified! Welcome!</b>\n"
                f"👤 {user_link(q.from_user)} passed the captcha!",
                parse_mode="HTML")
        except: pass
    else:
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await q.edit_message_text(
                f"❌ <b>Wrong answer! {user_link(q.from_user)} was removed.</b>",
                parse_mode="HTML")
        except: pass

async def goodbye_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not update.message.left_chat_member: return
    user = update.message.left_chat_member
    cfg = get_chat(chat.id)
    if cfg.get("clean_service"):
        try: await update.message.delete()
        except: pass
    if not cfg.get("goodbye_enabled", 1): return
    goodbye = cfg.get("goodbye_msg") or (
        "╔══════════════════════════╗\n"
        "║   👋 <b>GOODBYE!</b>         ║\n"
        "╚══════════════════════════╝\n\n"
        "😢 <b>{first}</b> has left.\n"
        "We'll miss you! Come back soon! 💙"
    )
    text = format_welcome(goodbye, user, chat)
    try: await context.bot.send_message(chat.id, text, parse_mode="HTML")
    except: pass

@admin_only
@groups_only
async def setwelcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and not (update.message.reply_to_message and update.message.reply_to_message.text):
        return await reply(update,
            "╔══════════════════════╗\n║  👋 <b>SET WELCOME</b>    ║\n╚══════════════════════╝\n\n"
            "<b>Usage:</b> <code>/setwelcome Your text here</code>\n\n"
            "<b>Placeholders:</b>\n"
            "<code>{mention}</code> <code>{first}</code> <code>{last}</code>\n"
            "<code>{username}</code> <code>{chatname}</code> <code>{count}</code>"
        )
    text = " ".join(context.args) if context.args else update.message.reply_to_message.text
    set_setting(update.effective_chat.id, "welcome_msg", text)
    await reply(update, "✅ <b>Welcome message updated!</b>\n<i>New members will see your custom message.</i>")

@admin_only
@groups_only
async def setgoodbye_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    if not text and update.message.reply_to_message:
        text = update.message.reply_to_message.text or ""
    if not text: return await reply(update, "❓ <b>Usage:</b> <code>/setgoodbye Your text</code>")
    set_setting(update.effective_chat.id, "goodbye_msg", text)
    await reply(update, "✅ <b>Goodbye message updated!</b>")

@admin_only
async def welcome_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "greetmembers", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Welcome {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def goodbye_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "goodbye_enabled", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Goodbye {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def captcha_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "welcome_captcha", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Captcha verification {'enabled' if val else 'disabled'}!</b>")

@admin_only
@groups_only
async def setrules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    if not text and update.message.reply_to_message:
        text = update.message.reply_to_message.text or ""
    if not text: return await reply(update, "❓ <b>Usage:</b> <code>/setrules Your rules here</code>")
    set_setting(update.effective_chat.id, "rules_text", text)
    await reply(update, "✅ <b>Rules updated!</b>")

async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules = get_setting(update.effective_chat.id, "rules_text", "")
    if not rules:
        return await reply(update,
            "📜 <b>No rules set yet!</b>\n"
            "<i>Admins can use /setrules to set the group rules.</i>")
    title = html.escape((update.effective_chat.title or "")[:15])
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ I Accept the Rules", callback_data="rules_accept")]])
    await reply(update,
        f"╔═══════════════════════════════╗\n"
        f"║  📜 <b>RULES — {title}</b>  ║\n"
        f"╚═══════════════════════════════╝\n\n"
        f"{html.escape(rules)}",
        reply_markup=kb
    )

async def rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer("✅ You accepted the rules!", show_alert=False)

@admin_only
async def welcdel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/welcdel seconds</code>")
    try: secs = int(context.args[0])
    except: return await reply(update, "❌ Invalid number.")
    set_setting(update.effective_chat.id, "welcome_delete_after", secs)
    if secs == 0:
        await reply(update, "✅ <b>Welcome auto-delete disabled!</b>")
    else:
        await reply(update, f"✅ <b>Welcome messages auto-delete after {secs}s!</b>")

# ═══════════════════════════════════════════════════════════════════════════════
#                         📝 NOTES
# ═══════════════════════════════════════════════════════════════════════════════
@admin_only
async def save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await reply(update, "❓ <b>Usage:</b> <code>/save name content</code>")
    name = context.args[0].lower()
    content = " ".join(context.args[1:])
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("INSERT OR REPLACE INTO notes (chat_id, name, content, created_by) VALUES (?,?,?,?)",
               (chat_id, name, content, update.effective_user.id))
    db.commit(); db.close()
    await reply(update,
        f"╔══════════════════════╗\n║   📝 <b>NOTE SAVED!</b>   ║\n╚══════════════════════╝\n\n"
        f"🔖 <b>Name:</b> <code>#{name}</code>\n"
        f"💾 Use <code>/get {name}</code> or <code>#{name}</code> to retrieve!"
    )

async def get_note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/get name</code>")
    await _send_note(update, context, context.args[0].lower())

async def _send_note(update, context, name):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    row = db.execute("SELECT * FROM notes WHERE chat_id=? AND name=?", (chat_id, name)).fetchone()
    db.close()
    if not row: return await reply(update, f"❌ <b>Note <code>#{name}</code> not found!</b>")
    content = row["content"] or ""
    kb = parse_buttons(row["buttons"] or "[]")
    await reply(update, content, reply_markup=InlineKeyboardMarkup(kb) if kb else None)

async def hash_note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    for word in update.message.text.split():
        if word.startswith("#") and len(word) > 1:
            await _send_note(update, context, word[1:].lower())
            return

async def notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    rows = db.execute("SELECT name FROM notes WHERE chat_id=? ORDER BY name", (chat_id,)).fetchall()
    db.close()
    if not rows:
        return await reply(update,
            "╔══════════════════════╗\n║    📝 <b>NO NOTES</b>     ║\n╚══════════════════════╝\n\n"
            "<i>No notes yet. Use /save to create one!</i>")
    # Build button grid
    note_buttons = []
    row = []
    for i, r in enumerate(rows):
        row.append(InlineKeyboardButton(f"#{r['name']}", callback_data=f"getnote:{r['name']}"))
        if len(row) == 3:
            note_buttons.append(row); row = []
    if row: note_buttons.append(row)
    kb = InlineKeyboardMarkup(note_buttons)
    await reply(update,
        f"╔══════════════════════╗\n║  📝 <b>NOTES ({len(rows)})</b>  ║\n╚══════════════════════╝\n\n"
        f"Tap a note button to retrieve it:",
        reply_markup=kb)

async def note_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    name = q.data.split(":", 1)[1]
    chat_id = q.message.chat_id
    db = get_db()
    row = db.execute("SELECT * FROM notes WHERE chat_id=? AND name=?", (chat_id, name)).fetchone()
    db.close()
    if not row:
        await q.message.reply_text(f"❌ <b>Note #{name} not found!</b>", parse_mode="HTML")
        return
    content = row["content"] or ""
    kb = parse_buttons(row["buttons"] or "[]")
    await q.message.reply_text(content, parse_mode="HTML",
                               reply_markup=InlineKeyboardMarkup(kb) if kb else None)

@admin_only
async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/clear name</code>")
    name = context.args[0].lower()
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM notes WHERE chat_id=? AND name=?", (chat_id, name))
    db.commit(); db.close()
    await reply(update, f"🗑️ <b>Note <code>#{name}</code> deleted!</b>")

@admin_only
async def clearall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM notes WHERE chat_id=?", (chat_id,))
    db.commit(); db.close()
    await reply(update, "🗑️ <b>All notes deleted!</b>")

# ═══════════════════════════════════════════════════════════════════════════════
#                         🔍 FILTERS
# ═══════════════════════════════════════════════════════════════════════════════
@admin_only
async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await reply(update, "❓ <b>Usage:</b> <code>/filter keyword reply</code>\n"
                           "<i>For regex: /filter regex:pattern reply</i>")
    keyword = context.args[0].lower()
    is_regex = keyword.startswith("regex:")
    if is_regex: keyword = keyword[6:]
    reply_text = " ".join(context.args[1:])
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("INSERT OR REPLACE INTO filters (chat_id, keyword, reply, is_regex, created_by) VALUES (?,?,?,?,?)",
               (chat_id, keyword, reply_text, 1 if is_regex else 0, update.effective_user.id))
    db.commit(); db.close()
    await reply(update,
        f"✅ <b>Filter added!</b>\n"
        f"🔑 <b>Keyword:</b> <code>{html.escape(keyword)}</code>\n"
        f"{'🔢 Regex mode' if is_regex else '📝 Exact match'}"
    )

async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    rows = db.execute("SELECT keyword, is_regex FROM filters WHERE chat_id=? ORDER BY keyword",
                      (chat_id,)).fetchall()
    db.close()
    if not rows: return await reply(update, "❌ <b>No filters active.</b>")
    lines = ["╔══════════════════════╗\n║  🔍 <b>ACTIVE FILTERS</b>  ║\n╚══════════════════════╝\n"]
    for r in rows:
        lines.append(f"{'🔢' if r['is_regex'] else '🔑'} <code>{html.escape(r['keyword'])}</code>")
    await reply(update, "\n".join(lines))

@admin_only
async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/stop keyword</code>")
    keyword = context.args[0].lower()
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM filters WHERE chat_id=? AND keyword=?", (chat_id, keyword))
    db.commit(); db.close()
    await reply(update, f"✅ <b>Filter removed:</b> <code>{html.escape(keyword)}</code>")

@admin_only
async def stopall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM filters WHERE chat_id=?", (chat_id,))
    db.commit(); db.close()
    await reply(update, "✅ <b>All filters removed!</b>")

async def filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text.lower()
    chat_id = update.effective_chat.id
    db = get_db()
    rows = db.execute("SELECT * FROM filters WHERE chat_id=?", (chat_id,)).fetchall()
    db.close()
    for row in rows:
        matched = False
        if row["is_regex"]:
            try: matched = bool(re.search(row["keyword"], text, re.IGNORECASE))
            except: pass
        else:
            matched = row["keyword"] in text
        if matched:
            content = row["reply"] or ""
            kb = parse_buttons(row["buttons"] or "[]")
            await reply(update, content, reply_markup=InlineKeyboardMarkup(kb) if kb else None)
            return

# ═══════════════════════════════════════════════════════════════════════════════
#                         🚫 BLACKLIST
# ═══════════════════════════════════════════════════════════════════════════════
@admin_only
async def addbl_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/addbl word</code>")
    word = " ".join(context.args).lower()
    is_regex = word.startswith("regex:")
    if is_regex: word = word[6:]
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("INSERT OR IGNORE INTO blacklist (chat_id, word, is_regex, added_by) VALUES (?,?,?,?)",
               (chat_id, word, 1 if is_regex else 0, update.effective_user.id))
    db.commit(); db.close()
    await reply(update, f"🚫 <b>Added to blacklist:</b> <code>{html.escape(word)}</code>")

@admin_only
async def unblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/rmbl word</code>")
    word = " ".join(context.args).lower()
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM blacklist WHERE chat_id=? AND word=?", (chat_id, word))
    db.commit(); db.close()
    await reply(update, f"✅ <b>Removed from blacklist:</b> <code>{html.escape(word)}</code>")

async def blacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    rows = db.execute("SELECT word, is_regex FROM blacklist WHERE chat_id=? ORDER BY word",
                      (chat_id,)).fetchall()
    db.close()
    if not rows: return await reply(update, "✅ <b>Blacklist is empty!</b>")
    lines = ["╔══════════════════════╗\n║    🚫 <b>BLACKLIST</b>     ║\n╚══════════════════════╝\n"]
    for r in rows:
        lines.append(f"• <code>{html.escape(r['word'])}</code>" + (" <i>(regex)</i>" if r["is_regex"] else ""))
    await reply(update, "\n".join(lines))

@admin_only
async def blacklistmode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ("delete", "warn", "mute", "ban"):
        return await reply(update, "❓ <b>Usage:</b> <code>/blmode delete|warn|mute|ban</code>")
    set_setting(update.effective_chat.id, "blacklist_action", context.args[0])
    await reply(update, f"✅ <b>Blacklist action:</b> <code>{context.args[0]}</code>")

async def blacklist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    if await is_admin(context, update.effective_chat.id, update.effective_user.id): return
    text = update.message.text.lower()
    chat_id = update.effective_chat.id
    db = get_db()
    rows = db.execute("SELECT * FROM blacklist WHERE chat_id=?", (chat_id,)).fetchall()
    db.close()
    cfg = get_chat(chat_id)
    action = cfg.get("blacklist_action", "delete")
    for row in rows:
        matched = False
        if row["is_regex"]:
            try: matched = bool(re.search(row["word"], text, re.IGNORECASE))
            except: pass
        else:
            matched = row["word"] in text
        if matched:
            try: await update.message.delete()
            except: pass
            if action == "warn":
                await _warn(update, context, silent=True)
            elif action == "mute":
                await context.bot.restrict_chat_member(chat_id, update.effective_user.id, MUTE_PERMS)
            elif action == "ban":
                await _do_ban(context, chat_id, update.effective_user.id)
            return

# ═══════════════════════════════════════════════════════════════════════════════
#                     🛡️ ANTI-SPAM / FLOOD / PROTECTION
# ═══════════════════════════════════════════════════════════════════════════════
async def antispam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user: return
    chat_id  = update.effective_chat.id
    user_id  = update.effective_user.id
    cfg      = get_chat(chat_id)
    if await is_admin(context, chat_id, user_id): return

    # Anti-flood
    if cfg.get("anti_flood", 1):
        flood_count  = cfg.get("flood_count", 5)
        flood_time   = cfg.get("flood_time", 5)
        flood_action = cfg.get("flood_action", "mute")
        now = time.time()
        key = f"{chat_id}:{user_id}"
        flood_cache[key].append(now)
        recent = [t for t in flood_cache[key] if now - t < flood_time]
        if len(recent) >= flood_count:
            flood_cache[key].clear()
            try: await update.message.delete()
            except: pass
            action_text = "banned" if flood_action == "ban" else ("kicked" if flood_action == "kick" else "muted")
            if flood_action == "ban":
                await _do_ban(context, chat_id, user_id)
            elif flood_action == "kick":
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.unban_chat_member(chat_id, user_id)
            else:
                await context.bot.restrict_chat_member(chat_id, user_id, MUTE_PERMS)
            await context.bot.send_message(chat_id,
                f"⚡ <b>FLOOD DETECTED!</b>\n"
                f"👤 {user_link(update.effective_user)} was <b>{action_text}</b> for flooding!",
                parse_mode="HTML")
            return

    msg = update.message

    # Anti-link
    if cfg.get("anti_link") and msg.text:
        url_pat = r'(https?://|t\.me/|@\w+|tg://|bit\.ly|goo\.gl)'
        if re.search(url_pat, msg.text, re.IGNORECASE):
            try: await msg.delete()
            except: pass
            return

    # Anti-forward
    if cfg.get("anti_forward") and msg.forward_date:
        try: await msg.delete()
        except: pass
        return

    # Anti-Arabic / RTL
    if cfg.get("anti_arabic") and msg.text:
        if re.search(r'[\u0600-\u06FF\u200F\u202B]', msg.text):
            try: await msg.delete()
            except: pass
            return

    # Content locks
    async def _del():
        try: await msg.delete()
        except: pass

    if msg.sticker    and cfg.get("lock_stickers"):  await _del(); return
    if msg.animation  and cfg.get("lock_gifs"):       await _del(); return
    if (msg.photo or msg.video or msg.audio) and cfg.get("lock_media"): await _del(); return
    if msg.poll       and cfg.get("lock_polls"):      await _del(); return
    if msg.voice      and cfg.get("lock_voice"):      await _del(); return
    if msg.video_note and cfg.get("lock_video"):      await _del(); return
    if msg.document   and cfg.get("lock_document"):   await _del(); return
    if msg.forward_date and cfg.get("lock_forward"):  await _del(); return
    if msg.game       and cfg.get("lock_games"):      await _del(); return

    # Track message count
    db = get_db()
    db.execute("UPDATE users SET total_msgs=total_msgs+1 WHERE user_id=?", (user_id,))
    db.commit(); db.close()

# ─── PROTECTION SETTINGS ──────────────────────────────────────────────────────
@admin_only
async def protect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Interactive protection panel."""
    cfg = get_chat(update.effective_chat.id)
    if not cfg:
        ensure_chat(update.effective_chat)
        cfg = get_chat(update.effective_chat.id)
    text = (
        f"╔══════════════════════════╗\n"
        f"║   🛡️ <b>PROTECTION PANEL</b>   ║\n"
        f"╠══════════════════════════╣\n"
        f"║  Tap a button to toggle!  ║\n"
        f"╚══════════════════════════╝"
    )
    kb = _build_protect_kb(cfg)
    if update.callback_query:
        try: await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except: pass
    else:
        await reply(update, text, reply_markup=kb)

def _build_protect_kb(cfg: dict) -> InlineKeyboardMarkup:
    toggles = [
        ("🌊 Flood",   "anti_flood"),
        ("🔗 Links",   "anti_link"),
        ("↩️ Forward", "anti_forward"),
        ("🤖 Bot",     "anti_bot"),
        ("🚨 Raid",    "anti_raid"),
        ("🔞 NSFW",    "anti_nsfw"),
        ("🔤 Arabic",  "anti_arabic"),
        ("🛡️ CAS",    "cas_enabled"),
        ("🆕 Restrict","restrict_new_members"),
    ]
    rows = []
    for i in range(0, len(toggles), 2):
        row = []
        for label, key in toggles[i:i+2]:
            val = cfg.get(key, 0)
            state = "✅" if val else "❌"
            row.append(InlineKeyboardButton(f"{state} {label}", callback_data=f"protect_toggle:{key}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

async def protect_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not await is_admin(context, q.message.chat_id, q.from_user.id):
        return await q.answer("🚫 Admins only!", show_alert=True)
    await q.answer()
    key = q.data.split(":")[1]
    cfg = get_chat(q.message.chat_id)
    new_val = 0 if cfg.get(key, 0) else 1
    set_setting(q.message.chat_id, key, new_val)
    cfg = get_chat(q.message.chat_id)
    kb = _build_protect_kb(cfg)
    try: await q.edit_message_reply_markup(reply_markup=kb)
    except: pass

# Protection toggle commands
@admin_only
async def antispam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_spam", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-spam {'on' if val else 'off'}!</b>")

@admin_only
async def antiflood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_flood", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-flood {'on' if val else 'off'}!</b>")

@admin_only
async def setflood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/setflood N [seconds]</code>")
    try:
        n = int(context.args[0])
        t = int(context.args[1]) if len(context.args) > 1 else 5
    except ValueError:
        return await reply(update, "❌ Invalid numbers.")
    db = get_db()
    db.execute("UPDATE chats SET flood_count=?, flood_time=? WHERE chat_id=?",
               (n, t, update.effective_chat.id))
    db.commit(); db.close()
    await reply(update,
        f"✅ <b>Flood limit:</b> {n} msgs in {t}s\n"
        f"⚡ <i>Anti-flood updated!</i>"
    )

@admin_only
async def setfloodaction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ("mute","ban","kick"):
        return await reply(update, "❓ <b>Usage:</b> <code>/setfloodaction mute|ban|kick</code>")
    set_setting(update.effective_chat.id, "flood_action", context.args[0])
    await reply(update, f"✅ <b>Flood action:</b> <code>{context.args[0]}</code>")

@admin_only
async def antilink_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_link", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-link {'on' if val else 'off'}!</b>")

@admin_only
async def antiforward_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_forward", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-forward {'on' if val else 'off'}!</b>")

@admin_only
async def antibot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_bot", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-bot {'on' if val else 'off'}!</b>")

@admin_only
async def antinsfw_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_nsfw", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-NSFW {'on' if val else 'off'}!</b>")

@admin_only
async def antiarabic_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_arabic", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-Arabic/RTL {'on' if val else 'off'}!</b>")

@admin_only
async def antiraid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_raid", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-raid {'on' if val else 'off'}!</b>")

@admin_only
async def setraid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/setraid N</code>")
    try: n = int(context.args[0])
    except: return await reply(update, "❌ Invalid number.")
    set_setting(update.effective_chat.id, "raid_threshold", n)
    await reply(update, f"✅ <b>Raid threshold:</b> {n} joins/minute")

@admin_only
async def cas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "cas_enabled", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>CAS protection {'on' if val else 'off'}!</b>")

@admin_only
async def restrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "restrict_new_members", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>New member restriction {'on' if val else 'off'}!</b>")

# ─── REPORT ───────────────────────────────────────────────────────────────────
async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await reply(update, "❓ <b>Reply to a message to report it!</b>")
    cfg = get_chat(update.effective_chat.id)
    if not cfg.get("report_enabled", 1):
        return await reply(update, "❌ <b>Reports disabled in this chat.</b>")
    reported = update.message.reply_to_message.from_user
    reason   = " ".join(context.args) if context.args else "No reason"
    db = get_db()
    db.execute("INSERT INTO reports (chat_id, reporter_id, reported_id, message_id, reason) VALUES (?,?,?,?,?)",
               (update.effective_chat.id, update.effective_user.id, reported.id,
                update.message.reply_to_message.message_id, reason))
    db.commit(); db.close()
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        mentions = " ".join(f'<a href="tg://user?id={a.user.id}">​</a>' for a in admins if not a.user.is_bot)
    except: mentions = ""
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔨 Ban", callback_data=f"report_ban:{reported.id}"),
        InlineKeyboardButton("🔇 Mute", callback_data=f"report_mute:{reported.id}"),
        InlineKeyboardButton("👢 Kick", callback_data=f"report_kick:{reported.id}"),
    ], [
        InlineKeyboardButton("✅ Dismiss", callback_data=f"report_dismiss:{reported.id}"),
    ]])
    await reply(update,
        f"╔══════════════════════╗\n║  🚨 <b>USER REPORTED</b>   ║\n╚══════════════════════╝\n\n"
        f"👤 <b>Reported:</b> {user_link(reported)}\n"
        f"📢 <b>Reporter:</b> {user_link(update.effective_user)}\n"
        f"📝 <b>Reason:</b> {html.escape(reason)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👮 {mentions}",
        reply_markup=kb
    )

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not await is_admin(context, update.effective_chat.id, q.from_user.id):
        return await q.answer("🚫 Admins only!", show_alert=True)
    await q.answer()
    data = q.data
    if data.startswith("report_ban:"):
        uid = int(data.split(":")[1])
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, uid)
            await q.edit_message_reply_markup(reply_markup=None)
            await q.message.reply_text(f"🔨 <b>Banned by {user_link(q.from_user)}!</b>", parse_mode="HTML")
        except Exception as e: await q.message.reply_text(f"❌ {e}")
    elif data.startswith("report_mute:"):
        uid = int(data.split(":")[1])
        try:
            await context.bot.restrict_chat_member(update.effective_chat.id, uid, MUTE_PERMS)
            await q.edit_message_reply_markup(reply_markup=None)
            await q.message.reply_text(f"🔇 <b>Muted by {user_link(q.from_user)}!</b>", parse_mode="HTML")
        except Exception as e: await q.message.reply_text(f"❌ {e}")
    elif data.startswith("report_kick:"):
        uid = int(data.split(":")[1])
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, uid)
            await context.bot.unban_chat_member(update.effective_chat.id, uid)
            await q.edit_message_reply_markup(reply_markup=None)
            await q.message.reply_text(f"👢 <b>Kicked by {user_link(q.from_user)}!</b>", parse_mode="HTML")
        except Exception as e: await q.message.reply_text(f"❌ {e}")
    elif data.startswith("report_dismiss:"):
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(f"✅ <b>Report dismissed by {user_link(q.from_user)}.</b>", parse_mode="HTML")

# ═══════════════════════════════════════════════════════════════════════════════
#                         🌐 FEDERATION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
@groups_only
async def newfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>Admins only.</b>")
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/newfed Name</code>")
    name   = " ".join(context.args)
    fed_id = str(uuid.uuid4())[:8].upper()
    db = get_db()
    db.execute("INSERT INTO federations (fed_id, name, owner_id) VALUES (?,?,?)",
               (fed_id, name, update.effective_user.id))
    db.execute("INSERT OR IGNORE INTO federation_chats (fed_id, chat_id) VALUES (?,?)",
               (fed_id, update.effective_chat.id))
    db.execute("UPDATE chats SET fed_id=? WHERE chat_id=?", (fed_id, update.effective_chat.id))
    db.commit(); db.close()
    await reply(update,
        f"╔══════════════════════╗\n║  🌐 <b>FEDERATION CREATED!</b>  ║\n╚══════════════════════╝\n\n"
        f"📋 <b>Name:</b> {html.escape(name)}\n"
        f"🔑 <b>Fed ID:</b> <code>{fed_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Share the ID so other groups can /joinfed!</i>"
    )

async def joinfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>Only group owner can join a federation.</b>")
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/joinfed fed_id</code>")
    fed_id = context.args[0].upper()
    db = get_db()
    fed = db.execute("SELECT * FROM federations WHERE fed_id=?", (fed_id,)).fetchone()
    if not fed: db.close(); return await reply(update, "❌ <b>Federation not found!</b>")
    db.execute("INSERT OR IGNORE INTO federation_chats (fed_id, chat_id) VALUES (?,?)",
               (fed_id, update.effective_chat.id))
    db.execute("UPDATE chats SET fed_id=? WHERE chat_id=?", (fed_id, update.effective_chat.id))
    db.commit(); db.close()
    await reply(update,
        f"✅ <b>Joined federation: {html.escape(fed['name'])}!</b>\n"
        f"<i>Fed bans will now apply to this group.</i>"
    )

async def leavefed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>Only group owner can leave a federation.</b>")
    db = get_db()
    row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not row or not row["fed_id"]: db.close(); return await reply(update, "❌ <b>Not in a federation!</b>")
    db.execute("DELETE FROM federation_chats WHERE fed_id=? AND chat_id=?",
               (row["fed_id"], update.effective_chat.id))
    db.execute("UPDATE chats SET fed_id=NULL WHERE chat_id=?", (update.effective_chat.id,))
    db.commit(); db.close()
    await reply(update, "✅ <b>Left the federation!</b>")

async def fedinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_id = context.args[0].upper() if context.args else None
    if not fed_id:
        row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
        fed_id = row["fed_id"] if row else None
    if not fed_id: db.close(); return await reply(update, "❌ <b>No federation!</b>")
    fed = db.execute("SELECT * FROM federations WHERE fed_id=?", (fed_id,)).fetchone()
    if not fed: db.close(); return await reply(update, "❌ <b>Federation not found!</b>")
    chats = db.execute("SELECT COUNT(*) as c FROM federation_chats WHERE fed_id=?", (fed_id,)).fetchone()["c"]
    bans  = db.execute("SELECT COUNT(*) as c FROM federation_bans WHERE fed_id=?", (fed_id,)).fetchone()["c"]
    admins = db.execute("SELECT COUNT(*) as c FROM federation_admins WHERE fed_id=?", (fed_id,)).fetchone()["c"]
    db.close()
    await reply(update,
        f"╔══════════════════════╗\n║    🌐 <b>FED INFO</b>     ║\n╚══════════════════════╝\n\n"
        f"📋 <b>Name:</b> {html.escape(fed['name'])}\n"
        f"🔑 <b>ID:</b> <code>{fed_id}</code>\n"
        f"💬 <b>Chats:</b> {chats}\n"
        f"👮 <b>Admins:</b> {admins+1}\n"
        f"🚫 <b>Bans:</b> {bans}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Created: {str(fed['created_at'])[:10]}</i>"
    )

async def fban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]: db.close(); return await reply(update, "❌ <b>Not in a federation!</b>")
    fed_id = fed_row["fed_id"]
    fed = db.execute("SELECT * FROM federations WHERE fed_id=?", (fed_id,)).fetchone()
    is_fed_admin = (update.effective_user.id == fed["owner_id"] or
                    db.execute("SELECT 1 FROM federation_admins WHERE fed_id=? AND user_id=?",
                               (fed_id, update.effective_user.id)).fetchone() or
                    is_sudo(update.effective_user.id))
    if not is_fed_admin: db.close(); return await reply(update, "❌ <b>Not a federation admin!</b>")
    target = get_target(update, context)
    if not target: db.close(); return await reply(update, "❓ Reply to a user.")
    reason = " ".join(context.args) if context.args else "Federation ban"
    db.execute("INSERT OR REPLACE INTO federation_bans (fed_id, user_id, reason, banned_by) VALUES (?,?,?,?)",
               (fed_id, target.id, reason, update.effective_user.id))
    chats = db.execute("SELECT chat_id FROM federation_chats WHERE fed_id=?", (fed_id,)).fetchall()
    db.commit(); db.close()
    m = await animate_loading(update, "Applying federation ban")
    banned_in = 0
    for ch in chats:
        try: await context.bot.ban_chat_member(ch["chat_id"], target.id); banned_in += 1
        except: pass
    await finish_anim(m,
        f"╔══════════════════════╗\n║  🌐 <b>FED BAN APPLIED</b>  ║\n╚══════════════════════╝\n\n"
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"📝 <b>Reason:</b> {html.escape(reason)}\n"
        f"💬 <b>Banned in:</b> {banned_in} chats"
    )

async def unfban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]: db.close(); return await reply(update, "❌ <b>Not in a federation!</b>")
    fed_id = fed_row["fed_id"]
    target = get_target(update, context)
    if not target: db.close(); return await reply(update, "❓ Reply to a user.")
    db.execute("DELETE FROM federation_bans WHERE fed_id=? AND user_id=?", (fed_id, target.id))
    chats = db.execute("SELECT chat_id FROM federation_chats WHERE fed_id=?", (fed_id,)).fetchall()
    db.commit(); db.close()
    for ch in chats:
        try: await context.bot.unban_chat_member(ch["chat_id"], target.id, only_if_banned=True)
        except: pass
    await reply(update, f"✅ <b>Fed ban lifted for {user_link(target)}!</b>\n<i>Unbanned from all fed chats.</i>")

async def fedbans_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]: db.close(); return await reply(update, "❌ <b>Not in a federation!</b>")
    fed_id = fed_row["fed_id"]
    bans = db.execute(
        "SELECT fb.*, u.username, u.first_name FROM federation_bans fb "
        "LEFT JOIN users u ON u.user_id=fb.user_id WHERE fb.fed_id=? LIMIT 20",
        (fed_id,)).fetchall()
    db.close()
    if not bans: return await reply(update, "✅ <b>No federation bans!</b>")
    lines = [f"╔══════════════════════╗\n║  🌐 <b>FED BANS ({len(bans)})</b>  ║\n╚══════════════════════╝\n"]
    for b in bans:
        name = html.escape(b["first_name"] or str(b["user_id"]))
        lines.append(f"🚫 {name} — <i>{html.escape(b['reason'] or 'No reason')}</i>")
    await reply(update, "\n".join(lines))

async def fadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]: db.close(); return await reply(update, "❌ <b>Not in a federation!</b>")
    fed_id = fed_row["fed_id"]
    fed = db.execute("SELECT * FROM federations WHERE fed_id=?", (fed_id,)).fetchone()
    if update.effective_user.id != fed["owner_id"] and not is_sudo(update.effective_user.id):
        db.close(); return await reply(update, "❌ <b>Only federation owner can add admins!</b>")
    target = get_target(update, context)
    if not target: db.close(); return await reply(update, "❓ Reply to a user.")
    db.execute("INSERT OR IGNORE INTO federation_admins (fed_id, user_id) VALUES (?,?)", (fed_id, target.id))
    db.commit(); db.close()
    await reply(update, f"✅ <b>{user_link(target)} is now a federation admin!</b>")

async def fremove_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]: db.close(); return await reply(update, "❌ <b>Not in a federation!</b>")
    fed_id = fed_row["fed_id"]
    target = get_target(update, context)
    if not target: db.close(); return await reply(update, "❓ Reply to a user.")
    db.execute("DELETE FROM federation_admins WHERE fed_id=? AND user_id=?", (fed_id, target.id))
    db.commit(); db.close()
    await reply(update, f"✅ <b>{user_link(target)} removed from federation admins!</b>")

# ═══════════════════════════════════════════════════════════════════════════════
#                     🔗 CONNECTION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
async def connect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return await reply(update, "❓ <b>Use this in my DM!</b>")
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/connect chat_id</code>")
    m = await animate_loading(update, "Connecting to group")
    try:
        chat_id = int(context.args[0])
        if not await is_admin(context, chat_id, update.effective_user.id):
            return await finish_anim(m, "❌ <b>You must be an admin in that group!</b>")
        connection_cache[update.effective_user.id] = chat_id
        db = get_db()
        db.execute("INSERT OR REPLACE INTO connections (user_id, chat_id) VALUES (?,?)",
                   (update.effective_user.id, chat_id))
        db.commit(); db.close()
        chat_obj = await context.bot.get_chat(chat_id)
        await finish_anim(m,
            f"✅ <b>Connected to:</b> {html.escape(chat_obj.title or str(chat_id))}\n"
            f"<i>Use admin commands from your DM!</i>"
        )
    except Exception as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def disconnect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    connection_cache.pop(update.effective_user.id, None)
    db = get_db()
    db.execute("DELETE FROM connections WHERE user_id=?", (update.effective_user.id,))
    db.commit(); db.close()
    await reply(update, "🔌 <b>Disconnected!</b>")

async def connected_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = connection_cache.get(update.effective_user.id)
    if not cid:
        db = get_db()
        row = db.execute("SELECT chat_id FROM connections WHERE user_id=?",
                         (update.effective_user.id,)).fetchone()
        db.close()
        if row: cid = row["chat_id"]; connection_cache[update.effective_user.id] = cid
    if not cid: return await reply(update, "🔌 <b>Not connected.</b> Use /connect [chat_id]")
    try:
        chat = await context.bot.get_chat(cid)
        await reply(update, f"✅ <b>Connected to:</b> {html.escape(chat.title or str(cid))}\n🆔 <code>{cid}</code>")
    except:
        await reply(update, f"🔗 <b>Connected to:</b> <code>{cid}</code>")

# ═══════════════════════════════════════════════════════════════════════════════
#                         😴 AFK
# ═══════════════════════════════════════════════════════════════════════════════
async def afk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason  = " ".join(context.args) if context.args else ""
    user_id = update.effective_user.id
    afk_cache[user_id] = {"reason": reason, "since": datetime.datetime.now(pytz.utc)}
    db = get_db()
    db.execute("UPDATE users SET is_afk=1, afk_reason=?, afk_since=CURRENT_TIMESTAMP WHERE user_id=?",
               (reason, user_id))
    db.commit(); db.close()
    await reply(update,
        f"╔══════════════════════╗\n║    😴 <b>AFK MODE ON</b>   ║\n╚══════════════════════╝\n\n"
        f"👤 {user_link(update.effective_user)} is now AFK!\n"
        + (f"📝 <b>Reason:</b> {html.escape(reason)}" if reason else "💭 <i>No reason given.</i>")
    )

async def afk_check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user: return
    user_id = update.effective_user.id
    if user_id in afk_cache:
        afk_data = afk_cache.pop(user_id)
        db = get_db()
        db.execute("UPDATE users SET is_afk=0, afk_reason=NULL WHERE user_id=?", (user_id,))
        db.commit(); db.close()
        since = afk_data.get("since", datetime.datetime.now(pytz.utc))
        diff  = datetime.datetime.now(pytz.utc) - since
        mins  = int(diff.total_seconds() // 60)
        hrs   = mins // 60; mins %= 60
        time_str = f"{hrs}h {mins}m" if hrs else f"{mins}m"
        await reply(update, f"✅ <b>{user_link(update.effective_user)} is back!</b>\n⏱️ <i>Was AFK for {time_str}.</i>")
    if update.message.reply_to_message:
        ru = update.message.reply_to_message.from_user
        if ru and ru.id in afk_cache:
            afk = afk_cache[ru.id]
            since = afk["since"]
            diff  = datetime.datetime.now(pytz.utc) - since
            total_mins = int(diff.total_seconds() // 60)
            hrs  = total_mins // 60; mins = total_mins % 60
            time_str = f"{hrs}h {mins}m" if hrs else f"{mins}m"
            reason = afk.get("reason", "")
            await reply(update,
                f"😴 <b>{user_link(ru)} is AFK!</b>\n"
                f"⏱️ <i>Away for {time_str}</i>"
                + (f"\n📝 <b>Reason:</b> {html.escape(reason)}" if reason else "")
            )

# ═══════════════════════════════════════════════════════════════════════════════
#                     🌍 GLOBAL BAN / SUDO
# ═══════════════════════════════════════════════════════════════════════════════
@owner_only
async def gban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    reason = (" ".join(context.args[1:]) if not update.message.reply_to_message
              else " ".join(context.args)) or "No reason"
    m = await animate_loading(update, "Applying global ban")
    db = get_db()
    db.execute("""INSERT INTO users (user_id, is_gbanned, gban_reason, gbanned_by, gbanned_at)
                  VALUES (?,1,?,?,CURRENT_TIMESTAMP)
                  ON CONFLICT(user_id) DO UPDATE SET is_gbanned=1, gban_reason=excluded.gban_reason,
                  gbanned_by=excluded.gbanned_by, gbanned_at=excluded.gbanned_at""",
               (target.id, reason, update.effective_user.id))
    chats = db.execute("SELECT chat_id FROM chats").fetchall()
    db.commit(); db.close()
    banned_in = 0
    for ch in chats:
        try: await context.bot.ban_chat_member(ch["chat_id"], target.id); banned_in += 1
        except: pass
    log_action(0, update.effective_user.id, "gban", target.id, reason)
    await finish_anim(m,
        f"╔══════════════════════╗\n║  🌍 <b>GLOBAL BAN!</b>   ║\n╚══════════════════════╝\n\n"
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"🆔 <b>ID:</b> <code>{target.id}</code>\n"
        f"📝 <b>Reason:</b> {html.escape(reason)}\n"
        f"💬 <b>Banned in:</b> {banned_in} chats\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <i>Ban applied globally!</i>"
    )
    if GBAN_LOG:
        try:
            await context.bot.send_message(GBAN_LOG,
                f"🌍 <b>GBAN</b>\nUser: {user_link(target)} (<code>{target.id}</code>)\n"
                f"By: {user_link(update.effective_user)}\nReason: {html.escape(reason)}",
                parse_mode="HTML")
        except: pass

@owner_only
async def ungban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    m = await animate_loading(update, "Removing global ban")
    db = get_db()
    db.execute("UPDATE users SET is_gbanned=0, gban_reason=NULL WHERE user_id=?", (target.id,))
    chats = db.execute("SELECT chat_id FROM chats").fetchall()
    db.commit(); db.close()
    for ch in chats:
        try: await context.bot.unban_chat_member(ch["chat_id"], target.id, only_if_banned=True)
        except: pass
    await finish_anim(m,
        f"✅ <b>Global ban lifted for {user_link(target)}!</b>\n<i>Removed from all {len(chats)} chats.</i>"
    )

@owner_only
async def sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    db = get_db()
    db.execute("INSERT OR IGNORE INTO sudo_users (user_id, added_by) VALUES (?,?)",
               (target.id, update.effective_user.id))
    db.execute("UPDATE users SET is_sudo=1 WHERE user_id=?", (target.id,))
    db.commit(); db.close()
    await reply(update, f"👑 <b>{user_link(target)} now has sudo powers!</b>")

@owner_only
async def unsudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    db = get_db()
    db.execute("DELETE FROM sudo_users WHERE user_id=?", (target.id,))
    db.execute("UPDATE users SET is_sudo=0 WHERE user_id=?", (target.id,))
    db.commit(); db.close()
    await reply(update, f"✅ <b>Sudo revoked from {user_link(target)}!</b>")

# ═══════════════════════════════════════════════════════════════════════════════
#                         📢 BROADCAST
# ═══════════════════════════════════════════════════════════════════════════════
@owner_only
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and not update.message.reply_to_message:
        return await reply(update,
            "📢 <b>Usage:</b>\n"
            "<code>/broadcast text</code> — all chats\n"
            "<code>/broadcastall text</code> — all members"
        )
    text = " ".join(context.args) if context.args else update.message.reply_to_message.text
    db = get_db()
    chats = db.execute("SELECT chat_id FROM chats").fetchall()
    db.close()
    total = len(chats)
    m = await context.bot.send_message(update.effective_chat.id,
        f"📢 <b>Broadcasting to {total} chats...</b>\n[{progress_bar(0, total)}]",
        parse_mode="HTML")
    sent = failed = 0
    for i, ch in enumerate(chats, 1):
        try:
            await context.bot.send_message(ch["chat_id"], text, parse_mode="HTML")
            sent += 1
        except: failed += 1
        if i % 10 == 0 or i == total:
            try:
                await m.edit_text(
                    f"📢 <b>Broadcasting...</b> [{progress_bar(i, total)}]\n"
                    f"{i}/{total} • ✅ {sent} | ❌ {failed}", parse_mode="HTML")
            except: pass
        await asyncio.sleep(0.05)
    await m.edit_text(
        f"╔══════════════════════╗\n║  📢 <b>BROADCAST DONE!</b> ║\n╚══════════════════════╝\n\n"
        f"💬 <b>Chats:</b> {total}\n✅ <b>Sent:</b> {sent}\n❌ <b>Failed:</b> {failed}\n"
        f"📊 <b>Rate:</b> {int(sent/total*100) if total else 0}%",
        parse_mode="HTML")

@owner_only
async def broadcastall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and not update.message.reply_to_message:
        return await reply(update, "❓ <b>Usage:</b> <code>/broadcastall Your message</code>")
    text = " ".join(context.args) if context.args else update.message.reply_to_message.text
    db = get_db()
    members = db.execute("SELECT DISTINCT user_id FROM chat_members WHERE is_bot=0").fetchall()
    db.close()
    total = len(members)
    if total == 0: return await reply(update, "❌ <b>No tracked members yet!</b>")
    m = await context.bot.send_message(update.effective_chat.id,
        f"📢 <b>Sending to {total} members...</b>\n[{progress_bar(0, total)}]",
        parse_mode="HTML")
    sent = failed = 0
    for i, member in enumerate(members, 1):
        try:
            await context.bot.send_message(member["user_id"], text, parse_mode="HTML")
            sent += 1
        except: failed += 1
        if i % 20 == 0 or i == total:
            try:
                await m.edit_text(
                    f"📢 [{progress_bar(i, total)}] {i}/{total}\n✅ {sent} | ❌ {failed}",
                    parse_mode="HTML")
            except: pass
        await asyncio.sleep(0.08)
    await m.edit_text(
        f"╔══════════════════════╗\n║  📢 <b>BROADCAST DONE!</b> ║\n╚══════════════════════╝\n\n"
        f"👥 <b>Members:</b> {total}\n✅ <b>Delivered:</b> {sent}\n❌ <b>Failed:</b> {failed}",
        parse_mode="HTML")

# ═══════════════════════════════════════════════════════════════════════════════
#                     📊 STATS / INFO
# ═══════════════════════════════════════════════════════════════════════════════
@owner_only
async def botstats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Fetching bot statistics")
    db = get_db()
    chats    = db.execute("SELECT COUNT(*) as c FROM chats").fetchone()["c"]
    users    = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    members  = db.execute("SELECT COUNT(*) as c FROM chat_members").fetchone()["c"]
    warns    = db.execute("SELECT COUNT(*) as c FROM warns").fetchone()["c"]
    bans     = db.execute("SELECT COUNT(*) as c FROM bans").fetchone()["c"]
    gbans    = db.execute("SELECT COUNT(*) as c FROM users WHERE is_gbanned=1").fetchone()["c"]
    notes    = db.execute("SELECT COUNT(*) as c FROM notes").fetchone()["c"]
    filters_ = db.execute("SELECT COUNT(*) as c FROM filters").fetchone()["c"]
    feds     = db.execute("SELECT COUNT(*) as c FROM federations").fetchone()["c"]
    db.close()
    uptime = datetime.datetime.now(pytz.utc) - START_TIME
    s = int(uptime.total_seconds())
    upstr = f"{s//86400}d {(s%86400)//3600}h {(s%3600)//60}m {s%60}s"
    bar = progress_bar(s % 86400, 86400)
    await finish_anim(m,
        f"╔══════════════════════════════╗\n║    📊 <b>BOT STATISTICS</b>    ║\n╚══════════════════════════════╝\n\n"
        f"💬 <b>Chats:</b> {chats}\n"
        f"👤 <b>Users:</b> {users}\n"
        f"👥 <b>Members tracked:</b> {members}\n"
        f"🌐 <b>Federations:</b> {feds}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b>Warns:</b> {warns}\n"
        f"🚫 <b>Bans:</b> {bans}\n"
        f"🌍 <b>Global bans:</b> {gbans}\n"
        f"📝 <b>Notes:</b> {notes}\n"
        f"🔍 <b>Filters:</b> {filters_}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ <b>Uptime:</b> {upstr}\n"
        f"[{bar}]\n"
        f"🤖 <b>Version:</b> <code>{VERSION}</code>"
    )

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = (update.message.reply_to_message.from_user
              if update.message.reply_to_message else update.effective_user)
    chat = update.effective_chat
    lines = [
        f"╔══════════════════════╗\n║       🆔 <b>IDs</b>        ║\n╚══════════════════════╝\n\n"
        f"👤 <b>User ID:</b> <code>{target.id}</code>\n"
        f"💬 <b>Chat ID:</b> <code>{chat.id}</code>"
    ]
    if update.message.reply_to_message and update.message.reply_to_message.forward_from:
        ff = update.message.reply_to_message.forward_from
        lines.append(f"\n📨 <b>Forward from ID:</b> <code>{ff.id}</code>")
    await reply(update, "\n".join(lines))

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Building profile")
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args and context.args[0].lstrip("-").isdigit():
        uid = int(context.args[0])
        target = type("U", (), {"id": uid, "first_name": str(uid), "username": None,
                                "last_name": None, "is_bot": False})()
    else:
        target = update.effective_user
    db = get_db()
    row    = db.execute("SELECT * FROM users WHERE user_id=?", (target.id,)).fetchone()
    warns  = db.execute("SELECT COUNT(*) as c FROM warns WHERE user_id=?", (target.id,)).fetchone()["c"]
    # Chat rank (messages)
    cm_row = None
    if update.effective_chat and update.effective_chat.type != "private":
        cm_row = db.execute(
            "SELECT msgs, (SELECT COUNT(*)+1 FROM chat_members cm2 WHERE cm2.chat_id=cm.chat_id AND cm2.msgs>cm.msgs) as rank "
            "FROM chat_members cm WHERE cm.chat_id=? AND cm.user_id=?",
            (update.effective_chat.id, target.id)).fetchone()
    db.close()
    name = html.escape(getattr(target, "first_name", "") or str(target.id))
    badges = ""
    if row and row["is_gbanned"]: badges += "🌍 GBanned "
    if row and row["is_sudo"]:    badges += "👑 Sudo "
    if getattr(target, "is_bot", False): badges += "🤖 Bot "
    coins = row["coins"] if row else 0
    bank  = row["bank"]  if row else 0
    rep   = row["reputation"] if row else 0
    msgs  = row["total_msgs"] if row else 0
    lvl   = level_from_msgs(msgs)
    lvl_bar = progress_bar(msgs % (lvl * 100), lvl * 100)

    text = (
        f"╔══════════════════════════╗\n║    👤 <b>USER PROFILE</b>    ║\n╚══════════════════════════╝\n\n"
        f"📋 <b>Name:</b> <a href='tg://user?id={target.id}'>{name}</a>\n"
        f"🆔 <b>ID:</b> <code>{target.id}</code>\n"
    )
    if getattr(target, "username", None): text += f"📌 @{html.escape(target.username)}\n"
    if badges: text += f"🏷️ <b>Badges:</b> {badges}\n"
    if row:
        text += (
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⭐ <b>Level:</b> {lvl} — {level_title(lvl)}\n"
            f"[{lvl_bar}]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 <b>Wallet:</b> {coins:,} 🪙 | 🏦 Bank: {bank:,}\n"
            f"⭐ <b>Reputation:</b> {rep}\n"
            f"💬 <b>Messages:</b> {msgs:,}\n"
            f"⚠️ <b>Warns:</b> {warns}\n"
        )
        if cm_row:
            text += f"🏆 <b>Chat rank:</b> #{cm_row['rank']} ({cm_row['msgs']} msgs)\n"
    if row and row["is_gbanned"]:
        text += f"\n🚫 <b>GLOBALLY BANNED</b>\n📝 {html.escape(row['gban_reason'] or 'No reason')}"
    await finish_anim(m, text)

async def chatinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Fetching chat info")
    chat = update.effective_chat
    try:
        members = await context.bot.get_chat_member_count(chat.id)
        db = get_db()
        tracked = db.execute("SELECT COUNT(*) as c FROM chat_members WHERE chat_id=?",
                             (chat.id,)).fetchone()["c"]
        notes   = db.execute("SELECT COUNT(*) as c FROM notes WHERE chat_id=?",
                             (chat.id,)).fetchone()["c"]
        filters_count = db.execute("SELECT COUNT(*) as c FROM filters WHERE chat_id=?",
                                   (chat.id,)).fetchone()["c"]
        db.close()
        admins = await context.bot.get_chat_administrators(chat.id)
        text = (
            f"╔══════════════════════════╗\n║    💬 <b>CHAT INFO</b>      ║\n╚══════════════════════════╝\n\n"
            f"📋 <b>Title:</b> {html.escape(chat.title or 'N/A')}\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n"
            f"📁 <b>Type:</b> {chat.type.title()}\n"
            f"👥 <b>Members:</b> {members:,}\n"
            f"👮 <b>Admins:</b> {len(admins)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 <b>Tracked:</b> {tracked} members\n"
            f"📝 <b>Notes:</b> {notes}\n"
            f"🔍 <b>Filters:</b> {filters_count}\n"
        )
        if chat.username: text += f"🔗 @{chat.username}"
        if chat.description: text += f"\n📄 {html.escape(chat.description[:100])}"
        await finish_anim(m, text)
    except Exception as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = time.time()
    m = await reply(update, "🏓 <b>Pinging...</b>")
    elapsed = (time.time() - start) * 1000
    quality = ("🟢 Excellent" if elapsed < 100 else
               "🟡 Good"     if elapsed < 300 else
               "🔴 Slow")
    if m:
        await m.edit_text(
            f"╔══════════════════════╗\n║  🏓 <b>PONG!</b>         ║\n╚══════════════════════╝\n\n"
            f"⚡ <b>Latency:</b> {elapsed:.1f}ms\n"
            f"📶 <b>Quality:</b> {quality}",
            parse_mode="HTML")

async def uptime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.datetime.now(pytz.utc) - START_TIME
    s = int(uptime.total_seconds())
    upstr = f"{s//86400}d {(s%86400)//3600}h {(s%3600)//60}m {s%60}s"
    bar   = progress_bar(s % 86400, 86400)
    await reply(update,
        f"╔══════════════════════╗\n║    ⏱️ <b>UPTIME</b>      ║\n╚══════════════════════╝\n\n"
        f"🕐 <b>{upstr}</b>\n[{bar}]\n\n"
        f"🚀 <i>Since {START_TIME.strftime('%Y-%m-%d %H:%M UTC')}</i>"
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                     🏆 LEADERBOARD — MULTI-TAB
# ═══════════════════════════════════════════════════════════════════════════════
async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tab = "coins"
    if context.args: tab = context.args[0].lower()
    await _send_leaderboard(update, context, tab)

async def _send_leaderboard(update, context, tab: str = "coins", edit_msg=None):
    db = get_db()
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    chat_id = update.effective_chat.id if update.effective_chat else 0
    is_group = chat_id and update.effective_chat.type != "private"

    if tab == "coins":
        if is_group:
            rows = db.execute(
                "SELECT u.user_id, u.first_name, u.coins FROM users u "
                "JOIN chat_members cm ON cm.user_id=u.user_id "
                "WHERE cm.chat_id=? ORDER BY u.coins DESC LIMIT 10", (chat_id,)).fetchall()
        else:
            rows = db.execute("SELECT user_id, first_name, coins FROM users ORDER BY coins DESC LIMIT 10").fetchall()
        title = "💰 <b>RICHEST MEMBERS</b>"
        lines = [f"╔══════════════════════════╗\n║   {title}   ║\n╚══════════════════════════╝\n"]
        for i, row in enumerate(rows):
            name = html.escape(row["first_name"] or str(row["user_id"]))
            bar  = progress_bar(min(row["coins"], 10000), 10000, length=6)
            lines.append(f"{medals[i] if i<10 else '•'} <a href='tg://user?id={row['user_id']}'>{name}</a>\n"
                         f"   [{bar}] <b>{row['coins']:,}</b> 🪙")
    elif tab == "msgs":
        if is_group:
            rows = db.execute(
                "SELECT cm.user_id, cm.first_name, cm.msgs FROM chat_members cm "
                "WHERE cm.chat_id=? ORDER BY cm.msgs DESC LIMIT 10", (chat_id,)).fetchall()
        else:
            rows = db.execute("SELECT user_id, first_name, total_msgs as msgs FROM users ORDER BY total_msgs DESC LIMIT 10").fetchall()
        title = "💬 <b>MOST ACTIVE</b>"
        lines = [f"╔══════════════════════════╗\n║   {title}    ║\n╚══════════════════════════╝\n"]
        for i, row in enumerate(rows):
            name = html.escape(row["first_name"] or str(row["user_id"]))
            msgs = row["msgs"] or 0
            lines.append(f"{medals[i] if i<10 else '•'} <a href='tg://user?id={row['user_id']}'>{name}</a>\n"
                         f"   <b>{msgs:,}</b> 💬 — Lvl {level_from_msgs(msgs)}")
    elif tab == "rep":
        rows = db.execute("SELECT user_id, first_name, reputation FROM users ORDER BY reputation DESC LIMIT 10").fetchall()
        title = "⭐ <b>REPUTATION LEADERS</b>"
        lines = [f"╔══════════════════════════╗\n║  {title}  ║\n╚══════════════════════════╝\n"]
        for i, row in enumerate(rows):
            name = html.escape(row["first_name"] or str(row["user_id"]))
            rep  = row["reputation"] or 0
            bar  = stars_bar(min(rep, 5))
            lines.append(f"{medals[i] if i<10 else '•'} <a href='tg://user?id={row['user_id']}'>{name}</a>\n"
                         f"   {bar} <b>{rep}</b> ⭐")
    else:
        db.close()
        tab = "coins"
        await _send_leaderboard(update, context, tab, edit_msg)
        return
    db.close()

    text = "\n".join(lines)
    tabs = [
        InlineKeyboardButton("💰 Coins" + (" ◀" if tab=="coins" else ""), callback_data="lb:coins"),
        InlineKeyboardButton("💬 Activity" + (" ◀" if tab=="msgs" else ""), callback_data="lb:msgs"),
        InlineKeyboardButton("⭐ Reputation" + (" ◀" if tab=="rep" else ""), callback_data="lb:rep"),
    ]
    kb = InlineKeyboardMarkup([tabs, [InlineKeyboardButton("🔄 Refresh", callback_data=f"lb:{tab}")]])
    if edit_msg:
        try: await edit_msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
        except: pass
    else:
        m = await animate_loading(update, "Loading leaderboard")
        await finish_anim(m, text, reply_markup=kb)

async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    tab = q.data.split(":")[1]
    await _send_leaderboard(update, context, tab, edit_msg=q.message)

# ─── RANK / TOP ───────────────────────────────────────────────────────────────
async def rank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context) or update.effective_user
    db = get_db()
    cm_row = db.execute(
        "SELECT cm.msgs, "
        "(SELECT COUNT(*)+1 FROM chat_members cm2 WHERE cm2.chat_id=cm.chat_id AND cm2.msgs>cm.msgs) as rank, "
        "(SELECT COUNT(*) FROM chat_members cm3 WHERE cm3.chat_id=cm.chat_id AND cm3.is_bot=0) as total "
        "FROM chat_members cm WHERE cm.chat_id=? AND cm.user_id=?",
        (update.effective_chat.id, target.id)).fetchone()
    u_row = db.execute("SELECT * FROM users WHERE user_id=?", (target.id,)).fetchone()
    db.close()
    if not cm_row:
        return await reply(update, f"❌ <b>{user_link(target)} has no activity in this chat!</b>")
    msgs = cm_row["msgs"] or 0
    rank = cm_row["rank"]
    total = cm_row["total"]
    lvl  = level_from_msgs(msgs)
    lvl_title = level_title(lvl)
    next_lvl_msgs = (lvl * 100)
    progress = msgs % next_lvl_msgs
    bar  = progress_bar(progress, next_lvl_msgs, length=15)
    rank_icon = rank_badge(rank)
    name = html.escape(getattr(target, "first_name", "") or str(target.id))
    text = (
        f"╔══════════════════════════════════╗\n"
        f"║  🏆 <b>RANK CARD — {name[:12]}</b>  ║\n"
        f"╚══════════════════════════════════╝\n\n"
        f"{rank_icon} <b>Rank #{rank}</b> of {total} members\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⭐ <b>Level:</b> {lvl} — <i>{lvl_title}</i>\n"
        f"[{bar}] {progress}/{next_lvl_msgs}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 <b>Messages:</b> {msgs:,}\n"
    )
    if u_row:
        text += (
            f"💰 <b>Coins:</b> {u_row['coins']:,} 🪙\n"
            f"⭐ <b>Reputation:</b> {u_row['reputation']}\n"
        )
    await reply(update, text)

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Top active members in this chat."""
    db = get_db()
    rows = db.execute(
        "SELECT user_id, first_name, msgs FROM chat_members WHERE chat_id=? AND is_bot=0 "
        "ORDER BY msgs DESC LIMIT 10",
        (update.effective_chat.id,)).fetchall()
    db.close()
    if not rows: return await reply(update, "❌ <b>No activity data yet!</b>")
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    lines = ["╔══════════════════════════╗\n║   🏆 <b>TOP ACTIVE MEMBERS</b>   ║\n╚══════════════════════════╝\n"]
    for i, row in enumerate(rows):
        name = html.escape(row["first_name"] or str(row["user_id"]))
        lines.append(f"{medals[i]} <a href='tg://user?id={row['user_id']}'>{name}</a> — {row['msgs']:,} msgs")
    await reply(update, "\n".join(lines))

# ─── REP ──────────────────────────────────────────────────────────────────────
async def rep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target:
        db = get_db()
        row = db.execute("SELECT reputation FROM users WHERE user_id=?",
                         (update.effective_user.id,)).fetchone()
        db.close()
        rep = row["reputation"] if row else 0
        return await reply(update,
            f"╔══════════════════════╗\n║    ⭐ <b>YOUR REP</b>    ║\n╚══════════════════════╝\n\n"
            f"⭐ <b>Reputation:</b> {rep}\n"
            f"[{stars_bar(min(rep, 5), 5)}]"
        )
    if target.id == update.effective_user.id:
        return await reply(update, "❌ <b>Can't rep yourself!</b>")
    giver = update.effective_user.id
    db = get_db()
    existing = db.execute("SELECT given_at FROM reputation WHERE giver_id=? AND receiver_id=? AND chat_id=?",
                          (giver, target.id, update.effective_chat.id)).fetchone()
    if existing:
        given = datetime.datetime.fromisoformat(str(existing["given_at"]).replace(" ", "T")).replace(tzinfo=pytz.utc)
        if (datetime.datetime.now(pytz.utc) - given).total_seconds() < 86400:
            db.close()
            return await reply(update, "⏰ <b>Already gave rep today!</b>\n<i>Come back tomorrow.</i>")
    db.execute("INSERT OR REPLACE INTO reputation (giver_id, receiver_id, chat_id) VALUES (?,?,?)",
               (giver, target.id, update.effective_chat.id))
    db.execute("UPDATE users SET reputation=reputation+1 WHERE user_id=?", (target.id,))
    row = db.execute("SELECT reputation FROM users WHERE user_id=?", (target.id,)).fetchone()
    db.commit(); db.close()
    rep = row["reputation"] if row else 1
    await reply(update,
        f"╔══════════════════════╗\n║  ⭐ <b>REP GIVEN!</b>   ║\n╚══════════════════════╝\n\n"
        f"🎁 {user_link(update.effective_user)} → +1 ⭐ → {user_link(target)}\n"
        f"📊 <b>Total rep:</b> {rep} [{stars_bar(min(rep, 5))}]"
    )

async def reprank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_leaderboard(update, context, "rep")

async def level_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context) or update.effective_user
    db = get_db()
    row = db.execute("SELECT total_msgs FROM users WHERE user_id=?", (target.id,)).fetchone()
    db.close()
    msgs = row["total_msgs"] if row else 0
    lvl  = level_from_msgs(msgs)
    next_msgs = lvl * 100
    bar  = progress_bar(msgs % next_msgs, next_msgs, length=15)
    await reply(update,
        f"╔══════════════════════╗\n║   ⭐ <b>LEVEL</b>        ║\n╚══════════════════════╝\n\n"
        f"👤 {user_link(target)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⭐ <b>Level {lvl}</b> — {level_title(lvl)}\n"
        f"[{bar}]\n"
        f"💬 {msgs:,} / {next_msgs*(lvl+1)} msgs to next level"
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                         💰 ECONOMY SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
DAILY_MIN, DAILY_MAX = 400, 700
MINE_MIN, MINE_MAX   = 10, 200
WORK_MIN, WORK_MAX   = 50, 400

WORK_JOBS = [
    "🧑‍💻 coded a website", "👨‍🍳 cooked at a restaurant",
    "📦 delivered packages", "🎨 sold a painting",
    "🎸 played at a gig", "🏗️ helped at a construction site",
    "📱 fixed phones", "🌱 worked at a farm",
    "🐕 walked dogs", "✍️ freelanced as a writer",
]

async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = get_db()
    ensure_user(update.effective_user)
    row = db.execute("SELECT last_daily, coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    now = datetime.datetime.now(pytz.utc)
    if row and row["last_daily"]:
        last = datetime.datetime.fromisoformat(str(row["last_daily"]).replace(" ", "T")).replace(tzinfo=pytz.utc)
        diff = now - last
        if diff.total_seconds() < 86400:
            remaining = 86400 - diff.total_seconds()
            h = int(remaining // 3600); mi = int((remaining % 3600) // 60)
            bar = progress_bar(int(86400 - remaining), 86400)
            db.close()
            return await reply(update,
                f"╔══════════════════════╗\n║  ⏰ <b>ALREADY CLAIMED</b>  ║\n╚══════════════════════╝\n\n"
                f"⏳ Come back in <b>{h}h {mi}m</b>\n[{bar}]"
            )
    coins = random.randint(DAILY_MIN, DAILY_MAX)
    bonus = 0
    # Streak bonus (simplified)
    db.execute("UPDATE users SET coins=coins+?, last_daily=CURRENT_TIMESTAMP WHERE user_id=?", (coins, user_id))
    db.commit()
    new_bal = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()["coins"]
    db.close()
    await reply(update,
        f"╔══════════════════════╗\n║   💰 <b>DAILY CLAIMED!</b>  ║\n╚══════════════════════╝\n\n"
        f"🎁 <b>+{coins} coins</b> added!\n"
        f"{'🔥 Bonus: +' + str(bonus) + ' coins!' + chr(10) if bonus else ''}"
        f"💳 <b>Balance:</b> {new_bal:,} 🪙\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <i>Come back in 24h for more!</i>"
    )

async def work_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(update.effective_user)
    now = time.time()
    last_work = work_cd.get(user_id, 0)
    cooldown = 3600  # 1 hour
    if now - last_work < cooldown:
        remaining = int(cooldown - (now - last_work))
        h = remaining // 3600; mi = (remaining % 3600) // 60
        bar = progress_bar(int(cooldown - remaining), cooldown)
        return await reply(update,
            f"╔══════════════════════╗\n║   😓 <b>TOO TIRED!</b>   ║\n╚══════════════════════╝\n\n"
            f"⏳ Rest for <b>{h}h {mi}m</b> more!\n[{bar}]"
        )
    m = await animate_loading(update, "Working hard")
    await asyncio.sleep(0.5)
    earned = random.randint(WORK_MIN, WORK_MAX)
    job = random.choice(WORK_JOBS)
    work_cd[user_id] = now
    db = get_db()
    db.execute("UPDATE users SET coins=coins+?, last_work=CURRENT_TIMESTAMP WHERE user_id=?", (earned, user_id))
    db.commit()
    bal = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()["coins"]
    db.close()
    await finish_anim(m,
        f"╔══════════════════════╗\n║   💼 <b>WORK DONE!</b>   ║\n╚══════════════════════╝\n\n"
        f"🧑‍🏭 You {job} and earned <b>{earned} coins</b>!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Balance:</b> {bal:,} 🪙"
    )

async def mine_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(update.effective_user)
    m = await animate_loading(update, "Mining")
    await asyncio.sleep(0.4)
    earned = random.randint(MINE_MIN, MINE_MAX)
    gems = random.choice(["⛏️", "💎", "🪨", "⚒️", "🌟"])
    db = get_db()
    db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (earned, user_id))
    db.commit()
    bal = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    await finish_anim(m,
        f"╔══════════════════════╗\n║   ⛏️ <b>MINING RESULT</b>  ║\n╚══════════════════════╝\n\n"
        f"{gems} <b>Found {earned} coins</b> in the mine!\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Balance:</b> {(bal['coins'] if bal else earned):,} 🪙"
    )

async def coins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context) or update.effective_user
    db = get_db()
    row = db.execute("SELECT coins, bank FROM users WHERE user_id=?", (target.id,)).fetchone()
    db.close()
    wallet = row["coins"] if row else 0
    bank   = row["bank"]  if row else 0
    bar    = progress_bar(min(wallet, 10000), 10000)
    await reply(update,
        f"╔══════════════════════╗\n║    💰 <b>WALLET</b>       ║\n╚══════════════════════╝\n\n"
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Wallet:</b> {wallet:,} 🪙\n"
        f"[{bar}]\n"
        f"🏦 <b>Bank:</b> {bank:,} 🪙\n"
        f"💼 <b>Total:</b> {wallet+bank:,} 🪙"
    )

async def bank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(update.effective_user)
    if not context.args or context.args[0] not in ("deposit", "withdraw", "balance"):
        return await reply(update,
            "╔══════════════════════╗\n║    🏦 <b>BANK</b>         ║\n╚══════════════════════╝\n\n"
            "<code>/bank deposit N</code> — Deposit coins\n"
            "<code>/bank withdraw N</code> — Withdraw coins\n"
            "<code>/bank balance</code> — Check balance"
        )
    action = context.args[0]
    db = get_db()
    row = db.execute("SELECT coins, bank FROM users WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    wallet = row["coins"] if row else 0
    bank   = row["bank"]  if row else 0
    if action == "balance":
        return await reply(update,
            f"╔══════════════════════╗\n║    🏦 <b>BANK BALANCE</b>  ║\n╚══════════════════════╝\n\n"
            f"💳 <b>Wallet:</b> {wallet:,} 🪙\n"
            f"🏦 <b>Bank:</b> {bank:,} 🪙\n"
            f"💼 <b>Total:</b> {wallet+bank:,} 🪙"
        )
    try: amount = int(context.args[1]) if len(context.args) > 1 else 0
    except: return await reply(update, "❌ <b>Invalid amount!</b>")
    if amount <= 0: return await reply(update, "❌ <b>Amount must be positive!</b>")
    if action == "deposit":
        if wallet < amount: return await reply(update, f"❌ <b>Not enough coins!</b> You have {wallet:,} 🪙")
        db = get_db()
        db.execute("UPDATE users SET coins=coins-?, bank=bank+? WHERE user_id=?", (amount, amount, user_id))
        db.commit(); db.close()
        await reply(update, f"🏦 <b>Deposited {amount:,} coins to bank!</b>\n💳 Wallet: {wallet-amount:,} | 🏦 Bank: {bank+amount:,}")
    else:
        if bank < amount: return await reply(update, f"❌ <b>Not enough in bank!</b> Bank: {bank:,} 🪙")
        db = get_db()
        db.execute("UPDATE users SET bank=bank-?, coins=coins+? WHERE user_id=?", (amount, amount, user_id))
        db.commit(); db.close()
        await reply(update, f"💳 <b>Withdrew {amount:,} coins from bank!</b>\n💳 Wallet: {wallet+amount:,} | 🏦 Bank: {bank-amount:,}")

async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2 and not (update.message.reply_to_message and context.args):
        return await reply(update, "❓ <b>Usage:</b> <code>/give @user amount</code>")
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user or provide @username.")
    try: amount = int(context.args[-1])
    except: return await reply(update, "❌ <b>Invalid amount!</b>")
    if amount <= 0: return await reply(update, "❌ <b>Amount must be positive!</b>")
    user_id = update.effective_user.id
    db = get_db()
    sender = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not sender or sender["coins"] < amount:
        db.close(); return await reply(update, "❌ <b>Insufficient coins!</b>")
    db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, user_id))
    db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, target.id))
    new_bal = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()["coins"]
    db.commit(); db.close()
    await reply(update,
        f"╔══════════════════════╗\n║  💸 <b>COINS SENT!</b>   ║\n╚══════════════════════╝\n\n"
        f"💰 <b>{amount:,}</b> coins sent!\n"
        f"📤 From: {user_link(update.effective_user)}\n"
        f"📥 To: {user_link(target)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Your balance:</b> {new_bal:,} 🪙"
    )

async def rob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user to rob.")
    if target.id == update.effective_user.id: return await reply(update, "❌ <b>Can't rob yourself!</b>")
    m = await animate_loading(update, "Planning the heist")
    db = get_db()
    victim = db.execute("SELECT coins FROM users WHERE user_id=?", (target.id,)).fetchone()
    if not victim or victim["coins"] < 100:
        db.close(); return await finish_anim(m, "❌ <b>Target doesn't have enough to rob!</b> (min 100 🪙)")
    if random.random() < 0.45:
        fine = random.randint(50, 250)
        db.execute("UPDATE users SET coins=MAX(0, coins-?) WHERE user_id=?", (fine, update.effective_user.id))
        db.commit(); db.close()
        await finish_anim(m,
            f"╔══════════════════════╗\n║   👮 <b>BUSTED!</b>      ║\n╚══════════════════════╝\n\n"
            f"🚓 Caught trying to rob {user_link(target)}!\n"
            f"💸 <b>Fine paid:</b> {fine:,} 🪙"
        )
    else:
        stolen = random.randint(50, min(500, victim["coins"]))
        db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (stolen, target.id))
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (stolen, update.effective_user.id))
        db.commit(); db.close()
        await finish_anim(m,
            f"╔══════════════════════╗\n║  💰 <b>HEIST SUCCESS!</b>  ║\n╚══════════════════════╝\n\n"
            f"🦹 Robbed {user_link(target)}!\n"
            f"💰 <b>Stolen:</b> {stolen:,} 🪙\n"
            f"<i>They'll never catch you!</i>"
        )

async def flip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        m = await animate_loading(update, "Flipping coin")
        result = "Heads 🦅" if random.random() > 0.5 else "Tails 🪙"
        await finish_anim(m,
            f"╔══════════════════════╗\n║   🪙 <b>COIN FLIP!</b>   ║\n╚══════════════════════╝\n\n"
            f"Result: <b>{result}</b>!"
        )
        return
    amount = int(context.args[0])
    user_id = update.effective_user.id
    db = get_db()
    row = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row or row["coins"] < amount:
        db.close(); return await reply(update, "❌ <b>Insufficient coins!</b>")
    m = await animate_loading(update, "Flipping")
    if random.random() > 0.5:
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, user_id))
        result_text = f"╔══════════════════════╗\n║   🎉 <b>YOU WON!</b>    ║\n╚══════════════════════╝\n\n🦅 <b>HEADS!</b>\n💰 <b>+{amount:,} coins</b>!"
    else:
        db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, user_id))
        result_text = f"╔══════════════════════╗\n║   😭 <b>YOU LOST!</b>   ║\n╚══════════════════════╝\n\n🪙 <b>TAILS!</b>\n💸 <b>-{amount:,} coins</b>!"
    bal = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()["coins"]
    db.commit(); db.close()
    await finish_anim(m, result_text + f"\n━━━━━━━━━━━━━━━━━━━━━\n💳 <b>Balance:</b> {bal:,} 🪙")

async def slots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols  = ["🍒","🍋","🍊","💎","7️⃣","⭐","🍇","🔔"]
    weights  = [25, 20, 18, 8, 4, 10, 10, 5]
    m = await animate_loading(update, "Spinning the reels")
    for _ in range(3):
        spin = " | ".join(random.choices(symbols, k=3))
        try: await m.edit_text(f"🎰 <b>Spinning...</b>\n┃ {spin} ┃", parse_mode="HTML")
        except: pass
        await asyncio.sleep(0.35)
    roll   = random.choices(symbols, weights=weights, k=3)
    result = " | ".join(roll)
    amount = int(context.args[0]) if context.args and context.args[0].isdigit() else 0
    user_id = update.effective_user.id
    if roll[0] == roll[1] == roll[2]:
        multiplier = 15 if roll[0]=="7️⃣" else (8 if roll[0]=="💎" else (5 if roll[0]=="⭐" else 3))
        winnings   = amount * multiplier
        outcome    = f"🎉 <b>JACKPOT!</b>\n💰 +<b>{winnings:,}</b> coins! (x{multiplier})"
        if amount:
            db = get_db()
            db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (winnings, user_id))
            db.commit(); db.close()
    elif roll[0] == roll[1] or roll[1] == roll[2] or roll[0] == roll[2]:
        outcome = "✨ <b>Pair! Bet returned!</b>"
    else:
        outcome = f"😢 <b>No match!</b> Lost <b>{amount:,}</b> coins."
        if amount:
            db = get_db()
            db.execute("UPDATE users SET coins=MAX(0,coins-?) WHERE user_id=?", (amount, user_id))
            db.commit(); db.close()
    await finish_anim(m,
        f"╔══════════════════════╗\n║    🎰 <b>SLOT MACHINE</b>   ║\n╚══════════════════════╝\n\n"
        f"┃ {result} ┃\n\n{outcome}"
    )

# ─── SHOP ─────────────────────────────────────────────────────────────────────
async def shop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    items = db.execute("SELECT * FROM shop_items ORDER BY price").fetchall()
    db.close()
    lines = ["╔══════════════════════╗\n║     🛍️ <b>SHOP</b>        ║\n╚══════════════════════╝\n"]
    kb_rows = []
    for item in items:
        lines.append(f"<b>[{item['id']}]</b> {item['name']}\n"
                     f"   📝 {item['description']}\n"
                     f"   💰 <b>{item['price']:,}</b> 🪙\n")
        kb_rows.append(InlineKeyboardButton(f"Buy {item['name']} ({item['price']:,}🪙)",
                                            callback_data=f"buy:{item['id']}"))
    kb = InlineKeyboardMarkup([[btn] for btn in kb_rows])
    await reply(update, "\n".join(lines) + "\n<i>Tap to buy!</i>", reply_markup=kb)

async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    item_id = int(q.data.split(":")[1])
    user_id = q.from_user.id
    db = get_db()
    item = db.execute("SELECT * FROM shop_items WHERE id=?", (item_id,)).fetchone()
    if not item: db.close(); return await q.answer("❌ Item not found!", show_alert=True)
    user = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not user or user["coins"] < item["price"]:
        db.close(); return await q.answer(f"❌ Not enough coins! Need {item['price']:,} 🪙", show_alert=True)
    db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (item["price"], user_id))
    db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?,?) ON CONFLICT(user_id, item_id) DO UPDATE SET quantity=quantity+1",
               (user_id, item_id))
    db.commit(); db.close()
    await q.answer(f"✅ Bought {item['name']}!", show_alert=True)
    await q.message.reply_text(f"✅ <b>{html.escape(q.from_user.first_name)}</b> bought <b>{item['name']}</b>!\n"
                               f"💰 Spent: {item['price']:,} 🪙", parse_mode="HTML")

async def buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/buy item_id</code>")
    try: item_id = int(context.args[0])
    except: return await reply(update, "❌ Invalid item ID.")
    user_id = update.effective_user.id
    db = get_db()
    item = db.execute("SELECT * FROM shop_items WHERE id=?", (item_id,)).fetchone()
    if not item: db.close(); return await reply(update, "❌ <b>Item not found!</b>")
    user = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not user or user["coins"] < item["price"]:
        db.close(); return await reply(update, f"❌ <b>Not enough coins!</b> Need {item['price']:,} 🪙")
    db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (item["price"], user_id))
    db.execute("INSERT INTO inventory (user_id, item_id) VALUES (?,?) ON CONFLICT(user_id, item_id) DO UPDATE SET quantity=quantity+1",
               (user_id, item_id))
    db.commit(); db.close()
    await reply(update,
        f"✅ <b>Purchased: {item['name']}!</b>\n"
        f"💰 Spent: {item['price']:,} 🪙\n"
        f"<i>Use /inventory to see your items!</i>"
    )

async def inventory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = get_db()
    rows = db.execute(
        "SELECT si.name, si.description, inv.quantity FROM inventory inv "
        "JOIN shop_items si ON si.id=inv.item_id WHERE inv.user_id=?",
        (user_id,)).fetchall()
    db.close()
    if not rows:
        return await reply(update, "🎒 <b>Your inventory is empty!</b>\nVisit /shop to buy items!")
    lines = ["╔══════════════════════╗\n║   🎒 <b>INVENTORY</b>    ║\n╚══════════════════════╝\n"]
    for r in rows:
        lines.append(f"• {r['name']} x{r['quantity']}\n  <i>{r['description']}</i>")
    await reply(update, "\n".join(lines))

# ═══════════════════════════════════════════════════════════════════════════════
#                         🎮 FUN & GAMES
# ═══════════════════════════════════════════════════════════════════════════════
EIGHTBALL_ANSWERS = [
    "🟢 It is certain!", "🟢 Absolutely yes!", "🟢 Without a doubt!",
    "🟢 Yes, definitely!", "🟢 As I see it, yes!", "🟢 Most likely!",
    "🟢 Outlook good!", "🟢 Signs point to yes!", "🟡 Reply hazy, try again...",
    "🟡 Ask again later...", "🟡 Better not tell you now.", "🟡 Cannot predict now.",
    "🔴 Don't count on it.", "🔴 My reply is no.", "🔴 My sources say NO.",
    "🔴 Outlook not so good.", "🔴 Very doubtful!", "🔴 Absolutely not!"
]

FACTS = [
    "🧠 Honey never spoils — archaeologists found 3000-year-old honey in Egyptian tombs!",
    "🐙 Octopuses have three hearts and blue blood!",
    "🌍 A day on Venus is longer than a year on Venus!",
    "🦷 Sharks are older than trees — they've been around 450 million years!",
    "🌙 The Moon is moving away from Earth at about 3.8 cm per year!",
    "🐘 Elephants are the only animals that can't jump!",
    "⚡ A bolt of lightning is 5x hotter than the surface of the Sun!",
    "🧬 You share 60% of your DNA with a banana!",
    "🌊 The ocean produces over 50% of Earth's oxygen!",
    "🐦 Crows can recognize human faces and hold grudges!",
]

QUOTES = [
    "💡 <i>\"The only way to do great work is to love what you do.\"</i> — Steve Jobs",
    "🌟 <i>\"In the middle of difficulty lies opportunity.\"</i> — Albert Einstein",
    "🚀 <i>\"Dream big. Work hard. Stay focused.\"</i> — Unknown",
    "🌈 <i>\"Be the change you wish to see in the world.\"</i> — Mahatma Gandhi",
    "⚡ <i>\"Success is not final, failure is not fatal.\"</i> — Churchill",
    "🎯 <i>\"The future belongs to those who believe in the beauty of their dreams.\"</i> — Roosevelt",
    "💪 <i>\"It always seems impossible until it's done.\"</i> — Nelson Mandela",
    "🧠 <i>\"Intelligence is the ability to adapt to change.\"</i> — Stephen Hawking",
]

JOKES = [
    "😂 <b>Why don't scientists trust atoms?</b>\nBecause they make up everything!",
    "😄 <b>Why did the scarecrow win an award?</b>\nHe was outstanding in his field! 🌾",
    "🤣 <b>What do you call fake spaghetti?</b>\nAn impasta! 🍝",
    "😆 <b>Why did the bicycle fall over?</b>\nIt was two-tired! 🚲",
    "😂 <b>Why can't you give Elsa a balloon?</b>\nShe'll let it go! ❄️",
    "🤣 <b>What do you call cheese that isn't yours?</b>\nNacho cheese! 🧀",
    "😄 <b>Why did the math book look sad?</b>\nBecause it had too many problems! 📚",
    "😂 <b>What do you call a fish without eyes?</b>\nA fsh! 🐟",
]

TRUTHS = [
    "What's your biggest fear you've never told anyone?",
    "What's the most embarrassing thing you've done in public?",
    "Have you ever pretended to be sick to get out of something?",
    "What's a secret talent you've been hiding?",
    "What's your biggest regret from the past year?",
    "Have you ever lied to a close friend? What about?",
    "What's something you're addicted to?",
    "What's the weirdest thing you've googled?",
]

DARES = [
    "🎤 Send a voice message singing a song right now!",
    "💌 Tag 3 friends and give each a genuine compliment!",
    "🎭 Speak in rhymes for your next 5 messages.",
    "🔢 Count to 20 in a language you barely know!",
    "🤳 Change your profile picture to something funny for 1 hour.",
    "📸 Post an embarrassing selfie in this chat!",
    "🗣️ Type only in CAPITALS for the next 10 minutes!",
    "🧏 Pretend you can only communicate in emojis for 5 messages!",
]

SLAPS = [
    "🐟 {user} slapped {target} with a large trout! The fish is shocked!",
    "👋 {user} delivered a thunderous slap to {target}! The room went silent.",
    "⚡ {user} slapped {target} so hard they saw stars! ⭐",
    "🧤 {user} put on a glove and slapped {target}!",
    "🤚 {user} gives {target} an epic open-handed slap!",
]

HUGS = [
    "🤗 {user} gave {target} a warm, cozy hug! So wholesome!",
    "🐻 {user} wrapped {target} in the biggest bear hug!",
    "💙 {user} hugged {target} tightly. Everything feels better now!",
    "✨ {user} and {target} share a magical hug! Friendship +100!",
]

KISSES = [
    "💋 {user} gave {target} a sweet kiss on the cheek! 🥰",
    "😘 {user} blew {target} a kiss across the room!",
    "💑 {user} and {target} shared a romantic moment! 💕",
]

PATS = [
    "🫶 {user} gave {target} a gentle head pat! So wholesome!",
    "😊 {user} patted {target} encouragingly. You've got this!",
    "🌸 {user} pats {target} on the back. Great job!",
]

POKES = [
    "👉 {user} poked {target}! Hey, pay attention!",
    "😆 {user} keeps poking {target}! Stop being AFK!",
    "🫷 {user} poked {target} in the ribs. Ouch!",
]

ROASTS = [
    "If laziness was a sport, you'd win gold — without trying.",
    "You're like a cloud. When you disappear, it's a beautiful day.",
    "I'd agree with you but then we'd both be wrong.",
    "You have the charm of a wet napkin and twice the density.",
    "Your Wi-Fi personality? Weak signal, constant disconnects.",
    "Even your shadow needs a break from you.",
    "If you were any slower, you'd be going backwards.",
    "You're not completely useless — you can always serve as a bad example.",
]

COMPLIMENTS = [
    "✨ You light up every room you walk into!",
    "🌟 Your kindness is contagious in the best way!",
    "💪 You're stronger than you think!",
    "🎨 Your creativity is genuinely inspiring!",
    "🧠 Your mind works in fascinating ways!",
    "💙 The world is genuinely better with you in it!",
    "🌸 You make hard things look effortlessly beautiful!",
    "🚀 You inspire others to be their best selves!",
]

TRIVIA_QUESTIONS = [
    {"q": "What is the capital of France?", "a": "Paris", "wrong": ["London", "Berlin", "Madrid"]},
    {"q": "How many planets are in our solar system?", "a": "8", "wrong": ["7", "9", "10"]},
    {"q": "What is the largest ocean on Earth?", "a": "Pacific", "wrong": ["Atlantic", "Indian", "Arctic"]},
    {"q": "Who painted the Mona Lisa?", "a": "Da Vinci", "wrong": ["Picasso", "Van Gogh", "Rembrandt"]},
    {"q": "What is the chemical symbol for Gold?", "a": "Au", "wrong": ["Ag", "Fe", "Cu"]},
    {"q": "Which planet is known as the Red Planet?", "a": "Mars", "wrong": ["Jupiter", "Saturn", "Venus"]},
    {"q": "What is the fastest land animal?", "a": "Cheetah", "wrong": ["Lion", "Horse", "Falcon"]},
    {"q": "How many sides does a hexagon have?", "a": "6", "wrong": ["5", "7", "8"]},
    {"q": "Who wrote Romeo and Juliet?", "a": "Shakespeare", "wrong": ["Dickens", "Tolstoy", "Austen"]},
    {"q": "What is H₂O?", "a": "Water", "wrong": ["Oxygen", "Hydrogen", "Salt"]},
]

WYR_QUESTIONS = [
    ("🔥 Be able to fly", "🌊 Be able to breathe underwater"),
    ("💰 Have unlimited money", "⏳ Live forever"),
    ("🧠 Be the smartest person alive", "😍 Be the most attractive person alive"),
    ("🎵 Know every language", "🎸 Master every musical instrument"),
    ("🌍 Travel anywhere instantly", "🏠 Have a mansion anywhere you want"),
    ("🦸 Have super strength", "🦊 Have super speed"),
    ("❄️ Always be cold", "🔥 Always be hot"),
    ("🐕 Be able to talk to animals", "🌱 Be able to grow any plant instantly"),
]

async def eightball_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Ask me a question!</b>\n<code>/8ball Will I win?</code>")
    q = " ".join(context.args)
    m = await animate_loading(update, "Consulting the magic ball")
    answer = random.choice(EIGHTBALL_ANSWERS)
    await finish_anim(m,
        f"╔══════════════════════╗\n║    🎱 <b>MAGIC 8-BALL</b>   ║\n╚══════════════════════╝\n\n"
        f"❓ <b>Q:</b> <i>{html.escape(q)}</i>\n\n"
        f"🎱 <b>A:</b> {answer}"
    )

async def roll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sides = int(context.args[0]) if context.args and context.args[0].isdigit() else 6
    if sides < 2: sides = 6
    m = await animate_loading(update, "Rolling")
    result = random.randint(1, sides)
    extra = ("🎯 <i>CRITICAL HIT!</i>" if result == sides else
             "💀 <i>CRITICAL FAIL!</i>" if result == 1 else "")
    await finish_anim(m,
        f"╔══════════════════════╗\n║    🎲 <b>DICE ROLL</b>     ║\n╚══════════════════════╝\n\n"
        f"🎲 <b>d{sides}</b> → <b>{result}</b>! {extra}"
    )

async def trivia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q_data = random.choice(TRIVIA_QUESTIONS)
    options = [q_data["a"]] + random.sample(q_data["wrong"], 3)
    random.shuffle(options)
    chat_id = update.effective_chat.id
    trivia_cache[chat_id] = {"answer": q_data["a"], "asked_at": time.time()}
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(opt, callback_data=f"trivia:{chat_id}:{opt}:{q_data['a']}")]
        for opt in options
    ])
    await reply(update,
        f"╔══════════════════════╗\n║     ❓ <b>TRIVIA!</b>      ║\n╚══════════════════════╝\n\n"
        f"🧠 <b>{html.escape(q_data['q'])}</b>\n\n"
        f"<i>Tap the correct answer below! ⬇️</i>",
        reply_markup=kb
    )

async def trivia_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    given, correct = parts[2], parts[3]
    if given == correct:
        reward = random.randint(10, 50)
        db = get_db()
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (reward, q.from_user.id))
        db.commit(); db.close()
        await q.answer(f"✅ Correct! +{reward} coins!", show_alert=True)
        await q.edit_message_text(
            f"╔══════════════════════╗\n║  ✅ <b>CORRECT!</b>     ║\n╚══════════════════════╝\n\n"
            f"🎉 {user_link(q.from_user)} got it right!\n"
            f"💰 Earned <b>+{reward} coins</b>!\n"
            f"📋 Answer: <b>{html.escape(correct)}</b>",
            parse_mode="HTML")
    else:
        await q.answer(f"❌ Wrong! The answer was: {correct}", show_alert=True)
        await q.edit_message_text(
            f"╔══════════════════════╗\n║  ❌ <b>WRONG!</b>       ║\n╚══════════════════════╝\n\n"
            f"😢 {user_link(q.from_user)} got it wrong!\n"
            f"📋 Answer was: <b>{html.escape(correct)}</b>",
            parse_mode="HTML")

async def wyr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    opt1, opt2 = random.choice(WYR_QUESTIONS)
    m = await animate_loading(update, "Generating question")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(opt1, callback_data=f"wyr:a"),
        InlineKeyboardButton(opt2, callback_data=f"wyr:b"),
    ]])
    await finish_anim(m,
        f"╔══════════════════════╗\n║  🤔 <b>WOULD YOU RATHER</b>  ║\n╚══════════════════════╝\n\n"
        f"<b>Option A:</b> {opt1}\n\n<i>OR</i>\n\n"
        f"<b>Option B:</b> {opt2}\n\n"
        f"<i>Vote below! ⬇️</i>",
        reply_markup=kb
    )

async def wyr_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    choice = "Option A" if q.data == "wyr:a" else "Option B"
    await q.message.reply_text(
        f"🗳️ {user_link(q.from_user)} chose <b>{choice}</b>!",
        parse_mode="HTML")

async def pp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context) or update.effective_user
    power  = random.randint(1, 100)
    bar    = progress_bar(power, 100, length=12)
    level  = ("💀 LEGENDARY" if power > 95 else
              "⚡ ULTRA" if power > 80 else
              "🔥 HIGH" if power > 60 else
              "✨ AVERAGE" if power > 40 else
              "😴 LOW" if power > 20 else
              "💤 ROCK BOTTOM")
    await reply(update,
        f"╔══════════════════════╗\n║  💪 <b>POWER LEVEL</b>   ║\n╚══════════════════════╝\n\n"
        f"👤 {user_link(target)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"[{bar}] <b>{power}%</b>\n"
        f"⚡ <b>Status:</b> {level}"
    )

async def slap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to someone to slap them!")
    msg = random.choice(SLAPS).format(user=user_link(update.effective_user), target=user_link(target))
    await reply(update, f"╔══════════════════════╗\n║    👋 <b>SLAP!</b>        ║\n╚══════════════════════╝\n\n{msg}")

async def hug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to someone to hug them!")
    msg = random.choice(HUGS).format(user=user_link(update.effective_user), target=user_link(target))
    await reply(update, f"╔══════════════════════╗\n║    🤗 <b>HUG!</b>         ║\n╚══════════════════════╝\n\n{msg}")

async def kiss_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to someone to kiss them!")
    msg = random.choice(KISSES).format(user=user_link(update.effective_user), target=user_link(target))
    await reply(update, f"╔══════════════════════╗\n║    💋 <b>KISS!</b>         ║\n╚══════════════════════╝\n\n{msg}")

async def pat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to someone to pat them!")
    msg = random.choice(PATS).format(user=user_link(update.effective_user), target=user_link(target))
    await reply(update, f"🫶 {msg}")

async def poke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to someone to poke them!")
    msg = random.choice(POKES).format(user=user_link(update.effective_user), target=user_link(target))
    await reply(update, f"👉 {msg}")

async def ship_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        u1 = update.effective_user; u2 = update.message.reply_to_message.from_user
    elif context.args:
        u1 = update.effective_user
        u2 = type("U", (), {"first_name": context.args[0], "id": 0})()
    else:
        return await reply(update, "❓ Reply to a user or provide a name.")
    m = await animate_loading(update, "Calculating compatibility")
    compat = random.randint(1, 100)
    hearts = "❤️" * (compat // 10) + "🖤" * (10 - compat // 10)
    verdict = ("💞 A match made in heaven!" if compat >= 80 else
               "💕 Very compatible!" if compat >= 60 else
               "💙 There's potential..." if compat >= 40 else
               "💔 Not the best match...")
    n2 = html.escape(u2.first_name or "?")
    await finish_anim(m,
        f"╔══════════════════════╗\n║   💕 <b>SHIP METER</b>    ║\n╚══════════════════════╝\n\n"
        f"{user_link(u1)} ❤️ {n2}\n\n"
        f"[{hearts}]\n"
        f"💯 <b>{compat}% compatible!</b>\n"
        f"<i>{verdict}</i>"
    )

async def roast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    name   = user_link(target) if target else user_link(update.effective_user)
    await reply(update, f"╔══════════════════════╗\n║    🔥 <b>ROASTED!</b>     ║\n╚══════════════════════╝\n\n🔥 {name}:\n<i>{random.choice(ROASTS)}</i>")

async def compliment_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    name   = user_link(target) if target else user_link(update.effective_user)
    await reply(update, f"╔══════════════════════╗\n║   💐 <b>COMPLIMENT</b>    ║\n╚══════════════════════╝\n\n💐 {name}:\n{random.choice(COMPLIMENTS)}")

async def joke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, f"╔══════════════════════╗\n║    😂 <b>JOKE!</b>        ║\n╚══════════════════════╝\n\n{random.choice(JOKES)}")

async def fact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, f"╔══════════════════════╗\n║   🧠 <b>RANDOM FACT</b>    ║\n╚══════════════════════╝\n\n{random.choice(FACTS)}")

async def quote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, f"╔══════════════════════╗\n║   💬 <b>DAILY QUOTE</b>   ║\n╚══════════════════════╝\n\n{random.choice(QUOTES)}")

async def truth_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, f"╔══════════════════════╗\n║   💭 <b>TRUTH!</b>         ║\n╚══════════════════════╝\n\n🤔 <i>{random.choice(TRUTHS)}</i>")

async def dare_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, f"╔══════════════════════╗\n║   😈 <b>DARE!</b>           ║\n╚══════════════════════╝\n\n{random.choice(DARES)}")

async def meme_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memes = [
        "🧠 When you say 'just one more episode' at 3am... 🧠",
        "🤔 Me: I should sleep\nAlso me: Let me research the economic history of the Byzantine Empire",
        "💻 Error: undefined is not a function\nMe: 🎉 I found the bug!\nAlso me: 😭",
        "🛌 My 8am alarm vs My 8:07am alarm:\nFirst: *barely wakes up*\nSecond: ATOMIC BOMB",
        "📱 Me texting: 'On my way!' *hasn't left bed yet*",
    ]
    await reply(update, f"╔══════════════════════╗\n║     😎 <b>MEME</b>          ║\n╚══════════════════════╝\n\n{random.choice(memes)}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         🔧 UTILITY
# ═══════════════════════════════════════════════════════════════════════════════
async def calc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/calc expression</code>")
    expr = " ".join(context.args)
    allowed = set("0123456789+-*/().% ")
    if not all(c in allowed for c in expr):
        return await reply(update, "❌ <b>Invalid characters!</b> Only: +, -, *, /, (), %, numbers")
    try:
        result = eval(expr, {"__builtins__": {}}, {})
        await reply(update,
            f"╔══════════════════════╗\n║    🧮 <b>CALCULATOR</b>   ║\n╚══════════════════════╝\n\n"
            f"📝 <code>{html.escape(expr)}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>= {result}</b>"
        )
    except Exception as e:
        await reply(update, f"❌ <b>Math Error:</b> {html.escape(str(e))}")

async def qr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/qr text or URL</code>")
    import qrcode
    text = " ".join(context.args)
    m = await animate_loading(update, "Generating QR code")
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO(); img.save(buf, "PNG"); buf.seek(0)
        try: await m.delete()
        except: pass
        await update.message.reply_photo(buf,
            caption=f"📱 <b>QR Code</b>\n<code>{html.escape(text[:50])}</code>",
            parse_mode="HTML")
    except Exception as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/tr lang text</code>\nExample: <code>/tr es Hello!</code>")
    lang = context.args[0]
    text = " ".join(context.args[1:]) if len(context.args) > 1 else (
        update.message.reply_to_message.text if update.message.reply_to_message else "")
    if not text: return await reply(update, "❌ <b>Provide text to translate!</b>")
    m = await animate_loading(update, "Translating")
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={lang}&dt=t&q={urllib.parse.quote(text)}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                translated = "".join(p[0] for p in data[0] if p[0])
                await finish_anim(m,
                    f"╔══════════════════════╗\n║   🌐 <b>TRANSLATION</b>   ║\n╚══════════════════════╝\n\n"
                    f"🔤 <b>Original:</b>\n<i>{html.escape(text[:200])}</i>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🌍 <b>→ {lang.upper()}:</b>\n{html.escape(translated)}"
                )
    except Exception as e:
        await finish_anim(m, f"❌ <b>Translation failed:</b> {html.escape(str(e))}")

async def hash_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/hash text</code>")
    text = " ".join(context.args).encode()
    md5    = hashlib.md5(text).hexdigest()
    sha1   = hashlib.sha1(text).hexdigest()
    sha256 = hashlib.sha256(text).hexdigest()
    await reply(update,
        f"╔══════════════════════╗\n║    🔐 <b>HASHES</b>       ║\n╚══════════════════════╝\n\n"
        f"🔑 <b>MD5:</b>\n<code>{md5}</code>\n\n"
        f"🔑 <b>SHA1:</b>\n<code>{sha1}</code>\n\n"
        f"🔑 <b>SHA256:</b>\n<code>{sha256}</code>"
    )

async def b64_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await reply(update, "❓ <b>Usage:</b> <code>/b64 encode|decode text</code>")
    mode = context.args[0].lower()
    text = " ".join(context.args[1:])
    try:
        if mode == "encode":
            result = base64.b64encode(text.encode()).decode(); label = "📤 Encoded"
        else:
            result = base64.b64decode(text.encode()).decode(); label = "📥 Decoded"
        await reply(update, f"╔══════════════════════╗\n║    🔢 <b>BASE64</b>       ║\n╚══════════════════════╝\n\n{label}:\n<code>{html.escape(result)}</code>")
    except Exception as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/weather city</code>")
    city = " ".join(context.args)
    m = await animate_loading(update, "Fetching weather")
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                cur  = data["current_condition"][0]
                desc = cur["weatherDesc"][0]["value"]
                area = data["nearest_area"][0]["areaName"][0]["value"]
                icons = {"Clear":"☀️","Sunny":"☀️","Cloudy":"☁️","Rain":"🌧️",
                         "Snow":"❄️","Thunder":"⛈️","Fog":"🌫️","Partly":"⛅"}
                icon = next((v for k, v in icons.items() if k.lower() in desc.lower()), "🌤️")
                await finish_anim(m,
                    f"╔══════════════════════════╗\n║  {icon} <b>WEATHER — {html.escape(area[:10])}</b>  ║\n╚══════════════════════════╝\n\n"
                    f"🌡️ <b>Temp:</b> {cur['temp_C']}°C / {cur['temp_F']}°F\n"
                    f"🤔 <b>Feels:</b> {cur['FeelsLikeC']}°C\n"
                    f"📋 <b>Condition:</b> {html.escape(desc)}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💧 <b>Humidity:</b> {cur['humidity']}%\n"
                    f"💨 <b>Wind:</b> {cur['windspeedKmph']} km/h\n"
                    f"👁️ <b>Visibility:</b> {cur['visibility']} km"
                )
    except Exception as e:
        await finish_anim(m, f"❌ <b>Weather lookup failed:</b> {html.escape(str(e))}")

async def time_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tz_str = " ".join(context.args) if context.args else "UTC"
    try:
        tz  = pytz.timezone(tz_str)
        now = datetime.datetime.now(tz)
        h   = now.hour
        tod = ("🌅 Morning" if 5 <= h < 12 else "☀️ Afternoon" if 12 <= h < 17
               else "🌇 Evening" if 17 <= h < 21 else "🌙 Night")
        await reply(update,
            f"╔══════════════════════╗\n║    🕐 <b>CURRENT TIME</b>   ║\n╚══════════════════════╝\n\n"
            f"📍 <b>Timezone:</b> {html.escape(tz_str)}\n"
            f"🗓️ <b>Date:</b> {now.strftime('%Y-%m-%d')}\n"
            f"⏰ <b>Time:</b> {now.strftime('%H:%M:%S %Z')}\n"
            f"🌞 <b>Period:</b> {tod}"
        )
    except:
        await reply(update, f"❌ <b>Unknown timezone:</b> <code>{html.escape(tz_str)}</code>")

async def reverse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else (
        update.message.reply_to_message.text if update.message.reply_to_message else "")
    if not text: return await reply(update, "❓ <b>Usage:</b> <code>/reverse text</code>")
    await reply(update,
        f"╔══════════════════════╗\n║    🔄 <b>REVERSED</b>     ║\n╚══════════════════════╝\n\n"
        f"📝 <b>Original:</b> {html.escape(text[:100])}\n"
        f"🔁 <b>Reversed:</b> {html.escape(text[::-1][:100])}"
    )

async def ascii_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/ascii text</code>")
    text   = " ".join(context.args)
    result = " ".join(str(ord(c)) for c in text[:20])
    await reply(update,
        f"╔══════════════════════╗\n║    💻 <b>ASCII CODES</b>   ║\n╚══════════════════════╝\n\n"
        f"📝 <code>{html.escape(text[:20])}</code>\n"
        f"🔢 <code>{html.escape(result)}</code>"
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                     ⚙️ SETTINGS PANEL (INTERACTIVE)
# ═══════════════════════════════════════════════════════════════════════════════
async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_chat(update.effective_chat.id)
    if not cfg:
        ensure_chat(update.effective_chat)
        cfg = get_chat(update.effective_chat.id)
    text = (
        f"╔══════════════════════════════╗\n"
        f"║  ⚙️ <b>SETTINGS — {html.escape((update.effective_chat.title or '')[:12])}</b>  ║\n"
        f"╚══════════════════════════════╝\n\n"
        f"<i>Navigate panels using the buttons below:</i>"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡️ Protection", callback_data="protect_panel"),
         InlineKeyboardButton("🔒 Locks", callback_data="locks_panel")],
        [InlineKeyboardButton("👋 Welcome", callback_data="welcome_panel"),
         InlineKeyboardButton("💰 Economy", callback_data="economy_panel")],
        [InlineKeyboardButton("🗃️ Other", callback_data="other_panel")],
    ])
    if update.callback_query:
        try: await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except: pass
    else:
        await reply(update, text, reply_markup=kb)

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not await is_admin(context, q.message.chat_id, q.from_user.id):
        return await q.answer("🚫 Admins only!", show_alert=True)
    await q.answer()
    data = q.data
    chat_id = q.message.chat_id
    cfg = get_chat(chat_id)

    if data == "protect_panel":
        text = (f"╔══════════════════════════╗\n║   🛡️ <b>PROTECTION PANEL</b>   ║\n"
                f"╠══════════════════════════╣\n║  Tap to toggle!           ║\n╚══════════════════════════╝")
        try: await q.edit_message_text(text, parse_mode="HTML", reply_markup=_build_protect_kb(cfg))
        except: pass
    elif data == "locks_panel":
        text = (f"╔══════════════════════════╗\n║      🔒 <b>LOCK PANEL</b>       ║\n"
                f"╠══════════════════════════╣\n║  Tap to toggle!           ║\n╚══════════════════════════╝\n"
                f"<i>🟢 = Allowed • 🔴 = Locked</i>")
        try: await q.edit_message_text(text, parse_mode="HTML", reply_markup=_build_locks_kb(cfg))
        except: pass
    elif data == "welcome_panel":
        text = (
            f"╔══════════════════════════╗\n║   👋 <b>WELCOME SETTINGS</b>    ║\n╚══════════════════════════╝\n\n"
            f"{tog(cfg.get('greetmembers',1))} Welcome Messages\n"
            f"{tog(cfg.get('goodbye_enabled',1))} Goodbye Messages\n"
            f"{tog(cfg.get('welcome_captcha',0))} Captcha Verification\n"
            f"{tog(cfg.get('clean_service',0))} Clean Service Messages\n"
            f"⏱️ Welcome delete: {cfg.get('welcome_delete_after', 0)}s"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{'✅' if cfg.get('greetmembers',1) else '❌'} Welcome",
                                  callback_data="toggle:greetmembers"),
             InlineKeyboardButton(f"{'✅' if cfg.get('goodbye_enabled',1) else '❌'} Goodbye",
                                  callback_data="toggle:goodbye_enabled")],
            [InlineKeyboardButton(f"{'✅' if cfg.get('welcome_captcha',0) else '❌'} Captcha",
                                  callback_data="toggle:welcome_captcha"),
             InlineKeyboardButton(f"{'✅' if cfg.get('clean_service',0) else '❌'} Clean Service",
                                  callback_data="toggle:clean_service")],
            [InlineKeyboardButton("« Back", callback_data="settings_back")],
        ])
        try: await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except: pass
    elif data == "economy_panel":
        text = (
            f"╔══════════════════════════╗\n║   💰 <b>ECONOMY SETTINGS</b>   ║\n╚══════════════════════════╝\n\n"
            f"{tog(cfg.get('economy_enabled',1))} Economy System\n"
            f"{tog(cfg.get('rep_enabled',1))} Reputation System\n"
            f"{tog(cfg.get('fun_enabled',1))} Fun Commands\n"
            f"{tog(cfg.get('report_enabled',1))} Report System"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{'✅' if cfg.get('economy_enabled',1) else '❌'} Economy",
                                  callback_data="toggle:economy_enabled"),
             InlineKeyboardButton(f"{'✅' if cfg.get('rep_enabled',1) else '❌'} Reputation",
                                  callback_data="toggle:rep_enabled")],
            [InlineKeyboardButton(f"{'✅' if cfg.get('fun_enabled',1) else '❌'} Fun",
                                  callback_data="toggle:fun_enabled"),
             InlineKeyboardButton(f"{'✅' if cfg.get('report_enabled',1) else '❌'} Reports",
                                  callback_data="toggle:report_enabled")],
            [InlineKeyboardButton("« Back", callback_data="settings_back")],
        ])
        try: await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except: pass
    elif data == "other_panel":
        text = (
            f"╔══════════════════════════╗\n║   🗃️ <b>OTHER SETTINGS</b>     ║\n╚══════════════════════════╝\n\n"
            f"{tog(cfg.get('delete_commands',0))} Delete Commands\n"
            f"⚠️ Warn limit: {cfg.get('warn_limit',3)} → {cfg.get('warn_action','mute')}\n"
            f"🌊 Flood: {cfg.get('flood_count',5)} msgs/{cfg.get('flood_time',5)}s → {cfg.get('flood_action','mute')}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{'✅' if cfg.get('delete_commands',0) else '❌'} Delete Commands",
                                  callback_data="toggle:delete_commands")],
            [InlineKeyboardButton("« Back", callback_data="settings_back")],
        ])
        try: await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except: pass
    elif data == "settings_back":
        text = (f"╔══════════════════════════════╗\n║  ⚙️ <b>SETTINGS — {html.escape((q.message.chat.title or '')[:12])}</b>  ║\n╚══════════════════════════════╝\n\n"
                f"<i>Navigate panels below:</i>")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛡️ Protection", callback_data="protect_panel"),
             InlineKeyboardButton("🔒 Locks", callback_data="locks_panel")],
            [InlineKeyboardButton("👋 Welcome", callback_data="welcome_panel"),
             InlineKeyboardButton("💰 Economy", callback_data="economy_panel")],
            [InlineKeyboardButton("🗃️ Other", callback_data="other_panel")],
        ])
        try: await q.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except: pass

async def toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not await is_admin(context, q.message.chat_id, q.from_user.id):
        return await q.answer("🚫 Admins only!", show_alert=True)
    await q.answer()
    key = q.data.split(":")[1]
    cfg = get_chat(q.message.chat_id)
    new_val = 0 if cfg.get(key, 0) else 1
    set_setting(q.message.chat_id, key, new_val)
    await q.answer(f"{'✅ Enabled' if new_val else '❌ Disabled'}: {key}", show_alert=False)

# ─── MISC SETTINGS ─────────────────────────────────────────────────────────────
@admin_only
async def cleanservice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "clean_service", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Clean service messages {'on' if val else 'off'}!</b>")

@admin_only
async def delcommands_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "delete_commands", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Delete commands {'on' if val else 'off'}!</b>")

# ═══════════════════════════════════════════════════════════════════════════════
#                         📅 SCHEDULE
# ═══════════════════════════════════════════════════════════════════════════════
@admin_only
async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await reply(update,
            "╔══════════════════════╗\n║  📅 <b>SCHEDULE</b>       ║\n╚══════════════════════╝\n\n"
            "❓ <b>Usage:</b> <code>/schedule 1h Your message</code>\n"
            "⏱️ Durations: 1m, 1h, 1d, 1w"
        )
    time_str = context.args[0]
    message  = " ".join(context.args[1:])
    duration = parse_duration(time_str)
    if not duration: return await reply(update, "❌ <b>Invalid duration.</b>")
    next_run = datetime.datetime.now(pytz.utc) + duration
    db = get_db()
    db.execute("INSERT INTO schedules (chat_id, message, next_run, created_by) VALUES (?,?,?,?)",
               (update.effective_chat.id, message, next_run.isoformat(), update.effective_user.id))
    db.commit(); db.close()
    await reply(update,
        f"✅ <b>Scheduled!</b>\n"
        f"⏰ <b>In:</b> {html.escape(fmt_duration(duration))}\n"
        f"📅 <b>At:</b> {next_run.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"💬 <b>Message:</b> {html.escape(message[:80])}"
    )

async def run_scheduler(context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    now = datetime.datetime.now(pytz.utc)
    rows = db.execute(
        "SELECT * FROM schedules WHERE is_active=1 AND next_run<=?",
        (now.isoformat(),)).fetchall()
    for row in rows:
        try:
            await context.bot.send_message(row["chat_id"], row["message"], parse_mode="HTML")
        except: pass
        if row["repeat"] == "none":
            db.execute("UPDATE schedules SET is_active=0 WHERE id=?", (row["id"],))
        else:
            delta = parse_duration(f"{row['repeat_val']}{row['repeat'][0]}")
            if delta:
                nxt = now + delta
                db.execute("UPDATE schedules SET next_run=? WHERE id=?", (nxt.isoformat(), row["id"]))
    db.commit(); db.close()

# ═══════════════════════════════════════════════════════════════════════════════
#                     👑 OWNER / ADMIN COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════
@owner_only
async def chatlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Fetching chat list")
    db = get_db()
    rows = db.execute("SELECT chat_id, title, chat_type FROM chats ORDER BY title LIMIT 50").fetchall()
    db.close()
    lines = [f"╔══════════════════════╗\n║  💬 <b>CHAT LIST ({len(rows)})</b>  ║\n╚══════════════════════╝\n"]
    icons = {"group":"👥","supergroup":"💬","channel":"📣","private":"👤"}
    for r in rows:
        icon = icons.get(r["chat_type"], "💬")
        lines.append(f"{icon} {html.escape(r['title'] or 'Unknown')} <code>{r['chat_id']}</code>")
    await finish_anim(m, "\n".join(lines))

@owner_only
async def leave_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = int(context.args[0]) if context.args else update.effective_chat.id
    try:
        await context.bot.leave_chat(chat_id)
        await reply(update, f"✅ <b>Left chat {chat_id}!</b>")
    except Exception as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

@owner_only
async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Creating backup")
    chat_id = update.effective_chat.id
    db = get_db()
    notes   = db.execute("SELECT * FROM notes WHERE chat_id=?", (chat_id,)).fetchall()
    filters = db.execute("SELECT * FROM filters WHERE chat_id=?", (chat_id,)).fetchall()
    bl      = db.execute("SELECT * FROM blacklist WHERE chat_id=?", (chat_id,)).fetchall()
    cfg     = get_chat(chat_id)
    db.close()
    backup = {
        "chat_id": chat_id,
        "timestamp": datetime.datetime.now(pytz.utc).isoformat(),
        "config": dict(cfg),
        "notes": [dict(n) for n in notes],
        "filters": [dict(f) for f in filters],
        "blacklist": [dict(b) for b in bl],
    }
    buf  = io.BytesIO(json.dumps(backup, indent=2, default=str).encode())
    fname = f"backup_{chat_id}_{datetime.date.today()}.json"
    try: await m.delete()
    except: pass
    await update.message.reply_document(buf, filename=fname,
                                        caption=f"💾 <b>Backup complete!</b>\n"
                                                f"📊 {len(notes)} notes, {len(filters)} filters, {len(bl)} blacklist words",
                                        parse_mode="HTML")

# ─── HANDLE MEMBER UPDATES ────────────────────────────────────────────────────
async def chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    chat = result.chat; ensure_chat(chat)
    if result.new_chat_member and result.new_chat_member.status in ("member","administrator","creator"):
        user = result.new_chat_member.user
        ensure_user(user); track_member(chat.id, user)

# ─── MAIN MESSAGE HANDLER ─────────────────────────────────────────────────────
async def main_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user or not update.effective_chat: return
    if update.effective_chat.type == "private": return

    user = update.effective_user
    chat = update.effective_chat
    ensure_chat(chat); ensure_user(user)
    track_member(chat.id, user, increment_msg=True)

    reason = is_gbanned(user.id)
    if reason:
        try:
            await context.bot.ban_chat_member(chat.id, user.id)
            await context.bot.send_message(chat.id,
                f"🌍 <b>Globally banned user removed!</b>\n📝 {html.escape(reason)}",
                parse_mode="HTML")
            return
        except: pass

    await afk_check_handler(update, context)
    await antispam_handler(update, context)
    await blacklist_handler(update, context)
    await filter_handler(update, context)
    await hash_note_handler(update, context)

    if update.message.text:
        txt = update.message.text.lower()
        if "@admins" in txt or "@admin" in txt:
            await tag_admins_handler(update, context)
        if update.message.text.strip() in ("+rep", "+1") and update.message.reply_to_message:
            await rep_cmd(update, context)

    cfg = get_chat(chat.id)
    if cfg.get("delete_commands") and update.message.text and update.message.text.startswith("/"):
        try: await update.message.delete()
        except: pass

# ═══════════════════════════════════════════════════════════════════════════════
#                          BOT SETUP & RUN
# ═══════════════════════════════════════════════════════════════════════════════
def build_commands():
    return [
        BotCommand("start",          "🤖 Start the bot"),
        BotCommand("help",           "📖 Help menu"),
        BotCommand("ban",            "🔨 Ban user"),
        BotCommand("tban",           "⏱️ Temp ban"),
        BotCommand("unban",          "🔓 Unban user"),
        BotCommand("kick",           "👢 Kick user"),
        BotCommand("mute",           "🔇 Mute user"),
        BotCommand("tmute",          "⏱️ Temp mute"),
        BotCommand("unmute",         "🔊 Unmute user"),
        BotCommand("warn",           "⚠️ Warn user"),
        BotCommand("warns",          "📋 View warns"),
        BotCommand("unwarn",         "✅ Remove warn"),
        BotCommand("resetwarn",      "🗑️ Reset warns"),
        BotCommand("promote",        "⬆️ Promote user"),
        BotCommand("demote",         "⬇️ Demote user"),
        BotCommand("admintitle",     "🏷️ Set admin title"),
        BotCommand("adminlist",      "👮 List admins"),
        BotCommand("purge",          "🗑️ Delete messages"),
        BotCommand("del",            "🗑️ Delete message"),
        BotCommand("pin",            "📌 Pin message"),
        BotCommand("unpin",          "📌 Unpin message"),
        BotCommand("slowmode",       "🐢 Set slowmode"),
        BotCommand("zombies",        "🧟 Count zombies"),
        BotCommand("kickzombies",    "💥 Remove zombies"),
        BotCommand("lock",           "🔒 Lock content type"),
        BotCommand("unlock",         "🔓 Unlock content"),
        BotCommand("locks",          "🔒 Lock panel"),
        BotCommand("protect",        "🛡️ Protection panel"),
        BotCommand("antispam",       "🛡️ Toggle anti-spam"),
        BotCommand("antiflood",      "🌊 Toggle anti-flood"),
        BotCommand("setflood",       "⚙️ Set flood limit"),
        BotCommand("antilink",       "🔗 Toggle anti-link"),
        BotCommand("antiforward",    "↩️ Toggle anti-forward"),
        BotCommand("antibot",        "🤖 Toggle anti-bot"),
        BotCommand("antinsfw",       "🔞 Toggle anti-NSFW"),
        BotCommand("antiarabic",     "🔤 Toggle anti-Arabic"),
        BotCommand("antiraid",       "🚨 Toggle anti-raid"),
        BotCommand("setrules",       "📜 Set rules"),
        BotCommand("rules",          "📜 Show rules"),
        BotCommand("setwelcome",     "👋 Set welcome message"),
        BotCommand("setgoodbye",     "👋 Set goodbye message"),
        BotCommand("welcome",        "👋 Toggle welcome"),
        BotCommand("goodbye",        "👋 Toggle goodbye"),
        BotCommand("captcha",        "🔐 Toggle captcha"),
        BotCommand("save",           "💾 Save note"),
        BotCommand("get",            "📝 Get note"),
        BotCommand("notes",          "📋 List notes"),
        BotCommand("clear",          "🗑️ Delete note"),
        BotCommand("filter",         "🔍 Add filter"),
        BotCommand("filters",        "📋 List filters"),
        BotCommand("stop",           "🛑 Remove filter"),
        BotCommand("addbl",          "🚫 Blacklist word"),
        BotCommand("rmbl",           "✅ Remove from blacklist"),
        BotCommand("blacklist",      "📋 Show blacklist"),
        BotCommand("report",         "🚨 Report message"),
        BotCommand("afk",            "😴 Set AFK"),
        BotCommand("settings",       "⚙️ Settings panel"),
        BotCommand("daily",          "💰 Claim daily"),
        BotCommand("work",           "💼 Work for coins"),
        BotCommand("mine",           "⛏️ Mine coins"),
        BotCommand("coins",          "💳 Check balance"),
        BotCommand("bank",           "🏦 Bank system"),
        BotCommand("give",           "💸 Give coins"),
        BotCommand("rob",            "🦹 Rob coins"),
        BotCommand("flip",           "🪙 Coin flip"),
        BotCommand("slots",          "🎰 Slot machine"),
        BotCommand("shop",           "🛍️ View shop"),
        BotCommand("buy",            "🛒 Buy item"),
        BotCommand("inventory",      "🎒 Your inventory"),
        BotCommand("leaderboard",    "🏆 Leaderboard"),
        BotCommand("rank",           "🏆 Your rank"),
        BotCommand("top",            "📊 Top members"),
        BotCommand("level",          "⭐ Your level"),
        BotCommand("rep",            "⭐ Give reputation"),
        BotCommand("reprank",        "📊 Rep leaderboard"),
        BotCommand("id",             "🆔 Get IDs"),
        BotCommand("info",           "👤 User profile"),
        BotCommand("chatinfo",       "💬 Chat info"),
        BotCommand("ping",           "🏓 Ping bot"),
        BotCommand("uptime",         "⏱️ Bot uptime"),
        BotCommand("calc",           "🧮 Calculator"),
        BotCommand("qr",             "📱 QR code"),
        BotCommand("tr",             "🌐 Translate"),
        BotCommand("hash",           "🔐 Hash text"),
        BotCommand("b64",            "🔢 Base64"),
        BotCommand("weather",        "🌤️ Weather"),
        BotCommand("time",           "🕐 Current time"),
        BotCommand("reverse",        "🔄 Reverse text"),
        BotCommand("8ball",          "🎱 Magic 8-ball"),
        BotCommand("roll",           "🎲 Roll dice"),
        BotCommand("trivia",         "❓ Trivia quiz"),
        BotCommand("wyr",            "🤔 Would you rather"),
        BotCommand("pp",             "💪 Power level"),
        BotCommand("slap",           "👋 Slap user"),
        BotCommand("hug",            "🤗 Hug user"),
        BotCommand("kiss",           "💋 Kiss user"),
        BotCommand("pat",            "🫶 Pat user"),
        BotCommand("poke",           "👉 Poke user"),
        BotCommand("ship",           "💕 Ship users"),
        BotCommand("roast",          "🔥 Roast user"),
        BotCommand("compliment",     "💐 Compliment"),
        BotCommand("joke",           "😂 Random joke"),
        BotCommand("fact",           "🧠 Random fact"),
        BotCommand("quote",          "💬 Quote"),
        BotCommand("truth",          "💭 Truth question"),
        BotCommand("dare",           "😈 Dare"),
        BotCommand("meme",           "😎 Meme text"),
        BotCommand("schedule",       "📅 Schedule message"),
        BotCommand("newfed",         "🌐 Create federation"),
        BotCommand("joinfed",        "🌐 Join federation"),
        BotCommand("leavefed",       "🌐 Leave federation"),
        BotCommand("fedinfo",        "ℹ️ Fed info"),
        BotCommand("fban",           "🚫 Fed ban"),
        BotCommand("unfban",         "✅ Fed unban"),
        BotCommand("fedbans",        "📋 Fed bans"),
        BotCommand("fadmin",         "👮 Add fed admin"),
        BotCommand("fremove",        "👤 Remove fed admin"),
        BotCommand("connect",        "🔗 Connect to group"),
        BotCommand("disconnect",     "🔌 Disconnect"),
        BotCommand("connected",      "📡 Connection info"),
        BotCommand("gban",           "🌍 Global ban"),
        BotCommand("ungban",         "✅ Remove gban"),
        BotCommand("sudo",           "👑 Add sudo user"),
        BotCommand("unsudo",         "👤 Remove sudo"),
        BotCommand("broadcast",      "📢 Broadcast"),
        BotCommand("broadcastall",   "📢 Broadcast all"),
        BotCommand("botstats",       "📊 Bot stats"),
        BotCommand("chatlist",       "💬 Chat list"),
        BotCommand("leave",          "🚪 Leave chat"),
        BotCommand("backup",         "💾 Backup chat"),
        BotCommand("setwarnlimit",   "⚙️ Warn limit"),
        BotCommand("setwarnaction",  "⚙️ Warn action"),
        BotCommand("cleanservice",   "🧹 Clean service"),
        BotCommand("delcommands",    "🗑️ Delete commands"),
        BotCommand("welcdel",        "⏱️ Welcome delete"),
        BotCommand("blmode",         "⚙️ Blacklist action"),
        BotCommand("ascii",          "💻 ASCII codes"),
        BotCommand("setfloodaction", "⚙️ Flood action"),
        BotCommand("setraid",        "🚨 Raid threshold"),
        BotCommand("cas",            "🛡️ CAS protection"),
    ][:100]

async def post_init(application: Application):
    try:
        await application.bot.set_my_commands(build_commands())
        info = await application.bot.get_me()
        logger.info(f"✅ {info.first_name} (@{info.username}) initialized — v{VERSION}")
        db = get_db()
        connections = db.execute("SELECT user_id, chat_id FROM connections").fetchall()
        db.close()
        for conn in connections:
            connection_cache[conn["user_id"]] = conn["chat_id"]
        logger.info(f"✅ Restored {len(connections)} connections")
        db = get_db()
        afk_users = db.execute("SELECT user_id, afk_reason, afk_since FROM users WHERE is_afk=1").fetchall()
        db.close()
        for u in afk_users:
            try:
                since = datetime.datetime.fromisoformat(str(u["afk_since"]).replace(" ","T")).replace(tzinfo=pytz.utc)
            except:
                since = datetime.datetime.now(pytz.utc)
            afk_cache[u["user_id"]] = {"reason": u["afk_reason"] or "", "since": since}
        logger.info(f"✅ Restored {len(afk_users)} AFK statuses")
    except Exception as e:
        logger.error(f"Post-init error: {e}")

def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    init_db()
    logger.info(f"🚀 Starting NEXUS Bot {VERSION}")

    app = (Application.builder()
           .token(BOT_TOKEN)
           .post_init(post_init)
           .build())

    # ── Core ──────────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",         start_cmd))
    app.add_handler(CommandHandler("help",          help_cmd))
    app.add_handler(CallbackQueryHandler(help_callback, pattern=r"^help_"))

    # ── Moderation ────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("ban",            ban_cmd))
    app.add_handler(CommandHandler("tban",           tban_cmd))
    app.add_handler(CommandHandler("sban",           sban_cmd))
    app.add_handler(CommandHandler("unban",          unban_cmd))
    app.add_handler(CommandHandler("kick",           kick_cmd))
    app.add_handler(CommandHandler("skick",          skick_cmd))
    app.add_handler(CommandHandler("mute",           mute_cmd))
    app.add_handler(CommandHandler("tmute",          tmute_cmd))
    app.add_handler(CommandHandler("unmute",         unmute_cmd))
    app.add_handler(CommandHandler("warn",           warn_cmd))
    app.add_handler(CommandHandler("dwarn",          dwarn_cmd))
    app.add_handler(CommandHandler("swarn",          swarn_cmd))
    app.add_handler(CommandHandler("unwarn",         unwarn_cmd))
    app.add_handler(CommandHandler("resetwarn",      resetwarn_cmd))
    app.add_handler(CommandHandler("warns",          warns_cmd))
    app.add_handler(CommandHandler("setwarnlimit",   setwarnlimit_cmd))
    app.add_handler(CommandHandler("setwarnaction",  setwarnaction_cmd))
    app.add_handler(CommandHandler("promote",        promote_cmd))
    app.add_handler(CommandHandler("demote",         demote_cmd))
    app.add_handler(CommandHandler("admintitle",     admintitle_cmd))
    app.add_handler(CommandHandler("adminlist",      adminlist_cmd))
    app.add_handler(CommandHandler("zombies",        zombies_cmd))
    app.add_handler(CommandHandler("kickzombies",    kickzombies_cmd))
    app.add_handler(CommandHandler("pin",            pin_cmd))
    app.add_handler(CommandHandler("unpin",          unpin_cmd))
    app.add_handler(CommandHandler("unpinall",       unpinall_cmd))
    app.add_handler(CommandHandler("purge",          purge_cmd))
    app.add_handler(CommandHandler("del",            del_cmd))
    app.add_handler(CommandHandler("slowmode",       slowmode_cmd))
    app.add_handler(CallbackQueryHandler(unban_callback,      pattern=r"^unban:"))
    app.add_handler(CallbackQueryHandler(unmute_callback,     pattern=r"^unmute:"))
    app.add_handler(CallbackQueryHandler(warn_action_callback, pattern=r"^(unwarn|resetwarn):"))

    # ── Locks ─────────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("lock",           lock_cmd))
    app.add_handler(CommandHandler("unlock",         unlock_cmd))
    app.add_handler(CommandHandler("locks",          locks_cmd))
    app.add_handler(CallbackQueryHandler(lock_toggle_callback, pattern=r"^(lock_toggle|lock_all):"))

    # ── Protection ────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("protect",        protect_cmd))
    app.add_handler(CommandHandler("antispam",       antispam_cmd))
    app.add_handler(CommandHandler("antiflood",      antiflood_cmd))
    app.add_handler(CommandHandler("setflood",       setflood_cmd))
    app.add_handler(CommandHandler("setfloodaction", setfloodaction_cmd))
    app.add_handler(CommandHandler("antilink",       antilink_cmd))
    app.add_handler(CommandHandler("antiforward",    antiforward_cmd))
    app.add_handler(CommandHandler("antibot",        antibot_cmd))
    app.add_handler(CommandHandler("antinsfw",       antinsfw_cmd))
    app.add_handler(CommandHandler("antiarabic",     antiarabic_cmd))
    app.add_handler(CommandHandler("antiraid",       antiraid_cmd))
    app.add_handler(CommandHandler("setraid",        setraid_cmd))
    app.add_handler(CommandHandler("cas",            cas_cmd))
    app.add_handler(CommandHandler("restrict",       restrict_cmd))
    app.add_handler(CallbackQueryHandler(protect_toggle_callback, pattern=r"^protect_toggle:"))

    # ── Welcome / Rules ───────────────────────────────────────────────────────
    app.add_handler(CommandHandler("setwelcome",     setwelcome_cmd))
    app.add_handler(CommandHandler("setgoodbye",     setgoodbye_cmd))
    app.add_handler(CommandHandler("welcome",        welcome_toggle_cmd))
    app.add_handler(CommandHandler("goodbye",        goodbye_toggle_cmd))
    app.add_handler(CommandHandler("captcha",        captcha_cmd))
    app.add_handler(CommandHandler("welcdel",        welcdel_cmd))
    app.add_handler(CommandHandler("setrules",       setrules_cmd))
    app.add_handler(CommandHandler("rules",          rules_cmd))
    app.add_handler(CallbackQueryHandler(captcha_callback,  pattern=r"^captcha:"))
    app.add_handler(CallbackQueryHandler(rules_callback,    pattern=r"^rules_accept$"))

    # ── Notes ─────────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("save",           save_cmd))
    app.add_handler(CommandHandler("get",            get_note_cmd))
    app.add_handler(CommandHandler("notes",          notes_cmd))
    app.add_handler(CommandHandler("clear",          clear_cmd))
    app.add_handler(CommandHandler("clearall",       clearall_cmd))
    app.add_handler(CallbackQueryHandler(note_button_callback, pattern=r"^getnote:"))

    # ── Filters / Blacklist ───────────────────────────────────────────────────
    app.add_handler(CommandHandler("filter",         filter_cmd))
    app.add_handler(CommandHandler("filters",        filters_cmd))
    app.add_handler(CommandHandler("stop",           stop_cmd))
    app.add_handler(CommandHandler("stopall",        stopall_cmd))
    app.add_handler(CommandHandler("addbl",          addbl_cmd))
    app.add_handler(CommandHandler(["unblacklist","rmbl"], unblacklist_cmd))
    app.add_handler(CommandHandler("blacklist",      blacklist_cmd))
    app.add_handler(CommandHandler(["blacklistmode","blmode"], blacklistmode_cmd))

    # ── Report ────────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("report",         report_cmd))
    app.add_handler(CallbackQueryHandler(report_callback, pattern=r"^report_"))

    # ── Federation ────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("newfed",         newfed_cmd))
    app.add_handler(CommandHandler("joinfed",        joinfed_cmd))
    app.add_handler(CommandHandler("leavefed",       leavefed_cmd))
    app.add_handler(CommandHandler("fedinfo",        fedinfo_cmd))
    app.add_handler(CommandHandler("fban",           fban_cmd))
    app.add_handler(CommandHandler("unfban",         unfban_cmd))
    app.add_handler(CommandHandler("fedbans",        fedbans_cmd))
    app.add_handler(CommandHandler("fadmin",         fadmin_cmd))
    app.add_handler(CommandHandler("fremove",        fremove_cmd))

    # ── Connection ────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("connect",        connect_cmd))
    app.add_handler(CommandHandler("disconnect",     disconnect_cmd))
    app.add_handler(CommandHandler("connected",      connected_cmd))

    # ── AFK ───────────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("afk",            afk_cmd))

    # ── Global ban / Sudo ─────────────────────────────────────────────────────
    app.add_handler(CommandHandler("gban",           gban_cmd))
    app.add_handler(CommandHandler("ungban",         ungban_cmd))
    app.add_handler(CommandHandler("sudo",           sudo_cmd))
    app.add_handler(CommandHandler("unsudo",         unsudo_cmd))

    # ── Broadcast ─────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("broadcast",      broadcast_cmd))
    app.add_handler(CommandHandler("broadcastall",   broadcastall_cmd))

    # ── Info / Stats ──────────────────────────────────────────────────────────
    app.add_handler(CommandHandler(["botstats","stats"], botstats_cmd))
    app.add_handler(CommandHandler("id",             id_cmd))
    app.add_handler(CommandHandler("info",           info_cmd))
    app.add_handler(CommandHandler("chatinfo",       chatinfo_cmd))
    app.add_handler(CommandHandler("ping",           ping_cmd))
    app.add_handler(CommandHandler("uptime",         uptime_cmd))
    app.add_handler(CommandHandler("chatlist",       chatlist_cmd))
    app.add_handler(CommandHandler("leave",          leave_cmd))
    app.add_handler(CommandHandler("backup",         backup_cmd))

    # ── Settings ──────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("settings",       settings_cmd))
    app.add_handler(CommandHandler("cleanservice",   cleanservice_cmd))
    app.add_handler(CommandHandler("delcommands",    delcommands_cmd))
    app.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^(protect_panel|locks_panel|welcome_panel|economy_panel|other_panel|settings_back)$"))
    app.add_handler(CallbackQueryHandler(toggle_callback,   pattern=r"^toggle:"))

    # ── Economy ───────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("daily",          daily_cmd))
    app.add_handler(CommandHandler("work",           work_cmd))
    app.add_handler(CommandHandler("mine",           mine_cmd))
    app.add_handler(CommandHandler("coins",          coins_cmd))
    app.add_handler(CommandHandler("bank",           bank_cmd))
    app.add_handler(CommandHandler("give",           give_cmd))
    app.add_handler(CommandHandler("rob",            rob_cmd))
    app.add_handler(CommandHandler("flip",           flip_cmd))
    app.add_handler(CommandHandler("slots",          slots_cmd))
    app.add_handler(CommandHandler("shop",           shop_cmd))
    app.add_handler(CommandHandler("buy",            buy_cmd))
    app.add_handler(CommandHandler("inventory",      inventory_cmd))
    app.add_handler(CallbackQueryHandler(buy_callback, pattern=r"^buy:"))

    # ── Leaderboard / Rank ────────────────────────────────────────────────────
    app.add_handler(CommandHandler("leaderboard",    leaderboard_cmd))
    app.add_handler(CommandHandler("rank",           rank_cmd))
    app.add_handler(CommandHandler("top",            top_cmd))
    app.add_handler(CommandHandler("level",          level_cmd))
    app.add_handler(CommandHandler("rep",            rep_cmd))
    app.add_handler(CommandHandler("reprank",        reprank_cmd))
    app.add_handler(CallbackQueryHandler(leaderboard_callback, pattern=r"^lb:"))

    # ── Fun / Games ───────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("8ball",          eightball_cmd))
    app.add_handler(CommandHandler("roll",           roll_cmd))
    app.add_handler(CommandHandler("trivia",         trivia_cmd))
    app.add_handler(CommandHandler("wyr",            wyr_cmd))
    app.add_handler(CommandHandler("pp",             pp_cmd))
    app.add_handler(CommandHandler("slap",           slap_cmd))
    app.add_handler(CommandHandler("hug",            hug_cmd))
    app.add_handler(CommandHandler("kiss",           kiss_cmd))
    app.add_handler(CommandHandler("pat",            pat_cmd))
    app.add_handler(CommandHandler("poke",           poke_cmd))
    app.add_handler(CommandHandler("ship",           ship_cmd))
    app.add_handler(CommandHandler("roast",          roast_cmd))
    app.add_handler(CommandHandler("compliment",     compliment_cmd))
    app.add_handler(CommandHandler("joke",           joke_cmd))
    app.add_handler(CommandHandler("fact",           fact_cmd))
    app.add_handler(CommandHandler("quote",          quote_cmd))
    app.add_handler(CommandHandler("truth",          truth_cmd))
    app.add_handler(CommandHandler("dare",           dare_cmd))
    app.add_handler(CommandHandler("meme",           meme_cmd))
    app.add_handler(CallbackQueryHandler(trivia_callback, pattern=r"^trivia:"))
    app.add_handler(CallbackQueryHandler(wyr_callback,    pattern=r"^wyr:"))

    # ── Utilities ─────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("calc",           calc_cmd))
    app.add_handler(CommandHandler("qr",             qr_cmd))
    app.add_handler(CommandHandler(["tr","translate"], translate_cmd))
    app.add_handler(CommandHandler("hash",           hash_cmd))
    app.add_handler(CommandHandler("b64",            b64_cmd))
    app.add_handler(CommandHandler("weather",        weather_cmd))
    app.add_handler(CommandHandler("time",           time_cmd))
    app.add_handler(CommandHandler("reverse",        reverse_cmd))
    app.add_handler(CommandHandler("ascii",          ascii_cmd))
    app.add_handler(CommandHandler("schedule",       schedule_cmd))

    # ── Message handlers ──────────────────────────────────────────────────────
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_handler))
    app.add_handler(ChatMemberHandler(chat_member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & ~filters.StatusUpdate.ALL,
        main_message_handler
    ))

    # ── Job queue ─────────────────────────────────────────────────────────────
    if app.job_queue:
        app.job_queue.run_repeating(run_scheduler, interval=60, first=10)
        logger.info("✅ Job queue initialized")

    logger.info("🚀 NEXUS Bot is running!")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
