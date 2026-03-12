"""
Domain & Requirements Analysis Agent
Extracts business rules, roles, data rules, and converts to testable ACs
"""
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
import json
import re

class DomainAnalysisAgent(BaseAgent):
    """Agent for analyzing domain and extracting requirements"""
    
    def __init__(self, config: Dict[str, Any], llm_client: Any):
        super().__init__(config, llm_client)
        self.agent_name = "Domain Analysis Agent"
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute domain analysis"""
        self.log_start()
        
        try:
            document_content = input_data.get("document_content", "")
            classification = input_data.get("classification", {})
            
            # Build analysis prompt
            system_prompt = self._get_system_prompt()
            user_prompt = self._build_analysis_prompt(document_content, classification)
            
            # Call LLM
            self.logger.info("Analyzing domain and extracting requirements...")
            response = self.call_llm(user_prompt, system_prompt, temperature=0.4)
            
            # Parse response
            analysis_data = self._parse_analysis_response(response)
            
            # Validate output
            if not self.validate_output(analysis_data):
                raise ValueError("Invalid analysis output")
            
            self.log_end()
            return analysis_data
            
        except Exception as e:
            self.logger.error(f"Domain analysis failed: {str(e)}")
            raise
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for domain analysis"""
        return """You are an expert Business Analyst specializing in requirement extraction and structuring.

Your task is to:
1. Extract all testable requirements from documents
2. Identify business rules and validation logic
3. Extract roles, permissions, and access controls
4. Identify data rules (mandatory fields, formats, constraints)
5. Infer implicit validations from domain context
6. Convert vague requirements into specific, testable Acceptance Criteria

Be thorough and precise. Every requirement must be testable."""
    
    def _build_analysis_prompt(self, content: str, classification: Dict) -> str:
        """Build analysis prompt"""
        domain = classification.get('domain', 'General')
        app_type = classification.get('applicationType', 'Unknown')
        
        return f"""Analyze the following document and extract structured requirements:

DOMAIN: {domain}
APPLICATION TYPE: {app_type}

DOCUMENT CONTENT:
{content}

REQUIRED OUTPUT (JSON):
{{
  "requirements": [
    {{
      "reqId": "REQ001",
      "title": "Requirement title",
      "description": "Detailed description",
      "type": "Functional | Non-Functional",
      "priority": "High | Medium | Low",
      "category": "FUNC | API | ETL | NF"
    }}
  ],
  "acceptanceCriteria": [
    {{
      "acId": "AC-001",
      "reqId": "REQ001",
      "description": "Testable criterion",
      "testable": true
    }}
  ],
  "businessRules": [
    {{
      "ruleId": "BR-001",
      "description": "Business rule description",
      "type": "Validation | Calculation | Workflow | Authorization"
    }}
  ],
  "roles": [
    {{
      "roleName": "Admin",
      "permissions": ["create", "read", "update", "delete"],
      "restrictions": ["cannot delete own account"]
    }}
  ],
  "dataRules": [
    {{
      "fieldName": "email",
      "mandatory": true,
      "format": "email format",
      "maxLength": 255,
      "validations": ["unique", "valid email format"]
    }}
  ],
  "implicitValidations": [
    "Age must be 18+ (inferred from 'adult customer')",
    "SSN required for US residents (inferred from regulatory context)"
  ],
  "integrationPoints": [
    {{
      "system": "Payment Gateway",
      "type": "REST API",
      "operations": ["authorize", "capture", "refund"]
    }}
  ]
}}

EXTRACTION RULES:
1. Every requirement MUST have at least one testable AC
2. Extract all business rules explicitly mentioned or implied
3. Identify ALL user roles and their permissions
4. For each data field, extract: mandatory status, format, validations
5. Infer implicit validations from domain knowledge
6. If document lacks explicit ACs, create them from requirements

Analyze thoroughly and provide complete structured output."""
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured data"""
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            
            analysis = json.loads(json_str)
            
            # Add metadata
            analysis["agent"] = self.agent_name
            analysis["timestamp"] = self.start_time.isoformat()
            analysis["totalRequirements"] = len(analysis.get("requirements", []))
            analysis["totalACs"] = len(analysis.get("acceptanceCriteria", []))
            analysis["totalBusinessRules"] = len(analysis.get("businessRules", []))
            
            return analysis
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {str(e)}")
            self.logger.debug(f"Response: {response}")
            raise
