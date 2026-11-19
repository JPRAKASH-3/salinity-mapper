import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api } from "../services/api";
type User = { id: number; email: string; full_name: string; role: "admin" | "farmer" | "researcher" | "public" };
const Ctx = createContext<{ user: User | null; login: (t: string) => Promise<void>; logout: () => void; ready: boolean }>(null!);
export const useAuth = () => useContext(Ctx);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null); const [ready, setReady] = useState(false);
  const load = async () => { try { setUser((await api.get("/api/auth/profile")).data); } catch { setUser(null); } setReady(true); };
  useEffect(() => { localStorage.getItem("token") ? load() : setReady(true); }, []);
  const login = async (t: string) => { localStorage.setItem("token", t); await load(); };
  const logout = () => { localStorage.removeItem("token"); setUser(null); };
  return <Ctx.Provider value={{ user, login, logout, ready }}>{children}</Ctx.Provider>;
}
