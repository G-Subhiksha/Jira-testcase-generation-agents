"""
Positive Test Case Generation Agent
Generates happy path and valid scenario test cases
"""
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
import json

class PositiveTestAgent(BaseAgent):
    """Agent for generating positive test cases"""
    
    def __init__(self, config: Dict[str, Any], llm_client: Any):
        super().__init__(config, llm_client)
        self.agent_name = "Positive Test Agent"
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute positive test generation"""
        self.log_start()
        
        try:
            classification = input_data.get("classification", {})
            domain_analysis = input_data.get("domain_analysis", {})
            document_content = input_data.get("document_content", "")
            
            # Build generation prompt
            system_prompt = self._get_system_prompt()
            user_prompt = self._build_generation_prompt(classification, domain_analysis, document_content)
            
            # Call LLM
            self.logger.info("Generating positive test cases...")
            response = self.call_llm(user_prompt, system_prompt, temperature=0.6)
            
            # Parse response
            test_cases = self._parse_test_cases_response(response)
            
            # Validate output
            if not self.validate_output(test_cases):
                raise ValueError("Invalid test cases output")
            
            self.log_end()
            return test_cases
            
        except Exception as e:
            self.logger.error(f"Positive test generation failed: {str(e)}")
            raise
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for positive test generation"""
        return """You are an expert QA Test Designer specializing in positive/happy path test case generation.

Your task is to create comprehensive positive test cases that:
1. Cover all happy path scenarios
2. Test valid inputs and expected successful outcomes
3. Verify successful state transitions
4. Test CRUD operations (Create, Read, Update, Delete) with valid data
5. Cover end-to-end business workflows
6. Apply Equivalence Partitioning for valid input classes

Generate detailed test cases with:
- Clear test case IDs
- Descriptive titles
- Specific preconditions
- Exact test data values
- Step-by-step procedures
- Measurable expected results
- Proper categorization and prioritization"""
    
    def _build_generation_prompt(self, classification: Dict, domain_analysis: Dict, document_content: str = "") -> str:
        """Build test generation prompt"""
        domain = classification.get('domain', '')
        project_state = classification.get('projectState', 'New')
        state_focus = classification.get('stateDrivenFocus', '')
        
        requirements = domain_analysis.get('requirements', [])
        acs = domain_analysis.get('acceptanceCriteria', [])
        business_rules = domain_analysis.get('businessRules', [])
        
        doc_section = f"""\nORIGINAL DOCUMENT CONTENT (use this to extract specific features, roles, fields, and values):\n{document_content[:3000]}\n""" if document_content else ""
        
        return f"""Generate POSITIVE test cases for the following requirements:{doc_section}
CONTEXT:
- Domain: {domain}
- Project State: {project_state}
- Focus: {state_focus}

REQUIREMENTS:
{json.dumps(requirements, indent=2)}

ACCEPTANCE CRITERIA:
{json.dumps(acs, indent=2)}

BUSINESS RULES:
{json.dumps(business_rules, indent=2)}

REQUIRED OUTPUT (JSON array of test cases):
{{
  "testCases": [
    {{
      "testCaseId": "<ReqID>_FUNC_001",
      "title": "Clear description of what is being tested",
      "category": "FUNC | API | ETL",
      "priority": "P1 | P2 | P3 | P4",
      "automation": "Yes | Maybe | No",
      "domain": "{domain}",
      "projectState": "{project_state}",
      "stateDrivenFocus": "{state_focus}",
      "acMapped": "AC-001",
      "preconditions": ["Specific prerequisite 1", "Specific prerequisite 2"],
      "testData": {{
        "field1": "specific value",
        "field2": "specific value"
      }},
      "steps": [
        "Detailed step 1",
        "Detailed step 2",
        "Detailed step 3"
      ],
      "expectedResults": [
        "Specific measurable outcome 1",
        "Specific measurable outcome 2"
      ],
      "traceability": "REQ001/AC-001"
    }}
  ]
}}

TEST CASE GENERATION RULES:
1. Generate 2-4 positive tests per AC/requirement
2. Focus on HAPPY PATH scenarios
3. Use VALID inputs from valid equivalence classes
4. Test successful state transitions
5. For APIs: Test successful CRUD operations (201, 200, 204)
6. For ETL: Test valid data transformations
7. Include specific test data values (not generic "valid data")
8. Priority: P1 for critical paths, P2 for important features
9. Mark stable APIs and backend tests as "Automation: Yes"
10. Mark UI-heavy tests as "Automation: Maybe"

Generate comprehensive positive test cases now."""
    
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
            test_data["testType"] = "Positive"
            
            return test_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {str(e)}")
            self.logger.debug(f"Response: {response}")
            raise
