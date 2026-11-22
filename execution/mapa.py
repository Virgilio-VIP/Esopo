"""Mapa Leaflet da fazenda: importação de KML, vínculo com Tab_local e camada de animais."""

from __future__ import annotations

import base64
import html
import json
import os

import folium
import pandas as pd
import plotly.graph_objects as go
from branca.element import MacroElement
from jinja2 import Template
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components
from folium.plugins import Draw, Fullscreen
from folium.raster_layers import ImageOverlay
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


class _RotulosPorZoom(MacroElement):
    """Tamanho do código cresce de forma contínua com o zoom."""

    _template = Template(
        """
    {% macro script(this, kwargs) %}
    var map = {{this._parent.get_name()}};
    function atualizaRotulosEsopo() {
        var z = map.getZoom();
        document.querySelectorAll('.esopo-mapa-rotulo').forEach(function(el) {
            var cod = el.querySelector('.rotulo-cod');
            var desc = el.querySelector('.rotulo-desc');
            if (z < 13) {
                el.style.visibility = 'hidden';
                return;
            }
            el.style.visibility = 'visible';
            var px = Math.round(Math.max(12, Math.min(18, 12 + (z - 13) * 1.5)));
            if (cod) cod.style.fontSize = px + 'px';
            if (desc) {
                if (z < 15) {
                    desc.style.display = 'none';
                } else {
                    desc.style.display = 'block';
                    desc.style.fontSize = Math.max(9, Math.round(px * 0.62)) + 'px';
                }
            }
        });
    }
    map.on('zoom zoomend', atualizaRotulosEsopo);
    map.whenReady(atualizaRotulosEsopo);
    {% endmacro %}
    """
    )


class _PersistenciaTimelapse(MacroElement):
    """Mantém a camada Timelapse selecionada e troca os frames instantaneamente sem recriar o mapa nem piscar."""

    _template = Template(
        """
    {% macro script(this, kwargs) %}
    (function() {
        var map = {{this._parent.get_name()}};
        var chave = 'esopo_timelapse_checked_{{this.cod_fazenda}}';
        var chaveIdx = 'esopo_tl_idx_{{this.cod_fazenda}}';

        map.on('overlayadd', function(e) {
            if (e && e.name === 'Timelapse') {
                try { sessionStorage.setItem(chave, '1'); } catch(err){}
                {% if this.overlay_names %}
                if (typeof sincronizarQuadro === 'function') {
                    sincronizarQuadro();
                }
                {% endif %}
            }
        });
        map.on('overlayremove', function(e) {
            if (e && e.name === 'Timelapse') {
                try { sessionStorage.setItem(chave, '0'); } catch(err){}
            }
        });

        function aplicarPersistencia() {
            try {
                {% if this.ativo %}
                var salvo = sessionStorage.getItem(chave);
                if (salvo === '1') {
                    var labels = document.querySelectorAll('.leaflet-control-layers-overlays label');
                    for (var i = 0; i < labels.length; i++) {
                        var lbl = labels[i];
                        if (lbl.textContent && lbl.textContent.indexOf('Timelapse') !== -1) {
                            var cb = lbl.querySelector('input[type="checkbox"]');
                            if (cb && !cb.checked) {
                                cb.click();
                            }
                            break;
                        }
                    }
                }
                {% else %}
                sessionStorage.removeItem(chave);
                {% endif %}
            } catch (e) {
                console.error(e);
            }
        }

        {% if this.overlay_names %}
        var overlays = [ {{ this.overlay_names | join(', ') }} ];
        var ultimoIdx = -1;

        function trocarQuadro(idx) {
            if (!overlays || overlays.length === 0) return;
            idx = Math.max(0, Math.min(idx, overlays.length - 1));
            if (idx === ultimoIdx) return;
            ultimoIdx = idx;

            // 1. Exibe primeiro o próximo quadro (já carregado e decodificado no DOM)
            var proximoOverlay = overlays[idx];
            if (proximoOverlay) {
                var proximoEl = proximoOverlay.getElement();
                if (proximoEl) {
                    proximoEl.style.display = 'block';
                }
                proximoOverlay.setOpacity(0.9);
            }

            // 2. Oculta todos os demais quadros imediatamente
            for (var i = 0; i < overlays.length; i++) {
                if (i !== idx && overlays[i]) {
                    overlays[i].setOpacity(0);
                    var el = overlays[i].getElement();
                    if (el) {
                        el.style.display = 'none';
                    }
                }
            }
        }

        if (window.BroadcastChannel) {
            try {
                var bc = new BroadcastChannel('esopo_tl_channel_{{this.cod_fazenda}}');
                bc.onmessage = function(e) {
                    if (e && e.data && typeof e.data.idx === 'number') {
                        trocarQuadro(e.data.idx);
                    }
                };
            } catch(e) {}
        }

        function sincronizarQuadro() {
            try {
                var val = localStorage.getItem(chaveIdx);
                if (val !== null) {
                    var idx = parseInt(val, 10);
                    if (!isNaN(idx)) {
                        trocarQuadro(idx);
                        return;
                    }
                }
            } catch(e) {}
            if (ultimoIdx < 0) {
                trocarQuadro({{ this.indice_inicial }});
            }
        }

        setInterval(sincronizarQuadro, 40);
        sincronizarQuadro();
        {% endif %}

        aplicarPersistencia();
        map.whenReady(function() {
            aplicarPersistencia();
            {% if this.overlay_names %}
            sincronizarQuadro();
            {% endif %}
            setTimeout(aplicarPersistencia, 60);
            setTimeout(aplicarPersistencia, 200);
        });
    })();
    {% endmacro %}
    """
    )

    def __init__(self, cod_fazenda: int, ativo: bool, overlays=None, indice_inicial: int = 0):
        super().__init__()
        self.cod_fazenda = int(cod_fazenda)
        self.ativo = bool(ativo)
        self.overlay_names = [ov.get_name() for ov in (overlays or []) if ov is not None]
        self.indice_inicial = int(indice_inicial)


