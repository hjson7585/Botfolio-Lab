import { useNavigate } from "react-router-dom";
import AgentCard from "../components/AgentCard";
import { usePortfolio } from "../context/PortfolioContext";

const AGENT_CONFIGS = [
    {
        id: 1,
        name: "인더스트리곰",
        character: "🐻",
        market: "미국 섹터 ETF",
        style: "중장기 섹터 추세 추종",
        strategy: "모멘텀·뉴스 감성 스코어로 ETF 선별",
        path: "/agent/industry-bear",
        key: "bearData",
    },
    {
        id: 2,
        name: "모멘텀여우",
        character: "🦊",
        market: "미국 대형주·나스닥 ETF",
        style: "중단기 추세 추종",
        strategy: "시장 레짐을 판단해 상승 모멘텀 강한 ETF 매수",
        path: "/momentum-fox",
        key: "foxData",
    },
    {
        id: 3,
        name: "배당거북",
        character: "🐢",
        market: "미국 고배당·배당성장 ETF",
        style: "장기 인컴",
        strategy: "배당수익률·배당성장률 기반으로 우량 ETF를 장기 보유",
        path: "/agent/dividend-turtle",
        key: "turtleData",
    },
];

function Home({ user, login, logout }) {
    const navigate = useNavigate();
    const ADMIN_EMAIL = "hjson7585@gmail.com";
    const isAdmin = user?.email === ADMIN_EMAIL;

    const portfolioCtx = usePortfolio();

    const agents = AGENT_CONFIGS.map((cfg) => {
        const data = portfolioCtx?.[cfg.key];
        return {
            ...cfg,
            profit: data?.profit_rate ?? null,
        };
    });

    return (
        <div className="min-h-screen bg-[#f5f7fb]">

            {/* 헤더 */}
            <div className="px-5 sm:px-8 md:px-12 pt-8 pb-6 md:pt-10 md:pb-8">
                <div className="flex flex-col gap-4 sm:flex-row sm:justify-between sm:items-start">

                    {/* 타이틀 */}
                    <div>
                        <h1 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight text-gray-800">
                            Botfolio Lab
                        </h1>
                        <p className="text-gray-500 mt-2 text-base md:text-lg">
                            AI 투자 에이전트 연구소
                        </p>
                    </div>

                    {/* 로그인 영역 */}
                    <div className="self-start">
                        {!user ? (
                            <button
                                onClick={login}
                                className="bg-blue-500 hover:bg-blue-600 text-white px-5 py-2.5 md:px-6 md:py-3 rounded-2xl font-semibold transition text-sm md:text-base"
                            >
                                Google 로그인
                            </button>
                        ) : (
                            <div className="bg-white border border-gray-100 rounded-3xl shadow-sm px-4 py-3 md:px-5 md:py-4 flex flex-wrap items-center gap-3">
                                <div>
                                    <p className="text-xs md:text-sm text-gray-500">로그인됨</p>
                                    <p className="font-semibold text-gray-800 text-sm md:text-base">{user.email}</p>
                                </div>
                                {isAdmin && (
                                    <button
                                        onClick={() => navigate("/admin")}
                                        className="bg-blue-100 hover:bg-blue-200 text-blue-700 px-3 py-1.5 md:px-4 md:py-2 rounded-xl font-semibold transition text-sm"
                                    >
                                        관리자 대시보드
                                    </button>
                                )}
                                <button
                                    onClick={logout}
                                    className="bg-red-500 hover:bg-red-600 text-white px-3 py-1.5 md:px-4 md:py-2 rounded-xl transition text-sm"
                                >
                                    로그아웃
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* AI Agent 카드 */}
            <div className="px-5 sm:px-8 md:px-12 pb-12">
                <div className="flex flex-col sm:flex-row sm:flex-wrap gap-6 md:gap-8">
                    {agents.map((agent) => (
                        <AgentCard key={agent.id} agent={agent} />
                    ))}
                </div>
            </div>
        </div>
    );
}

export default Home;
