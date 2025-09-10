import functools
import os
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.security import check_password_hash, generate_password_hash
from game_shop.db import get_db
from datetime import datetime, timedelta
from game_shop.image_uploader import upload_image_to_xenko

# Flask-WTF থেকে ইম্পোর্ট (ফর্ম সুরক্ষার জন্য)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FloatField
from wtforms.validators import DataRequired, Length, NumberRange
import psycopg2
import psycopg2.extras

bp = Blueprint('user_auth', __name__, url_prefix='/user')

# Form Classes
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Log In')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Register')

class AddFundsForm(FlaskForm):
    amount = FloatField('Amount', validators=[DataRequired(message="Please enter an amount."), NumberRange(min=1, message="Amount must be greater than zero.")])
    submit = SubmitField('Next Step')

class RedeemForm(FlaskForm):
    code = StringField('Redeem Code', validators=[DataRequired(message="Please enter a redeem code.")])
    submit = SubmitField('Redeem Now')


@bp.route('/register', methods=('GET', 'POST'))
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)",
                (username, generate_password_hash(password)),
            )
            db.commit()
        except (psycopg2.IntegrityError, psycopg2.errors.UniqueViolation):
            db.rollback()
            flash(f"User '{username}' is already registered.")
        else:
            flash('Registration successful! Please log in.')
            return redirect(url_for("user_auth.login"))
        finally:
            cursor.close()
    return render_template('register.html', form=form)

