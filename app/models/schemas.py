from pydantic import BaseModel, Field, ConfigDict, computed_field, EmailStr
from typing import List, Optional
from datetime import datetime
from ..models.models import EntryType, TransactionType

class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class CustomerBase(BaseModel):
    name: str
    email: EmailStr

class CustomerCreate(CustomerBase):
    name: str
    email: EmailStr
    password: str  # Password for the associated user account

class CustomerResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)

class Customer(CustomerBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AccountCreate(BaseModel):
    initial_deposit: float = Field(gt=0)
    customer_id: int

    def get_initial_deposit_cents(self) -> int:
        """Convert initial deposit from dollars to cents"""
        return int(self.initial_deposit * 100)

class LedgerEntryBase(BaseModel):
    entry_type: EntryType
    amount_cents: int = Field(gt=0)

    @computed_field
    def amount(self) -> float:
        """Get amount in dollars"""
        return self.amount_cents / 100

class LedgerEntry(LedgerEntryBase):
    id: int
    transaction_id: int
    account_id: int
    model_config = ConfigDict(from_attributes=True)

class TransactionBase(BaseModel):
    transaction_type: TransactionType
    description: str

class Transaction(TransactionBase):
    id: int
    timestamp: datetime
    entries: List[LedgerEntry]
    model_config = ConfigDict(from_attributes=True)

class Account(BaseModel):
    id: int
    account_number: str
    customer_id: int
    balance_cents: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def balance(self) -> float:
        """Get balance in dollars"""
        return self.balance_cents / 100

class CustomerList(BaseModel):
    """Response model for list of customers"""
    customers: List[Customer]
    total: int

class AccountList(BaseModel):
    """Response model for list of accounts"""
    accounts: List[Account]
    total: int
    total_balance: float

class TransferCreate(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float = Field(gt=0)
    description: str = "Transfer between accounts"

    def get_amount_cents(self) -> int:
        """Convert amount from dollars to cents"""
        return int(self.amount * 100)

class TransactionHistory(BaseModel):
    transactions: List[Transaction] 