"""Session isolation, UUID validation, and TTL pruning."""

from app.sessions.store import SessionStore, is_valid_session_id


def test_invalid_session_id_gets_new_uuid():
    store = SessionStore()
    a = store.resolve("not-a-uuid")
    b = store.resolve("also-invalid")
    assert is_valid_session_id(a.session_id)
    assert is_valid_session_id(b.session_id)
    assert a.session_id != b.session_id


def test_valid_uuid_is_reused():
    store = SessionStore()
    first = store.resolve(None)
    again = store.resolve(first.session_id)
    assert again.session_id == first.session_id
    store.append(first.session_id, "user", "hello")
    assert again.as_langchain_turns()[-1]["content"] == "hello"


def test_sessions_do_not_share_messages():
    store = SessionStore()
    one = store.resolve(None)
    two = store.resolve(None)
    store.append(one.session_id, "user", "from one")
    store.append(two.session_id, "user", "from two")
    texts_one = [m["content"] for m in one.as_langchain_turns()]
    texts_two = [m["content"] for m in two.as_langchain_turns()]
    assert "from one" in texts_one
    assert "from two" not in texts_one
    assert "from two" in texts_two
    assert "from one" not in texts_two


def test_predictable_id_does_not_collide():
    store = SessionStore()
    a = store.resolve("1")
    b = store.resolve("1")
    store.append(a.session_id, "user", "alice")
    store.append(b.session_id, "user", "bob")
    assert a.session_id != b.session_id
    assert [m["content"] for m in a.as_langchain_turns()] != [
        m["content"] for m in b.as_langchain_turns()
    ]
