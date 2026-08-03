import pytest

from dtokens import contrast
from dtokens import validate as validate_mod


# --- color parsing ---------------------------------------------------------

@pytest.mark.parametrize("value,expected", [
    ("#fff", (255, 255, 255)),
    ("#000000", (0, 0, 0)),
    ("#3b82f6", (0x3b, 0x82, 0xf6)),
    ("rgb(255, 0, 0)", (255, 0, 0)),
    ("rgb(100% 0% 0%)", (255, 0, 0)),
    ("rgba(1 2 3)", (1, 2, 3)),
])
def test_parse_color(value, expected):
    assert contrast.parse_color(value) == expected


def test_parse_oklch_matches_hex():
    # The oklch value Tailwind/better-colors give for #3b82f6.
    assert contrast.to_hex(contrast.parse_color("oklch(0.623 0.188 259.815)")) == "#3b82f6"


@pytest.mark.parametrize("value", [
    "#ffffff80",                 # hex with alpha
    "rgba(0, 0, 0, 0.5)",        # rgb with alpha
    "oklch(0.8 0.05 200 / 0.5)", # oklch with alpha
    "var(--brand)",
    "currentColor",
    "linear-gradient(red, blue)",
    42,
])
def test_unparseable_colors_raise(value):
    with pytest.raises(contrast.Unparseable):
        contrast.parse_color(value)


# --- WCAG ------------------------------------------------------------------

def test_wcag_black_on_white_is_21():
    assert round(contrast.wcag_ratio((0, 0, 0), (255, 255, 255)), 2) == 21.0


def test_wcag_is_order_independent():
    a = contrast.wcag_ratio((0x76,) * 3, (255,) * 3)
    b = contrast.wcag_ratio((255,) * 3, (0x76,) * 3)
    assert round(a, 2) == round(b, 2) == 4.54  # #767676 is the classic AA edge


# --- APCA ------------------------------------------------------------------
# Anchors from the published APCA 0.1.9 test set.

@pytest.mark.parametrize("fg,bg,expected", [
    ((0, 0, 0), (255, 255, 255), 106.04),
    ((255, 255, 255), (0, 0, 0), -107.88),
    ((0x88,) * 3, (255,) * 3, 63.06),
])
def test_apca_reference_values(fg, bg, expected):
    assert round(contrast.apca_lc(fg, bg), 2) == expected


def test_apca_polarity_sign():
    assert contrast.apca_lc((0, 0, 0), (255,) * 3) > 0    # dark on light
    assert contrast.apca_lc((255,) * 3, (0, 0, 0)) < 0    # light on dark


def test_apca_identical_colors_is_zero():
    assert contrast.apca_lc((0x40,) * 3, (0x40,) * 3) == 0.0


# --- OKLCH round-trip ------------------------------------------------------

@pytest.mark.parametrize("hexv", ["#3b82f6", "#0d1117", "#f5b8a5", "#ffffff", "#000000"])
def test_oklch_round_trip_is_lossless(hexv):
    rgb = contrast.parse_color(hexv)
    L, C, H = contrast.rgb_to_oklch(rgb)
    assert contrast.to_hex(contrast.oklch_to_rgb(L, C, H)) == hexv


# --- remediation -----------------------------------------------------------

def test_suggest_fix_preserves_hue_and_chroma():
    fg = contrast.parse_color("#9ec5fe")   # light blue, unreadable on white
    bg = contrast.parse_color("#ffffff")
    _, C0, H0 = contrast.rgb_to_oklch(fg)
    fix = contrast.suggest_fix(fg, bg, "apca", 75.0)
    assert fix is not None
    _, C1, H1 = contrast.rgb_to_oklch(contrast.parse_color(fix[0]))
    assert abs(C1 - C0) < 0.02
    assert abs(H1 - H0) < 2.0


