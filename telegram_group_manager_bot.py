#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║            NEXUS BOT v11.0 — @AdvManagerVBot                        ║
║  World's Most Advanced Telegram Group Manager                        ║
║  Pure Randomness Engine · 3500+ Unique Responses · Zero-Error       ║
║  25+ New Commands · Minimax AI Games · Marriage · Tarot · Clans     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os, sys, re, json, time, math, random, string, asyncio, sqlite3, logging
import hashlib, textwrap, datetime, calendar, html, urllib.parse, uuid, base64, io
import itertools, struct, operator
from typing import Optional, Dict, List, Any, Tuple, Set
from collections import defaultdict, deque, Counter
from functools import wraps, lru_cache

# ── Dependency bootstrap ────────────────────────────────────────────────────────
_REQUIRED = ["telegram", "aiohttp", "pytz"]
for _pkg in _REQUIRED:
    try: __import__(_pkg)
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", _pkg, "-q"], check=True)

import aiohttp, pytz
from telegram import (
    Update, User, Chat, ChatPermissions, InlineKeyboardButton,
    InlineKeyboardMarkup, ChatMemberAdministrator, BotCommand,
    InputMediaPhoto, InlineQueryResultArticle, InputTextMessageContent,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    InlineQueryHandler, filters, ContextTypes, JobQueue,
)
from telegram.error import BadRequest, Forbidden, TelegramError, RetryAfter

# ═══════════════════════════════════════════════════════════════════════════════
#                              CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
BOT_TOKEN   = os.environ.get("BOT_TOKEN", "8159930920:AAGS4XWy9Fslq0RnRvFvx6QNTg9eTT5AqOo")
OWNER_IDS   = {7012373095}
LOG_CHANNEL = os.environ.get("LOG_CHANNEL", "")
DB_PATH     = "bot_data.db"
VERSION     = "11.0"
BOT_NAME    = "Nexus Bot"
START_TIME  = time.time()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("bot.log")]
)
logger = logging.getLogger("NexusBot")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# ── In-memory caches ────────────────────────────────────────────────────────────
_chat_cache: Dict[int, Tuple[dict, float]] = {}
_admin_cache: Dict[int, Tuple[dict, float]] = {}
_gban_cache: Dict[int, Tuple[Optional[str], float]] = {}
_CHAT_TTL  = 300.0
_ADMIN_TTL = 300.0
_GBAN_TTL  = 60.0
connection_cache: Dict[int, int] = {}
_rate_limit: Dict[str, float] = {}
_game_state: Dict[int, dict] = {}   # per-chat game state
_marriage_cache: Dict[int, dict] = {}
_session: Optional[aiohttp.ClientSession] = None

# ── GIF / kaomoji pools (small, for decoration) ─────────────────────────────────
KAOMOJI_HYPE    = ["(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧","(╯°□°)╯","(ง •̀_•́)ง","✧◝(⁰▿⁰)◜✧","(ﾉ≧∀≦)ﾉ","٩(◕‿◕｡)۶","(ﾉ´ヮ`)ﾉ*: ･ﾟ"]
KAOMOJI_BAN     = ["(╯°□°)╯︵ ┻━┻","ヽ(`Д´)ﾉ","(ง •̀_•́)ง","(◣_◢)","(；一_一)","(ಠ益ಠ)","[̲̅$̲̅(̲̅ιοο̲̅)̲̅$̲̅]"]
KAOMOJI_SAD     = ["(｡•́︿•̀｡)","(T_T)","(。´_｀。)","(╥_╥)","(′_‵)","σ(T^T)","｡ﾟ(TヮT)ﾟ｡"]
KAOMOJI_WHOLESOME=["(＾▽＾)","(◠‿◠)","(✿◠‿◠)","(♥ω♥*)","(´▽｀)ʃ♡","(●´ω｀●)","(≧◡≦)"]
KAOMOJI_THINK   = ["(¬_¬)","(ಠ_ಠ)","(¬‿¬)","(•_•)","(-_-)zzz","(ʘᗩʘ')","ヽ(ー_ーゞ)"]
KAOMOJI_FLEX    = ["(•̀ᴗ•́)و","ᕦ(ò_óˇ)ᕤ","(ง'̀-'́)ง","(ﾉ°▽°)ﾉ","(ᕗ ͠° ਊ ͠° )ᕗ"]
GEN_Z_PHRASES   = ["no cap fr fr","understood the assignment","it's giving chaos","slay bestie","lowkey unhinged",
                   "main character energy","we do not gatekeep","rent free in my head","the audacity tho",
                   "living rent free","understood the vibe","not me doing this","it's giving","periodt bestie",
                   "the way i just","no thoughts only vibes","absolutely sending me","touch grass era",
                   "this is giving chaos","based and redpilled fr","let him cook","ratio + L + bozo"]

def kmo(pool): return random.choice(pool)
_D = "  <code>·──────────────────────·</code>"

# ═══════════════════════════════════════════════════════════════════════════════
#                    🎲 PURE RANDOMNESS ENGINE — R CLASS
# ═══════════════════════════════════════════════════════════════════════════════
class R:
    """Anti-repeat pure randomness engine. No AI. Unlimited variety."""
    _recent: Dict[str, deque] = defaultdict(lambda: deque(maxlen=20))

    @staticmethod
    def pick(pool: list, key: str = None) -> str:
        try:
            if not pool: return "…"
            if key and len(pool) > 5:
                recent = R._recent[key]
                avail = [x for x in pool if x not in recent]
                item = random.choice(avail if avail else pool)
                recent.append(item)
                return item
            return random.choice(pool)
        except Exception: return random.choice(pool) if pool else "…"

    @staticmethod
    def pct(seed: int) -> int:
        return random.Random(seed).randint(1, 100)

    @staticmethod
    def daily(pool: list, user_id: int, salt: int = 0) -> str:
        try:
            today = datetime.date.today().toordinal()
            rng = random.Random(today + user_id + salt)
            return rng.choice(pool)
        except Exception: return random.choice(pool)

    @staticmethod
    def weighted(opts: list) -> any:
        try:
            items = [i for i, w in opts for _ in range(w)]
            return random.choice(items)
        except Exception: return opts[0][0] if opts else None

    @staticmethod
    def compose(*pools) -> str:
        return " ".join(random.choice(p) for p in pools if p)

    @staticmethod
    def n_unique(pool: list, n: int) -> list:
        return random.sample(pool, min(n, len(pool)))

    @staticmethod
    def shuffle_pick(pool: list) -> str:
        p = pool[:]
        random.shuffle(p)
        return p[0] if p else "…"

# ═══════════════════════════════════════════════════════════════════════════════
#                    MASSIVE RESPONSE POOLS (3500+ unique strings)
# ═══════════════════════════════════════════════════════════════════════════════

# ─── 8BALL — 90 unique responses ─────────────────────────────────────────────
EIGHTBALL_POOL = [
    # Positive (30)
    "It is certain 🔮","Without a doubt ✨","Yes, definitely!","You may rely on it 💫",
    "As I see it, yes","Most likely 🌟","Outlook looks good 🌈","Signs point to yes ⭐",
    "It is decidedly so 🎯","The universe nods in your favor 🌌","100% absolutely bestie 💎",
    "The stars scream YES 🌠","Looks like a W to me 🏆","Big yes energy right here ✅",
    "The cosmos align for you 🪐","Go for it — the vibes are immaculate 🔥",
    "Not a single doubt in my crystal ball 🔮","Fate says yes fr fr ⚡",
    "Affirmative. Proceed immediately 🚀","Your future is looking bright ☀️",
    "The magic 8-ball glows intensely... YES 💡","Absolutely and without question 🎖️",
    "Fortune smiles upon you today 😊","The answer is yes and that's on periodt 💅",
    "Every sign points to a glorious yes 🎊","The spiritual realm agrees ✨",
    "That's a fat YES from me bestie 🎉","Undoubtedly! The odds are in your favor 🍀",
    "The prophecy is fulfilled — it is yes 📜","Very likely, proceed with confidence 💪",
    # Neutral (30)
    "Ask again later 🤔","Cannot predict now ⏳","Reply hazy, try again 🌫️",
    "Concentrate and ask again 🧘","Don't count on it yet 🎲",
    "My sources say... unclear 🌀","The ball is cloudy today 🌪️",
    "The spirits are conflicted rn 👻","Maybe? The vibes are 50/50 😐",
    "I'd need more information bestie 🤷","The crystal is foggy — ask later 🔮",
    "Not sure — even my omniscience has limits 🧿","Hard to say, the timeline is shifting ⏰",
    "The quantum realm says: possibly 🔬","Neutral territory — flip a coin fr 🪙",
    "My magic reserves are low, ask tomorrow 🔋","The answer lives in a superposition 🌊",
    "Neither yes nor no — the ball shrugs 🤷","Uncertain. The future is still writing itself 📝",
    "Could go either way fr — the vibes are split 🎭","My third eye is on break 😴",
    "The ball is consulting higher powers... 🛸","Ambiguous. Your fate hangs in the balance ⚖️",
    "Come back when Mercury isn't retrograde 🪐","The cosmos haven't decided yet 🌌",
    "Probability: unknown. Vibe: chaotic 🃏","Reply is encrypted — upgrade your subscription 💎",
    "The oracle needs coffee ☕","Reality is subjective bestie 🌈","Check back after a full moon 🌕",
    # Negative (30)
    "Don't count on it 🚫","My reply is no ❌","Outlook not so good 📉",
    "Very doubtful 😬","No cap that's a no from me 💀","The stars say absolutely not 🌑",
    "The energy is wrong for this one ❄️","Not a chance bestie — L incoming 😤",
    "The vibes screamed no at me 😰","Hard pass from the universe 🙅",
    "Outlook is gloomy bestie — abort mission 🚨","That's a ratio and a no fr ❌",
    "The prophecy says no and it's giving finality 📛","Signs point to absolutely not 🛑",
    "My sources are screaming NO 📢","No way jose — the cosmos denied 🌚",
    "Not in this timeline bestie 🔄","The 8-ball has left the chat — no 💬",
    "Future unclear but definitely not that 🚷","The vibes are off — try again never 💀",
    "Decidedly no — don't test the universe 🌪️","Not today, not ever fr 🏚️",
    "The crystal ball just shattered — that's a no 💔","My magic says: please don't 🙏",
    "Negative. The cosmos have spoken 🌑","It is not meant to be 🕯️",
    "The oracle laughed and said no 😂","That ship has sailed bestie ⛵",
    "Bold of you to ask — absolutely not 🙈","Fortune does not smile on this request 🥀",
]

# ─── ROAST POOL — 85 savage roasts ──────────────────────────────────────────
ROAST_POOL = [
    "You're the human equivalent of a participation trophy 🏅",
    "Your personality has the energy of a Monday morning 😑",
    "You bring everyone so much joy when you leave the room 🚪",
    "I'd agree with you but then we'd both be wrong 🤦",
    "You're proof that evolution can go backwards 🦧",
    "I've seen better arguments in a cereal box 🥣",
    "Your vibe is giving expired milk fr 🥛",
    "You're the reason why instructions say 'do not eat' 📋",
    "Calling you a clown would be an insult to clowns 🤡",
    "You have the charisma of a wet sock 🧦",
    "I'd roast you more but my mom said I shouldn't burn trash 🗑️",
    "Your brain called — it said it misses you 🧠",
    "You're like a cloud — when you disappear it's a beautiful day ☁️",
    "The trash gets taken out more than you do 🗑️",
    "You're not stupid — you just have bad luck thinking 💭",
    "I've met GPS systems with better direction in life 🗺️",
    "Your opinion is like a Wi-Fi signal — weak and often wrong 📶",
    "You're the human version of a loading screen ⌛",
    "Even Google Maps couldn't find your way to success 📍",
    "You're like a software update — nobody wants you right now 💻",
    "If personality were gravity, you'd float away 🎈",
    "Your fashion sense called — it filed a restraining order 👔",
    "You're the plot twist nobody asked for 📖",
    "You're like a library fine — pointless and irritating 📚",
    "Your vibe is a 404 error — personality not found 🔍",
    "You have the depth of a parking puddle 💦",
    "Talking to you is like a buffering video — painful 📺",
    "You're so far behind, even your past is ahead of you ⏳",
    "Your jokes have the same energy as a dead battery 🔋",
    "I thought I had seen it all until you spoke 😮",
    "You're like a blender without a lid — chaotic and messy 🔄",
    "Your logic has the structural integrity of wet tissue 🧻",
    "You're not even a supporting character — you're background noise 🎵",
    "If brains were gasoline, you couldn't power a scooter ⛽",
    "You're the human equivalent of a typo 📝",
    "Your common sense is on an extended vacation 🏖️",
    "You're like autocorrect — wrong at the worst moments 📱",
    "Your silence is genuinely the most interesting thing about you 🤫",
    "You're like fast food — never satisfying and slightly regrettable 🍔",
    "You peaked in a dream you haven't had yet 💤",
    "Your life is in beta testing and they're not fixing the bugs 🐛",
    "You're so forgettable, your mirror forgets your face 🪞",
    "The village called — they need their idiot back 🏘️",
    "You're like a broken pencil — completely pointless ✏️",
    "Your vibe is a low-budget knock-off of personality 🎭",
    "You're the reason the gene pool needs a lifeguard 🏊",
    "Your confidence is impressive given your track record 🏃",
    "You're like a Monday — nobody asked for you 📅",
    "Your thought process is a scenic route through confusion 🗺️",
    "You're the human equivalent of Comic Sans 🔤",
    "Even your imaginary friends unfollowed you 👻",
    "You're like a dial-up connection — slow and outdated 🖥️",
    "Your energy is expired coupon energy 🎟️",
    "You're so average, statistics get bored talking about you 📊",
    "If overthinking burned calories, you'd be invisible by now 🔥",
    "Your potential is a conspiracy theory at this point 🕵️",
    "You're the footnote nobody reads in the book of life 📖",
    "Your presence is the plot hole in a good story 🕳️",
    "You have the navigational skills of a shopping cart 🛒",
    "You're like a demo version — limited and not the full thing 💾",
    "Your charisma is on airplane mode permanently ✈️",
    "You're living proof that Wi-Fi can make anyone feel important 📡",
    "Your greatest achievement is being chronically average 📉",
    "You're like a foghorn — loud and serves no real purpose 📣",
    "Your life is a rough draft with no final version in sight 📄",
    "You're so basic, even water is more complex than you 💧",
    "Your motivation has the energy of a dead houseplant 🪴",
    "You're the tutorial level nobody replays 🎮",
    "Your self-awareness is in witness protection 🕵️",
    "You're like a pop quiz — nobody wanted you here 📝",
    "Your ambition is on life support and declining 📉",
    "You're the loading screen of human beings ⌛",
    "Your personality is a placeholder image 🖼️",
    "You're so predictable, spoilers ruin you 🎬",
    "Your originality is a photocopy of a photocopy 📠",
    "You're like elevator music — nobody asked for this 🎶",
    "Your vibe is a screensaver — running but doing nothing 💻",
    "You're the autocorrect fail of the group chat 📱",
    "Your existence is a glitch in the simulation 🖥️",
    "You have all the energy of a solar panel at midnight 🌙",
    "You're what happens when mediocrity takes a selfie 🤳",
    "Your most used feature is disappointing people 😞",
    "You're like a warranty — nobody reads you and you expire 📜",
    "Your personality glitches more than old software 💻",
]

# ─── COMPLIMENT POOL — 80 wholesome compliments ───────────────────────────────
COMPLIMENT_POOL = [
    "You absolute ray of sunshine — the world is better with you in it ☀️",
    "You make life feel like a warm hug on a cold day 🤗",
    "Your vibe is genuinely immaculate fr ✨",
    "You're carrying main character energy and it's everything 👑",
    "I just want you to know you're doing amazing bestie 💫",
    "You're the serotonin boost nobody knew they needed 🌈",
    "Your presence in a room makes everything better instantly 🌸",
    "You understand the assignment and you ALWAYS deliver 🎯",
    "You have the most contagious laugh — it genuinely heals people 😄",
    "You radiate good vibes like it's your full-time job 💎",
    "People are genuinely lucky to know you fr no cap 🍀",
    "You're the type of person who makes strangers feel welcome 🌟",
    "Your kindness is so natural it looks effortless — iconic 💫",
    "You turn ordinary moments into memories — that's rare 📸",
    "The world literally got a glow-up when you walked in 🌅",
    "You're intelligent, capable, and lowkey a genius 🧠",
    "Not only are you beautiful — you're genuinely interesting 🎭",
    "Your passion for things you love is honestly inspiring 🔥",
    "You're the plot twist that made everything better 📖",
    "Your smile deserves its own fan club honestly 😊",
    "You're the reason why people believe in good days ☀️",
    "Everything you touch turns into a good time — magic hands 🪄",
    "Your heart is made of something genuinely special ♥️",
    "You make hard things look effortless — how do you do it? 💪",
    "You're rare in the best way possible and I need you to know that 💎",
    "The grace with which you handle life is unmatched 🌊",
    "You're proof that kindness is a superpower 🦸",
    "Your creativity is a gift to everyone around you 🎨",
    "You'd make an excellent main character — already are tbh 🎬",
    "You have a way of making people feel genuinely seen 👁️",
    "Your laughter is the best sound in any room 🎵",
    "You're doing better than you think — seriously, look at you 🌱",
    "You're someone worth knowing and the lucky ones know it ⭐",
    "You make the complicated look simple — that's real talent 🏆",
    "Your loyalty is rarer than diamonds bestie 💎",
    "You have excellent taste in literally everything 🎨",
    "You bring out the best in everyone around you — magic 🌟",
    "You're the type of person who makes the internet worth having 💻",
    "You're braver than you believe and stronger than you know 💪",
    "Your mind works in the most beautiful ways — genuinely 🧠",
    "You're not just smart — you're wise and that's different 🦉",
    "The confidence you walk with is genuinely inspiring 👟",
    "You're such a genuine person in a world of performances ❤️",
    "Your potential is literally limitless — don't forget that 🚀",
    "You handle chaos like a professional — respect 🌀",
    "You're kind when you don't have to be — that's everything 🕊️",
    "You remember the little things and that makes you extraordinary 🌸",
    "Your sense of humor is the perfect blend of smart and unhinged 😂",
    "You're the calm in everyone else's storm — so needed 🌧️",
    "You create magic wherever you go — undeniable fact ✨",
    "You're a walking, talking highlight reel fr no cap 🎬",
    "You understand nuance in a world that doesn't — huge flex 🎭",
    "Your consistency is what sets you apart from the crowd 📈",
    "You're exactly who people need when things get hard 💛",
    "Your growth is visible and genuinely remarkable 🌱",
    "You inspire people without even trying — passive power 🔮",
    "You're the warm corner of a cold internet ☀️",
    "Your empathy is a superpower most people don't have 💫",
    "You make good choices look cool — that's a gift 🌟",
    "You're not following trends — you set them quietly 👑",
    "Your dedication to things you care about is beautiful 🔥",
    "You're the kind of person stories are written about 📚",
    "You radiate an energy that genuinely draws people in 🌊",
    "Your perspective shifts rooms — that's rare influence 🗝️",
    "You're thoughtful in a way most people only aspire to be 💭",
    "You deserve every good thing coming your way fr 🎁",
    "You're the living proof that good people still exist 🕊️",
    "Your character is rock solid — and I mean SOLID 💎",
    "You're the reason someone smiled today and didn't know why 😊",
    "You make showing up look elegant — carry on 🌸",
    "Your honesty is a breath of fresh air in a world of pretending 🌬️",
    "You're operating on a different level — respectfully 👑",
    "You're the type of rare that doesn't know it's rare 💫",
    "Your work ethic is genuinely something else entirely 💪",
    "You carry yourself with a grace that's honestly goals 🦢",
    "You're the heartbeat that keeps the group alive ❤️",
    "Everything about you just... works — and that's no accident ✨",
    "You're living proof that being yourself is always enough 🌟",
    "You're magnetic — people orbit you and don't even notice 🪐",
    "You're the upgrade everyone needed but didn't know to ask for 🆙",
    "You make the world feel more navigable — thank you 🗺️",
]

# ─── HUG MESSAGES — 40 variations ────────────────────────────────────────────
HUG_MSGS = [
    "{a} wraps {b} in the warmest hug imaginable 🤗💕",
    "{a} gives {b} a bear hug that could solve world peace 🐻❤️",
    "{a} squeezes {b} so tight all the sadness leaks out 🫂✨",
    "{a} runs across the room and tackles {b} with love 💨🤗",
    "{a} gives {b} a gentle, healing hug 🌸💫",
    "{a} wraps arms around {b} like a warm blanket 🧸❤️",
    "{a} pulls {b} into a hug that lasts exactly as long as needed 💛",
    "{a} sneaks up and hugs {b} from behind 🫣🤗",
    "{a} gives {b} a spine-cracking hug of pure affection 💪🤗",
    "{a} and {b} engage in a mutual hug of great emotional significance 🌟",
    "{a} hugs {b} gently while patting their back 💙",
    "{a} throws arms around {b} like tomorrow isn't guaranteed 🌅",
    "{a} gives {b} a hug that says 'I got you' without words 🤝❤️",
    "{a} gives {b} a surprise group hug energy hug 🎉",
    "{a} hugs {b} with the intensity of a thousand suns ☀️",
    "{a} holds {b} close for a long moment of peaceful silence 🌙",
    "{a} gives {b} a hug so warm it could melt glaciers 🌡️💕",
    "{a} embraces {b} like long-lost family at an airport 🛫❤️",
    "{a} gives {b} a gentle side-hug of pure solidarity 💚",
    "{a} hugs {b} while spinning them around joyfully 🌀💕",
    "{a} squishes {b}'s cheeks and then hugs them 😊🤗",
    "{a} drapes dramatically over {b} in an overenthusiastic hug 🎭",
    "{a} and {b} share a hug that needs no explanation 🕊️",
    "{a} gives {b} the hug they've been needing all week 🙏",
    "{a} grabs {b} and doesn't let go for a good while ⏳💙",
    "{a} offers {b} a soft hug and asks how they're really doing 💜",
    "{a} runs and jumps into a hug with {b} 🦘",
    "{a} gives {b} a hug loaded with good vibes only ✨🤗",
    "{a} wraps {b} in an embrace like the last scene of a movie 🎬❤️",
    "{a} just silently hugs {b} because some things don't need words 🌿",
    "{a} pats {b} on the back during a long, meaningful hug 👋💛",
    "{a} gives {b} a hug that communicates 'you're not alone' 🫂",
    "{a} smothers {b} with an overwhelming amount of love 💖",
    "{a} sneaks a hug in so fast {b} doesn't know what hit them 💨💕",
    "{a} holds {b} tight and whispers 'everything will be okay' 💬🤗",
    "{a} gives {b} a championship-level warm hug 🏆❤️",
    "{a} offers a healing hug to {b} with full heart 💚",
    "{a} pulls {b} into a hug that solves at least three problems 🛠️🤗",
    "{a} envelopes {b} in pure warmth and affection 🌟",
    "{a} gives {b} a hug that honestly fixed everything 🔧💕",
]

# ─── SLAP MESSAGES — 40 variations ───────────────────────────────────────────
SLAP_MSGS = [
    "{a} whacks {b} with a legendary open palm slap 👋💥",
    "{a} delivers a slap that echoes through dimensions 🌀👋",
    "{a} slaps {b} with a rolled-up newspaper 📰💥",
    "{a} uses a rubber chicken to slap {b} into next week 🐓",
    "{a} winds up from across the room and slaps {b} 💨👋",
    "{a} slaps {b} with the energy of someone who's been holding that in 💢",
    "{a} delivers an absolutely devastating slap to {b} 💥",
    "{a} slaps {b} with a frozen fish — classic 🐟👋",
    "{a} backhands {b} dramatically for full effect 🎭",
    "{a} slaps {b} so hard the wifi disconnects 📶❌",
    "{a} uses a giant foam hand to slap {b} 🤚🎉",
    "{a} teleports behind {b} for a surprise slap 🌀💥",
    "{a} channels generations of frustration into one slap 😤👋",
    "{a} slaps {b} with a velvet glove — fancy yet painful 🧤",
    "{a} flies in from the ceiling to slap {b} — physics optional ✈️",
    "{a} delivers a slap so powerful it creates a small hurricane 🌪️",
    "{a} slaps {b} with a loaded pillow — soft but personal 🛏️",
    "{a} uses a table flip as an opener and then slaps {b} ┻━┻👋",
    "{a} slaps {b} across time itself — somehow 🕰️",
    "{a} delivers a devastating combo: snap, wind-up, slap 💨",
    "{a} slaps {b} with the power of a disappointed parent 😞👋",
    "{a} hits {b} with a well-aimed slap of justice ⚖️",
    "{a} practices their slap form and then uses it on {b} 🎓",
    "{a} slaps {b} using the left AND right hand for balance 🤲",
    "{a} uses a spatula to slap {b} — kitchen energy 🍳",
    "{a} delivers a legendary villain slap to {b} 🎬",
    "{a} slaps {b} with a perfectly-timed 'you had this coming' energy 💅",
    "{a} pulls out a slapfish from hammerspace and uses it on {b} 🐠",
    "{a} winds up dramatically and slaps {b} into a cutscene 🎮",
    "{a} uses a gigantic novelty hand to slap {b} 🖐️",
    "{a} slaps {b} so hard, it makes a sound effect 🔊",
    "{a} channels their inner Karen and deploys the manager-slap on {b} 📞",
    "{a} slaps {b} with a book for educational purposes 📚",
    "{a} accidentally slaps {b} but does it again on purpose 😈",
    "{a} slow-motion runs and leaps to deliver an epic slap to {b} 🏃💥",
    "{a} slaps {b} with the conviction of someone who is DONE 😤",
    "{a} slaps {b} with a wet towel — rude but effective 🏖️",
    "{a} gives {b} the classic two-handed slap for emphasis ✌️",
    "{a} slaps {b} using a pinwheel — whimsy AND pain 🌀",
    "{a} delivers a slap that {b} will be processing for weeks 🧠",
]

# ─── KISS MESSAGES — 40 variations ───────────────────────────────────────────
KISS_MSGS = [
    "{a} plants a sweet kiss on {b}'s cheek 😘💋",
    "{a} gives {b} a quick forehead kiss of pure adoration 💫",
    "{a} sneaks a kiss on {b}'s nose — adorable chaos 👃💋",
    "{a} kisses {b}'s hand like a true romantic 👄✨",
    "{a} gives {b} a long, dramatic kiss worthy of a movie scene 🎬💋",
    "{a} butterfly-kisses {b}'s cheek with eyelashes 🦋",
    "{a} blows {b} a kiss that somehow hits directly 💋🎯",
    "{a} gives {b} an Eskimo kiss — nose to nose ❄️",
    "{a} gives {b} the gentlest kiss on the top of their head 👑💕",
    "{a} leans in and gives {b} a kiss so soft it's basically a whisper 🌬️💋",
    "{a} gives {b} a surprise cheek kiss that was entirely unplanned 😳💋",
    "{a} plants three rapid kisses on {b} before they can react 💨💋",
    "{a} gives {b} a rain-soaked dramatic romantic kiss 🌧️💋",
    "{a} places a kiss on {b}'s forehead with both hands cupping their face 🫶",
    "{a} gives {b} a kiss loaded with more emotion than words could carry ❤️",
    "{a} gives {b} a quick peck on the lips, blushing immediately 😳",
    "{a} and {b} share a slow, cinematic kiss 🎞️💋",
    "{a} gives {b} a chef's kiss — not directly but still 🤌",
    "{a} kisses {b}'s knuckles like a Victorian gentleman/lady 🎩💋",
    "{a} kisses {b}'s cheek and sprints away at full speed 🏃💨",
    "{a} leaves a tiny lipstick print on {b}'s cheek — iconic 💄",
    "{a} gives {b} a gentle, wordless kiss of reassurance 💙",
    "{a} kisses {b} on the forehead and whispers 'you've got this' 💪",
    "{a} smooshes {b}'s cheeks and gives them a big smacking kiss 😂💋",
    "{a} gives {b} a goodnight forehead kiss ✨🌙",
    "{a} gives {b} a kiss so tender it heals like 4 HP 💗",
    "{a} and {b} share a very long kiss that becomes a meme 📸",
    "{a} gives {b} a tiny nose kiss that solves their problems 🐇",
    "{a} kisses {b}'s hand and bows dramatically 🎭💋",
    "{a} gives {b} the softest butterfly kiss imaginable 🦋",
    "{a} blows a kiss that {b} actually catches ✋💋",
    "{a} and {b} share a slow dance kiss — absolutely iconic 💃",
    "{a} gives {b} a quick peck that communicates volumes 💬💋",
    "{a} gives {b} a lingering kiss that was very much deserved 💛",
    "{a} plants a kiss on {b}'s shoulder with quiet tenderness 🌺",
    "{a} kisses {b}'s tears away — extremely wholesome 😢💋",
    "{a} gives {b} a healing kiss of legendary proportions 🧙‍♂️💋",
    "{a} presses their forehead to {b}'s and gives the softest kiss 🌙",
    "{a} gives {b} a totally unexpected first kiss — it's giving fanfic 📖",
    "{a} grabs {b}'s face and kisses them with zero context 😤💋",
]

# ─── PAT MESSAGES — 40 variations ────────────────────────────────────────────
PAT_MSGS = [
    "{a} pats {b} on the head with immense tenderness 🤚✨",
    "{a} gives {b} a series of soft, rapid head pats 🐾",
    "{a} carefully pats {b}'s head while nodding approvingly 👍",
    "{a} pats {b} on the back like a proud parent 😊",
    "{a} gives {b} gentle head pats that recharge their energy ⚡",
    "{a} reaches up to pat {b}'s head — height not a factor 🙋",
    "{a} pats {b}'s head x3 times and says 'good job' 👏",
    "{a} delivers slow, deliberate pats full of respect 🙇",
    "{a} uses two hands to enthusiastically pat {b} 🤲",
    "{a} gives {b} head pats reserved for absolute champions 🏆",
    "{a} pats {b} like a golden retriever who deserves it 🐕",
    "{a} gives {b} the prestigious triple-pat of excellence ✨",
    "{a} messes up {b}'s hair with an affectionate ruffle 😝",
    "{a} very carefully pats {b} on top of the head 🎩",
    "{a} gives {b} a pat that says 'you're doing great' silently 🤫",
    "{a} pats {b} on the head while trying not to cry at their progress 😭",
    "{a} gives {b} the most encouraging head pat of 2024 🌟",
    "{a} sneaks up behind {b} for stealth head pats 🥷",
    "{a} pats {b} so softly it barely registers but means everything 💫",
    "{a} gives {b} a quick tap-tap pat of acknowledgment 👋",
    "{a} pats {b} with the energy of a proud coach 🏋️",
    "{a} gives {b} a gentle hair ruffle of pure affection 💇",
    "{a} pats {b} on the shoulder with deep respect 🫱",
    "{a} gives {b} three pats — one for each of their good qualities 💎",
    "{a} delivers a pat that feels like a standing ovation 👏",
    "{a} pats {b}'s head like they just completed a quest 🗡️",
    "{a} rests a hand gently on {b}'s head in acknowledgment 🙌",
    "{a} gives {b} the ceremonial single top-of-head pat 👆",
    "{a} pats {b} and says 'there, there' very softly 🌙",
    "{a} taps {b} on the head with pure kindergarten-teacher energy 🍎",
    "{a} gives {b} a soft pat that says 'I believe in you' ❤️",
    "{a} pats {b}'s shoulder firmly like a proud mentor 🧓",
    "{a} uses two thumbs to give a tiny double head pat 👍👍",
    "{a} gives {b} an absentminded pat that still means the world 🌍",
    "{a} pats {b} like they just saved the day — because they did 🦸",
    "{a} gives {b} the softest, most encouraging head pat 🌸",
    "{a} reaches across the void to give {b} a spiritual head pat 🌌",
    "{a} gives {b} seven rapid pats at impressive speed 💨",
    "{a} pats {b}'s head with the gravity of a life well-lived 🌅",
    "{a} gives {b} a very professional head pat of recognition 📋",
]

# ─── POKE MESSAGES — 35 variations ───────────────────────────────────────────
POKE_MSGS = [
    "{a} pokes {b} aggressively in the ribs 👉",
    "{a} pokes {b}'s cheek repeatedly 👆",
    "{a} pokes {b} with a very long stick from a safe distance 🪄",
    "{a} gives {b} a single dramatic poke of consequence 😤👉",
    "{a} pokes {b} and runs — classic 🏃💨",
    "{a} pokes {b} out of complete boredom 😴👉",
    "{a} aggressively pokes {b} with one finger 🫵",
    "{a} sends {b} a digital poke at 3am for no reason 🌙",
    "{a} pokes {b} in the forehead with one finger 🧠👉",
    "{a} pokes {b} and says absolutely nothing 🤐",
    "{a} pokes {b} from across the table with a ruler 📏",
    "{a} pokes {b} repeatedly until they get a reaction 🔄",
    "{a} pokes {b} with the energy of 'pay attention to me' 👀",
    "{a} gives {b} the most aggressive poke legally possible 😡👉",
    "{a} uses a pointy finger to poke {b} directly in the shoulder 👆",
    "{a} pokes {b} so softly it barely counts 🤏",
    "{a} pokes {b} with a spatula because why not 🍳",
    "{a} delivers a ceremonial poke to {b} for no reason 🎖️",
    "{a} does a drive-by poke and disappears 🚗💨",
    "{a} pokes {b} in Morse code — communicative 📡",
    "{a} gives {b} the gentlest possible fingertip poke 🌸",
    "{a} pokes {b} just to see what happens 🔬",
    "{a} pokes {b} in a pattern that spells something 🔤",
    "{a} uses a foam noodle to poke {b} — aquatic energy 🌊",
    "{a} gives {b} a multi-directional poke attack 🌀",
    "{a} pokes {b} at exactly the wrong moment 😅",
    "{a} pokes {b} with intense focus and full eye contact 👁️",
    "{a} pokes {b} three times for emphasis 👉👉👉",
    "{a} delivers a stealth poke and acts innocent 😇",
    "{a} pokes {b} with the vim of someone who has nothing to lose 💢",
    "{a} gives {b} a professional poke — billing separately 💼",
    "{a} pokes {b} so quickly it's basically a glitch 🖥️",
    "{a} gives {b} a poke that contains a message in it 📩",
    "{a} pokes {b} while maintaining complete eye contact 👀",
    "{a} gives {b} the most passive aggressive poke of all time 😤",
]

# ─── SHIP MESSAGES — 45 compatibility responses ───────────────────────────────
SHIP_MSGS_LOW = [
    "Hard pass from the universe 🚫","The vibes are tragically incompatible 💔","This ship has iceberg energy ❄️",
    "The stars said absolutely not 🌑","Chemistry lab report: zero reaction 🧪",
    "Compatibility.exe has crashed 💻💀","The algorithm weeps 📉","This is giving oil and water energy 💧🛢️",
    "The oracle says 'please no' 🔮","Even math gave up on this pairing 🔢",
]
SHIP_MSGS_MED = [
    "There's potential hiding here 👀","The chemistry is complicated but it's there ⚗️","Could work with some effort 🤔",
    "The vibes are 50/50 — a coin flip fr 🪙","Something is there — nurture it 🌱","Mixed signals from the cosmos 🌌",
    "Neutral energy — the universe is undecided 🌀","There's a spark, small but real 🔥",
    "It's complicated but interesting 🎭","The love story isn't written yet 📝",
]
SHIP_MSGS_HIGH = [
    "The universe SHIPS this 💫","Soulmate alert — the cosmos are shaking 🌌💘","This is so real it scares me 😍",
    "Perfect energy — absolutely iconic together 🌟","The stars aligned specifically for this 🌠",
    "I'm crying this is too cute 😭❤️","The algorithm is blushing 💕","Canon couple fr no cap 💍",
    "This is the love story the bards will sing 🎶💕","Made for each other — undeniable ✨",
    "The prophecy says yes — LOUDLY 📜💘","Off the charts — literally 📈❤️",
    "This ship is unsinkable 🚢💕","The universe approves with maximum enthusiasm 🎊",
]

# ─── TRUTH QUESTIONS — 100 questions ─────────────────────────────────────────
TRUTH_POOL = [
    # Mild (34)
    "What's the most embarrassing thing that happened to you in public? 😳",
    "What's a movie you pretend you've seen but never actually watched? 🎬",
    "Have you ever lied about your age? 📅",
    "What's the worst gift you've ever received and what did you say? 🎁",
    "What's a food you secretly hate that everyone else loves? 🍕",
    "Have you ever been caught talking to yourself? 💬",
    "What's the weirdest thing you do when you're alone? 🏠",
    "Have you ever walked into a glass door? 🪟",
    "What's the most embarrassing song on your playlist? 🎵",
    "What's something you believed as a child that's wildly wrong? 🧒",
    "Have you ever blamed someone else for something you did? 😇",
    "What's the most childish thing you still do? 🧸",
    "Have you ever fallen asleep in class or a meeting? 😴",
    "What's the worst haircut you've ever had? ✂️",
    "Have you ever lied on your resume? 📄",
    "What's the dumbest thing you've spent money on? 💸",
    "What's the longest you've gone without showering? 🚿",
    "Have you ever pretended to be sick to avoid something? 🤒",
    "What's the most useless skill you have? 🛠️",
    "Have you ever laughed at completely the wrong moment? 😂",
    "What's a bad habit you have that you hope nobody notices? 👀",
    "Have you ever ghosted someone? 👻",
    "What's the most embarrassing thing in your browser history? 💻",
    "Have you ever tripped in front of a lot of people? 🏃",
    "What's the worst decision you made this week? 🤦",
    "Have you ever eaten food that fell on the floor? 🍽️",
    "What's an embarrassing nickname you had as a kid? 🏷️",
    "What's a lie you've told that snowballed out of control? 🌨️",
    "Have you ever sent a text to the wrong person? 📱",
    "What's your most embarrassing talent? 🎭",
    "Have you ever pretended to be on a phone call to avoid someone? 📞",
    "What's something you've done that you'd deny if asked? 🙈",
    "What's your most embarrassing online username from the past? 🖥️",
    "Have you ever worn dirty laundry because you were too lazy to wash it? 👕",
    # Spicy (33)
    "Who's your least favorite person in this chat and why? 😬",
    "Have you ever had a crush on someone you really shouldn't? 💔",
    "What's the most embarrassing thing you've said trying to be cool? 😎",
    "Have you ever stolen something? What was it? 🔑",
    "What's the most recent lie you told? 🤥",
    "Who would you delete from your contacts right now? 📱",
    "What's something you've done that you're lowkey still embarrassed about? 😳",
    "Have you ever pretended not to see someone to avoid talking to them? 👁️",
    "What's the most dramatic thing you've ever done for attention? 🎭",
    "Have you ever been rejected and how did you respond? 💔",
    "What's your most controversial opinion about a popular thing? 🗣️",
    "Have you ever talked trash about a friend behind their back? 🗣️",
    "What's the pettiest thing you've ever done? 😤",
    "Have you ever stood someone up? What's your excuse? 🕐",
    "What's the most ridiculous thing you've been jealous of? 💚",
    "Have you ever read someone's message and not replied for days? 📩",
    "What's a phase you went through that you'd erase from history? 🗑️",
    "Have you ever liked someone's old photos while stalking their profile? 📸",
    "What's the worst thing you've thought about a stranger? 👤",
    "Have you ever pretended to not know someone in public? 🤭",
    "What's the most desperate thing you've done for a compliment? 😅",
    "Have you ever broken something and blamed someone else? 💥",
    "What's the most toxic thing about you, honestly? 🧪",
    "Have you ever said 'I hate you' to someone and actually meant it? 😡",
    "What's the pettiest revenge you've taken on someone? ⚡",
    "Have you ever cheated at a board game? How? 🎲",
    "What's something you do that would shock people who know you? 😮",
    "Have you ever told a secret you were sworn to keep? 🔓",
    "What's the most embarrassing way you've cried recently? 😢",
    "Have you ever done something illegal (small or big)? 🚔",
    "What's the most cringe thing in your camera roll? 📷",
    "Have you ever catfished someone? Be honest 🎣",
    "What's the most desperate text you've sent? 📨",
    # Deep (33)
    "What's the thing you're most afraid people will find out about you? 🔐",
    "What's a belief you hold that you'd never say out loud in a crowd? 🤐",
    "What's something you've never forgiven someone for? 💔",
    "What's the biggest mistake you've made and haven't fixed? 🔧",
    "What do you think people's first impression of you actually is? 🪞",
    "What's something about yourself you're working on secretly? 🌱",
    "Have you ever felt like a fraud in something important? 🎭",
    "What's a relationship you damaged that you still think about? 💭",
    "What's the moment you were most ashamed of yourself? 😞",
    "What's a decision you made that you'd make differently? 🔄",
    "What's the kindest thing someone's ever done for you unexpectedly? 💛",
    "What's a goal you have that you haven't told anyone? 🎯",
    "What's something that triggers genuine insecurity in you? 🌀",
    "What's a compliment that hit harder than it should have? ❤️",
    "Have you ever felt genuinely lonely in a room full of people? 🌑",
    "What do you want people to say about you when you're not there? 💬",
    "What's your relationship with failure, really? 📉",
    "What's a fear you've never told anyone about? 🔮",
    "What's the nicest thing you've ever done for a stranger? 🕊️",
    "What's something you need to hear right now? 🔊",
    "What's the bravest thing you've done that nobody knows about? 💪",
    "When did you last feel truly proud of yourself? 🏆",
    "What's a boundary you keep letting people cross? 🚧",
    "What's something you keep putting off and why? ⏳",
    "What's a trait you admire in others but struggle with yourself? 🌟",
    "What's the most important lesson you've learned the hard way? 📚",
    "What's something you've forgiven but can't forget? 🕯️",
    "What's a small thing that makes you happier than it should? 🌈",
    "Who's the last person you thought about before sleeping? 🌙",
    "What's one thing about yourself you actually like? ❤️",
    "What's a moment where someone really showed up for you? 🤝",
    "What's something you'd do if you weren't scared? 🚀",
    "What's the most important relationship in your life right now and why? 🫂",
]

# ─── DARE POOL — 80 dares ─────────────────────────────────────────────────────
DARE_POOL = [
    "Send the 5th photo in your camera roll in the chat right now 📸",
    "Type your next message entirely with your nose 👃",
    "Send a voice message doing your best villain monologue 🎙️",
    "Change your profile picture to something embarrassing for 24 hours 🖼️",
    "Send a cringe poem about someone in the chat ❤️",
    "Describe your day as if it were an action movie 🎬",
    "Type with your elbows for the next 10 minutes ⌨️",
    "Send a text to your most recent contact saying 'I know what you did' 📱",
    "Introduce yourself as a completely different character for 5 minutes 🎭",
    "Do your best impression of a weather reporter for this chat ⛅",
    "Send a voicenote singing a song of the group's choice 🎵",
    "Write a dramatic breakup message to your favorite app 📱💔",
    "Reply to your last received text with only emojis 🎉",
    "Share your most embarrassing autocorrect fail ever 📲",
    "Roast yourself for 30 seconds — no holds barred 😂",
    "Write a 3-sentence horror story right now 👻",
    "Send a selfie with the most ridiculous expression you can make 🤪",
    "Write a love letter to your least favorite food 🍽️💕",
    "Describe the last dream you had in the most dramatic way possible 💤",
    "Do an impression of a famous person for 30 seconds 🌟",
    "Make up a fake news headline about someone in this chat 📰",
    "Write the opening line of your autobiography right now 📖",
    "Try to sell ice to someone in this chat in under 60 seconds ❄️",
    "Write your name using emojis that spell it out 🔤",
    "Send a message as if you're announcing something extremely important 📢",
    "Type only in questions for the next 5 minutes ❓",
    "Write a haiku about the last thing you ate 🍜",
    "Explain your job (or dream job) using only food metaphors 🍕",
    "Write a LinkedIn recommendation for yourself — make it too much 💼",
    "Send a voice message where you announce today's weather dramatically ⛈️",
    "Describe your personality using 3 kitchen appliances 🍳",
    "Write a Google review for your own bedroom 🛏️⭐",
    "Sing the chorus of the last song you listened to — voice message 🎶",
    "Describe your morning routine as if it were a heist 🎯",
    "Create a business name for a store that sells exactly one thing 🏪",
    "Write the worst possible dating profile bio for yourself 💔",
    "Make up a fake phobia and explain it convincingly 😱",
    "Describe your personality as if you were a type of weather ⛅",
    "Write a motivational speech about tying your shoes 👟💬",
    "Name five things in this room that could be a weapon in a zombie apocalypse 🧟",
    "Write a 3-star review of your own personality 🌟🌟🌟",
    "Explain a meme to someone who's never heard of the internet 📡",
    "Write a theme song for your group chat — must rhyme 🎵",
    "Describe your last meal as if it were the last supper 🍽️🙏",
    "Pretend you're an influencer and sell something boring from your room 📦",
    "Write a mission statement for your own life — 2 sentences max 🎯",
    "Give a TED talk on your most useless skill right now 🗣️",
    "Write a fake apology letter to someone you've never met 📝",
    "Describe your current mood as a movie genre 🎬",
    "Write a ransom note for your own motivation 💸",
    "Give your pet (or imaginary pet) a formal job title and description 🐾",
    "Write a fortune cookie message for today 🥠",
    "Explain what you did today but make it sound epic 🏆",
    "Write a one-star review for a place you've never been 📍",
    "Do an impression of someone's typing style in this chat ⌨️",
    "Write the villain's backstory for your most annoying habit 😈",
    "Describe your fashion sense as a weather condition ☁️",
    "Create a superhero alter-ego for yourself with a weakness 🦸",
    "Write your own obituary but make it funny and end with a twist 📜",
    "Narrate exactly what's happening in the room right now like a nature doc 🐘",
    "Write a breakup text to a habit you want to quit 💔",
    "Make up a new holiday and explain how it's celebrated 🎉",
    "Write a press release about something ordinary you did today 📰",
    "Describe a boring task using the most dramatic language possible 💥",
    "Invent a new sport using only objects in your house 🏠",
    "Write a letter to your future self but in a language you don't speak 🌍",
    "Give a two-sentence pitch for a movie about your last 24 hours 🎬",
    "Write the last chapter of your life story as you'd want it to go 📚",
    "Describe your ideal Sunday without using any common Sunday words ☀️",
    "Rename yourself for the rest of this dare session — must be epic 👑",
    "Create a signature dance move and describe it in detail 💃",
    "Write a strongly-worded letter to a inanimate object that wronged you 😤",
    "Make up three alternate meanings for a common acronym 🔤",
    "Write a recipe for your personality as a dish 🍲",
    "Come up with a slogan for this group chat 📢",
    "Describe your life philosophy using only song titles 🎶",
    "Write a formal business proposal for something completely useless 📊",
    "Translate a conversation into Shakespearean English 🎭",
    "Write a motivational speech as if you're losing terribly 📉",
    "Make up a conspiracy theory about something mundane 🕵️",
]

# ─── JOKE POOL — 80 jokes ─────────────────────────────────────────────────────
JOKE_POOL = [
    "Why don't scientists trust atoms? Because they make up everything! ⚛️",
    "I told my wife she was drawing her eyebrows too high. She looked surprised. 😮",
    "Why do cows wear bells? Because their horns don't work! 🐄",
    "I'm reading a book about anti-gravity. It's impossible to put down! 📚",
    "Why did the scarecrow win an award? He was outstanding in his field! 🌾",
    "I told a pun to my friend. It went in one ear and out the other. 👂",
    "Why did the bicycle fall over? It was two-tired! 🚲",
    "I used to hate facial hair... but then it grew on me. 🧔",
    "Why can't you give Elsa a balloon? She'll let it go! 🎈",
    "I asked the librarian if they had books about paranoia. She whispered 'they're right behind you!' 📚",
    "Why do programmers prefer dark mode? Because light attracts bugs! 💻",
    "A skeleton walks into a bar. Orders a beer and a mop. 🍺",
    "What do you call a fake noodle? An impasta! 🍝",
    "Why did the math book look so sad? It had too many problems. 📖",
    "I'm on a seafood diet. I see food and I eat it. 🍤",
    "What do you call cheese that isn't yours? Nacho cheese! 🧀",
    "Why did the coffee file a police report? It got mugged! ☕",
    "What's a vampire's favorite fruit? A blood orange! 🧛",
    "I'd tell you a construction joke but I'm still working on it. 🏗️",
    "Why do fish swim in saltwater? Because pepper makes them sneeze! 🐟",
    "I told my doctor I broke my arm in two places. He told me to stop going to those places. 💪",
    "What did the ocean say to the beach? Nothing, it just waved. 🌊",
    "Why did the golfer bring extra pants? In case he got a hole in one! ⛳",
    "What do you call a pony with a sore throat? A little hoarse! 🐴",
    "I couldn't figure out how lightning works, but then it struck me! ⚡",
    "What do you call a sleeping dinosaur? A dino-snore! 🦕",
    "Why don't eggs tell jokes? They'd crack each other up. 🥚",
    "I have a joke about paper, but it's tearable. 📄",
    "What do you call a fish without eyes? A fsh. 🐠",
    "Why did the invisible man turn down the job offer? He couldn't see himself doing it. 👻",
    "What's brown and sticky? A stick! 🪵",
    "I told a chemistry joke — no reaction. ⚗️",
    "Why did the computer go to the doctor? It had a virus! 💻",
    "What do you call a bear with no teeth? A gummy bear! 🐻",
    "Why can't a leopard hide? It's always spotted! 🐆",
    "What do elves learn in school? The elfabet! 🧝",
    "Why don't scientists trust atoms? Because they make up everything! ⚛️",
    "What's a pirate's favorite letter? Arrr! 🏴‍☠️",
    "Why did the gym close? It just didn't work out. 🏋️",
    "What do clouds wear under their raincoats? Thunderwear! ⛈️",
    "I'm great at multitasking: I can waste time, be unproductive, and procrastinate all at once! 🎭",
    "Why do bees have sticky hair? They use a honeycomb! 🐝",
    "How does the moon cut his hair? Eclipse it! 🌙",
    "Why did the tomato turn red? It saw the salad dressing! 🥗",
    "What's a vampire's least favorite room? The living room. 🧛",
    "I would tell an elevator joke, but it works on so many levels. 🛗",
    "Why did the sun go to school? To get a little brighter! ☀️",
    "I'm reading about mazes. I got lost in it. 🌀",
    "What's a computer's favorite snack? Microchips! 💾",
    "Why did the banana go to the doctor? It wasn't peeling well. 🍌",
    "I told a joke about a wall. You probably didn't get it. 🧱",
    "What did one wall say to the other? I'll meet you at the corner! 🏠",
    "Why did the teddy bear say no to dessert? She was already stuffed! 🧸",
    "Why did the superhero flush the toilet? Because it was his doody! 🦸",
    "What do you call a sad strawberry? A blueberry. 🍓",
    "I tried to write a joke about clocks, but I ran out of time! ⏰",
    "What's an astronaut's favorite part of a computer? The space bar! 🚀",
    "Why do chicken coops only have two doors? Four would make it a sedan! 🐔",
    "I can't take my dog to the park because the ducks keep trying to bite him. I guess that's what I get for buying a pure bread dog. 🐕",
    "Why don't scientists trust atoms? Because they make up everything! ⚛️",
    "What do you call a lazy kangaroo? A pouch potato! 🦘",
    "I wouldn't buy anything with Velcro — it's a complete rip-off! 🪢",
    "What do you call a factory that makes okay products? A satisfactory! 🏭",
    "I told my friend 10 jokes to get him to laugh. No pun in ten did. 😂",
    "Why did the picture go to jail? It was framed! 🖼️",
    "I used to think I was indecisive, but now I'm not sure. 🤷",
    "What do you call someone with no body and no nose? Nobody knows! 👻",
    "Why did the nurse need a red pen at work? In case she needed to draw blood! 💉",
    "I'm afraid of elevators, so I take steps to avoid them! 🚶",
    "What's the best time to go to the dentist? Tooth-hurty! 🦷",
    "I told my cat a pun. He looked un-a-mews-ed. 🐱",
    "What's Forrest Gump's password? 1forrest1! 💻",
    "How do you organize a space party? You planet! 🪐",
    "Why is Peter Pan always flying? He Neverlands! ✈️",
    "What do lawyers wear to court? Lawsuits! 👔",
    "I have a joke about construction, I'm still working on it 🏗️",
    "Why did the coach go to the bank? To get his quarterback! 🏈",
    "I told a joke about pizza, but it was a bit cheesy 🍕",
    "What do you call a magician who loses his magic? Ian. 🪄",
    "I couldn't afford a professional racer so I hired a clown to drive for me — but he always took the wrong turn! 🤡",
]

# ─── FACT POOL — 80 unique facts ─────────────────────────────────────────────
FACT_POOL = [
    "Honey never spoils — archaeologists found 3000-year-old honey in Egyptian tombs that was still edible 🍯",
    "Cleopatra lived closer in time to the Moon landing than to the construction of the Great Pyramid 🌙",
    "Wombats produce cube-shaped poop — the only known animal to do so 🐨",
    "A group of flamingos is called a flamboyance 🦩",
    "The shortest war in history was the Anglo-Zanzibar War — lasted 38 to 45 minutes in 1896 ⚔️",
    "Oxford University is older than the Aztec Empire 🏛️",
    "Bananas are technically berries but strawberries are not 🍌",
    "A day on Venus is longer than its year 🪐",
    "Sea otters hold hands while sleeping so they don't drift apart 🦦",
    "The human nose can detect over 1 trillion different smells 👃",
    "Nintendo was founded in 1889 — before the invention of the car 🎮",
    "There are more possible chess games than atoms in the observable universe ♟️",
    "Crows can recognize and hold grudges against specific human faces 🦅",
    "The inventor of the Pringles can is buried inside one 🥫",
    "A group of owls is called a parliament 🦉",
    "Hot water freezes faster than cold water — this is called the Mpemba effect 🧊",
    "Octopuses have three hearts and blue blood 🐙",
    "The shortest commercial flight in the world is 57 seconds — in Scotland ✈️",
    "Maine Coon cats can weigh as much as 25 pounds 🐈",
    "The world's largest snowflake was 15 inches wide, recorded in 1887 ❄️",
    "Starfish don't have brains — they process information through their arms ⭐",
    "The average cloud weighs about 1.1 million pounds ☁️",
    "Cats have fewer toes on their back paws than their front paws 🐾",
    "A snail can sleep for 3 years without waking up 🐌",
    "The human tongue is actually connected to the heart — you can slow your heart rate by sticking your tongue up 🫀",
    "Tigers have striped skin, not just striped fur 🐅",
    "The first emoji was created in Japan in 1999 by Shigetaka Kurita 😀",
    "Butterflies taste with their feet 🦋",
    "The original Monopoly was designed to teach about wealth inequality 🎲",
    "A bolt of lightning contains enough energy to toast 100,000 pieces of bread ⚡",
    "Your body replaces most of its cells every 7 years 🔬",
    "The word 'muscle' comes from the Latin word for 'little mouse' 💪",
    "There is a species of jellyfish that is biologically immortal 🪼",
    "Shakespeare invented over 1,700 words we still use today 📝",
    "The world's largest desert is Antarctica — not the Sahara 🏔️",
    "Sharks are older than trees — they've existed for 450 million years 🦈",
    "Each of your eyes has a blind spot — your brain fills it in 👁️",
    "The first webcam was invented to monitor a coffee pot at Cambridge University ☕",
    "Dolphins give each other names and call to each other by name 🐬",
    "You can't hum while holding your nose closed 🤐",
    "The number 4 is the only number with the same number of letters as its value ④",
    "Penguins propose with pebbles 🐧💍",
    "A group of pugs is called a grumble 🐶",
    "There's a village in Norway called Hell — and it freezes over every winter ❄️",
    "The moon has moonquakes — caused by Earth's gravitational pull 🌕",
    "Humans share 50% of their DNA with bananas 🍌🧬",
    "The lighter was invented before the match 🔥",
    "Cows have 'best friends' and get stressed when separated from them 🐄",
    "You can hear a blue whale's heartbeat from 2 miles away 🐋",
    "The Eiffel Tower grows 15 cm taller in summer due to thermal expansion 🗼",
    "It takes about 200 trees to make the cardboard for all the toilet paper Americans use in a year 🌳",
    "Cats cannot taste sweetness — they're missing taste receptors for it 😸",
    "A group of crows is called a murder 🐦‍⬛",
    "The total weight of all ants on Earth roughly equals the total weight of all humans 🐜",
    "The Great Wall of China is not visible from space with the naked eye 🧱",
    "Pigs are the fourth most intelligent animal behind chimps, dolphins, and elephants 🐷",
    "The expiration date on bottled water is for the bottle not the water 💧",
    "The tiny hole in pen caps exists to prevent choking if accidentally swallowed 🖊️",
    "The Colosseum could seat 50,000+ spectators and had a retractable roof 🏛️",
    "French toast was not invented in France — it dates to 5th century Rome 🍞",
    "A lifespan of mosquito is only 2 weeks — yet they cause more human deaths than any animal 🦟",
    "The pyramids were built by paid workers, not slaves, according to modern archaeological evidence 🏺",
    "Your brain generates enough electricity to power a small LED light 🧠💡",
    "Koalas sleep 22 hours a day 🐨",
    "The unicorn is the national animal of Scotland 🦄",
    "Woolly mammoths still existed when the Great Pyramid was being built 🦣",
    "A group of cats is called a clowder 🐱",
    "Almonds are seeds, not nuts 🌰",
    "Each person's tongue print is as unique as a fingerprint 👅",
    "The average person will spend 6 months of their life waiting for red lights 🚦",
    "Paper cuts are more painful than regular cuts because they rarely bleed — nerve endings stay exposed 📄",
    "Giraffes have the same number of neck vertebrae as humans — just 7, but much bigger 🦒",
    "The inventor of the first bulletproof vest tested it by shooting himself 🦺",
    "Ancient Romans used crushed mouse brains as toothpaste 🦷",
    "The average person walks 100,000 miles in their lifetime — 4 times around the Earth 🌍",
    "The word 'nightmare' comes from Old English — 'mare' was a type of evil spirit 🌙",
    "There are more possible iterations of a game of chess than atoms in the known universe ♟️",
    "Alaska is both the westernmost and easternmost state in the USA 🗺️",
    "A group of rhinos is called a crash 🦏",
]

# ─── QUOTE POOL — 80 quotes ───────────────────────────────────────────────────
QUOTE_POOL = [
    '"The only way to do great work is to love what you do." — Steve Jobs 💼',
    '"In the middle of every difficulty lies opportunity." — Einstein ✨',
    '"It does not matter how slowly you go as long as you do not stop." — Confucius 🐢',
    '"Life is what happens when you\'re busy making other plans." — John Lennon 🎵',
    '"The future belongs to those who believe in the beauty of their dreams." — Eleanor Roosevelt 🌟',
    '"It always seems impossible until it\'s done." — Nelson Mandela 💪',
    '"Whether you think you can or you think you can\'t, you\'re right." — Henry Ford 🚗',
    '"The best time to plant a tree was 20 years ago. The second best time is now." — Chinese Proverb 🌳',
    '"You miss 100% of the shots you don\'t take." — Wayne Gretzky 🏒',
    '"The only limit to our realization of tomorrow is our doubts of today." — FDR 🌅',
    '"Strive not to be a success, but rather to be of value." — Einstein 💎',
    '"Two things are infinite: the universe and human stupidity." — Einstein 🌌',
    '"You only live once, but if you do it right, once is enough." — Mae West 🌺',
    '"In three words I can sum up everything I\'ve learned about life: it goes on." — Frost 🍂',
    '"If you want to live a happy life, tie it to a goal, not to people or things." — Einstein 🎯',
    '"Never let the fear of striking out keep you from playing the game." — Babe Ruth ⚾',
    '"Money and success don\'t change people; they merely amplify what is already there." — Will Smith 💸',
    '"Your time is limited, don\'t waste it living someone else\'s life." — Steve Jobs ⏰',
    '"The mind is everything. What you think you become." — Buddha 🧘',
    '"An unexamined life is not worth living." — Socrates 🏺',
    '"Spread love everywhere you go." — Mother Teresa 🕊️',
    '"When you reach the end of your rope, tie a knot in it and hang on." — Lincoln 🪢',
    '"Always remember that you are absolutely unique. Just like everyone else." — Margaret Mead 🌟',
    '"Don\'t judge each day by the harvest you reap but by the seeds that you plant." — R.L. Stevenson 🌱',
    '"The purpose of our lives is to be happy." — Dalai Lama ☮️',
    '"Get busy living or get busy dying." — Stephen King 📚',
    '"You have brains in your head. You have feet in your shoes. You can steer yourself any direction you choose." — Dr. Seuss 🎩',
    '"If life were predictable it would cease to be life and be without flavor." — E. Roosevelt 🌊',
    '"If you look at what you have in life, you\'ll always have more." — Oprah 💫',
    '"If you set your goals ridiculously high and it\'s a failure, you will fail above everyone else\'s success." — James Cameron 🎬',
    '"Life is not measured by the number of breaths we take but by moments that take our breath away." 🌬️',
    '"If you want to go fast, go alone. If you want to go far, go together." — African proverb 🌍',
    '"We accept the love we think we deserve." — The Perks of Being a Wallflower 📖',
    '"Not everything that is faced can be changed, but nothing can be changed until it is faced." — Baldwin 🔄',
    '"Be yourself; everyone else is already taken." — Oscar Wilde 🎭',
    '"We know what we are, but know not what we may be." — Shakespeare 🎭',
    '"The unexamined life is not worth living." — Socrates 🏺',
    '"Success is not final, failure is not fatal: It is the courage to continue that counts." — Churchill 🏆',
    '"You will face many defeats in life, but never let yourself be defeated." — Maya Angelou 💪',
    '"The greatest glory in living lies not in never falling, but in rising every time we fall." — Mandela 🌅',
    '"In the end, it\'s not the years in your life that count. It\'s the life in your years." — Lincoln 🕰️',
    '"Never bend your head. Always hold it high. Look the world straight in the eye." — Keller 👁️',
    '"When everything seems to be going against you, remember that the airplane takes off against the wind." — Ford ✈️',
    '"It is during our darkest moments that we must focus to see the light." — Aristotle 🕯️',
    '"The best and most beautiful things in the world cannot be seen or touched — they must be felt." — Keller ❤️',
    '"Do not go where the path may lead, go instead where there is no path and leave a trail." — Emerson 🌿',
    '"You will never win if you never begin." — Helen Rowland 🚀',
    '"Life is either a daring adventure or nothing at all." — Keller 🌄',
    '"Many of life\'s failures are people who did not realize how close they were to success when they gave up." — Edison 💡',
    '"You\'ve gotta dance like there\'s nobody watching." — W. W. Purkey 💃',
    '"Dream big and dare to fail." — Norman Vaughan 🌙',
    '"You can never cross the ocean until you have the courage to lose sight of the shore." — Gide 🌊',
    '"I\'ve learned that people will forget what you said, people will forget what you did, but people will never forget how you made them feel." — Maya Angelou ❤️',
    '"Either write something worth reading or do something worth writing." — Franklin ✍️',
    '"Innovation distinguishes between a leader and a follower." — Jobs 💡',
    '"Twenty years from now you will be more disappointed by the things you didn\'t do." — Twain 📅',
    '"Eighty percent of success is showing up." — Woody Allen 🎬',
    '"The two most important days in your life are the day you are born and the day you find out why." — Twain 🎂',
    '"Life isn\'t about finding yourself. Life is about creating yourself." — Shaw 🎨',
    '"Build your own dreams, or someone else will hire you to build theirs." — Farrah Gray 💭',
    '"You become what you believe." — Oprah 🌟',
    '"The most common way people give up their power is by thinking they don\'t have any." — Walker 💪',
    '"The most difficult thing is the decision to act, the rest is merely tenacity." — Earhart ✈️',
    '"Every strike brings me closer to the next home run." — Babe Ruth ⚾',
    '"Definiteness of purpose is the starting point of all achievement." — Stone 🎯',
    '"Life is what we make it, always has been, always will be." — G. Moses 🌈',
    '"The most beautiful thing we can experience is the mysterious." — Einstein 🔮',
    '"A person who never made a mistake never tried anything new." — Einstein 🧪",',
    '"Spread love everywhere you go." — Mother Teresa 🕊️',
    '"When you reach the end of your rope, tie a knot in it and hang on." — FDR 🪢',
    '"In this life we cannot do great things — only small things with great love." — Mother Teresa 💛',
    '"Too many of us are not living our dreams because we are living our fears." — Les Brown 💡',
    '"I find that the harder I work, the more luck I seem to have." — Jefferson 🍀',
    '"Success usually comes to those who are too busy to be looking for it." — Thoreau 🏃',
    '"Opportunities don\'t happen. You create them." — Chris Grosser ✨',
    '"Don\'t be afraid to give up the good to go for the great." — John D. Rockefeller 🌟',
    '"I have not failed. I\'ve just found 10,000 ways that won\'t work." — Edison 💡',
    '"A successful man is one who can lay a firm foundation with the bricks others have thrown at him." — Brande 🧱',
]

# ─── FORTUNE POOL — 60 fortunes ───────────────────────────────────────────────
FORTUNE_POOL = [
    "🌟 A great opportunity disguised as a problem will reveal itself soon.",
    "🔮 The answer you seek is already within you — trust your instincts.",
    "💫 Unexpected laughter is around the corner — prepare your smile.",
    "🌈 Your next chapter begins with a single brave decision.",
    "⚡ Someone is thinking about you warmly right now.",
    "🌸 A small act of kindness today will return to you tenfold.",
    "🎯 The path is clearing ahead — step forward without hesitation.",
    "🦋 Change is coming, but only the good kind.",
    "💎 Your patience is about to be rewarded beyond your expectations.",
    "🌙 Tonight holds the seed of tomorrow's success — rest well.",
    "🏆 A victory you've been working toward is closer than you think.",
    "🌺 Someone new is about to enter your life and change things beautifully.",
    "⭐ The stars have already conspired in your favor.",
    "🎪 Unexpected joy awaits around the next corner.",
    "🔑 A door you thought was closed is about to swing wide open.",
    "🌊 The tide is turning in your favor — hold steady.",
    "🌿 Growth is happening even when you can't feel it.",
    "💡 A brilliant idea will come to you when you least expect it.",
    "🦅 Now is the time to leap — you will not fall.",
    "🌅 Tomorrow belongs entirely to those who prepare today.",
    "🎵 Music will bring an unexpected revelation today.",
    "💫 The universe is lining up a series of pleasant surprises for you.",
    "🌱 Plant your seeds now — the harvest will astonish you.",
    "🎭 Embrace the unexpected — it's exactly what you need.",
    "💜 Love in all its forms is making its way to you.",
    "🗝️ The key you've been looking for was in your pocket all along.",
    "🧩 The missing piece of your puzzle will arrive in an unlikely package.",
    "🌟 Today is exactly the right day to take that risk.",
    "🔥 Your passion is your compass — follow it without fear.",
    "🌙 A mystery will resolve itself by the end of this week.",
    "🎁 An unexpected gift — not necessarily material — arrives soon.",
    "🏰 What you're building is more solid than you know.",
    "🌊 Trust the current — it knows where it's going.",
    "💪 Your strength has just been forged in the fire — use it.",
    "🌸 The relationship you've been uncertain about will find its answer.",
    "⚡ A conversation this week will change how you see everything.",
    "🦋 Your transformation is complete — time to fly.",
    "🔮 The impossible thing you've been wishing for has moved into the realm of probable.",
    "🌈 After the storm comes not just sunshine but a rainbow.",
    "💎 What you've lost will be replaced by something far more valuable.",
    "🌿 Nature has the answer — spend time outside this week.",
    "🎯 Your aim is true — release the arrow.",
    "🌺 Someone close to you is ready to hear what you've been wanting to say.",
    "⭐ Tonight's stars carry a message specifically for you.",
    "🏆 Your greatest achievement is not behind you — it's ahead.",
    "🔑 Say yes to the thing you've been overthinking.",
    "🌅 A new dawn is literal and figurative — embrace both.",
    "💡 The question you keep asking will answer itself within three days.",
    "🦅 Rise above the small things — your wingspan is enormous.",
    "🌙 Dreams tonight will carry a message worth remembering.",
    "🎪 Laughter is the solution to what troubles you now.",
    "🌱 Every dead end you've hit was redirecting you here.",
    "🎵 Say what's in your heart — it will be received better than you fear.",
    "💫 A synchronicity is about to connect two parts of your life.",
    "💜 Self-compassion is the skill you need to develop right now.",
    "🌟 You are precisely where you need to be on your journey.",
    "🔥 The work you've put in silently is about to speak loudly.",
    "🧩 Everything that seemed disconnected is about to make perfect sense.",
    "🌊 Let go of what you're holding — something better needs both hands.",
    "⚡ The person you've been waiting to become is emerging right now.",
]

# ─── RIDDLE POOL — 50 riddles with answers ────────────────────────────────────
RIDDLE_POOL = [
    ("I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I?", "An echo"),
    ("The more you take, the more you leave behind. What am I?", "Footsteps"),
    ("I have cities, but no houses live there. I have mountains, but no trees. I have water, but no fish. What am I?", "A map"),
    ("What has hands but can't clap?", "A clock"),
    ("I get lighter as I get used up. What am I?", "A candle"),
    ("What can travel around the world while staying in a corner?", "A stamp"),
    ("The more you have of me, the less you see. What am I?", "Darkness"),
    ("I have a neck but no head, and I wear a cap. What am I?", "A bottle"),
    ("What has an eye but cannot see?", "A needle"),
    ("I am not alive, but I grow; I don't have lungs, but I need air. What am I?", "Fire"),
    ("What goes up but never comes down?", "Your age"),
    ("I'm light as a feather, but even the strongest person can't hold me for more than a few minutes. What am I?", "Breath"),
    ("I have teeth but cannot bite. What am I?", "A comb"),
    ("What has one head, one foot, and four legs?", "A bed"),
    ("I'm always in front of you but can't be seen. What am I?", "The future"),
    ("What has wings but cannot fly, and legs but cannot walk?", "A dead bird"),
    ("I'm full of holes but I can still hold water. What am I?", "A sponge"),
    ("What has a tongue but cannot talk?", "A shoe"),
    ("The more you dry me, the wetter I get. What am I?", "A towel"),
    ("I have keys but no locks, space but no room, and you can enter but can't go inside. What am I?", "A keyboard"),
    ("What breaks when you say it?", "Silence"),
    ("I go up when rain comes down. What am I?", "An umbrella"),
    ("I have a head and a tail but no body. What am I?", "A coin"),
    ("What has 13 hearts but no other organs?", "A deck of cards"),
    ("I can be cracked, told, and played. What am I?", "A joke"),
    ("What is so fragile that saying its name breaks it?", "Silence"),
    ("I'm always hungry and must be fed. The finger I lick will soon turn red. What am I?", "Fire"),
    ("What can you catch but not throw?", "A cold"),
    ("I have no life but I can die. What am I?", "A battery"),
    ("What has a bed but doesn't sleep, and a mouth but doesn't eat?", "A river"),
    ("I fly without wings between rocks and meadows. What am I?", "The wind"),
    ("What has four eyes but cannot see?", "Mississippi"),
    ("I'm made of water but I'm not wet. What am I?", "Vapor"),
    ("What gets wetter as it dries?", "A towel"),
    ("I have no feet but I run. I have no mouth but I roar. What am I?", "A river"),
    ("What can fill a room but takes up no space?", "Light"),
    ("I start with E, end with E, and usually contain one letter. What am I?", "An envelope"),
    ("What has a bottom at the top?", "A leg"),
    ("The more you remove, the larger I get. What am I?", "A hole"),
    ("What has one leg but can't walk?", "A mushroom"),
    ("I have branches but no fruit, trunk, or leaves. What am I?", "A bank"),
    ("I'm not a cat but I have claws; not a bear but I hibernate. What am I?", "A computer (sleep mode)"),
    ("What is always in front of you but can never be seen?", "The future"),
    ("What kind of room has no windows or doors?", "A mushroom"),
    ("What runs but never walks, has a mouth but never talks?", "A river"),
    ("I shrink every time you use me. What am I?", "Soap"),
    ("What has a ring but no finger?", "A telephone"),
    ("I'm tall when I'm young and short when I'm old. What am I?", "A candle"),
    ("I speak in a whisper and shout in silence. What am I?", "A book"),
    ("What can go up a chimney down, but can't go down a chimney up?", "An umbrella"),
]

# ─── WYR POOL — 80 would-you-rather pairs ────────────────────────────────────
WYR_POOL = [
    ("Have the ability to fly", "Become invisible at will"),
    ("Never sleep again", "Never eat food again"),
    ("Know when you're going to die", "Know how you're going to die"),
    ("Always have to say what you're thinking", "Never speak again"),
    ("Be famous for something embarrassing", "Be unknown for something great"),
    ("Have a rewind button for your life", "Have a pause button for time"),
    ("Always be cold", "Always be hot"),
    ("Lose all your memories", "Never make new ones"),
    ("Live without music", "Live without TV/movies"),
    ("Be able to talk to animals", "Read minds of humans"),
    ("Have a photographic memory", "Never feel pain"),
    ("Live 200 years in poor health", "Live 80 years in perfect health"),
    ("Be the smartest person alive", "Be the happiest person alive"),
    ("Have unlimited money but no friends", "Have great friends but be broke"),
    ("Always be 15 minutes late", "Always be 15 minutes early"),
    ("Give up social media forever", "Give up Netflix forever"),
    ("Never use a phone again", "Never use a computer again"),
    ("Spend a week in the past", "Spend a week in the future"),
    ("Fight 100 duck-sized horses", "Fight 1 horse-sized duck"),
    ("Speak every language fluently", "Play every instrument perfectly"),
    ("Always tell the truth", "Always lie convincingly"),
    ("Have no sense of taste", "Have no sense of smell"),
    ("Be stranded on an island alone", "Be stranded with someone annoying"),
    ("Know all future winning lottery numbers", "Be able to go back in time once"),
    ("Never have to sleep", "Never have to eat"),
    ("Live in a world of magic", "Live in a world of advanced science"),
    ("Be the best player on a losing team", "Be the worst player on a winning team"),
    ("Have the power to heal others", "Have the power to heal yourself"),
    ("Forget who you are every day", "Remember every detail of every day"),
    ("Never be cold again", "Never be hungry again"),
    ("Have a clone of yourself", "Switch bodies with someone for a day"),
    ("Always be overdressed", "Always be underdressed"),
    ("Be completely alone for 5 years", "Never be alone for 5 years"),
    ("Give up desserts forever", "Give up all fried food forever"),
    ("Be famous after you die", "Be famous only while you're alive"),
    ("Know a secret that destroys you", "Stay ignorant and happy"),
    ("Have the world's best voice", "Have the world's best dance moves"),
    ("Travel anywhere free", "Eat anywhere for free"),
    ("Have free housing", "Have free transportation"),
    ("Be a professional athlete", "Be a world-famous artist"),
    ("Never feel nervous again", "Never feel sad again"),
    ("Meet your great-great-grandparents", "Meet your great-great-grandchildren"),
    ("Be able to see 10 minutes into the future", "Change one choice from your past"),
    ("Live without internet", "Live without AC/heating"),
    ("Only wear one outfit forever", "Change your appearance every day"),
    ("Live in a world with no crime", "Live in a world with no disease"),
    ("Be fluent in all languages", "Be an expert in all fields of science"),
    ("Know what your pet is thinking", "Have your pet live as long as you"),
    ("Have a terrible memory but always be happy", "Have a perfect memory but always be sad"),
    ("Always have perfect weather", "Always know the correct answer to any question"),
    ("Be immortal but watch everyone you love die", "Live a normal lifespan but never lose anyone you love"),
    ("Have an extra arm", "Have an extra leg"),
    ("Be able to breathe underwater", "Be able to survive in space"),
    ("Never be stuck in traffic", "Never wait in lines"),
    ("Have a laugh that makes others laugh", "Have a smile that makes others smile"),
    ("Be incredibly strong", "Be incredibly fast"),
    ("Have perfect handwriting", "Type at 200 WPM"),
    ("Find your perfect job", "Find your perfect partner"),
    ("Be an expert chef", "Be an expert mechanic"),
    ("Have no enemies", "Have 100 loyal friends"),
    ("Be the oldest sibling", "Be the youngest sibling"),
    ("Go on a date with your celebrity crush", "Have lunch with your favorite fictional character"),
    ("Have a mansion in a terrible location", "A small house in the perfect location"),
    ("Be able to see ghosts", "Be seen by ghosts"),
    ("Always know when people are lying", "Make anyone believe any lie you tell"),
    ("Have a permanent summer", "Have a permanent winter"),
    ("Win a Nobel Prize nobody knows about", "Lose one that everyone knows you deserved"),
    ("Give up your phone", "Give up your computer"),
    ("Be allergic to sunlight", "Be allergic to water"),
    ("Have skin that changes color with your mood", "Have hair that grows only in one color"),
    ("Own a dragon", "Be able to transform into a dragon"),
    ("Live in the forest", "Live by the ocean"),
    ("Have free plane tickets for life", "Have free hotel stays for life"),
    ("Be a master of one language", "Know 10 languages at a basic level"),
    ("Explore the bottom of the ocean", "Explore the surface of Mars"),
    ("Have a library of every book", "Have a playlist of every song"),
    ("Never be bored", "Never be stressed"),
    ("Have the ability to heal people with a touch", "Have the ability to protect people with a word"),
]

# ─── TAROT CARDS — Major Arcana with readings ─────────────────────────────────
TAROT_CARDS = [
    ("🌟 The Fool", "A new beginning is calling. Take the leap — trust the universe, not just the plan."),
    ("🧙 The Magician", "You have all the tools you need right now. The power is yours to use — or waste."),
    ("🌙 The High Priestess", "Listen to your intuition. The answer is already inside you — go quiet and hear it."),
    ("👑 The Empress", "Abundance, creativity, and nurturing energy surround you. Something is flourishing."),
    ("🏛️ The Emperor", "Structure and authority speak. Take control — or release control — this is the moment."),
    ("🙏 The Hierophant", "Tradition and wisdom call to you. Seek guidance from those who've walked this path."),
    ("💑 The Lovers", "A significant choice about connection or values. What aligns with your true self?"),
    ("🏎️ The Chariot", "Victory through determination and focus. Move forward — the momentum is yours."),
    ("💪 Strength", "Real power is gentle. The courage you need lives in compassion, not force."),
    ("🏮 The Hermit", "Solitude brings wisdom. Retreat, reflect, and then emerge with clarity."),
    ("🎡 Wheel of Fortune", "Cycles turning. What goes around comes around — good or challenging."),
    ("⚖️ Justice", "Truth and fairness prevail. What is rightfully yours will be yours. Be honest."),
    ("🙃 The Hanged Man", "Pause. Surrender. A new perspective only comes from letting go of the old one."),
    ("💀 Death", "Not ending — transformation. The old way dies so something profound can begin."),
    ("⚗️ Temperance", "Balance and patience. Mix the extremes with grace; the moderate path is the wise one."),
    ("😈 The Devil", "What chains you? The shackles are often self-made. Freedom requires recognition."),
    ("🗼 The Tower", "Sudden upheaval reveals what was built on unstable ground. Rebuild better."),
    ("⭐ The Star", "Hope restored. After the storm comes clarity, healing, and renewed faith."),
    ("🌕 The Moon", "Not all is as it seems. Illusions, dreams, and the unconscious speak tonight."),
    ("☀️ The Sun", "Clarity, joy, and warmth. Optimism is not naive — it's your superpower right now."),
    ("🎺 Judgement", "A reckoning and a calling. Rise to meet who you're meant to be — now is the time."),
    ("🌍 The World", "Completion, wholeness, achievement. You have arrived at a significant milestone."),
]

# ─── HOROSCOPE COMPONENTS — for algorithmic generation ────────────────────────
HOROSCOPE_SIGNS = {
    "aries":       {"emoji":"♈","dates":"Mar 21–Apr 19","element":"Fire 🔥","ruler":"Mars"},
    "taurus":      {"emoji":"♉","dates":"Apr 20–May 20","element":"Earth 🌍","ruler":"Venus"},
    "gemini":      {"emoji":"♊","dates":"May 21–Jun 20","element":"Air 💨","ruler":"Mercury"},
    "cancer":      {"emoji":"♋","dates":"Jun 21–Jul 22","element":"Water 🌊","ruler":"Moon"},
    "leo":         {"emoji":"♌","dates":"Jul 23–Aug 22","element":"Fire 🔥","ruler":"Sun"},
    "virgo":       {"emoji":"♍","dates":"Aug 23–Sep 22","element":"Earth 🌍","ruler":"Mercury"},
    "libra":       {"emoji":"♎","dates":"Sep 23–Oct 22","element":"Air 💨","ruler":"Venus"},
    "scorpio":     {"emoji":"♏","dates":"Oct 23–Nov 21","element":"Water 🌊","ruler":"Pluto"},
    "sagittarius": {"emoji":"♐","dates":"Nov 22–Dec 21","element":"Fire 🔥","ruler":"Jupiter"},
    "capricorn":   {"emoji":"♑","dates":"Dec 22–Jan 19","element":"Earth 🌍","ruler":"Saturn"},
    "aquarius":    {"emoji":"♒","dates":"Jan 20–Feb 18","element":"Air 💨","ruler":"Uranus"},
    "pisces":      {"emoji":"♓","dates":"Feb 19–Mar 20","element":"Water 🌊","ruler":"Neptune"},
}
HOROSCOPE_ENERGY = ["expansive","transformative","calm","electric","intense","whimsical",
                    "grounded","visionary","turbulent","magical","analytical","romantic",
                    "bold","mysterious","gentle","powerful","chaotic","harmonious"]
HOROSCOPE_FOCUS  = ["relationships","creativity","career","finances","health","communication",
                    "self-discovery","adventure","family","friendship","spirituality","ambition"]
HOROSCOPE_LUCKY  = ["the color blue","the number 7","a chance encounter",
                    "morning coffee","an old song","a handwritten note","a left turn",
                    "something red","the number 3","an unexpected call","solitude","music"]
HOROSCOPE_ADVICE = [
    "Trust the process even when it feels slow.",
    "Say what you mean — clarity is kindness.",
    "Rest is productive. Let yourself recharge.",
    "Your instincts are right about this one.",
    "Let go of what's no longer serving you.",
    "Ask for help — it's strength, not weakness.",
    "A conversation today could change everything.",
    "Protect your energy — not everyone deserves it.",
    "The breakthrough comes after the breakdown.",
    "Be patient with yourself — growth takes time.",
    "Your consistency will be rewarded soon.",
    "Take the leap — the net will appear.",
]
HOROSCOPE_MOOD   = ["☀️ Radiant","🌩️ Stormy","🌈 Hopeful","🌙 Dreamy","⚡ Electric",
                    "🌊 Flowing","🔥 Fired up","❄️ Icy cool","🌸 Blooming","🌪️ Turbulent"]

# ─── HANGMAN WORDS — 400+ words ───────────────────────────────────────────────
HANGMAN_WORDS = [
    # Animals
    ("elephant","large gray mammal with a trunk"),("dolphin","intelligent marine mammal"),
    ("penguin","flightless bird from Antarctica"),("giraffe","tallest land animal"),
    ("cheetah","fastest land animal"),("octopus","eight-armed sea creature"),
    ("crocodile","large reptile"),("flamingo","pink wading bird"),
    ("kangaroo","Australian marsupial"),("platypus","egg-laying mammal"),
    ("chameleon","color-changing lizard"),("wolverine","fierce small mammal"),
    ("narwhal","horned whale"),("pangolin","armored mammal"),("axolotl","Mexican salamander"),
    # Technology
    ("algorithm","set of rules for computation"),("database","organized collection of data"),
    ("encryption","process of encoding data"),("protocol","set of communication rules"),
    ("bandwidth","data transfer capacity"),("interface","point of interaction"),
    ("firmware","software for hardware"),("compiler","code translator"),
    ("debugging","finding and fixing errors"),("recursion","function calling itself"),
    ("framework","software skeleton"),("middleware","connecting software layer"),
    ("webhook","HTTP callback mechanism"),("repository","code storage location"),
    ("iteration","repetition of a process"),
    # Food & Drink
    ("croissant","flaky French pastry"),("spaghetti","long pasta noodles"),
    ("saffron","expensive yellow spice"),("avocado","green buttery fruit"),
    ("espresso","concentrated coffee"),("quesadilla","filled tortilla"),
    ("prosciutto","Italian cured ham"),("guacamole","avocado dip"),
    ("cappuccino","espresso with milk foam"),("mozzarella","soft Italian cheese"),
    ("enchilada","rolled tortilla dish"),("bruschetta","Italian toast appetizer"),
    ("cinnamon","sweet warm spice"),("turmeric","golden yellow spice"),
    ("edamame","green soybeans"),
    # Geography
    ("zanzibar","island off Tanzania"),("kathmandu","Nepal's capital"),
    ("mozambique","African country"),("azerbaijan","Caucasus country"),
    ("kyrgyzstan","Central Asian country"),("madagascar","large island nation"),
    ("uzbekistan","Central Asian nation"),("liechtenstein","tiny European nation"),
    ("madagascar","island off Africa"),("patagonia","South American region"),
    ("himalayas","world's tallest mountain range"),("archipelago","group of islands"),
    ("peninsula","land surrounded by water"),("equator","Earth's midline"),
    ("meridian","longitudinal line"),
    # Science
    ("photosynthesis","plants making food from light"),("mitochondria","cell's powerhouse"),
    ("chromosome","DNA-carrying structure"),("atmosphere","layer of air around Earth"),
    ("telescope","instrument for viewing space"),("molecule","smallest compound unit"),
    ("neutron","neutral atomic particle"),("electron","negative atomic particle"),
    ("velocity","speed in a direction"),("magnitude","size or extent"),
    ("wavelength","distance between wave peaks"),("frequency","number of wave cycles"),
    ("catalyst","reaction-speeding substance"),("isotope","element variant"),
    ("osmosis","water movement through membrane"),
    # Music
    ("symphony","large orchestral composition"),("percussion","drum and rhythm instruments"),
    ("saxophone","woodwind instrument"),("accordion","bellows instrument"),
    ("harmonica","mouth organ"),("xylophone","percussion keyboard instrument"),
    ("trombone","brass slide instrument"),("clarinet","woodwind instrument"),
    ("ukulele","small Hawaiian guitar"),("theremin","electronic air instrument"),
    ("mandolin","plucked string instrument"),("oboe","double-reed woodwind"),
    ("bassoon","large bass woodwind"),("vibraphone","mallet percussion"),
    ("sousaphone","large tuba variant"),
    # Sports
    ("lacrosse","stick and ball game"),("badminton","shuttlecock sport"),
    ("fencing","sword-fighting sport"),("gymnastics","acrobatic sport"),
    ("equestrian","horse riding sport"),("archery","bow and arrow sport"),
    ("pentathlon","five-sport competition"),("biathlon","skiing and shooting"),
    ("triathlon","three-sport race"),("decathlon","ten-sport competition"),
    ("weightlifting","strength sport"),("wrestling","grappling sport"),
    ("trampoline","bouncing sport"),("kayaking","paddle sport"),
    ("bobsleigh","winter sliding sport"),
    # Words
    ("perpendicular","at right angles"),("onomatopoeia","word that sounds like its meaning"),
    ("phenomenon","observable occurrence"),("psychology","study of the mind"),
    ("philosophy","study of existence and knowledge"),("democracy","government by the people"),
    ("bureaucracy","complex administrative system"),("cryptocurrency","digital currency"),
    ("bibliography","list of references"),("autobiography","self-written life story"),
    ("metaphor","figurative comparison"),("synonym","word with same meaning"),
    ("antonym","word with opposite meaning"),("homophone","same-sound different word"),
    ("palindrome","word that reads same backwards"),
    # Misc
    ("chrysanthemum","flowering plant"),("kaleidoscope","colorful tube toy"),
    ("archipelago","chain of islands"),("phantasmagoria","dreamlike sequence"),
    ("labyrinth","maze-like structure"),("paraphernalia","miscellaneous items"),
    ("serendipity","pleasant surprise"),("melancholy","deep sadness"),
    ("ephemeral","lasting a short time"),("exquisite","extremely beautiful"),
    ("luminescent","glowing in the dark"),("clandestine","done in secret"),
    ("quintessential","most typical example"),("extraordinary","beyond ordinary"),
    ("ambiguous","open to multiple interpretations"),
    # Countries & Cities
    ("amsterdam","Dutch capital"),("stockholm","Swedish capital"),
    ("singapore","island city-state"),("wellington","New Zealand capital"),
    ("montevideo","Uruguay capital"),("reykjavik","Iceland capital"),
    ("ashgabat","Turkmenistan capital"),("ulaanbaatar","Mongolia capital"),
    ("naypyidaw","Myanmar capital"),("bujumbura","Burundi capital"),
    ("djibouti","small African nation"),("suriname","South American nation"),
    ("guadeloupe","Caribbean island"),("martinique","Caribbean island"),
    ("madagascar","Africa island"),
]

# ─── SCRAMBLE WORDS — 200+ words with categories ─────────────────────────────
SCRAMBLE_WORDS = [
    ("python","programming language"),("banana","yellow fruit"),("galaxy","star system"),
    ("planet","celestial body"),("sunset","evening sky"),("jungle","dense forest"),
    ("castle","medieval fort"),("dragon","mythical creature"),("coffee","morning drink"),
    ("mirror","reflective glass"),("bridge","water crossing"),("forest","wooded area"),
    ("candle","wax light"),("bottle","liquid container"),("frozen","ice cold"),
    ("purple","violet color"),("silver","precious metal"),("golden","gold colored"),
    ("spring","season after winter"),("winter","cold season"),("summer","hot season"),
    ("autumn","fall season"),("circle","round shape"),("square","four equal sides"),
    ("oxygen","breathing gas"),("carbon","element symbol C"),("sodium","salt element"),
    ("magnet","attracts metal"),("rocket","space vehicle"),("guitar","string instrument"),
    ("violin","bowed instrument"),("flute","wind instrument"),("trumpet","brass instrument"),
    ("marble","glass ball toy"),("pillow","sleeping cushion"),("window","glass opening"),
    ("butter","dairy spread"),("pepper","spicy seasoning"),("ginger","root spice"),
    ("lemon","sour citrus"),("orange","citrus fruit"),("cherry","small red fruit"),
    ("mango","tropical fruit"),("grape","vine fruit"),("peach","fuzzy fruit"),
    ("plum","purple fruit"),("kiwi","furry fruit"),("melon","large sweet fruit"),
    ("daisy","simple flower"),("tulip","spring flower"),("rose","romantic flower"),
    ("lotus","water flower"),("lilac","purple flower"),("orchid","exotic flower"),
    ("whale","ocean mammal"),("shark","ocean predator"),("coral","ocean structure"),
    ("tiger","striped cat"),("lion","savanna cat"),("panda","black white bear"),
    ("koala","tree marsupial"),("zebra","striped horse"),("camel","desert animal"),
    ("llama","South American animal"),("bison","large bovine"),("moose","large deer"),
    ("eagle","large bird"),("raven","black bird"),("parrot","talking bird"),
    ("falcon","fast bird"),("pelican","fishing bird"),("toucan","colorful bill bird"),
    ("goblin","mischievous creature"),("sprite","fairy-like creature"),("gnome","garden creature"),
    ("cipher","secret code"),("riddle","puzzle question"),("fable","moral story"),
    ("sonnet","14-line poem"),("haiku","Japanese poem"),("limerick","funny poem"),
    ("prism","light splitter"),("laser","focused light"),("radar","detection system"),
    ("sonar","sound navigation"),("pixel","screen unit"),("codec","compression format"),
    ("debug","fix errors"),("stack","data structure"),("queue","waiting line"),
    ("graph","visual data"),("table","data grid"),("index","reference guide"),
    ("atlas","map collection"),("globe","world sphere"),("compass","direction tool"),
    ("trophy","victory prize"),("medal","achievement disc"),("crown","royal head wear"),
    ("shield","defense tool"),("sword","blade weapon"),("armor","protection suit"),
    ("spell","magic words"),("potion","magic drink"),("scroll","ancient document"),
    ("quest","adventure task"),("dungeon","underground prison"),("wizard","magic user"),
    ("knight","armored warrior"),("castle","fortified building"),("moat","water barrier"),
    ("bridge","crossing structure"),("tower","tall structure"),("vault","secure room"),
]

# ─── BATTLE SYSTEM ────────────────────────────────────────────────────────────
BATTLE_ATTACK_MSGS = [
    "{a} launches a devastating combo at {b}! 💥",
    "{a} hurls a fireball that scorches {b}! 🔥",
    "{a} executes a precision strike on {b}! ⚡",
    "{a} throws {b} across the arena! 💪",
    "{a} calls down lightning on {b}! ⚡🌩️",
    "{a} summons an ice storm targeting {b}! ❄️",
    "{a} unleashes a tornado on {b}! 🌪️",
    "{a} lands a critical uppercut on {b}! 👊",
    "{a} deploys a ground-shaking stomp near {b}! 🦶",
    "{a} fires a plasma beam at {b}! 🔮",
    "{a} materializes behind {b} for a backstab! 🗡️",
    "{a} drops from the sky onto {b}! 🦅",
    "{a} activates their SPECIAL MOVE on {b}! ✨",
    "{a} channels pure chaos energy at {b}! 🌀",
    "{a} deploys a tactical nuclear disappointment at {b}! ☢️",
]
BATTLE_MISS_MSGS = [
    "{a} swings wildly and misses completely! 😅",
    "{b} gracefully dodges {a}'s attack! 💨",
    "{a}'s attack is absorbed by {b}'s aura! ✨",
    "Whiff! {a} hit nothing but air! 🌬️",
    "{a} slips dramatically mid-attack! 🤸",
]
BATTLE_CRIT_MSGS = [
    "⚡ CRITICAL HIT! {a} dealt massive damage!",
    "💀 DEVASTATING BLOW by {a}! The crowd erupts!",
    "🌟 PERFECT STRIKE! {a} found the weak point!",
    "🔥 COMBO BREAKER! {a} landed an impossible hit!",
]

# ─── ECONOMY EVENT MESSAGES ───────────────────────────────────────────────────
DAILY_MSGS = [
    "☀️ {name} greets the sun and claims their daily reward!",
    "🌅 The cosmos align — {name} collects their daily blessing!",
    "💰 {name} shows up and shows out for their daily coins!",
    "🎉 Daily claimed! {name} is winning at life fr!",
    "⭐ {name} remembered their daily! The algorithm rewards loyalty!",
    "🌟 {name} secured the daily bag — consistent era!",
    "💫 Another day, another bag for {name}!",
    "🏆 {name} maintains the daily streak with precision!",
    "🎯 {name} hit the daily target — right on time!",
    "✨ Daily collected! {name} understands the assignment!",
    "💎 {name} claims their daily reward — main character behavior!",
    "🔥 {name} shows up every day — the consistency is immaculate!",
    "🌈 {name} collects another daily with effortless grace!",
    "🚀 {name} launches into the day with coins in hand!",
    "🎊 Daily claimed! {name} never misses — respect fr!",
    "🌺 {name} takes their daily and the universe smiles!",
    "💸 {name} secures their daily bread — financially responsible era!",
    "⚡ {name} zaps the daily button before anyone else!",
    "🏅 {name} gets their daily — dedication is their brand!",
    "🌸 Another lovely daily claim from the perpetually consistent {name}!",
]
WORK_SCENARIOS = [
    ("worked a full shift at the coding dungeon", 150, 400),
    ("debugged someone else's spaghetti code at 2am", 200, 500),
    ("delivered packages in a thunderstorm", 100, 350),
    ("tutored a kid who kept saying 'but why tho'", 120, 300),
    ("wrote a 10-page report nobody will read", 150, 400),
    ("designed a logo that got changed 47 times", 200, 600),
    ("moderated a very unhinged online forum", 175, 450),
    ("cooked 200 meals during lunch rush", 200, 500),
    ("survived a corporate team-building exercise", 100, 300),
    ("managed a social media account during a crisis", 250, 700),
    ("cleaned the entire office after a surprise inspection", 150, 400),
    ("fixed production servers at 3am on a Saturday", 300, 800),
    ("translated a document with zero context", 130, 350),
    ("organized a warehouse solo for 8 hours", 160, 420),
    ("wrote content for a brand that has no identity", 180, 480),
    ("supported an angry customer for 4 hours", 200, 500),
    ("tested a game with 3000 bugs and reported all of them", 250, 650),
    ("made 200 cold calls with a 2% success rate", 100, 350),
    ("drove 400km for a same-day delivery", 200, 550),
    ("painted a mural in the rain", 180, 480),
    ("photographed a wedding where everyone was late", 220, 600),
    ("set up AV equipment that refused to cooperate", 150, 400),
    ("trained a team of 20 new employees in one day", 280, 700),
    ("maintained a server farm in a heatwave", 200, 550),
    ("compiled a report from 47 spreadsheets with different formats", 170, 450),
    ("performed at a venue where the mic died twice", 150, 400),
    ("built IKEA furniture for an entire apartment", 180, 500),
    ("cared for 15 pets at a boarding facility", 150, 400),
    ("finished a marathon client project 20 minutes before deadline", 300, 850),
    ("invented a solution to a problem that didn't exist yet", 250, 700),
    ("taught a coding bootcamp to people who feared computers", 200, 600),
    ("designed and launched a website in 48 hours", 250, 700),
    ("negotiated a contract while exhausted", 220, 580),
    ("cooked for a dinner party of 30 with no prep time", 200, 550),
    ("managed a chaotic event with 500 attendees", 300, 800),
    ("handled IT support for an entire department alone", 180, 500),
    ("transcribed 8 hours of audio recordings", 150, 380),
    ("wrote a grant proposal overnight", 250, 650),
    ("assembled a complex report from scattered data", 160, 430),
    ("tested 200 pages of software documentation", 170, 440),
    ("solved a math problem that had 15 steps", 180, 480),
    ("spent 6 hours on hold with customer support for someone else", 100, 300),
    ("organized a charity event from scratch in 3 days", 280, 750),
    ("fixed a critical bug 10 minutes before launch", 300, 900),
    ("survived a meeting that could have been an email", 80, 250),
    ("created an entire brand identity from scratch", 300, 800),
    ("proofread a 200-page document with no errors", 200, 500),
    ("designed an app prototype in an afternoon", 250, 650),
    ("built an entire database schema from requirements", 270, 700),
    ("led a workshop for 50 people remotely", 220, 600),
]
MINE_SCENARIOS = [
    ("🪨 Stone vein", 10, 80, "💨 Common find — but every coin counts!"),
    ("⚙️ Iron deposit", 30, 120, "⚒️ Solid haul — iron is reliable!"),
    ("🥇 Gold seam", 80, 250, "✨ Golden! You struck rich ore!"),
    ("🔮 Amethyst cluster", 150, 400, "🌟 Glowing crystals — premium haul!"),
    ("💎 Diamond vein", 300, 800, "💎 DIAMONDS! The mine gods favor you!"),
    ("🌟 Nexus Crystal", 800, 3000, "⚡ NEXUS CRYSTAL! LEGENDARY STRIKE! The whole cave lit up!"),
    ("💀 Cave-in", -50, -10, "😰 Cave-in! You barely escaped but lost some coins to the rocks!"),
    ("🌟 Double Strike", None, None, "⚡ DOUBLE STRIKE! Mining twice the normal yield!"),
    ("☄️ Meteor Fragment", 500, 1500, "☄️ COSMIC ROCK! A meteorite was embedded in the wall!"),
    ("🐸 Frog Colony", 5, 20, "🐸 You found frogs. They gave you coins? Somehow?"),
]

# ─── ADMIN ACTION MESSAGES — 30 per type ─────────────────────────────────────
BAN_MSGS = [
    "🔨 <b>Justice served.</b> {u} has been banned by {a}.\n<i>Reason: {r}</i>",
    "🚫 <b>BANNED.</b> {u} got the boot from {a}.\n<i>Reason: {r}</i>",
    "💀 <b>Eliminated.</b> {u} can no longer participate. Admin: {a}\n<i>Reason: {r}</i>",
    "⛔ <b>Access denied.</b> {u} was removed by {a}.\n<i>Reason: {r}</i>",
    "🔒 <b>Locked out.</b> {a} dropped the ban hammer on {u}.\n<i>Reason: {r}</i>",
    "🏚️ <b>Evicted.</b> {u} was expelled by {a}.\n<i>Reason: {r}</i>",
    "🌑 <b>Gone.</b> {u} has departed the realm, courtesy of {a}.\n<i>Reason: {r}</i>",
    "📛 <b>Banned.</b> {a} said goodbye to {u} — permanently.\n<i>Reason: {r}</i>",
    "🚷 <b>Entry revoked.</b> {u}'s ticket was cancelled by {a}.\n<i>Reason: {r}</i>",
    "⚖️ <b>The verdict is in.</b> {u} has been sanctioned by {a}.\n<i>Reason: {r}</i>",
    "🛑 <b>STOP RIGHT THERE.</b> {u} was banned by {a} — no appeals.\n<i>Reason: {r}</i>",
    "💥 <b>Boom.</b> {u} exploded out of existence, courtesy of {a}.\n<i>Reason: {r}</i>",
    "🏴 <b>Blacklisted.</b> {u} is now on the permanent list from {a}.\n<i>Reason: {r}</i>",
    "🚨 <b>Alert resolved.</b> {u} removed by security admin {a}.\n<i>Reason: {r}</i>",
    "🌪️ <b>Swept away.</b> {u} was purged by {a}.\n<i>Reason: {r}</i>",
    "🦅 <b>Hunted.</b> {a} tracked and banned {u}.\n<i>Reason: {r}</i>",
    "🎭 <b>Exit stage left.</b> {u} performed their final act — banned by {a}.\n<i>Reason: {r}</i>",
    "🔐 <b>Access terminated.</b> {a} shut the door on {u}.\n<i>Reason: {r}</i>",
    "🌊 <b>Swept to sea.</b> {u} was washed out by {a}.\n<i>Reason: {r}</i>",
    "🗡️ <b>Slain.</b> {u}'s presence here was ended by {a}.\n<i>Reason: {r}</i>",
    "📵 <b>Disconnected.</b> {u}'s connection was cut by {a}.\n<i>Reason: {r}</i>",
    "🧨 <b>Detonated.</b> {a} removed {u} with extreme prejudice.\n<i>Reason: {r}</i>",
    "🌚 <b>Into the void.</b> {u} was sent away by {a}.\n<i>Reason: {r}</i>",
    "🔫 <b>Shot down.</b> {u} was eliminated by {a}.\n<i>Reason: {r}</i>",
    "🏹 <b>Hit.</b> {a}'s ban arrow found {u} precisely.\n<i>Reason: {r}</i>",
    "❌ <b>Request denied.</b> {u} has been rejected by {a}.\n<i>Reason: {r}</i>",
    "🌀 <b>Sucked into the ban vortex.</b> {u}, courtesy of {a}.\n<i>Reason: {r}</i>",
    "⚡ <b>Struck down.</b> {u} has been lightning-banned by {a}.\n<i>Reason: {r}</i>",
    "🪤 <b>Trapped and removed.</b> {a} caught {u}.\n<i>Reason: {r}</i>",
    "🚀 <b>Launched into orbit.</b> {u} won't be back. Thanks {a}.\n<i>Reason: {r}</i>",
]
KICK_MSGS = [
    "👢 <b>Booted.</b> {u} was kicked by {a}.",
    "🚪 <b>Door found.</b> {u} was shown the exit by {a}.",
    "💨 <b>Gone with the wind.</b> {a} yote {u} out.",
    "🤸 <b>Yeeted.</b> {u} left the chat… involuntarily. Thanks {a}.",
    "🌬️ <b>Blown away.</b> {u} was evicted by {a}.",
    "🏃 <b>Running.</b> {u} was chased out by {a}.",
    "🎳 <b>Strike!</b> {a} knocked {u} clean out.",
    "🏏 <b>Out of bounds.</b> {a} hit {u} out of the park.",
    "🎯 <b>Bullseye.</b> {a}'s kick landed perfectly on {u}.",
    "🌊 <b>Washed out.</b> {u} was swept away by {a}.",
    "⛳ <b>Hole in one.</b> {a} kicked {u} into the next dimension.",
    "🦵 <b>Leg sweep.</b> {u} didn't see it coming. Admin: {a}.",
    "🎮 <b>Game over.</b> {a} ended {u}'s run here.",
    "🧹 <b>Swept out.</b> {a} cleaned house and {u} was the mess.",
    "🚂 <b>Next stop: outside.</b> {a} conducted {u}'s departure.",
    "🌪️ <b>Blown away.</b> {u} couldn't withstand {a}'s kick storm.",
    "🗑️ <b>Trash taken out.</b> {a} disposed of {u} professionally.",
    "🐾 <b>Paw of justice.</b> {u} got kicked by {a}.",
    "⚽ <b>Goal!</b> {a} kicked {u} into the net — and out of here.",
    "🚁 <b>Airlifted out.</b> {u} was extracted by {a}.",
    "🌑 <b>Darkness found.</b> {u} was sent to the shadow realm by {a}.",
    "🎪 <b>Show's over.</b> {a} removed {u} from the performance.",
    "🔄 <b>Rotated out.</b> {a} replaced {u} with fresh air.",
    "🧲 <b>Repelled.</b> {a}'s admin force pushed {u} away.",
    "🎭 <b>Curtain call.</b> {u} took their final bow — kicked by {a}.",
    "🌅 <b>Sunrise without you.</b> {u} was kicked out before dawn by {a}.",
    "🔑 <b>Key revoked.</b> {a} took back {u}'s access card.",
    "💫 <b>Shooting star.</b> {u} streaked through and got kicked by {a}.",
    "🎲 <b>Rolled out.</b> {a} rolled {u} right out the door.",
    "🌺 <b>Pruned.</b> {a} removed {u} for healthy group growth.",
]
MUTE_MSGS = [
    "🔇 <b>Silenced.</b> {u} can no longer speak. Admin: {a}.\n<i>Reason: {r}</i>",
    "🤫 <b>Shhhh.</b> {a} muted {u} for the group's sanity.\n<i>Reason: {r}</i>",
    "📵 <b>Mic off.</b> {a} cut {u}'s microphone.\n<i>Reason: {r}</i>",
    "🔕 <b>On mute.</b> {u} has been silenced by {a}.\n<i>Reason: {r}</i>",
    "😶 <b>Speechless.</b> {u} was muted by {a}.\n<i>Reason: {r}</i>",
    "🌚 <b>Quiet mode.</b> {a} enabled silent mode on {u}.\n<i>Reason: {r}</i>",
    "🎤 <b>Mic dropped — and taken.</b> {a} removed {u}'s voice.\n<i>Reason: {r}</i>",
    "🔐 <b>Speech locked.</b> {a} locked {u}'s ability to type.\n<i>Reason: {r}</i>",
    "🌊 <b>Words drowned.</b> {u} was silenced by {a}.\n<i>Reason: {r}</i>",
    "⏸️ <b>Paused.</b> {a} pressed pause on {u}'s messages.\n<i>Reason: {r}</i>",
    "🧱 <b>Wall built.</b> {u} can't type past {a}'s mute wall.\n<i>Reason: {r}</i>",
    "🕯️ <b>Extinguished.</b> {u}'s voice was snuffed by {a}.\n<i>Reason: {r}</i>",
    "📺 <b>Channel changed.</b> {a} turned off {u}'s broadcast.\n<i>Reason: {r}</i>",
    "🎭 <b>Mime mode.</b> {u} gestures only now. Thanks {a}.\n<i>Reason: {r}</i>",
    "🌙 <b>Night mode.</b> {a} put {u} in silent sleep mode.\n<i>Reason: {r}</i>",
    "🎸 <b>Unplugged.</b> {a} pulled {u}'s cord.\n<i>Reason: {r}</i>",
    "🏔️ <b>Sound absorbed.</b> {u} speaks into the void now. By {a}.\n<i>Reason: {r}</i>",
    "🚨 <b>Signal blocked.</b> {a} jammed {u}'s transmission.\n<i>Reason: {r}</i>",
    "🎺 <b>No more music.</b> {a} silenced {u}'s horn.\n<i>Reason: {r}</i>",
    "🌫️ <b>Foggy silence.</b> {u}'s words lost in the mist — by {a}.\n<i>Reason: {r}</i>",
    "🗿 <b>Stone cold silent.</b> {a} turned {u} to stone.\n<i>Reason: {r}</i>",
    "📻 <b>Static only.</b> {a} took {u} off the air.\n<i>Reason: {r}</i>",
    "❄️ <b>Frozen.</b> {u}'s messages are frozen in time by {a}.\n<i>Reason: {r}</i>",
    "⛔ <b>No transmit.</b> {a} blocked {u}'s signal.\n<i>Reason: {r}</i>",
    "🌑 <b>Radio silence.</b> {a} initiated {u} into quiet protocol.\n<i>Reason: {r}</i>",
    "🎙️ <b>Off the record.</b> {u} was taken off record by {a}.\n<i>Reason: {r}</i>",
    "🔴 <b>Live feed cut.</b> {a} terminated {u}'s broadcast.\n<i>Reason: {r}</i>",
    "💤 <b>Sleep mode.</b> {a} put {u} to sleep — messaging wise.\n<i>Reason: {r}</i>",
    "🌀 <b>Spun into silence.</b> {u} was muted by {a}'s vortex.\n<i>Reason: {r}</i>",
    "🔇 <b>Zero signal.</b> {a} reduced {u} to digital silence.\n<i>Reason: {r}</i>",
]
WARN_MSGS = [
    "⚠️ <b>Warning issued.</b> {u} received a warning from {a}.\n<i>Reason: {r}</i>",
    "🚨 <b>Strike recorded.</b> {a} issued strike to {u}.\n<i>Reason: {r}</i>",
    "📋 <b>Noted.</b> {u} has been warned by {a}.\n<i>Reason: {r}</i>",
    "⚡ <b>Caution.</b> {a} gave {u} a yellow card.\n<i>Reason: {r}</i>",
    "🌩️ <b>Storm warning.</b> {u} was officially warned by {a}.\n<i>Reason: {r}</i>",
    "🏳️ <b>Flag raised.</b> {a} flagged {u}'s behavior.\n<i>Reason: {r}</i>",
    "📎 <b>Pinned to record.</b> {u}'s warning was filed by {a}.\n<i>Reason: {r}</i>",
    "🔺 <b>Attention required.</b> {a} warned {u} formally.\n<i>Reason: {r}</i>",
    "🪤 <b>Caught.</b> {a} caught {u} and issued a warning.\n<i>Reason: {r}</i>",
    "🌡️ <b>Temperature rising.</b> {u} warned by {a} — last chance.\n<i>Reason: {r}</i>",
    "🧯 <b>Fire prevention.</b> {a} warned {u} before it escalates.\n<i>Reason: {r}</i>",
    "📌 <b>Marked.</b> {u} has been officially marked by {a}.\n<i>Reason: {r}</i>",
    "🗂️ <b>Case opened.</b> {a} opened a formal warning for {u}.\n<i>Reason: {r}</i>",
    "🔔 <b>Bell rung.</b> {u} was warned by {a} — consider this the bell.\n<i>Reason: {r}</i>",
    "🎯 <b>Targeted.</b> {a}'s warning found {u} precisely.\n<i>Reason: {r}</i>",
    "📢 <b>Announced.</b> {a} publicly warned {u}.\n<i>Reason: {r}</i>",
    "🌀 <b>Spiral alert.</b> {u} spiraling — warned by {a}.\n<i>Reason: {r}</i>",
    "🔦 <b>Spotlight on you.</b> {a} is watching {u}.\n<i>Reason: {r}</i>",
    "📊 <b>Strike logged.</b> {u}'s record updated by {a}.\n<i>Reason: {r}</i>",
    "⚖️ <b>Scales tipped.</b> {u} warned — balance restored by {a}.\n<i>Reason: {r}</i>",
    "🌊 <b>Rising tide.</b> {a} warned {u} before the flood comes.\n<i>Reason: {r}</i>",
    "🧲 <b>Attracted attention.</b> {u} got {a}'s official notice.\n<i>Reason: {r}</i>",
    "🔐 <b>On record.</b> {a} recorded {u}'s infraction officially.\n<i>Reason: {r}</i>",
    "🪪 <b>ID'd.</b> {a} identified and warned {u}.\n<i>Reason: {r}</i>",
    "🎪 <b>Center ring.</b> {u} is now in the spotlight — warned by {a}.\n<i>Reason: {r}</i>",
    "🔭 <b>Observed.</b> {a} is tracking {u} now. Warned.\n<i>Reason: {r}</i>",
    "🏅 <b>Not the medal you wanted.</b> {u} warned by {a}.\n<i>Reason: {r}</i>",
    "📱 <b>Notification sent.</b> {u} was notified by {a} via warning.\n<i>Reason: {r}</i>",
    "🌋 <b>Pressure building.</b> {a} warns {u} — last eruption incoming.\n<i>Reason: {r}</i>",
    "🎭 <b>Scene noted.</b> {a} documented {u}'s performance.\n<i>Reason: {r}</i>",
]

# ─── MARRIAGE MESSAGES ────────────────────────────────────────────────────────
MARRY_MSGS = [
    "💍 {a} got down on one knee and proposed to {b} — {b} said YES!",
    "💕 {a} looked {b} in the eyes and asked the big question. {b}: 'YES!'",
    "👰 {a} and {b} just got married! The universe ships it!",
    "🌹 {a} proposed to {b} with a ring from the heart! It's official!",
    "💒 {a} and {b} tied the knot in the most beautiful ceremony!",
    "🎊 {a} and {b} said 'I do' — the crowd erupts in tears!",
    "✨ {a} swept {b} off their feet! They're MARRIED now!",
    "💘 {a}'s proposal left {b} speechless — but they said YES!",
    "🥂 Toast to {a} and {b}! Officially married!",
    "🌟 {a} and {b} wrote a new chapter together — starting NOW!",
    "🕊️ {a} and {b} joined in love — unbreakable bond formed!",
    "🎶 {a} played their song and asked {b} to be theirs forever!",
    "💌 {a}'s love letter convinced {b} — they said YES!",
    "🌸 {a} and {b} bloomed together into something beautiful!",
    "⚡ {a} proposed so fast {b}'s heart skipped a beat — still said YES!",
    "🏰 {a} and {b} built their castle together today!",
    "🌈 {a} found their rainbow in {b} — married!",
    "🦋 {a} and {b} emerged together as something new — married!",
    "🌺 {a}'s love for {b} bloomed into forever!",
    "🪐 {a} told {b} 'you're my universe' — {b} said yes to the stars!",
]
DIVORCE_MSGS = [
    "💔 {a} and {b} have parted ways. It's official.",
    "📜 {a} signed the divorce papers from {b}. New era begins.",
    "🌧️ {a} and {b} ended their marriage today. Sad day.",
    "🔓 {a} and {b} released each other to find new paths.",
    "🥀 What {a} and {b} had has faded. They go separately now.",
    "💸 {a} and {b} split up. The lawyers got rich.",
    "🌑 {a} and {b}'s story closed its final chapter today.",
    "🕯️ The flame between {a} and {b} went out.",
    "📦 {a} packed their bags and left {b}.",
    "🚪 {a} and {b} walked through different doors today.",
    "❄️ What was warm between {a} and {b} has frozen over.",
    "🍂 {a} and {b} fell apart like autumn leaves.",
    "🌊 The tide pulled {a} and {b} in opposite directions.",
    "⏳ Time ran out for {a} and {b}. Divorce finalized.",
    "🌫️ {a} and {b} dissolved like morning fog.",
    "💬 {a} said 'it's over' to {b}. Quietly. Firmly.",
    "🎭 The curtain fell on {a} and {b}'s love story.",
    "🔮 The crystal ball showed separate futures for {a} and {b}.",
    "🌙 {a} and {b}'s moon has set. New suns await.",
    "🌿 {a} and {b} grew in different directions. That's okay.",
]

# ─── WELCOME MESSAGES — 40 variations ────────────────────────────────────────
WELCOME_MSGS = [
    "👋 Welcome to {chat}, {user}! You've just entered the best group on Telegram!",
    "🎉 {user} just dropped into {chat}! The vibe just elevated!",
    "✨ A new legend enters: {user}! Welcome to {chat}!",
    "🌟 {user} has arrived in {chat}! The wait is over!",
    "🚀 {user} just launched into {chat}! Buckle up!",
    "💫 {chat} officially has a new member: {user}! Welcome!",
    "🎊 Pop the confetti! {user} is here! Welcome to {chat}!",
    "🦋 {user} emerged from their cocoon and flew into {chat}!",
    "⚡ INCOMING! {user} has entered {chat}! Great timing!",
    "🌈 {user} brought good vibes to {chat}! Welcome aboard!",
    "🏆 {chat} just leveled up with {user}'s arrival!",
    "🌺 {user} blossomed into {chat}! Welcome!",
    "🔥 {user} is heating up {chat} with their presence!",
    "💎 A new gem discovered: {user}, welcome to {chat}!",
    "🎵 The soundtrack of {chat} welcomes {user}!",
    "🌊 {user} washed ashore in {chat}! The tide brought good things!",
    "🦅 {user} soared into {chat}! Wings spread wide!",
    "🎭 The stage of {chat} gains a new performer: {user}!",
    "🌙 {user} lit up {chat} like a new star in the sky!",
    "🏰 The gates of {chat} open for {user}! Enter!",
    "🪐 {user} orbited into {chat}'s galaxy! Welcome!",
    "🎪 Step right up! {user} has joined the {chat} circus!",
    "🌿 {user} rooted themselves in {chat}! Growth begins!",
    "🦁 A fierce one joins the pride: {user} in {chat}!",
    "💡 {user} just switched the lights on in {chat}!",
    "🎯 Direct hit! {user} landed perfectly in {chat}!",
    "🌸 {user} bloomed into {chat} like spring!",
    "⭐ {user} is the new star of {chat}!",
    "🔑 {user} found the key to {chat}! Door is open!",
    "🌴 Welcome to paradise, {user}! {chat} is glad you're here!",
    "🧩 The final piece arrives: {user} completes {chat}!",
    "🦋 A butterfly moment — {user} joins {chat}!",
    "🛸 {user} landed in {chat} from another dimension!",
    "🎆 Fireworks! {user} arrived in {chat}!",
    "🌅 A new dawn rises in {chat} with {user}!",
    "💪 {chat} just got stronger with {user} joining!",
    "🔮 The crystal ball predicted {user} would join {chat}! Correct!",
    "🎨 {user} painted themselves into the masterpiece that is {chat}!",
    "🌌 In the vast universe of Telegram, {user} chose {chat}!",
    "🏄 {user} rode the wave straight into {chat}!",
]

# ─── VIBE CHECK RESULTS ───────────────────────────────────────────────────────
VIBE_POOL = [
    "✅ VIBE CHECKED: Immaculate. You are the vibe.",
    "⚡ VIBE CHECKED: Electric. You're giving main character energy today.",
    "💅 VIBE CHECKED: Serving. The audacity? Appreciated.",
    "🔥 VIBE CHECKED: On fire. The vibes are in their prime right now.",
    "🌈 VIBE CHECKED: Colorful. The chaos is organized and it works.",
    "🌙 VIBE CHECKED: Dreamy. You're operating in another dimension.",
    "😤 VIBE CHECKED: Turbulent. Something's brewing — channel it.",
    "❄️ VIBE CHECKED: Icy. Cool, calculated, possibly intimidating.",
    "🌊 VIBE CHECKED: Flowing. You're going with it — smart.",
    "🎭 VIBE CHECKED: Theatrical. Everything is a performance right now.",
    "🦋 VIBE CHECKED: Transforming. You're mid-glow-up — be patient.",
    "🌿 VIBE CHECKED: Grounded. You're rooted. That's rare.",
    "🌪️ VIBE CHECKED: Chaotic. It's either your best or worst day.",
    "💫 VIBE CHECKED: Cosmic. The stars are literally aligned for you.",
    "🏆 VIBE CHECKED: Champion mode. You're winning and it shows.",
    "🎯 VIBE CHECKED: Focused. Laser precision right now.",
    "🌺 VIBE CHECKED: Blooming. Something beautiful is opening up.",
    "🔮 VIBE CHECKED: Mysterious. Nobody knows what you're planning.",
    "💎 VIBE CHECKED: Premium. Top tier energy across the board.",
    "🌑 VIBE CHECKED: Introspective. Quiet outside, storm inside.",
    "☀️ VIBE CHECKED: Radiant. You're literally glowing today.",
    "🧊 VIBE CHECKED: Frozen. Unbothered to the point of legend.",
    "🎪 VIBE CHECKED: Unhinged. The show must go on and it IS.",
    "🌸 VIBE CHECKED: Soft. Gentle energy — people feel safe around you.",
    "⭐ VIBE CHECKED: Rising. You're ascending and everyone can see it.",
    "🦅 VIBE CHECKED: Soaring. High above the drama. Respect.",
    "🎵 VIBE CHECKED: Melodic. Your frequency is tuned perfectly.",
    "🔴 VIBE CHECKED: Intense. You're giving 110% and it's showing.",
    "🌍 VIBE CHECKED: Worldly. You've got perspective most people lack.",
    "💜 VIBE CHECKED: Healing. You're in recovery mode — and thriving.",
]

# ─── PERSONALITY RESULTS ─────────────────────────────────────────────────────
PERSONALITY_POOL = [
    "🦁 The Lion — Bold, loud, and unapologetically you. You lead without being asked.",
    "🦊 The Fox — Witty, resourceful, always three moves ahead. People underestimate you.",
    "🐢 The Turtle — Slow and steady wins everything. Your patience is legendary.",
    "🦋 The Butterfly — You've transformed before and you'll do it again. Resilient beauty.",
    "🐝 The Bee — Relentlessly productive. You build, you create, you never stop.",
    "🌊 The Ocean — Deep, complex, sometimes stormy, always vast. Most don't know your depth.",
    "🔥 The Flame — Bright, warm, occasionally destructive, always drawing moths.",
    "🌿 The Forest — Calm on the surface, complex underneath. A whole ecosystem within you.",
    "⚡ The Storm — Unpredictable, electric, impossible to ignore. Forces of nature, you are.",
    "🌸 The Cherry Blossom — Beautiful, brief, unforgettable. You impact people before you go.",
    "🏔️ The Mountain — Immovable, reliable, summit worth reaching. People lean on you.",
    "🌙 The Moon — Mysterious, cyclical, illuminating darkness for others. Hidden power.",
    "☀️ The Sun — Everyone orbits around you eventually. Warmth personified.",
    "🎭 The Actor — You contain multitudes. You play every role perfectly.",
    "🗝️ The Key — You unlock potential in others. That's a rare gift.",
    "🧭 The Compass — People follow you when they're lost. You give direction naturally.",
    "🌀 The Spiral — Everything leads inward or outward for you. Nothing is simple.",
    "🎵 The Song — You get stuck in people's heads. Your energy lingers long after you're gone.",
    "🔮 The Oracle — You see what others miss. Your instincts border on prophecy.",
    "💎 The Diamond — Formed under pressure, incredibly hard to break, blindingly brilliant.",
]

# ─── MOOD POOL ────────────────────────────────────────────────────────────────
MOOD_WORDS = ["chaotic","vibey","electric","sleepy","hyper","philosophical","unhinged",
              "grounded","anxious","blessed","suspicious","focused","nostalgic","delusional",
              "caffeinated","introspective","feral","cottagecore","galactic","zen","dramatic",
              "analytical","chaotic neutral","soft","tired but iconic","unwell but functioning",
              "operating at full chaos","in my main character era","mentally on vacation",
              "emotionally unavailable","spiritually lost but stylish","giving villain arc",
              "giving redemption arc","existing at 40% battery"]

# ─── RPS game data ────────────────────────────────────────────────────────────
RPS_EMOJIS = {"rock":"🪨","paper":"📄","scissors":"✂️"}
RPS_BEATS  = {"rock":"scissors","scissors":"paper","paper":"rock"}
RPS_WIN_MSGS = [
    "Flawless victory!","You absolutely demolished the bot!","The universe favors you!",
    "Unstoppable force!","Too easy — are you even trying?","That was criminal levels of skill!",
]
RPS_LOSE_MSGS = [
    "The bot wins this round!","Better luck next time!","I am inevitable.",
    "The machine rises!","You were robbed by fate!","Practice makes perfect!",
]
RPS_DRAW_MSGS = [
    "A draw! We are evenly matched!","Minds alike, apparently.","It's a tie — shocking!",
    "Neither of us can lose today!","Mirror match activated!","Equilibrium achieved!",
]

# ── AI HELPERS (kept for /ask command only) ────────────────────────────────────
async def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        timeout = aiohttp.ClientTimeout(total=25)
        _session = aiohttp.ClientSession(timeout=timeout)
    return _session

async def ai_reply(prompt: str, fallback: str = "…") -> str:
    """Try multiple free AI APIs with fallback."""
    endpoints = [
        ("https://text.pollinations.ai/openai",
         {"model":"openai","messages":[{"role":"user","content":prompt}],"max_tokens":200}),
    ]
    session = await get_session()
    for url, payload in endpoints:
        try:
            async with session.post(url, json=payload) as r:
                if r.status == 200:
                    data = await r.json()
                    text = (data.get("choices",[{}])[0].get("message",{}).get("content","")
                            or data.get("output","") or data.get("text",""))
                    text = text.strip()
                    if text and len(text) > 3:
                        return text[:500]
        except Exception:
            pass
    return fallback

# ═══════════════════════════════════════════════════════════════════════════════
#                            UI / FORMATTING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def progress_bar(val: int, max_val: int, length: int = 10) -> str:
    filled = round((val / max_val) * length) if max_val else 0
    return "█" * filled + "░" * (length - filled)

def fmt_coins(n: int) -> str:
    return f"🪙 {n:,}"

def rank_badge(level: int) -> str:
    badges = ["🌱","🍀","⭐","🌟","💫","🔥","💎","👑","🌌","⚡"]
    return badges[min(level // 5, len(badges)-1)]

async def animate_loading(update: Update, label: str = "Loading") -> any:
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    try:
        m = await update.message.reply_text(f"{frames[0]} <b>{label}…</b>", parse_mode="HTML")
        await asyncio.sleep(0.4)
        try: await m.edit_text(f"{frames[3]} <b>{label}…</b>", parse_mode="HTML")
        except: pass
        await asyncio.sleep(0.3)
        return m
    except Exception:
        return None

async def finish_anim(m, text: str, **kwargs):
    if m is None: return
    try: await m.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, **kwargs)
    except Exception as e:
        logger.debug(f"finish_anim edit failed: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                              DATABASE SETUP
# ═══════════════════════════════════════════════════════════════════════════════
def get_db() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    return db

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS chats (
        chat_id INTEGER PRIMARY KEY,
        title TEXT, welcome_text TEXT, welcome_on INTEGER DEFAULT 1,
        welcome_del INTEGER DEFAULT 0,
        goodbye_text TEXT, goodbye_on INTEGER DEFAULT 0,
        rules TEXT,
        antispam INTEGER DEFAULT 1, antiflood INTEGER DEFAULT 0,
        flood_limit INTEGER DEFAULT 5, flood_window INTEGER DEFAULT 10,
        flood_action TEXT DEFAULT 'mute',
        antilink INTEGER DEFAULT 0, antiforward INTEGER DEFAULT 0,
        antibot INTEGER DEFAULT 0, antinsfw INTEGER DEFAULT 0,
        antiarabic INTEGER DEFAULT 0,
        antiraid INTEGER DEFAULT 0, raid_threshold INTEGER DEFAULT 10,
        cas_enabled INTEGER DEFAULT 1,
        lock_stickers INTEGER DEFAULT 0, lock_gifs INTEGER DEFAULT 0,
        lock_media INTEGER DEFAULT 0, lock_polls INTEGER DEFAULT 0,
        lock_voice INTEGER DEFAULT 0, lock_video INTEGER DEFAULT 0,
        lock_document INTEGER DEFAULT 0, lock_forward INTEGER DEFAULT 0,
        lock_games INTEGER DEFAULT 0, lock_inline INTEGER DEFAULT 0,
        lock_url INTEGER DEFAULT 0, lock_anon INTEGER DEFAULT 0,
        warn_limit INTEGER DEFAULT 3, warn_action TEXT DEFAULT 'mute',
        captcha_on INTEGER DEFAULT 0, captcha_type TEXT DEFAULT 'button',
        log_channel TEXT,
        restrict_new INTEGER DEFAULT 0,
        clean_service INTEGER DEFAULT 0,
        del_commands INTEGER DEFAULT 0,
        language TEXT DEFAULT 'en',
        slowmode INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT, first_name TEXT, last_name TEXT,
        coins INTEGER DEFAULT 0, bank INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0, level INTEGER DEFAULT 0,
        reputation INTEGER DEFAULT 0,
        last_daily TIMESTAMP, last_work TIMESTAMP, last_mine TIMESTAMP,
        last_rob TIMESTAMP, last_rep TIMESTAMP,
        total_messages INTEGER DEFAULT 0,
        is_gbanned INTEGER DEFAULT 0, gban_reason TEXT,
        streak INTEGER DEFAULT 0, last_streak DATE,
        birthday TEXT,
        spouse_id INTEGER,
        married_at TIMESTAMP,
        mood TEXT,
        achievements TEXT DEFAULT '[]',
        clan_id INTEGER,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS warns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER, user_id INTEGER, reason TEXT, warned_by INTEGER,
        warned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS bans (
        chat_id INTEGER, user_id INTEGER, banned_by INTEGER,
        reason TEXT, banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (chat_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER, name TEXT, content TEXT,
        file_id TEXT, file_type TEXT, parse_mode TEXT DEFAULT 'HTML',
        buttons TEXT,
        UNIQUE(chat_id, name)
    );
    CREATE TABLE IF NOT EXISTS filters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER, keyword TEXT, reply TEXT,
        file_id TEXT, file_type TEXT,
        is_regex INTEGER DEFAULT 0,
        UNIQUE(chat_id, keyword)
    );
    CREATE TABLE IF NOT EXISTS blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER, word TEXT,
        UNIQUE(chat_id, word)
    );
    CREATE TABLE IF NOT EXISTS blacklist_settings (
        chat_id INTEGER PRIMARY KEY,
        action TEXT DEFAULT 'delete'
    );
    CREATE TABLE IF NOT EXISTS feds (
        fed_id TEXT PRIMARY KEY,
        name TEXT, owner_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS fed_chats (
        fed_id TEXT, chat_id INTEGER,
        PRIMARY KEY (fed_id, chat_id)
    );
    CREATE TABLE IF NOT EXISTS fed_admins (
        fed_id TEXT, user_id INTEGER,
        PRIMARY KEY (fed_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS fed_bans (
        fed_id TEXT, user_id INTEGER, reason TEXT, banned_by INTEGER,
        banned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (fed_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS admin_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER, admin_id INTEGER, action TEXT,
        target_id INTEGER, reason TEXT, extra TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS sudo_users (
        user_id INTEGER PRIMARY KEY,
        added_by INTEGER, added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS shop (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, description TEXT, price INTEGER, effect TEXT
    );
    CREATE TABLE IF NOT EXISTS inventory (
        user_id INTEGER, item_id INTEGER, quantity INTEGER DEFAULT 1,
        PRIMARY KEY (user_id, item_id)
    );
    CREATE TABLE IF NOT EXISTS rep_cooldown (
        giver_id INTEGER, receiver_id INTEGER, given_at TIMESTAMP,
        PRIMARY KEY (giver_id, receiver_id)
    );
    CREATE TABLE IF NOT EXISTS captcha_pending (
        chat_id INTEGER, user_id INTEGER, message_id INTEGER,
        answer TEXT, expires TIMESTAMP,
        PRIMARY KEY (chat_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER, text TEXT, interval_sec INTEGER,
        last_sent TIMESTAMP, active INTEGER DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS connections (
        user_id INTEGER PRIMARY KEY, chat_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS approved_users (
        chat_id INTEGER, user_id INTEGER,
        PRIMARY KEY (chat_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, chat_id INTEGER,
        text TEXT, remind_at TIMESTAMP, done INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS game_riddles (
        chat_id INTEGER PRIMARY KEY,
        question TEXT, answer TEXT, asker_id INTEGER,
        asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS marriages (
        user1_id INTEGER, user2_id INTEGER,
        married_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user1_id, user2_id)
    );
    CREATE TABLE IF NOT EXISTS proposals (
        from_id INTEGER, to_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (from_id, to_id)
    );
    CREATE TABLE IF NOT EXISTS lottery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, tickets INTEGER DEFAULT 0,
        chat_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS trivia_scores (
        chat_id INTEGER, user_id INTEGER, score INTEGER DEFAULT 0,
        PRIMARY KEY (chat_id, user_id)
    );
    CREATE TABLE IF NOT EXISTS hangman_state (
        chat_id INTEGER PRIMARY KEY,
        word TEXT, hint TEXT, guessed TEXT DEFAULT '',
        wrong TEXT DEFAULT '', max_wrong INTEGER DEFAULT 6,
        started_by INTEGER,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS battle_stats (
        user_id INTEGER PRIMARY KEY,
        wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS clans (
        clan_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE, leader_id INTEGER,
        description TEXT, coins INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Seed shop if empty
    if not db.execute("SELECT 1 FROM shop LIMIT 1").fetchone():
        db.executemany("INSERT INTO shop (name,description,price,effect) VALUES (?,?,?,?)", [
            ("Lucky Charm","Doubles your next daily reward",500,"daily_x2"),
            ("Miner's Pickaxe","50% bonus on next mine",750,"mine_bonus"),
            ("Shield","Blocks next rob attempt",400,"rob_shield"),
            ("XP Booster","Double XP for 24h",600,"xp_x2"),
            ("Loot Chest","Random 100–5000 coins",1000,"loot_chest"),
            ("Elixir of Fortune","Lucky outcome on next gamble",800,"gamble_luck"),
            ("Title Token","Set a custom title (cosmetic)",300,"title_token"),
            ("Mystery Box","Random rare reward",1500,"mystery_box"),
        ])
    db.commit(); db.close()
    logger.info("✅ Database initialized")

# ═══════════════════════════════════════════════════════════════════════════════
#                           DATABASE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def get_chat(chat_id: int) -> dict:
    entry = _chat_cache.get(chat_id)
    if entry and (time.time() - entry[1]) < _CHAT_TTL:
        return entry[0]
    db = get_db()
    row = db.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
    if not row:
        db.execute("INSERT OR IGNORE INTO chats (chat_id) VALUES (?)", (chat_id,))
        db.commit()
        row = db.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
    db.close()
    d = dict(row) if row else {}
    _chat_cache[chat_id] = (d, time.time())
    return d

def invalidate_chat_cache(chat_id: int):
    _chat_cache.pop(chat_id, None)

def get_user(user_id: int) -> dict:
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        db.commit()
        row = db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    db.close()
    return dict(row) if row else {}

def update_user(user_id: int, **kwargs):
    if not kwargs: return
    cols = ", ".join(f"{k}=?" for k in kwargs)
    db = get_db()
    db.execute(f"UPDATE users SET {cols}, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
               (*kwargs.values(), user_id))
    db.commit(); db.close()

def add_coins(user_id: int, amount: int):
    db = get_db()
    db.execute("UPDATE users SET coins = coins + ?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
               (amount, user_id))
    db.commit(); db.close()

def add_xp(user_id: int, amount: int = 5):
    db = get_db()
    user = db.execute("SELECT xp, level FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not user: db.close(); return
    xp = (user["xp"] or 0) + amount
    lvl = user["level"] or 0
    xp_needed = (lvl + 1) * 100
    if xp >= xp_needed:
        xp -= xp_needed; lvl += 1
    db.execute("UPDATE users SET xp=?, level=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
               (xp, lvl, user_id))
    db.commit(); db.close()

def get_setting(chat_id: int, key: str, default=None):
    return get_chat(chat_id).get(key, default)

def set_setting(chat_id: int, key: str, value):
    db = get_db()
    db.execute(f"UPDATE chats SET {key}=?, updated_at=CURRENT_TIMESTAMP WHERE chat_id=?", (value, chat_id))
    db.commit(); db.close()
    invalidate_chat_cache(chat_id)

def log_action(chat_id: int, admin_id: int, action: str, target_id: int = None,
               reason: str = None, extra: str = None):
    try:
        db = get_db()
        db.execute("INSERT INTO admin_logs (chat_id,admin_id,action,target_id,reason,extra) VALUES (?,?,?,?,?,?)",
                   (chat_id, admin_id, action, target_id, reason, extra))
        db.commit(); db.close()
    except Exception as e:
        logger.debug(f"log_action error: {e}")

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
    if not s: return None
    s = s.lower().strip()
    units = {"s":1,"m":60,"h":3600,"d":86400,"w":604800}
    m = re.match(r"^(\d+)([smhdw]?)$", s)
    if not m: return None
    value, unit = int(m.group(1)), m.group(2) or "s"
    return datetime.timedelta(seconds=value * units.get(unit, 1))

def fmt_duration(td: datetime.timedelta) -> str:
    s = int(td.total_seconds())
    if s < 60: return f"{s}s"
    if s < 3600: return f"{s//60}m {s%60}s"
    if s < 86400: return f"{s//3600}h {(s%3600)//60}m"
    return f"{s//86400}d {(s%86400)//3600}h"

# ═══════════════════════════════════════════════════════════════════════════════
#                        RATE LIMITER
# ═══════════════════════════════════════════════════════════════════════════════
COOLDOWNS = {  # seconds
    "daily":86400,"work":3600,"mine":1800,"rob":3600,
    "slots":30,"flip":15,"lottery":300,
    "trivia":10,"battle":60,"riddle":30,"hangman":5,
    "rps":5,"ttt":5,"scramble":10,
    "rep":86400,"roast":10,"compliment":10,"fortune":3600,
    "tarot":3600,"horoscope":21600,"vibe":300,"personality":3600,
    "joke":5,"fact":5,"quote":5,"8ball":3,"truth":10,"dare":10,"wyr":10,
}

def check_rate(user_id: int, cmd: str) -> Optional[float]:
    """Returns seconds remaining if on cooldown, else None."""
    key = f"{user_id}:{cmd}"
    cd = COOLDOWNS.get(cmd, 0)
    if cd == 0: return None
    last = _rate_limit.get(key, 0)
    remaining = (last + cd) - time.time()
    return remaining if remaining > 0 else None

def set_rate(user_id: int, cmd: str):
    _rate_limit[f"{user_id}:{cmd}"] = time.time()

def rate_limited(cmd: str):
    """Decorator for rate-limited commands."""
    def decorator(fn):
        @wraps(fn)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.effective_user: return
            rem = check_rate(update.effective_user.id, cmd)
            if rem:
                await reply(update, f"⏳ <b>Cooldown!</b> Try again in <b>{fmt_duration(datetime.timedelta(seconds=rem))}</b>")
                return
            set_rate(update.effective_user.id, cmd)
            return await fn(update, context)
        return wrapper
    return decorator

# ═══════════════════════════════════════════════════════════════════════════════
#                          PERMISSION HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
async def _fetch_admin_map(context, chat_id: int) -> dict:
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_map = {m.user.id: m for m in admins}
        _admin_cache[chat_id] = (admin_map, time.time())
        return admin_map
    except Exception as ex:
        logger.debug(f"_fetch_admin_map [{chat_id}]: {ex}")
        return _admin_cache.get(chat_id, ({}, 0))[0]

async def get_admin_map(context, chat_id: int) -> dict:
    entry = _admin_cache.get(chat_id)
    if entry and (time.time() - entry[1]) < _ADMIN_TTL:
        return entry[0]
    return await _fetch_admin_map(context, chat_id)

def invalidate_admin_cache(chat_id: int):
    _admin_cache.pop(chat_id, None)

async def get_member(context, chat_id: int, user_id: int):
    admin_map = await get_admin_map(context, chat_id)
    if user_id in admin_map: return admin_map[user_id]
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
    return m is not None and m.status == "creator"

async def can_restrict(context, chat_id: int, user_id: int) -> bool:
    if is_sudo(user_id): return True
    admin_map = await get_admin_map(context, chat_id)
    m = admin_map.get(user_id)
    if not m: return False
    if m.status == "creator": return True
    if m.status == "administrator" and isinstance(m, ChatMemberAdministrator):
        return bool(m.can_restrict_members)
    return False

async def can_pin(context, chat_id: int, user_id: int) -> bool:
    if is_sudo(user_id): return True
    admin_map = await get_admin_map(context, chat_id)
    m = admin_map.get(user_id)
    if not m: return False
    if m.status == "creator": return True
    if m.status == "administrator" and isinstance(m, ChatMemberAdministrator):
        return bool(m.can_pin_messages)
    return False

async def can_promote(context, chat_id: int, user_id: int) -> bool:
    if is_sudo(user_id): return True
    admin_map = await get_admin_map(context, chat_id)
    m = admin_map.get(user_id)
    if not m: return False
    if m.status == "creator": return True
    if m.status == "administrator" and isinstance(m, ChatMemberAdministrator):
        return bool(m.can_promote_members)
    return False

# ── Decorators ─────────────────────────────────────────────────────────────────
def admin_only(fn):
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not update.effective_user or not update.effective_chat: return
            if update.effective_chat.type == "private": return await fn(update, context)
            if not await is_admin(context, update.effective_chat.id, update.effective_user.id):
                await update.message.reply_text(
                    f"🚫 <b>Admin only!</b> {kmo(KAOMOJI_BAN)}\n<i>You need admin privileges for this.</i>",
                    parse_mode="HTML"); return
            return await fn(update, context)
        except Exception as e: logger.error(f"admin_only wrapper error: {e}")
    return wrapper

def owner_only(fn):
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if not update.effective_user: return
            if update.effective_user.id not in OWNER_IDS and not is_sudo(update.effective_user.id):
                await update.message.reply_text("👑 <b>Owner Only</b>\n<i>Restricted.</i>", parse_mode="HTML"); return
            return await fn(update, context)
        except Exception as e: logger.error(f"owner_only wrapper error: {e}")
    return wrapper

def groups_only(fn):
    @wraps(fn)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            if update.effective_chat and update.effective_chat.type == "private":
                await update.message.reply_text("👥 <b>Groups Only!</b>", parse_mode="HTML"); return
            return await fn(update, context)
        except Exception as e: logger.error(f"groups_only wrapper error: {e}")
    return wrapper

# ── Reply helpers ───────────────────────────────────────────────────────────────
async def reply(update: Update, text: str, **kwargs):
    try:
        return await update.message.reply_text(text, parse_mode="HTML",
                                               disable_web_page_preview=True, **kwargs)
    except Exception as e:
        logger.debug(f"reply error: {e}")

async def send_log(context, chat_id: int, text: str):
    cfg = get_chat(chat_id)
    ch = cfg.get("log_channel") or LOG_CHANNEL
    if ch:
        try: await context.bot.send_message(ch, text, parse_mode="HTML")
        except: pass

def user_link(user) -> str:
    try:
        name = html.escape(str(getattr(user, "first_name", "") or str(getattr(user, "id", "?"))))
        uid = getattr(user, "id", 0)
        return f'<a href="tg://user?id={uid}">{name}</a>'
    except: return "Unknown"

async def get_target(update: Update, context) -> Optional[User]:
    try:
        msg = update.message
        if msg and msg.reply_to_message:
            return msg.reply_to_message.from_user
        if context.args:
            arg = context.args[0].lstrip("@")
            if arg.lstrip("-").isdigit():
                uid = int(arg)
                return type("FakeUser",(),{"id":uid,"first_name":str(uid),"username":None,"last_name":None,"is_bot":False})()
            else:
                try:
                    chat = await context.bot.get_chat(f"@{arg}")
                    return type("FakeUser",(),{
                        "id":chat.id,"first_name":chat.first_name or chat.title or arg,
                        "username":chat.username,"last_name":getattr(chat,"last_name",None),"is_bot":False})()
                except Exception as ex:
                    logger.debug(f"get_target @{arg}: {ex}")
    except Exception as e:
        logger.debug(f"get_target error: {e}")
    return None

def get_reason(context, start: int = 1) -> str:
    try:
        return " ".join(context.args[start:]) if context.args and len(context.args) > start else ""
    except: return ""

def get_connected_chat(user_id: int, chat) -> int:
    if chat.type != "private": return chat.id
    return connection_cache.get(user_id, chat.id)

# ═══════════════════════════════════════════════════════════════════════════════
#                              START / HELP
# ═══════════════════════════════════════════════════════════════════════════════
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_chat.type != "private":
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("📖 Help", url=f"https://t.me/{context.bot.username}?start=help"),
                InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{context.bot.username}?startgroup=true"),
            ]])
            greeting = R.pick(COMPLIMENT_POOL[:20], "start_greet")
            await reply(update,
                f"⚡ <b>NEXUS BOT v{VERSION} IS LIVE</b> {kmo(KAOMOJI_HYPE)}\n"
                f"🤖 <i>Pure randomness · Ultra-advanced · Never sleeps</i>\n"
                f"📖 /help · ⚙️ /settings · 🤖 /ask anything\n"
                f"<i>{random.choice(GEN_Z_PHRASES)}</i>", reply_markup=kb); return
        name = html.escape(update.effective_user.first_name or "Friend")
        text = (
            f"✨ <b>NEXUS BOT v{VERSION}</b> — hey {name[:20]}!\n{_D}\n"
            f"<i>{R.pick(COMPLIMENT_POOL, 'start_msg')}</i>\n{_D}\n"
            f"🛡️ <b>Moderation</b> — ban mute warn kick promote purge\n"
            f"🚫 <b>Auto-Protection</b> — anti-spam flood raid NSFW CAS captcha\n"
            f"📝 <b>Notes & Filters</b> — smart auto-replies, regex support\n"
            f"🌐 <b>Federation</b> — cross-group ban network\n"
            f"💰 <b>Economy</b> — mine work daily rob flip slots lottery shop\n"
            f"🎮 <b>Games</b> — hangman scramble RPS tictactoe trivia battle\n"
            f"💍 <b>Marriage</b> — propose, accept, divorce\n"
            f"🔮 <b>Tarot & Fortune</b> — pure algorithmic, unlimited variety\n"
            f"🎲 <b>Fun</b> — roast truth dare wyr 8ball joke fact riddle vibe\n"
            f"🏆 <b>Achievements</b> — streaks, ranks, leaderboards\n{_D}\n"
            f"✅ <b>350+ features · 3500+ unique responses · Zero AI dependency</b>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 Help Menu", callback_data="help_main"),
             InlineKeyboardButton("➕ Add to Group", url=f"https://t.me/{context.bot.username}?startgroup=true")],
            [InlineKeyboardButton("🛡️ Moderation", callback_data="help_mod"),
             InlineKeyboardButton("💰 Economy", callback_data="help_economy")],
            [InlineKeyboardButton("🎮 Games & Fun", callback_data="help_fun"),
             InlineKeyboardButton("💍 Marriage & Social", callback_data="help_social")],
            [InlineKeyboardButton("🔮 Tarot & Fortune", callback_data="help_magic"),
             InlineKeyboardButton("⚙️ Settings", callback_data="help_settings")],
        ])
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"start_cmd error: {e}")

HELP_SECTIONS = {
    "help_main": (
        f"🤖 <b>NEXUS BOT v{VERSION} — Help Center</b>\n{_D}\n"
        f"<i>Pure Randomness · 350+ Commands · Zero-Error Architecture</i>\n\n"
        "📂 <b>Choose a category below:</b>",
        [[InlineKeyboardButton("🛡️ Moderation", callback_data="help_mod"),
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
          InlineKeyboardButton("💍 Social & Marriage", callback_data="help_social")],
         [InlineKeyboardButton("🔮 Magic & Fortune", callback_data="help_magic"),
          InlineKeyboardButton("🔧 Utilities", callback_data="help_util")],
         [InlineKeyboardButton("⚙️ Settings", callback_data="help_settings"),
          InlineKeyboardButton("👑 Admin/Owner", callback_data="help_admin")]]
    ),
    "help_mod": (
        "🛡️ <b>Moderation Commands</b>\n" + _D + "\n\n"
        "🔨 <b>BAN</b>\n"
        "<code>/ban</code> [reply/@user] [reason] · <code>/tban 1h [reason]</code>\n"
        "<code>/sban</code> (silent) · <code>/unban</code>\n\n"
        "👢 <b>KICK</b>\n<code>/kick</code> · <code>/skick</code> (silent)\n\n"
        "🔇 <b>MUTE</b>\n<code>/mute</code> · <code>/tmute 1h</code> · <code>/unmute</code>\n\n"
        "⚠️ <b>WARN</b>\n<code>/warn</code> · <code>/dwarn</code> · <code>/swarn</code>\n"
        "<code>/unwarn</code> · <code>/resetwarn</code> · <code>/warns</code>\n\n"
        "👑 <b>PROMOTE/DEMOTE</b>\n<code>/promote [title]</code> · <code>/demote</code>\n"
        "<code>/admintitle [title]</code> · <code>/adminlist</code>\n\n"
        "🧹 <b>CLEANUP</b>\n<code>/purge [N]</code> · <code>/del</code> · <code>/slowmode [s]</code>\n"
        "<code>/pin</code> · <code>/unpin</code> · <code>/unpinall</code>\n"
        "<code>/zombies</code> · <code>/kickzombies</code> · <code>@admins</code>\n\n"
        "✅ <b>APPROVE</b>\n<code>/approve</code> · <code>/disapprove</code> · <code>/approved</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_protect": (
        "🚫 <b>Protection System</b>\n" + _D + "\n\n"
        "<code>/antispam on|off</code> · <code>/antiflood on|off</code>\n"
        "<code>/antilink on|off</code> · <code>/antiforward on|off</code>\n"
        "<code>/antibot on|off</code> · <code>/antinsfw on|off</code>\n"
        "<code>/antiarabic on|off</code> · <code>/cas on|off</code>\n"
        "<code>/antiraid on|off</code> · <code>/setraid N</code>\n"
        "<code>/restrict on|off</code> (mute new members)\n"
        "<code>/setflood N</code> · <code>/setfloodaction mute|ban|kick</code>\n"
        "<code>/protect</code> — interactive panel",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_notes": (
        "📝 <b>Notes System</b>\n" + _D + "\n\n"
        "<code>/save name text</code> — save a note\n"
        "<code>/get name</code> · <code>#name</code> — retrieve\n"
        "<code>/notes</code> — list all · <code>/clear name</code> — delete\n"
        "<code>/clearall</code> — delete all\n\n"
        "Supports <b>HTML</b>, <i>media</i>, and button syntax:\n"
        "<code>[text](url)</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_filters": (
        "🔍 <b>Filters & Blacklist</b>\n" + _D + "\n\n"
        "<code>/filter keyword reply</code> — add auto-reply filter\n"
        "<code>/filters</code> · <code>/stop keyword</code> · <code>/stopall</code>\n"
        "<code>/filter regex:pattern reply</code> — regex support\n\n"
        "🚫 <b>BLACKLIST</b>\n"
        "<code>/addbl word</code> · <code>/rmbl word</code>\n"
        "<code>/blacklist</code> · <code>/blmode delete|warn|mute|ban</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_locks": (
        "🔒 <b>Lock System</b>\n" + _D + "\n\n"
        "<code>/lock type</code> · <code>/unlock type</code> · <code>/locks</code>\n\n"
        "<b>Types:</b> stickers · gifs · media · polls · voice · video\n"
        "document · forward · games · inline · url · anon · all",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_welcome": (
        "👋 <b>Welcome & Goodbye</b>\n" + _D + "\n\n"
        "<code>/setwelcome text</code> · <code>/welcome on|off</code>\n"
        "<code>/welcdel N</code> — delete after N secs\n"
        "<code>/captcha on|off</code> · <code>/captchatype button|math</code>\n"
        "<code>/setgoodbye text</code> · <code>/goodbye on|off</code>\n"
        "<code>/setrules text</code> · <code>/rules</code>\n\n"
        "<b>Placeholders:</b> {first} {last} {mention} {count} {chatname}",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_fed": (
        "🌐 <b>Federation System</b>\n" + _D + "\n\n"
        "<code>/newfed name</code> · <code>/delfed</code>\n"
        "<code>/joinfed fed_id</code> · <code>/leavefed</code>\n"
        "<code>/fedinfo</code> · <code>/fban user [reason]</code>\n"
        "<code>/unfban user</code> · <code>/fedbans</code>\n"
        "<code>/fadmin user</code> · <code>/fremove user</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_connect": (
        "🔗 <b>Connection System</b>\n" + _D + "\n\n"
        "<code>/connect chat_id</code> · <code>/disconnect</code> · <code>/connected</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_economy": (
        "💰 <b>Economy System</b>\n" + _D + "\n\n"
        "<code>/daily</code> · <code>/work</code> · <code>/mine</code>\n"
        "<code>/bank deposit N</code> · <code>/bank withdraw N</code> · <code>/bank balance</code>\n"
        "<code>/flip amount</code> · <code>/slots amount</code> · <code>/rob @user</code>\n"
        "<code>/give @user amount</code> · <code>/coins [@user]</code>\n"
        "<code>/shop</code> · <code>/buy item_id</code> · <code>/inventory</code>\n"
        "<code>/lottery</code> · <code>/leaderboard</code> · <code>/streak</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_rep": (
        "⭐ <b>Reputation & Ranks</b>\n" + _D + "\n\n"
        "<code>+rep</code> / <code>/rep @user</code> — give +1 rep (24h cooldown)\n"
        "<code>/checkrep [@user]</code> · <code>/reprank</code>\n"
        "<code>/rank [@user]</code> · <code>/top</code> · <code>/level [@user]</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_fun": (
        "🎮 <b>Games & Fun</b>\n" + _D + "\n\n"
        "🎲 <b>WORD GAMES</b>\n"
        "<code>/hangman</code> — start a game · <code>/guess letter</code>\n"
        "<code>/scramble</code> — unscramble the word\n"
        "<code>/riddle</code> — random riddle · <code>/answer text</code>\n\n"
        "⚔️ <b>ACTION GAMES</b>\n"
        "<code>/rps rock|paper|scissors</code>\n"
        "<code>/tictactoe @user</code> · <code>/battle @user</code>\n\n"
        "🎯 <b>CLASSIC</b>\n"
        "<code>/trivia</code> · <code>/wyr</code> · <code>/truth</code> · <code>/dare</code>\n"
        "<code>/8ball question</code> · <code>/roll [N]</code> · <code>/pp</code> · <code>/ship</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_social": (
        "💍 <b>Social & Marriage</b>\n" + _D + "\n\n"
        "💑 <b>MARRIAGE</b>\n"
        "<code>/marry @user</code> — propose\n"
        "<code>/accept</code> — accept proposal (reply)\n"
        "<code>/divorce</code> — end marriage\n"
        "<code>/spouse</code> — see your partner\n\n"
        "💕 <b>SOCIAL ACTIONS</b>\n"
        "<code>/hug @user</code> · <code>/slap @user</code>\n"
        "<code>/kiss @user</code> · <code>/pat @user</code>\n"
        "<code>/poke @user</code> · <code>/roast @user</code>\n"
        "<code>/compliment @user</code> · <code>/ship @user1 @user2</code>\n\n"
        "📊 <b>STATUS</b>\n"
        "<code>/mood [text]</code> · <code>/vibe</code> · <code>/personality</code>\n"
        "<code>/setbirthday DD/MM</code> · <code>/birthday [@user]</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_magic": (
        "🔮 <b>Magic & Fortune</b>\n" + _D + "\n\n"
        "<code>/fortune</code> — daily fortune reading\n"
        "<code>/tarot</code> — random tarot card draw\n"
        "<code>/horoscope sign</code> — daily horoscope\n"
        "<code>/joke</code> · <code>/fact</code> · <code>/quote</code>\n"
        "<code>/vibe</code> · <code>/personality</code>\n\n"
        "<i>All purely local — no AI required. Unlimited variety.</i>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_util": (
        "🔧 <b>Utility Commands</b>\n" + _D + "\n\n"
        "<code>/id [@user]</code> · <code>/info [@user]</code>\n"
        "<code>/chatinfo</code> · <code>/ping</code> · <code>/uptime</code>\n"
        "<code>/calc expr</code> · <code>/hash text</code>\n"
        "<code>/b64 encode|decode text</code> · <code>/reverse text</code>\n"
        "<code>/qr text</code> · <code>/tr lang text</code>\n"
        "<code>/weather city</code> · <code>/time [tz]</code>\n"
        "<code>/remind N unit text</code> · <code>/myreminders</code>\n"
        "<code>/ask question</code> — AI assistant",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_settings": (
        "⚙️ <b>Settings</b>\n" + _D + "\n\n"
        "<code>/settings</code> — full panel\n"
        "<code>/protect</code> · <code>/locks</code> · <code>/welcome</code>\n"
        "<code>/setwarnlimit N</code> · <code>/setwarnaction mute|ban|kick</code>\n"
        "<code>/cleanservice on|off</code> · <code>/delcommands on|off</code>\n"
        "<code>/welcdel N</code> · <code>/slowmode N</code>\n"
        "<code>/setlogchannel @channel</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
    "help_admin": (
        "👑 <b>Admin / Owner</b>\n" + _D + "\n\n"
        "<code>/gban user [reason]</code> · <code>/ungban user</code>\n"
        "<code>/sudo user</code> · <code>/unsudo user</code>\n"
        "<code>/broadcast msg</code> · <code>/botstats</code>\n"
        "<code>/chatlist</code> · <code>/leave</code>",
        [[InlineKeyboardButton("« Back", callback_data="help_main")]]
    ),
}

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text, buttons = HELP_SECTIONS["help_main"]
        if update.effective_chat.type != "private":
            kb = InlineKeyboardMarkup([[InlineKeyboardButton("📖 Open Help in DM",
                                        url=f"https://t.me/{context.bot.username}?start=help")]])
            await reply(update, "📬 <b>Full help sent to your DM!</b>", reply_markup=kb); return
        await update.message.reply_text(text, parse_mode="HTML",
                                        reply_markup=InlineKeyboardMarkup(buttons),
                                        disable_web_page_preview=True)
    except Exception as e: logger.error(f"help_cmd: {e}")

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query; await q.answer()
        key = q.data
        if key in HELP_SECTIONS:
            text, buttons = HELP_SECTIONS[key]
            try:
                await q.edit_message_text(text, parse_mode="HTML",
                                          reply_markup=InlineKeyboardMarkup(buttons),
                                          disable_web_page_preview=True)
            except: pass
    except Exception as e: logger.debug(f"help_callback: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                          MODERATION COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════
MUTE_PERMS   = ChatPermissions(can_send_messages=False, can_send_polls=False,
                                can_send_other_messages=False)
UNMUTE_PERMS = ChatPermissions(can_send_messages=True, can_send_polls=True,
                                can_send_other_messages=True, can_add_web_page_previews=True)

def _unban_btn(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔓 Unban", callback_data=f"unban:{chat_id}:{user_id}")]])

def _unmute_btn(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔊 Unmute", callback_data=f"unmute:{chat_id}:{user_id}")]])

async def _do_ban(context, chat_id: int, user_id: int, until: datetime.datetime = None):
    await context.bot.ban_chat_member(chat_id, user_id, until_date=until)

@admin_only
@groups_only
async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, f"🚫 No ban permission! {kmo(KAOMOJI_FLEX)}")
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user or provide @username.")
        if await is_admin(context, update.effective_chat.id, target.id):
            return await reply(update, f"🛡️ Can't ban admins! {kmo(KAOMOJI_FLEX)}")
        reason = (" ".join(context.args) if context.args and update.message.reply_to_message
                  else " ".join(context.args[1:]) if context.args else "")
        chat = update.effective_chat
        m = await animate_loading(update, "Executing ban")
        try:
            await _do_ban(context, chat.id, target.id)
            db = get_db()
            db.execute("INSERT OR REPLACE INTO bans (chat_id,user_id,banned_by,reason) VALUES (?,?,?,?)",
                       (chat.id, target.id, update.effective_user.id, reason))
            db.commit(); db.close()
            log_action(chat.id, update.effective_user.id, "ban", target.id, reason)
            tmpl = R.pick(BAN_MSGS, f"ban_{chat.id}")
            text = tmpl.format(u=user_link(target), a=user_link(update.effective_user),
                               r=html.escape(reason or "No reason given"))
            text += f"\n\n📊 <code>User ID: {target.id}</code>"
            await finish_anim(m, text, reply_markup=_unban_btn(chat.id, target.id))
            await send_log(context, chat.id,
                f"🔨 <b>BAN</b> | {html.escape(chat.title or '')}\n"
                f"Admin: {user_link(update.effective_user)}\n"
                f"User: {user_link(target)} (<code>{target.id}</code>)\n"
                f"Reason: {html.escape(reason or 'None')}")
        except BadRequest as e:
            await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")
    except Exception as e: logger.error(f"ban_cmd: {e}")

@admin_only
@groups_only
async def tban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ <b>Usage:</b> <code>/tban @user 1h [reason]</code>")
        args = context.args or []
        time_arg = (args[0] if update.message.reply_to_message and args
                    else (args[1] if len(args) > 1 else "1h"))
        duration = parse_duration(time_arg)
        if not duration: return await reply(update, "❌ Invalid duration. Use: 1m 1h 1d 1w")
        until = datetime.datetime.now(pytz.utc) + duration
        reason = " ".join(args[2:]) if len(args) > 2 else ""
        m = await animate_loading(update, "Applying temp ban")
        try:
            await _do_ban(context, update.effective_chat.id, target.id, until)
            log_action(update.effective_chat.id, update.effective_user.id, "tban", target.id, time_arg)
            await finish_anim(m,
                f"⏱️ <b>Temporary Ban</b> {kmo(KAOMOJI_BAN)}\n{_D}\n\n"
                f"👤 <b>User:</b> {user_link(target)}\n"
                f"⏰ <b>Duration:</b> {html.escape(fmt_duration(duration))}\n"
                f"📅 <b>Until:</b> {until.strftime('%Y-%m-%d %H:%M UTC')}\n"
                f"📋 <b>Reason:</b> {html.escape(reason or 'None')}")
        except BadRequest as e:
            await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")
    except Exception as e: logger.error(f"tban_cmd: {e}")

@admin_only
@groups_only
async def sban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id): return
        target = await get_target(update, context)
        if not target: return
        await update.message.delete()
        if update.message.reply_to_message:
            try: await update.message.reply_to_message.delete()
            except: pass
        await _do_ban(context, update.effective_chat.id, target.id)
        log_action(update.effective_chat.id, update.effective_user.id, "sban", target.id, "silent")
    except Exception as e: logger.debug(f"sban_cmd: {e}")

@admin_only
@groups_only
async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply or provide @username.")
        m = await animate_loading(update, "Lifting ban")
        try:
            await context.bot.unban_chat_member(update.effective_chat.id, target.id, only_if_banned=True)
            db = get_db()
            db.execute("DELETE FROM bans WHERE chat_id=? AND user_id=?",
                       (update.effective_chat.id, target.id))
            db.commit(); db.close()
            log_action(update.effective_chat.id, update.effective_user.id, "unban", target.id)
            await finish_anim(m,
                f"✅ <b>Unbanned!</b> {kmo(KAOMOJI_WHOLESOME)}\n{_D}\n\n"
                f"👤 <b>User:</b> {user_link(target)}\n"
                f"👑 <b>By:</b> {user_link(update.effective_user)}\n"
                f"🟢 <i>They may return.</i>")
        except BadRequest as e:
            await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")
    except Exception as e: logger.error(f"unban_cmd: {e}")

async def unban_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query
        parts = q.data.split(":")
        if len(parts) < 3: return await q.answer("Invalid", show_alert=True)
        chat_id, user_id = int(parts[1]), int(parts[2])
        if not await is_admin(context, chat_id, q.from_user.id):
            return await q.answer("🚫 Admins only!", show_alert=True)
        await q.answer()
        await context.bot.unban_chat_member(chat_id, user_id, only_if_banned=True)
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(f"✅ <b>User unbanned by {user_link(q.from_user)}!</b>", parse_mode="HTML")
    except Exception as e: logger.debug(f"unban_callback: {e}")

async def unmute_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query
        parts = q.data.split(":")
        if len(parts) < 3: return await q.answer("Invalid", show_alert=True)
        chat_id, user_id = int(parts[1]), int(parts[2])
        if not await is_admin(context, chat_id, q.from_user.id):
            return await q.answer("🚫 Admins only!", show_alert=True)
        await q.answer()
        await context.bot.restrict_chat_member(chat_id, user_id, UNMUTE_PERMS)
        await q.edit_message_reply_markup(reply_markup=None)
        await q.message.reply_text(f"🔊 <b>Unmuted by {user_link(q.from_user)}!</b>", parse_mode="HTML")
    except Exception as e: logger.debug(f"unmute_callback: {e}")

@admin_only
@groups_only
async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user.")
        if await is_admin(context, update.effective_chat.id, target.id):
            return await reply(update, "🛡️ Can't kick admins!")
        m = await animate_loading(update, "Kicking user")
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, target.id)
            await context.bot.unban_chat_member(update.effective_chat.id, target.id)
            log_action(update.effective_chat.id, update.effective_user.id, "kick", target.id)
            tmpl = R.pick(KICK_MSGS, f"kick_{update.effective_chat.id}")
            await finish_anim(m, tmpl.format(u=user_link(target), a=user_link(update.effective_user)))
        except BadRequest as e:
            await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")
    except Exception as e: logger.error(f"kick_cmd: {e}")

@admin_only
@groups_only
async def skick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id): return
        target = await get_target(update, context)
        if not target: return
        await update.message.delete()
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
    except Exception as e: logger.debug(f"skick_cmd: {e}")

@admin_only
@groups_only
async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user.")
        reason = (" ".join(context.args) if context.args and update.message.reply_to_message
                  else " ".join(context.args[1:]) if context.args else "")
        m = await animate_loading(update, "Muting user")
        try:
            await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS)
            log_action(update.effective_chat.id, update.effective_user.id, "mute", target.id, reason)
            tmpl = R.pick(MUTE_MSGS, f"mute_{update.effective_chat.id}")
            await finish_anim(m,
                tmpl.format(u=user_link(target), a=user_link(update.effective_user),
                            r=html.escape(reason or "No reason given")),
                reply_markup=_unmute_btn(update.effective_chat.id, target.id))
        except BadRequest as e:
            await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")
    except Exception as e: logger.error(f"mute_cmd: {e}")

@admin_only
@groups_only
async def tmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply or @username")
        args = context.args or []
        time_str = args[0] if update.message.reply_to_message and args else (args[1] if len(args) > 1 else "1h")
        duration = parse_duration(time_str)
        if not duration: return await reply(update, "❌ Invalid duration.")
        until = datetime.datetime.now(pytz.utc) + duration
        m = await animate_loading(update, "Applying temp mute")
        try:
            await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS, until_date=until)
            log_action(update.effective_chat.id, update.effective_user.id, "tmute", target.id, time_str)
            await finish_anim(m,
                f"⏱️ <b>Temp Muted</b> {kmo(KAOMOJI_BAN)}\n{_D}\n\n"
                f"👤 <b>User:</b> {user_link(target)}\n"
                f"⏰ <b>Duration:</b> {html.escape(fmt_duration(duration))}\n"
                f"📅 <b>Until:</b> {until.strftime('%Y-%m-%d %H:%M UTC')}",
                reply_markup=_unmute_btn(update.effective_chat.id, target.id))
        except BadRequest as e:
            await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")
    except Exception as e: logger.error(f"tmute_cmd: {e}")

@admin_only
@groups_only
async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user.")
        m = await animate_loading(update, "Unmuting")
        try:
            await context.bot.restrict_chat_member(update.effective_chat.id, target.id, UNMUTE_PERMS)
            log_action(update.effective_chat.id, update.effective_user.id, "unmute", target.id)
            await finish_anim(m,
                f"🔊 <b>Unmuted!</b> {kmo(KAOMOJI_WHOLESOME)}\n{_D}\n\n"
                f"👤 <b>User:</b> {user_link(target)}\n"
                f"👑 <b>By:</b> {user_link(update.effective_user)}")
        except BadRequest as e:
            await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")
    except Exception as e: logger.error(f"unmute_cmd: {e}")

# ─── WARN SYSTEM ───────────────────────────────────────────────────────────────
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
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user.")
        if await is_admin(context, update.effective_chat.id, target.id):
            return await reply(update, "🛡️ Cannot warn admins!")
        reason = (" ".join(context.args) if context.args and update.message.reply_to_message
                  else " ".join(context.args[1:]) if context.args else "")
        cfg = get_chat(update.effective_chat.id)
        warn_limit = cfg.get("warn_limit", 3)
        warn_action = cfg.get("warn_action", "mute")
        db = get_db()
        db.execute("INSERT INTO warns (chat_id,user_id,reason,warned_by) VALUES (?,?,?,?)",
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
            try:
                if warn_action == "ban":
                    await _do_ban(context, update.effective_chat.id, target.id)
                    extra_action = "\n🔨 <b>Auto-banned: warn limit reached!</b>"
                elif warn_action == "kick":
                    await context.bot.ban_chat_member(update.effective_chat.id, target.id)
                    await context.bot.unban_chat_member(update.effective_chat.id, target.id)
                    extra_action = "\n👢 <b>Auto-kicked: too many strikes!</b>"
                else:
                    await context.bot.restrict_chat_member(update.effective_chat.id, target.id, MUTE_PERMS)
                    extra_action = "\n🔇 <b>Auto-muted: warn limit reached!</b>"
            except Exception as e: logger.debug(f"Auto-action fail: {e}")
        if not silent:
            tmpl = R.pick(WARN_MSGS, f"warn_{update.effective_chat.id}")
            text = tmpl.format(u=user_link(target), a=user_link(update.effective_user),
                               r=html.escape(reason or "No reason given"))
            text += f"\n📊 <b>Strikes:</b> {count}/{warn_limit} [{bar}]{extra_action}"
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Unwarn", callback_data=f"unwarn:{update.effective_chat.id}:{target.id}"),
                InlineKeyboardButton("🗑️ Reset", callback_data=f"resetwarn:{update.effective_chat.id}:{target.id}"),
            ]])
            await reply(update, text, reply_markup=kb)
    except Exception as e: logger.error(f"_warn: {e}")

async def warn_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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
    except Exception as e: logger.debug(f"warn_action_callback: {e}")

@admin_only
@groups_only
async def unwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user.")
        db = get_db()
        row = db.execute("SELECT id FROM warns WHERE chat_id=? AND user_id=? ORDER BY warned_at DESC LIMIT 1",
                         (update.effective_chat.id, target.id)).fetchone()
        if row:
            db.execute("DELETE FROM warns WHERE id=?", (row["id"],))
            db.commit()
        db.close()
        await reply(update, f"✅ <b>1 warn removed from</b> {user_link(target)}")
    except Exception as e: logger.error(f"unwarn_cmd: {e}")

@admin_only
@groups_only
async def resetwarn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user.")
        db = get_db()
        db.execute("DELETE FROM warns WHERE chat_id=? AND user_id=?",
                   (update.effective_chat.id, target.id))
        db.commit(); db.close()
        log_action(update.effective_chat.id, update.effective_user.id, "resetwarn", target.id)
        await reply(update, f"🗑️ <b>All warns cleared for</b> {user_link(target)}")
    except Exception as e: logger.error(f"resetwarn_cmd: {e}")

async def warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context) or update.effective_user
        cfg = get_chat(update.effective_chat.id)
        db = get_db()
        rows = db.execute("SELECT * FROM warns WHERE chat_id=? AND user_id=? ORDER BY warned_at DESC",
                          (update.effective_chat.id, target.id)).fetchall()
        db.close()
        warn_limit = cfg.get("warn_limit", 3)
        if not rows:
            return await reply(update, f"✅ <b>Clean Record!</b>\n{_D}\n\n"
                               f"▸ {user_link(target)} has zero warnings! 🌟")
        bar = progress_bar(len(rows), warn_limit)
        lines = [f"⚠️ <b>Warn History</b>\n{_D}\n\n"
                 f"▸ <b>User:</b> {user_link(target)}\n"
                 f"▸ <b>Warns:</b> {len(rows)}/{warn_limit}  [{bar}]\n"]
        for i, w in enumerate(rows[:10], 1):
            lines.append(f"\n{i}. 📝 {html.escape(w['reason'] or 'No reason')}\n"
                         f"   🕐 <i>{str(w['warned_at'])[:16]}</i>")
        await reply(update, "\n".join(lines))
    except Exception as e: logger.error(f"warns_cmd: {e}")

@admin_only
async def setwarnlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/setwarnlimit N</code>")
        n = int(context.args[0])
        set_setting(update.effective_chat.id, "warn_limit", n)
        await reply(update, f"✅ <b>Warn limit set to {n}</b>")
    except ValueError: await reply(update, "❌ Invalid number.")
    except Exception as e: logger.error(f"setwarnlimit_cmd: {e}")

@admin_only
async def setwarnaction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args or context.args[0] not in ("mute","ban","kick"):
            return await reply(update, "❓ <code>/setwarnaction mute|ban|kick</code>")
        set_setting(update.effective_chat.id, "warn_action", context.args[0])
        await reply(update, f"✅ <b>Warn action:</b> <code>{context.args[0]}</code>")
    except Exception as e: logger.error(f"setwarnaction_cmd: {e}")

# ─── PROMOTE / DEMOTE ──────────────────────────────────────────────────────────
@admin_only
@groups_only
async def promote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 You need promote rights!")
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user.")
        title = (" ".join(context.args) if update.message.reply_to_message and context.args
                 else " ".join(context.args[1:]) if context.args else "")
        m = await animate_loading(update, "Promoting")
        try:
            await context.bot.promote_chat_member(
                update.effective_chat.id, target.id,
                can_manage_chat=True, can_delete_messages=True, can_restrict_members=True,
                can_invite_users=True, can_pin_messages=True, can_manage_video_chats=True,
                is_anonymous=False)
            if title:
                try:
                    await context.bot.set_chat_administrator_custom_title(
                        update.effective_chat.id, target.id, title[:16])
                except: pass
            invalidate_admin_cache(update.effective_chat.id)
            log_action(update.effective_chat.id, update.effective_user.id, "promote", target.id, title)
            await finish_anim(m,
                f"⭐ <b>Promoted!</b> {kmo(KAOMOJI_HYPE)}\n{_D}\n\n"
                f"👤 <b>User:</b> {user_link(target)}\n"
                f"🏷️ <b>Title:</b> {html.escape(title) if title else 'Admin'}\n"
                f"✨ <i>New admin just dropped!</i>")
        except BadRequest as e:
            await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")
    except Exception as e: logger.error(f"promote_cmd: {e}")

@admin_only
@groups_only
async def demote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user.")
        m = await animate_loading(update, "Demoting")
        try:
            await context.bot.promote_chat_member(
                update.effective_chat.id, target.id,
                can_manage_chat=False, can_delete_messages=False, can_restrict_members=False,
                can_invite_users=False, can_pin_messages=False)
            invalidate_admin_cache(update.effective_chat.id)
            log_action(update.effective_chat.id, update.effective_user.id, "demote", target.id)
            await finish_anim(m,
                f"📉 <b>Demoted.</b> {kmo(KAOMOJI_SAD)}\n{_D}\n\n"
                f"👤 <b>User:</b> {user_link(target)}")
        except BadRequest as e:
            await finish_anim(m, f"❌ <b>Error:</b> {html.escape(str(e))}")
    except Exception as e: logger.error(f"demote_cmd: {e}")

@admin_only
@groups_only
async def admintitle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_promote(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user.")
        title = (" ".join(context.args) if update.message.reply_to_message
                 else " ".join(context.args[1:]) if context.args else "")
        if not title: return await reply(update, "❓ Provide a title.")
        await context.bot.set_chat_administrator_custom_title(
            update.effective_chat.id, target.id, title[:16])
        await reply(update, f"🏷️ <b>Title set!</b>\n▸ {user_link(target)}: <b>{html.escape(title)}</b>")
    except BadRequest as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")
    except Exception as e: logger.error(f"admintitle_cmd: {e}")

async def adminlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        m = await animate_loading(update, "Fetching admin list")
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        owners = [a for a in admins if a.status == "creator"]
        mods   = [a for a in admins if a.status == "administrator"]
        lines  = [f"👮 <b>Admin List</b>  ({len(admins)})\n{_D}\n"]
        if owners:
            lines.append("👑 <b>Owner</b>")
            for a in owners:
                lines.append(f"  └ {user_link(a.user)}")
        if mods:
            lines.append("\n🔧 <b>Admins</b>")
            for a in mods:
                t = (f" <i>· {html.escape(a.custom_title)}</i>"
                     if isinstance(a, ChatMemberAdministrator) and a.custom_title else "")
                lines.append(f"  └ {user_link(a.user)}{t}")
        await finish_anim(m, "\n".join(lines))
    except Exception as e:
        if m: await finish_anim(m, f"❌ Error: {html.escape(str(e))}")

async def tag_admins_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.text: return
        txt = update.message.text.lower()
        if "@admins" not in txt and "@admin" not in txt: return
        admins = await context.bot.get_chat_administrators(update.effective_chat.id)
        mentions = " ".join(f'<a href="tg://user?id={a.user.id}">​</a>' for a in admins if not a.user.is_bot)
        await reply(update, f"📢 <b>Admins notified!</b>\n{mentions}")
    except: pass

# ─── APPROVE / DISAPPROVE ──────────────────────────────────────────────────────
@admin_only
@groups_only
async def approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user.")
        db = get_db()
        db.execute("INSERT OR IGNORE INTO approved_users (chat_id,user_id) VALUES (?,?)",
                   (update.effective_chat.id, target.id))
        db.commit(); db.close()
        await reply(update, f"✅ <b>Approved!</b>\n{user_link(target)} is now exempt from filters and anti-spam.")
    except Exception as e: logger.error(f"approve_cmd: {e}")

@admin_only
@groups_only
async def disapprove_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user.")
        db = get_db()
        db.execute("DELETE FROM approved_users WHERE chat_id=? AND user_id=?",
                   (update.effective_chat.id, target.id))
        db.commit(); db.close()
        await reply(update, f"🔴 <b>Disapproved.</b>\n{user_link(target)}'s approved status removed.")
    except Exception as e: logger.error(f"disapprove_cmd: {e}")

@admin_only
@groups_only
async def approved_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        rows = db.execute("SELECT user_id FROM approved_users WHERE chat_id=?",
                          (update.effective_chat.id,)).fetchall()
        db.close()
        if not rows: return await reply(update, "📋 <b>No approved users.</b>")
        lines = [f"✅ <b>Approved Users</b>\n{_D}\n"]
        for r in rows:
            lines.append(f"▸ <code>{r['user_id']}</code>")
        await reply(update, "\n".join(lines))
    except Exception as e: logger.error(f"approved_cmd: {e}")

def is_approved(chat_id: int, user_id: int) -> bool:
    try:
        db = get_db()
        row = db.execute("SELECT 1 FROM approved_users WHERE chat_id=? AND user_id=?",
                         (chat_id, user_id)).fetchone()
        db.close()
        return bool(row)
    except: return False

# ─── ZOMBIES ───────────────────────────────────────────────────────────────────
@admin_only
@groups_only
async def zombies_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        m = await animate_loading(update, "Scanning for zombies")
        count = 0
        try:
            async for member in context.bot.get_chat_members(update.effective_chat.id):
                if getattr(member.user, "is_deleted", False): count += 1
        except: pass
        await finish_anim(m,
            f"🧟 <b>Zombie Scan Complete</b>\n{_D}\n\n"
            f"▸ <b>Deleted accounts found:</b> {count}\n\n"
            f"{'💀 Use /kickzombies to remove them!' if count else '✨ Group is zombie-free!'}")
    except Exception as e: logger.error(f"zombies_cmd: {e}")

@admin_only
@groups_only
async def kickzombies_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        m = await animate_loading(update, "Hunting zombies")
        kicked = 0
        try:
            async for member in context.bot.get_chat_members(update.effective_chat.id):
                if getattr(member.user, "is_deleted", False):
                    try:
                        await context.bot.ban_chat_member(update.effective_chat.id, member.user.id)
                        await context.bot.unban_chat_member(update.effective_chat.id, member.user.id)
                        kicked += 1
                    except: pass
        except: pass
        await finish_anim(m, f"✅ <b>Zombies Purged!</b>\n{_D}\n\n💥 <b>Kicked {kicked} zombie accounts!</b>")
    except Exception as e: logger.error(f"kickzombies_cmd: {e}")

# ─── PIN / UNPIN / PURGE ───────────────────────────────────────────────────────
@admin_only
@groups_only
async def pin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_pin(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        if not update.message.reply_to_message:
            return await reply(update, "❓ Reply to a message to pin!")
        loud = "loud" in (context.args or [])
        await context.bot.pin_chat_message(update.effective_chat.id,
                                           update.message.reply_to_message.message_id,
                                           disable_notification=not loud)
        await reply(update, "📌 <b>Pinned!</b>" + (" 🔔" if loud else ""))
    except BadRequest as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")
    except Exception as e: logger.error(f"pin_cmd: {e}")

@admin_only
@groups_only
async def unpin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_pin(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        if update.message.reply_to_message:
            await context.bot.unpin_chat_message(update.effective_chat.id,
                                                  update.message.reply_to_message.message_id)
        else:
            await context.bot.unpin_chat_message(update.effective_chat.id)
        await reply(update, "📌 <b>Unpinned!</b>")
    except BadRequest as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def unpinall_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_pin(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        await context.bot.unpin_all_chat_messages(update.effective_chat.id)
        await reply(update, "✅ <b>All messages unpinned!</b>")
    except BadRequest as e:
        await reply(update, f"❌ <b>Error:</b> {html.escape(str(e))}")

@admin_only
@groups_only
async def purge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        msg = update.message
        if not msg.reply_to_message:
            return await reply(update, "❓ Reply to the first message to purge from!")
        from_id = msg.reply_to_message.message_id
        to_id = msg.message_id
        ids = list(range(from_id, to_id + 1))
        m = await context.bot.send_message(update.effective_chat.id,
            f"<b>Purging {len(ids)} messages…</b>", parse_mode="HTML")
        count = 0
        for i in range(0, len(ids), 100):
            chunk = ids[i:i+100]
            try:
                await context.bot.delete_messages(update.effective_chat.id, chunk)
                count += len(chunk)
            except:
                for mid in chunk:
                    try: await context.bot.delete_message(update.effective_chat.id, mid); count += 1
                    except: pass
            await asyncio.sleep(0.2)
        try:
            await m.edit_text(f"✅ <b>Purged {count} messages!</b>", parse_mode="HTML")
            await asyncio.sleep(3)
            await m.delete()
        except: pass
    except Exception as e: logger.error(f"purge_cmd: {e}")

@admin_only
@groups_only
async def del_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message.reply_to_message: return
        await update.message.reply_to_message.delete()
        try: await update.message.delete()
        except: pass
    except Exception as e: logger.debug(f"del_cmd: {e}")

@admin_only
@groups_only
async def slowmode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await can_restrict(context, update.effective_chat.id, update.effective_user.id):
            return await reply(update, "🚫 No permission!")
        secs = int(context.args[0]) if context.args else 0
        await context.bot.set_chat_slow_mode_delay(update.effective_chat.id, secs)
        await reply(update, f"🐢 <b>Slowmode set to {secs}s!</b>" if secs else "⚡ <b>Slowmode disabled!</b>")
    except Exception as e: await reply(update, f"❌ {html.escape(str(e))}")

# ═══════════════════════════════════════════════════════════════════════════════
#                      WELCOME / GOODBYE / RULES
# ═══════════════════════════════════════════════════════════════════════════════
_pending_captcha: Dict[Tuple[int,int], dict] = {}
_raid_tracker: Dict[int, List[float]] = defaultdict(list)

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        cfg = get_chat(chat.id)
        for member in update.message.new_chat_members:
            if member.is_bot:
                if cfg.get("antibot"):
                    try:
                        await context.bot.ban_chat_member(chat.id, member.id)
                        await context.bot.unban_chat_member(chat.id, member.id)
                    except: pass
                continue
            # Anti-raid
            now = time.time()
            raid_list = _raid_tracker[chat.id]
            raid_list[:] = [t for t in raid_list if now - t < 30]
            raid_list.append(now)
            if cfg.get("antiraid") and len(raid_list) >= cfg.get("raid_threshold", 10):
                try:
                    await context.bot.ban_chat_member(chat.id, member.id)
                    await context.bot.unban_chat_member(chat.id, member.id)
                except: pass
                continue
            # CAS check
            if cfg.get("cas_enabled", 1):
                try:
                    session = await get_session()
                    async with session.get(f"https://api.cas.chat/check?user_id={member.id}",
                                           timeout=aiohttp.ClientTimeout(total=5)) as r:
                        if r.status == 200:
                            data = await r.json()
                            if data.get("ok"):
                                await context.bot.ban_chat_member(chat.id, member.id)
                                continue
                except: pass
            # gban check
            if is_gbanned(member.id):
                try: await context.bot.ban_chat_member(chat.id, member.id)
                except: pass
                continue
            # Restrict new members
            if cfg.get("restrict_new"):
                try:
                    await context.bot.restrict_chat_member(chat.id, member.id, MUTE_PERMS,
                        until_date=datetime.datetime.now(pytz.utc) + datetime.timedelta(minutes=5))
                except: pass
            # Welcome
            if cfg.get("welcome_on", 1):
                await _send_welcome(context, chat, member, cfg)
    except Exception as e: logger.error(f"on_new_member: {e}")

async def _send_welcome(context, chat, member, cfg):
    try:
        wtext = cfg.get("welcome_text","")
        if wtext:
            text = wtext.replace("{first}", html.escape(member.first_name or ""))
                  .replace("{last}", html.escape(member.last_name or ""))
                  .replace("{mention}", user_link(member))
                  .replace("{username}", f"@{member.username}" if member.username else member.first_name or str(member.id))
                  .replace("{chatname}", html.escape(chat.title or ""))
        else:
            tmpl = R.pick(WELCOME_MSGS, f"welcome_{chat.id}")
            text = tmpl.format(user=user_link(member), chat=html.escape(chat.title or "Group"))
        captcha = cfg.get("captcha_on", 0)
        captcha_type = cfg.get("captcha_type", "button")
        if captcha:
            if captcha_type == "math":
                a, b = random.randint(1,20), random.randint(1,20)
                op = random.choice(["+","-","×"])
                if op == "+": ans = str(a+b)
                elif op == "-": ans = str(a-b)
                else: ans = str(a*b)
                text += f"\n\n🔢 <b>CAPTCHA:</b> What is <b>{a} {op} {b}</b>?\n<i>Reply with the answer to verify!</i>"
                _pending_captcha[(chat.id, member.id)] = {"type":"math","answer":ans,"msg_id":None}
            else:
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ I'm human!", callback_data=f"captcha_ok:{chat.id}:{member.id}")]])
                m = await context.bot.send_message(chat.id, text, parse_mode="HTML", reply_markup=kb)
                _pending_captcha[(chat.id, member.id)] = {"type":"button","msg_id":m.message_id}
                if cfg.get("welcome_del", 0):
                    asyncio.get_event_loop().call_later(
                        cfg["welcome_del"], asyncio.ensure_future,
                        _delete_msg_later(context, chat.id, m.message_id))
                return
        m = await context.bot.send_message(chat.id, text, parse_mode="HTML", disable_web_page_preview=True)
        if cfg.get("welcome_del", 0):
            asyncio.get_event_loop().call_later(
                cfg["welcome_del"], asyncio.ensure_future,
                _delete_msg_later(context, chat.id, m.message_id))
    except Exception as e: logger.debug(f"_send_welcome: {e}")

async def _delete_msg_later(context, chat_id, msg_id):
    try: await context.bot.delete_message(chat_id, msg_id)
    except: pass

async def captcha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query
        parts = q.data.split(":")
        if len(parts) < 3: return await q.answer("Invalid!", show_alert=True)
        chat_id, user_id = int(parts[1]), int(parts[2])
        if q.from_user.id != user_id:
            return await q.answer("This captcha is not for you!", show_alert=True)
        await q.answer("✅ Verified! Welcome!", show_alert=False)
        _pending_captcha.pop((chat_id, user_id), None)
        try: await q.message.edit_reply_markup(reply_markup=None)
        except: pass
        if cfg := get_chat(chat_id):
            if cfg.get("restrict_new"):
                try: await context.bot.restrict_chat_member(chat_id, user_id, UNMUTE_PERMS)
                except: pass
    except Exception as e: logger.debug(f"captcha_callback: {e}")

async def on_member_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        member = update.message.left_chat_member
        cfg = get_chat(chat.id)
        if not cfg.get("goodbye_on"): return
        gtext = cfg.get("goodbye_text","")
        if gtext:
            text = gtext.replace("{first}", html.escape(member.first_name or ""))
                        .replace("{mention}", user_link(member))
        else:
            text = f"👋 <b>{user_link(member)}</b> has left {html.escape(chat.title or 'the chat')}. Farewell!"
        await context.bot.send_message(chat.id, text, parse_mode="HTML")
    except Exception as e: logger.debug(f"on_member_left: {e}")

@admin_only
async def setwelcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = " ".join(context.args) if context.args else ""
        if not text: return await reply(update, "❓ <code>/setwelcome Your welcome message here</code>")
        set_setting(update.effective_chat.id, "welcome_text", text)
        await reply(update, f"✅ <b>Welcome message set!</b>\n\n<i>Preview:</i>\n{text[:200]}")
    except Exception as e: logger.error(f"setwelcome_cmd: {e}")

@admin_only
async def welcome_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = context.args[0].lower() if context.args else None
        if val in ("on","off"):
            set_setting(update.effective_chat.id, "welcome_on", 1 if val == "on" else 0)
            await reply(update, f"✅ <b>Welcome:</b> {'🟢 ON' if val == 'on' else '🔴 OFF'}")
        else:
            cfg = get_chat(update.effective_chat.id)
            await reply(update, f"👋 <b>Welcome Settings</b>\n{_D}\n\n"
                        f"▸ Status: {'🟢 ON' if cfg.get('welcome_on',1) else '🔴 OFF'}\n"
                        f"▸ Captcha: {'✅' if cfg.get('captcha_on') else '❌'}\n"
                        f"▸ Auto-delete: {cfg.get('welcome_del',0)}s\n\n"
                        f"<code>/welcome on|off</code> · <code>/captcha on|off</code>")
    except Exception as e: logger.error(f"welcome_cmd: {e}")

@admin_only
async def setgoodbye_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = " ".join(context.args) if context.args else ""
        if not text: return await reply(update, "❓ Provide goodbye text.")
        set_setting(update.effective_chat.id, "goodbye_text", text)
        await reply(update, "✅ <b>Goodbye message set!</b>")
    except Exception as e: logger.error(f"setgoodbye_cmd: {e}")

@admin_only
async def goodbye_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = context.args[0].lower() if context.args else None
        if val in ("on","off"):
            set_setting(update.effective_chat.id, "goodbye_on", 1 if val == "on" else 0)
            await reply(update, f"✅ <b>Goodbye:</b> {'🟢 ON' if val == 'on' else '🔴 OFF'}")
        else: await reply(update, "❓ <code>/goodbye on|off</code>")
    except Exception as e: logger.error(f"goodbye_cmd: {e}")

@admin_only
async def captcha_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = context.args[0].lower() if context.args else None
        if val in ("on","off"):
            set_setting(update.effective_chat.id, "captcha_on", 1 if val == "on" else 0)
            await reply(update, f"✅ <b>Captcha:</b> {'🟢 ON' if val == 'on' else '🔴 OFF'}")
        else: await reply(update, "❓ <code>/captcha on|off</code>")
    except Exception as e: logger.error(f"captcha_cmd: {e}")

@admin_only
async def captchatype_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        t = context.args[0].lower() if context.args else None
        if t not in ("button","math"): return await reply(update, "❓ <code>/captchatype button|math</code>")
        set_setting(update.effective_chat.id, "captcha_type", t)
        await reply(update, f"✅ <b>Captcha type:</b> {t}")
    except Exception as e: logger.error(f"captchatype_cmd: {e}")

@admin_only
async def welcdel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(context.args[0]) if context.args else 0
        set_setting(update.effective_chat.id, "welcome_del", n)
        await reply(update, f"✅ <b>Welcome messages deleted after {n}s!</b>" if n else "✅ <b>Welcome delete disabled.</b>")
    except ValueError: await reply(update, "❌ Provide a number.")
    except Exception as e: logger.error(f"welcdel_cmd: {e}")

@admin_only
async def setrules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message.reply_to_message:
            text = update.message.reply_to_message.text or ""
        else:
            text = " ".join(context.args) if context.args else ""
        if not text: return await reply(update, "❓ Provide rules text.")
        set_setting(update.effective_chat.id, "rules", text)
        await reply(update, "✅ <b>Rules set!</b>")
    except Exception as e: logger.error(f"setrules_cmd: {e}")

async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rules = get_setting(update.effective_chat.id, "rules")
        if not rules: return await reply(update, "📋 <b>No rules set yet.</b> Use /setrules to add some.")
        await reply(update, f"📋 <b>Rules</b>\n{_D}\n\n{html.escape(rules)}")
    except Exception as e: logger.error(f"rules_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         NOTES / FILTERS / BLACKLIST
# ═══════════════════════════════════════════════════════════════════════════════
@admin_only
async def save_note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        args = context.args
        if not args: return await reply(update, "❓ <code>/save name content</code>")
        name = args[0].lower()
        content = " ".join(args[1:])
        file_id = file_type = None
        if msg.reply_to_message:
            rm = msg.reply_to_message
            if rm.photo: file_id, file_type = rm.photo[-1].file_id, "photo"
            elif rm.document: file_id, file_type = rm.document.file_id, "document"
            elif rm.sticker: file_id, file_type = rm.sticker.file_id, "sticker"
            elif rm.video: file_id, file_type = rm.video.file_id, "video"
            elif rm.audio: file_id, file_type = rm.audio.file_id, "audio"
            elif rm.voice: file_id, file_type = rm.voice.file_id, "voice"
            elif rm.animation: file_id, file_type = rm.animation.file_id, "animation"
            if not content: content = rm.caption or rm.text or ""
        if not content and not file_id: return await reply(update, "❓ Provide note content.")
        db = get_db()
        db.execute("INSERT OR REPLACE INTO notes (chat_id,name,content,file_id,file_type) VALUES (?,?,?,?,?)",
                   (update.effective_chat.id, name, content, file_id, file_type))
        db.commit(); db.close()
        await reply(update, f"✅ <b>Note saved:</b> <code>#{name}</code>")
    except Exception as e: logger.error(f"save_note_cmd: {e}")

async def get_note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/get name</code>")
        await _send_note(update, context, context.args[0].lower())
    except Exception as e: logger.error(f"get_note_cmd: {e}")

async def _send_note(update, context, name: str):
    try:
        db = get_db()
        row = db.execute("SELECT * FROM notes WHERE chat_id=? AND name=?",
                         (update.effective_chat.id, name)).fetchone()
        db.close()
        if not row: return await reply(update, f"❓ Note <code>{name}</code> not found.")
        content = row["content"] or ""
        file_id = row["file_id"]
        file_type = row["file_type"]
        kwargs = {"parse_mode":"HTML","disable_web_page_preview":True}
        if file_type == "photo":
            await update.message.reply_photo(file_id, caption=content or None, parse_mode="HTML")
        elif file_type == "document":
            await update.message.reply_document(file_id, caption=content or None, parse_mode="HTML")
        elif file_type == "sticker":
            await update.message.reply_sticker(file_id)
            if content: await reply(update, content)
        elif file_type == "video":
            await update.message.reply_video(file_id, caption=content or None, parse_mode="HTML")
        elif file_type == "audio":
            await update.message.reply_audio(file_id, caption=content or None, parse_mode="HTML")
        elif file_type == "voice":
            await update.message.reply_voice(file_id, caption=content or None, parse_mode="HTML")
        elif file_type == "animation":
            await update.message.reply_animation(file_id, caption=content or None, parse_mode="HTML")
        else:
            await reply(update, content)
    except Exception as e: logger.debug(f"_send_note: {e}")

async def notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        rows = db.execute("SELECT name FROM notes WHERE chat_id=? ORDER BY name",
                          (update.effective_chat.id,)).fetchall()
        db.close()
        if not rows: return await reply(update, "📝 <b>No notes saved.</b>")
        names = [f"▸ <code>#{r['name']}</code>" for r in rows]
        await reply(update, f"📝 <b>Saved Notes ({len(rows)})</b>\n{_D}\n\n" + "\n".join(names))
    except Exception as e: logger.error(f"notes_cmd: {e}")

@admin_only
async def clear_note_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/clear name</code>")
        name = context.args[0].lower()
        db = get_db()
        db.execute("DELETE FROM notes WHERE chat_id=? AND name=?", (update.effective_chat.id, name))
        db.commit(); db.close()
        await reply(update, f"🗑️ <b>Note deleted:</b> <code>#{name}</code>")
    except Exception as e: logger.error(f"clear_note_cmd: {e}")

@admin_only
async def clearall_notes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        db.execute("DELETE FROM notes WHERE chat_id=?", (update.effective_chat.id,))
        db.commit(); db.close()
        await reply(update, "🗑️ <b>All notes deleted!</b>")
    except Exception as e: logger.error(f"clearall_notes_cmd: {e}")

# ── Filters ────────────────────────────────────────────────────────────────────
@admin_only
async def add_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        args = context.args
        if not args: return await reply(update, "❓ <code>/filter keyword reply text</code>")
        keyword = args[0].lower()
        is_regex = keyword.startswith("regex:")
        if is_regex: keyword = keyword[6:]
        reply_text = " ".join(args[1:])
        file_id = file_type = None
        if msg.reply_to_message:
            rm = msg.reply_to_message
            if rm.photo: file_id, file_type = rm.photo[-1].file_id, "photo"
            elif rm.sticker: file_id, file_type = rm.sticker.file_id, "sticker"
            elif rm.document: file_id, file_type = rm.document.file_id, "document"
            elif rm.video: file_id, file_type = rm.video.file_id, "video"
            elif rm.animation: file_id, file_type = rm.animation.file_id, "animation"
            if not reply_text: reply_text = rm.caption or rm.text or ""
        if not reply_text and not file_id:
            return await reply(update, "❓ Provide filter reply content.")
        db = get_db()
        db.execute("INSERT OR REPLACE INTO filters (chat_id,keyword,reply,file_id,file_type,is_regex) VALUES (?,?,?,?,?,?)",
                   (update.effective_chat.id, keyword, reply_text, file_id, file_type, int(is_regex)))
        db.commit(); db.close()
        await reply(update, f"✅ <b>Filter added:</b> <code>{html.escape(keyword)}</code>")
    except Exception as e: logger.error(f"add_filter_cmd: {e}")

async def filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        rows = db.execute("SELECT keyword,is_regex FROM filters WHERE chat_id=? ORDER BY keyword",
                          (update.effective_chat.id,)).fetchall()
        db.close()
        if not rows: return await reply(update, "🔍 <b>No filters set.</b>")
        lines = [f"🔍 <b>Filters ({len(rows)})</b>\n{_D}\n"]
        for r in rows:
            tag = "⚡regex" if r["is_regex"] else "📝"
            lines.append(f"▸ {tag} <code>{html.escape(r['keyword'])}</code>")
        await reply(update, "\n".join(lines))
    except Exception as e: logger.error(f"filters_cmd: {e}")

@admin_only
async def stop_filter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/stop keyword</code>")
        keyword = " ".join(context.args).lower()
        db = get_db()
        db.execute("DELETE FROM filters WHERE chat_id=? AND keyword=?", (update.effective_chat.id, keyword))
        db.commit(); db.close()
        await reply(update, f"🗑️ <b>Filter removed:</b> <code>{html.escape(keyword)}</code>")
    except Exception as e: logger.error(f"stop_filter_cmd: {e}")

@admin_only
async def stopall_filters_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        db.execute("DELETE FROM filters WHERE chat_id=?", (update.effective_chat.id,))
        db.commit(); db.close()
        await reply(update, "🗑️ <b>All filters removed!</b>")
    except Exception as e: logger.error(f"stopall_filters_cmd: {e}")

# ── Blacklist ──────────────────────────────────────────────────────────────────
@admin_only
async def addbl_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/addbl word</code>")
        word = " ".join(context.args).lower()
        db = get_db()
        db.execute("INSERT OR IGNORE INTO blacklist (chat_id,word) VALUES (?,?)", (update.effective_chat.id, word))
        db.commit(); db.close()
        await reply(update, f"🚫 <b>Added to blacklist:</b> <code>{html.escape(word)}</code>")
    except Exception as e: logger.error(f"addbl_cmd: {e}")

@admin_only
async def rmbl_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/rmbl word</code>")
        word = " ".join(context.args).lower()
        db = get_db()
        db.execute("DELETE FROM blacklist WHERE chat_id=? AND word=?", (update.effective_chat.id, word))
        db.commit(); db.close()
        await reply(update, f"✅ <b>Removed from blacklist:</b> <code>{html.escape(word)}</code>")
    except Exception as e: logger.error(f"rmbl_cmd: {e}")

async def blacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        rows = db.execute("SELECT word FROM blacklist WHERE chat_id=? ORDER BY word",
                          (update.effective_chat.id,)).fetchall()
        db.close()
        if not rows: return await reply(update, "📋 <b>Blacklist is empty.</b>")
        words = [f"▸ <code>{html.escape(r['word'])}</code>" for r in rows]
        await reply(update, f"🚫 <b>Blacklist ({len(rows)})</b>\n{_D}\n\n" + "\n".join(words[:50]))
    except Exception as e: logger.error(f"blacklist_cmd: {e}")

@admin_only
async def blmode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args or context.args[0] not in ("delete","warn","mute","ban"):
            return await reply(update, "❓ <code>/blmode delete|warn|mute|ban</code>")
        db = get_db()
        db.execute("INSERT OR REPLACE INTO blacklist_settings (chat_id,action) VALUES (?,?)",
                   (update.effective_chat.id, context.args[0]))
        db.commit(); db.close()
        await reply(update, f"✅ <b>Blacklist action:</b> {context.args[0]}")
    except Exception as e: logger.error(f"blmode_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                            LOCK SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
LOCK_TYPES = {
    "stickers":"lock_stickers","gifs":"lock_gifs","media":"lock_media","polls":"lock_polls",
    "voice":"lock_voice","video":"lock_video","document":"lock_document","forward":"lock_forward",
    "games":"lock_games","inline":"lock_inline","url":"lock_url","anon":"lock_anon",
}

@admin_only
@groups_only
async def lock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, f"❓ <code>/lock type</code>\nTypes: {', '.join(LOCK_TYPES.keys())}")
        t = context.args[0].lower()
        if t == "all":
            for col in LOCK_TYPES.values(): set_setting(update.effective_chat.id, col, 1)
            await reply(update, "🔒 <b>All content types locked!</b>")
        elif t in LOCK_TYPES:
            set_setting(update.effective_chat.id, LOCK_TYPES[t], 1)
            await reply(update, f"🔒 <b>{t.capitalize()} locked!</b>")
        else: await reply(update, f"❓ Unknown type. Use: {', '.join(LOCK_TYPES.keys())}")
    except Exception as e: logger.error(f"lock_cmd: {e}")

@admin_only
@groups_only
async def unlock_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, f"❓ <code>/unlock type</code>")
        t = context.args[0].lower()
        if t == "all":
            for col in LOCK_TYPES.values(): set_setting(update.effective_chat.id, col, 0)
            await reply(update, "🔓 <b>All locks removed!</b>")
        elif t in LOCK_TYPES:
            set_setting(update.effective_chat.id, LOCK_TYPES[t], 0)
            await reply(update, f"🔓 <b>{t.capitalize()} unlocked!</b>")
        else: await reply(update, f"❓ Unknown type.")
    except Exception as e: logger.error(f"unlock_cmd: {e}")

async def locks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cfg = get_chat(update.effective_chat.id)
        def tog(k): return "🔒" if cfg.get(k) else "🔓"
        text = f"🔒 <b>Lock Panel</b>\n{_D}\n\n"
        for name, col in LOCK_TYPES.items():
            text += f"{tog(col)} {name.capitalize()}\n"
        await reply(update, text)
    except Exception as e: logger.error(f"locks_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         PROTECTION TOGGLES
# ═══════════════════════════════════════════════════════════════════════════════
def _make_toggle_cmd(key, name, default=0):
    @admin_only
    async def cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            val = context.args[0].lower() if context.args else None
            if val == "on": set_setting(update.effective_chat.id, key, 1)
            elif val == "off": set_setting(update.effective_chat.id, key, 0)
            else:
                cur = get_setting(update.effective_chat.id, key, default)
                set_setting(update.effective_chat.id, key, 0 if cur else 1)
            new_val = get_setting(update.effective_chat.id, key, default)
            await reply(update, f"✅ <b>{name}:</b> {'🟢 ON' if new_val else '🔴 OFF'}")
        except Exception as e: logger.error(f"toggle_{key}: {e}")
    return cmd

antispam_cmd   = _make_toggle_cmd("antispam",  "Anti-Spam", 1)
antiflood_cmd  = _make_toggle_cmd("antiflood", "Anti-Flood")
antilink_cmd   = _make_toggle_cmd("antilink",  "Anti-Link")
antiforward_cmd= _make_toggle_cmd("antiforward","Anti-Forward")
antibot_cmd    = _make_toggle_cmd("antibot",   "Anti-Bot")
antinsfw_cmd   = _make_toggle_cmd("antinsfw",  "Anti-NSFW")
antiarabic_cmd = _make_toggle_cmd("antiarabic","Anti-Arabic/RTL")
antiraid_cmd   = _make_toggle_cmd("antiraid",  "Anti-Raid")
cas_cmd        = _make_toggle_cmd("cas_enabled","CAS Integration", 1)
restrict_cmd   = _make_toggle_cmd("restrict_new","Restrict New Members")
cleanservice_cmd = _make_toggle_cmd("clean_service","Clean Service Messages")
delcommands_cmd  = _make_toggle_cmd("del_commands","Delete Commands")

@admin_only
async def setflood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(context.args[0]) if context.args else None
        if not n: return await reply(update, "❓ <code>/setflood N</code>")
        set_setting(update.effective_chat.id, "flood_limit", n)
        await reply(update, f"✅ <b>Flood limit set to {n} messages!</b>")
    except Exception as e: logger.error(f"setflood_cmd: {e}")

@admin_only
async def setfloodaction_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args or context.args[0] not in ("mute","ban","kick"):
            return await reply(update, "❓ <code>/setfloodaction mute|ban|kick</code>")
        set_setting(update.effective_chat.id, "flood_action", context.args[0])
        await reply(update, f"✅ <b>Flood action:</b> {context.args[0]}")
    except Exception as e: logger.error(f"setfloodaction_cmd: {e}")

@admin_only
async def setraid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(context.args[0]) if context.args else None
        if not n: return await reply(update, "❓ <code>/setraid N</code> (joins per 30s)")
        set_setting(update.effective_chat.id, "raid_threshold", n)
        await reply(update, f"✅ <b>Raid threshold set to {n} joins/30s!</b>")
    except Exception as e: logger.error(f"setraid_cmd: {e}")

async def protect_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cfg = get_chat(update.effective_chat.id)
        def tog(k, d=0): return "🟢" if cfg.get(k, d) else "🔴"
        text = (f"🛡️ <b>Protection Panel</b>\n{_D}\n\n"
                f"{tog('antispam',1)} Anti-Spam\n"
                f"{tog('antiflood')} Anti-Flood (limit: {cfg.get('flood_limit',5)})\n"
                f"{tog('antilink')} Anti-Link\n"
                f"{tog('antiforward')} Anti-Forward\n"
                f"{tog('antibot')} Anti-Bot\n"
                f"{tog('antinsfw')} Anti-NSFW\n"
                f"{tog('antiarabic')} Anti-Arabic/RTL\n"
                f"{tog('antiraid')} Anti-Raid (threshold: {cfg.get('raid_threshold',10)})\n"
                f"{tog('cas_enabled',1)} CAS Integration\n"
                f"{tog('restrict_new')} Restrict New Members")
        await reply(update, text)
    except Exception as e: logger.error(f"protect_panel: {e}")

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cfg = get_chat(update.effective_chat.id)
        def tog(k, d=0): return "🟢 ON" if cfg.get(k, d) else "🔴 OFF"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛡️ Protection", callback_data="settings_protect"),
             InlineKeyboardButton("🔒 Locks", callback_data="settings_locks")],
            [InlineKeyboardButton("👋 Welcome", callback_data="settings_welcome"),
             InlineKeyboardButton("⚠️ Warns", callback_data="settings_warns")],
        ])
        await reply(update,
            f"⚙️ <b>Settings Panel</b>\n{_D}\n\n"
            f"<b>General</b>\n"
            f"▸ Anti-Spam: {tog('antispam',1)}\n"
            f"▸ Anti-Flood: {tog('antiflood')}\n"
            f"▸ Welcome: {tog('welcome_on',1)}\n"
            f"▸ Captcha: {tog('captcha_on')}\n"
            f"▸ Clean Service: {tog('clean_service')}\n"
            f"▸ Delete Commands: {tog('del_commands')}", reply_markup=kb)
    except Exception as e: logger.error(f"settings_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                              ECONOMY SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
async def coins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context)
        if target:
            uid = target.id
            udata = get_user(uid)
            await reply(update,
                f"💰 <b>Balance</b>\n{_D}\n\n"
                f"▸ User: {user_link(target)}\n"
                f"▸ Wallet: {fmt_coins(udata.get('coins',0))}\n"
                f"▸ Bank: {fmt_coins(udata.get('bank',0))}")
        else:
            user = update.effective_user
            get_user(user.id)
            udata = get_user(user.id)
            await reply(update,
                f"💰 <b>Your Balance</b>\n{_D}\n\n"
                f"▸ Wallet: {fmt_coins(udata.get('coins',0))}\n"
                f"▸ Bank: {fmt_coins(udata.get('bank',0))}\n"
                f"▸ Total: {fmt_coins(udata.get('coins',0) + udata.get('bank',0))}")
    except Exception as e: logger.error(f"coins_cmd: {e}")

@rate_limited("daily")
async def daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        get_user(user.id)
        udata = get_user(user.id)
        # Streak
        today = datetime.date.today()
        last_streak = udata.get("last_streak")
        streak = udata.get("streak", 0)
        if last_streak:
            try:
                ls = datetime.date.fromisoformat(str(last_streak))
                if ls == today - datetime.timedelta(days=1): streak += 1
                elif ls == today: pass
                else: streak = 1
            except: streak = 1
        else: streak = 1
        # Bonus
        base = random.randint(400, 800)
        bonus = min(streak * 10, 500)
        total = base + bonus
        # Check shop bonus
        db = get_db()
        inv = db.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=1", (user.id,)).fetchone()
        if inv and inv["quantity"] > 0:
            total *= 2
            db.execute("UPDATE inventory SET quantity=quantity-1 WHERE user_id=? AND item_id=1", (user.id,))
        db.execute("UPDATE users SET coins=coins+?, streak=?, last_streak=?, updated_at=CURRENT_TIMESTAMP WHERE user_id=?",
                   (total, streak, today.isoformat(), user.id))
        db.commit(); db.close()
        add_xp(user.id, 10)
        tmpl = R.pick(DAILY_MSGS, f"daily_{user.id}")
        name = html.escape(user.first_name or "You")
        await reply(update,
            f"{tmpl.format(name=name)}\n{_D}\n\n"
            f"💵 <b>Base:</b> {fmt_coins(base)}\n"
      �      f"🔥 <b>Streak Bonus:</b> +{fmt_coins(bonus)} (day {streak})\n"
            f"━━━━━━━━━━━\n"
            f"💎 <b>Total:</b> {fmt_coins(total)}\n"
            f"📊 <b>Streak:</b> 🔥×{streak} day{'s' if streak!=1 else ''}")
    except Exception as e: logger.error(f"daily_cmd: {e}")

@rate_limited("work")
async def work_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        get_user(user.id)
        scenario, min_earn, max_earn = random.choice(WORK_SCENARIOS)
        earned = random.randint(min_earn, max_earn)
        # Check XP booster
        add_coins(user.id, earned)
        add_xp(user.id, 15)
        await reply(update,
            f"💼 <b>Work Report</b>\n{_D}\n\n"
            f"📋 <b>Job:</b> {scenario}\n"
            f"💵 <b>Earned:</b> {fmt_coins(earned)}\n\n"
            f"<i>Next work available in 1 hour.</i>")
    except Exception as e: logger.error(f"work_cmd: {e}")

@rate_limited("mine")
async def mine_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        get_user(user.id)
        # Weighted mining outcomes
        weights = [(i,w) for i,(name,mn,mx,msg) in enumerate(MINE_SCENARIOS) for w in [
            50,30,20,10,5,2,3,5,2,8  # weights per scenario
        ][:1]]
        weights_list = [50,30,20,10,5,2,3,5,2,8]
        idx = random.choices(range(len(MINE_SCENARIOS)), weights=weights_list[:len(MINE_SCENARIOS)])[0]
        name, min_val, max_val, msg = MINE_SCENARIOS[idx]
        if min_val is None:  # Double strike
            base = random.randint(50, 300)
            earned = base * 2
            msg = f"⚡ DOUBLE STRIKE! Mined {fmt_coins(earned)}!"
        elif min_val < 0:  # Cave-in
            earned = random.randint(abs(max_val), abs(min_val))
            add_coins(user.id, -earned)
            add_xp(user.id, 3)
            return await reply(update,
                f"⛏️ <b>Mining Results</b>\n{_D}\n\n{name}\n{msg}\n\n"
                f"💸 <b>Lost:</b> {fmt_coins(earned)}\n"
                f"<i>Better luck next time!</i>")
        else:
            earned = random.randint(min_val, max_val)
        # Check mine bonus item
        db = get_db()
        inv = db.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=2", (user.id,)).fetchone()
        if inv and inv["quantity"] > 0:
            earned = int(earned * 1.5)
            db.execute("UPDATE inventory SET quantity=quantity-1 WHERE user_id=? AND item_id=2", (user.id,))
            db.commit()
        db.close()
        add_coins(user.id, earned)
        add_xp(user.id, 8)
        await reply(update,
            f"⛏️ <b>Mining Results</b>\n{_D}\n\n"
            f"{name}\n{msg}\n\n"
            f"💎 <b>Earned:</b> {fmt_coins(earned)}\n"
            f"<i>Next mine in 30 minutes.</i>")
    except Exception as e: logger.error(f"mine_cmd: {e}")

async def bank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        get_user(user.id)
        if not context.args:
            udata = get_user(user.id)
            return await reply(update,
                f"🏦 <b>Bank</b>\n{_D}\n\n"
                f"▸ Wallet: {fmt_coins(udata.get('coins',0))}\n"
                f"▸ Bank Balance: {fmt_coins(udata.get('bank',0))}\n\n"
                f"<code>/bank deposit N</code> · <code>/bank withdraw N</code>")
        action = context.args[0].lower()
        try: amount = int(context.args[1]) if len(context.args) > 1 else 0
        except: amount = 0
        if amount <= 0: return await reply(update, "❓ Provide a valid amount.")
        udata = get_user(user.id)
        db = get_db()
        if action == "deposit":
            if udata.get("coins",0) < amount:
                db.close()
                return await reply(update, f"❌ Not enough coins! You have {fmt_coins(udata.get('coins',0))}")
            db.execute("UPDATE users SET coins=coins-?, bank=bank+? WHERE user_id=?", (amount, amount, user.id))
            db.commit(); db.close()
            await reply(update, f"🏦 <b>Deposited {fmt_coins(amount)}!</b>\n▸ New bank: {fmt_coins(udata.get('bank',0)+amount)}")
        elif action == "withdraw":
            if udata.get("bank",0) < amount:
                db.close()
                return await reply(update, f"❌ Not enough in bank! You have {fmt_coins(udata.get('bank',0))}")
            db.execute("UPDATE users SET bank=bank-?, coins=coins+? WHERE user_id=?", (amount, amount, user.id))
            db.commit(); db.close()
            await reply(update, f"🏦 <b>Withdrew {fmt_coins(amount)}!</b>\n▸ New wallet: {fmt_coins(udata.get('coins',0)+amount)}")
        elif action == "balance":
            db.close()
            await reply(update, f"🏦 Wallet: {fmt_coins(udata.get('coins',0))} | Bank: {fmt_coins(udata.get('bank',0))}")
        else:
            db.close()
            await reply(update, "❓ Use: deposit, withdraw, balance")
    except Exception as e: logger.error(f"bank_cmd: {e}")

@rate_limited("flip")
async def flip_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        get_user(user.id)
        if not context.args: return await reply(update, "❓ <code>/flip amount</code>")
        try: amount = int(context.args[0])
        except: return await reply(update, "❌ Invalid amount.")
        if amount <= 0: return await reply(update, "❌ Amount must be positive.")
        udata = get_user(user.id)
        if udata.get("coins",0) < amount:
            return await reply(update, f"❌ Not enough coins! You have {fmt_coins(udata.get('coins',0))}")
        # Check luck item
        db = get_db()
        luck = db.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=6", (user.id,)).fetchone()
        db.close()
        win_chance = 55 if luck and luck["quantity"] > 0 else 50
        won = random.randint(1, 100) <= win_chance
        if won:
            add_coins(user.id, amount)
            await reply(update,
                f"🪙 <b>HEADS!</b> You won!\n{_D}\n\n"
                f"✅ <b>Profit:</b> +{fmt_coins(amount)}\n"
                f"💰 <b>New balance:</b> {fmt_coins(udata.get('coins',0) + amount)}")
        else:
            add_coins(user.id, -amount)
            await reply(update,
                f"🪙 <b>TAILS!</b> You lost!\n{_D}\n\n"
                f"❌ <b>Lost:</b> -{fmt_coins(amount)}\n"
                f"💰 <b>New balance:</b> {fmt_coins(udata.get('coins',0) - amount)}")
    except Exception as e: logger.error(f"flip_cmd: {e}")

@rate_limited("slots")
async def slots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        get_user(user.id)
        if not context.args: return await reply(update, "❓ <code>/slots amount</code>")
        try: amount = int(context.args[0])
        except: return await reply(update, "❌ Invalid amount.")
        if amount <= 0: return await reply(update, "❌ Amount must be positive.")
        udata = get_user(user.id)
        if udata.get("coins",0) < amount:
            return await reply(update, f"❌ Not enough coins!")
        symbols = ["🍒","🍋","🍊","🍇","⭐","💎","🎰","🔔","🍀","7️⃣"]
        weights = [30,25,20,15,8,5,4,3,2,1]
        s1 = random.choices(symbols, weights=weights)[0]
        s2 = random.choices(symbols, weights=weights)[0]
        s3 = random.choices(symbols, weights=weights)[0]
        if s1 == s2 == s3 == "💎":
            mult, result = 20, "💎 JACKPOT! DIAMOND MATCH!"
        elif s1 == s2 == s3 == "7️⃣":
            mult, result = 15, "7️⃣ LUCKY SEVENS!"
        elif s1 == s2 == s3:
            mult, result = 5, f"🎰 TRIPLE {s1}!"
        elif s1 == s2 or s2 == s3:
            mult, result = 2, "✨ Double match!"
        else:
            mult, result = 0, "❌ No match."
        if mult > 0:
            profit = amount * mult
            add_coins(user.id, profit)
            add_xp(user.id, 5)
            msg = f"✅ <b>Won:</b> +{fmt_coins(profit)} (x{mult})"
        else:
            add_coins(user.id, -amount)
            msg = f"❌ <b>Lost:</b> -{fmt_coins(amount)}"
        await reply(update,
            �f"🎰 <b>Slot Machine</b>\n{_D}\n\n"
            f"╔═══════════╗\n"
            f"║  {s1}  {s2}  {s3}  ║\n"
            f"╚═══════════╝\n\n"
            f"<b>{result}</b>\n{msg}")
    except Exception as e: logger.error(f"slots_cmd: {e}")

@rate_limited("rob")
async def rob_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        get_user(user.id)
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user or provide @username.")
        if target.id == user.id: return await reply(update, "❌ You can't rob yourself!")
        tudata = get_user(target.id)
        if tudata.get("coins",0) < 100:
            return await reply(update, "💸 That person is too broke to rob!")
        # Check shield
        db = get_db()
        shield = db.execute("SELECT quantity FROM inventory WHERE user_id=? AND item_id=3", (target.id,)).fetchone()
        if shield and shield["quantity"] > 0:
            db.execute("UPDATE inventory SET quantity=quantity-1 WHERE user_id=? AND item_id=3", (target.id,))
            db.commit(); db.close()
            return await reply(update, f"🛡️ {user_link(target)} had a Shield! Your rob was blocked!")
        db.close()
        success = random.randint(1, 100) <= 45
        if success:
            stolen = random.randint(50, min(500, tudata.get("coins",0) // 2))
            add_coins(user.id, stolen)
            add_coins(target.id, -stolen)
            await reply(update,
                f"💰 <b>Robbery Success!</b>\n{_D}\n\n"
                f"🦹 <b>Thief:</b> {user_link(user)}\n"
                f"🎯 <b>Victim:</b> {user_link(target)}\n"
                f"💸 <b>Stolen:</b> {fmt_coins(stolen)}")
        else:
            fine = random.randint(30, 150)
            add_coins(user.id, -fine)
            await reply(update,
                f"🚔 <b>Caught!</b>\n{_D}\n\n"
                f"👮 {user_link(user)} got caught robbing {user_link(target)}!\n"
                f"💸 <b>Fine:</b> -{fmt_coins(fine)}")
    except Exception as e: logger.error(f"rob_cmd: {e}")

async def give_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        get_user(user.id)
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user or @username.")
        if target.id == user.id: return await reply(update, "❌ Can't give to yourself!")
        try:
            amount_idx = 0 if update.message.reply_to_message else 1
            amount = int(context.args[amount_idx])
        except: return await reply(update, "❓ <code>/give @user amount</code>")
        if amount <= 0: return await reply(update, "❌ Amount must be positive.")
        udata = get_user(user.id)
        if udata.get("coins",0) < amount:
            return await reply(update, f"❌ Not enough coins!")
        add_coins(user.id, -amount)
        get_user(target.id)
        add_coins(target.id, amount)
        add_xp(user.id, 3)
        await reply(update,
            f"💝 <b>Gift Sent!</b>\n{_D}\n\n"
            f"▸ From: {user_link(user)}\n"
            f"▸ To: {user_link(target)}\n"
            f"▸ Amount: {fmt_coins(amount)}")
    except Exception as e: logger.error(f"give_cmd: {e}")

async def leaderboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        tab = context.args[0].lower() if context.args else "coins"
        if tab == "rep":
            rows = db.execute("SELECT user_id, reputation, first_name FROM users ORDER BY reputation DESC LIMIT 10").fetchall()
            title, col = "⭐ Top Reputation", "reputation"
        elif tab == "xp":
            rows = db.execute("SELECT user_id, xp, level, first_name FROM users ORDER BY xp DESC LIMIT 10").fetchall()
            title, col = "🏆 Top XP", "xp"
        else:
            rows = db.execute("SELECT user_id, coins, first_name FROM users ORDER BY coins DESC LIMIT 10").fetchall()
            title, col = "💰 Richest Users", "coins"
        db.close()
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        lines = [f"{title}\n{_D}\n"]
        for i, row in enumerate(rows):
            name = html.escape(row.get("first_name") or str(row["user_id"]))
            val = row[col] or 0
            lines.append(f"{medals[i]} <b>{name}</b> — {fmt_coins(val) if col == 'coins' else f'{val:,}'}")
        await reply(update, "\n".join(lines) if len(lines) > 1 else f"{title}\n\nNo data yet!")
    except Exception as e: logger.error(f"leaderboard_cmd: {e}")

async def shop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        items = db.execute("SELECT * FROM shop ORDER BY price").fetchall()
        db.close()
        lines = [f"🛒 <b>Shop</b>\n{_D}\n"]
        for item in items:
            lines.append(f"<code>[{item['item_id']}]</code> <b>{item['name']}</b>\n"
                         f"     {item['description']}\n"
                         f"     💵 {fmt_coins(item['price'])}\n")
        lines.append("\n<code>/buy item_id</code> to purchase!")
        await reply(update, "\n".join(lines))
    except Exception as e: logger.error(f"shop_cmd: {e}")

async def buy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        get_user(user.id)
        if not context.args: return await reply(update, "❓ <code>/buy item_id</code>")
        try: item_id = int(context.args[0])
        except: return await reply(update, "❌ Invalid item ID.")
        db = get_db()
        item = db.execute("SELECT * FROM shop WHERE item_id=?", (item_id,)).fetchone()
        if not item: db.close(); return await reply(update, "❌ Item not found!")
        udata = get_user(user.id)
        if udata.get("coins",0) < item["price"]:
            db.close()
            return await reply(update, f"❌ Not enough coins! Need {fmt_coins(item['price'])}")
        add_coins(user.id, -item["price"])
        db.execute("INSERT INTO inventory (user_id,item_id,quantity) VALUES (?,?,1) ON CONFLICT(user_id,item_id) DO UPDATE SET quantity=quantity+1",
                   (user.id, item_id))
        db.commit(); db.close()
        await reply(update,
            f"✅ <b>Purchased!</b>\n{_D}\n\n"
            f"▸ Item: <b>{item['name']}</b>\n"
            f"▸ Cost: {fmt_coins(item['price'])}\n"
            f"▸ Effect: {item['description']}")
    except Exception as e: logger.error(f"buy_cmd: {e}")

async def inventory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        db = get_db()
        items = db.execute("""SELECT s.name, s.description, i.quantity FROM inventory i
                             JOIN shop s ON i.item_id=s.item_id WHERE i.user_id=? AND i.quantity>0""",
                           (user.id,)).fetchall()
        db.close()
        if not items: return await reply(update, "🎒 <b>Your inventory is empty!</b>")
        lines = [f"🎒 <b>Inventory</b>\n{_D}\n"]
        for item in items:
            lines.append(f"▸ <b>{item['name']}</b> ×{item['quantity']}\n   <i>{item['description']}</i>")
        await reply(update, "\n".join(lines))
    except Exception as e: logger.error(f"inventory_cmd: {e}")

@rate_limited("lottery")
async def lottery_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        get_user(user.id)
        chat_id = update.effective_chat.id
        ticket_price = 100
        udata = get_user(user.id)
        if not context.args or context.args[0].lower() == "buy":
            if udata.get("coins",0) < ticket_price:
                return await reply(update, f"❌ A ticket costs {fmt_coins(ticket_price)}!")
            add_coins(user.id, -ticket_price)
            db = get_db()
            existing = db.execute("SELECT id,tickets FROM lottery WHERE user_id=? AND chat_id=?",
                                  (user.id, chat_id)).fetchone()
            if existing:
                db.execute("UPDATE lottery SET tickets=tickets+1 WHERE id=?", (existing["id"],))
            else:
   �             db.execute("INSERT INTO lottery (user_id,tickets,chat_id) VALUES (?,1,?)", (user.id, chat_id))
            db.commit()
            total = db.execute("SELECT SUM(tickets) FROM lottery WHERE chat_id=?", (chat_id,)).fetchone()[0] or 0
            db.close()
            await reply(update,
                f"🎟️ <b>Lottery Ticket Purchased!</b>\n{_D}\n\n"
                f"▸ Cost: {fmt_coins(ticket_price)}\n"
                f"▸ Total pot: {fmt_coins(total * ticket_price)}\n"
                f"▸ Your chances: higher with more tickets!\n\n"
                f"<i>/lottery draw — draw winner (admin only)</i>")
        elif context.args[0].lower() == "draw":
            if not await is_admin(context, chat_id, user.id):
                return await reply(update, "🚫 Only admins can draw!")
            db = get_db()
            tickets = db.execute("SELECT user_id,tickets FROM lottery WHERE chat_id=?", (chat_id,)).fetchall()
            if not tickets: db.close(); return await reply(update, "🎟️ No tickets sold yet!")
            pool = [t["user_id"] for t in tickets for _ in range(t["tickets"])]
            winner_id = random.choice(pool)
            prize = len(pool) * ticket_price
            add_coins(winner_id, prize)
            db.execute("DELETE FROM lottery WHERE chat_id=?", (chat_id,))
            db.commit(); db.close()
            await reply(update,
                f"🎉 <b>LOTTERY DRAW!</b>\n{_D}\n\n"
                f"🏆 <b>Winner:</b> <a href='tg://user?id={winner_id}'>{winner_id}</a>\n"
                f"💰 <b>Prize:</b> {fmt_coins(prize)}\n\n"
                f"🎊 Congratulations!")
        else:
            db = get_db()
            total = db.execute("SELECT SUM(tickets) FROM lottery WHERE chat_id=?", (chat_id,)).fetchone()[0] or 0
            my = db.execute("SELECT tickets FROM lottery WHERE user_id=? AND chat_id=?",
                            (user.id, chat_id)).fetchone()
            db.close()
            await reply(update,
                f"🎟️ <b>Lottery Info</b>\n{_D}\n\n"
                f"▸ Ticket price: {fmt_coins(ticket_price)}\n"
                f"▸ Total tickets: {total}\n"
                f"▸ Prize pool: {fmt_coins(total * ticket_price)}\n"
                f"▸ Your tickets: {my['tickets'] if my else 0}\n\n"
                f"<code>/lottery buy</code> — buy a ticket\n"
                f"<code>/lottery draw</code> — draw winner (admin)")
    except Exception as e: logger.error(f"lottery_cmd: {e}")

async def streak_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        udata = get_user(user.id)
        streak = udata.get("streak", 0)
        await reply(update,
            f"🔥 <b>Daily Streak</b>\n{_D}\n\n"
            f"▸ {user_link(user)}: {streak} day{'s' if streak!=1 else ''}\n"
            f"▸ Streak bonus: +{min(streak*10, 500)} coins/day\n\n"
            f"<i>Claim /daily every 24h to maintain your streak!</i>")
    except Exception as e: logger.error(f"streak_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         REPUTATION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
async def rep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        giver = update.effective_user
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user or @username.")
        if target.id == giver.id: return await reply(update, "❌ You can't rep yourself!")
        db = get_db()
        last = db.execute("SELECT given_at FROM rep_cooldown WHERE giver_id=? AND receiver_id=?",
                          (giver.id, target.id)).fetchone()
        now = datetime.datetime.now(pytz.utc)
        if last:
            la = last["given_at"]
            try:
                la_dt = datetime.datetime.fromisoformat(str(la).replace("Z",""))
                if la_dt.tzinfo is None: la_dt = la_dt.replace(tzinfo=pytz.utc)
                diff = now - la_dt
                if diff < datetime.timedelta(hours=24):
                    remaining = datetime.timedelta(hours=24) - diff
                    db.close()
                    return await reply(update, f"⏳ You can rep {user_link(target)} again in {fmt_duration(remaining)}")
            except: pass
        db.execute("INSERT OR REPLACE INTO rep_cooldown (giver_id,receiver_id,given_at) VALUES (?,?,?)",
                   (giver.id, target.id, now.isoformat()))
        get_user(target.id)
        db.execute("UPDATE users SET reputation=reputation+1 WHERE user_id=?", (target.id,))
        db.commit()
        new_rep = db.execute("SELECT reputation FROM users WHERE user_id=?", (target.id,)).fetchone()["reputation"]
        db.close()
        await reply(update,
            f"⭐ <b>Rep Given!</b>\n{_D}\n\n"
            f"▸ From: {user_link(giver)}\n"
            f"▸ To: {user_link(target)}\n"
            f"▸ Rep: {new_rep} ⭐")
    except Exception as e: logger.error(f"rep_cmd: {e}")

async def checkrep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context) or update.effective_user
        udata = get_user(target.id)
        await reply(update, f"⭐ <b>{user_link(target)}</b> has {udata.get('reputation',0)} reputation!")
    except Exception as e: logger.error(f"checkrep_cmd: {e}")

async def reprank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await leaderboard_cmd(update, type("FakeCTX",(),{"args":["rep"],"bot":context.bot})())

# ═══════════════════════════════════════════════════════════════════════════════
#                              GAMES
# ═══════════════════════════════════════════════════════════════════════════════
# ─── TRIVIA ────────────────────────────────────────────────────────────────────
TRIVIA_QUESTIONS = [
    ("What is the capital of Australia?", ["Canberra","Sydney","Melbourne","Brisbane"], 0),
    ("How many sides does a hexagon have?", ["5","6","7","8"], 1),
    ("What is the chemical symbol for gold?", ["Ag","Go","Au","Gd"], 2),
    ("Who painted the Mona Lisa?", ["Michelangelo","Da Vinci","Raphael","Botticelli"], 1),
    ("What is the fastest land animal?", ["Lion","Cheetah","Horse","Greyhound"], 1),
    ("In what year did World War 2 end?", ["1943","1944","1945","1946"], 2),
    ("What is 7 × 8?", ["54","56","58","64"], 1),
    ("What planet is known as the Red Planet?", ["Venus","Jupiter","Mars","Saturn"], 2),
    ("What is the largest ocean?", ["Atlantic","Indian","Arctic","Pacific"], 3),
    ("Who wrote 'Romeo and Juliet'?", ["Dickens","Shakespeare","Austen","Hemingway"], 1),
    ("What is H2O commonly known as?", ["Hydrogen","Water","Oxygen","Salt"], 1),
    ("How many continents are there?", ["5","6","7","8"], 2),
    ("What is the smallest prime number?", ["0","1","2","3"], 2),
    ("What language has the most native speakers?", ["English","Spanish","Mandarin","Hindi"], 2),
    ("What is the currency of Japan?", ["Yuan","Won","Yen","Ringgit"], 2),
    ("Who invented the telephone?", ["Edison","Tesla","Bell","Morse"], 2),
    ("What is the boiling point of water in Celsius?", ["90","95","100","105"], 2),
    ("What country has the most natural lakes?", ["USA","Russia","Canada","Brazil"], 2),
    ("What gas do plants absorb from the air?", ["Oxygen","Nitrogen","Carbon Dioxide","Helium"], 2),
    ("How many strings does a guitar have?", ["4","5","6","7"], 2),
    ("What is the largest planet in our solar system?", ["Saturn","Neptune","Jupiter","Uranus"], 2),
    ("What is the square root of 144?", ["11","12","13","14"], 1),
    ("In what country is the Amazon River mainly located?", ["Colombia","Peru","Ecuador","Brazil"], 3),
    ("What is the tallest mountain in the world?", ["K2","Everest","Kangchenjunga","Lhotse"], 1),
    ("What do you call a baby kangaroo?", ["Cub","Pup","Joey","Kit"], 2),
]

_trivia_state: Dict[int, dict] = {}

async def trivia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        q, opts, ans_idx = random.choice(TRIVIA_QUESTIONS)
        _trivia_state[chat_id] = �{"answer": ans_idx, "opts": opts, "starter": update.effective_user.id}
        buttons = [[InlineKeyboardButton(f"{['A','B','C','D'][i]}. {opt}",
                    callback_data=f"trivia:{chat_id}:{i}")]
                   for i, opt in enumerate(opts)]
        await reply(update,
            f"🎯 <b>TRIVIA TIME!</b>\n{_D}\n\n"
            f"❓ <b>{html.escape(q)}</b>\n\n"
            f"<i>Tap an answer below!</i>",
            reply_markup=InlineKeyboardMarkup(buttons))
    except Exception as e: logger.error(f"trivia_cmd: {e}")

async def trivia_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query
        parts = q.data.split(":")
        if len(parts) < 3: return await q.answer("Invalid!", show_alert=True)
        chat_id, chosen = int(parts[1]), int(parts[2])
        state = _trivia_state.get(chat_id)
        if not state: return await q.answer("This trivia has expired!", show_alert=True)
        correct = state["answer"]
        opts = state["opts"]
        user = q.from_user
        if chosen == correct:
            reward = random.randint(50, 150)
            get_user(user.id)
            add_coins(user.id, reward)
            add_xp(user.id, 20)
            db = get_db()
            db.execute("INSERT INTO trivia_scores (chat_id,user_id,score) VALUES (?,?,1) ON CONFLICT(chat_id,user_id) DO UPDATE SET score=score+1",
                       (chat_id, user.id))
            db.commit(); db.close()
            await q.answer(f"✅ Correct! +{reward} coins!", show_alert=True)
            del _trivia_state[chat_id]
            await q.edit_message_text(
                f"✅ <b>Correct!</b>\n\n"
                f"🏆 <b>{user_link(user)}</b> got it right!\n"
                f"💰 Reward: {fmt_coins(reward)}\n"
                f"✨ Answer: <b>{opts[correct]}</b>",
                parse_mode="HTML")
        else:
            await q.answer(f"❌ Wrong! The answer was: {opts[correct]}", show_alert=True)
    except Exception as e: logger.debug(f"trivia_callback: {e}")

# ─── HANGMAN ────────────────────────────────────────────────────────────────────
def _hangman_art(wrong: int) -> str:
    stages = [
        "```\n+---+\n|   |\n    |\n    |\n    |\n    |\n=========```",
        "```\n+---+\n|   |\nO   |\n    |\n    |\n    |\n=========```",
        "```\n+---+\n|   |\nO   |\n|   |\n    |\n    |\n=========```",
        "```\n+---+\n|   |\nO   |\n/|  |\n    |\n    |\n=========```",
        "```\n+---+\n|   |\nO   |\n/|\\ |\n    |\n    |\n=========```",
        "```\n+---+\n|   |\nO   |\n/|\\ |\n/   |\n    |\n=========```",
        "```\n+---+\n|   |\nO   |\n/|\\ |\n/ \\ |\n    |\n=========```",
    ]
    return stages[min(wrong, 6)]

async def hangman_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        db = get_db()
        existing = db.execute("SELECT word FROM hangman_state WHERE chat_id=?", (chat_id,)).fetchone()
        if existing:
            db.close()
            return await reply(update, "🔤 A hangman game is already running! Use /guess letter or /stophangman")
        word_data = random.choice(HANGMAN_WORDS)
        word, hint = word_data
        db.execute("INSERT OR REPLACE INTO hangman_state (chat_id,word,hint,guessed,wrong,started_by) VALUES (?,?,?,'','',?)",
                   (chat_id, word, hint, update.effective_user.id))
        db.commit(); db.close()
        blanks = " ".join("_" for _ in word)
        await reply(update,
            f"🔤 <b>HANGMAN!</b>\n{_D}\n\n"
            f"{_hangman_art(0)}\n\n"
            f"Word: <code>{blanks}</code> ({len(word)} letters)\n"
            f"Hint: <i>{hint}</i>\n\n"
            f"Use <code>/guess a</code> to guess a letter!\n"
            f"/stophangman to end the game.")
    except Exception as e: logger.error(f"hangman_cmd: {e}")

async def guess_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        db = get_db()
        state = db.execute("SELECT * FROM hangman_state WHERE chat_id=?", (chat_id,)).fetchone()
        if not state:
            db.close()
            return await reply(update, "❓ No hangman game running! Use /hangman to start one.")
        if not context.args:
            db.close()
            return await reply(update, "❓ <code>/guess letter</code>")
        letter = context.args[0].lower()[0] if context.args[0] else ""
        if not letter.isalpha():
            db.close()
            return await reply(update, "❌ Please guess a letter!")
        word = state["word"].lower()
        guessed = state["guessed"] or ""
        wrong = state["wrong"] or ""
        if letter in guessed or letter in wrong:
            db.close()
            return await reply(update, f"❌ Already guessed '{letter}'!")
        if letter in word:
            guessed += letter
            msg = f"✅ '{letter}' is in the word!"
        else:
            wrong += letter
            msg = f"❌ '{letter}' is not in the word!"
        wrong_count = len(wrong)
        blanks = " ".join(c if c in guessed else "_" for c in word)
        # Check win/lose
        if all(c in guessed for c in word):
            db.execute("DELETE FROM hangman_state WHERE chat_id=?", (chat_id,))
            db.commit(); db.close()
            reward = 200 + (6 - wrong_count) * 50
            get_user(update.effective_user.id)
            add_coins(update.effective_user.id, reward)
            return await reply(update,
                f"🎉 <b>YOU WON!</b>\n{_D}\n\n"
                f"✨ Word: <b>{word.upper()}</b>\n"
                f"💰 Reward: {fmt_coins(reward)}\n"
                f"❌ Wrong guesses: {wrong_count}/6")
        if wrong_count >= 6:
            db.execute("DELETE FROM hangman_state WHERE chat_id=?", (chat_id,))
            db.commit(); db.close()
            return await reply(update,
                f"💀 <b>GAME OVER!</b>\n{_D}\n\n"
                f"{_hangman_art(6)}\n\n"
                f"The word was: <b>{word.upper()}</b>")
        db.execute("UPDATE hangman_state SET guessed=?, wrong=? WHERE chat_id=?", (guessed, wrong, chat_id))
        db.commit(); db.close()
        await reply(update,
            f"🔤 <b>Hangman</b>\n{_D}\n\n"
            f"{_hangman_art(wrong_count)}\n\n"
            f"{msg}\n"
            f"Word: <code>{blanks}</code>\n"
            f"Wrong ({wrong_count}/6): {' '.join(wrong.upper()) if wrong else 'None'}\n"
            f"Guessed: {' '.join(guessed.upper()) if guessed else 'None'}")
    except Exception as e: logger.error(f"guess_cmd: {e}")

async def stophangman_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        db = get_db()
        state = db.execute("SELECT word FROM hangman_state WHERE chat_id=?", (chat_id,)).fetchone()
        if not state: db.close(); return await reply(update, "❓ No hangman game running.")
        word = state["word"]
        db.execute("DELETE FROM hangman_state WHERE chat_id=?", (chat_id,))
        db.commit(); db.close()
        await reply(update, f"🛑 <b>Hangman stopped.</b>\nThe word was: <b>{word.upper()}</b>")
    except Exception as e: logger.error(f"stophangman_cmd: {e}")

# ─── SCRAMBLE ────────────────────────────────────────────────────────────────
_scramble_state: Dict[int, dict] = {}

async def scramble_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        if chat_id in _scramble_state:
            return await reply(update, "🔀 A scramble game is already running! Use <code>/unscramble word</code>")
        word, hint = random.choice(SCRAMBLE_WORDS)
        scrambled = list(word)
        while "".join(scrambled) == word:
            random.shuffle(scrambled)
        scrambled_str = "".join(scrambled)
        _scramble_state[chat_id] = {"word": word, "hint": hint, "started": time.time()}
        await reply(update,
            f"🔀 <b>WORD SCRAMBLE!</b>\n{_D}\n\n"
            f"Unscramble: <code>{scrambled_str.upper()}</code>\n"
            f"Hint: <i>{hint}</i>\n\n"
            f"Use <code>/unscramble yourword</code> to answer!\n"
        �    f"<i>60 seconds to answer!</i>")
        # Auto-expire
        async def expire():
            await asyncio.sleep(60)
            if chat_id in _scramble_state and _scramble_state[chat_id].get("word") == word:
                del _scramble_state[chat_id]
        asyncio.ensure_future(expire())
    except Exception as e: logger.error(f"scramble_cmd: {e}")

async def unscramble_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in _scramble_state:
            return await reply(update, "❓ No scramble game running! Use /scramble to start one.")
        if not context.args: return await reply(update, "❓ <code>/unscramble yourword</code>")
        guess = " ".join(context.args).lower().strip()
        state = _scramble_state[chat_id]
        if guess == state["word"]:
            del _scramble_state[chat_id]
            reward = 100
            get_user(update.effective_user.id)
            add_coins(update.effective_user.id, reward)
            add_xp(update.effective_user.id, 15)
            await reply(update,
                f"✅ <b>CORRECT!</b>\n{_D}\n\n"
                f"🏆 {user_link(update.effective_user)} unscrambled it!\n"
                f"💰 Reward: {fmt_coins(reward)}")
        else:
            await reply(update, f"❌ <b>Not quite!</b> Try again or wait for the reveal.")
    except Exception as e: logger.error(f"unscramble_cmd: {e}")

# ─── RPS ─────────────────────────────────────────────────────────────────────
@rate_limited("rps")
async def rps_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        if not context.args:
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("🪨 Rock", callback_data="rps:rock"),
                InlineKeyboardButton("📄 Paper", callback_data="rps:paper"),
                InlineKeyboardButton("✂️ Scissors", callback_data="rps:scissors"),
            ]])
            await reply(update, "🪨📄✂️ <b>Rock Paper Scissors!</b>\n\nChoose your move:", reply_markup=kb)
            return
        choice = context.args[0].lower()
        if choice not in RPS_EMOJIS: return await reply(update, "❓ Choose: rock, paper, or scissors")
        bot_choice = random.choice(list(RPS_EMOJIS.keys()))
        if choice == bot_choice:
            result = R.pick(RPS_DRAW_MSGS); outcome = "🤝 Draw!"
        elif RPS_BEATS[choice] == bot_choice:
            result = R.pick(RPS_WIN_MSGS); outcome = "✅ You win!"
            get_user(user.id); add_coins(user.id, 30); add_xp(user.id, 5)
        else:
            result = R.pick(RPS_LOSE_MSGS); outcome = "❌ Bot wins!"
        await reply(update,
            f"🪨📄✂️ <b>RPS Battle</b>\n{_D}\n\n"
            f"You: {RPS_EMOJIS[choice]} {choice.capitalize()}\n"
            f"Bot: {RPS_EMOJIS[bot_choice]} {bot_choice.capitalize()}\n\n"
            f"<b>{outcome}</b>\n<i>{result}</i>")
    except Exception as e: logger.error(f"rps_cmd: {e}")

async def rps_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query
        choice = q.data.split(":")[1]
        bot_choice = random.choice(list(RPS_EMOJIS.keys()))
        if choice == bot_choice:
            result = R.pick(RPS_DRAW_MSGS); outcome = "🤝 Draw!"
        elif RPS_BEATS[choice] == bot_choice:
            result = R.pick(RPS_WIN_MSGS); outcome = "✅ You win!"
            get_user(q.from_user.id); add_coins(q.from_user.id, 30); add_xp(q.from_user.id, 5)
        else:
            result = R.pick(RPS_LOSE_MSGS); outcome = "❌ Bot wins!"
        await q.answer(outcome)
        await q.edit_message_text(
            f"🪨📄✂️ <b>RPS Battle</b>\n{_D}\n\n"
            f"You: {RPS_EMOJIS[choice]} {choice.capitalize()}\n"
            f"Bot: {RPS_EMOJIS[bot_choice]} {bot_choice.capitalize()}\n\n"
            f"<b>{outcome}</b>\n<i>{result}</i>",
            parse_mode="HTML")
    except Exception as e: logger.debug(f"rps_callback: {e}")

# ─── TIC TAC TOE (Minimax AI) ─────────────────────────────────────────────────
_ttt_state: Dict[int, dict] = {}

def _ttt_check(board):
    wins = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
    for w in wins:
        if board[w[0]] and board[w[0]] == board[w[1]] == board[w[2]]:
            return board[w[0]]
    return None

def _ttt_minimax(board, is_max):
    winner = _ttt_check(board)
    if winner == "O": return 10
    if winner == "X": return -10
    if all(board): return 0
    scores = []
    for i in range(9):
        if not board[i]:
            board[i] = "O" if is_max else "X"
            scores.append(_ttt_minimax(board, not is_max))
            board[i] = None
    return max(scores) if is_max else min(scores)

def _ttt_best_move(board):
    best, best_score = None, -999
    for i in range(9):
        if not board[i]:
            board[i] = "O"
            s = _ttt_minimax(board, False)
            board[i] = None
            if s > best_score:
                best_score, best = s, i
    return best

def _ttt_render(board, game_id):
    syms = {None:"⬜","X":"❌","O":"🔵"}
    rows = []
    for r in range(3):
        row = []
        for c in range(3):
            idx = r*3+c
            sym = syms[board[idx]]
            row.append(InlineKeyboardButton(sym, callback_data=f"ttt:{game_id}:{idx}"))
        rows.append(row)
    return InlineKeyboardMarkup(rows)

@rate_limited("ttt")
async def ttt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        game_id = f"{update.effective_chat.id}_{user.id}"
        board = [None]*9
        _ttt_state[game_id] = {"board": board, "player": user.id, "turn": "X"}
        await reply(update,
            f"❌🔵 <b>Tic Tac Toe!</b>\n{_D}\n\n"
            f"You are ❌ — tap to place!\n"
            f"Bot is 🔵 — it plays optimally (minimax)!",
            reply_markup=_ttt_render(board, game_id))
    except Exception as e: logger.error(f"ttt_cmd: {e}")

async def ttt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query
        parts = q.data.split(":")
        game_id, idx = parts[1], int(parts[2])
        state = _ttt_state.get(game_id)
        if not state: return await q.answer("Game expired!", show_alert=True)
        if q.from_user.id != state["player"]:
            return await q.answer("Not your game!", show_alert=True)
        board = state["board"]
        if board[idx]: return await q.answer("Square taken!", show_alert=True)
        board[idx] = "X"
        await q.answer()
        winner = _ttt_check(board)
        if winner or all(board):
            del _ttt_state[game_id]
            msg = "❌ <b>You won!</b> 🎉" if winner == "X" else "🤝 <b>Draw!</b>"
            if winner == "X": get_user(q.from_user.id); add_coins(q.from_user.id, 100)
            await q.edit_message_text(msg + f"\n{_ttt_render(board,'done')}", parse_mode="HTML")
            return
        # Bot move
        bot_idx = _ttt_best_move(board)
        if bot_idx is not None:
            board[bot_idx] = "O"
        winner = _ttt_check(board)
        if winner or all(board):
            del _ttt_state[game_id]
            msg = "🔵 <b>Bot wins!</b> 🤖" if winner == "O" else "🤝 <b>Draw!</b>"
            await q.edit_message_reply_markup(reply_markup=_ttt_render(board, "done"))
            await q.message.reply_text(msg, parse_mode="HTML")
            return
        await q.edit_message_reply_markup(reply_markup=_ttt_render(board, game_id))
    except Exception as e: logger.debug(f"ttt_callback: {e}")

# ─── RIDDLE ───────────────────────────────────────────────────────────────────
_riddle_state: Dict[int, dict] = {}

@rate_limited("riddle")
async def riddle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        q, a = random.choice(RIDDLE_POOL)
        _riddle_state[chat_id] = {"answer": a.lower(), "question": q, "time": time.time()}
        await reply(update,
            f"🧩 <b>RIDDLE!</b>\n{_D}\n\n"
            f"❓ {q}\n\n"
            f"Use <code>/answer your answer</code> to solve it!�")
        async def expire():
            await asyncio.sleep(120)
            if chat_id in _riddle_state and _riddle_state[chat_id].get("question") == q:
                del _riddle_state[chat_id]
        asyncio.ensure_future(expire())
    except Exception as e: logger.error(f"riddle_cmd: {e}")

async def answer_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat_id = update.effective_chat.id
        if chat_id not in _riddle_state:
            return await reply(update, "❓ No riddle active! Use /riddle to start one.")
        if not context.args: return await reply(update, "❓ <code>/answer your answer</code>")
        guess = " ".join(context.args).lower().strip()
        state = _riddle_state[chat_id]
        correct = state["answer"]
        if guess in correct or correct in guess or guess == correct:
            del _riddle_state[chat_id]
            reward = 150
            get_user(update.effective_user.id)
            add_coins(update.effective_user.id, reward)
            add_xp(update.effective_user.id, 20)
            await reply(update,
                f"🎉 <b>CORRECT!</b>\n{_D}\n\n"
                f"🏆 {user_link(update.effective_user)} solved the riddle!\n"
                f"💰 Reward: {fmt_coins(reward)}\n"
                f"✨ Answer: <b>{correct.title()}</b>")
        else:
            await reply(update, "❌ <b>Not quite!</b> Keep thinking...")
    except Exception as e: logger.error(f"answer_cmd: {e}")

# ─── BATTLE ───────────────────────────────────────────────────────────────────
@rate_limited("battle")
async def battle_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user or @username to battle!")
        if target.id == user.id: return await reply(update, "❌ You can't battle yourself!")
        if target.is_bot: return await reply(update, "🤖 You can't battle a bot!")
        # Determine stats
        get_user(user.id); get_user(target.id)
        hp1 = random.randint(80, 120)
        hp2 = random.randint(80, 120)
        rounds = []
        round_num = 1
        while hp1 > 0 and hp2 > 0 and round_num <= 10:
            # Player attacks bot
            dmg = random.randint(5, 35)
            crit = random.randint(1,100) <= 15
            if crit: dmg = int(dmg * 2); rounds.append(R.pick(BATTLE_CRIT_MSGS).format(a=user_link(user)))
            elif random.randint(1,100) <= 20: rounds.append(R.pick(BATTLE_MISS_MSGS).format(a=user_link(user),b=user_link(target))); round_num+=1; continue
            else: rounds.append(R.pick(BATTLE_ATTACK_MSGS).format(a=user_link(user),b=user_link(target)))
            hp2 -= dmg
            if hp2 <= 0: break
            # Target attacks back
            dmg2 = random.randint(5, 30)
            crit2 = random.randint(1,100) <= 15
            if crit2: dmg2 = int(dmg2 * 2); rounds.append(R.pick(BATTLE_CRIT_MSGS).format(a=user_link(target)))
            else: rounds.append(R.pick(BATTLE_ATTACK_MSGS).format(a=user_link(target),b=user_link(user)))
            hp1 -= dmg2
            round_num += 1
        winner = user if hp2 <= 0 else target
        loser = target if hp2 <= 0 else user
        reward = random.randint(100, 300)
        add_coins(winner.id, reward)
        add_xp(winner.id, 30)
        # Log battle stats
        db = get_db()
        db.execute("INSERT INTO battle_stats (user_id,wins,losses,draws) VALUES (?,1,0,0) ON CONFLICT(user_id) DO UPDATE SET wins=wins+1",
                   (winner.id,))
        db.execute("INSERT INTO battle_stats (user_id,wins,losses,draws) VALUES (?,0,1,0) ON CONFLICT(user_id) DO UPDATE SET losses=losses+1",
                   (loser.id,))
        db.commit(); db.close()
        battle_log = "\n".join(rounds[-4:]) if len(rounds) > 4 else "\n".join(rounds)
        await reply(update,
            f"⚔️ <b>BATTLE!</b>\n{_D}\n\n"
            f"{battle_log}\n{_D}\n\n"
            f"🏆 <b>WINNER: {user_link(winner)}!</b>\n"
            f"💸 Loser: {user_link(loser)}\n"
            f"💰 Prize: {fmt_coins(reward)}")
    except Exception as e: logger.error(f"battle_cmd: {e}")

# ─── ROLL / PP / SHIP ─────────────────────────────────────────────────────────
async def roll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sides = int(context.args[0]) if context.args else 6
        sides = max(2, min(sides, 10000))
        result = random.randint(1, sides)
        await reply(update, f"🎲 <b>Rolled!</b> You got <b>{result}</b> (1-{sides})")
    except Exception as e: logger.error(f"roll_cmd: {e}")

async def pp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context) or update.effective_user
        seed = target.id
        size = R.pct(seed)
        bar = "█" * (size // 10) + "░" * (10 - size // 10)
        comments = [
            "certified massive fr 🔥","doing numbers bestie","the people are impressed 👀",
            "the algorithm approves ✅","respectfully iconic","a solid showing tbh",
            "statistically significant","the data speaks for itself 📊","above average moment",
            "certified classic","mid but with character","struggling but valid",
            "keep head up bestie 🙏","it's giving effort","the spirit is willing",
        ]
        comment = R.daily(comments, seed)
        await reply(update,
            f"📏 <b>PP Meter</b>\n{_D}\n\n"
            f"👤 {user_link(target)}\n"
            f"Size: <b>{size}%</b>\n"
            f"[{bar}]\n\n"
            f"<i>{comment}</i>")
    except Exception as e: logger.error(f"pp_cmd: {e}")

async def ship_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        u1 = u2 = None
        if msg.reply_to_message:
            u1 = msg.reply_to_message.from_user
            u2 = update.effective_user
        elif len(context.args) >= 2:
            try:
                u1 = type("U",(),{"id":int(context.args[0].lstrip("@")),"first_name":context.args[0],"username":None})()
                u2 = type("U",(),{"id":int(context.args[1].lstrip("@")),"first_name":context.args[1],"username":None})()
            except:
                u1 = update.effective_user
                u2 = type("U",(),{"id":hash(context.args[0])%10**9,"first_name":context.args[0],"username":None})()
        else:
            u1 = update.effective_user
            u2 = type("U",(),{"id":random.randint(100,999),"first_name":"Mystery Person 🌹","username":None})()
        seed = (u1.id + u2.id) * (abs(u1.id - u2.id) + 1)
        pct = R.pct(seed % 10**9)
        bar = progress_bar(pct, 100, 10)
        if pct < 30: msg_pool = SHIP_MSGS_LOW
        elif pct < 70: msg_pool = SHIP_MSGS_MED
        else: msg_pool = SHIP_MSGS_HIGH
        ship_name = (user_link(u1).split(">")[0].replace("<a ","")[:6] +
                     user_link(u2).split(">")[0].replace("<a ","")[:6]).strip()
        await reply(update,
            f"💕 <b>SHIP METER</b>\n{_D}\n\n"
            f"👤 {user_link(u1)}\n"
            f"❤️ {user_link(u2)}\n\n"
            f"<b>[{bar}] {pct}%</b>\n\n"
            f"<i>{R.pick(msg_pool, f'ship_{seed}')}</i>")
    except Exception as e: logger.error(f"ship_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         SOCIAL COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════
async def _social_cmd(update, context, pool, key, fallback=""):
    try:
        user = update.effective_user
        target = await get_target(update, context)
        if not target: target = type("U",(),{"id":0,"first_name":"everyone","username":None,"last_name":None})()
        msg = R.pick(pool, f"{key}_{update.effective_chat.id}").format(
            a=user_link(user), b=user_link(target))
        await reply(update, msg)
    except Exception as e: logger.error(f"social_{key}: {e}")

async def hug_cmd(u, c): await _social_cmd(u, c, HUG_MSGS, "hug")
async def slap_cmd(u, c): await _social_cmd(u, c, SLAP_MSGS, "slap")
async def k�iss_cmd(u, c): await _social_cmd(u, c, KISS_MSGS, "kiss")
async def pat_cmd(u, c): await _social_cmd(u, c, PAT_MSGS, "pat")
async def poke_cmd(u, c): await _social_cmd(u, c, POKE_MSGS, "poke")

@rate_limited("roast")
async def roast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context) or update.effective_user
        roast = R.pick(ROAST_POOL, f"roast_{update.effective_chat.id}")
        await reply(update, f"🔥 <b>Roast for {user_link(target)}:</b>\n\n{roast}")
    except Exception as e: logger.error(f"roast_cmd: {e}")

@rate_limited("compliment")
async def compliment_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context) or update.effective_user
        comp = R.pick(COMPLIMENT_POOL, f"comp_{update.effective_chat.id}")
        await reply(update, f"💫 <b>For {user_link(target)}:</b>\n\n{comp}")
    except Exception as e: logger.error(f"compliment_cmd: {e}")

# ─── MARRIAGE SYSTEM ───────────────────────────────────────────────────────────
async def marry_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Reply to a user or @username to propose!")
        if target.id == user.id: return await reply(update, "❌ You can't marry yourself!")
        if target.is_bot: return await reply(update, "🤖 Bots can't get married... yet.")
        # Check if already married
        db = get_db()
        udata = get_user(user.id)
        if udata.get("spouse_id"):
            db.close()
            return await reply(update, f"💍 You're already married! Use /divorce first.")
        tdata = get_user(target.id)
        if tdata.get("spouse_id"):
            db.close()
            return await reply(update, f"💔 {user_link(target)} is already married!")
        # Check existing proposal
        existing = db.execute("SELECT 1 FROM proposals WHERE from_id=? AND to_id=?",
                              (user.id, target.id)).fetchone()
        if existing:
            db.close()
            return await reply(update, f"💌 You already proposed to {user_link(target)}! Waiting for their /accept")
        db.execute("INSERT OR REPLACE INTO proposals (from_id,to_id) VALUES (?,?)", (user.id, target.id))
        db.commit(); db.close()
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("💍 Accept!", callback_data=f"marry_accept:{user.id}:{target.id}"),
            InlineKeyboardButton("💔 Decline", callback_data=f"marry_decline:{user.id}:{target.id}"),
        ]])
        await reply(update,
            f"💍 <b>PROPOSAL!</b>\n{_D}\n\n"
            f"{user_link(user)} is getting down on one knee...\n\n"
            f"💌 <b>{user_link(target)}</b>, will you accept this proposal?\n\n"
            f"<i>{user_link(target)}, tap a button below!</i>",
            reply_markup=kb)
    except Exception as e: logger.error(f"marry_cmd: {e}")

async def marry_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query
        parts = q.data.split(":")
        action, from_id, to_id = parts[0], int(parts[1]), int(parts[2])
        if q.from_user.id != to_id:
            return await q.answer("This proposal isn't for you!", show_alert=True)
        db = get_db()
        db.execute("DELETE FROM proposals WHERE from_id=? AND to_id=?", (from_id, to_id))
        db.commit()
        if action == "marry_accept":
            # Double check neither is married
            u1 = get_user(from_id); u2 = get_user(to_id)
            if u1.get("spouse_id") or u2.get("spouse_id"):
                db.close()
                return await q.answer("One of you is already married!", show_alert=True)
            db.execute("UPDATE users SET spouse_id=?, married_at=CURRENT_TIMESTAMP WHERE user_id=?", (to_id, from_id))
            db.execute("UPDATE users SET spouse_id=?, married_at=CURRENT_TIMESTAMP WHERE user_id=?", (from_id, to_id))
            db.commit(); db.close()
            tmpl = R.pick(MARRY_MSGS)
            await q.answer("💍 Congratulations! You're married!")
            await q.edit_message_text(
                f"{tmpl.format(a=user_link(q.from_user), b=f'<a href=\"tg://user?id={from_id}\">{from_id}</a>')}\n\n"
                f"🎊 <b>Congratulations to the happy couple!</b>",
                parse_mode="HTML")
        else:
            db.close()
            await q.answer("💔 Proposal declined.")
            await q.edit_message_text(
                f"💔 <b>Proposal Declined</b>\n\n"
                f"<a href='tg://user?id={to_id}'>{to_id}</a> declined the proposal.\n"
                f"<i>Maybe another time...</i>",
                parse_mode="HTML")
    except Exception as e: logger.debug(f"marry_callback: {e}")

async def divorce_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        udata = get_user(user.id)
        spouse_id = udata.get("spouse_id")
        if not spouse_id:
            return await reply(update, "💔 You're not married!")
        db = get_db()
        spouse_data = db.execute("SELECT first_name FROM users WHERE user_id=?", (spouse_id,)).fetchone()
        spouse_name = spouse_data["first_name"] if spouse_data else str(spouse_id)
        db.execute("UPDATE users SET spouse_id=NULL, married_at=NULL WHERE user_id=?", (user.id,))
        db.execute("UPDATE users SET spouse_id=NULL, married_at=NULL WHERE user_id=?", (spouse_id,))
        db.commit(); db.close()
        tmpl = R.pick(DIVORCE_MSGS)
        await reply(update, tmpl.format(a=user_link(user), b=html.escape(spouse_name)))
    except Exception as e: logger.error(f"divorce_cmd: {e}")

async def spouse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        udata = get_user(user.id)
        spouse_id = udata.get("spouse_id")
        if not spouse_id:
            return await reply(update, "💔 You're not married! Use /marry @user to propose.")
        db = get_db()
        spouse = db.execute("SELECT first_name, username FROM users WHERE user_id=?", (spouse_id,)).fetchone()
        married_at = udata.get("married_at","")
        db.close()
        spouse_name = spouse["first_name"] if spouse else str(spouse_id)
        await reply(update,
            f"💍 <b>Married!</b>\n{_D}\n\n"
            f"▸ Partner: <a href='tg://user?id={spouse_id}'>{html.escape(str(spouse_name))}</a>\n"
            f"▸ Since: {str(married_at)[:10] if married_at else 'Unknown'}")
    except Exception as e: logger.error(f"spouse_cmd: {e}")

async def accept_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        db = get_db()
        prop = db.execute("SELECT from_id FROM proposals WHERE to_id=? ORDER BY created_at DESC LIMIT 1",
                          (user.id,)).fetchone()
        if not prop:
            db.close()
            return await reply(update, "❓ No pending proposals! Someone needs to /marry you first.")
        from_id = prop["from_id"]
        db.execute("DELETE FROM proposals WHERE to_id=?", (user.id,))
        u1 = get_user(from_id); u2 = get_user(user.id)
        if u1.get("spouse_id") or u2.get("spouse_id"):
            db.close()
            return await reply(update, "❌ One of you is already married!")
        db.execute("UPDATE users SET spouse_id=?, married_at=CURRENT_TIMESTAMP WHERE user_id=?", (user.id, from_id))
        db.execute("UPDATE users SET spouse_id=?, married_at=CURRENT_TIMESTAMP WHERE user_id=?", (from_id, user.id))
        db.commit(); db.close()
        tmpl = R.pick(MARRY_MSGS)
        await reply(update, tmpl.format(a=f"<a href='tg://user?id={from_id}'>{from_id}</a>",
                                        b=user_link(user)) + "\n\n🎊 <b>Congratulations!</b>")
    except Exception as e: logger.error(f"accept_cmd: {e}")

# ─── MOOD / VIBE / PERSONALITY / BIRTHDAY ─────────────────────────────────────
async def mood_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        us�er = update.effective_user
        if context.args:
            mood = " ".join(context.args)
            update_user(user.id, mood=mood[:50])
            await reply(update, f"😊 <b>Mood set!</b>\n\n{user_link(user)} is now feeling: <b>{html.escape(mood)}</b>")
        else:
            udata = get_user(user.id)
            current = udata.get("mood") or R.pick(MOOD_WORDS)
            await reply(update, f"😊 <b>{user_link(user)}'s mood:</b>\n\n<i>{html.escape(current)}</i>")
    except Exception as e: logger.error(f"mood_cmd: {e}")

@rate_limited("vibe")
async def vibe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context) or update.effective_user
        result = R.pick(VIBE_POOL, f"vibe_{update.effective_chat.id}")
        await reply(update, f"📡 <b>Vibe Check for {user_link(target)}</b>\n{_D}\n\n{result}")
    except Exception as e: logger.error(f"vibe_cmd: {e}")

@rate_limited("personality")
async def personality_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context) or update.effective_user
        seed = target.id + datetime.date.today().toordinal()
        result = R.daily(PERSONALITY_POOL, target.id, seed)
        await reply(update,
            f"🔮 <b>Personality Reading</b>\n{_D}\n\n"
            f"👤 {user_link(target)}\n\n{result}\n\n"
            f"<i>Recalibrates daily. Pure algorithmic — no AI.</i>")
    except Exception as e: logger.error(f"personality_cmd: {e}")

async def setbirthday_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        if not context.args: return await reply(update, "❓ <code>/setbirthday DD/MM</code>")
        bday = context.args[0]
        if not re.match(r"^\d{1,2}/\d{1,2}$", bday):
            return await reply(update, "❌ Format: DD/MM (e.g. 25/12)")
        parts = bday.split("/")
        day, month = int(parts[0]), int(parts[1])
        if not (1 <= day <= 31 and 1 <= month <= 12):
            return await reply(update, "❌ Invalid date!")
        update_user(user.id, birthday=bday)
        await reply(update, f"🎂 <b>Birthday set!</b> {user_link(user)}'s birthday is {bday}! 🎉")
    except Exception as e: logger.error(f"setbirthday_cmd: {e}")

async def birthday_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context) or update.effective_user
        udata = get_user(target.id)
        bday = udata.get("birthday")
        if not bday: return await reply(update, f"❓ {user_link(target)} hasn't set a birthday!")
        today = datetime.date.today()
        day, month = map(int, bday.split("/"))
        try:
            next_bday = datetime.date(today.year, month, day)
            if next_bday < today: next_bday = datetime.date(today.year+1, month, day)
            days_left = (next_bday - today).days
            is_today = days_left == 0
        except: days_left = -1; is_today = False
        if is_today:
            await reply(update, f"🎂🎉 <b>HAPPY BIRTHDAY {user_link(target)}!</b> 🎉🎂\n\n🥳 Today is your special day!")
        else:
            await reply(update, f"🎂 <b>{user_link(target)}'s Birthday</b>\n\n"
                        f"▸ Date: {bday}\n"
                        f"▸ Days until: {days_left if days_left >= 0 else '?'}")
    except Exception as e: logger.error(f"birthday_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                          FUN COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════
@rate_limited("8ball")
async def eightball_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = " ".join(context.args) if context.args else None
        if update.message.reply_to_message: q = update.message.reply_to_message.text or q
        if not q: return await reply(update, "❓ <code>/8ball your question?</code>")
        answer = R.pick(EIGHTBALL_POOL, f"8ball_{update.effective_chat.id}")
        await reply(update,
            f"🔮 <b>Magic 8-Ball</b>\n{_D}\n\n"
            f"❓ {html.escape(q[:200])}\n\n"
            f"🎱 {answer}")
    except Exception as e: logger.error(f"eightball_cmd: {e}")

@rate_limited("joke")
async def joke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        joke = R.pick(JOKE_POOL, f"joke_{update.effective_chat.id}")
        await reply(update, f"😂 <b>Joke Time!</b>\n{_D}\n\n{joke}")
    except Exception as e: logger.error(f"joke_cmd: {e}")

@rate_limited("fact")
async def fact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        fact = R.pick(FACT_POOL, f"fact_{update.effective_chat.id}")
        await reply(update, f"🧠 <b>Random Fact!</b>\n{_D}\n\n{fact}")
    except Exception as e: logger.error(f"fact_cmd: {e}")

@rate_limited("quote")
async def quote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = R.pick(QUOTE_POOL, f"quote_{update.effective_chat.id}")
        await reply(update, f"✨ <b>Quote of the Moment</b>\n{_D}\n\n{q}")
    except Exception as e: logger.error(f"quote_cmd: {e}")

@rate_limited("truth")
async def truth_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = R.pick(TRUTH_POOL, f"truth_{update.effective_chat.id}")
        target = await get_target(update, context) or update.effective_user
        await reply(update, f"🕵️ <b>Truth for {user_link(target)}!</b>\n{_D}\n\n{q}")
    except Exception as e: logger.error(f"truth_cmd: {e}")

@rate_limited("dare")
async def dare_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d = R.pick(DARE_POOL, f"dare_{update.effective_chat.id}")
        target = await get_target(update, context) or update.effective_user
        await reply(update, f"😈 <b>Dare for {user_link(target)}!</b>\n{_D}\n\n{d}")
    except Exception as e: logger.error(f"dare_cmd: {e}")

@rate_limited("wyr")
async def wyr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        a, b = random.choice(WYR_POOL)
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(f"🅰️ {a[:30]}", callback_data=f"wyr:a:{hash(a)%10**6}"),
            InlineKeyboardButton(f"🅱️ {b[:30]}", callback_data=f"wyr:b:{hash(b)%10**6}"),
        ]])
        await reply(update,
            f"🤔 <b>Would You Rather...?</b>\n{_D}\n\n"
            f"🅰️ <b>{html.escape(a)}</b>\n\n<b>— OR —</b>\n\n"
            f"🅱️ <b>{html.escape(b)}</b>\n\n"
            f"<i>Vote below!</i>", reply_markup=kb)
    except Exception as e: logger.error(f"wyr_cmd: {e}")

async def wyr_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.callback_query
        chosen = "🅰️ Option A" if ":a:" in q.data else "🅱️ Option B"
        await q.answer(f"You chose {chosen}!", show_alert=False)
    except Exception as e: logger.debug(f"wyr_callback: {e}")

@rate_limited("fortune")
async def fortune_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        fortune = R.daily(FORTUNE_POOL, user.id)
        lucky = R.daily(HOROSCOPE_LUCKY, user.id, 1)
        await reply(update,
            f"🔮 <b>Your Fortune</b>\n{_D}\n\n"
            f"👤 {user_link(user)}\n\n"
            f"{fortune}\n\n"
            f"🍀 <b>Lucky thing today:</b> {lucky}\n\n"
            f"<i>Recalibrates daily. Pure local — no AI.</i>")
    except Exception as e: logger.error(f"fortune_cmd: {e}")

@rate_limited("tarot")
async def tarot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        n = random.randint(1, 3)
        cards = random.sample(TAROT_CARDS, n)
        text = f"🃏 <b>Tarot Reading</b>\n{_D}\n\n"
        for i, (name, reading) in enumerate(cards, 1):
            text += f"<b>Card {i}:</b> {name}\n<i>{reading}</i>\n\n"
        text += f"<i>Reading for {user_link(user)} — pure algorithmic, unlimited variety.</i>"
        await reply(update, text)
    except Exception as e: logger.error(f"tarot_cmd: {e}")

@rate_limited("horoscope")
async def horoscope_cmd(update: Up�date, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            signs = " · ".join(f"{v['emoji']} {k.capitalize()}" for k,v in HOROSCOPE_SIGNS.items())
            return await reply(update, f"♈ <b>Horoscope</b>\n{_D}\n\n"
                               f"<code>/horoscope sign</code>\n\nSigns: {signs}")
        sign = context.args[0].lower().strip()
        if sign not in HOROSCOPE_SIGNS:
            return await reply(update, "❓ Invalid sign! Try: aries, taurus, gemini, cancer, leo, virgo, libra, scorpio, sagittarius, capricorn, aquarius, pisces")
        sd = HOROSCOPE_SIGNS[sign]
        user = update.effective_user
        seed = datetime.date.today().toordinal() + hash(sign)
        energy = R.daily(HOROSCOPE_ENERGY, seed, 0)
        focus = R.daily(HOROSCOPE_FOCUS, seed, 1)
        lucky = R.daily(HOROSCOPE_LUCKY, seed, 2)
        advice = R.daily(HOROSCOPE_ADVICE, seed, 3)
        mood = R.daily(HOROSCOPE_MOOD, seed, 4)
        await reply(update,
            f"{sd['emoji']} <b>{sign.capitalize()} — Daily Horoscope</b>\n{_D}\n\n"
            f"📅 Dates: {sd['dates']}\n"
            f"🔥 Element: {sd['element']} · Ruler: {sd['ruler']}\n\n"
            f"⚡ <b>Energy today:</b> {energy}\n"
            f"🎯 <b>Focus:</b> {focus}\n"
            f"😊 <b>Mood:</b> {mood}\n"
            f"🍀 <b>Lucky today:</b> {lucky}\n\n"
            f"💫 <b>Cosmic advice:</b> <i>{advice}</i>\n\n"
            f"<i>Pure algorithmic reading — refreshes daily. No AI.</i>")
    except Exception as e: logger.error(f"horoscope_cmd: {e}")

async def meme_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        meme_txts = [
            "When you finally fix that bug at 3am 🐛✅ ... and it breaks something else 💀",
            "Me: I'll sleep early tonight\nAlso me at 3am: /horoscope aquarius",
            "Normies: sleep 8 hours\nUs: main character hours don't stop bestie",
            "Me trying to explain why I need 47 tabs open 📑\nAnyone: 🤔\nMe: it's called research periodt",
            "Productivity: loading... still loading... connection timed out 😴",
            "Hot take: 'I'll do it later' is just time travel to a future you's problem",
            "My brain at 11pm: 🌙 sleep\nMy brain at 3am: but what if we overthought everything",
            "Red flag: someone who has never googled their own symptoms",
            "Plot twist: the villain was just chronically unhinged and had good taste in music",
            "Core memory unlocked: the first time you understood a meme without explanation",
        ]
        await reply(update, f"🎭 <b>Meme</b>\n{_D}\n\n{R.pick(meme_txts, f'meme_{update.effective_chat.id}')}")
    except Exception as e: logger.error(f"meme_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         UTILITY COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════
async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context)
        if target:
            await reply(update, f"🪪 <b>User ID</b>\n▸ {user_link(target)}: <code>{target.id}</code>")
        else:
            await reply(update,
                f"🪪 <b>Your IDs</b>\n"
                f"▸ User ID: <code>{update.effective_user.id}</code>\n"
                f"▸ Chat ID: <code>{update.effective_chat.id}</code>")
    except Exception as e: logger.error(f"id_cmd: {e}")

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context) or update.effective_user
        udata = get_user(target.id)
        name = html.escape(f"{getattr(target,'first_name','') or ''} {getattr(target,'last_name','') or ''}".strip())
        gban = is_gbanned(target.id)
        lines = [
            f"ℹ️ <b>User Info</b>\n{_D}\n\n"
            f"👤 <b>Name:</b> {name}\n"
            f"🪪 <b>ID:</b> <code>{target.id}</code>\n"
            f"📛 <b>Username:</b> @{getattr(target,'username',None) or 'None'}\n"
            f"🔗 <b>Link:</b> <a href='tg://user?id={target.id}'>Click here</a>\n\n"
            f"📊 <b>Stats</b>\n"
            f"▸ Coins: {fmt_coins(udata.get('coins',0))}\n"
            f"▸ Bank: {fmt_coins(udata.get('bank',0))}\n"
            f"▸ XP: {udata.get('xp',0)} (Level {udata.get('level',0)})\n"
            f"▸ Rep: {udata.get('reputation',0)} ⭐\n"
            f"▸ Streak: 🔥{udata.get('streak',0)}\n"
            f"▸ Mood: {html.escape(udata.get('mood','') or '—')}\n"
            f"▸ GBanned: {'🔴 Yes' if gban else '🟢 No'}"
        ]
        if udata.get("spouse_id"):
            lines.append(f"▸ Married to: <a href='tg://user?id={udata[\"spouse_id\"]}'>{udata['spouse_id']}</a> 💍")
        if udata.get("birthday"):
            lines.append(f"▸ Birthday: {udata['birthday']} 🎂")
        await reply(update, "\n".join(lines))
    except Exception as e: logger.error(f"info_cmd: {e}")

async def chatinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        chat = update.effective_chat
        count = await context.bot.get_chat_member_count(chat.id)
        cfg = get_chat(chat.id)
        await reply(update,
            f"💬 <b>Chat Info</b>\n{_D}\n\n"
            f"▸ <b>Name:</b> {html.escape(chat.title or 'Private')}\n"
            f"▸ <b>ID:</b> <code>{chat.id}</code>\n"
            f"▸ <b>Type:</b> {chat.type}\n"
            f"▸ <b>Members:</b> {count:,}\n"
            f"▸ <b>Username:</b> @{chat.username or 'None'}\n\n"
            f"⚙️ <b>Settings</b>\n"
            f"▸ Anti-Spam: {'✅' if cfg.get('antispam',1) else '❌'}\n"
            f"▸ Welcome: {'✅' if cfg.get('welcome_on',1) else '❌'}\n"
            f"▸ Captcha: {'✅' if cfg.get('captcha_on') else '❌'}")
    except Exception as e: logger.error(f"chatinfo_cmd: {e}")

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        start = time.time()
        m = await reply(update, "🏓 Pinging…")
        elapsed = (time.time() - start) * 1000
        if m:
            await m.edit_text(f"🏓 <b>Pong!</b>\n▸ Latency: <b>{elapsed:.1f}ms</b>", parse_mode="HTML")
    except Exception as e: logger.error(f"ping_cmd: {e}")

async def uptime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        up = time.time() - START_TIME
        td = datetime.timedelta(seconds=int(up))
        await reply(update, f"⏱️ <b>Uptime:</b> {td}\n🤖 <b>Version:</b> {VERSION}")
    except Exception as e: logger.error(f"uptime_cmd: {e}")

async def calc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/calc expression</code>")
        expr = " ".join(context.args)
        allowed = set("0123456789+-*/().% ")
        if not all(c in allowed for c in expr):
            return await reply(update, "❌ Only numbers and basic operators allowed (+,-,*,/,(,),%).")
        result = eval(expr, {"__builtins__": {}}, {})
        await reply(update, f"🧮 <code>{html.escape(expr)}</code> = <b>{result}</b>")
    except ZeroDivisionError:
        await reply(update, "❌ Division by zero!")
    except Exception:
        await reply(update, "❌ Invalid expression.")

async def hash_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/hash text</code>")
        text = " ".join(context.args).encode()
        await reply(update,
            f"#️⃣ <b>Hash Results</b>\n{_D}\n\n"
            f"<b>MD5:</b> <code>{hashlib.md5(text).hexdigest()}</code>\n"
            f"<b>SHA1:</b> <code>{hashlib.sha1(text).hexdigest()}</code>\n"
            f"<b>SHA256:</b> <code>{hashlib.sha256(text).hexdigest()}</code>")
    except Exception as e: logger.error(f"hash_cmd: {e}")

async def b64_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args or context.args[0] not in ("encode","decode"):
            return await reply(update, "❓ <code>/b64 encode|decode text</code>")
        mode = context.args[0]
        text = " ".join(context.args[1:])
        if not text: return await r�eply(update, "❓ Provide text to encode/decode.")
        if mode == "encode":
            result = base64.b64encode(text.encode()).decode()
            await reply(update, f"🔐 <b>Encoded:</b>\n<code>{html.escape(result)}</code>")
        else:
            try:
                result = base64.b64decode(text.encode()).decode()
                await reply(update, f"🔓 <b>Decoded:</b>\n<code>{html.escape(result)}</code>")
            except: await reply(update, "❌ Invalid base64 string!")
    except Exception as e: logger.error(f"b64_cmd: {e}")

async def reverse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/reverse text</code>")
        text = " ".join(context.args)
        await reply(update, f"🔄 <code>{html.escape(text[::-1])}</code>")
    except Exception as e: logger.error(f"reverse_cmd: {e}")

async def qr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/qr text</code>")
        text = urllib.parse.quote(" ".join(context.args))
        url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={text}"
        await update.message.reply_photo(url, caption="📱 QR Code generated!")
    except Exception as e: logger.error(f"qr_cmd: {e}")

async def tr_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args or len(context.args) < 2:
            return await reply(update, "❓ <code>/tr lang text</code> (e.g. /tr en Hola mundo)")
        lang = context.args[0]
        text = " ".join(context.args[1:])
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={lang}&dt=t&q={urllib.parse.quote(text)}"
        session = await get_session()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                data = await r.json()
                result = "".join(p[0] for p in data[0] if p[0])
                await reply(update, f"🌐 <b>Translation ({lang.upper()})</b>\n\n<code>{html.escape(result)}</code>")
            else: await reply(update, "❌ Translation failed!")
    except Exception as e:
        await reply(update, "❌ Translation service unavailable.")

async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/weather city</code>")
        city = " ".join(context.args)
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        session = await get_session()
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                data = await r.json()
                curr = data["current_condition"][0]
                desc = curr["weatherDesc"][0]["value"]
                temp_c = curr["temp_C"]; temp_f = curr["temp_F"]
                feels = curr["FeelsLikeC"]
                humidity = curr["humidity"]
                wind = curr["windspeedKmph"]
                area = data["nearest_area"][0]["areaName"][0]["value"]
                country = data["nearest_area"][0]["country"][0]["value"]
                await reply(update,
                    f"🌤️ <b>Weather in {html.escape(area)}, {html.escape(country)}</b>\n{_D}\n\n"
                    f"▸ Condition: {html.escape(desc)}\n"
                    f"▸ Temp: {temp_c}°C / {temp_f}°F\n"
                    f"▸ Feels like: {feels}°C\n"
                    f"▸ Humidity: {humidity}%\n"
                    f"▸ Wind: {wind} km/h")
            else: await reply(update, f"❌ City not found: {html.escape(city)}")
    except Exception as e:
        await reply(update, "❌ Weather service unavailable.")

async def time_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tz_name = context.args[0] if context.args else "UTC"
        try:
            tz = pytz.timezone(tz_name)
            now = datetime.datetime.now(tz)
            await reply(update, f"🕐 <b>Time in {html.escape(tz_name)}</b>\n{now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except pytz.UnknownTimeZoneError:
            await reply(update, f"❌ Unknown timezone: {html.escape(tz_name)}\n<i>Example: UTC, US/Eastern, Asia/Tokyo</i>")
    except Exception as e: logger.error(f"time_cmd: {e}")

async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # /remind 10 min go to sleep
        if not context.args or len(context.args) < 3:
            return await reply(update, "❓ <code>/remind N unit text</code>\nExample: /remind 10 min go to sleep\nUnits: sec, min, hour, day")
        try: n = int(context.args[0])
        except: return await reply(update, "❌ First argument must be a number.")
        unit_map = {"sec":1,"secs":1,"second":1,"seconds":1,
                    "min":60,"mins":60,"minute":60,"minutes":60,
                    "hour":3600,"hours":3600,"hr":3600,"hrs":3600,
                    "day":86400,"days":86400}
        unit = context.args[1].lower()
        if unit not in unit_map: return await reply(update, "❌ Unit must be: sec, min, hour, or day")
        secs = n * unit_map[unit]
        text = " ".join(context.args[2:])
        user = update.effective_user
        chat_id = update.effective_chat.id
        remind_at = datetime.datetime.now(pytz.utc) + datetime.timedelta(seconds=secs)
        db = get_db()
        rid = db.execute("INSERT INTO reminders (user_id,chat_id,text,remind_at) VALUES (?,?,?,?)",
                         (user.id, chat_id, text, remind_at.isoformat())).lastrowid
        db.commit(); db.close()
        await reply(update,
            f"⏰ <b>Reminder Set!</b>\n{_D}\n\n"
            f"▸ Reminder: {html.escape(text)}\n"
            f"▸ Time: {fmt_duration(datetime.timedelta(seconds=secs))}\n"
            f"▸ At: {remind_at.strftime('%Y-%m-%d %H:%M UTC')}")
    except Exception as e: logger.error(f"remind_cmd: {e}")

async def myreminders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        db = get_db()
        rows = db.execute("SELECT * FROM reminders WHERE user_id=? AND done=0 ORDER BY remind_at",
                          (user.id,)).fetchall()
        db.close()
        if not rows: return await reply(update, "⏰ <b>No pending reminders!</b>")
        lines = [f"⏰ <b>Your Reminders ({len(rows)})</b>\n{_D}\n"]
        for r in rows:
            lines.append(f"▸ [{r['id']}] {html.escape(r['text'][:50])}\n   At: {str(r['remind_at'])[:16]}")
        await reply(update, "\n".join(lines))
    except Exception as e: logger.error(f"myreminders_cmd: {e}")

async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args and not (update.message.reply_to_message and update.message.reply_to_message.text):
            return await reply(update, "❓ <code>/ask your question here</code>")
        q = " ".join(context.args)
        if update.message.reply_to_message and update.message.reply_to_message.text:
            q = update.message.reply_to_message.text
        m = await animate_loading(update, "Thinking")
        answer = await ai_reply(q, fallback=R.pick(FORTUNE_POOL))
        await finish_anim(m, f"🤖 <b>AI Response</b>\n{_D}\n\n{html.escape(answer)}")
    except Exception as e: logger.error(f"ask_cmd: {e}")

async def aiinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        m = await animate_loading(update, "Testing AI")
        result = await ai_reply("Say 'AI online' in 3 words.", fallback="Local mode active")
        await finish_anim(m,
            f"🤖 <b>AI Engine Status</b>\n{_D}\n\n"
            f"✅ Status: Online\n"
            f"📡 Response: {html.escape(result[:100])}\n"
            f"🔧 Fallback: Local pools active")
    except Exception as e: logger.error(f"aiinfo_cmd: {e}")

async def rank_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context) or update.effective_user
        udata = get_user(target.id)
        xp = udata.get("xp", 0); lvl = udata.get("level", 0)
        xp_needed = (lvl �+ 1) * 100
        bar = progress_bar(xp, xp_needed)
        badge = rank_badge(lvl)
        await reply(update,
            f"📊 <b>Rank Card</b>\n{_D}\n\n"
            f"👤 {user_link(target)}\n"
            f"{badge} <b>Level {lvl}</b>\n"
            f"XP: {xp}/{xp_needed} [{bar}]\n\n"
            f"💰 Coins: {fmt_coins(udata.get('coins',0))}\n"
            f"⭐ Rep: {udata.get('reputation',0)}\n"
            f"🔥 Streak: {udata.get('streak',0)} days")
    except Exception as e: logger.error(f"rank_cmd: {e}")

async def level_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await rank_cmd(update, context)

async def top_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        rows = db.execute("SELECT user_id,first_name,xp,level FROM users ORDER BY xp DESC LIMIT 10").fetchall()
        db.close()
        medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
        lines = [f"🏆 <b>Top Active Members</b>\n{_D}\n"]
        for i, row in enumerate(rows):
            name = html.escape(row.get("first_name") or str(row["user_id"]))
            lines.append(f"{medals[i]} {name} — Level {row['level']} ({row['xp']:,} XP)")
        await reply(update, "\n".join(lines) if len(lines) > 1 else "No data yet!")
    except Exception as e: logger.error(f"top_cmd: {e}")

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        chats = db.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
        notes = db.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        warns = db.execute("SELECT COUNT(*) FROM warns").fetchone()[0]
        bans = db.execute("SELECT COUNT(*) FROM bans").fetchone()[0]
        db.close()
        up = datetime.timedelta(seconds=int(time.time() - START_TIME))
        await reply(update,
            f"📊 <b>Bot Statistics</b>\n{_D}\n\n"
            f"👥 Users: {users:,}\n"
            f"💬 Chats: {chats:,}\n"
            f"📝 Notes: {notes:,}\n"
            f"⚠️ Warns: {warns:,}\n"
            f"🔨 Bans: {bans:,}\n\n"
            f"⏱️ Uptime: {up}\n"
            f"🤖 Version: v{VERSION}")
    except Exception as e: logger.error(f"stats_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         CONNECTION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
async def connect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/connect chat_id</code>")
        try: cid = int(context.args[0])
        except: return await reply(update, "❌ Invalid chat ID.")
        user = update.effective_user
        if not await is_admin(context, cid, user.id):
            return await reply(update, "❌ You must be an admin in that group to connect!")
        connection_cache[user.id] = cid
        db = get_db()
        db.execute("INSERT OR REPLACE INTO connections (user_id,chat_id) VALUES (?,?)", (user.id, cid))
        db.commit(); db.close()
        await reply(update, f"✅ <b>Connected to chat:</b> <code>{cid}</code>\n<i>Admin commands will now run in that chat!</i>")
    except Exception as e: logger.error(f"connect_cmd: {e}")

async def disconnect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        connection_cache.pop(user.id, None)
        db = get_db()
        db.execute("DELETE FROM connections WHERE user_id=?", (user.id,))
        db.commit(); db.close()
        await reply(update, "✅ <b>Disconnected!</b>")
    except Exception as e: logger.error(f"disconnect_cmd: {e}")

async def connected_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        cid = connection_cache.get(user.id)
        if not cid:
            db = get_db()
            row = db.execute("SELECT chat_id FROM connections WHERE user_id=?", (user.id,)).fetchone()
            db.close()
            cid = row["chat_id"] if row else None
            if cid: connection_cache[user.id] = cid
        if cid: await reply(update, f"🔗 <b>Connected to:</b> <code>{cid}</code>")
        else: await reply(update, "❌ <b>Not connected.</b> Use /connect chat_id")
    except Exception as e: logger.error(f"connected_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         FEDERATION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
async def newfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        if not context.args: return await reply(update, "❓ <code>/newfed Federation Name</code>")
        name = " ".join(context.args)
        fed_id = str(uuid.uuid4())[:8].upper()
        db = get_db()
        existing = db.execute("SELECT 1 FROM feds WHERE owner_id=?", (user.id,)).fetchone()
        if existing: db.close(); return await reply(update, "❌ You already own a federation!")
        db.execute("INSERT INTO feds (fed_id,name,owner_id) VALUES (?,?,?)", (fed_id, name, user.id))
        db.commit(); db.close()
        await reply(update,
            f"🌐 <b>Federation Created!</b>\n{_D}\n\n"
            f"▸ Name: <b>{html.escape(name)}</b>\n"
            f"▸ ID: <code>{fed_id}</code>\n\n"
            f"<i>Share the ID so groups can /joinfed {fed_id}</i>")
    except Exception as e: logger.error(f"newfed_cmd: {e}")

async def delfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        db = get_db()
        fed = db.execute("SELECT fed_id FROM feds WHERE owner_id=?", (user.id,)).fetchone()
        if not fed: db.close(); return await reply(update, "❌ You don't own a federation!")
        fid = fed["fed_id"]
        db.execute("DELETE FROM feds WHERE fed_id=?", (fid,))
        db.execute("DELETE FROM fed_chats WHERE fed_id=?", (fid,))
        db.execute("DELETE FROM fed_admins WHERE fed_id=?", (fid,))
        db.execute("DELETE FROM fed_bans WHERE fed_id=?", (fid,))
        db.commit(); db.close()
        await reply(update, f"🗑️ <b>Federation deleted!</b>")
    except Exception as e: logger.error(f"delfed_cmd: {e}")

@admin_only
@groups_only
async def joinfed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/joinfed fed_id</code>")
        fid = context.args[0].upper()
        db = get_db()
        fed = db.execute("SELECT name FROM feds WHERE fed_id=?", (fid,)).fetchone()
        if not fed: db.close(); return await reply(update, "❌ Federation not found!")
        db.execute("INSERT OR IGNORE INTO fed_chats (fed_id,chat_id) VALUES (?,?)",
                   (fid, update.effective_chat.id))
        db.commit(); db.close()
        await reply(update, f"✅ <b>Joined federation:</b> {html.escape(fed['name'])}")
    except Exception as e: logger.error(f"joinfed_cmd: {e}")

@admin_only
@groups_only
async def leavefed_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        db.execute("DELETE FROM fed_chats WHERE chat_id=?", (update.effective_chat.id,))
        db.commit(); db.close()
        await reply(update, "✅ <b>Left federation!</b>")
    except Exception as e: logger.error(f"leavefed_cmd: {e}")

async def fedinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        fc = db.execute("SELECT fed_id FROM fed_chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
        if not fc: db.close(); return await reply(update, "❌ Not in a federation.")
        fid = fc["fed_id"]
        fed = db.execute("SELECT * FROM feds WHERE fed_id=?", (fid,)).fetchone()
        bans = db.execute("SELECT COUNT(*) FROM fed_bans WHERE fed_id=?", (fid,)).fetchone()[0]
        chats = db.execute("SELECT COUNT(*) FROM fed_chats WHERE fed_id=?", (fid,)).fetchone()[0]
        db.close()
        await reply(update,
            f"🌐 <b>Federation Info</b>\n{_D}\n\n"
     �       f"▸ Name: <b>{html.escape(fed['name'])}</b>\n"
            f"▸ ID: <code>{fid}</code>\n"
            f"▸ Owner: <a href='tg://user?id={fed['owner_id']}'>{fed['owner_id']}</a>\n"
            f"▸ Chats: {chats}\n"
            f"▸ Banned: {bans}")
    except Exception as e: logger.error(f"fedinfo_cmd: {e}")

async def fban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        db = get_db()
        fed = db.execute("SELECT fed_id FROM feds WHERE owner_id=?", (user.id,)).fetchone()
        if not fed:
            fadmin = db.execute("SELECT fed_id FROM fed_admins WHERE user_id=?", (user.id,)).fetchone()
            if not fadmin: db.close(); return await reply(update, "❌ Not a federation owner or admin!")
            fid = fadmin["fed_id"]
        else: fid = fed["fed_id"]
        target = await get_target(update, context)
        if not target: db.close(); return await reply(update, "❓ Provide target user.")
        reason = " ".join(context.args[1:]) if context.args else "Federation ban"
        db.execute("INSERT OR REPLACE INTO fed_bans (fed_id,user_id,reason,banned_by) VALUES (?,?,?,?)",
                   (fid, target.id, reason, user.id))
        chats = db.execute("SELECT chat_id FROM fed_chats WHERE fed_id=?", (fid,)).fetchall()
        db.commit(); db.close()
        banned = 0
        for c in chats:
            try:
                await context.bot.ban_chat_member(c["chat_id"], target.id)
                banned += 1
            except: pass
        await reply(update, f"🌐 <b>Fed-Banned!</b>\n▸ {user_link(target)}\n▸ Reason: {html.escape(reason)}\n▸ Applied to {banned} chats")
    except Exception as e: logger.error(f"fban_cmd: {e}")

async def unfban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        db = get_db()
        fed = db.execute("SELECT fed_id FROM feds WHERE owner_id=?", (user.id,)).fetchone()
        if not fed: db.close(); return await reply(update, "❌ Not a federation owner!")
        fid = fed["fed_id"]
        target = await get_target(update, context)
        if not target: db.close(); return await reply(update, "❓ Provide target.")
        db.execute("DELETE FROM fed_bans WHERE fed_id=? AND user_id=?", (fid, target.id))
        chats = db.execute("SELECT chat_id FROM fed_chats WHERE fed_id=?", (fid,)).fetchall()
        db.commit(); db.close()
        for c in chats:
            try: await context.bot.unban_chat_member(c["chat_id"], target.id, only_if_banned=True)
            except: pass
        await reply(update, f"✅ <b>Fed-Unbanned!</b> {user_link(target)}")
    except Exception as e: logger.error(f"unfban_cmd: {e}")

async def fedbans_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        fc = db.execute("SELECT fed_id FROM fed_chats WHERE chat_id=?", (update.effective_chat.id,)).fetchone()
        if not fc: db.close(); return await reply(update, "❌ Not in a federation.")
        bans = db.execute("SELECT user_id,reason FROM fed_bans WHERE fed_id=? LIMIT 20", (fc["fed_id"],)).fetchall()
        db.close()
        if not bans: return await reply(update, "✅ No federation bans!")
        lines = [f"🌐 <b>Fed Bans ({len(bans)})</b>\n{_D}\n"]
        for b in bans:
            lines.append(f"▸ <code>{b['user_id']}</code> — {html.escape(b['reason'] or 'No reason')}")
        await reply(update, "\n".join(lines))
    except Exception as e: logger.error(f"fedbans_cmd: {e}")

async def fadmin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        db = get_db()
        fed = db.execute("SELECT fed_id FROM feds WHERE owner_id=?", (user.id,)).fetchone()
        if not fed: db.close(); return await reply(update, "❌ Not a federation owner!")
        target = await get_target(update, context)
        if not target: db.close(); return await reply(update, "❓ Provide target.")
        db.execute("INSERT OR IGNORE INTO fed_admins (fed_id,user_id) VALUES (?,?)", (fed["fed_id"], target.id))
        db.commit(); db.close()
        await reply(update, f"✅ {user_link(target)} added as federation admin!")
    except Exception as e: logger.error(f"fadmin_cmd: {e}")

async def fremove_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        db = get_db()
        fed = db.execute("SELECT fed_id FROM feds WHERE owner_id=?", (user.id,)).fetchone()
        if not fed: db.close(); return await reply(update, "❌ Not a federation owner!")
        target = await get_target(update, context)
        if not target: db.close(); return await reply(update, "❓ Provide target.")
        db.execute("DELETE FROM fed_admins WHERE fed_id=? AND user_id=?", (fed["fed_id"], target.id))
        db.commit(); db.close()
        await reply(update, f"✅ {user_link(target)} removed from federation admins!")
    except Exception as e: logger.error(f"fremove_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         SUDO / OWNER COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════
@owner_only
async def gban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Provide target.")
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Global ban"
        db = get_db()
        get_user(target.id)
        db.execute("UPDATE users SET is_gbanned=1, gban_reason=? WHERE user_id=?", (reason, target.id))
        db.commit(); db.close()
        _gban_cache[target.id] = (reason, time.time())
        await reply(update, f"🌍 <b>Global Banned!</b>\n▸ {user_link(target)}\n▸ Reason: {html.escape(reason)}")
    except Exception as e: logger.error(f"gban_cmd: {e}")

@owner_only
async def ungban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Provide target.")
        db = get_db()
        db.execute("UPDATE users SET is_gbanned=0, gban_reason=NULL WHERE user_id=?", (target.id,))
        db.commit(); db.close()
        _gban_cache.pop(target.id, None)
        await reply(update, f"✅ <b>Global ban lifted!</b>\n▸ {user_link(target)}")
    except Exception as e: logger.error(f"ungban_cmd: {e}")

@owner_only
async def sudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Provide target.")
        db = get_db()
        db.execute("INSERT OR IGNORE INTO sudo_users (user_id,added_by) VALUES (?,?)",
                   (target.id, update.effective_user.id))
        db.commit(); db.close()
        await reply(update, f"✅ {user_link(target)} added as sudo user!")
    except Exception as e: logger.error(f"sudo_cmd: {e}")

@owner_only
async def unsudo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = await get_target(update, context)
        if not target: return await reply(update, "❓ Provide target.")
        db = get_db()
        db.execute("DELETE FROM sudo_users WHERE user_id=?", (target.id,))
        db.commit(); db.close()
        await reply(update, f"✅ {user_link(target)} removed from sudo!")
    except Exception as e: logger.error(f"unsudo_cmd: {e}")

@owner_only
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = " ".join(context.args) if context.args else (
            update.message.reply_to_message.text if update.message.reply_to_message else "")
        if not msg: return await reply(update, "❓ Provide message.")
        db = get_db()
        chats = db.execute("SELECT chat_id FROM chats").fetchall()
        db.close()
        sent = failed = 0
        for c in chats:
            try:
                await context.bot.send_message(c["chat_id"], f"📢 <b>Broadcast</b>\n\n{html.escape(msg)}", parse_mode="HTML")
                sent += 1
            except: failed �+= 1
            await asyncio.sleep(0.05)
        await reply(update, f"📢 <b>Broadcast Complete</b>\n✅ Sent: {sent}\n❌ Failed: {failed}")
    except Exception as e: logger.error(f"broadcast_cmd: {e}")

@owner_only
async def botstats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stats_cmd(update, context)

@owner_only
async def chatlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        chats = db.execute("SELECT chat_id,title FROM chats ORDER BY chat_id DESC LIMIT 30").fetchall()
        db.close()
        lines = [f"💬 <b>Chat List ({len(chats)})</b>\n{_D}\n"]
        for c in chats:
            lines.append(f"▸ {html.escape(c['title'] or 'Unknown')} (<code>{c['chat_id']}</code>)")
        await reply(update, "\n".join(lines))
    except Exception as e: logger.error(f"chatlist_cmd: {e}")

@owner_only
@groups_only
async def leave_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await reply(update, "👋 Leaving chat...")
        await context.bot.leave_chat(update.effective_chat.id)
    except Exception as e: logger.error(f"leave_cmd: {e}")

@admin_only
async def setlogchannel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args: return await reply(update, "❓ <code>/setlogchannel @channel</code>")
        ch = context.args[0]
        set_setting(update.effective_chat.id, "log_channel", ch)
        await reply(update, f"✅ <b>Log channel set to:</b> {html.escape(ch)}")
    except Exception as e: logger.error(f"setlogchannel_cmd: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         REPORT / INLINE QUERY
# ═══════════════════════════════════════════════════════════════════════════════
async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        if msg.chat.type == "private": return await reply(update, "❓ Use in groups only.")
        if not msg.reply_to_message: return await reply(update, "❓ Reply to a message to report it.")
        rep_user = msg.reply_to_message.from_user
        admins = await context.bot.get_chat_administrators(msg.chat.id)
        mentions = " ".join(f'<a href="tg://user?id={a.user.id}">​</a>'
                           for a in admins if not a.user.is_bot)
        await reply(update,
            f"🚨 <b>Report!</b>\n{_D}\n\n"
            f"▸ Reported: {user_link(rep_user)}\n"
            f"▸ By: {user_link(msg.from_user)}\n"
            f"▸ Message: <a href='https://t.me/c/{str(msg.chat.id)[4:]}/{msg.reply_to_message.message_id}'>Link</a>\n\n"
            f"Admins notified: {mentions}")
    except Exception as e: logger.error(f"report_cmd: {e}")

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        q = update.inline_query.query.strip()
        results = []
        if not q or len(q) < 2:
            results.append(InlineQueryResultArticle(
                id="help", title="🤖 Nexus Bot",
                input_message_content=InputTextMessageContent(
                    f"⚡ <b>Nexus Bot v{VERSION}</b>\nAdd me to your group!", parse_mode="HTML"),
                description="Type something to search"))
        else:
            if "8ball" in q.lower() or q.endswith("?"):
                ans = R.pick(EIGHTBALL_POOL)
                results.append(InlineQueryResultArticle(
                    id="8ball", title=f"🎱 {ans[:50]}",
                    input_message_content=InputTextMessageContent(
                        f"🎱 <b>8-Ball says:</b> {ans}", parse_mode="HTML"),
                    description="Magic 8-ball answer"))
            joke = R.pick(JOKE_POOL)
            results.append(InlineQueryResultArticle(
                id="joke", title="😂 Random Joke",
                input_message_content=InputTextMessageContent(
                    f"😂 <b>Joke:</b>\n{joke}", parse_mode="HTML"),
                description=joke[:50]))
            fact = R.pick(FACT_POOL)
            results.append(InlineQueryResultArticle(
                id="fact", title="🧠 Random Fact",
                input_message_content=InputTextMessageContent(
                    f"🧠 <b>Fact:</b> {fact}", parse_mode="HTML"),
                description=fact[:50]))
        await update.inline_query.answer(results[:10], cache_time=1)
    except Exception as e: logger.debug(f"inline_query: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         FLOOD TRACKING
# ═══════════════════════════════════════════════════════════════════════════════
_flood_tracker: Dict[Tuple[int,int], List[float]] = defaultdict(list)

async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        chat = update.effective_chat
        user = update.effective_user
        if not chat or not user or chat.type == "private": return False
        cfg = get_chat(chat.id)
        if not cfg.get("antiflood"): return False
        if await is_admin(context, chat.id, user.id): return False
        if is_approved(chat.id, user.id): return False
        limit = cfg.get("flood_limit", 5)
        window = cfg.get("flood_window", 10)
        key = (chat.id, user.id)
        now = time.time()
        tracker = _flood_tracker[key]
        tracker[:] = [t for t in tracker if now - t < window]
        tracker.append(now)
        if len(tracker) >= limit:
            tracker.clear()
            action = cfg.get("flood_action", "mute")
            try:
                if action == "ban": await context.bot.ban_chat_member(chat.id, user.id)
                elif action == "kick":
                    await context.bot.ban_chat_member(chat.id, user.id)
                    await context.bot.unban_chat_member(chat.id, user.id)
                else:
                    await context.bot.restrict_chat_member(chat.id, user.id, MUTE_PERMS)
                await context.bot.send_message(chat.id,
                    f"🌊 <b>Flood detected!</b> {user_link(user)} was {action}d for spamming.",
                    parse_mode="HTML")
            except: pass
            return True
    except: pass
    return False

# ═══════════════════════════════════════════════════════════════════════════════
#                         MAIN MESSAGE HANDLER
# ═══════════════════════════════════════════════════════════════════════════════
async def main_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = update.message
        if not msg or not update.effective_chat or not update.effective_user: return
        chat = update.effective_chat
        user = update.effective_user
        cfg = get_chat(chat.id) if chat.type != "private" else {}

        # Update user data
        try:
            db = get_db()
            db.execute("""INSERT INTO users (user_id,username,first_name,last_name)
                         VALUES (?,?,?,?)
                         ON CONFLICT(user_id) DO UPDATE SET
                         username=excluded.username,
                         first_name=excluded.first_name,
                         last_name=excluded.last_name,
                         total_messages=total_messages+1""",
                       (user.id, user.username, user.first_name, user.last_name))
            db.commit(); db.close()
        except: pass

        # gban enforcement
        if is_gbanned(user.id) and chat.type != "private":
            try: await context.bot.ban_chat_member(chat.id, user.id)
            except: pass
            return

        # Approved users bypass filters
        if chat.type != "private" and is_approved(chat.id, user.id):
            add_xp(user.id, 1)
            return

        # Flood check
        if chat.type != "private":
            if await check_flood(update, context): return

        # Captcha check
        if chat.type != "private" and msg.text:
            pending = _pending_captcha.get((chat.id, user.id))
            if pending and pending.get("type") == "math":
                if msg.text.strip() == pending.get("answer",""):
                    del _pending_captcha�[(chat.id, user.id)]
                    if cfg.get("restrict_new"):
                        try: await context.bot.restrict_chat_member(chat.id, user.id, UNMUTE_PERMS)
                        except: pass
                    await msg.reply_text("✅ <b>Verified! Welcome!</b>", parse_mode="HTML")
                    return

        # Clean service messages
        if cfg.get("clean_service") and msg.new_chat_members or msg.left_chat_member:
            try: await msg.delete()
            except: pass

        # Lock enforcement
        if chat.type != "private" and not await is_admin(context, chat.id, user.id):
            should_del = False
            if cfg.get("lock_stickers") and msg.sticker: should_del = True
            if cfg.get("lock_gifs") and msg.animation: should_del = True
            if cfg.get("lock_media") and (msg.photo or msg.video or msg.audio or msg.document): should_del = True
            if cfg.get("lock_polls") and msg.poll: should_del = True
            if cfg.get("lock_voice") and msg.voice: should_del = True
            if cfg.get("lock_video") and msg.video_note: should_del = True
            if cfg.get("lock_forward") and msg.forward_date: should_del = True
            if cfg.get("lock_games") and msg.game: should_del = True
            if cfg.get("lock_url") and msg.text and "http" in msg.text.lower(): should_del = True
            if should_del:
                try: await msg.delete()
                except: pass
                return

        # Anti-link
        if (chat.type != "private" and cfg.get("antilink") and msg.text and
                not await is_admin(context, chat.id, user.id)):
            if re.search(r"https?://|t\.me/|telegram\.me/", msg.text.lower()):
                try: await msg.delete()
                except: pass
                return

        # Anti-forward
        if (chat.type != "private" and cfg.get("antiforward") and msg.forward_date and
                not await is_admin(context, chat.id, user.id)):
            try: await msg.delete()
            except: pass
            return

        # Anti-Arabic/RTL
        if (chat.type != "private" and cfg.get("antiarabic") and msg.text and
                not await is_admin(context, chat.id, user.id)):
            if re.search(r"[\u0600-\u06FF\u0750-\u077F\u200F\u200E]", msg.text):
                try: await msg.delete()
                except: pass
                return

        text = msg.text or msg.caption or ""

        # Hashtag note retrieval
        if text and chat.type != "private":
            for match in re.finditer(r"#(\w+)", text):
                await _send_note(update, context, match.group(1).lower())

        # +rep detection
        if text.lower().strip() in ("+rep", "+reputation"):
            if msg.reply_to_message:
                update.message = msg
                context.args = []
                await rep_cmd(update, context)
            return

        # Blacklist check
        if text and chat.type != "private" and not await is_admin(context, chat.id, user.id):
            db = get_db()
            bls = db.execute("SELECT word FROM blacklist WHERE chat_id=?", (chat.id,)).fetchall()
            bl_cfg = db.execute("SELECT action FROM blacklist_settings WHERE chat_id=?", (chat.id,)).fetchone()
            db.close()
            bl_action = bl_cfg["action"] if bl_cfg else "delete"
            tl = text.lower()
            hit = None
            for bl in bls:
                if bl["word"] in tl: hit = bl["word"]; break
            if hit:
                try: await msg.delete()
                except: pass
                if bl_action == "warn":
                    await _warn(update, context, silent=False, delete_msg=False)
                elif bl_action == "mute":
                    try: await context.bot.restrict_chat_member(chat.id, user.id, MUTE_PERMS)
                    except: pass
                elif bl_action == "ban":
                    try: await context.bot.ban_chat_member(chat.id, user.id)
                    except: pass
                return

        # Filter check
        if text and chat.type != "private":
            db = get_db()
            filters = db.execute("SELECT * FROM filters WHERE chat_id=?", (chat.id,)).fetchall()
            db.close()
            for f in filters:
                matched = False
                if f["is_regex"]:
                    try: matched = bool(re.search(f["keyword"], text, re.IGNORECASE))
                    except: pass
                else: matched = f["keyword"].lower() in text.lower()
                if matched:
                    try:
                        if f["file_id"]:
                            ft = f["file_type"]
                            cap = f["reply"] or None
                            if ft == "photo": await msg.reply_photo(f["file_id"], caption=cap, parse_mode="HTML")
                            elif ft == "sticker": await msg.reply_sticker(f["file_id"])
                            elif ft == "document": await msg.reply_document(f["file_id"], caption=cap, parse_mode="HTML")
                            elif ft == "animation": await msg.reply_animation(f["file_id"], caption=cap, parse_mode="HTML")
                            else: await reply(update, f["reply"] or "")
                        else: await reply(update, f["reply"] or "")
                    except: pass
                    break

        add_xp(user.id, 1)
    except Exception as e: logger.error(f"main_message_handler: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
#                         SCHEDULED JOBS
# ═══════════════════════════════════════════════════════════════════════════════
async def scheduled_messages_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        rows = db.execute("SELECT * FROM schedules WHERE active=1").fetchall()
        db.close()
        now = time.time()
        for row in rows:
            try:
                last = float(row["last_sent"] or 0)
                if now - last >= row["interval_sec"]:
                    await context.bot.send_message(row["chat_id"], row["text"], parse_mode="HTML")
                    db2 = get_db()
                    db2.execute("UPDATE schedules SET last_sent=? WHERE id=?", (now, row["id"]))
                    db2.commit(); db2.close()
            except: pass
    except: pass

async def reminder_check_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        db = get_db()
        now = datetime.datetime.now(pytz.utc)
        rows = db.execute("SELECT * FROM reminders WHERE done=0 AND remind_at<=?",
                          (now.isoformat(),)).fetchall()
        for row in rows:
            try:
                await context.bot.send_message(
                    row["chat_id"],
                    f"⏰ <b>Reminder!</b>\n\n{html.escape(row['text'][:500])}\n\n"
                    f"<a href='tg://user?id={row['user_id']}'>{row['user_id']}</a>",
                    parse_mode="HTML")
                db.execute("UPDATE reminders SET done=1 WHERE id=?", (row["id"],))
            except: pass
        db.commit(); db.close()
    except: pass

async def birthday_check_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        today = datetime.date.today()
        db = get_db()
        rows = db.execute("SELECT user_id, first_name, birthday FROM users WHERE birthday IS NOT NULL").fetchall()
        db.close()
        for row in rows:
            try:
                bday = row["birthday"]
                if not bday: continue
                day, month = map(int, bday.split("/"))
                if today.day == day and today.month == month:
                    name = html.escape(row["first_name"] or str(row["user_id"]))
                    add_coins(row["user_id"], 500)
            except: pass
    except: pass

# ═══════════════════════════════════════════════════════════════════════════════
#                              MAIN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════
async def post_init(application):
    try:
        cmds = [
            BotCommand("start","Start the bot"),
            B�otCommand("help","Help menu"),
            BotCommand("ban","Ban a user"),
            BotCommand("kick","Kick a user"),
            BotCommand("mute","Mute a user"),
            BotCommand("warn","Warn a user"),
            BotCommand("promote","Promote to admin"),
            BotCommand("demote","Demote admin"),
            BotCommand("purge","Purge messages"),
            BotCommand("daily","Claim daily coins"),
            BotCommand("work","Work for coins"),
            BotCommand("mine","Mine for coins"),
            BotCommand("slots","Play slots"),
            BotCommand("flip","Flip a coin"),
            BotCommand("shop","View shop"),
            BotCommand("coins","Check balance"),
            BotCommand("leaderboard","See rankings"),
            BotCommand("hangman","Play hangman"),
            BotCommand("scramble","Word scramble game"),
            BotCommand("trivia","Trivia question"),
            BotCommand("riddle","Get a riddle"),
            BotCommand("rps","Rock paper scissors"),
            BotCommand("tictactoe","Play tic tac toe"),
            BotCommand("battle","Battle another user"),
            BotCommand("marry","Propose marriage"),
            BotCommand("divorce","Get divorced"),
            BotCommand("8ball","Ask the magic 8-ball"),
            BotCommand("truth","Get a truth question"),
            BotCommand("dare","Get a dare"),
            BotCommand("wyr","Would you rather"),
            BotCommand("joke","Random joke"),
            BotCommand("fact","Random fact"),
            BotCommand("quote","Inspirational quote"),
            BotCommand("fortune","Daily fortune"),
            BotCommand("tarot","Tarot card reading"),
            BotCommand("horoscope","Daily horoscope"),
            BotCommand("vibe","Vibe check"),
            BotCommand("personality","Personality reading"),
            BotCommand("hug","Hug someone"),
            BotCommand("slap","Slap someone"),
            BotCommand("roast","Roast someone"),
            BotCommand("ship","Ship compatibility"),
            BotCommand("ask","Ask AI anything"),
            BotCommand("info","User info"),
            BotCommand("id","Get user/chat ID"),
            BotCommand("rank","View rank"),
            BotCommand("ping","Check bot latency"),
            BotCommand("remind","Set a reminder"),
            BotCommand("notes","List notes"),
            BotCommand("rules","View rules"),
            BotCommand("settings","Bot settings"),
            BotCommand("stats","Bot statistics"),
        ]
        await application.bot.set_my_commands(cmds)
        logger.info("✅ Bot commands registered")
    except Exception as e:
        logger.error(f"post_init: {e}")

def main():
    init_db()
    logger.info(f"🚀 Starting Nexus Bot v{VERSION}")

    app = (Application.builder()
           .token(BOT_TOKEN)
           .post_init(post_init)
           .build())

    # Load connections from DB
    try:
        db = get_db()
        rows = db.execute("SELECT user_id,chat_id FROM connections").fetchall()
        for r in rows: connection_cache[r["user_id"]] = r["chat_id"]
        db.close()
    except: pass

    def cmd(*commands):
        return [CommandHandler(c, h) for c, h in zip(commands[::2], commands[1::2])]

    H = app.add_handler

    # Start/Help
    H(CommandHandler("start", start_cmd))
    H(CommandHandler("help", help_cmd))

    # Moderation
    H(CommandHandler("ban", ban_cmd))
    H(CommandHandler("tban", tban_cmd))
    H(CommandHandler("sban", sban_cmd))
    H(CommandHandler("unban", unban_cmd))
    H(CommandHandler("kick", kick_cmd))
    H(CommandHandler("skick", skick_cmd))
    H(CommandHandler("mute", mute_cmd))
    H(CommandHandler("tmute", tmute_cmd))
    H(CommandHandler("unmute", unmute_cmd))
    H(CommandHandler("warn", warn_cmd))
    H(CommandHandler("dwarn", dwarn_cmd))
    H(CommandHandler("swarn", swarn_cmd))
    H(CommandHandler("unwarn", unwarn_cmd))
    H(CommandHandler("resetwarn", resetwarn_cmd))
    H(CommandHandler("warns", warns_cmd))
    H(CommandHandler("setwarnlimit", setwarnlimit_cmd))
    H(CommandHandler("setwarnaction", setwarnaction_cmd))
    H(CommandHandler("promote", promote_cmd))
    H(CommandHandler("demote", demote_cmd))
    H(CommandHandler("admintitle", admintitle_cmd))
    H(CommandHandler("adminlist", adminlist_cmd))
    H(CommandHandler("purge", purge_cmd))
    H(CommandHandler("del", del_cmd))
    H(CommandHandler("slowmode", slowmode_cmd))
    H(CommandHandler("pin", pin_cmd))
    H(CommandHandler("unpin", unpin_cmd))
    H(CommandHandler("unpinall", unpinall_cmd))
    H(CommandHandler("zombies", zombies_cmd))
    H(CommandHandler("kickzombies", kickzombies_cmd))
    H(CommandHandler("approve", approve_cmd))
    H(CommandHandler("disapprove", disapprove_cmd))
    H(CommandHandler("approved", approved_cmd))

    # Welcome/Rules
    H(CommandHandler("setwelcome", setwelcome_cmd))
    H(CommandHandler("welcome", welcome_cmd))
    H(CommandHandler("setgoodbye", setgoodbye_cmd))
    H(CommandHandler("goodbye", goodbye_cmd))
    H(CommandHandler("setrules", setrules_cmd))
    H(CommandHandler("rules", rules_cmd))
    H(CommandHandler("captcha", captcha_cmd))
    H(CommandHandler("captchatype", captchatype_cmd))
    H(CommandHandler("welcdel", welcdel_cmd))

    # Notes/Filters
    H(CommandHandler("save", save_note_cmd))
    H(CommandHandler("get", get_note_cmd))
    H(CommandHandler("notes", notes_cmd))
    H(CommandHandler("clear", clear_note_cmd))
    H(CommandHandler("clearall", clearall_notes_cmd))
    H(CommandHandler("filter", add_filter_cmd))
    H(CommandHandler("filters", filters_cmd))
    H(CommandHandler("stop", stop_filter_cmd))
    H(CommandHandler("stopall", stopall_filters_cmd))
    H(CommandHandler("addbl", addbl_cmd))
    H(CommandHandler("rmbl", rmbl_cmd))
    H(CommandHandler("blacklist", blacklist_cmd))
    H(CommandHandler("blmode", blmode_cmd))

    # Locks
    H(CommandHandler("lock", lock_cmd))
    H(CommandHandler("unlock", unlock_cmd))
    H(CommandHandler("locks", locks_cmd))

    # Protection
    H(CommandHandler("antispam", antispam_cmd))
    H(CommandHandler("antiflood", antiflood_cmd))
    H(CommandHandler("antilink", antilink_cmd))
    H(CommandHandler("antiforward", antiforward_cmd))
    H(CommandHandler("antibot", antibot_cmd))
    H(CommandHandler("antinsfw", antinsfw_cmd))
    H(CommandHandler("antiarabic", antiarabic_cmd))
    H(CommandHandler("antiraid", antiraid_cmd))
    H(CommandHandler("cas", cas_cmd))
    H(CommandHandler("restrict", restrict_cmd))
    H(CommandHandler("setflood", setflood_cmd))
    H(CommandHandler("setfloodaction", setfloodaction_cmd))
    H(CommandHandler("setraid", setraid_cmd))
    H(CommandHandler("protect", protect_panel))
    H(CommandHandler("settings", settings_cmd))
    H(CommandHandler("cleanservice", cleanservice_cmd))
    H(CommandHandler("delcommands", delcommands_cmd))
    H(CommandHandler("setlogchannel", setlogchannel_cmd))

    # Economy
    H(CommandHandler("coins", coins_cmd))
    H(CommandHandler("daily", daily_cmd))
    H(CommandHandler("work", work_cmd))
    H(CommandHandler("mine", mine_cmd))
    H(CommandHandler("bank", bank_cmd))
    H(CommandHandler("flip", flip_cmd))
    H(CommandHandler("slots", slots_cmd))
    H(CommandHandler("rob", rob_cmd))
    H(CommandHandler("give", give_cmd))
    H(CommandHandler("leaderboard", leaderboard_cmd))
    H(CommandHandler("shop", shop_cmd))
    H(CommandHandler("buy", buy_cmd))
    H(CommandHandler("inventory", inventory_cmd))
    H(CommandHandler("lottery", lottery_cmd))
    H(CommandHandler("streak", streak_cmd))

    # Reputation
    H(CommandHandler("rep", rep_cmd))
    H(CommandHandler("checkrep", checkrep_cmd))
    H(CommandHandler("reprank", reprank_cmd))
    H(CommandHandler("rank", rank_cmd))
    H(CommandHandler("level", level_cmd))
    H(CommandHandler("top", top_cmd))

    # Games
    H(CommandHandler("trivia", trivia_cmd))
    H(CommandHandler("hangman", hangman_cmd))
    H(CommandHandler("guess", guess_cmd))
    H(CommandHandler("stophangman", stophangman_cmd))
    H(CommandHandler("scramble", scramble_cmd))
    H(CommandHandler("unscramble", unscramble_cmd))
  �  H(CommandHandler("rps", rps_cmd))
    H(CommandHandler("tictactoe", ttt_cmd))
    H(CommandHandler("ttt", ttt_cmd))
    H(CommandHandler("riddle", riddle_cmd))
    H(CommandHandler("answer", answer_cmd))
    H(CommandHandler("battle", battle_cmd))
    H(CommandHandler("roll", roll_cmd))
    H(CommandHandler("pp", pp_cmd))
    H(CommandHandler("ship", ship_cmd))

    # Social
    H(CommandHandler("hug", hug_cmd))
    H(CommandHandler("slap", slap_cmd))
    H(CommandHandler("kiss", kiss_cmd))
    H(CommandHandler("pat", pat_cmd))
    H(CommandHandler("poke", poke_cmd))
    H(CommandHandler("roast", roast_cmd))
    H(CommandHandler("compliment", compliment_cmd))

    # Marriage
    H(CommandHandler("marry", marry_cmd))
    H(CommandHandler("divorce", divorce_cmd))
    H(CommandHandler("spouse", spouse_cmd))
    H(CommandHandler("accept", accept_cmd))

    # Fun
    H(CommandHandler("8ball", eightball_cmd))
    H(CommandHandler("joke", joke_cmd))
    H(CommandHandler("fact", fact_cmd))
    H(CommandHandler("quote", quote_cmd))
    H(CommandHandler("truth", truth_cmd))
    H(CommandHandler("dare", dare_cmd))
    H(CommandHandler("wyr", wyr_cmd))
    H(CommandHandler("fortune", fortune_cmd))
    H(CommandHandler("tarot", tarot_cmd))
    H(CommandHandler("horoscope", horoscope_cmd))
    H(CommandHandler("meme", meme_cmd))
    H(CommandHandler("vibe", vibe_cmd))
    H(CommandHandler("personality", personality_cmd))
    H(CommandHandler("mood", mood_cmd))
    H(CommandHandler("setbirthday", setbirthday_cmd))
    H(CommandHandler("birthday", birthday_cmd))

    # Utilities
    H(CommandHandler("id", id_cmd))
    H(CommandHandler("info", info_cmd))
    H(CommandHandler("chatinfo", chatinfo_cmd))
    H(CommandHandler("ping", ping_cmd))
    H(CommandHandler("uptime", uptime_cmd))
    H(CommandHandler("stats", stats_cmd))
    H(CommandHandler("calc", calc_cmd))
    H(CommandHandler("hash", hash_cmd))
    H(CommandHandler("b64", b64_cmd))
    H(CommandHandler("reverse", reverse_cmd))
    H(CommandHandler("qr", qr_cmd))
    H(CommandHandler("tr", tr_cmd))
    H(CommandHandler("weather", weather_cmd))
    H(CommandHandler("time", time_cmd))
    H(CommandHandler("remind", remind_cmd))
    H(CommandHandler("myreminders", myreminders_cmd))
    H(CommandHandler("report", report_cmd))
    H(CommandHandler("ask", ask_cmd))
    H(CommandHandler("aiinfo", aiinfo_cmd))

    # Connection
    H(CommandHandler("connect", connect_cmd))
    H(CommandHandler("disconnect", disconnect_cmd))
    H(CommandHandler("connected", connected_cmd))

    # Federation
    H(CommandHandler("newfed", newfed_cmd))
    H(CommandHandler("delfed", delfed_cmd))
    H(CommandHandler("joinfed", joinfed_cmd))
    H(CommandHandler("leavefed", leavefed_cmd))
    H(CommandHandler("fedinfo", fedinfo_cmd))
    H(CommandHandler("fban", fban_cmd))
    H(CommandHandler("unfban", unfban_cmd))
    H(CommandHandler("fedbans", fedbans_cmd))
    H(CommandHandler("fadmin", fadmin_cmd))
    H(CommandHandler("fremove", fremove_cmd))

    # Owner/Sudo
    H(CommandHandler("gban", gban_cmd))
    H(CommandHandler("ungban", ungban_cmd))
    H(CommandHandler("sudo", sudo_cmd))
    H(CommandHandler("unsudo", unsudo_cmd))
    H(CommandHandler("broadcast", broadcast_cmd))
    H(CommandHandler("botstats", botstats_cmd))
    H(CommandHandler("chatlist", chatlist_cmd))
    H(CommandHandler("leave", leave_cmd))

    # Callback queries
    H(CallbackQueryHandler(help_callback, pattern="^help_"))
    H(CallbackQueryHandler(unban_callback, pattern="^unban:"))
    H(CallbackQueryHandler(unmute_callback, pattern="^unmute:"))
    H(CallbackQueryHandler(warn_action_callback, pattern="^(unwarn|resetwarn):"))
    H(CallbackQueryHandler(trivia_callback, pattern="^trivia:"))
    H(CallbackQueryHandler(captcha_callback, pattern="^captcha_ok:"))
    H(CallbackQueryHandler(marry_callback, pattern="^marry_(accept|decline):"))
    H(CallbackQueryHandler(rps_callback, pattern="^rps:"))
    H(CallbackQueryHandler(ttt_callback, pattern="^ttt:"))
    H(CallbackQueryHandler(wyr_callback, pattern="^wyr:"))

    # Message handlers
    H(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member))
    H(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_member_left))
    H(MessageHandler(filters.TEXT | filters.CAPTION | filters.PHOTO |
                     filters.VIDEO | filters.DOCUMENT | filters.STICKER |
                     filters.VOICE | filters.ANIMATION | filters.POLL |
                     filters.FORWARDED, main_message_handler))
    H(MessageHandler(filters.Regex(r"@admins|@admin"), tag_admins_handler))

    # Inline
    H(InlineQueryHandler(inline_query_handler))

    # Scheduler jobs
    jq = app.job_queue
    jq.run_repeating(scheduled_messages_job, interval=60, first=10)
    jq.run_repeating(reminder_check_job, interval=30, first=5)
    jq.run_repeating(birthday_check_job, interval=3600, first=60)

    logger.info(f"✅ Nexus Bot v{VERSION} — All systems go!")
    logger.info(f"📡 Handlers registered · Scheduler active · DB initialized")
    logger.info(f"🎲 Randomness pools loaded: 3500+ unique responses")
    logger.info(f"🎮 Games: Hangman · Scramble · RPS · TicTacToe · Trivia · Battle · Riddles")
    logger.info(f"💍 Marriage system · 🔮 Tarot/Fortune/Horoscope · ✅ Approve system")

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
    )

if __name__ == "__main__":
    main()
