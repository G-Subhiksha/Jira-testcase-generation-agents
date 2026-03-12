"""
Security & Non-Functional Test Agent
Generates security, performance, and non-functional test cases
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent
import json

class SecurityNFAgent(BaseAgent):
    """Agent for generating security and non-functional test cases"""
    
    def __init__(self, config: Dict[str, Any], llm_client: Any):
        super().__init__(config, llm_client)
        self.agent_name = "Security & NF Agent"
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute security/NF test generation"""
        self.log_start()
        
        try:
            classification = input_data.get("classification", {})
            domain_analysis = input_data.get("domain_analysis", {})
            document_content = input_data.get("document_content", "")
            
            system_prompt = self._get_system_prompt()
            user_prompt = self._build_generation_prompt(classification, domain_analysis, document_content)
            
            self.logger.info("Generating security and non-functional test cases...")
            response = self.call_llm(user_prompt, system_prompt, temperature=0.6)
            
            test_cases = self._parse_test_cases_response(response)
            
            if not self.validate_output(test_cases):
                raise ValueError("Invalid test cases output")
            
            self.log_end()
            return test_cases
            
        except Exception as e:
            self.logger.error(f"Security/NF test generation failed: {str(e)}")
            raise
    
    def _get_system_prompt(self) -> str:
        return """You are an expert Security and Performance Test Designer.

Generate comprehensive security and non-functional test cases covering:

**SECURITY (OWASP Top 10 2021)**:
- A01 Broken Access Control
- A02 Cryptographic Failures
- A03 Injection (SQL, XSS, LDAP, etc.)
- A04 Insecure Design
- A05 Security Misconfiguration
- A06 Vulnerable Components
- A07 Auth/AuthN Failures
- A08 Data Integrity Failures
- A09 Logging Failures
- A10 Server-Side Request Forgery

**PERFORMANCE**:
- Load Testing (normal load)
- Stress Testing (beyond capacity)
- Spike Testing (sudden surge)
- Endurance Testing (sustained load)
- Scalability Testing

**OTHER NON-FUNCTIONAL**:
- Reliability/Availability
- Failover/Recovery
- Usability
- Accessibility
- Compliance"""
    
    def _build_generation_prompt(self, classification: Dict, domain_analysis: Dict, document_content: str = "") -> str:
        domain = classification.get('domain', '')
        project_state = classification.get('projectState', 'New')
        
        doc_section = f"""\nORIGINAL DOCUMENT CONTENT:\n{document_content[:2000]}\n""" if document_content else ""
        
        return f"""Generate SECURITY and NON-FUNCTIONAL test cases:{doc_section}
CONTEXT:
- Domain: {domain}
- Project State: {project_state}

REQUIREMENTS:
{json.dumps(domain_analysis.get('requirements', []), indent=2)}

INTEGRATION POINTS:
{json.dumps(domain_analysis.get('integrationPoints', []), indent=2)}

REQUIRED OUTPUT:
{{
  "testCases": [
    {{
      "testCaseId": "<ReqID>_NF_001",
      "title": "Security/Performance test description",
      "category": "NF",
      "subCategory": "Security | Performance | Reliability | Compliance",
      "priority": "P1 | P2 | P3",
      "automation": "Yes | Maybe | No",
      "domain": "{domain}",
      "projectState": "{project_state}",
      "owaspCategory": "A01-A10 (if security test)",
      "preconditions": ["Prerequisites"],
      "testData": {{}},
      "steps": ["Detailed steps"],
      "expectedResults": ["Expected outcomes"],
      "traceability": "REQ/NFR"
    }}
  ]
}}

GENERATE:
1. **Authentication/Authorization Tests** (401, 403):
   - Missing auth token
   - Expired token
   - Invalid token
   - Insufficient permissions
   - Role-based access control violations

2. **Injection Tests**:
   - SQL Injection: ' OR '1'='1
   - XSS: <script>alert('XSS')</script>
   - LDAP Injection
   - Command Injection

3. **Performance Tests**:
   - Load test: X concurrent users
   - Response time thresholds
   - Throughput requirements
   - Resource utilization limits

4. **Reliability Tests**:
   - Failover scenarios
   - Recovery time
   - Data integrity after failure

Priority P1 for critical security issues, P2 for performance baselines."""
    
    def _parse_test_cases_response(self, response: str) -> Dict[str, Any]:
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            test_data = json.loads(response[start_idx:end_idx])
            
            test_data["agent"] = self.agent_name
            test_data["timestamp"] = self.start_time.isoformat()
            test_data["totalTestCases"] = len(test_data.get("testCases", []))
            test_data["testType"] = "Security & Non-Functional"
            
            return test_data
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {str(e)}")
            raise
