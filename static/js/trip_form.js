/* trip_form.js — حسابات فورم إضافة/تعديل الرحلة */
(function () {
  "use strict";

  /* ── البيانات من الـ server ─────────────────────────── */
  var vehiclesMap = window.__vehiclesMap || {};  // {id: {ownership_type, owner_name}}
  var tollMap = window.__tollMap || {};          // {"اسم المسار": سعر_الكارتة}

  /* ── العناصر ─────────────────────────────────────────── */
  var vehicleSelect  = document.getElementById("vehicle_id");
  var ownerHint      = document.getElementById("owner_hint");
  var ownerFeeGroup  = document.getElementById("owner_fee_group");
  var ownerFeeInput  = document.getElementById("owner_fee");
  var driverFeeInput = document.getElementById("driver_fee");
  var fuelLiters     = document.getElementById("fuel_liters");
  var fuelPrice      = document.getElementById("fuel_price_per_liter");
  var fuelDisplay    = document.getElementById("fuel_cost_display");
  var tollCostInput  = document.getElementById("toll_cost");
  var routePreset    = document.getElementById("route_preset");
  var routeNameHid   = document.getElementById("route_name");
  var tripPriceInput = document.getElementById("trip_price");
  var calcTotalCost  = document.getElementById("calc-total-cost");
  var calcNetProfit  = document.getElementById("calc-net-profit");
  var calcHighlight  = calcNetProfit ? calcNetProfit.closest(".calc-highlight") : null;

  /* ── أدوات ──────────────────────────────────────────── */
  function safeNum(v) {
    var n = parseFloat(v);
    return isNaN(n) || n < 0 ? 0 : n;
  }

  function fmt(n) {
    if (n === Math.floor(n)) return n.toLocaleString("ar-EG") + " جنيه";
    return n.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",") + " جنيه";
  }

  /* ── تحديث عرض صاحب العربية ─────────────────────────── */
  function updateOwnerDisplay() {
    if (!vehicleSelect) return;
    var id = vehicleSelect.value;
    var info = vehiclesMap[id] || {};
    var isFree = info.ownership_type === "free";
    if (ownerFeeGroup) ownerFeeGroup.style.display = isFree ? "" : "none";
    if (!isFree && ownerFeeInput) ownerFeeInput.value = "";
    if (ownerHint) {
      ownerHint.textContent = isFree
        ? (info.owner_name ? "صاحب العربية: " + info.owner_name : "عربية حرة")
        : "عربية ملك الشركة — مفيش أجرة صاحب عربية";
    }
    updateCalc();
  }

  /* ── اختيار مسار الكارتة ─────────────────────────────── */
  if (routePreset && tollCostInput) {
    routePreset.addEventListener("change", function () {
      var selectedText = routePreset.options[routePreset.selectedIndex].text;
      var price = parseFloat(routePreset.value);
      if (!isNaN(price)) {
        tollCostInput.value = price;
        if (routeNameHid) {
          var parts = selectedText.split(" (");
          routeNameHid.value = parts[0].trim();
        }
      } else {
        tollCostInput.value = "";
      }
      updateCalc();
    });
  }

  /* ── الحساب التلقائي ─────────────────────────────────── */
  function updateCalc() {
    var liters = safeNum(fuelLiters ? fuelLiters.value : 0);
    var ppL    = safeNum(fuelPrice  ? fuelPrice.value  : 0);
    var fCost  = liters * ppL;
    if (fuelDisplay) fuelDisplay.value = fmt(fCost);

    var isFree = false;
    if (vehicleSelect) {
      var info = vehiclesMap[vehicleSelect.value] || {};
      isFree = info.ownership_type === "free";
    }
    var ownerFee  = isFree ? safeNum(ownerFeeInput  ? ownerFeeInput.value  : 0) : 0;
    var driverFee = safeNum(driverFeeInput ? driverFeeInput.value : 0);
    var toll      = safeNum(tollCostInput  ? tollCostInput.value  : 0);
    var tripPrice = safeNum(tripPriceInput ? tripPriceInput.value : 0);

    var totalCost = fCost + toll + driverFee + ownerFee;
    var netProfit = tripPrice - totalCost;

    if (calcTotalCost) calcTotalCost.textContent = fmt(totalCost);
    if (calcNetProfit) {
      calcNetProfit.textContent = fmt(netProfit);
      calcNetProfit.style.color = netProfit >= 0 ? "#f5a623" : "#f87171";
    }
  }

  /* ── ربط الأحداث ─────────────────────────────────────── */
  [tripPriceInput, ownerFeeInput, driverFeeInput, fuelLiters, fuelPrice, tollCostInput]
    .forEach(function (el) { if (el) el.addEventListener("input", updateCalc); });

  if (vehicleSelect) vehicleSelect.addEventListener("change", updateOwnerDisplay);

  /* ── تشغيل أولي ──────────────────────────────────────── */
  updateOwnerDisplay();
  updateCalc();

})();
