from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import List
from datetime import datetime
from ..models.models import EntryType, TransactionType

class CustomerBase(BaseModel):
    name: str
    email: str

class CustomerCreate(CustomerBase):
    pass

class Customer(CustomerBase):
    id: int
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
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    def balance(self) -> float:
        """Get balance in dollars"""
        return self.balance_cents / 100

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