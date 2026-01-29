"""Tests for the /fuse endpoint."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Inventory, Item, ItemType, Rarity, User


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    """Create a test client with the test database."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def user_with_items(db_session):
    """Create a test user with items in inventory."""
    user = User(userid=1, gold=100)
    db_session.add(user)

    item1 = Item(
        name="Iron Ore",
        type=ItemType.material,
        rarity=Rarity.Material,
        gold_value=2,
    )
    item2 = Item(
        name="Silver Ore",
        type=ItemType.material,
        rarity=Rarity.Material,
        gold_value=2,
    )
    db_session.add_all([item1, item2])
    db_session.flush()

    inv1 = Inventory(userid=1, itemid=item1.itemid)
    inv2 = Inventory(userid=1, itemid=item2.itemid)
    db_session.add_all([inv1, inv2])
    db_session.commit()

    return user, [item1, item2]


def test_fuse_success(client, user_with_items):
    """Test successful fusion of two items."""
    user, items = user_with_items

    response = client.post(
        "/fuse",
        json={"userid": 1, "itemids": [items[0].itemid, items[1].itemid]},
    )

    assert response.status_code == 200
    data = response.json()

    assert "item" in data
    assert "alchemist_says" in data
    assert "critic_score" in data

    assert data["item"]["name"]
    assert data["item"]["type"] in ["weapon", "armor", "consumable"]
    assert 0.0 <= data["critic_score"] <= 1.0


def test_fuse_user_not_found(client):
    """Test fusion with non-existent user."""
    response = client.post(
        "/fuse",
        json={"userid": 999, "itemids": [1, 2]},
    )

    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]


def test_fuse_item_not_in_inventory(client, db_session):
    """Test fusion with item not in user's inventory."""
    user = User(userid=1, gold=100)
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/fuse",
        json={"userid": 1, "itemids": [999, 998]},
    )

    assert response.status_code == 400
    assert "not found in user's inventory" in response.json()["detail"]


def test_fuse_requires_two_items(client):
    """Test that fusion requires exactly 2 items."""
    response = client.post(
        "/fuse",
        json={"userid": 1, "itemids": [1]},
    )

    assert response.status_code == 422  # Validation error


def test_fuse_consumes_items(client, user_with_items, db_session):
    """Test that fusion consumes the input items from inventory."""
    user, items = user_with_items

    # Verify items are in inventory before fusion
    inv_count_before = db_session.query(Inventory).filter(Inventory.userid == 1).count()
    assert inv_count_before == 2

    response = client.post(
        "/fuse",
        json={"userid": 1, "itemids": [items[0].itemid, items[1].itemid]},
    )

    assert response.status_code == 200

    # Verify original items removed, new item added (net: 2 - 2 + 1 = 1)
    inv_count_after = db_session.query(Inventory).filter(Inventory.userid == 1).count()
    assert inv_count_after == 1


# ============== New Fusability Tests ==============


