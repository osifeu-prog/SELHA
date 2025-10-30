import os
import logging
import asyncio
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
from fastapi import FastAPI, Request
import uvicorn

# הגדרת לוגר
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_required_env(var_name):
    """קבלת משתנה סביבה נדרש עם הודעת שגיאה ברורה"""
    value = os.getenv(var_name)
    if not value:
        logger.error(f"❌ Missing required environment variable: {var_name}")
        raise ValueError(f"{var_name} is required. Please set it in Railway environment variables.")
    return value

def get_optional_env(var_name, default=None):
    """קבלת משתנה סביבה אופציונלי"""
    return os.getenv(var_name, default)

try:
    # משתני סביבה נדרשים
    TELEGRAM_BOT_TOKEN = get_required_env("TELEGRAM_BOT_TOKEN")
    SLH_API_BASE = get_required_env("SLH_API_BASE")
    PUBLIC_BOT_BASE = get_required_env("PUBLIC_BOT_BASE")
    
    # משתני סביבה אופציונליים
    ADMIN_TOKEN = get_optional_env("ADMIN_TOKEN")
    ADMIN_CHAT_ID = int(get_optional_env("ADMIN_CHAT_ID", "0"))
    PORT = int(get_optional_env("PORT", "8080"))
    
    # וידוא ש-PUBLIC_BOT_BASE הוא HTTPS
    if not PUBLIC_BOT_BASE.startswith("https://"):
        logger.warning("⚠️ PUBLIC_BOT_BASE should be HTTPS for production")
    
    logger.info("✅ All environment variables loaded successfully")
    
except ValueError as e:
    logger.error(f"❌ Configuration error: {e}")
    TELEGRAM_BOT_TOKEN = None
    SLH_API_BASE = None
    PUBLIC_BOT_BASE = None
    ADMIN_TOKEN = None
    ADMIN_CHAT_ID = 0
    PORT = 8080

# קליינט HTTP
client = httpx.AsyncClient(timeout=30.0)

headers = {"X-Admin-Token": ADMIN_TOKEN} if ADMIN_TOKEN else {}

# יצירת אפליקציית FastAPI
app = FastAPI(title="SLH Bot Webhook")

class SLHBot:
    def __init__(self):
        self.application = None
        self.is_configured = all([TELEGRAM_BOT_TOKEN, SLH_API_BASE, PUBLIC_BOT_BASE])

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /start"""
        if not self.is_configured:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        user = update.effective_user
        chat_id = update.effective_chat.id
        
        try:
            # קבלת מחיר עדכני מה-API
            price_response = await client.get(f"{SLH_API_BASE}/config/price")
            price_data = price_response.json()
            sela_price = price_data.get("sela_price_nis", 4.0)
            
            welcome_text = f"""
👋 שלום {user.first_name}!

ברוך הבא לקהילת SELA - המערכת הקהילתית למסחר SELA!

💎 **מחיר SELA נוכחי:** {sela_price} ₪

🤖 **מה אני יכול לעשות:**
• `/price` - הצגת מחיר SELA עדכני
• `/wallet <address>` - הצגת יתרת SELA בארנק שלך
• `/unlock39` - הצטרפות לקהילה (39₪)
• `/status` - סטטוס הנוכחי

🔗 **לאחר Unlock** תקבל גישה ל:
• קישור לקבוצת הקהילה
• אפשרויות שליחה וקבלה של SELA
• עדכונים שוטפים

