from app.ui.copy import safe_script_json


def test_copy_payload_does_not_allow_script_termination() -> None:
    encoded = safe_script_json('</script><script>alert("x")</script>')
    assert "</script>" not in encoded
    assert "\\u003c" in encoded
