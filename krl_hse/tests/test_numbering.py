import frappe
from frappe.tests import IntegrationTestCase

from krl_hse.tests.utils import make_branch, set_document_code
from krl_hse.utils.numbering import (
	financial_year_label,
	make_document_number,
	preview_number,
)


class TestFinancialYear(IntegrationTestCase):
	def test_april_start(self):
		self.assertEqual(financial_year_label("2026-04-01", 4), "2026-27")
		self.assertEqual(financial_year_label("2027-03-31", 4), "2026-27")
		self.assertEqual(financial_year_label("2026-03-31", 4), "2025-26")

	def test_label_formats(self):
		self.assertEqual(financial_year_label("2026-05-10", 4, "26-27"), "26-27")
		self.assertEqual(financial_year_label("2026-05-10", 4, "2026-2027"), "2026-2027")

	def test_other_start_month(self):
		self.assertEqual(financial_year_label("2026-06-30", 7), "2025-26")
		self.assertEqual(financial_year_label("2026-07-01", 7), "2026-27")

	def test_january_start_is_calendar_year(self):
		self.assertEqual(financial_year_label("2026-12-31", 1), "2026")
		self.assertEqual(financial_year_label("2026-12-31", 1, "26-27"), "26")


class TestNumbering(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_branch("TEST Athagarh", "T")
		make_branch("TEST Jharsuguda", "J")
		make_branch("TEST Head Office", "HO", head_office=1)

	def setUp(self):
		# Series rows are not rolled back between tests, so start each test from a clean run.
		frappe.db.sql("delete from `tabSeries` where `name` like 'KRL/%' or `name` like 'ABC/%'")
		settings = frappe.get_doc("HSE Settings")
		settings.document_prefix = "KRL"
		settings.fy_start_month = "April"
		settings.fy_label_format = "2026-27"
		settings.sequence_digits = 4
		settings.default_number_format = "{prefix}/{doc_code}/{branch}/{fy}/{seq}"
		settings.save(ignore_permissions=True)
		set_document_code("ToDo", "TD")

	def test_default_format(self):
		number = make_document_number("ToDo", "TEST Athagarh", on_date="2026-10-29")
		self.assertEqual(number, "KRL/TD/T/2026-27/0001")

	def test_numbers_run_on_and_never_repeat(self):
		first = make_document_number("ToDo", "TEST Athagarh", on_date="2026-10-29")
		second = make_document_number("ToDo", "TEST Athagarh", on_date="2026-10-29")
		self.assertEqual(first[-4:], "0001")
		self.assertEqual(second[-4:], "0002")

	def test_each_branch_and_year_has_its_own_run(self):
		make_document_number("ToDo", "TEST Athagarh", on_date="2026-10-29")
		make_document_number("ToDo", "TEST Athagarh", on_date="2026-10-29")
		self.assertEqual(
			make_document_number("ToDo", "TEST Jharsuguda", on_date="2026-10-29"), "KRL/TD/J/2026-27/0001"
		)
		self.assertEqual(
			make_document_number("ToDo", "TEST Athagarh", on_date="2027-04-01"), "KRL/TD/T/2027-28/0001"
		)

	def test_job_in_the_number_and_empty_job_leaves_no_gap(self):
		set_document_code("ToDo", "WPSA", "{prefix}/{doc_code}/{branch}/{fy}/{job}/{seq}")
		self.assertEqual(
			make_document_number("ToDo", "TEST Athagarh", job="LRF", on_date="2026-10-29"),
			"KRL/WPSA/T/2026-27/LRF/0001",
		)
		self.assertEqual(
			make_document_number("ToDo", "TEST Athagarh", on_date="2026-10-29"),
			"KRL/WPSA/T/2026-27/0001",
		)

	def test_settings_drive_the_number(self):
		settings = frappe.get_doc("HSE Settings")
		settings.document_prefix = "ABC"
		settings.fy_start_month = "January"
		settings.sequence_digits = 6
		settings.save(ignore_permissions=True)
		self.assertEqual(
			make_document_number("ToDo", "TEST Head Office", on_date="2026-10-29"), "ABC/TD/HO/2026/000001"
		)

	def test_preview_does_not_use_up_a_number(self):
		self.assertEqual(
			preview_number("ToDo", "TEST Athagarh", on_date="2026-10-29"), "KRL/TD/T/2026-27/0001"
		)
		self.assertEqual(
			preview_number("ToDo", "TEST Athagarh", on_date="2026-10-29"), "KRL/TD/T/2026-27/0001"
		)
		make_document_number("ToDo", "TEST Athagarh", on_date="2026-10-29")
		self.assertEqual(
			preview_number("ToDo", "TEST Athagarh", on_date="2026-10-29"), "KRL/TD/T/2026-27/0002"
		)

	def test_missing_document_code_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			make_document_number("Note", "TEST Athagarh")

	def test_branch_without_code_is_refused(self):
		make_branch("TEST No Code", "X")
		frappe.db.set_value("Branch", "TEST No Code", "hse_branch_code", None)
		with self.assertRaises(frappe.ValidationError):
			make_document_number("ToDo", "TEST No Code")

	def test_unknown_token_is_refused_in_settings(self):
		settings = frappe.get_doc("HSE Settings")
		settings.default_number_format = "{prefix}/{nonsense}/{seq}"
		with self.assertRaises(frappe.ValidationError):
			settings.save(ignore_permissions=True)

	def test_default_format_must_have_a_running_number(self):
		settings = frappe.get_doc("HSE Settings")
		settings.default_number_format = "{prefix}/{doc_code}"
		with self.assertRaises(frappe.ValidationError):
			settings.save(ignore_permissions=True)

	def test_same_document_type_twice_is_refused(self):
		settings = frappe.get_doc("HSE Settings")
		settings.append("document_codes", {"reference_doctype": "ToDo", "document_code": "T2"})
		with self.assertRaises(frappe.ValidationError):
			settings.save(ignore_permissions=True)


class TestBranchCode(IntegrationTestCase):
	def test_two_branches_cannot_share_a_code(self):
		make_branch("TEST One", "Q")
		with self.assertRaises(frappe.ValidationError):
			make_branch("TEST Two", "Q")

	def test_code_may_only_have_letters_and_digits(self):
		with self.assertRaises(frappe.ValidationError):
			make_branch("TEST Slash", "A/B")

	def test_blank_code_is_allowed(self):
		branch = make_branch("TEST Blank", "")
		self.assertFalse(branch.hse_branch_code)
