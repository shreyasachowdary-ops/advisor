from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class Audience(str, Enum):
    PARENT = "parent"
    TEACHER = "teacher"


class AgeBand(str, Enum):
    TWO_YEARS = "2_years"
    THREE_YEARS = "3_years"
    FOUR_YEARS = "4_years"
    FIVE_YEARS = "5_years"


class RiskLevel(str, Enum):
    NORMAL = "normal"
    REFERRAL = "referral"
    URGENT = "urgent"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    audience: Audience = Audience.PARENT
    age_band: AgeBand = AgeBand.FOUR_YEARS
    language: Literal["en"] = "en"
    session_id: str | None = Field(
        default=None,
        max_length=64,
        description="Optional UUID session id; server creates one if omitted or invalid",
    )


class Citation(BaseModel):
    source_id: str = Field(..., description="Stable KB document/chunk identifier")
    title: str
    url: str = ""
    chunk_id: str = Field(..., description="Vector store chunk id")
    section: str | None = None
    publication_date: str | None = None
    reviewed_at: str | None = None


SourceCitation = Citation


class ChatResponse(BaseModel):
    message_id: str
    session_id: str
    answer: str
    risk_level: RiskLevel
    citations: list[Citation] = Field(default_factory=list)
    sources: list[Citation] = Field(default_factory=list)
    suggested_follow_up: str | None = None
    requires_human_review: bool = False
    requires_confirmation: bool = Field(
        default=False,
        description="True when user must explicitly confirm before safeguarding submit",
    )
    safeguarding_event_id: str | None = None
    safeguarding_category: str | None = Field(
        default=None,
        description="Classifier category hint for confirm UI (urgent only)",
    )
    activity_plan: dict[str, Any] | None = None
    degraded: bool = Field(
        default=False,
        description="True when the language model was unavailable or failed and a template answer was used",
    )

    @model_validator(mode="after")
    def _sync_sources_alias(self) -> "ChatResponse":
        if self.citations and not self.sources:
            object.__setattr__(self, "sources", list(self.citations))
        elif self.sources and not self.citations:
            object.__setattr__(self, "citations", list(self.sources))
        elif self.citations and self.sources and self.citations != self.sources:
            object.__setattr__(self, "sources", list(self.citations))
        return self


class FeedbackRequest(BaseModel):
    message_id: str = Field(..., min_length=8, max_length=64)
    session_id: str | None = None
    rating: Literal["helpful", "not_helpful", "unsafe"]


class SafeguardingConfirmRequest(BaseModel):
    message_id: str = Field(..., min_length=8, max_length=64)
    session_id: str | None = None
    category: str
    severity: Literal["low", "medium", "high", "critical"]
    user_summary: str = Field(..., max_length=2000)
    user_confirmed: bool = False


class SafeguardingConfirmResponse(BaseModel):
    status: str
    message: str
    safeguarding_event_id: str | None = None
    message_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    ollama: bool
    kb_version: str


class ReadyResponse(BaseModel):
    ready: bool
    ollama: bool
    chroma: bool
    mcp: bool
    kb_version: str
