"""
Requirements Traceability Agent
Maps test cases to requirements and ensures coverage
"""
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
import json

class TraceabilityAgent(BaseAgent):
    """Agent for creating traceability matrix and coverage analysis"""
    
    def __init__(self, config: Dict[str, Any], llm_client: Any):
        super().__init__(config, llm_client)
        self.agent_name = "Traceability Agent"
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute traceability mapping"""
        self.log_start()
        
        try:
            domain_analysis = input_data.get("domain_analysis", {})
            positive_tests = input_data.get("positive_tests", {})
            negative_tests = input_data.get("negative_tests", {})
            security_tests = input_data.get("security_tests", {})
            
            # Combine all test cases
            all_test_cases = []
            all_test_cases.extend(positive_tests.get("testCases", []))
            all_test_cases.extend(negative_tests.get("testCases", []))
            all_test_cases.extend(security_tests.get("testCases", []))
            
            # Build traceability
            traceability_data = self._build_traceability(
                domain_analysis,
                all_test_cases
            )
            
            # Calculate coverage metrics
            coverage_metrics = self._calculate_coverage(
                domain_analysis,
                traceability_data
            )
            
            result = {
                "agent": self.agent_name,
                "timestamp": self.start_time.isoformat(),
                "traceabilityMatrix": traceability_data,
                "coverageMetrics": coverage_metrics,
                "totalTestCases": len(all_test_cases)
            }
            
            self.log_end()
            return result
            
        except Exception as e:
            self.logger.error(f"Traceability mapping failed: {str(e)}")
            raise
    
    def _build_traceability(self, domain_analysis: Dict, test_cases: List[Dict]) -> List[Dict]:
        """Build traceability matrix directly from test case metadata.
        
        Groups test cases by (storyId, acMapped) so each row in the matrix
        represents one Acceptance Criterion with all its linked test cases.
        This approach is robust regardless of how reqId / acId strings are
        formatted across different stories.
        """
        # --- index test cases by (storyId, acMapped) -----------------------
        # Key: (story_id, ac_id)  →  list of test cases
        ac_map: Dict[tuple, List[Dict]] = {}
        for tc in test_cases:
            story_id = tc.get("storyId", "")
            ac_id    = tc.get("acMapped", "")
            if not ac_id:
                # fall back: derive from traceability field  e.g. "US001_REQ001/US001_AC-001"
                trace = tc.get("traceability", "")
                ac_id = trace.split("/")[-1] if "/" in trace else trace
            key = (story_id, ac_id)
            ac_map.setdefault(key, []).append(tc)

        # --- also build a req_id lookup from traceability field  ------------
        # traceability format: "{storyId}_REQ{n}/{storyId}_AC-{n}"
        req_for_ac: Dict[tuple, str] = {}
        for tc in test_cases:
            story_id = tc.get("storyId", "")
            ac_id    = tc.get("acMapped", "")
            trace    = tc.get("traceability", "")
            if "/" in trace:
                req_part = trace.split("/")[0]   # e.g. "US001_REQ001"
            else:
                req_part = trace
            key = (story_id, ac_id)
            if key not in req_for_ac and req_part:
                req_for_ac[key] = req_part

        # --- also pull AC descriptions from domain_analysis if available ---
        acs_lookup: Dict[str, str] = {}
        for ac in domain_analysis.get("acceptanceCriteria", []):
            acs_lookup[ac.get("acId", "")] = ac.get("description", "")

        # --- pull req descriptions as fallback for ACs beyond domain range --
        req_desc_lookup: Dict[str, str] = {}
        for req in domain_analysis.get("requirements", []):
            req_desc_lookup[req.get("reqId", "")] = req.get("description", "")

        # --- build matrix rows sorted by storyId then acMapped -------------
        traceability: List[Dict] = []
        for key in sorted(ac_map.keys()):
            story_id, ac_id = key
            tcs_for_ac = ac_map[key]
            req_id = req_for_ac.get(key, f"{story_id}_REQ")

            # Resolve AC description: domain lookup → req description fallback → TC title fallback
            ac_desc = acs_lookup.get(ac_id, "")
            if not ac_desc:
                # Try req description (req_id may be "US001_REQ001" — normalise hyphens)
                req_id_norm = req_id.replace("_REQ0", "_REQ-0").replace("_REQ", "_REQ-") if "_REQ-" not in req_id else req_id
                ac_desc = req_desc_lookup.get(req_id, "") or req_desc_lookup.get(req_id_norm, "")
            if not ac_desc:
                # Use the test case title/objective as last resort
                first_tc = tcs_for_ac[0]
                ac_desc = first_tc.get("title", first_tc.get("objective", "")).strip()

            # categorize
            test_ids_by_category: Dict[str, List[str]] = {}
            for tc in tcs_for_ac:
                cat = tc.get("category", "FUNC")
                test_ids_by_category.setdefault(cat, []).append(tc.get("testCaseId", ""))

            n = len(tcs_for_ac)
            traceability.append({
                "requirementId"     : req_id,
                "requirementTitle"  : None,
                "storyId"           : story_id,
                "acId"              : ac_id,
                "acDescription"     : ac_desc,
                "testCases"         : [tc.get("testCaseId", "") for tc in tcs_for_ac],
                "testCasesByCategory": test_ids_by_category,
                "totalTests"        : n,
                "coverage"          : "Full" if n >= 3 else "Partial" if n > 0 else "None",
            })

        return traceability
    
    def _calculate_coverage(self, domain_analysis: Dict, traceability: List[Dict]) -> Dict:
        """Calculate coverage metrics"""
        total_requirements = len(domain_analysis.get("requirements", []))
        total_acs = len(domain_analysis.get("acceptanceCriteria", []))
        
        # Count coverage
        fully_covered = len([t for t in traceability if t["coverage"] == "Full"])
        partially_covered = len([t for t in traceability if t["coverage"] == "Partial"])
        not_covered = len([t for t in traceability if t["coverage"] == "None"])
        
        # Calculate ratios
        total_tests = sum(t["totalTests"] for t in traceability)
        coverage_ratio = total_tests / total_acs if total_acs > 0 else 0
        
        # Identify gaps
        gaps = [
            t for t in traceability 
            if t["coverage"] in ["None", "Partial"]
        ]
        
        return {
            "totalRequirements": total_requirements,
            "totalAcceptanceCriteria": total_acs,
            "fullyCovered": fully_covered,
            "partiallyCovered": partially_covered,
            "notCovered": not_covered,
            "coveragePercentage": round((fully_covered / total_acs * 100) if total_acs > 0 else 0, 2),
            "averageTestsPerAC": round(coverage_ratio, 2),
            "totalTestCases": total_tests,
            "coverageGaps": len(gaps),
            "gapDetails": gaps[:5]  # Top 5 gaps
        }
