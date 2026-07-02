import feedparser

SECTOR_RSS = {
    "XLK": "https://finance.yahoo.com/rss/headline?s=XLK",
    "SOXX": "https://finance.yahoo.com/rss/headline?s=SOXX",
    "XLV": "https://finance.yahoo.com/rss/headline?s=XLV",
    "XLF": "https://finance.yahoo.com/rss/headline?s=XLF",
    "XLE": "https://finance.yahoo.com/rss/headline?s=XLE",
    "XLI": "https://finance.yahoo.com/rss/headline?s=XLI",
    "XLY": "https://finance.yahoo.com/rss/headline?s=XLY",
    "XLP": "https://finance.yahoo.com/rss/headline?s=XLP",
    "XLC": "https://finance.yahoo.com/rss/headline?s=XLC",
    "XLU": "https://finance.yahoo.com/rss/headline?s=XLU",
    "XLRE": "https://finance.yahoo.com/rss/headline?s=XLRE",
    "XLB": "https://finance.yahoo.com/rss/headline?s=XLB",
}


def get_latest_news() -> dict:
    """각 ETF별 최신 뉴스 제목 1개씩 반환 {symbol: title}"""
    result = {}
    for symbol, url in SECTOR_RSS.items():
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                result[symbol] = feed.entries[0].title[:80]  # 80자 제한
        except Exception:
            pass
    return result
