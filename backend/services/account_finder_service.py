"""Account Violation Finder — the primary user-facing workflow.

Given a public social-media account URL, this orchestrates:
  1. Platform identification (by domain).
  2. Public-only evidence collection (services.osint_service).
  3. Registration of a Target + a PUBLIC_PROFILE evidence item (with
     source URL + collection timestamp, so it can enter the same
     chain-of-custody / verification pipeline as any other evidence).
  4. Optional case creation.
  5. Policy-keyword triage over the collected page text (never a final
     verdict — see services.violation_service and POLICY_ENGINE.md).

It never fabricates evidence. If public collection fails or is blocked,
findings are reported as "tidak dapat dikumpulkan" rather than guessed.
"""

from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.case import Case
from models.content import Content
from models.enums import CaseStatus, EvidenceType, EvidenceVerificationStatus, Priority
from models.evidence import Evidence
from models.platform import Platform
from models.target import Target
from services import audit_service, policy_service, osint_service
from utils.ids import generate_case_number, generate_evidence_number
from utils.validators import is_valid_http_url


def _find_platform_by_url(db: Session, url: str) -> Platform | None:
    host = (urlparse(url).hostname or "").lower()
    platforms = db.query(Platform).all()
    for p in platforms:
        if p.domain and p.domain.lower() in host:
            return p
    return None


def _get_or_create_target(db: Session, platform: Platform, url: str, collected: dict, user_id: str) -> Target:
    existing = db.query(Target).filter(Target.platform_id == platform.id, Target.profile_url == url).first()
    if existing:
        return existing

    username = urlparse(url).path.strip("/").split("/")[-1] or url
    target = Target(
        platform_id=platform.id,
        username=username,
        display_name=collected.get("og_title") or collected.get("title"),
        profile_url=url,
        profile_description=collected.get("description"),
        verification_status="UNKNOWN",
        collected_by=user_id,
        source_url=url,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    audit_service.log_action(db, user_id, "TARGET_COLLECTED", "target", target.id, {"profile_url": url})
    return target


def analyze_account(db: Session, account_url: str, create_case: bool, user_id: str) -> dict:
    # Belt-and-suspenders: schemas.osint.AccountFinderRequest already rejects
    # a non-http(s) account_url (e.g. a javascript: URI whose hostname still
    # substring-matches a platform domain below), but this function is where
    # the value actually gets persisted to Target.profile_url/source_url and
    # must not trust that every caller went through that schema.
    if not is_valid_http_url(account_url):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "account_url must be a valid http(s) URL")

    platform = _find_platform_by_url(db, account_url)
    if platform is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Platform tidak dikenali dari URL yang diberikan. Tambahkan platform ini ke daftar Platform terlebih dahulu.",
        )

    collected = osint_service.collect_public_page(account_url)
    collection_status = collected["status"]

    target = _get_or_create_target(db, platform, account_url, collected if collection_status == "COLLECTED" else {}, user_id)

    case = None
    if create_case:
        case = Case(
            case_number=generate_case_number(db),
            title=f"Account review: {target.username} ({platform.name})",
            platform_id=platform.id,
            target_id=target.id,
            report_category="ACCOUNT_VIOLATION_FINDER",
            priority=Priority.MEDIUM,
            description=f"Automated intake from Account Violation Finder for {account_url}",
            status=CaseStatus.COLLECTING_EVIDENCE,
            created_by=user_id,
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        audit_service.log_action(db, user_id, "CASE_CREATED", "case", case.case_number, {"source": "account_finder"})

    findings: list[dict] = []

    if collection_status != "COLLECTED":
        return {
            "case_id": case.id if case else None,
            "target_id": target.id,
            "platform": platform.name,
            "profile_url": account_url,
            "collection_status": collection_status,
            "findings": [],
            "summary": (
                "Tidak dapat mengumpulkan konten publik dari URL ini "
                f"({collected.get('reason', 'alasan tidak diketahui')}). "
                "Tidak ditemukan bukti pelanggaran yang memadai dari sumber publik yang diperiksa."
            ),
            "dossier_ready": False,
        }

    profile_evidence = Evidence(
        evidence_number=generate_evidence_number(db),
        case_id=case.id if case else None,
        type=EvidenceType.PUBLIC_PROFILE,
        source_url=account_url,
        description=collected.get("description") or collected.get("title") or "Public profile snapshot",
        collected_by=user_id,
        verification_status=EvidenceVerificationStatus.PENDING,
    )
    if case:
        db.add(profile_evidence)
        db.commit()
        db.refresh(profile_evidence)

    content_text = " ".join(filter(None, [collected.get("title"), collected.get("description"), collected.get("og_title")]))

    rules = policy_service.get_rules_for_platform(db, platform.id)
    hits = policy_service.triage_by_keyword(content_text, rules)

    if case and content_text:
        content_row = Content(
            case_id=case.id,
            target_id=target.id,
            content_url=account_url,
            content_type="profile",
            excerpt=content_text[:2000],
            observed_at=datetime.now(timezone.utc),
        )
        db.add(content_row)
        db.commit()

    if not hits:
        summary = "Tidak ditemukan bukti pelanggaran yang memadai dari sumber publik yang diperiksa."
    else:
        summary = (
            f"Ditemukan {len(hits)} indikasi awal berdasarkan pencocokan kata kunci kebijakan. "
            "Bukti ini memerlukan verifikasi manual sebelum dapat disimpulkan sebagai pelanggaran."
        )
        for idx, (rule, matched_keywords) in enumerate(hits, start=1):
            findings.append(
                {
                    "finding_number": f"TEMUAN #{idx:03d}",
                    "category": policy_service.category_display(rule.category),
                    "source_url": account_url,
                    "observed_at": collected.get("collected_at"),
                    "evidence_ids": [profile_evidence.evidence_number] if case else [],
                    "reasoning": (
                        f"Konten publik pada profil ini mengandung istilah yang berasosiasi dengan kebijakan "
                        f"{rule.rule_code} ({policy_service.category_display(rule.category)}): {matched_keywords}. "
                        "Ini adalah sinyal triase berbasis kata kunci, BUKAN kesimpulan pelanggaran — "
                        "konteks, target, dan niat belum diverifikasi oleh manusia."
                    ),
                    "policy_reference": rule.rule_code,
                    "confidence": round(min(0.3 + 0.15 * len(matched_keywords), 0.7), 2),
                    "status": "PERLU_VERIFIKASI",
                }
            )

    audit_service.log_action(
        db, user_id, "ACCOUNT_FINDER_RUN", "target", target.id,
        {"platform": platform.name, "findings": len(findings)},
    )

    return {
        "case_id": case.id if case else None,
        "target_id": target.id,
        "platform": platform.name,
        "profile_url": account_url,
        "collection_status": collection_status,
        "findings": findings,
        "summary": summary,
        "dossier_ready": bool(case) and bool(findings),
    }
