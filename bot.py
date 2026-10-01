import asyncio
import html
import logging
import os
import re
import sqlite3
import time

from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv


# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(
    BASE_DIR / ".env",
    override=True
)


BOT_TOKEN = os.getenv(
    "BOT_TOKEN",
    ""
).strip()


if not BOT_TOKEN:

    raise RuntimeError(
        "BOT_TOKEN topilmadi. "
        ".env faylga BOT_TOKEN=... yozing."
    )


ADMIN_ID = int(
    os.getenv(
        "ADMIN_ID",
        "7582210709"
    )
)


ADMIN_USERNAME = os.getenv(
    "ADMIN_USERNAME",
    "yoldoshev_org"
).strip().lstrip("@")


BOT_USERNAME = os.getenv(
    "BOT_USERNAME",
    "mrxstarss_bot"
).strip().lstrip("@")


DB_FILE = (
    BASE_DIR
    / "mrx_bot.db"
)


# ============================================================
# STARS
# ============================================================

STARS_REF_REWARD = 3


STARS_WITHDRAW_OPTIONS = (
    15,
    25,
    50,
    100,
    150,
    200,
    300,
)


# ============================================================
# ANTI SPAM
# ============================================================

RATE_WINDOW = 10

MAX_REQUESTS = 18


REQUESTS = defaultdict(
    deque
)


# ============================================================
# 4 TA MAJBURIY KANAL
# ============================================================

CHANNELS = [

    {
        "chat_id": "@MRX_starss",

        "title": "⭐ MRX STARS",

        "url": "https://t.me/MRX_starss",
    },

    {
        "chat_id": "@MRX_security",

        "title": "🛡 MRX SECURITY",

        "url": "https://t.me/MRX_security",
    },

    {
        "chat_id": "@mrx_otzivv",

        "title": "💬 MRX OTZIV",

        "url": "https://t.me/mrx_otzivv",
    },

    {
        "chat_id": "@mrxstarss",

        "title": "⭐ MRX STARSS",

        "url": "https://t.me/mrxstarss",
    },

]


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(

    level=logging.INFO,

    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)


logger = logging.getLogger(
    "MRX_STARS_PREMIUM"
)


# ============================================================
# BOT
# ============================================================

bot = Bot(
    BOT_TOKEN
)


dp = Dispatcher()


router = Router()


dp.include_router(
    router
)


# ============================================================
# DATABASE
# ============================================================

db = sqlite3.connect(

    DB_FILE,

    check_same_thread=False
)


db.row_factory = sqlite3.Row


cur = db.cursor()


cur.execute(
    "PRAGMA journal_mode=WAL"
)


# ============================================================
# TIME
# ============================================================

def now_string():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# ============================================================
# DATABASE INIT
# ============================================================

def init_db():

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            user_id INTEGER PRIMARY KEY,

            username TEXT,

            first_name TEXT,

            phone TEXT,

            stars_balance INTEGER
                NOT NULL DEFAULT 0,

            stars_referrals INTEGER
                NOT NULL DEFAULT 0,

            withdrawn_stars INTEGER
                NOT NULL DEFAULT 0,

            referrer_id INTEGER,

            referral_type TEXT,

            referral_rewarded INTEGER
                NOT NULL DEFAULT 0,

            banned INTEGER
                NOT NULL DEFAULT 0,

            created_at TEXT,

            last_seen TEXT
        )
        """
    )


    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS referral_log (

            id INTEGER
                PRIMARY KEY AUTOINCREMENT,

            referrer_id INTEGER
                NOT NULL,

            referred_id INTEGER
                NOT NULL UNIQUE,

            referral_type TEXT,

            reward INTEGER
                NOT NULL,

            created_at TEXT
                NOT NULL
        )
        """
    )


    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stars_withdrawals (

            id INTEGER
                PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER
                NOT NULL,

            amount INTEGER
                NOT NULL,

            status TEXT
                NOT NULL DEFAULT 'pending',

            created_at TEXT
                NOT NULL
        )
        """
    )


    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (

            id INTEGER
                PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER
                NOT NULL,

            amount INTEGER
                NOT NULL,

            type TEXT
                NOT NULL,

            description TEXT,

            created_at TEXT
                NOT NULL
        )
        """
    )


    db.commit()


init_db()


# ============================================================
# DATABASE MIGRATION
# Eski mrx_bot.db bilan ishlashi uchun
# ============================================================

