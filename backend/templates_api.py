# =====================================================
# templates_api.py - إدارة النماذج الجاهزة للطلبات السريعة
# الإصدار 2.0 - مع دعم تفعيل/تعطيل النماذج وإحصائيات الاستخدام
# =====================================================

import logging
from flask import Blueprint, request, jsonify
from decorators import login_required, role_required
from models import TemplateModel, ProductModel, LogModel

logger = logging.getLogger(__name__)
templates_bp = Blueprint('templates', __name__)


# ===================== جلب النماذج (للعملاء) =====================

@templates_bp.route('/templates', methods=['GET'])
@login_required
def get_templates():
    """
    جلب جميع النماذج النشطة (للاستخدام من قبل العملاء)
    """
    try:
        templates = TemplateModel.get_active_templates()
        
        # إضافة معلومات إضافية لكل نموذج (عدد الأصناف، إجمالي السعر التقريبي)
        for template in templates:
            items = template.get('items', [])
            template['items_count'] = len(items)
            
            # حساب السعر التقريبي (اختياري)
            total_price = 0
            for item in items:
                sku = item.get('sku')
                quantity = item.get('quantity', 0)
                product = ProductModel.get_by_sku(sku)
                if product:
                    unit_price = product.get('unit_price', 0)
                    total_price += unit_price * quantity
            template['estimated_price'] = round(total_price, 2)
        
        return jsonify(templates), 200
    except Exception as e:
        logger.error(f"❌ Error in get_templates: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء جلب النماذج'}), 500


@templates_bp.route('/templates/<int:template_id>/apply', methods=['POST'])
@login_required
def apply_template(template_id):
    """
    تطبيق نموذج: إرجاع قائمة الأصناف التي سيتم إضافتها إلى السلة.
    يمكن للعميل استدعاء هذا الـ endpoint ثم إضافة الأصناف إلى السلة محلياً.
    """
    try:
        templates = TemplateModel.get_active_templates()
        template = next((t for t in templates if t['id'] == template_id), None)
        
        if not template:
            return jsonify({'error': 'النموذج غير موجود أو غير نشط'}), 404
        
        items = template.get('items', [])
        
        # التحقق من توفر المنتجات في المخزون
        unavailable_items = []
        for item in items:
            sku = item.get('sku')
            quantity = item.get('quantity', 0)
            product = ProductModel.get_by_sku(sku)
            
            if not product:
                unavailable_items.append({'sku': sku, 'reason': 'غير موجود'})
            elif product.get('quantity_in_stock', 0) < quantity:
                unavailable_items.append({
                    'sku': sku, 
                    'reason': f'الكمية المتوفرة: {product.get("quantity_in_stock", 0)}',
                    'available': product.get('quantity_in_stock', 0)
                })
        
        # إضافة أسماء المنتجات للعناصر
        enriched_items = []
        for item in items:
            sku = item.get('sku')
            product = ProductModel.get_by_sku(sku)
            enriched_items.append({
                'sku': sku,
                'name': product['name'] if product else sku,
                'quantity': item.get('quantity', 0),
                'unit_price': product['unit_price'] if product else 0,
                'is_required': item.get('is_required', True)
            })
        
        # تسجيل استخدام النموذج (للإحصائيات)
        LogModel.create(
            request.user['user_id'], 
            f'تطبيق نموذج: {template["name"]}', 
            request.remote_addr
        )
        
        return jsonify({
            'template_id': template['id'],
            'name': template['name'],
            'description': template.get('description', ''),
            'items': enriched_items,
            'items_count': len(enriched_items),
            'unavailable_items': unavailable_items,
            'has_unavailable': len(unavailable_items) > 0
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error in apply_template: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء تطبيق النموذج'}), 500


# ===================== إدارة النماذج (للمسؤول) =====================

@templates_bp.route('/admin/templates', methods=['GET'])
@login_required
@role_required(['admin'])
def admin_get_templates():
    """
    جلب جميع النماذج (بما فيها غير النشطة) للمسؤول
    """
    try:
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        templates = TemplateModel.get_all(include_inactive=include_inactive)
        
        # إضافة إحصائيات لكل نموذج
        for template in templates:
            items = template.get('items', [])
            template['items_count'] = len(items)
            
            # حساب إجمالي السعر التقريبي
            total_price = 0
            for item in items:
                sku = item.get('sku')
                quantity = item.get('quantity', 0)
                product = ProductModel.get_by_sku(sku)
                if product:
                    total_price += product.get('unit_price', 0) * quantity
            template['estimated_price'] = round(total_price, 2)
        
        return jsonify(templates), 200
    except Exception as e:
        logger.error(f"❌ Error in admin_get_templates: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء جلب النماذج'}), 500


@templates_bp.route('/admin/templates', methods=['POST'])
@login_required
@role_required(['admin'])
def create_template():
    """
    إنشاء نموذج طلب سريع جديد.
    
    الجسم: {
        "name": "طلب تأسيس منزل",
        "description": "يشمل جميع الأصناف الأساسية",
        "items": [
            {"sku": "WIRE-001", "quantity": 100, "is_required": true, "name": "سلك 2.5 مم"}
        ]
    }
    """
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description', '')
        items = data.get('items', [])
        
        if not name:
            return jsonify({'error': 'اسم النموذج مطلوب'}), 400
        
        if not items:
            return jsonify({'error': 'يجب إضافة صنف واحد على الأقل للنموذج'}), 400
        
        # التحقق من صحة العناصر
        for item in items:
            sku = item.get('sku')
            quantity = item.get('quantity', 0)
            
            if not sku:
                return jsonify({'error': 'SKU مطلوب لكل صنف'}), 400
            
            if quantity <= 0:
                return jsonify({'error': f'الكمية يجب أن تكون أكبر من صفر للصنف {sku}'}), 400
            
            # التحقق من وجود المنتج
            product = ProductModel.get_by_sku(sku)
            if not product:
                return jsonify({'error': f'المنتج {sku} غير موجود'}), 404
            
            # إضافة اسم المنتج تلقائياً (اختياري)
            if 'name' not in item:
                item['name'] = product['name']
        
        created_by = request.user['user_id']
        template = TemplateModel.create_template(name, description, items, created_by)
        
        if not template:
            return jsonify({'error': 'فشل إنشاء النموذج'}), 500
        
        LogModel.create(created_by, f'إنشاء نموذج جديد: {name}', request.remote_addr)
        
        return jsonify(template), 201
        
    except Exception as e:
        logger.error(f"❌ Error in create_template: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء إنشاء النموذج'}), 500


@templates_bp.route('/admin/templates/<int:template_id>', methods=['PUT'])
@login_required
@role_required(['admin'])
def update_template(template_id):
    """
    تحديث نموذج موجود
    """
    try:
        data = request.json
        existing_templates = TemplateModel.get_all(include_inactive=True)
        existing = next((t for t in existing_templates if t['id'] == template_id), None)
        
        if not existing:
            return jsonify({'error': 'النموذج غير موجود'}), 404
        
        # التحقق من العناصر إذا تم تحديثها
        if 'items' in data:
            items = data['items']
            for item in items:
                sku = item.get('sku')
                if sku:
                    product = ProductModel.get_by_sku(sku)
                    if not product:
                        return jsonify({'error': f'المنتج {sku} غير موجود'}), 404
        
        success = TemplateModel.update_template(template_id, data)
        
        if not success:
            return jsonify({'error': 'فشل تحديث النموذج'}), 500
        
        LogModel.create(request.user['user_id'], f'تحديث نموذج {template_id}', request.remote_addr)
        
        return jsonify({'message': 'تم تحديث النموذج بنجاح'}), 200
        
    except Exception as e:
        logger.error(f"❌ Error in update_template: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء تحديث النموذج'}), 500


@templates_bp.route('/admin/templates/<int:template_id>', methods=['DELETE'])
@login_required
@role_required(['admin'])
def delete_template(template_id):
    """
    حذف نموذج (تعطيله فقط، لا حذف نهائي)
    """
    try:
        success = TemplateModel.delete_template(template_id)
        
        if not success:
            return jsonify({'error': 'النموذج غير موجود'}), 404
        
        LogModel.create(request.user['user_id'], f'حذف نموذج {template_id}', request.remote_addr)
        
        return jsonify({'message': 'تم حذف النموذج بنجاح'}), 200
        
    except Exception as e:
        logger.error(f"❌ Error in delete_template: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء حذف النموذج'}), 500


@templates_bp.route('/admin/templates/<int:template_id>/toggle', methods=['POST'])
@login_required
@role_required(['admin'])
def toggle_template_status(template_id):
    """
    تفعيل أو تعطيل نموذج (بدون حذف)
    الجسم: {"is_active": true/false}
    """
    try:
        data = request.json
        is_active = data.get('is_active', True)
        
        success = TemplateModel.update_template(template_id, {'is_active': is_active})
        
        if not success:
            return jsonify({'error': 'النموذج غير موجود'}), 404
        
        status_text = 'تفعيل' if is_active else 'تعطيل'
        LogModel.create(request.user['user_id'], f'{status_text} نموذج {template_id}', request.remote_addr)
        
        return jsonify({'message': f'تم {status_text} النموذج بنجاح'}), 200
        
    except Exception as e:
        logger.error(f"❌ Error in toggle_template_status: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء تغيير حالة النموذج'}), 500


@templates_bp.route('/admin/templates/<int:template_id>/duplicate', methods=['POST'])
@login_required
@role_required(['admin'])
def duplicate_template(template_id):
    """
    نسخ نموذج موجود (لإنشاء نموذج مشابه)
    """
    try:
        existing_templates = TemplateModel.get_all(include_inactive=True)
        source = next((t for t in existing_templates if t['id'] == template_id), None)
        
        if not source:
            return jsonify({'error': 'النموذج غير موجود'}), 404
        
        # إنشاء نسخة
        new_name = f"{source['name']} (نسخة)"
        new_template = TemplateModel.create_template(
            name=new_name,
            description=source.get('description', ''),
            items=source.get('items', []),
            created_by=request.user['user_id']
        )
        
        LogModel.create(request.user['user_id'], f'نسخ نموذج {template_id} إلى {new_template["id"]}', request.remote_addr)
        
        return jsonify(new_template), 201
        
    except Exception as e:
        logger.error(f"❌ Error in duplicate_template: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء نسخ النموذج'}), 500