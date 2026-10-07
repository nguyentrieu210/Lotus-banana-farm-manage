frappe.ui.form.on("Material Requirement", {
  refresh(frm) {
    if (frm.doc.docstatus !== 1) return;
    frm.add_custom_button(__("Kiểm tra vật tư / đề nghị mua"), () => {
      const dialog = new frappe.ui.Dialog({title: "Vật tư còn trong kho", fields: [
        {fieldname: "warehouse", label: "Kho", fieldtype: "Link", options: "Warehouse", reqd: 1, get_query: () => ({filters: {company: frm.doc.company, is_group: 0, disabled: 0}})},
        {fieldname: "schedule_date", label: "Ngày cần", fieldtype: "Date", reqd: 1, default: frm.doc.posting_date}
      ], primary_action_label: "Kiểm tra", async primary_action(values) {
        const response = await frappe.call({method: "lotus_farm.daily_api.material_availability", args: {requirement: frm.doc.name, warehouse: values.warehouse}});
        const rows = response.message.rows;
        const escape = value => frappe.utils.escape_html(String(value));
        const html = `<table class="table"><thead><tr><th>Vật tư</th><th>Cần</th><th>Còn khả dụng</th><th>Thiếu</th></tr></thead><tbody>${rows.map(r => `<tr><td>${escape(r.item)} (${escape(r.uom)})</td><td>${escape(r.required_qty)}</td><td>${escape(r.available_qty)}</td><td>${escape(r.shortage_qty)}</td></tr>`).join("")}</tbody></table>`;
        frappe.msgprint({title: "Nhu cầu và tồn kho", message: html, primary_action: {label: "Tạo đề nghị mua phần thiếu", action: async () => {
          const result = await frappe.call({method: "lotus_farm.daily_api.create_material_request", args: {requirement: frm.doc.name, warehouse: values.warehouse, schedule_date: values.schedule_date}, freeze: true});
          frappe.set_route("Form", "Material Request", result.message.material_request);
        }}});
        dialog.hide();
      }});
      dialog.show();
    });
  }
});
