import os
# =====================================================
# admin_api.py - لوحة تحكم المسؤول المتكاملة
# الإصدار 2.0 - إدارة المنتجات، المستخدمين، الصور، النماذج، الإعلانات، الإعدادات
# =====================================================

import logging
import base64
from flask import Blueprint, request, jsonify
from decorators import login_required, role_required
from models import (
    ProductModel, UserModel, QuoteModel, TemplateModel,
    PromotionModel, ImageModel, SettingsModel, LogModel
)
from supabase_storage import upload_image, delete_image
from image_optimizer import optimize_image_to_target
from datetime import datetime

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

# ===================== الإحصائيات الرئيسية =====================

@admin_bp.route('/admin/stats', methods=['GET'])
@login_required
@role_required(['admin'])
def get_stats():
    """إحصائيات سريعة للوحة التحكم"""
    try:
        product_count = ProductModel.count_all()
        user_count = UserModel.count_all()
        customer_count = UserModel.count_by_role('customer')
        delivery_count = UserModel.count_by_role('delivery')
        quote_count = QuoteModel.count_all()
        pending_quotes = QuoteModel.count_by_status('pending')
        approved_quotes = QuoteModel.count_by_status('approved')
        rejected_quotes = QuoteModel.count_by_status('rejected')
        active_promotions = PromotionModel.count_active()
        template_count = TemplateModel.count_active()
        pending_images = ImageModel.count_pending()
        
        recent_quotes = QuoteModel.get_recent(5)
        
        return jsonify({
            'productCount': product_count,
            'userCount': user_count,
            'customerCount': customer_count,
            'deliveryCount': delivery_count,
            'quoteCount': quote_count,
            'pendingQuotes': pending_quotes,
            'approvedQuotes': approved_quotes,
            'rejectedQuotes': rejected_quotes,
            'activePromotions': active_promotions,
            'templateCount': template_count,
            'pendingImages': pending_images,
            'recentQuotes': recent_quotes
        }), 200
    except Exception as e:
        logger.error(f"Error in get_stats: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء جلب الإحصائيات'}), 500

# ===================== إدارة المنتجات =====================

@admin_bp.route('/admin/products', methods=['GET'])
@login_required
@role_required(['admin'])
def list_products_admin():
    """جلب جميع المنتجات مع إمكانية التصفية والبحث"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        category = request.args.get('category', None)
        search = request.args.get('search', None)
        
        products = ProductModel.get_all(limit, offset, category, search)
        total = ProductModel.count_all(category, search)
        
        # إضافة عدد الصور لكل منتج
        for product in products:
            images = ImageModel.get_images(product['sku'])
            product['image_count'] = len(images)
        
        return jsonify({
            'products': products,
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
    except Exception as e:
        logger.error(f"Error in list_products_admin: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء جلب المنتجات'}), 500

@admin_bp.route('/admin/products/<sku>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def admin_delete_product(sku):
    """حذف منتج بالكامل (بما في ذلك صوره)"""
    try:
        product = ProductModel.get_by_sku(sku)
        if not product:
            return jsonify({'error': 'المنتج غير موجود'}), 404
        
        # حذف الصور أولاً
        ImageModel.delete_all_images(sku)
        
        # حذف المنتج
        ProductModel.delete(sku)
        
        LogModel.create(request.user['user_id'], f'حذف منتج {sku}', request.remote_addr)
        return jsonify({'message': 'تم حذف المنتج بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in admin_delete_product: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء حذف المنتج'}), 500

@admin_bp.route('/admin/products/<sku>', methods=['PUT'])
@login_required
@role_required(['admin'])
def admin_update_product(sku):
    """تحديث بيانات منتج"""
    try:
        data = request.json
        product = ProductModel.get_by_sku(sku)
        if not product:
            return jsonify({'error': 'المنتج غير موجود'}), 404
        
        ProductModel.update(sku, data)
        LogModel.create(request.user['user_id'], f'تحديث منتج {sku}', request.remote_addr)
        return jsonify({'message': 'تم تحديث المنتج بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in admin_update_product: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء تحديث المنتج'}), 500

@admin_bp.route('/admin/products', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_create_product():
    """إنشاء منتج جديد"""
    try:
        data = request.json
        required_fields = ['sku', 'name', 'unit_price']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'حقل {field} مطلوب'}), 400
        
        product = ProductModel.create_or_update(data)
        LogModel.create(request.user['user_id'], f'إنشاء منتج جديد {data["sku"]}', request.remote_addr)
        return jsonify(product), 201
    except Exception as e:
        logger.error(f"Error in admin_create_product: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء إنشاء المنتج'}), 500

# ===================== إدارة الصور =====================

@admin_bp.route('/admin/products/<sku>/upload-images', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_upload_images(sku):
    """رفع صور جديدة لمنتج (مع ضغط تلقائي)"""
    try:
        product = ProductModel.get_by_sku(sku)
        if not product:
            return jsonify({'error': 'المنتج غير موجود'}), 404
        
        max_images = SettingsModel.get_int('max_images_per_product', 4)
        current_images = ImageModel.get_images(sku)
        if len(current_images) >= max_images:
            return jsonify({'error': f'لا يمكن إضافة أكثر من {max_images} صور'}), 400
        
        if 'images' not in request.files:
            return jsonify({'error': 'لم يتم إرسال أي صور'}), 400
        
        files = request.files.getlist('images')
        if len(files) > max_images - len(current_images):
            return jsonify({'error': f'يمكن رفع {max_images - len(current_images)} صور كحد أقصى'}), 400
        
        image_urls = []
        for file in files:
            file_bytes = file.read()
            optimized_bytes, content_type, final_size = optimize_image_to_target(file_bytes, file.filename)
            url = upload_image(optimized_bytes, file.filename, content_type)
            image_urls.append(url)
            logger.info(f"Uploaded image for {sku}, size: {final_size:.1f}KB")
        
        ImageModel.add_images(sku, image_urls)
        LogModel.create(request.user['user_id'], f'رفع {len(image_urls)} صورة للمنتج {sku}', request.remote_addr)
        return jsonify({'message': 'تم رفع الصور بنجاح', 'urls': image_urls}), 200
    except Exception as e:
        logger.error(f"Error in admin_upload_images: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء رفع الصور'}), 500

@admin_bp.route('/admin/products/<sku>/images/<int:image_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def admin_delete_image(sku, image_id):
    """حذف صورة محددة من منتج"""
    try:
        from supabase import create_client
        from config import Config
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        result = supabase.table('product_images').select('image_url').eq('id', image_id).eq('product_sku', sku).execute()
        if not result.data:
            return jsonify({'error': 'الصورة غير موجودة'}), 404
        
        delete_image(result.data[0]['image_url'])
        supabase.table('product_images').delete().eq('id', image_id).execute()
        
        LogModel.create(request.user['user_id'], f'حذف صورة من المنتج {sku}', request.remote_addr)
        return jsonify({'message': 'تم حذف الصورة بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in admin_delete_image: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء حذف الصورة'}), 500

# ===================== إدارة الصور المعلقة (من المندوبين) =====================

@admin_bp.route('/admin/pending-images', methods=['GET'])
@login_required
@role_required(['admin'])
def get_pending_images():
    """جلب جميع الصور المعلقة التي تنتظر الموافقة"""
    try:
        pending = ImageModel.get_pending_images()
        # إضافة اسم المنتج لكل صورة معلقة
        for p in pending:
            product = ProductModel.get_by_sku(p['product_sku'])
            p['product_name'] = product['name'] if product else p['product_sku']
        return jsonify(pending), 200
    except Exception as e:
        logger.error(f"Error in get_pending_images: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

@admin_bp.route('/admin/pending-images/<int:image_id>/approve', methods=['POST'])
@login_required
@role_required(['admin'])
def approve_pending_image(image_id):
    """الموافقة على صورة معلقة ونقلها إلى صور المنتج النشطة"""
    try:
        success = ImageModel.approve_image(image_id)
        if not success:
            return jsonify({'error': 'الصورة غير موجودة'}), 404
        LogModel.create(request.user['user_id'], f'موافقة على صورة {image_id}', request.remote_addr)
        return jsonify({'message': 'تمت الموافقة على الصورة'}), 200
    except Exception as e:
        logger.error(f"Error in approve_pending_image: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

@admin_bp.route('/admin/pending-images/<int:image_id>/reject', methods=['DELETE'])
@login_required
@role_required(['admin'])
def reject_pending_image(image_id):
    """رفض صورة معلقة وحذفها نهائياً"""
    try:
        success = ImageModel.reject_image(image_id)
        if not success:
            return jsonify({'error': 'الصورة غير موجودة'}), 404
        LogModel.create(request.user['user_id'], f'رفض صورة {image_id}', request.remote_addr)
        return jsonify({'message': 'تم رفض الصورة'}), 200
    except Exception as e:
        logger.error(f"Error in reject_pending_image: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

# ===================== إدارة عروض الأسعار =====================

@admin_bp.route('/admin/quotes', methods=['GET'])
@login_required
@role_required(['admin'])
def list_quotes_admin():
    """عرض جميع عروض الأسعار مع إمكانية التصفية حسب الحالة"""
    try:
        status = request.args.get('status', None)
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        quotes = QuoteModel.get_all(status, limit, offset)
        total = QuoteModel.count_all(status)
        return jsonify({
            'quotes': quotes,
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
    except Exception as e:
        logger.error(f"Error in list_quotes_admin: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

@admin_bp.route('/admin/quotes/<int:quote_id>', methods=['GET'])
@login_required
@role_required(['admin'])
def get_quote_details(quote_id):
    """جلب تفاصيل عرض سعر محدد"""
    try:
        from supabase import create_client
        from config import Config
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        result = supabase.table('quotes').select('*, quote_items(*)').eq('id', quote_id).execute()
        if not result.data:
            return jsonify({'error': 'عرض السعر غير موجود'}), 404
        
        quote = result.data[0]
        # إضافة معلومات المستخدم
        user = UserModel.get_by_id(quote['user_id'])
        if user:
            quote['user_email'] = user.get('email')
            quote['user_name'] = user.get('full_name')
        
        return jsonify(quote), 200
    except Exception as e:
        logger.error(f"Error in get_quote_details: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

@admin_bp.route('/admin/quotes/<int:quote_id>/status', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_quote_status(quote_id):
    """تغيير حالة عرض السعر (pending, approved, rejected, sent)"""
    try:
        data = request.json
        new_status = data.get('status')
        if new_status not in ['pending', 'approved', 'rejected', 'sent']:
            return jsonify({'error': 'حالة غير صالحة'}), 400
        
        success = QuoteModel.update_status(quote_id, new_status)
        if not success:
            return jsonify({'error': 'عرض السعر غير موجود'}), 404
        
        LogModel.create(request.user['user_id'], f'تغيير حالة عرض السعر {quote_id} إلى {new_status}', request.remote_addr)
        return jsonify({'message': 'تم تحديث الحالة بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in update_quote_status: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

# ===================== إدارة المستخدمين =====================

@admin_bp.route('/admin/users', methods=['GET'])
@login_required
@role_required(['admin'])
def list_users_admin():
    """عرض جميع المستخدمين مع التصفية حسب الدور"""
    try:
        role = request.args.get('role', None)
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        users = UserModel.get_all(role, limit, offset)
        total = UserModel.count_all(role)
        
        # إخفاء كلمة المرور
        for user in users:
            user.pop('password_hash', None)
        
        return jsonify({
            'users': users,
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
    except Exception as e:
        logger.error(f"Error in list_users_admin: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

@admin_bp.route('/admin/users/<user_id>', methods=['GET'])
@login_required
@role_required(['admin'])
def get_user_details(user_id):
    """جلب تفاصيل مستخدم محدد"""
    try:
        user = UserModel.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        user.pop('password_hash', None)
        return jsonify(user), 200
    except Exception as e:
        logger.error(f"Error in get_user_details: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

@admin_bp.route('/admin/users/<user_id>/role', methods=['PUT'])
@login_required
@role_required(['admin'])
def change_user_role(user_id):
    """تغيير دور المستخدم"""
    try:
        data = request.json
        new_role = data.get('role')
        if new_role not in ['customer', 'delivery', 'admin']:
            return jsonify({'error': 'دور غير صالح'}), 400
        
        success = UserModel.update_role(user_id, new_role)
        if not success:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        LogModel.create(request.user['user_id'], f'تغيير دور المستخدم {user_id} إلى {new_role}', request.remote_addr)
        return jsonify({'message': 'تم تحديث الدور بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in change_user_role: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

@admin_bp.route('/admin/users/<user_id>/activate', methods=['POST'])
@login_required
@role_required(['admin'])
def toggle_user_activation(user_id):
    """تفعيل أو تعطيل حساب مستخدم"""
    try:
        data = request.json
        is_active = data.get('is_active', True)
        success = UserModel.set_active(user_id, is_active)
        if not success:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        
        action = 'تفعيل' if is_active else 'تعطيل'
        LogModel.create(request.user['user_id'], f'{action} حساب المستخدم {user_id}', request.remote_addr)
        return jsonify({'message': f'تم {action} الحساب بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in toggle_user_activation: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

# ===================== إدارة الإعدادات العامة =====================

@admin_bp.route('/admin/settings', methods=['GET'])
@login_required
@role_required(['admin'])
def get_settings():
    """جلب جميع الإعدادات العامة"""
    try:
        keys = [
            'max_images_per_product',
            'carousel_interval',
            'bulk_quantity_threshold',
            'bulk_suggestion_message',
            'company_name',
            'company_logo',
            'contact_phone',
            'contact_email'
        ]
        settings = {key: SettingsModel.get(key) for key in keys}
        return jsonify(settings), 200
    except Exception as e:
        logger.error(f"Error in get_settings: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

@admin_bp.route('/admin/settings', methods=['POST'])
@login_required
@role_required(['admin'])
def update_settings():
    """تحديث إعداد واحد أو أكثر"""
    try:
        data = request.json
        for key, value in data.items():
            SettingsModel.set(key, str(value))
        LogModel.create(request.user['user_id'], 'تحديث الإعدادات العامة', request.remote_addr)
        return jsonify({'message': 'تم حفظ الإعدادات بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in update_settings: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء حفظ الإعدادات'}), 500

# ===================== سجل النشاطات =====================

@admin_bp.route('/admin/logs', methods=['GET'])
@login_required
@role_required(['admin'])
def get_logs():
    """عرض سجل النشاطات مع التصفية والترقيم"""
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        user_id = request.args.get('user_id', None)
        action_filter = request.args.get('action', None)
        
        logs = LogModel.get_all(limit, offset, user_id, action_filter)
        total = LogModel.count_all(user_id, action_filter)
        
        return jsonify({
            'logs': logs,
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
    except Exception as e:
        logger.error(f"Error in get_logs: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

# ===================== التحقق من صلاحية المسؤول =====================

@admin_bp.route('/admin/check', methods=['GET'])
@login_required
@role_required(['admin'])
def admin_check():
    """التحقق من أن المستخدم الحالي هو مسؤول"""
    return jsonify({
        'is_admin': True,
        'user_id': request.user['user_id'],
        'email': request.user['email']
    }), 200

# ===================== إحصائيات إضافية =====================

@admin_bp.route('/admin/stats/charts', methods=['GET'])
@login_required
@role_required(['admin'])
def get_chart_stats():
    """إحصائيات للرسوم البيانية (آخر 7 أيام)"""
    try:
        from datetime import timedelta
        from collections import defaultdict
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        # جلب عروض الأسعار حسب اليوم
        quotes = supabase.table('quotes').select('created_at, total_amount').gte('created_at', start_date.isoformat()).execute()
        
        daily_counts = defaultdict(int)
        daily_totals = defaultdict(float)
        
        for q in quotes.data:
            date_str = q['created_at'][:10]
            daily_counts[date_str] += 1
            daily_totals[date_str] += float(q['total_amount'] or 0)
        
        # جلب التواريخ الكاملة لآخر 7 أيام
        dates = [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(8)]
        
        return jsonify({
            'dates': dates,
            'counts': [daily_counts.get(d, 0) for d in dates],
            'totals': [daily_totals.get(d, 0) for d in dates]
        }), 200
    except Exception as e:
        logger.error(f"Error in get_chart_stats: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500

# استيراد supabase للاستخدام في الدوال
from supabase import create_client
from config import Config
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
# ============= إدارة مفاتيح الترخيص =============
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import hashlib
import secrets

# قائمة المفاتيح المخزنة (يمكن نقلها إلى قاعدة البيانات لاحقاً)
LICENSE_STORE = {}

def send_license_email(user_email, license_key, expiry_date, user_name=""):
    """إرسال مفتاح الترخيص إلى البريد الإلكتروني"""
    try:
        sender_email = "mahmoodalturki2015@gmail.com"
        sender_password = "rxwq jqyl jsqd vpgn"  # App Password
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = "🔑 مفتاح الترخيص - منظومة بن عبيد"
        
        body = f"""
        <html dir="rtl">
        <body style="font-family: Arial, sans-serif; text-align: right;">
            <div style="max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #2a5298;">🔑 مفتاح الترخيص الخاص بك</h2>
                <p>مرحباً {user_name or user_email}،</p>
                <p>تم إنشاء مفتاح الترخيص التالي لمنظومة بن عبيد:</p>
                <div style="background: #f0f0f0; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0;">
                    <code style="font-size: 18px; font-weight: bold;">{license_key}</code>
                </div>
                <p><strong>📅 تاريخ الانتهاء:</strong> {expiry_date}</p>
                <p><strong>👤 المستخدم:</strong> {user_email}</p>
                <hr>
                <p style="font-size: 12px; color: #888;">هذا المفتاح خاص بك، لا تشاركه مع أي شخص آخر.</p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def generate_license_key(user_email, days_valid=365):
    """إنشاء مفتاح ترخيص جديد"""
    expiry_date = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d")
    unique_string = f"{user_email}-{secrets.token_hex(32)}-{expiry_date}"
    license_key = hashlib.sha256(unique_string.encode()).hexdigest()
    return license_key, expiry_date

@admin_bp.route('/admin/licenses', methods=['GET'])
@login_required
@role_required(['admin'])
def get_all_licenses():
    """جلب جميع مفاتيح الترخيص"""
    return jsonify(LICENSE_STORE), 200

@admin_bp.route('/admin/licenses/generate', methods=['POST'])
@login_required
@role_required(['admin'])
def create_license():
    """إنشاء مفتاح ترخيص جديد وإرساله إلى البريد"""
    data = request.json
    user_email = data.get('email')
    days_valid = data.get('days_valid', 365)
    user_name = data.get('name', '')
    
    if not user_email:
        return jsonify({'error': 'البريد الإلكتروني مطلوب'}), 400
    
    # إنشاء المفتاح
    license_key, expiry_date = generate_license_key(user_email, days_valid)
    
    # تخزين المفتاح
    LICENSE_STORE[license_key] = {
        'email': user_email,
        'name': user_name,
        'expiry_date': expiry_date,
        'created_at': datetime.now().isoformat(),
        'is_active': True
    }
    
    # إرسال المفتاح إلى بريد المستخدم
    email_sent = send_license_email(user_email, license_key, expiry_date, user_name)
    
    # إرسال نسخة إلى بريدك الشخصي
    send_license_email("mahmoodalturki2015@gmail.com", license_key, expiry_date, f"نسخة احتياطية - {user_email}")
    
    return jsonify({
        'success': True,
        'license_key': license_key,
        'expiry_date': expiry_date,
        'email_sent': email_sent
    }), 201

@admin_bp.route('/admin/licenses/<license_key>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def revoke_license(license_key):
    """إلغاء مفتاح ترخيص"""
    if license_key in LICENSE_STORE:
        LICENSE_STORE[license_key]['is_active'] = False
        return jsonify({'message': 'تم إلغاء المفتاح بنجاح'}), 200
    return jsonify({'error': 'المفتاح غير موجود'}), 404

# ============= إرسال SMS باستخدام Twilio =============
from twilio.rest import Client

# إعدادات Twilio (سجل مجاني من twilio.com)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER', '')

def send_sms(phone_number, message):
    """إرسال رسالة نصية SMS"""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("Twilio not configured. SMS will not be sent.")
        return False
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        logger.info(f"SMS sent to {phone_number}, SID: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return False

def send_verification_code(phone_number, code):
    """إرسال رمز التحقق عبر SMS"""
    message = f"""🔐 رمز التحقق لمنظومة بن عبيد: {code}
    هذا الرمز صالح لمدة 10 دقائق. لا تشاركه مع أي شخص."""
    return send_sms(phone_number, message)

@admin_bp.route('/admin/licenses/generate-with-phone', methods=['POST'])
@login_required
@role_required(['admin'])
def generate_license_with_phone():
    """إنشاء مفتاح ترخيص مع إرسال SMS"""
    data = request.json
    user_email = data.get('email')
    user_phone = data.get('phone')  # رقم الهاتف بصيغة دولية مثلاً 0096770491653
    days_valid = data.get('days_valid', 365)
    user_name = data.get('name', '')
    
    if not user_email:
        return jsonify({'error': 'البريد الإلكتروني مطلوب'}), 400
    
    if not user_phone:
        return jsonify({'error': 'رقم الهاتف مطلوب'}), 400
    
    # إنشاء المفتاح
    license_key, expiry_date = generate_license_key(user_email, days_valid)
    
    # تخزين المفتاح
    LICENSE_STORE[license_key] = {
        'email': user_email,
        'phone': user_phone,
        'name': user_name,
        'expiry_date': expiry_date,
        'created_at': datetime.now().isoformat(),
        'is_active': True
    }
    
    # إرسال المفتاح عبر SMS
    sms_message = f"""🔑 مفتاح الترخيص لمنظومة بن عبيد:
    
المفتاح: {license_key}
تاريخ الانتهاء: {expiry_date}
    
يمكنك استخدام هذا المفتاح لتفعيل التطبيق."""
    
    sms_sent = send_sms_local(user_phone, sms_message)
    
    # إرسال نسخة إلى بريدك الشخصي
    send_license_email("mahmoodalturki2015@gmail.com", license_key, expiry_date, f"نسخة احتياطية - {user_email} - هاتف: {user_phone}")
    
    return jsonify({
        'success': True,
        'license_key': license_key,
        'expiry_date': expiry_date,
        'sms_sent': sms_sent,
        'message': 'تم إرسال المفتاح عبر SMS إلى الرقم المطلوب'
    }), 201

@admin_bp.route('/admin/licenses/resend-sms/<license_key>', methods=['POST'])
@login_required
@role_required(['admin'])
def resend_license_sms(license_key):
    """إعادة إرسال المفتاح عبر SMS"""
    if license_key not in LICENSE_STORE:
        return jsonify({'error': 'المفتاح غير موجود'}), 404
    
    license_data = LICENSE_STORE[license_key]
    user_phone = license_data.get('phone')
    
    if not user_phone:
        return jsonify({'error': 'رقم الهاتف غير متوفر لهذا المفتاح'}), 400
    
    sms_message = f"""🔑 مفتاح الترخيص لمنظومة بن عبيد:
    
المفتاح: {license_key}
تاريخ الانتهاء: {license_data['expiry_date']}
    
يمكنك استخدام هذا المفتاح لتفعيل التطبيق."""
    
    sms_sent = send_sms_local(user_phone, sms_message)
    
    return jsonify({
        'success': sms_sent,
        'message': 'تم إعادة إرسال المفتاح عبر SMS' if sms_sent else 'فشل إرسال SMS'
    }), 200

# ============= إرسال SMS محلي باستخدام Termux API =============
import subprocess

def send_sms_local(phone_number, message):
    """إرسال رسالة نصية SMS عبر termux-sms-send (محلي)"""
    try:
        # تنسيق رقم الهاتف (إزالة + إذا وجدت)
        phone = phone_number.replace('+', '').replace(' ', '')
        
        # تنفيذ أمر termux-sms-send
        result = subprocess.run(
            ['termux-sms-send', '-n', phone, message],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info(f"Local SMS sent to {phone_number}")
            return True
        else:
            logger.error(f"Local SMS failed: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Local SMS error: {e}")
        return False

def send_license_sms(phone_number, license_key, expiry_date):
    """إرسال مفتاح الترخيص عبر SMS محلي"""
    message = f"""🔑 مفتاح الترخيص لمنظومة بن عبيد:

المفتاح: {license_key}
تاريخ الانتهاء: {expiry_date}

يمكنك استخدام هذا المفتاح لتفعيل التطبيق."""
    return send_sms_local(phone_number, message)

# ===================== إدارة الملف الشخصي للمسؤول =====================
@admin_bp.route('/admin/profile', methods=['GET'])
@login_required
@role_required(['admin'])
def get_profile():
    """جلب بيانات المستخدم الحالي"""
    user_id = request.user['user_id']
    user = UserModel.get_by_id(user_id)
    if not user:
        return jsonify({'error': 'المستخدم غير موجود'}), 404
    return jsonify({
        'id': user['id'],
        'email': user['email'],
        'full_name': user.get('full_name', ''),
        'phone': user.get('phone', ''),
        'role': user['role'],
        'biometric_enabled': user.get('biometric_enabled', False)
    }), 200

@admin_bp.route('/admin/profile', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_profile():
    """تحديث بيانات المستخدم (الاسم، الهاتف، البريد، كلمة المرور)"""
    user_id = request.user['user_id']
    data = request.json
    updates = {}
    if 'full_name' in data:
        updates['full_name'] = data['full_name']
    if 'phone' in data:
        updates['phone'] = data['phone']
    if 'email' in data:
        # التحقق من عدم وجود البريد الجديد مستخدماً من قبل مستخدم آخر
        existing = UserModel.get_by_email(data['email'])
        if existing and existing['id'] != user_id:
            return jsonify({'error': 'البريد الإلكتروني مستخدم بالفعل'}), 409
        updates['email'] = data['email']
    if 'biometric_enabled' in data:
        updates['biometric_enabled'] = data['biometric_enabled']
    if data.get('new_password'):
        from werkzeug.security import generate_password_hash
        updates['password_hash'] = generate_password_hash(data['new_password'])
    if updates:
        supabase.table('users').update(updates).eq('id', user_id).execute()
    return jsonify({'message': 'تم تحديث الملف الشخصي بنجاح'}), 200
