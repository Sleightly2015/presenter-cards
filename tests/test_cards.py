"""Run:  python -m pytest"""

from pypdf import PdfReader

from presenter_cards.parse import parse
from presenter_cards.render import CARD_H, CARD_W, Options, render

SAMPLE = """---
title: Test Talk
---
# Opening
@ 0:30
- First point with **bold**
> Pause here
Plain sentence & <symbols>

## Second card
1. Step one
2. Step two
"""


def test_parse_structure():
    deck = parse(SAMPLE)
    assert deck.title == "Test Talk"
    assert [c.heading for c in deck.cards] == ["Opening", "Second card"]
    first = deck.cards[0]
    assert first.time == "0:30"
    assert [k for k, _ in first.items] == ["bullet", "cue", "text"]
    assert deck.cards[1].items[1] == ("number", "2. Step two")


def test_text_before_first_heading_gets_a_card():
    deck = parse("Just a note\n# Real card\n- x")
    assert len(deck.cards) == 2 and deck.cards[0].heading == ""


def test_single_layout_page_size(tmp_path):
    out = tmp_path / "cards.pdf"
    assert render(parse(SAMPLE), str(out)) == []
    reader = PdfReader(out)
    assert len(reader.pages) == 2
    box = reader.pages[0].mediabox
    assert round(float(box.width)) == round(CARD_W) and round(float(box.height)) == round(CARD_H)
    assert "Step two" in reader.pages[1].extract_text()


def test_a4_layout_puts_four_cards_per_sheet(tmp_path):
    md = "\n".join(f"# Card {i}\n- point {i}" for i in range(1, 7))
    out = tmp_path / "sheet.pdf"
    render(parse(md), str(out), Options(layout="a4"))
    assert len(PdfReader(out).pages) == 2


def test_overflow_is_reported(tmp_path):
    md = "# Too much\n" + "\n".join(f"- a very long bullet point number {i} " * 3 for i in range(40))
    assert render(parse(md), str(tmp_path / "x.pdf")) == [1]
