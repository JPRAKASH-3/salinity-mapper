import { useState } from "react"; import { api, errMsg } from "../services/api"; import { useFetch } from "../components/Common";
export default function Admin() {
  const [msg, setMsg] = useState(""); const pend = useFetch(async () => (await api.get("/api/water-quality", { params: { status: "pending", limit: 50 } })).data, [msg]);
  const act = async (fn: () => Promise<any>) => { setMsg("…"); try { setMsg(JSON.stringify((await fn()).data)); } catch (e) { setMsg(String(errMsg(e))); } };
  return (<div className="space-y-4"><h1 className="text-2xl font-semibold">Admin</h1>{msg && <div className="card text-sm break-words">{msg}</div>}
    <div className="card flex flex-wrap gap-2"><button className="btn" onClick={() => act(() => api.post("/api/analytics/assess-all"))}>Assess all borewells</button><button className="btn" onClick={() => act(() => api.post("/api/notifications/retest-sweep"))}>Retest sweep</button>
      <button className="btn" onClick={() => act(() => api.post("/api/ml/train"))}>Train model (real data only)</button></div>
    <div className="card overflow-x-auto"><h2 className="font-medium mb-2">Pending samples</h2><table className="text-sm w-full"><thead><tr className="text-left text-slate-500"><th>ID</th><th>Borewell</th><th>Date</th><th>EC</th><th>Origin</th><th /></tr></thead>
      <tbody>{(pend.data as any[] ?? []).map((r) => <tr key={r.id} className="border-t"><td>{r.id}</td><td>{r.borewell_id ?? "—"}</td><td>{r.sampled_on}</td><td>{r.ec_us_cm}</td><td>{r.origin}</td><td className="space-x-2"><button className="text-fresh" onClick={() => act(() => api.post(`/api/water-quality/${r.id}/verify?ok=true`))}>Verify</button><button className="text-crit" onClick={() => act(() => api.post(`/api/water-quality/${r.id}/verify?ok=false`))}>Reject</button></td></tr>)}</tbody></table></div></div>);
}
