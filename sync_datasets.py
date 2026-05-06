"""Create or update one HDX dataset per NASA FIRMS region on stage, each
linked to NASA-hosted files via external URLs. Idempotent: re-running this
script updates existing datasets in place.

Resource matrix per dataset:
- 4 sensors x 3 windows x 3 formats = 36 resources for most regions
- Canada and USA (Contiguous + Hawaii) include Landsat OLI as well, so 45

Defaults to DRY RUN. Set DRY_RUN = False at the top to actually write.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from hdx.data.resource import Resource

# ---------- knobs ----------
DRY_RUN = True
HDX_SITE = "stage"   # flip to "prod" only after a successful stage dry-run
USER_AGENT = "HDXINTERNAL_<YourName>_AdHoc"

# Stage IDs. To find your own user id (to use as MAINTAINER_ID), see
# CLAUDE.md > "Looking up IDs and vocabularies".
ORG_ID = "fcc8b988-f150-4d57-af3d-4dee06896aac"         # nasa-firms (stage)
MAINTAINER_ID = "b682f6f7-cd7e-4bd4-8aa7-f74138dc6313"  # nasa-firms admin (stage)

LICENSE_ID = "other-pd-nr"   # Public Domain / No restrictions (CC0)
TAGS = ["climate hazards", "natural disasters", "hazards and risk",
        "geodata", "environment"]

BASE = "https://firms.modaps.eosdis.nasa.gov/data/active_fire"

# ---------- sensors / windows / formats ----------
class Sensor(NamedTuple):
    label: str
    path: str       # subdir under /active_fire/
    prefix: str     # filename prefix

SENSORS = [
    Sensor("MODIS C6.1 (Terra/Aqua)",   "modis-c6.1",          "MODIS_C6_1_"),
    Sensor("VIIRS S-NPP C2 (Suomi-NPP)", "suomi-npp-viirs-c2", "SUOMI_VIIRS_C2_"),
    Sensor("VIIRS NOAA-20 C2",           "noaa-20-viirs-c2",   "J1_VIIRS_C2_"),
    Sensor("VIIRS NOAA-21 C2",           "noaa-21-viirs-c2",   "J2_VIIRS_C2_"),
]

# Landsat OLI 8/9 is published by NASA only for Canada and the contiguous USA
# (+ Hawaii). KML doesn't get a 7d file — it gets an animated_48h instead.
LANDSAT_SENSOR = Sensor("Landsat 8/9 OLI", "landsat", "LANDSAT_")
LANDSAT_REGION_SLUGS = {"canada", "usa-contiguous-and-hawaii"}

WINDOWS = [("24h", "last 24 hours"), ("48h", "last 48 hours"), ("7d", "last 7 days")]

# Format / sensor / window order matches the NASA FIRMS active_fire page:
# the page stacks SHP -> KML -> CSV sections (top-to-bottom), and within each
# table sensors run MODIS -> S-NPP -> NOAA-20 -> NOAA-21 across columns and
# time windows run 24h -> 48h -> 7d.
FORMATS = [
    ("shapes/zips",  "zip",  "SHP"),   # SHP zipped
    ("kml",          "kml",  "KML"),
    ("csv",          "csv",  "CSV"),
]

# ---------- regions ----------
# NASA's regions overlap and are bbox-cut, so the country lists below are the
# *primary* coverage per UN M49 with adjacent-country additions where the
# observed bbox extends. Resources still contain everything in NASA's bbox.
class Region(NamedTuple):
    nasa_name: str            # NASA path token (case-sensitive)
    pretty: str               # human title
    slug_part: str            # for the dataset slug
    locations: list[str]      # ISO3 lowercase, or ["world"] for global

REGIONS = [
    # Order matches the NASA FIRMS active_fire page (World first, then Canada
    # before Alaska, etc).
    Region("Global", "Global", "global", ["world"]),
    Region("Canada", "Canada", "canada", ["can"]),
    Region("Alaska", "Alaska", "alaska", ["usa"]),
    Region("USA_contiguous_and_Hawaii", "USA (Contiguous & Hawaii)",
           "usa-contiguous-and-hawaii", ["usa"]),
    Region("Central_America", "Central America & the Caribbean",
           "central-america-and-caribbean",
           ["mex", "blz", "cri", "slv", "gtm", "hnd", "nic", "pan",
            "atg", "bhs", "brb", "cub", "dma", "dom", "grd", "hti", "jam",
            "kna", "lca", "vct", "tto", "pri"]),
    Region("South_America", "South America", "south-america",
           ["arg", "bol", "bra", "chl", "col", "ecu", "flk", "guf",
            "guy", "pry", "per", "sur", "ury", "ven"]),
    Region("Europe", "Europe", "europe",
           ["alb", "and", "aut", "blr", "bel", "bih", "bgr", "hrv", "cyp",
            "cze", "dnk", "est", "fin", "fra", "deu", "grc", "hun", "isl",
            "irl", "ita", "lva", "lie", "ltu", "lux", "mlt", "mda", "mco",
            "mne", "nld", "mkd", "nor", "pol", "prt", "rou", "smr", "srb",
            "svk", "svn", "esp", "swe", "che", "tur", "ukr", "gbr", "vat"]),
    Region("Northern_and_Central_Africa", "Northern and Central Africa",
           "northern-and-central-africa",
           ["dza", "egy", "lby", "mar", "tun", "esh",
            "sdn", "ssd", "mrt", "mli", "bfa", "ner", "tcd",
            "sen", "gmb", "gin", "gnb", "sle", "lbr", "civ", "gha", "tgo",
            "ben", "nga", "cmr", "caf", "gnq", "stp", "gab", "cog", "cod",
            "eth", "eri", "dji", "som", "ken", "uga", "rwa", "bdi"]),
    Region("Southern_Africa", "Southern Africa", "southern-africa",
           ["zaf", "nam", "bwa", "zwe", "moz", "zmb", "mwi", "mdg",
            "lso", "swz", "com", "mus", "syc", "ago", "tza"]),
    Region("Russia_Asia", "Russia and Asia", "russia-and-asia",
           ["rus", "kaz", "kgz", "tjk", "tkm", "uzb",
            "mng", "chn", "prk", "kor", "jpn",
            "geo", "arm", "aze", "irn", "irq", "syr", "lbn", "isr", "pse",
            "jor", "sau", "yem", "omn", "are", "qat", "bhr", "kwt"]),
    Region("South_Asia", "South Asia", "south-asia",
           ["afg", "bgd", "btn", "ind", "mdv", "npl", "pak", "lka"]),
    Region("SouthEast_Asia", "Southeast Asia", "southeast-asia",
           ["brn", "khm", "idn", "lao", "mys", "mmr", "phl",
            "sgp", "tha", "tls", "vnm", "png"]),
    Region("Australia_NewZealand", "Australia and New Zealand",
           "australia-and-new-zealand",
           ["aus", "nzl", "slb", "vut", "ncl", "fji", "ton", "wsm",
            "cok", "nfk"]),
]

# ---------- copy ----------
NOTES_TEMPLATE = """\
Near-real-time active fire and thermal anomaly detections from NASA's Fire \
Information for Resource Management System (FIRMS) covering **{pretty}**.

