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
