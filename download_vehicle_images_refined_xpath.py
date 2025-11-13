#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Refined downloader with XPath support.

Usage examples:
  pip install cloudscraper beautifulsoup4 lxml tqdm
  python download_vehicle_images_refined_xpath.py --category "車輛用油" --img-xpath '//*[@id="ContentPlaceHolder1_divMarqueePics"]/div/div/div/div/ul/li/div/div/div/div/span' --list-only
  python download_vehicle_images_refined_xpath.py --category "車輛用油" --img-xpath '...same...' --download

Notes:
- The script will look for <img> inside the XPath nodes, or try to parse background-image from style attributes.
- If the XPath points to a container linking to a product detail page instead of directly to an image,
  the script will try to extract the nearest ancestor <a href="..."> and follow that page (if --follow-details).
"""
import os
import re
import json
import time
import hashlib
import argparse
from urllib.parse import urljoin, urlparse

from tqdm import tqdm
from bs4 import BeautifulSoup

try:
    import cloudscraper
except Exception:
    cloudscraper = None

try:
    import lxml.html
except Exception:
    lxml = None
    lxml_html = None
else:
    lxml_html = lxml.html

ALLOWED_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
DEFAULT_OUTDIR = "downloads/vehicle_oil_xpath"
REQUEST_TIMEOUT = 30
SLEEP = 0.6

def sanitize_name(url):
    p = urlparse(url)
    name = os.path.basename(p.path) or "image"
    name = name.split("?")[0]
    if not os.path.splitext(name)[1]:
        name = name + "_" + hashlib.sha1(url.encode()).hexdigest()[:8]
    return name

def extract_url_from_style(style_value):
    # extract url(...) from style background-image
    m = re.search(r'url\((["\']?)(.*?)\1\)', style_value, flags=re.IGNORECASE)
    if m:
        return m.group(2)
    # fallback: look for plain url without parentheses
    m2 = re.search(r'url[:=]\s*(["\']?)(.*?)\1', style_value, flags=re.IGNORECASE)
    if m2:
        return m2.group(2)
    return None

def images_from_xpath_html(base_url, html, xpath_expr):
    """
    Use lxml to evaluate xpath_expr against html and return list of image dicts:
    {"url": full_url, "alt": alt_text, "node": repr}
    """
    if lxml_html is None:
        raise RuntimeError("lxml is required for XPath mode. Install with: pip install lxml")
    doc = lxml_html.fromstring(html)
    # ensure returned nodes for the xpath
    nodes = doc.xpath(xpath_expr)
    results = []
    for node in nodes:
        # node may be an element, get inner <img> if present
        try:
            imgs = node.xpath('.//img')
        except Exception:
            imgs = []
        if imgs:
            for im in imgs:
                src = im.get('src') or im.get('data-src') or im.get('data-original') or ''
                alt = (im.get('alt') or '').strip()
                if src:
                    full = urljoin(base_url, src)
                    results.append({"url": full, "alt": alt, "node": lxml_html.tostring(node, encoding='unicode', with_tail=False)[:200]})
                    continue
        # if no <img>, check node's style attribute for background-image
        style = node.get('style') if hasattr(node, 'get') else None
        if style:
            found = extract_url_from_style(style)
            if found:
                full = urljoin(base_url, found)
                results.append({"url": full, "alt": "", "node": lxml_html.tostring(node, encoding='unicode', with_tail=False)[:200]})
                continue
        # if still nothing, maybe the node itself has data-* attributes with image url
        for attr in ('data-src', 'data-original', 'data-image', 'data-bg'):
            val = node.get(attr) if hasattr(node, 'get') else None
            if val:
                full = urljoin(base_url, val)
                results.append({"url": full, "alt": "", "node": lxml_html.tostring(node, encoding='unicode', with_tail=False)[:200]})
                break
        # Lastly, try if the node contains a parent <a> linking to a detail page
        # That will be handled by caller if follow-details is enabled
    # dedupe
    seen = set()
    uniq = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            uniq.append(r)
    return uniq

def parse_images_from_html(base_url, html, img_selector=None):
    soup = BeautifulSoup(html, "html.parser")
    imgs = []
    if img_selector:
        nodes = soup.select(img_selector)
        for img in nodes:
            src = img.get("src") or img.get("data-src")
            if not src:
                continue
            full = urljoin(base_url, src)
            imgs.append({"url": full, "alt": img.get("alt") or "", "node": str(img)[:200]})
    else:
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")
            if not src:
                continue
            full = urljoin(base_url, src)
            imgs.append({"url": full, "alt": img.get("alt") or "", "node": str(img)[:200]})
        for a in soup.find_all("a"):
            href = a.get("href")
            if not href:
                continue
            full = urljoin(base_url, href)
            if any(full.lower().split("?")[0].endswith(ext) for ext in ALLOWED_EXT):
                imgs.append({"url": full, "alt": a.get_text(strip=True) or "", "node": str(a)[:200]})
    # dedupe
    seen = set()
    uniq = []
    for i in imgs:
        if i["url"] not in seen:
            seen.add(i["url"])
            uniq.append(i)
    return uniq

def fetch_with_scraper(scraper, url, timeout=REQUEST_TIMEOUT):
    try:
        r = scraper.get(url, timeout=timeout)
        r.raise_for_status()
        return r
    except Exception:
        return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default="車輛用油")
    parser.add_argument("--img-xpath", default=None, help="XPath to target nodes on page")
    parser.add_argument("--img-selector", default=None, help="CSS selector (fallback)")
    parser.add_argument("--follow-details", action="store_true", help="Follow detail pages")
    parser.add_argument("--download", action="store_true", help="Download matched images")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL verification (test only)")
    parser.add_argument("--outdir", default=DEFAULT_OUTDIR)
    parser.add_argument("--list-only", action="store_true", help="Only list candidates, don't download")
    args = parser.parse_args()

    if cloudscraper is None:
        print("Please install cloudscraper: pip install cloudscraper")
        return
    if args.img_xpath and lxml_html is None:
        print("XPath mode requires lxml: pip install lxml")
        return

    # get category url from product_classification if available
    try:
        from product_classification import classify
        info = classify(args.category)
    except Exception:
        info = None
    if not info:
        info = {"cpc_url": "https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=13"}
    start_url = info["cpc_url"]
    print("Start URL:", start_url)

    scraper = cloudscraper.create_scraper(browser={"custom": "Mozilla/5.0"})
    if args.insecure:
        scraper.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        print("WARNING: SSL verification disabled (insecure)")

    os.makedirs(args.outdir, exist_ok=True)

    # fetch category page
    print("Fetching category page...")
    r = fetch_with_scraper(scraper, start_url)
    if not r:
        print("Failed to fetch category page.")
        return
    cat_html = r.text

    candidates = []
    # XPath mode
    if args.img_xpath:
        try:
            matches = images_from_xpath_html(start_url, cat_html, args.img_xpath)
            for m in matches:
                candidates.append({"source": start_url, "image": m})
        except Exception as e:
            print("XPath extraction error:", e)
    # CSS / default mode
    if args.img_selector and not candidates:
        matches = parse_images_from_html(start_url, cat_html, img_selector=args.img_selector)
        for m in matches:
            candidates.append({"source": start_url, "image": m})
    # fallback to generic parsing if still empty
    if not candidates:
        matches = parse_images_from_html(start_url, cat_html)
        for m in matches:
            candidates.append({"source": start_url, "image": m})

    # If follow-details is requested and XPath points to a container with links, we may want to find detail links:
    detail_links = []
    if args.follow_details:
        # simple same-origin anchor collection
        soup = BeautifulSoup(cat_html, "html.parser")
        for a in soup.find_all("a", href=True):
            full = urljoin(start_url, a['href'])
            if urlparse(full).netloc == urlparse(start_url).netloc:
                detail_links.append(full)
        # optionally trim
        detail_links = list(dict.fromkeys(detail_links))[:60]
        # fetch each and run xpath/selector on detail pages
        for link in tqdm(detail_links, desc="Detail pages"):
            time.sleep(SLEEP)
            rr = fetch_with_scraper(scraper, link)
            if not rr:
                continue
            html = rr.text
            if args.img_xpath:
                try:
                    matches = images_from_xpath_html(link, html, args.img_xpath)
                except Exception:
                    matches = []
            else:
                matches = parse_images_from_html(link, html, img_selector=args.img_selector)
            for m in matches:
                candidates.append({"source": link, "image": m})

    # filter same-origin and dedupe
    parsed_start = urlparse(start_url)
    final = []
    seen = set()
    for c in candidates:
        u = c["image"]["url"]
        if urlparse(u).netloc != parsed_start.netloc:
            continue
        if u in seen:
            continue
        seen.add(u)
        final.append(c)

    manifest = {"start_url": start_url, "candidates": final}
    with open(os.path.join(args.outdir, "candidates.json"), "w", encoding="utf-8") as jf:
        json.dump(manifest, jf, ensure_ascii=False, indent=2)
    print("Saved candidates manifest:", os.path.join(args.outdir, "candidates.json"))
    print(f"Found {len(final)} image candidates.")

    for i, it in enumerate(final[:40], 1):
        print(f"[{i}] source: {it['source']}")
        print("    url :", it['image']['url'])
        print("    alt :", it['image'].get('alt','')[:140])
        print("    node:", it['image'].get('node','')[:200])

    if args.download and final and not args.list_only:
        print("Downloading images...")
        for it in tqdm(final, desc="Downloading"):
            u = it["image"]["url"]
            fname = sanitize_name(u)
            dest = os.path.join(args.outdir, fname)
            if os.path.exists(dest):
                continue
            try:
                rr = scraper.get(u, timeout=REQUEST_TIMEOUT, stream=True)
                if rr.status_code == 200 and rr.headers.get("content-type","").startswith("image"):
                    with open(dest, "wb") as f:
                        for chunk in rr.iter_content(8192):
                            if chunk:
                                f.write(chunk)
                    time.sleep(SLEEP)
                else:
                    continue
            except Exception as e:
                print("Download error for", u, e)
        print("Downloaded images to:", os.path.abspath(args.outdir))

if __name__ == "__main__":
    import argparse
    main()