from unittest.mock import patch

from fastapi import BackgroundTasks
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi_limiter import FastAPILimiter
from redis import asyncio as aioredis

from config.general import settings
from src.auth.models import Role
from main import app
from src.auth.utils import get_gravatar_url



@pytest.mark.asyncio
async def test_create_user(user_role: Role, override_get_db, faker):
    redis = aioredis.from_url(settings.redis_url, encoding="utf-8")
    await FastAPILimiter.init(redis)
    with patch.object(BackgroundTasks, "add_task"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            email = faker.email()
            username = faker.user_name()
            password = faker.password()
            avatar = get_gravatar_url(email)
            payload = {
                "email": email,
                "username": username,
                "password": password,
                "avatar": avatar,
            }
            response = await ac.post(
                "/auth/register",
                json=payload,
            )
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == payload["email"]
            assert data["username"] == payload["username"]
            assert data.get("password") is None
            assert data["id"] is not None
            assert data["avatar"] == payload["avatar"]


@pytest.mark.asyncio
async def test_user_login(override_get_db, test_user, user_password):
     async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/auth/token",
            data={
                "username": test_user.username,
                "password": user_password
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

