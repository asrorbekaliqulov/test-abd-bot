from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from asgiref.sync import sync_to_async
from .models.TelegramBot import Channel, TelegramUser
from telegram.constants import ChatAction
from .utils import save_user_to_db

lists = ["administrator", "member", "creator"]


def admin_required(func):
    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user_id = update.effective_user.id
        # Adminni tekshirish
        try:
            user = await TelegramUser.objects.aget(
                user_id=user_id
            )  # Django ORM ning asinxron `aget` metodi
            if not user.is_admin:
                await context.bot.send_message(
                    chat_id=user_id, text="Siz admin emassiz!😠"
                )
                return ConversationHandler.END

        except TelegramUser.DoesNotExist:
            await context.bot.send_message(
                chat_id=user_id, text="Sizning ma'lumotlaringiz topilmadi.\n/start"
            )
            return ConversationHandler.END

        # Agar admin bo‘lsa, funksiya chaqiriladi
        return await func(update, context, *args, **kwargs)

    return wrapper


# Barcha Channel ma'lumotlarini olish uchun asinxron funksiya
@sync_to_async
def get_all_channels():
    return list(Channel.objects.all())  # QuerySet ni ro'yxatga aylantirish


# Foydalanuvchi kanalga a'zo ekanligini tekshirish uchun dekorator
def mandatory_channel_required(func):
    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        user_id = update.effective_user.id

        try:
            # Foydalanuvchini bazadan topish
            user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
            user_id = user.user_id

            # InlineKeyboard uchun tugmalar yaratish
            keyboards = []

            # Barcha kanallarni olish
            channels = await get_all_channels()

            # Har bir kanal uchun tugma yaratish
            for channel in channels:
                keyboards.append(
                    [InlineKeyboardButton(text=f"{channel.name}", url=f"{channel.url}")]
                )

            # Foydalanuvchi kanalga a'zo ekanligini tekshirish
            for channel in channels:
                try:
                    # Foydalanuvchi statusini tekshirish
                    is_member = await context.bot.get_chat_member(
                        chat_id=channel.channel_id, user_id=user_id
                    )
                    if is_member.status in ["member", "administrator", "creator"]:
                        continue
                    else:
                        # Agar foydalanuvchi kanalga a'zo bo'lmasa, xabar yuborish
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="Iltimos, botdan to'liq foydalanish uchun quyidagi kanallarga a'zo bo'ling:",
                            reply_markup=InlineKeyboardMarkup(keyboards),
                        )
                        return  # Funksiyani to'xtatish
                except Exception as e:
                    print(f"Xatolik: {e}")
                    continue

        except TelegramUser.DoesNotExist:
            # Agar foydalanuvchi topilmasa, xabar yuborish
            data = update.effective_user
            is_save = await save_user_to_db(data)
            return await func(update, context, *args, **kwargs)

        # Agar foydalanuvchi barcha kanallarga a'zo bo'lsa, asosiy funksiyani davom ettirish
        return await func(update, context, *args, **kwargs)

    return wrapper


def typing_action(func):
    @wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        await context.bot.send_chat_action(
            chat_id=update.effective_user.id, action=ChatAction.TYPING
        )
        return await func(update, context, *args, **kwargs)

    return wrapper


def telegram_auth_required():
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            telegram_id = update.effective_user.id
            try:
                user = await sync_to_async(TelegramUser.objects.get)(user_id=telegram_id)
                if user.is_authenticated():
                    return await func(update, context, *args, **kwargs)
            except TelegramUser.DoesNotExist:
                pass

            # Auth yo'q bo'lsa - foydalanuvchiga ro'yxatdan o'tish tugmasi
            keyboard = [
                [InlineKeyboardButton("🔐 Tizimga kirish", callback_data="LoginTestAbd")],
                [InlineKeyboardButton("📜 Ro'yxatdan o'tish", url="https://testabd.uz/register")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "<b>Assalomu alaykum?</b>\nBotdan foydalanishingiz uchun avval tizimga kirishingiz kerak.\n\nTestAbd.uz platformasida ro'yxatdan o'ting va botga kirish uchun quyidagi <b>🔐 Tizimga kirish</b> tugmasini bosing.",
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            return

        return wrapper
    return decorator



