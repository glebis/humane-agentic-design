import json
import pathlib

from dtokens import cli

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_validate_ok(capsys):
    rc = cli.main(["validate", str(FIXTURES / "global.base.tokens.json")])
    assert rc == 0
    assert "OK" in capsys.readouterr().out


def test_validate_warns_on_silent_art_direction(capsys):
    # global.base has no brand block -> valid (rc 0) but a stderr warning.
    rc = cli.main(["validate", str(FIXTURES / "global.base.tokens.json")])
    assert rc == 0
    captured = capsys.readouterr()
    assert "OK" in captured.out
    assert "warning:" in captured.err
    assert "imageryStyle" in captured.err or "brand-style block" in captured.err


def test_validate_no_warning_with_complete_brand_block(tmp_path, capsys):
    good = tmp_path / "good.tokens.json"
    good.write_text(json.dumps({
        "color": {"$type": "color", "primary": {"$value": "#0E7C7B"}},
        "$extensions": {"community.design-tokens.brand": {
            "mood": ["calm"], "imageryStyle": "flat vector, dot-grid"}},
    }))
    rc = cli.main(["validate", str(good)])
    assert rc == 0
    assert "warning:" not in capsys.readouterr().err


def test_validate_reports_errors(tmp_path, capsys):
    bad = tmp_path / "bad.tokens.json"
    bad.write_text(json.dumps({"a": {"$type": "color", "$value": "{missing}"}}))
    rc = cli.main(["validate", str(bad)])
    assert rc == 1
    assert "missing" in capsys.readouterr().out


def _write_clamp_set(tmp_path):
    p = tmp_path / "fluid.tokens.json"
    p.write_text(json.dumps({
        "space": {"$type": "dimension", "section": {"$value": "clamp(72px, 11vw, 150px)"}},
        "$extensions": {"community.design-tokens.brand": {
            "mood": ["calm"], "imageryStyle": "flat vector"}},
    }))
    return p


def test_validate_clamp_warns_but_passes_by_default(tmp_path, capsys):
    rc = cli.main(["validate", str(_write_clamp_set(tmp_path))])
    assert rc == 0
    captured = capsys.readouterr()
    assert "OK" in captured.out
    assert "non-DTCG dimension kept verbatim" in captured.err
    assert "clamp(72px, 11vw, 150px)" in captured.err


def test_validate_strict_makes_clamp_an_error(tmp_path, capsys):
    rc = cli.main(["validate", "--strict", str(_write_clamp_set(tmp_path))])
    assert rc == 1
    captured = capsys.readouterr()
    assert "OK" not in captured.out
    assert "non-DTCG dimension kept verbatim" in captured.out  # promoted to error (stdout)


def test_clamp_set_exports_css_verbatim(tmp_path):
    out_css = tmp_path / "out.css"
    rc = cli.main(["export-css", str(_write_clamp_set(tmp_path)), "-o", str(out_css)])
    assert rc == 0
    assert "--space-section: clamp(72px, 11vw, 150px);" in out_css.read_text()


def test_merge_then_export_matches_golden(tmp_path):
    merged = tmp_path / "merged.tokens.json"
    cli.main([
        "merge",
        str(FIXTURES / "global.base.tokens.json"),
        str(FIXTURES / "project.override.tokens.json"),
        "-o", str(merged),
    ])
    out_css = tmp_path / "out.css"
    cli.main(["export-css", str(merged), "-o", str(out_css)])
    expected = (FIXTURES / "expected.tokens.css").read_text()
    assert out_css.read_text() == expected


def test_setup_edit_scaffolds_and_validates(tmp_path, capsys):
    dest = tmp_path / "new.tokens.json"
    rc = cli.main(["setup-edit", str(dest)])
    assert rc == 0
    assert dest.exists()
    assert "color" in json.loads(dest.read_text())


def test_setup_edit_emits_design_md_sibling(tmp_path, capsys):
    dest = tmp_path / "new.tokens.json"
    rc = cli.main(["setup-edit", str(dest)])
    assert rc == 0
    design = tmp_path / "DESIGN.md"
    assert design.exists()
    text = design.read_text()
    assert 'generator: "design-tokens"' in text
    assert 'source: "new.tokens.json"' in text
    assert "do not hand-edit" in text
    assert "wrote" in capsys.readouterr().out


