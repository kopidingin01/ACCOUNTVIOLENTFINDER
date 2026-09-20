from models.user import Role

from conftest import auth_headers, login, make_user


def test_only_admin_can_create_users(client, SessionLocal):
    make_user(SessionLocal, "admin_u1", Role.ADMIN)
    make_user(SessionLocal, "analyst_u1", Role.ANALYST)
    admin_token = login(client, "admin_u1")
    analyst_token = login(client, "analyst_u1")

    resp = client.post(
        "/api/users",
        headers=auth_headers(analyst_token),
        json={"username": "newbie", "email": "newbie@example.com", "full_name": "New Bie", "password": "SecurePass1", "role": "REVIEWER"},
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/users",
        headers=auth_headers(admin_token),
        json={"username": "newbie", "email": "newbie@example.com", "full_name": "New Bie", "password": "SecurePass1", "role": "REVIEWER"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["username"] == "newbie"
    assert body["role"] == "REVIEWER"
    assert "password" not in body
    assert "password_hash" not in body


def test_new_user_can_immediately_log_in_with_their_role(client, SessionLocal):
    make_user(SessionLocal, "admin_u2", Role.ADMIN)
    admin_token = login(client, "admin_u2")
    client.post(
        "/api/users",
        headers=auth_headers(admin_token),
        json={"username": "teammate1", "email": "teammate1@example.com", "full_name": "Team Mate", "password": "SecurePass1", "role": "ANALYST"},
    )

    token = login(client, "teammate1", password="SecurePass1")
    me = client.get("/api/auth/me", headers=auth_headers(token)).json()
    assert me["role"] == "ANALYST"

    # An analyst still cannot create other users.
    resp = client.post(
        "/api/users",
        headers=auth_headers(token),
        json={"username": "x", "email": "x@example.com", "full_name": "X", "password": "SecurePass1", "role": "VIEWER"},
    )
    assert resp.status_code == 403


def test_duplicate_username_rejected(client, SessionLocal):
    make_user(SessionLocal, "admin_u3", Role.ADMIN)
    admin_token = login(client, "admin_u3")
    payload = {"username": "dupeuser", "email": "dupe1@example.com", "full_name": "Dupe", "password": "SecurePass1", "role": "VIEWER"}
    first = client.post("/api/users", headers=auth_headers(admin_token), json=payload)
    assert first.status_code == 201

    payload2 = dict(payload, email="dupe2@example.com")
    second = client.post("/api/users", headers=auth_headers(admin_token), json=payload2)
    assert second.status_code == 409


def test_admin_can_deactivate_user(client, SessionLocal):
    make_user(SessionLocal, "admin_u4", Role.ADMIN)
    admin_token = login(client, "admin_u4")
    created = client.post(
        "/api/users",
        headers=auth_headers(admin_token),
        json={"username": "todeactivate", "email": "todeactivate@example.com", "full_name": "To Deactivate", "password": "SecurePass1", "role": "VIEWER"},
    ).json()

    resp = client.patch(f"/api/users/{created['id']}", headers=auth_headers(admin_token), json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    login_resp = client.post("/api/auth/login", json={"username": "todeactivate", "password": "SecurePass1"})
    assert login_resp.status_code == 401
