[CmdletBinding()]
param(
    [ValidateSet('codex', 'claude-code')]
    [string[]]$Agents = @('codex', 'claude-code'),
    [switch]$AllowModelUse,
    [ValidateRange(30, 600)]
    [int]$TimeoutSeconds = 120
)

$ErrorActionPreference = 'Stop'
if (-not $AllowModelUse) {
    throw 'This smoke makes one live model call per selected agent. Re-run with -AllowModelUse after reviewing the cost boundary.'
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$git = (Get-Command git -ErrorAction Stop).Source
$pwsh = (Get-Command pwsh -ErrorAction Stop).Source
$skills = Join-Path $repoRoot 'node_modules\.bin\skills.cmd'
if (-not (Test-Path -LiteralPath $skills -PathType Leaf)) {
    throw 'Pinned skills CLI is missing. Run npm ci --ignore-scripts first.'
}

$prompt = @'
Use the project skill $damage-report. First locate and read its SKILL.md with the available skill discovery/read tools. Start the final answer with exactly:
ASTROMECH_RUNTIME_OK: damage-report
Then reproduce the five numbered development-review question headings from that skill in Traditional Chinese. You may read the skill instructions, but do not modify files.
'@

function Invoke-BoundedProcess {
    param(
        [Parameter(Mandatory)][string]$Command,
        [Parameter(Mandatory)][string[]]$Arguments,
        [Parameter(Mandatory)][string]$WorkingDirectory,
        [Parameter(Mandatory)][int]$Timeout
    )

    $payload = @{ command = $Command; arguments = $Arguments } | ConvertTo-Json -Compress
    $payload64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($payload))
    $runner = @"
`$payload = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('$payload64')) | ConvertFrom-Json
& `$payload.command @(`$payload.arguments)
if (`$null -ne `$LASTEXITCODE) { exit `$LASTEXITCODE }
"@
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($runner))
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $pwsh
    $start.WorkingDirectory = $WorkingDirectory
    $start.UseShellExecute = $false
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    [void]$start.ArgumentList.Add('-NoProfile')
    [void]$start.ArgumentList.Add('-NonInteractive')
    [void]$start.ArgumentList.Add('-EncodedCommand')
    [void]$start.ArgumentList.Add($encoded)
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    [void]$process.Start()
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($Timeout * 1000)) {
        $process.Kill($true)
        $process.WaitForExit()
        throw "Process timed out after $Timeout seconds: $Command"
    }
    [pscustomobject]@{
        ExitCode = $process.ExitCode
        StdOut = $stdoutTask.GetAwaiter().GetResult()
        StdErr = $stderrTask.GetAwaiter().GetResult()
    }
}

function Assert-DamageReportDiscovery {
    param(
        [Parameter(Mandatory)][string]$Text,
        [bool]$RequireSentinel = $true
    )
    if ($RequireSentinel -and $Text -notmatch 'ASTROMECH_RUNTIME_OK:\s*damage-report') {
        throw 'Runtime output omitted the required discovery sentinel.'
    }
    foreach ($number in 1..5) {
        if ($Text -notmatch "(?m)^\s*$number[.)、．]\s*") {
            throw "Runtime output omitted numbered damage-report item $number."
        }
    }
}

function Assert-DamageReportConcepts {
    param([Parameter(Mandatory)][string]$Text)
    $patterns = @(
        '原本.*問題|問題.*原本',
        '越界|範圍|不該',
        '生效|有效',
        '驗證|證據|測試',
        '誰在用|使用者|使用的人|交付'
    )
    foreach ($pattern in $patterns) {
        if ($Text -notmatch $pattern) {
            throw "Runtime output omitted a damage-report concept: $pattern"
        }
    }
}

$tempBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
$smokeRoot = Join-Path $tempBase ("astromech-runtime-smoke-{0}-{1}" -f $PID, [guid]::NewGuid().ToString('N'))
$resolvedSmoke = [IO.Path]::GetFullPath($smokeRoot)
if (-not $resolvedSmoke.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase) -or
    (Split-Path -Leaf $resolvedSmoke) -notmatch '^astromech-runtime-smoke-[0-9]+-[0-9a-f]{32}$') {
    throw "Unsafe smoke path: $resolvedSmoke"
}

