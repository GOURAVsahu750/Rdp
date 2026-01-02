import logging
import sqlite3
import random
import string
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================= CONFIG =================
TOKEN = "8255403112:AAGbXkLDdJMzNXt77DbVVOUX84UCa4XmMjY"
OWNER_ID = 8188215655

FORCE_CHANNELS = ["@TITANXBOTMAKING", "@TITANXERA1"]
PRIVATE_CHANNEL_LINK = "https://t.me/+78TCYQvug8JjYmNl"

REQUIRED_REFERRALS = 8
PORT = int(os.environ.get("PORT", 8080))

# Railway public URL (CHANGE PROJECT NAME ONLY)
WEBHOOK_URL = "https://rdp-production-3cc0.up.railway.app"
# =========================================

logging.basicConfig(level=logging.INFO)

# ================= DATABASE =================
db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS rdp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS redeem_codes (
    code TEXT PRIMARY KEY,
    points INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS states (
    user_id INTEGER PRIMARY KEY,
    state TEXT
)
""")

db.commit()

upload_buffer = []

# ================= FORCE JOIN =================
async def is_joined(bot, uid):
    for ch in FORCE_CHANNELS:
        try:
            m = await bot.get_chat_member(ch, uid)
            if m.status in ("left", "kicked"):
                return False
        except:
            return False
    return True

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if not await is_joined(context.bot, user.id):
        kb = [
            [InlineKeyboardButton("📢 Join Channel 1", url="https://t.me/TITANXBOTMAKING")],
            [InlineKeyboardButton("📢 Join Channel 2", url="https://t.me/TITANXERA1")],
            [InlineKeyboardButton("🔒 Private Channel (Request)", url=PRIVATE_CHANNEL_LINK)],
        ]
        await update.message.reply_text(
            "❌ Pehle sab channels join karo",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return

    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users VALUES (?,0)", (user.id,))
        db.commit()

        if args:
            try:
                ref = int(args[0])
                cur.execute(
                    "UPDATE users SET balance = balance + 1 WHERE user_id=?",
                    (ref,),
                )
                db.commit()
                await context.bot.send_message(ref, "🎉 1 referral added!")
            except:
                pass

        await context.bot.send_message(
            OWNER_ID, f"🆕 New user joined: {user.id}"
        )

    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("🔗 Invite", callback_data="invite")],
        [InlineKeyboardButton("🎁 Claim RDP", callback_data="claim")],
        [InlineKeyboardButton("🏆 Top Rank", callback_data="top")],
    ]

    await update.message.reply_text(
        "🤖 Welcome to Free RDP Bot",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ================= BUTTONS =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    if q.data == "balance":
        cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        await q.message.reply_text(f"💰 Balance: {cur.fetchone()[0]}")

    elif q.data == "invite":
        await q.message.reply_text(
            f"https://t.me/{context.bot.username}?start={uid}"
        )

    elif q.data == "top":
        cur.execute(
            "SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10"
        )
        text = "🏆 TOP REFERRERS\n\n"
        for i, r in enumerate(cur.fetchall(), 1):
            text += f"{i}. {r[0]} → {r[1]}\n"
        await q.message.reply_text(text)

    elif q.data == "claim":
        cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        bal = cur.fetchone()[0]

        if bal < REQUIRED_REFERRALS:
            await q.message.reply_text("❌ 8 referrals required")
            return

        cur.execute("SELECT id, data FROM rdp LIMIT 1")
        rdp = cur.fetchone()

        if not rdp:
            await q.message.reply_text(
                "❌ Stock not available, try again later"
            )
            return

        cur.execute("DELETE FROM rdp WHERE id=?", (rdp[0],))
        cur.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id=?",
            (REQUIRED_REFERRALS, uid),
        )
        db.commit()

        await q.message.reply_text(f"🎁 Your RDP:\n\n{rdp[1]}")

# ================= STOCK =================
async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    cur.execute("SELECT COUNT(*) FROM rdp")
    await update.message.reply_text(
        f"📦 RDP Stock: {cur.fetchone()[0]}"
    )

# ================= UPLOAD =================
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        upload_buffer.clear()
        await update.message.reply_text(
            "📤 Send RDP details (multiple), then /done"
        )

async def collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        upload_buffer.append(update.message.text)

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        for i in upload_buffer:
            cur.execute("INSERT INTO rdp (data) VALUES (?)", (i,))
        db.commit()
        upload_buffer.clear()
        await update.message.reply_text("✅ RDP stock updated")

# ================= MAIN (CORRECT) =================
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("stock", stock))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect))

    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
    )

if __name__ == "__main__":
    main()
