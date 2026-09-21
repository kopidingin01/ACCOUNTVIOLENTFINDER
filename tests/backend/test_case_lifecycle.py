from models.user import Role

from conftest import auth_headers, login, make_user


def _setup_full_case(client, admin_token, analyst_token, suffix):
    platform = client.post(
        "/api/platforms",
        headers=auth_headers(admin_token),
        json={"name": f"LifecyclePlatform{suffix}", "domain": f"lifecycle-platform{suffix}.example"},
    ).json()
    case = client.post(
        "/api/cases",
        headers=auth_headers(analyst_token),
        json={"title": "Lifecycle test case", "platform_id": platform["id"]},
    ).json()
    ev = client.post(
        "/api/evidence",
        headers=auth_headers(analyst_token),
        data={
            "case_id": case["id"],
            "type": "PUBLIC_POST",
            "source_url": f"https://lifecycle-platform{suffix}.example/post/1",
            "description": "Some evidence description",
        },
    ).json()
    client.post(f"/api/evidence/{ev['id']}/verify", headers=auth_headers(analyst_token), json={})
    client.post("/api/assessments", headers=auth_headers(analyst_token), json={"case_id": case["id"]})
    client.post("/api/reports", headers=auth_headers(analyst_token), json={"case_id": case["id"]})
    return case


def test_update_case_status_reject_and_close(client, SessionLocal):
    make_user(SessionLocal, "admin_cl1", Role.ADMIN)
    make_user(SessionLocal, "analyst_cl1", Role.ANALYST)
    admin_token = login(client, "admin_cl1")
    analyst_token = login(client, "analyst_cl1")
    case = _setup_full_case(client, admin_token, analyst_token, "1")

    resp = client.patch(
        f"/api/cases/{case['id']}",
        headers=auth_headers(analyst_token),
        json={"status": "REJECTED", "description": "Duplicate of another case"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "REJECTED"
    assert body["description"] == "Duplicate of another case"


def test_delete_case_requires_admin(client, SessionLocal):
    make_user(SessionLocal, "admin_cl2", Role.ADMIN)
    make_user(SessionLocal, "analyst_cl2", Role.ANALYST)
    admin_token = login(client, "admin_cl2")
    analyst_token = login(client, "analyst_cl2")
    case = _setup_full_case(client, admin_token, analyst_token, "2")

    resp = client.delete(f"/api/cases/{case['id']}", headers=auth_headers(analyst_token))
    assert resp.status_code == 403

    still_there = client.get(f"/api/cases/{case['id']}", headers=auth_headers(analyst_token))
    assert still_there.status_code == 200


def test_delete_case_cascades_to_children(client, SessionLocal):
    make_user(SessionLocal, "admin_cl3", Role.ADMIN)
    make_user(SessionLocal, "analyst_cl3", Role.ANALYST)
    admin_token = login(client, "admin_cl3")
    analyst_token = login(client, "analyst_cl3")
    case = _setup_full_case(client, admin_token, analyst_token, "3")

    assert client.get("/api/evidence", headers=auth_headers(admin_token), params={"case_id": case["id"]}).json()
    assert client.get("/api/assessments", headers=auth_headers(admin_token), params={"case_id": case["id"]}).json()
    assert client.get("/api/reports", headers=auth_headers(admin_token), params={"case_id": case["id"]}).json()

    resp = client.delete(f"/api/cases/{case['id']}", headers=auth_headers(admin_token))
    assert resp.status_code == 204

    assert client.get(f"/api/cases/{case['id']}", headers=auth_headers(admin_token)).status_code == 404
    assert client.get("/api/evidence", headers=auth_headers(admin_token), params={"case_id": case["id"]}).json() == []
    assert client.get("/api/reports", headers=auth_headers(admin_token), params={"case_id": case["id"]}).json() == []

    audit = client.get("/api/audit?resource_type=case", headers=auth_headers(admin_token)).json()
    deleted_entries = [a for a in audit if a["resource_id"] == case["case_number"] and a["action"] == "CASE_DELETED"]
    assert len(deleted_entries) == 1
