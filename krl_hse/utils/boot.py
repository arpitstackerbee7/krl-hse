import frappe


def boot_session(bootinfo):
	"""Tell the browser which HSE document types carry a branch (see hooks.hse_branch_doctypes)."""
	bootinfo.hse_branch_doctypes = frappe.get_hooks("hse_branch_doctypes")
