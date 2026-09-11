# -*- coding: utf-8 -*-
"""
data_access.py
===============
طبقة الوصول للبيانات: كل عمليات الإضافة/التعديل/الحذف/الاستعلام
لكل كيانات النظام (عملاء، عربيات، أصحاب عربيات، سواقين، رحلات،
صيانة، مصاريف، تحصيلات) + التقارير + بيانات الداشبورد.

كل دالة هنا هي "الباب الوحيد" للتعامل مع نوع بيانات معين - الـ routes
منادية على الدوال دي بس، ومفيش أي route بيلمس excel_db مباشرة.
كل الحسابات المالية بتتم فعليًا في calculations.py، الملف ده بس بيجمّع
البيانات ويناديها.
"""

from datetime import datetime, date

import excel_db as db
import calculations as calc

PARTY_SHEETS = {
    "customer": "Customers",
    "owner": "Vehicle_Owners",
    "driver": "Drivers",
}
PARTY_LABELS = {
    "Customers": "العميل",
    "Vehicle_Owners": "صاحب العربية",
    "Drivers": "السواق",
}


def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def today_str():
    return date.today().strftime("%Y-%m-%d")


def month_prefix(d=None):
    return (d or today_str())[:7]


# ===========================================================================
# أصحاب العلاقة العامة (عملاء / أصحاب عربيات / سواقين) - CRUD موحّد
# نفس الهيكل بالظبط: id, name, phone, notes, is_deleted, created_at
# ===========================================================================
def list_parties(sheet_name, search=None):
    with db.read_only() as wb:
        rows = db.get_all(wb, sheet_name)
    if search:
        s = search.strip().lower()
        rows = [r for r in rows if s in str(r.get("name", "")).lower() or s in str(r.get("phone", "")).lower()]
    rows.sort(key=lambda r: str(r.get("name", "")))
    return rows


def get_party(sheet_name, item_id):
    with db.read_only() as wb:
        return db.get_by_id(wb, sheet_name, item_id, include_deleted=True)


def add_party(sheet_name, form):
    name = (form.get("name") or "").strip()
    errors = []
    if not name:
        errors.append(f"لازم تكتب {PARTY_LABELS.get(sheet_name, 'الاسم')}")
    if errors:
        return errors, None
    with db.transaction() as wb:
        new_id = db.get_next_id(wb, sheet_name, start=1)
        db.append_row(wb, sheet_name, {
            "id": new_id,
            "name": name,
            "phone": (form.get("phone") or "").strip(),
            "notes": (form.get("notes") or "").strip(),
            "is_deleted": False,
            "created_at": now_str(),
        })
    return [], new_id


def update_party(sheet_name, item_id, form):
    name = (form.get("name") or "").strip()
    errors = []
    if not name:
        errors.append(f"لازم تكتب {PARTY_LABELS.get(sheet_name, 'الاسم')}")
    if errors:
        return errors
    with db.transaction() as wb:
        ok = db.update_row(wb, sheet_name, item_id, {
            "name": name,
            "phone": (form.get("phone") or "").strip(),
            "notes": (form.get("notes") or "").strip(),
        })
        if not ok:
            errors.append("العنصر غير موجود")
    return errors


def delete_party(sheet_name, item_id):
    with db.transaction() as wb:
        db.soft_delete(wb, sheet_name, item_id)


def _vehicle_ids_for_owner(vehicles, owner_id):
    return {
        str(v["id"]) for v in vehicles
        if str(v.get("owner_id")) == str(owner_id) and v.get("ownership_type") == "free"
    }


def get_customer_statement(customer_id):
    with db.read_only() as wb:
        customer = db.get_by_id(wb, "Customers", customer_id, include_deleted=True)
        if not customer:
            return None
        trips = [t for t in db.get_all(wb, "Trips") if str(t.get("customer_id")) == str(customer_id)]
        payments = [p for p in db.get_all(wb, "Customer_Payments") if str(p.get("customer_id")) == str(customer_id)]
        vehicles = {str(v["id"]): v for v in db.get_all(wb, "Vehicles", include_deleted=True)}
        drivers = {str(d["id"]): d for d in db.get_all(wb, "Drivers", include_deleted=True)}
    return _build_statement(customer, trips, payments, vehicles, drivers, {}, amount_field="revenue")


def get_owner_statement(owner_id):
    with db.read_only() as wb:
        owner = db.get_by_id(wb, "Vehicle_Owners", owner_id, include_deleted=True)
        if not owner:
            return None
        vehicles_all = db.get_all(wb, "Vehicles", include_deleted=True)
        vehicles = {str(v["id"]): v for v in vehicles_all}
        owner_vehicle_ids = _vehicle_ids_for_owner(vehicles_all, owner_id)
        trips = [t for t in db.get_all(wb, "Trips") if str(t.get("vehicle_id")) in owner_vehicle_ids]
        payments = [p for p in db.get_all(wb, "Owner_Payments") if str(p.get("owner_id")) == str(owner_id)]
        customers = {str(c["id"]): c for c in db.get_all(wb, "Customers", include_deleted=True)}
    return _build_statement(owner, trips, payments, vehicles, {}, customers, amount_field="owner_fee")


def get_driver_statement(driver_id):
    with db.read_only() as wb:
        driver = db.get_by_id(wb, "Drivers", driver_id, include_deleted=True)
        if not driver:
            return None
        trips = [t for t in db.get_all(wb, "Trips") if str(t.get("driver_id")) == str(driver_id)]
        payments = [p for p in db.get_all(wb, "Driver_Payments") if str(p.get("driver_id")) == str(driver_id)]
        vehicles = {str(v["id"]): v for v in db.get_all(wb, "Vehicles", include_deleted=True)}
        customers = {str(c["id"]): c for c in db.get_all(wb, "Customers", include_deleted=True)}
    return _build_statement(driver, trips, payments, vehicles, {}, customers, amount_field="driver_fee")


