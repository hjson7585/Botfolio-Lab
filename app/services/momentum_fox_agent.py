# app/services/momentum_fox_agent.py
"""
모멘텀여우 에이전트 — 듀얼 모멘텀 단기투자 (1주 ~ 3개월)
ETF 유니버스: QQQ, VGT, SOXX, SMH, SPY, VOO, IWM, MTUM, QUAL, TLT, IEF, GLD

전략 핵심:
  1. 절대 모멘텀 (Absolute Momentum): 12주 수익률이 T-bill 수익률(기준: 0.05%) 초과 여부
  2. 상대 모멘텀 (Relative Momentum): 후보 ETF 중 모멘텀 스코어 상위 순위
  3. VIX 레짐 필터: RISK_ON / RISK_OFF / EXTREME_FEAR 3단계

모멘텀 스코어 (5점 만점):
  - 12주 수익률 상위 33% +1점
  -  4주 수익률 상위 33% +1점
  -  2주 수익률 상위 33% +1점
  - SMA20 위 +1점
  - SMA50 위 +1점

리스크 관리:
  - 손절:    -7.0% (개별 포지션)
  - 익절:   +20.0% (개별 포지션)
  - 최대 보유: 5종목
  - EXTREME_FEAR(VIX>35): 신규 매수 금지 + 기존 포지션 청산 고려
  - RISK_OFF(VIX>25): 방어 ETF(TLT/IEF/GLD) 우선
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yfinance as yf
from openai import OpenAI

# ── 설정 ──────────────────────────────────────────────────────────────────────
UNIVERSE = [
    "QQQ",
    "VGT",
    "SOXX",
    "SMH",
    "SPY",
    "VOO",
    "IWM",
    "MTUM",
    "QUAL",
    "TLT",
    "IEF",
    "GLD",
]
DEFENSIVE = {"TLT", "IEF", "GLD"}
MAX_HOLD = 5
STOP_LOSS = -0.07
TAKE_PROFIT = 0.20
ABS_MOM_THRESHOLD = 0.0005

VIX_RISK_OFF = 25.0
VIX_EXTREME_FEAR = 35.0

NY_TZ = ZoneInfo("America/New_York")

LOG_FILE = Path("logs/fox_logs.json")
PORT_FILE = Path("logs/fox_portfolio.json")
LOG_FILE.parent.mkdir(exist_ok=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o-mini"
MAX_TOKENS = 500


def load_portfolio():
    if PORT_FILE.exists():
        return json.loads(PORT_FILE.read_text(encoding="utf-8"))
    return []


def save_portfolio(portfolio):
    PORT_FILE.write_text(
        json.dumps(portfolio, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_logs():
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text(encoding="utf-8"))
    return []


def save_log(entry):
    logs = load_logs()
    logs.insert(0, entry)
    LOG_FILE.write_text(
        json.dumps(logs[:50], ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fetch_price_data(symbols, period="6mo"):
    raw = yf.download(symbols, period=period, auto_adjust=True, progress=False)
    if len(symbols) == 1:
        close = raw["Close"].to_frame(symbols[0])
    else:
        close = raw["Close"]
    return {sym: close[sym].dropna() for sym in symbols if sym in close.columns}


def get_vix():
    vix = yf.Ticker("^VIX")
    hist = vix.history(period="2d")
    return round(float(hist["Close"].iloc[-1]), 2) if not hist.empty else 20.0


def calc_momentum_scores(prices):
    results, ret_12, ret_4, ret_2 = {}, {}, {}, {}
    for sym, ser in prices.items():
        if len(ser) < 60:
            continue
        r12 = ser.iloc[-1] / ser.iloc[-60] - 1
        r4 = (ser.iloc[-1] / ser.iloc[-20] - 1) if len(ser) >= 20 else None
        r2 = (ser.iloc[-1] / ser.iloc[-10] - 1) if len(ser) >= 10 else None
        sma20 = ser.iloc[-20:].mean()
        sma50 = ser.iloc[-50:].mean() if len(ser) >= 50 else ser.mean()
        cur = ser.iloc[-1]
        results[sym] = {
            "ret_12w": round(r12 * 100, 2),
            "ret_4w": round(r4 * 100, 2) if r4 else None,
            "ret_2w": round(r2 * 100, 2) if r2 else None,
            "above_sma20": cur > sma20,
            "above_sma50": cur > sma50,
            "current_price": round(float(cur), 2),
        }
        ret_12[sym] = r12
        if r4:
            ret_4[sym] = r4
        if r2:
            ret_2[sym] = r2

    def top_third(d):
        if not d:
            return set()
        cutoff = sorted(d.values(), reverse=True)[max(0, len(d) // 3 - 1)]
        return {s for s, v in d.items() if v >= cutoff}

    top12 = top_third(ret_12)
    top4 = top_third(ret_4)
    top2 = top_third(ret_2)

    for sym in results:
        score = sum(
            [
                sym in top12,
                sym in top4,
                sym in top2,
                results[sym]["above_sma20"],
                results[sym]["above_sma50"],
            ]
        )
        results[sym]["score"] = score
        r12_val = (results[sym]["ret_12w"] or 0) / 100
        results[sym]["abs_momentum_pass"] = r12_val > ABS_MOM_THRESHOLD

    return results


def check_stop_take(portfolio, prices):
    stops, takes = [], []
    for pos in portfolio:
        sym = pos["symbol"]
        cur_ser = prices.get(sym)
        if cur_ser is None or cur_ser.empty:
            continue
        cur = float(cur_ser.iloc[-1])
        avg = float(pos.get("avg_price", cur))
        pct = (cur - avg) / avg
        if pct <= STOP_LOSS:
            stops.append(sym)
        elif pct >= TAKE_PROFIT:
            takes.append(sym)
    return stops, takes


def llm_decide(regime, vix, scores, portfolio, stop_list, take_list):
    if regime == "RISK_OFF":
        candidates = [
            (s, d)
            for s, d in scores.items()
            if s in DEFENSIVE and d.get("abs_momentum_pass")
        ]
    else:
        candidates = [(s, d) for s, d in scores.items() if d.get("abs_momentum_pass")]

    sorted_etfs = sorted(candidates, key=lambda x: x[1]["score"], reverse=True)[:8]
    held_symbols = [p["symbol"] for p in portfolio]

    system_prompt = (
        "You are MomentumFox, a short-term ETF momentum trading AI (hold 1w-3m). "
        "Dual Momentum: absolute + relative. Max 5 positions. "
        "EXTREME_FEAR→no new buys, liquidate. RISK_OFF→prefer defensive(TLT,IEF,GLD). "
        "Min score for new buy: 3/5. "
        'Respond ONLY JSON: {"action":"BUY|SELL|HOLD|REBAL","buys":[],"sells":[],"note":"..."}'
    )
    user_msg = (
        f"Regime:{regime}|VIX:{vix}\nPortfolio:{held_symbols}\n"
        f"StopLoss:{stop_list}|TakeProfit:{take_list}\nCandidates:\n"
    )
    for sym, d in sorted_etfs:
        user_msg += f"  {sym}:score={d['score']}/5 ret12w={d['ret_12w']}% ret4w={d['ret_4w']}% SMA20={'Y' if d['above_sma20'] else 'N'} SMA50={'Y' if d['above_sma50'] else 'N'}\n"
    user_msg += f"MaxPos:{MAX_HOLD} Holding:{len(held_symbols)}"

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.2,
    )
    raw = resp.choices[0].message.content.strip()
    tokens = resp.usage.total_tokens
    try:
        result = json.loads(raw[raw.find("{") : raw.rfind("}") + 1])
    except Exception:
        result = {"action": "HOLD", "buys": [], "sells": [], "note": raw[:200]}
    result["total_tokens"] = tokens
    result["model"] = MODEL
    return result


def update_portfolio(portfolio, buys, sells, prices, stop_list, take_list):
    trade_results = []
    held = {p["symbol"]: p for p in portfolio}

    for sym in set(stop_list + take_list):
        if sym in held:
            cur = (
                float(prices[sym].iloc[-1]) if sym in prices else held[sym]["avg_price"]
            )
            pct = (cur - held[sym]["avg_price"]) / held[sym]["avg_price"] * 100
            reason = "STOP_LOSS" if sym in stop_list else "TAKE_PROFIT"
            trade_results.append(f"{sym} {reason} @${cur:.2f} ({pct:+.1f}%)")
            del held[sym]

    for sym in sells:
        if sym in held:
            cur = (
                float(prices[sym].iloc[-1]) if sym in prices else held[sym]["avg_price"]
            )
            pct = (cur - held[sym]["avg_price"]) / held[sym]["avg_price"] * 100
            trade_results.append(f"{sym} SELL @${cur:.2f} ({pct:+.1f}%)")
            del held[sym]

    for sym, pos in held.items():
        if sym in prices:
            cur = float(prices[sym].iloc[-1])
            pos["current_price"] = round(cur, 2)
            pos["profit_rate"] = round(
                (cur - pos["avg_price"]) / pos["avg_price"] * 100, 2
            )

    slots = MAX_HOLD - len(held)
    for sym in buys:
        if slots <= 0:
            break
        if sym in held or sym not in prices:
            continue
        cur = float(prices[sym].iloc[-1])
        held[sym] = {
            "symbol": sym,
            "avg_price": round(cur, 2),
            "current_price": round(cur, 2),
            "quantity": 1,
            "profit_rate": 0.0,
            "weight": 0.0,
            "bought_at": datetime.now(NY_TZ).isoformat(),
        }
        trade_results.append(f"{sym} BUY @${cur:.2f}")
        slots -= 1

    total_val = sum(p["current_price"] * p.get("quantity", 1) for p in held.values())
    for pos in held.values():
        pos["weight"] = (
            round(pos["current_price"] * pos.get("quantity", 1) / total_val * 100, 2)
            if total_val
            else 0.0
        )

    return list(held.values()), trade_results


def run_momentum_fox():
    print("[MomentumFox] ▶ 실행 시작")
    now = datetime.now(NY_TZ)
    prices = fetch_price_data(UNIVERSE, period="6mo")
    vix = get_vix()

    if vix >= VIX_EXTREME_FEAR:
        regime = "EXTREME_FEAR"
    elif vix >= VIX_RISK_OFF:
        regime = "RISK_OFF"
    else:
        regime = "RISK_ON"

    print(f"[MomentumFox] VIX={vix} | 레짐={regime}")

    scores = calc_momentum_scores(prices)
    portfolio = load_portfolio()
    stop_list, take_list = check_stop_take(portfolio, prices)
    decision = llm_decide(regime, vix, scores, portfolio, stop_list, take_list)

    new_portfolio, trade_results = update_portfolio(
        portfolio,
        buys=decision.get("buys", []),
        sells=decision.get("sells", []),
        prices=prices,
        stop_list=stop_list,
        take_list=take_list,
    )
    save_portfolio(new_portfolio)

    save_log(
        {
            "timestamp": now.strftime("%Y-%m-%d %H:%M %Z"),
            "regime": regime,
            "vix": vix,
            "action": decision.get("action", "HOLD"),
            "buys": decision.get("buys", []),
            "sells": decision.get("sells", []),
            "note": decision.get("note", ""),
            "trade_results": trade_results,
            "model": decision.get("model", MODEL),
            "total_tokens": decision.get("total_tokens", 0),
            "portfolio": [p["symbol"] for p in new_portfolio],
        }
    )
    print("[MomentumFox] ✅ 완료")


if __name__ == "__main__":
    run_momentum_fox()
