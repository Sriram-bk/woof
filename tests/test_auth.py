from fastapi import status

def test_register_user(client):
    """Test user registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["is_admin"] == False
    assert "password" not in data
    assert "hashed_password" not in data

def test_register_duplicate_email(client, normal_user):
    """Test registering with an email that's already taken."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already registered" in response.json()["detail"]

def test_login_success(client, normal_user):
    """Test successful login."""
    response = client.post(
        "/api/v1/auth/token",
        data={  # Note: using form data, not JSON
            "username": "user@example.com",
            "password": "userpass"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_wrong_password(client, normal_user):
    """Test login with wrong password."""
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": "user@example.com",
            "password": "wrongpass"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_login_nonexistent_user(client):
    """Test login with non-existent user."""
    response = client.post(
        "/api/v1/auth/token",
        data={
            "username": "nonexistent@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_protected_route_no_token(client):
    """Test accessing protected route without token."""
    response = client.get("/api/v1/customers/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_protected_route_invalid_token(client):
    """Test accessing protected route with invalid token."""
    headers = {"Authorization": "Bearer invalid_token"}
    response = client.get("/api/v1/customers/", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_protected_route_non_admin(client, normal_user):
    """Test accessing protected route with non-admin token."""
    headers = {"Authorization": f"Bearer {normal_user['token']}"}
    response = client.get("/api/v1/customers/", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_protected_route_admin(client, admin_headers):
    """Test accessing protected route with admin token."""
    response = client.get("/api/v1/customers/", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK 