// 127.0.0.1 주소의 8000번 서버에
// /ws 경로로 WebSocket 연결을 만듦
const socket = new WebSocket("ws://127.0.0.1:8000/ws");

// 이 socket을 다른 파일에서도 쓸 수 있게 내보냄
export default socket;
