SELHA — SLH Bot + API (PRODUCTION READY) 🚀
מערכת קהילתית למסחר SELA: בוט טלגרם + API מבוסס FastAPI.
מעודכן לאחר כל התיקונים והשיפורים שבוצעו היום!

📋 תוכן עניינים
ארכיטקטורה

מבנה הריפו

תלויות/Requirements

משתני סביבה

פריסה ל-Railway

בדיקות מהירות

נקודות קצה API

פקודות הבוט

זרימת Unlock ותשלום

תוכנית דרך: MVP → PROD

אבטחה והקשחה

תקלות ידועות ופתרונות

רישוי

🏗️ ארכיטקטורה
bot/ — בוט טלגרם (python-telegram-bot v20.8) שעובד ב-Webhook ומדבר מול ה-API.

api/ — FastAPI שמנהל קונפיג/פרסיסטנס (JSON), אימות Unlock, וקריאות Web3 ליתרות SELA.

shared/ — עזרי Web3 משותפים.

data/ — קובצי JSON (config/unlocked) נוצרים בזמן ריצה.

זרימה טיפוסית:

משתמש נכנס לבוט → מקבל הסבר, מחיר SELA עדכני וקישור הצטרפות (לאחר Unlock).

מזין כתובת ארנק → הבוט שואל את ה-API ומחזיר יתרת SELA.

Unlock: תשלום 39₪ לחשבונות היעד → אדמין מאשר דרך הבוט.

לאחר Unlock → קישור לקבוצת הקהילה ו-UX ארנק מלא (שליחה/קבלה).

📁 מבנה הריפו
text
.
├── api/
│   ├── main.py              # FastAPI עם Web3 integration
│   ├── requirements.txt     # תלויות API
│   ├── Dockerfile          # Containerization
│   └── Procfile            # Railway deployment
├── bot/
│   ├── bot.py              # Telegram Bot עם Webhook
│   ├── requirements.txt    # תלויות Bot
│   ├── Dockerfile          # Containerization  
│   ├── Procfile            # Railway deployment
│   └── start.sh            # Script הרצה
├── shared/
│   └── slh_web3.py         # Web3 helpers
├── data/
│   ├── .keep               # שמירת תיקייה
│   └── .gitignore          # ignore קבצי נתונים
├── docker-compose.yml      # הרצה מקומית
└── README.md               # מדריך זה
📦 תלויות/Requirements
API (/api/requirements.txt):
txt
fastapi==0.115.5
uvicorn[standard]==0.32.0
web3==6.19.0
httpx==0.27.2
python-dotenv==1.0.1
setuptools==69.5.1
python-multipart==0.0.9
BOT (/bot/requirements.txt):
txt
python-telegram-bot==20.8
httpx==0.26.0
python-json-logger==2.0.7
uvloop==0.20.0
python-dotenv==1.0.1
fastapi==0.115.5
uvicorn[standard]==0.32.0
🔑 משתני סביבה
לשירות SLH_API
ADMIN_TOKEN — טוקן אדמין סודי לניהול קונפיג/אישורים

BSC_RPC_URL — URL ל-BSC (Mainnet/Testnet)

SELA_TOKEN_ADDRESS — כתובת הטוקן SELA (0xACb0A09414CEA1C879c67bB7A877E4e19480f022)

CORS_ORIGINS — (אופציונלי) * או רשימת דומיינים

MIN_NIS_TO_UNLOCK — (אופציונלי) ברירת מחדל 39

לשירות SLH_BOT
TELEGRAM_BOT_TOKEN — טוקן הבוט מטלגרם

