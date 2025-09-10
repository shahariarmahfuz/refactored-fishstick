import functools
from flask import Blueprint, request, jsonify, current_app
from game_shop.db import get_db
import psycopg2.extras

bp = Blueprint('api', __name__, url_prefix='/api')

# API কী যাচাই করার জন্য ডেকোরেটর
def api_key_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        api_key = request.headers.get('X-API-KEY')
        if not api_key or api_key != current_app.config.get('API_SECURITY_KEY'):
            return jsonify({'error': 'Unauthorized: Invalid or missing API key'}), 401
        return view(**kwargs)
    return wrapped_view

@bp.route('/users')
@api_key_required
def get_users():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT id, username, balance FROM users ORDER BY id')
    users = cursor.fetchall()
    cursor.close()
    return jsonify([dict(user) for user in users])

@bp.route('/users/<username>/orders')
@api_key_required
def get_user_orders(username):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # URL থেকে স্ট্যাটাস ফিল্টার গ্রহণ করা হচ্ছে
    status_filter = request.args.get('status', 'all').lower()

    cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        return jsonify({'error': f'User {username} not found'}), 404
    
    # বেস কোয়েরি
    query = '''
        SELECT o.id, o.game_uid, o.status, o.payment_method, o.order_time, p.name as product_name, p.price
        FROM orders o JOIN product p ON o.product_id = p.id
        WHERE o.account_user_id = %s
    '''
    params = [user['id']]

    # স্ট্যাটাস অনুযায়ী কোয়েরি পরিবর্তন করা হচ্ছে
    if status_filter == 'pending':
        query += " AND o.status IN ('Pending Payment', 'Awaiting Payment', 'Pending')"
    elif status_filter == 'accepted' or status_filter == 'completed':
        query += " AND o.status = 'Completed'"
    elif status_filter == 'rejected':
        query += " AND o.status = 'Rejected'"
    
    query += ' ORDER BY o.order_time DESC'
    
    cursor.execute(query, tuple(params))
    orders = cursor.fetchall()
    cursor.close()
    return jsonify([dict(order) for order in orders])

@bp.route('/games')
@api_key_required
def get_games():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM game ORDER BY title')
    games = cursor.fetchall()
    cursor.close()
    return jsonify([dict(game) for game in games])

@bp.route('/games/<int:game_id>/categories')
@api_key_required
def get_game_categories(game_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM category WHERE game_id = %s ORDER BY name', (game_id,))
    categories = cursor.fetchall()
    cursor.close()
    return jsonify([dict(category) for category in categories])

@bp.route('/categories/<int:category_id>/products')
@api_key_required
def get_category_products(category_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM product WHERE category_id = %s', (category_id,))
    products = cursor.fetchall()
    cursor.close()
    return jsonify([dict(product) for product in products])