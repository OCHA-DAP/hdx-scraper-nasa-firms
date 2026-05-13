"""Resource and Dataset builders for the NASA FIRMS regional rollout."""

from __future__ import annotations

from hdx.data.dataset import Dataset
from hdx.data.resource import Resource

from .config import BASE, DATA_DIR, LICENSE_ID, MAINTAINER_ID, ORG_ID, TAGS
from .models import Family, Region, Sensor, load_families, load_windows_formats

FAMILIES = load_families()
WINDOWS, FORMATS = load_windows_formats()

NOTES_TEMPLATE = (DATA_DIR / "notes_template.txt").read_text()
CAVEATS_TEMPLATE = (DATA_DIR / "caveats.txt").read_text().rstrip("\n")


def methodology_for(family: Family) -> str:
    return (DATA_DIR / f"methodology_{family.suffix}.txt").read_text().rstrip("\n")

LANDSAT_KML_NOTE = (
    " (Landsat KML uses an animated 48-hour file in place of the 7-day one.)"
)


def resource_url(
    sensor: Sensor, region: Region, fmt_subdir: str, ext: str, window: str
) -> str:
    return f"{BASE}/{sensor.path}/{fmt_subdir}/{sensor.prefix}{region.nasa_name}_{window}.{ext}"


def resource_name(sensor: Sensor, window: str, fmt_label: str) -> str:
    return f"{sensor.label} - {window} ({fmt_label})"


def windows_for(family: Family, fmt_label: str) -> list[tuple[str, str]]:
    # NASA publishes Landsat KML only as 24h / 48h / animated_48h — no 7-day
    # file for that format/sensor pair. Everything else uses the standard
    # WINDOWS list (24h / 48h / 7d).
    if family.suffix == "landsat" and fmt_label == "KML":
        return [("24h", "24h"), ("48h", "48h"), ("animated_48h", "animated 48h")]
    return [(w, w) for w, _ in WINDOWS]


def build_resources(region: Region, family: Family) -> list[Resource]:
    # Walk format -> sensor -> window so the resource list mirrors the
    # top-to-bottom, left-to-right reading order of the NASA FIRMS page.
    resources = []
    for fmt_subdir, ext, fmt_label in FORMATS:
        for sensor in family.sensors:
            for win_path, win_label in windows_for(family, fmt_label):
                url = resource_url(sensor, region, fmt_subdir, ext, win_path)
                r = Resource(
                    {
                        "name": resource_name(sensor, win_label, fmt_label),
                        "description": (
                            f"{sensor.label} active fire detections for the "
                            f"{region.pretty} region over the {win_label} window. "
                            f"External link to the NASA FIRMS file (continuously "
                            f"updated)."
                        ),
                        "url": url,
                    }
                )
                r.set_format(fmt_label)
                resources.append(r)
    return resources


def dataset_slug(region: Region, family: Family) -> str:
    return f"nasa-firms-active-fire-{region.slug_part}-{family.suffix}"


def build_dataset(region: Region, family: Family) -> Dataset:
    slug = dataset_slug(region, family)
    title = f"{region.pretty} - {family.display} Active Fire Detections"

    landsat_kml_note = LANDSAT_KML_NOTE if family.suffix == "landsat" else ""
    ds = Dataset(
        {
            "name": slug,
            "title": title,
            "notes": NOTES_TEMPLATE.format(
                pretty=region.pretty,
                family_display=family.display,
                since=family.since,
                landsat_kml_note=landsat_kml_note,
            ),
            "dataset_source": "NASA Fire Information for Resource Management System (FIRMS)",
            "methodology": "Other",
            "methodology_other": methodology_for(family),
            "caveats": CAVEATS_TEMPLATE.format(pretty=region.pretty),
            "license_id": LICENSE_ID,
            "data_update_frequency": "0",  # live (string, per SDK convention — int 0 trips check_required_fields)
            "subnational": "1",  # point-level / sub-national
            "private": False,
        }
    )
    ds.set_maintainer(MAINTAINER_ID)
    ds.set_organization(ORG_ID)
    for iso in region.locations:
        if iso == "world":
            ds.add_other_location("world")
        else:
            ds.add_country_location(iso)
    # Open-ended period: start = sensor-family archive era, end = ongoing.
    # Resources are external links to continuously-updated NASA files.
    ds.set_time_period(family.data_start, ongoing=True)
    ds.add_tags(TAGS)

    for r in build_resources(region, family):
        ds.add_update_resource(r)
    return ds
