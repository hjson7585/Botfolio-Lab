// WebSocket 서버에 연결
// "ws://127.0.0.1:8000/ws" 주소로 실시간 통신 연결을 만듦
const socket = new WebSocket("ws://127.0.0.1:8000/ws");

// 서버에서 메시지가 도착할 때마다 실행되는 함수
socket.onmessage = function(event) {

    // 서버에서 받은 문자열 데이터를 JavaScript 객체로 변환
    // 예: '{"stocks":[...], "total_value":1234.5}' → 객체 형태로 바뀜
    const data = JSON.parse(event.data);

    // id가 "portfolio"인 HTML 요소를 가져옴
    // 이 변수는 현재 코드에서는 실제로 사용되지 않지만,
    // 포트폴리오 영역 전체를 참조하려고 만든 것으로 보임
    const portfolioDiv = document.getElementById("portfolio");

    // 표 안에 들어갈 HTML 문자열을 저장할 변수
    let html = "";

    // data.stocks 배열에 들어 있는 각 종목 데이터를 하나씩 반복 처리
    data.stocks.forEach(stock => {

        // 각 종목 정보를 표의 한 줄(<tr>)로 만들어 html 변수에 이어 붙임
        html += `
            <tr>
                <td>${stock.symbol}</td>
                <td>${stock.quantity}</td>
                <td>$${stock.avg_price}</td>
                <td>$${stock.current_price}</td>
                <td>$${stock.current_value}</td>
            </tr>
        `;
    });

    // id가 "portfolio-body"인 요소(보통 <tbody>) 안의 내용을
    // 위에서 만든 html 문자열로 통째로 바꿈
    document.getElementById("portfolio-body").innerHTML = html;

    // id가 "total-value"인 요소의 텍스트를 현재 총 자산 값으로 변경
    document.getElementById("total-value").innerText =
        `$${data.total_value}`;
};
