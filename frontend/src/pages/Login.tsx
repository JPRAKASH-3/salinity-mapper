import { useState } from "react"; import { useNavigate } from "react-router-dom"; import { api, errMsg } from "../services/api"; import { useAuth } from "../context/Auth";
export default function Login() {
  const [mode, setMode] = useState<"in" | "up">("in"); const [f, setF] = useState({ email: "", password: "", full_name: "", role: "public", district: "" });
  const [err, setErr] = useState(""); const { login } = useAuth(); const nav = useNavigate(); const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value });
  const submit = async () => { setErr(""); try {
    const r = mode === "in" ? await api.post("/api/auth/login", new URLSearchParams({ username: f.email, password: f.password })) : await api.post("/api/auth/register", f);
    await login(r.data.access_token); nav("/app"); } catch (e) { setErr(String(errMsg(e))); } };
  return (<div className="min-h-screen grid place-items-center p-4"><div className="card w-full max-w-sm space-y-3">
    <h1 className="text-xl font-semibold">{mode === "in" ? "Sign in" : "Create account"}</h1>
    {mode === "up" && <><input className="input" placeholder="Full name" value={f.full_name} onChange={set("full_name")} />
      <select className="input" value={f.role} onChange={set("role")}><option value="public">General public</option><option value="farmer">Farmer</option><option value="researcher">Researcher</option></select></>}
    <input className="input" type="email" placeholder="Email" value={f.email} onChange={set("email")} />
    <input className="input" type="password" placeholder="Password (min 8)" value={f.password} onChange={set("password")} />
    {err && <div className="text-sm text-crit">{err}</div>}<button className="btn w-full" onClick={submit}>{mode === "in" ? "Sign in" : "Register"}</button>
    <button className="text-sm text-ocean underline" onClick={() => setMode(mode === "in" ? "up" : "in")}>{mode === "in" ? "Need an account?" : "Have an account?"}</button></div></div>);
}
