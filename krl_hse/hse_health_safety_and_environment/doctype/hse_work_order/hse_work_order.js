frappe.ui.form.on("HSE Work Order", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Add Workplace Area"), () => {
				frappe.new_doc("HSE Workplace Area", {
					branch: frm.doc.branch,
					work_order: frm.doc.name,
				});
			});
		}
	},
});
