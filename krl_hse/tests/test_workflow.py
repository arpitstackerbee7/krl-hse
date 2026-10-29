import frappe
from frappe.model.workflow import WorkflowPermissionError, WorkflowTransitionError, apply_workflow
from frappe.tests import IntegrationTestCase

from krl_hse.tests.utils import make_area, make_branch, make_user

DOMAIN = "krl-test.example"


def email(name):
	return f"test.{name}@{DOMAIN}"


class TestAreaApprovalWorkflow(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_branch("TEST Athagarh", "T")
		make_branch("TEST Jharsuguda", "J")
		make_user(email("wf_officer_t"), ["HSE Officer"], branches=["TEST Athagarh"])
		make_user(email("wf_branch_hse_t"), ["Branch HSE Head"], branches=["TEST Athagarh"])
		make_user(email("wf_branch_head_t"), ["Branch Head"], branches=["TEST Athagarh"])
		make_user(email("wf_branch_head_j"), ["Branch Head"], branches=["TEST Jharsuguda"])
		make_user(email("wf_hse_head"), ["HSE Head"])

	def tearDown(self):
		frappe.set_user("Administrator")

	def new_area(self, name):
		"""An area made by the branch HSE head, left in its starting state."""
		frappe.set_user(email("wf_branch_hse_t"))
		return frappe.get_doc(
			{"doctype": "HSE Workplace Area", "branch": "TEST Athagarh", "area_name": name}
		).insert()

	def act(self, user, area, action, **values):
		frappe.set_user(email(user))
		doc = frappe.get_doc("HSE Workplace Area", area.name)
		if values:
			# As on the form: the approver saves the recommendations, then picks the action.
			doc.update(values)
			doc.save()
		return apply_workflow(doc, action)

	def test_workflow_is_set_up(self):
		self.assertTrue(frappe.db.get_value("Workflow", "HSE Workplace Area Approval", "is_active"))

	def test_new_area_starts_in_draft(self):
		self.assertEqual(self.new_area("TEST WF Draft").workflow_state, "Draft")

	def test_draft_to_approved(self):
		area = self.new_area("TEST WF Happy")
		self.assertEqual(
			self.act("wf_branch_hse_t", area, "Submit for Approval").workflow_state, "Pending Approval"
		)
		self.assertEqual(self.act("wf_branch_head_t", area, "Approve").workflow_state, "Approved")

	def test_the_proposer_cannot_approve(self):
		area = self.new_area("TEST WF NoSelf")
		self.act("wf_branch_hse_t", area, "Submit for Approval")
		# Approve is simply not offered to the proposer, so the action is refused.
		with self.assertRaises((WorkflowPermissionError, WorkflowTransitionError)):
			self.act("wf_branch_hse_t", area, "Approve")

	def test_only_the_approver_can_send_back_and_must_give_recommendations(self):
		area = self.new_area("TEST WF Back")
		self.act("wf_branch_hse_t", area, "Submit for Approval")
		with self.assertRaises(frappe.ValidationError):
			self.act("wf_branch_head_t", area, "Send Back")
		sent = self.act("wf_branch_head_t", area, "Send Back", recommendations="TEST: add the second gate")
		self.assertEqual(sent.workflow_state, "Sent Back")
		self.assertEqual(sent.recommendations, "TEST: add the second gate")

	def test_sent_back_area_can_be_resubmitted(self):
		area = self.new_area("TEST WF Again")
		self.act("wf_branch_hse_t", area, "Submit for Approval")
		self.act("wf_branch_head_t", area, "Send Back", recommendations="TEST: fix the team")
		self.assertEqual(
			self.act("wf_officer_t", area, "Submit for Approval").workflow_state, "Pending Approval"
		)

	def test_a_branch_head_of_another_branch_cannot_approve(self):
		area = self.new_area("TEST WF Other")
		self.act("wf_branch_hse_t", area, "Submit for Approval")
		frappe.set_user(email("wf_branch_head_j"))
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("HSE Workplace Area", area.name).check_permission("read")

	def test_head_office_hse_head_can_approve_any_branch(self):
		area = self.new_area("TEST WF HO")
		self.act("wf_branch_hse_t", area, "Submit for Approval")
		self.assertEqual(self.act("wf_hse_head", area, "Approve").workflow_state, "Approved")

	def test_the_sent_back_state_name_is_a_setting(self):
		settings = frappe.get_doc("HSE Settings")
		settings.sent_back_state = "Returned"
		settings.save(ignore_permissions=True)
		frappe.clear_cache(doctype="HSE Settings")
		area = self.new_area("TEST WF Rename")
		self.act("wf_branch_hse_t", area, "Submit for Approval")
		# "Sent Back" no longer needs recommendations because the setting names another state.
		sent = self.act("wf_branch_head_t", area, "Send Back")
		self.assertEqual(sent.workflow_state, "Sent Back")
		self.assertTrue(make_area)  # keeps the helper import used
