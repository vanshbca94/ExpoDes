#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║         ULTRA ADVANCED TELEGRAM GROUP & CHANNEL MANAGER BOT v6.0           ║
║      Beyond MissRose • All-in-One • Single File • Python • 250+ features   ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os, sys, re, json, time, math, random, string, asyncio, sqlite3, logging
import hashlib, textwrap, datetime, calendar, html, urllib.parse, uuid
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
VERSION     = "6.0.0-ULTRA"
START_TIME  = datetime.datetime.now(pytz.utc)

# ─── In-Memory Caches ────────────────────────────────────────────────────────
flood_cache:      Dict[int, deque]   = defaultdict(lambda: deque(maxlen=50))
spam_cache:       Dict[int, List]    = defaultdict(list)
afk_cache:        Dict[int, dict]    = {}
raid_tracker:     Dict[int, deque]   = defaultdict(lambda: deque(maxlen=50))
msg_hashes:       Dict[int, deque]   = defaultdict(lambda: deque(maxlen=30))
connection_cache: Dict[int, int]     = {}   # user_id -> chat_id
warn_cd:          Dict[Tuple, float] = {}

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
    db.execute("""INSERT OR IGNORE INTO chats (chat_id, title, chat_type) VALUES (?,?,?)""",
               (chat.id, chat.title or "", chat.type))
    db.execute("UPDATE chats SET title=?, updated_at=CURRENT_TIMESTAMP WHERE chat_id=?",
               (chat.title or "", chat.id))
    db.commit(); db.close()

def ensure_user(user: User):
    db = get_db()
    db.execute("""INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
                  VALUES (?,?,?,?)""",
               (user.id, user.username or "", user.first_name or "", user.last_name or ""))
    db.execute("""UPDATE users SET username=?, first_name=?, last_name=?, last_seen=CURRENT_TIMESTAMP
                  WHERE user_id=?""",
               (user.username or "", user.first_name or "", user.last_name or "", user.id))
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

# ─── Decorators ──────────────────────────────────────────────────────────────
def admin_only(fn):
    from functools import wraps
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.effective_chat: return
        if update.effective_chat.type == "private": return await fn(update, context)
        if not await is_admin(context, update.effective_chat.id, update.effective_user.id):
            await update.message.reply_text("❌ Admins only.")
            return
        return await fn(update, context)
    return wrapper

def owner_only(fn):
    from functools import wraps
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user: return
        if update.effective_user.id not in OWNER_IDS and not is_sudo(update.effective_user.id):
            await update.message.reply_text("❌ Owner only command.")
            return
        return await fn(update, context)
    return wrapper

def groups_only(fn):
    from functools import wraps
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat and update.effective_chat.type == "private":
            await update.message.reply_text("❌ This command works in groups only.")
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

def user_link(user: User) -> str:
    name = html.escape(user.first_name or str(user.id))
    return f'<a href="tg://user?id={user.id}">{name}</a>'

def get_target(update: Update, context) -> Optional[User]:
    msg = update.message
    if msg.reply_to_message:
        return msg.reply_to_message.from_user
    if context.args:
        arg = context.args[0].lstrip("@")
        if arg.isdigit():
            return type("FakeUser", (), {"id": int(arg), "first_name": arg, "username": None, "last_name": None, "mention_html": lambda self=None: f"<code>{arg}</code>", "is_bot": False})()
    return None

def get_reason(context, start=1) -> str:
    return " ".join(context.args[start:]) if context.args and len(context.args) > start else ""

# ═══════════════════════════════════════════════════════════════════════════════
#                          COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

# ────────────── START / HELP ──────────────────────────────────────────────────
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await reply(update, "👋 I'm alive! Use /help to see what I can do.")
        return
    text = (
        f"<b>🤖 UltraGroupManager v{VERSION}</b>\n\n"
        "I'm an advanced all-in-one Telegram group manager that surpasses the competition.\n\n"
        "<b>Key Features:</b>\n"
        "• Advanced moderation (ban/mute/kick/warn/restrict)\n"
        "• Anti-spam, anti-flood, anti-raid protection\n"
        "• Notes, filters, blacklist system\n"
        "• Federation system (ban across groups)\n"
        "• Connection system (manage groups from PM)\n"
        "• Welcome/goodbye with custom buttons\n"
        "• Economy & reputation system\n"
        "• Admin tag, zombie purge, and 250+ features\n\n"
        "Add me to your group as admin to get started!\n"
        "Use /help for full command list."
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📖 Help", callback_data="help_main"),
        InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{context.bot.username}?startgroup=true"),
    ]])
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)

HELP_SECTIONS = {
    "help_main": (
        "📋 <b>Help Menu</b>\n\nChoose a category:",
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
        "🛡️ <b>Moderation Commands</b>\n\n"
        "<code>/ban [reply/@user] [reason]</code> — Ban\n"
        "<code>/tban [reply/@user] 1h [reason]</code> — Temp ban\n"
        "<code>/sban [reply/@user]</code> — Silent ban\n"
        "<code>/unban [reply/@user]</code> — Unban\n"
        "<code>/kick [reply/@user]</code> — Kick\n"
        "<code>/skick [reply/@user]</code> — Silent kick\n"
        "<code>/mute [reply/@user] [reason]</code> — Mute\n"
        "<code>/tmute [reply/@user] 1h [reason]</code> — Temp mute\n"
        "<code>/unmute [reply/@user]</code> — Unmute\n"
        "<code>/warn [reply/@user] [reason]</code> — Warn\n"
        "<code>/dwarn [reply/@user] [reason]</code> — Warn+delete msg\n"
        "<code>/swarn [reply/@user] [reason]</code> — Warn silently\n"
        "<code>/unwarn [reply/@user]</code> — Remove 1 warn\n"
        "<code>/resetwarn [reply/@user]</code> — Reset all warns\n"
        "<code>/warns [reply/@user]</code> — View warns\n"
        "<code>/promote [reply/@user] [title]</code> — Promote\n"
        "<code>/demote [reply/@user]</code> — Demote\n"
        "<code>/admintitle [reply/@user] [title]</code> — Set title\n"
        "<code>/pin / /unpin / /unpinall</code> — Pin messages\n"
        "<code>/purge [N]</code> — Purge messages\n"
        "<code>/del</code> — Delete replied message\n"
        "<code>/kick</code>+reply — Kick user\n"
        "<code>/zombies</code> — Count deleted accounts\n"
        "<code>/kickzombies</code> — Kick deleted accounts\n"
        "<code>@admins</code> — Tag all admins\n"
        "<code>/adminlist</code> — List admins",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_antispam": (
        "🚫 <b>Anti-Spam / Protection</b>\n\n"
        "<code>/antispam on|off</code> — Toggle anti-spam\n"
        "<code>/antiflood on|off</code> — Toggle anti-flood\n"
        "<code>/setflood N [time]</code> — Set flood limit\n"
        "<code>/setfloodaction mute|ban|kick</code> — Flood action\n"
        "<code>/antilink on|off</code> — Block links\n"
        "<code>/antiforward on|off</code> — Block forwards\n"
        "<code>/antibot on|off</code> — Block bots joining\n"
        "<code>/antiraid on|off</code> — Anti-raid mode\n"
        "<code>/raidmode on|off</code> — Toggle raid lockdown\n"
        "<code>/setraid N</code> — Raid threshold\n"
        "<code>/cas on|off</code> — CAS protection\n"
        "<code>/restrict on|off</code> — Restrict new members\n",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_notes": (
        "📝 <b>Notes</b>\n\n"
        "<code>/save name text</code> — Save a note\n"
        "<code>/get name</code> or <code>#name</code> — Get note\n"
        "<code>/notes</code> — List all notes\n"
        "<code>/clear name</code> — Delete a note\n"
        "<code>/clearall</code> — Delete all notes\n"
        "<code>/pmnote name</code> — Send note in PM\n\n"
        "<b>Formatting:</b> HTML, markdown, buttons\n"
        "Button syntax: <code>[text](buttonurl://url)</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_filters": (
        "🔍 <b>Filters (Auto-Respond)</b>\n\n"
        "<code>/filter keyword reply</code> — Add filter\n"
        "<code>/filters</code> — List all filters\n"
        "<code>/stop keyword</code> — Remove filter\n"
        "<code>/stopall</code> — Remove all filters\n"
        "<code>/filter regex:pattern reply</code> — Regex filter\n\n"
        "<b>Blacklist:</b>\n"
        "<code>/addbl word</code> — Add to blacklist\n"
        "<code>/unblacklist word</code> — Remove from blacklist\n"
        "<code>/blacklist</code> — View blacklist\n"
        "<code>/blacklistmode delete|warn|mute|ban</code> — Set action",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_locks": (
        "🔒 <b>Locks</b>\n\n"
        "<code>/lock stickers|gifs|media|polls|voice|video|doc|forward|games|inline|url|all</code>\n"
        "<code>/unlock ...</code> — Unlock\n"
        "<code>/locks</code> — View lock status\n"
        "<code>/locktypes</code> — Available lock types",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_welcome": (
        "👋 <b>Welcome/Goodbye</b>\n\n"
        "<code>/setwelcome text</code> — Set welcome message\n"
        "<code>/setgoodbye text</code> — Set goodbye message\n"
        "<code>/welcome</code> — Preview welcome\n"
        "<code>/cleanwelcome on|off</code> — Delete old welcomes\n"
        "<code>/welcdel N</code> — Auto-delete after N secs\n"
        "<code>/welcome on|off</code> — Toggle welcome\n"
        "<code>/goodbye on|off</code> — Toggle goodbye\n"
        "<code>/setrules text</code> — Set rules\n"
        "<code>/rules</code> — Show rules\n\n"
        "<b>Placeholders:</b> {first} {last} {username} {mention} {count} {chatname}",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_fed": (
        "🌐 <b>Federation System</b>\n\n"
        "<code>/newfed name</code> — Create federation\n"
        "<code>/delfed fed_id</code> — Delete federation\n"
        "<code>/joinfed fed_id</code> — Join a federation\n"
        "<code>/leavefed</code> — Leave current federation\n"
        "<code>/fedinfo [fed_id]</code> — Federation info\n"
        "<code>/fban user [reason]</code> — Federation ban\n"
        "<code>/unfban user</code> — Remove federation ban\n"
        "<code>/fedmembers</code> — List federation chats\n"
        "<code>/fadmin user</code> — Add federation admin\n"
        "<code>/fremove user</code> — Remove federation admin\n"
        "<code>/fedbans [fed_id]</code> — List federation bans",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_connect": (
        "🔗 <b>Connection System</b>\n\n"
        "Manage groups from your private messages!\n\n"
        "<code>/connect chat_id</code> — Connect to a group\n"
        "<code>/disconnect</code> — Disconnect\n"
        "<code>/connected</code> — Check connection\n\n"
        "Once connected, you can use admin commands from PM.",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_economy": (
        "💰 <b>Economy</b>\n\n"
        "<code>/daily</code> — Claim daily coins\n"
        "<code>/coins [@user]</code> — Check balance\n"
        "<code>/mine</code> — Mine coins\n"
        "<code>/give @user amount</code> — Transfer coins\n"
        "<code>/rob @user</code> — Steal coins\n"
        "<code>/flip amount</code> — Coin flip\n"
        "<code>/slots amount</code> — Slot machine\n"
        "<code>/leaderboard</code> — Top balances\n"
        "<code>/shop</code> — View shop items",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_rep": (
        "⭐ <b>Reputation</b>\n\n"
        "<code>+rep</code> / <code>/rep @user</code> — Give reputation\n"
        "<code>/reprank</code> — Rep leaderboard\n"
        "<code>/checkrep [@user]</code> — Check reputation",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_fun": (
        "🎮 <b>Fun Commands</b>\n\n"
        "<code>/8ball question</code> — Magic 8-ball\n"
        "<code>/roll [sides]</code> — Roll dice\n"
        "<code>/flip</code> — Coin flip\n"
        "<code>/slap @user</code> — Slap someone\n"
        "<code>/hug @user</code> — Hug someone\n"
        "<code>/ship @user1 @user2</code> — Ship them\n"
        "<code>/roast @user</code> — Roast someone\n"
        "<code>/compliment @user</code> — Compliment someone\n"
        "<code>/joke</code> — Random joke\n"
        "<code>/meme</code> — Random meme text\n"
        "<code>/trivia</code> — Trivia question\n"
        "<code>/ttt</code> — Tic-tac-toe\n"
        "<code>/truth / /dare</code> — Truth or dare",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_util": (
        "🔧 <b>Utility</b>\n\n"
        "<code>/calc expr</code> — Calculator\n"
        "<code>/qr text</code> — QR code\n"
        "<code>/tr lang text</code> — Translate\n"
        "<code>/hash text</code> — MD5/SHA hash\n"
        "<code>/b64 encode|decode text</code> — Base64\n"
        "<code>/id [@user]</code> — Get user/chat ID\n"
        "<code>/info [@user]</code> — User info\n"
        "<code>/chatinfo</code> — Chat info\n"
        "<code>/ping</code> — Bot ping\n"
        "<code>/uptime</code> — Bot uptime\n"
        "<code>/weather city</code> — Weather\n"
        "<code>/time [timezone]</code> — Current time\n"
        "<code>/shorten url</code> — Shorten URL\n"
        "<code>/paste text</code> — Paste to hastebin\n"
        "<code>/ascii text</code> — ASCII art\n"
        "<code>/reverse text</code> — Reverse text",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_settings": (
        "⚙️ <b>Settings</b>\n\n"
        "<code>/setlang lang</code> — Set language\n"
        "<code>/setwarnlimit N</code> — Warn limit\n"
        "<code>/setwarnaction mute|ban|kick</code> — Warn action\n"
        "<code>/setmuteaction N</code> — Mute duration (secs)\n"
        "<code>/setblacklistaction delete|warn|mute|ban</code>\n"
        "<code>/delcommands on|off</code> — Delete commands\n"
        "<code>/cleanservice on|off</code> — Clean service messages\n"
        "<code>/settings</code> — View current settings",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_admin": (
        "👑 <b>Admin / Owner Commands</b>\n\n"
        "<code>/gban user [reason]</code> — Global ban\n"
        "<code>/ungban user</code> — Remove global ban\n"
        "<code>/broadcast msg</code> — Broadcast to all chats\n"
        "<code>/sudo user</code> — Add sudo user\n"
        "<code>/unsudo user</code> — Remove sudo user\n"
        "<code>/stats</code> — Bot statistics\n"
        "<code>/chatlist</code> — List all chats\n"
        "<code>/backup</code> — Export chat backup\n"
        "<code>/restore</code> — Restore from backup\n"
        "<code>/leave</code> — Leave chat\n"
        "<code>/update</code> — Update bot",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
}

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, buttons = HELP_SECTIONS["help_main"]
    if update.effective_chat.type != "private":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("📖 Open Help in PM", url=f"https://t.me/{context.bot.username}?start=help")]])
        await reply(update, "Help sent to your PM!", reply_markup=kb)
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
        return await reply(update, "❌ You don't have restrict rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user or provide a username.")
    reason = get_reason(context, 1 if update.message.reply_to_message else 1)
    if update.message.reply_to_message:
        reason = " ".join(context.args) if context.args else ""
    chat = update.effective_chat
    try:
        await _do_ban(context, chat.id, target.id)
        db = get_db()
        db.execute("INSERT OR REPLACE INTO bans (chat_id, user_id, banned_by, reason) VALUES (?,?,?,?)",
                   (chat.id, target.id, update.effective_user.id, reason))
        db.commit(); db.close()
        log_action(chat.id, update.effective_user.id, "ban", target.id, reason)
        await reply(update, f"🚫 <b>Banned:</b> {user_link(target)}\n📝 Reason: {html.escape(reason or 'None')}")
        await send_log(context, chat.id, f"🚫 BAN\nChat: {html.escape(chat.title)}\nAdmin: {user_link(update.effective_user)}\nUser: {user_link(target)}\nReason: {html.escape(reason or 'None')}")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

