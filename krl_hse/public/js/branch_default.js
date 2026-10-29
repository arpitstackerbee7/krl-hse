// A user who is limited to one branch should not have to pick it on every new HSE document.
// Frappe fills a Link field on its own only when the User Permission is marked "Is Default",
// so this does the same for the single-branch case, for every HSE document type that has a
// branch (the list comes from `hse_branch_doctypes` in hooks.py, sent to the browser at login).
$(document).on("form-refresh", (event, frm) => {
	const hse_doctypes = (frappe.boot && frappe.boot.hse_branch_doctypes) || [];
	if (!hse_doctypes.includes(frm.doctype) || !frm.is_new() || frm.doc.branch) return;
	if (!frm.fields_dict.branch) return;

	const permissions = (frappe.defaults.get_user_permissions() || {}).Branch || [];
	const allowed = frappe.perm.filter_allowed_docs_for_doctype(permissions, frm.doctype, false);
	if (allowed.length === 1) {
		frm.set_value("branch", allowed[0]);
	}
});
