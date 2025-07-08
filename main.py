
# main.py — Telegram-бот для TON Portfolio

import asyncio
import nest_asyncio
nest_asyncio.apply()
import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import requests

BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN"
TONAPI_KEY = "PASTE_YOUR_TONAPI_KEY"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

user_wallets = {}
subscribed_users = set()

MAIN_KB = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🔗 Подключить TON-кошелёк", web_app=WebAppInfo(url="https://ton-mini-app-1bw.pages.dev"))],
        ["💰 Баланс", "🛡️ Скам-чек"],
        ["🐋 Alerts ON/OFF", "🧾 Показать кошелёк"],
        ["🎨 NFT-проверка"]
    ],
    resize_keyboard=True,
)

def api_get(endpoint: str, params: dict = None):
    headers = {"X-API-Key": TONAPI_KEY}
    url = f"https://tonapi.io/v1/{endpoint}"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logger.error(f"API request error: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Выбери действие:", reply_markup=MAIN_KB)

async def webapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    data = update.message.web_app_data.data
    if not data.startswith("0:") or len(data) < 10:
        await update.message.reply_text("❌ Неверный адрес кошелька!")
        return
    user_wallets[uid] = data
    await update.message.reply_text(f"✅ Кошелёк сохранён:
`{data}`", parse_mode="Markdown")

async def cmd_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    w = user_wallets.get(uid)
    if w:
        await update.message.reply_text(f"🧾 Ваш кошелёк:
`{w}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Кошелёк не подключён. Используйте кнопку ниже.")

async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    address = user_wallets.get(uid)
    if not address:
        await update.message.reply_text("❌ Сначала подключите кошелёк.")
        return

    try:
        url = "https://toncenter.com/api/v2/getAddressBalance"
        response = requests.get(url, params={"address": address}).json()
        if response.get("ok") and "result" in response:
            balance = int(response["result"]) / 1e9
            await update.message.reply_text(f"💰 Баланс: {balance:.4f} TON")
        else:
            await update.message.reply_text("⚠️ Не удалось получить баланс.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Ошибка: {e}")

async def cmd_nfts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    addr = user_wallets.get(uid)
    if not addr:
        await update.message.reply_text("❌ Сначала подключите кошелёк.")
        return

    await update.message.reply_text("⏳ Ищу NFT…")
    data = api_get(f"accounts/{addr}/nfts", {"limit": 10})
    if not data or not data.get("nft_items"):
        await update.message.reply_text("😢 NFT не найдены.")
        return

    for nft in data["nft_items"]:
        name = nft.get("metadata", {}).get("name", "Без имени")
        img = nft.get("metadata", {}).get("image", "")
        link = nft.get("address", "")
        caption = f"🖼️ <b>{name}</b>
<code>{link}</code>"
        try:
            if img.endswith((".png", ".jpg", ".jpeg", ".gif", ".svg")):
                await update.message.reply_photo(img, caption=caption, parse_mode="HTML")
            else:
                await update.message.reply_text(caption, parse_mode="HTML")
        except Exception:
            await update.message.reply_text(caption, parse_mode="HTML")

async def cmd_scam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Используйте команду: /scamcheck <адрес>")
        return

    addr = context.args[0].strip()
    await update.message.reply_text("🛡️ Проверяю адрес…")
    data = api_get(f"accounts/{addr}")
    if data is None:
        await update.message.reply_text("⚠️ Не удалось получить данные.")
        return

    if data.get("is_scam"):
        reason = data.get("scam_info", {}).get("type", "Обозначен как скам")
        await update.message.reply_text(f"🚨 Адрес помечен как скам!
Причина: {reason}")
    else:
        await update.message.reply_text("✅ Адрес не помечен как скам.")

async def toggle_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in subscribed_users:
        subscribed_users.remove(uid)
        await update.message.reply_text("❌ Alerts выключены.")
    else:
        if uid not in user_wallets:
            await update.message.reply_text("❌ Сначала подключите кошелёк.")
            return
        subscribed_users.add(uid)
        await update.message.reply_text("🐋 Alerts включены.")

def get_big_txs(address: str, threshold=10000):
    data = api_get("transactions/account", {"account": address, "limit": 10})
    if not data or "transactions" not in data:
        return []
    big_txs = []
    for tx in data["transactions"]:
        try:
            val = float(tx.get("amount", 0)) / 1e9
            if val >= threshold:
                big_txs.append({"hash": tx.get("hash", ""), "value": val})
        except Exception:
            continue
    return big_txs

async def whale_alerts_loop(app: Application):
    while True:
        try:
            for uid in list(subscribed_users):
                w = user_wallets.get(uid)
                if not w:
                    continue
                big_txs = get_big_txs(w)
                for tx in big_txs:
                    try:
                        await app.bot.send_message(uid, f"🐋 Крупная транзакция:
{tx['value']} TON
Hash: {tx['hash'][:12]}...")
                    except Exception as e:
                        logger.error(f"Ошибка alert: {e}")
            await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Ошибка в loop: {e}")
            await asyncio.sleep(30)

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💰 Баланс":
        await cmd_balance(update, context)
    elif text == "🛡️ Скам-чек":
        await update.message.reply_text("Для проверки отправьте /scamcheck <адрес>")
    elif text == "🐋 Alerts ON/OFF":
        await toggle_alerts(update, context)
    elif text == "🧾 Показать кошелёк":
        await cmd_wallet(update, context)
    elif text == "🎨 NFT-проверка":
        await cmd_nfts(update, context)
    else:
        await update.message.reply_text("Неизвестная команда. Используйте меню.")

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("wallet", cmd_wallet))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("scamcheck", cmd_scam))
    app.add_handler(CommandHandler("alerts", toggle_alerts))
    app.add_handler(CommandHandler("nfts", cmd_nfts))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_router))
    asyncio.create_task(whale_alerts_loop(app))
    print("🤖 Бот запущен и работает!")
    await app.run_polling()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
