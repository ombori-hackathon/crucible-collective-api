"""Inventory model for The Crucible TCG."""

from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db import Base


class Inventory(Base):
    """Inventory model linking users to their items."""

    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    itemid = Column(Integer, ForeignKey("items.itemid"), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="inventory")
    item = relationship("Item")
