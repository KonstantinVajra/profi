"""
DialogueCopilotService
──────────────────────
Receives client message + project context, returns DialogueSuggestion.

Responsibilities:
- detect client intent from message
- determine funnel stage
- generate 3 contextual reply options
- suggest next best question to move deal forward
"""
from app.schemas.dialogue import DialogueSuggestion


class DialogueCopilotService:
    def suggest(self, client_message: str, project_id: str) -> DialogueSuggestion:
        # TODO: implement in Phase 3
        raise NotImplementedError
