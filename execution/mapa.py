"""Mapa Leaflet da fazenda: importação de KML, vínculo com Tab_local e camada de animais."""

from __future__ import annotations

import html
import json
import os

import folium
import pandas as pd
import streamlit as st
from folium.plugins import Draw, Fullscreen
from pyproj import Geod
from shapely.geometry import LineString, Point, mapping, shape
from streamlit_folium import st_folium

from gis.kml_import import network_from_lines, parse_kml
from gis.store import desvincular, open_store, vincular

_SEM_VINCULO = "— não vincular —"
_SITUACAO = {
    "ok": "fechada",
    "pequena": "pequena — conferir",
    "uniao": "união de pastos — cerca aberta",
    "vinculada": "vinculada — travada",
}
_GEOD = Geod(ellps="WGS84")


def render_mapa(conn, df_farms: pd.DataFrame, selected_codes: list):
    store, info = open_store(conn)
    farms = df_farms[df_farms["cod_fazenda"].isin(selected_codes)].copy()
    farms["cod_fazenda"] = farms["cod_fazenda"].astype(int)
    if farms.empty:
        st.warning("Selecione uma fazenda no filtro acima.")
        return

    st.caption(f"Geometrias: {info.label}")
    if info.warning:
        st.info(info.warning)

    labels = {
        int(row.cod_fazenda): f"{row.descricao} ({int(row.cod_fazenda)})"
        for row in farms.itertuples(index=False)
    }
    preferred = 4 if 4 in labels else int(farms["cod_fazenda"].iloc[0])
    cod_fazenda = st.selectbox(
        "Fazenda do mapa",
        options=list(labels.keys()),
        index=list(labels.keys()).index(preferred),
        format_func=lambda cod: labels[cod],
        key="mapa_fazenda",
    )

    tab_mapa, tab_importar = st.tabs(["Mapa", "Importar KML"])
    with tab_mapa:
        _mapa_interativo(conn, store, int(cod_fazenda))
    with tab_importar:
        _importar(conn, store, int(cod_fazenda))


def _mapa_interativo(conn, store, cod_fazenda: int):
    areas = store.areas(cod_fazenda)
    lines = store.lines(cod_fazenda)
    if not areas:
        st.info("Esta fazenda ainda não tem áreas importadas. Use a aba Importar KML.")
        return

    locais = _locais(conn, cod_fazenda)
    por_id = {int(row.id_geo_area): row for row in locais.itertuples(index=False) if pd.notna(row.id_geo_area)}
    contagem = _contagem(conn, cod_fazenda)

    features_animais = []
    features_biomassa = []
    for area in areas:
        local = por_id.get(int(area["id"]))
        cod_local = "" if local is None else str(local.cod_local)
        nome = "Sem local vinculado" if local is None else f"{str(local.cod_local).strip()} — {local.descricao}"
        cabecas = int(contagem.get(cod_local.strip(), 0)) if cod_local else 0
        props = {
            "geo_id": int(area["id"]),
            "nome": nome,
            "descricao": "" if local is None else str(local.descricao or ""),
            "area_ha": area["area_ha"],
            "cabecas": cabecas,
            "cod_local": cod_local,
        }
        features_animais.append({"type": "Feature", "properties": props, "geometry": area["geojson"]})
        features_biomassa.append(
            {
                "type": "Feature",
                "properties": {**props, "biomassa": "sem medição"},
                "geometry": area["geojson"],
            }
        )

    mapa = _base_map(features_animais)
    folium.GeoJson(
        {"type": "FeatureCollection", "features": features_animais},
        name="Animais",
        style_function=_estilo_animais,
        highlight_function=lambda _f: {"weight": 3, "color": "#be185d", "fillOpacity": 0.35},
        tooltip=folium.GeoJsonTooltip(
            fields=["nome", "area_ha", "cabecas"],
            aliases=["Local", "Área (ha)", "Animais"],
            sticky=True,
        ),
    ).add_to(mapa)
    folium.GeoJson(
        {"type": "FeatureCollection", "features": features_biomassa},
        name="Biomassa",
        show=False,
        style_function=lambda _f: {
            "fillColor": "#d97706",
            "color": "#92400e",
            "weight": 1.5,
            "fillOpacity": 0.35,
            "dashArray": "4 4",
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["nome", "biomassa"],
            aliases=["Local", "Biomassa"],
            sticky=True,
        ),
    ).add_to(mapa)
    _linhas_no_mapa(mapa, lines)
    for feature in features_animais:
        codigo = str(feature["properties"].get("cod_local") or "").strip()
        if not codigo:
            continue
        ponto = shape(feature["geometry"]).representative_point()
        _rotulo_no_mapa(mapa, ponto.y, ponto.x, codigo, feature["properties"].get("descricao") or "")
    folium.LayerControl(collapsed=False).add_to(mapa)

    st.markdown(
        "A camada **Animais** pinta cada área pela quantidade de cabeças ativas do local vinculado. "
        "A camada **Biomassa** já está no controle do mapa, pronta para receber medição de pasto. "
        "Para fechar um vão ou traçar uma cerca nova, use **Importar KML**. "
        "Área já vinculada a um local não se edita: desvincule antes."
    )
    clique = _desenhar(mapa, f"mapa-{cod_fazenda}")
    _painel_clique(conn, cod_fazenda, areas, por_id, clique)

    vinculados = sum(1 for area in areas if int(area["id"]) in por_id)
    em_ni = int(contagem.get("NI", 0))
    c1, c2, c3 = st.columns(3)
    c1.metric("Áreas no mapa", len(areas))
    c2.metric("Vinculadas a um local", vinculados)
    c3.metric("Animais em NI", f"{em_ni:,}".replace(",", "."))
    if em_ni:
        st.caption(
            "NI (Não Informado) não é uma divisão do KML. Enquanto o animal estiver nesse local, "
            "ele não aparece dentro de um pasto."
        )


