# hdx-scraper-nasa-firms

Maintains the [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/active_fire/) datasets on HDX. Each HDX dataset is one NASA FIRMS region with **external-URL resources pointing directly at NASA-hosted files** — there is no local data fetching, no transformation, and no upload. Files refresh on NASA's side (typically every 3 hours); HDX always serves the latest.

## What it creates

13 datasets under [`organization/nasa-firms`](https://data.humdata.org/organization/nasa-firms), one per NASA-defined region:

```
Global, Canada, Alaska, USA (Contiguous & Hawaii), Central America & Caribbean,
South America, Europe, Northern and Central Africa, Southern Africa,
Russia and Asia, South Asia, Southeast Asia, Australia and New Zealand
```

Each dataset has 36 resources (4 sensors × 3 time windows × 3 formats), or 45 for Canada and the contiguous USA + Hawaii (which add Landsat 8/9 OLI). Resource ordering on HDX mirrors the FIRMS download page (Shapefile → KML → CSV; MODIS → S-NPP → NOAA-20 → NOAA-21 → Landsat; 24h → 48h → 7d).

## Usage

Prereq: an `~/.hdx_configuration.yaml` with `hdx_key_stage` (and `hdx_key` for prod). See `CLAUDE.md` for the full HDX-API setup.

```bash
uv venv --python 3.13
uv pip install hdx-python-api

# Dry run (default — does not write):
.venv/bin/python sync_datasets.py

# Edit DRY_RUN = False at the top of the script, then re-run to apply.
```

The script is idempotent: it CREATEs missing datasets and UPDATEs existing ones, including reordering resources via `match_resource_order=True`.

## Promoting from stage to prod

1. With `HDX_SITE = "stage"` and `DRY_RUN = True`, run and confirm the diff looks right.
2. Set `DRY_RUN = False`, re-run, spot-check the URLs printed at the end.
3. Update `ORG_ID` and `MAINTAINER_ID` to their **prod** equivalents (these IDs differ between sites).
4. Set `HDX_SITE = "prod"`, leave `DRY_RUN = True`, dry-run again — confirm there are no slug collisions with someone else's datasets.
5. Set `DRY_RUN = False`, run for real.

## Editing the dataset matrix

To add/remove resources, change the description, etc., edit the corresponding constants in `sync_datasets.py`:

| What                        | Edit                               |
| --------------------------- | ---------------------------------- |
| Region list                 | `REGIONS`                          |
| Sensor list                 | `SENSORS`, `LANDSAT_SENSOR`        |
| Time windows                | `WINDOWS`                          |
| Output formats              | `FORMATS`                          |
| Per-region copy / locations | `Region` entries, `NOTES_TEMPLATE` |
| Tags / license              | `TAGS`, `LICENSE_ID`               |

Re-run the script to push edits.

## See also

- `CLAUDE.md` — general HDX-API patterns, gotchas, and per-user setup notes (used by Claude Code when working in this repo).
- NASA FIRMS download page: <https://firms.modaps.eosdis.nasa.gov/active_fire/>
- File manifest used to derive the matrix: <https://firms.modaps.eosdis.nasa.gov/api/active_fire_files/all?format=json>
