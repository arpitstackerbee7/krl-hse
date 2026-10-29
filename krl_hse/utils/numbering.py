"""Document numbering for every HSE record.

The pattern is a setting, not code. HSE Settings holds a default number format and, per
document type, a document code and an optional format of its own. A format is plain text with
these tokens:

	{prefix}    company prefix from HSE Settings (for example KRL)
	{doc_code}  the document code of the document type (for example WPSA)
	{branch}    the HSE Branch Code of the record's branch (for example J)
	{fy}        the financial year the record falls in (for example 2026-27)
	{job}       the job code of the Work Order the record belongs to (may be empty)
	{seq}       the running number

The running number restarts for every different combination of the other tokens, so a
register is numbered per branch, financial year and job, as the BRD (section 6.9.1) asks.
Numbers come from Frappe's Series table, which is atomic and never hands out a number twice.
"""

import re

import frappe
from frappe import _
from frappe.model.naming import getseries
from frappe.utils import cint, getdate, nowdate

MONTHS = [
	"January",
	"February",
	"March",
	"April",
	"May",
	"June",
	"July",
	"August",
	"September",
	"October",
	"November",
	"December",
]

FY_LABEL_FORMATS = ["2026-27", "26-27", "2026-2027"]

TOKENS = ("prefix", "doc_code", "branch", "fy", "job", "seq")

TOKEN_PATTERN = re.compile(r"\{(\w+)\}")
REPEATED_SEPARATOR = re.compile(r"([/\-_.])\1+")


def financial_year_label(on_date, start_month=4, label_format="2026-27"):
	"""Label of the financial year that `on_date` falls in.

	`start_month` is 1 to 12. When the year starts in January the label is the calendar year.
	"""
	date = getdate(on_date)
	start_month = cint(start_month) or 4
	start_year = date.year if date.month >= start_month else date.year - 1

	if start_month == 1:
		return str(start_year)[2:] if label_format == "26-27" else str(start_year)

	end_year = start_year + 1
	if label_format == "26-27":
		return f"{str(start_year)[2:]}-{str(end_year)[2:]}"
	if label_format == "2026-2027":
		return f"{start_year}-{end_year}"
	return f"{start_year}-{str(end_year)[2:]}"


def month_number(month_name):
	"""1 to 12 for a month name from HSE Settings."""
	return MONTHS.index(month_name) + 1 if month_name in MONTHS else 4


def check_format(number_format):
	"""Raise if a format uses a token we do not know."""
	for token in TOKEN_PATTERN.findall(number_format or ""):
		if token not in TOKENS:
			frappe.throw(
				_("Number format {0} uses the unknown token {{{1}}}. Allowed tokens: {2}").format(
					frappe.bold(number_format), token, ", ".join("{" + t + "}" for t in TOKENS)
				),
				title=_("Invalid number format"),
			)


def _fill(text, values):
	text = TOKEN_PATTERN.sub(lambda m: str(values.get(m.group(1), "")), text)
	return REPEATED_SEPARATOR.sub(r"\1", text)


def get_number_parts(doctype, branch, job=None, on_date=None):
	"""Work out the fixed text around the running number for one record.

	Returns (series_key, digits, before, after). The number is before + running number + after.
	"""
	settings = frappe.get_cached_doc("HSE Settings")

	row = next((r for r in settings.document_codes if r.reference_doctype == doctype), None)
	if not row or not row.document_code:
		frappe.throw(
			_("No document code is set for {0}. Add it in HSE Settings, under Document Codes.").format(
				frappe.bold(doctype)
			),
			title=_("Document code missing"),
		)

	if not branch:
		frappe.throw(_("Branch is required to number a {0}.").format(doctype))

	branch_code = frappe.db.get_value("Branch", branch, "hse_branch_code")
	if not branch_code:
		frappe.throw(
			_("Branch {0} has no HSE Branch Code. Set it on the Branch record first.").format(
				frappe.bold(branch)
			),
			title=_("Branch code missing"),
		)

	number_format = row.number_format or settings.default_number_format
	if "{seq}" not in number_format:
		number_format = number_format + "{seq}"
	check_format(number_format)

	values = {
		"prefix": settings.document_prefix,
		"doc_code": row.document_code,
		"branch": branch_code,
		"fy": financial_year_label(
			on_date or nowdate(), month_number(settings.fy_start_month), settings.fy_label_format
		),
		"job": job or "",
	}

	before, _sep, after = number_format.partition("{seq}")
	before = _fill(before, values)
	after = _fill(after, values)
	key = before if not after else f"{before}|{after}"
	return key, cint(settings.sequence_digits) or 4, before, after


def make_document_number(doctype, branch, job=None, on_date=None):
	"""Take the next number for a record. Call once, when the record is first saved."""
	key, digits, before, after = get_number_parts(doctype, branch, job, on_date)
	return f"{before}{getseries(key, digits)}{after}"


def _current_value(key):
	"""Last number taken for a series key (0 if none yet). Series has no creation column."""
	rows = frappe.db.sql("select `current` from `tabSeries` where `name` = %s", (key,))
	return cint(rows[0][0]) if rows else 0


@frappe.whitelist()
def preview_number(doctype, branch, job=None, on_date=None):
	"""The number the next record would get, without using it up."""
	frappe.has_permission("HSE Settings", "read", throw=True)
	key, digits, before, after = get_number_parts(doctype, branch, job, on_date)
	current = _current_value(key)
	return f"{before}{str(current + 1).zfill(digits)}{after}"
