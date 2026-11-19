import { useState } from "react"; import { api, errMsg } from "../services/api"; import { Note, useFetch } from "../components/Common";
export default function Predictions() {
  const perf = useFetch(async () => (await api.get("/api/ml/model-performance")).data); const [id, setId] = useState(""); const [h, setH] = useState(180); const [out, setOut] = useState<any>(null); const [err, setErr] = useState("");
  const m: any = perf.data; const run = async () => { setErr(""); setOut(null); try { setOut((await api.post("/api/ml/predict", { borewell_id: Number(id), horizon_days: h })).data); } catch (e) { setErr(String(errMsg(e))); } };
  const row = (k: string, v: any) => <tr key={k}><td className="pr-4 text-slate-500">{k}</td><td>{v && `MAE ${v.MAE} · RMSE ${v.RMSE} · R² ${v.R2}`}</td></tr>;
  return (<div className="space-y-4 max-w-3xl"><h1 className="text-2xl font-semibold">AI prediction dashboard</h1>
    <div className="card"><h2 className="font-medium mb-2">Model performance (held-out data)</h2>{!m ? <div className="skeleton h-16" /> : !m.trained ? <div className="text-sm">{m.message}</div> : <>
      {m.contains_synthetic && <div className="bg-purple-50 text-purple-900 text-sm p-2 rounded mb-2">This model was trained with SYNTHETIC data — for pipeline testing only.</div>}
      <table className="text-sm"><tbody>{row("Spatial hold-out (unseen districts)", m.spatial_holdout)}{row("Temporal hold-out (latest 20%)", m.temporal_holdout)}{row("Baseline: ‘no change’", m.baseline_persistence_temporal)}
        <tr><td className="pr-4 text-slate-500">80% interval coverage</td><td>{m.interval_80_coverage_temporal}</td></tr></tbody></table>
      {m.classification && <div className="mt-2 text-sm">Class prediction — precision {m.classification.precision_macro}, recall {m.classification.recall_macro}, F1 {m.classification.f1_macro}<pre className="text-xs mt-1">{m.classification.confusion_matrix.map((r: number[]) => r.join("\t")).join("\n")}</pre></div>}
      <Note>{m.n_pairs} sample pairs from {m.n_borewells} borewells · model {m.model_version}. If the model does not beat the ‘no change’ baseline, do not rely on it.</Note></>}</div>
    <div className="card space-y-2"><h2 className="font-medium">Predict EC for a borewell</h2><div className="flex gap-2"><input className="input" placeholder="Borewell id" value={id} onChange={(e) => setId(e.target.value)} />
      <select className="input" value={h} onChange={(e) => setH(Number(e.target.value))}>{[90, 180, 365].map((d) => <option key={d} value={d}>{d} days</option>)}</select><button className="btn" onClick={run}>Predict</button></div>
      {err && <div className="text-sm text-crit">{err}</div>}{out && <div className="text-sm"><b>{out.predicted_ec} µS/cm</b> (80% interval {out.lower_80}–{out.upper_80}) · class {out.predicted_class ?? "n/a"}<Note>{out.label}. Model {out.model_version}.</Note></div>}</div></div>);
}
