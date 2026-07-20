# app/services/news_service.py
"""
뉴스 서비스 — 중장기 투자 관점 감성 분석 포함
  - 헤드라인 최대 3개 수집
  - LLM으로 '6개월~2년 장기 영향' 기준 감성 점수 산출
    +1: 장기 긍정 (구조적 성장, 정책 수혜, 실적 개선 등)
     0: 중립 또는 단기 이벤트 (단발성 뉴스, 불확실)
    -1: 장기 부정 (구조적 침체, 규제 리스크, 섹터 쇠퇴 등)
"""

import os
import json
import hashlib
from datetime import datetime, timedelta

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

NEWS_CACHE_FILE = "logs/news_sentiment_cache.json"
NEWS_CACHE_TTL = 23 * 60  # 23시간


# ── 캐시 (파일 실패 시 예외 전파 없이 무시) ────────────
def _news_cache_key(symbol: str, headlines: list[str]) -> str:
    raw = symbol + "|".join(headlines)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _load_news_cache() -> dict:
    try:
        if not os.path.exists(NEWS_CACHE_FILE):
            return {}
        with open(NEWS_CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[뉴스 캐시 로드 실패 — 무시] {e}")
        return {}


def _save_news_cache(cache: dict):
    try:
        os.makedirs("logs", exist_ok=True)
        now = datetime.now()
        cache = {
            k: v for k, v in cache.items() if datetime.fromisoformat(v["expires"]) > now
        }
        with open(NEWS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # ✅ 파일 저장 실패해도 예외 전파 X
        print(f"[뉴스 캐시 저장 실패 — 무시] {e}")


def _get_news_cached(key: str) -> dict | None:
    try:
        cache = _load_news_cache()
        entry = cache.get(key)
        if not entry:
            return None
        if datetime.now() > datetime.fromisoformat(entry["expires"]):
            return None
        return entry["data"]
    except Exception:
        return None


def _set_news_cached(key: str, data: dict):
    try:
        cache = _load_news_cache()
        cache[key] = {
            "data": data,
            "expires": (datetime.now() + timedelta(minutes=NEWS_CACHE_TTL)).isoformat(),
        }
        _save_news_cache(cache)
    except Exception as e:
        print(f"[뉴스 캐시 set 실패 — 무시] {e}")


# ── 헤드라인 수집 ──────────────────────────────────────
def get_latest_news(max_per_symbol: int = 3) -> dict:
    result = {}
    for symbol, url in SECTOR_RSS.items():
        try:
            feed = feedparser.parse(url)
            titles = [
                e.title[:100]
                for e in feed.entries[:max_per_symbol]
                if hasattr(e, "title")
            ]
            if titles:
                result[symbol] = titles
        except Exception:
            pass
    return result


# ── 장기 감성 분석 (LLM) ────────────────────────────────
def analyze_news_sentiment_longterm(
    news: dict,
    symbols: list[str],
) -> dict:
    """
    LLM으로 각 섹터 ETF 뉴스의 '6개월~2년 장기 영향' 감성 점수 산출
    반환: {symbol: {"score": int, "reason": str}}
      score: +1 (장기 긍정) / 0 (중립·단기) / -1 (장기 부정)
    """
    from app.services.llm_service import ask_llm

    target_news = {sym: news.get(sym, []) for sym in symbols if sym in news}
    if not target_news:
        return {sym: {"score": 0, "reason": "no news"} for sym in symbols}

    cache_key = _news_cache_key(
        "sentiment", [f"{s}:{h}" for s, hs in sorted(target_news.items()) for h in hs]
    )
    cached = _get_news_cached(cache_key)
    if cached:
        print("[뉴스 캐시 히트] 감성 분석 생략")
        return cached

    news_block = "\n".join(
        f"{sym}: {' | '.join(titles)}" for sym, titles in target_news.items()
    )

    system_prompt = (
        "You are a long-term sector analyst (6-month to 2-year horizon). "
        "Evaluate each sector ETF's news headlines for STRUCTURAL, LONG-TERM impact only.\n\n"
        "Scoring rules (strict):\n"
        "  +1: Structural tailwind — policy support, secular growth trend, "
        "      multi-year earnings cycle, major capex expansion\n"
        "   0: Neutral or SHORT-TERM only — quarterly beat/miss, "
        "      one-time events, temporary volatility, unclear impact\n"
        "  -1: Structural headwind — regulatory crackdown with lasting effect, "
        "      secular demand destruction, paradigm shift away from sector\n\n"
        "IMPORTANT: Single earnings reports, CEO changes, or macro data prints "
        "are almost always 0 (short-term). Only score +1 or -1 for clearly "
        "multi-year structural changes.\n\n"
        "Return ONLY compact JSON, no prose:\n"
        '{"XLK":{"score":1,"reason":"AI capex supercycle"},'
        '"XLE":{"score":-1,"reason":"IRA accelerates fossil fuel decline"}}'
    )

    user_prompt = (
        f"Analyze these sector ETF headlines for 6mo~2yr structural impact:\n\n"
        f"{news_block}\n\n"
        "Reply ONLY JSON."
    )

    result = ask_llm(system_prompt + "\n\n" + user_prompt)
    raw = result.get("text", "{}")

    try:
        if "```" in raw:
            for part in raw.split("```"):
                if "{" in part:
                    raw = part.strip()
                    break
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        parsed = json.loads(raw)
    except Exception:
        print(f"[뉴스 감성 파싱 오류] {raw[:100]}")
        parsed = {}

    sentiment = {}
    for sym in symbols:
        entry = parsed.get(sym, {})
        score = entry.get("score", 0) if isinstance(entry, dict) else 0
        score = max(-1, min(1, int(score)))
        sentiment[sym] = {
            "score": score,
            "reason": (
                entry.get("reason", "no signal")
                if isinstance(entry, dict)
                else "no signal"
            ),
        }

    _set_news_cached(cache_key, sentiment)
    return sentiment
