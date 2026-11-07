import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { post, type Priority, type Ticket } from "../api";

export default function NewTicket() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [f, setF] = useState({ subject: "", description: "", category: "general", priority: "medium" as Priority });
  const m = useMutation({
    mutationFn: () => post<Ticket>("/tickets", f),
    onSuccess: (t) => { qc.invalidateQueries({ queryKey: ["tickets"] }); nav(`/tickets/${t.id}`); },
  });
  const submit = (e: FormEvent) => { e.preventDefault(); m.mutate(); };
  return (
    <form className="card" onSubmit={submit}>
      <h2>New ticket</h2>
      <label>Subject<input required minLength={3} maxLength={200} value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} /></label>
      <label>Description<textarea required rows={6} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} /></label>
      <div className="row">
        <label>Category
          <select value={f.category} onChange={(e) => setF({ ...f, category: e.target.value })}>
            {["general", "billing", "bug", "feature", "account", "performance"].map((c) => <option key={c}>{c}</option>)}
          </select>
        </label>
        <label>Priority
          <select value={f.priority} onChange={(e) => setF({ ...f, priority: e.target.value as Priority })}>
            {["low", "medium", "high", "urgent"].map((p) => <option key={p}>{p}</option>)}
          </select>
        </label>
      </div>
      {m.error && <p className="error" role="alert">{m.error.message}</p>}
      <button disabled={m.isPending}>{m.isPending ? "Submitting…" : "Submit ticket"}</button>
    </form>
  );
}
