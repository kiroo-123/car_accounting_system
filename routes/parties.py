# -*- coding: utf-8 -*-
"""
routes/parties.py
==================
مصنع Blueprint موحّد للعملاء / السواقين / أصحاب العربيات - نفس الهيكل
بالظبط (اسم، هاتف، ملاحظات) فبيستخدموا نفس الـ routes والـ templates.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

import data_access as da

PARTY_TYPES = {
    "customers": {
        "sheet": "Customers",
        "url_prefix": "/customers",
        "endpoint": "customers",
        "title": "العملاء",
        "singular": "عميل",
        "add_title": "إضافة عميل جديد",
        "amount_field": "revenue",
        "amount_label": "قيمة الرحلة",
        "dues_label": "إجمالي المستحق على العميل",
        "collected_label": "المحصّل من العميل",
        "pay_label": "تسجيل تحصيل من العميل",
    },
    "drivers": {
        "sheet": "Drivers",
        "url_prefix": "/drivers",
        "endpoint": "drivers",
        "title": "السواقين",
        "singular": "سواق",
        "add_title": "إضافة سواق جديد",
        "amount_field": "driver_fee",
        "amount_label": "أجر السواق",
        "dues_label": "إجمالي مستحقات السواق",
        "collected_label": "المدفوع للسواق",
        "pay_label": "تسجيل دفعة للسواق",
    },
    "owners": {
        "sheet": "Vehicle_Owners",
        "url_prefix": "/owners",
        "endpoint": "owners",
        "title": "أصحاب العربيات",
        "singular": "صاحب عربية",
        "add_title": "إضافة صاحب عربية جديد",
        "amount_field": "owner_fee",
        "amount_label": "أجرة صاحب العربية",
        "dues_label": "إجمالي مستحقات صاحب العربية",
        "collected_label": "المدفوع لصاحب العربية",
        "pay_label": "تسجيل دفعة لصاحب العربية",
    },
}


def _make_blueprint(key, cfg):
    bp = Blueprint(cfg["endpoint"], __name__, url_prefix=cfg["url_prefix"])
    sheet = cfg["sheet"]

    @bp.route("/")
    def list_view():
        search = request.args.get("q", "").strip()
        items = da.list_parties(sheet, search=search or None)
        return render_template("parties/list.html", items=items, cfg=cfg, search=search)

    @bp.route("/add", methods=["GET", "POST"])
    def add_view():
        if request.method == "POST":
            errors, new_id = da.add_party(sheet, request.form)
            if errors:
                for e in errors:
                    flash(e, "error")
                return render_template("parties/form.html", cfg=cfg, mode="add", values=request.form)
            flash(f"تم إضافة {cfg['singular']} بنجاح", "success")
            return redirect(url_for(f"{cfg['endpoint']}.detail_view", item_id=new_id))
        return render_template("parties/form.html", cfg=cfg, mode="add", values={})

    @bp.route("/<int:item_id>")
    def detail_view(item_id):
        statement = da.get_party_statement(sheet, item_id)
        if not statement:
            flash(f"{cfg['singular']} غير موجود", "error")
            return redirect(url_for(f"{cfg['endpoint']}.list_view"))
        return render_template("parties/detail.html", s=statement, cfg=cfg, item_id=item_id)

    @bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
    def edit_view(item_id):
        if request.method == "POST":
            errors = da.update_party(sheet, item_id, request.form)
            if errors:
                for e in errors:
                    flash(e, "error")
                return render_template("parties/form.html", cfg=cfg, mode="edit", values=request.form, item_id=item_id)
            flash(f"تم تعديل بيانات {cfg['singular']}", "success")
            return redirect(url_for(f"{cfg['endpoint']}.detail_view", item_id=item_id))

        item = da.get_party(sheet, item_id)
        if not item:
            flash(f"{cfg['singular']} غير موجود", "error")
            return redirect(url_for(f"{cfg['endpoint']}.list_view"))
        return render_template("parties/form.html", cfg=cfg, mode="edit", values=item, item_id=item_id)

    @bp.route("/<int:item_id>/delete", methods=["POST"])
    def delete_view(item_id):
        da.delete_party(sheet, item_id)
        flash(f"تم حذف {cfg['singular']}", "success")
        return redirect(url_for(f"{cfg['endpoint']}.list_view"))

    @bp.route("/<int:item_id>/pay", methods=["POST"])
    def pay_view(item_id):
        errors = da.add_party_payment(sheet, item_id, request.form)
        for e in errors:
            flash(e, "error")
        if not errors:
            flash("تم تسجيل الدفعة بنجاح", "success")
        return redirect(url_for(f"{cfg['endpoint']}.detail_view", item_id=item_id))

    return bp


customers_bp = _make_blueprint("customers", PARTY_TYPES["customers"])
drivers_bp = _make_blueprint("drivers", PARTY_TYPES["drivers"])
owners_bp = _make_blueprint("owners", PARTY_TYPES["owners"])