def _timelapse_play_ligar(cod_fazenda: int) -> None:
    st.session_state[f"timelapse_play_{cod_fazenda}"] = True


def _timelapse_play_pausar(cod_fazenda: int) -> None:
    st.session_state[f"timelapse_play_{cod_fazenda}"] = False


def _autoplay_tick(cod_fazenda: int, limite: int) -> None:
    """Avança o mês só no timer do fragmento, sem recriar o mapa neste passo."""
    from streamlit.runtime.scriptrunner_utils.script_run_context import get_script_run_ctx

    ctx = get_script_run_ctx()
    if ctx is None or not ctx.fragment_ids_this_run:
        return
    if not st.session_state.get(f"timelapse_play_{cod_fazenda}"):
        return
    idx_key = f"timelapse_idx_{cod_fazenda}"
    atual = int(st.session_state.get(idx_key, 0))
    st.session_state[idx_key] = 0 if atual >= int(limite) else atual + 1
    st.rerun(scope="app")


def _velocimetro_timelapse(segundos: float) -> None:
    segundos = max(0.25, min(8.0, float(segundos)))
    angulo = 120 - 240 * (segundos - 0.25) / 7.75
    st.markdown(
        f"""<div style="max-width:220px;margin:0 auto;text-align:center;">
        <svg viewBox="0 0 200 110" width="100%" height="88" aria-label="Velocidade da reprodução">
          <path d="M 25 95 A 75 75 0 0 1 175 95" fill="none" stroke="#cbd5e1" stroke-width="10" stroke-linecap="round"/>
          <g transform="translate(100,95) rotate({angulo})">
            <line x1="0" y1="0" x2="0" y2="-62" stroke="#0f172a" stroke-width="3" stroke-linecap="round"/>
            <circle r="5" fill="#ea580c"/>
          </g>
          <text x="100" y="108" text-anchor="middle" font-size="11" fill="#475569">1 quadro a cada {segundos:.2f} s</text>
        </svg>
        </div>""",
        unsafe_allow_html=True,
    )


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

    st.caption("Mapa · versão 20/nov/2025 — timelapse, UA/ha, pressão % e gráficos mensais")

    tab_mapa, tab_importar = st.tabs(["Mapa", "Importar KML"])
    with tab_mapa:
        _mapa_interativo(conn, store, int(cod_fazenda))
    with tab_importar:
        _importar(conn, store, int(cod_fazenda))


_RAMPA_ACIMA = (
    (0.0, (228, 208, 148)),
    (0.5, (134, 239, 172)),
    (1.0, (20, 83, 45)),
)
_RAMPA_ABAIXO = (
    (0.0, (194, 65, 12)),
    (1.0, (228, 208, 148)),
)
_CINZA_SEM_ANIMAL = "#cbd5e1"
_ESPECTRO_TEMPO = (
    (0.0, "#1e3a8a"),
    (0.17, "#14532d"),
    (0.33, "#86efac"),
    (0.5, "#facc15"),
    (0.67, "#ea580c"),
    (0.83, "#c2410c"),
    (1.0, "#dc2626"),
)
_LIMITES_TEMPO_PADRAO = {
    "biomassa": [
        {"classe": "Crítica", "maximo": 0.5},
        {"classe": "Baixa", "maximo": 1.0},
        {"classe": "Média", "maximo": 2.0},
        {"classe": "Boa", "maximo": 3.5},
        {"classe": "Alta", "maximo": 6.0},
        {"classe": "Sobra", "maximo": 999.0},
    ],
    "carga": [
        {"classe": "Sub", "maximo": 0.3},
        {"classe": "Baixa", "maximo": 0.5},
        {"classe": "Média", "maximo": 0.8},
        {"classe": "Boa", "maximo": 1.0},
        {"classe": "Alta", "maximo": 1.5},
        {"classe": "Sobre", "maximo": 999.0},
    ],
    "ua_ha": [
        {"classe": "Sub", "maximo": 0.3},
        {"classe": "Baixa", "maximo": 0.5},
        {"classe": "Média", "maximo": 0.8},
        {"classe": "Boa", "maximo": 1.0},
        {"classe": "Alta", "maximo": 1.5},
        {"classe": "Sobre", "maximo": 999.0},
    ],
    "pressao_pct": [
        {"classe": "Leve", "maximo": 1.5},
        {"classe": "Baixa", "maximo": 3.0},
        {"classe": "Média", "maximo": 4.0},
        {"classe": "Boa", "maximo": 6.0},
        {"classe": "Alta", "maximo": 8.0},
        {"classe": "Crítica", "maximo": 999.0},
    ],
}


