from sqlalchemy import Column, Integer, String, DateTime, Text 
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String)
    hashed_password = Column(String)

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String)
    exam_date = Column(String)
    history = Column(String)
    technique = Column(String)
    findings = Column(String)
    created_by = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    image_base64 = Column(Text) 
