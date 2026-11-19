import { useEffect, useState } from "react"; import { api } from "../services/api";
export default function Alerts() {
  const [items, setItems] = useState<any[] | null>(null); const load = () => api.get("/api/notifications").then((r) => setItems(r.data)); useEffect(() => { load(); }, []);
  return (<div className="space-y-3 max-w-3xl"><h1 className="text-2xl font-semibold">Alerts &amp; notifications</h1>{items?.length === 0 && <div className="card text-sm">No alerts.</div>}
    {items?.map((n) => <div key={n.id} className={`card flex justify-between gap-3 ${n.is_read ? "opacity-60" : ""}`}><div><span className={`text-xs px-2 py-0.5 rounded text-white mr-2 ${n.basis === "measured" ? "bg-ocean" : "bg-purple-600"}`}>{n.basis === "measured" ? "MEASURED" : "PREDICTED"}</span><span className="text-sm">{n.message.replace(/^\[\w+\]\s*/, "")}</span><div className="text-xs text-slate-400">{new Date(n.created_at).toLocaleString()}</div></div>
      {!n.is_read && <button className="text-sm text-ocean" onClick={() => api.post(`/api/notifications/${n.id}/read`).then(load)}>Mark read</button>}</div>)}</div>);
}
