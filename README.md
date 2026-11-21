
# Participative Soil Observation Platform
### Plateforme participative d'observation des sols — Chott Mariem, Sousse

> **All data is simulated.** No real field measurements or verified coordinates
> are represented. Map tiles and Leaflet require an internet connection.

---

<img width="5208" height="4922" alt="diagram" src="https://github.com/user-attachments/assets/317fb037-21ee-4534-a389-ba2dd7f61d07" />

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Browser                                                │
│  Leaflet 1.9.4 (CDN) + vanilla JS + HTML/CSS           │
│  map.js: map, markers, popups, add-site mode            │
│  forms.js: observation form, add-site form              │
└───────────────────┬─────────────────────────────────────┘
                    │  HTTP JSON / GeoJSON
                    │  (localhost:5000)
┌───────────────────▼─────────────────────────────────────┐
│  Flask app  (host, Python 3.15 64-bit, .venv)           │
│  app.py       — routes, serialisation                   │
│  config.py    — all constants (single source of truth)  │
│  db.py        — psycopg2 connection helper              │
│  validators.py — pure validation functions              │
└───────────────────┬─────────────────────────────────────┘
                    │  psycopg2 TCP (localhost:5433)
┌───────────────────▼─────────────────────────────────────┐
│  PostGIS 16-3.4  (Docker container "soil_platform_db")  │
│  table: sites        — geometry + attributes            │
│  table: observations — linked field records             │
│  Named Docker volume — data persists across restarts    │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Docker Desktop** (running) — [docs.docker.com](https://docs.docker.com/desktop/)
- **Python 3.15.2 64-bit** at `C:\Users\adame\AppData\Local\Programs\Python\Python315\python.exe`
- **Internet connection** (for OSM map tiles and Leaflet CDN on first load)
- The virtual environment `.venv` must already exist (see Setup step 2)

---

## Setup and run (PowerShell)

### Step 1 — Start the database

```powershell
cd C:\Users\adame\Desktop\Soil_Platform\soil-platform

# Start PostGIS in Docker (creates tables and seed data on first run)
docker compose up -d

# Wait ~15 seconds, then verify the container is healthy
docker compose ps

# Verify PostGIS and seed data
docker compose exec db psql -U soil_user -d soil_platform -c "SELECT PostGIS_Version();"
docker compose exec db psql -U soil_user -d soil_platform -c "SELECT count(*) FROM sites;"
```

Expected: `count` = 18.

### Step 2 — Activate the virtual environment

```powershell
# If activation is blocked by execution policy, fix for this session only:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Activate
.\.venv\Scripts\Activate.ps1
```

The prompt should change to show `(.venv)`.

### Step 3 — Install Python dependencies

```powershell
pip install -r requirements.txt
```

### Step 4 — Run the Flask app

```powershell
python app.py
```

Open your browser at: **http://127.0.0.1:5000**

---

## Run the tests

```powershell
# From soil-platform/ with the venv activated:

# Unit tests (no Docker required)
python -m pytest tests/test_validators.py -v

# API tests (Docker must be running)
python -m pytest tests/test_api.py -v

# All tests
python -m pytest -v
```

If Docker is not running, `test_api.py` tests are **skipped** (not failed) with
a clear message.

---

## Export sites to GeoJSON

```powershell
# With venv activated and Docker running:
python scripts/export_geojson.py
```

Output: `data/sites.geojson`

---

## API reference

| Method | Endpoint | Purpose | Response |
|--------|----------|---------|----------|
| GET | `/` | Map page | 200 HTML |
| GET | `/api/sites` | All approved sites (GeoJSON FeatureCollection) | 200 |
| GET | `/api/sites/<id>` | One site (GeoJSON Feature) | 200 / 404 |
| GET | `/api/options` | All dropdown lists + site list | 200 |
| GET | `/api/sites/<id>/observations` | Observations for a site (newest first) | 200 / 404 |
| POST | `/api/sites/<id>/observations` | Create an observation | 201 / 400 / 404 |
| POST | `/api/sites` | Create a new site | 201 / 400 |

**Error response shape (always JSON):**
```json
{
  "error": "Veuillez vérifier les champs du formulaire.",
  "errors": { "ph": "Le pH doit être compris entre 0 et 14." }
}
```

---

## Reset the database

> ⚠️ This destroys ALL data, including every site and observation you have added.
> Only do this if you need a clean start. Ask before running in an academic context.

```powershell
docker compose down -v     # deletes the named volume (ALL data gone)
docker compose up -d       # recreates the container and re-applies schema + seed
```

---

## Troubleshooting

### Docker is not running
Start Docker Desktop and wait until the whale icon in the taskbar is steady
(not animating). Then run `docker compose up -d`.

### Port 5433 is already in use
Edit `docker-compose.yml`: change `"5433:5432"` to `"5434:5432"` (or any free port).
Also change `POSTGRES_PORT=5433` to `5434` in `.env`. Restart Docker.

### Tables are missing after `docker compose up -d`
The init scripts only run on the **first** start with an empty volume.
Check the logs: `docker compose logs db`.
If the volume was not empty, you need to reset (see above — data will be lost).

### Accented characters look wrong in the terminal
This is a Windows console code page issue. The browser is the real test.
Check the page — if accents display correctly there, the data is fine.
To fix the terminal: `chcp 65001` (sets console to UTF-8).

### Flask cannot connect to the database
1. Check `.env` — `POSTGRES_HOST` must be `localhost`, `POSTGRES_PORT` must
   match the host port in `docker-compose.yml` (default: 5433).
2. Run `docker compose ps` — the `db` service must show `healthy`.
3. Run `docker compose logs db` — look for errors.

### venv activation blocked
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```
This only affects the current PowerShell session.

### Map tiles or Leaflet not loading
You need an internet connection. The map tiles come from OpenStreetMap's CDN;
Leaflet 1.9.4 is loaded from unpkg.com.

### Longitude / latitude swapped
If sites appear in the wrong location, the coordinate order in
`ST_MakePoint` is wrong. It must always be `ST_MakePoint(longitude, latitude)`.
The coordinate-order test in `test_api.py` catches this.
