from pydantic import BaseModel


class PlatformOut(BaseModel):
    id: str
    name: str
    domain: str
    reporting_url: str | None = None
    api_endpoint: str | None = None
    has_official_api: bool
    allowed_categories: list[str] = []
    required_fields: list[str] = []
    attachment_rules: dict = {}
    rate_limit_notes: str | None = None
    terms_url: str | None = None

    class Config:
        from_attributes = True


class ApiCredentialCreate(BaseModel):
    credential_type: str  # api_key, oauth2, webhook_secret
    value: str
    enabled: bool = True


class ApiCredentialOut(BaseModel):
    """Never includes the secret value — only metadata, per spec section 23
    ("never displayed in logs, never returned through frontend API")."""

    id: str
    platform_id: str
    credential_type: str
    enabled: bool

    class Config:
        from_attributes = True


class PlatformCreate(BaseModel):
    name: str
    domain: str
    reporting_url: str | None = None
    api_endpoint: str | None = None
    has_official_api: bool = False
    allowed_categories: list[str] = []
    required_fields: list[str] = []
    attachment_rules: dict = {}
    rate_limit_notes: str | None = None
    terms_url: str | None = None
    privacy_requirements: str | None = None
