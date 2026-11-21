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