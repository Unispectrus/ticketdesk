import { useState, type FormEvent } from "react";
import { useAuth } from "../auth";

type Mode = "login" | "register" | "org";

export default function Login() {
  const { login, register, registerOrg } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [f, setF] = useState({ org: "acme", orgName: "", name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      if (mode === "login") await login(f.org, f.email, f.password);
      else if (mode === "register") await register(f.org, f.name, f.email, f.password);
      else await registerOrg(f.orgName, f.org, f.name, f.email, f.password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally { setBusy(false); }
  }

  return (
    <form className="card auth" onSubmit={submit}>
      <h1>TicketDesk</h1>
      <p className="muted">{mode === "login" ? "Sign in to your workspace" : mode === "register" ? "Create a customer account" : "Create a new workspace"}</p>
      {mode === "org" && <label>Company name<input required value={f.orgName} onChange={set("orgName")} /></label>}
      <label>Workspace ID<input required pattern="[a-z0-9\-]+" value={f.org} onChange={set("org")} placeholder="acme" /></label>
      {mode !== "login" && <label>Full name<input required value={f.name} onChange={set("name")} /></label>}
      <label>Email<input required type="email" value={f.email} onChange={set("email")} /></label>
      <label>Password<input required type="password" minLength={8} value={f.password} onChange={set("password")} /></label>
      {error && <p className="error" role="alert">{error}</p>}
      <button disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}</button>
      <p className="muted small">
        {mode !== "login" && <button type="button" className="link" onClick={() => setMode("login")}>Sign in</button>}
        {mode !== "register" && <button type="button" className="link" onClick={() => setMode("register")}>Customer sign-up</button>}
        {mode !== "org" && <button type="button" className="link" onClick={() => setMode("org")}>New workspace</button>}
      </p>
      <p className="muted small">Demo (after seeding): workspace <code>acme</code>, <code>admin@acme.com</code> / <code>demo1234</code></p>
    </form>
  );
}