def _dist_m(a, b) -> float:
    _az1, _az2, dist = _GEOD.inv(a[0], a[1], b[0], b[1])
    return abs(dist)


def _centro_de(geojson) -> list[float]:
    ponto = shape(geojson).representative_point()
    return [round(ponto.x, 6), round(ponto.y, 6)]


def _vinculadas(locais: pd.DataFrame, areas: list[dict]) -> list[dict]:
    por_id = {}
    for row in locais.itertuples(index=False):
        if pd.notna(row.id_geo_area):
            por_id[int(row.id_geo_area)] = row
    saida = []
    for area in areas:
        local = por_id.get(int(area["id"]))
        if local is None:
            continue
        saida.append(
            {
                "id": int(area["id"]),
                "area_ha": float(area["area_ha"] or 0),
                "geojson": area["geojson"],
                "cod_local": local.cod_local,
                "descricao": local.descricao,
                "nome": _rotulo_local(local.cod_local, local.descricao),
            }
        )
    return saida


def _casa_vinculo(poly: dict, vinculadas: list[dict]):
    geom = shape(poly["geojson"])
    ponto = geom.representative_point()
    for item in vinculadas:
        antigo = shape(item["geojson"])
        if not (antigo.covers(ponto) or antigo.buffer(0.00005).covers(ponto)):
            continue
        base = float(item["area_ha"] or poly["area_ha"] or 1)
        if abs(float(poly["area_ha"]) - base) / base <= 0.03:
            return item
    return None


def _perto_de_oculta(poly: dict, ocultas: list[dict]) -> bool:
    centro = poly.get("centro") or _centro_de(poly["geojson"])
    for oculta in ocultas:
        outro = oculta.get("centro") or _centro_de(oculta["geojson"])
        if _dist_m(centro, outro) < 40:
            return True
    return False


def _classificar(polygons: list[dict], vinculadas: list[dict], ocultas: list[dict]) -> list[dict]:
    saida = []
    for poly in polygons:
        lock = _casa_vinculo(poly, vinculadas)
        if lock:
            saida.append({
                **poly,
                "travada": True,
                "geo_id": lock["id"],
                "local": lock["nome"],
                "cod_local": str(lock["cod_local"]).strip(),
                "descricao": lock.get("descricao") or "",
            })
            continue
        if _perto_de_oculta(poly, ocultas):
            continue
        saida.append({**poly, "travada": False, "geo_id": None, "local": ""})
    return saida


def _fontes(lines: list[dict]) -> list[tuple[str, LineString]]:
    fontes = []
    for linha in lines:
        if linha.get("dangling"):
            continue
        geom = shape(linha["geojson"])
        if geom.geom_type == "LineString" and len(geom.coords) >= 2:
            fontes.append((linha.get("nome") or "cerca", geom))
    return fontes


def _aplicar_rede(prev: dict, snap: float, vinculadas: list[dict], ocultas: list[dict]):
    resultado = network_from_lines(_fontes(prev["lines"]), snap)
    for item in vinculadas:
        ponto = shape(item["geojson"]).representative_point()
        achou = None
        for poly in resultado.polygons:
            geom = shape(poly["geojson"])
            if geom.covers(ponto) or geom.buffer(0.00005).covers(ponto):
                achou = poly
                break
        if achou is None:
            return None, f"Essa cerca desfaz a área vinculada a {item['nome']}. Desvincule esse local antes."
        base = float(item["area_ha"] or achou["area_ha"] or 1)
        if abs(achou["area_ha"] - base) / base > 0.03:
            return None, (
                f"Essa cerca corta ou junta a área vinculada a {item['nome']}. "
                "Desvincule esse local, ajuste, e vincule de novo."
            )
    return {
        "nome": prev.get("nome"),
        "stats": resultado.stats,
        "polygons": _classificar(resultado.polygons, vinculadas, ocultas),
        "lines": resultado.lines,
        "ocultas": ocultas,
    }, None


