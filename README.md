# CPC 產品圖片下載工具

這個專案提供 `cpcl_image_downloader.py`，可從中油 CPC 的產品型錄頁面中抓取指定分類的產品圖片，並依產品名稱建立資料夾。

## 需求
- Python 3.9+
- `requests`
- `beautifulsoup4`

安裝方式：

```bash
pip install -r requirements.txt
```

## 使用方式

```bash
python cpcl_image_downloader.py \
    --categories 車輛用油 海運用油 工業用油 滑脂 基礎油 \
    --output ./downloads \
    --delay 0.5
```

- `--categories`：自訂要下載的分類名稱，預設即為上例中的五個分類。
- `--output`：下載資料夾 (預設 `./downloads`)。
- `--delay`：每一次 HTTP 請求後的延遲秒數，避免對官方網站造成過大壓力。
- `--retries` 與 `--timeout` 也可視需要調整。

腳本會依序：
1. 在分類列表頁中找出匹配的分類連結。
2. 掃描分類頁面內的所有產品，抓取詳細頁網址。
3. 在產品詳細頁面搜尋圖片連結並下載。
4. 以「分類/產品名稱」建立資料夾儲存圖片，若檔案已存在則自動略過。

> **注意**：中油網站屬於 ASP.NET WebForms，若官方有調整 HTML 版型，請更新腳本內的選擇條件或直接指定新的分類網址。

## 限制與建議
- 為降低被封鎖的風險，建議將 `--delay` 設為 0.5 秒以上。
- 若分類名稱未出現在型錄首頁，腳本會提示錯誤，可直接修改 `cpcl_image_downloader.py` 內的 `CATALOG_URL` 或手動指定分類連結。
- 圖片檔名會自動以流水號 `01.jpg`, `02.jpg` ... 命名，以便區分同一產品的多張圖片。
