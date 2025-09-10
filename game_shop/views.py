from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app, send_from_directory
)
from game_shop.db import get_db
from werkzeug.utils import secure_filename
import os
from game_shop.user_auth import login_required
from datetime import datetime, timedelta
import psycopg2.extras
from game_shop.image_uploader import upload_image_to_xenko

bp = Blueprint('views', __name__)

@bp.route('/')
def home():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT content FROM notices WHERE is_active = 1 LIMIT 1')
    active_notice = cursor.fetchone()
    cursor.execute('SELECT * FROM banners WHERE is_active = 1 ORDER BY id')
    active_banners = cursor.fetchall()
    cursor.execute('SELECT * FROM popup_messages WHERE is_active = 1 LIMIT 1')
    active_popup = cursor.fetchone()
    cursor.execute('SELECT * FROM game ORDER BY title')
    games = cursor.fetchall()
    games_with_categories = []
    for game in games:
        cursor.execute('SELECT * FROM category WHERE game_id = %s ORDER BY name', (game['id'],))
        categories = cursor.fetchall()
        games_with_categories.append({'game': game, 'categories': categories})
    cursor.close()
    return render_template('home.html', notice=active_notice, banners=active_banners, popup=active_popup, games_data=games_with_categories)

@bp.route('/category/<int:category_id>', methods=('GET', 'POST'))
@login_required
def view_category(category_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(
        'SELECT c.id, c.name, c.image_url, c.rules_text, g.title as game_title FROM category c JOIN game g ON c.game_id = g.id WHERE c.id = %s',
        (category_id,)
    )
    category = cursor.fetchone()

    if category is None:
        cursor.close()
        return "Category not found", 404

    if request.method == 'POST':
        game_uid = request.form.get('game_uid')
        product_id = request.form.get('product_id')
        payment_option = request.form.get('payment_option')

        cursor.execute('SELECT * FROM product WHERE id = %s', (product_id,))
        product = cursor.fetchone()

        if not (game_uid and product):
            flash('দয়া করে একটি প্রোডাক্ট সিলেক্ট করুন এবং আপনার গেম UID দিন।')
            cursor.close()
            return redirect(url_for('views.view_category', category_id=category_id))

        if product['restriction_days'] and product['restriction_days'] > 0:
            cursor.execute(
                '''SELECT order_time FROM orders 
                   WHERE game_uid = %s AND product_id = %s AND status != 'Rejected'
                   ORDER BY order_time DESC LIMIT 1''',
                (game_uid, product_id)
            )
            last_order = cursor.fetchone()
            if last_order and last_order['order_time']:
                time_since_order = datetime.now() - last_order['order_time']
                if time_since_order.days < product['restriction_days']:
                    wait_days = product['restriction_days'] - time_since_order.days
                    flash(f"এই UID দিয়ে প্রোডাক্টটি কেনার পর {product['restriction_days']} দিন পার হয়নি। আবার কেনার জন্য আপনাকে আরও {wait_days} দিন অপেক্ষা করতে হবে।")
                    cursor.close()
                    return redirect(url_for('views.view_category', category_id=category_id))

        if product['is_limited'] and product['stock'] <= 0:
            flash(f"দুঃখিত, '{product['name']}' বর্তমানে আউট অফ স্টক।")
            cursor.close()
            return redirect(url_for('views.view_category', category_id=category_id))

        if payment_option == 'wallet':
            if g.user['balance'] >= product['price']:
                if product['is_limited']:
                    cursor.execute('UPDATE product SET stock = stock - 1 WHERE id = %s', (product_id,))
                cursor.execute('UPDATE users SET balance = balance - %s WHERE id = %s', (product['price'], g.user['id']))
                cursor.execute(
                    'INSERT INTO orders (product_id, account_user_id, game_uid, status, payment_method) VALUES (%s, %s, %s, %s, %s)',
                    (product_id, g.user['id'], game_uid, 'Pending Payment', 'Wallet')
                )
                db.commit()
                flash('ওয়ালেট থেকে পেমেন্ট সফল হয়েছে। আপনার অর্ডারটি এখন পর্যালোচনার অধীনে আছে।')
                cursor.close()
                return redirect(url_for('views.my_orders'))
            else:
                flash('আপনার ওয়ালেটে পর্যাপ্ত ব্যালেন্স নেই। অনুগ্রহ করে টাকা যোগ করুন।')
                cursor.close()
                return redirect(url_for('user_auth.add_funds'))

        elif payment_option == 'online':
            if product['is_limited']:
                cursor.execute('UPDATE product SET stock = stock - 1 WHERE id = %s', (product_id,))
            cursor.execute(
                'INSERT INTO orders (product_id, account_user_id, game_uid, status) VALUES (%s, %s, %s, %s) RETURNING id',
                (product_id, g.user['id'], game_uid, 'Awaiting Payment')
            )
            order_id = cursor.fetchone()[0]
            db.commit()
            cursor.close()
            return redirect(url_for('views.checkout', order_id=order_id))

    cursor.execute('SELECT * FROM product WHERE category_id = %s AND is_active = 1 ORDER BY price', (category_id,))
    products = cursor.fetchall()
    cursor.close()
    return render_template('category_products.html', category=category, products=products)

@bp.route('/checkout/<int:order_id>')
@login_required
def checkout(order_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(
        'SELECT o.id, p.name as product_name, p.price FROM orders o JOIN product p ON o.product_id = p.id WHERE o.id = %s AND o.status = %s AND o.account_user_id = %s',
        (order_id, 'Awaiting Payment', g.user['id'])
    )
    order = cursor.fetchone()
    if not order:
        cursor.close()
        flash('অর্ডার খুঁজে পাওয়া যায়নি অথবা ইতিমধ্যে প্রক্রিয়াধীন।')
        return redirect(url_for('views.home'))
    cursor.execute('SELECT name FROM payment_methods WHERE is_active = 1')
    payment_methods = cursor.fetchall()
    cursor.close()
    return render_template('select_payment.html', order=order, payment_methods=payment_methods)

@bp.route('/payment/<int:order_id>/<string:method>')
@login_required
def payment_page(order_id, method):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(
        'SELECT o.id, p.price FROM orders o JOIN product p ON o.product_id = p.id WHERE o.id = %s AND o.status = %s AND o.account_user_id = %s',
        (order_id, 'Awaiting Payment', g.user['id'])
    )
    order = cursor.fetchone()
    cursor.execute('SELECT name, account_number FROM payment_methods WHERE name = %s AND is_active = 1', (method,))
    payment_method = cursor.fetchone()
    cursor.close()
    if not order or not payment_method:
        flash('অর্ডার অথবা পেমেন্ট মেথড খুঁজে পাওয়া যায়নি।')
        return redirect(url_for('views.home'))
    return render_template('checkout.html', order=order, payment_method=payment_method)

@bp.route('/place_order/<int:order_id>', methods=['POST'])
@login_required
def place_order(order_id):
    db = get_db()
    cursor = db.cursor()
    payment_method = request.form.get('payment_method')
    transaction_id = request.form.get('transaction_id')
    screenshot = request.files.get('screenshot')
    screenshot_url = None
    if not transaction_id and (not screenshot or screenshot.filename == ''):
        flash('অনুগ্রহ করে ট্রানজেকশন আইডি দিন অথবা স্ক্রিনশট আপলোড করুন।')
        return redirect(url_for('views.payment_page', order_id=order_id, method=payment_method))
    if screenshot and screenshot.filename != '':
        uploaded_url = upload_image_to_xenko(screenshot)
        if uploaded_url:
            screenshot_url = uploaded_url
        else:
            flash('দুঃখিত, ছবিটি আপলোড করা সম্ভব হয়নি। অনুগ্রহ করে আবার চেষ্টা করুন।')
            return redirect(url_for('views.payment_page', order_id=order_id, method=payment_method))
    cursor.execute(
        'UPDATE orders SET status = %s, payment_method = %s, transaction_id = %s, screenshot_url = %s WHERE id = %s AND account_user_id = %s',
        ('Pending Payment', payment_method, transaction_id, screenshot_url, order_id, g.user['id'])
    )
    db.commit()
    cursor.close()
    flash('আপনার অর্ডারটি সফলভাবে জমা দেওয়া হয়েছে এবং পর্যালোচনার অধীনে আছে।')
    return redirect(url_for('views.my_orders'))

@bp.route('/my-orders')
@login_required
def my_orders():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(
        'SELECT o.id, o.status, o.order_time, o.completion_time, o.game_uid, p.name as product_name, p.price FROM orders o JOIN product p ON o.product_id = p.id WHERE o.account_user_id = %s ORDER BY o.order_time DESC',
        (g.user['id'],)
    )
    orders = cursor.fetchall()
    cursor.close()
    return render_template('my_orders.html', orders=orders)