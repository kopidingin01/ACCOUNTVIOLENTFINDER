import pytest
from pydantic import ValidationError

from models.target import Target
from models.user import Role
from schemas.osint import AccountFinderRequest

from conftest import auth_headers, login, make_user


def _register_platform(client, admin_token, domain="facebook.com"):
    return client.post(
        "/api/platforms",
        headers=auth_headers(admin_token),
        json={"name": "Facebook", "domain": domain},
    ).json()


def test_javascript_uri_account_url_is_rejected(client, SessionLocal):
    make_user(SessionLocal, "admin_xss1", Role.ADMIN)
    make_user(SessionLocal, "analyst_xss1", Role.ANALYST)
    admin_token = login(client, "admin_xss1")
    analyst_token = login(client, "analyst_xss1")
    _register_platform(client, admin_token)

    # javascript://facebook.com%0aalert(1) : urlparse(...).hostname resolves
    # to "facebook.com%0aalert(1)", which still substring-matches the
    # registered "facebook.com" platform domain, so nothing but explicit
    # scheme validation stops this from reaching storage.
    payload = {"account_url": "javascript://facebook.com%0aalert(document.cookie)", "create_case": False}
    resp = client.post("/api/osint/account-finder", headers=auth_headers(analyst_token), json=payload)

    assert resp.status_code == 422, resp.text

    db = SessionLocal()
    stored = db.query(Target).filter(Target.profile_url.like("javascript:%")).all()
    db.close()
    assert stored == [], "a javascript: URI must never be persisted as a Target profile_url"


@pytest.mark.parametrize(
    "account_url",
    [
        "javascript://facebook.com%0aalert(document.cookie)",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "not a url",
    ],
)
def test_schema_rejects_non_http_account_url(account_url):
    with pytest.raises(ValidationError):
        AccountFinderRequest(account_url=account_url)


@pytest.mark.parametrize("account_url", ["https://example-social.com/u/someone", "http://example-social.com/u/someone"])
def test_schema_accepts_http_account_url(account_url):
    # No network call happens at schema-construction time — this only
    # checks that a well-formed http(s) URL isn't rejected the way every
    # non-http(s) scheme above is.
    assert AccountFinderRequest(account_url=account_url).account_url == account_url
