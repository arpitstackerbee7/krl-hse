"""Demo data for the Phase 1 walk-through. NOT part of the live install.

Nothing here runs on install or migrate. It is run by hand on a demo or test site:

	bench --site <site> execute krl_hse.demo.seed.load
	bench --site <site> execute krl_hse.demo.seed.clear

Rules it follows:
  * Every record it makes carries a TEST name or a TEST address, so it is easy to find.
  * People have dummy names. Email addresses use the reserved example domain, so nothing
    can reach a real person.
  * It never edits an existing record except to give an existing Branch its HSE Branch Code,
    and it says so before it does.
  * `clear` archives by default (cancels work orders, disables areas and users). It deletes
    only when called with delete=1, which is for KRL-approved clean-up before go-live.

Branches are never created here and no branch name is fixed in this file. The branches already on
the site are given their HSE Branch Code by the person running the load:

	bench --site <site> execute krl_hse.demo.seed.load --kwargs \\
		"{'branches': {'<branch name>': '<code>', ...}, 'head_office': '<branch name>'}"

If every branch already has its code, `load` needs no arguments. The sample people and records refer
to branches by code. J and T carry the two sample jobs. A person or record whose code is not on the
site is skipped, and the load says so.
"""

import json

import frappe

DOMAIN = "krl-demo.example"

# One dummy person per role. (key, role, first name, branch codes, or None for all branches)
USERS = [
	("director", "Director", "TEST Director", None),
	("hse_head", "HSE Head", "TEST HSE Head", None),
	("ho_hse", "HO HSE Team", "TEST HO HSE Member", None),
	("bhse_t", "Branch HSE Head", "TEST Athagarh HSE Head", ["T"]),
	("bhse_j", "Branch HSE Head", "TEST Jharsuguda HSE Head", ["J"]),
	("officer_t", "HSE Officer", "TEST Athagarh HSE Officer", ["T"]),
	("hse_sup_t", "HSE Supervisor", "TEST Athagarh HSE Supervisor", ["T"]),
	("bhead_t", "Branch Head", "TEST Athagarh Branch Head", ["T"]),
	("bhead_j", "Branch Head", "TEST Jharsuguda Branch Head", ["J"]),
	("dept_t", "Branch Department Head", "TEST Athagarh Maintenance Head", ["T"]),
	("site_sup_t", "Site Supervisor", "TEST Athagarh Site Supervisor", ["T"]),
	("store_t", "Store In-charge", "TEST Athagarh Store In-charge", ["T"]),
]

WORK_ORDERS = [
	{
		"branch": "J",
		"job_code": "TEST-SLAG",
		"work_title": "TEST Slag handling at the client plant",
		"client_name": "TEST Client Steel Limited",
		"plant_name": "TEST Client Plant, Sambalpur",
		"po_number": "TEST-4500188553",
		"po_date": "2024-06-01",
		"start_date": "2024-07-01",
		"completion_date": "2025-06-30",
		"client_safety_terms": "<p>TEST: workers must be above 18 years. Working height as stated per service.</p>",
		"service_lines": [
			{
				"service_code": "TEST-S1",
				"description": "TEST Handling of furnace slag",
				"qty": 340000,
				"uom": "Tonne",  # dropped by _ensure_work_orders if this UOM does not exist on the site
				"working_height_m": 0,
			},
			{
				"service_code": "TEST-S2",
				"description": "TEST Cleaning of slag pit",
				"qty": 1,
				"working_height_m": 3,
			},
		],
		"contacts": [
			{"contact_role": "Branch Head", "contact_name": "TEST Jharsuguda Branch Head"},
			{"contact_role": "HSE Head", "contact_name": "TEST Jharsuguda HSE Head"},
			{"contact_role": "Client Representative", "contact_name": "TEST Client Representative"},
			{"contact_role": "Client HSE Representative", "contact_name": "TEST Client HSE Officer"},
		],
	},
	{
		"branch": "T",
		"job_code": "TEST-ATH",
		"work_title": "TEST Material handling at Athagarh",
		"client_name": "TEST Client Metals Limited",
		"plant_name": "TEST Client Plant, Athagarh",
		"po_number": "TEST-ATH-001",
		"po_date": "2026-04-01",
		"start_date": "2026-04-15",
		"completion_date": "2027-03-31",
		"service_lines": [{"service_code": "TEST-A1", "description": "TEST Loading and unloading", "qty": 1}],
		"contacts": [{"contact_role": "Branch Head", "contact_name": "TEST Athagarh Branch Head"}],
	},
]

