"""Persiste áreas do KML.

PostGIS é o destino quando PG_PASSWORD está preenchido.
Sem essa senha, as geometrias ficam em Vipper_FRS (Esopo_geo_area / Esopo_geo_linha),
que é o banco já conectado. Tab_local.id_geo_area aponta para o id da área.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

_AREA_DDL = """
IF OBJECT_ID('Esopo_geo_area', 'U') IS NULL
CREATE TABLE Esopo_geo_area (
    id           INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    cod_fazenda  INT NOT NULL,
    arquivo      NVARCHAR(260) NULL,
    seq          INT NOT NULL,
    area_ha      FLOAT NULL,
    situacao     NVARCHAR(20) NULL,
    geojson      NVARCHAR(MAX) NOT NULL,
    criado_em    DATETIME NOT NULL CONSTRAINT DF_Esopo_geo_area_criado DEFAULT GETDATE()
);
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'IX_Esopo_geo_area_fazenda' AND object_id = OBJECT_ID('Esopo_geo_area')
)
CREATE INDEX IX_Esopo_geo_area_fazenda ON Esopo_geo_area (cod_fazenda);
"""

_LINE_DDL = """
IF OBJECT_ID('Esopo_geo_linha', 'U') IS NULL
CREATE TABLE Esopo_geo_linha (
    id           INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
    cod_fazenda  INT NOT NULL,
    arquivo      NVARCHAR(260) NULL,
    nome         NVARCHAR(80) NULL,
    dangling     BIT NOT NULL CONSTRAINT DF_Esopo_geo_linha_dangling DEFAULT 0,
    geojson      NVARCHAR(MAX) NOT NULL,
    criado_em    DATETIME NOT NULL CONSTRAINT DF_Esopo_geo_linha_criado DEFAULT GETDATE()
);
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes WHERE name = 'IX_Esopo_geo_linha_fazenda' AND object_id = OBJECT_ID('Esopo_geo_linha')
)
CREATE INDEX IX_Esopo_geo_linha_fazenda ON Esopo_geo_linha (cod_fazenda);
"""


@dataclass
class StoreInfo:
    backend: str
    label: str
    warning: str | None = None


class SqlServerStore:
    backend = "sqlserver"

    def __init__(self, conn):
        self.conn = conn
        self.label = "SQL Server · Vipper_FRS.Esopo_geo_area"
        cur = conn.cursor()
        cur.execute(_AREA_DDL)
        cur.execute(_LINE_DDL)
        cur.execute("SELECT COL_LENGTH('Tab_local', 'id_geo_area')")
        if cur.fetchone()[0] is None:
            cur.execute("ALTER TABLE Tab_local ADD id_geo_area INT NULL")
        conn.commit()

    def areas(self, cod_fazenda: int) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, seq, area_ha, situacao, geojson
            FROM Esopo_geo_area
            WHERE cod_fazenda = ?
              AND ISNULL(situacao, '') <> 'excluida'
            ORDER BY seq
            """,
            int(cod_fazenda),
        )
        cols = [c[0] for c in cur.description]
        return [_row(cols, row) for row in cur.fetchall()]

    def lines(self, cod_fazenda: int) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, nome, dangling, geojson
            FROM Esopo_geo_linha
            WHERE cod_fazenda = ?
            """,
            int(cod_fazenda),
        )
        cols = [c[0] for c in cur.description]
        rows = []
        for row in cur.fetchall():
            item = _row(cols, row)
            item["dangling"] = bool(item["dangling"])
            rows.append(item)
        return rows

    def replace(self, cod_fazenda: int, arquivo: str, polygons: list[dict], lines: list[dict]) -> dict[int, int]:
        cod = int(cod_fazenda)
        cur = self.conn.cursor()
        cur.execute("DELETE FROM Esopo_geo_linha WHERE cod_fazenda = ?", cod)
        cur.execute("DELETE FROM Esopo_geo_area WHERE cod_fazenda = ?", cod)
        seq_to_id: dict[int, int] = {}
        for poly in polygons:
            cur.execute(
                """
                INSERT INTO Esopo_geo_area (cod_fazenda, arquivo, seq, area_ha, situacao, geojson)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                cod,
                arquivo[:260],
                int(poly["seq"]),
                float(poly["area_ha"]),
                poly.get("situacao"),
                json.dumps(poly["geojson"], ensure_ascii=False),
            )
            seq_to_id[int(poly["seq"])] = int(cur.fetchone()[0])
        for line in lines:
            cur.execute(
                """
                INSERT INTO Esopo_geo_linha (cod_fazenda, arquivo, nome, dangling, geojson)
                VALUES (?, ?, ?, ?, ?)
                """,
                cod,
                arquivo[:260],
                (line.get("nome") or "")[:80],
                1 if line.get("dangling") else 0,
                json.dumps(line["geojson"], ensure_ascii=False),
            )
        self.conn.commit()
        return seq_to_id

    def replace_unlinked(self, cod_fazenda: int, arquivo: str, polygons: list[dict], lines: list[dict], keep_ids: list[int]) -> dict[int, int]:
        """Troca só as áreas sem vínculo. `keep_ids` são as já ligadas a Tab_local e não são apagadas."""
        cod = int(cod_fazenda)
        keep = [int(i) for i in keep_ids]
        cur = self.conn.cursor()
        cur.execute("DELETE FROM Esopo_geo_linha WHERE cod_fazenda = ?", cod)
        if keep:
            marks = ",".join("?" for _ in keep)
            cur.execute(
                f"DELETE FROM Esopo_geo_area WHERE cod_fazenda = ? AND id NOT IN ({marks})",
                [cod, *keep],
            )
        else:
            cur.execute("DELETE FROM Esopo_geo_area WHERE cod_fazenda = ?", cod)
        seq_to_id = self._insert_areas_and_lines(cur, cod, arquivo, polygons, lines)
        self.conn.commit()
        return seq_to_id

    def _insert_areas_and_lines(self, cur, cod, arquivo, polygons, lines) -> dict[int, int]:
        seq_to_id: dict[int, int] = {}
        for poly in polygons:
            cur.execute(
                """
                INSERT INTO Esopo_geo_area (cod_fazenda, arquivo, seq, area_ha, situacao, geojson)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                cod,
                (arquivo or "")[:260],
                int(poly["seq"]),
                float(poly["area_ha"]),
                poly.get("situacao"),
                json.dumps(poly["geojson"], ensure_ascii=False),
            )
            seq_to_id[int(poly["seq"])] = int(cur.fetchone()[0])
        for line in lines:
            cur.execute(
                """
                INSERT INTO Esopo_geo_linha (cod_fazenda, arquivo, nome, dangling, geojson)
                VALUES (?, ?, ?, ?, ?)
                """,
                cod,
                (arquivo or "")[:260],
                (line.get("nome") or "")[:80],
                1 if line.get("dangling") else 0,
                json.dumps(line["geojson"], ensure_ascii=False),
            )
        return seq_to_id

    def excluidas(self, cod_fazenda: int) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, seq, area_ha, situacao, geojson
            FROM Esopo_geo_area
            WHERE cod_fazenda = ? AND situacao = 'excluida'
            """,
            int(cod_fazenda),
        )
        cols = [c[0] for c in cur.description]
        return [_row(cols, row) for row in cur.fetchall()]

    def apagar_excluidas(self, cod_fazenda: int):
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM Esopo_geo_area WHERE cod_fazenda = ? AND situacao = 'excluida'",
            int(cod_fazenda),
        )
        self.conn.commit()


