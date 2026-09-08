"""Idempotent first-admin seed.

Run with: uv run python -m app.scripts.seed_admin

Reads FIRST_ADMIN_EMAIL / FIRST_ADMIN_PASSWORD / FIRST_ADMIN_FULL_NAME from
settings (see .env / .env.example). No-ops with a warning if the email or
password isn't set. Safe to run repeatedly (in docker-compose's startup
command, in CI, ...): if the account already exists it is left untouched
unless its role isn't `admin`, in which case it's promoted -- it is never
re-created and its password is never overwritten by this script.
"""

import asyncio
import logging

from app.core.asyncio_compat import apply_windows_event_loop_policy
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


async def seed_admin() -> None:
    if not settings.FIRST_ADMIN_EMAIL or not settings.FIRST_ADMIN_PASSWORD:
        logger.warning(
            "FIRST_ADMIN_EMAIL/FIRST_ADMIN_PASSWORD not set -- skipping admin seed."
        )
        return

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_email(settings.FIRST_ADMIN_EMAIL)

        if existing is not None:
            if existing.role != UserRole.ADMIN:
                await repo.update(existing, {"role": UserRole.ADMIN})
                await session.commit()
                logger.info("Promoted existing user %s to admin.", existing.email)
            else:
                logger.info("Admin user %s already exists -- nothing to do.", existing.email)
            return

        admin = await repo.create(
            {
                "email": settings.FIRST_ADMIN_EMAIL.lower(),
                "hashed_password": hash_password(settings.FIRST_ADMIN_PASSWORD),
                "full_name": settings.FIRST_ADMIN_FULL_NAME,
                "role": UserRole.ADMIN,
                "is_active": True,
            }
        )
        await session.commit()
        logger.info("Created admin user %s (id=%s).", admin.email, admin.id)


if __name__ == "__main__":
    apply_windows_event_loop_policy()
    configure_logging()
    asyncio.run(seed_admin())
