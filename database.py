# database.py

import sqlite3
from werkzeug.security import generate_password_hash

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with open('schema.sql') as f:
        conn.executescript(f.read())

    # ডিফল্ট অ্যাডমিন তৈরি করা
    # username: admin, password: password
    try:
        conn.execute(
            "INSERT INTO admin (username, password) VALUES (?, ?)",
            ('admin', generate_password_hash('password'))
        )
        conn.commit()
        print("Default admin (user: admin, pass: password) created successfully.")
    except sqlite3.IntegrityError:
        print("Admin user already exists.")
    finally:
        conn.close()