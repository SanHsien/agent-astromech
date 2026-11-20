# Repository review ledger

本檔只保留最新一輪審查（latest-only）。前一輪（2026-08-24 全量審查，R-01～R-11，全數已修）見 git 歷史中本檔的前一版。

## 2026-11-20／21：增量審查（`c769863..29d88b7`）

### 範圍與基準

- 範圍：`git diff c769863..29d88b7`，13 個 commit、29 檔（略過 lockfile；文件只看宣稱行為的段落）。
- 方法：唯讀審查加合成 fixtures 重現（harvest 跨午夜與亂序、watchdog 孤兒行程、npm 壞 registry 探測）。沒有讀真實 transcript。
- 結論：無 P0／P1。confirmed 4（F-8 經獨立驗收由 needs_validation 升級）、hardening 3、needs_validation 1。

### Findings 與處理

| ID | 類別 | Finding | 處理 |
|---|---|---|---|
| F-1 | confirmed，P3 | `harvest.py`：跨午夜回應的後續行只有 `requestId`、沒有 `message.id` 時，前後兩天各算一次（`pre_ids` 只收 id、翌日分支只認 id）。 | ✅ 已修 `020134b`（2026-11-21）。兩趟掃描：第一趟建 requestId→id 對照並求每則回應最早的時間戳，第二趟只在那一天計入、四欄取最大。回歸：`test_requestid_only_continuation_not_recounted_next_day`。 |
| F-2 | confirmed，P3 | `harvest.py`：去重依賴檔案行序；翌日行排在前面時同一則回應兩天都算，且 output 沒取到最大值（R-01 的回歸）。 | ✅ 已修 `020134b`（2026-11-21），與 F-1 同一個設計。回歸：`test_midnight_straddle_independent_of_line_order`（三行的六種行序結果一致）。 |
| F-3 | confirmed，P3，文件 | `token-optimizer` §1 第 1 條說 Agent tool 沒有 `effort` 參數，與目前宿主不符。 | ✅ 已修 `14e53b5`（2026-11-21）。改寫成隨宿主 CLI 版本而異，說明何時才設、fork 忽略、省略時繼承什麼。 |
| F-4 | hardening，P3 | `ai-review.sh` watchdog：每次執行（含成功）都留下 watcher 的孤兒 `sleep <timeout>`。 | ✅ 已修 `e480e3a`（2026-11-21）。watcher 改為對 deadline 每秒輪詢、命令結束自行退出，呼叫端 wait 而不 kill；先試過 TERM trap 殺 sleep，Git Bash 壓測 25 次仍漏 3～4 支（訊號競態），故不採用。回歸：矩陣新增「watchdog：命令結束後沒有殘留 sleep 行程」，bash／dash 修前皆 FAIL、修後皆過。順手修正矩陣計數 46→52（watchdog 測項加入時已漂移）。 |
| F-5 | hardening，P3 | `check_dependency_freshness.py`：兩個 pre-release 不排序，`2.0.0-rc.1` 對 latest `2.0.0-rc.2` 被標成 Ahead 並靜音。 | ✅ 已修 `c0039a3`（2026-11-21）。依 SemVer 2.0.0 §11 逐段比較。回歸：`test_older_prerelease_behind_newer_prerelease_is_maintenance`、`test_newer_prerelease_ahead_of_older_prerelease_stays_quiet`、`test_prerelease_precedence_follows_semver_section_11`。 |
| F-6 | hardening，P3，既有 | 本機沒有 `node_modules` 時 `npm outdated` 回 `{}`／rc 0，報告寫「Everything is current」。 | ✅ 已修 `c0039a3`（2026-11-21）。manifest 有宣告依賴卻沒有安裝時回報 check error。回歸：`test_missing_node_modules_is_reported_unchecked_not_current`。 |
| F-7 | needs_validation | Git Bash 下「自訂後端逾時→failed_timeout」偶發判成 `failed_network`（高負載時 1 次，單獨重跑 3/3 過）。走 coreutils `timeout` 路徑，不在本次 diff。 | ⏳ 未修，未查到根因。本輪修正後的兩次 dev_check 與 bash／dash 矩陣都沒有重現。再出現時保存完整矩陣輸出與當下負載再查。 |
| F-8 | confirmed，P3（原 needs_validation） | harvest 的去重範圍是單一 jsonl；resume 會把舊訊息（同 `message.id`）複寫進新 session 檔，同一則回應在兩個 session 各算一次。獨立驗收以本機資料證實：最近 300 個 transcript 的 44,589 個 message.id 中有 5,570 個（約 12%）出現在不只一個檔。 | ✅ 已修 `8285d2e`（2026-11-21）。第一趟改為掃完全部檔案，記下每個 id 最早出現的檔與時間；該檔、該日擁有這則回應，其他檔的副本整行不算、只把用量併過去取最大。本機 3.8 GB 語料執行時間與修前相當。回歸：`test_response_copied_into_resumed_session_counted_once`、`test_copied_response_stays_on_its_earliest_day_across_files`（修前皆失敗）。save-all 只讀目前 session 的單一檔，沒有跨檔重複；但 resume 後的檔含複寫來的舊回應，它的「session 累計」要不要排除這些副本，本輪未處理。 |

### 驗收清冊

- `python -X utf8 skills/mission-log/tests/harvest_test.py`：24 項全過（修前新增項失敗：F-8 兩項；F-1 得 18 而非 63；F-2 六種行序皆錯）。
- `python -X utf8 -m unittest discover -s tests -p "test_*.py"`：全過（修前 F-5 三項、F-6 一項失敗）。
- `SH=bash|dash sh skills/ai-review/tests/matrix.sh`：51 過／0 失敗／1 略過（修前兩個 shell 都是殘留 sleep 那項 FAIL）。
- `pwsh -NoProfile -File tools\dev_check.ps1`：exit 0。

### 未能檢查

- Linux 5-shell（ksh／zsh／yash）與 macOS 真機的新 watchdog：只在 Windows Git Bash 跑了 bash／dash，Linux 由 CI 驗。
- 真實 transcript 中「沒有 id、只有 requestId」的行有多常見。
