"""Small, centralised encoders for untrusted text embedded in VayoLoop UI."""
from __future__ import annotations

import json
from html import escape
from typing import Any


def html_text(value: Any) -> str:
    """Escape untrusted text before interpolating it into an HTML fragment."""
    return escape("" if value is None else str(value), quote=True)


def json_for_script(value: Any) -> str:
    """Serialise JSON safely inside an HTML script element.

    Escaping angle brackets prevents user-controlled strings from terminating
    the script element. U+2028 and U+2029 are escaped for JavaScript safety.
    """
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        encoded.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\\u2028", "\\u2028")
        .replace("\\u2029", "\\u2029")
    )
