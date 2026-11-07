from datetime import timedelta

from app.models import Ticket, utcnow
from app.services.sla import mark_breaches


def new_ticket(client, headers, **over):
    body = {"subject": "Cannot login", "description": "Login page errors out", "priority": "medium", **over}
    r = client.post("/tickets", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def setup(client, make_org, make_user):
    slug, admin = make_org()
    cust, cust_id = make_user(slug, "c1@x.com")
    cust2, _ = make_user(slug, "c2@x.com")
    agent, agent_id = make_user(slug, "agent@x.com", admin, "agent")
    return slug, admin, cust, cust2, agent, agent_id


def test_customer_creates_and_sees_only_own(client, make_org, make_user):
    _, admin, cust, cust2, agent, _ = setup(client, make_org, make_user)
    t = new_ticket(client, cust)
    assert t["status"] == "open" and t["requester"]["role"] == "customer"
    assert client.get("/tickets", headers=cust).json()["total"] == 1
    assert client.get("/tickets", headers=cust2).json()["total"] == 0
    assert client.get(f"/tickets/{t['id']}", headers=cust2).status_code == 404
    assert client.get("/tickets", headers=agent).json()["total"] == 1


def test_tenant_isolation(client, make_org, make_user):
    slug, admin, cust, *_ = setup(client, make_org, make_user)
    _, other_admin = make_org("other", "admin@other.com")
    t = new_ticket(client, cust)
    assert client.get("/tickets", headers=other_admin).json()["total"] == 0
    assert client.get(f"/tickets/{t['id']}", headers=other_admin).status_code == 404
    assert client.patch(f"/tickets/{t['id']}", json={"status": "in_progress"}, headers=other_admin).status_code == 404
    assert client.post(f"/tickets/{t['id']}/comments", json={"body": "hi"}, headers=other_admin).status_code == 404
    assert len(client.get("/admin/users", headers=other_admin).json()) == 1


def test_customer_cannot_change_priority_assignee_or_work_ticket(client, make_org, make_user):
    _, _, cust, _, _, agent_id = setup(client, make_org, make_user)
    t = new_ticket(client, cust)
    assert client.patch(f"/tickets/{t['id']}", json={"priority": "urgent"}, headers=cust).status_code == 403
    assert client.patch(f"/tickets/{t['id']}", json={"assignee_id": agent_id}, headers=cust).status_code == 403
    assert client.patch(f"/tickets/{t['id']}", json={"status": "in_progress"}, headers=cust).status_code in (403,)


def test_agent_workflow_and_history(client, make_org, make_user):
    _, _, cust, _, agent, agent_id = setup(client, make_org, make_user)
    t = new_ticket(client, cust)
    tid = t["id"]
    assert client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers=agent).status_code == 409  # open -> resolved invalid
    r = client.patch(f"/tickets/{tid}", json={"assignee_id": agent_id}, headers=agent)
    assert r.status_code == 200 and r.json()["status"] == "in_progress" and r.json()["assignee"]["id"] == agent_id
    assert client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers=agent).json()["resolved_at"]
    assert client.patch(f"/tickets/{tid}", json={"status": "closed"}, headers=agent).status_code == 200
    fields = [(h["field"], h["new_value"]) for h in client.get(f"/tickets/{tid}", headers=agent).json()["history"]]
    assert fields[0] == ("status", "open")
    assert ("assignee", str(agent_id)) in fields and ("status", "closed") in fields


def test_customer_can_close_resolved_and_reopen(client, make_org, make_user):
    _, _, cust, _, agent, agent_id = setup(client, make_org, make_user)
    tid = new_ticket(client, cust)["id"]
    client.patch(f"/tickets/{tid}", json={"assignee_id": agent_id}, headers=agent)
    client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers=agent)
    assert client.patch(f"/tickets/{tid}", json={"status": "open"}, headers=cust).json()["status"] == "open"
    client.patch(f"/tickets/{tid}", json={"status": "in_progress"}, headers=agent)
    client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers=agent)
    assert client.patch(f"/tickets/{tid}", json={"status": "closed"}, headers=cust).json()["status"] == "closed"
    assert client.post(f"/tickets/{tid}/comments", json={"body": "more"}, headers=cust).status_code == 409


