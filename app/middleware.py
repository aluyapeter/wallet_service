from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from app.core.redis import get_redis
import json

class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "GET":
            return await call_next(request)
        
        key = request.headers.get("idempotency-key")
        if not key:
            return await call_next(request)
        
        redis = get_redis()
        cached_response = await redis.get(f"idemp:{key}")
        if cached_response:
            print(f"Idempotency Hit! Returning cached response for {key}")
            return Response(content=cached_response, status_code=200)
        
        response = await call_next(request)
        if 200 <= response.status_code < 300:
            body_chunks = [chunk async for chunk in response.body_iterator]
            response_body = b"".join(body_chunks)

            await redis.set(f"idemp:{key}", response_body, ex=86400)

            return Response(content=response_body, status_code=response.status_code)
        return response