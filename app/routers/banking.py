from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db
from ..models import models, schemas
from ..models.models import EntryType, TransactionType
from ..utils import generate_account_number
from ..auth.utils import get_current_admin, get_password_hash

router = APIRouter(dependencies=[Depends(get_current_admin)])

@router.get("/customers/", response_model=schemas.CustomerList)
def get_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get list of customers with optional search and pagination.
    
    Args:
        skip: Number of customers to skip (offset)
        limit: Maximum number of customers to return
        search: Optional search term for customer name or email
        db: Database session
    """
    query = db.query(models.Customer)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (models.Customer.name.ilike(search_term)) |
            (models.Customer.email.ilike(search_term))
        )
    query = query.order_by(models.Customer.id.asc())
    
    total = query.count()
    customers = query.offset(skip).limit(limit).all()
    
    return {
        "customers": customers,
        "total": total
    }

@router.get("/customers/{customer_id}", response_model=schemas.Customer)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """
    Get customer details.
    
    Args:
        customer_id: ID of the customer
        db: Database session
    """
    customer = (
        db.query(models.Customer)
        .filter(models.Customer.id == customer_id)
        .first()
    )
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return customer

@router.get("/customers/{customer_id}/accounts", response_model=schemas.AccountList)
def get_customer_accounts(
    customer_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get all accounts for a specific customer with pagination.
    
    Args:
        customer_id: ID of the customer
        skip: Number of accounts to skip (offset)
        limit: Maximum number of accounts to return
        db: Database session
    """
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    query = db.query(models.Account).filter(models.Account.customer_id == customer_id)
    
    total = query.count()
    
    accounts = query.order_by(models.Account.created_at.desc()).offset(skip).limit(limit).all()

    total_balance = sum(account.balance for account in accounts)
    
    return {
        "accounts": accounts,
        "total": total,
        "total_balance": total_balance
    }

@router.post("/customers/", response_model=schemas.CustomerResponse)
def create_customer(
    customer: schemas.CustomerCreate,
    db: Session = Depends(get_db)
):
    """Create a new customer."""
    # Check if user with email already exists
    existing_user = db.query(models.User).filter(models.User.email == customer.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user = models.User(
        email=customer.email,
        hashed_password=get_password_hash(customer.password),
        is_admin=False
    )
    db.add(user)
    db.flush()  # Get the user ID
    
    # Create customer
    db_customer = models.Customer(
        name=customer.name,
        email=customer.email,
        user_id=user.id
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    
    return schemas.CustomerResponse(
        id=db_customer.id,
        name=db_customer.name,
        email=db_customer.email
    )

@router.post("/accounts/", response_model=schemas.Account)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    # Verify customer exists
    customer = db.query(models.Customer).filter(models.Customer.id == account.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    account_number = generate_account_number(db)
    
    db_account = models.Account(
        account_number=account_number,
        customer_id=account.customer_id
    )
    db.add(db_account)
    db.flush()  # Get the account ID
    
    transaction = models.Transaction(
        transaction_type=TransactionType.DEPOSIT,
        description=f"Initial deposit of ${account.initial_deposit:.2f}"
    )
    db.add(transaction)
    db.flush()  # Get the transaction ID
    
    ledger_entry = models.LedgerEntry(
        transaction_id=transaction.id,
        account_id=db_account.id,
        entry_type=EntryType.CREDIT,
        amount_cents=account.get_initial_deposit_cents()
    )
    db.add(ledger_entry)
    
    db.commit()
    db.refresh(db_account)
    return db_account

@router.post("/transfers/", response_model=schemas.Transaction)
def create_transfer(transfer: schemas.TransferCreate, db: Session = Depends(get_db)):
    # Get accounts
    from_account = db.query(models.Account).filter(models.Account.id == transfer.from_account_id).first()
    to_account = db.query(models.Account).filter(models.Account.id == transfer.to_account_id).first()
    
    if not from_account or not to_account:
        raise HTTPException(status_code=404, detail="One or both accounts not found")
    
    amount_cents = transfer.get_amount_cents()
    if from_account.balance_cents < amount_cents:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    transaction = models.Transaction(
        transaction_type=TransactionType.TRANSFER,
        description=transfer.description
    )
    db.add(transaction)
    db.flush()  # Get the transaction ID
    
    debit_entry = models.LedgerEntry(
        transaction_id=transaction.id,
        account_id=from_account.id,
        entry_type=EntryType.DEBIT,
        amount_cents=amount_cents
    )
    
    credit_entry = models.LedgerEntry(
        transaction_id=transaction.id,
        account_id=to_account.id,
        entry_type=EntryType.CREDIT,
        amount_cents=amount_cents
    )
    
    db.add(debit_entry)
    db.add(credit_entry)
    db.commit()
    db.refresh(transaction)
    return transaction

@router.get("/accounts/{account_id}/balance")
def get_balance(account_id: int, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return {"balance": account.balance}

@router.get("/accounts/{account_id}/transactions", response_model=schemas.TransactionHistory)
def get_transaction_history(account_id: int, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Get all transactions involving this account
    transactions = (
        db.query(models.Transaction)
        .join(models.LedgerEntry)
        .filter(models.LedgerEntry.account_id == account_id)
        .distinct()
        .all()
    )
    
    return {"transactions": transactions} 