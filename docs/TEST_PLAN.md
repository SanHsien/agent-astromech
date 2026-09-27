# agent-astromech 測試計畫

> 本計畫的存在理由：v0.1.1 帶著 5 支無效 YAML 上線三天無人發現（`npx skills add` 對**所有** agent 0/5 全滅，不只 Claude Code）。教訓＝**發布關卡必須擋在 push 之前，且驗證範圍要涵蓋所有宣稱相容的工具**。
>
> 各項標註可測性：🟢 本機純機械可測／🟡 需對應 agent CLI 在場／✋ 需人工判讀。

## 層次定義（跨工具相容的三層，逐層驗、不可混談）

1. **安裝層**：`npx skills add` 能把檔案裝進該 agent 的 skills 目錄。
2. **發現層**：該 agent 本體真的列出／載入這些 skill（安裝成功 ≠ 看得到，見 CROSS-02 的 trusted-folder 教訓）。
3. **執行層**：agent 收到觸發詞後真的照 SKILL.md 內文正確行事。

---

## A. 發布前回歸（每次 release tag 前必跑，全綠才可 push）

> **一鍵版**（canonical gate；不要在本段複製一份容易漂移的 CI 內容）：
>
> ```powershell
> pwsh -NoProfile -File tools\dev_check.ps1
> ```
>
> ```bash
> sh tools/dev_check.sh
> ```

### REG-01 🟢 YAML frontmatter 雙 parser 驗證

```bash
python3 -c "
import yaml,glob,re
for f in sorted(glob.glob('skills/*/SKILL.md')):
    m=re.match(r'^---\n(.*?)\n---\n',open(f).read(),re.S)
    try: print('OK  ',f,list(yaml.safe_load(m.group(1)).keys()))
    except Exception as e: print('FAIL',f,type(e).__name__)
"
```

**通過**：全部 skill（v0.8.0 起為 14 支）全 `OK`。有第二個 parser（ruby psych／js-yaml）就交叉驗。這是 v0.1.1 事故的直接回歸項。
⚠️ 驗證器自己也要驗：跑一次**故意壞掉的 YAML**（如 `description: bad: colon`）確認它真的會 FAIL，否則你可能在看一個永遠說 OK 的空轉腳本。

### REG-02 🟢 agentskills.io 官方 validator

```bash
npm ci --ignore-scripts --no-audit --no-fund
for d in skills/*/; do ./node_modules/.bin/skills-ref validate "$d"; done
```

**通過**：全數（現為 14 支）全過。驗 name 格式（小寫/連字號/=目錄名）、description ≤1024 字等規格硬約束。

### REG-03 🟢 本地安裝煙霧測試

```bash
npm ci --ignore-scripts --no-audit --no-fund
REPO_ROOT=$PWD
TARGET=$(mktemp -d)
git -C "$TARGET" init -q
(cd "$TARGET" && "$REPO_ROOT/node_modules/.bin/skills" add "$REPO_ROOT" --copy -y)
```

**通過**：回報 `Installed 14 skills`（與 repo 現有支數一致）、0 個 Skipped。

### REG-04 🟢 公開內容守門

跑 repo `CLAUDE.md` 鐵則 1 的守門 grep（含 `--untracked` 與 `-i`），除已知預期命中外 0 命中。

### REG-05 🟢 文件連動掃描

依 `CLAUDE.md` 鐵則 3 連動清單逐項核對（README 雙檔／plugin.json／marketplace.json／adapters 矩陣）。

---

## B. 跨工具相容（宣稱相容的每個工具，逐層驗證）

### CROSS-01 🟢 多 agent 安裝層矩陣

```bash
REPO_ROOT=$PWD
SKILLS="$REPO_ROOT/node_modules/.bin/skills"
for a in gemini-cli codex cursor github-copilot; do
  TARGET=$(mktemp -d)
  git -C "$TARGET" init -q
  (cd "$TARGET" && "$SKILLS" add "$REPO_ROOT" --agent "$a" --copy -y)
done
```

**通過**：每個 agent 都回報 Installed 支數=repo 現有支數、0 Skipped。
狀態（2026-09-05，本 fork 自量）：`codex`／`claude-code`／`gemini-cli` 三個目標各自乾淨的 Windows
隔離專案逐一 `--agent` 安裝，皆 **Installed 14、0 Skipped、磁碟實數 14**；`chatgpt` 為陰性對照，
照文件所述被 `Invalid agents: chatgpt` 擋下。由 `tools/windows_agent_smoke.ps1` 執行，已接進
canonical gate，每次跑 gate 都會重量一次。
⚠️ **`gemini-cli` 這格只證明安裝層**：`skills add --agent <名>` 是**安裝器**的行為、寫進統一的
`.agents/skills/`，與目標 CLI 在不在場無關。發現層是另一件事，已於 2026-09-06 補驗，見 CROSS-02。
**`cursor`／`github-copilot` 亦於 2026-09-06 補測**：兩者各自乾淨的 Windows 隔離專案逐一 `--agent` 安裝，
皆 **14 支、0 Skipped**，安裝目標同樣是統一的 `.agents/skills/`——與 `gemini-cli` 同理，
這證明的是**安裝器行為**，兩者的發現層與執行層皆未驗（本機沒有這兩個工具）。
至此 CROSS-01 涵蓋 `npx skills` 的五個目標，無未測項。
**安裝器版本**：全部以 repo 釘住的 `skills` **1.5.23**（`package.json` devDependency，腳本走 `node_modules/.bin/skills` 而不是 `npx` 抓最新）執行——與上游 2026-08-29 那次同版，所以差異只在 repo 支數，不在安裝器。日後這格重跑要一併記當下的釘版，不然「14/14」讀不出是哪一版安裝器量的。

### CROSS-02 🟡 Gemini CLI 發現層（trusted-folder 關卡）

```bash
gemini skills list --all   # 分別在「未信任」與「已信任」的專案目錄各跑一次
```

**通過**：未信任時輸出含 `Skipping project agents due to untrusted folder`（skill 不出現＝**預期行為**，不是 bug）；信任該資料夾後全數 skill 列出並標 `[Enabled]`。
⚠️ 這道關卡是無聲的（不報錯），文件必須揭露，否則使用者會以為安裝失敗。建議用隔離 `HOME` 測「已信任」情境，避免動到真實 `~/.gemini/trustedFolders.json`。
狀態（2026-09-06，gemini-cli **0.58.0**，本 fork 自量，兩情境皆實測）：

| 情境 | 磁碟上的 agent-astromech skill | `skills list --all` 列出的 agent-astromech skill | 關卡訊息 |
|---|---|---|---|
| 未信任 | 14 | **0** | `Skipping project agents due to untrusted folder`＋`Project hooks disabled because the folder is not trusted` |
| 已信任 | 14 | **14，全部 `[Enabled]`** | 關卡訊息消失 |

