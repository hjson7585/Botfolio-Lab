# app/services/industry_bear_agent.py
"""
인더스트리곰 — 미국 섹터 ETF 중장기 투자 에이전트
전략: 6개월 ~ 2년 보유 목표
  - 손절: -20% / 익절: +40% (최소 90일 보유 후)
  - 매일 매매 조건 확인
  - 리밸런싱: run_industry_bear_rebalance()
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

CACHE_FILE = "logs/response_cache.json"
CACHE_TTL_MINUTES = 23 * 60
MAX_POSITIONS = 5
STOP_LOSS_PCT = -20.0
TAKE_PROFIT_PCT = 40.0
MIN_SCORE = 3
MIN_HOLD_DAYS = 90
MIN_TRADE_CASH = 200.0
REBALANCE_INTERVAL_DAYS = 25
LAST_RUN_FILE = "logs/bear_last_rebalance.txt"
AGENT = "bear"

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


# ── 리밸런싱 주기 ────────────────────────────────────────
def _should_rebalance() -> bool:
    try:
        if not os.path.exists(LAST_RUN_FILE):
            return True
        with open(LAST_RUN_FILE, "r") as f:
            last = datetime.fromisoformat(f.read().strip())
        return (datetime.now() - last).days >= REBALANCE_INTERVAL_DAYS
    except Exception:
        return True


def _update_last_rebalance():
    try:
        os.makedirs("logs", exist_ok=True)
        with open(LAST_RUN_FILE, "w") as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        print(f"[_update_last_rebalance 실패 — 무시] {e}")


# ── 보유 기간 ────────────────────────────────────────────
def _get_hold_days(symbol: str) -> int:
    from app.db.database import SessionLocal
    from app.db.models import Trade

    db = SessionLocal()
    try:
        first_buy = (
            db.query(Trade)
            .filter(Trade.agent == AGENT, Trade.symbol == symbol, Trade.action == "BUY")
            .order_by(Trade.id.asc())
            .first()
        )
        if first_buy and hasattr(first_buy, "created_at") and first_buy.created_at:
            return (datetime.now() - first_buy.created_at).days
        return 999
    finally:
        db.close()


# ── 캐시 ─────────────────────────────────────────────────
def _cache_key(data: str) -> str:
    return hashlib.md5(data.encode()).hexdigest()[:12]


def load_cache() -> dict:
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_cache(cache: dict):
    try:
        os.makedirs("logs", exist_ok=True)
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"[캐시 저장 오류 — 무시] {e}")


def get_cached(key: str) -> dict | None:
    try:
        cache = load_cache()
        entry = cache.get(key)
        if not entry:
            return None
        expires = datetime.fromisoformat(entry["expires"])
        if datetime.now() > expires:
            return None
        return entry["parsed"]
    except Exception:
        return None


def set_cached(key: str, parsed: dict):
    try:
        cache = load_cache()
        cache[key] = {
            "parsed": parsed,
            "expires": (
                datetime.now() + timedelta(minutes=CACHE_TTL_MINUTES)
            ).isoformat(),
        }
        now = datetime.now()
        cache = {
            k: v for k, v in cache.items() if datetime.fromisoformat(v["expires"]) > now
        }
        save_cache(cache)
    except Exception as e:
        print(f"[set_cached 오류 — 무시] {e}")


# ── DB 로그 저장 ─────────────────────────────────────────
def save_log(log_data: dict):
    import traceback
    from app.db.database import SessionLocal, engine
    from app.db.models import AgentLog, Base

    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
    except Exception as e:
        print(f"[save_log] 테이블 생성 오류: {e}")

    db = SessionLocal()
    try:
        entry = AgentLog(
            agent=AGENT,
            data=json.dumps(log_data, ensure_ascii=False),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        print(
            f"[로그 저장 완료] id={entry.id} action={log_data.get('action', log_data.get('strategy', ''))}"
        )

        rows = (
            db.query(AgentLog)
            .filter(AgentLog.agent == AGENT)
            .order_by(AgentLog.id.desc())
            .all()
        )
        if len(rows) > 20:
            for old in rows[20:]:
                db.delete(old)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"[로그 DB 저장 오류] {e}")
        print(traceback.format_exc())
    finally:
        db.close()


# ── ETF 기술 점수 계산 ───────────────────────────────────
def compute_etf_scores(sentiment: dict | None = None) -> list[dict]:
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

            def mo_ret(n):
                p = float(closes[-n]) if len(closes) >= n else float(closes[0])
                return round((price - p) / p * 100, 2)

            mo1r = mo_ret(21)
            mo3r = mo_ret(63)
            mo6r = mo_ret(126)
            mo12r = mo_ret(252)

            score = 0
            if price > sma50:
                score += 1
            if price > sma200:
                score += 1
            if mo3r > 0:
                score += 1
            if mo6r > 0:
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
                    "mo1r": mo1r,
                    "mo3r": mo3r,
                    "mo6r": mo6r,
                    "mo12r": mo12r,
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
        vix = yf.Ticker("^VIX").info.get("regularMarketPrice", 20)
        spy_chg = yf.Ticker("SPY").info.get("regularMarketChangePercent", 0)
        return {
            "vix": round(float(vix), 1),
            "spy_chg": round(float(spy_chg), 2),
            "regime": "RISK_OFF" if float(vix) > 30 else "RISK_ON",
        }
    except Exception:
        return {"vix": 20.0, "spy_chg": 0.0, "regime": "RISK_ON"}


def get_holdings() -> tuple[list[dict], float]:
    from app.db.database import SessionLocal
    from app.db.models import Portfolio, Account

    db = SessionLocal()
    try:
        items = db.query(Portfolio).filter(Portfolio.agent == AGENT).all()
        account = db.query(Account).filter(Account.agent == AGENT).first()
        cash = float(account.cash) if account and account.cash is not None else 0.0

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
                        "hold_days": _get_hold_days(item.symbol),
                    }
                )
            except Exception as e:
                print(f"[보유 조회 오류] {item.symbol}: {e}")
        return holdings, round(cash, 2)
    finally:
        db.close()


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

    try:
        buys = json.loads(rx(r'"buys"\s*:\s*(\[[^\]]*\])') or "[]")
    except Exception:
        buys = []
    try:
        sells = json.loads(rx(r'"sells"\s*:\s*(\[[^\]]*\])') or "[]")
    except Exception:
        sells = []
    return {
        "buys": buys,
        "sells": sells,
        "note": rx(r'"note"\s*:\s*"([^"]*)"') or "recovered",
    }


def _run_llm_decision(
    market: dict,
    etf_scores: list[dict],
    holdings: list[dict],
    sentiment: dict,
    cash: float,
) -> tuple[dict, dict, set]:
    current_symbols = {h["etf"] for h in holdings}
    cash_sufficient = cash >= MIN_TRADE_CASH
    defensive = {"XLP", "XLU", "XLV"}

    score_map = {e["etf"]: e for e in etf_scores}
    sma200_weak = set()
    for h in holdings:
        info = score_map.get(h["etf"])
        if info and info["price"] < info["sma200"] and info["mo3r"] < -5.0:
            if h.get("hold_days", 999) >= MIN_HOLD_DAYS:
                sma200_weak.add(h["etf"])

    candidates = [
        e
        for e in etf_scores
        if e["score"] >= MIN_SCORE
        and e["etf"] not in current_symbols
        and (market["regime"] != "RISK_OFF" or e["etf"] in defensive)
    ][:6]

    cache_input = json.dumps(
        {
            "market": market,
            "top": [
                (e["etf"], e["score"], e["mo3r"], e["mo6r"], e["news_score"])
                for e in candidates
            ],
            "holdings": [(h["etf"], h["pnl"], h.get("hold_days", 0)) for h in holdings],
            "weak": sorted(sma200_weak),
        },
        sort_keys=True,
    )
    ck = _cache_key(cache_input)
    cached = get_cached(ck)
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

    etf_rows = "\n".join(
        f"{e['etf']}|{e['score']}/6|RSI:{e['rsi']}"
        f"|3m:{e['mo3r']}%|6m:{e['mo6r']}%|12m:{e['mo12r']}%"
        f"|news:{e['news_score']:+d}({e['news_reason']})"
        for e in candidates
    )
    holding_rows = (
        "\n".join(
            f"{h['etf']}|avg:{h['avg']}|cur:{h['cur']}|pnl:{h['pnl']}%|held:{h.get('hold_days',0)}d"
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

    slots = MAX_POSITIONS - len(current_symbols)
    cash_note = (
        f"CASH=${cash:.0f} (insufficient)"
        if not cash_sufficient
        else f"CASH=${cash:.0f}"
    )

    prompt = (
        "You are a long-term US sector ETF portfolio manager (6mo~2yr horizon).\n"
        f"Rules: max_positions={MAX_POSITIONS}, stop_loss={STOP_LOSS_PCT}%, "
        f"take_profit={TAKE_PROFIT_PCT}%, min_score={MIN_SCORE}/6, min_hold={MIN_HOLD_DAYS}d.\n"
        "Do NOT sell unless SMA200 breakdown OR news_score=-1 with mo6r<0.\n"
        'Output ONLY JSON: {"buys":["XLK"],"sells":[],"note":"<20 words"}\n\n'
        f"MARKET: VIX={market['vix']} SPY={market['spy_chg']}% regime={market['regime']}\n"
        f"SLOTS={slots} {cash_note}\n\n"
        f"CANDIDATES:\n{etf_rows}\n\n"
        f"HOLDINGS:\n{holding_rows}\n\n"
        f"SMA200_WEAK: {', '.join(sma200_weak) or 'none'}\n\n"
        f"SENTIMENT:\n{sentiment_rows}\n\nReply ONLY JSON."
    )

    result = ask_llm(prompt)
    print(f"[LLM 응답]\n{result['text']}\n")
    parsed = parse_llm_response(result["text"])
    set_cached(ck, parsed)
    return parsed, result, sma200_weak


def _execute_trades(parsed: dict, holdings: list[dict], cash: float) -> list[str]:
    trade_results = []

    for sym in parsed.get("sells", []):
        h = next((x for x in holdings if x["etf"] == sym), None)
        if h:
            hold_days = h.get("hold_days", 999)
            if hold_days >= MIN_HOLD_DAYS:
                r = sell_stock(sym, h["qty"], agent=AGENT)
                msg = f"[LLM매도] {sym} pnl={h['pnl']}% ({hold_days}일) → {r.get('message', r.get('error', ''))}"
            else:
                msg = f"[매도 보류] {sym} — {MIN_HOLD_DAYS}일 미달 ({hold_days}일)"
            trade_results.append(msg)
            print(msg)

    holdings_after, cash_after = get_holdings()
    slots = MAX_POSITIONS - len({h["etf"] for h in holdings_after})
    buy_targets = [
        b for b in parsed.get("buys", []) if b not in {h["etf"] for h in holdings_after}
    ][:slots]

    if cash_after < MIN_TRADE_CASH:
        msg = f"BUY SKIPPED: cash=${cash_after:.0f} below minimum"
        trade_results.append(msg)
        print(f"[매수 스킵] {msg}")
    elif buy_targets:
        alloc = cash_after / len(buy_targets)
        for sym in buy_targets:
            try:
                info = yf.Ticker(sym).info
                price = float(
                    info.get("preMarketPrice") or info.get("regularMarketPrice") or 1
                )
                qty = int(alloc // price)
                if qty <= 0:
                    trade_results.append(
                        f"BUY SKIPPED {sym}: alloc=${alloc:.0f} < price=${price:.0f}"
                    )
                    continue
                r = buy_stock(sym, quantity=qty, agent=AGENT)
                msg = f"BUY {sym} x{qty}: {r.get('message', r.get('error', ''))}"
                trade_results.append(msg)
                print(f"[매수] {msg}")
            except Exception as e:
                trade_results.append(f"BUY ERROR {sym}: {e}")
                print(f"[매수 오류] {sym}: {e}")

    return trade_results


# ════════════════════════════════════════════════════════
# 메인 실행
# ════════════════════════════════════════════════════════
def run_industry_bear():
    import traceback

    print("\n=== 인더스트리곰 (매일 실행) ===\n")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    trade_results = []

    # ✅ 최외곽 try/except — 어느 위치에서 예외가 나도 반드시 로그 저장
    try:
        holdings, cash = get_holdings()

        # STEP 1: 손절/익절
        print("[STEP 1] 손절/익절 체크")
        for h in holdings:
            hold_days = h.get("hold_days", 999)
            if h["pnl"] <= STOP_LOSS_PCT:
                r = sell_stock(h["etf"], h["qty"], agent=AGENT)
                msg = f"[손절] {h['etf']} {h['pnl']}% ({hold_days}일) → {r.get('message', r.get('error', ''))}"
                print(msg)
                trade_results.append(msg)
            elif h["pnl"] >= TAKE_PROFIT_PCT:
                if hold_days >= MIN_HOLD_DAYS:
                    r = sell_stock(h["etf"], h["qty"], agent=AGENT)
                    msg = f"[익절] {h['etf']} {h['pnl']}% ({hold_days}일) → {r.get('message', r.get('error', ''))}"
                else:
                    msg = f"[익절 보류] {h['etf']} {h['pnl']}% — {MIN_HOLD_DAYS}일 미달 ({hold_days}일)"
                print(msg)
                trade_results.append(msg)

        # STEP 2: 뉴스 + 기술 분석
        print("[STEP 2] 뉴스/기술 분석")
        raw_news = get_latest_news(max_per_symbol=3)
        sentiment = analyze_news_sentiment_longterm(
            news=raw_news, symbols=list(INDUSTRY_ETFS.keys())
        )
        etf_scores = compute_etf_scores(sentiment=sentiment)
        market = get_market_state()
        holdings, cash = get_holdings()

        print(f"[시장] VIX={market['vix']} regime={market['regime']}")
        print(f"[보유] {len(holdings)}개 포지션, 현금 ${cash:,.0f}")

        current_symbols = {h["etf"] for h in holdings}
        score_map = {e["etf"]: e for e in etf_scores}
        sma200_weak = set()
        for h in holdings:
            info = score_map.get(h["etf"])
            if info and info["price"] < info["sma200"] and info["mo3r"] < -5.0:
                if h.get("hold_days", 999) >= MIN_HOLD_DAYS:
                    sma200_weak.add(h["etf"])

        available_slots = MAX_POSITIONS - len(current_symbols)
        has_opportunity = (available_slots > 0 and cash >= MIN_TRADE_CASH) or len(
            sma200_weak
        ) > 0

        if not has_opportunity:
            print("[매매 스킵] 조건 미충족")
            save_log(
                {
                    "agent": "인더스트리곰",
                    "timestamp": ts,
                    "action": "NO_TRADE",
                    "regime": market["regime"],
                    "vix": market["vix"],
                    "holdings_count": len(holdings),
                    "cash": cash,
                    "available_slots": available_slots,
                    "trade_results": trade_results,
                    "note": "매매 조건 미충족 — 손절/익절 체크만 완료",
                }
            )
            return {"action": "no_trade", "trade_results": trade_results}

        # STEP 3: LLM 판단 + 매매 실행
        parsed, result, sma200_weak = _run_llm_decision(
            market=market,
            etf_scores=etf_scores,
            holdings=holdings,
            sentiment=sentiment,
            cash=cash,
        )
        llm_trades = _execute_trades(parsed, holdings, cash)
        trade_results.extend(llm_trades)

        # STEP 4: 정상 완료 로그 저장
        save_log(
            {
                "agent": "인더스트리곰",
                "timestamp": ts,
                "strategy": "중장기 매일 매매",
                "regime": market["regime"],
                "vix": market["vix"],
                "holdings_count": len(holdings),
                "cash": cash,
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

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[인더스트리곰 최외곽 예외]\n{tb}")
        # ✅ 어떤 예외든 반드시 ERROR 로그 DB 저장
        save_log(
            {
                "agent": "인더스트리곰",
                "timestamp": ts,
                "action": "ERROR",
                "error": str(e),
                "traceback": tb,
                "trade_results": trade_results,
                "note": f"실행 중 예외 발생: {str(e)[:300]}",
            }
        )
        return {"action": "error", "error": str(e), "trade_results": trade_results}


# ════════════════════════════════════════════════════════
# 리밸런싱
# ════════════════════════════════════════════════════════
def run_industry_bear_rebalance(force: bool = False):
    import traceback

    print("\n=== 인더스트리곰 리밸런싱 ===\n")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if not force and not _should_rebalance():
            msg = f"{REBALANCE_INTERVAL_DAYS}일 주기 미도달"
            print(f"[리밸런싱 건너뜀] {msg}")
            save_log(
                {
                    "agent": "인더스트리곰",
                    "timestamp": ts,
                    "action": "REBALANCE_SKIPPED",
                    "note": msg,
                }
            )
            return {"skipped": True, "reason": msg}

        _update_last_rebalance()

        raw_news = get_latest_news(max_per_symbol=3)
        sentiment = analyze_news_sentiment_longterm(
            news=raw_news, symbols=list(INDUSTRY_ETFS.keys())
        )
        etf_scores = compute_etf_scores(sentiment=sentiment)
        market = get_market_state()
        holdings, cash = get_holdings()

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
                "timestamp": ts,
                "strategy": f"리밸런싱 {'(강제)' if force else '(정기)'}",
                "regime": market["regime"],
                "vix": market["vix"],
                "holdings_count": len(holdings),
                "cash": cash,
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

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[리밸런싱 최외곽 예외]\n{tb}")
        save_log(
            {
                "agent": "인더스트리곰",
                "timestamp": ts,
                "action": "ERROR",
                "error": str(e),
                "traceback": tb,
                "note": f"리밸런싱 중 예외 발생: {str(e)[:300]}",
            }
        )
        return {"action": "error", "error": str(e)}
