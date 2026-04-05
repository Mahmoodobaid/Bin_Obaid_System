// =====================================================
// auth_provider.dart - إدارة حالة المصادقة
// =====================================================

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../api_service.dart';
import '../utils/constants.dart';

class AuthProvider with ChangeNotifier {
  final ApiService _api = ApiService();
  
  bool _isAuthenticated = false;
  String? _userEmail;
  String? _userName;
  String? _userRole;
  bool _isLoading = false;

  bool get isAuthenticated => _isAuthenticated;
  String? get userEmail => _userEmail;
  String? get userName => _userName;
  String? get userRole => _userRole;
  bool get isLoading => _isLoading;

  AuthProvider() {
    _loadUserFromStorage();
  }

  Future<void> _loadUserFromStorage() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(Constants.tokenKey);
    final userJson = prefs.getString(Constants.userKey);
    
    if (token != null && userJson != null) {
      final user = json.decode(userJson);
      _isAuthenticated = true;
      _userEmail = user['email'];
      _userName = user['full_name'];
      _userRole = user['role'];
      notifyListeners();
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    notifyListeners();
    
    try {
      final data = await _api.login(email, password);
      _isAuthenticated = true;
      _userEmail = data['user']['email'];
      _userName = data['user']['full_name'];
      _userRole = data['user']['role'];
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> register(String email, String password, String fullName) async {
    _isLoading = true;
    notifyListeners();
    
    try {
      await _api.register(email, password, fullName);
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    await _api.logout();
    _isAuthenticated = false;
    _userEmail = null;
    _userName = null;
    _userRole = null;
    notifyListeners();
  }

  bool get isAdmin => _userRole == 'admin';
}
  Future<bool> loginWithPhone(String phone, String password) async {
    _isLoading = true;
    notifyListeners();
    
    try {
      final response = await http.post(
        Uri.parse('${Constants.apiBaseUrl}/auth/login-with-phone'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'phone': phone, 'password': password}),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString(Constants.tokenKey, data['access_token']);
        await prefs.setString(Constants.userKey, json.encode(data['user']));
        _isAuthenticated = true;
        _userEmail = data['user']['email'];
        _userName = data['user']['full_name'];
        _userRole = data['user']['role'];
        _isLoading = false;
        notifyListeners();
        return true;
      } else {
        _isLoading = false;
        notifyListeners();
        return false;
      }
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }
