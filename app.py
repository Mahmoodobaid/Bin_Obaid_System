# ==========================================
# منظومة محلات بن عبيد التجارية - الـ Backend الكامله (v1.0.0)
# ==========================================

import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from supabase import create_client, Client
import jwt
from datetime import datetime, timedelta
import functools

# --- إعدادات التطبيق ---
app = Flask(__name__)
# تفعيل CORS للسماح بالطلبات من أي مكان (Android, Flutter, JS)
CORS(app)

# --- إعدادات البيئة (سرية للغاية - .env) ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
JWT_SECRET = os.environ.get("JWT_SECRET")

# --- الاتصال بـ Supabase ---
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("⚠️ خطأ حرجي: بيانات Supabase غير مكتملة في .env")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- الخدمات (FCM, Excel, Google Auth, etc.) ---
# نستخدم ملف credentials.json للإشعارات الحديثة
from firebase_admin import credentials, messaging, initialize_app
try:
    # تحميل ملف Firebase من مجلد المشروع
    firebase_cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), 'credentials.json'))
    initialize_app(firebase_cred)
    app.config['FCM_ENABLED'] = True
    print("✅ تم تفعيل خدمة الإشعارات (Firebase FCM) بنجاح.")
except Exception as e:
    print(f"⚠️ خطأ في تفعيل الإشعارات: {e}")
    app.config['FCM_ENABLED'] = False

# --- المسارات والخدمات الأساسية (The API core) ---

@app.route('/', methods=['GET'])
def index():
    """مسار الواجهة الرئيسية البسيط للتأكد من تشغيل السيرفر"""
    return jsonify({
        "status": "success",
        "message": "🚀 سيرفر بن عبيد يعمل الآن بنجاح على السحابة!",
        "version": "1.0.0",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }), 200

# TODO: أضف هنا باقي المسارات (Routes) لإدارة المستخدمين، المخزون، الطلبات، إلخ.
# كما جهزناها معاً في الكود الأصلي.

# --- تشغيل السيرفر ---
if __name__ == '__main__':
    # نحصل على المنفذ من متغير البيئة ليتناسب مع Render
    port = int(os.environ.get("PORT", 5000))
    # نستخدم Gunicorn في الإنتاج، و Flask للمطور
    print(f"🚀 سيرفر بن عبيد قيد التشغيل على المنفذ {port}...")
    # تفعيل وضع المطور لإظهار الأخطاء
    app.run(host='0.0.0.0', port=port, debug=True)
