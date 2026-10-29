from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from krl_hse import hooks
from krl_hse.tests.utils import make_area, make_branch, make_user, make_work_order

DOMAIN = "krl-test.example"


def email(name):
	return f"test.{name}@{DOMAIN}"


class TestBranchAccess(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_branch("TEST Athagarh", "T")
		make_branch("TEST Jharsuguda", "J")
		make_branch("TEST Head Office", "HO", head_office=1)

		cls.order_t = make_work_order("TEST Athagarh", "ACC-T")
		cls.order_j = make_work_order("TEST Jharsuguda", "ACC-J")
		cls.area_t = make_area("TEST Athagarh", "TEST Access Area T")
		cls.area_j = make_area("TEST Jharsuguda", "TEST Access Area J")

		make_user(email("branch_hse_t"), ["Branch HSE Head"], branches=["TEST Athagarh"])
		make_user(email("branch_hse_j"), ["Branch HSE Head"], branches=["TEST Jharsuguda"])
		make_user(email("branch_hse_none"), ["Branch HSE Head"])
		make_user(email("ho_team"), ["HO HSE Team"])
		make_user(email("hse_head"), ["HSE Head"])
		make_user(email("director"), ["Director"])
		make_user(email("site_sup_t"), ["Site Supervisor"], branches=["TEST Athagarh"])
		make_user(email("employee_t"), ["Employee"], branches=["TEST Athagarh"])

	def tearDown(self):
		frappe.set_user("Administrator")

	def names(self, doctype, user):
		frappe.set_user(email(user))
		return set(frappe.get_list(doctype, pluck="name", limit_page_length=0))

	def test_branch_user_sees_only_own_branch(self):
		seen = self.names("HSE Work Order", "branch_hse_t")
		self.assertIn(self.order_t.name, seen)
		self.assertNotIn(self.order_j.name, seen)

		seen = self.names("HSE Workplace Area", "branch_hse_j")
		self.assertIn(self.area_j.name, seen)
		self.assertNotIn(self.area_t.name, seen)

	def test_branch_user_cannot_open_another_branch_record(self):
		frappe.set_user(email("branch_hse_t"))
		self.assertFalse(frappe.has_permission("HSE Work Order", "read", doc=self.order_j.name))
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("HSE Work Order", self.order_j.name).check_permission("read")

	def test_branch_user_cannot_create_for_another_branch(self):
		frappe.set_user(email("branch_hse_t"))
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc(
				{
					"doctype": "HSE Workplace Area",
					"branch": "TEST Jharsuguda",
					"area_name": "TEST Sneaky Area",
				}
			).insert()

	def test_branch_user_can_create_for_own_branch(self):
		frappe.set_user(email("branch_hse_t"))
		area = frappe.get_doc(
			{"doctype": "HSE Workplace Area", "branch": "TEST Athagarh", "area_name": "TEST Own Area"}
		).insert()
		self.assertTrue(area.name)

	def test_user_with_no_branch_sees_nothing(self):
		self.assertEqual(self.names("HSE Work Order", "branch_hse_none"), set())
		self.assertEqual(self.names("HSE Workplace Area", "branch_hse_none"), set())

	def test_head_office_roles_see_every_branch(self):
		for who in ("ho_team", "hse_head", "director"):
			seen = self.names("HSE Work Order", who)
			self.assertIn(self.order_t.name, seen, who)
			self.assertIn(self.order_j.name, seen, who)

	def test_a_permission_for_other_document_types_does_not_open_hse_records(self):
		"""A User Permission limited to Employee must not count as a branch grant for HSE."""
		make_user(email("narrow"), ["Branch HSE Head"])
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": email("narrow"),
				"allow": "Branch",
				"for_value": "TEST Athagarh",
				"applicable_for": "Employee",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(self.names("HSE Work Order", "narrow"), set())

	def test_roles_that_see_all_branches_are_a_setting(self):
		"""Taking a role out of the setting puts it back under branch rules."""
		settings = frappe.get_doc("HSE Settings")
		original = [r.role for r in settings.all_branch_roles]
		settings.all_branch_roles = [r for r in settings.all_branch_roles if r.role != "Director"]
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="HSE Settings")
		self.assertEqual(self.names("HSE Work Order", "director"), set())

		settings.reload()
		settings.all_branch_roles = []
		for role in original:
			settings.append("all_branch_roles", {"role": role})
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="HSE Settings")
		self.assertIn(self.order_t.name, self.names("HSE Work Order", "director"))

	def test_every_branch_doctype_is_registered(self):
		"""A new HSE document type with a branch field must be listed in hooks.py."""
		module_path = Path(frappe.get_app_path("krl_hse", "hse_health_safety_and_environment", "doctype"))
		missing = []
		for folder in sorted(p for p in module_path.iterdir() if p.is_dir()):
			json_file = folder / f"{folder.name}.json"
			if not json_file.exists():
				continue
			meta = frappe.parse_json(json_file.read_text())
			if meta.get("istable") or meta.get("issingle"):
				continue
			has_branch = any(f["fieldname"] == "branch" and f["fieldtype"] == "Link" for f in meta["fields"])
			if has_branch and meta["name"] not in hooks.hse_branch_doctypes:
				missing.append(meta["name"])
		self.assertEqual(missing, [])


