# The Crucible TCG - FastAPI Backend

Python FastAPI backend for The Crucible generative trading card game.

## Commands
- Run dev server: `uv run fastapi dev`
- Run tests: `uv run pytest`
- Sync dependencies: `uv sync`
- Add dependency: `uv add <package>`

## Project Structure
```
app/
├── main.py              # FastAPI app entry point
├── config.py            # Pydantic settings (database_url, gemini_api_key)
├── db.py                # SQLAlchemy database setup
├── logging_config.py    # Centralized logging with request IDs
├── models/              # SQLAlchemy ORM models
│   ├── item.py          # Item model (ItemType, Rarity enums)
│   ├── user.py          # User model
│   └── inventory.py     # Inventory model (user-item relationship)
├── schemas/             # Pydantic request/response schemas
│   ├── item.py          # Item schemas
│   ├── user.py          # User schemas
│   └── inventory.py     # Inventory schemas
├── routers/             # API route handlers
│   ├── loot.py          # GET /loot - random materials
│   ├── fuse.py          # POST /fuse - combine materials (stub)
│   ├── stash.py         # GET /stash - view inventory (stub)
│   └── sell.py          # POST /sell - sell items (stub)
├── services/            # External service integrations
│   └── gemini_service.py # Singleton for Gemini AI (text + image)
├── orchestrator/        # Game logic
│   └── crucible.py      # Rarity math, gold calculation
├── personas/            # AI character prompts
│   ├── alchemist.py     # Fusion descriptions (stub)
│   └── critic.py        # Item evaluation (stub)
└── data/
    └── base_materials.json # 30 base materials (10 ores, 10 plants, 10 resources)
```

## Database Schema
- **items**: itemid, name, type, stat, stat_value, gold_value, description, base64, rarity
- **users**: userid, gold
- **inventory**: id, userid, itemid

## Environment Variables
```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/hackathon
DEBUG=true
GEMINI_API_KEY=  # Optional - AI features disabled without it
```

## API Endpoints
- `GET /loot?userid=1` - Get 4 random materials, adds to inventory
- `POST /fuse` - Combine materials (coming soon)
- `GET /stash?userid=1` - View inventory (coming soon)
- `POST /sell` - Sell items for gold (coming soon)
- `GET /health` - Health check
- `GET /docs` - Swagger UI

## Logging Pattern
```python
from app.logging_config import get_logger
logger = get_logger(__name__)

logger.info(f"Processing user {userid}")
logger.debug(f"Selected items: {items}")
logger.error(f"Failed: {type(e).__name__}: {e}")
```

## Economy Constants
```python
GOLD_RANGES = {
    "Material": (1, 2),
    "Common": (5, 10),
    "Uncommon": (10, 20),
    "Rare": (20, 50),
    "Epic": (50, 150),
    "Legendary": (150, 300)
}
```

## Adding Features
1. Create model in app/models/ and export in __init__.py
2. Create schemas in app/schemas/ and export in __init__.py
3. Create router in app/routers/
4. Register router in app/main.py
