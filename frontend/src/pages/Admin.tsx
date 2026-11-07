import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, patch, type Role, type SlaReport, type User } from "../api";
import { useAuth } from "../auth";

export default function Admin() {
  const { user: me } = useAuth();
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ["users"], queryFn: () => api<User[]>("/admin/users") });
  const report = useQuery({ queryKey: ["sla"], queryFn: () => api<SlaReport>("/admin/reports/sla") });
  const update = useMutation({
    mutationFn: ({ id, ...body }: { id: number; role?: Role; is_active?: boolean }) => patch(`/admin/users/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
  const r = report.data;

  return (
    <div>
      <h2>SLA report</h2>
      {r && (
        <div className="stats">
          <div className="card"><div className="big">{r.total_tickets}</div>tickets</div>
          <div className="card"><div className="big">{r.breached}</div>breached</div>
          <div className="card"><div className="big">{r.open_overdue}</div>open &amp; overdue</div>
          <div className="card"><div className="big">{(r.breach_rate * 100).toFixed(1)}%</div>breach rate</div>
        </div>
      )}
      {r && (
        <table>
          <thead><tr><th>Priority</th><th>Total</th><th>Breached</th></tr></thead>
          <tbody>{Object.entries(r.by_priority).map(([p, v]) => <tr key={p}><td>{p}</td><td>{v.total}</td><td>{v.breached}</td></tr>)}</tbody>
        </table>
      )}
      <h2>Users</h2>
      {update.error && <p className="error">{update.error.message}</p>}
      <table>
        <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Active</th></tr></thead>
        <tbody>
          {users.data?.map((u) => (
            <tr key={u.id}>
              <td>{u.full_name}</td><td>{u.email}</td>
              <td>
                <select value={u.role} disabled={u.id === me!.id} onChange={(e) => update.mutate({ id: u.id, role: e.target.value as Role })}>
                  {["customer", "agent", "admin"].map((x) => <option key={x}>{x}</option>)}
                </select>
              </td>
              <td><input type="checkbox" checked={u.is_active} disabled={u.id === me!.id} onChange={(e) => update.mutate({ id: u.id, is_active: e.target.checked })} aria-label={`Active ${u.full_name}`} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
