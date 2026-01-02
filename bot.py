import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    CommandHandler, MessageHandler, filters
)

import config
import database as db

logging.basicConfig(level=logging.INFO)

# ---------- FORCE JOIN CHECK ----------
async def force_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot = context.bot

    try:
        await bot.get_chat_member(config.PUBLIC_CHANNELS[0], user_id)
        await bot.get_chat_member(config.PUBLIC_CHANNELS[1], user_id)
        return True
    except:
        keyboard = [
            [InlineKeyboardButton("🔒 Join Private Channel", url=config.PRIVATE_CHANNEL_INVITE)],
            [InlineKeyboardButton("📢 Public Channel 1", url=f"https://t.me/{config.PUBLIC_CHANNELS[0][1:]}")],
            [InlineKeyboardButton("📢 Public Channel 2", url=f"https://t.me/{config.PUBLIC_CHANNELS[1][1:]}")]
        ]
        await update.message.reply_text(
            "❌ Pehle saare channels join karo",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return False

# ---------- START / AUTO ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await force_join(update, context):
        return

    user_id = update.effective_user.id
    ref = context.args[0] if context.args else None

    db.cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not db.cur.fetchone():
        db.cur.execute("INSERT INTO users (user_id, ref_by) VALUES (?,?)", (user_id, ref))
        if ref:
            db.cur.execute("UPDATE users SET points = points + 1 WHERE user_id=?", (ref,))
        db.conn.commit()

        for admin in config.ADMIN_IDS:
            await context.bot.send_message(admin, f"🆕 New User Joined: `{user_id}`")

    link = f"https://t.me/{context.bot.username}?start={user_id}"
    await update.message.reply_text(
        f"👋 Welcome\n\n"
        f"🎯 Refer 8 users & get RDP\n"
        f"🔗 Your referral link:\n{link}"
    )

# ---------- UPLOAD RDP ----------
async def upload_rdp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return

    rdp = " ".join(context.args)
    if not rdp:
        await update.message.reply_text("Usage: /uploadrdp user:pass|ip")
        return

    db.cur.execute("INSERT INTO rdp_stock (rdp) VALUES (?)", (rdp,))
    db.conn.commit()
    await update.message.reply_text("✅ RDP added to stock")

# ---------- CHECK POINTS ----------
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    db.cur.execute("SELECT points, redeemed FROM users WHERE user_id=?", (user_id,))
    row = db.cur.fetchone()

    if not row or row[0] < config.REF_POINTS_REQUIRED:
        await update.message.reply_text("❌ 8 referrals required")
        return

    if row[1]:
        await update.message.reply_text("❌ Already redeemed")
        return

    db.cur.execute("SELECT id, rdp FROM rdp_stock WHERE used=0 LIMIT 1")
    rdp = db.cur.fetchone()

    if not rdp:
        await update.message.reply_text("❌ Stock empty, try later")
        return

    db.cur.execute("UPDATE rdp_stock SET used=1 WHERE id=?", (rdp[0],))
    db.cur.execute("UPDATE users SET redeemed=1 WHERE user_id=?", (user_id,))
    db.conn.commit()

    await update.message.reply_text(f"🎉 Your RDP:\n`{rdp[1]}`")

# ---------- STOCK ----------
async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.cur.execute("SELECT COUNT(*) FROM rdp_stock WHERE used=0")
    count = db.cur.fetchone()[0]
    await update.message.reply_text(f"📦 Available RDP: {count}")

# ---------- BROADCAST ----------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in config.ADMIN_IDS:
        return

    msg = " ".join(context.args)
    db.cur.execute("SELECT user_id FROM users")
    for u in db.cur.fetchall():
        try:
            await context.bot.send_message(u[0], msg)
        except:
            pass

    await update.message.reply_text("✅ Broadcast sent")

# ---------- MAIN ----------
def main():
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("uploadrdp", upload_rdp))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("stock", stock))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.run_polling()

if __name__ == "__main__":
    main()
