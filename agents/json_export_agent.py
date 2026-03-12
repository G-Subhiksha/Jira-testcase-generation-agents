"""
JSON Export Agent
Converts the generated test_cases.xlsx into a structured JSON file
and saves it in the same output folder as the Excel file.

JSON structure:
{
  "metadata":        { ... summary / classification info ... },
  "epicOverview":    { epicTitle, applicationType, domain, ... },
  "features":        [ { featureId, featureTitle, stories: [...] } ],
  "stories":         { "US-001": { storyId, title, testCases: [...] } },
  "testCases":       [ all test cases, flat list ],
  "traceabilityMatrix": [ ... ],
  "summary":         { totalTestCases, byCategory, byPriority, ... }
}
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List

from agents.base_agent import BaseAgent


class JsonExportAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any], llm_client: Any):
        super().__init__(config, llm_client)
        self.agent_name = "JsonExportAgent"

    # ------------------------------------------------------------------
    # Entry point called by the orchestrator
    # ------------------------------------------------------------------
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expected input_data keys (all optional – gracefully handled):
            excel_path        str   – path to the generated .xlsx
            output_path       str   – desired .json path  (default: same dir as xlsx)
            optimized_suite   dict
            traceability      dict
            classification    dict
            decomposition     dict  (epic mode only)
        """
        self.log_start()
        try:
            excel_path     = input_data.get("excel_path", "")
            output_path    = input_data.get("output_path", "")
            optimized_suite = input_data.get("optimized_suite", {})
            traceability   = input_data.get("traceability", {})
            classification = input_data.get("classification", {})
            decomposition  = input_data.get("decomposition", {})

            # Determine output JSON path
            if not output_path:
                if excel_path:
                    base = os.path.splitext(excel_path)[0]
                    output_path = base + ".json"
                else:
                    output_path = "output/test_cases.json"

            self.logger.info(f"Building JSON export → {output_path}")

            payload = self._build_payload(
                optimized_suite, traceability, classification, decomposition, excel_path
            )

            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2, ensure_ascii=False)

            self.logger.info(
                f"JSON export saved: {output_path}  "
                f"({payload['metadata']['totalTestCases']} test cases)"
            )
            self.log_end()
            return {
                "jsonPath":      output_path,
                "testCaseCount": payload["metadata"]["totalTestCases"],
                "agent":         self.agent_name,
                "timestamp":     datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"JSON export failed: {str(e)}")
            raise

    # ------------------------------------------------------------------
    # Build the full JSON payload from in-memory agent outputs
    # ------------------------------------------------------------------
    def _build_payload(
        self,
        optimized_suite: Dict,
        traceability: Dict,
        classification: Dict,
        decomposition: Dict,
        excel_path: str,
    ) -> Dict:
        test_cases: List[Dict] = optimized_suite.get("optimizedTestSuite", [])

        # ── metadata ────────────────────────────────────────────────────
        category_counts: Dict[str, int] = {}
        priority_counts: Dict[str, int] = {}
        automation_counts: Dict[str, int] = {}
        story_counts: Dict[str, int] = {}

        for tc in test_cases:
            _inc(category_counts,  tc.get("category",   "Unknown"))
            _inc(priority_counts,  tc.get("priority",   "Unknown"))
            _inc(automation_counts, tc.get("automation", "Unknown"))
            sid = tc.get("storyId", "")
            if sid:
                _inc(story_counts, sid)

        metadata = {
            "generatedOn":       datetime.now().isoformat(),
            "excelSource":       excel_path,
            "applicationType":   classification.get("applicationType", ""),
            "domain":            classification.get("domain", ""),
            "product":           classification.get("product", ""),
            "projectState":      classification.get("projectState", ""),
            "totalTestCases":    len(test_cases),
            "byCategory":        category_counts,
            "byPriority":        priority_counts,
            "byAutomation":      automation_counts,
            "byStory":           story_counts,
        }

        # ── epic / features ──────────────────────────────────────────────
        features_raw = decomposition.get("features", [])
        epic_title   = decomposition.get("epicTitle", "")

        epic_overview = {
            "epicTitle":       epic_title,
            "applicationType": classification.get("applicationType", ""),
            "domain":          classification.get("domain", ""),
            "product":         classification.get("product", ""),
            "projectState":    classification.get("projectState", ""),
            "totalFeatures":   len(features_raw),
            "totalStories":    sum(len(f.get("stories", [])) for f in features_raw),
            "totalTestCases":  len(test_cases),
        } if features_raw else {}

        features_json: List[Dict] = []
        for feat in features_raw:
            stories_in_feat = []
            for s in feat.get("stories", []):
                sid = s.get("storyId", "")
                stories_in_feat.append({
                    "storyId":   sid,
                    "title":     s.get("title", ""),
                    "role":      s.get("role", ""),
                    "priority":  s.get("priority", ""),
                    "testCount": story_counts.get(sid, 0),
                })
            features_json.append({
                "featureId":    feat.get("featureId", ""),
                "featureTitle": feat.get("featureTitle", ""),
                "stories":      stories_in_feat,
            })

        # ── per-story test cases ─────────────────────────────────────────
        tc_by_story: Dict[str, List[Dict]] = {}
        for tc in test_cases:
            sid = tc.get("storyId", "ALL")
            tc_by_story.setdefault(sid, []).append(tc)

        all_stories_meta: Dict[str, Dict] = {
            s.get("storyId", ""): s
            for feat in features_raw
            for s in feat.get("stories", [])
        }

        stories_json: Dict[str, Dict] = {}
        for sid, tcs in tc_by_story.items():
            meta = all_stories_meta.get(sid, {})
            acs_raw = meta.get("acceptanceCriteria", [])
            acs = []
            for ac in acs_raw:
                if isinstance(ac, dict):
                    acs.append({"acId": ac.get("acId", ""), "description": ac.get("description", str(ac))})
                else:
                    acs.append({"acId": "", "description": str(ac)})

            stories_json[sid] = {
                "storyId":            sid,
                "title":              meta.get("title", ""),
                "story":              meta.get("story", ""),
                "role":               meta.get("role", ""),
                "priority":           meta.get("priority", ""),
                "acceptanceCriteria": acs,
                "testCases":          [_clean_tc(tc) for tc in tcs],
            }

        # ── flat test cases (clean) ──────────────────────────────────────
        flat_test_cases = [_clean_tc(tc) for tc in test_cases]

        # ── traceability matrix ──────────────────────────────────────────
        matrix = traceability.get("traceabilityMatrix", [])
        coverage_metrics = traceability.get("coverageMetrics", {})

        return {
            "metadata":          metadata,
            "epicOverview":      epic_overview,
            "features":          features_json,
            "stories":           stories_json,
            "testCases":         flat_test_cases,
            "traceabilityMatrix": matrix,
            "coverageMetrics":   coverage_metrics,
            "summary": {
                "totalTestCases":     len(test_cases),
                "byCategory":         category_counts,
                "byPriority":         priority_counts,
                "byAutomation":       automation_counts,
                "byStory":            story_counts,
                "optimizationMetrics": {
                    "originalCount":        optimized_suite.get("originalCount", 0),
                    "duplicatesRemoved":    optimized_suite.get("duplicatesRemoved", 0),
                    "redundanciesRemoved":  optimized_suite.get("redundanciesRemoved", 0),
                    "reductionPercentage":  optimized_suite.get("reductionPercentage", 0),
                },
            },
        }


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _inc(d: Dict[str, int], key: str) -> None:
    d[key] = d.get(key, 0) + 1


