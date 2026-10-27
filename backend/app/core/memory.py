import time
from typing import Dict, Any, List, Optional
from collections import defaultdict

class ConversationTurn:
    def __init__(self, role: str, message: str, intent: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        self.role = role
        self.message = message
        self.intent = intent
        self.metadata = metadata or {}
        self.timestamp = time.time()

class SessionMemoryManager:
    """Maintains multi-turn context and tracks operational entities across conversation turns."""
    def __init__(self, max_history: int = 6):
        self.max_history = max_history
        self._sessions: Dict[str, List[ConversationTurn]] = defaultdict(list)
        self._session_context: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "active_sku": None,
            "active_tenant": None,
            "active_topic": None
        })

    def add_turn(self, session_id: str, role: str, message: str, intent: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        turn = ConversationTurn(role, message, intent, metadata)
        history = self._sessions[session_id]
        history.append(turn)
        if len(history) > self.max_history:
            self._sessions[session_id] = history[-self.max_history:]

        # Update persistent context tags
        if metadata:
            ctx = self._session_context[session_id]
            if metadata.get("active_sku"):
                ctx["active_sku"] = metadata["active_sku"]
            if metadata.get("active_tenant"):
                ctx["active_tenant"] = metadata["active_tenant"]
            if metadata.get("active_topic"):
                ctx["active_topic"] = metadata["active_topic"]

    def get_context(self, session_id: str) -> Dict[str, Any]:
        return self._session_context[session_id]

    def get_recent_history(self, session_id: str) -> List[Dict[str, Any]]:
        return [{"role": t.role, "message": t.message, "intent": t.intent} for t in self._sessions[session_id]]

session_memory = SessionMemoryManager(max_history=6)