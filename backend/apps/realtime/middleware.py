"""JWT authentication for WebSocket connections.

The browser WebSocket API cannot set headers, so the access token rides in
the query string: ws://host/ws/rides/?token=<access>. Invalid or missing
tokens yield AnonymousUser; the consumer then closes with code 4401.
"""
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

logger = logging.getLogger(__name__)


@database_sync_to_async
def _user_for_token(raw_token: str):
    from django.contrib.auth.models import AnonymousUser
    from rest_framework_simplejwt.authentication import JWTAuthentication

    if not raw_token:
        return AnonymousUser()
    try:
        auth = JWTAuthentication()
        return auth.get_user(auth.get_validated_token(raw_token))
    except Exception:  # expired/garbage token, inactive user — treat all as anon
        logger.debug("WebSocket token rejected", exc_info=True)
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query = parse_qs(scope.get("query_string", b"").decode())
        token = (query.get("token") or [""])[0]
        scope["user"] = await _user_for_token(token)
        return await super().__call__(scope, receive, send)
