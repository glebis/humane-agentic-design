import json

import pytest

from tspec import SpecimenError, config

from tests.helpers import filled


def test_starter_is_valid_but_flags_its_placeholders():
    cfg = config.starter()
    assert config.validate(cfg) == []
    assert set(config.todos(cfg)) == {
        "display", "headline", "weights", "prose", "caps", "rows", "table", "tableHead"}


def test_filled_config_has_no_todos():
    assert config.validate(filled()) == []
    assert config.todos(filled()) == []


def test_ru_starter_ships_a_cyrillic_alphabet_and_script_range():
    cfg = config.starter(locale="ru")
    assert config.validate(cfg) == []
    assert "А" in cfg["texts"]["alphabet"]
    assert cfg["scriptRange"] == r"U\+04"


def test_starter_rejects_an_unknown_locale():
    with pytest.raises(SpecimenError):
        config.starter(locale="de")


# ── slot shape ────────────────────────────────────────────────────────────

def test_single_line_slot_rejects_a_second_line():
    cfg = filled()
    cfg["texts"]["display"] = "one\ntwo"
    assert any("display must be a single line" in e for e in config.validate(cfg))


def test_multiline_slot_accepts_many_lines():
    cfg = filled()
    cfg["texts"]["prose"] = "a\nb\nc\n"
    assert config.validate(cfg) == []


def test_cell_count_is_enforced_per_line():
    cfg = filled()
    cfg["texts"]["table"] = "a :: b :: c\nd :: e"
    errors = config.validate(cfg)
    assert any("table line 2" in e and "3 '::'" in e for e in errors)


def test_blank_lines_do_not_count_as_rows():
    cfg = filled()
    cfg["texts"]["rows"] = "a :: b\n\n\nc :: d\n"
    assert config.validate(cfg) == []


def test_empty_slot_is_an_error():
    cfg = filled()
    cfg["texts"]["caps"] = "   "
    assert any("caps must be a non-empty string" in e for e in config.validate(cfg))


def test_unknown_slot_is_reported():
    cfg = filled()
    cfg["texts"]["ligatures"] = "fi fl"
    assert any("unknown text slot 'ligatures'" in e for e in config.validate(cfg))


# ── families and groups ───────────────────────────────────────────────────

def test_family_name_may_not_contain_the_cell_separator():
    cfg = filled(families=[{"name": "Bad :: Name", "group": "sf"}])
    assert any("may not contain" in e for e in config.validate(cfg))


def test_duplicate_families_are_reported():
    cfg = filled(families=[{"name": "Inter", "group": "sf"},
                           {"name": "Inter", "group": "sf"}])
    assert any("duplicate family" in e for e in config.validate(cfg))


def test_family_in_an_undeclared_group_is_reported():
    cfg = filled(families=[{"name": "Inter", "group": "ghost"}])
    assert any("not declared in groups" in e for e in config.validate(cfg))


def test_all_is_a_reserved_group_id():
    cfg = filled(groups=[{"id": "all", "label": "Everything"}],
                 families=[{"name": "Inter", "group": ""}])
    assert any("reserved" in e for e in config.validate(cfg))


def test_empty_family_group_is_allowed():
    cfg = filled(families=[{"name": "Inter", "group": ""}])
    assert config.validate(cfg) == []


# ── scalars and colours ───────────────────────────────────────────────────

def test_id_must_be_a_safe_localstorage_key():
    assert any("id must be" in e for e in config.validate(filled(id="two words")))


@pytest.mark.parametrize("key,bad", [
    ("size", 40), ("weight", 950), ("lh", 3.0), ("ls", 1.0),
])
def test_scalars_outside_the_slider_range_are_rejected(key, bad):
    assert any(key in e for e in config.validate(filled(**{key: bad})))


def test_booleans_are_not_accepted_as_numbers():
    # bool is an int subclass, so this needs its own guard.
    assert any("size" in e for e in config.validate(filled(size=True)))


@pytest.mark.parametrize("key", ["bg", "fg"])
def test_colours_must_be_six_digit_hex(key):
    assert any(key in e for e in config.validate(filled(**{key: "#fff"})))


def test_dark_and_light_must_be_pairs():
    assert any("dark" in e for e in config.validate(filled(dark=["#000000"])))


def test_bad_script_range_regex_is_reported():
    assert any("not a valid regex" in e for e in config.validate(filled(scriptRange="U\\+[04")))


# ── load ──────────────────────────────────────────────────────────────────

def test_load_applies_defaults_and_infers_id_from_the_filename(tmp_path):
    p = tmp_path / "kettle.json"
    body = {k: v for k, v in filled().items() if k not in ("id", "title", "size")}
    p.write_text(json.dumps(body), encoding="utf-8")
    cfg = config.load(p)
    assert cfg["id"] == "kettle"
    assert cfg["title"] == "kettle"
    assert cfg["size"] == config.DEFAULTS["size"]


def test_load_fills_missing_slots_from_the_starter(tmp_path):
    p = tmp_path / "part.json"
    body = filled()
    body["texts"] = {"display": "Only this one"}
    p.write_text(json.dumps(body), encoding="utf-8")
    cfg = config.load(p)
    assert cfg["texts"]["display"] == "Only this one"
    assert cfg["texts"]["alphabet"] == config.STARTER_TEXTS["alphabet"]


def test_load_reports_bad_json_by_path(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{nope", encoding="utf-8")
    with pytest.raises(SpecimenError, match="not valid JSON"):
        config.load(p)


def test_load_reports_a_missing_file(tmp_path):
    with pytest.raises(SpecimenError, match="no such config"):
        config.load(tmp_path / "absent.json")


def test_load_rejects_a_json_array(tmp_path):
    p = tmp_path / "list.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(SpecimenError, match="JSON object"):
        config.load(p)
