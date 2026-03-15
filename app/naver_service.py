from typing import Any

import requests


NAVER_ETF_URL = "https://finance.naver.com/api/sise/etfItemList.nhn"


def fetch_etf_items() -> list[dict[str, str]]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://finance.naver.com/",
    }
    response = requests.get(NAVER_ETF_URL, headers=headers, timeout=10)
    response.raise_for_status()
    data: dict[str, Any] = response.json()
    items = data.get("result", {}).get("etfItemList", [])
    result: list[dict[str, str]] = []
    for item in items:
        symbol = str(item.get("itemcode", "")).strip()
        name = str(item.get("itemname", "")).strip()
        if symbol and name and len(symbol) == 6:
            result.append({"symbol": symbol, "name": name, "market": "ETF"})
    return result
