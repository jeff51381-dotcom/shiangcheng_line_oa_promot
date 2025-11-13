#!/usr/bin/env python3
"""Utility for downloading CPC product images by category.

This script scrapes https://cpclube.cpc.com.tw for the CPC product catalog
and downloads all of the product images belonging to the requested
categories.  Each product receives its own folder so that assets remain
organized even when multiple categories share the same product.

Because the official web site is implemented with ASP.NET WebForms, the
script uses heuristics instead of brittle CSS selectors to locate category
and product links.  The approach was chosen so that the scraper keeps
working even if the site's markup receives minor adjustments.
"""
from __future__ import annotations

import argparse
import itertools
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://cpclube.cpc.com.tw/"
CATALOG_URL = "https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=0"
DEFAULT_CATEGORIES = [
    "車輛用油",
    "海運用油",
    "工業用油",
    "滑脂",
    "基礎油",
]
IMG_NAME_PATTERN = re.compile(r"[^0-9A-Za-z\-._]+")


@dataclass
class DownloadResult:
    """Summary of what happened while downloading a single product."""

    product: str
    images: List[Path]
    skipped: int


class CPCScraper:
    def __init__(self, delay: float = 0.5, retries: int = 3, timeout: int = 15):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            }
        )
        self.delay = delay
        self.retries = retries
        self.timeout = timeout

    # ------------------------------------------------------------------
    # HTTP helpers
    def get_text(self, url: str) -> str:
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:  # pragma: no cover - network error
                if attempt == self.retries:
                    raise
                backoff = self.delay * attempt
                print(f"Request failed ({exc}), retrying in {backoff:.1f}s", file=sys.stderr)
                time.sleep(backoff)
        raise RuntimeError("unreachable")

    def get_binary(self, url: str) -> bytes:
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.content
            except requests.RequestException as exc:  # pragma: no cover - network error
                if attempt == self.retries:
                    raise
                backoff = self.delay * attempt
                print(f"Image request failed ({exc}), retrying in {backoff:.1f}s", file=sys.stderr)
                time.sleep(backoff)
        raise RuntimeError("unreachable")

    # ------------------------------------------------------------------
    def fetch_category_links(self, categories: Sequence[str]) -> Dict[str, str]:
        """Return a mapping from category name to absolute URL."""

        page = self.get_text(CATALOG_URL)
        soup = BeautifulSoup(page, "html.parser")
        wanted = {name: None for name in categories}
        for anchor in soup.find_all("a", href=True):
            normalized = anchor.get_text(strip=True)
            if not normalized:
                continue
            for target in categories:
                if target in normalized and not wanted[target]:
                    wanted[target] = urljoin(BASE_URL, anchor["href"])
        missing = [name for name, url in wanted.items() if not url]
        if missing:
            raise RuntimeError(
                "無法在產品目錄頁面中找到下列分類: " + ", ".join(missing)
            )
        return wanted  # type: ignore[return-value]

    def fetch_products(self, category_url: str) -> Dict[str, str]:
        """Return mapping from product name to detail page."""

        html = self.get_text(category_url)
        soup = BeautifulSoup(html, "html.parser")
        products: Dict[str, str] = {}
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            if "C_Products_Detail" not in href:
                continue
            name = anchor.get_text(strip=True) or anchor.get("title", "").strip()
            if not name:
                continue
            products[name] = urljoin(BASE_URL, href)
        if not products:
            raise RuntimeError(
                "在分類頁面中找不到任何產品項目 (" f"{category_url})."
            )
        return products

    def fetch_product_images(self, product_url: str) -> List[str]:
        html = self.get_text(product_url)
        soup = BeautifulSoup(html, "html.parser")
        candidates: List[str] = []
        for img in soup.find_all("img", src=True):
            src = img["src"]
            lower = src.lower()
            if any(token in lower for token in ("/upload", "product")) and not lower.endswith(".gif"):
                candidates.append(urljoin(BASE_URL, src))
        return list(dict.fromkeys(candidates))  # deduplicate while preserving order


# ----------------------------------------------------------------------
def sanitize_name(value: str) -> str:
    safe = IMG_NAME_PATTERN.sub("_", value.strip())
    safe = safe.strip("._")
    return safe or "product"


def save_images(scraper: CPCScraper, product: str, images: Sequence[str], folder: Path) -> DownloadResult:
    product_dir = folder / sanitize_name(product)
    product_dir.mkdir(parents=True, exist_ok=True)
    downloaded: List[Path] = []
    skipped = 0
    for index, url in enumerate(images, start=1):
        ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
        filename = f"{index:02d}{ext}"
        destination = product_dir / filename
        if destination.exists():
            skipped += 1
            continue
        data = scraper.get_binary(url)
        destination.write_bytes(data)
        downloaded.append(destination)
    return DownloadResult(product=product, images=downloaded, skipped=skipped)


def run(categories: Sequence[str], output: Path, delay: float, retries: int, timeout: int) -> None:
    scraper = CPCScraper(delay=delay, retries=retries, timeout=timeout)
    category_links = scraper.fetch_category_links(categories)
    output.mkdir(parents=True, exist_ok=True)

    for category, url in category_links.items():
        print(f"處理分類: {category} -> {url}")
        products = scraper.fetch_products(url)
        for product, detail_url in products.items():
            print(f"  下載產品: {product}")
            image_urls = scraper.fetch_product_images(detail_url)
            if not image_urls:
                print(f"    ⚠️ 找不到圖片: {detail_url}")
                continue
            result = save_images(scraper, product, image_urls, output / sanitize_name(category))
            print(
                f"    完成 {len(result.images)} 張 (略過 {result.skipped}) -> {result.product}"
            )
            if scraper.delay:
                time.sleep(scraper.delay)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="下載 CPC 產品圖片")
    parser.add_argument(
        "--categories",
        nargs="*",
        default=DEFAULT_CATEGORIES,
        help="要下載的產品分類名稱 (預設: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("downloads"),
        help="圖片輸出資料夾",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="每次請求後的延遲秒數",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="HTTP 失敗時的重試次數",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="請求逾時秒數",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str]) -> int:
    args = parse_args(argv)
    try:
        run(args.categories, args.output, args.delay, args.retries, args.timeout)
    except Exception as exc:  # pragma: no cover - CLI error handler
        print(f"發生錯誤: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entrypoint
    raise SystemExit(main(sys.argv[1:]))