def _vinculos_por_centro(editado: pd.DataFrame, polygons: list[dict]) -> dict:
    if editado is None or editado.empty or "seq" not in editado.columns:
        return {}
    por_seq = {int(row.seq): row.vinculo for row in editado.itertuples(index=False)}
    saida = {}
    for poly in polygons:
        if poly.get("travada") or not poly.get("centro"):
            continue
        vinculo = por_seq.get(int(poly["seq"]))
        if vinculo:
            saida[tuple(poly["centro"])] = vinculo
    return saida


def _copiar_vinculos(df: pd.DataFrame, polygons: list[dict], por_centro: dict) -> pd.DataFrame:
    if df.empty or not por_centro:
        return df
    livres = [poly for poly in polygons if not poly.get("travada")]
    for indice, row in df.iterrows():
        poly = next(item for item in livres if int(item["seq"]) == int(row["seq"]))
        centro = tuple(poly.get("centro") or _centro_de(poly["geojson"]))
        melhor = None
        melhor_dist = 30
        for antigo, vinculo in por_centro.items():
            dist = _dist_m(centro, antigo)
            if dist < melhor_dist:
                melhor = vinculo
                melhor_dist = dist
        if melhor:
            df.at[indice, "vinculo"] = melhor
    return df


def _publicar(cod_fazenda: int, prev: dict, locais: pd.DataFrame, por_centro: dict | None = None):
    livres = [poly for poly in prev["polygons"] if not poly.get("travada")]
    df = _sugerir(livres, locais)
    df = _copiar_vinculos(df, prev["polygons"], por_centro or {})
    st.session_state[f"kml_prev_{cod_fazenda}"] = prev
    st.session_state[f"kml_df_{cod_fazenda}"] = df
    st.session_state[f"kml_nonce_{cod_fazenda}"] = st.session_state.get(f"kml_nonce_{cod_fazenda}", 0) + 1


def _chave_linha(coords) -> str:
    return json.dumps([[round(float(x), 5), round(float(y), 5)] for x, y, *_rest in coords])


