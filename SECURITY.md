# 安全政策

## 回報漏洞

請使用 GitHub 的 private vulnerability reporting 向 `SanHsien/agent-astromech` 回報。若該功能不可用，請先建立不含利用細節的最小 issue，等維護者提供私人管道。不要在公開 issue、PR 或 review 輸出中放入 token、個資、未公開漏洞細節或可直接利用的 payload。

## 資料邊界

`ai-review` 會把指定內容送往外部模型後端。執行前必須自行移除憑證、個資、客戶資料與未公開程式碼；本 repo 無法撤回已送出的內容，也不替第三方服務提供保留期或資料使用保證。

## 本機輸出

- POSIX 環境會以私有暫存檔與 `0600` 結果檔降低同機暴露風險。
- Git Bash 位於 NTFS 時，`ls -l` 的 mode bit 不能證明 Windows ACL。需要嚴格隔離時，改在 Linux filesystem 執行並核對實際權限。
- 測試涵蓋同秒碰撞、暫存殘留與 symlink 攻擊，但不宣稱能抵抗已控制同一帳號或具管理權限的攻擊者。
- `.ai-reviews/` 已忽略；不要把真實 review 產物加入版本控制。

支援範圍與驗證方式見 [`docs/TEST_PLAN.md`](docs/TEST_PLAN.md)。
