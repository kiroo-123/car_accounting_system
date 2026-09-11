# -*- coding: utf-8 -*-
"""
routes/finance.py
==================
الصيانة والمصاريف العامة.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

import data_access as da

finance_bp = Blueprint("finance", __name__)


# ---------------------------- الصيانة ----------------------------
@finance_bp.route("/maintenance")
def maintenance_list():
    vehicle_id = request.args.get("vehicle_id", "").strip()
    rows = da.list_maintenance(vehicle_id=vehicle_id or None)
    total = round(sum(r["amount"] or 0 for r in rows), 2)
    vehicles = da.list_vehicles()
    return render_template("finance/maintenance_list.html", rows=rows, total=total, vehicles=vehicles, vehicle_id=vehicle_id)


@finance_bp.route("/maintenance/add", methods=["GET", "POST"])
def maintenance_add():
    if request.method == "POST":
        errors, new_id = da.add_maintenance(request.form)
        for e in errors:
            flash(e, "error")
        if not errors:
            flash("تم تسجيل مصروف الصيانة", "success")
            return redirect(url_for("finance.maintenance_list"))
        vehicles = da.list_vehicles()
        types = da.get_maintenance_expense_types()
        return render_template("finance/maintenance_form.html", mode="add", values=request.form, vehicles=vehicles, types=types)

    vehicles = da.list_vehicles()
    types = da.get_maintenance_expense_types()
    prefill = {"vehicle_id": request.args.get("vehicle_id", "")}
    return render_template("finance/maintenance_form.html", mode="add", values=prefill, vehicles=vehicles, types=types)


@finance_bp.route("/maintenance/<int:item_id>/edit", methods=["GET", "POST"])
def maintenance_edit(item_id):
    if request.method == "POST":
        errors = da.update_maintenance(item_id, request.form)
        for e in errors:
            flash(e, "error")
        if not errors:
            flash("تم تعديل مصروف الصيانة", "success")
            return redirect(url_for("finance.maintenance_list"))
        vehicles = da.list_vehicles()
        types = da.get_maintenance_expense_types()
        return render_template("finance/maintenance_form.html", mode="edit", values=request.form, item_id=item_id, vehicles=vehicles, types=types)

    item = da.get_maintenance(item_id)
    if not item:
        flash("السجل غير موجود", "error")
        return redirect(url_for("finance.maintenance_list"))
    vehicles = da.list_vehicles()
    types = da.get_maintenance_expense_types()
    return render_template("finance/maintenance_form.html", mode="edit", values=item, item_id=item_id, vehicles=vehicles, types=types)


@finance_bp.route("/maintenance/<int:item_id>/delete", methods=["POST"])
def maintenance_delete(item_id):
    da.delete_maintenance(item_id)
    flash("تم حذف سجل الصيانة", "success")
    return redirect(url_for("finance.maintenance_list"))


# ------------------------- المصاريف العامة -------------------------
@finance_bp.route("/expenses")
def expenses_list():
    rows = da.list_expenses()
    total = round(sum(r["amount"] or 0 for r in rows), 2)
    return render_template("finance/expenses_list.html", rows=rows, total=total)


@finance_bp.route("/expenses/add", methods=["GET", "POST"])
def expenses_add():
    if request.method == "POST":
        errors, new_id = da.add_expense(request.form)
        for e in errors:
            flash(e, "error")
        if not errors:
            flash("تم تسجيل المصروف", "success")
            return redirect(url_for("finance.expenses_list"))
        types = da.get_general_expense_types()
        return render_template("finance/expenses_form.html", mode="add", values=request.form, types=types)

    types = da.get_general_expense_types()
    return render_template("finance/expenses_form.html", mode="add", values={}, types=types)


@finance_bp.route("/expenses/<int:item_id>/edit", methods=["GET", "POST"])
def expenses_edit(item_id):
    if request.method == "POST":
        errors = da.update_expense(item_id, request.form)
        for e in errors:
            flash(e, "error")
        if not errors:
            flash("تم تعديل المصروف", "success")
            return redirect(url_for("finance.expenses_list"))
        types = da.get_general_expense_types()
        return render_template("finance/expenses_form.html", mode="edit", values=request.form, item_id=item_id, types=types)

    item = da.get_expense(item_id)
    if not item:
        flash("السجل غير موجود", "error")
        return redirect(url_for("finance.expenses_list"))
    types = da.get_general_expense_types()
    return render_template("finance/expenses_form.html", mode="edit", values=item, item_id=item_id, types=types)


@finance_bp.route("/expenses/<int:item_id>/delete", methods=["POST"])
def expenses_delete(item_id):
    da.delete_expense(item_id)
    flash("تم حذف المصروف", "success")
    return redirect(url_for("finance.expenses_list"))
