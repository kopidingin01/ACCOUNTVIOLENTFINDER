from models.enums import ReadinessLevel
from models.user import Role

from conftest import auth_headers, login, make_user
from services import report_service


def test_readiness_scoring_weights_and_levels():
    full_checklist = {
        "target": True, "content": True, "evidence": True, "source_verified": True,
        "timestamp": True, "policy": True, "context": True, "integrity": True,
        "human_review": True, "duplicate_check": True,
    }
    score, level, missing = report_service.compute_readiness(full_checklist)
    assert score == 100.0
    assert level == ReadinessLevel.READY
    assert missing == []

    no_review_checklist = dict(full_checklist, human_review=False)
    score, level, missing = report_service.compute_readiness(no_review_checklist)
    assert score == 90.0
    assert level == ReadinessLevel.NEEDS_REVIEW  # READY requires human_review specifically
    assert "Human review completed" in missing

    bare_checklist = {k: False for k in full_checklist}
    score, level, missing = report_service.compute_readiness(bare_checklist)
    assert score == 0.0
    assert level == ReadinessLevel.INSUFFICIENT
    assert len(missing) == len(full_checklist)


def _setup_case_with_evidence(client, admin_token, analyst_token, suffix=""):
    platform = client.post(
        "/api/platforms",
        headers=auth_headers(admin_token),
        json={"name": f"ReportPlatform{suffix}", "domain": f"report-platform{suffix}.example"},
    ).json()
    case = client.post(
        "/api/cases",
        headers=auth_headers(analyst_token),
        json={"title": "Report test case", "platform_id": platform["id"]},
    ).json()
    ev = client.post(
        "/api/evidence",
        headers=auth_headers(analyst_token),
        data={
            "case_id": case["id"],
            "type": "PUBLIC_POST",
            "source_url": f"https://report-platform{suffix}.example/post/1",
            "description": "Some evidence description",
        },
    ).json()
    client.post(f"/api/evidence/{ev['id']}/verify", headers=auth_headers(analyst_token), json={})
    return case


def test_duplicate_report_detected_on_second_generation(client, SessionLocal):
    make_user(SessionLocal, "admin_rd1", Role.ADMIN)
    make_user(SessionLocal, "analyst_rd1", Role.ANALYST)
    admin_token = login(client, "admin_rd1")
    analyst_token = login(client, "analyst_rd1")
    case = _setup_case_with_evidence(client, admin_token, analyst_token, suffix="1")

    first = client.post("/api/reports", headers=auth_headers(analyst_token), json={"case_id": case["id"]})
    assert first.status_code == 201
    first_report_number = first.json()["report_number"]

    second = client.post("/api/reports", headers=auth_headers(analyst_token), json={"case_id": case["id"]})
    assert second.status_code == 409
    detail = second.json()["detail"]
    assert detail["error"] == "DUPLICATE_REPORT_DETECTED"
    assert detail["existing_report_id"] == first_report_number


def test_report_submission_blocked_until_ready(client, SessionLocal):
    make_user(SessionLocal, "admin_rd2", Role.ADMIN)
    make_user(SessionLocal, "analyst_rd2", Role.ANALYST)
    admin_token = login(client, "admin_rd2")
    analyst_token = login(client, "analyst_rd2")
    case = _setup_case_with_evidence(client, admin_token, analyst_token, suffix="2")

    report = client.post("/api/reports", headers=auth_headers(analyst_token), json={"case_id": case["id"]}).json()
    # No assessment/policy match/human review yet -> not READY.
    assert report["readiness_level"] != "READY"

    submit = client.post(
        f"/api/reports/{report['id']}/submit",
        headers=auth_headers(analyst_token),
        json={"method": "MANUAL"},
    )
    assert submit.status_code == 400
    assert submit.json()["detail"]["error"] == "REPORT_NOT_READY"


