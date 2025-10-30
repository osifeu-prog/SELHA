import os
import logging
import asyncio
import httpx
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    KeyboardButton,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    ContextTypes, 
    MessageHandler, 
    filters
)
from telegram.constants import ParseMode
from fastapi import FastAPI, Request
import uvicorn
import time

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

    def get_main_keyboard(self):
        """יצירת Keyboard ראשי"""
        return ReplyKeyboardMarkup([
            [KeyboardButton("💎 מחיר"), KeyboardButton("👛 ארנק")],
            [KeyboardButton("🔓 הצטרפות"), KeyboardButton("📊 סטטוס")],
            [KeyboardButton("❓ תמיכה"), KeyboardButton("🎯 הדרכה")]
        ], resize_keyboard=True)

    def get_admin_keyboard(self):
        """יצירת Keyboard למנהלים"""
        return ReplyKeyboardMarkup([
            [KeyboardButton("📊 סטטוס"), KeyboardButton("⏳ ממתינים")],
            [KeyboardButton("💎 מחיר"), KeyboardButton("⚙️ קונפיג")],
            [KeyboardButton("🏠 תפריט ראשי")]
        ], resize_keyboard=True)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /start משודרגת"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        user = update.effective_user
        
        try:
            # קבלת מחיר עדכני מה-API
            price_response = await client.get(f"{SLH_API_BASE}/config/price")
            price_data = price_response.json()
            sela_price = price_data.get("price_nis", 444.0)  # שינוי מ� sela_price_nis ל-price_nis
            
            welcome_text = f"""
🎉 **ברוך הבא לקהילת SELA!** 🎉

🤝 **קהילת העסקים והמסחר המתקדמת בישראל**

💎 **מחיר SELA נוכחי:** {sela_price} ₪

**🚀 ההטבות שמחכות לך לאחר ההצטרפות:**

✅ **גישה לקהילת עסקים אקסקלוסיבית**
✅ **פלטפורמת מסחר למכירת SELA במחיר אישי**
✅ **ניהול תיק השקעות מתקדם**
✅ **עדכונים שוטפים והזדמנויות עסקיות**
✅ **תמיכה טכנית מלאה**

**📱 בחר פעולה מהתפריט:**
            """
            
            await update.message.reply_text(
                welcome_text, 
                reply_markup=self.get_main_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"✅ Sent welcome message to user {user.id}")
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text(
                "⚠️ שגיאה בהתחברות למערכת. נסה שוב מאוחר יותר.",
                reply_markup=self.get_main_keyboard()
            )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /help משודרגת"""
        help_text = """
🎯 **הדרכה לשימוש בבוט**

**פקודות עיקריות:**
• `💎 מחיר` - הצג מחיר SELA נוכחי
• `👛 ארנק` - הצג יתרת SELA בארנק
• `🔓 הצטרפות` - הוראות הצטרפות לקהילה
• `📊 סטטוס` - בדיקת סטטוס המערכת

**לאחר Unlock:**
• `/join` - קבל קישור לקבוצת הקהילה
• `/send` - שליחת SELA לאחרים
• `/receive` - קבלת SELA

**דוגמאות:**
`/wallet 0x742EfA6c6D2876E8700c5A0e2b0e2e1C5c3A1B2f`
`/unlock_verify TX123456789`

**תמיכה:**
לחץ '❓ תמיכה' לעזרה נוספת
        """
        await update.message.reply_text(
            help_text, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_main_keyboard()
        )

    async def price_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /price"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        try:
            response = await client.get(f"{SLH_API_BASE}/config/price")
            price_data = response.json()
            sela_price = price_data.get("price_nis", 444.0)  # שינוי מ� sela_price_nis ל-price_nis
            
            price_text = f"""
💎 **מחיר SELA נוכחי:**

💰 **{sela_price} ₪** לשקל