✅ 兩個方向都對上了：**未信任時 skill 完全不出現是預期行為**（磁碟上明明有 14 支），
信任後 14 支全數列出。做法：`mktemp -d` 建隔離專案與隔離 `HOME`，用 `npx --yes @google/gemini-cli`
免全域安裝，信任狀態靠寫入隔離 `HOME` 的 `.gemini/trustedFolders.json`
（`{"<專案絕對路徑>": "TRUST_FOLDER"}`）切換，**沒有動到真實的 `~/.gemini/`**。
🪟 Windows 注意：`git -C`／`python` 這類原生 Windows 程式收 Git Bash 的 `/tmp/...` 會失敗
（首次嘗試就因此靜默裝了 0 支、讓「未信任」的結論變成假陽性），一律先 `cygpath -w`。
❓ **執行層仍未驗**：本次只證明「Gemini 找得到、載得進去」，沒有證明它照 SKILL.md 正確行事。

### CROSS-03 🟡 Codex CLI 發現層（原生注入驗證）

```bash
# 於已用 --agent codex 裝好的專案目錄：
codex debug prompt-input "test" | grep -E "dropoff|pickup|save-all|token-optimizer|flight-to-calendar"
```

**通過**:全數 skill 的 name＋description 均出現在 model-visible prompt 的 skills 區塊。
狀態（2026-07-30，codex-cli 0.145.0）：已實測通過——Codex 有原生 skill 機制（`~/.codex/skills/.system/`），**不需**手動併入 AGENTS.md。

### CROSS-04 🟢 ChatGPT 消費版陰性對照

```bash
./node_modules/.bin/skills add "$PWD" --agent chatgpt --copy -y
```

**通過**：CLI 回報 `Invalid agents: chatgpt`（**預期失敗**）。ChatGPT 消費版無檔案系統／無 CLI，唯一路徑是 `adapters/openai/` 的手動貼入法。此項用來持續確認該定位仍準確。

### CROSS-05 ✋ 執行層端到端（每個 release 至少抽測一支）

在隔離目錄以各 agent 非互動模式觸發低風險 skill（建議 `dropoff`）：

```bash
codex exec "觸發 dropoff：幫示範任務寫一張交接卡"     # 或 gemini -p "..."
```

**通過**：真的產出交接卡檔案，frontmatter（status/from/to/created）齊全、內容符合 SKILL.md 步驟。需人工核對格式，「有產出檔案」不算過。
狀態（2026-09-06，本 fork 首次實測；**此項自 repo 建立以來一直是「未實測」**）：

| 工具 | 產出 | frontmatter 人工核對 | 判定 |
|---|---|---|---|
| **Codex CLI 0.150.0** | `.claude/handoffs/20260906-1059-*.md` | `status: pending`／`from`／`to`／`created: 2026-09-06 10:59`／`priority: normal` 全中，格式與規格逐欄相符；選填的 `from-session`／`notify` 依規定省略 | ✅ 過 |
| **Claude Code CLI**（非互動 `-p`） | `.claude/handoffs/20260906-1110-*.md`，86 行 | 同上五欄全中，另正確使用選填的 `notify: silent` | ✅ 過 |
| **Gemini CLI 0.58.0**（`-p --yolo`，隔離 `HOME`＋已信任） | `.claude/handoffs/20260906-2029-*.md`，18 行 | 五欄全中、YAML 可解析、`status` 正確解析為 `pending`；章節（要做什麼／脈絡／相關檔案／完成的定義）齊 | ✅ 過（附兩個小瑕疵，見下） |

兩者都**不只是產出檔案**：Codex 主動回報「目前沒有其他可通知的 session，因此未按即時門鈴」，
Claude Code 以 `notify: silent` 記錄同一件事——這正是 SKILL.md 對「無門鈴能力時降級」的要求，
兩個不同 agent 各自獨立走到同一個正確行為。Claude Code 那次還主動把「卡不該落在會消失的沙盒裡」
提出來讓使用者否決，屬於 skill 要求的判斷而非幻覺。

⚠️ 範圍界定：受測 skill 是 `dropoff` 一支，不是全部 14 支；`dropoff` 是規則＋檔案寫入類，
結論不自動延伸到需要外部 connector 的 `flight-to-calendar` 或需子代理的 `blind-review`。
📌 附帶修正既有敘述：README 註⁵ 說「Claude Code 2.1.231 的 Windows 非互動 `-p` 抽測未產出完整五問」
——那是對 `damage-report` 的觀察；本次同一個非互動 `-p` 模式**成功**跑完 `dropoff` 並落檔，
所以該限制是**特定 skill 的**，不是「非互動模式不能跑 skill」。
✅ **gemini-cli 執行層已於 2026-09-06 補驗通過**（維護者當日提供 `GEMINI_API_KEY` 後解除阻礙）。
做法沿用 CROSS-02 那套隔離：`mktemp` 隔離專案＋隔離 `HOME`＋`trustedFolders.json`，
金鑰**從登錄檔讀進子行程、全程未列印**，跑完即清除；事後確認真實 `~/.gemini/` 未被動到
（仍無 `trustedFolders.json`）、暫存目錄 0 殘留。

⚠️ 兩個小瑕疵（**不影響判定，但值得記**）：
1. **模板註解外洩**：卡上寫成 `status: pending          # pending → picked → done`——
   那串 `#` 註解是 `dropoff/SKILL.md` 模板裡給人看的說明，被原樣抄進產物。
   YAML 會把它當註解剝掉（故 `status` 仍正確解析為 `pending`），屬美觀問題不是格式錯誤。
2. **`to` 欄語意偏差**：規格是 `to: <目標專案>`，它填了 `gemini-cli`（工具名而非專案名）。
   三個 agent 裡只有它這樣填，Codex 填 `SanHsien/agent-astromech`、Claude Code 填「agent-astromech（同專案未來 session）」。

📌 **三個 agent 的橫向對照才是本項真正的收穫**：同一份 SKILL.md、同一個觸發語句，
Codex／Claude Code／Gemini 都產出結構正確的卡並各自獨立走到「無門鈴能力→降級不通知」，
但**詳盡度差距很大**（86 行 vs 18 行）。這說明 skill 的規格約束住了**結構**，
沒有、也不該約束**內容深度**——驗收標準寫成「frontmatter 齊、章節符合」是對的，
若寫成「要有多少行」就會變成不可移植的宣稱。

### CROSS-06 🟢 事故回歸（YAML × 真實安裝）

REG-01 ＋ REG-03 合跑。此缺陷影響**所有** npx-skills 下游 agent，不是 Claude Code 特有——發布關卡的涵蓋範圍要與此對齊。

