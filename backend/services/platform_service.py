"""Platform reporting adapters.

PlatformAdapter defines the contract every platform integration must
follow. ManualPlatformAdapter is always available and never automates
submission — it prepares the report for a human to copy/attach and open
the platform's own official reporting page. OfficialApiPlatformAdapter is
only usable when the platform is configured with `has_official_api=True`
and a real, operator-supplied credential exists; it calls that API over
HTTPS and nothing else. Neither adapter ever attempts to defeat CAPTCHAs,
rate limits, login walls, or any other anti-abuse control.
"""

from abc import ABC, abstractmethod

import httpx
from sqlalchemy.orm import Session

from models.platform import ApiCredential, Platform
from models.report import Report
from services.crypto_service import decrypt_secret


class PlatformAdapter(ABC):
    def __init__(self, platform: Platform):
        self.platform = platform

    @abstractmethod
    def validate_payload(self, report: Report) -> list[str]:
        """Return a list of validation problems (empty = valid)."""

    @abstractmethod
    def submit_report(self, report: Report) -> dict:
        """Attempt submission. Returns a dict describing the outcome."""

    @abstractmethod
    def get_status(self, external_reference: str) -> dict:
        """Query submission status if the platform supports it."""


class ManualPlatformAdapter(PlatformAdapter):
    def validate_payload(self, report: Report) -> list[str]:
        problems = []
        required = self.platform.required_fields or []
        for field in required:
            if field not in report.body or not report.body.get(field):
                problems.append(f"Missing required field for this platform: {field}")
        return problems

    def submit_report(self, report: Report) -> dict:
        return {
            "method": "MANUAL",
            "status": "AWAITING_HUMAN_SUBMISSION",
            "reporting_url": self.platform.reporting_url,
            "instructions": (
                "Export this report (PDF/JSON) and submit it yourself through the "
                "platform's official reporting page. No automated submission is performed."
            ),
        }

    def get_status(self, external_reference: str) -> dict:
        return {"status": "UNKNOWN", "note": "Manual submissions must be tracked by the operator."}


class OfficialApiPlatformAdapter(PlatformAdapter):
    def __init__(self, platform: Platform, credential: ApiCredential):
        super().__init__(platform)
        self.credential = credential

    def validate_payload(self, report: Report) -> list[str]:
        problems = []
        if not self.platform.api_endpoint:
            problems.append("Platform has no configured API endpoint")
        required = self.platform.required_fields or []
        for field in required:
            if field not in report.body or not report.body.get(field):
                problems.append(f"Missing required field for this platform: {field}")
        return problems

    def submit_report(self, report: Report) -> dict:
        problems = self.validate_payload(report)
        if problems:
            return {"method": "API", "status": "REJECTED_LOCALLY", "problems": problems}

        api_key = decrypt_secret(self.credential.encrypted_value)
        try:
            response = httpx.post(
                self.platform.api_endpoint,
                json=report.body,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15.0,
            )
            return {
                "method": "API",
                "status": "SUBMITTED" if response.is_success else "FAILED",
                "http_status": response.status_code,
                "response_body": _safe_json(response),
            }
        except httpx.HTTPError as exc:
            return {"method": "API", "status": "FAILED", "error": str(exc)}

    def get_status(self, external_reference: str) -> dict:
        return {"status": "UNKNOWN", "note": "Status polling depends on the specific platform API contract."}


def _safe_json(response: httpx.Response) -> dict | str:
    try:
        return response.json()
    except ValueError:
        return response.text[:500]


def get_adapter(db: Session, platform: Platform) -> PlatformAdapter:
    if platform.has_official_api:
        credential = (
            db.query(ApiCredential)
            .filter(ApiCredential.platform_id == platform.id, ApiCredential.enabled.is_(True))
            .first()
        )
        if credential:
            return OfficialApiPlatformAdapter(platform, credential)
    return ManualPlatformAdapter(platform)
