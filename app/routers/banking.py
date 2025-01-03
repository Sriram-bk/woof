from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import models, schemas
from ..models.models import EntryType, TransactionType
from ..utils import generate_account_number

router = APIRouter()

@router.post("/customers/", response_model=schemas.Customer)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    db_customer = models.Customer(name=customer.name, email=customer.email)
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

@router.post("/accounts/", response_model=schemas.Account)
def create_account(account: schemas.AccountCreate, db: Session = Depends(get_db)):
    # Verify customer exists
    customer = db.query(models.Customer).filter(models.Customer.id == account.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Generate unique account number with sequence
    account_number = generate_account_number(db)
    
    # Create account
    db_account = models.Account(
        account_number=account_number,
        customer_id=account.customer_id
    )
    db.add(db_account)
    db.flush()  # Get the account ID
    
    # Create initial deposit transaction
    transaction = models.Transaction(
        transaction_type=TransactionType.DEPOSIT,
        description=f"Initial deposit of ${account.initial_deposit:.2f}"
    )
    db.add(transaction)
    db.flush()  # Get the transaction ID
    
    # Create ledger entry for the deposit
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
    
    # Create transaction
    transaction = models.Transaction(
        transaction_type=TransactionType.TRANSFER,
        description=transfer.description
    )
    db.add(transaction)
    db.flush()  # Get the transaction ID
    
    # Create ledger entries
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