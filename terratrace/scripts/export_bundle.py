#!/usr/bin/env python3
"""Export a complete TerraTrace study DELIVERABLE in one command.

With ``--study PATH`` an existing study package JSON is bundled; otherwise a
fresh synthetic study is run (``terratrace.study.run_study``). The JSON package,
Markdown + HTML reports, data-sources credits, offline viewer, and a checksums
manifest are written into ``--out``, and the output directory plus every file
written is printed. Offline; no third-party dependencies.

    python3 scripts/export_bundle.py
    python3 scripts/export_bundle.py --study artifacts/study.json --out artifacts/bundle
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import bundle, study


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--study", default=None,
                    help="existing study package JSON to bundle; if omitted, a fresh "
                         "synthetic study is run")
    ap.add_argument("--out", default="artifacts/bundle",
                    help="output directory for the deliverable bundle "
                         "(default: artifacts/bundle)")
    ap.add_argument("--n-boot", type=int, default=0,
                    help="bootstrap resamples when running a fresh study (default: 0)")
    args = ap.parse_args(argv)

    if args.study:
        with open(args.study, encoding="utf-8") as fh:
            pkg = json.load(fh)
    else:
        pkg = study.run_study(n_boot=args.n_boot)

    manifest = bundle.export_bundle(pkg, args.out)
    bundle.write_manifest(manifest, args.out)

    print(f"bundle -> {manifest['outdir']}")
    for name in sorted(manifest["files"]):
        info = manifest["files"][name]
        print(f"  {name}  ({info['bytes']} bytes, sha256 {info['sha256'][:12]}...)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