def _clean_tc(tc: Dict) -> Dict:
    """Return a clean, serialisable copy of a test case dict."""
    preconditions = tc.get("preconditions", [])
    if isinstance(preconditions, str):
        preconditions = [p.strip() for p in preconditions.splitlines() if p.strip()]

    test_data = tc.get("testData", {})
    if isinstance(test_data, str):
        # keep as string if it's already formatted
        pass

    steps = tc.get("steps", [])
    if isinstance(steps, str):
        steps = [s.strip() for s in steps.splitlines() if s.strip()]

    expected = tc.get("expectedResults", [])
    if isinstance(expected, str):
        expected = [e.strip() for e in expected.splitlines() if e.strip()]

    return {
        "testCaseId":      tc.get("testCaseId", ""),
        "storyId":         tc.get("storyId", ""),
        "storyTitle":      tc.get("storyTitle", ""),
        "title":           tc.get("title", ""),
        "category":        tc.get("category", ""),
        "priority":        tc.get("priority", ""),
        "automation":      tc.get("automation", ""),
        "domain":          tc.get("domain", ""),
        "projectState":    tc.get("projectState", ""),
        "acMapped":        tc.get("acMapped", ""),
        "traceability":    tc.get("traceability", ""),
        "preconditions":   preconditions,
        "testData":        test_data,
        "steps":           steps,
        "expectedResults": expected,
    }
