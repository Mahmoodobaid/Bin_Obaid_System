# =====================================================
# images_api.py - إدارة صور المنتجات (رفع، استرجاع، حذف)
# الإصدار 2.0 - مع ضغط تلقائي ودعم Supabase Storage
# =====================================================

import logging
import base64
from flask import Blueprint, request, jsonify
from decorators import login_required, role_required
from models import ProductModel, ImageModel, SettingsModel
from supabase_storage import upload_image, delete_image
from image_optimizer import optimize_image_to_target

logger = logging.getLogger(__name__)
images_bp = Blueprint('images', __name__)


@images_bp.route('/products/<sku>/images', methods=['POST'])
@login_required
@role_required(['admin'])
def upload_images(sku):
    """
    رفع صورة أو عدة صور لمنتج معين.
    يدعم رفع الملفات المباشرة (multipart/form-data) أو base64.
    
    الجسم (multipart): images[] = ملفات الصور
    الجسم (JSON): {"images_base64": ["data:image/jpeg;base64,...", ...]}
    """
    try:
        # التحقق من وجود المنتج
        product = ProductModel.get_by_sku(sku)
        if not product:
            return jsonify({'error': 'المنتج غير موجود'}), 404

        # قراءة الحد الأقصى للصور من الإعدادات
        max_images = SettingsModel.get_int('max_images_per_product', 4)

        # التحقق من عدد الصور الحالية
        current_images = ImageModel.get_images(sku)
        if len(current_images) >= max_images:
            return jsonify({'error': f'لا يمكن إضافة أكثر من {max_images} صور لهذا المنتج'}), 400

        # تحديد عدد الصور المطلوب رفعها في هذا الطلب
        images_count = 0
        if 'images' in request.files:
            files = request.files.getlist('images')
            images_count = len([f for f in files if f and f.filename])
        elif 'images_base64' in request.json:
            images_count = len(request.json['images_base64'])
        
        if images_count == 0:
            return jsonify({'error': 'لم يتم إرسال أي صور'}), 400
        
        if images_count > max_images - len(current_images):
            return jsonify({'error': f'يمكنك رفع {max_images - len(current_images)} صور كحد أقصى'}), 400

        image_urls = []

        # حالة رفع الملفات المباشرة
        if 'images' in request.files:
            for file in request.files.getlist('images'):
                if file and file.filename:
                    # قراءة محتوى الملف
                    file_bytes = file.read()
                    # ضغط الصورة تلقائياً إلى 200KB أو أقل
                    optimized_bytes, content_type, final_size_kb = optimize_image_to_target(file_bytes, file.filename)
                    # رفع الصورة المضغوطة إلى Supabase Storage
                    url = upload_image(optimized_bytes, file.filename, content_type)
                    image_urls.append(url)
                    logger.info(f"📤 Uploaded image for {sku}, size: {final_size_kb:.1f}KB")

        # حالة رفع base64 (من تطبيق Flutter)
        elif 'images_base64' in request.json:
            for idx, b64 in enumerate(request.json['images_base64']):
                # إزالة رأس data:image إذا وجد
                if ',' in b64:
                    b64 = b64.split(',')[1]
                file_bytes = base64.b64decode(b64)
                optimized_bytes, content_type, final_size_kb = optimize_image_to_target(file_bytes, f"image_{idx}.jpg")
                url = upload_image(optimized_bytes, f"image_{idx}.jpg", content_type)
                image_urls.append(url)
                logger.info(f"📤 Uploaded base64 image for {sku}, size: {final_size_kb:.1f}KB")

        # حفظ الروابط في قاعدة البيانات
        if image_urls:
            ImageModel.add_images(sku, image_urls)
            return jsonify({
                'message': f'تم رفع {len(image_urls)} صورة بنجاح',
                'urls': image_urls
            }), 201
        else:
            return jsonify({'error': 'فشل رفع الصور'}), 500

    except Exception as e:
        logger.error(f"❌ Error in upload_images for {sku}: {str(e)}")
        return jsonify({'error': f'حدث خطأ أثناء رفع الصور: {str(e)}'}), 500


