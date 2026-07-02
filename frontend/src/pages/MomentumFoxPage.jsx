import { useEffect, useMemo, useRef, useState } from "react";

const API = "http://localhost:8000";

const ETF_NAMES = {
    QQQ: "Invesco QQQ Trust (Nasdaq-100)",
    VGT: "Vanguard Information Technology ETF",
    SOXX: "iShares Semiconductor ETF",
    SMH: "VanEck Semiconductor ETF",
    SPY: "SPDR S&P 500 ETF",
    VOO: "Vanguard S&P 500 ETF",
    IWM: "iShares Russell 2000 ETF",
    MTUM: "iShares MSCI USA Momentum Factor ETF",
    QUAL: "iShares MSCI USA Quality Factor ETF",
    TLT: "iShares 20+ Year Treasury Bond ETF",
    IEF: "iShares 7-10 Year Treasury Bond ETF",
    GLD: "SPDR Gold Shares",
};

const ETF_TYPE = {
    QQQ: "공격", VGT: "공격", SOXX: "공격", SMH: "공격",
    SPY: "코어", VOO: "코어", IWM: "코어",
    MTUM: "팩터", QUAL: "팩터",
    TLT: "방어", IEF: "방어", GLD: "방어",
};
const TYPE_COLOR = {
    공격: "#f59e0b", 코어: "#3b82f6", 팩터: "#8b5cf6", 방어: "#10b981",
};

