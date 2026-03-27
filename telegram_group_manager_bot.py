#!/usr/bin/env python3
"""
Nexus Bot v10.0 — Ultra Advanced Telegram Group Manager
Modern · Animated · Cute · Powerful · AI-Powered
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
BOT_TOKEN       = os.environ.get("TELEGRAM_BOT_TOKEN", "8159930920:AAGS4XWy9Fslq0RnRvFvx6QNTg9eTT5AqOo")
OWNER_IDS       = [int(x) for x in os.environ.get("OWNER_IDS", "7012373095").split(",") if x.strip().isdigit()]
LOG_CHANNEL     = int(os.environ.get("LOG_CHANNEL_ID", "0") or 0)
GBAN_LOG        = int(os.environ.get("GBAN_LOG_CHANNEL", "0") or 0)
DB_PATH         = os.environ.get("DB_PATH", "bot_data.db")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")   # free key → aistudio.google.com/app/apikey
VERSION         = "10.0.0-NEXUS"
START_TIME      = datetime.datetime.now(pytz.utc)

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
mine_cd:          Dict[int, float]   = {}
daily_cd:         Dict[int, float]   = {}
_ai_api_index:    int                = 0      # rotating AI API index

# ─── Speed Caches (performance critical) ─────────────────────────────────────
# Admin cache: chat_id → (user_id → ChatMember, timestamp)
_admin_cache:   Dict[int, Tuple[dict, float]] = {}
_ADMIN_TTL:     float = 300.0   # refresh every 5 minutes

# Chat config cache: chat_id → (config_dict, timestamp)
_chat_cfg_cache: Dict[int, Tuple[dict, float]] = {}
_CHAT_CFG_TTL:   float = 30.0   # refresh every 30 seconds

# gban cache: user_id → (reason_or_None, timestamp)
_gban_cache:    Dict[int, Tuple[Optional[str], float]] = {}
_GBAN_TTL:      float = 120.0   # refresh every 2 minutes

# Persistent HTTP session (created on first use)
_http_session: Optional[aiohttp.ClientSession] = None

def _get_http_session() -> aiohttp.ClientSession:
    """Return a long-lived aiohttp session (created lazily, reused always)."""
    global _http_session
    if _http_session is None or _http_session.closed:
        connector = aiohttp.TCPConnector(
            limit=20, ttl_dns_cache=300, ssl=False,
            keepalive_timeout=30
        )
        _http_session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=10),
            headers={"User-Agent": "NexusBot/9.0"},
        )
    return _http_session

# ═══════════════════════════════════════════════════════════════════════════════
#              💀 GEN Z ANIMATION & VIBE SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

# Kaomoji pools by vibe category
KAOMOJI_BAN       = ["(╯°□°）╯︵ ┻━┻", "ψ(`∇`)ψ", "(ง ͠° ͟ل͜ ͡°)ง", "٩(ఠ益ఠ)۶", "(҂◡_◡) ᕤ", "(ꐦ°᷄д°᷅)"]
KAOMOJI_HYPE      = ["\\(★ω★)/", "(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧", "(*≧ω≦)", "٩(◕‿◕｡)۶", "\\(^▽^)/", "ヽ(o＾▽＾o)ノ"]
KAOMOJI_SAD       = ["(；ω；)", "(╥_╥)", "｡ﾟ(ﾟ`Д`)ﾟ｡", "(っ˘̩╭╮˘̩)っ", "(T_T)", "( ≧Д≦)"]
KAOMOJI_MONEY     = ["(ﾉ≧∀≦)ﾉ", "(*＾▽＾)ノ", "\\(★ω★)/", "ヾ(≧▽≦*)o", "(⌐■_■)💰", "꒰◍ᐡ◡ᐡ◍꒱"]
KAOMOJI_WHOLESOME = ["(っ◔◡◔)っ ♥", "(ﾉ◕ヮ◕)ﾉ", "(｡♥‿♥｡)", "( ˘ ³˘)♥", "(づ｡◕‿‿◕｡)づ", "ʕっ•ᴥ•ʔっ"]
KAOMOJI_FLEX      = ["(`• ω •`)", "( •̀ ω •́ )✧", "ᕙ(⇀‸↼‶)ᕗ", "(⌐■_■)", "( ᐛ )و", "¯\\_(ツ)_/¯"]
KAOMOJI_VIBE      = ["(￣▽￣)ノ", "(｡•̀ᴗ-)✧", "(*˘︶˘*).｡.:*♡", "( ᐛ )و", "~(˘▾˘~)", "✧˖°(◍•ᴗ•◍)°˖✧"]
KAOMOJI_THINK     = ["(°ロ°)", "∑(O_O；)", "(⊙_☉)", "(*°△°*)", "Σ(･ω･ノ)ノ", "(￢_￢;)"]
KAOMOJI_WIN       = ["(ﾉ≧∀≦)ﾉ　ＹＡＹ！", "\\(★ω★)/", "٩(ˊᗜˋ*)و", "(⌐■_■)", "(*≧∀≦*)", "\\(◕ ‿ ◕)/"]
KAOMOJI_LOSE      = ["(╥_╥)", "（；д；）", "(ﾒ` ﾛ `)ﾒ", "(¬_¬)", "(-_-;)", "눈_눈"]
KAOMOJI_FIRE      = ["(🔥ω🔥)", "( •̀ᴗ•́ )و ̑̑🔥", "ψ(*`ー`)ψ🔥", "( ͡° ͜ʖ ͡°)🔥", "(っ▀¯▀)つ🔥"]

GEN_Z_PHRASES = [
    "no cap fr fr", "periodt bestie", "it's giving slay", "understood the assignment",
    "ngl tho", "lowkey ate this one", "main character energy", "not the bot going off",
    "ate and left no crumbs", "we don't miss bestie", "that's so bussin",
    "rent free in my head", "based and valid", "W moment", "slay era activated",
    "living for this", "real ones know", "zero cap rn", "the vibes are immaculate",
]

GEN_Z_LOADING = [
    "⌛ brb one sec bestie...",
    "💫 loading no cap...",
    "🔄 hold tf on fr fr...",
    "✨ giving moment hold on...",
    "⚡ processing like a serve...",
    "🌀 slay wait a sec...",
    "💅 lemme cook bestie...",
    "🎯 on it fr no cap...",
]

# Tenor GIF cache and search terms
_gif_cache: Dict[str, List[str]] = {}
TENOR_KEY = "LIVDSRZULELA"
GIF_SEARCHES = {
    "ban":        "anime ban hammer gif",
    "kick":       "anime kick gif",
    "mute":       "anime silence shh gif",
    "warn":       "anime point finger gif",
    "unban":      "anime welcome back gif",
    "promote":    "anime celebrate promotion gif",
    "start":      "anime wave hello gif",
    "win":        "anime celebrate happy gif",
    "lose":       "anime cry sad gif",
    "hug":        "anime hug gif",
    "slap":       "anime slap gif",
    "kiss":       "anime kiss gif",
    "pat":        "anime headpat gif",
    "poke":       "anime poke gif",
    "daily":      "anime money cash gif",
    "work":       "anime working hard gif",
    "slots":      "anime slot machine gif",
    "flip":       "anime coin flip gif",
    "mine":       "anime digging gif",
    "roast":      "anime roast savage gif",
    "trivia":     "anime thinking gif",
    "wyr":        "anime hmm think gif",
    "hype":       "anime hype gif",
    "dance":      "anime dance gif",
    "vibe":       "anime vibes good gif",
    "robbery":    "anime heist gif",
}

async def fetch_gif(category: str) -> Optional[str]:
    """Fetch a random GIF URL from Tenor for the given category, with caching."""
    if category in _gif_cache and _gif_cache[category]:
        return random.choice(_gif_cache[category])
    search = GIF_SEARCHES.get(category, "anime reaction gif")
    try:
        url = (
            f"https://tenor.googleapis.com/v2/search"
            f"?q={urllib.parse.quote(search)}&key={TENOR_KEY}"
            f"&limit=20&media_filter=gif&contentfilter=medium"
        )
        sess = _get_http_session()
        async with sess.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
            if r.status == 200:
                data = await r.json()
                urls = [
                    result["media_formats"]["gif"]["url"]
                    for result in data.get("results", [])
                    if "gif" in result.get("media_formats", {})
                ]
                if urls:
                    _gif_cache[category] = urls
                    return random.choice(urls)
    except Exception as ex:
        logger.debug(f"fetch_gif [{category}]: {ex}")
    return None

async def send_gif_reply(update: Update, category: str, caption: str,
                         reply_markup=None) -> Optional[Message]:
    """Send an animated GIF with caption; fall back to text if GIF unavailable."""
    gif_url = await fetch_gif(category)
    if gif_url:
        try:
            return await update.message.reply_animation(
                gif_url, caption=caption, parse_mode="HTML",
                reply_markup=reply_markup
            )
        except Exception as ex:
            logger.debug(f"send_gif_reply failed gif send: {ex}")
    try:
        return await update.message.reply_text(
            caption, parse_mode="HTML", reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception as ex:
        logger.debug(f"send_gif_reply fallback: {ex}")
    return None

# ─── AI HELPER (Custom API) ───────────────────────────────────────────────────
_CUSTOM_AI_URL = "https://sheikhhridoy.hstn.me/gpt-4.php"

# Gen Z suffix phrases added to AI responses for personality
_AI_SUFFIXES = [
    " no cap fr fr 💀", " periodt bestie ✨", " lowkey ate this one 🔥",
    " understood the assignment 👑", " ngl tho 😭", " main character energy 💅",
    " we don't miss bestie 🙌", " that's so bussin fr 🤩", " rent free in my head 💭",
    " based and valid ⚡", " W moment 🏆", " slay era activated ✨",
    " zero cap rn 🫡", " the vibes are immaculate 🌟", " real ones know 💯",
    " ate and left no crumbs 🔥", "", "", "",  # blank entries = undecorated (weighted)
]

# Emoji openers to randomly prefix AI messages
_AI_OPENERS = [
    "✨", "🔥", "💀", "😭", "👑", "💅", "⚡", "🌟", "🫡", "🤩",
    "🙌", "💯", "🎯", "🌈", "🚀", "", "", "",
]

_POLLINATIONS_URL = "https://text.pollinations.ai/"
_OPENROUTER_URL   = "https://openrouter.ai/api/v1/chat/completions"

_AI_APIS = [
    "pollinations",
    "custom",
    "gemini",
]

async def _try_pollinations(prompt: str, timeout: float = 7.0) -> str:
    """Pollinations AI — completely free, no key required."""
    try:
        safe_prompt = urllib.parse.quote(prompt, safe="")
        url = f"{_POLLINATIONS_URL}{safe_prompt}"
        sess = _get_http_session()
        async with sess.get(url, timeout=aiohttp.ClientTimeout(total=timeout),
                            headers={"User-Agent": "NexusBot/10.0"}) as resp:
            if resp.status == 200:
                text = (await resp.text()).strip()
                if text and len(text) > 2:
                    return text
    except Exception as ex:
        logger.debug(f"pollinations_ai: {ex}")
    return ""

async def _try_custom_api(prompt: str, timeout: float = 6.0) -> str:
    """Custom GPT-4 API endpoint."""
    try:
        encoded = urllib.parse.quote(prompt, safe="")
        url = f"{_CUSTOM_AI_URL}?q={encoded}"
        sess = _get_http_session()
        async with sess.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                raw = await resp.text()
                text = ""
                try:
                    data = json.loads(raw)
                    for key in ("response", "reply", "answer", "result",
                                "text", "content", "message", "output"):
                        if isinstance(data, dict) and data.get(key):
                            text = str(data[key]).strip()
                            break
                    if not text and isinstance(data, dict):
                        for v in data.values():
                            if isinstance(v, str) and v.strip():
                                text = v.strip()
                                break
                    if not text and isinstance(data, str):
                        text = data.strip()
                except (json.JSONDecodeError, ValueError):
                    text = raw.strip()
                if text and len(text) > 2:
                    return text
    except Exception as ex:
        logger.debug(f"custom_ai: {ex}")
    return ""

async def _try_gemini(prompt: str, timeout: float = 8.0) -> str:
    """Gemini AI — requires GEMINI_API_KEY."""
    if not GEMINI_API_KEY:
        return ""
    try:
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}")
        payload = {"contents": [{"parts": [{"text": prompt}]}],
                   "generationConfig": {"maxOutputTokens": 200, "temperature": 0.9}}
        sess = _get_http_session()
        async with sess.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if text and len(text) > 2:
                        return text
                except (KeyError, IndexError):
                    pass
    except Exception as ex:
        logger.debug(f"gemini_ai: {ex}")
    return ""

async def ai_reply(prompt: str, fallback: str = "", timeout: float = 7.0,
                   max_tokens: int = 200) -> str:
    """
    Multi-API AI engine with automatic rotating failover:
    1. Pollinations AI (free, no key)
    2. Custom GPT-4 endpoint
    3. Gemini API (if key set)
    Falls back gracefully to `fallback` string if all APIs fail.
    """
    global _ai_api_index
    apis = [
        lambda: _try_pollinations(prompt, timeout),
        lambda: _try_custom_api(prompt, timeout),
        lambda: _try_gemini(prompt, timeout),
    ]
    start_idx = _ai_api_index % len(apis)
    for i in range(len(apis)):
        idx = (start_idx + i) % len(apis)
        try:
            text = await apis[idx]()
            if text:
                _ai_api_index = (idx + 1) % len(apis)
                opener = random.choice(_AI_OPENERS)
                suffix = random.choice(_AI_SUFFIXES)
                return f"{opener} {text}{suffix}".strip()
        except Exception as ex:
            logger.debug(f"ai_reply api[{idx}]: {ex}")
    return fallback

async def ai_ask(question: str, timeout: float = 10.0) -> str:
    """Direct AI Q&A without Gen Z decoration — for /ask command."""
    global _ai_api_index
    apis = [
        lambda: _try_pollinations(question, timeout),
        lambda: _try_custom_api(question, timeout),
        lambda: _try_gemini(question, timeout),
    ]
    start_idx = _ai_api_index % len(apis)
    for i in range(len(apis)):
        idx = (start_idx + i) % len(apis)
        try:
            text = await apis[idx]()
            if text:
                _ai_api_index = (idx + 1) % len(apis)
                return text.strip()
        except Exception as ex:
            logger.debug(f"ai_ask api[{idx}]: {ex}")
    return "🤖 AI is taking a nap rn, try again in a sec bestie 😴"

def kmo(pool: List[str]) -> str:
    """Pick a random kaomoji from a pool."""
    return random.choice(pool)

def gz() -> str:
    """Return a random Gen Z phrase."""
    return random.choice(GEN_Z_PHRASES)

async def animate_loading(update: Update, label: str = "Processing") -> Optional[Message]:
    """Fast single-message loading placeholder — no delays, instant response."""
    try:
        return await update.message.reply_text(
            f"{kmo(KAOMOJI_VIBE)}\n<b>{random.choice(GEN_Z_LOADING)}</b>",
            parse_mode="HTML"
        )
    except:
        return None

async def send_loading(update: Update, text: str = None) -> Optional[Message]:
    k = kmo(KAOMOJI_VIBE)
    msg_text = text or f"{k}\n<b>brb bestie no cap...</b>"
    try:
        return await update.message.reply_text(msg_text, parse_mode="HTML")
    except:
        return None

async def finish_anim(m: Optional[Message], text: str, reply_markup=None) -> None:
    if not m: return
    try:
        await m.edit_text(text, parse_mode="HTML", reply_markup=reply_markup,
                          disable_web_page_preview=True)
    except Exception as ex:
        logger.debug(f"finish_anim: {ex}")

SPARKLE_FRAMES = ["✦", "✧", "⋆", "★", "☆", "✨", "💫", "🌟"]
HEART_FRAMES   = ["💗", "💖", "💝", "💘", "💓", "💕"]
DOT_FRAMES     = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# ─── UI HELPERS ───────────────────────────────────────────────────────────────
def div() -> str:
    """Decorative divider line (used before _D is defined)."""
    return "  <code>·──────────────────────·</code>"

def progress_bar(current: int, maximum: int, length: int = 10) -> str:
    """Return a Unicode block progress bar string."""
    maximum = max(maximum, 1)
    current = max(0, min(current, maximum))
    filled  = int(round(length * current / maximum))
    empty   = length - filled
    return "█" * filled + "░" * empty

def level_from_msgs(msgs: int) -> int:
    """Calculate level from total message count (level 1 = 0-99 msgs)."""
    return max(1, 1 + int(msgs / 100))

_LEVEL_TITLES = [
    "Newcomer", "Regular", "Active", "Chatty", "Social Butterfly",
    "Veteran", "Legend", "Elite", "Master", "Grand Master",
    "Champion", "Immortal", "God Tier", "Mythic", "Nexus God",
]

def level_title(lvl: int) -> str:
    """Return a title string for the given level number."""
    idx = min(lvl - 1, len(_LEVEL_TITLES) - 1)
    return _LEVEL_TITLES[max(0, idx)]

_RANK_BADGES = {1: "🥇", 2: "🥈", 3: "🥉"}

def rank_badge(rank: int) -> str:
    """Return an emoji badge for the given rank position."""
    return _RANK_BADGES.get(rank, f"#{rank}")

def stars_bar(count: int, max_stars: int = 5) -> str:
    """Return a filled/empty star bar string."""
    count     = max(0, min(count, max_stars))
    max_stars = max(1, max_stars)
    return "⭐" * count + "☆" * (max_stars - count)

# ═══════════════════════════════════════════════════════════════════════════════
#                          DATABASE
# ═══════════════════════════════════════════════════════════════════════════════
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-32000")   # 32 MB page cache
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA mmap_size=134217728")  # 128 MB mmap
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

    c.execute("""INSERT OR IGNORE INTO shop_items (id, name, description, price, effect)
                 VALUES
                 (1, '⭐ VIP Badge', 'Show your VIP status', 5000, 'vip'),
                 (2, '🔥 Flame Badge', 'Hot member badge', 2500, 'flame'),
                 (3, '💎 Diamond Badge', 'Diamond member status', 10000, 'diamond'),
                 (4, '🎭 Jester Hat', 'For the fun ones', 1000, 'jester'),
                 (5, '🛡️ Shield', 'Protection badge', 3000, 'shield')""")

    db.commit(); db.close()
    logger.info("✅ Database initialized (v9.0 NEXUS)")

# ─── DB helpers ───────────────────────────────────────────────────────────────
def get_chat(chat_id: int) -> dict:
    now = time.time()
    entry = _chat_cfg_cache.get(chat_id)
    if entry and (now - entry[1]) < _CHAT_CFG_TTL:
        return entry[0]
    db = get_db()
    row = db.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
    db.close()
    cfg = dict(row) if row else {}
    _chat_cfg_cache[chat_id] = (cfg, now)
    return cfg

def invalidate_chat_cache(chat_id: int):
    """Force next get_chat() to re-read from DB."""
    _chat_cfg_cache.pop(chat_id, None)

def ensure_chat(chat: Chat):
    db = get_db()
    db.execute("INSERT OR IGNORE INTO chats (chat_id, title, chat_type) VALUES (?,?,?)",
               (chat.id, chat.title or "", chat.type))
    db.execute("UPDATE chats SET title=?, updated_at=CURRENT_TIMESTAMP WHERE chat_id=?",
               (chat.title or "", chat.id))
    db.commit(); db.close()
    invalidate_chat_cache(chat.id)

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
    invalidate_chat_cache(chat_id)

def log_action(chat_id: int, admin_id: int, action: str, target_id: int = None,
               reason: str = None, extra: str = None):
    db = get_db()
    db.execute("INSERT INTO admin_logs (chat_id, admin_id, action, target_id, reason, extra) VALUES (?,?,?,?,?,?)",
               (chat_id, admin_id, action, target_id, reason, extra))
    db.commit(); db.close()

def is_gbanned(user_id: int) -> Optional[str]:
    now = time.time()
    entry = _gban_cache.get(user_id)
    if entry and (now - entry[1]) < _GBAN_TTL:
        return entry[0]
    db = get_db()
    row = db.execute("SELECT gban_reason FROM users WHERE user_id=? AND is_gbanned=1", (user_id,)).fetchone()
    db.close()
    reason = row["gban_reason"] if row else None
    _gban_cache[user_id] = (reason, now)
    return reason

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
async def _fetch_admin_map(context, chat_id: int) -> dict:
    """Fetch all admins for a chat and populate the cache. Returns user_id→ChatMember map."""
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_map = {m.user.id: m for m in admins}
        _admin_cache[chat_id] = (admin_map, time.time())
        return admin_map
    except Exception as ex:
        logger.debug(f"_fetch_admin_map [{chat_id}]: {ex}")
        return _admin_cache.get(chat_id, ({}, 0))[0]

async def get_admin_map(context, chat_id: int) -> dict:
    """Return cached admin map for chat, refreshing if stale (TTL=5min)."""
    entry = _admin_cache.get(chat_id)
    if entry and (time.time() - entry[1]) < _ADMIN_TTL:
        return entry[0]
    return await _fetch_admin_map(context, chat_id)

def invalidate_admin_cache(chat_id: int):
    """Force next admin check to re-fetch from Telegram."""
    _admin_cache.pop(chat_id, None)

async def get_member(context, chat_id: int, user_id: int):
    """Get a single chat member. Uses admin cache first to avoid extra API calls."""
    admin_map = await get_admin_map(context, chat_id)
    if user_id in admin_map:
        return admin_map[user_id]
    try: return await context.bot.get_chat_member(chat_id, user_id)
    except: return None

async def is_admin(context, chat_id: int, user_id: int) -> bool:
    if is_sudo(user_id): return True
    admin_map = await get_admin_map(context, chat_id)
    return user_id in admin_map

async def is_owner(context, chat_id: int, user_id: int) -> bool:
    if user_id in OWNER_IDS: return True
    admin_map = await get_admin_map(context, chat_id)
    m = admin_map.get(user_id)
    return m is not None and m.status == m.OWNER

async def can_restrict(context, chat_id: int, user_id: int) -> bool:
    if is_sudo(user_id): return True
    admin_map = await get_admin_map(context, chat_id)
    m = admin_map.get(user_id)
    if not m: return False
    if m.status == m.OWNER: return True
    if m.status == m.ADMINISTRATOR and isinstance(m, ChatMemberAdministrator):
        return bool(m.can_restrict_members)
    return False

async def can_pin(context, chat_id: int, user_id: int) -> bool:
    if is_sudo(user_id): return True
    admin_map = await get_admin_map(context, chat_id)
    m = admin_map.get(user_id)
    if not m: return False
    if m.status == m.OWNER: return True
    if m.status == m.ADMINISTRATOR and isinstance(m, ChatMemberAdministrator):
        return bool(m.can_pin_messages)
    return False

async def can_promote(context, chat_id: int, user_id: int) -> bool:
    if is_sudo(user_id): return True
    admin_map = await get_admin_map(context, chat_id)
    m = admin_map.get(user_id)
    if not m: return False
    if m.status == m.OWNER: return True
    if m.status == m.ADMINISTRATOR and isinstance(m, ChatMemberAdministrator):
        return bool(m.can_promote_members)
    return False

# ─── Decorators ───────────────────────────────────────────────────────────────
def admin_only(fn):
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user or not update.effective_chat: return
        if update.effective_chat.type == "private": return await fn(update, context)
        if not await is_admin(context, update.effective_chat.id, update.effective_user.id):
            await update.message.reply_text(
                f"🚫 <b>nuh uh bestie.</b> {kmo(KAOMOJI_BAN)}\n"
                f"<i>this command is admin-only fr fr. no cap.</i>",
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
                "👑 <b>Owner Only</b>\n<i>Restricted to bot owner / sudo users.</i>",
                parse_mode="HTML")
            return
        return await fn(update, context)
    return wrapper

def groups_only(fn):
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat and update.effective_chat.type == "private":
            await update.message.reply_text(
                "👥 <b>Groups Only</b>\n<i>This command works only in groups.</i>",
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

async def get_target(update: Update, context) -> Optional[User]:
    msg = update.message
    if msg and msg.reply_to_message:
        return msg.reply_to_message.from_user
    if context.args:
        arg = context.args[0].lstrip("@")
        if arg.lstrip("-").isdigit():
            uid = int(arg)
            return type("FakeUser", (), {
                "id": uid, "first_name": str(uid), "username": None,
                "last_name": None, "is_bot": False
            })()
        else:
            # Resolve @username via Telegram API
            try:
                chat = await context.bot.get_chat(f"@{arg}")
                return type("FakeUser", (), {
                    "id": chat.id,
                    "first_name": chat.first_name or chat.title or arg,
                    "username": chat.username,
                    "last_name": getattr(chat, "last_name", None),
                    "is_bot": False,
                })()
            except Exception as ex:
                logger.debug(f"get_target: username @{arg} lookup failed: {ex}")
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
#                    🚀 START / HELP
# ═══════════════════════════════════════════════════════════════════════════════
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📖 Help", url=f"https://t.me/{context.bot.username}?start=help"),
            InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{context.bot.username}?startgroup=true"),
        ]])
        await reply(update,
            f"⚡ <b>NEXUS BOT v10.0 IS LIVE</b> {kmo(KAOMOJI_HYPE)}\n"
            f"🤖 <i>AI-powered · Ultra-advanced · Never sleeps</i>\n"
            f"📖 /help · ⚙️ /settings · 🤖 /ask anything\n"
            f"<i>{random.choice(GEN_Z_PHRASES)}</i>",
            reply_markup=kb)
        return

    m = await animate_loading(update, "Powering up")
    name = html.escape(update.effective_user.first_name or "Friend")

    ai_greeting, _ = await asyncio.gather(
        ai_reply(
            f"Write one warm, hype Gen Z welcome sentence for someone named {name} starting a Telegram bot. "
            "Make it feel premium and exciting. 1 sentence, max 15 words, emojis. No intro. Plain text only.",
            fallback=f"you just unlocked the most advanced Telegram bot ever made bestie fr no cap 🔥",
        ),
        asyncio.sleep(0),
    )

    text = (
        f"✨ <b>NEXUS BOT v10.0</b> — hey {name[:20]}!\n"
        f"{_D}\n"
        f"<i>{html.escape(ai_greeting)}</i>\n"
        f"{_D}\n"
        f"🛡️ <b>Moderation</b> — ban mute warn kick promote purge\n"
        f"🚫 <b>Auto-Protection</b> — anti-spam flood raid NSFW CAS\n"
        f"📝 <b>Notes & Filters</b> — smart auto-replies, regex\n"
        f"🌐 <b>Federation</b> — cross-group ban network\n"
        f"💰 <b>Economy</b> — mine work daily rob flip slots shop\n"
        f"⛏️ <b>Mining</b> — 6 ore tiers, jackpots, cave-ins!\n"
        f"🤖 <b>AI Engine</b> — 3 free APIs, always on, /ask anything\n"
        f"🎮 <b>Games</b> — trivia ship truth dare wyr 8ball\n"
        f"🏆 <b>Levels & Ranks</b> — XP leaderboard reputation\n"
        f"{_D}\n"
        f"✅ <b>All 300+ features fully synced.</b> {kmo(KAOMOJI_HYPE)}"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📖 Help Menu", callback_data="help_main"),
         InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{context.bot.username}?startgroup=true")],
        [InlineKeyboardButton("🛡️ Moderation", callback_data="help_mod"),
         InlineKeyboardButton("💰 Economy", callback_data="help_economy")],
        [InlineKeyboardButton("🎮 Games & Fun", callback_data="help_fun"),
         InlineKeyboardButton("🤖 AI Commands", callback_data="help_ai")],
        [InlineKeyboardButton("🔧 Utilities", callback_data="help_util"),
         InlineKeyboardButton("⚙️ Admin Tools", callback_data="help_owner")],
    ])
    await finish_anim(m, text, reply_markup=kb)

# ─── HELP SYSTEM ──────────────────────────────────────────────────────────────
_D = "  <code>·──────────────────────·</code>"

HELP_SECTIONS = {
    "help_main": (
        f"🤖 <b>NEXUS BOT v10.0 — Help Center</b>\n{_D}\n"
        f"<i>AI-powered · 300+ commands · Always on</i>\n\n"
        "📂 <b>Choose a category below:</b>",
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
             InlineKeyboardButton("🤖 AI Commands", callback_data="help_ai")],
            [InlineKeyboardButton("🔧 Utilities", callback_data="help_util"),
             InlineKeyboardButton("⚙️ Admin Tools", callback_data="help_owner")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="help_settings"),
             InlineKeyboardButton("👑 Admin/Owner", callback_data="help_admin")],
        ]
    ),
    "help_mod": (
        "🛡️ <b>Moderation Commands</b>\n" + _D + "\n\n"
        "🔨 <b>BAN</b>\n"
        "<code>/ban</code> [reply/@user] [reason]\n"
        "<code>/tban</code> [reply/@user] 1h [reason]\n"
        "<code>/sban</code> — silent ban\n"
        "<code>/unban</code> [reply/@user]\n\n"
        "👢 <b>KICK</b>\n"
        "<code>/kick</code> · <code>/skick</code> (silent)\n\n"
        "🔇 <b>MUTE</b>\n"
        "<code>/mute</code> · <code>/tmute 1h</code> · <code>/unmute</code>\n\n"
        "⚠️ <b>WARN</b>\n"
        "<code>/warn</code> · <code>/dwarn</code> · <code>/swarn</code>\n"
        "<code>/unwarn</code> · <code>/resetwarn</code> · <code>/warns</code>\n\n"
        "👑 <b>PROMOTE / DEMOTE</b>\n"
        "<code>/promote [title]</code> · <code>/demote</code>\n"
        "<code>/admintitle [title]</code> · <code>/adminlist</code>\n\n"
        "🧹 <b>CLEANUP</b>\n"
        "<code>/purge [N]</code> · <code>/del</code> · <code>/slowmode [s]</code>\n"
        "<code>/pin</code> · <code>/unpin</code> · <code>/unpinall</code>\n"
        "<code>/zombies</code> · <code>/kickzombies</code> · <code>@admins</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_protect": (
        "🚫 <b>Protection System</b>\n" + _D + "\n\n"
        "⚙️ <b>TOGGLES</b>\n"
        "<code>/antispam on|off</code> — anti-spam\n"
        "<code>/antiflood on|off</code> — anti-flood\n"
        "<code>/antilink on|off</code> — block links\n"
        "<code>/antiforward on|off</code> — block forwards\n"
        "<code>/antibot on|off</code> — block bots joining\n"
        "<code>/antinsfw on|off</code> — anti-NSFW\n"
        "<code>/antiarabic on|off</code> — block Arabic/RTL\n\n"
        "🚨 <b>RAID PROTECTION</b>\n"
        "<code>/antiraid on|off</code> · <code>/setraid N</code>\n"
        "<code>/cas on|off</code> — CAS integration\n"
        "<code>/restrict on|off</code> — mute new members\n\n"
        "🌊 <b>FLOOD SETTINGS</b>\n"
        "<code>/setflood N [time]</code>\n"
        "<code>/setfloodaction mute|ban|kick</code>\n\n"
        "🛡️ <b>PANEL</b>\n"
        "<code>/protect</code> — interactive panel",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_notes": (
        "📝 <b>Notes System</b>\n" + _D + "\n\n"
        "<code>/save name text</code> — save a note\n"
        "<code>/get name</code> — retrieve a note\n"
        "<code>#name</code> — quick retrieval\n"
        "<code>/notes</code> — list all notes\n"
        "<code>/clear name</code> — delete a note\n"
        "<code>/clearall</code> — delete all notes\n\n"
        "📐 <b>FORMATTING</b>\n"
        "Supports <b>HTML</b> and <i>Markdown</i>\n"
        "Button syntax: <code>[text](url)</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_filters": (
        "🔍 <b>Filters & Blacklist</b>\n" + _D + "\n\n"
        "🔑 <b>AUTO-FILTERS</b>\n"
        "<code>/filter keyword reply text</code>\n"
        "<i>Reply to sticker/photo/gif/video + /filter keyword</i>\n"
        "<code>/filters</code> — list all filters\n"
        "<code>/stop keyword</code> — remove filter\n"
        "<code>/stopall</code> — remove all filters\n"
        "<code>/filter regex:pattern reply</code> — regex\n\n"
        "📎 <b>SUPPORTS ALL MEDIA</b>\n"
        "Sticker · Photo · Video · GIF · Voice · Audio · Document\n\n"
        "🚫 <b>BLACKLIST</b>\n"
        "<code>/addbl word</code> — add to blacklist\n"
        "<code>/rmbl word</code> — remove word\n"
        "<code>/blacklist</code> — view blacklist\n"
        "<code>/blmode delete|warn|mute|ban</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_locks": (
        "🔒 <b>Lock System</b>\n" + _D + "\n\n"
        "📦 <b>LOCK TYPES</b>\n"
        "<code>stickers</code> · <code>gifs</code> · <code>media</code> · <code>polls</code>\n"
        "<code>voice</code> · <code>video</code> · <code>document</code>\n"
        "<code>forward</code> · <code>games</code> · <code>inline</code>\n"
        "<code>url</code> · <code>anon</code> · <code>all</code>\n\n"
        "🔧 <b>COMMANDS</b>\n"
        "<code>/lock type</code> — lock content type\n"
        "<code>/unlock type</code> — unlock content\n"
        "<code>/locks</code> — interactive lock panel",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_welcome": (
        "👋 <b>Welcome & Goodbye</b>\n" + _D + "\n\n"
        "🌸 <b>WELCOME</b>\n"
        "<code>/setwelcome text</code> — set welcome\n"
        "<code>/welcome on|off</code> — toggle\n"
        "<code>/welcdel N</code> — delete after N secs\n"
        "<code>/captcha on|off</code> — verify new members\n\n"
        "👋 <b>GOODBYE</b>\n"
        "<code>/setgoodbye text</code> · <code>/goodbye on|off</code>\n\n"
        "📜 <b>RULES</b>\n"
        "<code>/setrules text</code> · <code>/rules</code>\n\n"
        "🏷️ <b>PLACEHOLDERS</b>\n"
        "<code>{first}</code> <code>{last}</code> <code>{mention}</code>\n"
        "<code>{username}</code> <code>{count}</code> <code>{chatname}</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_fed": (
        "🌐 <b>Federation System</b>\n" + _D + "\n\n"
        "<i>Ban users across multiple groups at once!</i>\n\n"
        "⚙️ <b>MANAGEMENT</b>\n"
        "<code>/newfed name</code> — create federation\n"
        "<code>/delfed</code> — delete your federation\n"
        "<code>/joinfed fed_id</code> — join a federation\n"
        "<code>/leavefed</code> — leave federation\n"
        "<code>/fedinfo</code> — federation info\n\n"
        "🚫 <b>FED BANS</b>\n"
        "<code>/fban user [reason]</code> — fed ban\n"
        "<code>/unfban user</code> — remove fed ban\n"
        "<code>/fedbans</code> — list fed bans\n"
        "<code>/fadmin user</code> — add fed admin\n"
        "<code>/fremove user</code> — remove fed admin",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_connect": (
        "🔗 <b>Connection System</b>\n" + _D + "\n\n"
        "<i>Manage groups from your DMs!</i>\n\n"
        "📡 <b>COMMANDS</b>\n"
        "<code>/connect chat_id</code> — connect to group\n"
        "<code>/disconnect</code> — disconnect\n"
        "<code>/connected</code> — check connection\n\n"
        "📖 <b>HOW IT WORKS</b>\n"
        "1️⃣ Get your group ID with /id in group\n"
        "2️⃣ Send /connect [group_id] in my PM\n"
        "3️⃣ Use all admin commands from DM!",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_ai": (
        "🤖 <b>AI Command Center</b>\n" + _D + "\n\n"
        "⚡ <b>POWERED BY 3 FREE APIS</b>\n"
        "🌸 Pollinations AI · ⚡ GPT-4 · 💎 Gemini\n"
        "<i>Auto-rotates for 100% uptime. Never fails.</i>\n\n"
        "📡 <b>AI COMMANDS</b>\n"
        "<code>/ask question</code> — ask AI anything\n"
        "<code>/aiinfo</code> — check AI engine status\n\n"
        "🎮 <b>AI-POWERED FUN</b>\n"
        "<code>/joke</code> — AI-generated joke\n"
        "<code>/fact</code> — AI random fact\n"
        "<code>/roast @user</code> — AI roast\n"
        "<code>/compliment @user</code> — AI compliment\n"
        "<code>/quote</code> — AI wisdom\n"
        "<code>/meme</code> — AI meme\n"
        "<code>/truth</code> / <code>/dare</code> — AI T&D\n"
        "<code>/wyr</code> — AI would you rather\n"
        "<code>/8ball question</code> — AI magic ball\n\n"
        "💰 <b>AI ECONOMY</b>\n"
        "<i>work, mine, daily — all use AI for unique stories!</i>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_economy": (
        "💰 <b>Economy System</b>\n" + _D + "\n\n"
        "🌱 <b>EARNING</b>\n"
        "<code>/daily</code> — claim daily reward (400–800+)\n"
        "<code>/work</code> — work for coins 1h cooldown (150–1000+)\n"
        "<code>/mine</code> — mine coins 30min cooldown\n\n"
        "⛏️ <b>MINING TIERS</b>\n"
        "🪨 Stone · ⚙️ Iron · 🥇 Gold · 🔮 Amethyst\n"
        "💎 Diamond (600–1500) · 🌟 Nexus Crystal (1500–8000+)\n"
        "<i>Special events: cave-in, double strike, jackpot!</i>\n\n"
        "🏦 <b>BANKING</b>\n"
        "<code>/bank deposit N</code> · <code>/bank withdraw N</code>\n"
        "<code>/bank balance</code>\n\n"
        "🎰 <b>GAMBLING</b>\n"
        "<code>/flip amount</code> — 50/50 coin flip\n"
        "<code>/slots amount</code> — slot machine\n"
        "<code>/rob @user</code> — steal coins\n\n"
        "🤝 <b>SOCIAL</b>\n"
        "<code>/give @user amount</code> · <code>/coins [@user]</code>\n"
        "<code>/shop</code> · <code>/buy item_id</code> · <code>/inventory</code>\n"
        "<code>/leaderboard</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_rep": (
        "⭐ <b>Reputation & Ranks</b>\n" + _D + "\n\n"
        "🎖️ <b>REPUTATION</b>\n"
        "<code>+rep</code> or <code>/rep @user</code> — give +1 rep\n"
        "<code>/checkrep [@user]</code> — check rep\n"
        "<code>/reprank</code> — rep leaderboard\n\n"
        "📊 <b>ACTIVITY RANKS</b>\n"
        "<code>/rank [@user]</code> — rank card\n"
        "<code>/top</code> — most active members\n"
        "<code>/level [@user]</code> — your level\n\n"
        "🏆 <b>LEADERBOARD TABS</b>\n"
        "Coins · Messages · Reputation\n\n"
        "⏰ 1 rep per user per 24h · Can't rep yourself",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_fun": (
        "🎮 <b>Games & Fun</b>\n" + _D + "\n\n"
        "🎯 <b>GAMES</b>\n"
        "<code>/8ball question</code> · <code>/roll [sides]</code>\n"
        "<code>/trivia</code> · <code>/wyr</code> · <code>/pp</code>\n"
        "<code>/truth</code> · <code>/dare</code>\n\n"
        "💕 <b>SOCIAL</b>\n"
        "<code>/slap</code> · <code>/hug</code> · <code>/kiss</code>\n"
        "<code>/pat</code> · <code>/poke</code> · <code>/ship</code>\n"
        "<code>/roast @user</code> · <code>/compliment @user</code>\n\n"
        "🎲 <b>RANDOM</b>\n"
        "<code>/joke</code> · <code>/fact</code> · <code>/quote</code> · <code>/meme</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_util": (
        "🔧 <b>Utility Commands</b>\n" + _D + "\n\n"
        "ℹ️ <b>INFO</b>\n"
        "<code>/id [@user]</code> · <code>/info [@user]</code>\n"
        "<code>/chatinfo</code> · <code>/ping</code> · <code>/uptime</code>\n"
        "<code>/stats</code>\n\n"
        "🧮 <b>TEXT TOOLS</b>\n"
        "<code>/calc expr</code> · <code>/hash text</code>\n"
        "<code>/b64 encode|decode</code> · <code>/reverse text</code>\n\n"
        "🌐 <b>ONLINE</b>\n"
        "<code>/qr text</code> — QR code\n"
        "<code>/tr lang text</code> — translate\n"
        "<code>/weather city</code> · <code>/time [tz]</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_settings": (
        "⚙️ <b>Settings</b>\n" + _D + "\n\n"
        "🎛️ <b>INTERACTIVE PANELS</b>\n"
        "<code>/settings</code> — full settings panel\n"
        "<code>/protect</code> — protection panel\n"
        "<code>/locks</code> — lock types panel\n"
        "<code>/welcome</code> — welcome settings\n\n"
        "⚠️ <b>WARN SETTINGS</b>\n"
        "<code>/setwarnlimit N</code> · <code>/setwarnaction mute|ban|kick</code>\n\n"
        "💬 <b>CHAT SETTINGS</b>\n"
        "<code>/cleanservice on|off</code>\n"
        "<code>/delcommands on|off</code>\n"
        "<code>/welcdel N</code> · <code>/slowmode N</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_admin": (
        "👑 <b>Admin / Owner Commands</b>\n" + _D + "\n\n"
        "🌍 <b>GLOBAL MODERATION</b>\n"
        "<code>/gban user [reason]</code> — global ban\n"
        "<code>/ungban user</code> — remove global ban\n"
        "<code>/sudo user</code> · <code>/unsudo user</code>\n\n"
        "📢 <b>BROADCAST</b>\n"
        "<code>/broadcast msg</code> — all chats\n"
        "<code>/broadcastall msg</code> — all members\n\n"
        "🤖 <b>BOT MANAGEMENT</b>\n"
        "<code>/botstats</code> · <code>/chatlist</code>\n"
        "<code>/leave</code> · <code>/backup</code>",
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
        return await reply(update, f"🚫 bestie you don't have ban perms lmaoo {kmo(KAOMOJI_FLEX)}")
    target = await get_target(update, context)
    if not target:
        return await reply(update, "❓ <b>Who to ban?</b> Reply to a user or provide @username.")
    if await is_admin(context, update.effective_chat.id, target.id):
        return await reply(update, f"🛡️ ratio denied — you can't ban admins bestie {kmo(KAOMOJI_FLEX)} they're protected fr")
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
            f"🔨 <b>CANCELLED.</b> {kmo(KAOMOJI_BAN)}\n{_D}\n\n"
            f"👤 <b>User:</b> {user_link(target)} (<code>{target.id}</code>)\n"
            f"👑 <b>By:</b> {user_link(update.effective_user)}\n"
            f"📋 <b>Reason:</b> {html.escape(reason or 'no cap just vibes')}\n\n"
            f"🚫 <i>ratio'd + L + banned fr fr. periodt bestie</i>"
        )
        await finish_anim(m, text, reply_markup=_unban_btn(chat.id, target.id))
        await send_log(context, chat.id,
            f"🔨 <b>BAN</b> | {html.escape(chat.title or '')}\n"
            f"Admin: {user_link(update.effective_user)}\n"
            f"User: {user_link(target)} (<code>{target.id}</code>)\n"
            f"Reason: {html.escape(reason or 'None')}")
    except BadRequest as e:
        await finish_anim(m, f"💀 <b>oof something crashed fr:</b> {html.escape(str(e))} — that's an L ngl")

@admin_only
@groups_only
async def tban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, f"🚫 nuh uh bestie. no permission fr {kmo(KAOMOJI_BAN)}")
    target = await get_target(update, context)
    if not target:
        return await reply(update, "❓ <b>Usage:</b> <code>/tban @user 1h [reason]</code>")
    time_arg = (context.args[0] if update.message.reply_to_message and context.args
                else (context.args[1] if len(context.args) > 1 else "1h"))
    duration = parse_duration(time_arg)
    if not duration:
        return await reply(update, "❌ <b>Invalid duration.</b> Use: 1m, 1h, 1d, 1w")
    until = datetime.datetime.now(pytz.utc) + duration
    reason = " ".join(context.args[2:]) if len(context.args) > 2 else ""
    m = await animate_loading(update, "Applying temp ban")
    try:
        await _do_ban(context, update.effective_chat.id, target.id, until)
        log_action(update.effective_chat.id, update.effective_user.id, "tban", target.id, time_arg)
        await finish_anim(m,
            f"⏱️ <b>temp ban dropped bestie</b> {kmo(KAOMOJI_BAN)}\n{_D}\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"⏰ <b>Duration:</b> {html.escape(fmt_duration(duration))} — touch grass era\n"
            f"📅 <b>Expires:</b> {until.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"📋 <b>Reason:</b> {html.escape(reason or 'vibes were off ngl')}\n\n"
            f"🔓 <i>auto-unban coming. hope they learned fr periodt</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def sban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id): return
    target = await get_target(update, context)
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
    target = await get_target(update, context)
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
            f"✅ <b>unbanned bestie!!</b> {kmo(KAOMOJI_WHOLESOME)}\n{_D}\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👑 <b>By:</b> {user_link(update.effective_user)}\n\n"
            f"🟢 <i>they're back no cap. don't make us regret it tho fr</i>"
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
    target = await get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    m = await animate_loading(update, "Kicking user")
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        log_action(update.effective_chat.id, update.effective_user.id, "kick", target.id)
        await finish_anim(m,
            f"👢 <b>YEETED.</b> {kmo(KAOMOJI_BAN)}\n{_D}\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👑 <b>By:</b> {user_link(update.effective_user)}\n\n"
            f"🚪 <i>kicked out fr fr. the door was right there bestie ngl</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def skick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id): return
    target = await get_target(update, context)
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
    target = await get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    reason = " ".join(context.args) if context.args and not update.message.reply_to_message else get_reason(context)
    m = await animate_loading(update, "Muting user")
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS)
        log_action(update.effective_chat.id, update.effective_user.id, "mute", target.id, reason)
        _r = html.escape(reason or "the vibes weren't it")
        await finish_anim(m,
            f"🔇 <b>shhhh bestie.</b> {kmo(KAOMOJI_BAN)}\n{_D}\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👑 <b>By:</b> {user_link(update.effective_user)}\n"
            f"📋 <b>Reason:</b> {_r}\n\n"
            f"🤫 <i>muted. they can read but can't talk fr periodt</i>",
            reply_markup=_unmute_btn(update.effective_chat.id, target.id)
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def tmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = await get_target(update, context)
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
            f"⏱️ <b>temp muted bestie</b> {kmo(KAOMOJI_BAN)}\n{_D}\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"⏰ <b>Duration:</b> {html.escape(fmt_duration(duration))} — silent era\n"
            f"📅 <b>Until:</b> {until.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"🔇 <i>auto-unmute incoming. hope they reflect fr</i>",
            reply_markup=_unmute_btn(update.effective_chat.id, target.id)
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = await get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    m = await animate_loading(update, "Unmuting user")
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, UNMUTE_PERMS)
        log_action(update.effective_chat.id, update.effective_user.id, "unmute", target.id)
        await finish_anim(m,
            f"🔊 <b>they can talk again bestie</b> {kmo(KAOMOJI_WHOLESOME)}\n{_D}\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👑 <b>By:</b> {user_link(update.effective_user)}\n\n"
            f"✅ <i>unmuted fr. don't make it weird again tho periodt</i>"
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
    target = await get_target(update, context)
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
            extra_action = f"\n🔨 <b>auto-cancelled — warn limit hit periodt bestie 💀</b>"
        elif warn_action == "kick":
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await context.bot.unban_chat_member(update.effective_chat.id, target.id)
            extra_action = f"\n👢 <b>auto-yeeted — too many strikes fr 💨</b>"
        else:
            await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS)
            extra_action = f"\n🔇 <b>auto-silenced — strikes are the law fr bestie 🤫</b>"

    if not silent:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Unwarn", callback_data=f"unwarn:{update.effective_chat.id}:{target.id}"),
            InlineKeyboardButton("🗑️ Reset All", callback_data=f"resetwarn:{update.effective_chat.id}:{target.id}"),
        ]])
        text = (
            f"⚠️ <b>yikes a warning bestie</b> {kmo(KAOMOJI_THINK)}\n{_D}\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"👑 <b>By:</b> {user_link(update.effective_user)}\n"
            f"📋 <b>Reason:</b> {html.escape(reason or 'not it bestie')}\n\n"
            f"📊 <b>Strikes:</b> {count}/{warn_limit} [{bar}]{extra_action}"
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
    target = await get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    db = get_db()
    row = db.execute("SELECT id FROM warns WHERE chat_id=? AND user_id=? ORDER BY warned_at DESC LIMIT 1",
                     (update.effective_chat.id, target.id)).fetchone()
    if row:
        db.execute("DELETE FROM warns WHERE id=?", (row["id"],))
        db.commit()
    db.close()
    await reply(update,
        f"✅ <b>Warn Removed</b>\n{_D}\n\n"
        f"▸ {user_link(target)}\n"
        f"✨ <i>1 warning has been lifted.</i>"
    )

@admin_only
@groups_only
async def resetwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    db = get_db()
    db.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?",
               (update.effective_chat.id, target.id))
    db.commit(); db.close()
    log_action(update.effective_chat.id, update.effective_user.id, "resetwarn", target.id)
    await reply(update,
        f"🗑️ <b>Warns Reset</b>\n{_D}\n\n"
        f"▸ {user_link(target)}\n"
        f"✨ <i>All warnings cleared!</i>"
    )

async def warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context) or update.effective_user
    cfg = get_chat(update.effective_chat.id)
    db = get_db()
    rows = db.execute("SELECT * FROM warns WHERE chat_id=? AND user_id=? ORDER BY warned_at DESC",
                      (update.effective_chat.id, target.id)).fetchall()
    db.close()
    warn_limit = cfg.get("warn_limit", 3)
    if not rows:
        return await reply(update,
            f"✅ <b>Clean Record!</b>\n{_D}\n\n"
            f"▸ {user_link(target)} has zero warnings! 🌟"
        )
    bar = progress_bar(len(rows), warn_limit)
    lines = [
        f"⚠️ <b>Warn History</b>\n{_D}\n\n"
        f"▸ <b>User:</b> {user_link(target)}\n"
        f"▸ <b>Warns:</b> {len(rows)}/{warn_limit}  [{bar}]\n"
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
    target = await get_target(update, context)
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
        invalidate_admin_cache(update.effective_chat.id)
        log_action(update.effective_chat.id, update.effective_user.id, "promote", target.id, title)
        await finish_anim(m,
            f"⭐ <b>SLAY ADMIN ERA</b> {kmo(KAOMOJI_HYPE)}\n{_D}\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n"
            f"🏷️ <b>Title:</b> {html.escape(title) if title else 'Admin'} — serving\n\n"
            f"✨ <i>understood the assignment. new admin just dropped fr no cap</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def demote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = await get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    m = await animate_loading(update, "Demoting user")
    try:
        await context.bot.promote_chat_member(
            update.effective_chat.id, target.id,
            can_manage_chat=False, can_delete_messages=False, can_restrict_members=False,
            can_invite_users=False, can_pin_messages=False
        )
        invalidate_admin_cache(update.effective_chat.id)
        log_action(update.effective_chat.id, update.effective_user.id, "demote", target.id)
        await finish_anim(m,
            f"📉 <b>admin era is OVER bestie</b> {kmo(KAOMOJI_SAD)}\n{_D}\n\n"
            f"👤 <b>User:</b> {user_link(target)}\n\n"
            f"💀 <i>demoted. L. not the glow-up we expected fr ngl</i>"
        )
    except BadRequest as e:
        await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def admintitle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    target = await get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    title = (" ".join(context.args) if update.message.reply_to_message
             else " ".join(context.args[1:]) if context.args else "")
    if not title: return await reply(update, "❓ <b>Provide a title.</b> <code>/admintitle Title Here</code>")
    try:
        await context.bot.set_chat_administrator_custom_title(
            update.effective_chat.id, target.id, title[:16])
        await reply(update,
            f"🏷️ <b>Title Set!</b>\n{_D}\n\n"
            f"▸ <b>User:</b> {user_link(target)}\n"
            f"▸ <b>Title:</b> <b>{html.escape(title)}</b>"
        )
    except BadRequest as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

async def adminlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Fetching admin list")
    try:
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        owners = [a for a in admins if a.status == "creator"]
        mods   = [a for a in admins if a.status == "administrator"]
        lines  = [f"👮 <b>Admin List</b>  ({len(admins)})\n{_D}\n"]
        if owners:
            lines.append("👑 <b>Owner</b>")
            for a in owners:
                lines.append(f"  └ <a href='tg://user?id={a.user.id}'>{html.escape(a.user.first_name or str(a.user.id))}</a>")
        if mods:
            lines.append("\n🔧 <b>Admins</b>")
            for a in mods:
                name = html.escape(a.user.first_name or str(a.user.id))
                t = (f" <i>· {html.escape(a.custom_title)}</i>"
                     if isinstance(a, ChatMemberAdministrator) and a.custom_title else "")
                lines.append(f"  └ <a href='tg://user?id={a.user.id}'>{name}</a>{t}")
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
    m = await animate_loading(update, "Scanning for zombies")
    try:
        count = 0
        async for member in context.bot.get_chat_members(update.effective_chat.id):
            if getattr(member.user, "is_deleted", False): count += 1
        await finish_anim(m,
            f"🧟 <b>Zombie Scan Complete</b>\n{_D}\n\n"
            f"▸ <b>Zombies found:</b> {count}\n\n"
            f"{'💀 Use /kickzombies to remove them!' if count else '✨ Group is zombie-free!'}"
        )
    except Exception as e:
        await finish_anim(m,
            f"🧟 <b>Zombie Scan</b>\n{_D}\n\n"
            f"⚠️ <i>Cannot iterate members in this group type.\n"
            f"This feature requires admin rights and may not work in all groups.</i>\n\n"
            f"<code>{html.escape(str(e)[:100])}</code>"
        )

@admin_only
@groups_only
async def kickzombies_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
        return await reply(update, "🚫 <b>No Permission</b>")
    m = await animate_loading(update, "Hunting zombies")
    try:
        kicked = 0
        async for member in context.bot.get_chat_members(update.effective_chat.id):
            if getattr(member.user, "is_deleted", False):
                try:
                    await context.bot.ban_chat_member(update.effective_chat.id, member.user.id)
                    await context.bot.unban_chat_member(update.effective_chat.id, member.user.id)
                    kicked += 1
                except: pass
        log_action(update.effective_chat.id, update.effective_user.id, "kickzombies", extra=str(kicked))
        await finish_anim(m,
            f"✅ <b>Zombies Purged!</b>\n{_D}\n\n"
            f"💥 <b>Kicked {kicked} zombie accounts!</b>\n"
            f"🌟 <i>Group is now clean!</i>"
        )
    except Exception as e:
        await finish_anim(m,
            f"⚠️ <b>Kick Zombies</b>\n{_D}\n\n"
            f"<i>Cannot iterate members in this group type.\n"
            f"This feature requires specific group permissions.</i>"
        )

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
        f"<b>Purging {len(ids)} messages...</b>\n[{progress_bar(0, len(ids))}]",
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
                f"<b>Purging...</b> [{progress_bar(min(i+100, len(ids)), len(ids))}]\n"
                f"<i>{min(i+100, len(ids))}/{len(ids)} deleted</i>",
                parse_mode="HTML")
        except: pass
    try:
        await m.edit_text(
            f"✅ <b>Purge Complete!</b>\n{_D}\n\n"
            f"💥 <b>Deleted {count} messages!</b>",
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
                f"🐢 <b>Slowmode Active</b>\n{_D}\n\n"
                f"▸ <b>Delay:</b> {seconds}s per message\n"
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
                           f"Or use <code>/locks</code> for the panel!")
    t = context.args[0].lower()
    if t not in LOCK_TYPES:
        return await reply(update, f"❌ <b>Unknown type.</b> Use: <code>{', '.join(LOCK_TYPES.keys())}</code>")
    set_setting(update.effective_chat.id, LOCK_TYPES[t], 1)
    icon = LOCK_ICONS.get(t, "🔒")
    await reply(update, f"{icon} <b>Locked: {t.upper()}</b>\n<i>{t.title()} are now blocked in this chat.</i>")

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
    await reply(update, f"{icon} <b>Unlocked: {t.upper()}</b>\n<i>{t.title()} are now allowed.</i>")

async def locks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_chat(update.effective_chat.id)
    if not cfg:
        ensure_chat(update.effective_chat)
        cfg = get_chat(update.effective_chat.id)
    text = (
        f"🔒 <b>Lock Panel</b>\n{_D}\n"
        "<i>🟢 = Allowed  ·  🔴 = Locked</i>"
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
            row.append(InlineKeyboardButton(f"{state} {icon} {name}", callback_data=f"lock_tog:{name}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("🔓 Unlock ALL", callback_data="lock_tog:__all_off__"),
                 InlineKeyboardButton("🔒 Lock ALL",   callback_data="lock_tog:__all_on__")])
    return InlineKeyboardMarkup(rows)

async def lock_toggle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not await is_admin(context, q.message.chat_id, q.from_user.id):
        return await q.answer("🚫 Admins only!", show_alert=True)
    await q.answer()
    lock_name = q.data.split(":", 1)[1]
    if lock_name == "__all_on__":
        db = get_db()
        for key in LOCK_TYPES.values():
            db.execute(f"UPDATE chats SET {key}=1 WHERE chat_id=?", (q.message.chat_id,))
        db.commit(); db.close()
    elif lock_name == "__all_off__":
        db = get_db()
        for key in LOCK_TYPES.values():
            db.execute(f"UPDATE chats SET {key}=0 WHERE chat_id=?", (q.message.chat_id,))
        db.commit(); db.close()
    else:
        key = LOCK_TYPES.get(lock_name)
        if key:
            cfg = get_chat(q.message.chat_id)
            new_val = 0 if cfg.get(key, 0) else 1
            set_setting(q.message.chat_id, key, new_val)
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
                    f"▸ {user_link(user)}\n▸ Reason: {html.escape(reason)}",
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
                    await context.bot.send_message(chat.id,
                        f"🚨 <b>RAID DETECTED!</b>\n<i>New member auto-banned during raid.</i>",
                        parse_mode="HTML")
                except: pass
                continue

        if cfg.get("restrict_new_members"):
            try: await context.bot.restrict_chat_member(chat.id, user.id, MUTE_PERMS)
            except: pass

        if cfg.get("cas_enabled"):
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.get(f"https://api.cas.chat/check?user_id={user.id}",
                                     timeout=aiohttp.ClientTimeout(total=5)) as r:
                        data = await r.json(content_type=None)
                        if data.get("ok"):
                            await context.bot.ban_chat_member(chat.id, user.id)
                            await context.bot.send_message(chat.id,
                                f"🛡️ <b>CAS banned user removed!</b>\n▸ {user_link(user)}",
                                parse_mode="HTML")
                            continue
            except: pass

        if cfg.get("welcome_captcha"):
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ I'm Human!", callback_data=f"captcha:{user.id}:{chat.id}"),
                InlineKeyboardButton("❌ Remove Bot", callback_data=f"captcha:kick:{user.id}:{chat.id}"),
            ]])
            name = html.escape(user.first_name or str(user.id))
            try:
                wm = await context.bot.send_message(chat.id,
                    f"🔐 <b>Verification Required</b>\n{_D}\n\n"
                    f"▸ {user_link(user)}, please verify you're human!\n"
                    f"<i>Tap the button below within 60 seconds.</i>",
                    parse_mode="HTML", reply_markup=kb)
                await context.bot.restrict_chat_member(chat.id, user.id, MUTE_PERMS)
                captcha_cache[(user.id, chat.id)] = {"msg_id": wm.message_id, "at": time.time()}
            except: pass
            continue

        custom_welcome = cfg.get("welcome_msg")
        if custom_welcome:
            text = format_welcome(custom_welcome, user, chat, count)
        else:
            name = html.escape(user.first_name or str(user.id))
            ai_welcome = await ai_reply(
                f"Write one warm, hype Gen Z welcome for '{name}' joining a Telegram group as member #{count}. "
                "1 sentence, friendly and exciting. Mention their name. Max 20 words. Emojis. Plain text only.",
                fallback=f"welcome {name}!! you're member #{count} and we're so glad you're here fr!! 🎉",
            )
            text = (
                f"✨ <b>Welcome, <a href='tg://user?id={user.id}'>{name}</a>!</b>\n"
                f"{_D}\n"
                f"<i>{html.escape(ai_welcome)}</i>\n"
                f"{_D}\n"
                f"👥 You're member <b>#{count}</b> in <b>{html.escape(chat.title or 'this group')}</b>"
            )
        delete_after = cfg.get("welcome_delete_after", 0)
        try:
            wm = await context.bot.send_message(chat.id, text, parse_mode="HTML")
            if delete_after:
                async def _del_later(msg=wm, sec=delete_after):
                    await asyncio.sleep(sec)
                    try: await msg.delete()
                    except: pass
                asyncio.create_task(_del_later())
        except: pass

async def captcha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    parts = q.data.split(":")
    if parts[1] == "kick":
        user_id, chat_id = int(parts[2]), int(parts[3])
        if not await is_admin(context, chat_id, q.from_user.id):
            return await q.answer("🚫 Admins only!", show_alert=True)
        await q.answer()
        try:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.unban_chat_member(chat_id, user_id)
            await q.message.delete()
        except: pass
        return
    user_id, chat_id = int(parts[1]), int(parts[2])
    if q.from_user.id != user_id:
        return await q.answer("❌ This isn't for you!", show_alert=True)
    await q.answer("✅ Verified! Welcome!", show_alert=False)
    try:
        await context.bot.restrict_chat_member(chat_id, user_id, UNMUTE_PERMS)
        await q.message.delete()
        captcha_cache.pop((user_id, chat_id), None)
    except: pass

async def goodbye_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.left_chat_member: return
    chat = update.effective_chat
    cfg  = get_chat(chat.id)
    if not cfg.get("goodbye_enabled", 1): return
    user = update.message.left_chat_member
    goodbye = cfg.get("goodbye_msg") or (
                f"😢 <b>{{first}} has left.</b>\n"
        f"We'll miss you! Come back soon! 💙"
    )
    text = format_welcome(goodbye, user, chat)
    try: await context.bot.send_message(chat.id, text, parse_mode="HTML")
    except: pass

@admin_only
@groups_only
async def setwelcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args and not (update.message.reply_to_message and update.message.reply_to_message.text):
        return await reply(update,
            f"👋 <b>Set Welcome</b>\n{_D}\n\n"
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
        f"📜 <b>Rules — {title}</b>\n{_D}\n\n"
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
    if not context.args:
        return await reply(update,
            f"📝 <b>Save Note — How to use</b>\n{_D}\n\n"
            "▸ <code>/save name text content</code>\n"
            "▸ Reply to any media + <code>/save name</code>\n"
            "▸ Reply to media + <code>/save name caption</code>\n\n"
            "<i>Retrieve with <code>/get name</code> or <code>#name</code></i>"
        )
    name       = context.args[0].lower()
    reply_msg  = update.message.reply_to_message
    media_type, media_id = _extract_media(reply_msg)

    if len(context.args) > 1:
        content = " ".join(context.args[1:])
    elif reply_msg:
        content = (reply_msg.caption or reply_msg.text or "").strip()
    else:
        content = ""

    if not media_type and not content:
        return await reply(update,
            "❓ <b>Nothing to save!</b>\n\n"
            "<i>Reply to a message/sticker/photo/video or add text after the name.</i>"
        )

    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO notes "
        "(chat_id, name, content, media_type, media_id, created_by) VALUES (?,?,?,?,?,?)",
        (chat_id, name, content, media_type, media_id, update.effective_user.id)
    )
    db.commit(); db.close()
    badge = _MEDIA_BADGE.get(media_type, "📝 Text")
    await reply(update,
        f"📝 <b>Note Saved!</b>\n{_D}\n\n"
        f"▸ <b>Name:</b> <code>#{name}</code>\n"
        f"▸ <b>Type:</b> {badge}\n\n"
        f"<i>Use <code>/get {name}</code> or <code>#{name}</code> to retrieve!</i>"
    )

async def get_note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/get name</code>")
    await _send_note(update, context, context.args[0].lower())

async def _send_note(update, context, name):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    row = db.execute("SELECT * FROM notes WHERE chat_id=? AND name=?", (chat_id, name)).fetchone()
    db.close()
    if not row:
        return await reply(update, f"❌ <b>Note <code>#{name}</code> not found!</b>")
    content    = row["content"] or ""
    media_type = row["media_type"] or ""
    media_id   = row["media_id"] or ""
    kb_raw     = parse_buttons(row["buttons"] or "[]")
    kb         = InlineKeyboardMarkup(kb_raw) if kb_raw else None
    await _send_media_response(update.message, media_type, media_id, content, kb)

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
            f"📝 <b>No Notes Yet</b>\n{_D}\n\n"
            "<i>Use /save to create one!</i>")
    note_buttons = []
    row = []
    for i, r in enumerate(rows):
        row.append(InlineKeyboardButton(f"#{r['name']}", callback_data=f"getnote:{r['name']}"))
        if len(row) == 3:
            note_buttons.append(row); row = []
    if row: note_buttons.append(row)
    kb = InlineKeyboardMarkup(note_buttons)
    await reply(update,
        f"📝 <b>Notes ({len(rows)})</b>\n{_D}\n\n"
        f"Tap a button to retrieve it:",
        reply_markup=kb)

async def note_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    name    = q.data.split(":", 1)[1]
    chat_id = q.message.chat_id
    db = get_db()
    row = db.execute("SELECT * FROM notes WHERE chat_id=? AND name=?", (chat_id, name)).fetchone()
    db.close()
    if not row:
        await q.message.reply_text(f"❌ <b>Note #{name} not found!</b>", parse_mode="HTML")
        return
    content    = row["content"] or ""
    media_type = row["media_type"] or ""
    media_id   = row["media_id"] or ""
    kb_raw     = parse_buttons(row["buttons"] or "[]")
    kb         = InlineKeyboardMarkup(kb_raw) if kb_raw else None
    await _send_media_response(q.message, media_type, media_id, content, kb)

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
def _extract_media(msg) -> tuple:
    """Extract (media_type, file_id) from a Message object. Returns ('', '') if none."""
    if not msg: return "", ""
    if msg.sticker:    return "sticker",    msg.sticker.file_id
    if msg.photo:      return "photo",      msg.photo[-1].file_id
    if msg.video:      return "video",      msg.video.file_id
    if msg.animation:  return "animation",  msg.animation.file_id
    if msg.voice:      return "voice",      msg.voice.file_id
    if msg.audio:      return "audio",      msg.audio.file_id
    if msg.video_note: return "video_note", msg.video_note.file_id
    if msg.document:   return "document",   msg.document.file_id
    return "", ""

_MEDIA_BADGE = {
    "sticker":    "🎭 Sticker",    "photo":      "🖼️ Photo",
    "video":      "🎬 Video",      "animation":  "🎞️ GIF",
    "voice":      "🎙️ Voice",      "audio":      "🎵 Audio",
    "video_note": "🔵 Video Note", "document":   "📄 Document",
}

async def _send_media_response(msg, media_type: str, media_id: str,
                               caption: str = "", reply_markup=None):
    """Send the correct media type as a reply to `msg`."""
    pm = "HTML"
    cap = caption or None
    try:
        if media_type == "sticker":
            await msg.reply_sticker(media_id)
            if caption:
                await msg.reply_text(caption, parse_mode=pm)
        elif media_type == "photo":
            await msg.reply_photo(media_id, caption=cap, parse_mode=pm, reply_markup=reply_markup)
        elif media_type == "video":
            await msg.reply_video(media_id, caption=cap, parse_mode=pm, reply_markup=reply_markup)
        elif media_type == "animation":
            await msg.reply_animation(media_id, caption=cap, parse_mode=pm, reply_markup=reply_markup)
        elif media_type == "voice":
            await msg.reply_voice(media_id, caption=cap, parse_mode=pm, reply_markup=reply_markup)
        elif media_type == "audio":
            await msg.reply_audio(media_id, caption=cap, parse_mode=pm, reply_markup=reply_markup)
        elif media_type == "video_note":
            await msg.reply_video_note(media_id)
            if caption:
                await msg.reply_text(caption, parse_mode=pm)
        elif media_type == "document":
            await msg.reply_document(media_id, caption=cap, parse_mode=pm, reply_markup=reply_markup)
        else:
            if caption:
                await msg.reply_text(caption, parse_mode=pm, reply_markup=reply_markup,
                                     disable_web_page_preview=True)
    except Exception as e:
        logger.debug(f"_send_media_response: {e}")
        if caption:
            try:
                await msg.reply_text(caption, parse_mode=pm, disable_web_page_preview=True)
            except Exception: pass

@admin_only
async def filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update,
            f"🔍 <b>Filter — How to use</b>\n{_D}\n\n"
            "▸ <code>/filter keyword reply text</code>\n"
            "▸ Reply to any media + <code>/filter keyword</code>\n"
            "▸ Reply to media + <code>/filter keyword caption</code>\n"
            "▸ Regex: <code>/filter regex:pattern reply</code>\n\n"
            "<i>🤖 Bot auto-replies whenever the keyword is detected in chat!</i>"
        )

    keyword = context.args[0].lower()
    is_regex = keyword.startswith("regex:")
    if is_regex:
        keyword = keyword[6:]
    if not keyword:
        return await reply(update, "❌ <b>Keyword cannot be empty!</b>")

    # Detect media from the replied-to message
    reply_msg             = update.message.reply_to_message
    media_type, media_id  = _extract_media(reply_msg)

    # Reply text: prefer command args[1:], fall back to caption/text of replied msg
    if len(context.args) > 1:
        reply_text = " ".join(context.args[1:])
    elif reply_msg:
        reply_text = (reply_msg.caption or reply_msg.text or "").strip()
    else:
        reply_text = ""

    if not media_type and not reply_text:
        return await reply(update,
            "❓ <b>Nothing to save!</b>\n\n"
            "<i>Either reply to a message/sticker/photo/video/gif, "
            "or add reply text after the keyword.</i>"
        )

    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute(
        "INSERT OR REPLACE INTO filters "
        "(chat_id, keyword, reply, is_regex, media_type, media_id, created_by) "
        "VALUES (?,?,?,?,?,?,?)",
        (chat_id, keyword, reply_text, 1 if is_regex else 0,
         media_type, media_id, update.effective_user.id)
    )
    db.commit(); db.close()

    badge = _MEDIA_BADGE.get(media_type, "📝 Text")
    await reply(update,
        f"✅ <b>Filter Saved!</b>\n{_D}\n\n"
        f"▸ <b>Keyword:</b> <code>{html.escape(keyword)}</code>\n"
        f"▸ <b>Response:</b> {badge}\n"
        f"▸ {'🔢 <b>Regex</b> mode' if is_regex else '🔑 <b>Exact</b> match'}\n\n"
        f"<i>🤖 I'll respond automatically every time someone types that keyword!</i>"
    )

async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    rows = db.execute(
        "SELECT keyword, is_regex, media_type FROM filters WHERE chat_id=? ORDER BY keyword",
        (chat_id,)
    ).fetchall()
    db.close()
    if not rows:
        return await reply(update,
            f"🔍 <b>No Filters Active</b>\n{_D}\n\n"
            "<i>Use <code>/filter keyword reply</code> to add one!</i>")
    lines = [f"🔍 <b>Active Filters ({len(rows)})</b>\n{_D}\n"]
    for r in rows:
        badge = _MEDIA_BADGE.get(r["media_type"] or "", "📝")[:2]
        mode  = "🔢" if r["is_regex"] else "🔑"
        lines.append(f"{mode} <code>{html.escape(r['keyword'])}</code>  {badge}")
    await reply(update, "\n".join(lines))

@admin_only
async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await reply(update, "❓ <b>Usage:</b> <code>/stop keyword</code>")
    keyword = context.args[0].lower()
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    cur = db.execute(
        "DELETE FROM filters WHERE chat_id=? AND keyword=?", (chat_id, keyword)
    )
    db.commit(); db.close()
    if cur.rowcount:
        await reply(update,
            f"✅ <b>Filter removed!</b>\n▸ <code>{html.escape(keyword)}</code>")
    else:
        await reply(update,
            f"❌ <b>Filter not found:</b> <code>{html.escape(keyword)}</code>")

@admin_only
async def stopall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = get_connected_chat(update.effective_user.id, update.effective_chat)
    db = get_db()
    db.execute("DELETE FROM filters WHERE chat_id=?", (chat_id,))
    db.commit(); db.close()
    await reply(update,
        f"✅ <b>All filters cleared!</b>\n{_D}\n\n"
        "<i>The slate is clean. No active filters.</i>")

async def filter_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    # Match against text OR caption (for photos/videos with captions)
    text = (update.message.text or update.message.caption or "").strip()
    if not text: return
    text_lower = text.lower()
    chat_id = update.effective_chat.id
    db = get_db()
    rows = db.execute("SELECT * FROM filters WHERE chat_id=?", (chat_id,)).fetchall()
    db.close()
    for row in rows:
        matched = False
        if row["is_regex"]:
            try:
                matched = bool(re.search(row["keyword"], text_lower, re.IGNORECASE))
            except Exception:
                pass
        else:
            matched = row["keyword"] in text_lower
        if matched:
            kb_raw  = parse_buttons(row["buttons"] or "[]")
            kb      = InlineKeyboardMarkup(kb_raw) if kb_raw else None
            content = row["reply"] or ""
            mtype   = row["media_type"] or ""
            mid     = row["media_id"] or ""
            await _send_media_response(update.message, mtype, mid, content, kb)
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
    lines = [f"🚫 <b>Blacklist</b>\n{_D}\n"]
    for r in rows:
        lines.append(f"▸ <code>{html.escape(r['word'])}</code>" + (" <i>(regex)</i>" if r["is_regex"] else ""))
    await reply(update, "\n".join(lines))

@admin_only
async def blacklistmode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ("delete", "warn", "mute", "ban"):
        return await reply(update, "❓ <b>Usage:</b> <code>/blmode delete|warn|mute|ban</code>")
    set_setting(update.effective_chat.id, "blacklist_action", context.args[0])
    await reply(update, f"✅ <b>Blacklist action:</b> <code>{context.args[0]}</code>")

async def blacklist_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    # Check text AND caption so photo captions are also scanned
    text = (update.message.text or update.message.caption or "").strip()
    if not text: return
    if await is_admin(context, update.effective_chat.id, update.effective_user.id): return
    text = text.lower()
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
                f"⚡ <b>Flood Detected!</b>\n"
                f"▸ {user_link(update.effective_user)} was <b>{action_text}</b> for flooding!",
                parse_mode="HTML")
            return

    msg = update.message

    if cfg.get("anti_link") and msg.text:
        url_pat = r'(https?://|t\.me/|@\w+|tg://|bit\.ly|goo\.gl)'
        if re.search(url_pat, msg.text, re.IGNORECASE):
            try: await msg.delete()
            except: pass
            return

    if cfg.get("anti_forward") and msg.forward_date:
        try: await msg.delete()
        except: pass
        return

    if cfg.get("anti_arabic") and msg.text:
        if re.search(r'[\u0600-\u06FF\u200F\u202B]', msg.text):
            try: await msg.delete()
            except: pass
            return

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

    db = get_db()
    db.execute("UPDATE users SET total_msgs=total_msgs+1 WHERE user_id=?", (user_id,))
    db.commit(); db.close()

# ─── PROTECTION SETTINGS ──────────────────────────────────────────────────────
@admin_only
async def protect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_chat(update.effective_chat.id)
    if not cfg:
        ensure_chat(update.effective_chat)
        cfg = get_chat(update.effective_chat.id)
    text = (
        f"🛡️ <b>Protection Panel</b>\n{_D}\n"
        "<i>Tap to toggle each setting on/off</i>"
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
    try:
        await q.edit_message_reply_markup(reply_markup=kb)
    except: pass

@admin_only
async def antispam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_spam", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-spam {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def antiflood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_flood", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-flood {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def setflood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/setflood N [time_secs]</code>")
    try:
        n = int(context.args[0])
        t = int(context.args[1]) if len(context.args) > 1 else 5
    except: return await reply(update, "❌ Invalid number.")
    set_setting(update.effective_chat.id, "flood_count", n)
    set_setting(update.effective_chat.id, "flood_time", t)
    await reply(update, f"✅ <b>Flood limit: {n} msgs in {t}s!</b>")

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
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-link {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def antiforward_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_forward", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-forward {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def antibot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_bot", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-bot joining {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def antinsfw_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_nsfw", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-NSFW {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def antiarabic_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_arabic", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-Arabic/RTL {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def antiraid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "anti_raid", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Anti-raid {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def setraid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/setraid N</code>")
    try: n = int(context.args[0])
    except: return await reply(update, "❌ Invalid number.")
    set_setting(update.effective_chat.id, "raid_threshold", n)
    await reply(update, f"✅ <b>Raid threshold: {n} joins/minute!</b>")

@admin_only
async def cas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "cas_enabled", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>CAS protection {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def restrict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "restrict_new_members", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>New member restriction {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def cleanservice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "clean_service", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Clean service messages {'enabled' if val else 'disabled'}!</b>")

@admin_only
async def delcommands_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = (context.args[0].lower() if context.args else "on") == "on"
    set_setting(update.effective_chat.id, "delete_commands", 1 if val else 0)
    await reply(update, f"{'✅' if val else '❌'} <b>Delete commands {'enabled' if val else 'disabled'}!</b>")

# ─── SETTINGS PANEL ───────────────────────────────────────────────────────────
@admin_only
async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = get_chat(update.effective_chat.id)
    if not cfg:
        ensure_chat(update.effective_chat)
        cfg = get_chat(update.effective_chat.id)
    text = (
        f"⚙️ <b>Settings Panel</b>\n{_D}\n\n"
        f"▸ <b>Anti-spam:</b> {on_off(cfg.get('anti_spam',1))}\n"
        f"▸ <b>Anti-flood:</b> {on_off(cfg.get('anti_flood',1))}\n"
        f"▸ <b>Anti-link:</b> {on_off(cfg.get('anti_link',0))}\n"
        f"▸ <b>Anti-raid:</b> {on_off(cfg.get('anti_raid',0))}\n"
        f"▸ <b>Welcome:</b> {on_off(cfg.get('greetmembers',1))}\n"
        f"▸ <b>Goodbye:</b> {on_off(cfg.get('goodbye_enabled',1))}\n"
        f"▸ <b>Captcha:</b> {on_off(cfg.get('welcome_captcha',0))}\n"
        f"▸ <b>Warn limit:</b> {cfg.get('warn_limit',3)}\n"
        f"▸ <b>Warn action:</b> {cfg.get('warn_action','mute')}\n"
        f"▸ <b>CAS:</b> {on_off(cfg.get('cas_enabled',0))}\n"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡️ Protection", callback_data="open_protect_panel"),
         InlineKeyboardButton("🔒 Locks", callback_data="help_locks")],
    ])
    if update.callback_query:
        try: await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except: pass
    else:
        await reply(update, text, reply_markup=kb)

# ─── REPORT ───────────────────────────────────────────────────────────────────
async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await reply(update, "❓ <b>Reply to a message to report it!</b>")
    cfg = get_chat(update.effective_chat.id)
    if not cfg.get("report_enabled", 1):
        return await reply(update, "❌ <b>Reports are disabled in this group.</b>")
    reported = update.message.reply_to_message.from_user
    reporter = update.effective_user
    reason   = " ".join(context.args) if context.args else "No reason given"
    if reported.id == reporter.id:
        return await reply(update, "❌ <b>You cannot report yourself!</b>")
    if await is_admin(context, update.effective_chat.id, reported.id):
        return await reply(update, "⚠️ <b>Cannot report an admin!</b>")

    db = get_db()
    db.execute("INSERT INTO reports (chat_id, reporter_id, reported_id, message_id, reason) VALUES (?,?,?,?,?)",
               (update.effective_chat.id, reporter.id, reported.id,
                update.message.reply_to_message.message_id, reason))
    db.commit(); db.close()

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔨 Ban",    callback_data=f"report_ban:{reported.id}"),
        InlineKeyboardButton("🔇 Mute",   callback_data=f"report_mute:{reported.id}"),
        InlineKeyboardButton("👢 Kick",   callback_data=f"report_kick:{reported.id}"),
        InlineKeyboardButton("✅ Dismiss", callback_data=f"report_dismiss:{reported.id}"),
    ]])
    await reply(update,
        f"🚨 <b>Report Filed!</b>\n{_D}\n\n"
        f"▸ <b>Reported:</b> {user_link(reported)}\n"
        f"▸ <b>Reporter:</b> {user_link(reporter)}\n"
        f"▸ <b>Reason:</b> {html.escape(reason)}\n\n"
        f"<i>Admins: take action below 👇</i>",
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
        f"🌐 <b>Federation Created!</b>\n{_D}\n\n"
        f"▸ <b>Name:</b> {html.escape(name)}\n"
        f"▸ <b>Fed ID:</b> <code>{fed_id}</code>\n\n"
        f"<i>Share the ID so other groups can /joinfed!</i>"
    )

async def delfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a federation that you own."""
    user_id = update.effective_user.id
    db = get_db()
    fed = db.execute("SELECT * FROM federations WHERE owner_id=?", (user_id,)).fetchone()
    if not fed:
        db.close()
        return await reply(update, "❌ <b>You don't own any federation!</b>")
    fed_id = fed["fed_id"]
    # Remove all federation data
    db.execute("DELETE FROM federation_bans   WHERE fed_id=?", (fed_id,))
    db.execute("DELETE FROM federation_admins WHERE fed_id=?", (fed_id,))
    db.execute("DELETE FROM federation_chats  WHERE fed_id=?", (fed_id,))
    db.execute("UPDATE chats SET fed_id=NULL  WHERE fed_id=?", (fed_id,))
    db.execute("DELETE FROM federations       WHERE fed_id=?", (fed_id,))
    db.commit(); db.close()
    await reply(update,
        f"💥 <b>Federation Deleted!</b>\n{_D}\n\n"
        f"▸ <b>Name:</b> {html.escape(fed['name'])}\n"
        f"▸ <b>ID:</b> <code>{fed_id}</code>\n\n"
        f"<i>All fed bans and members have been cleared. no cap fr fr 💀</i>"
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
        f"✅ <b>Joined federation:</b> {html.escape(fed['name'])}!\n"
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
        f"🌐 <b>Federation Info</b>\n{_D}\n\n"
        f"▸ <b>Name:</b> {html.escape(fed['name'])}\n"
        f"▸ <b>ID:</b> <code>{fed_id}</code>\n"
        f"▸ <b>Chats:</b> {chats}\n"
        f"▸ <b>Admins:</b> {admins+1}\n"
        f"▸ <b>Bans:</b> {bans}\n\n"
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
    target = await get_target(update, context)
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
        f"🌐 <b>Fed Ban Applied!</b>\n{_D}\n\n"
        f"▸ <b>User:</b> {user_link(target)}\n"
        f"▸ <b>Reason:</b> {html.escape(reason)}\n"
        f"▸ <b>Banned in:</b> {banned_in} chats"
    )

