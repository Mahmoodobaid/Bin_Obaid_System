// =====================================================
// product.dart - نموذج بيانات المنتج
// =====================================================

class Product {
  final String sku;
  final String name;
  final String description;
  final String category;
  final int quantityInStock;
  final double unitPrice;
  final List<String> imageUrls;
  final String? firstImage;

  Product({
    required this.sku,
    required this.name,
    this.description = '',
    this.category = '',
    this.quantityInStock = 0,
    this.unitPrice = 0.0,
    this.imageUrls = const [],
    this.firstImage,
  });

  factory Product.fromJson(Map<String, dynamic> json) {
    List<String> images = [];
    if (json['images'] != null) {
      images = List<String>.from(json['images']);
    } else if (json['image_urls'] != null) {
      images = List<String>.from(json['image_urls']);
    }
    
    return Product(
      sku: json['sku'] ?? '',
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      category: json['category'] ?? '',
      quantityInStock: json['quantity_in_stock'] ?? 0,
      unitPrice: (json['unit_price'] ?? 0).toDouble(),
      imageUrls: images,
      firstImage: json['first_image'] ?? (images.isNotEmpty ? images.first : null),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'sku': sku,
      'name': name,
      'description': description,
      'category': category,
      'quantity_in_stock': quantityInStock,
      'unit_price': unitPrice,
      'image_urls': imageUrls,
    };
  }

  double get totalValue => unitPrice * quantityInStock;
  
  bool get isInStock => quantityInStock > 0;
  
  bool get isLowStock => quantityInStock > 0 && quantityInStock < 10;
  
  String get formattedPrice => '${unitPrice.toStringAsFixed(2)} ريال';
  
  String get stockStatus {
    if (quantityInStock <= 0) return 'غير متوفر';
    if (quantityInStock < 10) return 'المتبقي: $quantityInStock';
    return 'متوفر';
  }

  Product copyWith({
    String? sku,
    String? name,
    String? description,
    String? category,
    int? quantityInStock,
    double? unitPrice,
    List<String>? imageUrls,
  }) {
    return Product(
      sku: sku ?? this.sku,
      name: name ?? this.name,
      description: description ?? this.description,
      category: category ?? this.category,
      quantityInStock: quantityInStock ?? this.quantityInStock,
      unitPrice: unitPrice ?? this.unitPrice,
      imageUrls: imageUrls ?? this.imageUrls,
    );
  }
}