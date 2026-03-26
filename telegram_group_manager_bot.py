#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║      ULTRA ADVANCED TELEGRAM GROUP & CHANNEL MANAGER BOT v7.0              ║
║   Beyond MissRose • All-in-One • Single File • Python • 250+ features      ║
║              🎨 FULLY ANIMATED • 🔒 PERSISTENT • 🚀 HOSTABLE              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, re, json, time, math, random, string, asyncio, sqlite3, logging
import hashlib, textwrap, datetime, calendar, html, urllib.parse, uuid, base64, io
from typing import Optional, Dict, List, Any, Tuple
from collections import defaultdict, deque

# ─── Dependencies ────────────────────────────────────────────────────────────
def _install(pkg):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

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

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log")]
)
logger = logging.getLogger("GroupManagerBot")

# ─── Config ───────────────────────────────────────────────────────────────────
BOT_TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OWNER_IDS   = [int(x) for x in os.environ.get("OWNER_IDS", "").split(",") if x.strip().isdigit()]
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL_ID", "0") or 0)
GBAN_LOG    = int(os.environ.get("GBAN_LOG_CHANNEL", "0") or 0)
DB_PATH     = os.environ.get("DB_PATH", "bot_data.db")
VERSION     = "7.0.0-ULTRA-ANIMATED"
START_TIME  = datetime.datetime.now(pytz.utc)

# ─── In-Memory Caches ────────────────────────────────────────────────────────
flood_cache:      Dict[str, deque]   = defaultdict(lambda: deque(maxlen=50))
spam_cache:       Dict[int, List]    = defaultdict(list)
afk_cache:        Dict[int, dict]    = {}
raid_tracker:     Dict[int, deque]   = defaultdict(lambda: deque(maxlen=50))
msg_hashes:       Dict[int, deque]   = defaultdict(lambda: deque(maxlen=30))
connection_cache: Dict[int, int]     = {}
warn_cd:          Dict[Tuple, float] = {}

# ═══════════════════════════════════════════════════════════════════════════════
#                   🎨 ANIMATION & BEAUTIFUL UI SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

LOADING_FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
PROGRESS_CHARS = ["▱▱▱▱▱▱▱▱▱▱", "▰▱▱▱▱▱▱▱▱▱", "▰▰▱▱▱▱▱▱▱▱",
                  "▰▰▰▱▱▱▱▱▱▱", "▰▰▰▰▱▱▱▱▱▱", "▰▰▰▰▰▱▱▱▱▱",
                  "▰▰▰▰▰▰▱▱▱▱", "▰▰▰▰▰▰▰▱▱▱", "▰▰▰▰▰▰▰▰▱▱",
                  "▰▰▰▰▰▰▰▰▰▱", "▰▰▰▰▰▰▰▰▰▰"]

def box(title: str, body: str, width: int = 38) -> str:
    """Create a beautiful text box."""
    top    = f"╔{'═' * (width - 2)}╗"
    mid    = f"║ {title.center(width - 4)} ║"
    sep    = f"╠{'═' * (width - 2)}╣"
    bottom = f"╚{'═' * (width - 2)}╝"
    body_lines = []
    for line in body.split("\n"):
        body_lines.append(f"║ {line:<{width - 4}} ║")
    return f"{top}\n{mid}\n{sep}\n" + "\n".join(body_lines) + f"\n{bottom}"

def progress_bar(value: int, max_val: int, length: int = 10, filled: str = "█", empty: str = "░") -> str:
    """Create a progress bar."""
    if max_val == 0: return empty * length
    filled_len = int(length * value / max_val)
    return filled * filled_len + empty * (length - filled_len)

def divider(char: str = "─", length: int = 32) -> str:
    return char * length

async def send_loading(update: Update, text: str = None) -> Message:
    """Send an animated loading message."""
    frame = random.choice(LOADING_FRAMES)
    msg_text = text or f"{frame} <b>Processing...</b>"
    try:
        return await update.message.reply_text(msg_text, parse_mode="HTML")
    except Exception:
        return None

async def animate_loading(update: Update, label: str = "Processing") -> Message:
    """Send multi-step animated loading."""
    steps = [
        f"⚡ <b>{label}</b> <code>.</code>",
        f"⚡ <b>{label}</b> <code>..</code>",
        f"⚡ <b>{label}</b> <code>...</code>",
    ]
    try:
        m = await update.message.reply_text(steps[0], parse_mode="HTML")
        for step in steps[1:]:
            await asyncio.sleep(0.3)
            try:
                await m.edit_text(step, parse_mode="HTML")
            except:
                pass
        return m
    except Exception:
        return None

