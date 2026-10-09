"""Transfer-gap taxonomy.

Every comparison carries an explicit ledger of what an Earth morphology
match can and cannot establish about a planetary operation. Transfer
classes:

  T0 comparable observable at declared support
  T1 potentially informative but context dependent
  T2 non-replicable physical condition
  T3 unknown (insufficient data/support/evidence)
  T4 requires authorized field or laboratory experiment
"""
from __future__ import annotations

MARS_TRANSFER_LEDGER = [
    {"category": "topographic_morphology", "class": "T0",
     "statement": "Map-scale slope/relief/ruggedness comparable at declared support.",
     "prohibited": "Do not infer rock-scale obstacles or wheel-scale hazards."},
    {"category": "low_slope_connectivity", "class": "T1",
     "statement": "Broad corridor structure is comparable at declared support.",
     "prohibited": "Not a traversable route or path guarantee."},
    {"category": "gravity", "class": "T2",
     "statement": "Mars surface gravity (~0.38 g) is not reproduced on Earth.",
     "prohibited": "Do not infer mobility, slip, or stability transfer."},
    {"category": "atmosphere_pressure", "class": "T2",
     "statement": "Mars atmospheric density/pressure is not reproduced.",
     "prohibited": "Do not infer dust lofting, aero-thermal, or EDL behaviour."},
    {"category": "regolith_mechanics", "class": "T3",
     "statement": "Mechanical soil behaviour is not inferred from a DEM.",
     "prohibited": "Do not claim traction, sinkage, or bearing equivalence."},
    {"category": "radiation", "class": "T2",
     "statement": "Surface radiation environment is not reproduced.",
     "prohibited": "Do not infer radiation effects from terrain."},
    {"category": "thermal_cycle", "class": "T3",
     "statement": "Diurnal/seasonal thermal regime is not inferred from terrain.",
     "prohibited": "Do not infer thermal survival."},
    {"category": "illumination", "class": "T3",
     "statement": "Illumination geometry is context only unless modelled.",
     "prohibited": "Do not infer power or imaging performance."},
    {"category": "communications", "class": "T3",
     "statement": "Relay/line-of-sight geometry is not inferred from terrain.",
     "prohibited": "Do not infer link availability."},
    {"category": "site_access", "class": "T4",
     "statement": "Field access/permission is not implied by public data.",
     "prohibited": "Do not present as an authorized test site."},
    {"category": "ecology_community", "class": "T4",
     "statement": "Ecological and community governance must be verified.",
     "prohibited": "Do not plan field work without authorization."},
]


def ledger_for(result_state):
    """Return the transfer-gap ledger plus a header note tied to the result."""
    note = ("Morphology comparison only. The following conditions are not "
            "established by this result and bound every downstream claim.")
    return {"note": note, "result_state": result_state, "gaps": MARS_TRANSFER_LEDGER}


def prohibited_claims():
    return [g["prohibited"] for g in MARS_TRANSFER_LEDGER]
