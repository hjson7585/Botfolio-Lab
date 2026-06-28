import { useNavigate }
    from "react-router-dom";


function AgentCard({ agent }) {

    const navigate = useNavigate();

    if (!agent) {

        return null;
    }

    return (

        <div

            onClick={() => {

                navigate(

                    `/agent/${agent.id}`
                );
            }}

            className="
                w-[320px]
                bg-white
                rounded-3xl
                p-8
                shadow-sm
                border
                border-gray-100
                cursor-pointer
                hover:shadow-xl
                hover:-translate-y-1
                transition
            "
        >

            {/* 캐릭터 */}
            <div className="text-6xl mb-5">

                {agent.character || "🤖"}

            </div>

            {/* 이름 */}
            <h2
                className="
                    text-2xl
                    font-black
                    text-gray-800
                    mb-3
                "
            >

                {agent.name || "이름 없음"}

            </h2>

            {/* 수익률 */}
            <p
                className="
                    text-green-500
                    text-3xl
                    font-black
                    mb-5
                "
            >

                {agent.profit || "0%"}

            </p>

            {/* 정보 */}
            <div className="space-y-2">

                <p className="text-gray-600">

                    시장:
                    {" "}

                    {agent.market || "-"}

                </p>

                <p className="text-gray-600">

                    투자 스타일:
                    {" "}

                    {agent.style || "-"}

                </p>

                <p className="text-gray-600">

                    전략:
                    {" "}

                    {agent.strategy || "-"}

                </p>

            </div>

        </div>
    );
}

export default AgentCard;
