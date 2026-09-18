from __future__ import annotations

import json
from uuid import uuid4

import streamlit.components.v1 as components


def safe_script_json(text: str) -> str:
    return json.dumps(text, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def render_copy_button(text: str, label: str) -> None:
    """Render a browser-local clipboard control with safely serialized text."""
    element_id = f"copy-{uuid4().hex}"
    payload = safe_script_json(text)
    html = f'''<button id="{element_id}" style="border:1px solid #d0d7de;border-radius:6px;background:white;padding:6px 10px;cursor:pointer">{label}</button>
<script>
const button = document.getElementById({json.dumps(element_id)});
const text = {payload};
button.addEventListener("click", async () => {{
  try {{ await navigator.clipboard.writeText(text); button.textContent = "已复制"; }}
  catch (_) {{ button.textContent = "复制失败，请手动复制"; }}
}});
</script>'''
    components.html(html, height=42)
