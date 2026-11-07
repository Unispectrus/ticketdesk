from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import Priority, Role, Status


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth ---
class RegisterOrg(BaseModel):
    org_name: str = Field(min_length=2, max_length=120)
    org_slug: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9-]+$")
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegisterCustomer(BaseModel):
    org_slug: str
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class Login(BaseModel):
    org_slug: str
    email: EmailStr
    password: str


class Refresh(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    org_id: int


class UserBrief(ORM):
    id: int
    full_name: str
    role: Role


# --- tickets ---
class TicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    category: str = Field(default="general", max_length=50)
    priority: Priority = Priority.medium


class TicketUpdate(BaseModel):
    status: Status | None = None
    priority: Priority | None = None
    assignee_id: int | None = None
    unassign: bool = False


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)
    is_internal: bool = False


class CommentOut(ORM):
    id: int
    body: str
    is_internal: bool
    created_at: datetime
    author: UserBrief


class HistoryOut(ORM):
    id: int
    field: str
    old_value: str | None
    new_value: str | None
    created_at: datetime
    actor: UserBrief


class TicketOut(ORM):
    id: int
    subject: str
    description: str
    category: str
    status: Status
    priority: Priority
    created_at: datetime
    updated_at: datetime
    sla_due_at: datetime
    sla_breached: bool
    resolved_at: datetime | None
    requester: UserBrief
    assignee: UserBrief | None


class TicketDetail(TicketOut):
    comments: list[CommentOut]
    history: list[HistoryOut]


class Page(BaseModel):
    items: list[TicketOut]
    total: int
    page: int
    page_size: int


# --- admin ---
class UserAdminUpdate(BaseModel):
    role: Role | None = None
    is_active: bool | None = None


class SlaReport(BaseModel):
    total_tickets: int
    breached: int
    open_overdue: int
    breach_rate: float
    by_priority: dict[str, dict[str, int]]
