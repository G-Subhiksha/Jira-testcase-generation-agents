
"""
Epic Decomposition Agent
Flow: Epic -> Features -> User Stories -> (test cases generated per story by other agents)
Runs only when document_type = "Epic"
"""
import re
import json
import logging
from typing import Dict, Any, List
from agents.base_agent import BaseAgent


class EpicDecompositionAgent(BaseAgent):
	"""Decomposes an Epic into Features and User Stories"""

	def __init__(self, config: Dict[str, Any], llm_client: Any):
		super().__init__(config, llm_client)
		self.agent_name = "Epic Decomposition Agent"

	def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Decompose epic -> features -> stories"""
		self.log_start()
		try:
			document_content = input_data.get("document_content", "")
			classification   = input_data.get("classification", {})

			system_prompt = self._get_system_prompt()
			user_prompt   = self._build_prompt(document_content, classification)

			self.logger.info("Decomposing Epic into Features & User Stories...")
			response = self.call_llm(user_prompt, system_prompt, temperature=0.4)

			features = self._parse_response(response, document_content, classification)
			stories  = [s for f in features for s in f.get("stories", [])]

			self.logger.info(
				f"Decomposed into {len(features)} features, {len(stories)} user stories"
			)
			self.log_end()
			return {
				"epicTitle"   : self._extract_epic_title(document_content),
				"features"    : features,
				"featureCount": len(features),
				"stories"     : stories,
				"storyCount"  : len(stories),
				"agent"       : self.agent_name,
			}

		except Exception as e:
			self.logger.error(f"Epic decomposition failed: {str(e)}")
			raise

	# ── prompts ───────────────────────────────────────────────────────────────

	def _get_system_prompt(self) -> str:
		return """You are a senior Business Analyst who decomposes Epics into Features and User Stories.

Structure:
  Epic -> Features (functional groupings) -> User Stories (independently testable)

For each Feature:
- Give it a unique ID (F-001, F-002 ...) and a short title
- List 1-4 User Stories under it

For each User Story:
- Unique ID (US-001, US-002 ...)
- Clear title
- "As a <role>, I want to <action>, so that <benefit>." format
- 2-4 Acceptance Criteria (AC-001, AC-002 ...)
- Primary role/actor and priority (High / Medium / Low)

Output valid JSON only."""

	def _build_prompt(self, content: str, classification: Dict) -> str:
		domain = classification.get("domain", "")
		return f"""Decompose the following Epic into Features and User Stories.

DOMAIN: {domain}

EPIC CONTENT:
{content}

REQUIRED OUTPUT (JSON):
{{
  "epicTitle": "...",
  "features": [
	{{
	  "featureId": "F-001",
	  "featureTitle": "Short feature group name",
	  "stories": [
		{{
		  "storyId": "US-001",
		  "title": "Short story title",
		  "story": "As a <role>, I want to <action>, so that <benefit>.",
		  "role": "primary actor",
		  "priority": "High | Medium | Low",
		  "acceptanceCriteria": [
			"AC-001: <testable criterion>",
			"AC-002: <testable criterion>"
		  ]
		}}
	  ]
	}}
  ]
}}