def _importar(conn, store, cod_fazenda: int):
    pasta = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "KML"))
    arquivos = []
    if os.path.isdir(pasta):
        arquivos = sorted(
            (nome for nome in os.listdir(pasta) if nome.lower().endswith((".kml", ".klm"))),
            key=lambda nome: (0 if nome.lower() == "tailandiavp.kml" else 1, nome.lower()),
        )
    origem = st.radio(
        "Origem do arquivo",
        ["Pasta KML do projeto", "Enviar arquivo"],
        horizontal=True,
        key=f"origem_kml_{cod_fazenda}",
    )
    payload = None
    nome = None
    if origem == "Pasta KML do projeto":
        if not arquivos:
            st.warning(f"Nenhum .kml em {pasta}.")
        else:
            nome = st.selectbox("Arquivo", arquivos, key=f"arquivo_kml_{cod_fazenda}")
            if nome:
                with open(os.path.join(pasta, nome), "rb") as handle:
                    payload = handle.read()
    else:
        enviado = st.file_uploader("KML", type=["kml", "klm"], key=f"upload_kml_{cod_fazenda}")
        if enviado is not None:
            nome = enviado.name
            payload = enviado.getvalue()

    snap = st.slider(
        "Tolerância para fechar vão de cerca (metros)",
        min_value=5,
        max_value=40,
        value=15,
        key=f"snap_{cod_fazenda}",
    )
    st.markdown(
        "Cercas que não fecharam ficam **vermelhas**. O mapa fica em cima da tabela. "
        "Para emendar um vão ou dividir um pasto, use o ícone de **linha** no canto superior esquerdo, "
        "logo abaixo do + e do −. Clique o começo e o fim da cerca e termine com o último ponto. "
        "Área azul já está vinculada e não muda: desvincule o local antes."
    )
    locais = _locais(conn, cod_fazenda)
    vinculadas = _vinculadas(locais, store.areas(cod_fazenda))
    ocultas_db = []
    for area in store.excluidas(cod_fazenda):
        area["centro"] = _centro_de(area["geojson"])
        ocultas_db.append(area)

    ligados = locais[locais["id_geo_area"].notna()] if "id_geo_area" in locais.columns else locais.iloc[0:0]
    if not ligados.empty:
        st.markdown("**Locais já vinculados** — a geometria deles está travada.")
        escolha = st.selectbox(
            "Local para desvincular",
            options=[_rotulo_local(row.cod_local, row.descricao) for row in ligados.itertuples(index=False)],
            key=f"desv_escolha_{cod_fazenda}",
        )
        if st.button("Desvincular", key=f"desv_btn_{cod_fazenda}"):
            cod_local = _cod_do_rotulo(escolha, locais)
            desvincular(conn, cod_fazenda, cod_local)
            prev_atual = st.session_state.get(f"kml_prev_{cod_fazenda}")
            if prev_atual:
                vinculadas_novas = [item for item in vinculadas if item["cod_local"] != cod_local]
                novo, erro = _aplicar_rede(prev_atual, float(snap), vinculadas_novas, prev_atual.get("ocultas") or ocultas_db)
                if erro:
                    st.error(erro)
                else:
                    _publicar(cod_fazenda, novo, _locais(conn, cod_fazenda))
            st.rerun()

    col_a, col_b = st.columns(2)
    with col_a:
        ler = st.button("Ler KML e sugerir vínculos", type="primary", disabled=payload is None, use_container_width=True)
    with col_b:
        abrir = st.button("Abrir cercas já gravadas", use_container_width=True)
    restaurar = st.button("Restaurar áreas excluídas")

    if restaurar:
        store.apagar_excluidas(cod_fazenda)
        prev_atual = st.session_state.get(f"kml_prev_{cod_fazenda}")
        if prev_atual:
            novo, erro = _aplicar_rede(prev_atual, float(snap), vinculadas, [])
            if erro:
                st.error(erro)
            else:
                _publicar(cod_fazenda, novo, locais)
        st.rerun()

    if ler:
        try:
            resultado = parse_kml(payload, snap_m=float(snap))
        except Exception as exc:
            st.error(f"Não foi possível ler o KML: {exc}")
            return
        if resultado.stats.get("origem") == "poligono":
            for poly in resultado.polygons:
                row = _local_do_nome(poly.get("nome_kml"), locais)
                if row is None:
                    continue
                poly["cod_local"] = str(row.cod_local).strip()
                poly["descricao"] = str(row.descricao or "").strip()
            _publicar(
                cod_fazenda,
                {
                    "nome": nome,
                    "stats": resultado.stats,
                    "polygons": _classificar(resultado.polygons, vinculadas, ocultas_db),
                    "lines": [],
                    "ocultas": ocultas_db,
                },
                locais,
            )
            st.rerun()
        novo, erro = _aplicar_rede(
            {"nome": nome, "lines": resultado.lines},
            float(snap),
            vinculadas,
            ocultas_db,
        )
        if erro:
            st.error(erro)
            return
        _publicar(cod_fazenda, novo, locais)
        st.rerun()

    if abrir:
        gravadas = store.lines(cod_fazenda)
        if not any(not linha.get("dangling") for linha in gravadas):
            st.warning("Ainda não há cercas gravadas para esta fazenda.")
        else:
            try:
                novo, erro = _aplicar_rede(
                    {"nome": "cercas gravadas", "lines": gravadas},
                    float(snap),
                    vinculadas,
                    ocultas_db,
                )
            except Exception as exc:
                st.error(f"Não foi possível reabrir as cercas: {exc}")
                return
            if erro:
                st.error(erro)
            else:
                _publicar(cod_fazenda, novo, locais)
                st.rerun()

    prev = st.session_state.get(f"kml_prev_{cod_fazenda}")
    if not prev:
        return

    stats = prev["stats"]
    travadas = sum(1 for poly in prev["polygons"] if poly.get("travada"))
    if stats.get("origem") == "poligono":
        st.markdown(
            f"**{stats['poligonos']}** polígonos lidos pelo nome do KML, no mesmo código de `tab_local.cod_local`. "
            f"**{travadas}** já vinculados e travados. "
            "O que ainda não está desenhado no arquivo entra na próxima leitura."
        )
    else:
        st.markdown(
            f"**{stats['poligonos']}** áreas fechadas a partir de **{stats['cercas']}** cercas. "
            f"**{travadas}** travadas por vínculo. "
            f"Cerca ainda aberta: **{stats['vao_m']:.0f} m**."
        )
    opcoes = [_SEM_VINCULO] + [
        _rotulo_local(row.cod_local, row.descricao) for row in locais.itertuples(index=False) if _area_util(row)
    ]
    df_key = f"kml_df_{cod_fazenda}"
    df_ajuste = st.session_state.get(df_key, pd.DataFrame())
    if not df_ajuste.empty and "excluir" not in df_ajuste.columns:
        df_ajuste = df_ajuste.copy()
        df_ajuste["excluir"] = False
        st.session_state[df_key] = df_ajuste

    if stats.get("origem") == "poligono":
        st.caption("O nome de cada polígono já escolhe o local. Confira a tabela e salve. Espaço no código (26A e 26 A) é o mesmo local.")
    else:
        st.caption("Para fechar ou dividir: ícone de linha no canto superior esquerdo, logo abaixo do + e do −.")
    preview = _base_map(
        [
            {
                "type": "Feature",
                "properties": {"seq": poly["seq"], "area_ha": poly["area_ha"]},
                "geometry": poly["geojson"],
            }
            for poly in prev["polygons"]
        ]
    )
    folium.GeoJson(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "seq": poly["seq"],
                        "area_ha": poly["area_ha"],
                        "nome": poly.get("nome_kml") or poly.get("cod_local") or "",
                        "situacao": "vinculada" if poly.get("travada") else _SITUACAO.get(poly["situacao"], poly["situacao"]),
                    },
                    "geometry": poly["geojson"],
                }
                for poly in prev["polygons"]
            ],
        },
        name="Áreas",
        style_function=_estilo_ajuste,
        tooltip=folium.GeoJsonTooltip(fields=["nome", "seq", "area_ha", "situacao"], aliases=["Nome", "Área", "ha", "Leitura"]),
    ).add_to(preview)
    for poly in prev["polygons"]:
        codigo = (poly.get("cod_local") or poly.get("nome_kml") or "").strip()
        if not codigo:
            continue
        ponto = shape(poly["geojson"]).representative_point()
        _rotulo_no_mapa(mapa=preview, lat=ponto.y, lon=ponto.x, codigo=codigo, descricao=poly.get("descricao") or "")
    _linhas_no_mapa(preview, prev["lines"], mostrar_vao=True)
    if stats.get("origem") != "poligono":
        Draw(
            export=False,
            position="topleft",
            draw_options={
                "polyline": {"shapeOptions": {"color": "#facc15", "weight": 4}},
                "polygon": False,
                "rectangle": False,
                "circle": False,
                "marker": False,
                "circlemarker": False,
            },
            edit_options={"edit": False, "remove": False},
        ).add_to(preview)
    folium.LayerControl(position="bottomright", collapsed=True).add_to(preview)
    desenhos = _desenhar_ajuste(
        preview,
        f"ajuste-{cod_fazenda}-{st.session_state.get(f'kml_nonce_{cod_fazenda}', 0)}",
    )
    vistas = st.session_state.setdefault(f"cercas_vistas_{cod_fazenda}", set())
    rejeitadas = st.session_state.setdefault(f"cercas_rejeitadas_{cod_fazenda}", {})
    for feat in desenhos if stats.get("origem") != "poligono" else []:
        geom = feat.get("geometry") or {}
        if geom.get("type") != "LineString":
            continue
        coords = geom.get("coordinates") or []
        if len(coords) < 2:
            continue
        chave = _chave_linha(coords)
        if chave in rejeitadas:
            st.warning(rejeitadas[chave])
        if chave in vistas:
            continue
        vistas.add(chave)
        linha = LineString([(float(pto[0]), float(pto[1])) for pto in coords])
        candidata = {
            "nome": prev.get("nome"),
            "lines": [item for item in prev["lines"] if not item.get("dangling")]
            + [{"nome": "cerca desenhada", "dangling": False, "geojson": mapping(linha)}],
        }
        novo, erro = _aplicar_rede(candidata, float(snap), vinculadas, prev.get("ocultas") or ocultas_db)
        if erro:
            rejeitadas[chave] = erro
            st.warning(erro)
            continue
        _publicar(cod_fazenda, novo, locais, _vinculos_por_centro(df_ajuste, prev["polygons"]))
        st.rerun()

    editado = df_ajuste
    if not df_ajuste.empty:
        editado = st.data_editor(
            df_ajuste,
            key=f"editor_kml_{cod_fazenda}_{st.session_state.get(f'kml_nonce_{cod_fazenda}', 0)}",
            hide_index=True,
            use_container_width=True,
            column_config={
                "seq": st.column_config.NumberColumn("Área", disabled=True),
                "area_kml_ha": st.column_config.NumberColumn("KML (ha)", format="%.2f", disabled=True),
                "situacao": st.column_config.TextColumn("Leitura", disabled=True),
                "area_cadastro_ha": st.column_config.NumberColumn("Cadastro (ha)", format="%.2f", disabled=True),
                "diferenca_pct": st.column_config.NumberColumn("Diferença %", format="%.0f", disabled=True),
                "excluir": st.column_config.CheckboxColumn("Excluir"),
                "vinculo": st.column_config.SelectboxColumn("Local em Tab_local", options=opcoes, required=True),
            },
        )
        if st.button("Tirar do mapa as áreas marcadas"):
            ficam = []
            novas_ocultas = list(prev.get("ocultas") or [])
            marcadas = {int(row.seq) for row in editado.itertuples(index=False) if row.excluir}
            for poly in prev["polygons"]:
                if poly.get("travada"):
                    ficam.append(poly)
                elif int(poly["seq"]) in marcadas:
                    novas_ocultas.append(poly)
                else:
                    ficam.append(poly)
            prev = {**prev, "polygons": ficam, "ocultas": novas_ocultas}
            _publicar(cod_fazenda, prev, locais, _vinculos_por_centro(editado, prev["polygons"]))
            st.rerun()

    if st.button("Salvar áreas e vínculos", type="primary"):
        try:
            _salvar_ajuste(conn, store, cod_fazenda, prev, editado, locais, vinculadas)
        except Exception as exc:
            st.error(f"Não salvou: {exc}")
            return
        st.success("Ajuste gravado. Áreas vinculadas foram mantidas.")
        st.session_state.pop(f"kml_prev_{cod_fazenda}", None)


