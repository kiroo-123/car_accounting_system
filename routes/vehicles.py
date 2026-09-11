# -*- coding: utf-8 -*-
"""
routes/vehicles.py
===================
العربيات: القائمة، إضافة، تعديل، كشف حساب العربية، حذف.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

import data_access as da

vehicles_bp = Blueprint("vehicles", __name__, url_prefix="/vehicles")


@vehicles_bp.route("/")
def list_view():
    search = request.args.get("q", "").strip()
    ownership = request.args.get("ownership_type", "").strip()
    vehicles = da.list_vehicles(search=search or None, ownership_type=ownership or None)
    return render_template("vehicles/list.html", vehicles=vehicles, search=search, ownership=ownership)


@vehicles_bp.route("/add", methods=["GET", "POST"])
def add_view():
    if request.method == "POST":
        errors, new_id = da.add_vehicle(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            owners = da.list_parties("Vehicle_Owners")
            return render_template("vehicles/form.html", mode="add", values=request.form, owners=owners)
        flash("تم إضافة العربية بنجاح", "success")
        return redirect(url_for("vehicles.detail_view", vehicle_id=new_id))

    owners = da.list_parties("Vehicle_Owners")
    return render_template("vehicles/form.html", mode="add", values={}, owners=owners)


@vehicles_bp.route("/<int:vehicle_id>")
def detail_view(vehicle_id):
    statement = da.get_vehicle_statement(vehicle_id)
    if not statement:
        flash("العربية غير موجودة", "error")
        return redirect(url_for("vehicles.list_view"))
    return render_template("vehicles/detail.html", s=statement)


@vehicles_bp.route("/<int:vehicle_id>/edit", methods=["GET", "POST"])
def edit_view(vehicle_id):
    if request.method == "POST":
        errors = da.update_vehicle(vehicle_id, request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            owners = da.list_parties("Vehicle_Owners")
            return render_template("vehicles/form.html", mode="edit", values=request.form, vehicle_id=vehicle_id, owners=owners)
        flash("تم تعديل بيانات العربية", "success")
        return redirect(url_for("vehicles.detail_view", vehicle_id=vehicle_id))

    vehicle = da.get_vehicle(vehicle_id)
    if not vehicle:
        flash("العربية غير موجودة", "error")
        return redirect(url_for("vehicles.list_view"))
    owners = da.list_parties("Vehicle_Owners")
    return render_template("vehicles/form.html", mode="edit", values=vehicle, vehicle_id=vehicle_id, owners=owners)


@vehicles_bp.route("/<int:vehicle_id>/delete", methods=["POST"])
def delete_view(vehicle_id):
    da.delete_vehicle(vehicle_id)
    flash("تم حذف العربية", "success")
    return redirect(url_for("vehicles.list_view"))
