export type Role = "customer" | "agent" | "admin";
export type Status = "open" | "in_progress" | "resolved" | "closed";
export type Priority = "low" | "medium" | "high" | "urgent";

export interface UserBrief { id: number; full_name: string; role: Role }
export interface User extends UserBrief { email: string; is_active: boolean; org_id: number }
export interface Ticket {
  id: number; subject: string; description: string; category: string;
  status: Status; priority: Priority; created_at: string; updated_at: string;
  sla_due_at: string; sla_breached: boolean; resolved_at: string | null;
  requester: UserBrief; assignee: UserBrief | null;
}
export interface Comment { id: number; body: string; is_internal: boolean; created_at: string; author: UserBrief }
export interface HistoryEntry { id: number; field: string; old_value: string | null; new_value: string | null; created_at: string; actor: UserBrief }
export interface TicketDetail extends Ticket { comments: Comment[]; history: HistoryEntry[] }
export interface Page { items: Ticket[]; total: number; page: number; page_size: number }
export interface SlaReport { total_tickets: number; breached: number; open_overdue: number; breach_rate: number; by_priority: Record<string, { total: number; breached: number }> }

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const KEY = "ticketdesk.tokens";

interface Tokens { access_token: string; refresh_token: string }

export const tokenStore = {
  get(): Tokens | null {
    try { return JSON.parse(localStorage.getItem(KEY) ?? "null"); } catch { return null; }
  },
  set(t: Tokens | null) {
    try { t ? localStorage.setItem(KEY, JSON.stringify(t)) : localStorage.removeItem(KEY); } catch { /* storage unavailable */ }
  },
};

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

let refreshing: Promise<boolean> | null = null;

async function refresh(): Promise<boolean> {
  const t = tokenStore.get();
  if (!t) return false;
  const r = await fetch(`${BASE}/auth/refresh`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: t.refresh_token }) });
  if (!r.ok) { tokenStore.set(null); return false; }
  tokenStore.set(await r.json());
  return true;
}

function detail(body: unknown, fallback: string): string {
  const d = (body as { detail?: unknown })?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e) => (e as { msg: string }).msg).join("; ");
  return fallback;
}

export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const t = tokenStore.get();
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (t) headers.set("Authorization", `Bearer ${t.access_token}`);
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (res.status === 401 && retry && t) {
    refreshing ??= refresh().finally(() => { refreshing = null; });
    if (await refreshing) return api<T>(path, init, false);
    window.dispatchEvent(new Event("ticketdesk:logout"));
  }
  const body = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new ApiError(res.status, detail(body, res.statusText));
  return body as T;
}

export const post = <T,>(path: string, data: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(data) });
export const patch = <T,>(path: string, data: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(data) });
