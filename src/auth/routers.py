"""
Authentication Routers for FastAPI

This module contains routes for user registration, email verification, login, 
and token refresh functionalities. It leverages FastAPI, OAuth2, and Jinja2 
for templating and user management.

Routes:
    - `/register`: Handles user registration and sends email verification.
    - `/verify-email`: Verifies the user's email using a token.
    - `/token`: Provides access and refresh tokens for authentication.
    - `/refresh_token`: Refreshes the access token using the provided refresh token.
"""


from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession
from jinja2 import Environment, FileSystemLoader

from config.db import get_db
from src.auth.repos import UserRepository
from src.auth.schema import UserCreate, UserResponse, Token
from src.auth.mail_utils import send_verification
from src.auth.pass_utils import verify_password
from src.auth.utils import (
    create_access_token, 
    create_refresh_token, 
    decode_access_token,
    create_verification_token,
    decode_verification_token,
)


router = APIRouter()
env = Environment(loader=FileSystemLoader("src/templates"))


@router.post(
        "/register", 
        response_model=UserResponse, 
        status_code=status.HTTP_201_CREATED,
        description='No more than 5 requests per 30 seconds',
        dependencies=[Depends(RateLimiter(times=5, seconds=30))]
)
async def register(
    user_create: UserCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),

):
    """
    Register a new user and send a verification email.

    Args:
        user_create (UserCreate): User creation data (email, username, password).
        background_tasks (BackgroundTasks): Background task manager for sending emails.
        db (AsyncSession): Database session.

    Returns:
        UserResponse: Details of the newly registered user.

    Raises:
        HTTPException: If the user already exists (HTTP 409).
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_email(user_create.email)
    if user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already register")
    user = await user_repo.create_user(user_create)
    verification_token = create_verification_token(user.email)
    verification_link = (
        f"http://localhost:8000/auth/verify-email?token={verification_token}"
    )
    template = env.get_template("email.html")
    email_body = template.render(verification_link=verification_link)
    background_tasks.add_task(send_verification, user.email, email_body)
    return user


@router.get("/verify-email")
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Verify the user's email using the token.

    Args:
        token (str): Verification token from the email.
        db (AsyncSession): Database session.

    Returns:
        dict: Success message upon verification.

    Raises:
        HTTPException: If the user is not found (HTTP 404).
    """
    email: str = decode_verification_token(token)
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    await user_repo.activate_user(user)
    return {"msg": "Email verified successfully"}


@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    Authenticate a user and return access and refresh tokens.

    Args:
        form_data (OAuth2PasswordRequestForm): User credentials (username, password).
        db (AsyncSession): Database session.

    Returns:
        Token: Access and refresh tokens with token type.

    Raises:
        HTTPException: If authentication fails (HTTP 401).
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_username(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")


@router.post("/refresh_token", response_model=Token)
async def refresh_token(
    refresh_token: str, db: AsyncSession = Depends(get_db)
):
    """
    Refresh the access token using the provided refresh token.

    Args:
        refresh_token (str): Refresh token to validate and decode.
        db (AsyncSession): Database session.

    Returns:
        Token: New access and refresh tokens with token type.

    Raises:
        HTTPException: If the user does not exist (HTTP 401).
    """
    token_data = decode_access_token(refresh_token)
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_username(token_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    return Token(access_token=access_token, refresh_token=refresh_token, token_type="bearer")