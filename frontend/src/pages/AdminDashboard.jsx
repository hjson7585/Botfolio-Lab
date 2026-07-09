import { useEffect, useMemo, useState } from "react";
import {
    PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
    LineChart, Line, XAxis, YAxis, CartesianGrid, Legend,
    BarChart, Bar,
} from "recharts";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const TOKEN_COLORS = ["#3B82F6", "#10B981"];
const AGENT_COLORS = { bear: "#3B82F6", fox: "#F59E0B", turtle: "#10B981" };

// 수정 — localStorage (브라우저 재시작해도 유지)
function getOrCreateSessionId() {
    const KEY = "botfolio_session_id";
    let sid = localStorage.getItem(KEY);
    if (!sid) {
        sid = crypto.randomUUID();
        localStorage.setItem(KEY, sid);
    }
    return sid;
}

/* ─────────────────────────────────────────────────────────────
   전략 파라미터
───────────────────────────────────────────────────────────── */
const PARAMS = {
    bear: [
        ["전략 유형", "섹터 ETF 중장기 로테이션 (6개월~2년)"],
        ["투자 기간", "6개월 ~ 2년 (최소 보유 90일)"],
        ["실행 주기", "손절/익절 매일 체크 · 리밸런싱 월 1회"],
        ["ETF 유니버스", "12개 섹터 ETF"],
        ["최대 보유 종목", "5종목"],
        ["종목당 비중", "현금 균등 배분 (포트폴리오의 최대 20%)"],
        ["진입 조건", "점수 3/6↑ · SMA50/200 정배열 · 3·6개월 모멘텀 · 뉴스 장기 감성"],
        ["AI 모델", "deepseek (뉴스 감성 분석 + 최종 매매 판단)"],
        ["토큰 절감", "감성 캐시 23h · 후보 상위 6개만 LLM 전달"],
        ["손절 기준", "-20.0% (보유 기간 무관 즉시 실행)"],
        ["익절 기준", "+40.0% (최소 90일 보유 후 실행)"],
        ["리밸런싱", "SMA200 하회 + 3개월 -5% 시 구조적 교체"],
    ],
    fox: [
        ["전략 유형", "단기 모멘텀 + 시장 레짐 필터"],
        ["투자 기간", "1주 ~ 3개월"],
        ["실행 주기", "매일 오전 10:31 ET (장 마감 후)"],
        ["ETF 유니버스", "12개 ETF (공격·코어·팩터·방어)"],
        ["최대 보유 종목", "5종목"],
        ["종목당 비중", "포트폴리오의 최대 20%"],
        ["진입 조건", "모멘텀 스코어 3점↑ / 5점 만점"],
        ["AI 모델", "deepseek"],
        ["토큰 절감", "레짐 필터 후 상위 후보만 LLM 전달"],
        ["손절 기준", "-7.0% (평균 단가 대비)"],
        ["익절 기준", "+20.0% (평균 단가 대비)"],
        ["리밸런싱", "VIX 25↑ 방어 전환 / VIX 35↑ 현금화"],
    ],
    turtle: [
        ["전략 유형", "고배당 ETF 장기 배당 복리 투자"],
        ["투자 기간", "6개월 ~ 2년"],
        ["실행 주기", "매일 오전 10:31 ET (장 마감 후)"],
        ["ETF 유니버스", "12개 고배당 ETF"],
        ["최대 보유 종목", "3종목"],
        ["종목당 비중", "포트폴리오의 최대 33%"],
        ["진입 조건", "배당수익률 3%↑ + MA50 위 + RSI 45~65 + 배당성장 3년↑"],
        ["AI 모델", "deepseek"],
        ["토큰 절감", "배당스코어 상위 후보 3개만 LLM 전달"],
        ["손절 기준", "-12.0% (평균 단가 대비)"],
        ["익절 기준", "+30.0% 또는 배당 삭감 감지 즉시 매도"],
        ["리밸런싱", "분기 배당 재투자 + 배당수익률 역전 시 교체"],
    ],
};

