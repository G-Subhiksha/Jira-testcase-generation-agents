# Quick Start Guide
## Test Case Generation Multi-Agent System

This guide will help you get started in 5 minutes!

---

## Prerequisites

✅ Python 3.9 or higher  
✅ OpenAI API key OR Anthropic API key  
✅ Terminal/Command Prompt access

---

## Step 1: Installation (2 minutes)

```bash
# Navigate to the project directory
cd test_case_generation_agents

# Install dependencies
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed openai-1.12.0 anthropic-0.18.0 ...
```

---

## Step 2: Configuration (1 minute)

```bash
# Copy environment template
cp .env.example .env

# Edit .env file (use your favorite editor)
nano .env  # or vi .env, or code .env
```

**Configure your API key:**

**Option A: OpenAI**
```
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4-turbo-preview
```

**Option B: Anthropic**
```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-key-here
ANTHROPIC_MODEL=claude-3-opus-20240229
```

Save and close the file.

---

## Step 3: Run the System (1 minute)

```bash
# Start the application
python main.py
```

You'll see an interactive interface:

```
╔══════════════════════════════════════════════════════════════╗
║     Enterprise Test Case Generation Multi-Agent System       ║
╚══════════════════════════════════════════════════════════════╝

? Select input type: 
  ❯ BRD (Business Requirements Document)
    User Story
    Epic
```

---

## Step 4: Try the Sample (1 minute)

### Option 1: Use Sample File

When prompted for input:

1. Select: **User Story**
2. Select: **Upload file (.pdf, .docx, .txt, .md)**
3. Enter path: `inputs/sample_user_story.md`
4. Enter project name: `Sample_Test`
5. Confirm: **Yes**

### Option 2: Paste Sample Text

1. Select: **User Story**
2. Select: **Paste text content**
3. Paste this minimal story:
```
Story: Customer can login with email and password
AC-001: User enters valid email and password, system authenticates
AC-002: User enters invalid credentials, system shows error
```
4. Press `Ctrl+D` (Mac/Linux) or `Ctrl+Z` (Windows)
5. Enter project name: `Login_Test`
6. Confirm: **Yes**

---

## Step 5: Review Output (30 seconds)

After execution completes, you'll see:

```
✓ GENERATION COMPLETE

Total Test Cases: 24
  FUNC: 12
  API: 6
  NF: 6

📁 Output Location:
   output/Sample_Test_20260308_143022/

📊 Excel File:
   output/Sample_Test_20260308_143022/test_cases.xlsx

? Open output folder? (Y/n): 
```

Press **Y** to open the output folder.

---

## What You'll Get

### Main Output: `test_cases.xlsx`

Four sheets:
1. **Test Cases** - All generated test cases
2. **Traceability Matrix** - Requirements mapping
3. **Coverage Summary** - Metrics and stats
4. **Execution Tracker** - Ready for test execution

### Additional Outputs: `agent_outputs/` folder

JSON files from each agent:
- `classification_metadata.json`
- `domain_analysis.json`
- `positive_test_cases.json`
- `negative_edge_test_cases.json`
- `security_nf_test_cases.json`
- `traceability_matrix.json`
- `optimized_test_suite.json`
- `execution_summary.json`

---

## Common Commands

### Run with Default Settings
```bash
python main.py
```

### Check Python Version
```bash
python --version
# Should show 3.9 or higher
```

### Reinstall Dependencies
```bash
pip install -r requirements.txt --upgrade
```

### View Logs
```bash
# Logs are saved in logs/ directory
cat logs/execution_*.log
```

---

## Troubleshooting

### Issue: "Module not found" error
**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: "API key not found"
**Solution:**
1. Check `.env` file exists
2. Verify API key is set correctly
3. No spaces around `=` sign
```bash
# ✅ Correct
OPENAI_API_KEY=sk-your-key

# ❌ Wrong
OPENAI_API_KEY = sk-your-key
```

### Issue: "PDF parsing failed"
**Solution:**
```bash
pip install pdfplumber PyPDF2
```

### Issue: "DOCX parsing failed"
**Solution:**
```bash
pip install python-docx
```

### Issue: Slow execution
**Reason:** LLM API calls take time (30-120 seconds total)
**Normal:** 8 agents × 10-15 seconds each = 80-120 seconds

---

## Next Steps

### 1. Try Your Own Document
- Prepare a BRD, Story, or Epic
- Run the system with your document
- Review generated test cases
- Adjust and iterate

### 2. Customize Configuration
- Edit `config/agent_config.json`
- Enable/disable specific agents
- Adjust settings

### 3. Integrate with Your Workflow
- Import Excel to test management tool
- Link to Jira/Azure DevOps
- Add to CI/CD pipeline

### 4. Train Your Team
- Share this quick start guide
- Run demo session
- Create team templates

---

## Tips for Best Results

### ✅ DO:
- Provide complete requirements with acceptance criteria
- Include business rules and validations
- Specify data formats and constraints
- Document user roles and permissions

### ❌ DON'T:
- Use vague or ambiguous requirements
- Omit acceptance criteria
- Skip business context
- Forget to specify data rules

---

## Sample Commands Reference

```bash
# Full workflow
cd test_case_generation_agents
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API key
python main.py

# Check installation
python --version
pip list | grep openai
pip list | grep anthropic

# Run with sample
python main.py
# Select: User Story
# Path: inputs/sample_user_story.md
# Project: Sample_Test

# View output
open output/Sample_Test_*/test_cases.xlsx  # macOS
start output/Sample_Test_*/test_cases.xlsx # Windows
xdg-open output/Sample_Test_*/test_cases.xlsx # Linux
```

---

## Support

### Documentation
- `README.md` - Full documentation
- `docs/CLIENT_PRESENTATION.md` - Detailed presentation
- `logs/` - Execution logs

### Help
If you encounter issues:
1. Check logs in `logs/` directory
2. Review error messages
3. Verify .env configuration
4. Contact: support@casegeni.com

---

## Success Checklist

- [x] Python 3.9+ installed
- [x] Dependencies installed (`pip install -r requirements.txt`)
- [x] API key configured in `.env`
- [x] Sample execution completed successfully
- [x] Output Excel file reviewed
- [x] Ready to process real documents

---

**Congratulations! You're all set to generate test cases! 🎉**

For questions or support, contact: support@casegeni.com
