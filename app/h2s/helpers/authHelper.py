import base64
from datetime import datetime, timedelta, timezone
import hashlib
import os
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import BaseModel

from h2s.helpers.httpHelper import getHttpRequest
from h2s.models.user import UserModel
from passlib.context import CryptContext


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str


class TokenData(BaseModel):
    lid: int | None
    uid: int | None
    udname: str | None
    sid: str | None


# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "09d25e094faa6ca2556c818136b7a9563b0ef7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 24*60  # 24 hours
APP_SERVER_URL = os.environ.get("APP_SERVER_URL")
OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="/h2s/web")


def create_access_token(data: TokenData, expires_delta: timedelta | None = None):
    to_encode = data.__dict__
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def generate_sid(user: UserModel):
    hash_obj = hashlib.sha256(user.get_encoded_user_string())
    base64_hash = base64.urlsafe_b64encode(hash_obj.digest()).decode('utf-8')
    return base64_hash[:20]


def get_tokens(
    login_id: int,
    user: UserModel,
    refresh_token: str | None = None
) -> Token:
    token_data = TokenData(
        lid=login_id, uid=user.id,
        udname=user.name, sid=generate_sid(user)
    )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data=token_data,
        expires_delta=access_token_expires
    )

    if refresh_token is None:
        refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
        refresh_token = create_access_token(
            data=token_data,
            expires_delta=refresh_token_expires
        )
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


def get_token_data(token: Annotated[str, Depends(OAUTH2_SCHEME)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenData(**payload)
        if token_data.uid and token_data.lid and token_data.sid:
            return token_data
        else:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception


async def get_current_user(
    token_data: Annotated[TokenData, Depends(get_token_data)],
):
    success, user = await getHttpRequest(f"{APP_SERVER_URL}/h2s/db/user/{token_data.user_id}")
    if success:
        return UserModel(**user)
    else:
        raise HTTPException(status_code=401, detail="Invalid user")


def get_password_hash(password):
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)