def test_suggest_fix_actually_clears_the_threshold():
    fg = contrast.parse_color("#9ec5fe")
    bg = contrast.parse_color("#ffffff")
    fixed_hex, _ = contrast.suggest_fix(fg, bg, "apca", 75.0)
    assert abs(contrast.apca_lc(contrast.parse_color(fixed_hex), bg)) >= 75.0


def test_suggest_fix_returns_none_when_lightness_cannot_save_it():
    # Foreground and background are the same color: no lightness move on the
    # foreground alone can be found before running out of the 0..1 axis in the
    # chosen direction is not the case here, so assert the honest path instead:
    # a mid-grey on mid-grey needs a very large move but one exists; use a
    # threshold nothing can reach.
    fg = contrast.parse_color("#808080")
    bg = contrast.parse_color("#808080")
    assert contrast.suggest_fix(fg, bg, "apca", 200.0) is None


# --- pairing policy --------------------------------------------------------

def _resolved(**colors):
    return {path: {"type": "color", "value": value} for path, value in colors.items()}


def test_pairs_text_over_background_as_body():
    resolved = _resolved(**{"color.text": "#333333", "color.background": "#ffffff"})
    pairs = contrast.build_pairs(resolved)
    assert ("color.text", "color.background", "body") in pairs


def test_pairs_accent_over_background_as_non_body():
    resolved = _resolved(**{"color.accent": "#3b82f6", "color.background": "#ffffff"})
    assert ("color.accent", "color.background", "non-body") in pairs_of(resolved)


def pairs_of(resolved, **kw):
    return contrast.build_pairs(resolved, **kw)


def test_on_token_pairs_with_its_fill_not_the_page_background():
    resolved = _resolved(**{
        "color.primary": "#1d4ed8",
        "color.on-primary": "#ffffff",
        "color.background": "#ffffff",
    })
    pairs = contrast.build_pairs(resolved)
    assert ("color.on-primary", "color.primary", "body") in pairs
    assert not any(fg == "color.on-primary" and bg == "color.background"
                   for fg, bg, _ in pairs)


def test_level_override_forces_one_threshold():
    resolved = _resolved(**{"color.accent": "#3b82f6", "color.background": "#ffffff"})
    pairs = contrast.build_pairs(resolved, level="body")
    assert all(lvl == "body" for _, _, lvl in pairs)


def test_no_self_pairs():
    resolved = _resolved(**{"color.background": "#ffffff"})
    assert all(fg != bg for fg, bg, _ in contrast.build_pairs(resolved))


# --- report ----------------------------------------------------------------

def test_check_flags_a_failing_pair_and_offers_a_fix():
    resolved = _resolved(**{"color.muted": "#cccccc", "color.background": "#ffffff"})
    report = contrast.check(resolved)
    assert len(report["results"]) == 1
    result = report["results"][0]
    assert result["passed"] is False
    assert result["fix"] is not None


def test_check_passes_a_readable_pair():
    resolved = _resolved(**{"color.text": "#1a1a1a", "color.background": "#ffffff"})
    result = contrast.check(resolved)["results"][0]
    assert result["passed"] is True
    assert result["fix"] is None


def test_unparseable_color_is_unmeasured_never_a_failure():
    resolved = _resolved(**{"color.text": "var(--ink)", "color.background": "#ffffff"})
    report = contrast.check(resolved)
    assert report["results"] == []
    assert [p for p, _v, _r in report["unmeasured"]] == ["color.text"]
    assert contrast.failures(resolved) == []


def test_unmeasured_is_deduplicated_across_pairs():
    resolved = _resolved(**{
        "color.text": "var(--ink)",
        "color.background": "#ffffff",
        "color.surface": "#eeeeee",
    })
    report = contrast.check(resolved)
    assert len(report["unmeasured"]) == 1


def test_standard_selects_which_scale_gates():
    # #747474 on white: ratio 4.67 clears WCAG AA body, Lc 72.5 misses APCA's
    # 75 — the standards genuinely disagree in this band.
    resolved = _resolved(**{"color.text": "#747474", "color.background": "#ffffff"})
    assert contrast.check(resolved, standard="wcag")["results"][0]["passed"] is True
    assert contrast.check(resolved, standard="apca")["results"][0]["passed"] is False
    assert contrast.check(resolved, standard="both")["results"][0]["passed"] is False