def _build_statement(entity, trips, payments, vehicles, drivers, customers, amount_field):
    trips = sorted(trips, key=lambda t: str(t.get("date", "")), reverse=True)
    totals = calc.sum_trip_financials(trips, vehicles_by_id=vehicles)
    total_paid = calc.sum_amounts(payments)
    total_dues = totals["revenue"] if amount_field == "revenue" else totals[amount_field]
    remaining = calc.compute_dues(total_dues, total_paid)
    trip_rows = []
    for t in trips:
        vehicle = vehicles.get(str(t.get("vehicle_id")))
        fin = calc.compute_trip_financials(t, vehicle=vehicle)
        row = {**t, **fin}
        row["vehicle_name"] = (vehicle.get("code_name") or vehicle.get("plate_number")) if vehicle else "-"
        if drivers:
            row["driver_name"] = drivers.get(str(t.get("driver_id")), {}).get("name", "-")
        if customers:
            row["customer_name"] = customers.get(str(t.get("customer_id")), {}).get("name", "-")
        row["amount"] = fin[amount_field]
        trip_rows.append(row)
    return {
        "entity": entity,
        "trips": trip_rows,
        "payments": sorted(payments, key=lambda p: str(p.get("date", "")), reverse=True),
        "trip_count": totals["trip_count"],
        "total_dues": round(total_dues, 2),
        "total_collected": total_paid,
        "remaining": remaining,
    }


def get_party_statement(sheet_name, item_id):
    if sheet_name == "Customers":
        return get_customer_statement(item_id)
    if sheet_name == "Vehicle_Owners":
        return get_owner_statement(item_id)
    if sheet_name == "Drivers":
        return get_driver_statement(item_id)
    return None


def add_customer_payment(customer_id, form):
    return _add_payment("Customer_Payments", "customer_id", "Customers", customer_id, form)


def add_owner_payment(owner_id, form):
    return _add_payment("Owner_Payments", "owner_id", "Vehicle_Owners", owner_id, form)


def add_driver_payment(driver_id, form):
    return _add_payment("Driver_Payments", "driver_id", "Drivers", driver_id, form)


def _add_payment(payments_sheet, fk_field, party_sheet, party_id, form):
    errors = []
    amount_raw = (form.get("amount") or "").strip()
    amount_val = 0
    try:
        amount_val = float(amount_raw)
        if amount_val <= 0:
            errors.append("المبلغ لازم يكون أكبر من صفر")
    except ValueError:
        errors.append("المبلغ لازم يكون رقم")
    if not (form.get("date") or "").strip():
        errors.append("لازم تحدد تاريخ الدفع")
    if errors:
        return errors
    with db.transaction() as wb:
        party = db.get_by_id(wb, party_sheet, party_id, include_deleted=True)
        if not party:
            return ["العنصر غير موجود"]
        new_id = db.get_next_id(wb, payments_sheet, start=1)
        db.append_row(wb, payments_sheet, {
            "id": new_id,
            fk_field: party_id,
            "date": form.get("date"),
            "amount": round(amount_val, 2),
            "method": form.get("method") or "كاش",
            "notes": (form.get("notes") or "").strip(),
            "is_deleted": False,
            "created_at": now_str(),
        })
        _refresh_monthly_summary(wb)
    return []


def add_party_payment(sheet_name, item_id, form):
    if sheet_name == "Customers":
        return add_customer_payment(item_id, form)
    if sheet_name == "Vehicle_Owners":
        return add_owner_payment(item_id, form)
    if sheet_name == "Drivers":
        return add_driver_payment(item_id, form)
    return ["نوع غير معروف"]


# ===========================================================================
# العربيات
# ===========================================================================
def list_vehicles(search=None, ownership_type=None, include_deleted=False):
    with db.read_only() as wb:
        rows = db.get_all(wb, "Vehicles", include_deleted=include_deleted)
        owners = {str(o["id"]): o for o in db.get_all(wb, "Vehicle_Owners", include_deleted=True)}
    if ownership_type:
        rows = [r for r in rows if r.get("ownership_type") == ownership_type]
    if search:
        s = search.strip().lower()
        rows = [r for r in rows if s in str(r.get("plate_number", "")).lower() or s in str(r.get("code_name", "")).lower()]
    for r in rows:
        owner = owners.get(str(r.get("owner_id")))
        r["owner_name"] = owner.get("name") if owner else None
        r["ownership_label"] = "ملك الشركة" if r.get("ownership_type") == "company" else "عربية حرة"
    rows.sort(key=lambda r: str(r.get("code_name") or r.get("plate_number") or ""))
    return rows


def get_vehicle(vehicle_id):
    with db.read_only() as wb:
        return db.get_by_id(wb, "Vehicles", vehicle_id, include_deleted=True)


def validate_vehicle_form(form):
    errors = []
    plate = (form.get("plate_number") or "").strip()
    code_name = (form.get("code_name") or "").strip()
    ownership_type = form.get("ownership_type") or "company"
    if not plate and not code_name:
        errors.append("لازم تكتب رقم اللوحة أو اسم/كود العربية")
    if ownership_type not in ("company", "free"):
        errors.append("نوع الملكية لازم يكون ملك الشركة أو عربية حرة")
    if ownership_type == "free" and not (form.get("owner_id") or "").strip():
        errors.append("لازم تختار صاحب العربية للعربيات الحرة")
    return errors


def add_vehicle(form):
    errors = validate_vehicle_form(form)
    if errors:
        return errors, None
    ownership_type = form.get("ownership_type") or "company"
    owner_id = form.get("owner_id") if ownership_type == "free" else ""
    with db.transaction() as wb:
        new_id = db.get_next_id(wb, "Vehicles", start=1)
        db.append_row(wb, "Vehicles", {
            "id": new_id,
            "plate_number": (form.get("plate_number") or "").strip(),
            "code_name": (form.get("code_name") or "").strip(),
            "vehicle_type": (form.get("vehicle_type") or "").strip(),
            "capacity": (form.get("capacity") or "").strip(),
            "ownership_type": ownership_type,
            "owner_id": owner_id or "",
            "status": form.get("status") or "نشطة",
            "notes": (form.get("notes") or "").strip(),
            "is_deleted": False,
            "created_at": now_str(),
        })
    return [], new_id


