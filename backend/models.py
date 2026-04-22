# =====================================================
# models.py - دوال التعامل مع قاعدة البيانات (Supabase)
# الإصدار 2.0 - شامل جميع الجداول والعمليات الأساسية
# =====================================================

import logging
from datetime import datetime
from supabase import create_client
from config import Config

logger = logging.getLogger(__name__)
supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)


# ===================== فئة المستخدمين =====================

class UserModel:
    @staticmethod
    def get_by_email(email: str):
        result = supabase.table('users').select('*').eq('email', email.lower()).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_by_id(user_id: str):
        result = supabase.table('users').select('*').eq('id', user_id).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_all(role: str = None, limit: int = 100, offset: int = 0):
        query = supabase.table('users').select('*').range(offset, offset + limit - 1)
        if role:
            query = query.eq('role', role)
        result = query.execute()
        return result.data

    @staticmethod
    def count_all(role: str = None):
        query = supabase.table('users').select('*', count='exact')
        if role:
            query = query.eq('role', role)
        result = query.execute()
        return result.count

    @staticmethod
    def count_by_role(role: str):
        return UserModel.count_all(role)

    @staticmethod
    def update_role(user_id: str, new_role: str):
        result = supabase.table('users').update({'role': new_role}).eq('id', user_id).execute()
        return len(result.data) > 0

    @staticmethod
    def set_active(user_id: str, is_active: bool):
        result = supabase.table('users').update({'is_active': is_active}).eq('id', user_id).execute()
        return len(result.data) > 0

    @staticmethod
    def get_all_customers():
        result = supabase.table('users').select('id, email, full_name, fcm_token').eq('role', 'customer').execute()
        return result.data

    @staticmethod
    def create_user(user_data: dict):
        result = supabase.table('users').insert(user_data).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def update_user(user_id: str, updates: dict):
        result = supabase.table('users').update(updates).eq('id', user_id).execute()
        return len(result.data) > 0

    @staticmethod
    def delete_user(user_id: str):
        result = supabase.table('users').delete().eq('id', user_id).execute()
        return len(result.data) > 0


# ===================== فئة المنتجات =====================

class ProductModel:
    @staticmethod
    def create_or_update(product_data: dict):
        sku = product_data.get('sku')
        existing = supabase.table('products').select('sku').eq('sku', sku).execute()
        if existing.data:
            result = supabase.table('products').update(product_data).eq('sku', sku).execute()
        else:
            result = supabase.table('products').insert(product_data).execute()
        # إضافة إلى sync_queue
        supabase.table('sync_queue').insert({
            'entity_type': 'product',
            'entity_id': sku,
            'action': 'UPDATE' if existing.data else 'INSERT'
        }).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_by_sku(sku: str):
        result = supabase.table('products').select('*').eq('sku', sku).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def get_all(limit: int = 100, offset: int = 0, category: str = None, search: str = None):
        query = supabase.table('products').select('*').range(offset, offset + limit - 1)
        if category:
            query = query.eq('category', category)
        if search:
            query = query.ilike('name', f'%{search}%')
        result = query.order('name').execute()
        return result.data

    @staticmethod
    def count_all(category: str = None, search: str = None):
        query = supabase.table('products').select('*', count='exact')
        if category:
            query = query.eq('category', category)
        if search:
            query = query.ilike('name', f'%{search}%')
        result = query.execute()
        return result.count

    @staticmethod
    def update(sku: str, updates: dict):
        result = supabase.table('products').update(updates).eq('sku', sku).execute()
        if result.data:
            supabase.table('sync_queue').insert({
                'entity_type': 'product',
                'entity_id': sku,
                'action': 'UPDATE'
            }).execute()
            return True
        return False

    @staticmethod
    def delete(sku: str):
        result = supabase.table('products').delete().eq('sku', sku).execute()
        if result.data:
            supabase.table('sync_queue').insert({
                'entity_type': 'product',
                'entity_id': sku,
                'action': 'DELETE'
            }).execute()
            return True
        return False

    @staticmethod
    def get_categories():
        result = supabase.table('products').select('category').execute()
        categories = set()
        for p in result.data:
            if p.get('category'):
                categories.add(p['category'])
        return sorted(list(categories))


# ===================== فئة الصور =====================

