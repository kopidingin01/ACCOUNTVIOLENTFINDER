from pydantic import BaseModel, EmailStr

from models.user import Role


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    username: str
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool

    class Config:
        from_attributes = True
