// =====================================================
// constants.dart - الثوابت العامة للتطبيق
// =====================================================

class Constants {
  // رابط API الأساسي (غيّره إلى رابط سيرفرك في الإنتاج)
 // static const String apiBaseUrl = 'http://localhost:5000/api';
  static const String apiBaseUrl = 'https://bin-obaid-system.onrender.com/api';
  // مفاتيح التخزين المحلي
  static const String tokenKey = 'jwt_token';
  static const String userKey = 'user_data';
  static const String cartKey = 'user_cart';
  
  // إصدار التطبيق الحالي
  static const String currentVersion = '1.0.0';
  
  // إعدادات الكاش للصور
  static const int cacheMaxAgeDays = 30;
  static const int cacheMaxObjects = 500;
  
  // إعدادات الكروسيل
  static const int carouselAutoPlayInterval = 4000; // 4 ثوانٍ
  
  // حدود التطبيق
  static const int maxCartItems = 100;
  static const int minSearchLength = 2;
}
