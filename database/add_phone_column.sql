-- إضافة عمود رقم الهاتف إلى جدول المستخدمين
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT UNIQUE;

-- تحديث المستخدم الحالي (استبدل الرقم برقم هاتفك)
UPDATE users SET phone = '0096770491653' WHERE email = 'newadmin@example.com';

-- إضافة فهرس للبحث السريع
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
