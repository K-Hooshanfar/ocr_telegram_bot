# app/models.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import secrets

def generate_api_key():
    return secrets.token_urlsafe(32)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    credits = Column(Integer, default=0)
    api_key = Column(String, unique=True, index=True, default=generate_api_key)
    ocr_requests = relationship("OCRRequest", back_populates="owner")



class OCRRequest(Base):
    __tablename__ = "ocr_requests"
    id = Column(Integer, primary_key=True, index=True)
    image_path = Column(String)
    original_filename = Column(String)
    direction = Column(String, default="ltr")
    result_text = Column(Text)
    docx_path = Column(String, nullable=True)  # ← new!
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", back_populates="ocr_requests")
