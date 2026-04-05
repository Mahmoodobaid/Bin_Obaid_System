-- =====================================================
-- منظومة بن عبيد لإدارة المخازن وعروض الأسعار
-- إنشاء جميع الجداول (نسخة متوافقة مع Supabase)
-- الإصدار 2.0
-- =====================================================

-- =====================================================
-- 1. جدول المستخدمين (users)
-- =====================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'customer' CHECK (role IN ('admin', 'customer', 'delivery')),
    can_view_prices BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    fcm_token TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- =====================================================
-- 2. جدول المنتجات (products)
-- =====================================================
CREATE TABLE IF NOT EXISTS products (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    quantity_in_stock INTEGER DEFAULT 0,
    unit_price DECIMAL(10,2),
    last_updated TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 3. جدول صور المنتجات (product_images)
-- =====================================================
CREATE TABLE IF NOT EXISTS product_images (
    id SERIAL PRIMARY KEY,
    product_sku TEXT REFERENCES products(sku) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 4. جدول الإعدادات العامة (settings)
-- =====================================================
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT
);

-- إدراج الإعدادات الافتراضية
INSERT INTO settings (key, value, description) VALUES
('max_images_per_product', '4', 'الحد الأقصى لعدد الصور لكل منتج'),
('carousel_interval', '4000', 'الوقت بين تغيير الصور تلقائياً (مللي ثانية)'),
('bulk_quantity_threshold', '100', 'الكمية التي تعتبر "كبيرة" ويتم الإيحاء بها'),
('bulk_suggestion_message', 'متوفر بكمية كبيرة، اطلب كمية إضافية واحصل على خصم', 'نص الإيحاء'),
('company_name', 'بن عبيد للتجارة', 'اسم الشركة'),
('company_logo', '', 'شعار الشركة'),
('contact_phone', '', 'رقم هاتف التواصل'),
('contact_email', '', 'بريد التواصل')
ON CONFLICT (key) DO NOTHING;

-- =====================================================
-- 5. جدول سجل المزامنة (sync_queue)
-- =====================================================
CREATE TABLE IF NOT EXISTS sync_queue (
    id SERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    synced BOOLEAN DEFAULT FALSE
);

-- =====================================================
-- 6. جدول سجل النشاطات (logs)
-- =====================================================
CREATE TABLE IF NOT EXISTS logs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 7. جداول عروض الأسعار
-- =====================================================
CREATE TABLE IF NOT EXISTS quotes (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'sent', 'cancelled')),
    total_amount DECIMAL(10,2) DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS quote_items (
    id SERIAL PRIMARY KEY,
    quote_id INTEGER REFERENCES quotes(id) ON DELETE CASCADE,
    product_sku TEXT REFERENCES products(sku),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

-- =====================================================
-- 8. جداول الإعلانات والترويج
-- =====================================================
CREATE TABLE IF NOT EXISTS promotions (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT,
    image_url TEXT,
    product_sku TEXT REFERENCES products(sku),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS promotion_clicks (
    id SERIAL PRIMARY KEY,
    promotion_id INTEGER REFERENCES promotions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    clicked_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 9. جدول نماذج الطلبات السريعة
-- =====================================================
CREATE TABLE IF NOT EXISTS quote_templates (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    items JSONB NOT NULL,
    created_by UUID REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 10. جدول أجهزة المستخدمين لـ FCM
-- =====================================================
CREATE TABLE IF NOT EXISTS user_devices (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    fcm_token TEXT UNIQUE NOT NULL,
    device_info TEXT,
    last_active TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 11. جدول refresh tokens
-- =====================================================
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 12. جدول password_resets
-- =====================================================
CREATE TABLE IF NOT EXISTS password_resets (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- 13. جدول الصور المعلقة (pending_images)
-- =====================================================
CREATE TABLE IF NOT EXISTS pending_images (
    id SERIAL PRIMARY KEY,
    product_sku TEXT REFERENCES products(sku) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    submitted_by UUID REFERENCES users(id),
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- الفهارس (Indexes) لتحسين الأداء
-- =====================================================
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_product_images_product ON product_images(product_sku);
CREATE INDEX IF NOT EXISTS idx_quotes_user ON quotes(user_id);
CREATE INDEX IF NOT EXISTS idx_quotes_status ON quotes(status);
CREATE INDEX IF NOT EXISTS idx_quotes_created ON quotes(created_at);
CREATE INDEX IF NOT EXISTS idx_quote_items_quote ON quote_items(quote_id);
CREATE INDEX IF NOT EXISTS idx_promotions_active ON promotions(is_active, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id);
CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_token ON refresh_tokens(token);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_password_resets_token ON password_resets(token);
CREATE INDEX IF NOT EXISTS idx_pending_images_status ON pending_images(status);
CREATE INDEX IF NOT EXISTS idx_pending_images_product ON pending_images(product_sku);
CREATE INDEX IF NOT EXISTS idx_user_devices_token ON user_devices(fcm_token);
CREATE INDEX IF NOT EXISTS idx_sync_queue_synced ON sync_queue(synced);

-- =====================================================
-- تفعيل Row Level Security (RLS)
-- =====================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_images ENABLE ROW LEVEL SECURITY;
ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE promotions ENABLE ROW LEVEL SECURITY;
ALTER TABLE quote_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE pending_images ENABLE ROW LEVEL SECURITY;