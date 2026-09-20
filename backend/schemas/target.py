from datetime import datetime

from pydantic import BaseModel, field_validator


class TargetCreate(BaseModel):
    platform_id: str
    username: str
    display_name: str | None = None
    profile_url: str
    account_id: str | None = None
    profile_description: str | None = None
    account_created_at: datetime | None = None
    public_followers: int | None = None
    public_following: int | None = None
    public_posts: int | None = None
    verification_status: str = "UNKNOWN"
    source_url: str

    @field_validator("profile_url", "source_url")
    @classmethod
    def must_be_https_url(cls, v: str) -> str:
        if not v.startswith("https://") and not v.startswith("http://"):
            raise ValueError("URL must start with http:// or https://")
        return v


class TargetOut(BaseModel):
    id: str
    platform_id: str
    username: str
    display_name: str | None
    profile_url: str
    account_id: str | None
    profile_description: str | None
    account_created_at: datetime | None
    public_followers: int | None
    public_following: int | None
    public_posts: int | None
    verification_status: str
    collected_at: datetime
    collected_by: str | None
    source_url: str

    class Config:
        from_attributes = True
