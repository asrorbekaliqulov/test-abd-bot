from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import requests
from ..models.TelegramBot import TelegramUser
from io import BytesIO
from datetime import datetime
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from TestAbdBot.settings import BASE_API_URL

PROFILE, STATS = range(2)

PROFILE, STATS, CATEGORIES, LOCATION = range(4)

async def MyProfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /profile command or profile_main callback to display user profile."""
    user_id = update.effective_user.id
    query = update.callback_query
    if query:
        await query.answer("Yuklanmoqda...")

    try:
        # Fetch user data if not cached
        data = context.user_data.get('profile_data')
        if not data:
            user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
            headers = {"Authorization": f"Bearer {user.access_token}"}
            url = f"{BASE_API_URL}accounts/me/"

            response = await sync_to_async(requests.get)(url, headers=headers)

            if response.status_code == 401:
                refresh_response = await sync_to_async(requests.post)(
                    f"{BASE_API_URL}accounts/token/refresh/", 
                    json={"refresh": user.refresh_token}
                )
                if refresh_response.status_code == 200:
                    tokens = refresh_response.json()
                    user.access_token = tokens['access']
                    await sync_to_async(user.save)()
                    headers["Authorization"] = f"Bearer {user.access_token}"
                    response = await sync_to_async(requests.get)(url, headers=headers)
                else:
                    if query:
                        await query.message.reply_text("❌ Token yangilashda xatolik yuz berdi.")
                    else:
                        await update.message.reply_text("❌ Token yangilashda xatolik yuz berdi.")
                    return ConversationHandler.END

            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}")

            data = response.json()
            context.user_data['profile_data'] = data

        join_date = datetime.fromisoformat(data['join_date']).strftime("%Y-%m-%d")

        # Profile text
        text = f"""👤 <b>{data['first_name']} {data['last_name'] if data['first_name'] or data['last_name'] else 'TestAbd foydalanuvchisi'}</b>
📛 <b>Username:</b> <a href='https://testabd.uz/profile/{data['username']}'>@{data['username']}</a>
🎖️ <b>Level:</b> {data.get('level', 'Nomaʼlum')}
⚖️ <b>Ulushi:</b> {data['coin_percentage']}%
🪙 <b>Coinlari:</b> {data.get('coins', 0)} ta
🗓 <b>Qo'shilgan sana:</b> {join_date}

