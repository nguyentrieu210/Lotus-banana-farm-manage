frappe.ui.form.on("Harvest Forecast", {
  refresh(frm) {
    if (frm.doc.docstatus !== 1) return;
    frappe.call({
      method: "lotus_farm.api.v1.availability.get",
      type: "GET",
      args: {forecast: frm.doc.name},
      callback(r) {
        if (!r.message) return;
        const x = r.message;
        frm.dashboard.set_headline(__(
          "Current availability: {0} kg | Reserved: {1} kg | Retired into stock: {2} kg | Shortage: {3} kg",
          [x.available_to_promise_kg, x.committed_qty_kg, x.materialized_qty_kg, x.shortage_kg]
        ));
      }
    });
  }
});
