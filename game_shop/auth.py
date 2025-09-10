import functools
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash
from game_shop.db import get_db
import psycopg2 # নতুন ইম্পোর্ট
import psycopg2.extras # নতুন ইম্পোর্ট

bp = Blueprint('auth', __name__, url_prefix='/admin')

@bp.route('/login', methods=('GET', 'POST'))
def admin_login():
    if g.user: # যদি সাধারণ ইউজার হিসেবে লগইন করা থাকে
        # অ্যাডমিন হিসেবে লগইন করার জন্য তাকে অ্যাডমিন টেবিলেও থাকতে হবে
        db = get_db()
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute('SELECT * FROM admin WHERE username = %s', (g.user['username'],))
        admin_user = cursor.fetchone()
        cursor.close()
        if admin_user:
            session['admin_id'] = admin_user['id']
            return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        error = None
        cursor.execute(
            'SELECT * FROM admin WHERE username = %s', (username,)
        )
        admin = cursor.fetchone()
        cursor.close()

        if admin is None or not check_password_hash(admin['password'], password):
            error = 'ভুল ইউজারনেম অথবা পাসওয়ার্ড।'

        if error is None:
            session.clear()
            session['admin_id'] = admin['id']
            return redirect(url_for('admin.dashboard'))

        flash(error)
    return render_template('admin_login.html')

@bp.before_app_request
def load_logged_in_admin():
    admin_id = session.get('admin_id')
    g.admin = None
    if admin_id is not None:
        db = get_db()
        cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(
            'SELECT * FROM admin WHERE id = %s', (admin_id,)
        )
        g.admin = cursor.fetchone()
        cursor.close()

@bp.route('/logout')
def logout():
    # শুধুমাত্র অ্যাডমিন সেশন ক্লিয়ার করা হবে
    session.pop('admin_id', None)
    return redirect(url_for('views.home'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.admin is None:
            return redirect(url_for('auth.admin_login'))
        return view(**kwargs)
    return wrapped_view