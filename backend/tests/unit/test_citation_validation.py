"""Citation validation must not false-negative when chunk_id and source_id differ."""

from app.citations import (
    allowed_chunk_keys,
    citations_from_hits,
    validate_citations_subset_of_hits,
)
from app.models import Citation


def test_allowed_keys_include_both_chunk_and_source_id():
    hits = [{"chunk_id": "kb-chunk-03", "source_id": "cdc-routines-001", "title": "T", "url": ""}]
    allowed = allowed_chunk_keys(hits)
    assert "kb-chunk-03" in allowed
    assert "cdc-routines-001" in allowed


def test_validate_accepts_citation_when_only_source_id_matches_allowed():
    hits = [{"chunk_id": "kb-chunk-03", "source_id": "cdc-routines-001", "title": "T", "url": ""}]
    cites = citations_from_hits(hits)
    assert validate_citations_subset_of_hits(cites, hits)


def test_fabricated_citation_rejected():
    hits = [{"chunk_id": "kb-real", "source_id": "kb-real", "title": "T", "url": ""}]
    fake = [
        Citation(
            source_id="kb-fake",
            chunk_id="kb-fake",
            title="Fake",
            url="https://evil.example",
        )
    ]
    assert not validate_citations_subset_of_hits(fake, hits)
