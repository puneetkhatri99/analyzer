from typing import Literal

from pydantic import BaseModel


class Login(BaseModel):
    email: str
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class NewUser(BaseModel):
    email: str
    role: Literal["viewer", "editor"]
    password: str  # one-time; the user must change it at first sign-in


class UserChange(BaseModel):
    role: Literal["viewer", "editor"] | None = None
    password: str | None = None  # a new one-time password
