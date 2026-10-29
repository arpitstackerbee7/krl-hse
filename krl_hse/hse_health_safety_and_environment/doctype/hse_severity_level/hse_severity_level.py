import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class HSESeverityLevel(Document):
	def validate(self):
		if cint(self.level) < 1:
			frappe.throw(_("Level Number must be 1 or more."))

		if cint(self.rectify_within_days) < 0:
			frappe.throw(_("Rectify Within (Days) cannot be negative."))

		if self.rectify_immediately:
			self.rectify_within_days = 0
