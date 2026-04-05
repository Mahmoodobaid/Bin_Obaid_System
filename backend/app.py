from flask import send_from_directory
# =====================================================
# منظومة بن عبيد - الخادم الرئيسي (Flask API)
# الإصدار 2.0 - متكامل مع جميع المراحل والتحسينات
# =====================================================

import os
import logging
from datetime import datetime
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from dotenv import load_dotenv
import time

# تحميل متغيرات البيئة
load_dotenv()

# إعداد التسجيل (logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ===================== إعدادات التطبيق =====================
class Config:
    """إعدادات التطبيق المستمدة من متغيرات البيئة"""
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
    JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', 24))
    FCM_SERVER_KEY = os.getenv('FCM_SERVER_KEY')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', 60))
    PORT = int(os.getenv('PORT', 5000))


# ===================== استيراد الـ Blueprints =====================
from auth import auth_bp
from products_api import products_bp
from images_api import images_bp
from quote_api import quote_bp
from templates_api import templates_bp
from promotions_api import promotions_bp
from admin_api import admin_bp
from auto_update import update_bp


# ===================== Middleware =====================
def setup_logging_middleware(app):
    """إعداد middleware لتسجيل الطلبات وزمن الاستجابة"""
    
    @app.before_request
    def before_request():
        g.start_time = time.time()
        if app.debug:
            logger.info(f"📥 Request: {request.method} {request.path} - IP: {request.remote_addr}")
    
    @app.after_request
    def after_request(response):
        if hasattr(g, 'start_time'):
            elapsed = time.time() - g.start_time
            response.headers['X-Response-Time'] = f"{elapsed:.3f}s"
            if app.debug:
                logger.info(f"📤 Response: {response.status_code} - Time: {elapsed:.3f}s")
        return response


def register_error_handlers(app):
    """تسجيل معالجات الأخطاء المركزية"""
    
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({'error': 'طلب غير صحيح', 'details': str(e)}), 400
    
    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({'error': 'غير مصرح به، يلزم تسجيل الدخول'}), 401
    
    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({'error': 'ليس لديك صلاحية للوصول'}), 403
    
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'الرابط غير موجود'}), 404
    
    @app.errorhandler(429)
    def too_many_requests(e):
        return jsonify({'error': 'تم تجاوز الحد المسموح من الطلبات، حاول بعد دقيقة'}), 429
    
    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"❌ Internal server error: {str(e)}")
        return jsonify({'error': 'خطأ داخلي في الخادم، حاول لاحقاً'}), 500


# Rate limiting بسيط (في الذاكرة)
rate_limit_store = {}

def rate_limit_middleware(app):
    """تقييد عدد الطلبات لكل IP في الدقيقة"""
    
    @app.before_request
    def limit_requests():
        if app.debug:
            return  # لا تفعيل rate limit في وضع التطوير
        
        client_ip = request.remote_addr
        now = time.time()
        window_start = now - 60
        
        # تنظيف الإدخالات القديمة
        for ip in list(rate_limit_store.keys()):
            rate_limit_store[ip] = [t for t in rate_limit_store[ip] if t > window_start]
        
        if client_ip not in rate_limit_store:
            rate_limit_store[client_ip] = []
        
        requests_count = len(rate_limit_store[client_ip])
        if requests_count >= Config.RATE_LIMIT_PER_MINUTE:
            return jsonify({'error': 'تم تجاوز الحد المسموح من الطلبات، حاول بعد دقيقة'}), 429
        
        rate_limit_store[client_ip].append(now)


# ===================== تهيئة تخزين Supabase =====================
def init_supabase_storage():
    """تهيئة Supabase Storage (إنشاء bucket إذا لم يكن موجوداً)"""
    try:
        from supabase_storage import init_storage_bucket
        init_storage_bucket()
        logger.info("✅ Supabase Storage initialized")
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize Supabase Storage: {e}")


# ===================== إنشاء التطبيق =====================
def create_app():
    """إنشاء وتكوين تطبيق Flask"""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['JSON_AS_ASCII'] = False  # دعم اللغة العربية
    
    # ========== خدمة ملفات admin_web الثابتة ==========
    # إنشاء مجلد static إذا لم يكن موجوداً
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    admin_web_dir = os.path.join(static_dir, 'admin_web')
    
    if not os.path.exists(admin_web_dir):
        # محاولة نسخ admin_web من frontend
        source_dir = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'admin_web')
        if os.path.exists(source_dir):
            import shutil
            os.makedirs(static_dir, exist_ok=True)
            shutil.copytree(source_dir, admin_web_dir)
            logger.info(f"✅ Copied admin_web to {admin_web_dir}")
    
    @app.route('/admin_web/<path:filename>')
    def serve_admin_web(filename):
        return send_from_directory('static/admin_web', filename)
    
    # CORS - السماح بالطلبات من التطبيقات المختلفة
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:5000", "*"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # تسجيل الـ Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(products_bp, url_prefix='/api')
    app.register_blueprint(images_bp, url_prefix='/api')
    app.register_blueprint(quote_bp, url_prefix='/api')
    app.register_blueprint(templates_bp, url_prefix='/api')
    app.register_blueprint(promotions_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    app.register_blueprint(update_bp, url_prefix='/api')
    
    # إضافة Middleware
    setup_logging_middleware(app)
    register_error_handlers(app)
    
    if not app.debug:
        rate_limit_middleware(app)
        logger.info("🚦 Rate limiting enabled")
    
    # ===================== نقاط النهاية العامة =====================
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """فحص صحة الخادم (للاستخدام مع مراقبة الخدمات)"""
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0.0'
        }), 200
    
    @app.route('/', methods=['GET'])
    def home():
        """الصفحة الرئيسية للـ API"""
        return jsonify({
            'message': 'مرحباً بك في منظومة بن عبيد لإدارة المخازن وعروض الأسعار',
            'version': '2.0.0',
            'status': 'running',
            'endpoints': {
                'auth': '/api/auth/register, /api/auth/login',
                'products': '/api/products, /api/products/upload-excel',
                'images': '/api/products/<sku>/images',
                'quotes': '/api/quote/submit, /api/quotes',
                'templates': '/api/templates',
                'promotions': '/api/promotions',
                'admin': '/api/admin/stats, /api/admin/users',
                'update': '/api/version'
            },
            'documentation': 'https://github.com/Mahmoodobaid/Bin_Obaid_System'
        }), 200
    
    @app.route('/api/info', methods=['GET'])
    def api_info():
        """معلومات عن الـ API (للاستخدام من التطبيقات)"""
        return jsonify({
            'name': 'Bin Obeid System API',
            'version': '2.0.0',
            'environment': 'development' if app.debug else 'production',
            'features': [
                'authentication',
                'product_management',
                'image_upload_with_compression',
                'quote_system',
                'templates',
                'promotions',
                'admin_dashboard',
                'auto_update'
            ]
        }), 200
    
    # تهيئة Supabase Storage
    init_supabase_storage()
    
    return app


# ===================== تشغيل التطبيق =====================
if __name__ == '__main__':
    app = create_app()
    port = Config.PORT
    
    print("=" * 50)
    print("🚀 منظومة بن عبيد - خادم Flask API")
    print(f"📍 الإصدار: 2.0.0")
    print(f"🌐 التشغيل على: http://localhost:{port}")
    print(f"🔧 وضع التطوير: {Config.DEBUG}")
    print("=" * 50)
    
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
