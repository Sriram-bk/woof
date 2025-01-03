import pytest
from fastapi import status
import re
from datetime import datetime

def test_create_customer(client):
    response = client.post(
        "/api/v1/customers/",
        json={"name": "John Doe", "email": "john@example.com"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["name"] == "John Doe"
    assert data["email"] == "john@example.com"
    assert "id" in data

def test_account_number_format(client, test_customer):
    """Test that generated account numbers follow the correct format"""
    response = client.post(
        "/api/v1/accounts/",
        json={
            "initial_deposit": 1000.00,
            "customer_id": test_customer.id
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Check account number format (YYYYMMDDNNNNNXXX)
    account_number = data["account_number"]
    pattern = r"^\d{8}\d{5}[A-Z0-9]{3}$"
    assert re.match(pattern, account_number), f"Account number {account_number} doesn't match expected format"
    assert len(account_number) == 16, "Account number should be exactly 16 characters"
    
    # Verify date part is current date
    date_part = account_number[:8]
    current_date = datetime.now().strftime("%Y%m%d")
    assert date_part == current_date, "Account number date part should be current date"
    
    # Verify sequence starts from 1
    sequence_part = account_number[8:13]
    assert sequence_part == "00001", "First account of the day should have sequence 00001"

def test_account_number_sequence(client, test_customer):
    """Test that account numbers have sequential numbering within the same day"""
    # Create multiple accounts
    account_numbers = []
    for _ in range(3):
        response = client.post(
            "/api/v1/accounts/",
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

def test_account_number_uniqueness(client, test_customer):
    """Test that generated account numbers are unique"""
    # Create multiple accounts
    account_numbers = set()
    for _ in range(3):
        response = client.post(
            "/api/v1/accounts/",
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

def test_create_account(client, test_customer):
    response = client.post(
        "/api/v1/accounts/",
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

def test_create_account_invalid_customer(client):
    response = client.post(
        "/api/v1/accounts/",
        json={
            "initial_deposit": 1000.00,
            "customer_id": 999  # Non-existent customer
        }
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Customer not found"

def test_get_balance(client, test_account):
    response = client.get(f"/api/v1/accounts/{test_account.id}/balance")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["balance"] == 1000.00

def test_get_balance_invalid_account(client):
    response = client.get("/api/v1/accounts/999/balance")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Account not found"

def test_create_transfer(client, test_account, db_session):
    # Create second account for transfer
    response = client.post(
        "/api/v1/accounts/",
        json={
            "initial_deposit": 500.00,
            "customer_id": test_account.owner.id
        }
    )
    second_account_id = response.json()["id"]
    
    # Perform transfer
    response = client.post(
        "/api/v1/transfers/",
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
    response = client.get(f"/api/v1/accounts/{test_account.id}/balance")
    assert response.json()["balance"] == 700.00  # 1000 - 300
    
    response = client.get(f"/api/v1/accounts/{second_account_id}/balance")
    assert response.json()["balance"] == 800.00  # 500 + 300

def test_transfer_insufficient_funds(client, test_account, db_session):
    # Create second account for transfer
    response = client.post(
        "/api/v1/accounts/",
        json={
            "initial_deposit": 500.00,
            "customer_id": test_account.owner.id
        }
    )
    second_account_id = response.json()["id"]
    
    # Attempt transfer with insufficient funds
    response = client.post(
        "/api/v1/transfers/",
        json={
            "from_account_id": test_account.id,
            "to_account_id": second_account_id,
            "amount": 2000.00,  # More than available balance
            "description": "Test transfer"
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Insufficient funds"

def test_get_transaction_history(client, test_account, db_session):
    # Create second account and make a transfer to generate history
    response = client.post(
        "/api/v1/accounts/",
        json={
            "initial_deposit": 500.00,
            "customer_id": test_account.owner.id
        }
    )
    second_account_id = response.json()["id"]
    
    # Perform transfer
    client.post(
        "/api/v1/transfers/",
        json={
            "from_account_id": test_account.id,
            "to_account_id": second_account_id,
            "amount": 300.00,
            "description": "Test transfer"
        }
    )
    
    # Get transaction history
    response = client.get(f"/api/v1/accounts/{test_account.id}/transactions")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Should have 2 transactions: initial deposit and transfer
    assert len(data["transactions"]) == 2
    
    # Verify transaction types
    transaction_types = [t["transaction_type"] for t in data["transactions"]]
    assert "DEPOSIT" in transaction_types
    assert "TRANSFER" in transaction_types

def test_amount_precision(client, test_customer):
    """Test that monetary amounts are handled precisely"""
    # Create account with a precise amount
    response = client.post(
        "/api/v1/accounts/",
        json={
            "initial_deposit": 100.99,  # Test precise decimal amount
            "customer_id": test_customer.id
        }
    )
    account_id = response.json()["id"]
    
    # Verify the amount is stored and returned correctly
    response = client.get(f"/api/v1/accounts/{account_id}/balance")
    assert response.json()["balance"] == 100.99
    
    # Create second account for transfer
    response = client.post(
        "/api/v1/accounts/",
        json={
            "initial_deposit": 50.00,
            "customer_id": test_customer.id
        }
    )
    second_account_id = response.json()["id"]
    
    # Perform transfer with precise amount
    response = client.post(
        "/api/v1/transfers/",
        json={
            "from_account_id": account_id,
            "to_account_id": second_account_id,
            "amount": 50.99,
            "description": "Test precise transfer"
        }
    )
    
    # Verify both balances are correct after transfer
    response = client.get(f"/api/v1/accounts/{account_id}/balance")
    assert response.json()["balance"] == 50.00  # 100.99 - 50.99
    
    response = client.get(f"/api/v1/accounts/{second_account_id}/balance")
    assert response.json()["balance"] == 100.99  # 50.00 + 50.99 