def update_vehicle(vehicle_id, form):
    errors = validate_vehicle_form(form)
    if errors:
        return errors
    ownership_type = form.get("ownership_type") or "company"
    owner_id = form.get("owner_id") if ownership_type == "free" else ""
    with db.transaction() as wb:
        ok = db.update_row(wb, "Vehicles", vehicle_id, {
            "plate_number": (form.get("plate_number") or "").strip(),
            "code_name": (form.get("code_name") or "").strip(),
            "vehicle_type": (form.get("vehicle_type") or "").strip(),
            "capacity": (form.get("capacity") or "").strip(),
            "ownership_type": ownership_type,
            "owner_id": owner_id or "",
            "status": form.get("status") or "نشطة",
            "notes": (form.get("notes") or "").strip(),
        })
        if not ok:
            errors.append("العربية غير موجودة")
    return errors


def delete_vehicle(vehicle_id):
    with db.transaction() as wb:
        db.soft_delete(wb, "Vehicles", vehicle_id)


def get_vehicle_statement(vehicle_id):
    with db.read_only() as wb:
        vehicle = db.get_by_id(wb, "Vehicles", vehicle_id, include_deleted=True)
        if not vehicle:
            return None
        trips = [t for t in db.get_all(wb, "Trips") if str(t.get("vehicle_id")) == str(vehicle_id)]
        maintenance = [m for m in db.get_all(wb, "Maintenance") if str(m.get("vehicle_id")) == str(vehicle_id)]
        customers = {str(c["id"]): c for c in db.get_all(wb, "Customers", include_deleted=True)}
        drivers = {str(d["id"]): d for d in db.get_all(wb, "Drivers", include_deleted=True)}
        owners = {str(o["id"]): o for o in db.get_all(wb, "Vehicle_Owners", include_deleted=True)}
    trips = sorted(trips, key=lambda t: str(t.get("date", "")), reverse=True)
    totals = calc.sum_trip_financials(trips, vehicles_by_id={str(vehicle_id): vehicle})
    maint_total = calc.sum_amounts(maintenance)
    total_cost = round(totals["total_cost"] + maint_total, 2)
    net_profit = round(totals["revenue"] - total_cost, 2)
    trip_rows = []
    for t in trips:
        fin = calc.compute_trip_financials(t, vehicle=vehicle)
        trip_rows.append({
            **t, **fin,
            "customer_name": customers.get(str(t.get("customer_id")), {}).get("name", "-"),
            "driver_name": drivers.get(str(t.get("driver_id")), {}).get("name", "-"),
        })
    owner = owners.get(str(vehicle.get("owner_id")))
    return {
        "vehicle": vehicle,
        "owner_name": owner.get("name") if owner else None,
        "owner_id": owner.get("id") if owner else None,
        "trips": trip_rows,
        "maintenance": sorted(maintenance, key=lambda m: str(m.get("date", "")), reverse=True),
        "trip_count": totals["trip_count"],
        "revenue": totals["revenue"],
        "fuel_cost": totals["fuel_cost"],
        "toll_cost": totals["toll_cost"],
        "driver_cost": totals["driver_fee"],
        "owner_cost": totals["owner_fee"],
        "maintenance_cost": maint_total,
        "total_cost": total_cost,
        "net_profit": net_profit,
    }


# ===========================================================================
# الرحلات
# ===========================================================================
NUMERIC_TRIP_FIELDS = [
    ("trip_price", "سعر الرحلة"),
    ("owner_fee", "أجرة صاحب العربية"),
    ("driver_fee", "أجر السواق"),
    ("fuel_liters", "لترات السولار"),
    ("fuel_price_per_liter", "سعر لتر السولار"),
    ("toll_cost", "الكارتة"),
    ("commission", "العمولة"),
]


def validate_trip_form(form):
    errors = []
    if not (form.get("customer_id") or "").strip():
        errors.append("لازم تختار العميل")
    if not (form.get("vehicle_id") or "").strip():
        errors.append("لازم تختار العربية")
    if not (form.get("date") or "").strip():
        errors.append("لازم تحدد تاريخ الرحلة")
    for field, label in NUMERIC_TRIP_FIELDS:
        val = (form.get(field) or "").strip()
        if val == "":
            continue
        try:
            fval = float(val)
            if fval < 0:
                errors.append(f"{label} لازم يكون رقم موجب")
        except ValueError:
            errors.append(f"{label} لازم يكون رقم")
    return errors


def _raw_trip_values(form):
    return {
        "trip_price": form.get("trip_price") or 0,
        "owner_fee": form.get("owner_fee") or 0,
        "driver_fee": form.get("driver_fee") or 0,
        "fuel_liters": form.get("fuel_liters") or 0,
        "fuel_price_per_liter": form.get("fuel_price_per_liter") or 0,
        "toll_cost": form.get("toll_cost") or 0,
        "commission": form.get("commission") or 0,
    }


