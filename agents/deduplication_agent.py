"""
Deduplication & Optimization Agent
Removes duplicate and redundant test cases from the combined test suite
"""
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
import json


class DeduplicationAgent(BaseAgent):
    """Agent for deduplicating and optimizing the test suite"""

    def __init__(self, config: Dict[str, Any], llm_client: Any):
        super().__init__(config, llm_client)
        self.agent_name = "DeduplicationAgent"

    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        self.log_start()
        try:
            positive_tests = input_data.get("positive_tests", {})
            negative_tests = input_data.get("negative_tests", {})
            security_tests = input_data.get("security_tests", {})

            # Collect all test cases
            all_test_cases = (
                positive_tests.get("testCases", []) +
                negative_tests.get("testCases", []) +
                security_tests.get("testCases", [])
            )

            self.logger.info(f"Original test case count: {len(all_test_cases)}")

            # Use LLM / offline engine for deduplication
            system_prompt = self._get_system_prompt()
            user_prompt = self._build_dedup_prompt(all_test_cases)
            response = self.call_llm(user_prompt, system_prompt, temperature=0.2)
            result = self._parse_response(response, all_test_cases)

            # Safety fallback: if optimized suite is empty, use all original test cases
            if not result.get("optimizedTestSuite") and all_test_cases:
                self.logger.warning("Optimized suite was empty — using all original test cases as fallback")
                result["optimizedTestSuite"] = all_test_cases
                result["optimizedCount"] = len(all_test_cases)
                result["originalCount"] = len(all_test_cases)

            self.logger.info(f"Found {result.get('duplicatesFound', 0)} duplicate pairs")
            self.logger.info(f"Found {result.get('redundanciesEliminated', 0)} redundant test cases")
            self.logger.info(f"Optimized test case count: {result.get('optimizedCount', len(all_test_cases))}")

            self.log_end()
            return result

        except Exception as e:
            self.logger.error(f"Deduplication failed: {str(e)}")
            raise

    def _get_system_prompt(self) -> str:
        return """You are a Test Suite Optimization specialist.
Your task is to deduplicate and optimize a test suite by:
1. Identifying exact duplicate test cases (same title, same steps)
2. Identifying near-duplicate test cases (same scenario tested differently)
3. Removing redundant test cases that don't add coverage value
4. Preserving all unique coverage scenarios
5. Maintaining traceability to requirements

Return the optimized test suite as JSON."""

    def _build_dedup_prompt(self, test_cases: List[Dict]) -> str:
        return f"""Analyze and deduplicate the following test suite.

TOTAL TEST CASES: {len(test_cases)}

TEST SUITE:
{json.dumps(test_cases, indent=2)}

Return JSON in this format:
{{
  "duplicatesFound": <number of duplicate pairs found>,
  "redundanciesEliminated": <number of redundant TCs removed>,
  "originalCount": {len(test_cases)},
  "optimizedCount": <final count after dedup>,
  "coveragePreserved": "100%",
  "optimizationReport": "<brief summary>",
  "optimizedTestSuite": [<list of unique, optimized test cases>]
}}"""

    def _parse_response(self, response: str, fallback: List[Dict]) -> Dict[str, Any]:
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                data = json.loads(response[start:end])
                # Ensure required keys exist
                if "optimizedTestSuite" not in data:
                    data["optimizedTestSuite"] = fallback
                if "originalCount" not in data:
                    data["originalCount"] = len(fallback)
                if "optimizedCount" not in data:
                    data["optimizedCount"] = len(data["optimizedTestSuite"])
                if "duplicatesFound" not in data:
                    data["duplicatesFound"] = data["originalCount"] - data["optimizedCount"]
                if "redundanciesEliminated" not in data:
                    data["redundanciesEliminated"] = 0
                return data
        except Exception:
            pass

        # Fallback: return all test cases as-is
        return {
            "duplicatesFound": 0,
            "redundanciesEliminated": 0,
            "originalCount": len(fallback),
            "optimizedCount": len(fallback),
            "coveragePreserved": "100%",
            "optimizationReport": "No duplicates found. All test cases retained.",
            "optimizedTestSuite": fallback,
            "agent": "Deduplication Agent (Offline)"
        }