class ImageModel:
    @staticmethod
    def add_images(product_sku: str, image_urls: list):
        for idx, url in enumerate(image_urls):
            supabase.table('product_images').insert({
                'product_sku': product_sku,
                'image_url': url,
                'display_order': idx
            }).execute()
        supabase.table('sync_queue').insert({
            'entity_type': 'image',
            'entity_id': product_sku,
            'action': 'INSERT'
        }).execute()

    @staticmethod
    def get_images(product_sku: str):
        result = supabase.table('product_images').select('image_url, display_order, id').eq('product_sku', product_sku).order('display_order').execute()
        return result.data

    @staticmethod
    def get_image_urls(product_sku: str):
        result = supabase.table('product_images').select('image_url').eq('product_sku', product_sku).order('display_order').execute()
        return [row['image_url'] for row in result.data]

    @staticmethod
    def delete_all_images(product_sku: str):
        # حذف من التخزين (يتم استدعاء supabase_storage.delete_image لكل صورة)
        images = ImageModel.get_image_urls(product_sku)
        from supabase_storage import delete_image
        for url in images:
            delete_image(url)
        supabase.table('product_images').delete().eq('product_sku', product_sku).execute()
        supabase.table('sync_queue').insert({
            'entity_type': 'image',
            'entity_id': product_sku,
            'action': 'DELETE'
        }).execute()

    @staticmethod
    def count_all():
        result = supabase.table('product_images').select('*', count='exact').execute()
        return result.count

    @staticmethod
    def count_products_with_images():
        result = supabase.table('product_images').select('product_sku').execute()
        unique_skus = set(row['product_sku'] for row in result.data)
        return len(unique_skus)

    @staticmethod
    def count_pending():
        result = supabase.table('pending_images').select('*', count='exact').eq('status', 'pending').execute()
        return result.count

    @staticmethod
    def add_pending_image(product_sku: str, image_url: str, submitted_by: str):
        supabase.table('pending_images').insert({
            'product_sku': product_sku,
            'image_url': image_url,
            'submitted_by': submitted_by,
            'status': 'pending'
        }).execute()

    @staticmethod
    def get_pending_images(product_sku: str = None):
        query = supabase.table('pending_images').select('*').eq('status', 'pending')
        if product_sku:
            query = query.eq('product_sku', product_sku)
        result = query.execute()
        return result.data

    @staticmethod
    def approve_image(image_id: int):
        result = supabase.table('pending_images').select('*').eq('id', image_id).execute()
        if not result.data:
            return False
        pending = result.data[0]
        supabase.table('product_images').insert({
            'product_sku': pending['product_sku'],
            'image_url': pending['image_url'],
            'display_order': 999
        }).execute()
        supabase.table('pending_images').update({'status': 'approved'}).eq('id', image_id).execute()
        return True

    @staticmethod
    def reject_image(image_id: int):
        result = supabase.table('pending_images').select('image_url').eq('id', image_id).execute()
        if result.data:
            from supabase_storage import delete_image
            delete_image(result.data[0]['image_url'])
        supabase.table('pending_images').delete().eq('id', image_id).execute()
        return True


# ===================== فئة عروض الأسعار =====================

class QuoteModel:
    @staticmethod
    def create_quote(user_id: str, total_amount: float):
        data = {
            'user_id': user_id,
            'total_amount': total_amount,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        }
        result = supabase.table('quotes').insert(data).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def add_quote_item(quote_id: int, product_sku: str, quantity: int, unit_price: float):
        data = {
            'quote_id': quote_id,
            'product_sku': product_sku,
            'quantity': quantity,
            'unit_price': unit_price
        }
        supabase.table('quote_items').insert(data).execute()

    @staticmethod
    def get_quotes_by_user(user_id: str):
        result = supabase.table('quotes').select('*, quote_items(*)').eq('user_id', user_id).order('created_at', desc=True).execute()
        return result.data

    @staticmethod
    def get_all(status: str = None, limit: int = 50, offset: int = 0):
        query = supabase.table('quotes').select('*, quote_items(*)').range(offset, offset + limit - 1)
        if status:
            query = query.eq('status', status)
        result = query.order('created_at', desc=True).execute()
        return result.data

    @staticmethod
    def count_all(status: str = None):
        query = supabase.table('quotes').select('*', count='exact')
        if status:
            query = query.eq('status', status)
        result = query.execute()
        return result.count

    @staticmethod
    def count_by_status(status: str):
        return QuoteModel.count_all(status)

    @staticmethod
    def count_created_since(since_date: datetime):
        result = supabase.table('quotes').select('*', count='exact').gte('created_at', since_date.isoformat()).execute()
        return result.count

    @staticmethod
    def get_recent(limit: int = 5):
        result = supabase.table('quotes').select('id, user_id, total_amount, status, created_at').order('created_at', desc=True).limit(limit).execute()
        return result.data

    @staticmethod
    def update_status(quote_id: int, new_status: str):
        result = supabase.table('quotes').update({'status': new_status}).eq('id', quote_id).execute()
        return len(result.data) > 0


