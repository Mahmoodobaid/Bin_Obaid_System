// =====================================================
// apply_template_button.dart - زر تطبيق النموذج على السلة
// =====================================================

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api_service.dart';
import '../providers/cart_provider.dart';
import '../models/cart_item.dart';

class ApplyTemplateButton extends StatefulWidget {
  final int templateId;
  final String templateName;
  final VoidCallback? onSuccess;

  const ApplyTemplateButton({
    super.key,
    required this.templateId,
    required this.templateName,
    this.onSuccess,
  });

  @override
  State<ApplyTemplateButton> createState() => _ApplyTemplateButtonState();
}

class _ApplyTemplateButtonState extends State<ApplyTemplateButton> {
  final ApiService _api = ApiService();
  bool _isLoading = false;

  Future<void> _applyTemplate() async {
    setState(() => _isLoading = true);

    try {
      final result = await _api.applyTemplate(widget.templateId);
      final items = List<Map<String, dynamic>>.from(result['items']);
      
      final cart = Provider.of<CartProvider>(context, listen: false);
      
      int addedCount = 0;
      for (var item in items) {
        cart.addItem(CartItem(
          sku: item['sku'],
          name: item['name'] ?? item['sku'],
          quantity: item['quantity'],
          unitPrice: item['unit_price'] ?? 0,
        ));
        addedCount++;
      }
      
      if (!mounted) return;
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('تمت إضافة $addedCount صنف إلى السلة'),
          backgroundColor: Colors.green,
          duration: const Duration(seconds: 2),
          action: SnackBarAction(
            label: 'عرض السلة',
            textColor: Colors.white,
            onPressed: () {
              Navigator.pushNamed(context, '/cart');
            },
          ),
        ),
      );
      
      widget.onSuccess?.call();
      
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('فشل تطبيق النموذج: ${e.toString()}'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return ElevatedButton.icon(
      onPressed: _isLoading ? null : _applyTemplate,
      icon: _isLoading
          ? const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Icon(Icons.add_shopping_cart),
      label: Text(_isLoading ? 'جاري التطبيق...' : 'تطبيق النموذج'),
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
    );
  }
}