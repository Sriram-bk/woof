import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.models import Base, Customer, Account, Transaction, LedgerEntry, EntryType

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    # Create all tables for each test
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after each test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def test_customer(db_session):
    customer = Customer(
        name="Test User",
        email="test@example.com"
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer

@pytest.fixture
def test_account(db_session, test_customer):
    # Create account
    account = Account(
        account_number="TEST123",
        customer_id=test_customer.id
    )
    db_session.add(account)
    db_session.flush()
    
    # Create initial deposit transaction
    transaction = Transaction(
        transaction_type="DEPOSIT",
        description="Initial test deposit"
    )
    db_session.add(transaction)
    db_session.flush()
    
    # Create ledger entry (100000 cents = $1000.00)
    entry = LedgerEntry(
        transaction_id=transaction.id,
        account_id=account.id,
        entry_type=EntryType.CREDIT,
        amount_cents=100000
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(account)
    
    return account 