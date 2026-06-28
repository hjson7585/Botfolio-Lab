import { useNavigate }
    from "react-router-dom";

import AgentCard
    from "../components/AgentCard";


function Home({

    user,

    login,

    logout

}) {

    const navigate = useNavigate();

    const ADMIN_EMAIL =
        "hjson7585@gmail.com";

    const isAdmin =

        user?.email === ADMIN_EMAIL;

    // AI 에이전트 데이터
    const agents = [

        {
            id: 1,
            name: "인더스트리곰",
            character: "🐻",
            profit: "+12.4%",
            market: "미국 산업 ETF",
            style: "장기 투자",
            strategy: "산업 사이클 분석"
        },

        {
            id: 2,
            name: "모멘텀여우",
            character: "🦊",
            profit: "+7.1%",
            market: "미국 기술 성장주",
            style: "공격형 투자",
            strategy: "모멘텀 전략"
        },

        {
            id: 3,
            name: "배당거북",
            character: "🐢",
            profit: "+5.3%",
            market: "고배당 ETF",
            style: "안정형 투자",
            strategy: "배당 복리 전략"
        }
    ];

    return (

        <div className="min-h-screen bg-[#f5f7fb]">

            {/* 헤더 */}
            <div className="px-12 pt-10 pb-8">

                <div
                    className="
                        flex
                        justify-between
                        items-start
                    "
                >

                    {/* 타이틀 */}
                    <div>

                        <h1
                            className="
                                text-5xl
                                font-black
                                tracking-tight
                                text-gray-800
                            "
                        >
                            Botfolio Lab
                        </h1>

                        <p
                            className="
                                text-gray-500
                                mt-3
                                text-lg
                            "
                        >
                            AI 투자 에이전트 연구소
                        </p>

                    </div>

                    {/* 로그인 영역 */}
                    <div>

                        {!user ? (

                            <button

                                onClick={login}

                                className="
                                    bg-blue-500
                                    hover:bg-blue-600
                                    text-white
                                    px-6
                                    py-3
                                    rounded-2xl
                                    font-semibold
                                    transition
                                "
                            >

                                Google 로그인

                            </button>

                        ) : (

                            <div
                                className="
                                    bg-white
                                    border
                                    border-gray-100
                                    rounded-3xl
                                    shadow-sm
                                    px-5
                                    py-4
                                    flex
                                    items-center
                                    gap-4
                                "
                            >

                                {/* 사용자 정보 */}
                                <div>

                                    <p
                                        className="
                                            text-sm
                                            text-gray-500
                                        "
                                    >
                                        로그인됨
                                    </p>

                                    <p
                                        className="
                                            font-semibold
                                            text-gray-800
                                        "
                                    >
                                        {user.email}
                                    </p>

                                </div>

                                {/* 관리자 버튼 */}
                                {isAdmin && (

                                    <button

                                        onClick={() => {

                                            navigate("/admin");
                                        }}

                                        className="
                                            bg-blue-100
                                            hover:bg-blue-200
                                            text-blue-700
                                            px-4
                                            py-2
                                            rounded-xl
                                            font-semibold
                                            transition
                                        "
                                    >

                                        관리자 대시보드

                                    </button>
                                )}

                                {/* 로그아웃 */}
                                <button

                                    onClick={logout}

                                    className="
                                        bg-red-500
                                        hover:bg-red-600
                                        text-white
                                        px-4
                                        py-2
                                        rounded-xl
                                        transition
                                    "
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

                <div
                    className="
                        flex
                        flex-wrap
                        gap-8
                    "
                >

                    {agents.map((agent) => (

                        <AgentCard

                            key={agent.id}

                            agent={agent}
                        />

                    ))}

                </div>

            </div>

        </div>
    );
}

export default Home;
