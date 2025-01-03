from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, func, Boolean
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import enum

class Base(DeclarativeBase):
    pass

class EntryType(enum.Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class TransactionType(enum.Enum):
    DEPOSIT = "DEPOSIT"
    TRANSFER = "TRANSFER"
    WITHDRAWAL = "WITHDRAWAL"

class DailyAccountSequence(Base):
    __tablename__ = "daily_account_sequences"
    
    date = Column(String, primary_key=True)
    sequence = Column(Integer, default=0)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationship to customers they can manage
    customers = relationship("Customer", back_populates="user")

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    accounts = relationship("Account", back_populates="customer")
    user = relationship("User", back_populates="customers")

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    account_number = Column(String, unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    created_at = Column(DateTime, default=datetime.now())
    customer = relationship("Customer", back_populates="accounts")
    ledger_entries = relationship("LedgerEntry", back_populates="account")

    @property
    def balance_cents(self):
        """Calculate balance in cents from ledger entries"""
        balance = 0
        for entry in self.ledger_entries:
            if entry.entry_type == EntryType.CREDIT:
                balance += entry.amount_cents
            else:
                balance -= entry.amount_cents
        return balance

    @property
    def balance(self):
        """Calculate balance in dollars from cents"""
        return self.balance_cents / 100

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_type = Column(Enum(TransactionType))
    timestamp = Column(DateTime, default=datetime.utcnow)
    description = Column(String)
    entries = relationship("LedgerEntry", back_populates="transaction")

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    account_id = Column(Integer, ForeignKey("accounts.id"))
    entry_type = Column(Enum(EntryType))
    amount_cents = Column(Integer)
    
    transaction = relationship("Transaction", back_populates="entries")
    account = relationship("Account", back_populates="ledger_entries")

    @property
    def amount(self):
        """Get amount in dollars"""
        return self.amount_cents / 100 