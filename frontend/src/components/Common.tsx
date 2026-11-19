import { ReactNode, useEffect, useState } from "react";
export const Badge = ({ origin }: { origin?: string }) => origin === "synthetic_demo"
  ? <span className="text-xs bg-purple-100 text-purple-800 px-2 py-0.5 rounded">SYNTHETIC DEMO</span>
  : <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded">{origin?.replace("_", " ")}</span>;
export const Pill = ({ text, color }: { text?: string | null; color?: string }) => text ? <span className="text-xs px-2 py-0.5 rounded text-white" style={{ background: color ?? "#64748b" }}>{text}</span> : <span className="text-slate-400">—</span>;
export function Kpi({ label, value, color }: { label: string; value?: number; color?: string }) {
  const [n, setN] = useState(0);
  useEffect(() => { if (value == null) return; let f = 0; const id = setInterval(() => { f += 1; setN(Math.round(value * Math.min(f / 20, 1))); if (f >= 20) clearInterval(id); }, 25); return () => clearInterval(id); }, [value]);
  return <div className="card"><div className="text-sm text-slate-500">{label}</div>{value == null ? <div className="skeleton h-8 w-16 mt-1" /> : <div className="text-3xl font-semibold" style={{ color }}>{n}</div>}</div>;
}
export const Note = ({ children }: { children: ReactNode }) => <div className="text-xs text-slate-500 border-l-4 border-ocean-aqua pl-2 my-2">{children}</div>;
export const useFetch = <T,>(fn: () => Promise<T>, deps: any[] = []) => {
  const [data, setData] = useState<T | null>(null); const [error, setError] = useState<string | null>(null);
  useEffect(() => { setData(null); fn().then(setData).catch((e) => setError(e?.response?.data?.detail ?? e.message)); }, deps); // eslint-disable-line
  return { data, error };
};
