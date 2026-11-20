"""Quadros do timelapse da Tailandia e a série mensal da fazenda inteira.

O MP4 é um cartão do Pasture Watch: 20 meses, de janeiro de 2025 a agosto de 2026.
O mapa em si ocupa um retângulo fixo. O contorno amarelo desse mapa, medido no
quadro de agosto de 2026 (pasto claro, linha separada da cor da biomassa),
é encaixado no perímetro dos pastos desenhados no Leaflet.
"""

from __future__ import annotations

import io
import os
import subprocess
from functools import lru_cache

import pandas as pd
from PIL import Image

_MESES = [
    (2025, 1, "Janeiro / 2025", 2.75),
    (2025, 2, "Fevereiro / 2025", 2.82),
    (2025, 3, "Março / 2025", 1.25),
    (2025, 4, "Abril / 2025", 1.18),
    (2025, 5, "Maio / 2025", 1.94),
    (2025, 6, "Junho / 2025", 0.78),
    (2025, 7, "Julho / 2025", 0.49),
    (2025, 8, "Agosto / 2025", 0.38),
    (2025, 9, "Setembro / 2025", 0.10),
    (2025, 10, "Outubro / 2025", 0.09),
    (2025, 11, "Novembro / 2025", 0.67),
    (2025, 12, "Dezembro / 2025", 1.29),
    (2026, 1, "Janeiro / 2026", 2.84),
    (2026, 2, "Fevereiro / 2026", 2.31),
    (2026, 3, "Março / 2026", 3.76),
    (2026, 4, "Abril / 2026", 2.59),
    (2026, 5, "Maio / 2026", 1.43),
    (2026, 6, "Junho / 2026", 0.88),
    (2026, 7, "Julho / 2026", 0.71),
    (2026, 8, "Agosto / 2026", 0.28),
]

# Recorte do mapa dentro do cartão, igual em todos os quadros.
_PAINEL = (76, 80, 404, 358)
# Caixa do contorno amarelo no quadro. Estes pixels, com a conta linear abaixo,
# são o encaixe que coincidia com os pastos quando a camada vinha do controle do mapa.
_LIMITE = (172, 174, 321, 288)


def arquivo_timelapse(raiz: str | None = None) -> str | None:
    pasta = raiz or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "KML"))
    if not os.path.isdir(pasta):
        return None
    for nome in os.listdir(pasta):
        if nome.lower() == "tailandia.mp4":
            return os.path.join(pasta, nome)
    return None


def bounds_painel(west: float, south: float, east: float, north: float) -> list[list[float]]:
    """Limites geográficos do recorte, a partir do contorno amarelo."""
    x1, y1, x2, y2 = _LIMITE
    esquerda, topo, direita, base = _PAINEL

    def lon(x: float) -> float:
        return west + (x - x1) / (x2 - x1) * (east - west)

    def lat(y: float) -> float:
        return north - (y - y1) / (y2 - y1) * (north - south)

    return [[lat(base), lon(esquerda)], [lat(topo), lon(direita)]]


def envelope(areas: list[dict]) -> tuple[float, float, float, float] | None:
    lons, lats = [], []
    for area in areas:
        if str(area.get("situacao") or "") == "perimetro":
            continue
        _coleta(area["geojson"], lons, lats)
    if not lons:
        return None
    return min(lons), min(lats), max(lons), max(lats)


