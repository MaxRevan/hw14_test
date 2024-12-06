import unittest
from unittest.mock import AsyncMock, MagicMock
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from src.contacts.models import Contact
from src.contacts.schema import ContactCreate
from src.contacts.repos import ContactRepository


class TestContactRepository(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_session = MagicMock(spec=AsyncSession)
        self.contact_repo = ContactRepository(self.mock_session)

    async def test_create_contact(self):
        mock_owner_id = 1
        mock_contact_data = ContactCreate(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="1234567890",
            birthday=date(1990, 1, 1),
            additional_info="info"
        )
        mock_contact = Contact(
            id=1,
            first_name=mock_contact_data.first_name,
            last_name=mock_contact_data.last_name,
            email=mock_contact_data.email,
            phone_number=mock_contact_data.phone_number,
            birthday=mock_contact_data.birthday,
            owner_id=mock_owner_id,
            additional_info=mock_contact_data.additional_info
        )
        self.mock_session.add = MagicMock()
        self.mock_session.commit = AsyncMock()
        self.mock_session.refresh = AsyncMock()
        result = await self.contact_repo.create_contact(mock_contact_data, mock_owner_id)
        added_contact = self.mock_session.add.call_args[0][0]
        self.assertEqual(result.first_name, mock_contact.first_name)
        self.assertEqual(result.last_name, mock_contact.last_name)
        self.assertEqual(result.email, mock_contact.email)
        self.assertEqual(result.phone_number, mock_contact.phone_number)
        self.assertEqual(result.birthday, mock_contact.birthday)
        self.assertEqual(result.owner_id, mock_contact.owner_id)
        self.assertEqual(result.additional_info, mock_contact.additional_info)
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(added_contact)


    async def test_get_contact(self):
        mock_contact_id = 1
        mock_owner_id = 10
        mock_contact = Contact(
            id=mock_contact_id,
            owner_id=mock_owner_id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="1234567890",
            birthday=date(1990, 1, 1),
            additional_info="info"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        self.mock_session.execute = AsyncMock(return_value=mock_result)
        result = await self.contact_repo.get_contact(mock_contact_id, mock_owner_id)
        self.assertEqual(result, mock_contact)
        self.mock_session.execute.assert_called_once()
        query = self.mock_session.execute.call_args[0][0]
        self.assertIn("contact.id = :id_1", str(query))
        self.assertIn("contact.owner_id = :owner_id_1", str(query))


    async def test_get_all_contacts(self):
        mock_owner_id = 10
        mock_contacts = [
            Contact(
                id=1,
                owner_id=mock_owner_id,
                first_name="John",
                last_name="Doe",
                email="john.doe@example.com",
                phone_number="1234567890",
                birthday=date(1990, 1, 1),
                additional_info="info"
            )
        ]
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_contacts
        mock_result.scalars.return_value = mock_scalars
        self.mock_session.execute.return_value = mock_result
        result = await self.contact_repo.get_all_contacts(mock_owner_id)
        self.assertEqual(result, mock_contacts)
        self.mock_session.execute.assert_called_once()
        query = self.mock_session.execute.call_args[0][0]
        self.assertIn("contact.owner_id = :owner_id_1", str(query))


    async def test_update_contact(self):
        mock_contact_id = 1
        mock_owner_id = 10
        mock_contact_data = ContactCreate(
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            phone_number="9876543210",
            birthday=date(1992, 2, 2),
            additional_info="updated info"
        )
        mock_contact = Contact(
            id=mock_contact_id,
            owner_id=mock_owner_id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="1234567890",
            birthday=date(1990, 1, 1),
            additional_info="info"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        self.mock_session.execute.return_value = mock_result
        updated_contact = await self.contact_repo.update_contact(
            contact_id=mock_contact_id,
            contact_data=mock_contact_data,
            owner_id=mock_owner_id
        )
        self.mock_session.execute.assert_called_once()
        self.mock_session.commit.assert_called_once()
        self.mock_session.refresh.assert_called_once_with(mock_contact)
        self.assertEqual(updated_contact.first_name, mock_contact_data.first_name)
        self.assertEqual(updated_contact.last_name, mock_contact_data.last_name)
        self.assertEqual(updated_contact.email, mock_contact_data.email)
        self.assertEqual(updated_contact.phone_number, mock_contact_data.phone_number)
        self.assertEqual(updated_contact.birthday, mock_contact_data.birthday)
        self.assertEqual(updated_contact.additional_info, mock_contact_data.additional_info)
        query = self.mock_session.execute.call_args[0][0]
        self.assertIn("contact.id = :id_1", str(query))
        self.assertIn("contact.owner_id = :owner_id_1", str(query))


    async def test_delete_contact(self):
        mock_contact_id = 1
        mock_owner_id = 10
        mock_contact = Contact(
            id=mock_contact_id,
            owner_id=mock_owner_id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="1234567890",
            birthday=date(1990, 1, 1),
            additional_info="info"
        )
        self.contact_repo.get_contact = AsyncMock(return_value=mock_contact)
        self.mock_session.delete = AsyncMock()
        self.mock_session.commit = AsyncMock()
        result = await self.contact_repo.delete_contact(
            contact_id=mock_contact_id,
            owner_id=mock_owner_id
        )
        self.mock_session.delete.assert_called_once_with(mock_contact)
        self.mock_session.commit.assert_called_once()
        self.assertTrue(result)


    async def test_delete_contact_not_found(self):
        mock_contact_id = 1
        mock_owner_id = 10
        self.contact_repo.get_contact = AsyncMock(return_value=None)
        result = await self.contact_repo.delete_contact(
            contact_id=mock_contact_id,
            owner_id=mock_owner_id
        )
        self.mock_session.delete.assert_not_called()
        self.mock_session.commit.assert_not_called()
        self.assertFalse(result)


    async def test_search_contacts_first_name(self):
        mock_owner_id = 10
        mock_first_name = "John"
        mock_contact = Contact(
            id=1,
            owner_id=mock_owner_id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="1234567890",
            birthday=date(1990, 1, 1),
            additional_info="info"
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_contact]
        self.mock_session.execute = AsyncMock(return_value=mock_result)
        result = await self.contact_repo.search_contacts(
            owner_id=mock_owner_id, 
            first_name=mock_first_name
        )
        self.mock_session.execute.assert_called_once()
        query = self.mock_session.execute.call_args[0][0]
        self.assertIn("lower(contact.first_name) LIKE lower(:first_name_1)", str(query))
        self.assertEqual(result, [mock_contact])


    async def test_search_contacts_last_name(self):
        mock_owner_id = 10
        mock_last_name = "Doe"
        mock_contact = Contact(
            id=1,
            owner_id=mock_owner_id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="1234567890",
            birthday=date(1990, 1, 1),
            additional_info="info"
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_contact]
        self.mock_session.execute = AsyncMock(return_value=mock_result)
        result = await self.contact_repo.search_contacts(
            owner_id=mock_owner_id, 
            last_name=mock_last_name
        )
        self.mock_session.execute.assert_called_once()
        query = self.mock_session.execute.call_args[0][0]
        self.assertIn("lower(contact.last_name) LIKE lower(:last_name_1)", str(query))
        self.assertEqual(result, [mock_contact])

    
    async def test_search_contacts_email(self):
        mock_owner_id = 10
        mock_email = "john.doe@example.com"
        mock_contact = Contact(
            id=1,
            owner_id=mock_owner_id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="1234567890",
            birthday=date(1990, 1, 1),
            additional_info="info"
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_contact]
        self.mock_session.execute = AsyncMock(return_value=mock_result)
        result = await self.contact_repo.search_contacts(
            owner_id=mock_owner_id, 
            email=mock_email
        )
        self.mock_session.execute.assert_called_once()
        query = self.mock_session.execute.call_args[0][0]
        self.assertIn("lower(contact.email) LIKE lower(:email_1)", str(query))
        self.assertEqual(result, [mock_contact])


    async def test_search_contacts_multiple_filters(self):
        mock_owner_id = 10
        mock_first_name = "John"
        mock_last_name = "Doe"
        mock_email = "john.doe@example.com"
        mock_contact = Contact(
            id=1,
            owner_id=mock_owner_id,
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone_number="1234567890",
            birthday=date(1990, 1, 1),
            additional_info="info"
        )
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_contact]
        self.mock_session.execute = AsyncMock(return_value=mock_result)
        result = await self.contact_repo.search_contacts(
            owner_id=mock_owner_id, 
            first_name=mock_first_name, 
            last_name=mock_last_name,
            email=mock_email
        )
        self.mock_session.execute.assert_called_once()
        query = self.mock_session.execute.call_args[0][0]
        self.assertIn("lower(contact.first_name) LIKE lower(:first_name_1)", str(query))
        self.assertIn("lower(contact.last_name) LIKE lower(:last_name_1)", str(query))
        self.assertIn("lower(contact.email) LIKE lower(:email_1)", str(query))
        self.assertEqual(result, [mock_contact])