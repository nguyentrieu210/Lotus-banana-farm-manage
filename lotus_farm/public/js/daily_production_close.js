frappe.ui.form.on("Daily Production Close", {
  refresh(frm) {
    if (frm.doc.docstatus !== 0 || !frm.doc.farm || !frm.doc.posting_date) return;
    frm.add_custom_button(__("Kiểm tra trước khi chốt"), async () => {
      const response = await frappe.call({method: "lotus_farm.daily_api.preview_close", args: {farm: frm.doc.farm, posting_date: frm.doc.posting_date}});
      const escape = value => frappe.utils.escape_html(String(value));
      frappe.msgprint({title: "Đối chiếu ngày", message: `<ul>${response.message.map(row => `<li>${row.status === "Pass" ? "✓" : "⚠"} ${escape(row.message)} ${escape(row.reference_name || "")}</li>`).join("")}</ul>`});
    });
  }
});
