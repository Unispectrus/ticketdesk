import { Link, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Admin from "./pages/Admin";
import Login from "./pages/Login";
import NewTicket from "./pages/NewTicket";
import TicketDetailPage from "./pages/TicketDetail";
import Tickets from "./pages/Tickets";

export default function App() {
  const { user, loading, logout } = useAuth();
  if (loading) return <p className="center">Loading…</p>;
  if (!user) return <Login />;
  const staff = user.role !== "customer";
  return (
    <>
      <header className="nav">
        <Link to="/" className="brand">TicketDesk</Link>
        <Link to="/">Tickets</Link>
        <Link to="/new">New ticket</Link>
        {user.role === "admin" && <Link to="/admin">Admin</Link>}
        <span className="spacer" />
        <span className="muted">{user.full_name} · {user.role}{staff ? "" : ""}</span>
        <button className="link" onClick={logout}>Log out</button>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Tickets />} />
          <Route path="/new" element={<NewTicket />} />
          <Route path="/tickets/:id" element={<TicketDetailPage />} />
          <Route path="/admin" element={user.role === "admin" ? <Admin /> : <Navigate to="/" />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
    </>
  );
}
