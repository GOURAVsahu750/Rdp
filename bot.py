import logging, sqlite3, random, string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# ================= CONFIG =================
TOKEN = "8188215655:AAGbXkLDdJMzNXt77DbVVOUX84UCa4XmMjY"
OWNER_ID = 8188215655

FORCE_CHANNELS = ["@TITANXBOTMAKING", "@TITANXERA1"]
PRIVATE_CHANNEL_LINK = "https://t.me/+78TCYQvug8JjYmNl"

REQUIRED_REFERRALS = 8
# =========================================

logging.basicConfig(level=logging.INFO)

db = sqlite3.connect("data.db", check_same_thread=False)
cur = db.cursor()

# ================= DATABASE =================
cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE IF NOT EXISTS rdp (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS redeem_codes (code TEXT PRIMARY KEY, points INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS states (user_id INTEGER PRIMARY KEY, state TEXT)")
db.commit()

upload_buffer = []

# ========== FORCE JOIN ==========
async def is_joined(bot, uid):
    for ch in FORCE_CHANNELS:
        try:
            m = await bot.get_chat_member(ch, uid)
            if m.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# ========== START ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    args = context.args

    if not await is_joined(context.bot, u.id):
        kb = [
            [InlineKeyboardButton("📢 Join Channel 1", url=f"https://t.me/{FORCE_CHANNELS[0][1:]}")],
            [InlineKeyboardButton("📢 Join Channel 2", url=f"https://t.me/{FORCE_CHANNELS[1][1:]}")],
            [InlineKeyboardButton("🔒 Join Private Channel (Request)", url=PRIVATE_CHANNEL_LINK)]
        ]
        await update.message.reply_text(
            "❌ Pehle sab channels join karo\n"
            "Private channel me join request bhejo",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    cur.execute("SELECT * FROM users WHERE user_id=?", (u.id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO users VALUES (?,0)", (u.id,))
        db.commit()

        if args:
            ref = int(args[0])
            cur.execute("UPDATE users SET balance = balance + 1 WHERE user_id=?", (ref,))
            db.commit()
            await context.bot.send_message(ref, "🎉 1 referral added!")

        await context.bot.send_message(OWNER_ID, f"🆕 New user joined: {u.id}")

    kb = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("🔗 Invite", callback_data="invite")],
        [InlineKeyboardButton("🎁 Claim RDP", callback_data="claim")],
        [InlineKeyboardButton("🏆 Top Rank", callback_data="top")]
    ]
    await update.message.reply_text("🤖 Welcome to Free RDP Bot", reply_markup=InlineKeyboardMarkup(kb))

# ========== BUTTONS ==========
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id
    await q.answer()

    if q.data == "balance":
        cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        await q.message.reply_text(f"💰 Balance: {cur.fetchone()[0]}")

    elif q.data == "invite":
        await q.message.reply_text(
            f"🔗 Referral link:\nhttps://t.me/{context.bot.username}?start={uid}"
        )

    elif q.data == "top":
        cur.execute("SELECT user_id,balance FROM users ORDER BY balance DESC LIMIT 10")
        txt = "🏆 TOP REFERRERS\n\n"
        for i,u in enumerate(cur.fetchall(),1):
            txt += f"{i}. {u[0]} → {u[1]}\n"
        await q.message.reply_text(txt)

    elif q.data == "claim":
        # balance check
        cur.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        bal = cur.fetchone()[0]

        if bal < REQUIRED_REFERRALS:
            await q.message.reply_text(f"❌ Need {REQUIRED_REFERRALS} referrals")
            return

        # RDP STOCK CHECK
        cur.execute("SELECT id, data FROM rdp ORDER BY id ASC LIMIT 1")
        r = cur.fetchone()

        if not r:
            await q.message.reply_text("❌ Stock not available, try again later")
            return

        rdp_id, rdp_data = r

        # CUT POINTS
        cur.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id=?",
            (REQUIRED_REFERRALS, uid)
        )

        # REMOVE RDP FROM STOCK
        cur.execute("DELETE FROM rdp WHERE id=?", (rdp_id,))
        db.commit()

        await q.message.reply_text(f"🎁 Your RDP:\n\n{rdp_data}")

# ========== UPLOAD ==========
async def upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        upload_buffer.clear()
        await update.message.reply_text("📤 Send RDP details (multiple). Use /done")

async def collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # REDEEM STATE
    cur.execute("SELECT state FROM states WHERE user_id=?", (uid,))
    st = cur.fetchone()

    if st and st[0] == "redeem_wait":
        code = update.message.text.strip()
        cur.execute("SELECT points FROM redeem_codes WHERE code=?", (code,))
        r = cur.fetchone()

        if r:
            cur.execute(
                "UPDATE users SET balance=balance+? WHERE user_id=?",
                (r[0], uid)
            )
            cur.execute("DELETE FROM redeem_codes WHERE code=?", (code,))
            db.commit()
            await update.message.reply_text(f"✅ Redeemed {r[0]} points!")
        else:
            await update.message.reply_text("❌ Invalid or already used code")

        cur.execute("DELETE FROM states WHERE user_id=?", (uid,))
        db.commit()
        return

    # ADMIN UPLOAD COLLECT
    if uid == OWNER_ID:
        upload_buffer.append(update.message.text)

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == OWNER_ID:
        for item in upload_buffer:
            cur.execute("INSERT INTO rdp (data) VALUES (?)", (item,))
        db.commit()
        upload_buffer.clear()
        await update.message.reply_text("✅ RDP Stock Updated")

# ========== REDEEM ==========
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute(
        "INSERT OR REPLACE INTO states VALUES (?,?)",
        (update.effective_user.id, "redeem_wait")
    )
    db.commit()
    await update.message.reply_text("🎟 Send redeem code")

# ========== CREATE REDEEM ==========
async def createredeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    c, p = int(context.args[0]), int(context.args[1])
    codes = []

    for _ in range(c):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        cur.execute("INSERT INTO redeem_codes VALUES (?,?)", (code, p))
        codes.append(code)

    db.commit()
    await update.message.reply_text("🎟 Redeem Codes:\n" + "\n".join(codes))

# ========== MAIN ==========
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(CommandHandler("upload", upload))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("createredeem", createredeem))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, collect))

    app.run_polling()

if __name__ == "__main__":
    main()