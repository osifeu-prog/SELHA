import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import httpx
from datetime import datetime

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL", "https://slhapi-production.up.railway.app")
GROUP_LINK = "https://t.me/+HIzvM8sEgh1kNWY0"

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SelaBot:
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
        self.user_states = {}

    def setup_handlers(self):
        """Setup command handlers"""
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("wallet", self.wallet))
        self.application.add_handler(CommandHandler("price", self.price))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("group", self.group))
        
        # Trading commands
        self.application.add_handler(CommandHandler("buy", self.buy))
        self.application.add_handler(CommandHandler("sell", self.sell))
        self.application.add_handler(CommandHandler("orderbook", self.orderbook))
        self.application.add_handler(CommandHandler("orders", self.orders))
        self.application.add_handler(CommandHandler("cancel", self.cancel))
        self.application.add_handler(CommandHandler("trades", self.trades))
        
        # Wallet management commands
        self.application.add_handler(CommandHandler("mywallet", self.my_wallet))
        self.application.add_handler(CommandHandler("register", self.register_wallet))
        self.application.add_handler(CommandHandler("send", self.send_tokens))
        self.application.add_handler(CommandHandler("receive", self.receive_tokens))
        self.application.add_handler(CommandHandler("staking", self.staking))
        self.application.add_handler(CommandHandler("transfer", self.transfer))
        
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        user = update.effective_user
        logger.info(f"👤 User {user.id} started the bot")
        
        keyboard = [
            [InlineKeyboardButton("👛 בדיקת ארנק", callback_data="check_wallet")],
            [InlineKeyboardButton("📈 מחיר SELA", callback_data="check_price")],
            [InlineKeyboardButton("⚡ סטטוס מערכת", callback_data="check_status")],
            [InlineKeyboardButton("🔄 מסחר", callback_data="trading_menu")],
            [InlineKeyboardButton("📤 העברות", callback_data="transfer_menu")],
            [InlineKeyboardButton("👥 הצטרף לקהילה", callback_data="join_group")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = f"""
🚀 **ברוך הבא {user.first_name} לבורסת SELA!**

הבורסה העברית הראשונה למסחר במטבע SELA על רשת **BSC**!

**🌐 רשת:** BSC (Binance Smart Chain)
**🔗 Chain ID:** 56
**⛽ גז:** BNB בלבד

**🎯 מה אפשר לעשות:**
• 👛 **בדיקת ארנק** - צפייה ביתרות BNB ו-SELA אמיתיות מהבלוקצ'יין
• 📈 **מחירים** - מחיר SELA מעודכן בזמן אמת
• 🔄 **מסחר** - קניה ומכירה של SELA
• 📤 **העברות** - שליחת SELA ו-BNB
• 🏦 **Staking** - ריבית של 15% APY
• 👥 **קהילה** - תמיכה ועדכונים

**📋 פקודות מהירות:**
/wallet <כתובת> - בדיקת יתרות אמיתיות
/price - מחיר SELA
/status - סטטוס מערכת
/buy - קניית SELA
/sell - מכירת SELA

**👉 השתמש בכפתורים למטה להתחלה מהירה!**
        """
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Wallet balance check - FIXED FOR BSC ONLY"""
        if context.args:
            wallet_address = context.args[0]
            await self.show_wallet_balance(update, wallet_address)
        else:
            keyboard = [
                [InlineKeyboardButton("💰 בדיקת ארנק", callback_data="enter_wallet")],
                [InlineKeyboardButton("📝 רישום ארנק", callback_data="register_wallet")],
                [InlineKeyboardButton("📤 שלח SELA", callback_data="send_sela"),
                 InlineKeyboardButton("📤 שלח BNB", callback_data="send_bnb")],
                [InlineKeyboardButton("📥 קבל", callback_data="receive_tokens")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            help_text = """
👛 **ניהול ארנקים - BSC**

**🌐 רשת:** BSC (Binance Smart Chain)
**🔗 Chain ID:** 56
**⛽ גז:** BNB בלבד

**💎 נתונים אמיתיים מהבלוקצ'יין!**

**אפשרויות:**
• **💰 בדיקת ארנק** - בדיקת יתרות אמיתיות מכתובת BSC
• **📝 רישום ארנק** - רישום ארנק חדש במערכת  
• **📤 שלח** - שליחת SELA או BNB
• **📥 קבל** - קבלת tokens לכתובת שלך

**שימוש מהיר:**
`/wallet 0xD0617B54FB4b6b66307846f217b4D685800E3dA4`

**🎯 מטבעות נתמכים:**
• 🪙 BNB - למסחר ועמלות רשת
• 🎯 SELA - מטבע הפרויקט שלנו (SLH)
"""
            await update.message.reply_text(
                help_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    async def show_wallet_balance(self, update: Update, wallet_address: str):
        """Show wallet balance - FIXED FOR BSC ONLY"""
        try:
            loading_text = "🔄 מתחבר לבלוקצ'יין BSC... זה יכול לקחת כמה שניות"
            if hasattr(update, 'message'):
                loading_msg = await update.message.reply_text(loading_text)
            else:
                await update.edit_message_text(loading_text)
                loading_msg = None
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                logger.info(f"🔍 Fetching blockchain data for: {wallet_address}")
                response = await client.get(f"{API_BASE_URL}/wallet/balance/{wallet_address}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # FIXED: Proper address display
                    display_address = f"{wallet_address[:8]}...{wallet_address[-6:]}"
                    
                    message = f"""
👛 **ארנק SELA - BSC**

🌐 **רשת:** {data.get('network', 'BSC (Binance Smart Chain)')}
📧 **כתובת:** `{display_address}`

💰 **יתרות אמיתיות מהבלוקצ'יין:**
🪙 **BNB:** {data.get('bnb_balance', 0):.6f}
🎯 **SELA (SLH):** {data.get('sela_balance', 0):.6f}

🔗 **Chain ID:** {data.get('chain_id', 56)}
⛽ **גז:** BNB בלבד
✅ **נתונים אמיתיים:** {data.get('is_real_data', False)}
🕐 **עדכון:** {datetime.now().strftime('%H:%M:%S')}
                    """
                    
                    if loading_msg:
                        await loading_msg.delete()
                    
                    keyboard = [
                        [InlineKeyboardButton("📤 שלח SELA", callback_data=f"send_sela_{wallet_address}"),
                         InlineKeyboardButton("📤 שלח BNB", callback_data=f"send_bnb_{wallet_address}")],
                        [InlineKeyboardButton("📥 קבל", callback_data="receive_tokens"),
                         InlineKeyboardButton("🔄 מסחר", callback_data="trading_menu")],
                        [InlineKeyboardButton("🔄 רענן", callback_data=f"refresh_{wallet_address}"),
                         InlineKeyboardButton("👛 ארנק אחר", callback_data="check_wallet")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    if hasattr(update, 'message'):
                        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
                    else:
                        await update.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
                    
                else:
                    if loading_msg:
                        await loading_msg.delete()
                    error_msg = "❌ **שגיאה בקבלת נתונים מהבלוקצ'יין**\n\nלא ניתן להתחבר ל-BSC או הכתובת לא תקינה.\n\n**🌐 ודא שהארנק ברשת BSC**"
                    if hasattr(update, 'message'):
                        await update.message.reply_text(error_msg, parse_mode='Markdown')
                    else:
                        await update.edit_message_text(error_msg, parse_mode='Markdown')
                    
        except httpx.TimeoutException:
            error_msg = "⏰ **פסק זמן**\n\nהחיבור לבלוקצ'יין ארך יותר מדי זמן. נסה שוב."
            if hasattr(update, 'message'):
                await update.message.reply_text(error_msg, parse_mode='Markdown')
            else:
                await update.edit_message_text(error_msg, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Wallet error: {str(e)}")
            error_msg = "❌ **שגיאה בחיבור לבלוקצ'יין**\n\nלא ניתן להתחבר ל-BSC כרגע."
            if hasattr(update, 'message'):
                await update.message.reply_text(error_msg, parse_mode='Markdown')
            else:
                await update.edit_message_text(error_msg, parse_mode='Markdown')

    async def price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Price check command"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{API_BASE_URL}/config/price")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    message = f"""
📈 **מחירי SELA מעודכנים**

💰 **מחיר SELA:** {data.get('sela_price_ils', 444.50)} ₪
🔓 **שחרור משתמש:** {data.get('unlock_price_ils', 39)} ₪ = {data.get('unlock_price_sela', 0.087838)} SELA
🏦 **Staking APY:** {data.get('staking_apy', 15)}%

🌐 **רשת:** BSC (Binance Smart Chain)
⛽ **גז:** BNB בלבד
💡 *מחירים מתעדכנים אוטומטית לפי השוק*
🕐 *{datetime.now().strftime('%H:%M:%S')}*
                    """
                    
                    await update.message.reply_text(message, parse_mode='Markdown')
                else:
                    message = """
📈 **מחירי SELA - ברירת מחדל**

💰 **מחיר SELA:** 444.50 ₪
🔓 **שחרור משתמש:** 39 ₪ = 0.087838 SELA  
🏦 **Staking APY:** 15%

🌐 **רשת:** BSC
⛽ **גז:** BNB בלבד
💡 *המערכת בתהליך עדכון*
                    """
                    await update.message.reply_text(message, parse_mode='Markdown')
                    
        except Exception as e:
            logger.error(f"Price error: {str(e)}")
            message = """
📈 **מחירי SELA**

💰 **מחיר SELA:** 444.50 ₪
🔓 **שחרור משתמש:** 39 ₪ = 0.087838 SELA
🏦 **Staking APY:** 15%

🌐 **רשת:** BSC
⛽ **גז:** BNB בלבד
🔧 *המערכת בעדכון - מחירי ברירת מחדל*
            """
            await update.message.reply_text(message, parse_mode='Markdown')

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """System status check - FIXED VERSION"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{API_BASE_URL}/healthz")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    status_emoji = "🟢" if data.get('status') == 'healthy' else "🔴"
                    bsc_emoji = "🟢" if data.get('bsc_connected') else "🔴"
                    token_emoji = "🟢" if data.get('token_connected') else "🔴"
                    
                    message = f"""
📊 **סטטוס מערכת SELA - BSC**

{status_emoji} **מצב API:** {data.get('status', 'unknown')}
{bsc_emoji} **חיבור BSC:** {'מחובר' if data.get('bsc_connected') else 'מנותק'}
{token_emoji} **חיבור Token:** {'מחובר' if data.get('token_connected') else 'מנותק'}
🔗 **Chain ID:** {data.get('chain_id', 56)}
🌐 **רשת:** BSC (Binance Smart Chain)
⛽ **גז:** BNB בלבד

**שירותים פעילים:**
• 🤖 בוט טלגרם
• 🔗 API מרכזי  
• 💰 אינטגרציית BSC
• 👛 ניהול ארנקים
• 📊 נתונים אמיתיים מהבלוקצ'יין

🕐 **עדכון:** {datetime.now().strftime('%H:%M:%S')}
                    """
                    
                else:
                    message = """
📊 **סטטוס מערכת SELA**

🔄 **מצב API:** בתהליך אתחול
🔗 **חיבור BSC:** במערכת
🌐 **רשת:** BSC
⛽ **גז:** BNB בלבד

**המערכת בעבודה - נסה שוב בעוד דקה**
                    """
                    
        except Exception as e:
            logger.error(f"Status error: {str(e)}")
            message = """
📊 **סטטוס מערכת SELA**

⚠️ **מצב API:** לא זמין כרגע
🔗 **חיבור BSC:** נבדק
🌐 **רשת:** BSC
⛽ **גז:** BNB בלבד

**המערכת מתאתחלת - נסה שוב בעוד כמה דקות**
            """
        
        await update.message.reply_text(message, parse_mode='Markdown')

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command - FIXED VERSION"""
        help_text = f"""
❓ **תמיכה ועזרה**

לשאלות והבהרות:

📞 מנהל המערכת: 0584203384

**בעיות טכניות:**
• בעיית חיבור לבוט
• שגיאה בהצגת יתרה  
• בעיית אישור תשלום
• בעיות עם ארנק

**נושאים כלליים:**
• הסבר על הקהילה
• הדרכה טכנית
• הצעות לשיפור

**🌐 רשת:** BSC (Binance Smart Chain)
**⛽ גז:** BNB בלבד
**🔗 Chain ID:** 56

**שעות פעילות:** 24/7

נשמח לעזור בכל שאלה! 😊
"""
        
        keyboard = [
            [InlineKeyboardButton("👥 הצטרף לקבוצה", url=GROUP_LINK)],
            [InlineKeyboardButton("👛 בדיקת ארנק", callback_data="check_wallet")],
            [InlineKeyboardButton("🔄 מסחר", callback_data="trading_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def my_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's registered wallet"""
        user_id = str(update.effective_user.id)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{API_BASE_URL}/wallet/user/{user_id}")
                
                if response.status_code == 200:
                    wallet_data = response.json()
                    
                    if wallet_data.get('wallet_address'):
                        wallet_address = wallet_data['wallet_address']
                        await self.show_wallet_balance(update, wallet_address)
                    else:
                        text = """
👛 **עדיין אין לך ארנק רשום**

כדי להשתמש בכל הפיצ'רים, אנא רשום את הארנק שלך:

**אפשרויות:**
• 📝 **רישום ארנק** - הרשם עם הארנק הקיים שלך
• 💰 **בדיקת ארנק** - בדוק יתרות ללא רישום

**🌐 רשת נתמכת:** BSC (Binance Smart Chain)
**⛽ גז:** BNB בלבד
**💎 נתונים אמיתיים מהבלוקצ'יין!**
"""
                        keyboard = [
                            [InlineKeyboardButton("📝 רישום ארנק", callback_data="register_wallet")],
                            [InlineKeyboardButton("💰 בדיקת ארנק", callback_data="check_wallet")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
                    
                else:
                    await update.message.reply_text("❌ שגיאה בטעינת נתוני הארנק")
                    
        except Exception as e:
            logger.error(f"My wallet error: {str(e)}")
            await update.message.reply_text("❌ שגיאה במערכת - נסה שוב מאוחר יותר")

    async def register_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Register wallet command"""
        if context.args:
            wallet_address = context.args[0]
            await self.process_wallet_registration(update, wallet_address)
        else:
            help_text = """
📝 **רישום ארנק BSC**

**שימוש:**
`/register <כתובת_ארנק>`

**דוגמה:**
`/register 0xD0617B54FB4b6b66307846f217b4D685800E3dA4`

**🌐 רשת:** BSC (Binance Smart Chain)
**🔗 Chain ID:** 56
**⛽ גז:** BNB בלבד

**💎 נתונים אמיתיים מהבלוקצ'יין!**

**או** לחץ על "📝 רישום ארנק" ואז שלח את כתובת הארנק שלך.

**📋 תנאים:**
• כתובת BSC תקינה (מתחילה ב-0x)
• הארנק שלך ופרטי בלעדיים לך

**🔒 אבטחה:**
המערכת אינה שומרת private keys!
רק כתובת ציבורית נשמרת.
"""
            await update.message.reply_text(help_text, parse_mode='Markdown')
            
            user_id = str(update.effective_user.id)
            self.user_states[user_id] = 'waiting_for_wallet'

    async def process_wallet_registration(self, update: Update, wallet_address: str):
        """Process wallet registration - FIXED VERSION"""
        user_id = str(update.effective_user.id)
        
        try:
            registration_data = {
                'user_id': user_id,
                'wallet_address': wallet_address
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"📝 Registering wallet: {wallet_address} for user: {user_id}")
                response = await client.post(f"{API_BASE_URL}/wallet/register", json=registration_data)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    success_text = f"""
✅ **ארנק BSC נרשם בהצלחה!**

**מספר משתמש:** {user_id}
**כתובת ארנק:** `{wallet_address}`

**💰 יתרות נוכחיות מהבלוקצ'יין:**
🪙 **BNB:** {result.get('bnb_balance', 0):.6f}
🎯 **SELA (SLH):** {result.get('sela_balance', 0):.6f}

**🌐 רשת:** BSC (Binance Smart Chain)
**🔗 Chain ID:** 56
**⛽ גז:** BNB בלבד

**🎉 עכשיו אתה יכול:**
• 💰 **לצפות ביתרות** שלך באופן קבוע
• 🔄 **לסחור** ב-SELA ו-BNB
• 📤 **לשלוח** tokens למשתמשים אחרים
• 🏦 **להשקיע** ב-staking

**👉 השתמש ב /mywallet כדי לראות את הארנק שלך!**
"""
                    
                    keyboard = [
                        [InlineKeyboardButton("👛 הארנק שלי", callback_data="my_wallet")],
                        [InlineKeyboardButton("💰 בדיקת יתרות", callback_data=f"check_{wallet_address}")],
                        [InlineKeyboardButton("🔄 מסחר", callback_data="trading_menu")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    if hasattr(update, 'message'):
                        await update.message.reply_text(
                            success_text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                    else:
                        await update.edit_message_text(
                            success_text,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                    
                    if user_id in self.user_states:
                        del self.user_states[user_id]
                        
                else:
                    error_detail = "שגיאה ברישום הארנק"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get('detail', error_detail)
                    except:
                        pass
                        
                    logger.error(f"❌ Registration failed: {response.status_code} - {error_detail}")
                    error_msg = f"❌ **{error_detail}**\n\nודא שהכתובת תקינה ונמצאת ברשת BSC."
                    if hasattr(update, 'message'):
                        await update.message.reply_text(error_msg, parse_mode='Markdown')
                    else:
                        await update.edit_message_text(error_msg, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Wallet registration error: {str(e)}")
            error_msg = "❌ **שגיאה במערכת** - נסה שוב מאוחר יותר"
            if hasattr(update, 'message'):
                await update.message.reply_text(error_msg, parse_mode='Markdown')
            else:
                await update.edit_message_text(error_msg, parse_mode='Markdown')

    async def send_tokens(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send tokens command - FIXED FOR BSC"""
        help_text = """
📤 **שליחת Tokens - BSC**

**שימוש:**
`/send <סוג> <כתובת_יעד> <כמות>`

**דוגמאות:**
`/send SELA 0x742E6f70B6c6E79763e1d7e5c5C3c9c5d6A1b3c2 10`
`/send BNB 0x742E6f70B6c6E79763e1d7e5c5C3c9c5d6A1b3c2 0.1`

**🌐 רשת:** BSC (Binance Smart Chain)
**⛽ גז:** BNB בלבד

**נדרש:**
• ארנק רשום במערכת (/mywallet)
• יתרה מספקת
• עמלת רשת BSC (BNB)

**💡 הערה:**
העסקאות מבוצעות על רשת BSC ודורשות BNB לעמלות.
"""
        
        keyboard = [
            [InlineKeyboardButton("👛 הארנק שלי", callback_data="my_wallet")],
            [InlineKeyboardButton("📥 קבל", callback_data="receive_tokens")],
            [InlineKeyboardButton("🔄 מסחר", callback_data="trading_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def transfer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Transfer command - alias for send"""
        await self.send_tokens(update, context)

    async def receive_tokens(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Receive tokens command - FIXED FOR BSC"""
        user_id = str(update.effective_user.id)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{API_BASE_URL}/wallet/user/{user_id}")
                
                if response.status_code == 200:
                    wallet_data = response.json()
                    wallet_address = wallet_data.get('wallet_address')
                    
                    if wallet_address:
                        receive_text = f"""
📥 **קבלת Tokens - BSC**

**כתובת הארנק שלך:**
`{wallet_address}`

**🌐 רשת:** BSC (Binance Smart Chain)
**🔗 Chain ID:** 56
**⛽ גז:** BNB בלבד

**🎯 לשליחת SELA:**
1. פתח את ארנק BSC שלך
2. שלח ל: `{wallet_address}`
3. בחר רשת: **BSC**
4. אשר העסקה

**💡 מידע:**
• **SELA Token Address:** `0xACb0A09414CEA1C879c67bB7A877E4e19480f022`
• **רשת:** BSC (Binance Smart Chain)
• **Chain ID:** 56
• **גז:** BNB בלבד

**⚠️ חשוב:**
שלח רק מ-BSC ל-BSC!
אל תשלח מרשת אחרת!
"""
                    else:
                        receive_text = """
📥 **קבלת Tokens**

עדיין אין לך ארנק רשום.

**📝 כדי לקבל tokens:**
1. **רשום ארנק** עם /register
2. **קבל את כתובת** הארנק שלך  
3. **שתף את הכתובת** עם השולח

**🌐 רשת:** BSC (Binance Smart Chain)
**⛽ גז:** BNB בלבד

**👉 התחל עם:** /register
"""
                    
                    keyboard = [
                        [InlineKeyboardButton("👛 הארנק שלי", callback_data="my_wallet")],
                        [InlineKeyboardButton("📝 רישום ארנק", callback_data="register_wallet")],
                        [InlineKeyboardButton("📤 שלח", callback_data="send_tokens")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(
                        receive_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    
                else:
                    await update.message.reply_text("❌ שגיאה בטעינת נתוני הארנק")
                    
        except Exception as e:
            logger.error(f"Receive tokens error: {str(e)}")
            await update.message.reply_text("❌ שגיאה במערכת")

    async def staking(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Staking information - FIXED FOR BSC"""
        staking_text = """
🏦 **Staking SELA - BSC**

**📊 נתונים נוכחיים:**
• **APY:** 15%
• **מינימום:** 10 SELA
• **נעילה:** 30 ימים
• **תשואה יומית:** ~0.041%

**🌐 רשת:** BSC (Binance Smart Chain)
**⛽ גז:** BNB בלבד

**🎯 איך מתחילים:**
1. **רשם ארנק** עם /register
2. **הפקד SELA** לארנק שלך
3. **השקע** דרך התפריט

**💰 יתרונות:**
• תשואה קבועה וצפויה
• ריבית יומית
• ביטחון מלא - הכסף נשאר בארנק שלך
• משיכה לאחר תקופת נעילה

**👉 Status:** זמין בקרוב!
"""
        
        keyboard = [
            [InlineKeyboardButton("👛 הארנק שלי", callback_data="my_wallet")],
            [InlineKeyboardButton("💰 בדיקת יתרות", callback_data="check_wallet")],
            [InlineKeyboardButton("🔄 מסחר", callback_data="trading_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(staking_text, reply_markup=reply_markup, parse_mode='Markdown')

    # ... (rest of the trading methods remain similar but with BSC references)

    async def group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Group link command - FIXED FOR BSC"""
        group_text = f"""
👥 **הצטרף לקהילת SELA!**

**🌐 קישור לקבוצה:** [לחץ כאן להצטרפות]({GROUP_LINK})

**🎯 למה להצטרף?**
• 💬 דיונים על מחירים וטכנולוגיה
• 📊 עדכונים שוטפים על הפרויקט
• 🤝 תמיכה טכנית מהקהילה
• 🚀 הכרזות על פיצ'רים חדשים
• 💡 רעיונות והצעות לפיתוח

**🌐 רשת:** BSC (Binance Smart Chain)
**⛽ גז:** BNB בלבד

**📞 הקבוצה פתוחה לכולם!**
הצטרפו עכשיו והיו חלק מהמהפכה העברית בבלוקצ'יין!

👉 [הצטרף עכשיו לקבוצה]({GROUP_LINK})
        """
        
        keyboard = [
            [InlineKeyboardButton("👥 הצטרף לקבוצה", url=GROUP_LINK)],
            [InlineKeyboardButton("👛 בדיקת ארנק", callback_data="check_wallet")],
            [InlineKeyboardButton("↩️ חזרה", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            group_text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown',
            disable_web_page_preview=False
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        text = update.message.text
        user_id = str(update.effective_user.id)
        
        if user_id in self.user_states and self.user_states[user_id] == 'waiting_for_wallet':
            if text.startswith('0x') and len(text) == 42:
                await self.process_wallet_registration(update, text)
                return
            else:
                await update.message.reply_text(
                    "❌ **כתובת לא תקינה**\n\n"
                    "אנא שלח כתובת BSC תקינה (מתחילה ב-0x, 42 תווים).\n"
                    "🌐 **רשת:** BSC\n"
                    "⛽ **גז:** BNB בלבד\n"
                    "💎 **נתונים אמיתיים מהבלוקצ'יין!**\n"
                    "או לחץ /cancel לביטול.",
                    parse_mode='Markdown'
                )
                return
        
        if text.startswith('0x') and len(text) == 42:
            await self.show_wallet_balance(update, text)
        else:
            keyboard = [
                [InlineKeyboardButton("👛 בדיקת ארנק", callback_data="enter_wallet")],
                [InlineKeyboardButton("📝 רישום ארנק", callback_data="register_wallet")],
                [InlineKeyboardButton("📋 תפריט ראשי", callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🤔 **לא הבנתי**\n\n"
                "אנא השתמש בפקודות או בכפתורים:\n"
                "• /start - לתפריט ראשי\n"
                "• /wallet - בדיקת ארנק\n"
                "• /help - לעזרה\n\n"
                "**🌐 רשת:** BSC\n"
                "**⛽ גז:** BNB בלבד\n"
                "**💎 נתונים אמיתיים מהבלוקצ'יין!**\n\n"
                "**או:**\n"
                "• שלח כתובת ארנק (מתחילה ב-0x)\n"
                "• לחץ על אחד הכפתורים",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

    # ... (rest of the button handlers remain similar but with BSC references)

    def run(self):
        """Run the bot"""
        logger.info("🚀 Starting SELA Trading Bot with BSC Blockchain Data...")
        self.application.run_polling()

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN environment variable is required")
        exit(1)
        
    bot = SelaBot()
    bot.run()
