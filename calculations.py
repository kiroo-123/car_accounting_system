# -*- coding: utf-8 -*-
"""
calculations.py
================
نموذج الحسابات المالية - المصدر الوحيد لكل المعادلات في النظام.

قاعدة أساسية: أي رقم مالي بيتحسب مرة واحدة بس، في مكان واحد بس، هنا.
باقي النظام (routes, reports, dashboard) بينادي على الدوال دي بدل ما
يعيد كتابة أي معادلة، عشان نضمن عدم التعارض أو الحساب المزدوج.

===========================================================================
معادلة الرحلة الواحدة (أهم معادلة في النظام):
===========================================================================

1) تكلفة السولار = عدد اللترات × سعر اللتر
   fuel_cost = fuel_liters * fuel_price_per_liter

2) إجمالي تكلفة الرحلة = السولار + الكارتة + أجر السواق + أجرة صاحب العربية
   total_cost = fuel_cost + toll_cost + driver_fee + owner_fee
   (owner_fee = 0 دايمًا لو العربية "ملك الشركة" - مفيش أجرة صاحب عربية
    لعربية الشركة نفسها. القاعدة دي متطبقة إجباريًا مش بس بالواجهة.)

3) صافي ربح الرحلة = سعر الرحلة من العميل − إجمالي تكلفة الرحلة
   net_profit = trip_price - total_cost

عن "العمولة":
--------------
العمولة قيمة **معلوماتية** فقط، بتوضح للمستخدم إن جزء من صافي ربح
الرحلة (اللي اتحسب في المعادلة رقم 3) هو تحديدًا نصيب الشركة كـ"سمسرة/
عمولة" مقابل توفير العربية - وده مهم خصوصًا في العربيات الحرة.
العمولة **مش بتتجمع على الإيراد ومش بتتطرح كتكلفة** في أي معادلة -
عشان كده مستحيل تتحسب مرتين. هي مجرد "لافتة" على جزء من رقم already
محسوب. لو حابب تغيّر الفكرة دي (مثلاً تخليها مبلغ إضافي يُضاف فوق سعر
الرحلة) ده تغيير بسيط في مكان واحد بس هنا في compute_trip_financials.

===========================================================================
مصاريف مش جزء من حساب الرحلة الواحدة:
===========================================================================
- الصيانة (Maintenance): مرتبطة بالعربية مش برحلة معينة، فبتتحسب على
  مستوى "كشف حساب العربية" و"ربح الشركة الإجمالي" فقط، مش على مستوى
  صافي ربح الرحلة الواحدة (لأنه مش منطقي تقسم فاتورة صيانة على رحلة
  واحدة بالذات).
- المصاريف العامة (Expenses): مصاريف الشركة العامة اللي مالهاش علاقة
  مباشرة برحلة أو عربية معينة (زي الإيجار مثلاً)، بتتحسب على مستوى
  ربح الشركة الإجمالي بس.

===========================================================================
ربح العربية الواحدة:
===========================================================================
vehicle_profit = SUM(net_profit لكل رحلات العربية) − SUM(الصيانة للعربية)

===========================================================================
ربح الشركة الإجمالي:
===========================================================================
company_profit = SUM(net_profit لكل الرحلات)
                  − SUM(كل الصيانة)
                  − SUM(كل المصاريف العامة)

===========================================================================
مستحقات العملاء / أصحاب العربيات / السواقين:
===========================================================================
customer_dues   = SUM(trip_price لرحلات العميل) − SUM(المحصل من العميل)
owner_dues      = SUM(owner_fee لرحلات صاحب العربية) − SUM(المدفوع لصاحب العربية)
driver_dues     = SUM(driver_fee لرحلات السواق) − SUM(المدفوع للسواق)
"""


def safe_num(value):
    """يحول أي قيمة (فاضية / نص / رقم) إلى float بأمان، بيرجع 0 لو مش صالحة."""
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def compute_trip_financials(trip, vehicle=None):
    """
    يحسب كل الأرقام المالية لرحلة واحدة من القيم الخام المدخلة.

    trip: dict فيه على الأقل:
        trip_price, fuel_liters, fuel_price_per_liter,
        toll_cost, driver_fee, owner_fee, commission
    vehicle: dict العربية (اختياري) - لو ownership_type == 'company'
             هيتم تصفير owner_fee إجباريًا بغض النظر عن أي قيمة مُدخلة.

    يرجع dict فيه: fuel_cost, toll_cost, driver_fee, owner_fee,
                   total_cost, revenue, net_profit, commission
    """
    fuel_liters = safe_num(trip.get("fuel_liters"))
    fuel_price = safe_num(trip.get("fuel_price_per_liter"))
    fuel_cost = round(fuel_liters * fuel_price, 2)

    toll_cost = round(safe_num(trip.get("toll_cost")), 2)
    driver_fee = round(safe_num(trip.get("driver_fee")), 2)

    owner_fee = round(safe_num(trip.get("owner_fee")), 2)
    if vehicle is not None and vehicle.get("ownership_type") == "company":
        owner_fee = 0.0  # قاعدة صارمة: عربية الشركة مالهاش أجرة صاحب عربية

    trip_price = round(safe_num(trip.get("trip_price")), 2)
    commission = round(safe_num(trip.get("commission")), 2)

    total_cost = round(fuel_cost + toll_cost + driver_fee + owner_fee, 2)
    net_profit = round(trip_price - total_cost, 2)

    return {
        "fuel_liters": fuel_liters,
        "fuel_price_per_liter": fuel_price,
        "fuel_cost": fuel_cost,
        "toll_cost": toll_cost,
        "driver_fee": driver_fee,
        "owner_fee": owner_fee,
        "total_cost": total_cost,
        "revenue": trip_price,
        "trip_price": trip_price,
        "net_profit": net_profit,
        "commission": commission,
    }


def sum_trip_financials(trips, vehicles_by_id=None):
    """
    يجمع أرقام مجموعة رحلات (تُستخدم في تقارير العربية / العميل / الشركة).
    trips: list of raw trip dicts.
    vehicles_by_id: dict اختياري {vehicle_id: vehicle_dict} عشان تطبيق
                    قاعدة "عربية الشركة مالهاش أجرة صاحب عربية" بشكل صحيح.
    """
    totals = {
        "trip_count": 0,
        "revenue": 0.0,
        "fuel_cost": 0.0,
        "toll_cost": 0.0,
        "driver_fee": 0.0,
        "owner_fee": 0.0,
        "total_cost": 0.0,
        "net_profit": 0.0,
        "commission": 0.0,
    }
    for trip in trips:
        vehicle = None
        if vehicles_by_id is not None:
            vehicle = vehicles_by_id.get(str(trip.get("vehicle_id")))
        fin = compute_trip_financials(trip, vehicle=vehicle)
        totals["trip_count"] += 1
        totals["revenue"] += fin["revenue"]
        totals["fuel_cost"] += fin["fuel_cost"]
        totals["toll_cost"] += fin["toll_cost"]
        totals["driver_fee"] += fin["driver_fee"]
        totals["owner_fee"] += fin["owner_fee"]
        totals["total_cost"] += fin["total_cost"]
        totals["net_profit"] += fin["net_profit"]
        totals["commission"] += fin["commission"]
    for k in totals:
        if k != "trip_count":
            totals[k] = round(totals[k], 2)
    return totals


def sum_amounts(records, field="amount"):
    return round(sum(safe_num(r.get(field)) for r in records), 2)


def compute_dues(total_owed, total_paid):
    return round(safe_num(total_owed) - safe_num(total_paid), 2)
