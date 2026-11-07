"""Seed demo data: python -m app.seed"""
import random
from datetime import timedelta

from sqlalchemy import select

from .database import SessionLocal
from .models import Comment, Organization, Priority, Role, Status, StatusHistory, Ticket, User, utcnow
from .security import hash_password
from .services.sla import due_date

PASSWORD = "demo1234"
SUBJECTS = [
    ("Cannot log in to dashboard", "billing"), ("Invoice shows wrong amount", "billing"), ("App crashes on export", "bug"),
    ("Request: dark mode", "feature"), ("Password reset email not arriving", "account"), ("Slow page loads on reports", "performance"),
    ("How do I add a teammate?", "general"), ("Webhook returning 500", "bug"), ("Update company address", "account"), ("Data export missing rows", "bug"),
]


def main() -> None:
    db = SessionLocal()
    if db.scalar(select(Organization).where(Organization.slug == "acme")):
        print("Already seeded")
        return
    org = Organization(name="Acme Corp", slug="acme")
    db.add(org)
    db.flush()

    def mk(email, name, role):
        u = User(org_id=org.id, email=email, full_name=name, password_hash=hash_password(PASSWORD), role=role)
        db.add(u)
        return u

    admin = mk("admin@acme.com", "Alice Admin", Role.admin)
    agents = [mk("agent1@acme.com", "Ravi Agent", Role.agent), mk("agent2@acme.com", "Sara Agent", Role.agent)]
    customers = [mk(f"customer{i}@example.com", n, Role.customer) for i, n in enumerate(["Chris Customer", "Dana Client", "Eli User"], 1)]
    db.flush()

    rnd = random.Random(42)
    for i in range(40):
        subject, cat = SUBJECTS[i % len(SUBJECTS)]
        prio = rnd.choice(list(Priority))
        created = utcnow() - timedelta(hours=rnd.randint(1, 20))
        status = rnd.choice(list(Status))
        assignee = rnd.choice(agents) if status != Status.open else None
        t = Ticket(
            org_id=org.id, subject=subject, description=f"{subject}. Details: customer reports this started recently.", category=cat,
            priority=prio, status=status, requester_id=rnd.choice(customers).id, assignee_id=assignee.id if assignee else None,
            created_at=created, sla_due_at=due_date(prio, created),
        )
        t.sla_breached = status in (Status.open, Status.in_progress) and t.sla_due_at < utcnow()
        if status in (Status.resolved, Status.closed):
            t.resolved_at = created + timedelta(hours=rnd.randint(1, 20))
            t.sla_breached = t.resolved_at > t.sla_due_at
        db.add(t)
        db.flush()
        db.add(StatusHistory(ticket_id=t.id, actor_id=t.requester_id, field="status", old_value=None, new_value="open", created_at=created))
        if assignee:
            db.add(Comment(ticket_id=t.id, author_id=assignee.id, body="Looking into this now.", created_at=created + timedelta(minutes=30)))
            db.add(Comment(ticket_id=t.id, author_id=assignee.id, body="Internal: check logs for tenant config.", is_internal=True, created_at=created + timedelta(minutes=35)))
    db.commit()
    print(f"Seeded. Org slug 'acme'. Logins (password '{PASSWORD}'): admin@acme.com, agent1@acme.com, customer1@example.com")


if __name__ == "__main__":
    main()
