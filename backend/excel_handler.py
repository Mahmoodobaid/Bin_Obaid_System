# =====================================================
# excel_handler.py - معالجة ملفات Excel واستيراد المنتجات
# الإصدار 2.0 - مع دعم تنسيقات متعددة وتحسين الأداء
# =====================================================

import pandas as pd
import logging
from io import BytesIO
from models import ProductModel
from datetime import datetime
import re

logger = logging.getLogger(__name__)


def normalize_column_name(col_name):
    """
    تطبيع أسماء الأعمدة للتعرف عليها بغض النظر عن اللغة أو التنسيق.
    
    المعاملات:
        col_name: str - اسم العمود الأصلي
    
    تعيد: str - اسم العمود موحداً
    """
    if not col_name:
        return ""
    
    col_lower = str(col_name).lower().strip()
    
    # إزالة التشكيل والمسافات الزائدة
    col_lower = re.sub(r'[^\w\u0600-\u06FF]', '', col_lower)
    
    return col_lower


def detect_columns(df):
    """
    التعرف على أسماء الأعمدة المطلوبة بغض النظر عن التنسيق.
    
    المعاملات:
        df: DataFrame - البيانات المقروءة من Excel
    
    تعيد: dict - قاموس يحتوي على أسماء الأعمدة الفعلية
    """
    columns_map = {
        'sku': None,
        'name': None,
        'stock': None,
        'price': None,
        'description': None,
        'category': None
    }
    
    # قائمة بالكلمات المفتاحية لكل عمود (عربي/إنجليزي)
    keywords = {
        'sku': ['sku', 'code', 'كود', 'رمز', 'productcode', 'itemcode', 'الرقم'],
        'name': ['name', 'product', 'اسم', 'المنتج', 'productname', 'item', 'description'],
        'stock': ['stock', 'quantity', 'qty', 'كمية', 'المخزون', 'inventory', 'available'],
        'price': ['price', 'cost', 'سعر', 'التكلفة', 'unitprice', 'السعر'],
        'description': ['description', 'desc', 'وصف', 'details', 'ملاحظات', 'تفاصيل'],
        'category': ['category', 'cat', 'فئة', 'تصنيف', 'group', 'قسم']
    }
    
    for col in df.columns:
        col_norm = normalize_column_name(col)
        for field, keys in keywords.items():
            if columns_map[field] is None:
                for key in keys:
                    if key in col_norm or key in str(col).lower():
                        columns_map[field] = col
                        break
    
    return columns_map


