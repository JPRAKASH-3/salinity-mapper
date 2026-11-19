import { lazy, Suspense } from "react"; import { Navigate, Route, Routes } from "react-router-dom";
import Shell from "./layouts/Shell"; import { useAuth } from "./context/Auth";
const Landing = lazy(() => import("./pages/Landing")); const Login = lazy(() => import("./pages/Login"));
const Dashboard = lazy(() => import("./pages/Dashboard")); const MapPage = lazy(() => import("./pages/MapPage"));
const Explorer = lazy(() => import("./pages/Explorer")); const Register = lazy(() => import("./pages/RegisterBorewell"));
const Predictions = lazy(() => import("./pages/Predictions")); const Analytics = lazy(() => import("./pages/Analytics"));
const Alerts = lazy(() => import("./pages/Alerts")); const Advisor = lazy(() => import("./pages/Advisor")); const Admin = lazy(() => import("./pages/Admin"));
function Guard({ roles, children }: { roles?: string[]; children: JSX.Element }) {
  const { user, ready } = useAuth(); if (!ready) return null;
  if (!user) return <Navigate to="/login" replace />; if (roles && !roles.includes(user.role)) return <Navigate to="/app" replace />; return children;
}
export default function App() {
  return (<Suspense fallback={<div className="p-8"><div className="skeleton h-8 w-64" /></div>}><Routes>
    <Route path="/" element={<Landing />} /><Route path="/login" element={<Login />} />
    <Route path="/app" element={<Shell />}>
      <Route index element={<Dashboard />} /><Route path="map" element={<MapPage />} /><Route path="borewells" element={<Explorer />} />
      <Route path="analytics" element={<Analytics />} /><Route path="advisor" element={<Advisor />} />
      <Route path="register" element={<Guard><Register /></Guard>} /><Route path="alerts" element={<Guard><Alerts /></Guard>} />
      <Route path="predictions" element={<Guard roles={["admin", "researcher", "farmer"]}><Predictions /></Guard>} />
      <Route path="admin" element={<Guard roles={["admin"]}><Admin /></Guard>} />
    </Route></Routes></Suspense>);
}