def _salvar_ajuste(conn, store, cod_fazenda, prev, editado, locais, vinculadas):
    por_seq = {}
    if editado is not None and not editado.empty:
        por_seq = {int(row.seq): row for row in editado.itertuples(index=False)}
    ja_ligados = {item["cod_local"]: item["id"] for item in vinculadas}
    lote = []
    ligacoes = []
    usados = set()
    numero = 1
    for poly in prev["polygons"]:
        if poly.get("travada"):
            continue
        row = por_seq.get(int(poly["seq"]))
        excluir = bool(getattr(row, "excluir", False)) if row is not None else False
        item = {**poly, "seq": numero, "situacao": "excluida" if excluir else poly.get("situacao")}
        lote.append(item)
        if row is not None and not excluir and row.vinculo != _SEM_VINCULO:
            cod_local = _cod_do_rotulo(row.vinculo, locais)
            if cod_local in ja_ligados:
                raise ValueError(f"{row.vinculo} já está vinculado. Desvincule antes de apontar outra área.")
            if cod_local in usados:
                raise ValueError(f"O local {row.vinculo} foi escolhido mais de uma vez.")
            usados.add(cod_local)
            ligacoes.append((numero, cod_local))
        numero += 1
    for oculta in prev.get("ocultas") or []:
        lote.append({**oculta, "seq": numero, "situacao": "excluida"})
        numero += 1
    keep = [int(poly["geo_id"]) for poly in prev["polygons"] if poly.get("travada") and poly.get("geo_id")]
    ids = store.replace_unlinked(cod_fazenda, prev.get("nome") or "ajuste", lote, prev["lines"], keep)
    vincular(conn, cod_fazenda, [(cod_local, ids[seq]) for seq, cod_local in ligacoes])


