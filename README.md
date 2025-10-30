# SELHA — SLH Bot + API (MVP → PROD)

מערכת קהילתית למסחר SELA: בוט טלגרם + API מבוסס FastAPI.  
מטרות: הרשמה לקהילה (Unlock), הצגת יתרות SELA מ-BSC, ניהול קונפיג דינאמי, והתרחבות לארנק תפקודי מלא.

---

## תוכן עניינים
- [ארכיטקטורה](#ארכיטקטורה)
- [מבנה הריפו](#מבנה-הריפו)
- [תלויות/Requirements](#תלויותrequirements)
- [משתני סביבה](#משתני-סביבה)
- [פריסה ל-Railway](#פריסה-לrailway)
- [בדיקות מהירות](#בדיקות-מהירות)
- [נקודות קצה API](#נקודות-קצה-api)
- [פקודות הבוט](#פקודות-הבוט)
- [זרימת Unlock ותשלום](#זרימת-unlock-ותשלום)
- [תוכנית דרך: MVP → PROD](#תוכנית-דרך-mvp--prod)
- [אבטחה והקשחה](#אבטחה-והקשחה)
- [תקלות ידועות ופתרונות](#תקלות-ידועות-ופתרונות)
- [רישוי](#רישוי)

---

## ארכיטקטורה

- **bot/** — בוט טלגרם (python-telegram-bot v20.8) שעובד ב-Webhook ומדבר מול ה-API.
- **api/** — FastAPI שמנהל קונפיג/פרסיסטנס (JSON בשלב זה), אימות Unlock, וקריאות Web3 ליתרות.
- **shared/** — עזרי Web3 משותפים (למשל `slh_web3.py`).
- **data/** — קובצי JSON (config/unlocked) נוצרים בזמן ריצה (Persist ב-Railway volume בהמשך).

זרימה טיפוסית:
1. משתמש נכנס לבוט → מקבל הסבר, מחיר SELA עדכני וקישור הצטרפות (לאחר Unlock).
2. מזין כתובת ארנק → הבוט שואל את ה-API ומחזיר יתרת SELA.
3. Unlock: תשלום 39₪ לחשבונות היעד → אדמין מאשר דרך הבוט (או אימות אוטומטי בהמשך).
4. לאחר Unlock → קישור לקבוצת הקהילה ו-UX ארנק מלא (שליחה/קבלה).

---

## מבנה הריפו

.
├─ api/
│ ├─ main.py
│ ├─ requirements.txt
│ ├─ Dockerfile
│ └─ Procfile
├─ bot/
│ ├─ bot.py
│ ├─ requirements.txt
│ ├─ Dockerfile
│ ├─ Procfile
│ └─ start.sh
├─ shared/
│ └─ slh_web3.py
├─ data/
│ ├─ .keep
│ └─ .gitignore
├─ docker-compose.yml
└─ README_DEPLOY.md (מדריך התקנה מפורט, אם קיים)

markdown
Copy code

---

## תלויות/Requirements

- **API** (`/api/requirements.txt`):
  - `fastapi==0.115.5`
  - `uvicorn[standard]==0.32.0`
  - `web3==6.19.0`
  - `httpx==0.27.2`
  - `python-dotenv==1.0.1`
  - `setuptools==69.5.1` ← נדרש ל-`pkg_resources` ב-Python 3.13

- **BOT** (`/bot/requirements.txt`):
  - `python-telegram-bot==20.8`
  - `httpx==0.26.0` ← תואם ל-PTB 20.8
  - `python-json-logger==2.0.7`
  - `uvloop==0.20.0`

---

## משתני סביבה

### לשירות **SLH_API**
- `ADMIN_TOKEN` — טוקן אדמין לניהול קונפיג/אישורים.
- `BSC_RPC_URL` — URL ל-BSC (Mainnet/Testnet).
- `SELA_TOKEN_ADDRESS` — כתובת הטוקן SELA (Checksum).
- `CORS_ORIGINS` — (אופציונלי) `*` או רשימת דומיינים.
- `MIN_NIS_TO_UNLOCK` — (אופציונלי) ברירת מחדל 39.
- `GROUP_INVITE_LINK` — (אופציונלי) קישור לקבוצת הקהילה.

### לשירות **SLH_BOT**
- `TELEGRAM_BOT_TOKEN`
- `SLH_API_BASE` — לדוגמה: `https://slhapi-production.up.railway.app`
- `PUBLIC_BOT_BASE` — לדוגמה: `https://slhbot-production.up.railway.app`
- `ADMIN_TOKEN` — זהה ל-API (לכותרת `X-Admin-Token`).
- `APPROVED_CHAT_ID` — (אופציונלי) מזהה צ׳אט של אדמין.

> *הערה:* חלק מהקונפיג ניתן לשינוי דרך API (ראה להלן), כך שניתן לצמצם משתני סביבה בפרודקשן.

---

## פריסה ל-Railway

### SLH_API
- **Root Directory**: `/api`
- **Start command**: `uvicorn main:app --host=0.0.0.0 --port=8080`
- ודא שכל משתני הסביבה קיימים (מפורט לעיל).
- פריסה מחדש.

### SLH_BOT
- **Root Directory**: `/bot`
- **Dockerfile**: `bot/Dockerfile`
- **Start command**: ריק (מומלץ) — תן ל-Dockerfile להריץ `CMD`, או `python -u bot.py`.
- ודא: `SLH_API_BASE`, `PUBLIC_BOT_BASE` הם **https**.
- פריסה מחדש.

#### למה זה חשוב?
- טלגרם דורש **HTTPS מלא** ל-webhook (לא `http://0.0.0.0`).
- Dockerfile של הבוט מעתיק את תוכן `/bot` ל-`/app` ומריץ `/app/bot.py`.

---

## בדיקות מהירות

### API
```bash
# בריאות
curl -s https://slhapi-production.up.railway.app/healthz

# מחיר
curl -s https://slhapi-production.up.railway.app/config/price

# יתרה
curl -s https://slhapi-production.up.railway.app/token/balance/0xYourBSCAddress
BOT
בטלגרם לשלוח לבוט:

/start

/price

/wallet 0xYourBSCAddress

/unlock39

/status

אדמין:

/approve <chat_id>

/set_price 444

/set_min 39

/set_group https://t.me/+invite

/add_account bank "בנק הפועלים סניף 153 חשבון 73462 המוטב: קאופמן צביקה"

נקודות קצה API
מתודה	נתיב	תיאור
GET	/healthz	בדיקת חיים
GET	/config	קבלת כל הקונפיג
POST	/config	עדכון חלקי (דורש X-Admin-Token)
GET	/config/price	קבלת מחיר SELA בנ״ש
POST	/config/price	עדכון מחיר (דורש X-Admin-Token)
GET	/unlock/status/{chat_id}	סטטוס Unlock
POST	/unlock/grant	אישור Unlock (אדמין)
POST	/unlock/revoke	ביטול Unlock (אדמין)
POST	/unlock/verify	רישום בקשת אימות (pending)
GET	/token/balance/{address}	יתרת SELA בכתובת

כותרת אדמין:
X-Admin-Token: <ADMIN_TOKEN>

פקודות הבוט
/start — הסבר על הקהילה, הצגת מחיר SELA עדכני.

/price — מחיר SELA נוכחי.

/wallet <address> — רישום כתובת והצגת יתרה.

/unlock39 — הוראות תשלום ואימות (39₪, ניתן לשינוי).

/unlock_verify <txhash|ref> — שליחת מזהה/Tx לאימות (MVP: pending).

/join — קישור הצטרפות לקבוצה (למאושרים).

/status — סטטוס API ו-Unlock.

אדמין:

/approve <chat_id> — מאשר משתמש (קורא /unlock/grant).

/set_price <nis> — עדכון מחיר דרך /config/price.

/set_min <nis> — עדכון min_nis_to_unlock.

/set_group <invite_link> — קביעת קישור קבוצה.

/add_account <type> <details...> — הוספת פרטי יעד תשלום לתצוגה.

זרימת Unlock ותשלום
משתמש מבקש /unlock39 → מוצגים חשבונות היעד לתשלום והסכום (min_nis_to_unlock).

לאחר תשלום, שולח /unlock_verify <ref> (למשל TxHash/קבלה).

אדמין מפעיל /approve <chat_id> (קריאה ל-/unlock/grant) → המשתמש מקבל גישה מלאה.

/join שולח קישור לקבוצה (אם הוגדר).

היום: האימות הוא ידני (pending → grant).
בהמשך (Prod): אימות אוטומטי לפי TxHash על BSC, או OCR לקבלות, ושמירה מתועדת.

תוכנית דרך (MVP → PROD)
MVP (בוצע):

בוט עובד ב-Webhook עם HTTPS ציבורי.

API ליתרות SELA (Web3), קונפיג מחיר/מינימום/קבוצה/חשבונות.

זרימת Unlock בסיסית: verify → approve (אדמין).

שמירת קונפיג/מאושרים בקובצי JSON ב-data/.

שלב 2 (מידי):

Persist אמין: קבצי JSON נעולים (קיים) → מעבר ל-Redis/DB לפי צורך.

Admin Panel בבוט (InlineKeyboard): Pending list, Approve/Reject, Health.

/send / /receive בבוט: UX מלא עם ולידציות והודעות שגיאה ידידותיות.

הצגת גז/עמלות, אזהרות “אין BNB לגז”.

שלב 3 (התקדמות):

אימות אוטומטי:

BSC TxHash (sum/date/recipient).

העלאת תמונת קבלה + בדיקת סכום/תאריך.

ניהול חשבונות יעד דרך API (מלא): add/remove/list.

/config מאובטח מלא: תפריט אדמין לשינוי כל ההגדרות דרך הבוט.

חזון Marketplace:

לכל משתמש “חנות” עם מחיר קניה/מכירה אישי.

רישום היסטוריית רכישות ומכירות, חישוב ממוצעים, יצירת ספר פקודות קהילתי (OTC).

ניהול הרשאות/תפקידים בקהילה (מוכרים מאומתים, מדדים).

אבטחה והקשחה
ADMIN_TOKEN חובה בפרודקשן לכל פעולת ניהול.

CORS מצומצם לדומיינים ידועים.

לוגים בפורמט JSON לצורך ניתוח/מוניטורינג.

שמירה על גרסאות תלויות תואמות (PTB 20.8 ↔ httpx 0.26.x).

בהמשך: WAF / Rate-limit, אימות Webhook חתום, ולידציית קלט חזקה.

תקלות ידועות ופתרונות
“Bad webhook: an https url must be provided for webhook”
ודא PUBLIC_BOT_BASE הוא https://... ציבורי. הבוט רושם webhook ל-{PUBLIC_BOT_BASE}/tg.

“python: can't open file '/app/bot.py'”
ב-Railway השאר Start command ריק (תן ל-Dockerfile להריץ CMD) או python -u bot.py.
אל תפעיל python -u bot/bot.py — הנתיב לא קיים בתמונה.

התנגשות תלויות PTB/httpx
השאר python-telegram-bot==20.8 עם httpx==0.26.0.

API: ModuleNotFoundError: pkg_resources
הוסף setuptools ל-/api/requirements.txt (נוסף כבר בקובץ).

רישוי
TBD (MIT/Apache-2.0/Proprietary) — עדכן לפי החלטת הפרויקט.

ruby
Copy code

**מה הלאה?**  
אחרי שתדביק את ה-README ותפרוס עם הקבצים שסידרנו (Dockerfile/requirements), תריץ בדיקות מהירות ותעדכן אותי על מצב `/start`, `/wallet`, `/price`, וזרימת `/unlock_verify` → `/approve` → `/join`. משם נתקדם ל-Wallet UX מלא ו-Persist ל-Redis/DB.
::contentReference[oaicite:0]{index=0}






