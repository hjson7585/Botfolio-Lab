# app/services/industry_bear_agent.py
"""
인더스트리곰 — 미국 섹터 ETF 중장기 투자 에이전트
전략: 6개월 ~ 2년 보유 목표
  - 손절: -20% (보유 기간 무관 즉시)
  - 익절: +40% (최소 90일 보유 후)
  - 매일 매매 조건 확인 → 조건 충족 시 즉시 매수/매도
  - 리밸런싱: 별도 함수(run_industry_bear_rebalance)로 분리
  - 매수 기준: 기술 점수(SMA50/200, 3·6개월 모멘텀, RSI) + 뉴스 장기 감성
  - 뉴스 감성: 6개월~2년 구조적 영향만 ±1점 반영 (단기 이벤트 = 0점)
"""

import json
import os
import re
import hashlib
from datetime import datetime, timedelta

import yfinance as yf
import numpy as np

from app.services.llm_service import ask_llm
from app.services.news_service import get_latest_news, analyze_news_sentiment_longterm
from app.services.trade_service import buy_stock, sell_stock

LOG_FILE = "logs/ai_logs.json"
CACHE_FILE = "logs/response_cache.json"

# ── 전략 파라미터 ────────────────────────────────────────
CACHE_TTL_MINUTES = 23 * 60  # 23시간 캐시
MAX_POSITIONS = 5  # 최대 동시 보유 ETF
STOP_LOSS_PCT = -20.0  # 손절: -20%
TAKE_PROFIT_PCT = 40.0  # 익절: +40%
MIN_SCORE = 3  # 매수 최소 점수 3/6
MIN_HOLD_DAYS = 90  # 익절/LLM매도 최소 보유일
MIN_TRADE_CASH = 200.0  # 최소 매수 가능 현금

# ── 리밸런싱 전용 파라미터 ───────────────────────────────
REBALANCE_INTERVAL_DAYS = 25  # 월 1회 리밸런싱 간격 (일)
LAST_RUN_FILE = "logs/bear_last_rebalance.txt"

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


# ── 리밸런싱 주기 체크 ───────────────────────────────────
def _should_rebalance() -> bool:
    if not os.path.exists(LAST_RUN_FILE):
        return True
    try:
        with open(LAST_RUN_FILE, "r") as f:
            last = datetime.fromisoformat(f.read().strip())
        return (datetime.now() - last).days >= REBALANCE_INTERVAL_DAYS
    except Exception:
        return True


def _update_last_rebalance():
    os.makedirs("logs", exist_ok=True)
    with open(LAST_RUN_FILE, "w") as f:
        f.write(datetime.now().isoformat())


# ── 보유 기간 조회 ───────────────────────────────────────
def _get_hold_days(symbol: str) -> int:
    from app.db.database import SessionLocal
    from app.db.models import Trade

    db = SessionLocal()
    try:
        first_buy = (
            db.query(Trade)
            .filter(Trade.symbol == symbol, Trade.action == "BUY")
            .order_by(Trade.id.asc())
            .first()
        )
        if first_buy and hasattr(first_buy, "created_at") and first_buy.created_at:
            return (datetime.now() - first_buy.created_at).days
        return 999
    finally:
        db.close()


# ── 응답 캐시 ────────────────────────────────────────────
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
    now = datetime.now()
    cache = {
        k: v for k, v in cache.items() if datetime.fromisoformat(v["expires"]) > now
    }
    save_cache(cache)


