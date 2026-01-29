"""Inventory model for The Crucible TCG."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db import Base


class Inventory(Base):
    """Inventory model linking users to their items with quantity."""

    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    userid = Column(Integer, ForeignKey("users.userid"), nullable=False, index=True)
    itemid = Column(Integer, ForeignKey("items.itemid"), nullable=False, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Unique constraint: one row per (user, item) pair
    __table_args__ = (UniqueConstraint("userid", "itemid", name="uix_user_item"),)

    # Relationships
    user = relationship("User", back_populates="inventory")
    item = relationship("Item")
