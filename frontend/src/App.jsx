import { useEffect, useState } from "react";
import {
    BrowserRouter, Routes, Route, Navigate,
} from "react-router-dom";
import {
    signInWithPopup, signOut, onAuthStateChanged,
} from "firebase/auth";
import { doc, setDoc } from "firebase/firestore";
import { auth, provider, db } from "./firebase";

import Home from "./pages/Home";
import AdminDashboard from "./pages/AdminDashboard";
import IndustryBearPage from "./pages/IndustryBearPage";
import MomentumFoxPage from "./pages/MomentumFoxPage";
import DividendTurtlePage from "./pages/DividendTurtlePage";
import AdminPage from "./pages/AdminPage";


function App() {
    const [user, setUser] = useState(null);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (u) => setUser(u));
        return () => unsubscribe();
    }, []);

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
            } catch (e) { console.log(e); }
        };
        trackVisitor();
    }, []);

    const login = async () => { try { await signInWithPopup(auth, provider); } catch (e) { console.log(e); } };
    const logout = async () => { try { await signOut(auth); } catch (e) { console.log(e); } };

    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Home user={user} login={login} logout={logout} />} />
                <Route path="/agent/industry-bear" element={<IndustryBearPage />} />
                <Route path="/momentum-fox" element={<MomentumFoxPage />} />
                <Route path="/agent/dividend-turtle" element={<DividendTurtlePage />} />
                <Route path="/admin"
                    element={
                        user?.email === "hjson7585@gmail.com"
                            ? <AdminDashboard />
                            : <Navigate to="/" />
                    }

                />
                <Route path="/admin/control" element={<AdminPage />} />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
