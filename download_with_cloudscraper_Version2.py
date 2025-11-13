# 使用 cloudscraper 嘗試取得分類頁並下載圖片
# 新增 --insecure 選項，若目標站 TLS 有問題可暫時使用（不建議在生產）

import os
import time
import hashlib
import argparse
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import cloudscraper
from tqdm import tqdm

DEFAULT_OUTDIR = "downloads/vehicle_oil"
ALLOWED_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
SLEEP = 0.8

def sanitize(url):
    p = urlparse(url)
    name = os.path.basename(p.path) or "image"
    name = name.split("?")[0]
    if not os.path.splitext(name)[1]:
        name = name + "_" + hashlib.sha1(url.encode()).hexdigest()[:8]
    return name

def parse_images(base_url, html):
    soup = BeautifulSoup(html, "html.parser")
    imgs = set()
    for t in soup.find_all("img"):
        src = t.get("src") or t.get("data-src")
        if not src: continue
        imgs.add(urljoin(base_url, src))
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href: continue
        full = urljoin(base_url, href)
        if any(full.lower().split("?")[0].endswith(ext) for ext in ALLOWED_EXT):
            imgs.add(full)
    return imgs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--insecure", action="store_true", help="Disable SSL verification (insecure)")
    args = parser.parse_args()

    start_url = "https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=13"
    outdir = DEFAULT_OUTDIR
    os.makedirs(outdir, exist_ok=True)

    print("Creating cloudscraper session...")
    # cloudscraper uses requests under the hood; can pass verify via .get(verify=...) or override session.verify
    scraper = cloudscraper.create_scraper(browser={"custom": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36"})
    if args.insecure:
        scraper.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("WARNING: SSL verification is disabled (insecure).")

    print("Fetching:", start_url)
    try:
        r = scraper.get(start_url, timeout=30)
        print("Status code:", r.status_code)
        if r.status_code != 200:
            print("Non-200 response, headers:", r.headers)
            return
    except Exception as e:
        print("Request failed:", e)
        return

    imgs = parse_images(start_url, r.text)
    print("Found", len(imgs), "candidate images (raw).")
    parsed = urlparse(start_url)
    imgs = [u for u in imgs if urlparse(u).netloc == parsed.netloc]
    print("After same-origin filter:", len(imgs))

    for u in tqdm(imgs):
        fname = sanitize(u)
        dest = os.path.join(outdir, fname)
        if os.path.exists(dest):
            continue
        try:
            rr = scraper.get(u, timeout=30, stream=True)
            if rr.status_code == 200 and rr.headers.get("content-type","").startswith("image"):
                with open(dest, "wb") as f:
                    for chunk in rr.iter_content(8192):
                        if chunk:
                            f.write(chunk)
                time.sleep(SLEEP)
            else:
                print("Skipping non-image or bad status for", u, rr.status_code, rr.headers.get("content-type"))
        except Exception as e:
            print("Download error for", u, e)

    print("Done. images saved to", os.path.abspath(outdir))

if __name__ == "__main__":
    main()