async def finish_anim(m: Message, text: str, reply_markup=None) -> None:
    """Replace loading animation with final result."""
    if not m:
        return
    try:
        await m.edit_text(text, parse_mode="HTML", reply_markup=reply_markup)
    except Exception as e:
        logger.debug(f"finish_anim edit error: {e}")

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
        chat_id INTEGER PRIMARY KEY,
        title TEXT,
        chat_type TEXT,
        lang TEXT DEFAULT 'en',
        welcome_msg TEXT,
        goodbye_msg TEXT,
        welcome_media TEXT,
        rules_text TEXT,
        welcome_buttons TEXT DEFAULT '[]',
        welcome_delete_after INTEGER DEFAULT 0,
        log_channel INTEGER DEFAULT 0,
        warn_limit INTEGER DEFAULT 3,
        warn_action TEXT DEFAULT 'mute',
        mute_duration INTEGER DEFAULT 3600,
        anti_spam INTEGER DEFAULT 1,
        anti_flood INTEGER DEFAULT 1,
        flood_count INTEGER DEFAULT 5,
        flood_time INTEGER DEFAULT 5,
        flood_action TEXT DEFAULT 'mute',
        anti_link INTEGER DEFAULT 0,
        anti_forward INTEGER DEFAULT 0,
        anti_bot INTEGER DEFAULT 0,
        anti_nsfw INTEGER DEFAULT 0,
        anti_raid INTEGER DEFAULT 0,
        raid_threshold INTEGER DEFAULT 10,
        slowmode_delay INTEGER DEFAULT 0,
        delete_commands INTEGER DEFAULT 0,
        delete_service_msgs INTEGER DEFAULT 0,
        lock_stickers INTEGER DEFAULT 0,
        lock_gifs INTEGER DEFAULT 0,
        lock_media INTEGER DEFAULT 0,
        lock_polls INTEGER DEFAULT 0,
        lock_inline INTEGER DEFAULT 0,
        lock_bots INTEGER DEFAULT 0,
        lock_forward INTEGER DEFAULT 0,
        lock_games INTEGER DEFAULT 0,
        lock_voice INTEGER DEFAULT 0,
        lock_video INTEGER DEFAULT 0,
        lock_document INTEGER DEFAULT 0,
        lock_all INTEGER DEFAULT 0,
        lock_preview INTEGER DEFAULT 0,
        lock_url INTEGER DEFAULT 0,
        lock_anon INTEGER DEFAULT 0,
        greetmembers INTEGER DEFAULT 1,
        goodbye_enabled INTEGER DEFAULT 1,
        force_sub INTEGER DEFAULT 0,
        force_sub_channel INTEGER DEFAULT 0,
        blacklist_action TEXT DEFAULT 'delete',
        cas_enabled INTEGER DEFAULT 0,
        report_enabled INTEGER DEFAULT 1,
        economy_enabled INTEGER DEFAULT 1,
        rep_enabled INTEGER DEFAULT 1,
        fun_enabled INTEGER DEFAULT 1,
        ai_enabled INTEGER DEFAULT 1,
        restrict_new_members INTEGER DEFAULT 0,
        new_member_mute_duration INTEGER DEFAULT 0,
        auto_delete_links INTEGER DEFAULT 0,
        clean_service INTEGER DEFAULT 0,
        tag_admins_on_report INTEGER DEFAULT 1,
        fed_id TEXT DEFAULT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        is_gbanned INTEGER DEFAULT 0,
        gban_reason TEXT,
        gbanned_by INTEGER DEFAULT 0,
        gbanned_at TIMESTAMP,
        is_sudo INTEGER DEFAULT 0,
        reputation INTEGER DEFAULT 0,
        bio TEXT,
        is_afk INTEGER DEFAULT 0,
        afk_reason TEXT,
        afk_since TIMESTAMP,
        coins INTEGER DEFAULT 0,
        last_daily TIMESTAMP,
        total_msgs INTEGER DEFAULT 0,
        badges TEXT DEFAULT '[]',
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    # Persistent member tracking — survives bot restarts
    c.execute("""CREATE TABLE IF NOT EXISTS chat_members (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        username TEXT,
        first_name TEXT,
        is_bot INTEGER DEFAULT 0,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (chat_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS warns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        reason TEXT,
        warned_by INTEGER,
        warned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        content TEXT,
        parse_mode TEXT DEFAULT 'HTML',
        media_type TEXT,
        media_id TEXT,
        buttons TEXT DEFAULT '[]',
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, name)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS filters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        keyword TEXT NOT NULL,
        reply TEXT,
        is_regex INTEGER DEFAULT 0,
        media_type TEXT,
        media_id TEXT,
        buttons TEXT DEFAULT '[]',
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, keyword)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        word TEXT NOT NULL,
        is_regex INTEGER DEFAULT 0,
        added_by INTEGER,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, word)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS mutes (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        muted_by INTEGER,
        muted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        until TIMESTAMP,
        reason TEXT,
        PRIMARY KEY(chat_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS bans (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        banned_by INTEGER,
        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reason TEXT,
        PRIMARY KEY(chat_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        media_id TEXT,
        media_type TEXT,
        parse_mode TEXT DEFAULT 'HTML',
        next_run TIMESTAMP NOT NULL,
        repeat TEXT DEFAULT 'none',
        repeat_val INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        reporter_id INTEGER NOT NULL,
        reported_id INTEGER NOT NULL,
        message_id INTEGER,
        reason TEXT,
        status TEXT DEFAULT 'open',
        resolved_by INTEGER,
        reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        admin_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        target_id INTEGER,
        reason TEXT,
        extra TEXT,
        action_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reputation (
        giver_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        given_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(giver_id, receiver_id, chat_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS economy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        chat_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        amount INTEGER NOT NULL,
        detail TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS connections (
        user_id INTEGER PRIMARY KEY,
        chat_id INTEGER NOT NULL,
        connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS federations (
        fed_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        owner_id INTEGER NOT NULL,
        logs_channel INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS federation_admins (
        fed_id TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        PRIMARY KEY(fed_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS federation_chats (
        fed_id TEXT NOT NULL,
        chat_id INTEGER NOT NULL,
        PRIMARY KEY(fed_id, chat_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS federation_bans (
        fed_id TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        reason TEXT,
        banned_by INTEGER,
        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(fed_id, user_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS custom_commands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        command TEXT NOT NULL,
        response TEXT NOT NULL,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, command)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sudo_users (
        user_id INTEGER PRIMARY KEY,
        added_by INTEGER,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    db.commit(); db.close()
    logger.info("✅ Database initialized")

# ─── DB helpers ──────────────────────────────────────────────────────────────
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

def track_member(chat_id: int, user: User):
    """Persistently track a member in a chat for broadcast and analytics."""
    if user.is_bot:
        return
    db = get_db()
    db.execute("""INSERT OR IGNORE INTO chat_members (chat_id, user_id, username, first_name, is_bot)
                  VALUES (?,?,?,?,?)""",
               (chat_id, user.id, user.username or "", user.first_name or "", 1 if user.is_bot else 0))
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

# ═══════════════════════════════════════════════════════════════════════════════
#                          PERMISSION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
async def get_member(context, chat_id: int, user_id: int):
    try:
        return await context.bot.get_chat_member(chat_id, user_id)
    except:
        return None

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
    return Falset

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

# ─── Decorators ──────────────────────────────────────────────────────────────
def admin_only(fn):
    from functools import wraps
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.effective_chat: return
        if update.effective_chat.type == "private": return await fn(update, context)
        if not await is_admin(context, update.effective_chat.id, update.effective_user.id):
            await update.message.reply_text(
                "🚫 <b>Access Denied</b>\n<i>This command is for admins only.</i>",
                parse_mode="HTML"
            )
            return
        return await fn(update, context)
    return wrapper

def owner_only(fn):
    from functools import wraps
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user: return
        if update.effective_user.id not in OWNER_IDS and not is_sudo(update.effective_user.id):
            await update.message.reply_text(
                "👑 <b>Owner Only</b>\n<i>This command is restricted to the bot owner.</i>",
                parse_mode="HTML"
            )
            return
        return await fn(update, context)
    return wrapper

def groups_only(fn):
    from functools import wraps
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat and update.effective_chat.type == "private":
            await update.message.reply_text(
                "👥 <b>Groups Only</b>\n<i>This command only works in group chats.</i>",
                parse_mode="HTML"
            )
            return
        return await fn(update, context)
    return wrapper

# ─── Reply helpers ───────────────────────────────────────────────────────────
async def reply(update: Update, text: str, **kwargs):
    try:
        return await update.message.reply_text(text, parse_mode="HTML", **kwargs)
    except Exception as e:
        logger.debug(f"Reply error: {e}")

async def send_log(context, chat_id: int, text: str):
    cfg = get_chat(chat_id)
    ch = cfg.get("log_channel") or LOG_CHANNEL
    if ch:
        try:
            await context.bot.send_message(ch, text, parse_mode="HTML")
        except:
            pass

def user_link(user) -> str:
    name = html.escape(str(getattr(user, 'first_name', '') or str(getattr(user, 'id', '?'))))
    uid = getattr(user, 'id', 0)
    return f'<a href="tg://user?id={uid}">{name}</a>'

def get_target(update: Update, context) -> Optional[User]:
    msg = update.message
    if msg.reply_to_message:
        return msg.reply_to_message.from_user
    if context.args:
        arg = context.args[0].lstrip("@")
        if arg.isdigit():
            return type("FakeUser", (), {
                "id": int(arg), "first_name": arg, "username": None,
                "last_name": None, "is_bot": False
            })()
    return None

def get_reason(context, start=1) -> str:
    return " ".join(context.args[start:]) if context.args and len(context.args) > start else ""

# ═══════════════════════════════════════════════════════════════════════════════
#                          COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

# ────────────── START / HELP ──────────────────────────────────────────────────
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await reply(update,
            "╔═══════════════════════╗\n"
            "║  🤖 <b>UltraGroupManager</b>  ║\n"
            "╚═══════════════════════╝\n\n"
            "✨ <b>I'm alive and ready!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📖 Use /help to see all my powers!"
        )
        return

    m = await animate_loading(update, "Starting up")
    text = (
        "╔══════════════════════════════╗\n"
        "║  🤖 <b>UltraGroupManager v7.0</b>  ║\n"
        "╚══════════════════════════════╝\n\n"
        "✨ <i>The most powerful group bot you'll ever need!</i>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛡️ <b>Advanced Moderation</b> — ban, mute, warn, restrict\n"
        "🚫 <b>Anti-Spam Engine</b> — flood, raid, link protection\n"
        "📝 <b>Notes & Filters</b> — auto-responses & knowledge base\n"
        "🌐 <b>Federation System</b> — cross-group bans\n"
        "💰 <b>Economy & Games</b> — coins, slots, daily rewards\n"
        "⭐ <b>Reputation System</b> — community scoring\n"
        "🔧 <b>250+ Features</b> — the complete group toolkit\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👇 <b>Add me to your group as admin to get started!</b>"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 Help Menu", callback_data="help_main"),
        InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{context.bot.username}?startgroup=true"),
    ], [
        InlineKeyboardButton("🌟 Features", callback_data="help_mod"),
        InlineKeyboardButton("⚙️ Settings", callback_data="help_settings"),
    ]])
    await finish_anim(m, text, reply_markup=kb)

HELP_SECTIONS = {
    "help_main": (
        "╔═══════════════════════╗\n"
        "║    📋 <b>Help Centre</b>    ║\n"
        "╚═══════════════════════╝\n\n"
        "🤖 <b>UltraGroupManager v7.0</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Select a category below to explore commands:</i>",
        [
            [InlineKeyboardButton("🛡️ Moderation", callback_data="help_mod"),
             InlineKeyboardButton("🚫 Anti-Spam", callback_data="help_antispam")],
            [InlineKeyboardButton("📝 Notes", callback_data="help_notes"),
             InlineKeyboardButton("🔍 Filters", callback_data="help_filters")],
            [InlineKeyboardButton("🔒 Locks", callback_data="help_locks"),
             InlineKeyboardButton("👋 Welcome", callback_data="help_welcome")],
            [InlineKeyboardButton("🌐 Federation", callback_data="help_fed"),
             InlineKeyboardButton("🔗 Connect", callback_data="help_connect")],
            [InlineKeyboardButton("💰 Economy", callback_data="help_economy"),
             InlineKeyboardButton("⭐ Reputation", callback_data="help_rep")],
            [InlineKeyboardButton("🎮 Fun", callback_data="help_fun"),
             InlineKeyboardButton("🔧 Utility", callback_data="help_util")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="help_settings"),
             InlineKeyboardButton("👑 Admin", callback_data="help_admin")],
        ]
    ),
    "help_mod": (
        "╔════════════════════════╗\n"
        "║  🛡️ <b>Moderation Commands</b>  ║\n"
        "╚════════════════════════╝\n\n"
        "━━━ <b>BAN</b> ━━━━━━━━━━━━━━━━━\n"
        "<code>/ban</code> [reply/@user] [reason] — Ban user\n"
        "<code>/tban</code> [reply/@user] 1h [reason] — Temp ban\n"
        "<code>/sban</code> [reply/@user] — Silent ban\n"
        "<code>/unban</code> [reply/@user] — Unban user\n\n"
        "━━━ <b>KICK</b> ━━━━━━━━━━━━━━━━\n"
        "<code>/kick</code> [reply/@user] — Kick user\n"
        "<code>/skick</code> [reply/@user] — Silent kick\n\n"
        "━━━ <b>MUTE</b> ━━━━━━━━━━━━━━━━\n"
        "<code>/mute</code> [reply/@user] [reason] — Mute\n"
        "<code>/tmute</code> [reply/@user] 1h — Temp mute\n"
        "<code>/unmute</code> [reply/@user] — Unmute\n\n"
        "━━━ <b>WARN</b> ━━━━━━━━━━━━━━━━\n"
        "<code>/warn</code> [reply/@user] [reason] — Warn\n"
        "<code>/dwarn</code> — Warn + delete message\n"
        "<code>/swarn</code> — Silent warn\n"
        "<code>/unwarn</code> — Remove 1 warn\n"
        "<code>/resetwarn</code> — Reset all warns\n"
        "<code>/warns</code> — View warns\n\n"
        "━━━ <b>PROMOTE</b> ━━━━━━━━━━━━━\n"
        "<code>/promote</code> [title] — Promote to admin\n"
        "<code>/demote</code> — Remove admin\n"
        "<code>/admintitle</code> [title] — Custom title\n"
        "<code>/adminlist</code> — List all admins\n\n"
        "━━━ <b>CLEANUP</b> ━━━━━━━━━━━━━\n"
        "<code>/purge [N]</code> — Delete messages\n"
        "<code>/del</code> — Delete replied message\n"
        "<code>/pin / /unpin / /unpinall</code> — Pins\n"
        "<code>/zombies</code> — Count ghost accounts\n"
        "<code>/kickzombies</code> — Remove ghost accounts\n"
        "<code>@admins</code> — Tag all admins",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_antispam": (
        "╔═══════════════════════╗\n"
        "║  🚫 <b>Anti-Spam / Protection</b>  ║\n"
        "╚═══════════════════════╝\n\n"
        "━━━ <b>SPAM PROTECTION</b> ━━━━━━━━\n"
        "<code>/antispam on|off</code> — Toggle anti-spam\n"
        "<code>/antiflood on|off</code> — Toggle anti-flood\n"
        "<code>/setflood N [time]</code> — Set flood limit\n"
        "<code>/setfloodaction mute|ban|kick</code> — Action\n\n"
        "━━━ <b>CONTENT FILTERS</b> ━━━━━━━\n"
        "<code>/antilink on|off</code> — Block all links\n"
        "<code>/antiforward on|off</code> — Block forwards\n"
        "<code>/antibot on|off</code> — Block bots joining\n\n"
        "━━━ <b>RAID PROTECTION</b> ━━━━━━━\n"
        "<code>/antiraid on|off</code> — Anti-raid mode\n"
        "<code>/setraid N</code> — Raid threshold (joins/min)\n"
        "<code>/cas on|off</code> — CAS ban protection\n"
        "<code>/restrict on|off</code> — Restrict new members",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_notes": (
        "╔═══════════════════════╗\n"
        "║       📝 <b>Notes System</b>       ║\n"
        "╚═══════════════════════╝\n\n"
        "━━━ <b>MANAGING NOTES</b> ━━━━━━━━\n"
        "<code>/save name text</code> — Save a note\n"
        "<code>/get name</code> — Retrieve a note\n"
        "<code>#name</code> — Quick note retrieval\n"
        "<code>/notes</code> — List all notes\n"
        "<code>/clear name</code> — Delete a note\n"
        "<code>/clearall</code> — Delete all notes\n"
        "<code>/pmnote name</code> — Send note in PM\n\n"
        "━━━ <b>FORMATTING</b> ━━━━━━━━━━━\n"
        "Supports <b>HTML</b>, <i>Markdown</i>, buttons\n"
        "Button syntax: <code>[text](buttonurl://url)</code>",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_filters": (
        "╔═══════════════════════╗\n"
        "║    🔍 <b>Filters & Blacklist</b>    ║\n"
        "╚═══════════════════════╝\n\n"
        "━━━ <b>AUTO-RESPONSE FILTERS</b> ━━━\n"
        "<code>/filter keyword reply</code> — Add filter\n"
        "<code>/filters</code> — List all filters\n"
        "<code>/stop keyword</code> — Remove filter\n"
        "<code>/stopall</code> — Remove all filters\n"
        "<code>/filter regex:pattern reply</code> — Regex\n\n"
        "━━━ <b>BLACKLIST</b> ━━━━━━━━━━━━━\n"
        "<code>/addbl word</code> — Add to blacklist\n"
        "<code>/unblacklist word</code> — Remove from blacklist\n"
        "<code>/blacklist</code> — View blacklist\n"
        "<code>/blacklistmode delete|warn|mute|ban</code>",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_locks": (
        "╔═══════════════════════╗\n"
        "║       🔒 <b>Lock System</b>       ║\n"
        "╚═══════════════════════╝\n\n"
        "━━━ <b>LOCK TYPES</b> ━━━━━━━━━━━\n"
        "<code>stickers</code> • <code>gifs</code> • <code>media</code> • <code>polls</code>\n"
        "<code>voice</code> • <code>video</code> • <code>document</code>\n"
        "<code>forward</code> • <code>games</code> • <code>inline</code>\n"
        "<code>url</code> • <code>anon</code> • <code>all</code>\n\n"
        "━━━ <b>COMMANDS</b> ━━━━━━━━━━━━\n"
        "<code>/lock type</code> — Lock a content type\n"
        "<code>/unlock type</code> — Unlock a content type\n"
        "<code>/locks</code> — View all lock statuses",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_welcome": (
        "╔═══════════════════════╗\n"
        "║    👋 <b>Welcome & Rules</b>     ║\n"
        "╚═══════════════════════╝\n\n"
        "━━━ <b>WELCOME MESSAGES</b> ━━━━━━\n"
        "<code>/setwelcome text</code> — Set welcome message\n"
        "<code>/welcome on|off</code> — Toggle welcome\n"
        "<code>/cleanwelcome on|off</code> — Delete old welcomes\n"
        "<code>/welcdel N</code> — Auto-delete after N secs\n\n"
        "━━━ <b>GOODBYE MESSAGES</b> ━━━━━\n"
        "<code>/setgoodbye text</code> — Set goodbye message\n"
        "<code>/goodbye on|off</code> — Toggle goodbye\n\n"
        "━━━ <b>RULES</b> ━━━━━━━━━━━━━━━\n"
        "<code>/setrules text</code> — Set rules\n"
        "<code>/rules</code> — Show rules\n\n"
        "━━━ <b>PLACEHOLDERS</b> ━━━━━━━━━\n"
        "<code>{first}</code> <code>{last}</code> <code>{username}</code>\n"
        "<code>{mention}</code> <code>{count}</code> <code>{chatname}</code>",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_fed": (
        "╔═══════════════════════╗\n"
        "║    🌐 <b>Federation System</b>    ║\n"
        "╚═══════════════════════╝\n\n"
        "<i>Ban users across multiple groups at once!</i>\n\n"
        "━━━ <b>FEDERATION MANAGEMENT</b> ━━\n"
        "<code>/newfed name</code> — Create a federation\n"
        "<code>/delfed fed_id</code> — Delete federation\n"
        "<code>/joinfed fed_id</code> — Join a federation\n"
        "<code>/leavefed</code> — Leave current federation\n"
        "<code>/fedinfo [fed_id]</code> — Federation info\n\n"
        "━━━ <b>FEDERATION BANS</b> ━━━━━━━\n"
        "<code>/fban user [reason]</code> — Federation ban\n"
        "<code>/unfban user</code> — Remove federation ban\n"
        "<code>/fedbans [fed_id]</code> — List fed bans\n"
        "<code>/fadmin user</code> — Add fed admin\n"
        "<code>/fremove user</code> — Remove fed admin",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_connect": (
        "╔═══════════════════════╗\n"
        "║    🔗 <b>Connection System</b>    ║\n"
        "╚═══════════════════════╝\n\n"
        "<i>Manage groups directly from your private messages!</i>\n\n"
        "━━━ <b>COMMANDS</b> ━━━━━━━━━━━━\n"
        "<code>/connect chat_id</code> — Connect to group\n"
        "<code>/disconnect</code> — Disconnect\n"
        "<code>/connected</code> — Check connection\n\n"
        "━━━ <b>HOW IT WORKS</b> ━━━━━━━━\n"
        "1️⃣ Get your group ID with /id in the group\n"
        "2️⃣ Send /connect [group_id] in my PM\n"
        "3️⃣ Use admin commands from your DM!",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_economy": (
        "╔═══════════════════════╗\n"
        "║     💰 <b>Economy System</b>     ║\n"
        "╚═══════════════════════╝\n\n"
        "━━━ <b>EARNING COINS</b> ━━━━━━━━\n"
        "<code>/daily</code> — Claim daily coins (~500)\n"
        "<code>/mine</code> — Mine coins (10-150)\n\n"
        "━━━ <b>SPENDING & GAMES</b> ━━━━━\n"
        "<code>/flip amount</code> — Coin flip gamble\n"
        "<code>/slots amount</code> — 🎰 Slot machine\n"
        "<code>/rob @user</code> — Steal coins (risky!)\n\n"
        "━━━ <b>SOCIAL</b> ━━━━━━━━━━━━━\n"
        "<code>/give @user amount</code> — Send coins\n"
        "<code>/coins [@user]</code> — Check balance\n"
        "<code>/leaderboard</code> — Top 10 richest\n"
        "<code>/shop</code> — View the shop",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_rep": (
        "╔═══════════════════════╗\n"
        "║   ⭐ <b>Reputation System</b>   ║\n"
        "╚═══════════════════════╝\n\n"
        "<i>Reward helpful members with reputation points!</i>\n\n"
        "━━━ <b>COMMANDS</b> ━━━━━━━━━━━━\n"
        "<code>+rep</code> or <code>/rep @user</code> — Give +1 rep\n"
        "<code>/checkrep [@user]</code> — Check reputation\n"
        "<code>/reprank</code> — Top reputation leaderboard\n\n"
        "━━━ <b>RULES</b> ━━━━━━━━━━━━━━\n"
        "⏰ 1 rep given per user per day\n"
        "🚫 Can't give rep to yourself",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_fun": (
        "╔═══════════════════════╗\n"
        "║      🎮 <b>Fun Commands</b>      ║\n"
        "╚═══════════════════════╝\n\n"
        "━━━ <b>GAMES</b> ━━━━━━━━━━━━━━\n"
        "<code>/8ball question</code> — 🎱 Magic 8-ball\n"
        "<code>/roll [sides]</code> — 🎲 Roll a dice\n"
        "<code>/truth</code> — 💭 Truth question\n"
        "<code>/dare</code> — 😈 Dare challenge\n\n"
        "━━━ <b>SOCIAL</b> ━━━━━━━━━━━━━\n"
        "<code>/slap @user</code> — 👋 Slap someone\n"
        "<code>/hug @user</code> — 🤗 Hug someone\n"
        "<code>/ship @user1 @user2</code> — 💕 Ship them\n"
        "<code>/roast @user</code> — 🔥 Roast someone\n"
        "<code>/compliment @user</code> — 💐 Compliment\n\n"
        "━━━ <b>ENTERTAINMENT</b> ━━━━━━━\n"
        "<code>/joke</code> — 😂 Random joke\n"
        "<code>/meme</code> — 🎭 Meme text",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_util": (
        "╔═══════════════════════╗\n"
        "║    🔧 <b>Utility Commands</b>    ║\n"
        "╚═══════════════════════╝\n\n"
        "━━━ <b>INFO & IDs</b> ━━━━━━━━━━\n"
        "<code>/id [@user]</code> — Get user/chat ID\n"
        "<code>/info [@user]</code> — Detailed user info\n"
        "<code>/chatinfo</code> — Chat information\n"
        "<code>/ping</code> — 🏓 Bot latency\n"
        "<code>/uptime</code> — ⏱️ Bot uptime\n\n"
        "━━━ <b>TEXT TOOLS</b> ━━━━━━━━━\n"
        "<code>/calc expr</code> — 🧮 Calculator\n"
        "<code>/hash text</code> — 🔐 MD5/SHA hashes\n"
        "<code>/b64 encode|decode text</code> — Base64\n"
        "<code>/reverse text</code> — 🔄 Reverse text\n"
        "<code>/ascii text</code> — ASCII codes\n\n"
        "━━━ <b>GENERATORS</b> ━━━━━━━━━\n"
        "<code>/qr text</code> — 📱 QR code\n"
        "<code>/tr lang text</code> — 🌐 Translate\n"
        "<code>/weather city</code> — 🌤️ Weather\n"
        "<code>/time [timezone]</code> — 🕐 Current time",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_settings": (
        "╔═══════════════════════╗\n"
        "║     ⚙️ <b>Settings</b>      ║\n"
        "╚═══════════════════════╝\n\n"
        "━━━ <b>MODERATION SETTINGS</b> ━━━\n"
        "<code>/setwarnlimit N</code> — Warn limit\n"
        "<code>/setwarnaction mute|ban|kick</code>\n"
        "<code>/setmuteaction N</code> — Mute duration\n"
        "<code>/setblacklistaction delete|warn|mute|ban</code>\n\n"
        "━━━ <b>CHAT SETTINGS</b> ━━━━━━━\n"
        "<code>/delcommands on|off</code> — Delete commands\n"
        "<code>/cleanservice on|off</code> — Clean service msgs\n"
        "<code>/welcdel N</code> — Welcome delete timer\n"
        "<code>/setlang lang</code> — Set chat language\n\n"
        "━━━ <b>VIEW SETTINGS</b> ━━━━━━━\n"
        "<code>/settings</code> — View all current settings",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
    "help_admin": (
        "╔═══════════════════════╗\n"
        "║   👑 <b>Admin / Owner Commands</b>  ║\n"
        "╚═══════════════════════╝\n\n"
        "━━━ <b>GLOBAL MODERATION</b> ━━━━━\n"
        "<code>/gban user [reason]</code> — Global ban\n"
        "<code>/ungban user</code> — Remove global ban\n"
        "<code>/sudo user</code> — Add sudo user\n"
        "<code>/unsudo user</code> — Remove sudo user\n\n"
        "━━━ <b>BROADCAST</b> ━━━━━━━━━━━\n"
        "<code>/broadcast msg</code> — Broadcast to all chats\n"
        "<code>/broadcastall msg</code> — Broadcast to all members\n\n"
        "━━━ <b>BOT MANAGEMENT</b> ━━━━━━\n"
        "<code>/stats</code> — 📊 Bot statistics\n"
        "<code>/chatlist</code> — 💬 List all chats\n"
        "<code>/backup</code> — 💾 Export chat backup\n"
        "<code>/leave</code> — Leave a chat",
        [[InlineKeyboardButton("« Back to Menu", callback_data="help_main")]]
    ),
}

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, buttons = HELP_SECTIONS["help_main"]
    if update.effective_chat.type != "private":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📖 Open Help in PM", url=f"https://t.me/{context.bot.username}?start=help")]])
        await reply(update, "📬 <b>Help sent to your DM!</b>", reply_markup=kb)
        return
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    key = q.data
    if key in HELP_SECTIONS:
        text, buttons = HELP_SECTIONS[key]
        await q.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))

# ────────────── MODERATION ───────────────────────────────────────────────────
async def _do_ban(context, chat_id: int, user_id: int, until: datetime.datetime = None):
    await context.bot.ban_chat_member(chat_id, user_id, until_date=until)

@admin_only
@groups_only
async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>\n<i>You need restrict rights to ban users.</i>")
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ <b>Who to ban?</b>\n<i>Reply to a user or provide their @username.</i>")
    reason = " ".join(context.args) if context.args and update.message.reply_to_message else get_reason(context)
    if not update.message.reply_to_message and context.args:
        reason = " ".join(context.args[1:])
    chat = update.effective_chat
    m = await animate_loading(update, "Banning user")
    try:
        await _do_ban(context, chat.id, target.id)
        db = get_db()
        db.execute("INSERT OR REPLACE INTO bans (chat_id, user_id, banned_by, reason) VALUES (?,?,?,?)",
                   (chat.id, target.id, update.effective_user.id, reason))
        db.commit(); db.close()
        log_action(chat.id, update.effective_user.id, "ban", target.id, reason)
        text = (
            "╔══════════════════════╗\n"
            "║     🔨 <b>USER BANNED</b>     ║\n"
            "╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"📝 <b>Reason:</b> {html.escape(reason or 'No reason provided')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚫 <i>User has been removed from this chat.</i>"
        )
        await finish_anim(m, text)
        await send_log(context, chat.id,
            f"🔨 <b>BAN</b> | {html.escape(chat.title)}\n"
            f"Admin: {user_link(update.effective_user)}\n"
            f"User: {user_link(target)}\n"
            f"Reason: {html.escape(reason or 'None')}")
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def tban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>\n<i>You need restrict rights.</i>")
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/tban @user 1h [reason]</code>\n<i>Durations: 1m, 1h, 1d, 1w</i>")
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ <b>Who to ban?</b> Provide a user.")
    time_arg = context.args[0] if update.message.reply_to_message else (context.args[1] if len(context.args) > 1 else "1h")
    duration = parse_duration(time_arg)
    if not duration:
        return await reply(update, "❌ <b>Invalid duration.</b>\n<i>Use: 1m, 1h, 1d, 1w</i>")
    until = datetime.datetime.now(pytz.utc) + duration
    m = await animate_loading(update, "Processing temp ban")
    try:
        await _do_ban(context, update.effective_chat.id, target.id, until)
        log_action(update.effective_chat.id, update.effective_user.id, "tban", target.id, time_arg)
        text = (
            "╔══════════════════════╗\n"
            "║   ⏱️ <b>TEMP BANNED</b>    ║\n"
            "╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"⏰ <b>Duration:</b> {html.escape(time_arg)}\n"
            f"📅 <b>Expires:</b> {until.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔓 <i>Will be automatically unbanned.</i>"
        )
        await finish_anim(m, text)
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def sban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ Reply to a user.")
    try:
        await update.message.delete()
        if update.message.reply_to_message:
            await update.message.reply_to_message.delete()
        await _do_ban(context, update.effective_chat.id, target.id)
        log_action(update.effective_chat.id, update.effective_user.id, "sban", target.id, "silent")
    except:
        pass

@admin_only
@groups_only
async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ Reply to a user or provide username.")
    m = await animate_loading(update, "Unbanning user")
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id, only_if_banned=True)
        db = get_db()
        db.execute("DELETE FROM bans WHERE chat_id=? AND user_id=?", (update.effective_chat.id, target.id))
        db.commit(); db.close()
        log_action(update.effective_chat.id, update.effective_user.id, "unban", target.id)
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║     ✅ <b>USER UNBANNED</b>    ║\n"
            "╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 <i>User can now rejoin the group.</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ Reply to a user.")
    m = await animate_loading(update, "Kicking user")
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        log_action(update.effective_chat.id, update.effective_user.id, "kick", target.id)
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║     👢 <b>USER KICKED</b>      ║\n"
            "╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚪 <i>User was kicked. They can rejoin.</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def skick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return
    target = get_target(update, context)
    if not target:
        return
    try:
        await update.message.delete()
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
    except:
        pass

MUTE_PERMS = ChatPermissions(can_send_messages=False,
                              can_send_polls=False, can_send_other_messages=False)
UNMUTE_PERMS = ChatPermissions(can_send_messages=True,
                                can_send_polls=True, can_send_other_messages=True,
                                can_add_web_page_previews=True)

@admin_only
@groups_only
async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ Reply to a user.")
    reason = " ".join(context.args) if context.args and not update.message.reply_to_message else get_reason(context)
    m = await animate_loading(update, "Muting user")
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS)
        log_action(update.effective_chat.id, update.effective_user.id, "mute", target.id, reason)
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║     🔇 <b>USER MUTED</b>       ║\n"
            "╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"📝 <b>Reason:</b> {html.escape(reason or 'No reason provided')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔕 <i>User's messages are now silenced.</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def tmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ Reply to a user or provide username.")
    time_str = (context.args[1] if update.message.reply_to_message and len(context.args) > 0 else
                (context.args[1] if len(context.args) > 1 else "1h"))
    duration = parse_duration(time_str)
    if not duration:
        return await reply(update, "❌ <b>Invalid duration.</b>\n<i>Use: 1m, 1h, 1d</i>")
    until = datetime.datetime.now(pytz.utc) + duration
    m = await animate_loading(update, "Processing temp mute")
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS, until_date=until)
        log_action(update.effective_chat.id, update.effective_user.id, "tmute", target.id, time_str)
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║   ⏱️ <b>TEMP MUTED</b>     ║\n"
            "╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"⏰ <b>Duration:</b> {html.escape(time_str)}\n"
            f"📅 <b>Expires:</b> {until.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔓 <i>Will be automatically unmuted.</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ Reply to a user.")
    m = await animate_loading(update, "Unmuting user")
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, UNMUTE_PERMS)
        log_action(update.effective_chat.id, update.effective_user.id, "unmute", target.id)
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║    🔊 <b>USER UNMUTED</b>     ║\n"
            "╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 <i>User can now send messages again.</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

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
    if not target:
        return await reply(update, "❓ Reply to a user.")
    if await is_admin(context, update.effective_chat.id, target.id):
        return await reply(update, "🛡️ <b>Cannot warn admins!</b>")
    reason = " ".join(context.args) if context.args else ""
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
        db.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (update.effective_chat.id, target.id))
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
        text = (
            "╔══════════════════════╗\n"
            "║     ⚠️ <b>USER WARNED</b>      ║\n"
            "╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👮 <b>Admin:</b> {user_link(update.effective_user)}\n"
            f"📝 <b>Reason:</b> {html.escape(reason or 'No reason provided')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔢 <b>Warns:</b> [{count}/{warn_limit}]\n"
            f"[{bar}]{extra_action}"
        )
        await reply(update, text)

@admin_only
@groups_only
async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ Reply to a user.")
    db = get_db()
    row = db.execute("SELECT id FROM warns WHERE chat_id=? AND user_id=? ORDER BY warned_at DESC LIMIT 1",
                     (update.effective_chat.id, target.id)).fetchone()
    if row:
        db.execute("DELETE FROM warns WHERE id=?", (row["id"],))
        db.commit()
    db.close()
    await reply(update,
        "╔══════════════════════╗\n"
        "║  ✅ <b>WARN REMOVED</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"✨ <i>1 warning has been lifted.</i>"
    )

@admin_only
@groups_only
async def resetwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ Reply to a user.")
    db = get_db()
    db.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (update.effective_chat.id, target.id))
    db.commit(); db.close()
    log_action(update.effective_chat.id, update.effective_user.id, "resetwarn", target.id)
    await reply(update,
        "╔══════════════════════╗\n"
        "║  🗑️ <b>WARNS RESET</b>    ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"✨ <i>All warnings have been cleared!</i>"
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
            "╔══════════════════════╗\n"
            "║    ✅ <b>NO WARNINGS</b>    ║\n"
            "╚══════════════════════╝\n\n"
            f"👤 {user_link(target)} is clean!\n"
            f"🌟 <i>No warnings on record.</i>"
        )
    bar = progress_bar(len(rows), warn_limit)
    lines = [
        "╔══════════════════════╗\n"
        f"║  ⚠️ <b>WARN HISTORY</b>   ║\n"
        "╚══════════════════════╝\n",
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"🔢 <b>Warns:</b> [{len(rows)}/{warn_limit}] [{bar}]\n"
        "━━━━━━━━━━━━━━━━━━━━━"
    ]
    for i, w in enumerate(rows[:10], 1):
        lines.append(f"\n{i}. 📝 {html.escape(w['reason'] or 'No reason')}\n   <i>🕐 {w['warned_at']}</i>")
    await reply(update, "\n".join(lines))

# ────────────── PROMOTE / DEMOTE ─────────────────────────────────────────────
@admin_only
@groups_only
async def promote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>\n<i>You need promote rights.</i>")
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ Reply to a user.")
    title = " ".join(context.args[1:]) if not update.message.reply_to_message and len(context.args) > 1 else (
        " ".join(context.args) if context.args else "")
    m = await animate_loading(update, "Promoting user")
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, target.id,
            can_manage_chat=True, can_delete_messages=True, can_restrict_members=True,
            can_invite_users=True, can_pin_messages=True, can_manage_video_chats=True,
            is_anonymous=False
        )
        if title:
            await context.bot.set_chat_administrator_custom_title(update.effective_chat.id, target.id, title[:16])
        log_action(update.effective_chat.id, update.effective_user.id, "promote", target.id, title)
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║   ⬆️ <b>USER PROMOTED</b>    ║\n"
            "╚══════════════════════╝\n\n"
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
    if not target:
        return await reply(update, "❓ Reply to a user.")
    m = await animate_loading(update, "Demoting user")
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, target.id,
            can_manage_chat=False, can_delete_messages=False, can_restrict_members=False,
            can_invite_users=False, can_pin_messages=False
        )
        log_action(update.effective_chat.id, update.effective_user.id, "demote", target.id)
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║   ⬇️ <b>USER DEMOTED</b>    ║\n"
            "╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📉 <i>Admin rights have been removed.</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def admintitle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = get_target(update, context)
    if not target:
        return await reply(update, "❓ Reply to a user.")
    title = " ".join(context.args) if update.message.reply_to_message else " ".join(context.args[1:])
    if not title:
        return await reply(update, "❓ <b>Provide a title.</b>\n<code>/admintitle [reply] Title Here</code>")
    try:
        await context.bot.set_chat_administrator_custom_title(update.effective_chat.id, target.id, title[:16])
        await reply(update,
            "╔══════════════════════╗\n"
            "║  🏷️ <b>TITLE SET</b>   ║\n"
            "╚══════════════════════╝\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"🏅 <b>Title:</b> <b>{html.escape(title)}</b>\n"
            f"✨ <i>Custom admin title applied!</i>"
        )
    except BadRequest as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def adminlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Fetching admin list")
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        lines = [
            "╔══════════════════════╗\n"
            "║    👮 <b>ADMIN LIST</b>     ║\n"
            "╚══════════════════════╝\n"
        ]
        owners = [a for a in admins if a.status == "creator"]
        mods = [a for a in admins if a.status == "administrator"]
        if owners:
            lines.append("━━━ 👑 <b>Owner</b> ━━━━━━━━━━━")
            for a in owners:
                name = html.escape(a.user.first_name or str(a.user.id))
                lines.append(f"👑 <a href='tg://user?id={a.user.id}'>{name}</a>")
        if mods:
            lines.append("\n━━━ 🔧 <b>Admins</b> ━━━━━━━━━━")
            for a in mods:
                name = html.escape(a.user.first_name or str(a.user.id))
                t = f" — <i>{html.escape(a.custom_title)}</i>" if isinstance(a, ChatMemberAdministrator) and a.custom_title else ""
                lines.append(f"🔧 <a href='tg://user?id={a.user.id}'>{name}</a>{t}")
        lines.append(f"\n📊 <b>Total: {len(admins)} admins</b>")
        await finish_anim(m, "\n".join(lines))
    except Exception as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

# ────────────── TAG ADMINS ────────────────────────────────────────────────────
async def tag_admins_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    if "@admins" not in update.message.text.lower() and "@admin" not in update.message.text.lower(): return
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        mentions = " ".join(
            f'<a href="tg://user?id={a.user.id}">​</a>'
            for a in admins if not a.user.is_bot
        )
        await reply(update,
            "📢 <b>Admins have been notified!</b>\n"
            f"{mentions}"
        )
    except:
        pass

# ────────────── ZOMBIES ───────────────────────────────────────────────────────
@admin_only
@groups_only
async def zombies_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Scanning for zombie accounts")
    try:
        count = 0
        async for member in context.bot.get_chat_members(update.effective_chat.id):
            if member.user.is_deleted:
                count += 1
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║   🧟 <b>ZOMBIE SCAN</b>    ║\n"
            "╚══════════════════════╝\n\n"
            f"🔍 <b>Scan complete!</b>\n"
            f"🧟 <b>Zombies found:</b> {count}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"{'💀 <i>Use /kickzombies to remove them!</i>' if count else '✨ <i>This group is zombie-free!</i>'}"
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
                except:
                    pass
        log_action(update.effective_chat.id, update.effective_user.id, "kickzombies", extra=str(kicked))
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║  ✅ <b>ZOMBIES PURGED</b>   ║\n"
            "╚══════════════════════╝\n\n"
            f"💥 <b>Successfully kicked {kicked} zombie accounts!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌟 <i>Group is now zombie-free!</i>"
        )
    except Exception as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

# ────────────── PIN ───────────────────────────────────────────────────────────
@admin_only
@groups_only
async def pin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_pin(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    if not update.message.reply_to_message:
        return await reply(update, "❓ <b>Reply to a message to pin it!</b>")
    silent = "silent" in (context.args or []) or "notify" not in (context.args or [])
    try:
        await context.bot.pin_chat_message(update.effective_chat.id,
                                           update.message.reply_to_message.message_id,
                                           disable_notification=silent)
        await reply(update,
            "╔══════════════════════╗\n"
            "║    📌 <b>PINNED</b>       ║\n"
            "╚══════════════════════╝\n\n"
            f"✅ <i>Message has been pinned!</i>"
        )
    except BadRequest as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def unpin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_pin(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    try:
        if update.message.reply_to_message:
            await context.bot.unpin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        else:
            await context.bot.unpin_chat_message(update.effective_chat.id)
        await reply(update, "📌 <b>Unpinned!</b> Message has been unpinned.")
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
        await finish_anim(m, "✅ <b>All messages unpinned!</b>\n<i>The pinned messages list is now empty.</i>")
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

# ────────────── PURGE ─────────────────────────────────────────────────────────
@admin_only
@groups_only
async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    msg = update.message
    if not msg.reply_to_message:
        return await reply(update, "❓ <b>Reply to the first message you want to purge from!</b>")
    from_id = msg.reply_to_message.message_id
    to_id = msg.message_id
    ids = list(range(from_id, to_id + 1))
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
                except:
                    pass
        try:
            await m.edit_text(
                f"🗑️ <b>Purging...</b>\n[{progress_bar(min(i + 100, len(ids)), len(ids))}]\n"
                f"<i>{min(i+100, len(ids))}/{len(ids)} deleted</i>",
                parse_mode="HTML"
            )
        except:
            pass
    try:
        await m.edit_text(
            f"╔══════════════════════╗\n"
            f"║   🗑️ <b>PURGE COMPLETE</b>  ║\n"
            f"╚══════════════════════╝\n\n"
            f"✅ <b>Deleted {count} messages!</b>",
            parse_mode="HTML"
        )
        await asyncio.sleep(3)
        await m.delete()
    except:
        pass

@admin_only
async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await reply(update, "❓ <b>Reply to a message to delete it!</b>")
    try:
        await update.message.reply_to_message.delete()
        await update.message.delete()
    except:
        pass

# ────────────── LOCKS ─────────────────────────────────────────────────────────
LOCK_TYPES = {
    "stickers": "lock_stickers", "gifs": "lock_gifs", "media": "lock_media",
    "polls": "lock_polls", "inline": "lock_inline", "bots": "lock_bots",
    "forward": "lock_forward", "games": "lock_games", "voice": "lock_voice",
    "video": "lock_video", "document": "lock_document", "all": "lock_all",
    "preview": "lock_preview", "url": "lock_url", "anon": "lock_anon"
}

@admin_only
@groups_only
async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, f"❓ <b>Usage:</b> <code>/lock {' | '.join(LOCK_TYPES.keys())}</code>")
    t = context.args[0].lower()
    if t not in LOCK_TYPES:
        return await reply(update, f"❌ <b>Unknown type.</b> Available: <code>{', '.join(LOCK_TYPES.keys())}</code>")
    set_setting(update.effective_chat.id, LOCK_TYPES[t], 1)
    await reply(update,
        "╔══════════════════════╗\n"
        "║      🔒 <b>LOCKED</b>       ║\n"
        "╚══════════════════════╝\n\n"
        f"🔐 <b>Type:</b> <code>{t}</code>\n"
        f"🚫 <i>This content type is now blocked.</i>"
    )

@admin_only
@groups_only
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, f"❓ <b>Usage:</b> <code>/unlock {' | '.join(LOCK_TYPES.keys())}</code>")
    t = context.args[0].lower()
    if t not in LOCK_TYPES:
        return await reply(update, f"❌ <b>Unknown type.</b>")
    set_setting(update.effective_chat.id, LOCK_TYPES[t], 0)
    await reply(update,
        "╔══════════════════════╗\n"
        "║      🔓 <b>UNLOCKED</b>      ║\n"
        "╚══════════════════════╝\n\n"
        f"🟢 <b>Type:</b> <code>{t}</code>\n"
        f"✅ <i>This content type is now allowed.</i>"
    )

async def locks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_chat(update.effective_chat.id)
    locked = [name for name, key in LOCK_TYPES.items() if cfg.get(key, 0)]
    unlocked = [name for name, key in LOCK_TYPES.items() if not cfg.get(key, 0)]
    text = (
        "╔══════════════════════╗\n"
        "║   🔒 <b>LOCK STATUS</b>    ║\n"
        "╚══════════════════════╝\n\n"
        "🔴 <b>Locked:</b>\n" +
        (" ".join(f"<code>{n}</code>" for n in locked) if locked else "<i>None</i>") +
        "\n\n🟢 <b>Unlocked:</b>\n" +
        (" ".join(f"<code>{n}</code>" for n in unlocked) if unlocked else "<i>None</i>")
    )
    await reply(update, text)

# ────────────── WELCOME / GOODBYE / RULES ────────────────────────────────────
def format_welcome(text: str, user: User, chat: Chat) -> str:
    name = html.escape(user.first_name or "")
    last = html.escape(user.last_name or "")
    username = f"@{user.username}" if user.username else name
    mention = mention_html(user.id, name)
    return (text
            .replace("{first}", name).replace("{last}", last)
            .replace("{username}", username).replace("{mention}", mention)
            .replace("{chatname}", html.escape(chat.title or ""))
            .replace("{id}", str(user.id)).replace("{count}", "?"))

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
    for user in members:
        ensure_user(user)
        track_member(chat.id, user)
        if user.is_bot:
            if cfg.get("anti_bot"):
                try:
                    await context.bot.ban_chat_member(chat.id, user.id)
                    await context.bot.unban_chat_member(chat.id, user.id)
                    return
                except: pass
            continue
        reason = is_gbanned(user.id)
        if reason:
            try:
                await context.bot.ban_chat_member(chat.id, user.id)
                await context.bot.send_message(chat.id,
                    f"🌍 <b>Globally banned user removed!</b>\n"
                    f"👤 User: <a href='tg://user?id={user.id}'>{html.escape(user.first_name)}</a>\n"
                    f"📝 Reason: {html.escape(reason)}",
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
                        "🚨 <b>ANTI-RAID ACTIVATED!</b>\n"
                        "⚡ <i>Suspicious join spike detected! New member removed.</i>",
                        parse_mode="HTML")
                except: pass
                continue
        if cfg.get("restrict_new_members"):
            dur = cfg.get("new_member_mute_duration", 300)
            until = datetime.datetime.now(pytz.utc) + datetime.timedelta(seconds=dur)
            try:
                await context.bot.restrict_chat_member(chat.id, user.id, MUTE_PERMS, until_date=until)
            except: pass
        welcome = cfg.get("welcome_msg") or (
            "╔══════════════════════════╗\n"
            "║   👋 <b>WELCOME!</b>        ║\n"
            "╚══════════════════════════╝\n\n"
            "🌟 Hey {mention}!\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Welcome to <b>{chatname}</b>! 🎉\n"
            "We're happy to have you here!"
        )
        text = format_welcome(welcome, user, chat)
        buttons_raw = cfg.get("welcome_buttons", "[]")
        kb = parse_buttons(buttons_raw)
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
        except Exception as e:
            logger.debug(f"Welcome error: {e}")

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
        "║   👋 <b>GOODBYE!</b>        ║\n"
        "╚══════════════════════════╝\n\n"
        "😢 <b>{first}</b> has left the group.\n"
        "We'll miss you! Come back soon! 💙"
    )
    text = format_welcome(goodbye, user, chat)
    try:
        await context.bot.send_message(chat.id, text, parse_mode="HTML")
    except: pass

def parse_buttons(raw: str) -> List[List[InlineKeyboardButton]]:
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            rows = []
            for row in data:
                if isinstance(row, list):
                    rows.append([InlineKeyboardButton(b.get("text", ""), url=b.get("url", "#")) for b in row])
                elif isinstance(row, dict):
                    rows.append([InlineKeyboardButton(row.get("text", ""), url=row.get("url", "#"))])
            return rows
    except: pass
    return []

@admin_only
@groups_only
async def setwelcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and not (update.message.reply_to_message and update.message.reply_to_message.text):
        return await reply(update,
            "╔════════════════════════════╗\n"
            "║  👋 <b>SET WELCOME</b>      ║\n"
            "╚════════════════════════════╝\n\n"
            "<b>Usage:</b> <code>/setwelcome Your welcome text</code>\n\n"
            "<b>Placeholders:</b>\n"
            "<code>{mention}</code> — User mention\n"
            "<code>{first}</code> — First name\n"
            "<code>{last}</code> — Last name\n"
            "<code>{username}</code> — Username\n"
            "<code>{chatname}</code> — Group name\n"
            "<code>{id}</code> — User ID"
        )
    text = " ".join(context.args) if context.args else update.message.reply_to_message.text
    set_setting(update.effective_chat.id, "welcome_msg", text)
    await reply(update,
        "╔══════════════════════╗\n"
        "║  ✅ <b>WELCOME SET!</b>  ║\n"
        "╚══════════════════════╝\n\n"
        "🎉 <i>New members will now see your custom welcome message!</i>"
    )

@admin_only
@groups_only
async def setgoodbye_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    if not text:
        return await reply(update, "❓ <b>Usage:</b> <code>/setgoodbye Your goodbye text</code>")
    set_setting(update.effective_chat.id, "goodbye_msg", text)
    await reply(update,
        "╔══════════════════════╗\n"
        "║  ✅ <b>GOODBYE SET!</b>  ║\n"
        "╚══════════════════════╝\n\n"
        "👋 <i>Goodbye message has been updated!</i>"
    )

async def welcome_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = context.args[0].lower() if context.args else "on"
    set_setting(update.effective_chat.id, "greetmembers", 1 if val == "on" else 0)
    icon = "✅" if val == "on" else "❌"
    await reply(update, f"{icon} <b>Welcome messages {'enabled' if val == 'on' else 'disabled'}!</b>")

async def goodbye_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = context.args[0].lower() if context.args else "on"
    set_setting(update.effective_chat.id, "goodbye_enabled", 1 if val == "on" else 0)
    icon = "✅" if val == "on" else "❌"
    await reply(update, f"{icon} <b>Goodbye messages {'enabled' if val == 'on' else 'disabled'}!</b>")

@admin_only
@groups_only
async def setrules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    if not text and update.message.reply_to_message:
        text = update.message.reply_to_message.text or ""
    if not text:
        return await reply(update, "❓ <b>Usage:</b> <code>/setrules Your rules text</code>")
    set_setting(update.effective_chat.id, "rules_text", text)
    await reply(update,
        "╔══════════════════════╗\n"
        "║  ✅ <b>RULES UPDATED!</b>  ║\n"
        "╚══════════════════════╝\n\n"
        "📜 <i>New rules have been saved!</i>"
    )

async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules = get_setting(update.effective_chat.id, "rules_text", "")
    if not rules:
        return await reply(update,
            "📜 <b>No rules set yet!</b>\n"
            "<i>Admins can use /setrules to set the rules.</i>"
        )
    await reply(update,
        "╔══════════════════════════════╗\n"
        f"║  📜 <b>RULES — {html.escape((update.effective_chat.title or '')[:12])}</b>  ║\n"
        "╚══════════════════════════════╝\n\n"
        f"{html.escape(rules)}"
    )

# ────────────── NOTES ─────────────────────────────────────────────────────────
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
        "╔══════════════════════╗\n"
        "║   ✅ <b>NOTE SAVED!</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"📝 <b>Name:</b> <code>#{name}</code>\n"
        f"💾 <i>Retrieve anytime with <code>/get {name}</code> or <code>#{name}</code></i>"
    )

async def get_note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/get name</code>")
    await _send_note(update, context, context.args[0].lower())

async def _send_note(update, context, name):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    row = db.execute("SELECT * FROM notes WHERE chat_id=? AND name=?", (chat_id, name)).fetchone()
    db.close()
    if not row:
        return await reply(update, f"❌ <b>Note <code>#{name}</code> not found!</b>")
    content = row["content"] or ""
    kb = parse_buttons(row["buttons"] or "[]")
    await reply(update, content, reply_markup=InlineKeyboardMarkup(kb) if kb else None)

async def hash_note_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    words = update.message.text.split()
    for word in words:
        if word.startswith("#") and len(word) > 1:
            name = word[1:].lower()
            await _send_note(update, context, name)
            return

async def notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    rows = db.execute("SELECT name FROM notes WHERE chat_id=? ORDER BY name", (chat_id,)).fetchall()
    db.close()
    if not rows:
        return await reply(update,
            "╔══════════════════════╗\n"
            "║    📝 <b>NO NOTES</b>    ║\n"
            "╚══════════════════════╝\n\n"
            "<i>No notes saved yet. Use /save to create one!</i>"
        )
    names = " | ".join(f"<code>#{r['name']}</code>" for r in rows)
    await reply(update,
        "╔══════════════════════╗\n"
        "║    📝 <b>NOTES LIST</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"<b>{len(rows)} notes saved:</b>\n{names}"
    )

@admin_only
async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/clear name</code>")
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

# ────────────── FILTERS ───────────────────────────────────────────────────────
@admin_only
async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await reply(update, "❓ <b>Usage:</b> <code>/filter keyword reply text</code>")
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
        "╔══════════════════════╗\n"
        "║  ✅ <b>FILTER ADDED!</b>  ║\n"
        "╚══════════════════════╝\n\n"
        f"🔑 <b>Keyword:</b> <code>{html.escape(keyword)}</code>\n"
        f"{'🔢 <b>Type:</b> Regex' if is_regex else '📝 <b>Type:</b> Exact match'}\n"
        f"💬 <i>I'll auto-respond when someone says this!</i>"
    )

async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    rows = db.execute("SELECT keyword, is_regex FROM filters WHERE chat_id=? ORDER BY keyword", (chat_id,)).fetchall()
    db.close()
    if not rows:
        return await reply(update, "❌ <b>No filters active.</b>")
    lines = [
        "╔══════════════════════╗\n"
        "║  🔍 <b>ACTIVE FILTERS</b>  ║\n"
        "╚══════════════════════╝\n"
    ]
    for r in rows:
        icon = "🔢" if r["is_regex"] else "🔑"
        lines.append(f"{icon} <code>{html.escape(r['keyword'])}</code>")
    await reply(update, "\n".join(lines))

@admin_only
async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/stop keyword</code>")
    keyword = context.args[0].lower()
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM filters WHERE chat_id=? AND keyword=?", (chat_id, keyword))
    db.commit(); db.close()
    await reply(update, f"✅ <b>Filter <code>{html.escape(keyword)}</code> removed!</b>")

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
        kw = row["keyword"]
        matched = False
        if row["is_regex"]:
            try: matched = bool(re.search(kw, text, re.IGNORECASE))
            except: pass
        else:
            matched = kw in text
        if matched:
            content = row["reply"] or ""
            kb = parse_buttons(row["buttons"] or "[]")
            await reply(update, content, reply_markup=InlineKeyboardMarkup(kb) if kb else None)
            return

# ────────────── BLACKLIST ─────────────────────────────────────────────────────
@admin_only
async def addbl_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/addbl word</code>")
    word = " ".join(context.args).lower()
    is_regex = word.startswith("regex:")
    if is_regex: word = word[6:]
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("INSERT OR IGNORE INTO blacklist (chat_id, word, is_regex, added_by) VALUES (?,?,?,?)",
               (chat_id, word, 1 if is_regex else 0, update.effective_user.id))
    db.commit(); db.close()
    await reply(update,
        "╔══════════════════════╗\n"
        "║  ✅ <b>WORD BLACKLISTED</b> ║\n"
        "╚══════════════════════╝\n\n"
        f"🚫 <code>{html.escape(word)}</code> added to blacklist!"
    )

@admin_only
async def unblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/unblacklist word</code>")
    word = " ".join(context.args).lower()
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM blacklist WHERE chat_id=? AND word=?", (chat_id, word))
    db.commit(); db.close()
    await reply(update, f"✅ <b><code>{html.escape(word)}</code> removed from blacklist!</b>")

async def blacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    rows = db.execute("SELECT word, is_regex FROM blacklist WHERE chat_id=? ORDER BY word", (chat_id,)).fetchall()
    db.close()
    if not rows:
        return await reply(update, "✅ <b>Blacklist is empty!</b>")
    lines = [
        "╔══════════════════════╗\n"
        "║    🚫 <b>BLACKLIST</b>    ║\n"
        "╚══════════════════════╝\n"
    ]
    for r in rows:
        lines.append(f"• <code>{html.escape(r['word'])}</code>" + (" <i>(regex)</i>" if r["is_regex"] else ""))
    await reply(update, "\n".join(lines))

@admin_only
async def blacklistmode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ("delete", "warn", "mute", "ban"):
        return await reply(update, "❓ <b>Usage:</b> <code>/blacklistmode delete|warn|mute|ban</code>")
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

# ────────────── ANTI-SPAM / FLOOD ─────────────────────────────────────────────
async def antispam_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user: return
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    cfg = get_chat(chat_id)
    if await is_admin(context, chat_id, user_id): return

    if cfg.get("anti_flood", 1):
        flood_count = cfg.get("flood_count", 5)
        flood_time = cfg.get("flood_time", 5)
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
                f"👤 {user_link(update.effective_user)} has been <b>{action_text}</b> for flooding!",
                parse_mode="HTML")
            return

    if cfg.get("anti_link") and update.message.text:
        url_pattern = r'(https?://|t\.me/|@\w+|tg://)'
        if re.search(url_pattern, update.message.text, re.IGNORECASE):
            try: await update.message.delete()
            except: pass
            return

    if cfg.get("anti_forward") and update.message.forward_date:
        try: await update.message.delete()
        except: pass
        return

    msg = update.message
    async def _del():
        try: await msg.delete()
        except: pass
    if msg.sticker and cfg.get("lock_stickers"):
        await _del(); return
    if msg.animation and cfg.get("lock_gifs"):
        await _del(); return
    if (msg.photo or msg.document or msg.video or msg.audio) and cfg.get("lock_media"):
        await _del(); return
    if msg.poll and cfg.get("lock_polls"):
        await _del(); return
    if msg.voice and cfg.get("lock_voice"):
        await _del(); return
    if msg.video_note and cfg.get("lock_video"):
        await _del(); return
    if msg.document and cfg.get("lock_document"):
        await _del(); return
    if msg.forward_date and cfg.get("lock_forward"):
        await _del(); return
    if msg.game and cfg.get("lock_games"):
        await _del(); return

    db = get_db()
    db.execute("UPDATE users SET total_msgs=total_msgs+1 WHERE user_id=?", (user_id,))
    db.commit(); db.close()

# ────────────── ANTI-SPAM SETTINGS ────────────────────────────────────────────
@admin_only
async def antispam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_spam", 1 if val else 0)
    icon = "✅" if val else "❌"
    await reply(update, f"{icon} <b>Anti-spam {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def antiflood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_flood", 1 if val else 0)
    icon = "✅" if val else "❌"
    await reply(update, f"{icon} <b>Anti-flood {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def setflood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/setflood N [seconds]</code>")
    try:
        n = int(context.args[0])
        t = int(context.args[1]) if len(context.args) > 1 else 5
    except ValueError:
        return await reply(update, "❌ <b>Invalid numbers provided.</b>")
    db = get_db()
    db.execute("UPDATE chats SET flood_count=?, flood_time=? WHERE chat_id=?", (n, t, update.effective_chat.id))
    db.commit(); db.close()
    await reply(update,
        "╔══════════════════════╗\n"
        "║  🌊 <b>FLOOD LIMIT SET</b> ║\n"
        "╚══════════════════════╝\n\n"
        f"🔢 <b>Limit:</b> {n} messages\n"
        f"⏱️ <b>Window:</b> {t} seconds\n"
        f"✅ <i>Anti-flood configured!</i>"
    )

@admin_only
async def setfloodaction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ("mute", "ban", "kick"):
        return await reply(update, "❓ <b>Usage:</b> <code>/setfloodaction mute|ban|kick</code>")
    set_setting(update.effective_chat.id, "flood_action", context.args[0])
    await reply(update, f"✅ <b>Flood action:</b> <code>{context.args[0]}</code>")

@admin_only
async def antilink_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_link", 1 if val else 0)
    icon = "✅" if val else "❌"
    await reply(update, f"{icon} <b>Anti-link {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def antiforward_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_forward", 1 if val else 0)
    icon = "✅" if val else "❌"
    await reply(update, f"{icon} <b>Anti-forward {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def antibot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_bot", 1 if val else 0)
    icon = "✅" if val else "❌"
    await reply(update, f"{icon} <b>Anti-bot {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def antiraid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_raid", 1 if val else 0)
    icon = "✅" if val else "❌"
    await reply(update, f"{icon} <b>Anti-raid {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def setraid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/setraid N</code>")
    try:
        n = int(context.args[0])
    except ValueError:
        return await reply(update, "❌ <b>Invalid number.</b>")
    set_setting(update.effective_chat.id, "raid_threshold", n)
    await reply(update, f"✅ <b>Raid threshold:</b> {n} joins/minute")

@admin_only
async def cas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "cas_enabled", 1 if val else 0)
    icon = "✅" if val else "❌"
    await reply(update, f"{icon} <b>CAS protection {'enabled' if val else 'disabled'}!</b>")

# ────────────── WARN SETTINGS ────────────────────────────────────────────────
@admin_only
async def setwarnlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/setwarnlimit N</code>")
    try:
        n = int(context.args[0])
    except ValueError:
        return await reply(update, "❌ <b>Invalid number.</b>")
    set_setting(update.effective_chat.id, "warn_limit", n)
    await reply(update, f"✅ <b>Warn limit set to {n}!</b>")

@admin_only
async def setwarnaction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ("mute", "ban", "kick"):
        return await reply(update, "❓ <b>Usage:</b> <code>/setwarnaction mute|ban|kick</code>")
    set_setting(update.effective_chat.id, "warn_action", context.args[0])
    await reply(update, f"✅ <b>Warn action:</b> <code>{context.args[0]}</code>")

# ────────────── REPORT ────────────────────────────────────────────────────────
async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await reply(update, "❓ <b>Reply to a message to report it!</b>")
    cfg = get_chat(update.effective_chat.id)
    if not cfg.get("report_enabled", 1):
        return await reply(update, "❌ <b>Reports are disabled in this chat.</b>")
    reported = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "No reason given"
    db = get_db()
    db.execute("INSERT INTO reports (chat_id, reporter_id, reported_id, message_id, reason) VALUES (?,?,?,?,?)",
               (update.effective_chat.id, update.effective_user.id, reported.id,
                update.message.reply_to_message.message_id, reason))
    db.commit(); db.close()
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        mentions = " ".join(f'<a href="tg://user?id={a.user.id}">​</a>' for a in admins if not a.user.is_bot)
    except:
        mentions = ""
    text = (
        "╔══════════════════════╗\n"
        "║    🚨 <b>USER REPORTED</b>  ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 <b>Reported:</b> {user_link(reported)}\n"
        f"📢 <b>Reporter:</b> {user_link(update.effective_user)}\n"
        f"📝 <b>Reason:</b> {html.escape(reason)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👮 {mentions}"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔨 Ban", callback_data=f"report_ban:{reported.id}"),
        InlineKeyboardButton("🔇 Mute", callback_data=f"report_mute:{reported.id}"),
        InlineKeyboardButton("✅ Dismiss", callback_data=f"report_dismiss:{update.message.reply_to_message.message_id}"),
    ]])
    await reply(update, text, reply_markup=kb)

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not await is_admin(context, update.effective_chat.id, q.from_user.id):
        await q.answer("🚫 Admins only!", show_alert=True); return
    await q.answer()
    data = q.data
    if data.startswith("report_ban:"):
        uid = int(data.split(":")[1])
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, uid)
            await q.edit_message_text(
                q.message.text + f"\n\n🔨 <b>Banned by {user_link(q.from_user)}</b>",
                parse_mode="HTML")
        except Exception as e:
            await q.message.reply_text(f"❌ {e}")
    elif data.startswith("report_mute:"):
        uid = int(data.split(":")[1])
        try:
            await context.bot.restrict_chat_member(update.effective_chat.id, uid, MUTE_PERMS)
            await q.edit_message_text(
                q.message.text + f"\n\n🔇 <b>Muted by {user_link(q.from_user)}</b>",
                parse_mode="HTML")
        except Exception as e:
            await q.message.reply_text(f"❌ {e}")
    elif data.startswith("report_dismiss:"):
        await q.edit_message_text(f"✅ <b>Report dismissed by {user_link(q.from_user)}</b>", parse_mode="HTML")

# ────────────── FEDERATION SYSTEM ─────────────────────────────────────────────
@groups_only
async def newfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>Admins only.</b>")
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/newfed FederationName</code>")
    name = " ".join(context.args)
    fed_id = str(uuid.uuid4())[:8]
    db = get_db()
    db.execute("INSERT INTO federations (fed_id, name, owner_id) VALUES (?,?,?)",
               (fed_id, name, update.effective_user.id))
    db.execute("INSERT OR IGNORE INTO federation_chats (fed_id, chat_id) VALUES (?,?)",
               (fed_id, update.effective_chat.id))
    db.execute("UPDATE chats SET fed_id=? WHERE chat_id=?", (fed_id, update.effective_chat.id))
    db.commit(); db.close()
    await reply(update,
        "╔══════════════════════╗\n"
        "║  🌐 <b>FEDERATION CREATED!</b>  ║\n"
        "╚══════════════════════╝\n\n"
        f"📋 <b>Name:</b> {html.escape(name)}\n"
        f"🔑 <b>Fed ID:</b> <code>{fed_id}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Share the Fed ID so other groups can /joinfed!</i>"
    )

async def joinfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>Only group owner can join a federation.</b>")
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/joinfed fed_id</code>")
    fed_id = context.args[0]
    db = get_db()
    fed = db.execute("SELECT * FROM federations WHERE fed_id=?", (fed_id,)).fetchone()
    if not fed: db.close(); return await reply(update, "❌ <b>Federation not found!</b>")
    db.execute("INSERT OR IGNORE INTO federation_chats (fed_id, chat_id) VALUES (?,?)",
               (fed_id, update.effective_chat.id))
    db.execute("UPDATE chats SET fed_id=? WHERE chat_id=?", (fed_id, update.effective_chat.id))
    db.commit(); db.close()
    await reply(update,
        "╔══════════════════════╗\n"
        "║  🌐 <b>FEDERATION JOINED!</b>  ║\n"
        "╚══════════════════════╝\n\n"
        f"✅ Joined <b>{html.escape(fed['name'])}</b>!\n"
        f"<i>Fed bans will now apply to this group.</i>"
    )

async def leavefed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>Only group owner can leave a federation.</b>")
    db = get_db()
    fed_id = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_id or not fed_id["fed_id"]:
        db.close(); return await reply(update, "❌ <b>This chat isn't in a federation!</b>")
    db.execute("DELETE FROM federation_chats WHERE fed_id=? AND chat_id=?", (fed_id["fed_id"], update.effective_chat.id))
    db.execute("UPDATE chats SET fed_id=NULL WHERE chat_id=?", (update.effective_chat.id,))
    db.commit(); db.close()
    await reply(update, "✅ <b>Left the federation successfully!</b>")

async def fedinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_id = context.args[0] if context.args else None
    if not fed_id:
        row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
        fed_id = row["fed_id"] if row else None
    if not fed_id: db.close(); return await reply(update, "❌ <b>No federation found!</b>")
    fed = db.execute("SELECT * FROM federations WHERE fed_id=?", (fed_id,)).fetchone()
    if not fed: db.close(); return await reply(update, "❌ <b>Federation not found!</b>")
    chat_count = db.execute("SELECT COUNT(*) as c FROM federation_chats WHERE fed_id=?", (fed_id,)).fetchone()["c"]
    ban_count = db.execute("SELECT COUNT(*) as c FROM federation_bans WHERE fed_id=?", (fed_id,)).fetchone()["c"]
    db.close()
    await reply(update,
        "╔══════════════════════╗\n"
        "║    🌐 <b>FED INFO</b>     ║\n"
        "╚══════════════════════╝\n\n"
        f"📋 <b>Name:</b> {html.escape(fed['name'])}\n"
        f"🔑 <b>ID:</b> <code>{fed_id}</code>\n"
        f"💬 <b>Chats:</b> {chat_count}\n"
        f"🚫 <b>Total Bans:</b> {ban_count}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Created: {fed['created_at']}</i>"
    )

async def fban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]:
        db.close(); return await reply(update, "❌ <b>This chat isn't in a federation!</b>")
    fed_id = fed_row["fed_id"]
    fed = db.execute("SELECT * FROM federations WHERE fed_id=?", (fed_id,)).fetchone()
    is_fed_admin = (update.effective_user.id == fed["owner_id"] or
                    db.execute("SELECT 1 FROM federation_admins WHERE fed_id=? AND user_id=?",
                               (fed_id, update.effective_user.id)).fetchone() or
                    is_sudo(update.effective_user.id))
    if not is_fed_admin:
        db.close(); return await reply(update, "❌ <b>You're not a federation admin!</b>")
    target = get_target(update, context)
    if not target: db.close(); return await reply(update, "❓ Reply to a user or provide username.")
    reason = " ".join(context.args) if context.args else "Federation ban"
    db.execute("INSERT OR REPLACE INTO federation_bans (fed_id, user_id, reason, banned_by) VALUES (?,?,?,?)",
               (fed_id, target.id, reason, update.effective_user.id))
    chats = db.execute("SELECT chat_id FROM federation_chats WHERE fed_id=?", (fed_id,)).fetchall()
    db.commit(); db.close()
    m = await animate_loading(update, "Applying federation ban")
    banned_in = 0
    for ch in chats:
        try:
            await context.bot.ban_chat_member(ch["chat_id"], target.id)
            banned_in += 1
        except: pass
    await finish_anim(m,
        "╔══════════════════════╗\n"
        "║   🌐 <b>FED BAN APPLIED!</b>  ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"📝 <b>Reason:</b> {html.escape(reason)}\n"
        f"💬 <b>Banned in:</b> {banned_in} chats\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <i>Ban applied across the entire federation.</i>"
    )

async def unfban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]:
        db.close(); return await reply(update, "❌ <b>Not in a federation!</b>")
    fed_id = fed_row["fed_id"]
    target = get_target(update, context)
    if not target: db.close(); return await reply(update, "❓ Reply to a user or provide username.")
    db.execute("DELETE FROM federation_bans WHERE fed_id=? AND user_id=?", (fed_id, target.id))
    chats = db.execute("SELECT chat_id FROM federation_chats WHERE fed_id=?", (fed_id,)).fetchall()
    db.commit(); db.close()
    for ch in chats:
        try: await context.bot.unban_chat_member(ch["chat_id"], target.id, only_if_banned=True)
        except: pass
    await reply(update,
        "╔══════════════════════╗\n"
        "║  ✅ <b>FED BAN LIFTED!</b>  ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"🟢 <i>User unbanned from all federation chats.</i>"
    )

async def fedbans_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]:
        db.close(); return await reply(update, "❌ <b>Not in a federation!</b>")
    fed_id = fed_row["fed_id"]
    bans = db.execute(
        "SELECT fb.*, u.username, u.first_name FROM federation_bans fb "
        "LEFT JOIN users u ON u.user_id=fb.user_id WHERE fb.fed_id=? LIMIT 20",
        (fed_id,)).fetchall()
    db.close()
    if not bans:
        return await reply(update, "✅ <b>No federation bans!</b>")
    lines = [
        "╔══════════════════════╗\n"
        f"║  🌐 <b>FED BANS ({len(bans)})</b>  ║\n"
        "╚══════════════════════╝\n"
    ]
    for b in bans:
        name = html.escape(b["first_name"] or str(b["user_id"]))
        lines.append(f"🚫 {name} — <i>{html.escape(b['reason'] or 'No reason')}</i>")
    await reply(update, "\n".join(lines))

# ────────────── CONNECTION SYSTEM ─────────────────────────────────────────────
def get_connected_chat(user_id: int, chat: Chat) -> int:
    if chat.type != "private": return chat.id
    return connection_cache.get(user_id, chat.id)

async def connect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return await reply(update, "❓ <b>Use this command in my DM!</b>")
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/connect chat_id</code>")
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
            "╔══════════════════════╗\n"
            "║  🔗 <b>CONNECTED!</b>   ║\n"
            "╚══════════════════════╝\n\n"
            f"💬 <b>Group:</b> {html.escape(chat_obj.title or str(chat_id))}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <i>You can now use admin commands from here!</i>"
        )
    except Exception as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def disconnect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return await reply(update, "❓ <b>Use this command in my DM!</b>")
    connection_cache.pop(update.effective_user.id, None)
    db = get_db()
    db.execute("DELETE FROM connections WHERE user_id=?", (update.effective_user.id,))
    db.commit(); db.close()
    await reply(update, "🔌 <b>Disconnected!</b>\n<i>You're no longer connected to any group.</i>")

async def connected_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = connection_cache.get(update.effective_user.id)
    if not cid:
        db = get_db()
        row = db.execute("SELECT chat_id FROM connections WHERE user_id=?", (update.effective_user.id,)).fetchone()
        db.close()
        if row:
            cid = row["chat_id"]
            connection_cache[update.effective_user.id] = cid
    if not cid:
        return await reply(update, "🔌 <b>Not connected!</b>\n<i>Use /connect [chat_id] to connect.</i>")
    try:
        chat = await context.bot.get_chat(cid)
        await reply(update,
            "╔══════════════════════╗\n"
            "║  🔗 <b>CONNECTION INFO</b>  ║\n"
            "╚══════════════════════╝\n\n"
            f"✅ Connected to: <b>{html.escape(chat.title or str(cid))}</b>\n"
            f"🆔 <b>ID:</b> <code>{cid}</code>"
        )
    except:
        await reply(update, f"🔗 <b>Connected to:</b> <code>{cid}</code>")

# ────────────── AFK ───────────────────────────────────────────────────────────
async def afk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = " ".join(context.args) if context.args else ""
    user_id = update.effective_user.id
    afk_cache[user_id] = {"reason": reason, "since": datetime.datetime.now(pytz.utc)}
    db = get_db()
    db.execute("UPDATE users SET is_afk=1, afk_reason=?, afk_since=CURRENT_TIMESTAMP WHERE user_id=?",
               (reason, user_id))
    db.commit(); db.close()
    await reply(update,
        "╔══════════════════════╗\n"
        "║    😴 <b>AFK MODE ON</b>   ║\n"
        "╚══════════════════════╝\n\n"
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
        diff = datetime.datetime.now(pytz.utc) - since
        mins = int(diff.total_seconds() // 60)
        await reply(update,
            f"✅ <b>{user_link(update.effective_user)} is back!</b>\n"
            f"⏱️ <i>Was AFK for {mins} minutes.</i>"
        )
    if update.message.reply_to_message:
        ru = update.message.reply_to_message.from_user
        if ru and ru.id in afk_cache:
            afk = afk_cache[ru.id]
            since = afk["since"]
            diff = datetime.datetime.now(pytz.utc) - since
            hours = int(diff.total_seconds() // 3600)
            mins = int((diff.total_seconds() % 3600) // 60)
            reason = afk.get("reason", "")
            time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
            await reply(update,
                f"😴 <b>{user_link(ru)} is AFK!</b>\n"
                f"⏱️ <i>Away for {time_str}</i>"
                + (f"\n📝 <b>Reason:</b> {html.escape(reason)}" if reason else "")
            )

# ────────────── GLOBAL BAN ────────────────────────────────────────────────────
@owner_only
async def gban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user or provide username.")
    reason = " ".join(context.args[1:]) if not update.message.reply_to_message else " ".join(context.args)
    m = await animate_loading(update, "Applying global ban")
    db = get_db()
    db.execute("""INSERT INTO users (user_id, is_gbanned, gban_reason, gbanned_by, gbanned_at)
                  VALUES (?,1,?,?,CURRENT_TIMESTAMP)
                  ON CONFLICT(user_id) DO UPDATE SET is_gbanned=1, gban_reason=excluded.gban_reason,
                  gbanned_by=excluded.gbanned_by, gbanned_at=excluded.gbanned_at""",
               (target.id, reason or "No reason", update.effective_user.id))
    chats = db.execute("SELECT chat_id FROM chats").fetchall()
    db.commit(); db.close()
    banned_in = 0
    for ch in chats:
        try:
            await context.bot.ban_chat_member(ch["chat_id"], target.id)
            banned_in += 1
        except: pass
    log_action(0, update.effective_user.id, "gban", target.id, reason)
    await finish_anim(m,
        "╔══════════════════════╗\n"
        "║  🌍 <b>GLOBAL BAN!</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"📝 <b>Reason:</b> {html.escape(reason or 'No reason')}\n"
        f"💬 <b>Banned in:</b> {banned_in} chats\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <i>Ban applied globally across all groups!</i>"
    )
    if GBAN_LOG:
        try:
            await context.bot.send_message(GBAN_LOG,
                f"🌍 <b>GBAN</b>\n"
                f"User: {user_link(target)} (<code>{target.id}</code>)\n"
                f"By: {user_link(update.effective_user)}\n"
                f"Reason: {html.escape(reason or 'None')}",
                parse_mode="HTML")
        except: pass

@owner_only
async def ungban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user or provide username.")
    m = await animate_loading(update, "Removing global ban")
    db = get_db()
    db.execute("UPDATE users SET is_gbanned=0, gban_reason=NULL WHERE user_id=?", (target.id,))
    chats = db.execute("SELECT chat_id FROM chats").fetchall()
    db.commit(); db.close()
    for ch in chats:
        try: await context.bot.unban_chat_member(ch["chat_id"], target.id, only_if_banned=True)
        except: pass
    await finish_anim(m,
        "╔══════════════════════╗\n"
        "║  ✅ <b>GBAN LIFTED!</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"🟢 <i>Global ban removed from all chats!</i>"
    )

# ────────────── SUDO ──────────────────────────────────────────────────────────
@owner_only
async def sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    db = get_db()
    db.execute("INSERT OR IGNORE INTO sudo_users (user_id, added_by) VALUES (?,?)",
               (target.id, update.effective_user.id))
    db.execute("UPDATE users SET is_sudo=1 WHERE user_id=?", (target.id,))
    db.commit(); db.close()
    await reply(update,
        "╔══════════════════════╗\n"
        "║  👑 <b>SUDO GRANTED!</b>  ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 {user_link(target)} now has sudo powers!"
    )

@owner_only
async def unsudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    db = get_db()
    db.execute("DELETE FROM sudo_users WHERE user_id=?", (target.id,))
    db.execute("UPDATE users SET is_sudo=0 WHERE user_id=?", (target.id,))
    db.commit(); db.close()
    await reply(update, f"✅ <b>Sudo revoked from {user_link(target)}!</b>")

# ────────────── BROADCAST ─────────────────────────────────────────────────────
@owner_only
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast to all chats. All members stay tracked even after restarts."""
    if not context.args and not update.message.reply_to_message:
        return await reply(update,
            "╔══════════════════════╗\n"
            "║  📢 <b>BROADCAST</b>     ║\n"
            "╚══════════════════════╝\n\n"
            "📣 <b>Usage:</b> <code>/broadcast Your message here</code>\n"
            "💡 <i>Or reply to a message with /broadcast</i>\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🔹 <code>/broadcast</code> — sends to all <b>chats</b>\n"
            "🔹 <code>/broadcastall</code> — sends to all <b>members</b>"
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
        except:
            failed += 1
        if i % 10 == 0 or i == total:
            try:
                await m.edit_text(
                    f"📢 <b>Broadcasting...</b>\n"
                    f"[{progress_bar(i, total)}] {i}/{total}\n"
                    f"✅ Sent: {sent} | ❌ Failed: {failed}",
                    parse_mode="HTML")
            except: pass
        await asyncio.sleep(0.05)
    await m.edit_text(
        "╔══════════════════════╗\n"
        "║  📢 <b>BROADCAST DONE!</b>  ║\n"
        "╚══════════════════════╝\n\n"
        f"💬 <b>Total chats:</b> {total}\n"
        f"✅ <b>Sent:</b> {sent}\n"
        f"❌ <b>Failed:</b> {failed}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Success rate:</b> {int(sent/total*100) if total else 0}%",
        parse_mode="HTML")

@owner_only
async def broadcastall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast to ALL individual members — persists across bot restarts."""
    if not context.args and not update.message.reply_to_message:
        return await reply(update,
            "❓ <b>Usage:</b> <code>/broadcastall Your message</code>\n"
            "<i>Sends to all tracked individual members (survives restarts)</i>"
        )
    text = " ".join(context.args) if context.args else update.message.reply_to_message.text
    db = get_db()
    # Get all unique non-bot users who have ever been seen
    members = db.execute(
        "SELECT DISTINCT user_id FROM chat_members WHERE is_bot=0"
    ).fetchall()
    db.close()
    total = len(members)
    if total == 0:
        return await reply(update, "❌ <b>No members tracked yet!</b>\n<i>Members are tracked as they interact with the bot.</i>")
    m = await context.bot.send_message(update.effective_chat.id,
        f"📢 <b>Sending to {total} members...</b>\n[{progress_bar(0, total)}]",
        parse_mode="HTML")
    sent = failed = 0
    for i, member in enumerate(members, 1):
        try:
            await context.bot.send_message(member["user_id"], text, parse_mode="HTML")
            sent += 1
        except:
            failed += 1
        if i % 20 == 0 or i == total:
            try:
                await m.edit_text(
                    f"📢 <b>Broadcasting to members...</b>\n"
                    f"[{progress_bar(i, total)}] {i}/{total}\n"
                    f"✅ {sent} | ❌ {failed}",
                    parse_mode="HTML")
            except: pass
        await asyncio.sleep(0.08)  # Rate limit: ~12/sec
    await m.edit_text(
        "╔══════════════════════╗\n"
        "║ 📢 <b>BROADCAST COMPLETE!</b> ║\n"
        "╚══════════════════════╝\n\n"
        f"👥 <b>Total members:</b> {total}\n"
        f"✅ <b>Delivered:</b> {sent}\n"
        f"❌ <b>Failed:</b> {failed}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Delivery rate:</b> {int(sent/total*100) if total else 0}%",
        parse_mode="HTML")

# ────────────── STATS ─────────────────────────────────────────────────────────
@owner_only
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Fetching bot statistics")
    db = get_db()
    chats    = db.execute("SELECT COUNT(*) as c FROM chats").fetchone()["c"]
    users    = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    members  = db.execute("SELECT COUNT(*) as c FROM chat_members").fetchone()["c"]
    warns    = db.execute("SELECT COUNT(*) as c FROM warns").fetchone()["c"]
    bans     = db.execute("SELECT COUNT(*) as c FROM bans").fetchone()["c"]
    gbans    = db.execute("SELECT COUNT(*) as c FROM users WHERE is_gbanned=1").fetchone()["c"]
    notes    = db.execute("SELECT COUNT(*) as c FROM notes").fetchone()["c"]
    filters_c = db.execute("SELECT COUNT(*) as c FROM filters").fetchone()["c"]
    db.close()
    uptime = datetime.datetime.now(pytz.utc) - START_TIME
    total_seconds = int(uptime.total_seconds())
    days  = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    mins  = (total_seconds % 3600) // 60
    secs  = total_seconds % 60
    bar = progress_bar(min(total_seconds, 86400), 86400)
    await finish_anim(m,
        "╔══════════════════════════╗\n"
        "║    📊 <b>BOT STATISTICS</b>    ║\n"
        "╚══════════════════════════╝\n\n"
        f"💬 <b>Chats:</b> {chats}\n"
        f"👤 <b>Users tracked:</b> {users}\n"
        f"👥 <b>Members tracked:</b> {members}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ <b>Total warns:</b> {warns}\n"
        f"🚫 <b>Chat bans:</b> {bans}\n"
        f"🌍 <b>Global bans:</b> {gbans}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>Notes:</b> {notes}\n"
        f"🔍 <b>Filters:</b> {filters_c}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ <b>Uptime:</b> {days}d {hours}h {mins}m {secs}s\n"
        f"[{bar}]\n"
        f"🤖 <b>Version:</b> <code>{VERSION}</code>"
    )

# ────────────── INFO / ID ─────────────────────────────────────────────────────
async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    chat = update.effective_chat
    await reply(update,
        "╔══════════════════════╗\n"
        "║     🆔 <b>IDs</b>        ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 <b>User ID:</b> <code>{target.id}</code>\n"
        f"💬 <b>Chat ID:</b> <code>{chat.id}</code>"
    )

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Fetching user info")
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
    elif context.args:
        try:
            uid = int(context.args[0]) if context.args[0].isdigit() else None
            if uid:
                target = type("U", (), {"id": uid, "first_name": str(uid), "username": None, "last_name": None, "is_bot": False})()
            else:
                target = update.effective_user
        except:
            target = update.effective_user
    else:
        target = update.effective_user
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE user_id=?", (target.id,)).fetchone()
    warns = db.execute("SELECT COUNT(*) as c FROM warns WHERE user_id=?", (target.id,)).fetchone()["c"]
    db.close()
    name = html.escape(target.first_name or str(target.id))
    badges = ""
    if row and row["is_gbanned"]:
        badges += "🌍 GBanned "
    if row and row["is_sudo"]:
        badges += "👑 Sudo "
    if target.is_bot:
        badges += "🤖 Bot "
    text = (
        "╔══════════════════════════╗\n"
        "║    👤 <b>USER PROFILE</b>    ║\n"
        "╚══════════════════════════╝\n\n"
        f"📋 <b>Name:</b> <a href='tg://user?id={target.id}'>{name}</a>\n"
        f"🆔 <b>ID:</b> <code>{target.id}</code>\n"
    )
    if target.username:
        text += f"📌 <b>Username:</b> @{html.escape(target.username)}\n"
    if badges:
        text += f"🏷️ <b>Badges:</b> {badges}\n"
    if row:
        text += (
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>Warns:</b> {warns}\n"
            f"💰 <b>Coins:</b> {row['coins'] or 0}\n"
            f"⭐ <b>Reputation:</b> {row['reputation'] or 0}\n"
            f"💬 <b>Messages:</b> {row['total_msgs'] or 0}\n"
            f"🕐 <b>Last seen:</b> {row['last_seen'] or 'N/A'}"
        )
    if row and row["is_gbanned"]:
        text += f"\n\n🚫 <b>GLOBALLY BANNED</b>\n📝 Reason: {html.escape(row['gban_reason'] or 'No reason')}"
    await finish_anim(m, text)

async def chatinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Fetching chat info")
    chat = update.effective_chat
    try:
        members = await context.bot.get_chat_member_count(chat.id)
        db = get_db()
        tracked = db.execute("SELECT COUNT(*) as c FROM chat_members WHERE chat_id=?", (chat.id,)).fetchone()["c"]
        db.close()
        text = (
            "╔══════════════════════════╗\n"
            "║    💬 <b>CHAT INFO</b>      ║\n"
            "╚══════════════════════════╝\n\n"
            f"📋 <b>Title:</b> {html.escape(chat.title or 'N/A')}\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n"
            f"📁 <b>Type:</b> {chat.type.title()}\n"
            f"👥 <b>Members:</b> {members}\n"
            f"📊 <b>Tracked:</b> {tracked} members\n"
        )
        if chat.username:
            text += f"🔗 <b>Username:</b> @{chat.username}"
        await finish_anim(m, text)
    except Exception as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = time.time()
    m = await reply(update,
        "╔══════════════════════╗\n"
        "║  🏓 <b>PONG!</b>        ║\n"
        "╚══════════════════════╝\n\n"
        "⏱️ <i>Measuring latency...</i>"
    )
    elapsed = (time.time() - start) * 1000
    quality = "🟢 Excellent" if elapsed < 100 else ("🟡 Good" if elapsed < 300 else "🔴 Slow")
    await m.edit_text(
        "╔══════════════════════╗\n"
        "║  🏓 <b>PONG!</b>        ║\n"
        "╚══════════════════════╝\n\n"
        f"⚡ <b>Latency:</b> {elapsed:.1f}ms\n"
        f"📶 <b>Quality:</b> {quality}",
        parse_mode="HTML"
    )

async def uptime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.datetime.now(pytz.utc) - START_TIME
    total_seconds = int(uptime.total_seconds())
    days  = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    mins  = (total_seconds % 3600) // 60
    secs  = total_seconds % 60
    bar = progress_bar(total_seconds % 86400, 86400)
    await reply(update,
        "╔══════════════════════╗\n"
        "║    ⏱️ <b>UPTIME</b>      ║\n"
        "╚══════════════════════╝\n\n"
        f"🕐 <b>{days}d {hours}h {mins}m {secs}s</b>\n"
        f"[{bar}]\n\n"
        f"🚀 <i>Running since {START_TIME.strftime('%Y-%m-%d %H:%M UTC')}</i>"
    )

# ────────────── ECONOMY ───────────────────────────────────────────────────────
DAILY_COINS = 500
MINE_MIN, MINE_MAX = 10, 150

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
                "╔══════════════════════╗\n"
                "║  ⏰ <b>ALREADY CLAIMED</b>  ║\n"
                "╚══════════════════════╝\n\n"
                f"⏳ Come back in <b>{h}h {mi}m</b>\n"
                f"[{bar}]"
            )
    coins = DAILY_COINS + random.randint(0, 100)
    db.execute("UPDATE users SET coins=coins+?, last_daily=CURRENT_TIMESTAMP WHERE user_id=?", (coins, user_id))
    db.commit()
    new_bal = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()["coins"]
    db.close()
    await reply(update,
        "╔══════════════════════╗\n"
        "║   💰 <b>DAILY CLAIMED!</b>  ║\n"
        "╚══════════════════════╝\n\n"
        f"🎁 <b>+{coins} coins</b> added!\n"
        f"💳 <b>Balance:</b> {new_bal} coins\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ <i>Come back tomorrow for more!</i>"
    )

async def coins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context) or update.effective_user
    db = get_db()
    row = db.execute("SELECT coins FROM users WHERE user_id=?", (target.id,)).fetchone()
    db.close()
    balance = row["coins"] if row else 0
    bar = progress_bar(min(balance, 10000), 10000)
    await reply(update,
        "╔══════════════════════╗\n"
        "║    💰 <b>WALLET</b>       ║\n"
        "╚══════════════════════╝\n\n"
        f"👤 <b>User:</b> {user_link(target)}\n"
        f"💳 <b>Balance:</b> {balance:,} coins\n"
        f"[{bar}]"
    )

async def mine_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    m = await animate_loading(update, "Mining coins")
    await asyncio.sleep(0.5)
    earned = random.randint(MINE_MIN, MINE_MAX)
    db = get_db()
    db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (earned, user_id))
    db.commit()
    bal = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    msgs = [
        f"⛏️ <b>You mined {earned} coins!</b> Keep going!",
        f"💎 <b>Diamond vein! +{earned} coins!</b>",
        f"🪨 <b>Cracked a rock! Found {earned} coins!</b>",
        f"⚒️ <b>Hard work pays off! +{earned} coins!</b>",
    ]
    await finish_anim(m,
        "╔══════════════════════╗\n"
        "║   ⛏️ <b>MINING RESULT</b>  ║\n"
        "╚══════════════════════╝\n\n"
        f"{random.choice(msgs)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Balance:</b> {(bal['coins'] if bal else earned):,} coins"
    )

async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2 and not (update.message.reply_to_message and context.args):
        return await reply(update, "❓ <b>Usage:</b> <code>/give @user amount</code>")
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user or provide username.")
    try:
        amount = int(context.args[-1])
    except:
        return await reply(update, "❌ <b>Invalid amount!</b>")
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
        "╔══════════════════════╗\n"
        "║  💸 <b>COINS SENT!</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"💰 <b>Amount:</b> {amount:,} coins\n"
        f"📤 <b>From:</b> {user_link(update.effective_user)}\n"
        f"📥 <b>To:</b> {user_link(target)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Your balance:</b> {new_bal:,} coins"
    )

async def rob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user to rob.")
    if target.id == update.effective_user.id: return await reply(update, "❌ <b>Can't rob yourself!</b>")
    m = await animate_loading(update, "Planning the heist")
    db = get_db()
    victim = db.execute("SELECT coins FROM users WHERE user_id=?", (target.id,)).fetchone()
    if not victim or victim["coins"] < 100:
        db.close(); return await finish_anim(m, "❌ <b>That user doesn't have enough coins to rob!</b>")
    if random.random() < 0.4:
        fine = random.randint(50, 200)
        db.execute("UPDATE users SET coins=MAX(0, coins-?) WHERE user_id=?", (fine, update.effective_user.id))
        db.commit(); db.close()
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║   👮 <b>BUSTED!</b>      ║\n"
            "╚══════════════════════╝\n\n"
            f"🚓 You got caught trying to rob {user_link(target)}!\n"
            f"💸 <b>Fine:</b> {fine} coins paid"
        )
    else:
        stolen = random.randint(50, min(300, victim["coins"]))
        db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (stolen, target.id))
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (stolen, update.effective_user.id))
        db.commit(); db.close()
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║  💰 <b>HEIST SUCCESS!</b>  ║\n"
            "╚══════════════════════╝\n\n"
            f"🦹 You robbed {user_link(target)}!\n"
            f"💰 <b>Stolen:</b> {stolen:,} coins\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>They'll never see you coming!</i>"
        )

async def flip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        m = await animate_loading(update, "Flipping coin")
        result = "Heads 🦅" if random.random() > 0.5 else "Tails 🪙"
        await finish_anim(m,
            "╔══════════════════════╗\n"
            "║   🪙 <b>COIN FLIP!</b>   ║\n"
            "╚══════════════════════╝\n\n"
            f"Result: <b>{result}</b>!"
        )
        return
    amount = int(context.args[0])
    user_id = update.effective_user.id
    db = get_db()
    row = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row or row["coins"] < amount:
        db.close(); return await reply(update, "❌ <b>Insufficient coins!</b>")
    m = await animate_loading(update, "Flipping the coin")
    if random.random() > 0.5:
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, user_id))
        result_text = (
            "╔══════════════════════╗\n"
            "║   🎉 <b>YOU WON!</b>    ║\n"
            "╚══════════════════════╝\n\n"
            f"🦅 <b>HEADS!</b>\n"
            f"💰 <b>+{amount:,} coins</b> won!\n"
        )
    else:
        db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, user_id))
        result_text = (
            "╔══════════════════════╗\n"
            "║   😭 <b>YOU LOST!</b>   ║\n"
            "╚══════════════════════╝\n\n"
            f"🪙 <b>TAILS!</b>\n"
            f"💸 <b>-{amount:,} coins</b> lost!\n"
        )
    bal = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()["coins"]
    db.commit(); db.close()
    await finish_anim(m, result_text + f"━━━━━━━━━━━━━━━━━━━━━\n💳 <b>Balance:</b> {bal:,} coins")

async def slots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols = ["🍒", "🍋", "🍊", "💎", "7️⃣", "⭐"]
    weights = [30, 25, 20, 10, 5, 10]
    m = await animate_loading(update, "Spinning the reels")
    # Animate spinning
    for _ in range(2):
        spin = " | ".join(random.choices(symbols, k=3))
        try:
            await m.edit_text(f"🎰 <b>Spinning...</b>\n[ {spin} ]", parse_mode="HTML")
        except: pass
        await asyncio.sleep(0.4)
    roll = random.choices(symbols, weights=weights, k=3)
    result = " | ".join(roll)
    amount = int(context.args[0]) if context.args and context.args[0].isdigit() else 0
    user_id = update.effective_user.id
    if roll[0] == roll[1] == roll[2]:
        multiplier = 10 if roll[0] == "7️⃣" else (5 if roll[0] == "💎" else 3)
        winnings = amount * multiplier
        outcome = (
            f"🎉 <b>JACKPOT!</b>\n"
            f"💰 Won <b>{winnings:,} coins</b>! (x{multiplier})\n"
        )
        if amount:
            db = get_db()
            db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (winnings, user_id))
            db.commit(); db.close()
    elif roll[0] == roll[1] or roll[1] == roll[2]:
        outcome = "✨ <b>Small win!</b> Bet returned!\n"
    else:
        outcome = f"😢 <b>No match!</b> Lost <b>{amount:,} coins</b>.\n"
        if amount:
            db = get_db()
            db.execute("UPDATE users SET coins=MAX(0,coins-?) WHERE user_id=?", (amount, user_id))
            db.commit(); db.close()
    await finish_anim(m,
        "╔══════════════════════╗\n"
        "║    🎰 <b>SLOT MACHINE</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"[ {result} ]\n\n"
        f"{outcome}"
    )

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Loading leaderboard")
    db = get_db()
    rows = db.execute("SELECT user_id, username, first_name, coins FROM users ORDER BY coins DESC LIMIT 10").fetchall()
    db.close()
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [
        "╔══════════════════════════╗\n"
        "║   💰 <b>RICHEST MEMBERS</b>   ║\n"
        "╚══════════════════════════╝\n"
    ]
    for i, row in enumerate(rows):
        name = html.escape(row["first_name"] or str(row["user_id"]))
        lines.append(f"{medals[i]} {name} — <b>{row['coins']:,}</b> 🪙")
    await finish_anim(m, "\n".join(lines))

# ────────────── REPUTATION ────────────────────────────────────────────────────
async def rep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target:
        db = get_db()
        row = db.execute("SELECT reputation FROM users WHERE user_id=?", (update.effective_user.id,)).fetchone()
        db.close()
        rep = row["reputation"] if row else 0
        bar = progress_bar(rep, max(100, rep + 10))
        return await reply(update,
            "╔══════════════════════╗\n"
            "║    ⭐ <b>YOUR REP</b>    ║\n"
            "╚══════════════════════╝\n\n"
            f"⭐ <b>Reputation:</b> {rep}\n"
            f"[{bar}]"
        )
    if target.id == update.effective_user.id:
        return await reply(update, "❌ <b>Can't give rep to yourself!</b>")
    giver = update.effective_user.id
    db = get_db()
    existing = db.execute("SELECT given_at FROM reputation WHERE giver_id=? AND receiver_id=? AND chat_id=?",
                          (giver, target.id, update.effective_chat.id)).fetchone()
    if existing:
        given = datetime.datetime.fromisoformat(str(existing["given_at"]).replace(" ", "T")).replace(tzinfo=pytz.utc)
        if (datetime.datetime.now(pytz.utc) - given).total_seconds() < 86400:
            db.close()
            return await reply(update, "⏰ <b>Already given rep today!</b>\n<i>Come back tomorrow.</i>")
    db.execute("INSERT OR REPLACE INTO reputation (giver_id, receiver_id, chat_id) VALUES (?,?,?)",
               (giver, target.id, update.effective_chat.id))
    db.execute("UPDATE users SET reputation=reputation+1 WHERE user_id=?", (target.id,))
    row = db.execute("SELECT reputation FROM users WHERE user_id=?", (target.id,)).fetchone()
    db.commit(); db.close()
    rep = row["reputation"] if row else 1
    await reply(update,
        "╔══════════════════════╗\n"
        "║  ⭐ <b>REP GIVEN!</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"🎁 {user_link(update.effective_user)} gave +1 ⭐ to {user_link(target)}!\n"
        f"📊 <b>Total rep:</b> {rep}"
    )

async def reprank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Loading reputation board")
    db = get_db()
    rows = db.execute("SELECT user_id, first_name, reputation FROM users ORDER BY reputation DESC LIMIT 10").fetchall()
    db.close()
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = [
        "╔══════════════════════════╗\n"
        "║  ⭐ <b>REPUTATION LEADERS</b>  ║\n"
        "╚══════════════════════════╝\n"
    ]
    for i, row in enumerate(rows):
        name = html.escape(row["first_name"] or str(row["user_id"]))
        lines.append(f"{medals[i]} {name} — <b>{row['reputation']}</b> ⭐")
    await finish_anim(m, "\n".join(lines))

# ────────────── FUN ───────────────────────────────────────────────────────────
EIGHTBALL_ANSWERS = [
    "🟢 It is certain!", "🟢 Absolutely yes!", "🟢 Without a doubt!",
    "🟢 Yes, definitely!", "🟢 You may rely on it!", "🟢 As I see it, yes!",
    "🟢 Most likely!", "🟢 Outlook good!", "🟢 Signs point to yes!",
    "🟡 Reply hazy, try again...", "🟡 Ask again later...", "🟡 Better not tell you now.",
    "🟡 Cannot predict now.", "🔴 Don't count on it.", "🔴 My reply is no.",
    "🔴 My sources say NO.", "🔴 Outlook not so good.", "🔴 Very doubtful!"
]

async def eightball_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Ask me a question!</b>\n<code>/8ball Will I win the lottery?</code>")
    q = " ".join(context.args)
    m = await animate_loading(update, "Consulting the magic ball")
    answer = random.choice(EIGHTBALL_ANSWERS)
    await finish_anim(m,
        "╔══════════════════════╗\n"
        "║    🎱 <b>MAGIC 8-BALL</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"❓ <b>Q:</b> <i>{html.escape(q)}</i>\n\n"
        f"🎱 <b>A:</b> {answer}"
    )

async def roll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sides = int(context.args[0]) if context.args and context.args[0].isdigit() else 6
    m = await animate_loading(update, "Rolling the dice")
    result = random.randint(1, sides)
    await finish_anim(m,
        "╔══════════════════════╗\n"
        "║    🎲 <b>DICE ROLL!</b>    ║\n"
        "╚══════════════════════╝\n\n"
        f"🎲 <b>d{sides}</b> → <b>{result}</b>!\n"
        + ("🎯 <i>Critical hit!</i>" if result == sides else
           ("💀 <i>Critical fail!</i>" if result == 1 else
            f"<i>Result: {result}/{sides}</i>"))
    )

SLAP_MSGS = [
    "🐟 {user} slapped {target} with a large trout! The fish is shocked!",
    "👋 {user} delivered a thunderous slap to {target}! The room went silent.",
    "⚡ {user} slapped {target} so hard they saw stars! ⭐",
    "🧤 {user} put on a glove and slapped {target} across the face!",
]
HUG_MSGS = [
    "🤗 {user} gave {target} a warm, cozy hug! So wholesome!",
    "🐻 {user} wrapped {target} in the biggest bear hug ever!",
    "💙 {user} hugged {target} tightly. Everything feels better now!",
    "✨ {user} and {target} share a magical hug! Friendship +100!",
]
ROASTS = [
    "If laziness was a sport, you'd win a gold medal — without trying.",
    "You're like a cloud. When you disappear, it's a beautiful day.",
    "I'd agree with you but then we'd both be wrong.",
    "You have the charm of a wet napkin and twice the density.",
    "I've seen better arguments from a Magic 8-Ball.",
    "Your Wi-Fi personality? Weak signal, constant dropping.",
    "Even your shadow needs a break from you sometimes.",
    "If you were any slower, you'd be going backwards.",
]
COMPLIMENTS = [
    "✨ You light up every room you walk into!",
    "🌟 Your kindness is contagious in the best way!",
    "💪 You're stronger than you think you are!",
    "🎨 Your creativity is genuinely inspiring!",
    "🧠 Your mind works in the most fascinating ways!",
    "💙 The world is genuinely better with you in it!",
    "🌸 You make hard things look effortlessly beautiful!",
]
JOKES = [
    "😂 Why don't scientists trust atoms?\nBecause they make up everything!",
    "😄 Why did the scarecrow win an award?\nHe was outstanding in his field! 🌾",
    "🤣 What do you call fake spaghetti?\nAn impasta! 🍝",
    "😆 Why did the bicycle fall over?\nIt was two-tired! 🚲",
    "😂 What do you call a fish without eyes?\nA fsh! 🐟",
    "😄 Why can't you give Elsa a balloon?\nShe'll let it go! ❄️",
    "🤣 What do you call cheese that isn't yours?\nNacho cheese! 🧀",
]
TRUTH_QUESTIONS = [
    "What's your biggest fear you've never told anyone?",
    "What's the most embarrassing thing you've done in public?",
    "Have you ever pretended to be sick to avoid something?",
    "What's a secret talent you've been hiding?",
    "What's your biggest regret from the past year?",
    "Have you ever lied to a close friend? About what?",
]
DARES = [
    "🎤 Send a voice message singing a song right now!",
    "😂 Change your profile bio to something embarrassing for 1 hour.",
    "💌 Tag 3 friends and say one genuine compliment about each!",
    "🤔 Share your most embarrassing selfie in the chat.",
    "🎭 Speak in rhymes for the next 5 messages.",
    "🔢 Count to 20 in a language you barely know!",
]

async def slap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to someone to slap them!")
    msg = random.choice(SLAP_MSGS).format(user=user_link(update.effective_user), target=user_link(target))
    await reply(update,
        "╔══════════════════════╗\n"
        "║    👋 <b>SLAP!</b>        ║\n"
        "╚══════════════════════╝\n\n"
        f"{msg}"
    )

async def hug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❓ Reply to someone to hug them!")
    msg = random.choice(HUG_MSGS).format(user=user_link(update.effective_user), target=user_link(target))
    await reply(update,
        "╔══════════════════════╗\n"
        "║    🤗 <b>HUG!</b>         ║\n"
        "╚══════════════════════╝\n\n"
        f"{msg}"
    )

async def ship_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        u1 = update.effective_user
        u2 = update.message.reply_to_message.from_user
    elif context.args:
        u1 = update.effective_user
        u2 = type("U", (), {"first_name": context.args[0], "id": 0})()
    else:
        return await reply(update, "❓ Reply to a user or provide a name.")
    m = await animate_loading(update, "Calculating compatibility")
    compat = random.randint(1, 100)
    bar_filled = int(compat / 10)
    bar = "❤️" * bar_filled + "🖤" * (10 - bar_filled)
    if compat >= 80:
        verdict = "💞 A perfect match made in heaven!"
    elif compat >= 60:
        verdict = "💕 Very compatible!"
    elif compat >= 40:
        verdict = "💙 There's potential here..."
    else:
        verdict = "💔 Not the best match..."
    await finish_anim(m,
        "╔══════════════════════╗\n"
        "║   💕 <b>SHIP METER!</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"{user_link(u1)} ❤️ {html.escape(u2.first_name or '?')}\n\n"
        f"[{bar}]\n"
        f"💯 <b>{compat}% compatible!</b>\n"
        f"<i>{verdict}</i>"
    )

async def roast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    name = user_link(target) if target else user_link(update.effective_user)
    await reply(update,
        "╔══════════════════════╗\n"
        "║    🔥 <b>ROASTED!</b>     ║\n"
        "╚══════════════════════╝\n\n"
        f"🔥 {name}:\n<i>{random.choice(ROASTS)}</i>"
    )

async def compliment_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    name = user_link(target) if target else user_link(update.effective_user)
    await reply(update,
        "╔══════════════════════╗\n"
        "║   💐 <b>COMPLIMENT!</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"💐 {name}:\n{random.choice(COMPLIMENTS)}"
    )

async def joke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update,
        "╔══════════════════════╗\n"
        "║    😂 <b>JOKE TIME!</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"{random.choice(JOKES)}"
    )

async def truth_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update,
        "╔══════════════════════╗\n"
        "║   💭 <b>TRUTH!</b>       ║\n"
        "╚══════════════════════╝\n\n"
        f"🤔 <i>{random.choice(TRUTH_QUESTIONS)}</i>"
    )

async def dare_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update,
        "╔══════════════════════╗\n"
        "║   😈 <b>DARE!</b>        ║\n"
        "╚══════════════════════╝\n\n"
        f"{random.choice(DARES)}"
    )

# ────────────── UTILITY ───────────────────────────────────────────────────────
async def calc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/calc expression</code>\n<i>Example: /calc 2 + 2 * 5</i>")
    expr = " ".join(context.args)
    allowed = set("0123456789+-*/().% ")
    if not all(c in allowed for c in expr):
        return await reply(update, "❌ <b>Invalid characters!</b>\n<i>Only numbers and +, -, *, /, (), % allowed.</i>")
    try:
        result = eval(expr, {"__builtins__": {}}, {})
        await reply(update,
            "╔══════════════════════╗\n"
            "║    🧮 <b>CALCULATOR</b>   ║\n"
            "╚══════════════════════╝\n\n"
            f"📝 <code>{html.escape(expr)}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ <b>= {result}</b>"
        )
    except Exception as e:
        await reply(update, f"❌ <b>Math Error:</b> {html.escape(str(e))}")

async def qr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/qr text or URL</code>")
    import qrcode
    text = " ".join(context.args)
    m = await animate_loading(update, "Generating QR code")
    try:
        img = qrcode.make(text)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        buf.seek(0)
        try: await m.delete()
        except: pass
        await update.message.reply_photo(buf, caption=
            "╔══════════════════════╗\n"
            "║    📱 <b>QR CODE</b>     ║\n"
            "╚══════════════════════╝\n\n"
            f"📝 Content: <code>{html.escape(text[:50])}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/tr lang text</code>\n<i>Example: /tr es Hello world!</i>")
    lang = context.args[0]
    text = " ".join(context.args[1:]) if len(context.args) > 1 else (
        update.message.reply_to_message.text if update.message.reply_to_message else "")
    if not text:
        return await reply(update, "❌ <b>Provide text to translate!</b>")
    m = await animate_loading(update, "Translating")
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={lang}&dt=t&q={urllib.parse.quote(text)}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                translated = "".join(p[0] for p in data[0] if p[0])
                await finish_anim(m,
                    "╔══════════════════════╗\n"
                    "║   🌐 <b>TRANSLATION</b>   ║\n"
                    "╚══════════════════════╝\n\n"
                    f"🔤 <b>Original:</b>\n<i>{html.escape(text[:200])}</i>\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"🌍 <b>→ {lang.upper()}:</b>\n{html.escape(translated)}"
                )
    except Exception as e:
        await finish_anim(m, f"❌ <b>Translation failed:</b> {html.escape(str(e))}")

async def hash_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/hash text</code>")
    text = " ".join(context.args).encode()
    md5    = hashlib.md5(text).hexdigest()
    sha1   = hashlib.sha1(text).hexdigest()
    sha256 = hashlib.sha256(text).hexdigest()
    await reply(update,
        "╔══════════════════════╗\n"
        "║    🔐 <b>HASHES</b>       ║\n"
        "╚══════════════════════╝\n\n"
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
            result = base64.b64encode(text.encode()).decode()
            label = "📤 Encoded"
        else:
            result = base64.b64decode(text.encode()).decode()
            label = "📥 Decoded"
        await reply(update,
            "╔══════════════════════╗\n"
            "║    🔢 <b>BASE64</b>       ║\n"
            "╚══════════════════════╝\n\n"
            f"{label}:\n<code>{html.escape(result)}</code>"
        )
    except Exception as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/weather city</code>")
    city = " ".join(context.args)
    m = await animate_loading(update, "Fetching weather")
    url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                current = data["current_condition"][0]
                temp_c = current["temp_C"]
                temp_f = current["temp_F"]
                desc = current["weatherDesc"][0]["value"]
                feels = current["FeelsLikeC"]
                humidity = current["humidity"]
                wind = current["windspeedKmph"]
                area = data["nearest_area"][0]["areaName"][0]["value"]
                weather_icons = {"Clear": "☀️", "Sunny": "☀️", "Cloudy": "☁️",
                                 "Rain": "🌧️", "Snow": "❄️", "Thunder": "⛈️",
                                 "Fog": "🌫️", "Partly": "⛅"}
                icon = next((v for k, v in weather_icons.items() if k.lower() in desc.lower()), "🌤️")
                await finish_anim(m,
                    "╔══════════════════════════╗\n"
                    f"║  {icon} <b>WEATHER — {html.escape(area[:12])}</b>  ║\n"
                    "╚══════════════════════════╝\n\n"
                    f"🌡️ <b>Temperature:</b> {temp_c}°C / {temp_f}°F\n"
                    f"🤔 <b>Feels like:</b> {feels}°C\n"
                    f"📋 <b>Condition:</b> {html.escape(desc)}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"💧 <b>Humidity:</b> {humidity}%\n"
                    f"💨 <b>Wind:</b> {wind} km/h"
                )
    except Exception as e:
        await finish_anim(m, f"❌ <b>Weather lookup failed:</b> {html.escape(str(e))}")

async def time_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tz_str = " ".join(context.args) if context.args else "UTC"
    try:
        tz = pytz.timezone(tz_str)
        now = datetime.datetime.now(tz)
        hour = now.hour
        if 5 <= hour < 12: tod = "🌅 Morning"
        elif 12 <= hour < 17: tod = "☀️ Afternoon"
        elif 17 <= hour < 21: tod = "🌇 Evening"
        else: tod = "🌙 Night"
        await reply(update,
            "╔══════════════════════╗\n"
            "║    🕐 <b>CURRENT TIME</b>   ║\n"
            "╚══════════════════════╝\n\n"
            f"📍 <b>Timezone:</b> {html.escape(tz_str)}\n"
            f"🗓️ <b>Date:</b> {now.strftime('%Y-%m-%d')}\n"
            f"⏰ <b>Time:</b> {now.strftime('%H:%M:%S %Z')}\n"
            f"🌞 <b>Period:</b> {tod}"
        )
    except Exception:
        await reply(update, f"❌ <b>Unknown timezone:</b> <code>{html.escape(tz_str)}</code>")

async def reverse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else (
        update.message.reply_to_message.text if update.message.reply_to_message else "")
    if not text:
        return await reply(update, "❓ <b>Usage:</b> <code>/reverse text</code>")
    await reply(update,
        "╔══════════════════════╗\n"
        "║    🔄 <b>REVERSED!</b>    ║\n"
        "╚══════════════════════╝\n\n"
        f"📝 <b>Original:</b> {html.escape(text[:100])}\n"
        f"🔁 <b>Reversed:</b> {html.escape(text[::-1][:100])}"
    )

async def ascii_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/ascii text</code>")
    text = " ".join(context.args)
    result = " ".join(str(ord(c)) for c in text[:20])
    await reply(update,
        "╔══════════════════════╗\n"
        "║    💻 <b>ASCII CODES</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"📝 <b>Text:</b> <code>{html.escape(text[:20])}</code>\n"
        f"🔢 <b>Codes:</b>\n<code>{html.escape(result)}</code>"
    )

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Loading settings")
    cfg = get_chat(update.effective_chat.id)
    if not cfg:
        return await finish_anim(m, "❌ <b>No settings found!</b>")
    def tog(val): return "✅" if val else "❌"
    await finish_anim(m,
        "╔══════════════════════════════╗\n"
        f"║  ⚙️ <b>SETTINGS — {html.escape((update.effective_chat.title or '')[:10])}</b>  ║\n"
        "╚══════════════════════════════╝\n\n"
        f"━━━ <b>PROTECTION</b> ━━━━━━━━━━━━━\n"
        f"{tog(cfg.get('anti_spam'))} Anti-Spam\n"
        f"{tog(cfg.get('anti_flood'))} Anti-Flood ({cfg.get('flood_count', 5)} msgs/{cfg.get('flood_time', 5)}s)\n"
        f"{tog(cfg.get('anti_link'))} Anti-Link\n"
        f"{tog(cfg.get('anti_forward'))} Anti-Forward\n"
        f"{tog(cfg.get('anti_bot'))} Anti-Bot\n"
        f"{tog(cfg.get('anti_raid'))} Anti-Raid\n\n"
        f"━━━ <b>MODERATION</b> ━━━━━━━━━━━\n"
        f"⚠️ Warn limit: <b>{cfg.get('warn_limit', 3)}</b> → <b>{cfg.get('warn_action', 'mute')}</b>\n\n"
        f"━━━ <b>MESSAGES</b> ━━━━━━━━━━━━━\n"
        f"{tog(cfg.get('greetmembers', 1))} Welcome\n"
        f"{tog(cfg.get('goodbye_enabled', 1))} Goodbye\n"
        f"{tog(cfg.get('economy_enabled', 1))} Economy\n"
        f"{tog(cfg.get('rep_enabled', 1))} Reputation"
    )

# ────────────── SETTINGS SHORTCUTS ───────────────────────────────────────────
@admin_only
async def cleanservice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "clean_service", 1 if val else 0)
    icon = "✅" if val else "❌"
    await reply(update, f"{icon} <b>Clean service messages {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def delcommands_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "delete_commands", 1 if val else 0)
    icon = "✅" if val else "❌"
    await reply(update, f"{icon} <b>Delete commands {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def welcdel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/welcdel seconds</code>\n<i>Set to 0 to disable</i>")
    try:
        secs = int(context.args[0])
    except ValueError:
        return await reply(update, "❌ <b>Invalid number.</b>")
    set_setting(update.effective_chat.id, "welcome_delete_after", secs)
    if secs == 0:
        await reply(update, "✅ <b>Welcome auto-delete disabled!</b>")
    else:
        await reply(update, f"✅ <b>Welcome messages will auto-delete after {secs}s!</b>")

# ────────────── SCHEDULE ──────────────────────────────────────────────────────
@admin_only
async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await reply(update,
            "╔══════════════════════╗\n"
            "║  📅 <b>SCHEDULE MSG</b>  ║\n"
            "╚══════════════════════╝\n\n"
            "❓ <b>Usage:</b> <code>/schedule 1h Your message</code>\n\n"
            "⏱️ <b>Durations:</b> 1m, 1h, 1d, 1w"
        )
    time_str = context.args[0]
    message = " ".join(context.args[1:])
    duration = parse_duration(time_str)
    if not duration:
        return await reply(update, "❌ <b>Invalid duration.</b>\n<i>Use: 1m, 1h, 1d</i>")
    next_run = datetime.datetime.now(pytz.utc) + duration
    db = get_db()
    db.execute("INSERT INTO schedules (chat_id, message, next_run, created_by) VALUES (?,?,?,?)",
               (update.effective_chat.id, message, next_run.isoformat(), update.effective_user.id))
    db.commit(); db.close()
    await reply(update,
        "╔══════════════════════╗\n"
        "║  ✅ <b>SCHEDULED!</b>   ║\n"
        "╚══════════════════════╝\n\n"
        f"⏰ <b>In:</b> {html.escape(time_str)}\n"
        f"📅 <b>At:</b> {next_run.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"💬 <b>Message:</b> {html.escape(message[:100])}"
    )

async def run_scheduler(context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    now = datetime.datetime.now(pytz.utc)
    rows = db.execute("SELECT * FROM schedules WHERE is_active=1 AND next_run<=?", (now.isoformat(),)).fetchall()
    for row in rows:
        try:
            await context.bot.send_message(row["chat_id"], row["message"], parse_mode="HTML")
        except: pass
        if row["repeat"] == "none":
            db.execute("UPDATE schedules SET is_active=0 WHERE id=?", (row["id"],))
        else:
            interval = datetime.timedelta(seconds=row["repeat_val"])
            next_run = now + interval
            db.execute("UPDATE schedules SET next_run=? WHERE id=?", (next_run.isoformat(), row["id"]))
    db.commit(); db.close()

# ────────────── INLINE QUERY ─────────────────────────────────────────────────
async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.inline_query.query
    results = []
    if not q:
        results.append(InlineQueryResultArticle(
            id="1",
            title="🤖 UltraGroupManager v7.0",
            description="The most powerful Telegram group manager!",
            input_message_content=InputTextMessageContent(
                f"🤖 <b>UltraGroupManager v{VERSION}</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "✨ Advanced group management • 250+ features\n"
                "🛡️ Moderation • 💰 Economy • 🎮 Fun",
                parse_mode="HTML"
            )
        ))
    else:
        results.append(InlineQueryResultArticle(
            id="q",
            title=f"📢 Share: {q[:50]}",
            description=f"Send this message to the chat",
            input_message_content=InputTextMessageContent(q)
        ))
    await update.inline_query.answer(results, cache_time=5)

# ────────────── BACKUP / RESTORE ─────────────────────────────────────────────
@admin_only
async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Creating backup")
    chat_id = update.effective_chat.id
    db = get_db()
    data = {
        "chat_id": chat_id,
        "version": VERSION,
        "exported_at": datetime.datetime.now(pytz.utc).isoformat(),
        "settings": dict(db.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,)).fetchone() or {}),
        "notes": [dict(r) for r in db.execute("SELECT * FROM notes WHERE chat_id=?", (chat_id,)).fetchall()],
        "filters": [dict(r) for r in db.execute("SELECT * FROM filters WHERE chat_id=?", (chat_id,)).fetchall()],
        "blacklist": [dict(r) for r in db.execute("SELECT * FROM blacklist WHERE chat_id=?", (chat_id,)).fetchall()],
    }
    db.close()
    try:
        await m.delete()
    except: pass
    buf = io.BytesIO(json.dumps(data, indent=2, default=str).encode())
    buf.name = f"backup_{chat_id}.json"
    await update.message.reply_document(buf,
        caption=
            "╔══════════════════════╗\n"
            "║  💾 <b>BACKUP READY!</b>  ║\n"
            "╚══════════════════════╝\n\n"
            f"💬 <b>Chat:</b> {html.escape(update.effective_chat.title or '')}\n"
            f"📝 <b>Notes:</b> {len(data['notes'])}\n"
            f"🔍 <b>Filters:</b> {len(data['filters'])}\n"
            f"🚫 <b>Blacklist:</b> {len(data['blacklist'])}\n"
            f"🕐 <b>Time:</b> {data['exported_at'][:19]}",
        parse_mode="HTML"
    )

# ────────────── LEAVE ─────────────────────────────────────────────────────────
@owner_only
async def leave_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and update.effective_chat.type == "private":
        return await reply(update, "❓ <b>Usage:</b> <code>/leave [chat_id]</code>")
    target_id = int(context.args[0]) if context.args else update.effective_chat.id
    try:
        await context.bot.leave_chat(target_id)
        if target_id != update.effective_chat.id:
            await reply(update, f"✅ <b>Left chat</b> <code>{target_id}</code>")
    except Exception as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

# ────────────── CHATLIST ──────────────────────────────────────────────────────
@owner_only
async def chatlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Fetching chat list")
    db = get_db()
    rows = db.execute("SELECT chat_id, title, chat_type FROM chats ORDER BY title LIMIT 30").fetchall()
    total = db.execute("SELECT COUNT(*) as c FROM chats").fetchone()["c"]
    db.close()
    lines = [
        "╔══════════════════════════════╗\n"
        f"║  💬 <b>CHAT LIST ({total} total)</b>  ║\n"
        "╚══════════════════════════════╝\n"
    ]
    type_icons = {"group": "👥", "supergroup": "🏛️", "channel": "📢", "private": "👤"}
    for r in rows:
        icon = type_icons.get(r["chat_type"], "💬")
        lines.append(f"{icon} {html.escape(r['title'] or 'Unknown')} <code>{r['chat_id']}</code>")
    await finish_anim(m, "\n".join(lines))

# ────────────── HANDLE MEMBER UPDATES ────────────────────────────────────────
async def chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    chat = result.chat
    ensure_chat(chat)
    # Track new members when they join
    if result.new_chat_member and result.new_chat_member.status in ("member", "administrator", "creator"):
        user = result.new_chat_member.user
        ensure_user(user)
        track_member(chat.id, user)

# ────────────── MAIN MESSAGE HANDLER ─────────────────────────────────────────
async def main_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user or not update.effective_chat: return
    if update.effective_chat.type == "private": return

    user = update.effective_user
    chat = update.effective_chat
    ensure_chat(chat)
    ensure_user(user)
    track_member(chat.id, user)  # Persistent member tracking — survives restarts!

    reason = is_gbanned(user.id)
    if reason:
        try:
            await context.bot.ban_chat_member(chat.id, user.id)
            await context.bot.send_message(chat.id,
                f"🌍 <b>Globally banned user removed!</b>\n"
                f"📝 Reason: {html.escape(reason)}",
                parse_mode="HTML")
            return
        except: pass

    await afk_check_handler(update, context)
    await antispam_handler(update, context)
    await blacklist_handler(update, context)
    await filter_handler(update, context)
    await hash_note_handler(update, context)

    if update.message.text and ("@admins" in update.message.text.lower() or "@admin" in update.message.text.lower()):
        await tag_admins_handler(update, context)

    if update.message.text and update.message.text.strip() in ("+rep", "+1") and update.message.reply_to_message:
        await rep_cmd(update, context)

    if cfg := get_chat(chat.id):
        if cfg.get("delete_commands") and update.message.text and update.message.text.startswith("/"):
            try: await update.message.delete()
            except: pass

# ────────────── PARSE DURATION ───────────────────────────────────────────────
def parse_duration(s: str) -> Optional[datetime.timedelta]:
    s = s.lower().strip()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    match = re.match(r"^(\d+)([smhdw]?)$", s)
    if not match: return None
    value, unit = int(match.group(1)), match.group(2) or "s"
    return datetime.timedelta(seconds=value * units.get(unit, 1))

# ═══════════════════════════════════════════════════════════════════════════════
#                          BOT SETUP & RUN
# ═══════════════════════════════════════════════════════════════════════════════
def build_commands():
    return [
        BotCommand("start", "🤖 Start the bot"),
        BotCommand("help", "📖 Show help menu"),
        BotCommand("ban", "🔨 Ban a user"),
        BotCommand("tban", "⏱️ Temp ban a user"),
        BotCommand("sban", "🔇 Silent ban"),
        BotCommand("unban", "🔓 Unban a user"),
        BotCommand("kick", "👢 Kick a user"),
        BotCommand("skick", "🤫 Silent kick"),
        BotCommand("mute", "🔇 Mute a user"),
        BotCommand("tmute", "⏱️ Temp mute"),
        BotCommand("unmute", "🔊 Unmute a user"),
        BotCommand("warn", "⚠️ Warn a user"),
        BotCommand("dwarn", "⚠️ Warn and delete message"),
        BotCommand("swarn", "⚠️ Silent warn"),
        BotCommand("unwarn", "✅ Remove a warn"),
        BotCommand("resetwarn", "🗑️ Reset all warns"),
        BotCommand("warns", "📋 Show warns"),
        BotCommand("promote", "⬆️ Promote a user"),
        BotCommand("demote", "⬇️ Demote a user"),
        BotCommand("admintitle", "🏷️ Set admin title"),
        BotCommand("adminlist", "👮 List all admins"),
        BotCommand("zombies", "🧟 Count zombie accounts"),
        BotCommand("kickzombies", "💥 Kick zombie accounts"),
        BotCommand("pin", "📌 Pin a message"),
        BotCommand("unpin", "📌 Unpin a message"),
        BotCommand("unpinall", "📌 Unpin all messages"),
        BotCommand("purge", "🗑️ Purge messages"),
        BotCommand("del", "🗑️ Delete a message"),
        BotCommand("lock", "🔒 Lock a message type"),
        BotCommand("unlock", "🔓 Unlock a message type"),
        BotCommand("locks", "🔒 Show lock status"),
        BotCommand("antispam", "🛡️ Toggle anti-spam"),
        BotCommand("antiflood", "🌊 Toggle anti-flood"),
        BotCommand("setflood", "⚙️ Set flood limit"),
        BotCommand("antilink", "🔗 Toggle anti-link"),
        BotCommand("antiforward", "📨 Toggle anti-forward"),
        BotCommand("antibot", "🤖 Toggle anti-bot"),
        BotCommand("antiraid", "🚨 Toggle anti-raid"),
        BotCommand("setwelcome", "👋 Set welcome message"),
        BotCommand("setgoodbye", "👋 Set goodbye message"),
        BotCommand("welcome", "👋 Toggle welcome"),
        BotCommand("goodbye", "👋 Toggle goodbye"),
        BotCommand("setrules", "📜 Set rules"),
        BotCommand("rules", "📜 Show rules"),
        BotCommand("save", "💾 Save a note"),
        BotCommand("get", "📝 Get a note"),
        BotCommand("notes", "📋 List all notes"),
        BotCommand("clear", "🗑️ Delete a note"),
        BotCommand("filter", "🔍 Add a filter"),
        BotCommand("filters", "📋 List filters"),
        BotCommand("stop", "🛑 Remove a filter"),
        BotCommand("addbl", "🚫 Add to blacklist"),
        BotCommand("unblacklist", "✅ Remove from blacklist"),
        BotCommand("blacklist", "📋 Show blacklist"),
        BotCommand("report", "🚨 Report a message"),
        BotCommand("afk", "😴 Set AFK status"),
        BotCommand("gban", "🌍 Global ban"),
        BotCommand("ungban", "✅ Remove global ban"),
        BotCommand("broadcast", "📢 Broadcast to chats"),
        BotCommand("broadcastall", "📢 Broadcast to all members"),
        BotCommand("stats", "📊 Bot statistics"),
        BotCommand("id", "🆔 Get user/chat ID"),
        BotCommand("info", "👤 Get user info"),
        BotCommand("chatinfo", "💬 Get chat info"),
        BotCommand("ping", "🏓 Ping the bot"),
        BotCommand("uptime", "⏱️ Show uptime"),
        BotCommand("settings", "⚙️ View settings"),
        BotCommand("daily", "💰 Claim daily coins"),
        BotCommand("coins", "💳 Check balance"),
        BotCommand("mine", "⛏️ Mine coins"),
        BotCommand("give", "💸 Transfer coins"),
        BotCommand("rob", "🦹 Rob coins"),
        BotCommand("flip", "🪙 Flip a coin"),
        BotCommand("slots", "🎰 Slot machine"),
        BotCommand("leaderboard", "🏆 Coins leaderboard"),
        BotCommand("rep", "⭐ Give reputation"),
        BotCommand("reprank", "📊 Rep leaderboard"),
        BotCommand("newfed", "🌐 Create federation"),
        BotCommand("joinfed", "🌐 Join a federation"),
        BotCommand("leavefed", "🌐 Leave federation"),
        BotCommand("fban", "🚫 Federation ban"),
        BotCommand("unfban", "✅ Federation unban"),
        BotCommand("fedinfo", "ℹ️ Federation info"),
        BotCommand("fedbans", "📋 List federation bans"),
        BotCommand("connect", "🔗 Connect to a group"),
        BotCommand("disconnect", "🔌 Disconnect from group"),
        BotCommand("connected", "📡 Show connection"),
        BotCommand("calc", "🧮 Calculator"),
        BotCommand("qr", "📱 Generate QR code"),
        BotCommand("tr", "🌐 Translate text"),
        BotCommand("hash", "🔐 Hash text"),
        BotCommand("b64", "🔢 Base64 encode/decode"),
        BotCommand("weather", "🌤️ Check weather"),
        BotCommand("time", "🕐 Current time"),
        BotCommand("reverse", "🔄 Reverse text"),
        BotCommand("8ball", "🎱 Magic 8-ball"),
        BotCommand("roll", "🎲 Roll a dice"),
        BotCommand("slap", "👋 Slap a user"),
        BotCommand("hug", "🤗 Hug a user"),
        BotCommand("ship", "💕 Ship compatibility"),
        BotCommand("roast", "🔥 Roast a user"),
        BotCommand("compliment", "💐 Compliment a user"),
        BotCommand("joke", "😂 Random joke"),
        BotCommand("truth", "💭 Truth question"),
        BotCommand("dare", "😈 Dare challenge"),
        BotCommand("schedule", "📅 Schedule a message"),
        BotCommand("backup", "💾 Export chat backup"),
        BotCommand("setwarnlimit", "⚙️ Set warn limit"),
        BotCommand("setwarnaction", "⚙️ Set warn action"),
        BotCommand("cleanservice", "🧹 Toggle clean service msgs"),
        BotCommand("delcommands", "🗑️ Toggle delete commands"),
        BotCommand("welcdel", "⏱️ Set welcome delete time"),
        BotCommand("chatlist", "💬 List all chats"),
        BotCommand("sudo", "👑 Add sudo user"),
        BotCommand("unsudo", "👤 Remove sudo user"),
        BotCommand("leave", "🚪 Leave a chat"),
        BotCommand("ascii", "💻 Text to ASCII codes"),
        BotCommand("setfloodaction", "⚙️ Set flood action"),
        BotCommand("setraid", "🚨 Set raid threshold"),
        BotCommand("cas", "🛡️ CAS protection"),
        BotCommand("blacklistmode", "⚙️ Set blacklist action"),
        BotCommand("stopall", "🛑 Remove all filters"),
    ][:100]  # Telegram limit is 100 commands

async def post_init(application: Application):
    try:
        await application.bot.set_my_commands(build_commands())
        info = await application.bot.get_me()
        logger.info(f"✅ {info.first_name} (@{info.username}) initialized — v{VERSION}")
        # Restore connection cache from DB on startup
        db = get_db()
        connections = db.execute("SELECT user_id, chat_id FROM connections").fetchall()
        db.close()
        for conn in connections:
            connection_cache[conn["user_id"]] = conn["chat_id"]
        logger.info(f"✅ Restored {len(connections)} cached connections from DB")
        # Restore AFK cache from DB
        db = get_db()
        afk_users = db.execute("SELECT user_id, afk_reason, afk_since FROM users WHERE is_afk=1").fetchall()
        db.close()
        for u in afk_users:
            try:
                since = datetime.datetime.fromisoformat(str(u["afk_since"]).replace(" ", "T")).replace(tzinfo=pytz.utc)
            except:
                since = datetime.datetime.now(pytz.utc)
            afk_cache[u["user_id"]] = {"reason": u["afk_reason"] or "", "since": since}
        logger.info(f"✅ Restored {len(afk_users)} AFK statuses from DB")
    except Exception as e:
        logger.error(f"Post-init error: {e}")

def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set! Set it in your environment secrets.")
        sys.exit(1)

    init_db()
    logger.info(f"🚀 Starting UltraGroupManager {VERSION}")

    app = (Application.builder()
           .token(BOT_TOKEN)
           .post_init(post_init)
           .build())

    # ── Handlers ──────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))

    # Moderation
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("tban", tban_cmd))
    app.add_handler(CommandHandler("sban", sban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    app.add_handler(CommandHandler("skick", skick_cmd))
    app.add_handler(CommandHandler("mute", mute_cmd))
    app.add_handler(CommandHandler("tmute", tmute_cmd))
    app.add_handler(CommandHandler("unmute", unmute_cmd))
    app.add_handler(CommandHandler("warn", warn_cmd))
    app.add_handler(CommandHandler("dwarn", dwarn_cmd))
    app.add_handler(CommandHandler("swarn", swarn_cmd))
    app.add_handler(CommandHandler("unwarn", unwarn_cmd))
    app.add_handler(CommandHandler("resetwarn", resetwarn_cmd))
    app.add_handler(CommandHandler("warns", warns_cmd))
    app.add_handler(CommandHandler("promote", promote_cmd))
    app.add_handler(CommandHandler("demote", demote_cmd))
    app.add_handler(CommandHandler("admintitle", admintitle_cmd))
    app.add_handler(CommandHandler("adminlist", adminlist_cmd))
    app.add_handler(CommandHandler("zombies", zombies_cmd))
    app.add_handler(CommandHandler("kickzombies", kickzombies_cmd))
    app.add_handler(CommandHandler("pin", pin_cmd))
    app.add_handler(CommandHandler("unpin", unpin_cmd))
    app.add_handler(CommandHandler("unpinall", unpinall_cmd))
    app.add_handler(CommandHandler("purge", purge_cmd))
    app.add_handler(CommandHandler("del", del_cmd))

    # Locks
    app.add_handler(CommandHandler("lock", lock_cmd))
    app.add_handler(CommandHandler("unlock", unlock_cmd))
    app.add_handler(CommandHandler("locks", locks_cmd))

    # Anti-spam settings
    app.add_handler(CommandHandler("antispam", antispam_cmd))
    app.add_handler(CommandHandler("antiflood", antiflood_cmd))
    app.add_handler(CommandHandler("setflood", setflood_cmd))
    app.add_handler(CommandHandler("setfloodaction", setfloodaction_cmd))
    app.add_handler(CommandHandler("antilink", antilink_cmd))
    app.add_handler(CommandHandler("antiforward", antiforward_cmd))
    app.add_handler(CommandHandler("antibot", antibot_cmd))
    app.add_handler(CommandHandler("antiraid", antiraid_cmd))
    app.add_handler(CommandHandler("setraid", setraid_cmd))
    app.add_handler(CommandHandler("cas", cas_cmd))
    app.add_handler(CommandHandler("setwarnlimit", setwarnlimit_cmd))
    app.add_handler(CommandHandler("setwarnaction", setwarnaction_cmd))
    app.add_handler(CommandHandler("cleanservice", cleanservice_cmd))
    app.add_handler(CommandHandler("delcommands", delcommands_cmd))
    app.add_handler(CommandHandler("welcdel", welcdel_cmd))

    # Welcome/Goodbye/Rules
    app.add_handler(CommandHandler("setwelcome", setwelcome_cmd))
    app.add_handler(CommandHandler("setgoodbye", setgoodbye_cmd))
    app.add_handler(CommandHandler("welcome", welcome_toggle_cmd))
    app.add_handler(CommandHandler("goodbye", goodbye_toggle_cmd))
    app.add_handler(CommandHandler("setrules", setrules_cmd))
    app.add_handler(CommandHandler("rules", rules_cmd))

    # Notes
    app.add_handler(CommandHandler("save", save_cmd))
    app.add_handler(CommandHandler("get", get_note_cmd))
    app.add_handler(CommandHandler("notes", notes_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(CommandHandler("clearall", clearall_cmd))

    # Filters/Blacklist
    app.add_handler(CommandHandler("filter", filter_cmd))
    app.add_handler(CommandHandler("filters", filters_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("stopall", stopall_cmd))
    app.add_handler(CommandHandler("addbl", addbl_cmd))
    app.add_handler(CommandHandler(["unblacklist", "rmbl"], unblacklist_cmd))
    app.add_handler(CommandHandler("blacklist", blacklist_cmd))
    app.add_handler(CommandHandler("blacklistmode", blacklistmode_cmd))

    # Report
    app.add_handler(CommandHandler("report", report_cmd))

    # AFK
    app.add_handler(CommandHandler("afk", afk_cmd))

    # Federation
    app.add_handler(CommandHandler("newfed", newfed_cmd))
    app.add_handler(CommandHandler("joinfed", joinfed_cmd))
    app.add_handler(CommandHandler("leavefed", leavefed_cmd))
    app.add_handler(CommandHandler("fedinfo", fedinfo_cmd))
    app.add_handler(CommandHandler("fban", fban_cmd))
    app.add_handler(CommandHandler("unfban", unfban_cmd))
    app.add_handler(CommandHandler("fedbans", fedbans_cmd))

    # Connection
    app.add_handler(CommandHandler("connect", connect_cmd))
    app.add_handler(CommandHandler("disconnect", disconnect_cmd))
    app.add_handler(CommandHandler("connected", connected_cmd))

    # Global ban / sudo
    app.add_handler(CommandHandler("gban", gban_cmd))
    app.add_handler(CommandHandler("ungban", ungban_cmd))
    app.add_handler(CommandHandler("sudo", sudo_cmd))
    app.add_handler(CommandHandler("unsudo", unsudo_cmd))

    # Info / utility
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("id", id_cmd))
    app.add_handler(CommandHandler("info", info_cmd))
    app.add_handler(CommandHandler("chatinfo", chatinfo_cmd))
    app.add_handler(CommandHandler("ping", ping_cmd))
    app.add_handler(CommandHandler("uptime", uptime_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("chatlist", chatlist_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("broadcastall", broadcastall_cmd))
    app.add_handler(CommandHandler("backup", backup_cmd))
    app.add_handler(CommandHandler("leave", leave_cmd))
    app.add_handler(CommandHandler("schedule", schedule_cmd))

    # Economy
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler(["coins", "balance"], coins_cmd))
    app.add_handler(CommandHandler("mine", mine_cmd))
    app.add_handler(CommandHandler("give", give_cmd))
    app.add_handler(CommandHandler("rob", rob_cmd))
    app.add_handler(CommandHandler(["flip", "coinflip"], flip_cmd))
    app.add_handler(CommandHandler("slots", slots_cmd))
    app.add_handler(CommandHandler("leaderboard", leaderboard_cmd))

    # Reputation
    app.add_handler(CommandHandler("rep", rep_cmd))
    app.add_handler(CommandHandler("reprank", reprank_cmd))

    # Fun
    app.add_handler(CommandHandler("8ball", eightball_cmd))
    app.add_handler(CommandHandler("roll", roll_cmd))
    app.add_handler(CommandHandler("slap", slap_cmd))
    app.add_handler(CommandHandler("hug", hug_cmd))
    app.add_handler(CommandHandler("ship", ship_cmd))
    app.add_handler(CommandHandler("roast", roast_cmd))
    app.add_handler(CommandHandler("compliment", compliment_cmd))
    app.add_handler(CommandHandler("joke", joke_cmd))
    app.add_handler(CommandHandler("truth", truth_cmd))
    app.add_handler(CommandHandler("dare", dare_cmd))

    # Utility
    app.add_handler(CommandHandler("calc", calc_cmd))
    app.add_handler(CommandHandler("qr", qr_cmd))
    app.add_handler(CommandHandler(["tr", "translate"], translate_cmd))
    app.add_handler(CommandHandler("hash", hash_cmd))
    app.add_handler(CommandHandler("b64", b64_cmd))
    app.add_handler(CommandHandler("weather", weather_cmd))
    app.add_handler(CommandHandler("time", time_cmd))
    app.add_handler(CommandHandler("reverse", reverse_cmd))
    app.add_handler(CommandHandler("ascii", ascii_cmd))

    # Message handlers
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND & filters.ChatType.GROUPS, main_message_handler))
    app.add_handler(ChatMemberHandler(chat_member_handler))

    # Callbacks
    app.add_handler(CallbackQueryHandler(help_callback, pattern="^help_"))
    app.add_handler(CallbackQueryHandler(report_callback, pattern="^report_"))

    # Inline
    app.add_handler(InlineQueryHandler(inline_query_handler))

    # Job queue — scheduler
    jq = app.job_queue
    if jq:
        jq.run_repeating(run_scheduler, interval=60, first=10)
        logger.info("✅ Job queue initialized")

    logger.info("🚀 Bot is running! Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
