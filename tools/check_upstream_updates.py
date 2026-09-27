#!/usr/bin/env python3
"""Fail-closed comparison of upstream state against reviewed watermarks."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = ROOT / "tools" / "upstream_baseline.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class CheckError(RuntimeError):
    """Raised when upstream state cannot be checked safely."""


@dataclass(frozen=True)
class Result:
    upstream: str
    reviewed_through: str
    upstream_head: str
    new_commits: tuple[str, ...]
    new_prs: tuple[int, ...]
    new_issues: tuple[int, ...]
    changed_branches: tuple[str, ...]

    @property
    def needs_attention(self) -> bool:
        return any(
            (
                self.new_commits,
                self.new_prs,
                self.new_issues,
                self.changed_branches,
            )
        )


def load_baseline(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CheckError(f"cannot read baseline {path}: {exc}") from exc

    required = {
        "schema_version",
        "upstream",
        "default_branch",
        "reviewed_through",
        "reviewed_pr_through",
        "reviewed_issue_through",
        "reviewed_branches",
    }
    if set(data) != required:
        raise CheckError("baseline keys do not match schema v1")
    if data["schema_version"] != 1 or isinstance(data["schema_version"], bool):
        raise CheckError("schema_version must be integer 1")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", data["upstream"]):
        raise CheckError("upstream must be owner/repo")
    if not isinstance(data["default_branch"], str) or not data["default_branch"]:
        raise CheckError("default_branch must be non-empty")
    if not SHA_RE.fullmatch(data["reviewed_through"]):
        raise CheckError("reviewed_through must be a 40-character lowercase SHA")
    for key in ("reviewed_pr_through", "reviewed_issue_through"):
        if isinstance(data[key], bool) or not isinstance(data[key], int) or data[key] < 0:
            raise CheckError(f"{key} must be a non-negative integer")
    branches = data["reviewed_branches"]
    if not isinstance(branches, dict) or not branches:
        raise CheckError("reviewed_branches must be a non-empty object")
    if any(not isinstance(name, str) or not SHA_RE.fullmatch(sha) for name, sha in branches.items()):
        raise CheckError("reviewed_branches contains an invalid name or SHA")
    if branches.get(data["default_branch"]) != data["reviewed_through"]:
        raise CheckError("default branch watermark must equal reviewed_through")
    return data


def gh_json(endpoint: str) -> Any:
    command = ["gh", "api", "--paginate", "--slurp", endpoint]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()
        summary = detail[-1] if detail else "unknown gh failure"
        raise CheckError(f"gh api failed for {endpoint}: {summary}")
    try:
        pages = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise CheckError(f"gh api returned invalid JSON for {endpoint}") from exc
    if not isinstance(pages, list) or not pages:
        raise CheckError(f"gh api returned no pages for {endpoint}")
    if len(pages) == 1 and not isinstance(pages[0], list):
        return pages[0]
    if not all(isinstance(page, list) for page in pages):
        raise CheckError(f"gh api pagination shape is invalid for {endpoint}")
    return [item for page in pages for item in page]


def evaluate(baseline: dict[str, Any], get_json: Callable[[str], Any]) -> Result:
    repo = baseline["upstream"]
    branch = baseline["default_branch"]
    compare = get_json(
        f"repos/{repo}/compare/{baseline['reviewed_through']}...{branch}"
    )
    if not isinstance(compare, dict) or not isinstance(compare.get("commits"), list):
        raise CheckError("compare response is missing commits")
    new_commits = tuple(
        item["sha"]
        for item in compare["commits"]
        if isinstance(item, dict) and SHA_RE.fullmatch(str(item.get("sha", "")))
    )
    if len(new_commits) != len(compare["commits"]):
        raise CheckError("compare response contains an invalid commit")

    pulls = get_json(f"repos/{repo}/pulls?state=all&per_page=100&sort=created&direction=asc")
    issues = get_json(f"repos/{repo}/issues?state=all&per_page=100&sort=created&direction=asc")
    branches = get_json(f"repos/{repo}/branches?per_page=100")
    if not all(isinstance(value, list) for value in (pulls, issues, branches)):
        raise CheckError("ticket or branch response is not a list")

    def numbers(items: list[dict[str, Any]], *, issues_only: bool = False) -> tuple[int, ...]:
        values: list[int] = []
        for item in items:
            if not isinstance(item, dict) or isinstance(item.get("number"), bool):
                raise CheckError("ticket response contains an invalid item")
            if issues_only and "pull_request" in item:
                continue
            number = item.get("number")
            if not isinstance(number, int) or number < 1:
                raise CheckError("ticket response contains an invalid number")
            values.append(number)
        return tuple(sorted(values))

    new_prs = tuple(
        value for value in numbers(pulls) if value > baseline["reviewed_pr_through"]
    )
    new_issues = tuple(
        value
        for value in numbers(issues, issues_only=True)
        if value > baseline["reviewed_issue_through"]
    )

    current_branches: dict[str, str] = {}
    for item in branches:
        if not isinstance(item, dict):
            raise CheckError("branch response contains an invalid item")
        name = item.get("name")
        sha = item.get("commit", {}).get("sha")
        if not isinstance(name, str) or not SHA_RE.fullmatch(str(sha)):
            raise CheckError("branch response contains an invalid name or SHA")
        current_branches[name] = sha
    upstream_head = current_branches.get(branch)
    if not isinstance(upstream_head, str) or not SHA_RE.fullmatch(upstream_head):
        raise CheckError("branch response is missing a valid upstream head")
    changed = tuple(
        sorted(
            name
            for name in set(current_branches) | set(baseline["reviewed_branches"])
            if current_branches.get(name) != baseline["reviewed_branches"].get(name)
        )
    )
    return Result(
        upstream=repo,
        reviewed_through=baseline["reviewed_through"],
        upstream_head=upstream_head,
        new_commits=new_commits,
        new_prs=new_prs,
        new_issues=new_issues,
        changed_branches=changed,
    )


def render(result: Result) -> str:
    status = "NEEDS REVIEW" if result.needs_attention else "UP TO DATE"
    lines = [
        "# Upstream review report",
        "",
        f"- Status: **{status}**",
        f"- Upstream: `{result.upstream}`",
        f"- Reviewed through: `{result.reviewed_through}`",
        f"- Current upstream head: `{result.upstream_head}`",
        f"- New commits: {len(result.new_commits)}",
        f"- New PRs: {', '.join(map(str, result.new_prs)) or 'none'}",
        f"- New issues: {', '.join(map(str, result.new_issues)) or 'none'}",
        f"- Changed branches: {', '.join(result.changed_branches) or 'none'}",
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = evaluate(load_baseline(args.baseline), gh_json)
        report = render(result)
        if args.output:
            args.output.write_text(report, encoding="utf-8", newline="\n")
        else:
            sys.stdout.write(report)
        if args.github_output:
            output_path = os.environ.get("GITHUB_OUTPUT")
            if not output_path:
                raise CheckError("GITHUB_OUTPUT is required with --github-output")
            with Path(output_path).open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(f"needs_attention={'true' if result.needs_attention else 'false'}\n")
        return 1 if args.strict and result.needs_attention else 0
    except CheckError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
