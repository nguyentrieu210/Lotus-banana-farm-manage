frappe.ui.form.on('Packout Run', {
    refresh(frm) {
        if (frm.is_new() || frm.is_dirty()) return;
        if (frm.doc.docstatus === 0 && frm.doc.qc_state === 'Hold' && frappe.user.has_role('Lotus QC Manager')) {
            frm.add_custom_button(__('QC duyệt đóng gói'), async () => {
                await frm.set_value('qc_state', 'Released');
                await frm.save();
            });
        }
        if (frm.doc.docstatus === 1 && frappe.user.has_role('Lotus Packing Supervisor')) {
            frm.add_custom_button(__('Tạo phiếu kho nháp'), async () => {
                const result = await frappe.call('lotus_farm.stock_bridge.make_repack_entry', { packout: frm.doc.name });
                frappe.set_route('Form', 'Stock Entry', result.message.stock_entry);
            });
        }
    }
});
