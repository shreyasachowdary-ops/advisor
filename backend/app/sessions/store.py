"""In-memory conversation sessions with isolation, TTL, and a size cap."""

from __future__ import annotations

import re
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from threading import Lock

from app.config import settings

_UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def is_valid_session_id(session_id: str | None) -> bool:
    return bool(session_id and _UUID_RE.match(session_id.strip()))


@dataclass
class SessionMessage:
    role: str
    content: str


@dataclass
class ConversationSession:
    session_id: str
    messages: deque[SessionMessage] = field(default_factory=deque)
    last_access: float = field(default_factory=time.monotonic)

    def touch(self) -> None:
        self.last_access = time.monotonic()

    def append(self, role: str, content: str) -> None:
        self.touch()
        self.messages.append(SessionMessage(role=role, content=content))
        while len(self.messages) > settings.session_max_messages:
            self.messages.popleft()

    def as_langchain_turns(self) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.messages]


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ConversationSession] = {}
        self._lock = Lock()

    def _prune_locked(self) -> None:
        ttl = settings.session_ttl_seconds
        now = time.monotonic()
        if ttl > 0:
            expired = [sid for sid, s in self._sessions.items() if now - s.last_access > ttl]
            for sid in expired:
                del self._sessions[sid]
        max_sessions = settings.session_max_sessions
        if max_sessions > 0 and len(self._sessions) > max_sessions:
            by_age = sorted(self._sessions.items(), key=lambda kv: kv[1].last_access)
            overflow = len(self._sessions) - max_sessions
            for sid, _ in by_age[:overflow]:
                del self._sessions[sid]

    def resolve(self, session_id: str | None) -> ConversationSession:
        with self._lock:
            self._prune_locked()
            sid = session_id.strip() if is_valid_session_id(session_id) else str(uuid.uuid4())
            session = self._sessions.get(sid)
            if not session:
                session = ConversationSession(session_id=sid)
                self._sessions[sid] = session
            session.touch()
            return session

    def append(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            self._prune_locked()
            session = self._sessions.get(session_id)
            if not session:
                session = ConversationSession(session_id=session_id)
                self._sessions[session_id] = session
            session.append(role, content)

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)


session_store = SessionStore()
