"""Server-Sent Events endpoint for real-time frontend updates."""

import asyncio
import json

from fastapi import APIRouter, Query, HTTPException, status
from starlette.requests import Request
from starlette.responses import StreamingResponse

from app.core.events import event_bus
from app.services.auth import decode_token

router = APIRouter(prefix="/api/events", tags=["SSE"])


@router.get("")
async def stream(request: Request, token: str = Query(...)):
    """SSE stream authenticated via query-string token (EventSource can't set headers)."""
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id = payload["sub"]

    async def generate():
        queue = event_bus.subscribe(user_id)
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=25)
                    yield f"event: {msg['event']}\ndata: {json.dumps(msg['data'])}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_bus.unsubscribe(user_id, queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
