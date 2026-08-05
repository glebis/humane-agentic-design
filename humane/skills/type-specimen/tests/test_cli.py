import json

from tspec import cli, config


def run(*argv):
    return cli.main(list(argv))


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_init_writes_a_config_that_checks_but_has_todos(tmp_path, capsys):
    p = tmp_path / "kettle.json"
    assert run("init", "-o", str(p), "--context", "a till for cafés") == 0
    cfg = read(p)
    assert cfg["id"] == "kettle"
    assert cfg["context"] == "a till for cafés"
    # `check` is the gate: valid structure, unwritten copy.
    assert run("check", str(p)) == 1


def test_init_refuses_to_clobber_without_force(tmp_path, capsys):
    p = tmp_path / "c.json"
    run("init", "-o", str(p))
    assert run("init", "-o", str(p)) == 2
    assert "already exists" in capsys.readouterr().err
    assert run("init", "-o", str(p), "--force") == 0


def test_init_reads_context_from_a_file(tmp_path):
    src = tmp_path / "brief.md"
    src.write_text("Receipts are read at arm's length.", encoding="utf-8")
    p = tmp_path / "c.json"
    run("init", "-o", str(p), "--context", "a till", "--from-file", str(src))
    assert read(p)["context"] == "a till\n\nReceipts are read at arm's length."


def fill(p):
    run("texts", str(p),
        "--set", "display=Display",
        "--set", "headline=Headline",
        "--set", "weights=Weights",
        "--set", "prose=One.\\nTwo.",
        "--set", "caps=CAPS",
        "--set", "rows=Name :: Value",
        "--set", "table=a :: b :: c",
        "--set", "tableHead=A :: B :: C")


def test_texts_set_writes_slots_and_expands_newlines(tmp_path):
    p = tmp_path / "c.json"
    run("init", "-o", str(p))
    fill(p)
    cfg = read(p)
    assert cfg["texts"]["prose"] == "One.\nTwo."
    assert config.todos(cfg) == []
    assert run("check", str(p)) == 0


def test_texts_rejects_an_unknown_slot(tmp_path, capsys):
    p = tmp_path / "c.json"
    run("init", "-o", str(p))
    assert run("texts", str(p), "--set", "kerning=on") == 2
    assert "unknown slot 'kerning'" in capsys.readouterr().err


def test_a_bad_set_does_not_corrupt_the_config(tmp_path, capsys):
    p = tmp_path / "c.json"
    run("init", "-o", str(p))
    fill(p)
    before = read(p)
    # Two cells where the table wants three.
    assert run("texts", str(p), "--set", "table=a :: b") == 2
    assert "table line 1" in capsys.readouterr().err
    assert read(p) == before


def test_texts_appends_to_the_stored_brief(tmp_path):
    p = tmp_path / "c.json"
    run("init", "-o", str(p), "--context", "first")
    run("texts", str(p), "--context", "second")
    assert read(p)["context"] == "first\n\nsecond"


def test_build_refuses_a_config_with_todos(tmp_path, capsys):
    p = tmp_path / "c.json"
    run("init", "-o", str(p))
    assert run("build", str(p), "--no-serve") == 2
    assert "still say TODO" in capsys.readouterr().err
    assert not (tmp_path / "c.html").exists()


def test_build_with_allow_todo_writes_the_page_and_warns(tmp_path, capsys):
    p = tmp_path / "c.json"
    run("init", "-o", str(p))
    assert run("build", str(p), "--no-serve", "--allow-todo") == 0
    assert (tmp_path / "c.html").exists()
    assert "unwritten slot" in capsys.readouterr().err


def test_build_defaults_the_output_next_to_the_config(tmp_path):
    p = tmp_path / "c.json"
    run("init", "-o", str(p))
    fill(p)
    assert run("build", str(p), "--no-serve") == 0
    html = (tmp_path / "c.html").read_text(encoding="utf-8")
    assert "Headline" in html


def test_build_creates_a_missing_output_directory(tmp_path):
    p = tmp_path / "c.json"
    run("init", "-o", str(p))
    fill(p)
    out = tmp_path / "site" / "spec.html"
    assert run("build", str(p), "-o", str(out), "--no-serve") == 0
    assert out.exists()


def test_missing_config_exits_cleanly(tmp_path, capsys):
    assert run("check", str(tmp_path / "absent.json")) == 2
    assert "no such config" in capsys.readouterr().err