def add_column_if_missing(
    table,
    column,
    definition
):

    cur.execute(
        f"PRAGMA table_info({table})"
    )


    columns = [

        row["name"]

        for row in cur.fetchall()

    ]


    if column not in columns:

        cur.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN {column} {definition}
            """
        )

        db.commit()


add_column_if_missing(
    "users",
    "phone",
    "TEXT"
)


add_column_if_missing(
    "users",
    "stars_balance",
    "INTEGER DEFAULT 0"
)


add_column_if_missing(
    "users",
    "stars_referrals",
    "INTEGER DEFAULT 0"
)


add_column_if_missing(
    "users",
    "withdrawn_stars",
    "INTEGER DEFAULT 0"
)


add_column_if_missing(
    "users",
    "referrer_id",
    "INTEGER"
)


add_column_if_missing(
    "users",
    "referral_type",
    "TEXT"
)


add_column_if_missing(
    "users",
    "referral_rewarded",
    "INTEGER DEFAULT 0"
)


add_column_if_missing(
    "users",
    "banned",
    "INTEGER DEFAULT 0"
)


add_column_if_missing(
    "users",
    "created_at",
    "TEXT"
)


add_column_if_missing(
    "users",
    "last_seen",
    "TEXT"
)


# ============================================================
# USER HELPERS
# ============================================================

def get_user(
    user_id
):

    cur.execute(
        """
        SELECT *

        FROM users

        WHERE user_id=?
        """,
        (
            user_id,
        )
    )


    return cur.fetchone()


def update_user_info(
    tg_user
):

    cur.execute(
        """
        UPDATE users

        SET
            username=?,
            first_name=?,
            last_seen=?

        WHERE user_id=?
        """,
        (
            tg_user.username,

            tg_user.first_name,

            now_string(),

            tg_user.id,
        )
    )


    db.commit()


# ============================================================
# CREATE / UPDATE USER
# ============================================================

def create_or_update_user(
    tg_user,
    referrer_id=None
):

    user = get_user(
        tg_user.id
    )


    if user:

        update_user_info(
            tg_user
        )


        if (
            referrer_id
            and
            referrer_id
            != tg_user.id
            and
            not user["phone"]
            and
            not user["referrer_id"]
            and
            get_user(referrer_id)
        ):

            cur.execute(
                """
                UPDATE users

                SET
                    referrer_id=?,
                    referral_type='stars'

                WHERE user_id=?
                """,
                (
                    referrer_id,

                    tg_user.id,
                )
            )


            db.commit()


        return False


    if referrer_id:

        if (
            referrer_id
            == tg_user.id
            or
            not get_user(
                referrer_id
            )
        ):

            referrer_id = None


    cur.execute(
        """
        INSERT INTO users (

            user_id,

            username,

            first_name,

            referrer_id,

            referral_type,

            created_at,

            last_seen

        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?
        )
        """,
        (
            tg_user.id,

            tg_user.username,

            tg_user.first_name,

            referrer_id,

            (
                "stars"
                if referrer_id
                else None
            ),

            now_string(),

            now_string(),
        )
    )


    db.commit()


    return True


# ============================================================
# TRANSACTION
# ============================================================

def add_transaction(
    user_id,
    amount,
    kind,
    description
):

    cur.execute(
        """
        INSERT INTO transactions (

            user_id,

            amount,

            type,

            description,

            created_at

        )

        VALUES (
            ?, ?, ?, ?, ?
        )
        """,
        (
            user_id,

            amount,

            kind,

            description,

            now_string(),
        )
    )


    db.commit()


# ============================================================
# CHANGE STARS
# ============================================================

def change_stars(
    user_id,
    amount,
    description="Stars o'zgardi"
):

    if amount < 0:

        cur.execute(
            """
            UPDATE users

            SET
                stars_balance =
                stars_balance + ?

            WHERE user_id=?

            AND stars_balance >= ?
            """,
            (
                amount,

                user_id,

                abs(amount),
            )
        )

    else:

        cur.execute(
            """
            UPDATE users

            SET
                stars_balance =
                stars_balance + ?

            WHERE user_id=?
            """,
            (
                amount,

                user_id,
            )
        )


    if cur.rowcount != 1:

        db.rollback()

        return False


    db.commit()


    add_transaction(

        user_id,

        amount,

        "stars",

        description
    )


    return True


# ============================================================
# PHONE HELPERS
# ============================================================

def phone_used_by_other(
    phone,
    user_id
):

    cur.execute(
        """
        SELECT user_id

        FROM users

        WHERE phone=?

        AND user_id<>?

        LIMIT 1
        """,
        (
            phone,

            user_id,
        )
    )


    return (
        cur.fetchone()
        is not None
    )


def save_phone(
    user_id,
    phone
):

    cur.execute(
        """
        UPDATE users

        SET phone=?

        WHERE user_id=?
        """,
        (
            phone,

            user_id,
        )
    )


    db.commit()


def is_admin(
    user_id
):

    return (
        user_id
        == ADMIN_ID
    )


# ============================================================
# RATE LIMIT
# ============================================================

def rate_limit_ok(
    user_id
):

    if is_admin(
        user_id
    ):

        return True


    current = time.time()


    queue = REQUESTS[
        user_id
    ]


    while (
        queue
        and
        current - queue[0]
        > RATE_WINDOW
    ):

        queue.popleft()


    if (
        len(queue)
        >= MAX_REQUESTS
    ):

        return False


    queue.append(
        current
    )


    return True


# ============================================================
# PHONE VALIDATION
# ============================================================

def normalize_phone(
    phone
):

    phone = re.sub(
        r"[^0-9+]",
        "",
        phone or ""
    )


    if not phone.startswith(
        "+"
    ):

        phone = (
            "+"
            + phone
        )


    return phone


def valid_phone(
    phone
):

    # O'zbekiston
    if re.fullmatch(
        r"\+998\d{9}",
        phone
    ):

        return True


    # Qirg'iziston
    if re.fullmatch(
        r"\+996\d{9}",
        phone
    ):

        return True


    # Rossiya / Qozog'iston
    if re.fullmatch(
        r"\+7\d{10}",
        phone
    ):

        return True


    return False


# ============================================================
# MAIN KEYBOARD
# ============================================================

def main_keyboard():

    return ReplyKeyboardMarkup(

        keyboard=[

            [
                KeyboardButton(
                    text="⭐ Stars ishlash"
                ),

                KeyboardButton(
                    text="⭐ Stars yechish"
                ),
            ],

            [
                KeyboardButton(
                    text="👤 Hisobim"
                ),

                KeyboardButton(
                    text="🌐 Raqam sotib olish"
                ),
            ],

            [
                KeyboardButton(
                    text="💎 NFT sotib olish"
                ),

                KeyboardButton(
                    text="🤝 Homiy bo'lish"
                ),
            ],

            [
                KeyboardButton(
                    text="🆘 Yordam"
                ),

                KeyboardButton(
                    text="📖 Qo'llanma"
                ),
            ],

        ],

        resize_keyboard=True,
    )


# ============================================================
# ADMIN LINK
# ============================================================

def admin_link_keyboard(
    text="📩 Admin bilan bog'lanish"
):

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [
                InlineKeyboardButton(

                    text=text,

                    url=(
                        f"https://t.me/"
                        f"{ADMIN_USERNAME}"
                    ),
                )
            ]

        ]
    )


# ============================================================
# MAJBURIY OBUNA KEYBOARD
# ============================================================

def subscription_keyboard():

    rows = []


    for channel in CHANNELS:

        rows.append(
            [
                InlineKeyboardButton(

                    text=channel[
                        "title"
                    ],

                    url=channel[
                        "url"
                    ],
                )
            ]
        )


    rows.append(
        [
            InlineKeyboardButton(

                text=(
                    "✅ OBUNANI TEKSHIRISH"
                ),

                callback_data="check_sub",
            )
        ]
    )


    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# ============================================================
# PHONE KEYBOARD
# ============================================================

def phone_keyboard():

    return ReplyKeyboardMarkup(

        keyboard=[

            [
                KeyboardButton(

                    text=(
                        "📱 Raqamimni yuborish"
                    ),

                    request_contact=True,
                )
            ]

        ],

        resize_keyboard=True,

        one_time_keyboard=True,
    )


# ============================================================
# WITHDRAW KEYBOARD
# ============================================================

def withdraw_keyboard():

    rows = []

    row = []


    for amount in (
        STARS_WITHDRAW_OPTIONS
    ):

        row.append(
            InlineKeyboardButton(

                text=f"⭐ {amount}",

                callback_data=(
                    f"wd:{amount}"
                ),
            )
        )


        if len(row) == 2:

            rows.append(
                row
            )

            row = []


    if row:

        rows.append(
            row
        )


    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# ============================================================
# ADMIN PANEL KEYBOARD
# ============================================================

def admin_panel_keyboard():

    return InlineKeyboardMarkup(

        inline_keyboard=[

            [
                InlineKeyboardButton(

                    text="📊 Statistika",

                    callback_data=(
                        "adm:stats"
                    ),
                ),

                InlineKeyboardButton(

                    text="⏳ Pending",

                    callback_data=(
                        "adm:pending"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(

                    text="📚 Buyruqlar",

                    callback_data=(
                        "adm:help"
                    ),
                ),
            ],

        ]
    )


# ============================================================
# MAJBURIY OBUNA TEKSHIRISH
# ============================================================

async def check_subscription(
    user_id
):

    missing = []

    errors = []


    for channel in CHANNELS:

        try:

            member = (
                await bot.get_chat_member(

                    chat_id=channel[
                        "chat_id"
                    ],

                    user_id=user_id,
                )
            )


            if member.status in (

                ChatMemberStatus.MEMBER,

                ChatMemberStatus.ADMINISTRATOR,

                ChatMemberStatus.CREATOR,

            ):

                continue


            # Restricted user kanal ichida
            # bo'lsa ham qabul qilamiz

            if (
                member.status
                == ChatMemberStatus.RESTRICTED
            ):

                if getattr(
                    member,
                    "is_member",
                    False
                ):

                    continue


            missing.append(
                channel
            )


        except Exception as error:

            logger.warning(

                "Subscription check failed "
                "for %s: %s",

                channel[
                    "chat_id"
                ],

                error
            )


            errors.append(
                channel
            )


    ok = (
        not missing
        and
        not errors
    )


    return (
        ok,
        missing,
        errors
    )


# ============================================================
# SEND SUBSCRIPTION
# ============================================================

async def send_subscription(
    message
):

    await message.answer(

        "🔐 <b>MAJBURIY OBUNA</b>\n\n"

        "Botdan foydalanish uchun "
        "quyidagi <b>4 ta kanalga</b> "
        "obuna bo'ling.\n\n"

        "Barcha kanallarga obuna "
        "bo'lgach:\n\n"

        "✅ <b>OBUNANI TEKSHIRISH</b>\n\n"

        "tugmasini bosing.",

        parse_mode="HTML",

        reply_markup=(
            subscription_keyboard()
        ),
    )


# ============================================================
# ASK PHONE
# ============================================================

async def ask_phone(
    message
):

    await message.answer(

        "📱 <b>TELEFON TASDIQLASH</b>\n\n"

        "✅ Obuna tasdiqlandi!\n\n"

        "Endi Telegram hisobingizga "
        "ulangan <b>o'z telefon "
        "raqamingizni</b> yuboring.\n\n"

        "Qabul qilinadi:\n\n"

        "🇺🇿 +998 — O'zbekiston\n"

        "🇰🇬 +996 — Qirg'iziston\n"

        "🇷🇺 +7 — Rossiya\n"

        "🇰🇿 +7 — Qozog'iston\n\n"

        "👇 Pastdagi tugmani bosing:",

        parse_mode="HTML",

        reply_markup=(
            phone_keyboard()
        ),
    )


# ============================================================
# ADMIN REGISTRATION NOTIFICATION
# ============================================================

async def notify_admin_registration(
    message,
    phone
):

    tg_user = (
        message.from_user
    )


    username = (

        f"@{html.escape(tg_user.username)}"

        if tg_user.username

        else "Yo'q"
    )


    user = get_user(
        tg_user.id
    )


    referrer_id = (

        user[
            "referrer_id"
        ]

        if user

        else None
    )


    text = (

        "🆕 <b>YANGI "
        "FOYDALANUVCHI!</b>\n\n"

        f"👤 Ism: "
        f"<b>{html.escape(tg_user.first_name or '')}</b>\n"

        f"🆔 ID: "
        f"<code>{tg_user.id}</code>\n"

        f"🔗 Username: "
        f"<b>{username}</b>\n"

        f"📱 Telefon: "
        f"<code>{html.escape(phone)}</code>\n"

        f"👥 Referrer ID: "
        f"<code>{referrer_id or 'yoq'}</code>\n"

        f"📅 Sana: "
        f"<b>{now_string()}</b>"
    )


    try:

        await bot.send_message(

            ADMIN_ID,

            text,

            parse_mode="HTML",
        )


    except Exception as error:

        logger.warning(

            "Admin registration "
            "notify failed: %s",

            error
        )


# ============================================================
# REFERRAL +2 STARS
# ============================================================

async def reward_referrer(
    referred_id
):

    user = get_user(
        referred_id
    )


    if not user:

        return


    if user[
        "referral_rewarded"
    ]:

        return


    if not user[
        "phone"
    ]:

        return


    referrer_id = (
        user[
            "referrer_id"
        ]
    )


    if not referrer_id:

        return


    if (
        referrer_id
        == referred_id
    ):

        return


    referrer = get_user(
        referrer_id
    )


    if not referrer:

        return


    if referrer[
        "banned"
    ]:

        return


    try:

        cur.execute(
            "BEGIN IMMEDIATE"
        )


        cur.execute(
            """
            INSERT INTO referral_log (

                referrer_id,

                referred_id,

                referral_type,

                reward,

                created_at

            )

            VALUES (
                ?, ?, 'stars', ?, ?
            )
            """,
            (
                referrer_id,

                referred_id,

                STARS_REF_REWARD,

                now_string(),
            )
        )


        cur.execute(
            """
            UPDATE users

            SET
                stars_balance =
                stars_balance + ?,

                stars_referrals =
                stars_referrals + 1

            WHERE user_id=?
            """,
            (
                STARS_REF_REWARD,

                referrer_id,
            )
        )


        cur.execute(
            """
            UPDATE users

            SET referral_rewarded=1

            WHERE user_id=?
            """,
            (
                referred_id,
            )
        )


        cur.execute(
            """
            INSERT INTO transactions (

                user_id,

                amount,

                type,

                description,

                created_at

            )

            VALUES (
                ?, ?, 'stars',
                'Referral bonusi', ?
            )
            """,
            (
                referrer_id,

                STARS_REF_REWARD,

                now_string(),
            )
        )


        db.commit()


    except sqlite3.IntegrityError:

        db.rollback()

        return


    except Exception:

        db.rollback()

        raise


    referrer = get_user(
        referrer_id
    )


    try:

        await bot.send_message(

            referrer_id,

            "🎉 <b>YANGI REFERRAL!</b>\n\n"

            f"⭐ Sizga: "
            f"<b>+{STARS_REF_REWARD} Stars</b>\n\n"

            f"👥 Jami referral: "
            f"<b>{referrer['stars_referrals']} ta</b>\n"

            f"⭐ Balans: "
            f"<b>{referrer['stars_balance']} Stars</b>",

            parse_mode="HTML",
        )


    except Exception:

        pass


# ============================================================
# SHOW MENU
# ============================================================

async def show_menu(
    message,
    user_id
):

    user = get_user(
        user_id
    )


    if not user:

        await message.answer(
            "❌ User topilmadi. "
            "/start ni qayta bosing."
        )

        return


    await message.answer(

        "💎 <b>MRX STARSS BOT</b>\n\n"

        "Xush kelibsiz! 🚀\n\n"

        f"⭐ Balans: "
        f"<b>{user['stars_balance']} Stars</b>\n"

        f"👥 Referallar: "
        f"<b>{user['stars_referrals']} ta</b>\n\n"

        "👇 Kerakli bo'limni tanlang:",

        parse_mode="HTML",

        reply_markup=(
            main_keyboard()
        ),
    )


# ============================================================
# REGISTER CHECK
# ============================================================

async def ensure_registered(
    message,
    check_sub=True
):

    if not rate_limit_ok(
        message.from_user.id
    ):

        await message.answer(

            "⚠️ Juda ko'p so'rov "
            "yubordingiz. Bir oz kuting."
        )

        return False


    user = get_user(
        message.from_user.id
    )


    if not user:

        await message.answer(
            "❌ Avval /start bosing."
        )

        return False


    if user[
        "banned"
    ]:

        await message.answer(
            "⛔ Siz botdan bloklangansiz."
        )

        return False


    if not user[
        "phone"
    ]:

        await message.answer(

            "📱 Avval /start orqali "
            "ro'yxatdan o'ting."
        )

        return False


    if check_sub:

        ok, missing, errors = (
            await check_subscription(
                message.from_user.id
            )
        )


        if not ok:

            if errors:

                names = "\n".join(

                    f"• {channel['title']}"

                    for channel in errors
                )


                await message.answer(

                    "⚠️ <b>OBUNANI "
                    "TEKSHIRIB BO'LMADI</b>\n\n"

                    "Bot quyidagi kanal(lar)ni "
                    "tekshira olmadi:\n\n"

                    f"{names}\n\n"

                    "❗ Botni shu kanal(lar)ga "
                    "<b>ADMIN</b> qilib qo'ying.",

                    parse_mode="HTML",
                )


            else:

                await send_subscription(
                    message
                )


            return False


    return True


# ============================================================
# START
# ============================================================

@router.message(
    CommandStart()
)
async def start_handler(
    message: Message
):

    referrer_id = None


    parts = (
        message.text
        or ""
    ).split(
        maxsplit=1
    )


    if (
        len(parts) == 2
        and
        parts[1].startswith(
            "stars_"
        )
    ):

        try:

            referrer_id = int(
                parts[1].split(
                    "_",
                    1
                )[1]
            )


        except ValueError:

            referrer_id = None


    create_or_update_user(

        message.from_user,

        referrer_id
    )


    user = get_user(
        message.from_user.id
    )


    if user[
        "banned"
    ]:

        await message.answer(
            "⛔ Siz botdan bloklangansiz."
        )

        return


    # ----------------------------------------
    # 1. MAJBURIY OBUNA
    # ----------------------------------------

    ok, missing, errors = (
        await check_subscription(
            message.from_user.id
        )
    )


    if not ok:

        if errors:

            names = "\n".join(

                f"• {channel['title']}"

                for channel in errors
            )


            await message.answer(

                "⚠️ <b>KANAL TEKSHIRISH "
                "XATOSI</b>\n\n"

                "Bot quyidagi kanal(lar)ni "
                "tekshira olmadi:\n\n"

                f"{names}\n\n"

                "❗ Botni shu kanal(lar)ga "
                "<b>ADMIN</b> qilib qo'ying.\n\n"

                "Keyin /start ni "
                "qayta bosing.",

                parse_mode="HTML",

                reply_markup=(
                    subscription_keyboard()
                ),
            )

            return


        await send_subscription(
            message
        )

        return


    # ----------------------------------------
    # 2. TELEFON
    # ----------------------------------------

    if not user[
        "phone"
    ]:

        await ask_phone(
            message
        )

        return


    # ----------------------------------------
    # 3. MENYU
    # ----------------------------------------

    await show_menu(

        message,

        message.from_user.id
    )


# ============================================================
# CHECK SUB CALLBACK
# ============================================================

@router.callback_query(
    F.data == "check_sub"
)
async def check_sub_callback(
    callback: CallbackQuery
):

    user = get_user(
        callback.from_user.id
    )


    if not user:

        await callback.answer(

            "Avval /start bosing.",

            show_alert=True
        )

        return


    if user[
        "banned"
    ]:

        await callback.answer(

            "⛔ Siz botdan "
            "bloklangansiz.",

            show_alert=True
        )

        return


    ok, missing, errors = (
        await check_subscription(
            callback.from_user.id
        )
    )


    # ----------------------------------------
    # BOT KANALNI TEKSHIRA OLMADI
    # ----------------------------------------

    if errors:

        names = "\n".join(

            f"• {channel['title']}"

            for channel in errors
        )


        await callback.answer(

            "⚠️ Kanalni tekshirishda "
            "xatolik bor.",

            show_alert=True
        )


        await callback.message.answer(

            "⚠️ <b>KANAL TEKSHIRISH "
            "XATOSI</b>\n\n"

            "Bot quyidagi kanal(lar)ni "
            "tekshira olmadi:\n\n"

            f"{names}\n\n"

            "❗ Botni shu kanal(lar)ga "
            "<b>ADMIN</b> qilib qo'ying.\n\n"

            "Agar kanal username'i "
            "o'zgargan bo'lsa kodni "
            "ham to'g'rilang.",

            parse_mode="HTML",
        )

        return


    # ----------------------------------------
    # USER OBUNA EMAS
    # ----------------------------------------

    if missing:

        names = "\n".join(

            f"❌ {channel['title']}"

            for channel in missing
        )


        await callback.answer(

            "❌ Hali barcha kanallarga "
            "obuna bo'lmagansiz.",

            show_alert=True
        )


        await callback.message.answer(

            "❌ <b>OBUNA TOPILMADI</b>\n\n"

            "Quyidagi kanal(lar)ga "
            "obuna bo'ling:\n\n"

            f"{names}\n\n"

            "Keyin yana "
            "<b>✅ OBUNANI TEKSHIRISH</b> "
            "tugmasini bosing.",

            parse_mode="HTML",

            reply_markup=(
                subscription_keyboard()
            ),
        )

        return


    if not ok:

        await callback.answer(

            "❌ Obunani tekshirib "
            "bo'lmadi.",

            show_alert=True
        )

        return


    # ----------------------------------------
    # HAMMASI TASDIQLANDI
    # ----------------------------------------

    await callback.answer(

        "✅ Barcha obunalar tasdiqlandi!",

        show_alert=True
    )


    try:

        await callback.message.edit_text(

            "✅ <b>OBUNA "
            "TASDIQLANDI!</b>\n\n"

            "Siz barcha 4 ta kanalga "
            "obuna bo'lgansiz.",

            parse_mode="HTML",
        )


    except Exception:

        pass


    user = get_user(
        callback.from_user.id
    )


    if not user[
        "phone"
    ]:

        await ask_phone(
            callback.message
        )

        return


    await show_menu(

        callback.message,

        callback.from_user.id
    )


# ============================================================
# TELEFON REGISTRATION
# ============================================================

@router.message(
    F.contact
)
async def contact_handler(
    message: Message
):

    user = get_user(
        message.from_user.id
    )


    if not user:

        await message.answer(
            "❌ Avval /start bosing."
        )

        return


    if user[
        "banned"
    ]:

        await message.answer(
            "⛔ Siz botdan bloklangansiz."
        )

        return


    # ----------------------------------------
    # OLDIN RO'YXATDAN O'TGAN
    # ----------------------------------------

    if user[
        "phone"
    ]:

        await message.answer(

            "✅ Siz allaqachon "
            "ro'yxatdan o'tgansiz.\n\n"

            f"📱 "
            f"{html.escape(user['phone'])}",

            reply_markup=(
                main_keyboard()
            ),
        )

        return


    # ----------------------------------------
    # FAQAT O'Z KONTAKTI
    # ----------------------------------------

    if (
        message.contact.user_id
        != message.from_user.id
    ):

        await message.answer(

            "❌ Boshqa odamning "
            "telefon raqami "
            "qabul qilinmaydi.\n\n"

            "👇 O'z raqamingizni "
            "tugma orqali yuboring.",

            reply_markup=(
                phone_keyboard()
            ),
        )

        return


    # ----------------------------------------
    # OBUNANI YANA TEKSHIRISH
    # ----------------------------------------

    ok, missing, errors = (
        await check_subscription(
            message.from_user.id
        )
    )


    if not ok:

        await message.answer(

            "❌ Avval barcha "
            "4 ta kanalga obuna bo'ling "
            "va obunani tasdiqlang.",

            reply_markup=(
                ReplyKeyboardRemove()
            ),
        )


        await send_subscription(
            message
        )

        return


    phone = normalize_phone(
        message.contact.phone_number
    )


    # ----------------------------------------
    # DAVLAT TEKSHIRISH
    # ----------------------------------------

    if not valid_phone(
        phone
    ):

        await message.answer(

            "❌ <b>BU RAQAM "
            "QABUL QILINMAYDI</b>\n\n"

            "Faqat:\n\n"

            "🇺🇿 +998 — O'zbekiston\n"

            "🇰🇬 +996 — Qirg'iziston\n"

            "🇷🇺 +7 — Rossiya\n"

            "🇰🇿 +7 — Qozog'iston\n\n"

            "raqamlari qabul qilinadi.",

            parse_mode="HTML",

            reply_markup=(
                phone_keyboard()
            ),
        )

        return


    # ----------------------------------------
    # BIR TELEFON = BIR AKKAUNT
    # ----------------------------------------

    if phone_used_by_other(

        phone,

        message.from_user.id
    ):

        await message.answer(

            "❌ Bu telefon raqami "
            "boshqa akkauntda "
            "ro'yxatdan o'tgan.",

            reply_markup=(
                phone_keyboard()
            ),
        )

        return


    save_phone(

        message.from_user.id,

        phone
    )


    await message.answer(

        "✅ <b>RO'YXATDAN "
        "O'TDINGIZ!</b>\n\n"

        f"📱 Telefon: "
        f"<code>{html.escape(phone)}</code>",

        parse_mode="HTML",

        reply_markup=(
            ReplyKeyboardRemove()
        ),
    )


    # ----------------------------------------
    # ADMIN NOTIFICATION
    # ----------------------------------------

    await notify_admin_registration(

        message,

        phone
    )


    # ----------------------------------------
    # REFERRAL +2 STARS
    # ----------------------------------------

    await reward_referrer(
        message.from_user.id
    )


    # ----------------------------------------
    # MENYU
    # ----------------------------------------

    await show_menu(

        message,

        message.from_user.id
    )


# ============================================================
# STARS ISHLASH
# ============================================================

@router.message(
    F.text == "⭐ Stars ishlash"
)
async def stars_earn(
    message: Message
):

    if not await ensure_registered(

        message,

        check_sub=True
    ):

        return


    user = get_user(
        message.from_user.id
    )


    link = (

        f"https://t.me/"
        f"{BOT_USERNAME}"

        f"?start=stars_"
        f"{message.from_user.id}"
    )


    share = (

        "https://t.me/share/url"

        f"?url={quote(link)}"

        f"&text="
        f"{quote('⭐ MRX STARSS BOT orqali Stars ishlang!')}"
    )


    keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [
                InlineKeyboardButton(

                    text=(
                        "🚀 Do'stlarga yuborish"
                    ),

                    url=share,
                )
            ]

        ]
    )


    await message.answer(

        "⭐ <b>STARS ISHLASH</b>\n\n"

        "Har bir yangi do'stingiz "
        "sizning havolangiz orqali "
        "botga kirib:\n\n"

        "1️⃣ 4 ta kanalga obuna bo'lsa\n"

        "2️⃣ O'z telefon raqamini yuborsa\n"

        "3️⃣ To'liq ro'yxatdan o'tsa\n\n"

        f"Sizga "
        f"<b>+{STARS_REF_REWARD} Stars</b> "
        "beriladi.\n\n"

        f"👥 Referallar: "
        f"<b>{user['stars_referrals']} ta</b>\n"

        f"⭐ Balans: "
        f"<b>{user['stars_balance']} Stars</b>\n\n"

        "🔗 Sizning referral havolangiz:\n"

        f"<code>{link}</code>",

        parse_mode="HTML",

        reply_markup=keyboard,
    )


# ============================================================
# HISOBIM
# ============================================================

@router.message(
    F.text == "👤 Hisobim"
)
async def account(
    message: Message
):

    if not await ensure_registered(

        message,

        check_sub=True
    ):

        return


    user = get_user(
        message.from_user.id
    )


    username = (

        f"@{html.escape(message.from_user.username)}"

        if message.from_user.username

        else "Yo'q"
    )


    await message.answer(

        "👤 <b>MENING HISOBIM</b>\n\n"

        f"🆔 ID: "
        f"<code>{user['user_id']}</code>\n"

        f"🔗 Username: "
        f"<b>{username}</b>\n"

        f"📱 Telefon: "
        f"<code>{html.escape(user['phone'])}</code>\n\n"

        f"⭐ Balans: "
        f"<b>{user['stars_balance']} Stars</b>\n"

        f"👥 Referallar: "
        f"<b>{user['stars_referrals']} ta</b>\n"

        f"💸 Yechilgan: "
        f"<b>{user['withdrawn_stars']} Stars</b>\n\n"

        f"📅 Ro'yxatdan o'tgan: "
        f"<b>{user['created_at'] or '-'}</b>",

        parse_mode="HTML",
    )


# ============================================================
# STARS YECHISH
# ============================================================

@router.message(
    F.text == "⭐ Stars yechish"
)
async def stars_withdraw(
    message: Message
):

    if not await ensure_registered(

        message,

        check_sub=True
    ):

        return


    user = get_user(
        message.from_user.id
    )


    await message.answer(

        "⭐ <b>STARS YECHISH</b>\n\n"

        f"⭐ Balansingiz: "
        f"<b>{user['stars_balance']} Stars</b>\n\n"

        "Yechmoqchi bo'lgan "
        "miqdorni tanlang:",

        parse_mode="HTML",

        reply_markup=(
            withdraw_keyboard()
        ),
    )


# ============================================================
# WITHDRAW REQUEST
# ============================================================

@router.callback_query(
    F.data.startswith(
        "wd:"
    )
)
async def withdraw_callback(
    callback: CallbackQuery
):

    try:

        amount = int(
            callback.data.split(
                ":",
                1
            )[1]
        )


    except ValueError:

        await callback.answer(

            "❌ Xatolik.",

            show_alert=True
        )

        return


    if (
        amount
        not in STARS_WITHDRAW_OPTIONS
    ):

        await callback.answer(

            "❌ Noto'g'ri miqdor.",

            show_alert=True
        )

        return


    user = get_user(
        callback.from_user.id
    )


    if not user:

        await callback.answer(

            "❌ Avval /start bosing.",

            show_alert=True
        )

        return


    if not user[
        "phone"
    ]:

        await callback.answer(

            "📱 Avval ro'yxatdan o'ting.",

            show_alert=True
        )

        return


    if user[
        "banned"
    ]:

        await callback.answer(

            "⛔ Siz bloklangansiz.",

            show_alert=True
        )

        return


    # ----------------------------------------
    # OBUNA TEKSHIRISH
    # ----------------------------------------

    ok, missing, errors = (
        await check_subscription(
            callback.from_user.id
        )
    )


    if not ok:

        if errors:

            await callback.answer(

                "⚠️ Bot kanallardan birini "
                "tekshira olmadi. "
                "Bot adminligini tekshiring.",

                show_alert=True
            )


        else:

            await callback.answer(

                "❌ Avval barcha "
                "4 ta kanalga obuna bo'ling.",

                show_alert=True
            )


        return


    # ----------------------------------------
    # STARSNI VAQTINCHA AYIRISH
    # ----------------------------------------

    try:

        cur.execute(
            "BEGIN IMMEDIATE"
        )


        cur.execute(
            """
            UPDATE users

            SET
                stars_balance =
                stars_balance - ?

            WHERE user_id=?

            AND stars_balance >= ?
            """,
            (
                amount,

                callback.from_user.id,

                amount,
            )
        )


        if cur.rowcount != 1:

            db.rollback()


            await callback.answer(

                "❌ Stars balansingiz "
                "yetarli emas.",

                show_alert=True
            )

            return


        cur.execute(
            """
            INSERT INTO stars_withdrawals (

                user_id,

                amount,

                status,

                created_at

            )

            VALUES (
                ?, ?, 'pending', ?
            )
            """,
            (
                callback.from_user.id,

                amount,

                now_string(),
            )
        )


        withdrawal_id = (
            cur.lastrowid
        )


        cur.execute(
            """
            INSERT INTO transactions (

                user_id,

                amount,

                type,

                description,

                created_at

            )

            VALUES (
                ?, ?, 'stars', ?, ?
            )
            """,
            (
                callback.from_user.id,

                -amount,

                (
                    "Stars yechish "
                    f"so'rovi #{withdrawal_id}"
                ),

                now_string(),
            )
        )


        db.commit()


    except Exception:

        db.rollback()

        raise


    username = (

        f"@{html.escape(callback.from_user.username)}"

        if callback.from_user.username

        else "Yo'q"
    )


    admin_keyboard = InlineKeyboardMarkup(

        inline_keyboard=[

            [
                InlineKeyboardButton(

                    text="✅ Tasdiqlash",

                    callback_data=(
                        f"wda:"
                        f"{withdrawal_id}"
                    ),
                ),

                InlineKeyboardButton(

                    text="❌ Rad etish",

                    callback_data=(
                        f"wdr:"
                        f"{withdrawal_id}"
                    ),
                ),
            ]

        ]
    )


    try:

        await bot.send_message(

            ADMIN_ID,

            "⭐ <b>YANGI STARS "
            "YECHISH SO'ROVI</b>\n\n"

            f"🆔 So'rov: "
            f"<code>#{withdrawal_id}</code>\n"

            f"👤 Ism: "
            f"<b>{html.escape(callback.from_user.first_name or '')}</b>\n"

            f"🔗 Username: "
            f"<b>{username}</b>\n"

            f"🆔 Telegram ID: "
            f"<code>{callback.from_user.id}</code>\n"

            f"📱 Telefon: "
            f"<code>{html.escape(user['phone'])}</code>\n"

            f"⭐ Miqdor: "
            f"<b>{amount} Stars</b>",

            parse_mode="HTML",

            reply_markup=(
                admin_keyboard
            ),
        )


    except Exception as error:

        logger.warning(

            "Withdraw admin "
            "notification error: %s",

            error
        )


    await callback.message.answer(

        "✅ <b>SO'ROV YUBORILDI!</b>\n\n"

        f"⭐ Miqdor: "
        f"<b>{amount} Stars</b>\n"

        f"🆔 So'rov: "
        f"<code>#{withdrawal_id}</code>\n\n"

        "Admin so'rovingizni "
        "tekshiradi.",

        parse_mode="HTML",
    )


    await callback.answer()


# ============================================================
# ADMIN APPROVE WITHDRAW
# ============================================================

@router.callback_query(
    F.data.startswith(
        "wda:"
    )
)
async def withdrawal_approve(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(

            "⛔ Ruxsat yo'q.",

            show_alert=True
        )

        return


    try:

        withdrawal_id = int(
            callback.data.split(
                ":",
                1
            )[1]
        )


    except ValueError:

        return


    cur.execute(
        """
        SELECT *

        FROM stars_withdrawals

        WHERE id=?
        """,
        (
            withdrawal_id,
        )
    )


    withdrawal = (
        cur.fetchone()
    )


    if not withdrawal:

        await callback.answer(

            "❌ So'rov topilmadi.",

            show_alert=True
        )

        return


    cur.execute(
        """
        UPDATE stars_withdrawals

        SET status='approved'

        WHERE id=?

        AND status='pending'
        """,
        (
            withdrawal_id,
        )
    )


    if cur.rowcount != 1:

        db.rollback()


        await callback.answer(

            "⚠️ Bu so'rov "
            "allaqachon ko'rib chiqilgan.",

            show_alert=True
        )

        return


    cur.execute(
        """
        UPDATE users

        SET
            withdrawn_stars =
            withdrawn_stars + ?

        WHERE user_id=?
        """,
        (
            withdrawal[
                "amount"
            ],

            withdrawal[
                "user_id"
            ],
        )
    )


    db.commit()


    try:

        await bot.send_message(

            withdrawal[
                "user_id"
            ],

            "✅ <b>STARS YECHISH "
            "TASDIQLANDI!</b>\n\n"

            f"⭐ Miqdor: "
            f"<b>{withdrawal['amount']} Stars</b>\n\n"

            "So'rovingiz admin "
            "tomonidan tasdiqlandi.",

            parse_mode="HTML",
        )


    except Exception:

        pass


    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )


    except Exception:

        pass


    await callback.message.answer(

        f"✅ So'rov "
        f"#{withdrawal_id} "
        f"tasdiqlandi."
    )


    await callback.answer(
        "✅ Tasdiqlandi"
    )


# ============================================================
# ADMIN REJECT WITHDRAW
# ============================================================

@router.callback_query(
    F.data.startswith(
        "wdr:"
    )
)
async def withdrawal_reject(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(

            "⛔ Ruxsat yo'q.",

            show_alert=True
        )

        return


    try:

        withdrawal_id = int(
            callback.data.split(
                ":",
                1
            )[1]
        )


    except ValueError:

        return


    cur.execute(
        """
        SELECT *

        FROM stars_withdrawals

        WHERE id=?
        """,
        (
            withdrawal_id,
        )
    )


    withdrawal = (
        cur.fetchone()
    )


    if not withdrawal:

        await callback.answer(

            "❌ So'rov topilmadi.",

            show_alert=True
        )

        return


    try:

        cur.execute(
            "BEGIN IMMEDIATE"
        )


        cur.execute(
            """
            UPDATE stars_withdrawals

            SET status='rejected'

            WHERE id=?

            AND status='pending'
            """,
            (
                withdrawal_id,
            )
        )


        if cur.rowcount != 1:

            db.rollback()


            await callback.answer(

                "⚠️ Bu so'rov "
                "allaqachon ko'rib chiqilgan.",

                show_alert=True
            )

            return


        cur.execute(
            """
            UPDATE users

            SET
                stars_balance =
                stars_balance + ?

            WHERE user_id=?
            """,
            (
                withdrawal[
                    "amount"
                ],

                withdrawal[
                    "user_id"
                ],
            )
        )


        cur.execute(
            """
            INSERT INTO transactions (

                user_id,

                amount,

                type,

                description,

                created_at

            )

            VALUES (
                ?, ?, 'stars', ?, ?
            )
            """,
            (
                withdrawal[
                    "user_id"
                ],

                withdrawal[
                    "amount"
                ],

                (
                    "Rad etilgan yechish "
                    f"#{withdrawal_id} "
                    "qaytarildi"
                ),

                now_string(),
            )
        )


        db.commit()


    except Exception:

        db.rollback()

        raise


    try:

        await bot.send_message(

            withdrawal[
                "user_id"
            ],

            "❌ <b>STARS YECHISH "
            "RAD ETILDI</b>\n\n"

            f"⭐ <b>{withdrawal['amount']} "
            "Stars</b> balansingizga "
            "qaytarildi.",

            parse_mode="HTML",
        )


    except Exception:

        pass


    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )


    except Exception:

        pass


    await callback.message.answer(

        f"❌ So'rov "
        f"#{withdrawal_id} "
        "rad etildi.\n"

        "Stars userga qaytarildi."
    )


    await callback.answer(
        "❌ Rad etildi"
    )


# ============================================================
# NUMBER SHOP
# ============================================================

@router.message(
    F.text == "🌐 Raqam sotib olish"
)
async def number_shop(
    message: Message
):

    if not await ensure_registered(

        message,

        check_sub=True
    ):

        return


    await message.answer(

        "🌐 <b>TELEGRAM UCHUN "
        "XORIJIY RAQAMLAR SOTUVDA!</b> ‼️\n"

        "💎 <b>PREMIUM RAQAMLAR — "
        "QULAY NARXLAR</b> 💎\n\n"

        "🇺🇿 <b>O'zbekiston — 12 939 so'm</b>\n"

        "🇰🇬 <b>Qirg'iziston — 20 503 so'm</b>\n"

        "🇬🇪 <b>Gruziya — 23 253 so'm</b>\n"

        "🇦🇿 <b>Ozarbayjon — 23 253 so'm</b>\n"

        "🇹🇲 <b>Turkmaniston — 14 314 so'm</b>\n"

        "🇹🇯 <b>Tojikiston — 13 627 so'm</b>\n"

        "🇮🇷 <b>Eron — 10 876 so'm</b>\n"

        "🇳🇵 <b>Nepal — 10 876 so'm</b>\n"

        "🇲🇳 <b>Mongoliya — 21 878 so'm</b>\n"

        "🇧🇹 <b>Butan — 24 628 so'm</b>\n"

        "🇨🇴 <b>Kolumbiya — 8 126 so'm</b>\n"

        "🇺🇸 <b>Amerika Qo'shma "
        "Shtatlari — 8 813 so'm</b>\n"

        "🇧🇩 <b>Bangladesh — 8 813 so'm</b>\n"

        "🇮🇳 <b>Hindiston — 8 813 so'm</b>\n"

        "🇮🇩 <b>Indoneziya — 9 501 so'm</b>\n"

        "🇨🇱 <b>Chili — 10 188 so'm</b>\n"

        "🇵🇰 <b>Pokiston — 10 188 so'm</b>\n"

        "🇲🇲 <b>Myanma (Birma) — "
        "10 188 so'm</b>\n"

        "🇰🇪 <b>Keniya — 10 188 so'm</b>\n"

        "🇦🇴 <b>Angola — 10 601 so'm</b>\n\n"

        "━━━━━━━━━━━━━━━━\n"

        "☄️ <b>TEZKOR XIZMAT</b>\n"

        "💵 <b>HAMYONBOP NARXLAR</b>\n"

        "🌐 <b>20 TA DAVLAT "
        "RAQAMLARI MAVJUD</b>\n"

        "✈️ <b>TELEGRAM UCHUN RAQAMLAR</b>\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🛒 <b>BUYURTMA BERISH UCHUN:</b>\n"

        "📩 <b>@YOLDOSHEV_ORG</b>\n\n"

        "📈 Kerakli davlatni tanlang "
        "va buyurtma bering! 🔥",

        parse_mode="HTML",

        reply_markup=(
            admin_link_keyboard(
                "🛒 Raqam buyurtma qilish"
            )
        ),
    )


# ============================================================
# NFT BUY
# ============================================================

@router.message(
    F.text == "💎 NFT sotib olish"
)
async def nft_buy(
    message: Message
):

    if not await ensure_registered(

        message,

        check_sub=True
    ):

        return


    await message.answer(

        "💎 <b>NFT SOTIB OLISH</b>\n\n"

        "NFT sotib olish uchun "
        "admin bilan bog'laning.\n\n"

        "👇 Tugmani bosing:",

        parse_mode="HTML",

        reply_markup=(
            admin_link_keyboard(
                "💎 NFT sotib olish"
            )
        ),
    )


# ============================================================
# SPONSOR
# ============================================================

@router.message(
    F.text == "🤝 Homiy bo'lish"
)
async def sponsor(
    message: Message
):

    if not await ensure_registered(

        message,

        check_sub=True
    ):

        return


    await message.answer(

        "🤝 <b>HOMIY BO'LISH</b>\n\n"

        "Reklama, homiylik va "
        "hamkorlik uchun "
        "admin bilan bog'laning.",

        parse_mode="HTML",

        reply_markup=(
            admin_link_keyboard(
                "🤝 Homiylik bo'yicha yozish"
            )
        ),
    )


# ============================================================
# HELP
# ============================================================

@router.message(
    F.text == "🆘 Yordam"
)
async def help_handler(
    message: Message
):

    if not await ensure_registered(

        message,

        check_sub=True
    ):

        return


    await message.answer(

        "🆘 <b>YORDAM</b>\n\n"

        "Bot bo'yicha savol yoki "
        "muammo bo'lsa admin bilan "
        "bog'laning.\n\n"

        "📩 <b>@yoldoshev_org</b>",

        parse_mode="HTML",

        reply_markup=(
            admin_link_keyboard(
                "🆘 Adminga yozish"
            )
        ),
    )


# ============================================================
# GUIDE
# ============================================================

@router.message(
    F.text == "📖 Qo'llanma"
)
async def guide(
    message: Message
):

    if not await ensure_registered(

        message,

        check_sub=True
    ):

        return


    await message.answer(

        "📖 <b>BOT QO'LLANMASI</b>\n\n"

        "⭐ <b>STARS ISHLASH</b>\n\n"

        "Stars ishlash tugmasini "
        "bosing va referral "
        "havolangizni do'stlaringizga "
        "yuboring.\n\n"

        "Do'stingiz:\n\n"

        "1️⃣ Havolangiz orqali botga kiradi\n"

        "2️⃣ 4 ta kanalga obuna bo'ladi\n"

        "3️⃣ O'z telefon raqamini yuboradi\n"

        "4️⃣ To'liq ro'yxatdan o'tadi\n\n"

        f"Shundan keyin sizga "
        f"<b>+{STARS_REF_REWARD} Stars</b> "
        "beriladi.\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "⭐ <b>STARS YECHISH</b>\n\n"

        "Balansingiz yetarli bo'lsa "
        "Stars yechish bo'limiga "
        "kiring va kerakli miqdorni "
        "tanlang.\n\n"

        "So'rov adminga yuboriladi.\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "🌐 <b>RAQAM SOTIB OLISH</b>\n\n"

        "Kerakli davlat narxini "
        "ko'ring va @yoldoshev_org orqali "
        "buyurtma bering.\n\n"

        "━━━━━━━━━━━━━━━━\n\n"

        "💎 <b>NFT SOTIB OLISH</b>\n\n"

        "NFT sotib olish uchun "
        "@yoldoshev_org bilan bog'laning.",

        parse_mode="HTML",
    )


# ============================================================
# ADMIN PANEL
# ============================================================

@router.message(
    Command("admin")
)
async def admin_panel(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return


    await message.answer(

        "⚙️ <b>MRX ADMIN PANEL</b>\n\n"

        "Kerakli bo'limni tanlang:",

        parse_mode="HTML",

        reply_markup=(
            admin_panel_keyboard()
        ),
    )


# ============================================================
# ADMIN STATS
# ============================================================

@router.callback_query(
    F.data == "adm:stats"
)
async def admin_stats(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        return


    cur.execute(
        """
        SELECT COUNT(*) AS n

        FROM users
        """
    )


    total = (
        cur.fetchone()["n"]
    )


    cur.execute(
        """
        SELECT COUNT(*) AS n

        FROM users

        WHERE phone IS NOT NULL

        AND phone<>''
        """
    )


    registered = (
        cur.fetchone()["n"]
    )


    cur.execute(
        """
        SELECT
            COALESCE(
                SUM(stars_balance),
                0
            ) AS n

        FROM users
        """
    )


    stars = (
        cur.fetchone()["n"]
    )


    cur.execute(
        """
        SELECT COUNT(*) AS n

        FROM stars_withdrawals

        WHERE status='pending'
        """
    )


    pending = (
        cur.fetchone()["n"]
    )


    cur.execute(
        """
        SELECT COUNT(*) AS n

        FROM referral_log

        WHERE referral_type='stars'
        """
    )


    referrals = (
        cur.fetchone()["n"]
    )


    await callback.message.answer(

        "📊 <b>STATISTIKA</b>\n\n"

        f"👥 Jami user: "
        f"<b>{total}</b>\n"

        f"📱 Ro'yxatdan o'tgan: "
        f"<b>{registered}</b>\n"

        f"👥 Referral: "
        f"<b>{referrals}</b>\n"

        f"⭐ Userlardagi Stars: "
        f"<b>{stars}</b>\n"

        f"⏳ Pending yechish: "
        f"<b>{pending}</b>",

        parse_mode="HTML",
    )


    await callback.answer()


# ============================================================
# ADMIN PENDING
# ============================================================

@router.callback_query(
    F.data == "adm:pending"
)
async def admin_pending(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        return


    cur.execute(
        """
        SELECT

            w.*,

            u.username,

            u.first_name

        FROM stars_withdrawals w

        LEFT JOIN users u

        ON u.user_id=w.user_id

        WHERE w.status='pending'

        ORDER BY w.id DESC

        LIMIT 10
        """
    )


    rows = (
        cur.fetchall()
    )


    if not rows:

        await callback.message.answer(
            "✅ Pending so'rov yo'q."
        )


        await callback.answer()

        return


    text = (
        "⏳ <b>OXIRGI PENDING "
        "SO'ROVLAR</b>\n\n"
    )


    for row in rows:

        text += (

            f"#{row['id']} | "

            f"ID "
            f"<code>{row['user_id']}</code> | "

            f"<b>{row['amount']} ⭐</b>\n"
        )


    await callback.message.answer(

        text,

        parse_mode="HTML",
    )


    await callback.answer()


# ============================================================
# ADMIN HELP
# ============================================================

@router.callback_query(
    F.data == "adm:help"
)
async def admin_help(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        return


    await callback.message.answer(

        "📚 <b>ADMIN BUYRUQLARI</b>\n\n"

        "<code>/user USER_ID</code>\n"
        "— user ma'lumoti\n\n"

        "<code>/addstars USER_ID MIQDOR</code>\n"
        "— Stars qo'shish\n\n"

        "<code>/removestars USER_ID MIQDOR</code>\n"
        "— Stars ayirish\n\n"

        "<code>/ban USER_ID</code>\n"
        "— bloklash\n\n"

        "<code>/unban USER_ID</code>\n"
        "— blokdan chiqarish\n\n"

        "<code>/all MATN</code>\n"
        "— barcha userlarga xabar",

        parse_mode="HTML",
    )


    await callback.answer()


# ============================================================
# ADMIN USER INFO
# ============================================================

@router.message(
    Command("user")
)
async def admin_user(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return


    parts = (
        message.text
        or ""
    ).split()


    if (
        len(parts) != 2
        or
        not parts[1].isdigit()
    ):

        await message.answer(

            "Format:\n"

            "<code>"
            "/user 123456789"
            "</code>",

            parse_mode="HTML",
        )

        return


    user = get_user(
        int(parts[1])
    )


    if not user:

        await message.answer(
            "❌ User topilmadi."
        )

        return


    username = (
        user[
            "username"
        ]
        or "yoq"
    )


    await message.answer(

        "👤 <b>USER MA'LUMOTLARI</b>\n\n"

        f"🆔 ID: "
        f"<code>{user['user_id']}</code>\n"

        f"🔗 Username: "
        f"@{html.escape(username)}\n"

        f"👤 Ism: "
        f"{html.escape(user['first_name'] or '')}\n"

        f"📱 Telefon: "
        f"<code>"
        f"{html.escape(user['phone'] or 'yoq')}"
        f"</code>\n"

        f"⭐ Stars: "
        f"<b>{user['stars_balance']}</b>\n"

        f"👥 Referral: "
        f"<b>{user['stars_referrals']}</b>\n"

        f"💸 Yechilgan: "
        f"<b>{user['withdrawn_stars']}</b>\n"

        f"🚫 Banned: "
        f"<b>{user['banned']}</b>",

        parse_mode="HTML",
    )


# ============================================================
# ADMIN ADD STARS
# ============================================================

@router.message(
    Command("addstars")
)
async def admin_addstars(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return


    parts = (
        message.text
        or ""
    ).split()


    if len(
        parts
    ) != 3:

        await message.answer(

            "Format:\n"

            "<code>"
            "/addstars USER_ID 10"
            "</code>",

            parse_mode="HTML",
        )

        return


    try:

        user_id = int(
            parts[1]
        )

        amount = int(
            parts[2]
        )


    except ValueError:

        await message.answer(
            "❌ Raqam kiriting."
        )

        return


    if (
        amount <= 0
        or
        not get_user(
            user_id
        )
    ):

        await message.answer(

            "❌ User yoki miqdor "
            "noto'g'ri."
        )

        return


    change_stars(

        user_id,

        amount,

        "Admin Stars qo'shdi"
    )


    await message.answer(

        f"✅ <code>{user_id}</code> "
        f"ga <b>+{amount} Stars</b> "
        "qo'shildi.",

        parse_mode="HTML",
    )


    try:

        await bot.send_message(

            user_id,

            "🎁 <b>ADMIN BALANSINGIZGA "
            "STARS QO'SHDI</b>\n\n"

            f"⭐ +{amount} Stars",

            parse_mode="HTML",
        )


    except Exception:

        pass


# ============================================================
# ADMIN REMOVE STARS
# ============================================================

@router.message(
    Command("removestars")
)
async def admin_removestars(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return


    parts = (
        message.text
        or ""
    ).split()


    if len(
        parts
    ) != 3:

        await message.answer(

            "Format:\n"

            "<code>"
            "/removestars USER_ID 10"
            "</code>",

            parse_mode="HTML",
        )

        return


    try:

        user_id = int(
            parts[1]
        )

        amount = int(
            parts[2]
        )


    except ValueError:

        await message.answer(
            "❌ Raqam kiriting."
        )

        return


    if (
        amount <= 0
        or
        not get_user(
            user_id
        )
    ):

        await message.answer(

            "❌ User yoki miqdor "
            "noto'g'ri."
        )

        return


    if not change_stars(

        user_id,

        -amount,

        "Admin Stars ayirdi"
    ):

        await message.answer(

            "❌ User balansida "
            "yetarli Stars yo'q."
        )

        return


    await message.answer(

        f"✅ <code>{user_id}</code> "
        f"dan <b>{amount} Stars</b> "
        "ayirildi.",

        parse_mode="HTML",
    )


# ============================================================
# ADMIN BAN
# ============================================================

@router.message(
    Command("ban")
)
async def admin_ban(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return


    parts = (
        message.text
        or ""
    ).split()


    if (
        len(parts) != 2
        or
        not parts[1].isdigit()
    ):

        await message.answer(

            "Format:\n"

            "<code>"
            "/ban USER_ID"
            "</code>",

            parse_mode="HTML",
        )

        return


    user_id = int(
        parts[1]
    )


    if not get_user(
        user_id
    ):

        await message.answer(
            "❌ User topilmadi."
        )

        return


    cur.execute(
        """
        UPDATE users

        SET banned=1

        WHERE user_id=?
        """,
        (
            user_id,
        )
    )


    db.commit()


    await message.answer(
        "✅ User bloklandi."
    )


# ============================================================
# ADMIN UNBAN
# ============================================================

@router.message(
    Command("unban")
)
async def admin_unban(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return


    parts = (
        message.text
        or ""
    ).split()


    if (
        len(parts) != 2
        or
        not parts[1].isdigit()
    ):

        await message.answer(

            "Format:\n"

            "<code>"
            "/unban USER_ID"
            "</code>",

            parse_mode="HTML",
        )

        return


    user_id = int(
        parts[1]
    )


    if not get_user(
        user_id
    ):

        await message.answer(
            "❌ User topilmadi."
        )

        return


    cur.execute(
        """
        UPDATE users

        SET banned=0

        WHERE user_id=?
        """,
        (
            user_id,
        )
    )


    db.commit()


    await message.answer(
        "✅ User blokdan chiqarildi."
    )


# ============================================================
# BROADCAST
# ============================================================

@router.message(
    Command("all")
)
async def admin_broadcast(
    message: Message
):

    if not is_admin(
        message.from_user.id
    ):

        return


    text_to_send = (
        message.text
        or ""
    ).partition(
        " "
    )[2].strip()


    if not text_to_send:

        await message.answer(

            "Format:\n"

            "<code>"
            "/all Xabaringiz"
            "</code>",

            parse_mode="HTML",
        )

        return


    cur.execute(
        """
        SELECT user_id

        FROM users

        WHERE banned=0
        """
    )


    user_ids = [

        row[
            "user_id"
        ]

        for row in cur.fetchall()

    ]


    success = 0

    failed = 0


    status = await message.answer(

        f"📨 Yuborish boshlandi:\n"
        f"<b>{len(user_ids)} user</b>",

        parse_mode="HTML",
    )


    for user_id in user_ids:

        try:

            await bot.send_message(

                user_id,

                text_to_send
            )


            success += 1


        except Exception:

            failed += 1


        await asyncio.sleep(
            0.05
        )


    await status.edit_text(

        "✅ <b>BROADCAST TUGADI</b>\n\n"

        f"📨 Yetdi: "
        f"<b>{success}</b>\n"

        f"❌ Yetmadi: "
        f"<b>{failed}</b>",

        parse_mode="HTML",
    )


# ============================================================
# UNKNOWN MESSAGE
# ============================================================

@router.message()
async def unknown(
    message: Message
):

    user = get_user(
        message.from_user.id
    )


    if not user:

        await message.answer(

            "Botni boshlash uchun "
            "/start bosing."
        )

        return


    if user[
        "banned"
    ]:

        await message.answer(
            "⛔ Siz botdan bloklangansiz."
        )

        return


    if not user[
        "phone"
    ]:

        await message.answer(

            "📱 Avval /start orqali "
            "ro'yxatdan o'ting."
        )

        return


    await message.answer(

        "👇 Menyudan kerakli "
        "bo'limni tanlang.",

        reply_markup=(
            main_keyboard()
        ),
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    global BOT_USERNAME


    me = await bot.get_me()


    BOT_USERNAME = (
        me.username
    )


    print(
        "=" * 56
    )


    print(
        "MRX STARSS PREMIUM BOT "
        "ISHGA TUSHDI"
    )


    print(
        f"Bot: @{BOT_USERNAME}"
    )


    print(
        f"Admin: {ADMIN_ID}"
    )


    print(
        "Majburiy kanallar:"
    )


    for channel in CHANNELS:

        print(
            " -",
            channel[
                "chat_id"
            ]
        )


    print(
        f"Referral bonus: "
        f"+{STARS_REF_REWARD} Stars"
    )


    print(
        "=" * 56
    )


    await bot.delete_webhook(
        drop_pending_updates=True
    )


    await dp.start_polling(

        bot,

        allowed_updates=(
            dp.resolve_used_update_types()
        ),
    )


if __name__ == "__main__":

    try:

        asyncio.run(
            main()
        )


    except KeyboardInterrupt:

        print(
            "Bot to'xtatildi."
        )