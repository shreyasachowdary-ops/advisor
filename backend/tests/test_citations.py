"""Citation provenance from retrieval hits."""

from app.citations import citation_from_retrieval_hit, dedupe_citations


def test_citation_from_hit_includes_provenance():
    hit = {
        "chunk_id": "kb-cdc-routines-001",
        "source_id": "kb-cdc-routines-001",
        "title": "CDC Routines",
        "url": "https://example.org/cdc",
        "section": "routines",
        "publication_date": "2024-01-01",
        "reviewed_at": "2025-09-01",
        "distance": 0.42,
    }
    c = citation_from_retrieval_hit(hit)
    assert c.source_id == "kb-cdc-routines-001"
    assert c.chunk_id == "kb-cdc-routines-001"
    assert c.section == "routines"
    assert not hasattr(c, "confidence")
    assert "distance" not in c.model_dump()


def test_dedupe_citations():
    a = citation_from_retrieval_hit({"chunk_id": "x", "source_id": "x", "title": "A", "url": ""})
    b = citation_from_retrieval_hit({"chunk_id": "x", "source_id": "x", "title": "A", "url": ""})
    assert len(dedupe_citations([a, b])) == 1
