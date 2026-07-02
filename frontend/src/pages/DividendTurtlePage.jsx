import { useEffect, useMemo, useRef, useState } from "react";
import ProfitChart from "../components/ProfitChart";

const API = "http://localhost:8000";
const REFRESH_MS = 2000;
const DIVIDEND_REFRESH_MS = 60000;

const ETF_NAMES = {
    SCHD: "Schwab U.S. Dividend Equity ETF",
    DGRO: "iShares Core Dividend Growth ETF",
    VYM: "Vanguard High Dividend Yield ETF",
    VIG: "Vanguard Dividend Appreciation ETF",
    HDV: "iShares Core High Dividend ETF",
    SPYD: "SPDR Portfolio S&P 500 High Div ETF",
    JEPI: "JPMorgan Equity Premium Income ETF",
    JEPQ: "JPMorgan Nasdaq Equity Premium ETF",
    DIVO: "Amplify CWP Enhanced Dividend Income",
    VNQ: "Vanguard Real Estate ETF",
    XLU: "Utilities Select Sector SPDR ETF",
    NOBL: "ProShares S&P 500 Dividend Aristocrats",
};

const ETF_TYPE = {
    SCHD: "배당성장", DGRO: "배당성장", VIG: "배당성장", NOBL: "배당성장",
    VYM: "고배당", HDV: "고배당", SPYD: "고배당",
    JEPI: "커버드콜", JEPQ: "커버드콜", DIVO: "커버드콜",
    VNQ: "리츠",
    XLU: "유틸리티",
};

const TYPE_STYLE = {
    배당성장: { bg: "bg-blue-100", text: "text-blue-600" },
    고배당: { bg: "bg-green-100", text: "text-green-600" },
    커버드콜: { bg: "bg-amber-100", text: "text-amber-600" },
    리츠: { bg: "bg-purple-100", text: "text-purple-600" },
    유틸리티: { bg: "bg-teal-100", text: "text-teal-600" },
};

const COLORS = [
    "#10b981", "#3b82f6", "#f59e0b", "#8b5cf6",
    "#06b6d4", "#ef4444", "#84cc16", "#f97316",
    "#ec4899", "#a855f7", "#14b8a6", "#f43f5e",
];

function fmt(v) {
    if (v == null || v === "") return "-";
    return new Intl.NumberFormat("ko-KR").format(Number(v));
}
function fmtPct(v) {
    if (v == null || v === "") return "-";
    const n = Number(v);
    return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}