def perimetro_pastos(areas: list[dict]) -> tuple[dict, float] | None:
    """Polígono externo da união dos pastos e a área geodésica em hectares."""
    from pyproj import Geod
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union

    partes = []
    for area in areas:
        if str(area.get("situacao") or "") == "perimetro":
            continue
        try:
            geom = shape(area["geojson"])
        except (TypeError, ValueError, KeyError):
            continue
        if geom.is_empty:
            continue
        partes.append(geom)
    if not partes:
        return None
    uniao = unary_union(partes)
    if not uniao.is_valid:
        uniao = uniao.buffer(0)
    if uniao.geom_type == "GeometryCollection":
        polys = [g for g in uniao.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
        uniao = unary_union(polys) if polys else None
    if uniao is None or uniao.is_empty:
        return None
    geod = Geod(ellps="WGS84")
    if uniao.geom_type == "Polygon":
        pedacos = [uniao]
    elif uniao.geom_type == "MultiPolygon":
        pedacos = list(uniao.geoms)
    else:
        return None
    metros = 0.0
    for pedaco in pedacos:
        area, _perimetro = geod.geometry_area_perimeter(pedaco)
        metros += abs(area)
    return mapping(uniao), round(metros / 10_000, 2)


def _coleta(geometry, lons, lats):
    tipo = geometry.get("type")
    coords = geometry.get("coordinates")
    if tipo == "Point":
        lons.append(coords[0])
        lats.append(coords[1])
    elif tipo in ("LineString", "MultiPoint"):
        for ponto in coords:
            lons.append(ponto[0])
            lats.append(ponto[1])
    elif tipo in ("Polygon", "MultiLineString"):
        for anel in coords:
            _coleta({"type": "LineString", "coordinates": anel}, lons, lats)
    elif tipo == "MultiPolygon":
        for poly in coords:
            _coleta({"type": "Polygon", "coordinates": poly}, lons, lats)


@lru_cache(maxsize=2)
def quadros_jpeg(path: str, mtime: float) -> tuple[bytes, ...]:
    del mtime
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run(
        [ffmpeg, "-v", "error", "-i", path, "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
        capture_output=True,
        check=True,
    )
    imagens = _pngs(proc.stdout)
    if len(imagens) != len(_MESES):
        raise ValueError(f"O timelapse tem {len(imagens)} quadros; o esperado são {len(_MESES)} meses.")
    saida = []
    for blob in imagens:
        imagem = Image.open(io.BytesIO(blob)).convert("RGB")
        recorte = imagem.crop(_PAINEL)
        buffer = io.BytesIO()
        recorte.save(buffer, format="JPEG", quality=72, optimize=True)
        saida.append(buffer.getvalue())
    return tuple(saida)


def _pngs(blob: bytes) -> list[bytes]:
    assinatura = b"\x89PNG\r\n\x1a\n"
    pedacos = blob.split(assinatura)
    return [assinatura + pedaco for pedaco in pedacos[1:] if pedaco]


def rebanho_mensal(conn, cod_fazenda: int) -> pd.DataFrame:
    """Cabeças e UA no dia 1º; peso = soma só dos animais com pesagem até essa data."""
    return pd.read_sql(
        """
        WITH meses AS (
            SELECT CAST('2025-01-01' AS date) AS dia
            UNION ALL
            SELECT DATEADD(month, 1, dia) FROM meses WHERE dia < '2026-08-01'
        ),
        animais AS (
            SELECT
                c.Cod_Animal,
                CAST(COALESCE(c.Dt_Entrada, c.Dt_Compra, c.Dt_Nascimento) AS date) AS entrada,
                CAST(v.Data AS date) AS venda,
                CAST(m.Data AS date) AS morte,
                ISNULL(CAST(t.Unidade_Animal AS float), 0) AS ua
            FROM cad_fichario c
            LEFT JOIN Tab_categoria t ON c.Cod_Categoria = t.Cod_Categoria
            OUTER APPLY (
                SELECT TOP 1 Data FROM Cad_Venda WHERE Cod_animal = c.Cod_Animal ORDER BY Data
            ) v
            OUTER APPLY (
                SELECT TOP 1 Data FROM Cad_Morte WHERE Cod_animal = c.Cod_Animal ORDER BY Data
            ) m
            WHERE c.Cod_Fazenda = ? AND c.Origem <> 'E'
        )
        SELECT
            mes.dia,
            COUNT(*) AS cabecas,
            SUM(a.ua) AS ua_total,
            SUM(CASE WHEN p.peso IS NULL THEN 0 ELSE 1 END) AS com_peso,
            SUM(ISNULL(p.peso, 0)) AS peso
        FROM meses mes
        JOIN animais a
          ON a.entrada <= mes.dia
         AND (a.venda IS NULL OR a.venda > mes.dia)
         AND (a.morte IS NULL OR a.morte > mes.dia)
        OUTER APPLY (
            SELECT TOP 1 Peso AS peso
            FROM cad_pesagem_corte
            WHERE cod_animal = a.Cod_Animal AND Data <= mes.dia
            ORDER BY Data DESC
        ) p
        GROUP BY mes.dia
        ORDER BY mes.dia
        OPTION (MAXRECURSION 30)
        """,
        conn,
        params=[int(cod_fazenda)],
    )


def serie_fazenda(conn, cod_fazenda: int, hectares: float) -> pd.DataFrame:
    rebanho = rebanho_mensal(conn, cod_fazenda)
    por_dia = {str(row.dia)[:10]: row for row in rebanho.itertuples(index=False)}
    linhas = []
    for ano, mes, rotulo, biomassa in _MESES:
        dia = f"{ano:04d}-{mes:02d}-01"
        info = por_dia.get(dia)
        cabecas = 0 if info is None else int(info.cabecas)
        com_peso = 0 if info is None else int(info.com_peso)
        ua_total = 0.0 if info is None else float(info.ua_total or 0)
        peso_kg = 0.0 if info is None else float(info.peso or 0)
        ms_kg = biomassa * hectares * 1000 if hectares else 0.0
        linhas.append(
            {
                "mes": rotulo,
                "mes_idx": len(linhas),
                "biomassa": biomassa,
                "cabecas": cabecas,
                "com_peso": com_peso,
                "sem_peso": cabecas - com_peso,
                "ua": round(ua_total, 2),
                "arrobas": round(peso_kg / 30.0, 1),
                "carga": None if not hectares else round(cabecas / hectares, 2),
                "ua_ha": None if not hectares else round(ua_total / hectares, 3),
                "pressao_pct": None if ms_kg <= 0 else round(peso_kg / ms_kg * 100, 1),
            }
        )
    return pd.DataFrame(linhas)
