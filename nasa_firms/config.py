"""Static configuration: HDX IDs, tags, base URL, and the data directory path."""

from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

USER_AGENT = "HDXINTERNAL_NASA_FIRMS_AdHoc"

# Stage IDs. To find your own user id (to use as MAINTAINER_ID), see
# CLAUDE.md > "Looking up IDs and vocabularies".
ORG_ID = "fcc8b988-f150-4d57-af3d-4dee06896aac"  # nasa-firms (stage)
MAINTAINER_ID = "b682f6f7-cd7e-4bd4-8aa7-f74138dc6313"  # nasa-firms admin (stage)

LICENSE_ID = "other-pd-nr"  # Public Domain / No restrictions (CC0)
TAGS = [
    "climate hazards",
    "natural disasters",
    "hazards and risk",
    "geodata",
    "environment",
]

BASE = "https://firms.modaps.eosdis.nasa.gov/data/active_fire"
