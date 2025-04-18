import threading
import logging
import os
import time
import psycopg2.extras
from bot import start_bot
from api import run_api
from database import create_table

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# سيتم التعامل مع JSON داخل الدوال التي تتطلب ذلك

if __name__ == "__main__":
    # تهيئة قاعدة البيانات
    logger.info("جاري تهيئة قاعدة البيانات...")
    create_table()
    
    # بدء خادم API في ثريد منفصل
    logger.info("جاري بدء خادم FastAPI...")
    api_thread = threading.Thread(target=run_api)
    api_thread.daemon = True
    api_thread.start()
    
    # بدء بوت تيليجرام في الثريد الرئيسي
    logger.info("جاري بدء بوت تيليجرام...")
    start_bot()