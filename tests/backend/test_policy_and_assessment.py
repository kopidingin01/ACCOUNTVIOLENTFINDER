from models.enums import ViolationCategory
from models.user import Role

from conftest import auth_headers, login, make_user


def _setup_case_with_policy(client, admin_token, analyst_token, keywords="bunuh,ancam"):
    platform = client.post(
        "/api/platforms",
        headers=auth_headers(admin_token),
        json={"name": "PolicyPlatform", "domain": "policy-platform.example"},
    ).json()
    policy = client.post(
        "/api/policies",
        headers=auth_headers(admin_token),
        json={"platform_id": platform["id"], "name": "Test Guidelines"},
    ).json()
    rule = client.post(
        "/api/policies/rules",
        headers=auth_headers(admin_token),
        json={
            "policy_id": policy["id"],
            "rule_code": "POL-TEST-1",
            "category": ViolationCategory.THREATS.value,
            "description": "Explicit threats of harm.",
            "severity": "CRITICAL",
            "keywords": keywords,
        },
    ).json()
    case = client.post(
        "/api/cases",
        headers=auth_headers(analyst_token),
        json={"title": "Policy test case", "platform_id": platform["id"]},
    ).json()
    return platform, policy, rule, case


def test_assessment_is_insufficient_without_verified_evidence(client, SessionLocal):
    make_user(SessionLocal, "admin_pa1", Role.ADMIN)
    make_user(SessionLocal, "analyst_pa1", Role.ANALYST)
    admin_token = login(client, "admin_pa1")
    analyst_token = login(client, "analyst_pa1")
    _, _, _, case = _setup_case_with_policy(client, admin_token, analyst_token)

    resp = client.post("/api/assessments", headers=auth_headers(analyst_token), json={"case_id": case["id"]})
    assert resp.status_code == 201
    assessments = resp.json()
    assert len(assessments) == 1
    assert assessments[0]["status"] == "INSUFFICIENT_EVIDENCE"
    assert assessments[0]["requires_human_review"] is True


def test_keyword_alone_does_not_confirm_a_violation(client, SessionLocal):
    """Core false-positive-protection guarantee (spec section 39): even a
    strong keyword match against a policy rule must come back as a
    PENDING_REVIEW/INSUFFICIENT_EVIDENCE triage signal, never CONFIRMED,
    until a human reviewer explicitly approves it."""
    make_user(SessionLocal, "admin_pa2", Role.ADMIN)
    make_user(SessionLocal, "analyst_pa2", Role.ANALYST)
    admin_token = login(client, "admin_pa2")
    analyst_token = login(client, "analyst_pa2")
    _, _, rule, case = _setup_case_with_policy(client, admin_token, analyst_token, keywords="bunuh,ancam")

    ev = client.post(
        "/api/evidence",
        headers=auth_headers(analyst_token),
        data={
            "case_id": case["id"],
            "type": "PUBLIC_POST",
            "source_url": "https://policy-platform.example/post/1",
            "description": "Postingan publik berisi kata 'bunuh' dalam konteks yang belum jelas.",
        },
    ).json()
    client.post(f"/api/evidence/{ev['id']}/verify", headers=auth_headers(analyst_token), json={})

    resp = client.post("/api/assessments", headers=auth_headers(analyst_token), json={"case_id": case["id"]})
    assessments = resp.json()
    assert len(assessments) == 1
    assessment = assessments[0]
    assert assessment["category"] == "THREATS"
    assert assessment["status"] != "CONFIRMED"
    assert assessment["requires_human_review"] is True
    assert assessment["confidence"] < 1.0


def test_no_keyword_match_reports_insufficient_not_a_false_violation(client, SessionLocal):
    make_user(SessionLocal, "admin_pa3", Role.ADMIN)
    make_user(SessionLocal, "analyst_pa3", Role.ANALYST)
    admin_token = login(client, "admin_pa3")
    analyst_token = login(client, "analyst_pa3")
    _, _, _, case = _setup_case_with_policy(client, admin_token, analyst_token, keywords="bunuh,ancam")

    ev = client.post(
        "/api/evidence",
        headers=auth_headers(analyst_token),
        data={
            "case_id": case["id"],
            "type": "PUBLIC_POST",
            "source_url": "https://policy-platform.example/post/2",
            "description": "A perfectly ordinary public post about gardening.",
        },
    ).json()
    client.post(f"/api/evidence/{ev['id']}/verify", headers=auth_headers(analyst_token), json={})

    resp = client.post("/api/assessments", headers=auth_headers(analyst_token), json={"case_id": case["id"]})
    assessments = resp.json()
    assert assessments[0]["status"] == "INSUFFICIENT_EVIDENCE"


def test_assessment_is_enqueued_for_human_review_and_reviewer_can_approve(client, SessionLocal):
    make_user(SessionLocal, "admin_pa4", Role.ADMIN)
    make_user(SessionLocal, "analyst_pa4", Role.ANALYST)
    make_user(SessionLocal, "reviewer_pa4", Role.REVIEWER)
    admin_token = login(client, "admin_pa4")
    analyst_token = login(client, "analyst_pa4")
    reviewer_token = login(client, "reviewer_pa4")
    _, _, _, case = _setup_case_with_policy(client, admin_token, analyst_token, keywords="scam,penipuan")

    ev = client.post(
        "/api/evidence",
        headers=auth_headers(analyst_token),
        data={
            "case_id": case["id"],
            "type": "PUBLIC_POST",
            "source_url": "https://policy-platform.example/post/3",
            "description": "Public post advertising a scam investment scheme.",
        },
    ).json()
    client.post(f"/api/evidence/{ev['id']}/verify", headers=auth_headers(analyst_token), json={})
    client.post("/api/assessments", headers=auth_headers(analyst_token), json={"case_id": case["id"]})

    queue = client.get("/api/reviews?status_filter=PENDING", headers=auth_headers(reviewer_token)).json()
    matching = [q for q in queue if q["case_id"] == case["id"]]
    assert len(matching) == 1

    decide = client.post(
        f"/api/reviews/{matching[0]['id']}/decide",
        headers=auth_headers(reviewer_token),
        json={"action": "APPROVE", "notes": "Reviewed manually"},
    )
    assert decide.status_code == 200
    assert decide.json()["status"] == "APPROVED"

    assessment_id = matching[0]["assessment_id"]
    assessment = client.get(f"/api/assessments/{assessment_id}", headers=auth_headers(analyst_token)).json()
    assert assessment["status"] == "CONFIRMED"
    assert assessment["reviewed_by"] is not None
