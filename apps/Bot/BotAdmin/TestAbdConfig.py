from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from TestAbdBot.settings import BASE_API_URL
from telegram.ext import ContextTypes
from asgiref.sync import sync_to_async


keyboardButton = [
    [
        KeyboardButton(text="📊 Stаtistikа"), 
        KeyboardButton(text="⚙️ Sozlаmаlаr")
    ],
    [
        KeyboardButton(text="Web Admin panel", web_app=WebAppInfo(url="https://backend.testabd.uz/admin"))
    ]
]

async def TestAbdMenu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("TestAbd boshqaruv menyusi")
    await update.callback_query.delete_message()
    await context.bot.send_message(chat_id=update.effective_user.id, text="TestAbd.uz boshqaruv menyusiga xush kelibsiz", reply_markup=ReplyKeyboardMarkup(keyboardButton, one_time_keyboard=True, resize_keyboard=True))

async def Statistika(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

import json
import requests
from django.conf import settings
from ..models.TelegramBot import TelegramUser
from django.core.exceptions import ObjectDoesNotExist

# API endpoints
STATS_API_URL = f'{BASE_API_URL}system/system-stats/'
REFRESH_TOKEN_URL = f'{BASE_API_URL}accounts/token/refresh/'
CONFIG_API_URL = f'{BASE_API_URL}system/system-config/'

async def get_system_config(telegram_user_id: int) -> tuple[dict, int]:
    """Fetch system config and its pk from the API using access_token, refreshing if necessary."""
    try:
        telegram_user = await sync_to_async(TelegramUser.objects.get)(user_id=telegram_user_id)
        access_token = telegram_user.access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        response = await sync_to_async(requests.get)(CONFIG_API_URL, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # Assume the response contains 'id' or 'pk' for the instance
            pk = data.get('id', data.get('pk', 1))  # Default to 1 if not found
            return data, pk

        if response.status_code == 401:
            refresh_response = await sync_to_async(requests.post)(REFRESH_TOKEN_URL, json={'refresh': telegram_user.refresh_token})
            if refresh_response.status_code == 200:
                new_tokens = refresh_response.json()
                telegram_user.access_token = new_tokens.get('access')
                await sync_to_async(telegram_user.save)()
                headers = {'Authorization': f'Bearer {new_tokens.get("access")}'}
                retry_response = await sync_to_async(requests.get)(CONFIG_API_URL, headers=headers)
                if retry_response.status_code == 200:
                    data = retry_response.json()
                    pk = data.get('id', data.get('pk', 1))
                    return data, pk
                else:
                    raise Exception("Failed to fetch config after token refresh")
            else:
                telegram_user.access_token = None
                telegram_user.refresh_token = None
                await sync_to_async(telegram_user.save)()
                raise Exception("Refresh token invalid, tokens cleared")
        
        raise Exception(f"API request failed with status {response.status_code}")

    except ObjectDoesNotExist:
        raise Exception("Telegram user not found")
    except Exception as e:
        raise Exception(f"Error fetching config: {str(e)}")

# Sections available for navigation
SECTIONS = {
    'user_stats': '👥 Foydalanuvchilar',
    'test_stats': '📝 Testlar',
    'question_stats': '❓ Savollar',
    'ad_stats': '📢 Reklamalar',
    'coin_stats': '💰 Coinlar',
    'chat_stats': '💬 Chatlar',
    'notification_stats': '🔔 Bildirishnomalar',
    'location_stats': '📍 Joylashuv',
    'subscription_stats': '📊 Obunalar',
    'social_stats': '🌐 Ijtimoiy'
}

async def get_stats_data(telegram_user_id):
    """Fetch stats data from the API using access_token, refreshing if necessary."""
    try:
        telegram_user = await sync_to_async(TelegramUser.objects.get)(user_id=telegram_user_id)
        access_token = telegram_user.access_token
        headers = {'Authorization': f'Bearer {access_token}'}

        # First attempt to fetch stats
        response = requests.get(STATS_API_URL, headers=headers)
        
        if response.status_code == 200:
            return response.json()

        if response.status_code == 401:  # Unauthorized, try refreshing token
            refresh_response = requests.post(REFRESH_TOKEN_URL, json={'refresh': telegram_user.refresh_token})
            
            if refresh_response.status_code == 200:
                new_tokens = refresh_response.json()
                telegram_user.access_token = new_tokens.get('access')
                await sync_to_async(telegram_user.save)()
                # Retry with new access token
                headers = {'Authorization': f'Bearer {new_tokens.get("access")}'}
                response = requests.get(STATS_API_URL, headers=headers)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise Exception("Failed to fetch stats after token refresh")
            
            else:  # Refresh token invalid, clear tokens
                telegram_user.access_token = None
                telegram_user.refresh_token = None
                await sync_to_async(telegram_user.save)()
                raise Exception("Refresh token invalid, tokens cleared")
        
        raise Exception(f"API request failed with status {response.status_code}")

    except ObjectDoesNotExist:
        raise Exception("Telegram user not found")
    except Exception as e:
        raise Exception(f"Error fetching stats: {str(e)}")

async def check_user_role(telegram_user_id):
    """Check if the user has admin or developer role."""
    try:
        telegram_user = await sync_to_async(TelegramUser.objects.get)(user_id=telegram_user_id)
        return telegram_user.is_admin
    except ObjectDoesNotExist:
        return False

def format_stats_section(section_key, data):
    """Format a specific stats section into Markdown text."""
    section_data = data['data'].get(section_key, {})
    if not section_data:
        return f"*{SECTIONS[section_key]}*\nMa'lumotlar topilmadi."

    formatted = f"*{SECTIONS[section_key]}*\n\n"
    
    if section_key == 'user_stats':
        formatted += (
            f"👤 Umumiy foydalanuvchilar: {section_data.get('total_users', 0)}\n"
            f"✅ Faol foydalanuvchilar: {section_data.get('active_users', 0)}\n"
            f"💎 Premium foydalanuvchilar: {section_data.get('premium_users', 0)}\n"
            f"🏅 Nishonli foydalanuvchilar: {section_data.get('badged_users', 0)}\n"
            f"🕒 So'nggi 24 soatda yangi: {section_data.get('new_users_24h', 0)}\n"
            f"🕖 So'nggi 7 kunda yangi: {section_data.get('new_users_7d', 0)}\n"
            f"🕙 So'nggi 30 kunda yangi: {section_data.get('new_users_30d', 0)}\n"
            f"\n*Rollarga ko'ra:*\n"
        )
        for role in section_data.get('users_by_role', []):
            formatted += f"  - {role['role'].capitalize()}: {role['count']}\n"
        formatted += f"\n*Darajalarga ko'ra:*\n"
        for level in section_data.get('users_by_level', []):
            formatted += f"  - {level['level'].capitalize()}: {level['count']}\n"
        formatted += f"\n*Davlatlar bo'yicha:*\n"
        for country in section_data.get('users_by_country', []):
            formatted += f"  - {country['country__name']}: {country['count']}\n"
    
    elif section_key == 'test_stats':
        formatted += (
            f"📚 Umumiy testlar: {section_data.get('total_tests', 0)}\n"
            f"🌐 Ommaviy testlar: {section_data.get('public_tests', 0)}\n"
            f"📋 Qoralama testlar: {section_data.get('draft_tests', 0)}\n"
            f"🔒 Yashirin testlar: {section_data.get('unlisted_tests', 0)}\n"
            f"🏃 Faol testlar: {section_data.get('active_tests', 0)}\n"
            f"📊 O'rtacha ball: {section_data.get('average_score', 0):.2f}\n"
            f"🔄 Umumiy urinishlar: {section_data.get('total_attempts', 0)}\n"
            f"\n*Kategoriyalar bo'yicha:*\n"
        )
        for category in section_data.get('tests_by_category', []):
            formatted += f"  - {category['category__title']}: {category['count']}\n"
    
    elif section_key == 'question_stats':
        formatted += (
            f"❓ Umumiy savollar: {section_data.get('total_questions', 0)}\n"
            f"📈 O'rtacha qiyinlik: {section_data.get('avg_difficulty', 0):.2f}%\n"
            f"🔄 Umumiy urinishlar: {section_data.get('total_attempts', 0)}\n"
            f"✅ To'g'ri javoblar: {section_data.get('correct_attempts', 0)}\n"
            f"❌ Noto'g'ri javoblar: {section_data.get('wrong_attempts', 0)}\n"
            f"\n*Turlarga ko'ra:*\n"
        )
        for q_type in section_data.get('questions_by_type', []):
            formatted += f"  - {q_type['question_type'].replace('_', ' ').capitalize()}: {q_type['count']}\n"
    
    elif section_key == 'ad_stats':
        formatted += (
            f"📢 Umumiy reklamalar: {section_data.get('total_ads', 0)}\n"
            f"🏃 Faol reklamalar: {section_data.get('active_ads', 0)}\n"
            f"👀 Umumiy ko'rishlar: {section_data.get('total_views', 0)}\n"
            f"🖱️ Umumiy bosishlar: {section_data.get('total_clicks', 0)}\n"
            f"💸 Umumiy daromad: {section_data.get('total_revenue', 0):.2f}\n"
            f"\n*Turlarga ko'ra:*\n"
        )
        for ad_type in section_data.get('ads_by_type', []):
            formatted += f"  - {ad_type['ad_type'].capitalize()}: {ad_type['count']}\n"
    
    elif section_key == 'coin_stats':
        formatted += (
            f"💰 Umumiy tranzaksiyalar: {section_data.get('total_transactions', 0)}\n"
            f"📤 Taqsimlangan coinlar: {section_data.get('total_coins_distributed', 0)}\n"
            f"📥 Sarflangan coinlar: {section_data.get('total_coins_spent', 0)}\n"
            f"\n*Sabablarga ko'ra:*\n"
        )
        for reason in section_data.get('transactions_by_reason', []):
            formatted += f"  - {reason['reason'].replace('_', ' ').capitalize()}: {reason['count']} (Jami: {reason['total_amount']})\n"
    
    elif section_key == 'chat_stats':
        formatted += (
            f"💬 Umumiy chat xonalari: {section_data.get('total_chat_rooms', 0)}\n"
            f"👥 Guruh chatlari: {section_data.get('group_chats', 0)}\n"
            f"🤝 Shaxsiy chatlar: {section_data.get('private_chats', 0)}\n"
            f"✉️ Umumiy xabarlar: {section_data.get('total_messages', 0)}\n"
            f"🕒 So'nggi 24 soatdagi xabarlar: {section_data.get('messages_24h', 0)}\n"
            f"📎 Faylli xabarlar: {section_data.get('messages_with_files', 0)}\n"
            f"😊 Reaksiyali xabarlar: {section_data.get('messages_with_reactions', 0)}\n"
        )
    
    elif section_key == 'notification_stats':
        formatted += (
            f"🔔 Umumiy bildirishnomalar: {section_data.get('total_notifications', 0)}\n"
            f"📬 O'qilmagan bildirishnomalar: {section_data.get('unread_notifications', 0)}\n"
            f"\n*Turlarga ko'ra:*\n"
        )
        for n_type in section_data.get('notifications_by_type', []):
            formatted += f"  - {n_type['verb'].replace('_', ' ').capitalize()}: {n_type['count']}\n"
    
    elif section_key == 'location_stats':
        formatted += (
            f"🌍 Davlatlar: {section_data.get('countries', 0)}\n"
            f"🏞️ Viloyatlar: {section_data.get('regions', 0)}\n"
            f"🏙️ Tumanlar: {section_data.get('districts', 0)}\n"
            f"🏘️ Mahallalar: {section_data.get('settlements', 0)}\n"
        )
    
    elif section_key == 'subscription_stats':
        formatted += (
            f"📊 Umumiy obunalar: {section_data.get('total_subscriptions', 0)}\n"
            f"✅ Faol obunalar: {section_data.get('active_subscriptions', 0)}\n"
            f"\n*Turlarga ko'ra:*\n"
        )
        for s_type in section_data.get('subscriptions_by_type', []):
            formatted += f"  - {s_type['type'].capitalize()}: {s_type['count']}\n"
    
    elif section_key == 'social_stats':
        formatted += (
            f"👍 Yoqtirishlar: {section_data.get('total_likes', 0)}\n"
            f"💬 Izohlar: {section_data.get('total_comments', 0)}\n"
            f"👀 Ko'rishlar: {section_data.get('total_views', 0)}\n"
            f"👥 Kuzatuvchilar: {section_data.get('total_followers', 0)}\n"
            f"🔖 Xatcho'plar: {section_data.get('total_bookmarks', 0)}\n"
        )
    
    return formatted

from typing import List, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from typing import List, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import requests
from asgiref.sync import sync_to_async

# ... (Previous imports and SECTIONS dictionary unchanged)


def get_button_label(section: str, config: dict) -> str:
    """Return the button label with ♦️ if the corresponding feature is disabled."""
    feature_map = {
        'chat_stats': 'enable_chat',
        'ad_stats': 'enable_ads',
        'subscription_stats': 'enable_subscription',
        'coin_stats': 'enable_monetization',
        'notification_stats': 'enable_realtime_notifications',
        'test_stats': 'enable_test_creation'
    }
    feature = feature_map.get(section)
    if feature and not config.get(feature, True):
        return f"{SECTIONS[section]} ♦️"
    return SECTIONS[section]

async def start_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the Statistika message to display initial stats (user_stats)."""
    telegram_user_id = update.effective_user.id

    # Check if user has admin or developer role
    if not await check_user_role(telegram_user_id):
        await update.message.reply_text("❌ Sizda ushbu buyruqni ishlatish huquqi yo'q!")
        return

    try:
        # Fetch stats and config data
        stats_data = await get_stats_data(telegram_user_id)
        config_data, config_pk = await get_system_config(telegram_user_id)

        # Initialize user data for tracking navigation history
        context.user_data['stats_history'] = ['user_stats']
        context.user_data['current_section'] = 'user_stats'

        # Format initial section (user_stats)
        text = format_stats_section('user_stats', stats_data)

        # Create inline keyboard with all sections except the current one, in two columns
        other_sections: List[str] = [section for section in SECTIONS if section != 'user_stats']
        keyboard: List[List[InlineKeyboardButton]] = []
        for i in range(0, len(other_sections), 2):
            row: List[InlineKeyboardButton] = [
                InlineKeyboardButton(get_button_label(other_sections[i], config_data), callback_data=f"section:{other_sections[i]}")
            ]
            if i + 1 < len(other_sections):
                row.append(InlineKeyboardButton(get_button_label(other_sections[i+1], config_data), callback_data=f"section:{other_sections[i+1]}"))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("📋 Bosh menu", callback_data="main_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"❌ Xatolik yuz berdi: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks for section navigation."""
    query = update.callback_query
    await query.answer()

    telegram_user_id = query.from_user.id
    data = query.data
    current_section = context.user_data.get('current_section', 'user_stats')
    history = context.user_data.get('stats_history', ['user_stats'])

    try:
        # Fetch stats and config data
        stats_data = await get_stats_data(telegram_user_id)
        config_data, config_pk = await get_system_config(telegram_user_id)

        keyboard: List[List[InlineKeyboardButton]] = []
        if data == 'main_menu':
            # Reset to user_stats
            context.user_data['current_section'] = 'user_stats'
            context.user_data['stats_history'] = ['user_stats']
            text = format_stats_section('user_stats', stats_data)
            other_sections: List[str] = [section for section in SECTIONS if section != 'user_stats']
            for i in range(0, len(other_sections), 2):
                row: List[InlineKeyboardButton] = [
                    InlineKeyboardButton(get_button_label(other_sections[i], config_data), callback_data=f"section:{other_sections[i]}")
                ]
                if i + 1 < len(other_sections):
                    row.append(InlineKeyboardButton(get_button_label(other_sections[i+1], config_data), callback_data=f"section:{other_sections[i+1]}"))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("📋 Bosh menu", callback_data="main_menu")])
        
        elif data == 'back':
            # Go back to the previous section
            if len(history) > 1:
                history.pop()  # Remove current section
                previous_section = history[-1]
                context.user_data['current_section'] = previous_section
                text = format_stats_section(previous_section, stats_data)
                # Create keyboard with all sections except current, in two columns
                other_sections: List[str] = [section for section in SECTIONS if section != previous_section]
                for i in range(0, len(other_sections), 2):
                    row: List[InlineKeyboardButton] = [
                        InlineKeyboardButton(
                            get_button_label(other_sections[i], config_data) if other_sections[i] != history[-2] else get_button_label(history[-2], config_data),
                            callback_data=f"section:{other_sections[i]}" if other_sections[i] != history[-2] else "back"
                        )
                    ]
                    if i + 1 < len(other_sections):
                        row.append(InlineKeyboardButton(
                            get_button_label(other_sections[i+1], config_data) if other_sections[i+1] != history[-2] else get_button_label(history[-2], config_data),
                            callback_data=f"section:{other_sections[i+1]}" if other_sections[i+1] != history[-2] else "back"
                        ))
                    keyboard.append(row)
                keyboard.append([
                    InlineKeyboardButton("⬅️ Ortga", callback_data="back"),
                    InlineKeyboardButton("📋 Bosh menu", callback_data="main_menu")
                ])
            else:
                other_sections: List[str] = [section for section in SECTIONS if section != previous_section]
                for i in range(0, len(other_sections), 2):
                    row: List[InlineKeyboardButton] = [
                        InlineKeyboardButton(get_button_label(other_sections[i], config_data), callback_data=f"section:{other_sections[i]}")
                    ]
                    if i + 1 < len(other_sections):
                        row.append(InlineKeyboardButton(get_button_label(other_sections[i+1], config_data), callback_data=f"section:{other_sections[i+1]}"))
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("📋 Bosh menu", callback_data="main_menu")])
        
        elif data.startswith('section:'):
            # Switch to a new section
            new_section = data.split(':')[1]
            if new_section in SECTIONS:
                history.append(new_section)
                context.user_data['stats_history'] = history
                context.user_data['current_section'] = new_section
                text = format_stats_section(new_section, stats_data)
                # Create keyboard with all sections except current, in two columns
                previous_section = history[-2] if len(history) > 1 else None
                other_sections: List[str] = [section for section in SECTIONS if section != new_section]
                for i in range(0, len(other_sections), 2):
                    row: List[InlineKeyboardButton] = [
                        InlineKeyboardButton(
                            get_button_label(other_sections[i], config_data) if other_sections[i] != previous_section else get_button_label(current_section, config_data),
                            callback_data=f"section:{other_sections[i]}" if other_sections[i] != previous_section else "back"
                        )
                    ]
                    if i + 1 < len(other_sections):
                        row.append(InlineKeyboardButton(
                            get_button_label(other_sections[i+1], config_data) if other_sections[i+1] != previous_section else get_button_label(current_section, config_data),
                            callback_data=f"section:{other_sections[i+1]}" if other_sections[i+1] != previous_section else "back"
                        ))
                    keyboard.append(row)
                keyboard.append([
                    InlineKeyboardButton("⬅️ Ortga", callback_data="back"),
                    InlineKeyboardButton("📋 Bosh menu", callback_data="main_menu")
                ]) if len(history) > 1 else [
                    [InlineKeyboardButton(get_button_label(other_sections[i], config_data), callback_data=f"section:{other_sections[i]}")]
                    for i in range(len(other_sections) - 1, len(other_sections), 2)
                ] + [[InlineKeyboardButton("📋 Bosh menu", callback_data="main_menu")]]

        else:
            await query.message.reply_text("Noma'lum buyruq!")
            return

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=reply_markup)

    except Exception as e:
        await query.message.reply_text(f"❌ Xatolik yuz berdi: {str(e)}")
    """Handle inline button callbacks for section navigation."""
    query = update.callback_query
    await query.answer()

    telegram_user_id = query.from_user.id
    data = query.data
    current_section = context.user_data.get('current_section', 'user_stats')
    history = context.user_data.get('stats_history', ['user_stats'])

    try:
        # Fetch stats data
        stats_data = await get_stats_data(telegram_user_id)

        keyboard: List[List[InlineKeyboardButton]] = []
        if data == 'main_menu':
            # Reset to user_stats
            context.user_data['current_section'] = 'user_stats'
            context.user_data['stats_history'] = ['user_stats']
            text = format_stats_section('user_stats', stats_data)
            other_sections: List[str] = [section for section in SECTIONS if section != 'user_stats']
            for i in range(0, len(other_sections), 2):
                row: List[InlineKeyboardButton] = [
                    InlineKeyboardButton(SECTIONS[other_sections[i]], callback_data=f"section:{other_sections[i]}")
                ]
                if i + 1 < len(other_sections):
                    row.append(InlineKeyboardButton(SECTIONS[other_sections[i+1]], callback_data=f"section:{other_sections[i+1]}"))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("📋 Bosh menu", callback_data="main_menu")])
        
        elif data == 'back':
            # Go back to the previous section
            if len(history) > 1:
                history.pop()  # Remove current section
                previous_section = history[-1]
                context.user_data['current_section'] = previous_section
                text = format_stats_section(previous_section, stats_data)
                # Create keyboard with all sections except current, in two columns
                other_sections: List[str] = [section for section in SECTIONS if section != previous_section]
                for i in range(0, len(other_sections), 2):
                    row: List[InlineKeyboardButton] = [
                        InlineKeyboardButton(
                            SECTIONS[other_sections[i]] if other_sections[i] != history[-2] else SECTIONS[history[-2]],
                            callback_data=f"section:{other_sections[i]}" if other_sections[i] != history[-2] else "back"
                        )
                    ]
                    if i + 1 < len(other_sections):
                        row.append(InlineKeyboardButton(
                            SECTIONS[other_sections[i+1]] if other_sections[i+1] != history[-2] else SECTIONS[history[-2]],
                            callback_data=f"section:{other_sections[i+1]}" if other_sections[i+1] != history[-2] else "back"
                        ))
                    keyboard.append(row)
                keyboard.append([
                    InlineKeyboardButton("⬅️ Ortga", callback_data="back"),
                    InlineKeyboardButton("📋 Bosh menu", callback_data="main_menu")
                ])
            else:
                other_sections: List[str] = [section for section in SECTIONS if section != previous_section]
                for i in range(0, len(other_sections), 2):
                    row: List[InlineKeyboardButton] = [
                        InlineKeyboardButton(SECTIONS[other_sections[i]], callback_data=f"section:{other_sections[i]}")
                    ]
                    if i + 1 < len(other_sections):
                        row.append(InlineKeyboardButton(SECTIONS[other_sections[i+1]], callback_data=f"section:{other_sections[i+1]}"))
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("📋 Bosh menu", callback_data="main_menu")])
        
        elif data.startswith('section:'):
            # Switch to a new section
            new_section = data.split(':')[1]
            if new_section in SECTIONS:
                history.append(new_section)
                context.user_data['stats_history'] = history
                context.user_data['current_section'] = new_section
                text = format_stats_section(new_section, stats_data)
                # Create keyboard with all sections except current, in two columns
                previous_section = history[-2] if len(history) > 1 else None
                other_sections: List[str] = [section for section in SECTIONS if section != new_section]
                for i in range(0, len(other_sections), 2):
                    row: List[InlineKeyboardButton] = [
                        InlineKeyboardButton(
                            SECTIONS[other_sections[i]] if other_sections[i] != previous_section else SECTIONS[current_section],
                            callback_data=f"section:{other_sections[i]}" if other_sections[i] != previous_section else "back"
                        )
                    ]
                    if i + 1 < len(other_sections):
                        row.append(InlineKeyboardButton(
                            SECTIONS[other_sections[i+1]] if other_sections[i+1] != previous_section else SECTIONS[current_section],
                            callback_data=f"section:{other_sections[i+1]}" if other_sections[i+1] != previous_section else "back"
                        ))
                    keyboard.append(row)
                keyboard.append([
                    InlineKeyboardButton("⬅️ Ortga", callback_data="back"),
                    InlineKeyboardButton("📋 Bosh menu", callback_data="main_menu")
                ]) if len(history) > 1 else [
                    [InlineKeyboardButton(SECTIONS[other_sections[i]], callback_data=f"section:{other_sections[i]}")]
                    for i in range(len(other_sections) - 1, len(other_sections), 2)
                ] + [[InlineKeyboardButton("📋 Bosh menu", callback_data="main_menu")]]

        else:
            await query.message.reply_text("Noma'lum buyruq!")
            return

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, parse_mode='Markdown', reply_markup=reply_markup)

    except Exception as e:
        await query.message.reply_text(f"❌ Xatolik yuz berdi: {str(e)}")