def test_readiness_preview_available_before_report_exists(client, SessionLocal):
    make_user(SessionLocal, "admin_rd4", Role.ADMIN)
    make_user(SessionLocal, "analyst_rd4", Role.ANALYST)
    admin_token = login(client, "admin_rd4")
    analyst_token = login(client, "analyst_rd4")

    platform = client.post(
        "/api/platforms",
        headers=auth_headers(admin_token),
        json={"name": "ReadinessPlatform", "domain": "readiness-platform.example"},
    ).json()
    case = client.post(
        "/api/cases",
        headers=auth_headers(analyst_token),
        json={"title": "Readiness preview case", "platform_id": platform["id"]},
    ).json()

    # Before any evidence exists at all.
    empty_preview = client.get(f"/api/cases/{case['id']}/readiness", headers=auth_headers(analyst_token)).json()
    assert empty_preview["level"] == "INSUFFICIENT"
    assert empty_preview["score"] == 0.0
    assert any(item["key"] == "evidence" and not item["met"] for item in empty_preview["items"])

    # No Report row should exist yet from just previewing.
    reports = client.get("/api/reports", headers=auth_headers(analyst_token), params={"case_id": case["id"]}).json()
    assert reports == []

    ev = client.post(
        "/api/evidence",
        headers=auth_headers(analyst_token),
        data={
            "case_id": case["id"],
            "type": "PUBLIC_POST",
            "source_url": "https://readiness-platform.example/post/1",
            "description": "Some context here",
        },
    ).json()
    client.post(f"/api/evidence/{ev['id']}/verify", headers=auth_headers(analyst_token), json={})

    better_preview = client.get(f"/api/cases/{case['id']}/readiness", headers=auth_headers(analyst_token)).json()
    assert better_preview["score"] > empty_preview["score"]
    assert any(item["key"] == "evidence" and item["met"] for item in better_preview["items"])


def test_report_policy_citation_includes_full_reference(client, SessionLocal):
    make_user(SessionLocal, "admin_rd5", Role.ADMIN)
    make_user(SessionLocal, "analyst_rd5", Role.ANALYST)
    admin_token = login(client, "admin_rd5")
    analyst_token = login(client, "analyst_rd5")

    platform = client.post(
        "/api/platforms",
        headers=auth_headers(admin_token),
        json={"name": "CitationPlatform", "domain": "citation-platform.example"},
    ).json()
    policy = client.post(
        "/api/policies",
        headers=auth_headers(admin_token),
        json={"platform_id": platform["id"], "name": "Community Guidelines", "policy_url": "https://citation-platform.example/rules"},
    ).json()
    rule = client.post(
        "/api/policies/rules",
        headers=auth_headers(admin_token),
        json={
            "policy_id": policy["id"],
            "rule_code": "POL-CITE-1",
            "category": "SPAM",
            "description": "Repetitive unsolicited promotional content.",
            "severity": "LOW",
            "keywords": "promo gratis",
        },
    ).json()
    case = client.post(
        "/api/cases",
        headers=auth_headers(analyst_token),
        json={"title": "Citation test case", "platform_id": platform["id"]},
    ).json()
    ev = client.post(
        "/api/evidence",
        headers=auth_headers(analyst_token),
        data={
            "case_id": case["id"],
            "type": "PUBLIC_POST",
            "source_url": "https://citation-platform.example/post/1",
            "description": "promo gratis klaim sekarang",
        },
    ).json()
    client.post(f"/api/evidence/{ev['id']}/verify", headers=auth_headers(analyst_token), json={})
    assessment = client.post("/api/assessments", headers=auth_headers(analyst_token), json={"case_id": case["id"]}).json()[0]

    report = client.post(
        "/api/reports",
        headers=auth_headers(analyst_token),
        json={"case_id": case["id"], "assessment_id": assessment["id"]},
    ).json()

    relevant_policy = report["body"]["relevant_policy"]
    assert relevant_policy["policy_name"] == "Community Guidelines"
    assert relevant_policy["policy_url"] == "https://citation-platform.example/rules"
    assert relevant_policy["rule_code"] == "POL-CITE-1"
    assert "Community Guidelines" in relevant_policy["citation"]
    assert "POL-CITE-1" in relevant_policy["citation"]


def test_report_export_formats(client, SessionLocal):
    make_user(SessionLocal, "admin_rd3", Role.ADMIN)
    make_user(SessionLocal, "analyst_rd3", Role.ANALYST)
    admin_token = login(client, "admin_rd3")
    analyst_token = login(client, "analyst_rd3")
    case = _setup_case_with_evidence(client, admin_token, analyst_token, suffix="3")
    report = client.post("/api/reports", headers=auth_headers(analyst_token), json={"case_id": case["id"]}).json()

    json_resp = client.get(f"/api/reports/{report['id']}/export/json", headers=auth_headers(analyst_token))
    assert json_resp.status_code == 200
    assert json_resp.headers["content-type"].startswith("application/json")

    pdf_resp = client.get(f"/api/reports/{report['id']}/export/pdf", headers=auth_headers(analyst_token))
    assert pdf_resp.status_code == 200
    assert pdf_resp.content[:4] == b"%PDF"

    csv_resp = client.get(f"/api/reports/{report['id']}/export/csv", headers=auth_headers(analyst_token))
    assert csv_resp.status_code == 200
    assert b"report_id" in csv_resp.content

    bad_resp = client.get(f"/api/reports/{report['id']}/export/exe", headers=auth_headers(analyst_token))
    assert bad_resp.status_code == 400
