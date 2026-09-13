from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_repo_contract", ROOT / "tools" / "check_repo_contract.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RepoContractTests(unittest.TestCase):
    def test_current_repository_satisfies_contract(self) -> None:
        self.assertEqual(MODULE.validate(ROOT), [])

    def test_missing_required_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            (copy / "SECURITY.md").unlink()
            self.assertIn("missing required file: SECURITY.md", MODULE.validate(copy))

    def test_readme_line_drift_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            with (copy / "README.en.md").open("a", encoding="utf-8") as handle:
                handle.write("extra line\n")
            self.assertTrue(any("README line counts differ" in item for item in MODULE.validate(copy)))

    def test_review_watermarks_can_advance_without_source_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            path = copy / "tools" / "upstream_baseline.json"
            baseline = json.loads(path.read_text(encoding="utf-8"))
            advanced_sha = "1" * 40
            baseline.update(
                reviewed_through=advanced_sha,
                reviewed_pr_through=7,
                reviewed_issue_through=9,
                reviewed_branches={"main": advanced_sha, "release": "2" * 40},
            )
            path.write_text(json.dumps(baseline), encoding="utf-8")
            self.assertEqual(MODULE.validate(copy), [])

    def test_unpinned_workflow_action_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            path = copy / ".github" / "workflows" / "unpinned.yaml"
            path.write_text(
                "jobs:\n  check:\n    steps:\n      - uses: actions/checkout@v5\n",
                encoding="utf-8",
            )
            self.assertTrue(
                any("workflow action must pin" in item for item in MODULE.validate(copy))
            )

    def test_runtime_smoke_requires_explicit_model_use_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            path = copy / "tools" / "windows_runtime_smoke.ps1"
            text = path.read_text(encoding="utf-8").replace("AllowModelUse", "ModelUse")
            path.write_text(text, encoding="utf-8")
            self.assertIn(
                "Windows runtime smoke is missing safety contract: AllowModelUse",
                MODULE.validate(copy),
            )

    def test_runtime_evidence_must_preserve_unknown_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            path = copy / "docs" / "WINDOWS-RUNTIME-EVIDENCE.md"
            text = path.read_text(encoding="utf-8").replace("unknown", "untested")
            path.write_text(text, encoding="utf-8")
            self.assertIn(
                "Windows runtime evidence is missing claim boundary: unknown",
                MODULE.validate(copy),
            )


if __name__ == "__main__":
    unittest.main()
