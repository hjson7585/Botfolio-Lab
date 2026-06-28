import json
import os
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
            hist = yf.Ticker(symbol).history(period="5d")
            if hist.empty or len(hist) < 2:
                continue
            latest = round(hist.iloc[-1]["Close"], 2)
            prev = round(hist.iloc[-2]["Close"], 2)
            chg = round(((latest - prev) / prev) * 100, 2) if prev else 0
            result.append({"symbol": symbol, "price": latest, "change_pct": chg})
        except Exception as e:
            print(e)
    return result


def get_industry_etf_summary():
    result = []
    for sector, symbol in INDUSTRY_ETFS.items():
        try:
            hist = yf.Ticker(symbol).history(period="1mo")
            if hist.empty or len(hist) < 6:
                continue
            latest = round(hist.iloc[-1]["Close"], 2)
            week_ago = round(hist.iloc[-6]["Close"], 2)
            month_ago = round(hist.iloc[0]["Close"], 2)
            week_chg = (
                round(((latest - week_ago) / week_ago) * 100, 2) if week_ago else 0
            )
            month_chg = (
                round(((latest - month_ago) / month_ago) * 100, 2) if month_ago else 0
            )
            result.append(
                {
                    "sector": sector,
                    "etf": symbol,
                    "price": latest,
                    "week_change_pct": week_chg,
                    "month_change_pct": month_chg,
                }
            )
        except Exception as e:
            print(e)
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
        print("\n로그 저장 완료")
    except Exception as e:
        print(e)


def run_industry_bear():
    print("\n===================")
    print("인더스트리곰 실행")
    print("===================\n")

    news = get_latest_news()[:5]
    market = get_market_summary()
    etfs = get_industry_etf_summary()

    prompt = f"""
너는 미국 산업 ETF 전문 투자 AI다.
아래 정보를 보고 지금 가장 유망한 미국 산업 ETF 1개를 선택해서 매수(BUY)하거나, 없으면 HOLD해라.

[시장 요약]
{market}

[산업 ETF 후보 - 최근 수익률 포함]
{etfs}

[최신 뉴스]
{news}

규칙:
1. 반드시 산업 ETF 후보 목록 안에서만 1개 선택
2. 지금 매수할 만한 ETF가 없으면 action은 HOLD
3. BUY이면 selected_etf에 티커, HOLD이면 selected_etf는 NONE
4. reason은 한국어로 두 문장 이내
5. JSON만 출력

JSON only:
{{
  "action": "BUY",
  "selected_etf": "SOXX",
  "sector": "Semiconductors",
  "reason": "반도체 ETF 월간 수익률이 가장 높고 관련 뉴스 모멘텀이 강합니다."
}}
"""

    result = ask_llm(prompt)
    print("\nLLM 응답\n", result["text"])

    try:
        text = result["text"].strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text.strip())
    except Exception:
        parsed = {
            "action": "HOLD",
            "selected_etf": "NONE",
            "sector": "NONE",
            "reason": "JSON parse fail",
        }

    action = parsed.get("action", "HOLD")
    selected_etf = parsed.get("selected_etf", "NONE")

    # 실제 가상 매매 실행 (BUY일 때만, 현재 잔액으로 최대 구매)
    trade_msg = "HOLD — 매매 없음"
    if action == "BUY" and selected_etf != "NONE":
        trade_result = buy_stock(selected_etf, 1)
        trade_msg = trade_result.get("message", str(trade_result))
        print(f"\n[매수 실행] {selected_etf} → {trade_msg}")

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