function fmtUSD(v) {
    if (v == null || v === "") return "-";
    return `$${Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
function profitColor(v) {
    const n = Number(v);
    if (v == null || isNaN(n) || n === 0) return "text-gray-900";
    return n > 0 ? "text-red-500" : "text-blue-500";
}
function profitBadge(v) {
    const n = Number(v);
    if (v == null || isNaN(n) || n === 0) return "bg-gray-100 text-gray-900";
    return n > 0 ? "bg-red-50 text-red-500" : "bg-blue-50 text-blue-500";
}

function polarToCartesian(cx, cy, r, deg) {
    const rad = ((deg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}
function buildArc(cx, cy, outerR, innerR, startDeg, endDeg) {
    if (endDeg - startDeg >= 359.9) endDeg = startDeg + 359.9;
    const large = endDeg - startDeg > 180 ? 1 : 0;
    const o1 = polarToCartesian(cx, cy, outerR, startDeg);
    const o2 = polarToCartesian(cx, cy, outerR, endDeg);
    const i1 = polarToCartesian(cx, cy, innerR, endDeg);
    const i2 = polarToCartesian(cx, cy, innerR, startDeg);
    return [
        `M ${o1.x} ${o1.y}`,
        `A ${outerR} ${outerR} 0 ${large} 1 ${o2.x} ${o2.y}`,
        `L ${i1.x} ${i1.y}`,
        `A ${innerR} ${innerR} 0 ${large} 0 ${i2.x} ${i2.y}`,
        "Z",
    ].join(" ");
}

function DonutChart({ items }) {
    const wrapRef = useRef(null);
    const [hovered, setHovered] = useState(null);

    const slices = useMemo(() => {
        const valid = items.filter((i) => Number(i.weight) > 0);
        const total = valid.reduce((s, i) => s + Number(i.weight), 0) || 100;
        let cum = 0;
        return valid.map((item, idx) => {
            const startDeg = (cum / total) * 360;
            cum += Number(item.weight);
            const endDeg = (cum / total) * 360;
            return { ...item, color: COLORS[idx % COLORS.length], startDeg, endDeg };
        });
    }, [items]);

    if (!slices.length) {
        return (
            <div className="flex items-center justify-center h-40 rounded-2xl bg-gray-50 text-gray-400 text-sm">
                보유 ETF 없음
            </div>
        );
    }

    const CX = 100, CY = 100, OUTER = 90, INNER = 52;

    const handleMove = (e, s) => {
        const rect = wrapRef.current?.getBoundingClientRect() ?? { left: 0, top: 0 };
        setHovered({
            symbol: s.symbol, name: ETF_NAMES[s.symbol] || s.symbol,
            weight: s.weight, color: s.color,
            x: e.clientX - rect.left + 16,
            y: e.clientY - rect.top - 12,
        });
    };

    return (
        <div ref={wrapRef} className="flex flex-col items-center gap-4" style={{ position: "relative" }}>
            <svg width={200} height={200} viewBox="0 0 200 200"
                style={{ display: "block", overflow: "visible" }}
                onMouseLeave={() => setHovered(null)}>
                {slices.map((s) => {
                    const gap = slices.length > 1 ? 1.5 : 0;
                    const isHov = hovered?.symbol === s.symbol;
                    return (
                        <path key={s.symbol}
                            d={buildArc(CX, CY, OUTER, INNER, s.startDeg + gap, s.endDeg - gap)}
                            fill={s.color}
                            opacity={hovered ? (isHov ? 1 : 0.45) : 0.85}
                            style={{
                                cursor: "pointer",
                                transition: "opacity 0.15s, transform 0.15s",
                                transformOrigin: `${CX}px ${CY}px`,
                                transform: isHov ? "scale(1.05)" : "scale(1)",
                            }}
                            onMouseMove={(e) => handleMove(e, s)}
                            onMouseEnter={(e) => handleMove(e, s)}
                            onMouseLeave={() => setHovered(null)}
                        />
                    );
                })}
                <circle cx={CX} cy={CY} r={INNER} fill="white" stroke="#f3f4f6" strokeWidth={1}
                    style={{ pointerEvents: "none" }} />
                {hovered ? (
                    <>
                        <text x={CX} y={CY - 6} textAnchor="middle"
                            fill={hovered.color} fontSize={16} fontWeight={700}
                            style={{ pointerEvents: "none" }}>{hovered.symbol}</text>
                        <text x={CX} y={CY + 14} textAnchor="middle"
                            fill="#6b7280" fontSize={11}
                            style={{ pointerEvents: "none" }}>{fmtPct(hovered.weight)}</text>
                    </>
                ) : (
                    <>
                        <text x={CX} y={CY - 6} textAnchor="middle"
                            fill="#9ca3af" fontSize={12}
                            style={{ pointerEvents: "none" }}>ETF</text>
                        <text x={CX} y={CY + 18} textAnchor="middle"
                            fill="#1f2937" fontSize={26} fontWeight={700}
                            style={{ pointerEvents: "none" }}>{slices.length}</text>
                    </>
                )}
            </svg>

            {hovered && (
                <div style={{
                    position: "absolute", left: hovered.x, top: hovered.y,
                    pointerEvents: "none", zIndex: 999,
                    background: "rgba(17,24,39,0.95)",
                    border: `1px solid ${hovered.color}66`,
                    borderRadius: 12, padding: "10px 14px",
                    boxShadow: `0 8px 24px rgba(0,0,0,0.25), 0 0 0 1px ${hovered.color}22`,
                    minWidth: 200, backdropFilter: "blur(6px)",
                }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                        <span style={{ width: 10, height: 10, borderRadius: "50%", background: hovered.color, display: "inline-block", flexShrink: 0 }} />
                        <span style={{ fontWeight: 700, fontSize: 14, color: "#f9fafb" }}>{hovered.symbol}</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#9ca3af", marginBottom: 5, lineHeight: 1.4 }}>{hovered.name}</div>
                    <div style={{ fontSize: 13, color: hovered.color, fontWeight: 700 }}>비중 {fmtPct(hovered.weight)}</div>
                </div>
            )}

            <div className="w-full flex flex-col gap-2">
                {slices.map((s) => {
                    const type = ETF_TYPE[s.symbol];
                    const ts = type ? TYPE_STYLE[type] : null;
                    return (
                        <div key={s.symbol}
                            className="flex items-center justify-between px-3 py-2 rounded-xl transition-all duration-150"
                            style={{
                                background: hovered?.symbol === s.symbol ? `${s.color}18` : "#f9fafb",
                                border: `1px solid ${hovered?.symbol === s.symbol ? s.color + "44" : "transparent"}`,
                                cursor: "pointer",
                            }}
                            onMouseEnter={() => setHovered({ symbol: s.symbol, name: ETF_NAMES[s.symbol] || s.symbol, weight: s.weight, color: s.color, x: 220, y: 10 })}
                            onMouseLeave={() => setHovered(null)}>
                            <div className="flex items-center gap-2">
                                <span className="inline-block rounded-full" style={{ width: 10, height: 10, background: s.color }} />
                                <span className="text-sm text-gray-700 font-medium">{s.symbol}</span>
                                {ts && (
                                    <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${ts.bg} ${ts.text}`}>{type}</span>
                                )}
                            </div>
                            <span className="text-sm font-bold" style={{ color: s.color }}>{fmtPct(s.weight)}</span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

