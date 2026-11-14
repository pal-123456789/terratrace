#!/usr/bin/env bash
# Verify TerraTrace end to end, from a checkout, in one command.
#
#   bash scripts/reproduce_all.sh
#
# Five steps. The first three need nothing but Python and NumPy. The fourth reads only committed
# records. The fifth needs the terrain data, which is deliberately NOT in the repository (it is
# hundreds of megabytes of third-party rasters), so it SAYS SO and stops rather than reporting a pass
# it did not earn -- a skip that looks like a success is the failure mode this whole project is about.
#
# No step rewrites a published result. Every step that produces an artifact writes it from a frozen
# protocol, and the atlas REFUSES to write at all if two of its six records disagree.
set -euo pipefail
cd "$(dirname "$0")/.."

DATA_MISSING=""
for d in data/moon data/earth; do
  [ -d "$d" ] || DATA_MISSING="$DATA_MISSING $d"
done

hr() { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }

hr "1/5  the offline test suite"
python3 tests/run_tests.py

hr "2/5  the scientific-correctness oracles"
python3 scripts/run_validation.py

hr "3/5  the documentation-consistency guard"
python3 scripts/doc_consistency_check.py

hr "4/5  the scale-resolved discovery atlas"
# Reads artifacts/*.json only, so it runs anywhere. It reconciles six committed records and refuses
# to publish on a single disagreement between any two of them.
python3 scripts/run_discovery_atlas.py

if [ -n "$DATA_MISSING" ]; then
  hr "5/5  SKIPPED -- the independent-axis probe"
  cat <<EOF
NOT RUN. Its inputs are absent:$DATA_MISSING

The probe re-windows the real lunar and Earth rasters, and that data is not in the repository. Its
record IS committed (artifacts/lunar_axis_probe/lunar_axis_probe.json) and step 4 reconciles that
record against the others, so the published finding is checked here. What is skipped is re-deriving
it from the rasters, not the finding itself.

To run it: place the lunar surface tiles under data/moon/ and the Copernicus GLO-30 tiles under
data/earth/ as listed in REAL-DATA-RUNBOOK.md, then re-run this script.
EOF
  exit 0
fi

hr "5/5  the independent-axis probe"
python3 scripts/lunar_axis_probe.py

hr "done"
echo "All five steps completed. Nothing above was skipped silently."
