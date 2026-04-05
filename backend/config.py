# =====================================================
# config.py - إعدادات وتكوينات منظومة بن عبيد
# الإصدار 2.0 - مع تحميل تلقائي للمتغيرات والتحقق منها
# =====================================================

import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env (يجب أن يكون في الجذر أو مسار مطلق)
load_dotenv()

class Config:
    # ============= Supabase (قاعدة البيانات والتخزين) =============
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    # ============= الأمان والتوكن =============
    JWT_SECRET = os.getenv('JWT_SECRET', 'default-secret-change-me')
    JWT_ACCESS_EXPIRES_HOURS = int(os.getenv('JWT_ACCESS_EXPIRES_HOURS', 24))
    JWT_REFRESH_EXPIRES_DAYS = int(os.getenv('JWT_REFRESH_EXPIRES_DAYS', 30))
    
    # ============= إعدادات الأمان (قفل الحساب، معدل الطلبات) =============
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
    LOCKOUT_TIME_MINUTES = int(os.getenv('LOCKOUT_TIME_MINUTES', 30))
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))
    
    # ============= Firebase Cloud Messaging (الإشعارات) =============
    # إذا كانت القيمة "none" أو None، سيتم استخدام credentials.json
    FCM_SERVER_KEY = os.getenv('FCM_SERVER_KEY')
    if FCM_SERVER_KEY == 'none' or FCM_SERVER_KEY == '':
        FCM_SERVER_KEY = None
    
    # ============= GitHub (التحديث التلقائي) =============
    GITHUB_REPO = os.getenv('GITHUB_REPO', 'your-username/your-repo')
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
    UPDATE_CACHE_SECONDS = int(os.getenv('UPDATE_CACHE_SECONDS', 300))
    
    # ============= البريد الإلكتروني (SMTP) =============
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', MAIL_USERNAME)
    
    # ============= إعدادات Flask والخادم =============
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    
    # ============= إعدادات إضافية =============
    FORCE_UPDATE_VERSION = os.getenv('FORCE_UPDATE_VERSION', '')
    
    # ============= مسار ملف credentials.json (لخدمة Google) =============
    # يتم وضعه في نفس مجلد backend
    CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), 'credentials.json')
    
    @classmethod
    def validate(cls):
        """التحقق من وجود المتغيرات الأساسية"""
        required = ['SUPABASE_URL', 'SUPABASE_KEY']
        missing = [r for r in required if not getattr(cls, r)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
        
        # تحذيرات غير حرجة
        if not cls.JWT_SECRET or cls.JWT_SECRET == 'default-secret-change-me':
            print("⚠️ WARNING: JWT_SECRET is using default value. Change it in production!")
        
        if not cls.FCM_SERVER_KEY and not os.path.exists(cls.CREDENTIALS_PATH):
            print("⚠️ WARNING: Neither FCM_SERVER_KEY nor credentials.json found. Push notifications will not work.")
        
        if cls.GITHUB_REPO == 'your-username/your-repo':
            print("⚠️ WARNING: GITHUB_REPO not configured. Auto-update will not work.")
        
        return True

# عند استيراد هذا الملف، يتم التحقق تلقائياً (يمكن تعطيله في الإنتاج إذا أردت)
if __name__ != '__main__':
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Config Error: {e}")
        # في التطوير، نسمح بالاستمرار؛ في الإنتاج قد نرفع استثناء
        if Config.FLASK_DEBUG:
            print("⚠️ Continuing in debug mode despite missing config.")
        else:
            raise