def _cor_espectro(t: float) -> str:
    t = max(0.0, min(1.0, float(t)))
    for i in range(len(_ESPECTRO_TEMPO) - 1):
        t0, c0 = _ESPECTRO_TEMPO[i]
        t1, c1 = _ESPECTRO_TEMPO[i + 1]
        if t <= t1 or i == len(_ESPECTRO_TEMPO) - 2:
            peso = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            return _mistura_hex(c0, c1, peso)
    return _ESPECTRO_TEMPO[-1][1]


def _mistura_hex(c0: str, c1: str, peso: float) -> str:
    def par(hex_cor):
        hex_cor = hex_cor.lstrip("#")
        return tuple(int(hex_cor[i : i + 2], 16) for i in (0, 2, 4))

    a, b = par(c0), par(c1)
    rgb = tuple(round(x + (y - x) * peso) for x, y in zip(a, b))
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _limites_timelapse(cod_fazenda: int, criterio: str) -> pd.DataFrame:
    chave = f"limites_tempo_{criterio}_{cod_fazenda}"
    if chave not in st.session_state:
        st.session_state[chave] = pd.DataFrame(_LIMITES_TEMPO_PADRAO[criterio])
    return st.session_state[chave]


def _indice_classe(valor, limites: pd.DataFrame) -> int:
    if valor is None or pd.isna(valor) or limites is None or limites.empty:
        return 0
    for indice, row in limites.sort_values("maximo").iterrows():
        if float(valor) <= float(row.maximo):
            return int(indice)
    return len(limites) - 1


def _cor_por_classe(valor, limites: pd.DataFrame | None) -> str:
    if limites is None or limites.empty:
        return "#475569"
    n = len(limites)
    if n <= 1:
        return _cor_espectro(0.5)
    classe = _indice_classe(valor, limites)
    return _cor_espectro(classe / max(n - 1, 1))


def _cartao_indicador(titulo: str, valor, unidade: str, limites: pd.DataFrame | None, casas: int = 2):
    texto = "—" if valor is None or pd.isna(valor) else _numero(valor, casas)
    cor = _cor_por_classe(valor, limites)
    fundo = _mistura_hex(cor, "#0f172a", 0.72)
    st.markdown(
        f"""<div style="background:{fundo};border:2px solid {cor};border-radius:12px;padding:14px 10px;text-align:center;">
        <div style="color:#e2e8f0;font-size:12px;font-weight:600;">{html.escape(titulo)}</div>
        <div style="color:#fff;font-size:26px;font-weight:700;line-height:1.1;">{texto}</div>
        <div style="color:#cbd5e1;font-size:11px;">{html.escape(unidade)}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def _criterio_mapa(cod_fazenda: int) -> str:
    chave = f"mapa_criterio_{cod_fazenda}"
    atual = st.session_state.get(chave, "UA/ha")
    st.markdown("**Critério que colore a camada Animais**")
    ua, gpd, _resto = st.columns([1, 1, 3])
    if ua.button(
        "UA/ha",
        key=f"btn_ua_{cod_fazenda}",
        type="primary" if atual == "UA/ha" else "secondary",
        use_container_width=True,
    ):
        st.session_state[chave] = "UA/ha"
        if atual != "UA/ha":
            st.rerun()
    if gpd.button(
        "GPD",
        key=f"btn_gpd_{cod_fazenda}",
        type="primary" if atual == "GPD" else "secondary",
        use_container_width=True,
    ):
        st.session_state[chave] = "GPD"
        if atual != "GPD":
            st.rerun()
    return st.session_state.get(chave, "UA/ha")


def _mistura(rampa, t: float) -> str:
    t = max(0.0, min(1.0, t))
    for i in range(len(rampa) - 1):
        t0, cor0 = rampa[i]
        t1, cor1 = rampa[i + 1]
        if t <= t1 or i == len(rampa) - 2:
            peso = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            rgb = tuple(round(a + (b - a) * peso) for a, b in zip(cor0, cor1))
            return "#{:02x}{:02x}{:02x}".format(*rgb)
    return "#14532d"


def _hex_indice(valor, baixo, media, alto) -> str:
    if valor is None or pd.isna(valor) or baixo is None or media is None or alto is None:
        return _CINZA_SEM_ANIMAL
    valor = float(valor)
    if alto <= baixo:
        return _mistura(_RAMPA_ACIMA, 1.0)
    if valor >= media:
        faixa = alto - media
        t = 1.0 if faixa <= 0 else (valor - media) / faixa
        return _mistura(_RAMPA_ACIMA, t)
    faixa = media - baixo
    t = 0.0 if faixa <= 0 else (valor - baixo) / faixa
    return _mistura(_RAMPA_ABAIXO, t)


def _faixa(serie: pd.Series):
    valores = [float(v) for v in serie.dropna()]
    if not valores:
        return None, None, None
    return min(valores), sum(valores) / len(valores), max(valores)


def _indices(conn, cod_fazenda: int) -> pd.DataFrame:
    return pd.read_sql(
        """
        WITH Ultima AS (
            SELECT cod_animal, peso, data, GPD,
                   ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) AS rn
            FROM cad_pesagem_corte
        )
        SELECT
            RTRIM(c.Cod_Local) AS cod_local,
            COUNT(*) AS cabecas,
            SUM(CASE WHEN u.peso IS NOT NULL THEN 1 ELSE 0 END) AS pesados,
            AVG(CAST(u.peso AS float)) AS peso_medio,
            SUM(CAST(u.peso AS float)) AS peso_total,
            AVG(CAST(u.GPD AS float)) AS gpd,
            AVG(CAST(DATEDIFF(day, u.data, GETDATE()) AS float)) AS dias
        FROM cad_fichario c
        LEFT JOIN Ultima u ON c.cod_animal = u.cod_animal AND u.rn = 1
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