@admin_only
@groups_only
async def tban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have restrict rights.")
    if not context.args: return await reply(update, "Usage: /tban @user 1h [reason]")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Provide a user.")
    time_arg = context.args[0] if update.message.reply_to_message else (context.args[1] if len(context.args) > 1 else "1h")
    duration = parse_duration(time_arg)
    if not duration: return await reply(update, "❌ Invalid duration. Use: 1m, 1h, 1d, 1w")
    until = datetime.datetime.now(pytz.utc) + duration
    try:
        await _do_ban(context, update.effective_chat.id, target.id, until)
        log_action(update.effective_chat.id, update.effective_user.id, "tban", target.id, f"{time_arg}")
        await reply(update, f"⏱️ Temp banned {user_link(target)} for <b>{time_arg}</b>")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

@admin_only
@groups_only
async def sban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have restrict rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
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
        return await reply(update, "❌ You don't have restrict rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user or provide username.")
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id, only_if_banned=True)
        db = get_db()
        db.execute("DELETE FROM bans WHERE chat_id=? AND user_id=?", (update.effective_chat.id, target.id))
        db.commit(); db.close()
        log_action(update.effective_chat.id, update.effective_user.id, "unban", target.id)
        await reply(update, f"✅ Unbanned {user_link(target)}")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

@admin_only
@groups_only
async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have restrict rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        log_action(update.effective_chat.id, update.effective_user.id, "kick", target.id)
        await reply(update, f"👢 Kicked {user_link(target)}")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

@admin_only
@groups_only
async def skick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have restrict rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    try:
        await update.message.delete()
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
    except:
        pass

MUTE_PERMS = ChatPermissions(can_send_messages=False, can_send_media_messages=False,
                             can_send_polls=False, can_send_other_messages=False)
UNMUTE_PERMS = ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                               can_send_polls=True, can_send_other_messages=True,
                               can_add_web_page_previews=True)

@admin_only
@groups_only
async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have restrict rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    reason = " ".join(context.args) if context.args and not update.message.reply_to_message else get_reason(context)
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS)
        log_action(update.effective_chat.id, update.effective_user.id, "mute", target.id, reason)
        await reply(update, f"🔇 Muted {user_link(target)}\nReason: {html.escape(reason or 'None')}")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

@admin_only
@groups_only
async def tmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have restrict rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user or provide username.")
    time_str = (context.args[1] if update.message.reply_to_message and len(context.args) > 0 else
                (context.args[1] if len(context.args) > 1 else "1h"))
    duration = parse_duration(time_str)
    if not duration: return await reply(update, "❌ Invalid duration.")
    until = datetime.datetime.now(pytz.utc) + duration
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS, until_date=until)
        log_action(update.effective_chat.id, update.effective_user.id, "tmute", target.id, time_str)
        await reply(update, f"🔇 Muted {user_link(target)} for <b>{time_str}</b>")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

@admin_only
@groups_only
async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have restrict rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, UNMUTE_PERMS)
        log_action(update.effective_chat.id, update.effective_user.id, "unmute", target.id)
        await reply(update, f"🔊 Unmuted {user_link(target)}")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

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
        return await reply(update, "❌ You don't have restrict rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    if await is_admin(context, update.effective_chat.id, target.id):
        return await reply(update, "❌ Can't warn admins.")
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
    if not silent:
        text = f"⚠️ <b>Warned</b> {user_link(target)} [{count}/{warn_limit}]\nReason: {html.escape(reason or 'None')}"

    if count >= warn_limit:
        db = get_db()
        db.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (update.effective_chat.id, target.id))
        db.commit(); db.close()
        if warn_action == "ban":
            await _do_ban(context, update.effective_chat.id, target.id)
            if not silent: text += "\n\n🚫 <b>Auto-banned</b> (warn limit reached)"
        elif warn_action == "kick":
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await context.bot.unban_chat_member(update.effective_chat.id, target.id)
            if not silent: text += "\n\n👢 <b>Auto-kicked</b> (warn limit reached)"
        else:
            await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS)
            if not silent: text += "\n\n🔇 <b>Auto-muted</b> (warn limit reached)"

    if not silent:
        await reply(update, text)

@admin_only
@groups_only
async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    db = get_db()
    row = db.execute("SELECT id FROM warns WHERE chat_id=? AND user_id=? ORDER BY warned_at DESC LIMIT 1",
                     (update.effective_chat.id, target.id)).fetchone()
    if row:
        db.execute("DELETE FROM warns WHERE id=?", (row["id"],))
        db.commit()
    db.close()
    await reply(update, f"✅ Removed 1 warn from {user_link(target)}")

@admin_only
@groups_only
async def resetwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    db = get_db()
    db.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?", (update.effective_chat.id, target.id))
    db.commit(); db.close()
    log_action(update.effective_chat.id, update.effective_user.id, "resetwarn", target.id)
    await reply(update, f"✅ Reset all warns for {user_link(target)}")

async def warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context) or update.effective_user
    cfg = get_chat(update.effective_chat.id)
    db = get_db()
    rows = db.execute("SELECT * FROM warns WHERE chat_id=? AND user_id=? ORDER BY warned_at DESC",
                      (update.effective_chat.id, target.id)).fetchall()
    db.close()
    if not rows:
        return await reply(update, f"✅ {user_link(target)} has no warnings.")
    lines = [f"⚠️ <b>Warns for {user_link(target)}:</b> [{len(rows)}/{cfg.get('warn_limit', 3)}]"]
    for i, w in enumerate(rows[:10], 1):
        lines.append(f"{i}. {html.escape(w['reason'] or 'No reason')} — <i>{w['warned_at']}</i>")
    await reply(update, "\n".join(lines))

# ────────────── PROMOTE / DEMOTE ─────────────────────────────────────────────
@admin_only
@groups_only
async def promote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have promote rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    title = " ".join(context.args[1:]) if not update.message.reply_to_message and len(context.args) > 1 else (
        " ".join(context.args) if context.args else "")
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
        await reply(update, f"⬆️ Promoted {user_link(target)}" + (f" as <b>{html.escape(title)}</b>" if title else ""))
    except BadRequest as e:
        await reply(update, f"❌ {e}")

@admin_only
@groups_only
async def demote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have promote rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, target.id,
            can_manage_chat=False, can_delete_messages=False, can_restrict_members=False,
            can_invite_users=False, can_pin_messages=False
        )
        log_action(update.effective_chat.id, update.effective_user.id, "demote", target.id)
        await reply(update, f"⬇️ Demoted {user_link(target)}")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

