import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

const API = "http://localhost:8000";

const BEAR_PARAMS = [
    ["보유기간", "제한 없음 (장기)"],
    ["손절", "-10.0%"],
    ["익절", "없음 (장기 보유)"],
    ["최대보유", "3종목"],
    ["전략", "산업 사이클 분석"],
    ["실행주기", "매일 오전 10:31 ET"],
];

const FOX_PARAMS = [
    ["보유기간", "1주 ~ 3개월"],
    ["손절", "-7.0%"],
    ["익절", "+20.0%"],
    ["최대보유", "5종목"],
    ["스코어", "5점 만점 / 최소 3점"],
    ["레짐", "VIX 25 / 35 기준"],
];

const FOX_ETF_NAMES = {
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

const FOX_ETF_TYPE = {
    QQQ: "공격", VGT: "공격", SOXX: "공격", SMH: "공격",
    SPY: "코어", VOO: "코어", IWM: "코어",
    MTUM: "팩터", QUAL: "팩터",
    TLT: "방어", IEF: "방어", GLD: "방어",
};

const TYPE_STYLE = {
    공격: { bg: "bg-amber-100", text: "text-amber-600" },
    코어: { bg: "bg-blue-100", text: "text-blue-600" },
    팩터: { bg: "bg-purple-100", text: "text-purple-600" },
    방어: { bg: "bg-green-100", text: "text-green-600" },
};

const BEAR_ETF_NAMES = {
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

const TOKEN_COLORS = ["#3B82F6", "#10B981"];

function ParamTable({ params, accentBg, accentText, accentBorder }) {
    return (
        <div className={`rounded-2xl px-5 py-4 border ${accentBg} ${accentBorder}`}>
            {params.map(([k, v]) => (
                <div key={k} className="flex justify-between text-sm mb-2 last:mb-0">
                    <span className="text-gray-400">{k}</span>
                    <span className={`font-semibold ${accentText}`}>{v}</span>
                </div>
            ))}
        </div>
    );
}

function LogList({ logs, type }) {
    if (!logs.length) {
        return (
            <div className="flex items-center justify-center h-24 rounded-2xl bg-gray-50 text-gray-400 text-sm">
                로그 없음
            </div>
        );
    }

    if (type === "fox") {
        return (
            <div className="flex flex-col gap-3">
                {logs.map((log, i) => {
                    const hasBuy = log.buys?.length > 0;
                    const hasSell = log.sells?.length > 0;
                    const action = hasBuy && hasSell ? "REBAL" : hasBuy ? "BUY" : hasSell ? "SELL" : "HOLD";
                    const actionCls = {
                        BUY: "bg-green-100 text-green-600",
                        SELL: "bg-red-100 text-red-500",
                        REBAL: "bg-amber-100 text-amber-600",
                        HOLD: "bg-gray-200 text-gray-500",
                    }[action];
                    return (
                        <div key={i} className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                            <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <span className={`text-xs font-bold px-3 py-1 rounded-full ${actionCls}`}>{action}</span>
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

    // bear 로그
    return (
        <div className="flex flex-col gap-3">
            {logs.map((log, i) => (
                <div key={i} className="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                    <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                            <span className={`text-xs font-bold px-3 py-1 rounded-full ${log.action === "BUY" ? "bg-green-100 text-green-600" :
                                    log.action === "SELL" ? "bg-red-100 text-red-500" :
                                        "bg-gray-200 text-gray-500"
                                }`}>
                                {log.action || "HOLD"}
                            </span>
                            <strong className="text-sm text-gray-700">
                                {log.selected_etf && log.selected_etf !== "NONE" ? log.selected_etf : "-"}
                            </strong>
                            {log.sector && log.sector !== "NONE" && (
                                <span className="text-xs text-gray-400">{log.sector}</span>
                            )}
                        </div>
                        <span className="text-xs text-gray-300">{log.timestamp || ""}</span>
                    </div>
                    <p className="text-xs text-gray-500 mb-1">{log.reason || "-"}</p>
                    <div className="flex gap-3 text-xs text-gray-300">
                        <span>모델: {log.model || "-"}</span>
                        <span>토큰: {log.total_tokens ?? "-"}</span>
                        {log.trade_result && <span>매매결과: {log.trade_result}</span>}
                    </div>
                </div>
            ))}
        </div>
    );
}

export default function AdminDashboard() {
    const [activeAgent, setActiveAgent] = useState("bear");
    const [visitorCount, setVisitorCount] = useState(0);
    const [bearLogs, setBearLogs] = useState([]);
    const [foxLogs, setFoxLogs] = useState([]);
    const [bearTokenData, setBearTokenData] = useState([]);
    const [foxTokenData, setFoxTokenData] = useState([]);

    useEffect(() => {
        // 인더스트리곰 로그
        fetch(`${API}/ai-logs`)
            .then((r) => r.json())
            .then((data) => {
                setBearLogs(Array.isArray(data) ? data : []);
                setVisitorCount((prev) => prev + (Array.isArray(data) ? data.length : 0));
                let inp = 0, out = 0;
                data.forEach((l) => { inp += l.input_tokens || 0; out += l.output_tokens || 0; });
                setBearTokenData([{ name: "입력 토큰", value: inp }, { name: "출력 토큰", value: out }]);
            })
            .catch(() => { });

        // 모멘텀여우 로그
        fetch(`${API}/fox-logs`)
            .then((r) => r.json())
            .then((data) => {
                setFoxLogs(Array.isArray(data) ? data : []);
                let inp = 0, out = 0;
                data.forEach((l) => { inp += l.input_tokens || 0; out += l.output_tokens || 0; });
                setFoxTokenData([{ name: "입력 토큰", value: inp }, { name: "출력 토큰", value: out }]);
            })
            .catch(() => { });
    }, []);

    const isBear = activeAgent === "bear";
    const logs = isBear ? bearLogs : foxLogs;
    const tokenData = isBear ? bearTokenData : foxTokenData;

    return (
        <div className="min-h-screen bg-[#f5f7fb] p-12">

            {/* 헤더 */}
            <div className="mb-10">
                <h1 className="text-5xl font-black text-gray-800 mb-2">관리자 대시보드</h1>
                <p className="text-gray-400 text-lg">Botfolio AI 관리자 시스템</p>
            </div>

            {/* 방문자 + 토큰 요약 */}
            <div className="grid grid-cols-2 gap-8 mb-10">
                <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                    <p className="text-gray-400 mb-3 text-sm">전체 방문자 수</p>
                    <h2 className="text-6xl font-black text-blue-500">{visitorCount}</h2>
                </div>

                <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-black text-gray-800">토큰 사용량</h2>
                        <div className="flex gap-2">
                            {["bear", "fox"].map((a) => (
                                <button
                                    key={a}
                                    onClick={() => setActiveAgent(a)}
                                    className={`text-xs font-bold px-3 py-1.5 rounded-full transition ${activeAgent === a
                                            ? a === "bear" ? "bg-blue-500 text-white" : "bg-amber-400 text-white"
                                            : "bg-gray-100 text-gray-500"
                                        }`}
                                >
                                    {a === "bear" ? "🐻 인더스트리곰" : "🦊 모멘텀여우"}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="w-full h-[220px]">
                        <ResponsiveContainer>
                            <PieChart>
                                <Pie data={tokenData} cx="50%" cy="50%"
                                    innerRadius={60} outerRadius={90}
                                    paddingAngle={5} dataKey="value">
                                    {tokenData.map((_, idx) => (
                                        <Cell key={idx} fill={TOKEN_COLORS[idx]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="flex gap-6 justify-center mt-2">
                        <div className="flex items-center gap-2 text-sm">
                            <div className="w-3 h-3 bg-blue-500 rounded-full" /> 입력 토큰
                        </div>
                        <div className="flex items-center gap-2 text-sm">
                            <div className="w-3 h-3 bg-green-500 rounded-full" /> 출력 토큰
                        </div>
                    </div>
                </div>
            </div>

            {/* 에이전트 탭 */}
            <div className="flex gap-3 mb-8">
                {[
                    { key: "bear", label: "🐻 인더스트리곰", active: "bg-blue-500 text-white", inactive: "bg-white text-gray-500 border border-gray-100" },
                    { key: "fox", label: "🦊 모멘텀여우", active: "bg-amber-400 text-white", inactive: "bg-white text-gray-500 border border-gray-100" },
                ].map(({ key, label, active, inactive }) => (
                    <button
                        key={key}
                        onClick={() => setActiveAgent(key)}
                        className={`px-6 py-3 rounded-2xl font-bold text-sm shadow-sm transition ${activeAgent === key ? active : inactive}`}
                    >
                        {label}
                    </button>
                ))}
            </div>

            {/* 에이전트별 상세 */}
            <div className="grid grid-cols-3 gap-8">

                {/* 전략 파라미터 */}
                <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                    <h3 className="text-lg font-black text-gray-800 mb-4">
                        {isBear ? "⚙️ 전략 파라미터" : "⚡ 전략 파라미터"}
                    </h3>
                    <ParamTable
                        params={isBear ? BEAR_PARAMS : FOX_PARAMS}
                        accentBg={isBear ? "bg-blue-50" : "bg-amber-50"}
                        accentText={isBear ? "text-blue-700" : "text-amber-700"}
                        accentBorder={isBear ? "border-blue-100" : "border-amber-100"}
                    />
                </div>

                {/* ETF 유니버스 */}
                <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                    <h3 className="text-lg font-black text-gray-800 mb-4">📋 ETF 유니버스</h3>
                    <div className="flex flex-col gap-2 max-h-[400px] overflow-y-auto pr-1">
                        {Object.entries(isBear ? BEAR_ETF_NAMES : FOX_ETF_NAMES).map(([sym, name]) => {
                            const type = !isBear ? FOX_ETF_TYPE[sym] : null;
                            const ts = type ? TYPE_STYLE[type] : null;
                            return (
                                <div key={sym} className="flex items-center justify-between bg-gray-50 rounded-xl px-3 py-2 border border-gray-100">
                                    <div className="flex items-center gap-2">
                                        <span className="font-black text-gray-800 text-sm">{sym}</span>
                                        {ts && (
                                            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${ts.bg} ${ts.text}`}>
                                                {type}
                                            </span>
                                        )}
                                    </div>
                                    <span className="text-xs text-gray-400 text-right max-w-[140px] leading-tight">{name}</span>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* AI 로그 */}
                <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-black text-gray-800">🤖 AI 판단 로그</h3>
                        <span className="text-xs text-gray-400">최근 {logs.length}건</span>
                    </div>
                    <div className="max-h-[400px] overflow-y-auto pr-1">
                        <LogList logs={logs} type={isBear ? "bear" : "fox"} />
                    </div>
                </div>
            </div>
        </div>
    );
}
