import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.models.models import Base, User, Customer, Account, Transaction, TransactionType, LedgerEntry, EntryType
from app.auth.utils import create_access_token, get_password_hash
from app.utils import generate_account_number

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def engine():
    """Create test database engine."""
    return create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

@pytest.fixture(scope="session")
def tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session(engine, tables):
    """Create a fresh database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """Create test client with database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    del app.dependency_overrides[get_db]

@pytest.fixture
def admin_user(db_session):
    """Create an admin user and return their token."""
    admin = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminpass"),
        is_admin=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin

@pytest.fixture
def admin_headers(admin_user):
    """Get headers with admin token."""
    access_token = create_access_token(data={"sub": admin_user.email})
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password=get_password_hash("testpass123"),
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def test_customer(db_session, test_user):
    """Create a test customer."""
    customer = Customer(
        name="Test Customer",
        email=test_user.email,
        user_id=test_user.id
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer

@pytest.fixture
def test_account(db_session, test_customer):
    """Create a test account with initial balance."""
    # Create account
    account = Account(
        account_number=generate_account_number(db_session),
        customer_id=test_customer.id
    )
    db_session.add(account)
    db_session.flush()  # Get the account ID
    
    # Create initial deposit transaction
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        description="Initial deposit of $1000.00"
    )
    db_session.add(transaction)
    db_session.flush()  # Get the transaction ID
    
    # Create ledger entry for initial deposit
    ledger_entry = LedgerEntry(
        transaction_id=transaction.id,
        account_id=account.id,
        entry_type=EntryType.CREDIT,
        amount_cents=100000  # $1000.00
    )
    db_session.add(ledger_entry)
    
    db_session.commit()
    db_session.refresh(account)
    return account 

@pytest.fixture
def normal_user(db_session):
    """Create a non-admin user and return their token."""
    user = User(
        email="user@example.com",
        hashed_password=get_password_hash("userpass"),
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    access_token = create_access_token(data={"sub": user.email})
    return {"user": user, "token": access_token}

@pytest.fixture
def normal_user_headers(normal_user):
    """Get headers with normal user token."""
    return {"Authorization": f"Bearer {normal_user['token']}"} 