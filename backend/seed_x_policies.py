"""One-time setup script: registers the platform X (domain x.com) and a
broad set of Policy Rules covering the violation categories most commonly
reported there (hate speech/SARA, misinformation, sexual content, illegal
gambling, scam/fraud, phishing, threats, harassment, child safety, self
harm, impersonation, spam, and privacy violation).

Run with: python seed_x_policies.py (inside backend/, with DATABASE_URL
pointed at your real database). Safe to re-run — every insert is
idempotent (skipped if the platform/policy/rule already exists).

IMPORTANT — what this script does NOT do: it does not report anything to
X, does not configure any API credential, and the keyword lists below are
triage hints only (see services/policy_service.triage_by_keyword and
POLICY_ENGINE.md) — a keyword match is never treated as a confirmed
violation by this system. Every match still requires human review before
a report can be submitted.
"""

import datetime as dt

import models  # noqa: F401
from database import Base, SessionLocal, engine
from models.enums import ViolationCategory
from models.platform import Platform
from models.policy import Policy, PolicyRule

Base.metadata.create_all(bind=engine)

db = SessionLocal()

print("Setting up platform 'X' and its policy rules...")

platform = db.query(Platform).filter(Platform.domain == "x.com").first()
if not platform:
    platform = Platform(
        name="X",
        domain="x.com",
        reporting_url="https://help.x.com/en/rules-and-policies",
        has_official_api=False,
        allowed_categories=[c.value for c in ViolationCategory],
        required_fields=["target", "evidence", "violation_category"],
        attachment_rules={"max_files": 4, "max_size_mb": 5},
        rate_limit_notes="Manual reporting only via X's own report form; no automated submission.",
        terms_url="https://x.com/en/tos",
    )
    db.add(platform)
    db.commit()
    db.refresh(platform)
    print(f"  Created platform: {platform.name} ({platform.domain})")
else:
    print(f"  Platform already exists: {platform.name} ({platform.domain})")

policy = db.query(Policy).filter(Policy.platform_id == platform.id).first()
if not policy:
    policy = Policy(
        platform_id=platform.id,
        name="X Rules",
        policy_url="https://help.x.com/en/rules-and-policies/x-rules",
        effective_date=dt.date(2025, 1, 1),
        last_updated=dt.date(2026, 1, 1),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    print(f"  Created policy: {policy.name}")
else:
    print(f"  Policy already exists: {policy.name}")

# (rule_code, category, description, severity, triage keywords)
# Keywords are illustrative patterns for triage, not slurs or explicit
# content — see the module docstring and POLICY_ENGINE.md.
RULES = [
    (
        "X-POL-001", ViolationCategory.HATE,
        "Attacks or demeans people based on race, ethnicity, religion, national origin, or other protected "
        "characteristics (hate speech / unsur SARA).",
        "HIGH",
        "hina agama,rendahkan suku,ras inferior,usir dari negeri,musnahkan kaum,kafir semua",
    ),
    (
        "X-POL-002", ViolationCategory.DECEPTIVE_PRACTICE,
        "Spreads fabricated or deliberately misleading claims presented as fact (misinformation / hoax).",
        "MEDIUM",
        "berita hoax,fakta disembunyikan,pemerintah menutupi,bukti direkayasa,vaksin berbahaya",
    ),
    (
        "X-POL-003", ViolationCategory.SEXUAL_CONTENT,
        "Explicit sexual content or pornography shared without appropriate labeling or consent.",
        "HIGH",
        "konten dewasa,video eksplisit,materi pornografi,konten +18",
    ),
    (
        "X-POL-004", ViolationCategory.ILLEGAL_CONTENT,
        "Promotes unlicensed online gambling (judi online) prohibited under applicable law.",
        "HIGH",
        "slot gacor,situs judi,bandar togel,link slot,daftar judi online,maxwin",
    ),
    (
        "X-POL-005", ViolationCategory.SCAM,
        "Deceptive schemes designed to defraud users of money or personal data (penipuan/investasi bodong).",
        "HIGH",
        "investasi pasti untung,transfer dulu,modal kecil untung besar,giveaway palsu,kirim ongkir dulu",
    ),
    (
        "X-POL-006", ViolationCategory.PHISHING,
        "Attempts to trick users into revealing credentials or financial information via fake links or forms.",
        "HIGH",
        "verifikasi akun klik link,update data rekening,akun akan diblokir,masukkan password di sini",
    ),
    (
        "X-POL-007", ViolationCategory.THREATS,
        "Explicit statements of intent to cause physical harm to a specific person or group.",
        "CRITICAL",
        "akan membunuh,bakar rumahmu,kutemukan kau,balas dendam,kuhabisi",
    ),
    (
        "X-POL-008", ViolationCategory.HARASSMENT,
        "Targeted, repeated abusive behavior directed at an individual.",
        "MEDIUM",
        "dasar bodoh,tidak berguna,pantas dihina,sampah masyarakat",
    ),
    (
        "X-POL-009", ViolationCategory.CHILD_SAFETY,
        "Content that endangers, sexualizes, or exploits minors. Zero-tolerance category.",
        "CRITICAL",
        "eksploitasi anak,grooming anak,konten anak eksplisit",
    ),
    (
        "X-POL-010", ViolationCategory.SELF_HARM,
        "Content that promotes or provides instructions for suicide or self-harm.",
        "CRITICAL",
        "cara mengakhiri hidup,ingin bunuh diri,melukai diri sendiri",
    ),
    (
        "X-POL-011", ViolationCategory.IMPERSONATION,
        "Pretending to be another real person, brand, or official entity without authorization.",
        "MEDIUM",
        "akun resmi padahal palsu,mengaku pejabat,official account tapi bukan,verified palsu",
    ),
    (
        "X-POL-012", ViolationCategory.SPAM,
        "Repetitive, unsolicited promotional content or engagement-bait.",
        "LOW",
        "follow back,klik link ini,promo terbatas,like dan retweet berhadiah",
    ),
    (
        "X-POL-013", ViolationCategory.PRIVACY_VIOLATION,
        "Publishes another person's private information without consent (doxing).",
        "HIGH",
        "alamat rumah korban,nomor hp pribadi,data ktp bocor,sebar data pribadi",
    ),
]

created, skipped = 0, 0
for rule_code, category, description, severity, keywords in RULES:
    existing = db.query(PolicyRule).filter(PolicyRule.rule_code == rule_code).first()
    if existing:
        skipped += 1
        continue
    rule = PolicyRule(
        policy_id=policy.id,
        rule_code=rule_code,
        category=category,
        description=description,
        severity=severity,
        keywords=keywords,
    )
    db.add(rule)
    created += 1

db.commit()
print(f"  Policy rules: {created} created, {skipped} already existed.")
print("Done. Platform 'X' is ready to use in Cases / Account Finder / Policy Rules.")
db.close()