@admin_only
@groups_only
async def admintitle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ No promote rights.")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    title = " ".join(context.args) if update.message.reply_to_message else " ".join(context.args[1:])
    if not title: return await reply(update, "❌ Provide a title.")
    try:
        await context.bot.set_chat_administrator_custom_title(update.effective_chat.id, target.id, title[:16])
        await reply(update, f"✅ Set title <b>{html.escape(title)}</b> for {user_link(target)}")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

async def adminlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        lines = ["👮 <b>Admins:</b>"]
        for a in admins:
            name = html.escape(a.user.first_name or str(a.user.id))
            title = ""
            if isinstance(a, ChatMemberAdministrator) and a.custom_title:
                title = f" — <i>{html.escape(a.custom_title)}</i>"
            icon = "👑" if a.status == "creator" else "🔧"
            lines.append(f"{icon} <a href='tg://user?id={a.user.id}'>{name}</a>{title}")
        await reply(update, "\n".join(lines))
    except Exception as e:
        await reply(update, f"❌ {e}")

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
        await reply(update, f"📢 Admins tagged! {mentions}")
    except:
        pass

# ────────────── ZOMBIES ───────────────────────────────────────────────────────
@admin_only
@groups_only
async def zombies_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, "🔍 Scanning for zombie accounts... (this may take a while for large groups)")
    try:
        count = 0
        async for member in context.bot.get_chat_members(update.effective_chat.id):
            if member.user.is_deleted:
                count += 1
        await reply(update, f"🧟 Found <b>{count}</b> deleted (zombie) accounts.")
    except Exception as e:
        await reply(update, f"❌ {e}")

@admin_only
@groups_only
async def kickzombies_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have restrict rights.")
    await reply(update, "🔍 Scanning and kicking zombie accounts...")
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
        await reply(update, f"✅ Kicked <b>{kicked}</b> zombie accounts.")
    except Exception as e:
        await reply(update, f"❌ {e}")

# ────────────── PIN ───────────────────────────────────────────────────────────
@admin_only
@groups_only
async def pin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_pin(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have pin rights.")
    if not update.message.reply_to_message: return await reply(update, "❌ Reply to a message to pin it.")
    silent = "silent" in (context.args or []) or "notify" not in (context.args or [])
    try:
        await context.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id, disable_notification=silent)
        await reply(update, "📌 Message pinned.")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

@admin_only
@groups_only
async def unpin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_pin(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have pin rights.")
    try:
        if update.message.reply_to_message:
            await context.bot.unpin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        else:
            await context.bot.unpin_chat_message(update.effective_chat.id)
        await reply(update, "📌 Unpinned.")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

@admin_only
@groups_only
async def unpinall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_pin(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have pin rights.")
    try:
        await context.bot.unpin_all_chat_messages(update.effective_chat.id)
        await reply(update, "✅ Unpinned all messages.")
    except BadRequest as e:
        await reply(update, f"❌ {e}")

# ────────────── PURGE ─────────────────────────────────────────────────────────
@admin_only
@groups_only
async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ You don't have delete rights.")
    msg = update.message
    if not msg.reply_to_message: return await reply(update, "❌ Reply to the first message to purge from.")
    from_id = msg.reply_to_message.message_id
    to_id = msg.message_id
    count = 0
    ids = list(range(from_id, to_id + 1))
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
    m = await context.bot.send_message(update.effective_chat.id, f"🗑️ Purged <b>{count}</b> messages.", parse_mode="HTML")
    await asyncio.sleep(3)
    try: await m.delete()
    except: pass

@admin_only
async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return await reply(update, "❌ Reply to a message to delete.")
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
    if not context.args: return await reply(update, f"Usage: /lock {' | '.join(LOCK_TYPES.keys())}")
    t = context.args[0].lower()
    if t not in LOCK_TYPES: return await reply(update, f"❌ Unknown type. Options: {', '.join(LOCK_TYPES.keys())}")
    set_setting(update.effective_chat.id, LOCK_TYPES[t], 1)
    await reply(update, f"🔒 Locked: <b>{t}</b>")

@admin_only
@groups_only
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, f"Usage: /unlock {' | '.join(LOCK_TYPES.keys())}")
    t = context.args[0].lower()
    if t not in LOCK_TYPES: return await reply(update, f"❌ Unknown type.")
    set_setting(update.effective_chat.id, LOCK_TYPES[t], 0)
    await reply(update, f"🔓 Unlocked: <b>{t}</b>")

async def locks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_chat(update.effective_chat.id)
    lines = ["🔒 <b>Lock Status:</b>"]
    for name, key in LOCK_TYPES.items():
        icon = "🔴" if cfg.get(key, 0) else "🟢"
        lines.append(f"{icon} {name}")
    await reply(update, "\n".join(lines))

# ────────────── WELCOME / GOODBYE / RULES ────────────────────────────────────
def format_welcome(text: str, user: User, chat: Chat) -> str:
    count = "?"
    name = html.escape(user.first_name or "")
    last = html.escape(user.last_name or "")
    username = f"@{user.username}" if user.username else name
    mention = mention_html(user.id, name)
    return (text
            .replace("{first}", name)
            .replace("{last}", last)
            .replace("{username}", username)
            .replace("{mention}", mention)
            .replace("{chatname}", html.escape(chat.title or ""))
            .replace("{id}", str(user.id))
            .replace("{count}", count))

async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    ensure_chat(chat)
    cfg = get_chat(chat.id)
    members = update.message.new_chat_members if update.message else []
    if not members: return

    # Clean service
    if cfg.get("clean_service"):
        try: await update.message.delete()
        except: pass

    if not cfg.get("greetmembers", 1): return

    for user in members:
        ensure_user(user)
        if user.is_bot:
            if cfg.get("anti_bot"):
                try:
                    await context.bot.ban_chat_member(chat.id, user.id)
                    await context.bot.unban_chat_member(chat.id, user.id)
                    return
                except:
                    pass
            continue

        # Check gban
        reason = is_gbanned(user.id)
        if reason:
            try:
                await context.bot.ban_chat_member(chat.id, user.id)
                await context.bot.send_message(chat.id, f"🚫 Globally banned user <a href='tg://user?id={user.id}'>{html.escape(user.first_name)}</a> was removed.\nReason: {html.escape(reason)}", parse_mode="HTML")
            except:
                pass
            continue

        # Anti-raid
        if cfg.get("anti_raid"):
            raid_tracker[chat.id].append(time.time())
            threshold = cfg.get("raid_threshold", 10)
            recent = [t for t in raid_tracker[chat.id] if time.time() - t < 60]
            if len(recent) >= threshold:
                try:
                    await context.bot.ban_chat_member(chat.id, user.id)
                    await context.bot.unban_chat_member(chat.id, user.id)
                    await context.bot.send_message(chat.id, "🚨 Anti-raid: Suspicious join spike detected! New member kicked.")
                except:
                    pass
                continue

        # Restrict new members
        if cfg.get("restrict_new_members"):
            dur = cfg.get("new_member_mute_duration", 300)
            until = datetime.datetime.now(pytz.utc) + datetime.timedelta(seconds=dur)
            try:
                await context.bot.restrict_chat_member(chat.id, user.id, MUTE_PERMS, until_date=until)
            except:
                pass

        # Welcome message
        welcome = cfg.get("welcome_msg") or "Welcome {mention} to {chatname}! 👋"
        text = format_welcome(welcome, user, chat)
        buttons_raw = cfg.get("welcome_buttons", "[]")
        kb = parse_buttons(buttons_raw)

        try:
            m = await context.bot.send_message(chat.id, text, parse_mode="HTML",
                                               reply_markup=InlineKeyboardMarkup(kb) if kb else None)
            # Auto-delete welcome
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
    goodbye = cfg.get("goodbye_msg") or "Goodbye, {first}! 👋"
    text = format_welcome(goodbye, user, chat)
    try:
        await context.bot.send_message(chat.id, text, parse_mode="HTML")
    except:
        pass

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
    except:
        pass
    return []

@admin_only
@groups_only
async def setwelcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and not (update.message.reply_to_message and update.message.reply_to_message.text):
        return await reply(update, "Usage: /setwelcome Your welcome text\nPlaceholders: {mention} {first} {last} {username} {chatname}")
    text = " ".join(context.args) if context.args else update.message.reply_to_message.text
    set_setting(update.effective_chat.id, "welcome_msg", text)
    await reply(update, "✅ Welcome message set!")

@admin_only
@groups_only
async def setgoodbye_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    if not text: return await reply(update, "Usage: /setgoodbye Your goodbye text")
    set_setting(update.effective_chat.id, "goodbye_msg", text)
    await reply(update, "✅ Goodbye message set!")

async def welcome_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = context.args[0].lower() if context.args else "on"
    set_setting(update.effective_chat.id, "greetmembers", 1 if val == "on" else 0)
    await reply(update, f"✅ Welcome {'enabled' if val == 'on' else 'disabled'}")

async def goodbye_toggle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = context.args[0].lower() if context.args else "on"
    set_setting(update.effective_chat.id, "goodbye_enabled", 1 if val == "on" else 0)
    await reply(update, f"✅ Goodbye {'enabled' if val == 'on' else 'disabled'}")

@admin_only
@groups_only
async def setrules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else ""
    if not text and update.message.reply_to_message:
        text = update.message.reply_to_message.text or ""
    if not text: return await reply(update, "Usage: /setrules Your rules text")
    set_setting(update.effective_chat.id, "rules_text", text)
    await reply(update, "✅ Rules set!")

async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules = get_setting(update.effective_chat.id, "rules_text", "")
    if not rules: return await reply(update, "❌ No rules set. Use /setrules to set them.")
    await reply(update, f"📜 <b>Rules for {html.escape(update.effective_chat.title or '')}:</b>\n\n{html.escape(rules)}")

# ────────────── NOTES ─────────────────────────────────────────────────────────
@admin_only
async def save_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2: return await reply(update, "Usage: /save name content")
    name = context.args[0].lower()
    content = " ".join(context.args[1:])
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("INSERT OR REPLACE INTO notes (chat_id, name, content, created_by) VALUES (?,?,?,?)",
               (chat_id, name, content, update.effective_user.id))
    db.commit(); db.close()
    await reply(update, f"✅ Note <b>#{name}</b> saved!")

async def get_note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /get name")
    await _send_note(update, context, context.args[0].lower())

async def _send_note(update, context, name):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    row = db.execute("SELECT * FROM notes WHERE chat_id=? AND name=?", (chat_id, name)).fetchone()
    db.close()
    if not row: return await reply(update, f"❌ Note <b>#{name}</b> not found.")
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
    if not rows: return await reply(update, "❌ No notes saved.")
    names = " | ".join(f"<code>#{r['name']}</code>" for r in rows)
    await reply(update, f"📝 <b>Notes:</b>\n{names}")

@admin_only
async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /clear name")
    name = context.args[0].lower()
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM notes WHERE chat_id=? AND name=?", (chat_id, name))
    db.commit(); db.close()
    await reply(update, f"✅ Note <b>#{name}</b> deleted.")

@admin_only
async def clearall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM notes WHERE chat_id=?", (chat_id,))
    db.commit(); db.close()
    await reply(update, "✅ All notes deleted.")

# ────────────── FILTERS ───────────────────────────────────────────────────────
@admin_only
async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2: return await reply(update, "Usage: /filter keyword reply text")
    keyword = context.args[0].lower()
    is_regex = keyword.startswith("regex:")
    if is_regex: keyword = keyword[6:]
    reply_text = " ".join(context.args[1:])
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("INSERT OR REPLACE INTO filters (chat_id, keyword, reply, is_regex, created_by) VALUES (?,?,?,?,?)",
               (chat_id, keyword, reply_text, 1 if is_regex else 0, update.effective_user.id))
    db.commit(); db.close()
    await reply(update, f"✅ Filter <b>{html.escape(keyword)}</b> added!")

async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    rows = db.execute("SELECT keyword, is_regex FROM filters WHERE chat_id=? ORDER BY keyword", (chat_id,)).fetchall()
    db.close()
    if not rows: return await reply(update, "❌ No filters set.")
    lines = ["🔍 <b>Active Filters:</b>"]
    for r in rows:
        icon = "🔢" if r["is_regex"] else "🔑"
        lines.append(f"{icon} <code>{html.escape(r['keyword'])}</code>")
    await reply(update, "\n".join(lines))

@admin_only
async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /stop keyword")
    keyword = context.args[0].lower()
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM filters WHERE chat_id=? AND keyword=?", (chat_id, keyword))
    db.commit(); db.close()
    await reply(update, f"✅ Filter <b>{html.escape(keyword)}</b> removed.")

@admin_only
async def stopall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM filters WHERE chat_id=?", (chat_id,))
    db.commit(); db.close()
    await reply(update, "✅ All filters removed.")

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
    if not context.args: return await reply(update, "Usage: /addbl word")
    word = " ".join(context.args).lower()
    is_regex = word.startswith("regex:")
    if is_regex: word = word[6:]
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("INSERT OR IGNORE INTO blacklist (chat_id, word, is_regex, added_by) VALUES (?,?,?,?)",
               (chat_id, word, 1 if is_regex else 0, update.effective_user.id))
    db.commit(); db.close()
    await reply(update, f"✅ Added <code>{html.escape(word)}</code> to blacklist.")

@admin_only
async def unblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /unblacklist word")
    word = " ".join(context.args).lower()
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM blacklist WHERE chat_id=? AND word=?", (chat_id, word))
    db.commit(); db.close()
    await reply(update, f"✅ Removed <code>{html.escape(word)}</code> from blacklist.")

async def blacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    rows = db.execute("SELECT word, is_regex FROM blacklist WHERE chat_id=? ORDER BY word", (chat_id,)).fetchall()
    db.close()
    if not rows: return await reply(update, "❌ Blacklist is empty.")
    lines = ["🚫 <b>Blacklist:</b>"]
    for r in rows:
        lines.append(f"• <code>{html.escape(r['word'])}</code>" + (" (regex)" if r["is_regex"] else ""))
    await reply(update, "\n".join(lines))

@admin_only
async def blacklistmode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ("delete", "warn", "mute", "ban"):
        return await reply(update, "Usage: /blacklistmode delete|warn|mute|ban")
    set_setting(update.effective_chat.id, "blacklist_action", context.args[0])
    await reply(update, f"✅ Blacklist action set to <b>{context.args[0]}</b>")

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

    # Anti-flood
    if cfg.get("anti_flood", 1):
        flood_count = cfg.get("flood_count", 5)
        flood_time = cfg.get("flood_time", 5)
        flood_action = cfg.get("flood_action", "mute")
        now = time.time()
        flood_cache[f"{chat_id}:{user_id}"].append(now)
        recent = [t for t in flood_cache[f"{chat_id}:{user_id}"] if now - t < flood_time]
        if len(recent) >= flood_count:
            flood_cache[f"{chat_id}:{user_id}"].clear()
            try:
                await update.message.delete()
            except:
                pass
            if flood_action == "ban":
                await _do_ban(context, chat_id, user_id)
                await context.bot.send_message(chat_id, f"🚫 {user_link(update.effective_user)} has been banned for flooding.", parse_mode="HTML")
            elif flood_action == "kick":
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.unban_chat_member(chat_id, user_id)
                await context.bot.send_message(chat_id, f"👢 {user_link(update.effective_user)} has been kicked for flooding.", parse_mode="HTML")
            else:
                await context.bot.restrict_chat_member(chat_id, user_id, MUTE_PERMS)
                await context.bot.send_message(chat_id, f"🔇 {user_link(update.effective_user)} has been muted for flooding.", parse_mode="HTML")
            return

    # Anti-link
    if cfg.get("anti_link") and update.message.text:
        url_pattern = r'(https?://|t\.me/|@\w+|tg://)'
        if re.search(url_pattern, update.message.text, re.IGNORECASE):
            try: await update.message.delete()
            except: pass
            return

    # Anti-forward
    if cfg.get("anti_forward") and update.message.forward_date:
        try: await update.message.delete()
        except: pass
        return

    # Lock checks
    msg = update.message
    if msg.sticker and cfg.get("lock_stickers"):
        try: await msg.delete()
        except: pass
        return
    if msg.animation and cfg.get("lock_gifs"):
        try: await msg.delete()
        except: pass
        return
    if (msg.photo or msg.document or msg.video or msg.audio) and cfg.get("lock_media"):
        try: await msg.delete()
        except: pass
        return
    if msg.poll and cfg.get("lock_polls"):
        try: await msg.delete()
        except: pass
        return
    if msg.voice and cfg.get("lock_voice"):
        try: await msg.delete()
        except: pass
        return
    if msg.video_note and cfg.get("lock_video"):
        try: await msg.delete()
        except: pass
        return
    if msg.document and cfg.get("lock_document"):
        try: await msg.delete()
        except: pass
        return
    if msg.forward_date and cfg.get("lock_forward"):
        try: await msg.delete()
        except: pass
        return
    if msg.game and cfg.get("lock_games"):
        try: await msg.delete()
        except: pass
        return

    # Update message count
    db = get_db()
    db.execute("UPDATE users SET total_msgs=total_msgs+1 WHERE user_id=?", (user_id,))
    db.commit(); db.close()

# ────────────── ANTI-SPAM SETTINGS ────────────────────────────────────────────
@admin_only
async def antispam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_spam", 1 if val else 0)
    await reply(update, f"✅ Anti-spam {'enabled' if val else 'disabled'}")

@admin_only
async def antiflood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_flood", 1 if val else 0)
    await reply(update, f"✅ Anti-flood {'enabled' if val else 'disabled'}")

@admin_only
async def setflood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /setflood N [seconds]")
    n = int(context.args[0])
    t = int(context.args[1]) if len(context.args) > 1 else 5
    db = get_db()
    db.execute("UPDATE chats SET flood_count=?, flood_time=? WHERE chat_id=?", (n, t, update.effective_chat.id))
    db.commit(); db.close()
    await reply(update, f"✅ Flood limit: <b>{n}</b> messages in <b>{t}s</b>")

@admin_only
async def setfloodaction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ("mute", "ban", "kick"):
        return await reply(update, "Usage: /setfloodaction mute|ban|kick")
    set_setting(update.effective_chat.id, "flood_action", context.args[0])
    await reply(update, f"✅ Flood action: <b>{context.args[0]}</b>")

@admin_only
async def antilink_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_link", 1 if val else 0)
    await reply(update, f"✅ Anti-link {'enabled' if val else 'disabled'}")

@admin_only
async def antiforward_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_forward", 1 if val else 0)
    await reply(update, f"✅ Anti-forward {'enabled' if val else 'disabled'}")

@admin_only
async def antibot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_bot", 1 if val else 0)
    await reply(update, f"✅ Anti-bot {'enabled' if val else 'disabled'}")

@admin_only
async def antiraid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_raid", 1 if val else 0)
    await reply(update, f"✅ Anti-raid {'enabled' if val else 'disabled'}")

@admin_only
async def setraid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /setraid N")
    set_setting(update.effective_chat.id, "raid_threshold", int(context.args[0]))
    await reply(update, f"✅ Raid threshold set to <b>{context.args[0]}</b> joins/min")

@admin_only
async def cas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "cas_enabled", 1 if val else 0)
    await reply(update, f"✅ CAS {'enabled' if val else 'disabled'}")

