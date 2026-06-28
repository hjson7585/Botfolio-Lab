// 구글 로그인 버튼 컴포넌트 import
import { GoogleLogin } from "@react-oauth/google";

// HTTP 요청을 보내기 위한 axios import
import axios from "axios";


function LoginButton() {

    // 구글 로그인 성공 시 실행되는 함수
    const handleSuccess = async (credentialResponse) => {

        try {
            // 구글이 전달한 credential 토큰 꺼내기
            const token = credentialResponse.credential;

            // 백엔드 서버로 토큰 전송
            // 백엔드에서 토큰 검증 후 자체 access_token과 email 반환
            const response = await axios.post(
                "http://127.0.0.1:8000/auth/google",
                {
                    token: token
                }
            );

            // 서버 응답 확인
            console.log(response.data);

            // 서버가 발급한 access_token 저장
            localStorage.setItem(
                "access_token",
                response.data.access_token
            );

            // 로그인한 사용자 이메일 저장
            localStorage.setItem(
                "is_admin",
                response.data.is_admin
            );

            // 로그인 상태 반영을 위해 새로고침
            window.location.reload();

        } catch (error) {
            // 로그인 처리 중 에러 발생 시 콘솔 출력
            console.log(error);
        }
    };

    return (
        <GoogleLogin
            // 로그인 성공 시 handleSuccess 실행
            onSuccess={handleSuccess}

            // 로그인 실패 시 실행
            onError={() => {
                console.log("로그인 실패");
            }}
        />
    );
}

export default LoginButton;
