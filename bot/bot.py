import os, sys, json, asyncio, logging
from typing import Optional, Dict, Any
import httpx

from pythonjsonlogger import jsonlogger
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler,
    ContextTypes
)

# ===== env =====
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
SLH_API_BASE = os.getenv("SLH_API_BASE", "").strip().rstrip("/")
PUBLIC_BOT_BASE = os.getenv("PUBLIC_BOT_BASE", "").strip().rstrip("/")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "").strip()
GROUP_INVITE_LINK = os.getenv("GROUP_INVITE_LINK", "").strip()
APPROVED_CHAT_ID = int(os.getenv("APPROVED_CHAT_ID", "0") or 0)

# ===== logging (JSON) =====
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
root = logging.getLogger()
root.handlers = [handler]
root.setLevel(logging.INFO)
log = logging.getLogger("slh.bot")

# ===== helpers =====
def is_admin(user_id: int) -> bool:
    # MVP: אם APPROVED_CHAT_ID=0 => מאפשר פקודות אדמין למי שמוגדר לבדוק; אחרת – רק ה־ID הזה אדמין
    return (APPROVED_CHAT_ID == 0) or (user_id == APPROVED_CHAT_ID)

def api_headers(admin: bool = False) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if admin and ADMIN_TOKEN:
        h["X-Admin-Token"] = ADMIN_TOKEN
    return h

async def api_get(path: str, *, admin: bool = False, timeout: float = 10) -> Optional[Dict[str, Any]]:
    if not SLH_API_BASE.startswith("http"):
        raise RuntimeError("SLH_API_BASE must start with http(s)://")
    url = f"{SLH_API_BASE}{path}"
    async with httpx.AsyncClient(timeout=timeout) as cli:
        r = await cli.get(url, headers=api_headers(admin=admin))
        if r.status_code // 100 == 2:
            try:
                return r.json()
            except Exception:
                return {"ok": True, "text": r.text}
        return {"ok": False, "status": r.status_code, "text": r.text}

