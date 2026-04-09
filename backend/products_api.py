# =====================================================
# products_api.py - إدارة المنتجات (واجهة برمجة التطبيقات)
# =====================================================

import logging
from flask import Blueprint, request, jsonify
from decorators import login_required, role_required
from models import ProductModel, ImageModel, SettingsModel, LogModel
from supabase_storage import upload_image, delete_image
from image_optimizer import optimize_image_to_target

logger = logging.getLogger(__name__)
products_bp = Blueprint('products', __name__)

# ===================== APIs العامة (للعملاء والزوار) =====================

@products_bp.route('/products', methods=['GET'])
def get_public_products():
    """جلب المنتجات للعرض العام (بدون حماية) - يمكن تخصيصها حسب الحاجة"""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        category = request.args.get('category', None)
        search = request.args.get('search', None)
        products = ProductModel.get_all(limit, offset, category, search)
        total = ProductModel.count_all(category, search)
        # إضافة عدد الصور لكل منتج
        for p in products:
            images = ImageModel.get_images(p['sku'])
            p['image_count'] = len(images)
        return jsonify({
            'products': products,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total
        }), 200
    except Exception as e:
        logger.error(f"Error in get_public_products: {str(e)}")
        return jsonify({'error': str(e)}), 500


@products_bp.route('/products/<sku>', methods=['GET'])
def get_public_product(sku):
    """جلب منتج واحد بتفاصيله (عام)"""
    try:
        product = ProductModel.get_by_sku(sku)
        if not product:
            return jsonify({'error': 'المنتج غير موجود'}), 404
        # جلب الصور المرتبطة
        images = ImageModel.get_images(sku)
        product['images'] = images
        return jsonify(product), 200
    except Exception as e:
        logger.error(f"Error in get_public_product: {str(e)}")
        return jsonify({'error': str(e)}), 500


@products_bp.route('/products/categories', methods=['GET'])
def get_public_categories():
    """جلب قائمة الفئات (يمكن تحسينها لاحقاً من جدول الفئات)"""
    try:
        # حالياً نرجع قائمة فارغة أو نستخرجها من المنتجات
        from supabase import create_client
        from config import Config
        supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        res = supabase_client.table('products').select('category').execute()
        cats = set()
        for item in res.data:
            if item.get('category'):
                cats.add(item['category'])
        return jsonify({'categories': sorted(list(cats))}), 200
    except Exception as e:
        logger.error(f"Error in get_public_categories: {str(e)}")
        return jsonify({'categories': []}), 200


# ===================== APIs إدارة المنتجات (للمسؤول فقط) =====================

@products_bp.route('/admin/products', methods=['GET'])
@login_required
@role_required(['admin'])
def list_products_admin():
    """جلب جميع المنتجات للوحة التحكم"""
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
        return jsonify({
            'products': products,
            'total': total,
            'limit': limit,
            'offset': offset
        }), 200
    except Exception as e:
        logger.error(f"Error in list_products_admin: {str(e)}")
        return jsonify({'error': str(e)}), 500


@products_bp.route('/admin/products/<sku>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def admin_delete_product(sku):
    """حذف منتج مع جميع صوره"""
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


@products_bp.route('/admin/products/<sku>', methods=['PUT'])
@login_required
@role_required(['admin'])
def admin_update_product(sku):
    """تحديث بيانات منتج"""
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


@products_bp.route('/admin/products', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_create_product():
    """إنشاء منتج جديد"""
    try:
        data = request.json
        required = ['sku', 'name', 'unit_price']
        for f in required:
            if f not in data:
                return jsonify({'error': f'حقل {f} مطلوب'}), 400
        # التحقق من عدم وجود SKU مسبقاً
        existing = ProductModel.get_by_sku(data['sku'])
        if existing:
            return jsonify({'error': 'الرمز التعريفي SKU مستخدم مسبقاً'}), 409
        product = ProductModel.create_or_update(data)
        LogModel.create(request.user['user_id'], f'إنشاء منتج {data["sku"]}', request.remote_addr)
        return jsonify(product), 201
    except Exception as e:
        logger.error(f"Error in admin_create_product: {str(e)}")
        return jsonify({'error': str(e)}), 500


# ===================== إدارة صور المنتجات (للمسؤول) =====================

@products_bp.route('/admin/products/<sku>/upload-images', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_upload_images(sku):
    """رفع صور جديدة لمنتج"""
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


@products_bp.route('/admin/products/<sku>/images/<int:image_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def admin_delete_image(sku, image_id):
    """حذف صورة محددة من منتج"""
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
