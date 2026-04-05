// =====================================================
// api_service.dart - دوال استدعاء API (GET/POST مع JWT)
// الإصدار 2.0 - شامل جميع دوال التطبيق
// =====================================================

import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'models/product.dart';
import 'utils/constants.dart';

class ApiService {
  // استخراج التوكن من التخزين المحلي
  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(Constants.tokenKey);
  }

  // إعداد رأس الطلب مع التوكن
  Future<Map<String, String>> _headers() async {
    final token = await _getToken();
    return {
      'Content-Type': 'application/json',
      if (token != null) 'Authorization': 'Bearer $token',
    };
  }

  // ===================== المصادقة =====================

  Future<Map<String, dynamic>> login(String email, String password) async {
    final url = Uri.parse('${Constants.apiBaseUrl}/auth/login');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'email': email, 'password': password}),
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(Constants.tokenKey, data['access_token']);
      await prefs.setString(Constants.userKey, json.encode(data['user']));
      return data;
    } else {
      throw Exception('فشل تسجيل الدخول');
    }
  }

  Future<Map<String, dynamic>> register(String email, String password, String fullName, {String role = 'customer'}) async {
    final url = Uri.parse('${Constants.apiBaseUrl}/auth/register');
    final response = await http.post(
      url,
      headers: {'Content-Type': 'application/json'},
      body: json.encode({
        'email': email,
        'password': password,
        'full_name': fullName,
        'role': role,
      }),
    );
    
    if (response.statusCode == 201) {
      return json.decode(response.body);
    } else {
      throw Exception('فشل التسجيل');
    }
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(Constants.tokenKey);
    await prefs.remove(Constants.userKey);
  }

  // ===================== المنتجات =====================

  Future<List<Product>> fetchProducts({int limit = 50, int offset = 0}) async {
    final url = Uri.parse('${Constants.apiBaseUrl}/products?limit=$limit&offset=$offset');
    final response = await http.get(url, headers: await _headers());
    
    if (response.statusCode == 200) {
      final Map<String, dynamic> data = json.decode(response.body);
      final List<dynamic> productsJson = data['products'];
      return productsJson.map((json) => Product.fromJson(json)).toList();
    } else {
      throw Exception('فشل تحميل المنتجات');
    }
  }

  Future<Product> fetchProductDetails(String sku) async {
    final url = Uri.parse('${Constants.apiBaseUrl}/products/$sku');
    final response = await http.get(url, headers: await _headers());
    
    if (response.statusCode == 200) {
      return Product.fromJson(json.decode(response.body));
    } else {
      throw Exception('فشل تحميل تفاصيل المنتج');
    }
  }

  Future<List<String>> fetchProductImages(String sku) async {
    final url = Uri.parse('${Constants.apiBaseUrl}/products/$sku/images');
    final response = await http.get(url, headers: await _headers());
    
    if (response.statusCode == 200) {
      final Map<String, dynamic> data = json.decode(response.body);
      return List<String>.from(data['images']);
    } else {
      return [];
    }
  }

  // ===================== السلة وعروض الأسعار =====================

  Future<List<Map<String, dynamic>>> getBulkSuggestions(List<Map<String, dynamic>> cartItems) async {
    final url = Uri.parse('${Constants.apiBaseUrl}/cart/suggestions');
    final response = await http.post(
      url,
      headers: await _headers(),
      body: json.encode({'items': cartItems}),
    );
    
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return List<Map<String, dynamic>>.from(data['suggestions']);
    }
    return [];
  }

  Future<bool> submitQuote(List<Map<String, dynamic>> items, {String notes = ''}) async {
    final url = Uri.parse('${Constants.apiBaseUrl}/quote/submit');
    final response = await http.post(
      url,
      headers: await _headers(),
      body: json.encode({'items': items, 'notes': notes}),
    );
    return response.statusCode == 201;
  }

  Future<List<Map<String, dynamic>>> fetchUserQuotes() async {
    final url = Uri.parse('${Constants.apiBaseUrl}/quotes');
    final response = await http.get(url, headers: await _headers());
    
    if (response.statusCode == 200) {
      return List<Map<String, dynamic>>.from(json.decode(response.body));
    }
    return [];
  }

  // ===================== النماذج =====================

  Future<List<Map<String, dynamic>>> fetchTemplates() async {
    final url = Uri.parse('${Constants.apiBaseUrl}/templates');
    final response = await http.get(url, headers: await _headers());
    
    if (response.statusCode == 200) {
      return List<Map<String, dynamic>>.from(json.decode(response.body));
    }
    return [];
  }

  Future<Map<String, dynamic>> applyTemplate(int templateId) async {
    final url = Uri.parse('${Constants.apiBaseUrl}/templates/$templateId/apply');
    final response = await http.post(url, headers: await _headers());
    
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    throw Exception('فشل تطبيق النموذج');
  }

  // ===================== الإعلانات =====================

  Future<List<Map<String, dynamic>>> fetchPromotions() async {
    final url = Uri.parse('${Constants.apiBaseUrl}/promotions');
    final response = await http.get(url, headers: await _headers());
    
    if (response.statusCode == 200) {
      return List<Map<String, dynamic>>.from(json.decode(response.body));
    }
    return [];
  }

  Future<void> trackPromotionClick(int promoId) async {
    final url = Uri.parse('${Constants.apiBaseUrl}/promotions/$promoId/click');
    await http.post(url, headers: await _headers());
  }

  // ===================== التحديث التلقائي =====================

  Future<Map<String, dynamic>> getLatestVersion() async {
    final url = Uri.parse('${Constants.apiBaseUrl}/version');
    final response = await http.get(url);
    
    if (response.statusCode == 200) {
      return json.decode(response.body);
    }
    return {'version': Constants.currentVersion, 'update_available': false};
  }

  Future<void> registerFCMToken(String token) async {
    final url = Uri.parse('${Constants.apiBaseUrl}/register-fcm');
    await http.post(
      url,
      headers: await _headers(),
      body: json.encode({'token': token}),
    );
  }
}