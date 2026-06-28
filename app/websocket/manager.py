# FastAPI에서 WebSocket 기능을 사용할 때 필요한 WebSocket 클래스 import
from fastapi import WebSocket


# 여러 WebSocket 연결을 관리하기 위한 클래스 정의
class ConnectionManager:

    # 클래스가 처음 만들어질 때 실행되는 초기화 함수
    def __init__(self):
        # 현재 연결되어 있는 WebSocket 객체들을 저장할 리스트
        self.active_connections = []

    # 새로운 사용자가 WebSocket으로 접속했을 때 실행되는 함수
    async def connect(self, websocket: WebSocket):
        # 클라이언트의 WebSocket 연결 요청을 수락
        await websocket.accept()

        # 연결된 WebSocket 객체를 active_connections 리스트에 추가
        self.active_connections.append(websocket)

    # 사용자가 연결을 끊었을 때 실행되는 함수
    def disconnect(self, websocket: WebSocket):
        # active_connections 리스트에서 해당 연결 제거
        self.active_connections.remove(websocket)

    # 현재 연결된 모든 사용자에게 같은 데이터를 보내는 함수
    async def broadcast(self, data):
        # 연결된 모든 WebSocket을 하나씩 꺼내서 반복
        for connection in self.active_connections:
            # 각 사용자에게 JSON 형태로 데이터 전송
            await connection.send_json(data)


# ConnectionManager 객체를 하나 생성
# 보통 이 객체를 전역으로 만들어두고 여러 WebSocket 요청에서 같이 사용함
manager = ConnectionManager()
