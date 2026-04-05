// =====================================================
// promotion.dart - نموذج بيانات الإعلان الترويجي
// =====================================================

class Promotion {
  final int id;
  final String title;
  final String? body;
  final String? imageUrl;
  final String? productSku;
  final String? startDate;
  final String? endDate;
  final bool isActive;
  final int? clickCount;
  final String? createdAt;

  Promotion({
    required this.id,
    required this.title,
    this.body,
    this.imageUrl,
    this.productSku,
    this.startDate,
    this.endDate,
    this.isActive = true,
    this.clickCount,
    this.createdAt,
  });

  factory Promotion.fromJson(Map<String, dynamic> json) {
    return Promotion(
      id: json['id'] ?? 0,
      title: json['title'] ?? '',
      body: json['body'],
      imageUrl: json['image_url'],
      productSku: json['product_sku'],
      startDate: json['start_date'],
      endDate: json['end_date'],
      isActive: json['is_active'] ?? true,
      clickCount: json['click_count'],
      createdAt: json['created_at'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'title': title,
      'body': body,
      'image_url': imageUrl,
      'product_sku': productSku,
      'start_date': startDate,
      'end_date': endDate,
      'is_active': isActive,
      'click_count': clickCount,
      'created_at': createdAt,
    };
  }

  bool get isCurrentlyActive {
    if (!isActive) return false;
    if (startDate != null) {
      try {
        final start = DateTime.parse(startDate!);
        if (start.isAfter(DateTime.now())) return false;
      } catch (_) {}
    }
    if (endDate != null) {
      try {
        final end = DateTime.parse(endDate!);
        if (end.isBefore(DateTime.now())) return false;
      } catch (_) {}
    }
    return true;
  }

  String get statusText {
    if (!isActive) return 'غير نشط';
    if (startDate != null) {
      try {
        final start = DateTime.parse(startDate!);
        if (start.isAfter(DateTime.now())) return 'قادم';
      } catch (_) {}
    }
    if (endDate != null) {
      try {
        final end = DateTime.parse(endDate!);
        if (end.isBefore(DateTime.now())) return 'منتهي';
      } catch (_) {}
    }
    return 'نشط';
  }
  
  Color get statusColor {
    switch (statusText) {
      case 'نشط': return Colors.green;
      case 'قادم': return Colors.orange;
      case 'منتهي': return Colors.grey;
      default: return Colors.red;
    }
  }
}