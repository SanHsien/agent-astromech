# 貢獻指南

感謝你協助改善 agent-astromech。本 fork 接受產品修正、測試、文件與維護工具的貢獻；請先確認變更屬於 `SanHsien/agent-astromech`，不要把 fork 專屬治理誤送到 upstream。

## 開始之前

1. 閱讀 `AGENTS.md`、`CLAUDE.md` 與 `docs/DEVELOPMENT.md`。
2. 從最新 `main` 開始，保持變更單一目的。
3. 不提交憑證、個資、私人 prompt 或真實 review 內容。
4. 行為修正先加入失敗測試；文件修正要同步繁中／英文契約。

## 驗證

Windows：

```powershell
pwsh -NoProfile -File tools\dev_check.ps1
```

Linux／macOS：

```bash
sh tools/dev_check.sh
```

送出前再跑 `git diff --check`，並人工閱讀完整 diff。Git Bash／NTFS 無法證明 POSIX `0600` mode bit；該安全斷言由 Linux CI 負責。

## Commit 與 PR

- 使用 Conventional Commits。
- 外部貢獻從最新 `main` 建 branch，經 `SanHsien/agent-astromech` PR 與 required checks 合併。
- 維護者的日常變更直接推 `main`（分支保護不對管理者強制），只有需要他人審查或高風險改動才退回 branch → PR。直推一樣會觸發 CI，但那是在 commit 已經落在 `main` 之後——紅燈擋不住它，只會留下壞掉的 `main`。所以直推前要在本機跑完整 gate。
- PR 需說明問題、解法、風險與實際驗證證據。
- PR 一律建立在 `SanHsien/agent-astromech`；回貢 upstream 必須另取得維護者明確授權。
- CI 綠燈不取代 diff review。
