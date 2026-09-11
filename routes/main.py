# -*- coding: utf-8 -*-
"""
routes/main.py
===============
الرئيسية (Dashboard) + التحصيل + الإعدادات + النسخ الاحتياطي/إعادة التهيئة.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

import data_access as da

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def dashboard():
    data = da.get_dashboard_data()
    return render_template("dashboard.html", data=data)


@main_bp.route("/collection")
def collection():
    report = da.get_collection_report()
    return render_template("collection/index.html", report=report)


@main_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "set_company_name":
            da.set_company_name(request.form.get("company_name"))
            flash("تم تحديث اسم الشركة", "success")
        elif action == "add_toll_route":
            errors = da.add_toll_route(request.form.get("route_name"), request.form.get("toll_price"))
            for e in errors:
                flash(e, "error")
            if not errors:
                flash("تم إضافة المسار", "success")
        elif action == "add_maintenance_type":
            errors = da.add_maintenance_expense_type(request.form.get("type_name"))
            for e in errors:
                flash(e, "error")
            if not errors:
                flash("تم إضافة نوع المصروف", "success")
        elif action == "add_general_expense_type":
            errors = da.add_general_expense_type(request.form.get("type_name"))
            for e in errors:
                flash(e, "error")
            if not errors:
                flash("تم إضافة نوع المصروف", "success")
        return redirect(url_for("main.settings"))

    return render_template(
        "admin/settings.html",
        company_name=da.get_company_name(),
        toll_routes=da.get_toll_routes(),
        maintenance_types=da.get_maintenance_expense_types(),
        general_expense_types=da.get_general_expense_types(),
    )


@main_bp.route("/backup")
def backup_page():
    backups = da.list_backups()
    return render_template("admin/backup.html", backups=backups, db_path=str(da.db.DB_PATH))


@main_bp.route("/backup/create", methods=["POST"])
def backup_create():
    path = da.create_backup()
    if path:
        flash(f"تم إنشاء نسخة احتياطية: {path.name}", "success")
    else:
        flash("لا يوجد ملف بيانات لعمل نسخة منه بعد", "error")
    return redirect(url_for("main.backup_page"))


@main_bp.route("/system/reset", methods=["POST"])
def system_reset():
    confirm = request.form.get("confirm_text", "").strip()
    load_demo = request.form.get("load_demo") == "1"
    if confirm != "متأكد":
        flash('لازم تكتب كلمة "متأكد" بالظبط عشان تأكد إعادة التهيئة', "error")
        return redirect(url_for("main.settings"))
    da.reset_system(load_demo=load_demo)
    flash("تم إعادة تهيئة النظام. اتعمل نسخة احتياطية من البيانات القديمة قبل المسح.", "success")
    return redirect(url_for("main.dashboard"))
