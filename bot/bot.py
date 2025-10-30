import os
import logging
import asyncio
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode
import json

# הגדרת לוגר
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# משתני סביבה
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SLH_API_BASE = os.getenv("SLH_API_BASE")
PUBLIC_BOT_BASE = os.getenv("PUBLIC_BOT_BASE")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# וידוא משתנים חיוניים
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is required")
if not SLH_API_BASE:
    raise ValueError("SLH_API_BASE is required")
if not PUBLIC_BOT_BASE:
    raise ValueError("PUBLIC_BOT_BASE is required")
if not PUBLIC_BOT_BASE.startswith("https://"):
    raise RuntimeError("PUBLIC_BOT_BASE must be https://... (Telegram מחייב https)")

# קליינט HTTP
client = httpx.AsyncClient(timeout=30.0)

headers = {"X-Admin-Token": ADMIN_TOKEN} if ADMIN_TOKEN else {}

class SLHBot:
    def __init__(self):
        self.application = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /start"""
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
• `/set_min <amount>` - שנה סכום Unlock מינימלי
• `/set_group <link>` - הגדר קישור קבוצה
• `/add_account <type> <details>` - הוסף חשבון תשלום

📝 **דוגמאות:**
`/wallet 0x742EfA6c6D2876E8700c5A0e2b0e2e1C5c3A1B2f`
`/unlock39`
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /price"""
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
            
            # קבלת מחיר נוכחי
            price_response = await client.get(f"{SLH_API_BASE}/config/price")
            price_data = price_response.json()
            sela_price = price_data.get("sela_price_nis", 4.0)
            
            # חישוב ערך בשקלים
            value_nis = balance * sela_price
            
            balance_text = f"""
👛 **יתרת SELA**

📍 **כתובת:** `{wallet_address}`
💎 **יתרה:** {balance:,.2f} SELA
💰 **ערך נוכחי:** {value_nis:,.2f} ₪

💡 *מחיר SELA: {sela_price} ₪*
            """
            
            await update.message.reply_text(balance_text, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            await update.message.reply_text("⚠️ שגיאה בקבלת יתרת הארנק. ודא שהכתובת תקינה ונסה שוב.")

    async def unlock39_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /unlock39"""
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
            
            for i, account in enumerate(payment_accounts, 1):
                acc_type = account.get("type", "חשבון")
                details = account.get("details", "")
                payment_text += f"\n{i}. **{acc_type}:** {details}"
            
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
        if not context.args:
            await update.message.reply_text("❌ אנא ספק מזהה תשלום. דוגמה:\n`/unlock_verify TX123456789`")
            return
        
        payment_ref = context.args[0]
        chat_id = update.effective_chat.id
        
        try:
            # שליחת בקשת אימות ל-API
            verify_data = {
                "chat_id": chat_id,
                "wallet_address": "to_be_provided",  # המשתמש צריך להזין כתובת קודם
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

    # פקודות מנהל
    async def approve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /approve למנהלים"""
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
        webhook_url = f"{PUBLIC_BOT_BASE}/tg"
        await self.application.bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")

    async def run(self):
        """הרצת הבוט"""
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        self.setup_handlers()
        await self.setup_webhook()
        
        # הרצת הבוט
        logger.info("Bot is starting...")
        await self.application.run_polling()

async def main():
    """פונקציה ראשית"""
    bot = SLHBot()
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
