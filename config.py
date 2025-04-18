import os

# استرجاع متغيرات البيئة المطلوبة
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8125867347:AAFEh8OYVL-JpYGj1l6RRCXBqE7tG0WOzQQ")
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/points_db")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://nitrodz00.github.io/ForexFabric2025/")

# إعدادات نظام النقاط
DAILY_POINTS = 10  # نقاط المكافأة اليومية
REFERRAL_POINTS = 50  # نقاط الإحالة
SOCIAL_MEDIA_POINTS = 50  # نقاط زيارة مواقع التواصل الاجتماعي (مرة واحدة فقط)
TASK_POINTS = {
    "community": 20,  # نقاط المشاركة في المجتمع
    "profile": 15,    # نقاط استكمال الملف الشخصي
    "engagement": 5,  # نقاط التفاعل اليومي
    "instagram": SOCIAL_MEDIA_POINTS,  # نقاط زيارة انستقرام
    "telegram": SOCIAL_MEDIA_POINTS,   # نقاط زيارة تيليغرام
    "website": SOCIAL_MEDIA_POINTS,    # نقاط زيارة الموقع الرسمي
    "support": SOCIAL_MEDIA_POINTS     # نقاط زيارة خدمة الدعم
}

# المدة بين المطالبات اليومية (بالثواني)
DAILY_CLAIM_COOLDOWN = 24 * 60 * 60  # 24 ساعة

# روابط التواصل الاجتماعي
SOCIAL_MEDIA_LINKS = {
    "instagram": "https://www.instagram.com/forex_fabric?igsh=ajZzNnVxb3oyM3J0",
    "telegram": "https://t.me/Forex_Fabric",
    "website": "http://www.forexfabric.com/",
    "support": "http://t.me/ForexFabric_support"
}