@bp.route('/login', methods=('GET', 'POST'))
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember = form.remember_me.data
        db = get_db()
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password'], password):
            session.clear()
            session['user_id'] = user['id']
            if remember:
                session.permanent = True
            return redirect(url_for('views.home'))
        else:
            flash('Incorrect username or password.')
    return render_template('login.html', form=form)

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')
    g.user = None
    if user_id is not None:
        db = get_db()
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        g.user = cursor.fetchone()
        cursor.close()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('views.home'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash('এই পেজটি দেখার জন্য আপনাকে লগইন করতে হবে।')
            return redirect(url_for('user_auth.login'))
        return view(**kwargs)
    return wrapped_view

# --- Wallet Management (User) ---
@bp.route('/wallet')
@login_required
def wallet():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    filter_status = request.args.get('filter', 'all')
    query = 'SELECT amount, status, request_time FROM wallet_transactions WHERE user_id = %s'
    params = [g.user['id']]
    if filter_status != 'all':
        query += ' AND status = %s'
        params.append(filter_status)
    query += ' ORDER BY request_time DESC'
    cursor.execute(query, tuple(params))
    transactions = cursor.fetchall()
    cursor.close()
    return render_template('wallet.html', user=g.user, transactions=transactions, filter=filter_status)

@bp.route('/wallet/add-funds', methods=['GET', 'POST'])
@login_required
def add_funds():
    form = AddFundsForm()
    if form.validate_on_submit():
        amount = form.amount.data
        return redirect(url_for('user_auth.add_funds_payment', amount=amount))
    return render_template('add_funds.html', form=form)

@bp.route('/wallet/add-funds/<float:amount>')
@login_required
def add_funds_payment(amount):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT name FROM payment_methods WHERE is_active = 1')
    payment_methods = cursor.fetchall()
    cursor.close()
    return render_template('select_payment_wallet.html', amount=amount, payment_methods=payment_methods)

@bp.route('/wallet/payment/<float:amount>/<string:method>')
@login_required
def add_funds_payment_page(amount, method):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM payment_methods WHERE name = %s AND is_active = 1', (method,))
    payment_method = cursor.fetchone()
    cursor.close()
    if not payment_method:
        flash('পেমেন্ট মেথড খুঁজে পাওয়া যায়নি।')
        return redirect(url_for('user_auth.wallet'))
    return render_template('checkout_wallet.html', amount=amount, payment_method=payment_method)

@bp.route('/wallet/submit-deposit/<float:amount>', methods=['POST'])
@login_required
def submit_deposit(amount):
    db = get_db()
    cursor = db.cursor()
    payment_method = request.form.get('payment_method')
    transaction_id = request.form.get('transaction_id')
    screenshot = request.files.get('screenshot')
    screenshot_url = None

    if not transaction_id and (not screenshot or screenshot.filename == ''):
        flash('অনুগ্রহ করে ট্রানজেকশন আইডি দিন অথবা স্ক্রিনশট আপলোড করুন।')
        return redirect(url_for('user_auth.add_funds_payment_page', amount=amount, method=payment_method))

    if screenshot and screenshot.filename != '':
        uploaded_url = upload_image_to_xenko(screenshot)
        if uploaded_url:
            screenshot_url = uploaded_url
        else:
            flash('দুঃখিত, ছবিটি আপলোড করা সম্ভব হয়নি। অনুগ্রহ করে আবার চেষ্টা করুন।')
            return redirect(url_for('user_auth.add_funds_payment_page', amount=amount, method=payment_method))

    cursor.execute(
        'INSERT INTO wallet_transactions (user_id, amount, payment_method, transaction_id, screenshot_url) VALUES (%s, %s, %s, %s, %s)',
        (g.user['id'], amount, payment_method, transaction_id, screenshot_url)
    )
    db.commit()
    cursor.close()
    flash('আপনার টাকা যোগ করার অনুরোধটি সফলভাবে জমা দেওয়া হয়েছে।')
    return redirect(url_for('user_auth.wallet'))

# --- My Account ---
@bp.route('/account')
@login_required
def my_account():
    db = get_db()
    cursor = db.cursor()
    user_id = g.user['id']
    cursor.execute(
        'SELECT SUM(p.price) FROM orders o JOIN product p ON o.product_id = p.id WHERE o.account_user_id = %s AND o.status = %s',
        (user_id, 'Completed')
    )
    total_spent = cursor.fetchone()[0] or 0.0
    one_week_ago = datetime.now() - timedelta(days=7)
    cursor.execute(
        'SELECT SUM(p.price) FROM orders o JOIN product p ON o.product_id = p.id WHERE o.account_user_id = %s AND o.status = %s AND o.completion_time >= %s',
        (user_id, 'Completed', one_week_ago)
    )
    weekly_spent = cursor.fetchone()[0] or 0.0
    cursor.execute('SELECT COUNT(id) FROM orders WHERE account_user_id = %s', (user_id,))
    total_orders = cursor.fetchone()[0]
    cursor.close()
    stats = { 'total_spent': total_spent, 'weekly_spent': weekly_spent, 'total_orders': total_orders }
    return render_template('my_account.html', user=g.user, stats=stats)

# --- Redeem Code (User) ---
@bp.route('/redeem', methods=['GET', 'POST'])
@login_required
def redeem():
    form = RedeemForm()
    if form.validate_on_submit():
        code = form.code.data.upper().strip()
        db = get_db()
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM redeem_codes WHERE code = %s', (code,))
        redeem_code = cursor.fetchone()
        error = None
        if not redeem_code: error = 'ভুল কোড।'
        elif redeem_code['is_used'] == 1: error = 'এই কোডটি ইতিমধ্যে ব্যবহৃত হয়েছে।'
        elif redeem_code['expires_at'] and datetime.now() > redeem_code['expires_at']: error = 'এই কোডটির মেয়াদ শেষ হয়ে গেছে।'
        if error:
            flash(error)
        else:
            cursor.execute('UPDATE users SET balance = balance + %s WHERE id = %s', (redeem_code['value'], g.user['id']))
            cursor.execute('UPDATE redeem_codes SET is_used = 1, used_by_id = %s, used_at = %s WHERE id = %s',
                           (g.user['id'], datetime.now(), redeem_code['id']))
            db.commit()
            flash(f'{redeem_code["value"]} টাকা আপনার ওয়ালেটে সফলভাবে যোগ করা হয়েছে!')
        cursor.close()
        return redirect(url_for('user_auth.wallet'))
    return render_template('redeem.html', form=form)