"""Draw cards to PDF with ReportLab.

Each card is A6 landscape (148 x 105 mm), a quarter of an A4 sheet.
Layouts:
    single  one card per page; print on A6 card stock or "fit to page"
    a4      four cards per A4 landscape sheet with cut marks; cut once each way
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

from .parse import Card, Deck

CARD_W, CARD_H = 148 * mm, 105 * mm
MARGIN = 7 * mm
FOOTER_H = 6 * mm
ACCENT = colors.HexColor("#7A1F2B")   # deep claret
MUTED = colors.HexColor("#6B6B6B")
CUE_BG = colors.HexColor("#F3ECE4")


@dataclass
class Options:
    layout: str = "single"
    max_size: float = 22
    min_size: float = 11
    numbered: bool = True


def inline(text: str) -> str:
    """Escape for ReportLab and convert **bold** and *italic*."""
    t = escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t)
    return t


def _paragraphs(card: Card, size: float) -> list[Paragraph]:
    lead = size * 1.22
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=size, leading=lead,
                          spaceAfter=size * 0.35)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=size * 0.9,
                            bulletIndent=0, bulletFontName="Helvetica-Bold",
                            bulletFontSize=size, bulletColor=ACCENT)
    cue = ParagraphStyle("cue", parent=body, fontName="Helvetica-Oblique",
                         fontSize=size * 0.85, leading=size * 1.05, textColor=ACCENT,
                         backColor=CUE_BG, borderPadding=(3, 5, 3, 5),
                         leftIndent=5, rightIndent=5,
                         spaceBefore=size * 0.3, spaceAfter=size * 0.55)
    out = []
    for kind, text in card.items:
        if kind == "bullet":
            out.append(Paragraph(inline(text), bullet, bulletText="•"))
        elif kind == "cue":
            out.append(Paragraph("» " + inline(text), cue))
        else:
            out.append(Paragraph(inline(text), body))
    return out


def _fit(card: Card, width: float, height: float, opts: Options):
    """Largest font size whose paragraphs fit the body box."""
    size = opts.max_size
    while True:
        paras = _paragraphs(card, size)
        total = 0.0
        for p in paras:
            _, h = p.wrap(width, height)
            total += h + p.style.spaceBefore + p.style.spaceAfter
        if total <= height or size <= opts.min_size:
            return paras, size, total <= height
        size -= 0.5


def draw_card(c: canvas.Canvas, x: float, y: float, card: Card, idx: int, total: int,
              deck: Deck, opts: Options) -> bool:
    """Draw one card with its lower-left corner at (x, y). Returns False on overflow."""
    inner_w = CARD_W - 2 * MARGIN
    top = y + CARD_H - MARGIN

    # Heading
    # The heading is a small label; the body text is what you read at the podium.
    head_style = ParagraphStyle("head", fontName="Helvetica-Bold", fontSize=11,
                                leading=13, textColor=ACCENT)
    head_h = 0.0
    if card.heading:
        head = Paragraph(inline(card.heading.upper()), head_style)
        _, head_h = head.wrap(inner_w, 40 * mm)
        head.drawOn(c, x + MARGIN, top - head_h)
        head_h += 2.5 * mm
        c.setStrokeColor(ACCENT)
        c.setLineWidth(1.2)
        c.line(x + MARGIN, top - head_h + 1 * mm, x + MARGIN + 18 * mm, top - head_h + 1 * mm)
        head_h += 2 * mm

    # Body, auto-sized
    body_top = top - head_h
    body_bottom = y + MARGIN + FOOTER_H
    paras, _, fits = _fit(card, inner_w, body_top - body_bottom, opts)
    cursor = body_top
    for p in paras:
        _, h = p.wrap(inner_w, body_top - body_bottom)
        cursor -= p.style.spaceBefore
        if cursor - h < body_bottom:
            break
        p.drawOn(c, x + MARGIN, cursor - h)
        cursor -= h + p.style.spaceAfter

    # Footer
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    c.drawString(x + MARGIN, y + MARGIN, deck.title[:70])
    right = f"{idx} / {total}" if opts.numbered else ""
    if card.time:
        right = f"{card.time}   {right}".strip()
    c.drawRightString(x + CARD_W - MARGIN, y + MARGIN, right)
    c.setFillColor(colors.black)
    return fits


def _cut_marks(c: canvas.Canvas, page_w: float, page_h: float):
    c.setStrokeColor(colors.HexColor("#BBBBBB"))
    c.setLineWidth(0.4)
    c.setDash(2, 2)
    c.line(page_w / 2, 0, page_w / 2, 6 * mm)
    c.line(page_w / 2, page_h - 6 * mm, page_w / 2, page_h)
    c.line(0, page_h / 2, 6 * mm, page_h / 2)
    c.line(page_w - 6 * mm, page_h / 2, page_w, page_h / 2)
    c.setDash()


def render(deck: Deck, out_path: str, opts: Options | None = None) -> list[int]:
    """Write the PDF. Returns the numbers of cards whose text did not fit."""
    opts = opts or Options()
    overflow: list[int] = []
    total = len(deck.cards)

    if opts.layout == "a4":
        page = landscape(A4)
        c = canvas.Canvas(out_path, pagesize=page)
        slots = [(0, CARD_H), (CARD_W, CARD_H), (0, 0), (CARD_W, 0)]
        # Center the 2x2 grid (A4 is 297 x 210 mm; four cards are 296 x 210 mm).
        dx = (page[0] - 2 * CARD_W) / 2
        for i, card in enumerate(deck.cards):
            if i and i % 4 == 0:
                c.showPage()
            if i % 4 == 0:
                _cut_marks(c, *page)
            sx, sy = slots[i % 4]
            if not draw_card(c, dx + sx, sy, card, i + 1, total, deck, opts):
                overflow.append(i + 1)
    else:
        c = canvas.Canvas(out_path, pagesize=(CARD_W, CARD_H))
        for i, card in enumerate(deck.cards):
            if i:
                c.showPage()
            if not draw_card(c, 0, 0, card, i + 1, total, deck, opts):
                overflow.append(i + 1)

    c.setTitle(deck.title or "Presenter cards")
    c.save()
    return overflow