def get_button_label(section: str, config: dict) -> str:
    """Return the button label with ♦️ if the corresponding feature is disabled."""
    feature_map = {
        'chat_stats': 'enable_chat',
        'ad_stats': 'enable_ads',
        'subscription_stats': 'enable_subscription'
    }
    feature = feature_map.get(section)
    if feature and not config.get(feature, True):
        return f"{SECTIONS[section]} ♦️"
    return SECTIONS[section]

def format_config_message(config: dict) -> str:
    """Format the config message with enabled features in HTML."""
    enabled_features = []
    field_labels = {
        'enable_chat': '💬 Chatlar',
        'enable_ads': '📢 Reklamalar',
        'enable_test_creation': '📝 Test yaratish',
        'enable_map_view': '📍 Xarita ko‘rinishi',
        'enable_realtime_notifications': '🔔 Real vaqtda bildirishnomalar',
        'enable_monetization': '💰 Monetizatsiya',
        'enable_subscription': '📊 Obunalar',
        'maintenance_mode': '🛠️ Texnik xizmat ko‘rsatish rejimi',
        'allow_registration': '📋 Ro‘yxatdan o‘tish',
        'require_premium_for_ad_free': '💎 Reklamasiz premium talab qilinadi',
        'require_verification_for_boosted_tests': '✅ Kuchaytirilgan testlar uchun tasdiqlash'
    }
    for field, label in field_labels.items():
        if config.get(field, False):
            enabled_features.append(f"<b>{label}</b>")
    
    message = "<b>⚙️ Tizim sozlamalari</b>\n\n"
    message += "<b>Yoniq funksiyalar:</b>\n"
    if enabled_features:
        message += "\n".join([f"• {feature}" for feature in enabled_features])
    else:
        message += "Hech qanday funksiya yoniq emas."
    return message