def _quadro_indices(areas: list[dict], por_id: dict, indices: pd.DataFrame) -> pd.DataFrame:
    por_cod = {}
    if indices is not None and not indices.empty:
        for row in indices.itertuples(index=False):
            por_cod[str(row.cod_local).strip()] = row
    linhas = []
    for area in areas:
        local = por_id.get(int(area["id"]))
        if local is None:
            continue
        codigo = str(local.cod_local).strip()
        info = por_cod.get(codigo)
        ha = float(area["area_ha"] or 0)
        cabecas = int(info.cabecas) if info is not None else 0
        peso_medio = None if info is None or pd.isna(info.peso_medio) else float(info.peso_medio)
        peso_total = None if info is None or pd.isna(info.peso_total) else float(info.peso_total)
        gpd = None if info is None or pd.isna(info.gpd) else float(info.gpd)
        dias = None if info is None or pd.isna(info.dias) else int(round(float(info.dias)))
        ua_ha = (peso_total / 450.0) / ha if peso_total is not None and ha > 0 else None
        linhas.append(
            {
                "geo_id": int(area["id"]),
                "cod_local": codigo,
                "local": f"{codigo} — {local.descricao}",
                "ha": round(ha, 2),
                "cabecas": cabecas,
                "peso_medio": None if peso_medio is None else round(peso_medio, 1),
                "peso_total": None if peso_total is None else round(peso_total, 1),
                "dias": dias,
                "gpd": None if gpd is None else round(gpd, 3),
                "ua_ha": None if ua_ha is None else round(ua_ha, 3),
            }
        )
    return pd.DataFrame(linhas)


def _preparar_timelapse(conn, cod_fazenda: int, areas: list[dict]) -> tuple[pd.DataFrame | None, tuple[bytes, ...] | None, str | None]:
    """Série mensal e JPEGs do vídeo, sem depender do Folium."""
    if int(cod_fazenda) != 4:
        return None, None, None
    from gis.timelapse import arquivo_timelapse, envelope, quadros_recortados, serie_fazenda

    video = arquivo_timelapse()
    if video is None:
        return None, None, "Não encontrei `KML/Tailandia.mp4`."
    if envelope(areas) is None:
        return None, None, "O mapa ainda não tem áreas para encaixar o vídeo."
    try:
        mtime = os.path.getmtime(video)
        hectares = round(sum(float(area.get("area_ha") or 0) for area in areas), 2)
        chave_serie = f"timelapse_serie_v2_{cod_fazenda}"
        if st.session_state.get(f"{chave_serie}_ha") != hectares or chave_serie not in st.session_state:
            st.session_state[chave_serie] = serie_fazenda(conn, cod_fazenda, hectares)
            st.session_state[f"{chave_serie}_ha"] = hectares
        serie = st.session_state[chave_serie]

        chave_img = f"timelapse_img_masked_{cod_fazenda}"
        import gis.timelapse as _tl_mod
        _tl_mtime = round(os.path.getmtime(_tl_mod.__file__), 0)
        _cache_key = (mtime, _tl_mtime, len(areas))
        if st.session_state.get(f"{chave_img}_mtime") != _cache_key:
            st.session_state[chave_img] = quadros_recortados(video, areas)
            st.session_state[f"{chave_img}_mtime"] = _cache_key
        imagens = st.session_state[chave_img]
        return serie, imagens, None
    except Exception as exc:
        return None, None, str(exc)


def _url_quadro(imagens: tuple[bytes, ...], indice: int) -> str:
    indice = max(0, min(int(indice), len(imagens) - 1))
    return "data:image/png;base64," + base64.b64encode(imagens[indice]).decode("ascii")


def _timelapse_na_camada(mapa, areas, imagens: tuple[bytes, ...] | None, indice_inicial: int = 0) -> list:
    """Pré-carrega todos os quadros recortados como ImageOverlays no FeatureGroup do Leaflet."""
    if not imagens:
        return []
    from gis.timelapse import bounds_painel, envelope

    caixa = envelope(areas)
    if caixa is None:
        return []
    west, south, east, north = caixa
    bounds = bounds_painel(west, south, east, north)
    grupo = folium.FeatureGroup(name="Timelapse", show=False)
    overlays = []
    total = len(imagens)
    for i in range(total):
        eh_inicial = (i == indice_inicial)
        overlay = ImageOverlay(
            _url_quadro(imagens, i),
            bounds=bounds,
            opacity=0.9 if eh_inicial else 0.0,
            interactive=False,
            cross_origin=False,
            zindex=1,
        )
        overlay.add_to(grupo)
        overlays.append(overlay)
    grupo.add_to(mapa)
    return overlays


