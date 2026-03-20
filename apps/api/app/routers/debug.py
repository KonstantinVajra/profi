"""
Debug router
────────────
GET /projects/{project_id}/debug-trace

Read-only endpoint to inspect the full AI pipeline trace for a project.
Returns all trace records sorted by created_at ASC.

Optional query param:
  ?stage=extraction | reply_generation | landing_generation_step1 | landing_generation_step2

Does NOT affect any existing endpoints or business logic.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.debug_trace_repo import DebugTraceRepository

logger = logging.getLogger(__name__)
router = APIRouter()


def _try_parse_json(value: str | None) -> Any:
    """
    Attempt to parse a stored JSON string back into a Python object.
    Returns the parsed object on success, the raw string on failure, None if input is None.
    """
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


@router.get(
    "/{project_id}/debug-trace",
    summary="Return full AI pipeline trace for a project",
)
def get_debug_trace(
    project_id: str,
    stage: str | None = Query(default=None, description="Filter by stage name"),
    db: Session = Depends(get_db),
):
    repo = DebugTraceRepository(db)
    records = repo.get_traces_by_project(project_id, stage=stage)

    traces = []
    for r in records:
        traces.append({
            "id": r.id,
            "stage": r.stage,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "input_payload": _try_parse_json(r.input_payload),
            "prompt_text": r.prompt_text,
            "raw_ai_output": r.raw_ai_output,
            "parsed_output": _try_parse_json(r.parsed_output),
        })

    return {
        "project_id": project_id,
        "traces": traces,
    }
