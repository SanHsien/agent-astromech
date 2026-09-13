[CmdletBinding()]
param(
    [string]$BaseRef,
    # Skip the cross-shell ai-review/ai-search matrices, which dominate the
    # total runtime (ai-review alone is 27 seconds per shell). Everything else
    # still runs. Meant for the
    # end-of-turn Stop hook, which has a 90 second budget and silently skips the
    # gate when it is exceeded -- a gate that never finishes protects nothing.
    # CI and pre-commit runs should stay on the full check.
    [switch]$Quick
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-Gate {
    param([string]$Name, [scriptblock]$Command)
    Write-Host "==> $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
}

$python = (Get-Command python -ErrorAction Stop).Source
$git = (Get-Command git -ErrorAction Stop).Source

# Walk up from wherever git.exe was found until bin\bash.exe turns up.
# Which git.exe resolves depends on who launched this script: a plain
# PowerShell finds <Git>\cmd\git.exe, but one launched from Git Bash finds
# <Git>\mingw64\bin\git.exe, because Git Bash puts mingw64\bin first on PATH.
# Assuming a fixed depth works in the first case and fails in the second --
# which is the case that matters, since the Stop hook runs from Bash.
$bash = $null
$probe = Split-Path -Parent $git
while ($probe) {
    $candidate = Join-Path $probe 'bin\bash.exe'
    if (Test-Path -LiteralPath $candidate) { $bash = $candidate; break }
    $probe = Split-Path -Parent $probe
}
if (-not $bash) {
    throw 'Git for Windows Bash was not found. Install Git for Windows.'
}
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source

Push-Location $repoRoot
try {
    $env:PYTHONUTF8 = '1'
    Invoke-Gate 'Install pinned maintainer tools' {
        & $npm ci --ignore-scripts --no-audit --no-fund
    }
    $skillsRef = Join-Path $repoRoot 'node_modules\.bin\skills-ref.cmd'
    Invoke-Gate 'Maintenance unit tests' {
        & $python -m unittest discover -s tests -p 'test_*.py' -v
    }
    Invoke-Gate 'Repository contract' { & $python tools/check_repo_contract.py }
    Invoke-Gate 'mission-log harvest tests' {
        & $python skills/mission-log/tests/harvest_test.py
    }
    if ($Quick) {
        Write-Host '==> ai-review/ai-search matrices -- SKIPPED (-Quick)'
    } else {
        foreach ($shell in @('sh', 'bash')) {
            Invoke-Gate "ai-review matrix ($shell on Git Bash/NTFS)" {
                $env:SH = $shell
                & $bash skills/ai-review/tests/matrix.sh
            }
            Invoke-Gate "ai-search matrix ($shell on Git Bash/NTFS)" {
                $env:SH = $shell
                & $bash skills/ai-search/tests/matrix.sh
            }
        }
        Remove-Item Env:SH -ErrorAction SilentlyContinue
    }
    foreach ($skill in Get-ChildItem -LiteralPath skills -Directory | Sort-Object Name) {
        Invoke-Gate "skills-ref validate $($skill.Name)" {
            & $skillsRef validate $skill.FullName
        }
    }
    Invoke-Gate 'Windows AI Desktop/TUI/CLI isolated install smoke' {
        & pwsh -NoProfile -File tools/windows_agent_smoke.ps1
    }
    Invoke-Gate 'git diff --check (unstaged)' { git diff --check }
    Invoke-Gate 'git diff --cached --check (staged)' { git diff --cached --check }
    # Whitespace has to be checked across every commit being introduced, not just
    # the tip. On a pull request the base is the merge target; on a push it is
    # `github.event.before`, the tip main had before the push. A push of five
    # commits used to leave the middle three unchecked.
    #
    # `before` is all zeros for a branch's first push, and after a force push it
    # is not an ancestor of HEAD, so the range is anchored on the merge base and
    # falls back to the tip commit when no usable base exists.
    if (-not [string]::IsNullOrWhiteSpace($BaseRef) -and $BaseRef -notmatch '^0{40}$') {
        $baseCommit = (& git rev-parse --verify "$BaseRef^{commit}" 2>$null | Select-Object -First 1)
        if ($LASTEXITCODE -eq 0 -and $baseCommit) {
            $mergeBase = (& git merge-base $baseCommit HEAD 2>$null | Select-Object -First 1)
            $rangeStart = if ($LASTEXITCODE -eq 0 -and $mergeBase) { $mergeBase } else { $baseCommit }
            Invoke-Gate "git diff --check $rangeStart..HEAD" { git diff --check "$rangeStart..HEAD" }
        } else {
            # A shallow clone cannot see the base. Say so loudly: silently
            # checking only HEAD is how the gap got there in the first place.
            Write-Host "WARN: BaseRef '$BaseRef' is unavailable (shallow clone?); only the tip commit is checked."
            Invoke-Gate 'git show --check HEAD fallback' { git show --check --format= HEAD }
        }
    } else {
        Invoke-Gate 'git show --check HEAD' { git show --check --format= HEAD }
    }
    Write-Host 'DEV CHECK PASSED'
} finally {
    Remove-Item Env:SH -ErrorAction SilentlyContinue
    Pop-Location
}
