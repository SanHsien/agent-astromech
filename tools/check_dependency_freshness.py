#!/usr/bin/env python3
"""Report how far the declared npm dependencies have fallen behind.

Dependabot proposes upgrades one pull request at a time. It cannot answer the
question a monthly review actually asks: across every direct dependency, how
much is behind, and is anything vulnerable? This runs ``npm outdated`` and
``npm audit`` over the declared dependencies and renders one report.

It reads. It never installs, edits a manifest, or merges anything.

    python tools/check_dependency_freshness.py --github-output --output report.md
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFERRALS_PATH = ROOT / ".github" / "dependency-deferrals.json"
SEVERITIES = ("info", "low", "moderate", "high", "critical", "total")
EMPTY_AUDIT = {name: 0 for name in SEVERITIES}
RELEASE_PATTERN = re.compile(r"^\d+(?:\.\d+)*")

# A row in one of these states is a recorded decision, not maintenance work.
QUIET_STATUSES = frozenset(
    {"OK", "Ahead of dist-tag latest", "Deferred by review"}
)


def release_key(version: str) -> list[int] | None:
    match = RELEASE_PATTERN.match(str(version).strip())
    return [int(part) for part in match.group(0).split(".")] if match else None


def is_newer(candidate: str, reference: str) -> bool:
    left, right = release_key(candidate), release_key(reference)
    if left is None or right is None:
        return False
    for index in range(max(len(left), len(right))):
        a = left[index] if index < len(left) else 0
        b = right[index] if index < len(right) else 0
        if a != b:
            return a > b
    return False


def normalize_outdated(outdated: dict) -> list[dict]:
    rows = [
        {
            "name": name,
            "type": details.get("type", "unknown"),
            "current": details.get("current", "unknown"),
            "wanted": details.get("wanted", "unknown"),
            "latest": details.get("latest", "unknown"),
        }
        for name, details in (outdated or {}).items()
    ]
    return sorted(rows, key=lambda row: row["name"])


def normalize_audit(audit: dict) -> dict:
    counts = (audit or {}).get("metadata", {}).get("vulnerabilities", {})
    return {name: int(counts.get(name, 0) or 0) for name in SEVERITIES}


def load_deferrals(path: Path = DEFERRALS_PATH) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def apply_deferrals(rows: list[dict], deferrals: dict) -> list[dict]:
    """Attach an approved deferral to the row it was approved for.

    A deferral names the exact version it was judged against. When upstream
    publishes something newer the deferral stops applying and the row comes
    back, so "we looked at this and decided not yet" cannot quietly become
    "we stopped looking".
    """
    result = []
    for row in rows:
        deferral = (deferrals or {}).get(row["name"]) or {}
        reason = str(deferral.get("reason", "")).strip()
        applies = bool(
            reason
            and deferral.get("deferredLatest") == row["latest"]
            and row["current"] == row["wanted"]
        )
        result.append({**row, "deferredReason": reason} if applies else dict(row))
    return result


def status_for(row: dict) -> str:
    current, wanted, latest = row["current"], row["wanted"], row["latest"]
    if current != wanted:
        return (
            "In-range update available"
            if wanted == latest
            else "In-range update, newer major to assess"
        )
    if current == latest:
        return "OK"
    if row.get("deferredReason"):
        return "Deferred by review"
    # A pinned pre-release, or a version since unpublished, can leave the
    # installed copy ahead of the dist-tag. That is not maintenance work, so it
    # must not be reported as such.
    return "Newer release to assess" if is_newer(latest, current) else "Ahead of dist-tag latest"


def needs_maintenance(row: dict) -> bool:
    return status_for(row) not in QUIET_STATUSES


def run_npm(args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    # On Windows npm is a shim rather than an executable, so it has to go
    # through the command interpreter.
    if sys.platform == "win32":
        comspec = os.environ.get("ComSpec", "cmd.exe")
        command = [comspec, "/d", "/s", "/c", "npm " + " ".join(args)]
    else:
        command = ["npm", *args]
    return subprocess.run(
        command, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", check=False
    )


def check_dependencies(cwd: Path = ROOT, npm=run_npm) -> tuple[list[dict], dict, str]:
    # `npm outdated` exits 1 when anything is outdated and `npm audit` exits 1
    # when it finds a vulnerability. Both are results, not failures.
    errors: list[str] = []
    rows: list[dict] = []
    audit = dict(EMPTY_AUDIT)

    outdated_result = npm(["outdated", "--json", "--long", "--all=false"], cwd)
    if outdated_result.returncode not in (0, 1):
        errors.append(
            (outdated_result.stderr or f"npm outdated exited {outdated_result.returncode}").strip()
        )
    else:
        try:
            payload = json.loads(outdated_result.stdout) if outdated_result.stdout.strip() else {}
            rows = normalize_outdated(payload)
        except json.JSONDecodeError as error:
            errors.append(f"Cannot parse npm outdated: {error}")

    audit_result = npm(["audit", "--json"], cwd)
    if audit_result.returncode not in (0, 1):
        errors.append(
            (audit_result.stderr or f"npm audit exited {audit_result.returncode}").strip()
        )
    else:
        try:
            audit = normalize_audit(json.loads(audit_result.stdout))
        except json.JSONDecodeError as error:
            errors.append(f"Cannot parse npm audit: {error}")

    return rows, audit, "; ".join(part for part in errors if part)


def render_markdown(rows: list[dict], audit: dict, check_error: str = "") -> str:
    lines = [
        "# agent-astromech dependency freshness",
        "",
        "| Package | Type | Installed | In-range | Latest | Status |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        reason = row.get("deferredReason")
        status = f"Deferred by review: {reason}" if reason else status_for(row)
        lines.append(
            f"| `{row['name']}` | `{row['type']}` | `{row['current']}` | "
            f"`{row['wanted']}` | `{row['latest']}` | {status} |"
        )
    if not rows and not check_error:
        lines.append("| - | - | - | - | - | Everything is current |")

    lines += [
        "",
        "## npm audit",
        "",
        "| Info | Low | Moderate | High | Critical | Total |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| {audit['info']} | {audit['low']} | {audit['moderate']} | "
        f"{audit['high']} | {audit['critical']} | {audit['total']} |",
    ]
    if check_error:
        lines += ["", f"> Check failed: {check_error}"]

    lines += [
        "",
        "These are pinned maintainer tools, not runtime dependencies: they build the",
        "skill bundles, so an upgrade is judged by re-running the full gate",
        "(`tools/dev_check.ps1`), not by the version number alone.",
        "",
        "Rows marked *Deferred by review* were judged against the exact version shown",
        "in `.github/dependency-deferrals.json`. Publish anything newer and they come",
        "back on their own.",
        "",
    ]
    return "\n".join(lines) + "\n"


def write_github_output(needs_attention: bool, check_failed: bool, report_path: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        handle.write(f"needs_attention={'true' if needs_attention else 'false'}\n")
        handle.write(f"check_failed={'true' if check_failed else 'false'}\n")
        handle.write(f"report_path={report_path}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="dependency-freshness-report.md")
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when anything needs maintenance.",
    )
    args = parser.parse_args(argv)

    raw_rows, audit, check_error = check_dependencies()
    rows = apply_deferrals(raw_rows, load_deferrals())
    report = render_markdown(rows, audit, check_error)
    Path(args.output).write_text(report, encoding="utf-8")
    sys.stdout.write(report)

    needs_attention = (
        any(needs_maintenance(row) for row in rows)
        or audit["total"] > 0
        or bool(check_error)
    )
    if args.github_output:
        write_github_output(needs_attention, bool(check_error), args.output)
    if args.strict and needs_attention:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