@images_bp.route('/products/<sku>/images', methods=['GET'])
def get_images(sku):
    """
    استرجاع جميع صور منتج معين (عام، لا يحتاج مصادقة)
    """
    try:
        images = ImageModel.get_images(sku)
        return jsonify({'images': images}), 200
    except Exception as e:
        logger.error(f"❌ Error in get_images for {sku}: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء جلب الصور'}), 500


@images_bp.route('/products/<sku>/images/<int:image_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_image(sku, image_id):
    """
    حذف صورة محددة لمنتج معين
    """
    try:
        # التحقق من وجود المنتج
        product = ProductModel.get_by_sku(sku)
        if not product:
            return jsonify({'error': 'المنتج غير موجود'}), 404

        # جلب معلومات الصورة من قاعدة البيانات
        from supabase import create_client
        from config import Config
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        result = supabase.table('product_images').select('image_url').eq('id', image_id).eq('product_sku', sku).execute()
        if not result.data:
            return jsonify({'error': 'الصورة غير موجودة'}), 404

        image_url = result.data[0]['image_url']

        # حذف من Supabase Storage
        delete_image(image_url)

        # حذف من قاعدة البيانات
        supabase.table('product_images').delete().eq('id', image_id).execute()

        # إضافة إلى sync_queue
        supabase.table('sync_queue').insert({
            'entity_type': 'image',
            'entity_id': sku,
            'action': 'DELETE'
        }).execute()

        logger.info(f"🗑️ Deleted image {image_id} for product {sku}")
        return jsonify({'message': 'تم حذف الصورة بنجاح'}), 200
        
    except Exception as e:
        logger.error(f"❌ Error in delete_image for {sku}: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء حذف الصورة'}), 500


@images_bp.route('/products/<sku>/images/reorder', methods=['PUT'])
@login_required
@role_required(['admin'])
def reorder_images(sku):
    """
    إعادة ترتيب صور المنتج.
    الجسم: {"order": [image_id1, image_id2, ...]}
    """
    try:
        data = request.json
        new_order = data.get('order', [])
        
        if not isinstance(new_order, list):
            return jsonify({'error': 'الترتيب يجب أن يكون قائمة'}), 400
        
        from supabase import create_client
        from config import Config
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

        for idx, image_id in enumerate(new_order):
            supabase.table('product_images').update({'display_order': idx}).eq('id', image_id).eq('product_sku', sku).execute()

        logger.info(f"🔄 Reordered images for product {sku}")
        return jsonify({'message': 'تم إعادة ترتيب الصور بنجاح'}), 200
        
    except Exception as e:
        logger.error(f"❌ Error in reorder_images for {sku}: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء إعادة الترتيب'}), 500


@images_bp.route('/products/<sku>/images/primary/<int:image_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def set_primary_image(sku, image_id):
    """
    تعيين صورة كالصورة الرئيسية (ترتيب 0)
    """
    try:
        from supabase import create_client
        from config import Config
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        # التحقق من وجود المنتج
        product = ProductModel.get_by_sku(sku)
        if not product:
            return jsonify({'error': 'المنتج غير موجود'}), 404
        
        # إعادة تعيين جميع الصور إلى ترتيب 1 فأكثر
        supabase.table('product_images').update({'display_order': 1}).eq('product_sku', sku).execute()
        
        # تعيين الصورة المحددة كالصورة الرئيسية (ترتيب 0)
        supabase.table('product_images').update({'display_order': 0}).eq('id', image_id).eq('product_sku', sku).execute()
        
        logger.info(f"⭐ Set image {image_id} as primary for product {sku}")
        return jsonify({'message': 'تم تعيين الصورة الرئيسية بنجاح'}), 200
        
    except Exception as e:
        logger.error(f"❌ Error in set_primary_image for {sku}: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء تعيين الصورة الرئيسية'}), 500