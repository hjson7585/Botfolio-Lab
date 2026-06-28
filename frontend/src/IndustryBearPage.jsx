import { useEffect, useMemo, useState } from "react";

const API = "http://localhost:8000";

function fmt(v) {
    if (v == null || v === "") return "-";
    return new Intl.NumberFormat("ko-KR").format(Number(v));
}
function fmtPct(v) {
    if (v == null || v === "") return "-";
    const n = Number(v);
    return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function DonutChart({ items }) {
    const slices = useMemo(() => {
        const valid = items.filter((i) => Number(i.weight) > 0);
        const colors = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#84cc16", "#f97316", "#ec4899", "#a855f7", "#14b8a6", "#f43f5e"];
        let cum = 0;
        return valid.map((item, idx) => {
            const start = cum;
            cum += Number(item.weight);
            return { ...item, color: colors[idx % colors.length], start };
        });
    }, [items]);

    if (!slices.length)
        return <div style={styles.empty}>보유 ETF 없음</div>;

    return (
        <div style={styles.donutWrap}>
            <div style={{ ...styles.donut, background: `conic-gradient(${slices.map((s) => `${s.color} ${s.start}% ${s.start + s.weight}%`).join(",")})` }}>
                <div style={styles.donutHole}>
                    <span style={{ fontSize: 12, color: "#94a3b8" }}>ETF</span>
                    <strong style={{ fontSize: 28 }}>{slices.length}</strong>
                </div>
            </div>
            <div style={styles.legend}>
                {slices.map((s) => (
                    <div key={s.symbol} style={styles.legendRow}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ width: 10, height: 10, borderRadius: "50%", background: s.color, display: "inline-block" }} />
                            <span style={{ fontSize: 13, color: "#e2e8f0" }}>{s.symbol}</span>
                        </div>
                        <span style={{ fontSize: 13, fontWeight: 700 }}>{fmtPct(s.weight)}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default function IndustryBearPage() {
    const [logs, setLogs] = useState([]);
    const [data, setData] = useState({ portfolio: [], cash: null, total_asset: null, profit_rate: null });

    useEffect(() => {
        fetch(`${API}/ai-logs`).then((r) => r.json()).then((d) => setLogs(Array.isArray(d) ? d : [])).catch(() => { });
        fetch(`${API}/portfolio`).then((r) => r.json()).then((d) => setData(d)).catch(() => { });
    }, []);

    return (
        <div style={styles.page}>
            <div style={styles.container}>

                {/* TOP */}
                <div style={styles.topGrid}>

                    {/* LEFT — 로고 + 자금현황 */}
                    <section style={{ ...styles.panel, ...styles.leftPanel }}>
                        <div style={styles.logo}>곰</div>
                        <h1 style={{ margin: "16px 0 4px", fontSize: 26 }}>인더스트리곰</h1>
                        <p style={{ margin: 0, color: "#94a3b8", fontSize: 14, lineHeight: 1.6 }}>
                            미국 산업 ETF AI 자동매매 에이전트
                        </p>
                        <div style={styles.summaryList}>
                            {[
                                { label: "실시간 수익률", value: data.profit_rate != null ? fmtPct(data.profit_rate) : "-" },
                                { label: "총 자산", value: data.total_asset != null ? `$${fmt(data.total_asset)}` : "-" },
                                { label: "보유 현금", value: data.cash != null ? `$${fmt(data.cash)}` : "-" },
                            ].map(({ label, value }) => (
                                <div key={label} style={styles.summaryCard}>
                                    <span style={{ color: "#94a3b8", fontSize: 13, display: "block", marginBottom: 6 }}>{label}</span>
                                    <strong style={{ fontSize: 22 }}>{value}</strong>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* RIGHT — ETF 목록 */}
                    <section style={styles.panel}>
                        <div style={styles.sectionTitle}>
                            <h2 style={{ margin: 0, fontSize: 20 }}>보유 ETF 목록</h2>
                            <span style={{ color: "#94a3b8", fontSize: 13 }}>보유 비중 및 상세 정보</span>
                        </div>

                        <div style={styles.etfLayout}>
                            <DonutChart items={data.portfolio} />

                            <div style={{ display: "grid", gap: 12 }}>
                                {data.portfolio.length === 0 ? (
                                    <div style={styles.empty}>보유 중인 ETF 데이터가 없습니다.</div>
                                ) : (
                                    data.portfolio.map((item) => (
                                        <div key={item.symbol} style={styles.detailCard}>
                                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                                                <div>
                                                    <h3 style={{ margin: 0, fontSize: 18 }}>{item.symbol}</h3>
                                                    <p style={{ margin: "4px 0 0", color: "#94a3b8", fontSize: 13 }}>
                                                        {item.sector || ""}
                                                    </p>
                                                </div>
                                                <span style={styles.badge}>{fmtPct(item.weight)}</span>
                                            </div>
                                            <div style={styles.metricGrid}>
                                                {[
                                                    { label: "보유 수량", value: `${fmt(item.quantity)}주` },
                                                    { label: "평균 단가", value: `$${fmt(item.avg_price)}` },
                                                    { label: "평가금액", value: `$${fmt(item.market_value)}` },
                                                    { label: "수익률", value: fmtPct(item.profit_rate) },
                                                ].map(({ label, value }) => (
                                                    <div key={label} style={styles.metric}>
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

                {/* BOTTOM — 판단 로그 */}
                <section style={styles.panel}>
                    <div style={styles.sectionTitle}>
                        <h2 style={{ margin: 0, fontSize: 20 }}>AI 판단 로그</h2>
                        <span style={{ color: "#94a3b8", fontSize: 13 }}>최근 20건</span>
                    </div>

                    {logs.length === 0 ? (
                        <div style={styles.empty}>아직 표시할 판단 로그가 없습니다.</div>
                    ) : (
                        <div style={{ display: "grid", gap: 12 }}>
                            {logs.map((log, i) => (
                                <div key={i} style={styles.logCard}>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                                            <span style={{ ...styles.actionBadge, background: log.action === "BUY" ? "rgba(16,185,129,0.2)" : log.action === "SELL" ? "rgba(239,68,68,0.2)" : "rgba(148,163,184,0.2)", color: log.action === "BUY" ? "#6ee7b7" : log.action === "SELL" ? "#fca5a5" : "#94a3b8" }}>
                                                {log.action || "HOLD"}
                                            </span>
                                            <strong style={{ fontSize: 15 }}>{log.selected_etf && log.selected_etf !== "NONE" ? log.selected_etf : "-"}</strong>
                                            {log.sector && log.sector !== "NONE" && <span style={{ color: "#94a3b8", fontSize: 13 }}>{log.sector}</span>}
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

const styles = {
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
    donutWrap: { display: "grid", gap: 16 },
    donut: { width: 220, height: 220, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto" },
    donutHole: { width: 120, height: 120, borderRadius: "50%", background: "#0f172a", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", border: "1px solid rgba(148,163,184,0.15)" },
    legend: { display: "grid", gap: 8 },
    legendRow: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 10px", borderRadius: 10, background: "rgba(30,41,59,0.55)" },
    detailCard: { background: "rgba(30,41,59,0.6)", border: "1px solid rgba(148,163,184,0.1)", borderRadius: 14, padding: 16 },
    badge: { padding: "6px 12px", borderRadius: 999, background: "rgba(37,99,235,0.18)", color: "#93c5fd", fontSize: 13, fontWeight: 700 },
    metricGrid: { display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10 },
    metric: { background: "rgba(15,23,42,0.7)", borderRadius: 10, padding: 10 },
    logCard: { background: "rgba(30,41,59,0.58)", border: "1px solid rgba(148,163,184,0.1)", borderRadius: 14, padding: 16 },
    actionBadge: { padding: "4px 10px", borderRadius: 999, fontSize: 13, fontWeight: 700 },
    empty: { minHeight: 140, display: "flex", alignItems: "center", justifyContent: "center", color: "#94a3b8", borderRadius: 14, background: "rgba(30,41,59,0.45)", textAlign: "center", padding: 20 },
};
