// =====================================================
// user.dart - نموذج بيانات المستخدم
// =====================================================

class User {
  final String id;
  final String email;
  final String? fullName;
  final String role;
  final bool canViewPrices;
  final bool isActive;
  final String? createdAt;
  final String? lastLogin;

  User({
    required this.id,
    required this.email,
    this.fullName,
    this.role = 'customer',
    this.canViewPrices = false,
    this.isActive = true,
    this.createdAt,
    this.lastLogin,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] ?? '',
      email: json['email'] ?? '',
      fullName: json['full_name'],
      role: json['role'] ?? 'customer',
      canViewPrices: json['can_view_prices'] ?? false,
      isActive: json['is_active'] ?? true,
      createdAt: json['created_at'],
      lastLogin: json['last_login'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'full_name': fullName,
      'role': role,
      'can_view_prices': canViewPrices,
      'is_active': isActive,
      'created_at': createdAt,
      'last_login': lastLogin,
    };
  }

  String get displayName => fullName ?? email.split('@').first;
  
  String get roleText {
    switch (role) {
      case 'admin': return 'مدير';
      case 'delivery': return 'مندوب توصيل';
      default: return 'عميل';
    }
  }
  
  bool get isAdmin => role == 'admin';
  
  bool get isDelivery => role == 'delivery';
  
  bool get isCustomer => role == 'customer';

  User copyWith({
    String? id,
    String? email,
    String? fullName,
    String? role,
    bool? canViewPrices,
    bool? isActive,
  }) {
    return User(
      id: id ?? this.id,
      email: email ?? this.email,
      fullName: fullName ?? this.fullName,
      role: role ?? this.role,
      canViewPrices: canViewPrices ?? this.canViewPrices,
      isActive: isActive ?? this.isActive,
      createdAt: createdAt,
      lastLogin: lastLogin,
    );
  }
}