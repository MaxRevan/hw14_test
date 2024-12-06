import pytest
from fastapi import status
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.asyncio
async def test_create_contact(auth_header, override_get_db, faker):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "first_name": faker.first_name(),
            "last_name": faker.user_name(),
            "email": faker.email(),
            "phone_number": faker.phone_number(),
            "birthday": faker.date_of_birth().isoformat(),
            "additional_info": faker.text()
        } 
        response = await ac.post("/contacts/", json=payload, headers=auth_header)                 
        assert response.status_code == 201
        data = response.json()
        assert data['first_name'] == payload["first_name"]
        assert data['last_name'] == payload["last_name"]


@pytest.mark.asyncio
async def test_search_contacts_by_first_name(
    auth_header, 
    test_user_contact, 
    override_get_db,
    db_session, 
    faker
):
    test_user_contact.first_name = faker.first_name()
    test_user_contact.last_name = faker.last_name()
    test_user_contact.email = faker.email()
    async with override_get_db() as session:
        session.add(test_user_contact)
        await session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {"first_name": test_user_contact.first_name}
        response = await ac.get("/contacts/search", params=payload, headers=auth_header)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data[0]["first_name"] == payload["first_name"]
        assert "first_name" in data[0]
        assert len(response.json()) > 0
    