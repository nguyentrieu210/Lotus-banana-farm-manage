frappe.ui.form.on("Daily Work Plan", {
  refresh(frm) {
    if (frm.doc.docstatus === 0 && frm.doc.price_approval_state === 'Pending') {
      frm.add_custom_button(__('Duyệt giá và giao việc'), () => {
        if (frm.is_dirty()) {frappe.msgprint(__('Lưu các thay đổi trước khi duyệt.')); return;}
        frappe.confirm(__('Duyệt đơn giá vượt niêm yết và giao toàn bộ kế hoạch này?'), async () => {
          await frappe.call({method:'lotus_farm.mobile_assignment.approve_price',args:{plan:frm.doc.name},freeze:true});
          frm.reload_doc();
        });
      });
    }
    if (frm.doc.docstatus !== 1) return;
    frm.add_custom_button(__("Tính nhu cầu vật tư"), async () => {
      const response = await frappe.call({method: "lotus_farm.daily_api.create_requirements", args: {work_plan: frm.doc.name}, freeze: true});
      if (response.message.length === 1) frappe.set_route("Form", "Material Requirement", response.message[0]);
      else frappe.set_route("List", "Material Requirement", {work_plan: frm.doc.name});
    });
    for (const [label, doctype] of [["Ghi kết quả", "Daily Work Result"], ["Bố trí nhân công", "Labor Allocation"]]) {
      frm.add_custom_button(__(label), () => {
        const choices = frm.doc.lines.map(row => ({label: `${row.idx}. ${row.work_type} — ${row.farm_plot}`, row}));
        const dialog = new frappe.ui.Dialog({title: __(label), fields: [{fieldname: "task", label: "Công việc", fieldtype: "Select", options: choices.map(c => c.label), reqd: 1}], primary_action_label: "Tạo phiếu", primary_action(values) {
          const row = choices.find(c => c.label === values.task).row;
          const scope = Object.fromEntries(["farm", "farm_block", "farm_plot", "crop_cycle", "sucker_selection_batch"].map(key => [key, row[key]]));
          dialog.hide();
          frappe.new_doc(doctype, {...scope, posting_date: frm.doc.posting_date, work_plan: frm.doc.name, work_plan_line: row.name});
        }});
        dialog.show();
      });
    }
  },
  farm(frm) {frm.set_query("farm_block", "lines", () => ({filters: {farm: frm.doc.farm, active: 1}}));},
  setup(frm) {
    frm.set_query("farm_block", "lines", () => ({filters: {farm: frm.doc.farm, active: 1}}));
    frm.set_query("farm_plot", "lines", (doc, cdt, cdn) => ({filters: {farm: doc.farm, farm_block: locals[cdt][cdn].farm_block, active: 1}}));
    frm.set_query("crop_cycle", "lines", (doc, cdt, cdn) => ({filters: {farm: doc.farm, farm_plot: locals[cdt][cdn].farm_plot, status: ["!=", "Closed"]}}));
    frm.set_query("sucker_selection_batch", "lines", (doc, cdt, cdn) => ({filters: {crop_cycle: locals[cdt][cdn].crop_cycle}}));
    frm.set_query("norm_profile", "lines", (doc, cdt, cdn) => ({filters: {farm: doc.farm, work_type: locals[cdt][cdn].work_type, approval_state: "Approved"}}));
  }
});