הקלד /help לקבלת רשימת פקודות מלאה.
            """
            
            await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
            logger.info(f"✅ Sent welcome message to user {user.id}")
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("⚠️ שגיאה בהתחברות למערכת. נסה שוב מאוחר יותר.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /help"""
        help_text = """
📋 **רשימת פקודות:**

**לכל המשתמשים:**
• `/start` - התחל עבודה עם הבוט
• `/price` - הצג מחיר SELA נוכחי
• `/wallet <address>` - הצג יתרת SELA בארנק
• `/unlock39` - הוראות הצטרפות לקהילה
• `/status` - בדיקת סטטוס

**למשתמשים מאושרים:**
• `/join` - קבל קישור לקבוצת הקהילה

**למנהלים:**
• `/approve <chat_id>` - אשר משתמש
• `/set_price <price>` - שנה מחיר SELA

📝 **דוגמאות:**
`/wallet 0x742EfA6c6D2876E8700c5A0e2b0e2e1C5c3A1B2f`
`/unlock39`
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /price"""
        if not self.is_configured:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        try:
            response = await client.get(f"{SLH_API_BASE}/config/price")
            price_data = response.json()
            sela_price = price_data.get("sela_price_nis", 4.0)
            
            price_text = f"""
💎 **מחיר SELA נוכחי:**

💰 **{sela_price} ₪** לשקל

המחיר מתעדכן באופן שוטף לפי תנאי השוק.
            """
            
            await update.message.reply_text(price_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error getting price: {e}")
            await update.message.reply_text("⚠️ לא ניתן לקבל מחיר עדכני כרגע. נסה שוב מאוחר יותר.")

    # ... (כל שאר הפקודות נשארות כמו בקוד הקודם)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """טיפול בשגיאות"""
        logger.error(f"Exception while handling an update: {context.error}")
        
        try:
            if update and update.effective_chat:
                await update.effective_chat.send_message(
                    "❌ אירעה שגיאה בבוט. אנא נסה שוב מאוחר יותר."
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

    def setup_handlers(self):
        """הגדרת handlers"""
        # handlers בסיסיים
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("price", self.price_command))
        self.application.add_handler(CommandHandler("wallet", self.wallet_command))
        self.application.add_handler(CommandHandler("unlock39", self.unlock39_command))
        self.application.add_handler(CommandHandler("unlock_verify", self.unlock_verify_command))
        self.application.add_handler(CommandHandler("join", self.join_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # handlers מנהלים
        self.application.add_handler(CommandHandler("approve", self.approve_command))
        self.application.add_handler(CommandHandler("set_price", self.set_price_command))
        
        # handler שגיאות
        self.application.add_error_handler(self.error_handler)

    async def setup_webhook(self):
        """הגדרת webhook"""
        if not self.is_configured:
            logger.error("❌ Cannot setup webhook - bot not configured")
            return
            
        try:
            # שינוי חשוב: webhook endpoint צריך להיות / (root) ולא /webhook
            webhook_url = f"{PUBLIC_BOT_BASE}/"
            await self.application.bot.set_webhook(webhook_url)
            logger.info(f"✅ Webhook set to: {webhook_url}")
        except Exception as e:
            logger.error(f"❌ Error setting webhook: {e}")

    async def initialize(self):
        """אתחול הבוט"""
        if not self.is_configured:
            logger.error("❌ Bot not configured - missing required environment variables")
            return False
            
        try:
            self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            self.setup_handlers()
            await self.setup_webhook()
            logger.info("✅ Bot initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error initializing bot: {e}")
            return False

# יצירת instance גלובלי של הבוט
bot_instance = SLHBot()

@app.post("/")
async def webhook(request: Request):
    """Endpoint לקבלת עדכונים מטלגרם - שינוי ל-/"""
    try:
        json_data = await request.json()
        logger.info(f"📨 Received webhook update: {json_data}")
        update = Update.de_json(json_data, bot_instance.application.bot)
        await bot_instance.application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error in webhook: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "SLH Bot",
        "configured": bot_instance.is_configured
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SLH Bot is running",
        "webhook_url": f"{PUBLIC_BOT_BASE}/",
        "configured": bot_instance.is_configured,
        "status": "ready"
    }

async def main():
    """פונקציה ראשית"""
    success = await bot_instance.initialize()
    if not success:
        logger.error("❌ Failed to initialize bot. Check environment variables.")
        return
    
    # הרצת שרת FastAPI
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=PORT,
        log_level="info"
    )
    server = uvicorn.Server(config)
    logger.info(f"✅ Starting webhook server on port {PORT}")
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
