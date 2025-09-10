from flask import render_template, request, flash, redirect, url_for
from game_shop.auth import login_required
from game_shop.db import get_db
from game_shop.admin import bp
import psycopg2.extras

@bp.route('/payment-settings', methods=['GET', 'POST'])
@login_required
def payment_settings():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        methods = ['bKash', 'Nagad']
        for method_name in methods:
            number = request.form.get(f'{method_name}_number')
            if number:
                cursor.execute('SELECT id FROM payment_methods WHERE name = %s', (method_name,))
                exists = cursor.fetchone()
                if exists:
                    cursor.execute('UPDATE payment_methods SET account_number = %s WHERE name = %s', (number, method_name))
                else:
                    cursor.execute('INSERT INTO payment_methods (name, account_number) VALUES (%s, %s)', (method_name, number))
        db.commit()
        flash('পেমেন্ট নম্বর সফলভাবে আপডেট করা হয়েছে।')
        cursor.close()
        return redirect(url_for('admin.payment_settings'))

    cursor.execute('SELECT name, account_number FROM payment_methods')
    settings = cursor.fetchall()
    cursor.close()
    payment_data = {setting['name']: setting['account_number'] for setting in settings}
    return render_template('payment_settings.html', settings=payment_data)

@bp.route('/manage-wallets', methods=['GET', 'POST'])
@login_required
def manage_wallets():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        user_id = request.form['user_id']
        new_balance = request.form['balance']
        try:
            balance_float = float(new_balance)
            cursor.execute('UPDATE users SET balance = %s WHERE id = %s', (balance_float, user_id))
            db.commit()
            flash('ইউজারের ব্যালেন্স সফলভাবে আপডেট করা হয়েছে।')
        except ValueError:
            flash('অনুগ্রহ করে সঠিক সংখ্যা লিখুন।')
        cursor.close()
        return redirect(url_for('admin.manage_wallets'))

    cursor.execute('SELECT id, username, balance FROM users ORDER BY username')
    users = cursor.fetchall()
    cursor.close()
    return render_template('manage_wallets.html', users=users)