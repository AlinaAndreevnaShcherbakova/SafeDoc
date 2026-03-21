from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    surname: str | None = Field(default=None, pattern=r"^[A-Za-zА-Яа-яЁё]+$")
    name: str | None = Field(default=None, pattern=r"^[A-Za-zА-Яа-яЁё]+$")
    middle_name: str | None = Field(default=None, pattern=r"^[A-Za-zА-Яа-яЁё]+$")
    department: str | None = None
    position: str | None = None
    email: EmailStr | None = None


