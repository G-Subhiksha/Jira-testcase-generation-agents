# Enterprise Test Case Generation Multi-Agent System

## 🎯 Overview

An **AI-Powered Multi-Agent Orchestration System** that automatically generates comprehensive test suites from Business Requirements Documents (BRDs), User Stories, or Epics. The system employs 8 specialized agents working together to ensure complete test coverage with full requirements traceability, exported to professional Excel format.

## 🏗️ Architecture

### Multi-Agent Design

The system uses **8 specialized agents** orchestrated sequentially:

1. **Classification Agent** - Classifies application type, product, module, and project state
2. **Domain Analysis Agent** - Extracts requirements, business rules, and acceptance criteria
3. **Positive Test Agent** - Generates happy path test cases
4. **Negative & Edge Case Agent** - Generates boundary conditions and negative scenarios
5. **Security & NF Agent** - Generates security and non-functional test cases
6. **Traceability Agent** - Maps test cases to requirements and ensures coverage
7. **Deduplication Agent** - Removes duplicate and redundant test cases
8. **Excel Export Agent** - Generates professional Excel workbooks

```
Input (BRD/Story/Epic) → Agent 1 → Agent 2 → Agent 3 → Agent 4 → 
Agent 5 → Agent 6 → Agent 7 → Agent 8 → Output (Excel)
```

## ✨ Key Features

- ✅ **Automated Test Generation** - AI-powered test case creation from requirements
- ✅ **Multiple Input Formats** - Supports PDF, DOCX, TXT, MD, or pasted text
- ✅ **8 Specialized Agents** - Each agent handles a specific aspect of test design
- ✅ **Advanced Test Techniques** - BVA, EP, Pairwise, State Transition, Decision Tables
- ✅ **Complete Traceability** - Bidirectional mapping between requirements and test cases
- ✅ **Deduplication & Optimization** - Removes duplicate and redundant tests
- ✅ **Professional Excel Output** - Ready-to-use test case workbooks
- ✅ **Interactive CLI** - User-friendly terminal interface
- ✅ **Support for Multiple Domains** - ERP, CRM, Banking, Insurance, Healthcare, E-Commerce

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- OpenAI API key or Anthropic API key

### Installation

```bash
# Clone or navigate to the project directory
cd test_case_generation_agents

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env

# Edit .env file with your API key
# For OpenAI:
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here

# For Anthropic:
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
```

### Usage

```bash
# Run the CLI application
python main.py

# Run the Streamlit UI application
streamlit run streamlit_app.py
```

> ✅ New: `streamlit_app.py` is now included in CASEGENI_2.0 for browser-based workflow. It supports file upload, pasted requirements, project naming, and results download (Excel + JSON).

The interactive CLI will guide you through:
1. Selecting input type (BRD/Story/Epic)
2. Providing the document (file upload or paste)
3. Entering project name
4. Executing the generation process

### Example Session

```
? Select input type: BRD (Business Requirements Document)
? Select input method: Upload file (.pdf, .docx, .txt, .md)
? Enter file path: /path/to/requirements.pdf
? Enter project name: Customer_Registration

✓ Document loaded successfully
  Type: BRD
  Characters: 15,234
  Project: Customer_Registration

? Proceed with test case generation? Yes

[Agent orchestration progress...]

✓ GENERATION COMPLETE

Total Test Cases: 84
  FUNC: 36
  API: 22
  ETL: 8
  NF: 18

Requirements Covered: 24/24 (100%)
Duplicates Removed: 8

📁 Output Location:
   output/Customer_Registration_20260308_143022/

📊 Excel File:
   output/Customer_Registration_20260308_143022/test_cases.xlsx
```

## 📂 Project Structure

```
test_case_generation_agents/
├── agents/
│   ├── base_agent.py                 # Base class for all agents
│   ├── classification_agent.py       # Agent 1: Classification
│   ├── domain_analysis_agent.py      # Agent 2: Domain Analysis
│   ├── positive_test_agent.py        # Agent 3: Positive Tests
│   ├── negative_edge_case_agent.py   # Agent 4: Negative/Edge Cases
│   ├── security_nf_agent.py          # Agent 5: Security & NF Tests
│   ├── traceability_agent.py         # Agent 6: Traceability
│   ├── deduplication_agent.py        # Agent 7: Deduplication
│   └── excel_export_agent.py         # Agent 8: Excel Export
├── config/
│   └── agent_config.json             # Agent configuration
├── output/                           # Generated outputs
├── inputs/                           # Sample input files
├── logs/                             # Execution logs
├── docs/                             # Documentation
├── main.py                           # CLI application
├── orchestrator.py                   # Agent orchestration
├── llm_client.py                     # LLM interface
├── document_parser.py                # Document parsing
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variables template
└── README.md                         # This file
```