$results = @()
New-Item -ItemType Directory -Path $resolvedSmoke | Out-Null
try {
    foreach ($agent in $Agents) {
        $project = Join-Path $resolvedSmoke $agent
        New-Item -ItemType Directory -Path $project | Out-Null
        & $git -C $project init -q
        if ($LASTEXITCODE -ne 0) { throw "git init failed for $agent" }
        Push-Location $project
        try {
            & $skills add $repoRoot --agent $agent --skill damage-report --copy -y
            if ($LASTEXITCODE -ne 0) { throw "skills install failed for $agent" }
        } finally {
            Pop-Location
        }
        $installed = @(Get-ChildItem -LiteralPath $project -Recurse -File -Filter SKILL.md)
        if ($installed.Count -ne 1 -or $installed[0].Directory.Name -ne 'damage-report') {
            throw "$agent did not install exactly one damage-report skill"
        }

        if ($agent -eq 'codex') {
            $command = (Get-Command codex.exe -ErrorAction Stop | Select-Object -First 1).Source
            $auth = Invoke-BoundedProcess -Command $command -Arguments @('login', 'status') -WorkingDirectory $project -Timeout 30
            $authText = $auth.StdOut + $auth.StdErr
            if ($auth.ExitCode -ne 0 -or $authText -notmatch 'Logged in') {
                throw 'Codex is not logged in; no model call was made.'
            }
            $answer = Join-Path $project 'codex-answer.txt'
            $call = Invoke-BoundedProcess -Command $command -Arguments @(
                'exec', '--json', '-s', 'read-only', '--skip-git-repo-check', '--ephemeral',
                '-C', $project, '-o', $answer, $prompt
            ) -WorkingDirectory $project -Timeout $TimeoutSeconds
            if ($call.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $answer -PathType Leaf)) {
                throw "Codex runtime smoke failed with exit code $($call.ExitCode)."
            }
            if ($call.StdOut -notmatch 'damage-report' -or $call.StdOut -notmatch 'SKILL\.md') {
                throw 'Codex runtime events did not prove that damage-report/SKILL.md was discovered and read.'
            }
            $text = Get-Content -LiteralPath $answer -Raw -Encoding UTF8
            Assert-DamageReportDiscovery -Text $text -RequireSentinel $true
            $version = (Invoke-BoundedProcess -Command $command -Arguments @('--version') -WorkingDirectory $project -Timeout 30).StdOut.Trim()
        } else {
            $command = (Get-Command claude.cmd -ErrorAction Stop | Select-Object -First 1).Source
            $auth = Invoke-BoundedProcess -Command $command -Arguments @('--setting-sources', 'project', 'auth', 'status') -WorkingDirectory $project -Timeout 30
            $authText = $auth.StdOut + $auth.StdErr
            if ($auth.ExitCode -ne 0 -or $authText -notmatch '"loggedIn"\s*:\s*true') {
                throw 'Claude Code is not logged in; no model call was made.'
            }
            $claudePrompt = @'
/damage-report

For this isolated runtime smoke, reproduce the five numbered development-review question headings from the skill in Traditional Chinese. Do not modify files.
'@
            $call = Invoke-BoundedProcess -Command $command -Arguments @(
                '--setting-sources', 'project', '-p', '--permission-mode', 'plan',
                '--tools', 'Skill,Read', '--no-session-persistence', '--output-format', 'json',
                '--max-budget-usd', '0.50', '--model', 'haiku', $claudePrompt
            ) -WorkingDirectory $project -Timeout $TimeoutSeconds
            if ($call.ExitCode -ne 0) {
                try {
                    $failure = $call.StdOut | ConvertFrom-Json -ErrorAction Stop
                    $errorKinds = @($failure.errors) -join '; '
                    $deniedTools = @($failure.permission_denials.tool_name | Sort-Object -Unique) -join ','
                    throw "Claude Code runtime smoke failed: subtype=$($failure.subtype); errors=$errorKinds; denied_tools=$deniedTools"
                } catch {
                    if ($_.Exception.Message -like 'Claude Code runtime smoke failed:*') { throw }
                    throw "Claude Code runtime smoke failed with exit code $($call.ExitCode); diagnostic JSON was unavailable."
                }
            }
            try {
                $text = ($call.StdOut | ConvertFrom-Json -ErrorAction Stop).result
            } catch {
                throw 'Claude Code runtime smoke did not return valid JSON.'
            }
            Assert-DamageReportConcepts -Text $text
            $version = (Invoke-BoundedProcess -Command $command -Arguments @('--version') -WorkingDirectory $project -Timeout 30).StdOut.Trim()
        }

        $results += [ordered]@{
            agent = $agent
            version = $version
            package = 'passed'
            discovery = 'passed'
            runtime = 'passed'
        }
        Write-Host "OK $agent package + discovery + one bounded runtime call"
    }

    $head = (& $git -C $repoRoot rev-parse HEAD).Trim()
    [ordered]@{
        schema_version = 1
        observed_at_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        repo_head = $head
        results = $results
    } | ConvertTo-Json -Depth 5
    Write-Host 'WINDOWS RUNTIME SMOKE PASSED'
} finally {
    if (Test-Path -LiteralPath $resolvedSmoke) {
        $finalPath = [IO.Path]::GetFullPath($resolvedSmoke)
        if ($finalPath.StartsWith($tempBase, [StringComparison]::OrdinalIgnoreCase) -and
            (Split-Path -Leaf $finalPath) -match '^astromech-runtime-smoke-[0-9]+-[0-9a-f]{32}$') {
            Remove-Item -LiteralPath $finalPath -Recurse -Force
        } else {
            Write-Warning "Refusing to remove unexpected path: $finalPath"
        }
    }
}
