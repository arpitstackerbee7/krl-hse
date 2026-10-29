// Branch rules every HSE form shares. The list of HSE document types that carry a `branch`
// comes from `hse_branch_doctypes` in hooks.py, sent to the browser at login.
$(document).on("form-refresh", (event, frm) => {
	const hse_doctypes = (frappe.boot && frappe.boot.hse_branch_doctypes) || [];
	if (!hse_doctypes.includes(frm.doctype) || !frm.fields_dict.branch) return;

	// A site that has been disabled for HSE is not offered when choosing a branch.
	frm.set_query("branch", () => ({ filters: { hse_disabled: 0 } }));

	// A user limited to one branch should not have to pick it on every new document. Frappe fills a
	// Link field on its own only when the User Permission is marked "Is Default", so this does the
	// same for the single-branch case.
	if (!frm.is_new() || frm.doc.branch) return;

	const permissions = (frappe.defaults.get_user_permissions() || {}).Branch || [];
	const allowed = frappe.perm.filter_allowed_docs_for_doctype(permissions, frm.doctype, false);
	if (allowed.length === 1) {
		frm.set_value("branch", allowed[0]);
	}
});
