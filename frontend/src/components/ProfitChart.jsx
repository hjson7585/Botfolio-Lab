import { useEffect, useState, useMemo } from "react";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";

const API = "http://localhost:8000";

const INITIAL_CAPITAL = 10_000;

const PERIOD_OPTIONS = [
    { key: "daily", label: "일별" },
    { key: "weekly", label: "주별" },
    { key: "monthly", label: "월별" },
    { key: "yearly", label: "연별" },
];

const AGENT_COLOR = {
    bear: "#3B82F6",
    fox: "#F59E0B",
    turtle: "#10B981",
};

function CustomTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    const isPositive = d.profit_rate >= 0;
    return (
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 px-4 py-3 text-sm">
            <p className="text-gray-400 mb-1">{label}</p>
            <p className={`text-xl font-black ${isPositive ? "text-blue-500" : "text-red-500"}`}>
                {isPositive ? "+" : ""}{d.profit_rate}%
            </p>
            <p className="text-gray-500 mt-0.5">
                총 자산:{" "}
                <span className="font-bold text-gray-700">
                    ${d.total_asset?.toLocaleString()}
                </span>
            </p>
        </div>
    );
}

// ✅ liveAsset, liveRate: 각 에이전트 페이지에서 실시간으로 전달받는 값
export default function ProfitChart({ agent, liveAsset, liveRate }) {
    const [data, setData] = useState(null);
    const [period, setPeriod] = useState("daily");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);

    const color = AGENT_COLOR[agent] || "#6b7280";

    useEffect(() => {
        setLoading(true);
        setError(false);
        fetch(`${API}/profit-history/${agent}`)
            .then((r) => r.json())
            .then((d) => { setData(d); setLoading(false); })
            .catch(() => { setError(true); setLoading(false); });
    }, [agent]);

    const chartData = useMemo(() => data?.[period] || [], [data, period]);

    const { minRate, maxRate } = useMemo(() => {
        if (!chartData.length) return { minRate: -10, maxRate: 10 };
        const rates = chartData.map((d) => d.profit_rate);
        const min = Math.min(...rates);
        const max = Math.max(...rates);
        const pad = Math.max(Math.abs(max - min) * 0.15, 2);
        return { minRate: Math.floor(min - pad), maxRate: Math.ceil(max + pad) };
    }, [chartData]);

    // ✅ 카드 수치는 props로 받은 실시간 값 우선 사용 (없으면 차트 최신값 fallback)
    const displayRate = liveRate ?? chartData.at(-1)?.profit_rate ?? 0;
    const displayAsset = liveAsset ?? chartData.at(-1)?.total_asset ?? INITIAL_CAPITAL;
    const isPositive = displayRate >= 0;
    // ✅ 손익 = 실시간 총자산 - 초기자본 $10,000
    const pnl = displayAsset - INITIAL_CAPITAL;

    return (
        <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 mb-8">

            {/* 헤더 */}
            <div className="flex items-start justify-between mb-6">
                <div>
                    <h2 className="text-xl font-black text-gray-800">📈 실시간 수익률 추이</h2>
                    <p className="text-xs text-gray-400 mt-0.5">초기 자본 $10,000 기준</p>
                </div>
                <div className="flex gap-2">
                    {PERIOD_OPTIONS.map(({ key, label }) => (
                        <button
                            key={key}
                            onClick={() => setPeriod(key)}
                            className={`text-xs font-bold px-4 py-2 rounded-full transition
                                ${period === key
                                    ? "text-white"
                                    : "bg-gray-100 text-gray-400 hover:bg-gray-200"
                                }`}
                            style={period === key ? { background: color } : {}}
                        >
                            {label}
                        </button>
                    ))}
                </div>
            </div>

            {/* 요약 수치 카드 — 사이드바와 동일한 실시간 값 표시 */}
            <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-50 rounded-2xl px-5 py-4 border border-gray-100">
                    <p className="text-xs text-gray-400 mb-1">현재 수익률</p>
                    <p className={`text-3xl font-black ${isPositive ? "text-blue-500" : "text-red-500"}`}>
                        {isPositive ? "+" : ""}{Number(displayRate).toFixed(2)}%
                    </p>
                </div>
                <div className="bg-gray-50 rounded-2xl px-5 py-4 border border-gray-100">
                    <p className="text-xs text-gray-400 mb-1">현재 총 자산</p>
                    <p className="text-3xl font-black text-gray-800">
                        ${Number(displayAsset).toLocaleString()}
                    </p>
                </div>
                <div className="bg-gray-50 rounded-2xl px-5 py-4 border border-gray-100">
                    <p className="text-xs text-gray-400 mb-1">손익</p>
                    {/* ✅ 실시간 총자산 - $10,000 */}
                    <p className={`text-3xl font-black ${pnl >= 0 ? "text-emerald-500" : "text-red-500"}`}>
                        {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
                    </p>
                </div>
            </div>

            {/* 차트 */}
            {loading ? (
                <div className="flex items-center justify-center h-48 text-gray-300 text-sm">
                    불러오는 중...
                </div>
            ) : error ? (
                <div className="flex items-center justify-center h-48 text-gray-300 text-sm">
                    데이터를 불러올 수 없습니다
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={260}>
                    <LineChart
                        data={
                            chartData.length >= 2
                                ? chartData
                                : [
                                    { date: "시작", profit_rate: 0, total_asset: INITIAL_CAPITAL },
                                    { date: "현재", profit_rate: displayRate, total_asset: displayAsset },
                                ]
                        }
                        margin={{ top: 8, right: 16, left: 0, bottom: 0 }}
                    >
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis
                            dataKey="date"
                            tick={{ fontSize: 11, fill: "#9ca3af" }}
                            tickLine={false}
                            axisLine={false}
                        />
                        <YAxis
                            domain={[minRate, maxRate]}
                            tick={{ fontSize: 11, fill: "#9ca3af" }}
                            tickLine={false}
                            axisLine={false}
                            width={48}
                            tickFormatter={(v) => `${v}%`}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <ReferenceLine y={0} stroke="#e5e7eb" strokeWidth={1.5} strokeDasharray="4 3" />
                        <Line
                            type="monotone"
                            dataKey="profit_rate"
                            name="수익률"
                            stroke={color}
                            strokeWidth={2.5}
                            dot={{ r: 3, fill: color, strokeWidth: 0 }}
                            activeDot={{ r: 6, fill: color, strokeWidth: 0 }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            )}
        </div>
    );
}