const COLORS = [
    "#f59e0b", "#3b82f6", "#10b981", "#8b5cf6",
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

/* ── 도넛 차트 ── */
function polarToCartesian(cx, cy, r, angleDeg) {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}
function buildArcPath(cx, cy, outerR, innerR, startDeg, endDeg) {
    if (endDeg - startDeg >= 359.9) endDeg = startDeg + 359.9;
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
    const [tooltip, setTooltip] = useState(null);
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

    if (!slices.length) return <div style={S.empty}>보유 ETF 없음</div>;

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
            <div style={{ display: "flex", justifyContent: "center" }}>
                <svg width={220} height={220} viewBox="0 0 220 220"
                    onMouseLeave={() => setTooltip(null)}>
                    {slices.map((s) => {
                        const gap = slices.length > 1 ? 1.5 : 0;
                        const path = buildArcPath(CX, CY, OUTER, INNER, s.startDeg + gap, s.endDeg - gap);
                        return (
                            <path key={s.symbol} d={path} fill={s.color}
                                opacity={tooltip?.symbol === s.symbol ? 1 : 0.72}
                                style={{
                                    cursor: "pointer", transition: "opacity 0.15s,transform 0.15s",
                                    transformOrigin: `${CX}px ${CY}px`,
                                    transform: tooltip?.symbol === s.symbol ? "scale(1.04)" : "scale(1)",
                                }}
                                onMouseMove={(e) => handleMouseMove(e, s)}
                                onMouseEnter={(e) => handleMouseMove(e, s)}
                                onMouseLeave={() => setTooltip(null)}
                            />
                        );
                    })}
                    <circle cx={CX} cy={CY} r={INNER} fill="#0f172a"
                        stroke="rgba(148,163,184,0.15)" strokeWidth={1}
                        style={{ pointerEvents: "none" }} />
                    {tooltip ? (
                        <>
                            <text x={CX} y={CY - 6} textAnchor="middle" fill={tooltip.color}
                                fontSize={18} fontWeight={700} style={{ pointerEvents: "none" }}>
                                {tooltip.symbol}
                            </text>
                            <text x={CX} y={CY + 14} textAnchor="middle" fill="#94a3b8"
                                fontSize={11} style={{ pointerEvents: "none" }}>
                                {fmtPct(tooltip.weight)}
                            </text>
                        </>
                    ) : (
                        <>
                            <text x={CX} y={CY - 8} textAnchor="middle" fill="#94a3b8"
                                fontSize={12} style={{ pointerEvents: "none" }}>ETF</text>
                            <text x={CX} y={CY + 16} textAnchor="middle" fill="#e2e8f0"
                                fontSize={28} fontWeight={700} style={{ pointerEvents: "none" }}>
                                {slices.length}
                            </text>
                        </>
                    )}
                </svg>
            </div>

            {tooltip && (
                <div style={{
                    position: "absolute", left: tooltip.x, top: tooltip.y,
                    pointerEvents: "none", zIndex: 999,
                    background: "rgba(10,15,30,0.97)",
                    border: `1px solid ${tooltip.color}55`,
                    borderRadius: 12, padding: "10px 14px",
                    boxShadow: `0 8px 24px rgba(0,0,0,0.55),0 0 0 1px ${tooltip.color}22`,
                    minWidth: 180, backdropFilter: "blur(8px)",
                }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
                        <span style={{
                            width: 10, height: 10, borderRadius: "50%",
                            background: tooltip.color, flexShrink: 0, display: "inline-block"
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

            <div style={S.legend}>
                {slices.map((s) => (
                    <div key={s.symbol}
                        style={{
                            ...S.legendRow,
                            background: tooltip?.symbol === s.symbol ? `${s.color}22` : "rgba(30,41,59,0.55)",
                            borderColor: tooltip?.symbol === s.symbol ? `${s.color}66` : "transparent",
                            border: "1px solid", transition: "background 0.15s",
                        }}
                        onMouseEnter={() =>
                            setTooltip({
                                symbol: s.symbol, name: ETF_NAMES[s.symbol] || s.symbol,
                                weight: s.weight, color: s.color, x: 240, y: 10
                            })}
                        onMouseLeave={() => setTooltip(null)}
                    >
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{
                                width: 10, height: 10, borderRadius: "50%",
                                background: s.color, display: "inline-block", flexShrink: 0
                            }} />
                            <span style={{ fontSize: 13, color: "#e2e8f0" }}>{s.symbol}</span>
                            {ETF_TYPE[s.symbol] && (
                                <span style={{
                                    fontSize: 11, padding: "2px 6px", borderRadius: 999,
                                    background: `${TYPE_COLOR[ETF_TYPE[s.symbol]]}22`,
                                    color: TYPE_COLOR[ETF_TYPE[s.symbol]], fontWeight: 600,
                                }}>{ETF_TYPE[s.symbol]}</span>
                            )}
                        </div>
                        <span style={{ fontSize: 13, fontWeight: 700, color: s.color }}>{fmtPct(s.weight)}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

/* ── 레짐 뱃지 ── */
function RegimeBadge({ regime }) {
    const MAP = {
        RISK_ON: { label: "RISK ON", bg: "rgba(16,185,129,0.18)", color: "#6ee7b7" },
        RISK_OFF: { label: "RISK OFF", bg: "rgba(239,68,68,0.18)", color: "#fca5a5" },
        EXTREME_FEAR: { label: "EXTREME FEAR", bg: "rgba(239,68,68,0.35)", color: "#ff6060" },
    };
    const style = MAP[regime] || { label: regime || "-", bg: "rgba(148,163,184,0.2)", color: "#94a3b8" };
    return (
        <span style={{
            padding: "5px 12px", borderRadius: 999, fontSize: 13, fontWeight: 700,
            background: style.bg, color: style.color,
        }}>{style.label}</span>
    );
}

/* ════════════════════════════════
   메인 페이지
════════════════════════════════ */
export default function MomentumFoxPage() {
    const [logs, setLogs] = useState([]);
    const [data, setData] = useState({ portfolio: [], cash: null, total_asset: null, profit_rate: null });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        Promise.all([
            fetch(`${API}/fox-logs`).then((r) => r.json()).catch(() => []),
            fetch(`${API}/portfolio`).then((r) => r.json()).catch(() => ({})),
        ]).then(([logsData, portData]) => {
            setLogs(Array.isArray(logsData) ? logsData : []);
            setData(portData);
            setLoading(false);
        });
    }, []);

    const latestRegime = logs[0]?.regime || null;
    const latestVix = logs[0]?.vix || null;

    return (
        <div style={S.page}>
            <div style={S.container}>

                {/* ── 상단 그리드 ── */}
                <div style={S.topGrid}>

                    {/* 왼쪽 — 요약 패널 */}
                    <section style={{ ...S.panel, ...S.leftPanel }}>
                        <div style={S.logo}>🦊</div>
                        <h1 style={{ margin: "16px 0 4px", fontSize: 26 }}>모멘텀여우</h1>
                        <p style={{ margin: 0, color: "#94a3b8", fontSize: 14, lineHeight: 1.6 }}>
                            미국 ETF 단기 모멘텀 AI 자동매매 에이전트
                        </p>
                        <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: 12 }}>
                            듀얼 모멘텀 · 보유기간 1주~3개월
                        </p>

                        {(latestRegime || latestVix) && (
                            <div style={{ marginTop: 16, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                                {latestRegime && <RegimeBadge regime={latestRegime} />}
                                {latestVix && (
                                    <span style={{ fontSize: 13, color: "#94a3b8" }}>VIX {latestVix}</span>
                                )}
                            </div>
                        )}

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

                        <div style={{ ...S.strategyBox, marginTop: 16 }}>
                            <div style={{ fontSize: 12, color: "#f59e0b", fontWeight: 700, marginBottom: 8 }}>⚡ 전략 파라미터</div>
                            {[
                                ["보유기간", "1주 ~ 3개월"],
                                ["손절", "-7.0%"],
                                ["익절", "+20.0%"],
                                ["최대보유", "5종목"],
                                ["스코어", "5점 만점 / 최소 3점"],
                                ["레짐", "VIX 25/35 기준"],
                            ].map(([k, v]) => (
                                <div key={k} style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                                    <span style={{ color: "#64748b" }}>{k}</span>
                                    <span style={{ color: "#e2e8f0", fontWeight: 600 }}>{v}</span>
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
                            <DonutChart items={data.portfolio || []} />
                            <div style={{ display: "grid", gap: 12 }}>
                                {(!data.portfolio || data.portfolio.length === 0) ? (
                                    <div style={S.empty}>보유 중인 ETF 데이터가 없습니다.</div>
                                ) : (
                                    data.portfolio.map((item) => (
                                        <div key={item.symbol} style={S.detailCard}>
                                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                                                <div>
                                                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                                        <h3 style={{ margin: 0, fontSize: 18 }}>{item.symbol}</h3>
                                                        {ETF_TYPE[item.symbol] && (
                                                            <span style={{
                                                                fontSize: 11, padding: "2px 8px", borderRadius: 999,
                                                                background: `${TYPE_COLOR[ETF_TYPE[item.symbol]]}22`,
                                                                color: TYPE_COLOR[ETF_TYPE[item.symbol]], fontWeight: 700,
                                                            }}>{ETF_TYPE[item.symbol]}</span>
                                                        )}
                                                    </div>
                                                    <p style={{ margin: "4px 0 0", color: "#94a3b8", fontSize: 12 }}>
                                                        {ETF_NAMES[item.symbol] || ""}
                                                    </p>
                                                </div>
                                                <span style={{
                                                    ...S.badge,
                                                    color: Number(item.profit_rate) >= 0 ? "#6ee7b7" : "#fca5a5",
                                                    background: Number(item.profit_rate) >= 0 ? "rgba(16,185,129,0.18)" : "rgba(239,68,68,0.18)",
                                                }}>
                                                    {fmtPct(item.profit_rate)}
                                                </span>
                                            </div>
                                            <div style={S.metricGrid}>
                                                {[
                                                    { label: "보유 수량", value: `${fmt(item.quantity)}주` },
                                                    { label: "평균 단가", value: `$${fmt(item.avg_price)}` },
                                                    { label: "현재가", value: `$${fmt(item.current_price)}` },
                                                    { label: "평가금액", value: `$${fmt(item.market_value)}` },
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

                {/* ── ETF 유니버스 현황판 ── */}
                <section style={S.panel}>
                    <div style={S.sectionTitle}>
                        <h2 style={{ margin: 0, fontSize: 20 }}>ETF 유니버스</h2>
                        <span style={{ color: "#94a3b8", fontSize: 13 }}>모멘텀여우 운용 대상 12종</span>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(200px,1fr))", gap: 10 }}>
                        {Object.entries(ETF_NAMES).map(([sym, name]) => {
                            const type = ETF_TYPE[sym];
                            const typeColor = TYPE_COLOR[type] || "#94a3b8";
                            const isHeld = (data.portfolio || []).some((p) => p.symbol === sym);
                            return (
                                <div key={sym} style={{
                                    ...S.universeCard,
                                    borderColor: isHeld ? `${typeColor}55` : "rgba(148,163,184,0.1)",
                                    background: isHeld ? `${typeColor}0d` : "rgba(30,41,59,0.5)",
                                }}>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                                        <span style={{ fontWeight: 700, fontSize: 15, color: "#e2e8f0" }}>{sym}</span>
                                        <div style={{ display: "flex", gap: 4 }}>
                                            {type && (
                                                <span style={{
                                                    fontSize: 11, padding: "2px 6px", borderRadius: 999,
                                                    background: `${typeColor}22`, color: typeColor, fontWeight: 600,
                                                }}>{type}</span>
                                            )}
                                            {isHeld && (
                                                <span style={{
                                                    fontSize: 11, padding: "2px 6px", borderRadius: 999,
                                                    background: "rgba(16,185,129,0.2)", color: "#6ee7b7", fontWeight: 700,
                                                }}>보유</span>
                                            )}
                                        </div>
                                    </div>
                                    <p style={{ margin: 0, fontSize: 11, color: "#64748b", lineHeight: 1.4 }}>{name}</p>
                                </div>
                            );
                        })}
                    </div>
                </section>

                {/* ── AI 판단 로그 ── */}
                <section style={S.panel}>
                    <div style={S.sectionTitle}>
                        <h2 style={{ margin: 0, fontSize: 20 }}>AI 판단 로그</h2>
                        <span style={{ color: "#94a3b8", fontSize: 13 }}>최근 20건</span>
                    </div>
                    {logs.length === 0 ? (
                        <div style={S.empty}>아직 표시할 판단 로그가 없습니다.</div>
                    ) : (
                        <div style={{ display: "grid", gap: 12 }}>
                            {logs.map((log, i) => {
                                const hasBuy = log.buys?.length > 0;
                                const hasSell = log.sells?.length > 0;
                                const action = hasBuy && hasSell ? "REBAL" : hasBuy ? "BUY" : hasSell ? "SELL" : "HOLD";
                                const actionColor = { BUY: "#6ee7b7", SELL: "#fca5a5", REBAL: "#fcd34d", HOLD: "#94a3b8" }[action];
                                const actionBg = { BUY: "rgba(16,185,129,0.2)", SELL: "rgba(239,68,68,0.2)", REBAL: "rgba(245,158,11,0.2)", HOLD: "rgba(148,163,184,0.2)" }[action];

                                return (
                                    <div key={i} style={S.logCard}>
                                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                                                <span style={{ ...S.actionBadge, background: actionBg, color: actionColor }}>{action}</span>
                                                {log.buys?.length > 0 && <span style={{ fontSize: 13, color: "#6ee7b7" }}>매수: {log.buys.join(", ")}</span>}
                                                {log.sells?.length > 0 && <span style={{ fontSize: 13, color: "#fca5a5" }}>매도: {log.sells.join(", ")}</span>}
                                                {log.regime && <RegimeBadge regime={log.regime} />}
                                            </div>
                                            <span style={{ color: "#64748b", fontSize: 12 }}>{log.timestamp || ""}</span>
                                        </div>
                                        {log.note && (
                                            <p style={{ margin: "0 0 8px", fontSize: 14, color: "#cbd5e1", fontStyle: "italic" }}>
                                                "{log.note}"
                                            </p>
                                        )}
                                        {log.trade_results?.length > 0 && (
                                            <div style={{ marginBottom: 8 }}>
                                                {log.trade_results.map((r, j) => (
                                                    <div key={j} style={{ fontSize: 12, color: "#94a3b8", marginBottom: 3 }}>• {r}</div>
                                                ))}
                                            </div>
                                        )}
                                        <div style={{ display: "flex", gap: 16, fontSize: 12, color: "#64748b", flexWrap: "wrap" }}>
                                            <span>모델: {log.model || "-"}</span>
                                            <span>토큰: {log.total_tokens ?? "-"}</span>
                                            {log.vix && <span>VIX: {log.vix}</span>}
                                        </div>
                                    </div>
                                );
                            })}
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
    page: {
        minHeight: "100vh", padding: 24,
        background: "linear-gradient(180deg,#0f172a 0%,#111827 100%)",
        color: "#e5e7eb", fontFamily: "Arial,sans-serif", boxSizing: "border-box",
    },
    container: { maxWidth: 1440, margin: "0 auto", display: "grid", gap: 24 },
    topGrid: { display: "grid", gridTemplateColumns: "340px 1fr", gap: 24, alignItems: "start" },
    panel: {
        background: "rgba(15,23,42,0.85)",
        border: "1px solid rgba(148,163,184,0.18)",
        borderRadius: 20, padding: 24,
        boxShadow: "0 10px 30px rgba(0,0,0,0.22)",
    },
    leftPanel: { display: "flex", flexDirection: "column", gap: 0 },
    logo: {
        width: 80, height: 80, borderRadius: "50%",
        background: "linear-gradient(135deg,#f59e0b,#ef4444)",
        display: "flex", alignItems: "center", justifyContent: "center", fontSize: 38,
    },
    strategyBox: {
        background: "rgba(245,158,11,0.06)",
        border: "1px solid rgba(245,158,11,0.2)",
        borderRadius: 12, padding: "12px 14px",
    },
    summaryList: { display: "grid", gap: 12, marginTop: 20 },
    summaryCard: {
        background: "rgba(30,41,59,0.7)", borderRadius: 14,
        padding: 16, border: "1px solid rgba(148,163,184,0.12)",
    },
    sectionTitle: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 },
    etfLayout: { display: "grid", gridTemplateColumns: "280px 1fr", gap: 20 },
    donutWrap: { display: "grid", gap: 12 },
    legend: { display: "grid", gap: 8 },
    legendRow: {
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "8px 10px", borderRadius: 10, cursor: "pointer",
    },
    detailCard: {
        background: "rgba(30,41,59,0.6)",
        border: "1px solid rgba(148,163,184,0.1)",
        borderRadius: 14, padding: 16,
    },
    universeCard: {
        borderRadius: 12, padding: "10px 14px",
        border: "1px solid", transition: "background 0.15s",
    },
    badge: { padding: "6px 12px", borderRadius: 999, fontSize: 13, fontWeight: 700 },
    metricGrid: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10 },
    metric: { background: "rgba(15,23,42,0.7)", borderRadius: 10, padding: 10 },
    logCard: {
        background: "rgba(30,41,59,0.58)",
        border: "1px solid rgba(148,163,184,0.1)",
        borderRadius: 14, padding: 16,
    },
    actionBadge: { padding: "4px 10px", borderRadius: 999, fontSize: 13, fontWeight: 700 },
    empty: {
        minHeight: 140, display: "flex", alignItems: "center",
        justifyContent: "center", color: "#94a3b8", borderRadius: 14,
        background: "rgba(30,41,59,0.45)", textAlign: "center", padding: 20,
    },
};
