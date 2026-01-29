"""Item model for The Crucible TCG."""

import enum

from sqlalchemy import Column, Enum, Integer, String, Text

from app.db import Base


class ItemType(enum.Enum):
    """Types of items in the game."""

    material = "material"
    weapon = "weapon"
    armor = "armor"
    consumable = "consumable"


class Rarity(enum.Enum):
    """Rarity tiers for items."""

    Material = "Material"
    Common = "Common"
    Uncommon = "Uncommon"
    Rare = "Rare"
    Epic = "Epic"
    Legendary = "Legendary"


class Item(Base):
    """Item model representing cards/materials in the game."""

    __tablename__ = "items"

    itemid = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    type = Column(Enum(ItemType), nullable=False, default=ItemType.material)
    stat = Column(String(50), nullable=True)  # strength/defense/magic/speed/luck
    stat_value = Column(Integer, default=0)
    gold_value = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=True)
    base64 = Column(Text, nullable=True)  # Base64 encoded image data
    rarity = Column(Enum(Rarity), nullable=False, default=Rarity.Material)
