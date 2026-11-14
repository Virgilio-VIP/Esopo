-- Catálogo geográfico do Esopo.
-- Use quando PG_HOST / PG_PASSWORD estiverem no .env.
-- O vínculo com o rebanho continua em Vipper_FRS.Tab_local.id_geo_area.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS geo_area (
    id           SERIAL PRIMARY KEY,
    cod_fazenda  INTEGER NOT NULL,
    arquivo      TEXT,
    seq          INTEGER NOT NULL,
    area_ha      DOUBLE PRECISION,
    situacao     TEXT,
    geojson      TEXT NOT NULL,
    geom         geometry(Polygon, 4326),
    criado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS geo_area_fazenda_idx ON geo_area (cod_fazenda);
CREATE INDEX IF NOT EXISTS geo_area_geom_idx ON geo_area USING GIST (geom);

CREATE TABLE IF NOT EXISTS geo_linha (
    id           SERIAL PRIMARY KEY,
    cod_fazenda  INTEGER NOT NULL,
    arquivo      TEXT,
    nome         TEXT,
    dangling     BOOLEAN NOT NULL DEFAULT FALSE,
    geojson      TEXT NOT NULL,
    geom         geometry(LineString, 4326),
    criado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS geo_linha_fazenda_idx ON geo_linha (cod_fazenda);
CREATE INDEX IF NOT EXISTS geo_linha_geom_idx ON geo_linha USING GIST (geom);
