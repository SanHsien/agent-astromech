# Windows AI Desktop／TUI／CLI 開發與驗收

本 fork 把 Windows 原生的 AI Desktop、TUI 與 CLI 都視為一級開發環境。不同產品的 skill 能力不相同，因此驗收分成 package、discovery、trust 與 runtime 四層；其中一種介面安裝成功，不能直接替另一種介面宣稱可用。

最近一次逐層結果與 exact-SHA 證據見 [`WINDOWS-RUNTIME-EVIDENCE.md`](WINDOWS-RUNTIME-EVIDENCE.md)。

## 共用 package 層

```powershell
pwsh -NoProfile -File tools\windows_agent_smoke.ps1
```

腳本只在 Windows 系統暫存目錄建立唯一 Git project，以 `--copy` 分別安裝 Codex 與 Claude Code target，核對各有 10 份 `SKILL.md`，再驗證 ChatGPT target 的預期失敗。它不修改 user-level skills、不啟動模型，也不消耗模型用量。

## Codex for Windows

- `npx skills add <repo> --agent codex -y` 建立 project-level `.agents/skills/`。
- package smoke 驗證檔案結構；model-visible discovery 必須分別在實際 Codex Desktop、Windows TUI 或 Windows CLI task 中抽測。
- 各介面可能有不同的 workspace、trust、hook 或 PATH 狀態；證據分開記錄，不互相替代。

## Claude for Windows

- `npx skills add <repo> --agent claude-code -y` 驗證 Claude Code project skill 格式，供 Windows TUI／CLI 工作流使用。
- plugin 路徑使用 `/plugin marketplace add SanHsien/agent-astromech`；這是 Claude Code／Cowork 能力，不代表所有 Claude Desktop 對話都能讀本機 skill。
- 不反向覆蓋既有 user-level 同名私人 skills；需要並存時使用 plugin namespace。

## ChatGPT Desktop for Windows

ChatGPT 消費版沒有 `npx skills` 的 `chatgpt` agent target；負向測試應回報 `Invalid agents: chatgpt`。使用 [`adapters/openai/README.md`](../adapters/openai/README.md) 的 prompt／手動移植方式，不宣稱具備本機 shell 或共享檔案系統。

## 其他 Windows TUI／CLI

Cursor、Gemini CLI、GitHub Copilot 或未來新增的 Windows TUI／CLI，可先用 `npx skills add <repo> --agent <name> --copy -y` 驗 package 層，再分別檢查 trusted-folder、project scope、prompt discovery 與一次低風險 trigger。未實測的宿主保持 `unknown`，不能從相同檔案格式推論 runtime 支援。

## Linux CI 的角色

Linux 不是本 fork 的主要互動開發介面；CI 只補驗 Git Bash／NTFS 無法證明的 POSIX mode bit、5-shell 行為與 workflow 一致性。Windows gate 仍是本機 canonical entrypoint。

## 高成本抽測停止條件

每個 release 對每個宣稱支援的 Windows 宿主最多做一次低風險抽測；取得「安裝 artifact、discovery/trust、實際產出」三層證據後立即停止。登入或 trust 必須由使用者完成時，只交接必要動作，完成後從現有狀態續驗。

CLI runtime 抽測必須由維護者明確加 `-AllowModelUse`，預設不消耗額度：

```powershell
pwsh -NoProfile -File tools\windows_runtime_smoke.ps1 -AllowModelUse
```

這個結果只證明被選取 CLI 的 package、model-visible discovery 與 runtime engine；不替 Desktop 或互動 TUI 的 workspace／trust／UI 宣稱成功。