async def edit_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /edit_config command to display and edit system configuration."""
    telegram_user_id = update.effective_user.id

    if not await check_user_role(telegram_user_id):
        await update.message.reply_text("<b>❌ Sizda ushbu buyruqni ishlatish huquqi yo‘q!</b>", parse_mode='HTML')
        return

    try:
        config_data, config_pk = await get_system_config(telegram_user_id)
        context.user_data['config'] = config_data.copy()
        context.user_data['config_pk'] = config_pk
        context.user_data['editing_field'] = None

        text = format_config_message(config_data)
        fields = [
            ('enable_chat', '💬 Chatlar'),
            ('enable_ads', '📢 Reklamalar'),
            ('enable_test_creation', '📝 Test yaratish'),
            ('enable_map_view', '📍 Xarita ko‘rinishi'),
            ('enable_realtime_notifications', '🔔 Real vaqtda bildirishnomalar'),
            ('enable_monetization', '💰 Monetizatsiya'),
            ('enable_subscription', '📊 Obunalar'),
            ('maintenance_mode', '🛠️ Texnik xizmat rejimi'),
            ('allow_registration', '📋 Ro‘yxatdan o‘tish'),
            ('require_premium_for_ad_free', '💎 Reklamasiz premium'),
            ('require_verification_for_boosted_tests', '✅ Kuchaytirilgan testlar'),
            ('max_test_attempts_per_user', '🔢 Max test urinishlari'),
            ('min_days_between_attempts', '📅 Urinishlar orasidagi kunlar'),
            ('min_tests_required_for_creation', '📚 Test yaratish uchun testlar'),
            ('default_feed_page_size', '📏 Feed sahifasi hajmi'),
            ('default_language', '🌐 Standart til')
        ]
        keyboard: List[List[InlineKeyboardButton]] = []
        for i in range(0, len(fields), 2):
            row: List[InlineKeyboardButton] = [
                InlineKeyboardButton(
                    f"{fields[i][1]} {'🟢' if config_data.get(fields[i][0], False) else '🔴'}" if fields[i][0] in config_data and isinstance(config_data[fields[i][0]], bool) else fields[i][1],
                    callback_data=f"edit_config:{fields[i][0]}"
                )
            ]
            if i + 1 < len(fields):
                row.append(InlineKeyboardButton(
                    f"{fields[i+1][1]} {'🟢' if config_data.get(fields[i+1][0], False) else '🔴'}" if fields[i+1][0] in config_data and isinstance(config_data[fields[i+1][0]], bool) else fields[i+1][1],
                    callback_data=f"edit_config:{fields[i+1][0]}"
                ))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("💾 Saqlash", callback_data="edit_config:save")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"<b>❌ Xatolik yuz berdi:</b> {str(e)}", parse_mode='HTML')

async def button_callback_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks for config editing."""
    query = update.callback_query
    await query.answer()

    telegram_user_id = query.from_user.id
    data = query.data

    try:
        config_data = context.user_data.get('config', None)
        config_pk = context.user_data.get('config_pk', None)
        if not config_data or not config_pk:
            config_data, config_pk = await get_system_config(telegram_user_id)
            context.user_data['config'] = config_data
            context.user_data['config_pk'] = config_pk

        if data == 'edit_config:save':
            telegram_user = await sync_to_async(TelegramUser.objects.get)(user_id=telegram_user_id)
            headers = {'Authorization': f'Bearer {telegram_user.access_token}'}
            update_url = f"{CONFIG_API_URL}{config_pk}/"
            response = await sync_to_async(requests.put)(update_url, json=config_data, headers=headers)
            
            if response.status_code in [200, 201]:
                await query.edit_message_text(
                    "<b>✅ Sozlamalar muvaffaqiyatli yangilandi!</b>",
                    parse_mode='HTML'
                )
                context.user_data.pop('config', None)
                context.user_data.pop('config_pk', None)
                context.user_data.pop('editing_field', None)
                return
            elif response.status_code == 401:
                refresh_response = await sync_to_async(requests.post)(REFRESH_TOKEN_URL, json={'refresh': telegram_user.refresh_token})
                if refresh_response.status_code == 200:
                    new_tokens = refresh_response.json()
                    telegram_user.access_token = new_tokens.get('access')
                    await sync_to_async(telegram_user.save)()
                    headers = {'Authorization': f'Bearer {new_tokens.get("access")}'}
                    retry_response = await sync_to_async(requests.put)(update_url, json=config_data, headers=headers)
                    if retry_response.status_code in [200, 201]:
                        await query.edit_message_text(
                            "<b>✅ Sozlamalar muvaffaqiyatli yangilandi!</b>",
                            parse_mode='HTML'
                        )
                        context.user_data.pop('config', None)
                        context.user_data.pop('config_pk', None)
                        context.user_data.pop('editing_field', None)
                        return
                    else:
                        raise Exception(f"Failed to update config after token refresh: {retry_response.status_code}")
                else:
                    telegram_user.access_token = None
                    telegram_user.refresh_token = None
                    await sync_to_async(telegram_user.save)()
                    raise Exception("Refresh token invalid, tokens cleared")
            else:
                raise Exception(f"Failed to update config: {response.status_code}")

        elif data == 'edit_config:cancel':
            context.user_data['editing_field'] = None
            text = format_config_message(config_data)
            fields = [
                ('enable_chat', '💬 Chatlar'),
                ('enable_ads', '📢 Reklamalar'),
                ('enable_test_creation', '📝 Test yaratish'),
                ('enable_map_view', '📍 Xarita ko‘rinishi'),
                ('enable_realtime_notifications', '🔔 Real vaqtda bildirishnomalar'),
                ('enable_monetization', '💰 Monetizatsiya'),
                ('enable_subscription', '📊 Obunalar'),
                ('maintenance_mode', '🛠️ Texnik xizmat rejimi'),
                ('allow_registration', '📋 Ro‘yxatdan o‘tish'),
                ('require_premium_for_ad_free', '💎 Reklamasiz premium'),
                ('require_verification_for_boosted_tests', '✅ Kuchaytirilgan testlar'),
                ('max_test_attempts_per_user', '🔢 Max test urinishlari'),
                ('min_days_between_attempts', '📅 Urinishlar orasidagi kunlar'),
                ('min_tests_required_for_creation', '📚 Test yaratish uchun testlar'),
                ('default_feed_page_size', '📏 Feed sahifasi hajmi'),
                ('default_language', '🌐 Standart til')
            ]
            keyboard: List[List[InlineKeyboardButton]] = []
            for i in range(0, len(fields), 2):
                row: List[InlineKeyboardButton] = [
                    InlineKeyboardButton(
                        f"{fields[i][1]} {'🟢' if config_data.get(fields[i][0], False) else '🔴'}" if fields[i][0] in config_data and isinstance(config_data[fields[i][0]], bool) else fields[i][1],
                        callback_data=f"edit_config:{fields[i][0]}"
                    )
                ]
                if i + 1 < len(fields):
                    row.append(InlineKeyboardButton(
                        f"{fields[i+1][1]} {'🟢' if config_data.get(fields[i+1][0], False) else '🔴'}" if fields[i+1][0] in config_data and isinstance(config_data[fields[i+1][0]], bool) else fields[i+1][1],
                        callback_data=f"edit_config:{fields[i+1][0]}"
                    ))
                keyboard.append(row)
            keyboard.append([InlineKeyboardButton("💾 Saqlash", callback_data="edit_config:save")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(text=text, parse_mode='HTML', reply_markup=reply_markup)
            return

        elif data.startswith('edit_config:'):
            field = data.split(':')[1]
            if field in [
                'enable_chat', 'enable_ads', 'enable_test_creation', 'enable_map_view',
                'enable_realtime_notifications', 'enable_monetization', 'enable_subscription',
                'maintenance_mode', 'allow_registration', 'require_premium_for_ad_free',
                'require_verification_for_boosted_tests'
            ]:
                config_data[field] = not config_data.get(field, False)
                context.user_data['config'] = config_data
                text = format_config_message(config_data)
                fields = [
                    ('enable_chat', '💬 Chatlar'),
                    ('enable_ads', '📢 Reklamalar'),
                    ('enable_test_creation', '📝 Test yaratish'),
                    ('enable_map_view', '📍 Xarita ko‘rinishi'),
                    ('enable_realtime_notifications', '🔔 Real vaqtda bildirishnomalar'),
                    ('enable_monetization', '💰 Monetizatsiya'),
                    ('enable_subscription', '📊 Obunalar'),
                    ('maintenance_mode', '🛠️ Texnik xizmat rejimi'),
                    ('allow_registration', '📋 Ro‘yxatdan o‘tish'),
                    ('require_premium_for_ad_free', '💎 Reklamasiz premium'),
                    ('require_verification_for_boosted_tests', '✅ Kuchaytirilgan testlar'),
                    ('max_test_attempts_per_user', '🔢 Max test urinishlari'),
                    ('min_days_between_attempts', '📅 Urinishlar orasidagi kunlar'),
                    ('min_tests_required_for_creation', '📚 Test yaratish uchun testlar'),
                    ('default_feed_page_size', '📏 Feed sahifasi hajmi'),
                    ('default_language', '🌐 Standart til')
                ]
                keyboard: List[List[InlineKeyboardButton]] = []
                for i in range(0, len(fields), 2):
                    row: List[InlineKeyboardButton] = [
                        InlineKeyboardButton(
                            f"{fields[i][1]} {'🟢' if config_data.get(fields[i][0], False) else '🔴'}" if fields[i][0] in config_data and isinstance(config_data[fields[i][0]], bool) else fields[i][1],
                            callback_data=f"edit_config:{fields[i][0]}"
                        )
                    ]
                    if i + 1 < len(fields):
                        row.append(InlineKeyboardButton(
                            f"{fields[i+1][1]} {'🟢' if config_data.get(fields[i+1][0], False) else '🔴'}" if fields[i+1][0] in config_data and isinstance(config_data[fields[i+1][0]], bool) else fields[i+1][1],
                            callback_data=f"edit_config:{fields[i+1][0]}"
                        ))
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("💾 Saqlash", callback_data="edit_config:save")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(text=text, parse_mode='HTML', reply_markup=reply_markup)
            
            elif field in ['max_test_attempts_per_user', 'min_days_between_attempts', 'min_tests_required_for_creation', 'default_feed_page_size', 'default_language']:
                context.user_data['editing_field'] = field
                field_labels = {
                    'max_test_attempts_per_user': 'Maksimal test urinishlari soni',
                    'min_days_between_attempts': 'Urinishlar orasidagi minimal kunlar',
                    'min_tests_required_for_creation': 'Test yaratish uchun zarur testlar soni',
                    'default_feed_page_size': 'Feed sahifasi hajmi',
                    'default_language': 'Standart til'
                }
                example_value = config_data[field] if config_data.get(field) else '5' if field != 'default_language' else 'uz'
                await query.message.reply_text(
                    f"<b>✍️ {field_labels[field]} uchun yangi qiymatni kiriting:</b>\n"
                    f"Masalan: <code>/{example_value}</code>",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Bekor qilish", callback_data="edit_config:cancel")]
                    ])
                )
            
            else:
                await query.message.reply_text("<b>❌ Noma‘lum sozlama!</b>", parse_mode='HTML')
                return

    except Exception as e:
        await query.message.reply_text(f"<b>❌ Xatolik yuz berdi:</b> {str(e)}", parse_mode='HTML')