### CROSS-07 ✋ 矩陣宣稱 × 實測交叉稽核

README 相容性矩陣與 adapters 上的每個 ✅／⚠️／❌，都要能對應到一次實際指令輸出佐證（本項曾抓到 adapters 對 Codex 的描述整段過時）。有落差→下個 release tag 前修文件或重測。

---

## J. 日誌三支（mission-log／daily-debrief／weekly-debrief，v0.3.0 起）

Windows 回歸：`harvest.py` 必須使用跨平台主機名 API、固定 UTF-8 輸出，並以 `--timezone +08:00` 讓日界線不依賴 POSIX `TZ`；Windows Python 執行 16 項 synthetic fixture tests 全過，禁止重新引入 `os.uname()`。

### J-01 🟢 收割器零 token 實跑

```bash
python3 skills/mission-log/scripts/harvest.py --date <近 7 天內某日>
```

**通過**：列出該日活躍 session（時間段／專案名／turns／tokens／工具／原話），全程無模型呼叫；中文專案名正確顯示（cwd 欄位路徑，非目錄編碼的 `-----`）。
狀態（2026-08-02~03）：✅ 已實測（端到端）。

### J-02 🟢 跨機收割（ssh 餵單檔）

```bash
ssh <主機> "python3 - --date <日期>" < skills/mission-log/scripts/harvest.py
```

**通過**：遠端輸出自帶主機名；⚠️ 別加 `ssh -n`（stdin 會被接到 /dev/null，腳本餵不進去——實測踩過）。
狀態（2026-08-02~03）：✅ 已實測（端到端，跨機餵單檔）。

### J-03 ✋ 日期參數解析

`/daily-debrief`（今天）／`yesterday`／`YYYY-MM-DD`；`/weekly-debrief`／`last`／`YYYY-Www`／任一日期落到該週。**通過**：各形式都收割到正確日期範圍。
狀態（2026-09-06 補測，**腳本層驗全、agent 層仍未驗**）：

腳本層（`harvest.py --date`）已逐項實測：

| 輸入 | 結果 | 判定 |
|---|---|---|
| `2026-09-05`（ISO） | 21 筆骨架、exit 0 | ✅ |
| 不給 `--date`（預設） | 21 筆，與 `2026-09-05` 一致＝**預設就是昨天** | ✅ |
| 保留期外 `2026-01-01` | 0 筆、exit 0（空不是錯） | ✅ |
| `yesterday`／`not-a-date`／`2026-13-45` | **exit 1** | ✅ 失敗大聲，無安靜的假成功 |

🔑 釐清一個容易誤判的邊界：**`today`／`yesterday` 這類關鍵字不是腳本的介面**，
`--date` 只吃 ISO（`datetime.date.fromisoformat`）；關鍵字解析是 **agent 照 SKILL.md 做的**。
📌 本次自己踩過這個坑：先前用 `--date yesterday | wc -l` 得到「7 筆」，那 7 其實是
**traceback 的行數**，不是資料筆數——`wc -l` 會把錯誤訊息也算成資料。
⚠️ 教訓寫進來：**計數型驗證要先確認退出碼**，否則會把失敗讀成一個看似合理的數字。
❓ 仍未驗：agent 層的關鍵字解析（`/daily-debrief` 不帶參數＝今天、`yesterday`、`YYYY-Www` 等），
與 J-05 卡在同一件事——隔離環境跑 agent 需要憑證。
📌 `defer`（不改）：非法日期目前是裸 traceback 而非引導訊息。exit 1 正確、不會假成功，
純屬可讀性；改它要動上游檔案、多一處 fetch 衝突面，性價比不划算。上游若自己修就採納。

### J-04 ✋ daily 冪等與誠實

同一天重跑 → 覆蓋更新不疊加；該日無記錄 → 檔案照寫、內容明講原因；summary 只含骨架撐得起的敘述（抽查比對原話）。
狀態（2026-08-02~03 試用期）：⚠️ 部分實測（未逐項驗全）。

### J-05 ✋ weekly 缺口自癒

刪掉該週某天的日報 md 再跑 weekly → 自動補生成；把日期設到保留期外 → 週報標「無記錄」而非報錯。
狀態（2026-09-07，**維護者授權後對真實 journal 實跑，兩個分支都過**）：

**分支一：缺口自癒**——本機 `~/.claude/journal/` 原本**不存在**（三支從未使用），
等於該週 7 天全缺，比規格的「刪掉某一天」更嚴苛。
獨立 agent 跑 `/weekly-debrief 2026-W36` 後：

| 產物 | 結果 |
|---|---|
| `journal/daily/2026-08-31 ~ 09-06.md` | **7 份全部補生成**（11–16 行不等） |
| `journal/weekly/2026-W36.md` | 33 行，三個必備區塊（本週主線／數字與趨勢／Reflection）齊 |
| `journal/weekly/2026-W36.digest.txt` | 19 行純文字通知摘要 |

agent 明講「先用 mission-log harvest 零 token 撈了 7 天骨架（全部在保留期內，無缺口），
回溯補生成 7 份日報，再收斂成週報」，並正確指出「上週檔不存在，所以沒寫『比上週』」——
**沒有無中生有一個比較基準**。

**分支二：保留期外標「無記錄」而非報錯**——跑 `/weekly-debrief 2026-W20`（2026-05-11~17）。
收割器先驗過該週三天皆 0 筆。agent 自行算出 transcript 最舊只到 2026-05-22、
判定 W20 超出保留期，明白引用 skill 規則「標『無記錄(超出保留期)』，不假造」，
**沒有報錯、沒有編造**。
📌 額外的正確判斷：它發現舊 Overnight 系統剛好有一份涵蓋該週的週報，
**停下來問要不要採用**，而不是默默拿另一個資料源頂替。
⚠️ 一個小落差：規格說「週報標無記錄」，它是在對話中回報無記錄並停下來問，**沒有落檔**。
偏保守、不算錯（避免產生一份誤導的檔案），但與字面規格有差，記於此。

### J-06 🟢 歸檔搬移

放一個假日期（>30 天前）的日報檔再跑 daily → 檔案被移入 `journal/archive/YYYY-MM/`，且 weekly 不讀 archive。
狀態（2026-08-02~03）：✅ 已實測（端到端）。

---

## D. 交接門鈴（dropoff/pickup 的跨 session 即時通知，v0.4.0 起）

> 底層＝Claude Code v2.1.224+ 的 cross-session messaging（`ListAgents`＋`SendMessage`；桌面 app 為 session 管理工具變體，以 sessionId 定址）。官方支援 macOS／Linux；送往 bypass-permissions session 的訊息會被暫留待人工核准（`crossSessionInbound`）。版本與行為敘述已對照官方 changelog 與 docs 查證（2026-08-09）。設計原則：門鈴只是通知，卡片檔案才是真相——以下任何一項失敗都不得影響交接成立。

