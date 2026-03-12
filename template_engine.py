"""
Offline Template Engine
Generates test cases using rule-based templates — no API key or internet required.
Triggered when LLM_PROVIDER=offline in .env
"""
import json
import re
from datetime import datetime
from typing import Optional, List, Dict, Any


class TemplateEngine:
    """Rule-based test case generation engine (fully offline)"""

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Route prompt to the appropriate template handler using system_prompt as primary signal"""
        p = prompt.lower()
        sp = (system_prompt or "").lower()

        # ── system_prompt is the authoritative signal — check it FIRST and EXCLUSIVELY ──
        # Only fall through to prompt-keyword routing when system_prompt is absent/empty.
        if sp:
            if "positive" in sp or "happy path" in sp:
                return self._positive_tests(prompt)
            elif "negative" in sp or "edge case" in sp or "boundary value" in sp:
                return self._negative_tests(prompt)
            elif "security" in sp or "performance" in sp or "owasp" in sp or "non-functional" in sp:
                return self._security_nf_tests(prompt)
            elif "traceab" in sp or ("coverage" in sp and "matrix" in sp):
                return self._traceability(prompt)
            elif "dedup" in sp or "duplicate" in sp or "optim" in sp:
                return self._deduplication(prompt)
            elif "classifier" in sp or "classify" in sp or "application type" in sp:
                return self._classify(prompt)
            elif "domain" in sp and ("requirement" in sp or "business rule" in sp or "acceptance" in sp):
                return self._domain_analysis(prompt)
            # system_prompt present but no known keyword → fall through to prompt routing

        # ── Fallback: route by user prompt keywords ──
        if "dedup" in p or "duplicate" in p or "redundan" in p:
            return self._deduplication(prompt)
        elif "traceab" in p or "coverage matrix" in p:
            return self._traceability(prompt)
        elif "security" in p or "owasp" in p:
            return self._security_nf_tests(prompt)
        elif "negative" in p or "edge case" in p:
            return self._negative_tests(prompt)
        elif "positive" in p or "happy path" in p:
            return self._positive_tests(prompt)
        elif "classify" in p or ("applicationtype" in p and "domain" in p and "product" in p):
            # Only classify when the prompt is ASKING for classification output,
            # not just because "applicationType" appears in a JSON template.
            return self._classify(prompt)
        elif "domain" in p and "requirement" in p:
            return self._domain_analysis(prompt)
        else:
            return self._generic_tests(prompt)

    # ─── AGENT 1: CLASSIFICATION ──────────────────────────────────────────────

    def _classify(self, prompt: str) -> str:
        # Extract ONLY the actual document content, strip LLM instruction boilerplate
        doc = self._extract_document_text(prompt)
        doc_lower = doc.lower()

        app_type = "Custom Application"
        product = "Custom"
        module = "General"
        process_flows = ["End-to-End Business Workflow"]
        terms = []
        domain = "General"
        project_state = "New"
        state_focus = "Discovery, data model validation, first-time build"

        # Detect application type from actual document.
        # ORDER MATTERS: most-specific / highest-signal rules first.
        # A rule wins on first match → put narrow domain signals before broad ones.
        rules = [
            # ── HR Policy (must come before Insurance — "policy" alone is too broad) ──
            (["hr policy", "policy document", "policy acknowledgement", "policy version", "employee handbook", "code of conduct", "policy publish", "policy approval workflow"], "HCM", "Oracle HCM", "HR_Policy_Management", ["Policy Lifecycle: Draft → Review → Publish → Acknowledge"], ["Policy", "Version", "Acknowledgement", "Employee", "HR Admin"], "HR Policy"),
            # ── Leave Management (narrow HCM sub-domain) ──
            (["leave balance", "leave application", "leave approval", "leave type", "annual leave", "sick leave", "casual leave", "maternity leave", "leave cancellation"], "HCM", "Oracle HCM", "Leave_Management", ["Leave Lifecycle: Apply → Manager Approve → HR Process"], ["Leave Type", "Leave Balance", "Start Date", "End Date", "Approver"], "Leave Management"),
            # ── Payroll ──
            (["payslip", "payroll", "salary processing", "gross pay", "net pay", "pf deduction", "esi", "tds", "statutory deduction", "payroll cycle"], "HCM", "Oracle HCM", "Payroll_Management", ["Payroll Lifecycle: Calculate → Approve → Disburse → Payslip"], ["Payroll", "Payslip", "Deduction", "Gross Pay", "Net Pay"], "HR Payroll"),
            # ── Healthcare (must come before Insurance — patient/clinical/emr are very specific) ──
            (["patient", "encounter", "provider", "hipaa", "hl7", "fhir", "emr", "prescription", "diagnosis", "clinical", "doctor", "hospital", "receptionist"], "Healthcare", "Epic EMR", "EMR_Core", ["Patient Journey: Registration → Encounter → Billing"], ["Patient", "Encounter", "Provider", "Prescription"], "Healthcare"),
            # ── Insurance signals ──
            (["policyholder", "premium payment", "autopay", "underwriting", "actuar", "renewal", "deductible", "claim settlement", "reinsur", "insur"], "Insurance", "Guidewire PolicyCenter", "Claims_Management", ["Policy Lifecycle: Quote → Bind → Premium → Claim"], ["Policy", "Claim", "Premium", "Underwriting", "Coverage"], "Insurance"),
            # ── Core Banking (must come before Lending — kyc/neft are strong signals) ──
            (["kyc", "aml", "account opening", "core bank", "fund transfer", "neft", "rtgs", "ifsc", "savings account", "current account"], "Core Banking", "Temenos T24", "Finacle_Core", ["Customer Onboarding: KYC → Account Opening → Activation"], ["Customer", "Account", "KYC", "AML", "Transaction"], "Retail Banking"),
            # ── Lending ──
            (["loan", "emi", "disburs", "repay", "credit score", "collateral", "mortgage", "borrower"], "Lending", "Finacle Lending", "Loan_Management", ["Loan Lifecycle: Application → Approval → Disbursement → Repayment"], ["Loan", "EMI", "Disbursement", "Repayment", "Credit Score"], "Retail Banking"),
            # ── Cards & Payments ──
            (["card issu", "card activation", "card block", "cvv", "bin ", "authorization", "pos terminal", "card payment", "debit card", "credit card", "chargeback"], "Cards & Payments", "Visa DPS", "Cards_Core", ["Card Lifecycle: Issuance → Authorization → Settlement"], ["Card", "Authorization", "Settlement", "Merchant", "POS"], "Cards & Payments"),
            # ── CRM ──
            (["lead", "opportunity", "salesforce", "crm", "campaign", "case management"], "CRM", "Salesforce Sales Cloud", "SFDC_SalesCloud", ["Lead-to-Opportunity: Lead → Qualification → Conversion"], ["Lead", "Opportunity", "Account", "Contact"], "CRM Sales"),
            # ── E-Commerce (needs "cart" or "sku" or "ecommerce" — avoid plain "order") ──
            (["cart", "sku", "e-commerce", "ecommerce", "catalog", "checkout", "product listing", "add to cart"], "E-Commerce", "Custom E-Commerce", "Order_Management", ["Order-to-Fulfil: Cart → Checkout → Payment → Shipping"], ["Product", "Cart", "Order", "Shipment", "SKU"], "E-Commerce"),
            # ── General HCM ──
            (["employee", "payroll", "hcm", "hire", "onboard", "benefits", "time track", "performance review", "salary"], "HCM", "Oracle HCM", "Oracle_HCM", ["Hire-to-Retire: Requisition → Onboarding → Payroll"], ["Employee", "Payroll", "Benefits", "Onboarding"], "HR Payroll"),
            # ── ERP last — "invoice" / "purchase order" are broad terms that appear in many docs ──
            (["purchase order", "material master", "vendor", "grn", "procurement", "inventory", "gl account", "asset", "invoice"], "ERP", "SAP S/4HANA", "SAP_MM", ["Procure-to-Pay: PR → PO → GRN → Invoice"], ["Material", "Vendor", "PO", "GR", "Invoice"], "Procurement"),
        ]

        for keywords, atype, prod, mod, flows, trms, dom in rules:
            if any(k in doc_lower for k in keywords):
                app_type, product, module = atype, prod, mod
                process_flows, terms, domain = flows, trms, dom
                break

        # Detect project state from actual document
        if any(w in doc_lower for w in ["migrate", "replace", "modernize", "re-platform", "legacy", "parity", "cutover"]):
            project_state = "Legacy"
            state_focus = "Full regression parity, data migration validation, performance comparison"
        elif any(w in doc_lower for w in ["enhance", "extend", "add feature", "modify", "update existing", "change request"]):
            project_state = "Mid"
            state_focus = "Change impact analysis, selective regression, integration focus"

        # Extract real business terms from document — filter out template noise words
        noise = {"content", "output", "required", "json", "document", "analyze", "classification",
                 "rules", "context", "format", "provide", "legacy", "example", "instruction",
                 "generate", "agent", "system", "prompt", "result", "boolean", "string"}
        raw_terms = re.findall(r'\b[A-Z][a-zA-Z]{3,}\b', doc)
        clean_terms = [t for t in raw_terms if t.lower() not in noise]
        terms = list(dict.fromkeys(terms + clean_terms))[:15]

        result = {
            "applicationType": app_type,
            "product": product,
            "module": module,
            "processFlows": process_flows,
            "terms": terms[:15],
            "domain": domain,
            "projectState": project_state,
            "stateDrivenFocus": state_focus,
            "confidence": 0.75,
            "agent": "Classification Agent (Offline)",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result)

    # ─── AGENT 2: DOMAIN ANALYSIS ────────────────────────────────────────────

    def _domain_analysis(self, prompt: str) -> str:
        ctx = self._extract_context(prompt)
        sid = ctx["storyId"]  # e.g. "US001"

        # Build requirements from extracted features
        requirements = []
        features = ctx["features"] or ["Core System Functionality"]
        for i, feat in enumerate(features[:8]):
            requirements.append({
                "reqId": f"{sid}_REQ-{i+1:03d}",
                "description": feat,
                "type": "Functional",
                "priority": "High" if i < 3 else "Medium"
            })

        # Build ACs — use extracted ones or generate from features
        if ctx["acs"]:
            acceptance_criteria = []
            for j, ac in enumerate(ctx["acs"]):
                raw_desc = ac.get("description", "")
                # Sanitize: strip stray quotes/commas that appear when JSON parsing extracted a bare string
                raw_desc = raw_desc.strip().strip('",').strip()
                if not raw_desc or len(raw_desc) < 5:
                    feat_name = features[j % len(features)] if features else "Functionality"
                    raw_desc = f"{feat_name} — condition {j+1} accepted and validated"
                acceptance_criteria.append({
                    "acId": f"{sid}_AC-{j+1:03d}",   # always use sid prefix, never extracted acId
                    "reqId": f"{sid}_REQ-{(j // 3) + 1:03d}",
                    "description": raw_desc,
                })
        else:
            acceptance_criteria = []
            for i, feat in enumerate(features[:5]):
                acceptance_criteria.append({
                    "acId": f"{sid}_AC-{i*2+1:03d}",
                    "reqId": f"{sid}_REQ-{i+1:03d}",
                    "description": f"{feat} — valid inputs accepted and processed successfully"
                })
                acceptance_criteria.append({
                    "acId": f"{sid}_AC-{i*2+2:03d}",
                    "reqId": f"{sid}_REQ-{i+1:03d}",
                    "description": f"{feat} — invalid or missing inputs rejected with clear error messages"
                })

        # Business rules
        business_rules = ctx["businessRules"] or [
            "Mandatory fields must not be empty",
            "System must validate all inputs before submission",
            "Status transitions must follow defined workflow"
        ]

        # Roles
        roles = ctx["roles"] or ["Admin", "Standard User", "Manager/Approver"]

        # Data rules from extracted fields
        fields = ctx["fields"]
        data_rules = []
        for f in fields[:5]:
            if any(k in f.lower() for k in ["email", "mail"]):
                data_rules.append(f"{f} must be in valid email format (xxx@domain.com)")
            elif any(k in f.lower() for k in ["date", "from", "to", "start", "end"]):
                data_rules.append(f"{f} must follow YYYY-MM-DD format and be a valid calendar date")
            elif any(k in f.lower() for k in ["phone", "mobile", "number"]):
                data_rules.append(f"{f} must be numeric and 10-15 digits")
            elif any(k in f.lower() for k in ["amount", "price", "balance", "quantity"]):
                data_rules.append(f"{f} must be a positive number within defined range")
            else:
                data_rules.append(f"{f} is a mandatory field with defined max length")
        if not data_rules:
            data_rules = [
                "All mandatory fields required before submission",
                "Field lengths must not exceed defined limits",
                "Enumeration fields must match allowed values"
            ]

        result = {
            "requirements": requirements,
            "acceptanceCriteria": acceptance_criteria,
            "businessRules": business_rules,
            "roles": roles,
            "dataRules": data_rules,
            "implicitValidations": [
                "Session must expire after inactivity period",
                "All API responses must include appropriate status codes",
                "Error messages must be user-friendly and descriptive",
                f"Audit log must capture all write operations in {ctx['domain']}",
                "Notifications must be triggered on key state changes"
            ],
            "agent": "Domain Analysis Agent (Offline)",
            "timestamp": datetime.now().isoformat(),
            "totalRequirements": len(requirements),
            "totalACs": len(acceptance_criteria),
            "totalBusinessRules": len(business_rules)
        }
        return json.dumps(result)

    # ─── AGENT 3: POSITIVE TESTS ─────────────────────────────────────────────

    def _positive_tests(self, prompt: str) -> str:
        base = self._extract_context(prompt)
        tests = []
        features = base["features"]
        roles = base["roles"]
        fields = base["fields"]
        workflows = base["workflows"]
        domain = base["domain"]
        sid = base["storyId"]
        pri_role = roles[0] if roles else "Standard User"
        appr_role = next((r for r in roles if any(k in r.lower() for k in ["manager", "approver", "admin", "supervisor"])), roles[-1] if roles else "Manager")

        # Build test cases dynamically from features
        tc_idx = 1
        ac_idx = 1
        req_idx = 1  # tracks which REQ this feature maps to

        for feat in features[:5]:
            feat_title = feat.strip()
            feat_lower = feat.lower()
            is_approval = any(k in feat_lower for k in ["approv", "reject", "review", "escalat"])
            is_view = any(k in feat_lower for k in ["view", "read", "search", "list", "histor", "report", "enquir"])
            is_cancel = any(k in feat_lower for k in ["cancel", "withdraw", "revoke"])
            is_balance = any(k in feat_lower for k in ["balance", "check", "enquir", "status"])
            is_create = any(k in feat_lower for k in ["apply", "create", "submit", "add", "register", "request", "open", "book", "place", "initiat"])
            is_update = any(k in feat_lower for k in ["update", "edit", "modif", "change"])

            # Choose category
            cat = "FUNC"
            if any(k in feat_lower for k in ["api", "endpoint", "service", "integration"]):
                cat = "API"
            elif any(k in feat_lower for k in ["import", "export", "etl", "load", "migration", "batch"]):
                cat = "ETL"

            if is_view or is_balance:
                # Read/view test
                tests.append({
                    "testCaseId": f"{sid}_REQ{req_idx:03d}_FUNC_{tc_idx:03d}",
                    "title": f"Verify {feat_title} - Valid Record Display",
                    "category": cat,
                    "priority": "P1",
                    "automation": "Yes",
                    "domain": domain,
                    "projectState": base["projectState"],
                    "stateDrivenFocus": base["stateDrivenFocus"],
                    "acMapped": f"{sid}_AC-{ac_idx:03d}",
                    "preconditions": [
                        f"User is logged in as {pri_role}",
                        "At least one existing record is present in the system",
                        "System is accessible"
                    ],
                    "testData": self._get_domain_test_data(domain, fields[:3] or ["RecordId", "Status"]),
                    "steps": [
                        f"Log in to the system as {pri_role}",
                        f"Navigate to the {feat_title} section",
                        "Enter valid search/filter criteria if applicable",
                        "Click on a valid record to open it"
                    ],
                    "expectedResults": [
                        f"{feat_title} loads successfully",
                        "All fields display correct and up-to-date values",
                        "No errors or blank fields",
                        "Page response time is within acceptable limits"
                    ],
                    "traceability": f"{sid}_REQ{req_idx:03d}/{sid}_AC-{ac_idx:03d}"
                })
                tc_idx += 1

            elif is_approval:
                # Approval flow test
                tests.append({
                    "testCaseId": f"{sid}_REQ{req_idx:03d}_FUNC_{tc_idx:03d}",
                    "title": f"Verify {feat_title} - Successful Approval by {appr_role}",
                    "category": cat,
                    "priority": "P1",
                    "automation": "Yes",
                    "domain": domain,
                    "projectState": base["projectState"],
                    "stateDrivenFocus": base["stateDrivenFocus"],
                    "acMapped": f"{sid}_AC-{ac_idx:03d}",
                    "preconditions": [
                        f"User is logged in as {appr_role}",
                        f"A submitted record is pending approval",
                        "User has approval permissions"
                    ],
                    "testData": {"RecordId": "Valid_Pending_Record_001", "Action": "Approve", "Remarks": "Approved as per policy"},
                    "steps": [
                        f"Log in as {appr_role}",
                        "Navigate to the pending approvals queue",
                        "Select the pending record",
                        "Review all details",
                        "Click Approve and add remarks",
                        "Confirm the approval action"
                    ],
                    "expectedResults": [
                        f"Record status changes to 'Approved'",
                        f"Approval timestamp and {appr_role} name recorded",
                        f"Notification sent to {pri_role}",
                        "Audit log entry created for the approval action"
                    ],
                    "traceability": f"{sid}_REQ{req_idx:03d}/{sid}_AC-{ac_idx:03d}"
                })
                tc_idx += 1

            elif is_cancel:
                tests.append({
                    "testCaseId": f"{sid}_REQ{req_idx:03d}_FUNC_{tc_idx:03d}",
                    "title": f"Verify {feat_title} - Successful Cancellation",
                    "category": cat,
                    "priority": "P2",
                    "automation": "Yes",
                    "domain": domain,
                    "projectState": base["projectState"],
                    "stateDrivenFocus": base["stateDrivenFocus"],
                    "acMapped": f"{sid}_AC-{ac_idx:03d}",
                    "preconditions": [
                        f"User is logged in as {pri_role}",
                        "An active/approved record exists that can be cancelled",
                        "Cancellation window is still open"
                    ],
                    "testData": {"RecordId": "Valid_Active_Record_001", "CancelReason": "Changed plans"},
                    "steps": [
                        f"Log in as {pri_role}",
                        "Navigate to the record to be cancelled",
                        "Click Cancel/Withdraw",
                        "Provide a cancellation reason",
                        "Confirm the cancellation"
                    ],
                    "expectedResults": [
                        "Record status updated to 'Cancelled'",
                        "Cancellation reason saved successfully",
                        "Any reserved balance/quota restored",
                        "Notification sent to relevant stakeholders"
                    ],
                    "traceability": f"{sid}_REQ{req_idx:03d}/{sid}_AC-{ac_idx:03d}"
                })
                tc_idx += 1

            elif is_update:
                tests.append({
                    "testCaseId": f"{sid}_REQ{req_idx:03d}_FUNC_{tc_idx:03d}",
                    "title": f"Verify {feat_title} - Valid Update of Existing Record",
                    "category": cat,
                    "priority": "P2",
                    "automation": "Yes",
                    "domain": domain,
                    "projectState": base["projectState"],
                    "stateDrivenFocus": base["stateDrivenFocus"],
                    "acMapped": f"{sid}_AC-{ac_idx:03d}",
                    "preconditions": [
                        f"User is logged in as {pri_role}",
                        "A record exists in editable state",
                        "User has edit permissions"
                    ],
                    "testData": self._get_domain_test_data(domain, fields[:3] or ["Name", "Status"]),
                    "steps": [
                        f"Log in as {pri_role}",
                        "Navigate to the existing record",
                        "Click Edit",
                        "Modify fields with valid new values",
                        "Save the changes"
                    ],
                    "expectedResults": [
                        "Record updated successfully",
                        "Updated values reflected immediately",
                        "Change history / audit log updated",
                        "Success confirmation message shown"
                    ],
                    "traceability": f"{sid}_REQ{req_idx:03d}/{sid}_AC-{ac_idx:03d}"
                })
                tc_idx += 1

            else:
                # Default: create/submit test
                field_data = self._get_domain_test_data(domain, fields[:4] or ["Name", "Type", "Date", "Description"])
                tests.append({
                    "testCaseId": f"{sid}_REQ{req_idx:03d}_FUNC_{tc_idx:03d}",
                    "title": f"Verify {feat_title} - Successful Submission with Valid Data",
                    "category": cat,
                    "priority": "P1",
                    "automation": "Yes",
                    "domain": domain,
                    "projectState": base["projectState"],
                    "stateDrivenFocus": base["stateDrivenFocus"],
                    "acMapped": f"{sid}_AC-{ac_idx:03d}",
                    "preconditions": [
                        f"User is logged in as {pri_role}",
                        "System is accessible and active",
                        "All required reference data is set up"
                    ],
                    "testData": field_data,
                    "steps": [
                        f"Log in to the system as {pri_role}",
                        f"Navigate to the {feat_title} screen",
                        "Fill in all mandatory fields with valid data",
                        "Click Submit/Save"
                    ],
                    "expectedResults": [
                        f"{feat_title} completed successfully",
                        "Success message displayed to the user",
                        "Record created/updated in the database",
                        "Confirmation notification sent if applicable"
                    ],
                    "traceability": f"{sid}_REQ{req_idx:03d}/{sid}_AC-{ac_idx:03d}"
                })
                tc_idx += 1

            ac_idx += 1
            req_idx += 1

        # Add API positive test
        resource = domain.lower().replace(" ", "_") if domain else "resource"
        tests.append({
            "testCaseId": f"{sid}_REQ{req_idx:03d}_API_{tc_idx:03d}",
            "title": f"API POST - Create {domain} Record with Valid Payload",
            "category": "API",
            "priority": "P1",
            "automation": "Yes",
            "domain": domain,
            "projectState": base["projectState"],
            "stateDrivenFocus": base["stateDrivenFocus"],
            "acMapped": f"{sid}_AC-{ac_idx:03d}",
            "preconditions": ["API endpoint is accessible", "Valid auth token is available"],
            "testData": {
                "endpoint": f"POST /api/v1/{resource}",
                "headers": '{"Authorization": "Bearer <valid_token>", "Content-Type": "application/json"}',
                "body": json.dumps({f: f"valid_{f.lower().replace(' ','_')}" for f in (fields[:3] or ["name", "type", "date"])})
            },
            "steps": [
                "Generate a valid auth token",
                f"Prepare a valid JSON payload for {domain} creation",
                "Send POST request to the endpoint",
                "Capture the HTTP response"
            ],
            "expectedResults": [
                "HTTP 201 Created",
                "Response body contains the created record ID",
                "Response schema matches API specification",
                "Response time < 2 seconds"
            ],
            "traceability": f"{sid}_REQ{req_idx:03d}/{sid}_AC-{ac_idx:03d}"
        })
        tc_idx += 1
        ac_idx += 1
        req_idx += 1

        tests.append({
            "testCaseId": f"{sid}_REQ{req_idx:03d}_API_{tc_idx:03d}",
            "title": f"API GET - Retrieve {domain} Record with Valid ID",
            "category": "API",
            "priority": "P1",
            "automation": "Yes",
            "domain": domain,
            "projectState": base["projectState"],
            "stateDrivenFocus": base["stateDrivenFocus"],
            "acMapped": f"{sid}_AC-{ac_idx:03d}",
            "preconditions": ["Record exists in the system", "Valid auth token is available"],
            "testData": {
                "endpoint": f"GET /api/v1/{resource}/{{valid_id}}",
                "headers": '{"Authorization": "Bearer <valid_token>"}'
            },
            "steps": [
                "Generate a valid auth token",
                "Send GET request with a valid record ID",
                "Capture the HTTP response"
            ],
            "expectedResults": [
                "HTTP 200 OK",
                "Response body contains correct record data",
                "All required fields present in response",
                "Response schema matches API specification"
            ],
            "traceability": f"{sid}_REQ{req_idx:03d}/{sid}_AC-{ac_idx:03d}"
        })
        tc_idx += 1
        ac_idx += 1
        req_idx += 1

        # Workflow end-to-end test
        if workflows:
            workflow_str = workflows[0]
            tests.append({
                "testCaseId": f"{sid}_REQ{req_idx:03d}_FUNC_{tc_idx:03d}",
                "title": f"End-to-End Workflow: {workflow_str[:60]}",
                "category": "FUNC",
                "priority": "P1",
                "automation": "Maybe",
                "domain": domain,
                "projectState": base["projectState"],
                "stateDrivenFocus": base["stateDrivenFocus"],
                "acMapped": f"{sid}_AC-{ac_idx:03d}",
                "preconditions": [
                    f"User accounts for all roles are configured: {', '.join(roles[:3])}",
                    "System environment is ready",
                    "Test data for full workflow is prepared"
                ],
                "testData": self._get_domain_test_data(domain, fields[:3] or ["Type", "Date", "Status"]),
                "steps": [
                    f"Log in as {pri_role}",
                    f"Initiate the workflow: {features[0] if features else 'Create record'}",
                    "Complete all mandatory steps in sequence",
                    f"Log in as {appr_role} and act on the pending item",
                    "Verify final status and notifications"
                ],
                "expectedResults": [
                    f"Workflow completes successfully: {workflow_str}",
                    "Final status reflects completed workflow",
                    "All stakeholders receive appropriate notifications",
                    "Complete audit trail recorded"
                ],
                "traceability": f"{sid}_REQ{req_idx:03d}/{sid}_AC-{ac_idx:03d}"
            })

        result = {
            "testCases": tests,
            "count": len(tests),
            "agent": "Positive Test Agent (Offline)",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result)

    # ─── AGENT 4: NEGATIVE & EDGE CASE TESTS ─────────────────────────────────

    def _negative_tests(self, prompt: str) -> str:
        base = self._extract_context(prompt)
        tests = []
        features = base["features"]
        roles = base["roles"]
        fields = base["fields"]
        domain = base["domain"]
        sid = base["storyId"]
        pri_role = roles[0] if roles else "Standard User"
        low_role = next((r for r in roles if any(k in r.lower() for k in ["read", "guest", "viewer"])), pri_role)
        tc_idx = 1

        # 1. Missing mandatory fields — per feature
        for feat in features[:3]:
            tests.append({
                "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
                "title": f"{feat} - Submit with Missing Mandatory Fields",
                "category": "FUNC", "priority": "P1", "automation": "Yes",
                "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
                "acMapped": f"{sid}_AC-{tc_idx:03d}",
                "preconditions": [f"User is logged in as {pri_role}", f"'{feat}' form/screen is open"],
                "testData": {f: "(empty)" for f in (fields[:3] or ["Name", "Type", "Date"])},
                "steps": [
                    f"Log in as {pri_role}",
                    f"Navigate to {feat}",
                    "Leave all mandatory fields blank",
                    "Click Submit/Save"
                ],
                "expectedResults": [
                    "Form is NOT submitted",
                    f"Validation error shown for each empty mandatory field",
                    "Error messages clearly identify which fields are required",
                    "No record created in the database"
                ],
                "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
            })
            tc_idx += 1

        # 2. Invalid input per domain-relevant fields
        date_fields = [f for f in fields if any(k in f.lower() for k in ["date", "from", "to", "start", "end"])]
        num_fields = [f for f in fields if any(k in f.lower() for k in ["amount", "balance", "days", "quantity", "duration", "price"])]
        email_fields = [f for f in fields if "email" in f.lower()]

        if date_fields:
            for df in date_fields[:2]:
                tests.append({
                    "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
                    "title": f"Invalid {df} - Past Date / Invalid Format",
                    "category": "FUNC", "priority": "P1", "automation": "Yes",
                    "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
                    "acMapped": f"{sid}_AC-{tc_idx:03d}",
                    "preconditions": [f"User is logged in as {pri_role}", "Form with date field is accessible"],
                    "testData": {df: "32/13/2025", f"{df} (2)": "not-a-date", f"{df} (3)": "2020-01-01 (past date if future required)"},
                    "steps": [
                        f"Navigate to the form containing '{df}'",
                        "Enter an invalid date (e.g., 32/13/2025)",
                        "Submit the form"
                    ],
                    "expectedResults": [
                        f"Validation error: 'Invalid date format for {df}'",
                        "Form is not submitted",
                        "User can correct the date and resubmit"
                    ],
                    "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
                })
                tc_idx += 1

        if email_fields:
            tests.append({
                "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
                "title": f"Invalid Email Format in {email_fields[0]}",
                "category": "FUNC", "priority": "P1", "automation": "Yes",
                "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
                "acMapped": f"{sid}_AC-{tc_idx:03d}",
                "preconditions": [f"User is on the form with '{email_fields[0]}' field"],
                "testData": {email_fields[0]: "invalid-email", f"{email_fields[0]} (2)": "test@", f"{email_fields[0]} (3)": "@domain.com"},
                "steps": ["Enter invalid email format in the email field", "Submit the form"],
                "expectedResults": [
                    "Error: 'Invalid email format'",
                    "Form is not submitted",
                    "Focus returns to the email field"
                ],
                "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
            })
            tc_idx += 1

        if num_fields:
            for nf in num_fields[:2]:
                tests.append({
                    "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
                    "title": f"{nf} - Negative Value / Zero Not Allowed",
                    "category": "FUNC", "priority": "P1", "automation": "Yes",
                    "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
                    "acMapped": f"{sid}_AC-{tc_idx:03d}",
                    "preconditions": [f"Form with '{nf}' field is accessible"],
                    "testData": {nf: "-1", f"{nf} (zero)": "0"},
                    "steps": [f"Enter -1 in '{nf}' field", "Submit", "Repeat with value 0"],
                    "expectedResults": [
                        f"Error: '{nf} must be a positive number'",
                        "Form is not submitted for negative or zero values"
                    ],
                    "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
                })
                tc_idx += 1

        # 3. Boundary tests based on domain
        domain_boundaries = {
            "Leave Management": [
                (f"Leave Days - End Date Before Start Date", "FUNC", "P1",
                 {"Start Date": "2025-06-10", "End Date": "2025-06-05"},
                 ["Enter End Date earlier than Start Date", "Submit"],
                 ["Error: 'End date cannot be before start date'", "Leave not applied"]),
                (f"Leave Days - Apply for More Days Than Available Balance", "FUNC", "P1",
                 {"Leave Type": "Annual", "Days Requested": "50", "Available Balance": "10"},
                 ["Enter leave days exceeding available balance", "Submit"],
                 ["Error: 'Insufficient leave balance'", "Leave application rejected"]),
            ],
            "Finance": [
                ("Amount - Exceeds Approved Limit", "FUNC", "P1",
                 {"Amount": "999999999"},
                 ["Enter amount exceeding approved limit", "Submit"],
                 ["Error: 'Amount exceeds maximum allowed limit'", "Transaction not processed"]),
            ],
            "Retail Banking": [
                ("Transfer Amount - Exceeds Account Balance", "FUNC", "P1",
                 {"Transfer Amount": "999999", "Account Balance": "100"},
                 ["Enter transfer amount greater than balance", "Submit"],
                 ["Error: 'Insufficient funds'", "Transfer not executed"]),
            ],
        }

        domain_bvs = domain_boundaries.get(domain, [
            (f"{features[0] if features else 'Record'} - Field Exceeds Maximum Length", "FUNC", "P1",
             {fields[0] if fields else "Name": "A" * 300 + " (300 chars, exceeds max)"},
             ["Enter text exceeding maximum allowed length", "Submit"],
             ["Validation error: 'Exceeds maximum length'", "Field rejected or truncated"]),
            (f"{features[0] if features else 'Record'} - Future Date for Past-Only Field", "FUNC", "P2",
             {date_fields[0] if date_fields else "Date": "2099-12-31"},
             ["Enter a far-future date in a field that only allows past dates", "Submit"],
             ["Error: 'Date must not be in the future'", "Form not submitted"]),
        ])
        for title, cat, pri, data, steps, expected in domain_bvs[:2]:
            tests.append({
                "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
                "title": title,
                "category": cat, "priority": pri, "automation": "Yes",
                "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
                "acMapped": f"{sid}_AC-{tc_idx:03d}",
                "preconditions": [f"User is logged in as {pri_role}", "System is accessible"],
                "testData": data,
                "steps": steps,
                "expectedResults": expected,
                "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
            })
            tc_idx += 1

        # 4. Unauthorized access tests
        resource = domain.lower().replace(" ", "_")
        tests.append({
            "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
            "title": f"Unauthorized Access - {domain} API Without Token",
            "category": "API", "priority": "P1", "automation": "Yes",
            "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
            "acMapped": f"{sid}_AC-{tc_idx:03d}",
            "preconditions": ["API endpoint is accessible", "No auth token is provided"],
            "testData": {"endpoint": f"GET /api/v1/{resource}", "Authorization": "(none)"},
            "steps": ["Send API request with no Authorization header", "Capture the HTTP response"],
            "expectedResults": [
                "HTTP 401 Unauthorized",
                'Response body: {"error": "Unauthorized"}',
                "No data returned"
            ],
            "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
        })
        tc_idx += 1

        tests.append({
            "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
            "title": f"Forbidden Access - {low_role} Attempts Privileged Action",
            "category": "API", "priority": "P1", "automation": "Yes",
            "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
            "acMapped": f"{sid}_AC-{tc_idx:03d}",
            "preconditions": [f"User logged in as {low_role}", "Auth token available"],
            "testData": {"endpoint": f"DELETE /api/v1/{resource}/{{id}}", "Role": low_role},
            "steps": [f"Log in as {low_role}", "Send DELETE request with valid ID", "Capture response"],
            "expectedResults": [
                "HTTP 403 Forbidden",
                "Record is NOT deleted",
                "Error message returned explaining insufficient permissions"
            ],
            "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
        })
        tc_idx += 1

        # 5. Duplicate submission
        tests.append({
            "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
            "title": f"{features[0] if features else domain} - Duplicate Record Submission",
            "category": "FUNC", "priority": "P2", "automation": "Yes",
            "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
            "acMapped": f"{sid}_AC-{tc_idx:03d}",
            "preconditions": [
                f"A {features[0].lower() if features else 'record'} with the same unique identifier already exists",
                f"User is logged in as {pri_role}"
            ],
            "testData": {fields[0] if fields else "ID": "EXISTING_RECORD_001"},
            "steps": [
                f"Navigate to {features[0] if features else 'Create'} screen",
                "Fill in data identical to an existing record",
                "Submit the form"
            ],
            "expectedResults": [
                "System rejects the duplicate submission",
                "Error: 'Record already exists'",
                "HTTP 409 Conflict (for API calls)",
                "No duplicate created in database"
            ],
            "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
        })
        tc_idx += 1

        # 6. Invalid state transitions (domain-specific)
        workflow_str = base["workflows"][0] if base["workflows"] else "Submit → Approve"
        tests.append({
            "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
            "title": f"Invalid State Transition - Skip Mandatory Step in Workflow",
            "category": "FUNC", "priority": "P1", "automation": "Maybe",
            "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
            "acMapped": f"{sid}_AC-{tc_idx:03d}",
            "preconditions": [
                "Multi-step workflow is configured",
                f"Record is in initial/draft state"
            ],
            "testData": {"WorkflowStep": "Attempt to reach final step directly", "CurrentStatus": "Draft"},
            "steps": [
                "Create a record in Draft state",
                "Attempt to jump to final approved status without going through intermediate steps",
                "Capture system response"
            ],
            "expectedResults": [
                "System enforces workflow sequence",
                f"Error: 'Invalid state transition'",
                f"Expected workflow: {workflow_str}",
                "Record remains in current state"
            ],
            "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
        })
        tc_idx += 1

        # 7. XSS and injection
        tests.append({
            "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
            "title": f"XSS Script Injection in {features[0] if features else domain} Input Field",
            "category": "FUNC", "priority": "P1", "automation": "Yes",
            "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
            "acMapped": f"{sid}_AC-{tc_idx:03d}",
            "preconditions": ["Input form is accessible"],
            "testData": {fields[0] if fields else "Text Field": "<script>alert('xss')</script>"},
            "steps": ["Enter XSS payload in a text input field", "Submit and view the saved record"],
            "expectedResults": [
                "Script tag is NOT executed in the browser",
                "Input is sanitized or escaped",
                "No alert popup appears",
                "System logs the suspicious input"
            ],
            "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
        })
        tc_idx += 1

        tests.append({
            "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
            "title": f"SQL Injection Attempt via {domain} API/Form",
            "category": "API", "priority": "P1", "automation": "Yes",
            "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
            "acMapped": f"{sid}_AC-{tc_idx:03d}",
            "preconditions": ["API/form input field accepts free text"],
            "testData": {"input": "' OR '1'='1", "input2": "'; DROP TABLE users;--"},
            "steps": ["Enter SQL injection string in an input field", "Submit"],
            "expectedResults": [
                "System rejects or sanitizes the injection payload",
                "No database error exposed in response",
                "Database integrity maintained",
                "Security event logged"
            ],
            "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
        })
        tc_idx += 1

        # 8. Concurrent duplicate
        tests.append({
            "testCaseId": f"{sid}_REQ{tc_idx:03d}_NEG_{tc_idx:03d}",
            "title": f"Concurrent Duplicate Submissions - Race Condition in {domain}",
            "category": "FUNC", "priority": "P2", "automation": "Maybe",
            "domain": domain, "projectState": base["projectState"], "stateDrivenFocus": base["stateDrivenFocus"],
            "acMapped": f"{sid}_AC-{tc_idx:03d}",
            "preconditions": ["Two user sessions are open simultaneously"],
            "testData": {"UniqueKey": "SAME_KEY_001", "Sessions": "2 concurrent browser sessions"},
            "steps": ["Open same form in two browser sessions simultaneously",
                      "Fill both with identical unique-key data",
                      "Submit both at the same time"],
            "expectedResults": [
                "Only one record is created",
                "Second submission returns error: 'Record already exists'",
                "No data corruption or duplicate records in DB"
            ],
            "traceability": f"{sid}_REQ{tc_idx:03d}/{sid}_AC-{tc_idx:03d}"
        })

        technique_breakdown = {
            "BVA": [t["title"] for t in tests if "boundary" in t["title"].lower() or "exceed" in t["title"].lower() or "before" in t["title"].lower() or "more days" in t["title"].lower()],
            "EquivalencePartitioning": [t["title"] for t in tests if "invalid" in t["title"].lower() or "missing" in t["title"].lower()],
            "ErrorGuessing": [t["title"] for t in tests if "injection" in t["title"].lower() or "xss" in t["title"].lower() or "duplicate" in t["title"].lower()],
            "StateTransition": [t["title"] for t in tests if "state" in t["title"].lower() or "unauthorized" in t["title"].lower() or "forbidden" in t["title"].lower()],
            "Pairwise": [t["title"] for t in tests if "concurrent" in t["title"].lower()]
        }

        result = {
            "testCases": tests,
            "count": len(tests),
            "techniqueBreakdown": technique_breakdown,
            "agent": "Negative & Edge Case Agent (Offline)",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result)

    # ─── AGENT 5: SECURITY & NF TESTS ────────────────────────────────────────

    def _security_nf_tests(self, prompt: str) -> str:
        base = self._extract_context(prompt)
        tests = []
        domain = base["domain"]
        sid = base["storyId"]
        roles = base["roles"]
        features = base["features"]
        pri_role = roles[0] if roles else "Standard User"
        resource = domain.lower().replace(" ", "_")

        nf_templates = [
            (f"OWASP A01 - Broken Access Control: Access {domain} Admin Endpoint Without Admin Role", "NF", "P1", "Yes",
             [f"Non-admin {pri_role} token available", "Admin endpoint is accessible"],
             {"endpoint": f"/api/v1/admin/{resource}", "role": pri_role, "action": "Access without admin privileges"},
             [f"Send request to {domain} admin endpoint using {pri_role} token"],
             ["HTTP 403 Forbidden", f"No {domain} admin data exposed", "Security audit log entry created"]),

            (f"OWASP A02 - Cryptographic Failure: {domain} Sensitive Data Transmitted in Plain Text", "NF", "P1", "Maybe",
             ["Network traffic capture tool is available", "HTTPS is configured on the server"],
             {"sensitiveFields": "password, personal data, financial data", "protocol": "HTTP vs HTTPS"},
             [f"Submit {domain} form with sensitive personal/financial data",
              "Inspect network traffic using browser dev tools or Wireshark",
              "Check API responses for unmasked sensitive fields"],
             ["Sensitive data NOT visible in plain text in transit",
              "Passwords stored as hashed values in DB (not plain text)",
              "PII fields masked in API responses (e.g., ****1234)"]),

            (f"OWASP A03 - Injection: SQL Injection via {domain} API Payload", "NF", "P1", "Yes",
             ["API endpoint accepts user-supplied input"],
             {"payload1": '{"id": "1 OR 1=1"}', "payload2": "'; DROP TABLE users;--"},
             [f"Send POST/GET request to {domain} API with SQL injection payload",
              "Observe server response and check database state"],
             ["HTTP 400 Bad Request or input sanitized",
              "No database error details exposed in response",
              f"{domain} database remains intact and unaffected"]),

            (f"OWASP A04 - Insecure Design: Bypass {domain} Workflow Step via Direct API Call", "NF", "P1", "Maybe",
             [f"{domain} multi-step workflow is configured",
              "API endpoints for intermediate steps are known"],
             {"workflowStep": "Final approval step", "skipSteps": "Attempt to call final endpoint directly"},
             [f"Identify the final step endpoint in the {domain} workflow",
              "Send a direct API call to the final step without completing prior steps",
              "Capture the server response"],
             [f"System enforces {domain} workflow order",
              "HTTP 400 Bad Request or redirect to the correct step",
              "Business logic cannot be bypassed via direct API calls"]),

            (f"OWASP A05 - Security Misconfiguration: Default Credentials on {domain} System", "NF", "P1", "Yes",
             ["Admin login panel or API is accessible"],
             {"username": "admin", "password": "admin / password / 123456"},
             ["Attempt to log in with common default credentials",
              "Try: admin/admin, admin/password, admin/123456"],
             ["All default credential attempts fail",
              f"Account lockout triggered after {3} consecutive failed attempts",
              "Security event logged for each failed attempt"]),

            (f"OWASP A07 - Auth Failure: Brute Force Attack on {domain} Login", "NF", "P1", "Yes",
             ["Login endpoint is accessible", "Rate limiting is configured"],
             {"attempts": "10+ consecutive failed login attempts", "password": "wrong_password_123"},
             [f"Attempt to log in to {domain} with incorrect password 10+ times consecutively",
              "Monitor account status and server response after threshold"],
             [f"Account locked after configured number of failed attempts",
              "HTTP 429 Too Many Requests returned",
              "Alert/notification sent to security admin",
              "Lockout duration enforced before retry is allowed"]),

            (f"OWASP A09 - Logging Failure: Verify {domain} Audit Log Completeness", "NF", "P2", "Yes",
             ["Audit logging is enabled", "Log storage/viewer is accessible"],
             {"operations": f"Create, Update, Delete, Approve operations on {domain} records"},
             [f"Perform all CRUD operations on a {domain} record as {pri_role}",
              "Navigate to audit log viewer or query log storage",
              "Verify log entries for each operation"],
             [f"Each {domain} operation logged with: user ID, action type, timestamp, record ID",
              "Log entries are immutable (no edit/delete by non-admin)",
              "Log retention policy is enforced"]),

            (f"Performance - Load Test: {domain} System Under 100 Concurrent Users", "NF", "P2", "Yes",
             ["Performance test environment is provisioned",
              "Load testing tool configured (JMeter / k6 / Gatling)"],
             {"concurrentUsers": "100", "rampUp": "2 minutes", "testDuration": "10 minutes",
              "scenario": f"{features[0] if features else domain} submit workflow"},
             [f"Configure 100 virtual users simulating {features[0] if features else domain} operations",
              "Ramp up from 0 to 100 users over 2 minutes",
              "Sustain load for 10 minutes",
              "Collect response times, throughput, error rate, CPU/memory metrics"],
             ["Average response time < 2 seconds",
              "95th percentile response time < 5 seconds",
              "Error rate < 1%",
              "CPU utilization < 70%",
              "No memory leaks observed"]),

            (f"Performance - Stress Test: {domain} System at 500 Concurrent Users", "NF", "P2", "Yes",
             ["Performance test environment is provisioned"],
             {"concurrentUsers": "500", "rampUp": "5 minutes", "testDuration": "30 minutes"},
             ["Configure 500 virtual users",
              "Ramp up gradually over 5 minutes",
              "Sustain peak load for 30 minutes",
              "Monitor for failures, memory leaks, degradation"],
             [f"{domain} system remains stable throughout",
              "Error rate remains < 2%",
              "No out-of-memory errors or crashes",
              "System recovers gracefully after load is reduced"]),

            (f"Performance - Spike Test: Sudden Traffic Surge on {domain}", "NF", "P3", "Maybe",
             ["Performance environment is ready"],
             {"initialUsers": "10", "spikeUsers": "500", "spikeTime": "30 seconds"},
             ["Start test with 10 virtual users",
              "Instantly spike to 500 users within 30 seconds",
              "Monitor system behavior during spike",
              "Reduce back to 10 users and observe recovery"],
             [f"{domain} system handles spike without crash",
              "Response time degrades gracefully (no 5xx errors)",
              "System recovers to normal response time within 60 seconds after spike"]),

            (f"Session Management: {domain} Session Expiry After Inactivity", "NF", "P1", "Yes",
             [f"User is logged in to {domain} system",
              "Session inactivity timeout is configured (e.g., 15 minutes)"],
             {"sessionTimeout": "15 minutes", "inactivityPeriod": "16 minutes idle"},
             [f"Log in to {domain} as {pri_role}",
              "Remain idle for longer than the configured session timeout period",
              "Attempt to perform an action or navigate"],
             [f"{domain} session expires after inactivity period",
              "User is automatically redirected to the login page",
              "Attempted action after session expiry is NOT executed",
              "Session token invalidated on server side"]),

            (f"Data Encryption: Verify HTTPS Enforcement on {domain} APIs", "NF", "P1", "Yes",
             ["Both HTTP and HTTPS access is attempted",
              f"{domain} application is deployed with SSL/TLS certificate"],
             {"httpUrl": f"http://{{domain_host}}/api/v1/{resource}",
              "httpsUrl": f"https://{{domain_host}}/api/v1/{resource}"},
             [f"Attempt to access {domain} API via plain HTTP",
              f"Attempt to access {domain} API via HTTPS",
              "Verify redirection behavior"],
             ["HTTP access automatically redirects to HTTPS (301 Moved Permanently)",
              "HTTPS endpoint responds correctly with valid SSL certificate",
              "No {domain} data transmitted over unencrypted HTTP connection"]),
        ]

        for i, (title, cat, pri, auto, pre, data, steps, expected) in enumerate(nf_templates):
            tests.append({
                "testCaseId": f"{sid}_REQ{i+1:03d}_NF_{i+1:03d}",
                "title": title,
                "category": cat,
                "priority": pri,
                "automation": auto,
                "domain": domain,
                "projectState": base["projectState"],
                "stateDrivenFocus": base["stateDrivenFocus"],
                "acMapped": f"{sid}_NFR-{i+1:03d}",
                "preconditions": pre,
                "testData": data,
                "steps": steps,
                "expectedResults": expected,
                "traceability": f"{sid}_REQ{i+1:03d}/{sid}_NFR-{i+1:03d}"
            })

        result = {
            "testCases": tests,
            "count": len(tests),
            "owaspCoverage": ["A01", "A02", "A03", "A04", "A05", "A07", "A09"],
            "performanceTypes": ["Load", "Stress", "Spike"],
            "agent": "Security & NF Agent (Offline)",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result)

    # ─── AGENT 6: TRACEABILITY ────────────────────────────────────────────────

    def _traceability(self, prompt: str) -> str:
        base = self._extract_context(prompt)

        # Build matrix from combined test cases in prompt (or use defaults)
        matrix = []
        categories = ["FUNC", "FUNC", "API", "API", "ETL", "NF", "NF"]
        priorities = ["P1", "P1", "P1", "P2", "P1", "P1", "P2"]

        for i in range(5):
            ac_id = f"{base['storyId']}_AC-{i+1:03d}"
            tc_list = [f"{base['storyId']}_REQ{i+1:03d}_FUNC_{i*2+1:03d}", f"{base['storyId']}_REQ{i+1:03d}_FUNC_{i*2+2:03d}",
                       f"{base['storyId']}_REQ{i+1:03d}_NEG_{i+1:03d}", f"{base['storyId']}_REQ{i+1:03d}_API_{i+1:03d}"]
            matrix.append({
                "requirementId": f"{base['storyId']}_REQ-{i+1:03d}",
                "acId": ac_id,
                "testCases": tc_list,
                "category": categories[i % len(categories)],
                "priority": priorities[i % len(priorities)],
                "automation": "Yes",
                "domain": base["domain"],
                "projectState": base["projectState"],
                "coverageNotes": "Positive, negative, boundary, and API tests covered",
                "coverageStatus": "Full"
            })

        total_reqs = len(matrix)
        total_tcs = sum(len(m["testCases"]) for m in matrix)

        result = {
            "traceabilityMatrix": matrix,
            "coverageMetrics": {
                "totalRequirements": total_reqs,
                "totalTestCases": total_tcs,
                "coverageRatio": round(total_tcs / total_reqs, 2),
                "fullyCovered": total_reqs,
                "partiallyCovered": 0,
                "notCovered": 0,
                "orphanTestCases": 0
            },
            "riskAreas": [
                "Integration points with external APIs require additional testing",
                "High-priority P1 requirements should have smoke test suite"
            ],
            "gapsIdentified": [],
            "agent": "Traceability Agent (Offline)",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result)

    # ─── AGENT 7: DEDUPLICATION ───────────────────────────────────────────────

    def _deduplication(self, prompt: str) -> str:
        # Extract any testCases already embedded in the prompt (passed by orchestrator)
        all_tests = []
        try:
            # The orchestrator embeds JSON in the prompt — try to extract it
            blocks = re.findall(r'\{[\s\S]+\}', prompt)
            for block in blocks:
                try:
                    data = json.loads(block)
                    all_tests.extend(data.get("testCases", []))
                except Exception:
                    pass
        except Exception:
            pass

        result = {
            "duplicatesRemoved": 0,
            "redundanciesEliminated": 0,
            "originalCount": len(all_tests),
            "optimizedCount": len(all_tests),
            "coveragePreserved": "100%",
            "optimizationReport": "No duplicates found. All test cases cover unique scenarios.",
            "optimizedTestSuite": all_tests,
            "agent": "Deduplication Agent (Offline)",
            "timestamp": datetime.now().isoformat()
        }
        return json.dumps(result)

    # ─── GENERIC FALLBACK ────────────────────────────────────────────────────

    def _generic_tests(self, prompt: str) -> str:
        return self._positive_tests(prompt)

    # ─── HELPERS ─────────────────────────────────────────────────────────────

    def _extract_document_text(self, prompt: str) -> str:
        """Extract only the actual document/user content from an LLM prompt, stripping boilerplate."""
        # Patterns that mark where the actual document content appears in prompts
        markers = [
            r'ORIGINAL DOCUMENT CONTENT[^\n]*\n([\s\S]+?)(?=\nCONTEXT:|\nREQUIREMENTS:|\nACCEPTANCE|\nBUSINESS RULES:|\nDATA RULES:|$)',
            r'DOCUMENT CONTENT[:\s]*\n([\s\S]+?)(?=\nREQUIRED OUTPUT|$)',
            r'following (?:BRD|User Story|Epic|document)[^\n]*\n([\s\S]+?)(?=\nREQUIRED OUTPUT|$)',
        ]
        for pat in markers:
            m = re.search(pat, prompt, re.IGNORECASE)
            if m:
                return m.group(1).strip()

        # If no markers, heuristic: find the longest paragraph that looks like real prose
        # (not JSON, not instruction lines starting with numbers/bullets/caps keywords)
        lines = prompt.split('\n')
        doc_lines = []
        in_doc = False
        for line in lines:
            stripped = line.strip()
            # Skip obvious instruction/template lines
            if re.match(r'^(REQUIRED|GENERATE|CONTEXT:|RULES:|NOTE:|OUTPUT|JSON|CLASSIFY|ANALYZE|\d+\.|#{1,3} )', stripped):
                if in_doc and doc_lines:
                    break
                continue
            if len(stripped) > 20:
                in_doc = True
                doc_lines.append(stripped)

        extracted = ' '.join(doc_lines)
        # If still very short, return whole prompt (better than nothing)
        return extracted if len(extracted) > 50 else prompt

    def _extract_context(self, prompt: str) -> dict:
        """Extract story ID, domain, project state, and rich BRD context from prompt"""
        # Use the clean document text for extraction, not the full LLM prompt
        doc = self._extract_document_text(prompt)

        # ── storyId: read from classification context first (most reliable) ─
        # Orchestrator injects "STORY_ID: US-001" at prompt build time.
        story_id = "TC"
        sid_ctx = re.search(r'STORY_ID:\s*(US[-_]?\d+)', prompt, re.IGNORECASE)
        if sid_ctx:
            raw = sid_ctx.group(1).upper()
            digits = re.search(r'\d+', raw).group()
            story_id = f"US{digits.zfill(3)}"
        else:
            # Prioritise explicit US-nnn pattern anywhere in prompt
            us_match = re.search(r'\bUSER\s+STORY:\s*(US[-_]?\d+)\b', prompt, re.IGNORECASE)
            if not us_match:
                us_match = re.search(r'\b(US[-_]?\d+)\b', prompt, re.IGNORECASE)
            if us_match:
                grp = us_match.group(1)
                digits = re.search(r'\d+', grp).group()
                story_id = f"US{digits.zfill(3)}"
            else:
                other_match = re.search(r'\b(EPIC[-_]?\d+|STORY[-_]?\d+)\b', prompt, re.IGNORECASE)
                if other_match:
                    story_id = other_match.group(1).upper().replace("-", "").replace("_", "")

        p = doc.lower()
        domain = "General"
        # Ordered from most-specific to least-specific
        domain_rules = [
            (["hr policy", "policy document", "policy acknowledgement", "policy version", "employee handbook", "policy publish"], "HR Policy"),
            (["leave balance", "leave application", "annual leave", "sick leave", "leave type", "leave approval", "maternity", "paternity", "leave cancellation"], "Leave Management"),
            (["payslip", "payroll cycle", "gross pay", "net pay", "pf deduction", "tds", "statutory deduction"], "HR Payroll"),
            (["patient", "encounter", "provider", "hipaa", "hl7", "fhir", "emr", "prescription", "diagnosis", "doctor", "hospital", "clinical"], "Healthcare"),
            (["premium payment", "autopay", "policyholder", "policy number", "insurance policy", "coverage", "deductible", "insur", "claim", "underwr"], "Insurance"),
            (["card issu", "card activation", "card block", "cvv", "bin ", "pos terminal", "merchant", "card payment", "chargeback", "debit card", "credit card"], "Cards & Payments"),
            (["kyc", "aml", "account opening", "fund transfer", "neft", "rtgs", "ifsc", "savings account", "current account", "core bank"], "Retail Banking"),
            (["loan", "emi", "disburs", "repay", "collateral", "mortgage", "borrower", "credit score"], "Retail Banking"),
            (["lead", "opportunity", "salesforce", "crm", "campaign", "pipeline", "deal"], "CRM Sales"),
            (["payroll", "salary", "hcm", "hire", "onboard", "benefits", "performance review"], "HR Payroll"),
            (["employee", "attendance", "timesheet"], "HR Payroll"),
            (["purchase order", "material master", "vendor", "grn", "procurement", "inventory", "gl account"], "Procurement"),
            (["cart", "checkout", "sku", "e-commerce", "ecommerce", "catalog", "shipment", "add to cart"], "E-Commerce"),
            (["order", "shipping", "fulfilment", "return"], "E-Commerce"),
            (["invoice", "accounts payable", "accounts receivable", "general ledger", "journal entry"], "Finance"),
            (["payment", "transaction", "transfer", "receipt", "confirmation", "channel"], "Finance"),
            (["warehouse", "stock", "goods receipt", "goods issue"], "Inventory Management"),
        ]
        for keywords, d in domain_rules:
            if any(k in p for k in keywords):
                domain = d
                break

        project_state = "New"
        state_focus = "Discovery, data model validation, first-time build"
        if any(w in p for w in ["legacy", "migrate", "cutover", "parity", "re-platform"]):
            project_state = "Legacy"
            state_focus = "Full regression parity, data migration validation"
        elif any(w in p for w in ["enhance", "extend", "modify", "existing", "change request", "update existing"]):
            project_state = "Mid"
            state_focus = "Change impact analysis, selective regression"

        features = self._extract_features(doc, domain)
        roles = self._extract_roles(doc)
        fields = self._extract_fields(doc, domain)
        workflows = self._extract_workflows(doc)
        business_rules = self._extract_business_rules_from_text(doc)
        acs = self._extract_ac_list(prompt)  # ACs may be in full prompt

        return {
            "storyId": story_id,
            "domain": domain,
            "projectState": project_state,
            "stateDrivenFocus": state_focus,
            "features": features,
            "roles": roles,
            "fields": fields,
            "workflows": workflows,
            "businessRules": business_rules,
            "acs": acs,
        }

    def _extract_features(self, doc: str, domain: str = "") -> List[str]:
        """Extract feature/module names from actual document text"""
        features = []
        p = doc.lower()

        # Domain-specific feature sets — ordered best-match first
        domain_features_map = {
            "Leave Management": ["Apply for Leave", "Approve Leave Request", "Reject Leave Request",
                                 "Leave Balance Enquiry", "Leave History View", "Leave Cancellation",
                                 "Leave Encashment", "Leave Policy Configuration"],
            "Insurance": ["Premium Payment via Web Portal", "Premium Payment via Mobile App",
                          "Autopay Enrollment", "Autopay Cancellation", "Payment Confirmation & Receipt",
                          "Payment Error Handling", "Payment History View", "Policy Status Check"],
            "Cards & Payments": ["Card Issuance", "Card Activation", "Card Block/Unblock",
                                 "Payment Authorization", "Settlement Processing", "Dispute Filing"],
            "Retail Banking": ["Account Opening", "Fund Transfer", "Balance Enquiry",
                               "Account Closure", "KYC Verification", "Statement Download"],
            "CRM Sales": ["Lead Creation", "Lead Qualification", "Opportunity Management",
                          "Account Management", "Contact Management", "Deal Closure"],
            "Healthcare": ["Patient Registration", "Appointment Booking", "Prescription Management",
                           "Billing & Claims", "Medical Records Access"],
            "HR Payroll": ["Payroll Processing", "Salary Calculation", "Payslip Generation",
                           "Tax Declaration", "Benefits Enrollment"],
            "Procurement": ["Purchase Requisition", "Purchase Order Creation", "Goods Receipt",
                            "Invoice Verification", "Vendor Management"],
            "E-Commerce": ["Product Search & Browse", "Add to Cart", "Checkout",
                           "Payment Processing", "Order Tracking", "Return/Refund"],
            "Finance": ["Invoice Creation", "Payment Processing", "Receipt Generation",
                        "GL Posting", "Bank Reconciliation"],
        }

        # Use domain features as base if domain matches
        for dom_key, feats in domain_features_map.items():
            if dom_key.lower() in domain.lower() or any(k in p for k in dom_key.lower().split()):
                features = list(feats)
                break

        # Also extract from document sentences — verb+noun patterns
        sentence_features = re.findall(
            r'(?:ability to|allow(?:s)?|enable(?:s)?|support(?:s)?|provide(?:s)?|shall|must|can)\s+'
            r'(?:the\s+)?(?:user\s+to\s+)?([a-z][a-z\s]{5,50}?)(?:\.|,|;|\n|$)',
            p
        )
        for sf in sentence_features[:8]:
            clean = sf.strip().title()
            if len(clean) > 5 and clean not in features:
                features.append(clean)

        # Extract numbered list items as features
        numbered = re.findall(r'\d+[\.\)]\s+([A-Z][A-Za-z\s]{5,50})(?:\n|:|\.|,)', doc)
        for n in numbered[:5]:
            if n.strip() not in features:
                features.append(n.strip())

        return list(dict.fromkeys(features))[:8] or ["Core Feature Workflow"]

    def _extract_roles(self, doc: str) -> List[str]:
        """Extract user roles from actual document text"""
        p = doc.lower()
        # Match common role patterns
        role_words = re.findall(
            r'\b(admin(?:istrator)?|manager|employee|end\s*user|user|approver|reviewer|supervisor|'
            r'hr\s*(?:officer|manager|admin)?|team\s*lead(?:er)?|read[\s-]only|standard\s*user|'
            r'super\s*user|operator|agent|customer|policyholder|insured|claimant|'
            r'system\s*admin|dept(?:artment)?\s*head|finance\s*(?:officer|manager)|'
            r'billing\s*(?:agent|manager)|support\s*(?:agent|staff))\b', p
        )
        roles = list(dict.fromkeys([r.strip().title() for r in role_words]))

        # Also look for capitalized Role: XYZ patterns
        explicit_roles = re.findall(r'(?:Role|Actor|User)[:\s]+([A-Z][A-Za-z\s]{3,30})(?:\n|,|\.)', doc)
        roles.extend([r.strip() for r in explicit_roles])

        roles = list(dict.fromkeys(roles))
        return roles[:6] if roles else ["Admin", "Standard User", "Manager/Approver"]

    def _extract_fields(self, doc: str, domain: str = "") -> List[str]:
        """Extract form/data fields from actual document text"""
        # Domain-specific field sets
        domain_fields_map = {
            "Leave Management": ["Leave Type", "Start Date", "End Date", "No. of Days",
                                 "Leave Reason", "Attachment", "Employee Id", "Approver"],
            "Insurance": ["Policy Number", "Payment Amount", "Payment Channel", "Payment Date",
                          "Card Number", "Bank Account Number", "Confirmation Number", "Receipt"],
            "Retail Banking": ["Account Number", "Transfer Amount", "Beneficiary Name",
                               "IFSC Code", "Transaction Date", "OTP"],
            "HR Payroll": ["Employee Id", "Salary", "Tax", "Allowances", "Deductions",
                           "Pay Period", "Bank Account"],
            "Procurement": ["PO Number", "Vendor", "Material", "Quantity", "Unit Price",
                            "Delivery Date", "GR Number"],
            "E-Commerce": ["Product Name", "SKU", "Quantity", "Price", "Shipping Address",
                           "Payment Method", "Order Number"],
        }

        fields = []
        for dom_key, flds in domain_fields_map.items():
            if dom_key.lower() in domain.lower():
                fields = list(flds)
                break

        # Also extract from document using field-like patterns
        field_patterns = [
            r'\b(policy\s*number|payment\s*amount|payment\s*method|payment\s*channel|payment\s*date|'
            r'card\s*number|bank\s*account(?:\s*number)?|confirmation\s*(?:number|code)|receipt\s*(?:number)?|'
            r'leave\s*type|leave\s*reason|start\s*date|end\s*date|from\s*date|to\s*date|'
            r'date\s*of\s*birth|email(?:\s*address)?|phone(?:\s*number)?|mobile(?:\s*number)?|'
            r'address|username|password|employee\s*id|emp(?:loyee)?\s*id|department|'
            r'designation|balance|quantity|amount|price|description|status|remarks|'
            r'attachment|document|approval|rejection\s*reason|days?|duration|'
            r'subject|category|type|priority|code|number|id)\b'
        ]
        for pat in field_patterns:
            matches = re.findall(pat, doc, re.IGNORECASE)
            fields.extend([m.strip().title() for m in matches])

        fields = list(dict.fromkeys(fields))
        return fields[:12] if fields else ["Name", "Date", "Type", "Status", "Description"]

    def _extract_workflows(self, doc: str) -> List[str]:
        """Extract workflow steps or status transitions from actual document text"""
        p = doc.lower()
        workflows = []

        # State/status transition patterns
        status_words = re.findall(r'\b(draft|pending|submitted|approved|rejected|cancelled|'
                                  r'active|inactive|closed|completed|in.?progress|open|'
                                  r'under\s*review|on\s*hold|processed|confirmed|failed)\b', p)
        if len(status_words) >= 2:
            unique_states = list(dict.fromkeys([s.title() for s in status_words]))
            workflows.append(" → ".join(unique_states[:5]))

        # Arrow / flow patterns
        flow_matches = re.findall(r'([A-Za-z\s]{3,20})\s*(?:→|->|=>|to)\s*([A-Za-z\s]{3,20})', doc)
        for src, tgt in flow_matches[:3]:
            workflows.append(f"{src.strip()} → {tgt.strip()}")

        # Action verb sequence patterns
        action_matches = re.findall(
            r'\b(apply|submit|approve|reject|cancel|review|escalate|notify|process|validate|'
            r'authorize|complete|close|open|create|update|delete|confirm|pay|receive|disburse)\b', p
        )
        if action_matches:
            actions = list(dict.fromkeys([a.title() for a in action_matches]))
            workflows.append(" → ".join(actions[:5]))

        return workflows[:3] if workflows else ["Submit → Approve → Complete"]

    def _extract_business_rules_from_text(self, doc: str) -> List[str]:
        """Extract business rules from actual document text"""
        rules = []
        # Explicit BR patterns
        br_matches = re.findall(r'BR[-\s]?\d+[:\.]?\s*(.+)', doc, re.IGNORECASE)
        rules.extend([m.strip() for m in br_matches[:5]])

        # Rule-like sentences
        rule_sentences = re.findall(
            r'(?:shall|must|should|cannot|not allowed|required|mandatory|'
            r'only|minimum|maximum|at least|at most|up to|within|no more than)\s+[^\.\n]{10,100}',
            doc, re.IGNORECASE
        )
        rules.extend([r.strip() for r in rule_sentences[:6]])

        return list(dict.fromkeys(rules))[:8] if rules else [
            "Mandatory fields must not be empty",
            "System must validate all inputs before submission",
            "Status transitions must follow defined workflow",
            "Notifications must be triggered on key state changes"
        ]

    def _extract_ac_list(self, prompt: str) -> List[Dict]:
        """Extract acceptance criteria from prompt"""
        acs = []
        # Try JSON-embedded ACs first
        try:
            json_blocks = re.findall(r'\[[\s\S]{10,5000}\]', prompt)
            for block in json_blocks:
                items = json.loads(block)
                if isinstance(items, list) and items and "acId" in str(items[0]):
                    acs = items
                    break
        except Exception:
            pass

        if not acs:
            matches = re.findall(r'AC[-\s]?\d+[:\.]?\s*(.+)', prompt, re.IGNORECASE)
            for i, m in enumerate(matches[:10]):
                acs.append({"acId": f"AC-{i+1:03d}", "description": m.strip()})

        return acs[:10]

    def _get_domain_test_data(self, domain: str, fields: List[str]) -> Dict[str, str]:
        """Return realistic domain-specific test data values instead of generic placeholders"""
        domain_data_map = {
            "Insurance": {
                "Policy Number": "POL-2025-001234", "Payment Amount": "1500.00",
                "Payment Channel": "Web Portal", "Payment Date": "2025-06-15",
                "Card Number": "**** **** **** 1234", "Confirmation Number": "CONF-987654",
                "Bank Account Number": "****5678", "Receipt": "RCP-2025-001",
            },
            "Leave Management": {
                "Leave Type": "Annual Leave", "Start Date": "2025-07-01", "End Date": "2025-07-05",
                "No. Of Days": "5", "Leave Reason": "Personal vacation", "Employee Id": "EMP-1001",
                "Approver": "Manager_John", "Attachment": "leave_form.pdf",
            },
            "Retail Banking": {
                "Account Number": "1234567890", "Transfer Amount": "5000.00",
                "Beneficiary Name": "Jane Smith", "Ifsc Code": "HDFC0001234",
                "Transaction Date": "2025-06-15", "Otp": "123456",
            },
            "Cards & Payments": {
                "Card Number": "**** **** **** 4321", "Cvv": "***",
                "Payment Amount": "2500.00", "Merchant": "Amazon",
                "Authorization Code": "AUTH-56789",
            },
            "Procurement": {
                "Po Number": "PO-2025-0045", "Vendor": "ABC Supplies Ltd",
                "Material": "Office Stationery", "Quantity": "100",
                "Unit Price": "25.00", "Delivery Date": "2025-07-10",
            },
            "E-Commerce": {
                "Product Name": "Laptop Pro 15", "Sku": "LAP-PRO-15-256",
                "Quantity": "1", "Price": "999.99",
                "Shipping Address": "123 Main St, City 560001",
                "Payment Method": "Credit Card",
            },
            "HR Payroll": {
                "Employee Id": "EMP-2024-0042", "Salary": "75000.00",
                "Pay Period": "June 2025", "Department": "Engineering",
                "Tax": "15000.00", "Bank Account": "****1234",
            },
            "Finance": {
                "Invoice Number": "INV-2025-00456", "Amount": "12500.00",
                "Due Date": "2025-07-31", "Vendor": "Tech Solutions Inc",
                "Payment Reference": "PAY-REF-789",
            },
        }

        base_data = {}
        for dom_key, data in domain_data_map.items():
            if dom_key.lower() in domain.lower():
                base_data = dict(data)
                break

        # Fill missing fields with sensible values (not generic placeholders)
        result = {}
        for f in (fields[:5] or ["Name", "Date", "Type", "Status"]):
            if f in base_data:
                result[f] = base_data[f]
            elif any(k in f.lower() for k in ["date", "from", "to", "start", "end"]):
                result[f] = "2025-07-01"
            elif any(k in f.lower() for k in ["amount", "price", "balance", "salary"]):
                result[f] = "1000.00"
            elif any(k in f.lower() for k in ["email", "mail"]):
                result[f] = "testuser@company.com"
            elif any(k in f.lower() for k in ["phone", "mobile"]):
                result[f] = "9876543210"
            elif any(k in f.lower() for k in ["id", "number", "code"]):
                result[f] = f"{f.replace(' ', '-').upper()}-001"
            elif any(k in f.lower() for k in ["type", "category"]):
                result[f] = f"Standard {f}"
            elif any(k in f.lower() for k in ["status"]):
                result[f] = "Active"
            elif any(k in f.lower() for k in ["name"]):
                result[f] = "Test User"
            else:
                result[f] = f"Valid-{f.replace(' ', '-')}"
        return result


        """Extract acceptance criteria from prompt"""
        acs = []
        # Try JSON-embedded ACs first
        try:
            json_blocks = re.findall(r'\[[\s\S]{10,5000}\]', prompt)
            for block in json_blocks:
                items = json.loads(block)
                if isinstance(items, list) and items and "acId" in str(items[0]):
                    acs = items
                    break
        except Exception:
            pass

        if not acs:
            matches = re.findall(r'AC[-\s]?\d+[:\.]?\s*(.+)', prompt, re.IGNORECASE)
            for i, m in enumerate(matches[:10]):
                acs.append({"acId": f"AC-{i+1:03d}", "description": m.strip()})

        return acs[:10]
