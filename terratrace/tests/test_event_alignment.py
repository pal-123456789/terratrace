"""Event alignment: the official requirements, and whether the artefacts actually meet them.

MOST OF THIS FILE IS ABOUT ONE NUMBER AND ONE SENTENCE.

The number is **7** -- the 2026 Judging & Awards Guide admits "a slide presentation (7-slide limit
including title and intro slides) or a video presentation (30-second limit)", and nothing else. A
submission deck of eight slides is not a stylistic problem, it is out of spec. So the slide count is
read out of the .pptx as a ZIP ARCHIVE using only the standard library, because the CI interpreter
has NumPy and nothing else and a check that skips itself on the machine that matters is not a check.

The sentence is the eligibility rule. An earlier version of this repository's eligibility note
asserted that official guidance "permits preparation and data exploration beforehand". No official
page says that; the Participant FAQ says the opposite -- teams "are not allowed to begin working on
the challenges prior to the hackathon". A test below pins the correction in place, because a
softening sentence that nobody is watching is exactly the kind of claim that comes back.

The remaining tests are the discipline this repository applies everywhere else: every quoted official
fact names the page it came from, the audit that judges this work is allowed to have an open row
rather than being uniformly green, and the alignment page is registered with the documentation guard
so its numbers are checked like everything else. A page about compliance that no guard reads would be
the least compliant thing in the tree.
"""
import pathlib
import re
import sys
import zipfile

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent
_REPO = _ROOT.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_HERE))          # harness.py lives HERE, not in the package

from harness import require                                        # noqa: E402

ALIGN = _ROOT / "docs" / "EVENT-ALIGNMENT.md"
ELIG = _ROOT / "docs" / "event" / "eligibility-evidence.md"
SI = _ROOT / "docs" / "event" / "SI-DISCLOSURE.md"
DEMO = _ROOT / "docs" / "DEMO.md"
GUARD = _ROOT / "scripts" / "doc_consistency_check.py"
MKDOCS = _ROOT / "mkdocs.yml"
SUBMISSION_DECK = _REPO / "TerraTrace-submission.pptx"

# The five criteria, spelled as the official page spells them. Pinned as a set so a criterion cannot
# be quietly dropped from the alignment table, and so a sixth one cannot be invented.
CRITERIA = ("Impact", "Creativity", "Validity", "Relevance", "Presentation")

# The three official pages every fact in the alignment document is quoted from.
SOURCES = ("/resources/participant-faqs/",
           "/resources/judging-awards-guide/",
           "/2026/challenges/")


def _text(path):
    require(path.exists(), f"{path.name} is missing, so nothing about it can be checked")
    return path.read_text(encoding="utf-8")


def _flat(path):
    """The same text with whitespace collapsed, for comparing a QUOTED STRING against prose.

    A title or a quoted sentence can be wrapped across lines by an editor without changing what it
    says, so a byte-for-byte search reports a missing quote that is really a line break. The first
    version of the title test did exactly that and failed on a document whose quote was intact.
    """
    return re.sub(r"\s+", " ", _text(path))


# ------------------------------------------------------------------ the demo limit

def test_the_submission_deck_is_within_the_seven_slide_limit():
    """Counted out of the archive, because python-pptx is not on the CI interpreter.

    A .pptx is a zip; its slides are the parts named ``ppt/slides/slideN.xml``. Reading the count
    that way costs nothing and works everywhere, which matters because this is the one check that
    decides whether the submission is admissible.
    """
    require(SUBMISSION_DECK.exists(),
            "TerraTrace-submission.pptx is absent, so the one hard documentary requirement "
            "(a 7-slide or 30-second demo) cannot be checked at all")
    with zipfile.ZipFile(SUBMISSION_DECK) as z:
        slides = [n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]
        require(len(slides) > 0,
                "no slide parts were found in the deck archive; the count below would be vacuous")
        # the notes parts are separate and must not be counted as slides
        notes = [n for n in z.namelist() if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n)]
    assert len(slides) == 7, (
        f"the submission deck has {len(slides)} slides and the limit is 7 including title and intro "
        f"slides; a deck over the limit is out of spec, not merely long")
    assert all(int(re.search(r"(\d+)", n).group(1)) <= len(slides) for n in slides)
    assert len(notes) <= len(slides), "more speaker-note parts than slides is a corrupt archive"


def test_the_two_admissible_demo_forms_are_both_recorded():
    """Both limits, in both places a reader might look. One without the other is a half-truth."""
    for path in (ALIGN, ELIG):
        t = _text(path)
        assert "7-slide" in t, f"{path.name} does not state the 7-slide limit"
        assert "30-second" in t, f"{path.name} does not state the 30-second limit"


def test_the_demo_script_is_not_offered_as_the_submission_demo():
    """The 2½-minute script exceeds both admissible limits and has to say so at the top."""
    t = _text(DEMO)
    head = t[:1400]
    assert "not the submission demo" in head, (
        "DEMO.md does not warn that it is not the submission demo; it is the first thing a hurried "
        "reader will mistake for one")
    assert "7-slide" in head and "30-second" in head, (
        "the warning does not state the limits it is warning about")


# ------------------------------------------------------------------ the eligibility rule

def test_the_preparation_rule_is_quoted_as_the_official_page_states_it():
    t = _text(ALIGN)
    assert "are not allowed" in t and "to begin working on the challenges prior to the hackathon" in t, (
        "the alignment page does not carry the official preparation rule verbatim, so the position "
        "rests on a paraphrase again")
    # and the paraphrase that was NOT supportable must not have come back
    for path in (ALIGN, ELIG):
        assert "permits preparation and data exploration" not in _text(path), (
            f"{path.name} has the unsupported 'permits preparation and data exploration' claim "
            f"back; no official page states it")


