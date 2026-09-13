#!/usr/bin/env python3
"""Validate maintained-fork files and public repository contracts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    ".editorconfig",
    ".gitattributes",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/dependabot.yml",
    ".github/dependency-deferrals.json",
    ".github/pull_request_template.md",
    ".github/workflows/ci.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/dependency-freshness.yml",
    ".github/workflows/upstream-check.yml",
    "AGENTS.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "FORK.md",
    "NOTICE.md",
    "package-lock.json",
    "package.json",
    "SECURITY.md",
    "docs/DECISIONS.md",
    "docs/DEVELOPMENT.md",
    "docs/REVIEW.md",
    "docs/UPSTREAM.md",
    "docs/WINDOWS-AI-ENVIRONMENTS.md",
    "docs/WINDOWS-RUNTIME-EVIDENCE.md",
    "tools/dev_check.ps1",
    "tools/dev_check.sh",
    "tools/windows_agent_smoke.ps1",
    "tools/windows_runtime_smoke.ps1",
    "tools/upstream_baseline.json",
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in REQUIRED:
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    readme = root / "README.md"
    readme_en = root / "README.en.md"
    if readme.is_file() and readme_en.is_file():
        zh_lines = readme.read_text(encoding="utf-8").splitlines()
        en_lines = readme_en.read_text(encoding="utf-8").splitlines()
        if len(zh_lines) != len(en_lines):
            errors.append(f"README line counts differ: {len(zh_lines)} != {len(en_lines)}")
        for path, lines in ((readme, zh_lines), (readme_en, en_lines)):
            if not any("SanHsien/agent-astromech" in line for line in lines):
                errors.append(f"{path.name} does not identify the maintained fork")

    skills = sorted((root / "skills").glob("*/SKILL.md"))
    if len(skills) != 14:
        errors.append(f"expected 14 skills, found {len(skills)}")
    frontmatter = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
    for skill in skills:
        match = frontmatter.match(skill.read_text(encoding="utf-8"))
        if not match:
            errors.append(f"missing frontmatter: {skill.relative_to(root)}")
            continue
        keys = [line.split(":", 1)[0] for line in match.group(1).splitlines() if ":" in line]
        allowed = ["name", "description"]
        if skill.parent.name == "token-optimizer":
            allowed.append("license")
        if keys != allowed:
            errors.append(f"unexpected frontmatter keys/order: {skill.relative_to(root)}")
        if not any(line.startswith("description: '") for line in match.group(1).splitlines()):
            errors.append(f"description must use single quotes: {skill.relative_to(root)}")

    for relative in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
        path = root / relative
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"invalid JSON {relative}: {exc}")
            continue
        if data.get("name") != "agent-astromech":
            errors.append(f"{relative} must preserve name agent-astromech")

    baseline_path = root / "tools/upstream_baseline.json"
    if baseline_path.is_file():
        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid upstream baseline JSON: {exc}")
        else:
            required_keys = {
                "schema_version",
                "upstream",
                "default_branch",
                "reviewed_through",
                "reviewed_pr_through",
                "reviewed_issue_through",
                "reviewed_branches",
            }
            if set(baseline) != required_keys:
                errors.append("baseline keys do not match schema v1")
            if baseline.get("schema_version") != 1 or isinstance(
                baseline.get("schema_version"), bool
            ):
                errors.append("baseline schema_version must be integer 1")
            if baseline.get("upstream") != "tingyulu/MyR2D2":
                errors.append("baseline upstream must be 'tingyulu/MyR2D2'")
            if baseline.get("default_branch") != "main":
                errors.append("baseline default_branch must be 'main'")
            reviewed = baseline.get("reviewed_through")
            if not isinstance(reviewed, str) or not SHA_RE.fullmatch(reviewed):
                errors.append("baseline reviewed_through must be a lowercase 40-character SHA")
            for key in ("reviewed_pr_through", "reviewed_issue_through"):
                value = baseline.get(key)
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    errors.append(f"baseline {key} must be a non-negative integer")
            branches = baseline.get("reviewed_branches")
            if not isinstance(branches, dict) or not branches:
                errors.append("baseline reviewed_branches must be a non-empty object")
            elif any(
                not isinstance(name, str)
                or not name
                or not isinstance(sha, str)
                or not SHA_RE.fullmatch(sha)
                for name, sha in branches.items()
            ):
                errors.append("baseline reviewed_branches contains an invalid name or SHA")
            elif branches.get("main") != reviewed:
                errors.append("baseline main branch SHA must equal reviewed_through")

    agents = root / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8")
        for phrase in ("SanHsien/agent-astromech", "tingyulu/MyR2D2", "gh repo set-default"):
            if phrase not in text:
                errors.append(f"AGENTS.md is missing boundary: {phrase}")

    runtime_smoke = root / "tools/windows_runtime_smoke.ps1"
    if runtime_smoke.is_file():
        runtime_text = runtime_smoke.read_text(encoding="utf-8")
        for phrase in ("AllowModelUse", "TimeoutSeconds", "Assert-DamageReportDiscovery"):
            if phrase not in runtime_text:
                errors.append(f"Windows runtime smoke is missing safety contract: {phrase}")

    runtime_evidence = root / "docs/WINDOWS-RUNTIME-EVIDENCE.md"
    if runtime_evidence.is_file():
        evidence_text = runtime_evidence.read_text(encoding="utf-8")
        for phrase in ("exact repo SHA", "Codex Desktop", "unknown"):
            if phrase not in evidence_text:
                errors.append(f"Windows runtime evidence is missing claim boundary: {phrase}")

    harvester = root / "skills/mission-log/scripts/harvest.py"
    if harvester.is_file() and "os.uname(" in harvester.read_text(encoding="utf-8"):
        errors.append("mission-log harvester must not use os.uname() on Windows")

    attributes = root / ".gitattributes"
    if attributes.is_file() and "* text=auto eol=lf" not in attributes.read_text(encoding="utf-8"):
        errors.append(".gitattributes must normalize text to LF")

    action_use = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")
    workflows = root / ".github" / "workflows"
    if workflows.is_dir():
        workflow_files = [*workflows.glob("*.yml"), *workflows.glob("*.yaml")]
        for workflow in sorted(workflow_files):
            for line_number, line in enumerate(
                workflow.read_text(encoding="utf-8").splitlines(), 1
            ):
                match = action_use.match(line)
                if not match:
                    continue
                action = match.group(1)
                if action.startswith("./") or action.startswith("docker://"):
                    continue
                ref = action.rsplit("@", 1)[-1] if "@" in action else ""
                if not SHA_RE.fullmatch(ref):
                    errors.append(
                        f"workflow action must pin a full commit SHA: "
                        f"{workflow.relative_to(root)}:{line_number}"
                    )
    return errors


def main() -> int:
    errors = validate(ROOT)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print("REPO CONTRACT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
