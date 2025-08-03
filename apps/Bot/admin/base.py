from django.contrib import admin
from ..models.TelegramBot import TelegramUser, Channel, Referral, Guide, Appeal
from django.contrib import admin
from unfold.admin import ModelAdmin


@admin.register(TelegramUser)
class UserAdmin(ModelAdmin):
    list_display = (
        "user_id",
        "first_name",
        "username",
        "is_active",
        "is_admin",
        "date_joined",
        "last_active",
    )
    list_filter = ("is_active", "is_admin")
    search_fields = ("username", "first_name")
    ordering = ("user_id",)
    list_editable = ("is_active", "is_admin")


@admin.register(Channel)
class ChannelAdmin(ModelAdmin):
    list_display = ("name", "type", "url", "channel_id")  # Jadval ustunlari
    list_filter = ("type",)  # Filtrlash uchun ustunlar
    search_fields = ("name", "channel_id")  # Qidiruv uchun ustunlar


@admin.register(Referral)
class ReferralAdmin(ModelAdmin):
    list_display = ("referrer", "referred_user", "created_at")  # Jadval ustunlari
    search_fields = (
        "referrer__username",
        "referred_user__username",
    )  # Qidiruv uchun ustunlar


@admin.register(Guide)
class GuideAdmin(ModelAdmin):
    list_display = ("title", "status", "created_at")
    search_fields = ("title", "content")


@admin.register(Appeal)
class AppealAdmin(ModelAdmin):
    list_display = ("user", "message", "created_at")
    search_fields = ("user__username", "message")
    list_filter = ("created_at",)
