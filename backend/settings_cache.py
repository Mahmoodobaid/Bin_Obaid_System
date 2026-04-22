# =====================================================
# settings_cache.py - تخزين مؤقت للإعدادات لتقليل استعلامات DB
# الإصدار 2.0 - مع دعم التحديث التلقائي وانتهاء الصلاحية
# =====================================================

import time
import threading
from models import SettingsModel

class SettingsCache:
    """
    تخزين مؤقت للإعدادات في الذاكرة لتقليل عدد الاستعلامات إلى قاعدة البيانات.
    يدعم انتهاء الصلاحية التلقائي والتحديث اليدوي.
    """
    
    _cache = {}
    _cache_timestamps = {}
    _default_ttl = 300  # 5 دقائق افتراضياً
    _lock = threading.Lock()
    
    @classmethod
    def get(cls, key, default=None, ttl=None):
        """
        استرجاع قيمة إعداد من الكاش أو من قاعدة البيانات.
        
        المعاملات:
            key: str - مفتاح الإعداد
            default: any - القيمة الافتراضية إذا لم يوجد
            ttl: int - مدة الصلاحية بالثواني (اختياري)
        
        تعيد: str - قيمة الإعداد أو القيمة الافتراضية
        """
        ttl = ttl or cls._default_ttl
        
        with cls._lock:
            # التحقق من وجود الإعداد في الكاش وصلاحيته
            if key in cls._cache and key in cls._cache_timestamps:
                if time.time() - cls._cache_timestamps[key] < ttl:
                    return cls._cache[key]
            
            # جلب من قاعدة البيانات
            try:
                value = SettingsModel.get(key)
                if value is not None:
                    cls._cache[key] = value
                    cls._cache_timestamps[key] = time.time()
                    return value
                else:
                    cls._cache[key] = default
                    cls._cache_timestamps[key] = time.time()
                    return default
            except Exception as e:
                # في حالة خطأ قاعدة البيانات، نستخدم القيمة المخزنة مؤقتاً إن وجدت
                if key in cls._cache:
                    return cls._cache[key]
                return default
    
    @classmethod
    def get_int(cls, key, default=0, ttl=None):
        """استرجاع إعداد كرقم صحيح"""
        value = cls.get(key, str(default), ttl)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    @classmethod
    def get_float(cls, key, default=0.0, ttl=None):
        """استرجاع إعداد كرقم عشري"""
        value = cls.get(key, str(default), ttl)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @classmethod
    def get_bool(cls, key, default=False, ttl=None):
        """استرجاع إعداد كقيمة منطقية"""
        value = cls.get(key, str(default), ttl)
        if isinstance(value, bool):
            return value
        return str(value).lower() in ('true', '1', 'yes', 'on')
    
    @classmethod
    def set(cls, key, value):
        """
        تحديث إعداد في قاعدة البيانات وفي الكاش.
        
        المعاملات:
            key: str - مفتاح الإعداد
            value: str - القيمة الجديدة
        """
        with cls._lock:
            # تحديث في قاعدة البيانات
            SettingsModel.set(key, str(value))
            # تحديث في الكاش
            cls._cache[key] = str(value)
            cls._cache_timestamps[key] = time.time()
    
    @classmethod
    def refresh(cls, key=None):
        """
        تحديث الكاش لقيمة محددة أو كل القيم.
        
        المعاملات:
            key: str - مفتاح الإعداد المطلوب تحديثه (اختياري، None لتحديث الكل)
        """
        with cls._lock:
            if key:
                # حذف مفتاح محدد
                cls._cache.pop(key, None)
                cls._cache_timestamps.pop(key, None)
            else:
                # حذف الكل
                cls._cache.clear()
                cls._cache_timestamps.clear()
    
    @classmethod
    def get_all(cls, ttl=None):
        """
        استرجاع جميع الإعدادات (كامل القاموس).
        """
        try:
            # جلب جميع الإعدادات من قاعدة البيانات
            all_settings = SettingsModel.get_all()
            
            # تحديث الكاش
            with cls._lock:
                for key, value in all_settings.items():
                    cls._cache[key] = value
                    cls._cache_timestamps[key] = time.time()
            
            return all_settings
        except Exception as e:
            # في حالة الخطأ، نعيد ما في الكاش
            with cls._lock:
                return cls._cache.copy()
    
    @classmethod
    def invalidate_all(cls):
        """مسح الكاش بالكامل (إجبار على إعادة التحميل)"""
        with cls._lock:
            cls._cache.clear()
            cls._cache_timestamps.clear()


# ===================== دوال مساعدة للاستخدام المباشر =====================

def get_setting(key, default=None):
    """دالة مساعدة للوصول السريع للإعدادات"""
    return SettingsCache.get(key, default)


def get_int_setting(key, default=0):
    """دالة مساعدة للوصول السريع للإعدادات الرقمية"""
    return SettingsCache.get_int(key, default)


def update_setting(key, value):
    """دالة مساعدة لتحديث إعداد"""
    SettingsCache.set(key, value)


def refresh_settings(key=None):
    """دالة مساعدة لتحديث الكاش"""
    SettingsCache.refresh(key)