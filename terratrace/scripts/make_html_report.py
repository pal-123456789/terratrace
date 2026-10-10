#!/usr/bin/env python3
"""Render a TerraTrace study or batch package to a self-contained HTML report.

Loads a study package (default artifacts/study.json) or, with --batch, a batch
report, renders it via terratrace.report_html into a single offline HTML file
(inline CSS, no external assets), writes it into the output directory, and
prints the written path. Offline; no third-party dependencies.

    python3 scripts/make_html_report.py                          # study -> study_report.html
    python3 scripts/make_html_report.py --study artifacts/study.json
    python3 scripts/make_html_report.py --batch artifacts/batch.json
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import report_html


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--study", default="artifacts/study.json",
                    help="study package JSON (default: artifacts/study.json)")
    ap.add_argument("--batch", default=None,
                    help="batch report JSON (e.g. artifacts/batch.json); "
                         "overrides --study when given")
    ap.add_argument("--out", default="artifacts",
                    help="output directory for the HTML report (default: artifacts)")
    args = ap.parse_args(argv)

    if args.batch:
        pkg = json.load(open(args.batch, encoding="utf-8"))
        html_str = report_html.batch_report_html(pkg)
        out_path = os.path.join(args.out, "batch_report.html")
    else:
        pkg = json.load(open(args.study, encoding="utf-8"))
        html_str = report_html.study_report_html(pkg)
        out_path = os.path.join(args.out, "study_report.html")

    report_html.write_html(html_str, out_path)
    print(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
