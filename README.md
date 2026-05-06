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
.venv/bin/python run.py

# Edit DRY_RUN = False at the top of run.py, then re-run to apply.
```

The script is idempotent: it CREATEs missing datasets and UPDATEs existing ones, including reordering resources via `match_resource_order=True`.

## Promoting from stage to prod

1. With `HDX_SITE = "stage"` and `DRY_RUN = True`, run and confirm the diff looks right.
2. Set `DRY_RUN = False`, re-run, spot-check the URLs printed at the end.
3. Update `ORG_ID` and `MAINTAINER_ID` in `nasa_firms/config.py` to their **prod** equivalents (these IDs differ between sites).
4. Set `HDX_SITE = "prod"`, leave `DRY_RUN = True`, dry-run again — confirm there are no slug collisions with someone else's datasets.
5. Set `DRY_RUN = False`, run for real.

## Editing the dataset matrix

To add/remove resources, change the description, etc., edit the corresponding file:

| What                        | Edit                                                                       |
| --------------------------- | -------------------------------------------------------------------------- |
| Region list / locations     | `data/regions.json`                                                        |
| Sensor list                 | `data/sensors.json` (incl. `landsat_sensor`, `landsat_region_slugs`)       |
| Time windows / formats      | `data/windows_formats.json`                                                |
| Dataset description (notes) | `data/notes_template.txt`                                                  |
| Methodology blurb           | `data/methodology.txt`                                                     |
| Tags, license, IDs, base URL | `nasa_firms/config.py`                                                    |
| Resource / dataset shape    | `nasa_firms/builders.py`                                                   |
| DRY_RUN / HDX_SITE knobs    | `run.py`                                                                   |

Re-run `run.py` to push edits.

## Layout

```
run.py                      # entry point — DRY_RUN, HDX_SITE, orchestration loop
nasa_firms/
  config.py                 # IDs, tags, base URL, DATA_DIR
  models.py                 # Sensor, Region NamedTuples + JSON loaders
  builders.py               # build_resources, build_dataset
data/
  regions.json              # 13 regions × ISO3 country lists
  sensors.json              # MODIS / VIIRS / Landsat
  windows_formats.json      # 24h/48h/7d × SHP/KML/CSV
  notes_template.txt        # dataset description (markdown)
  methodology.txt           # methodology_other field
```

## See also

- `CLAUDE.md` — general HDX-API patterns, gotchas, and per-user setup notes (used by Claude Code when working in this repo).
- NASA FIRMS download page: <https://firms.modaps.eosdis.nasa.gov/active_fire/>
- File manifest used to derive the matrix: <https://firms.modaps.eosdis.nasa.gov/api/active_fire_files/all?format=json>