def test_cannot_assign_customer_or_foreign_user(client, make_org, make_user):
    slug, admin, cust, _, agent, _ = setup(client, make_org, make_user)
    _, foreign_admin = make_org("other", "admin@other.com")
    foreign_id = client.get("/auth/me", headers=foreign_admin).json()["id"]
    cust_id = client.get("/auth/me", headers=cust).json()["id"]
    tid = new_ticket(client, cust)["id"]
    assert client.patch(f"/tickets/{tid}", json={"assignee_id": cust_id}, headers=agent).status_code == 422
    assert client.patch(f"/tickets/{tid}", json={"assignee_id": foreign_id}, headers=agent).status_code == 422


def test_internal_notes_hidden_from_customer(client, make_org, make_user):
    _, _, cust, _, agent, _ = setup(client, make_org, make_user)
    tid = new_ticket(client, cust)["id"]
    assert client.post(f"/tickets/{tid}/comments", json={"body": "secret", "is_internal": True}, headers=cust).status_code == 403
    client.post(f"/tickets/{tid}/comments", json={"body": "secret", "is_internal": True}, headers=agent)
    client.post(f"/tickets/{tid}/comments", json={"body": "public reply"}, headers=agent)
    assert [c["body"] for c in client.get(f"/tickets/{tid}", headers=cust).json()["comments"]] == ["public reply"]
    assert len(client.get(f"/tickets/{tid}", headers=agent).json()["comments"]) == 2


def test_filters_search_pagination(client, make_org, make_user):
    _, _, cust, _, agent, _ = setup(client, make_org, make_user)
    for i in range(5):
        new_ticket(client, cust, subject=f"Printer {i} jammed", priority="high" if i < 2 else "low")
    new_ticket(client, cust, subject="Invoice question", description="billing")
    assert client.get("/tickets?q=printer", headers=agent).json()["total"] == 5
    assert client.get("/tickets?priority=high", headers=agent).json()["total"] == 2
    p = client.get("/tickets?page=2&page_size=4", headers=agent).json()
    assert p["total"] == 6 and len(p["items"]) == 2
    assert client.get("/tickets?page_size=1000", headers=agent).status_code == 422
    assert client.get("/tickets?status=closed", headers=agent).json()["total"] == 0


def test_priority_change_recomputes_sla(client, make_org, make_user):
    _, _, cust, _, agent, _ = setup(client, make_org, make_user)
    t = new_ticket(client, cust, priority="low")
    r = client.patch(f"/tickets/{t['id']}", json={"priority": "urgent"}, headers=agent).json()
    assert r["sla_due_at"] < t["sla_due_at"]


def test_sla_breach_worker_and_report(client, make_org, make_user, db_session):
    _, admin, cust, _, agent, _ = setup(client, make_org, make_user)
    late = new_ticket(client, cust, priority="urgent")
    new_ticket(client, cust, priority="low")
    ticket = db_session.get(Ticket, late["id"])
    ticket.sla_due_at = utcnow() - timedelta(hours=1)
    db_session.commit()
    assert mark_breaches(db_session) == 1
    assert mark_breaches(db_session) == 0  # idempotent
    rep = client.get("/admin/reports/sla", headers=admin).json()
    assert rep["total_tickets"] == 2 and rep["breached"] == 1 and rep["open_overdue"] == 1 and rep["breach_rate"] == 0.5
    assert client.get("/admin/reports/sla", headers=agent).status_code == 403
    assert client.get("/tickets?sla_breached=true", headers=agent).json()["total"] == 1


def test_resolving_after_deadline_marks_breach(client, make_org, make_user, db_session):
    _, _, cust, _, agent, agent_id = setup(client, make_org, make_user)
    tid = new_ticket(client, cust, priority="urgent")["id"]
    db_session.get(Ticket, tid).sla_due_at = utcnow() - timedelta(minutes=5)
    db_session.commit()
    client.patch(f"/tickets/{tid}", json={"assignee_id": agent_id}, headers=agent)
    assert client.patch(f"/tickets/{tid}", json={"status": "resolved"}, headers=agent).json()["sla_breached"] is True


def test_admin_user_management_rules(client, make_org, make_user):
    _, admin, cust, _, agent, _ = setup(client, make_org, make_user)
    admin_id = client.get("/auth/me", headers=admin).json()["id"]
    assert client.patch(f"/admin/users/{admin_id}", json={"role": "agent"}, headers=admin).status_code == 409
    assert client.get("/admin/users", headers=cust).status_code == 403
    assert client.get("/admin/users", headers=agent).status_code == 200
    assert client.patch(f"/admin/users/{admin_id}", json={"role": "agent"}, headers=agent).status_code == 403
