from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(
        min_length=3,
        max_length=320,
    )
    password: str = Field(
        min_length=1,
        max_length=1024,
    )


class LoginResponse(BaseModel):
    user_id: UUID
    session_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime


class SessionResponse(BaseModel):
    session_id: UUID
    user_id: UUID
    expires_at: datetime
