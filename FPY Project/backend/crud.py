from sqlalchemy.orm import Session
from models import User, Report
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, email: str, hashed_password: str):
    db_user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if user and pwd_context.verify(password, user.hashed_password):
        return user
    return None

def create_report(db: Session, report_data, created_by: str): 
    report = Report(**report_data.dict(), created_by=created_by, created_at=datetime.utcnow())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

def get_reports_by_user(db: Session, username: str):
    return db.query(Report).filter(Report.created_by == username).all()

def get_report_by_id(db: Session, report_id: int, username: str): 
    return db.query(Report).filter(Report.id == report_id, Report.created_by == username).first()

def delete_report(db: Session, report_id: int, username: str):
    report = db.query(Report).filter(Report.id == report_id, Report.created_by == username).first()
    if report:
        db.delete(report)
        db.commit()
        return True  
    return False  

def delete_all_reports_by_user(db: Session, username: str):
    """Deletes all reports created by a specific user."""
    db.query(Report).filter(Report.created_by == username).delete(synchronize_session=False)
    db.commit()
    return True

def delete_user(db: Session, username: str): 
    user = db.query(User).filter(User.username == username).first()
    if user:
        db.delete(user)
        db.commit()
        return True  
    return False  

def update_user_fields(db: Session, user: User, updates: dict):
    """Updates specific fields for a given user."""
    for key, value in updates.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user