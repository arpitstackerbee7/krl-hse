import frappe
from frappe.tests import IntegrationTestCase

from krl_hse.tests.utils import current_fy, make_area, make_branch, make_work_order

# These masters belong to ERPNext. The tests here need none of their sample records.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Customer", "Employee", "UOM", "DocType"]


class TestHSEWorkplaceArea(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_branch("TEST Athagarh", "T")
		make_branch("TEST Jharsuguda", "J")
		cls.order = make_work_order("TEST Athagarh", "AREA-WO")

	def test_number_uses_the_area_code(self):
		area = make_area("TEST Athagarh", "TEST Slag Yard")
		self.assertTrue(area.name.startswith(f"KRL/WPAD/T/{current_fy()}/"), area.name)

	def test_area_name_is_unique_within_branch_and_work(self):
		make_area("TEST Athagarh", "TEST Gate", work_order=self.order.name)
		with self.assertRaises(frappe.ValidationError):
			make_area("TEST Athagarh", "TEST Gate", work_order=self.order.name)
		# The same name is fine in another branch, or for no work order.
		make_area("TEST Jharsuguda", "TEST Gate")
		make_area("TEST Athagarh", "TEST Gate")

	def test_work_order_must_belong_to_the_same_branch(self):
		with self.assertRaises(frappe.ValidationError):
			make_area("TEST Jharsuguda", "TEST Wrong Branch", work_order=self.order.name)

	def test_team_leader_is_picked_from_the_team(self):
		area = make_area(
			"TEST Athagarh",
			"TEST Crusher",
			team=[
				{
					"team_role": "Team Lead",
					"member_name": "TEST Lead One",
					"category": "SL",
					"from_date": "2026-04-01",
				},
				{
					"team_role": "Member 1",
					"member_name": "TEST Member A",
					"category": "Worker",
					"from_date": "2026-04-01",
				},
				{
					"team_role": "Member 2",
					"member_name": "TEST Member B",
					"category": "Worker",
					"from_date": "2026-04-01",
				},
			],
		)
		self.assertEqual(area.team_leader, "TEST Lead One")

	def test_only_one_current_leader(self):
		with self.assertRaises(frappe.ValidationError):
			make_area(
				"TEST Athagarh",
				"TEST Two Leaders",
				team=[
					{"team_role": "Team Lead", "member_name": "TEST Lead One", "from_date": "2026-04-01"},
					{"team_role": "Team Lead", "member_name": "TEST Lead Two", "from_date": "2026-04-01"},
				],
			)

	def test_changing_the_leader_keeps_the_history(self):
		area = make_area(
			"TEST Athagarh",
			"TEST Change",
			team=[{"team_role": "Team Lead", "member_name": "TEST Old Lead", "from_date": "2026-04-01"}],
		)
		area.team[0].to_date = "2026-09-30"
		area.append(
			"team", {"team_role": "Team Lead", "member_name": "TEST New Lead", "from_date": "2026-10-01"}
		)
		area.save(ignore_permissions=True)
		area.reload()
		self.assertEqual(len(area.team), 2)
		self.assertEqual(area.team_leader, "TEST New Lead")

	def test_team_dates_must_make_sense(self):
		with self.assertRaises(frappe.ValidationError):
			make_area(
				"TEST Athagarh",
				"TEST Bad Dates",
				team=[
					{
						"team_role": "Member 1",
						"member_name": "TEST Member",
						"from_date": "2026-05-01",
						"to_date": "2026-04-01",
					}
				],
			)

	def test_team_has_no_set_size(self):
		area = make_area(
			"TEST Athagarh",
			"TEST Big Team",
			team=[
				{"team_role": "Member 1", "member_name": f"TEST Member {i}", "from_date": "2026-04-01"}
				for i in range(6)
			],
		)
		self.assertEqual(len(area.team), 6)