# ────────────── WARN SETTINGS ────────────────────────────────────────────────
@admin_only
async def setwarnlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /setwarnlimit N")
    set_setting(update.effective_chat.id, "warn_limit", int(context.args[0]))
    await reply(update, f"✅ Warn limit set to <b>{context.args[0]}</b>")

@admin_only
async def setwarnaction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ("mute", "ban", "kick"):
        return await reply(update, "Usage: /setwarnaction mute|ban|kick")
    set_setting(update.effective_chat.id, "warn_action", context.args[0])
    await reply(update, f"✅ Warn action: <b>{context.args[0]}</b>")

# ────────────── REPORT ────────────────────────────────────────────────────────
async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message: return await reply(update, "❌ Reply to a message to report it.")
    cfg = get_chat(update.effective_chat.id)
    if not cfg.get("report_enabled", 1): return await reply(update, "❌ Reports are disabled in this chat.")
    reported = update.message.reply_to_message.from_user
    reason = " ".join(context.args) if context.args else "No reason"
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

    text = (f"🚨 <b>Report</b>\n"
            f"Reporter: {user_link(update.effective_user)}\n"
            f"Reported: {user_link(reported)}\n"
            f"Reason: {html.escape(reason)}\n"
            f"Admins: {mentions}")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🚫 Ban", callback_data=f"report_ban:{reported.id}"),
        InlineKeyboardButton("🔇 Mute", callback_data=f"report_mute:{reported.id}"),
        InlineKeyboardButton("❌ Dismiss", callback_data=f"report_dismiss:{update.message.reply_to_message.message_id}"),
    ]])
    await reply(update, text, reply_markup=kb)

async def report_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not await is_admin(context, update.effective_chat.id, q.from_user.id):
        await q.answer("❌ Admins only.", show_alert=True); return
    await q.answer()
    data = q.data
    if data.startswith("report_ban:"):
        uid = int(data.split(":")[1])
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, uid)
            await q.edit_message_text(q.message.text + f"\n\n✅ Banned by {user_link(q.from_user)}", parse_mode="HTML")
        except Exception as e:
            await q.message.reply_text(f"❌ {e}")
    elif data.startswith("report_mute:"):
        uid = int(data.split(":")[1])
        try:
            await context.bot.restrict_chat_member(update.effective_chat.id, uid, MUTE_PERMS)
            await q.edit_message_text(q.message.text + f"\n\n✅ Muted by {user_link(q.from_user)}", parse_mode="HTML")
        except Exception as e:
            await q.message.reply_text(f"❌ {e}")
    elif data.startswith("report_dismiss:"):
        await q.edit_message_text(f"✅ Report dismissed by {user_link(q.from_user)}", parse_mode="HTML")

# ────────────── FEDERATION SYSTEM ─────────────────────────────────────────────
@groups_only
async def newfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ Admins only.")
    if not context.args: return await reply(update, "Usage: /newfed FederationName")
    name = " ".join(context.args)
    fed_id = str(uuid.uuid4())[:8]
    db = get_db()
    db.execute("INSERT INTO federations (fed_id, name, owner_id) VALUES (?,?,?)",
               (fed_id, name, update.effective_user.id))
    db.execute("INSERT OR IGNORE INTO federation_chats (fed_id, chat_id) VALUES (?,?)",
               (fed_id, update.effective_chat.id))
    db.execute("UPDATE chats SET fed_id=? WHERE chat_id=?", (fed_id, update.effective_chat.id))
    db.commit(); db.close()
    await reply(update, f"✅ Federation <b>{html.escape(name)}</b> created!\nFed ID: <code>{fed_id}</code>\nUse this ID for other chats to join.")