def _grafico_timelapse(serie: pd.DataFrame):
    fig = make_subplots(
        rows=2,
        cols=2,
        shared_xaxes=True,
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
        subplot_titles=("Biomassa (t MS/ha)", "Carga (cab/ha)", "UA/ha", "Pressão de pastejo (%)"),
    )
    meses = serie["mes"].tolist()
    fig.add_trace(
        go.Scatter(x=meses, y=serie["biomassa"], mode="lines+markers", fill="tozeroy", name="Biomassa", line=dict(color="#1e3a8a")),
        row=1,
        col=1,
    )
    fig.add_trace(go.Scatter(x=meses, y=serie["carga"], mode="lines+markers", name="Carga", line=dict(color="#14532d")), row=1, col=2)
    fig.add_trace(go.Scatter(x=meses, y=serie["ua_ha"], mode="lines+markers", name="UA/ha", line=dict(color="#86efac")), row=2, col=1)
    fig.add_trace(
        go.Scatter(x=meses, y=serie["pressao_pct"], mode="lines+markers", name="Pressão", line=dict(color="#ea580c")),
        row=2,
        col=2,
    )
    fig.update_layout(
        height=460,
        margin=dict(l=24, r=16, t=40, b=80),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.03)",
    )
    fig.update_xaxes(tickangle=-35, row=2, col=1)
    fig.update_xaxes(tickangle=-35, row=2, col=2)
    st.plotly_chart(fig, use_container_width=True)


def _timelapse_mes_menos(chave_idx: str) -> None:
    st.session_state[chave_idx] = max(0, int(st.session_state.get(chave_idx, 0)) - 1)


def _timelapse_mes_mais(chave_idx: str, limite: int) -> None:
    st.session_state[chave_idx] = min(limite, int(st.session_state.get(chave_idx, 0)) + 1)


def _painel_timelapse(serie: pd.DataFrame, cod_fazenda: int):
    if serie is None or serie.empty:
        return
    idx_key = f"timelapse_idx_{cod_fazenda}"
    limite = len(serie) - 1
    if idx_key not in st.session_state:
        st.session_state[idx_key] = 0

    play_key = f"timelapse_play_{cod_fazenda}"
    vel_key = f"timelapse_vel_{cod_fazenda}"
    if play_key not in st.session_state:
        st.session_state[play_key] = False
    if vel_key not in st.session_state:
        st.session_state[vel_key] = 2.0

    st.markdown(
        """<div style="background:linear-gradient(90deg,#0f172a,#14532d);color:#f8fafc;padding:14px 18px;border-radius:12px;margin:8px 0 12px;">
        <div style="font-size:18px;font-weight:700;">Pasture Watch · Timelapse</div>
        <div style="font-size:12px;opacity:0.9;">Jan/2025 a Ago/2026 · o mês escolhido aqui atualiza o quadro no mapa acima</div>
        </div>""",
        unsafe_allow_html=True,
    )
    c_play, c_pause, c_vel, c_gauge = st.columns([1, 1, 2.2, 1.2])
    with c_play:
        st.button(
            "Reproduzir",
            key=f"tempo_play_{cod_fazenda}",
            use_container_width=True,
            on_click=_timelapse_play_ligar,
            args=(cod_fazenda,),
        )
    with c_pause:
        st.button(
            "Pausar",
            key=f"tempo_pause_{cod_fazenda}",
            use_container_width=True,
            on_click=_timelapse_play_pausar,
            args=(cod_fazenda,),
        )
    estado = "Reproduzindo" if st.session_state[play_key] else "Pausado"
    st.caption(f"**{estado}.** ◀ e ▶ trocam o mês na hora. Reproduzir segue sozinho no intervalo ao lado.")
    with c_vel:
        st.slider(
            "Intervalo entre quadros (segundos)",
            min_value=0.25,
            max_value=8.0,
            step=0.25,
            key=vel_key,
            help="Quanto menor o intervalo, mais rápida a animação.",
        )
    with c_gauge:
        _velocimetro_timelapse(st.session_state[vel_key])

    c_prev, c_slider, c_next = st.columns([0.6, 6.4, 0.6])
    with c_prev:
        st.button(
            "◀",
            key=f"tempo_prev_{cod_fazenda}",
            use_container_width=True,
            on_click=_timelapse_mes_menos,
            args=(idx_key,),
        )
    with c_slider:
        st.slider(
            "Mês do timelapse",
            min_value=0,
            max_value=limite,
            format="%d",
            key=idx_key,
            label_visibility="collapsed",
        )
    with c_next:
        st.button(
            "▶",
            key=f"tempo_next_{cod_fazenda}",
            use_container_width=True,
            on_click=_timelapse_mes_mais,
            args=(idx_key, limite),
        )

    linha = serie.iloc[int(st.session_state[idx_key])]
    st.markdown(f"**{linha['mes']}** · mês {int(st.session_state[idx_key]) + 1} de {len(serie)}")
    if int(linha.get("sem_peso", 0)) > 0:
        st.caption(
            f"Pressão e @ usam só as **{int(linha.com_peso)}** cabeças com pesagem até o dia 1º "
            f"({int(linha.sem_peso)} sem peso não entram no peso total)."
        )

    limites_bio = _limites_timelapse(cod_fazenda, "biomassa")
    limites_carga = _limites_timelapse(cod_fazenda, "carga")
    limites_ua = _limites_timelapse(cod_fazenda, "ua_ha")
    limites_pressao = _limites_timelapse(cod_fazenda, "pressao_pct")

    r1 = st.columns(6)
    with r1[0]:
        _cartao_indicador("Biomassa média", linha.biomassa, "t MS / ha", limites_bio, 2)
    with r1[1]:
        _cartao_indicador("Cabeças", linha.cabecas, "animais ativos", None, 0)
    with r1[2]:
        _cartao_indicador("Total UA", linha.ua, "unidades", None, 2)
    with r1[3]:
        _cartao_indicador("Carga", linha.carga, "cab / ha", limites_carga, 2)
    with r1[4]:
        _cartao_indicador("UA/ha", linha.ua_ha, "UA / ha", limites_ua, 3)
    with r1[5]:
        _cartao_indicador("Pressão", linha.pressao_pct, "% do estoque MS", limites_pressao, 1)

    r2 = st.columns(1)
    with r2[0]:
        _cartao_indicador("Peso total", linha.arrobas, "@ (peso ÷ 30)", None, 1)

    st.caption(
        "Pressão (%) = peso total (kg) ÷ biomassa seca estimada (t MS/ha × ha × 1000) × 100. "
        "UA vem de Tab_categoria.Unidade_Animal por animal presente no mês."
    )

    st.markdown("**Faixas de cor dos indicadores** — ajuste os tetos de cada classe")
    faixas = st.columns(4)
    defs = [
        ("biomassa", "t MS/ha", faixas[0]),
        ("carga", "cab/ha", faixas[1]),
        ("ua_ha", "UA/ha", faixas[2]),
        ("pressao_pct", "% pressão", faixas[3]),
    ]
    for chave, rotulo, coluna in defs:
        with coluna:
            st.caption(rotulo)
            chave_sessao = f"limites_tempo_{chave}_{cod_fazenda}"
            editado = st.data_editor(
                _limites_timelapse(cod_fazenda, chave),
                key=f"editor_limites_{chave}_{cod_fazenda}",
                hide_index=True,
                use_container_width=True,
                column_config={
                    "classe": st.column_config.TextColumn("Classe"),
                    "maximo": st.column_config.NumberColumn("Até", format="%.2f"),
                },
            )
            st.session_state[chave_sessao] = editado
            teto = float(editado["maximo"].max() or 1)
            preview = "".join(
                f'<span style="display:inline-block;width:14%;height:10px;background:{_cor_por_classe(teto * t, editado)}"></span>'
                for t in (0.15, 0.35, 0.55, 0.75, 0.95)
            )
            st.markdown(f'<div style="border-radius:6px;overflow:hidden;">{preview}</div>', unsafe_allow_html=True)

    st.markdown("**Série mensal**")
    _grafico_timelapse(serie)


