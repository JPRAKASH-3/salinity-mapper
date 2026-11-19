import axios from "axios";
export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? "" });
api.interceptors.request.use((c) => { const t = localStorage.getItem("token"); if (t) c.headers.Authorization = `Bearer ${t}`; return c; });
export const CAT_COLOR: Record<string, string> = { Low: "#22C55E", Moderate: "#FACC15", Elevated: "#F97316", High: "#DC2626" };
export const RISK_COLOR: Record<string, string> = { "Low Risk": "#22C55E", "Moderate Risk": "#FACC15", "High Risk": "#F97316", "Very High Risk": "#DC2626" };
export const errMsg = (e: any) => e?.response?.data?.detail ?? e?.message ?? "Request failed";