def process_excel(file_storage, dry_run=False):
    """
    قراءة ملف Excel وتحديث/إدراج المنتجات في قاعدة البيانات.
    
    المعاملات:
        file_storage: FileStorage - ملف Excel المرفوع
        dry_run: bool - إذا كان True، يعيد التحليل فقط دون حفظ
    
    تعيد: dict - إحصائيات العملية
    """
    try:
        # محاولة قراءة الملف بتنسيقات مختلفة
        file_bytes = file_storage.read()
        
        # تجربة قراءة الملف
        try:
            df = pd.read_excel(BytesIO(file_bytes), engine='openpyxl')
        except:
            try:
                df = pd.read_excel(BytesIO(file_bytes), engine='xlrd')
            except:
                raise ValueError("لم نتمكن من قراءة الملف. تأكد من أنه بصيغة Excel صالحة (.xlsx أو .xls)")
        
        if df.empty:
            raise ValueError("الملف لا يحتوي على أي بيانات")
        
        # التعرف على الأعمدة
        columns = detect_columns(df)
        
        # التحقق من وجود الأعمدة الأساسية
        if not columns['sku']:
            raise ValueError("لم يتم العثور على عمود SKU أو الكود في الملف")
        if not columns['name']:
            raise ValueError("لم يتم العثور على عمود اسم المنتج")
        
        logger.info(f"Detected columns: SKU={columns['sku']}, Name={columns['name']}, "
                   f"Stock={columns['stock']}, Price={columns['price']}")
        
        products_updated = 0
        products_inserted = 0
        products_skipped = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # استخراج SKU
                sku = str(row[columns['sku']]).strip()
                if not sku or sku == 'nan' or sku == 'None':
                    products_skipped += 1
                    errors.append(f"الصف {index + 2}: SKU فارغ")
                    continue
                
                # استخراج الاسم
                name = str(row[columns['name']]).strip()
                if name == 'nan' or name == 'None':
                    name = sku
                
                # استخراج الكمية (إذا وجد العمود)
                quantity = 0
                if columns['stock'] and pd.notna(row[columns['stock']]):
                    try:
                        quantity = int(float(row[columns['stock']]))
                        if quantity < 0:
                            quantity = 0
                    except:
                        quantity = 0
                
                # استخراج السعر (إذا وجد العمود)
                price = 0.0
                if columns['price'] and pd.notna(row[columns['price']]):
                    try:
                        price = float(row[columns['price']])
                        if price < 0:
                            price = 0
                    except:
                        price = 0.0
                
                # استخراج الوصف (إذا وجد العمود)
                description = ''
                if columns['description'] and pd.notna(row[columns['description']]):
                    description = str(row[columns['description']])
                    if description == 'nan':
                        description = ''
                
                # استخراج الفئة (إذا وجد العمود)
                category = ''
                if columns['category'] and pd.notna(row[columns['category']]):
                    category = str(row[columns['category']])
                    if category == 'nan':
                        category = ''
                
                product_data = {
                    'sku': sku,
                    'name': name,
                    'description': description,
                    'category': category,
                    'quantity_in_stock': quantity,
                    'unit_price': price,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
                if dry_run:
                    continue
                
                # التحقق مما إذا كان المنتج موجوداً مسبقاً
                existing = ProductModel.get_by_sku(sku)
                if existing:
                    ProductModel.update(sku, product_data)
                    products_updated += 1
                else:
                    ProductModel.create_or_update(product_data)
                    products_inserted += 1
                    
            except Exception as row_error:
                products_skipped += 1
                errors.append(f"الصف {index + 2}: {str(row_error)}")
                logger.warning(f"Error in row {index}: {row_error}")
                continue
        
        result = {
            'inserted': products_inserted,
            'updated': products_updated,
            'skipped': products_skipped,
            'total': products_inserted + products_updated,
            'errors': errors[:10]  # أقصى 10 أخطاء
        }
        
        logger.info(f"Excel processed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Excel processing error: {str(e)}")
        raise ValueError(f"فشل معالجة ملف Excel: {str(e)}")


def export_products_to_excel():
    """
    تصدير جميع المنتجات إلى ملف Excel (بايتس) للتنزيل.
    
    تعيد: bytes - محتوى ملف Excel
    """
    try:
        products = ProductModel.get_all(limit=10000)
        
        if not products:
            raise ValueError("لا توجد منتجات للتصدير")
        
        # تحويل إلى DataFrame
        df = pd.DataFrame(products)
        
        # اختيار الأعمدة المناسبة وإعادة تسميتها
        column_mapping = {
            'sku': 'SKU',
            'name': 'اسم المنتج',
            'description': 'الوصف',
            'category': 'الفئة',
            'quantity_in_stock': 'الكمية المتوفرة',
            'unit_price': 'السعر',
            'last_updated': 'آخر تحديث'
        }
        
        existing_cols = [c for c in column_mapping.keys() if c in df.columns]
        df = df[existing_cols]
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in existing_cols})
        
        # إنشاء ملف Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='المنتجات', index=False)
            
            # تنسيق الأعمدة
            worksheet = writer.sheets['المنتجات']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        output.seek(0)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        raise ValueError(f"فشل تصدير المنتجات: {str(e)}")


def validate_excel_columns(file_storage):
    """
    التحقق من صحة أعمدة ملف Excel دون معالجته.
    
    المعاملات:
        file_storage: FileStorage - ملف Excel المرفوع
    
    تعيد: dict - معلومات عن الأعمدة المكتشفة
    """
    try:
        file_bytes = file_storage.read()
        df = pd.read_excel(BytesIO(file_bytes), engine='openpyxl', nrows=1)
        columns = detect_columns(df)
        
        return {
            'valid': columns['sku'] is not None and columns['name'] is not None,
            'detected_columns': {
                'sku': columns['sku'],
                'name': columns['name'],
                'stock': columns['stock'],
                'price': columns['price'],
                'description': columns['description'],
                'category': columns['category']
            },
            'available_columns': list(df.columns)
        }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }