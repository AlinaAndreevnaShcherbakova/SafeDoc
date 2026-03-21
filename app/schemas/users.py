from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    login: str = Field(pattern=r"^[A-Za-z0-9]+$")
    surname: str = Field(pattern=r"^[A-Za-zА-Яа-яЁё]+$")
    name: str = Field(pattern=r"^[A-Za-zА-Яа-яЁё]+$")
    middle_name: str | None = Field(default=None, pattern=r"^[A-Za-zА-Яа-яЁё]+$")
    department: str
    position: str
    email: EmailStr


class UserCreate(UserBase):
    password: str
    is_superadmin: bool = False


class UserUpdate(BaseModel):
    surname: str | None = Field(default=None, pattern=r"^[A-Za-zА-Яа-яЁё]+$")
    name: str | None = Field(default=None, pattern=r"^[A-Za-zА-Яа-яЁё]+$")
    middle_name: str | None = Field(default=None, pattern=r"^[A-Za-zА-Яа-яЁё]+$")
    department: str | None = None
    position: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    is_superadmin: bool | None = None


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_superadmin: bool
    role: str
