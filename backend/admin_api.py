# =====================================================
# admin_api.py - لوحة تحكم المسؤول المتكاملة
# الإصدار 2.1 - مع دعم إشعارات Firebase Cloud Messaging
# =====================================================

import logging
from flask import Blueprint, request, jsonify
from decorators import login_required, role_required
from models import ProductModel, UserModel, QuoteModel, TemplateModel, PromotionModel, ImageModel, SettingsModel, LogModel
from supabase_storage import upload_image, delete_image
from image_optimizer import optimize_image_to_target
from datetime import datetime
import uuid

# استيراد مكتبات Firebase Admin (ستتم تهيئتها في app.py)
try:
    from firebase_admin import messaging
except ImportError:
    messaging = None

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

# ===================== الإحصائيات الرئيسية =====================

@admin_bp.route('/admin/stats', methods=['GET'])
@login_required
@role_required(['admin'])
def get_stats():
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
            'productCount': product_count, 'userCount': user_count,
            'customerCount': customer_count, 'deliveryCount': delivery_count,
            'quoteCount': quote_count, 'pendingQuotes': pending_quotes,
            'approvedQuotes': approved_quotes, 'rejectedQuotes': rejected_quotes,
            'activePromotions': active_promotions, 'templateCount': template_count,
            'pendingImages': pending_images, 'recentQuotes': recent_quotes
        }), 200
    except Exception as e:
        logger.error(f"Error in get_stats: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/stats/charts', methods=['GET'])
@login_required
@role_required(['admin'])
def get_charts_data():
    """بيانات الرسم البياني لآخر 7 أيام"""
    try:
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        # يمكنك تخصيص هذا الاستعلام حسب جدول عروض الأسعار لديك
        result = supabase_client.table('quotes').select('created_at').gte('created_at', (datetime.now().replace(hour=0, minute=0, second=0) - __import__('datetime').timedelta(days=7)).isoformat()).execute()
        # معالجة بسيطة لتجميع الأيام
        dates = []
        counts = []
        # ... يمكنك تحسين هذا الجزء حسب احتياجك
        return jsonify({'dates': dates, 'counts': counts}), 200
    except Exception as e:
        logger.error(f"Error in get_charts_data: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== إدارة المنتجات =====================

@admin_bp.route('/admin/products', methods=['GET'])
@login_required
@role_required(['admin'])
def list_products_admin():
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        category = request.args.get('category', None)
        search = request.args.get('search', None)
        products = ProductModel.get_all(limit, offset, category, search)
        total = ProductModel.count_all(category, search)
        for product in products:
            images = ImageModel.get_images(product['sku'])
            product['image_count'] = len(images)
        return jsonify({'products': products, 'total': total, 'limit': limit, 'offset': offset}), 200
    except Exception as e:
        logger.error(f"Error in list_products_admin: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/products/<sku>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def admin_delete_product(sku):
    try:
        if not ProductModel.get_by_sku(sku):
            return jsonify({'error': 'المنتج غير موجود'}), 404
        ImageModel.delete_all_images(sku)
        ProductModel.delete(sku)
        LogModel.create(request.user['user_id'], f'حذف منتج {sku}', request.remote_addr)
        return jsonify({'message': 'تم حذف المنتج بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in admin_delete_product: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/products/<sku>', methods=['PUT'])
@login_required
@role_required(['admin'])
def admin_update_product(sku):
    try:
        if not ProductModel.get_by_sku(sku):
            return jsonify({'error': 'المنتج غير موجود'}), 404
        data = request.json
        ProductModel.update(sku, data)
        LogModel.create(request.user['user_id'], f'تحديث منتج {sku}', request.remote_addr)
        return jsonify({'message': 'تم تحديث المنتج بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in admin_update_product: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/products', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_create_product():
    try:
        data = request.json
        required = ['sku', 'name', 'unit_price']
        for f in required:
            if f not in data:
                return jsonify({'error': f'حقل {f} مطلوب'}), 400
        product = ProductModel.create_or_update(data)
        LogModel.create(request.user['user_id'], f'إنشاء منتج {data["sku"]}', request.remote_addr)
        return jsonify(product), 201
    except Exception as e:
        logger.error(f"Error in admin_create_product: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== إدارة الصور =====================

@admin_bp.route('/admin/products/<sku>/upload-images', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_upload_images(sku):
    try:
        product = ProductModel.get_by_sku(sku)
        if not product:
            return jsonify({'error': 'المنتج غير موجود'}), 404
        max_images = SettingsModel.get_int('max_images_per_product', 4)
        current = ImageModel.get_images(sku)
        if len(current) >= max_images:
            return jsonify({'error': f'لا يمكن إضافة أكثر من {max_images} صور'}), 400
        if 'images' not in request.files:
            return jsonify({'error': 'لم يتم إرسال أي صور'}), 400
        files = request.files.getlist('images')
        if len(files) > max_images - len(current):
            return jsonify({'error': f'يمكن رفع {max_images - len(current)} صور كحد أقصى'}), 400
        urls = []
        for f in files:
            fb = f.read()
            opt, ct, sz = optimize_image_to_target(fb, f.filename)
            url = upload_image(opt, f.filename, ct)
            urls.append(url)
        ImageModel.add_images(sku, urls)
        LogModel.create(request.user['user_id'], f'رفع {len(urls)} صورة للمنتج {sku}', request.remote_addr)
        return jsonify({'message': 'تم رفع الصور بنجاح', 'urls': urls}), 200
    except Exception as e:
        logger.error(f"Error in admin_upload_images: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/products/<sku>/images/<int:image_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def admin_delete_image(sku, image_id):
    try:
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        res = supabase_client.table('product_images').select('image_url').eq('id', image_id).eq('product_sku', sku).execute()
        if not res.data:
            return jsonify({'error': 'الصورة غير موجودة'}), 404
        delete_image(res.data[0]['image_url'])
        supabase_client.table('product_images').delete().eq('id', image_id).execute()
        LogModel.create(request.user['user_id'], f'حذف صورة من المنتج {sku}', request.remote_addr)
        return jsonify({'message': 'تم حذف الصورة بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in admin_delete_image: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== إدارة الصور المعلقة =====================

@admin_bp.route('/admin/pending-images', methods=['GET'])
@login_required
@role_required(['admin'])
def get_pending_images():
    try:
        pending = ImageModel.get_pending_images()
        for p in pending:
            prod = ProductModel.get_by_sku(p['product_sku'])
            p['product_name'] = prod['name'] if prod else p['product_sku']
        return jsonify(pending), 200
    except Exception as e:
        logger.error(f"Error in get_pending_images: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/pending-images/<int:image_id>/approve', methods=['POST'])
@login_required
@role_required(['admin'])
def approve_pending_image(image_id):
    try:
        success = ImageModel.approve_image(image_id)
        if not success:
            return jsonify({'error': 'الصورة غير موجودة'}), 404
        LogModel.create(request.user['user_id'], f'موافقة على صورة {image_id}', request.remote_addr)
        return jsonify({'message': 'تمت الموافقة على الصورة'}), 200
    except Exception as e:
        logger.error(f"Error in approve_pending_image: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/pending-images/<int:image_id>/reject', methods=['DELETE'])
@login_required
@role_required(['admin'])
def reject_pending_image(image_id):
    try:
        success = ImageModel.reject_image(image_id)
        if not success:
            return jsonify({'error': 'الصورة غير موجودة'}), 404
        LogModel.create(request.user['user_id'], f'رفض صورة {image_id}', request.remote_addr)
        return jsonify({'message': 'تم رفض الصورة'}), 200
    except Exception as e:
        logger.error(f"Error in reject_pending_image: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== إدارة عروض الأسعار =====================

@admin_bp.route('/admin/quotes', methods=['GET'])
@login_required
@role_required(['admin'])
def list_quotes_admin():
    try:
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        quotes = QuoteModel.get_all(status, limit, offset)
        total = QuoteModel.count_all(status)
        return jsonify({'quotes': quotes, 'total': total, 'limit': limit, 'offset': offset}), 200
    except Exception as e:
        logger.error(f"Error in list_quotes_admin: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/quotes/<int:quote_id>', methods=['GET'])
@login_required
@role_required(['admin'])
def get_quote_details(quote_id):
    try:
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        res = supabase_client.table('quotes').select('*, quote_items(*)').eq('id', quote_id).execute()
        if not res.data:
            return jsonify({'error': 'عرض السعر غير موجود'}), 404
        quote = res.data[0]
        user = UserModel.get_by_id(quote['user_id'])
        if user:
            quote['user_email'] = user.get('email')
            quote['user_name'] = user.get('full_name')
        return jsonify(quote), 200
    except Exception as e:
        logger.error(f"Error in get_quote_details: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/quotes/<int:quote_id>/status', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_quote_status(quote_id):
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
        return jsonify({'error': str(e)}), 500


# ===================== إدارة المستخدمين =====================

@admin_bp.route('/admin/users', methods=['GET'])
@login_required
@role_required(['admin'])
def list_users_admin():
    try:
        role = request.args.get('role')
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        users = UserModel.get_all(role, limit, offset)
        total = UserModel.count_all(role)
        for u in users:
            u.pop('password_hash', None)
        return jsonify({'users': users, 'total': total, 'limit': limit, 'offset': offset}), 200
    except Exception as e:
        logger.error(f"Error in list_users_admin: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/users/<user_id>', methods=['GET'])
@login_required
@role_required(['admin'])
def get_user_details(user_id):
    try:
        user = UserModel.get_by_id(user_id)
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        user.pop('password_hash', None)
        return jsonify(user), 200
    except Exception as e:
        logger.error(f"Error in get_user_details: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/users/<user_id>/role', methods=['PUT'])
@login_required
@role_required(['admin'])
def change_user_role(user_id):
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
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/users/<user_id>/activate', methods=['POST'])
@login_required
@role_required(['admin'])
def toggle_user_activation(user_id):
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
        return jsonify({'error': str(e)}), 500


# ===================== إدارة النماذج =====================

@admin_bp.route('/admin/templates', methods=['GET'])
@login_required
@role_required(['admin'])
def list_templates():
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        templates = TemplateModel.get_all(include_inactive=include_inactive)
        return jsonify(templates), 200
    except Exception as e:
        logger.error(f"Error in list_templates: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/templates', methods=['POST'])
@login_required
@role_required(['admin'])
def create_template():
    try:
        data = request.json
        name = data.get('name')
        if not name:
            return jsonify({'error': 'اسم النموذج مطلوب'}), 400
        items = data.get('items', [])
        if not items:
            return jsonify({'error': 'يجب إضافة صنف واحد على الأقل'}), 400
        template = TemplateModel.create_template(name, data.get('description', ''), items, request.user['user_id'])
        LogModel.create(request.user['user_id'], f'إنشاء نموذج جديد: {name}', request.remote_addr)
        return jsonify(template), 201
    except Exception as e:
        logger.error(f"Error in create_template: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/templates/<int:template_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_template(template_id):
    try:
        data = request.json
        success = TemplateModel.update_template(template_id, data)
        if not success:
            return jsonify({'error': 'النموذج غير موجود'}), 404
        LogModel.create(request.user['user_id'], f'تحديث نموذج {template_id}', request.remote_addr)
        return jsonify({'message': 'تم تحديث النموذج بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in update_template: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/templates/<int:template_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_template(template_id):
    try:
        success = TemplateModel.delete_template(template_id)
        if not success:
            return jsonify({'error': 'النموذج غير موجود'}), 404
        LogModel.create(request.user['user_id'], f'حذف نموذج {template_id}', request.remote_addr)
        return jsonify({'message': 'تم حذف النموذج بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in delete_template: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== إدارة الإعلانات =====================

@admin_bp.route('/admin/promotions', methods=['GET'])
@login_required
@role_required(['admin'])
def list_promotions():
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        promotions = PromotionModel.get_all(include_inactive=include_inactive)
        return jsonify(promotions), 200
    except Exception as e:
        logger.error(f"Error in list_promotions: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/promotions', methods=['POST'])
@login_required
@role_required(['admin'])
def create_promotion():
    try:
        data = request.json
        title = data.get('title')
        if not title:
            return jsonify({'error': 'عنوان الإعلان مطلوب'}), 400
        promo = PromotionModel.create(
            title=title, body=data.get('body', ''), image_url=data.get('image_url'),
            product_sku=data.get('product_sku'), start_date=data.get('start_date'),
            end_date=data.get('end_date'), created_by=request.user['user_id']
        )
        LogModel.create(request.user['user_id'], f'إنشاء إعلان: {title}', request.remote_addr)
        return jsonify(promo), 201
    except Exception as e:
        logger.error(f"Error in create_promotion: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/promotions/<int:promo_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_promotion(promo_id):
    try:
        data = request.json
        success = PromotionModel.update(promo_id, data)
        if not success:
            return jsonify({'error': 'الإعلان غير موجود'}), 404
        LogModel.create(request.user['user_id'], f'تحديث إعلان {promo_id}', request.remote_addr)
        return jsonify({'message': 'تم تحديث الإعلان بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in update_promotion: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/promotions/<int:promo_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_promotion(promo_id):
    try:
        success = PromotionModel.delete(promo_id)
        if not success:
            return jsonify({'error': 'الإعلان غير موجود'}), 404
        LogModel.create(request.user['user_id'], f'حذف إعلان {promo_id}', request.remote_addr)
        return jsonify({'message': 'تم حذف الإعلان بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in delete_promotion: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== إدارة الإعدادات العامة =====================

@admin_bp.route('/admin/settings', methods=['GET'])
@login_required
@role_required(['admin'])
def get_settings():
    try:
        keys = ['max_images_per_product', 'carousel_interval', 'bulk_quantity_threshold',
                'bulk_suggestion_message', 'company_name', 'company_logo', 'contact_phone', 'contact_email']
        settings = {k: SettingsModel.get(k) for k in keys}
        return jsonify(settings), 200
    except Exception as e:
        logger.error(f"Error in get_settings: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/settings', methods=['POST'])
@login_required
@role_required(['admin'])
def update_settings():
    try:
        data = request.json
        for k, v in data.items():
            SettingsModel.set(k, str(v))
        LogModel.create(request.user['user_id'], 'تحديث الإعدادات العامة', request.remote_addr)
        return jsonify({'message': 'تم حفظ الإعدادات بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in update_settings: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== سجل النشاطات =====================

@admin_bp.route('/admin/logs', methods=['GET'])
@login_required
@role_required(['admin'])
def get_logs():
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        user_id = request.args.get('user_id')
        action_filter = request.args.get('action')
        logs = LogModel.get_all(limit, offset, user_id, action_filter)
        total = LogModel.count_all(user_id, action_filter)
        return jsonify({'logs': logs, 'total': total, 'limit': limit, 'offset': offset}), 200
    except Exception as e:
        logger.error(f"Error in get_logs: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== التحقق من صلاحية المسؤول =====================

@admin_bp.route('/admin/check', methods=['GET'])
@login_required
@role_required(['admin'])
def admin_check():
    return jsonify({'is_admin': True, 'user_id': request.user['user_id'], 'email': request.user['email']}), 200


# ===================== طلبات التسجيل (pending_users) =====================

@admin_bp.route('/admin/pending-users', methods=['GET'])
@login_required
@role_required(['admin'])
def get_pending_users():
    try:
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        result = supabase_client.table('pending_users').select('*').eq('status', 'pending').execute()
        return jsonify(result.data), 200
    except Exception as e:
        logger.error(f"Error in get_pending_users: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/pending-users/<user_id>/approve', methods=['POST'])
@login_required
@role_required(['admin'])
def approve_user(user_id):
    try:
        import secrets, string
        from werkzeug.security import generate_password_hash
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        pending = supabase_client.table('pending_users').select('*').eq('id', user_id).execute()
        if not pending.data:
            return jsonify({'error': 'الطلب غير موجود'}), 404
        ud = pending.data[0]
        alphabet = string.ascii_letters + string.digits
        temp_pass = ''.join(secrets.choice(alphabet) for _ in range(8))
        new_user = {
            'id': str(uuid.uuid4()),
            'email': f"{ud['phone']}@temp.com",
            'password_hash': generate_password_hash(temp_pass),
            'full_name': ud['full_name'],
            'role': 'customer',
            'phone': ud['phone'],
            'is_active': True
        }
        supabase_client.table('users').insert(new_user).execute()
        supabase_client.table('pending_users').update({'status': 'approved'}).eq('id', user_id).execute()
        # إرسال رسالة نصية (اختياري)
        try:
            from fcm_sender import send_sms
            send_sms(ud['phone'], f"تهانينا {ud['full_name']}! تم قبول طلب التسجيل. كلمة المرور المؤقتة: {temp_pass}")
        except:
            pass
        LogModel.create(request.user['user_id'], f'قبول طلب تسجيل {ud["phone"]}', request.remote_addr)
        return jsonify({'message': 'تم قبول الطلب وإنشاء الحساب'}), 200
    except Exception as e:
        logger.error(f"Error in approve_user: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/pending-users/<user_id>/reject', methods=['DELETE'])
@login_required
@role_required(['admin'])
def reject_user(user_id):
    try:
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        supabase_client.table('pending_users').update({'status': 'rejected'}).eq('id', user_id).execute()
        LogModel.create(request.user['user_id'], f'رفض طلب تسجيل {user_id}', request.remote_addr)
        return jsonify({'message': 'تم رفض الطلب'}), 200
    except Exception as e:
        logger.error(f"Error in reject_user: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/pending-users/<user_id>/send-instructions', methods=['POST'])
@login_required
@role_required(['admin'])
def send_instructions(user_id):
    try:
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        pending = supabase_client.table('pending_users').select('*').eq('id', user_id).execute()
        if not pending.data:
            return jsonify({'error': 'الطلب غير موجود'}), 404
        ud = pending.data[0]
        instructions = f"مرحباً {ud['full_name']}، لاستكمال تسجيلك في بن عبيد التجارية، يرجى التأكد من صحة بياناتك. سيتم إعلامك عند قبول الطلب. شكراً لتواصلك."
        try:
            from fcm_sender import send_sms
            send_sms(ud['phone'], instructions)
        except:
            pass
        LogModel.create(request.user['user_id'], f'إرسال تعليمات للرقم {ud["phone"]}', request.remote_addr)
        return jsonify({'message': 'تم إرسال التعليمات بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in send_instructions: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== طلبات إعادة تعيين كلمة المرور =====================

@admin_bp.route('/admin/password-reset-requests', methods=['GET'])
@login_required
@role_required(['admin'])
def get_reset_requests():
    try:
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        result = supabase_client.table('password_reset_requests').select('*').eq('status', 'pending').execute()
        return jsonify(result.data), 200
    except Exception as e:
        logger.error(f"Error in get_reset_requests: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/password-reset-requests/<int:req_id>/generate', methods=['POST'])
@login_required
@role_required(['admin'])
def generate_new_password(req_id):
    try:
        import secrets, string
        from werkzeug.security import generate_password_hash
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        req = supabase_client.table('password_reset_requests').select('*').eq('id', req_id).execute()
        if not req.data:
            return jsonify({'error': 'الطلب غير موجود'}), 404
        phone = req.data[0]['phone']
        alphabet = string.ascii_letters + string.digits
        new_pass = ''.join(secrets.choice(alphabet) for _ in range(8))
        hashed = generate_password_hash(new_pass)
        supabase_client.table('users').update({'password_hash': hashed}).eq('phone', phone).execute()
        supabase_client.table('password_reset_requests').update({'status': 'sent'}).eq('id', req_id).execute()
        LogModel.create(request.user['user_id'], f'إعادة تعيين كلمة المرور للرقم {phone}', request.remote_addr)
        return jsonify({'new_password': new_pass}), 200
    except Exception as e:
        logger.error(f"Error in generate_new_password: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/password-reset-requests/<int:req_id>/mark-sent', methods=['POST'])
@login_required
@role_required(['admin'])
def mark_request_sent(req_id):
    try:
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        supabase_client.table('password_reset_requests').update({'status': 'sent'}).eq('id', req_id).execute()
        return jsonify({'message': 'تم تحديث الحالة'}), 200
    except Exception as e:
        logger.error(f"Error in mark_request_sent: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== الملف الشخصي للمسؤول =====================

@admin_bp.route('/admin/profile', methods=['GET'])
@login_required
@role_required(['admin'])
def get_profile():
    try:
        user = UserModel.get_by_id(request.user['user_id'])
        if not user:
            return jsonify({'error': 'المستخدم غير موجود'}), 404
        return jsonify({
            'id': user['id'], 'email': user['email'], 'full_name': user.get('full_name', ''),
            'phone': user.get('phone', ''), 'role': user['role'], 'biometric_enabled': user.get('biometric_enabled', False)
        }), 200
    except Exception as e:
        logger.error(f"Error in get_profile: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/admin/profile', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_profile():
    try:
        data = request.json
        user_id = request.user['user_id']
        updates = {}
        if 'full_name' in data:
            updates['full_name'] = data['full_name']
        if 'phone' in data:
            updates['phone'] = data['phone']
        if 'email' in data:
            from models import UserModel
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
            from supabase import create_client
            from config import Config
            supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
            supabase_client.table('users').update(updates).eq('id', user_id).execute()
        LogModel.create(user_id, 'تحديث الملف الشخصي', request.remote_addr)
        return jsonify({'message': 'تم تحديث الملف الشخصي بنجاح'}), 200
    except Exception as e:
        logger.error(f"Error in update_profile: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== إدارة توكنات FCM (Firebase Cloud Messaging) =====================

@admin_bp.route('/api/fcm/register-token', methods=['POST'])
@login_required
def register_fcm_token():
    """حفظ توكن FCM الخاص بجهاز المستخدم لإرسال الإشعارات"""
    try:
        data = request.json
        token = data.get('token')
        if not token:
            return jsonify({'error': 'Token is required'}), 400

        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        user_id = request.user['user_id']

        # التحقق من وجود التوكن مسبقاً
        existing = supabase_client.table('fcm_tokens').select('*').eq('token', token).execute()
        if not existing.data:
            supabase_client.table('fcm_tokens').insert({
                'user_id': user_id,
                'token': token,
                'created_at': datetime.now().isoformat()
            }).execute()
        else:
            # تحديث وقت آخر استخدام
            supabase_client.table('fcm_tokens').update({
                'last_used': datetime.now().isoformat()
            }).eq('token', token).execute()

        return jsonify({'message': 'Token registered successfully'}), 200
    except Exception as e:
        logger.error(f"Error registering FCM token: {str(e)}")
        return jsonify({'error': str(e)}), 500


def send_fcm_notification(user_id, title, body, data=None):
    """إرسال إشعار FCM إلى جميع أجهزة المستخدم باستخدام Firebase Admin SDK"""
    if messaging is None:
        logger.warning("Firebase Admin SDK not initialized. Cannot send FCM notification.")
        return
    try:
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        tokens_res = supabase_client.table('fcm_tokens').select('token').eq('user_id', user_id).execute()
        if not tokens_res.data:
            return

        notification = messaging.Notification(title=title, body=body)
        for token_row in tokens_res.data:
            token = token_row['token']
            message = messaging.Message(
                notification=notification,
                token=token,
                data=data or {}
            )
            try:
                response = messaging.send(message)
                logger.info(f"FCM sent to {token}: {response}")
            except Exception as e:
                logger.error(f"FCM failed for token {token}: {e}")
                # حذف التوكن غير الصالح
                if 'invalid-registration-token' in str(e) or 'not-registered' in str(e):
                    supabase_client.table('fcm_tokens').delete().eq('token', token).execute()
    except Exception as e:
        logger.error(f"Error sending FCM notification: {str(e)}")
