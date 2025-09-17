from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup
)
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from ..models.TelegramBot import TelegramUser
from TestAbdBot.settings import BASE_API_URL
import requests, re
from asgiref.sync import sync_to_async

# --- States ---
AMOUNT, METHOD, CARD_NUMBER, PHONE_NUMBER = range(4)

# --- Helpers ---
def luhn_checksum(card_number: str) -> bool:
    def digits_of(n): return [int(d) for d in n]
    digits = digits_of(card_number)
    odd_sum = sum(digits[-1::-2])
    even_sum = 0
    for d in digits[-2::-2]:
        doubled = d * 2
        even_sum += sum(digits_of(str(doubled)))
    return (odd_sum + even_sum) % 10 == 0

def detect_card_type(card_number: str) -> str:
    if re.match(r'^4', card_number): return "VISA"
    if re.match(r'^(5[1-5]|2(2[2-9]|[3-6]\d|7[01]|720))', card_number): return "MASTERCARD"
    if re.match(r'^(8600|8601|8602)', card_number): return "UZCARD"
    if re.match(r'^(9860)', card_number): return "HUMO"
    return "UNKNOWN"

def is_valid_phone(phone: str) -> bool:
    return bool(re.fullmatch(r'\+998\d{9}', phone))

# --- API calls ---
@sync_to_async
def fetch_user_coin(user_id: int):
    try:
        tg_user = TelegramUser.objects.get(user_id=user_id)
        API_TOKEN = tg_user.access_token
        headers = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}
        response = requests.get(f"{BASE_API_URL}accounts/user-balance/", headers=headers, timeout=5)
        response.raise_for_status()
        return response.json()  # {'username': '...', 'balance': 12345}
    except Exception as e:
        print(f"Error fetch_user_coin: {e}")
        return None

@sync_to_async
def withdraw_request(token: str, amount: int):
    url = f"{BASE_API_URL}accounts/withdraw-coin/"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"amount": amount}
    resp = requests.post(url, json=payload, headers=headers)
    return resp.status_code, resp.json() if resp.content else {}

# --- User Flow ---
async def EarnMoneyMenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start withdrawal: fetch balance"""
    user = update.effective_user
    user_data = await fetch_user_coin(user.id)
    if not user_data:
        await update.callback_query.answer("Xatolik: balans olinmadi.")
        return ConversationHandler.END

    balance = user_data["balance"]
    context.user_data["balance"] = balance
    context.user_data["username"] = user_data["username"]

    await update.callback_query.edit_message_text(
        text=f"<b>1 Coin = 1 So'm</b>\n\n"
             f"Hisobingiz: <b>{balance}</b> coin\n"
             f"Yechmoqchi bo‘lgan summani kiriting.\n\n"
             f"<i>Minimal yechish miqdori 5000 coin</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton(text=str(balance))]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return AMOUNT

async def amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not re.fullmatch(r"\d+", text):
        await update.message.reply_text("Faqat son kiriting. Masalan: 10000")
        return AMOUNT

    amount = int(text)
    balance = context.user_data.get("balance", 0)

    if amount < 5000:
        await update.message.reply_text("Minimal yechish miqdori 5000 coin.")
        return AMOUNT
    if amount > balance:
        await update.message.reply_text(f"Balansingizda {balance} coin bor. Shu yoki undan kam miqdor kiriting.")
        return AMOUNT

    context.user_data["withdraw_amount"] = amount
    keyboard = [[
        InlineKeyboardButton("💳 Karta", callback_data="method_card"),
        InlineKeyboardButton("📱 Telefon", callback_data="method_phone")
    ]]
    await update.message.reply_text("To‘lov usulini tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))
    return METHOD

async def method_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "method_card":
        await query.edit_message_text("Karta raqamini kiriting (raqamlar, bo‘sh joysiz):")
        return CARD_NUMBER
    else:
        await query.edit_message_text("Telefon raqamingizni +998XXXXXXXXX formatida kiriting:")
        return PHONE_NUMBER

async def card_number_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = re.sub(r"\s+", "", update.message.text)
    if not re.fullmatch(r"\d{12,19}", text) or not luhn_checksum(text):
        await update.message.reply_text("Karta raqami noto‘g‘ri. Qayta urinib ko‘ring.")
        return CARD_NUMBER

    context.user_data["method"] = "card"
    context.user_data["card_number"] = text
    context.user_data["card_type"] = detect_card_type(text)

    await notify_admins_withdraw_request(update, context)
    await update.message.reply_text("✅ So‘rovingiz adminlarga yuborildi. Tez orada ko‘rib chiqiladi.")
    return ConversationHandler.END

async def phone_number_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not is_valid_phone(text):
        await update.message.reply_text("Telefon raqam noto‘g‘ri. Masalan: +998901234567")
        return PHONE_NUMBER

    context.user_data["method"] = "phone"
    context.user_data["phone"] = text

    await notify_admins_withdraw_request(update, context)
    await update.message.reply_text("✅ So‘rovingiz adminlarga yuborildi.")
    return ConversationHandler.END

# --- Notify Admins ---
async def notify_admins_withdraw_request(update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = user.id
    username = context.user_data["username"]
    balance = context.user_data["balance"]
    amount = context.user_data["withdraw_amount"]
    method = context.user_data["method"]

    details = ""
    if method == "card":
        details = f"Karta: {context.user_data['card_type']} (**** {context.user_data['card_number'][-4:]})"
    else:
        details = f"Telefon: {context.user_data['phone']}"

    text = (
        f"📢 <b>Yangi pul yechish so‘rovi</b>\n"
        f"👤 @{username} (id: {uid})\n"
        f"💰 Balans: {balance}\n"
        f"💵 So‘ralgan: {amount}\n"
        f"<code>{details}</code>"
    )

    keyboard = [[
        InlineKeyboardButton("✅ To‘lov qilindi", callback_data=f"admin_pay_{uid}_{amount}_{username}"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data=f"admin_cancel_{uid}_{amount}_{username}")
    ]]
    admin_ids = await TelegramUser.get_admin_ids()
    for admin_id in admin_ids:
        try:
            await context.bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            print(f"Admin xabarida xato: {e}")

# --- Conversation ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operatsiya bekor qilindi.")
    return ConversationHandler.END

Withdraw_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(EarnMoneyMenu, pattern=r"^earn_money")],
    states={
        AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_received)],
        METHOD: [CallbackQueryHandler(method_chosen)],
        CARD_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, card_number_received)],
        PHONE_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_number_received)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
)


from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from asgiref.sync import sync_to_async
from ..models.TelegramBot import TelegramUser
from TestAbdBot.settings import BASE_API_URL
import requests

# States
ADMIN_WAIT_PHOTO, ADMIN_WAIT_REASON = range(2)

# --- API call ---
@sync_to_async
def withdraw_request(token: str, amount: int):
    url = f"{BASE_API_URL}accounts/withdraw-coin/"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"amount": amount}
    resp = requests.post(url, json=payload, headers=headers)
    return resp.status_code, resp.json() if resp.content else {}

# --- Admin Button Handler ---
async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("admin_pay_"):
        _, _, uid, amount, username = data.split("_", 4)
        context.user_data["pay_target"] = {"uid": int(uid), "amount": int(amount), "username": username}

        await query.edit_message_text(
            f"✅ Foydalanuvchi @{username} uchun {amount} so‘m to‘lov qilindi.\n"
            "📷 To‘lov chek rasmini yuboring:"
        )
        return ADMIN_WAIT_PHOTO

    elif data.startswith("admin_cancel_"):
        _, _, uid, amount, username = data.split("_", 4)
        context.user_data["cancel_target"] = {"uid": int(uid), "amount": int(amount), "username": username}

        await query.edit_message_text(
            f"❌ Foydalanuvchi @{username} uchun {amount} so‘m so‘rov bekor qilindi.\n"
            "✍️ Sababni yuboring:"
        )
        return ADMIN_WAIT_REASON

    return ConversationHandler.END

# --- Admin sends photo (after pay) ---
async def admin_photo_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "pay_target" not in context.user_data:
        await update.message.reply_text("❗ Avval to‘lov so‘rovini tanlang.")
        return ConversationHandler.END

    target = context.user_data["pay_target"]
    uid = target["uid"]
    amount = target["amount"]
    username = target["username"]

    # Photo file_id
    photo = update.message.photo[-1].file_id

    # foydalanuvchiga yuborish
    await context.bot.send_photo(
        chat_id=uid,
        photo=photo,
        caption=f"✅ To‘lov amalga oshirildi!\n💵 Miqdor: {amount} so‘m\n"
                f"🛡️ Admin tomonidan tasdiqlandi."
    )

    # backend withdraw-coin
    tg_user = await TelegramUser.objects.aget(user_id=uid)
    token = tg_user.access_token
    status, resp = await withdraw_request(token, amount)
    print(f"Withdraw response: {status} {resp}")

    await update.message.reply_text("✅ To‘lov tasdiqlandi va foydalanuvchiga yuborildi.")
    context.user_data.pop("pay_target", None)
    return ConversationHandler.END

# --- Admin sends cancel reason ---
async def admin_text_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "cancel_target" not in context.user_data:
        await update.message.reply_text("❗ Avval bekor qilish so‘rovini tanlang.")
        return ConversationHandler.END

    target = context.user_data["cancel_target"]
    uid = target["uid"]
    amount = target["amount"]
    username = target["username"]

    reason = update.message.text

    await context.bot.send_message(
        chat_id=uid,
        text=f"❌ Sizning {amount} so‘m yechish so‘rovingiz bekor qilindi.\n\n"
             f"📝 Sabab: {reason}"
    )

    await update.message.reply_text("❌ Bekor qilish sababi foydalanuvchiga yuborildi.")
    context.user_data.pop("cancel_target", None)
    return ConversationHandler.END

# --- Cancel fallback ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operatsiya bekor qilindi.")
    return ConversationHandler.END

# --- Admin ConversationHandler ---
AdminWithdraw_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(admin_button_handler, pattern=r"^admin_")],
    states={
        ADMIN_WAIT_PHOTO: [MessageHandler(filters.PHOTO, admin_photo_listener)],
        ADMIN_WAIT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_listener)],
    },
    fallbacks=[MessageHandler(filters.COMMAND, cancel)],
)