Each resource is an external link directly to a NASA-hosted file. The files \
are continuously updated as new satellite overpasses are processed (typically \
within 3 hours of acquisition).

**Formats:**

- Zipped Shapefile
- KML
- CSV

**Sensors:**

- MODIS Collection 6.1 — Terra and Aqua satellites (since 2000/2002)
- VIIRS Collection 2 — Suomi-NPP (since 2011)
- VIIRS Collection 2 — NOAA-20 (since 2017)
- VIIRS Collection 2 — NOAA-21 (since 2022){landsat_line}

**Time windows:**

- Last 24 hours
- Last 48 hours
- Last 7 days{landsat_kml_note}

Each detection is a 375 m (VIIRS) or 1 km (MODIS) pixel where the sensor \
identified a thermal anomaly. Common attributes include latitude, longitude, \
brightness temperature, scan/track pixel size, acquisition date/time (UTC), \
detection confidence, fire radiative power (FRP), and day/night flag.

**Note on coverage:** NASA's "{pretty}" file is bounded by a fixed lat/lon \
box, which may include parts of adjacent countries beyond the locations \
listed for this dataset. For arbitrary bounding boxes or country-level \
extracts, use the FIRMS Area API \
(https://firms.modaps.eosdis.nasa.gov/api/area/) with a free MAP_KEY.

