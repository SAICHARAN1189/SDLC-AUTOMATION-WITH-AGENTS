from __future__ import annotations

import json
import queue

from flask import Blueprint, Response, g, stream_with_context

from backend.api.auth import require_auth
from backend.api.responses import fail
from backend.orchestration.events import event_bus
from backend.persistence import repositories

sse_bp = Blueprint("sse", __name__)


@sse_bp.get("/api/runs/<run_id>/stream")
@require_auth
def stream_run(run_id: str):
    run = repositories.get_run(run_id, g.user["id"])
    if not run:
        return fail("NOT_FOUND", "Run not found", status=404)
    q: queue.Queue = queue.Queue()

    def listener(event):
        q.put(event)

    unsubscribe = event_bus.subscribe(run_id, listener)

    def generate():
        try:
            yield "event: ready\ndata: {\"ok\": true}\n\n"
            while True:
                try:
                    event = q.get(timeout=15)
                    yield f"event: workflow\ndata: {json.dumps(event, default=str)}\n\n"
                    if event.get("event_type") in {"PIPELINE_COMPLETED", "PIPELINE_FAILED", "MANUAL_INTERVENTION_REQUIRED"}:
                        break
                except queue.Empty:
                    yield "event: ping\ndata: {}\n\n"
        finally:
            unsubscribe()

    return Response(stream_with_context(generate()), mimetype="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
