import { AnimatePresence, motion } from "framer-motion"; import { Bell, BarChart3, Brain, Database, Droplets, LogOut, Map, PlusCircle, Shield, Sprout, LayoutDashboard } from "lucide-react";
import { NavLink, Outlet, useLocation, Link } from "react-router-dom"; import { useAuth } from "../context/Auth";
export default function Shell() {
  const { user, logout } = useAuth(); const loc = useLocation();
  const items = [["/app", "Dashboard", LayoutDashboard], ["/app/map", "Map", Map], ["/app/borewells", "Borewells", Database], ["/app/analytics", "Analytics", BarChart3],
    ["/app/advisor", "Advisor", Sprout], ["/app/predictions", "AI Predictions", Brain], ["/app/register", "Add data", PlusCircle], ["/app/alerts", "Alerts", Bell]] as const;
  return (<div className="min-h-screen flex flex-col md:flex-row">
    <aside className="md:w-56 bg-ocean-deep text-white p-3 flex md:flex-col gap-1 overflow-x-auto">
      <Link to="/" className="flex items-center gap-2 font-semibold p-2 shrink-0"><Droplets className="text-ocean-aqua" />Salinity Mapper</Link>
      {items.map(([to, label, Icon]) => <NavLink key={to} to={to} end={to === "/app"} className={({ isActive }) => `flex items-center gap-2 px-3 py-2 rounded-lg shrink-0 ${isActive ? "bg-ocean" : "hover:bg-white/10"}`}><Icon size={18} />{label}</NavLink>)}
      {user?.role === "admin" && <NavLink to="/app/admin" className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-white/10 shrink-0"><Shield size={18} />Admin</NavLink>}
      <div className="md:mt-auto p-2 text-sm shrink-0">{user ? <button onClick={logout} className="flex gap-2 items-center"><LogOut size={16} />{user.full_name} ({user.role})</button> : <Link to="/login">Sign in</Link>}</div>
    </aside>
    <main className="flex-1 p-4 md:p-6 min-w-0"><AnimatePresence mode="wait"><motion.div key={loc.pathname} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: .2 }}><Outlet /></motion.div></AnimatePresence></main></div>);
}
