import { useEffect, useMemo, useRef, useState } from "react";

const API = "http://localhost:8000";

const ETF_NAMES = {
    XLK: "Technology Select Sector SPDR",
    SOXX: "iShares Semiconductor ETF",
    XLF: "Financial Select Sector SPDR",
    XLY: "Consumer Discretionary Select Sector SPDR",
    XLC: "Communication Services Select Sector SPDR",
    XLI: "Industrial Select Sector SPDR",
    XLE: "Energy Select Sector SPDR",
    XLB: "Materials Select Sector SPDR",
    XLV: "Health Care Select Sector SPDR",
    XLP: "Consumer Staples Select Sector SPDR",
    XLU: "Utilities Select Sector SPDR",
    XLRE: "Real Estate Select Sector SPDR",
};

const COLORS = [
    "#3b82f6", "#10b981", "#f59e0b", "#ef4444",
    "#8b5cf6", "#06b6d4", "#84cc16", "#f97316",
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

function polarToCartesian(cx, cy, r, angleDeg) {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}
function buildArcPath(cx, cy, outerR, innerR, startDeg, endDeg) {
    // 360도짜리(전체 원) 처리
    if (endDeg - startDeg >= 359.9) {
        endDeg = startDeg + 359.9;
    }
    const largeArc = endDeg - startDeg > 180 ? 1 : 0;
    const o1 = polarToCartesian(cx, cy, outerR, startDeg);
    const o2 = polarToCartesian(cx, cy, outerR, endDeg);
    const i1 = polarToCartesian(cx, cy, innerR, endDeg);
    const i2 = polarToCartesian(cx, cy, innerR, startDeg);
    return [
        `M ${o1.x} ${o1.y}`,
        `A ${outerR} ${outerR} 0 ${largeArc} 1 ${o2.x} ${o2.y}`,
        `L ${i1.x} ${i1.y}`,
        `A ${innerR} ${innerR} 0 ${largeArc} 0 ${i2.x} ${i2.y}`,
        "Z",
    ].join(" ");
}

function DonutChart({ items }) {
    const [tooltip, setTooltip] = useState(null); // { symbol, name, weight, color, x, y }
    const wrapRef = useRef(null);

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

    if (!slices.length)
        return <div style={S.empty}>보유 ETF 없음</div>;

    const CX = 110, CY = 110, OUTER = 100, INNER = 58;

    const handleMouseMove = (e, slice) => {
        const rect = wrapRef.current?.getBoundingClientRect() ?? { left: 0, top: 0 };
        setTooltip({
            symbol: slice.symbol,
            name: ETF_NAMES[slice.symbol] || slice.symbol,
            weight: slice.weight,
            color: slice.color,
            x: e.clientX - rect.left + 14,
            y: e.clientY - rect.top - 10,
        });
    };

    return (
        <div ref={wrapRef} style={{ ...S.donutWrap, position: "relative" }}>
            {/* ── 도넛 SVG ── */}
            <div style={{ display: "flex", justifyContent: "center" }}>
                <svg
                    width={220}
                    height={220}
                    viewBox="0 0 220 220"
                    style={{ display: "block" }}
                    onMouseLeave={() => setTooltip(null)}
                >
                    {slices.map((s) => {
                        const gap = slices.length > 1 ? 1.5 : 0;
                        const path = buildArcPath(CX, CY, OUTER, INNER, s.startDeg + gap, s.endDeg - gap);
                        return (
                            <path
                                key={s.symbol}
                                d={path}
                                fill={s.color}
                                opacity={tooltip?.symbol === s.symbol ? 1 : 0.72}
                                style={{
                                    cursor: "pointer",
                                    transition: "opacity 0.15s, transform 0.15s",
                                    transformOrigin: `${CX}px ${CY}px`,
                                    transform: tooltip?.symbol === s.symbol ? "scale(1.04)" : "scale(1)",
                                }}
                                onMouseMove={(e) => handleMouseMove(e, s)}
                                onMouseEnter={(e) => handleMouseMove(e, s)}
                                onMouseLeave={() => setTooltip(null)}
                            />
                        );
                    })}

                    {/* 가운데 원 */}
                    <circle
                        cx={CX} cy={CY} r={INNER}
                        fill="#0f172a"
                        stroke="rgba(148,163,184,0.15)"
                        strokeWidth={1}
                        style={{ pointerEvents: "none" }}
                    />
                    {/* 가운데 텍스트 — hover 시 symbol 표시, 아니면 개수 */}
                    {tooltip ? (
                        <>
                            <text x={CX} y={CY - 6} textAnchor="middle" fill={tooltip.color} fontSize={18} fontWeight={700} style={{ pointerEvents: "none" }}>
                                {tooltip.symbol}
                            </text>
                            <text x={CX} y={CY + 14} textAnchor="middle" fill="#94a3b8" fontSize={11} style={{ pointerEvents: "none" }}>
                                {fmtPct(tooltip.weight)}
                            </text>
                        </>
                    ) : (
                        <>
                            <text x={CX} y={CY - 8} textAnchor="middle" fill="#94a3b8" fontSize={12} style={{ pointerEvents: "none" }}>ETF</text>
                            <text x={CX} y={CY + 16} textAnchor="middle" fill="#e2e8f0" fontSize={28} fontWeight={700} style={{ pointerEvents: "none" }}>
                                {slices.length}
                            </text>
                        </>
                    )}
                </svg>
            </div>

            {/* ── 커서 따라다니는 Floating Tooltip ── */}
            {tooltip && (
                <div
                    style={{
                        position: "absolute",
                        left: tooltip.x,
                        top: tooltip.y,
                        pointerEvents: "none",
                        zIndex: 999,
                        background: "rgba(10,15,30,0.97)",
                        border: `1px solid ${tooltip.color}55`,
                        borderRadius: 12,
                        padding: "10px 14px",
                        boxShadow: `0 8px 24px rgba(0,0,0,0.55), 0 0 0 1px ${tooltip.color}22`,
                        minWidth: 180,
                        backdropFilter: "blur(8px)",
                    }}
                >
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                        <span style={{
                            width: 10, height: 10, borderRadius: "50%",
                            background: tooltip.color, flexShrink: 0, display: "inline-block",
                        }} />
                        <span style={{ fontWeight: 700, fontSize: 15, color: "#f1f5f9" }}>{tooltip.symbol}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 6, lineHeight: 1.4 }}>
                        {tooltip.name}
                    </div>
                    <div style={{ fontSize: 13, color: tooltip.color, fontWeight: 700 }}>
                        비중 {fmtPct(tooltip.weight)}
                    </div>
                </div>
            )}

            {/* ── 범례 ── */}
            <div style={S.legend}>
                {slices.map((s) => (
                    <div
                        key={s.symbol}
                        style={{
                            ...S.legendRow,
                            background: tooltip?.symbol === s.symbol
                                ? `${s.color}22`
                                : "rgba(30,41,59,0.55)",
                            borderColor: tooltip?.symbol === s.symbol
                                ? `${s.color}66`
                                : "transparent",
                            border: "1px solid",
                            transition: "background 0.15s",
                        }}
                        onMouseEnter={() =>
                            setTooltip({ symbol: s.symbol, name: ETF_NAMES[s.symbol] || s.symbol, weight: s.weight, color: s.color, x: 240, y: 10 })
                        }
                        onMouseLeave={() => setTooltip(null)}
                    >
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ width: 10, height: 10, borderRadius: "50%", background: s.color, display: "inline-block", flexShrink: 0 }} />
                            <span style={{ fontSize: 13, color: "#e2e8f0" }}>{s.symbol}</span>
                        </div>
                        <span style={{ fontSize: 13, fontWeight: 700, color: s.color }}>{fmtPct(s.weight)}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ════════════════════════════════
   메인 페이지
════════════════════════════════ */
export default function IndustryBearPage() {
    const [logs, setLogs] = useState([]);
    const [data, setData] = useState({ portfolio: [], cash: null, total_asset: null, profit_rate: null });

    useEffect(() => {
        fetch(`${API}/ai-logs`).then((r) => r.json()).then((d) => setLogs(Array.isArray(d) ? d : [])).catch(() => { });
        fetch(`${API}/portfolio`).then((r) => r.json()).then((d) => setData(d)).catch(() => { });
    }, []);

    return (
        <div style={S.page}>
            <div style={S.container}>

                <div style={S.topGrid}>
                    {/* 왼쪽 — 요약 패널 */}
                    <section style={{ ...S.panel, ...S.leftPanel }}>
                        <div style={S.logo}>곰</div>
                        <h1 style={{ margin: "16px 0 4px", fontSize: 26 }}>인더스트리곰</h1>
                        <p style={{ margin: 0, color: "#94a3b8", fontSize: 14, lineHeight: 1.6 }}>
                            미국 산업 ETF AI 자동매매 에이전트
                        </p>
                        <div style={S.summaryList}>
                            {[
                                { label: "실시간 수익률", value: data.profit_rate != null ? fmtPct(data.profit_rate) : "-" },
                                { label: "총 자산", value: data.total_asset != null ? `$${fmt(data.total_asset)}` : "-" },
                                { label: "보유 현금", value: data.cash != null ? `$${fmt(data.cash)}` : "-" },
                            ].map(({ label, value }) => (
                                <div key={label} style={S.summaryCard}>
                                    <span style={{ color: "#94a3b8", fontSize: 13, display: "block", marginBottom: 6 }}>{label}</span>
                                    <strong style={{ fontSize: 22 }}>{value}</strong>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* 오른쪽 — ETF 목록 */}
                    <section style={S.panel}>
                        <div style={S.sectionTitle}>
                            <h2 style={{ margin: 0, fontSize: 20 }}>보유 ETF 목록</h2>
                            <span style={{ color: "#94a3b8", fontSize: 13 }}>보유 비중 및 상세 정보</span>
                        </div>
                        <div style={S.etfLayout}>
                            <DonutChart items={data.portfolio} />
                            <div style={{ display: "grid", gap: 12 }}>
                                {data.portfolio.length === 0 ? (
                                    <div style={S.empty}>보유 중인 ETF 데이터가 없습니다.</div>
                                ) : (
                                    data.portfolio.map((item) => (
                                        <div key={item.symbol} style={S.detailCard}>
                                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                                                <div>
                                                    <h3 style={{ margin: 0, fontSize: 18 }}>{item.symbol}</h3>
                                                    <p style={{ margin: "4px 0 0", color: "#94a3b8", fontSize: 13 }}>{item.sector || ""}</p>
                                                </div>
                                                <span style={S.badge}>{fmtPct(item.weight)}</span>
                                            </div>
                                            <div style={S.metricGrid}>
                                                {[
                                                    { label: "보유 수량", value: `${fmt(item.quantity)}주` },
                                                    { label: "평균 단가", value: `$${fmt(item.avg_price)}` },
                                                    { label: "평가금액", value: `$${fmt(item.market_value)}` },
                                                    { label: "수익률", value: fmtPct(item.profit_rate) },
                                                ].map(({ label, value }) => (
                                                    <div key={label} style={S.metric}>
                                                        <span style={{ color: "#94a3b8", fontSize: 12, display: "block", marginBottom: 4 }}>{label}</span>
                                                        <strong style={{ fontSize: 15 }}>{value}</strong>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </section>
                </div>

                {/* AI 로그 */}
                <section style={S.panel}>
                    <div style={S.sectionTitle}>
                        <h2 style={{ margin: 0, fontSize: 20 }}>AI 판단 로그</h2>
                        <span style={{ color: "#94a3b8", fontSize: 13 }}>최근 20건</span>
                    </div>
                    {logs.length === 0 ? (
                        <div style={S.empty}>아직 표시할 판단 로그가 없습니다.</div>
                    ) : (
                        <div style={{ display: "grid", gap: 12 }}>
                            {logs.map((log, i) => (
                                <div key={i} style={S.logCard}>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                                            <span style={{
                                                ...S.actionBadge,
                                                background: log.action === "BUY" ? "rgba(16,185,129,0.2)"
                                                    : log.action === "SELL" ? "rgba(239,68,68,0.2)"
                                                        : "rgba(148,163,184,0.2)",
                                                color: log.action === "BUY" ? "#6ee7b7"
                                                    : log.action === "SELL" ? "#fca5a5"
                                                        : "#94a3b8",
                                            }}>
                                                {log.action || "HOLD"}
                                            </span>
                                            <strong style={{ fontSize: 15 }}>
                                                {log.selected_etf && log.selected_etf !== "NONE" ? log.selected_etf : "-"}
                                            </strong>
                                            {log.sector && log.sector !== "NONE" && (
                                                <span style={{ color: "#94a3b8", fontSize: 13 }}>{log.sector}</span>
                                            )}
                                        </div>
                                        <span style={{ color: "#64748b", fontSize: 12 }}>{log.timestamp || ""}</span>
                                    </div>
                                    <p style={{ margin: "0 0 6px", fontSize: 14, color: "#cbd5e1" }}>{log.reason || "-"}</p>
                                    <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#64748b" }}>
                                        <span>모델: {log.model || "-"}</span>
                                        <span>토큰: {log.total_tokens ?? "-"}</span>
                                        {log.trade_result && <span>매매: {log.trade_result}</span>}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
}

/* ════════════════════════════════
   스타일
════════════════════════════════ */
const S = {
    page: { minHeight: "100vh", padding: 24, background: "linear-gradient(180deg,#0f172a 0%,#111827 100%)", color: "#e5e7eb", fontFamily: "Arial,sans-serif", boxSizing: "border-box" },
    container: { maxWidth: 1440, margin: "0 auto", display: "grid", gap: 24 },
    topGrid: { display: "grid", gridTemplateColumns: "320px 1fr", gap: 24, alignItems: "start" },
    panel: { background: "rgba(15,23,42,0.85)", border: "1px solid rgba(148,163,184,0.18)", borderRadius: 20, padding: 24, boxShadow: "0 10px 30px rgba(0,0,0,0.22)" },
    leftPanel: { display: "flex", flexDirection: "column", gap: 0 },
    logo: { width: 80, height: 80, borderRadius: "50%", background: "linear-gradient(135deg,#2563eb,#06b6d4)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 32, fontWeight: 700, color: "white" },
    summaryList: { display: "grid", gap: 12, marginTop: 20 },
    summaryCard: { background: "rgba(30,41,59,0.7)", borderRadius: 14, padding: 16, border: "1px solid rgba(148,163,184,0.12)" },
    sectionTitle: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
    etfLayout: { display: "grid", gridTemplateColumns: "280px 1fr", gap: 20 },
    donutWrap: { display: "grid", gap: 12 },
    legend: { display: "grid", gap: 8 },
    legendRow: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 10px", borderRadius: 10, cursor: "pointer" },
    detailCard: { background: "rgba(30,41,59,0.6)", border: "1px solid rgba(148,163,184,0.1)", borderRadius: 14, padding: 16 },
    badge: { padding: "6px 12px", borderRadius: 999, background: "rgba(37,99,235,0.18)", color: "#93c5fd", fontSize: 13, fontWeight: 700 },
    metricGrid: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10 },
    metric: { background: "rgba(15,23,42,0.7)", borderRadius: 10, padding: 10 },
    logCard: { background: "rgba(30,41,59,0.58)", border: "1px solid rgba(148,163,184,0.1)", borderRadius: 14, padding: 16 },
    actionBadge: { padding: "4px 10px", borderRadius: 999, fontSize: 13, fontWeight: 700 },
    empty: { minHeight: 140, display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8", borderRadius: 14, background: "rgba(30,41,59,0.45)", textAlign: "center", padding: 20 },
};
