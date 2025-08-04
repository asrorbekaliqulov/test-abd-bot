from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import requests
from ..models.TelegramBot import TelegramUser
from io import BytesIO
from datetime import datetime
from asgiref.sync import sync_to_async
from ..decorators import mandatory_channel_required
from django.core.exceptions import ObjectDoesNotExist
from TestAbdBot.settings import BASE_API_URL
import os
import time
import uuid

PROFILE, STATS, CATEGORIES, LOCATION, EDIT_PROFILE, EDIT_FIELD, REFERRALS, SELECT_COUNTRY, SELECT_REGION, SELECT_DISTRICT, SELECT_SETTLEMENT = range(11)

@mandatory_channel_required
async def MyProfile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /profile command or profile_main callback to display user profile."""
    user_id = update.effective_user.id
    query = update.callback_query
    if query:
        await query.answer("Yuklanmoqda...")

    try:
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
                    error_text = "❌ Token yangilashda xatolik yuz berdi."
                    if query:
                        await query.message.reply_text(error_text)
                    else:
                        await update.message.reply_text(error_text)
                    return ConversationHandler.END

            if response.status_code != 200:
                raise Exception(f"API request failed with status {response.status_code}")

            data = response.json()
            context.user_data['profile_data'] = data

        join_date = datetime.fromisoformat(data['date_joined'].replace('Z', '+00:00')).strftime("%Y-%m-%d")

        text = f"""👤 <b>{data['first_name']} {data['last_name'] if data['first_name'] or data['last_name'] else 'TestAbd foydalanuvchisi'}</b>