async def joinfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ Only group owner can join a federation.")
    if not context.args: return await reply(update, "Usage: /joinfed fed_id")
    fed_id = context.args[0]
    db = get_db()
    fed = db.execute("SELECT * FROM federations WHERE fed_id=?", (fed_id,)).fetchone()
    if not fed: db.close(); return await reply(update, "❌ Federation not found.")
    db.execute("INSERT OR IGNORE INTO federation_chats (fed_id, chat_id) VALUES (?,?)",
               (fed_id, update.effective_chat.id))
    db.execute("UPDATE chats SET fed_id=? WHERE chat_id=?", (fed_id, update.effective_chat.id))
    db.commit(); db.close()
    await reply(update, f"✅ Joined federation <b>{html.escape(fed['name'])}</b>!")

async def leavefed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "❌ Only group owner can leave a federation.")
    db = get_db()
    fed_id = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_id or not fed_id["fed_id"]:
        db.close(); return await reply(update, "❌ This chat isn't in a federation.")
    db.execute("DELETE FROM federation_chats WHERE fed_id=? AND chat_id=?", (fed_id["fed_id"], update.effective_chat.id))
    db.execute("UPDATE chats SET fed_id=NULL WHERE chat_id=?", (update.effective_chat.id,))
    db.commit(); db.close()
    await reply(update, "✅ Left the federation.")

async def fedinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_id = context.args[0] if context.args else None
    if not fed_id:
        row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
        fed_id = row["fed_id"] if row else None
    if not fed_id: db.close(); return await reply(update, "❌ No federation found.")
    fed = db.execute("SELECT * FROM federations WHERE fed_id=?", (fed_id,)).fetchone()
    if not fed: db.close(); return await reply(update, "❌ Federation not found.")
    chat_count = db.execute("SELECT COUNT(*) as c FROM federation_chats WHERE fed_id=?", (fed_id,)).fetchone()["c"]
    ban_count = db.execute("SELECT COUNT(*) as c FROM federation_bans WHERE fed_id=?", (fed_id,)).fetchone()["c"]
    db.close()
    await reply(update, f"🌐 <b>Federation: {html.escape(fed['name'])}</b>\n"
                       f"ID: <code>{fed_id}</code>\n"
                       f"Chats: {chat_count}\n"
                       f"Total bans: {ban_count}")

async def fban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]:
        db.close(); return await reply(update, "❌ This chat isn't in a federation.")
    fed_id = fed_row["fed_id"]
    fed = db.execute("SELECT * FROM federations WHERE fed_id=?", (fed_id,)).fetchone()
    # Check if user is fed owner or admin
    is_fed_admin = (update.effective_user.id == fed["owner_id"] or
                    db.execute("SELECT 1 FROM federation_admins WHERE fed_id=? AND user_id=?",
                               (fed_id, update.effective_user.id)).fetchone() or
                    is_sudo(update.effective_user.id))
    if not is_fed_admin:
        db.close(); return await reply(update, "❌ You're not a federation admin.")
    target = get_target(update, context)
    if not target: db.close(); return await reply(update, "❌ Reply to a user or provide username.")
    reason = " ".join(context.args) if context.args else "Fed ban"
    db.execute("INSERT OR REPLACE INTO federation_bans (fed_id, user_id, reason, banned_by) VALUES (?,?,?,?)",
               (fed_id, target.id, reason, update.effective_user.id))
    # Ban from all federation chats
    chats = db.execute("SELECT chat_id FROM federation_chats WHERE fed_id=?", (fed_id,)).fetchall()
    db.commit(); db.close()
    banned_in = 0
    for ch in chats:
        try:
            await context.bot.ban_chat_member(ch["chat_id"], target.id)
            banned_in += 1
        except:
            pass
    await reply(update, f"🌐 Fed-banned {user_link(target)}\nReason: {html.escape(reason)}\nBanned in {banned_in} chats.")

async def unfban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]:
        db.close(); return await reply(update, "❌ Not in a federation.")
    fed_id = fed_row["fed_id"]
    target = get_target(update, context)
    if not target: db.close(); return await reply(update, "❌ Reply to a user or provide username.")
    db.execute("DELETE FROM federation_bans WHERE fed_id=? AND user_id=?", (fed_id, target.id))
    chats = db.execute("SELECT chat_id FROM federation_chats WHERE fed_id=?", (fed_id,)).fetchall()
    db.commit(); db.close()
    for ch in chats:
        try:
            await context.bot.unban_chat_member(ch["chat_id"], target.id, only_if_banned=True)
        except:
            pass
    await reply(update, f"✅ Fed-unbanned {user_link(target)}")

async def fedbans_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]:
        db.close(); return await reply(update, "❌ Not in a federation.")
    fed_id = fed_row["fed_id"]
    bans = db.execute("SELECT fb.*, u.username, u.first_name FROM federation_bans fb LEFT JOIN users u ON u.user_id=fb.user_id WHERE fb.fed_id=? LIMIT 20", (fed_id,)).fetchall()
    db.close()
    if not bans: return await reply(update, "✅ No federation bans.")
    lines = [f"🌐 <b>Federation Bans ({len(bans)}):</b>"]
    for b in bans:
        name = html.escape(b["first_name"] or str(b["user_id"]))
        lines.append(f"• {name} — {html.escape(b['reason'] or 'No reason')}")
    await reply(update, "\n".join(lines))

# ────────────── CONNECTION SYSTEM ─────────────────────────────────────────────
def get_connected_chat(user_id: int, chat: Chat) -> int:
    if chat.type != "private": return chat.id
    return connection_cache.get(user_id, chat.id)

async def connect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return await reply(update, "❌ Use this command in private chat.")
    if not context.args: return await reply(update, "Usage: /connect chat_id")
    try:
        chat_id = int(context.args[0])
        # Verify user is admin there
        if not await is_admin(context, chat_id, update.effective_user.id):
            return await reply(update, "❌ You must be an admin in that group.")
        connection_cache[update.effective_user.id] = chat_id
        db = get_db()
        db.execute("INSERT OR REPLACE INTO connections (user_id, chat_id) VALUES (?,?)",
                   (update.effective_user.id, chat_id))
        db.commit(); db.close()
        chat_obj = await context.bot.get_chat(chat_id)
        await reply(update, f"✅ Connected to <b>{html.escape(chat_obj.title or str(chat_id))}</b>!\nYou can now use admin commands from here.")
    except Exception as e:
        await reply(update, f"❌ {e}")

async def disconnect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return await reply(update, "❌ Use this command in private chat.")
    connection_cache.pop(update.effective_user.id, None)
    db = get_db()
    db.execute("DELETE FROM connections WHERE user_id=?", (update.effective_user.id,))
    db.commit(); db.close()
    await reply(update, "✅ Disconnected.")

async def connected_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = connection_cache.get(update.effective_user.id)
    if not cid:
        # Load from DB
        db = get_db()
        row = db.execute("SELECT chat_id FROM connections WHERE user_id=?", (update.effective_user.id,)).fetchone()
        db.close()
        if row:
            cid = row["chat_id"]
            connection_cache[update.effective_user.id] = cid
    if not cid:
        return await reply(update, "❌ Not connected. Use /connect chat_id")
    try:
        chat = await context.bot.get_chat(cid)
        await reply(update, f"🔗 Connected to: <b>{html.escape(chat.title or str(cid))}</b>")
    except:
        await reply(update, f"🔗 Connected to: <code>{cid}</code>")

# ────────────── AFK ───────────────────────────────────────────────────────────
async def afk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = " ".join(context.args) if context.args else ""
    user_id = update.effective_user.id
    afk_cache[user_id] = {"reason": reason, "since": datetime.datetime.now(pytz.utc)}
    db = get_db()
    db.execute("UPDATE users SET is_afk=1, afk_reason=?, afk_since=CURRENT_TIMESTAMP WHERE user_id=?",
               (reason, user_id))
    db.commit(); db.close()
    await reply(update, f"😴 {user_link(update.effective_user)} is now AFK" + (f": {html.escape(reason)}" if reason else ""))

async def afk_check_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user: return
    user_id = update.effective_user.id

    # Check if this user is AFK (unset)
    if user_id in afk_cache:
        del afk_cache[user_id]
        db = get_db()
        db.execute("UPDATE users SET is_afk=0, afk_reason=NULL WHERE user_id=?", (user_id,))
        db.commit(); db.close()
        await reply(update, f"✅ {user_link(update.effective_user)} is back!")

    # Check if replied user is AFK
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
            msg = f"😴 {user_link(ru)} is AFK for <b>{time_str}</b>"
            if reason: msg += f"\nReason: {html.escape(reason)}"
            await reply(update, msg)

# ────────────── GLOBAL BAN ────────────────────────────────────────────────────
@owner_only
async def gban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user or provide username.")
    reason = " ".join(context.args[1:]) if not update.message.reply_to_message else " ".join(context.args)
    db = get_db()
    db.execute("""INSERT INTO users (user_id, is_gbanned, gban_reason, gbanned_by, gbanned_at)
                  VALUES (?,1,?,?,CURRENT_TIMESTAMP)
                  ON CONFLICT(user_id) DO UPDATE SET is_gbanned=1, gban_reason=excluded.gban_reason,
                  gbanned_by=excluded.gbanned_by, gbanned_at=excluded.gbanned_at""",
               (target.id, reason or "No reason", update.effective_user.id))
    # Ban from all chats
    chats = db.execute("SELECT chat_id FROM chats").fetchall()
    db.commit(); db.close()
    banned_in = 0
    for ch in chats:
        try:
            await context.bot.ban_chat_member(ch["chat_id"], target.id)
            banned_in += 1
        except:
            pass
    log_action(0, update.effective_user.id, "gban", target.id, reason)
    await reply(update, f"🌍 <b>Global Banned</b> {user_link(target)}\nReason: {html.escape(reason or 'None')}\nBanned in {banned_in} chats.")
    if GBAN_LOG:
        try:
            await context.bot.send_message(GBAN_LOG, f"🌍 GBAN\nUser: {user_link(target)} (<code>{target.id}</code>)\nBy: {user_link(update.effective_user)}\nReason: {html.escape(reason or 'None')}", parse_mode="HTML")
        except:
            pass

@owner_only
async def ungban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user or provide username.")
    db = get_db()
    db.execute("UPDATE users SET is_gbanned=0, gban_reason=NULL WHERE user_id=?", (target.id,))
    chats = db.execute("SELECT chat_id FROM chats").fetchall()
    db.commit(); db.close()
    for ch in chats:
        try:
            await context.bot.unban_chat_member(ch["chat_id"], target.id, only_if_banned=True)
        except:
            pass
    await reply(update, f"✅ Removed global ban for {user_link(target)}")

# ────────────── SUDO ──────────────────────────────────────────────────────────
@owner_only
async def sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    db = get_db()
    db.execute("INSERT OR IGNORE INTO sudo_users (user_id, added_by) VALUES (?,?)",
               (target.id, update.effective_user.id))
    db.execute("UPDATE users SET is_sudo=1 WHERE user_id=?", (target.id,))
    db.commit(); db.close()
    await reply(update, f"✅ {user_link(target)} added as sudo user.")

