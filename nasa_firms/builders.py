"""Resource and Dataset builders for the NASA FIRMS regional rollout."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hdx.data.dataset import Dataset
from hdx.data.resource import Resource

from .config import BASE, DATA_DIR, LICENSE_ID, MAINTAINER_ID, ORG_ID, TAGS
from .models import Region, Sensor, load_sensors, load_windows_formats

SENSORS, LANDSAT_SENSOR, LANDSAT_REGION_SLUGS = load_sensors()
WINDOWS, FORMATS = load_windows_formats()

NOTES_TEMPLATE = (DATA_DIR / "notes_template.txt").read_text()
METHODOLOGY_OTHER = (DATA_DIR / "methodology.txt").read_text().rstrip("\n")


def resource_url(
    sensor: Sensor, region: Region, fmt_subdir: str, ext: str, window: str
) -> str:
    return f"{BASE}/{sensor.path}/{fmt_subdir}/{sensor.prefix}{region.nasa_name}_{window}.{ext}"


def resource_name(sensor: Sensor, window: str, fmt_label: str) -> str:
    return f"{sensor.label} - {window} ({fmt_label})"


def build_resources(region: Region) -> list[Resource]:
    # Walk format -> sensor -> window so the resource list mirrors the
    # top-to-bottom, left-to-right reading order of the NASA FIRMS page.
    resources = []
    for fmt_subdir, ext, fmt_label in FORMATS:
        for sensor in SENSORS:
            for window, _ in WINDOWS:
                url = resource_url(sensor, region, fmt_subdir, ext, window)
                r = Resource(
                    {
                        "name": resource_name(sensor, window, fmt_label),
                        "description": (
                            f"{sensor.label} active fire detections for the "
                            f"{region.pretty} region over the {window} window. "
                            f"External link to the NASA FIRMS file (continuously "
                            f"updated)."
                        ),
                        "url": url,
                    }
                )
                r.set_format(fmt_label)
                resources.append(r)
        # Landsat appears after the four MODIS/VIIRS sensors in NASA's
        # manifest, but only for Canada and USA (Conterminous) and Hawaii.
        if region.slug_part in LANDSAT_REGION_SLUGS:
            if fmt_label == "KML":
                ls_windows = [
                    ("24h", "24h"),
                    ("48h", "48h"),
                    ("animated_48h", "animated 48h"),
                ]
            else:
                ls_windows = [(w, w) for w, _ in WINDOWS]
            for win_path, win_label in ls_windows:
                url = (
                    f"{BASE}/{LANDSAT_SENSOR.path}/{fmt_subdir}/"
                    f"{LANDSAT_SENSOR.prefix}{region.nasa_name}_{win_path}.{ext}"
                )
                r = Resource(
                    {
                        "name": f"{LANDSAT_SENSOR.label} - {win_label} ({fmt_label})",
                        "description": (
                            f"{LANDSAT_SENSOR.label} (30 m) active fire detections "
                            f"for the {region.pretty} region over the {win_label} "
                            f"window. External link to the NASA FIRMS file "
                            f"(continuously updated)."
                        ),
                        "url": url,
                    }
                )
                r.set_format(fmt_label)
                resources.append(r)
    return resources


def build_dataset(region: Region) -> Dataset:
    slug = f"nasa-firms-active-fire-{region.slug_part}"
    title = f"{region.pretty}: NASA FIRMS Active Fire Detections"

    has_landsat = region.slug_part in LANDSAT_REGION_SLUGS
    landsat_line = "\n- Landsat 8/9 OLI (30 m) — since 2022" if has_landsat else ""
    landsat_kml_note = (
        " (Landsat KML uses an animated 48-hour file in place of the 7-day one.)"
        if has_landsat
        else ""
    )
    ds = Dataset(
        {
            "name": slug,
            "title": title,
            "notes": NOTES_TEMPLATE.format(
                pretty=region.pretty,
                landsat_line=landsat_line,
                landsat_kml_note=landsat_kml_note,
            ),
            "dataset_source": "NASA Fire Information for Resource Management System (FIRMS)",
            "methodology": "Other",
            "methodology_other": METHODOLOGY_OTHER,
            "license_id": LICENSE_ID,
            "data_update_frequency": 1,  # daily
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
    # Rolling 7-day window for the resource contents
    now = datetime.now(timezone.utc)
    ds.set_time_period(now - timedelta(days=7), now)
    ds.add_tags(TAGS)

    for r in build_resources(region):
        ds.add_update_resource(r)
    return ds
