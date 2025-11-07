
import os, sys, asyncio, logging, httpx
from pythonjsonlogger import jsonlogger
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

API_BASE = os.getenv("SLH_API_BASE","").rstrip("/")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN","")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID","0") or 0)
WEBHOOK_URL = os.getenv("WEBHOOK_URL","")
LOG_LEVEL = os.getenv("LOG_LEVEL","INFO").upper()
PORT = int(os.getenv("PORT","8080"))

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
root = logging.getLogger()
root.handlers = [handler]
root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

async def ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text("pong")

async def whoami(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(f"chat_id={update.effective_chat.id}")

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient(timeout=10) as cli:
        price = None
        try:
            r = await cli.get(f"{API_BASE}/config/price")
            price = r.json().get("price_nis")
        except Exception:
            pass
        try:
            s = await cli.get(f"{API_BASE}/unlock/status/{update.effective_chat.id}")
            unlocked = s.json().get("unlocked")
        except Exception:
            unlocked = False
    msg = ["ברוך הבא ל-SLH", f"מחיר נוכחי: {price} ₪" if price else "", f"סטטוס: {'✅ פתוח' if unlocked else '🔒 סגור'}"]
    await update.effective_message.reply_text("\n".join([m for m in msg if m]))

async def run_webhook(application: Application):
    if WEBHOOK_URL:
        me = await application.bot.get_me()
        logging.getLogger(__name__).info(f"Bot username: @{me.username}")
        ok = await application.bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        logging.getLogger(__name__).info(f"set_webhook={ok}")
        await application.run_webhook(listen="0.0.0.0", port=PORT, webhook_url=WEBHOOK_URL, allowed_updates=Update.ALL_TYPES)
    else:
        logging.getLogger(__name__).warning("WEBHOOK_URL missing; running polling fallback")
        await application.delete_webhook(drop_pending_updates=True)
        await application.run_polling(close_loop=False, allowed_updates=Update.ALL_TYPES)

async def main():
    if not BOT_TOKEN or not API_BASE:
        logging.getLogger(__name__).error("Missing TELEGRAM_BOT_TOKEN or SLH_API_BASE in env")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("whoami", whoami))
    application.add_handler(CommandHandler("start", start))
    await run_webhook(application)

if __name__ == "__main__":
    asyncio.run(main())
