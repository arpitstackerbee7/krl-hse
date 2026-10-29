frappe.ui.form.on("HSE Workplace Area", {
	setup(frm) {
		frm.set_query("work_order", () => ({
			filters: { branch: frm.doc.branch || undefined, status: ["!=", "Cancelled"] },
		}));
	},

	branch(frm) {
		// A work order belongs to one branch, so a changed branch clears a work order from another.
		if (frm.doc.work_order) {
			frm.set_value("work_order", null);
		}
	},
});
