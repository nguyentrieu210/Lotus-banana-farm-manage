frappe.ui.form.on("Supply Reconciliation", {
    refresh(frm) {
        if (frm.doc.docstatus !== 1 || frm.doc.state !== "Approved") return;
        frm.add_custom_button(__("Apply Reconciliation"), async () => {
            const result = await frappe.call(
                "lotus_farm.reconciliation.execute",
                { reconciliation: frm.doc.name }
            );
            if (result.message?.state === "Applied") {
                await frm.reload_doc();
            }
        }, __("Actions"));
    }
});