### D-01 ✋ 去程：閒置 session 被門鈴喚醒並開工

發訊給一個閒置（非執行中）的 session，內含卡片路徑與接手指示。
**通過**：對面無需人工介入即開始處理（讀卡、認領）。
狀態（2026-08-09）：✅ 已實測（桌面變體）——閒置 session 39 秒內完成「收訊→執行指令→落檔」。

### D-02 ✋ 回程：完成回訊送達來源 session

接手方完成後回訊來源 session（from 位址）。
**通過**：來源 session 收到完成訊息並被觸發。
狀態（2026-08-09）：✅ 已實測（桌面變體，雙向閉環成立）。

### D-03 ✋ CLI 原生變體（terminal 間、名稱定址）

兩個 terminal `claude` session 間以 `ListAgents`＋`SendMessage` 完成 D-01/D-02 同款流程。
**通過**：同 D-01/D-02。
狀態（2026-08-09）：✅ 已實測（首次真實交接即驗證）——發送端為 headless `-p` session，`ListAgents` 以名稱定址找到 tmux 內的互動 session、`SendMessage` 送達（回執含 msg_id）；接收端互動 session 無人工介入即開工跑 pickup 流程。附帶發現：headless `-p` **能發不能收**（官方文件僅載明不能收）；名稱定址有時要求帶短識別碼（裸名被拒、`名稱 [ref]` 成功）。後續同日：互動 terminal 當發送端亦經真實回訊驗證，且該回訊**跨機**送達另一台機器的桌面 session（經雲端 bridge 定址；單次觀察、機制歸因未確認，勿當保證）。

### D-04 ✋ 靜默檔（「不用即時通知」）（**2026-09-06 已驗**）

dropoff 時使用者說「不用即時通知」→ 不發訊、卡上 `notify: silent`；後續 /pickup 掃卡仍撈得到。
**通過**：無訊息送出且卡片欄位正確。
狀態（2026-09-06）：✅ **已實測**——對 Codex CLI 下達「**不用即時通知**，排隊就好」，
產出的卡 frontmatter 含 `notify: silent`，agent 明講「未按即時門鈴」，且卡片照常落地、欄位完整。
兩個條件都成立：**不發訊**＋**卡仍撈得到**。
📌 與 D-05 的差別要分清：D-05 是**環境沒有門鈴能力**時的自動降級，D-04 是**使用者主動要求**靜默；
兩者最終都寫 `notify: silent`，但觸發原因不同，本次是分開兩次實跑各自驗到的。

### D-05 ✋ 無能力環境降級（**2026-09-06 已驗**）

在無跨 session 傳訊工具的環境（Gemini CLI／Codex／Cowork）跑 dropoff。
**通過**：門鈴步驟被跳過、無報錯、交接卡照常成立。
狀態（2026-09-06）：✅ **已實測，而且是兩個獨立來源**——CROSS-05 的執行層實跑順帶量到本項：
Codex CLI 主動回報「目前沒有其他可通知的 session，因此未按即時門鈴；未來 session 執行 `/pickup` 即可接手」；
Claude Code CLI 則在卡上寫 `notify: silent` 並說明沒有跨 session 傳訊工具可用。
兩者**都照常產出交接卡且 frontmatter 完整**＝純檔案交接不受影響，正是本項要的降級行為。
📌 兩個不同 agent 各自獨立走到同一結論，比單一次觀察強。

### D-06 ✋ 誤喚醒防呆（新鮮度三分支＋路由記憶）（**2026-09-07 實測，抓到兩個真缺陷並修掉**）

dropoff 篩目標專案候選（新鮮＝7 天內活躍）的三種情況，逐一驗：
**通過**：恰好一個新鮮候選 → 自動發訊；超過一個 → 列出問使用者挑，且選擇被記進 `.claude/handoffs/routing.md`（下次同目標直接用，該 session 消失／過期則重問並更新）；一個都沒有（全過期）→ 仍問使用者（硬按過期的 or 只留卡），不自動喚醒沉睡 session。
狀態（2026-09-07，以**真實 5 個同時在線的 session** 實測，非模擬）：

**分支「超過一個新鮮候選」——第一次跑就失敗，修規則後才過。**

| 輪次 | 規則狀態 | 行為 | 判定 |
|---|---|---|---|
| 第 1 輪 | 原規則 | 看到 4 個新鮮候選，**自己挑了「最新啟動的」直接按鈴**，寫進 `routing.md`，事後才補「如果不是你要的跟我說」 | ❌ **失敗**——這正是本規則要防的誤喚醒 |
| 第 2 輪 | 修掉「不准自選」後 | **沒有自選**，卻從第 1 輪那張舊卡的 `rung-at` 欄位**反推**出路由並沿用 | ❌ **仍失敗，且更隱蔽**——第 1 輪的亂挑變成第 2 輪的「既有慣例」 |
| 第 3 輪 | 再補「路由要有出處」後（乾淨環境） | 列出 5 個候選成表、**停下來問**、**一則訊息未發**、**未建 `routing.md`**；卡片照常落地 | ✅ **通過** |

🔑 **第 2 輪才是這次最有價值的發現**：修掉「自己挑」之後，錯誤沒有消失，只是換了個**合規的**外衣——
沿用 `routing.md` 是規格允許的，但那筆紀錄的來源是上一輪的亂挑。
**壞路由會自我延續，而且每一次沿用看起來都完全合規。**
因此 `skills/dropoff/SKILL.md` 新增兩條硬規則：
① 多個候選一律先問，不准以「最新／最近活躍／看起來最像」自選；
② **路由要有出處**——只有 `routing.md` 內標著 `decided-by: user` 的紀錄可免問沿用，
   舊卡片上的 `rung-at`／`notify: rung` 不是路由紀錄。

📌 **誤喚醒的實際代價（2026-09-11 事後發現）**：第 1、2 輪按到的 `claude-6e` **真的開工了**，
在它自己的專案目錄交出兩份完整盤點報告（共約 240 行，耗時橫跨兩天）。
一個原本在做別的事的 session 被拉去做了兩件沒人排定的工作——這正是本規則要防的事，
而且**對方不會拒絕、也不會回報「這不是我該做的」**。報告內容品質良好，其發現已於 v0.9.1 採納。

📌 第 3 輪的 agent 還自己講出了規則背後的理由：「ListAgents 沒有 cwd 欄位，
ref 也對不回 session id，我無法驗證哪一個是」——它辨識出**判斷依據不存在**，所以問。
那正是規則要教會的事。

