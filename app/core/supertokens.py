import asyncio
import os
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from supertokens_python import InputAppInfo, SupertokensConfig, init
from supertokens_python.recipe import emailpassword, session
from supertokens_python.recipe.emailpassword import InputFormField
from supertokens_python.recipe.emailpassword.interfaces import (
    APIInterface,
    APIOptions,
    SignInPostOkResult,
    SignUpPostOkResult,
)
from supertokens_python.recipe.session import SessionContainer

from app.db.database import async_session
from app.db.models import User


async def sync_user_to_db(user_id: str, email: str) -> None:
    """
    Sync user from Supertokens to main database.

    Args:
        user_id: Supertokens user ID
        email: User email
    """
    async with async_session() as db:
        # Check if user already exists
        result = await db.execute(select(User).where(User.id == user_id))
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            # Create new user using INSERT ... ON CONFLICT DO NOTHING
            stmt = (
                pg_insert(User)
                .values(
                    id=user_id,
                    email=email,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )

            await db.execute(stmt)
            await db.commit()


def override_emailpassword_apis(original_implementation: APIInterface) -> APIInterface:
    """Override EmailPassword APIs to sync users with main database."""

    original_sign_up_post = original_implementation.sign_up_post
    original_sign_in_post = original_implementation.sign_in_post

    async def sign_up_post(
        form_fields: list[Any],
        tenant_id: str,
        session: SessionContainer | None,
        should_try_linking_with_session_user: bool | None,
        api_options: APIOptions,
        user_context: dict[str, Any],
    ) -> SignUpPostOkResult | Any:
        """Override sign_up_post to sync user to main database."""
        response = await original_sign_up_post(
            form_fields,
            tenant_id,
            session,
            should_try_linking_with_session_user,
            api_options,
            user_context,
        )

        # If signup was successful, sync user to database
        if isinstance(response, SignUpPostOkResult):
            user_id = response.user.id
            email = response.user.emails[0]
            asyncio.create_task(sync_user_to_db(user_id, email))

        return response

    async def sign_in_post(
        form_fields: list[Any],
        tenant_id: str,
        session: SessionContainer | None,
        should_try_linking_with_session_user: bool | None,
        api_options: APIOptions,
        user_context: dict[str, Any],
    ) -> SignInPostOkResult | Any:
        """Override sign_in_post to ensure user exists in main database."""
        response = await original_sign_in_post(
            form_fields,
            tenant_id,
            session,
            should_try_linking_with_session_user,
            api_options,
            user_context,
        )

        # If signin was successful, ensure user exists in database
        if isinstance(response, SignInPostOkResult):
            user_id = response.user.id
            email = response.user.emails[0]
            asyncio.create_task(sync_user_to_db(user_id, email))

        return response

    original_implementation.sign_up_post = sign_up_post
    original_implementation.sign_in_post = sign_in_post
    return original_implementation


def init_supertokens():
    """Initialize Supertokens with EmailPassword and Session recipes"""

    init(
        app_info=InputAppInfo(
            app_name="AudioNotesApp",
            api_domain=os.getenv("SUPERTOKENS_API_DOMAIN", "http://localhost:8000"),
            website_domain=os.getenv("SUPERTOKENS_WEBSITE_DOMAIN", "http://localhost:3000"),
            api_base_path="/auth",
            website_base_path="/auth",
        ),
        supertokens_config=SupertokensConfig(
            connection_uri=os.getenv("SUPERTOKENS_CONNECTION_URI", "http://supertokens:3567"),
            api_key=os.getenv("SUPERTOKENS_API_KEY", ""),
        ),
        framework="fastapi",
        recipe_list=[
            emailpassword.init(
                sign_up_feature=emailpassword.InputSignUpFeature(
                    form_fields=[InputFormField(id="email"), InputFormField(id="password")]
                ),
                override=emailpassword.InputOverrideConfig(
                    apis=override_emailpassword_apis,
                ),
            ),
            session.init(
                cookie_secure=False,  # Set to True in production with HTTPS
                cookie_same_site="lax",
            ),
        ],
        mode="asgi",
    )
