from models.user import Role

from conftest import auth_headers, login, make_user


def test_login_success_and_me(client, SessionLocal):
    make_user(SessionLocal, "admin1", Role.ADMIN)
    token = login(client, "admin1")
    resp = client.get("/api/auth/me", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin1"
    assert resp.json()["role"] == "ADMIN"


def test_login_wrong_password_rejected(client, SessionLocal):
    make_user(SessionLocal, "admin2", Role.ADMIN)
    resp = client.post("/api/auth/login", json={"username": "admin2", "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_unknown_user_rejected(client):
    resp = client.post("/api/auth/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


def test_login_inactive_user_rejected(client, SessionLocal):
    user = make_user(SessionLocal, "inactive1", Role.ANALYST)
    db = SessionLocal()
    db.query(type(user)).filter_by(id=user.id).update({"is_active": False})
    db.commit()
    db.close()
    resp = client.post("/api/auth/login", json={"username": "inactive1", "password": "TestPass123!"})
    assert resp.status_code == 401


def test_unauthenticated_request_rejected(client):
    resp = client.get("/api/cases")
    assert resp.status_code == 401


def test_viewer_cannot_create_case(client, SessionLocal):
    make_user(SessionLocal, "viewerX", Role.VIEWER)
    token = login(client, "viewerX")
    resp = client.post(
        "/api/cases",
        headers=auth_headers(token),
        json={"title": "x", "platform_id": "does-not-matter"},
    )
    assert resp.status_code == 403


def test_analyst_can_create_case_but_not_manage_policies(client, SessionLocal):
    make_user(SessionLocal, "analystX", Role.ANALYST)
    make_user(SessionLocal, "adminX", Role.ADMIN)
    admin_token = login(client, "adminX")
    platform = client.post(
        "/api/platforms",
        headers=auth_headers(admin_token),
        json={"name": "Platform X", "domain": "platform-x.example"},
    ).json()

    analyst_token = login(client, "analystX")
    resp = client.post(
        "/api/cases",
        headers=auth_headers(analyst_token),
        json={"title": "Analyst-created case", "platform_id": platform["id"]},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "NEW"

    # Analysts cannot create policies (admin-only in this system).
    resp = client.post(
        "/api/policies",
        headers=auth_headers(analyst_token),
        json={"platform_id": platform["id"], "name": "Some Policy"},
    )
    assert resp.status_code == 403


def test_reviewer_cannot_create_case_but_can_read_review_queue(client, SessionLocal):
    make_user(SessionLocal, "reviewerX", Role.REVIEWER)
    token = login(client, "reviewerX")
    resp = client.post("/api/cases", headers=auth_headers(token), json={"title": "x", "platform_id": "y"})
    assert resp.status_code == 403

    resp = client.get("/api/reviews", headers=auth_headers(token))
    assert resp.status_code == 200


def test_auditor_can_read_audit_log_others_cannot(client, SessionLocal):
    make_user(SessionLocal, "auditorX", Role.AUDITOR)
    make_user(SessionLocal, "viewerY", Role.VIEWER)

    auditor_token = login(client, "auditorX")
    resp = client.get("/api/audit", headers=auth_headers(auditor_token))
    assert resp.status_code == 200

    viewer_token = login(client, "viewerY")
    resp = client.get("/api/audit", headers=auth_headers(viewer_token))
    assert resp.status_code == 403


def test_admin_has_full_access(client, SessionLocal):
    make_user(SessionLocal, "superadmin", Role.ADMIN)
    token = login(client, "superadmin")
    for path in ["/api/cases", "/api/reviews", "/api/audit", "/api/platforms"]:
        resp = client.get(path, headers=auth_headers(token))
        assert resp.status_code == 200, f"{path} -> {resp.status_code}"