class TestRolePermissions(IntegrationTestCase):
	"""One test user per role. Each sees and does exactly what the setup allows on Phase 1 records."""

	# role: (read, create, edit) on HSE Work Order and HSE Workplace Area
	EXPECTED = {  # noqa: RUF012
		"Director": (True, False, False),
		"HSE Head": (True, True, True),
		"HO HSE Team": (True, True, True),
		"Branch HSE Head": (True, True, True),
		"HSE Officer": (True, True, True),
		"HSE Supervisor": (True, False, False),
		"Branch Head": (True, True, True),
		"Branch Department Head": (True, False, False),
		"Site Supervisor": (True, False, False),
		"Store In-charge": (True, False, False),
	}

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_branch("TEST Athagarh", "T")
		cls.order = make_work_order("TEST Athagarh", "ROLE-T")
		cls.area = make_area("TEST Athagarh", "TEST Role Area")
		for role in cls.EXPECTED:
			make_user(email(f"role_{frappe.scrub(role)}"), [role], branches=["TEST Athagarh"])
		# ERPNext only keeps the Employee role on a user who has an Employee record, so the
		# role is lent to the test user below instead of being assigned.
		make_user(email("role_employee"), [], branches=["TEST Athagarh"])

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_each_role_gets_what_the_setup_allows(self):
		for role, (can_read, can_create, can_edit) in self.EXPECTED.items():
			frappe.set_user(email(f"role_{frappe.scrub(role)}"))
			for doctype, name in (
				("HSE Work Order", self.order.name),
				("HSE Workplace Area", self.area.name),
			):
				self.assertEqual(
					frappe.has_permission(doctype, "read", doc=name), can_read, f"{role} read {doctype}"
				)
				self.assertEqual(
					frappe.has_permission(doctype, "create"), can_create, f"{role} create {doctype}"
				)
				self.assertEqual(
					frappe.has_permission(doctype, "write", doc=name), can_edit, f"{role} edit {doctype}"
				)

	def as_employee(self):
		frappe.set_user(email("role_employee"))
		frappe.cache.hdel("roles", email("role_employee"))
		return patch("frappe.get_roles", return_value=["All", "Guest", "Desk User", "Employee"])

	def test_employee_can_pick_the_work_but_not_browse_work_orders(self):
		with self.as_employee():
			self.assertFalse(frappe.has_permission("HSE Work Order", "read"))
			self.assertTrue(frappe.has_permission("HSE Work Order", "select"))

	def test_employee_can_read_areas(self):
		with self.as_employee():
			self.assertTrue(frappe.has_permission("HSE Workplace Area", "read", doc=self.area.name))
			self.assertFalse(frappe.has_permission("HSE Workplace Area", "write", doc=self.area.name))


class TestPickingABranch(IntegrationTestCase):
	"""HSE roles must be able to choose a branch in a form, but not open or change Branch records."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_branch("TEST Athagarh", "T")
		make_branch("TEST Jharsuguda", "J")
		make_user(email("pick_t"), ["Branch HSE Head"], branches=["TEST Athagarh"])
		make_user(email("pick_ho"), ["HO HSE Team"])

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_branch_user_can_search_only_own_branch(self):
		from frappe.desk.search import search_link

		frappe.set_user(email("pick_t"))
		found = {r["value"] for r in search_link("Branch", "TEST", page_length=20)}
		self.assertIn("TEST Athagarh", found)
		self.assertNotIn("TEST Jharsuguda", found)

	def test_head_office_user_can_search_every_branch(self):
		from frappe.desk.search import search_link

		frappe.set_user(email("pick_ho"))
		found = {r["value"] for r in search_link("Branch", "TEST", page_length=20)}
		self.assertTrue({"TEST Athagarh", "TEST Jharsuguda"} <= found)

	def test_picking_does_not_allow_editing_a_branch(self):
		frappe.set_user(email("pick_ho"))
		self.assertTrue(frappe.has_permission("Branch", "select"))
		self.assertFalse(frappe.has_permission("Branch", "write"))
		self.assertFalse(frappe.has_permission("Branch", "create"))

	def test_hr_keeps_its_own_branch_permissions(self):
		roles = set(frappe.get_all("Custom DocPerm", filters={"parent": "Branch", "write": 1}, pluck="role"))
		self.assertTrue({"HR Manager", "HR User"} <= roles)