Data source: https://firms.modaps.eosdis.nasa.gov/active_fire/
"""

METHODOLOGY_OTHER = (
    "Active fire / thermal anomaly detections derived from MODIS (1 km) and "
    "VIIRS (375 m) instruments. Detections are produced by NASA's Land, "
    "Atmosphere Near real-time Capability for EOS (LANCE) and distributed via "
    "FIRMS. See https://earthdata.nasa.gov/faq/firms-faq for algorithm "
    "details, known limitations, and disclaimer."
)

# ---------- builders ----------
def resource_url(sensor: Sensor, region: Region, fmt_subdir: str,
                 ext: str, window: str) -> str:
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
                r = Resource({
                    "name": resource_name(sensor, window, fmt_label),
                    "description": (
                        f"{sensor.label} active fire detections for the "
                        f"{region.pretty} region over the {window} window. "
                        f"External link to the NASA FIRMS file (continuously "
                        f"updated)."
                    ),
                    "url": url,
                })
                r.set_format(fmt_label)
                resources.append(r)
        # Landsat appears after the four MODIS/VIIRS sensors in NASA's
        # manifest, but only for Canada and USA (Conterminous) and Hawaii.
        if region.slug_part in LANDSAT_REGION_SLUGS:
            if fmt_label == "KML":
                ls_windows = [("24h", "24h"), ("48h", "48h"),
                              ("animated_48h", "animated 48h")]
            else:
                ls_windows = [(w, w) for w, _ in WINDOWS]
            for win_path, win_label in ls_windows:
                url = (f"{BASE}/{LANDSAT_SENSOR.path}/{fmt_subdir}/"
                       f"{LANDSAT_SENSOR.prefix}{region.nasa_name}_{win_path}.{ext}")
                r = Resource({
                    "name": f"{LANDSAT_SENSOR.label} - {win_label} ({fmt_label})",
                    "description": (
                        f"{LANDSAT_SENSOR.label} (30 m) active fire detections "
                        f"for the {region.pretty} region over the {win_label} "
                        f"window. External link to the NASA FIRMS file "
                        f"(continuously updated)."
                    ),
                    "url": url,
                })
                r.set_format(fmt_label)
                resources.append(r)
    return resources

def build_dataset(region: Region) -> Dataset:
    slug = f"nasa-firms-active-fire-{region.slug_part}"
    title = f"{region.pretty}: NASA FIRMS Active Fire Detections"

    has_landsat = region.slug_part in LANDSAT_REGION_SLUGS
    landsat_line = (
        "\n- Landsat 8/9 OLI (30 m) — since 2022"
        if has_landsat else ""
    )
    landsat_kml_note = (
        " (Landsat KML uses an animated 48-hour file in place of the 7-day one.)"
        if has_landsat else ""
    )
    ds = Dataset({
        "name": slug,
        "title": title,
        "notes": NOTES_TEMPLATE.format(pretty=region.pretty,
                                       landsat_line=landsat_line,
                                       landsat_kml_note=landsat_kml_note),
        "dataset_source": "NASA Fire Information for Resource Management System (FIRMS)",
        "methodology": "Other",
        "methodology_other": METHODOLOGY_OTHER,
        "license_id": LICENSE_ID,
        "data_update_frequency": 1,   # daily
        "subnational": "1",            # point-level / sub-national
        "private": False,
    })
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

# ---------- run ----------
def main() -> None:
    Configuration.create(
        user_agent=USER_AGENT,
        hdx_site=HDX_SITE,
        hdx_read_only=DRY_RUN,
    )
    site_root = ("https://stage.data-humdata-org.ahconu.org" if HDX_SITE == "stage"
                 else "https://data.humdata.org")

    print(f"\n{'DRY RUN' if DRY_RUN else 'LIVE WRITE'} on hdx_site={HDX_SITE}")
    print(f"Will process {len(REGIONS)} datasets, "
          f"{len(SENSORS) * len(WINDOWS) * len(FORMATS)} resources each "
          f"= {len(REGIONS) * len(SENSORS) * len(WINDOWS) * len(FORMATS)} resources total.\n")

    for region in REGIONS:
        ds = build_dataset(region)
        slug = ds["name"]
        existing = Dataset.read_from_hdx(slug)
        action = "UPDATE" if existing else "CREATE"

        print(f"[{action}] {slug}")
        print(f"  title:      {ds['title']}")
        print(f"  locations:  {[g['name'] for g in ds.get('groups', [])] or region.locations}")
        print(f"  resources:  {len(ds.get_resources())}")
        print(f"  url:        {site_root}/dataset/{slug}")

        if DRY_RUN:
            try:
                ds.check_required_fields()
                print("  required fields: OK")
            except Exception as e:
                print(f"  required fields: FAIL -> {e}")
            continue

        if existing:
            ds.update_in_hdx(
                remove_additional_resources=False,
                match_resource_order=True,
                hxl_update=False,
                updated_by_script=f"{USER_AGENT} - nasa-firms regional rollout",
            )
        else:
            ds.create_in_hdx(
                allow_no_resources=False,
                updated_by_script=f"{USER_AGENT} - nasa-firms regional rollout",
            )
        print(f"  -> wrote: {site_root}/dataset/{slug}")

if __name__ == "__main__":
    main()
