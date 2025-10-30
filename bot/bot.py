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
        self.initialized = False

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /start"""
        if not self.initialized:
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
• פלטפורמת מסחר למכירת SELA
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
        if not self.initialized:
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

    async def wallet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /wallet"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        if not context.args:
            await update.message.reply_text("❌ אנא ספק כתובת ארנק. דוגמה:\n`/wallet 0x742EfA6c6D2876E8700c5A0e2b0e2e1C5c3A1B2f`", parse_mode=ParseMode.MARKDOWN)
            return
        
        wallet_address = context.args[0]
        
        try:
            response = await client.get(f"{SLH_API_BASE}/token/balance/{wallet_address}")
            balance_data = response.json()
            
            if "error" in balance_data:
                await update.message.reply_text(f"❌ שגיאה: {balance_data['error']}")
                return
            
            balance = balance_data.get("balance", 0)
            symbol = balance_data.get("symbol", "SELA")
            
            # קבלת מחיר נוכחי
            price_response = await client.get(f"{SLH_API_BASE}/config/price")
            price_data = price_response.json()
            sela_price = price_data.get("sela_price_nis", 4.0)
            
            # חישוב ערך בשקלים
            value_nis = balance * sela_price
            
            balance_text = f"""
👛 **יתרת {symbol}**

📍 **כתובת:** `{wallet_address}`
💎 **יתרה:** {balance:,.2f} {symbol}
💰 **ערך נוכחי:** {value_nis:,.2f} ₪

💡 *מחיר {symbol}: {sela_price} ₪*
            """
            
            await update.message.reply_text(balance_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            await update.message.reply_text("⚠️ שגיאה בקבלת יתרת הארנק. ודא שהכתובת תקינה ונסה שוב.")

    async def unlock39_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /unlock39"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        chat_id = update.effective_chat.id
        
        try:
            # קבלת קונפיג מה-API
            config_response = await client.get(f"{SLH_API_BASE}/config")
            config = config_response.json()
            
            min_nis = config.get("min_nis_to_unlock", 39)
            payment_accounts = config.get("payment_accounts", [])
            
            # בדיקת סטטוס Unlock
            status_response = await client.get(f"{SLH_API_BASE}/unlock/status/{chat_id}")
            status = status_response.json()
            
            if status.get("approved"):
                # כבר מאושר - שליחת קישור קבוצה
                invite_link = config.get("community_invite_link", "")
                if invite_link:
                    await update.message.reply_text(
                        f"✅ אתה כבר מאושר! הצטרף לקבוצה כאן: {invite_link}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await update.message.reply_text("✅ אתה כבר מאושר! קישור הקבוצה יישלח בהמשך.")
                return
            
            if status.get("pending"):
                await update.message.reply_text("⏳ הבקשה שלך ממתינה לאישור. נא להמתין לאישור מנהל.")
                return
            
            # הוראות תשלום
            payment_text = f"""
🔓 **הצטרפות לקהילת SELA**

💰 **עלות:** {min_nis} ₪

**הוראות תשלום:**

1. העבר {min_nis} ₪ לאחד החשבונות הבאים:
"""
            
            if payment_accounts:
                for i, account in enumerate(payment_accounts, 1):
                    acc_type = account.get("type", "חשבון")
                    details = account.get("details", "")
                    payment_text += f"\n{i}. **{acc_type}:** {details}"
            else:
                payment_text += "\n**בנק: פועלים**\n**סניף: 153**\n**חשבון: 73462**\n**שם: קאופמן צביקה**"
            
            payment_text += f"""

2. לאחר התשלום, שלח לנו את פרטי הארנק שלך עם הפקודה:
`/wallet <your_wallet_address>`

3. שלח את מספר העסקה או קבלה עם:
`/unlock_verify <transaction_reference>`

📞 **לשאלות:** פנה למנהל המערכת.

