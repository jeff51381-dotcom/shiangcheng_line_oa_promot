#!/usr/bin/env python3
# 檢查 CPC 分類頁面可存取性（列印 status code / headers / 简短 body sample）
import requests
from urllib.parse import urlparse
import sys

URL = "https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=13"
UA_SIMPLE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0 Safari/537.36"

def try_request(url, headers=None):
    try:
        r = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
        print("Status:", r.status_code)
        print("Final URL:", r.url)
        print("Headers (response):")
        for k,v in r.headers.items():
            print("  ", k, ":", v)
        print("\nBody sample (first 1000 chars):\n")
        print(r.text[:1000])
    except Exception as e:
        print("Request error:", e)

def main():
    print("1) 直接無 header 請求")
    try_request(URL)
    print("\n2) 加 Browser-like User-Agent")
    try_request(URL, headers={"User-Agent": UA_SIMPLE})
    print("\n3) 用 HEAD 檢查")
    try:
        h = requests.head(URL, headers={"User-Agent": UA_SIMPLE}, timeout=15, allow_redirects=True)
        print("HEAD status:", h.status_code)
        print("HEAD headers sample:")
        for k in ["content-type","server","set-cookie","vary","x-frame-options"]:
            if k in h.headers:
                print("  ", k, ":", h.headers[k])
    except Exception as e:
        print("HEAD error:", e)

if __name__ == '__main__':
    main()