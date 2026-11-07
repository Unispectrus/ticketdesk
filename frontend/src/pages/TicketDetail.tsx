import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useParams } from "react-router-dom";
import { api, patch, post, type Priority, type Status, type TicketDetail, type User } from "../api";
import { useAuth } from "../auth";
import { Badge, fmt } from "../ui";

const NEXT: Record<Status, Status[]> = {
  open: ["in_progress", "closed"], in_progress: ["resolved", "open"], resolved: ["closed", "open"], closed: ["open"],
};
const CUSTOMER_OK = new Set(["resolved>closed", "open>closed", "resolved>open", "closed>open"]);

export default function TicketDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const qc = useQueryClient();
  const staff = user!.role !== "customer";
  const key = ["ticket", id];
  const { data: t, error, isLoading } = useQuery({ queryKey: key, queryFn: () => api<TicketDetail>(`/tickets/${id}`) });
  const { data: staffList } = useQuery({ queryKey: ["staff"], enabled: staff, queryFn: async () => (await api<User[]>("/admin/users")).filter((u) => u.role !== "customer" && u.is_active) });

  const refresh = () => { qc.invalidateQueries({ queryKey: key }); qc.invalidateQueries({ queryKey: ["tickets"] }); };
  const update = useMutation({ mutationFn: (body: object) => patch(`/tickets/${id}`, body), onSuccess: refresh });
  const [body, setBody] = useState("");
  const [internal, setInternal] = useState(false);
  const comment = useMutation({
    mutationFn: () => post(`/tickets/${id}/comments`, { body, is_internal: internal }),
    onSuccess: () => { setBody(""); setInternal(false); refresh(); },
  });
  const submit = (e: FormEvent) => { e.preventDefault(); comment.mutate(); };

  if (isLoading) return <p className="muted">Loading…</p>;
  if (error || !t) return <p className="error">{error?.message ?? "Not found"}</p>;
  const allowed = NEXT[t.status].filter((s) => staff || CUSTOMER_OK.has(`${t.status}>${s}`));

  return (
    <div className="grid">
      <section>
        <div className="card">
          <h2>#{t.id} {t.subject}</h2>
          <p className="muted">By {t.requester.full_name} · {fmt(t.created_at)} · {t.category}</p>
          <p className="pre">{t.description}</p>
        </div>
        <h3>Conversation</h3>
        {t.comments.length === 0 && <p className="muted">No replies yet.</p>}
        {t.comments.map((c) => (
          <div key={c.id} className={`card comment ${c.is_internal ? "internal" : ""}`}>
            <strong>{c.author.full_name}</strong> <span className="muted">{c.author.role} · {fmt(c.created_at)}</span>
            {c.is_internal && <Badge kind="internal">internal note</Badge>}
            <p className="pre">{c.body}</p>
          </div>
        ))}
        {t.status !== "closed" && (
          <form className="card" onSubmit={submit}>
            <textarea required rows={3} placeholder="Write a reply…" value={body} onChange={(e) => setBody(e.target.value)} />
            <div className="row">
              {staff && <label className="inline"><input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} /> Internal note</label>}
              <span className="spacer" />
              <button disabled={comment.isPending}>{internal ? "Add note" : "Send reply"}</button>
            </div>
            {comment.error && <p className="error">{comment.error.message}</p>}
          </form>
        )}
      </section>
      <aside>
        <div className="card">
          <h3>Details</h3>
          <p>Status <Badge kind={t.status}>{t.status.replace("_", " ")}</Badge></p>
          <p>Priority <Badge kind={t.priority}>{t.priority}</Badge></p>
          <p>SLA due <span className={t.sla_breached ? "error" : ""}>{fmt(t.sla_due_at)}{t.sla_breached && " (breached)"}</span></p>
          <p>Assignee {t.assignee?.full_name ?? <span className="muted">Unassigned</span>}</p>
          {allowed.length > 0 && (
            <div className="actions">
              {allowed.map((s) => <button key={s} disabled={update.isPending} onClick={() => update.mutate({ status: s })}>Mark {s.replace("_", " ")}</button>)}
            </div>
          )}
          {staff && (
            <>
              <label>Priority
                <select value={t.priority} onChange={(e) => update.mutate({ priority: e.target.value as Priority })}>
                  {["low", "medium", "high", "urgent"].map((p) => <option key={p}>{p}</option>)}
                </select>
              </label>
              <label>Assign to
                <select value={t.assignee?.id ?? ""} onChange={(e) => update.mutate(e.target.value ? { assignee_id: Number(e.target.value) } : { unassign: true })}>
                  <option value="">Unassigned</option>
                  {staffList?.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
                </select>
              </label>
            </>
          )}
          {update.error && <p className="error">{update.error.message}</p>}
        </div>
        <div className="card">
          <h3>History</h3>
          <ul className="history">
            {t.history.map((h) => (
              <li key={h.id}><strong>{h.actor.full_name}</strong> {h.field}: {h.old_value ?? "—"} → {h.new_value ?? "—"}<br /><span className="muted small">{fmt(h.created_at)}</span></li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  );
}
