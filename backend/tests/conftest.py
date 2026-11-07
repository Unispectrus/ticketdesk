import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.security import login_limiter


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    login_limiter.reset()
    yield TestClient(app)
    app.dependency_overrides.clear()


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture()
def make_org(client):
    """Creates an org with admin; returns (slug, admin_headers)."""

    def _make(slug="acme", email="admin@acme.com"):
        r = client.post("/auth/register-org", json={"org_name": slug.title(), "org_slug": slug, "full_name": "Admin", "email": email, "password": "password123"})
        assert r.status_code == 201, r.text
        return slug, _auth(r.json())

    return _make


@pytest.fixture()
def make_user(client):
    """Registers a customer, optionally promoted by admin headers to a role. Returns (headers, id)."""

    def _make(slug, email, admin_headers=None, role="customer"):
        r = client.post("/auth/register", json={"org_slug": slug, "full_name": email.split("@")[0], "email": email, "password": "password123"})
        assert r.status_code == 201, r.text
        headers = _auth(r.json())
        uid = client.get("/auth/me", headers=headers).json()["id"]
        if role != "customer":
            assert client.patch(f"/admin/users/{uid}", json={"role": role}, headers=admin_headers).status_code == 200
        return headers, uid

    return _make
