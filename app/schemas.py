from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None
    is_admin: bool = False
    user_id: int | None = None


class UserBase(BaseModel):
    username: str


class UserInDB(UserBase):
    hashed_password: str
    is_admin: bool
    is_active: bool
    credits: int


class UserOut(UserBase):
    is_admin: bool
    is_active: bool
    credits: int


class TokenWithApiKey(Token):
    api_key: str