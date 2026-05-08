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


class Family(NamedTuple):
    suffix: str  # dataset slug suffix, e.g. "modis"
    display: str  # title-case display name, e.g. "MODIS"
    since: str  # one-line "since YYYY" string for the notes template
    data_start: str  # ISO date when this family's FIRMS archive begins
    sensors: list[Sensor]
    only_region_slugs: frozenset[str] | None  # None = all regions


def load_regions() -> list[Region]:
    # NASA's regions overlap and are bbox-cut, so the per-region country lists
    # are the *primary* coverage per UN M49 with adjacent-country additions
    # where the observed bbox extends. Resources still contain everything in
    # NASA's bbox.
    data = json.loads((DATA_DIR / "regions.json").read_text())
    return [Region(**r) for r in data]


def load_families() -> list[Family]:
    # Each family becomes one HDX dataset per region, so each dataset is a
    # filterable single-sensor (or single sensor-line, in VIIRS's case) view.
    # Landsat is restricted to Canada + USA-Contiguous-and-Hawaii — it's the
    # only family NASA publishes selectively, and KML uses animated_48h instead
    # of 7d (handled in builders.windows_for).
    data = json.loads((DATA_DIR / "sensors.json").read_text())
    families = []
    for f in data["families"]:
        only = f.get("only_region_slugs")
        families.append(
            Family(
                suffix=f["suffix"],
                display=f["display"],
                since=f["since"],
                data_start=f["data_start"],
                sensors=[Sensor(**s) for s in f["sensors"]],
                only_region_slugs=frozenset(only) if only else None,
            )
        )
    return families


def families_for_region(families: list[Family], region: Region) -> list[Family]:
    return [
        f
        for f in families
        if f.only_region_slugs is None or region.slug_part in f.only_region_slugs
    ]


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