class PostgisStore:
    backend = "postgis"

    def __init__(self, conn):
        self.conn = conn
        self.label = f"PostGIS · {os.getenv('PG_DATABASE', 'esopo_gis')}.geo_area"
        self._ensure()

    def _ensure(self):
        cur = self.conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS geo_area (
                id SERIAL PRIMARY KEY,
                cod_fazenda INTEGER NOT NULL,
                arquivo TEXT,
                seq INTEGER NOT NULL,
                area_ha DOUBLE PRECISION,
                situacao TEXT,
                geojson TEXT NOT NULL,
                geom geometry(Polygon, 4326),
                criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS geo_linha (
                id SERIAL PRIMARY KEY,
                cod_fazenda INTEGER NOT NULL,
                arquivo TEXT,
                nome TEXT,
                dangling BOOLEAN NOT NULL DEFAULT FALSE,
                geojson TEXT NOT NULL,
                geom geometry(LineString, 4326),
                criado_em TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        self.conn.commit()

    def areas(self, cod_fazenda: int) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, seq, area_ha, situacao, geojson
            FROM geo_area
            WHERE cod_fazenda = %s
              AND COALESCE(situacao, '') <> 'excluida'
            ORDER BY seq
            """,
            (int(cod_fazenda),),
        )
        cols = [c[0] for c in cur.description]
        return [_row(cols, row) for row in cur.fetchall()]

    def lines(self, cod_fazenda: int) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, nome, dangling, geojson
            FROM geo_linha WHERE cod_fazenda = %s
            """,
            (int(cod_fazenda),),
        )
        cols = [c[0] for c in cur.description]
        return [_row(cols, row) for row in cur.fetchall()]

    def replace(self, cod_fazenda: int, arquivo: str, polygons: list[dict], lines: list[dict]) -> dict[int, int]:
        cod = int(cod_fazenda)
        cur = self.conn.cursor()
        cur.execute("DELETE FROM geo_linha WHERE cod_fazenda = %s", (cod,))
        cur.execute("DELETE FROM geo_area WHERE cod_fazenda = %s", (cod,))
        seq_to_id: dict[int, int] = {}
        for poly in polygons:
            payload = json.dumps(poly["geojson"], ensure_ascii=False)
            cur.execute(
                """
                INSERT INTO geo_area (cod_fazenda, arquivo, seq, area_ha, situacao, geojson, geom)
                VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
                RETURNING id
                """,
                (cod, arquivo, int(poly["seq"]), float(poly["area_ha"]), poly.get("situacao"), payload, payload),
            )
            seq_to_id[int(poly["seq"])] = int(cur.fetchone()[0])
        for line in lines:
            payload = json.dumps(line["geojson"], ensure_ascii=False)
            cur.execute(
                """
                INSERT INTO geo_linha (cod_fazenda, arquivo, nome, dangling, geojson, geom)
                VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
                """,
                (
                    cod,
                    arquivo,
                    line.get("nome"),
                    bool(line.get("dangling")),
                    payload,
                    payload,
                ),
            )
        self.conn.commit()
        return seq_to_id

    def replace_unlinked(self, cod_fazenda: int, arquivo: str, polygons: list[dict], lines: list[dict], keep_ids: list[int]) -> dict[int, int]:
        cod = int(cod_fazenda)
        keep = [int(i) for i in keep_ids]
        cur = self.conn.cursor()
        cur.execute("DELETE FROM geo_linha WHERE cod_fazenda = %s", (cod,))
        if keep:
            cur.execute(
                "DELETE FROM geo_area WHERE cod_fazenda = %s AND NOT (id = ANY(%s))",
                (cod, keep),
            )
        else:
            cur.execute("DELETE FROM geo_area WHERE cod_fazenda = %s", (cod,))
        seq_to_id: dict[int, int] = {}
        for poly in polygons:
            payload = json.dumps(poly["geojson"], ensure_ascii=False)
            cur.execute(
                """
                INSERT INTO geo_area (cod_fazenda, arquivo, seq, area_ha, situacao, geojson, geom)
                VALUES (%s, %s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
                RETURNING id
                """,
                (cod, arquivo, int(poly["seq"]), float(poly["area_ha"]), poly.get("situacao"), payload, payload),
            )
            seq_to_id[int(poly["seq"])] = int(cur.fetchone()[0])
        for line in lines:
            payload = json.dumps(line["geojson"], ensure_ascii=False)
            cur.execute(
                """
                INSERT INTO geo_linha (cod_fazenda, arquivo, nome, dangling, geojson, geom)
                VALUES (%s, %s, %s, %s, %s, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))
                """,
                (cod, arquivo, line.get("nome"), bool(line.get("dangling")), payload, payload),
            )
        self.conn.commit()
        return seq_to_id

    def excluidas(self, cod_fazenda: int) -> list[dict]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT id, seq, area_ha, situacao, geojson
            FROM geo_area
            WHERE cod_fazenda = %s AND situacao = 'excluida'
            """,
            (int(cod_fazenda),),
        )
        cols = [c[0] for c in cur.description]
        return [_row(cols, row) for row in cur.fetchall()]

    def apagar_excluidas(self, cod_fazenda: int):
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM geo_area WHERE cod_fazenda = %s AND situacao = 'excluida'",
            (int(cod_fazenda),),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


def _row(cols, row) -> dict:
    item = dict(zip(cols, row))
    if isinstance(item.get("geojson"), str):
        item["geojson"] = json.loads(item["geojson"])
    return item


def _postgis_connection():
    import psycopg2

    host = os.getenv("PG_HOST", "localhost")
    port = int(os.getenv("PG_PORT", "5432"))
    user = os.getenv("PG_USER", "postgres")
    password = os.getenv("PG_PASSWORD", "")
    database = os.getenv("PG_DATABASE", "esopo_gis")
    admin = psycopg2.connect(host=host, port=port, user=user, password=password, dbname="postgres")
    admin.autocommit = True
    cur = admin.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
    if cur.fetchone() is None:
        cur.execute(f'CREATE DATABASE "{database}"')
    admin.close()
    return psycopg2.connect(host=host, port=port, user=user, password=password, dbname=database)


def open_store(sql_conn) -> tuple[SqlServerStore | PostgisStore, StoreInfo]:
    password = (os.getenv("PG_PASSWORD") or "").strip()
    if password:
        try:
            store = PostgisStore(_postgis_connection())
            _ensure_sql_link(sql_conn)
            return store, StoreInfo("postgis", store.label)
        except Exception as exc:
            store = SqlServerStore(sql_conn)
            return store, StoreInfo(
                "sqlserver",
                store.label,
                f"PostGIS não abriu ({exc}). As geometrias foram para o SQL Server.",
            )
    store = SqlServerStore(sql_conn)
    return store, StoreInfo(
        "sqlserver",
        store.label,
        "PostGIS local está instalado, mas PG_PASSWORD está vazio. As áreas ficam em Vipper_FRS até você informar a senha no .env.",
    )


def _ensure_sql_link(sql_conn):
    cur = sql_conn.cursor()
    cur.execute("SELECT COL_LENGTH('Tab_local', 'id_geo_area')")
    if cur.fetchone()[0] is None:
        cur.execute("ALTER TABLE Tab_local ADD id_geo_area INT NULL")
        sql_conn.commit()


def vincular(sql_conn, cod_fazenda: int, pairs: list[tuple[str, int]]):
    """Grava vínculos novos sem mexer nos locais que não estão na lista."""
    cur = sql_conn.cursor()
    for cod_local, geo_id in pairs:
        cur.execute(
            """
            UPDATE Tab_local
            SET id_geo_area = ?
            WHERE Cod_Fazenda = ? AND Cod_Local = ?
            """,
            int(geo_id),
            int(cod_fazenda),
            cod_local,
        )
    sql_conn.commit()


def desvincular(sql_conn, cod_fazenda: int, cod_local: str):
    cur = sql_conn.cursor()
    cur.execute(
        """
        UPDATE Tab_local
        SET id_geo_area = NULL
        WHERE Cod_Fazenda = ? AND Cod_Local = ?
        """,
        int(cod_fazenda),
        cod_local,
    )
    sql_conn.commit()