❓ **另外兩個分支今天造不出條件**（誠實界定，非略過）：
- 「恰好一個新鮮候選」→ 本機同時有 5 個新鮮 session，無法製造「只剩一個」。
- 「一個都沒有（全過期）」→ 需要候選存在但全部超過 7 天未活動；本機 session 全是當日的。
- 相鄰的第 ④ 種情況（該專案**完全無 session**）已由 CROSS-05 三個 agent 各驗一次：
  都明講「無 session 可即時通知」並照常落卡。

---

## E. ai-review（跨模型二審，v0.5.0 起）

> 腳本＝`skills/ai-review/scripts/ai-review.sh`（單檔 POSIX shell）。設計原則：**狀態走 stdout、
> 退出碼只分真失敗** —— 沒裝後端是預期中的降級，不得中斷上層流程。

### E-01 🟢 多 shell 語法與行為矩陣

```bash
for s in /bin/sh /bin/dash /bin/bash /bin/ksh /bin/zsh; do $s -n skills/ai-review/scripts/ai-review.sh; done
```

行為矩陣**已隨 skill 出貨**＝`skills/ai-review/tests/matrix.sh`（46 項，stub 後端不燒額度、
產出寫暫存區不弄髒目錄、開頭自動 `unset` 外部 `AI_REVIEW_*` 變數以隔離環境、全過回 0 可進 CI）：

```bash
for s in /bin/sh /bin/dash /bin/bash /bin/ksh /bin/zsh; do SH=$s sh skills/ai-review/tests/matrix.sh; done
```

**通過**：語法全過；每個 shell 皆 45/45（缺 `python3`+`pyyaml` 時 44 過 1 略過）。
狀態：歷史 macOS 27 快照為 5 shell 41/41；本次 timeout 契約新增後待下次 macOS release 抽測。Windows 11 Git Bash 為 44 過、0 失敗、1 項 NTFS mode-bit 明確略過，Linux CI 仍須 45/45。外部 `export AI_REVIEW_CMD` 污染下結果不變；`npx skills add` 後 `tests/` 隨 skill 一起裝出。

### E-02 🟡 真實後端 ok 路徑

```bash
skills/ai-review/scripts/ai-review.sh <某檔> --rubric code
```

**通過**：回 `AI_REVIEW_STATUS: ok`、退出碼 0、意見內容確實依 rubric 分項（不是錯誤頁）。
狀態（2026-08-20）：✅ 已實測（Codex CLI 0.148.0，真的抓出示範檔的邏輯錯誤）。

### E-03 ✋ 降級不中斷上層

在 `set -e` 的 wrapper 內、且輸出被 `$(…)` 捕捉的情況下，對「沒有後端」的環境呼叫。
**通過**：wrapper 繼續往下跑、退出碼 0、狀態為 `skipped_not_installed`。
狀態（2026-08-20）：✅ 已實測（含 `--strict` 反向確認會回 3）。

### E-04 ✋ 未登入偵測

登出後端後呼叫（或以 stub 模擬 `codex login status` 回「not logged in」）。
**通過**：狀態為 `skipped_not_logged_in`、退出碼 0，且引導文字講的是**登入**不是重裝。
狀態（2026-08-20）：⚠️ **僅以 stub 實測**；沒有真的把帳號登出驗過（會影響使用中的環境）。

### E-06 🟢 跨模型二審抓到的缺陷回歸（v0.5.1）

v0.5.0 出貨後把「SKILL.md＋腳本」整包送 GPT 與 Gemini 各審一次，兩邊獨立指出同一批缺陷。
逐項回歸（納入 E-01 的矩陣，每個 shell 都跑）：

1. `AI_REVIEW_CMD` 指到不存在的命令（exit 127）→ 必須 `skipped_not_installed`＋exit 0
   （原本落進 `failed_unknown`＋exit 2，**直接違反「沒有後端不得中斷上層流程」的硬需求**）。
2. 自訂後端回「not logged in」→ `skipped_not_logged_in`＋exit 0（原本被強制轉成 `failed_unknown`）。
3. `authorization policy denied`／`auth service unavailable` 這類**真失敗不得被吞成 skipped**
   （原本分類器有一條模糊的 `*auth*`，會讓真失敗安靜地回 exit 0）。
4. `--effort` 非白名單值 → exit 1（原本會送進後端，最後被誤判成「版本不相容」並給錯引導；
   值也會被插進 `-c model_reasoning_effort="…"`）。
5. 一次給兩份來源檔 → exit 1（原本靜默只審最後一份）。
6. 同一秒跑兩次 → 落檔不互相覆蓋（檔名加 PID）。
7. 檔名含冒號／空白 → frontmatter 仍是合法 YAML（值加引號並跳脫）。
8. 後端 exit 0 但回空 → 照印原始 stderr（SKILL.md 宣稱「失敗時一律照印」，原本空回覆這條沒做到）。

9. `--soft-fail` → `failed_*` 也回 exit 0（狀態字串照印）；不加時維持回 2。

狀態（2026-08-20）：✅ 全數實測通過（5 shell × 28 項）。

### E-07 🟢 第二輪跨模型二審的回歸（v0.5.3）

v0.5.1／v0.5.2 之後再送一次 GPT＋Gemini。這輪抓到的是**修法本身帶出來的新問題**：

1. `--strict` 與 `--soft-fail` 併用語意衝突（一個要把「沒審到」變失敗、一個要把失敗變沒事）→ 直接報錯 exit 1。
2. 自訂 rubric 是路徑時（`--rubric ../shared/x.md`），路徑會被塞進落檔檔名 → 帶著 `/`、`..` 寫到別的目錄。改成內建三份保留原名、其餘一律 `custom`。
3. 後端把錯誤寫到 **stdout 後回非零**：原本只看 stderr，分類拿到空字串、畫面印「原始錯誤」卻沒東西 → 改成 stderr＋stdout 都納入分類並照印。
4. `--` 沒有真正停止解析選項 → 改成 `--` 之後全部當來源檔。
5. 落檔非原子、且會跟隨既有 symlink → 暫存檔改建在**目標目錄內**再 `mv`（同檔案系統的 rename 才是原子）。
6. **上一輪的修法自己帶出的風險**：登入偵測加了裸的 `*expired*`／`*sign in*`，但「已登入」訊息也可能含 `sign-in method`／`session expires` → 會把正常登入誤判成沒登入而白白略過二審。改成只收 `token expired`／`please sign in` 這種明確片語。
7. `cut -c` 在非 UTF-8 locale 下切的是 bytes，長中文檔名會被切出殘缺位元組 → 依 locale 分流（UTF-8 保留原名，其餘降級成 ASCII 安全字元）。

狀態（2026-08-20）：✅ 全數實測通過（5 shell × 35 項；含 `LC_ALL=C` 下的長中文檔名落檔）。