/* ─────────────────────────────────────────────────────────────
   ETF 유니버스
───────────────────────────────────────────────────────────── */
const ETF_UNIVERSE = {
    bear: {
        XLK: "Technology Select Sector SPDR",
        SOXX: "iShares Semiconductor ETF",
        XLF: "Financial Select Sector SPDR",
        XLY: "Consumer Discretionary Select Sector",
        XLC: "Communication Services Select Sector",
        XLI: "Industrial Select Sector SPDR",
        XLE: "Energy Select Sector SPDR",
        XLB: "Materials Select Sector SPDR",
        XLV: "Health Care Select Sector SPDR",
        XLP: "Consumer Staples Select Sector SPDR",
        XLU: "Utilities Select Sector SPDR",
        XLRE: "Real Estate Select Sector SPDR",
    },
    fox: {
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
    },
    turtle: {
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
    },
};

const FOX_ETF_TYPE = {
    QQQ: "공격", VGT: "공격", SOXX: "공격", SMH: "공격",
    SPY: "코어", VOO: "코어", IWM: "코어",
    MTUM: "팩터", QUAL: "팩터",
    TLT: "방어", IEF: "방어", GLD: "방어",
};

const TURTLE_ETF_TYPE = {
    SCHD: "배당성장", DGRO: "배당성장", VIG: "배당성장", NOBL: "배당성장",
    VYM: "고배당", HDV: "고배당", SPYD: "고배당",
    JEPI: "커버드콜", JEPQ: "커버드콜", DIVO: "커버드콜",
    VNQ: "리츠",
    XLU: "유틸리티",
};

const TYPE_STYLE = {
    공격: { bg: "bg-amber-100", text: "text-amber-600" },
    코어: { bg: "bg-blue-100", text: "text-blue-600" },
    팩터: { bg: "bg-purple-100", text: "text-purple-600" },
    방어: { bg: "bg-green-100", text: "text-green-600" },
    배당성장: { bg: "bg-blue-100", text: "text-blue-600" },
    고배당: { bg: "bg-green-100", text: "text-green-600" },
    커버드콜: { bg: "bg-amber-100", text: "text-amber-600" },
    리츠: { bg: "bg-purple-100", text: "text-purple-600" },
    유틸리티: { bg: "bg-teal-100", text: "text-teal-600" },
};

const AGENT_META = {
    bear: { label: "🐻 인더스트리곰", active: "bg-blue-500 text-white", inactive: "bg-white text-gray-500 border border-gray-100" },
    fox: { label: "🦊 모멘텀여우", active: "bg-amber-400 text-white", inactive: "bg-white text-gray-500 border border-gray-100" },
    turtle: { label: "🐢 배당거북", active: "bg-emerald-500 text-white", inactive: "bg-white text-gray-500 border border-gray-100" },
};

const HIGHLIGHT_KEYS = {
    "손절 기준": "text-red-500",
    "익절 기준": "text-green-500",
    "진입 조건": "text-indigo-600",
    "리밸런싱": "text-orange-500",
};

/* ─────────────────────────────────────────────────────────────
   유틸
───────────────────────────────────────────────────────────── */
function buildDailyTokens(logs) {
    const map = {};
    logs.forEach((log) => {
        if (!log.timestamp) return;
        const dateStr = log.timestamp.slice(0, 10);
        if (!map[dateStr]) map[dateStr] = { input: 0, output: 0 };
        map[dateStr].input += log.input_tokens || 0;
        map[dateStr].output += log.output_tokens || 0;
    });
    return Object.entries(map)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([date, v]) => ({
            date: date.slice(5).replace("-", "/"),
            input: v.input,
            output: v.output,
            total: v.input + v.output,
        }));
}

