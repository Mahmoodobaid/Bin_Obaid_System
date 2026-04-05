// =====================================================
// cart_item.dart - نموذج بيانات عنصر في سلة التسوق
// =====================================================

class CartItem {
  final String sku;
  final String name;
  int quantity;
  final double unitPrice;
  final String? imageUrl;

  CartItem({
    required this.sku,
    required this.name,
    required this.quantity,
    required this.unitPrice,
    this.imageUrl,
  });

  factory CartItem.fromJson(Map<String, dynamic> json) {
    return CartItem(
      sku: json['sku'] ?? '',
      name: json['name'] ?? '',
      quantity: json['quantity'] ?? 1,
      unitPrice: (json['unitPrice'] ?? 0).toDouble(),
      imageUrl: json['imageUrl'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'sku': sku,
      'name': name,
      'quantity': quantity,
      'unitPrice': unitPrice,
      'imageUrl': imageUrl,
    };
  }

  double get totalPrice => quantity * unitPrice;
  
  String get formattedTotalPrice => '${totalPrice.toStringAsFixed(2)} ريال';
  
  String get formattedUnitPrice => '${unitPrice.toStringAsFixed(2)} ريال';

  void incrementQuantity() {
    quantity++;
  }

  bool decrementQuantity() {
    if (quantity > 1) {
      quantity--;
      return true;
    }
    return false;
  }

  CartItem copyWith({
    String? sku,
    String? name,
    int? quantity,
    double? unitPrice,
    String? imageUrl,
  }) {
    return CartItem(
      sku: sku ?? this.sku,
      name: name ?? this.name,
      quantity: quantity ?? this.quantity,
      unitPrice: unitPrice ?? this.unitPrice,
      imageUrl: imageUrl ?? this.imageUrl,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is CartItem && other.sku == sku;
  }

  @override
  int get hashCode => sku.hashCode;
}