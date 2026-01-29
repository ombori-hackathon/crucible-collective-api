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
