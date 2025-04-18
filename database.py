import logging
import time
import os
import psycopg2
import psycopg2.extras
import json
from datetime import datetime, timezone, timedelta
from config import (
    DATABASE_URL, DAILY_POINTS, REFERRAL_POINTS, TASK_POINTS, 
    DAILY_CLAIM_COOLDOWN, SOCIAL_MEDIA_POINTS, SOCIAL_MEDIA_LINKS
)

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """مدير السياق للحصول على اتصال قاعدة البيانات"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    except Exception as e:
        logger.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
        raise

def get_db_cursor():
    """مدير السياق للحصول على مؤشر قاعدة البيانات"""
    conn = get_db_connection()
    return conn, conn.cursor()

def create_table():
    """إنشاء جداول قاعدة البيانات إذا لم تكن موجودة"""
    conn, cur = get_db_cursor()
    try:
        # جدول المستخدمين
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                points INTEGER DEFAULT 0,
                total_points INTEGER DEFAULT 0,
                last_claim_time TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # جدول الإحالات
        cur.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id SERIAL PRIMARY KEY,
                referrer_id BIGINT REFERENCES users(user_id),
                referred_id BIGINT REFERENCES users(user_id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(referrer_id, referred_id)
            )
        ''')

        # جدول النشاطات
        cur.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                activity_type VARCHAR(50) NOT NULL,
                points INTEGER NOT NULL,
                details JSONB DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # جدول مواقع التواصل الاجتماعي
        cur.execute('''
            CREATE TABLE IF NOT EXISTS social_media_visits (
                id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                social_type VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, social_type)
            )
        ''')

        logger.info("تم إنشاء جداول قاعدة البيانات بنجاح")
    except Exception as e:
        logger.error(f"خطأ في إنشاء الجداول: {e}")
    finally:
        cur.close()
        conn.close()

def add_user(user_id, username, full_name=None):
    """إضافة مستخدم جديد إلى قاعدة البيانات أو تجاهله إذا كان موجودًا بالفعل"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    '''
                    INSERT INTO users (user_id, username, full_name, points, total_points)
                    VALUES (%s, %s, %s, 0, 0)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET username = %s, full_name = COALESCE(%s, users.full_name)
                    ''',
                    (user_id, username, full_name, username, full_name)
                )
                logger.info(f"تمت إضافة المستخدم {user_id} ({username}) أو هو موجود بالفعل")
                return True
    except Exception as e:
        logger.error(f"خطأ في إضافة المستخدم: {e}")
        return False

def get_user(user_id):
    """الحصول على بيانات المستخدم من قاعدة البيانات"""
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                'SELECT points, total_points, last_claim_time, username, full_name FROM users WHERE user_id = %s',
                (user_id,)
            )
            result = cursor.fetchone()
        return result
    except Exception as e:
        logger.error(f"خطأ في الحصول على بيانات المستخدم: {e}")
        return None

def update_points(user_id, points_to_add, activity_type, details=None):
    """تحديث نقاط المستخدم وإضافة نشاط جديد"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # تحديث النقاط الحالية والإجمالية للمستخدم
                cursor.execute(
                    'UPDATE users SET points = points + %s, total_points = total_points + %s WHERE user_id = %s RETURNING points, total_points',
                    (points_to_add, points_to_add, user_id)
                )
                new_points, total_points = cursor.fetchone()
                
                # تسجيل النشاط
                if details is None:
                    details = {}
                
                cursor.execute(
                    'INSERT INTO activities (user_id, activity_type, points, details) VALUES (%s, %s, %s, %s)',
                    (user_id, activity_type, points_to_add, json.dumps(details))
                )
                
                conn.commit()
                
                logger.info(f"تم تحديث نقاط المستخدم {user_id}: +{points_to_add} نقطة من النشاط {activity_type}")
                
                return True, {
                    'points': new_points,
                    'total_points': total_points,
                    'points_added': points_to_add
                }
    except Exception as e:
        logger.error(f"خطأ في تحديث النقاط: {e}")
        return False, str(e)

def daily_claim(user_id):
    """معالجة المطالبة اليومية بالنقاط"""
    # الحصول على بيانات المستخدم
    user_data = get_user(user_id)
    if not user_data:
        return None, None
    
    # التحقق مما إذا كان يمكن للمستخدم المطالبة بالمكافأة اليومية
    can_claim, claim_info = can_claim_daily(user_id)
    
    if not can_claim:
        return False, claim_info
    
    # إضافة النقاط للمستخدم وتحديث وقت آخر مطالبة
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # تحديث النقاط ووقت آخر مطالبة
                current_time = datetime.now(timezone.utc)
                cursor.execute(
                    'UPDATE users SET points = points + %s, total_points = total_points + %s, last_claim_time = %s WHERE user_id = %s RETURNING points, total_points',
                    (DAILY_POINTS, DAILY_POINTS, current_time, user_id)
                )
                new_points, total_points = cursor.fetchone()
                
                # تسجيل نشاط المطالبة اليومية
                cursor.execute(
                    'INSERT INTO activities (user_id, activity_type, points, details) VALUES (%s, %s, %s, %s)',
                    (user_id, 'daily_claim', DAILY_POINTS, json.dumps({'claim_time': current_time.isoformat()}))
                )
                
                conn.commit()
                
                logger.info(f"تم منح المستخدم {user_id} المكافأة اليومية: {DAILY_POINTS} نقطة")
                
                return True, {
                    'points': new_points,
                    'total_points': total_points,
                    'points_added': DAILY_POINTS
                }
    except Exception as e:
        logger.error(f"خطأ في معالجة المطالبة اليومية: {e}")
        return False, str(e)

def can_claim_daily(user_id):
    """التحقق مما إذا كان المستخدم يمكنه المطالبة بالنقاط اليومية"""
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                'SELECT last_claim_time FROM users WHERE user_id = %s',
                (user_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                return False, "المستخدم غير موجود"
                
            last_claim = result[0]
            
            if not last_claim:
                return True, "المطالبة الأولى"
                
            current_time = datetime.now(timezone.utc)
            
            # تحويل last_claim إلى UTC إذا لم يكن بالفعل
            if last_claim.tzinfo is None:
                last_claim = last_claim.replace(tzinfo=timezone.utc)
                
            time_since_last_claim = (current_time - last_claim).total_seconds()
            
            if time_since_last_claim >= DAILY_CLAIM_COOLDOWN:
                return True, "مؤهل للمطالبة"
            else:
                remaining_time = DAILY_CLAIM_COOLDOWN - time_since_last_claim
                return False, int(remaining_time)
    except Exception as e:
        logger.error(f"خطأ في التحقق من أهلية المطالبة اليومية: {e}")
        return False, str(e)

def get_referrals(user_id):
    """الحصول على عدد الإحالات للمستخدم"""
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                'SELECT COUNT(*) FROM referrals WHERE referrer_id = %s',
                (user_id,)
            )
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"خطأ في الحصول على عدد الإحالات: {e}")
        return 0

def add_referral(referrer_id, referred_id):
    """إضافة إحالة جديدة وتحديث النقاط"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # التحقق من وجود المستخدمين
                cursor.execute(
                    'SELECT 1 FROM users WHERE user_id IN (%s, %s)',
                    (referrer_id, referred_id)
                )
                if len(cursor.fetchall()) < 2:
                    return False, "المستخدمون غير موجودين"
                
                # محاولة إضافة الإحالة
                try:
                    cursor.execute(
                        'INSERT INTO referrals (referrer_id, referred_id) VALUES (%s, %s)',
                        (referrer_id, referred_id)
                    )
                except psycopg2.errors.UniqueViolation:
                    conn.rollback()
                    return False, "تمت الإحالة بالفعل"
                
                # تحديث نقاط المستخدم المحيل
                cursor.execute(
                    'UPDATE users SET points = points + %s, total_points = total_points + %s WHERE user_id = %s RETURNING points, total_points',
                    (REFERRAL_POINTS, REFERRAL_POINTS, referrer_id)
                )
                new_points, total_points = cursor.fetchone()
                
                # تسجيل نشاط الإحالة
                details = {'referred_id': referred_id}
                cursor.execute(
                    'INSERT INTO activities (user_id, activity_type, points, details) VALUES (%s, %s, %s, %s)',
                    (referrer_id, 'referral', REFERRAL_POINTS, json.dumps(details))
                )
                
                conn.commit()
                
                logger.info(f"تمت إضافة إحالة جديدة: {referrer_id} أحال {referred_id} (+{REFERRAL_POINTS} نقطة)")
                
                return True, {
                    'points': new_points,
                    'total_points': total_points,
                    'points_added': REFERRAL_POINTS
                }
    except Exception as e:
        logger.error(f"خطأ في إضافة الإحالة: {e}")
        return False, str(e)

def get_user_activities(user_id, limit=10):
    """الحصول على آخر أنشطة المستخدم"""
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                '''
                SELECT activity_type, points, created_at, details
                FROM activities
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                ''',
                (user_id, limit)
            )
            activities = cursor.fetchall()
            return activities
    except Exception as e:
        logger.error(f"خطأ في الحصول على أنشطة المستخدم: {e}")
        return []

def social_media_visit(user_id, social_type):
    """تسجيل زيارة لموقع تواصل اجتماعي وإضافة نقاط (مرة واحدة فقط)"""
    if social_type not in SOCIAL_MEDIA_LINKS:
        return False, "نوع موقع التواصل الاجتماعي غير معروف"
        
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # التحقق مما إذا كان المستخدم قد قام بالزيارة من قبل
                cursor.execute(
                    'SELECT 1 FROM social_media_visits WHERE user_id = %s AND social_type = %s',
                    (user_id, social_type)
                )
                if cursor.fetchone():
                    return False, "تمت الزيارة بالفعل"
                
                # تسجيل الزيارة
                cursor.execute(
                    'INSERT INTO social_media_visits (user_id, social_type) VALUES (%s, %s)',
                    (user_id, social_type)
                )
                
                # إضافة النقاط
                points_to_add = SOCIAL_MEDIA_POINTS
                cursor.execute(
                    'UPDATE users SET points = points + %s, total_points = total_points + %s WHERE user_id = %s RETURNING points, total_points',
                    (points_to_add, points_to_add, user_id)
                )
                new_points, total_points = cursor.fetchone()
                
                # تسجيل النشاط
                details = {'social_type': social_type, 'url': SOCIAL_MEDIA_LINKS[social_type]}
                cursor.execute(
                    'INSERT INTO activities (user_id, activity_type, points, details) VALUES (%s, %s, %s, %s)',
                    (user_id, f'social_{social_type}', points_to_add, json.dumps(details))
                )
                
                conn.commit()
                
                logger.info(f"المستخدم {user_id} قام بزيارة {social_type} (+{points_to_add} نقطة)")
                
                return True, {
                    'points': new_points,
                    'total_points': total_points,
                    'points_added': points_to_add
                }
    except Exception as e:
        logger.error(f"خطأ في تسجيل زيارة موقع تواصل اجتماعي: {e}")
        return False, str(e)

def get_social_media_visits(user_id):
    """الحصول على قائمة بالمواقع التي زارها المستخدم بالفعل"""
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                'SELECT social_type FROM social_media_visits WHERE user_id = %s',
                (user_id,)
            )
            results = cursor.fetchall()
            return [result[0] for result in results]
    except Exception as e:
        logger.error(f"خطأ في الحصول على زيارات مواقع التواصل الاجتماعي: {e}")
        return []

def get_leaderboard(limit=10):
    """الحصول على لوحة المتصدرين"""
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                '''
                SELECT user_id, username, points, total_points
                FROM users
                ORDER BY points DESC
                LIMIT %s
                ''',
                (limit,)
            )
            leaderboard = cursor.fetchall()
            return leaderboard
    except Exception as e:
        logger.error(f"خطأ في الحصول على لوحة المتصدرين: {e}")
        return []

def request_withdrawal(user_id, amount, details=None):
    """تسجيل طلب سحب النقاط"""
    if details is None:
        details = {}
        
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # التحقق من وجود رصيد كافٍ
                cursor.execute(
                    'SELECT points FROM users WHERE user_id = %s',
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if not result:
                    return False, "المستخدم غير موجود"
                    
                current_points = result[0]
                
                if current_points < amount:
                    return False, "رصيد غير كافٍ"
                
                # خصم النقاط من المستخدم
                cursor.execute(
                    'UPDATE users SET points = points - %s WHERE user_id = %s',
                    (amount, user_id)
                )
                
                # تسجيل النشاط
                cursor.execute(
                    'INSERT INTO activities (user_id, activity_type, points, details) VALUES (%s, %s, %s, %s)',
                    (user_id, 'withdrawal', -amount, json.dumps(details))
                )
                
                # تسجيل طلب السحب
                cursor.execute(
                    '''
                    INSERT INTO withdrawals (user_id, amount, details)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    ''',
                    (user_id, amount, json.dumps(details))
                )
                withdrawal_id = cursor.fetchone()[0]
                
                conn.commit()
                
                logger.info(f"تم تسجيل طلب سحب للمستخدم {user_id}: {amount} نقطة (معرف الطلب: {withdrawal_id})")
                
                return True, {
                    'withdrawal_id': withdrawal_id,
                    'amount': amount,
                    'remaining_points': current_points - amount
                }
    except Exception as e:
        logger.error(f"خطأ في تسجيل طلب السحب: {e}")
        return False, str(e)