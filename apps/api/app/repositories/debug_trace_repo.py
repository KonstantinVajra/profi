"""
DebugTraceRepository
────────────────────
Database access layer for pipeline debug traces.
No business logic — only DB reads and writes.

Methods:
  create_trace             — persist one stage trace record
  get_traces_by_project    — return all traces for a project, sorted by created_at ASC

Transaction note:
  create_trace opens its own short-lived session so that committing the trace
  record never touches unrelated pending state on the caller's shared request session.
  get_traces_by_project uses the shared session passed in — read-only, safe.
"""

import json
import logging

from sqlalchemy.orm import Session

from app.models.debug_trace import PipelineTrace

logger = logging.getLogger(__name__)


class DebugTraceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_trace(
        self,
        project_id: str,
        stage: str,
        input_payload: dict | list | None,
        prompt_text: str | None,
        raw_ai_output: str | None,
        parsed_output: dict | list | None,
    ) -> None:
        """
        Persist one pipeline trace record using an isolated session.

        Opens a dedicated short-lived session so that commit() here never
        accidentally flushes unrelated pending objects on the caller's
        shared request session.

        input_payload and parsed_output are passed as Python dicts/lists
        and serialised to JSON strings for storage.
        raw_ai_output is stored as-is (already a string from the AI response).
        """
        from app.database import SessionLocal

        trace_db = SessionLocal()
        try:
            record = PipelineTrace(
                project_id=project_id,
                stage=stage,
                input_payload=json.dumps(input_payload, ensure_ascii=False) if input_payload is not None else None,
                prompt_text=prompt_text,
                raw_ai_output=raw_ai_output,
                parsed_output=json.dumps(parsed_output, ensure_ascii=False, default=str) if parsed_output is not None else None,
            )
            trace_db.add(record)
            trace_db.commit()
            logger.debug("PipelineTrace saved | stage=%s | project=%s", stage, project_id)
        except Exception:
            trace_db.rollback()
            raise
        finally:
            trace_db.close()

    def get_traces_by_project(
        self,
        project_id: str,
        stage: str | None = None,
    ) -> list[PipelineTrace]:
        """
        Return all trace records for the given project, sorted oldest-first.
        Optionally filter by stage.
        """
        query = (
            self.db.query(PipelineTrace)
            .filter(PipelineTrace.project_id == project_id)
        )
        if stage:
            query = query.filter(PipelineTrace.stage == stage)

        return query.order_by(PipelineTrace.created_at.asc()).all()
