// =====================================================
// product_detail_screen.dart - شاشة عرض تفاصيل المنتج
// =====================================================

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/product.dart';
import '../models/cart_item.dart';
import '../providers/cart_provider.dart';
import '../widgets/gallery_carousel.dart';
import '../api_service.dart';

class ProductDetailScreen extends StatefulWidget {
  final Product product;
  const ProductDetailScreen({super.key, required this.product});

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  int _quantity = 1;
  bool _isLoading = false;
  late Future<List<String>> _imagesFuture;
  final ApiService _api = ApiService();

  @override
  void initState() {
    super.initState();
    _imagesFuture = _api.fetchProductImages(widget.product.sku);
  }

  void _addToCart() {
    final cart = Provider.of<CartProvider>(context, listen: false);
    final cartItem = CartItem(
      sku: widget.product.sku,
      name: widget.product.name,
      quantity: _quantity,
      unitPrice: widget.product.unitPrice,
      imageUrl: widget.product.firstImage,
    );
    cart.addItem(cartItem);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('تم إضافة ${_quantity} × ${widget.product.name} إلى السلة'),
        backgroundColor: Colors.green,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.product.name),
        centerTitle: true,
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // معرض الصور
            FutureBuilder<List<String>>(
              future: _imagesFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return Container(
                    height: 300,
                    color: Colors.grey.shade200,
                    child: const Center(child: CircularProgressIndicator()),
                  );
                }
                final images = snapshot.data ?? [];
                if (images.isEmpty) {
                  return Container(
                    height: 300,
                    color: Colors.grey.shade200,
                    child: const Icon(Icons.image_not_supported, size: 50),
                  );
                }
                return GalleryCarousel(imageUrls: images);
              },
            ),
            // معلومات المنتج
            Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // اسم المنتج
                  Text(
                    widget.product.name,
                    style: const TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  // السعر
                  Row(
                    children: [
                      Text(
                        '${widget.product.unitPrice.toStringAsFixed(2)} ريال',
                        style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: Colors.green,
                        ),
                      ),
                      const SizedBox(width: 8),
                      if (widget.product.quantityInStock < 10)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.orange.shade100,
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            'المتبقي: ${widget.product.quantityInStock}',
                            style: TextStyle(
                              color: Colors.orange.shade800,
                              fontSize: 12,
                            ),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  // حالة المخزون
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 8,
                    ),
                    decoration: BoxDecoration(
                      color: widget.product.quantityInStock > 0
                          ? Colors.green.shade50
                          : Colors.red.shade50,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          widget.product.quantityInStock > 0
                              ? Icons.check_circle
                              : Icons.cancel,
                          color: widget.product.quantityInStock > 0
                              ? Colors.green
                              : Colors.red,
                          size: 20,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          widget.product.quantityInStock > 0
                              ? 'متوفر في المخزون'
                              : 'غير متوفر حالياً',
                          style: TextStyle(
                            color: widget.product.quantityInStock > 0
                                ? Colors.green.shade800
                                : Colors.red.shade800,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  // الوصف
                  if (widget.product.description.isNotEmpty) ...[
                    const Text(
                      'الوصف',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      widget.product.description,
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey.shade700,
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  // الفئة
                  if (widget.product.category.isNotEmpty) ...[
                    const Text(
                      'الفئة',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.blue.shade50,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        widget.product.category,
                        style: TextStyle(color: Colors.blue.shade700),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  // SKU
                  Text(
                    'SKU: ${widget.product.sku}',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey.shade500,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
      bottomNavigationBar: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.grey.shade200,
              blurRadius: 10,
              offset: const Offset(0, -5),
            ),
          ],
        ),
        child: SafeArea(
          child: Row(
            children: [
              // تحديد الكمية
              Container(
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey.shade300),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  children: [
                    IconButton(
                      onPressed: _quantity > 1
                          ? () => setState(() => _quantity--)
                          : null,
                      icon: const Icon(Icons.remove),
                    ),
                    SizedBox(
                      width: 40,
                      child: Text(
                        '$_quantity',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    IconButton(
                      onPressed: widget.product.quantityInStock > _quantity
                          ? () => setState(() => _quantity++)
                          : null,
                      icon: const Icon(Icons.add),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              // زر الإضافة إلى السلة
              Expanded(
                child: ElevatedButton(
                  onPressed: widget.product.quantityInStock > 0 && !_isLoading
                      ? _addToCart
                      : null,
                  style: ElevatedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                  child: Text(
                    'إضافة إلى السلة - ${(widget.product.unitPrice * _quantity).toStringAsFixed(2)} ريال',
                    style: const TextStyle(fontSize: 16),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}