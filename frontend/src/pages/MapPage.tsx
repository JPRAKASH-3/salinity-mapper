import { useEffect, useMemo, useState } from "react"; import { CircleMarker, GeoJSON, LayersControl, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster"; import { api, CAT_COLOR, RISK_COLOR } from "../services/api"; import HeatLayer from "../maps/HeatLayer"; import { Badge, Note } from "../components/Common";
function Fly({ to }: { to: [number, number] | null }) { const m = useMap(); useEffect(() => { if (to) m.flyTo(to, 13); }, [to, m]); return null; }
export default function MapPage() {
  const [fc, setFc] = useState<any>(null); const [heat, setHeat] = useState<number[][]>([]); const [zones, setZones] = useState<any>(null); const [bounds, setBounds] = useState<any>(null);
  const [mode, setMode] = useState<"measured" | "risk">("measured"); const [q, setQ] = useState(""); const [fly, setFly] = useState<[number, number] | null>(null);
  useEffect(() => { api.get("/api/maps/borewells").then((r) => setFc(r.data)); api.get("/api/maps/heatmap").then((r) => setHeat(r.data)); api.get("/api/maps/risk-zones").then((r) => setZones(r.data));
    api.get("/api/maps/boundaries?level=districts").then((r) => setBounds(r.data)).catch(() => {}); }, []);
  const feats = useMemo(() => (fc?.features ?? []) as any[], [fc]);
  const hit = q.length > 1 ? feats.filter((f) => `${f.properties.name} ${f.properties.village} ${f.properties.district}`.toLowerCase().includes(q.toLowerCase())) : [];
  return (<div className="space-y-2"><div className="flex flex-wrap gap-2 items-center"><h1 className="text-2xl font-semibold mr-4">Coastal salinity map</h1>
    <div className="relative"><input className="input w-64" placeholder="Search district, village, borewell" value={q} onChange={(e) => setQ(e.target.value)} />
      {hit.length > 0 && <div className="absolute z-[1000] bg-white border rounded-lg w-full max-h-56 overflow-auto">{hit.slice(0, 8).map((f) => <button key={f.properties.id} className="block w-full text-left px-3 py-1 hover:bg-slate-100 text-sm"
        onClick={() => { setFly([f.geometry.coordinates[1], f.geometry.coordinates[0]]); setQ(""); }}>{f.properties.name} · {f.properties.district}</button>)}</div>}</div>
    <div className="flex rounded-lg overflow-hidden border">{(["measured", "risk"] as const).map((m) => <button key={m} onClick={() => setMode(m)} className={`px-3 py-2 text-sm ${mode === m ? "bg-ocean text-white" : "bg-white"}`}>{m === "measured" ? "Measured class" : "Risk assessment"}</button>)}</div></div>
    <div className="h-[70vh] rounded-xl overflow-hidden border"><MapContainer center={[11.2, 79.6]} zoom={7} scrollWheelZoom><TileLayer attribution="&copy; OpenStreetMap contributors" url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" /><Fly to={fly} />
      <LayersControl position="topright">
        <LayersControl.Overlay checked name="Borewells (clustered)"><MarkerClusterGroup chunkedLoading>{feats.map((f) => { const p = f.properties; const c = mode === "measured" ? CAT_COLOR[p.measured_category] : RISK_COLOR[p.risk_category];
          return <CircleMarker key={p.id} center={[f.geometry.coordinates[1], f.geometry.coordinates[0]]} radius={8} pathOptions={{ color: "#fff", weight: 1, fillColor: c ?? "#94a3b8", fillOpacity: .9 }}>
            <Popup><div className="space-y-1 text-sm"><b>{p.name}</b> <Badge origin={p.origin} /><div>{p.village}, {p.district} · {p.distance_to_coast_km} km from coast</div>
              <div><b>Measured:</b> {p.measured_category ?? "n/a"} (EC {p.ec_us_cm ?? "—"} µS/cm, {p.sampled_on ?? "—"}, {p.record_status})</div>
              <div><b>Risk assessment:</b> {p.risk_category ?? "not assessed"}{p.risk_confidence != null && ` (confidence ${p.risk_confidence})`}</div></div></Popup></CircleMarker>; })}</MarkerClusterGroup></LayersControl.Overlay>
        <LayersControl.Overlay name="EC heatmap (measured)"><HeatLayer points={heat} /></LayersControl.Overlay>
        {zones?.features?.length > 0 && <LayersControl.Overlay checked name="Indicative risk zones"><GeoJSON data={zones} style={{ color: "#DC2626", weight: 1, fillOpacity: .15 }} /></LayersControl.Overlay>}
        {bounds && <LayersControl.Overlay name="District boundaries"><GeoJSON data={bounds} style={{ color: "#0B2545", weight: 1, fill: false }} /></LayersControl.Overlay>}
      </LayersControl></MapContainer></div>
    <div className="flex flex-wrap gap-3 text-xs">{Object.entries(mode === "measured" ? CAT_COLOR : RISK_COLOR).map(([k, c]) => <span key={k} className="flex items-center gap-1"><i className="w-3 h-3 rounded-full inline-block" style={{ background: c }} />{k}</span>)}</div>
    <Note>Measured class comes from lab/field values vs configurable thresholds. Risk assessment is a separate heuristic score — it is not confirmed saltwater intrusion. Coastline distance is approximate.</Note></div>);
}
