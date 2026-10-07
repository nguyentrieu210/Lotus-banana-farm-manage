frappe.ui.form.on('Packout Run', {
    refresh(frm) {
        if (frm.is_new() || frm.is_dirty()) return;
        if (frm.doc.docstatus === 0 && frm.doc.qc_state === 'Hold' && frappe.user.has_role('Lotus QC Manager')) {
            frm.add_custom_button(__('QC duyệt đóng gói'), async () => {
                await frm.set_value('qc_state', 'Released');
                await frm.save();
            });
        }
        if (frm.doc.docstatus === 1 && frm.doc.qc_state === 'Released' &&
            (frm.doc.outputs || []).length > 1 && frappe.user.has_role('Lotus Stock Reviewer')) {
            frm.add_custom_button(__('Nhập giá vốn thành phẩm'), () => {
                const fields = (frm.doc.outputs || []).map((row, index) => ({
                    fieldname: `rate_${index}`,
                    fieldtype: 'Currency',
                    label: __(`Giá vốn/kg — ${row.item}`),
                    reqd: 1,
                    default: row.valuation_rate || null
                }));
                const dialog = new frappe.ui.Dialog({
                    title: __('Giá vốn cho mẻ nhiều thành phẩm'),
                    fields,
                    primary_action_label: __('Ghi nhận giá vốn'),
                    primary_action: async values => {
                        const rates = {};
                        (frm.doc.outputs || []).forEach((row, index) => {
                            rates[row.item] = values[`rate_${index}`];
                        });
                        await frappe.call('lotus_farm.stock_bridge.set_output_valuation', {
                            packout: frm.doc.name,
                            rates: JSON.stringify(rates)
                        });
                        dialog.hide();
                        await frm.reload_doc();
                    }
                });
                dialog.show();
            });
        }
        if (frm.doc.docstatus === 1 &&
            (frappe.user.has_role('Lotus Packing Supervisor') || frappe.user.has_role('Lotus Stock Reviewer'))) {
            frm.add_custom_button(__('Tạo phiếu kho nháp'), async () => {
                const result = await frappe.call('lotus_farm.stock_bridge.make_repack_entry', { packout: frm.doc.name });
                frappe.set_route('Form', 'Stock Entry', result.message.stock_entry);
            });
        }
    }
});
