from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin, require_staff
from ..models import Role, Status, Ticket, User, utcnow
from ..schemas import SlaReport, UserAdminUpdate, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(role: Role | None = None, admin: User = Depends(require_staff), db: Session = Depends(get_db)):
    """Staff can list users (needed to assign tickets); only admins can modify them."""
    stmt = select(User).where(User.org_id == admin.org_id).order_by(User.id)
    if role:
        stmt = stmt.where(User.role == role)
    return db.scalars(stmt).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserAdminUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.id == user_id, User.org_id == admin.org_id))
    if user is None:
        raise HTTPException(404, "User not found")
    if user.id == admin.id and (data.role not in (None, Role.admin) or data.is_active is False):
        raise HTTPException(409, "You cannot demote or deactivate yourself")
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    db.commit()
    return user


@router.get("/reports/sla", response_model=SlaReport)
def sla_report(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    now = utcnow()
    rows = db.execute(
        select(
            Ticket.priority,
            func.count().label("total"),
            func.sum(case((Ticket.sla_breached.is_(True), 1), else_=0)).label("breached"),
            func.sum(case(((Ticket.status.in_([Status.open, Status.in_progress])) & (Ticket.sla_due_at < now), 1), else_=0)).label("overdue"),
        ).where(Ticket.org_id == admin.org_id).group_by(Ticket.priority)
    ).all()
    total = sum(r.total for r in rows)
    breached = sum(int(r.breached or 0) for r in rows)
    overdue = sum(int(r.overdue or 0) for r in rows)
    return SlaReport(
        total_tickets=total,
        breached=breached,
        open_overdue=overdue,
        breach_rate=round(breached / total, 3) if total else 0.0,
        by_priority={r.priority.value: {"total": r.total, "breached": int(r.breached or 0)} for r in rows},
    )
