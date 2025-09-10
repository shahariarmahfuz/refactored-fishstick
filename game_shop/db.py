import psycopg2
import psycopg2.extras
import click
from flask import current_app, g
from werkzeug.security import generate_password_hash

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(current_app.config['DATABASE'])
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    # নিচের এই লাইনটি ঠিক করা হয়েছে
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    cursor = db.cursor()
    with current_app.open_resource('schema.sql') as f:
        cursor.execute(f.read().decode('utf8'))

    try:
        cursor.execute(
            "INSERT INTO admin (username, password) VALUES (%s, %s)",
            ('admin', generate_password_hash('password')),
        )
    except (psycopg2.IntegrityError, psycopg2.errors.UniqueViolation):
        db.rollback()
    else:
        db.commit()

    cursor.close()

@click.command('init-db')
def init_db_command():
    """ডাটাবেসের টেবিল এবং ডিফল্ট অ্যাডমিন তৈরি করে।"""
    init_db()
    click.echo('Initialized the PostgreSQL database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)