SLH_API_BASE — כתובת ה-API (לדוגמה: https://slhapi-production.up.railway.app)

PUBLIC_BOT_BASE — כתובת ציבורית של הבוט (לדוגמה: https://slhbot-production.up.railway.app)

ADMIN_TOKEN — זהה ל-API (לכותרת X-Admin-Token)

ADMIN_CHAT_ID — (אופציונלי) מזהה צ'אט של אדמין

הערה: חלק מהקונפיג ניתן לשינוי דרך API, כך שניתן לצמצם משתני סביבה בפרודקשן.

🚀 פריסה ל-Railway
SLH_API
Root Directory: /api

Start command: uvicorn main:app --host=0.0.0.0 --port=8080

ודא שכל משתני הסביבה קיימים

פריסה מחדש

SLH_BOT
Root Directory: /bot

Dockerfile: bot/Dockerfile

Start command: python -u bot.py

ודא: SLH_API_BASE, PUBLIC_BOT_BASE הם https

למה זה חשוב?
טלגרם דורש HTTPS מלא ל-webhook

Dockerfile של הבוט מעתיק את תוכן /bot ל-/app ומריץ /app/bot.py

🧪 בדיקות מהירות
API
bash
# בריאות
curl -s https://slhapi-production.up.railway.app/healthz

# מחיר
curl -s https://slhapi-production.up.railway.app/config/price

# יתרה
curl -s https://slhapi-production.up.railway.app/token/balance/0xYourBSCAddress

# מידע טוקן
curl -s https://slhapi-production.up.railway.app/token/info
BOT
בטלגרם לשלוח לבוט:

/start - הודעת פתיחה

/price - מחיר SELA

/wallet 0xYourBSCAddress - יתרת SELA

/unlock39 - הוראות הצטרפות

/status - סטטוס מערכת

אדמין:

/approve <chat_id> - אשר משתמש

/set_price 444 - עדכון מחיר

🔌 נקודות קצה API
מתודה	נתיב	תיאור
GET	/healthz	בדיקת חיים + סטטוס Web3
GET	/	הודעת שורש
GET	/config	קבלת כל הקונפיג
POST	/config	עדכון חלקי (דורש X-Admin-Token)
GET	/config/price	קבלת מחיר SELA בנ״ש
POST	/config/price	עדכון מחיר (דורש X-Admin-Token)
GET	/token/balance/{address}	יתרת SELA בכתובת
GET	/token/info	מידע על טוקן SELA
GET	/unlock/status/{chat_id}	סטטוס Unlock
POST	/unlock/verify	רישום בקשת אימות (pending)
POST	/unlock/grant	אישור Unlock (אדמין)
GET	/unlock/pending	בקשות ממתינות (אדמין)
כותרת אדמין:

text
X-Admin-Token: <ADMIN_TOKEN>
🤖 פקודות הבוט
לכל המשתמשים
/start — הסבר על הקהילה, הצגת מחיר SELA עדכני

/price — מחיר SELA נוכחי

/wallet <address> — רישום כתובת והצגת יתרה

/unlock39 — הוראות תשלום ואימות (39₪, ניתן לשינוי)

/unlock_verify <txhash\|ref> — שליחת מזהה/Tx לאימות

/join — קישור הצטרפות לקבוצה (למאושרים)

/status — סטטוס API ו-Unlock

למנהלים
/approve <chat_id> — מאשר משתמש (קורא /unlock/grant)

/set_price <nis> — עדכון מחיר דרך /config/price

/pending — הצג בקשות ממתינות

💰 זרימת Unlock ותשלום
משתמש מבקש /unlock39 → מוצגים חשבונות היעד לתשלום והסכום (min_nis_to_unlock)

לאחר תשלום, שולח /unlock_verify <ref> (למשל TxHash/קבלה)

אדמין מפעיל /approve <chat_id> (קריאה ל-/unlock/grant) → המשתמש מקבל גישה מלאה

/join שולח קישור לקבוצה (אם הוגדר)

היום: האימות הוא ידני (pending → grant)
בהמשך (Prod): אימות אוטומטי לפי TxHash על BSC, או OCR לקבלות

🗺️ תוכנית דרך (MVP → PROD)
✅ MVP (בוצע והופעל היום):
בוט עובד ב-Webhook עם HTTPS ציבורי

API ליתרות SELA (Web3), קונפיג מחיר/מינימום/קבוצה/חשבונות

זרימת Unlock בסיסית: verify → approve (אדמין)

שמירת קונפיג/מאושרים בקובצי JSON ב-data/

חיבור ל-BSC Testnet (Chain ID: 97)

🔄 שלב 2 (מידי):
Persist אמין: קבצי JSON נעולים → מעבר ל-Redis/DB לפי צורך

Admin Panel בבוט (InlineKeyboard): Pending list, Approve/Reject, Health

/send / /receive בבוט: UX מלא עם ולידציות

הצגת גז/עמלות, אזהרות "אין BNB לגז"

מעבר ל-BSC Mainnet

🚀 שלב 3 (התקדמות):
אימות אוטומטי:

BSC TxHash (sum/date/recipient)

העלאת תמונת קבלה + בדיקת סכום/תאריך

ניהול חשבונות יעד דרך API (מלא): add/remove/list

/config מאובטח מלא: תפריט אדמין לשינוי כל ההגדרות דרך הבוט

🌟 חזון Marketplace:
לכל משתמש "חנות" עם מחיר קניה/מכירה אישי

רישום היסטוריית רכישות ומכירות, חישוב ממוצעים

יצירת ספר פקודות קהילתי (OTC)

ניהול הרשאות/תפקידים בקהילה (מוכרים מאומתים, מדדים)

🔒 אבטחה והקשחה
ADMIN_TOKEN חובה בפרודקשן לכל פעולת ניהול

CORS מצומצם לדומיינים ידועים

לוגים בפורמט JSON לצורך ניתוח/מוניטורינג

שמירה על גרסאות תלויות תואמות (PTB 20.8 ↔ httpx 0.26.x)

בהמשך: WAF / Rate-limit, אימות Webhook חתום, ולידציית קלט חזקה

🐛 תקלות ידועות ופתרונות
"Bad webhook: an https url must be provided for webhook"
ודא PUBLIC_BOT_BASE הוא https://... ציבורי

הבוט רושם webhook ל-{PUBLIC_BOT_BASE}/webhook

"python: can't open file '/app/bot.py'"
ב-Railway השתמש ב-Start command: python -u bot.py

אל תפעיל python -u bot/bot.py — הנתיב לא קיים בתמונה

"This Application was not initialized via Application.initialize"
הוסף await self.application.initialize() לפני setup_webhook()

ודא אתחול מלא לפני קבלת הודעות

API: ModuleNotFoundError: pkg_resources
הוסף setuptools ל-/api/requirements.txt

404 Not Found מה-API
ודא שה-API רץ וכל האנדפוינטים זמינים

בדוק את הלוגים של ה-API בשגיאות

📄 רישוי
TBD (MIT/Apache-2.0/Proprietary) — עדכן לפי החלטת הפרויקט.

🎯 סטטוס נוכחי - PRODUCTION READY ✅
מה עובד עכשיו:

✅ בוט טלגרם פעיל ומגיב

✅ API עם חיבור ל-BSC

✅ קריאת יתרות SELA מכל ארנק

✅ מערכת Unlock בסיסית

✅ ניהול קונפיג דינמי

✅ פריסה אוטומטית ב-Railway

השלבים הבאים:

בדיקת חיבור ל-BSC Mainnet (לשנות RPC URL)

הוספת יכולות מסחר (קניה/מכירה)

אימות אוטומטי של תשלומים

פלטפורמת Marketplace מלאה

🔄 מעודכן אחרון: 30/10/2025 - לאחר כל התיקונים והשיפורים שבוצעו היום!