function buildCombinedDailyTokens(allLogs) {
    const map = {};
    Object.entries(allLogs).forEach(([agent, logs]) => {
        logs.forEach((log) => {
            if (!log.timestamp) return;
            const date = log.timestamp.slice(0, 10);
            if (!map[date]) map[date] = { bear: 0, fox: 0, turtle: 0 };
            map[date][agent] += (log.input_tokens || 0) + (log.output_tokens || 0);
        });
    });
    return Object.entries(map)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([date, v]) => ({
            date: date.slice(5).replace("-", "/"),
            bear: v.bear,
            fox: v.fox,
            turtle: v.turtle,
            total: v.bear + v.fox + v.turtle,
        }));
}

/* ─────────────────────────────────────────────────────────────
   서브 컴포넌트
───────────────────────────────────────────────────────────── */
function ParamTable({ params, accentBg, accentText, accentBorder }) {
    return (
        <div className={`rounded-2xl border overflow-hidden ${accentBorder}`}>
            {params.map(([k, v], idx) => {
                const hlColor = HIGHLIGHT_KEYS[k] || accentText;
                return (
                    <div key={k}
                        className={`flex justify-between items-start gap-3 px-4 py-3 text-sm
                            ${idx % 2 === 0 ? accentBg : "bg-white"}
                            ${idx !== params.length - 1 ? `border-b ${accentBorder}` : ""}`}>
                        <span className="text-gray-400 shrink-0 w-28">{k}</span>
                        <span className={`font-semibold text-right leading-snug ${hlColor}`}>{v}</span>
                    </div>
                );
            })}
        </div>
    );
}

