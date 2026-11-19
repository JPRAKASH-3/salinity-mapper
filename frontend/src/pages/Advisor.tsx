import { useState } from "react"; import { api, errMsg } from "../services/api"; import { Note } from "../components/Common";
export default function Advisor() {
  const [id, setId] = useState(""); const [a, setA] = useState<any>(null); const [err, setErr] = useState(""); const [bl, setBl] = useState({ ec_saline: "", ec_fresh: "", target_ec: "" }); const [mix, setMix] = useState<any>(null);
  return (<div className="space-y-4 max-w-3xl"><h1 className="text-2xl font-semibold">Agricultural advisor</h1>
    <div className="card space-y-2"><div className="flex gap-2"><input className="input" placeholder="Borewell id" value={id} onChange={(e) => setId(e.target.value)} /><button className="btn" onClick={async () => { setErr(""); try { setA((await api.get(`/api/agri/advisory/${id}`)).data); } catch (e) { setErr(String(errMsg(e))); } }}>Assess</button></div>
      {err && <div className="text-sm text-crit">{err}</div>}{a && <div className="text-sm space-y-2"><div><b>{a.suitability}</b> — {a.borewell}, sample {a.based_on_sample} ({a.record_status})</div><ul className="list-disc ml-5">{a.notes.map((n: string) => <li key={n}>{n}</li>)}</ul>
        <div><b>Crop groups to consider:</b> {a.crop_groups.map((g: any) => <div key={g.group}>{g.group}: {g.examples.join(", ")}</div>)}</div><ul className="list-disc ml-5">{a.management.map((n: string) => <li key={n}>{n}</li>)}</ul><Note>{a.disclaimer}</Note></div>}</div>
    <div className="card space-y-2"><h2 className="font-medium">Freshwater blending calculator (EC µS/cm)</h2><div className="grid grid-cols-3 gap-2">{(["ec_saline", "ec_fresh", "target_ec"] as const).map((k) => <input key={k} className="input" placeholder={k} value={bl[k]} onChange={(e) => setBl({ ...bl, [k]: e.target.value })} />)}</div>
      <button className="btn" onClick={async () => { try { setMix((await api.get("/api/agri/blend", { params: bl })).data); } catch (e) { setMix({ note: String(errMsg(e)) }); } }}>Calculate</button>
      {mix && <div className="text-sm">{mix.fresh_fraction != null && <>Fresh {Math.round(mix.fresh_fraction * 100)}% / saline {Math.round(mix.saline_fraction * 100)}%. </>}{mix.note}</div>}</div></div>);
}
