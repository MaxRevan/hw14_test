"""
Repository layer for managing database operations related to contacts.

This module contains a single repository class, `ContactRepository`, which provides methods
for CRUD operations, searching contacts, and retrieving contacts with upcoming birthdays.

Dependencies:
- SQLAlchemy: For ORM-based database operations.
- datetime: To handle date and time calculations for birthdays.
- Pydantic schemas for validating and passing contact data.

Classes:
    - ContactRepository
"""


from sqlalchemy import select

from datetime import date, timedelta
from typing import List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from src.contacts.models import Contact
from src.contacts.schema import ContactCreate


class ContactRepository:
    """
    Repository class for managing `Contact` data.

    Args:
        session (AsyncSession): SQLAlchemy asynchronous session for database operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session


    async def create_contact(self, contact: ContactCreate, owner_id: int) -> Contact:
        """
        Creates a new contact for a specific owner.

        Args:
            contact (ContactCreate): Schema containing the contact's details.
            owner_id (int): ID of the owner associated with the contact.

        Returns:
            Contact: The newly created `Contact` object.
        """
        new_contact = Contact(**contact.model_dump(), owner_id=owner_id)
        self.session.add(new_contact)
        await self.session.commit()
        await self.session.refresh(new_contact)
        return new_contact


    async def get_contact(self, contact_id: int, owner_id: int) -> Contact:
        """
        Retrieves a contact by its ID and owner ID.

        Args:
            contact_id (int): ID of the contact to retrieve.
            owner_id (int): ID of the owner associated with the contact.

        Returns:
            Contact or None: The `Contact` object if found, otherwise `None`.
        """
        query = select(Contact).where(Contact.id == contact_id).where(Contact.owner_id == owner_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    

    async def get_all_contacts(self, owner_id) -> list[Contact]:
        """
        Retrieves all contacts associated with a specific owner.

        Args:
            owner_id (int): ID of the owner.

        Returns:
            list[Contact]: A list of all `Contact` objects for the owner.
        """
        query = select(Contact).where(Contact.owner_id == owner_id)
        result = await self.session.execute(query)
        return result.scalars().all()
    

    async def update_contact(
        self, 
        contact_id: int, 
        contact_data: ContactCreate, 
        owner_id: int
    ) -> Contact:
        """
        Updates a contact's details.

        Args:
            contact_id (int): ID of the contact to update.
            contact_data (ContactCreate): Schema containing updated contact details.
            owner_id (int): ID of the owner associated with the contact.

        Returns:
            Contact or None: The updated `Contact` object if found, otherwise `None`.
        """
        query = select(Contact).where(Contact.id == contact_id).where(Contact.owner_id == owner_id)
        result = await self.session.execute(query)
        contact = result.scalar_one_or_none()
        if contact:
            for key, value in contact_data.model_dump().items():
                setattr(contact, key, value)
            await self.session.commit()
            await self.session.refresh(contact)
        return contact
    

    async def delete_contact(self, contact_id: int, owner_id: int) -> bool:
        """
        Deletes a contact by its ID and owner ID.

        Args:
            contact_id (int): ID of the contact to delete.
            owner_id (int): ID of the owner associated with the contact.

        Returns:
            bool: `True` if the contact was deleted, otherwise `False`.
        """
        contact = await self.get_contact(contact_id, owner_id=owner_id)
        if contact:
            await self.session.delete(contact)
            await self.session.commit()
            return True
        return False


    async def search_contacts(
        self, 
        owner_id: int,
        first_name: str = None, 
        last_name: str = None, 
        email: str = None
    ) -> List[Contact]:
        """
        Searches for contacts based on optional filters.

        Args:
            owner_id (int): ID of the owner.
            first_name (str, optional): Filter by first name (case-insensitive partial match).
            last_name (str, optional): Filter by last name (case-insensitive partial match).
            email (str, optional): Filter by email (case-insensitive partial match).

        Returns:
            List[Contact]: A list of matching `Contact` objects.
        """
        query = select(Contact).where(Contact.owner_id == owner_id)
        if first_name:
            query = query.filter(Contact.first_name.ilike(f"%{first_name}%"))
        if last_name:
            query = query.filter(Contact.last_name.ilike(f"%{last_name}%"))
        if email:
            query = query.filter(Contact.email.ilike(f"%{email}%"))
        result = await self.session.execute(query)
        return result.scalars().all()
    

    async def get_upcoming_birthdays(self, owner_id: int) -> List[Dict]:
        """
        Retrieves contacts with upcoming birthdays within the next 7 days.

        Args:
            owner_id (int): ID of the owner.

        Returns:
            List[Dict]: A list of dictionaries with contact details and adjusted birthday dates.
        """
        upcoming_birthdays = []
        today = date.today()
        query = (
            select(Contact)
            .where(Contact.owner_id == owner_id)
            .where(Contact.birthday.isnot(None))
        )
        result = await self.session.execute(query)
        async for contact in result.scalars():
            if contact.birthday:
                birthday = contact.birthday

            birthday_this_year = birthday.replace(year=today.year)

            if birthday_this_year < today:
                birthday_this_year = birthday_this_year.replace(year=today.year + 1)

            if today <= birthday_this_year <= today + timedelta(days=7):
                birthday_dict = {
                    "id": contact.id,
                    "first_name": contact.first_name,
                    "last_name": contact.last_name,
                    "email": contact.email or None,
                    "phone_number": contact.phone_number or None,
                    "birthday": birthday_this_year,
                    "additional_info": contact.additional_info or None,
                }

                if birthday_this_year.weekday() >= 5:
                    next_monday = birthday_this_year + timedelta(days=(7 - birthday_this_year.weekday()))
                    birthday_dict["birthday"] = next_monday

                upcoming_birthdays.append(birthday_dict)

        return upcoming_birthdays
