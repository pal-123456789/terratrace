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

__version__ = "0.1.0"