ℹ️ <b>Biografiya:</b> {data.get('bio', "Yozilmagan")}"""

        # Buttons in two-column layout
        keyboard = [
            [InlineKeyboardButton("📊 Statistika", callback_data="profile_stats"),
             InlineKeyboardButton("🎯 Qiziqishlar", callback_data="profile_categories")],
            [InlineKeyboardButton("📍 Joylashuv", callback_data="profile_location"),
             InlineKeyboardButton("✏️ Profilni tahrirlash", callback_data="edit_profile")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="Main_Menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Profile image handling
        profile_image_url = data.get("profile_image")
        context.user_data['profile_image_url'] = profile_image_url  # Cache image URL

        if query:
            if profile_image_url:
                try:
                    if profile_image_url.startswith("http://192.") or "localhost" in profile_image_url or "127.0.0.1" in profile_image_url:
                        image_response = await sync_to_async(requests.get)(profile_image_url)
                        image_response.raise_for_status()
                        image_data = BytesIO(image_response.content)
                        await query.message.edit_media(
                            media=InputMediaPhoto(media=image_data, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                            reply_markup=reply_markup
                        )
                    else:
                        await query.message.edit_media(
                            media=InputMediaPhoto(media=profile_image_url, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                            reply_markup=reply_markup
                        )
                except Exception as e:
                    print("Rasmni tahrirlashda xatolik:", e)
                    await query.edit_message_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            else:
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        else:
            if profile_image_url:
                try:
                    if profile_image_url.startswith("http://192.") or "localhost" in profile_image_url or "127.0.0.1" in profile_image_url:
                        image_response = await sync_to_async(requests.get)(profile_image_url)
                        image_response.raise_for_status()
                        image_data = BytesIO(image_response.content)
                        image_data.name = "profile.jpg"
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=image_data,
                            caption=f"Profil rasmi👆👆👆\n\n{text}",
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                    else:
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=profile_image_url,
                            caption=f"Profil rasmi👆👆👆\n\n{text}",
                            reply_markup=reply_markup,
                            parse_mode='HTML'
                        )
                except Exception as e:
                    print("Rasmni yuborishda xatolik:", e)
                    await update.message.reply_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )

    except ObjectDoesNotExist:
        if query:
            await query.message.reply_text("❌ Foydalanuvchi topilmadi.")
        else:
            await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        if query:
            await query.message.reply_text(f"❌ Ma'lumotlarni olishda xatolik yuz berdi: {str(e)}")
        else:
            await update.message.reply_text(f"❌ Ma'lumotlarni olishda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

    return PROFILE

async def profile_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the profile_stats callback to display user statistics."""
    query = update.callback_query
    await query.answer("Statistika yuklanmoqda...")
    user_id = update.effective_user.id

    try:
        # Check if profile data is cached
        data = context.user_data.get('profile_data')
        if not data:
            user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
            headers = {"Authorization": f"Bearer {user.access_token}"}
            url = f"{BASE_API_URL}accounts/me/"

            response = await sync_to_async(requests.get)(url, headers=headers)

            if response.status_code == 401:
                refresh_response = await sync_to_async(requests.post)(
                    f"{BASE_API_URL}accounts/token/refresh/", 
                    json={"refresh": user.refresh_token}
                )
                if refresh_response.status_code == 200:
                    tokens = refresh_response.json()
                    user.access_token = tokens['access']
                    await sync_to_async(user.save)()
                    headers["Authorization"] = f"Bearer {user.access_token}"
                    response = await sync_to_async(requests.get)(url, headers=headers)
                else:
                    await query.message.reply_text("❌ Token yangilashda xatolik yuz berdi.")
                    return ConversationHandler.END

            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}")

            data = response.json()
            context.user_data['profile_data'] = data

        # Format weekly test count
        weekly_tests = data.get('weekly_test_count', {})
        weekly_text = "\n".join([f"  • <b>{day}</b>: {count} ta" for day, count in weekly_tests.items()])

        # Statistics message
        text = f"""📊 <b>{data['first_name']} {data['last_name'] if data['first_name'] or data['last_name'] else 'TestAbd foydalanuvchisi'} uchun statistika</b>

🎖️ <b>Level:</b> {data.get('level', 'Nomaʼlum')}
🪙 <b>Coinlari:</b> {data.get('coins', 0)} ta
⚖️ <b>Ulushi:</b> {data['coin_percentage']}%
✅ <b>To‘g‘ri javoblar:</b> {data.get('correct_count', 0)} ta
❌ <b>Noto‘g‘ri javoblar:</b> {data.get('wrong_count', 0)} ta
📝 <b>Yechilgan testlar:</b> {data.get('tests_solved', 0)} ta
⏱️ <b><s>O‘rtacha vaqt:</b> {data.get('average_time', 0)} sekund</s>
🔥 <b>Streak kunlari:</b> {data.get('streak_day', 0)} kun
📅 <b>Haftalik testlar:</b>
{weekly_text}"""

        # Buttons in two-column layout
        keyboard = [
            [InlineKeyboardButton("👤 Profil", callback_data="profile_main"),
             InlineKeyboardButton("🎯 Qiziqishlar", callback_data="profile_categories")],
            [InlineKeyboardButton("📍 Joylashuv", callback_data="profile_location"),
             InlineKeyboardButton("✏️ Profilni tahrirlash", callback_data="edit_profile")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="Main_Menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Profile image handling
        profile_image_url = context.user_data.get('profile_image_url')

        if profile_image_url:
            try:
                if profile_image_url.startswith("http://192.") or "localhost" in profile_image_url or "127.0.0.1" in profile_image_url:
                    image_response = await sync_to_async(requests.get)(profile_image_url)
                    image_response.raise_for_status()
                    image_data = BytesIO(image_response.content)
                    await query.message.edit_media(
                        media=InputMediaPhoto(media=image_data, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                        reply_markup=reply_markup
                    )
                else:
                    await query.message.edit_media(
                        media=InputMediaPhoto(media=profile_image_url, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print("Rasmni tahrirlashda xatolik:", e)
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    except ObjectDoesNotExist:
        await query.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Ma'lumotlarni olishda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

    return STATS

async def profile_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the profile_categories callback to display user interests."""
    query = update.callback_query
    await query.answer("Qiziqishlar yuklanmoqda...")
    user_id = update.effective_user.id

    try:
        # Check if profile data is cached
        data = context.user_data.get('profile_data')
        if not data:
            user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
            headers = {"Authorization": f"Bearer {user.access_token}"}
            url = f"{BASE_API_URL}accounts/me/"

            response = await sync_to_async(requests.get)(url, headers=headers)

            if response.status_code == 401:
                refresh_response = await sync_to_async(requests.post)(
                    f"{BASE_API_URL}accounts/token/refresh/", 
                    json={"refresh": user.refresh_token}
                )
                if refresh_response.status_code == 200:
                    tokens = refresh_response.json()
                    user.access_token = tokens['access']
                    await sync_to_async(user.save)()
                    headers["Authorization"] = f"Bearer {user.access_token}"
                    response = await sync_to_async(requests.get)(url, headers=headers)
                else:
                    await query.message.reply_text("❌ Token yangilashda xatolik yuz berdi.")
                    return ConversationHandler.END

            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}")

            data = response.json()
            context.user_data['profile_data'] = data

        # Format interests
        categories = data.get('categories_of_interest', [])
        categories_text = "\n".join([f"  • {category}" for category in categories]) if categories else "Qiziqishlar kiritilmagan."

        # Interests message
        text = f"""🎯 <b>{data['first_name']} {data['last_name'] if data['first_name'] or data['last_name'] else 'TestAbd foydalanuvchisi'} uchun qiziqishlar</b>

📋 <b>Qiziqishlar:</b>
{categories_text}"""

        # Buttons in two-column layout
        keyboard = [
            [InlineKeyboardButton("👤 Profil", callback_data="profile_main"),
             InlineKeyboardButton("📊 Statistika", callback_data="profile_stats")],
            [InlineKeyboardButton("📍 Joylashuv", callback_data="profile_location"),
             InlineKeyboardButton("✏️ Profilni tahrirlash", callback_data="edit_profile")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="Main_Menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Profile image handling
        profile_image_url = context.user_data.get('profile_image_url')

        if profile_image_url:
            try:
                if profile_image_url.startswith("http://192.") or "localhost" in profile_image_url or "127.0.0.1" in profile_image_url:
                    image_response = await sync_to_async(requests.get)(profile_image_url)
                    image_response.raise_for_status()
                    image_data = BytesIO(image_response.content)
                    await query.message.edit_media(
                        media=InputMediaPhoto(media=image_data, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                        reply_markup=reply_markup
                    )
                else:
                    await query.message.edit_media(
                        media=InputMediaPhoto(media=profile_image_url, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print("Rasmni tahrirlashda xatolik:", e)
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    except ObjectDoesNotExist:
        await query.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Ma'lumotlarni olishda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

    return CATEGORIES

async def profile_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the profile_location callback to display user location."""
    query = update.callback_query
    await query.answer("Joylashuv yuklanmoqda...")
    user_id = update.effective_user.id

    try:
        # Check if profile data is cached
        data = context.user_data.get('profile_data')
        if not data:
            user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
            headers = {"Authorization": f"Bearer {user.access_token}"}
            url = f"{BASE_API_URL}accounts/me/"

            response = await sync_to_async(requests.get)(url, headers=headers)

            if response.status_code == 401:
                refresh_response = await sync_to_async(requests.post)(
                    f"{BASE_API_URL}accounts/token/refresh/", 
                    json={"refresh": user.refresh_token}
                )
                if refresh_response.status_code == 200:
                    tokens = refresh_response.json()
                    user.access_token = tokens['access']
                    await sync_to_async(user.save)()
                    headers["Authorization"] = f"Bearer {user.access_token}"
                    response = await sync_to_async(requests.get)(url, headers=headers)
                else:
                    await query.message.reply_text("❌ Token yangilashda xatolik yuz berdi.")
                    return ConversationHandler.END

            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}")

            data = response.json()
            context.user_data['profile_data'] = data

        # Format location
        country = data.get('country', {}).get('name', 'Nomaʼlum')
        region = data.get('region', {}).get('name', 'Nomaʼlum')
        district = data.get('district', {}).get('name', 'Nomaʼlum')
        settlement = data.get('settlement', {}).get('name', 'Nomaʼlum')

        # Location message
        text = f"""📍 <b>{data['first_name']} {data['last_name'] if data['first_name'] or data['last_name'] else 'TestAbd foydalanuvchisi'} uchun joylashuv</b>

🌍 <b>Mamlakat:</b> {country}
🏞️ <b>Viloyat:</b> {region}
🏙️ <b>Tuman:</b> {district}
🏘️ <b>Mahalla:</b> {settlement}"""

        # Buttons in two-column layout, replacing Joylashuv with Profil
        keyboard = [
            [InlineKeyboardButton("👤 Profil", callback_data="profile_main"),
             InlineKeyboardButton("📊 Statistika", callback_data="profile_stats")],
            [InlineKeyboardButton("🎯 Qiziqishlar", callback_data="profile_categories"),
             InlineKeyboardButton("✏️ Profilni tahrirlash", callback_data="edit_profile")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="Main_Menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Profile image handling
        profile_image_url = context.user_data.get('profile_image_url')

        if profile_image_url:
            try:
                if profile_image_url.startswith("http://192.") or "localhost" in profile_image_url or "127.0.0.1" in profile_image_url:
                    image_response = await sync_to_async(requests.get)(profile_image_url)
                    image_response.raise_for_status()
                    image_data = BytesIO(image_response.content)
                    await query.message.edit_media(
                        media=InputMediaPhoto(media=image_data, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                        reply_markup=reply_markup
                    )
                else:
                    await query.message.edit_media(
                        media=InputMediaPhoto(media=profile_image_url, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print("Rasmni tahrirlashda xatolik:", e)
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    except ObjectDoesNotExist:
        await query.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Ma'lumotlarni olishda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

    return LOCATION

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Placeholder for editing profile."""
    query = update.callback_query
    await query.answer("Profil tahrirlash yuklanmoqda...")

    try:
        text = "✏️ <b>Profilni tahrirlash</b>\n\nHozircha bu funksiya ishlab chiqish jarayonida. Kelajakda bio, ismingiz va boshqa ma'lumotlarni tahrirlashingiz mumkin bo'ladi."

        # Buttons in two-column layout
        keyboard = [
            [InlineKeyboardButton("👤 Profil", callback_data="profile_main"),
             InlineKeyboardButton("📊 Statistika", callback_data="profile_stats")],
            [InlineKeyboardButton("🎯 Qiziqishlar", callback_data="profile_categories"),
             InlineKeyboardButton("📍 Joylashuv", callback_data="profile_location")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="Main_Menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Profile image handling
        profile_image_url = context.user_data.get('profile_image_url')

        if profile_image_url:
            try:
                if profile_image_url.startswith("http://192.") or "localhost" in profile_image_url or "127.0.0.1" in profile_image_url:
                    image_response = await sync_to_async(requests.get)(profile_image_url)
                    image_response.raise_for_status()
                    image_data = BytesIO(image_response.content)
                    await query.message.edit_media(
                        media=InputMediaPhoto(media=image_data, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                        reply_markup=reply_markup
                    )
                else:
                    await query.message.edit_media(
                        media=InputMediaPhoto(media=profile_image_url, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print("Rasmni tahrirlashda xatolik:", e)
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Tahrirlashda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

    return PROFILE  # Return to PROFILE state for navigation

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the main_menu callback to return to the main menu."""
    query = update.callback_query
    await query.answer("Bosh menyuga qaytish...")

    try:
        text = "🏠 <b>Bosh menyu</b>\n\nIltimos, bosh menyudan kerakli buyruqni tanlang (masalan, /profile, /stats, /edit_config)."

        # Minimal buttons or none, as this is a placeholder
        keyboard = [
            [InlineKeyboardButton("👤 Profil", callback_data="profile_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Profile image handling
        profile_image_url = context.user_data.get('profile_image_url')

        if profile_image_url:
            try:
                if profile_image_url.startswith("http://192.") or "localhost" in profile_image_url or "127.0.0.1" in profile_image_url:
                    image_response = await sync_to_async(requests.get)(profile_image_url)
                    image_response.raise_for_status()
                    image_data = BytesIO(image_response.content)
                    await query.message.edit_media(
                        media=InputMediaPhoto(media=image_data, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                        reply_markup=reply_markup
                    )
                else:
                    await query.message.edit_media(
                        media=InputMediaPhoto(media=profile_image_url, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                        reply_markup=reply_markup
                    )
            except Exception as e:
                print("Rasmni tahrirlashda xatolik:", e)
                await query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        else:
            await query.edit_message_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Bosh menyuga qaytishda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

    return ConversationHandler.END





profile_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(MyProfile, pattern=r"^MyProfile$")
],
    states={
        PROFILE: [
            CallbackQueryHandler(profile_stats, pattern="^profile_stats$"),
            CallbackQueryHandler(profile_categories, pattern="^profile_categories$"),
            CallbackQueryHandler(profile_location, pattern="^profile_location$"),
            CallbackQueryHandler(edit_profile, pattern="^edit_profile$"),
            CallbackQueryHandler(MyProfile, pattern="^profile_main$"),
        ],
        STATS: [
            CallbackQueryHandler(MyProfile, pattern="^profile_main$"),
            CallbackQueryHandler(profile_categories, pattern="^profile_categories$"),
            CallbackQueryHandler(profile_location, pattern="^profile_location$"),
            CallbackQueryHandler(edit_profile, pattern="^edit_profile$"),
        ],
        CATEGORIES: [
            CallbackQueryHandler(MyProfile, pattern="^profile_main$"),
            CallbackQueryHandler(profile_stats, pattern="^profile_stats$"),
            CallbackQueryHandler(profile_location, pattern="^profile_location$"),
            CallbackQueryHandler(edit_profile, pattern="^edit_profile$"),
        ],
        LOCATION: [
            CallbackQueryHandler(MyProfile, pattern="^profile_main$"),
            CallbackQueryHandler(profile_stats, pattern="^profile_stats$"),
            CallbackQueryHandler(profile_categories, pattern="^profile_categories$"),
            CallbackQueryHandler(edit_profile, pattern="^edit_profile$"),
        ],
    },
    fallbacks=[]
)