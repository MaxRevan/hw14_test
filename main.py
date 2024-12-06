"""
Main application setup for FastAPI.

This module initializes the FastAPI application with middleware, 
routers, and caching configurations. It also sets up Redis for 
rate limiting and caching purposes.

Modules:
    - FastAPI: The core application framework.
    - FastAPICache: Used for caching responses with a Redis backend.
    - FastAPILimiter: Implements rate limiting using Redis.
    - CORSMiddleware: Adds Cross-Origin Resource Sharing (CORS) support.
    - aioredis: Provides asynchronous Redis connection management.

Routers:
    - contacts_router: Handles contact-related endpoints.
    - auth_router: Manages authentication-related endpoints.
    - users_router: Manages user-related endpoints.

Lifespan:
    The lifespan context manager ensures proper setup and teardown 
    of Redis connections during the application lifecycle.
"""


from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from fastapi_limiter import FastAPILimiter
from fastapi.middleware.cors import CORSMiddleware
from redis import asyncio as aioredis

from config.general import settings
from src.contacts.routers import router as contacts_router
from src.auth.routers import router as auth_router
from src.users.routers import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for the FastAPI application.

    Handles setup and teardown tasks for the application lifecycle, 
    including initializing Redis for rate limiting and caching.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: Provides a context for the lifespan of the app.
    """
    # Startup event
    redis = aioredis.from_url(settings.redis_url, encoding="utf-8")
    await FastAPILimiter.init(redis)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
    yield
    # Shutdown event
    await redis.close()


app = FastAPI(lifespan=lifespan)


origins = [ 
    "http://localhost:3000"
    ]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(contacts_router, prefix="/contacts", tags=["contacts"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="/users", tags=["users"])