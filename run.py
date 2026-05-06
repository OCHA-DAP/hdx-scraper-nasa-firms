"""Create or update one HDX dataset per NASA FIRMS region on stage, each
linked to NASA-hosted files via external URLs. Idempotent: re-running this
script updates existing datasets in place.

Resource matrix per dataset:
- 4 sensors x 3 windows x 3 formats = 36 resources for most regions
- Canada and USA (Contiguous + Hawaii) include Landsat OLI as well, so 45

Defaults to DRY RUN. Set DRY_RUN = False below to actually write.
"""

from __future__ import annotations

from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset

from nasa_firms.builders import FORMATS, SENSORS, WINDOWS, build_dataset
from nasa_firms.config import USER_AGENT
from nasa_firms.models import load_regions

# ---------- knobs ----------
DRY_RUN = True
HDX_SITE = "stage"  # flip to "prod" only after a successful stage dry-run


def main() -> None:
    Configuration.create(
        user_agent=USER_AGENT,
        hdx_site=HDX_SITE,
        hdx_read_only=DRY_RUN,
    )
    site_root = (
        "https://stage.data-humdata-org.ahconu.org"
        if HDX_SITE == "stage"
        else "https://data.humdata.org"
    )

    regions = load_regions()
    print(f"\n{'DRY RUN' if DRY_RUN else 'LIVE WRITE'} on hdx_site={HDX_SITE}")
    print(
        f"Will process {len(regions)} datasets, "
        f"{len(SENSORS) * len(WINDOWS) * len(FORMATS)} resources each "
        f"= {len(regions) * len(SENSORS) * len(WINDOWS) * len(FORMATS)} resources total.\n"
    )

    for region in regions:
        ds = build_dataset(region)
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
