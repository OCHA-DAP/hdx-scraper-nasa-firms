# HDX Python API Assistant

This repo is a workspace for using agents to drive the [`hdx-python-api`](https://hdx-python-api.readthedocs.io/) for **ad-hoc** dataset and resource operations on HDX — one-off scripts that would otherwise require a full pipeline.

## HDX environment

- **Credentials file:** `~/.hdx_configuration.yaml` — each user maintains their own with their HDX API keys:
  - `hdx_key` — prod
  - `hdx_key_stage` — stage
  - `hdx_key_dev` — feature/dev
- **`user_agent`** — pick a stable identifier per user, e.g. `HDXINTERNAL_<YourName>_AdHoc`. It shows up in audit logs.
- **Default site for ad-hoc work:** `stage` (`https://stage.data-humdata-org.ahconu.org/`)
- **Production:** `prod` (`https://data.humdata.org`) — only after a successful dry-run on stage **and** explicit confirmation from the user in the same session.

## Local setup (one-time)

From this directory:

```bash
uv venv --python 3.13
uv pip install hdx-python-api
```

Then either activate (`source .venv/bin/activate`) or call `.venv/bin/python` directly. Ad-hoc scripts go in `tmp/` (gitignored); don't commit them.

## Boilerplate

Always set `hdx_site` explicitly so the active environment is obvious from the script — don't rely on the YAML default.

```python
from hdx.api.configuration import Configuration
from hdx.data.dataset import Dataset
from hdx.data.resource import Resource

Configuration.create(
    user_agent="HDXINTERNAL_<YourName>_AdHoc",
    hdx_site="stage",        # flip to "prod" only after a stage dry-run
    hdx_read_only=False,     # set True for any inspect-only script
)
```

`Configuration.create()` can only be called once per process; restart the interpreter to switch sites.

## Read-only inspection (always safe)

```python
ds = Dataset.read_from_hdx("dataset-slug")   # None if missing on this site
if ds:
    for r in ds.get_resources():
        print(r["name"], r.get_format(), r.get("url"))
    print(ds.get_dataset_dict())              # raw CKAN metadata
```

## Looking up IDs and vocabularies

A surprising amount of stuff isn't wrapped by `hdx-python-api` and needs a raw CKAN call. Use the YAML-loaded API key directly:

```python
import os, yaml, requests
key = yaml.safe_load(open(os.path.expanduser("~/.hdx_configuration.yaml")))["hdx_key_stage"]
def ckan(action, **payload):
    r = requests.post(f"https://stage.data-humdata-org.ahconu.org/api/3/action/{action}",
                      headers={"Authorization": key}, json=payload)
    return r.json().get("result")
```

**Maintainer / your own user ID.** `User.read_from_hdx()` returns `NotAuthorized` for non-admins. Fastest workaround: list members of an org you administer — your user ID is in the result.

```python
ckan("member_list", id="<org-name>", object_type="user")
# -> [['<user-id>', 'user', 'Admin', 'admin'], ...]
```

Also useful: `ckan("organization_list_for_user", permission="create_dataset")` confirms which orgs your key can write to.

**Approved tags.** `Vocabulary.approved_tags()` returns the full list (~145 tags on stage). It's narrower than you'd expect — there's no `fire`, `wildfire`, `satellite`, or `remote sensing` tag. Always grep the vocab before guessing:

```python
from hdx.data.vocabulary import Vocabulary
[t for t in Vocabulary.approved_tags() if "hazard" in t.lower()]
```

Unknown tags are silently dropped by CKAN.

**Licenses.** Use `ckan("license_list")`. The IDs are non-obvious — for public-domain / CC0 work the ID is `other-pd-nr`, not `cc0-1.0`. Common ones:

| ID            | Use for                                                              |
| ------------- | -------------------------------------------------------------------- |
| `cc-by`       | Creative Commons Attribution                                         |
| `cc-by-igo`   | CC BY for intergovernmental orgs                                     |
| `cc-by-sa`    | CC BY-Share-Alike                                                    |
| `hdx-pddl`    | Open Data Commons PDDL                                               |
| `other-pd-nr` | Public Domain / No restrictions / **CC0** (e.g. NASA, US government) |
| `hdx-other`   | Anything else (free-text in `license_other`)                         |
| `hdx-multi`   | Multiple licenses                                                    |

## Resources (the main use case)

```python
ds = Dataset.read_from_hdx("dataset-slug")

r = Resource({"name": "indicators_2026.csv", "description": "Q1 indicators"})
r.set_file_to_upload("/path/to/indicators_2026.csv")   # filestore upload
r.set_format("CSV")
ds.add_update_resource(r)                              # matches existing by name
ds.update_in_hdx()                                     # actually write
```

- **External URL** instead of upload: pass `"url": "https://..."` in the Resource dict; do not call `set_file_to_upload`.
- **Replace**: same `name` + `add_update_resource` overwrites the existing one.
- **Delete**: `ds.delete_resource(resource)` then `ds.update_in_hdx()`.
- **Reorder**: the displayed order is whatever order you build the resource list in. Pass the full ordered list via `add_update_resources(...)` (or repeated `add_update_resource` calls) and add `match_resource_order=True` to `update_in_hdx` — without that flag, existing resources keep their stored order regardless of input order.
- **Format strings are case-sensitive**: `"CSV"`, `"XLSX"`, `"GeoJSON"`, `"Geodatabase"` (not `"GDB"`), `"SHP"`.

## Dataset metadata edits

```python
ds = Dataset.read_from_hdx("dataset-slug")
ds["title"] = "New title"
ds["notes"] = "New description..."
ds["methodology_other"] = "..."
ds["caveats"] = "..."
ds["data_update_frequency"] = 7              # days, int (-1 = "as needed", 0 = never)
ds.add_country_location("ssd")               # ISO3, lowercase; or add_other_location("world")
ds.set_time_period(start, end)               # datetime objects (NOT date — see gotchas)
ds.add_tags(["conflict", "displacement"])    # must be HDX-approved tags
ds.update_in_hdx()
```

## Dataset creation from scratch

Required fields (`dataset.check_required_fields()` enforces them): `title`, `name` (slug), `notes`, `dataset_source`, `owner_org`, `maintainer`, `methodology`, `license_id`, `private`, time period, at least one location, tags, `data_update_frequency`.

```python
from datetime import datetime, timezone

ds = Dataset({
    "name": "ad-hoc-slug-here",
    "title": "Title",
    "notes": "Description",
    "dataset_source": "Source name",
    "methodology": "Other",
    "methodology_other": "...",
    "license_id": "cc-by",
    "data_update_frequency": -1,
    "private": False,            # required; bool
    "subnational": "1",          # "1" sub-national, "0" national-only — string, not bool
})
ds.set_maintainer("<user-id>")
ds.set_organization("<org-id>")
ds.add_country_location("ssd")
ds.set_time_period(datetime(2026, 1, 1, tzinfo=timezone.utc),
                   datetime(2026, 12, 31, tzinfo=timezone.utc))
ds.add_tags(["..."])
ds.add_update_resource(r)
ds.create_in_hdx(updated_by_script="HDXINTERNAL_<YourName>_AdHoc - <task description>")
```

Pre-validate ISO3 codes against `hdx-python-country` before building — some entries are unrecognised (e.g. `xkx` Kosovo):

```python
from hdx.location.country import Country
assert Country.get_country_info_from_iso3("SSD") is not None
```

## Title and description style

**Title convention.** Sampling stage HDX shows the dominant pattern is `<Region/Country>: <Description>` (colon-space separator) with `<Country>: <Event> - <Detail> - <Date>` (space-hyphen-space) a close second for emergency datasets. Em-dashes are nearly absent. Region/country goes first as the qualifier.

**Description (notes) field is markdown**, but CKAN's renderer is strict:

- **Lists need a blank line before the first bullet.** `**Heading:**\n- item` renders as plain text; you need `**Heading:**\n\n- item`. Real HDX datasets use `\r\n\r\n-` style separation. Same applies after any paragraph that precedes a list.
- `-` and `*` bullets both work; `-` is far more common in existing HDX content.
- Standard inline markdown (`**bold**`, `[text](url)`, backticks for code) renders fine.

When generating notes, prefer building the string as a multi-line literal and printing it once before pushing — easier to spot a missing blank line than to debug "why doesn't my list render."

## Common gotchas

- `hdx_read_only=True` blocks writes only — `Dataset.read_from_hdx` still hits the live API.
- **`set_time_period` requires `datetime`, not `date`** — bare `date` objects raise `TypeError: replace() takes at most 3 keyword arguments`. Use `datetime(..., tzinfo=timezone.utc)` or an ISO string.
- **`"private"` is a required field** on creation. `check_required_fields()` fails with `Field private is missing`. Set `"private": False` (or True) explicitly in the Dataset dict.
- `data_update_frequency` is **days as int**, not a cron string: `7` weekly, `1` daily, `-1` "as needed", `0` never.
- `subnational` and `p_coded` are the strings `"1"`/`"0"` and `"True"`/`"False"`, not Python bools.
- Filestore uploads require a real on-disk path; presigned/remote URLs aren't supported by `set_file_to_upload`.
- `update_in_hdx(remove_additional_resources=True)` **deletes** any resource not in the current list — leave it `False` for additive ad-hoc edits.
- Stage and prod are separate databases. A slug that exists on prod may not exist on stage; copy the dataset over first if you need to dry-run.
- `Configuration.create()` is one-shot per process — to switch sites, exit and re-run the script.
- Tags are validated against the HDX-approved vocabulary; unknown tags are silently dropped or rejected by CKAN. There's no `fire`/`wildfire`/`satellite` tag — see _Looking up IDs and vocabularies_ above.

## How to help

- **Default to `stage`.** Before any `prod` write (`create_in_hdx` / `update_in_hdx` / `delete_resource` against `hdx_site="prod"`), confirm with the user in-session — even if they asked for a prod operation earlier, ask again before each write.
- **Dry-run first.** First run of any new script: `hdx_read_only=True`, print what _would_ change, then flip to `False`.
- **Make scripts idempotent** — branch on `Dataset.read_from_hdx(slug)` returning `None` (CREATE) vs an existing dataset (UPDATE). The same script then doubles as the maintenance/sync script.
- **Print the dataset URL after every write** so the user can spot-check in the browser. Use `https://stage.data-humdata-org.ahconu.org/dataset/<slug>` for stage, `https://data.humdata.org/dataset/<slug>` for prod.
- **Never invent a dataset slug.** Ask the user for the exact slug or list candidates via `Dataset.search_in_hdx("...")`.
- **Ad-hoc scripts live in `tmp/`.** Don't create top-level `.py` files; don't commit anything in `tmp/`.
- **Existing pipelines for reference patterns:** the OCHA-DAP GitHub org has good examples — `dpt-internal-scripts`, `hdx-scraper-cod-ab-country`, `hdx-scraper-cod-ab-global`.
