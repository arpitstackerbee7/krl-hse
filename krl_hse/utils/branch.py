import re

import frappe
from frappe import _

CODE_PATTERN = re.compile(r"^[A-Za-z0-9]+$")


def validate_branch(doc, method=None):
	"""Keep the HSE Branch Code clean and different for every branch."""
	code = (doc.get("hse_branch_code") or "").strip()
	doc.hse_branch_code = code or None
	if not code:
		return

	if not CODE_PATTERN.match(code):
		frappe.throw(
			_("HSE Branch Code {0} may only have letters and digits, so it can sit inside a document number.").format(
				frappe.bold(code)
			)
		)

	clash = frappe.db.get_value("Branch", {"hse_branch_code": code, "name": ("!=", doc.name)}, "name")
	if clash:
		frappe.throw(
			_("HSE Branch Code {0} is already used by branch {1}.").format(frappe.bold(code), frappe.bold(clash))
		)