async def unfban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]: db.close(); return await reply(update, "❌ <b>Not in a federation!</b>")
    fed_id = fed_row["fed_id"]
    target = await get_target(update, context)
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
    lines = [f"🌐 <b>Fed Bans ({len(bans)})</b>\n{_D}\n"]
    for b in bans:
        name = html.escape(b["first_name"] or str(b["user_id"]))
        lines.append(f"▸ {name} — <i>{html.escape(b['reason'] or 'No reason')}</i>")
    await reply(update, "\n".join(lines))

async def fadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]: db.close(); return await reply(update, "❌ <b>Not in a federation!</b>")
    fed_id = fed_row["fed_id"]
    fed = db.execute("SELECT * FROM federations WHERE fed_id=?", (fed_id,)).fetchone()
    if update.effective_user.id != fed["owner_id"] and not is_sudo(update.effective_user.id):
        db.close(); return await reply(update, "❌ <b>Only federation owner can add admins!</b>")
    target = await get_target(update, context)
    if not target: db.close(); return await reply(update, "❓ Reply to a user.")
    db.execute("INSERT OR IGNORE INTO federation_admins (fed_id, user_id) VALUES (?,?)", (fed_id, target.id))
    db.commit(); db.close()
    await reply(update, f"✅ <b>{user_link(target)} is now a federation admin!</b>")

