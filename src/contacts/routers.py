"""
Contacts Routers for FastAPI

This module handles operations for managing contacts, including creation, 
retrieval, updating, deletion, and searching. Rate limiting is applied to all 
routes to ensure fair usage.

Routes:
    - `/search`: Search contacts by first name, last name, or email.
    - `/upcoming_birthdays`: Retrieve contacts with upcoming birthdays in the next 7 days.
    - `/`: Retrieve all contacts for a user, with an option for admin access to all contacts.
    - `/{contact_id}`: Retrieve, update, or delete a specific contact.
    - `/all/`: Admin-only route to retrieve all contacts.
"""


from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_limiter.depends import RateLimiter

from config.db import get_db
from src.contacts.schema import ContactCreate, ContactResponse, ContactUpdate
from src.contacts.repos import ContactRepository
from src.auth.models import User
from src.auth.utils import get_current_user, RoleChecker
from src.auth.schema import RoleEnum


router = APIRouter()


@router.get(
        "/search", 
        response_model=list[ContactResponse], 
        description='No more than 5 requests per 30 seconds',
        dependencies=[Depends(RateLimiter(times=5, seconds=30))]
)
async def search_contacts(
    first_name: str = Query(None, alias="first_name"),
    last_name: str = Query(None),
    email: str = Query(None),
    user: User = Depends(RoleChecker([RoleEnum.USER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for contacts by first name, last name, or email.

    Args:
        first_name (str, optional): The first name to search for.
        last_name (str, optional): The last name to search for.
        email (str, optional): The email to search for.
        user (User): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        list[ContactResponse]: A list of contacts matching the search criteria.

    Raises:
        HTTPException: If no search parameters are provided.
    """
    if not first_name and not last_name and not email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="At least one search parameter is required")
    contact_repo = ContactRepository(db)
    contacts = await contact_repo.search_contacts(
        user.id,
        first_name=first_name, 
        last_name=last_name, 
        email=email
    )
    return contacts


@router.get(
        "/upcoming_birthdays", 
        description='No more than 5 requests per 30 seconds',
        dependencies=[Depends(RateLimiter(times=5, seconds=30))],
        response_model=list[ContactResponse]
)
async def upcoming_birthdays(
    user: User = Depends(RoleChecker([RoleEnum.USER, RoleEnum.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve contacts with birthdays in the next 7 days.

    Args:
        user (User): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        list[ContactResponse]: A list of contacts with upcoming birthdays.

    Raises:
        HTTPException: If no contacts with upcoming birthdays are found.
    """
    contact_repo = ContactRepository(db)
    contacts = await contact_repo.get_upcoming_birthdays(user.id)
    print(f"Found {len(contacts)} upcoming birthdays for user {user.id}")
    if not contacts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No contacts with birthdays in the next 7 days"
        )
    return contacts


@router.post("/", 
            response_model=ContactResponse, 
            status_code=status.HTTP_201_CREATED,
            description='No more than 5 requests per 30 seconds',
            dependencies=[Depends(RateLimiter(times=5, seconds=30))]
)
async def create_contact(
    contact: ContactCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new contact.

    Args:
        contact (ContactCreate): The contact creation data.
        user (User): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        ContactResponse: The created contact.
    """
    contact_repo = ContactRepository(db)
    return await contact_repo.create_contact(contact, user.id)
     

@router.get(
        "/{contact_id}", 
        description='No more than 5 requests per 30 seconds',
        dependencies=[Depends(RateLimiter(times=5, seconds=30))],
        response_model=ContactResponse
)
async def get_contact(
    contact_id: int, 
    user: User = Depends(RoleChecker([RoleEnum.USER, RoleEnum.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a specific contact by ID.

    Args:
        contact_id (int): The ID of the contact.
        user (User): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        ContactResponse: The retrieved contact.

    Raises:
        HTTPException: If the contact is not found.
    """
    contact_repo = ContactRepository(db)
    contact = await contact_repo.get_contact(contact_id, user.id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.get(
        "/", 
        response_model=list[ContactResponse], 
        description='No more than 5 requests per 30 seconds',
        dependencies=[Depends(RateLimiter(times=5, seconds=30))],
)
async def get_all_contacts(
    user: User = Depends(RoleChecker([RoleEnum.ADMIN, RoleEnum.USER])),
    # user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all contacts for the current user.

    Args:
        user (User): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        list[ContactResponse]: A list of all contacts for the user.
    """
    contact_repo = ContactRepository(db)
    contacts = await contact_repo.get_all_contacts(user.id)
    return contacts


@router.get(
    "/all/",
    response_model=list[ContactResponse],
    description='No more than 5 requests per 30 seconds',
    dependencies=[Depends(RateLimiter(times=5, seconds=30))],
    tags=["admin"],
)
async def get_contacts(
    user: User = Depends(RoleChecker([RoleEnum.ADMIN])), 
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only route to retrieve all contacts in the system.

    Args:
        user (User): The current authenticated admin user.
        db (AsyncSession): Database session dependency.

    Returns:
        list[ContactResponse]: A list of all contacts.
    """
    contact_repo = ContactRepository(db)
    return await contact_repo.get_all_contacts(user.id)


@router.put(
        "/{contact_id}", 
        response_model=ContactResponse, 
        status_code=status.HTTP_200_OK,
        description='No more than 5 requests per 30 seconds',
        dependencies=[Depends(RateLimiter(times=5, seconds=30))]
)
async def update_contact(
    contact_id: int, 
    contact_data: ContactUpdate, 
    user: User = Depends(RoleChecker([RoleEnum.USER, RoleEnum.ADMIN])),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing contact by ID.

    Args:
        contact_id (int): The ID of the contact to update.
        contact_data (ContactUpdate): The updated contact data.
        user (User): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        ContactResponse: The updated contact.

    Raises:
        HTTPException: If the contact is not found.
    """
    contact_repo = ContactRepository(db)
    contact = await contact_repo.update_contact(contact_id, contact_data, user.id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.delete(
        "/{contact_id}", 
        status_code=status.HTTP_204_NO_CONTENT,
        description='No more than 5 requests per 30 seconds',
        dependencies=[Depends(RateLimiter(times=5, seconds=30))]
)
async def delete_contact(
    contact_id: int, 
    user: User = Depends(RoleChecker([RoleEnum.USER])),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific contact by ID.

    Args:
        contact_id (int): The ID of the contact to delete.
        user (User): The current authenticated user.
        db (AsyncSession): Database session dependency.

    Returns:
        dict: Confirmation message indicating successful deletion.

    Raises:
        HTTPException: If the contact is not found.
    """
    contact_repo = ContactRepository(db)
    success = await contact_repo.delete_contact(contact_id, user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return {"message": "Contact deleted successfully"}