class TestFusabilityRules:
    """Tests for the deterministic fusability rules."""

    def test_can_fuse_material_material(self):
        """Material + Material should be valid."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        assert CrucibleOrchestrator.can_fuse(Rarity.Material, Rarity.Material)

    def test_can_fuse_material_uncommon(self):
        """Material + Uncommon should be valid (special combo)."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        assert CrucibleOrchestrator.can_fuse(Rarity.Material, Rarity.Uncommon)
        assert CrucibleOrchestrator.can_fuse(Rarity.Uncommon, Rarity.Material)

    def test_cannot_fuse_common_material(self):
        """Common + Material should be invalid."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        assert not CrucibleOrchestrator.can_fuse(Rarity.Common, Rarity.Material)

    def test_cannot_fuse_common_rare(self):
        """Cross-rarity fusion (Common + Rare) should be invalid."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        assert not CrucibleOrchestrator.can_fuse(Rarity.Common, Rarity.Rare)

    def test_can_fuse_same_rarity(self):
        """Same rarity fusion should be valid for all tiers."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        for rarity in [
            Rarity.Common,
            Rarity.Uncommon,
            Rarity.Rare,
            Rarity.Epic,
            Rarity.Legendary,
        ]:
            assert CrucibleOrchestrator.can_fuse(
                rarity, rarity
            ), f"{rarity} + {rarity} should fuse"


class TestDeterministicRarity:
    """Tests for deterministic rarity calculation."""

    def test_result_material_material(self):
        """Material + Material should produce Common."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        result = CrucibleOrchestrator.calculate_deterministic_rarity(
            Rarity.Material, Rarity.Material
        )
        assert result == Rarity.Common

    def test_result_material_uncommon(self):
        """Material + Uncommon should produce Common."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        result = CrucibleOrchestrator.calculate_deterministic_rarity(
            Rarity.Material, Rarity.Uncommon
        )
        assert result == Rarity.Common

    def test_result_common_common(self):
        """Common + Common should produce Uncommon."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        result = CrucibleOrchestrator.calculate_deterministic_rarity(
            Rarity.Common, Rarity.Common
        )
        assert result == Rarity.Uncommon

    def test_result_uncommon_uncommon(self):
        """Uncommon + Uncommon should produce Rare."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        result = CrucibleOrchestrator.calculate_deterministic_rarity(
            Rarity.Uncommon, Rarity.Uncommon
        )
        assert result == Rarity.Rare

    def test_result_rare_rare(self):
        """Rare + Rare should produce Epic."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        result = CrucibleOrchestrator.calculate_deterministic_rarity(
            Rarity.Rare, Rarity.Rare
        )
        assert result == Rarity.Epic

    def test_result_epic_epic(self):
        """Epic + Epic should produce Legendary."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        result = CrucibleOrchestrator.calculate_deterministic_rarity(
            Rarity.Epic, Rarity.Epic
        )
        assert result == Rarity.Legendary

    def test_result_legendary_legendary(self):
        """Legendary + Legendary should produce Legendary (capped)."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        result = CrucibleOrchestrator.calculate_deterministic_rarity(
            Rarity.Legendary, Rarity.Legendary
        )
        assert result == Rarity.Legendary

    def test_invalid_combination_returns_none(self):
        """Invalid combinations should return None."""
        from app.orchestrator.crucible import CrucibleOrchestrator

        result = CrucibleOrchestrator.calculate_deterministic_rarity(
            Rarity.Common, Rarity.Rare
        )
        assert result is None


class TestFuseEndpointFusability:
    """Tests for /fuse endpoint fusability validation."""

    @pytest.fixture
    def user_with_mixed_items(self, db_session):
        """Create a test user with items of different rarities."""
        user = User(userid=2, gold=100)
        db_session.add(user)

        common_item = Item(
            name="Iron Sword",
            type=ItemType.weapon,
            rarity=Rarity.Common,
            gold_value=5,
        )
        rare_item = Item(
            name="Dragon Scale",
            type=ItemType.armor,
            rarity=Rarity.Rare,
            gold_value=30,
        )
        db_session.add_all([common_item, rare_item])
        db_session.flush()

        inv1 = Inventory(userid=2, itemid=common_item.itemid)
        inv2 = Inventory(userid=2, itemid=rare_item.itemid)
        db_session.add_all([inv1, inv2])
        db_session.commit()

        return user, [common_item, rare_item]

    def test_fuse_rejects_incompatible_rarities(self, client, user_with_mixed_items):
        """Test that /fuse returns 400 for incompatible rarity combinations."""
        user, items = user_with_mixed_items

        response = client.post(
            "/fuse",
            json={"userid": 2, "itemids": [items[0].itemid, items[1].itemid]},
        )

        assert response.status_code == 400
        assert "Cannot fuse" in response.json()["detail"]

    def test_fuse_response_includes_attempts(self, client, user_with_items):
        """Test that /fuse response includes the attempts field."""
        user, items = user_with_items

        response = client.post(
            "/fuse",
            json={"userid": 1, "itemids": [items[0].itemid, items[1].itemid]},
        )

        assert response.status_code == 200
        data = response.json()

        assert "attempts" in data
        assert 1 <= data["attempts"] <= 3
