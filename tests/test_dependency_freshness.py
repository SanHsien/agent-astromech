"""Unit tests for tools/check_dependency_freshness.py.

The checker shells out to npm, so every test here feeds it a recorded npm
payload instead. What is being pinned is the judgement -- which rows count as
maintenance work and which are recorded decisions -- not npm's behaviour.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import check_dependency_freshness as checker  # noqa: E402


def completed(stdout: str = "", returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess(
        args=["npm"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def fake_npm(outdated: str, audit: str, outdated_rc: int = 1, audit_rc: int = 0):
    def _npm(args, cwd=None):
        if args[0] == "outdated":
            return completed(outdated, outdated_rc)
        return completed(audit, audit_rc)

    return _npm


AUDIT_CLEAN = json.dumps({"metadata": {"vulnerabilities": {"info": 0, "low": 0, "moderate": 0, "high": 0, "critical": 0, "total": 0}}})


class StatusTests(unittest.TestCase):
    def test_current_version_is_ok(self):
        row = {"current": "1.5.23", "wanted": "1.5.23", "latest": "1.5.23"}
        self.assertEqual(checker.status_for(row), "OK")
        self.assertFalse(checker.needs_maintenance(row))

    def test_behind_latest_needs_assessment(self):
        row = {"current": "1.5.23", "wanted": "1.5.23", "latest": "1.6.0"}
        self.assertEqual(checker.status_for(row), "Newer release to assess")
        self.assertTrue(checker.needs_maintenance(row))

    def test_in_range_update_is_dependabot_work(self):
        row = {"current": "1.5.23", "wanted": "1.5.24", "latest": "1.5.24"}
        self.assertEqual(checker.status_for(row), "In-range update available")
        self.assertTrue(checker.needs_maintenance(row))

    def test_installed_ahead_of_dist_tag_is_not_maintenance(self):
        # A pre-release pin, or a version pulled from the registry, can sit
        # ahead of `latest`. Reporting that as work to do is a false alarm.
        row = {"current": "2.0.0-rc.1", "wanted": "2.0.0-rc.1", "latest": "1.9.0"}
        self.assertEqual(checker.status_for(row), "Ahead of dist-tag latest")
        self.assertFalse(checker.needs_maintenance(row))


class DeferralTests(unittest.TestCase):
    def test_deferral_silences_the_exact_version_it_was_judged_against(self):
        rows = [{"name": "skills", "type": "devDependencies", "current": "1.5.23", "wanted": "1.5.23", "latest": "1.6.0"}]
        deferrals = {"skills": {"deferredLatest": "1.6.0", "reason": "bundle format change, needs a full gate run"}}
        applied = checker.apply_deferrals(rows, deferrals)
        self.assertEqual(checker.status_for(applied[0]), "Deferred by review")
        self.assertFalse(checker.needs_maintenance(applied[0]))

    def test_a_newer_release_brings_the_row_back(self):
        # This is the whole point of recording the version: the deferral expires
        # by itself instead of silencing the row forever.
        rows = [{"name": "skills", "type": "devDependencies", "current": "1.5.23", "wanted": "1.5.23", "latest": "1.7.0"}]
        deferrals = {"skills": {"deferredLatest": "1.6.0", "reason": "bundle format change"}}
        applied = checker.apply_deferrals(rows, deferrals)
        self.assertTrue(checker.needs_maintenance(applied[0]))

    def test_a_deferral_without_a_reason_does_not_apply(self):
        rows = [{"name": "skills", "type": "devDependencies", "current": "1.5.23", "wanted": "1.5.23", "latest": "1.6.0"}]
        applied = checker.apply_deferrals(rows, {"skills": {"deferredLatest": "1.6.0", "reason": "   "}})
        self.assertTrue(checker.needs_maintenance(applied[0]))

    def test_missing_deferrals_file_is_not_an_error(self):
        self.assertEqual(checker.load_deferrals(Path("does-not-exist.json")), {})

    def test_repo_deferrals_file_parses(self):
        self.assertIsInstance(checker.load_deferrals(), dict)


class CheckDependenciesTests(unittest.TestCase):
    def test_outdated_exit_one_is_a_result_not_a_failure(self):
        outdated = json.dumps({"skills": {"current": "1.5.23", "wanted": "1.5.23", "latest": "1.6.0", "type": "devDependencies"}})
        rows, audit, error = checker.check_dependencies(npm=fake_npm(outdated, AUDIT_CLEAN))
        self.assertEqual(error, "")
        self.assertEqual([row["name"] for row in rows], ["skills"])
        self.assertEqual(audit["total"], 0)

    def test_unexpected_exit_code_is_reported(self):
        rows, _audit, error = checker.check_dependencies(
            npm=fake_npm("", AUDIT_CLEAN, outdated_rc=127)
        )
        self.assertEqual(rows, [])
        self.assertIn("npm outdated exited 127", error)

    def test_unparsable_output_is_reported_not_swallowed(self):
        _rows, _audit, error = checker.check_dependencies(npm=fake_npm("not json", AUDIT_CLEAN))
        self.assertIn("Cannot parse npm outdated", error)

    def test_empty_stdout_means_nothing_outdated(self):
        rows, _audit, error = checker.check_dependencies(
            npm=fake_npm("", AUDIT_CLEAN, outdated_rc=0)
        )
        self.assertEqual(rows, [])
        self.assertEqual(error, "")


class RenderTests(unittest.TestCase):
    def test_clean_report_says_so(self):
        report = checker.render_markdown([], dict(checker.EMPTY_AUDIT))
        self.assertIn("Everything is current", report)

    def test_deferral_reason_reaches_the_report(self):
        rows = [{"name": "skills", "type": "devDependencies", "current": "1.5.23", "wanted": "1.5.23", "latest": "1.6.0", "deferredReason": "needs a full gate run"}]
        self.assertIn("Deferred by review: needs a full gate run", checker.render_markdown(rows, dict(checker.EMPTY_AUDIT)))

    def test_check_error_is_visible_in_the_report(self):
        report = checker.render_markdown([], dict(checker.EMPTY_AUDIT), "npm outdated exited 127")
        self.assertIn("Check failed: npm outdated exited 127", report)

    def test_audit_counts_are_rendered(self):
        audit = {"info": 0, "low": 1, "moderate": 2, "high": 3, "critical": 4, "total": 10}
        self.assertIn("| 0 | 1 | 2 | 3 | 4 | 10 |", checker.render_markdown([], audit))


if __name__ == "__main__":
    unittest.main()