### E-08 🟡 第三方環境獨立複驗（v0.5.3）

在**另一個專案目錄**以 `npx skills add` 裝好後，用同一份行為矩陣獨立再跑一次，
並實測 skill 層（發現、觸發、有沒有真的去跑腳本、有沒有消化意見）。
**通過**：矩陣同樣全過；skill 被列出；觸發後真的執行腳本並依 `AI_REVIEW_STATUS` 定調。
狀態（2026-08-20）：✅ 已由另一個 session 在獨立沙盒複驗（35/35、真實後端 ok、降級 rc=0、
skill 層三項行為皆正確、damage-report 整合節可達）。

⚠️ 該次複驗抓到**兩層命名碰撞**，是本專案兩輪跨模型二審都沒看到的角度：

1. **skill 觸發詞碰撞**：使用者若已有同義的個人 skill（例如另一支也宣稱「二審／cross-model review」
   的 skill），**personal 層優先於 project 層** —— 喊觸發詞會叫到那一支，測起來像本 skill 壞了。
   測試時用明確指名（Skill 工具指定名稱、或直接讀本 skill 的 SKILL.md）繞過。
2. **PATH 執行檔碰撞**：`ai-review` 是很容易撞名的命令名。若使用者 `PATH` 上有另一支同名執行檔，
   打**裸命令名**會叫到那一支，而且它可能看起來也在做二審 —— 不會報錯，只會安靜地測錯對象。
   ⇒ 本 skill 與 damage-report 的文件一律用**完整路徑**呼叫腳本，這是刻意的。

### E-09 🟢 第三輪跨模型二審的回歸（v0.5.4）

第三輪只有 GPT 一腿（Gemini 免費額度當日用盡），但抓到的全是**第二輪修法自己帶出來的**：

1. **可預測的暫存檔名**（`.ai-review.<pid>.tmp`）：別人可在共用落檔目錄先放同名 symlink，
   `>` 會跟著它把別的檔案截斷 → 改用 `mktemp` 產生不可預測檔名並 `chmod 600`。
   回歸測試直接放一個惡意 symlink，確認受害檔案沒被寫穿。
2. **群組寫入吞掉中途失敗**：`{ …; cat X; printf '\n'; } > f` 只要最後一個 `printf` 成功，
   整組就回 0 —— 於是「送出殘缺 prompt」與「存下被截斷的審閱結果」都會被判成成功。
   改成群組內 `&&` 串接，任一步失敗即中止。
3. **裸的 `401` 比對**（登入偵測與後端分類器各一份）：`session expires in 401 seconds`、
   request id 含 401 都會命中 → 真失敗被判成 skipped（exit 0）。收窄成
   `http 401`／`status 401`／`401 unauthorized` 等帶語境寫法。
   ⚠️ 第一次修還修錯：改成 `*"401 "*` 仍會命中「401 seconds」，是**回歸測試自己抓出來的**。
4. 契約對齊：`dump_backend_output` 只印尾 20 行，文件原本寫「都照印」→ 改成「各印尾 20 行」，
   並警告該輸出可能含 secrets。落檔改為 600 並在文件說明。

狀態（2026-08-20）：✅ 全數實測通過（5 shell × 40 項，含 symlink 攻擊與落檔權限 600 檢查）。

### E-10 🟢 有界 wall-clock timeout（v0.5.4 maintained fork）

`--timeout <正整數秒>`／`AI_REVIEW_TIMEOUT_SECONDS` 對自訂後端、Codex 登入前置檢查與實際 review 呼叫都生效；預設 600 秒。Linux／Windows Git Bash 使用 GNU coreutils `timeout`，其他 POSIX 環境使用內建 watchdog，逾時先 TERM、兩秒後仍存活才 KILL。

**通過**：自訂後端、Codex 登入檢查與 Codex review 三條 stub 路徑睡眠超過一秒時皆回 `failed_timeout`＋exit 2；timeout 非正整數在後端啟動前回 exit 1。狀態（2026-08-24）：✅ Windows Git Bash 已納入矩陣（現為 46 項）；Linux 5-shell 由 exact-SHA CI 驗證。

### E-05 ✋ 平台與方案覆蓋

>（編號跳序＝歷史演進痕跡，刻意保留：E-05 性質是收尾總查，物理位置固定在 E-09 之後，編號不重排。）

**通過**：README 宣稱支援的平台與帳號方案都實跑過。
狀態（2026-08-24）：✅ **Linux 經 CI（ubuntu-latest）**——ai-review 矩陣 5 shell × 46 項、ai-search 5 shell × 44 項與 harvest 測試隨每次 push 實跑；
✅ **Windows 11 Git Bash 已納入 canonical gate，但 POSIX `0600` 由 Linux CI 驗證**。

🚫 **免費方案帳號：刻意不驗，本項就此結案（2026-09-07 決定）** ——
不是「還沒排到」，是**決定不做**。驗它需要另外申請一個免費 ChatGPT／Codex 帳號，
維護者明確表示不為此申請；而借用他人帳號驗證不具代表性（地區、組織政策、帳號狀態都會影響）。
官方用量限制表本來就不含免費方案（見 `AI_REVIEW_SOURCES.md`），
所以**這一格永遠不會有本專案的實測數據**，README 與 SKILL.md 也從未作過相反宣稱。
✅ 現況已是正確狀態：**兩處都寫「免費方案帳號未實測」，那句話本身就是最終答案**，
不需要再被當成待辦追蹤。重查條件：只有在有人自願提供免費帳號實測結果時才更新。

---

## F. ai-search（帶引用即時查證，v0.8.0 自上游採納）

> 腳本＝`skills/ai-search/scripts/ai-search.sh`（單檔 POSIX shell，與 ai-review 同架構）。
> 設計原則相同：**狀態走 stdout、退出碼只分真失敗**，沒裝後端是預期降級、不得中斷上層。
> 🔴 誠實註記：本段的「已測」欄位**分兩種來源，不可混談**——
> ① 上游 `tingyulu/MyR2D2` 在 macOS 與其 CI 上量到的結果（採納時原樣轉錄，本 fork 未複製其環境）；
> ② 本 fork 自己在 Windows／Linux CI 上跑出來的結果。凡標「上游」者，本 fork 未重驗。
> ai-search 尚未經過 ai-review 那樣的多輪跨模型家族二審。

### F-01 🟢 多 shell 語法與行為矩陣

```bash
for s in /bin/sh /bin/dash /bin/bash /bin/ksh /bin/zsh; do $s -n skills/ai-search/scripts/ai-search.sh; done
for s in /bin/sh /bin/dash /bin/bash /bin/ksh /bin/zsh; do SH=$s sh skills/ai-search/tests/matrix.sh; done
```

