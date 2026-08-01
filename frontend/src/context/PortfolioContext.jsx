import { createContext, useContext, useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const REFRESH_MS = 2000;

const PortfolioContext = createContext(null);

export function PortfolioProvider({ children }) {
    const [bearData, setBearData] = useState({
        portfolio: [], cash: null, total_asset: null, profit_rate: null,
    });
    const [foxData, setFoxData] = useState({
        portfolio: [], cash: null, total_asset: null, profit_rate: null,
    });
    const [turtleData, setTurtleData] = useState({
        portfolio: [], cash: null, total_asset: null, profit_rate: null,
    });

    const timerRef = useRef(null);

    useEffect(() => {
        const fetchAll = () => {
            fetch(`${API}/portfolio`)
                .then((r) => r.json())
                .then((d) => setBearData(d))
                .catch(() => { });

            fetch(`${API}/fox-portfolio`)
                .then((r) => r.json())
                .then((d) => setFoxData(d))
                .catch(() => { });

            fetch(`${API}/turtle-portfolio`)
                .then((r) => r.json())
                .then((d) => setTurtleData(d))
                .catch(() => { });
        };

        fetchAll();
        timerRef.current = setInterval(fetchAll, REFRESH_MS);
        return () => clearInterval(timerRef.current);
    }, []);

    return (
        <PortfolioContext.Provider value={{ bearData, foxData, turtleData }}>
            {children}
        </PortfolioContext.Provider>
    );
}

export function usePortfolio() {
    return useContext(PortfolioContext);
}