def _mapa_interativo(conn, store, cod_fazenda: int):
    areas = store.areas(cod_fazenda)
    lines = store.lines(cod_fazenda)
    perimetro = None
    perimetro_id = None
    from gis.timelapse import perimetro_pastos

    uniao = perimetro_pastos(areas)
    if uniao is not None:
        perimetro, hectares_perimetro = uniao
        try:
            perimetro_id = store.salvar_perimetro(cod_fazenda, perimetro, hectares_perimetro)
        except Exception as exc:
            st.caption(f"Não gravei o perímetro da fazenda: {exc}")
    if not areas:
        st.info("Esta fazenda ainda não tem áreas importadas. Use a aba Importar KML.")
        return

    locais = _locais(conn, cod_fazenda)
    por_id = {int(row.id_geo_area): row for row in locais.itertuples(index=False) if pd.notna(row.id_geo_area)}
    contagem = _contagem(conn, cod_fazenda)
    criterio = _criterio_mapa(cod_fazenda)
    quadro = _quadro_indices(areas, por_id, _indices(conn, cod_fazenda))
    st.session_state[f"mapa_indices_{cod_fazenda}"] = quadro.to_dict("records")
    coluna = "ua_ha" if criterio == "UA/ha" else "gpd"
    com_animal = quadro[quadro["cabecas"] > 0] if not quadro.empty else quadro
    baixo, media, alto = _faixa(com_animal[coluna]) if not com_animal.empty else (None, None, None)
    cor_por_area = {}
    if not quadro.empty:
        for row in quadro.itertuples(index=False):
            valor = getattr(row, coluna)
            if row.cabecas <= 0 or valor is None or pd.isna(valor):
                cor_por_area[int(row.geo_id)] = _CINZA_SEM_ANIMAL
            else:
                cor_por_area[int(row.geo_id)] = _hex_indice(valor, baixo, media, alto)
    por_geo = {} if quadro.empty else {int(row.geo_id): row for row in quadro.itertuples(index=False)}

    features_animais = []
    features_biomassa = []
    for area in areas:
        local = por_id.get(int(area["id"]))
        cod_local = "" if local is None else str(local.cod_local)
        nome = "Sem local vinculado" if local is None else f"{str(local.cod_local).strip()} — {local.descricao}"
        info = por_geo.get(int(area["id"]))
        cabecas = 0 if info is None else int(info.cabecas)
        props = {
            "geo_id": int(area["id"]),
            "nome": nome,
            "descricao": "" if local is None else str(local.descricao or ""),
            "area_ha": area["area_ha"],
            "cabecas": cabecas,
            "cod_local": cod_local,
            "peso_medio": "—" if info is None or info.peso_medio is None else info.peso_medio,
            "gpd": "—" if info is None or info.gpd is None else info.gpd,
            "ua_ha": "—" if info is None or info.ua_ha is None else info.ua_ha,
            "dias": "—" if info is None or info.dias is None else info.dias,
            "cor": cor_por_area.get(int(area["id"]), _CINZA_SEM_ANIMAL),
        }
        features_animais.append({"type": "Feature", "properties": props, "geometry": area["geojson"]})
        features_biomassa.append(
            {
                "type": "Feature",
                "properties": {**props, "biomassa": "sem medição"},
                "geometry": area["geojson"],
            }
        )

    serie_tempo = None
    imagens_tempo = None
    erro_tempo = None
    tl_key = f"timelapse_ativo_{cod_fazenda}"
    if int(cod_fazenda) == 4:
        serie_tempo, imagens_tempo, erro_tempo = _preparar_timelapse(conn, cod_fazenda, areas)
        if f"timelapse_vel_{cod_fazenda}" not in st.session_state:
            st.session_state[f"timelapse_vel_{cod_fazenda}"] = 2.0
        # Toggle que controla visibilidade da camada e do painel abaixo do mapa
        timelapse_ativo = st.toggle(
            "Camada Timelapse",
            value=st.session_state.get(tl_key, False),
            key=tl_key,
            help="Habilita/desabilita o Pasture Watch · Timelapse no mapa e os controles abaixo.",
        )
    else:
        timelapse_ativo = False

    mapa = _base_map(features_animais)
    indice_tempo = int(st.session_state.get(f"timelapse_idx_{cod_fazenda}", 0))
    overlays_tl = []
    if int(cod_fazenda) == 4 and imagens_tempo and timelapse_ativo:
        try:
            overlays_tl = _timelapse_na_camada(mapa, areas, imagens_tempo, indice_inicial=indice_tempo)
        except Exception as exc:
            erro_tempo = erro_tempo or str(exc)
    folium.GeoJson(
        {"type": "FeatureCollection", "features": features_animais},
        name="Animais",
        style_function=_estilo_animais,
        highlight_function=lambda _f: {"weight": 3, "color": "#be185d", "fillOpacity": 0.35},
        tooltip=folium.GeoJsonTooltip(
            fields=["nome", "area_ha", "cabecas", "peso_medio", "dias", "gpd", "ua_ha"],
            aliases=["Local", "Área (ha)", "Cabeças", "Peso médio (kg)", "Dias da pesagem", "GPD", "UA/ha"],
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
    rotulos = folium.FeatureGroup(name="Rótulos dos locais", show=True)
    for feature in features_animais:
        codigo = str(feature["properties"].get("cod_local") or "").strip()
        if not codigo:
            continue
        ponto = shape(feature["geometry"]).representative_point()
        _rotulo_no_mapa(rotulos, ponto.y, ponto.x, codigo, feature["properties"].get("descricao") or "")
    rotulos.add_to(mapa)
    _RotulosPorZoom().add_to(mapa)
    folium.LayerControl(collapsed=False).add_to(mapa)
    _PersistenciaTimelapse(int(cod_fazenda), timelapse_ativo, overlays_tl, indice_inicial=indice_tempo).add_to(mapa)

    if media is None:
        st.caption("Ainda não há pesagem nos pastos com animal. As áreas ficam cinza.")
    else:
        texto_media = _numero(media, 3)
        st.caption(
            f"Média geral de {criterio}: {texto_media}. "
            "Verde escuro é o maior índice, palha fica na média e laranja amarronzado é o menor. "
            "Pasto sem animal ativo permanece cinza."
        )
    if int(cod_fazenda) == 4 and timelapse_ativo:
        components.html(
            f"""
            <script>
                (function() {{
                    var idx = {indice_tempo};
                    try {{
                        localStorage.setItem('esopo_tl_idx_{cod_fazenda}', String(idx));
                        if (window.BroadcastChannel) {{
                            var bc = new BroadcastChannel('esopo_tl_channel_{cod_fazenda}');
                            bc.postMessage({{type: 'FRAME_CHANGE', idx: idx}});
                            bc.close();
                        }}
                    }} catch(e) {{}}
                }})();
            </script>
            """,
            height=0,
            width=0,
        )
    clique = _desenhar(mapa, f"mapa-folium-{cod_fazenda}")
    if perimetro_id is not None:
        st.caption(
            f"Perímetro externo dos pastos gravado em **Esopo_geo_area**, id **{perimetro_id}** "
            "(situação `perimetro`). No local Fazenda Tailandia, relacione `Tab_local.id_geo_area` a este id."
        )
    if int(cod_fazenda) != 4:
        st.info("O **Pasture Watch (timelapse)** está liberado na **Fazenda Tailandia (4)**. Escolha essa opção em *Fazenda do mapa*.")
    elif not timelapse_ativo:
        pass  # camada desabilitada — painel oculto
    elif serie_tempo is not None:
        st.caption("Ligue a camada **Timelapse** no quadro de camadas do mapa. O mês é o controle abaixo.")
        _painel_timelapse(serie_tempo, cod_fazenda)
        st.fragment(
            _autoplay_tick,
            run_every=float(st.session_state.get(f"timelapse_vel_{cod_fazenda}", 2.0)),
        )(cod_fazenda, len(serie_tempo) - 1)
    elif erro_tempo:
        st.warning(f"Timelapse indisponível: {erro_tempo}")
    _tabela_indices(quadro, criterio, media)
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
    rotulos_prev = folium.FeatureGroup(name="Rótulos dos locais", show=True)
    for poly in prev["polygons"]:
        codigo = (poly.get("cod_local") or poly.get("nome_kml") or "").strip()
        if not codigo:
            continue
        ponto = shape(poly["geojson"]).representative_point()
        _rotulo_no_mapa(rotulos_prev, ponto.y, ponto.x, codigo, poly.get("descricao") or "")
    rotulos_prev.add_to(preview)
    _RotulosPorZoom().add_to(preview)
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
        zoom = 14
    else:
        centro = [sum(lats) / len(lats), sum(lons) / len(lons)]
        zoom = 14
    mapa = folium.Map(location=list(centro), zoom_start=int(zoom), tiles=None, max_zoom=22)
    if lats:
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


def _rotulo_no_mapa(destino, lat: float, lon: float, codigo: str, descricao: str):
    codigo_html = html.escape(str(codigo).strip())
    descricao_html = html.escape(str(descricao or "").strip())
    folium.Marker(
        location=[lat, lon],
        interactive=False,
        icon=folium.DivIcon(
            icon_size=(160, 40),
            icon_anchor=(80, 20),
            html=(
                '<div class="esopo-mapa-rotulo" style="pointer-events:none;text-align:center;line-height:1.1;'
                'text-shadow:0 1px 2px #000,0 0 4px #000;white-space:nowrap;">'
                f'<div class="rotulo-cod" style="font-size:14px;font-weight:700;color:#fff;">{codigo_html}</div>'
                f'<div class="rotulo-desc" style="display:none;font-size:10px;font-weight:500;color:#e2e8f0;">{descricao_html}</div>'
                "</div>"
            ),
        ),
    ).add_to(destino)


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
    # Centro e zoom ficam no navegador. Devolvê-los recriava o mapa e piscava a tela.
    saida = st_folium(
        mapa,
        key=key,
        height=680,
        use_container_width=True,
        returned_objects=["last_object_clicked"],
    )
    return (saida or {}).get("last_object_clicked") or {}


def _numero(valor, casas: int) -> str:
    return f"{float(valor):.{casas}f}".replace(".", ",")


def _tabela_indices(quadro: pd.DataFrame, criterio: str, media):
    st.markdown(f"**Índices da camada Animais** — o mapa está colorido por {criterio}")
    if quadro.empty or quadro["cabecas"].sum() == 0:
        st.info("Nenhum local vinculado tem animal ativo.")
        return
    coluna = "ua_ha" if criterio == "UA/ha" else "gpd"
    visao = quadro[quadro["cabecas"] > 0].copy()
    visao["vs_media"] = None if media is None else (visao[coluna] - float(media)).round(3)
    visao = visao.sort_values(coluna, ascending=False, na_position="last")
    st.dataframe(
        visao[
            ["local", "ha", "cabecas", "peso_medio", "peso_total", "dias", "gpd", "ua_ha", "vs_media"]
        ],
        hide_index=True,
        use_container_width=True,
        column_config={
            "local": st.column_config.TextColumn("Local"),
            "ha": st.column_config.NumberColumn("Hectares", format="%.2f"),
            "cabecas": st.column_config.NumberColumn("Cabeças"),
            "peso_medio": st.column_config.NumberColumn("Peso médio (kg)", format="%.1f"),
            "peso_total": st.column_config.NumberColumn("Peso total (kg)", format="%.1f"),
            "dias": st.column_config.NumberColumn("Dias da pesagem", format="%.0f"),
            "gpd": st.column_config.NumberColumn("GPD médio", format="%.3f"),
            "ua_ha": st.column_config.NumberColumn("UA/ha", format="%.3f"),
            "vs_media": st.column_config.NumberColumn(f"vs média de {criterio}", format="%.3f"),
        },
    )
    st.caption(
        "UA/ha = (peso total da última pesagem ÷ 450 kg) ÷ hectares da área no mapa. "
        "GPD médio e os dias são da última pesagem de cada animal até hoje. "
        "A média geral usa só os pastos com animal ativo."
    )


def _estilo_animais(feature):
    cor = feature["properties"].get("cor") or _CINZA_SEM_ANIMAL
    return {
        "fillColor": cor,
        "color": "#334155" if cor == _CINZA_SEM_ANIMAL else "#14532d",
        "weight": 1.6,
        "fillOpacity": 0.28 if cor == _CINZA_SEM_ANIMAL else 0.62,
    }


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

