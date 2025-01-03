import pytest
from fastapi import status
import re
from datetime import datetime

def test_create_customer(client, admin_headers):
    response = client.post(
        "/api/v1/customers/",
        headers=admin_headers,
        json={
            "name": "John Doe",
            "email": "john@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"

def test_account_number_format(client, test_customer, admin_headers):
    """Test that generated account numbers follow the correct format"""
    response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "initial_deposit": 1000.00,
            "customer_id": test_customer.id
        }
    )
    assert response.status_code == status.HTTP_200_OK
    account_number = response.json()["account_number"]
    
    # Verify format: YYYYMMDDNNNNNXXX
    assert len(account_number) == 16
    assert account_number[:8].isdigit()  # Date part
    assert account_number[8:13].isdigit()  # Sequence
    assert account_number[13:].isalnum()  # Random part

def test_account_number_sequence(client, test_customer, admin_headers):
    """Test that account numbers have sequential numbering within the same day"""
    # Create multiple accounts
    account_numbers = []
    for _ in range(3):
        response = client.post(
            "/api/v1/accounts/",
            headers=admin_headers,
            json={
                "initial_deposit": 1000.00,
                "customer_id": test_customer.id
            }
        )
        assert response.status_code == status.HTTP_200_OK
        account_numbers.append(response.json()["account_number"])
    
    # Extract and verify sequences
    sequences = [int(num[8:13]) for num in account_numbers]
    assert sequences == [1, 2, 3], "Account sequences should be consecutive"
    
    # Verify date part remains constant
    date_parts = set(num[:8] for num in account_numbers)
    assert len(date_parts) == 1, "All accounts should have same date"

def test_account_number_uniqueness(client, test_customer, admin_headers):
    """Test that generated account numbers are unique"""
    # Create multiple accounts
    account_numbers = set()
    for _ in range(3):
        response = client.post(
            "/api/v1/accounts/",
            headers=admin_headers,
            json={
                "initial_deposit": 1000.00,
                "customer_id": test_customer.id
            }
        )
        assert response.status_code == status.HTTP_200_OK
        account_number = response.json()["account_number"]
        
        # Verify this account number hasn't been seen before
        assert account_number not in account_numbers, "Duplicate account number generated"
        account_numbers.add(account_number)

def test_create_account(client, test_customer, admin_headers):
    response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "initial_deposit": 1000.00,
            "customer_id": test_customer.id
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["customer_id"] == test_customer.id
    assert data["balance"] == 1000.00
    assert data["balance_cents"] == 100000

def test_create_account_invalid_customer(client, admin_headers):
    response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "initial_deposit": 1000.00,
            "customer_id": 999  # Non-existent customer
        }
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Customer not found"

def test_get_balance(client, test_account, admin_headers):
    response = client.get(
        f"/api/v1/accounts/{test_account.id}/balance",
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["balance"] == 1000.00

def test_get_balance_invalid_account(client, admin_headers):
    response = client.get(
        "/api/v1/accounts/999/balance",
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Account not found"

def test_create_transfer(client, test_account, db_session, admin_headers):
    # Create second account for transfer
    response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "initial_deposit": 500.00,
            "customer_id": test_account.customer.id
        }
    )
    second_account_id = response.json()["id"]
    
    # Perform transfer
    response = client.post(
        "/api/v1/transfers/",
        headers=admin_headers,
        json={
            "from_account_id": test_account.id,
            "to_account_id": second_account_id,
            "amount": 300.00,
            "description": "Test transfer"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["transaction_type"] == "TRANSFER"
    assert len(data["entries"]) == 2
    
    # Verify balances
    response = client.get(
        f"/api/v1/accounts/{test_account.id}/balance",
        headers=admin_headers
    )
    assert response.json()["balance"] == 700.00  # 1000 - 300
    
    response = client.get(
        f"/api/v1/accounts/{second_account_id}/balance",
        headers=admin_headers
    )
    assert response.json()["balance"] == 800.00  # 500 + 300

def test_transfer_insufficient_funds(client, test_account, db_session, admin_headers):
    # Create second account for transfer
    response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "initial_deposit": 500.00,
            "customer_id": test_account.customer.id
        }
    )
    second_account_id = response.json()["id"]
    
    # Attempt transfer with insufficient funds
    response = client.post(
        "/api/v1/transfers/",
        headers=admin_headers,
        json={
            "from_account_id": test_account.id,
            "to_account_id": second_account_id,
            "amount": 2000.00,  # More than available balance
            "description": "Test transfer"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Insufficient funds"

def test_get_transaction_history(client, test_account, db_session, admin_headers):
    # Create second account and make a transfer to generate history
    response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "initial_deposit": 500.00,
            "customer_id": test_account.customer.id
        }
    )
    second_account_id = response.json()["id"]
    
    # Perform transfer
    client.post(
        "/api/v1/transfers/",
        headers=admin_headers,
        json={
            "from_account_id": test_account.id,
            "to_account_id": second_account_id,
            "amount": 300.00,
            "description": "Test transfer"
        }
    )
    
    # Get transaction history
    response = client.get(
        f"/api/v1/accounts/{test_account.id}/transactions",
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Should have 2 transactions: initial deposit and transfer
    assert len(data["transactions"]) == 2
    
    # Verify transaction types
    transaction_types = [t["transaction_type"] for t in data["transactions"]]
    assert "DEPOSIT" in transaction_types
    assert "TRANSFER" in transaction_types

def test_amount_precision(client, test_customer, admin_headers):
    """Test that monetary amounts are handled precisely"""
    # Create account with a precise amount
    response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "initial_deposit": 100.99,  # Test precise decimal amount
            "customer_id": test_customer.id
        }
    )
    account_id = response.json()["id"]
    
    # Verify the amount is stored and returned correctly
    response = client.get(f"/api/v1/accounts/{account_id}/balance", headers=admin_headers)
    assert response.json()["balance"] == 100.99
    
    # Create second account for transfer
    response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "initial_deposit": 50.00,
            "customer_id": test_customer.id
        }
    )
    second_account_id = response.json()["id"]
    
    # Perform transfer with precise amount
    response = client.post(
        "/api/v1/transfers/",
        headers=admin_headers,
        json={
            "from_account_id": account_id,
            "to_account_id": second_account_id,
            "amount": 50.99,
            "description": "Test precise transfer"
        }
    )
    
    # Verify both balances are correct after transfer
    response = client.get(f"/api/v1/accounts/{account_id}/balance", headers=admin_headers)
    assert response.json()["balance"] == 50.00  # 100.99 - 50.99
    
    response = client.get(f"/api/v1/accounts/{second_account_id}/balance", headers=admin_headers)
    assert response.json()["balance"] == 100.99  # 50.00 + 50.99 

