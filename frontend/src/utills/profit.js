// src/utils/profit.js

export function fmtProfit(v) {
    if (v == null || v === "") return "-";
    const n = Number(v);
    return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

export function profitColor(v) {
    const n = Number(v);
    if (v == null || isNaN(n) || n === 0) return "text-gray-900";
    return n > 0 ? "text-red-500" : "text-blue-500";
}

export function profitBadge(v) {
    const n = Number(v);
    if (v == null || isNaN(n) || n === 0) return "bg-gray-100 text-gray-900";
    return n > 0 ? "bg-red-50 text-red-500" : "bg-blue-50 text-blue-500";
}
