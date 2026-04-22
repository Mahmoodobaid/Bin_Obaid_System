# =====================================================
# decorators.py - ديكوراتورات المصادقة والصلاحيات
# الإصدار 2.0 - مع دعم الأدوار المتعددة والتحقق المتقدم
# =====================================================

from functools import wraps
from flask import request, jsonify
import jwt
import os

JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')


def decode_token(token):
    """
    فك تشفير JWT والتحقق من صلاحيته.
    
    المعاملات:
        token: str - التوكن المراد فك تشفيره
    
    تعيد: dict - بيانات التوكن إذا كان صالحاً، None إذا كان غير صالح
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required(f):
    """
    ديكوراتور للتحقق من وجود توكن صالح في رأس الطلب.
    يضيف request.user وهو قاموس يحتوي على بيانات المستخدم من التوكن.
    
    الاستخدام:
        @app.route('/protected')
        @login_required
        def protected():
            user_id = request.user['user_id']
            return jsonify({'message': f'Hello user {user_id}'})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # التحقق من وجود التوكن في رأس Authorization
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'الرمز غير موجود. يرجى تسجيل الدخول'}), 401
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'تنسيق الرمز غير صحيح. يجب أن يبدأ بـ Bearer'}), 401
        
        token = auth_header.split(' ')[1]
        if not token:
            return jsonify({'error': 'الرمز فارغ'}), 401
        
        # فك تشفير التوكن
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'الرمز غير صالح أو منتهي الصلاحية. يرجى تسجيل الدخول مرة أخرى'}), 401
        
        # التحقق من نوع التوكن (يجب أن يكون access)
        if payload.get('type') != 'access':
            return jsonify({'error': 'نوع الرمز غير صالح'}), 401
        
        # إضافة بيانات المستخدم إلى الطلب
        request.user = payload
        return f(*args, **kwargs)
    
    return decorated


def role_required(allowed_roles):
    """
    ديكوراتور للتحقق من صلاحيات الدور (role).
    يجب أن يأتي بعد @login_required.
    
    المعاملات:
        allowed_roles: list - قائمة بالأدوار المسموح بها مثل ['admin', 'manager']
    
    الاستخدام:
        @app.route('/admin')
        @login_required
        @role_required(['admin'])
        def admin_panel():
            return jsonify({'message': 'مرحباً أيها المدير'})
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # التحقق من وجود بيانات المستخدم في الطلب
            if not hasattr(request, 'user') or not request.user:
                return jsonify({'error': 'غير مصرح به. يرجى تسجيل الدخول'}), 401
            
            user_role = request.user.get('role')
            if user_role not in allowed_roles:
                return jsonify({
                    'error': 'ليس لديك صلاحية للوصول إلى هذه الصفحة',
                    'required_roles': allowed_roles,
                    'your_role': user_role
                }), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    """
    ديكوراتور مختصر للتحقق من صلاحية المسؤول (ادمن).
    يعادل @role_required(['admin'])
    
    الاستخدام:
        @app.route('/admin')
        @login_required
        @admin_required
        def admin_panel():
            return jsonify({'message': 'مرحباً أيها المدير'})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'الرمز غير موجود'}), 401
        
        token = auth_header.split(' ')[1]
        payload = decode_token(token)
        
        if not payload:
            return jsonify({'error': 'الرمز غير صالح أو منتهي الصلاحية'}), 401
        
        if payload.get('role') != 'admin':
            return jsonify({'error': 'هذه الصفحة متاحة للمسؤولين فقط'}), 403
        
        request.user = payload
        return f(*args, **kwargs)
    
    return decorated


def optional_auth(f):
    """
    ديكوراتور للتحقق الاختياري (إن وجد توكن صالح يضيف user، وإلا يكمل بدون).
    مفيد لل endpoints التي تعرض بيانات عامة ولكن مع ميزات إضافية للمسجلين.
    
    الاستخدام:
        @app.route('/products')
        @optional_auth
        def products():
            if request.user:
                # عرض أسعار خاصة للمستخدمين المسجلين
                pass
            else:
                # عرض أسعار عامة
                pass
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        request.user = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            payload = decode_token(token)
            if payload and payload.get('type') == 'access':
                request.user = payload
        
        return f(*args, **kwargs)
    
    return decorated


def rate_limit(limit_per_minute=60):
    """
    ديكوراتور لتقييد عدد الطلبات لكل IP في الدقيقة.
    ملاحظة: هذا تطبيق بسيط في الذاكرة، للإنتاج يُفضل استخدام Redis.
    
    المعاملات:
        limit_per_minute: int - الحد الأقصى للطلبات في الدقيقة
    """
    # مخزن مؤقت بسيط للطلبات
    _requests_store = {}
    
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            client_ip = request.remote_addr
            now = __import__('time').time()
            window_start = now - 60
            
            # تنظيف الإدخالات القديمة
            for ip in list(_requests_store.keys()):
                _requests_store[ip] = [t for t in _requests_store[ip] if t > window_start]
            
            if client_ip not in _requests_store:
                _requests_store[client_ip] = []
            
            if len(_requests_store[client_ip]) >= limit_per_minute:
                return jsonify({'error': f'تم تجاوز الحد المسموح من الطلبات ({limit_per_minute} طلب في الدقيقة). حاول لاحقاً'}), 429
            
            _requests_store[client_ip].append(now)
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_permission(permission):
    """
    ديكوراتور للتحقق من صلاحية محددة (لمنظومات أكثر تعقيداً).
    
    المعاملات:
        permission: str - اسم الصلاحية المطلوبة مثل 'products.delete'
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            user_role = request.user.get('role')
            # تعريف صلاحيات الأدوار
            role_permissions = {
                'admin': ['*'],  # كل الصلاحيات
                'manager': ['products.view', 'products.edit', 'quotes.view'],
                'customer': ['products.view', 'quotes.create', 'quotes.view_own'],
                'delivery': ['quotes.view_assigned']
            }
            
            user_permissions = role_permissions.get(user_role, [])
            if permission not in user_permissions and '*' not in user_permissions:
                return jsonify({'error': f'ليس لديك صلاحية {permission}'}), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator