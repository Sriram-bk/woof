import time
import random
import string
from sqlalchemy.orm import Session
from sqlalchemy import func
from .models.models import DailyAccountSequence

def get_daily_sequence(db: Session, date: str) -> int:
    """
    Get and increment the daily sequence number for account generation.
    Uses database transaction to ensure thread safety.
    
    Args:
        db (Session): Database session
        date (str): Date in YYYYMMDD format
        
    Returns:
        int: Next sequence number
    """
    # Get or create sequence for today
    sequence = db.query(DailyAccountSequence).filter(
        DailyAccountSequence.date == date
    ).with_for_update().first()
    
    if not sequence:
        sequence = DailyAccountSequence(date=date, sequence=0)
        db.add(sequence)
    
    sequence.sequence += 1
    current_sequence = sequence.sequence
    
    return current_sequence

def generate_account_number(db: Session) -> str:
    """
    Generate a unique account number using the format:
    YYYYMMDDNNNNNXXX
    
    Example: 2023121500001XY9
    
    Where:
    - YYYYMMDD: Current date
    - NNNNN: 5-digit daily sequence number (00001-99999)
    - XXX: 3 random characters for additional uniqueness
    
    Args:
        db (Session): Database session
        
    Returns:
        str: A unique account number (16 characters)
    """
    current_date = time.strftime("%Y%m%d")
    
    sequence = get_daily_sequence(db, current_date)

    random_chars = ''.join(random.choices(
        string.ascii_uppercase + string.digits, 
        k=3
    ))
    
    # Format sequence as 5 digits with leading zeros
    sequence_str = f"{sequence:05d}"
    
    return f"{current_date}{sequence_str}{random_chars}" 