💡 *לאחר אישור התשלום תקבל גישה מלאה לקהילה!*
            """
            
            await update.message.reply_text(payment_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in unlock39 command: {e}")
            await update.message.reply_text("⚠️ שגיאה בהצגת הוראות התשלום. נסה שוב מאוחר יותר.")

    async def unlock_verify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /unlock_verify"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        if not context.args:
            await update.message.reply_text("❌ אנא ספק מזהה תשלום. דוגמה:\n`/unlock_verify TX123456789`")
            return
        
        payment_ref = context.args[0]
        chat_id = update.effective_chat.id
        
        try:
            # שליחת בקשת אימות ל-API
            verify_data = {
                "chat_id": chat_id,
                "wallet_address": "to_be_provided",
                "payment_ref": payment_ref
            }
            
            response = await client.post(
                f"{SLH_API_BASE}/unlock/verify",
                json=verify_data,
                headers=headers
            )
            
            result = response.json()
            
            if result.get("status") == "pending_approval":
                await update.message.reply_text("✅ בקשתך התקבלה וממתינה לאישור. תתעדכן כאשר תאושר.")
                
                # הודעה למנהל
                if ADMIN_CHAT_ID:
                    admin_msg = f"🔔 בקשה חדשה לאישור!\nמשתמש: {chat_id}\nמזהה תשלום: {payment_ref}"
                    await context.bot.send_message(ADMIN_CHAT_ID, admin_msg)
                    
            elif result.get("status") == "already_approved":
                await update.message.reply_text("✅ אתה כבר מאושר! השתמש ב-/join כדי לקבל קישור קבוצה.")
            elif result.get("status") == "already_pending":
                await update.message.reply_text("⏳ כבר יש לך בקשה ממתינה לאישור.")
            else:
                await update.message.reply_text("⚠️ שגיאה ברישום הבקשה. נסה שוב.")
                
        except Exception as e:
            logger.error(f"Error in unlock_verify: {e}")
            await update.message.reply_text("⚠️ שגיאה בשליחת הבקשה. נסה שוב מאוחר יותר.")

    async def join_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /join"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        chat_id = update.effective_chat.id
        
        try:
            # בדיקת סטטוס
            status_response = await client.get(f"{SLH_API_BASE}/unlock/status/{chat_id}")
            status = status_response.json()
            
            if not status.get("approved"):
                await update.message.reply_text("❌ אתה עדיין לא מאושר. השתמש ב-/unlock39 כדי להצטרף.")
                return
            
            # קבלת קישור קבוצה
            config_response = await client.get(f"{SLH_API_BASE}/config")
            config = config_response.json()
            
            invite_link = config.get("community_invite_link", "")
            
            if invite_link:
                await update.message.reply_text(
                    f"🎉 ברוך הבא לקהילה! הצטרף כאן: {invite_link}",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await update.message.reply_text("✅ אתה מאושר! קישור הקבוצה יישלח בהמשך.")
                
        except Exception as e:
            logger.error(f"Error in join command: {e}")
            await update.message.reply_text("⚠️ שגיאה בקבלת קישור הקבוצה. נסה שוב מאוחר יותר.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /status"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        chat_id = update.effective_chat.id
        
        try:
            # בדיקת סטטוס API
            health_response = await client.get(f"{SLH_API_BASE}/healthz")
            api_status = "🟢 פעיל" if health_response.status_code == 200 else "🔴 לא פעיל"
            
            # בדיקת סטטוס Unlock
            status_response = await client.get(f"{SLH_API_BASE}/unlock/status/{chat_id}")
            status = status_response.json()
            
            unlock_status = "🟢 מאושר" if status.get("approved") else "🟡 ממתין" if status.get("pending") else "🔴 לא מאושר"
            
            status_text = f"""
📊 **סטטוס מערכת**

🤖 **בוט:** 🟢 פעיל
🔗 **API:** {api_status}
🔓 **סטטוס Unlock:** {unlock_status}

💡 **פרטים:**
• **מזהה צ'אט:** {chat_id}
• **API Base:** {SLH_API_BASE}
            """
            
            await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text("⚠️ שגיאה בבדיקת סטטוס. ה-API כנראה לא זמין.")

    async def approve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /approve למנהלים"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        if update.effective_chat.id != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ גישה נדחתה - מנהל בלבד.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ אנא ספק מזהה צ'אט. דוגמה: `/approve 123456789`", parse_mode=ParseMode.MARKDOWN)
            return
        
        try:
            chat_id = int(context.args[0])
            
            response = await client.post(
                f"{SLH_API_BASE}/unlock/grant",
                params={"chat_id": chat_id},
                headers=headers
            )
            
            result = response.json()
            
            if result.get("status") == "approved":
                await update.message.reply_text(f"✅ משתמש {chat_id} אושר בהצלחה!")
                
                # הודעה למשתמש
                try:
                    await context.bot.send_message(
                        chat_id, 
                        "🎉 **הבקשה שלך אושרה!**\n\nכעת אתה חבר בקהילת SELA. השתמש ב-/join כדי לקבל קישור לקבוצה.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Could not notify user {chat_id}: {e}")
                    
            else:
                await update.message.reply_text("❌ שגיאה באישור המשתמש.")
                
        except Exception as e:
            logger.error(f"Error in approve command: {e}")
            await update.message.reply_text("⚠️ שגיאה באישור המשתמש.")

    async def set_price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /set_price למנהלים"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        if update.effective_chat.id != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ גישה נדחתה - מנהל בלבד.")
            return
        
        if not context.args:
            await update.message.reply_text("❌ אנא ספק מחיר. דוגמה: `/set_price 4.5`", parse_mode=ParseMode.MARKDOWN)
            return
        
        try:
            new_price = float(context.args[0])
            
            response = await client.post(
                f"{SLH_API_BASE}/config/price",
                json={"sela_price_nis": new_price},
                headers=headers
            )
            
            result = response.json()
            
            if result.get("status") == "price_updated":
                await update.message.reply_text(f"✅ מחיר SELA עודכן ל-{new_price} ₪")
            else:
                await update.message.reply_text("❌ שגיאה בעדכון המחיר.")
                
        except Exception as e:
            logger.error(f"Error in set_price command: {e}")
            await update.message.reply_text("⚠️ שגיאה בעדכון המחיר.")

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
            webhook_url = f"{PUBLIC_BOT_BASE}/webhook"
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
            
            # אתחול האפליקציה - זה מה שהיה חסר!
            await self.application.initialize()
            
            await self.setup_webhook()
            self.initialized = True
            logger.info("✅ Bot initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Error initializing bot: {e}")
            return False

# יצירת instance גלובלי של הבוט
bot_instance = SLHBot()

@app.post("/webhook")
async def webhook(request: Request):
    """Endpoint לקבלת עדכונים מטלגרם"""
    if not bot_instance.initialized:
        logger.error("❌ Bot not initialized yet")
        return {"status": "error", "message": "Bot not initialized"}
    
    try:
        json_data = await request.json()
        logger.info(f"📨 Received webhook update for chat: {json_data.get('message', {}).get('chat', {}).get('id')}")
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
        "configured": bot_instance.is_configured,
        "initialized": bot_instance.initialized
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SLH Bot is running",
        "webhook_url": f"{PUBLIC_BOT_BASE}/webhook",
        "configured": bot_instance.is_configured,
        "initialized": bot_instance.initialized,
        "status": "ready" if bot_instance.initialized else "initializing"
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
