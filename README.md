🚀 SELA Trading Platform
בורסת SELA העברית הראשונה למסחר ב-SELA ו-BNB על רשת BSC.

📦 התכונות העיקריות
🔄 מערכת מסחר מלאה
קניה/מכירה של SELA עם BNB
ספר הזמנות מלא ומתעדכן בזמן אמת
מנוע מסחר אוטומטי להתאמת הזמנות
היסטוריית עסקאות מלאה

💰 ניהול ארנקים
צפייה ביתרות BNB ו-SELA
אימות ארנקים מול רשת BSC
מעקב אחר עסקאות
העברות SELA ו-BNB בין משתמשים

🎯 ממשק משתמש
בוט טלגרם בעברית מלאה
כפתורים אינטראקטיביים לניווט קל
פקודות טקסט למשתמשים מתקדמים

🚀 התקנה והפעלה
דרישות מוקדמות
Docker & Docker Compose
Token בוט טלגרם

הפעלה מהירה
```bash
# Clone the repository
git clone <repository-url>
cd sela-trading

# Copy environment file
cp .env.example .env

# Edit .env עם הטוקנים שלך
nano .env

# Start services
docker-compose up -d
📡 API Endpoints
בסיסיים
GET /healthz - בדיקת סטטוס
GET /wallet/balance/{address} - יתרות ארנק
GET /config/price - מחירים

מסחר
POST /order - יצירת הזמנה
GET /orderbook/{pair} - ספר הזמנות
GET /user/orders/{user_id} - הזמנות משתמש
POST /order/cancel - ביטול הזמנה

העברות
POST /transfer/sela - העברת SELA
POST /transfer/bnb - העברת BNB
GET /transfers/{wallet_address} - היסטוריית העברות

🎯 פקודות בוט
בסיסיות
/start - תפריט ראשי
/wallet <address> - צפייה ביתרות
/price - מחיר SELA
/status - סטטוס מערכת
/mywallet - הארנק הרשום שלי
/register <address> - רישום ארנק

מסחר
/buy <pair> <price> <amount> - קניית SELA
/sell <pair> <price> <amount> - מכירת SELA
/orderbook <pair> - ספר הזמנות
/orders - ההזמנות שלי
/cancel <order_id> - ביטול הזמנה

העברות
/send <type> <address> <amount> - שליחת tokens
/transfer - alias for send
/receive - קבלת tokens

🔧 קונפיגורציה
זוגות מסחר
SELA_BNB - SELA/BNB
SELA_USD - SELA/USD

עמלות
עמלת מסחר: 0.1%
אין עמלות נסתרות

🌐 רשת
BSC (Binance Smart Chain)
Chain ID: 56
SELA Token: 0xACb0A09414CEA1C879c67bB7A877E4e19480f022

🤝 תמיכה
הצטרף לקבוצה שלנו: SELA Community

text

### 📄 .env.example
```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# BSC Configuration
BSC_RPC_URL=https://bsc-dataseed.binance.org/
SELA_TOKEN_ADDRESS=0xACb0A09414CEA1C879c67bB7A877E4e19480f022

# API Configuration
API_BASE_URL=http://localhost:8000

# Admin Configuration
ADMIN_CHAT_ID=your_chat_id_here
ADMIN_TOKEN=your_admin_token_here

# External APIs
BSCSCAN_API_KEY=your_bscscan_api_key
ETHERSCAN_API_KEY=your_etherscan_api_key
ETH_RPC_URL=https://eth.llamarpc.com

# Business Logic
MIN_NIS_TO_UNLOCK=39
