import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AgentCard from "../components/AgentCard";

const API = "http://localhost:8000";
const REFRESH_MS = 2000;

const AGENT_CONFIGS = [
    {
        id: 1,
        name: "인더스트리곰",
        character: "🐻",
        market: "미국 섹터 ETF",
        style: "중장기 섹터 추세 추종",
        strategy: "모멘텀·뉴스 감성 스코어로 ETF 선별",
        path: "/agent/industry-bear",
        endpoint: "/portfolio",
    },
    {
        id: 2,
        name: "모멘텀여우",
        character: "🦊",
        market: "미국 대형주·나스닥 ETF",
        style: "중단기 추세 추종",
        strategy: "시장 레짐을 판단해 상승 모멘텀 강한 ETF 매수",
        path: "/momentum-fox",
        endpoint: "/fox-portfolio",
    },
    {
        id: 3,
        name: "배당거북",
        character: "🐢",
        market: "미국 고배당·배당성장 ETF",
        style: "장기 인컴",
        strategy: "배당수익률·배당성장률 기반으로 우량 ETF를 장기 보유",
        path: "/agent/dividend-turtle",
        endpoint: "/turtle-portfolio",
    },
];

function Home({ user, login, logout }) {
    const navigate = useNavigate();
    const ADMIN_EMAIL = "hjson7585@gmail.com";
    const isAdmin = user?.email === ADMIN_EMAIL;

    // 에이전트별 실시간 수익률 상태
    const [profitMap, setProfitMap] = useState({
        "/portfolio": null,
        "/fox-portfolio": null,
        "/turtle-portfolio": null,
    });

    useEffect(() => {
        const fetchAll = () => {
            AGENT_CONFIGS.forEach(({ endpoint }) => {
                fetch(`${API}${endpoint}`)
                    .then((r) => r.json())
                    .then((d) => {
                        setProfitMap((prev) => ({
                            ...prev,
                            [endpoint]: d.profit_rate ?? null,
                        }));
                    })
                    .catch(() => { });
            });
        };

        fetchAll();
        const timer = setInterval(fetchAll, REFRESH_MS);
        return () => clearInterval(timer);
    }, []);

    const agents = AGENT_CONFIGS.map((cfg) => ({
        ...cfg,
        profit: profitMap[cfg.endpoint],
    }));

    return (
        <div className="min-h-screen bg-[#f5f7fb]">

            {/* 헤더 */}
            <div className="px-12 pt-10 pb-8">
                <div className="flex justify-between items-start">

                    {/* 타이틀 */}
                    <div>
                        <h1 className="text-5xl font-black tracking-tight text-gray-800">
                            Botfolio Lab
                        </h1>
                        <p className="text-gray-500 mt-3 text-lg">
                            AI 투자 에이전트 연구소
                        </p>
                    </div>

                    {/* 로그인 영역 */}
                    <div>
                        {!user ? (
                            <button
                                onClick={login}
                                className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-2xl font-semibold transition"
                            >
                                Google 로그인
                            </button>
                        ) : (
                            <div className="bg-white border border-gray-100 rounded-3xl shadow-sm px-5 py-4 flex items-center gap-4">
                                <div>
                                    <p className="text-sm text-gray-500">로그인됨</p>
                                    <p className="font-semibold text-gray-800">{user.email}</p>
                                </div>
                                {isAdmin && (
                                    <button
                                        onClick={() => navigate("/admin")}
                                        className="bg-blue-100 hover:bg-blue-200 text-blue-700 px-4 py-2 rounded-xl font-semibold transition"
                                    >
                                        관리자 대시보드
                                    </button>
                                )}
                                <button
                                    onClick={logout}
                                    className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-xl transition"
                                >
                                    로그아웃
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* AI Agent 카드 */}
            <div className="px-12 pb-12">
                <div className="flex flex-wrap gap-8">
                    {agents.map((agent) => (
                        <AgentCard key={agent.id} agent={agent} />
                    ))}
                </div>
            </div>
        </div>
    );
}

export default Home;
