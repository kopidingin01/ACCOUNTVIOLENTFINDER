from pydantic import BaseModel, field_validator

from utils.validators import is_valid_http_url


class AccountFinderRequest(BaseModel):
    account_url: str
    create_case: bool = True

    @field_validator("account_url")
    @classmethod
    def must_be_http_url(cls, v: str) -> str:
        # Rejects anything but a well-formed http(s) URL — in particular a
        # javascript: URI (e.g. "javascript://facebook.com%0aalert(1)",
        # whose hostname still substring-matches a registered platform
        # domain in account_finder_service._find_platform_by_url). Without
        # this, that string reaches _get_or_create_target and is persisted
        # verbatim as Target.profile_url/source_url, which every page with
        # target:read renders as a raw <a href> — stored XSS.
        if not is_valid_http_url(v):
            raise ValueError("account_url must be a valid http(s) URL")
        return v


class FindingOut(BaseModel):
    finding_number: str
    category: str
    source_url: str
    observed_at: str | None
    evidence_ids: list[str]
    reasoning: str
    policy_reference: str | None
    confidence: float
    status: str  # PERLU_VERIFIKASI, TIDAK_CUKUP_BUKTI, TIDAK_DITEMUKAN


class AccountFinderResult(BaseModel):
    case_id: str | None
    target_id: str
    platform: str
    profile_url: str
    collection_status: str
    findings: list[FindingOut]
    summary: str
    dossier_ready: bool