行為矩陣隨 skill 出貨＝`skills/ai-search/tests/matrix.sh`（44 項，stub 後端**不燒額度、不連網**、
產出寫暫存區、開頭自動 `unset` 外部 `AI_SEARCH_*` 變數以隔離環境）。涵蓋：後端錯誤分類、
`--strict`／`--soft-fail`、可插拔後端、`set -e`＋`$(…)` 呼叫鏈（含負對照：真失敗必須中斷上層）、
問題輸入多形式（位置參數接句／stdin `-`／`--` 之後當文字）、分類器不把真失敗吞成 skipped、
落檔不覆蓋／600／防 symlink、含冒號引號的問題 frontmatter 仍是合法 YAML、非 UTF-8 locale 長中文落檔。
**通過**：語法全過；每個 shell 皆 43/43（缺 `python3`+`pyyaml` 時 42 過 1 略過）。
狀態：上游於 macOS 五 shell 實測 42 過 1 略（2026-08-24）。**本 fork 已在 Windows 11 Git Bash 實測**
（2026-09-05，`sh`／`dash`／`bash` 各 **43 過 / 0 失敗 / 1 略過**，exit 0）——該 1 略＝落檔權限 `0600`，
NTFS 不提供 POSIX mode-bit 證據，比照 ai-review 由 Linux CI 權威驗證（本 fork 為此在
`tests/matrix.sh` 補上與 ai-review 同形的 `MINGW*|MSYS*` 略過分支，上游無此分支）。
矩陣已接進兩個 canonical gate（`tools/dev_check.sh`、`tools/dev_check.ps1` 的 `sh`／`bash`）
與 CI（ubuntu-latest 五 shell），隨每次 push 實跑。
v0.8.1 新增第 44 項「傳給後端的 `-C` 路徑格式」（見 F-05），並修掉兩個讓本段長期不可信的
測試自身缺陷：① frontmatter 驗證把 POSIX 路徑交給原生 Windows `python3` → `FileNotFoundError`
誤判成 YAML 壞掉；② 改走 stdin 後仍依 locale 解碼，cp950 把 UTF-8 中文解成代理字元 →
PyYAML 報 `unacceptable character #xdce5`。兩者都讓一份**合法**的 frontmatter 假紅，且
在有設 `PYTHONIOENCODING` 的 shell 會過、沒設的會紅——典型的「看起來像 flaky」假訊號。

### F-02 🟡 真實後端 ok 路徑

```bash
skills/ai-search/scripts/ai-search.sh "某個需要查證現況的問題"
```

**通過**：回 `AI_SEARCH_STATUS: ok`、退出碼 0、答案結論先行且附**可點的來源連結**（不是錯誤頁），
內容反映當前網路資訊而非訓練知識填答。
狀態：上游單次實測通過（Codex CLI 真實 `web_search` 後端，2026-08-24，答出當日 release 版本＝確實查了即時網路）。
✅ **本 fork 已在 Windows 驗到 `ok`，兩條後端路徑都驗了（2026-09-06）**：

| 後端 | 指令 | 結果 |
|---|---|---|
| **預設**（Codex CLI 內建 `web_search`） | 直接跑腳本 | `AI_SEARCH_STATUS: ok`＋exit 0，答案附官方來源（台北 101 官網、臺北市政府）並自行分級官方 vs 二手 |
| **可插拔**（`AI_SEARCH_CMD`） | `claude -p --allowedTools WebSearch` | `ok`＋exit 0，結論先行、兩個官方 API 來源互相印證、主動標時效風險、明講哪段沒查 |

🔑 **「確實查了即時網路」的證據**：可插拔後端那次答出 Codex CLI `0.153.4`（2026-09-04 發布），
而本機安裝的是 `0.150.0`——**答案比本機還新**，不可能來自舊知識或本機狀態。

📌 預設後端稍早（2026-09-05）撞到帳號用量上限，當時只驗到 `failed_quota` 被正確分類；
額度於 2026-09-06 恢復後補驗成功。**那次失敗的觀察仍然有效且值得留著**——
它證明了真實後端的失敗分類在 Windows 上正確，那是 stub 測不出來的。

### F-05 🟢 傳給後端的路徑格式（Windows 迴歸）

```bash
for s in sh dash bash; do SH=$s sh skills/ai-search/tests/matrix.sh; done   # 內含本項
```

**背景（實錯，v0.8.1 修）**：Git Bash 上的 `codex` 是**原生 Windows 執行檔**，
腳本把 `-C "$TMPD"`／`-o "$ANSWER_FILE"` 以 POSIX 路徑交給它 → `Error: 系統找不到指定的檔案。 (os error 2)`
→ 分類器歸成 `failed_unknown`。使用者看到的是「無法歸類的錯誤」，不是「路徑格式不對」，
且 **`ai-review` 有完全相同的缺陷**——意即這個 fork 宣稱支援的 Windows 平台上，
兩支腳本從來沒有真正碰到過真實後端。
**為什麼矩陣抓不到**：矩陣的 stub 後端是 `sh` 腳本，POSIX 路徑照吃；只有真實的原生 exe 會踩到。
**修法**：`winpath()` 在 `MINGW*|MSYS*|CYGWIN*` 上用 `cygpath -w` 轉換傳給後端的路徑，
本腳本自己仍用 POSIX 路徑讀同一個檔案。
**測法**：改成攔截 argv——stub 把 `"$@"` 寫進檔案，測項只斷言 `-C` 的值在 MSYS 上是 `?:\…`、
在 POSIX 平台維持 `/…`。
**通過**：三個 shell 皆 ok。狀態（2026-09-05）：✅ Windows 實測通過；
✅ **陽性對照**——把 `winpath` 還原成上游寫法後本項確實轉紅
（`FAIL 傳給後端的 -C 已轉成 Windows 路徑（實得 POSIX：/tmp/…）`），證明它不是永遠說 OK 的空轉測試。
`ai-review` 的矩陣有同形測項（第 46 項）。

### F-03 ✋ 降級不中斷上層

在 `set -e` 的 wrapper 內、輸出被 `$(…)` 捕捉時，對「沒有後端」的環境呼叫。
**通過**：wrapper 繼續往下跑、退出碼 0、狀態 `skipped_not_installed`；`--strict` 反向確認回 3。
狀態：由矩陣涵蓋（stub 實測），本 fork 的 gate 與 CI 每次跑到。

### F-04 🟡 web_search 旗標實際生效

真實後端下，確認腳本送的 `-c tools.web_search=true` 真的讓後端上網（而非拿舊知識答）。
**通過**：答案含**當下**才查得到的事實與來源連結。
狀態（2026-09-06，**跑了兩輪；第二輪推翻第一輪的證據，結論不變但理由換了**）：