# ── ETF 점수 계산 ────────────────────────────────────────
def compute_etf_scores(sentiment: dict | None = None) -> list[dict]:
    """
    중장기 기준 ETF 점수 (0~6점)
      +1 price > SMA50
      +1 price > SMA200
      +1 3개월 수익률 > 0
      +1 6개월 수익률 > 0
      +1 RSI 40~70
      +1/-1 뉴스 장기 감성
    패널티: price < SMA200 → -1
    """
    results = []
    for symbol in INDUSTRY_ETFS:
        try:
            hist = yf.Ticker(symbol).history(period="2y", interval="1d")
            if len(hist) < 60:
                continue

            closes = hist["Close"].values.astype(float)
            price = round(float(closes[-1]), 2)
            sma50 = round(float(np.mean(closes[-50:])), 2)

            if len(closes) >= 200:
                sma200 = round(float(np.mean(closes[-200:])), 2)
                sma200_real = True
            else:
                sma200 = sma50
                sma200_real = False

            delta = np.diff(closes[-15:])
            gain = np.mean(np.where(delta > 0, delta, 0))
            loss = np.mean(np.where(delta < 0, -delta, 0))
            rsi = round(100 - 100 / (1 + gain / loss) if loss != 0 else 100.0, 1)

            mo1_price = float(closes[-21]) if len(closes) >= 21 else float(closes[0])
            mo3_price = float(closes[-63]) if len(closes) >= 63 else float(closes[0])
            mo6_price = float(closes[-126]) if len(closes) >= 126 else float(closes[0])
            mo12_price = float(closes[-252]) if len(closes) >= 252 else float(closes[0])

            mo1_ret = round((price - mo1_price) / mo1_price * 100, 2)
            mo3_ret = round((price - mo3_price) / mo3_price * 100, 2)
            mo6_ret = round((price - mo6_price) / mo6_price * 100, 2)
            mo12_ret = round((price - mo12_price) / mo12_price * 100, 2)

            score = 0
            if price > sma50:
                score += 1
            if price > sma200:
                score += 1
            if mo3_ret > 0:
                score += 1
            if mo6_ret > 0:
                score += 1
            if 40 <= rsi <= 70:
                score += 1
            if price < sma200:
                score = max(0, score - 1)

            news_score = 0
            news_reason = "no signal"
            if sentiment and symbol in sentiment:
                news_score = sentiment[symbol].get("score", 0)
                news_reason = sentiment[symbol].get("reason", "no signal")
                score = max(0, score + news_score)

            results.append(
                {
                    "etf": symbol,
                    "sector": INDUSTRY_ETFS[symbol],
                    "price": price,
                    "sma50": sma50,
                    "sma200": sma200,
                    "sma200_real": sma200_real,
                    "rsi": rsi,
                    "mo1r": mo1_ret,
                    "mo3r": mo3_ret,
                    "mo6r": mo6_ret,
                    "mo12r": mo12_ret,
                    "score": score,
                    "news_score": news_score,
                    "news_reason": news_reason,
                }
            )
        except Exception as e:
            print(f"[ETF 스코어 오류] {symbol}: {e}")

    return sorted(results, key=lambda x: (x["score"], x["mo6r"]), reverse=True)


def get_market_state() -> dict:
    try:
        vix_info = yf.Ticker("^VIX").info
        spy_info = yf.Ticker("SPY").info
        vix = vix_info.get("regularMarketPrice", 20)
        spy_chg = spy_info.get("regularMarketChangePercent", 0)
        regime = "RISK_OFF" if vix > 30 else "RISK_ON"
        return {
            "vix": round(float(vix), 1),
            "spy_chg": round(float(spy_chg), 2),
            "regime": regime,
        }
    except Exception:
        return {"vix": 20.0, "spy_chg": 0.0, "regime": "RISK_ON"}


def get_holdings() -> tuple[list[dict], float]:
    from app.db.database import SessionLocal
    from app.db.models import Portfolio, Account

    db = SessionLocal()
    try:
        items = (
            db.query(Portfolio).filter(Portfolio.agent == "bear").all()
        )  # ← agent 필터 추가
        account = (
            db.query(Account)
            .filter(Account.agent == "bear")
            .first()  # ← agent 필터 추가
        )
        cash = (
            float(account.cash) if account and account.cash is not None else 0.0
        )  # ← None 방어
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
                hold_days = _get_hold_days(item.symbol)
                holdings.append(
                    {
                        "etf": item.symbol,
                        "qty": item.quantity,
                        "avg": round(item.average_price, 2),
                        "cur": round(float(cur), 2),
                        "pnl": pnl,
                        "hold_days": hold_days,
                    }
                )
            except Exception:
                pass
        return holdings, round(cash, 2)
    finally:
        db.close()


# ── 로그 저장 ────────────────────────────────────────────
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


