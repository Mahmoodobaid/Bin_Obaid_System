// =====================================================
// template.dart - نموذج بيانات النموذج الجاهز للطلبات السريعة
// =====================================================

class TemplateItem {
  final String sku;
  final String? name;
  final int quantity;
  final bool isRequired;
  final double? unitPrice;

  TemplateItem({
    required this.sku,
    this.name,
    this.quantity = 1,
    this.isRequired = true,
    this.unitPrice,
  });

  factory TemplateItem.fromJson(Map<String, dynamic> json) {
    return TemplateItem(
      sku: json['sku'] ?? '',
      name: json['name'],
      quantity: json['quantity'] ?? 1,
      isRequired: json['is_required'] ?? true,
      unitPrice: (json['unit_price'] ?? 0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'sku': sku,
      'name': name,
      'quantity': quantity,
      'is_required': isRequired,
      'unit_price': unitPrice,
    };
  }
  
  String get displayName => name ?? sku;
  
  double get estimatedTotal => (unitPrice ?? 0) * quantity;
}

class QuoteTemplate {
  final int id;
  final String name;
  final String? description;
  final List<TemplateItem> items;
  final bool isActive;
  final double? estimatedPrice;
  final String? createdAt;

  QuoteTemplate({
    required this.id,
    required this.name,
    this.description,
    this.items = const [],
    this.isActive = true,
    this.estimatedPrice,
    this.createdAt,
  });

  factory QuoteTemplate.fromJson(Map<String, dynamic> json) {
    List<TemplateItem> items = [];
    if (json['items'] != null) {
      items = (json['items'] as List)
          .map((item) => TemplateItem.fromJson(item))
          .toList();
    }
    
    return QuoteTemplate(
      id: json['id'] ?? 0,
      name: json['name'] ?? '',
      description: json['description'],
      items: items,
      isActive: json['is_active'] ?? true,
      estimatedPrice: (json['estimated_price'] ?? 0).toDouble(),
      createdAt: json['created_at'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'items': items.map((e) => e.toJson()).toList(),
      'is_active': isActive,
      'estimated_price': estimatedPrice,
      'created_at': createdAt,
    };
  }
  
  int get itemCount => items.length;
  
  String get statusText => isActive ? 'نشط' : 'غير نشط';
  
  Color get statusColor => isActive ? Colors.green : Colors.grey;
  
  String get formattedDate {
    if (createdAt == null) return '';
    try {
      final date = DateTime.parse(createdAt!);
      return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    } catch (e) {
      return createdAt!;
    }
  }
  
  List<TemplateItem> get requiredItems => items.where((i) => i.isRequired).toList();
  
  List<TemplateItem> get optionalItems => items.where((i) => !i.isRequired).toList();
}