from flask import Blueprint, g
from game_shop.db import get_db
import psycopg2.extras # DictCursor ব্যবহারের জন্য

# মূল অ্যাডমিন ব্লুপ্রিন্ট তৈরি করা হচ্ছে
bp = Blueprint('admin', __name__, url_prefix='/admin')

# এই ফাংশনটি অ্যাডমিন প্যানেলের যেকোনো পেজ লোড হওয়ার আগে কাজ করবে
@bp.before_request
def load_pending_counts_for_admin():
    db = get_db()
    # execute() চালানোর জন্য একটি cursor তৈরি করতে হবে
    cursor = db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute(
        "SELECT COUNT(id) FROM orders WHERE status = 'Pending Payment'"
    )
    pending_orders_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(id) FROM wallet_transactions WHERE status = 'Pending'"
    )
    pending_deposits_count = cursor.fetchone()[0]

    # cursor ব্যবহার শেষ হলে বন্ধ করে দিতে হবে
    cursor.close()

    # গণনাকৃত সংখ্যাগুলোকে গ্লোবাল ভেরিয়েবল 'g'-তে সেভ করা হচ্ছে
    g.pending_orders_count = pending_orders_count
    g.pending_deposits_count = pending_deposits_count


# অন্য সব রাউট ফাইলকে ইম্পোর্ট করা হচ্ছে যাতে সেগুলো ব্লুপ্রিন্টের সাথে রেজিস্টার হয়ে যায়
from game_shop.admin import dashboard, game_routes, order_routes, content_routes, settings_routes, redeem_routes