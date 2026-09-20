from models.user import Role

from conftest import auth_headers, login, make_user


def test_credential_value_never_returned_and_only_admin_can_manage(client, SessionLocal):
    make_user(SessionLocal, "admin_cred1", Role.ADMIN)
    make_user(SessionLocal, "analyst_cred1", Role.ANALYST)
    admin_token = login(client, "admin_cred1")
    analyst_token = login(client, "analyst_cred1")

    platform = client.post(
        "/api/platforms",
        headers=auth_headers(admin_token),
        json={"name": "CredPlatform", "domain": "cred-platform.example", "has_official_api": True},
    ).json()

    # Analyst cannot manage credentials.
    resp = client.post(
        f"/api/platforms/{platform['id']}/credentials",
        headers=auth_headers(analyst_token),
        json={"credential_type": "api_key", "value": "super-secret-value"},
    )
    assert resp.status_code == 403

    created = client.post(
        f"/api/platforms/{platform['id']}/credentials",
        headers=auth_headers(admin_token),
        json={"credential_type": "api_key", "value": "super-secret-value"},
    )
    assert created.status_code == 201
    body = created.json()
    assert "value" not in body
    assert "encrypted_value" not in body
    assert body["credential_type"] == "api_key"

    listed = client.get(f"/api/platforms/{platform['id']}/credentials", headers=auth_headers(admin_token)).json()
    assert len(listed) == 1
    assert "value" not in listed[0]
    assert "encrypted_value" not in listed[0]
