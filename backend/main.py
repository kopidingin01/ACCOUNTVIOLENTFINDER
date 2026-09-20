from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import models  # noqa: F401 ensures all models are registered on Base.metadata
from config import get_settings
from database import Base, engine
from routers import assessments, audit, auth, cases, dashboard, evidence, osint, platforms, policies, reports, reviews, targets

settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.rate_limit_per_minute}/minute"])

app = FastAPI(
    title="Report Validator — Evidence Collection, Violation Validation & Platform Reporting",
    description=(
        "Trust & Safety case management for evidence-based report validation and the "
        "Account Violation Finder workflow. Not a mass-reporting or takedown-bot tool: "
        "the system enforces human review before any report reaches SUBMITTED status."
    ),
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


@app.on_event("startup")
def on_startup():
    # Dev/demo convenience: creates tables if they do not exist yet.
    # For production, use versioned migrations (see database/migrations/).
    Base.metadata.create_all(bind=engine)


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(targets.router)
app.include_router(evidence.router)
app.include_router(policies.router)
app.include_router(assessments.router)
app.include_router(reports.router)
app.include_router(reviews.router)
app.include_router(platforms.router)
app.include_router(audit.router)
app.include_router(dashboard.router)
app.include_router(osint.router)
