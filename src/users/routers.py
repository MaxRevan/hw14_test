"""
User Routers Module

This module provides API routes for user-related functionality, including retrieving the current user's information 
and updating the user's avatar. 

Routes:
    - GET /me/:
        Retrieve information about the currently authenticated user.
    - PATCH /avatar:
        Upload and update the avatar of the currently authenticated user.

Dependencies:
    - FastAPI RateLimiter: Limits the number of requests to prevent abuse.
    - Cloudinary: Used for storing and managing user avatars.
    - SQLAlchemy AsyncSession: Handles database operations asynchronously.
    - Custom Authentication: Ensures routes are accessible only to authenticated users.

Usage:
    Import this module and include it in the main FastAPI application using `APIRouter`.
"""


from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession
import cloudinary
import cloudinary.uploader

from config.db import get_db
from config.general import settings
from src.auth.utils import get_current_user
from src.auth.schema import UserResponse
from src.auth.repos import UserRepository
from src.auth.models import User


router = APIRouter()


@router.get("/me/", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Retrieve the current authenticated user's information.

    Args:
        current_user (User): The current authenticated user, fetched via dependency injection.

    Returns:
        UserResponse: The information of the authenticated user.
    """
    return current_user


@router.patch(
        '/avatar', 
        response_model=UserResponse, 
        description='No more than 5 requests per 30 seconds',
        dependencies=[Depends(RateLimiter(times=5, seconds=30))]
)
async def update_avatar_user(
    file: UploadFile = File(), 
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the avatar for the authenticated user.

    The avatar is uploaded to Cloudinary, and the user's profile is updated with the new avatar URL.

    Args:
        file (UploadFile): The uploaded avatar file.
        current_user (User): The current authenticated user, fetched via dependency injection.
        db (AsyncSession): The database session.

    Returns:
        UserResponse: The updated user information including the new avatar URL.

    Raises:
        HTTPException: If an error occurs during avatar upload to Cloudinary or database update.
    """
    cloudinary.config(
        cloud_name=settings.cloudinary_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True
    )
    try:
        r = cloudinary.uploader.upload(
            file.file, 
            public_id=f'avatars/{current_user.username}',
            overwrite=True,
        )
        src_url = cloudinary.CloudinaryImage(f'avatars/{current_user.username}')\
                        .build_url(width=250, height=250, crop='fill', version=r.get('version'))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading avatar: {str(e)}"
        )
    user_repo = UserRepository(db)
    user = await user_repo.update_avatar(current_user.email, src_url)
    return user
