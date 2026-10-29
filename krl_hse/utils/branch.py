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
			_(
				"HSE Branch Code {0} may only have letters and digits, so it can sit inside a document number."
			).format(frappe.bold(code))
		)

	clash = frappe.db.get_value("Branch", {"hse_branch_code": code, "name": ("!=", doc.name)}, "name")
	if clash:
		frappe.throw(
			_("HSE Branch Code {0} is already used by branch {1}.").format(
				frappe.bold(code), frappe.bold(clash)
			)
		)


# People with access to a site (the "People With Access" list on the Branch form)
# --------------------------------------------------------------------------------
# A person is given a site as a Frappe User Permission on Branch that applies to every
# document type, which is the same thing the Branch form does behind the scenes. These
# methods are for whoever may edit the site (head office HSE roles, HR roles, System Manager).


def _site_permissions(branch, user=None):
	filters = {"allow": "Branch", "for_value": branch}
	if user:
		filters["user"] = user
	rows = frappe.get_all("User Permission", filters=filters, fields=["name", "user", "applicable_for"])
	# A permission limited to certain document types is not a site-wide access, so it is not shown
	# here and not removed from here.
	return [r for r in rows if not r.applicable_for]


@frappe.whitelist()
def get_branch_users(branch):
	"""The people given this site, with the HSE roles they hold."""
	frappe.has_permission("Branch", "write", doc=branch, throw=True)

	from krl_hse.setup.install import _load

	hse_roles = {r["role_name"] for r in _load("roles.json")["roles"]}
	people = []
	for row in _site_permissions(branch):
		full_name, enabled = frappe.db.get_value("User", row.user, ["full_name", "enabled"]) or (row.user, 0)
		people.append(
			{
				"user": row.user,
				"full_name": full_name,
				"enabled": enabled,
				"roles": sorted(set(frappe.get_roles(row.user)) & hse_roles),
			}
		)
	return sorted(people, key=lambda p: (p["full_name"] or "").lower())


@frappe.whitelist()
def grant_branch_access(branch, user):
	"""Give a person this site. Does nothing if they already have it."""
	frappe.has_permission("Branch", "write", doc=branch, throw=True)

	from krl_hse.utils.branch_access import sees_all_branches

	if not frappe.db.exists("Branch", branch):
		frappe.throw(_("Branch {0} does not exist.").format(frappe.bold(branch)))
	if user == "Administrator" or not frappe.db.get_value("User", {"name": user, "enabled": 1}):
		frappe.throw(_("{0} is not an enabled user.").format(frappe.bold(user)))
	if sees_all_branches(user):
		frappe.throw(
			_("{0} has a role that already sees every branch, so no branch needs to be given.").format(
				frappe.bold(user)
			)
		)

	if _site_permissions(branch, user):
		return {"added": 0}

	frappe.get_doc(
		{
			"doctype": "User Permission",
			"user": user,
			"allow": "Branch",
			"for_value": branch,
			"apply_to_all_doctypes": 1,
		}
	).insert(ignore_permissions=True)
	return {"added": 1}


@frappe.whitelist()
def revoke_branch_access(branch, user):
	"""Take this site away from a person. Their other sites are not touched."""
	frappe.has_permission("Branch", "write", doc=branch, throw=True)

	removed = 0
	for row in _site_permissions(branch, user):
		frappe.delete_doc("User Permission", row.name, ignore_permissions=True)
		removed += 1
	return {"removed": removed}
