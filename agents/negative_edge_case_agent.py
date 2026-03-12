"""
Negative & Edge Case Generation Agent
Generates negative scenarios, boundary conditions, and edge cases
"""
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
import json

class NegativeEdgeCaseAgent(BaseAgent):
    """Agent for generating negative and edge case test cases"""
    
    def __init__(self, config: Dict[str, Any], llm_client: Any):
        super().__init__(config, llm_client)
        self.agent_name = "Negative & Edge Case Agent"
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute negative/edge case test generation"""
        self.log_start()
        
        try:
            classification = input_data.get("classification", {})
            domain_analysis = input_data.get("domain_analysis", {})
            document_content = input_data.get("document_content", "")
            
            # Build generation prompt
            system_prompt = self._get_system_prompt()
            user_prompt = self._build_generation_prompt(classification, domain_analysis, document_content)
            
            # Call LLM
            self.logger.info("Generating negative and edge case test cases...")
            response = self.call_llm(user_prompt, system_prompt, temperature=0.7)
            
            # Parse response
            test_cases = self._parse_test_cases_response(response)
            
            # Validate output
            if not self.validate_output(test_cases):
                raise ValueError("Invalid test cases output")
            
            self.log_end()
            return test_cases
            
        except Exception as e:
            self.logger.error(f"Negative/edge case generation failed: {str(e)}")
            raise
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for negative/edge case generation"""
        return """You are an expert QA Test Designer specializing in negative testing and edge case generation.

Your task is to create comprehensive negative and edge case test cases using advanced test design techniques:

**Test Design Techniques to Apply:**
1. **Boundary Value Analysis (BVA)**: Test min-1, min, min+1, max-1, max, max+1
2. **Equivalence Partitioning**: Test invalid input classes
3. **Error Guessing**: Anticipate common error scenarios
4. **Pairwise/Combinatorial**: Test invalid parameter combinations
5. **State Transition**: Test invalid state transitions
6. **Decision Tables**: Test error conditions

**Negative Test Scenarios:**
- Invalid input formats
- Missing mandatory fields
- Field length violations (too short, too long)
- Data type mismatches
- Constraint violations
- Unauthorized access attempts
- Concurrent operation conflicts
- Special characters and injection attempts
- Null, empty, and whitespace-only inputs
- Unicode and internationalization edge cases

Generate detailed test cases with specific invalid inputs and expected error responses."""
    
    def _build_generation_prompt(self, classification: Dict, domain_analysis: Dict, document_content: str = "") -> str:
        """Build test generation prompt"""
        domain = classification.get('domain', '')
        project_state = classification.get('projectState', 'New')
        state_focus = classification.get('stateDrivenFocus', '')
        
        requirements = domain_analysis.get('requirements', [])
        acs = domain_analysis.get('acceptanceCriteria', [])
        data_rules = domain_analysis.get('dataRules', [])
        business_rules = domain_analysis.get('businessRules', [])
        
        doc_section = f"""\nORIGINAL DOCUMENT CONTENT (extract specific fields, rules, channels, values from this):\n{document_content[:3000]}\n""" if document_content else ""
        
        return f"""Generate NEGATIVE and EDGE CASE test cases for the following requirements:{doc_section}
CONTEXT:
- Domain: {domain}
- Project State: {project_state}
- Focus: {state_focus}

REQUIREMENTS:
{json.dumps(requirements, indent=2)}

ACCEPTANCE CRITERIA:
{json.dumps(acs, indent=2)}

DATA RULES:
{json.dumps(data_rules, indent=2)}

BUSINESS RULES:
{json.dumps(business_rules, indent=2)}

REQUIRED OUTPUT (JSON array of test cases):
{{
  "testCases": [
    {{
      "testCaseId": "<ReqID>_FUNC_NEG_001",
      "title": "Descriptive negative test scenario",
      "category": "FUNC | API | ETL",
      "priority": "P1 | P2 | P3",
      "automation": "Yes | Maybe | No",
      "domain": "{domain}",
      "projectState": "{project_state}",
      "stateDrivenFocus": "{state_focus}",
      "acMapped": "AC-001",
      "testDesignTechnique": "BVA | EP | Error Guessing | Pairwise | State Transition",
      "preconditions": ["Specific prerequisite"],
      "testData": {{
        "field1": "INVALID value with explanation",
        "field2": "boundary value (max+1)"
      }},
      "steps": [
        "Detailed step 1",
        "Detailed step 2"
      ],
      "expectedResults": [
        "Error message: 'specific error text'",
        "HTTP Status: 400 Bad Request",
        "Field validation error displayed"
      ],
      "traceability": "REQ001/AC-001"
    }}
  ]
}}

GENERATION RULES:

1. **Boundary Value Analysis (BVA)** - For each numeric/length field:
   - Test min-1 (just below minimum)
   - Test min (exact minimum)
   - Test min+1 (just above minimum)
   - Test max-1 (just below maximum)
   - Test max (exact maximum)
   - Test max+1 (just above maximum)

2. **Invalid Input Classes** (Equivalence Partitioning):
   - Wrong data type (string for number, number for string)
   - Invalid format (invalid email, phone, date)
   - Special characters where not allowed
   - SQL injection attempts: ' OR '1'='1, <script>alert()</script>
   - Path traversal: ../../etc/passwd
   - Null bytes: %00
   - Unicode: emoji, RTL characters, zero-width characters

3. **Missing/Empty Values**:
   - Mandatory field missing
   - Empty string ""
   - Whitespace only "   "
   - Null value

4. **Business Rule Violations**:
   - Violate calculation rules
   - Break workflow state transitions
   - Violate authorization rules
   - Exceed business limits

5. **Concurrent/Race Conditions**:
   - Simultaneous updates to same record
   - Delete while in use
   - Duplicate submission

6. **API-Specific Negative Tests**:
   - 400 Bad Request (invalid payload)
   - 401 Unauthorized (missing/invalid token)
   - 403 Forbidden (insufficient permissions)
   - 404 Not Found (non-existent resource)
   - 409 Conflict (duplicate/constraint violation)
   - 422 Unprocessable Entity (validation error)

7. **Priority Guidelines**:
   - P1: Critical security vulnerabilities, data corruption risks
   - P2: Important validation failures, error handling
   - P3: Edge cases with low probability

Generate 3-5 negative/edge tests per AC, covering different techniques."""
    
    def _parse_test_cases_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into test cases"""
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            
            test_data = json.loads(json_str)
            
            # Add metadata
            test_data["agent"] = self.agent_name
            test_data["timestamp"] = self.start_time.isoformat()
            test_data["totalTestCases"] = len(test_data.get("testCases", []))
            test_data["testType"] = "Negative & Edge Case"
            
            # Count by technique
            techniques = {}
            for tc in test_data.get("testCases", []):
                technique = tc.get("testDesignTechnique", "Unknown")
                techniques[technique] = techniques.get(technique, 0) + 1
            test_data["techniqueBreakdown"] = techniques
            
            return test_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {str(e)}")
            self.logger.debug(f"Response: {response}")
            raise
