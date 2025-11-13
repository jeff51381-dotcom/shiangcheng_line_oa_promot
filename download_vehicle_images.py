#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_vehicle_images.py
下載 CPC 分類（預設：車輛用油）頁面與相關商品頁面的圖片。

用法範例：
  python download_vehicle_images.py --category "車輛用油" --follow-details --workers 6

必要套件：
  pip install requests beautifulsoup4 tqdm
"""
import os
import time
import hashlib
import argparse
import logging
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

# Try to import tqdm for progress bar; fallback if missing
try:
    from tqdm import tqdm
except Exception:
    tqdm = lambda x, **k: x

# 如果你把 product_classification.py 放在同一目錄，直接匯入即可
try:
    from product_classification import classify
except Exception:
    def classify(name):
        # fallback URL for 車輛用油 if product_classification 不在同目錄
        if name == "車輛用油":
            return {"cpc_url": "https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=13"}
        return None

# 設定
USER_AGENT = "ImageDownloader/1.0 (+https://your.domain)"
ALLOWED_IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
DEFAULT_OUTDIR = "downloads/vehicle_oil"
REQUEST_TIMEOUT = 20
RETRY_TIMES = 3
SLEEP_BETWEEN_REQUESTS = 0.8  # rate limiting

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def is_same_origin(a_url, b_url):
    a = urlparse(a_url)
    b = urlparse(b_url)
    return (a.scheme, a.netloc) == (b.scheme, b.netloc)


def sanitize_filename_from_url(url):
    p = urlparse(url)
    name = os.path.basename(p.path) or "index"
    # remove query params
    name = name.split("?")[0]
    if not os.path.splitext(name)[1]:
        # if no ext, add sha suffix
        name = name + "_" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return name


def fetch_url(session, url):
    for attempt in range(1, RETRY_TIMES + 1):
        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp
        except Exception as e:
            logging.debug("fetch error (%s) attempt %d/%d: %s", url, attempt, RETRY_TIMES, e)
            time.sleep(1 * attempt)
    logging.warning("Failed to fetch URL after retries: %s", url)
    return None


def parse_image_urls(base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    imgs = set()
    # 1) <img> tags
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if not src:
            continue
        full = urljoin(base_url, src)
        imgs.add(full)
    # 2) <a> tags that directly link to image files
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(base_url, href)
        if any(full.lower().split("?")[0].endswith(ext) for ext in ALLOWED_IMAGE_EXT):
            imgs.add(full)
    return imgs


def parse_detail_links(base_url, html):
    """解析商品細節頁連結（深度1用）— 會回傳與 base 同源的相對或絕對連結"""
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(base_url, href)
        # 過濾到同一個 domain（避免跑到外站）
        if is_same_origin(base_url, full):
            links.add(full)
    return links


def download_image(session, url, outdir):
    # skip non-image-looking urls early
    if not any(url.lower().split("?")[0].endswith(ext) for ext in ALLOWED_IMAGE_EXT):
        # still attempt to download if server serves correct content-type
        pass
    fname = sanitize_filename_from_url(url)
    path = os.path.join(outdir, fname)
    # avoid re-downloading existing file (quick check)
    if os.path.exists(path):
        return (url, path, "exists")
    try:
        resp = fetch_url(session, url)
        if resp is None:
            return (url, None, "failed")
        # Basic content-type check
        ctype = resp.headers.get("Content-Type", "")
        if not ctype.startswith("image/") and not any(url.lower().endswith(ext) for ext in ALLOWED_IMAGE_EXT):
            logging.debug("skipping non-image content-type %s for %s", ctype, url)
            return (url, None, "not-image")
        # write file
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return (url, path, "ok")
    except Exception as e:
        logging.debug("download error %s: %s", url, e)
        return (url, None, "error")


def check_robots_allowed(base_url, user_agent, target_path="/"):
    # basic robots.txt check
    try:
        parsed = urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        r = requests.get(robots_url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": user_agent})
        if r.status_code != 200:
            return True  # no robots, allow
        from urllib.robotparser import RobotFileParser
        rp = RobotFileParser()
        rp.parse(r.text.splitlines())
        return rp.can_fetch(user_agent, target_path)
    except Exception:
        return True


def main():
    parser = argparse.ArgumentParser(description="Download images for a CPC product category")
    parser.add_argument("--category", default="車輛用油", help="Category name (as in product_classification)")
    parser.add_argument("--outdir", default=DEFAULT_OUTDIR, help="Output directory")
    parser.add_argument("--follow-details", action="store_true", help="Also follow product detail links (depth=1) to find images")
    parser.add_argument("--workers", type=int, default=4, help="Number of concurrent downloads")
    parser.add_argument("--max-detail-pages", type=int, default=30, help="Max number of detail pages to fetch when following details")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    info = classify(args.category)
    if not info or "cpc_url" not in info:
        logging.error("找不到 %s 的分類對應。請確認 product_classification.py 或輸入正確的分類名稱。", args.category)
        return

    start_url = info["cpc_url"]
    logging.info("開始：分類 %s -> %s", args.category, start_url)

    # robots.txt check
    allowed = check_robots_allowed(start_url, USER_AGENT, urlparse(start_url).path)
    if not allowed:
        logging.error("robots.txt 不允許抓取該路徑，停止。")
        return

    os.makedirs(args.outdir, exist_ok=True)
    sess = requests.Session()
    sess.headers.update({"User-Agent": USER_AGENT})

    # fetch category page
    resp = fetch_url(sess, start_url)
    if resp is None:
        logging.error("無法取得分類頁面：%s", start_url)
        return
    html = resp.text

    image_urls = set()
    image_urls.update(parse_image_urls(start_url, html))

    detail_links = set()
    if args.follow_details:
        # 收集分類頁面上的內部連結（可能為多個商品頁面）
        detail_links.update(parse_detail_links(start_url, html))
        logging.info("分類頁面找到 %d 內部連結，會嘗試追訪以搜尋圖片（上限 %d）", len(detail_links), args.max_detail_pages)
        # limit number of pages to avoid過多請求
        detail_links = list(detail_links)[: args.max_detail_pages]
        # Fetch each detail page and parse images
        for link in tqdm(detail_links, desc="Fetching detail pages"):
            time.sleep(SLEEP_BETWEEN_REQUESTS)
            r = fetch_url(sess, link)
            if not r:
                continue
            image_urls.update(parse_image_urls(link, r.text))

    # Filter image URLs to same origin or allow remote?
    # We'll allow same-origin and absolute image links under same domain
    parsed_start = urlparse(start_url)
    image_urls = {u for u in image_urls if urlparse(u).netloc == parsed_start.netloc}

    logging.info("總共發現 %d 圖片候選檔案（同源過濾後）", len(image_urls))

    # download images concurrently
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(download_image, sess, url, args.outdir): url for url in image_urls}
        for f in tqdm(as_completed(futures), total=len(futures), desc="Downloading"):
            # as_completed yields futures as they finish
            res = f.result()
            results.append(res)

    # summarize
    ok = [r for r in results if r[2] == "ok"]
    exists = [r for r in results if r[2] == "exists"]
    failed = [r for r in results if r[2] not in ("ok", "exists")]

    logging.info("下載完成：成功 %d，已存在 %d，失敗 %d", len(ok), len(exists), len(failed))
    if failed:
        logging.info("失敗清單樣本：")
        for r in failed[:10]:
            logging.info(" - %s -> %s", r[0], r[2])

    logging.info("圖片儲存在: %s", os.path.abspath(args.outdir))


if __name__ == "__main__":
    main()