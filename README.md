# hdx-scraper-nasa-firms

Maintains the [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/active_fire/) datasets on HDX. Each HDX dataset is one NASA FIRMS region × sensor family with **external-URL resources pointing directly at NASA-hosted files** — there is no local data fetching, no transformation, and no upload. Files refresh on NASA's side (typically every 3 hours); HDX always serves the latest.

## What it creates

28 datasets under [`organization/nasa-firms`](https://data.humdata.org/organization/nasa-firms), one per (region × sensor family) pair. The 13 regions are:

```
Global, Canada, Alaska, USA (Contiguous & Hawaii), Central America & Caribbean,
South America, Europe, Northern and Central Africa, Southern Africa,
Russia and Asia, South Asia, Southeast Asia, Australia and New Zealand
```

Each region produces a MODIS dataset and a VIIRS dataset; Canada and USA (Contiguous & Hawaii) additionally produce a Landsat dataset. Resource counts:

| Family  | Sensors                                  | Resources / dataset |
| ------- | ---------------------------------------- | ------------------- |
| MODIS   | MODIS C6.1                               | 9 (1 × 3 × 3)       |
| VIIRS   | S-NPP, NOAA-20, NOAA-21                  | 27 (3 × 3 × 3)      |
| Landsat | Landsat 8/9 OLI (Canada + USA only)      | 9 (KML uses animated_48h instead of 7d) |

Resource ordering on HDX mirrors the FIRMS download page (Shapefile → KML → CSV; within VIIRS: S-NPP → NOAA-20 → NOAA-21; 24h → 48h → 7d).

## Usage

Prereq: an `~/.hdx_configuration.yaml` with `hdx_key_stage` (and `hdx_key` for prod). See `CLAUDE.md` for the full HDX-API setup.

```bash
uv sync                  # creates .venv and installs from uv.lock

# Dry run (default — does not write):
uv run run.py

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

| What                          | Edit                                                                       |
| ----------------------------- | -------------------------------------------------------------------------- |
| Region list / locations       | `data/regions.json`                                                        |
| Sensor families / `since` lines / Landsat region carve-out | `data/sensors.json` (the `families` list)            |
| Time windows / formats        | `data/windows_formats.json`                                                |
| Dataset description (notes)   | `data/notes_template.txt`                                                  |
| Methodology (per family)      | `data/methodology_modis.txt`, `methodology_viirs.txt`, `methodology_landsat.txt` |
| Caveats (coverage note)       | `data/caveats.txt`                                                         |
| Tags, license, IDs, base URL  | `nasa_firms/config.py`                                                     |
| Resource / dataset shape      | `nasa_firms/builders.py`                                                   |
| DRY_RUN / HDX_SITE knobs      | `run.py`                                                                   |

Re-run `run.py` to push edits.

## Layout

```
run.py                      # entry point — DRY_RUN, HDX_SITE, orchestration loop
nasa_firms/
  config.py                 # IDs, tags, base URL, DATA_DIR
  models.py                 # Sensor, Region, Family NamedTuples + JSON loaders
  builders.py               # build_resources, build_dataset (per region × family)
data/
  regions.json              # 13 regions × ISO3 country lists
  sensors.json              # families: MODIS / VIIRS / Landsat
  windows_formats.json      # 24h/48h/7d × SHP/KML/CSV
  notes_template.txt        # dataset description (markdown)
  methodology_<family>.txt  # methodology_other field, one per sensor family
  caveats.txt               # caveats field (coverage / bbox note)
```

## See also

- `CLAUDE.md` — general HDX-API patterns, gotchas, and per-user setup notes (used by Claude Code when working in this repo).
- NASA FIRMS download page: <https://firms.modaps.eosdis.nasa.gov/active_fire/>
- File manifest used to derive the matrix: <https://firms.modaps.eosdis.nasa.gov/api/active_fire_files/all?format=json>
