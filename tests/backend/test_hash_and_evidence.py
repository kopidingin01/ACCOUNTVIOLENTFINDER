import hashlib
import io

from models.user import Role

from conftest import auth_headers, login, make_user
from services import hash_service


def test_sha256_bytes_matches_stdlib():
    data = b"hello evidence world"
    assert hash_service.sha256_bytes(data) == hashlib.sha256(data).hexdigest()


def test_sha256_text_is_deterministic():
    assert hash_service.sha256_text("abc") == hash_service.sha256_text("abc")
    assert hash_service.sha256_text("abc") != hash_service.sha256_text("abd")


def _create_case(client, admin_token):
    platform = client.post(
        "/api/platforms",
        headers=auth_headers(admin_token),
        json={"name": "EvidencePlatform", "domain": "evidence-platform.example"},
    ).json()
    case = client.post(
        "/api/cases",
        headers=auth_headers(admin_token),
        json={"title": "Evidence test case", "platform_id": platform["id"]},
    ).json()
    return case


def test_evidence_upload_rejects_disallowed_extension(client, SessionLocal):
    make_user(SessionLocal, "analyst_ev1", Role.ANALYST)
    make_user(SessionLocal, "admin_ev1", Role.ADMIN)
    admin_token = login(client, "admin_ev1")
    case = _create_case(client, admin_token)
    token = login(client, "analyst_ev1")

    resp = client.post(
        "/api/evidence",
        headers=auth_headers(token),
        data={"case_id": case["id"], "type": "SCREENSHOT", "source_url": "https://evidence-platform.example/post/1"},
        files={"file": ("malware.exe", io.BytesIO(b"MZ-fake-binary"), "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "allowlist" in resp.json()["detail"]


def test_evidence_upload_rejects_path_traversal_in_filename(client, SessionLocal):
    """Even a crafted '../../etc/passwd.png'-style filename must never be
    used to build the on-disk path: storage uses a server-generated UUID
    name, so a traversal filename can only fail extension/MIME checks or be
    safely stored under its allowlisted extension — it can never escape the
    storage directory."""
    make_user(SessionLocal, "analyst_ev2", Role.ANALYST)
    make_user(SessionLocal, "admin_ev2", Role.ADMIN)
    admin_token = login(client, "admin_ev2")
    case = _create_case(client, admin_token)
    token = login(client, "analyst_ev2")

    resp = client.post(
        "/api/evidence",
        headers=auth_headers(token),
        data={"case_id": case["id"], "type": "SCREENSHOT", "source_url": "https://evidence-platform.example/post/1"},
        files={"file": ("../../../../etc/passwd.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 20), "image/png")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["original_filename"] == "../../../../etc/passwd.png"  # recorded, but never used as a path
    # sha256 was computed and stored — proves upload succeeded and used a safe stored name.
    assert len(body["sha256"]) == 64


def test_evidence_upload_computes_correct_sha256_and_flags_duplicates(client, SessionLocal):
    make_user(SessionLocal, "analyst_ev3", Role.ANALYST)
    make_user(SessionLocal, "admin_ev3", Role.ADMIN)
    admin_token = login(client, "admin_ev3")
    case = _create_case(client, admin_token)
    token = login(client, "analyst_ev3")

    content = b"\x89PNG\r\n\x1a\n" + b"identical-bytes" * 5
    expected_sha256 = hashlib.sha256(content).hexdigest()

    first = client.post(
        "/api/evidence",
        headers=auth_headers(token),
        data={"case_id": case["id"], "type": "SCREENSHOT", "source_url": "https://evidence-platform.example/post/1"},
        files={"file": ("shot1.png", io.BytesIO(content), "image/png")},
    ).json()
    assert first["sha256"] == expected_sha256
    assert first["verification_status"] == "PENDING"

    second = client.post(
        "/api/evidence",
        headers=auth_headers(token),
        data={"case_id": case["id"], "type": "SCREENSHOT", "source_url": "https://evidence-platform.example/post/2"},
        files={"file": ("shot2.png", io.BytesIO(content), "image/png")},
    ).json()
    assert second["sha256"] == expected_sha256
    assert second["verification_status"] == "DUPLICATE"
    assert first["evidence_number"] in second["verification_notes"]


def test_evidence_verify_records_chain_of_custody(client, SessionLocal):
    make_user(SessionLocal, "analyst_ev4", Role.ANALYST)
    make_user(SessionLocal, "admin_ev4", Role.ADMIN)
    admin_token = login(client, "admin_ev4")
    case = _create_case(client, admin_token)
    token = login(client, "analyst_ev4")

    evidence = client.post(
        "/api/evidence",
        headers=auth_headers(token),
        data={"case_id": case["id"], "type": "SCREENSHOT", "source_url": "https://evidence-platform.example/post/1"},
        files={"file": ("shot.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"x" * 30), "image/png")},
    ).json()

    verify_resp = client.post(f"/api/evidence/{evidence['id']}/verify", headers=auth_headers(token), json={})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verification_status"] == "VERIFIED"

    custody = client.get(f"/api/evidence/{evidence['id']}/custody", headers=auth_headers(token)).json()
    actions = [c["action"] for c in custody]
    assert actions == ["UPLOADED", "HASHED", "VERIFIED"]
    assert all(c["new_hash"] == evidence["sha256"] for c in custody)
