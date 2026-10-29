"""Helpers shared by the app's tests."""

import frappe


def make_branch(name, code, head_office=0):
	if frappe.db.exists("Branch", name):
		frappe.db.set_value("Branch", name, {"hse_branch_code": code, "hse_is_head_office": head_office})
		return frappe.get_doc("Branch", name)
	return frappe.get_doc(
		{"doctype": "Branch", "branch": name, "hse_branch_code": code, "hse_is_head_office": head_office}
	).insert(ignore_permissions=True)


def set_document_code(doctype, code, number_format=""):
	"""Put a document code row into HSE Settings for a test."""
	settings = frappe.get_doc("HSE Settings")
	settings.document_codes = [r for r in settings.document_codes if r.reference_doctype != doctype]
	settings.append(
		"document_codes",
		{"reference_doctype": doctype, "document_code": code, "number_format": number_format},
	)
	settings.save(ignore_permissions=True)
	frappe.clear_cache(doctype="HSE Settings")
	return settings