def test_setup_edit_guards_hand_edited_design_md(tmp_path, capsys):
    # a DESIGN.md without our marker must NOT be clobbered
    (tmp_path / "DESIGN.md").write_text("# My hand-written design notes\n")
    rc = cli.main(["setup-edit", str(tmp_path / "new.tokens.json")])
    assert rc == 0
    assert (tmp_path / "DESIGN.md").read_text() == "# My hand-written design notes\n"
    assert "no design-tokens generator marker" in capsys.readouterr().err


def test_setup_edit_regenerates_own_design_md(tmp_path):
    assert cli.main(["setup-edit", str(tmp_path / "a.tokens.json")]) == 0
    design = tmp_path / "DESIGN.md"
    design.write_text(design.read_text() + "\n<!-- stale -->\n")  # still carries the marker
    assert cli.main(["setup-edit", str(tmp_path / "b.tokens.json")]) == 0
    assert "<!-- stale -->" not in design.read_text()
    assert 'generator: "design-tokens"' in design.read_text()


def test_setup_edit_imports_brand_draft(tmp_path, capsys):
    # brandkit handoff leaves a draft when no token set exists yet
    (tmp_path / "brand-block.draft.json").write_text(json.dumps({
        "$extensions": {"community.design-tokens.brand": {
            "imageryStyle": "risograph", "mood": ["calm"], "avoid": ["neon glow"]}}}))
    dest = tmp_path / "new.tokens.json"
    rc = cli.main(["setup-edit", str(dest)])
    assert rc == 0
    tree = json.loads(dest.read_text())
    block = tree["$extensions"]["community.design-tokens.brand"]
    assert block["imageryStyle"] == "risograph"
    assert block["mood"] == ["calm"]
    assert "imported brand block" in capsys.readouterr().err
    # and the sibling DESIGN.md now carries the Brand direction section
    assert "## Brand direction" in (tmp_path / "DESIGN.md").read_text()


def test_setup_edit_refuses_overwrite(tmp_path):
    dest = tmp_path / "exists.tokens.json"
    dest.write_text("{}")
    rc = cli.main(["setup-edit", str(dest)])
    assert rc == 1


def test_setup_edit_from_clones_source_deterministically(tmp_path):
    src = FIXTURES / "global.base.tokens.json"
    a = tmp_path / "a.tokens.json"
    b = tmp_path / "b.tokens.json"
    assert cli.main(["setup-edit", str(a), "--from", str(src)]) == 0
    assert cli.main(["setup-edit", str(b), "--from", str(src)]) == 0
    # same source -> byte-identical output, and content matches the source tree
    assert a.read_text() == b.read_text()
    assert json.loads(a.read_text()) == json.loads(src.read_text())


def test_setup_edit_from_rejects_missing_source(tmp_path, capsys):
    rc = cli.main(["setup-edit", str(tmp_path / "x.tokens.json"), "--from", str(tmp_path / "nope.json")])
    assert rc == 1
    assert "not found" in capsys.readouterr().out


def test_use_writes_css_and_design_md(tmp_path):
    rc = cli.main([
        "use",
        str(FIXTURES / "global.base.tokens.json"),
        "--name", "Base",
        "--out-dir", str(tmp_path),
    ])
    assert rc == 0
    assert (tmp_path / "tokens.css").exists()
    design = (tmp_path / "DESIGN.md").read_text()
    assert design.startswith("---\nversion: alpha")
    assert 'action-primary: "#1A73E8"' in design
    assert "## Colors" in design
    preview = (tmp_path / "preview.html").read_text()
    assert preview.startswith("<!doctype html>")
    assert "background: #1A73E8" in preview


def test_design_md_command_emits_to_stdout(capsys):
    rc = cli.main(["design-md", str(FIXTURES / "design-md-source.tokens.json"), "--name", "Test Brand"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.startswith("---\nversion: alpha")
    assert "## Typography" in out
