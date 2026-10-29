"""Branch-level access for HSE records (BRD section 14: branch roles act on their own branch only).

Rules:
  * Administrator, System Manager and any role listed under "Roles That See All Branches" in
    HSE Settings see every branch.
  * Everyone else sees only the branches given to them as User Permissions on Branch.
  * A user who has no branch given sees nothing, so a missing User Permission can never
    open all branches by mistake.

Frappe applies User Permissions to link fields by itself. These hooks add the "sees nothing"
rule and make the branch rule independent of how a User Permission was set up: a User
Permission limited to other document types does not widen access here.
"""

import frappe


def get_all_branch_roles():
	settings = frappe.get_cached_doc("HSE Settings")
	return {row.role for row in settings.all_branch_roles}


def sees_all_branches(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	roles = set(frappe.get_roles(user))
	return "System Manager" in roles or bool(roles & get_all_branch_roles())


def get_allowed_branches(user=None, doctype=None):
	"""Branches given to a user. A permission limited to other document types does not count."""
	user = user or frappe.session.user
	rows = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": "Branch"},
		fields=["for_value", "applicable_for"],
	)
	return sorted({r.for_value for r in rows if not r.applicable_for or r.applicable_for == doctype})


def permission_query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if sees_all_branches(user):
		return ""

	branches = get_allowed_branches(user, doctype)
	if not branches:
		return "1=0"

	values = ", ".join(frappe.db.escape(b) for b in branches)
	return f"`tab{doctype}`.`branch` in ({values})"


def has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if sees_all_branches(user):
		return True

	branches = get_allowed_branches(user, doc.doctype)
	if not branches:
		return False

	# A record without a branch cannot be judged yet. The mandatory-field check refuses it on save.
	return not doc.get("branch") or doc.get("branch") in branches
