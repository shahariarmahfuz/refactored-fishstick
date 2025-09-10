from flask import render_template, request, redirect, url_for, flash
from game_shop.auth import login_required
from game_shop.db import get_db
from game_shop.admin import bp
import datetime
import psycopg2.extras

@bp.route('/orders')
@login_required
def view_orders():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    status_filter = request.args.get('status', 'pending').lower()

    query = '''
        SELECT o.id, o.game_uid, o.status, o.order_time, o.payment_method, 
               o.transaction_id, o.screenshot_url, p.name as product_name, 
               p.price, c.name as category_name, g.title as game_title, u.username
        FROM orders o 
        JOIN product p ON o.product_id = p.id 
        JOIN category c ON p.category_id = c.id 
        JOIN game g ON c.game_id = g.id
        JOIN users u ON o.account_user_id = u.id
    '''
    params = []

    if status_filter == 'pending':
        query += " WHERE o.status = %s"
        params.append('Pending Payment')
    elif status_filter == 'accepted':
        query += " WHERE o.status = %s"
        params.append('Completed')
    elif status_filter == 'rejected':
        query += " WHERE o.status = %s"
        params.append('Rejected')
    
    query += ' ORDER BY o.order_time DESC'
    
    cursor.execute(query, tuple(params))
    orders = cursor.fetchall()
    cursor.close()
    
    return render_template('view_orders.html', orders=orders, current_filter=status_filter)

@bp.route('/update_order/<int:order_id>', methods=['POST'])
@login_required
def update_order(order_id):
    status = request.form['status']
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    if status == 'Rejected':
        cursor.execute(
            '''SELECT o.account_user_id, o.payment_method, p.price 
               FROM orders o JOIN product p ON o.product_id = p.id
               WHERE o.id = %s''',
            (order_id,)
        )
        order_to_reject = cursor.fetchone()

        if order_to_reject and order_to_reject['payment_method'] == 'Wallet':
            cursor.execute(
                'UPDATE users SET balance = balance + %s WHERE id = %s',
                (order_to_reject['price'], order_to_reject['account_user_id'])
            )
            flash(f"Order #{order_id} rejected. {order_to_reject['price']} Taka has been refunded to the user's wallet.")

    if status == 'Completed':
        completion_time = datetime.datetime.now()
        cursor.execute('UPDATE orders SET status = %s, completion_time = %s WHERE id = %s',
                   (status, completion_time, order_id))
    else:
        cursor.execute('UPDATE orders SET status = %s WHERE id = %s', (status, order_id))
    
    db.commit()
    cursor.close()
    return redirect(url_for('admin.view_orders'))

@bp.route('/wallet-deposits')
@login_required
def wallet_deposits():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('''
        SELECT wt.id, wt.amount, wt.status, wt.payment_method, wt.transaction_id, wt.screenshot_url, u.username
        FROM wallet_transactions wt JOIN users u ON wt.user_id = u.id
        WHERE wt.status = 'Pending'
        ORDER BY wt.request_time DESC
    ''')
    deposits = cursor.fetchall()
    cursor.close()
    return render_template('wallet_deposits.html', deposits=deposits)

@bp.route('/wallet-deposits/update/<int:deposit_id>', methods=['POST'])
@login_required
def update_deposit(deposit_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    new_status = request.form['status']
    cursor.execute('SELECT * FROM wallet_transactions WHERE id = %s', (deposit_id,))
    deposit = cursor.fetchone()

    if not deposit:
        flash('অনুরোধটি খুঁজে পাওয়া যায়নি।')
        cursor.close()
        return redirect(url_for('admin.wallet_deposits'))
    
    if new_status == 'Approved' and deposit['status'] == 'Pending':
        cursor.execute('UPDATE users SET balance = balance + %s WHERE id = %s', (deposit['amount'], deposit['user_id']))
        cursor.execute('UPDATE wallet_transactions SET status = %s WHERE id = %s', (new_status, deposit_id))
        db.commit()
        flash('অনুরোধটি Approve করা হয়েছে এবং ইউজারের ওয়ালেটে টাকা যোগ হয়েছে।')
    elif new_status == 'Rejected':
        cursor.execute('UPDATE wallet_transactions SET status = %s WHERE id = %s', (new_status, deposit_id))
        db.commit()
        flash('অনুরোধটি Reject করা হয়েছে।')
    
    cursor.close()
    return redirect(url_for('admin.wallet_deposits'))
