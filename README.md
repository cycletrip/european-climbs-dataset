# European Road Cycling Climbs Dataset

Structured, openly licensed data on road-cycling climbs across Europe — length,
elevation gain, average and maximum gradient, summit elevation, difficulty
category and coordinates for every ascent side — computed by
**[CycleTrip](https://cycletrip.pro)** from digital elevation models and
OpenStreetMap road geometry.

**License:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) — free to
use, share and adapt, including commercially, with attribution (see below).

| file | what |
|---|---|
| `data/climbs.csv` | one row per **ascent side** (a climb with three roads to the top = three rows) |
| `data/climbs.geojson` | the same rows as Point features (summit) |
| `data/sides.geojson` | simplified LineString geometry per side |
| `data/manifest.json` | generation date, counts, version |

Current release: **v1.0.0** — **783** climbs / **1291** sides in **6** countries.

## Columns (`climbs.csv`)

| column | type | description |
|---|---|---|
| `climb_slug` | string | stable identifier; `https://cycletrip.pro/climbs/<slug>` |
| `climb_name` | string | name of the pass/summit (verified-or-NULL rule: never a generated name) |
| `country` | ISO-3166-1 alpha-2 | |
| `region` | string | CycleTrip region (e.g. Provence, Dolomites) |
| `side` | string | start of the ascent, e.g. `Bédoin` |
| `category` | HC / 1 / 2 / 3 / 4 | computed: `score = (avg_grade %)² × length_km`; HC ≥ 900, Cat 1 ≥ 330, Cat 2 ≥ 205, Cat 3 ≥ 70, else Cat 4 (thresholds calibrated against 159 official Grand Tour categorisations: 67 % exact, 97.5 % within one class) |
| `length_km` | float | road distance from `start` to summit |
| `elevation_gain_m` | int | positive gain along the road (DEM-sampled, smoothed) |
| `avg_grade_pct` | float | `elevation_gain / length` |
| `max_grade_pct` | float | steepest sustained segment |
| `summit_elevation_m` | int | from the hand-verified summit catalogue |
| `summit_lat`, `summit_lon` | WGS84 | summit point (hand-verified) |
| `start_lat`, `start_lon` | WGS84 | start of the side |
| `wikidata_id` | Q-id | when the pass has a Wikidata item |
| `cycletrip_url` | URL | full page with interactive profile, GPX, photos and how to get there |

## Methodology (short)

1. **Summits** come from a hand-verified catalogue (OSM `mountain_pass`/`natural=saddle`,
   Wikidata, official race parcours, plus curated famous climbs that detectors miss).
   Peaks (`natural=peak`) are naming references only and are not in this dataset.
2. **Sides** are traced along OSM roads from each valid approach to the summit;
   elevation is sampled from a DEM and smoothed before gradients are computed.
3. **Category** uses the formula above; where an official race categorisation exists
   CycleTrip displays that on the site, but this file always contains the computed value
   so that every row is comparable.
4. **Names** follow a verified-or-NULL rule — rows without a verifiable name are excluded.

Full methodology: <https://cycletrip.pro/methodology>

Every release is archived on Zenodo with a DOI.

## Attribution

Please credit **CycleTrip** and link to <https://cycletrip.pro> wherever the data is
used or displayed, for example:

> Climb data: [CycleTrip](https://cycletrip.pro), CC BY 4.0

Underlying road geometry © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) (ODbL).

## Citation

See [`CITATION.cff`](CITATION.cff) (GitHub renders a "Cite this repository" button).
A DOI is minted for every release via Zenodo.

## Updating

The dataset is regenerated from the CycleTrip database with
`scripts/export_climbs_dataset.py`; releases follow semantic versioning
(`vMAJOR.MINOR.PATCH`) and each release is archived on Zenodo.

## Contact

hello@cycletrip.pro · <https://cycletrip.pro>
