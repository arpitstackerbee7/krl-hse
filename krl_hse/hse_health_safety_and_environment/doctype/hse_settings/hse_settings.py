import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from krl_hse.utils.numbering import check_format


class HSESettings(Document):
	def validate(self):
		if not 1 <= cint(self.sequence_digits) <= 10:
			frappe.throw(_("Digits in Running Number must be between 1 and 10."))

		self.validate_default_format()
		self.validate_document_codes()

	def validate_default_format(self):
		if "{seq}" not in (self.default_number_format or ""):
			frappe.throw(
				_(
					"The default number format must include {0}, which is where the running number goes."
				).format(frappe.bold("{seq}"))
			)
		check_format(self.default_number_format)

	def validate_document_codes(self):
		seen = set()
		for row in self.document_codes:
			if row.reference_doctype in seen:
				frappe.throw(
					_("Row {0}: {1} appears more than once in Document Codes.").format(
						row.idx, frappe.bold(row.reference_doctype)
					)
				)
			seen.add(row.reference_doctype)

			row.document_code = (row.document_code or "").strip()
			if row.number_format:
				check_format(row.number_format)

		# Two document types with the same code would give numbers that look alike.
		codes = {}
		for row in self.document_codes:
			codes.setdefault(row.document_code, []).append(row.reference_doctype)
		for code, doctypes in codes.items():
			if len(doctypes) > 1:
				frappe.msgprint(
					_("Document code {0} is used by more than one document type: {1}.").format(
						frappe.bold(code), ", ".join(doctypes)
					),
					indicator="orange",
					alert=True,
				)
