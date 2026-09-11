# -*- coding: utf-8 -*-
"""
seed_data.py
============
بيانات تجريبية (Demo) لتجربة النظام بأرقام حقيقية بدل شاشة فاضية.
تقدر تمسحها أو تعيد تهيئة النظام في أي وقت من صفحة "الإعدادات".

يشمل: 5 عربيات ملك الشركة، 5 عربيات حرة (بـ5 أصحاب عربيات)، 5 سواقين،
3 عملاء، 20 رحلة موزعة على آخر ~5 أسابيع، صيانة، وتحصيلات جزئية.
"""
import random
from datetime import datetime, timedelta

import excel_db as db
import calculations as calc


def _dt_str(d):
    return d.strftime("%Y-%m-%d %H:%M") if hasattr(d, "strftime") else str(d)


def load_demo_data():
    random.seed(42)
    with db.transaction() as wb:
        for sheet in db.SHEETS:
            db.clear_sheet_data(wb, sheet)

        today = datetime.now().date()

        # -------- العملاء --------
        customers = [
            {"id": 1, "name": "شركة Fresh للأغذية", "phone": "01001112223", "notes": "عميل شهري ثابت"},
            {"id": 2, "name": "مصنع النور للصناعات الغذائية", "phone": "01002223334", "notes": ""},
            {"id": 3, "name": "مقاولون الدلتا للمشروعات", "phone": "01003334445", "notes": "بيحاسب آخر الشهر"},
        ]
        for c in customers:
            db.append_row(wb, "Customers", {**c, "is_deleted": False, "created_at": _dt_str(today)})

        # -------- أصحاب العربيات --------
        owners = [
            {"id": 1, "name": "محمد السيد", "phone": "01012345671"},
            {"id": 2, "name": "أحمد جمال", "phone": "01012345672"},
            {"id": 3, "name": "كريم فتحي", "phone": "01012345673"},
            {"id": 4, "name": "حسام الدين", "phone": "01012345674"},
            {"id": 5, "name": "رمضان عبد الله", "phone": "01012345675"},
        ]
        for o in owners:
            db.append_row(wb, "Vehicle_Owners", {**o, "notes": "", "is_deleted": False, "created_at": _dt_str(today)})

        # -------- السواقين --------
        drivers = [
            {"id": 1, "name": "أحمد محمود"},
            {"id": 2, "name": "سيد إبراهيم"},
            {"id": 3, "name": "جمال حسن"},
            {"id": 4, "name": "عماد فاروق"},
            {"id": 5, "name": "طارق سعيد"},
        ]
        for i, d in enumerate(drivers, start=1):
            db.append_row(wb, "Drivers", {
                **d, "phone": f"0111111111{i}", "notes": "",
                "is_deleted": False, "created_at": _dt_str(today),
            })

        # -------- العربيات: 5 ملك الشركة --------
        company_vehicles = [
            {"id": 1, "plate_number": "أ ب ج 1234", "code_name": "عربية 1", "vehicle_type": "ميكروباص", "capacity": "14 راكب"},
            {"id": 2, "plate_number": "س ص ع 5678", "code_name": "عربية 2", "vehicle_type": "ميكروباص", "capacity": "14 راكب"},
            {"id": 3, "plate_number": "ط ظ ع 4321", "code_name": "عربية 3", "vehicle_type": "هايس", "capacity": "12 راكب"},
            {"id": 4, "plate_number": "م ن ه 8765", "code_name": "عربية 4", "vehicle_type": "ميكروباص", "capacity": "14 راكب"},
            {"id": 5, "plate_number": "ك ل م 2468", "code_name": "عربية 5", "vehicle_type": "هايس", "capacity": "12 راكب"},
        ]
        for v in company_vehicles:
            db.append_row(wb, "Vehicles", {
                **v, "ownership_type": "company", "owner_id": "", "status": "نشطة",
                "notes": "", "is_deleted": False, "created_at": _dt_str(today),
            })

        # -------- العربيات: 5 حرة --------
        free_vehicles = [
            {"id": 6, "plate_number": "ق ر ش 1111", "code_name": "عربية محمد", "vehicle_type": "ميكروباص", "capacity": "14 راكب", "owner_id": 1},
            {"id": 7, "plate_number": "ت ث خ 2222", "code_name": "عربية أحمد", "vehicle_type": "هايس", "capacity": "12 راكب", "owner_id": 2},
            {"id": 8, "plate_number": "ذ ز و 3333", "code_name": "عربية كريم", "vehicle_type": "ميكروباص", "capacity": "14 راكب", "owner_id": 3},
            {"id": 9, "plate_number": "ح ط ي 4444", "code_name": "عربية حسام", "vehicle_type": "ميكروباص", "capacity": "14 راكب", "owner_id": 4},
            {"id": 10, "plate_number": "ك ل م 5555", "code_name": "عربية رمضان", "vehicle_type": "هايس", "capacity": "12 راكب", "owner_id": 5},
        ]
        for v in free_vehicles:
            db.append_row(wb, "Vehicles", {
                **v, "ownership_type": "free", "status": "نشطة",
                "notes": "", "is_deleted": False, "created_at": _dt_str(today),
            })

        vehicles_by_id = {}
        for v in company_vehicles:
            vehicles_by_id[str(v["id"])] = {**v, "ownership_type": "company"}
        for v in free_vehicles:
            vehicles_by_id[str(v["id"])] = {**v, "ownership_type": "free"}
        all_vehicle_ids = list(vehicles_by_id.keys())

        # -------- إعدادات: اسم الشركة + مسارات/كارتة --------
        toll_routes = [
            ("القاهرة - مدينة العاشر من رمضان", 50),
            ("القاهرة - العين السخنة", 75),
            ("داخل القاهرة الكبرى", 0),
            ("القاهرة - المنصورة", 60),
        ]
        setting_id = 1
        db.append_row(wb, "Settings", {
            "id": setting_id, "category": "general", "key": "company_name",
            "value": "شركتك لتوريد وتأجير السيارات والميكروباصات", "notes": "",
        })
        setting_id += 1
        for name, price in toll_routes:
            db.append_row(wb, "Settings", {
                "id": setting_id, "category": "toll_route", "key": name, "value": price, "notes": "",
            })
            setting_id += 1

        # -------- 20 رحلة تجريبية موزعة على آخر ~5 أسابيع --------
        days_ago_options = [0, 0, 1, 2, 3, 5, 6, 8, 10, 12, 14, 15, 18, 20, 22, 25, 28, 30, 33, 36]
        trip_id = 10001
        customer_totals = {c["id"]: 0.0 for c in customers}
        owner_totals = {o["id"]: 0.0 for o in owners}
        driver_totals = {d["id"]: 0.0 for d in drivers}
        for i in range(20):
            trip_date = today - timedelta(days=days_ago_options[i])
            customer = random.choice(customers)
            vehicle_id = random.choice(all_vehicle_ids)
            vehicle = vehicles_by_id[vehicle_id]
            driver = random.choice(drivers)
            route_name, toll_default = random.choice(toll_routes)

            trip_price = random.choice([1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700])
            fuel_liters = random.choice([15, 18, 20])
            fuel_price = random.choice([19.5, 20, 20.5])
            driver_fee = random.choice([150, 180, 200])
            is_free = vehicle["ownership_type"] == "free"
            owner_fee = random.choice([300, 350, 400]) if is_free else 0
            commission = random.choice([0, 0, 40, 50, 60, 75]) if is_free else 0

            raw = {
                "trip_price": trip_price, "owner_fee": owner_fee, "driver_fee": driver_fee,
                "fuel_liters": fuel_liters, "fuel_price_per_liter": fuel_price,
                "toll_cost": toll_default, "commission": commission,
            }
            fin = calc.compute_trip_financials(raw, vehicle=vehicle)
            customer_totals[customer["id"]] += fin["trip_price"]
            driver_totals[driver["id"]] += fin["driver_fee"]
            if is_free:
                owner_totals[vehicle["owner_id"]] += fin["owner_fee"]

            db.append_row(wb, "Trips", {
                "id": trip_id,
                "date": trip_date.strftime("%Y-%m-%d"),
                "customer_id": customer["id"],
                "vehicle_id": int(vehicle_id),
                "driver_id": driver["id"],
                "route_name": route_name,
                "trip_price": fin["trip_price"], "owner_fee": fin["owner_fee"],
                "driver_fee": fin["driver_fee"], "fuel_liters": fin["fuel_liters"],
                "fuel_price_per_liter": fin["fuel_price_per_liter"], "fuel_cost": fin["fuel_cost"],
                "toll_cost": fin["toll_cost"], "commission": fin["commission"],
                "total_cost": fin["total_cost"], "net_profit": fin["net_profit"],
                "notes": "", "is_deleted": False,
                "created_at": _dt_str(trip_date), "updated_at": _dt_str(trip_date),
            })
            trip_id += 1

        # -------- صيانة تجريبية --------
        maint_items = [
            (1, "تغيير زيت", "تغيير زيت وفلتر", 1200, 3),
            (1, "كاوتش", "تغيير كاوتشين خلفي", 1800, 20),
            (2, "فرامل", "تيل فرامل أمامي وخلفي", 700, 7),
            (3, "إصلاح عطل", "إصلاح دينامو", 1200, 15),
            (4, "صيانة دورية", "فحص دوري شامل", 600, 10),
            (5, "كهرباء", "إصلاح ماسورة كهرباء", 400, 25),
        ]
        for i, (vid, mtype, desc, amount, days_ago) in enumerate(maint_items, start=1):
            m_date = today - timedelta(days=days_ago)
            db.append_row(wb, "Maintenance", {
                "id": i, "vehicle_id": vid, "date": m_date.strftime("%Y-%m-%d"),
                "expense_type": mtype, "description": desc, "amount": amount,
                "notes": "", "is_deleted": False, "created_at": _dt_str(m_date),
            })

        # -------- تحصيلات جزئية من العملاء (نسبة واقعية مما استُحق فعليًا) --------
        cp_id = 1
        for c in customers:
            owed = customer_totals[c["id"]]
            if owed <= 0:
                continue
            to_pay = owed * random.choice([0.5, 0.55, 0.6, 0.65])
            for days_ago in (6, 18):
                amount = round(to_pay / 2, -1)
                if amount <= 0:
                    continue
                p_date = today - timedelta(days=days_ago)
                db.append_row(wb, "Customer_Payments", {
                    "id": cp_id, "customer_id": c["id"], "date": p_date.strftime("%Y-%m-%d"),
                    "amount": amount, "method": "كاش",
                    "notes": "", "is_deleted": False, "created_at": _dt_str(p_date),
                })
                cp_id += 1

        # -------- دفعات جزئية لأصحاب العربيات (نسبة واقعية مما استُحق فعليًا) --------
        op_id = 1
        for idx, o in enumerate(owners):
            owed = owner_totals[o["id"]]
            if owed <= 0:
                continue
            amount = round(owed * random.choice([0.4, 0.5, 0.6]), -1)
            if amount <= 0:
                continue
            p_date = today - timedelta(days=(9 + idx * 3))
            db.append_row(wb, "Owner_Payments", {
                "id": op_id, "owner_id": o["id"], "date": p_date.strftime("%Y-%m-%d"),
                "amount": amount, "method": "كاش",
                "notes": "", "is_deleted": False, "created_at": _dt_str(p_date),
            })
            op_id += 1

        # -------- دفعات جزئية للسواقين (نسبة واقعية مما استُحق فعليًا) --------
        dp_id = 1
        for idx, d in enumerate(drivers):
            owed = driver_totals[d["id"]]
            if owed <= 0:
                continue
            amount = round(owed * random.choice([0.4, 0.5, 0.6]), -1)
            if amount <= 0:
                continue
            p_date = today - timedelta(days=(8 + idx * 4))
            db.append_row(wb, "Driver_Payments", {
                "id": dp_id, "driver_id": d["id"], "date": p_date.strftime("%Y-%m-%d"),
                "amount": amount, "method": "كاش",
                "notes": "", "is_deleted": False, "created_at": _dt_str(p_date),
            })
            dp_id += 1

        # -------- مصاريف عامة --------
        db.append_row(wb, "Expenses", {
            "id": 1, "date": (today - timedelta(days=5)).strftime("%Y-%m-%d"),
            "expense_type": "إيجار", "description": "إيجار المكتب والجراج", "amount": 2000,
            "notes": "", "is_deleted": False, "created_at": _dt_str(today),
        })
        db.append_row(wb, "Expenses", {
            "id": 2, "date": (today - timedelta(days=12)).strftime("%Y-%m-%d"),
            "expense_type": "فواتير", "description": "فاتورة تليفونات وإنترنت", "amount": 450,
            "notes": "", "is_deleted": False, "created_at": _dt_str(today),
        })

        # -------- تحديث الملخص الشهري --------
        import data_access as da
        da._refresh_monthly_summary(wb)


if __name__ == "__main__":
    if not db.DB_PATH.exists():
        db.init_db()
    load_demo_data()
    print("تم تحميل البيانات التجريبية بنجاح.")