def test_the_announcement_and_resource_dates_are_recorded_in_both_documents():
    """The dates are what make 'before the challenge existed' an argument rather than a plea."""
    for path in (ALIGN, ELIG):
        t = _text(path)
        assert ("October 28" in t or "28 October" in t), (
            f"{path.name} does not record that the challenges were announced on 28 October 2026")
        assert ("November 13" in t or "13 November" in t), (
            f"{path.name} does not record that challenge resources were published on 13 November")


# ------------------------------------------------------------------ the five criteria

def test_all_five_official_criteria_are_answered():
    t = _text(ALIGN)
    for c in CRITERIA:
        assert f"**{c}**" in t, f"the alignment table does not answer the official criterion {c!r}"
    # exactly these five, so the table cannot grow a criterion the event does not have. Scoped to
    # §5, because every table in the document uses the same bold-first-column shape.
    section = t[t.index("## 5."):t.index("### The judging flow")]
    named = set(re.findall(r"^\| \*\*([A-Za-z &]+)\*\* \|", section, re.M))
    assert named == set(CRITERIA), f"the criteria table names {sorted(named)}"


# ------------------------------------------------------------------ attribution and honesty

def test_every_official_quote_names_the_page_it_came_from():
    t = _text(ALIGN)
    for src in SOURCES:
        assert src in t, (
            f"no official fact in the alignment page is attributed to {src}; an unattributed quote "
            f"cannot be checked by a reader, which is the whole point of the page")


def test_the_challenge_title_is_confirmed_and_sourced():
    """The title was the one claim in the submission that tooling could not verify.

    It was closed by a person reading the official portal, which is a stronger source than the page
    fetch that failed. Pinned rather than deleted, for two reasons: the confirmation has to keep
    saying WHERE it came from, and the string has to stay identical everywhere it is quoted — a deck
    that names a challenge slightly differently from the submission form is a real defect, and a
    silent drift between the five artefacts that carry it is exactly what this test exists to catch.

    The dead end is kept too. If the note about the CSRF-guarded GraphQL endpoint is dropped, the next
    person will spend the same hour rediscovering that the titles cannot be fetched from here.
    """
    title = "Identify Earth Locations that Analog the Permanent Moon Base Locations and Mars"
    t = _flat(ALIGN)
    assert title in t, "the alignment page no longer records the confirmed title"
    assert "CONFIRMED" in t and "2026-11-15" in t, (
        "the title's confirmation has lost its date, so it reads as an assumption again")
    assert "submission portal" in t, (
        "the confirmation no longer names its source; a confirmed fact with no source is weaker than "
        "an acknowledged uncertainty")
    assert "apollo-require-preflight" in t, (
        "the recorded reason tooling could not read the challenge list has been dropped")
    for path in (ELIG, _REPO / "README.md", _ROOT / "docs" / "SUBMISSION.md"):
        assert title in _flat(path), (
            f"{path.name} does not quote the confirmed challenge title, so a reader of that file "
            f"alone cannot tell which challenge this is submitted to")


def test_the_quality_audit_admits_at_least_one_open_item():
    """An audit table that is uniformly green is not an audit; this one has a known open row."""
    t = _text(ALIGN)
    body = t[t.index("## 9. Quality audit"):t.index("## 10.")]
    rows = [ln for ln in body.splitlines() if ln.startswith("| **")]
    assert len(rows) >= 8, f"the quality audit has {len(rows)} dimensions; that is too few to be one"
    met = sum(1 for ln in rows if ln.rstrip().endswith("**Met** |"))
    assert met < len(rows), (
        f"all {len(rows)} quality-audit rows claim to be met. The eligibility position is DISCLOSED "
        f"but not organizer-confirmed, and a green audit at this stage would be smoothing an open "
        f"risk rather than reporting it")


def test_the_version_strings_stay_off_the_alignment_page():
    """The page is about event rules. A test count on it invites the inference this project refuses."""
    t = _text(ALIGN)
    assert not re.search(r"\b\d{3,4}\s+(?:offline\s+)?tests?\b", t), (
        "the alignment page quotes a test count; a check count is not evidence of compliance")


# ------------------------------------------------------------------ the disclosure

def test_the_mandatory_si_disclosure_exists_and_uses_the_official_term():
    t = _text(SI)
    assert "must include a description of how SI tools were used" in t, (
        "the disclosure page does not carry the official requirement it exists to satisfy")
    assert "Super Intelligence" in t, (
        "the official 2026 term for the disclosure is 'Super Intelligence (SI)'; using only 'AI' "
        "risks not answering the field that was asked")
    assert SI.exists() and ALIGN.exists()
    assert "SI-DISCLOSURE.md" in _text(ALIGN), (
        "the alignment page does not link the disclosure it requires")


# ------------------------------------------------------------------ it is guarded

def test_the_alignment_pages_are_registered_with_the_documentation_guard():
    """A compliance page no guard reads is the least compliant artefact in the tree."""
    g = _text(GUARD)
    mk = _text(MKDOCS)
    for name in ("EVENT-ALIGNMENT.md", "event/SI-DISCLOSURE.md"):
        assert name in g or name.split("/")[-1] in g, (
            f"{name} is not in the documentation guard's canonical list, so its numbers are "
            f"unchecked while every other current document's are checked")
        assert name.split("/")[-1] in mk, f"{name} is not in the mkdocs nav"
    assert "event/eligibility-evidence.md" in mk
