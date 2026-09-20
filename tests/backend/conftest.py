import os
import pathlib
import sys

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-only-do-not-use-in-prod")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import models  # noqa: E402,F401
from database import Base, get_db  # noqa: E402
from main import app  # noqa: E402
from models.user import Role, User  # noqa: E402
from security import hash_password  # noqa: E402

DEFAULT_PASSWORD = "TestPass123!"


@pytest.fixture()
def db_engine(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def SessionLocal(db_engine):
    return sessionmaker(bind=db_engine, autoflush=False, autocommit=False)


@pytest.fixture()
def client(SessionLocal, tmp_path):
    from config import get_settings

    storage_dir = tmp_path / "evidence_storage"
    storage_dir.mkdir()
    # get_settings() is an lru_cache singleton shared by every module that
    # imported it, so mutating the one instance updates it everywhere
    # (evidence_service, routers/evidence.py, etc.) without extra patching.
    get_settings().storage_path = str(storage_dir)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(SessionLocal, username: str, role: Role, password: str = DEFAULT_PASSWORD) -> User:
    db = SessionLocal()
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username.title(),
        role=role,
        password_hash=hash_password(password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def login(client, username: str, password: str = DEFAULT_PASSWORD) -> str:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