async def fremove_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    fed_row = db.execute("SELECT fed_id FROM chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
    if not fed_row or not fed_row["fed_id"]: db.close(); return await reply(update, "❌ <b>Not in a federation!</b>")
    fed_id = fed_row["fed_id"]
    target = await get_target(update, context)
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
            f"✅ <b>Connected!</b>\n"
            f"▸ {html.escape(chat_obj.title or str(chat_id))}\n"
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
        await reply(update, f"✅ <b>Connected to:</b> {html.escape(chat.title or str(cid))}\n▸ <code>{cid}</code>")
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
                f"😴 {user_link(update.effective_user)} is now AFK!\n"
        + (f"▸ <b>Reason:</b> {html.escape(reason)}" if reason else "<i>No reason given.</i>")
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
        await reply(update,
                        f"✅ <b>{user_link(update.effective_user)} is back!</b>\n"
            f"⏱️ <i>Was AFK for {time_str}.</i>"
        )
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
                + (f"\n▸ <b>Reason:</b> {html.escape(reason)}" if reason else "")
            )

# ═══════════════════════════════════════════════════════════════════════════════
#                     🌍 GLOBAL BAN / SUDO
# ═══════════════════════════════════════════════════════════════════════════════
@owner_only
async def gban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context)
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
        f"🌍 <b>Global Ban!</b>\n{_D}\n\n"
        f"▸ <b>User:</b> {user_link(target)}\n"
        f"▸ <b>ID:</b> <code>{target.id}</code>\n"
        f"▸ <b>Reason:</b> {html.escape(reason)}\n"
        f"▸ <b>Banned in:</b> {banned_in} chats\n\n"
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
    target = await get_target(update, context)
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
        f"✅ <b>Global ban lifted for {user_link(target)}!</b>\n"
        f"<i>Removed from all {len(chats)} chats.</i>"
    )