def test_create_customer_admin(client, admin_headers):
    """Test creating a customer as admin."""
    response = client.post(
        "/api/v1/customers/",
        headers=admin_headers,
        json={
            "name": "John Doe", 
            "email": "john@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"

def test_create_customer_no_auth(client):
    """Test creating a customer without authentication."""
    response = client.post(
        "/api/v1/customers/",
        json={"name": "John Doe", "email": "john@example.com"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_create_customer_non_admin(client, normal_user):
    """Test creating a customer as non-admin user."""
    headers = {"Authorization": f"Bearer {normal_user['token']}"}
    response = client.post(
        "/api/v1/customers/",
        headers=headers,
        json={"name": "John Doe", "email": "john@example.com"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_get_customers_admin(client, admin_headers):
    """Test getting customers list as admin."""
    # First create a customer
    client.post(
        "/api/v1/customers/",
        headers=admin_headers,
        json={"name": "John Doe", "email": "john@example.com", "password": "testpass123"}
    )
    
    response = client.get("/api/v1/customers/", headers=admin_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total"] == 1
    assert len(data["customers"]) == 1
    assert data["customers"][0]["name"] == "John Doe"

def test_create_account_admin(client, admin_headers):
    """Test creating an account as admin."""
    # First create a customer
    customer_response = client.post(
        "/api/v1/customers/",
        headers=admin_headers,
        json={"name": "John Doe", "email": "john@example.com", "password": "testpass123"}
    )
    customer_id = customer_response.json()["id"]
    
    response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "customer_id": customer_id,
            "initial_deposit": 1000.00
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["customer_id"] == customer_id
    assert data["balance"] == 1000.00

def test_create_transfer_admin(client, admin_headers):
    """Test creating a transfer as admin."""
    # Create customer
    customer_response = client.post(
        "/api/v1/customers/",
        headers=admin_headers,
        json={"name": "John Doe", "email": "john@example.com", "password": "testpass123"}
    )
    customer_id = customer_response.json()["id"]
    
    # Create two accounts
    account1_response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "customer_id": customer_id,
            "initial_deposit": 1000.00
        }
    )
    account2_response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "customer_id": customer_id,
            "initial_deposit": 500.00
        }
    )
    
    account1_id = account1_response.json()["id"]
    account2_id = account2_response.json()["id"]
    
    # Create transfer
    response = client.post(
        "/api/v1/transfers/",
        headers=admin_headers,
        json={
            "from_account_id": account1_id,
            "to_account_id": account2_id,
            "amount": 300.00,
            "description": "Test transfer"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Verify balances
    balance1_response = client.get(
        f"/api/v1/accounts/{account1_id}/balance",
        headers=admin_headers
    )
    balance2_response = client.get(
        f"/api/v1/accounts/{account2_id}/balance",
        headers=admin_headers
    )
    
    assert balance1_response.json()["balance"] == 700.00  # 1000 - 300
    assert balance2_response.json()["balance"] == 800.00  # 500 + 300

def test_get_transaction_history_admin(client, admin_headers):
    """Test getting transaction history as admin."""
    # Create customer and account with initial deposit
    customer_response = client.post(
        "/api/v1/customers/",
        headers=admin_headers,
        json={"name": "John Doe", "email": "john@example.com", "password": "testpass123"}
    )
    customer_id = customer_response.json()["id"]
    
    account_response = client.post(
        "/api/v1/accounts/",
        headers=admin_headers,
        json={
            "customer_id": customer_id,
            "initial_deposit": 1000.00
        }
    )
    account_id = account_response.json()["id"]
    
    # Get transaction history
    response = client.get(
        f"/api/v1/accounts/{account_id}/transactions",
        headers=admin_headers
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["transactions"]) == 1  # Initial deposit transaction
    assert data["transactions"][0]["transaction_type"] == "DEPOSIT" 