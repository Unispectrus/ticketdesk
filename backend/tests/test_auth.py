import jwt

from app.config import settings


def test_register_login_me(client, make_org):
    slug, _ = make_org()
    client.post("/auth/register", json={"org_slug": slug, "full_name": "Cu", "email": "Cu@x.com", "password": "password123"})
    r = client.post("/auth/login", json={"org_slug": slug, "email": "cu@x.com", "password": "password123"})
    assert r.status_code == 200
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["role"] == "customer" and me["email"] == "cu@x.com"


def test_wrong_password_and_unknown_user_same_error(client, make_org):
    slug, _ = make_org()
    a = client.post("/auth/login", json={"org_slug": slug, "email": "admin@acme.com", "password": "wrong-pass"})
    b = client.post("/auth/login", json={"org_slug": slug, "email": "nobody@acme.com", "password": "wrong-pass"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_duplicate_email_and_slug(client, make_org):
    slug, _ = make_org()
    body = {"org_slug": slug, "full_name": "x", "email": "dup@x.com", "password": "password123"}
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 409
    assert client.post("/auth/register-org", json={"org_name": "Again", "org_slug": slug, "full_name": "a", "email": "a@b.com", "password": "password123"}).status_code == 409


def test_same_email_allowed_in_different_orgs(client, make_org):
    make_org("one"), make_org("two", "admin@two.com")
    for slug in ("one", "two"):
        r = client.post("/auth/register", json={"org_slug": slug, "full_name": "x", "email": "same@x.com", "password": "password123"})
        assert r.status_code == 201


def test_refresh_token_cannot_be_used_as_access(client, make_org):
    slug, _ = make_org()
    tokens = client.post("/auth/login", json={"org_slug": slug, "email": "admin@acme.com", "password": "password123"}).json()
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}).status_code == 401
    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401


def test_tampered_or_missing_token_rejected(client):
    assert client.get("/auth/me").status_code == 401
    bad = jwt.encode({"sub": "1", "type": "access"}, "other-secret", algorithm="HS256")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {bad}"}).status_code == 401


def test_login_rate_limit(client, make_org):
    slug, _ = make_org()
    codes = [client.post("/auth/login", json={"org_slug": slug, "email": "admin@acme.com", "password": "bad-password"}).status_code for _ in range(settings.login_rate_limit + 2)]
    assert codes[0] == 401 and codes[-1] == 429


def test_deactivated_user_locked_out(client, make_org, make_user):
    slug, admin = make_org()
    h, uid = make_user(slug, "c@x.com")
    client.patch(f"/admin/users/{uid}", json={"is_active": False}, headers=admin)
    assert client.get("/auth/me", headers=h).status_code == 401
    assert client.post("/auth/login", json={"org_slug": slug, "email": "c@x.com", "password": "password123"}).status_code == 401


def test_short_password_rejected(client, make_org):
    slug, _ = make_org()
    r = client.post("/auth/register", json={"org_slug": slug, "full_name": "x", "email": "s@x.com", "password": "short"})
    assert r.status_code == 422