AREAS = [
	# (branch code, job code of its work or None, area name, division type, details, leader, members)
	(
		"T",
		"TEST-ATH",
		"TEST Loading Yard",
		"Location",
		"TEST: open yard near gate 1",
		"TEST Yard Lead",
		["TEST Yard Member A", "TEST Yard Member B"],
	),
	(
		"T",
		"TEST-ATH",
		"TEST Workshop",
		"Work",
		"TEST: maintenance workshop",
		"TEST Workshop Lead",
		["TEST Workshop Member A", "TEST Workshop Member B"],
	),
	(
		"J",
		"TEST-SLAG",
		"TEST Slag Pit",
		"Location",
		"TEST: pit side",
		"TEST Pit Lead",
		["TEST Pit Member A", "TEST Pit Member B"],
	),
]


def email_for(key):
	return f"test.{key}@{DOMAIN}"


def load(password=None, branches=None, head_office=None):
	"""Create the demo data. Safe to run twice: existing TEST records are skipped.

	branches     {branch name: HSE Branch Code} for branches that do not have their code yet. A branch that
	             already has a code keeps it. Branches are never created here.
	head_office  the name of the head office branch, among those in `branches`.
	"""
	frappe.flags.in_demo_seed = True
	sites = _prepare_branches(branches, head_office)
	if not sites:
		return

	_ensure_users(password, sites)
	_ensure_work_orders(sites)
	_ensure_areas(sites)
	frappe.db.commit()
	print(f"Demo data loaded for branches {', '.join(f'{c} ({n})' for c, n in sorted(sites.items()))}.")
	print(f"Test logins end with @{DOMAIN}.")


def _prepare_branches(branches, head_office):
	"""Give the named branches their HSE Branch Code and return {code: branch name} for the site."""
	if isinstance(branches, str):
		branches = json.loads(branches)

	if branches:
		missing = [name for name in branches if not frappe.db.exists("Branch", name)]
		if missing:
			print(f"These branches are not on this site, so nothing was loaded: {', '.join(missing)}.")
			return None
		if head_office and head_office not in branches:
			print(f"The head office {head_office} is not among the branches given, so nothing was loaded.")
			return None

		for name, code in branches.items():
			current = frappe.db.get_value("Branch", name, "hse_branch_code")
			if current and current != code:
				print(f"Branch {name} already has code {current}; leaving it.")
				continue
			clash = frappe.db.get_value("Branch", {"hse_branch_code": code, "name": ["!=", name]}, "name")
			if clash:
				print(f"Code {code} is already used by branch {clash}; {name} is left without it.")
				continue
			if not current:
				print(f"Giving branch {name} the HSE Branch Code {code}.")
				frappe.db.set_value(
					"Branch", name, {"hse_branch_code": code, "hse_is_head_office": int(name == head_office)}
				)

	rows = frappe.get_all(
		"Branch", filters={"hse_branch_code": ["is", "set"]}, fields=["name", "hse_branch_code"]
	)
	if not rows:
		names = ", ".join(frappe.get_all("Branch", pluck="name")) or "none"
		print(
			"No branch has an HSE Branch Code yet, so nothing was loaded.\n"
			f"Branches on this site: {names}.\n"
			"Run again with branches={'<branch name>': '<code>', ...} and head_office='<branch name>'."
		)
		return None
	return {row.hse_branch_code: row.name for row in rows}


