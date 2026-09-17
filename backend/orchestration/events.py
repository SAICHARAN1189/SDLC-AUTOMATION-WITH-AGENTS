from __future__ import annotations

import threading
from collections import defaultdict, deque
from typing import Any, Callable

from backend.models.schemas import new_id, utc_now
from backend.persistence import repositories
from backend.utils.logging import logger

Listener = Callable[[dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buffers: dict[str, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=2000))
        self._listeners: dict[str, list[Listener]] = defaultdict(list)

    def publish(self, event: dict[str, Any]) -> dict[str, Any]:
        event.setdefault("event_id", new_id())
        event.setdefault("timestamp", utc_now().isoformat())
        run_id = event["run_id"]
        stored = repositories.add_event(
            {
                "event_id": event["event_id"],
                "run_id": run_id,
                "timestamp": utc_now(),
                "stage": event.get("stage"),
                "agent": event.get("agent"),
                "event_type": event["event_type"],
                "status": event.get("status") or "INFO",
                "message": event.get("message") or "",
                "metadata": event.get("metadata") or {},
            }
        )
        event["id"] = stored["id"]
        with self._lock:
            self._buffers[run_id].append(event)
            listeners = list(self._listeners[run_id])
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                logger.debug("event listener failed")
        return event

    def subscribe(self, run_id: str, listener: Listener) -> Callable[[], None]:
        with self._lock:
            self._listeners[run_id].append(listener)
            snapshot = list(self._buffers[run_id])

        def unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners[run_id]:
                    self._listeners[run_id].remove(listener)

        for item in snapshot:
            listener(item)
        return unsubscribe

    def history(self, run_id: str) -> list[dict[str, Any]]:
        persisted = repositories.list_events(run_id)
        if persisted:
            return persisted
        with self._lock:
            return list(self._buffers[run_id])


event_bus = EventBus()


def emit(run_id: str, event_type: str, message: str, stage: str, agent: str | None = None, status: str = "INFO", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    return event_bus.publish(
        {
            "run_id": run_id,
            "event_type": event_type,
            "message": message,
            "stage": stage,
            "agent": agent,
            "status": status,
            "metadata": metadata or {},
        }
    )
