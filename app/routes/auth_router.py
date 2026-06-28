# 운영체제의 환경 변수 값을 읽기 위한 모듈
import os

# .env 파일의 값을 불러오기 위한 함수
from dotenv import load_dotenv

# FastAPI에서 라우터를 만들기 위한 클래스
from fastapi import APIRouter

# 구글 로그인 토큰 검증에 필요한 모듈
from google.oauth2 import id_token
from google.auth.transport import requests

# JWT 토큰 생성에 사용할 라이브러리
from jose import jwt

# .env 파일을 읽어서 환경 변수로 등록
load_dotenv()

# 인증 관련 API들을 묶는 라우터 생성
router = APIRouter()

# 환경 변수에서 SECRET_KEY 읽어오기
# .env 파일에 SECRET_KEY=값 형태로 저장되어 있어야 함
SECRET_KEY = os.getenv("SECRET_KEY")

# 관리자 이메일
# 로그인한 사용자의 이메일이 이 값과 같으면 관리자 권한 부여
ADMIN_EMAIL = "hjson7585@gmail.com"


# "/auth/google" 경로로 POST 요청이 들어오면 실행되는 함수
@router.post("/auth/google")
async def google_auth(data: dict):

    # 오류가 발생할 수 있는 코드를 try 안에서 실행
    try:

        # 프론트엔드가 보낸 구글 토큰 꺼내기
        token = data["token"]

        # Google 토큰 검증
        # 이 토큰이 진짜 구글에서 발급한 토큰인지 확인
        idinfo = id_token.verify_oauth2_token(token, requests.Request())

        # 검증된 토큰 정보에서 사용자 이메일 가져오기
        email = idinfo["email"]

        # 관리자 여부 확인
        # 이메일이 관리자 이메일과 같으면 True, 아니면 False
        is_admin = email == ADMIN_EMAIL

        # JWT 안에 담을 데이터(payload) 만들기
        payload = {"email": email, "is_admin": is_admin}

        # JWT 생성
        # payload를 SECRET_KEY로 서명해서 access_token 생성
        access_token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        # 성공했을 때 프론트엔드에 결과 반환
        return {"access_token": access_token, "email": email, "is_admin": is_admin}

    # try 안에서 에러가 발생하면 여기로 들어옴
    except Exception as e:

        # 서버 콘솔에 에러 메시지 출력
        print("Google 로그인 오류:")
        print(e)

        # 프론트엔드에 에러 내용 반환
        return {"error": str(e)}
