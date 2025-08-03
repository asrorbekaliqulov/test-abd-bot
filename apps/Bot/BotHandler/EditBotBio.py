from telegram import Update
from telegram.ext import ContextTypes
from ..utils import quotes


async def edit_bot_bio(update: Update | None, context: ContextTypes.DEFAULT_TYPE):
    """
    Botni bio ma'lumotini o'zgartirish uchun komanda.
    """
    try:
        quote = quotes()
        quote_message = f"{quote['quote']}\n\n{quote['author']}"
        await context.bot.set_my_short_description(quote_message)
    except Exception as e:
        description = "Dunyodagi barcha davlatlar haqida ma'lumot beruvchi telegram bot"
        await context.bot.set_my_short_description(description)
