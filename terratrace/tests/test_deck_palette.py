"""The two decks must be one design, not two copies that drift.

There are two generators: `build_deck.js` (the 10-slide technical deck) and
`build_submission_deck.js` (the 7-slide official submission deck). The second was written by copying
the palette out of the first, and the comment in the copy says a test asserts they stay equal. This
is that test.

The risk it guards is specific and it has already bitten this project once in another form: a
published number lived in two files and only one of them was audited. A palette is the same shape of
mistake made visible — the slides would just stop matching, and nobody would notice until they were
side by side on a projector. So the values are compared mechanically rather than trusted.

House style: module-level ``def test_*()`` functions, no pytest, stdlib only.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TECH = ROOT / "scripts" / "build_deck.js"
SUBMISSION = ROOT / "scripts" / "build_submission_deck.js"

_HEX = re.compile(r'([A-Za-z0-9_]+)\s*:\s*"([0-9A-Fa-f]{6})"')


def _read(path):
    assert path.exists(), f"{path.name} is missing; the deck generators moved?"
    return path.read_text(encoding="utf-8")


def _palette(text):
    """The `const INK = ... BG = "......";` declaration, whitespace-normalised."""
    m = re.search(r'^const INK = .*?BG = "[0-9A-Fa-f]{6}";', text, re.M | re.S)
    assert m, "the palette declaration is gone or restructured; update this test with it"
    return re.sub(r"\s+", " ", m.group(0)).strip()


def _theme_colors(text):
    """The pptx theme's colour map, as a dict, with trailing comments stripped."""
    m = re.search(r"colors:\s*\{(.*?)\}", text, re.S)
    assert m, "no `colors:` theme block found"
    return {k: v.upper() for k, v in _HEX.findall(re.sub(r"//.*", "", m.group(1)))}


def _fonts(text):
    return {k: v for k, v in re.findall(
        r"\b(headFontFace|bodyFontFace)\s*:\s*\"([^\"]+)\"", text)}


def _canvas(text):
    m = re.search(r"^const (M|HEAD|BODY) = .*?;\s*$", text, re.M)
    canvas = re.search(r"^const M = .*?H = ([0-9.]+);", text, re.M)
    assert m and canvas, "layout constants not found"
    return canvas.group(0)


# --------------------------------------------------------------------------- the assertion

def test_both_deck_generators_declare_the_same_palette():
    """The named colour constants are equal value for value."""
    tech, sub = _palette(_read(TECH)), _palette(_read(SUBMISSION))
    assert tech == sub, (
        "the submission deck's palette has drifted from the technical deck's:\n"
        f"  build_deck.js            {tech}\n  build_submission_deck.js {sub}"
    )


def test_both_deck_generators_declare_the_same_theme_map():
    """The underlying pptx theme (what PowerPoint shows as theme colours) matches too."""
    tech, sub = _theme_colors(_read(TECH)), _theme_colors(_read(SUBMISSION))
    assert tech == sub, f"theme colour maps differ: only-tech {tech.keys() - sub.keys()}, "\
                        f"only-submission {sub.keys() - tech.keys()}, "\
                        f"changed { {k: (tech[k], sub[k]) for k in tech.keys() & sub.keys() if tech[k] != sub[k]} }"


def test_both_deck_generators_use_the_same_typefaces_and_canvas():
    """Same fonts and same 16:9 canvas, or the two decks are visibly different documents."""
    a, b = _read(TECH), _read(SUBMISSION)
    assert _fonts(a) == _fonts(b), f"font faces differ: {_fonts(a)} vs {_fonts(b)}"
    assert _canvas(a) == _canvas(b), f"canvas differs: {_canvas(a)!r} vs {_canvas(b)!r}"


def test_the_palette_is_dark_text_on_light_ink_and_not_inverted():
    """A sanity check on the values themselves, so an inverted copy cannot pass.

    Both decks are light-ink-on-dark. If someone swapped foreground and background while keeping
    the two files consistent, the equality tests above would still pass — this catches that.
    """
    colors = _theme_colors(_read(TECH))
    def lum(h):
        return int(h[0:2], 16) + int(h[2:4], 16) + int(h[4:6], 16)
    assert lum(colors["dk1"]) > lum(colors["lt1"]), "text1 is not lighter than background1"
    assert lum(colors["lt2"]) > lum(colors["lt1"]), "the panel is not distinguishable from the page"
    assert lum(colors["accent1"]) > lum(colors["lt1"]) + 60, "the accent is too dark to read"


# --------------------------------------------------------------------------- negative control

def test_the_comparison_can_actually_fail():
    """A comparison that always returns equal would pass on any two files, so perturb one.

    This is the check the whole file rests on: if `_palette` were matching something too loose (say,
    the word `const`), every assertion above would be vacuous.
    """
    text = _read(TECH)
    baseline = _palette(text)
    assert _palette(text) == baseline, "the extractor is not deterministic"
    mutated = text.replace('ACC = "6FD6C0"', 'ACC = "6FD6C1"', 1)
    assert mutated != text, "the mutation helper found nothing to change; the pattern is stale"
    assert _palette(mutated) != baseline, (
        "a one-digit palette change went undetected — the extractor is matching too loosely"
    )
    # and the theme map extractor must flag a changed theme entry too
    mut2 = text.replace('"EEF2F7",      // text1', '"EEF2F8",      // text1', 1)
    assert mut2 != text, "the theme mutation helper found nothing to change"
    assert _theme_colors(mut2) != _theme_colors(text)
