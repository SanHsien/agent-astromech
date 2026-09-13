# AGENTS.md

本檔提供 Codex、Claude Code、Cursor 與其他自動化代理在本 fork 工作時的共同指引。產品規格先讀 [`README.md`](README.md) 與 [`CLAUDE.md`](CLAUDE.md)；開發與驗收細節見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。

## 專案定位

本 repo 源自 [`tingyulu/MyR2D2`](https://github.com/tingyulu/MyR2D2) 的 MIT 維護型 fork：

- `origin`：`SanHsien/agent-astromech`
- `upstream`：`tingyulu/MyR2D2`
- 預設分支：`main`
- Windows 權威入口：`pwsh -NoProfile -File tools\dev_check.ps1`
- Linux／macOS 入口：`sh tools/dev_check.sh`

主要開發平台是 Windows 11；Codex／Claude 等 Windows Desktop、Windows TUI 與 Windows CLI 都是一級宿主。Git Bash 只提供必要的 POSIX shell 相容層，Linux CI 補驗 POSIX 權限與多 shell 語義。

專案名稱為 agent-astromech、保留上游作者歸屬、上游 12 支 skill（fork 另加 `recap`、`blind-review`，共 14 支）、公開介面與 MIT 授權。fork 的維護差異記在 [`FORK.md`](FORK.md)、[`docs/DECISIONS.md`](docs/DECISIONS.md) 與 [`docs/UPSTREAM.md`](docs/UPSTREAM.md)。

## 硬性邊界

- 遵守 `CLAUDE.md` 的去識別化、SKILL.md 格式、連動清單、版號與本機安裝隔離規則。
- 不提交 API key、token、cookie、帳號資料、私人 prompt、真實客戶資料或 `.ai-reviews/` 產物。
- 跨模型 review 前先去識別化；送給後端的內容視為已離開本機信任邊界。
- 不把 Git Bash／NTFS 的 mode-bit 顯示當成 POSIX 權限證據。`0600` 安全斷言由 Linux CI 驗證。
- 不對 `main` force-push，不刪除 `upstream` remote，不盲目 merge upstream。
- 不新增 CHANGELOG；版本與 release 慣例沿用 `CLAUDE.md`。

## 開發方式

- 維護者的日常變更直接推 `origin/main`，不開功能分支、不開維護 PR（2026-08-24 起，全庫一致）。只有在需要他人審查、或改動風險高到值得先讓 CI 在 PR 上跑一輪時，才退回 **branch → PR → required checks → merge**。外部貢獻一律走 PR。
- 分支保護仍擋 force-push 與刪分支，且對走 PR 的路徑要求 required checks；`enforce_admins` 為 false，所以維護者直推 `main` 不受阻。
- **直推一樣會跑 CI**（`ci.yml` 同時掛 `push: [main]` 與 `pull_request`），差別在**時機**：走 PR 時 CI 在合併前跑、紅燈擋住合併；直推時 CI 在 commit 已經落在 `main` 之後才跑，紅燈只會留下一條壞掉的 `main`。所以**直推前要在本機跑完 `tools\dev_check.ps1`**——那才是取代「合併前那道閘」的東西。
- whitespace gate 兩條路徑都覆蓋整個引入範圍：PR 用合併目標，直推用 `github.event.before`（推送前 `main` 的 tip），所以一次推多個 commit 時中間那幾個也會被檢查。範圍以 merge-base 為錨（force push 後 `before` 不是祖先），沒有可用 base 時（分支首次推送，`before` 是全零）退回只檢查 tip 並印出原因。兩個 job 的 checkout 因此都要 `fetch-depth: 0`——預設深度 1 拿不到 base commit。
- **合併任何 PR（含 Dependabot）前先讀完整 diff**：`gh pr diff <編號>`。CI 綠燈證明的是「測試沒紅」，不是「改了什麼、該不該進 `main`」——lockfile 的連鎖升級、跨出宣告範圍的變更，只有讀 diff 看得到。核准或合併訊息要寫出讀到什麼、為什麼可接受。
- commit 使用 Conventional Commits，例如 `chore: add Windows development gate`。
- 修 bug 先建立可重現測試，再做最小修正。
- 改 skill 時必須同步檢查兩份 README、plugin metadata、adapter 與 `docs/TEST_PLAN.md`。
- `README.md` 與 `README.en.md` 行數必須一致。

## 上游同步

1. `git fetch upstream main`
2. `python tools/check_upstream_updates.py --strict`
3. 逐筆檢查 commit、PR、issue 與 branch head。
4. 把採用／略過／延後的證據寫入 `docs/UPSTREAM.md` 與 `docs/DECISIONS.md`。
5. 跑完整 gate 後才更新 `tools/upstream_baseline.json`。

Baseline 只表示「已審查」，不表示「全部已合併」。

## 依賴新鮮度

`dependency-freshness` 每月 1 日跑一次（可手動觸發），比對 `package.json` 宣告與 npm registry，並帶 `npm audit`。它只讀，不安裝也不改 manifest；有落後或漏洞就讓 run 紅燈並把報告寫進 step summary，與 `upstream-check` 同一條通知路線。

已評估但這次不升的，寫進 `.github/dependency-deferrals.json`：記下**當時判斷的版本**與理由。上游一發佈更新的版本，deferral 自動失效、項目回到報告裡。**不准用調高版本宣告來消音**——那是把相容性宣告當關掉警報的開關。

## 對外邊界

- PR、push、release 一律指向 `SanHsien/agent-astromech`。
- 未經維護者在當次對話明確同意，不得對 `tingyulu/MyR2D2` push、開 PR、發 release 或觸發 workflow。
- 每個 clone 先執行 `gh repo set-default SanHsien/agent-astromech`，並以 `gh repo set-default --view` 核對。
- 建立 PR 時仍須明寫 `--repo SanHsien/agent-astromech`，並檢查輸出 URL 的 owner。

## 完成條件

```powershell
pwsh -NoProfile -File tools\dev_check.ps1
git diff --check
git status --short
```

沒有實際跑過 gate、檢查完整 diff 與遠端 exact SHA，不宣稱完成。
