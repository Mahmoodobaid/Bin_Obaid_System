from flask import Blueprint, request, jsonify
from decorators import login_required, role_required
from models import ProductModel, SettingsModel
import logging

logger = logging.getLogger(__name__)
products_bp = Blueprint('products', __name__)

@products_bp.route('/products', methods=['GET'])
def get_products():
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        category = request.args.get('category', None)
        search = request.args.get('search', None)
        products = ProductModel.get_all(limit, offset, category, search)
        total = ProductModel.count_all(category, search)
        # بدون إضافة الصور
        return jsonify({
            'products': products,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + limit < total
        }), 200
    except Exception as e:
        logger.error(f"Error in get_products: {str(e)}")
        return jsonify({'error': str(e)}), 500

@products_bp.route('/products/<sku>', methods=['GET'])
def get_product(sku):
    try:
        product = ProductModel.get_by_sku(sku)
        if not product:
            return jsonify({'error': 'المنتج غير موجود'}), 404
        return jsonify(product), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/products/categories', methods=['GET'])
def get_categories():
    return jsonify({'categories': []}), 200
