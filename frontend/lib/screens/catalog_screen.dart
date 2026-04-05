// =====================================================
// catalog_screen.dart - شاشة عرض قائمة المنتجات (الكتالوج)
// =====================================================

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../providers/cart_provider.dart';
import '../api_service.dart';
import '../models/product.dart';
import '../widgets/product_card.dart';
import '../widgets/promo_banner.dart';
import 'cart_screen.dart';
import 'templates_screen.dart';
import 'promotions_screen.dart';
import 'product_detail_screen.dart';

class CatalogScreen extends StatefulWidget {
  const CatalogScreen({super.key});

  @override
  State<CatalogScreen> createState() => _CatalogScreenState();
}

class _CatalogScreenState extends State<CatalogScreen> {
  late Future<List<Product>> _productsFuture;
  final ApiService _api = ApiService();
  String _searchQuery = '';
  String? _selectedCategory;
  List<String> _categories = [];

  @override
  void initState() {
    super.initState();
    _productsFuture = _api.fetchProducts();
    _loadCategories();
  }

  Future<void> _loadCategories() async {
    try {
      final response = await _api.fetchCategories();
      setState(() {
        _categories = response;
      });
    } catch (e) {
      print('Error loading categories: $e');
    }
  }

  void _searchProducts(String query) {
    setState(() {
      _searchQuery = query;
      _productsFuture = _api.searchProducts(query);
    });
  }

  void _filterByCategory(String? category) {
    setState(() {
      _selectedCategory = category;
      if (category != null && category.isNotEmpty) {
        _productsFuture = _api.fetchProducts(category: category);
      } else {
        _productsFuture = _api.fetchProducts();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final auth = Provider.of<AuthProvider>(context);
    final cart = Provider.of<CartProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('بن عبيد للتجارة'),
        centerTitle: true,
        actions: [
          // زر السلة
          Stack(
            children: [
              IconButton(
                icon: const Icon(Icons.shopping_cart_outlined),
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => const CartScreen()),
                  );
                },
              ),
              if (cart.itemCount > 0)
                Positioned(
                  right: 4,
                  top: 4,
                  child: Container(
                    padding: const EdgeInsets.all(2),
                    decoration: const BoxDecoration(
                      color: Colors.red,
                      shape: BoxShape.circle,
                    ),
                    constraints: const BoxConstraints(
                      minWidth: 16,
                      minHeight: 16,
                    ),
                    child: Text(
                      '${cart.itemCount}',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
            ],
          ),
          // زر تسجيل الخروج
          IconButton(
            icon: const Icon(Icons.exit_to_app),
            onPressed: () async {
              await auth.logout();
              if (!mounted) return;
              Navigator.pushReplacementNamed(context, '/login');
            },
          ),
        ],
      ),
      body: Column(
        children: [
          // شريط الإعلانات
          const PromoBanner(),
          // شريط البحث
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: TextField(
              decoration: InputDecoration(
                hintText: 'بحث عن منتج...',
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onChanged: _searchProducts,
            ),
          ),
          // فلتر الفئات
          if (_categories.isNotEmpty)
            SizedBox(
              height: 50,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: 8),
                children: [
                  FilterChip(
                    label: const Text('الكل'),
                    selected: _selectedCategory == null,
                    onSelected: (_) => _filterByCategory(null),
                  ),
                  const SizedBox(width: 8),
                  ..._categories.map((cat) => Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: FilterChip(
                          label: Text(cat),
                          selected: _selectedCategory == cat,
                          onSelected: (_) => _filterByCategory(cat),
                        ),
                      )),
                ],
              ),
            ),
          // قائمة المنتجات
          Expanded(
            child: FutureBuilder<List<Product>>(
              future: _productsFuture,
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
                        const SizedBox(height: 8),
                        Text('حدث خطأ: ${snapshot.error}'),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: () {
                            setState(() {
                              _productsFuture = _api.fetchProducts();
                            });
                          },
                          child: const Text('إعادة المحاولة'),
                        ),
                      ],
                    ),
                  );
                }
                final products = snapshot.data!;
                if (products.isEmpty) {
                  return const Center(
                    child: Text('لا توجد منتجات'),
                  );
                }
                return GridView.builder(
                  padding: const EdgeInsets.all(8),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2,
                    childAspectRatio: 0.7,
                    crossAxisSpacing: 8,
                    mainAxisSpacing: 8,
                  ),
                  itemCount: products.length,
                  itemBuilder: (context, index) => ProductCard(
                    product: products[index],
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => ProductDetailScreen(
                            product: products[index],
                          ),
                        ),
                      );
                    },
                  ),
                );
              },
            ),
          ),
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        type: BottomNavigationBarType.fixed,
        currentIndex: 0,
        onTap: (index) {
          switch (index) {
            case 0:
              // الكتالوج (نحن فيه)
              break;
            case 1:
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const TemplatesScreen()),
              );
              break;
            case 2:
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const PromotionsScreen()),
              );
              break;
            case 3:
              Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const CartScreen()),
              );
              break;
          }
        },
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.storefront),
            label: 'المنتجات',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.file_copy),
            label: 'النماذج',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.local_offer),
            label: 'العروض',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.shopping_cart),
            label: 'السلة',
          ),
        ],
      ),
    );
  }
}