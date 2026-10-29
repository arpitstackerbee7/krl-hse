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


def make_work_order(branch, job_code, **kw):
	values = {
		"doctype": "HSE Work Order",
		"branch": branch,
		"job_code": job_code,
		"work_title": f"TEST work {job_code}",
		"client_name": "TEST Client",
	}
	values.update(kw)
	return frappe.get_doc(values).insert(ignore_permissions=True)


def make_area(branch, area_name, **kw):
	values = {"doctype": "HSE Workplace Area", "branch": branch, "area_name": area_name}
	values.update(kw)
	return frappe.get_doc(values).insert(ignore_permissions=True)


def current_fy():
	"""Financial year label for today, as HSE Settings is set up."""
	from frappe.utils import nowdate

	from krl_hse.utils.numbering import financial_year_label, month_number

	settings = frappe.get_cached_doc("HSE Settings")
	return financial_year_label(nowdate(), month_number(settings.fy_start_month), settings.fy_label_format)
