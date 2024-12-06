"""
Authentication Utilities Module

This module contains utility functions and classes for handling authentication-related tasks,
such as creating and decoding JWT tokens, managing user roles, and generating Gravatar URLs.
It is designed to work with FastAPI, and integrates with OAuth2 password-based authentication.

Key Functions:
    - `create_verification_token`: Generates a JWT token used for email verification.
    - `decode_verification_token`: Decodes a JWT verification token to extract the email address.
    - `create_access_token`: Generates a JWT token used for user authentication (access token).
    - `create_refresh_token`: Generates a JWT token used for refreshing access tokens.
    - `decode_access_token`: Decodes an access token and returns the token data.
    - `get_current_user`: Retrieves the current user from the provided access token.
    - `get_gravatar_url`: Generates a Gravatar URL based on the user's email.
    - `RoleChecker`: A class that checks whether the current user has the required role(s).

Constants:
    - `ALGORITHM`: The algorithm used for signing the JWT tokens (e.g., 'HS256').
    - `ACCESS_TOKEN_EXPIRE_MINUTES`: Expiration time in minutes for access tokens.
    - `REFRESH_TOKEN_EXPIRE_DAYS`: Expiration time in days for refresh tokens.
    - `VERIFICATION_TOKEN_EXPIRE_HOURS`: Expiration time in hours for verification tokens.

Usage:
    - `create_access_token`: Create an access token to authenticate users.
    - `create_refresh_token`: Create a refresh token to issue new access tokens.
    - `decode_access_token`: Decode an access token to extract user information.
    - `get_current_user`: Fetch the current authenticated user based on the token.
"""


from fastapi import Depends, status, HTTPException
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
from datetime import datetime, timedelta, timezone

from src.auth.schema import TokenData, RoleEnum
from src.auth.repos import UserRepository
from src.auth.models import User
from config.general import settings
from config.db import get_db



ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days
VERIFICATION_TOKEN_EXPIRE_HOURS = settings.verification_token_expire_hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def create_verification_token(email: str) -> str:
    """
    Create a verification token for email verification.

    Args:
        email (str): The email address to associate with the token.

    Returns:
        str: The generated JWT verification token.

    Example:
        verification_token = create_verification_token("user@example.com")
    """
    expire = datetime.now(timezone.utc) + timedelta(
        hours=VERIFICATION_TOKEN_EXPIRE_HOURS
    )
    to_encode = {"exp": expire, "sub": email}
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_verification_token(token: str) -> str | None:
    """
    Decode a verification token to retrieve the email address.

    Args:
        token (str): The verification JWT token.

    Returns:
        str | None: The email address if the token is valid, None otherwise.

    Example:
        email = decode_verification_token(token)
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None


def create_access_token(data: dict):
    """
    Create an access token for user authentication.

    Args:
        data (dict): The data to encode in the token, typically the user's username.

    Returns:
        str: The generated access JWT token.

    Example:
        access_token = create_access_token({"sub": "username"})
    """
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encode_jwt


def create_refresh_token(data: dict):
    """
    Create a refresh token to allow the user to obtain a new access token.

    Args:
        data (dict): The data to encode in the token.

    Returns:
        str: The generated refresh JWT token.

    Example:
        refresh_token = create_refresh_token({"sub": "username"})
    """
    to_encode = data.copy()
    expire = datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encode_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return encode_jwt


def decode_access_token(token: str) -> TokenData | None:
    """
    Decode an access token to retrieve the user's token data.

    Args:
        token (str): The access JWT token.

    Returns:
        TokenData | None: The decoded token data containing the user's username, or None if invalid.

    Example:
        token_data = decode_access_token(token)
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return TokenData(username=username)
    except JWTError:
        return None
    

async def get_current_user(token: str = Depends(oauth2_scheme), 
                           db: AsyncSession = Depends(get_db)) -> User:
    """
    Get the current authenticated user based on the provided access token.

    Args:
        token (str): The access JWT token (from the `Authorization` header).
        db (AsyncSession): The database session.

    Returns:
        User: The current user object.

    Raises:
        HTTPException: If the token is invalid or the user is not found.

    Example:
        user = await get_current_user(token, db)
    """
    credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = decode_access_token(token)
    if token_data is None:
        raise credentials_exception
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_username(token_data.username)
    if user is None:
        raise credentials_exception
    return user


def get_gravatar_url(email):
    """
    Generate a Gravatar URL based on the user's email address.

    Args:
        email (str): The user's email address.

    Returns:
        str: The URL of the user's Gravatar image.

    Example:
        gravatar_url = get_gravatar_url("user@example.com")
    """
    email_hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    return f"https://www.gravatar.com/avatar/{email_hash}"


class RoleChecker:
    """
    A class to check if the current user has one of the allowed roles.

    Attributes:
        allowed_roles (list[RoleEnum]): A list of allowed roles for access.

    Methods:
        __call__(token: str, db: AsyncSession): Check if the user has one of the allowed roles.
    """

    def __init__(self, allowed_roles: list[RoleEnum]):
        """
        Initialize the RoleChecker with a list of allowed roles.

        Args:
            allowed_roles (list[RoleEnum]): A list of allowed roles.
        """
        self.allowed_roles = allowed_roles

    async def __call__(
        self, token: str = Depends(oauth2_scheme), 
        db: AsyncSession = Depends(get_db)
    ) -> User:
        """
        Check if the current user has one of the allowed roles.

        Args:
            token (str): The access JWT token (from the `Authorization` header).
            db (AsyncSession): The database session.

        Returns:
            User: The user object if the role matches one of the allowed roles.

        Raises:
            HTTPException: If the user does not have permission (HTTP 403).
        """
        user = await get_current_user(token, db)
        if user.role.name not in [role.value for role in self.allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action"
            )
        return user
