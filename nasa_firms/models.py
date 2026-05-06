"""NamedTuple types and JSON loaders for the dataset matrix."""

from __future__ import annotations

import json
from typing import NamedTuple

from .config import DATA_DIR


class Sensor(NamedTuple):
    label: str
    path: str  # subdir under /active_fire/
    prefix: str  # filename prefix


class Region(NamedTuple):
    nasa_name: str  # NASA path token (case-sensitive)
    pretty: str  # human title
    slug_part: str  # for the dataset slug
    locations: list[str]  # ISO3 lowercase, or ["world"] for global


def load_regions() -> list[Region]:
    # NASA's regions overlap and are bbox-cut, so the per-region country lists
    # are the *primary* coverage per UN M49 with adjacent-country additions
    # where the observed bbox extends. Resources still contain everything in
    # NASA's bbox.
    data = json.loads((DATA_DIR / "regions.json").read_text())
    return [Region(**r) for r in data]


def load_sensors() -> tuple[list[Sensor], Sensor, set[str]]:
    # Landsat OLI 8/9 is published by NASA only for Canada and the contiguous
    # USA (+ Hawaii); KML doesn't get a 7d file — it gets an animated_48h.
    data = json.loads((DATA_DIR / "sensors.json").read_text())
    sensors = [Sensor(**s) for s in data["sensors"]]
    landsat = Sensor(**data["landsat_sensor"])
    return sensors, landsat, set(data["landsat_region_slugs"])


def load_windows_formats() -> (
    tuple[list[tuple[str, str]], list[tuple[str, str, str]]]
):
    # Format / sensor / window order mirrors the NASA FIRMS active_fire page:
    # the page stacks SHP -> KML -> CSV (top-to-bottom), and within each table
    # sensors run MODIS -> S-NPP -> NOAA-20 -> NOAA-21 across columns and time
    # windows run 24h -> 48h -> 7d.
    data = json.loads((DATA_DIR / "windows_formats.json").read_text())
    windows = [tuple(w) for w in data["windows"]]
    formats = [tuple(f) for f in data["formats"]]
    return windows, formats
