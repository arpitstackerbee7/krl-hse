"""Setup that must exist before the HSE module can be used.

`ensure_setup` runs after install and after every migrate. It only adds what is missing and
never overwrites something KRL has changed.
"""

import json
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

DATA = Path(__file__).parent / "data"

BRANCH_FIELDS = {
	"Branch": [
		{
			"fieldname": "hse_section",
			"fieldtype": "Section Break",
			"label": "HSE",
			"insert_after": "branch",
		},
		{
			"fieldname": "hse_branch_code",
			"fieldtype": "Data",
			"label": "HSE Branch Code",
			"insert_after": "hse_section",
			"description": "Short code used in HSE document numbers, for example J. Must be different for every branch.",
		},
		{
			"fieldname": "hse_is_head_office",
			"fieldtype": "Check",
			"label": "Head Office",
			"insert_after": "hse_branch_code",
			"description": "Tick for the head office. Head office records are not tied to a plant.",
		},
	]
}


def after_install():
	ensure_setup()


def after_migrate():
	ensure_setup()


def ensure_setup():
	create_custom_fields(BRANCH_FIELDS, update=True)
	ensure_roles()
	seed_masters()
	ensure_settings_defaults()
	frappe.db.commit()


def _load(name):
	with open(DATA / name) as fh:
		return json.load(fh)


def ensure_roles():
	"""Create the system roles of BRD section 14.1 that do not exist yet."""
	for entry in _load("roles.json")["roles"]:
		if frappe.db.exists("Role", entry["role_name"]):
			continue
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": entry["role_name"],
				"desk_access": 1,
				"is_custom": 1,
			}
		).insert(ignore_permissions=True)


def seed_masters():
	"""Load the starting records of a master, but only while that master is empty.

	After that the records belong to KRL: a record it edits or deletes is not touched again.
	"""
	for doctype, records in _load("masters.json").items():
		if doctype.startswith("_") or not frappe.db.exists("DocType", doctype):
			continue
		if frappe.db.count(doctype):
			continue
		for record in records:
			frappe.get_doc({"doctype": doctype, **record}).insert(ignore_permissions=True)


def ensure_settings_defaults():
	"""Fill HSE Settings with the starting values.

	Roles that see all branches are loaded once. Document codes are loaded once for each
	document type, the first time that type exists, so a row KRL deletes is not brought back.
	"""
	if not frappe.db.exists("DocType", "HSE Settings"):
		return

	settings = frappe.get_doc("HSE Settings")
	changed = False

	if not settings.defaults_loaded:
		for entry in _load("roles.json")["roles"]:
			if entry.get("all_branches"):
				settings.append("all_branch_roles", {"role": entry["role_name"]})
		settings.defaults_loaded = 1
		changed = True

	seeded = set((settings.seeded_doctypes or "").split("\n")) - {""}
	for phase, rows in _load("document_codes.json").items():
		if phase.startswith("_"):
			continue
		for row in rows:
			doctype = row["reference_doctype"]
			if doctype in seeded or not frappe.db.exists("DocType", doctype):
				continue
			if not any(r.reference_doctype == doctype for r in settings.document_codes):
				settings.append("document_codes", row)
			seeded.add(doctype)
			changed = True

	if changed:
		settings.seeded_doctypes = "\n".join(sorted(seeded))
		settings.save(ignore_permissions=True)
