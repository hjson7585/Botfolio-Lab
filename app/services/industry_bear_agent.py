import json
import os
import re
from datetime import datetime

import yfinance as yf

from app.services.llm_service import ask_llm
from app.services.news_service import get_latest_news
from app.services.trade_service import buy_stock

LOG_FILE = "logs/ai_logs.json"

INDUSTRY_ETFS = {
    "Technology": "XLK",
    "Semiconductors": "SOXX",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Communication Services": "XLC",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
}


def get_market_summary():
    symbols = ["SPY", "QQQ", "^VIX"]
    result = []
    for symbol in symbols:
        try:
            info = yf.Ticker(symbol).info
            price = (
                info.get("preMarketPrice")
                or info.get("postMarketPrice")
                or info.get("regularMarketPrice")
            )
            prev = info.get("regularMarketPreviousClose")
            chg = round(((price - prev) / prev) * 100, 2) if price and prev else 0
            result.append(
                {
                    "symbol": symbol,
                    "price": round(price, 2) if price else None,
                    "change_pct": chg,
                    "market_state": info.get("marketState", ""),
                }
            )
        except Exception as e:
            print(f"[시장 요약 오류] {symbol}: {e}")
    return result


def get_industry_etf_summary():
    result = []
    for sector, symbol in INDUSTRY_ETFS.items():
        try:
            hist = yf.Ticker(symbol).history(period="1mo")
            if hist.empty or len(hist) < 6:
                continue
            latest = round(float(hist.iloc[-1]["Close"]), 2)
            week_ago = round(float(hist.iloc[-6]["Close"]), 2)
            month_ago = round(float(hist.iloc[0]["Close"]), 2)
            week_chg = (
                round(((latest - week_ago) / week_ago) * 100, 2) if week_ago else 0
            )
            month_chg = (
                round(((latest - month_ago) / month_ago) * 100, 2) if month_ago else 0
            )
            vol_avg = int(hist["Volume"].tail(5).mean())
            result.append(
                {
                    "sector": sector,
                    "etf": symbol,
                    "price": latest,
                    "week_change_pct": week_chg,
                    "month_change_pct": month_chg,
                    "avg_volume_5d": vol_avg,
                }
            )
        except Exception as e:
            print(f"[ETF 요약 오류] {symbol}: {e}")
    return result


def save_log(log_data):
    try:
        os.makedirs("logs", exist_ok=True)
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
        logs.insert(0, log_data)
        logs = logs[:20]
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        print("로그 저장 완료")
    except Exception as e:
        print(f"[로그 저장 오류] {e}")


def parse_llm_response(text: str) -> dict:
    """LLM 응답이 잘리거나 깨져도 action/selected_etf를 최대한 복구"""
    text = text.strip()

    # 코드블록 제거
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            if "{" in part:
                text = part.strip()
                break
    if text.lower().startswith("json"):
        text = text[4:].strip()

    # 정상 JSON 파싱 시도
    try:
        return json.loads(text)
    except Exception:
        pass

    # 잘린 JSON 복구: 정규식으로 핵심 필드만 추출
    action_m = re.search(r'"action"\s*:\s*"(\w+)"', text)
    etf_m = re.search(r'"selected_etf"\s*:\s*"(\w+)"', text)
    sector_m = re.search(r'"sector"\s*:\s*"([^"]+)"', text)
    reason_m = re.search(r'"reason"\s*:\s*"([^"]*)', text)

    recovered = {
        "action": action_m.group(1) if action_m else "HOLD",
        "selected_etf": etf_m.group(1) if etf_m else "NONE",
        "sector": sector_m.group(1) if sector_m else "NONE",
        "reason": (reason_m.group(1).rstrip("\\") if reason_m else "이유 없음") + "...",
    }
    print(f"[JSON 복구] action={recovered['action']}, etf={recovered['selected_etf']}")
    return recovered


def run_industry_bear():
    print("\n===================")
    print("인더스트리곰 실행")
    print("===================\n")

    news = get_latest_news()[:5]
    market = get_market_summary()
    etfs = get_industry_etf_summary()

    print(f"[데이터 수집 완료] ETF {len(etfs)}개, 뉴스 {len(news)}개\n")

    prompt = f"""
너는 미국 산업 ETF 전문 퀀트 투자 AI다.
아래 실시간 데이터를 분석해서 지금 당장 매수하기 가장 좋은 산업 ETF 1개를 선택해라.

[미국 시장 현황]
{json.dumps(market, ensure_ascii=False)}

[산업 ETF 데이터]
{json.dumps(etfs, ensure_ascii=False)}

[최신 뉴스]
{json.dumps(news, ensure_ascii=False)}

분석 기준:
1. 월간/주간 수익률 모멘텀이 강한 섹터 우선
2. 거래량이 높아 유동성이 확보된 ETF 우선
3. VIX 높으면 방어 섹터(XLP, XLU, XLV) 선택
4. 매수할 ETF 없으면 HOLD

JSON만 출력. 다른 텍스트 절대 금지. reason은 반드시 50자 이내로 작성.

{{"action":"BUY","selected_etf":"XLV","sector":"Healthcare","reason":"50자 이내 이유"}}
"""

    result = ask_llm(prompt)
    print(f"[LLM 응답]\n{result['text']}\n")

    parsed = parse_llm_response(result["text"])

    action = parsed.get("action", "HOLD")
    selected_etf = parsed.get("selected_etf", "NONE")

    # 실제 가상 매매 실행
    trade_msg = "HOLD — 매매 없음"
    if action == "BUY" and selected_etf and selected_etf != "NONE":
        trade_result = buy_stock(selected_etf, use_all_cash=True)
        trade_msg = trade_result.get("message", str(trade_result))
        print(f"[전액 매수] {selected_etf} → {trade_msg}")
    else:
        print("[HOLD] 매매 없음")

    log_data = {
        "agent": "인더스트리곰",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "selected_etf": selected_etf,
        "sector": parsed.get("sector", "NONE"),
        "reason": parsed.get("reason", "No reason"),
        "trade_result": trade_msg,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "total_tokens": result["total_tokens"],
        "model": result["model"],
    }

    save_log(log_data)
    return log_data
