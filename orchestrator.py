"""
Agent Orchestrator
Coordinates sequential execution of all specialized agents
"""
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from agents.classification_agent import ClassificationAgent
from agents.domain_analysis_agent import DomainAnalysisAgent
from agents.epic_decomposition_agent import EpicDecompositionAgent
from agents.positive_test_agent import PositiveTestAgent
from agents.negative_edge_case_agent import NegativeEdgeCaseAgent
from agents.security_nf_agent import SecurityNFAgent
from agents.traceability_agent import TraceabilityAgent
from agents.deduplication_agent import DeduplicationAgent
from agents.excel_export_agent import ExcelExportAgent
from agents.json_export_agent import JsonExportAgent

class AgentOrchestrator:
    """Orchestrates the execution of all test generation agents"""
    
    def __init__(self, config: Dict[str, Any], llm_client: Any):
        self.config = config
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
        # Initialize all agents
        self.agents = self._initialize_agents()
        
        # Execution state
        self.execution_state = {}
        self.start_time = None
        self.end_time = None
    
    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize all specialized agents"""
        agents = {}
        
        agent_classes = {
            "classification": ClassificationAgent,
            "domain_analysis": DomainAnalysisAgent,
            "epic_decomposition": EpicDecompositionAgent,
            "positive_test": PositiveTestAgent,
            "negative_edge": NegativeEdgeCaseAgent,
            "security_nf": SecurityNFAgent,
            "traceability": TraceabilityAgent,
            "deduplication": DeduplicationAgent,
            "excel_export": ExcelExportAgent,
            "json_export":  JsonExportAgent,
        }
        
        for agent_name, agent_class in agent_classes.items():
            agent_config = self.config.get("agents", {}).get(f"{agent_name}_agent", {})
            if agent_config.get("enabled", True):
                agents[agent_name] = agent_class(agent_config, self.llm_client)
                self.logger.info(f"Initialized {agent_name} agent")
        
        return agents
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all agents in sequence"""
        self.start_time = datetime.now()
        self.logger.info("="*80)
        self.logger.info("STARTING AGENT ORCHESTRATION")
        self.logger.info("="*80)

        try:
            output_dir = self._create_output_directory(input_data)

            # Agent 1: Classification (same for all input types)
            self.logger.info("\n[1/8] Running Classification Agent...")
            classification = self.agents["classification"].execute(input_data)
            self._save_agent_output(output_dir, "classification_metadata.json", classification)
            self.execution_state["classification"] = classification

            # ── EPIC PATH ────────────────────────────────────────────────────
            if input_data.get("document_type", "").upper() == "EPIC":
                return self._execute_epic_flow(input_data, classification, output_dir)

            # ── BRD / STORY PATH (unchanged) ─────────────────────────────────
            return self._execute_standard_flow(input_data, classification, output_dir)

        except Exception as e:
            self.logger.error(f"Orchestration failed: {str(e)}")
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # EPIC FLOW
    # ─────────────────────────────────────────────────────────────────────────

    def _execute_epic_flow(
        self, input_data: Dict[str, Any], classification: Dict, output_dir: str
    ) -> Dict[str, Any]:
        """Decompose Epic → generate tests per story → merge → export"""

        # Step 2: Decompose Epic into User Stories
        self.logger.info("\n[2/9] Running Epic Decomposition Agent...")
        decomp_input = {
            "document_content": input_data.get("document_content", ""),
            "classification": classification,
        }
        decomposition = self.agents["epic_decomposition"].execute(decomp_input)
        self._save_agent_output(output_dir, "epic_decomposition.json", decomposition)
        stories = decomposition.get("stories", [])
        self.logger.info(f"  → {len(stories)} user stories extracted")

        # Step 3–5: Generate tests for EACH story
        all_positive, all_negative, all_security = [], [], []
        story_analyses = []

        for i, story in enumerate(stories):
            story_id = story.get("storyId", f"US-{i+1:03d}")
            # Normalised prefix used inside all generated IDs: US001, US002 …
            sid_prefix = story_id.replace("-", "").replace("_", "")  # e.g. "US001"

            story_text = (
                f"STORY_ID: {story_id}\n"
                f"USER STORY: {story_id}\n"
                f"{story.get('title', '')}\n\n"
                f"{story.get('story', '')}\n\n"
                + "\n".join(
                    ac.get("description", ac) if isinstance(ac, dict) else str(ac)
                    for ac in story.get("acceptanceCriteria", [])
                )
            )

            self.logger.info(f"\n  Story {i+1}/{len(stories)}: {story_id} — {story.get('title', '')}")

            # Inject story_id into classification so _extract_context can use it
            story_classification = {**classification, "storyId": story_id}

            story_input_data = {
                "document_content": story_text,
                "document_type": "Story",
                "classification": story_classification,
            }

            # Domain analysis per story
            story_analysis = self.agents["domain_analysis"].execute(story_input_data)
            story_analysis["storyId"] = story_id
            # Re-stamp reqId / acId with correct story prefix
            self._restamp_analysis_ids(story_analysis, sid_prefix)
            story_analyses.append(story_analysis)

            test_input = {
                "classification": story_classification,
                "domain_analysis": story_analysis,
                "document_content": story_text,
                "document_type": "Story",
            }

            # Positive tests
            pos = self.agents["positive_test"].execute(test_input)
            for tc in pos.get("testCases", []):
                tc["storyId"] = story_id
                tc["storyTitle"] = story.get("title", "")
                self._restamp_tc_ids(tc, sid_prefix)
            all_positive.extend(pos.get("testCases", []))

            # Negative tests
            neg = self.agents["negative_edge"].execute(test_input)
            for tc in neg.get("testCases", []):
                tc["storyId"] = story_id
                tc["storyTitle"] = story.get("title", "")
                self._restamp_tc_ids(tc, sid_prefix)
            all_negative.extend(neg.get("testCases", []))

            # Security/NF — only once (for the first story), then reuse
            if i == 0:
                sec = self.agents["security_nf"].execute(test_input)
                for tc in sec.get("testCases", []):
                    tc["storyId"] = "EPIC"
                    tc["storyTitle"] = "Epic-level Security & NF"
                    self._restamp_tc_ids(tc, sid_prefix)  # keeps EPIC TCs tagged with first-story prefix
                all_security.extend(sec.get("testCases", []))

        # Save merged per-category outputs
        positive_tests = {"testCases": all_positive, "count": len(all_positive), "agent": "Positive Test Agent"}
        negative_tests = {"testCases": all_negative, "count": len(all_negative), "agent": "Negative & Edge Case Agent"}
        security_tests = {"testCases": all_security, "count": len(all_security), "agent": "Security & NF Agent"}

        self._save_agent_output(output_dir, "positive_test_cases.json", positive_tests)
        self._save_agent_output(output_dir, "negative_edge_test_cases.json", negative_tests)
        self._save_agent_output(output_dir, "security_nf_test_cases.json", security_tests)

        # Combined domain analysis (merge all story analyses)
        merged_domain = self._merge_story_analyses(story_analyses)
        self._save_agent_output(output_dir, "domain_analysis.json", merged_domain)

        # Traceability
        self.logger.info("\n[6/9] Running Traceability Agent...")
        traceability_input = {
            "domain_analysis": merged_domain,
            "positive_tests": positive_tests,
            "negative_tests": negative_tests,
            "security_tests": security_tests,
        }
        traceability = self.agents["traceability"].execute(traceability_input)
        self._save_agent_output(output_dir, "traceability_matrix.json", traceability)

        # Deduplication
        self.logger.info("\n[7/9] Running Deduplication Agent...")
        dedup_input = {
            "positive_tests": positive_tests,
            "negative_tests": negative_tests,
            "security_tests": security_tests,
        }
        optimized_suite = self.agents["deduplication"].execute(dedup_input)
        self._save_agent_output(output_dir, "optimized_test_suite.json", optimized_suite)

        # Excel Export — pass story grouping info
        self.logger.info("\n[8/9] Running Excel Export Agent...")
        excel_input = {
            "optimized_suite": optimized_suite,
            "traceability": traceability,
            "classification": classification,
            "decomposition": decomposition,
            "output_path": os.path.join(output_dir, "test_cases.xlsx"),
        }
        excel_result = self.agents["excel_export"].execute(excel_input)

        # JSON Export — same folder as the Excel file
        self.logger.info("\n[9/9] Running JSON Export Agent...")
        json_input = {
            "excel_path":      os.path.join(output_dir, "test_cases.xlsx"),
            "output_path":     os.path.join(output_dir, "test_cases.json"),
            "optimized_suite": optimized_suite,
            "traceability":    traceability,
            "classification":  classification,
            "decomposition":   decomposition,
        }
        json_result = self.agents["json_export"].execute(json_input)

        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        self.execution_state.update({
            "classification": classification,
            "decomposition": decomposition,
            "positive_tests": positive_tests,
            "negative_tests": negative_tests,
            "security_tests": security_tests,
            "traceability": traceability,
            "optimized_suite": optimized_suite,
            "excel_export": excel_result,
            "json_export":   json_result,
        })

        summary = self._generate_summary(output_dir, duration)
        self._save_agent_output(output_dir, "execution_summary.json", summary)
        self.logger.info(f"\nEpic flow complete — {len(stories)} stories, {len(all_positive)+len(all_negative)+len(all_security)} total test cases in {duration:.1f}s")
        return summary

    # ─────────────────────────────────────────────────────────────────────────
    # ID RE-STAMPING HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _restamp_analysis_ids(self, analysis: Dict, sid_prefix: str) -> None:
        """Replace any generic prefix (TC, REQ001, etc.) in reqId / acId with sid_prefix."""
        import re

        def fix(val: str) -> str:
            if not isinstance(val, str):
                return val
            # Replace leading token (anything before first _REQ or _AC) with sid_prefix
            val = re.sub(r'^[A-Z0-9]+(_REQ)', rf'{sid_prefix}\1', val)
            val = re.sub(r'^[A-Z0-9]+(_AC)',  rf'{sid_prefix}\1', val)
            return val

        for req in analysis.get("requirements", []):
            req["reqId"] = fix(req.get("reqId", ""))
        for ac in analysis.get("acceptanceCriteria", []):
            ac["acId"]  = fix(ac.get("acId", ""))
            ac["reqId"] = fix(ac.get("reqId", ""))

    def _restamp_tc_ids(self, tc: Dict, sid_prefix: str) -> None:
        """Replace generic prefix in testCaseId, acMapped, traceability with sid_prefix."""
        import re

        def fix(val: str) -> str:
            if not isinstance(val, str):
                return val
            # Replace leading token before _REQ / _AC / _NFR / _NF / _NEG / _FUNC / _API / _ETL
            val = re.sub(r'^[A-Z0-9]+(_(?:REQ|AC|NFR|NF|NEG|FUNC|API|ETL))', rf'{sid_prefix}\1', val)
            return val

        tc["testCaseId"]  = fix(tc.get("testCaseId", ""))
        tc["acMapped"]    = fix(tc.get("acMapped", ""))
        tc["traceability"] = fix(tc.get("traceability", ""))

    def _merge_story_analyses(self, story_analyses: list) -> Dict:
        """Merge individual story domain analyses into one combined analysis"""
        all_reqs, all_acs, all_rules, all_roles = [], [], [], []
        for sa in story_analyses:
            all_reqs.extend(sa.get("requirements", []))
            all_acs.extend(sa.get("acceptanceCriteria", []))
            all_rules.extend(sa.get("businessRules", []))
            all_roles.extend(sa.get("roles", []))
        return {
            "requirements": all_reqs,
            "acceptanceCriteria": all_acs,
            "businessRules": list({str(r): r for r in all_rules}.values()),
            "roles": list({r.get("roleName", str(r)): r for r in all_roles}.values()) if all_roles and isinstance(all_roles[0], dict) else list(dict.fromkeys(all_roles)),
            "dataRules": story_analyses[0].get("dataRules", []) if story_analyses else [],
            "implicitValidations": story_analyses[0].get("implicitValidations", []) if story_analyses else [],
            "agent": "Domain Analysis Agent (Epic Merged)",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # STANDARD FLOW (BRD / Story — unchanged logic)
    # ─────────────────────────────────────────────────────────────────────────

    def _execute_standard_flow(
        self, input_data: Dict[str, Any], classification: Dict, output_dir: str
    ) -> Dict[str, Any]:
        """Original BRD/Story flow"""

        # Agent 2: Domain Analysis
        self.logger.info("\n[2/8] Running Domain Analysis Agent...")
        input_data["classification"] = classification
        domain_analysis = self.agents["domain_analysis"].execute(input_data)
        self._save_agent_output(output_dir, "domain_analysis.json", domain_analysis)
        self.execution_state["domain_analysis"] = domain_analysis

        # Agent 3: Positive Test Generation
        self.logger.info("\n[3/8] Running Positive Test Agent...")
        test_input = {
            "classification": classification,
            "domain_analysis": domain_analysis,
            "document_content": input_data.get("document_content", ""),
            "document_type": input_data.get("document_type", "")
        }
        positive_tests = self.agents["positive_test"].execute(test_input)
        self._save_agent_output(output_dir, "positive_test_cases.json", positive_tests)
        self.execution_state["positive_tests"] = positive_tests

        # Agent 4: Negative & Edge Case Generation
        self.logger.info("\n[4/8] Running Negative & Edge Case Agent...")
        negative_tests = self.agents["negative_edge"].execute(test_input)
        self._save_agent_output(output_dir, "negative_edge_test_cases.json", negative_tests)
        self.execution_state["negative_tests"] = negative_tests

        # Agent 5: Security & NF Generation
        self.logger.info("\n[5/8] Running Security & NF Agent...")
        security_tests = self.agents["security_nf"].execute(test_input)
        self._save_agent_output(output_dir, "security_nf_test_cases.json", security_tests)
        self.execution_state["security_tests"] = security_tests

        # Agent 6: Traceability
        self.logger.info("\n[6/8] Running Traceability Agent...")
        traceability_input = {
            "domain_analysis": domain_analysis,
            "positive_tests": positive_tests,
            "negative_tests": negative_tests,
            "security_tests": security_tests
        }
        traceability = self.agents["traceability"].execute(traceability_input)
        self._save_agent_output(output_dir, "traceability_matrix.json", traceability)
        self.execution_state["traceability"] = traceability

        # Agent 7: Deduplication & Optimization
        self.logger.info("\n[7/8] Running Deduplication Agent...")
        dedup_input = {
            "positive_tests": positive_tests,
            "negative_tests": negative_tests,
            "security_tests": security_tests
        }
        optimized_suite = self.agents["deduplication"].execute(dedup_input)
        self._save_agent_output(output_dir, "optimized_test_suite.json", optimized_suite)
        self.execution_state["optimized_suite"] = optimized_suite

        # Agent 8: Excel Export
        self.logger.info("\n[8/8] Running Excel Export Agent...")
        excel_input = {
            "optimized_suite": optimized_suite,
            "traceability": traceability,
            "classification": classification,
            "output_path": os.path.join(output_dir, "test_cases.xlsx")
        }
        excel_result = self.agents["excel_export"].execute(excel_input)
        self.execution_state["excel_export"] = excel_result

        # JSON Export — same folder as the Excel file
        self.logger.info("\n[9/8] Running JSON Export Agent...")
        json_input = {
            "excel_path":      os.path.join(output_dir, "test_cases.xlsx"),
            "output_path":     os.path.join(output_dir, "test_cases.json"),
            "optimized_suite": optimized_suite,
            "traceability":    traceability,
            "classification":  classification,
            "decomposition":   {},
        }
        json_result = self.agents["json_export"].execute(json_input)
        self.execution_state["json_export"] = json_result

        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()

        # Generate execution summary
        summary = self._generate_summary(output_dir, duration)
        self._save_agent_output(output_dir, "execution_summary.json", summary)

        self.logger.info("\n" + "="*80)
        self.logger.info("AGENT ORCHESTRATION COMPLETED SUCCESSFULLY")
        self.logger.info(f"Total execution time: {duration:.2f} seconds")
        self.logger.info(f"Output directory: {output_dir}")
        self.logger.info("="*80)

        return summary

    def _create_output_directory(self, input_data: Dict[str, Any]) -> str:
        """Create output directory for this execution"""
        project_name = input_data.get("project_name", "test_generation")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output_dir = os.path.join("output", f"{project_name}_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "agent_outputs"), exist_ok=True)
        
        return output_dir
    
    def _save_agent_output(self, output_dir: str, filename: str, data: Dict[str, Any]):
        """Save agent output to file"""
        filepath = os.path.join(output_dir, "agent_outputs", filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _generate_summary(self, output_dir: str, duration: float) -> Dict[str, Any]:
        """Generate execution summary"""
        optimized_suite = self.execution_state.get("optimized_suite", {})
        traceability = self.execution_state.get("traceability", {})
        classification = self.execution_state.get("classification", {})
        
        test_cases = optimized_suite.get("optimizedTestSuite", [])
        coverage = traceability.get("coverageMetrics", {})
        
        # Count by category
        category_count = {}
        priority_count = {}
        automation_count = {}
        
        for tc in test_cases:
            cat = tc.get("category", "Unknown")
            pri = tc.get("priority", "Unknown")
            auto = tc.get("automation", "Unknown")
            
            category_count[cat] = category_count.get(cat, 0) + 1
            priority_count[pri] = priority_count.get(pri, 0) + 1
            automation_count[auto] = automation_count.get(auto, 0) + 1
        
        summary = {
            "executionTimestamp": self.start_time.isoformat(),
            "totalDuration": round(duration, 2),
            "outputDirectory": output_dir,
            "classification": {
                "applicationType": classification.get("applicationType"),
                "domain": classification.get("domain"),
                "projectState": classification.get("projectState")
            },
            "testSuiteMetrics": {
                "totalTestCases": len(test_cases),
                "byCategory": category_count,
                "byPriority": priority_count,
                "byAutomation": automation_count
            },
            "coverageMetrics": coverage,
            "optimizationMetrics": {
                "originalCount": optimized_suite.get("originalCount", 0),
                "duplicatesRemoved": optimized_suite.get("duplicatesRemoved", 0),
                "redundanciesRemoved": optimized_suite.get("redundanciesRemoved", 0),
                "reductionPercentage": optimized_suite.get("reductionPercentage", 0)
            },
            "outputFiles": {
                "excelFile":   os.path.join(output_dir, "test_cases.xlsx"),
                "jsonFile":    os.path.join(output_dir, "test_cases.json"),
                "agentOutputs": os.path.join(output_dir, "agent_outputs")
            }
        }
        
        return summary
