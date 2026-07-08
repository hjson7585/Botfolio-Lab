import os
import firebase_admin
from firebase_admin import credentials

def init_firebase():
    if firebase_admin._apps:
        return

    # 환경변수 방식 (Render 배포용)
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
    private_key = os.getenv("FIREBASE_PRIVATE_KEY")

    if project_id and client_email and private_key:
        cred = credentials.Certificate({
            "type": "service_account",
            "project_id": project_id,
            "client_email": client_email,
            "private_key": private_key.replace("\\n", "\n"),
            "token_uri": "https://oauth2.googleapis.com/token",
        })
        firebase_admin.initialize_app(cred)
        print("[Firebase] 환경변수로 초기화 완료")
    else:
        # 로컬 개발용 폴백 (파일이 있을 때만)
        import json
        from pathlib import Path
        local_path = Path(__file__).resolve().parent.parent / "firebase-service-account.json"
        if local_path.exists():
            cred = credentials.Certificate(str(local_path))
            firebase_admin.initialize_app(cred)
            print("[Firebase] 로컬 파일로 초기화 완료")
        else:
            raise RuntimeError("Firebase 인증 정보가 없습니다. 환경변수를 확인하세요.")