def add_trip(form):
    errors = validate_trip_form(form)
    if errors:
        return errors, None
    with db.transaction() as wb:
        vehicle = db.get_by_id(wb, "Vehicles", form.get("vehicle_id"), include_deleted=True)
        if not vehicle:
            return ["العربية غير موجودة"], None
        customer = db.get_by_id(wb, "Customers", form.get("customer_id"), include_deleted=True)
        if not customer:
            return ["العميل غير موجود"], None
        fin = calc.compute_trip_financials(_raw_trip_values(form), vehicle=vehicle)
        new_id = db.get_next_id(wb, "Trips", start=10001)
        db.append_row(wb, "Trips", {
            "id": new_id,
            "date": form.get("date"),
            "customer_id": form.get("customer_id"),
            "vehicle_id": form.get("vehicle_id"),
            "driver_id": form.get("driver_id") or "",
            "route_name": (form.get("route_name") or "").strip(),
            "trip_price": fin["trip_price"],
            "owner_fee": fin["owner_fee"],
            "driver_fee": fin["driver_fee"],
            "fuel_liters": fin["fuel_liters"],
            "fuel_price_per_liter": fin["fuel_price_per_liter"],
            "fuel_cost": fin["fuel_cost"],
            "toll_cost": fin["toll_cost"],
            "commission": fin["commission"],
            "total_cost": fin["total_cost"],
            "net_profit": fin["net_profit"],
            "notes": (form.get("notes") or "").strip(),
            "is_deleted": False,
            "created_at": now_str(),
            "updated_at": now_str(),
        })
        _refresh_monthly_summary(wb)
    return [], new_id


def update_trip(trip_id, form):
    errors = validate_trip_form(form)
    if errors:
        return errors
    with db.transaction() as wb:
        existing = db.get_by_id(wb, "Trips", trip_id, include_deleted=True)
        if not existing:
            return ["الرحلة غير موجودة"]
        vehicle = db.get_by_id(wb, "Vehicles", form.get("vehicle_id"), include_deleted=True)
        if not vehicle:
            return ["العربية غير موجودة"]
        fin = calc.compute_trip_financials(_raw_trip_values(form), vehicle=vehicle)
        db.update_row(wb, "Trips", trip_id, {
            "date": form.get("date"),
            "customer_id": form.get("customer_id"),
            "vehicle_id": form.get("vehicle_id"),
            "driver_id": form.get("driver_id") or "",
            "route_name": (form.get("route_name") or "").strip(),
            "trip_price": fin["trip_price"],
            "owner_fee": fin["owner_fee"],
            "driver_fee": fin["driver_fee"],
            "fuel_liters": fin["fuel_liters"],
            "fuel_price_per_liter": fin["fuel_price_per_liter"],
            "fuel_cost": fin["fuel_cost"],
            "toll_cost": fin["toll_cost"],
            "commission": fin["commission"],
            "total_cost": fin["total_cost"],
            "net_profit": fin["net_profit"],
            "notes": (form.get("notes") or "").strip(),
            "updated_at": now_str(),
        })
        _refresh_monthly_summary(wb)
    return []


def delete_trip(trip_id):
    with db.transaction() as wb:
        db.soft_delete(wb, "Trips", trip_id)
        _refresh_monthly_summary(wb)


def get_trip(trip_id):
    with db.read_only() as wb:
        trip = db.get_by_id(wb, "Trips", trip_id, include_deleted=True)
        if not trip:
            return None
        vehicle = db.get_by_id(wb, "Vehicles", trip.get("vehicle_id"), include_deleted=True)
        customer = db.get_by_id(wb, "Customers", trip.get("customer_id"), include_deleted=True)
        driver = db.get_by_id(wb, "Drivers", trip.get("driver_id"), include_deleted=True) if trip.get("driver_id") else None
        owner = None
        if vehicle and vehicle.get("owner_id"):
            owner = db.get_by_id(wb, "Vehicle_Owners", vehicle.get("owner_id"), include_deleted=True)
    fin = calc.compute_trip_financials(trip, vehicle=vehicle)
    return {"trip": trip, "fin": fin, "vehicle": vehicle, "customer": customer, "driver": driver, "owner": owner}


def list_trips(filters=None):
    filters = filters or {}
    with db.read_only() as wb:
        trips = db.get_all(wb, "Trips")
        vehicles = {str(v["id"]): v for v in db.get_all(wb, "Vehicles", include_deleted=True)}
        customers = {str(c["id"]): c for c in db.get_all(wb, "Customers", include_deleted=True)}
        drivers = {str(d["id"]): d for d in db.get_all(wb, "Drivers", include_deleted=True)}

    if filters.get("date_from"):
        trips = [t for t in trips if str(t.get("date", "")) >= filters["date_from"]]
    if filters.get("date_to"):
        trips = [t for t in trips if str(t.get("date", "")) <= filters["date_to"]]
    if filters.get("customer_id"):
        trips = [t for t in trips if str(t.get("customer_id")) == str(filters["customer_id"])]
    if filters.get("vehicle_id"):
        trips = [t for t in trips if str(t.get("vehicle_id")) == str(filters["vehicle_id"])]
    if filters.get("driver_id"):
        trips = [t for t in trips if str(t.get("driver_id")) == str(filters["driver_id"])]
    if filters.get("owner_id"):
        owner_vehicle_ids = {str(v["id"]) for v in vehicles.values() if str(v.get("owner_id")) == str(filters["owner_id"])}
        trips = [t for t in trips if str(t.get("vehicle_id")) in owner_vehicle_ids]
    if filters.get("q"):
        q = filters["q"].strip().lower()
        trips = [
            t for t in trips
            if q in str(t.get("id", "")).lower()
            or q in str(t.get("route_name", "")).lower()
            or q in str(t.get("notes", "")).lower()
        ]

    trips.sort(key=lambda t: (str(t.get("date", "")), int(t.get("id") or 0)), reverse=True)

    rows = []
    for t in trips:
        vehicle = vehicles.get(str(t.get("vehicle_id")))
        fin = calc.compute_trip_financials(t, vehicle=vehicle)
        rows.append({
            **t, **fin,
            "customer_name": customers.get(str(t.get("customer_id")), {}).get("name", "-"),
            "vehicle_name": (vehicle.get("code_name") or vehicle.get("plate_number")) if vehicle else "-",
            "driver_name": drivers.get(str(t.get("driver_id")), {}).get("name", "-"),
        })
    return rows


