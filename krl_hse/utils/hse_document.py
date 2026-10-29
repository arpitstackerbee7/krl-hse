import frappe
from frappe import _
from frappe.model.document import Document

from krl_hse.utils.numbering import make_document_number


class HSEDocument(Document):
	"""Base class for every HSE record.

	Every KRL format carries Branch, Area and Work (BRD 6.9.1), so each HSE record has a
	`branch` field. The record number is built from the branch, the financial year and the
	job, as set in HSE Settings.

	A document type can name, on the class:
	  number_date_field  the date field that decides the financial year (default: today)
	  number_job_field   a Link to HSE Work Order whose job code goes into the number
	"""

	number_date_field: str | None = None
	number_job_field: str | None = None

	def autoname(self):
		on_date = self.get(self.number_date_field) if self.number_date_field else None
		job = None
		if self.number_job_field and self.get(self.number_job_field):
			job = frappe.db.get_value("HSE Work Order", self.get(self.number_job_field), "job_code")
		self.name = make_document_number(self.doctype, self.branch, job=job, on_date=on_date)

	def before_save(self):
		self.check_send_back_recommendations()

	def check_send_back_recommendations(self):
		"""The approver must say why a record is sent back (BRD 6.9.1: sent back with recommendations).

		The name of the sent-back state is a setting, so renaming the state in the workflow only
		needs the setting changed.
		"""
		if not self.meta.has_field("recommendations") or not self.meta.has_field("workflow_state"):
			return

		sent_back = frappe.get_cached_doc("HSE Settings").sent_back_state
		if sent_back and self.workflow_state == sent_back and not (self.recommendations or "").strip():
			frappe.throw(
				_("Give the recommendations before sending this back."), title=_("Recommendations needed")
			)
