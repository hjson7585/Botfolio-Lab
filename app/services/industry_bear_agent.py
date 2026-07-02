import json
import os
import re
import hashlib
from datetime import datetime, timedelta

import yfinance as yf
import numpy as np

from app.services.llm_service import ask_llm
from app.services.news_service import get_latest_news
from app.services.trade_service import buy_stock, sell_stock

LOG_FILE = "logs/ai_logs.json"
CACHE_FILE = "logs/response_cache.json"
CACHE_TTL_MINUTES = 25  # 30분 스케줄러보다 짧게

INDUSTRY_ETFS = {
    "XLK": "Technology",
    "SOXX": "Semiconductors",
    "XLV": "Healthcare",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLY": "ConsumerDisc",
    "XLP": "ConsumerStap",
    "XLC": "Communication",
    "XLU": "Utilities",
    "XLRE": "RealEstate",
    "XLB": "Materials",
}

MAX_POSITIONS = 5  # 최대 동시 보유 ETF 수
STOP_LOSS_PCT = -8.0  # 손절 기준 (%)
TAKE_PROFIT_PCT = 15.0  # 익절 기준 (%)
MIN_SCORE = 2  # 매수 최소 점수 (0~4)


# ── 응답 캐시 ──────────────────────────────────────────
def _cache_key(data: str) -> str:
    return hashlib.md5(data.encode()).hexdigest()[:12]


