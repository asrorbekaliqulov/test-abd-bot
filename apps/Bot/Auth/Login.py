from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler
from ..models.TelegramBot import TelegramUser
from asgiref.sync import sync_to_async
import requests
from TestAbdBot.settings import BASE_API_URL

BASE_URL = BASE_API_URL

async def StartLogin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Bot login funksiyasi.
    Foydalanuvchini botga kirishi uchun TestAbd.uz saytidan autentifikatsiya qilish
    """
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Siz TestAbd.uz tizimiga kirmoqdasiz. Iltimos, TestAbd.uz foydalanuvchi nomingizni kiriting.",
    )
    return "login_username"

async def LoginUsername(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Foydalanuvchi TestAbd.uz foydalanuvchi nomini kiritadi.
    """
    username = update.message.text.strip()
    url = f"{BASE_URL}accounts/check-username/?username={username}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get("available") is False:
            context.user_data["username"] = username
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"<blockquote>username={username},</blockquote> \nTestAbd.uz parolingizni kiriting.",
                parse_mode="html",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Bekor qilish", callback_data="Main_Menu")]
                ])
            )
            return "login_password"
        else:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text="Kiritilgan foydalanuvchi nomi topilmadi. Iltimos, qayta urinib ko'ring.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Bekor qilish", callback_data="Main_Menu")]
                ])
            )
            return "login_username"
    else:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="TestAbd.uz serveriga ulanishda xatolik yuz berdi. Iltimos, keyinroq qayta urinib ko'ring.",
        )
        return ConversationHandler.END

async def LoginPassword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Foydalanuvchi TestAbd.uz parolini kiritadi.
    """
    password = update.message.text.strip()
    username = context.user_data.get("username")
    
    if not username:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Foydalanuvchi nomi topilmadi. Iltimos, qayta urinib ko'ring.",
        )
        return "login_username"

    url = f"{BASE_URL}accounts/login/"
    data = {
        "username": username,
        "password": password
    }
    
    response = requests.post(url, data=data)
    print(f"Login response: {response.status_code}, {response.json()}")  # Debugging line
    if response.status_code == 200:
        data = response.json()
        access_token = data.get("access")
        refresh_token = data.get("refresh")
        # Foydalanuvchini bazaga saqlash yoki yangilash
        update_user = await sync_to_async(TelegramUser.objects.update_or_create)(
            user_id=update.effective_user.id,
            defaults={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "is_active": True,
            }
        )
        context.user_data["access_token"] = access_token
        context.user_data["refresh_token"] = refresh_token
        
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="TestAbd.uz tizimiga muvaffaqiyatli kirildi!\n/start buyrug'ini yuboring",
        )
        return ConversationHandler.END
    else:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="Parol noto'g'ri yoki nomalum xatolik ro'y berdi. Iltimos, qayta urinib ko'ring.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Bekor qilish", callback_data="cancel")]
            ])
        )
        return "login_password"


login_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(StartLogin, pattern='^LoginTestAbd$')],
    states={
        "login_username": [MessageHandler(filters.TEXT & ~filters.COMMAND, LoginUsername)],
        "login_password": [MessageHandler(filters.TEXT & ~filters.COMMAND, LoginPassword)],
    },
    fallbacks=[],
)