function EtfList({ universe, typeMap }) {
    return (
        <div className="flex flex-col gap-2 max-h-[460px] overflow-y-auto pr-1">
            {Object.entries(universe).map(([sym, name]) => {
                const type = typeMap?.[sym];
                const ts = type ? TYPE_STYLE[type] : null;
                return (
                    <div key={sym}
                        className="flex items-center justify-between bg-gray-50 rounded-xl px-3 py-2 border border-gray-100">
                        <div className="flex items-center gap-2">
                            <span className="font-black text-gray-800 text-sm">{sym}</span>
                            {ts && (
                                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${ts.bg} ${ts.text}`}>
                                    {type}
                                </span>
                            )}
                        </div>
                        <span className="text-xs text-gray-400 text-right max-w-[150px] leading-tight">{name}</span>
                    </div>
                );
            })}
        </div>
    );
}

function LogList({ logs, type }) {
    if (!logs.length)
        return (
            <div className="flex items-center justify-center h-24 rounded-2xl bg-gray-50 text-gray-400 text-sm">
                로그 없음
            </div>
        );

    if (type === "fox") {
        return (
            <div className="flex flex-col gap-3">
                {logs.map((log, i) => {
                    const hasBuy = log.buys?.length > 0;
                    const hasSell = log.sells?.length > 0;
                    const action = hasBuy && hasSell ? "REBAL" : hasBuy ? "BUY" : hasSell ? "SELL" : "HOLD";
                    const cls = {
                        BUY: "bg-green-100 text-green-600",
                        SELL: "bg-red-100 text-red-500",
                        REBAL: "bg-amber-100 text-amber-600",
                        HOLD: "bg-gray-200 text-gray-500",
                    }[action];
                    return (
                        <div key={i} className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                            <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <span className={`text-xs font-bold px-3 py-1 rounded-full ${cls}`}>{action}</span>
                                    {hasBuy && <span className="text-xs font-bold text-green-600">매수: {log.buys.join(", ")}</span>}
                                    {hasSell && <span className="text-xs font-bold text-red-500">매도: {log.sells.join(", ")}</span>}
                                    {log.regime && <span className="text-xs text-gray-400">{log.regime}</span>}
                                </div>
                                <span className="text-xs text-gray-300">{log.timestamp || ""}</span>
                            </div>
                            {log.note && <p className="text-xs text-gray-500 mb-1 italic">"{log.note}"</p>}
                            <div className="flex gap-3 text-xs text-gray-300">
                                <span>모델: {log.model || "-"}</span>
                                <span>토큰: {log.total_tokens ?? "-"}</span>
                                {log.vix && <span>VIX: {log.vix}</span>}
                            </div>
                        </div>
                    );
                })}
            </div>
        );
    }

    if (type === "turtle") {
        return (
            <div className="flex flex-col gap-3">
                {logs.map((log, i) => (
                    <div key={i} className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                        <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className={`text-xs font-bold px-3 py-1 rounded-full ${log.action === "BUY" ? "bg-green-100 text-green-600" :
                                    log.action === "SELL" ? "bg-red-100 text-red-500" :
                                        "bg-gray-200 text-gray-500"}`}>
                                    {log.action || "HOLD"}
                                </span>
                                <strong className="text-sm text-gray-700">
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
                        <p className="text-xs text-gray-500 mb-1">{log.reason || "-"}</p>
                        <div className="flex gap-3 text-xs text-gray-300">
                            <span>모델: {log.model || "-"}</span>
                            <span>토큰: {log.total_tokens ?? "-"}</span>
                            {log.score && <span>점수: {log.score}/10</span>}
                            {log.trade_result && <span>매매결과: {log.trade_result}</span>}
                        </div>
                    </div>
                ))}
            </div>
        );
    }

    // bear
    return (
        <div className="flex flex-col gap-3">
            {logs.map((log, i) => {
                const hasBuy = log.buys?.length > 0;
                const hasSell = log.sells?.length > 0;
                const isSkip = log.action === "SKIP_REBALANCE";
                const action = isSkip ? "SKIP"
                    : hasBuy && hasSell ? "REBAL"
                        : hasBuy ? "BUY"
                            : hasSell ? "SELL"
                                : "HOLD";
                const cls = {
                    BUY: "bg-green-100 text-green-600",
                    SELL: "bg-red-100 text-red-500",
                    REBAL: "bg-blue-100 text-blue-600",
                    HOLD: "bg-gray-200 text-gray-500",
                    SKIP: "bg-gray-100 text-gray-400",
                }[action];
                const sentimentEntries = log.sentiment_signals
                    ? Object.entries(log.sentiment_signals) : [];

                return (
                    <div key={i} className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                        <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className={`text-xs font-bold px-3 py-1 rounded-full ${cls}`}>{action}</span>
                                {hasBuy && <span className="text-xs font-bold text-green-600">매수: {log.buys.join(", ")}</span>}
                                {hasSell && <span className="text-xs font-bold text-red-500">매도: {log.sells.join(", ")}</span>}
                                {log.regime && <span className="text-xs text-gray-400">{log.regime}</span>}
                                {log.sma200_weak?.length > 0 && (
                                    <span className="text-xs text-orange-400">SMA200↓ {log.sma200_weak.join(", ")}</span>
                                )}
                            </div>
                            <span className="text-xs text-gray-300">{log.timestamp || ""}</span>
                        </div>
                        {sentimentEntries.length > 0 && (
                            <div className="flex flex-wrap gap-1 mb-1">
                                {sentimentEntries.map(([sym, s]) => (
                                    <span key={sym}
                                        className={`text-xs font-bold px-2 py-0.5 rounded-full
                                            ${s.score > 0 ? "bg-green-50 text-green-600" : "bg-red-50 text-red-500"}`}>
                                        {s.score > 0 ? "📈" : "📉"} {sym}
                                    </span>
                                ))}
                            </div>
                        )}
                        {log.note && <p className="text-xs text-gray-500 mb-1 italic">"{log.note}"</p>}
                        <div className="flex gap-3 text-xs text-gray-300">
                            <span>모델: {log.model || "-"}</span>
                            <span>토큰: {log.total_tokens ?? "-"}</span>
                            {log.vix && <span>VIX: {log.vix}</span>}
                            {log.strategy && <span>{log.strategy}</span>}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

/* ─── 차트 컴포넌트 ─── */
function AgentTokenLineChart({ dailyData, agentKey }) {
    const color = AGENT_COLORS[agentKey];
    if (!dailyData.length)
        return (
            <div className="flex items-center justify-center h-40 rounded-2xl bg-gray-50 text-gray-400 text-sm">
                데이터 없음
            </div>
        );
    return (
        <div style={{ width: "100%", height: 200, minWidth: 0 }}>
            <ResponsiveContainer width="100%" height="100%" debounce={1}>
                <LineChart data={dailyData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} width={48} />
                    <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 20px rgba(0,0,0,0.1)", fontSize: 12 }}
                        formatter={(v, n) => [v.toLocaleString(), n]} />
                    <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} iconType="circle" />
                    <Line type="monotone" dataKey="input" name="입력 토큰" stroke={color} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                    <Line type="monotone" dataKey="output" name="출력 토큰" stroke={TOKEN_COLORS[1]} strokeWidth={2} strokeDasharray="4 2" dot={{ r: 3 }} activeDot={{ r: 5 }} />
                    <Line type="monotone" dataKey="total" name="합계" stroke="#111827" strokeWidth={1.5} dot={false} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}

function CombinedTokenLineChart({ combinedData }) {
    if (!combinedData.length)
        return (
            <div className="flex items-center justify-center h-40 rounded-2xl bg-gray-50 text-gray-400 text-sm">
                데이터 없음
            </div>
        );
    return (
        <div style={{ width: "100%", height: 240, minWidth: 0 }}>
            <ResponsiveContainer width="100%" height="100%" debounce={1}>
                <LineChart data={combinedData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} width={52} />
                    <Tooltip contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 20px rgba(0,0,0,0.1)", fontSize: 12 }}
                        formatter={(v, n) => [v.toLocaleString(), n]} />
                    <Legend wrapperStyle={{ fontSize: 12, paddingTop: 8 }} iconType="circle" />
                    <Line type="monotone" dataKey="bear" name="🐻 인더스트리곰" stroke={AGENT_COLORS.bear} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                    <Line type="monotone" dataKey="fox" name="🦊 모멘텀여우" stroke={AGENT_COLORS.fox} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                    <Line type="monotone" dataKey="turtle" name="🐢 배당거북" stroke={AGENT_COLORS.turtle} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                    <Line type="monotone" dataKey="total" name="전체 합계" stroke="#6b7280" strokeWidth={2} strokeDasharray="5 3" dot={false} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}

/* ✅ 일별 방문자 바 + 라인 차트 */
function VisitorLineChart({ dailyData }) {
    if (!dailyData.length)
        return (
            <div className="flex items-center justify-center h-40 rounded-2xl bg-gray-50 text-gray-400 text-sm">
                방문 데이터 없음
            </div>
        );
    return (
        <div style={{ width: "100%", height: 200, minWidth: 0 }}>
            <ResponsiveContainer width="100%" height="100%" debounce={1}>
                <BarChart data={dailyData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} />
                    <YAxis
                        tick={{ fontSize: 11, fill: "#9ca3af" }}
                        tickLine={false}
                        axisLine={false}
                        width={32}
                        allowDecimals={false}
                    />
                    <Tooltip
                        contentStyle={{ borderRadius: 12, border: "none", boxShadow: "0 4px 20px rgba(0,0,0,0.1)", fontSize: 12 }}
                        formatter={(v) => [`${v}명`, "방문자"]}
                    />
                    <Bar dataKey="count" name="방문자" fill="#3B82F6" radius={[6, 6, 0, 0]} maxBarSize={36} />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

/* ✅ 토큰 파이 차트 — 별도 컴포넌트로 분리, 고정 픽셀 높이 + debounce 적용 */
function TokenPieChart({ tokenData }) {
    return (
        <div style={{ width: "100%", height: 200, minWidth: 0 }}>
            <ResponsiveContainer width="100%" height="100%" debounce={1}>
                <PieChart>
                    <Pie data={tokenData} cx="50%" cy="50%"
                        innerRadius={55} outerRadius={85}
                        paddingAngle={5} dataKey="value">
                        {tokenData.map((_, idx) => (
                            <Cell key={idx} fill={TOKEN_COLORS[idx]} />
                        ))}
                    </Pie>
                    <Tooltip />
                </PieChart>
            </ResponsiveContainer>
        </div>
    );
}

/* ─────────────────────────────────────────────────────────────
   메인 컴포넌트
───────────────────────────────────────────────────────────── */
export default function AdminDashboard() {
    const [activeAgent, setActiveAgent] = useState("bear");
    const [allLogs, setAllLogs] = useState({ bear: [], fox: [], turtle: [] });
    const [allTokens, setAllTokens] = useState({ bear: [], fox: [], turtle: [] });

    // ✅ 방문자 상태
    const [visitorTotal, setVisitorTotal] = useState(0);
    const [visitorDaily, setVisitorDaily] = useState([]);
    const [todayVisitors, setTodayVisitors] = useState(0);

    /* ── 방문 기록 + 집계 로드 ── */
    useEffect(() => {
        const sid = getOrCreateSessionId();

        // 방문 신고 (세션당 하루 1회)
        fetch(`${API}/visit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sid }),
        }).catch(() => { });

        // 누적 방문자 수
        fetch(`${API}/visit-count`)
            .then((r) => r.json())
            .then((d) => setVisitorTotal(d.total || 0))
            .catch(() => { });

        // 일별 방문자 (최근 30일)
        fetch(`${API}/visit-daily?days=30`)
            .then((r) => r.json())
            .then((arr) => {
                setVisitorDaily(Array.isArray(arr) ? arr : []);
                // 오늘 방문자
                const today = new Date();
                const mm = String(today.getMonth() + 1).padStart(2, "0");
                const dd = String(today.getDate()).padStart(2, "0");
                const todayStr = `${mm}/${dd}`;
                const todayRow = arr.find((r) => r.date === todayStr);
                setTodayVisitors(todayRow?.count || 0);
            })
            .catch(() => { });
    }, []);

    /* ── AI 로그 로드 ── */
    useEffect(() => {
        const calcTokens = (data) => {
            let inp = 0, out = 0;
            data.forEach((l) => { inp += l.input_tokens || 0; out += l.output_tokens || 0; });
            return [{ name: "입력 토큰", value: inp }, { name: "출력 토큰", value: out }];
        };

        fetch(`${API}/ai-logs`)
            .then((r) => r.json())
            .then((d) => {
                const data = Array.isArray(d) ? d : [];
                setAllLogs((p) => ({ ...p, bear: data }));
                setAllTokens((p) => ({ ...p, bear: calcTokens(data) }));
            }).catch(() => { });

        fetch(`${API}/fox-logs`)
            .then((r) => r.json())
            .then((d) => {
                const data = Array.isArray(d) ? d : [];
                setAllLogs((p) => ({ ...p, fox: data }));
                setAllTokens((p) => ({ ...p, fox: calcTokens(data) }));
            }).catch(() => { });

        fetch(`${API}/turtle-logs`)
            .then((r) => r.json())
            .then((d) => {
                const data = Array.isArray(d) ? d : [];
                setAllLogs((p) => ({ ...p, turtle: data }));
                setAllTokens((p) => ({ ...p, turtle: calcTokens(data) }));
            }).catch(() => { });
    }, []);

    const logs = allLogs[activeAgent];
    const tokenData = allTokens[activeAgent];

    const dailyTokens = useMemo(
        () => buildDailyTokens(allLogs[activeAgent]),
        [allLogs, activeAgent]
    );

    const combinedDailyTokens = useMemo(
        () => buildCombinedDailyTokens(allLogs),
        [allLogs]
    );

    const totalAllTokens = useMemo(() => {
        let total = 0;
        Object.values(allLogs).forEach((logs) =>
            logs.forEach((l) => { total += (l.input_tokens || 0) + (l.output_tokens || 0); })
        );
        return total;
    }, [allLogs]);

    const accentMap = {
        bear: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-100" },
        fox: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-100" },
        turtle: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-100" },
    };
    const accent = accentMap[activeAgent];
    const typeMapBy = { bear: {}, fox: FOX_ETF_TYPE, turtle: TURTLE_ETF_TYPE };

    return (
        <div className="min-h-screen bg-[#f5f7fb] p-12">

            {/* ── 헤더 ── */}
            <div className="mb-10">
                <h1 className="text-5xl font-black text-gray-800 mb-2">관리자 대시보드</h1>
                <p className="text-gray-400 text-lg">Botfolio AI 관리자 시스템</p>
            </div>

            {/* ── 상단 요약 카드 2열 ── */}
            <div className="grid grid-cols-2 gap-8 mb-10">

                {/* ✅ 방문자 카드 — 누적 + 오늘 + 일별 바차트 */}
                <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                    <p className="text-gray-400 mb-1 text-sm">방문자 현황</p>

                    {/* 누적 + 오늘 요약 */}
                    <div className="flex items-end gap-6 mb-6">
                        <div>
                            <p className="text-xs text-gray-400 mb-1">누적 방문자</p>
                            <h2 className="text-6xl font-black text-blue-500">
                                {visitorTotal.toLocaleString()}
                            </h2>
                        </div>
                        <div className="mb-2">
                            <p className="text-xs text-gray-400 mb-1">오늘 방문자</p>
                            <p className="text-3xl font-black text-indigo-400">
                                {todayVisitors.toLocaleString()}
                            </p>
                        </div>
                    </div>

                    {/* 일별 바차트 */}
                    <div>
                        <p className="text-xs text-gray-400 mb-3">일별 방문자 (최근 30일)</p>
                        <VisitorLineChart dailyData={visitorDaily} />
                    </div>
                </div>

                {/* 토큰 파이 차트 */}
                <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                        <div>
                            <h2 className="text-xl font-black text-gray-800">deepseek 토큰 사용량</h2>
                            <p className="text-xs text-gray-400 mt-0.5">
                                전체 합산:{" "}
                                <span className="font-bold text-gray-600">
                                    {totalAllTokens.toLocaleString()} 토큰
                                </span>
                            </p>
                        </div>
                        <div className="flex gap-2 flex-wrap">
                            {Object.entries(AGENT_META).map(([key, { label, active, inactive }]) => (
                                <button key={key} onClick={() => setActiveAgent(key)}
                                    className={`text-xs font-bold px-3 py-1.5 rounded-full transition
                                        ${activeAgent === key ? active : inactive}`}>
                                    {label}
                                </button>
                            ))}
                        </div>
                    </div>
                    <TokenPieChart tokenData={tokenData} />
                    <div className="flex gap-6 justify-center mt-2">
                        {["입력 토큰", "출력 토큰"].map((label, idx) => (
                            <div key={label} className="flex items-center gap-2 text-sm">
                                <div className="w-3 h-3 rounded-full" style={{ background: TOKEN_COLORS[idx] }} />
                                {label}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* ── 일별 토큰 라인 — 에이전트별 ── */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 mb-10">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-xl font-black text-gray-800">📈 일별 토큰 사용량</h2>
                        <p className="text-xs text-gray-400 mt-0.5">
                            {AGENT_META[activeAgent].label} — 입력 / 출력 토큰 추이
                        </p>
                    </div>
                    <div className="flex gap-2">
                        {Object.entries(AGENT_META).map(([key, { label, active, inactive }]) => (
                            <button key={key} onClick={() => setActiveAgent(key)}
                                className={`text-xs font-bold px-3 py-1.5 rounded-full transition
                                    ${activeAgent === key ? active : inactive}`}>
                                {label}
                            </button>
                        ))}
                    </div>
                </div>
                <div className="grid grid-cols-3 gap-4 mb-6">
                    {[
                        { label: "입력 토큰 합계", value: (tokenData[0]?.value || 0).toLocaleString(), color: "text-blue-500" },
                        { label: "출력 토큰 합계", value: (tokenData[1]?.value || 0).toLocaleString(), color: "text-emerald-500" },
                        { label: "총 토큰", value: ((tokenData[0]?.value || 0) + (tokenData[1]?.value || 0)).toLocaleString(), color: "text-black-800" },
                    ].map(({ label, value, color }) => (
                        <div key={label} className="bg-gray-50 rounded-2xl px-5 py-4 border border-gray-100">
                            <p className="text-xs text-gray-400 mb-1">{label}</p>
                            <p className={`text-2xl font-black ${color}`}>{value}</p>
                        </div>
                    ))}
                </div>
                <AgentTokenLineChart dailyData={dailyTokens} agentKey={activeAgent} />
            </div>

            {/* ── 전체 에이전트 합산 ── */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 mb-10">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-xl font-black text-gray-800">🔢 전체 에이전트 토큰 합산 추이</h2>
                        <p className="text-xs text-gray-400 mt-0.5">인더스트리곰 · 모멘텀여우 · 배당거북 일별 비교</p>
                    </div>
                    <div className="bg-gray-50 rounded-2xl px-5 py-3 border border-gray-100 text-right">
                        <p className="text-xs text-gray-400">3개 에이전트 누적 합계</p>
                        <p className="text-2xl font-black text-gray-700">{totalAllTokens.toLocaleString()}</p>
                    </div>
                </div>
                <div className="grid grid-cols-3 gap-4 mb-6">
                    {Object.entries(AGENT_META).map(([key, { label }]) => {
                        const agentTotal = allLogs[key].reduce(
                            (s, l) => s + (l.input_tokens || 0) + (l.output_tokens || 0), 0
                        );
                        return (
                            <div key={key} className="rounded-2xl px-5 py-4 border"
                                style={{ background: `${AGENT_COLORS[key]}10`, borderColor: `${AGENT_COLORS[key]}33` }}>
                                <p className="text-xs font-semibold mb-1" style={{ color: AGENT_COLORS[key] }}>{label}</p>
                                <p className="text-2xl font-black text-gray-800">{agentTotal.toLocaleString()}</p>
                            </div>
                        );
                    })}
                </div>
                <CombinedTokenLineChart combinedData={combinedDailyTokens} />
            </div>

            {/* ── 에이전트 탭 ── */}
            <div className="flex gap-3 mb-8">
                {Object.entries(AGENT_META).map(([key, { label, active, inactive }]) => (
                    <button key={key} onClick={() => setActiveAgent(key)}
                        className={`px-6 py-3 rounded-2xl font-bold text-sm shadow-sm transition
                            ${activeAgent === key ? active : inactive}`}>
                        {label}
                    </button>
                ))}
            </div>

            {/* ── 3단 패널 ── */}
            <div className="grid grid-cols-3 gap-8">
                <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                    <h3 className="text-lg font-black text-gray-800 mb-4">⚙️ 전략 파라미터</h3>
                    <ParamTable
                        params={PARAMS[activeAgent]}
                        accentBg={accent.bg}
                        accentText={accent.text}
                        accentBorder={accent.border}
                    />
                </div>
                <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                    <h3 className="text-lg font-black text-gray-800 mb-4">📋 ETF 유니버스</h3>
                    <EtfList universe={ETF_UNIVERSE[activeAgent]} typeMap={typeMapBy[activeAgent]} />
                </div>
                <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-black text-gray-800">🤖 AI 판단 로그</h3>
                        <span className="text-xs text-gray-400">최근 {logs.length}건</span>
                    </div>
                    <div className="max-h-[460px] overflow-y-auto pr-1">
                        <LogList logs={logs} type={activeAgent} />
                    </div>
                </div>
            </div>
        </div>
    );
}
