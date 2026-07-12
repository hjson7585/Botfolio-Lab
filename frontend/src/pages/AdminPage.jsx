import { useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";

const AGENTS = [
    { key: "bear", label: "🐻 인더스트리곰", color: "#3B82F6" },
    { key: "fox", label: "🦊 모멘텀여우", color: "#F59E0B" },
    { key: "turtle", label: "🐢 배당거북", color: "#10B981", disabled: true },
];

function AgentCard({ agent }) {
    const [runStatus, setRunStatus] = useState(null);
    const [logStatus, setLogStatus] = useState(null);
    const [running, setRunning] = useState(false);
    const [deleting, setDeleting] = useState(false);

    const handleRun = async () => {
        if (!confirm(`${agent.label} 에이전트를 지금 바로 실행할까요?`)) return;
        setRunning(true); setRunStatus(null);
        try {
            const res = await fetch(`${API}/admin/run/${agent.key}`, { method: "POST" });
            const data = await res.json();
            setRunStatus(res.ok ? { ok: true, msg: data.message } : { ok: false, msg: data.detail });
        } catch {
            setRunStatus({ ok: false, msg: "네트워크 오류" });
        } finally { setRunning(false); }
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

                {/* 실행 버튼 */}
                <button
                    onClick={handleRun}
                    disabled={running || agent.disabled}
                    className="w-full py-3 rounded-2xl text-sm font-bold text-white transition disabled:opacity-40"
                    style={{ background: agent.color }}
                >
                    {running ? "실행 중..." : "▶ 지금 실행"}
                </button>
                {runStatus && (
                    <p className={`text-xs font-semibold ${runStatus.ok ? "text-green-500" : "text-red-500"}`}>
                        {runStatus.ok ? "✅ " : "❌ "}{runStatus.msg}
                    </p>
                )}

                {/* 로그 삭제 버튼 */}
                <button
                    onClick={handleClearLog}
                    disabled={deleting}
                    className="w-full py-3 rounded-2xl text-sm font-bold text-red-500 border border-red-200 bg-red-50 hover:bg-red-100 transition disabled:opacity-40"
                >
                    {deleting ? "삭제 중..." : "🗑 로그 삭제"}
                </button>
                {logStatus && (
                    <p className={`text-xs font-semibold ${logStatus.ok ? "text-green-500" : "text-red-500"}`}>
                        {logStatus.ok ? "✅ " : "❌ "}{logStatus.msg}
                    </p>
                )}

            </div>
            {agent.disabled && (
                <p className="text-xs text-gray-400 mt-3">※ 미구현 에이전트</p>
            )}
        </div>
    );
}

export default function AdminPage() {
    return (
        <div className="min-h-screen bg-gray-50 p-8">
            <div className="max-w-3xl mx-auto">
                <h1 className="text-3xl font-black text-gray-800 mb-2">⚙️ 관리자 대시보드</h1>
                <p className="text-sm text-gray-400 mb-8">에이전트 수동 실행 및 로그 관리</p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {AGENTS.map(a => <AgentCard key={a.key} agent={a} />)}
                </div>
            </div>
        </div>
    );
}
