from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# Earning system text in HTML format for Telegram
EARNING_TEXT = """
<b>💰 TestAbd.uz’da Pul Ishlash – Oson va Qiziqarli! 💸</b>

TestAbd.uz loyihasida har bir harakatingiz uchun <b>coin</b> to‘plashingiz mumkin! Bu coinlar loyihaning daromadidan ulush olish imkonini beradi. Qanday qilib? Quyida barcha yo‘llarni tushuntiramiz! 👇

<b>📝 Coin Toplash Yo‘llari:</b>
• <b>Test ishlash:</b> Har bir testni muvaffaqiyatli yakunlasangiz, <b>1 coin</b> olasiz.
• <b>Savol yaratish:</b> Har bir yangi savol uchun <b>5 coin</b> beriladi.
• <b>Do‘st taklif qilish:</b>
  - Do‘stingiz sizning referral kodingiz orqali ro‘yxatdan o‘tsa, <b>10 coin</b>.
  - Do‘stingiz emailini tasdiqlasa, yana <b>5 coin</b>. Jami <b>15 coin</b>!
• <b>Ro‘yxatdan o‘tish:</b>
  - Referral kodsiz ro‘yxatdan o‘tsangiz, coin berilmaydi.
  - Referral kod bilan ro‘yxatdan o‘tsangiz, <b>5 coin</b>.
  - Emailingizni tasdiqlasangiz, har qanday holatda <b>5 coin</b>.
• <b>Obunachilar:</b> Har bir followeringiz uchun <b>1 coin</b>. Obunachilar soni o‘zgarsa, coinlaringiz ham mos ravishda o‘zgaradi (ko‘payadi yoki kamayadi).

<b>💵 Daramoddan Ulish:</b>
Loyiha daromad keltirganda, umumiy daromadning <b>50%</b>i foydalanuvchilar o‘rtasida taqsimlanadi! 😍
• Umumiy coinlar 100% deb olinadi.
• Sizning coinlaringiz umumiy coinlarning qancha foizini tashkil qilsa, daromadning o‘sha foizini olasiz.

<i>Misol:</i> Agar loyiha 1,000,000$ daromad keltirsa va sizning coinlaringiz umumiy coinlarning 5% ini tashkil qilsa, siz <b>25,000$</b> olasiz! <i>(va bu bir martalik emas har oylik daromad)</i>

<b>🚀 Bugun boshlang!</b> Testlar ishlang, savollar yarating, do‘stlaringizni taklif qiling va obunachilar to‘plang – har bir harakatingiz sizni katta daromadga yaqinlashtiradi! 💪

<i>TestAbd.uz – bu nafaqat bilim, balki daromad manbai! 🌟</i>
"""


async def EarnMoneyMenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("Pul ishlash")

    await update.callback_query.edit_message_text(
        text=EARNING_TEXT,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text="Asosiy Menyu", callback_data="Main_Menu")]])
    )
    return ConversationHandler.END