# ===================== فئة النماذج =====================

class TemplateModel:
    @staticmethod
    def get_active_templates():
        result = supabase.table('quote_templates').select('*').eq('is_active', True).execute()
        return result.data

    @staticmethod
    def get_all(include_inactive: bool = False):
        query = supabase.table('quote_templates').select('*')
        if not include_inactive:
            query = query.eq('is_active', True)
        result = query.execute()
        return result.data

    @staticmethod
    def count_active():
        result = supabase.table('quote_templates').select('*', count='exact').eq('is_active', True).execute()
        return result.count

    @staticmethod
    def create_template(name: str, description: str, items: list, created_by: str):
        data = {
            'name': name,
            'description': description,
            'items': items,
            'created_by': created_by,
            'is_active': True
        }
        result = supabase.table('quote_templates').insert(data).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def update_template(template_id: int, updates: dict):
        result = supabase.table('quote_templates').update(updates).eq('id', template_id).execute()
        return len(result.data) > 0

    @staticmethod
    def delete_template(template_id: int):
        result = supabase.table('quote_templates').update({'is_active': False}).eq('id', template_id).execute()
        return len(result.data) > 0


# ===================== فئة الإعلانات =====================

class PromotionModel:
    @staticmethod
    def get_active():
        now = datetime.utcnow().isoformat()
        result = supabase.table('promotions').select('*').eq('is_active', True).lt('start_date', now).gt('end_date', now).execute()
        return result.data

    @staticmethod
    def get_all(include_inactive: bool = False):
        query = supabase.table('promotions').select('*')
        if not include_inactive:
            query = query.eq('is_active', True)
        result = query.order('created_at', desc=True).execute()
        return result.data

    @staticmethod
    def count_active():
        result = supabase.table('promotions').select('*', count='exact').eq('is_active', True).execute()
        return result.count

    @staticmethod
    def create(title: str, body: str, image_url: str, product_sku: str, start_date: str, end_date: str, created_by: str):
        data = {
            'title': title,
            'body': body,
            'image_url': image_url,
            'product_sku': product_sku,
            'start_date': start_date,
            'end_date': end_date,
            'created_by': created_by,
            'is_active': True
        }
        result = supabase.table('promotions').insert(data).execute()
        return result.data[0] if result.data else None

    @staticmethod
    def update(promo_id: int, updates: dict):
        result = supabase.table('promotions').update(updates).eq('id', promo_id).execute()
        return len(result.data) > 0

    @staticmethod
    def delete(promo_id: int):
        result = supabase.table('promotions').update({'is_active': False}).eq('id', promo_id).execute()
        return len(result.data) > 0

    @staticmethod
    def record_click(promo_id: int, user_id: str):
        supabase.table('promotion_clicks').insert({
            'promotion_id': promo_id,
            'user_id': user_id
        }).execute()

    @staticmethod
    def get_click_count(promo_id: int) -> int:
        result = supabase.table('promotion_clicks').select('*', count='exact').eq('promotion_id', promo_id).execute()
        return result.count


# ===================== فئة الإعدادات =====================

class SettingsModel:
    @staticmethod
    def get(key: str):
        result = supabase.table('settings').select('value').eq('key', key).execute()
        return result.data[0]['value'] if result.data else None

    @staticmethod
    def get_int(key: str, default: int = 0) -> int:
        val = SettingsModel.get(key)
        return int(val) if val else default

    @staticmethod
    def set(key: str, value: str):
        supabase.table('settings').upsert({'key': key, 'value': value}).execute()

    @staticmethod
    def get_all():
        result = supabase.table('settings').select('*').execute()
        return {row['key']: row['value'] for row in result.data}


# ===================== فئة السجلات =====================

class LogModel:
    @staticmethod
    def create(user_id: str, action: str, ip_address: str = None, user_agent: str = None):
        data = {
            'user_id': user_id,
            'action': action,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'created_at': datetime.utcnow().isoformat()
        }
        supabase.table('logs').insert(data).execute()

    @staticmethod
    def get_all(limit: int = 100, offset: int = 0, user_id: str = None, action_filter: str = None):
        query = supabase.table('logs').select('*').range(offset, offset + limit - 1)
        if user_id:
            query = query.eq('user_id', user_id)
        if action_filter:
            query = query.eq('action', action_filter)
        result = query.order('created_at', desc=True).execute()
        return result.data

    @staticmethod
    def count_all(user_id: str = None, action_filter: str = None):
        query = supabase.table('logs').select('*', count='exact')
        if user_id:
            query = query.eq('user_id', user_id)
        if action_filter:
            query = query.eq('action', action_filter)
        result = query.execute()
        return result.count