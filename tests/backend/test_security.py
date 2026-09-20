from models.user import Role

from conftest import auth_headers, login, make_user


def test_sql_injection_style_query_param_is_safely_parameterized(client, SessionLocal):
    """SQLAlchemy's query builder parameterizes all filter values, so a
    classic injection payload in a query string is treated as a literal
    string to match against — never as SQL. This should return an empty,
    well-formed result, not a 500 or unexpected data dump."""
    make_user(SessionLocal, "admin_sec1", Role.ADMIN)
    token = login(client, "admin_sec1")

    payload = "x' OR '1'='1"
    resp = client.get("/api/cases", params={"platform_id": payload}, headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_xss_payload_in_case_description_is_stored_and_returned_literally(client, SessionLocal):
    """The API is a JSON service, not an HTML renderer: a script-tag payload
    must round-trip as inert text data, never be interpreted, stripped
    silently in a way that hides tampering, or cause a server error."""
    make_user(SessionLocal, "admin_sec2", Role.ADMIN)
    token = login(client, "admin_sec2")

    platform = client.post(
        "/api/platforms",
        headers=auth_headers(token),
        json={"name": "SecPlatform", "domain": "sec-platform.example"},
    ).json()

    payload = "<script>alert('xss')</script>"
    case = client.post(
        "/api/cases",
        headers=auth_headers(token),
        json={"title": "XSS test", "platform_id": platform["id"], "description": payload},
    ).json()
    assert case["description"] == payload

    fetched = client.get(f"/api/cases/{case['id']}", headers=auth_headers(token)).json()
    assert fetched["description"] == payload


def test_path_traversal_in_evidence_file_lookup_returns_404_not_arbitrary_file(client, SessionLocal):
    make_user(SessionLocal, "admin_sec3", Role.ADMIN)
    token = login(client, "admin_sec3")
    resp = client.get("/api/evidence/../../../../etc/passwd/file", headers=auth_headers(token))
    assert resp.status_code in (404, 422)


def test_missing_or_malformed_token_rejected(client):
    resp = client.get("/api/cases", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401

    resp = client.get("/api/cases", headers={"Authorization": "not-even-bearer-format"})
    assert resp.status_code == 401


def test_evidence_upload_rejects_oversized_declared_type_mismatch(client, SessionLocal):
    """A file whose Content-Type is not on the evidence MIME allowlist must
    be rejected even if the extension looks fine, so an attacker can't
    smuggle an executable by just renaming its extension and Content-Type."""
    import io

    make_user(SessionLocal, "admin_sec4", Role.ADMIN)
    make_user(SessionLocal, "analyst_sec4", Role.ANALYST)
    admin_token = login(client, "admin_sec4")
    analyst_token = login(client, "analyst_sec4")
    platform = client.post(
        "/api/platforms",
        headers=auth_headers(admin_token),
        json={"name": "SecPlatform2", "domain": "sec-platform2.example"},
    ).json()
    case = client.post(
        "/api/cases",
        headers=auth_headers(analyst_token),
        json={"title": "Sec case", "platform_id": platform["id"]},
    ).json()

    resp = client.post(
        "/api/evidence",
        headers=auth_headers(analyst_token),
        data={"case_id": case["id"], "type": "SCREENSHOT", "source_url": "https://sec-platform2.example/post/1"},
        files={"file": ("shot.png", io.BytesIO(b"not really a png"), "application/x-msdownload")},
    )
    assert resp.status_code == 400
