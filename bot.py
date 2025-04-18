import logging
import time
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
import json

from database import (
    add_user, get_user, daily_claim, can_claim_daily, get_referrals,
    add_referral, get_user_activities, add_task_completion, reset_user_points,
    social_media_visit, get_social_media_visits
)
from config import SOCIAL_MEDIA_LINKS, WEBAPP_URL, 8125867347:AAFEh8OYVL-JpYGj1l6RRCXBqE7tG0WOzQQ

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def start(update: Update, context: CallbackContext):
    """أمر البدء - تسجيل المستخدم وتوفير الرابط لتطبيق الويب"""
    user = update.message.from_user
    user_id = user.id
    username = user.username or user.first_name
    full_name = f"{user.first_name} {user.last_name if user.last_name else ''}"
    
    # التحقق من وجود معلومات إحالة
    if context.args and context.args[0].isdigit():
        referrer_id = int(context.args[0])
        if referrer_id != user_id:  # لا يمكن للمستخدم إحالة نفسه
            add_user(user_id, username, full_name)
            process_referral(update, context)
            return

    # إضافة المستخدم مع الاسم الكامل
    add_user(user_id, username, full_name)
    
    # إنشاء زر لفتح تطبيق الويب
    keyboard = [
        [InlineKeyboardButton("📱 فتح تطبيق الويب", url=f"{WEBAPP_URL}?user_id={user.id}")],
        [InlineKeyboardButton("💰 احصل على نقاطك اليومية", callback_data="daily_claim")],
        [InlineKeyboardButton("👥 دعوة أصدقاء", callback_data="referral")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        f"🎉 مرحبًا {full_name}!\n\n"
        f"أهلاً بك في شركة Forex Fabric. يمكنك كسب النقاط من خلال المهام اليومية والإحالات.\n\n"
        f"استخدم /help لمعرفة الأوامر المتاحة.",
        reply_markup=reply_markup
    )

def handle_callback(update: Update, context: CallbackContext):
    """التعامل مع الأزرار التفاعلية"""
    query = update.callback_query
    query.answer()
    
    if query.data == "daily_claim":
        daily_claim_handler(update, context)
    elif query.data == "referral":
        referral_handler(update, context)
    elif query.data == "tasks":
        tasks_handler(update, context)
    elif query.data.startswith("social_"):
        social_type = query.data.replace("social_", "")
        social_media_handler(update, context, social_type)

def daily_claim_handler(update: Update, context: CallbackContext):
    """التعامل مع المطالبة اليومية من خلال الأزرار"""
    user_id = update.callback_query.from_user.id
    result, data = daily_claim(user_id)
    
    if not result:
        if isinstance(data, int):
            # تحويل الثواني إلى صيغة مقروءة
            hours, remainder = divmod(data, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{int(hours)} ساعة و {int(minutes)} دقيقة"
            update.callback_query.message.reply_text(f"⏳ لا يمكنك المطالبة الآن. يرجى الانتظار {time_str}.")
        else:
            update.callback_query.message.reply_text(f"⚠️ {data}")
    else:
        # تم المطالبة بنجاح
        points = data['points']
        total_points = data['total_points']
        points_added = data['points_added']
        
        update.callback_query.message.reply_text(
            f"🎁 تمت إضافة {points_added} نقطة بنجاح!\n"
            f"رصيدك الحالي: {points} نقطة\n"
            f"إجمالي النقاط: {total_points} نقطة"
        )

def daily_claim_command(update: Update, context: CallbackContext):
    """السماح للمستخدمين بالمطالبة بالنقاط اليومية"""
    user_id = update.message.from_user.id
    result, data = daily_claim(user_id)
    
    if not result:
        if isinstance(data, int):
            # تحويل الثواني إلى صيغة مقروءة
            hours, remainder = divmod(data, 3600)
            minutes, seconds = divmod(remainder, 60)
            time_str = f"{int(hours)} ساعة و {int(minutes)} دقيقة"
            update.message.reply_text(f"⏳ لا يمكنك المطالبة الآن. يرجى الانتظار {time_str}.")
        else:
            update.message.reply_text(f"⚠️ {data}")
    else:
        # تم المطالبة بنجاح
        points = data['points']
        total_points = data['total_points']
        points_added = data['points_added']
        
        update.message.reply_text(
            f"🎁 تمت إضافة {points_added} نقطة بنجاح!\n"
            f"رصيدك الحالي: {points} نقطة\n"
            f"إجمالي النقاط: {total_points} نقطة"
        )

def balance_command(update: Update, context: CallbackContext):
    """عرض رصيد النقاط الحالي للمستخدم"""
    user_id = update.message.from_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        update.message.reply_text("⚠️ لم يتم العثور على بيانات المستخدم. يرجى استخدام /start أولاً.")
        return
        
    points, total_points, last_claim, username, full_name = user_data
    referrals_count = get_referrals(user_id)
    
    update.message.reply_text(
        f"💰 رصيد نقاطك الحالي: {points} نقطة\n"
        f"📊 إجمالي النقاط المكتسبة: {total_points} نقطة\n"
        f"👥 عدد الإحالات: {referrals_count}\n\n"
        f"استخدم /daily_claim للحصول على نقاطك اليومية."
    )

def referral_handler(update: Update, context: CallbackContext):
    """التعامل مع طلب الإحالة من الأزرار"""
    user_id = update.callback_query.from_user.id
    bot_username = context.bot.username
    
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    update.callback_query.message.reply_text(
        f"👥 دعوة أصدقاء\n\n"
        f"انسخ الرابط التالي وأرسله لأصدقائك. عندما يقومون بتسجيل الدخول، ستحصل على 50 نقطة مكافأة!\n\n"
        f"{referral_link}"
    )

def referral_command(update: Update, context: CallbackContext):
    """إنشاء رابط إحالة للمستخدم"""
    user_id = update.message.from_user.id
    bot_username = context.bot.username
    
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    keyboard = [
        [InlineKeyboardButton("📱 فتح تطبيق الويب", url=f"{WEBAPP_URL}?user_id={user_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"👥 دعوة أصدقاء\n\n"
        f"انسخ الرابط التالي وأرسله لأصدقائك. عندما يقومون بتسجيل الدخول، ستحصل على 50 نقطة مكافأة!\n\n"
        f"{referral_link}",
        reply_markup=reply_markup
    )

def tasks_command(update: Update, context: CallbackContext):
    """عرض المهام المتاحة للمستخدم"""
    user_id = update.message.from_user.id
    
    # قائمة بمواقع التواصل الاجتماعي التي زارها المستخدم
    visited_socials = get_social_media_visits(user_id)
    
    # إنشاء أزرار لمواقع التواصل الاجتماعي
    keyboard = []
    
    # إضافة أزرار لمواقع التواصل الاجتماعي
    social_icons = {
        "instagram": "📸",
        "telegram": "📱",
        "website": "🌐",
        "support": "🆘"
    }
    
    social_names = {
        "instagram": "انستغرام",
        "telegram": "تيليغرام",
        "website": "الموقع الرسمي",
        "support": "الدعم الفني"
    }
    
    for social_type, url in SOCIAL_MEDIA_LINKS.items():
        icon = social_icons.get(social_type, "🔗")
        name = social_names.get(social_type, social_type)
        status = "✅" if social_type in visited_socials else "🔹"
        
        keyboard.append([
            InlineKeyboardButton(
                f"{status} {icon} زيارة {name}", 
                callback_data=f"social_{social_type}" if social_type not in visited_socials else "social_done",
                url=url if social_type not in visited_socials else None
            )
        ])
    
    # إضافة زر للعودة
    keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="back")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"📋 المهام المتاحة\n\n"
        f"قم بزيارة مواقع التواصل الاجتماعي للحصول على 50 نقطة لكل موقع (مرة واحدة فقط):",
        reply_markup=reply_markup
    )

def social_media_handler(update: Update, context: CallbackContext, social_type):
    """التعامل مع زيارات مواقع التواصل الاجتماعي"""
    user_id = update.callback_query.from_user.id
    
    if social_type == "done":
        update.callback_query.message.reply_text("✅ لقد قمت بزيارة هذا الموقع بالفعل.")
        return
    
    if social_type not in SOCIAL_MEDIA_LINKS:
        update.callback_query.message.reply_text("⚠️ خطأ: موقع التواصل الاجتماعي غير معروف.")
        return
    
    result, data = social_media_visit(user_id, social_type)
    
    if not result:
        update.callback_query.message.reply_text(f"⚠️ {data}")
    else:
        # تم تسجيل الزيارة بنجاح
        points = data['points']
        total_points = data['total_points']
        points_added = data['points_added']
        
        social_names = {
            "instagram": "انستغرام",
            "telegram": "تيليغرام",
            "website": "الموقع الرسمي",
            "support": "الدعم الفني"
        }
        
        name = social_names.get(social_type, social_type)
        
        update.callback_query.message.reply_text(
            f"✅ تمت زيارة {name} بنجاح!\n"
            f"🎁 تمت إضافة {points_added} نقطة بنجاح!\n"
            f"💰 رصيدك الحالي: {points} نقطة\n"
            f"📊 إجمالي النقاط: {total_points} نقطة"
        )

def history_command(update: Update, context: CallbackContext):
    """عرض تاريخ نشاطات المستخدم"""
    user_id = update.message.from_user.id
    activities = get_user_activities(user_id, 5)  # عرض آخر 5 نشاطات
    
    if not activities:
        update.message.reply_text("📝 لا توجد نشاطات سابقة.")
        return
        
    activity_names = {
        "daily_claim": "المكافأة اليومية",
        "referral": "إحالة صديق",
        "task_completion": "إكمال مهمة",
        "social_instagram": "زيارة انستغرام",
        "social_telegram": "زيارة تيليغرام",
        "social_website": "زيارة الموقع الرسمي",
        "social_support": "زيارة الدعم الفني",
    }
    
    message = "📝 آخر النشاطات:\n\n"
    
    for activity in activities:
        activity_type, points, created_at, details = activity
        activity_name = activity_names.get(activity_type, activity_type)
        sign = '+' if points > 0 else ''
        
        message += f"• {activity_name}: {sign}{points} نقطة ({created_at.strftime('%Y-%m-%d %H:%M')})\n"
    
    update.message.reply_text(message)

def help_command(update: Update, context: CallbackContext):
    """عرض معلومات المساعدة"""
    update.message.reply_text(
        "🔍 الأوامر المتاحة:\n\n"
        "/start - بدء البوت وفتح تطبيق الويب\n"
        "/daily_claim - الحصول على النقاط اليومية\n"
        "/balance - عرض رصيدك الحالي\n"
        "/referral - الحصول على رابط الإحالة الخاص بك\n"
        "/tasks - عرض المهام المتاحة\n"
        "/history - عرض تاريخ نشاطاتك\n"
        "/help - عرض هذه المساعدة\n"
        "/leaderboard - عرض لوحة المتصدرين\n\n"
        "🌐 روابط مهمة:\n"
        "• انستغرام: https://www.instagram.com/forex_fabric\n"
        "• تيليغرام: https://t.me/Forex_Fabric\n"
        "• الموقع الرسمي: http://www.forexfabric.com\n"
        "• الدعم: https://t.me/ForexFabric_support"
    )

def leaderboard_command(update: Update, context: CallbackContext):
    """عرض لوحة المتصدرين"""
    from database import get_leaderboard
    
    leaderboard = get_leaderboard(10)  # عرض أفضل 10 مستخدمين
    
    if not leaderboard:
        update.message.reply_text("🏆 لا توجد بيانات متاحة للوحة المتصدرين.")
        return
        
    message = "🏆 لوحة المتصدرين (أعلى 10):\n\n"
    
    for i, (user_id, username, points, total_points) in enumerate(leaderboard, 1):
        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f"{i}."
        message += f"{medal} {username}: {points} نقطة\n"
    
    update.message.reply_text(message)

def process_referral(update: Update, context: CallbackContext):
    """معالجة الإحالات عندما يبدأ المستخدم البوت باستخدام رابط الإحالة"""
    if not context.args or not context.args[0].isdigit():
        return

    referred_id = update.message.from_user.id
    referrer_id = int(context.args[0])
    
    # التأكد من أن المستخدم لا يحيل نفسه
    if referred_id == referrer_id:
        return
    
    result, data = add_referral(referrer_id, referred_id)
    
    if result:
        update.message.reply_text(
            "👥 تمت إضافتك بنجاح من خلال رابط إحالة! تم منح المستخدم الذي دعاك 50 نقطة."
        )
    # عدم إظهار رسالة خطأ للمستخدم المحال إذا كانت الإحالة موجودة بالفعل

def start_bot():
    """تهيئة وتشغيل بوت تيليجرام"""
    logger.info("جاري تشغيل البوت...")
    
    updater = Updater(TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher
    
    # إضافة معالجات الأوامر
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("daily_claim", daily_claim_command))
    dispatcher.add_handler(CommandHandler("balance", balance_command))
    dispatcher.add_handler(CommandHandler("referral", referral_command))
    dispatcher.add_handler(CommandHandler("tasks", tasks_command))
    dispatcher.add_handler(CommandHandler("history", history_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("leaderboard", leaderboard_command))
    
    # إضافة معالج الأزرار
    dispatcher.add_handler(CallbackQueryHandler(handle_callback))
    
    # بدء البوت
    updater.start_polling()
    logger.info("تم تشغيل البوت بنجاح!")
    
    # إبقاء البوت قيد التشغيل
    updater.idle()