def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict):
    os.makedirs("logs", exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def get_cached(key: str) -> dict | None:
    cache = load_cache()
    entry = cache.get(key)
    if not entry:
        return None
    expires = datetime.fromisoformat(entry["expires"])
    if datetime.now() > expires:
        return None
    return entry["parsed"]


def set_cached(key: str, parsed: dict):
    cache = load_cache()
    cache[key] = {
        "parsed": parsed,
        "expires": (datetime.now() + timedelta(minutes=CACHE_TTL_MINUTES)).isoformat(),
    }
    # 오래된 캐시 정리
    now = datetime.now()
    cache = {
        k: v for k, v in cache.items() if datetime.fromisoformat(v["expires"]) > now
    }
    save_cache(cache)


# ── yfinance 데이터 수집 ──────────────────────────────
def compute_etf_scores() -> list[dict]:
    """
    각 ETF 점수 계산 (0~4점)
    기준:
      +1 price > SMA50 (단기 상승 추세)
      +1 price > SMA200 (장기 상승 추세)
      +1 RSI 45~65 (과열/과매도 아닌 모멘텀 구간)
      +1 1mo 수익률 > 0 (양의 모멘텀)
    """
    results = []
    for symbol in INDUSTRY_ETFS:
        try:
            hist = yf.Ticker(symbol).history(period="3mo", interval="1d")
            if len(hist) < 50:
                continue

            closes = hist["Close"].values.astype(float)
            price = round(float(closes[-1]), 2)
            sma50 = round(float(np.mean(closes[-50:])), 2)
            sma200_available = len(closes) >= 60
            sma200 = (
                round(float(np.mean(closes[-60:])), 2) if sma200_available else sma50
            )

            # RSI(14)
            delta = np.diff(closes[-15:])
            gain = np.mean(np.where(delta > 0, delta, 0))
            loss = np.mean(np.where(delta < 0, -delta, 0))
            rsi = round(100 - 100 / (1 + gain / loss) if loss != 0 else 100.0, 1)

            # 1개월 수익률
            mo1_price = float(closes[-21]) if len(closes) >= 21 else float(closes[0])
            mo1_ret = round((price - mo1_price) / mo1_price * 100, 2)

            # 3개월 수익률
            mo3_ret = round((price - float(closes[0])) / float(closes[0]) * 100, 2)

            # 점수 계산
            score = 0
            if price > sma50:
                score += 1
            if price > sma200:
                score += 1
            if 45 <= rsi <= 65:
                score += 1
            if mo1_ret > 0:
                score += 1

            results.append(
                {
                    "etf": symbol,
                    "sector": INDUSTRY_ETFS[symbol],
                    "price": price,
                    "sma50": sma50,
                    "sma200": sma200,
                    "rsi": rsi,
                    "mo1r": mo1_ret,  # 1mo return %
                    "mo3r": mo3_ret,  # 3mo return %
                    "score": score,
                }
            )
        except Exception as e:
            print(f"[ETF 스코어 오류] {symbol}: {e}")

    return sorted(results, key=lambda x: (x["score"], x["mo1r"]), reverse=True)


def get_market_state() -> dict:
    try:
        vix_info = yf.Ticker("^VIX").info
        spy_info = yf.Ticker("SPY").info
        vix = vix_info.get("regularMarketPrice", 20)
        spy_chg = spy_info.get("regularMarketChangePercent", 0)
        regime = "RISK_OFF" if vix > 25 else "RISK_ON"
        return {
            "vix": round(float(vix), 1),
            "spy_chg": round(float(spy_chg), 2),
            "regime": regime,
        }
    except:
        return {"vix": 20.0, "spy_chg": 0.0, "regime": "RISK_ON"}


def get_holdings() -> list[dict]:
    """현재 보유 포지션 + 수익률 조회"""
    from app.db.database import SessionLocal
    from app.db.models import Portfolio, Account

    db = SessionLocal()
    try:
        items = db.query(Portfolio).all()
        account = db.query(Account).first()
        cash = account.cash if account else 0
        holdings = []
        for item in items:
            try:
                info = yf.Ticker(item.symbol).info
                cur = (
                    info.get("regularMarketPrice")
                    or info.get("preMarketPrice")
                    or item.average_price
                )
                pnl = round(
                    (float(cur) - item.average_price) / item.average_price * 100, 2
                )
                holdings.append(
                    {
                        "etf": item.symbol,
                        "qty": item.quantity,
                        "avg": round(item.average_price, 2),
                        "cur": round(float(cur), 2),
                        "pnl": pnl,
                    }
                )
            except:
                pass
        return holdings, round(cash, 2)
    finally:
        db.close()


# ── 로그 저장 ──────────────────────────────────────────
def save_log(log_data: dict):
    try:
        os.makedirs("logs", exist_ok=True)
        logs = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        logs.insert(0, log_data)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs[:20], f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[로그 오류] {e}")


# ── JSON 파싱 복구 ──────────────────────────────────────
def parse_llm_response(text: str) -> dict:
    text = text.strip()
    if "```" in text:
        for part in text.split("```"):
            if "{" in part:
                text = part.strip()
                break
    if text.lower().startswith("json"):
        text = text[4:].strip()
    try:
        return json.loads(text)
    except:
        pass

    # 정규식 복구
    def rx(pattern):
        m = re.search(pattern, text)
        return m.group(1) if m else None

    buys_raw = rx(r'"buys"\s*:\s*(\[[^\]]*\])')
    sells_raw = rx(r'"sells"\s*:\s*(\[[^\]]*\])')
    try:
        buys = json.loads(buys_raw) if buys_raw else []
    except:
        buys = []
    try:
        sells = json.loads(sells_raw) if sells_raw else []
    except:
        sells = []
    return {
        "buys": buys,
        "sells": sells,
        "note": rx(r'"note"\s*:\s*"([^"]*)"') or "recovered",
    }


# ── 메인 에이전트 ──────────────────────────────────────
def run_industry_bear():
    print("\n=== 인더스트리곰 실행 ===\n")

    # 1. 데이터 수집
    etf_scores = compute_etf_scores()
    market = get_market_state()
    news = get_latest_news()
    holdings, cash = get_holdings()

    print(f"[시장] VIX={market['vix']} regime={market['regime']}")
    print(f"[보유] {len(holdings)}개 포지션, 현금 ${cash:,.0f}")

    # ── 자동 손절/익절 (LLM 없이 즉시 실행) ──────────────
    for h in holdings:
        if h["pnl"] <= STOP_LOSS_PCT:
            r = sell_stock(h["etf"], h["qty"])
            print(f"[손절] {h['etf']} {h['pnl']}% → {r.get('message')}")
        elif h["pnl"] >= TAKE_PROFIT_PCT:
            r = sell_stock(h["etf"], h["qty"])
            print(f"[익절] {h['etf']} {h['pnl']}% → {r.get('message')}")

    # 손절/익절 후 포지션 재조회
    holdings, cash = get_holdings()
    current_symbols = {h["etf"] for h in holdings}
    available_slots = MAX_POSITIONS - len(current_symbols)

    # ── 매수 후보 필터링 ──────────────────────────────────
    # 리스크오프 시 방어 섹터만 허용
    defensive = {"XLP", "XLU", "XLV"}
    candidates = []
    for e in etf_scores:
        if e["score"] < MIN_SCORE:
            continue
        if market["regime"] == "RISK_OFF" and e["etf"] not in defensive:
            continue
        if e["etf"] in current_symbols:
            continue
        candidates.append(e)

    # 상위 8개만 LLM에 전달 (토큰 절약)
    top_candidates = candidates[:8]

    # ── 응답 캐시 확인 ────────────────────────────────────
    cache_input = json.dumps(
        {
            "market": market,
            "top": [(e["etf"], e["score"], e["mo1r"]) for e in top_candidates],
            "holdings": [(h["etf"], h["pnl"]) for h in holdings],
        },
        sort_keys=True,
    )
    cache_key = _cache_key(cache_input)
    cached = get_cached(cache_key)

    if cached:
        print("[캐시 히트] LLM 호출 생략")
        parsed = cached
        result = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "model": "cache",
        }
    else:
        # ── 프롬프트 구성 (토큰 최적화) ─────────────────────
        # ETF 데이터: 핵심 필드만, 소수점 최소화
        etf_rows = "\n".join(
            f"{e['etf']}|{e['score']}/4|RSI:{e['rsi']}|1m:{e['mo1r']}%|3m:{e['mo3r']}%"
            for e in top_candidates
        )
        holding_rows = (
            "\n".join(
                f"{h['etf']}|avg:{h['avg']}|cur:{h['cur']}|pnl:{h['pnl']}%"
                for h in holdings
            )
            or "none"
        )
        news_rows = (
            "\n".join(
                f"{sym}:{title}"
                for sym, title in news.items()
                if sym in {e["etf"] for e in top_candidates}
            )
            or "none"
        )

        # 영어 프롬프트 + 시스템 지시문 캐싱 대상 분리
        system_prompt = (
            "You are a US sector ETF quant. "
            "Analyze data and return ONLY compact JSON. No prose.\n"
            "Rules: max_buys=5, equal_weight, "
            f"stop_loss={STOP_LOSS_PCT}%, take_profit={TAKE_PROFIT_PCT}%, "
            "min_score=2/4, prefer momentum+trend alignment.\n"
            "Output schema (keep it minimal):\n"
            '{"buys":["XLK","XLV"],"sells":[],"note":"<15 words"}'
        )

        user_prompt = (
            f"MARKET: VIX={market['vix']} SPY_chg={market['spy_chg']}% regime={market['regime']}\n"
            f"SLOTS={available_slots} HELD={len(current_symbols)}\n\n"
            f"CANDIDATES(etf|score|RSI|1m|3m):\n{etf_rows}\n\n"
            f"HOLDINGS:\n{holding_rows}\n\n"
            f"NEWS:\n{news_rows}\n\n"
            "Decide: which ETFs to BUY (max fills SLOTS), any to SELL?\n"
            "Reply ONLY JSON."
        )

        result = ask_llm(system_prompt + "\n\n" + user_prompt)
        print(f"[LLM 응답]\n{result['text']}\n")
        parsed = parse_llm_response(result["text"])
        set_cached(cache_key, parsed)

    # ── 매매 실행 ──────────────────────────────────────────
    buys = parsed.get("buys", [])
    sells = parsed.get("sells", [])
    trade_results = []

    # 추가 매도
    for sym in sells:
        h = next((x for x in holdings if x["etf"] == sym), None)
        if h:
            r = sell_stock(sym, h["qty"])
            trade_results.append(f"SELL {sym}: {r.get('message','')}")
            print(f"[매도] {sym}")

    # 보유 수 재계산 후 균등 매수
    holdings_after_sell, cash = get_holdings()
    current_count = len({h["etf"] for h in holdings_after_sell})
    slots = MAX_POSITIONS - current_count

    buy_targets = [b for b in buys if b not in {h["etf"] for h in holdings_after_sell}][
        :slots
    ]

    if buy_targets and cash > 0:
        alloc_per_etf = cash / len(buy_targets)
        for sym in buy_targets:
            try:
                info = yf.Ticker(sym).info
                price = (
                    info.get("preMarketPrice") or info.get("regularMarketPrice") or 1
                )
                qty = int(alloc_per_etf // float(price))
                if qty > 0:
                    r = buy_stock(sym, quantity=qty)
                    trade_results.append(f"BUY {sym} x{qty}: {r.get('message','')}")
                    print(f"[매수] {sym} x{qty}")
            except Exception as e:
                print(f"[매수 오류] {sym}: {e}")

    # ── 로그 저장 ──────────────────────────────────────────
    save_log(
        {
            "agent": "인더스트리곰",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "regime": market["regime"],
            "vix": market["vix"],
            "buys": buys,
            "sells": sells,
            "trade_results": trade_results,
            "note": parsed.get("note", ""),
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
            "total_tokens": result.get("total_tokens", 0),
            "model": result.get("model", ""),
        }
    )
    return parsed
