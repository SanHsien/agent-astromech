[CmdletBinding()]
param(
    # gemini-cli is installed here even though the Gemini CLI itself is not on the
    # box: `skills add --agent <name>` is the *installer's* per-agent behaviour, and
    # it writes to the same unified .agents/skills/ target regardless of whether the
    # target CLI exists. That makes this a real per-agent install-layer measurement
    # (TEST_PLAN CROSS-01) rather than a claim carried over from upstream. It does
    # NOT measure the discovery layer -- that still needs the CLI and stays untested.
    [string[]]$Agents = @('codex', 'claude-code', 'gemini-cli')
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$git = (Get-Command git -ErrorAction Stop).Source
$skills = Join-Path $repoRoot 'node_modules\.bin\skills.cmd'
if (-not (Test-Path -LiteralPath $skills -PathType Leaf)) {
    throw 'Pinned skills CLI is missing. Run npm ci --ignore-scripts first.'
}
$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$smokeRoot = Join-Path $tempBase ("astromech-agent-smoke-{0}-{1}" -f $PID, [guid]::NewGuid().ToString('N'))
$resolvedSmoke = [IO.Path]::GetFullPath($smokeRoot)
if (-not $resolvedSmoke.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase) -or
    (Split-Path -Leaf $resolvedSmoke) -notmatch '^astromech-agent-smoke-[0-9]+-[0-9a-f]{32}$') {
    throw "Unsafe smoke path: $resolvedSmoke"
}

New-Item -ItemType Directory -Path $resolvedSmoke | Out-Null
try {
    foreach ($agent in $Agents) {
        if ($agent -notmatch '^[a-z0-9-]+$') { throw "Invalid agent name: $agent" }
        $project = Join-Path $resolvedSmoke $agent
        New-Item -ItemType Directory -Path $project | Out-Null
        & $git -C $project init -q
        if ($LASTEXITCODE -ne 0) { throw "git init failed for $agent" }
        Push-Location $project
        try {
            & $skills add $repoRoot --agent $agent --copy -y
            if ($LASTEXITCODE -ne 0) { throw "skills install failed for $agent" }
        } finally {
            Pop-Location
        }
        $count = @(Get-ChildItem -LiteralPath $project -Recurse -File -Filter SKILL.md).Count
        if ($count -ne 14) { throw "$agent installed $count SKILL.md files; expected 14" }
        Write-Host "OK $agent installed 14 skills in isolated Windows project"
    }

    $negative = Join-Path $resolvedSmoke 'chatgpt-negative'
    New-Item -ItemType Directory -Path $negative | Out-Null
    & $git -C $negative init -q
    Push-Location $negative
    try {
        $output = (& $skills add $repoRoot --agent chatgpt --copy -y 2>&1 | Out-String)
        $exitCode = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($exitCode -eq 0 -or $output -notmatch 'Invalid agents:\s*chatgpt') {
        throw "ChatGPT negative control did not fail as documented. Output: $output"
    }
    Write-Host 'OK chatgpt remains an unsupported npx target (expected negative control)'
    Write-Host 'WINDOWS AGENT SMOKE PASSED'
} finally {
    if (Test-Path -LiteralPath $resolvedSmoke) {
        $finalPath = [IO.Path]::GetFullPath($resolvedSmoke)
        if ($finalPath.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase) -and
            (Split-Path -Leaf $finalPath) -match '^astromech-agent-smoke-[0-9]+-[0-9a-f]{32}$') {
            Remove-Item -LiteralPath $finalPath -Recurse -Force
        } else {
            Write-Warning "Refusing to remove unexpected path: $finalPath"
        }
    }
}
