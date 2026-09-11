# -*- coding: utf-8 -*-
"""
routes/trips.py
================
الرحلات: القائمة (مع فلاتر وبحث)، إضافة، تعديل، تفاصيل، حذف.
"""
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash

import data_access as da

trips_bp = Blueprint("trips", __name__, url_prefix="/trips")


def _form_context():
    """المتغيرات المشتركة اللازمة لعرض فورم إضافة/تعديل رحلة."""
    return {
        "lookup": da.get_form_lookup_data(),
        "toll_routes": da.get_toll_routes(),
        "vehicles_map": json.dumps(da.get_vehicles_js_map(), ensure_ascii=False),
        "toll_map": json.dumps(da.get_toll_routes_js_map(), ensure_ascii=False),
    }


@trips_bp.route("/")
def list_view():
    filters = {
        "date_from": request.args.get("date_from", "").strip(),
        "date_to": request.args.get("date_to", "").strip(),
        "customer_id": request.args.get("customer_id", "").strip(),
        "vehicle_id": request.args.get("vehicle_id", "").strip(),
        "driver_id": request.args.get("driver_id", "").strip(),
        "owner_id": request.args.get("owner_id", "").strip(),
        "q": request.args.get("q", "").strip(),
    }
    filters = {k: v for k, v in filters.items() if v}
    trips = da.list_trips(filters)
    lookup = da.get_form_lookup_data()
    total_revenue = round(sum(t["revenue"] for t in trips), 2)
    total_profit = round(sum(t["net_profit"] for t in trips), 2)
    return render_template(
        "trips/list.html", trips=trips, lookup=lookup, filters=request.args,
        total_revenue=total_revenue, total_profit=total_profit,
    )


@trips_bp.route("/add", methods=["GET", "POST"])
def add_view():
    if request.method == "POST":
        errors, new_id = da.add_trip(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("trips/form.html", mode="add", values=request.form, **_form_context())
        flash(f"تم تسجيل الرحلة رقم {new_id} بنجاح", "success")
        return redirect(url_for("trips.detail_view", trip_id=new_id))

    return render_template("trips/form.html", mode="add", values={}, **_form_context())


@trips_bp.route("/<int:trip_id>")
def detail_view(trip_id):
    ctx = da.get_trip(trip_id)
    if not ctx:
        flash("الرحلة غير موجودة", "error")
        return redirect(url_for("trips.list_view"))
    return render_template("trips/detail.html", ctx=ctx)


@trips_bp.route("/<int:trip_id>/edit", methods=["GET", "POST"])
def edit_view(trip_id):
    if request.method == "POST":
        errors = da.update_trip(trip_id, request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("trips/form.html", mode="edit", values=request.form, trip_id=trip_id, **_form_context())
        flash("تم تعديل الرحلة بنجاح", "success")
        return redirect(url_for("trips.detail_view", trip_id=trip_id))

    ctx = da.get_trip(trip_id)
    if not ctx:
        flash("الرحلة غير موجودة", "error")
        return redirect(url_for("trips.list_view"))
    return render_template("trips/form.html", mode="edit", values=ctx["trip"], trip_id=trip_id, **_form_context())


@trips_bp.route("/<int:trip_id>/delete", methods=["POST"])
def delete_view(trip_id):
    da.delete_trip(trip_id)
    flash("تم حذف الرحلة", "success")
    return redirect(url_for("trips.list_view"))
