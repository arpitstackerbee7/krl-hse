import frappe
from frappe import _
from frappe.utils import getdate

from krl_hse.utils.hse_document import HSEDocument


class HSEWorkplaceArea(HSEDocument):
	"""A part of a branch (by location or by work) with the team that looks after it.

	Records the BRD asks to be tagged to an area (6.9.1) link to this master. The team keeps
	its history: a member who leaves gets an end date instead of being deleted.
	"""

	def validate(self):
		self.validate_work_order()
		self.validate_unique_area()
		self.validate_team()
		self.set_team_leader()

	def validate_work_order(self):
		if not self.work_order:
			return
		work_branch = frappe.db.get_value("HSE Work Order", self.work_order, "branch")
		if work_branch != self.branch:
			frappe.throw(
				_("Work {0} belongs to branch {1}, but this area is in branch {2}.").format(
					frappe.bold(self.work_order), frappe.bold(work_branch), frappe.bold(self.branch)
				)
			)

	def validate_unique_area(self):
		filters = {
			"branch": self.branch,
			"area_name": self.area_name,
			"work_order": self.work_order or ["is", "not set"],
			"name": ("!=", self.name),
		}
		clash = frappe.db.get_value("HSE Workplace Area", filters, "name")
		if clash:
			frappe.throw(
				_("An area named {0} already exists in this branch for the same work: {1}.").format(
					frappe.bold(self.area_name), frappe.bold(clash)
				)
			)

	def validate_team(self):
		leader_roles = set(frappe.get_all("HSE Area Team Role", filters={"is_leader": 1}, pluck="name"))
		current_leaders = 0

		for row in self.team:
			if row.to_date and getdate(row.to_date) < getdate(row.from_date):
				frappe.throw(_("Row {0}: To cannot be before From.").format(row.idx))

			if row.team_role in leader_roles and not row.to_date:
				current_leaders += 1

		if current_leaders > 1:
			frappe.throw(
				_(
					"An area can have only one current team leader. End the earlier leader's row by giving it a To date."
				)
			)

	def set_team_leader(self):
		leader_roles = set(frappe.get_all("HSE Area Team Role", filters={"is_leader": 1}, pluck="name"))
		self.team_leader = next(
			(row.member_name for row in self.team if row.team_role in leader_roles and not row.to_date), ""
		)