**第一輪（比對答案內容）—— 方法有瑕疵，保留作為教訓**
拿掉旗標、其餘相同，它照樣答出 `0.153.4` 並附連結，於是判定「旗標非成因」。
⚠️ 這個推論當時**站不住**：`0.153.4` 有可能本來就在模型知識內，**答得出來不等於查過**。
用「答案對不對」證明「有沒有查」，中間隔著一個沒被排除的解釋。

**第二輪（改數實際工具呼叫事件）—— 這才是證據**
改用 `codex exec --json` 讀事件流直接數 `web_search` 事件，並換一個**本機絕對答不出**的問題
（GitHub star 數）。先前用「現在 UTC 幾點」是壞題目：它跑本機 PowerShell 就答完了，
事件流裡零個 `web_search`，差點被讀成「旗標無效」。

| 組別 | `web_search` 工具事件 | 判讀 |
|---|---|---|
| `-c tools.web_search=true` | **有** | 會搜 |
| `-c tools.web_search=false` | **也有** | **關不掉** |

`--strict-config -c tools.web_search=false` 未報錯 ⇒ 這個 key **被 config schema 認得**，
但在 codex 0.150.0 上**兩個方向都無效**。本機 `~/.codex/config.toml` 亦查無相關設定。

**結論（與第一輪相同，但這次站得住）**：`-c tools.web_search=true` 在此環境**冗餘**，
不是搜尋之所以發生的原因；搜尋能力由後端／帳號決定，不由這個旗標決定。
🚫 不得寫成「ai-search 與 ai-review 的關鍵差異」——真正的差異是提問裡那四條要求。
✅ 旗標保留（無害；別的 build 上可能仍必要）。

📌 **「能不能造出預設關閉搜尋的 build 來驗旗標必要性」——本項就此結案（2026-09-07 決定）**：
本次就是去造那個條件的，結果是**造不出來，因為那個開關在 codex 0.150.0 上是死的**
（`--strict-config` 認得這個 key，但 true／false 兩個方向都不生效）。
這不是「沒去試」，是試過並量到為什麼不行。

**因此對這個旗標的最終處置**（不再列為待辦）：
- ✅ **保留 `-c tools.web_search=true`**。它在此環境無作用但也無害；一旦哪天 codex
  改成預設關閉搜尋，帶著它才是對的。移除它換不到任何好處，只換到一個未來的風險。
- ✅ **文件與程式註解一律據實描述**：它是「明確要求後端開啟搜尋」的宣告，
  **不是**「ai-search 與 ai-review 的關鍵差異」。真正的差異是提問裡那四條要求。
- 🚫 **不再追這件事**。要證明旗標在別的 build 上是否必要，需要一個預設關閉搜尋的
  codex build 或帳號——那不是本專案能製造的條件，也不影響任何使用者可見的行為。
  若上游哪天自己改了預設值，屆時再重驗。

📌 **方法論教訓**（已寫進 `docs/DECISIONS.md`）：要證明「某機制有沒有發生」，就看該機制的
**直接證據**（工具呼叫事件、log），不要用產出內容回推——產出對不對有太多其他解釋。
本項第一輪差點以錯誤理由發布出去。

---

## C. 相容性結論快照（Gemini 安裝層與發現層 2026-09-06 由本 fork 重驗；其餘各列日期見格內）

| 工具 | 安裝層 | 發現層 | 執行層 |
|---|---|---|---|
| Claude Code CLI 2.1.231 | ✅ Windows package 實測 | ⚠️ 非互動 `/damage-report` 有觸發但未產出完整五問 | ✅ `dropoff` 於非互動 `-p` 實測通過、卡片 frontmatter 逐欄符合規格（2026-09-06，CROSS-05）；`damage-report` 仍未通過＝**特定 skill 的限制** |
| Gemini CLI 0.58.0 | ✅ 實測 14/14（2026-09-06） | ✅ 實測 14/14 `[Enabled]`——但**需先信任資料夾**（無聲關卡，未信任時 0/14，見 CROSS-02） | ✅ `dropoff` 實測通過（2026-09-06，CROSS-05；模板註解外洩與 `to` 欄語意兩個小瑕疵） |
| Codex CLI 0.150.0 | ✅ Windows package 實測 | ✅ `exec --json` 證明讀取 `damage-report/SKILL.md`（2026-08-24） | ✅ `dropoff` 端到端實測、卡片 frontmatter 逐欄符合規格（2026-09-06，CROSS-05） |
| ChatGPT 消費版 | ❌ 無安裝路徑（產品限制） | ❌ 無 skill 概念 | 僅手動貼入，網頁端人工驗 |
| Cursor／Copilot 等 | ✅ 實測 14/14（2026-09-06，安裝器行為） | ❓ 未測（本機無此二工具） | ❓ 未測 |

註（2026-08-09）：v0.4.0 的交接門鈴（D 段）為 Claude Code 限定的選用增強，各工具評級不因此變動——非 Claude Code 環境自動降級純檔案交接（見 README 矩陣註³）。

註（v0.7.0，**已由 2026-09-06 的重跑取代，保留作為當時判斷的記錄**）：新增 `recap` 與 `blind-review` 兩支、支數由 10 變 12 時，上表 Gemini CLI 那格還是 2026-08-21 的「實測 10/10」，當時明令**不准**改寫成 12/12——因為那不是量出來的。後來 CROSS-01 於 2026-09-06 真的重跑，該格才依實測改為 14/14。
📌 這條註記的價值不在數字（數字已過期），而在方法：**表格數字只能被重跑取代，不能被推算取代**。`recap`／`blind-review` 兩支仍無新外部依賴（前者純規則，後者需環境能派唯讀子代理，派不出來的降級路徑寫在 skill 與 adapters 矩陣裡），兩支的執行層仍未驗。

註（v0.8.0）：自上游 v0.7.3 採納 `new-mission` 與 `ai-search`，repo 現有支數由 12 變 14。上表各格的實測數字**一律不改寫成 14/14**——那不是本 fork 量出來的。上游在 2026-08-29 對 gemini-cli／codex 逐一 `--agent` 重驗過 12/12（0 Skipped，skills CLI 1.5.23），但那是**上游 12 支**的 working tree，不含本 fork 的 `recap`／`blind-review`，兩者不可相加。CROSS-01 與 REG-03 的通過標準本來就寫成「支數＝repo 現有支數」，重跑一次即可更新；在重跑之前，README 矩陣的這兩列掛註⁷（評級沿用上游實測、本 fork 未重驗）。新增依賴只有一項：`ai-search` 需要一個**會上網搜尋**的後端，沒有時回 `skipped_*` 並回 0（降級不中斷，見 F-03）。
