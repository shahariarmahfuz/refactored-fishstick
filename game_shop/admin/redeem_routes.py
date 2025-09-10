from flask import render_template, request, flash, redirect, url_for
from game_shop.auth import login_required
from game_shop.db import get_db
from game_shop.admin import bp
import string
import random
from datetime import datetime, timedelta
import psycopg2.extras

def generate_redeem_code(length=12):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@bp.route('/redeem-codes', methods=['GET', 'POST'])
@login_required
def manage_codes():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if request.method == 'POST':
        try:
            value = float(request.form['value'])
            expiry_days = request.form.get('expiry_days')

            if value <= 0:
                flash('টাকার পরিমাণ অবশ্যই শূন্যের বেশি হতে হবে।')
                return redirect(url_for('admin.manage_codes'))

            new_code = generate_redeem_code()
            expires_at = None
            if expiry_days and expiry_days.isdigit():
                expires_at = datetime.now() + timedelta(days=int(expiry_days))

            cursor.execute(
                'INSERT INTO redeem_codes (code, value, expires_at) VALUES (%s, %s, %s)',
                (new_code, value, expires_at)
            )
            db.commit()
            flash(f"নতুন কোড '{new_code}' সফলভাবে তৈরি হয়েছে।")
        except (ValueError, TypeError):
            flash('অনুগ্রহ করে সঠিক মান লিখুন।')

        cursor.close()
        return redirect(url_for('admin.manage_codes'))

    cursor.execute('''
        SELECT rc.*, u.username as used_by_username
        FROM redeem_codes rc
        LEFT JOIN users u ON rc.used_by_id = u.id
        ORDER BY rc.created_at DESC
    ''')
    codes = cursor.fetchall()
    cursor.close()

    current_time = datetime.now()
    return render_template('manage_codes.html', codes=codes, now=current_time)