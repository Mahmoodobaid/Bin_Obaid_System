# =====================================================
# supabase_storage.py - رفع وإدارة الصور عبر Supabase Storage
# بديل آمن ومجاني لـ Cloudinary (متوفر في اليمن)
# الإصدار 2.0 - مع دعم ضغط الصور والتحقق من المساحة
# =====================================================

import os
import uuid
import logging
from datetime import datetime
from supabase import create_client
from config import Config
from image_optimizer import optimize_image_to_target

logger = logging.getLogger(__name__)

# الاتصال بـ Supabase
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

# اسم الـ bucket لتخزين صور المنتجات
PRODUCT_IMAGES_BUCKET = "product_images"
MAX_FILE_SIZE_MB = 2  # الحد الأقصى لحجم الملف (2 ميغابايت)


def init_storage_bucket():
    """
    إنشاء الـ bucket إذا لم يكن موجوداً.
    يجب استدعاء هذه الدالة مرة واحدة عند بدء تشغيل التطبيق.
    """
    try:
        # التحقق من وجود الـ bucket
        buckets = supabase.storage.list_buckets()
        bucket_names = [b['name'] for b in buckets]
        
        if PRODUCT_IMAGES_BUCKET not in bucket_names:
            # إنشاء bucket جديد (عام للقراءة)
            supabase.storage.create_bucket(
                PRODUCT_IMAGES_BUCKET, 
                {'public': True}
            )
            logger.info(f"✅ Bucket '{PRODUCT_IMAGES_BUCKET}' created successfully")
        else:
            logger.info(f"✅ Bucket '{PRODUCT_IMAGES_BUCKET}' already exists")
            
        # إضافة سياسات الأمان (اختياري)
        _setup_bucket_policies()
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize storage bucket: {str(e)}")


def _setup_bucket_policies():
    """إعداد سياسات الوصول للـ bucket (اختياري)"""
    try:
        # سياسة للقراءة العامة (تسمح للجميع بقراءة الصور)
        policy_read = f"""
        CREATE POLICY IF NOT EXISTS "Public read access" 
        ON storage.objects FOR SELECT 
        USING (bucket_id = '{PRODUCT_IMAGES_BUCKET}');
        """
        
        # سياسة للرفع من قبل المستخدمين المسجلين
        policy_insert = f"""
        CREATE POLICY IF NOT EXISTS "Authenticated upload" 
        ON storage.objects FOR INSERT 
        WITH CHECK (bucket_id = '{PRODUCT_IMAGES_BUCKET}' AND auth.role() = 'authenticated');
        """
        
        # تنفيذ السياسات (قد تتطلب صلاحيات إضافية)
        # supabase.sql(policy_read).execute()
        # supabase.sql(policy_insert).execute()
        
    except Exception as e:
        logger.warning(f"Could not setup bucket policies: {e}")


def upload_image(file_bytes, filename, content_type='image/jpeg'):
    """
    رفع صورة إلى Supabase Storage مع ضغط تلقائي.
    
    المعاملات:
        file_bytes: bytes - محتوى الصورة
        filename: str - اسم الملف الأصلي
        content_type: str - نوع المحتوى (اختياري)
    
    تعيد: str - الرابط العام للصورة
    
    يرفع استثناء: Exception في حالة فشل الرفع
    """
    try:
        # التحقق من حجم الملف
        file_size_mb = len(file_bytes) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.warning(f"File size {file_size_mb:.2f}MB exceeds limit, compressing...")
        
        # ضغط الصورة وتحسينها
        optimized_bytes, content_type, final_size_kb = optimize_image_to_target(file_bytes, filename)
        logger.info(f"Image compressed: {file_size_mb:.2f}MB -> {final_size_kb/1024:.2f}MB")
        
        # إنشاء مسار فريد للملف
        ext = filename.split('.')[-1] if '.' in filename else 'jpg'
        unique_name = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        file_path = f"products/{unique_name}"
        
        # رفع الملف المضغوط
        supabase.storage.from_(PRODUCT_IMAGES_BUCKET).upload(
            file_path,
            optimized_bytes,
            file_options={"content-type": content_type}
        )
        
        # الحصول على الرابط العام
        public_url = supabase.storage.from_(PRODUCT_IMAGES_BUCKET).get_public_url(file_path)
        
        logger.info(f"✅ Image uploaded successfully: {public_url[:50]}...")
        return public_url
        
    except Exception as e:
        logger.error(f"❌ Supabase Storage upload failed: {str(e)}")
        raise Exception(f"Failed to upload image: {str(e)}")


