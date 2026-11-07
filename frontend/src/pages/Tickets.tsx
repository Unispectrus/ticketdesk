import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Page } from "../api";
import { Badge, fmt } from "../ui";

export default function Tickets() {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => { const t = setTimeout(() => { setDebounced(q); setPage(1); }, 300); return () => clearTimeout(t); }, [q]);

  const params = new URLSearchParams({ page: String(page), page_size: "15" });
  if (debounced) params.set("q", debounced);
  if (status) params.set("status", status);
  if (priority) params.set("priority", priority);

  const { data, isLoading, error } = useQuery({
    queryKey: ["tickets", debounced, status, priority, page],
    queryFn: () => api<Page>(`/tickets?${params}`),
    placeholderData: keepPreviousData,
  });
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div>
      <div className="row filters">
        <input placeholder="Search tickets…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} aria-label="Status">
          <option value="">All statuses</option>
          {["open", "in_progress", "resolved", "closed"].map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
        </select>
        <select value={priority} onChange={(e) => { setPriority(e.target.value); setPage(1); }} aria-label="Priority">
          <option value="">All priorities</option>
          {["urgent", "high", "medium", "low"].map((p) => <option key={p}>{p}</option>)}
        </select>
      </div>
      {isLoading && <p className="muted">Loading…</p>}
      {error && <p className="error">{error.message}</p>}
      {data && (
        <>
          <table>
            <thead><tr><th>#</th><th>Subject</th><th>Status</th><th>Priority</th><th>Requester</th><th>Assignee</th><th>SLA due</th></tr></thead>
            <tbody>
              {data.items.map((t) => (
                <tr key={t.id}>
                  <td>{t.id}</td>
                  <td><Link to={`/tickets/${t.id}`}>{t.subject}</Link></td>
                  <td><Badge kind={t.status}>{t.status.replace("_", " ")}</Badge></td>
                  <td><Badge kind={t.priority}>{t.priority}</Badge></td>
                  <td>{t.requester.full_name}</td>
                  <td>{t.assignee?.full_name ?? <span className="muted">—</span>}</td>
                  <td className={t.sla_breached ? "error" : ""}>{fmt(t.sla_due_at)}{t.sla_breached && " ⚠"}</td>
                </tr>
              ))}
              {data.items.length === 0 && <tr><td colSpan={7} className="muted center">No tickets found</td></tr>}
            </tbody>
          </table>
          <div className="row pager">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
            <span className="muted">Page {page} of {pages} · {data.total} tickets</span>
            <button disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
          </div>
        </>
      )}
    </div>
  );
}
