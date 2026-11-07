import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, post, tokenStore, type User } from "./api";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (org: string, email: string, password: string) => Promise<void>;
  register: (org: string, name: string, email: string, password: string) => Promise<void>;
  registerOrg: (orgName: string, slug: string, name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const qc = useQueryClient();

  const loadMe = useCallback(async () => {
    try { setUser(await api<User>("/auth/me")); } catch { setUser(null); }
  }, []);

  useEffect(() => {
    (tokenStore.get() ? loadMe() : Promise.resolve()).finally(() => setLoading(false));
  }, [loadMe]);

  const logout = useCallback(() => { tokenStore.set(null); setUser(null); qc.clear(); }, [qc]);
  useEffect(() => {
    window.addEventListener("ticketdesk:logout", logout);
    return () => window.removeEventListener("ticketdesk:logout", logout);
  }, [logout]);

  const finish = async (tokens: { access_token: string; refresh_token: string }) => { tokenStore.set(tokens); await loadMe(); };

  const value: AuthCtx = {
    user, loading, logout,
    login: async (org_slug, email, password) => finish(await post("/auth/login", { org_slug, email, password })),
    register: async (org_slug, full_name, email, password) => finish(await post("/auth/register", { org_slug, full_name, email, password })),
    registerOrg: async (org_name, org_slug, full_name, email, password) => finish(await post("/auth/register-org", { org_name, org_slug, full_name, email, password })),
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth outside AuthProvider");
  return v;
}
