# ai-review 的前提查證（2026-08-20）

`ai-review` 對外宣稱的兩件事 ——「Codex 含在 ChatGPT 各方案（包含免費方案）」與
「安裝／登入怎麼做」—— 都會過期。這份檔記錄**查證當下的原文與方法**，
方便日後對照；**引用前請自己重查**。

## 1. 方案涵蓋範圍

- 來源：ChatGPT 官方說明站 pricing 頁 `https://learn.chatgpt.com/docs/pricing`
- 查證日期：2026-08-20
- 原句（節錄）：<q>ChatGPT Work and Codex are included in your ChatGPT Free, Go, Plus, Pro, Business, Edu, or Enterprise plan</q>
- 免費方案該頁標 `$0/month`，用途寫的是快速的程式任務。
- 🔴 **同頁的「用量限制」表不含免費方案**（2026-08-20 第二次細查）：表上只有 Plus、Pro 5x、
  Pro 20x、Business 與 API Key，**免費方案的可用模型與額度沒有數字**。
  ⚠️ 因此「免費方案額度最少」是**推論**，而且更重要的是：**無法從官方文件確認免費帳號
  跑得動 Codex CLI 的預設模型**。本專案**沒有在免費帳號上實測過**，文件一律不作此保證。
  （這一條是先前版本寫太滿、被自己的 research rubric 二審抓到後重查修正的。）

⚠️ **不要把這句話讀成「人人都能免費用」**：方案表列有 ≠ 你的地區、帳號狀態、
組織政策都允許跑起來，也不保證登入後當期真有可用額度。README 與 SKILL.md 的措辭
都刻意留了餘地。

## 2. 安裝與登入指令

| 項目 | 驗證到的寫法 | 怎麼驗的 |
|---|---|---|
| 官方安裝腳本 | `curl -fsSL https://chatgpt.com/codex/install.sh \| sh` | 官方 CLI 頁原文（`learn.chatgpt.com/docs/codex/cli`，2026-08-20） |
| npm | `npm install -g @openai/codex` | `npm view @openai/codex version` 回 `0.148.0`（實跑，2026-08-20） |
| Homebrew | `brew install --cask codex` | `brew info --formula codex` **查無 formula**；`brew info --cask codex` 回 `codex (Codex): 0.147.0`（實跑）。⚠️ 只證明 cask 存在，**未實跑安裝** |
| 互動登入 | `codex login` | `codex login --help`（本機 codex-cli 0.148.0） |
| API key 登入 | `printenv OPENAI_API_KEY \| codex login --with-api-key` | 同上 —— help 原文寫明 `Read the API key from stdin` |
| 驗證登入 | `codex login status` | 實跑，已登入時回 `Logged in using ChatGPT`、退出碼 0 |

🔴 **修正記錄**：本 skill 的設計文件原本寫 `brew install codex`（無 `--cask`）——
實跑會失敗（`No available formula with the name "codex"`）。腳本印出的引導已改成
上表的寫法。⚠️ 代價說清楚：**寫進工具裡的指令一樣會過期，而且比 README 更難改**
（使用者手上是舊版就一直印舊指令）；這裡選擇寫進工具，是因為使用者不會回頭讀 README，
不是因為工具裡的字比較不會爛。

⚠️ 表中版本號（`0.148.0`／`0.147.0`）是**當次觀測值，不是最低需求版本**。

## 3. 沒驗到的部分（誠實標註）

- 官方頁面**沒有標示最後更新日期**，只能確認 2026-08-20 可存取且內容如上。
- `learn.chatgpt.com/docs/codex/auth` 於同日回 **404**；登入指令改以本機
  `codex login --help` 的原文為準（第一手，但只證明 0.148.0 這一版）。
- npm／brew 兩個安裝管道是**套件庫實查**，不是官方文件原文背書；**三條安裝路徑都沒有在
  乾淨環境端到端跑過**（能查到 ≠ 裝得起來）。
- `codex login status` 只驗過「已用 ChatGPT 登入」這個正例；未登入、憑證過期、
  API key 登入、組織封鎖等情況**沒實測**（腳本因此設計成「只在有正面證據時才判定未登入」）。
- `--with-api-key` 走的是 API 計費，與 ChatGPT 方案內含的額度**是不同的帳**；本檔未查證其細節。
- Codex CLI 的**錯誤訊息格式沒有官方保證** —— 腳本的狀態分類是比對文字的啟發式，
  升版可能失準，所以失敗時一律照印原始 stderr。