# ===========================================================================
# بيانات مساعدة للفورمات (Dropdowns + Auto-fill عبر JavaScript)
# ===========================================================================
def get_form_lookup_data():
    with db.read_only() as wb:
        customers = db.get_all(wb, "Customers")
        vehicles = db.get_all(wb, "Vehicles")
        drivers = db.get_all(wb, "Drivers")
        owners = db.get_all(wb, "Vehicle_Owners")
    customers.sort(key=lambda c: c.get("name", ""))
    drivers.sort(key=lambda d: d.get("name", ""))
    owners.sort(key=lambda o: o.get("name", ""))
    vehicles.sort(key=lambda v: str(v.get("code_name") or v.get("plate_number") or ""))
    return {"customers": customers, "vehicles": vehicles, "drivers": drivers, "owners": owners}


def get_vehicles_js_map():
    with db.read_only() as wb:
        vehicles = db.get_all(wb, "Vehicles")
        owners = {str(o["id"]): o for o in db.get_all(wb, "Vehicle_Owners", include_deleted=True)}
    out = {}
    for v in vehicles:
        owner = owners.get(str(v.get("owner_id")))
        out[str(v["id"])] = {
            "ownership_type": v.get("ownership_type"),
            "owner_name": owner.get("name") if owner else None,
        }
    return out


def get_toll_routes_js_map():
    routes = get_toll_routes()
    return {r["key"]: calc.safe_num(r["value"]) for r in routes}


# ===========================================================================
# الصيانة
# ===========================================================================
DEFAULT_MAINTENANCE_TYPES = [
    "تغيير زيت", "كاوتش", "فرامل", "قطع غيار", "كهرباء", "ميكانيكا",
    "إصلاح عطل", "صيانة دورية", "أخرى",
]
DEFAULT_GENERAL_EXPENSE_TYPES = ["إيجار", "رواتب إدارية", "فواتير", "أخرى"]


def list_maintenance(vehicle_id=None):
    with db.read_only() as wb:
        rows = db.get_all(wb, "Maintenance")
        vehicles = {str(v["id"]): v for v in db.get_all(wb, "Vehicles", include_deleted=True)}
    if vehicle_id:
        rows = [r for r in rows if str(r.get("vehicle_id")) == str(vehicle_id)]
    for r in rows:
        v = vehicles.get(str(r.get("vehicle_id")))
        r["vehicle_name"] = (v.get("code_name") or v.get("plate_number")) if v else "-"
    rows.sort(key=lambda r: str(r.get("date", "")), reverse=True)
    return rows


def _validate_amount_date(form, extra_required=None):
    errors = []
    amount_raw = (form.get("amount") or "").strip()
    amount_val = 0
    try:
        amount_val = float(amount_raw) if amount_raw != "" else 0
        if amount_val < 0:
            errors.append("المبلغ لازم يكون رقم موجب")
    except ValueError:
        errors.append("المبلغ لازم يكون رقم")
    if not (form.get("date") or "").strip():
        errors.append("لازم تحدد التاريخ")
    for field, label in (extra_required or []):
        if not (form.get(field) or "").strip():
            errors.append(f"لازم تحدد {label}")
    return errors, amount_val


def add_maintenance(form):
    errors, amount_val = _validate_amount_date(form, extra_required=[("vehicle_id", "العربية"), ("expense_type", "نوع المصروف")])
    if errors:
        return errors, None
    with db.transaction() as wb:
        vehicle = db.get_by_id(wb, "Vehicles", form.get("vehicle_id"), include_deleted=True)
        if not vehicle:
            return ["العربية غير موجودة"], None
        new_id = db.get_next_id(wb, "Maintenance", start=1)
        db.append_row(wb, "Maintenance", {
            "id": new_id,
            "vehicle_id": form.get("vehicle_id"),
            "date": form.get("date"),
            "expense_type": form.get("expense_type"),
            "description": (form.get("description") or "").strip(),
            "amount": round(amount_val, 2),
            "notes": (form.get("notes") or "").strip(),
            "is_deleted": False,
            "created_at": now_str(),
        })
        _refresh_monthly_summary(wb)
    return [], new_id


def update_maintenance(item_id, form):
    errors, amount_val = _validate_amount_date(form, extra_required=[("vehicle_id", "العربية"), ("expense_type", "نوع المصروف")])
    if errors:
        return errors
    with db.transaction() as wb:
        ok = db.update_row(wb, "Maintenance", item_id, {
            "vehicle_id": form.get("vehicle_id"),
            "date": form.get("date"),
            "expense_type": form.get("expense_type"),
            "description": (form.get("description") or "").strip(),
            "amount": round(amount_val, 2),
            "notes": (form.get("notes") or "").strip(),
        })
        if not ok:
            errors.append("السجل غير موجود")
        _refresh_monthly_summary(wb)
    return errors


def delete_maintenance(item_id):
    with db.transaction() as wb:
        db.soft_delete(wb, "Maintenance", item_id)
        _refresh_monthly_summary(wb)


def get_maintenance(item_id):
    with db.read_only() as wb:
        return db.get_by_id(wb, "Maintenance", item_id, include_deleted=True)


# ===========================================================================
# المصاريف العامة
# ===========================================================================
def list_expenses():
    with db.read_only() as wb:
        rows = db.get_all(wb, "Expenses")
    rows.sort(key=lambda r: str(r.get("date", "")), reverse=True)
    return rows


def add_expense(form):
    errors, amount_val = _validate_amount_date(form, extra_required=[("expense_type", "نوع المصروف")])
    if errors:
        return errors, None
    with db.transaction() as wb:
        new_id = db.get_next_id(wb, "Expenses", start=1)
        db.append_row(wb, "Expenses", {
            "id": new_id,
            "date": form.get("date"),
            "expense_type": form.get("expense_type"),
            "description": (form.get("description") or "").strip(),
            "amount": round(amount_val, 2),
            "notes": (form.get("notes") or "").strip(),
            "is_deleted": False,
            "created_at": now_str(),
        })
        _refresh_monthly_summary(wb)
    return [], new_id


