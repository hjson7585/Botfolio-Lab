import { useNavigate } from "react-router-dom";


function AgentCard({ agent }) {
    const navigate = useNavigate();
    if (!agent) return null;

    const formatted = fmtProfit(agent.profit);
    const isLoading = agent.profit === null || agent.profit === undefined;

    return (
        <div
            onClick={() => navigate(agent.path || `/agent/${agent.id}`)}
            className="w-[320px] bg-white rounded-3xl p-8 shadow-sm border border-gray-100 cursor-pointer hover:shadow-xl hover:-translate-y-1 transition"
        >
            <div className="text-6xl mb-5">{agent.character || "🤖"}</div>

            <h2 className="text-2xl font-black text-gray-800 mb-3">
                {agent.name || "이름 없음"}
            </h2>

            {/* 수익률 */}
            <div className="mb-5 flex items-center gap-2">
                {isLoading ? (
                    <div className="h-9 w-28 rounded-xl bg-gray-100 animate-pulse" />
                ) : (
                    <>
                        <p className={`text-3xl font-black ${profitColor(agent.profit)}`}>
                            {formatted}
                        </p>
                        <span className="flex items-center gap-1 text-xs font-bold text-gray-300 bg-gray-50 px-2 py-1 rounded-full border border-gray-100">
                            <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                            실시간
                        </span>
                    </>
                )}
            </div>

            <div className="space-y-2">
                <p className="text-gray-600"><span className="font-bold">시장</span>: {agent.market || "-"}</p>
                <p className="text-gray-600"><span className="font-bold">투자 스타일</span>: {agent.style || "-"}</p>
                <p className="text-gray-600"><span className="font-bold">전략</span>: {agent.strategy || "-"}</p>
            </div>
        </div>
    );
}

function profitColor(v) {
    const n = Number(v);
    if (v == null || isNaN(n) || n === 0) return "text-gray-900";
    return n > 0 ? "text-red-500" : "text-blue-500";
}
function fmtProfit(v) {
    if (v == null || v === "") return "-";
    const n = Number(v);
    return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

export default AgentCard;
