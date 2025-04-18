import logging
import time
import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from database import (
    get_user, daily_claim, get_referrals, 
    get_user_activities, get_leaderboard, request_withdrawal,
    social_media_visit, get_social_media_visits
)
from config import SOCIAL_MEDIA_LINKS

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إنشاء تطبيق FastAPI
api = FastAPI(
    title="نظام نقاط Forex Fabric",
    description="واجهة برمجة التطبيقات لنظام النقاط والإحالات",
    version="1.0.0"
)

# إضافة ميدلوير CORS للسماح بالطلبات من مصادر مختلفة
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # يمكن تقييده لاحقًا للإنتاج
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# تحميل الملفات الثابتة لتطبيق الويب
api.mount("/static", StaticFiles(directory="static"), name="static")

@api.get("/")
async def root():
    """تقديم صفحة تطبيق الويب الرئيسية"""
    return FileResponse("static/index.html")

@api.get("/api/user/{user_id}")
async def get_user_data(user_id: int):
    """الحصول على بيانات المستخدم بما في ذلك النقاط ووقت آخر مطالبة"""
    try:
        # الحصول على بيانات المستخدم الأساسية
        user_data = get_user(user_id)
        
        if not user_data:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")
            
        points, total_points, last_claim, username, full_name = user_data
        
        # الحصول على عدد الإحالات
        referrals_count = get_referrals(user_id)
        
        # التحقق من إمكانية المطالبة اليومية
        can_claim, claim_info = daily_claim(user_id)
        can_claim_status = can_claim
        
        # تحديد وقت المطالبة القادمة
        next_claim_time = 0
        if not can_claim and isinstance(claim_info, int):
            next_claim_time = claim_info
            
        # الحصول على المواقع الاجتماعية التي تمت زيارتها
        visited_socials = get_social_media_visits(user_id)
            
        return {
            "user_id": user_id,
            "username": username,
            "full_name": full_name if full_name else username,
            "points": points,
            "total_points": total_points,
            "last_claim_time": last_claim.isoformat() if last_claim else None,
            "referrals_count": referrals_count,
            "can_claim": can_claim_status,
            "next_claim_time": next_claim_time,
            "visited_socials": visited_socials,
            "social_links": SOCIAL_MEDIA_LINKS
        }
    except Exception as e:
        logger.error(f"خطأ في الحصول على بيانات المستخدم: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api.post("/api/daily_claim/{user_id}")
async def daily_claim_endpoint(user_id: int):
    """معالجة المطالبة اليومية من تطبيق الويب"""
    try:
        result, data = daily_claim(user_id)
        
        if result is None:
            raise HTTPException(status_code=404, detail="المستخدم غير موجود")
            
        if not result:
            if isinstance(data, int):
                return {
                    "success": False,
                    "message": "لا يمكنك المطالبة الآن",
                    "seconds_remaining": data
                }
            else:
                return {
                    "success": False,
                    "message": str(data)
                }
                
        # تم منح النقاط بنجاح
        points = data['points']
        total_points = data['total_points']
        points_added = data['points_added']
        
        return {
            "success": True,
            "message": f"تمت إضافة {points_added} نقطة بنجاح!",
            "points": points,
            "total_points": total_points,
            "points_added": points_added
        }
    except Exception as e:
        logger.error(f"خطأ في معالجة المطالبة اليومية: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api.post("/api/social_visit/{user_id}")
async def social_media_visit_endpoint(user_id: int, request: Request):
    """تسجيل زيارة لموقع تواصل اجتماعي"""
    try:
        data = await request.json()
        social_type = data.get("social_type")
        
        if not social_type or social_type not in SOCIAL_MEDIA_LINKS:
            raise HTTPException(status_code=400, detail="نوع موقع التواصل الاجتماعي غير صالح")
            
        result, data = social_media_visit(user_id, social_type)
        
        if not result:
            return {
                "success": False,
                "message": str(data)
            }
                
        # تم منح النقاط بنجاح
        points = data['points']
        total_points = data['total_points']
        points_added = data['points_added']
        
        return {
            "success": True,
            "message": f"تمت إضافة {points_added} نقطة بنجاح لزيارة {social_type}!",
            "points": points,
            "total_points": total_points,
            "points_added": points_added
        }
    except Exception as e:
        logger.error(f"خطأ في تسجيل زيارة موقع تواصل اجتماعي: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api.get("/api/activities/{user_id}")
async def get_activities_endpoint(user_id: int, limit: int = 10):
    """الحصول على قائمة بالأنشطة السابقة للمستخدم"""
    try:
        activities = get_user_activities(user_id, limit)
        
        # تنسيق البيانات للعرض
        formatted_activities = []
        for activity in activities:
            activity_type, points, created_at, details = activity
            
            # محاولة تحليل التفاصيل كـ JSON
            try:
                if isinstance(details, str):
                    details_dict = json.loads(details)
                else:
                    details_dict = details
            except:
                details_dict = {}
                
            formatted_activities.append({
                "activity_type": activity_type,
                "points": points,
                "created_at": created_at.isoformat(),
                "details": details_dict
            })
            
        return {"activities": formatted_activities}
    except Exception as e:
        logger.error(f"خطأ في الحصول على أنشطة المستخدم: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api.get("/api/leaderboard")
async def get_leaderboard_endpoint(limit: int = 10):
    """الحصول على لوحة المتصدرين"""
    try:
        leaderboard_data = get_leaderboard(limit)
        
        # تنسيق البيانات للعرض
        formatted_leaderboard = []
        for entry in leaderboard_data:
            user_id, username, points, total_points = entry
            formatted_leaderboard.append({
                "user_id": user_id,
                "username": username,
                "points": points,
                "total_points": total_points
            })
            
        return {"leaderboard": formatted_leaderboard}
    except Exception as e:
        logger.error(f"خطأ في الحصول على لوحة المتصدرين: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api.post("/api/withdraw/{user_id}")
async def withdraw_points(user_id: int, request: Request):
    """معالجة طلب سحب النقاط"""
    try:
        data = await request.json()
        amount = data.get("amount")
        details = data.get("details", {})
        
        if not amount or not isinstance(amount, int) or amount <= 0:
            raise HTTPException(status_code=400, detail="مبلغ غير صالح")
            
        result, data = request_withdrawal(user_id, amount, details)
        
        if not result:
            return {
                "success": False,
                "message": str(data)
            }
                
        return {
            "success": True,
            "message": f"تم تقديم طلب السحب بنجاح! المعرف: {data['withdrawal_id']}",
            "withdrawal_id": data["withdrawal_id"],
            "amount": data["amount"],
            "remaining_points": data["remaining_points"]
        }
    except Exception as e:
        logger.error(f"خطأ في معالجة طلب السحب: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def run_api():
    """تشغيل خادم FastAPI"""
    import uvicorn
    host = "0.0.0.0"
    port = 5000
    logger.info(f"بدء تشغيل واجهة API على {host}:{port}")
    uvicorn.run(api, host=host, port=port)