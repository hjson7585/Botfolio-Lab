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
import AdminDashboard from "./pages/AdminDashboard";
import IndustryBearPage from "./IndustryBearPage";
import MomentumFoxPage from "./pages/MomentumFoxPage";

function App() {
    const [user, setUser] = useState(null);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
            setUser(currentUser);
        });
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
            } catch (error) {
                console.log(error);
            }
        };
        trackVisitor();
    }, []);

    const login = async () => {
        try {
            await signInWithPopup(auth, provider);
        } catch (error) {
            console.log(error);
        }
    };

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

                <Route
                    path="/"
                    element={<Home user={user} login={login} logout={logout} />}
                />

                <Route
                    path="/agent/industry-bear"
                    element={<IndustryBearPage />}
                />

                <Route
                    path="/momentum-fox"
                    element={<MomentumFoxPage />}
                />

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
