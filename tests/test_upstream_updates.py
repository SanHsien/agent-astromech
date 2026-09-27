from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_upstream_updates", ROOT / "tools" / "check_upstream_updates.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

SHA = "0f74f6737dc19f2dd055681a981121f8b29191f0"
NEW_SHA = "1" * 40


def baseline() -> dict:
    return {
        "schema_version": 1,
        "upstream": "tingyulu/MyR2D2",
        "default_branch": "main",
        "reviewed_through": SHA,
        "reviewed_pr_through": 0,
        "reviewed_issue_through": 0,
        "reviewed_branches": {"main": SHA},
    }


class UpstreamCheckerTests(unittest.TestCase):
    def test_unchanged_upstream_is_current(self) -> None:
        responses = {
            "compare": {"status": "identical", "commits": []},
            "pulls": [],
            "issues": [],
            "branches": [{"name": "main", "commit": {"sha": SHA}}],
        }

        def get(endpoint: str):
            return responses[next(key for key in responses if key in endpoint)]

        result = MODULE.evaluate(baseline(), get)
        self.assertFalse(result.needs_attention)
        self.assertEqual(result.upstream_head, SHA)

    def test_all_change_surfaces_require_attention(self) -> None:
        def get(endpoint: str):
            if "compare" in endpoint:
                return {"status": "ahead", "commits": [{"sha": NEW_SHA}]}
            if "/pulls?" in endpoint:
                return [{"number": 1}]
            if "/issues?" in endpoint:
                return [{"number": 1}, {"number": 2, "pull_request": {}}]
            return [
                {"name": "main", "commit": {"sha": NEW_SHA}},
                {"name": "topic", "commit": {"sha": NEW_SHA}},
            ]

        result = MODULE.evaluate(baseline(), get)
        self.assertTrue(result.needs_attention)
        self.assertEqual(result.new_commits, (NEW_SHA,))
        self.assertEqual(result.new_prs, (1,))
        self.assertEqual(result.new_issues, (1,))
        self.assertEqual(result.changed_branches, ("main", "topic"))

    def test_invalid_baseline_fails_closed(self) -> None:
        data = baseline()
        data["schema_version"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "baseline.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(MODULE.CheckError):
                MODULE.load_baseline(path)

    def test_api_failure_is_not_treated_as_no_updates(self) -> None:
        def fail(_endpoint: str):
            raise MODULE.CheckError("network down")

        with self.assertRaises(MODULE.CheckError):
            MODULE.evaluate(baseline(), fail)

    def test_rewritten_default_branch_reports_authoritative_branch_head(self) -> None:
        merge_base = "2" * 40

        def get(endpoint: str):
            if "compare" in endpoint:
                return {
                    "status": "diverged",
                    "merge_base_commit": {"sha": merge_base},
                    "commits": [],
                }
            if "/pulls?" in endpoint or "/issues?" in endpoint:
                return []
            return [{"name": "main", "commit": {"sha": NEW_SHA}}]

        result = MODULE.evaluate(baseline(), get)
        self.assertTrue(result.needs_attention)
        self.assertEqual(result.upstream_head, NEW_SHA)
        self.assertEqual(result.changed_branches, ("main",))


if __name__ == "__main__":
    unittest.main()
