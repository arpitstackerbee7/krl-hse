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

Branch names below are the ones on KRL's demo site. Branch codes follow the plan: J, V, T and
HO until KRL confirms.
"""

import frappe

DOMAIN = "krl-demo.example"

BRANCHES = [
	# (branch name, HSE code, head office?)
	("Head Office", "HO", 1),
	("KRL - KJBPSL (JSW) Jharsuguda", "J", 0),
	("KRL - VSP (RINL)", "V", 0),
	("Athagarh", "T", 0),
]

# One dummy person per role. (key, role, first name, branches or None for all)
USERS = [
	("director", "Director", "TEST Director", None),
	("hse_head", "HSE Head", "TEST HSE Head", None),
	("ho_hse", "HO HSE Team", "TEST HO HSE Member", None),
	("bhse_t", "Branch HSE Head", "TEST Athagarh HSE Head", ["Athagarh"]),
	("bhse_j", "Branch HSE Head", "TEST Jharsuguda HSE Head", ["KRL - KJBPSL (JSW) Jharsuguda"]),
	("officer_t", "HSE Officer", "TEST Athagarh HSE Officer", ["Athagarh"]),
	("hse_sup_t", "HSE Supervisor", "TEST Athagarh HSE Supervisor", ["Athagarh"]),
	("bhead_t", "Branch Head", "TEST Athagarh Branch Head", ["Athagarh"]),
	("bhead_j", "Branch Head", "TEST Jharsuguda Branch Head", ["KRL - KJBPSL (JSW) Jharsuguda"]),
	("dept_t", "Branch Department Head", "TEST Athagarh Maintenance Head", ["Athagarh"]),
	("site_sup_t", "Site Supervisor", "TEST Athagarh Site Supervisor", ["Athagarh"]),
	("store_t", "Store In-charge", "TEST Athagarh Store In-charge", ["Athagarh"]),
]

WORK_ORDERS = [
	{
		"branch": "KRL - KJBPSL (JSW) Jharsuguda",
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
		"branch": "Athagarh",
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
	# (branch, job code of its work or None, area name, division type, details, leader, members)
	(
		"Athagarh",
		"TEST-ATH",
		"TEST Loading Yard",
		"Location",
		"TEST: open yard near gate 1",
		"TEST Yard Lead",
		["TEST Yard Member A", "TEST Yard Member B"],
	),
	(
		"Athagarh",
		"TEST-ATH",
		"TEST Workshop",
		"Work",
		"TEST: maintenance workshop",
		"TEST Workshop Lead",
		["TEST Workshop Member A", "TEST Workshop Member B"],
	),
	(
		"KRL - KJBPSL (JSW) Jharsuguda",
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


def load(password=None):
	"""Create the demo data. Safe to run twice: existing TEST records are skipped."""
	frappe.flags.in_demo_seed = True
	_ensure_branches()
	_ensure_users(password)
	_ensure_work_orders()
	_ensure_areas()
	frappe.db.commit()
	print(f"Demo data loaded. Test logins end with @{DOMAIN}.")


def _ensure_branches():
	for name, code, head_office in BRANCHES:
		if frappe.db.exists("Branch", name):
			current = frappe.db.get_value("Branch", name, "hse_branch_code")
			if current and current != code:
				print(f"Branch {name} already has code {current}; leaving it.")
				continue
			if not current:
				print(f"Giving existing branch {name} the HSE Branch Code {code}.")
				frappe.db.set_value(
					"Branch", name, {"hse_branch_code": code, "hse_is_head_office": head_office}
				)
			continue
		frappe.get_doc(
			{"doctype": "Branch", "branch": name, "hse_branch_code": code, "hse_is_head_office": head_office}
		).insert(ignore_permissions=True)


def _ensure_users(password):
	for key, role, first_name, branches in USERS:
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
		for branch in branches or []:
			frappe.get_doc(
				{"doctype": "User Permission", "user": user_email, "allow": "Branch", "for_value": branch}
			).insert(ignore_permissions=True)


def _ensure_work_orders():
	for values in WORK_ORDERS:
		if frappe.db.exists("HSE Work Order", {"job_code": values["job_code"]}):
			continue
		doc = frappe.get_doc({"doctype": "HSE Work Order", **values})
		for line in doc.service_lines:
			if line.uom and not frappe.db.exists("UOM", line.uom):
				line.uom = None
		doc.insert(ignore_permissions=True)


def _ensure_areas():
	for branch, job, name, division, details, leader, members in AREAS:
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
