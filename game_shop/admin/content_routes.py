from flask import render_template, request, flash, redirect, url_for
from game_shop.auth import login_required
from game_shop.db import get_db
from game_shop.admin import bp
import psycopg2.extras

# --- ব্যানার ম্যানেজমেন্ট ---
@bp.route('/banners')
@login_required
def banners():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM banners ORDER BY id DESC')
    all_banners = cursor.fetchall()
    cursor.close()
    return render_template('banners.html', banners=all_banners)

@bp.route('/banners/add', methods=['POST'])
@login_required
def add_banner():
    image_url = request.form['image_url']
    target_url = request.form.get('target_url')
    if image_url:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO banners (image_url, target_url) VALUES (%s, %s)', (image_url, target_url))
        db.commit()
        cursor.close()
        flash('নতুন ব্যানার সফলভাবে যোগ করা হয়েছে।')
    else:
        flash('ছবির URL আবশ্যক।')
    return redirect(url_for('admin.banners'))

@bp.route('/banners/edit/<int:banner_id>', methods=['GET', 'POST'])
@login_required
def edit_banner(banner_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM banners WHERE id = %s', (banner_id,))
    banner = cursor.fetchone()

    if request.method == 'POST':
        image_url = request.form['image_url']
        target_url = request.form.get('target_url')
        if image_url:
            cursor.execute('UPDATE banners SET image_url = %s, target_url = %s WHERE id = %s',
                           (image_url, target_url, banner_id))
            db.commit()
            flash('ব্যানার সফলভাবে আপডেট করা হয়েছে।')
            cursor.close()
            return redirect(url_for('admin.banners'))
        else:
            flash('ছবির URL আবশ্যক।')

    cursor.close()
    return render_template('edit_banner.html', banner=banner)

@bp.route('/banners/toggle/<int:banner_id>', methods=['POST'])
@login_required
def toggle_banner(banner_id):
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT is_active FROM banners WHERE id = %s', (banner_id,))
    banner = cursor.fetchone()
    if banner:
        new_status = 0 if banner['is_active'] == 1 else 1
        cursor.execute('UPDATE banners SET is_active = %s WHERE id = %s', (new_status, banner_id))
        db.commit()
    cursor.close()
    return redirect(url_for('admin.banners'))

@bp.route('/banners/delete/<int:banner_id>', methods=['POST'])
@login_required
def delete_banner(banner_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM banners WHERE id = %s', (banner_id,))
    db.commit()
    cursor.close()
    flash('ব্যানার সফলভাবে মুছে ফেলা হয়েছে।')
    return redirect(url_for('admin.banners'))

# --- নোটিস ম্যানেজমেন্ট ---
@bp.route('/notices')
@login_required
def notices():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM notices LIMIT 1')
    notice = cursor.fetchone()
    cursor.close()
    return render_template('notices.html', notice=notice)

@bp.route('/notices/save', methods=['POST'])
@login_required
def save_notice():
    content = request.form['content']
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if not content:
        flash('নোটিসের টেক্সট খালি রাখা যাবে না।')
        return redirect(url_for('admin.notices'))
    cursor.execute('SELECT id FROM notices LIMIT 1')
    notice = cursor.fetchone()
    if notice:
        cursor.execute('UPDATE notices SET content = %s WHERE id = %s', (content, notice['id']))
    else:
        cursor.execute('INSERT INTO notices (content) VALUES (%s)', (content,))
    db.commit()
    cursor.close()
    flash('নোটিস সফলভাবে সেভ করা হয়েছে।')
    return redirect(url_for('admin.notices'))

@bp.route('/notices/toggle', methods=['POST'])
@login_required
def toggle_notice():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT id, is_active FROM notices LIMIT 1')
    notice = cursor.fetchone()
    if notice:
        new_status = 0 if notice['is_active'] == 1 else 1
        cursor.execute('UPDATE notices SET is_active = %s WHERE id = %s', (new_status, notice['id']))
        db.commit()
    else:
        flash('প্রথমে একটি নোটিস সেভ করুন।')
    cursor.close()
    return redirect(url_for('admin.notices'))

# --- পপ-আপ মেসেজ ম্যানেজমেন্ট ---
@bp.route('/popup')
@login_required
def popup():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT * FROM popup_messages LIMIT 1')
    message = cursor.fetchone()
    cursor.close()
    return render_template('popup.html', message=message)

@bp.route('/popup/save', methods=['POST'])
@login_required
def save_popup():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    title = request.form.get('title', '')
    content = request.form['content']
    image_url = request.form.get('image_url')
    button_text = request.form.get('button_text')
    button_url = request.form.get('button_url')

    if not content:
        flash('কনটেন্ট অবশ্যই পূরণ করতে হবে।')
        return redirect(url_for('admin.popup'))

    cursor.execute('SELECT id FROM popup_messages LIMIT 1')
    message = cursor.fetchone()
    if message:
        cursor.execute(
            'UPDATE popup_messages SET title = %s, content = %s, image_url = %s, button_text = %s, button_url = %s WHERE id = %s',
            (title, content, image_url, button_text, button_url, message['id'])
        )
    else:
        cursor.execute(
            'INSERT INTO popup_messages (title, content, image_url, button_text, button_url) VALUES (%s, %s, %s, %s, %s)',
            (title, content, image_url, button_text, button_url)
        )
    db.commit()
    cursor.close()
    flash('পপ-আপ মেসেজ সফলভাবে সেভ করা হয়েছে।')
    return redirect(url_for('admin.popup'))

@bp.route('/popup/toggle', methods=['POST'])
@login_required
def toggle_popup():
    db = get_db()
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute('SELECT id, is_active FROM popup_messages LIMIT 1')
    message = cursor.fetchone()
    if message:
        new_status = 0 if message['is_active'] == 1 else 1
        cursor.execute('UPDATE popup_messages SET is_active = %s WHERE id = %s', (new_status, message['id']))
        db.commit()
    else:
        flash('প্রথমে একটি পপ-আপ মেসেজ সেভ করুন।')
    cursor.close()
    return redirect(url_for('admin.popup'))