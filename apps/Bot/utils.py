from asgiref.sync import sync_to_async
from .models.TelegramBot import TelegramUser, Channel, Referral
from TestAbdBot.settings import BASE_API_URL
import requests


async def save_user_to_db(data):
    user_id = data.id
    first_name = data.first_name
    username = data.username

    try:
        # Wrap the ORM operation with sync_to_async
        @sync_to_async
        def update_or_create_user():
            return TelegramUser.objects.update_or_create(
                user_id=user_id,  # Modeldagi `telegram_id` maydoniga moslashtirildi
                defaults={
                    "first_name": first_name,
                    "username": username,
                },
            )

        user, created = await update_or_create_user()
        return True
    except Exception as error:
        print(f"Error saving user to DB: {error}")
        return False


@sync_to_async
def create_channel(chat_id, chat_name: str, chat_type: str, url=None):
    channel = Channel.objects.create(
        channel_id=chat_id, name=chat_name, type=chat_type, url=url
    )
    return channel


@sync_to_async
def create_referral(referrer, referred_user, referral_price=0.0):
    referral = Referral.objects.create(
        referrer=referrer, referred_user=referred_user, referral_price=referral_price
    )
    return referral


def quotes():
    url = "https://quotes-api-self.vercel.app/quote"
    result = requests.get(url)
    return result.json()


import requests
from django.conf import settings
import os


# API configuration
API_BASE_URL = "http://192.168.100.14:8000/"  # Yangilangan API URL
REFRESH_TOKEN_URL = f"{API_BASE_URL}accounts/token/refresh/"


async def post_ad(data, telegram_user, image_path):
    """
    Sends a POST request to create an ad with the provided data and image.
    
    Args:
        data (dict): Dictionary containing ad data (title, link, ad_type, pricing, country, start_date, end_date, target_views, target_clicks).
        telegram_user: TelegramUser instance with access_token and refresh_token.
        image_path (str): Path to the image file in STATIC_ROOT.
    
    Returns:
        tuple: (success: bool, response_data: dict or None, error_message: str or None)
    """
    # Ma’lumotlarni UTF-8 ga aylantirish
    data = {k: v.encode('utf-8').decode('utf-8') if isinstance(v, str) else v for k, v in data.items()}
    print(f"Yuborilgan ma’lumotlar: {data}")
    
    # Fayl mavjudligini tekshirish
    if not os.path.exists(image_path):
        print(f"Rasm fayli topilmadi: {image_path}")
        return False, None, "Rasm fayli topilmadi!"
    
    headers = {"Authorization": f"Bearer {telegram_user.access_token}"}
    try:
        with open(image_path, 'rb') as image_file:
            files = {'image': image_file}
            print(f"Yuborilayotgan rasm: {image_path}")
            response = requests.post(f"{API_BASE_URL}accounts/ad-orders/", headers=headers, data=data, files=files)
        
        print(f"API javobi: Status {response.status_code}, Xabar: {response.text[:100]}")
        
        if response.status_code == 401:
            # Try refreshing token
            try:
                refresh_response = requests.post(REFRESH_TOKEN_URL, json={"refresh_token": telegram_user.refresh_token})
                print(f"Token yangilash: Status {refresh_response.status_code}, Xabar: {refresh_response.text[:100]}")
                if refresh_response.status_code == 200:
                    token_data = refresh_response.json()
                    telegram_user.access_token = token_data['access_token']
                    telegram_user.refresh_token = token_data.get('refresh_token', telegram_user.refresh_token)
                    telegram_user.save()
                    headers = {"Authorization": f"Bearer {telegram_user.access_token}"}
                    with open(image_path, 'rb') as image_file:
                        files = {'image': image_file}
                        response = requests.post(f"{API_BASE_URL}accounts/ad-orders/", headers=headers, data=data, files=files)
                    print(f"Qayta so'rov: Status {response.status_code}, Xabar: {response.text[:100]}")
                else:
                    telegram_user.access_token = None
                    telegram_user.refresh_token = None
                    telegram_user.save()
                    return False, None, "Tizimga qaytadan kiring!"
            except Exception as e:
                print(f"Token yangilash xatosi: {e}")
                telegram_user.access_token = None
                telegram_user.refresh_token = None
                telegram_user.save()
                return False, None, "Tizimga qaytadan kiring!"
        
        if response.status_code == 201:
            try:
                return True, response.json(), None
            except ValueError:
                print(f"API javobi JSON emas: {response.text[:100]}")
                return False, None, "API javobi noto‘g‘ri formatda!"
        else:
            print(f"Reklama yaratishda xatolik: Status {response.status_code}, Xabar: {response.text[:100]}")
            return False, None, f"Reklama yaratishda xatolik: {response.text[:100]}"
    except Exception as e:
        print(f"API so'rovida xato: {e}")
        return False, None, "API so'rovida xatolik!"