@owner_only
async def unsudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user.")
    db = get_db()
    db.execute("DELETE FROM sudo_users WHERE user_id=?", (target.id,))
    db.execute("UPDATE users SET is_sudo=0 WHERE user_id=?", (target.id,))
    db.commit(); db.close()
    await reply(update, f"✅ {user_link(target)} removed from sudo users.")

# ────────────── BROADCAST ─────────────────────────────────────────────────────
@owner_only
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and not (update.message.reply_to_message):
        return await reply(update, "Usage: /broadcast message")
    text = " ".join(context.args) if context.args else update.message.reply_to_message.text
    db = get_db()
    chats = db.execute("SELECT chat_id FROM chats").fetchall()
    db.close()
    sent = failed = 0
    for ch in chats:
        try:
            await context.bot.send_message(ch["chat_id"], text, parse_mode="HTML")
            sent += 1
        except:
            failed += 1
    await reply(update, f"📢 Broadcast done!\n✅ Sent: {sent}\n❌ Failed: {failed}")

# ────────────── STATS ─────────────────────────────────────────────────────────
@owner_only
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    chats = db.execute("SELECT COUNT(*) as c FROM chats").fetchone()["c"]
    users = db.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    warns = db.execute("SELECT COUNT(*) as c FROM warns").fetchone()["c"]
    bans = db.execute("SELECT COUNT(*) as c FROM bans").fetchone()["c"]
    gbans = db.execute("SELECT COUNT(*) as c FROM users WHERE is_gbanned=1").fetchone()["c"]
    notes = db.execute("SELECT COUNT(*) as c FROM notes").fetchone()["c"]
    filters_count = db.execute("SELECT COUNT(*) as c FROM filters").fetchone()["c"]
    db.close()
    uptime = datetime.datetime.now(pytz.utc) - START_TIME
    hours = int(uptime.total_seconds() // 3600)
    mins = int((uptime.total_seconds() % 3600) // 60)
    await reply(update,
        f"📊 <b>Bot Statistics</b>\n\n"
        f"👥 Chats: <b>{chats}</b>\n"
        f"👤 Users: <b>{users}</b>\n"
        f"⚠️ Total warns: <b>{warns}</b>\n"
        f"🚫 Total bans: <b>{bans}</b>\n"
        f"🌍 Global bans: <b>{gbans}</b>\n"
        f"📝 Notes: <b>{notes}</b>\n"
        f"🔍 Filters: <b>{filters_count}</b>\n"
        f"⏱️ Uptime: <b>{hours}h {mins}m</b>"
    )

# ────────────── INFO / ID ─────────────────────────────────────────────────────
async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    chat = update.effective_chat
    text = f"👤 User ID: <code>{target.id}</code>\n💬 Chat ID: <code>{chat.id}</code>"
    await reply(update, text)

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    text = [f"👤 <b>User Info</b>",
            f"Name: <a href='tg://user?id={target.id}'>{name}</a>",
            f"ID: <code>{target.id}</code>"]
    if target.username:
        text.append(f"Username: @{html.escape(target.username)}")
    if row:
        text.append(f"⚠️ Warns: {warns}")
        text.append(f"💰 Coins: {row['coins'] or 0}")
        text.append(f"⭐ Reputation: {row['reputation'] or 0}")
        text.append(f"💬 Messages: {row['total_msgs'] or 0}")
        if row["is_gbanned"]:
            text.append(f"🌍 Globally Banned: Yes — {html.escape(row['gban_reason'] or 'No reason')}")
        if row["is_sudo"]:
            text.append("👑 Sudo: Yes")
    await reply(update, "\n".join(text))

async def chatinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    members = await context.bot.get_chat_member_count(chat.id)
    text = (f"💬 <b>Chat Info</b>\n"
            f"Title: {html.escape(chat.title or 'N/A')}\n"
            f"ID: <code>{chat.id}</code>\n"
            f"Type: {chat.type}\n"
            f"Members: {members}\n"
            f"Username: @{chat.username}" if chat.username else "")
    await reply(update, text.strip())

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start = time.time()
    m = await reply(update, "🏓 Pong!")
    elapsed = (time.time() - start) * 1000
    await m.edit_text(f"🏓 Pong! <b>{elapsed:.1f}ms</b>", parse_mode="HTML")

async def uptime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.datetime.now(pytz.utc) - START_TIME
    total_seconds = int(uptime.total_seconds())
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    mins = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    await reply(update, f"⏱️ Uptime: <b>{days}d {hours}h {mins}m {secs}s</b>")

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
            h = int(remaining // 3600); m = int((remaining % 3600) // 60)
            db.close()
            return await reply(update, f"⏰ Daily already claimed! Come back in <b>{h}h {m}m</b>")
    coins = DAILY_COINS + random.randint(0, 100)
    db.execute("UPDATE users SET coins=coins+?, last_daily=CURRENT_TIMESTAMP WHERE user_id=?", (coins, user_id))
    db.commit(); db.close()
    await reply(update, f"💰 Daily claimed! You got <b>{coins} coins</b>!")

async def coins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context) or update.effective_user
    db = get_db()
    row = db.execute("SELECT coins FROM users WHERE user_id=?", (target.id,)).fetchone()
    db.close()
    balance = row["coins"] if row else 0
    await reply(update, f"💰 {user_link(target)}'s balance: <b>{balance} coins</b>")

async def mine_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    earned = random.randint(MINE_MIN, MINE_MAX)
    db = get_db()
    db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (earned, user_id))
    db.commit(); db.close()
    msgs = ["⛏️ You mined!", "💎 Jackpot!", "🪨 Nice find!"]
    await reply(update, f"{random.choice(msgs)} You earned <b>{earned} coins</b>!")

async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2 and not (update.message.reply_to_message and context.args):
        return await reply(update, "Usage: /give @user amount")
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user or provide username.")
    try:
        amount = int(context.args[-1])
    except:
        return await reply(update, "❌ Invalid amount.")
    if amount <= 0: return await reply(update, "❌ Amount must be positive.")
    user_id = update.effective_user.id
    db = get_db()
    sender = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not sender or sender["coins"] < amount:
        db.close(); return await reply(update, "❌ Insufficient coins.")
    db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, user_id))
    db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, target.id))
    db.commit(); db.close()
    await reply(update, f"✅ Sent <b>{amount} coins</b> to {user_link(target)}")

async def rob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to a user to rob.")
    if target.id == update.effective_user.id: return await reply(update, "❌ Can't rob yourself!")
    db = get_db()
    victim = db.execute("SELECT coins FROM users WHERE user_id=?", (target.id,)).fetchone()
    if not victim or victim["coins"] < 100:
        db.close(); return await reply(update, "❌ That user doesn't have enough coins to rob.")
    if random.random() < 0.4:
        fine = random.randint(50, 200)
        db.execute("UPDATE users SET coins=MAX(0, coins-?) WHERE user_id=?", (fine, update.effective_user.id))
        db.commit(); db.close()
        await reply(update, f"👮 You got caught robbing! Fined <b>{fine} coins</b>.")
    else:
        stolen = random.randint(50, min(300, victim["coins"]))
        db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (stolen, target.id))
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (stolen, update.effective_user.id))
        db.commit(); db.close()
        await reply(update, f"💰 You stole <b>{stolen} coins</b> from {user_link(target)}!")

async def flip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        result = "Heads" if random.random() > 0.5 else "Tails"
        await reply(update, f"🪙 {result}!")
        return
    amount = int(context.args[0])
    user_id = update.effective_user.id
    db = get_db()
    row = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row or row["coins"] < amount:
        db.close(); return await reply(update, "❌ Insufficient coins.")
    if random.random() > 0.5:
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, user_id))
        db.commit(); db.close()
        await reply(update, f"🪙 <b>Heads!</b> You won <b>{amount} coins</b>! 🎉")
    else:
        db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, user_id))
        db.commit(); db.close()
        await reply(update, f"🪙 <b>Tails!</b> You lost <b>{amount} coins</b>. 😢")

async def slots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols = ["🍒", "🍋", "🍊", "💎", "7️⃣", "⭐"]
    weights = [30, 25, 20, 10, 5, 10]
    roll = random.choices(symbols, weights=weights, k=3)
    result = " | ".join(roll)
    amount = int(context.args[0]) if context.args and context.args[0].isdigit() else 0
    user_id = update.effective_user.id

    if roll[0] == roll[1] == roll[2]:
        multiplier = 10 if roll[0] == "7️⃣" else (5 if roll[0] == "💎" else 3)
        winnings = amount * multiplier
        msg = f"🎰 {result}\n🎉 JACKPOT! Won <b>{winnings} coins</b>!"
        if amount:
            db = get_db()
            db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (winnings, user_id))
            db.commit(); db.close()
    elif roll[0] == roll[1] or roll[1] == roll[2]:
        winnings = amount
        msg = f"🎰 {result}\n✨ Small win! Got your bet back!"
    else:
        winnings = -amount
        msg = f"🎰 {result}\n😢 No match. Lost <b>{amount} coins</b>."
        if amount:
            db = get_db()
            db.execute("UPDATE users SET coins=MAX(0,coins-?) WHERE user_id=?", (amount, user_id))
            db.commit(); db.close()
    await reply(update, msg)

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    rows = db.execute("SELECT user_id, username, first_name, coins FROM users ORDER BY coins DESC LIMIT 10").fetchall()
    db.close()
    lines = ["💰 <b>Top 10 Richest:</b>"]
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    for i, row in enumerate(rows):
        name = html.escape(row["first_name"] or str(row["user_id"]))
        lines.append(f"{medals[i]} {name} — <b>{row['coins']}</b> coins")
    await reply(update, "\n".join(lines))

# ────────────── REPUTATION ────────────────────────────────────────────────────
async def rep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target:
        # Show own rep
        db = get_db()
        row = db.execute("SELECT reputation FROM users WHERE user_id=?", (update.effective_user.id,)).fetchone()
        db.close()
        rep = row["reputation"] if row else 0
        return await reply(update, f"⭐ Your reputation: <b>{rep}</b>")
    if target.id == update.effective_user.id:
        return await reply(update, "❌ Can't give rep to yourself!")
    giver = update.effective_user.id
    db = get_db()
    # Check cooldown (1 per day per user)
    existing = db.execute("SELECT given_at FROM reputation WHERE giver_id=? AND receiver_id=? AND chat_id=?",
                          (giver, target.id, update.effective_chat.id)).fetchone()
    if existing:
        given = datetime.datetime.fromisoformat(str(existing["given_at"]).replace(" ", "T")).replace(tzinfo=pytz.utc)
        if (datetime.datetime.now(pytz.utc) - given).total_seconds() < 86400:
            db.close()
            return await reply(update, "❌ You already gave rep to this user today!")
    db.execute("INSERT OR REPLACE INTO reputation (giver_id, receiver_id, chat_id) VALUES (?,?,?)",
               (giver, target.id, update.effective_chat.id))
    db.execute("UPDATE users SET reputation=reputation+1 WHERE user_id=?", (target.id,))
    row = db.execute("SELECT reputation FROM users WHERE user_id=?", (target.id,)).fetchone()
    db.commit(); db.close()
    rep = row["reputation"] if row else 1
    await reply(update, f"⭐ {user_link(update.effective_user)} gave +1 rep to {user_link(target)}\nTotal: <b>{rep}</b>")

