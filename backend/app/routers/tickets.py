from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..models import Comment, Priority, Role, Status, StatusHistory, Ticket, User, utcnow
from ..schemas import CommentCreate, CommentOut, Page, TicketCreate, TicketDetail, TicketOut, TicketUpdate
from ..services.notifications import send_email
from ..services.sla import as_utc, due_date

router = APIRouter(prefix="/tickets", tags=["tickets"])

TRANSITIONS: dict[Status, set[Status]] = {
    Status.open: {Status.in_progress, Status.closed},
    Status.in_progress: {Status.resolved, Status.open},
    Status.resolved: {Status.closed, Status.open},
    Status.closed: {Status.open},
}
# What a customer may do to their own ticket: close it, or reopen it.
CUSTOMER_TRANSITIONS = {(Status.resolved, Status.closed), (Status.open, Status.closed), (Status.resolved, Status.open), (Status.closed, Status.open)}


def is_staff(user: User) -> bool:
    return user.role in (Role.agent, Role.admin)


def get_ticket_or_404(db: Session, ticket_id: int, user: User) -> Ticket:
    """Tenant isolation + ownership enforced here: foreign-org and other customers' tickets look like 404."""
    stmt = select(Ticket).where(Ticket.id == ticket_id, Ticket.org_id == user.org_id)
    if not is_staff(user):
        stmt = stmt.where(Ticket.requester_id == user.id)
    ticket = db.scalar(stmt.options(joinedload(Ticket.requester), joinedload(Ticket.assignee)))
    if ticket is None:
        raise HTTPException(404, "Ticket not found")
    return ticket


def _log(db: Session, ticket: Ticket, actor: User, field: str, old, new) -> None:
    db.add(StatusHistory(ticket_id=ticket.id, actor_id=actor.id, field=field, old_value=None if old is None else str(old), new_value=None if new is None else str(new)))