def update_expense(item_id, form):
    errors, amount_val = _validate_amount_date(form, extra_required=[("expense_type", "نوع المصروف")])
    if errors:
        return errors
    with db.transaction() as wb:
        ok = db.update_row(wb, "Expenses", item_id, {
            "date": form.get("date"),
            "expense_type": form.get("expense_type"),
            "description": (form.get("description") or "").strip(),
            "amount": round(amount_val, 2),
            "notes": (form.get("notes") or "").strip(),
        })
        if not ok:
            errors.append("السجل غير موجود")
        _refresh_monthly_summary(wb)
    return errors


def delete_expense(item_id):
    with db.transaction() as wb:
        db.soft_delete(wb, "Expenses", item_id)
        _refresh_monthly_summary(wb)


def get_expense(item_id):
    with db.read_only() as wb:
        return db.get_by_id(wb, "Expenses", item_id, include_deleted=True)


# ===========================================================================
# الإعدادات (مسارات/كارتة، أنواع مصاريف، اسم الشركة)
# ===========================================================================
def get_settings_by_category(category):
    with db.read_only() as wb:
        rows = db.get_all(wb, "Settings")
    return [r for r in rows if r.get("category") == category]


def get_toll_routes():
    return get_settings_by_category("toll_route")


def add_toll_route(name, price):
    name = (name or "").strip()
    if not name:
        return ["لازم تكتب اسم المسار"]
    with db.transaction() as wb:
        new_id = db.get_next_id(wb, "Settings", start=1)
        db.append_row(wb, "Settings", {
            "id": new_id, "category": "toll_route", "key": name,
            "value": calc.safe_num(price), "notes": "",
        })
    return []


def get_maintenance_expense_types():
    rows = get_settings_by_category("expense_type")
    names = [r["key"] for r in rows]
    return names or DEFAULT_MAINTENANCE_TYPES


def add_maintenance_expense_type(name):
    name = (name or "").strip()
    if not name:
        return ["لازم تكتب اسم نوع المصروف"]
    with db.transaction() as wb:
        new_id = db.get_next_id(wb, "Settings", start=1)
        db.append_row(wb, "Settings", {
            "id": new_id, "category": "expense_type", "key": name, "value": "", "notes": "",
        })
    return []


def get_general_expense_types():
    rows = get_settings_by_category("general_expense_type")
    names = [r["key"] for r in rows]
    return names or DEFAULT_GENERAL_EXPENSE_TYPES


def add_general_expense_type(name):
    name = (name or "").strip()
    if not name:
        return ["لازم تكتب اسم نوع المصروف"]
    with db.transaction() as wb:
        new_id = db.get_next_id(wb, "Settings", start=1)
        db.append_row(wb, "Settings", {
            "id": new_id, "category": "general_expense_type", "key": name, "value": "", "notes": "",
        })
    return []


def get_company_name():
    rows = get_settings_by_category("general")
    for r in rows:
        if r.get("key") == "company_name":
            return r.get("value")
    return "شركة توريد وتأجير العربيات"


def set_company_name(name):
    name = (name or "").strip() or "شركة توريد وتأجير العربيات"
    with db.transaction() as wb:
        rows = db.get_all(wb, "Settings", include_deleted=True)
        existing = next((r for r in rows if r.get("category") == "general" and r.get("key") == "company_name"), None)
        if existing:
            db.update_row(wb, "Settings", existing["id"], {"value": name})
        else:
            new_id = db.get_next_id(wb, "Settings", start=1)
            db.append_row(wb, "Settings", {
                "id": new_id, "category": "general", "key": "company_name", "value": name, "notes": "",
            })


# ===========================================================================
# النسخ الاحتياطي وإعادة التهيئة
# ===========================================================================
def create_backup():
    return db.create_backup()


def list_backups():
    return db.list_backups()


def reset_system(load_demo=False):
    db.create_backup(label="قبل_اعادة_التهيئة")
    db.init_db(force=True)
    if load_demo:
        import seed_data
        seed_data.load_demo_data()


# ===========================================================================
# ملخص شهري (Monthly_Summary) - نسخة معلوماتية داخل الإكسل، يُعاد حسابها
# تلقائيًا بعد أي عملية تعديل على الرحلات/الصيانة/المصاريف/التحصيلات.
# النظام نفسه (الداشبورد والتقارير) بيحسب من البيانات الخام مباشرة، مش
# من الشيت ده - الشيت ده للعرض السريع لو حد فتح الإكسل يدويًا بس.
# ===========================================================================
def _compute_all_monthly_rows(wb):
    trips = db.get_all(wb, "Trips")
    maintenance = db.get_all(wb, "Maintenance")
    expenses = db.get_all(wb, "Expenses")
    cust_payments = db.get_all(wb, "Customer_Payments")
    owner_payments = db.get_all(wb, "Owner_Payments")
    driver_payments = db.get_all(wb, "Driver_Payments")
    vehicles = {str(v["id"]): v for v in db.get_all(wb, "Vehicles", include_deleted=True)}

    months = sorted({str(t.get("date", ""))[:7] for t in trips if t.get("date")})
    result = []
    for m in months:
        month_trips = [t for t in trips if str(t.get("date", ""))[:7] == m]
        upto_trips = [t for t in trips if str(t.get("date", ""))[:7] <= m]
        upto_cp = [p for p in cust_payments if str(p.get("date", ""))[:7] <= m]
        upto_op = [p for p in owner_payments if str(p.get("date", ""))[:7] <= m]
        upto_dp = [p for p in driver_payments if str(p.get("date", ""))[:7] <= m]

        month_totals = calc.sum_trip_financials(month_trips, vehicles_by_id=vehicles)
        upto_totals = calc.sum_trip_financials(upto_trips, vehicles_by_id=vehicles)

        month_maint = calc.sum_amounts([x for x in maintenance if str(x.get("date", ""))[:7] == m])
        month_exp = calc.sum_amounts([x for x in expenses if str(x.get("date", ""))[:7] == m])
        month_collected = calc.sum_amounts([p for p in cust_payments if str(p.get("date", ""))[:7] == m])

        result.append({
            "month": m,
            "total_revenue": month_totals["revenue"],
            "total_expenses": round(month_totals["total_cost"] + month_maint + month_exp, 2),
            "net_profit": round(month_totals["net_profit"] - month_maint - month_exp, 2),
            "collected": month_collected,
            "customer_dues": calc.compute_dues(upto_totals["revenue"], calc.sum_amounts(upto_cp)),
            "owner_dues": calc.compute_dues(upto_totals["owner_fee"], calc.sum_amounts(upto_op)),
            "driver_dues": calc.compute_dues(upto_totals["driver_fee"], calc.sum_amounts(upto_dp)),
            "trip_count": month_totals["trip_count"],
            "generated_at": now_str(),
        })
    return result


