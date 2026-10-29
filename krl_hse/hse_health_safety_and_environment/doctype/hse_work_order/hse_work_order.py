import re

import frappe
from frappe import _
from frappe.utils import getdate

from krl_hse.utils.hse_document import HSEDocument

JOB_CODE_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class HSEWorkOrder(HSEDocument):
	"""The 'Work' that every HSE record is tagged to (BRD 6.9.1).

	KRL has no ERP for its client orders yet, so the order is entered here. The optional ERP
	reference lets it point to a Sales Order or Project once those exist.
	"""

	def validate(self):
		self.validate_job_code()
		self.validate_dates()
		self.validate_contacts()

	def validate_job_code(self):
		self.job_code = (self.job_code or "").strip()
		if not JOB_CODE_PATTERN.match(self.job_code):
			frappe.throw(
				_(
					"Job Code {0} may only have letters, digits, hyphen and underscore, so it can sit inside a document number."
				).format(frappe.bold(self.job_code))
			)

	def validate_dates(self):
		if (
			self.start_date
			and self.completion_date
			and getdate(self.completion_date) < getdate(self.start_date)
		):
			frappe.throw(_("Work Completes cannot be before Work Starts."))

		if self.reference_doctype and not self.reference_name:
			frappe.throw(_("Set the ERP Reference, or clear the ERP Reference Type."))

	def validate_contacts(self):
		seen = set()
		for row in self.contacts:
			key = (row.contact_role, (row.contact_name or "").strip().lower())
			if key in seen:
				frappe.throw(
					_("Row {0}: {1} is already listed as {2}.").format(
						row.idx, frappe.bold(row.contact_name), frappe.bold(row.contact_role)
					)
				)
			seen.add(key)
