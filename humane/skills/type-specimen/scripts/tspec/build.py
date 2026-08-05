"""Inject a config into the template to produce a standalone specimen page."""

import html
import json
import pathlib

from . import SpecimenError

TEMPLATE = pathlib.Path(__file__).resolve().parents[2] / "templates" / "specimen.html"

# Config keys the page reads. Anything else in the file (notably `context`,
# which is for the agent writing the copy, not for the browser) is dropped so
# it does not travel with a page that may be shared.
PAGE_KEYS = (
    "id", "title", "locale", "scriptRange", "probe", "groups", "families",
    "texts", "glyphSets", "palette", "bg", "fg", "dark", "light",
    "contrastPreview", "size", "weight", "lh", "ls", "notes",
)


def _js_literal(obj):
    """A JSON literal safe to paste inside a <script> block.

    `</script>` anywhere in the data would close the block early, and U+2028 /
    U+2029 are line terminators to a JS parser though not to a JSON one.
    """
    text = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    return (text.replace("</", "<\\/")
                .replace(" ", "\\u2028")
                .replace(" ", "\\u2029"))


def build(cfg, template=None):
    """Return the finished HTML for a validated config."""
    path = pathlib.Path(template) if template else TEMPLATE
    try:
        src = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise SpecimenError(f"template not found: {path}")

    for marker in ("__CONFIG__", "__TITLE__"):
        if marker not in src:
            raise SpecimenError(f"template {path} has no {marker} placeholder")

    page_cfg = {k: cfg[k] for k in PAGE_KEYS if k in cfg}
    title = str(cfg.get("title") or cfg.get("id") or "Type specimen")

    out = src.replace("__CONFIG__", _js_literal(page_cfg))
    out = out.replace("__TITLE__", html.escape(title, quote=True))
    # So the page still declares its language before any script runs.
    out = out.replace('<html lang="ru">', f'<html lang="{html.escape(cfg["locale"])}">', 1)
    return out