def _ensure_users(password, sites):
	for key, role, first_name, codes in USERS:
		missing = [c for c in codes or [] if c not in sites]
		if missing:
			print(f"Skipping {first_name}: no branch with code {', '.join(missing)} on this site.")
			continue
		user_email = email_for(key)
		if frappe.db.exists("User", user_email):
			continue
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": user_email,
				"first_name": first_name,
				"send_welcome_email": 0,
				"enabled": 1,
				"roles": [{"role": role}],
			}
		)
		if password:
			user.new_password = password
		user.flags.no_welcome_mail = True
		user.insert(ignore_permissions=True)
		for code in codes or []:
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": user_email,
					"allow": "Branch",
					"for_value": sites[code],
				}
			).insert(ignore_permissions=True)


def _ensure_work_orders(sites):
	for values in WORK_ORDERS:
		if values["branch"] not in sites:
			print(f"Skipping work order {values['job_code']}: no branch with code {values['branch']}.")
			continue
		if frappe.db.exists("HSE Work Order", {"job_code": values["job_code"]}):
			continue
		doc = frappe.get_doc({"doctype": "HSE Work Order", **values, "branch": sites[values["branch"]]})
		for line in doc.service_lines:
			if line.uom and not frappe.db.exists("UOM", line.uom):
				line.uom = None
		doc.insert(ignore_permissions=True)


def _ensure_areas(sites):
	for code, job, name, division, details, leader, members in AREAS:
		if code not in sites:
			print(f"Skipping area {name}: no branch with code {code}.")
			continue
		branch = sites[code]
		work_order = frappe.db.get_value("HSE Work Order", {"job_code": job}, "name") if job else None
		if frappe.db.exists("HSE Workplace Area", {"branch": branch, "area_name": name}):
			continue
		team = [
			{"team_role": "Team Lead", "member_name": leader, "category": "SL", "from_date": "2026-04-01"}
		]
		for index, member in enumerate(members, start=1):
			team.append(
				{
					"team_role": f"Member {index}",
					"member_name": member,
					"category": "Worker",
					"from_date": "2026-04-01",
				}
			)
		frappe.get_doc(
			{
				"doctype": "HSE Workplace Area",
				"branch": branch,
				"work_order": work_order,
				"area_name": name,
				"division_type": division,
				"location_details": details,
				"team": team,
			}
		).insert(ignore_permissions=True)


def clear(delete=0):
	"""Archive the demo data: cancel work orders, disable areas and users.

	With delete=1 the records are removed for good. Do that only after KRL has approved the clean-up.
	"""
	delete = int(delete)

	for name in frappe.get_all("HSE Workplace Area", filters={"area_name": ["like", "TEST%"]}, pluck="name"):
		if delete:
			frappe.delete_doc("HSE Workplace Area", name, force=True, ignore_permissions=True)
		else:
			frappe.db.set_value("HSE Workplace Area", name, "disabled", 1)

	for name in frappe.get_all("HSE Work Order", filters={"job_code": ["like", "TEST%"]}, pluck="name"):
		if delete:
			frappe.delete_doc("HSE Work Order", name, force=True, ignore_permissions=True)
		else:
			frappe.db.set_value("HSE Work Order", name, "status", "Cancelled")

	for key, *_rest in USERS:
		user_email = email_for(key)
		if not frappe.db.exists("User", user_email):
			continue
		if delete:
			for perm in frappe.get_all("User Permission", filters={"user": user_email}, pluck="name"):
				frappe.delete_doc("User Permission", perm, force=True, ignore_permissions=True)
			frappe.delete_doc("User", user_email, force=True, ignore_permissions=True)
		else:
			frappe.db.set_value("User", user_email, "enabled", 0)

	frappe.db.commit()
	print("Demo data deleted." if delete else "Demo data archived.")