def _estilo_ajuste(feature):
    situacao = feature["properties"].get("situacao")
    if situacao == "vinculada":
        return {"fillColor": "#1e3a8a", "color": "#1e3a8a", "weight": 2, "fillOpacity": 0.4}
    if situacao == "fechada":
        return {"fillColor": "#059669", "color": "#064e3b", "weight": 1.5, "fillOpacity": 0.35}
    return {"fillColor": "#d97706", "color": "#064e3b", "weight": 1.5, "fillOpacity": 0.35}


def _desenhar_ajuste(mapa, key: str):
    saida = st_folium(
        mapa,
        key=key,
        height=680,
        use_container_width=True,
        returned_objects=["all_drawings"],
    )
    return (saida or {}).get("all_drawings") or []


def _norm_cod(valor) -> str:
    return "".join(str(valor or "").upper().split())


def _local_do_nome(nome, locais: pd.DataFrame):
    alvo = _norm_cod(nome)
    if not alvo:
        return None
    achados = [row for row in locais.itertuples(index=False) if _norm_cod(row.cod_local) == alvo]
    if not achados:
        return None
    pedido = str(nome).strip().upper()
    for row in achados:
        if str(row.cod_local).strip().upper() == pedido:
            return row
    return achados[0]


def _sugerir(polygons: list[dict], locais: pd.DataFrame) -> pd.DataFrame:
    por_nome: dict[int, tuple | None] = {}
    usados = set()
    for poly in polygons:
        nome = (poly.get("nome_kml") or "").strip()
        if not nome:
            continue
        row = _local_do_nome(nome, locais)
        if row is None:
            por_nome[int(poly["seq"])] = None
            continue
        rotulo = _rotulo_local(row.cod_local, row.descricao)
        if rotulo in usados:
            por_nome[int(poly["seq"])] = None
            continue
        usados.add(rotulo)
        area = float(row.area or 0)
        dif = abs(poly["area_ha"] - area) / area * 100 if area > 0 else None
        por_nome[int(poly["seq"])] = (rotulo, area or None, dif, nome)

    candidatos = []
    for row in locais.itertuples(index=False):
        if not _area_util(row):
            continue
        rotulo = _rotulo_local(row.cod_local, row.descricao)
        if rotulo in usados:
            continue
        candidatos.append((float(row.area or 0), rotulo))

    pares = []
    for poly in polygons:
        if int(poly["seq"]) in por_nome or poly["situacao"] != "ok":
            continue
        for area, rotulo in candidatos:
            if area <= 0:
                continue
            rel = abs(poly["area_ha"] - area) / area
            pares.append((rel, poly["seq"], rotulo, area))
    pares.sort()
    escolha = {}
    for rel, seq, rotulo, area in pares:
        if rel > 0.2 or seq in escolha or rotulo in usados:
            continue
        escolha[seq] = (rotulo, area, rel * 100)
        usados.add(rotulo)

    linhas = []
    for poly in polygons:
        seq = int(poly["seq"])
        if seq in por_nome and por_nome[seq] is not None:
            rotulo, area_cad, dif, nome = por_nome[seq]
            leitura = f"nome {nome}"
        elif seq in por_nome:
            rotulo, area_cad, dif = _SEM_VINCULO, None, None
            leitura = f"sem cadastro ({poly.get('nome_kml')})"
        else:
            rotulo, area_cad, dif = escolha.get(seq, (_SEM_VINCULO, None, None))
            leitura = _SITUACAO.get(poly["situacao"], poly["situacao"])
        linhas.append(
            {
                "seq": poly["seq"],
                "area_kml_ha": poly["area_ha"],
                "situacao": leitura,
                "area_cadastro_ha": area_cad,
                "diferenca_pct": dif,
                "excluir": False,
                "vinculo": rotulo,
            }
        )
    return pd.DataFrame(linhas)


