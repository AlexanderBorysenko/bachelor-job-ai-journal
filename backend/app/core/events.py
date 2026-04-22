"""In-process event bus for SSE — asyncio Queue-based pub/sub per user."""

import asyncio
from collections import defaultdict


class EventBus:
    def __init__(self):
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, user_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues[user_id].append(queue)
        return queue

    def unsubscribe(self, user_id: str, queue: asyncio.Queue):
        queues = self._queues.get(user_id, [])
        if queue in queues:
            queues.remove(queue)
        if not queues:
            self._queues.pop(user_id, None)

    async def publish(self, user_id: str, event: str, data: dict | None = None):
        for queue in self._queues.get(user_id, []):
            await queue.put({"event": event, "data": data or {}})


event_bus = EventBus()
