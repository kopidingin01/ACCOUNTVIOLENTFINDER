"""Demo seed data — entirely fictional users, targets, and content.

Run with: python seed.py (inside the backend/ directory, with DATABASE_URL
pointed at a real or throwaway database). Safe to re-run: it clears and
re-creates the demo rows it manages.
"""

import datetime as dt

import models  # noqa: F401
from database import Base, SessionLocal, engine
from models.case import Case
from models.content import Content
from models.enums import (
    AssessmentStatus,
    CaseStatus,
    EvidenceType,
    EvidenceVerificationStatus,
    Priority,
    ReadinessLevel,
    ReportStatus,
    ViolationCategory,
)
from models.evidence import Evidence
from models.platform import Platform
from models.policy import Policy, PolicyRule
from models.report import Report
from models.target import Target
from models.user import Role, User
from models.violation_assessment import ViolationAssessment
from security import hash_password
from services.hash_service import sha256_text as fake_sha256

Base.metadata.create_all(bind=engine)

db = SessionLocal()

print("Seeding demo data (fictional only)...")

USERS = [
    ("admin", "admin@example.com", "Admin Operator", Role.ADMIN),
    ("analyst1", "analyst1@example.com", "Ayu Analyst", Role.ANALYST),
    ("reviewer1", "reviewer1@example.com", "Rian Reviewer", Role.REVIEWER),
    ("auditor1", "auditor1@example.com", "Anwar Auditor", Role.AUDITOR),
    ("viewer1", "viewer1@example.com", "Vino Viewer", Role.VIEWER),
]

users = {}
for username, email, full_name, role in USERS:
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        users[username] = existing
        continue
    user = User(username=username, email=email, full_name=full_name, role=role, password_hash=hash_password("ChangeMe123!"))
    db.add(user)
    db.commit()
    db.refresh(user)
    users[username] = user

platform = db.query(Platform).filter(Platform.name == "Demo Social Platform").first()
if not platform:
    platform = Platform(
        name="Demo Social Platform",
        domain="demo-social.example",
        reporting_url="https://demo-social.example/report",
        has_official_api=False,
        allowed_categories=[c.value for c in ViolationCategory],
        required_fields=["target", "evidence", "violation_category"],
        attachment_rules={"max_files": 10, "max_size_mb": 25},
        rate_limit_notes="Manual reporting only; no published API rate limit.",
        terms_url="https://demo-social.example/terms",
    )
    db.add(platform)
    db.commit()
    db.refresh(platform)

policy = db.query(Policy).filter(Policy.platform_id == platform.id).first()
if not policy:
    policy = Policy(
        platform_id=platform.id,
        name="Demo Social Platform Community Guidelines",
        policy_url="https://demo-social.example/guidelines",
        effective_date=dt.date(2025, 1, 1),
        last_updated=dt.date(2026, 1, 1),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)

RULES = [
    ("POL-001", ViolationCategory.HARASSMENT, "Targeted harassment of an individual through repeated abusive messages.", "HIGH", "bodoh,tolol,hina"),
    ("POL-002", ViolationCategory.SCAM, "Deceptive schemes designed to defraud users of money or personal data.", "HIGH", "investasi pasti untung,transfer dulu,giveaway gratis"),
    ("POL-003", ViolationCategory.IMPERSONATION, "Pretending to be another person or organization without authorization.", "MEDIUM", "akun resmi,official account,verified"),
    ("POL-004", ViolationCategory.SPAM, "Repetitive, unsolicited promotional content.", "LOW", "klik link ini,follow back,promo terbatas"),
    ("POL-005", ViolationCategory.THREATS, "Explicit statements of intent to cause harm to a specific person.", "CRITICAL", "bunuh,ancam,serang"),
]
rules = {}
for code, category, desc, severity, keywords in RULES:
    rule = db.query(PolicyRule).filter(PolicyRule.rule_code == code).first()
    if not rule:
        rule = PolicyRule(policy_id=policy.id, rule_code=code, category=category, description=desc, severity=severity, keywords=keywords)
        db.add(rule)
        db.commit()
        db.refresh(rule)
    rules[code] = rule

analyst = users["analyst1"]
reviewer = users["reviewer1"]

