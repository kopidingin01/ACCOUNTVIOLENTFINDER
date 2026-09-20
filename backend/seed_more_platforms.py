"""One-time setup script: registers Facebook, Instagram, TikTok, YouTube,
and Threads, each with the same broad Policy Rule set used for X in
seed_x_policies.py (hate speech/SARA, misinformation, sexual content,
illegal gambling, scam/fraud, phishing, threats, harassment, child
safety, self harm, impersonation, spam, privacy violation).

Run with: python seed_more_platforms.py (inside backend/, with
DATABASE_URL pointed at your real database). Safe to re-run — every
insert is idempotent (skipped if the platform/policy/rule already
exists), and it does not touch the X platform this script doesn't
create (that's seed_x_policies.py's job — running both is fine, each
only manages its own platforms).

NOTE ON THE POLICY URLS BELOW: they point at each platform's real,
public community-guidelines/terms pages as of when this script was
written. Platforms restructure their help centers occasionally, so if a
link 404s, replace it via the Policies UI (or PATCH the Policy row
directly) rather than assuming the app is broken.

Same caveat as seed_x_policies.py: keyword lists are triage hints only —
see services/policy_service.triage_by_keyword and POLICY_ENGINE.md. A
keyword match is never a confirmed violation; human review is always
required before a report can be submitted.
"""

import datetime as dt

import models  # noqa: F401
from database import Base, SessionLocal, engine
from models.enums import ViolationCategory
from models.platform import Platform
from models.policy import Policy, PolicyRule

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Same 13-category template as seed_x_policies.py, kept in sync manually
# since each platform's Policy row needs its own rule_code namespace.
CATEGORY_TEMPLATE = [
    (ViolationCategory.HATE, "Attacks or demeans people based on race, ethnicity, religion, national origin, or other protected characteristics (hate speech / unsur SARA).", "HIGH", "hina agama,rendahkan suku,ras inferior,usir dari negeri,musnahkan kaum,kafir semua"),
    (ViolationCategory.DECEPTIVE_PRACTICE, "Spreads fabricated or deliberately misleading claims presented as fact (misinformation / hoax).", "MEDIUM", "berita hoax,fakta disembunyikan,pemerintah menutupi,bukti direkayasa,vaksin berbahaya"),
    (ViolationCategory.SEXUAL_CONTENT, "Explicit sexual content or pornography shared without appropriate labeling or consent.", "HIGH", "konten dewasa,video eksplisit,materi pornografi,konten +18"),
    (ViolationCategory.ILLEGAL_CONTENT, "Promotes unlicensed online gambling (judi online) prohibited under applicable law.", "HIGH", "slot gacor,situs judi,bandar togel,link slot,daftar judi online,maxwin"),
    (ViolationCategory.SCAM, "Deceptive schemes designed to defraud users of money or personal data (penipuan/investasi bodong).", "HIGH", "investasi pasti untung,transfer dulu,modal kecil untung besar,giveaway palsu,kirim ongkir dulu"),
    (ViolationCategory.PHISHING, "Attempts to trick users into revealing credentials or financial information via fake links or forms.", "HIGH", "verifikasi akun klik link,update data rekening,akun akan diblokir,masukkan password di sini"),
    (ViolationCategory.THREATS, "Explicit statements of intent to cause physical harm to a specific person or group.", "CRITICAL", "akan membunuh,bakar rumahmu,kutemukan kau,balas dendam,kuhabisi"),
    (ViolationCategory.HARASSMENT, "Targeted, repeated abusive behavior directed at an individual.", "MEDIUM", "dasar bodoh,tidak berguna,pantas dihina,sampah masyarakat"),
    (ViolationCategory.CHILD_SAFETY, "Content that endangers, sexualizes, or exploits minors. Zero-tolerance category.", "CRITICAL", "eksploitasi anak,grooming anak,konten anak eksplisit"),
    (ViolationCategory.SELF_HARM, "Content that promotes or provides instructions for suicide or self-harm.", "CRITICAL", "cara mengakhiri hidup,ingin bunuh diri,melukai diri sendiri"),
    (ViolationCategory.IMPERSONATION, "Pretending to be another real person, brand, or official entity without authorization.", "MEDIUM", "akun resmi padahal palsu,mengaku pejabat,official account tapi bukan,verified palsu"),
    (ViolationCategory.SPAM, "Repetitive, unsolicited promotional content or engagement-bait.", "LOW", "follow back,klik link ini,promo terbatas,like dan retweet berhadiah"),
    (ViolationCategory.PRIVACY_VIOLATION, "Publishes another person's private information without consent (doxing).", "HIGH", "alamat rumah korban,nomor hp pribadi,data ktp bocor,sebar data pribadi"),
]

