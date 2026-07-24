import asyncio
import json
import time
from typing import AsyncGenerator, Dict, Any


class EventBus:

    def __init__(self):
        self._subscribers: Dict[int, asyncio.Queue] = {}
        self._counter = 0

    def subscribe(self) -> int:
        self._counter += 1
        self._subscribers[self._counter] = asyncio.Queue()
        return self._counter

    def unsubscribe(self, subscriber_id: int):
        self._subscribers.pop(subscriber_id, None)

    async def publish(self, event_type: str, data: Dict[str, Any]):
        payload = json.dumps({"event": event_type, "data": data})
        for queue in list(self._subscribers.values()):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                pass

    async def stream(self, subscriber_id: int) -> AsyncGenerator[str, None]:
        queue = self._subscribers.get(subscriber_id)
        if not queue:
            return
        try:
            while True:
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            self.unsubscribe(subscriber_id)


event_bus = EventBus()
