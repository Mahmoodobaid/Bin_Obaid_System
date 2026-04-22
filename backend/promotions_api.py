# =====================================================
# promotions_api.py - إدارة الإعلانات الترويجية والإشعارات
# الإصدار 2.0 - مع دعم الإشعارات الفورية وتحليلات النقرات
# =====================================================

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from decorators import login_required, role_required
from models import PromotionModel, UserModel, ProductModel
from fcm_sender import send_to_customers, send_push_notification

logger = logging.getLogger(__name__)
promotions_bp = Blueprint('promotions', __name__)


# ===================== جلب الإعلانات (للعملاء) =====================

@promotions_bp.route('/promotions', methods=['GET'])
@login_required
def get_active_promotions():
    """
    جلب الإعلانات النشطة والفعالة للعملاء (يتطلب تسجيل دخول)
    """
    try:
        promotions = PromotionModel.get_active()
        
        # إضافة اسم المنتج إذا كان مرتبطاً بمنتج
        for promo in promotions:
            if promo.get('product_sku'):
                product = ProductModel.get_by_sku(promo['product_sku'])
                promo['product_name'] = product['name'] if product else None
        
        return jsonify(promotions), 200
    except Exception as e:
        logger.error(f"❌ Error in get_active_promotions: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء جلب الإعلانات'}), 500


@promotions_bp.route('/promotions/latest', methods=['GET'])
@login_required
def get_latest_promotions():
    """
    جلب أحدث 5 إعلانات نشطة (للشريط العلوي)
    """
    try:
        promotions = PromotionModel.get_active()
        # ترتيب حسب تاريخ الإنشاء (الأحدث أولاً)
        promotions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return jsonify(promotions[:5]), 200
    except Exception as e:
        logger.error(f"❌ Error in get_latest_promotions: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء جلب الإعلانات'}), 500


# ===================== إدارة الإعلانات (للمسؤول) =====================

@promotions_bp.route('/admin/promotions', methods=['GET'])
@login_required
@role_required(['admin'])
def admin_get_promotions():
    """
    جلب جميع الإعلانات (للمسؤول) مع إمكانية تضمين غير النشطة
    """
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        promotions = PromotionModel.get_all(include_inactive=include_inactive)
        
        # إضافة إحصائيات النقرات لكل إعلان
        for promo in promotions:
            promo['click_count'] = PromotionModel.get_click_count(promo['id'])
        
        return jsonify(promotions), 200
    except Exception as e:
        logger.error(f"❌ Error in admin_get_promotions: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء جلب الإعلانات'}), 500


@promotions_bp.route('/admin/promotions', methods=['POST'])
@login_required
@role_required(['admin'])
def create_promotion():
    """
    إنشاء إعلان ترويجي جديد مع إمكانية إرسال إشعار فوري.
    
    الجسم:
    {
        "title": "عرض خاص على الأسلاك",
        "body": "خصم 20% على جميع الأسلاك",
        "image_url": "https://...",
        "product_sku": "WIRE-001",
        "start_date": "2026-04-01T00:00:00",
        "end_date": "2026-04-30T23:59:59",
        "send_notification": true
    }
    """
    try:
        data = request.json
        title = data.get('title')
        body = data.get('body', '')
        image_url = data.get('image_url')
        product_sku = data.get('product_sku')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        send_notification = data.get('send_notification', False)
        
        if not title:
            return jsonify({'error': 'عنوان الإعلان مطلوب'}), 400
        
        # التحقق من صحة التواريخ
        if start_date:
            try:
                datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            except:
                return jsonify({'error': 'تاريخ البدء غير صالح'}), 400
        
        if end_date:
            try:
                datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            except:
                return jsonify({'error': 'تاريخ الانتهاء غير صالح'}), 400
        
        # التحقق من وجود المنتج إذا تم تحديده
        if product_sku:
            product = ProductModel.get_by_sku(product_sku)
            if not product:
                return jsonify({'error': 'المنتج المحدد غير موجود'}), 404
        
        created_by = request.user['user_id']
        promo = PromotionModel.create(
            title=title,
            body=body,
            image_url=image_url,
            product_sku=product_sku,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by
        )
        
        if not promo:
            return jsonify({'error': 'فشل إنشاء الإعلان'}), 500
        
        # تسجيل الحدث
        from models import LogModel
        LogModel.create(created_by, f'إنشاء إعلان: {title}', request.remote_addr)
        
        # إرسال إشعار فوري إذا طلب المسؤول
        if send_notification:
            notification_data = {
                'promotion_id': promo['id'],
                'product_sku': product_sku or '',
                'type': 'promotion'
            }
            
            # إرسال لجميع العملاء
            result = send_to_customers(title, body, notification_data)
            
            if result:
                logger.info(f"📢 Notification sent for promotion {promo['id']}")
            else:
                logger.warning(f"⚠️ Failed to send notifications for promotion {promo['id']}")
        
        return jsonify(promo), 201
        
    except Exception as e:
        logger.error(f"❌ Error in create_promotion: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء إنشاء الإعلان'}), 500


@promotions_bp.route('/admin/promotions/<int:promo_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_promotion(promo_id):
    """
    تحديث إعلان موجود
    """
    try:
        data = request.json
        success = PromotionModel.update(promo_id, data)
        
        if not success:
            return jsonify({'error': 'الإعلان غير موجود'}), 404
        
        from models import LogModel
        LogModel.create(request.user['user_id'], f'تحديث إعلان {promo_id}', request.remote_addr)
        
        return jsonify({'message': 'تم تحديث الإعلان بنجاح'}), 200
        
    except Exception as e:
        logger.error(f"❌ Error in update_promotion: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء تحديث الإعلان'}), 500


@promotions_bp.route('/admin/promotions/<int:promo_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_promotion(promo_id):
    """
    حذف إعلان (تعطيله فقط، لا حذف نهائي)
    """
    try:
        success = PromotionModel.delete(promo_id)
        
        if not success:
            return jsonify({'error': 'الإعلان غير موجود'}), 404
        
        from models import LogModel
        LogModel.create(request.user['user_id'], f'حذف إعلان {promo_id}', request.remote_addr)
        
        return jsonify({'message': 'تم حذف الإعلان بنجاح'}), 200
        
    except Exception as e:
        logger.error(f"❌ Error in delete_promotion: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء حذف الإعلان'}), 500


@promotions_bp.route('/admin/promotions/<int:promo_id>/toggle', methods=['POST'])
@login_required
@role_required(['admin'])
def toggle_promotion_status(promo_id):
    """
    تفعيل أو تعطيل إعلان (بدون حذف)
    الجسم: {"is_active": true/false}
    """
    try:
        data = request.json
        is_active = data.get('is_active', True)
        
        success = PromotionModel.update(promo_id, {'is_active': is_active})
        
        if not success:
            return jsonify({'error': 'الإعلان غير موجود'}), 404
        
        status_text = 'تفعيل' if is_active else 'تعطيل'
        from models import LogModel
        LogModel.create(request.user['user_id'], f'{status_text} إعلان {promo_id}', request.remote_addr)
        
        return jsonify({'message': f'تم {status_text} الإعلان بنجاح'}), 200
        
    except Exception as e:
        logger.error(f"❌ Error in toggle_promotion_status: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء تغيير حالة الإعلان'}), 500


# ===================== تتبع التفاعل مع الإعلانات =====================

@promotions_bp.route('/promotions/<int:promo_id>/click', methods=['POST'])
@login_required
def track_promotion_click(promo_id):
    """
    تسجيل نقرة على إعلان (للتحليلات)
    """
    try:
        user_id = request.user['user_id']
        PromotionModel.record_click(promo_id, user_id)
        
        # الحصول على رابط المنتج المرتبط إن وجد
        promo = PromotionModel.get_all(include_inactive=True)
        promo = next((p for p in promo if p['id'] == promo_id), None)
        
        return jsonify({
            'message': 'تم التسجيل',
            'product_sku': promo.get('product_sku') if promo else None
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error in track_promotion_click: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500


# ===================== إحصائيات الإعلانات =====================

@promotions_bp.route('/admin/promotions/stats', methods=['GET'])
@login_required
@role_required(['admin'])
def get_promotions_stats():
    """
    إحصائيات عامة للإعلانات (للمسؤول)
    """
    try:
        promotions = PromotionModel.get_all(include_inactive=True)
        
        total_clicks = 0
        active_count = 0
        expired_count = 0
        
        now = datetime.utcnow().isoformat()
        
        for promo in promotions:
            clicks = PromotionModel.get_click_count(promo['id'])
            total_clicks += clicks
            promo['click_count'] = clicks
            
            if promo.get('is_active'):
                active_count += 1
                # التحقق من انتهاء الصلاحية
                if promo.get('end_date') and promo['end_date'] < now:
                    expired_count += 1
        
        return jsonify({
            'total_promotions': len(promotions),
            'active_promotions': active_count,
            'expired_promotions': expired_count,
            'total_clicks': total_clicks,
            'average_clicks_per_promo': round(total_clicks / len(promotions), 2) if promotions else 0,
            'promotions': promotions
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error in get_promotions_stats: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء جلب الإحصائيات'}), 500


# ===================== إرسال إشعار يدوي =====================

@promotions_bp.route('/admin/send-notification', methods=['POST'])
@login_required
@role_required(['admin'])
def send_manual_notification():
    """
    إرسال إشعار يدوي لجميع العملاء (بدون إنشاء إعلان)
    
    الجسم:
    {
        "title": "تنبيه مهم",
        "body": "هذا نص الإشعار",
        "data": {"key": "value"}
    }
    """
    try:
        data = request.json
        title = data.get('title')
        body = data.get('body')
        notification_data = data.get('data', {})
        
        if not title or not body:
            return jsonify({'error': 'العنوان والنص مطلوبان'}), 400
        
        result = send_to_customers(title, body, notification_data)
        
        from models import LogModel
        LogModel.create(request.user['user_id'], f'إرسال إشعار يدوي: {title}', request.remote_addr)
        
        return jsonify({
            'message': 'تم إرسال الإشعار',
            'result': result
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error in send_manual_notification: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء إرسال الإشعار'}), 500