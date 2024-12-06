"""
Repository layer for managing database operations related to users and roles.

This module contains two repository classes:
- `UserRepository`: Handles operations for `User` models, including creating, retrieving, and updating users.
- `RoleRepository`: Manages operations for `Role` models, including retrieving roles by name.

Dependencies:
- SQLAlchemy: Provides ORM capabilities for database interactions.
- libgravatar: Used to fetch Gravatar images for user avatars.
- Custom utilities for password hashing and schema definitions.

Classes:
    - UserRepository
    - RoleRepository
"""


from libgravatar import Gravatar
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User, Role
from src.auth.pass_utils import get_password_hash
from src.auth.schema import UserCreate, RoleEnum


class UserRepository:
    """
    Repository class for managing `User` data.

    Args:
        session (AsyncSession): SQLAlchemy asynchronous session for database operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, user_create: UserCreate):
        """
        Creates a new user in the database.

        Hashes the user's password, fetches their Gravatar avatar, and assigns the default role.

        Args:
            user_create (UserCreate): Schema containing the new user's details.

        Returns:
            User: The newly created `User` object.
        """
        hashed_password = get_password_hash(user_create.password)
        user_role = await RoleRepository(self.session).get_role_by_name(RoleEnum.USER)
        avatar = None
        try:
            g = Gravatar(user_create.email)
            avatar = g.get_image()
        except Exception as e:
            print(f"Error generating Gravatar: {e}")
            avatar = "https://example.com/default_avatar.png"
        new_user = User(
            username=user_create.username,
            hashed_password=hashed_password,
            email=user_create.email,
            role_id=user_role.id,
            avatar=avatar,
            is_active=False,
        )
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user
    
    async def get_user_by_email(self, email):
        """
        Retrieves a user by their email address.

        Args:
            email (str): The email address of the user.

        Returns:
            User or None: The `User` object if found, otherwise `None`.
        """
        query = select(User).where(User.email == email)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username):
        """
        Retrieves a user by their username.

        Args:
            username (str): The username of the user.

        Returns:
            User or None: The `User` object if found, otherwise `None`.
        """
        query = select(User).where(User.username == username)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def update_avatar(self, email, url: str) -> User:
        """
        Updates a user's avatar URL.

        Args:
            email (str): The user's email address.
            url (str): The new avatar URL.

        Returns:
            User: The updated `User` object.
        """
        from src.auth.utils import get_gravatar_url
        user = await self.get_user_by_email(email)
        if not user.avatar or user.avatar.startswith("https://www.gravatar.com"):
            user.avatar = get_gravatar_url(email)
        else:
            user.avatar = url
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def activate_user(self, user: User):
        """
        Activates a user account.

        Args:
            user (User): The `User` object to activate.

        Returns:
            None
        """
        user.is_active = True
        await self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

class RoleRepository():
    """
    Repository class for managing `Role` data.

    Args:
        session (AsyncSession): SQLAlchemy asynchronous session for database operations.
    """

    def __init__(self, session):
        self.session = session

    
    async def get_role_by_name(self, name: RoleEnum):
        """
        Retrieves a role by its name.

        Args:
            name (RoleEnum): The name of the role to retrieve.

        Returns:
            Role or None: The `Role` object if found, otherwise `None`.
        """
        query = select(Role).where(Role.name == name.value)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


    