def _refresh_monthly_summary(wb):
    rows = _compute_all_monthly_rows(wb)
    db.clear_sheet_data(wb, "Monthly_Summary")
    for row in rows:
        db.append_row(wb, "Monthly_Summary", row)


# ===========================================================================
# الداشبورد
# ===========================================================================
def get_dashboard_data():
    today = today_str()
    m_prefix = month_prefix(today)
    with db.read_only() as wb:
        trips = db.get_all(wb, "Trips")
        maintenance = db.get_all(wb, "Maintenance")
        expenses = db.get_all(wb, "Expenses")
        cust_payments = db.get_all(wb, "Customer_Payments")
        owner_payments = db.get_all(wb, "Owner_Payments")
        driver_payments = db.get_all(wb, "Driver_Payments")
        vehicles_list = db.get_all(wb, "Vehicles")
        vehicles = {str(v["id"]): v for v in vehicles_list}

    today_trips = [t for t in trips if str(t.get("date", "")) == today]
    today_maint = calc.sum_amounts([m for m in maintenance if str(m.get("date", "")) == today])
    today_exp = calc.sum_amounts([e for e in expenses if str(e.get("date", "")) == today])
    today_totals = calc.sum_trip_financials(today_trips, vehicles_by_id=vehicles)

    month_trips = [t for t in trips if str(t.get("date", "")).startswith(m_prefix)]
    month_maint = calc.sum_amounts([m for m in maintenance if str(m.get("date", "")).startswith(m_prefix)])
    month_exp = calc.sum_amounts([e for e in expenses if str(e.get("date", "")).startswith(m_prefix)])
    month_totals = calc.sum_trip_financials(month_trips, vehicles_by_id=vehicles)
    month_collected = calc.sum_amounts([p for p in cust_payments if str(p.get("date", "")).startswith(m_prefix)])

    all_totals = calc.sum_trip_financials(trips, vehicles_by_id=vehicles)
    total_customer_dues = calc.compute_dues(all_totals["revenue"], calc.sum_amounts(cust_payments))
    total_owner_dues = calc.compute_dues(all_totals["owner_fee"], calc.sum_amounts(owner_payments))
    total_driver_dues = calc.compute_dues(all_totals["driver_fee"], calc.sum_amounts(driver_payments))

    return {
        "today": {
            "revenue": today_totals["revenue"],
            "expenses": round(today_totals["total_cost"] + today_maint + today_exp, 2),
            "net_profit": round(today_totals["net_profit"] - today_maint - today_exp, 2),
            "trip_count": today_totals["trip_count"],
        },
        "month": {
            "revenue": month_totals["revenue"],
            "expenses": round(month_totals["total_cost"] + month_maint + month_exp, 2),
            "net_profit": round(month_totals["net_profit"] - month_maint - month_exp, 2),
            "collected": month_collected,
            "trip_count": month_totals["trip_count"],
        },
        "dues": {
            "customer_dues": total_customer_dues,
            "owner_dues": total_owner_dues,
            "driver_dues": total_driver_dues,
        },
        "fleet": {
            "company_vehicles": len([v for v in vehicles_list if v.get("ownership_type") == "company"]),
            "free_vehicles": len([v for v in vehicles_list if v.get("ownership_type") == "free"]),
        },
    }


# ===========================================================================
# التقارير
# ===========================================================================
def get_vehicles_report():
    with db.read_only() as wb:
        vehicles = db.get_all(wb, "Vehicles")
        trips = db.get_all(wb, "Trips")
        maintenance = db.get_all(wb, "Maintenance")
        owners = {str(o["id"]): o for o in db.get_all(wb, "Vehicle_Owners", include_deleted=True)}
    vehicles_by_id = {str(v["id"]): v for v in vehicles}
    rows = []
    for v in vehicles:
        v_trips = [t for t in trips if str(t.get("vehicle_id")) == str(v["id"])]
        v_maint = [m for m in maintenance if str(m.get("vehicle_id")) == str(v["id"])]
        totals = calc.sum_trip_financials(v_trips, vehicles_by_id=vehicles_by_id)
        maint_total = calc.sum_amounts(v_maint)
        total_cost = round(totals["total_cost"] + maint_total, 2)
        net_profit = round(totals["revenue"] - total_cost, 2)
        owner = owners.get(str(v.get("owner_id")))
        rows.append({
            "id": v["id"],
            "name": v.get("code_name") or v.get("plate_number"),
            "ownership_label": "ملك الشركة" if v.get("ownership_type") == "company" else "عربية حرة",
            "owner_name": owner.get("name") if owner else "-",
            "vehicle_type": v.get("vehicle_type") or "-",
            "trip_count": totals["trip_count"],
            "revenue": totals["revenue"],
            "fuel_cost": totals["fuel_cost"],
            "toll_cost": totals["toll_cost"],
            "driver_cost": totals["driver_fee"],
            "owner_cost": totals["owner_fee"],
            "maintenance_cost": maint_total,
            "total_cost": total_cost,
            "net_profit": net_profit,
        })
    rows.sort(key=lambda r: r["net_profit"], reverse=True)
    return rows