@owner_only
async def sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context)
    if not target: return await reply(update, "❓ Reply to a user.")
    db = get_db()
    db.execute("INSERT OR IGNORE INTO sudo_users (user_id, added_by) VALUES (?,?)",
               (target.id, update.effective_user.id))
    db.execute("UPDATE users SET is_sudo=1 WHERE user_id=?", (target.id,))
    db.commit(); db.close()
    await reply(update, f"👑 <b>{user_link(target)} now has sudo powers!</b>")

@owner_only
async def unsudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context)
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
        f"<b>Broadcasting to {total} chats...</b>\n[{progress_bar(0, total)}]",
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
                    f"<b>Broadcasting...</b> [{progress_bar(i, total)}]\n"
                    f"{i}/{total} · ✅ {sent} | ❌ {failed}", parse_mode="HTML")
            except: pass
        await asyncio.sleep(0.05)
    await m.edit_text(
        f"✅ <b>Broadcast Done!</b>\n{_D}\n\n"
        f"▸ <b>Chats:</b> {total}\n▸ <b>Sent:</b> {sent}\n▸ <b>Failed:</b> {failed}\n"
        f"▸ <b>Rate:</b> {int(sent/total*100) if total else 0}%",
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
        f"<b>Sending to {total} members...</b>\n[{progress_bar(0, total)}]",
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
                    f"[{progress_bar(i, total)}] {i}/{total}\n✅ {sent} | ❌ {failed}",
                    parse_mode="HTML")
            except: pass
        await asyncio.sleep(0.08)
    await m.edit_text(
        f"✅ <b>Broadcast Done!</b>\n{_D}\n\n"
        f"▸ <b>Members:</b> {total}\n▸ <b>Delivered:</b> {sent}\n▸ <b>Failed:</b> {failed}",
        parse_mode="HTML")

