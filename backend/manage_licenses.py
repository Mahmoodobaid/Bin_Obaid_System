#!/usr/bin/env python3
"""
إدارة مفاتيح الترخيص - أضف أو أزل مستخدمين
"""

import hashlib
import secrets
from datetime import datetime, timedelta

def generate_license(email, days=365):
    """إنشاء مفتاح ترخيص لمستخدم"""
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    unique = f"{email}-{secrets.token_hex(16)}-{expiry}"
    license_key = hashlib.sha256(unique.encode()).hexdigest()
    return license_key, expiry

def main():
    print("=" * 50)
    print("🔑 إدارة مفاتيح الترخيص - بن عبيد")
    print("=" * 50)
    
    email = input("📧 البريد الإلكتروني للمستخدم: ").strip()
    days = input("📅 عدد أيام الصلاحية (افتراضي 365): ").strip()
    days = int(days) if days else 365
    
    license_key, expiry = generate_license(email, days)
    
    print("\n" + "=" * 50)
    print("✅ تم إنشاء المفتاح بنجاح!")
    print(f"👤 المستخدم: {email}")
    print(f"🔑 المفتاح: {license_key}")
    print(f"📅 ينتهي في: {expiry}")
    print("=" * 50)
    print("\n📝 أرسل هذا المفتاح للمستخدم ليتمكن من استخدام التطبيق")

if __name__ == "__main__":
    main()
