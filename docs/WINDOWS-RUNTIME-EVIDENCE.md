# Windows AI runtime 驗證證據

本頁只記錄實際跑過的層級。`package`、`discovery`、`runtime` 與介面 UI 是四種不同證據；任何一欄未測都不得由其他欄推論。

## 可重現命令

零模型用量的 package gate：

```powershell
pwsh -NoProfile -File tools\windows_agent_smoke.ps1
```

明確允許模型用量後，每個選定宿主只做一次唯讀、僅可讀 skill、無 session 保存的低風險呼叫：

```powershell
pwsh -NoProfile -File tools\windows_runtime_smoke.ps1 -AllowModelUse
```

runtime 腳本使用 pinned `skills` CLI，只安裝 `damage-report` 到唯一暫存 Git project。Codex 的 skill discovery 是 lazy search，因此以 `exec --json` 工具事件證明代理確實找到並讀取 `damage-report/SKILL.md`；不使用會漏掉 lazy skills 的靜態 prompt dump，最終輸出另須含 sentinel 與五個編號項目。Claude Code 則由原生 `/damage-report` 接管，不保留外層 sentinel且會自行選擇 Markdown 格式，因此以原生 trigger 成功與五個專有概念（原始問題、越界、生效、驗證證據、使用／交付）判定。Codex 使用 read-only sandbox；Claude Code 使用 plan mode、僅開 `Skill,Read`、Haiku 與 USD 0.50 單次上限。兩者皆有 120 秒預設 timeout，取得一次有效證據後停止，最後安全刪除暫存 project。

## 最近一次實證

日期：2026-08-24（Windows 11 原生 PowerShell 7）。送測內容是合成的 `damage-report` 題頭，不含 repo 私密資料、帳號資料或客戶內容。

| 宿主 | 版本 | exact candidate | package | discovery | runtime | 判定 |
|---|---|---|---|---|---|---|
| Codex Windows CLI | 0.146.0 | `b9d7a13e86d4e5e5790d4f0e39fa1725125010ff` | passed | passed；JSON tool event 含 `damage-report/SKILL.md` | passed；read-only、五項輸出 | 支援 CLI runtime |
| Claude Code Windows CLI | 2.1.231 | `1474f81dcfdbd1504a87f3ce21b57b5d95e7ca28` | passed | partial；原生 `/damage-report` 有回應 | failed；未涵蓋完整五問契約 | 不宣稱非互動 runtime 支援 |

抽測過程也抓到三個驗證器問題並已修進工具：Codex skills 是 lazy search，不能用靜態 prompt dump 判斷；Codex 與 Claude 的明確觸發字分別是 `$damage-report`／`/damage-report`；Claude 原生 slash 輸出不能強迫沿用外層 sentinel。Claude 的失敗保留為 fail-closed，不靠放寬成「有文字就算過」消除紅燈。

## 介面邊界

| 宿主 | package | model-visible discovery | runtime engine | Desktop／TUI UI |
|---|---|---|---|---|
| Codex Windows CLI | passed | passed | passed | 不適用 |
| Claude Code Windows CLI | passed | partial | failed | 不適用 |
| Codex Desktop | 共用 `.agents/skills` 格式 | 未在獨立 Desktop task 驗證 | 不以 CLI 證據替代 | unknown |
| Codex Windows TUI | 共用 `.agents/skills` 格式 | 未在互動 TUI 驗證 | 不以 print/exec 證據替代 UI | unknown |
| Claude Desktop／Cowork | plugin/prompt 路徑另見環境文件 | 未在獨立 Desktop task 驗證 | 不以 Claude Code CLI 證據替代 | unknown |
| 其他 Windows TUI／CLI | 逐宿主另測 | unknown | unknown | unknown |

`unknown` 是刻意的支援邊界，不是成功。要把任一介面升為「已驗證」，必須留下版本、日期、exact repo SHA、package/discovery/runtime 結果與一次低風險實際產出；不得只貼安裝成功畫面。
