#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

PYTHON=${PYTHON:-python3}
command -v "$PYTHON" >/dev/null 2>&1 || { echo "FAIL: python3 is required" >&2; exit 1; }
command -v npm >/dev/null 2>&1 || { echo "FAIL: Node.js/npm is required" >&2; exit 1; }

echo '==> Install pinned maintainer tools'
npm ci --ignore-scripts --no-audit --no-fund

echo '==> Maintenance unit tests'
"$PYTHON" -m unittest discover -s tests -p 'test_*.py' -v

echo '==> Repository contract'
"$PYTHON" tools/check_repo_contract.py

echo '==> mission-log harvest tests'
"$PYTHON" skills/mission-log/tests/harvest_test.py
LC_ALL=C "$PYTHON" skills/mission-log/tests/harvest_test.py

case "$(uname -s 2>/dev/null || printf unknown)" in
    MINGW*|MSYS*) shells='sh bash' ;;
    *) shells='sh dash bash ksh zsh' ;;
esac

for shell_name in $shells; do
    command -v "$shell_name" >/dev/null 2>&1 || {
        echo "FAIL: required shell is missing: $shell_name" >&2
        exit 1
    }
    echo "==> ai-review matrix ($shell_name)"
    SH=$shell_name sh skills/ai-review/tests/matrix.sh
    echo "==> ai-search matrix ($shell_name)"
    SH=$shell_name sh skills/ai-search/tests/matrix.sh
done

for skill in skills/*/; do
    echo "==> skills-ref validate $skill"
    ./node_modules/.bin/skills-ref validate "$skill"
done

echo '==> git diff --check'
git diff --check
git diff --cached --check

echo 'DEV CHECK PASSED'
