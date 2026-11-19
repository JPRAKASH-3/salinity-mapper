import { useState } from "react"; import { api, errMsg } from "../services/api"; import { useAuth } from "../context/Auth"; import { Note } from "../components/Common";
const num = (v: string) => (v === "" ? undefined : Number(v));
export default function RegisterBorewell() {
  const { user } = useAuth(); const [msg, setMsg] = useState(""); const [bw, setBw] = useState<any>({ name: "", latitude: "", longitude: "", district: "", village: "", depth_m: "", show_contributor: false });
  const [wq, setWq] = useState<any>({ borewell_id: "", sampled_on: "", ec_us_cm: "", tds_mg_l: "", ph: "", chloride_mg_l: "", sodium_mg_l: "", calcium_mg_l: "", magnesium_mg_l: "", sampling_method: "" });
  const [file, setFile] = useState<File | null>(null); const [origin, setOrigin] = useState("public_dataset"); const staff = user && ["admin", "researcher"].includes(user.role);
  const run = async (fn: () => Promise<any>, ok: (r: any) => string) => { setMsg(""); try { setMsg(ok((await fn()).data)); } catch (e) { setMsg("Error: " + JSON.stringify(errMsg(e))); } };
  return (<div className="space-y-4 max-w-3xl"><h1 className="text-2xl font-semibold">Add data</h1>{msg && <div className="card text-sm break-words">{msg}</div>}
    <div className="card space-y-2"><h2 className="font-medium">1. Register borewell</h2><div className="grid grid-cols-2 gap-2">
      {["name", "district", "village", "latitude", "longitude", "depth_m"].map((k) => <input key={k} className="input" placeholder={k} value={bw[k]} onChange={(e) => setBw({ ...bw, [k]: e.target.value })} />)}</div>
      <label className="text-sm flex gap-2"><input type="checkbox" checked={bw.show_contributor} onChange={(e) => setBw({ ...bw, show_contributor: e.target.checked })} />Show my name as contributor (off = private)</label>
      <button className="btn" onClick={() => run(() => api.post("/api/borewells", { ...bw, latitude: Number(bw.latitude), longitude: Number(bw.longitude), depth_m: num(bw.depth_m) }), (r) => `Created borewell id ${r.id} (${r.code}), status ${r.status}. Use this id below.`)}>Register</button></div>
    <div className="card space-y-2"><h2 className="font-medium">2. Add water-quality sample (EC µS/cm; TDS, Cl, Na, Ca, Mg mg/L)</h2><div className="grid grid-cols-2 md:grid-cols-3 gap-2">
      {Object.keys(wq).map((k) => <input key={k} className="input" type={k === "sampled_on" ? "date" : "text"} placeholder={k} value={wq[k]} onChange={(e) => setWq({ ...wq, [k]: e.target.value })} />)}</div>
      <button className="btn" onClick={() => run(() => api.post("/api/water-quality", { borewell_id: Number(wq.borewell_id), sampled_on: wq.sampled_on, sampling_method: wq.sampling_method || undefined,
        ...Object.fromEntries(["ec_us_cm", "tds_mg_l", "ph", "chloride_mg_l", "sodium_mg_l", "calcium_mg_l", "magnesium_mg_l"].map((k) => [k, num(wq[k])])) }), (r) => `Saved. Measured class: ${r.category ?? "n/a"} · status ${r.status}`)}>Save sample</button>
      <Note>Non-admin submissions stay “pending” until an administrator verifies them and are excluded from model training and verified statistics.</Note></div>
    {staff && <div className="card space-y-2"><h2 className="font-medium">3. Bulk upload (.csv / .xlsx)</h2><div className="text-sm">Required columns: borewell_code, sampled_on, ec_us_cm (optional: tds_mg_l, ph, chloride_mg_l, sodium_mg_l, calcium_mg_l, magnesium_mg_l)</div>
      <select className="input" value={origin} onChange={(e) => setOrigin(e.target.value)}><option value="public_dataset">Historical public dataset</option><option value="measured_verified">Measured (verified)</option><option value="user_submitted">User-submitted</option><option value="synthetic_demo">Synthetic demo</option></select>
      <input type="file" accept=".csv,.xlsx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <button className="btn" disabled={!file} onClick={() => { const fd = new FormData(); fd.append("file", file!); run(() => api.post(`/api/water-quality/upload?origin=${origin}&source_name=${encodeURIComponent(file!.name)}`, fd), (r) => `Accepted ${r.accepted}, rejected ${r.rejected}. ${JSON.stringify(r.errors.slice(0, 5))}`); }}>Upload</button></div>}</div>);
}