def _locais(conn, cod_fazenda: int) -> pd.DataFrame:
    df = pd.read_sql(
        """
        SELECT Cod_Local AS cod_local, Descricao AS descricao, Area AS area, id_geo_area
        FROM Tab_local
        WHERE Cod_Fazenda = ?
        ORDER BY Descricao
        """,
        conn,
        params=[int(cod_fazenda)],
    )
    return df


def _contagem(conn, cod_fazenda: int) -> dict[str, int]:
    df = pd.read_sql(
        """
        SELECT RTRIM(c.Cod_Local) AS cod_local, COUNT(*) AS cabecas
        FROM cad_fichario c
        WHERE c.Cod_Fazenda = ?
          AND c.Origem <> 'E'
          AND c.Cod_Categoria NOT IN (
              SELECT Cod_Categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S'
          )
        GROUP BY RTRIM(c.Cod_Local)
        """,
        conn,
        params=[int(cod_fazenda)],
    )
    return {str(row.cod_local): int(row.cabecas) for row in df.itertuples(index=False)}


def _animais(conn, cod_fazenda: int, cod_local: str) -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT
            c.ID_Animal AS Identificação,
            c.Nome AS Nome,
            c.Sexo AS Sexo,
            t.Descricao AS Categoria,
            t.Unidade_Animal AS UA
        FROM cad_fichario c
        LEFT JOIN Tab_categoria t ON c.Cod_Categoria = t.Cod_Categoria
        WHERE c.Cod_Fazenda = ?
          AND RTRIM(c.Cod_Local) = ?
          AND c.Origem <> 'E'
          AND c.Cod_Categoria NOT IN (
              SELECT Cod_Categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S'
          )
        ORDER BY t.Descricao, c.ID_Animal
        """,
        conn,
        params=[int(cod_fazenda), cod_local.strip()],
    )


def _painel_clique(conn, cod_fazenda, areas, por_id, clique):
    if not clique:
        st.caption("Clique dentro de uma área para listar os animais daquele local.")
        return
    props = clique.get("properties") or {}
    escolhida = None
    if props.get("geo_id") is not None:
        escolhida = next((area for area in areas if int(area["id"]) == int(props["geo_id"])), None)
    lat = clique.get("lat", clique.get("latitude"))
    lng = clique.get("lng", clique.get("longitude"))
    if escolhida is None and lat is not None and lng is not None:
        ponto = Point(float(lng), float(lat))
        for area in areas:
            geom = shape(area["geojson"])
            if geom.covers(ponto) or geom.buffer(0.00008).covers(ponto):
                if escolhida is None or float(area["area_ha"]) < float(escolhida["area_ha"]):
                    escolhida = area
    if escolhida is None and lat is None:
        st.caption("Clique dentro de uma área para listar os animais daquele local.")
        return
    if escolhida is None:
        st.caption("O clique ficou fora das áreas fechadas.")
        return
    local = por_id.get(int(escolhida["id"]))
    if local is None:
        st.warning(
            f"Área {escolhida['seq']} ({escolhida['area_ha']} ha) ainda não está vinculada a um local. "
            "Faça o vínculo na aba Importar KML."
        )
        return
    st.markdown(f"**{str(local.cod_local).strip()} — {local.descricao}** · {escolhida['area_ha']} ha")
    if st.button(
        "Desvincular este local",
        key=f"desv_mapa_{cod_fazenda}_{str(local.cod_local).strip()}",
    ):
        desvincular(conn, cod_fazenda, local.cod_local)
        st.session_state.pop(f"kml_prev_{cod_fazenda}", None)
        st.success("Vínculo removido. O ajuste dessa área volta a ficar disponível em Importar KML.")
        st.rerun()
    animais = _animais(conn, cod_fazenda, str(local.cod_local))
    if animais.empty:
        st.info("Nenhum animal ativo neste local.")
        return
    ua = pd.to_numeric(animais["UA"], errors="coerce").sum()
    st.caption(f"{len(animais)} animais · {ua:.2f} UA".replace(".", ","))
    st.dataframe(animais, use_container_width=True, hide_index=True)


def _base_map(features: list[dict]) -> folium.Map:
    lats, lons = [], []
    for feature in features:
        _coleta(feature["geometry"], lons, lats)
    if not lats:
        centro = [-16.02, -43.43]
        mapa = folium.Map(location=centro, zoom_start=14, tiles=None, max_zoom=22)
    else:
        mapa = folium.Map(
            location=[sum(lats) / len(lats), sum(lons) / len(lons)],
            zoom_start=14,
            tiles=None,
            max_zoom=22,
        )
        mapa.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]])
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, Maxar, Earthstar Geographics",
        name="Satélite",
        overlay=False,
        control=True,
        show=True,
        max_zoom=22,
        max_native_zoom=18,
    ).add_to(mapa)
    folium.TileLayer(
        tiles="OpenStreetMap",
        name="Ruas",
        overlay=False,
        control=True,
        show=False,
        max_zoom=19,
    ).add_to(mapa)
    Fullscreen(position="bottomleft").add_to(mapa)
    return mapa


def _rotulo_no_mapa(mapa, lat: float, lon: float, codigo: str, descricao: str):
    codigo_html = html.escape(str(codigo).strip())
    descricao_html = html.escape(str(descricao or "").strip())
    folium.Marker(
        location=[lat, lon],
        interactive=False,
        icon=folium.DivIcon(
            icon_size=(160, 40),
            icon_anchor=(80, 20),
            html=(
                '<div style="pointer-events:none;text-align:center;line-height:1.05;'
                'text-shadow:0 1px 2px #000,0 0 6px #000;">'
                f'<div style="font-size:22px;font-weight:700;color:#fff;">{codigo_html}</div>'
                f'<div style="font-size:11px;font-weight:500;color:#e2e8f0;">{descricao_html}</div>'
                "</div>"
            ),
        ),
    ).add_to(mapa)


def _coleta(geometry, lons, lats):
    tipo = geometry.get("type")
    coords = geometry.get("coordinates")
    if tipo == "Point":
        lons.append(coords[0])
        lats.append(coords[1])
    elif tipo in ("LineString", "MultiPoint"):
        for x, y, *_ in coords:
            lons.append(x)
            lats.append(y)
    elif tipo in ("Polygon", "MultiLineString"):
        for ring in coords:
            _coleta({"type": "LineString", "coordinates": ring}, lons, lats)
    elif tipo == "MultiPolygon":
        for poly in coords:
            _coleta({"type": "Polygon", "coordinates": poly}, lons, lats)


def _linhas_no_mapa(mapa, lines, mostrar_vao: bool = False):
    cercas = [ln for ln in lines if not ln.get("dangling")]
    vaos = [ln for ln in lines if ln.get("dangling")]
    if cercas:
        folium.GeoJson(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {"nome": ln.get("nome")}, "geometry": ln["geojson"]}
                    for ln in cercas
                ],
            },
            name="Cercas",
            style_function=lambda f: (
                {"color": "#facc15", "weight": 4, "opacity": 1}
                if f["properties"].get("nome") == "cerca desenhada"
                else {"color": "#f8fafc", "weight": 2, "opacity": 0.85}
            ),
        ).add_to(mapa)
    if vaos:
        folium.GeoJson(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {"nome": "vão"}, "geometry": ln["geojson"]}
                    for ln in vaos
                ],
            },
            name="Cercas abertas",
            show=mostrar_vao,
            style_function=lambda _f: {"color": "#e11d48", "weight": 3, "opacity": 0.9},
        ).add_to(mapa)


def _desenhar(mapa, key: str):
    # Só o clique volta para o Python. Centro e zoom ficam no Leaflet;
    # devolvê-los fazia o mapa reenquadrar e oscilar o zoom sozinho.
    saida = st_folium(
        mapa,
        key=key,
        height=680,
        use_container_width=True,
        returned_objects=["last_object_clicked"],
    )
    return (saida or {}).get("last_object_clicked") or {}


def _estilo_animais(feature):
    n = feature["properties"].get("cabecas") or 0
    if n <= 0:
        cor = "#cbd5e1"
    elif n <= 15:
        cor = "#6ee7b7"
    elif n <= 40:
        cor = "#059669"
    else:
        cor = "#064e3b"
    return {"fillColor": cor, "color": "#064e3b", "weight": 1.6, "fillOpacity": 0.62}


def _area_util(row) -> bool:
    descricao = str(row.descricao or "")
    codigo = str(row.cod_local or "").strip().upper()
    if codigo == "NI" or descricao.strip().upper() in {"NI", "NÃO INFORMADO", "NAO INFORMADO"}:
        return False
    try:
        return float(row.area or 0) > 0
    except (TypeError, ValueError):
        return False


def _rotulo_local(cod_local, descricao) -> str:
    return f"{str(cod_local).strip()} — {descricao}"


def _cod_do_rotulo(rotulo: str, locais: pd.DataFrame) -> str:
    for row in locais.itertuples(index=False):
        if _rotulo_local(row.cod_local, row.descricao) == rotulo:
            return row.cod_local
    raise ValueError(f"Local não encontrado: {rotulo}")

