"""Turn a Markdown outline into a list of cards.

Format:
    ---                      optional front matter
    title: My talk
    ---
    # Card heading           every top-level or second-level heading starts a card
    - a bullet point
    Plain lines become paragraphs.
    > Stage cue (click, pause, show prop)
    @ 2:30                   optional time mark for this card
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Card:
    heading: str
    items: list[tuple[str, str]] = field(default_factory=list)  # (kind, text)
    time: str | None = None


@dataclass
class Deck:
    title: str = ""
    cards: list[Card] = field(default_factory=list)


HEADING = re.compile(r"^#{1,2}\s+(.*)$")
BULLET = re.compile(r"^\s*[-*]\s+(.*)$")
NUMBERED = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
CUE = re.compile(r"^\s*>\s?(.*)$")
TIME = re.compile(r"^\s*@\s*(\S.*)$")


def parse(text: str) -> Deck:
    deck = Deck()
    lines = text.splitlines()

    if lines and lines[0].strip() == "---":
        end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), None)
        if end:
            for line in lines[1:end]:
                key, _, value = line.partition(":")
                if key.strip().lower() == "title":
                    deck.title = value.strip()
            lines = lines[end + 1:]

    card: Card | None = None
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        if m := HEADING.match(line):
            card = Card(heading=m.group(1).strip())
            deck.cards.append(card)
            continue
        if card is None:  # text before the first heading gets an untitled card
            card = Card(heading="")
            deck.cards.append(card)
        if m := TIME.match(line):
            card.time = m.group(1).strip()
        elif m := CUE.match(line):
            card.items.append(("cue", m.group(1).strip()))
        elif m := BULLET.match(line):
            card.items.append(("bullet", m.group(1).strip()))
        elif m := NUMBERED.match(line):
            card.items.append(("number", f"{m.group(1)}. {m.group(2).strip()}"))
        else:
            card.items.append(("text", line.strip()))
    return deck
