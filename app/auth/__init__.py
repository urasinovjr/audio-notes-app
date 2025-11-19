"""
Authentication module for Supertokens integration.
"""

from app.auth.config import init_supertokens
from app.auth.dependencies import get_current_user_id

__all__ = ["init_supertokens", "get_current_user_id"]
