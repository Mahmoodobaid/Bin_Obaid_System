// =====================================================
// gallery_carousel.dart - ويدجت عرض الصور في كروسيل متحرك
// =====================================================

import 'package:flutter/material.dart';
import 'package:carousel_slider/carousel_slider.dart';
import 'package:cached_network_image/cached_network_image.dart';

class GalleryCarousel extends StatefulWidget {
  final List<String> imageUrls;
  final Duration autoPlayInterval;
  final double height;

  const GalleryCarousel({
    super.key,
    required this.imageUrls,
    this.autoPlayInterval = const Duration(seconds: 4),
    this.height = 300,
  });

  @override
  State<GalleryCarousel> createState() => _GalleryCarouselState();
}

class _GalleryCarouselState extends State<GalleryCarousel> {
  int _currentIndex = 0;
  final CarouselSliderController _controller = CarouselSliderController();

  @override
  Widget build(BuildContext context) {
    if (widget.imageUrls.isEmpty) {
      return Container(
        height: widget.height,
        color: Colors.grey.shade200,
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.no_photography, size: 50, color: Colors.grey),
              SizedBox(height: 8),
              Text('لا توجد صور', style: TextStyle(color: Colors.grey)),
            ],
          ),
        ),
      );
    }

    return Column(
      children: [
        // الكروسيل
        Stack(
          children: [
            CarouselSlider(
              carouselController: _controller,
              options: CarouselOptions(
                height: widget.height,
                autoPlay: true,
                autoPlayInterval: widget.autoPlayInterval,
                enlargeCenterPage: true,
                viewportFraction: 0.9,
                onPageChanged: (index, reason) {
                  setState(() {
                    _currentIndex = index;
                  });
                },
              ),
              items: widget.imageUrls.map((url) {
                return Builder(
                  builder: (BuildContext context) {
                    return ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: CachedNetworkImage(
                        imageUrl: url,
                        fit: BoxFit.cover,
                        width: double.infinity,
                        placeholder: (context, url) => Container(
                          color: Colors.grey.shade200,
                          child: const Center(
                            child: CircularProgressIndicator(),
                          ),
                        ),
                        errorWidget: (context, url, error) => Container(
                          color: Colors.grey.shade200,
                          child: const Center(
                            child: Icon(Icons.broken_image, size: 50),
                          ),
                        ),
                      ),
                    );
                  },
                );
              }).toList(),
            ),
            // أزرار التنقل (اختيارية)
            if (widget.imageUrls.length > 1)
              Positioned(
                left: 8,
                top: widget.height / 2 - 20,
                child: GestureDetector(
                  onTap: () => _controller.previousPage(),
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.5),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.chevron_left,
                      color: Colors.white,
                      size: 24,
                    ),
                  ),
                ),
              ),
            if (widget.imageUrls.length > 1)
              Positioned(
                right: 8,
                top: widget.height / 2 - 20,
                child: GestureDetector(
                  onTap: () => _controller.nextPage(),
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.5),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.chevron_right,
                      color: Colors.white,
                      size: 24,
                    ),
                  ),
                ),
              ),
          ],
        ),
        const SizedBox(height: 12),
        // نقاط المؤشر
        if (widget.imageUrls.length > 1)
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: widget.imageUrls.asMap().entries.map((entry) {
              return Container(
                width: 8,
                height: 8,
                margin: const EdgeInsets.symmetric(horizontal: 4),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _currentIndex == entry.key
                      ? Colors.blue
                      : Colors.grey.shade400,
                ),
              );
            }).toList(),
          ),
        // عداد الصور
        if (widget.imageUrls.length > 1)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.black.withOpacity(0.6),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                '${_currentIndex + 1} / ${widget.imageUrls.length}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                ),
              ),
            ),
          ),
      ],
    );
  }
}