"""Session management and command history."""

from typing import List, Optional
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory


class Session:
    """Manages CLI session state and history."""

    def __init__(self):
        """Initialize a new session."""
        self.history = InMemoryHistory()
        self.prompt_session = PromptSession(
            history=self.history, auto_suggest=AutoSuggestFromHistory()
        )
        self.current_incident_id: Optional[str] = None
        self.incidents: List[str] = []

    async def get_input(self, prompt: str = "> ") -> str:
        """
        Get user input with history and auto-suggest.

        Args:
            prompt: Prompt string to display

        Returns:
            User input string
        """
        return await self.prompt_session.prompt_async(prompt)

    def add_incident(self, incident_id: str):
        """Add an incident to the session."""
        self.incidents.append(incident_id)
        self.current_incident_id = incident_id

    def get_incidents(self) -> List[str]:
        """Get all incidents from this session."""
        return self.incidents
