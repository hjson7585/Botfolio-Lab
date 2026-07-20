# ════════════════════════════════════════════════════════
# 메인 실행
# ════════════════════════════════════════════════════════
def run_industry_bear():
    print("\n=== 인더스트리곰 (매일 실행) ===\n")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    holdings, cash = get_holdings()
    trade_results = []

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
    try:
        raw_news = get_latest_news(max_per_symbol=3)
        sentiment = analyze_news_sentiment_longterm(
            news=raw_news, symbols=list(INDUSTRY_ETFS.keys())
        )
        etf_scores = compute_etf_scores(sentiment=sentiment)
        market = get_market_state()
        holdings, cash = get_holdings()
    except Exception as e:
        print(f"[STEP 2 오류] {e}")
        save_log(
            {
                "agent": "인더스트리곰",
                "timestamp": ts,
                "action": "ERROR",
                "error": str(e),
                "trade_results": trade_results,
                "note": f"뉴스/기술 분석 중 오류: {str(e)[:200]}",
            }
        )
        return {"action": "error", "error": str(e), "trade_results": trade_results}

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
    try:
        parsed, result, sma200_weak = _run_llm_decision(
            market=market,
            etf_scores=etf_scores,
            holdings=holdings,
            sentiment=sentiment,
            cash=cash,
        )
        llm_trades = _execute_trades(parsed, holdings, cash)
        trade_results.extend(llm_trades)
    except Exception as e:
        print(f"[STEP 3 오류] {e}")
        save_log(
            {
                "agent": "인더스트리곰",
                "timestamp": ts,
                "action": "ERROR",
                "error": str(e),
                "trade_results": trade_results,
                "note": f"LLM 판단/매매 실행 중 오류: {str(e)[:200]}",
            }
        )
        return {"action": "error", "error": str(e), "trade_results": trade_results}

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
