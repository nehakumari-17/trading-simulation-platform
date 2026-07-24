"""
Tests for authentication routes.
  POST /api/auth/register
  POST /api/auth/login
  GET  /api/auth/me
"""

import pytest


@pytest.mark.asyncio
class TestRegister:

    async def test_register_success(self, client):
        res = await client.post("/api/auth/register", json={
            "username": "newuser",
            "email":    "newuser@test.com",
            "password": "pass1234",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["username"] == "newuser"
        assert data["email"]    == "newuser@test.com"
        assert "password"       not in data       # password must never be returned
        assert "hashed_password" not in data
        assert "id"             in data
        assert data["is_active"] is True

    async def test_register_duplicate_email(self, client):
        payload = {"username": "u1", "email": "dup@test.com", "password": "pass"}
        await client.post("/api/auth/register", json=payload)

        # same email, different username
        res = await client.post("/api/auth/register", json={
            "username": "u2", "email": "dup@test.com", "password": "pass"
        })
        assert res.status_code == 400
        assert "email" in res.json()["detail"].lower()

    async def test_register_duplicate_username(self, client):
        await client.post("/api/auth/register", json={
            "username": "sameuser", "email": "a@test.com", "password": "pass"
        })
        res = await client.post("/api/auth/register", json={
            "username": "sameuser", "email": "b@test.com", "password": "pass"
        })
        assert res.status_code == 400
        assert "username" in res.json()["detail"].lower()

    async def test_register_creates_portfolio(self, client):
        # after registration, the user should have a portfolio with ₹10 lakh
        await client.post("/api/auth/register", json={
            "username": "portfoliouser",
            "email":    "portfolio@test.com",
            "password": "pass1234",
        })
        login = await client.post("/api/auth/login", json={
            "email": "portfolio@test.com", "password": "pass1234"
        })
        token   = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.get("/api/portfolio/summary", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["cash_balance"] == 1_000_000.0

    async def test_register_invalid_email(self, client):
        res = await client.post("/api/auth/register", json={
            "username": "baduser",
            "email":    "not-an-email",
            "password": "pass1234",
        })
        assert res.status_code == 422   # pydantic validation error


@pytest.mark.asyncio
class TestLogin:

    async def test_login_success(self, client):
        await client.post("/api/auth/register", json={
            "username": "loginuser",
            "email":    "login@test.com",
            "password": "mypassword",
        })
        res = await client.post("/api/auth/login", json={
            "email":    "login@test.com",
            "password": "mypassword",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20   # JWT is always long

    async def test_login_wrong_password(self, client):
        await client.post("/api/auth/register", json={
            "username": "wrongpass",
            "email":    "wrongpass@test.com",
            "password": "correct",
        })
        res = await client.post("/api/auth/login", json={
            "email":    "wrongpass@test.com",
            "password": "incorrect",
        })
        assert res.status_code == 401

    async def test_login_nonexistent_user(self, client):
        res = await client.post("/api/auth/login", json={
            "email":    "nobody@test.com",
            "password": "pass",
        })
        assert res.status_code == 401

    async def test_login_wrong_email_format(self, client):
        res = await client.post("/api/auth/login", json={
            "email":    "notanemail",
            "password": "pass",
        })
        assert res.status_code == 422


@pytest.mark.asyncio
class TestMe:

    async def test_me_returns_user(self, client, auth_headers):
        res = await client.get("/api/auth/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["email"]    == "test@example.com"
        assert data["username"] == "testuser"
        assert "password"       not in data

    async def test_me_no_token(self, client):
        res = await client.get("/api/auth/me")
        assert res.status_code == 401

    async def test_me_invalid_token(self, client):
        res = await client.get("/api/auth/me", headers={
            "Authorization": "Bearer this.is.not.a.valid.token"
        })
        assert res.status_code == 401