export default function DividendTurtlePage() {
    const [logs, setLogs] = useState([]);
    const [portfolioData, setPortfolioData] = useState({
        portfolio: [], cash: null, total_asset: null, profit_rate: null,
    });
    const [dividendData, setDividendData] = useState({
        total_dividend: null, dividend_by_symbol: [],
    });
    const [lastUpdated, setLastUpdated] = useState(null);
    const [flash, setFlash] = useState(false);
    const [divFlash, setDivFlash] = useState(false);
    const timerRef = useRef(null);
    const divTimerRef = useRef(null);
    const prevProfitRef = useRef(null);
    const prevDivRef = useRef(null);

    const fetchPortfolio = () => {
        fetch(`${API}/turtle-portfolio`)
            .then((r) => r.json())
            .then((d) => {
                if (prevProfitRef.current !== null && prevProfitRef.current !== d.profit_rate) {
                    setFlash(true);
                    setTimeout(() => setFlash(false), 600);
                }
                prevProfitRef.current = d.profit_rate;
                setPortfolioData(d);
                setLastUpdated(new Date().toLocaleTimeString("ko-KR"));
            })
            .catch(() => { });
    };

    const fetchDividend = () => {
        fetch(`${API}/turtle-dividend`)
            .then((r) => r.json())
            .then((d) => {
                if (prevDivRef.current !== null && prevDivRef.current !== d.total_dividend) {
                    setDivFlash(true);
                    setTimeout(() => setDivFlash(false), 800);
                }
                prevDivRef.current = d.total_dividend;
                setDividendData(d);
            })
            .catch(() => { });
    };

    useEffect(() => {
        fetch(`${API}/turtle-logs`)
            .then((r) => r.json())
            .then((d) => setLogs(Array.isArray(d) ? d : []))
            .catch(() => { });

        fetchPortfolio();
        fetchDividend();
        timerRef.current = setInterval(fetchPortfolio, REFRESH_MS);
        divTimerRef.current = setInterval(fetchDividend, DIVIDEND_REFRESH_MS);
        return () => {
            clearInterval(timerRef.current);
            clearInterval(divTimerRef.current);
        };
    }, []);

    const { portfolio, cash, total_asset, profit_rate } = portfolioData;
    const { total_dividend, dividend_by_symbol } = dividendData;

    const divMap = useMemo(() => {
        const m = {};
        (dividend_by_symbol || []).forEach((d) => { m[d.symbol] = d; });
        return m;
    }, [dividend_by_symbol]);

    return (
        <div className="min-h-screen bg-[#f5f7fb] p-10">

            <div className="flex gap-8 items-start mb-8">

                {/* 왼쪽: 로고 + 자금현황 + 누적배당금 */}
                <div className="w-72 shrink-0 bg-white rounded-3xl p-8 shadow-sm border border-gray-100 flex flex-col gap-6">
                    <div className="flex flex-col items-center gap-3">
                        <div className="rounded-full flex items-center justify-center text-4xl shadow-lg"
                            style={{ width: 88, height: 88, background: "linear-gradient(135deg,#10b981,#059669)" }}>
                            🐢
                        </div>
                        <h1 className="text-2xl font-black text-gray-800">배당거북</h1>
                        <p className="text-sm text-gray-400 text-center leading-relaxed">
                            고배당 ETF AI 자동매매 에이전트
                        </p>
                    </div>

                    <div className="flex flex-col gap-3">
                        <div className={`rounded-2xl px-5 py-4 border transition-all duration-300 ${flash ? "bg-yellow-50 border-yellow-200" : "bg-gray-50 border-gray-100"}`}>
                            <p className="text-xs text-gray-400 mb-1">실시간 수익률</p>
                            <p className={`text-xl font-black transition-all duration-300 ${profitColor(profit_rate)}`}>
                                {profit_rate != null ? fmtPct(profit_rate) : "-"}
                            </p>
                        </div>
                        <div className={`rounded-2xl px-5 py-4 border transition-all duration-300 ${flash ? "bg-yellow-50 border-yellow-200" : "bg-gray-50 border-gray-100"}`}>
                            <p className="text-xs text-gray-400 mb-1">총 자산</p>
                            <p className="text-xl font-black text-gray-800">
                                {total_asset != null ? `$${fmt(total_asset)}` : "-"}
                            </p>
                        </div>
                        <div className="bg-gray-50 rounded-2xl px-5 py-4 border border-gray-100">
                            <p className="text-xs text-gray-400 mb-1">보유 현금</p>
                            <p className="text-xl font-black text-gray-800">
                                {cash != null ? `$${fmt(cash)}` : "-"}
                            </p>
                        </div>
                        <div className={`rounded-2xl px-5 py-4 border transition-all duration-300 ${divFlash ? "bg-emerald-50 border-emerald-300" : "bg-emerald-50 border-emerald-100"}`}>
                            <div className="flex items-center justify-between mb-1">
                                <p className="text-xs text-emerald-600 font-semibold">💰 누적 배당금</p>
                                <span className="text-xs text-emerald-400">보유기간 합산</span>
                            </div>
                            <p className={`text-2xl font-black text-emerald-600 transition-all duration-300 ${divFlash ? "scale-105" : ""}`}>
                                {total_dividend != null ? fmtUSD(total_dividend) : "-"}
                            </p>
                            {dividend_by_symbol && dividend_by_symbol.length > 0 && (
                                <div className="mt-3 flex flex-col gap-1.5">
                                    {dividend_by_symbol
                                        .filter((d) => d.total_dividend > 0)
                                        .sort((a, b) => b.total_dividend - a.total_dividend)
                                        .map((d) => (
                                            <div key={d.symbol} className="flex items-center justify-between text-xs">
                                                <span className="text-emerald-700 font-bold">{d.symbol}</span>
                                                <div className="flex items-center gap-2">
                                                    <span className="text-gray-400">{d.dividend_count}회 지급</span>
                                                    <span className="text-emerald-600 font-semibold">{fmtUSD(d.total_dividend)}</span>
                                                </div>
                                            </div>
                                        ))}
                                </div>
                            )}
                        </div>
                    </div>

                    {lastUpdated && (
                        <div className="flex items-center justify-center gap-2">
                            <span className="inline-block w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                            <p className="text-xs text-gray-300">{lastUpdated} 기준</p>
                        </div>
                    )}
                </div>

                {/* 오른쪽: ETF 목록 */}
                <div className="flex-1 bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-6">
                        <h2 className="text-2xl font-black text-gray-800">보유 ETF 목록</h2>
                        <span className="text-sm text-gray-400">보유 비중 및 실시간 상세 정보</span>
                    </div>
                    <div className="flex gap-8">
                        <div className="w-56 shrink-0">
                            <DonutChart items={portfolio || []} />
                        </div>
                        <div className="flex-1 flex flex-col gap-4">
                            {!portfolio || portfolio.length === 0 ? (
                                <div className="flex items-center justify-center h-40 rounded-2xl bg-gray-50 text-gray-400 text-sm">
                                    보유 중인 ETF 데이터가 없습니다.
                                </div>
                            ) : (
                                portfolio.map((item) => {
                                    const type = ETF_TYPE[item.symbol];
                                    const ts = type ? TYPE_STYLE[type] : null;
                                    const div = divMap[item.symbol];
                                    return (
                                        <div key={item.symbol} className="bg-gray-50 rounded-2xl p-5 border border-gray-100">
                                            <div className="flex items-start justify-between mb-4">
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <h3 className="text-lg font-black text-gray-800">{item.symbol}</h3>
                                                        {ts && (
                                                            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${ts.bg} ${ts.text}`}>{type}</span>
                                                        )}
                                                    </div>
                                                    <p className="text-xs text-gray-400 mt-0.5">{ETF_NAMES[item.symbol] || ""}</p>
                                                </div>
                                                <span className={`text-xs font-bold px-3 py-1.5 rounded-full ${profitBadge(item.profit_rate)}`}>
                                                    {fmtPct(item.profit_rate)}
                                                </span>
                                            </div>
                                            <div className="grid grid-cols-4 gap-3 mb-3">
                                                {[
                                                    { label: "보유 수량", value: `${fmt(item.quantity)}주` },
                                                    { label: "평균 단가", value: `$${fmt(item.avg_price)}` },
                                                    { label: "현재가", value: `$${fmt(item.current_price)}` },
                                                    { label: "수익률", value: fmtPct(item.profit_rate), color: profitColor(item.profit_rate) },
                                                ].map(({ label, value, color }) => (
                                                    <div key={label} className="bg-white rounded-xl p-3 border border-gray-100">
                                                        <p className="text-xs text-gray-400 mb-1">{label}</p>
                                                        <p className={`font-bold text-sm ${color || "text-gray-800"}`}>{value}</p>
                                                    </div>
                                                ))}
                                            </div>
                                            {div && div.total_dividend > 0 && (
                                                <div className="flex items-center justify-between bg-emerald-50 rounded-xl px-4 py-2.5 border border-emerald-100">
                                                    <div className="flex items-center gap-2">
                                                        <span className="text-emerald-500 text-sm">💰</span>
                                                        <span className="text-xs text-emerald-600 font-semibold">누적 배당금</span>
                                                        <span className="text-xs text-gray-400">({div.dividend_count}회 수령)</span>
                                                    </div>
                                                    <span className="text-sm font-black text-emerald-600">{fmtUSD(div.total_dividend)}</span>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {/* ✅ 실시간 총자산·수익률을 ProfitChart에 직접 전달 */}
            <div className="w-full">
                <ProfitChart agent="turtle" liveAsset={total_asset} liveRate={profit_rate} />
            </div>
            {/* AI 판단 로그 */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                <div className="flex items-center justify-between mb-6">
                    <h2 className="text-2xl font-black text-gray-800">AI 판단 로그</h2>
                    <span className="text-sm text-gray-400">최근 20건</span>
                </div>
                {logs.length === 0 ? (
                    <div className="flex items-center justify-center h-32 rounded-2xl bg-gray-50 text-gray-400 text-sm">
                        아직 표시할 판단 로그가 없습니다.
                    </div>
                ) : (
                    <div className="flex flex-col gap-4">
                        {logs.map((log, i) => (
                            <div key={i} className="bg-gray-50 rounded-2xl p-5 border border-gray-100">
                                <div className="flex items-center justify-between mb-2">
                                    <div className="flex items-center gap-3">
                                        <span className={`text-xs font-bold px-3 py-1.5 rounded-full ${log.action === "BUY" ? "bg-green-100 text-green-600" :
                                            log.action === "SELL" ? "bg-red-100 text-red-500" :
                                                log.action === "HOLD" ? "bg-gray-200 text-gray-500" :
                                                    "bg-teal-100 text-teal-600"}`}>
                                            {log.action || "HOLD"}
                                        </span>
                                        <strong className="text-gray-800 font-bold">
                                            {log.selected_etf && log.selected_etf !== "NONE" ? log.selected_etf : "-"}
                                        </strong>
                                        {log.div_yield && (
                                            <span className="text-xs bg-emerald-50 text-emerald-600 font-bold px-2 py-0.5 rounded-full">
                                                배당수익률 {log.div_yield}%
                                            </span>
                                        )}
                                    </div>
                                    <span className="text-xs text-gray-300">{log.timestamp || ""}</span>
                                </div>
                                <p className="text-sm text-gray-600 mb-2">{log.reason || "-"}</p>
                                <div className="flex gap-4 text-xs text-gray-300">
                                    <span>모델: {log.model || "-"}</span>
                                    <span>토큰: {log.total_tokens ?? "-"}</span>
                                    {log.score && <span>점수: {log.score}/10</span>}
                                    {log.trade_result && <span>매매결과: {log.trade_result}</span>}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
