"""
seed_observations.py -- Generate simulated observations for the imported sites.

Run after import_geojson.py:
    python scripts/seed_observations.py

What it does:
  - Picks ~45 random sites (out of the 60 imported).
  - For each site creates 1-3 observations with:
      contributor_name = "Demo"
      observation_date = random date in the last 6 months
      all controlled vocabulary fields picked at random from valid lists
      pH 5.5-8.5, CE 0.3-6.0 dS/m, MO 0.5-4.0 %
      ~30% of observations omit the optional measurements
      remark = "Donnee simulee" (or None ~50% of the time)
      created_by = NULL (reference data)

All data is simulated. It is labelled as such in remarks and in REPORT_NOTES.md.
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import psycopg2
from config import (
    DB_SETTINGS,
    SOIL_TEXTURES,
    WATER_STATUSES,
    SALINITY_LEVELS,
    EROSION_TYPES,
    IRRIGATION_MODES,
    CULTURES,
)

random.seed(99)   # reproducible results

N_SITES_TO_USE = 45   # how many of the 60 sites get observations
MAX_OBS_PER_SITE = 3


def random_date_last_6_months():
    """Return a random date within the last 180 days."""
    days_back = random.randint(1, 180)
    return date.today() - timedelta(days=days_back)


def main():
    print("Connecting to database...")
    try:
        conn = psycopg2.connect(**DB_SETTINGS)
    except Exception as exc:
        print(f"ERROR: Could not connect: {exc}")
        sys.exit(1)

    cur = conn.cursor()

    # Fetch all site ids
    cur.execute("SELECT id FROM sites ORDER BY id")
    all_ids = [row[0] for row in cur.fetchall()]

    if not all_ids:
        print("ERROR: No sites found. Run import_geojson.py first.")
        sys.exit(1)

    # Pick a random subset
    chosen_ids = random.sample(all_ids, min(N_SITES_TO_USE, len(all_ids)))
    print(f"Creating observations for {len(chosen_ids)} sites...")

    total = 0
    for site_id in chosen_ids:
        n = random.randint(1, MAX_OBS_PER_SITE)
        for _ in range(n):
            # Optional measurements (~30% chance of omitting each)
            ph    = round(random.uniform(5.5, 8.5), 1) if random.random() > 0.3 else None
            ec    = round(random.uniform(0.3, 6.0), 2) if random.random() > 0.3 else None
            mo    = round(random.uniform(0.5, 4.0), 1) if random.random() > 0.3 else None
            # Remark present ~50% of the time
            remark = "Donnee simulee" if random.random() > 0.5 else None

            cur.execute("""
                INSERT INTO observations (
                    site_id, contributor_name, observation_date,
                    soil_texture, water_status, salinity, erosion,
                    culture, irrigation_mode,
                    ph, ec_dsm, organic_matter_pct,
                    remark, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
            """, (
                site_id,
                "Demo",
                random_date_last_6_months(),
                random.choice(SOIL_TEXTURES),
                random.choice(WATER_STATUSES),
                random.choice(SALINITY_LEVELS),
                random.choice(EROSION_TYPES),
                random.choice(CULTURES),
                random.choice(IRRIGATION_MODES),
                ph, ec, mo,
                remark,
            ))
            total += 1

    conn.commit()

    cur.execute("SELECT count(*) FROM observations")
    final = cur.fetchone()[0]
    cur.close()
    conn.close()

    print(f"  Observations inserted: {total}")
    print(f"  Total in DB:          {final}")
    print("\nAll done. Open http://localhost:5000/carte to see the data on the map.")


if __name__ == "__main__":
    main()