# ═══════════════════════════════════════════════════════════════════════════════
#                     📊 STATS / INFO
# ═══════════════════════════════════════════════════════════════════════════════
@owner_only
async def botstats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Compiling stats")
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
    total_coins = db.execute("SELECT COALESCE(SUM(coins+bank),0) as c FROM users").fetchone()["c"]
    db.close()
    uptime = datetime.datetime.now(pytz.utc) - START_TIME
    s = int(uptime.total_seconds())
    upstr = f"{s//86400}d {(s%86400)//3600}h {(s%3600)//60}m {s%60}s"
    bar = progress_bar(s % 86400, 86400)
    api_names = ["🌸 Pollinations", "⚡ Custom GPT-4", "💎 Gemini"]
    cur_api = api_names[_ai_api_index % 3]

    await finish_anim(m,
        f"📊 <b>NEXUS BOT STATS</b> — v{VERSION}\n{_D}\n\n"
        f"🌍 <b>REACH</b>\n"
        f"▸ Chats: <b>{chats:,}</b> · Users: <b>{users:,}</b>\n"
        f"▸ Members tracked: <b>{members:,}</b>\n"
        f"▸ Federations: <b>{feds:,}</b>\n"
        f"{_D}\n"
        f"⚠️ <b>MODERATION</b>\n"
        f"▸ Warns: <b>{warns:,}</b> · Bans: <b>{bans:,}</b>\n"
        f"▸ Global bans: <b>{gbans:,}</b>\n"
        f"▸ Notes: <b>{notes:,}</b> · Filters: <b>{filters_:,}</b>\n"
        f"{_D}\n"
        f"💰 <b>ECONOMY</b>\n"
        f"▸ Total coins in circulation: <b>{total_coins:,} 🪙</b>\n"
        f"{_D}\n"
        f"🤖 <b>AI ENGINE</b>\n"
        f"▸ Active API: {cur_api}\n"
        f"▸ Failover: 3-API rotating system\n"
        f"{_D}\n"
        f"⏱️ <b>Uptime:</b> {upstr}\n"
        f"[{bar}]"
    )

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = (update.message.reply_to_message.from_user
              if update.message.reply_to_message else update.effective_user)
    chat = update.effective_chat
    lines = [
        f"🆔 <b>IDs</b>\n{_D}\n\n"
        f"▸ <b>User ID:</b> <code>{target.id}</code>\n"
        f"▸ <b>Chat ID:</b> <code>{chat.id}</code>"
    ]
    if update.message.reply_to_message and update.message.reply_to_message.forward_from:
        ff = update.message.reply_to_message.forward_from
        lines.append(f"\n▸ <b>Forward from ID:</b> <code>{ff.id}</code>")
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
    lvl_bar = progress_bar(msgs % max(lvl * 100, 1), max(lvl * 100, 1))

    text = (
        f"👤 <b>User Profile</b>\n{_D}\n\n"
        f"▸ <b>Name:</b> <a href='tg://user?id={target.id}'>{name}</a>\n"
        f"▸ <b>ID:</b> <code>{target.id}</code>\n"
    )
    if getattr(target, "username", None): text += f"▸ @{html.escape(target.username)}\n"
    if badges: text += f"▸ <b>Badges:</b> {badges}\n"
    if row:
        text += (
            f"{_D}\n"
            f"⭐ <b>Level {lvl}</b> — {level_title(lvl)}\n"
            f"[{lvl_bar}]\n"
            f"{_D}\n"
            f"▸ <b>Wallet:</b> {coins:,} 🪙 · <b>Bank:</b> {bank:,}\n"
            f"▸ <b>Reputation:</b> {rep} ⭐\n"
            f"▸ <b>Messages:</b> {msgs:,}\n"
            f"▸ <b>Warns:</b> {warns}\n"
        )
        if cm_row:
            text += f"▸ <b>Chat rank:</b> #{cm_row['rank']} ({cm_row['msgs']} msgs)\n"
    if row and row["is_gbanned"]:
        text += f"\n🚫 <b>GLOBALLY BANNED</b>\n▸ {html.escape(row['gban_reason'] or 'No reason')}"
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
            f"💬 <b>Chat Info</b>\n{_D}\n\n"
            f"▸ <b>Title:</b> {html.escape(chat.title or 'N/A')}\n"
            f"▸ <b>ID:</b> <code>{chat.id}</code>\n"
            f"▸ <b>Type:</b> {chat.type.title()}\n"
            f"▸ <b>Members:</b> {members:,}\n"
            f"▸ <b>Admins:</b> {len(admins)}\n"
            f"{_D}\n"
            f"▸ <b>Tracked:</b> {tracked} members\n"
            f"▸ <b>Notes:</b> {notes}\n"
            f"▸ <b>Filters:</b> {filters_count}\n"
        )
        if chat.username: text += f"▸ @{chat.username}"
        if chat.description: text += f"\n▸ {html.escape(chat.description[:100])}"
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
    uptime = datetime.datetime.now(pytz.utc) - START_TIME
    s = int(uptime.total_seconds())
    upstr = f"{s//86400}d {(s%86400)//3600}h {(s%3600)//60}m {s%60}s"
    if m:
        await m.edit_text(
            f"🏓 <b>PONG!</b> {kmo(KAOMOJI_VIBE)}\n{_D}\n\n"
            f"▸ <b>Latency:</b> <code>{elapsed:.1f}ms</code> — {quality}\n"
            f"▸ <b>Uptime:</b> {upstr}\n"
            f"▸ <b>Version:</b> <code>{VERSION}</code>",
            parse_mode="HTML")

