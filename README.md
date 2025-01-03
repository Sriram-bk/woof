# Banking API

A FastAPI-based banking system that implements a double-entry ledger system for tracking financial transactions.

## Features

- User authentication with JWT tokens
- Role-based access control (admin/non-admin users)
- Create and manage customer accounts
- Create bank accounts with initial deposits
- Transfer money between accounts
- Track account balances
- View transaction history
- Double-entry ledger system for accurate financial records

## API Endpoints

### Authentication

#### Register User
```http
POST /api/v1/auth/register
```
Register a new user. By default, users are registered as non-admin users. Admin status must be granted manually in the database.

Request Body:
```json
{
    "email": "john@example.com",
    "password": "secretpassword"
}
```

Response:
```json
{
    "id": 1,
    "email": "john@example.com",
    "is_active": true,
    "is_admin": false,
    "created_at": "2023-12-15T10:30:00Z",
    "updated_at": "2023-12-15T10:30:00Z"
}
```

#### Login
```http
POST /api/v1/auth/token
```
Login to get an access token. Note: The login form uses the email as the username field.

Request Body (form-data):
- `username`: User's email address
- `password`: User's password

Response:
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

### Customers

#### List Customers
```http
GET /api/v1/customers/
```
Returns a paginated list of customers with optional search.

Query Parameters:
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum number of records to return (default: 100, max: 1000)
- `search` (optional): Search term to filter customers by name or email

Response:
```json
{
    "customers": [
        {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com"
        }
    ],
    "total": 1
}
```

#### Get Customer
```http
GET /api/v1/customers/{customer_id}
```
Returns details for a specific customer.

Response:
```json
{
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
}
```

#### List Customer Accounts
```http
GET /api/v1/customers/{customer_id}/accounts
```
Returns a paginated list of accounts for a specific customer.

Query Parameters:
- `skip` (optional): Number of records to skip (default: 0)
- `limit` (optional): Maximum number of records to return (default: 100, max: 1000)

Response:
```json
{
    "accounts": [
        {
            "id": 1,
            "account_number": "2023121500001ABC",
            "customer_id": 1,
            "balance": 1000.00,
            "created_at": "2023-12-15T10:30:00Z"
        }
    ],
    "total": 1,
    "total_balance": 1000.00
}
```

#### Create Customer
```http
POST /api/v1/customers/
```
Create a new customer.

Request Body:
```json
{
    "name": "John Doe",
    "email": "john@example.com",
    "password": "test123"
}
```

### Accounts

#### Create Account
```http
POST /api/v1/accounts/
```
Create a new bank account with an initial deposit.

Request Body:
```json
{
    "customer_id": 1,
    "initial_deposit": 1000.00
}
```

#### Get Account Balance
```http
GET /api/v1/accounts/{account_id}/balance
```
Get the current balance of an account.

Response:
```json
{
    "balance": 1000.00
}
```

### Transfers

#### Create Transfer
```http
POST /api/v1/transfers/
```
Transfer money between accounts.

Request Body:
```json
{
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": 500.00,
    "description": "Payment for services"
}
```

#### Get Transaction History
```http
GET /api/v1/accounts/{account_id}/transactions
```
Get the transaction history for an account.

Response:
```json
{
    "transactions": [
        {
            "id": 1,
            "transaction_type": "TRANSFER",
            "description": "Payment for services",
            "timestamp": "2023-12-15T10:30:00Z",
            "entries": [
                {
                    "id": 1,
                    "entry_type": "DEBIT",
                    "amount": 500.00,
                    "account_id": 1
                }
            ]
        }
    ]
}
```

## Technical Details

- Built with FastAPI and SQLAlchemy
- Uses SQLite database
- Implements double-entry accounting
- All monetary amounts stored in cents to avoid floating-point precision issues
- Account numbers are generated with a unique format: YYYYMMDDNNNNNXXX
  - YYYYMMDD: Current date
  - NNNNN: 5-digit daily sequence number
  - XXX: 3 random alphanumeric characters
- Role-based access control with admin/non-admin users

## Security

- JWT token-based authentication
- Role-based authorization (admin/non-admin)
- Password hashing using bcrypt
- Email-based user identification
- Token expiration

## Future Improvements

- Add admin user management interface
- Add support for different currencies
- Add support for recurring transfers
- Implement account statements generation