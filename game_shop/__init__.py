import os
from flask import Flask, render_template
import datetime
import pytz
from datetime import timedelta

def format_datetime_bst(utc_dt):
    if not utc_dt: return ""
    utc_timezone = pytz.timezone('UTC')
    if utc_dt.tzinfo is None: utc_dt = utc_timezone.localize(utc_dt)
    bst_timezone = pytz.timezone('Asia/Dhaka')
    bst_dt = utc_dt.astimezone(bst_timezone)
    return bst_dt.strftime('%d-%m-%Y, %I:%M:%S %p')

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # config.py ফাইল থেকে কনফিগারেশন লোড করা হচ্ছে
    app.config.from_pyfile(os.path.join(os.path.dirname(app.root_path), 'config.py'), silent=True)

    app.config.from_mapping(
        # SECRET_KEY সরাসরি এখানে সেট করা হয়েছে
        SECRET_KEY='আপনার জেনারেট করা শক্তিশালী কী এখানে বসান',
        DATABASE='postgresql://atopip_user:QW7SpBuDChO4yeMGMedeodl5lYEk9zYg@dpg-d2van9nfte5s73btn8hg-a.oregon-postgres.render.com/atopip',
        PERMANENT_SESSION_LIFETIME=timedelta(days=30)
    )

    if test_config is not None:
        app.config.from_mapping(test_config)

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    app.jinja_env.filters['bst_time'] = format_datetime_bst

    # ব্লুপ্রিন্ট রেজিস্টার করা
    from . import auth, admin, views, user_auth, api
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(views.bp)
    app.register_blueprint(user_auth.bp)
    app.register_blueprint(api.bp)

    app.add_url_rule('/', endpoint='index')

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    return app