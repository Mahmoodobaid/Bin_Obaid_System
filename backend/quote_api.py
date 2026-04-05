# =====================================================
# quote_api.py - إدارة السلة وعروض الأسعار والإيحاءات الذكية
# الإصدار 2.0 - مع دعم الإيحاءات وتتبع الطلبات
# =====================================================

import logging
from flask import Blueprint, request, jsonify
from decorators import login_required
from models import ProductModel, QuoteModel, SettingsModel
from bulk_suggestion import get_bulk_suggestions

logger = logging.getLogger(__name__)
quote_bp = Blueprint('quote', __name__)


# ===================== الإيحاءات الذكية =====================

@quote_bp.route('/cart/suggestions', methods=['POST'])
@login_required
def get_cart_suggestions():
    """
    إرجاع إيحاءات للمنتجات ذات الكمية الكبيرة بناءً على محتويات السلة.
    
    الجسم: {"items": [{"sku": "OB-001", "quantity": 5}, ...]}
    """
    try:
        data = request.json
        cart_items = data.get('items', [])
        
        if not cart_items:
            return jsonify({'suggestions': []}), 200
        
        suggestions = get_bulk_suggestions(cart_items)
        return jsonify({'suggestions': suggestions}), 200
        
    except Exception as e:
        logger.error(f"❌ Error in get_cart_suggestions: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء جلب الإيحاءات'}), 500


# ===================== إدارة عروض الأسعار =====================

@quote_bp.route('/quote/submit', methods=['POST'])
@login_required
def submit_quote():
    """
    إرسال عرض سعر نهائي.
    
    الجسم: {
        "items": [
            {"sku": "OB-001", "quantity": 10, "unit_price": 15.5},
            ...
        ],
        "notes": "ملاحظات اختيارية"
    }
    """
    try:
        data = request.json
        user_id = request.user['user_id']
        items = data.get('items', [])
        notes = data.get('notes', '')
        
        if not items:
            return jsonify({'error': 'السلة فارغة'}), 400
        
        # التحقق من صحة العناصر وحساب الإجمالي
        total = 0
        validated_items = []
        
        for item in items:
            sku = item.get('sku')
            quantity = item.get('quantity', 0)
            unit_price = item.get('unit_price', 0)
            
            if not sku or quantity <= 0 or unit_price <= 0:
                continue
            
            # التحقق من وجود المنتج
            product = ProductModel.get_by_sku(sku)
            if not product:
                logger.warning(f"Product {sku} not found in quote submission")
                continue
            
            # التحقق من توفر الكمية المطلوبة
            stock = product.get('quantity_in_stock', 0)
            if quantity > stock:
                return jsonify({
                    'error': f'الكمية المطلوبة للمنتج {product["name"]} ({quantity}) تتجاوز المخزون المتوفر ({stock})'
                }), 400
            
            item_total = quantity * unit_price
            total += item_total
            
            validated_items.append({
                'sku': sku,
                'quantity': quantity,
                'unit_price': unit_price,
                'total_price': item_total
            })
        
        if not validated_items:
            return jsonify({'error': 'لا توجد عناصر صالحة في السلة'}), 400
        
        # إنشاء عرض السعر
        quote = QuoteModel.create_quote(user_id, total)
        if not quote:
            return jsonify({'error': 'فشل إنشاء عرض السعر'}), 500
        
        # إضافة العناصر
        for item in validated_items:
            QuoteModel.add_quote_item(
                quote['id'], 
                item['sku'], 
                item['quantity'], 
                item['unit_price']
            )
        
        # تسجيل الحدث
        from models import LogModel
        LogModel.create(user_id, f'إنشاء عرض سعر #{quote["id"]} - {len(validated_items)} منتج', request.remote_addr)
        
        # (اختياري) تقليل المخزون؟ حسب سياسة العمل
        # يمكن تفعيلها لاحقاً
        
        return jsonify({
            'message': 'تم إرسال عرض السعر بنجاح',
            'quote_id': quote['id'],
            'total_amount': total,
            'items_count': len(validated_items)
        }), 201
        
    except Exception as e:
        logger.error(f"❌ Error in submit_quote: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء إرسال عرض السعر'}), 500


@quote_bp.route('/quotes', methods=['GET'])
@login_required
def get_user_quotes():
    """
    استرجاع عروض الأسعار السابقة للمستخدم الحالي
    """
    try:
        user_id = request.user['user_id']
        quotes = QuoteModel.get_quotes_by_user(user_id)
        
        # إضافة اسم المنتج لكل عنصر (اختياري للعرض)
        for quote in quotes:
            for item in quote.get('quote_items', []):
                product = ProductModel.get_by_sku(item['product_sku'])
                item['product_name'] = product['name'] if product else item['product_sku']
        
        return jsonify(quotes), 200
        
    except Exception as e:
        logger.error(f"❌ Error in get_user_quotes: {str(e)}")
        return jsonify({'error': 'حدث خطأ أثناء جلب العروض'}), 500


@quote_bp.route('/quotes/<int:quote_id>', methods=['GET'])
@login_required
def get_quote_details(quote_id):
    """
    استرجاع تفاصيل عرض سعر محدد
    """
    try:
        user_id = request.user['user_id']
        from supabase import create_client
        from config import Config
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        result = supabase.table('quotes').select('*, quote_items(*)').eq('id', quote_id).eq('user_id', user_id).execute()
        
        if not result.data:
            return jsonify({'error': 'عرض السعر غير موجود'}), 404
        
        quote = result.data[0]
        
        # إضافة أسماء المنتجات
        for item in quote.get('quote_items', []):
            product = ProductModel.get_by_sku(item['product_sku'])
            item['product_name'] = product['name'] if product else item['product_sku']
        
        return jsonify(quote), 200
        
    except Exception as e:
        logger.error(f"❌ Error in get_quote_details: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500


# ===================== إدارة حالة عروض الأسعار (للمستخدم) =====================

@quote_bp.route('/quotes/<int:quote_id>/cancel', methods=['POST'])
@login_required
def cancel_quote(quote_id):
    """
    إلغاء عرض سعر (للمستخدم فقط إذا كان pending)
    """
    try:
        user_id = request.user['user_id']
        
        # التحقق من ملكية عرض السعر
        quotes = QuoteModel.get_quotes_by_user(user_id)
        quote = next((q for q in quotes if q['id'] == quote_id), None)
        
        if not quote:
            return jsonify({'error': 'عرض السعر غير موجود'}), 404
        
        if quote['status'] != 'pending':
            return jsonify({'error': 'لا يمكن إلغاء عرض سعر تمت معالجته بالفعل'}), 400
        
        success = QuoteModel.update_status(quote_id, 'cancelled')
        
        if success:
            from models import LogModel
            LogModel.create(user_id, f'إلغاء عرض السعر #{quote_id}', request.remote_addr)
            return jsonify({'message': 'تم إلغاء عرض السعر بنجاح'}), 200
        
        return jsonify({'error': 'فشل إلغاء عرض السعر'}), 500
        
    except Exception as e:
        logger.error(f"❌ Error in cancel_quote: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500


# ===================== إحصائيات سريعة للمستخدم =====================

@quote_bp.route('/quotes/stats', methods=['GET'])
@login_required
def get_user_quote_stats():
    """
    إحصائيات عروض الأسعار للمستخدم الحالي
    """
    try:
        user_id = request.user['user_id']
        quotes = QuoteModel.get_quotes_by_user(user_id)
        
        total_quotes = len(quotes)
        pending = sum(1 for q in quotes if q['status'] == 'pending')
        approved = sum(1 for q in quotes if q['status'] == 'approved')
        rejected = sum(1 for q in quotes if q['status'] == 'rejected')
        cancelled = sum(1 for q in quotes if q['status'] == 'cancelled')
        
        total_spent = sum(float(q.get('total_amount', 0)) for q in quotes if q['status'] == 'approved')
        
        return jsonify({
            'total_quotes': total_quotes,
            'pending': pending,
            'approved': approved,
            'rejected': rejected,
            'cancelled': cancelled,
            'total_spent': round(total_spent, 2)
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error in get_user_quote_stats: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500


# ===================== إعادة استخدام عرض سعر سابق =====================

@quote_bp.route('/quotes/<int:quote_id>/reorder', methods=['POST'])
@login_required
def reorder_quote(quote_id):
    """
    إعادة طلب نفس منتجات عرض سعر سابق (نسخ إلى سلة جديدة)
    """
    try:
        user_id = request.user['user_id']
        
        # التحقق من ملكية عرض السعر
        quotes = QuoteModel.get_quotes_by_user(user_id)
        quote = next((q for q in quotes if q['id'] == quote_id), None)
        
        if not quote:
            return jsonify({'error': 'عرض السعر غير موجود'}), 404
        
        # استخراج العناصر
        items = []
        for item in quote.get('quote_items', []):
            items.append({
                'sku': item['product_sku'],
                'quantity': item['quantity'],
                'unit_price': item['unit_price']
            })
        
        return jsonify({
            'message': 'تم استرجاع عناصر العرض السابق',
            'items': items,
            'original_quote_id': quote_id
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error in reorder_quote: {str(e)}")
        return jsonify({'error': 'حدث خطأ'}), 500