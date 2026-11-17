"""Command-line entry point:  presenter-cards talk.md [-o cards.pdf] [--layout a4]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .parse import parse
from .render import Options, render


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="presenter-cards",
        description="Turn a Markdown outline into printable A6 presenter note cards.",
    )
    ap.add_argument("source", help="Markdown file; each # or ## heading starts a card")
    ap.add_argument("-o", "--output", help="PDF path (default: source name + .pdf)")
    ap.add_argument("--layout", choices=["single", "a4"], default="single",
                    help="single = one A6 card per page; a4 = four per A4 sheet with cut marks")
    ap.add_argument("--max-size", type=float, default=22, help="largest body font size (pt)")
    ap.add_argument("--min-size", type=float, default=11, help="smallest body font size (pt)")
    ap.add_argument("--no-numbers", action="store_true", help="hide the n / N card counter")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = ap.parse_args(argv)

    src = Path(args.source)
    deck = parse(src.read_text(encoding="utf-8"))
    if not deck.cards:
        print("No cards found. Start each card with a '# Heading' line.", file=sys.stderr)
        return 2
    if not deck.title:
        deck.title = src.stem.replace("_", " ").replace("-", " ")

    out = args.output or str(src.with_suffix(".pdf"))
    opts = Options(layout=args.layout, max_size=args.max_size, min_size=args.min_size,
                   numbered=not args.no_numbers)
    overflow = render(deck, out, opts)

    print(f"Wrote {len(deck.cards)} cards to {out}", file=sys.stderr)
    if overflow:
        print("Too much text even at the minimum size on card(s): "
              + ", ".join(map(str, overflow)) + ". Split them or trim text.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
