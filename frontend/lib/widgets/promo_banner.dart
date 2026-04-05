// =====================================================
// promo_banner.dart - شريط إعلانات متحرك في أعلى الصفحة الرئيسية
// =====================================================

import 'package:flutter/material.dart';
import 'package:carousel_slider/carousel_slider.dart';
import 'package:cached_network_image/cached_network_image.dart';
import '../api_service.dart';

class PromoBanner extends StatefulWidget {
  const PromoBanner({super.key});

  @override
  State<PromoBanner> createState() => _PromoBannerState();
}

class _PromoBannerState extends State<PromoBanner> {
  final ApiService _api = ApiService();
  List<Map<String, dynamic>> _promotions = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadPromotions();
  }

  Future<void> _loadPromotions() async {
    try {
      final promotions = await _api.fetchPromotions();
      setState(() {
        _promotions = promotions.take(5).toList();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
      });
    }
  }

  void _onPromotionTap(Map<String, dynamic> promotion) {
    _api.trackPromotionClick(promotion['id']);
    if (promotion['product_sku'] != null) {
      Navigator.pushNamed(context, '/product', arguments: promotion['product_sku']);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Container(
        height: 100,
        color: Colors.grey.shade100,
        child: const Center(
          child: SizedBox(
            height: 30,
            width: 30,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        ),
      );
    }

    if (_promotions.isEmpty) {
      return const SizedBox.shrink();
    }

    return CarouselSlider(
      options: CarouselOptions(
        height: 120,
        autoPlay: true,
        autoPlayInterval: const Duration(seconds: 5),
        enlargeCenterPage: false,
        viewportFraction: 1.0,
        pauseAutoPlayOnTouch: true,
      ),
      items: _promotions.map((promo) {
        return GestureDetector(
          onTap: () => _onPromotionTap(promo),
          child: Container(
            width: double.infinity,
            margin: const EdgeInsets.symmetric(horizontal: 8),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              gradient: LinearGradient(
                colors: [
                  Colors.blue.shade700,
                  Colors.blue.shade500,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Row(
              children: [
                // صورة الإعلان
                if (promo['image_url'] != null && promo['image_url'].isNotEmpty)
                  ClipRRect(
                    borderRadius: const BorderRadius.horizontal(
                      left: Radius.circular(12),
                    ),
                    child: CachedNetworkImage(
                      imageUrl: promo['image_url'],
                      width: 100,
                      height: 120,
                      fit: BoxFit.cover,
                      placeholder: (_, __) => Container(
                        width: 100,
                        color: Colors.blue.shade400,
                        child: const Center(
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                      ),
                      errorWidget: (_, __, ___) => Container(
                        width: 100,
                        color: Colors.blue.shade400,
                        child: const Icon(Icons.image, color: Colors.white),
                      ),
                    ),
                  ),
                // نص الإعلان
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          promo['title'],
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        if (promo['body'] != null && promo['body'].isNotEmpty)
                          Text(
                            promo['body'],
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 12,
                            ),
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                          ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            const Icon(
                              Icons.touch_app,
                              size: 14,
                              color: Colors.white70,
                            ),
                            const SizedBox(width: 4),
                            const Text(
                              'اضغط للتفاصيل',
                              style: TextStyle(
                                color: Colors.white70,
                                fontSize: 10,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      }).toList(),
    );
  }
}