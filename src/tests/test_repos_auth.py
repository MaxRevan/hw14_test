import unittest
from unittest import mock
from unittest.mock import AsyncMock, patch
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.auth.repos import UserRepository, RoleRepository
from src.auth.schema import UserCreate
from src.auth.models import User, Role
from src.auth.schema import RoleEnum



class TestUserRepository(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_session = AsyncMock(spec=AsyncSession)
        self.user_repo = UserRepository(self.mock_session)
        self.role_repo = RoleRepository(self.mock_session)


    @patch("src.auth.repos.RoleRepository.get_role_by_name")
    @patch("src.auth.repos.Gravatar")
    async def test_create_user(self, MockGravatar, MockGetRoleByName):
        mock_gravatar_instance = MockGravatar.return_value
        mock_gravatar_instance.get_image.return_value = "https://example.com/default_avatar.png"
        MockGetRoleByName.return_value = Role(id=1, name="user")
        user_create = UserCreate(
            username="testuser", 
            password="testpassword", 
            email="test@example.com", 
            avatar="https://example.com/default_avatar.png"
        )
        new_user = await self.user_repo.create_user(user_create)
        self.assertEqual(new_user.username, "testuser")
        self.assertEqual(new_user.email, "test@example.com")
        self.assertEqual(new_user.avatar, "https://example.com/default_avatar.png")
        self.mock_session.add.assert_called_once_with(new_user)
        self.mock_session.commit.assert_called_once()


    @patch("src.auth.repos.AsyncSession")
    async def test_get_user_by_email(self, MockSession):
        mock_user = User(
            username="testuser", 
            email="test@example.com", 
            hashed_password="hashed_password", 
            role_id=1, 
            avatar="avatar.png"
        )
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = mock_user
        mock_session_instance = MockSession.return_value
        mock_session_instance.execute = AsyncMock(return_value=mock_execute_result)
        self.user_repo = UserRepository(mock_session_instance)
        user = await self.user_repo.get_user_by_email("test@example.com")
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "test@example.com")
        self.assertEqual(user.username, "testuser")
        expected_query = select(User).where(User.email == "test@example.com")
        actual_query_str = str(mock_session_instance.execute.call_args[0][0])
        expected_query_str = str(expected_query)
        self.assertEqual(actual_query_str, expected_query_str)


    @patch("src.auth.repos.AsyncSession")
    async def test_get_user_by_username(self, MockSession):
        mock_user = User(username="testuser", email="test@example.com")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        self.mock_session.execute.return_value = mock_result
        user = await self.user_repo.get_user_by_username("testuser")
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        expected_query = select(User).where(User.username == "testuser")
        actual_query_str = str(self.mock_session.execute.call_args[0][0])
        expected_query_str = str(expected_query)
        self.assertEqual(actual_query_str, expected_query_str)


    @patch("src.auth.repos.AsyncSession")
    async def test_activate_user(self, MockSession):
        mock_session_instance = MockSession.return_value.__aenter__.return_value
        mock_session_instance.add = AsyncMock()
        mock_session_instance.commit = AsyncMock()
        mock_session_instance.refresh = AsyncMock()
        mock_user = User(username="testuser", email="test@example.com", is_active=False)
        user_repo = UserRepository(session=mock_session_instance)
        await user_repo.activate_user(mock_user)
        assert mock_user.is_active is True
        mock_session_instance.add.assert_called_once_with(mock_user)
        mock_session_instance.commit.assert_called_once()
        mock_session_instance.refresh.assert_called_once_with(mock_user)


class TestRoleRepository(unittest.IsolatedAsyncioTestCase):

    @patch("src.auth.repos.AsyncSession")  
    async def test_get_role_by_name(self, MockSession):
        mock_session_instance = MockSession.return_value.__aenter__.return_value
        mock_session_instance.execute = AsyncMock()
        mock_role = Role(name=RoleEnum.ADMIN)
        mock_session_instance.execute.return_value.scalar_one_or_none = MagicMock(return_value = mock_role)
        role_repo = RoleRepository(session=mock_session_instance)
        result = await role_repo.get_role_by_name(RoleEnum.ADMIN)
        self.assertEqual(result, mock_role)
        mock_session_instance.execute.assert_called_once()


    @patch("src.auth.repos.AsyncSession") 
    async def test_get_role_by_name_not_found(self, MockSession):
        mock_session_instance = MockSession.return_value.__aenter__.return_value
        mock_session_instance.execute = AsyncMock()
        mock_session_instance.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
        role_repo = RoleRepository(session=mock_session_instance)
        result = await role_repo.get_role_by_name(RoleEnum.ADMIN)
        self.assertIsNone(result)
        mock_session_instance.execute.assert_called_once()
