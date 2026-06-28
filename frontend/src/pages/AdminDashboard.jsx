import { useEffect, useState } from "react";

import {
    PieChart,
    Pie,
    Cell,
    Tooltip,
    ResponsiveContainer
} from "recharts";


function AdminDashboard() {

    const [visitorCount, setVisitorCount] = useState(0);
    const [logs, setLogs] = useState([]);
    const [tokenData, setTokenData] = useState([]);

    const COLORS = ["#3B82F6", "#10B981"];

    useEffect(() => {

        const fetchData = async () => {

            try {

                const res = await fetch("http://localhost:8000/ai-logs");

                const data = await res.json();

                setVisitorCount(data.length);
                setLogs(data);

                // ✅ 실제 토큰 합산
                let totalInput = 0;
                let totalOutput = 0;

                data.forEach(log => {

                    totalInput += log.input_tokens || 0;
                    totalOutput += log.output_tokens || 0;

                });

                setTokenData([
                    {
                        name: "입력 토큰",
                        value: totalInput
                    },
                    {
                        name: "출력 토큰",
                        value: totalOutput
                    }
                ]);

            } catch (error) {

                console.log(error);

            }
        };

        fetchData();

    }, []);

    return (

        <div className="min-h-screen bg-[#f5f7fb] p-12">

            {/* 제목 */}
            <div className="mb-10">

                <h1 className="text-5xl font-black text-gray-800 mb-4">
                    관리자 대시보드
                </h1>

                <p className="text-gray-500 text-lg">
                    Botfolio AI 관리자 시스템
                </p>

            </div>

            {/* 상단 카드 */}
            <div className="grid grid-cols-2 gap-8 mb-10">

                {/* 방문자 */}
                <div className="bg-white rounded-3xl p-8 shadow-sm border">

                    <p className="text-gray-500 mb-3">
                        전체 방문자 수
                    </p>

                    <h2 className="text-6xl font-black text-blue-500">
                        {visitorCount}
                    </h2>

                </div>

                {/* ✅ 토큰 차트 */}
                <div className="bg-white rounded-3xl p-8 shadow-sm border">

                    <h2 className="text-2xl font-black mb-6">
                        Gemini Flash 토큰 사용량
                    </h2>

                    <div className="w-full h-[300px]">

                        <ResponsiveContainer>

                            <PieChart>

                                <Pie
                                    data={tokenData}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={70}
                                    outerRadius={110}
                                    paddingAngle={5}
                                    dataKey="value"
                                >

                                    {tokenData.map((entry, index) => (
                                        <Cell
                                            key={index}
                                            fill={COLORS[index]}
                                        />
                                    ))}

                                </Pie>

                                <Tooltip />

                            </PieChart>

                        </ResponsiveContainer>

                    </div>

                    {/* 범례 */}
                    <div className="flex gap-6 justify-center mt-4">

                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 bg-blue-500 rounded-full" />
                            입력 토큰
                        </div>

                        <div className="flex items-center gap-2">
                            <div className="w-4 h-4 bg-green-500 rounded-full" />
                            출력 토큰
                        </div>

                    </div>

                </div>

            </div>

            {/* AI 로그 */}
            <div className="bg-white rounded-3xl p-8 shadow-sm border">

                <h2 className="text-2xl font-black mb-6">
                    최근 AI 판단 로그
                </h2>

                <div className="space-y-4">

                    {logs.map((log, index) => (

                        <div
                            key={index}
                            className="border rounded-2xl p-4"
                        >

                            <p className="font-bold">
                                {log.agent}
                            </p>

                            <p className="text-gray-600">
                                판단: {log.action}
                            </p>

                            <p className="text-gray-500 text-sm">
                                {log.reason}
                            </p>

                            {/* ✅ 추가된 정보 */}
                            <p className="text-xs text-gray-400 mt-1">
                                model: {log.model}
                            </p>

                            <p className="text-xs text-gray-400">
                                input: {log.input_tokens} / output: {log.output_tokens}
                            </p>

                        </div>

                    ))}

                </div>

            </div>

        </div>
    );
}

export default AdminDashboard;
