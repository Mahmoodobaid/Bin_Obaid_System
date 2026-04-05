// =====================================================
// quote.dart - نموذج بيانات عرض السعر
// =====================================================

class QuoteItem {
  final int? id;
  final int? quoteId;
  final String productSku;
  final String productName;
  final int quantity;
  final double unitPrice;
  final double totalPrice;

  QuoteItem({
    this.id,
    this.quoteId,
    required this.productSku,
    required this.productName,
    required this.quantity,
    required this.unitPrice,
    double? totalPrice,
  }) : totalPrice = totalPrice ?? (quantity * unitPrice);

  factory QuoteItem.fromJson(Map<String, dynamic> json) {
    return QuoteItem(
      id: json['id'],
      quoteId: json['quote_id'],
      productSku: json['product_sku'] ?? '',
      productName: json['product_name'] ?? json['product_sku'] ?? '',
      quantity: json['quantity'] ?? 0,
      unitPrice: (json['unit_price'] ?? 0).toDouble(),
      totalPrice: (json['total_price'] ?? 0).toDouble(),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'quote_id': quoteId,
      'product_sku': productSku,
      'product_name': productName,
      'quantity': quantity,
      'unit_price': unitPrice,
      'total_price': totalPrice,
    };
  }
}

class Quote {
  final int id;
  final String userId;
  final String? userName;
  final String? userEmail;
  final List<QuoteItem> items;
  final double totalAmount;
  final String status;
  final String? createdAt;
  final String? updatedAt;
  final String? notes;

  Quote({
    required this.id,
    required this.userId,
    this.userName,
    this.userEmail,
    this.items = const [],
    this.totalAmount = 0.0,
    this.status = 'pending',
    this.createdAt,
    this.updatedAt,
    this.notes,
  });

  factory Quote.fromJson(Map<String, dynamic> json) {
    List<QuoteItem> items = [];
    if (json['quote_items'] != null) {
      items = (json['quote_items'] as List)
          .map((item) => QuoteItem.fromJson(item))
          .toList();
    } else if (json['items'] != null) {
      items = (json['items'] as List)
          .map((item) => QuoteItem.fromJson(item))
          .toList();
    }
    
    return Quote(
      id: json['id'] ?? 0,
      userId: json['user_id'] ?? '',
      userName: json['user_name'],
      userEmail: json['user_email'],
      items: items,
      totalAmount: (json['total_amount'] ?? 0).toDouble(),
      status: json['status'] ?? 'pending',
      createdAt: json['created_at'],
      updatedAt: json['updated_at'],
      notes: json['notes'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'user_id': userId,
      'user_name': userName,
      'user_email': userEmail,
      'items': items.map((e) => e.toJson()).toList(),
      'total_amount': totalAmount,
      'status': status,
      'created_at': createdAt,
      'updated_at': updatedAt,
      'notes': notes,
    };
  }

  String get statusText {
    switch (status) {
      case 'approved': return 'تمت الموافقة';
      case 'rejected': return 'مرفوض';
      case 'sent': return 'تم الإرسال';
      case 'cancelled': return 'ملغي';
      default: return 'قيد المراجعة';
    }
  }
  
  Color get statusColor {
    switch (status) {
      case 'approved': return Colors.green;
      case 'rejected': return Colors.red;
      case 'sent': return Colors.blue;
      case 'cancelled': return Colors.grey;
      default: return Colors.orange;
    }
  }
  
  String get formattedDate {
    if (createdAt == null) return '';
    try {
      final date = DateTime.parse(createdAt!);
      return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
    } catch (e) {
      return createdAt!;
    }
  }
  
  int get itemCount => items.length;
  
  bool get canCancel => status == 'pending';
}