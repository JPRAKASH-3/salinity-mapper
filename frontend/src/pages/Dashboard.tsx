import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { api } from "../services/api"; import { Kpi, Note, useFetch } from "../components/Common"; import Aquifer3D from "../animations/Aquifer3D";
export default function Dashboard() {
  const ov = useFetch(async () => (await api.get("/api/analytics/overview")).data); const h = useFetch(async () => (await api.get("/api/analytics/historical")).data);
  const d = useFetch(async () => (await api.get("/api/analytics/districts")).data); const o: any = ov.data;
  const dist = o ? Object.entries(o.measured_distribution).map(([k, v]) => ({ k, v })) : [];
  const dr = (d.data as any[] | null)?.map((x) => ({ district: x.district, Low: x.risk_counts["Low Risk"] || 0, Moderate: x.risk_counts["Moderate Risk"] || 0, High: (x.risk_counts["High Risk"] || 0) + (x.risk_counts["Very High Risk"] || 0) }));
  return (<div className="space-y-4"><h1 className="text-2xl font-semibold">Dashboard</h1>
    {o?.contains_synthetic_demo && <div className="bg-purple-50 border border-purple-200 text-purple-900 rounded-lg p-3 text-sm">This database contains <b>synthetic demonstration data</b> (shown with a purple badge). It is not real groundwater evidence.</div>}
    <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
      <Kpi label="Registered borewells" value={o?.total_borewells} /><Kpi label="Verified samples" value={o?.verified_samples} />
      <Kpi label="Low risk" value={o?.risk_low} color="#22C55E" /><Kpi label="Moderate risk" value={o?.risk_moderate} color="#CA8A04" />
      <Kpi label="High / very high risk" value={o?.risk_high} color="#DC2626" /><Kpi label="Need retesting" value={o?.requiring_retest} color="#F97316" /></div>
    {o && o.unassessed > 0 && <Note>{o.unassessed} borewells have no risk assessment yet (run “Assess all” in Admin).</Note>}
    <div className="grid lg:grid-cols-2 gap-4">
      <div className="card h-72"><h3 className="font-medium mb-2">Measured salinity class (verified samples)</h3><ResponsiveContainer><BarChart data={dist}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="k" /><YAxis /><Tooltip /><Bar dataKey="v" fill="#087EAD" /></BarChart></ResponsiveContainer></div>
      <div className="card h-72"><h3 className="font-medium mb-2">Monthly mean EC / TDS (µS/cm · mg/L)</h3><ResponsiveContainer><LineChart data={h.data as any[] ?? []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="period" /><YAxis /><Tooltip /><Legend /><Line dataKey="avg_ec" name="EC" stroke="#087EAD" dot={false} /><Line dataKey="avg_tds" name="TDS" stroke="#F97316" dot={false} /></LineChart></ResponsiveContainer></div>
      <div className="card h-72"><h3 className="font-medium mb-2">District risk distribution (assessment)</h3><ResponsiveContainer><BarChart data={dr ?? []}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="district" tick={{ fontSize: 10 }} /><YAxis /><Tooltip /><Legend /><Bar stackId="a" dataKey="Low" fill="#22C55E" /><Bar stackId="a" dataKey="Moderate" fill="#FACC15" /><Bar stackId="a" dataKey="High" fill="#DC2626" /></BarChart></ResponsiveContainer></div>
      <div className="card"><h3 className="font-medium mb-2">Seawater-wedge schematic</h3><Aquifer3D intrusion={o ? Math.min(1, o.risk_high / Math.max(1, o.total_borewells) * 3) : .3} /><Note>Illustrative schematic only; wedge length is scaled from the share of high-risk borewells, not a hydrogeological model.</Note></div></div></div>);
}
