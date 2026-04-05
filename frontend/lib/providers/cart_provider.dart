// =====================================================
// cart_provider.dart - إدارة حالة سلة التسوق
// =====================================================

import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/cart_item.dart';
import '../utils/constants.dart';

class CartProvider with ChangeNotifier {
  List<CartItem> _items = [];

  CartProvider() {
    _loadCart();
  }

  List<CartItem> get items => _items;
  
  int get itemCount => _items.fold(0, (sum, item) => sum + item.quantity);
  
  double get totalAmount => _items.fold(0, (sum, item) => sum + item.totalPrice);

  Future<void> _saveCart() async {
    final prefs = await SharedPreferences.getInstance();
    final encoded = json.encode(_items.map((i) => i.toJson()).toList());
    await prefs.setString(Constants.cartKey, encoded);
  }

  Future<void> _loadCart() async {
    final prefs = await SharedPreferences.getInstance();
    final String? encoded = prefs.getString(Constants.cartKey);
    if (encoded != null) {
      final List<dynamic> decoded = json.decode(encoded);
      _items = decoded.map((e) => CartItem.fromJson(e)).toList();
      notifyListeners();
    }
  }

  void addItem(CartItem item) {
    final existingIndex = _items.indexWhere((i) => i.sku == item.sku);
    if (existingIndex != -1) {
      _items[existingIndex].quantity += item.quantity;
    } else {
      _items.add(item);
    }
    _saveCart();
    notifyListeners();
  }

  void updateQuantity(String sku, int newQuantity) {
    final index = _items.indexWhere((i) => i.sku == sku);
    if (index != -1) {
      if (newQuantity <= 0) {
        _items.removeAt(index);
      } else {
        _items[index].quantity = newQuantity;
      }
      _saveCart();
      notifyListeners();
    }
  }

  void removeItem(String sku) {
    _items.removeWhere((i) => i.sku == sku);
    _saveCart();
    notifyListeners();
  }

  void clearCart() {
    _items.clear();
    _saveCart();
    notifyListeners();
  }
}