from telegram.ext import ContextTypes, ConversationHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from ..utils import save_user_to_db, quotes
from ..models.TelegramBot import TelegramUser
from ..decorators import typing_action, mandatory_channel_required, telegram_auth_required
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from TestAbdBot.settings import BASE_API_URL
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async
import requests
import re



# API settings (replace with your actual API URL and token)
API_BASE_URL = f"{BASE_API_URL}system/system-config/"


@sync_to_async
def fetch_system_config(user_id):
    """Synchronously fetch SystemConfig from the API."""

    try:
        user = TelegramUser.objects.get(user_id=user_id)
        API_TOKEN = user.access_token
        headers = {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}
        response = requests.get(API_BASE_URL, headers=headers, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching SystemConfig: {e}")
        return None



async def get_user_keyboard(user_id):
    """Bot uchun inline keyboardni dinamik yaratish."""
    config = await fetch_system_config(user_id)

    # Agar maintenance_mode True bo'lsa, hech qanday tugma yuborilmaydi
    if config and config.get("maintenance_mode", True):
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📞 Murojaat", callback_data="appeal")]])

    # Profilim tugmasi bir o'zi birinchi qatorda
    users_keyboards = [
        [
            InlineKeyboardButton(text="📊 Profilim", callback_data="profile_main"),
        ],
    ]

    # Qolgan tugmalar ikki qatordan joylashadi
    other_buttons = []

    # enable_monetization bo'yicha tugma
    if config and config.get("enable_monetization", False):
        other_buttons.append(
            InlineKeyboardButton(text="💰 Pul ishlash", callback_data="earn_money")
        )

    # enable_subscription bo'yicha tugma
    if config and config.get("enable_subscription", False):
        other_buttons.append(
            InlineKeyboardButton(text="📑 Obunalar", callback_data="subscriptions")
        )

    # enable_ads bo'yicha tugma
    if config and config.get("enable_ads", False):
        other_buttons.append(
            InlineKeyboardButton(text="💠 Reklama boshqarish", callback_data="setAds")
        )

    # enable_realtime_notifications bo'yicha tugma
    if config and config.get("enable_realtime_notifications", False):
        other_buttons.append(
            InlineKeyboardButton(text="🔔 Bildirishnomalar", callback_data="notifications")
        )

    # Doim ko'rinadigan tugmalar
    other_buttons.append(
        InlineKeyboardButton(text="ℹ️ Qo'llanma", callback_data="getGuide")
    )
    other_buttons.append(
        InlineKeyboardButton(text="📞 Murojaat", callback_data="appeal")
    )

    # Tugmalarni ikki qatordan joylashtirish
    for i in range(0, len(other_buttons), 2):
        row = other_buttons[i:i+2]
        users_keyboards.append(row)

    return InlineKeyboardMarkup(users_keyboards)

@typing_action
@mandatory_channel_required
@telegram_auth_required()
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Botni ishga tushirish uchun komanda.
    """
    remove = ReplyKeyboardRemove()
    data = update.effective_user
    if update.callback_query:
        await update.callback_query.answer("Asosiy menyu")
        await update.callback_query.delete_message()
    reply_markup = await get_user_keyboard(update.effective_user.id)
    is_save = await save_user_to_db(data)
    admin_id = await TelegramUser.get_admin_ids()
    if update.effective_user.id in admin_id:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="<b>Main Menu 🖥\n<tg-spoiler>/admin_panel</tg-spoiler></b>",
            reply_markup=remove,
            parse_mode="html",
        )
    quote = quotes()
    quote_message = f"<b>{quote['quote']}</b>\n\n<i>{quote['author']}</i>"
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=f"<b>Assalomu alaykum 👋</b>\n\n<blockquote>Mativatsiya: {quote_message}</blockquote>\n\nTestAbd.uz – bu nafaqat bilim, balki daromad manbai! 🌟",
        parse_mode="html",
        reply_markup=reply_markup,
    )
    return ConversationHandler.END
