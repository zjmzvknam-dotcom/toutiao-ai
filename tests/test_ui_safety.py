from html import escape


def test_preview_content_is_escaped_before_html_rendering() -> None:
    untrusted = '<img src=x onerror="alert(1)">'
    assert "<img" not in escape(untrusted)
    assert "&lt;img" in escape(untrusted)
