from dtokens import validate


def test_valid_tree_returns_no_errors():
    tree = {
        "color": {
            "$type": "color",
            "blue": {"$value": "#00f"},
            "brand": {"$value": "{color.blue}"},
        }
    }
    assert validate.validate(tree) == []


def test_unknown_type_is_reported():
    tree = {"x": {"$type": "banana", "$value": "1"}}
    errors = validate.validate(tree)
    assert any("banana" in e and "x" in e for e in errors)


def test_undeterminable_type_is_reported():
    tree = {"x": {"$value": "whatever"}}
    errors = validate.validate(tree)
    assert any("type" in e.lower() and "x" in e for e in errors)


def test_dangling_alias_is_reported():
    tree = {"a": {"$type": "color", "$value": "{color.missing}"}}
    errors = validate.validate(tree)
    assert any("color.missing" in e for e in errors)


def test_circular_alias_is_reported():
    tree = {
        "a": {"$type": "color", "$value": "{b}"},
        "b": {"$type": "color", "$value": "{a}"},
    }
    errors = validate.validate(tree)
    assert any("circular" in e.lower() for e in errors)


# --- brand-block warnings (non-fatal art-direction contract) ---

def _brand_tree(brand):
    return {
        "color": {"$type": "color", "primary": {"$value": "#0E7C7B"}},
        "$extensions": {validate.BRAND_EXT_KEY: brand},
    }


def test_missing_brand_block_warns_not_errors():
    tree = {"color": {"$type": "color", "primary": {"$value": "#0E7C7B"}}}
    assert validate.validate(tree) == []          # still valid
    warns = validate.warnings(tree)
    assert len(warns) == 1
    assert "brand-style block" in warns[0]
    assert "brand-illustrate" in warns[0]


def test_brand_block_without_imagerystyle_warns():
    warns = validate.warnings(_brand_tree({"mood": ["calm"]}))
    assert len(warns) == 1
    assert "imageryStyle" in warns[0]


def test_complete_brand_block_has_no_warning():
    tree = _brand_tree({"mood": ["calm"], "imageryStyle": "flat vector, dot-grid"})
    assert validate.warnings(tree) == []


def test_empty_brand_block_warns_as_missing():
    assert "brand-style block" in validate.warnings(_brand_tree({}))[0]


# --- non-DTCG dimension tolerance (clamp/calc/var kept verbatim) ---

def _clamp_tree():
    return {
        "space": {"$type": "dimension",
                  "section": {"$value": "clamp(72px, 11vw, 150px)"},
                  "md": {"$value": {"value": 16, "unit": "px"}}},
        "type": {"display": {"$type": "typography", "$value": {
            "fontFamily": "Inter", "fontSize": "clamp(2.6rem, 5vw, 3.6rem)"}}},
    }


def test_clamp_dimension_is_valid_by_default():
    # not a hard error — the value is kept verbatim, only warned about
    assert validate.validate(_clamp_tree()) == []


def test_dimension_warnings_flag_string_dimensions():
    resolved = {
        "space.section": {"type": "dimension", "value": "clamp(72px, 11vw, 150px)"},
        "space.md": {"type": "dimension", "value": {"value": 16, "unit": "px"}},
        "type.display": {"type": "typography",
                         "value": {"fontFamily": "Inter", "fontSize": "clamp(2.6rem, 5vw, 3.6rem)"}},
    }
    warns = validate.dimension_warnings(resolved)
    assert any("space.section" in w and "clamp" in w for w in warns)
    assert any("type.display.fontSize" in w for w in warns)
    assert not any("space.md" in w for w in warns)  # well-formed token not flagged


def test_strict_promotes_dimension_warnings_to_errors():
    errors = validate.validate(_clamp_tree(), strict=True)
    assert any("non-DTCG dimension" in e and "space.section" in e for e in errors)
    assert validate.validate(_clamp_tree()) == []  # default keeps it valid


def test_warnings_includes_dimension_advisories():
    assert any("clamp" in w for w in validate.warnings(_clamp_tree()))