async def reprank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    rows = db.execute("SELECT user_id, first_name, reputation FROM users ORDER BY reputation DESC LIMIT 10").fetchall()
    db.close()
    lines = ["⭐ <b>Reputation Leaderboard:</b>"]
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    for i, row in enumerate(rows):
        name = html.escape(row["first_name"] or str(row["user_id"]))
        lines.append(f"{medals[i]} {name} — <b>{row['reputation']}</b> rep")
    await reply(update, "\n".join(lines))

# ────────────── FUN ───────────────────────────────────────────────────────────
EIGHTBALL_ANSWERS = [
    "It is certain. ✅", "It is decidedly so. ✅", "Without a doubt. ✅",
    "Yes, definitely. ✅", "You may rely on it. ✅", "As I see it, yes. ✅",
    "Most likely. ✅", "Outlook good. ✅", "Signs point to yes. ✅",
    "Reply hazy, try again. 🔄", "Ask again later. 🔄", "Better not tell you now. 🔄",
    "Cannot predict now. 🔄", "Don't count on it. ❌", "My reply is no. ❌",
    "My sources say no. ❌", "Outlook not so good. ❌", "Very doubtful. ❌"
]

async def eightball_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "🎱 Ask me a question!")
    q = " ".join(context.args)
    await reply(update, f"🎱 <b>Q:</b> {html.escape(q)}\n<b>A:</b> {random.choice(EIGHTBALL_ANSWERS)}")

async def roll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sides = int(context.args[0]) if context.args and context.args[0].isdigit() else 6
    result = random.randint(1, sides)
    await reply(update, f"🎲 Rolled a {sides}-sided die: <b>{result}</b>")

SLAP_MSGS = [
    "{user} slapped {target} with a large trout! 🐟",
    "{user} slapped {target} across the face! 👋",
    "{user} gave {target} a fierce slap! ⚡",
]
HUG_MSGS = [
    "{user} gave {target} a warm hug! 🤗",
    "{user} wrapped {target} in a big bear hug! 🐻",
]
ROASTS = [
    "You're so dumb, you'd drown in a parked car.",
    "You have the personality of a wet paper bag.",
    "Even your shadow doesn't want to follow you.",
    "You're not stupid, you just have bad luck thinking.",
    "I've seen better arguments in a kindergarten.",
]
COMPLIMENTS = [
    "You're more helpful than you even realize!",
    "You have a great sense of humor!",
    "You're a creative and fantastic person!",
    "Being around you makes everything better!",
]
JOKES = [
    "Why don't scientists trust atoms? Because they make up everything! 😂",
    "Why did the scarecrow win an award? He was outstanding in his field! 🌾",
    "What do you call fake spaghetti? An impasta! 🍝",
    "Why did the bicycle fall over? It was two-tired! 🚲",
    "What do you call a fish without eyes? A fsh! 🐟",
]

async def slap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to someone to slap.")
    msg = random.choice(SLAP_MSGS).format(user=user_link(update.effective_user), target=user_link(target))
    await reply(update, msg)

async def hug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    if not target: return await reply(update, "❌ Reply to someone to hug.")
    msg = random.choice(HUG_MSGS).format(user=user_link(update.effective_user), target=user_link(target))
    await reply(update, msg)

async def ship_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        u1 = update.effective_user
        u2 = update.message.reply_to_message.from_user
    elif len(context.args) >= 1:
        u1 = update.effective_user
        u2 = type("U", (), {"first_name": context.args[0], "id": 0})()
    else:
        return await reply(update, "❌ Reply to a user or provide a name.")
    compat = random.randint(1, 100)
    bar_filled = int(compat / 10)
    bar = "❤️" * bar_filled + "🖤" * (10 - bar_filled)
    await reply(update, f"💕 <b>Ship Meter</b>\n{user_link(u1)} + {html.escape(u2.first_name or '')}\n[{bar}] <b>{compat}%</b>")

async def roast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    name = user_link(target) if target else user_link(update.effective_user)
    await reply(update, f"🔥 {name}: {random.choice(ROASTS)}")

async def compliment_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = get_target(update, context)
    name = user_link(target) if target else user_link(update.effective_user)
    await reply(update, f"💐 {name}: {random.choice(COMPLIMENTS)}")

async def joke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, random.choice(JOKES))

TRUTH_QUESTIONS = [
    "What's your biggest fear?", "What's the most embarrassing thing you've done?",
    "Have you ever lied to a friend?", "What's your biggest regret?",
]
DARES = [
    "Send a voice message singing a song.", "Change your bio to something funny for 24 hours.",
    "Tag 3 friends and say something nice about them.", "Share your most embarrassing photo.",
]

async def truth_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, f"💭 <b>Truth:</b> {random.choice(TRUTH_QUESTIONS)}")

async def dare_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply(update, f"😈 <b>Dare:</b> {random.choice(DARES)}")

# ────────────── UTILITY ───────────────────────────────────────────────────────
async def calc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /calc expression")
    expr = " ".join(context.args)
    allowed = set("0123456789+-*/().% ")
    if not all(c in allowed for c in expr):
        return await reply(update, "❌ Invalid characters in expression.")
    try:
        result = eval(expr, {"__builtins__": {}}, {})
        await reply(update, f"🧮 <code>{html.escape(expr)}</code> = <b>{result}</b>")
    except Exception as e:
        await reply(update, f"❌ Error: {e}")

async def qr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /qr text")
    import io, qrcode
    text = " ".join(context.args)
    img = qrcode.make(text)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    await update.message.reply_photo(buf, caption=f"📱 QR Code for: {html.escape(text)}")

async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /tr lang text")
    lang = context.args[0]
    text = " ".join(context.args[1:]) if len(context.args) > 1 else (
        update.message.reply_to_message.text if update.message.reply_to_message else "")
    if not text: return await reply(update, "❌ Provide text to translate.")
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={lang}&dt=t&q={urllib.parse.quote(text)}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json(content_type=None)
                translated = "".join(p[0] for p in data[0] if p[0])
                await reply(update, f"🌐 <b>Translation ({lang}):</b>\n{html.escape(translated)}")
    except Exception as e:
        await reply(update, f"❌ Translation failed: {e}")

async def hash_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /hash text")
    text = " ".join(context.args).encode()
    md5 = hashlib.md5(text).hexdigest()
    sha1 = hashlib.sha1(text).hexdigest()
    sha256 = hashlib.sha256(text).hexdigest()
    await reply(update, f"🔐 <b>Hashes:</b>\nMD5: <code>{md5}</code>\nSHA1: <code>{sha1}</code>\nSHA256: <code>{sha256}</code>")

async def b64_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import base64
    if len(context.args) < 2: return await reply(update, "Usage: /b64 encode|decode text")
    mode = context.args[0].lower()
    text = " ".join(context.args[1:])
    try:
        if mode == "encode":
            result = base64.b64encode(text.encode()).decode()
        else:
            result = base64.b64decode(text.encode()).decode()
        await reply(update, f"<code>{html.escape(result)}</code>")
    except Exception as e:
        await reply(update, f"❌ {e}")

async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /weather city")
    city = " ".join(context.args)
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
                await reply(update, f"🌤️ <b>Weather in {html.escape(area)}:</b>\n"
                           f"🌡️ Temp: {temp_c}°C / {temp_f}°F\n"
                           f"🤔 Feels like: {feels}°C\n"
                           f"📋 {desc}\n"
                           f"💧 Humidity: {humidity}%\n"
                           f"💨 Wind: {wind} km/h")
    except Exception as e:
        await reply(update, f"❌ Weather lookup failed: {e}")

async def time_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tz_str = " ".join(context.args) if context.args else "UTC"
    try:
        tz = pytz.timezone(tz_str)
        now = datetime.datetime.now(tz)
        await reply(update, f"🕐 <b>Time in {html.escape(tz_str)}:</b>\n{now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    except Exception:
        await reply(update, f"❌ Unknown timezone: {tz_str}")

async def reverse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args) if context.args else (
        update.message.reply_to_message.text if update.message.reply_to_message else "")
    if not text: return await reply(update, "Usage: /reverse text")
    await reply(update, f"🔄 {html.escape(text[::-1])}")

async def ascii_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /ascii text")
    text = " ".join(context.args)
    result = " ".join(str(ord(c)) for c in text[:20])
    await reply(update, f"💻 <code>{html.escape(result)}</code>")

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_chat(update.effective_chat.id)
    if not cfg: return await reply(update, "❌ No settings found.")
    lines = [f"⚙️ <b>Settings for {html.escape(update.effective_chat.title or '')}:</b>",
             f"🛡️ Anti-spam: {'✅' if cfg.get('anti_spam') else '❌'}",
             f"🌊 Anti-flood: {'✅' if cfg.get('anti_flood') else '❌'} ({cfg.get('flood_count', 5)} msgs/{cfg.get('flood_time', 5)}s)",
             f"🔗 Anti-link: {'✅' if cfg.get('anti_link') else '❌'}",
             f"📨 Anti-forward: {'✅' if cfg.get('anti_forward') else '❌'}",
             f"🤖 Anti-bot: {'✅' if cfg.get('anti_bot') else '❌'}",
             f"⚡ Anti-raid: {'✅' if cfg.get('anti_raid') else '❌'}",
             f"⚠️ Warn limit: {cfg.get('warn_limit', 3)} → {cfg.get('warn_action', 'mute')}",
             f"👋 Welcome: {'✅' if cfg.get('greetmembers', 1) else '❌'}",
             f"👋 Goodbye: {'✅' if cfg.get('goodbye_enabled', 1) else '❌'}",
             f"📊 Economy: {'✅' if cfg.get('economy_enabled', 1) else '❌'}",
             f"⭐ Reputation: {'✅' if cfg.get('rep_enabled', 1) else '❌'}",
             ]
    await reply(update, "\n".join(lines))

# ────────────── SETTINGS SHORTCUTS ───────────────────────────────────────────
@admin_only
async def cleanservice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "clean_service", 1 if val else 0)
    await reply(update, f"✅ Clean service messages {'enabled' if val else 'disabled'}")

@admin_only
async def delcommands_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "delete_commands", 1 if val else 0)
    await reply(update, f"✅ Delete commands {'enabled' if val else 'disabled'}")

@admin_only
async def welcdel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "Usage: /welcdel seconds (0 to disable)")
    set_setting(update.effective_chat.id, "welcome_delete_after", int(context.args[0]))
    await reply(update, f"✅ Welcome messages will be deleted after <b>{context.args[0]}s</b>")

# ────────────── SCHEDULE ──────────────────────────────────────────────────────
@admin_only
async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2: return await reply(update, "Usage: /schedule 1h Your message")
    time_str = context.args[0]
    message = " ".join(context.args[1:])
    duration = parse_duration(time_str)
    if not duration: return await reply(update, "❌ Invalid time. Use: 1m, 1h, 1d")
    next_run = datetime.datetime.now(pytz.utc) + duration
    db = get_db()
    db.execute("INSERT INTO schedules (chat_id, message, next_run, created_by) VALUES (?,?,?,?)",
               (update.effective_chat.id, message, next_run.isoformat(), update.effective_user.id))
    db.commit(); db.close()
    await reply(update, f"✅ Message scheduled for <b>{time_str}</b> from now.")

