# 開發環境

agent-astromech 的產品本體是 Markdown、POSIX shell 與一個標準庫 Python 收割器。開發環境的目標是重現公開契約，不建立不必要的套件層。

## Windows 11

必要工具：

- PowerShell 7
- Git for Windows（含 Git Bash）
- Python 3.11+
- Node.js 22.20+／npm（lockfile 釘住 `skills` 與 `skills-ref`）

在 repo 根目錄執行：

```powershell
pwsh -NoProfile -File tools\dev_check.ps1
```

PowerShell gate 會執行 repo contract、upstream checker tests、兩個可用 shell 的 `ai-review` 矩陣、mission-log 測試、skills validator、隔離式 Codex／Claude Code package smoke 與 Git whitespace 檢查。它不呼叫模型；需要 release 級 runtime 證據時，另以明確的 `-AllowModelUse` 執行 `tools\windows_runtime_smoke.ps1`。

Git Bash 位於 NTFS 時不具 POSIX mode-bit 語義，因此 `0600` 顯示檢查會明確標成一項平台 skip；其他案例仍須通過。Linux CI 會執行沒有 skip 的完整 5-shell 矩陣。

## Linux／macOS

需要 `python3`、Node.js／npm、Ruby，以及 `sh`、`bash`、`dash`、`ksh`、`zsh`：

```bash
sh tools/dev_check.sh
```

缺少必要 shell 時 gate 會失敗並列出缺項，不會把未執行宣稱為成功。

## 常用聚焦檢查

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python skills/mission-log/tests/harvest_test.py
SH=bash sh skills/ai-review/tests/matrix.sh
npm ci --ignore-scripts --no-audit --no-fund
for d in skills/*/; do ./node_modules/.bin/skills-ref validate "$d"; done
```

## 修改連動

改任何 skill 前先讀 `CLAUDE.md` 的連動清單。README 雙語行數、plugin metadata、adapter、測試計畫與 skill 計數都屬公開契約。

## 遠端驗證

維護者的日常變更直接推 `origin/main`，只有需要他人審查或高風險改動才走 branch → `SanHsien/agent-astromech` PR → required checks → merge；外部貢獻一律走 PR。直推一樣會觸發 CI（`ci.yml` 同時掛 `push: [main]` 與 `pull_request`），差別在時機：走 PR 時紅燈擋住合併，直推時 CI 在 commit 已經落在 `main` 之後才跑，紅燈只會留下壞掉的 `main`。**推之前要在本機跑完 `tools\dev_check.ps1`**——那是取代「合併前那道閘」的東西。whitespace gate 在兩條路徑都檢查整個引入範圍（PR 用合併目標，直推用 `github.event.before`），以 merge-base 為錨，沒有可用 base 時退回只檢查 tip 並印出原因。推送或合併後以 exact SHA 核對 GitHub Actions，不要只看「最近一次」綠燈。上游審查方式見 [`UPSTREAM.md`](UPSTREAM.md)。

各 Windows AI Desktop／TUI／CLI 的能力與抽測邊界見 [`WINDOWS-AI-ENVIRONMENTS.md`](WINDOWS-AI-ENVIRONMENTS.md)。
最近一次完整 repository review、finding 與殘餘風險見 [`REVIEW.md`](REVIEW.md)。
