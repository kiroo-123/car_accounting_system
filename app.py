# -*- coding: utf-8 -*-
"""
app.py
======
نقطة تشغيل النظام. لتشغيل السيرفر:  python3 app.py
هيفتح على: http://127.0.0.1:5000
"""
import webbrowser
import os
from flask import Flask, render_template

import excel_db as db

SECRET_KEY = "car-accounting-system-local-dev-key-change-if-exposed-publicly"


def format_currency(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0
    if value == int(value):
        return f"{int(value):,} جنيه"
    return f"{value:,.2f} جنيه"


def format_number(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0
    if value == int(value):
        return f"{int(value):,}"
    return f"{value:,.2f}"


def format_date_ar(value):
    """يحول تاريخ ISO (YYYY-MM-DD) لعرض بسيط، مع الحفاظ على ترتيب الفرز."""
    if not value:
        return "-"
    return str(value)


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.jinja_env.filters["currency"] = format_currency
    app.jinja_env.filters["numfmt"] = format_number
    app.jinja_env.filters["ardate"] = format_date_ar
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    from routes.main import main_bp
    from routes.trips import trips_bp
    from routes.vehicles import vehicles_bp
    from routes.parties import customers_bp, drivers_bp, owners_bp
    from routes.finance import finance_bp
    from routes.reports import reports_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(trips_bp)
    app.register_blueprint(vehicles_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(drivers_bp)
    app.register_blueprint(owners_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(reports_bp)

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404, message="الصفحة اللي بتدور عليها مش موجودة"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", code=500, message="حصل خطأ غير متوقع في النظام. جرب تاني."), 500

    @app.context_processor
    def inject_globals():
        import data_access as da
        return {"company_name": da.get_company_name(), "today": da.today_str()}

    return app


if __name__ == "__main__":
    is_new = db.init_db()
    if is_new:
        print("تم إنشاء ملف قاعدة البيانات (Excel) لأول مرة.")

    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")

    url = f"http://{host}:{port}"
    print(f"\n  النظام شغال على: {url}\n")

    # فتح النظام تلقائيًا في المتصفح الخارجي الافتراضي
    webbrowser.open(url)

    app.run(host=host, port=port, debug=False, threaded=True)   