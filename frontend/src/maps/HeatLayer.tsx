import L from "leaflet"; import "leaflet.heat"; import { useEffect } from "react"; import { useMap } from "react-leaflet";
export default function HeatLayer({ points }: { points: number[][] }) {
  const map = useMap();
  useEffect(() => { const l = (L as any).heatLayer(points, { radius: 25, blur: 20, maxZoom: 11 }).addTo(map); return () => { map.removeLayer(l); }; }, [points, map]);
  return null;
}
