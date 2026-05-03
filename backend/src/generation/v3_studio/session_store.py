from __future__ import annotations

import asyncio
from dataclasses import dataclass

from v3_blueprint.models import ProductionBlueprint


@dataclass
class StoredBlueprint:
    blueprint: ProductionBlueprint
    template_id: str


class V3StudioSessionStore:
    """In-memory blueprint sessions and v3 generation SSE queues (single-worker deployments)."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._blueprints: dict[tuple[str, str], StoredBlueprint] = {}
        self._queues: dict[str, asyncio.Queue[str | None]] = {}
        self._owners: dict[str, str] = {}

    async def put_blueprint(self, user_id: str, blueprint_id: str, blueprint: ProductionBlueprint, template_id: str) -> None:
        async with self._lock:
            self._blueprints[(user_id, blueprint_id)] = StoredBlueprint(
                blueprint=blueprint, template_id=template_id
            )

    async def get_blueprint(self, user_id: str, blueprint_id: str) -> StoredBlueprint | None:
        async with self._lock:
            return self._blueprints.get((user_id, blueprint_id))

    async def delete_blueprint(self, user_id: str, blueprint_id: str) -> None:
        async with self._lock:
            self._blueprints.pop((user_id, blueprint_id), None)

    async def register_generation_stream(
        self,
        *,
        user_id: str,
        generation_id: str,
        queue: asyncio.Queue[str | None],
    ) -> None:
        async with self._lock:
            self._queues[generation_id] = queue
            self._owners[generation_id] = user_id

    async def get_queue(self, generation_id: str) -> asyncio.Queue[str | None] | None:
        async with self._lock:
            return self._queues.get(generation_id)

    async def owns_generation(self, user_id: str, generation_id: str) -> bool:
        async with self._lock:
            return self._owners.get(generation_id) == user_id

    async def cleanup_generation(self, generation_id: str) -> None:
        async with self._lock:
            self._queues.pop(generation_id, None)
            self._owners.pop(generation_id, None)


v3_studio_store = V3StudioSessionStore()

__all__ = ["StoredBlueprint", "V3StudioSessionStore", "v3_studio_store"]
