from pydantic import BaseModel


class AccountFinderRequest(BaseModel):
    account_url: str
    create_case: bool = True


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
