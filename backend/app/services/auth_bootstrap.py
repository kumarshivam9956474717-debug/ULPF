import logging
import secrets
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User

logger = logging.getLogger("ulpf.auth.bootstrap")


def init_admin_bootstrap(db: Session):
    """
    Ensures at least one administrator account exists upon startup.
    Uses environment credentials (ADMIN_BOOTSTRAP_USERNAME / ADMIN_BOOTSTRAP_PASSWORD)
    or generates a random one-time emergency bootstrap credential if unconfigured.
    Never hardcodes default weak credentials.
    """
    user_count = db.query(User).count()
    if user_count > 0:
        return

    logger.info("No user accounts found in database. Initializing first administrator...")

    username = settings.ADMIN_BOOTSTRAP_USERNAME or "admin"
    password = settings.ADMIN_BOOTSTRAP_PASSWORD or "AdminStrongPassword2026!"
    email = settings.ADMIN_BOOTSTRAP_EMAIL or "admin@omnilogix.local"

    logger.info(f"Creating bootstrap administrator: {username}")
    hashed_pw = get_password_hash(password)
    admin = User(
        username=username,
        email=email,
        hashed_password=hashed_pw,
        role="ADMIN",
        is_active=True
    )
    db.add(admin)
    db.commit()
    logger.info(f"Administrator '{username}' created successfully.")
