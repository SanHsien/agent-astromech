# Fork 維護說明

本 repo fork 自 [`tingyulu/MyR2D2`](https://github.com/tingyulu/MyR2D2)，保留完整 Git 歷史、agent-astromech 產品名稱、原作者 Eric Lu（tingyulu）的著作權聲明與 MIT License。

## 為什麼維護這個 fork

上游提供可直接安裝的繁中 Agent Skills，以及以另一模型家族做二審的 `ai-review`。本 fork 不重寫產品概念，而是補上可重複的 Windows 開發入口、跨平台驗證、維護治理與 upstream 水位，讓本機結果、CI 與遠端狀態能對應到同一個 commit。

## 本 fork 增加的內容

- Windows PowerShell 與 POSIX canonical gates。
- repo contract 與 upstream checker 的自動化測試。
- GitHub Actions、CodeQL、Dependabot、issue／PR 模板。
- `AGENTS.md`、貢獻、安全、開發、決策與 upstream ledger。
- 可追溯的 repository review ledger（[`docs/REVIEW.md`](docs/REVIEW.md)）。
- Windows／NTFS 與 POSIX 權限語義的明確邊界。
- `mission-log` 在 Windows 的 UTF-8、主機名稱與時區邊界修正。

## 不改變的內容

- agent-astromech 名稱與 `agent-astromech` plugin identifier。
- 上游 12 支 skill 的既有指令；`mission-log` 只新增可選的 `--timezone`，舊用法維持有效。
- 上游作者歸屬與 MIT License。
- `CLAUDE.md` 規定的雙語連動、去識別化與發布原則。

## 同步方法

```bash
git fetch upstream main
python tools/check_upstream_updates.py --strict
```

逐筆判斷後才 merge、cherry-pick 或最小重作。決策先寫入 [`docs/UPSTREAM.md`](docs/UPSTREAM.md)，完整 gate 通過後才推進 baseline。除非維護者在當次對話明確授權，所有對外寫入只指向 `SanHsien/agent-astromech`。
