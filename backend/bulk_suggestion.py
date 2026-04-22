# =====================================================
# bulk_suggestion.py - إيحاءات ذكية للمنتجات ذات الكمية الكبيرة
# الإصدار 2.0 - مع دعم الإعدادات الديناميكية وتحليل المخزون
# =====================================================

import logging
from models import ProductModel, SettingsModel

logger = logging.getLogger(__name__)


def get_bulk_suggestions(cart_items):
    """
    تحليل عناصر السلة وإرجاع إيحاءات للمنتجات التي تتوفر بكميات كبيرة.
    
    cart_items: قائمة من القواميس كل منها يحتوي على:
        - sku: str (رمز المنتج)
        - quantity: int (الكمية المطلوبة)
    
    تعيد: قائمة من القواميس لكل منتج تجاوز العتبة، تحتوي على:
        - sku: str
        - product_name: str
        - current_quantity: int
        - suggested_extra: int (الكمية الإضافية المقترحة)
        - message: str (نص الإيحاء)
        - stock: int (الكمية المتوفرة في المخزون)
        - available_to_add: int (الكمية المتبقية التي يمكن إضافتها)
    """
    try:
        # قراءة الإعدادات من قاعدة البيانات
        threshold = SettingsModel.get_int('bulk_quantity_threshold', 100)
        message_template = SettingsModel.get('bulk_suggestion_message')
        
        if not message_template:
            message_template = "🛍️ متوفر بكمية كبيرة، اطلب كمية إضافية واحصل على خصم"

        suggestions = []
        
        for item in cart_items:
            sku = item.get('sku')
            quantity = item.get('quantity', 0)
            
            if not sku:
                continue

            # جلب بيانات المنتج من قاعدة البيانات
            product = ProductModel.get_by_sku(sku)
            if not product:
                continue

            stock = product.get('quantity_in_stock', 0)
            product_name = product.get('name', sku)
            
            # التحقق مما إذا كان المنتج يستحق إيحاء
            # الشرط: الطلب الحالي >= العتبة OR المخزون >= العتبة
            if quantity >= threshold or stock >= threshold:
                
                # حساب الكمية الإضافية المقترحة
                # نستخدم 10% من المخزون أو العتبة أيهما أقل
                suggested_extra = min(
                    threshold,
                    max(10, int(stock * 0.1))  # على الأقل 10 وحدات
                )
                
                # التأكد من عدم تجاوز المخزون المتاح
                available_to_add = stock - quantity
                if available_to_add <= 0:
                    continue  # لا يوجد مخزون إضافي للإيحاء
                
                # إذا كانت الكمية المقترحة أكبر من المتاح، نخفضها
                if suggested_extra > available_to_add:
                    suggested_extra = available_to_add
                
                # تخصيص الرسالة حسب الحالة
                custom_message = message_template
                if stock >= threshold * 2:
                    custom_message = "🔥 عرض خاص! كمية كبيرة جداً متوفرة، اطلب الآن واحصل على خصم إضافي"
                elif stock >= threshold:
                    custom_message = message_template
                
                suggestions.append({
                    'sku': sku,
                    'product_name': product_name,
                    'current_quantity': quantity,
                    'suggested_extra': suggested_extra,
                    'message': custom_message,
                    'stock': stock,
                    'available_to_add': available_to_add
                })
        
        logger.info(f"Generated {len(suggestions)} bulk suggestions")
        return suggestions
        
    except Exception as e:
        logger.error(f"Error in get_bulk_suggestions: {str(e)}")
        return []


def get_product_bulk_info(sku):
    """
    الحصول على معلومات الكمية الكبيرة لمنتج محدد.
    مفيد لعرض الإيحاءات في صفحة تفاصيل المنتج.
    
    تعيد: dict أو None
    """
    try:
        threshold = SettingsModel.get_int('bulk_quantity_threshold', 100)
        product = ProductModel.get_by_sku(sku)
        
        if not product:
            return None
        
        stock = product.get('quantity_in_stock', 0)
        
        if stock >= threshold:
            return {
                'sku': sku,
                'product_name': product.get('name', sku),
                'stock': stock,
                'is_bulk_available': True,
                'bulk_threshold': threshold,
                'suggested_bulk_quantity': min(threshold, max(10, int(stock * 0.1))),
                'message': f"متوفر {stock} وحدة في المخزون، اطلب كمية كبيرة واحصل على خصم"
            }
        else:
            return {
                'sku': sku,
                'product_name': product.get('name', sku),
                'stock': stock,
                'is_bulk_available': False,
                'bulk_threshold': threshold
            }
            
    except Exception as e:
        logger.error(f"Error in get_product_bulk_info: {str(e)}")
        return None


def get_all_bulk_products(min_stock=None):
    """
    جلب جميع المنتجات التي تتوفر بكميات كبيرة (للمسؤول).
    
    min_stock: الحد الأدنى للكمية (اختياري، يستخدم العتبة الافتراضية إذا لم يُحدد)
    
    تعيد: قائمة بالمنتجات التي تتوفر بكميات كبيرة
    """
    try:
        threshold = min_stock or SettingsModel.get_int('bulk_quantity_threshold', 100)
        products = ProductModel.get_all(limit=10000)
        
        bulk_products = []
        for product in products:
            stock = product.get('quantity_in_stock', 0)
            if stock >= threshold:
                bulk_products.append({
                    'sku': product.get('sku'),
                    'name': product.get('name'),
                    'quantity_in_stock': stock,
                    'unit_price': product.get('unit_price', 0),
                    'category': product.get('category', ''),
                    'bulk_threshold': threshold
                })
        
        # ترتيب حسب الكمية (الأكبر أولاً)
        bulk_products.sort(key=lambda x: x['quantity_in_stock'], reverse=True)
        
        logger.info(f"Found {len(bulk_products)} products with bulk quantity (threshold: {threshold})")
        return bulk_products
        
    except Exception as e:
        logger.error(f"Error in get_all_bulk_products: {str(e)}")
        return []