async def api_post(path: str, body: Dict[str, Any], *, admin: bool = False, timeout: float = 15) -> Dict[str, Any]:
    if not SLH_API_BASE.startswith("http"):
        raise RuntimeError("SLH_API_BASE must start with http(s)://")
    url = f"{SLH_API_BASE}{path}"
    async with httpx.AsyncClient(timeout=timeout) as cli:
        r = await cli.post(url, headers=api_headers(admin=admin), json=body)
        try:
            js = r.json()
        except Exception:
            js = {"ok": r.status_code // 100 == 2, "text": r.text}
        js.setdefault("ok", r.status_code // 100 == 2)
        js.setdefault("status", r.status_code)
        return js

def fmt_nis(x: float) -> str:
    return f"{x:,.2f} ₪".replace(",", "'")

# זיכרון מקומי לכתובת ארנק שנרשמה לכל צ׳אט (MVP)
user_wallets: Dict[int, str] = {}

# ===== commands =====
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    price = await api_get("/config/price")
    price_txt = "לא זמין"
    if price and price.get("ok") and "price_nis" in price:
        price_txt = fmt_nis(float(price["price_nis"]))

    text = (
        "ברוך הבא ל־SLH!\n\n"
        "📜 *חזון*: כל אחד מקים חנות קלפים/אסימונים, כלכלה קהילתית חופשית, וארנק פרטי לניהול SELA.\n"
        "🔑 גישה מלאה לארנק ולכלי קהילה ניתנת לאחר אימות תשלום של 39 ₪.\n"
        f"💰 *מחיר SELA נוכחי*: {price_txt}\n\n"
        "מה אפשר לעשות כאן?\n"
        "• ‎/wallet <כתובת> — רישום/בדיקת כתובת BSC להצגת יתרות SELA\n"
        "• ‎/price — הצגת מחיר SELA\n"
        "• ‎/unlock39 — הסבר רכישה/אימות קבלה (39 ₪)\n"
        "• ‎/join — קישור לקבוצת הקהילה (לאחר קבלה)\n"
        "• ‎/status — סטטוס מערכת\n\n"
        "למנהלים:\n"
        "• ‎/approve <chat_id> — אישור משתמש מול ה־API\n"
        "• ‎/set_price <nis>, ‎/set_min <nis>, ‎/set_group <invite>, ‎/add_account <type> <details>\n"
    )

    kb = []
    if GROUP_INVITE_LINK:
        kb.append([InlineKeyboardButton("הצטרפות לקהילה", url=GROUP_INVITE_LINK)])
    kb.append([InlineKeyboardButton("הצגת מחיר", callback_data="show_price")])

    await ctx.bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="Markdown"
    )

async def cmd_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    price = await api_get("/config/price")
    if price and price.get("ok") and "price_nis" in price:
        await ctx.bot.send_message(chat_id, f"מחיר SELA כרגע: {fmt_nis(float(price['price_nis']))}")
    else:
        await ctx.bot.send_message(chat_id, "לא הצלחתי להביא מחיר כרגע.")

async def cmd_wallet(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    args = ctx.args
    if not args:
        await ctx.bot.send_message(chat_id, "שימוש: ‎/wallet 0xYourBSCAddress")
        return
    addr = args[0].strip()
    user_wallets[chat_id] = addr

    bal = await api_get(f"/token/balance/{addr}")
    if not bal or not bal.get("ok"):
        await ctx.bot.send_message(chat_id, "לא ניתן להביא יתרה כרגע.")
        return

    text = f"✅ נקלטה הכתובת: `{addr}`\n"
    if "symbol" in bal and "decimals" in bal and "balance" in bal:
        sym = bal["symbol"]
        dec = int(bal["decimals"])
        raw = int(bal["balance"])
        human = raw / (10 ** dec)
        text += f"יתרת {sym}: {human}\n"
    else:
        text += f"יתרה: {bal}\n"

    await ctx.bot.send_message(chat_id, text, parse_mode="Markdown")

async def cmd_unlock39(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    minv = await api_get("/config/min")
    min_txt = "39"
    if minv and minv.get("ok") and "min_nis" in minv:
        min_txt = str(minv["min_nis"])

    accounts = await api_get("/config/accounts")
    lines = []
    if accounts and accounts.get("ok") and "accounts" in accounts and accounts["accounts"]:
        for acc in accounts["accounts"]:
            lines.append(f"• {acc}")
    if not lines:
        lines.append("• בנק הפועלים, סניף כפר גנים (153), חשבון 73462 — המוטב: קאופמן צביקה")

    msg = (
        f"🔓 כדי לפתוח גישה מלאה, יש לשלם {min_txt} ₪.\n\n"
        "חשבונות לתשלום:\n" + "\n".join(lines) + "\n\n"
        "לאחר התשלום, שלח קבלה/צילום מסך – או העבר TxHash ב-/unlock_verify <txhash>.\n"
        "אדמין יאשר אותך, או אימות אוטומטי בקרוב.\n"
    )
    await ctx.bot.send_message(chat_id, msg)

async def cmd_unlock_verify(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not ctx.args:
        await ctx.bot.send_message(chat_id, "שימוש: ‎/unlock_verify <txhash | reference>")
        return
    ref = " ".join(ctx.args)
    res = await api_post("/unlock/verify", {"chat_id": chat_id, "reference": ref})
    if res.get("ok"):
        await ctx.bot.send_message(chat_id, "הבקשה נקלטה. תקבל אישור לאחר בדיקה ✅")
    else:
        await ctx.bot.send_message(chat_id, "שגיאה באימות. נסה שוב בעוד רגע.")

async def cmd_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    st = await api_get(f"/status/{chat_id}")
    if st and st.get("ok") and st.get("unlocked"):
        link = st.get("group_invite_link") or GROUP_INVITE_LINK or "לא הוגדר לינק לקבוצה."
        await ctx.bot.send_message(chat_id, f"ברוך הבא! זה הקישור: {link}")
    else:
        await ctx.bot.send_message(chat_id, "עדיין לא מאושר. השלם אימות ב-/unlock39.")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    h = await api_get("/healthz")
    u = await api_get(f"/status/{chat_id}")
    api_ok = bool(h and (h.get("ok") or "OK" in str(h)))
    unlocked = bool(u and u.get("ok") and u.get("unlocked"))
    await ctx.bot.send_message(chat_id, f"API: {'OK' if api_ok else 'DOWN'} | גישה: {'✅' if unlocked else '❌'}")

# ===== admin commands =====
async def cmd_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    if not is_admin(user.id):
        await ctx.bot.send_message(chat_id, "לא מורשה.")
        return
    if not ctx.args:
        await ctx.bot.send_message(chat_id, "שימוש: ‎/approve <chat_id>")
        return
    tchat = int(ctx.args[0])
    res = await api_post("/unlock/grant", {"chat_id": tchat}, admin=True)
    await ctx.bot.send_message(chat_id, "✅ אושר" if res.get("ok") else f"❌ נכשל: {res}")

async def cmd_set_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    if not is_admin(user.id):
        await ctx.bot.send_message(chat_id, "לא מורשה.")
        return
    if not ctx.args:
        await ctx.bot.send_message(chat_id, "שימוש: ‎/set_price <nis>")
        return
    try:
        val = float(ctx.args[0])
    except Exception:
        await ctx.bot.send_message(chat_id, "מספר לא חוקי.")
        return
    res = await api_post("/config/price", {"price_nis": val}, admin=True)
    await ctx.bot.send_message(chat_id, f"{'עודכן ✅' if res.get('ok') else f'❌: {res}'}")

async def cmd_set_min(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    if not is_admin(user.id):
        await ctx.bot.send_message(chat_id, "לא מורשה.")
        return
    if not ctx.args:
        await ctx.bot.send_message(chat_id, "שימוש: ‎/set_min <nis>")
        return
    try:
        val = int(float(ctx.args[0]))
    except Exception:
        await ctx.bot.send_message(chat_id, "מספר לא חוקי.")
        return
    res = await api_post("/config/min", {"min_nis": val}, admin=True)
    await ctx.bot.send_message(chat_id, f"{'עודכן ✅' if res.get('ok') else f'❌: {res}'}")

async def cmd_set_group(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    if not is_admin(user.id):
        await ctx.bot.send_message(chat_id, "לא מורשה.")
        return
    if not ctx.args:
        await ctx.bot.send_message(chat_id, "שימוש: ‎/set_group <invite_link>")
        return
    link = ctx.args[0]
    res = await api_post("/config/group", {"invite": link}, admin=True)
    await ctx.bot.send_message(chat_id, f"{'עודכן ✅' if res.get('ok') else f'❌: {res}'}")

async def cmd_add_account(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    if not is_admin(user.id):
        await ctx.bot.send_message(chat_id, "לא מורשה.")
        return
    if len(ctx.args) < 2:
        await ctx.bot.send_message(chat_id, "שימוש: ‎/add_account <type> <details...>")
        return
    typ = ctx.args[0]
    details = " ".join(ctx.args[1:])
    res = await api_post("/config/account", {"type": typ, "details": details}, admin=True)
    await ctx.bot.send_message(chat_id, f"{'נוסף ✅' if res.get('ok') else f'❌: {res}'}")

# ===== webhook bootstrap =====
async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing")
    if not SLH_API_BASE.startswith("http"):
        raise RuntimeError("SLH_API_BASE must be http(s)://")
    if not PUBLIC_BOT_BASE.startswith("https://"):
        raise RuntimeError("PUBLIC_BOT_BASE must be https://... (Telegram מחייב https)")

    app: Application = ApplicationBuilder().token(BOT_TOKEN).build()

    # handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("wallet", cmd_wallet))
    app.add_handler(CommandHandler("unlock39", cmd_unlock39))
    app.add_handler(CommandHandler("unlock_verify", cmd_unlock_verify))
    app.add_handler(CommandHandler("join", cmd_join))
    app.add_handler(CommandHandler("status", cmd_status))

    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("set_price", cmd_set_price))
    app.add_handler(CommandHandler("set_min", cmd_set_min))
    app.add_handler(CommandHandler("set_group", cmd_set_group))
    app.add_handler(CommandHandler("add_account", cmd_add_account))

    # webhook
    webhook_url = f"{PUBLIC_BOT_BASE}/tg"
    log.info(f"Setting webhook to {webhook_url}")

    await app.updater.start_webhook(
        listen="0.0.0.0", port=int(os.getenv("PORT", "8080")), url_path="tg",
        webhook_url=webhook_url
    )
    log.info("Application started")
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log.exception("Bot crashed: %s", e)
        raise
