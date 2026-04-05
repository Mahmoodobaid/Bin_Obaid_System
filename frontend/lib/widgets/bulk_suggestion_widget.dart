// =====================================================
// bulk_suggestion_widget.dart - إيحاءات للمنتجات ذات الكمية الكبيرة
// =====================================================

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/cart_provider.dart';
import '../api_service.dart';

class BulkSuggestionWidget extends StatefulWidget {
  final List<Map<String, dynamic>> cartItems;

  const BulkSuggestionWidget({
    super.key,
    required this.cartItems,
  });

  @override
  State<BulkSuggestionWidget> createState() => _BulkSuggestionWidgetState();
}

class _BulkSuggestionWidgetState extends State<BulkSuggestionWidget> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _suggestions = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchSuggestions();
  }

  @override
  void didUpdateWidget(BulkSuggestionWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.cartItems.length != widget.cartItems.length) {
      _fetchSuggestions();
    }
  }

  Future<void> _fetchSuggestions() async {
    if (widget.cartItems.isEmpty) {
      setState(() {
        _suggestions = [];
        _isLoading = false;
      });
      return;
    }

    setState(() => _isLoading = true);
    
    try {
      final suggestions = await _api.getBulkSuggestions(widget.cartItems);
      setState(() {
        _suggestions = suggestions;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _suggestions = [];
        _isLoading = false;
      });
    }
  }

  void _addSuggestedQuantity(Map<String, dynamic> suggestion) {
    final cart = Provider.of<CartProvider>(context, listen: false);
    final sku = suggestion['sku'];
    final suggestedExtra = suggestion['suggested_extra'] ?? 0;
    
    // الحصول على الكمية الحالية
    final currentItem = widget.cartItems.firstWhere(
      (item) => item['sku'] == sku,
      orElse: () => {'quantity': 0},
    );
    final newQuantity = (currentItem['quantity'] as int) + suggestedExtra;
    
    cart.updateQuantity(sku, newQuantity);
    
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('تمت إضافة $suggestedExtra وحدة إضافية من ${suggestion['product_name']}'),
        backgroundColor: Colors.green,
        duration: const Duration(seconds: 2),
      ),
    );
    
    // تحديث الإيحاءات
    _fetchSuggestions();
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const SizedBox.shrink();
    }
    
    if (_suggestions.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      margin: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [Colors.orange.shade50, Colors.orange.shade100],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.orange.shade300),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // العنوان
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.orange.shade200,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
            ),
            child: const Row(
              children: [
                Icon(Icons.lightbulb, color: Colors.orange, size: 20),
                SizedBox(width: 8),
                Text(
                  'إيحاءات ذكية',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
          ),
          // قائمة الإيحاءات
          ListView.separated(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _suggestions.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final suggestion = _suggestions[index];
              return Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            suggestion['product_name'],
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            suggestion['message'],
                            style: TextStyle(
                              color: Colors.orange.shade800,
                              fontSize: 12,
                            ),
                          ),
                          Text(
                            'المتبقي في المخزون: ${suggestion['stock']} قطعة',
                            style: TextStyle(
                              color: Colors.grey.shade600,
                              fontSize: 10,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    ElevatedButton(
                      onPressed: () => _addSuggestedQuantity(suggestion),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.orange,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                        ),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 10,
                        ),
                      ),
                      child: Text('+ ${suggestion['suggested_extra']}'),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}