async def uptime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.datetime.now(pytz.utc) - START_TIME
    s = int(uptime.total_seconds())
    upstr = f"{s//86400}d {(s%86400)//3600}h {(s%3600)//60}m {s%60}s"
    bar   = progress_bar(s % 86400, 86400)
    await reply(update,
        f"⏱️ <b>Uptime</b>\n{_D}\n\n"
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
        lines = [f"💰 <b>Richest Members</b>\n{_D}\n"]
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
        lines = [f"💬 <b>Most Active</b>\n{_D}\n"]
        for i, row in enumerate(rows):
            name = html.escape(row["first_name"] or str(row["user_id"]))
            msgs = row["msgs"] or 0
            lines.append(f"{medals[i] if i<10 else '•'} <a href='tg://user?id={row['user_id']}'>{name}</a>\n"
                         f"   <b>{msgs:,}</b> 💬 — Lvl {level_from_msgs(msgs)}")
    elif tab == "rep":
        rows = db.execute("SELECT user_id, first_name, reputation FROM users ORDER BY reputation DESC LIMIT 10").fetchall()
        lines = [f"⭐ <b>Reputation Leaders</b>\n{_D}\n"]
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
    tabs_row = [
        InlineKeyboardButton("💰 Coins" + (" ◀" if tab=="coins" else ""), callback_data="lb:coins"),
        InlineKeyboardButton("💬 Activity" + (" ◀" if tab=="msgs" else ""), callback_data="lb:msgs"),
        InlineKeyboardButton("⭐ Reputation" + (" ◀" if tab=="rep" else ""), callback_data="lb:rep"),
    ]
    kb = InlineKeyboardMarkup([tabs_row, [InlineKeyboardButton("🔄 Refresh", callback_data=f"lb:{tab}")]])
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
    target = await get_target(update, context) or update.effective_user
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
    next_lvl_msgs = max(lvl * 100, 1)
    progress = msgs % next_lvl_msgs
    bar  = progress_bar(progress, next_lvl_msgs, length=15)
    rank_icon = rank_badge(rank)
    name = html.escape(getattr(target, "first_name", "") or str(target.id))
    text = (
        f"🏆 <b>Rank Card</b> — {name[:15]}\n{_D}\n\n"
        f"{rank_icon} <b>Rank #{rank}</b> of {total} members\n"
        f"{_D}\n"
        f"⭐ <b>Level {lvl}</b> — <i>{lvl_title}</i>\n"
        f"[{bar}] {progress}/{next_lvl_msgs}\n"
        f"{_D}\n"
        f"▸ <b>Messages:</b> {msgs:,}\n"
    )
    if u_row:
        text += (
            f"▸ <b>Coins:</b> {u_row['coins']:,} 🪙\n"
            f"▸ <b>Reputation:</b> {u_row['reputation']} ⭐\n"
        )
    await reply(update, text)

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    rows = db.execute(
        "SELECT user_id, first_name, msgs FROM chat_members WHERE chat_id=? AND is_bot=0 "
        "ORDER BY msgs DESC LIMIT 10",
        (update.effective_chat.id,)).fetchall()
    db.close()
    if not rows: return await reply(update, "❌ <b>No activity data yet!</b>")
    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    top_name = html.escape(rows[0]["first_name"] or str(rows[0]["user_id"])) if rows else "someone"
    ai_comment = await ai_reply(
        f"Write one short Gen Z comment about '{top_name}' being the most active member in a group chat. "
        "1 sentence, hype energy. No intro. Emojis. Plain text.",
        fallback=random.choice([
            f"{top_name} really said main character energy and we respect it fr 👑",
            f"the most active member has been found and they are NOT normal fr 🔥",
            f"{top_name} on top and it's not even close bestie no cap 🏆",
        ])
    )
    lines = [
        f"🏆 <b>Top Active Members</b>\n{_D}\n",
        f"<i>{html.escape(ai_comment)}</i>\n",
    ]
    for i, row in enumerate(rows):
        name = html.escape(row["first_name"] or str(row["user_id"]))
        bar = progress_bar(row["msgs"], max(rows[0]["msgs"], 1), length=8)
        lines.append(f"{medals[i]} <a href='tg://user?id={row['user_id']}'>{name}</a> — <b>{row['msgs']:,}</b> msgs [{bar}]")
    await reply(update, "\n".join(lines))

# ─── REP ──────────────────────────────────────────────────────────────────────
async def rep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context)
    if not target:
        db = get_db()
        row = db.execute("SELECT reputation FROM users WHERE user_id=?",
                         (update.effective_user.id,)).fetchone()
        db.close()
        rep = row["reputation"] if row else 0
        return await reply(update,
            f"⭐ <b>Your Reputation</b>\n{_D}\n\n"
            f"▸ <b>Rep:</b> {rep}\n"
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
    ai_comment = await ai_reply(
        f"Write one short Gen Z compliment for someone who just received reputation in a group chat "
        f"and now has {rep} total rep points. Hype, warm, 1 sentence. No intro. Emojis. Plain text.",
        fallback=random.choice([
            f"the rep just hit different fr — recognized and appreciated bestie ⭐",
            f"glowing up in the reputation charts no cap fr fr 🌟",
            f"community said YES and we agree periodt ✨",
        ])
    )
    await reply(update,
        f"⭐ <b>Reputation Given!</b>\n{_D}\n\n"
        f"🎁 {user_link(update.effective_user)} → ⭐ +1 → {user_link(target)}\n"
        f"▸ <b>Total Rep:</b> {rep} {stars_bar(min(rep, 5))}\n\n"
        f"<i>{html.escape(ai_comment)}</i>"
    )

async def reprank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_leaderboard(update, context, "rep")

async def level_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context) or update.effective_user
    db = get_db()
    row = db.execute("SELECT total_msgs FROM users WHERE user_id=?", (target.id,)).fetchone()
    db.close()
    msgs = row["total_msgs"] if row else 0
    lvl  = level_from_msgs(msgs)
    next_msgs = max(lvl * 100, 1)
    bar  = progress_bar(msgs % next_msgs, next_msgs, length=15)
    await reply(update,
        f"⭐ <b>Level</b>\n{_D}\n\n"
        f"▸ {user_link(target)}\n"
        f"{_D}\n"
        f"⭐ <b>Level {lvl}</b> — {level_title(lvl)}\n"
        f"[{bar}]\n"
        f"▸ {msgs:,} / {next_msgs*(lvl+1)} msgs to next level"
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                         💰 ECONOMY
# ═══════════════════════════════════════════════════════════════════════════════
async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(update.effective_user)
    db = get_db()
    row = db.execute("SELECT last_daily, coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    now = datetime.datetime.now(pytz.utc)
    if row and row["last_daily"]:
        try:
            last = datetime.datetime.fromisoformat(str(row["last_daily"]).replace(" ", "T")).replace(tzinfo=pytz.utc)
            diff = (now - last).total_seconds()
            if diff < 86400:
                left = int(86400 - diff)
                h, m = left // 3600, (left % 3600) // 60
                return await reply(update,
                                        f"😭 bestie you already claimed today lmaoo {kmo(KAOMOJI_SAD)}\n"
                    f"⏰ <b>chill for {h}h {m}m</b> then come back fr fr"
                )
        except: pass
    # 5% chance of a bonus daily reward (1.5×)
    reward = random.randint(400, 800)
    bonus_txt = ""
    if random.random() < 0.05:
        reward = int(reward * 1.5)
        bonus_txt = "\n🎊 <b>LUCKY DAY! +50% bonus coins!</b>"
    db = get_db()
    db.execute("UPDATE users SET coins=coins+?, last_daily=? WHERE user_id=?",
               (reward, now.isoformat(), user_id))
    db.commit(); db.close()

    m, ai_msg = await asyncio.gather(
        animate_loading(update, "Preparing daily reward"),
        ai_reply(
            f"Write one short Gen Z hype sentence congratulating someone on claiming their daily reward of {reward} coins. "
            "1 sentence, celebratory, emojis. No intro. Plain text only.",
            fallback=random.choice([
                f"you showed up for the daily and the bag rewarded you fr no cap 💰",
                f"daily grind energy is REAL and you ate bestie periodt 🎁",
                f"every day is bag day when you're built different fr 💅",
                f"the daily was waiting for you and you DELIVERED no cap 🚀",
            ]),
        ),
    )
    await finish_anim(m,
        f"🎁 <b>DAILY CLAIM UNLOCKED</b> {kmo(KAOMOJI_MONEY)}\n{_D}\n\n"
        f"💰 <b>+{reward:,} 🪙 secured!</b>{bonus_txt}\n\n"
        f"<i>{html.escape(ai_msg)}</i>\n\n"
        f"📅 <i>come back in 24hrs. daily grind slay periodt ✨</i>"
    )

async def work_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(update.effective_user)
    now = time.time()
    if user_id in work_cd and now - work_cd[user_id] < 3600:
        left = int(3600 - (now - work_cd[user_id]))
        m, s = left // 60, left % 60
        return await reply(update,
                        f"😩 bestie you literally just worked lmao {kmo(KAOMOJI_SAD)}\n"
            f"⏰ <b>rest {m}m {s}s</b> more then come back and grind fr"
        )
    jobs = [
        ("🧑‍💻 coded a full-stack web app", 150, 500),
        ("🎨 designed a viral brand logo", 120, 400),
        ("📦 delivered packages all day", 80, 280),
        ("🍕 delivered 50 pizzas in record time", 70, 220),
        ("🔧 fixed a critical production bug", 200, 600),
        ("📚 tutored 5 struggling students", 100, 350),
        ("🎮 live-streamed and hit 1k viewers", 180, 550),
        ("🌟 wrote a viral article", 120, 380),
        ("🚗 drove rideshare all night", 100, 320),
        ("🌱 landscaped a mansion garden", 80, 250),
        ("🎵 produced a beat for an artist", 200, 700),
        ("📸 shot a brand photoshoot", 150, 450),
        ("🤖 trained an AI model for a startup", 300, 900),
        ("🛸 consulted for a tech company", 250, 800),
        ("🧪 ran a scientific experiment", 120, 400),
        ("✍️ ghostwrote a bestselling chapter", 180, 550),
        ("🏗️ helped build a new server rack", 100, 350),
        ("🎤 performed at a local event", 200, 600),
        ("🔍 did quality testing for a game", 150, 480),
        ("💹 executed a profitable trade", 200, 1000),
    ]
    job, low, high = random.choice(jobs)
    # bonus multiplier: 10% chance of 2× pay
    earned = random.randint(low, high)
    bonus = ""
    if random.random() < 0.10:
        earned = earned * 2
        bonus = "\n🎉 <b>BONUS PAYDAY! 2× earnings activated!</b>"
    work_cd[user_id] = now

    m, ai_story = await asyncio.gather(
        animate_loading(update, "Clocking out"),
        ai_reply(
            f"Write one short funny Gen Z sentence about someone who just finished this job: '{job}'. "
            "They earned money. 1 sentence, chaotic energy, emojis. No intro. Plain text only.",
            fallback=f"you {job} and secured the absolute bag fr no cap bestie 💅",
        ),
    )
    db = get_db()
    db.execute("UPDATE users SET coins=coins+?, last_work=CURRENT_TIMESTAMP WHERE user_id=?",
               (earned, user_id))
    db.commit(); db.close()
    await finish_anim(m,
        f"💼 <b>GRIND COMPLETE</b> {kmo(KAOMOJI_MONEY)}\n{_D}\n\n"
        f"▸ <b>Job:</b> {job}\n"
        f"▸ <b>Earned:</b> <b>+{earned:,} 🪙</b>{bonus}\n\n"
        f"<i>{html.escape(ai_story)}</i>\n\n"
        f"⏰ <i>come back in 1hr to grind again. bag mentality periodt 💰</i>"
    )

async def mine_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(update.effective_user)
    now = time.time()

    # 30-minute cooldown
    MINE_CD = 1800
    last = mine_cd.get(user_id, 0)
    remaining = MINE_CD - (now - last)
    if remaining > 0:
        m2 = int(remaining // 60)
        s2 = int(remaining % 60)
        return await reply(update,
            f"⛏️ <b>your pickaxe is recharging bestie</b> {kmo(KAOMOJI_SAD)}\n"
            f"⏰ <b>ready in {m2}m {s2}s</b> — skill issue (jk we love u) 💎"
        )

    # Weighted ore tier system
    tier_roll = random.random()
    if tier_roll < 0.02:        # 2% — Mythic jackpot
        tier = "mythic"
    elif tier_roll < 0.08:      # 6% — Legendary
        tier = "legendary"
    elif tier_roll < 0.20:      # 12% — Rare
        tier = "rare"
    elif tier_roll < 0.42:      # 22% — Uncommon
        tier = "uncommon"
    elif tier_roll < 0.75:      # 33% — Common
        tier = "common"
    else:                       # 25% — Stone (low)
        tier = "stone"

    # Event rarity: 3% cave-in (0 coins), 2% double strike
    event = None
    event_roll = random.random()
    if event_roll < 0.03:
        event = "cave_in"
    elif event_roll < 0.05:
        event = "double_strike"

    ore_data = {
        "mythic":    ("🌟 Nexus Crystal", 1500, 5000),
        "legendary": ("💎 Diamond Vein",   600, 1500),
        "rare":      ("🔮 Amethyst",        250,  600),
        "uncommon":  ("🥇 Gold Nugget",      80,  250),
        "common":    ("⚙️ Iron Ore",         30,   80),
        "stone":     ("🪨 Stone Chunk",       5,   30),
    }
    ore_name, low_r, high_r = ore_data[tier]
    found = random.randint(low_r, high_r)

    bonus_msg = ""
    special_event_msg = ""

    if event == "cave_in":
        found = 0
        special_event_msg = "\n\n💀 <b>CAVE-IN!</b> You barely escaped with your life... and no coins 😭"
    elif event == "double_strike":
        found *= 2
        special_event_msg = "\n\n⚡ <b>DOUBLE STRIKE!</b> You hit two veins at once! 2× coins fr!"

    # 5% jackpot bonus on top of mythic
    if tier == "mythic" and event != "cave_in":
        jackpot_extra = random.randint(1000, 3000)
        found += jackpot_extra
        bonus_msg = f"\n🏆 <b>JACKPOT BONUS:</b> +{jackpot_extra:,} extra 🪙!!"

    mine_cd[user_id] = now

    tier_badges = {
        "mythic":    "🌟 MYTHIC",
        "legendary": "💎 LEGENDARY",
        "rare":      "🔮 RARE",
        "uncommon":  "🥇 UNCOMMON",
        "common":    "⚙️ COMMON",
        "stone":     "🪨 STONE",
    }
    badge = tier_badges[tier]

    m, ai_story = await asyncio.gather(
        animate_loading(update, "Swinging pickaxe"),
        ai_reply(
            f"Write one short funny Gen Z sentence about a miner who found '{ore_name}' "
            f"and got {found} coins. {'They barely escaped a cave-in with nothing.' if event == 'cave_in' else ''}"
            "1 sentence, chaotic energy, emojis. No intro. Plain text only.",
            fallback=random.choice([
                f"bestie just swung a pickaxe and found {ore_name} like an actual legend no cap ⛏️",
                f"the mine was bussin fr — {ore_name} just dropped periodt 💎",
                f"mining arc activated and it ATE — {ore_name} secured 🔥",
                f"grind never stops and the mine said HERE, TAKE THIS 💎 fr fr",
            ]),
        ),
    )

    if found > 0:
        db = get_db()
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (found, user_id))
        db.commit(); db.close()

    rarity_color = {
        "mythic": "🌈", "legendary": "✨", "rare": "💫",
        "uncommon": "⭐", "common": "▸", "stone": "▸",
    }
    rc = rarity_color.get(tier, "▸")

    await finish_anim(m,
        f"⛏️ <b>MINING REPORT</b> {kmo(KAOMOJI_MONEY)}\n{_D}\n\n"
        f"{rc} <b>Ore:</b> {ore_name} — [{badge}]\n"
        f"{rc} <b>Earned:</b> <b>+{found:,} 🪙</b>{bonus_msg}"
        f"{special_event_msg}\n\n"
        f"<i>{html.escape(ai_story)}</i>\n\n"
        f"⏰ <i>pickaxe recharges in 30min. stay mining bestie fr</i>"
    )

async def coins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context) or update.effective_user
    ensure_user(target)
    db = get_db()
    row = db.execute("SELECT coins, bank FROM users WHERE user_id=?", (target.id,)).fetchone()
    db.close()
    wallet = row["coins"] if row else 0
    bank   = row["bank"]  if row else 0
    total  = wallet + bank
    bar    = progress_bar(min(wallet, 10000), 10000)
    wealth_tier = (
        "🌟 Nexus Whale" if total >= 50000 else
        "💎 Diamond Rich" if total >= 20000 else
        "🥇 Gold Stacker" if total >= 10000 else
        "💰 Getting there" if total >= 3000 else
        "🪙 Just started"
    )
    await reply(update,
        f"💰 <b>Wallet</b> — {user_link(target)}\n{_D}\n\n"
        f"🪙 <b>Wallet:</b> {wallet:,}\n"
        f"[{bar}]\n"
        f"🏦 <b>Bank:</b> {bank:,}\n"
        f"▸ <b>Net Worth:</b> {total:,} 🪙\n"
        f"{_D}\n"
        f"🏷️ <i>{wealth_tier}</i>"
    )

async def bank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    ensure_user(update.effective_user)
    if not context.args or context.args[0] not in ("deposit", "withdraw", "balance"):
        return await reply(update,
            f"🏦 <b>Bank of Nexus</b>\n{_D}\n\n"
            "▸ <code>/bank deposit N</code> — secure your bag\n"
            "▸ <code>/bank withdraw N</code> — pull coins out\n"
            "▸ <code>/bank balance</code> — check your vaults\n\n"
            "<i>Bank protects your coins from robbers! 🛡️</i>"
        )
    action = context.args[0]
    db = get_db()
    row = db.execute("SELECT coins, bank FROM users WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    wallet = row["coins"] if row else 0
    bank   = row["bank"]  if row else 0
    if action == "balance":
        bar_w = progress_bar(min(wallet, 10000), 10000)
        bar_b = progress_bar(min(bank, 50000), 50000)
        return await reply(update,
            f"🏦 <b>Bank of Nexus</b>\n{_D}\n\n"
            f"🪙 <b>Wallet:</b> {wallet:,}\n[{bar_w}]\n"
            f"🏦 <b>Bank:</b> {bank:,}\n[{bar_b}]\n"
            f"{_D}\n"
            f"▸ <b>Net Worth:</b> {wallet+bank:,} 🪙"
        )
    try: amount = int(context.args[1]) if len(context.args) > 1 else 0
    except: return await reply(update, "❌ <b>Invalid amount!</b>")
    if amount <= 0: return await reply(update, "❌ <b>Amount must be positive!</b>")
    if action == "deposit":
        if wallet < amount: return await reply(update,
            f"❌ <b>Not enough in wallet!</b>\n▸ Wallet: {wallet:,} 🪙")
        db = get_db()
        db.execute("UPDATE users SET coins=coins-?, bank=bank+? WHERE user_id=?", (amount, amount, user_id))
        db.commit(); db.close()
        await reply(update,
            f"🏦 <b>Deposited Successfully!</b>\n{_D}\n\n"
            f"▸ <b>Deposited:</b> {amount:,} 🪙\n"
            f"▸ <b>Wallet:</b> {wallet-amount:,} 🪙\n"
            f"▸ <b>Bank:</b> {bank+amount:,} 🪙 🔐")
    else:
        if bank < amount: return await reply(update,
            f"❌ <b>Not enough in bank!</b>\n▸ Bank: {bank:,} 🪙")
        db = get_db()
        db.execute("UPDATE users SET bank=bank-?, coins=coins+? WHERE user_id=?", (amount, amount, user_id))
        db.commit(); db.close()
        await reply(update, f"💳 <b>Withdrew {amount:,} coins!</b>\n▸ Wallet: {wallet+amount:,} · Bank: {bank-amount:,}")

async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2 and not (update.message.reply_to_message and context.args):
        return await reply(update, "❓ <b>Usage:</b> <code>/give @user amount</code>")
    target = await get_target(update, context)
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
        f"💸 <b>Coins Sent!</b>\n{_D}\n\n"
        f"▸ <b>Amount:</b> {amount:,} 🪙\n"
        f"▸ <b>From:</b> {user_link(update.effective_user)}\n"
        f"▸ <b>To:</b> {user_link(target)}\n{_D}\n"
        f"▸ <b>Your balance:</b> {new_bal:,} 🪙"
    )

async def rob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context)
    if not target: return await reply(update,
        f"❓ <b>Rob someone!</b>\n{_D}\n"
        f"<i>Reply to a user or use /rob @username</i>")
    if target.id == update.effective_user.id: return await reply(update,
        f"❌ <b>Can't rob yourself bestie 💀</b>\n<i>That's not how crime works fr</i>")
    robber = update.effective_user
    db = get_db()
    victim = db.execute("SELECT coins FROM users WHERE user_id=?", (target.id,)).fetchone()
    if not victim or victim["coins"] < 100:
        db.close()
        return await reply(update,
            f"😭 <b>ROB FAILED</b> {kmo(KAOMOJI_LOSE)}\n{_D}\n\n"
            f"▸ {user_link(target)} is literally broke bestie 💀\n"
            f"▸ <i>they need at least 100 🪙 to be worth robbing fr</i>")

    caught = random.random() < 0.42

    if caught:
        fine = random.randint(80, 300)
        m, ai_story = await asyncio.gather(
            animate_loading(update, "The heist went wrong"),
            ai_reply(
                f"Write one funny Gen Z sentence about a criminal who got caught trying to rob someone "
                f"and had to pay a {fine} coin fine. 1 sentence, chaotic, emojis. No intro. Plain text.",
                fallback=random.choice([
                    f"bestie really tried to rob someone and got CAUGHT — the audacity 💀",
                    f"the law said ABSOLUTELY NOT and slapped a fine on it fr",
                    f"criminal arc ended before it even started. that's an L periodt 👮",
                ])
            ),
        )
        db.execute("UPDATE users SET coins=MAX(0, coins-?) WHERE user_id=?", (fine, robber.id))
        db.commit(); db.close()
        await finish_anim(m,
            f"👮 <b>CAUGHT IN 4K</b> {kmo(KAOMOJI_BAN)}\n{_D}\n\n"
            f"🚔 {user_link(robber)} tried to rob {user_link(target)}\n"
            f"▸ <b>Fine paid:</b> {fine:,} 🪙 — ratio + L\n\n"
            f"<i>{html.escape(ai_story)}</i>"
        )
    else:
        stolen = random.randint(50, min(600, victim["coins"]))
        m, ai_story = await asyncio.gather(
            animate_loading(update, "Executing the heist"),
            ai_reply(
                f"Write one funny Gen Z sentence about a successful heist where someone stole {stolen} coins. "
                "1 sentence, triumphant chaos energy, emojis. No intro. Plain text only.",
                fallback=random.choice([
                    f"the heist WENT OFF and nobody saw it coming fr bestie 🦹",
                    f"smooth criminal behavior — stole the bag and left no trace 💎",
                    f"absolute villain arc moment. the coins are secured no cap 🔥",
                ])
            ),
        )
        db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (stolen, target.id))
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (stolen, robber.id))
        db.commit(); db.close()
        await finish_anim(m,
            f"🦹 <b>HEIST SUCCESSFUL</b> {kmo(KAOMOJI_WIN)}\n{_D}\n\n"
            f"💰 {user_link(robber)} robbed {user_link(target)}\n"
            f"▸ <b>Stolen:</b> <b>{stolen:,} 🪙</b> secured!\n\n"
            f"<i>{html.escape(ai_story)}</i>"
        )

async def flip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        m = await animate_loading(update, "Flipping coin")
        result = "Heads 🦅" if random.random() > 0.5 else "Tails 🪙"
        ai_comment = await ai_reply(
            f"Write one short Gen Z reaction to a coin landing on '{result}'. No intro. 1 sentence. Emojis. Plain text.",
            fallback="the coin has spoken and we respect the decision fr no cap 🪙",
        )
        await finish_anim(m,
            f"🪙 <b>COIN FLIP</b> {kmo(KAOMOJI_VIBE)}\n{_D}\n\n"
            f"▸ <b>Result: {result}!</b>\n\n"
            f"<i>{html.escape(ai_comment)}</i>"
        )
        return

    amount = int(context.args[0])
    if amount <= 0: return await reply(update, "❌ <b>Amount must be positive!</b>")
    user_id = update.effective_user.id
    ensure_user(update.effective_user)
    db = get_db()
    row = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row or row["coins"] < amount:
        db.close()
        return await reply(update,
            f"❌ <b>Not enough coins!</b>\n"
            f"▸ You have <b>{(row['coins'] if row else 0):,} 🪙</b>")

    won = random.random() > 0.5
    if won:
        db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (amount, user_id))
        ai_comment = await ai_reply(
            f"Write one short Gen Z celebration for winning a {amount} coin coin flip. "
            "1 sentence, triumphant energy. No intro. Emojis. Plain text.",
            fallback=random.choice([
                "the coin said YES and we respect that fr no cap 🦅",
                "HEADS and the bag is secured bestie periodt 💰",
                "winning arc activated — coin flip W no debate 🔥",
            ])
        )
        result_text = (
            f"🦅 <b>HEADS — YOU WIN!</b> {kmo(KAOMOJI_WIN)}\n{_D}\n\n"
            f"▸ <b>+{amount:,} 🪙</b> secured bestie!\n\n"
            f"<i>{html.escape(ai_comment)}</i>"
        )
    else:
        db.execute("UPDATE users SET coins=coins-? WHERE user_id=?", (amount, user_id))
        ai_comment = await ai_reply(
            f"Write one short funny Gen Z reaction to losing {amount} coins on a coin flip. "
            "1 sentence, chaotic sadness. No intro. Emojis. Plain text.",
            fallback=random.choice([
                "the coin said L and we have to respect it 😭 coin said no fr",
                "tails... the coins escaped the wallet. tragic periodt 💀",
                "L + ratio + coin flip gone wrong. skill issue fr 🪙",
            ])
        )
        result_text = (
            f"🪙 <b>TAILS — YOU LOSE</b> {kmo(KAOMOJI_LOSE)}\n{_D}\n\n"
            f"▸ <b>-{amount:,} 🪙</b> gone fr\n\n"
            f"<i>{html.escape(ai_comment)}</i>"
        )

    bal = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()["coins"]
    db.commit(); db.close()
    await reply(update, result_text + f"\n{_D}\n▸ <b>Balance:</b> {bal:,} 🪙")

async def slots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symbols = ["🍒","🍋","🍊","💎","7️⃣","⭐","🍇","🔔"]
    weights = [25, 20, 18, 8, 4, 10, 10, 5]
    user_id = update.effective_user.id
    ensure_user(update.effective_user)
    amount = 0
    if context.args and context.args[0].isdigit():
        amount = int(context.args[0])
        if amount > 0:
            db = get_db()
            row = db.execute("SELECT coins FROM users WHERE user_id=?", (user_id,)).fetchone()
            db.close()
            if not row or row["coins"] < amount:
                return await reply(update,
                    f"❌ <b>Not enough coins to bet!</b>\n"
                    f"▸ You have <b>{(row['coins'] if row else 0):,} 🪙</b>")

    m = await animate_loading(update, "Loading the casino")
    for _ in range(3):
        spin = " │ ".join(random.choices(symbols, k=3))
        try: await m.edit_text(f"🎰 <b>Spinning...</b>\n\n┃ {spin} ┃", parse_mode="HTML")
        except: pass
        await asyncio.sleep(0.4)

    roll   = random.choices(symbols, weights=weights, k=3)
    result = " │ ".join(roll)

    if roll[0] == roll[1] == roll[2]:
        multiplier = 15 if roll[0] == "7️⃣" else (10 if roll[0] == "💎" else (6 if roll[0] == "⭐" else 4))
        winnings   = max(amount * multiplier, 50) if amount else 0
        ai_comment = await ai_reply(
            f"Write one short Gen Z jackpot celebration for winning {winnings} coins on slots with triple {roll[0]}. "
            "1 sentence, absolute chaos, emojis. No intro. Plain text.",
            fallback=random.choice([
                "THE JACKPOT LANDED AND WE ARE NOT OKAY FR 🎰💎",
                "slots said YES and the bag said SECURED bestie no cap 🎉",
                "triple drop — casino LOST and we WON periodt 💅",
            ])
        )
        outcome = (
            f"🎉 <b>JACKPOT!!!</b> {kmo(KAOMOJI_WIN)}\n"
            f"▸ <b>+{winnings:,} 🪙</b> (×{multiplier})\n\n"
            f"<i>{html.escape(ai_comment)}</i>"
        )
        if amount:
            db = get_db()
            db.execute("UPDATE users SET coins=coins+? WHERE user_id=?", (winnings, user_id))
            db.commit(); db.close()
    elif roll[0] == roll[1] or roll[1] == roll[2] or roll[0] == roll[2]:
        ai_comment = await ai_reply(
            "Write one short Gen Z reaction to getting a pair on a slot machine — bet returned. "
            "1 sentence, neutral energy. No intro. Emojis. Plain text.",
            fallback="a pair! bet returned bestie — could've been worse ngl ✨",
        )
        outcome = (
            f"✨ <b>PAIR — BET RETURNED</b> {kmo(KAOMOJI_VIBE)}\n"
            f"▸ No gain, no loss. Neutral arc.\n\n"
            f"<i>{html.escape(ai_comment)}</i>"
        )
    else:
        ai_comment = await ai_reply(
            f"Write one short funny Gen Z reaction to losing {amount} coins on a slot machine. "
            "1 sentence, dramatic sadness. No intro. Emojis. Plain text.",
            fallback=random.choice([
                "slots ate the coins and left nothing behind. tragic periodt 🎰",
                "the casino won this round but we keep going fr 💀",
                "L + no match + the reels did NOT cooperate bestie",
            ])
        )
        outcome = (
            f"💀 <b>NO MATCH</b> {kmo(KAOMOJI_LOSE)}\n"
            f"▸ <b>-{amount:,} 🪙</b> gone\n\n"
            f"<i>{html.escape(ai_comment)}</i>"
        )
        if amount:
            db = get_db()
            db.execute("UPDATE users SET coins=MAX(0,coins-?) WHERE user_id=?", (amount, user_id))
            db.commit(); db.close()

    await finish_anim(m,
        f"🎰 <b>SLOT MACHINE</b> {kmo(KAOMOJI_HYPE)}\n{_D}\n\n"
        f"┃  {result}  ┃\n\n"
        f"{outcome}"
    )

# ─── SHOP ─────────────────────────────────────────────────────────────────────
async def shop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    items = db.execute("SELECT * FROM shop_items ORDER BY price").fetchall()
    db.close()
    lines = [f"🛍️ <b>Shop</b>\n{_D}\n"]
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
                               f"▸ Spent: {item['price']:,} 🪙", parse_mode="HTML")

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
        f"▸ Spent: {item['price']:,} 🪙\n"
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
    lines = [f"🎒 <b>Inventory</b>\n{_D}\n"]
    for r in rows:
        lines.append(f"▸ {r['name']} ×{r['quantity']}  —  <i>{r['description']}</i>")
    await reply(update, "\n".join(lines))

