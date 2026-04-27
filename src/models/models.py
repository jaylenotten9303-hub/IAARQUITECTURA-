from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from src.db.database import Base

class Problem(Base):
    __tablename__ = "problems"

    id         = Column(Integer, primary_key=True, index=True)
    input_type = Column(String)
    input_data = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Solution(Base):
    __tablename__ = "solutions"

    id                  = Column(Integer, primary_key=True, index=True)
    problem_id          = Column(Integer, ForeignKey("problems.id"))
    interpreted_data    = Column(JSONB)
    steps               = Column(JSONB)
    final_answer        = Column(Text)
    verification_status = Column(String)
    created_at          = Column(TIMESTAMP, server_default=func.now())

class Log(Base):
    __tablename__ = "logs"

    id         = Column(Integer, primary_key=True, index=True)
    event_type = Column(String)
    message    = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())