@router.post("", response_model=TicketOut, status_code=201)
def create_ticket(data: TicketCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = utcnow()
    ticket = Ticket(
        org_id=user.org_id, requester_id=user.id, subject=data.subject, description=data.description,
        category=data.category, priority=data.priority, sla_due_at=due_date(data.priority, now), created_at=now,
    )
    db.add(ticket)
    db.flush()
    _log(db, ticket, user, "status", None, Status.open.value)
    db.commit()
    return db.scalar(select(Ticket).where(Ticket.id == ticket.id).options(joinedload(Ticket.requester), joinedload(Ticket.assignee)))


@router.get("", response_model=Page)
def list_tickets(
    status: Status | None = None,
    priority: Priority | None = None,
    assignee_id: int | None = None,
    q: str | None = Query(None, max_length=100),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sla_breached: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conds = [Ticket.org_id == user.org_id]
    if not is_staff(user):
        conds.append(Ticket.requester_id == user.id)
    if status:
        conds.append(Ticket.status == status)
    if priority:
        conds.append(Ticket.priority == priority)
    if assignee_id is not None and is_staff(user):
        conds.append(Ticket.assignee_id == assignee_id)
    if date_from:
        conds.append(Ticket.created_at >= date_from)
    if date_to:
        conds.append(Ticket.created_at <= date_to)
    if sla_breached is not None:
        conds.append(Ticket.sla_breached.is_(sla_breached))
    if q:
        if db.bind.dialect.name == "postgresql":
            doc = func.to_tsvector("english", Ticket.subject + " " + Ticket.description)
            conds.append(doc.op("@@")(func.plainto_tsquery("english", q)))
        else:  # SQLite fallback used in tests
            like = f"%{q}%"
            conds.append(Ticket.subject.ilike(like) | Ticket.description.ilike(like))

    total = db.scalar(select(func.count()).select_from(Ticket).where(*conds)) or 0
    items = db.scalars(
        select(Ticket).where(*conds)
        .options(joinedload(Ticket.requester), joinedload(Ticket.assignee))  # no N+1
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())
        .limit(page_size).offset((page - 1) * page_size)
    ).all()
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ticket = get_ticket_or_404(db, ticket_id, user)
    comments = db.scalars(
        select(Comment).where(Comment.ticket_id == ticket.id).options(joinedload(Comment.author)).order_by(Comment.created_at, Comment.id)
    ).all()
    if not is_staff(user):
        comments = [c for c in comments if not c.is_internal]
    history = db.scalars(
        select(StatusHistory).where(StatusHistory.ticket_id == ticket.id).options(joinedload(StatusHistory.actor)).order_by(StatusHistory.created_at, StatusHistory.id)
    ).all()
    return TicketDetail.model_validate({**TicketOut.model_validate(ticket).model_dump(), "comments": comments, "history": history})


@router.patch("/{ticket_id}", response_model=TicketOut)
def update_ticket(
    ticket_id: int, data: TicketUpdate, bg: BackgroundTasks,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(db, ticket_id, user)
    staff = is_staff(user)
    old_status = ticket.status

    if (data.priority or data.assignee_id is not None or data.unassign) and not staff:
        raise HTTPException(403, "Only staff can change priority or assignee")

    if data.status and data.status != ticket.status:
        if data.status not in TRANSITIONS[ticket.status]:
            raise HTTPException(409, f"Cannot move ticket from {ticket.status.value} to {data.status.value}")
        if not staff and (ticket.status, data.status) not in CUSTOMER_TRANSITIONS:
            raise HTTPException(403, "Customers can only close or reopen their tickets")
        _log(db, ticket, user, "status", ticket.status.value, data.status.value)
        ticket.status = data.status
        if data.status == Status.resolved:
            ticket.resolved_at = utcnow()
            if utcnow() > as_utc(ticket.sla_due_at):
                ticket.sla_breached = True
        elif data.status == Status.open:
            ticket.resolved_at = None

    if data.priority and data.priority != ticket.priority:
        _log(db, ticket, user, "priority", ticket.priority.value, data.priority.value)
        ticket.priority = data.priority
        ticket.sla_due_at = due_date(data.priority, as_utc(ticket.created_at))

    if data.unassign and ticket.assignee_id is not None:
        _log(db, ticket, user, "assignee", ticket.assignee_id, None)
        ticket.assignee_id = None
    elif data.assignee_id is not None and data.assignee_id != ticket.assignee_id:
        assignee = db.scalar(select(User).where(User.id == data.assignee_id, User.org_id == user.org_id, User.is_active.is_(True)))
        if assignee is None or assignee.role == Role.customer:
            raise HTTPException(422, "Assignee must be an active agent or admin in your organization")
        _log(db, ticket, user, "assignee", ticket.assignee_id, assignee.id)
        ticket.assignee_id = assignee.id
        if ticket.status == Status.open and not data.status:
            _log(db, ticket, user, "status", Status.open.value, Status.in_progress.value)
            ticket.status = Status.in_progress

    db.commit()
    db.refresh(ticket)
    if ticket.status != old_status:
        bg.add_task(send_email, ticket.requester.email, f"[#{ticket.id}] Status: {ticket.status.value}", f"Your ticket '{ticket.subject}' is now {ticket.status.value}.")
    return ticket


@router.post("/{ticket_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    ticket_id: int, data: CommentCreate, bg: BackgroundTasks,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(db, ticket_id, user)
    if data.is_internal and not is_staff(user):
        raise HTTPException(403, "Only staff can post internal notes")
    if ticket.status == Status.closed:
        raise HTTPException(409, "Ticket is closed; reopen it to comment")
    comment = Comment(ticket_id=ticket.id, author_id=user.id, body=data.body, is_internal=data.is_internal)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    if is_staff(user) and not data.is_internal:
        bg.add_task(send_email, ticket.requester.email, f"[#{ticket.id}] New reply", f"{user.full_name} replied:\n\n{data.body}")
    return db.scalar(select(Comment).where(Comment.id == comment.id).options(joinedload(Comment.author)))
