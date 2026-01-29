"""User model for The Crucible TCG."""

from sqlalchemy import Column, Integer
from sqlalchemy.orm import relationship

from app.db import Base


class User(Base):
    """User model representing a player."""

    __tablename__ = "users"

    userid = Column(Integer, primary_key=True, index=True)
    gold = Column(Integer, default=100, nullable=False)

    # Relationship to inventory
    inventory = relationship("Inventory", back_populates="user")
