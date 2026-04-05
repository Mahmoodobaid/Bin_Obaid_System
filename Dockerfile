# =====================================================
# Dockerfile - حاوية خادم Flask لمنظومة بن عبيد
# الإصدار 2.0 - مع تحسينات الأداء والأمان
# =====================================================

# استخدام صورة Python 3.10 الرسمية (خفيفة ومعتمدة)
FROM python:3.10-slim

# تعيين متغيرات البيئة
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    TZ=Asia/Aden

# تثبيت حزم النظام الأساسية (لـ Pillow ومكتبات الصور)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# إنشاء مجلد العمل داخل الحاوية
WORKDIR /app

# نسخ ملف المتطلبات أولاً (للاستفادة من التخزين المؤقت)
COPY requirements.txt .

# تثبيت تبعيات Python
RUN pip install --no-cache-dir -r requirements.txt

# نسخ جميع ملفات المشروع إلى الحاوية
COPY . .

# إنشاء مجلد للصور المؤقتة (إذا لزم الأمر)
RUN mkdir -p /app/temp_images && chmod 755 /app/temp_images

# تعيين مستخدم غير جذر للأمان (اختياري)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# تعريض المنفذ الذي يستخدمه التطبيق
EXPOSE 5000

# تحديد أمر التشغيل (استخدام Gunicorn للإنتاج)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "120", "wsgi:app"]