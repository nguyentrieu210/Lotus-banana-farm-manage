frappe.ui.form.on("Packout Run", {
  refresh(frm) {
    if (frm.doc.docstatus === 1 && frm.doc.qc_status === "Released" && !frm.doc.stock_entry) {
      frm.add_custom_button(__("Create Stock Receipt"), () => {
        frappe.call({
          method: "lotus_farm.stock.create_stock_entry",
          type: "POST",
          args: {packout_run: frm.doc.name},
          callback(r) {
            if (r.message) frappe.set_route("Form", "Stock Entry", r.message);
          }
        });
      });
    }
  }
});