# ── JSON 파싱 복구 ───────────────────────────────────────
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
    except Exception:
        pass

    def rx(pattern):
        m = re.search(pattern, text)
        return m.group(1) if m else None

    buys_raw = rx(r'"buys"\s*:\s*(\[[^\]]*\])')
    sells_raw = rx(r'"sells"\s*:\s*(\[[^\]]*\])')
    try:
        buys = json.loads(buys_raw) if buys_raw else []
    except Exception:
        buys = []
    try:
        sells = json.loads(sells_raw) if sells_raw else []
    except Exception:
        sells = []
    return {
        "buys": buys,
        "sells": sells,
        "note": rx(r'"note"\s*:\s*"([^"]*)"') or "recovered",
    }


# ── LLM 판단 공통 로직 ───────────────────────────────────
def _run_llm_decision(
    market: dict,
    etf_scores: list[dict],
    holdings: list[dict],
    sentiment: dict,
    cash: float,
) -> tuple[dict, dict, set]:
    """
    매수/매도 LLM 판단을 실행합니다.
    캐시 히트 시 LLM 호출 없이 반환합니다.
    반환값: (parsed, result_meta)
    """
    current_symbols = {h["etf"] for h in holdings}
    available_slots = MAX_POSITIONS - len(current_symbols)
    cash_sufficient = cash >= MIN_TRADE_CASH
    defensive = {"XLP", "XLU", "XLV"}

    # SMA200 약세 체크
    sma200_weak = set()
    score_map = {e["etf"]: e for e in etf_scores}
    for h in holdings:
        info = score_map.get(h["etf"])
        hold_days = h.get("hold_days", 999)
        if info and info["price"] < info["sma200"] and info["mo3r"] < -5.0:
            if hold_days >= MIN_HOLD_DAYS:
                sma200_weak.add(h["etf"])

    # 매수 후보 필터
    candidates = []
    for e in etf_scores:
        if e["score"] < MIN_SCORE:
            continue
        if market["regime"] == "RISK_OFF" and e["etf"] not in defensive:
            continue
        if e["etf"] in current_symbols:
            continue
        candidates.append(e)
    top_candidates = candidates[:6]

    # 캐시 확인
    cache_input = json.dumps(
        {
            "market": market,
            "top": [
                (e["etf"], e["score"], e["mo3r"], e["mo6r"], e["news_score"])
                for e in top_candidates
            ],
            "holdings": [(h["etf"], h["pnl"], h.get("hold_days", 0)) for h in holdings],
            "weak": list(sma200_weak),
        },
        sort_keys=True,
    )
    cache_key = _cache_key(cache_input)
    cached = get_cached(cache_key)

    if cached:
        print("[캐시 히트] LLM 호출 생략")
        return (
            cached,
            {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "model": "cache",
            },
            sma200_weak,
        )

    # LLM 호출
    etf_rows = "\n".join(
        f"{e['etf']}|{e['score']}/6|RSI:{e['rsi']}"
        f"|3m:{e['mo3r']}%|6m:{e['mo6r']}%|12m:{e['mo12r']}%"
        f"|news:{e['news_score']:+d}({e['news_reason']})"
        for e in top_candidates
    )
    holding_rows = (
        "\n".join(
            f"{h['etf']}|avg:{h['avg']}|cur:{h['cur']}"
            f"|pnl:{h['pnl']}%|held:{h.get('hold_days', 0)}d"
            for h in holdings
        )
        or "none"
    )
    sentiment_rows = (
        "\n".join(
            f"{sym}|{s['score']:+d}|{s['reason']}"
            for sym, s in sentiment.items()
            if s["score"] != 0
        )
        or "none"
    )
    weak_rows = ", ".join(sma200_weak) if sma200_weak else "none"
    cash_note = (
        f"CASH=${cash:.0f} (insufficient — do NOT suggest any buys)"
        if not cash_sufficient
        else f"CASH=${cash:.0f}"
    )

    system_prompt = (
        "You are a long-term US sector ETF portfolio manager (6mo~2yr horizon). "
        "You combine technical scores AND long-term news sentiment to make decisions.\n\n"
        "Score breakdown: max 6pts "
        "(SMA50+SMA200+3mo_mom+6mo_mom+RSI + news_longterm_sentiment)\n"
        f"Rules: max_positions={MAX_POSITIONS}, equal_weight, "
        f"stop_loss={STOP_LOSS_PCT}%, take_profit={TAKE_PROFIT_PCT}%, "
        f"min_score={MIN_SCORE}/6, min_hold={MIN_HOLD_DAYS}d.\n\n"
        "News sentiment note: scores are STRUCTURAL LONG-TERM only "
        "(+1=secular tailwind, 0=short-term/neutral, -1=secular headwind). "
        "Weight news_score heavily in your decision.\n\n"
        "Do NOT sell unless: SMA200 breakdown confirmed OR "
        "news_score=-1 with mo6r<0 (structural deterioration).\n\n"
        'Output ONLY compact JSON: {"buys":["XLK"],"sells":[],"note":"<20 words"}'
    )
    user_prompt = (
        f"MARKET: VIX={market['vix']} SPY_chg={market['spy_chg']}% "
        f"regime={market['regime']}\n"
        f"SLOTS={available_slots} HELD={len(current_symbols)} {cash_note}\n\n"
        f"CANDIDATES(etf|score/6|RSI|3m|6m|12m|news_score(reason)):\n"
        f"{etf_rows}\n\n"
        f"HOLDINGS(etf|avg|cur|pnl|held_days):\n{holding_rows}\n\n"
        f"SMA200_WEAK(consider selling): {weak_rows}\n\n"
        f"LONG-TERM SENTIMENT SIGNALS:\n{sentiment_rows}\n\n"
        "Decide: BUY new slots (favor high score + positive news sentiment), "
        "SELL only structurally deteriorating positions.\n"
        "Reply ONLY JSON."
    )

    result = ask_llm(system_prompt + "\n\n" + user_prompt)
    print(f"[LLM 응답]\n{result['text']}\n")
    parsed = parse_llm_response(result["text"])
    set_cached(cache_key, parsed)

    return parsed, result, sma200_weak


