from flask import render_template
from game_shop.auth import login_required
from game_shop.db import get_db
from game_shop.admin import bp
from datetime import datetime, timedelta
import psycopg2.extras

@bp.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute('SELECT COUNT(id) FROM users')
    total_users = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(id) FROM orders')
    total_orders = cursor.fetchone()[0]

    cursor.execute(
        'SELECT SUM(p.price) FROM orders o JOIN product p ON o.product_id = p.id WHERE o.status = %s',
        ('Completed',)
    )
    total_revenue = cursor.fetchone()[0] or 0.0

    one_week_ago = datetime.now() - timedelta(days=7)
    cursor.execute(
        'SELECT SUM(p.price) FROM orders o JOIN product p ON o.product_id = p.id WHERE o.status = %s AND o.completion_time >= %s',
        ('Completed', one_week_ago)
    )
    weekly_revenue = cursor.fetchone()[0] or 0.0

    one_day_ago = datetime.now() - timedelta(days=1)
    cursor.execute('SELECT COUNT(id) FROM orders WHERE order_time >= %s', (one_day_ago,))
    daily_orders = cursor.fetchone()[0]

    cursor.execute('''
        SELECT o.id, o.status, p.name as product_name, u.username
        FROM orders o 
        JOIN product p ON o.product_id = p.id
        JOIN users u ON o.account_user_id = u.id
        ORDER BY o.order_time DESC
        LIMIT 5
    ''')
    recent_orders = cursor.fetchall()
    cursor.close()

    stats = {
        'total_users': total_users,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'weekly_revenue': weekly_revenue,
        'daily_orders': daily_orders
    }

    return render_template('dashboard.html', stats=stats, recent_orders=recent_orders)