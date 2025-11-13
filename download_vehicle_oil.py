# download_vehicle_oil.py
# 簡單範例：用 product_classification 取得車輛用油的 CPC 網頁，再下載頁面與頁面中常見檔案 (pdf, jpg, png)

import os
import time
import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from product_classification import classify

# 設定
OUT_DIR = "downloads/vehicle_oil"
USER_AGENT = "MyDownloader/1.0 (+https://yourdomain.example)"
SLEEP_BETWEEN_DOWNLOADS = 1.0  # 秒，避免打到伺服器太快

os.makedirs(OUT_DIR, exist_ok=True)

def download_url(url, dest_path):
    headers = {"User-Agent": USER_AGENT}
    with requests.get(url, headers=headers, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

def sanitize_filename(url):
    p = urlparse(url)
    name = os.path.basename(p.path) or "index.html"
    # fallback: remove query
    return name.split("?")[0]

def main():
    info = classify("車輛用油")
    if not info:
        print("找不到對應的 CPC 分類")
        return
    url = info["cpc_url"]
    print("CPC 頁面 URL:", url)

    # 1) 下載整個 HTML 頁面
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    html_path = os.path.join(OUT_DIR, "page.html")
    with open(html_path, "w", encoding=resp.encoding or "utf-8") as f:
        f.write(resp.text)
    print("已下載 HTML 到:", html_path)

    # 2) 解析並搜尋常見檔案連結 (pdf, jpg, png, zip)
    soup = BeautifulSoup(resp.text, "html.parser")
    tags = soup.find_all(["a", "img"])
    seen = set()
    for t in tags:
        href = t.get("href") or t.get("src")
        if not href:
            continue
        full = urljoin(url, href)
        if full in seen:
            continue
        seen.add(full)
        # 只抓常見檔案類型
        if any(full.lower().endswith(ext) for ext in [".pdf", ".zip", ".jpg", ".jpeg", ".png", ".gif"]):
            fname = sanitize_filename(full)
            dest = os.path.join(OUT_DIR, fname)
            try:
                print("下載:", full, "->", dest)
                download_url(full, dest)
                time.sleep(SLEEP_BETWEEN_DOWNLOADS)
            except Exception as e:
                print("下載失敗:", full, e)

    print("完成。檔案會放在:", os.path.abspath(OUT_DIR))

if __name__ == "__main__":
    main()