"""Create the first admin user when the app starts.

Edit this file when startup seed data or admin bootstrap rules change.
Copy the small helper style here when you add another startup seed step.
"""

from __future__ import annotations

import aiosqlite

from backend.auth.passwords import hash_password
from backend.config import Settings
from backend.db.users import create_user_if_missing, user_exists


async def seed_dev_data(db: aiosqlite.Connection, settings: Settings) -> None:
    if not await user_exists(db, settings.admin_username):
        await create_user_if_missing(db, settings.admin_username, hash_password(settings.admin_password), True)
