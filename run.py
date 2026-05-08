"""Create or update one HDX dataset per (region, sensor family) combination
on stage, each linked to NASA-hosted files via external URLs. Idempotent:
re-running this script updates existing datasets in place.

Sensor families:
- MODIS  (single sensor: MODIS C6.1)
- VIIRS  (S-NPP + NOAA-20 + NOAA-21 grouped)
- Landsat (Canada and USA-Contiguous-and-Hawaii only)

Resource matrix per dataset:
- MODIS:   1 sensor x 3 windows x 3 formats = 9 resources
- VIIRS:   3 sensors x 3 windows x 3 formats = 27 resources
- Landsat: 1 sensor x 3 formats x (3 std windows + animated_48h KML carve-out) = 9 resources

Defaults to DRY RUN. Set DRY_RUN = False below to actually write.
"""

from __future__ import annotations

from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset

from nasa_firms.builders import FAMILIES, build_dataset
from nasa_firms.config import USER_AGENT
from nasa_firms.models import families_for_region, load_regions

# ---------- knobs ----------
DRY_RUN = True
HDX_SITE = "stage"  # flip to "prod" only after a successful stage dry-run


def _site_root(hdx_site: str) -> str:
    return (
        "https://stage.data-humdata-org.ahconu.org"
        if hdx_site == "stage"
        else "https://data.humdata.org"
    )


def main() -> None:
    Configuration.create(
        user_agent=USER_AGENT,
        hdx_site=HDX_SITE,
        hdx_read_only=DRY_RUN,
    )
    site_root = _site_root(HDX_SITE)
    regions = load_regions()

    pairs = [(r, f) for r in regions for f in families_for_region(FAMILIES, r)]
    print(f"\n{'DRY RUN' if DRY_RUN else 'LIVE WRITE'} on hdx_site={HDX_SITE}")
    print(
        f"Will process {len(pairs)} datasets "
        f"({len(regions)} regions x families, with Landsat only for Canada + USA).\n"
    )

    for region, family in pairs:
        ds = build_dataset(region, family)
        slug = ds["name"]
        existing = Dataset.read_from_hdx(slug)
        action = "UPDATE" if existing else "CREATE"

        print(f"[{action}] {slug}")
        print(f"  title:      {ds['title']}")
        print(
            f"  locations:  {[g['name'] for g in ds.get('groups', [])] or region.locations}"
        )
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
                updated_by_script=f"{USER_AGENT} - nasa-firms per-sensor rollout",
            )
        else:
            ds.create_in_hdx(
                allow_no_resources=False,
                updated_by_script=f"{USER_AGENT} - nasa-firms per-sensor rollout",
            )
        print(f"  -> wrote: {site_root}/dataset/{slug}")


if __name__ == "__main__":
    main()