def upload_multiple_images(files_data):
    """
    رفع عدة صور في طلب واحد.
    
    المعاملات:
        files_data: list - قائمة من (file_bytes, filename, content_type)
    
    تعيد: list - قائمة بالروابط العامة للصور
    """
    urls = []
    for file_bytes, filename, content_type in files_data:
        try:
            url = upload_image(file_bytes, filename, content_type)
            urls.append(url)
        except Exception as e:
            logger.error(f"Failed to upload {filename}: {e}")
            # نستمر في رفع بقية الصور حتى لو فشلت واحدة
            continue
    return urls


def delete_image(image_url):
    """
    حذف صورة من Supabase Storage باستخدام الرابط العام.
    
    المعاملات:
        image_url: str - الرابط العام للصورة
    
    تعيد: bool - True إذا تم الحذف بنجاح، False إذا فشل
    """
    try:
        # استخراج مسار الملف من الرابط
        # الرابط يكون: https://[project].supabase.co/storage/v1/object/public/product_images/products/xxx.jpg
        parts = image_url.split(f'/product_images/')
        if len(parts) < 2:
            logger.warning(f"Could not extract path from URL: {image_url}")
            return False
        
        file_path = parts[1]
        supabase.storage.from_(PRODUCT_IMAGES_BUCKET).remove([file_path])
        logger.info(f"✅ Image deleted successfully: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to delete image: {str(e)}")
        return False


def delete_multiple_images(image_urls):
    """
    حذف عدة صور دفعة واحدة.
    
    المعاملات:
        image_urls: list - قائمة بالروابط العامة للصور
    
    تعيد: dict - إحصائيات الحذف (success, failed)
    """
    success_count = 0
    failed_count = 0
    
    for url in image_urls:
        if delete_image(url):
            success_count += 1
        else:
            failed_count += 1
    
    logger.info(f"Deleted {success_count} images, {failed_count} failed")
    return {'success': success_count, 'failed': failed_count}


def get_public_url(file_path):
    """
    الحصول على الرابط العام لملف معين داخل الـ bucket.
    
    المعاملات:
        file_path: str - مسار الملف داخل الـ bucket
    
    تعيد: str - الرابط العام
    """
    return supabase.storage.from_(PRODUCT_IMAGES_BUCKET).get_public_url(file_path)


def get_bucket_usage():
    """
    الحصول على معلومات عن استخدام الـ bucket.
    (ملاحظة: قد لا تعمل في الخطة المجانية)
    
    تعيد: dict - معلومات الاستخدام
    """
    try:
        # Supabase Storage API لا يوفر مباشرة حجم الـ bucket
        # يمكننا حساب عدد الملفات فقط
        files = supabase.storage.from_(PRODUCT_IMAGES_BUCKET).list('products/')
        return {
            'file_count': len(files),
            'bucket_name': PRODUCT_IMAGES_BUCKET,
            'max_file_size_mb': MAX_FILE_SIZE_MB
        }
    except Exception as e:
        logger.error(f"Failed to get bucket usage: {e}")
        return {'error': str(e)}


def delete_all_product_images(product_sku, image_urls):
    """
    حذف جميع صور منتج معين من التخزين.
    
    المعاملات:
        product_sku: str - كود المنتج
        image_urls: list - قائمة بروابط الصور المرتبطة بالمنتج
    
    تعيد: bool - True إذا تم حذف جميع الصور بنجاح
    """
    try:
        success = True
        for url in image_urls:
            if not delete_image(url):
                success = False
                logger.warning(f"Failed to delete image for product {product_sku}: {url}")
        return success
    except Exception as e:
        logger.error(f"Error deleting product images: {e}")
        return False


def get_image_url_by_path(file_path):
    """
    الحصول على الرابط العام لمسار معين.
    
    المعاملات:
        file_path: str - مسار الملف داخل الـ bucket (مثل: products/xxx.jpg)
    
    تعيد: str - الرابط العام
    """
    return supabase.storage.from_(PRODUCT_IMAGES_BUCKET).get_public_url(file_path)


def file_exists(file_path):
    """
    التحقق من وجود ملف معين في الـ bucket.
    
    المعاملات:
        file_path: str - مسار الملف داخل الـ bucket
    
    تعيد: bool - True إذا كان الملف موجوداً
    """
    try:
        supabase.storage.from_(PRODUCT_IMAGES_BUCKET).list(file_path)
        return True
    except Exception:
        return False