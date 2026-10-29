"""Managing sites: who may edit a branch, disabling a site, and giving people a site."""

import frappe
from frappe.tests import IntegrationTestCase

from krl_hse.setup.install import ensure_manage_permissions
from krl_hse.tests.utils import make_area, make_branch, make_user, make_work_order
from krl_hse.utils import branch as sites
from krl_hse.utils.branch_access import get_allowed_branches


def as_user(testcase, email):
	frappe.set_user(email)
	testcase.addCleanup(frappe.set_user, "Administrator")


class TestSiteRights(IntegrationTestCase):
	def can(self, email, right):
		return frappe.permissions.has_permission("Branch", right, user=email)

	def test_head_office_roles_can_create_and_edit_a_site_but_not_delete_it(self):
		for role in ("Director", "HSE Head", "HO HSE Team"):
			email = make_user(f"test.rights.{role.replace(' ', '').lower()}@example.com", [role]).name
			self.assertTrue(self.can(email, "create"), role)
			self.assertTrue(self.can(email, "write"), role)
			self.assertFalse(self.can(email, "delete"), role)

	def test_branch_roles_cannot_change_a_site(self):
		for role in ("Branch HSE Head", "HSE Officer", "Branch Head"):
			email = make_user(f"test.rights.{role.replace(' ', '').lower()}@example.com", [role]).name
			self.assertFalse(self.can(email, "create"), role)
			self.assertFalse(self.can(email, "write"), role)

	def test_rights_are_given_once_and_not_given_back(self):
		frappe.db.set_value(
			"Custom DocPerm", {"parent": "Branch", "role": "HO HSE Team", "permlevel": 0}, "write", 0
		)
		ensure_manage_permissions()
		self.assertEqual(
			frappe.db.get_value(
				"Custom DocPerm", {"parent": "Branch", "role": "HO HSE Team", "permlevel": 0}, "write"
			),
			0,
		)


class TestDisabledSite(IntegrationTestCase):
	def setUp(self):
		self.branch = make_branch("TEST Closed Site", "ZX")
		frappe.db.set_value("Branch", self.branch.name, "hse_disabled", 0)

	def disable(self):
		frappe.db.set_value("Branch", self.branch.name, "hse_disabled", 1)

	def test_a_disabled_site_takes_no_new_record(self):
		self.disable()
		with self.assertRaises(frappe.ValidationError):
			make_work_order(self.branch.name, "TEST-CLOSED-1")
		with self.assertRaises(frappe.ValidationError):
			make_area(self.branch.name, "TEST Closed Area")

	def test_records_made_before_stay_editable(self):
		area = make_area(self.branch.name, "TEST Open Area")
		self.disable()
		area.reload()
		area.location_details = "Edited after the site closed"
		area.save()
		self.assertEqual(
			frappe.db.get_value("HSE Workplace Area", area.name, "location_details"), area.location_details
		)

	def test_moving_a_record_to_a_disabled_site_is_refused(self):
		other = make_branch("TEST Open Site", "ZY")
		area = make_area(other.name, "TEST Moving Area")
		self.disable()
		area.reload()
		area.branch = self.branch.name
		with self.assertRaises(frappe.ValidationError):
			area.save()

	def test_an_open_site_still_works(self):
		area = make_area(self.branch.name, "TEST Fine Area")
		self.assertTrue(area.name)


class TestPeopleWithAccess(IntegrationTestCase):
	def setUp(self):
		self.site = make_branch("TEST Access Site", "ZA").name
		self.other_site = make_branch("TEST Access Other", "ZB").name
		self.manager = make_user("test.access.manager@example.com", ["Director"]).name
		self.officer = make_user("test.access.officer@example.com", ["HSE Officer"]).name

	def test_a_manager_gives_and_takes_back_a_site(self):
		as_user(self, self.manager)

		self.assertEqual(sites.grant_branch_access(self.site, self.officer), {"added": 1})
		self.assertEqual(get_allowed_branches(self.officer), [self.site])

		# Giving it again changes nothing.
		self.assertEqual(sites.grant_branch_access(self.site, self.officer), {"added": 0})
		self.assertEqual(
			frappe.db.count(
				"User Permission", {"user": self.officer, "allow": "Branch", "for_value": self.site}
			),
			1,
		)

		people = sites.get_branch_users(self.site)
		self.assertEqual([p["user"] for p in people], [self.officer])
		self.assertEqual(people[0]["roles"], ["HSE Officer"])

		self.assertEqual(sites.revoke_branch_access(self.site, self.officer), {"removed": 1})
		self.assertEqual(get_allowed_branches(self.officer), [])
		self.assertEqual(sites.get_branch_users(self.site), [])

	def test_taking_back_one_site_leaves_the_others(self):
		as_user(self, self.manager)
		sites.grant_branch_access(self.site, self.officer)
		sites.grant_branch_access(self.other_site, self.officer)

		sites.revoke_branch_access(self.site, self.officer)
		self.assertEqual(get_allowed_branches(self.officer), [self.other_site])

	def test_a_permission_limited_to_some_document_types_is_left_alone(self):
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": self.officer,
				"allow": "Branch",
				"for_value": self.site,
				"applicable_for": "HSE Work Order",
			}
		).insert(ignore_permissions=True)
		as_user(self, self.manager)

		self.assertEqual(sites.get_branch_users(self.site), [])
		self.assertEqual(sites.revoke_branch_access(self.site, self.officer), {"removed": 0})
		self.assertTrue(frappe.db.exists("User Permission", {"user": self.officer, "for_value": self.site}))

	def test_someone_who_already_sees_every_branch_is_refused(self):
		as_user(self, self.manager)
		with self.assertRaises(frappe.ValidationError):
			sites.grant_branch_access(self.site, self.manager)

	def test_a_disabled_or_unknown_user_is_refused(self):
		frappe.db.set_value("User", self.officer, "enabled", 0)
		as_user(self, self.manager)
		for user in (self.officer, "Administrator", "nobody.here@example.com"):
			with self.assertRaises(frappe.ValidationError):
				sites.grant_branch_access(self.site, user)

	def test_only_people_who_can_edit_the_site_may_change_access(self):
		head = make_user("test.access.bhead@example.com", ["Branch HSE Head"], branches=[self.site]).name
		as_user(self, head)
		with self.assertRaises(frappe.PermissionError):
			sites.grant_branch_access(self.site, self.officer)
		with self.assertRaises(frappe.PermissionError):
			sites.get_branch_users(self.site)
