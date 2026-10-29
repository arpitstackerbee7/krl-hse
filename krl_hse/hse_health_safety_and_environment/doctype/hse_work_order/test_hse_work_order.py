import frappe
from frappe.tests import IntegrationTestCase

from krl_hse.tests.utils import current_fy, make_branch, make_work_order

# These masters belong to ERPNext. The tests here need none of their sample records.
IGNORE_TEST_RECORD_DEPENDENCIES = ["Customer", "Employee", "UOM", "DocType"]


class TestHSEWorkOrder(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_branch("TEST Athagarh", "T")
		make_branch("TEST Jharsuguda", "J")
		frappe.db.sql("delete from `tabSeries` where `name` like 'KRL/WO/%'")
		frappe.clear_cache(doctype="HSE Settings")

	def test_number_carries_branch_and_financial_year(self):
		order = make_work_order("TEST Athagarh", "AT-1")
		self.assertTrue(order.name.startswith(f"KRL/WO/T/{current_fy()}/"), order.name)

	def test_numbers_are_separate_for_each_branch(self):
		first = make_work_order("TEST Jharsuguda", "JH-1")
		second = make_work_order("TEST Jharsuguda", "JH-2")
		other = make_work_order("TEST Athagarh", "AT-2")
		self.assertEqual(int(second.name[-4:]), int(first.name[-4:]) + 1)
		self.assertIn("/J/", first.name)
		self.assertIn("/T/", other.name)

	def test_job_code_must_be_unique(self):
		make_work_order("TEST Athagarh", "DUP-1")
		with self.assertRaises(frappe.UniqueValidationError):
			make_work_order("TEST Jharsuguda", "DUP-1")

	def test_job_code_cannot_break_the_number(self):
		with self.assertRaises(frappe.ValidationError):
			make_work_order("TEST Athagarh", "A/B")

	def test_completion_cannot_be_before_start(self):
		with self.assertRaises(frappe.ValidationError):
			make_work_order("TEST Athagarh", "DATE-1", start_date="2026-06-01", completion_date="2026-05-01")

	def test_erp_reference_needs_a_name(self):
		with self.assertRaises(frappe.ValidationError):
			make_work_order("TEST Athagarh", "REF-1", reference_doctype="Sales Order")

	def test_services_and_contacts_are_lists_of_any_length(self):
		order = make_work_order(
			"TEST Athagarh",
			"LIST-1",
			service_lines=[
				{"service_code": f"S{i}", "description": f"TEST service {i}", "qty": i, "working_height_m": 0}
				for i in range(1, 8)
			],
			contacts=[
				{"contact_role": "Client Representative", "contact_name": "TEST Client Rep"},
				{"contact_role": "Client HSE Representative", "contact_name": "TEST Client HSE"},
				{"contact_role": "Branch Head", "contact_name": "TEST Branch Head"},
			],
		)
		order.reload()
		self.assertEqual(len(order.service_lines), 7)
		self.assertEqual([c.party for c in order.contacts], ["Client", "Client", "KRL"])

	def test_same_person_cannot_hold_the_same_role_twice(self):
		with self.assertRaises(frappe.ValidationError):
			make_work_order(
				"TEST Athagarh",
				"CON-1",
				contacts=[
					{"contact_role": "Branch Head", "contact_name": "TEST Person"},
					{"contact_role": "Branch Head", "contact_name": "test person"},
				],
			)

	def test_one_branch_can_have_many_work_orders(self):
		for i in range(3):
			make_work_order("TEST Jharsuguda", f"MANY-{i}")
		self.assertGreaterEqual(frappe.db.count("HSE Work Order", {"branch": "TEST Jharsuguda"}), 3)
