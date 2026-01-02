from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from config import *
from database import *

users = load_json(USERS_FILE, {})
rdp_stock = load_json(RDP_FILE, {"rdps": []})

# ----------------- HELPERS -----------------

def save_all():
    save_json(USERS_FILE, users)
    save_json(RDP_FILE, rdp_stock)

def is_joined(user_id, bot):
    for ch in FORCE_CHANNELS:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# ----------------- START -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)

    if uid not in users:
        users[uid] = {
            "points": 0,
            "referred": [],
            "redeemed": False
        }

        if context.args:
            ref = context.args[0]
            if ref in users and uid not in users[ref]["referred"]:
                users[ref]["points"] += 1
                users[ref]["referred"].append(uid)

        save_all()

    if not is_joined(user.id, context.bot):
        btn = [
            [InlineKeyboardButton("🔒 Join Private Channel", url=PRIVATE_CHANNEL_INVITE)],
            [InlineKeyboardButton("✅ Verify", callback_data="verify")]
        ]
        await update.message.reply_text(
            "❌ Pehle saare channels join karo",
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return

    await update.message.reply_text(
        f"👋 Welcome {user.first_name}\n\n"
        f"⭐ Points: {users[uid]['points']}\n"
        f"🎁 Required: {POINTS_REQUIRED}"
    )

# ----------------- VERIFY -----------------

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if is_joined(q.from_user.id, context.bot):
        await q.message.edit_text("✅ Verified! Ab bot use karo")
    else:
        await q.message.edit_text("❌ Abhi bhi join nahi kiya")

# ----------------- UPLOAD RDP -----------------

async def uploadrdp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    await update.message.reply_text("📤 RDP details bhejo (text me)")

    context.user_data["uploading"] = True

async def receive_rdp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("uploading"):
        rdp_stock["rdps"].append(update.message.text)
        context.user_data["uploading"] = False
        save_all()
        await update.message.reply_text("✅ RDP Stock me add ho gaya")

# ----------------- REDEEM -----------------

async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)

    if users[uid]["redeemed"]:
        await update.message.reply_text("❌ Already redeemed")
        return

    if users[uid]["points"] < POINTS_REQUIRED:
        await update.message.reply_text("❌ Points insufficient")
        return

    if not rdp_stock["rdps"]:
        await update.message.reply_text("❌ Stock khatam")
        return

    rdp = rdp_stock["rdps"].pop(0)
    users[uid]["redeemed"] = True
    save_all()

    await update.message.reply_text(f"🎉 Your RDP:\n\n{rdp}")

# ----------------- STATS -----------------

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"👥 Users: {len(users)}\n"
        f"🖥 RDP Stock: {len(rdp_stock['rdps'])}"
    )

# ----------------- MAIN -----------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("uploadrdp", uploadrdp))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_rdp))

    app.run_polling()

if __name__ == "__main__":
    main()
