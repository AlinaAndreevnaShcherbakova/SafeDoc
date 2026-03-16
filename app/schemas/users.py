from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    login: str
    surname: str
    name: str
    middle_name: str | None = None
    department: str
    position: str
    email: EmailStr


class UserCreate(UserBase):
    password: str
    is_superadmin: bool = False


class UserUpdate(BaseModel):
    surname: str | None = None
    name: str | None = None
    middle_name: str | None = None
    department: str | None = None
    position: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    is_superadmin: bool | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_superadmin: bool