def test_failures_returns_readable_advisories():
    resolved = _resolved(**{"color.muted": "#cccccc", "color.background": "#ffffff"})
    msgs = contrast.failures(resolved)
    assert len(msgs) == 1
    assert "color.muted" in msgs[0] and "APCA" in msgs[0] and "try #" in msgs[0]


def test_format_report_is_stable_text():
    resolved = _resolved(**{"color.text": "#1a1a1a", "color.background": "#ffffff"})
    text = contrast.format_report(contrast.check(resolved))
    assert "1 pair(s) measured, 0 failing" in text
    assert "PASS" in text


def test_format_report_with_no_pairs_says_so():
    text = contrast.format_report(contrast.check(_resolved(**{"color.brandish": "#123456"})))
    assert "no measurable text/background pairs" in text


# --- wiring into validate --------------------------------------------------

_FAILING_TREE = {
    "color": {
        "$type": "color",
        "muted": {"$value": "#cccccc"},
        "background": {"$value": "#ffffff"},
    }
}


def test_contrast_failures_are_warnings_by_default():
    assert validate_mod.validate(_FAILING_TREE) == []
    assert any("contrast:" in w for w in validate_mod.warnings(_FAILING_TREE))


def test_contrast_failures_become_errors_under_strict():
    errors = validate_mod.validate(_FAILING_TREE, strict=True)
    assert any("contrast:" in e for e in errors)


def test_clean_tree_has_no_contrast_warnings():
    tree = {
        "color": {
            "$type": "color",
            "text": {"$value": "#1a1a1a"},
            "background": {"$value": "#ffffff"},
        }
    }
    assert not any("contrast:" in w for w in validate_mod.warnings(tree))
    assert validate_mod.validate(tree, strict=True) == []


# --- false-positive guards -------------------------------------------------

@pytest.mark.parametrize("name", ["ink-950", "amber-500", "slate.800", "gray_50"])
def test_palette_ramp_steps_are_recognised(name):
    assert contrast.is_palette_step(name)


@pytest.mark.parametrize("name", ["text", "muted", "background", "on-primary", "accent-1"])
def test_semantic_names_are_not_palette_steps(name):
    assert not contrast.is_palette_step(name)


def test_ramp_steps_are_not_paired():
    # `ink-950` is a swatch, not a role: pairing it with `background` produced
    # "make the ink lighter" nonsense on our own token set.
    resolved = _resolved(**{
        "color.ink-950": "#08080a",
        "color.background": "#08080a",
        "color.text": "#f5f5f5",
    })
    pairs = contrast.build_pairs(resolved)
    assert not any("ink-950" in fg or "ink-950" in bg for fg, bg, _ in pairs)
    assert ("color.text", "color.background", "body") in pairs


def test_identical_colors_are_a_collision_not_a_failure():
    resolved = _resolved(**{"color.text": "#101010", "color.background": "#101010"})
    report = contrast.check(resolved)
    assert report["results"] == []
    assert report["identical"] == [("color.text", "color.background", "#101010")]
    assert contrast.failures(resolved) == []


def test_identical_collision_is_shown_in_the_report():
    resolved = _resolved(**{"color.text": "#101010", "color.background": "#101010"})
    text = contrast.format_report(contrast.check(resolved))
    assert "same color on both sides" in text


# --- opt-in contrast declaration ($extensions) -----------------------------

_SPEC_TREE = {
    "$extensions": {
        "community.design-tokens.contrast": {
            "pairs": [["text", "background"]],
            "exclude": ["surface"],
        }
    },
    "color": {
        "$type": "color",
        "text": {"$value": "#e9e6df"},
        "background": {"$value": "#08080a"},
        "surface": {"$value": "#f2ede3"},
        "muted": {"$value": "#7d7d86"},
    },
}