המחיר מתעדכן באופן שוטף לפי תנאי השוק.
            """
            
            await update.message.reply_text(
                price_text, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_main_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error getting price: {e}")
            await update.message.reply_text(
                "⚠️ לא ניתן לקבל מחיר עדכני כרגע. נסה שוב מאוחר יותר.",
                reply_markup=self.get_main_keyboard()
            )

    async def wallet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /wallet"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        if not context.args:
            await update.message.reply_text(
                "👛 **רישום ארנק**\n\nשלח את כתובת ה-MetaMask או Trust Wallet שלך בפורמט:\n\n`/wallet 0x742EfA6c6D2876E8700c5A0e2b0e2e1C5c3A1B2f`\n\nאו לחץ על '👛 ארנק' והזן את הכתובת.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_main_keyboard()
            )
            return
        
        wallet_address = context.args[0]
        
        try:
            response = await client.get(f"{SLH_API_BASE}/token/balance/{wallet_address}")
            balance_data = response.json()
            
            if "error" in balance_data:
                await update.message.reply_text(
                    f"❌ שגיאה: {balance_data['error']}",
                    reply_markup=self.get_main_keyboard()
                )
                return
            
            balance = balance_data.get("balance_sela", 0)  # שינוי מ-balance ל-balance_sela
            symbol = "SELA"
            
            # קבלת מחיר נוכחי
            price_response = await client.get(f"{SLH_API_BASE}/config/price")
            price_data = price_response.json()
            sela_price = price_data.get("price_nis", 444.0)
            
            # חישוב ערך בשקלים
            value_nis = balance * sela_price
            
            balance_text = f"""
👛 **יתרת {symbol}**

📍 **כתובת:** `{wallet_address}`
💎 **יתרה:** {balance:,.2f} {symbol}
💰 **ערך נוכחי:** {value_nis:,.2f} ₪

💡 *מחיר {symbol}: {sela_price} ₪*
            """
            
            await update.message.reply_text(
                balance_text, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_main_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            await update.message.reply_text(
                "⚠️ שגיאה בקבלת יתרת הארנק. ודא שהכתובת תקינה ונסה שוב.",
                reply_markup=self.get_main_keyboard()
            )

    async def unlock39_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /unlock39 משודרגת"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        chat_id = update.effective_chat.id
        
        try:
            # קבלת קונפיג מה-API
            config_response = await client.get(f"{SLH_API_BASE}/config")
            config = config_response.json()
            
            min_nis = config.get("min_nis_to_unlock", 39)
            bank_accounts = config.get("bank_accounts", [])
            
            # בדיקת סטטוס Unlock
            status_response = await client.get(f"{SLH_API_BASE}/unlock/status/{chat_id}")
            status = status_response.json()
            
            if status.get("unlocked"):
                # כבר מאושר - שליחת קישור קבוצה
                telegram_group = config.get("telegram_group", "")
                if telegram_group:
                    await update.message.reply_text(
                        f"✅ אתה כבר מאושר! הצטרף לקבוצה כאן: {telegram_group}",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=self.get_main_keyboard()
                    )
                else:
                    await update.message.reply_text(
                        "✅ אתה כבר מאושר! קישור הקבוצה יישלח בהמשך.",
                        reply_markup=self.get_main_keyboard()
                    )
                return
            
            # הוראות תשלום משודרגות
            payment_text = f"""
🔓 **הצטרפות לקהילת SELA - צעד אחר צעד** 🔓

**💰 השקעה:** {min_nis} ₪ בלבד

**📋 שלבי ההצטרפות:**

1️⃣ **העברת תשלום**
   העבר {min_nis} ₪ לחשבון:
"""
            
            if bank_accounts:
                for account in bank_accounts:
                    bank = account.get("bank", "פועלים")
                    branch = account.get("branch", "153")
                    account_num = account.get("account", "73462")
                    name = account.get("name", "קאופמן צביקה")
                    
                    payment_text += f"""
   🏦 **בנק:** {bank}
   🏢 **סניף:** {branch}
   📊 **חשבון:** {account_num}
   👤 **שם:** {name}