Rules:
- Each feature is a distinct functional area
- Each story must be independently testable
- Minimum 2 features, minimum 2 stories per feature
- Maximum 5 features, maximum 4 stories per feature"""

	# ── parsing ───────────────────────────────────────────────────────────────

	def _parse_response(self, response: str, epic_content: str, classification: Dict) -> List[Dict]:
		"""Parse LLM JSON; fall back to rule-based decomposition"""
		try:
			start = response.find("{")
			end   = response.rfind("}") + 1
			data  = json.loads(response[start:end])
			features = data.get("features", [])
			if features:
				return self._enrich_features(features, classification)
		except Exception:
			self.logger.warning("JSON parse failed -- using rule-based decomposition")

		return self._rule_based_decompose(epic_content, classification)

	def _enrich_features(self, features: List[Dict], classification: Dict) -> List[Dict]:
		domain        = classification.get("domain", "General")
		project_state = classification.get("projectState", "New")
		state_focus   = classification.get("stateDrivenFocus", "")

		global_story_idx = 1
		for fi, feat in enumerate(features):
			feat.setdefault("featureId", f"F-{fi+1:03d}")
			feat.setdefault("featureTitle", f"Feature {fi+1}")
			for s in feat.get("stories", []):
				s.setdefault("storyId", f"US-{global_story_idx:03d}")
				s.setdefault("domain", domain)
				s.setdefault("projectState", project_state)
				s.setdefault("stateDrivenFocus", state_focus)
				s.setdefault("priority", "Medium")
				s["featureId"]    = feat["featureId"]
				s["featureTitle"] = feat["featureTitle"]
				acs = s.get("acceptanceCriteria", [])
				if acs and isinstance(acs[0], str):
					s["acceptanceCriteria"] = [
						{"acId": f"AC-{i+1:03d}",
						 "description": ac.split(":", 1)[-1].strip()}
						for i, ac in enumerate(acs)
					]
				global_story_idx += 1
		return features

	# ── rule-based domain templates ───────────────────────────────────────────

	def _rule_based_decompose(self, content: str, classification: Dict) -> List[Dict]:
		domain        = classification.get("domain", "General")
		project_state = classification.get("projectState", "New")
		state_focus   = classification.get("stateDrivenFocus", "")

		templates = {

			# ── Healthcare ────────────────────────────────────────────────────
			"Healthcare": [
				{
					"featureId": "F-001", "featureTitle": "Patient Registration",
					"stories": [
						{"storyId": "US-001", "title": "New Patient Registration",
						 "story": "As a Receptionist, I want to register a new patient, so that their records are created in the system.",
						 "role": "Receptionist", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Patient demographics (name, DOB, contact) captured and saved"},
							 {"acId": "AC-002", "description": "Unique Patient ID generated automatically"},
							 {"acId": "AC-003", "description": "Insurance/health card details linked to patient record"},
						 ]},
						{"storyId": "US-002", "title": "Patient Search & Record Retrieval",
						 "story": "As a Clinician, I want to search and retrieve patient records, so that I can review history before consultation.",
						 "role": "Clinician", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Search by patient ID, name, or DOB returns correct records"},
							 {"acId": "AC-002", "description": "Medical history, allergies, and medications visible"},
						 ]},
					],
				},
				{
					"featureId": "F-002", "featureTitle": "Appointment Scheduling",
					"stories": [
						{"storyId": "US-003", "title": "Book Appointment",
						 "story": "As a Patient, I want to book an appointment, so that I can see a doctor at a convenient time.",
						 "role": "Patient", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Available slots shown by doctor and date"},
							 {"acId": "AC-002", "description": "Confirmation SMS/email sent on booking"},
							 {"acId": "AC-003", "description": "Double-booking of the same slot is prevented"},
						 ]},
						{"storyId": "US-004", "title": "Cancel / Reschedule Appointment",
						 "story": "As a Patient, I want to cancel or reschedule an appointment, so that I can manage my schedule.",
						 "role": "Patient", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Cancellation allowed up to 2 hours before appointment"},
							 {"acId": "AC-002", "description": "Cancelled slot released for other bookings"},
							 {"acId": "AC-003", "description": "Patient notified of cancellation/reschedule confirmation"},
						 ]},
					],
				},
				{
					"featureId": "F-003", "featureTitle": "Clinical Documentation",
					"stories": [
						{"storyId": "US-005", "title": "Record Clinical Notes & Diagnosis",
						 "story": "As a Doctor, I want to record clinical notes and diagnosis, so that the patient's medical history is complete.",
						 "role": "Doctor", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Diagnosis coded using ICD-10 standard"},
							 {"acId": "AC-002", "description": "Notes auto-saved every 30 seconds"},
							 {"acId": "AC-003", "description": "Previous encounter notes visible in read-only mode"},
						 ]},
						{"storyId": "US-006", "title": "Prescription Management",
						 "story": "As a Doctor, I want to create and send prescriptions, so that the patient can get the right medication.",
						 "role": "Doctor", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Prescription includes drug name, dosage, frequency, duration"},
							 {"acId": "AC-002", "description": "Drug interaction alerts shown for conflicting medications"},
							 {"acId": "AC-003", "description": "E-prescription sent to pharmacy automatically"},
						 ]},
					],
				},
				{
					"featureId": "F-004", "featureTitle": "Billing & Claims",
					"stories": [
						{"storyId": "US-007", "title": "Generate Patient Bill",
						 "story": "As a Billing Staff, I want to generate a patient bill after consultation, so that payment can be collected.",
						 "role": "Billing Staff", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Bill itemises consultation, tests, and medication charges"},
							 {"acId": "AC-002", "description": "Insurance portion auto-deducted if applicable"},
							 {"acId": "AC-003", "description": "Bill printable and emailable to patient"},
						 ]},
						{"storyId": "US-008", "title": "Insurance Claim Submission",
						 "story": "As a Billing Staff, I want to submit insurance claims, so that the hospital receives reimbursement.",
						 "role": "Billing Staff", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Claim submitted with diagnosis codes and treatment details"},
							 {"acId": "AC-002", "description": "Claim status tracked in the system"},
							 {"acId": "AC-003", "description": "Rejected claims show reason and allow resubmission"},
						 ]},
					],
				},
			],

			# ── HR Policy ─────────────────────────────────────────────────────
			"HR Policy": [
				{
					"featureId": "F-001", "featureTitle": "Policy Creation & Publishing",
					"stories": [
						{"storyId": "US-001", "title": "Create New HR Policy",
						 "story": "As an HR Admin, I want to create a new HR policy, so that it is officially documented.",
						 "role": "HR Admin", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Policy draft saved with version number and effective date"},
							 {"acId": "AC-002", "description": "Draft sent to approver for review before publishing"},
							 {"acId": "AC-003", "description": "Policy categorised by type (Leave, Code of Conduct, etc.)"},
						 ]},
						{"storyId": "US-002", "title": "Publish & Notify Policy",
						 "story": "As an HR Admin, I want to publish an approved policy, so that employees can view it.",
						 "role": "HR Admin", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Published policy visible to all employees immediately"},
							 {"acId": "AC-002", "description": "Email notification sent to all employees on publish"},
							 {"acId": "AC-003", "description": "Previous version archived and accessible"},
						 ]},
					],
				},
				{
					"featureId": "F-002", "featureTitle": "Employee Acknowledgement",
					"stories": [
						{"storyId": "US-003", "title": "Employee Policy Acknowledgement",
						 "story": "As an Employee, I want to acknowledge that I have read the policy, so that HR has a compliance record.",
						 "role": "Employee", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Employee must tick 'I have read and understood' checkbox"},
							 {"acId": "AC-002", "description": "Acknowledgement date and time stamped against employee record"},
							 {"acId": "AC-003", "description": "Reminder email sent to non-compliant employees after 7 days"},
						 ]},
						{"storyId": "US-004", "title": "Acknowledgement Compliance Report",
						 "story": "As an HR Manager, I want to view acknowledgement compliance, so that I can follow up with non-compliant employees.",
						 "role": "HR Manager", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Report shows acknowledged vs pending count by department"},
							 {"acId": "AC-002", "description": "Report exportable to Excel"},
						 ]},
					],
				},
				{
					"featureId": "F-003", "featureTitle": "Policy Search & Version Control",
					"stories": [
						{"storyId": "US-005", "title": "Search and View Policy",
						 "story": "As an Employee, I want to search for and view HR policies, so that I can understand company rules.",
						 "role": "Employee", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Search by keyword returns relevant policies within 2 seconds"},
							 {"acId": "AC-002", "description": "Policy displayed with effective date and version number"},
							 {"acId": "AC-003", "description": "Only current active version shown by default"},
						 ]},
						{"storyId": "US-006", "title": "Policy Version History",
						 "story": "As an HR Admin, I want to view policy version history, so that I can track all changes.",
						 "role": "HR Admin", "priority": "Low",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "All versions listed with date, author, and change summary"},
							 {"acId": "AC-002", "description": "Any previous version can be viewed in read-only mode"},
						 ]},
					],
				},
			],

			# ── HR Payroll ────────────────────────────────────────────────────
			"HR Payroll": [
				{
					"featureId": "F-001", "featureTitle": "Payroll Processing",
					"stories": [
						{"storyId": "US-001", "title": "Run Monthly Payroll",
						 "story": "As a Payroll Admin, I want to run the monthly payroll, so that employees are paid accurately and on time.",
						 "role": "Payroll Admin", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Payroll calculated based on salary, attendance, and deductions"},
							 {"acId": "AC-002", "description": "Tax deductions (TDS/PAYE) computed correctly per tax slab"},
							 {"acId": "AC-003", "description": "Payroll locked after approval to prevent further changes"},
						 ]},
						{"storyId": "US-002", "title": "Process Off-Cycle Payroll",
						 "story": "As a Payroll Admin, I want to process off-cycle payroll for new joiners or corrections, so that exceptions are handled.",
						 "role": "Payroll Admin", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Off-cycle payroll run for selected employees only"},
							 {"acId": "AC-002", "description": "Audit trail recorded for all off-cycle processing"},
						 ]},
					],
				},
				{
					"featureId": "F-002", "featureTitle": "Payslip Management",
					"stories": [
						{"storyId": "US-003", "title": "Generate & Distribute Payslips",
						 "story": "As a Payroll Admin, I want to generate and distribute payslips, so that employees receive their pay details.",
						 "role": "Payroll Admin", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Payslip shows gross pay, all deductions, and net pay"},
							 {"acId": "AC-002", "description": "Payslip emailed to employee on payroll completion"},
							 {"acId": "AC-003", "description": "Payslip downloadable as PDF from self-service portal"},
						 ]},
						{"storyId": "US-004", "title": "Employee Payslip Self-Service",
						 "story": "As an Employee, I want to view and download past payslips, so that I have my pay records.",
						 "role": "Employee", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Last 24 months of payslips available"},
							 {"acId": "AC-002", "description": "Download as PDF works correctly for each month"},
						 ]},
					],
				},
				{
					"featureId": "F-003", "featureTitle": "Deductions & Benefits",
					"stories": [
						{"storyId": "US-005", "title": "Manage Statutory Deductions",
						 "story": "As a Payroll Admin, I want to configure statutory deductions, so that PF, ESI, and tax are deducted correctly.",
						 "role": "Payroll Admin", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "PF, ESI, and TDS auto-calculated per statutory rates"},
							 {"acId": "AC-002", "description": "Loan EMI deducted from salary on configured date"},
							 {"acId": "AC-003", "description": "Deduction changes take effect from the next payroll cycle"},
						 ]},
						{"storyId": "US-006", "title": "Benefits Enrolment",
						 "story": "As an Employee, I want to enrol in company benefits, so that I can avail health insurance and other perks.",
						 "role": "Employee", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Employee selects benefits during onboarding or open enrolment period"},
							 {"acId": "AC-002", "description": "Benefit deductions reflected in next payslip"},
						 ]},
					],
				},
			],

			# ── Leave Management ──────────────────────────────────────────────
			"Leave Management": [
				{
					"featureId": "F-001", "featureTitle": "Leave Application",
					"stories": [
						{"storyId": "US-001", "title": "Apply for Leave",
						 "story": "As an Employee, I want to apply for leave, so that I can request time off.",
						 "role": "Employee", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Employee selects leave type (Annual, Sick, Casual, Maternity, etc.), start date, end date"},
							 {"acId": "AC-002", "description": "System calculates number of working days automatically"},
							 {"acId": "AC-003", "description": "Application submitted with a unique reference number and email confirmation"},
						 ]},
						{"storyId": "US-002", "title": "Leave Cancellation",
						 "story": "As an Employee, I want to cancel an approved leave, so that I can update my plans.",
						 "role": "Employee", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Employee can cancel future-dated approved leave before its start date"},
							 {"acId": "AC-002", "description": "Cancelled days are credited back to the balance immediately"},
							 {"acId": "AC-003", "description": "Manager notified of the cancellation via email"},
						 ]},
					],
				},
				{
					"featureId": "F-002", "featureTitle": "Leave Approval Workflow",
					"stories": [
						{"storyId": "US-003", "title": "Manager Approve / Reject Leave",
						 "story": "As a Manager, I want to approve or reject leave requests, so that team availability is properly managed.",
						 "role": "Manager", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Manager receives email/in-app notification for pending requests"},
							 {"acId": "AC-002", "description": "Manager can approve or reject with mandatory remarks"},
							 {"acId": "AC-003", "description": "Employee notified of the decision immediately via email"},
						 ]},
						{"storyId": "US-004", "title": "Multi-Level Leave Approval",
						 "story": "As an HR Admin, I want multi-level approval for long leaves, so that extended absences are properly controlled.",
						 "role": "HR Admin", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Leaves exceeding 5 days escalated to HR for secondary approval"},
							 {"acId": "AC-002", "description": "Each approval level notified in sequence"},
							 {"acId": "AC-003", "description": "Employee notified only after all approval levels are complete"},
						 ]},
					],
				},
				{
					"featureId": "F-003", "featureTitle": "Leave Balance & Reports",
					"stories": [
						{"storyId": "US-005", "title": "Leave Balance Enquiry",
						 "story": "As an Employee, I want to check my leave balance, so that I know how many days I have available.",
						 "role": "Employee", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Balance shows available, used, and pending days per leave type"},
							 {"acId": "AC-002", "description": "Balance updates in real-time after approval or cancellation"},
						 ]},
						{"storyId": "US-006", "title": "Leave History View",
						 "story": "As an Employee, I want to view my leave history, so that I can track all past leave applications.",
						 "role": "Employee", "priority": "Low",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "History shows leave type, dates, status, and approver name"},
							 {"acId": "AC-002", "description": "Filterable by date range and status (Approved/Rejected/Cancelled)"},
						 ]},
					],
				},
			],

			# ── Insurance / Guidewire ─────────────────────────────────────────
			"Insurance": [
				{
					"featureId": "F-001", "featureTitle": "Payment Channels",
					"stories": [
						{"storyId": "US-001", "title": "Premium Payment via Web Portal",
						 "story": "As a Policyholder, I want to pay my premium through the web portal, so that I can manage payments conveniently online.",
						 "role": "Policyholder", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Policyholder can log in and navigate to the payment screen"},
							 {"acId": "AC-002", "description": "Payment is processed and a confirmation number is displayed"},
							 {"acId": "AC-003", "description": "Email receipt is sent immediately after successful payment"},
						 ]},
						{"storyId": "US-002", "title": "Premium Payment via Mobile App",
						 "story": "As a Policyholder, I want to pay my premium through the mobile app, so that I can make payments from anywhere.",
						 "role": "Policyholder", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Mobile app payment screen loads within 3 seconds"},
							 {"acId": "AC-002", "description": "Payment succeeds with valid card/bank details"},
							 {"acId": "AC-003", "description": "Push notification sent on successful payment"},
						 ]},
					],
				},
				{
					"featureId": "F-002", "featureTitle": "Autopay Management",
					"stories": [
						{"storyId": "US-003", "title": "Autopay Enrollment",
						 "story": "As a Policyholder, I want to enrol in autopay, so that my premiums are paid automatically each month.",
						 "role": "Policyholder", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "User can enter bank/card details for autopay"},
							 {"acId": "AC-002", "description": "Confirmation email sent on enrolment"},
							 {"acId": "AC-003", "description": "Autopay deduction happens on scheduled date"},
						 ]},
						{"storyId": "US-004", "title": "Autopay Cancellation",
						 "story": "As a Policyholder, I want to cancel autopay, so that I can switch to manual payment.",
						 "role": "Policyholder", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Autopay cancellation takes effect before next due date"},
							 {"acId": "AC-002", "description": "Confirmation email sent on cancellation"},
						 ]},
					],
				},
				{
					"featureId": "F-003", "featureTitle": "Error Handling & Retry",
					"stories": [
						{"storyId": "US-005", "title": "Payment Failure & Retry",
						 "story": "As a Policyholder, I want clear error messages when payment fails, so that I can correct and retry.",
						 "role": "Policyholder", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Declined card shows 'Payment declined' with retry option"},
							 {"acId": "AC-002", "description": "Network timeout shows 'Payment could not be processed, please retry'"},
							 {"acId": "AC-003", "description": "No duplicate charge created on failure"},
						 ]},
						{"storyId": "US-006", "title": "Insufficient Funds Handling",
						 "story": "As a Policyholder, I want to be notified of insufficient funds, so that I can top up and complete payment.",
						 "role": "Policyholder", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Insufficient funds error shown with clear message"},
							 {"acId": "AC-002", "description": "Link to update payment method provided"},
						 ]},
					],
				},
				{
					"featureId": "F-004", "featureTitle": "Payment History & Confirmation",
					"stories": [
						{"storyId": "US-007", "title": "Payment History & Receipts",
						 "story": "As a Policyholder, I want to view payment history and download receipts, so that I can track all transactions.",
						 "role": "Policyholder", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Payment history lists all transactions with date, amount, status"},
							 {"acId": "AC-002", "description": "Each receipt downloadable as PDF"},
							 {"acId": "AC-003", "description": "History filterable by date range"},
						 ]},
						{"storyId": "US-008", "title": "Real-Time Payment Confirmation",
						 "story": "As a Policyholder, I want real-time confirmation after payment, so that I know my policy is active.",
						 "role": "Policyholder", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Confirmation screen appears within 5 seconds of payment"},
							 {"acId": "AC-002", "description": "Policy status updates to 'Active' immediately"},
							 {"acId": "AC-003", "description": "Confirmation number is unique and traceable"},
						 ]},
					],
				},
			],

			# ── Core / Retail Banking ─────────────────────────────────────────
			"Retail Banking": [
				{
					"featureId": "F-001", "featureTitle": "Customer Onboarding & KYC",
					"stories": [
						{"storyId": "US-001", "title": "Customer KYC Verification",
						 "story": "As a Bank Officer, I want to complete KYC verification, so that the customer account is compliant.",
						 "role": "Bank Officer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Customer submits government-issued ID and address proof"},
							 {"acId": "AC-002", "description": "KYC status updated to 'Verified' after successful check"},
							 {"acId": "AC-003", "description": "Rejected KYC shows reason and allows resubmission"},
						 ]},
						{"storyId": "US-002", "title": "Account Opening",
						 "story": "As a Customer, I want to open a bank account online, so that I can access banking services.",
						 "role": "Customer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Account type selected (Savings / Current / Fixed Deposit)"},
							 {"acId": "AC-002", "description": "Account number generated within 24 hours of KYC approval"},
							 {"acId": "AC-003", "description": "Welcome kit and debit card dispatched automatically"},
						 ]},
					],
				},
				{
					"featureId": "F-002", "featureTitle": "Transactions & Fund Transfers",
					"stories": [
						{"storyId": "US-003", "title": "NEFT / RTGS Fund Transfer",
						 "story": "As a Customer, I want to transfer funds via NEFT/RTGS, so that I can send money to other banks.",
						 "role": "Customer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Transfer succeeds with valid IFSC and account number"},
							 {"acId": "AC-002", "description": "NEFT processes in next batch cycle; RTGS is real-time"},
							 {"acId": "AC-003", "description": "Debit confirmation SMS sent immediately"},
						 ]},
						{"storyId": "US-004", "title": "Account Statement Download",
						 "story": "As a Customer, I want to download my account statement, so that I can review transaction history.",
						 "role": "Customer", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Statement downloadable as PDF or CSV"},
							 {"acId": "AC-002", "description": "Date range filter works correctly"},
							 {"acId": "AC-003", "description": "Running balance shown for each transaction"},
						 ]},
					],
				},
				{
					"featureId": "F-003", "featureTitle": "Loan Management",
					"stories": [
						{"storyId": "US-005", "title": "Loan Application & Approval",
						 "story": "As a Customer, I want to apply for a loan, so that I can receive funds for my financial needs.",
						 "role": "Customer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Loan type, amount, and tenure selected by customer"},
							 {"acId": "AC-002", "description": "Credit score and eligibility checked automatically"},
							 {"acId": "AC-003", "description": "Approval/rejection decision communicated within 24 hours"},
						 ]},
						{"storyId": "US-006", "title": "EMI Repayment Tracking",
						 "story": "As a Customer, I want to view and track EMI repayments, so that I know my outstanding loan balance.",
						 "role": "Customer", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "EMI schedule shows due date, amount, and payment status"},
							 {"acId": "AC-002", "description": "Payment receipt generated for each EMI paid"},
							 {"acId": "AC-003", "description": "Overdue EMI highlighted with penalty amount shown"},
						 ]},
					],
				},
			],

			# ── Cards & Payments ──────────────────────────────────────────────
			"Cards & Payments": [
				{
					"featureId": "F-001", "featureTitle": "Card Issuance",
					"stories": [
						{"storyId": "US-001", "title": "Debit / Credit Card Application",
						 "story": "As a Customer, I want to apply for a new card, so that I can make payments conveniently.",
						 "role": "Customer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Card application submitted with account and address details"},
							 {"acId": "AC-002", "description": "Card dispatched within 5 business days"},
							 {"acId": "AC-003", "description": "PIN mailer sent separately from card"},
						 ]},
						{"storyId": "US-002", "title": "Card Activation",
						 "story": "As a Customer, I want to activate my new card, so that I can start using it.",
						 "role": "Customer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Card activated via IVR, mobile app, or net banking"},
							 {"acId": "AC-002", "description": "Confirmation SMS sent immediately after activation"},
							 {"acId": "AC-003", "description": "Card status changes to 'Active' in the system"},
						 ]},
					],
				},
				{
					"featureId": "F-002", "featureTitle": "Card Controls",
					"stories": [
						{"storyId": "US-003", "title": "Block / Unblock Card",
						 "story": "As a Customer, I want to block or unblock my card, so that I can protect myself against fraud.",
						 "role": "Customer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Card blocked immediately on request via app or call centre"},
							 {"acId": "AC-002", "description": "All transactions declined after block is activated"},
							 {"acId": "AC-003", "description": "Customer can unblock the card using OTP verification"},
						 ]},
						{"storyId": "US-004", "title": "Set Transaction Limits",
						 "story": "As a Customer, I want to set spending limits on my card, so that I can control card usage.",
						 "role": "Customer", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Daily POS, ATM, and online limits configurable separately"},
							 {"acId": "AC-002", "description": "Transactions exceeding set limit are declined with reason"},
							 {"acId": "AC-003", "description": "Limit change takes effect immediately"},
						 ]},
					],
				},
				{
					"featureId": "F-003", "featureTitle": "Statements & Disputes",
					"stories": [
						{"storyId": "US-005", "title": "Card Statement & Transaction History",
						 "story": "As a Customer, I want to view card statements, so that I can track my spending.",
						 "role": "Customer", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Monthly statement shows all transactions with merchant, amount, and date"},
							 {"acId": "AC-002", "description": "Statement downloadable as PDF"},
							 {"acId": "AC-003", "description": "Disputed transaction can be raised directly from statement view"},
						 ]},
						{"storyId": "US-006", "title": "Dispute Transaction",
						 "story": "As a Customer, I want to dispute an unrecognised transaction, so that I can protect against fraud.",
						 "role": "Customer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Dispute raised with transaction details and reason"},
							 {"acId": "AC-002", "description": "Dispute reference number provided to customer"},
							 {"acId": "AC-003", "description": "Provisional credit applied within 5 business days"},
						 ]},
					],
				},
			],

			# ── CRM ───────────────────────────────────────────────────────────
			"CRM Sales": [
				{
					"featureId": "F-001", "featureTitle": "Lead Management",
					"stories": [
						{"storyId": "US-001", "title": "Create & Qualify Lead",
						 "story": "As a Sales Rep, I want to create and qualify leads, so that I can focus on high-potential prospects.",
						 "role": "Sales Rep", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Lead created with name, email, phone, source, and company"},
							 {"acId": "AC-002", "description": "Lead score calculated automatically based on activity and profile"},
							 {"acId": "AC-003", "description": "Lead assigned to a sales rep based on territory rules"},
						 ]},
						{"storyId": "US-002", "title": "Convert Lead to Opportunity",
						 "story": "As a Sales Rep, I want to convert a qualified lead to an opportunity, so that I can track the deal.",
						 "role": "Sales Rep", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Lead converts to Opportunity with Account and Contact auto-created"},
							 {"acId": "AC-002", "description": "Opportunity stage set to 'Prospecting' by default"},
							 {"acId": "AC-003", "description": "Original lead record linked to the new opportunity"},
						 ]},
					],
				},
				{
					"featureId": "F-002", "featureTitle": "Opportunity & Pipeline",
					"stories": [
						{"storyId": "US-003", "title": "Manage Opportunity Pipeline",
						 "story": "As a Sales Manager, I want to manage the opportunity pipeline, so that I can forecast revenue accurately.",
						 "role": "Sales Manager", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Pipeline view shows all deals by stage and expected close date"},
							 {"acId": "AC-002", "description": "Deal value and win probability editable inline"},
							 {"acId": "AC-003", "description": "Forecast report generated from open opportunities"},
						 ]},
						{"storyId": "US-004", "title": "Close Won / Lost Opportunity",
						 "story": "As a Sales Rep, I want to close an opportunity as Won or Lost, so that the outcome is recorded.",
						 "role": "Sales Rep", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Closure reason mandatory for Lost opportunities"},
							 {"acId": "AC-002", "description": "Won deals trigger contract creation workflow automatically"},
							 {"acId": "AC-003", "description": "Closed opportunity no longer appears in active pipeline"},
						 ]},
					],
				},
				{
					"featureId": "F-003", "featureTitle": "Customer Account Management",
					"stories": [
						{"storyId": "US-005", "title": "Create & Update Customer Account",
						 "story": "As a Sales Rep, I want to manage customer accounts, so that all customer data is centralised.",
						 "role": "Sales Rep", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Account created with company name, industry, and address"},
							 {"acId": "AC-002", "description": "Duplicate account detection prevents creation of duplicates"},
							 {"acId": "AC-003", "description": "Account timeline shows all interactions and deals"},
						 ]},
						{"storyId": "US-006", "title": "Customer Interaction History",
						 "story": "As a Sales Rep, I want to log all customer interactions, so that the team has full context.",
						 "role": "Sales Rep", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Emails, calls, and meetings logged against the account"},
							 {"acId": "AC-002", "description": "Interaction timeline visible to all team members with access"},
						 ]},
					],
				},
			],

			# ── E-Commerce ────────────────────────────────────────────────────
			"E-Commerce": [
				{
					"featureId": "F-001", "featureTitle": "Product Discovery & Catalogue",
					"stories": [
						{"storyId": "US-001", "title": "Product Search & Browse",
						 "story": "As a Customer, I want to search and browse products, so that I can find what I need quickly.",
						 "role": "Customer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Search returns relevant results within 2 seconds"},
							 {"acId": "AC-002", "description": "Filters (category, price, brand, rating) work correctly"},
							 {"acId": "AC-003", "description": "Out-of-stock products shown with 'Notify Me' option"},
						 ]},
						{"storyId": "US-002", "title": "Product Detail View",
						 "story": "As a Customer, I want to view product details, so that I can make an informed purchase decision.",
						 "role": "Customer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Product images, description, price, and customer reviews shown"},
							 {"acId": "AC-002", "description": "Stock availability displayed in real-time"},
						 ]},
					],
				},
				{
					"featureId": "F-002", "featureTitle": "Cart & Checkout",
					"stories": [
						{"storyId": "US-003", "title": "Add to Cart and Checkout",
						 "story": "As a Customer, I want to add items to cart and checkout, so that I can purchase products.",
						 "role": "Customer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Cart persists items across browser sessions"},
							 {"acId": "AC-002", "description": "Checkout completes with valid payment details"},
							 {"acId": "AC-003", "description": "Order confirmation email sent with unique order number"},
						 ]},
						{"storyId": "US-004", "title": "Apply Coupon / Discount",
						 "story": "As a Customer, I want to apply discount coupons, so that I can reduce my purchase cost.",
						 "role": "Customer", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Valid coupon reduces order total correctly"},
							 {"acId": "AC-002", "description": "Expired or invalid coupon shows clear error message"},
						 ]},
					],
				},
				{
					"featureId": "F-003", "featureTitle": "Order Management & Returns",
					"stories": [
						{"storyId": "US-005", "title": "Order Tracking",
						 "story": "As a Customer, I want to track my order, so that I know the delivery status.",
						 "role": "Customer", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Order status updates (Placed, Shipped, Out for Delivery, Delivered)"},
							 {"acId": "AC-002", "description": "Estimated delivery date displayed and updated in real-time"},
							 {"acId": "AC-003", "description": "Tracking link provided via email/SMS"},
						 ]},
						{"storyId": "US-006", "title": "Return & Refund",
						 "story": "As a Customer, I want to return a product and get a refund, so that I can resolve unsatisfactory purchases.",
						 "role": "Customer", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Return request raised within 7 days of delivery"},
							 {"acId": "AC-002", "description": "Refund processed within 5 business days of return pickup"},
						 ]},
					],
				},
			],

			# ── Procurement / ERP ─────────────────────────────────────────────
			"Procurement": [
				{
					"featureId": "F-001", "featureTitle": "Purchase Requisition",
					"stories": [
						{"storyId": "US-001", "title": "Create Purchase Requisition",
						 "story": "As a Requester, I want to create a purchase requisition, so that I can request materials for my department.",
						 "role": "Requester", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "PR created with material description, quantity, required delivery date"},
							 {"acId": "AC-002", "description": "PR routed for approval to cost-centre manager automatically"},
							 {"acId": "AC-003", "description": "PR number generated and shared with requester by email"},
						 ]},
						{"storyId": "US-002", "title": "PR Approval & Rejection",
						 "story": "As a Manager, I want to approve or reject purchase requisitions, so that budget is controlled.",
						 "role": "Manager", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Manager receives notification for pending PRs"},
							 {"acId": "AC-002", "description": "Approved PR released to Purchasing for PO creation"},
							 {"acId": "AC-003", "description": "Rejected PR returned to requester with reason"},
						 ]},
					],
				},
				{
					"featureId": "F-002", "featureTitle": "Purchase Order Management",
					"stories": [
						{"storyId": "US-003", "title": "Create Purchase Order",
						 "story": "As a Buyer, I want to create a purchase order from an approved PR, so that I can procure materials.",
						 "role": "Buyer", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "PO created from approved PR with vendor and price details"},
							 {"acId": "AC-002", "description": "PO sent to vendor via email/EDI automatically"},
							 {"acId": "AC-003", "description": "PO number and delivery terms recorded in the system"},
						 ]},
						{"storyId": "US-004", "title": "Goods Receipt & Invoice Verification",
						 "story": "As a Warehouse Clerk, I want to record goods receipt and match it to the invoice, so that payment is accurate.",
						 "role": "Warehouse Clerk", "priority": "High",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "GRN recorded against PO with quantity and condition notes"},
							 {"acId": "AC-002", "description": "Invoice matched to PO and GRN (3-way match)"},
							 {"acId": "AC-003", "description": "Discrepancy flagged and held for resolution before payment"},
						 ]},
					],
				},
				{
					"featureId": "F-003", "featureTitle": "Vendor Management",
					"stories": [
						{"storyId": "US-005", "title": "Vendor Registration & Approval",
						 "story": "As a Procurement Admin, I want to register and approve vendors, so that only verified suppliers are used.",
						 "role": "Procurement Admin", "priority": "Medium",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Vendor registration captures company details, GST/tax ID, and bank info"},
							 {"acId": "AC-002", "description": "Vendor goes through approval workflow before activation"},
							 {"acId": "AC-003", "description": "Approved vendor added to vendor master automatically"},
						 ]},
						{"storyId": "US-006", "title": "Vendor Performance Evaluation",
						 "story": "As a Procurement Admin, I want to evaluate vendor performance, so that I can identify and retain best suppliers.",
						 "role": "Procurement Admin", "priority": "Low",
						 "acceptanceCriteria": [
							 {"acId": "AC-001", "description": "Vendor scored on delivery time, quality, and price"},
							 {"acId": "AC-002", "description": "Scorecard report generated quarterly per vendor"},
						 ]},
					],
				},
			],
		}

		# ── Domain key aliases so different spellings all resolve to a template key ──
		aliases = {
			"hcm": "HR Payroll",
			"hr payroll": "HR Payroll",
			"payroll": "HR Payroll",
			"hr policy": "HR Policy",
			"policy management": "HR Policy",
			"leave": "Leave Management",
			"leave management": "Leave Management",
			"insurance": "Insurance",
			"guidewire": "Insurance",
			"banking": "Retail Banking",
			"retail banking": "Retail Banking",
			"core banking": "Retail Banking",
			"cards": "Cards & Payments",
			"cards & payments": "Cards & Payments",
			"cards and payments": "Cards & Payments",
			"crm": "CRM Sales",
			"crm sales": "CRM Sales",
			"salesforce": "CRM Sales",
			"ecommerce": "E-Commerce",
			"e-commerce": "E-Commerce",
			"e commerce": "E-Commerce",
			"procurement": "Procurement",
			"erp": "Procurement",
			"healthcare": "Healthcare",
			"health care": "Healthcare",
		}

		# ── Domain matching: 4 strategies in order of specificity ─────────────
		matched_templates = None
		domain_lower = domain.lower().strip()

		# Strategy 1: exact key match (case-insensitive) + alias lookup
		resolved = aliases.get(domain_lower, domain_lower)
		for dom_key, feature_list in templates.items():
			if dom_key.lower() == domain_lower or dom_key.lower() == resolved.lower():
				matched_templates = feature_list
				break

		# Strategy 2: substring containment
		if not matched_templates:
			for dom_key, feature_list in templates.items():
				if dom_key.lower() in domain_lower or domain_lower in dom_key.lower():
					matched_templates = feature_list
					break

		# Strategy 3: keyword signals from the epic content
		if not matched_templates:
			content_lower = content.lower()
			keyword_map = [
				(["patient", "doctor", "clinic", "hospital", "diagnosis", "prescription", "ehr", "emr", "appointment", "clinical"], "Healthcare"),
				(["leave balance", "apply for leave", "sick leave", "annual leave", "casual leave", "leave approval", "leave type", "leave application"], "Leave Management"),
				(["hr policy", "policy document", "policy acknowledgement", "employee handbook", "code of conduct", "policy version", "policy publish"], "HR Policy"),
				(["payslip", "payroll", "salary", "deduction", "pf ", "esi", "tds", "gross pay", "net pay", "statutory deduction", "payroll admin"], "HR Payroll"),
				(["employee", "onboard", "hire", "benefit", "performance review", "hcm"], "HR Payroll"),
				(["kyc", "account opening", "neft", "rtgs", "fund transfer", "savings account", "ifsc", "core bank"], "Retail Banking"),
				(["loan", "emi", "disburs", "repay", "credit score", "collateral", "mortgage", "borrower"], "Retail Banking"),
				(["policyholder", "premium payment", "autopay", "claim", "underwriting", "insur", "policy number", "reinsur"], "Insurance"),
				(["card issu", "card activation", "card block", "cvv", "pos terminal", "card payment", "credit card", "debit card", "card limit"], "Cards & Payments"),
				(["purchase order", "vendor", "grn", "procurement", "goods receipt", "invoice", "requisition", "3-way match"], "Procurement"),
				(["lead", "opportunity", "salesforce", "crm", "campaign", "pipeline", "account management", "deal stage"], "CRM Sales"),
				(["cart", "checkout", "product listing", "sku", "ecommerce", "e-commerce", "add to cart", "return refund", "order tracking"], "E-Commerce"),
			]
			for keywords, template_key in keyword_map:
				if any(kw in content_lower for kw in keywords):
					matched_templates = templates.get(template_key)
					if matched_templates:
						break

		# Strategy 4: content-aware generic decomposition
		if not matched_templates:
			matched_templates = self._build_generic_features(content, domain)

		# Stamp domain / projectState on all stories
		global_idx = 1
		for feat in matched_templates:
			for s in feat.get("stories", []):
				s["featureId"]        = feat["featureId"]
				s["featureTitle"]     = feat["featureTitle"]
				s["domain"]           = domain
				s["projectState"]     = project_state
				s["stateDrivenFocus"] = state_focus
				s["storyId"]          = f"US-{global_idx:03d}"
				global_idx += 1

		return matched_templates

	# ── generic content-aware decomposition ───────────────────────────────────

	def _build_generic_features(self, content: str, domain: str) -> List[Dict]:
		sentences = [s.strip() for s in re.split(r'[.\n]', content) if len(s.strip()) > 20]
		features  = []
		fi, si    = 1, 1
		batch     = []
		for sent in sentences:
			if re.search(r'\b(shall|must|should|enable|allow|support|provide|user can|ability to|wants to|need to)\b', sent, re.I):
				batch.append(sent)
			if len(batch) >= 2 or (batch and fi > 3):
				stories = []
				for bsent in batch:
					title = bsent[:60].rstrip(",.")
					stories.append({
						"storyId": f"US-{si:03d}",
						"title": title,
						"story": f"As a User, I want to {bsent.lower()[:80]}, so that business goals are achieved.",
						"role": "User",
						"priority": "High" if si <= 2 else "Medium",
						"acceptanceCriteria": [
							{"acId": "AC-001", "description": f"{title} -- valid input accepted and processed successfully"},
							{"acId": "AC-002", "description": f"{title} -- invalid input rejected with a clear error message"},
						],
					})
					si += 1
				features.append({
					"featureId": f"F-{fi:03d}",
					"featureTitle": f"{domain} Feature {fi}",
					"stories": stories,
				})
				fi += 1
				batch = []
				if fi > 4:
					break

		if not features:
			features = [{
				"featureId": "F-001",
				"featureTitle": f"{domain} Core Feature",
				"stories": [{
					"storyId": "US-001",
					"title": "Core System Functionality",
					"story": "As a User, I want core system functionality, so that business objectives are met.",
					"role": "User",
					"priority": "High",
					"acceptanceCriteria": [
						{"acId": "AC-001", "description": "Feature works end-to-end with valid data"},
						{"acId": "AC-002", "description": "Error cases handled with clear messages"},
					],
				}],
			}]
		return features

	def _extract_epic_title(self, content: str) -> str:
		first_line = content.strip().split("\n")[0].strip()
		if 5 < len(first_line) < 100:
			return first_line
		return "Epic"
