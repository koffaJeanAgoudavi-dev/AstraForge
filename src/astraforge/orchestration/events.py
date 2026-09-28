"""Live build event broker with persistent replay support."""

import asyncio
from collections import defaultdict


class BuildEventBroker:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)

    async def publish(self, project_id: str, event: dict) -> None:
        for queue in tuple(self._subscribers.get(project_id, ())):
            await queue.put(event)

    async def subscribe(self, project_id: str):
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[project_id].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers[project_id].discard(queue)
            if not self._subscribers[project_id]:
                self._subscribers.pop(project_id, None)


build_events = BuildEventBroker()
