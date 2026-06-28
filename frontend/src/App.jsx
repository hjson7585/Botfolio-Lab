import { useEffect, useState } from "react";

import {
    BrowserRouter,
    Routes,
    Route,
    Navigate,
} from "react-router-dom";

import {
    signInWithPopup,
    signOut,
    onAuthStateChanged,
} from "firebase/auth";

import { doc, setDoc } from "firebase/firestore";

import { auth, provider, db } from "./firebase";

import Home from "./pages/Home";
import AgentDetail from "./pages/AgentDetail";
import AdminDashboard from "./pages/AdminDashboard";
import IndustryBearPage from "./IndustryBearPage"; // ✅ 추가

function App() {
    const [user, setUser] = useState(null);

    // Firebase 로그인 상태 감지
    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
            setUser(currentUser);
        });
        return () => unsubscribe();
    }, []);

    // 방문자 추적
    useEffect(() => {
        const trackVisitor = async () => {
            try {
                let visitorId = localStorage.getItem("visitor_id");
                if (!visitorId) {
                    visitorId = crypto.randomUUID();
                    localStorage.setItem("visitor_id", visitorId);
                }
                await setDoc(doc(db, "visitors", visitorId), {
                    visitedAt: new Date(),
                    userAgent: navigator.userAgent,
                });
            } catch (error) {
                console.log(error);
            }
        };
        trackVisitor();
    }, []);

    // 로그인
    const login = async () => {
        try {
            await signInWithPopup(auth, provider);
        } catch (error) {
            console.log(error);
        }
    };

    // 로그아웃
    const logout = async () => {
        try {
            await signOut(auth);
        } catch (error) {
            console.log(error);
        }
    };

    return (
        <BrowserRouter>
            <Routes>

                {/* 홈 */}
                <Route
                    path="/"
                    element={<Home user={user} login={login} logout={logout} />}
                />

                {/* 인더스트리곰 전용 페이지 */}                {/* ✅ 추가 */}
                <Route
                    path="/agent/industry-bear"
                    element={<IndustryBearPage />}
                />

                {/* AI 에이전트 상세 (기타 에이전트) */}
                <Route
                    path="/agent/:id"
                    element={<AgentDetail />}
                />

                {/* 관리자 페이지 */}
                <Route
                    path="/admin"
                    element={
                        user?.email === "hjson7585@gmail.com"
                            ? <AdminDashboard />
                            : <Navigate to="/" />
                    }
                />

            </Routes>
        </BrowserRouter>
    );
}

export default App;