# ═══════════════════════════════════════════════════════════════════════════════
#                         🎮 FUN & GAMES
# ═══════════════════════════════════════════════════════════════════════════════
EIGHTBALL_ANSWERS = [
    "🟢 bestie yes omg absolutely slay!!",
    "🟢 no cap that's a YES fr fr 💅",
    "🟢 the universe said YES and so do i ✨",
    "🟢 it's giving YES energy rn 🔮",
    "🟢 periodt. YES. we move 🚀",
    "🟢 that's so real, yas queen YES 👑",
    "🟡 idk bestie... the vibes are chaotic rn 😵‍💫",
    "🟡 ask again when mercury isn't retrograde 🪐",
    "🟡 the algorithm is loading... brb 💀",
    "🟡 not the answer i expected to give but... maybe?",
    "🔴 bestie no. that's a flop era 💀",
    "🔴 it's giving absolutely NOT, no cap 🚫",
    "🔴 nah fam. delete the idea rn 🗑️",
    "🔴 the vibes said NO and honestly respect that 🙅",
    "🔴 that's so not it chief 😭",
    "🔴 hard pass, slay elsewhere bestie 💅",
]

FACTS = [
    "🧠 Honey never spoils — archaeologists found 3000-year-old honey in Egyptian tombs!",
    "🐙 Octopuses have three hearts and blue blood!",
    "🌍 A day on Venus is longer than a year on Venus!",
    "🦷 Sharks are older than trees — they've existed for 450 million years!",
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
    "💀 me: i'll go to sleep early\nalso me at 3am: researching if penguins have knees",
    "😭 my situationship watching me write 'we need to talk' and then say 'nvm sorry wrong chat'",
    "💅 therapist: and what do we do when we're stressed?\nme: order food and spiral\ntherapist: no\nme: too late",
    "🪦 me: i'm deleting twitter\n*opens twitter*\nme: just one more scroll",
    "😂 the audacity of my brain sending anxiety at 2am about something from 7 years ago",
    "💀 plot twist: you were the toxic one all along 😇",
    "🫠 me pretending to understand something in a meeting so i don't have to ask again",
    "📱 me: i'm not on my phone that much\nalso me: *6 hours of screen time notification*",
    "😭 eating healthy for 3 days and checking if i have abs yet",
    "🫢 my roman empire: that thing i said in 2016 that nobody remembers except me",
    "💀 adulting is just googling things and then being more confused",
    "🤡 me: i'll just rest my eyes\n*wakes up 4 hours later*\n*it's dark outside*",
]

TRUTHS = [
    "spill the tea ☕ — what's the most chaotic thing you've done and never told anyone?",
    "be fr rn... do you have a situationship? don't lie 👀",
    "what's your most unhinged 3am thought that actually made sense?",
    "what's something you lowkey gatekeep from your friends?",
    "be honest — what's your villain era backstory? 😈",
    "what's the most embarrassing thing you've typed and almost sent?",
    "who's living rent free in your head rn and why? 🏠",
    "what's a red flag you have that you're trying to normalize? 🚩",
    "what's your most chronically online moment? no cap",
    "what app do you open first when you wake up and why is it embarrassing? 📱",
    "what's the most unhinged thing you've done for attention? 💀",
    "if your search history was read out loud rn... how cooked are you? 🫢",
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
    m, answer = await asyncio.gather(
        animate_loading(update, "Consulting the magic ball"),
        ai_reply(
            f"You are a mystical Gen Z magic 8-ball. Answer this yes/no question in one creative, "
            f"witty, Gen Z style sentence (use slang like 'no cap', 'bestie', 'periodt', 'fr fr', 'slay'). "
            f"Question: {q}",
            fallback=random.choice(EIGHTBALL_ANSWERS),
        ),
    )
    await finish_anim(m,
        f"🎱 <b>Magic 8-Ball</b>\n{_D}\n\n"
        f"❓ <b>Q:</b> <i>{html.escape(q)}</i>\n\n"
        f"🎱 <b>A:</b> {html.escape(answer)}"
    )

async def roll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sides = int(context.args[0]) if context.args and context.args[0].isdigit() else 6
    if sides < 2: sides = 6
    m = await animate_loading(update, "Rolling")
    result = random.randint(1, sides)
    extra = ("🎯 <i>CRITICAL HIT!</i>" if result == sides else
             "💀 <i>CRITICAL FAIL!</i>" if result == 1 else "")
    await finish_anim(m,
                f"🎲 <b>Dice Roll</b> — d{sides}\n{_D}\n\n"
        f"▸ <b>Result: {result}!</b> {extra}"
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
                f"❓ <b>trivia time bestie no cap</b> {kmo(KAOMOJI_THINK)}\n{_D}\n\n"
        f"🧠 <b>{html.escape(q_data['q'])}</b>\n\n"
        f"<i>tap the W answer below fr fr ⬇️</i>",
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
            f"✅ <b>ATE THAT fr!!</b> {kmo(KAOMOJI_WIN)}\n{_D}\n\n"
            f"🎉 {user_link(q.from_user)} understood the assignment!\n"
            f"<b>+{reward} 🪙</b> secured no cap\n"
            f"▸ Answer: <b>{html.escape(correct)}</b> periodt",
            parse_mode="HTML")
    else:
        await q.answer(f"❌ Wrong! The answer was: {correct}", show_alert=True)
        await q.edit_message_text(
            f"❌ <b>L bestie that was wrong lmao</b> {kmo(KAOMOJI_LOSE)}\n{_D}\n\n"
                f"💀 {user_link(q.from_user)} did not eat that one ngl\n"
                f"▸ Answer was: <b>{html.escape(correct)}</b> fr fr",
            parse_mode="HTML")

async def wyr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fallback_pair = random.choice(WYR_QUESTIONS)
    m, ai_text = await asyncio.gather(
        animate_loading(update, "Generating question"),
        ai_reply(
            "Generate a unique, creative 'would you rather' question for a Telegram chat. "
            "Format your response as exactly two options separated by ' ||| ' (three pipes). "
            "Make them funny, interesting or thought-provoking. No numbering, just the two options.",
            fallback="",
        ),
    )
    if ai_text and " ||| " in ai_text:
        parts = ai_text.split(" ||| ", 1)
        opt1, opt2 = parts[0].strip(), parts[1].strip()
    else:
        opt1, opt2 = fallback_pair
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(opt1[:50], callback_data="wyr:a"),
        InlineKeyboardButton(opt2[:50], callback_data="wyr:b"),
    ]])
    await finish_anim(m,
        f"🤔 <b>would you rather bestie??</b> {kmo(KAOMOJI_THINK)}\n{_D}\n\n"
        f"<b>A:</b> {html.escape(opt1)}\n\n<i>— or like —</i>\n\n"
        f"<b>B:</b> {html.escape(opt2)}\n\n"
        f"<i>pick ur fate below fr ⬇️ periodt</i>",
        reply_markup=kb
    )

async def wyr_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    is_a   = q.data == "wyr:a"
    label  = "A" if is_a else "B"
    badge  = "🅰️" if is_a else "🅱️"
    opt_text = f"Option {label}"
    try:
        txt = q.message.text or ""
        marker = f"{label}:"
        if marker in txt:
            opt_text = txt.split(marker, 1)[1].strip().split("\n")[0].strip()
    except Exception:
        pass
    phrases = ["chose and we respect it fr 💅", "said YES to this no hesitation 👑",
               "picked and honestly based 🔥", "vibing with this choice periodt ✨",
               "went for it no cap 💀", "selected their fate fr fr 🎯"]
    await q.message.reply_text(
        f"🗳️ {user_link(q.from_user)} {badge} <b>{html.escape(opt_text)}</b>\n"
        f"<i>{random.choice(phrases)}</i>",
        parse_mode="HTML")

async def pp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context) or update.effective_user
    power  = random.randint(1, 100)
    bar    = progress_bar(power, 100, length=12)
    level  = ("💀 LEGENDARY" if power > 95 else
              "⚡ ULTRA" if power > 80 else
              "🔥 HIGH" if power > 60 else
              "✨ AVERAGE" if power > 40 else
              "😴 LOW" if power > 20 else
              "💤 ROCK BOTTOM")
    await reply(update,
                f"💪 <b>power check bestie</b> {kmo(KAOMOJI_FLEX)}\n{_D}\n\n"
        f"▸ {user_link(target)}\n"
        f"[{bar}] <b>{power}%</b> — {gz()}\n"
        f"▸ <b>Status:</b> {level}"
    )

async def slap_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context)
    if not target:
        return await reply(update, f"❓ <b>Reply to someone</b> to slap them! {kmo(KAOMOJI_BAN)}")
    u  = update.effective_user
    un = html.escape(u.first_name or "Someone")
    tn = html.escape(target.first_name or "them")
    m, action = await asyncio.gather(
        animate_loading(update, "Loading chaos"),
        ai_reply(
            f"Write one short (1 sentence), funny, dramatic anime-style slap scene "
            f"where {u.first_name or 'Someone'} slaps {target.first_name or 'them'}. "
            "No intro, include emojis, Gen Z chaos energy. Plain text only.",
            fallback=random.choice([
                f"💥 {un} slapped {tn} with a legendary trout — the fish felt it too!",
                f"⚡ {un} delivered a thunderous slap to {tn}! The whole server shook fr.",
                f"🧤 {un} put on THE glove and slapped {tn} into another dimension!",
                f"🐟 {un} yeeted a salmon at {tn}'s face. Iconic. No notes.",
            ]),
        ),
    )
    caption = (
        f"👋 <b>SLAP DELIVERED</b> {kmo(KAOMOJI_BAN)}\n{_D}\n\n"
        f"😤 {user_link(u)} ──▶ {user_link(target)}\n\n"
        f"<i>{html.escape(action)}</i>\n\n"
        f"<b>💀 they did NOT see that coming fr ngl</b>"
    )
    await send_gif_reply(update, "slap", caption)

async def hug_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context)
    if not target:
        return await reply(update, f"❓ <b>Reply to someone</b> to hug them! {kmo(KAOMOJI_WHOLESOME)}")
    u  = update.effective_user
    un = html.escape(u.first_name or "Someone")
    tn = html.escape(target.first_name or "them")
    m, action = await asyncio.gather(
        animate_loading(update, "Spreading warmth"),
        ai_reply(
            f"Write one short (1 sentence), warm, wholesome hug scene where "
            f"{u.first_name or 'Someone'} hugs {target.first_name or 'them'}. "
            "No intro, cute emojis, cozy anime vibes. Plain text only.",
            fallback=random.choice([
                f"🤗 {un} wrapped {tn} in the warmest bear hug. Friendship +100 fr!",
                f"💙 {un} hugged {tn} so tight all their worries just evaporated!",
                f"✨ {un} and {tn} share a magical hug that healed everyone nearby!",
                f"🐻 {un} went full bear mode and pulled {tn} into a massive hug!",
            ]),
        ),
    )
    caption = (
        f"🤗 <b>HUG DEPLOYED</b> {kmo(KAOMOJI_WHOLESOME)}\n{_D}\n\n"
        f"💙 {user_link(u)} ──▶ {user_link(target)}\n\n"
        f"<i>{html.escape(action)}</i>\n\n"
        f"<b>✨ wholesome arc activated periodt</b>"
    )
    await send_gif_reply(update, "hug", caption)

async def kiss_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context)
    if not target:
        return await reply(update, f"❓ <b>Reply to someone</b> to kiss them! {kmo(KAOMOJI_WHOLESOME)}")
    u  = update.effective_user
    un = html.escape(u.first_name or "Someone")
    tn = html.escape(target.first_name or "them")
    m, action = await asyncio.gather(
        animate_loading(update, "Setting the mood"),
        ai_reply(
            f"Write one short (1 sentence) sweet, romantic kiss scene where "
            f"{u.first_name or 'Someone'} kisses {target.first_name or 'them'}. "
            "No intro, heart emojis, soft anime romance energy. Plain text only.",
            fallback=random.choice([
                f"😘 {un} blew {tn} a kiss across the room — the romance arc is REAL!",
                f"💋 {un} gave {tn} a sweet kiss on the cheek. Everyone in the chat: 🥹",
                f"💑 {un} and {tn} shared a moment so romantic the chat went quiet fr.",
                f"🌸 {un} kissed {tn}'s forehead softly. Main character behavior no cap.",
            ]),
        ),
    )
    caption = (
        f"💋 <b>KISS DETECTED</b> {kmo(KAOMOJI_WHOLESOME)}\n{_D}\n\n"
        f"😘 {user_link(u)} ──▶ {user_link(target)}\n\n"
        f"<i>{html.escape(action)}</i>\n\n"
        f"<b>💕 the romance arc is REAL fr periodt</b>"
    )
    await send_gif_reply(update, "kiss", caption)

async def pat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context)
    if not target:
        return await reply(update, f"❓ <b>Reply to someone</b> to pat them! {kmo(KAOMOJI_WHOLESOME)}")
    u  = update.effective_user
    un = html.escape(u.first_name or "Someone")
    tn = html.escape(target.first_name or "them")
    m, action = await asyncio.gather(
        animate_loading(update, "Preparing headpats"),
        ai_reply(
            f"Write one short (1 sentence) gentle, wholesome head-pat scene where "
            f"{u.first_name or 'Someone'} pats {target.first_name or 'them'}. "
            "No intro, gentle emojis, soft supportive energy. Plain text only.",
            fallback=random.choice([
                f"🫶 {un} gave {tn} the gentlest head pat. You've got this bestie fr!",
                f"😊 {un} patted {tn} encouragingly — instant serotonin boost unlocked!",
                f"🌸 {un} patted {tn}'s head softly. Wholesome content only in this chat.",
                f"✨ {un} gave {tn} a warm reassuring pat. Good vibes only fr!",
            ]),
        ),
    )
    caption = (
        f"🫶 <b>HEADPAT INCOMING</b> {kmo(KAOMOJI_WHOLESOME)}\n{_D}\n\n"
        f"🌸 {user_link(u)} ──▶ {user_link(target)}\n\n"
        f"<i>{html.escape(action)}</i>\n\n"
        f"<b>✨ serotonin +100 no cap</b>"
    )
    await send_gif_reply(update, "pat", caption)

async def poke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = await get_target(update, context)
    if not target:
        return await reply(update, f"❓ <b>Reply to someone</b> to poke them! {kmo(KAOMOJI_VIBE)}")
    u  = update.effective_user
    un = html.escape(u.first_name or "Someone")
    tn = html.escape(target.first_name or "them")
    m, action = await asyncio.gather(
        animate_loading(update, "Initiating poke"),
        ai_reply(
            f"Write one short (1 sentence) playful poke scene where "
            f"{u.first_name or 'Someone'} pokes {target.first_name or 'them'}. "
            "No intro, chaotic fun energy, emojis. Plain text only.",
            fallback=random.choice([
                f"👉 {un} poked {tn}! Hey! Wake up bestie, we see you lurking!",
                f"😆 {un} keeps poking {tn}! Stop being AFK fr fr!",
                f"🫷 {un} poked {tn} in the ribs. The audacity. Iconic honestly.",
                f"💥 {un} poked {tn} so hard they almost dropped their phone!",
            ]),
        ),
    )
    caption = (
        f"👉 <b>POKE LANDED</b> {kmo(KAOMOJI_VIBE)}\n{_D}\n\n"
        f"😆 {user_link(u)} ──▶ {user_link(target)}\n\n"
        f"<i>{html.escape(action)}</i>\n\n"
        f"<b>👀 you been poked, respond accordingly fr</b>"
    )
    await send_gif_reply(update, "poke", caption)

