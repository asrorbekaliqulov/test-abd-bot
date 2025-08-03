import requests
import uuid
import os
from django.conf import settings
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta
from asgiref.sync import sync_to_async
from ..models.TelegramBot import TelegramUser
from ..utils import post_ad
from TestAbdBot.settings import BASE_API_URL


REFRESH_TOKEN_URL = f"{BASE_API_URL}accounts/token/refresh/"

# Bot states
TITLE, IMAGE, LINK, AD_TYPE, DAYS, TARGET_VIEWS, TARGET_CLICKS, PAYMENT = range(8)

async def Ads_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        text="Reklama bo'limiga xush kelibsiz",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(text='Reklama yaratish', callback_data='create_ad')]])
    )

async def create_ad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    try:
        telegram_user = await sync_to_async(TelegramUser.objects.get)(user_id=user.id)
        if not telegram_user.access_token:
            keyboard = [[InlineKeyboardButton("Tizimga kirish", callback_data="login")]]
            await query.message.reply_text(
                "Iltimos, avval tizimga kiring!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return ConversationHandler.END
        context.user_data['telegram_user'] = telegram_user
    except TelegramUser.DoesNotExist:
        keyboard = [[InlineKeyboardButton("Tizimga kirish", callback_data="login")]]
        await query.message.reply_text(
            "Siz ro'yxatdan o'tmagansiz!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END

    await query.message.reply_text("Reklama sarlavhasini kiriting:")
    return TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("Reklama rasmini yuboring:")
    return IMAGE

async def get_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    
    # Ensure static directory exists
    static_ads_dir = os.path.join(settings.STATIC_ROOT, 'ads')
    os.makedirs(static_ads_dir, exist_ok=True)
    
    # Generate unique filename and save to static/ads/
    file_name = f"{uuid.uuid4()}.jpg"
    file_path = os.path.join(static_ads_dir, file_name)
    await file.download_to_drive(file_path)
    
    # Store full path for POST request
    context.user_data['image_path'] = file_path
    await update.message.reply_text("Reklama havolasini (URL) kiriting:")
    return LINK

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['link'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("Kunlik", callback_data="DAILY")],
        [InlineKeyboardButton("Ko'rishlar", callback_data="VIEWS")],
        [InlineKeyboardButton("Bosishlar", callback_data="CLICKS")]
    ]
    await update.message.reply_text(
        "Reklama turini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return AD_TYPE

async def get_ad_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ad_type = query.data
    context.user_data['ad_type'] = ad_type

    if ad_type == 'DAILY':
        keyboard = [
            [InlineKeyboardButton(f"{days} kun", callback_data=str(days))]
            for days in [1, 3, 5, 7, 10]
        ]
        await query.message.reply_text(
            "Reklama muddatini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return DAYS
    elif ad_type == 'VIEWS':
        await query.message.reply_text("Maqsadli ko'rishlar sonini kiriting:")
        return TARGET_VIEWS
    else:  # CLICKS
        await query.message.reply_text("Maqsadli bosishlar sonini kiriting:")
        return TARGET_CLICKS

async def get_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    days = int(query.data)
    context.user_data['days'] = days
    start_date = datetime.now()
    end_date = start_date + timedelta(days=days)
    context.user_data['start_date'] = start_date.strftime('%Y-%m-%d')
    context.user_data['end_date'] = end_date.strftime('%Y-%m-%d')
    
    # Fetch pricing and calculate cost
    telegram_user = context.user_data['telegram_user']
    response, error = await make_api_request('GET', f"{BASE_API_URL}accounts/ad-pricings/", telegram_user)
    if error:
        keyboard = [[InlineKeyboardButton("Tizimga kirish", callback_data="login")]] if "kirish" in error else []
        await query.message.reply_text(error, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    try:
        pricings = response.json()
        if not pricings or len(pricings) != 1:
            await query.message.reply_text("Narxlar jadvali topilmadi yoki noto'g'ri!")
            return ConversationHandler.END
        selected_pricing = pricings[0]  # Only one pricing option
        context.user_data['pricing'] = selected_pricing['id']
        context.user_data['country'] = "Uzbekistan"  # Hardcode Uzbekistan
        
        # Calculate total price
        ad_type = context.user_data['ad_type']
        total_price = selected_pricing['price_per_day'] * days
        context.user_data['total_price'] = total_price
        
        await query.message.reply_text(
            f"Reklama narxi: {total_price} so'm\n"
            "Iltimos, quyidagi kartaga to'lov qiling va to'lov chekining skrinshotini yuboring:\n"
            "Karta: 1234 5678 9012 3456"
        )
        return PAYMENT
    except ValueError:
        print(f"API javobi JSON emas: {response.text[:100]}")
        await query.message.reply_text("API javobi noto'g'ri formatda!")
        return ConversationHandler.END

async def get_target_views(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target_views'] = int(update.message.text)
    context.user_data['target_clicks'] = None
    context.user_data['start_date'] = datetime.now().strftime('%Y-%m-%d')
    context.user_data['end_date'] = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')  # Default 7 days
    
    # Fetch pricing and calculate cost
    telegram_user = context.user_data['telegram_user']
    response, error = await make_api_request('GET', f"{BASE_API_URL}accounts/ad-pricings/", telegram_user)
    if error:
        keyboard = [[InlineKeyboardButton("Tizimga kirish", callback_data="login")]] if "kirish" in error else []
        await update.message.reply_text(error, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    try:
        pricings = response.json()
        if not pricings or len(pricings) != 1:
            await update.message.reply_text("Narxlar jadvali topilmadi yoki noto'g'ri!")
            return ConversationHandler.END
        selected_pricing = pricings[0]  # Only one pricing option
        context.user_data['pricing'] = selected_pricing['id']
        context.user_data['country'] = "Uzbekistan"  # Hardcode Uzbekistan
        
        # Calculate total price
        total_price = selected_pricing['price_per_view'] * context.user_data['target_views']
        context.user_data['total_price'] = total_price
        
        await update.message.reply_text(
            f"Reklama narxi: {total_price} so'm\n"
            "Iltimos, quyidagi kartaga to'lov qiling va to'lov chekining skrinshotini yuboring:\n"
            "Karta: 1234 5678 9012 3456"
        )
        return PAYMENT
    except ValueError:
        print(f"API javobi JSON emas: {response.text[:100]}")
        await update.message.reply_text("API javobi noto'g'ri formatda!")
        return ConversationHandler.END

async def get_target_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target_clicks'] = int(update.message.text)
    context.user_data['target_views'] = None
    context.user_data['start_date'] = datetime.now().strftime('%Y-%m-%d')
    context.user_data['end_date'] = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')  # Default 7 days
    
    # Fetch pricing and calculate cost
    telegram_user = context.user_data['telegram_user']
    response, error = await make_api_request('GET', f"{BASE_API_URL}accounts/ad-pricings/", telegram_user)
    if error:
        keyboard = [[InlineKeyboardButton("Tizimga kirish", callback_data="login")]] if "kirish" in error else []
        await update.message.reply_text(error, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    try:
        pricings = response.json()
        if not pricings or len(pricings) != 1:
            await update.message.reply_text("Narxlar jadvali topilmadi yoki noto'g'ri!")
            return ConversationHandler.END
        selected_pricing = pricings[0]  # Only one pricing option
        context.user_data['pricing'] = selected_pricing['id']
        context.user_data['country'] = "Uzbekistan"  # Hardcode Uzbekistan
        
        # Calculate total price
        total_price = selected_pricing['price_per_click'] * context.user_data['target_clicks']
        context.user_data['total_price'] = total_price
        
        await update.message.reply_text(
            f"Reklama narxi: {total_price} so'm\n"
            "Iltimos, quyidagi kartaga to'lov qiling va to'lov chekining skrinshotini yuboring:\n"
            "Karta: 1234 5678 9012 3456"
        )
        return PAYMENT
    except ValueError:
        print(f"API javobi JSON emas: {response.text[:100]}")
        await update.message.reply_text("API javobi noto'g'ri formatda!")
        return ConversationHandler.END

async def get_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Iltimos, to'lov chekining skrinshotini yuboring!")
        return PAYMENT

    # Store screenshot file_id (kept on Telegram's servers)
    context.user_data['payment_screenshot'] = update.message.photo[-1].file_id

    # Prepare data for POST request
    data = {
        'title': context.user_data['title'],
        'link': context.user_data['link'],
        'ad_type': context.user_data['ad_type'],
        'pricing': context.user_data['pricing'],
        'country': 1,
        'start_date': context.user_data['start_date'],
        'end_date': context.user_data['end_date'],
    }
    if 'target_views' in context.user_data and context.user_data['target_views']:
        data['target_views'] = context.user_data['target_views']
    if 'target_clicks' in context.user_data and context.user_data['target_clicks']:
        data['target_clicks'] = context.user_data['target_clicks']

    telegram_user = context.user_data['telegram_user']
    success, ad_order, error = await post_ad(data, telegram_user, context.user_data['image_path'])
    if not success:
        keyboard = [[InlineKeyboardButton("Tizimga kirish", callback_data="login")]] if "kirish" in error else []
        await update.message.reply_text(error, reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END

    # Send ad details and screenshot to admins
    admin_ids = await TelegramUser.get_admin_ids()
    ad_details = (
        f"Yangi reklama so'rovi:\n"
        f"Sarlavha: {ad_order['title']}\n"
        f"ID: {ad_order['id']}\n"
        f"Havola: {ad_order['link']}\n"
        f"Turi: {ad_order['ad_type']}\n"
        f"Mamlakat: {ad_order['country_name']}\n"
        f"Narxlar jadvali: {ad_order['pricing_details']['name']}\n"
        f"Boshlanish sanasi: {ad_order['start_date']}\n"
        f"Tugash sanasi: {ad_order['end_date']}\n"
        f"Umumiy narx: {context.user_data['total_price']} so'm"
    )
    if ad_order['target_views']:
        ad_details += f"\nMaqsadli ko'rishlar: {ad_order['target_views']}"
    if ad_order['target_clicks']:
        ad_details += f"\nMaqsadli bosishlar: {ad_order['target_clicks']}"

    keyboard = [
        [
            InlineKeyboardButton(text="Tasdiqlash", callback_data="ApprovedAds"),
            InlineKeyboardButton(text="Bekor qilish", callback_data="DisapprovedAds")
        ]
        [
            InlineKeyboardButton("To'lov chekini ko'rish", callback_data=f"check_payment_{ad_order['id']}")
        ]
    ]
    for admin_id in admin_ids:
        await context.bot.send_message(admin_id, ad_details, reply_markup=InlineKeyboardMarkup(keyboard))
        await context.bot.send_photo(admin_id, context.user_data['payment_screenshot'])

    await update.message.reply_text("Reklama so'rovingiz adminga yuborildi! Tasdiq kuting.")
    return ConversationHandler.END

async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ad_id = query.data.split('_')[-1]
    telegram_user = context.user_data.get('telegram_user')
    if not telegram_user:
        await query.message.reply_text("Tizimga qaytadan kiring!")
        return

    # Re-send the screenshot for the ad
    if 'payment_screenshot' in context.user_data:
        await query.message.reply_photo(context.user_data['payment_screenshot'], caption=f"Reklama ID: {ad_id}")
    else:
        await query.message.reply_text("To'lov cheki topilmadi!")

async def login_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Iltimos, tizimga qaytadan kiring!")
    # Implement your login flow here (e.g., redirect to auth URL or collect credentials)

async def make_api_request(method, url, telegram_user, data=None, files=None):
    headers = {"Authorization": f"Bearer {telegram_user.access_token}", "Content-Type": "application/json"}
    try:
        response = requests.request(method, url, headers=headers, json=data, files=files)
        print(f"API so'rovi: {url}, Status: {response.status_code}, Javob: {response.text[:100]}")
        if response.status_code == 401:
            refresh_response = requests.post(REFRESH_TOKEN_URL, json={"refresh_token": telegram_user.refresh_token})
            print(f"Token yangilash: Status {refresh_response.status_code}, Javob: {refresh_response.text[:100]}")
            if refresh_response.status_code == 200:
                token_data = refresh_response.json()
                telegram_user.access_token = token_data['access_token']
                telegram_user.refresh_token = token_data.get('refresh_token', telegram_user.refresh_token)
                await sync_to_async(telegram_user.save)()
                headers = {"Authorization": f"Bearer {telegram_user.access_token}", "Content-Type": "application/json"}
                response = requests.request(method, url, headers=headers, json=data, files=files)
                print(f"Qayta so'rov: {url}, Status: {response.status_code}, Javob: {response.text[:100]}")
            else:
                telegram_user.access_token = None
                telegram_user.refresh_token = None
                await sync_to_async(telegram_user.save)()
                return None, "Tizimga qaytadan kiring!"
        if response.status_code == 404:
            return None, "API manzili topilmadi (404 xatosi). Administrator bilan bog'laning!"
        if response.status_code != 200:
            return None, f"API xatosi: Status {response.status_code}, Xabar: {response.text[:100]}"
        return response, None
    except Exception as e:
        print(f"API so'rovida xato: {e}")
        return None, "API so'rovida xatolik yuz berdi!"


Ads_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(create_ad, pattern='^create_ad$')],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
        IMAGE: [MessageHandler(filters.PHOTO, get_image)],
        LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_link)],
        AD_TYPE: [CallbackQueryHandler(get_ad_type)],
        DAYS: [CallbackQueryHandler(get_days)],
        TARGET_VIEWS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_target_views)],
        TARGET_CLICKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_target_clicks)],
        PAYMENT: [MessageHandler(filters.PHOTO, get_payment_screenshot)],
    },
    fallbacks=[],
)