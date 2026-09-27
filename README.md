# agent-astromech 🤖

> 這是源自 [`tingyulu/MyR2D2`](https://github.com/tingyulu/MyR2D2) 的 Windows-first 維護發行版；差異、歸屬與同步方式見 [FORK.md](FORK.md)，開發入口見 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

### 你的隨行 astromech droid — Claude skillset（繁中本體、中英雙語觸發）

**繁體中文（本頁）| [English](README.en.md)**

---

Astromech 隨行機器人從來不是主角，但每場任務都靠它：把關鍵資料帶出來、在後座默默修飛船、對抗系統失憶、管理工作流能源。

agent-astromech 就是這個定位 —— 14 支 skills，管的都是「不做不會死、但做了整個工作流才活得下去」的事:

| Skill | 一句話 | Astromech 隱喻 |
|---|---|---|
| **save-all** | 收工/重開機前，把只活在對話裡的東西全部落地並**驗證**寫進磁碟 | 重要資料寫進核心、安全落地 |
| **dropoff** | 把一件事連同完整脈絡寫成交接卡推給另一個 session；對面在線就即時按門鈴 | 錄下任務交接卡、推給下一位 |
| **pickup** | 新 session 開場撈交接卡（或被門鈴叫醒），讀全文、認領、開工，做完回訊收尾 | 撈起交接卡、播放任務脈絡 |
| **recap** | 平行 session 太多記不住時的現況重述：先刷新可能過期的東西，再報目標／證據／卡點／下一步 | 投出來的不是回憶，是接上系統讀回來的當下座標 |
| **mission-log** | 零 token 收割任一天的 session 活動骨架（transcript 本來就在記，只差讀取器） | 飛行記錄器從不休息 |
| **daily-debrief** | 日結：做了什麼＋reflection，趕在 transcript 30 天蒸發前把價值撈上岸 | 任務歸來的 debrief |
| **weekly-debrief** | 週結：7 份日結收斂成主線與趨勢 | 看得出補給線問題的是戰役，不是單次任務 |
| **new-mission** | 開工簡報：先查再問（最多五題）、給計畫、送審、等明確的「做」才動手，順便產出可重用的任務 prompt；執行結束交對照計畫的收尾報告 | 投影作戰藍圖，團隊確認路線可行才升空 |
| **damage-report** | 收尾自檢五問：寫回報前先對照原始需求跑一輪；建議欄沒有就寫「無」 | 修完系統自己跑一輪診斷，主動回報損傷——不等呼叫 |
| **blind-review** | 派一個**沒看過對話**的子代理攻擊你的改動，主代理補上假設與設計決策，產出給人看的導讀 | 插進接口時沒讀過作戰簡報——讀的是儀表上真實亮著的燈 |
| **ai-review** | 把產出送給**另一個模型**二審，消化意見後才寫回報；沒有後端就明講「僅自審」 | 跟另一個模型吵了一整輪，每次都是對方補上你漏的那半 |
| **ai-search** | 問一句，回你**附來源、可複查**的即時答案；查不到就說查不到，不拿舊知識硬填 | 插進外部終端機，讀的是當下的連線數據，不是背出來的舊情報 |
| **token-optimizer** | 多代理派工前的節流鐵則：模型分層、壓縮上報、失敗三次就停 | 能源分配，別讓護盾吃光動力 |
| **flight-to-calendar** | 航班上 Google Calendar：跨時區不出錯、轉機拆段、夕陽座位 | astromech 本職：導航 |

## 這套東西怎麼開發的

Claude 的 session 是**失憶的**：對話一關，沒寫進磁碟的東西全部蒸發。這套 skills 的共同主題就是對抗失憶——上表每一支，管的都是失憶鏈上的一段。全部是在真實日常使用中踩坑迭代出來的，不是理論設計。

開發流程自己也吃同一套規矩：**每版出貨前，先把產出送給另一個模型家族審一輪**（同一個模型再檢查一次，只會確認它本來就相信的事）。`ai-review` 這支就是這樣做出來的——三輪跨模型二審抓出 21 個缺陷、其中 13 個是前一輪修法自己帶出來的，46 項回歸測試隨包出貨。這些都查得到：測試方法與證據見 [docs/TEST_PLAN.md](docs/TEST_PLAN.md)，fork 每一版修了什麼見 [Releases](https://github.com/SanHsien/agent-astromech/releases)。

## 相容性矩陣

先看這張表，確認你的工具能用哪幾支：

| Skill | Claude Code CLI | Cowork / claude.ai | Gemini CLI | Codex CLI | ChatGPT（僅手動貼入） |
|---|---|---|---|---|---|
| save-all | ✅ | ✅（token 統計步自動跳過） | ✅\*（同左） | ✅\*（token 統計步刪掉） | ⚠️ 僅檢查清單 |
| dropoff / pickup³ | ✅ | ✅ | ✅\* | ✅\* | ❌（無共用磁碟） |
| recap⁶ | ✅ | ✅（規則類；刷新哪幾項看環境有哪些工具） | ✅（同左） | ✅（同左） | ⚠️ 只剩回報格式，無法刷新 |
| mission-log / daily-debrief / weekly-debrief | ✅ | ❌（無本機 transcript） | ❌² | ❌² | ❌² |
| new-mission⁷ | ✅ | ✅（規則類，零工具依賴） | ✅（規則類） | ✅（規則類） | ⚠️ 貼入當開工簡報流程 |
| damage-report | ⚠️⁵ | ✅（規則類，零工具依賴） | ✅（規則類） | ✅（Windows CLI runtime 實測） | ⚠️ 貼入當收尾檢查清單 |
| blind-review⁶ | ✅（需子代理派工） | ⚠️ 無子代理就改人工另開乾淨對話 | ⚠️ 同左 | ⚠️ 同左 | ⚠️ 另開一個空白對話當攻擊者 |
| ai-review | ✅（需二審後端⁴） | ⚠️ 規則可用、腳本要能跑 shell | ⚠️ 同左 | ⚠️ 同左 | ⚠️ 改用 prompts/ 貼進另一個 AI |
| ai-search⁷ | ✅（需搜尋後端） | ⚠️ 規則可用、腳本要能跑 shell | ⚠️ 同左 | ⚠️ 同左 | ⚠️ 用 prompts/＋自帶 browsing |
| token-optimizer | ✅ | ✅（規則類，無工具依賴） | ⚠️ 原則通用¹ | ⚠️ 原則通用¹ | ⚠️ 原則通用¹ |
| flight-to-calendar | ✅（需 Calendar connector） | ✅（需 Calendar connector） | ⚠️ 需自備 Calendar MCP（未實測） | ❌ 無 Calendar 工具 | ⚠️ 需自備 Action |

\* ＝安裝／發現層實測，執行層為規則推論（見 [docs/TEST_PLAN.md](docs/TEST_PLAN.md) CROSS-05）。
¹ 五鐵則通用、模型名自行對換；§1「進階兜底」（settings.json／env）僅 Claude Code 生效，其他工具跳過。
² 日誌三支的資料來源是 **Claude Code 自家的 transcript**（`~/.claude/projects/`）——skill 格式裝得進其他工具，但那裡沒有這份資料，故標 ❌。
³ 「即時門鈴」（推球後直接傳訊喚醒對面 session）為選用增強，僅 Claude Code v2.1.224+ 的 cross-session messaging 生效（官方支援 macOS／Linux；送往 bypass-permissions session 的訊息會先押著等人工核准）；其他工具偵測不到就自動跳過，純檔案交接不受影響。
⁴ `ai-review` 需要一個二審後端（預設 Codex CLI，可用 `AI_REVIEW_CMD` 換掉）＋能跑 POSIX shell 的環境。沒有後端／沒登入時回報 `skipped_*` 並**照常回 0**，不會中斷流程；額度或網路類失敗預設回 2，加 `--soft-fail` 可讓它也回 0。腳本刻意不釘死模型（釘了會過期），若後端預設模型不在你的方案內，用 `--model` 指定。macOS 與 Linux 會驗完整 POSIX 權限；Windows 11 Git Bash 驗其餘行為並明確略過 NTFS 無法證明的 mode bit。**免費方案帳號仍未實測**。⁵ Claude Code 2.1.231 的 Windows 非互動 `-p` 抽測**對 `damage-report`** 未產出完整五問，故該格不以 package 成功替 runtime 背書；互動 TUI 需另測。⚠️ 這是**特定 skill 的**限制，不是「非互動模式跑不了 skill」——同一個 `-p` 模式已成功跑完 `dropoff` 並落檔（見 TEST_PLAN CROSS-05）。⁶ `recap` 與 `blind-review` 於 v0.7.0 新增，**跨工具皆未實測**：表中評級是依「規則類／需子代理」推論的，不是量過的。
⁷ `new-mission` 與 `ai-search` 於 v0.8.0 自上游 `tingyulu/MyR2D2` v0.7.3 採納，v0.8.1–v0.8.4 補上 Windows 修復與實測。上兩列的評級**現在全部量過**：**安裝層** `codex`／`claude-code`／`gemini-cli`／`cursor`／`github-copilot` 五個目標各 **14/14、0 Skipped**；**發現層** Gemini 未信任時列出 0 支、信任後 **14 支全 `[Enabled]`**（0.58.0，trusted-folder 是無聲關卡）；**執行層**以 `dropoff` 在 **Codex CLI／Claude Code CLI／Gemini CLI 三者各實跑一次**，產出的交接卡 frontmatter 逐欄符合規格，且三者都獨立走到「無門鈴能力→降級不通知」（CROSS-05，此項自 repo 建立以來首次實測）；`ai-search` 44 項行為矩陣每次 push 實跑，**`ok` 路徑預設 codex 後端與可插拔後端都驗過**，失敗分類亦在真實後端驗過。**還沒量的**：執行層抽測只涵蓋 `dropoff` 一支，不自動延伸到需外部 connector（`flight-to-calendar`）或需子代理（`blind-review`）的 skill；`cursor`／`github-copilot` 只驗安裝層（本機無此二工具）；免費方案帳號**刻意不驗**（需另外申請帳號，借用他人帳號不具代表性——這是決定，不是待辦）。`ai-search` 需要一個**會上網搜尋**的後端（預設 Codex CLI 內建搜尋，可用 `AI_SEARCH_CMD` 換掉——但換的後端也得會搜尋）；沒有後端／沒登入回 `skipped_*` 並回 0，自動化只看退出碼會把「本次沒查證」當成功，要分辨就解析 stdout 末行的 `AI_SEARCH_STATUS:`。逐項證據見 [docs/TEST_PLAN.md](docs/TEST_PLAN.md) F 段、CROSS-02 與 CROSS-05。

- **Gemini CLI／Codex CLI**：三層皆已實測——Gemini 於 0.58.0 兩情境驗發現層（未信任 0/14、信任後 14/14 全 `[Enabled]`），**trusted-folder 是道無聲關卡：skill 沒出現時先信任專案資料夾**；兩者的執行層均以 `dropoff` 實跑通過（見 TEST_PLAN CROSS-05）。
- **ChatGPT**：無 CLI／無檔案系統，唯一路徑＝手動貼入（見 adapters）。
- Cursor／Copilot：**安裝層已實測**（各 14/14、0 Skipped，2026-09-06）；發現層與執行層未實測（本機無此二工具）。

ChatGPT / Codex 的移植方法（首選 `npx skills`、備援 AGENTS.md 併入、三個坑）見 **[adapters/openai/](adapters/openai/README.md)**。

## 安裝

**怎麼選**：CLI 使用者 → npx 或 Plugin｜想手動控制 → 手動複製｜只用網頁版 Chat → 免安裝簡版｜claude.ai Cowork → 最後一段。

### skills.sh（`npx skills`）——推薦，一行裝完

[![skills.sh](https://skills.sh/b/SanHsien/agent-astromech)](https://skills.sh/SanHsien/agent-astromech) [![CI](https://github.com/SanHsien/agent-astromech/actions/workflows/ci.yml/badge.svg)](https://github.com/SanHsien/agent-astromech/actions/workflows/ci.yml)
（skills.sh badge 的數字＝累計安裝次數，不是 skill 支數。）

```bash
npx skills add SanHsien/agent-astromech
```

[`npx skills`](https://github.com/vercel-labs/skills) 支援 Claude Code 與其他多種 agent（`gemini-cli`、`codex`、`cursor`…，完整清單見上游 README）。本 repo 已實測 `codex`／`claude-code`／`gemini-cli`／`cursor`／`github-copilot` **五個目標的安裝層**，各 14/14、0 Skipped（方法與證據見 [docs/TEST_PLAN.md](docs/TEST_PLAN.md) CROSS-01）。**預設裝到專案層** `./.claude/skills/`；要裝成全域才加 `-g`。想只裝其中幾支用 `--skill`。

### Claude Code CLI — Plugin（深度整合）

```
/plugin marketplace add SanHsien/agent-astromech
/plugin install agent-astromech@agent-astromech
```

skill 掛在 `agent-astromech:` 命名空間下（`/agent-astromech:dropoff`…）——與你機器上既有的同名 skill 結構上不衝突，且可經 marketplace 集中更新。

### Claude Code CLI — 手動複製

```bash
git clone https://github.com/SanHsien/agent-astromech.git
cp -rn agent-astromech/skills/* ~/.claude/skills/
```

⚠️ 用 `-n`（不覆蓋既有檔）：若你 `~/.claude/skills/` 底下已有同名資料夾，`cp -r` 會**直接覆蓋且不提示**。想更新既有的，先自己 diff 過再決定。

### 只用網頁版 Chat？免安裝簡版

不用 CLI、不裝任何東西：[prompts/](prompts/) 有可直接貼進對話（或 custom instructions）的簡版 prompt，規則類 skill 適用——`new-mission`（[繁中](prompts/new-mission.md)｜[EN](prompts/new-mission.en.md)，貼進常駐欄讓它**先問、給計畫、等你點頭才動手、做完交收尾報告**）、`damage-report`（[繁中](prompts/damage-report.md)｜[EN](prompts/damage-report.en.md)；繁中完整版 781 字元、連 ChatGPT Free 都放得下，另有[極簡版](prompts/damage-report.lite.md)供更窄欄位）、`ai-review`（[繁中](prompts/ai-review.md)｜[EN](prompts/ai-review.en.md)，貼進**另一個** AI 就是跨模型二審）、`ai-search`（[繁中](prompts/ai-search.md)｜[EN](prompts/ai-search.en.md)，貼進**有 browsing 的** AI 就是帶引用的即時查證）、`recap`（[繁中](prompts/recap.md)｜[EN](prompts/recap.en.md)，問進度時先重查再用四欄回報；查不到的標「未驗證」）與 `token-optimizer`（[繁中](prompts/token-optimizer.md)｜[EN](prompts/token-optimizer.en.md)，拆多段或多對話分工時的節流守則）。

### Cowork / claude.ai

先照「手動複製」段 `git clone`（或 GitHub 網頁 **Code → Download ZIP**）取得 repo，再把要用的 skill 資料夾（`skills/<名稱>/`）加進你的 Cowork 專案 skills（或專案目錄的 `.claude/skills/`）。

裝完打 `/save-all`、`/dropoff`、`/pickup`、`/recap`、`/daily-debrief`、`/new-mission`、`/damage-report`、`/blind-review`、`/ai-review`、`/ai-search` 等即可觸發，或用上面任一語言的自然語句。

## 更新

skill 裝進去的是當下快照，**有新版不會自動通知**。更新方式：

```bash
npx skills update
```

一行更新所有已裝 skill（來源記在安裝時的 lock 檔；`-g`／`-p` 限定全域／專案層）。Plugin 路徑裝的改用 `/plugin` 介面更新 marketplace。想在新版發布時收到通知：GitHub 上對本 repo **Watch → Custom → Releases**。

## 一組 skill、兩種語言習慣

Skill 本體是繁體中文（單一真相，不維護平行翻譯版）;**觸發詞中英各一組對應**，寫在每支 skill 的 description 裡:

- 中文習慣：「要重開機了」「交接給 X」「有沒有交接給我的」
- English habit: "about to reboot", "hand this off to X", "anything handed off to me?"

Claude 讀繁中指令、照樣用你的對話語言回覆 —— 英文使用者的體驗不打折，而 skill 永遠只有一份要維護。

## 各 skill 的依賴

| Skill | 依賴 |
|---|---|
| save-all | 無（token 統計那步限 Claude Code CLI，選跑） |
| dropoff / pickup | 無 — 交接卡就是專案目錄下的 Markdown 檔(`.claude/handoffs/`)；即時門鈴為選用增強（Claude Code v2.1.224+），偵測不到自動跳過 |
| recap | 無（純規則）—— 但**刷新那步吃工具**：版本控制／PR／CI／背景工作各查一次，環境沒有的就標「未驗證」，不得沿用對話裡的舊值 |
| mission-log | 無 — 收割器為純標準庫 python3 腳本，零 token。附測試（`tests/harvest_test.py`，合成 fixtures、不讀真資料） |
| daily-debrief | **需一併安裝 mission-log**（收割器在那支裡） |
| weekly-debrief | **需一併安裝 daily-debrief 與 mission-log**（缺日結會自動補生成） |
| new-mission | 無（純規則;第 3 步進階節的 `ai-review` 送審是選用交叉引用） |
| damage-report | 無（純規則;第 5 問提到的 `/dropoff`、進階節的 `ai-review` 都是選用交叉引用） |
| blind-review | **能派唯讀子代理的環境**（子代理拿不到對話是本 skill 的前提；派不出來就人工另開一個乾淨對話代替）。與 `ai-review` 互補不重疊：這支換脈絡，那支換模型家族 |
| ai-review | **二審後端**(預設 Codex CLI;`AI_REVIEW_CMD` 可換任何讀 stdin／吐 stdout 的命令)＋POSIX shell。內建 600 秒 wall-clock timeout，可用 `--timeout` 調整。無額外套件依賴:不需 npm 套件、brew formula 或自備 API key。附 46 項回歸測試(`tests/matrix.sh`,不燒額度) |
| ai-search | **會上網搜尋的後端**(預設 Codex CLI 內建 `web_search`;`AI_SEARCH_CMD` 可換,但換的後端也得會搜尋)＋POSIX shell。無額外套件依賴。附 44 項回歸測試(`tests/matrix.sh`,不燒額度、不連網) |
| token-optimizer | 無（規則類 skill;Workflow 相關條目需要有 Workflow tool 的環境——Workflow＝Claude Code 的多代理編排功能;§1「進階兜底」僅 Claude Code CLI 生效） |
| flight-to-calendar | **Google Calendar MCP connector**（硬依賴） |

dropoff/pickup 預設是零依賴的檔案版；如果你有自己的任務系統(CLI todo、Notion、Linear…),SKILL.md 內附「接上你自己的任務系統」的替換說明。

## 設計原則

1. **驗證優先於宣告** — 寫入要回讀驗證，完成要證據，不信字面成功訊息。
2. **脈絡自包含** — 交接卡假設讀者對前情一無所知。
3. **零依賴的最小公倍數** — 預設檔案版，進階才接外部系統。
4. **配額是共享資源** — 多代理派工的預設是省，全力跑是顯式開關。
5. **單一真相** — skill 只有一份（繁中），語言習慣靠雙語觸發詞對應，不維護平行翻譯版。

## Repo 結構

```
agent-astromech/
├── .claude-plugin/                    ← plugin.json + marketplace.json(單一 plugin)
├── .github/workflows/                 ← CI(YAML 驗證、守門 grep、行為矩陣、harvest 測試)
├── skills/                            ← 14 支 skill(繁中本體、雙語觸發)
│   ├── save-all/  ├── dropoff/  ├── pickup/  ├── recap/
│   ├── mission-log/  ├── daily-debrief/  ├── weekly-debrief/
│   ├── new-mission/  ├── damage-report/  ├── blind-review/
│   ├── ai-review/  ├── ai-search/
│   └── token-optimizer/  └── flight-to-calendar/
├── prompts/                           ← 免安裝簡版(貼進 Chat 就能用)
├── docs/                              ← 測試計畫、外部前提的查證記錄
│   └── cheatsheet.md                  ← 14 支速查小抄
├── adapters/openai/                   ← ChatGPT / Codex 移植包（其餘工具由 npx skills 直接安裝，不需移植包）
├── README.md                          ← 本頁(中文為主)
└── README.en.md                       ← English
```

## Attribution

- `token-optimizer` 改寫自 [kieiken/ultracode-token-optimization](https://github.com/kieiken/ultracode-token-optimization)(MIT)，泛化為全 Claude 環境版本。

## License

MIT — 詳見 [LICENSE](LICENSE)。

*agent-astromech 是為 AI Coding Agent 工作流設計的隨行技能包。*
