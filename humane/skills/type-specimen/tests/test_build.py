import json
import re

import pytest

from tspec import SpecimenError, build, config

from tests.helpers import filled


def page(**over):
    return build.build(filled(**over))


def injected(html):
    """The CFG literal the page will actually parse."""
    m = re.search(r"const CFG = (\{.*?\n\});", html, re.S)
    assert m, "CFG assignment not found in the built page"
    return json.loads(m.group(1))


def test_build_leaves_no_placeholders():
    assert not re.search(r"__[A-Z_]+__", page())


def test_config_round_trips_into_the_page():
    cfg = injected(page(bg="#101010"))
    assert cfg["bg"] == "#101010"
    assert cfg["texts"]["display"] == "Display"


def test_context_is_not_shipped_to_the_browser():
    # The brief is for whoever writes the copy; a shared page should not carry it.
    html = page(context="internal notes about the unreleased product")
    assert "unreleased product" not in html
    assert "context" not in injected(html)


def test_script_close_in_content_cannot_break_out_of_the_block():
    html = page(title="ok", notes=["</script><script>alert(1)</script>"])
    # The only real </script> is the one that ends the page's own block.
    assert html.count("</script>") == 1
    assert "<\\/script>" in html


def test_js_line_separators_are_escaped():
    # U+2028 is a line terminator to a JS parser but legal inside a JSON string.
    html = page(notes=["before after"])
    assert " " not in html
    assert "\\u2028" in html


def test_title_is_html_escaped():
    html = page(title='Kettle "Pro" & <Co>')
    assert "<title>Kettle &quot;Pro&quot; &amp; &lt;Co&gt;</title>" in html


def test_lang_attribute_follows_the_locale():
    assert '<html lang="en">' in page(locale="en")
    assert '<html lang="ru">' in config_ru()


def config_ru():
    cfg = config.starter(locale="ru")
    cfg["texts"].update({k: "x" for k in
                         ("display", "headline", "weights", "prose", "caps")})
    cfg["texts"]["rows"] = "a :: b"
    cfg["texts"]["table"] = "a :: b :: c"
    cfg["texts"]["tableHead"] = "A :: B :: C"
    return build.build(cfg)


def test_missing_template_is_a_clean_error(tmp_path):
    with pytest.raises(SpecimenError, match="template not found"):
        build.build(filled(), template=tmp_path / "nope.html")


def test_template_without_a_placeholder_is_rejected(tmp_path):
    t = tmp_path / "bare.html"
    t.write_text("<html><body>nothing here</body></html>", encoding="utf-8")
    with pytest.raises(SpecimenError, match="__CONFIG__"):
        build.build(filled(), template=t)


def test_bundled_template_carries_the_editing_contract():
    """The page's inline editing is built on these three data attributes; a
    template that lost them would still build and silently stop being editable."""
    src = build.TEMPLATE.read_text(encoding="utf-8")
    for attr in ("data-tk", "data-tl", "data-tc"):
        assert attr in src
    assert "function propagate" in src
    assert "function writeSlot" in src


def test_every_slot_is_reachable_from_the_page():
    src = build.TEMPLATE.read_text(encoding="utf-8")
    emitted = set(re.findall(r'ed\("(\w+)"', src))
    assert emitted == set(config.SLOTS), f"slots not editable in the page: {set(config.SLOTS) - emitted}"
