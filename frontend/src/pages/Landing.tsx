import { motion } from "framer-motion"; import { Link } from "react-router-dom"; import { lazy, Suspense } from "react"; import { Droplets } from "lucide-react";
const Particles = lazy(() => import("../animations/WaterParticles"));
export default function Landing() {
  return (<div className="relative min-h-screen bg-ocean-deep text-white overflow-hidden flex items-center">
    <Suspense fallback={null}><Particles /></Suspense>
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="relative z-10 max-w-3xl mx-auto p-6 text-center">
      <Droplets className="mx-auto text-ocean-aqua" size={48} />
      <h1 className="text-4xl md:text-5xl font-bold mt-4">Coastal Saltwater Intrusion &amp; Borewell Salinity Mapper</h1>
      <p className="mt-4 text-slate-200">Measured borewell chemistry, GIS risk assessment and forecasting for Tamil Nadu's coastal districts. Measurements, risk assessments and AI predictions are always labelled separately.</p>
      <div className="mt-8 flex gap-3 justify-center"><Link className="btn" to="/app/map">Explore the map</Link><Link className="px-4 py-2 rounded-lg border border-white/40" to="/login">Sign in / Register</Link></div>
    </motion.div></div>);
}