📛 <b>Username:</b> <a href='https://testabd.uz/profile/{data['username']}'>@{data['username']}</a>
🎖️ <b>Level:</b> {data.get('level', 'Nomaʼlum')}
🪙 <b>Coinlari:</b> {data.get('coins', 0)} ta
🗓 <b>Qo'shilgan sana:</b> {join_date}
ℹ️ <b>Biografiya:</b> {data.get('bio', "Yozilmagan")}
📧 <b>Email:</b> {data.get('email', 'Kiritilmagan')}"""

        keyboard = [
            [InlineKeyboardButton("📊 Statistika", callback_data="profile_stats"),
             InlineKeyboardButton("🎯 Qiziqishlar", callback_data="profile_categories")],
            [InlineKeyboardButton("📍 Joylashuv", callback_data="profile_location"),
             InlineKeyboardButton("🤝 Referrallar", callback_data="profile_referrals")],
            [InlineKeyboardButton("✏️ Profilni tahrirlash", callback_data="edit_profile_main"),
             InlineKeyboardButton("🏠 Bosh menyu", callback_data="Main_Menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        profile_image_url = data.get("profile_image")
        print(f"PROFILE IMAGE: {profile_image_url}")
        context.user_data['profile_image_url'] = profile_image_url
        is_localhost = BASE_API_URL.startswith("http://") or BASE_API_URL.startswith("http://127.0.0.1")

        if profile_image_url:
            try:
                if is_localhost:
                    user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
                    headers = {"Authorization": f"Bearer {user.access_token}"}
                    response = await sync_to_async(requests.get)(profile_image_url, headers=headers)
                    if response.status_code == 200:
                        content_type = response.headers.get('content-type', '')
                        if not content_type.startswith('image/'):
                            raise Exception(f"Invalid content type: {content_type}")
                        image_data = BytesIO(response.content)
                        image_data.seek(0)
                        if query:
                            await query.message.edit_media(
                                media=InputMediaPhoto(media=image_data, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                                reply_markup=reply_markup
                            )
                        else:
                            await context.bot.send_photo(
                                chat_id=user_id,
                                photo=image_data,
                                caption=f"Profil rasmi👆👆👆\n\n{text}",
                                reply_markup=reply_markup,
                                parse_mode='HTML'
                            )
                    else:
                        raise Exception(f"Failed to download profile image, status code: {response.status_code}")
                else:
                    if query:
                        await query.message.edit_media(
                            media=InputMediaPhoto(media=profile_image_url, caption=f"Profil rasmi👆👆👆\n\n{text}", parse_mode='HTML'),
                            reply_markup=reply_markup
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
                print(f"Rasmni tahrirlashda xatolik: {str(e)}")
                if query:
                    await query.message.edit_text(
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
        else:
            if query:
                await query.message.edit_text(
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
        error_text = "❌ Foydalanuvchi topilmadi."
        if query:
            await query.message.reply_text(error_text)
        else:
            await update.message.reply_text(error_text)
        return ConversationHandler.END
    except Exception as e:
        print(f"Xatolik: {str(e)}")
        error_text = f"❌ Ma'lumotlarni olishda xatolik yuz berdi: {str(e)}"
        if query:
            await query.message.reply_text(error_text)
        else:
            await update.message.reply_text(error_text)
        return ConversationHandler.END

    return PROFILE

async def profile_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the profile_stats callback to display user statistics."""
    query = update.callback_query
    await query.answer("Statistika yuklanmoqda...")
    user_id = update.effective_user.id

    try:
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

        weekly_tests = data.get('weekly_test_count', {})
        weekly_text = "\n".join([f"  • <b>{day}</b>: {count} ta" for day, count in weekly_tests.items()])

        text = f"""📊 <b>{data['first_name']} {data['last_name'] if data['first_name'] or data['last_name'] else 'TestAbd foydalanuvchisi'} uchun statistika</b>

🎖️ <b>Level:</b> {data.get('level', 'Nomaʼlum')}
🪙 <b>Coinlari:</b> {data.get('coins', 0)} ta
✅ <b>To‘g‘ri javoblar:</b> {data.get('correct_count', 0)} ta
❌ <b>Noto‘g‘ri javoblar:</b> {data.get('wrong_count', 0)} ta
📝 <b>Yechilgan testlar:</b> {data.get('tests_solved', 0)} ta
⏱️ <s><b>O‘rtacha vaqt:</b> {data.get('average_time', 0)} sekund</s>
🔥 <b>Streak kunlari:</b> {data.get('streak_day', 0)} kun
📅 <b>Haftalik testlar:</b>
{weekly_text}"""

        keyboard = [
            [InlineKeyboardButton("👤 Profil", callback_data="profile_main"),
             InlineKeyboardButton("🎯 Qiziqishlar", callback_data="profile_categories")],
            [InlineKeyboardButton("📍 Joylashuv", callback_data="profile_location"),
             InlineKeyboardButton("🤝 Referrallar", callback_data="profile_referrals")],
            [InlineKeyboardButton("✏️ Profilni tahrirlash", callback_data="edit_profile_main"),
             InlineKeyboardButton("🏠 Bosh menyu", callback_data="Main_Menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        profile_image_url = context.user_data.get('profile_image_url')
        if profile_image_url:
            await query.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await query.message.edit_text(
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

        categories = data.get('categories_of_interest', [])
        categories_text = ""
        if categories:
            for category in categories:
                categories_text += (
                    f"{category['emoji']} <b>{category['title']}</b>\n"
                    f"📝 Testlar soni: {category['total_tests']} ta\n"
                    f"❓ Savollar soni: {category['total_questions']} ta\n"
                    f"ℹ️ Tavsif: {category['description']}\n\n"
                )
        else:
            categories_text = "Qiziqishlar kiritilmagan."

        text = f"""🎯 <b>{data['first_name']} {data['last_name'] if data['first_name'] or data['last_name'] else 'TestAbd foydalanuvchisi'} uchun qiziqishlar</b>

📋 <b>Qiziqishlar:</b>
{categories_text}

ℹ️ <i>Ushbu ma'lumot TestAbd.uz saytidagi faoliyatingiz asosida o'zgaradi</i>"""

        keyboard = [
            [InlineKeyboardButton("👤 Profil", callback_data="profile_main"),
             InlineKeyboardButton("📊 Statistika", callback_data="profile_stats")],
            [InlineKeyboardButton("📍 Joylashuv", callback_data="profile_location"),
             InlineKeyboardButton("🤝 Referrallar", callback_data="profile_referrals")],
            [InlineKeyboardButton("✏️ Profilni tahrirlash", callback_data="edit_profile_main"),
             InlineKeyboardButton("🏠 Bosh menyu", callback_data="Main_Menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        profile_image_url = context.user_data.get('profile_image_url')
        if profile_image_url:
            await query.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await query.message.edit_text(
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

        country = data.get('country', {}).get('name', 'Nomaʼlum')
        region = data.get('region', {}).get('name', 'Nomaʼlum')
        district = data.get('district', {}).get('name', 'Nomaʼlum')
        settlement = data.get('settlement', {}).get('name', 'Nomaʼlum')

        text = f"""📍 <b>{data['first_name']} {data['last_name'] if data['first_name'] or data['last_name'] else 'TestAbd foydalanuvchisi'} uchun joylashuv</b>

🌍 <b>Mamlakat:</b> {country}
🏞️ <b>Viloyat:</b> {region}
🏙️ <b>Tuman:</b> {district}
🏘️ <b>Mahalla:</b> {settlement}"""

        keyboard = [
            [InlineKeyboardButton("👤 Profil", callback_data="profile_main"),
             InlineKeyboardButton("📊 Statistika", callback_data="profile_stats")],
            [InlineKeyboardButton("🎯 Qiziqishlar", callback_data="profile_categories"),
             InlineKeyboardButton("🤝 Referrallar", callback_data="profile_referrals")],
            [InlineKeyboardButton("✏️ Joylashuvni tahrirlash", callback_data="edit_profile_location"),
             InlineKeyboardButton("🏠 Bosh menyu", callback_data="Main_Menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        profile_image_url = context.user_data.get('profile_image_url')
        if profile_image_url:
            await query.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await query.message.edit_text(
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

async def profile_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the profile_referrals callback to display referral information."""
    query = update.callback_query
    await query.answer("Referrallar yuklanmoqda...")
    user_id = update.effective_user.id

    try:
        # Clear cached profile data to ensure fresh data
        context.user_data.pop('profile_data', None)
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
        referral_code = data.get('referral_code', None)
        referred_users = data.get('referred_users', [])[:5]
        referrals_text = "\n".join([f"  • @{user.get('username', 'Nomaʼlum')}" for user in referred_users]) if referred_users else "Hali taklif qilingan foydalanuvchilar yo'q."

        # Add timestamp to ensure message uniqueness
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not referral_code:
            text = f"""🔗 <b>Referal kodingizni yarating</b>\n\nSizda hali referal kodi yo'q. Taklif qilgan foydalanuvchilaringizni ko'rish uchun avval referal kodi yarating.\n\n<i>Yangilandi: {timestamp}</i>"""
            keyboard = [
                [InlineKeyboardButton("🔗 Kod yaratish", callback_data="create_referral_code")],
                [InlineKeyboardButton("⬅️ Orqaga", callback_data="profile_main")]
            ]
        else:
            text = f"""🤝 <b>Referrallar</b>

🔗 <b>Referal kodi:</b> {referral_code}
👥 <b>Oxirgi 5 ta taklif qilingan foydalanuvchilar:</b>
{referrals_text}

<i>Yangilandi: {timestamp}</i>"""

            keyboard = [
                [InlineKeyboardButton("👤 Profil", callback_data="profile_main"),
                 InlineKeyboardButton("📊 Statistika", callback_data="profile_stats")],
                [InlineKeyboardButton("🎯 Qiziqishlar", callback_data="profile_categories"),
                 InlineKeyboardButton("📍 Joylashuv", callback_data="profile_location")],
                [InlineKeyboardButton("🔄 Referal kodni o'zgartirish", callback_data="change_referral_code"),
                 InlineKeyboardButton("👥 Barcha referallarni ko'rish", callback_data="view_all_referrals")],
                [InlineKeyboardButton("🏠 Bosh menyu", callback_data="Main_Menu")]
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        profile_image_url = context.user_data.get('profile_image_url')
        try:
            if profile_image_url:
                await query.message.edit_caption(
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            else:
                await query.message.edit_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
        except Exception as e:
            if "Message is not modified" in str(e):
                # If message is not modified, send a new message instead
                if profile_image_url:
                    await query.message.reply_photo(
                        photo=profile_image_url,
                        caption=text,
                        reply_markup=reply_markup,
                        parse_mode="HTML"
                    )
                else:
                    await query.message.reply_text(
                        text=text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
            else:
                raise e

    except ObjectDoesNotExist:
        await query.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Ma'lumotlarni olishda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

    return REFERRALS

async def create_referral_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle creation of a new referral code via accounts/me/update/."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
        headers = {"Authorization": f"Bearer {user.access_token}"}
        url = f"{BASE_API_URL}accounts/me/update/"

        # Generate a new referral code
        new_referral_code = str(uuid.uuid4())[:8]  # 8-character unique code
        payload = {"referral_code": new_referral_code}

        response = await sync_to_async(requests.patch)(url, headers=headers, json=payload)

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
                response = await sync_to_async(requests.patch)(url, headers=headers, json=payload)
            else:
                await query.message.reply_text("❌ Token yangilashda xatolik yuz berdi.")
                return ConversationHandler.END

        if response.status_code != 200:
            print(f"Create referral response: {response.status_code}, {response.text}")
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        # Verify the referral code was set
        updated_data = response.json()
        if updated_data.get('referral_code') != new_referral_code:
            print(f"Referral code mismatch: expected {new_referral_code}, got {updated_data.get('referral_code')}")
            raise Exception("Referral code was not set correctly by the API")

        # Invalidate cached profile data and update
        context.user_data.pop('profile_data', None)
        context.user_data['profile_data'] = updated_data
        await query.message.reply_text(f"✅ Referal kodi muvaffaqiyatli yaratildi: {new_referral_code}")
        await profile_referrals(update, context)
        return REFERRALS

    except ObjectDoesNotExist:
        await query.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Referal kod yaratishda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

async def change_referral_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle updating the referral code via accounts/me/update/."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
        headers = {"Authorization": f"Bearer {user.access_token}"}
        url = f"{BASE_API_URL}accounts/me/update/"

        # Generate a new referral code
        new_referral_code = str(uuid.uuid4())[:8]  # 8-character unique code
        payload = {"referral_code": new_referral_code}

        response = await sync_to_async(requests.patch)(url, headers=headers, json=payload)

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
                response = await sync_to_async(requests.patch)(url, headers=headers, json=payload)
            else:
                await query.message.reply_text("❌ Token yangilashda xatolik yuz berdi.")
                return ConversationHandler.END

        if response.status_code != 200:
            print(f"Change referral response: {response.status_code}, {response.text}")
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        # Verify the referral code was updated
        updated_data = response.json()
        if updated_data.get('referral_code') != new_referral_code:
            print(f"Referral code mismatch: expected {new_referral_code}, got {updated_data.get('referral_code')}")
            raise Exception("Referral code was not updated correctly by the API")

        # Invalidate cached profile data and update
        context.user_data.pop('profile_data', None)
        context.user_data['profile_data'] = updated_data
        await query.message.reply_text(f"✅ Referal kodi muvaffaqiyatli yangilandi: {new_referral_code}")
        await profile_referrals(update, context)
        return REFERRALS

    except ObjectDoesNotExist:
        await query.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Referal kodni yangilashda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

async def view_all_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle viewing all referred users."""
    query = update.callback_query
    await query.answer("Barcha referallar yuklanmoqda...")
    user_id = update.effective_user.id

    try:
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
        referrals = data.get('referred_users', [])
        referrals_text = "\n".join([f"  • @{user.get('username', 'Nomaʼlum')}" for user in referrals]) if referrals else "Hali taklif qilingan foydalanuvchilar yo'q."

        text = f"""🤝 <b>Barcha referallar</b>

👥 <b>Taklif qilingan foydalanuvchilar:</b>
{referrals_text}"""

        keyboard = [
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="profile_referrals")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        profile_image_url = context.user_data.get('profile_image_url')
        if profile_image_url:
            await query.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await query.message.edit_text(
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

    return REFERRALS

async def edit_profile_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the edit_profile_main callback to show editable profile fields."""
    query = update.callback_query
    await query.answer("Profil tahrirlash menyusi...")

    try:
        data = context.user_data.get('profile_data')
        user_id = update.effective_user.id
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

        text = f"""✏️ <b>Profilni tahrirlash</b>

Quyidagi ma'lumotlardan birini tahrirlash uchun tugmani bosing:

👤 <b>Ism:</b> {data.get('first_name', 'Kiritilmagan')}
👤 <b>Familiya:</b> {data.get('last_name', 'Kiritilmagan')}
📛 <b>Username:</b> @{data.get('username', 'Kiritilmagan')}
📧 <b>Email:</b> {data.get('email', 'Kiritilmagan')}
ℹ️ <b>Bio:</b> {data.get('bio', 'Yozilmagan')}
📞 <b>Telefon:</b> {data.get('phone_number', 'Kiritilmagan')}
🖼️ <b>Profil rasmi:</b> {'Mavjud' if data.get('profile_image') else 'Yo\'q'}"""

        keyboard = [
            [InlineKeyboardButton("Ism", callback_data="edit_field_first_name"),
             InlineKeyboardButton("Familiya", callback_data="edit_field_last_name")],
            [InlineKeyboardButton("Username", callback_data="edit_field_username"),
             InlineKeyboardButton("Email", callback_data="edit_field_email")],
            [InlineKeyboardButton("Bio", callback_data="edit_field_bio"),
             InlineKeyboardButton("Telefon", callback_data="edit_field_phone_number")],
            [InlineKeyboardButton("🖼️ Profil rasmi", callback_data="edit_field_profile_image"),
             InlineKeyboardButton("⬅️ Orqaga", callback_data="profile_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        profile_image_url = context.user_data.get('profile_image_url')
        if profile_image_url:
            await query.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await query.message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    except ObjectDoesNotExist:
        await query.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Tahrirlashda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

    return EDIT_PROFILE

async def edit_profile_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the edit_profile_location callback to start location editing."""
    query = update.callback_query
    await query.answer("Joylashuvni tahrirlash...")

    try:
        user_id = update.effective_user.id
        user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
        headers = {"Authorization": f"Bearer {user.access_token}"}
        url = f"{BASE_API_URL}accounts/countries/"

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

        countries = response.json()
        text = "🌍 <b>Mamlakatni tanlang:</b>"
        keyboard = [
            [InlineKeyboardButton(country['name'], callback_data=f"select_country_{country['id']}")]
            for country in countries
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="profile_location")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        profile_image_url = context.user_data.get('profile_image_url')
        if profile_image_url:
            await query.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await query.message.edit_text(
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

    return SELECT_COUNTRY

async def select_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle country selection and fetch regions."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    try:
        country_id = query.data.replace("select_country_", "")
        user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
        headers = {"Authorization": f"Bearer {user.access_token}"}
        url = f"{BASE_API_URL}accounts/regions/{country_id}/"

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

        regions = response.json()
        context.user_data['selected_location'] = {'country_id': int(country_id)}

        text = "🏞️ <b>Viloyatni tanlang:</b>"
        keyboard = [
            [InlineKeyboardButton(region['name'], callback_data=f"select_region_{region['id']}")]
            for region in regions
        ]
        keyboard.append([InlineKeyboardButton("💾 Saqlash", callback_data="save_location")])
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="edit_profile_location")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        profile_image_url = context.user_data.get('profile_image_url')
        if profile_image_url:
            await query.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await query.message.edit_text(
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

    return SELECT_REGION

async def select_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle region selection and fetch districts."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    try:
        region_id = query.data.replace("select_region_", "")
        user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
        headers = {"Authorization": f"Bearer {user.access_token}"}
        url = f"{BASE_API_URL}accounts/districts/{region_id}/"

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

        districts = response.json()
        context.user_data['selected_location']['region_id'] = int(region_id)

        text = "🏙️ <b>Tumanni tanlang:</b>"
        keyboard = [
            [InlineKeyboardButton(district['name'], callback_data=f"select_district_{district['id']}")]
            for district in districts
        ]
        keyboard.append([InlineKeyboardButton("💾 Saqlash", callback_data="save_location")])
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=f"select_country_{context.user_data['selected_location']['country_id']}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        profile_image_url = context.user_data.get('profile_image_url')
        if profile_image_url:
            await query.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await query.message.edit_text(
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

    return SELECT_DISTRICT

async def select_district(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle district selection and fetch settlements."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    try:
        district_id = query.data.replace("select_district_", "")
        user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
        headers = {"Authorization": f"Bearer {user.access_token}"}
        url = f"{BASE_API_URL}accounts/settlements/{district_id}/"

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

        settlements = response.json()
        context.user_data['selected_location']['district_id'] = int(district_id)

        text = "🏘️ <b>Mahallani tanlang:</b>"
        keyboard = [
            [InlineKeyboardButton(settlement['name'], callback_data=f"select_settlement_{settlement['id']}")]
            for settlement in settlements
        ]
        keyboard.append([InlineKeyboardButton("💾 Saqlash", callback_data="save_location")])
        keyboard.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=f"select_region_{context.user_data['selected_location']['region_id']}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        profile_image_url = context.user_data.get('profile_image_url')
        if profile_image_url:
            await query.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await query.message.edit_text(
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

    return SELECT_SETTLEMENT

async def select_settlement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settlement selection and save location."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    try:
        settlement_id = query.data.replace("select_settlement_", "")
        context.user_data['selected_location']['settlement_id'] = int(settlement_id)
        await save_location(update, context)
        return LOCATION

    except ObjectDoesNotExist:
        await query.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Ma'lumotlarni saqlashda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

async def save_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the selected location to the API."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
        headers = {"Authorization": f"Bearer {user.access_token}"}
        url = f"{BASE_API_URL}accounts/me/update/"

        payload = {
            'country_id': context.user_data['selected_location'].get('country_id'),
            'region_id': context.user_data['selected_location'].get('region_id'),
            'district_id': context.user_data['selected_location'].get('district_id'),
            'settlement_id': context.user_data['selected_location'].get('settlement_id')
        }
        payload = {k: v for k, v in payload.items() if v is not None}

        response = await sync_to_async(requests.patch)(url, headers=headers, json=payload)
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
                response = await sync_to_async(requests.patch)(url, headers=headers, json=payload)
            else:
                await query.message.reply_text("❌ Token yangilashda xatolik yuz berdi.")
                return ConversationHandler.END

        if response.status_code != 200:
            print(f"Save location response: {response.status_code}, {response.text}")
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        context.user_data['profile_data'] = response.json()
        await query.message.reply_text("✅ Joylashuv muvaffaqiyatli yangilandi!")
        context.user_data['selected_location'] = {}
        await profile_location(update, context)
        return LOCATION

    except ObjectDoesNotExist:
        await query.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Ma'lumotlarni saqlashda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle specific field editing based on callback data."""
    query = update.callback_query
    await query.answer()

    field = query.data.replace("edit_field_", "")
    context.user_data['edit_field'] = field

    field_names = {
        'first_name': 'Ism',
        'last_name': 'Familiya',
        'username': 'Username',
        'email': 'Email',
        'bio': 'Biografiya',
        'phone_number': 'Telefon raqami',
        'profile_image': 'Profil rasmi'
    }

    text = f"✏️ <b>{field_names.get(field, field)} ni tahrirlash</b>\n\n"
    if field == 'profile_image':
        text += "Yangi profil rasmini yuboring (rasm sifatida):"
    else:
        text += "Yangi qiymatni kiriting:"

    keyboard = [[InlineKeyboardButton("⬅️ Bekor qilish", callback_data="cancel_edit")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    profile_image_url = context.user_data.get('profile_image_url')
    is_localhost = BASE_API_URL.startswith("http://localhost") or BASE_API_URL.startswith("http://127.0.0.1")

    if profile_image_url:
        await query.message.edit_caption(
            caption=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await query.message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    return EDIT_FIELD

async def save_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the edited field to the API."""
    user_id = update.effective_user.id
    field = context.user_data.get('edit_field')
    new_value = update.message.text.strip() if field != 'profile_image' else None

    field_names = {
        'first_name': 'Ism',
        'last_name': 'Familiya',
        'username': 'Username',
        'email': 'Email',
        'bio': 'Biografiya',
        'phone_number': 'Telefon raqami',
        'profile_image': 'Profil rasmi'
    }

    try:
        user = await sync_to_async(TelegramUser.objects.get)(user_id=user_id)
        headers = {"Authorization": f"Bearer {user.access_token}"}
        url = f"{BASE_API_URL}accounts/me/update/"

        if field == 'profile_image':
            if not update.message.photo:
                await update.message.reply_text("❌ Iltimos, rasm yuboring!")
                return EDIT_FIELD
            photo = update.message.photo[-1]
            photo_file = await photo.get_file()
            photo_data = await photo_file.download_as_bytearray()
            files = {'profile_image': (f'{user_id}.jpg', photo_data, 'image/jpeg')}
            response = await sync_to_async(requests.patch)(url, headers=headers, files=files)
        else:
            payload = {field: new_value}
            response = await sync_to_async(requests.patch)(url, headers=headers, json=payload)

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
                if field == 'profile_image':
                    response = await sync_to_async(requests.patch)(url, headers=headers, files=files)
                else:
                    response = await sync_to_async(requests.patch)(url, headers=headers, json=payload)
            else:
                await update.message.reply_text("❌ Token yangilashda xatolik yuz berdi.")
                return ConversationHandler.END

        if response.status_code != 200:
            print(f"Save field response: {response.status_code}, {response.text}")
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        updated_data = response.json()
        context.user_data['profile_data'] = updated_data
        if field == 'profile_image':
            context.user_data['profile_image_url'] = updated_data.get('profile_image')

        await update.message.reply_text(
            f"✅ {field_names.get(field, field).replace('_', ' ').title()} muvaffaqiyatli yangilandi!"
        )

        await MyProfile(update, context)
        return PROFILE

    except ObjectDoesNotExist:
        await update.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        await update.message.reply_text(f"❌ Ma'lumotlarni saqlashda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the editing process and return to the previous state."""
    query = update.callback_query
    await query.answer()

    field = context.user_data.get('edit_field', '')
    if field in ['first_name', 'last_name', 'username', 'email', 'bio', 'phone_number', 'profile_image']:
        await MyProfile(update, context)
        return PROFILE
    elif field in ['country_id', 'region_id', 'district_id', 'settlement_id']:
        await profile_location(update, context)
        return LOCATION

    await query.message.reply_text("❌ Tahrirlash bekor qilindi.")
    return ConversationHandler.END

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the main_menu callback to return to the main menu."""
    query = update.callback_query
    await query.answer("Bosh menyuga qaytish...")

    try:
        text = "🏠 <b>Bosh menyu</b>\n\nIltimos, bosh menyudan kerakli buyruqni tanlang (masalan, /profile, /stats, /edit_config)."
        keyboard = [
            [InlineKeyboardButton("👤 Profil", callback_data="profile_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        profile_image_url = context.user_data.get('profile_image_url')
        if profile_image_url:
            await query.message.edit_caption(
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        else:
            await query.message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

    except ObjectDoesNotExist:
        await query.message.reply_text("❌ Foydalanuvchi topilmadi.")
        return ConversationHandler.END
    except Exception as e:
        print("Xatolik:", e)
        await query.message.reply_text(f"❌ Bosh menyuga qaytishda xatolik yuz berdi: {str(e)}")
        return ConversationHandler.END

    return ConversationHandler.END

profile_handler = ConversationHandler(
    entry_points=[
        CommandHandler("profile", MyProfile),
        CallbackQueryHandler(MyProfile, pattern="^profile_main$")
    ],
    states={
        PROFILE: [
            CallbackQueryHandler(profile_stats, pattern="^profile_stats$"),
            CallbackQueryHandler(profile_categories, pattern="^profile_categories$"),
            CallbackQueryHandler(profile_location, pattern="^profile_location$"),
            CallbackQueryHandler(profile_referrals, pattern="^profile_referrals$"),
            CallbackQueryHandler(edit_profile_main, pattern="^edit_profile_main$"),
            CallbackQueryHandler(main_menu, pattern="^Main_Menu$")
        ],
        STATS: [
            CallbackQueryHandler(MyProfile, pattern="^profile_main$"),
            CallbackQueryHandler(profile_categories, pattern="^profile_categories$"),
            CallbackQueryHandler(profile_location, pattern="^profile_location$"),
            CallbackQueryHandler(profile_referrals, pattern="^profile_referrals$"),
            CallbackQueryHandler(edit_profile_main, pattern="^edit_profile_main$"),
            CallbackQueryHandler(main_menu, pattern="^Main_Menu$")
        ],
        CATEGORIES: [
            CallbackQueryHandler(MyProfile, pattern="^profile_main$"),
            CallbackQueryHandler(profile_stats, pattern="^profile_stats$"),
            CallbackQueryHandler(profile_location, pattern="^profile_location$"),
            CallbackQueryHandler(profile_referrals, pattern="^profile_referrals$"),
            CallbackQueryHandler(edit_profile_main, pattern="^edit_profile_main$"),
            CallbackQueryHandler(main_menu, pattern="^Main_Menu$")
        ],
        LOCATION: [
            CallbackQueryHandler(MyProfile, pattern="^profile_main$"),
            CallbackQueryHandler(profile_stats, pattern="^profile_stats$"),
            CallbackQueryHandler(profile_categories, pattern="^profile_categories$"),
            CallbackQueryHandler(profile_referrals, pattern="^profile_referrals$"),
            CallbackQueryHandler(edit_profile_location, pattern="^edit_profile_location$"),
            CallbackQueryHandler(main_menu, pattern="^Main_Menu$")
        ],
        REFERRALS: [
            CallbackQueryHandler(MyProfile, pattern="^profile_main$"),
            CallbackQueryHandler(profile_stats, pattern="^profile_stats$"),
            CallbackQueryHandler(profile_categories, pattern="^profile_categories$"),
            CallbackQueryHandler(profile_location, pattern="^profile_location$"),
            CallbackQueryHandler(create_referral_code, pattern="^create_referral_code$"),
            CallbackQueryHandler(change_referral_code, pattern="^change_referral_code$"),
            CallbackQueryHandler(view_all_referrals, pattern="^view_all_referrals$"),
            CallbackQueryHandler(main_menu, pattern="^Main_Menu$")
        ],
        EDIT_PROFILE: [
            CallbackQueryHandler(edit_field, pattern="^edit_field_.*$"),
            CallbackQueryHandler(MyProfile, pattern="^profile_main$"),
            CallbackQueryHandler(profile_stats, pattern="^profile_stats$"),
            CallbackQueryHandler(profile_categories, pattern="^profile_categories$"),
            CallbackQueryHandler(profile_location, pattern="^profile_location$"),
            CallbackQueryHandler(main_menu, pattern="^Main_Menu$")
        ],
        EDIT_FIELD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_field),
            MessageHandler(filters.PHOTO, save_field),
            CallbackQueryHandler(cancel_edit, pattern="^cancel_edit$")
        ],
        SELECT_COUNTRY: [
            CallbackQueryHandler(select_country, pattern="^select_country_.*$"),
            CallbackQueryHandler(profile_location, pattern="^profile_location$")
        ],
        SELECT_REGION: [
            CallbackQueryHandler(select_region, pattern="^select_region_.*$"),
            CallbackQueryHandler(save_location, pattern="^save_location$"),
            CallbackQueryHandler(edit_profile_location, pattern="^edit_profile_location$")
        ],
        SELECT_DISTRICT: [
            CallbackQueryHandler(select_district, pattern="^select_district_.*$"),
            CallbackQueryHandler(save_location, pattern="^save_location$"),
            CallbackQueryHandler(select_country, pattern="^select_country_.*$")
        ],
        SELECT_SETTLEMENT: [
            CallbackQueryHandler(select_settlement, pattern="^select_settlement_.*$"),
            CallbackQueryHandler(save_location, pattern="^save_location$"),
            CallbackQueryHandler(select_region, pattern="^select_region_.*$")
        ]
    },
    fallbacks=[
        CallbackQueryHandler(main_menu, pattern="^Main_Menu$")
    ]
)