def test_extract_spec_reads_the_block():
    assert contrast.extract_spec(_SPEC_TREE)["exclude"] == ["surface"]
    assert contrast.extract_spec({}) == {}
    assert contrast.extract_spec({"$extensions": {"other": 1}}) == {}


def test_declared_pairs_are_the_whole_truth():
    resolved = _resolved(**{
        "color.text": "#e9e6df", "color.background": "#08080a",
        "color.surface": "#f2ede3", "color.muted": "#7d7d86",
    })
    spec = contrast.extract_spec(_SPEC_TREE)
    pairs = contrast.build_pairs(resolved, spec=spec)
    assert pairs == [("color.text", "color.background", "body")]


def test_exclude_applies_to_inferred_pairs_too():
    resolved = _resolved(**{
        "color.text": "#e9e6df", "color.background": "#08080a",
        "color.surface": "#f2ede3",
    })
    pairs = contrast.build_pairs(resolved, spec={"exclude": ["surface"]})
    assert not any("surface" in fg or "surface" in bg for fg, bg, _ in pairs)
    assert ("color.text", "color.background", "body") in pairs


def test_spec_names_resolve_by_path_flat_name_or_role():
    resolved = _resolved(**{"color.ink": "#111111", "color.canvas": "#ffffff"})
    # "color.ink" is a path, "canvas" a flat name that infers the background role.
    pairs = contrast.build_pairs(resolved, spec={"pairs": [["color.ink", "canvas"]]})
    assert pairs == [("color.ink", "color.canvas", "body")]


def test_declared_pair_can_name_its_own_level():
    resolved = _resolved(**{"color.text": "#111111", "color.background": "#ffffff"})
    pairs = contrast.build_pairs(
        resolved, spec={"pairs": [["text", "background", "non-body"]]})
    assert pairs == [("color.text", "color.background", "non-body")]


def test_unknown_names_in_the_spec_are_skipped_not_fatal():
    resolved = _resolved(**{"color.text": "#111111", "color.background": "#ffffff"})
    pairs = contrast.build_pairs(
        resolved, spec={"pairs": [["text", "nope"], ["text", "background"], ["bad"]]})
    assert pairs == [("color.text", "color.background", "body")]


def test_spec_silences_the_print_surface_false_positive():
    # The real case from our own design.tokens.json: paper-50 is a print
    # surface, so text-on-surface is not a screen pair at all.
    before = validate_mod.warnings({k: v for k, v in _SPEC_TREE.items()
                                    if k != "$extensions"})
    after = validate_mod.warnings(_SPEC_TREE)
    assert any("color.surface" in w for w in before if "contrast:" in w)
    assert not any("color.surface" in w for w in after if "contrast:" in w)


# --- the graphic level (declared only, never inferred) ---------------------

def test_graphic_level_is_a_lower_bar_than_text():
    assert contrast.THRESHOLDS["graphic"]["apca"] < contrast.THRESHOLDS["non-body"]["apca"]
    assert contrast.THRESHOLDS["graphic"]["wcag"] == 3.0


def test_graphic_level_passes_a_fill_that_fails_as_text():
    # The real case: amber-500 on the near-black canvas. Lc -50.4 — too dim for
    # type, fine as a stroke or fill judged as a UI component.
    resolved = _resolved(**{"color.primary": "#e08b2c", "color.background": "#08080a"})
    as_text = contrast.check(resolved, spec={"pairs": [["primary", "background", "non-body"]]})
    as_fill = contrast.check(resolved, spec={"pairs": [["primary", "background", "graphic"]]})
    assert as_text["results"][0]["passed"] is False
    assert as_fill["results"][0]["passed"] is True


def test_graphic_is_never_inferred():
    # Inference cannot know whether a token is painted as type, so it must never
    # hand out the cheapest bar on its own.
    resolved = _resolved(**{"color.primary": "#e08b2c", "color.background": "#08080a"})
    assert all(lvl != "graphic" for _, _, lvl in contrast.build_pairs(resolved))