"""
            else:
                payment_text += """
   🏦 **בנק:** פועלים
   🏢 **סניף:** 153
   📊 **חשבון:** 73462
   👤 **שם:** קאופמן צביקה
"""
            
            payment_text += f"""

2️⃣ **רישום הארנק שלך**
   שלח את כתובת ה-MetaMask/Trust Wallet שלך:
   👉 `/wallet <your_wallet_address>`

3️⃣ **אישור התשלום**
   שלח תמונה של אישור ההעברה או מספר עסקה:
   👉 `/unlock_verify <transaction_reference>`

**🎁 מה תקבל לאחר האישור:**
✨ קישור לקבוצת הטלגרם האקסקלוסיבית
✨ גישה לפלטפורמת המסחר המלאה
✨ אפשרות למכור SELA במחיר אישי
✨ קהילת עסקים תומכת ופעילה

**❓ נתקלת בבעיה?**
לחץ '❓ תמיכה' לקבלת עזרה מיידית!
"""
            
            await update.message.reply_text(
                payment_text, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_main_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error in unlock39 command: {e}")
            await update.message.reply_text(
                "⚠️ שגיאה בהצגת הוראות התשלום. נסה שוב מאוחר יותר.",
                reply_markup=self.get_main_keyboard()
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """טיפול בהודעות טקסט מהכפתורים"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        text = update.message.text
        
        if text == "💎 מחיר":
            await self.price_command(update, context)
        elif text == "👛 ארנק":
            await update.message.reply_text(
                "👛 **רישום ארנק**\n\nשלח את כתובת ה-MetaMask או Trust Wallet שלך בפורמט:\n\n`/wallet 0x742EfA6c6D2876E8700c5A0e2b0e2e1C5c3A1B2f`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_main_keyboard()
            )
        elif text == "🔓 הצטרפות":
            await self.unlock39_command(update, context)
        elif text == "📊 סטטוס":
            await self.status_command(update, context)
        elif text == "❓ תמיכה":
            await self.support_command(update, context)
        elif text == "🎯 הדרכה":
            await self.help_command(update, context)
        elif text == "🏠 תפריט ראשי":
            await update.message.reply_text(
                "🏠 **תפריט ראשי**",
                reply_markup=self.get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "🤔 לא מזהה את הפקודה. השתמש בתפריט או הקלד /help לעזרה.",
                reply_markup=self.get_main_keyboard()
            )

    async def support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת תמיכה"""
        support_text = """
❓ **תמיכה ועזרה**

**לשאלות והבהרות:**

📞 **מנהל המערכת:** @OsifUngar

**בעיות טכניות:**
• בעיית חיבור לבוט
• שגיאה בהצגת יתרה
• בעיית אישור תשלום

**נושאים כלליים:**
• הסבר על הקהילה
• הדרכה טכנית
• הצעות לשיפור

**שעות פעילות:** 24/7

