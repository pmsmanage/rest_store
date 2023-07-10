from django.contrib.auth.models import AnonymousUser
from django.core.asgi import get_asgi_application
from rest_framework_simplejwt.tokens import AccessToken
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware

from channels.routing import ProtocolTypeRouter, URLRouter
from chat.consumers import PracticeConsumer
from django.urls import path
from django.contrib.auth.models import User
from rest_framework_simplejwt.exceptions import TokenError


@database_sync_to_async
def get_user(token):
    print("token is", token)
    decoded_token = AccessToken(token)
    user_id = decoded_token.payload['user_id']
    print('user id', user_id)
    return User.objects.get(pk=user_id)


class TokenAuthMiddleware(BaseMiddleware):
    def __init__(self, inner):
        super().__init__(inner)

    async def __call__(self, scope, receive, send):
        try:
            token = None
            for header in scope['headers']:
                print(header[0].decode())
                if header[0].decode().lower() == 'authorization':
                    elements = header[1].decode().split()
                    if elements[0].lower() in ['token', 'bearer']:
                        token = elements[1]
                    else:
                        token = elements[0]
            scope['user'] = await get_user(token)

        except Exception:
            await self.handle_unauthenticated(scope, receive, send)
            return

        print(scope['user'])
        return await super().__call__(scope, receive, send)

    async def handle_unauthenticated(self, scope, receive, send):
        response = {
            "status": 403,
            "type": "websocket.close",
            "code": 1008,
            "reason": "User is not authenticated or not allowed"
        }
        await send(response)


application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket":
        TokenAuthMiddleware(
            URLRouter(
                [
                    path(r'chat/<int:id>/', PracticeConsumer.as_asgi()),
                ]
            )
        )
})