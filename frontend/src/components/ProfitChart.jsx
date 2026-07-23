import { useEffect, useState, useMemo, useRef } from "react";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
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

// ── 수익률 색상 (양수=빨간 / 음수=파란 / 0=검은) ──────────
function rateColor(v) {
    const n = Number(v);
    if (v == null || isNaN(n) || n === 0) return "text-gray-900";
    return n > 0 ? "text-red-500" : "text-blue-500";
}

// ── 수익률 포맷 (양수=+X.XX% / 음수=-X.XX% / 0=0.00%) ──────
function fmtRate(v) {
    const n = Number(v);
    if (v == null || isNaN(n)) return "-";
    if (n > 0) return `+${n.toFixed(2)}%`;
    if (n < 0) return `${n.toFixed(2)}%`;
    return "0.00%";
}

function CustomTooltip({ active, payload, label }) {
    if (!active || !payload?.length) return null;
    const d = payload[0].payload;
    return (
        <div className="bg-white rounded-2xl shadow-lg border border-gray-100 px-4 py-3 text-sm">
            <p className="text-gray-400 mb-1">{label}</p>
            <p className={`text-xl font-black ${rateColor(d.profit_rate)}`}>
                {fmtRate(d.profit_rate)}
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

export default function ProfitChart({ agent, liveAsset, liveRate }) {
    const [data, setData] = useState(null);
    const [period, setPeriod] = useState("daily");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(false);
    const [mousePos, setMousePos] = useState(null);
    const chartWrapRef = useRef(null);

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

    const displayRate = liveRate ?? chartData.at(-1)?.profit_rate ?? 0;
    const displayAsset = liveAsset ?? chartData.at(-1)?.total_asset ?? INITIAL_CAPITAL;

    const handleChartMouseMove = (e) => {
        if (!chartWrapRef.current || !e) return;
        const rect = chartWrapRef.current.getBoundingClientRect();
        const clientX = e.activeCoordinate?.x != null ? rect.left + e.activeCoordinate.x : null;
        const clientY = e.chartY != null ? rect.top + e.chartY : null;
        if (clientX == null || clientY == null) return;
        setMousePos({ x: clientX - rect.left, y: clientY - rect.top });
    };

    const handleChartMouseLeave = () => {
        setMousePos(null);
    };

    return (
        <div className="bg-white rounded-3xl p-8 shadow-sm border border-gray-100 mb-8">

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

            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-gray-50 rounded-2xl px-5 py-4 border border-gray-100">
                    <p className="text-xs text-gray-400 mb-1">현재 수익률</p>
                    {/* 양수=+빨간 / 음수=−파란 / 0=검은 */}
                    <p className={`text-3xl font-black ${rateColor(displayRate)}`}>
                        {fmtRate(displayRate)}
                    </p>
                </div>
                <div className="bg-gray-50 rounded-2xl px-5 py-4 border border-gray-100">
                    <p className="text-xs text-gray-400 mb-1">현재 총 자산</p>
                    <p className="text-3xl font-black text-gray-800">
                        ${Number(displayAsset).toLocaleString()}
                    </p>
                </div>
            </div>

            {loading ? (
                <div className="flex items-center justify-center h-48 text-gray-300 text-sm">
                    불러오는 중...
                </div>
            ) : error ? (
                <div className="flex items-center justify-center h-48 text-gray-300 text-sm">
                    데이터를 불러올 수 없습니다
                </div>
            ) : (
                <div ref={chartWrapRef} style={{ width: "100%", height: 260, minWidth: 0, position: "relative" }}>
                    <ResponsiveContainer width="100%" height="100%" debounce={1}>
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
                            onMouseMove={handleChartMouseMove}
                            onMouseLeave={handleChartMouseLeave}
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
                            <Tooltip
                                content={<CustomTooltip />}
                                position={mousePos ? { x: mousePos.x + 16, y: mousePos.y - 12 } : undefined}
                                cursor={{ stroke: "#e5e7eb", strokeWidth: 1 }}
                            />
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
                </div>
            )}
        </div>
    );
}