# ─── SHIP COMMAND ─────────────────────────────────────────────────────────────
async def ship_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually ship two users: reply+target or two mentioned users."""
    u1 = update.effective_user
    target = await get_target(update, context)
    if not target or target.id == u1.id:
        # Pick a random member from the group instead
        db = get_db()
        members = db.execute(
            "SELECT user_id, first_name FROM chat_members "
            "WHERE chat_id=? AND is_bot=0 AND first_name IS NOT NULL "
            "AND user_id != ? AND last_seen >= datetime('now','-7 days') "
            "ORDER BY RANDOM() LIMIT 1",
            (update.effective_chat.id, u1.id)
        ).fetchall()
        db.close()
        if not members:
            return await reply(update,
                f"😭 <b>Not enough active members to ship!</b>\n"
                f"<i>Reply to someone with /ship or wait for more activity fr</i>"
            )
        row = members[0]
        u2 = type("FakeUser", (), {
            "id": row["user_id"],
            "first_name": row["first_name"],
            "username": None, "last_name": None, "is_bot": False
        })()
    else:
        u2 = target

    compat   = random.randint(45, 100)
    filled   = compat // 10
    hearts   = "❤️" * filled + "🖤" * (10 - filled)
    emoji    = random.choice(_SHIP_EMOJIS)
    fallback = random.choice(_SHIP_VERDICTS)
    m = await animate_loading(update, "Calculating compatibility")
    verdict = await ai_reply(
        f"Write one funny dramatic Gen Z ship verdict for {u1.first_name or 'User1'} "
        f"and {u2.first_name or 'User2'} who scored {compat}% compatibility. "
        "1 sentence, emojis, no intro. Plain text only.",
        fallback=fallback,
    )
    link1 = user_link(u1)
    link2 = user_link(u2)
    await finish_anim(m,
        f"{emoji} <b>SHIP ALERT</b> {kmo(KAOMOJI_WHOLESOME)}\n{_D}\n\n"
        f"💘 {link1} <b>×</b> {link2}\n\n"
        f"<code>{hearts}</code>\n"
        f"▸ <b>{compat}% compatible</b>\n\n"
        f"<i>{html.escape(verdict)}</i>\n\n"
        f"<b>{emoji} shipped. no debate. periodt.</b>"
    )

# ─── AUTO SHIP (hourly) ────────────────────────────────────────────────────────
_SHIP_EMOJIS   = ["💞","💕","❤️","💗","💘","💓","💝","🌹","🔥","✨"]
_SHIP_VERDICTS = [
    "the romance arc is REAL fr periodt 💅",
    "enemies to lovers but make it chaotic 🔥",
    "main character energy x2 no cap 👑",
    "the universe said YES and we agree 🌌",
    "certified power couple behavior fr 💪",
    "matching energy detected. we ship it. 🚢",
    "astrology said compatible. we agree periodt ♾️",
    "red string of fate is ACTIVATED no cap 🧵",
]

async def auto_ship_job(context: ContextTypes.DEFAULT_TYPE):
    """Runs every hour — picks 2 random active members from each group and ships them."""
    db = get_db()
    try:
        # Get all active groups with at least 2 human members seen in last 7 days
        groups = db.execute(
            "SELECT DISTINCT chat_id FROM chat_members "
            "WHERE is_bot=0 AND last_seen >= datetime('now','-7 days') "
            "GROUP BY chat_id HAVING COUNT(*) >= 2"
        ).fetchall()

        for group in groups:
            cid = group["chat_id"]
            members = db.execute(
                "SELECT user_id, first_name, username FROM chat_members "
                "WHERE chat_id=? AND is_bot=0 AND first_name IS NOT NULL "
                "AND last_seen >= datetime('now','-7 days') ORDER BY RANDOM() LIMIT 2",
                (cid,)
            ).fetchall()
            if len(members) < 2:
                continue

            u1, u2 = members[0], members[1]
            n1 = html.escape(u1["first_name"] or "Someone")
            n2 = html.escape(u2["first_name"] or "Someone")
            link1 = f'<a href="tg://user?id={u1["user_id"]}">{n1}</a>'
            link2 = f'<a href="tg://user?id={u2["user_id"]}">{n2}</a>'

            compat  = random.randint(55, 100)
            hearts  = "❤️" * (compat // 10) + "🖤" * (10 - compat // 10)
            emoji   = random.choice(_SHIP_EMOJIS)
            verdict = random.choice(_SHIP_VERDICTS)

            ai_verdict = await ai_reply(
                f"Write one funny, dramatic, Gen Z ship verdict for {u1['first_name'] or 'User1'} "
                f"and {u2['first_name'] or 'User2'} who scored {compat}% compatibility. "
                "1 sentence, emojis, no intro. Plain text only.",
                fallback=verdict,
            )

            text = (
                f"{emoji} <b>HOURLY SHIP ALERT</b> {kmo(KAOMOJI_WHOLESOME)}\n{_D}\n\n"
                f"💘 {link1} <b>×</b> {link2}\n\n"
                f"<code>{hearts}</code>\n"
                f"▸ <b>{compat}% compatible</b>\n\n"
                f"<i>{html.escape(ai_verdict)}</i>\n\n"
                f"<b>{emoji} shipped. no debate. periodt.</b>"
            )
            try:
                await context.bot.send_message(cid, text, parse_mode="HTML")
            except Exception as e:
                logger.debug(f"auto_ship_job: failed to send to {cid}: {e}")
    except Exception as e:
        logger.error(f"auto_ship_job error: {e}")
    finally:
        db.close()

async def roast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target      = await get_target(update, context)
    name        = user_link(target) if target else user_link(update.effective_user)
    target_name = (target or update.effective_user).first_name or "this person"
    m, roast    = await asyncio.gather(
        animate_loading(update, "Firing up the roaster"),
        ai_reply(
            f"Write one savage, witty roast for someone named {html.escape(target_name)}. "
            "Funny but not cruel. No intro. Max 2 sentences. Plain text only.",
            fallback=random.choice(ROASTS),
        ),
    )
    closers = ["L + ratio + touch grass 💀", "no cap this is facts 🔥",
               "somebody had to say it fr 😭", "the roast is REAL periodt 🫡"]
    await finish_anim(m,
        f"🔥 <b>COOKED. NO CRUMBS.</b> {kmo(KAOMOJI_FIRE)}\n{_D}\n\n"
        f"🎯 {name}\n\n"
        f"<i>{html.escape(roast)}</i>\n\n"
        f"<b>{random.choice(closers)}</b>"
    )

async def compliment_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target      = await get_target(update, context)
    name        = user_link(target) if target else user_link(update.effective_user)
    target_name = (target or update.effective_user).first_name or "this person"
    m, comp     = await asyncio.gather(
        animate_loading(update, "Writing something beautiful"),
        ai_reply(
            f"Write one genuine, warm, uplifting compliment for someone named {html.escape(target_name)}. "
            "Creative and specific. No intro. Max 2 sentences. Plain text only.",
            fallback=random.choice(COMPLIMENTS),
        ),
    )
    openers = ["slay check ✅", "understood the assignment 👑", "ate. no crumbs. periodt ✨",
               "this is facts no debate 💐"]
    await finish_anim(m,
        f"💐 <b>COMPLIMENT DROPPED</b> {kmo(KAOMOJI_WHOLESOME)}\n{_D}\n\n"
        f"🌟 {name}\n\n"
        f"<i>{html.escape(comp)}</i>\n\n"
        f"<b>{random.choice(openers)}</b>"
    )

async def joke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m, joke = await asyncio.gather(
        animate_loading(update, "Summoning a banger"),
        ai_reply(
            "Tell one original, funny joke — pun, one-liner, or short setup/punchline. "
            "No intro like 'Here is a joke'. Just the joke. Plain text only.",
            fallback=random.choice(JOKES),
        ),
    )
    closers = ["ok that was lowkey bussin 💀", "ngl I'm crying 😭", "LMAOOO periodt 🤣",
               "the comedy is REAL fr", "you're welcome bestie 😎"]
    await finish_anim(m,
        f"😂 <b>JOKE INCOMING</b> {kmo(KAOMOJI_VIBE)}\n{_D}\n\n"
        f"<i>{html.escape(joke)}</i>\n\n"
        f"<b>{random.choice(closers)}</b>"
    )

async def fact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m, fact = await asyncio.gather(
        animate_loading(update, "Loading brain fuel"),
        ai_reply(
            "Give one surprising, verified fact about nature, science, history, space, or animals. "
            "Start directly with the fact, no 'Did you know' intro. 1-2 sentences. Plain text only.",
            fallback=random.choice(FACTS),
        ),
    )
    closers = ["ngl that broke my brain fr 🤯", "the more you know bestie 🧠",
               "kinda bussin knowledge no cap ✨", "dropped. absorbed. periodt 📚"]
    await finish_anim(m,
        f"🧠 <b>FACT UNLOCKED</b> {kmo(KAOMOJI_THINK)}\n{_D}\n\n"
        f"<i>{html.escape(fact)}</i>\n\n"
        f"<b>{random.choice(closers)}</b>"
    )

async def quote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m, quote = await asyncio.gather(
        animate_loading(update, "Finding wisdom"),
        ai_reply(
            "Give one unique, inspiring or thought-provoking quote. Real or fictional person, "
            "or 'Unknown'. Format: quote text — Author. No extra text. Plain text only.",
            fallback=random.choice(QUOTES),
        ),
    )
    closers = ["understood the assignment ✨", "real ones felt that fr 👑",
               "marinating in this quote rn 💭", "dropped. we're changed. periodt 🌌"]
    await finish_anim(m,
        f"💬 <b>WISDOM DROPPED</b> {kmo(KAOMOJI_VIBE)}\n{_D}\n\n"
        f"<i>❝ {html.escape(quote)} ❞</i>\n\n"
        f"<b>{random.choice(closers)}</b>"
    )

async def truth_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m, truth = await asyncio.gather(
        animate_loading(update, "Digging up some tea"),
        ai_reply(
            "Write one juicy truth question for a Telegram group truth-or-dare game. "
            "Fun, a bit personal but appropriate. Gen Z casual language. No intro. Plain text only.",
            fallback=random.choice(TRUTHS),
        ),
    )
    await finish_anim(m,
        f"💭 <b>TRUTH UNLOCKED</b> {kmo(KAOMOJI_THINK)}\n{_D}\n\n"
        f"🤔 <i>{html.escape(truth)}</i>\n\n"
        f"<b>no lying allowed. we see you. answer fr 👀</b>"
    )

async def dare_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m, dare = await asyncio.gather(
        animate_loading(update, "Planning your fate"),
        ai_reply(
            "Write one fun dare for a Telegram group truth-or-dare game. "
            "Something doable in chat (send a message, post something, etc). "
            "No intro. Funny and light. Plain text only.",
            fallback=random.choice(DARES),
        ),
    )
    closers = ["no backing out. we're watching 😈", "you HAVE to do it. those are the rules fr 📜",
               "failure is not an option bestie 💀", "the chat has spoken. comply. periodt 👑"]
    await finish_anim(m,
        f"😈 <b>DARE ASSIGNED</b> {kmo(KAOMOJI_FIRE)}\n{_D}\n\n"
        f"⚡ <i>{html.escape(dare)}</i>\n\n"
        f"<b>{random.choice(closers)}</b>"
    )

async def meme_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m, meme = await asyncio.gather(
        animate_loading(update, "Generating a banger"),
        ai_reply(
            "Write one funny, relatable Gen Z meme for a Telegram group. "
            "Use formats like 'Me: ... Also me: ...' or 'POV: ...' or 'That one [person] who...'. "
            "Short, modern, no intro. Plain text only.",
            fallback=random.choice([
                "Me: I should sleep\nAlso me at 3am: Let me research Byzantine economic history 🤓",
                "POV: you said 'just 5 more minutes' 4 hours ago 💀",
                "Me: I'm fine\nAlso me internally: (╥_╥) whole essay",
                "My 8am alarm: *vibrates gently*\nMy 8:07am alarm: WAKE UP SOLDIER 💥",
                "The way I said 'on my way' while still in bed... criminal behavior fr 📱",
            ]),
        ),
    )
    await finish_anim(m,
        f"😎 <b>MEME DELIVERED</b> {kmo(KAOMOJI_VIBE)}\n{_D}\n\n"
        f"<i>{html.escape(meme)}</i>\n\n"
        f"<b>if this ain't you then you're lying no cap 💀</b>"
    )

# ═══════════════════════════════════════════════════════════════════════════════
#                     🤖 AI COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════
async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct AI question — multi-API powered."""
    question = " ".join(context.args) if context.args else ""
    if not question and update.message.reply_to_message:
        question = update.message.reply_to_message.text or ""
    if not question:
        return await reply(update,
            f"🤖 <b>Ask the AI anything!</b>\n{_D}\n\n"
            f"<b>Usage:</b> <code>/ask your question here</code>\n"
            f"<i>Powered by multi-API AI — Pollinations, GPT-4, Gemini</i>"
        )
    m = await animate_loading(update, "Thinking")
    answer = await ai_ask(question)
    await finish_anim(m,
        f"🤖 <b>AI ANSWER</b>\n{_D}\n\n"
        f"❓ <b>Q:</b> <i>{html.escape(question[:200])}</i>\n\n"
        f"💡 <b>A:</b> {html.escape(answer)}\n\n"
        f"<i>Powered by Nexus AI Engine v10 ⚡</i>"
    )

async def aiinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current AI engine status."""
    global _ai_api_index
    api_names = ["🌸 Pollinations AI", "⚡ Custom GPT-4", "💎 Google Gemini"]
    current = api_names[_ai_api_index % len(api_names)]
    gemini_status = "✅ Configured" if GEMINI_API_KEY else "❌ No key set"
    await reply(update,
        f"🤖 <b>Nexus AI Engine v10</b>\n{_D}\n\n"
        f"▸ <b>Current API:</b> {current}\n"
        f"▸ <b>APIs in rotation:</b>\n"
        f"  1. 🌸 <b>Pollinations AI</b> — Free, no key\n"
        f"  2. ⚡ <b>Custom GPT-4</b> — Free endpoint\n"
        f"  3. 💎 <b>Gemini 1.5 Flash</b> — {gemini_status}\n"
        f"{_D}\n"
        f"<i>Auto-rotates for 100% uptime. Never stops.</i>"
    )

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
            f"🧮 <b>Calculator</b>\n{_D}\n\n"
            f"▸ <code>{html.escape(expr)}</code>\n"
            f"▸ <b>= {result}</b>"
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
                    f"🌐 <b>Translation</b>\n{_D}\n\n"
                    f"▸ <b>Original:</b>\n<i>{html.escape(text[:200])}</i>\n\n"
                    f"▸ <b>→ {lang.upper()}:</b>\n{html.escape(translated)}"
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
        f"🔐 <b>Hashes</b>\n{_D}\n\n"
        f"▸ <b>MD5:</b>\n<code>{md5}</code>\n\n"
        f"▸ <b>SHA1:</b>\n<code>{sha1}</code>\n\n"
        f"▸ <b>SHA256:</b>\n<code>{sha256}</code>"
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
        await reply(update,
            f"🔢 <b>Base64</b>\n{_D}\n\n"
            f"▸ {label}:\n<code>{html.escape(result)}</code>"
        )
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
                    f"{icon} <b>Weather — {html.escape(area)}</b>\n{_D}\n\n"
                    f"▸ <b>Temp:</b> {cur['temp_C']}°C / {cur['temp_F']}°F\n"
                    f"▸ <b>Feels like:</b> {cur['FeelsLikeC']}°C\n"
                    f"▸ <b>Condition:</b> {html.escape(desc)}\n"
                    f"{_D}\n"
                    f"▸ <b>Humidity:</b> {cur['humidity']}%\n"
                    f"▸ <b>Wind:</b> {cur['windspeedKmph']} km/h\n"
                    f"▸ <b>Visibility:</b> {cur['visibility']} km"
                )
    except Exception as e:
        await finish_anim(m, f"❌ <b>Weather lookup failed:</b> {html.escape(str(e))}")

async def time_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tz_name = " ".join(context.args) if context.args else "UTC"
    try:
        tz = pytz.timezone(tz_name)
        now = datetime.datetime.now(tz)
        await reply(update,
            f"🕐 <b>Time</b>\n{_D}\n\n"
            f"▸ <b>Timezone:</b> {tz_name}\n"
            f"▸ <b>Time:</b> {now.strftime('%H:%M:%S')}\n"
            f"▸ <b>Date:</b> {now.strftime('%Y-%m-%d')}"
        )
    except Exception as e:
        await reply(update, f"❌ <b>Invalid timezone:</b> {html.escape(str(e))}")

async def reverse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        if update.message.reply_to_message and update.message.reply_to_message.text:
            text = update.message.reply_to_message.text
        else:
            return await reply(update, "❓ <b>Usage:</b> <code>/reverse text</code>")
    else:
        text = " ".join(context.args)
    await reply(update, f"🔄 <b>Reversed:</b>\n<code>{html.escape(text[::-1])}</code>")

async def ascii_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: return await reply(update, "❓ <b>Usage:</b> <code>/ascii text</code>")
    text = " ".join(context.args)[:20]
    codes = " ".join(str(ord(c)) for c in text)
    await reply(update, f"💻 <b>ASCII Codes</b>\n{_D}\n\n▸ <code>{html.escape(text)}</code>\n▸ <code>{codes}</code>")

# ─── OWNER COMMANDS ───────────────────────────────────────────────────────────
@owner_only
async def chatlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await animate_loading(update, "Fetching chat list")
    db = get_db()
    rows = db.execute("SELECT chat_id, title, chat_type FROM chats ORDER BY title LIMIT 50").fetchall()
    db.close()
    lines = [f"💬 <b>Chat List ({len(rows)})</b>\n{_D}\n"]
    icons = {"group":"👥","supergroup":"💬","channel":"📣","private":"👤"}
    for r in rows:
        icon = icons.get(r["chat_type"], "💬")
        lines.append(f"{icon} {html.escape(r['title'] or 'Unknown')} — <code>{r['chat_id']}</code>")
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
        "version": VERSION,
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
                                                f"▸ {len(notes)} notes · {len(filters)} filters · {len(bl)} blacklist words",
                                        parse_mode="HTML")

# ─── SCHEDULE ─────────────────────────────────────────────────────────────────
@admin_only
@groups_only
async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        return await reply(update, "❓ <b>Usage:</b> <code>/schedule 1h Your message here</code>")
    time_str = context.args[0]
    message  = " ".join(context.args[1:])
    duration = parse_duration(time_str)
    if not duration: return await reply(update, "❌ <b>Invalid duration.</b> Use: 1m, 1h, 1d")
    next_run = datetime.datetime.now(pytz.utc) + duration
    db = get_db()
    db.execute("INSERT INTO schedules (chat_id, message, next_run, created_by) VALUES (?,?,?,?)",
               (update.effective_chat.id, message, next_run.isoformat(), update.effective_user.id))
    db.commit(); db.close()
    await reply(update,
        f"📅 <b>Scheduled!</b>\n{_D}\n\n"
        f"▸ <b>In:</b> {html.escape(fmt_duration(duration))}\n"
        f"▸ <b>At:</b> {next_run.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"▸ <b>Message:</b> {html.escape(message[:80])}"
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
                f"🌍 <b>Globally banned user removed!</b>\n▸ {html.escape(reason)}",
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
        BotCommand("roast",          "🔥 Roast user"),
        BotCommand("compliment",     "💐 Compliment"),
        BotCommand("joke",           "😂 Random joke"),
        BotCommand("fact",           "🧠 Random fact"),
        BotCommand("quote",          "💬 Quote"),
        BotCommand("truth",          "💭 Truth question"),
        BotCommand("dare",           "😈 Dare"),
        BotCommand("meme",           "😎 Meme text"),
        BotCommand("ask",            "🤖 Ask AI anything"),
        BotCommand("aiinfo",         "⚡ AI engine status"),
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

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    import traceback as _tb
    err = context.error
    err_type = type(err).__name__
    err_msg  = str(err)

    tb_str = "".join(_tb.format_exception(type(err), err, err.__traceback__))
    logger.error(f"[NEXUS ERROR] {err_type}: {err_msg}\n{tb_str}")

    _ignored = (
        "Message is not modified",
        "Query is too old",
        "MESSAGE_NOT_MODIFIED",
        "QUERY_ID_INVALID",
        "Flood control exceeded",
        "Bad Request: can't parse",
        "Not enough rights",
        "Bad Request: have no rights",
        "Forbidden: bot was blocked",
        "Forbidden: bot was kicked",
        "Forbidden: bot can't",
        "Message to delete not found",
        "Message to edit not found",
        "Chat not found",
        "The group has been migrated",
        "Timed out",
        "NetworkError",
        "httpx",
    )
    for ignore in _ignored:
        if ignore.lower() in err_msg.lower():
            return

    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"⚠️ <b>Something went sideways...</b>\n"
                f"<i>The error has been logged and will be fixed. Try again!</i>",
                parse_mode="HTML"
            )
        except Exception:
            pass

def main():
    if not BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set! Please set the environment variable.")
        sys.exit(1)

    init_db()
    logger.info(f"🚀 Starting Nexus Bot {VERSION}")

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
    app.add_handler(CallbackQueryHandler(unban_callback,       pattern=r"^unban:"))
    app.add_handler(CallbackQueryHandler(unmute_callback,      pattern=r"^unmute:"))
    app.add_handler(CallbackQueryHandler(warn_action_callback, pattern=r"^(unwarn|resetwarn):"))

    # ── Locks ─────────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("lock",           lock_cmd))
    app.add_handler(CommandHandler("unlock",         unlock_cmd))
    app.add_handler(CommandHandler("locks",          locks_cmd))
    app.add_handler(CallbackQueryHandler(lock_toggle_callback, pattern=r"^lock_tog:"))

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
    app.add_handler(CommandHandler("cleanservice",   cleanservice_cmd))
    app.add_handler(CommandHandler("delcommands",    delcommands_cmd))
    app.add_handler(CallbackQueryHandler(protect_toggle_callback, pattern=r"^protect_toggle:"))

    async def open_protect_panel_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
        q = update.callback_query
        if not await is_admin(context, q.message.chat_id, q.from_user.id):
            return await q.answer("🚫 Admins only!", show_alert=True)
        await q.answer()
        await protect_cmd(update, context)

    app.add_handler(CallbackQueryHandler(open_protect_panel_cb, pattern=r"^open_protect_panel$"))

    # ── Welcome / Rules ───────────────────────────────────────────────────────
    app.add_handler(CommandHandler("setwelcome",     setwelcome_cmd))
    app.add_handler(CommandHandler("setgoodbye",     setgoodbye_cmd))
    app.add_handler(CommandHandler("welcome",        welcome_toggle_cmd))
    app.add_handler(CommandHandler("goodbye",        goodbye_toggle_cmd))
    app.add_handler(CommandHandler("captcha",        captcha_cmd))
    app.add_handler(CommandHandler("welcdel",        welcdel_cmd))
    app.add_handler(CommandHandler("setrules",       setrules_cmd))
    app.add_handler(CommandHandler("rules",          rules_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, goodbye_handler))
    app.add_handler(CallbackQueryHandler(captcha_callback, pattern=r"^captcha:"))
    app.add_handler(CallbackQueryHandler(rules_callback,   pattern=r"^rules_accept$"))

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
    app.add_handler(CommandHandler("delfed",         delfed_cmd))
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

    # ── Global Ban / Sudo ─────────────────────────────────────────────────────
    app.add_handler(CommandHandler("gban",           gban_cmd))
    app.add_handler(CommandHandler("ungban",         ungban_cmd))
    app.add_handler(CommandHandler("sudo",           sudo_cmd))
    app.add_handler(CommandHandler("unsudo",         unsudo_cmd))

    # ── Broadcast ─────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("broadcast",      broadcast_cmd))
    app.add_handler(CommandHandler("broadcastall",   broadcastall_cmd))

    # ── Stats / Info ──────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("botstats",       botstats_cmd))
    app.add_handler(CommandHandler("id",             id_cmd))
    app.add_handler(CommandHandler("info",           info_cmd))
    app.add_handler(CommandHandler("chatinfo",       chatinfo_cmd))
    app.add_handler(CommandHandler("ping",           ping_cmd))
    app.add_handler(CommandHandler("uptime",         uptime_cmd))

    # ── Settings ──────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("settings",       settings_cmd))

    # ── Owner ─────────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("chatlist",       chatlist_cmd))
    app.add_handler(CommandHandler("leave",          leave_cmd))
    app.add_handler(CommandHandler("backup",         backup_cmd))

    # ── Leaderboard / Ranks ───────────────────────────────────────────────────
    app.add_handler(CommandHandler("leaderboard",    leaderboard_cmd))
    app.add_handler(CommandHandler("rank",           rank_cmd))
    app.add_handler(CommandHandler("top",            top_cmd))
    app.add_handler(CommandHandler("level",          level_cmd))
    app.add_handler(CommandHandler("rep",            rep_cmd))
    app.add_handler(CommandHandler("reprank",        reprank_cmd))
    app.add_handler(CallbackQueryHandler(leaderboard_callback, pattern=r"^lb:"))

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

    # ── Games & Fun ───────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("ship",           ship_cmd))
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

    # ── AI Commands ───────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("ask",            ask_cmd))
    app.add_handler(CommandHandler("aiinfo",         aiinfo_cmd))

    # ── Utilities ─────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("calc",           calc_cmd))
    app.add_handler(CommandHandler("qr",             qr_cmd))
    app.add_handler(CommandHandler("tr",             translate_cmd))
    app.add_handler(CommandHandler("hash",           hash_cmd))
    app.add_handler(CommandHandler("b64",            b64_cmd))
    app.add_handler(CommandHandler("weather",        weather_cmd))
    app.add_handler(CommandHandler("time",           time_cmd))
    app.add_handler(CommandHandler("reverse",        reverse_cmd))
    app.add_handler(CommandHandler("ascii",          ascii_cmd))
    app.add_handler(CommandHandler("schedule",       schedule_cmd))

    # ── Message / Member handlers ─────────────────────────────────────────────
    app.add_handler(ChatMemberHandler(chat_member_handler, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VIDEO | filters.AUDIO |
        filters.Document.ALL | filters.VOICE | filters.Sticker.ALL |
        filters.ANIMATION | filters.FORWARDED | filters.POLL |
        filters.GAME | filters.VIDEO_NOTE,
        main_message_handler
    ))

    # ── Scheduler jobs ────────────────────────────────────────────────────────
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(run_scheduler,   interval=60,   first=10)
        job_queue.run_repeating(auto_ship_job,   interval=3600, first=120)

    # ── Global Error Handler ──────────────────────────────────────────────────
    app.add_error_handler(global_error_handler)

    logger.info("✅ All handlers registered. Starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
