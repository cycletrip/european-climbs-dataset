#!/usr/bin/env python
"""Export the public CycleTrip climbs dataset (CC-BY 4.0).

Reads `climbs` + `climb_sides` (+ regions/countries) from the CycleTrip
Postgres/PostGIS database and writes:

  data/climbs.csv       one row per climb SIDE (approach)
  data/climbs.geojson   same rows as Point features (summit) — optional
  data/sides.geojson    LineString geometries per side, simplified — optional

Usage (from backend/ with DATABASE_URL in env, e.g. inside the backend container):

  python scripts/export_climbs_dataset.py --out ../climbs-dataset/data --top 2000
  python scripts/export_climbs_dataset.py --out ../climbs-dataset/data --top 2000 --geojson

Rules:
  * `kind='peak'` rows are naming references only — never exported.
  * Only climbs with at least one built side (climb_sides) are exported.
  * Ranking for --top: score = (avg_grade%)^2 * length_km (same formula as
    build_climb_sides.categorize), best side per climb decides the climb rank.
  * Deterministic ordering (score desc, slug, from_place) so diffs are readable.
"""
import argparse
import csv
import json
import os
import sys
from datetime import date

try:
    import psycopg2
    import psycopg2.extras
except ImportError:  # pragma: no cover
    sys.exit("pip install psycopg2-binary")

SITE = os.environ.get("SITE_BASE_URL", "https://cycletrip.pro")
CLIMB_URL = SITE + "/climbs/{slug}"          # EN climb page: frontend/app/[locale]/climbs/[slug] (PL: /pl/podjazdy/{slug})

SQL = """
WITH ranked AS (
  SELECT
    c.id            AS climb_id,
    c.slug          AS climb_slug,
    c.name          AS climb_name,
    -- countries carry country_code; 78 sides have no region row, so fall back to the climb's own code
    COALESCE(co.country_code, c.country_code) AS country,
    r.name          AS region,
    c.summit_elevation_m,
    ST_Y(c.summit_coords) AS summit_lat,
    ST_X(c.summit_coords) AS summit_lon,
    c.wikidata_id,
    s.id            AS side_id,
    s.from_place,
    ST_Y(s.start_coords) AS start_lat,
    ST_X(s.start_coords) AS start_lon,
    s.length_m,
    s.elevation_gain,
    s.avg_grade,
    s.max_grade,
    s.category,
    (POWER(s.avg_grade, 2) * s.length_m / 1000.0) AS score,
    MAX(POWER(s.avg_grade, 2) * s.length_m / 1000.0) OVER (PARTITION BY c.id) AS climb_score,
    ST_AsGeoJSON(ST_SimplifyPreserveTopology(s.geom, 0.0002)) AS geom_json
  FROM climb_sides s
  JOIN climbs c   ON c.id = s.climb_id
  LEFT JOIN regions r    ON r.id = c.region_id
  LEFT JOIN countries co ON co.id = r.country_id
  WHERE COALESCE(c.kind, '') <> 'peak'
    AND c.name IS NOT NULL
)
SELECT * FROM ranked
ORDER BY climb_score DESC, climb_slug, from_place;
"""

FIELDS = [
    "climb_slug", "climb_name", "country", "region", "side", "category",
    "length_km", "elevation_gain_m", "avg_grade_pct", "max_grade_pct",
    "summit_elevation_m", "summit_lat", "summit_lon", "start_lat", "start_lon",
    "wikidata_id", "cycletrip_url",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data")
    ap.add_argument("--top", type=int, default=2000, help="max number of climbs (all sides of each kept)")
    ap.add_argument("--geojson", action="store_true")
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL"))
    a = ap.parse_args()
    if not a.dsn:
        sys.exit("DATABASE_URL not set")

    os.makedirs(a.out, exist_ok=True)
    conn = psycopg2.connect(a.dsn)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(SQL)
    rows = cur.fetchall()

    # keep the top-N climbs (by best side), all their sides
    kept, seen = [], []
    for r in rows:
        if r["climb_id"] not in seen:
            if len(seen) >= a.top:
                continue
            seen.append(r["climb_id"])
        kept.append(r)

    def rec(r):
        return {
            "climb_slug": r["climb_slug"],
            "climb_name": r["climb_name"],
            "country": r["country"],
            "region": r["region"],
            "side": r["from_place"],
            "category": r["category"],
            "length_km": round(r["length_m"] / 1000.0, 2),
            "elevation_gain_m": r["elevation_gain"],
            "avg_grade_pct": float(r["avg_grade"]),
            "max_grade_pct": float(r["max_grade"]) if r["max_grade"] is not None else "",
            "summit_elevation_m": r["summit_elevation_m"] or "",
            "summit_lat": round(r["summit_lat"], 5),
            "summit_lon": round(r["summit_lon"], 5),
            "start_lat": round(r["start_lat"], 5),
            "start_lon": round(r["start_lon"], 5),
            "wikidata_id": r["wikidata_id"] or "",
            "cycletrip_url": CLIMB_URL.format(slug=r["climb_slug"]),
        }

    with open(os.path.join(a.out, "climbs.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in kept:
            w.writerow(rec(r))

    if a.geojson:
        pts = {"type": "FeatureCollection", "features": [
            {"type": "Feature",
             "geometry": {"type": "Point", "coordinates": [r["summit_lon"], r["summit_lat"]]},
             "properties": rec(r)} for r in kept]}
        with open(os.path.join(a.out, "climbs.geojson"), "w", encoding="utf-8") as f:
            json.dump(pts, f, ensure_ascii=False)
        lines = {"type": "FeatureCollection", "features": [
            {"type": "Feature",
             "geometry": json.loads(r["geom_json"]),
             "properties": {k: rec(r)[k] for k in ("climb_slug", "side", "category", "cycletrip_url")}}
            for r in kept]}
        with open(os.path.join(a.out, "sides.geojson"), "w", encoding="utf-8") as f:
            json.dump(lines, f, ensure_ascii=False)

    meta = {"generated": date.today().isoformat(), "climbs": len(seen), "sides": len(kept),
            "license": "CC-BY-4.0", "source": SITE}
    with open(os.path.join(a.out, "manifest.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"exported {len(seen)} climbs / {len(kept)} sides -> {a.out}")


if __name__ == "__main__":
    main()
