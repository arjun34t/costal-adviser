import sys
import os

# Add the project root to sys.path so Vercel can resolve local modules (like agent, database, backend)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class StripApiPrefixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/"):
            request.scope["path"] = request.url.path[4:]  # strip "/api"
        return await call_next(request)


app.add_middleware(StripApiPrefixMiddleware)
