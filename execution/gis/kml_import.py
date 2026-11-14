"""Lê um KML de cercas (GPS TrackMaker) e fecha os pastos que a malha permite."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from pyproj import Geod, Transformer
from shapely.geometry import LineString, Point, Polygon, mapping
from shapely.ops import polygonize, polygonize_full, unary_union
from shapely.strtree import STRtree
from shapely import node

_GEOD = Geod(ellps="WGS84")
_TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:32723", always_xy=True)
_TO_WGS = Transformer.from_crs("EPSG:32723", "EPSG:4326", always_xy=True)


@dataclass
class KmlImport:
    polygons: list[dict] = field(default_factory=list)
    lines: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def _ns(root: ET.Element) -> str:
    if root.tag.startswith("{"):
        return root.tag[1:].split("}", 1)[0]
    return "http://www.opengis.net/kml/2.2"


def _coords(text: str) -> list[tuple[float, float]]:
    points = []
    for token in (text or "").replace("\n", " ").split():
        parts = token.split(",")
        if len(parts) >= 2:
            points.append((float(parts[0]), float(parts[1])))
    return points


def _project(line: LineString, transformer: Transformer) -> LineString:
    return LineString([transformer.transform(x, y) for x, y in line.coords])


def _explode(geom) -> list:
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        return [geom]
    if geom.geom_type in ("MultiLineString", "GeometryCollection"):
        parts = []
        for piece in geom.geoms:
            parts.extend(_explode(piece))
        return parts
    return []


def _area_ha(poly) -> float:
    def ring_area(ring) -> float:
        area, _ = _GEOD.polygon_area_perimeter(list(ring.xy[0]), list(ring.xy[1]))
        return abs(area)

    total = ring_area(poly.exterior)
    for hole in poly.interiors:
        total -= ring_area(hole)
    return total / 10000.0


def _situacao(area_ha: float) -> str:
    if area_ha < 12:
        return "pequena"
    if area_ha > 90:
        return "uniao"
    return "ok"


def _snap_and_split(lines: list[LineString], tolerance_m: float) -> list[LineString]:
    """Encosta pontas soltas na cerca mais próxima e corta a cerca nesse ponto."""
    tree = STRtree(lines)
    splits: dict[int, set[float]] = {i: set() for i in range(len(lines))}
    moved: list[list[tuple[float, float]]] = []

    for i, line in enumerate(lines):
        coords = list(line.coords)
        for idx in (0, -1):
            point = Point(coords[idx])
            best = None
            best_dist = tolerance_m
            best_j = None
            best_along = None
            for j in tree.query(point.buffer(tolerance_m)):
                j = int(j)
                if j == i:
                    continue
                other = lines[j]
                along = other.project(point)
                projected = other.interpolate(along)
                dist = point.distance(projected)
                if 0.05 < dist <= best_dist:
                    best_dist = dist
                    best = projected
                    best_j = j
                    best_along = along
            if best is not None:
                coords[idx] = (best.x, best.y)
                splits[best_j].add(round(best_along, 2))
        moved.append(coords)

    rebuilt = []
    for i, line in enumerate(lines):
        extras = sorted(splits[i])
        if not extras:
            coords = moved[i]
            if len(coords) >= 2:
                rebuilt.append(LineString(coords))
            continue

        marked = [(0.0, moved[i][0])]
        walked = 0.0
        pts = list(line.coords)
        for a, b in zip(pts[:-1], pts[1:]):
            seg_len = Point(a).distance(Point(b))
            nxt = walked + seg_len
            for along in extras:
                if walked + 0.05 < along < nxt - 0.05:
                    marked.append((along, line.interpolate(along).coords[0]))
            walked = nxt
            marked.append((walked, b))
        marked[-1] = (marked[-1][0], moved[i][-1])
        marked.sort(key=lambda item: item[0])
        clean = [marked[0][1]]
        for _, xy in marked[1:]:
            if Point(clean[-1]).distance(Point(xy)) > 0.05:
                clean.append(xy)
        if len(clean) >= 2:
            rebuilt.append(LineString(clean))
    return rebuilt


def _anel(texto: str) -> list[tuple[float, float]]:
    pts = _coords(texto)
    if len(pts) >= 3 and pts[0] != pts[-1]:
        pts.append(pts[0])
    return pts


def _poligonos_do_ponto(placemark, ns: dict) -> list[Polygon]:
    saida: list[Polygon] = []
    for elemento in placemark.findall(".//k:Polygon", ns):
        externo = elemento.find(".//k:outerBoundaryIs//k:coordinates", ns)
        if externo is None or not (externo.text or "").strip():
            continue
        casca = _anel(externo.text or "")
        if len(casca) < 4:
            continue
        furos = []
        for interno in elemento.findall(".//k:innerBoundaryIs//k:coordinates", ns):
            buraco = _anel(interno.text or "")
            if len(buraco) >= 4:
                furos.append(buraco)
        geom = Polygon(casca, furos)
        if not geom.is_valid:
            geom = geom.buffer(0)
        if geom.is_empty:
            continue
        pedacos = [geom] if geom.geom_type == "Polygon" else list(getattr(geom, "geoms", []))
        for pedaco in pedacos:
            if pedaco.geom_type == "Polygon" and not pedaco.is_empty:
                saida.append(pedaco)
    return saida


def _registro_poligono(nome: str, poly: Polygon, seq: int) -> dict:
    area = _area_ha(poly)
    ponto = poly.representative_point()
    return {
        "seq": seq,
        "area_ha": round(area, 2),
        "situacao": "ok",
        "geojson": mapping(poly),
        "centro": [round(ponto.x, 6), round(ponto.y, 6)],
        "travada": False,
        "nome_kml": nome,
    }


def polygons_from_placemarks(named: list[tuple[str, Polygon]]) -> KmlImport:
    polygons = [_registro_poligono(nome, poly, seq) for seq, (nome, poly) in enumerate(named, start=1)]
    return KmlImport(
        lines=[],
        polygons=polygons,
        stats={
            "origem": "poligono",
            "cercas": 0,
            "poligonos": len(polygons),
            "descartados": 0,
            "vao_m": 0.0,
            "snap_m": 0.0,
            "nomes": [nome for nome, _poly in named],
        },
    )


def parse_kml(payload: bytes | str, snap_m: float = 15.0) -> KmlImport:
    if isinstance(payload, str):
        root = ET.fromstring(payload)
    else:
        root = ET.fromstring(payload)
    ns = {"k": _ns(root)}

    poligonos: list[tuple[str, Polygon]] = []
    linhas: list[tuple[str, LineString]] = []
    for placemark in root.findall(".//k:Placemark", ns):
        name = (placemark.findtext("k:name", default="", namespaces=ns) or "").strip()
        desenhos = _poligonos_do_ponto(placemark, ns)
        if desenhos:
            poligonos.extend((name or f"poligono {len(poligonos) + 1}", poly) for poly in desenhos)
            continue
        geom = placemark.find(".//k:LineString", ns)
        if geom is None:
            continue
        pts = _coords(geom.findtext("k:coordinates", default="", namespaces=ns))
        if len(pts) < 2:
            continue
        linhas.append((name or "cerca", LineString(pts)))

    if poligonos:
        return polygons_from_placemarks(poligonos)
    if not linhas:
        raise ValueError("O KML não tem polígonos nem linhas de cerca.")
    return network_from_lines(linhas, snap_m)


def network_from_lines(named: list[tuple[str, LineString]], snap_m: float = 15.0) -> KmlImport:
    """Fecha os pastos a partir das cercas. `named` são as linhas originais, em WGS84."""
    if not named:
        raise ValueError("Não há cercas para fechar.")

    metric = [_project(line, _TO_UTM) for _, line in named]
    noded = node(unary_union(_snap_and_split(metric, snap_m)))
    faces, _cuts, dangles, _invalid = polygonize_full(noded)
    raw_faces = [poly for poly in polygonize(noded) if poly.area > 1]

    polygons = []
    discarded = 0
    for poly in raw_faces:
        if not poly.is_valid:
            poly = poly.buffer(0)
        pieces = [poly] if poly.geom_type == "Polygon" else list(getattr(poly, "geoms", []))
        for piece in pieces:
            if piece.geom_type != "Polygon":
                discarded += 1
                continue
            wgs = _project_poly(piece)
            area = _area_ha(wgs)
            if area < 0.8:
                discarded += 1
                continue
            ponto = wgs.representative_point()
            polygons.append(
                {
                    "seq": 0,
                    "area_ha": round(area, 2),
                    "situacao": _situacao(area),
                    "geojson": mapping(wgs),
                    "centro": [round(ponto.x, 6), round(ponto.y, 6)],
                    "travada": False,
                }
            )
    polygons.sort(key=lambda item: -item["area_ha"])
    for i, item in enumerate(polygons, start=1):
        item["seq"] = i

    lines = []
    for name, line in named:
        lines.append(
            {
                "nome": name,
                "dangling": False,
                "geojson": mapping(line),
            }
        )
    dangle_m = 0.0
    for piece in _explode(dangles):
        dangle_m += piece.length
        lines.append(
            {
                "nome": "vão",
                "dangling": True,
                "geojson": mapping(_project(piece, _TO_WGS)),
            }
        )

    return KmlImport(
        polygons=polygons,
        lines=lines,
        stats={
            "cercas": len(named),
            "poligonos": len(polygons),
            "descartados": discarded,
            "vao_m": round(dangle_m, 0),
            "snap_m": snap_m,
            "faces_brutas": len(getattr(faces, "geoms", []) or []),
        },
    )


def _project_poly(poly):
    from shapely.geometry import Polygon

    shell = [_TO_WGS.transform(x, y) for x, y in poly.exterior.coords]
    holes = [
        [_TO_WGS.transform(x, y) for x, y in ring.coords] for ring in poly.interiors
    ]
    return Polygon(shell, holes)
