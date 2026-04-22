# -*- coding: utf-8 -*-
import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

# ... باقي الملف (استيراد blueprints وتسجيلها)
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
