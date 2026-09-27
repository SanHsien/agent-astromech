# Repository review ledger

## 2026-08-24：Windows-first 維護型 fork 全量審查

### 範圍與基準

- 起始 candidate：`d3026af668b1b9ec40f74351eb9b53678cc8851a`。
- 範圍：所有 tracked files、Windows／POSIX gates、Python／shell／PowerShell 行為、GitHub Actions、npm supply chain、文件契約、upstream 邊界與 GitHub repo 設定。
- 方法：人工逐檔與資料流審查、合成 regression fixtures、relative-link scan、敏感內容篩查、`npm audit`、canonical gates、主代理二次 diff review 與 exact-SHA GitHub workflow 驗證。
- 限制：沒有送出 repo 真實內容做 live LLM review；只用合成題頭做 Windows CLI 抽測。Desktop 與互動 TUI 仍維持獨立 `unknown`，不以 CLI 證據替代。

### Findings 與處理

| ID | 嚴重度 | Finding | 處理與回歸證據 |
|---|---|---|---|
| R-01 | P1 | `mission-log` 信任檔案 mtime 與 transcript 時序；搬移、還原或亂序資料會安靜漏掉指定日活動。 | 移除兩個不可靠的提早略過條件；新增 old-mtime 與 out-of-order fixtures。 |
| R-02 | P1 | 合法但非 object 的 JSON、非預期 optional field 或不含 `-` 的 model 名會讓收割器崩潰。 | 非 object 行改為略過；cwd、branch、usage、model、tool name 做型別邊界；新增 malformed-fields、plain-model fixtures。 |
| R-03 | P2 | 同專案兩個 transcript 若前八碼相同會被合併，造成 session 與 token 數錯誤。 | 聚合 key 改用完整檔名，輸出使用最短可區分前綴；新增 collision fixture。 |
| R-04 | P2 | upstream 發生 rewrite／diverge 且 compare 沒有 commit 時，報告會把 merge-base 誤寫成 current head。 | current head 改由 branches API 的 default branch 取得；新增 rewritten-branch fixture。 |
| R-05 | P2 | 測試計畫仍複製舊 gate、使用浮動 npm 指令；README 行數與 lockfile 決策文件也已漂移。 | 測試計畫改指向 canonical scripts 與 locked CLIs；同步 180 行與 Node lockfile 決策。 |
| R-06 | P2 | Dependabot 設定引用 `dependencies`、`github-actions`、`npm` labels，但遠端 repo 尚未建立。 | 在 `SanHsien/agent-astromech` 建立三個 labels；不對 upstream 寫入。 |
| R-07 | P3 | Actions 現在雖已釘 full SHA，repo contract 沒有阻止未來退回 major tag。 | contract 新增 workflow action full-SHA 規則與反例測試。 |
| R-08 | P1 | `ai-review` 後端沒有 wall-clock 上限，CLI 或自訂命令卡住會無界等待。 | 新增預設 600 秒的 `--timeout`／`AI_REVIEW_TIMEOUT_SECONDS`，涵蓋自訂後端、Codex 登入檢查與 review；三條逾時路徑及非法值納入矩陣（現為 46 項）。 |
| R-09 | P1 | Windows package smoke 被誤當成 Desktop／TUI／CLI runtime 證據。 | 新增需明確 `-AllowModelUse` 的有界 runtime smoke 與 evidence ledger；Codex CLI 三層通過，Claude Code 非互動 runtime 失敗並降級 README 宣稱，Desktop／TUI 保持 `unknown`。 |
| R-10 | P2 | `main` 可直接 push，canonical gates 只能靠操作者自律。 | 交付後啟用 admin 也不得 bypass 的 branch protection，要求 PR、strict required checks、conversation resolution、linear history，禁 force push／delete。 |
| R-11 | P2 | fork README 保留上游作者第一人稱自介與社群連結，會讓讀者誤認 repo owner 身分。 | 繁中／英文 README 同步刪除作者自介段；歸屬仍保留在 fork banner、`FORK.md`、`NOTICE.md` 與 `LICENSE`。 |

本輪沒有 P0 finding。上述 P1／P2 全部修正；P3 同步補上防回歸契約。

### 驗收清冊

- `python -X utf8 skills/mission-log/tests/harvest_test.py`：16 項 fixtures 全過。
- `python -X utf8 -m unittest discover -s tests -p "test_*.py" -v`：repo contract 與 upstream checker 全過。
- `pwsh -NoProfile -File tools\dev_check.ps1`：Windows canonical gate 必須全過。
- Linux CI：ai-review 5 shell × 46 項、ai-search 5 shell × 44 項、mission-log C locale、repo contract 必須全過。
- CodeQL（Actions／Python）、Upstream check、npm audit：必須全綠／0 vulnerabilities。
- local `HEAD`、`origin/main`、GitHub API main SHA：必須完全相同，worktree 必須 clean。

### 殘餘風險處置

- **已關閉：無界等待。** 內建 timeout 與三條 wiring 回歸案例已進 canonical gates；狀態明確為 `failed_timeout`。
- **已關閉：跨介面過度宣稱。** package、discovery、runtime、UI 分欄記錄；未通過的 Claude Code 非互動 runtime 與未測 Desktop／TUI 都不能顯示為支援。
- **已關閉：未保護 main。** `SanHsien/agent-astromech` 的 branch protection 隨本次交付啟用並由 GitHub API 回讀；required checks 綁 `ci`、`Windows AI environment gate`、`actions security scan`、`python security scan`。
- **審查限制，不列產品通過證據。** Agent Advisor 的 fresh reviewer thread 因宿主未暴露可驗證的 model／effort／sandbox metadata 而中止；其內容未被採信。主代理完成完整 diff review、canonical gates 與 exact-SHA 遠端驗證。
