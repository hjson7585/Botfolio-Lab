function AgentCard({ agent }) {
    const [runStatus, setRunStatus] = useState(null);
    const [rebalStatus, setRebalStatus] = useState(null);
    const [logStatus, setLogStatus] = useState(null);
    const [running, setRunning] = useState(false);
    const [rebalancing, setRebalancing] = useState(false);
    const [deleting, setDeleting] = useState(false);

    const handleRun = async () => {
        if (!confirm(`${agent.label} 매일 실행 (손절/익절 + 매매 조건 확인)?`)) return;
        setRunning(true); setRunStatus(null);
        try {
            const res = await fetch(`${API}/admin/run/${agent.key}`, { method: "POST" });
            const data = await res.json();
            setRunStatus(res.ok ? { ok: true, msg: data.message } : { ok: false, msg: data.detail });
        } catch {
            setRunStatus({ ok: false, msg: "네트워크 오류" });
        } finally { setRunning(false); }
    };

    const handleRebalance = async (force = false) => {
        const label = force ? "리밸런싱 강제 실행 (주기 무시)" : "리밸런싱 실행 (25일 주기 적용)";
        if (!confirm(`🐻 ${label}?`)) return;
        setRebalancing(true); setRebalStatus(null);
        const url = force
            ? `${API}/admin/run/bear/rebalance/force`
            : `${API}/admin/run/bear/rebalance`;
        try {
            const res = await fetch(url, { method: "POST" });
            const data = await res.json();
            setRebalStatus(res.ok ? { ok: true, msg: data.message } : { ok: false, msg: data.detail });
        } catch {
            setRebalStatus({ ok: false, msg: "네트워크 오류" });
        } finally { setRebalancing(false); }
    };

    const handleClearLog = async () => {
        if (!confirm(`${agent.label} 로그를 전부 삭제할까요?`)) return;
        setDeleting(true); setLogStatus(null);
        try {
            const res = await fetch(`${API}/admin/logs/${agent.key}`, { method: "DELETE" });
            const data = await res.json();
            setLogStatus(res.ok ? { ok: true, msg: data.message } : { ok: false, msg: data.detail });
        } catch {
            setLogStatus({ ok: false, msg: "네트워크 오류" });
        } finally { setDeleting(false); }
    };

    return (
        <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-black text-gray-800 mb-4">{agent.label}</h3>
            <div className="flex flex-col gap-3">

                {/* 매일 실행 */}
                <button
                    onClick={handleRun}
                    disabled={running || agent.disabled}
                    className="w-full py-3 rounded-2xl text-sm font-bold text-white transition disabled:opacity-40"
                    style={{ background: agent.color }}
                >
                    {running ? "실행 중..." : "▶ 매일 실행 (손절/익절 + 매매)"}
                </button>
                {runStatus && (
                    <p className={`text-xs font-semibold ${runStatus.ok ? "text-green-500" : "text-red-500"}`}>
                        {runStatus.ok ? "✅ " : "❌ "}{runStatus.msg}
                    </p>
                )}

                {/* 🐻 리밸런싱 버튼 (인더스트리곰 전용) */}
                {agent.key === "bear" && (
                    <>
                        <button
                            onClick={() => handleRebalance(false)}
                            disabled={rebalancing}
                            className="w-full py-3 rounded-2xl text-sm font-bold text-orange-600 border border-orange-200 bg-orange-50 hover:bg-orange-100 transition disabled:opacity-40"
                        >
                            {rebalancing ? "리밸런싱 중..." : "🔄 리밸런싱 (25일 주기)"}
                        </button>
                        <button
                            onClick={() => handleRebalance(true)}
                            disabled={rebalancing}
                            className="w-full py-3 rounded-2xl text-sm font-bold text-red-600 border border-red-200 bg-red-50 hover:bg-red-100 transition disabled:opacity-40"
                        >
                            {rebalancing ? "리밸런싱 중..." : "⚡ 리밸런싱 강제 실행"}
                        </button>
                        {rebalStatus && (
                            <p className={`text-xs font-semibold ${rebalStatus.ok ? "text-green-500" : "text-red-500"}`}>
                                {rebalStatus.ok ? "✅ " : "❌ "}{rebalStatus.msg}
                            </p>
                        )}
                    </>
                )}

                {/* 로그 삭제 */}
                <button
                    onClick={handleClearLog}
                    disabled={deleting}
                    className="w-full py-3 rounded-2xl text-sm font-bold text-gray-500 border border-gray-200 bg-gray-50 hover:bg-gray-100 transition disabled:opacity-40"
                >
                    {deleting ? "삭제 중..." : "🗑 로그 삭제"}
                </button>
                {logStatus && (
                    <p className={`text-xs font-semibold ${logStatus.ok ? "text-green-500" : "text-red-500"}`}>
                        {logStatus.ok ? "✅ " : "❌ "}{logStatus.msg}
                    </p>
                )}
            </div>
            {agent.disabled && <p className="text-xs text-gray-400 mt-3">※ 미구현 에이전트</p>}
        </div>
    );
}