## 📊 Output Files

Each execution creates a timestamped folder with:

```
output/Project_Name_20260308_143022/
├── test_cases.xlsx                   # Main Excel workbook
│   ├── Sheet 1: Test Cases
│   ├── Sheet 2: Traceability Matrix
│   ├── Sheet 3: Coverage Summary
│   └── Sheet 4: Execution Tracker
├── agent_outputs/                    # Individual agent outputs
│   ├── classification_metadata.json
│   ├── domain_analysis.json
│   ├── positive_test_cases.json
│   ├── negative_edge_test_cases.json
│   ├── security_nf_test_cases.json
│   ├── traceability_matrix.json
│   ├── optimized_test_suite.json
│   └── execution_summary.json
└── execution_log.txt                 # Detailed log
```

## 🎨 Test Case Structure

Each generated test case includes:

```
TestCaseID: REQ001_FUNC_001
Title: Create Customer with Valid Data - Happy Path
Category: FUNC | API | ETL | NF
Priority: P1 | P2 | P3 | P4
Automation: Yes | Maybe | No
Domain: Banking
ProjectState: New | Mid | Legacy
StateDrivenFocus: Discovery, data model validation
AC Mapped: AC-001
Preconditions:
  - User logged in with 'Admin' role
  - Database is empty
Test Data:
  - firstName: "John"
  - lastName: "Doe"
  - email: "john.doe@example.com"
Steps:
  1. Navigate to customer creation page
  2. Enter customer details
  3. Click 'Create' button
Expected Results:
  - Customer created with status 'Active'
  - Success message displayed
  - Customer appears in customer list
Traceability: REQ001/AC-001
```

## 🧪 Test Design Techniques

The system applies industry-standard test design techniques:

- **Equivalence Partitioning (EP)** - Valid and invalid input classes
- **Boundary Value Analysis (BVA)** - Min, max, min-1, max+1
- **Pairwise Testing** - Combinatorial parameter coverage
- **State Transition** - Valid and invalid state changes
- **Decision Tables** - Complex business logic
- **Error Guessing** - Experience-based scenarios

## 🔒 Security Testing

Security tests aligned with OWASP Top 10:

- A01: Broken Access Control
- A02: Cryptographic Failures
- A03: Injection (SQL, XSS, etc.)
- A04-A10: Additional security risks

## 📈 Coverage Metrics

The system provides comprehensive coverage metrics:

- **Total Requirements** - Number of requirements analyzed
- **Total Test Cases** - Generated test cases
- **Coverage Ratio** - Tests per requirement
- **Coverage Percentage** - % of requirements fully covered
- **Category Breakdown** - FUNC, API, ETL, NF distribution
- **Priority Breakdown** - P1, P2, P3, P4 distribution

## 🛠️ Configuration

Customize agent behavior in `config/agent_config.json`:

```json
{
  "agents": {
    "classification_agent": {
      "enabled": true,
      "sequence": 1
    },
    ...
  },
  "settings": {
    "max_retries": 3,
    "timeout_seconds": 300,
    "log_level": "INFO"
  }
}
```

## 🎓 Supported Domains

- **ERP** - SAP, Oracle, Microsoft Dynamics
- **CRM** - Salesforce, HubSpot, Dynamics 365
- **Core Banking** - Temenos, Finacle, FIS
- **Cards & Payments** - Card issuance, authorization
- **HCM** - Workday, SuccessFactors
- **Insurance** - Policy management, claims
- **E-Commerce** - Shopify, Magento, custom platforms
- **Healthcare** - EMR, EHR systems

## 🤝 Support & Troubleshooting

### Common Issues

**Issue**: API key not found
```bash
# Solution: Check .env file
cat .env
# Ensure OPENAI_API_KEY or ANTHROPIC_API_KEY is set
```

**Issue**: Module import errors
```bash
# Solution: Reinstall dependencies
pip install -r requirements.txt --upgrade
```

**Issue**: PDF parsing fails
```bash
# Solution: Install additional dependencies
pip install pdfplumber PyPDF2
```

## 📝 License

Proprietary - For client use only

## 👥 Authors

CaseGeni Team - Enterprise Test Automation Solutions

## 📧 Contact

For support or questions, contact: support@casegeni.com

---

**Version**: 2.0  
**Last Updated**: March 2026
