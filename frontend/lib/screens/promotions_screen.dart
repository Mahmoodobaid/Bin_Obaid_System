// =====================================================
// promotions_screen.dart - شاشة عرض الإعلانات الترويجية والعروض
// =====================================================

import 'package:flutter/material.dart';
import '../api_service.dart';

class PromotionsScreen extends StatefulWidget {
  const PromotionsScreen({super.key});

  @override
  State<PromotionsScreen> createState() => _PromotionsScreenState();
}

class _PromotionsScreenState extends State<PromotionsScreen> {
  final ApiService _api = ApiService();
  late Future<List<Map<String, dynamic>>> _promotionsFuture;

  @override
  void initState() {
    super.initState();
    _promotionsFuture = _api.fetchPromotions();
  }

  void _showPromotionDetails(Map<String, dynamic> promotion) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Container(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 50,
                height: 4,
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            if (promotion['image_url'] != null && promotion['image_url'].isNotEmpty)
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.network(
                  promotion['image_url'],
                  height: 200,
                  width: double.infinity,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(
                    height: 200,
                    color: Colors.grey.shade200,
                    child: const Icon(Icons.broken_image, size: 50),
                  ),
                ),
              ),
            const SizedBox(height: 16),
            Text(
              promotion['title'],
              style: const TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            if (promotion['body'] != null && promotion['body'].isNotEmpty)
              Text(
                promotion['body'],
                style: TextStyle(color: Colors.grey.shade700, fontSize: 16),
              ),
            const SizedBox(height: 16),
            if (promotion['product_sku'] != null)
              Row(
                children: [
                  const Icon(Icons.qr_code, size: 16, color: Colors.grey),
                  const SizedBox(width: 4),
                  Text(
                    'SKU: ${promotion['product_sku']}',
                    style: TextStyle(color: Colors.grey.shade600),
                  ),
                ],
              ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.calendar_today, size: 16, color: Colors.grey),
                const SizedBox(width: 4),
                Text(
                  _formatDateRange(promotion),
                  style: TextStyle(color: Colors.grey.shade600),
                ),
              ],
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  if (promotion['product_sku'] != null) {
                    Navigator.pushNamed(context, '/product', arguments: promotion['product_sku']);
                  }
                },
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: Text(
                  promotion['product_sku'] != null ? 'عرض المنتج' : 'إغلاق',
                ),
              ),
            ),
          ],
        ),
      ),
    );
    
    // تسجيل النقرة
    _api.trackPromotionClick(promotion['id']);
  }

  String _formatDateRange(Map<String, dynamic> promotion) {
    final start = promotion['start_date'];
    final end = promotion['end_date'];
    
    if (start == null && end == null) return 'عرض مستمر';
    if (start != null && end == null) return 'يبدأ من ${_formatDate(start)}';
    if (start == null && end != null) return 'ينتهي في ${_formatDate(end)}';
    return '${_formatDate(start)} - ${_formatDate(end)}';
  }

  String _formatDate(String dateStr) {
    try {
      final date = DateTime.parse(dateStr);
      return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    } catch (e) {
      return dateStr;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('العروض الترويجية'),
        centerTitle: true,
      ),
      body: FutureBuilder<List<Map<String, dynamic>>>(
        future: _promotionsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          
          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline, size: 48, color: Colors.red),
                  const SizedBox(height: 16),
                  Text('حدث خطأ: ${snapshot.error}'),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () {
                      setState(() {
                        _promotionsFuture = _api.fetchPromotions();
                      });
                    },
                    child: const Text('إعادة المحاولة'),
                  ),
                ],
              ),
            );
          }
          
          final promotions = snapshot.data ?? [];
          
          if (promotions.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.local_offer_outlined, size: 80, color: Colors.grey.shade400),
                  const SizedBox(height: 16),
                  Text(
                    'لا توجد عروض حالياً',
                    style: TextStyle(color: Colors.grey.shade600),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'ترقبوا عروضنا القادمة',
                    style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
                  ),
                ],
              ),
            );
          }
          
          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: promotions.length,
            itemBuilder: (context, index) {
              final promo = promotions[index];
              final isExpired = promo['end_date'] != null && 
                  DateTime.parse(promo['end_date']).isBefore(DateTime.now());
              
              return Card(
                margin: const EdgeInsets.only(bottom: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(16),
                ),
                child: InkWell(
                  onTap: isExpired ? null : () => _showPromotionDetails(promo),
                  borderRadius: BorderRadius.circular(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (promo['image_url'] != null && promo['image_url'].isNotEmpty)
                        ClipRRect(
                          borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                          child: Image.network(
                            promo['image_url'],
                            height: 180,
                            width: double.infinity,
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(
                              height: 180,
                              color: Colors.grey.shade200,
                              child: const Icon(Icons.broken_image, size: 50),
                            ),
                          ),
                        ),
                      Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    promo['title'],
                                    style: const TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                                if (isExpired)
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 4,
                                    ),
                                    decoration: BoxDecoration(
                                      color: Colors.grey.shade200,
                                      borderRadius: BorderRadius.circular(20),
                                    ),
                                    child: const Text(
                                      'منتهي',
                                      style: TextStyle(fontSize: 10),
                                    ),
                                  ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            if (promo['body'] != null && promo['body'].isNotEmpty)
                              Text(
                                promo['body'],
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(color: Colors.grey.shade700),
                              ),
                            const SizedBox(height: 12),
                            Row(
                              children: [
                                Icon(
                                  Icons.calendar_today,
                                  size: 14,
                                  color: Colors.grey.shade500,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  _formatDateRange(promo),
                                  style: TextStyle(
                                    color: Colors.grey.shade500,
                                    fontSize: 12,
                                  ),
                                ),
                                const Spacer(),
                                if (!isExpired)
                                  const Text(
                                    'اضغط للتفاصيل',
                                    style: TextStyle(
                                      color: Colors.blue,
                                      fontSize: 12,
                                    ),
                                  ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}