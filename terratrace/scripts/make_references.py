#!/usr/bin/env python3
"""Write the TerraTrace 'Data sources & credits' Markdown bundle to a file.

Renders terratrace.references.references_md() -- the full catalog grouped by body,
each with its upstream provider's required citation and licence -- and writes it to
the output path, then prints that path. Offline; pure standard library.

    python3 scripts/make_references.py                    # -> artifacts/REFERENCES.md
    python3 scripts/make_references.py --out docs/REFERENCES.md
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import references


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="artifacts/REFERENCES.md",
                    help="output path for the Markdown credits "
                         "(default: artifacts/REFERENCES.md)")
    args = ap.parse_args(argv)

    markdown = references.references_md()
    parent = os.path.dirname(args.out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(markdown)
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
