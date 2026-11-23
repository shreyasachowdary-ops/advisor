"""Trusted school_id for policy lookup."""

from mcp_server.tools.school_policy import get_school_policy


def test_school_policy_ignores_untrusted_school_id(monkeypatch):
    monkeypatch.setattr(
        "app.tenant.trusted_school_id",
        lambda: "poc_test_school",
    )
    result = get_school_policy("bullying", school_id="attacker_school")
    assert result["school_id"] == "poc_test_school"
    assert result["policy_type"] == "bullying"