def get_customers_report():
    with db.read_only() as wb:
        customers = db.get_all(wb, "Customers")
        trips = db.get_all(wb, "Trips")
        payments = db.get_all(wb, "Customer_Payments")
    rows = []
    for c in customers:
        c_trips = [t for t in trips if str(t.get("customer_id")) == str(c["id"])]
        c_payments = [p for p in payments if str(p.get("customer_id")) == str(c["id"])]
        totals = calc.sum_trip_financials(c_trips)
        collected = calc.sum_amounts(c_payments)
        remaining = calc.compute_dues(totals["revenue"], collected)
        rows.append({
            "id": c["id"], "name": c["name"], "trip_count": totals["trip_count"],
            "total_dues": totals["revenue"], "collected": collected, "remaining": remaining,
        })
    rows.sort(key=lambda r: r["remaining"], reverse=True)
    return rows


def get_owners_report():
    with db.read_only() as wb:
        owners = db.get_all(wb, "Vehicle_Owners")
        vehicles = db.get_all(wb, "Vehicles", include_deleted=True)
        vehicles_by_id = {str(v["id"]): v for v in vehicles}
        trips = db.get_all(wb, "Trips")
        payments = db.get_all(wb, "Owner_Payments")
    rows = []
    for o in owners:
        o_vehicle_ids = _vehicle_ids_for_owner(vehicles, o["id"])
        o_trips = [t for t in trips if str(t.get("vehicle_id")) in o_vehicle_ids]
        o_payments = [p for p in payments if str(p.get("owner_id")) == str(o["id"])]
        totals = calc.sum_trip_financials(o_trips, vehicles_by_id=vehicles_by_id)
        paid = calc.sum_amounts(o_payments)
        remaining = calc.compute_dues(totals["owner_fee"], paid)
        rows.append({
            "id": o["id"], "name": o["name"], "trip_count": totals["trip_count"],
            "total_dues": totals["owner_fee"], "collected": paid, "remaining": remaining,
        })
    rows.sort(key=lambda r: r["remaining"], reverse=True)
    return rows


def get_drivers_report():
    with db.read_only() as wb:
        drivers = db.get_all(wb, "Drivers")
        trips = db.get_all(wb, "Trips")
        payments = db.get_all(wb, "Driver_Payments")
    rows = []
    for d in drivers:
        d_trips = [t for t in trips if str(t.get("driver_id")) == str(d["id"])]
        d_payments = [p for p in payments if str(p.get("driver_id")) == str(d["id"])]
        totals = calc.sum_trip_financials(d_trips)
        paid = calc.sum_amounts(d_payments)
        remaining = calc.compute_dues(totals["driver_fee"], paid)
        rows.append({
            "id": d["id"], "name": d["name"], "trip_count": totals["trip_count"],
            "total_dues": totals["driver_fee"], "collected": paid, "remaining": remaining,
        })
    rows.sort(key=lambda r: r["remaining"], reverse=True)
    return rows


def get_expenses_report(date_from=None, date_to=None):
    with db.read_only() as wb:
        trips = db.get_all(wb, "Trips")
        maintenance = db.get_all(wb, "Maintenance")
        expenses = db.get_all(wb, "Expenses")

    def in_range(d):
        d = str(d)
        if date_from and d < date_from:
            return False
        if date_to and d > date_to:
            return False
        return True

    trips = [t for t in trips if in_range(t.get("date"))]
    maintenance = [m for m in maintenance if in_range(m.get("date"))]
    expenses = [e for e in expenses if in_range(e.get("date"))]

    totals = calc.sum_trip_financials(trips)
    maint_total = calc.sum_amounts(maintenance)
    general_total = calc.sum_amounts(expenses)
    rows = [
        {"category": "السولار", "amount": totals["fuel_cost"]},
        {"category": "الكارتة", "amount": totals["toll_cost"]},
        {"category": "أجور السواقين", "amount": totals["driver_fee"]},
        {"category": "أجرة أصحاب العربيات", "amount": totals["owner_fee"]},
        {"category": "الصيانة", "amount": maint_total},
        {"category": "مصاريف عامة أخرى", "amount": general_total},
    ]
    grand_total = round(sum(r["amount"] for r in rows), 2)
    return {"rows": rows, "grand_total": grand_total}


def get_fuel_report():
    with db.read_only() as wb:
        trips = db.get_all(wb, "Trips")
        vehicles = {str(v["id"]): v for v in db.get_all(wb, "Vehicles", include_deleted=True)}
    total_liters = sum(calc.safe_num(t.get("fuel_liters")) for t in trips)
    total_cost = sum(calc.compute_trip_financials(t)["fuel_cost"] for t in trips)
    avg_price = round(total_cost / total_liters, 2) if total_liters else 0
    by_vehicle = {}
    for t in trips:
        vid = str(t.get("vehicle_id"))
        fin = calc.compute_trip_financials(t)
        if vid not in by_vehicle:
            v = vehicles.get(vid)
            by_vehicle[vid] = {
                "name": (v.get("code_name") or v.get("plate_number")) if v else "-",
                "liters": 0.0, "cost": 0.0, "trip_count": 0,
            }
        by_vehicle[vid]["liters"] += fin["fuel_liters"]
        by_vehicle[vid]["cost"] += fin["fuel_cost"]
        by_vehicle[vid]["trip_count"] += 1
    rows = sorted(by_vehicle.values(), key=lambda r: r["cost"], reverse=True)
    for r in rows:
        r["liters"] = round(r["liters"], 2)
        r["cost"] = round(r["cost"], 2)
    return {
        "total_liters": round(total_liters, 2),
        "total_cost": round(total_cost, 2),
        "avg_price": avg_price,
        "by_vehicle": rows,
    }


def get_maintenance_report():
    return list_maintenance()


def get_profit_report():
    with db.read_only() as wb:
        rows = _compute_all_monthly_rows(wb)
    return list(reversed(rows))  # الأحدث أولًا


def get_collection_report():
    return {
        "customers": get_customers_report(),
        "owners": get_owners_report(),
        "drivers": get_drivers_report(),
    }