async def handle_config_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle command-based input for non-boolean config fields (e.g., /10, /uz)."""
    telegram_user_id = update.effective_user.id
    editing_field = context.user_data.get('editing_field')

    if not editing_field:
        await update.message.reply_text("<b>❌ Hech qanday sozlama tahrirlanmoqda emas!</b>", parse_mode='HTML')
        return

    try:
        if not await check_user_role(telegram_user_id):
            await update.message.reply_text("<b>❌ Sizda ushbu buyruqni ishlatish huquqi yo‘q!</b>", parse_mode='HTML')
            context.user_data['editing_field'] = None
            return

        config_data = context.user_data.get('config', None)
        if not config_data:
            config_data, config_pk = await get_system_config(telegram_user_id)
            context.user_data['config'] = config_data
            context.user_data['config_pk'] = config_pk

        user_input = update.message.text.strip()
        
        if user_input.startswith('/'):
            user_input = user_input[1:]
        else:
            await update.message.reply_text(
                f"<b>❌ Qiymat komanda sifatida kiritilishi kerak!</b>\n"
                f"Masalan: <code>/{config_data[editing_field] or '5'}</code>",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Bekor qilish", callback_data="edit_config:cancel")]
                ])
            )
            return

        if editing_field in ['max_test_attempts_per_user', 'min_days_between_attempts', 'min_tests_required_for_creation', 'default_feed_page_size']:
            try:
                value = int(user_input)
                if value < 0:
                    raise ValueError("Qiymat 0 yoki undan katta bo‘lishi kerak!")
                config_data[editing_field] = value
            except ValueError:
                await update.message.reply_text(
                    f"<b>❌ Noto‘g‘ri qiymat kiritildi! Iltimos, butun son kiriting.</b>\n"
                    f"Masalan: <code>/{config_data[editing_field] or '5'}</code>",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Bekor qilish", callback_data="edit_config:cancel")]
                    ])
                )
                return
        elif editing_field == 'default_language':
            if not user_input:
                await update.message.reply_text(
                    f"<b>❌ Til kodi bo‘sh bo‘lishi mumkin emas!</b>\n"
                    f"Masalan: <code>/{config_data[editing_field] or 'uz'}</code>",
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("❌ Bekor qilish", callback_data="edit_config:cancel")]
                    ])
                )
                return
            config_data[editing_field] = user_input

        context.user_data['config'] = config_data
        context.user_data['editing_field'] = None

        text = format_config_message(config_data)
        fields = [
            ('enable_chat', '💬 Chatlar'),
            ('enable_ads', '📢 Reklamalar'),
            ('enable_test_creation', '📝 Test yaratish'),
            ('enable_map_view', '📍 Xarita ko‘rinishi'),
            ('enable_realtime_notifications', '🔔 Real vaqtda bildirishnomalar'),
            ('enable_monetization', '💰 Monetizatsiya'),
            ('enable_subscription', '📊 Obunalar'),
            ('maintenance_mode', '🛠️ Texnik xizmat rejimi'),
            ('allow_registration', '📋 Ro‘yxatdan o‘tish'),
            ('require_premium_for_ad_free', '💎 Reklamasiz premium'),
            ('require_verification_for_boosted_tests', '✅ Kuchaytirilgan testlar'),
            ('max_test_attempts_per_user', '🔢 Max test urinishlari'),
            ('min_days_between_attempts', '📅 Urinishlar orasidagi kunlar'),
            ('min_tests_required_for_creation', '📚 Test yaratish uchun testlar'),
            ('default_feed_page_size', '📏 Feed sahifasi hajmi'),
            ('default_language', '🌐 Standart til')
        ]
        keyboard: List[List[InlineKeyboardButton]] = []
        for i in range(0, len(fields), 2):
            row: List[InlineKeyboardButton] = [
                InlineKeyboardButton(
                    f"{fields[i][1]} {'🟢' if config_data.get(fields[i][0], False) else '🔴'}" if fields[i][0] in config_data and isinstance(config_data[fields[i][0]], bool) else fields[i][1],
                    callback_data=f"edit_config:{fields[i][0]}"
                )
            ]
            if i + 1 < len(fields):
                row.append(InlineKeyboardButton(
                    f"{fields[i+1][1]} {'🟢' if config_data.get(fields[i+1][0], False) else '🔴'}" if fields[i+1][0] in config_data and isinstance(config_data[fields[i+1][0]], bool) else fields[i+1][1],
                    callback_data=f"edit_config:{fields[i+1][0]}"
                ))
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("💾 Saqlash", callback_data="edit_config:save")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"<b>❌ Xatolik yuz berdi:</b> {str(e)}", parse_mode='HTML')
