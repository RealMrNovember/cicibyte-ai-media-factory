from mediafactory.core.redact import redact


def test_bearer_masked():
    out = redact("Authorization: Bearer sk-1234567890abcdef")
    assert "sk-1234567890abcdef" not in out
    assert "Bearer ****" in out


def test_query_key_masked():
    assert redact("https://x/?key=abc123&q=1") == "https://x/?key=****&q=1"


def test_assignments_masked():
    out = redact("api_key=secret1 token=secret2")
    assert "secret1" not in out and "secret2" not in out


def test_json_password_masked():
    out = redact('{"password": "hunter2", "user": "a"}')
    assert "hunter2" not in out
    assert '"user": "a"' in out


def test_plain_text_untouched():
    assert redact("nothing secret here") == "nothing secret here"
