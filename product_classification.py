# -*- coding: utf-8 -*-
"""
product_classification.py

Centralized product classification mapping and helpers for shiangcheng_line_oa_promot.

Purpose:
- Provide a single source of truth for product categories and their CPC mappings.
- Make it easy to import and use in serializers, DB seeds, APIs, and templates.

Usage examples:
from product_classification import classify, CPC_CATEGORIES, normalize_name
classify("車輛用油")
classify("vehicular oil")  # if you add synonyms below
"""

from typing import Dict, Optional

# Canonical categories and their CPC links / ids
CPC_CATEGORIES: Dict[str, Dict[str, str]] = {
    "車輛用油": {
        "cpc_name": "車輛用油",
        "cpc_url": "https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=13",
        "cpc_csn": "13",
    },
    "海運用油": {
        "cpc_name": "海運用油",
        "cpc_url": "https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=14",
        "cpc_csn": "14",
    },
    "工業用油": {
        "cpc_name": "工業用油",
        "cpc_url": "https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=64",
        "cpc_csn": "64",
    },
    "滑脂": {
        "cpc_name": "滑脂",
        "cpc_url": "https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=76",
        "cpc_csn": "76",
    },
    "基礎油": {
        "cpc_name": "基礎油",
        "cpc_url": "https://cpclube.cpc.com.tw/C_Products.aspx?n=7464&sms=12326&_CSN=77",
        "cpc_csn": "77",
    },
}

# Optional synonyms mapping to canonical keys (extend as needed)
SYNONYMS: Dict[str, str] = {
    # Chinese variants
    "車用機油": "車輛用油",
    "機車用油": "車輛用油",
    # English examples - add as required
    "vehicle oil": "車輛用油",
    "marine oil": "海運用油",
    "industrial oil": "工業用油",
    "grease": "滑脂",
    "base oil": "基礎油",
}


def normalize_name(name: str) -> str:
    """
    Normalize input name to the canonical category key.

    - Strips whitespace and lowercases ASCII.
    - Maps known synonyms to canonical names.
    - If exact match to canonical exists, returns it.
    - Otherwise returns the original stripped name.
    """
    if not name:
        return ""
    key = name.strip()
    lower = key.lower()
    # match synonyms by lowercased keys
    for syn, canon in SYNONYMS.items():
        if syn.lower() == lower:
            return canon
    # direct canonical match
    for canon in CPC_CATEGORIES.keys():
        if canon == key:
            return canon
        if canon.lower() == lower:
            return canon
    # fallback: return stripped original (caller may handle)
    return key


def classify(name: str) -> Optional[Dict[str, str]]:
    """
    Return classification info for a product name.

    - If name maps to a canonical CPC category, returns the CPC_CATEGORIES entry.
    - Otherwise returns None.
    """
    canon = normalize_name(name)
    return CPC_CATEGORIES.get(canon)

# Example quick test (run manually)
if __name__ == "__main__":
    examples = [
        "車輛用油",
        "車用機油",
        "marine oil",
        "基礎油",
        "unknown category",
    ]
    for e in examples:
        print(f"Input: {e!r} -> Normalized: {normalize_name(e)!r} -> Classification: {classify(e)}")