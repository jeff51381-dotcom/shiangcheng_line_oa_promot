```markdown
## CPC 產品下載（自動化）

本專案新增了用於從台灣中油 (CPC) 下載產品頁面與相關資源的工具與 CI workflow：

- product_classification.py：CPC 分類對照表與 classify(name) 函式。
- download_vehicle_oil.py：範例下載腳本，會下載「車輛用油」分類的頁面與頁面內常見資源（PDF、圖片等），輸出到 downloads/vehicle_oil。
- .github/workflows/download_cpc.yml：可手動觸發或在 push 到 add-product-classification 分支時執行的 GitHub Actions workflow，執行後會把 downloads 目錄上傳為 artifact（名稱：cpc-downloads）。

如何使用（快速上手）：
1. 取得或切換到分支：
   - 若分支已在遠端：  
     git fetch origin  
     git checkout -b add-product-classification origin/add-product-classification  
   - 若要在本機建新分支：  
     git checkout -b add-product-classification

2. （若你尚未新增 workflow）將 `.github/workflows/download_cpc.yml` 放入專案（內容如上）。

3. 確認下載腳本與分類模組在分支裡：
   - product_classification.py
   - download_vehicle_oil.py

4. Commit 並 push：
   git add .github/workflows/download_cpc.yml
   git commit -m "Add GitHub Actions workflow for CPC downloads and update README"
   git push --set-upstream origin add-product-classification

5. 在 GitHub UI 建立 Pull Request（推薦流程）：  
   - PR 標題：Add CPC download script and workflow  
   - PR 描述（可複製）：
     - 新增 product_classification.py（CPC 分類映射）
     - 新增 download_vehicle_oil.py（下載範例腳本）
     - 新增 workflow .github/workflows/download_cpc.yml（手動觸發 / push 觸發）
     - 請 reviewer 特別確認 SYNONYMS 與檔案放置路徑是否符合專案慣例

6. 觸發 workflow：
   - 在 GitHub → Actions → 選擇 "Download CPC Product Pages" → Run workflow（或 push 到 add-product-classification 分支）。
   - 執行完成後至該 run 的 Artifacts 區塊，下載 cpc-downloads artifact。

注意事項
- 若目標網站需要登入或有防爬機制，請把必要憑證、代理或 cookie 放到 repo Secrets，並在 workflow 中以 secrets 使用（不要把憑證寫入程式碼）。
- 請遵守網站使用條款與 robots.txt，避免短時間內大量請求。
- 建議先在開發分支上 review & 測試，再合併到主要分支。
