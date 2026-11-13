"""TerraTrace reference engine.

A clean-room-safe, synthetic-data reference implementation of the
Planetary Analog OS morphology-transfer nucleus.

This package computes map-scale terrain morphology features, compares a
reference ("planetary") terrain unit with candidate ("Earth") terrain
units at a declared common spatial support, exposes transfer gaps, and
emits a reproducible study package.

Scientific boundary: this engine screens terrain *morphology* only. It
does NOT estimate rover traversability, validate autonomy, establish
geological equivalence, certify site access, or certify mission
readiness.
"""

__version__ = "0.3.0"
# NOTE: this is the PACKAGE version. The study-package *schema* version
# (``terratrace.cli._SCHEMA_VERSION``) is a separate, slower-moving number: the
# on-disk shape of a study bundle has not changed. ``pyproject.toml`` must agree
# with ``__version__`` -- ``tests/test_ci_hygiene.py`` enforces that so the two
# cannot drift.

