import frappe
from frappe.tests import IntegrationTestCase


class TestHSESeverityLevel(IntegrationTestCase):
	def make_level(self, label, level, **kw):
		doc = frappe.get_doc({"doctype": "HSE Severity Level", "severity_label": label, "level": level, **kw})
		doc.insert(ignore_permissions=True)
		# Records made in one test must not leak into the next.
		self.addCleanup(frappe.delete_doc, "HSE Severity Level", doc.name, force=True, ignore_permissions=True)
		return doc

	def test_starting_scale_is_loaded_from_the_brd(self):
		levels = frappe.get_all(
			"HSE Severity Level",
			fields=["name", "level", "harm", "rectify_within_days", "rectify_immediately", "requires_capa", "stops_work"],
			order_by="level asc",
		)
		self.assertEqual([lv.level for lv in levels], [1, 2, 3, 4, 5])
		self.assertEqual([lv.name for lv in levels], ["Severity I", "Severity II", "Severity III", "Severity IV", "Severity V"])
		self.assertEqual([lv.rectify_within_days for lv in levels], [3, 3, 2, 0, 0])
		self.assertEqual([lv.requires_capa for lv in levels], [0, 0, 1, 1, 1])
		self.assertEqual([lv.stops_work for lv in levels], [0, 0, 0, 1, 1])
		self.assertEqual([lv.rectify_immediately for lv in levels], [0, 0, 0, 1, 1])

	def test_immediate_means_zero_days(self):
		level = self.make_level("TEST Level", 9, rectify_within_days=7, rectify_immediately=1)
		self.assertEqual(level.rectify_within_days, 0)

	def test_level_numbers_are_unique(self):
		with self.assertRaises(frappe.UniqueValidationError):
			self.make_level("TEST Dup", 3)

	def test_scale_can_be_extended(self):
		"""The scale has no fixed length: a sixth level is accepted."""
		before = frappe.db.count("HSE Severity Level")
		self.make_level("TEST Six", 6)
		self.assertEqual(frappe.db.count("HSE Severity Level"), before + 1)
