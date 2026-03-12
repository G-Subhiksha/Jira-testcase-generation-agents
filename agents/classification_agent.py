"""
Application & Project Classification Agent
Classifies application type, product, module, and project state
"""
from typing import Dict, Any
from agents.base_agent import BaseAgent
import json

class ClassificationAgent(BaseAgent):
    """Agent for classifying application and project metadata"""
    
    def __init__(self, config: Dict[str, Any], llm_client: Any):
        super().__init__(config, llm_client)
        self.agent_name = "Classification Agent"
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute classification analysis"""
        self.log_start()
        
        try:
            document_content = input_data.get("document_content", "")
            document_type = input_data.get("document_type", "")
            
            # Build classification prompt
            system_prompt = self._get_system_prompt()
            user_prompt = self._build_classification_prompt(document_content, document_type)
            
            # Call LLM
            self.logger.info("Analyzing document for classification...")
            response = self.call_llm(user_prompt, system_prompt, temperature=0.3)
            
            # Parse response
            classification_data = self._parse_classification_response(response)
            
            # Validate output
            if not self.validate_output(classification_data):
                raise ValueError("Invalid classification output")
            
            self.log_end()
            return classification_data
            
        except Exception as e:
            self.logger.error(f"Classification failed: {str(e)}")
            raise
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for classification"""
        return """You are an expert Enterprise Application Classifier. 
        
Your task is to analyze requirements documents and classify:
1. Application Type (ERP, CRM, Core Banking, Cards & Payments, HCM, Insurance, E-Commerce, Healthcare, etc.)
2. Product (SAP S/4HANA, Oracle Fusion, Salesforce, Temenos T24, etc.)
3. Module (SAP_MM, SAP_FI, SFDC_SalesCloud, etc.)
4. Process Flows (canonical business processes)
5. Key Terms (entities, master data, transactions)
6. Domain (Procurement, Finance, Banking, etc.)
7. Project State (New/Greenfield, Mid/Enhancement, Legacy/Migration)

Provide output in JSON format with high accuracy."""
    
    def _build_classification_prompt(self, content: str, doc_type: str) -> str:
        """Build classification prompt"""
        return f"""Analyze the following {doc_type} and provide classification:

DOCUMENT CONTENT:
{content}

REQUIRED OUTPUT (JSON):
{{
  "applicationType": "...",
  "product": "...",
  "module": "...",
  "processFlows": ["..."],
  "terms": ["..."],
  "domain": "...",
  "projectState": "New | Mid | Legacy",
  "stateDrivenFocus": "...",
  "confidence": 0.0
}}

CLASSIFICATION RULES:
1. applicationType indicators:
   - ERP: Purchase orders, inventory, GL accounts
   - CRM: Leads, opportunities, accounts, contacts
   - Core Banking: Accounts, KYC, AML, transactions
   - Cards: Card issuance, authorization, settlement
   - HCM: Employees, payroll, benefits
   - Insurance: Policies, claims, premiums

2. projectState indicators:
   - New: "new system", "build from scratch", "initial implementation"
   - Mid: "enhance", "add feature", "extend", "modify"
   - Legacy: "migrate", "replace", "modernize", "re-platform"

Analyze carefully and provide accurate classification."""
    
    def _parse_classification_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured data"""
        try:
            # Extract JSON from response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            
            classification = json.loads(json_str)
            
            # Add metadata
            classification["agent"] = self.agent_name
            classification["timestamp"] = self.start_time.isoformat()
            
            return classification
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON: {str(e)}")
            self.logger.debug(f"Response: {response}")
            raise
