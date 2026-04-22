# =====================================================
# utils.py - دوال مساعدة متنوعة (تشفير، تحقق، معالجة، توكن)
# الإصدار 2.0 - شامل جميع الدوال المساعدة للمشروع
# =====================================================

import bcrypt
import jwt
import uuid
import re
import hashlib
import random
import string
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from config import Config

# ===================== دوال التشفير والتحقق =====================

def hash_password(password: str) -> str:
    """
    تشفير كلمة المرور باستخدام bcrypt
    """
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """
    التحقق من صحة كلمة المرور مقابل التشفير
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_jwt(user_id: str, email: str, role: str) -> str:
    """
    إنشاء JWT (للتكامل مع الكود القديم)
    """
    payload = {
        'user_id': user_id,
        'email': email,
        'role': role,
        'type': 'access',
        'exp': datetime.utcnow() + timedelta(hours=Config.JWT_ACCESS_EXPIRES_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')

def generate_refresh_token(user_id: str) -> tuple:
    """
    إنشاء refresh token عشوائي طويل الصلاحية
    تعيد: (token, expires_at)
    """
    token = uuid.uuid4().hex + uuid.uuid4().hex
    expires_at = datetime.utcnow() + timedelta(days=Config.JWT_REFRESH_EXPIRES_DAYS)
    return token, expires_at

def decode_jwt(token: str) -> dict:
    """
    فك تشفير JWT والتحقق من صلاحيته
    """
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def get_current_user_from_token(token: str) -> dict:
    """
    استخراج بيانات المستخدم من التوكن
    """
    payload = decode_jwt(token)
    if not payload or payload.get('type') != 'access':
        return None
    return payload

def verify_token(token: str) -> bool:
    """
    التحقق من صحة access token
    """
    payload = decode_jwt(token)
    return payload is not None and payload.get('type') == 'access'

# ===================== دوال التحقق من الصيغ =====================

def is_valid_email(email: str) -> bool:
    """
    التحقق من صحة البريد الإلكتروني
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

def is_valid_password(password: str) -> bool:
    """
    التحقق من قوة كلمة المرور:
    - 8 أحرف على الأقل
    - حرف كبير واحد على الأقل
    - رقم واحد على الأقل
    """
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

def is_valid_uuid(uuid_string: str) -> bool:
    """
    التحقق من صحة UUID
    """
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        return False

def is_valid_sku(sku: str) -> bool:
    """
    التحقق من صحة SKU (حروف وأرقام وشرطة وعلامة تحت)
    """
    return bool(re.match(r'^[A-Za-z0-9\-_]+$', sku))

def is_valid_phone(phone: str) -> bool:
    """
    التحقق من صحة رقم الهاتف (يمني أو دولي)
    """
    # يدعم: 777123456, 01 234567, +967777123456
    pattern = r'^(\+967|0)?[1-9][0-9]{8}$'
    return bool(re.match(pattern, phone.strip()))

# ===================== دوال معالجة النصوص والروابط =====================

def slugify(text: str) -> str:
    """
    تحويل النص إلى slug صالح للروابط
    مثال: "مرحباً في اليمن" -> "مرحبا-في-اليمن"
    """
    # إزالة التشكيل (اختياري)
    text = re.sub(r'[^\w\s-]', '', text)
    text = text.lower().strip()
    text = re.sub(r'[-\s]+', '-', text)
    return text

def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """
    قص النص مع إضافة ... إذا تجاوز الطول
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix

def generate_unique_filename(original_filename: str) -> str:
    """
    إنشاء اسم ملف فريد مع الاحتفاظ بالامتداد
    """
    ext = original_filename.split('.')[-1] if '.' in original_filename else 'jpg'
    return f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"

def generate_random_code(length: int = 6) -> str:
    """
    إنشاء رمز عشوائي مكون من أرقام وحروف
    """
    characters = string.digits + string.ascii_uppercase
    return ''.join(random.choices(characters, k=length))

# ===================== دوال التنسيق =====================

def format_price(price: float) -> str:
    """
    تنسيق السعر بعملة ريال
    """
    return f"{price:,.2f} ريال"

def format_date(date_str: str, format: str = '%Y-%m-%d %H:%M') -> str:
    """
    تنسيق التاريخ
    """
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime(format)
    except:
        return date_str

def safe_get(dictionary: dict, key: str, default=None):
    """
    استخراج قيمة بأمان من القاموس
    """
    return dictionary.get(key, default)

def merge_dicts(dict1: dict, dict2: dict) -> dict:
    """
    دمج قاموسين (المفتاح في dict2 يلغي dict1)
    """
    result = dict1.copy()
    result.update(dict2)
    return result

# ===================== دوال معالجة الطلبات (Request) =====================

def get_client_ip() -> str:
    """
    استخراج IP العميل من request (مع دعم الـ proxy)
    """
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr

def get_user_agent() -> str:
    """
    استخراج User-Agent من الطلب
    """
    return request.headers.get('User-Agent', 'Unknown')

# ===================== دوال إنشاء المعرفات الفريدة =====================

def generate_id(prefix: str = '') -> str:
    """
    إنشاء معرف فريد (مع بادئة اختيارية)
    مثال: generate_id('USER') -> 'USER_a1b2c3d4'
    """
    unique = uuid.uuid4().hex[:8]
    return f"{prefix}_{unique}" if prefix else unique

def generate_order_number() -> str:
    """
    إنشاء رقم طلب فريد (للطلبات الداخلية)
    """
    now = datetime.now()
    return f"ORD{now.strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"

# ===================== دوال مساعدة للـ Decorators =====================

def rate_limit_store():
    """
    متجر بسيط لتخزين محاولات الطلبات (يستخدم مع الـ rate limiting)
    """
    from collections import defaultdict
    return defaultdict(list)