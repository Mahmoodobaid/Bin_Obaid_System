// =====================================================
// image_cache_service.dart - إدارة التخزين المؤقت للصور
// =====================================================

import 'package:flutter_cache_manager/flutter_cache_manager.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

class CustomCacheManager {
  static const String key = 'product_images_cache';
  static const int maxAgeDays = 30;
  static const int maxCacheObjects = 500;

  static CacheManager instance = CacheManager(
    Config(
      key,
      stalePeriod: Duration(days: maxAgeDays),
      maxNrOfCacheObjects: maxCacheObjects,
      repo: JsonCacheInfoRepository(databaseName: key),
      fileSystem: FileSystem(),
      maxAgeCacheObject: Duration(days: maxAgeDays),
    ),
  );

  // مسح الكاش بالكامل
  static Future<void> clearCache() async {
    await instance.emptyCache();
  }

  // الحصول على حجم الكاش (تقريبي)
  static Future<int> getCacheSize() async {
    final cacheDir = await getTemporaryDirectory();
    final cachePath = '${cacheDir.path}/$key';
    final directory = Directory(cachePath);
    if (!await directory.exists()) return 0;
    
    int totalSize = 0;
    await for (final entity in directory.list()) {
      if (entity is File) {
        totalSize += await entity.length();
      }
    }
    return totalSize;
  }

  // تنظيف الملفات القديمة
  static Future<void> cleanOldFiles() async {
    await instance.cleanCache();
  }
}

// ويدجت مساعد لعرض الصور مع كاش
import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';

class CachedImage extends StatelessWidget {
  final String imageUrl;
  final double? width;
  final double? height;
  final BoxFit fit;
  final BorderRadius borderRadius;

  const CachedImage({
    super.key,
    required this.imageUrl,
    this.width,
    this.height,
    this.fit = BoxFit.cover,
    this.borderRadius = BorderRadius.zero,
  });

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: borderRadius,
      child: CachedNetworkImage(
        imageUrl: imageUrl,
        width: width,
        height: height,
        fit: fit,
        cacheManager: CustomCacheManager.instance,
        placeholder: (context, url) => Container(
          color: Colors.grey.shade200,
          child: const Center(
            child: SizedBox(
              width: 30,
              height: 30,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          ),
        ),
        errorWidget: (context, url, error) => Container(
          color: Colors.grey.shade200,
          child: const Icon(Icons.broken_image, size: 40),
        ),
      ),
    );
  }
}