נשמח לעזור בכל שאלה! 😊
"""
        await update.message.reply_text(
            support_text, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=self.get_main_keyboard()
        )

    async def unlock_verify_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /unlock_verify"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        if not context.args:
            await update.message.reply_text(
                "❌ אנא ספק מזהה תשלום. דוגמה:\n`/unlock_verify TX123456789`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        payment_ref = context.args[0]
        chat_id = update.effective_chat.id
        
        try:
            # שליחת בקשת אימות ל-API
            verify_data = {
                "chat_id": str(chat_id),
                "reference": payment_ref,
                "wallet_address": "to_be_provided"  # המשתמש צריך לשלוח את הארנק בנפרד
            }
            
            response = await client.post(
                f"{SLH_API_BASE}/unlock/verify",
                json=verify_data,
                headers=headers
            )
            
            result = response.json()
            
            if result.get("status") == "pending":
                await update.message.reply_text(
                    "✅ בקשתך התקבלה וממתינה לאישור. תתעדכן כאשר תאושר.",
                    reply_markup=self.get_main_keyboard()
                )
                
                # הודעה למנהל
                if ADMIN_CHAT_ID:
                    admin_msg = f"🔔 בקשה חדשה לאישור!\nמשתמש: {chat_id}\nמזהה תשלום: {payment_ref}"
                    await context.bot.send_message(ADMIN_CHAT_ID, admin_msg)
                    
            elif result.get("status") == "already_approved":
                await update.message.reply_text(
                    "✅ אתה כבר מאושר! השתמש ב-/join כדי לקבל קישור קבוצה.",
                    reply_markup=self.get_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "⚠️ שגיאה ברישום הבקשה. נסה שוב.",
                    reply_markup=self.get_main_keyboard()
                )
                
        except Exception as e:
            logger.error(f"Error in unlock_verify: {e}")
            await update.message.reply_text(
                "⚠️ שגיאה בשליחת הבקשה. נסה שוב מאוחר יותר.",
                reply_markup=self.get_main_keyboard()
            )

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
            
            if not status.get("unlocked"):
                await update.message.reply_text(
                    "❌ אתה עדיין לא מאושר. השתמש ב-/unlock39 כדי להצטרף.",
                    reply_markup=self.get_main_keyboard()
                )
                return
            
            # קבלת קישור קבוצה
            config_response = await client.get(f"{SLH_API_BASE}/config")
            config = config_response.json()
            
            telegram_group = config.get("telegram_group", "")
            
            if telegram_group:
                await update.message.reply_text(
                    f"🎉 ברוך הבא לקהילה! הצטרף כאן: {telegram_group}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=self.get_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "✅ אתה מאושר! קישור הקבוצה יישלח בהמשך.",
                    reply_markup=self.get_main_keyboard()
                )
                
        except Exception as e:
            logger.error(f"Error in join command: {e}")
            await update.message.reply_text(
                "⚠️ שגיאה בקבלת קישור הקבוצה. נסה שוב מאוחר יותר.",
                reply_markup=self.get_main_keyboard()
            )

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
            
            unlock_status = "🟢 מאושר" if status.get("unlocked") else "🟡 ממתין" if status.get("pending") else "🔴 לא מאושר"
            
            status_text = f"""
📊 **סטטוס מערכת**

🤖 **בוט:** 🟢 פעיל
🔗 **API:** {api_status}
🔓 **סטטוס Unlock:** {unlock_status}

💡 **פרטים:**
• **מזהה צ'אט:** {chat_id}
• **API Base:** {SLH_API_BASE}
            """
            
            await update.message.reply_text(
                status_text, 
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=self.get_main_keyboard()
            )
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text(
                "⚠️ שגיאה בבדיקת סטטוס. ה-API כנראה לא זמין.",
                reply_markup=self.get_main_keyboard()
            )

    async def approve_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """פקודת /approve למנהלים"""
        if not self.initialized:
            await update.message.reply_text("⚠️ הבוט בתהליך אתחול. נסה שוב בעוד כמה דקות.")
            return
            
        if update.effective_chat.id != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ גישה נדחתה - מנהל בלבד.")
            return
        
        if not context.args:
            await update.message.reply_text(
                "❌ אנא ספק מזהה צ'אט. דוגמה: `/approve 123456789`", 
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            chat_id = int(context.args[0])
            
            response = await client.post(
                f"{SLH_API_BASE}/unlock/grant",
                json={"chat_id": str(chat_id)},
                headers=headers
            )
            
            result = response.json()
            
            if result.get("status") == "granted":
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
            await update.message.reply_text(
                "❌ אנא ספק מחיר. דוגמה: `/set_price 444`", 
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        try:
            new_price = float(context.args[0])
            
            response = await client.post(
                f"{SLH_API_BASE}/config/price",
                json={"price_nis": new_price},
                headers=headers
            )
            
            result = response.json()
            
            if result.get("status") == "updated":
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
                    "❌ אירעה שגיאה בבוט. אנא נסה שוב מאוחר יותר.",
                    reply_markup=self.get_main_keyboard()
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
        self.application.add_handler(CommandHandler("support", self.support_command))
        
        # handler להודעות טקסט (כפתורים)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
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
