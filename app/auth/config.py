"""
Supertokens authentication configuration.

This module initializes Supertokens with EmailPassword and Session recipes.
"""

import asyncio
from typing import Any

from supertokens_python import InputAppInfo, SupertokensConfig, init
from supertokens_python.recipe import emailpassword, session
from supertokens_python.recipe.emailpassword.interfaces import (
    APIInterface,
    APIOptions,
    SignUpPostOkResult,
)
from supertokens_python.recipe.session import SessionContainer

from app.auth.hooks import create_user_in_db
from app.core.config import settings


def override_emailpassword_apis(original_implementation: APIInterface) -> APIInterface:
    """
    Override EmailPassword API to sync users with main database.

    This override hooks into the signup process to create user records
    in the main application database after successful Supertokens signup.
    """
    original_sign_up_post = original_implementation.sign_up_post

    async def sign_up_post(
        form_fields: list[Any],
        tenant_id: str,
        session: SessionContainer | None,
        should_try_linking_with_session_user: bool | None,
        api_options: APIOptions,
        user_context: dict[str, Any],
    ) -> SignUpPostOkResult | Any:
        """Override sign_up_post to sync user to main database."""
        # Call the original implementation
        response = await original_sign_up_post(
            form_fields,
            tenant_id,
            session,
            should_try_linking_with_session_user,
            api_options,
            user_context,
        )

        # If signup was successful, create user in main database
        if isinstance(response, SignUpPostOkResult):
            user_id = response.user.id
            email = response.user.emails[0]

            # Sync user to main database (run in background to not block response)
            # Note: We use asyncio.create_task to run this in the background
            asyncio.create_task(create_user_in_db(user_id, email))

        return response

    original_implementation.sign_up_post = sign_up_post
    return original_implementation


def init_supertokens():
    """
    Initialize Supertokens with EmailPassword and Session recipes.

    This function should be called once at application startup.
    Includes override to sync users with main application database.
    """
    init(
        supertokens_config=SupertokensConfig(
            connection_uri=settings.SUPERTOKENS_CONNECTION_URI,
            api_key=settings.SUPERTOKENS_API_KEY,
        ),
        app_info=InputAppInfo(
            app_name="AudioNotesApp",
            api_domain=settings.SUPERTOKENS_API_DOMAIN,
            website_domain=settings.SUPERTOKENS_WEBSITE_DOMAIN,
        ),
        framework="fastapi",
        recipe_list=[
            emailpassword.init(
                override=emailpassword.InputOverrideConfig(
                    apis=override_emailpassword_apis,
                )
            ),
            session.init(),
        ],
    )
