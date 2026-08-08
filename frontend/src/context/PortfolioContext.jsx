import { createContext, useContext, useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
const REFRESH_MS = 2000;

const PortfolioContext = createContext(null);

const DEFAULT_STATE = {
    portfolio: [], cash: null, total_asset: null, profit_rate: null,
};

function parsePortfolio(d) {
    return {
        portfolio: Array.isArray(d?.portfolio) ? d.portfolio : [],
        cash: d?.cash ?? null,
        total_asset: d?.total_asset ?? null,
        profit_rate: d?.profit_rate ?? null,
    };
}

export function PortfolioProvider({ children }) {
    const [bearData, setBearData] = useState({ ...DEFAULT_STATE });
    const [foxData, setFoxData] = useState({ ...DEFAULT_STATE });
    const [turtleData, setTurtleData] = useState({ ...DEFAULT_STATE });

    const timerRef = useRef(null);

    useEffect(() => {
        const fetchAll = () => {
            fetch(`${API}/portfolio`)
                .then((r) => r.json())
                .then((d) => setBearData(parsePortfolio(d)))
                .catch(() => { });

            fetch(`${API}/fox-portfolio`)
                .then((r) => r.json())
                .then((d) => setFoxData(parsePortfolio(d)))
                .catch(() => { });

            fetch(`${API}/turtle-portfolio`)
                .then((r) => r.json())
                .then((d) => setTurtleData(parsePortfolio(d)))
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