async def run_scheduler(context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    now = datetime.datetime.now(pytz.utc)
    rows = db.execute("SELECT * FROM schedules WHERE is_active=1 AND next_run<=?", (now.isoformat(),)).fetchall()
    for row in rows:
        try:
            await context.bot.send_message(row["chat_id"], row["message"], parse_mode="HTML")
        except:
            pass
        if row["repeat"] == "none":
            db.execute("UPDATE schedules SET is_active=0 WHERE id=?", (row["id"],))
        else:
            interval = datetime.timedelta(seconds=row["repeat_val"])
            next_run = now + interval
            db.execute("UPDATE schedules SET next_run=? WHERE id=?", (next_run.isoformat(), row["id"]))
    db.commit(); db.close()

# ────────────── AFK HANDLER ──────────────────────────────────────────────────
async def handle_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await afk_check_handler(update, context)

# ────────────── INLINE QUERY ─────────────────────────────────────────────────
async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.inline_query.query
    results = []
    if not q:
        results.append(InlineQueryResultArticle(
            id="1",
            title="🤖 UltraGroupManager",
            description="Type to search notes or get info",
            input_message_content=InputTextMessageContent(f"🤖 UltraGroupManager v{VERSION} — Advanced group management bot!")
        ))
    else:
        results.append(InlineQueryResultArticle(
            id="q",
            title=f"🔍 Search: {q}",
            description="Send this search query",
            input_message_content=InputTextMessageContent(q)
        ))
    await update.inline_query.answer(results, cache_time=5)

# ────────────── BACKUP / RESTORE ─────────────────────────────────────────────
@admin_only
async def backup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    import io
    buf = io.BytesIO(json.dumps(data, indent=2, default=str).encode())
    buf.name = f"backup_{chat_id}.json"
    await update.message.reply_document(buf, caption=f"✅ Backup for {html.escape(update.effective_chat.title or '')}")

# ────────────── LEAVE ─────────────────────────────────────────────────────────
@owner_only
async def leave_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and update.effective_chat.type == "private":
        return await reply(update, "Usage: /leave [chat_id]")
    target_id = int(context.args[0]) if context.args else update.effective_chat.id
    try:
        await context.bot.leave_chat(target_id)
        if target_id != update.effective_chat.id:
            await reply(update, f"✅ Left chat {target_id}")
    except Exception as e:
        await reply(update, f"❌ {e}")

# ────────────── CHATLIST ──────────────────────────────────────────────────────
@owner_only
async def chatlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    rows = db.execute("SELECT chat_id, title, chat_type FROM chats ORDER BY title LIMIT 30").fetchall()
    db.close()
    lines = [f"💬 <b>Bot is in {len(rows)} chats:</b>"]
    for r in rows:
        lines.append(f"• {html.escape(r['title'] or 'Unknown')} (<code>{r['chat_id']}</code>) [{r['chat_type']}]")
    await reply(update, "\n".join(lines))

# ────────────── HANDLE MEMBER UPDATES ────────────────────────────────────────
async def chat_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result: return
    chat = result.chat
    ensure_chat(chat)

# ────────────── GBAN CHECK ON JOIN ────────────────────────────────────────────
async def check_gban_on_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Called from welcome_handler — checks gban"""
    pass  # Already handled in welcome_handler

# ────────────── MAIN MESSAGE HANDLER ─────────────────────────────────────────
async def main_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user or not update.effective_chat: return
    if update.effective_chat.type == "private": return

    user = update.effective_user
    chat = update.effective_chat
    ensure_chat(chat)
    ensure_user(user)

    # Gban check
    reason = is_gbanned(user.id)
    if reason:
        try:
            await context.bot.ban_chat_member(chat.id, user.id)
            await context.bot.send_message(chat.id, f"🌍 Globally banned user removed.\nReason: {html.escape(reason)}", parse_mode="HTML")
            return
        except:
            pass

    # AFK check
    await afk_check_handler(update, context)

    # Anti-spam
    await antispam_handler(update, context)

    # Blacklist
    await blacklist_handler(update, context)

    # Filters
    await filter_handler(update, context)

    # Hash notes (#name)
    await hash_note_handler(update, context)

    # Tag admins
    if update.message.text and ("@admins" in update.message.text.lower() or "@admin" in update.message.text.lower()):
        await tag_admins_handler(update, context)

    # Rep via +rep text
    if update.message.text and update.message.text.strip() in ("+rep", "+1") and update.message.reply_to_message:
        await rep_cmd(update, context)

    # Delete commands
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
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help menu"),
        BotCommand("ban", "Ban a user"),
        BotCommand("tban", "Temp ban a user"),
        BotCommand("sban", "Silent ban"),
        BotCommand("unban", "Unban a user"),
        BotCommand("kick", "Kick a user"),
        BotCommand("skick", "Silent kick"),
        BotCommand("mute", "Mute a user"),
        BotCommand("tmute", "Temp mute"),
        BotCommand("unmute", "Unmute a user"),
        BotCommand("warn", "Warn a user"),
        BotCommand("dwarn", "Warn and delete message"),
        BotCommand("swarn", "Silent warn"),
        BotCommand("unwarn", "Remove a warn"),
        BotCommand("resetwarn", "Reset all warns"),
        BotCommand("warns", "Show warns"),
        BotCommand("promote", "Promote a user"),
        BotCommand("demote", "Demote a user"),
        BotCommand("admintitle", "Set admin title"),
        BotCommand("adminlist", "List all admins"),
        BotCommand("zombies", "Count zombie accounts"),
        BotCommand("kickzombies", "Kick zombie accounts"),
        BotCommand("pin", "Pin a message"),
        BotCommand("unpin", "Unpin a message"),
        BotCommand("unpinall", "Unpin all messages"),
        BotCommand("purge", "Purge messages"),
        BotCommand("del", "Delete a message"),
        BotCommand("lock", "Lock a message type"),
        BotCommand("unlock", "Unlock a message type"),
        BotCommand("locks", "Show lock status"),
        BotCommand("antispam", "Toggle anti-spam"),
        BotCommand("antiflood", "Toggle anti-flood"),
        BotCommand("setflood", "Set flood limit"),
        BotCommand("setfloodaction", "Set flood action"),
        BotCommand("antilink", "Toggle anti-link"),
        BotCommand("antiforward", "Toggle anti-forward"),
        BotCommand("antibot", "Toggle anti-bot"),
        BotCommand("antiraid", "Toggle anti-raid"),
        BotCommand("setwelcome", "Set welcome message"),
        BotCommand("setgoodbye", "Set goodbye message"),
        BotCommand("welcome", "Toggle welcome"),
        BotCommand("goodbye", "Toggle goodbye"),
        BotCommand("setrules", "Set rules"),
        BotCommand("rules", "Show rules"),
        BotCommand("save", "Save a note"),
        BotCommand("get", "Get a note"),
        BotCommand("notes", "List all notes"),
        BotCommand("clear", "Delete a note"),
        BotCommand("filter", "Add a filter"),
        BotCommand("filters", "List filters"),
        BotCommand("stop", "Remove a filter"),
        BotCommand("addbl", "Add to blacklist"),
        BotCommand("unblacklist", "Remove from blacklist"),
        BotCommand("blacklist", "Show blacklist"),
        BotCommand("report", "Report a message"),
        BotCommand("afk", "Set AFK status"),
        BotCommand("gban", "Global ban"),
        BotCommand("ungban", "Remove global ban"),
        BotCommand("broadcast", "Broadcast message"),
        BotCommand("stats", "Bot statistics"),
        BotCommand("id", "Get user/chat ID"),
        BotCommand("info", "Get user info"),
        BotCommand("chatinfo", "Get chat info"),
        BotCommand("ping", "Ping the bot"),
        BotCommand("uptime", "Show uptime"),
        BotCommand("settings", "View settings"),
        BotCommand("daily", "Claim daily coins"),
        BotCommand("coins", "Check balance"),
        BotCommand("mine", "Mine coins"),
        BotCommand("give", "Transfer coins"),
        BotCommand("rob", "Rob coins"),
        BotCommand("flip", "Flip a coin"),
        BotCommand("slots", "Slot machine"),
        BotCommand("leaderboard", "Coins leaderboard"),
        BotCommand("rep", "Give reputation"),
        BotCommand("reprank", "Rep leaderboard"),
        BotCommand("newfed", "Create federation"),
        BotCommand("joinfed", "Join a federation"),
        BotCommand("leavefed", "Leave federation"),
        BotCommand("fban", "Federation ban"),
        BotCommand("unfban", "Federation unban"),
        BotCommand("fedinfo", "Federation info"),
        BotCommand("fedbans", "List federation bans"),
        BotCommand("connect", "Connect to a group"),
        BotCommand("disconnect", "Disconnect from group"),
        BotCommand("connected", "Show connection"),
        BotCommand("calc", "Calculator"),
        BotCommand("qr", "Generate QR code"),
        BotCommand("tr", "Translate text"),
        BotCommand("hash", "Hash text"),
        BotCommand("b64", "Base64 encode/decode"),
        BotCommand("weather", "Check weather"),
        BotCommand("time", "Current time"),
        BotCommand("reverse", "Reverse text"),
        BotCommand("8ball", "Magic 8-ball"),
        BotCommand("roll", "Roll a dice"),
        BotCommand("slap", "Slap a user"),
        BotCommand("hug", "Hug a user"),
        BotCommand("ship", "Ship compatibility"),
        BotCommand("roast", "Roast a user"),
        BotCommand("compliment", "Compliment a user"),
        BotCommand("joke", "Random joke"),
        BotCommand("truth", "Truth question"),
        BotCommand("dare", "Dare challenge"),
        BotCommand("schedule", "Schedule a message"),
        BotCommand("backup", "Export chat backup"),
        BotCommand("setwarnlimit", "Set warn limit"),
        BotCommand("setwarnaction", "Set warn action"),
        BotCommand("cleanservice", "Toggle clean service msgs"),
        BotCommand("delcommands", "Toggle delete commands"),
        BotCommand("welcdel", "Set welcome delete time"),
        BotCommand("chatlist", "List all chats"),
        BotCommand("sudo", "Add sudo user"),
        BotCommand("unsudo", "Remove sudo user"),
        BotCommand("leave", "Leave a chat"),
    ]

async def post_init(application: Application):
    try:
        await application.bot.set_my_commands(build_commands())
        info = await application.bot.get_me()
        logger.info(f"✅ {info.first_name} (@{info.username}) initialized with {len(build_commands())} commands")
    except Exception as e:
        logger.error(f"Post-init error: {e}")

def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set!")
        sys.exit(1)

    init_db()
    logger.info(f"🤖 Starting UltraGroupManager v{VERSION}")

    app = (Application.builder()
           .token(BOT_TOKEN)
           .post_init(post_init)
           .build())

    # ── Handlers ──────────────────────────────────────────────────────────────
    # Core
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
    app.add_handler(CommandHandler("backup", backup_cmd))
    app.add_handler(CommandHandler("leave", leave_cmd))
    app.add_handler(CommandHandler("schedule", schedule_cmd))

    # Economy
    app.add_handler(CommandHandler("daily", daily_cmd))
    app.add_handler(CommandHandler("coins", coins_cmd))
    app.add_handler(CommandHandler("balance", coins_cmd))
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

    logger.info("🚀 Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
