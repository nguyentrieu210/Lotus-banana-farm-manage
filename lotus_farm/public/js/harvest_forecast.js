frappe.ui.form.on('Harvest Forecast', {
    refresh(frm) {
        frm.set_df_property('allocations', 'read_only', 1);
        if (frm.is_new() || frm.is_dirty()) return;
        if (frm.doc.supply_state === 'Draft' && frappe.user.has_role('Lotus Farm Manager')) {
            frm.add_custom_button(__('Duyệt dự thu'), () => {
                frappe.confirm(__('Giữ nguyên nguồn và hệ số của bản dự thu này?'), async () => {
                    await frm.set_value('supply_state', 'Released');
                    await frm.save();
                });
            });
        }
        if (frm.doc.supply_state !== 'Released' || !frappe.user.has_role('Lotus Sales Planner')) return;
        frm.add_custom_button(__('Giữ hàng cho đơn'), () => {
            const event_id = crypto.randomUUID();
            const dialog = new frappe.ui.Dialog({
                title: __('Giữ dự thu cho một dòng đơn hàng'),
                fields: [
                    { fieldname: 'sales_order', fieldtype: 'Link', options: 'Sales Order', label: __('Đơn hàng'), reqd: 1,
                      onchange: async () => {
                        const name = dialog.get_value('sales_order');
                        dialog.set_value('sales_order_item', '');
                        if (!name) return;
                        const result = await frappe.call('frappe.client.get', { doctype: 'Sales Order', name });
                        const rows = result.message.items.filter(row => row.item_code === frm.doc.item);
                        dialog.set_df_property('sales_order_item', 'options', rows.map(row => ({
                            value: row.name, label: `${row.idx} — ${row.item_name} — ${row.qty} ${row.uom}`
                        })));
                      } },
                    { fieldname: 'sales_order_item', fieldtype: 'Select', label: __('Dòng sản phẩm'), options: [], reqd: 1 },
                    { fieldname: 'qty_kg', fieldtype: 'Float', label: __('Số kg giữ'), reqd: 1 }
                ],
                primary_action_label: __('Giữ hàng'),
                primary_action: async values => {
                    await frappe.call('lotus_farm.allocations.reserve', { ...values, forecast: frm.doc.name, client_event_id: event_id });
                    dialog.hide();
                    await frm.reload_doc();
                }
            });
            dialog.show();
        });
        const reserved = (frm.doc.allocations || []).filter(row => row.allocation_state === 'Reserved');
        if (!reserved.length) return;
        frm.add_custom_button(__('Bỏ giữ dự thu'), () => {
            frappe.prompt([{ fieldname: 'allocation', fieldtype: 'Select', label: __('Phần hàng đang giữ'), reqd: 1,
                options: reserved.map(row => ({ value: row.name, label: `${row.sales_order} — ${row.reserved_qty_kg} kg` })) }],
                async values => {
                    await frappe.call('lotus_farm.allocations.release', { forecast: frm.doc.name, allocation: values.allocation });
                    await frm.reload_doc();
                }, __('Bỏ giữ dự thu'));
        });
        frm.add_custom_button(__('Nối với hàng đã giữ trong kho'), () => {
            frappe.prompt([
                { fieldname: 'allocation', fieldtype: 'Select', label: __('Phần dự thu đã giữ'), reqd: 1,
                  options: reserved.map(row => ({ value: row.name, label: `${row.sales_order} — ${row.reserved_qty_kg} kg` })) },
                { fieldname: 'stock_reservation', fieldtype: 'Link', options: 'Stock Reservation Entry', label: __('Phiếu giữ hàng thật'), reqd: 1 }
            ], async values => {
                await frappe.call('lotus_farm.stock_bridge.link_stock_reservation', { ...values, forecast: frm.doc.name });
                await frm.reload_doc();
            }, __('Nối giữ dự thu với giữ hàng trong kho'));
        });
    }
});
