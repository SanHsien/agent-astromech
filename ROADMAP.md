# 路線圖

> 本 repo 後續工作的單一真相源。做完一項，就在同一個 commit 刪掉那一列；新工作只加在這裡。
> 現況段的數字是 2026-10-29 依 `main` `794dbcbfbb27` 查的快照，開工前先重查 GitHub。

## 現況

維護型 fork（上游 `tingyulu/MyR2D2`，審查水位 `32bef4ecbedf`，見 `tools/upstream_baseline.json`）：繁中 Agent Skills 與跨模型二審 `ai-review`，補上 Windows canonical gate 與治理文件；2026-10-24 歷史已壓成單一 commit，與上游無共同祖先是已知事實，不是缺陷。健康：2026-10-29 查到 open issue 0、open PR 0、Dependabot 與 Code scanning 告警各 0，`CI`、`CodeQL`、`Dependency freshness`、`Upstream check` 在 `main` 最近一次皆 success（2026-10-29 `gh` 查詢）；最近 release 為 v0.9.1（2026-09-11），之後的 `ai-review` 與 freshness 修正尚未發版。

## 近期：可以直接動手
| 項目 | 為什麼 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 為 `ai-review` 的 `AI_REVIEW_CMD` 逾時改為連孫行程一起終止，或在 `SKILL.md` 明寫限制 | 目前逾時只殺 `sh -c`，孫行程可能殘留；使用者看不到這個限制 | 二擇一：(a) matrix 新增「逾時後無殘留行程」情境且 Linux CI 綠；(b) `skills/ai-review/SKILL.md` 與 `docs/TEST_PLAN.md` 寫明並由 contract checker 釘住；Windows `dev_check.ps1` 同樣綠 | Claude Opus | 深掃報告（2026-10-26）「刻意不修／觀察」；`skills/ai-review/` |

## 中期：等條件成立再做
| 項目 | 觸發條件 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 同步上游新 commit | `Upstream check` workflow 在 `main` 轉為 failure（代表上游有未審項目），或週期性檢查發現上游前進 | 逐筆判斷 adopt／defer／skip，寫進 `docs/UPSTREAM.md`；`python tools/check_upstream_updates.py --strict` exit 0；完整 gate 通過後才推進 `tools/upstream_baseline.json`；`FORK.md`「同步方法」被遵守 | Claude Sonnet | `tools/upstream_baseline.json`；`docs/UPSTREAM.md`；`Upstream check` workflow 結果（見現況段） |
| 評估採納上游 `systems-check` 與 tag 版號 CI 步驟 | 上游修好 Windows 相容（`import fcntl`），或維護者決定由本 fork 自行改寫為跨平台並補 Windows 測試 | 在 Windows 原生 `selfcheck_scan.py --selftest` 全過；skill 計數、README 雙語、plugin metadata、adapter、TEST_PLAN、contract checker 一致連動；`dev_check.ps1` 綠 | Claude Opus | `docs/UPSTREAM.md:129`、`:130`；`docs/DECISIONS.md:160` |
| 發布下一個 release | 維護者決定要固定一個可回溯版本（v0.9.1 之後已有 `ai-review` watchdog 與 freshness 修正） | `plugin.json` 版號與 tag 一致；`gh release list --repo SanHsien/agent-astromech` 出現新版；發版前 `dev_check` 與 CI 綠 | 維護者 | `gh release list --repo SanHsien/agent-astromech`；`.claude-plugin/plugin.json:4` |
| 自行重跑 CROSS-01 per-agent 驗證 | 維護者需要對外宣稱 14 支 skill 的跨 agent 相容數字 | `docs/TEST_PLAN.md` 記錄以本 fork 14 支 working tree 實測的數字、日期與 agent 版本，不與上游 12 支數字相加 | 維護者 | `docs/UPSTREAM.md` 2026-09-05 段 `73d79e4` 列（defer） |

## 刻意不做
| 不做什麼 | 理由 | 什麼情況下重新考慮 |
| --- | --- | --- |
| 對上游提 PR、issue 或留言（含上游的跨午夜行小缺口） | 所有對外寫入只指向 `SanHsien/agent-astromech`，回貢需維護者當次對話明確授權 | 維護者在對話中明說要回貢上游 |
| 改寫歷史或強推以接回上游祖先 | 2026-10-24 單一 commit 是既定做法，要同步靠逐筆審查而非 merge | 不重新考慮 |
| 為 `blind-review` 補免安裝簡版 | 它的核心是「攻擊者拿不到對話」的操作安排，不是可貼進常駐欄的規則 | README 相容性矩陣把它改標為規則類 |
| 處理 `harvest.py` DST 日邊界偏一小時 | 上游同樣寫法，台灣無 DST，Windows 單元測試無法切換時區重現 | 維護者的環境改到有 DST 的時區 |

## 維護方式

fork：上游審查依 `FORK.md`「同步方法」逐筆判斷，決策先寫 `docs/UPSTREAM.md`，gate 通過才推進水位；`Upstream check` 轉紅就是有新項目待審，不是工具壞。依賴由 Dependabot 與 `Dependency freshness` 追蹤，不靠拉高下限消紅燈；在 `main` 直推前跑 `tools\dev_check.ps1`。
