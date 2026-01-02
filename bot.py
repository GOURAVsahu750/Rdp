from telegram import *
from telegram.ext import *
from config import *
import database as db

app = ApplicationBuilder().token(BOT_TOKEN).build()

# ---------- HELPERS ----------

def main_keyboard():
    return ReplyKeyboardMarkup([
        ["🎯 Refer", "📦 Stock"],
        ["🎁 Redeem", "📊 Stats"]
    ], resize_keyboard=True)

async def force_join(update, context):
    user = update.effective_user.id

    for ch in PUBLIC_CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch, user)
            if member.status == "left":
                return False
        except:
            return False
    return True

# ---------- START ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.id

    if not await force_join(update, context):
        await update.message.reply_text(
            "❌ Pehle channels join karo:\n"
            + "\n".join(PUBLIC_CHANNELS)
        )
        return

    ref = context.args[0] if context.args else None

    db.cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user,))
    if ref:
        db.cur.execute("UPDATE users SET points = points + 1 WHERE user_id=?", (ref,))
    db.conn.commit()

    await update.message.reply_text(
        "✅ Welcome!\n"
        "🔒 Private channel join request bhejo:\n"
        f"{PRIVATE_CHANNEL_LINK}",
        reply_markup=main_keyboard()
    )

# ---------- REFER ----------

async def refer(update, context):
    uid = update.effective_user.id
    link = f"https://t.me/{context.bot.username}?start={uid}"
    await update.message.reply_text(
        f"👥 Refer link:\n{link}\n\n"
        f"🎯 {POINTS_REQUIRED} points = 1 RDP"
    )

# ---------- STOCK ----------

async def stock(update, context):
    db.cur.execute("SELECT COUNT(*) FROM rdps WHERE assigned=0")
    s = db.cur.fetchone()[0]
    await update.message.reply_text(f"📦 Available RDPs: {s}")

# ---------- REDEEM ----------

async def redeem(update, context):
    uid = update.effective_user.id
    db.cur.execute("SELECT points FROM users WHERE user_id=?", (uid,))
    pts = db.cur.fetchone()[0]

    if pts < POINTS_REQUIRED:
        await update.message.reply_text("❌ Points not enough")
        return

    db.cur.execute("SELECT id, rdp FROM rdps WHERE assigned=0 LIMIT 1")
    rdp = db.cur.fetchone()

    if not rdp:
        await update.message.reply_text("⚠ Stock finished, try later")
        return

    db.cur.execute("UPDATE rdps SET assigned=1 WHERE id=?", (rdp[0],))
    db.cur.execute("UPDATE users SET points=points-? WHERE user_id=?", (POINTS_REQUIRED, uid))
    db.conn.commit()

    await update.message.reply_text(f"🎉 Your RDP:\n{rdp[1]}")

# ---------- UPLOAD RDP ----------

async def uploadrdp(update, context):
    if update.effective_user.id != OWNER_ID:
        return

    rdp = " ".join(context.args)
    db.cur.execute("INSERT INTO rdps (rdp) VALUES (?)", (rdp,))
    db.conn.commit()

    await update.message.reply_text("✅ RDP Added")

# ---------- STATS ----------

async def stats(update, context):
    db.cur.execute("SELECT COUNT(*) FROM users")
    u = db.cur.fetchone()[0]
    db.cur.execute("SELECT COUNT(*) FROM rdps WHERE assigned=0")
    s = db.cur.fetchone()[0]

    await update.message.reply_text(
        f"👤 Users: {u}\n📦 Stock: {s}"
    )

# ---------- HANDLERS ----------

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("uploadrdp", uploadrdp))
app.add_handler(MessageHandler(filters.Regex("🎯 Refer"), refer))
app.add_handler(MessageHandler(filters.Regex("📦 Stock"), stock))
app.add_handler(MessageHandler(filters.Regex("🎁 Redeem"), redeem))
app.add_handler(MessageHandler(filters.Regex("📊 Stats"), stats))

print("Bot Started")
app.run_polling()