# ── 매매 실행 공통 로직 ──────────────────────────────────
def _execute_trades(
    parsed: dict,
    holdings: list[dict],
    cash: float,
) -> list[str]:
    """
    LLM 판단 결과를 바탕으로 매도/매수를 실행합니다.
    반환값: trade_results 리스트
    """
    trade_results = []
    buys = parsed.get("buys", [])
    sells = parsed.get("sells", [])

    # LLM 추천 매도
    for sym in sells:
        h = next((x for x in holdings if x["etf"] == sym), None)
        if h:
            hold_days = h.get("hold_days", 999)
            if hold_days >= MIN_HOLD_DAYS:
                r = sell_stock(sym, h["qty"])
                msg = f"[LLM매도] {sym} pnl={h['pnl']}% (보유 {hold_days}일) → {r.get('message', '')}"
                trade_results.append(msg)
                print(msg)
            else:
                msg = f"[매도 보류] {sym} — 최소 보유 {MIN_HOLD_DAYS}일 미달 ({hold_days}일)"
                trade_results.append(msg)
                print(msg)

    # 매도 후 재조회
    holdings_after, cash_after = get_holdings()
    current_count = len({h["etf"] for h in holdings_after})
    slots = MAX_POSITIONS - current_count
    buy_targets = [b for b in buys if b not in {h["etf"] for h in holdings_after}][
        :slots
    ]

    cash_sufficient = cash_after >= MIN_TRADE_CASH
    if not cash_sufficient:
        print(f"[매수 스킵] 현금 ${cash_after:.0f} < 최소 기준 ${MIN_TRADE_CASH:.0f}")
        trade_results.append(f"BUY SKIPPED: cash=${cash_after:.0f} below minimum")
    elif buy_targets and cash_after > 0:
        alloc_per_etf = cash_after / len(buy_targets)
        for sym in buy_targets:
            try:
                info = yf.Ticker(sym).info
                price = (
                    info.get("preMarketPrice") or info.get("regularMarketPrice") or 1
                )
                qty = int(alloc_per_etf // float(price))
                if qty <= 0:
                    msg = f"BUY SKIPPED {sym}: alloc=${alloc_per_etf:.0f} < price=${price:.0f}"
                    trade_results.append(msg)
                    print(
                        f"[매수 스킵] {sym} — 현금 부족(할당 ${alloc_per_etf:.0f} < 현재가 ${price:.0f})"
                    )
                    continue
                r = buy_stock(sym, quantity=qty)
                msg = f"BUY {sym} x{qty}: {r.get('message', '')}"
                trade_results.append(msg)
                print(f"[매수] {sym} x{qty} — 중장기 편입")
            except Exception as e:
                print(f"[매수 오류] {sym}: {e}")
                trade_results.append(f"BUY ERROR {sym}: {e}")

    return trade_results


# ════════════════════════════════════════════════════════
# ── 메인 실행 함수: 매일 실행 ───────────────────────────
#    손절/익절 + 매일 매매 조건 확인 → 조건 충족 시 즉시 매매
# ════════════════════════════════════════════════════════
def run_industry_bear():
    print("\n=== 인더스트리곰 (매일 실행) ===\n")

    holdings, cash = get_holdings()
    trade_results = []

    # ──────────────────────────────────────────────────
    # STEP 1: 손절 / 익절 체크 (매일, 즉시 실행)
    # ──────────────────────────────────────────────────
    print("[STEP 1] 손절/익절 체크")
    for h in holdings:
        hold_days = h.get("hold_days", 999)

        if h["pnl"] <= STOP_LOSS_PCT:
            r = sell_stock(h["etf"], h["qty"])
            msg = f"[손절] {h['etf']} {h['pnl']}% (보유 {hold_days}일) → {r.get('message')}"
            print(msg)
            trade_results.append(msg)

        elif h["pnl"] >= TAKE_PROFIT_PCT:
            if hold_days >= MIN_HOLD_DAYS:
                r = sell_stock(h["etf"], h["qty"])
                msg = f"[익절] {h['etf']} {h['pnl']}% (보유 {hold_days}일) → {r.get('message')}"
                print(msg)
                trade_results.append(msg)
            else:
                msg = (
                    f"[익절 보류] {h['etf']} {h['pnl']}% — "
                    f"최소 보유 {MIN_HOLD_DAYS}일 미달 ({hold_days}일)"
                )
                print(msg)
                trade_results.append(msg)

    # ──────────────────────────────────────────────────
    # STEP 2: 매일 매매 조건 확인
    #   - 뉴스 감성 분석 + ETF 점수 계산
    #   - 빈 슬롯 있고 조건 충족 ETF → 즉시 매수
    #   - 구조적 하락 포지션 → 즉시 매도
    # ──────────────────────────────────────────────────
    print("[STEP 2] 매일 매매 조건 확인")

    raw_news = get_latest_news(max_per_symbol=3)
    sentiment = analyze_news_sentiment_longterm(
        news=raw_news,
        symbols=list(INDUSTRY_ETFS.keys()),
    )
    for sym, s in sentiment.items():
        if s["score"] != 0:
            label = "📈 장기긍정" if s["score"] > 0 else "📉 장기부정"
            print(f"  {sym} {label}: {s['reason']}")

    etf_scores = compute_etf_scores(sentiment=sentiment)
    market = get_market_state()
    holdings, cash = get_holdings()  # 손절/익절 반영 후 재조회

    print(f"[시장] VIX={market['vix']} regime={market['regime']}")
    print(f"[보유] {len(holdings)}개 포지션, 현금 ${cash:,.0f}")

    # 빈 슬롯 없고 현금 없으면 LLM 호출 스킵
    current_symbols = {h["etf"] for h in holdings}
    available_slots = MAX_POSITIONS - len(current_symbols)
    cash_sufficient = cash >= MIN_TRADE_CASH

    has_trade_opportunity = available_slots > 0 and cash_sufficient

    # SMA200 약세 포지션 확인 (매도 기회 체크)
    score_map = {e["etf"]: e for e in etf_scores}
    sma200_weak = set()
    for h in holdings:
        info = score_map.get(h["etf"])
        hold_days = h.get("hold_days", 999)
        if info and info["price"] < info["sma200"] and info["mo3r"] < -5.0:
            if hold_days >= MIN_HOLD_DAYS:
                sma200_weak.add(h["etf"])

    has_sell_opportunity = len(sma200_weak) > 0

    if not has_trade_opportunity and not has_sell_opportunity:
        print("[매매 스킵] 빈 슬롯 없거나 현금 부족 + 매도 후보 없음 — LLM 호출 생략")
        save_log(
            {
                "agent": "인더스트리곰",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "NO_TRADE",
                "regime": market["regime"],
                "vix": market["vix"],
                "trade_results": trade_results,
                "note": "매매 조건 미충족 — 손절/익절 체크만 완료",
            }
        )
        return {"action": "no_trade", "trade_results": trade_results}

    # LLM 판단 + 매매 실행
    parsed, result, sma200_weak = _run_llm_decision(
        market=market,
        etf_scores=etf_scores,
        holdings=holdings,
        sentiment=sentiment,
        cash=cash,
    )
    llm_trade_results = _execute_trades(parsed, holdings, cash)
    trade_results.extend(llm_trade_results)

    # 로그 저장
    save_log(
        {
            "agent": "인더스트리곰",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "strategy": "중장기 매일 매매",
            "regime": market["regime"],
            "vix": market["vix"],
            "buys": parsed.get("buys", []),
            "sells": parsed.get("sells", []),
            "sma200_weak": list(sma200_weak),
            "trade_results": trade_results,
            "note": parsed.get("note", ""),
            "sentiment_signals": {
                sym: s for sym, s in sentiment.items() if s["score"] != 0
            },
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
            "total_tokens": result.get("total_tokens", 0),
            "model": result.get("model", ""),
            "rebalance": False,
        }
    )

    return parsed


# ════════════════════════════════════════════════════════
# ── 리밸런싱 전용 함수 ───────────────────────────────────
#    섹터 교체 목적. 수동 또는 25일 주기 스케줄로 호출.
# ════════════════════════════════════════════════════════
def run_industry_bear_rebalance(force: bool = False):
    print("\n=== 인더스트리곰 리밸런싱 ===\n")

    if not force and not _should_rebalance():
        print(
            f"[리밸런싱 건너뜀] 마지막 실행으로부터 {REBALANCE_INTERVAL_DAYS}일 미경과"
        )
        return {"skipped": True, "reason": f"{REBALANCE_INTERVAL_DAYS}일 주기 미도달"}

    _update_last_rebalance()

    raw_news = get_latest_news(max_per_symbol=3)
    sentiment = analyze_news_sentiment_longterm(
        news=raw_news,
        symbols=list(INDUSTRY_ETFS.keys()),
    )

    etf_scores = compute_etf_scores(sentiment=sentiment)
    market = get_market_state()
    holdings, cash = get_holdings()

    print(f"[시장] VIX={market['vix']} regime={market['regime']}")
    print(f"[보유] {len(holdings)}개 포지션, 현금 ${cash:,.0f}")

    parsed, result, sma200_weak = _run_llm_decision(
        market=market,
        etf_scores=etf_scores,
        holdings=holdings,
        sentiment=sentiment,
        cash=cash,
    )
    trade_results = _execute_trades(parsed, holdings, cash)

    save_log(
        {
            "agent": "인더스트리곰",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "strategy": f"리밸런싱 {'(강제)' if force else '(정기)'}",
            "regime": market["regime"],
            "vix": market["vix"],
            "buys": parsed.get("buys", []),
            "sells": parsed.get("sells", []),
            "sma200_weak": list(sma200_weak),
            "trade_results": trade_results,
            "note": parsed.get("note", ""),
            "sentiment_signals": {
                sym: s for sym, s in sentiment.items() if s["score"] != 0
            },
            "input_tokens": result.get("input_tokens", 0),
            "output_tokens": result.get("output_tokens", 0),
            "total_tokens": result.get("total_tokens", 0),
            "model": result.get("model", ""),
            "rebalance": True,
            "forced": force,
        }
    )

    return parsed