PLATFORMS = [
    {
        "prefix": "FB",
        "name": "Facebook",
        "domain": "facebook.com",
        "reporting_url": "https://www.facebook.com/help/reportlink",
        "terms_url": "https://www.facebook.com/terms.php",
        "policy_name": "Meta Community Standards",
        "policy_url": "https://transparency.fb.com/policies/community-standards/",
    },
    {
        "prefix": "IG",
        "name": "Instagram",
        "domain": "instagram.com",
        "reporting_url": "https://help.instagram.com/192435014247952",
        "terms_url": "https://help.instagram.com/581066165581870",
        "policy_name": "Instagram Community Guidelines",
        "policy_url": "https://help.instagram.com/477434105621119",
    },
    {
        "prefix": "TT",
        "name": "TikTok",
        "domain": "tiktok.com",
        "reporting_url": "https://www.tiktok.com/legal/report/feedback",
        "terms_url": "https://www.tiktok.com/legal/page/global/terms-of-service/en",
        "policy_name": "TikTok Community Guidelines",
        "policy_url": "https://www.tiktok.com/community-guidelines/en",
    },
    {
        "prefix": "YT",
        "name": "YouTube",
        "domain": "youtube.com",
        "reporting_url": "https://support.google.com/youtube/answer/2802027",
        "terms_url": "https://www.youtube.com/t/terms",
        "policy_name": "YouTube Community Guidelines",
        "policy_url": "https://www.youtube.com/howyoutubeworks/policies/community-guidelines/",
    },
    {
        "prefix": "TH",
        "name": "Threads",
        "domain": "threads.net",
        "reporting_url": "https://help.instagram.com/192435014247952",
        "terms_url": "https://help.instagram.com/581066165581870",
        # Threads' own rules are governed by Instagram's Community Guidelines (per Meta).
        "policy_name": "Threads Community Guidelines (via Instagram)",
        "policy_url": "https://help.instagram.com/477434105621119",
    },
]

for cfg in PLATFORMS:
    print(f"Setting up platform '{cfg['name']}'...")

    platform = db.query(Platform).filter(Platform.domain == cfg["domain"]).first()
    if not platform:
        platform = Platform(
            name=cfg["name"],
            domain=cfg["domain"],
            reporting_url=cfg["reporting_url"],
            has_official_api=False,
            allowed_categories=[c.value for c in ViolationCategory],
            required_fields=["target", "evidence", "violation_category"],
            attachment_rules={"max_files": 4, "max_size_mb": 5},
            rate_limit_notes=f"Manual reporting only via {cfg['name']}'s own report form; no automated submission.",
            terms_url=cfg["terms_url"],
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
            name=cfg["policy_name"],
            policy_url=cfg["policy_url"],
            effective_date=dt.date(2025, 1, 1),
            last_updated=dt.date(2026, 1, 1),
        )
        db.add(policy)
        db.commit()
        db.refresh(policy)
        print(f"  Created policy: {policy.name}")
    else:
        print(f"  Policy already exists: {policy.name}")

    created, skipped = 0, 0
    for idx, (category, description, severity, keywords) in enumerate(CATEGORY_TEMPLATE, start=1):
        rule_code = f"{cfg['prefix']}-POL-{idx:03d}"
        if db.query(PolicyRule).filter(PolicyRule.rule_code == rule_code).first():
            skipped += 1
            continue
        db.add(PolicyRule(
            policy_id=policy.id,
            rule_code=rule_code,
            category=category,
            description=description,
            severity=severity,
            keywords=keywords,
        ))
        created += 1
    db.commit()
    print(f"  Policy rules: {created} created, {skipped} already existed.")

print("Done. Facebook, Instagram, TikTok, YouTube, and Threads are ready to use.")
db.close()
