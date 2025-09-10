from flask import flash, redirect, request, url_for, render_template
from game_shop.auth import login_required
from game_shop.db import get_db
from game_shop.admin import bp
import psycopg2
import psycopg2.extras

# --- গেম ম্যানেজমেন্ট ---
@bp.route('/games', methods=['GET', 'POST'])
@login_required
def manage_games():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        title = request.form['title']
        if title:
            try:
                cursor.execute('INSERT INTO game (title) VALUES (%s)', (title,))
                db.commit()
                flash(f"গেম '{title}' সফলভাবে যোগ করা হয়েছে।")
            except (psycopg2.IntegrityError, psycopg2.errors.UniqueViolation):
                db.rollback()
                flash('এই গেমটি আগে থেকেই যোগ করা আছে।')
        else:
            flash('গেমের নাম আবশ্যক।')
        cursor.close()
        return redirect(url_for('admin.manage_games'))

    cursor.execute('SELECT * FROM game ORDER BY title')
    games = cursor.fetchall()
    cursor.close()
    return render_template('manage_games.html', games=games)

@bp.route('/games/edit/<int:game_id>', methods=['GET', 'POST'])
@login_required
def edit_game(game_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM game WHERE id = %s', (game_id,))
    game = cursor.fetchone()
    if request.method == 'POST':
        title = request.form['title']
        if title:
            try:
                cursor.execute('UPDATE game SET title = %s WHERE id = %s', (title, game_id))
                db.commit()
                flash('গেম সফলভাবে আপডেট করা হয়েছে।')
                cursor.close()
                return redirect(url_for('admin.manage_games'))
            except (psycopg2.IntegrityError, psycopg2.errors.UniqueViolation):
                db.rollback()
                flash('এই নামের গেম আগে থেকেই আছে।')
        else:
            flash('গেমের নাম আবশ্যক।')
    cursor.close()
    return render_template('edit_game.html', game=game)

@bp.route('/games/delete/<int:game_id>', methods=['POST'])
@login_required
def delete_game(game_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT id FROM category WHERE game_id = %s LIMIT 1', (game_id,))
    existing_category = cursor.fetchone()
    if existing_category:
        flash('এই গেমটি ডিলিট করা যাবে না কারণ এর অধীনে ক্যাটাগরি রয়েছে।')
    else:
        cursor.execute('DELETE FROM game WHERE id = %s', (game_id,))
        db.commit()
        flash('গেম সফলভাবে মুছে ফেলা হয়েছে।')
    cursor.close()
    return redirect(url_for('admin.manage_games'))

# --- ক্যাটাগরি ম্যানেজমেন্ট ---
@bp.route('/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        game_id = request.form['game_id']
        name = request.form['name']
        image_url = request.form['image_url']
        rules_text = request.form.get('rules_text', '')
        if game_id and name and image_url:
            cursor.execute('INSERT INTO category (game_id, name, image_url, rules_text) VALUES (%s, %s, %s, %s)',
                           (game_id, name, image_url, rules_text))
            db.commit()
            flash(f"ক্যাটেগরি '{name}' সফলভাবে যোগ করা হয়েছে।")
        else:
            flash("ফর্মের সবগুলো আবশ্যক ফিল্ড পূরণ করুন।")
        cursor.close()
        return redirect(url_for('admin.manage_categories'))

    cursor.execute('SELECT c.id, c.name, c.image_url, g.title as game_title FROM category c JOIN game g ON c.game_id = g.id ORDER BY g.title, c.name')
    categories = cursor.fetchall()
    cursor.execute('SELECT * FROM game ORDER BY title')
    games = cursor.fetchall()
    cursor.close()
    return render_template('manage_categories.html', categories=categories, games=games)

@bp.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def edit_category(category_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM category WHERE id = %s', (category_id,))
    category = cursor.fetchone()
    if request.method == 'POST':
        game_id = request.form['game_id']
        name = request.form['name']
        image_url = request.form['image_url']
        rules_text = request.form.get('rules_text', '')
        if game_id and name and image_url:
            cursor.execute('UPDATE category SET game_id = %s, name = %s, image_url = %s, rules_text = %s WHERE id = %s',
                           (game_id, name, image_url, rules_text, category_id))
            db.commit()
            flash('ক্যাটেগরি সফলভাবে আপডেট করা হয়েছে।')
            cursor.close()
            return redirect(url_for('admin.manage_categories'))
        else:
            flash("ফর্মের সবগুলো আবশ্যক ফিল্ড পূরণ করুন।")
    cursor.execute('SELECT * FROM game ORDER BY title')
    games = cursor.fetchall()
    cursor.close()
    return render_template('edit_category.html', category=category, games=games)

@bp.route('/categories/delete/<int:category_id>', methods=['POST'])
@login_required
def delete_category(category_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT id FROM product WHERE category_id = %s LIMIT 1', (category_id,))
    existing_product = cursor.fetchone()
    if existing_product:
        flash('এই ক্যাটেগরিটি ডিলিট করা যাবে না কারণ এর অধীনে প্রোডাক্ট রয়েছে।')
    else:
        cursor.execute('DELETE FROM category WHERE id = %s', (category_id,))
        db.commit()
        flash('ক্যাটেগরি সফলভাবে মুছে ফেলা হয়েছে।')
    cursor.close()
    return redirect(url_for('admin.manage_categories'))

# --- প্রোডাক্ট/আইটেম ম্যানেজমেন্ট ---
@bp.route('/products')
@login_required
def manage_products():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('''
        SELECT c.id, c.name, g.title as game_title, COUNT(p.id) as product_count
        FROM category c LEFT JOIN product p ON c.id = p.category_id JOIN game g ON c.game_id = g.id
        GROUP BY c.id, g.title ORDER BY g.title, c.name
    ''')
    categories = cursor.fetchall()
    cursor.close()
    return render_template('manage_products.html', categories=categories)

@bp.route('/products/category/<int:category_id>', methods=['GET', 'POST'])
@login_required
def view_products_by_category(category_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        is_limited_bool = request.form.get('is_limited') == 'on'
        is_limited_int = 1 if is_limited_bool else 0
        stock = request.form.get('stock')
        restriction_days = request.form.get('restriction_days', 0)

        if not (name and price):
            flash("নাম এবং মূল্য আবশ্যক।")
        elif is_limited_bool and not (stock and stock.isdigit() and int(stock) >= 0):
            flash("লিমিটেড প্রোডাক্টের জন্য স্টকের সংখ্যা সঠিকভাবে দিন।")
        else:
            stock_value = int(stock) if is_limited_bool and stock else None
            restriction_value = int(restriction_days) if restriction_days and restriction_days.isdigit() else 0
            cursor.execute(
                'INSERT INTO product (category_id, name, price, is_limited, stock, restriction_days) VALUES (%s, %s, %s, %s, %s, %s)',
                (category_id, name, price, is_limited_int, stock_value, restriction_value)
            )
            db.commit()
            flash(f"প্রোডাক্ট '{name}' সফলভাবে যোগ করা হয়েছে।")
        cursor.close()
        return redirect(url_for('admin.view_products_by_category', category_id=category_id))

    cursor.execute('SELECT * FROM category WHERE id = %s', (category_id,))
    category = cursor.fetchone()
    cursor.execute('SELECT * FROM product WHERE category_id = %s ORDER BY name', (category_id,))
    products = cursor.fetchall()
    cursor.close()
    return render_template('view_category_products.html', products=products, category=category)

@bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM product WHERE id = %s', (product_id,))
    product = cursor.fetchone()

    if request.method == 'POST':
        category_id = request.form.get('category_id')
        name = request.form.get('name')
        price = request.form.get('price')
        is_limited_bool = request.form.get('is_limited') == 'on'
        is_limited_int = 1 if is_limited_bool else 0
        stock = request.form.get('stock')
        restriction_days = request.form.get('restriction_days', 0)

        if not (name and price):
            flash("নাম এবং মূল্য আবশ্যক।")
        elif is_limited_bool and not (stock and stock.isdigit() and int(stock) >= 0):
            flash("লিমিটেড প্রোডাক্টের জন্য স্টকের সংখ্যা সঠিকভাবে দিন।")
        else:
            stock_value = int(stock) if is_limited_bool and stock else None
            restriction_value = int(restriction_days) if restriction_days and restriction_days.isdigit() else 0
            cursor.execute(
                'UPDATE product SET category_id = %s, name = %s, price = %s, is_limited = %s, stock = %s, restriction_days = %s WHERE id = %s',
                (category_id, name, price, is_limited_int, stock_value, restriction_value, product_id)
            )
            db.commit()
            flash('প্রোডাক্ট সফলভাবে আপডেট করা হয়েছে।')
            cursor.close()
            return redirect(url_for('admin.view_products_by_category', category_id=product['category_id']))

    cursor.execute('SELECT c.id, c.name, g.title as game_title FROM category c JOIN game g ON c.game_id = g.id ORDER BY g.title, c.name')
    categories = cursor.fetchall()
    cursor.close()
    return render_template('edit_product.html', product=product, categories=categories)

@bp.route('/products/toggle_status/<int:product_id>', methods=['POST'])
@login_required
def toggle_product_status(product_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT is_active, category_id FROM product WHERE id = %s', (product_id,))
    product = cursor.fetchone()
    if product:
        new_status = 0 if product['is_active'] == 1 else 1
        cursor.execute('UPDATE product SET is_active = %s WHERE id = %s', (new_status, product_id))
        db.commit()
        flash('প্রোডাক্টের স্ট্যাটাস সফলভাবে পরিবর্তন করা হয়েছে।')
    category_id = product['category_id'] if product else 1
    cursor.close()
    return redirect(url_for('admin.view_products_by_category', category_id=category_id))