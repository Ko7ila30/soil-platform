-- =============================================================
-- schema.sql — Soil Observation Platform
-- Applied automatically on first Docker start (01_schema.sql).
-- All geometry stored in WGS84 (EPSG:4326).
-- =============================================================

SET client_encoding = 'UTF8';

-- PostGIS must be enabled before creating geometry columns.
-- The 01_ prefix ensures this script runs before the image's own init.
CREATE EXTENSION IF NOT EXISTS postgis;

-- -------------------------------------------------------------
-- Table: sites
-- One row per observation site (physical location on the map).
-- status: 'approved' sites are shown on the map.
--         'pending'  is reserved for optional bonus 3 (admin validation).
--         All sites created through the UI start as 'approved'.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sites (
    id         SERIAL PRIMARY KEY,
    name       TEXT    NOT NULL,
    culture    TEXT    NOT NULL,
    soil_type  TEXT    NOT NULL,

    -- geometry(Point, 4326): a single point in WGS84 lon/lat degrees.
    geom       geometry(Point, 4326) NOT NULL,

    created_at TIMESTAMP NOT NULL DEFAULT now(),

    status     TEXT NOT NULL DEFAULT 'approved'
               CHECK (status IN ('pending', 'approved'))
);

-- Spatial index speeds up bounding-box and nearest-neighbour queries.
CREATE INDEX IF NOT EXISTS idx_sites_geom ON sites USING GIST (geom);

-- -------------------------------------------------------------
-- Table: observations
-- One row per field visit by a contributor.
-- Linked to sites via site_id (CASCADE delete keeps DB consistent).
--
-- KEEP IN SYNC: the CHECK constraint values below must match
-- the lists defined in config.py (SOIL_TEXTURES, WATER_STATUSES,
-- SALINITY_LEVELS, EROSION_TYPES, IRRIGATION_MODES).
-- If you change a list value, update BOTH files.
-- -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS observations (
    id                 SERIAL PRIMARY KEY,
    site_id            INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,

    contributor_name   TEXT NOT NULL,
    observation_date   DATE NOT NULL,

    -- Controlled vocabulary fields — values must match config.py lists
    soil_texture       TEXT NOT NULL
        CHECK (soil_texture IN ('sableuse', 'limoneuse', 'argileuse', 'équilibrée')),

    water_status       TEXT NOT NULL
        CHECK (water_status IN ('sec', 'frais', 'humide', 'engorgé')),

    salinity           TEXT NOT NULL
        CHECK (salinity IN ('absente', 'traces', 'croûtes de sel visibles')),

    erosion            TEXT NOT NULL
        CHECK (erosion IN ('aucune', 'en nappe', 'rigoles', 'ravines')),

    culture            TEXT NOT NULL,

    irrigation_mode    TEXT NOT NULL
        CHECK (irrigation_mode IN ('goutte-à-goutte', 'aspersion', 'gravitaire', 'pluvial')),

    -- Optional measurements — NULL when not provided by the contributor.
    -- NUMERIC precision chosen to fit display and prevent DB errors for
    -- values the validator already checked; a friendly Python error is
    -- returned to the user instead of a raw DB constraint violation.
    ph                 NUMERIC(4,2)  CHECK (ph BETWEEN 0 AND 14),
    ec_dsm             NUMERIC(6,2)  CHECK (ec_dsm >= 0),
    organic_matter_pct NUMERIC(5,2)  CHECK (organic_matter_pct BETWEEN 0 AND 100),

    remark             TEXT,
    created_at         TIMESTAMP NOT NULL DEFAULT now()
);

-- Index for fetching all observations of a given site efficiently.
CREATE INDEX IF NOT EXISTS idx_observations_site ON observations (site_id);


-- ===== Phase 1 migration (users, zones, ownership columns) =====
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin')),
  created_at TIMESTAMP DEFAULT now()
);
CREATE TABLE IF NOT EXISTS zones (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  zone_type TEXT NOT NULL DEFAULT 'unité de sol',
  description TEXT,
  mukey TEXT, musym TEXT, source TEXT,
  geom geometry(MultiPolygon,4326) NOT NULL,
  created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMP DEFAULT now(),
  CONSTRAINT zones_valid CHECK (ST_IsValid(geom))
);
CREATE INDEX IF NOT EXISTS zones_geom_idx ON zones USING GIST (geom);
ALTER TABLE sites ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS mukey TEXT;
ALTER TABLE sites ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE observations ADD COLUMN IF NOT EXISTS created_by INTEGER REFERENCES users(id) ON DELETE SET NULL;