for i in range(1, 11):
    case_number = f"CASE-2026-{i:06d}"
    if db.query(Case).filter(Case.case_number == case_number).first():
        continue

    target = Target(
        platform_id=platform.id,
        username=f"demo_account_{i}",
        display_name=f"Demo Account {i}",
        profile_url=f"https://demo-social.example/u/demo_account_{i}",
        account_id=f"acc_{1000+i}",
        profile_description="Fictional demo profile used for seed data only.",
        public_followers=100 * i,
        public_following=50 * i,
        public_posts=20 * i,
        verification_status="UNVERIFIED",
        collected_by=analyst.id,
        source_url=f"https://demo-social.example/u/demo_account_{i}",
    )
    db.add(target)
    db.commit()
    db.refresh(target)

    case = Case(
        case_number=case_number,
        title=f"Demo case #{i}: reported behavior on demo_account_{i}",
        platform_id=platform.id,
        target_id=target.id,
        report_category="DEMO",
        priority=Priority.MEDIUM if i % 2 == 0 else Priority.HIGH,
        description="Seed/demo case for local development. Not a real report.",
        status=CaseStatus.UNDER_REVIEW if i % 3 == 0 else CaseStatus.COLLECTING_EVIDENCE,
        created_by=analyst.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    rule_code = list(rules.keys())[i % len(rules)]
    rule = rules[rule_code]

    content = Content(
        case_id=case.id,
        target_id=target.id,
        content_url=f"https://demo-social.example/u/demo_account_{i}/post/{i}",
        content_type="post",
        excerpt=f"Contoh cuplikan konten publik demo #{i} yang mengandung kata kunci triase seperti '{rule.keywords.split(',')[0]}'.",
        observed_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=i),
    )
    db.add(content)

    for j in range(1, 3):
        evidence = Evidence(
            evidence_number=f"EV-{(i - 1) * 2 + j:06d}",
            case_id=case.id,
            type=EvidenceType.PUBLIC_POST if j == 1 else EvidenceType.PUBLIC_PROFILE,
            source_url=content.content_url if j == 1 else target.profile_url,
            description=f"Demo evidence item {j} for case {case_number}",
            sha256=fake_sha256(f"{case_number}-{j}"),
            collected_by=analyst.id,
            verification_status=EvidenceVerificationStatus.VERIFIED if i % 2 == 0 else EvidenceVerificationStatus.PENDING,
            verification_notes="Verified during seed for demo purposes." if i % 2 == 0 else None,
        )
        db.add(evidence)
    db.commit()

    assessment = ViolationAssessment(
        case_id=case.id,
        category=rule.category,
        policy_rule_id=rule.id,
        confidence=0.55,
        evidence_ids=[f"EV-{(i - 1) * 2 + 1:06d}", f"EV-{(i - 1) * 2 + 2:06d}"],
        reason=f"Seed-generated triage match against {rule.rule_code} for demonstration purposes only.",
        missing_evidence=[] if i % 2 == 0 else ["Reviewer context notes"],
        requires_human_review=True,
        status=AssessmentStatus.CONFIRMED if i % 4 == 0 else AssessmentStatus.PENDING_REVIEW,
        generated_by="RULE_ENGINE",
        reviewed_by=reviewer.id if i % 4 == 0 else None,
        reviewed_at=dt.datetime.now(dt.timezone.utc) if i % 4 == 0 else None,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    if i <= 10 and i % 2 == 0:
        report = Report(
            report_number=f"REP-2026-{i:06d}",
            case_id=case.id,
            assessment_id=assessment.id,
            platform_id=platform.id,
            body={
                "case_number": case.case_number,
                "platform": platform.name,
                "target": {"username": target.username, "profile_url": target.profile_url},
                "violation_category": rule.category.value,
                "description": "Seed-generated demo report body.",
                "evidence": [],
                "disclaimer": "This report contains factual observations and supporting evidence submitted for platform review. Final enforcement decisions remain with the platform.",
            },
            report_hash=fake_sha256(f"report-{case_number}"),
            readiness_score=70.0,
            readiness_level=ReadinessLevel.NEEDS_REVIEW,
            missing_items=["Human review completed"] if i % 4 != 0 else [],
            status=ReportStatus.READY if i % 4 == 0 else ReportStatus.DRAFT,
            created_by=analyst.id,
        )
        db.add(report)
    db.commit()

print("Seed complete: 5 users, 10 cases, ~20 evidence items, 5 policy rules, 5 reports.")
db.close()
