frappe.ui.form.on("HSE Settings", {
	setup(frm) {
		frm.set_query("reference_doctype", "document_codes", () => ({
			filters: { module: "HSE Health Safety and Environment", istable: 0, issingle: 0 },
		}));
	},

	refresh(frm) {
		frm.add_custom_button(__("Preview a Number"), () => {
			const doctypes = (frm.doc.document_codes || []).map((row) => row.reference_doctype);
			frappe.prompt(
				[
					{ fieldname: "doctype", label: __("Document Type"), fieldtype: "Select", options: doctypes, reqd: 1 },
					{
						fieldname: "branch",
						label: __("Branch"),
						fieldtype: "Link",
						options: "Branch",
						reqd: 1,
						get_query: () => ({ filters: { hse_branch_code: ["is", "set"] } }),
					},
					{ fieldname: "job", label: __("Job Code"), fieldtype: "Data" },
					{ fieldname: "on_date", label: __("Document Date"), fieldtype: "Date", default: frappe.datetime.get_today() },
				],
				(values) => {
					frappe.call({
						method: "krl_hse.utils.numbering.preview_number",
						args: values,
						callback: (r) => {
							frappe.msgprint({
								title: __("Next Number"),
								message: `<div style="font-size:1.4em;font-weight:600">${frappe.utils.escape_html(r.message)}</div><p class="text-muted">${__("This is only a preview. No number is used up.")}</p>`,
							});
						},
					});
				},
				__("Preview a Number"),
				__("Show")
			);
		});
	},
});
