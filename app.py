# app_costeo_cemento_v16_pricing_toneladas.py
# Dashboard gerencial de costeo de cemento - v20 productos parametrizables desde Excel
# Fuente: Excel con hoja Consolidado y, opcionalmente, Metas Gerenciales

from __future__ import annotations

import io
import unicodedata
from dataclasses import dataclass
from typing import Iterable, Optional
from urllib.parse import quote
from html import escape

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Kolcem · Buenos Cimientos",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

import plotly.io as pio

# ── Enterprise dark palette ──────────────────────────────
ENTERPRISE_PALETTE = ["#E8650A","#F5A623","#2DBD6E","#60A5FA","#F472B6","#F59E0B","#A78BFA"]
POSITIVE_GREEN = "#2DBD6E"
WARNING_AMBER  = "#F59E0B"
NEGATIVE_RED   = "#FF4059"
NEUTRAL_SLATE  = "#94A3B8"

px.defaults.color_discrete_sequence = ENTERPRISE_PALETTE

# ── Custom Plotly dark template ──────────────────────────
_DARK_BG      = "rgba(0,0,0,0)"
_CARD_BG      = "rgba(255,255,255,0.03)"
_GRID_COLOR   = "rgba(255,255,255,0.06)"
_LINE_COLOR   = "rgba(255,255,255,0.1)"
_FONT_MAIN    = "DM Sans, sans-serif"
_FONT_TITLE   = "Sora, sans-serif"
_TEXT_PRI     = "#E2E8F0"
_TEXT_SEC     = "#94A3B8"

pio.templates["kolcem_dark"] = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor=_DARK_BG,
        plot_bgcolor=_CARD_BG,
        font=dict(family=_FONT_MAIN, color=_TEXT_SEC, size=12),
        title=dict(font=dict(family=_FONT_TITLE, color=_TEXT_PRI, size=14), x=0.0, pad=dict(l=4, t=4)),
        xaxis=dict(gridcolor=_GRID_COLOR, linecolor=_LINE_COLOR, tickcolor=_LINE_COLOR,
                   zerolinecolor=_LINE_COLOR, tickfont=dict(color=_TEXT_SEC)),
        yaxis=dict(gridcolor=_GRID_COLOR, linecolor=_LINE_COLOR, tickcolor=_LINE_COLOR,
                   zerolinecolor=_LINE_COLOR, tickfont=dict(color=_TEXT_SEC)),
        legend=dict(bgcolor="rgba(255,255,255,0.04)", bordercolor="rgba(255,255,255,0.08)",
                    borderwidth=1, font=dict(color=_TEXT_SEC)),
        colorway=ENTERPRISE_PALETTE,
        hoverlabel=dict(bgcolor="#1E2A3A", bordercolor="#E8650A", font=dict(color=_TEXT_PRI)),
        margin=dict(l=40, r=40, t=55, b=50),
    )
)
pio.templates.default = "kolcem_dark"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Space+Mono:wght@400;700&display=swap');

:root {
    --bg-primary:   #080D18;
    --bg-secondary: #0D1426;
    --bg-card:      rgba(255,255,255,0.04);
    --border-brand: rgba(232,101,10,0.22);
    --border-teal:  rgba(232,101,10,0.22);
    --border-sub:   rgba(255,255,255,0.07);
    --brand:        #E8650A;
    --gold:         #F5A623;
    --green:        #2DBD6E;
    --red:          #FF4059;
    --amber:        #F59E0B;
    --text-pri:     #E2E8F0;
    --text-sec:     #94A3B8;
    --text-muted:   #64748B;
    --shadow-card:  0 4px 24px rgba(0,0,0,0.45), 0 1px 4px rgba(0,0,0,0.3);
    --r-card:       18px;
}

/* ── Base ─────────────────────────────── */
.stApp {
    background: #080D18;
    background-image:
        radial-gradient(ellipse at 12% 8%,  rgba(232,101,10,0.07) 0%, transparent 45%),
        radial-gradient(ellipse at 88% 92%, rgba(245,166,35,0.05) 0%, transparent 45%);
    color: var(--text-pri);
}

/* ── Sidebar ──────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#0A1020 0%,#0D1528 100%) !important;
    border-right: 1px solid var(--border-brand) !important;
}
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] label { color: var(--text-sec) !important; }
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: var(--brand) !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.72rem !important; font-weight:700 !important;
    letter-spacing:0.12em !important; text-transform:uppercase !important;
}
section[data-testid="stSidebar"] hr { border-color: rgba(232,101,10,0.15) !important; }
section[data-testid="stSidebar"] .stFileUploader {
    border: 1px dashed rgba(232,101,10,0.35) !important;
    border-radius: 14px !important;
    background: rgba(232,101,10,0.05) !important;
    padding: 8px !important;
}

/* ── Layout ───────────────────────────── */
.block-container { padding-top:2rem !important; max-width:1580px !important; }

/* ── Typography ───────────────────────── */
html,body,[class*="css"],.stMarkdown { font-family:'DM Sans',sans-serif !important; }
h1,h2,h3,h4 { font-family:'Sora',sans-serif !important; color:var(--text-pri) !important; letter-spacing:-0.02em !important; }
.stMarkdown h3 {
    font-size:0.78rem !important; font-weight:700 !important;
    color:var(--text-sec) !important; text-transform:uppercase !important;
    letter-spacing:0.08em !important;
    border-bottom:1px solid rgba(255,255,255,0.06) !important;
    padding-bottom:8px !important; margin-bottom:14px !important;
}

/* ── Hero ─────────────────────────────── */
.hero-card {
    background: linear-gradient(135deg,rgba(13,20,38,0.97) 0%,rgba(8,13,24,0.99) 100%);
    border: 1px solid rgba(232,101,10,0.25);
    border-radius: 24px; padding: 34px 40px; margin-bottom: 24px;
    position: relative; overflow: hidden;
    box-shadow: 0 0 70px rgba(232,101,10,0.08), 0 24px 60px rgba(0,0,0,0.6);
}
.hero-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:1px;
    background: linear-gradient(90deg,transparent,#E8650A 40%,#F5A623 70%,transparent);
}
.hero-card::after {
    content:''; position:absolute; top:-100px; right:-100px;
    width:380px; height:380px;
    background: radial-gradient(circle,rgba(232,101,10,0.07) 0%,transparent 65%);
    pointer-events:none;
}
.hero-badge {
    display:inline-flex; align-items:center; gap:7px;
    background:rgba(232,101,10,0.1); border:1px solid rgba(232,101,10,0.32);
    border-radius:999px; padding:4px 14px;
    font-family:'Sora',sans-serif; font-size:0.7rem; font-weight:700;
    letter-spacing:0.12em; text-transform:uppercase; color:#E8650A;
    margin-bottom:16px;
}
.hero-dot {
    width:7px; height:7px; border-radius:50%; background:#00C47A;
    animation:_pulse 2.2s ease-in-out infinite;
}
@keyframes _pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.4;transform:scale(.7)} }
.hero-title {
    font-family:'Sora',sans-serif;
    font-size:clamp(1.75rem,2.8vw,2.7rem); font-weight:800;
    letter-spacing:-0.045em; line-height:1.05;
    background:linear-gradient(135deg,#F5F0EB 20%,#E8650A 60%,#F5A623 100%);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
    margin-bottom:10px;
}
.hero-subtitle {
    color:var(--text-sec); font-size:0.92rem; font-weight:500;
    font-family:'DM Sans',sans-serif;
}

/* ── KPI Cards ────────────────────────── */
.kpi-card {
    border-radius:var(--r-card); padding:20px 20px 15px;
    margin-bottom:16px; min-height:130px;
    display:flex; flex-direction:column; justify-content:space-between;
    position:relative; overflow:hidden;
    transition:transform .18s ease, box-shadow .18s ease;
}
.kpi-card:hover { transform:translateY(-2px); }
.kpi-card::before {
    content:''; position:absolute; top:0; left:0;
    width:3px; height:100%;
}
.kpi-neutral {
    background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
    box-shadow:var(--shadow-card);
}
.kpi-neutral::before { background:#64748B; }
.kpi-green {
    background:linear-gradient(135deg,rgba(45,189,110,0.09) 0%,rgba(45,189,110,0.04) 100%);
    border:1px solid rgba(45,189,110,0.22);
    box-shadow:var(--shadow-card),0 0 24px rgba(45,189,110,0.09);
}
.kpi-green::before { background:linear-gradient(180deg,#2DBD6E,#4AE898); }
.kpi-yellow {
    background:linear-gradient(135deg,rgba(245,158,11,0.09) 0%,rgba(245,158,11,0.04) 100%);
    border:1px solid rgba(245,158,11,0.22);
    box-shadow:var(--shadow-card),0 0 24px rgba(245,158,11,0.07);
}
.kpi-yellow::before { background:linear-gradient(180deg,#F59E0B,#FCD34D); }
.kpi-red {
    background:linear-gradient(135deg,rgba(255,64,89,0.11) 0%,rgba(255,64,89,0.05) 100%);
    border:1px solid rgba(255,64,89,0.28);
    box-shadow:var(--shadow-card),0 0 28px rgba(255,64,89,0.1);
}
.kpi-red::before { background:linear-gradient(180deg,#FF4059,#FF6B9D); }
.kpi-label {
    color:var(--text-sec); font-family:'DM Sans',sans-serif;
    font-size:0.72rem; font-weight:600; letter-spacing:0.06em;
    text-transform:uppercase; margin-bottom:10px; line-height:1.3;
}
.kpi-value {
    font-family:'Space Mono',monospace;
    font-size:clamp(0.96rem,1.18vw,1.34rem);
    font-weight:700; letter-spacing:-0.03em; line-height:1.08;
    font-variant-numeric:tabular-nums;
    white-space:normal;
    overflow-wrap:anywhere;
    word-break:break-word;
    max-width:100%;
}
.kpi-value.kpi-value-md { font-size:clamp(0.90rem,1.08vw,1.22rem); }
.kpi-value.kpi-value-sm { font-size:clamp(0.82rem,0.98vw,1.08rem); }
.kpi-value.kpi-value-xs { font-size:clamp(0.74rem,0.90vw,0.96rem); }
.kpi-green  .kpi-value { color:#2DBD6E; }
.kpi-yellow .kpi-value { color:#F59E0B; }
.kpi-red    .kpi-value { color:#FF4059; }
.kpi-neutral .kpi-value{ color:var(--text-pri); }
.kpi-delta {
    margin-top:8px; font-family:'DM Sans',sans-serif;
    font-size:0.74rem; font-weight:600; line-height:1.3;
}
.kpi-green  .kpi-delta  { color:#2DBD6E; }
.kpi-yellow .kpi-delta  { color:#F59E0B; }
.kpi-red    .kpi-delta  { color:#FF4059; }
.kpi-neutral .kpi-delta { color:var(--text-sec); }
.kpi-help { margin-top:4px; color:var(--text-muted); font-size:0.72rem; line-height:1.3; }

/* ── Tabs ─────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap:4px !important; background:rgba(255,255,255,0.03) !important;
    padding:6px !important; border-radius:16px !important;
    border:1px solid rgba(255,255,255,0.07) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius:12px !important; padding:9px 13px !important;
    color:var(--text-sec) !important; font-family:'DM Sans',sans-serif !important;
    font-weight:600 !important; font-size:0.82rem !important;
    transition:all .2s ease !important;
}
.stTabs [data-baseweb="tab"]:hover {
    background:rgba(232,101,10,0.08) !important; color:var(--brand) !important;
}
.stTabs [aria-selected="true"] {
    background:linear-gradient(135deg,#E8650A,#C94E00) !important;
    color:#FFFFFF !important; font-weight:700 !important;
    box-shadow:0 4px 14px rgba(232,101,10,0.4) !important;
}

/* ── DataFrames ───────────────────────── */
div[data-testid="stDataFrame"] {
    border-radius:14px !important; overflow:hidden;
    border:1px solid rgba(255,255,255,0.07) !important;
    box-shadow:var(--shadow-card);
}

/* ── Metrics ──────────────────────────── */
div[data-testid="stMetric"] {
    background:var(--bg-card); border:1px solid var(--border-sub);
    border-radius:var(--r-card); padding:16px 18px; box-shadow:var(--shadow-card);
}

/* ── Buttons ──────────────────────────── */
.stButton > button, .stDownloadButton > button {
    background:linear-gradient(135deg,#E8650A,#C94E00) !important;
    color:#FFFFFF !important; border:none !important;
    border-radius:999px !important; font-family:'DM Sans',sans-serif !important;
    font-weight:700 !important; letter-spacing:0.03em !important;
    box-shadow:0 4px 16px rgba(232,101,10,0.3) !important;
    transition:all .2s ease !important;
}
.stButton > button:hover, .stDownloadButton > button:hover {
    transform:translateY(-1px) !important;
    box-shadow:0 6px 22px rgba(232,101,10,0.4) !important;
}

/* ── Alert/info boxes ─────────────────── */
div[data-testid="stInfo"] {
    background:rgba(232,101,10,0.06) !important;
    border-left:4px solid #E8650A !important; border-radius:12px !important;
    color:var(--text-sec) !important;
}
div[data-testid="stWarning"] {
    background:rgba(245,158,11,0.07) !important;
    border-left:4px solid #F59E0B !important; border-radius:12px !important;
}
div[data-testid="stError"] {
    background:rgba(255,64,89,0.07) !important;
    border-left:4px solid #FF4059 !important; border-radius:12px !important;
}
div[data-testid="stSuccess"] {
    background:rgba(45,189,110,0.07) !important;
    border-left:4px solid #2DBD6E !important; border-radius:12px !important;
}

/* ── Misc ─────────────────────────────── */
.calm-note {
    background:rgba(232,101,10,0.06); border-left:4px solid rgba(232,101,10,0.45);
    border-radius:12px; padding:12px 16px; color:var(--text-sec);
    font-size:0.84rem; margin:10px 0 4px;
}
.stTextArea textarea {
    background:rgba(255,255,255,0.04) !important;
    border-color:rgba(255,255,255,0.1) !important;
    color:var(--text-sec) !important; border-radius:12px !important;
    font-family:'Space Mono',monospace !important; font-size:0.78rem !important;
}
.stCaption { color:var(--text-muted) !important; font-size:0.8rem !important; }
hr, .stDivider { border-color:rgba(255,255,255,0.07) !important; }
::-webkit-scrollbar { width:5px; height:5px; }
::-webkit-scrollbar-track { background:rgba(255,255,255,0.02); }
::-webkit-scrollbar-thumb { background:rgba(232,101,10,0.32); border-radius:3px; }; border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:rgba(232,101,10,0.52); }; }
</style>
""", unsafe_allow_html=True)


MESES = {
    "Enero": 1,
    "Febrero": 2,
    "Marzo": 3,
    "Abril": 4,
    "Mayo": 5,
    "Junio": 6,
    "Julio": 7,
    "Agosto": 8,
    "Septiembre": 9,
    "Octubre": 10,
    "Noviembre": 11,
    "Diciembre": 12,
}
MESES_INV = {v: k for k, v in MESES.items()}

INDICES_GRANEL = ["C MP UG", "C MO UG", "C CIF UG"]
INDICES_EMPACADO = ["C MP EMP", "C MO EMP", "C CIF EMP"]
INDICES_GASTOS_COMERCIALES_BASE = ["C MO ADM", "C CIF ADM", "C MO VEN", "C CIF VEN", "C FIN", "C IMP"]
INDICES_IMPUESTOS_OPCIONALES = ["C IMP REN", "C IMP PATR"]
INDICES_GASTOS_COMERCIALES = INDICES_GASTOS_COMERCIALES_BASE.copy()
INDICES_COSTO_TOTAL = INDICES_EMPACADO + INDICES_GASTOS_COMERCIALES

OBS_KG_GRANEL = "KG PRODUCIDOS Q"
OBS_UND_EMPACADO = "UND PRODUCIDAS Q"
OBS_CEMENTO_GRANEL_TRANSFERIDO = "CEMENTO A GRANEL DE USO GENERAL"
OBS_PRECIO_BOLSA = "PRECIO PROMEDIO POR BOLSA 50 KG"


@dataclass(frozen=True)
class ProductoCosteo:
    key: str
    nombre: str
    nombre_corto: str
    granel_producto: str
    empacado_producto: str
    precio_producto: str
    gastos_producto: str
    utilidad_producto: str
    peso_bolsa_kg: float
    indices_granel: list[str]
    indices_empacado: list[str]
    indices_gastos_base: list[str]
    indices_admin: list[str]
    indices_ventas: list[str]
    indices_fin: list[str]
    indices_imp_base: list[str]
    obs_cemento_transferido: str
    obs_cantidad_vendida: str
    obs_kg_granel: str = "KG PRODUCIDOS Q"
    obs_und_empacado: str = "UND PRODUCIDAS Q"
    obs_precio_bolsa: str = "PRECIO PROMEDIO POR BOLSA 50 KG"
    modo_gastos: str = "indices"  # indices | subtotales_producto
    obs_gastos_total: str = "GASTOS"
    obs_admin: str = "GASTOS ADMINISTRATIVOS"
    obs_ventas: str = "GASTOS DE VENTA"
    obs_financiero: str = "GATOS FINANCIEROS|GASTOS FINANCIEROS"


PRODUCTOS_COSTEO_DEFAULT: dict[str, ProductoCosteo] = {
    "UG_50": ProductoCosteo(
        key="UG_50",
        nombre="Cemento UG empacado 50 kg",
        nombre_corto="UG 50 kg",
        granel_producto="Granel de Uso General (2841)",
        empacado_producto="Empacado UG 50KG (2843)",
        precio_producto="Precio Final",
        gastos_producto="Gastos Administrativos y de Venta",
        utilidad_producto="Utilidad Bruta por Kilo de Cemento Vendido",
        peso_bolsa_kg=50.0,
        indices_granel=["C MP UG", "C MO UG", "C CIF UG"],
        indices_empacado=["C MP EMP", "C MO EMP", "C CIF EMP"],
        indices_gastos_base=["C MO ADM", "C CIF ADM", "C MO VEN", "C CIF VEN", "C FIN", "C IMP"],
        indices_admin=["C MO ADM", "C CIF ADM"],
        indices_ventas=["C MO VEN", "C CIF VEN"],
        indices_fin=["C FIN"],
        indices_imp_base=["C IMP"],
        obs_cemento_transferido="CEMENTO A GRANEL DE USO GENERAL",
        obs_cantidad_vendida="CEMENTO KOLCEM UG 50 KG",
        obs_kg_granel="KG PRODUCIDOS Q",
        obs_und_empacado="UND PRODUCIDAS Q",
        obs_precio_bolsa="PRECIO PROMEDIO POR BOLSA 50 KG",
        modo_gastos="indices",
    ),
    "ART_42_5": ProductoCosteo(
        key="ART_42_5",
        nombre="Cemento ART estructural empacado 42.5 kg",
        nombre_corto="ART 42.5 kg",
        granel_producto="Cemento Granel ART (3645)",
        empacado_producto="Cemento Empacado ART 42.5 (4223)",
        precio_producto="Precio Final ART",
        gastos_producto="Gastos Administrativos y de Venta ART",
        utilidad_producto="Utilidad Bruta por Kilo de Cemento Vendido ART",
        peso_bolsa_kg=42.5,
        indices_granel=["C MP ART GRN", "C MO ART GRN", "C CIF ART GRN"],
        indices_empacado=["C MP ART EMP", "C MO ART EMP", "C CIF ART EMP"],
        indices_gastos_base=["C ADM Y VEN ART EMP", "C FIN"],
        indices_admin=["C ADM Y VEN ART EMP"],
        indices_ventas=["C ADM Y VEN ART EMP"],
        indices_fin=["C FIN"],
        indices_imp_base=[],
        obs_cemento_transferido="CEMENTO A GRANEL ART USO ESTRUCTURAL",
        obs_cantidad_vendida="CEMENTO KOLCEM ART 42.5 KG",
        obs_kg_granel="KG PRODUCIDOS Q",
        obs_und_empacado="UND PRODUCIDAS Q",
        obs_precio_bolsa="PRECIO PROMEDIO POR BOLSA 42,5 KG",
        modo_gastos="subtotales_producto",
        obs_gastos_total="GASTOS",
        obs_admin="GASTOS ADMINISTRATIVOS",
        obs_ventas="GASTOS DE VENTA",
        obs_financiero="GATOS FINANCIEROS|GASTOS FINANCIEROS",
    ),
}

# Se reemplaza después de leer el Excel, si existe hoja "Parametros Productos".
PRODUCTOS_COSTEO: dict[str, ProductoCosteo] = PRODUCTOS_COSTEO_DEFAULT.copy()


def _split_param_list(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    for sep in ["\n", ";", ","]:
        text = text.replace(sep, "|")
    return [x.strip() for x in text.split("|") if x and x.strip()]


def _truthy_excel(value: object) -> bool:
    txt = norm_text(value)
    return txt in {"SI", "SÍ", "YES", "TRUE", "1", "ACTIVO", "X"}


def _param_get(row: pd.Series, aliases: list[str], default: object = "") -> object:
    col_map = {norm_text(c): c for c in row.index}
    for alias in aliases:
        c = col_map.get(norm_text(alias))
        if c is not None:
            val = row.get(c)
            if val is not None and not (isinstance(val, float) and pd.isna(val)):
                return val
    return default


def construir_productos_desde_parametros(parametros_df: pd.DataFrame) -> dict[str, ProductoCosteo]:
    """Lee la hoja 'Parametros Productos' del Excel y construye el catálogo dinámico.

    La fila queda bajo control del negocio: producto, presentación, índices, productos contables
    y observaciones críticas. Si la hoja no existe o tiene errores, se conserva el catálogo
    por defecto para no bloquear la operación.
    """
    if parametros_df is None or parametros_df.empty:
        return {}

    productos: dict[str, ProductoCosteo] = {}
    for _, row in parametros_df.iterrows():
        if not _truthy_excel(_param_get(row, ["Activo"], "Sí")):
            continue
        key = str(_param_get(row, ["Key", "ProductoKey", "Producto key"], "")).strip()
        if not key:
            continue
        base = PRODUCTOS_COSTEO_DEFAULT.get(key)

        def get_txt(aliases: list[str], attr: str | None = None, default: str = "") -> str:
            fallback = getattr(base, attr, default) if base is not None and attr else default
            return str(_param_get(row, aliases, fallback)).strip()

        def get_list(aliases: list[str], attr: str | None = None) -> list[str]:
            fallback = getattr(base, attr, []) if base is not None and attr else []
            raw = _param_get(row, aliases, "|".join(fallback) if fallback else "")
            parsed = _split_param_list(raw)
            return parsed if parsed else list(fallback)

        peso_raw = _param_get(row, ["Kg bolsa", "Peso bolsa kg", "Presentacion kg", "Presentación kg"], getattr(base, "peso_bolsa_kg", 50.0) if base else 50.0)
        peso = parse_valor(peso_raw)
        if peso <= 0:
            peso = float(getattr(base, "peso_bolsa_kg", 50.0) if base else 50.0)

        try:
            productos[key] = ProductoCosteo(
                key=key,
                nombre=get_txt(["Producto dashboard", "Producto", "Nombre"], "nombre", key),
                nombre_corto=get_txt(["Nombre corto", "Corto"], "nombre_corto", key),
                granel_producto=get_txt(["Producto granel", "Producción granel", "Produccion granel"], "granel_producto"),
                empacado_producto=get_txt(["Producto empacado", "Producción empacado", "Produccion empacado"], "empacado_producto"),
                precio_producto=get_txt(["Producto precio", "Precio producto"], "precio_producto"),
                gastos_producto=get_txt(["Producto gastos", "Gastos producto"], "gastos_producto"),
                utilidad_producto=get_txt(["Producto utilidad", "Utilidad producto"], "utilidad_producto"),
                peso_bolsa_kg=float(peso),
                indices_granel=get_list(["Indices granel", "Índices granel"], "indices_granel"),
                indices_empacado=get_list(["Indices empacado", "Índices empacado"], "indices_empacado"),
                indices_gastos_base=get_list(["Indices gastos base", "Índices gastos base", "Indices gastos"], "indices_gastos_base"),
                indices_admin=get_list(["Indices administración", "Indices administracion", "Índices administración", "Indices admin"], "indices_admin"),
                indices_ventas=get_list(["Indices ventas", "Índices ventas"], "indices_ventas"),
                indices_fin=get_list(["Indices financieros", "Índices financieros", "Indices fin"], "indices_fin"),
                indices_imp_base=get_list(["Indices impuestos base", "Índices impuestos base", "Indices imp base"], "indices_imp_base"),
                obs_cemento_transferido=get_txt(["Obs cemento transferido", "Observación cemento transferido", "Observacion cemento transferido"], "obs_cemento_transferido"),
                obs_cantidad_vendida=get_txt(["Obs cantidad vendida", "Observación cantidad vendida", "Observacion cantidad vendida"], "obs_cantidad_vendida"),
                obs_kg_granel=get_txt(["Obs kg granel", "Observación kg granel", "Observacion kg granel"], "obs_kg_granel", "KG PRODUCIDOS Q"),
                obs_und_empacado=get_txt(["Obs und empacado", "Observación und empacado", "Observacion und empacado"], "obs_und_empacado", "UND PRODUCIDAS Q"),
                obs_precio_bolsa=get_txt(["Obs precio bolsa", "Observación precio bolsa", "Observacion precio bolsa"], "obs_precio_bolsa", "PRECIO PROMEDIO POR BOLSA 50 KG"),
                modo_gastos=get_txt(["Modo gastos", "Modo de gastos"], "modo_gastos", "indices"),
                obs_gastos_total=get_txt(["Obs gastos total", "Observación gastos total", "Observacion gastos total"], "obs_gastos_total", "GASTOS"),
                obs_admin=get_txt(["Obs administración", "Obs administracion", "Observación administración", "Observacion administracion"], "obs_admin", "GASTOS ADMINISTRATIVOS"),
                obs_ventas=get_txt(["Obs ventas", "Observación ventas", "Observacion ventas"], "obs_ventas", "GASTOS DE VENTA"),
                obs_financiero=get_txt(["Obs financiero", "Observación financiero", "Observacion financiero"], "obs_financiero", "GATOS FINANCIEROS|GASTOS FINANCIEROS"),
            )
        except Exception:
            # Si una fila está mal, no se cae todo el dashboard.
            continue
    return productos


def producto_disponible(df_in: pd.DataFrame, producto: ProductoCosteo) -> bool:
    if df_in is None or df_in.empty or "Prod_norm" not in df_in.columns:
        return False
    prod_norm = df_in["Prod_norm"]
    claves = [producto.granel_producto, producto.empacado_producto, producto.precio_producto, producto.gastos_producto]
    claves_norm = {norm_text(x) for x in claves if str(x).strip()}
    return bool(prod_norm.isin(claves_norm).any())


def filtrar_producto_costeo(df_in: pd.DataFrame, producto: ProductoCosteo) -> pd.DataFrame:
    """Filtra Consolidado al producto seleccionado sin perder precio, gastos ni extraordinarios.

    La configuración viene de Excel. Esto evita mezclar cantidades, precios y costos entre
    productos con nombres de observación repetidos, por ejemplo UND PRODUCIDAS Q.
    """
    if df_in is None or df_in.empty:
        return df_in.copy()
    claves = {
        norm_text(producto.granel_producto),
        norm_text(producto.empacado_producto),
        norm_text(producto.precio_producto),
        norm_text(producto.gastos_producto),
        norm_text(producto.utilidad_producto),
        norm_text("Gastos ExtraOrdinarios"),
        norm_text("Cantidades Vendidas"),
    }
    claves = {x for x in claves if x}
    return df_in[df_in["Prod_norm"].isin(claves)].copy()

# ------------------------------------------------------------
# Utilidades de texto, números y formato
# ------------------------------------------------------------

def norm_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value)
    text = text.replace("\xa0", " ").replace(" ", " ")
    for dash in ["‐", "‑", "‒", "–", "—", "−"]:
        text = text.replace(dash, "-")
    text = " ".join(text.strip().upper().split())
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text


def parse_valor(value: object) -> float:
    """Convierte números desde Excel aunque vengan como texto colombiano.

    Soporta: 1.234.567,89 | $ 1.234.567,89 | (1.234) | guiones | espacios invisibles.
    """
    if value is None or pd.isna(value):
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        return 0.0 if pd.isna(value) else float(value)
    text = str(value).replace("\xa0", " ").replace(" ", " ").strip()
    text = text.replace("$", "").replace("COP", "").replace("cop", "").strip()
    if text in {"", "-", "–", "—"}:
        return 0.0
    neg = False
    if text.startswith("(") and text.endswith(")"):
        neg = True
        text = text[1:-1].strip()
    text = "".join(text.split())
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        out = float(text)
    except Exception:
        return 0.0
    return -out if neg else out


def money(v: float) -> str:
    if v is None or pd.isna(v):
        return "$0,00"
    return f"${v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(v: float, decimals: int = 2) -> str:
    if v is None or pd.isna(v):
        return f"{0:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{v:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float) -> str:
    if v is None or pd.isna(v):
        return "0,00%"
    return f"{v:.2%}".replace(".", ",")


def safe_div(a: float, b: float) -> float:
    if b is None or pd.isna(b) or abs(float(b)) < 1e-12:
        return 0.0
    return float(a) / float(b)


def status_icon(var_pct: float, lower_is_better: bool = True) -> str:
    """Semáforo gerencial.

    Costos: verde solo si baja; amarillo si queda estable o sube hasta 3%; rojo si sube más de 3%.
    Margen/utilidad: verde si mejora; amarillo si cae levemente; rojo si cae más de 3%.
    """
    if lower_is_better:
        if var_pct < -0.001:
            return "🟢"
        if var_pct <= 0.03:
            return "🟡"
        return "🔴"
    if var_pct > 0.001:
        return "🟢"
    if var_pct >= -0.03:
        return "🟡"
    return "🔴"


def _tone_from_text(label: str, value: str, delta: str | None = None) -> str:
    text = f"{label} {value} {delta or ''}".lower()
    if "🔴" in text or "crítica" in text or "critica" in text:
        return "red"
    if "🟡" in text or "media" in text:
        return "yellow"
    if "🟢" in text or "ok" in text:
        return "green"
    # Pérdidas o utilidad/margen negativo siempre en rojo.
    if ("utilidad" in text or "margen" in text or "brecha" in text) and ("$-" in text or "-$" in text or "-" in str(value)[:3]):
        return "red"
    return "neutral"


def _kpi_value_size_class(value: str) -> str:
    txt = str(value or "")
    compact = txt.replace(" ", "")
    n = len(compact)
    if n >= 22:
        return "kpi-value-xs"
    if n >= 18:
        return "kpi-value-sm"
    if n >= 14:
        return "kpi-value-md"
    return ""


def kpi(label: str, value: str, delta: str | None = None, help_text: str | None = None, tone: str | None = None):
    """Tarjeta KPI con semáforo controlado, sin etiquetas HTML visibles y con fuente más balanceada."""
    tone = tone or _tone_from_text(label, value, delta)
    tone = tone if tone in {"green", "yellow", "red", "neutral"} else "neutral"

    label_html = escape(str(label))
    value_html = escape(str(value))
    value_cls = _kpi_value_size_class(value)
    delta_html = f'<div class="kpi-delta">{escape(str(delta))}</div>' if delta else ""
    help_html = f'<div class="kpi-help">{escape(str(help_text))}</div>' if help_text else ""

    st.markdown(
        f'<div class="kpi-card kpi-{tone}">'
        f'<div>'
        f'<div class="kpi-label">{label_html}</div>'
        f'<div class="kpi-value {value_cls}" title="{value_html}">{value_html}</div>'
        f'</div>'
        f'<div>{delta_html}{help_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Formato gerencial de tablas
# ------------------------------------------------------------

def fmt_number(v: object, decimals: int = 2) -> str:
    if v is None or pd.isna(v):
        return ""
    try:
        x = float(v)
    except Exception:
        return str(v)
    return f"{x:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_money(v: object) -> str:
    if v is None or pd.isna(v):
        return "$0,00"
    try:
        x = float(v)
    except Exception:
        return str(v)
    return f"${x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(v: object) -> str:
    if v is None or pd.isna(v):
        return "0,00%"
    try:
        return f"{float(v):.2%}".replace(".", ",")
    except Exception:
        return str(v)


def format_df_gerencial(df_in: pd.DataFrame):
    """Aplica separador de miles y formatos gerenciales a tablas Streamlit."""
    df_out = df_in.copy()
    fmt = {}
    for col in df_out.columns:
        col_txt = norm_text(col)
        if not pd.api.types.is_numeric_dtype(df_out[col]):
            continue

        if any(k in col_txt for k in ["PARTICIPACION", "ACUMULADO", "MARGEN", "VARIACION %", "%"]):
            fmt[col] = fmt_pct
        elif any(k in col_txt for k in ["VALOR", "COSTO", "PRECIO", "BRECHA", "IMPACTO", "AHORRO", "UTILIDAD", "GASTO", "VARIACION $"]):
            fmt[col] = fmt_money
        elif any(k in col_txt for k in ["ANO", "MESNRO", "FILAS"]):
            fmt[col] = lambda x: fmt_number(x, 0)
        else:
            fmt[col] = lambda x: fmt_number(x, 2)

    return df_out.style.format(fmt) if fmt else df_out


def dataframe_gerencial(df_in: pd.DataFrame, **kwargs):
    st.dataframe(format_df_gerencial(df_in), use_container_width=True, hide_index=True, **kwargs)


def tabla_prompt(df_in: pd.DataFrame, max_rows: int = 12) -> str:
    """Convierte una tabla pequeña en texto legible para pegar en ChatGPT."""
    if df_in is None or df_in.empty:
        return "Sin datos."
    df_tmp = df_in.head(max_rows).copy()
    for col in df_tmp.columns:
        if pd.api.types.is_numeric_dtype(df_tmp[col]):
            col_norm = norm_text(col)
            if any(k in col_norm for k in ["PARTICIPACION", "ACUMULADO", "MARGEN", "VARIACION %", "%"]):
                df_tmp[col] = df_tmp[col].map(fmt_pct)
            elif any(k in col_norm for k in ["VALOR", "COSTO", "PRECIO", "BRECHA", "IMPACTO", "AHORRO", "UTILIDAD", "GASTO", "VARIACION $"]):
                df_tmp[col] = df_tmp[col].map(fmt_money)
            else:
                df_tmp[col] = df_tmp[col].map(lambda x: fmt_number(x, 2))
    return df_tmp.to_string(index=False)


def construir_prompt_chatgpt(
    periodo: Periodo,
    costo_emp: float,
    costo_saco_emp: float,
    costo_total_saco_sin_extra: float,
    costo_total_saco_con_extra: float,
    precio_actual: float,
    precio_obj_sin_extra: float,
    precio_obj_sin_extra_iva: float,
    margen_real: float,
    margen_obj: float,
    utilidad_saco: float,
    costo_granel: float,
    costo_kg_granel: float,
    incremental_saco: float,
    gastos_saco: float,
    gastos_extra_saco: float,
    kg_granel: float,
    und_emp: float,
    kg_emp: float,
    alertas_df: pd.DataFrame,
    pareto_emp: pd.DataFrame,
    pareto_total: pd.DataFrame,
    var_df: pd.DataFrame,
    tendencias_df: pd.DataFrame | None = None,
    tendencia_texto: str = "",
) -> str:
    """Genera un prompt ejecutivo prellenado para analizar alarmas y recomendaciones."""
    top_var = var_df.copy() if var_df is not None else pd.DataFrame()
    if not top_var.empty and "Variacion $" in top_var.columns:
        top_var = top_var.reindex(top_var["Variacion $"].abs().sort_values(ascending=False).index)

    return f"""Actúa como CFO industrial y experto en costeo de producción de cemento.

Contexto de negocio:
- Producto vendido actualmente: {NOMBRE_PRODUCTO}.
- Objetivo: maximizar rentabilidad sin sacrificar calidad, seguridad, continuidad operativa ni cumplimiento.
- Base de análisis: costeo mensual desde Consolidado.
- Mes analizado: {periodo.etiqueta}.

Reglas de decisión:
1. No recomiendes reducir costos que comprometan calidad del cemento, seguridad industrial, mantenimiento crítico, cumplimiento legal, trazabilidad o continuidad de producción.
2. Prioriza acciones con impacto alto en margen por saco, impacto rápido, bajo riesgo operativo y posibilidad real de negociación o control.
3. Separa costo de producción, gastos asignados, extraordinarios, precio, margen y alertas.
4. Identifica alarmas, causas probables, acciones concretas, responsable sugerido y prioridad.
5. No des recomendaciones genéricas. Usa los datos siguientes.

KPIs principales:
- Costo empacado completo: {fmt_money(costo_emp)}
- Costo empacado por saco: {fmt_money(costo_saco_emp)}
- Costo total comercial por saco sin extraordinarios: {fmt_money(costo_total_saco_sin_extra)}
- Costo total comercial por saco con extraordinarios: {fmt_money(costo_total_saco_con_extra)}
- Precio actual por saco antes de IVA: {fmt_money(precio_actual)}
- Precio objetivo antes de IVA sin extraordinarios: {fmt_money(precio_obj_sin_extra)}
- Precio objetivo con IVA sin extraordinarios: {fmt_money(precio_obj_sin_extra_iva)}
- Margen real: {fmt_pct(margen_real)}
- Margen objetivo editable usado: {fmt_pct(margen_obj)}
- Utilidad por saco: {fmt_money(utilidad_saco)}
- Costo granel total: {fmt_money(costo_granel)}
- Costo granel por kg: {fmt_money(costo_kg_granel)}
- Costo incremental de empaque por saco: {fmt_money(incremental_saco)}
- Gastos asignados por saco: {fmt_money(gastos_saco)}
- Gastos extraordinarios por saco: {fmt_money(gastos_extra_saco)}
- Nota sobre impuestos opcionales: el costo total comercial puede incluir C IMP REN y/o C IMP PATR si el usuario los activó en la barra lateral.
- Kg granel producidos: {fmt_number(kg_granel, 0)}
- Unidades empacadas producidas: {fmt_number(und_emp, 0)}
- Kg empacados producidos: {fmt_number(kg_emp, 0)}

Alertas detectadas:
{tabla_prompt(alertas_df, 20)}

Pareto empacado por observación:
{tabla_prompt(pareto_emp, 12)}

Pareto costo total comercial / gastos asignables:
{tabla_prompt(pareto_total, 12)}

Variaciones relevantes vs mes comparativo:
{tabla_prompt(top_var, 12)}

Entregable solicitado:
1. Resumen ejecutivo en máximo 10 líneas.
2. Top 5 alarmas gerenciales, con nivel de riesgo.
3. Top 5 oportunidades de ahorro sin sacrificar calidad ni seguridad.
4. Recomendaciones de precio: precio mínimo, precio objetivo, brecha frente al precio actual y acción comercial.
5. Acciones operativas concretas por responsable: producción, compras, mantenimiento, logística, gerencia financiera.
6. Evaluación de tendencia cuando la data lo permita: dirección, consistencia, riesgos y señales tempranas.
7. Lista de datos que debo validar antes de tomar decisión.
8. Decisión recomendada para el próximo comité de costos.
"""

# ------------------------------------------------------------
# Carga y normalización de Excel
# ------------------------------------------------------------


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza Consolidado de forma robusta para Streamlit Cloud.

    Corrige el error de Arrow/Pandas cuando MesNro/Año llegan vacíos o como texto.
    """
    mapping: dict[str, str] = {}
    for col in df.columns:
        n = norm_text(col)
        if "PRODU" in n:
            mapping[col] = "Produccion"
        elif n in {"INDICE", "RESULTADO"} or "INDICE" in n or "RESULTADO" in n:
            mapping[col] = "Indice"
        elif "CONCEP" in n or "OBSERV" in n:
            mapping[col] = "Observacion"
        elif "VALOR" in n:
            mapping[col] = "Valor"
        elif n == "MES":
            mapping[col] = "Mes"
        elif n in {"ANO", "AÑO"}:
            mapping[col] = "Ano"
        elif "MESNRO" in n or "MES NRO" in n or "MES_NUM" in n or "MES NUM" in n:
            mapping[col] = "MesNro"

    df = df.rename(columns=mapping).copy()

    # Elimina filas completamente vacías antes de forzar tipos.
    if not df.empty:
        df = df.dropna(how="all").copy()

    required = ["Produccion", "Indice", "Observacion", "Valor", "Mes"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Faltan columnas en Consolidado: " + ", ".join(missing))

    if df.empty:
        return df

    if "Ano" not in df.columns:
        df["Ano"] = 2026
    if "MesNro" not in df.columns:
        df["MesNro"] = np.nan

    for col in ["Produccion", "Indice", "Observacion", "Mes"]:
        df[col] = df[col].fillna("").map(lambda x: str(x).strip())

    df["Valor"] = df["Valor"].apply(parse_valor).fillna(0.0).astype(float)

    # AÑO: convertir sin permitir que ArrowStringArray vacío explote.
    ano_num = pd.to_numeric(df["Ano"], errors="coerce")
    df["Ano"] = ano_num.fillna(2026).astype("int64")

    # MESNRO: primero convierte la columna; si viene vacía, calcula desde Mes.
    mesnro_num = pd.to_numeric(df["MesNro"], errors="coerce")
    mes_desde_texto = df["Mes"].map(lambda x: MESES.get(str(x).strip(), np.nan))
    mesnro_num = mesnro_num.fillna(mes_desde_texto)

    # Si alguna fila todavía no tiene MesNro, no se puede analizar por periodo.
    df["MesNro"] = pd.to_numeric(mesnro_num, errors="coerce")
    df = df.dropna(subset=["MesNro"]).copy()
    if df.empty:
        raise ValueError("No hay MesNro válido. Revise las columnas Mes y MesNro en Consolidado.")
    df["MesNro"] = df["MesNro"].astype("int64")

    df["Mes_norm"] = df["Mes"].map(norm_text)
    df["Indice_norm"] = df["Indice"].map(norm_text)
    df["Obs_norm"] = df["Observacion"].map(norm_text)
    df["Prod_norm"] = df["Produccion"].map(norm_text)

    # Mantener solo filas reales; no eliminar REVISAR para poder auditar.
    df = df[~((df["Produccion"].str.strip() == "") & (df["Observacion"].str.strip() == ""))].copy()
    return df


def _build_consolidado_from_nuevo_mes(xls: pd.ExcelFile) -> pd.DataFrame:
    """Plan B: si Consolidado está vacío, arma una base temporal desde Nuevo mes + Ayudas.

    Usa Enero 2026 por defecto para no exponer al usuario a un bloqueo técnico.
    Luego el usuario puede cargar con macro o ajustar Mes/Año en Excel.
    """
    if "Nuevo mes" not in xls.sheet_names or "Ayudas" not in xls.sheet_names:
        return pd.DataFrame()

    nuevo = pd.read_excel(xls, sheet_name="Nuevo mes")
    ayudas = pd.read_excel(xls, sheet_name="Ayudas")
    if nuevo.empty or ayudas.empty:
        return pd.DataFrame()

    nuevo = nuevo.rename(columns={nuevo.columns[0]: "Produccion", nuevo.columns[1]: "Observacion", nuevo.columns[2]: "Valor"}).copy()
    ayudas = ayudas.rename(columns={ayudas.columns[0]: "Produccion", ayudas.columns[1]: "Observacion", ayudas.columns[2]: "Indice"}).copy()

    ayuda_map = {}
    for _, r in ayudas.iterrows():
        key = (norm_text(r.get("Produccion", "")), norm_text(r.get("Observacion", "")))
        if key not in ayuda_map:
            ayuda_map[key] = str(r.get("Indice", "REVISAR")).strip()

    out_rows = []
    for _, r in nuevo.iterrows():
        prod = str(r.get("Produccion", "")).strip()
        obs = str(r.get("Observacion", "")).strip()
        if prod == "" and obs == "":
            continue
        idx = ayuda_map.get((norm_text(prod), norm_text(obs)), "REVISAR")
        out_rows.append({
            "Produccion": prod,
            "Indice": idx,
            "Observacion": obs,
            "Valor": r.get("Valor", 0),
            "Mes": "Enero",
            "Ano": 2026,
            "MesNro": 1,
        })
    return pd.DataFrame(out_rows)

@st.cache_data(show_spinner=False)
def load_excel(uploaded_bytes: bytes) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str]]:
    xls = pd.ExcelFile(io.BytesIO(uploaded_bytes), engine="openpyxl")
    sheets = xls.sheet_names
    if "Consolidado" not in sheets:
        raise ValueError("El archivo debe tener una hoja llamada 'Consolidado'.")
    df_raw = pd.read_excel(xls, sheet_name="Consolidado")
    if df_raw.dropna(how="all").empty:
        # Plan B para archivos plantilla: construir temporalmente desde Nuevo mes + Ayudas.
        df_raw = _build_consolidado_from_nuevo_mes(xls)
        if df_raw.empty:
            raise ValueError("La hoja Consolidado está vacía debajo de los encabezados y no pude reconstruirla desde Nuevo mes + Ayudas.")
        st.warning("Consolidado estaba vacío. Se armó una base temporal desde 'Nuevo mes' + 'Ayudas' usando Enero 2026. Para producción, use la macro mensual para consolidar Mes/Año reales.")
    df = normalize_columns(df_raw)
    if df.empty:
        raise ValueError("La hoja Consolidado no tiene filas válidas después de normalizar Mes, Año y MesNro.")
    if "Metas Gerenciales" in sheets:
        metas = pd.read_excel(xls, sheet_name="Metas Gerenciales")
    else:
        metas = pd.DataFrame(columns=["KPI", "Producto", "Meta", "Unidad", "Vigente desde", "Comentario"])

    parametros_productos = pd.DataFrame()
    for sheet_producto in ["Parametros Productos", "Parámetros Productos", "Productos Dashboard", "Productos"]:
        if sheet_producto in sheets:
            # La tabla inicia en la fila 5 en la plantilla v20. Si no se reconoce, intenta lectura normal.
            tmp = pd.read_excel(xls, sheet_name=sheet_producto, header=4)
            if tmp.empty or "Key" not in [str(c) for c in tmp.columns]:
                tmp = pd.read_excel(xls, sheet_name=sheet_producto)
            parametros_productos = tmp.dropna(how="all").copy()
            break

    return df, metas, parametros_productos, sheets


@dataclass
class Periodo:
    ano: int
    mes: str
    mes_nro: int
    @property
    def etiqueta(self) -> str:
        return f"{self.mes} {self.ano}"


def periodo_anterior(periodo: Periodo) -> Periodo:
    mn = int(periodo.mes_nro) - 1
    ano = periodo.ano
    if mn <= 0:
        mn = 12
        ano -= 1
    return Periodo(ano=ano, mes=MESES_INV.get(mn, str(mn)), mes_nro=mn)


def filtro_periodo(df: pd.DataFrame, periodo: Periodo) -> pd.DataFrame:
    return df[(df["Ano"] == periodo.ano) & (df["MesNro"] == periodo.mes_nro)].copy()


def suma_indices(df: pd.DataFrame, indices: Iterable[str]) -> float:
    idx = {norm_text(x) for x in indices}
    return float(df.loc[df["Indice_norm"].isin(idx), "Valor"].sum())


def suma_obs(df: pd.DataFrame, obs: str, indices: Optional[Iterable[str]] = None) -> float:
    base = df[df["Obs_norm"] == norm_text(obs)]
    if indices is not None:
        idx = {norm_text(x) for x in indices}
        base = base[base["Indice_norm"].isin(idx)]
    return float(base["Valor"].sum())


def _dedupe_textos(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for val in values:
        txt = str(val or "").strip()
        if not txt:
            continue
        key = norm_text(txt)
        if key in seen:
            continue
        seen.add(key)
        out.append(txt)
    return out


def _texto_peso_bolsa_para_obs(peso_bolsa_kg: float) -> str:
    """Convierte 42.5 en '42,5' y 50.0 en '50' para observaciones de Excel."""
    try:
        peso = float(peso_bolsa_kg)
    except Exception:
        peso = 50.0
    if abs(peso - round(peso)) < 1e-9:
        return str(int(round(peso)))
    txt = f"{peso:.2f}".rstrip("0").rstrip(".")
    return txt.replace(".", ",")


def obs_precio_canonica(peso_bolsa_kg: float) -> str:
    return f"PRECIO PROMEDIO POR BOLSA {_texto_peso_bolsa_para_obs(peso_bolsa_kg)} KG"


def normalizar_obs_precio_bolsa(obs_configurada: str, peso_bolsa_kg: float) -> str:
    """Si un producto no es de 50 kg y trae la observación histórica de 50 kg, usa la presentación real."""
    obs = str(obs_configurada or "").strip()
    if not obs:
        return obs_precio_canonica(peso_bolsa_kg)
    try:
        peso = float(peso_bolsa_kg or 0)
    except Exception:
        peso = 50.0
    if abs(peso - 50.0) > 1e-6 and norm_text(obs) == norm_text("PRECIO PROMEDIO POR BOLSA 50 KG"):
        return obs_precio_canonica(peso)
    return obs


def candidatos_obs_precio_bolsa(obs_configurada: str, peso_bolsa_kg: float) -> list[str]:
    """Busca primero la observación correcta de la presentación y deja fallback histórico."""
    canon = normalizar_obs_precio_bolsa(obs_configurada, peso_bolsa_kg)
    peso_txt_coma = _texto_peso_bolsa_para_obs(peso_bolsa_kg)
    peso_txt_punto = peso_txt_coma.replace(",", ".")
    return _dedupe_textos([
        canon,
        f"PRECIO PROMEDIO POR BOLSA {peso_txt_punto} KG",
        str(obs_configurada or "").strip(),
        "PRECIO PROMEDIO POR BOLSA 50 KG",
    ])


def suma_obs_precio_bolsa(df: pd.DataFrame, obs_configurada: str, peso_bolsa_kg: float) -> tuple[float, str]:
    """Retorna el primer precio encontrado para evitar duplicar si existen observaciones alias."""
    for obs in candidatos_obs_precio_bolsa(obs_configurada, peso_bolsa_kg):
        valor = suma_obs(df, obs)
        if abs(valor) > 1e-12:
            return valor, obs
    canon = normalizar_obs_precio_bolsa(obs_configurada, peso_bolsa_kg)
    return 0.0, canon



OBS_GASTOS_SUBTOTALES = {
    norm_text("GASTOS"),
    norm_text("GASTOS ADMINISTRATIVOS"),
    norm_text("GATOS FINANCIEROS"),
    norm_text("GASTOS FINANCIEROS"),
    norm_text("GASTOS DE VENTA"),
    norm_text("PROVISIÓN IMPUESTOS DE RENTA"),
    norm_text("DIFERENCIA EN CAMBIO NETA NO REALIZADA"),
    norm_text("GASTOS ADMINISTRATIVOS, FINANCIEROS Y DE VTA UNITARIOS"),
}


def _producto_actual_es_art() -> bool:
    """Compatibilidad histórica: ahora significa que el producto usa subtotales de gasto configurados en Excel."""
    if not globals().get("producto_cfg"):
        return False
    modo = norm_text(getattr(producto_cfg, "modo_gastos", "indices"))
    return modo in {"SUBTOTALES_PRODUCTO", "SUBTOTALES", "DETALLE_PRODUCTO", "PRODUCTO_SUBTOTALES"}


def detalle_gastos_comerciales(df_in: pd.DataFrame) -> pd.DataFrame:
    """Devuelve el detalle de gastos sin subtotales duplicados para el producto activo."""
    if df_in is None or df_in.empty:
        return pd.DataFrame(columns=df_in.columns if df_in is not None else [])
    if _producto_actual_es_art():
        prod_gasto = norm_text(producto_cfg.gastos_producto)
        base = df_in[df_in["Prod_norm"] == prod_gasto].copy()
        base = base[~base["Indice_norm"].isin({norm_text("TOTAL"), norm_text("INFO")})].copy()
        base = base[~base["Obs_norm"].isin(OBS_GASTOS_SUBTOTALES)].copy()
        return base
    idx = {norm_text(i) for i in INDICES_GASTOS_COMERCIALES}
    return df_in[df_in["Indice_norm"].isin(idx)].copy()


def suma_gastos_comerciales(df_in: pd.DataFrame) -> float:
    """Suma gastos comerciales del producto activo evitando dobles conteos del nuevo ART.

    En UG los gastos vienen en índices separados. En ART el Excel nuevo trae un índice
    combinado C ADM Y VEN ART EMP con subtotales internos; por eso se toma el TOTAL/GASTOS
    del bloque ART y luego se respetan los interruptores de renta/patrimonio cuando existan.
    """
    if df_in is None or df_in.empty:
        return 0.0
    if _producto_actual_es_art():
        total = suma_obs(df_in, producto_cfg.obs_gastos_total, ["TOTAL"])
        if abs(total) < 1e-9:
            total = float(detalle_gastos_comerciales(df_in)["Valor"].sum())
        if not globals().get("incluir_imp_renta", False):
            total -= suma_indices(df_in, ["C IMP REN"])
        if not globals().get("incluir_imp_patrimonio", False):
            total -= suma_indices(df_in, ["C IMP PATR"])
        return float(total)
    return suma_indices(df_in, INDICES_GASTOS_COMERCIALES)




def suma_admin_comercial(df_in: pd.DataFrame) -> float:
    """Bloque administrativo para simulación, separado por producto."""
    if df_in is None or df_in.empty:
        return 0.0
    if _producto_actual_es_art():
        return suma_obs(df_in, producto_cfg.obs_admin, producto_cfg.indices_admin)
    return suma_indices(df_in, INDICES_ADMINISTRACION)


def suma_ventas_comercial(df_in: pd.DataFrame) -> float:
    """Bloque de ventas/logística comercial para simulación."""
    if df_in is None or df_in.empty:
        return 0.0
    if _producto_actual_es_art():
        return suma_obs(df_in, producto_cfg.obs_ventas, producto_cfg.indices_ventas or producto_cfg.indices_admin)
    return suma_indices(df_in, INDICES_VENTAS)


def suma_financiera_comercial(df_in: pd.DataFrame) -> float:
    """Bloque financiero para simulación. En ART combina el subtotal financiero y la diferencia en cambio."""
    if df_in is None or df_in.empty:
        return 0.0
    if _producto_actual_es_art():
        fin_subtotal = 0.0
        for obs_fin in _split_param_list(producto_cfg.obs_financiero):
            fin_subtotal += suma_obs(df_in, obs_fin, producto_cfg.indices_admin or producto_cfg.indices_gastos_base)
        return fin_subtotal + suma_indices(df_in, INDICES_FINANCIEROS)
    return suma_indices(df_in, INDICES_FINANCIEROS)


def suma_impuestos_base_comercial(df_in: pd.DataFrame) -> float:
    if df_in is None or df_in.empty:
        return 0.0
    if _producto_actual_es_art():
        return 0.0
    return suma_indices(df_in, INDICES_IMPUESTOS_BASE)

def resumen_gastos_comerciales(df_in: pd.DataFrame) -> pd.DataFrame:
    base = detalle_gastos_comerciales(df_in)
    if base.empty:
        return pd.DataFrame(columns=["Observacion", "Valor", "Participacion", "Acumulado"])
    out = base.groupby("Observacion", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
    total = suma_gastos_comerciales(df_in)
    if abs(total) < 1e-9:
        total = float(out["Valor"].sum()) if not out.empty else 0.0
    out["Participacion"] = out["Valor"].apply(lambda x: safe_div(x, total))
    out["Acumulado"] = out["Participacion"].cumsum()
    return out


def resumen_por_observacion(df: pd.DataFrame, indices: Iterable[str]) -> pd.DataFrame:
    idx = {norm_text(x) for x in indices}
    base = df[df["Indice_norm"].isin(idx)].copy()
    out = base.groupby("Observacion", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
    total = float(out["Valor"].sum()) if not out.empty else 0.0
    out["Participacion"] = out["Valor"].apply(lambda x: safe_div(x, total))
    out["Acumulado"] = out["Participacion"].cumsum()
    return out


def build_pareto(base: pd.DataFrame, denominador_sacos: float, denominador_kg: float) -> pd.DataFrame:
    out = base.copy()
    if out.empty:
        return out
    out["Impacto por saco"] = out["Valor"].apply(lambda x: safe_div(x, denominador_sacos))
    out["Impacto por kg"] = out["Valor"].apply(lambda x: safe_div(x, denominador_kg))
    out["Ahorro 5%"] = out["Valor"] * 0.05
    out["Ahorro 10%"] = out["Valor"] * 0.10
    out["Prioridad"] = np.where(out["Acumulado"] <= 0.8, "Alta", np.where(out["Acumulado"] <= 0.95, "Media", "Baja"))
    out["Acción sugerida"] = out["Observacion"].apply(sugerir_accion)
    return out


def sugerir_accion(obs: str) -> str:
    n = norm_text(obs)
    if "ENERG" in n or "ELECT" in n:
        return "Revisar consumo específico kWh/t, tarifa y horas pico."
    if "SACO" in n or "KRAFT" in n or "EMPAQUE" in n:
        return "Negociar proveedor, gramaje, merma y consumo por saco."
    if "CLINKER" in n or "CALIZA" in n or "YESO" in n:
        return "Validar dosificación, rendimiento, precio y merma de MP."
    if "MANTEN" in n or "REFACC" in n:
        return "Separar correctivo vs preventivo y revisar causa raíz."
    if "COMBUST" in n or "ACEITE" in n or "LUBRIC" in n:
        return "Revisar consumo por tonelada y plan de mantenimiento."
    if "SALARIO" in n or "NOMINA" in n or "PERSONAL" in n:
        return "Medir productividad por tonelada y turnos."
    if "TRANSP" in n:
        return "Revisar ruta, tarifa, cargue y facturación por tonelada."
    return "Revisar variación, proveedor, consumo y responsable del rubro."


def pareto_chart(df_pareto: pd.DataFrame, title: str, top_n: int = 12):
    data = df_pareto.head(top_n).copy()
    if data.empty:
        st.info("No hay datos para graficar.")
        return
    fig = go.Figure()
    fig.add_trace(go.Bar(x=data["Observacion"], y=data["Valor"], name="Valor"))
    fig.add_trace(go.Scatter(x=data["Observacion"], y=data["Acumulado"], name="% acumulado", yaxis="y2", mode="lines+markers"))
    fig.update_traces(
        selector=dict(type="bar"),
        marker_color="#E8650A", marker_line_color="rgba(232,101,10,0.25)", marker_line_width=1,
        opacity=0.85
    )
    fig.update_traces(
        selector=dict(type="scatter"),
        line_color="#F5A623", marker_color="#F5A623", marker_size=7,
    )
    fig.update_layout(
        title=title,
        xaxis=dict(tickangle=-35, tickfont=dict(size=11)),
        yaxis=dict(title="Valor"),
        yaxis2=dict(title="% acumulado", overlaying="y", side="right", tickformat=".0%", range=[0, 1.05]),
        legend=dict(orientation="h"),
        height=520,
        margin=dict(l=30, r=30, t=65, b=140),
    )
    st.plotly_chart(fig, use_container_width=True)


def waterfall(title: str, labels: list[str], values: list[float], total_label: str):
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"] * len(values) + ["total"],
        x=labels + [total_label],
        y=values + [sum(values)],
        connector={"line": {"color": "rgba(232,101,10,0.3)", "width": 1, "dash": "dot"}},
        increasing={"marker": {"color": "#FF4059", "line": {"color": "#FF4059", "width": 1}}},
        decreasing={"marker": {"color": "#00C47A", "line": {"color": "#00C47A", "width": 1}}},
        totals={"marker": {"color": "#00C9C8", "line": {"color": "#00C9C8", "width": 1}}},
    ))
    fig.update_layout(title=title, height=420, margin=dict(l=30, r=30, t=65, b=55))
    st.plotly_chart(fig, use_container_width=True)


def variacion(actual: float, previo: float, etiqueta_base: str = "base") -> tuple[float, str]:
    diff = actual - previo
    rel = safe_div(diff, previo)
    return rel, f"{pct(rel)} vs {etiqueta_base}"


def to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return output.getvalue()

# ------------------------------------------------------------
# Interfaz: carga
# ------------------------------------------------------------

st.markdown("""
<div class="hero-card">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:16px;">
    <div style="flex:1;min-width:260px;">
      <div class="hero-badge"><span class="hero-dot"></span>Sistema en vivo &nbsp;·&nbsp; Kolcem S.A.S.</div>
      <div class="hero-title">Cockpit Gerencial · Costeo de Cemento</div>
      <div class="hero-subtitle">Análisis ejecutivo de costos industriales &mdash; Multi-producto · Empacado · Granel · Comercial · Tendencias</div>
      <div class="calm-note" style="margin-top:14px;">
        🟢 Verde = mejora real de costo o margen &nbsp;&nbsp;
        🟡 Ámbar = atención controlada &nbsp;&nbsp;
        🔴 Rojo = pérdida o deterioro relevante
      </div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:8px;padding-top:4px;">
      <img src="https://www.kolcem.com/wp-content/uploads/2022/09/LOGO-1024x715.png"
           style="height:68px;width:auto;object-fit:contain;filter:brightness(1.1);"
           onerror="this.style.display='none'" alt="Kolcem" />
      <span style="font-family:'Sora',sans-serif;font-size:0.72rem;font-weight:700;
                   letter-spacing:0.1em;text-transform:uppercase;color:rgba(245,166,35,0.85);">
        Buenos Cimientos
      </span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
<div style="text-align:center;padding:12px 8px 16px;border-bottom:1px solid rgba(232,101,10,0.15);margin-bottom:14px;">
  <img src="https://www.kolcem.com/wp-content/uploads/2022/09/LOGO-1024x715.png"
       style="max-height:52px;width:auto;object-fit:contain;"
       onerror="this.style.display='none'" alt="Kolcem" />
  <div style="font-family:'Sora',sans-serif;font-size:0.65rem;font-weight:700;
              letter-spacing:0.14em;text-transform:uppercase;
              color:rgba(245,166,35,0.7);margin-top:6px;">Buenos Cimientos</div>
</div>
""", unsafe_allow_html=True)
uploaded = st.sidebar.file_uploader("Cargar Excel de costeo", type=["xlsm", "xlsx"])
if uploaded is None:
    st.info("Carga el Excel con la hoja Consolidado para iniciar.")
    st.stop()

try:
    df, metas_df, parametros_productos_df, sheet_names = load_excel(uploaded.getvalue())
except Exception as exc:
    st.error(f"No pude leer el archivo: {exc}")
    st.stop()

# ------------------------------------------------------------
# Selector de producto / presentación
# ------------------------------------------------------------

productos_excel = construir_productos_desde_parametros(parametros_productos_df)
PRODUCTOS_COSTEO = productos_excel if productos_excel else PRODUCTOS_COSTEO_DEFAULT.copy()

df_consolidado_completo = df.copy()
productos_disponibles = {
    key: cfg for key, cfg in PRODUCTOS_COSTEO.items()
    if producto_disponible(df_consolidado_completo, cfg)
}
if not productos_disponibles:
    st.error("No encontré productos compatibles en Consolidado. Revise los nombres de producción y los índices de Ayudas.")
    st.stop()

st.sidebar.divider()
st.sidebar.subheader("Producto")
producto_labels = {key: cfg.nombre for key, cfg in productos_disponibles.items()}
producto_key = st.sidebar.selectbox(
    "Producto / presentación",
    list(productos_disponibles.keys()),
    format_func=lambda k: producto_labels[k],
    index=0,
    help="Los productos y presentaciones se leen desde la hoja Parametros Productos del Excel. Evita mezclar cantidades, precios e índices entre productos.",
)
producto_cfg = productos_disponibles[producto_key]

NOMBRE_PRODUCTO = producto_cfg.nombre
PRODUCTO_CORTO = producto_cfg.nombre_corto
PESO_BOLSA_KG = float(producto_cfg.peso_bolsa_kg)
SACOS_POR_TON = safe_div(1000.0, PESO_BOLSA_KG)

INDICES_GRANEL = list(producto_cfg.indices_granel)
INDICES_EMPACADO = list(producto_cfg.indices_empacado)
INDICES_GASTOS_COMERCIALES_BASE = list(producto_cfg.indices_gastos_base)
INDICES_ADMINISTRACION = list(producto_cfg.indices_admin)
INDICES_VENTAS = list(producto_cfg.indices_ventas)
INDICES_FINANCIEROS = list(producto_cfg.indices_fin)
INDICES_IMPUESTOS_BASE = list(producto_cfg.indices_imp_base)
INDICES_GASTOS_COMERCIALES = INDICES_GASTOS_COMERCIALES_BASE.copy()
INDICES_COSTO_TOTAL = INDICES_EMPACADO + INDICES_GASTOS_COMERCIALES
OBS_KG_GRANEL = producto_cfg.obs_kg_granel
OBS_UND_EMPACADO = producto_cfg.obs_und_empacado
OBS_PRECIO_BOLSA = normalizar_obs_precio_bolsa(producto_cfg.obs_precio_bolsa, PESO_BOLSA_KG)
OBS_CEMENTO_GRANEL_TRANSFERIDO = producto_cfg.obs_cemento_transferido
OBS_CANTIDAD_VENDIDA = producto_cfg.obs_cantidad_vendida

df = filtrar_producto_costeo(df_consolidado_completo, producto_cfg)
if df.empty:
    st.error(f"No hay filas válidas para {producto_cfg.nombre} después de filtrar el Consolidado.")
    st.stop()

st.sidebar.caption(f"Presentación activa: {PESO_BOLSA_KG:g} kg/bolsa · {SACOS_POR_TON:.2f} bolsas/ton")

# ------------------------------------------------------------
# Selectores
# ------------------------------------------------------------

anios = sorted([int(x) for x in df["Ano"].dropna().unique()])
if not anios:
    st.error("No hay años válidos en Consolidado.")
    st.stop()
ano_sel = st.sidebar.selectbox("Año", anios, index=len(anios)-1)
meses_disponibles = df[df["Ano"] == ano_sel][["Mes", "MesNro"]].drop_duplicates().sort_values("MesNro")
meses_disponibles = meses_disponibles.dropna(subset=["MesNro"])
if meses_disponibles.empty:
    st.error("No hay meses válidos para el año seleccionado.")
    st.stop()
mes_sel = st.sidebar.selectbox("Mes a analizar", list(meses_disponibles["Mes"]), index=len(meses_disponibles)-1)
mes_nro_sel = int(meses_disponibles.loc[meses_disponibles["Mes"] == mes_sel, "MesNro"].iloc[0])
periodo = Periodo(ano=ano_sel, mes=mes_sel, mes_nro=mes_nro_sel)

# Comparación flexible: el usuario escoge contra qué mes comparar.
periodos_disponibles = (
    df[["Ano", "Mes", "MesNro"]]
    .dropna(subset=["Ano", "Mes", "MesNro"])
    .drop_duplicates()
    .sort_values(["Ano", "MesNro"])
)
periodos_disponibles["Etiqueta"] = periodos_disponibles.apply(
    lambda r: f"{str(r['Mes'])} {int(r['Ano'])}", axis=1
)
periodo_prev_auto = periodo_anterior(periodo)
def _periodo_key(row):
    return int(row["Ano"]), int(row["MesNro"])

keys = [(_periodo_key(r), lab) for _, r, lab in zip(periodos_disponibles.index, periodos_disponibles.to_dict('records'), periodos_disponibles["Etiqueta"])]
labels_comp = list(periodos_disponibles["Etiqueta"])
default_label = f"{periodo_prev_auto.mes} {periodo_prev_auto.ano}"
default_idx = labels_comp.index(default_label) if default_label in labels_comp else max(0, len(labels_comp)-2)

st.sidebar.divider()
st.sidebar.subheader("Comparación")
comp_label = st.sidebar.selectbox(
    "Comparar contra",
    labels_comp,
    index=default_idx,
    help="Escoge libremente el mes base de comparación. No tiene que ser el mes anterior.",
)
comp_row = periodos_disponibles.loc[periodos_disponibles["Etiqueta"] == comp_label].iloc[0]
periodo_comp = Periodo(ano=int(comp_row["Ano"]), mes=str(comp_row["Mes"]), mes_nro=int(comp_row["MesNro"]))

if periodo_comp.ano == periodo.ano and periodo_comp.mes_nro == periodo.mes_nro:
    st.sidebar.warning("Estás comparando el mes contra sí mismo. Las variaciones saldrán en cero.")

df_mes = filtro_periodo(df, periodo)
df_prev = filtro_periodo(df, periodo_comp)

st.sidebar.divider()
st.sidebar.subheader("Parámetros comerciales")
iva = st.sidebar.number_input("IVA", min_value=0.0, max_value=1.0, value=0.19, step=0.01, format="%.2f")
margen_obj = st.sidebar.number_input("Margen objetivo sobre precio", min_value=0.0, max_value=0.95, value=0.0, step=0.01, format="%.2f")
top_n = st.sidebar.slider("Top N Pareto", min_value=5, max_value=25, value=12, step=1)

st.sidebar.divider()
st.sidebar.subheader("Umbrales de alerta")
umbral_var_pct = st.sidebar.number_input(
    "Desviación relevante %",
    min_value=0.0,
    max_value=1.0,
    value=0.05,
    step=0.01,
    format="%.2f",
    help="0.05 equivale a 5%. Se usa para marcar variaciones relevantes por observación.",
)
umbral_impacto_saco = st.sidebar.number_input(
    "Impacto relevante por saco ($)",
    min_value=0.0,
    value=500.0,
    step=100.0,
    help="Desviación mínima por saco para que una observación aparezca como relevante.",
)

st.sidebar.divider()
st.sidebar.subheader("Impuestos opcionales · costeo real")
incluir_imp_renta = st.sidebar.checkbox(
    "Aplicar C IMP REN al costeo real",
    value=False,
    help="Impuesto de renta. Control independiente: si se activa, se suma al costo real producido, margen real, precio objetivo, metodología y exportación.",
)
incluir_imp_patrimonio = st.sidebar.checkbox(
    "Aplicar C IMP PATR al costeo real",
    value=False,
    help="Impuesto de patrimonio. Control independiente: si se activa, se suma al costo real producido, margen real, precio objetivo, metodología y exportación.",
)

INDICES_GASTOS_COMERCIALES = INDICES_GASTOS_COMERCIALES_BASE.copy()
if incluir_imp_renta:
    INDICES_GASTOS_COMERCIALES.append("C IMP REN")
if incluir_imp_patrimonio:
    INDICES_GASTOS_COMERCIALES.append("C IMP PATR")
INDICES_COSTO_TOTAL = INDICES_EMPACADO + INDICES_GASTOS_COMERCIALES

# ------------------------------------------------------------
# Cálculos centrales
# ------------------------------------------------------------

# Componentes dinámicos por producto seleccionado.
# UG usa C MP/MO/CIF UG y C MP/MO/CIF EMP; ART usa C MP/MO/CIF ART GRN y C MP/MO/CIF ART EMP.
c_mp_ug = suma_indices(df_mes, [INDICES_GRANEL[0]]) if len(INDICES_GRANEL) > 0 else 0.0
c_mo_ug = suma_indices(df_mes, [INDICES_GRANEL[1]]) if len(INDICES_GRANEL) > 1 else 0.0
c_cif_ug = suma_indices(df_mes, [INDICES_GRANEL[2]]) if len(INDICES_GRANEL) > 2 else 0.0
costo_granel = c_mp_ug + c_mo_ug + c_cif_ug
kg_granel = suma_obs(df_mes, OBS_KG_GRANEL)
costo_kg_granel = safe_div(costo_granel, kg_granel)

c_mp_emp = suma_indices(df_mes, [INDICES_EMPACADO[0]]) if len(INDICES_EMPACADO) > 0 else 0.0
c_mo_emp = suma_indices(df_mes, [INDICES_EMPACADO[1]]) if len(INDICES_EMPACADO) > 1 else 0.0
c_cif_emp = suma_indices(df_mes, [INDICES_EMPACADO[2]]) if len(INDICES_EMPACADO) > 2 else 0.0
costo_emp = c_mp_emp + c_mo_emp + c_cif_emp
und_emp = suma_obs(df_mes, OBS_UND_EMPACADO)
kg_emp = und_emp * PESO_BOLSA_KG
costo_saco_emp = safe_div(costo_emp, und_emp)
costo_kg_emp = safe_div(costo_emp, kg_emp)

cemento_transf = suma_obs(df_mes, OBS_CEMENTO_GRANEL_TRANSFERIDO, INDICES_EMPACADO)
incremental_emp = costo_emp - cemento_transf
incremental_saco = safe_div(incremental_emp, und_emp)
incremental_kg = safe_div(incremental_emp, kg_emp)

costos_gastos = suma_gastos_comerciales(df_mes)
gastos_saco = safe_div(costos_gastos, und_emp)
gastos_kg = safe_div(costos_gastos, kg_emp)

imp_renta_total = suma_indices(df_mes, ["C IMP REN"])
imp_patrimonio_total = suma_indices(df_mes, ["C IMP PATR"])
impuestos_opcionales_df = pd.DataFrame([
    ["C IMP REN", "Impuesto de renta", imp_renta_total, safe_div(imp_renta_total, und_emp), safe_div(imp_renta_total, kg_emp), "Sí" if incluir_imp_renta else "No"],
    ["C IMP PATR", "Impuesto de patrimonio", imp_patrimonio_total, safe_div(imp_patrimonio_total, und_emp), safe_div(imp_patrimonio_total, kg_emp), "Sí" if incluir_imp_patrimonio else "No"],
], columns=["Índice", "Concepto", "Valor total", "$/saco", "$/kg", "Aplica al costo"])

gastos_extra = float(df_mes.loc[df_mes["Prod_norm"].str.contains("GASTOS EXTRA", na=False), "Valor"].sum())
gastos_extra_saco = safe_div(gastos_extra, und_emp)
gastos_extra_kg = safe_div(gastos_extra, kg_emp)

costo_total_saco_sin_extra = costo_saco_emp + gastos_saco
costo_total_saco_con_extra = costo_total_saco_sin_extra + gastos_extra_saco
costo_total_kg_sin_extra = costo_kg_emp + gastos_kg
costo_total_kg_con_extra = costo_total_kg_sin_extra + gastos_extra_kg

precio_obj_sin_extra = safe_div(costo_total_saco_sin_extra, 1 - margen_obj)
precio_obj_con_extra = safe_div(costo_total_saco_con_extra, 1 - margen_obj)
precio_obj_sin_extra_iva = precio_obj_sin_extra * (1 + iva)
precio_obj_con_extra_iva = precio_obj_con_extra * (1 + iva)
und_vendida = suma_obs(df_mes, OBS_CANTIDAD_VENDIDA)
kg_vendido = und_vendida * PESO_BOLSA_KG
ton_vendida = safe_div(kg_vendido, 1000.0)

precio_actual_bruto, OBS_PRECIO_BOLSA_USADA = suma_obs_precio_bolsa(df_mes, OBS_PRECIO_BOLSA, PESO_BOLSA_KG)
precio_actual = precio_actual_bruto if und_vendida > 0 else 0.0
if und_vendida <= 0 and precio_actual_bruto > 0:
    OBS_PRECIO_BOLSA_USADA = f"{OBS_PRECIO_BOLSA_USADA} · sin ventas: precio promedio aplicado = 0"

utilidad_saco = precio_actual - costo_total_saco_sin_extra
margen_real = safe_div(utilidad_saco, precio_actual)
brecha_precio = precio_actual - precio_obj_sin_extra
brecha_margen = margen_real - margen_obj

# Resultado empresa del periodo seleccionado
venta_total_real = und_vendida * precio_actual
costo_total_real_sin_extra = costo_emp + costos_gastos
costo_total_real_con_extra = costo_total_real_sin_extra + gastos_extra
utilidad_total_real = venta_total_real - costo_total_real_sin_extra
utilidad_total_real_con_extra = venta_total_real - costo_total_real_con_extra
margen_total_real = safe_div(utilidad_total_real, venta_total_real)
margen_total_real_con_extra = safe_div(utilidad_total_real_con_extra, venta_total_real)
utilidad_total_real_ton = safe_div(utilidad_total_real, safe_div(kg_emp, 1000.0))

# ------------------------------------------------------------
# Variaciones relevantes a nivel de observación
# ------------------------------------------------------------
def calcular_variaciones_observacion(df_actual: pd.DataFrame, df_anterior: pd.DataFrame, und_base: float, kg_base: float) -> pd.DataFrame:
    if df_actual.empty:
        return pd.DataFrame(columns=["Indice", "Observacion", "Valor", "Valor anterior", "Variacion $", "Variacion %", "Impacto por saco", "Impacto por kg", "Criterio", "Alerta"])
    actual = df_actual.groupby(["Indice_norm", "Obs_norm", "Indice", "Observacion"], as_index=False)["Valor"].sum()
    if not df_anterior.empty:
        previo = df_anterior.groupby(["Indice_norm", "Obs_norm"], as_index=False)["Valor"].sum().rename(columns={"Valor": "Valor anterior"})
    else:
        previo = pd.DataFrame(columns=["Indice_norm", "Obs_norm", "Valor anterior"])
    var = actual.merge(previo, on=["Indice_norm", "Obs_norm"], how="left")
    var["Valor anterior"] = var["Valor anterior"].fillna(0.0)
    var["Variacion $"] = var["Valor"] - var["Valor anterior"]
    var["Variacion %"] = var.apply(lambda r: safe_div(r["Variacion $"], r["Valor anterior"]), axis=1)
    var["Impacto por saco"] = var["Variacion $"].apply(lambda x: safe_div(x, und_base))
    var["Impacto por kg"] = var["Variacion $"].apply(lambda x: safe_div(x, kg_base))
    var["Criterio"] = np.where(var["Variacion $"] > 0, "Sube costo", np.where(var["Variacion $"] < 0, "Baja costo", "Sin cambio"))
    var["Alerta"] = np.where(var["Variacion $"] > 0, "🔴", np.where(var["Variacion $"] < 0, "🟢", "⚪"))
    var = var.sort_values("Variacion $", key=lambda serie: serie.abs(), ascending=False)
    return var

variaciones_obs = calcular_variaciones_observacion(df_mes, df_prev, und_emp, kg_emp)
if not variaciones_obs.empty and not df_prev.empty:
    mask_rel = (variaciones_obs["Impacto por saco"].abs() >= umbral_impacto_saco) | (variaciones_obs["Variacion %"].abs() >= umbral_var_pct)
    variaciones_relevantes = variaciones_obs.loc[mask_rel].copy()
else:
    variaciones_relevantes = pd.DataFrame(columns=variaciones_obs.columns)

costo_emp_prev = suma_indices(df_prev, INDICES_EMPACADO)
und_emp_prev = suma_obs(df_prev, OBS_UND_EMPACADO)
costo_saco_prev = safe_div(costo_emp_prev, und_emp_prev)
var_costo_saco, delta_costo_saco = variacion(costo_saco_emp, costo_saco_prev, periodo_comp.etiqueta)

costo_granel_prev = suma_indices(df_prev, INDICES_GRANEL)
kg_granel_prev = suma_obs(df_prev, OBS_KG_GRANEL)
costo_kg_granel_prev = safe_div(costo_granel_prev, kg_granel_prev)
var_costo_kg_granel, delta_costo_kg_granel = variacion(costo_kg_granel, costo_kg_granel_prev, periodo_comp.etiqueta)


# ------------------------------------------------------------
# Evolución mensual y tendencias
# ------------------------------------------------------------

def periodo_label_df(df_in: pd.DataFrame) -> pd.DataFrame:
    out = df_in.copy()
    out["Periodo"] = out.apply(lambda r: f"{str(r['Mes'])} {int(r['Ano'])}", axis=1)
    out["PeriodoOrden"] = out["Ano"].astype(int) * 100 + out["MesNro"].astype(int)
    return out


def serie_mensual_observaciones(df_in: pd.DataFrame, indices: list[str], top_n_obs: int = 12) -> tuple[pd.DataFrame, list[str]]:
    idx_norm = {norm_text(x) for x in indices}
    base = df_in[df_in["Indice_norm"].isin(idx_norm)].copy()
    base = periodo_label_df(base)
    ranking = base.groupby("Observacion", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
    top_obs = list(ranking.head(top_n_obs)["Observacion"])
    serie = (
        base[base["Observacion"].isin(top_obs)]
        .groupby(["Ano", "Mes", "MesNro", "Periodo", "PeriodoOrden", "Observacion"], as_index=False)["Valor"]
        .sum()
        .sort_values(["PeriodoOrden", "Observacion"])
    )
    return serie, top_obs


def serie_mensual_kpis(df_in: pd.DataFrame) -> pd.DataFrame:
    rows = []
    periodos = df_in[["Ano", "Mes", "MesNro"]].dropna().drop_duplicates().sort_values(["Ano", "MesNro"])
    for _, r in periodos.iterrows():
        p = Periodo(int(r["Ano"]), str(r["Mes"]), int(r["MesNro"]))
        d = filtro_periodo(df_in, p)
        ce = suma_indices(d, INDICES_EMPACADO)
        ug = suma_obs(d, OBS_UND_EMPACADO)
        kg_e = ug * PESO_BOLSA_KG
        cg = suma_indices(d, INDICES_GRANEL)
        kg_g = suma_obs(d, OBS_KG_GRANEL)
        gastos = suma_gastos_comerciales(d)
        gastos_extra_mes = float(d.loc[d["Prod_norm"].str.contains("GASTOS EXTRA", na=False), "Valor"].sum())
        und_vendida_mes = suma_obs(d, OBS_CANTIDAD_VENDIDA)
        kg_vendido_mes = und_vendida_mes * PESO_BOLSA_KG
        ton_vendida_mes = safe_div(kg_vendido_mes, 1000.0)
        precio_bruto_mes, _obs_precio_mes = suma_obs_precio_bolsa(d, OBS_PRECIO_BOLSA, PESO_BOLSA_KG)
        precio = precio_bruto_mes if und_vendida_mes > 0 else 0.0
        costo_saco = safe_div(ce, ug)
        costo_comercial = costo_saco + safe_div(gastos, ug)
        utilidad = precio - costo_comercial
        venta_total_mes = und_vendida_mes * precio
        costo_comercial_total_mes = ce + gastos
        costo_comercial_total_con_extra_mes = costo_comercial_total_mes + gastos_extra_mes
        utilidad_empresa_mes = venta_total_mes - costo_comercial_total_mes
        utilidad_empresa_con_extra_mes = venta_total_mes - costo_comercial_total_con_extra_mes
        margen = safe_div(utilidad_empresa_mes, venta_total_mes)
        rows.append({
            "Ano": p.ano,
            "Mes": p.mes,
            "MesNro": p.mes_nro,
            "Periodo": p.etiqueta,
            "PeriodoOrden": p.ano * 100 + p.mes_nro,
            "Costo empacado": ce,
            "UND producidas": ug,
            "UND vendidas": und_vendida_mes,
            "Kg empacados": kg_e,
            "Kg vendidos": kg_vendido_mes,
            "Ton vendidas": ton_vendida_mes,
            "Costo / saco": costo_saco,
            "Costo comercial / saco": costo_comercial,
            "Precio actual / saco": precio,
            "Utilidad / saco": utilidad,
            "Venta total empresa": venta_total_mes,
            "Costo comercial total": costo_comercial_total_mes,
            "Gastos extraordinarios": gastos_extra_mes,
            "Utilidad empresa": utilidad_empresa_mes,
            "Utilidad empresa con extra": utilidad_empresa_con_extra_mes,
            "Utilidad / ton": safe_div(utilidad_empresa_mes, safe_div(kg_e, 1000.0)),
            "Margen real": margen,
            "Margen con extra": safe_div(utilidad_empresa_con_extra_mes, venta_total_mes),
            "Costo granel": cg,
            "Kg granel": kg_g,
            "Costo granel / kg": safe_div(cg, kg_g),
            "Gastos asignados": gastos,
            "Gastos / saco": safe_div(gastos, ug),
        })
    return pd.DataFrame(rows).sort_values("PeriodoOrden")


def texto_tendencia_kpis(kpis: pd.DataFrame, max_items: int = 8) -> str:
    if kpis is None or kpis.empty or len(kpis) < 3:
        return "No hay suficiente historia para evaluar tendencia. Se requieren al menos 3 meses cargados."
    cols = ["Utilidad empresa", "Utilidad empresa con extra", "Venta total empresa", "Costo comercial total", "Costo / saco", "Costo comercial / saco", "Precio actual / saco", "Utilidad / saco", "Margen real", "Costo granel / kg", "Gastos / saco", "UND producidas"]
    lineas = []
    for col in cols:
        if col not in kpis.columns:
            continue
        serie = pd.to_numeric(kpis[col], errors="coerce").dropna()
        if len(serie) < 3:
            continue
        first, last = float(serie.iloc[0]), float(serie.iloc[-1])
        diff = last - first
        rel = safe_div(diff, first)
        sentido = "sube" if diff > 0 else "baja" if diff < 0 else "estable"
        val_txt = fmt_pct(rel) if "Margen" in col else fmt_money(diff) if any(x in col for x in ["Costo", "Precio", "Utilidad", "Gastos"]) else fmt_number(diff, 0)
        lineas.append(f"- {col}: {sentido}; cambio desde el primer mes cargado: {val_txt}.")
    return "\n".join(lineas[:max_items]) if lineas else "No hay suficientes datos numéricos para tendencia."


kpis_mensuales = serie_mensual_kpis(df)
tendencia_texto = texto_tendencia_kpis(kpis_mensuales)

# ------------------------------------------------------------
# Alertas gerenciales
# ------------------------------------------------------------

alertas = []
if und_emp <= 0:
    alertas.append(["Crítica", "No se encontró UND PRODUCIDAS Q", "No se pueden calcular costos por saco."])
if precio_actual <= 0:
    alertas.append(["Alta", "No se encontró precio promedio por bolsa", "No se puede calcular margen real."])
if costo_saco_emp > 0 and precio_actual > 0 and utilidad_saco < 0:
    alertas.append(["Crítica", "Utilidad por saco negativa", "Precio actual está por debajo del costo total comercial."])
if margen_obj > 0 and brecha_precio < 0:
    alertas.append(["Alta", "Precio actual inferior al objetivo", f"Brecha estimada: {money(brecha_precio)} por saco."])
if safe_div(c_cif_ug, costo_granel) > 0.35:
    alertas.append(["Media", "CIF granel mayor a 35%", "Revisar energía, mantenimiento, depreciación y estructura indirecta."])
if (df_mes["Indice_norm"] == norm_text("REVISAR")).any():
    n_rev = int((df_mes["Indice_norm"] == norm_text("REVISAR")).sum())
    alertas.append(["Alta", f"{n_rev} filas con índice REVISAR", "Actualizar Ayudas y recargar el mes."])
if not alertas:
    alertas.append(["OK", "Sin alertas críticas", "El modelo tiene datos base suficientes para decisión."])
alertas_df = pd.DataFrame(alertas, columns=["Nivel", "Alerta", "Acción sugerida"])


# ------------------------------------------------------------
# Resumen multi-producto y portafolio
# ------------------------------------------------------------

def _dedupe_indices(indices: Iterable[str]) -> list[str]:
    """Conserva orden y elimina duplicados por texto normalizado."""
    out: list[str] = []
    seen: set[str] = set()
    for idx in indices or []:
        idx_txt = str(idx).strip()
        if not idx_txt:
            continue
        key = norm_text(idx_txt)
        if key in seen:
            continue
        seen.add(key)
        out.append(idx_txt)
    return out


def _indices_gastos_producto(producto: ProductoCosteo, incluir_renta: bool, incluir_patrimonio: bool) -> list[str]:
    indices = list(producto.indices_gastos_base or [])
    if incluir_renta:
        indices.append("C IMP REN")
    if incluir_patrimonio:
        indices.append("C IMP PATR")
    return _dedupe_indices(indices)


def _sumar_gastos_producto(df_producto_mes: pd.DataFrame, producto: ProductoCosteo, indices_gastos: list[str]) -> float:
    """Suma gastos sin duplicar subtotales. La regla base siempre son índices parametrizados."""
    if df_producto_mes is None or df_producto_mes.empty:
        return 0.0
    return suma_indices(df_producto_mes, indices_gastos)


def calcular_resumen_producto(
    df_full: pd.DataFrame,
    producto: ProductoCosteo,
    periodo_calc: Periodo,
    incluir_renta: bool = False,
    incluir_patrimonio: bool = False,
) -> dict[str, object]:
    """Calcula rentabilidad completa por producto desde la configuración del Excel.

    Esta función es la pieza clave de la nueva arquitectura: cada producto se evalúa con
    sus propios productos contables, índices, cantidades, precio y presentación.
    """
    df_producto = filtrar_producto_costeo(df_full, producto)
    df_producto_mes = filtro_periodo(df_producto, periodo_calc) if df_producto is not None and not df_producto.empty else pd.DataFrame()
    peso_bolsa = float(producto.peso_bolsa_kg or 0) or 50.0
    bolsas_por_ton = safe_div(1000.0, peso_bolsa)

    indices_gastos = _indices_gastos_producto(producto, incluir_renta, incluir_patrimonio)

    costo_granel_p = suma_indices(df_producto_mes, producto.indices_granel)
    kg_granel_p = suma_obs(df_producto_mes, producto.obs_kg_granel)
    costo_kg_granel_p = safe_div(costo_granel_p, kg_granel_p)

    costo_emp_p = suma_indices(df_producto_mes, producto.indices_empacado)
    und_emp_p = suma_obs(df_producto_mes, producto.obs_und_empacado)
    kg_emp_p = und_emp_p * peso_bolsa
    toneladas_p = safe_div(kg_emp_p, 1000.0)

    costo_saco_emp_p = safe_div(costo_emp_p, und_emp_p)
    costo_kg_emp_p = safe_div(costo_emp_p, kg_emp_p)

    cemento_transf_p = suma_obs(df_producto_mes, producto.obs_cemento_transferido, producto.indices_empacado)
    incremental_emp_p = costo_emp_p - cemento_transf_p
    incremental_saco_p = safe_div(incremental_emp_p, und_emp_p)

    gastos_p = _sumar_gastos_producto(df_producto_mes, producto, indices_gastos)
    gastos_saco_p = safe_div(gastos_p, und_emp_p)
    gastos_kg_p = safe_div(gastos_p, kg_emp_p)

    und_vendida_p = suma_obs(df_producto_mes, producto.obs_cantidad_vendida)
    kg_vendido_p = und_vendida_p * peso_bolsa
    toneladas_vendidas_p = safe_div(kg_vendido_p, 1000.0)

    precio_bolsa_bruto_p, obs_precio_usada_p = suma_obs_precio_bolsa(df_producto_mes, producto.obs_precio_bolsa, peso_bolsa)
    precio_bolsa_p = precio_bolsa_bruto_p if und_vendida_p > 0 else 0.0
    if und_vendida_p <= 0 and precio_bolsa_bruto_p > 0:
        obs_precio_usada_p = f"{obs_precio_usada_p} · sin ventas: precio promedio aplicado = 0"

    precio_kg_p = safe_div(precio_bolsa_p, peso_bolsa)
    precio_ton_p = precio_kg_p * 1000.0

    venta_total_p = und_vendida_p * precio_bolsa_p

    # Costeo industrial/comercial de lo producido.
    costo_produccion_total_p = costo_emp_p + gastos_p
    costo_total_saco_p = safe_div(costo_produccion_total_p, und_emp_p)
    costo_total_kg_p = safe_div(costo_produccion_total_p, kg_emp_p)
    costo_total_ton_p = costo_total_kg_p * 1000.0

    # Resultado real vendido: si no hay venta, no hay precio promedio aplicado ni ingreso.
    # La producción no vendida queda como costo/inventario económico, no como venta ficticia.
    costo_ventas_real_p = und_vendida_p * costo_total_saco_p
    bolsas_no_vendidas_p = max(und_emp_p - und_vendida_p, 0.0)
    costo_inventario_no_vendido_p = bolsas_no_vendidas_p * costo_total_saco_p

    venta_valorizada_produccion_p = und_emp_p * precio_bolsa_p
    utilidad_valorizada_produccion_p = venta_valorizada_produccion_p - costo_produccion_total_p

    utilidad_total_p = venta_total_p - costo_ventas_real_p
    utilidad_saco_p = safe_div(utilidad_total_p, und_vendida_p)
    utilidad_kg_p = safe_div(utilidad_total_p, kg_vendido_p)
    utilidad_ton_p = safe_div(utilidad_total_p, toneladas_vendidas_p)
    margen_p = safe_div(utilidad_total_p, venta_total_p)

    estado = "OK"
    if df_producto_mes.empty:
        estado = "Sin filas"
    elif und_emp_p <= 0:
        estado = "Sin unidades"
    elif precio_bolsa_p <= 0:
        estado = "Sin precio"
    elif utilidad_total_p < 0:
        estado = "Pérdida"

    return {
        "Key": producto.key,
        "Producto": producto.nombre,
        "Nombre corto": producto.nombre_corto,
        "Obs precio bolsa": obs_precio_usada_p,
        "Kg bolsa": peso_bolsa,
        "Bolsas / ton": bolsas_por_ton,
        "Toneladas": toneladas_p,
        "Bolsas producidas": und_emp_p,
        "Bolsas vendidas": und_vendida_p,
        "Bolsas": und_emp_p,
        "Kg empacados": kg_emp_p,
        "Kg vendidos": kg_vendido_p,
        "Toneladas vendidas": toneladas_vendidas_p,
        "Kg granel": kg_granel_p,
        "Costo granel": costo_granel_p,
        "Costo granel / kg": costo_kg_granel_p,
        "Costo empacado": costo_emp_p,
        "Costo empacado / bolsa": costo_saco_emp_p,
        "Costo empacado / kg": costo_kg_emp_p,
        "Cemento transferido": cemento_transf_p,
        "Incremental empaque": incremental_emp_p,
        "Incremental / bolsa": incremental_saco_p,
        "Gastos asignables": gastos_p,
        "Gastos / bolsa": gastos_saco_p,
        "Gastos / kg": gastos_kg_p,
        "Precio / bolsa": precio_bolsa_p,
        "Precio / kg": precio_kg_p,
        "Precio / ton": precio_ton_p,
        "Venta total": venta_total_p,
        "Costo producción total": costo_produccion_total_p,
        "Costo ventas real": costo_ventas_real_p,
        "Costo total comercial": costo_ventas_real_p,
        "Costo total / bolsa": costo_total_saco_p,
        "Costo total / kg": costo_total_kg_p,
        "Costo total / ton": costo_total_ton_p,
        "Bolsas no vendidas": bolsas_no_vendidas_p,
        "Costo inventario no vendido": costo_inventario_no_vendido_p,
        "Venta valorizada producción": venta_valorizada_produccion_p,
        "Utilidad valorizada producción": utilidad_valorizada_produccion_p,
        "Utilidad empresa": utilidad_total_p,
        "Utilidad / bolsa": utilidad_saco_p,
        "Utilidad / kg": utilidad_kg_p,
        "Utilidad / ton": utilidad_ton_p,
        "Margen": margen_p,
        "Estado": estado,
        "Índices granel": "|".join(producto.indices_granel),
        "Índices empacado": "|".join(producto.indices_empacado),
        "Índices gastos": "|".join(indices_gastos),
    }


def resumen_productos_periodo(
    df_full: pd.DataFrame,
    productos: dict[str, ProductoCosteo],
    periodo_calc: Periodo,
    incluir_renta: bool = False,
    incluir_patrimonio: bool = False,
) -> pd.DataFrame:
    rows = []
    for cfg in productos.values():
        rows.append(calcular_resumen_producto(df_full, cfg, periodo_calc, incluir_renta, incluir_patrimonio))
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["Participación venta"] = out["Venta total"].apply(lambda x: safe_div(x, float(out["Venta total"].sum())))
    out["Participación utilidad"] = out["Utilidad empresa"].apply(lambda x: safe_div(x, float(out["Utilidad empresa"].sum())))
    out["Contribución margen pp"] = out.apply(lambda r: r["Participación venta"] * r["Margen"], axis=1)
    return out.sort_values(["Venta total", "Utilidad empresa"], ascending=False)


def chart_empty_guard(df_chart: pd.DataFrame, y_col: str) -> bool:
    return df_chart is None or df_chart.empty or y_col not in df_chart.columns or float(pd.to_numeric(df_chart[y_col], errors="coerce").fillna(0).abs().sum()) <= 0

# ------------------------------------------------------------
# Tabs
# ------------------------------------------------------------

tabs = st.tabs([
    "📊 Resumen Gerencial",
    "💰 Precio & Margen",
    f"🏭 Granel {PRODUCTO_CORTO}",
    f"📦 Empacado {PRODUCTO_CORTO}",
    "🧾 Gastos ADM/Ventas",
    "📈 Paretos",
    "↕️ Variaciones",
    "📉 Evolución Mensual",
    "🔍 Calidad de Datos",
    "🎯 Metas / Exportar",
    "📐 Metodología",
    "🤖 Análisis IA",
    "📊 Utilidad Empresa",
    "🧮 Simulador Toneladas",
    "🧩 Escenarios Portafolio",
    "🏗️ Costeo Ambos Productos",
])

with tabs[0]:
    st.subheader(f"Resumen gerencial multi-producto - {periodo.etiqueta}")
    st.caption(
        "Vista consolidada por producto. Cada bloque se calcula desde la hoja Parametros Productos: "
        "producto contable, índices, observaciones, presentación y gastos. Al crear un nuevo producto en Excel, "
        "la app lo incorpora sin quemar lógica en el código."
    )

    resumen_productos_df = resumen_productos_periodo(
        df_consolidado_completo,
        productos_disponibles,
        periodo,
        incluir_imp_renta,
        incluir_imp_patrimonio,
    )

    if resumen_productos_df.empty:
        st.warning("No hay productos con datos suficientes para el periodo seleccionado.")
    else:
        venta_portafolio = float(resumen_productos_df["Venta total"].sum())
        costo_portafolio = float(resumen_productos_df["Costo total comercial"].sum())
        utilidad_portafolio = float(resumen_productos_df["Utilidad empresa"].sum())
        toneladas_portafolio = float(resumen_productos_df["Toneladas"].sum())
        margen_portafolio = safe_div(utilidad_portafolio, venta_portafolio)
        utilidad_ton_portafolio = safe_div(utilidad_portafolio, toneladas_portafolio)

        st.markdown("### Portafolio total del periodo")
        p1, p2, p3, p4 = st.columns(4)
        with p1:
            kpi("Venta total portafolio", money(venta_portafolio), help_text=f"{num(toneladas_portafolio, 2)} toneladas")
        with p2:
            kpi("Costo total portafolio", money(costo_portafolio), help_text="Costo comercial sin extraordinarios")
        with p3:
            kpi("Utilidad portafolio", money(utilidad_portafolio), help_text=f"{money(utilidad_ton_portafolio)}/ton", tone="red" if utilidad_portafolio < 0 else "green")
        with p4:
            kpi("Margen portafolio", pct(margen_portafolio), tone="red" if margen_portafolio < 0 else "green")

        st.markdown("### Rentabilidad separada por producto")
        productos_rows = resumen_productos_df.to_dict("records")
        for start_i in range(0, len(productos_rows), 2):
            cols = st.columns(min(2, len(productos_rows[start_i:start_i+2])))
            for col, row in zip(cols, productos_rows[start_i:start_i+2]):
                with col:
                    tone = "red" if float(row.get("Utilidad empresa", 0) or 0) < 0 else "green"
                    st.markdown(
                        f"""
                        <div class="kpi-card kpi-{tone}" style="min-height:220px;">
                          <div>
                            <div class="kpi-label">{escape(str(row.get('Nombre corto', row.get('Producto', 'Producto'))))}</div>
                            <div style="font-family:'Sora',sans-serif;font-size:1.05rem;font-weight:800;color:var(--text-pri);line-height:1.15;margin-bottom:10px;">
                              {escape(str(row.get('Producto','')))}
                            </div>
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;color:var(--text-sec);font-size:.82rem;">
                              <div>Presentación</div><div style="text-align:right;font-weight:800;">{fmt_number(row.get('Kg bolsa',0),2)} kg</div>
                              <div>Ton producidas</div><div style="text-align:right;font-weight:800;">{fmt_number(row.get('Toneladas',0),2)}</div>
                              <div>Bolsas vendidas</div><div style="text-align:right;font-weight:800;">{fmt_number(row.get('Bolsas vendidas',0),2)}</div>
                              <div>Precio / bolsa</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Precio / bolsa',0))}</div>
                              <div>Costo / bolsa</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Costo total / bolsa',0))}</div>
                              <div>Utilidad / bolsa</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Utilidad / bolsa',0))}</div>
                              <div>Margen</div><div style="text-align:right;font-weight:800;">{fmt_pct(row.get('Margen',0))}</div>
                            </div>
                          </div>
                          <div class="kpi-delta">Utilidad total: {fmt_money(row.get('Utilidad empresa',0))}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        columnas_resumen = [
            "Producto", "Obs precio bolsa", "Kg bolsa", "Toneladas", "Bolsas producidas", "Bolsas vendidas", "Toneladas vendidas", "Precio / bolsa", "Precio / ton",
            "Costo total / bolsa", "Costo total / ton", "Utilidad / bolsa", "Utilidad / ton",
            "Venta total", "Costo ventas real", "Utilidad empresa", "Margen", "Costo producción total", "Bolsas no vendidas", "Costo inventario no vendido", "Participación venta", "Participación utilidad", "Estado",
        ]
        dataframe_gerencial(resumen_productos_df[[c for c in columnas_resumen if c in resumen_productos_df.columns]])

        st.markdown("### Lectura visual por producto")
        c_left, c_right = st.columns(2)
        with c_left:
            if chart_empty_guard(resumen_productos_df, "Utilidad empresa"):
                st.info("No hay utilidad suficiente para graficar por producto.")
            else:
                fig = px.bar(
                    resumen_productos_df,
                    x="Nombre corto",
                    y="Utilidad empresa",
                    color="Nombre corto",
                    title="Utilidad total por producto",
                    text="Utilidad empresa",
                )
                fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
                fig.add_hline(y=0, line_dash="dot", line_color="#94A3B8", line_width=1.2)
                fig.update_layout(height=420, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        with c_right:
            if chart_empty_guard(resumen_productos_df, "Venta total"):
                st.info("No hay venta suficiente para graficar participación.")
            else:
                fig = px.pie(
                    resumen_productos_df,
                    names="Nombre corto",
                    values="Venta total",
                    title="Composición de venta por producto",
                    hole=0.42,
                )
                fig.update_layout(height=420)
                st.plotly_chart(fig, use_container_width=True)

        c_left, c_right = st.columns(2)
        with c_left:
            fig = px.bar(
                resumen_productos_df,
                x="Nombre corto",
                y="Margen",
                color="Nombre corto",
                title="Margen por producto",
                text="Margen",
            )
            fig.update_yaxes(tickformat=".1%")
            fig.update_traces(texttemplate="%{text:.1%}", textposition="outside")
            fig.update_layout(height=380, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        with c_right:
            unit_long = resumen_productos_df.melt(
                id_vars=["Nombre corto"],
                value_vars=["Precio / ton", "Costo total / ton", "Utilidad / ton"],
                var_name="Métrica",
                value_name="Valor",
            )
            fig = px.bar(
                unit_long,
                x="Nombre corto",
                y="Valor",
                color="Métrica",
                barmode="group",
                title="Precio, costo y utilidad por tonelada",
            )
            fig.update_layout(height=380)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Producto seleccionado para análisis operativo")
        st.info(
            f"Las demás pestañas muestran el detalle operativo de **{producto_cfg.nombre}**. "
            "Cambia el producto en la barra lateral para auditar otro producto sin mezclar índices ni presentaciones."
        )

        st.markdown("### Alertas gerenciales del producto seleccionado")
        dataframe_gerencial(alertas_df)

        st.markdown("### Desviaciones relevantes del producto seleccionado")
        if df_prev.empty:
            st.info("No existe mes anterior cargado para el producto seleccionado. Las desviaciones se activan desde el segundo mes.")
        elif variaciones_relevantes.empty:
            st.success("No hay desviaciones relevantes según los umbrales configurados.")
        else:
            dataframe_gerencial(variaciones_relevantes.head(10)[["Alerta", "Indice", "Observacion", "Valor", "Valor anterior", "Variacion $", "Variacion %", "Impacto por saco", "Impacto por kg", "Criterio"]])


with tabs[1]:
    st.subheader("Precio de venta, margen y escenarios por producto")
    st.caption(
        "Vista multi-producto: uso general y estructural se muestran en el mismo informe. "
        "Si un producto no tiene bolsas vendidas, su precio promedio aplicado queda en cero."
    )

    precio_productos_df = resumen_productos_periodo(
        df_consolidado_completo,
        productos_disponibles,
        periodo,
        incluir_imp_renta,
        incluir_imp_patrimonio,
    )

    if precio_productos_df.empty:
        st.info("No hay productos disponibles para analizar precio y margen.")
    else:
        precio_productos_df = precio_productos_df.copy()
        precio_productos_df["Precio objetivo / bolsa"] = precio_productos_df["Costo total / bolsa"].apply(
            lambda x: safe_div(x, 1 - margen_obj)
        )
        precio_productos_df["Precio objetivo + IVA / bolsa"] = precio_productos_df["Precio objetivo / bolsa"] * (1 + iva)
        precio_productos_df["Brecha vs objetivo"] = precio_productos_df["Precio / bolsa"] - precio_productos_df["Precio objetivo / bolsa"]
        precio_productos_df["Diferencia margen"] = precio_productos_df["Margen"] - margen_obj
        precio_productos_df["Sin ventas"] = precio_productos_df["Bolsas vendidas"].apply(lambda x: "Sí" if float(x or 0) <= 0 else "No")

        venta_total_precio = float(precio_productos_df["Venta total"].sum())
        costo_total_precio = float(precio_productos_df["Costo total comercial"].sum())
        utilidad_total_precio = float(precio_productos_df["Utilidad empresa"].sum())
        margen_total_precio = safe_div(utilidad_total_precio, venta_total_precio)
        productos_sin_venta = int((pd.to_numeric(precio_productos_df["Bolsas vendidas"], errors="coerce").fillna(0) <= 0).sum())

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            kpi("Venta real total", money(venta_total_precio), help_text="Calculada con bolsas vendidas")
        with k2:
            kpi("Costo total productos", money(costo_total_precio), help_text="Costo comercial del periodo")
        with k3:
            kpi("Utilidad total productos", money(utilidad_total_precio), tone="red" if utilidad_total_precio < 0 else "green")
        with k4:
            kpi("Productos sin venta", num(productos_sin_venta, 2), help_text="Precio promedio aplicado = $0,00", tone="yellow" if productos_sin_venta else "green")

        st.markdown("### Precio, margen y brecha por producto")
        productos_rows = precio_productos_df.to_dict("records")
        for start_i in range(0, len(productos_rows), 2):
            cols = st.columns(min(2, len(productos_rows[start_i:start_i + 2])))
            for col, row in zip(cols, productos_rows[start_i:start_i + 2]):
                with col:
                    sin_venta = float(row.get("Bolsas vendidas", 0) or 0) <= 0
                    tone = "yellow" if sin_venta else ("red" if float(row.get("Brecha vs objetivo", 0) or 0) < 0 else "green")
                    st.markdown(
                        f"""
                        <div class="kpi-card kpi-{tone}" style="min-height:255px;">
                          <div>
                            <div class="kpi-label">{escape(str(row.get('Nombre corto', row.get('Producto', 'Producto'))))}</div>
                            <div style="font-family:'Sora',sans-serif;font-size:1.02rem;font-weight:800;color:var(--text-pri);line-height:1.15;margin-bottom:10px;">
                              {escape(str(row.get('Producto','')))}
                            </div>
                            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px 16px;color:var(--text-sec);font-size:.82rem;">
                              <div>Presentación</div><div style="text-align:right;font-weight:800;">{fmt_number(row.get('Kg bolsa',0),2)} kg</div>
                              <div>Bolsas vendidas</div><div style="text-align:right;font-weight:800;">{fmt_number(row.get('Bolsas vendidas',0),2)}</div>
                              <div>Precio / bolsa</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Precio / bolsa',0))}</div>
                              <div>Precio / ton</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Precio / ton',0))}</div>
                              <div>Costo total / bolsa</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Costo total / bolsa',0))}</div>
                              <div>Precio objetivo / bolsa</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Precio objetivo / bolsa',0))}</div>
                              <div>Brecha / bolsa</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Brecha vs objetivo',0))}</div>
                              <div>Margen</div><div style="text-align:right;font-weight:800;">{fmt_pct(row.get('Margen',0))}</div>
                            </div>
                          </div>
                          <div class="kpi-delta">{"Sin ventas: precio promedio aplicado = $0,00" if sin_venta else "Venta total: " + fmt_money(row.get('Venta total',0))}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        columnas_precio = [
            "Producto", "Obs precio bolsa", "Kg bolsa", "Bolsas vendidas", "Toneladas vendidas",
            "Precio / bolsa", "Precio / ton", "Costo total / bolsa", "Costo total / ton",
            "Precio objetivo / bolsa", "Precio objetivo + IVA / bolsa",
            "Brecha vs objetivo", "Margen", "Diferencia margen", "Venta total", "Costo ventas real", "Utilidad empresa", "Costo producción total", "Costo inventario no vendido", "Sin ventas", "Estado",
        ]
        dataframe_gerencial(precio_productos_df[[c for c in columnas_precio if c in precio_productos_df.columns]])

        st.markdown("### Precio sugerido de venta por margen · todos los productos")
        st.caption("Tabla base de 5% a 30%. Cada producto usa su propia presentación, costo y precio real de venta.")

        margenes = [m / 100 for m in range(5, 31, 5)]
        sensibilidad_multi = []
        for _, row in precio_productos_df.iterrows():
            for m in margenes:
                costo_bolsa = float(row.get("Costo total / bolsa", 0) or 0)
                precio_obj_bolsa = safe_div(costo_bolsa, 1 - m)
                sensibilidad_multi.append([
                    row.get("Producto", ""),
                    row.get("Nombre corto", ""),
                    row.get("Kg bolsa", 0),
                    row.get("Bolsas vendidas", 0),
                    row.get("Precio / bolsa", 0),
                    row.get("Precio / ton", 0),
                    m,
                    precio_obj_bolsa,
                    precio_obj_bolsa * (1 + iva),
                    safe_div(precio_obj_bolsa, float(row.get("Kg bolsa", 0) or 0)) * 1000.0,
                    precio_obj_bolsa - float(row.get("Precio / bolsa", 0) or 0),
                ])
        sens_df = pd.DataFrame(
            sensibilidad_multi,
            columns=[
                "Producto", "Nombre corto", "Kg bolsa", "Bolsas vendidas", "Precio actual / bolsa",
                "Precio actual / ton", "Margen objetivo", "Precio objetivo / bolsa",
                "Precio objetivo con IVA / bolsa", "Precio objetivo / ton", "Brecha vs precio actual",
            ],
        )

        col_a, col_b = st.columns([1.25, 1])
        with col_a:
            dataframe_gerencial(sens_df)
        with col_b:
            fig = px.line(
                sens_df,
                x="Margen objetivo",
                y="Precio objetivo / bolsa",
                color="Nombre corto",
                markers=True,
                title="Curva de precio objetivo antes de IVA por producto",
            )
            fig.update_yaxes(tickprefix="$")
            fig.update_layout(height=430)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Comparativo precio, costo y utilidad por tonelada")
        comp_cols = ["Precio / ton", "Costo total / ton", "Utilidad / ton"]
        comp_df = precio_productos_df.melt(
            id_vars=["Nombre corto"],
            value_vars=[c for c in comp_cols if c in precio_productos_df.columns],
            var_name="Métrica",
            value_name="Valor",
        )
        fig = px.bar(
            comp_df,
            x="Nombre corto",
            y="Valor",
            color="Métrica",
            barmode="group",
            title="Precio, costo y utilidad por tonelada · todos los productos",
        )
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Detalle operativo del producto seleccionado")
        st.info(
            f"Producto seleccionado en la barra lateral: **{producto_cfg.nombre}**. "
            "Las pestañas de granel, empacado, variaciones, metodología y simulador profundizan en este producto específico."
        )

with tabs[2]:
    st.subheader(f"Granel {PRODUCTO_CORTO} - {periodo.etiqueta}")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Costo total granel", money(costo_granel))
    with c2: kpi("Kg producidos granel", num(kg_granel, 0))
    with c3: kpi("Costo / kg", money(costo_kg_granel), delta_costo_kg_granel)
    with c4: kpi("CIF / costo granel", pct(safe_div(c_cif_ug, costo_granel)))
    col_a, col_b = st.columns(2)
    with col_a:
        waterfall("Waterfall costo granel", ["MP", "MO", "CIF"], [c_mp_ug, c_mo_ug, c_cif_ug], "Total")
    with col_b:
        comp = pd.DataFrame({"Componente": ["MP", "MO", "CIF"], "Valor": [c_mp_ug, c_mo_ug, c_cif_ug]})
        fig_pie = px.pie(comp, names="Componente", values="Valor", title="Composición granel",
                         color_discrete_sequence=["#E8650A","#F5A623","#2DBD6E"])
        fig_pie.update_traces(textfont_color="#080D18", pull=[0.04,0,0])
        st.plotly_chart(fig_pie, use_container_width=True)
    pareto_g = build_pareto(resumen_por_observacion(df_mes, INDICES_GRANEL), und_emp, kg_emp)
    pareto_chart(pareto_g, "Pareto granel por observación", top_n)
    dataframe_gerencial(pareto_g)

with tabs[3]:
    st.subheader(f"Empacado {PRODUCTO_CORTO} - {periodo.etiqueta}")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Costo empacado completo", money(costo_emp))
    with c2: kpi("UND producidas", num(und_emp, 0))
    with c3: kpi("Costo / saco", money(costo_saco_emp), delta_costo_saco)
    with c4: kpi("Costo / kg", money(costo_kg_emp))
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Cemento transferido", money(cemento_transf))
    with c2: kpi("Incremental empaque", money(incremental_emp))
    with c3: kpi("Incremental / saco", money(incremental_saco))
    with c4: kpi("Incremental / kg", money(incremental_kg))
    col_a, col_b = st.columns(2)
    with col_a:
        waterfall("Waterfall empacado completo", ["Cemento granel", "MP/Empaque", "MO", "CIF"], [cemento_transf, c_mp_emp - cemento_transf, c_mo_emp, c_cif_emp], "Total")
    with col_b:
        comp = pd.DataFrame({"Componente": ["Cemento granel", "MP/Empaque", "MO", "CIF"], "Valor": [cemento_transf, c_mp_emp - cemento_transf, c_mo_emp, c_cif_emp]})
        fig_pie2 = px.pie(comp, names="Componente", values="Valor", title="Composición empacado",
                          color_discrete_sequence=["#E8650A","#F5A623","#2DBD6E","#F59E0B"])
        fig_pie2.update_traces(textfont_color="#080D18", pull=[0.04,0,0,0])
        st.plotly_chart(fig_pie2, use_container_width=True)
    pareto_e = build_pareto(resumen_por_observacion(df_mes, INDICES_EMPACADO), und_emp, kg_emp)
    pareto_chart(pareto_e, "Pareto empacado por observación", top_n)
    dataframe_gerencial(pareto_e)


with tabs[4]:
    st.subheader(f"Gastos administrativos, ventas, financieros e impuestos - {periodo.etiqueta}")
    st.caption("Estos índices no hacen parte del costo industrial puro, pero sí alimentan el costo total comercial y el precio mínimo de venta.")

    st.markdown("### Impuestos opcionales")
    st.caption("C IMP REN y C IMP PATR se muestran siempre, pero solo afectan costo, margen y precio objetivo cuando están activados en la barra lateral.")
    dataframe_gerencial(impuestos_opcionales_df)

    gastos_detalle = detalle_gastos_comerciales(df_mes)
    gastos_por_indice = (
        gastos_detalle.groupby("Indice", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
        if not gastos_detalle.empty else pd.DataFrame(columns=["Indice", "Valor"])
    )
    gastos_por_indice["Participacion"] = gastos_por_indice["Valor"].apply(lambda x: safe_div(x, costos_gastos))
    gastos_por_indice["Impacto por saco"] = gastos_por_indice["Valor"].apply(lambda x: safe_div(x, und_emp))
    gastos_por_indice["Impacto por kg"] = gastos_por_indice["Valor"].apply(lambda x: safe_div(x, kg_emp))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Gastos asignables totales", money(costos_gastos), tone="neutral")
    with c2:
        kpi("Gastos asignados / saco", money(gastos_saco), tone="neutral")
    with c3:
        kpi("Gastos asignados / kg", money(gastos_kg), tone="neutral")
    with c4:
        kpi("Participación sobre costo comercial", pct(safe_div(gastos_saco, costo_total_saco_sin_extra)), tone="yellow" if safe_div(gastos_saco, costo_total_saco_sin_extra) > 0.2 else "neutral")

    col_a, col_b = st.columns([1.1, 1])
    with col_a:
        st.markdown("### Resumen por índice")
        dataframe_gerencial(gastos_por_indice)
    with col_b:
        if gastos_por_indice.empty:
            st.info("No hay gastos asignables para el mes seleccionado.")
        else:
            fig = px.bar(
                gastos_por_indice,
                x="Indice",
                y="Valor",
                title="Gastos asignables por índice",
                text="Valor",
            )
            fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
            fig.update_layout(height=430, margin=dict(l=30, r=30, t=70, b=80))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Pareto de gastos asignables por observación")
    pareto_gastos = build_pareto(resumen_gastos_comerciales(df_mes), und_emp, kg_emp)
    pareto_chart(pareto_gastos, "Pareto ADM + Ventas + Financieros + Impuestos", top_n)
    dataframe_gerencial(pareto_gastos)

    st.markdown("### Lectura gerencial")
    if gastos_por_indice.empty:
        st.info("No se identificaron gastos asignables en el mes seleccionado.")
    else:
        principal = gastos_por_indice.iloc[0]
        st.markdown(
            f"""
            - El mayor bloque de gastos asignables es **{principal['Indice']}**, con **{fmt_money(principal['Valor'])}**.
            - Su impacto unitario es **{fmt_money(principal['Impacto por saco'])} por saco** y **{fmt_money(principal['Impacto por kg'])} por kg**.
            - Estos gastos se suman al costo empacado para construir el **costo total comercial**, que es el piso económico para definir precio de venta.
            """
        )

with tabs[5]:
    st.subheader("Paretos de decisión y ahorro potencial")
    vista = st.radio("Vista", ["Empacado", "Granel", "Gastos asignables", "Costo total comercial"], horizontal=True)
    if vista == "Empacado":
        base = resumen_por_observacion(df_mes, INDICES_EMPACADO)
    elif vista == "Granel":
        base = resumen_por_observacion(df_mes, INDICES_GRANEL)
    elif vista == "Gastos asignables":
        base = resumen_gastos_comerciales(df_mes)
    else:
        a = resumen_por_observacion(df_mes, INDICES_EMPACADO)
        b = resumen_gastos_comerciales(df_mes)
        base = pd.concat([a[["Observacion", "Valor"]], b[["Observacion", "Valor"]]], ignore_index=True)
        base = base.groupby("Observacion", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
        total = float(base["Valor"].sum()) if not base.empty else 0
        base["Participacion"] = base["Valor"].apply(lambda x: safe_div(x, total))
        base["Acumulado"] = base["Participacion"].cumsum()
    decision = build_pareto(base, und_emp, kg_emp)
    pareto_chart(decision, f"Pareto - {vista}", top_n)
    st.markdown("### Matriz de decisión")
    dataframe_gerencial(decision)

with tabs[6]:
    st.subheader(f"Variaciones vs {periodo_comp.etiqueta}")
    if df_prev.empty:
        st.info("No existe mes anterior cargado. Esta vista empezará a ser más útil desde el segundo mes.")
    else:
        st.markdown("### Desviaciones relevantes")
        st.caption("Relevante = supera el umbral de impacto por saco o el umbral porcentual configurado en la barra lateral.")
        if variaciones_relevantes.empty:
            st.success("No hay desviaciones relevantes según los umbrales configurados.")
        else:
            fig = px.bar(
                variaciones_relevantes.head(20),
                x="Observacion",
                y="Variacion $",
                color="Criterio",
                title="Desviaciones relevantes por observación",
                color_discrete_map={"Sube costo": "#c53030", "Baja costo": "#138a36", "Sin cambio": "#6b7280"},
            )
            fig.update_layout(xaxis_tickangle=-35, height=560, margin=dict(b=150))
            st.plotly_chart(fig, use_container_width=True)
            dataframe_gerencial(variaciones_relevantes[["Alerta", "Indice", "Observacion", "Valor", "Valor anterior", "Variacion $", "Variacion %", "Impacto por saco", "Impacto por kg", "Criterio"]])

        st.markdown("### Todas las variaciones por observación")
        dataframe_gerencial(variaciones_obs[["Alerta", "Indice", "Observacion", "Valor", "Valor anterior", "Variacion $", "Variacion %", "Impacto por saco", "Impacto por kg", "Criterio"]])


with tabs[7]:
    st.subheader("Evolución mensual y microtendencias")
    st.caption("Lectura longitudinal: gastos representativos, producción, costo unitario, precio y margen. Funciona mejor desde 3 meses cargados.")

    if kpis_mensuales.empty or len(kpis_mensuales) < 2:
        st.info("Carga al menos dos meses para visualizar evolución. Con tres o más meses el análisis de tendencia gana potencia gerencial.")
    else:
        st.markdown("### Producción mensual")
        col1, col2 = st.columns(2)
        with col1:
            fig = px.line(kpis_mensuales, x="Periodo", y="UND producidas", markers=True, title="UND producidas empacado")
            fig.update_traces(line_color="#E8650A", line_width=2.5, marker_color="#F5A623", marker_size=7)
            fig.update_layout(height=340, xaxis_tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.line(kpis_mensuales, x="Periodo", y="Kg granel", markers=True, title="Kg producidos granel")
            fig.update_traces(line_color="#F5A623", line_width=2.5, marker_color="#E8650A", marker_size=7)
            fig.update_layout(height=340, xaxis_tickangle=-35)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### KPIs unitarios y margen")
        kpi_long = kpis_mensuales.melt(
            id_vars=["Periodo", "PeriodoOrden"],
            value_vars=["Costo / saco", "Costo comercial / saco", "Precio actual / saco", "Gastos / saco"],
            var_name="KPI",
            value_name="Valor",
        ).sort_values("PeriodoOrden")
        fig = px.line(kpi_long, x="Periodo", y="Valor", color="KPI", markers=True, title="Evolución mensual de KPIs por saco")
        fig.update_layout(height=470, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

        fig = px.line(kpis_mensuales, x="Periodo", y="Margen real", markers=True, title="Margen real mensual")
        fig.update_traces(line_color="#2DBD6E", line_width=2.5, marker_size=8,
                          fill="tozeroy", fillcolor="rgba(45,189,110,0.1)")
        fig.update_yaxes(tickformat=".1%")
        fig.update_layout(height=350, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Utilidad mensualizada de la empresa")
        st.caption("Utilidad total por mes = venta total del mes - costo comercial total del mes. Respeta producto, presentación e impuestos opcionales activos.")
        util_cols = ["Periodo", "Venta total empresa", "Costo comercial total", "Utilidad empresa", "Utilidad empresa con extra", "Utilidad / ton", "Margen real", "Margen con extra"]
        util_mensual = kpis_mensuales[[c for c in util_cols if c in kpis_mensuales.columns]].copy()

        u1, u2, u3, u4 = st.columns(4)
        ultimo_util = kpis_mensuales.iloc[-1]
        with u1:
            kpi("Última utilidad mensual", money(ultimo_util.get("Utilidad empresa", 0)), help_text=str(ultimo_util.get("Periodo", "")), tone="red" if ultimo_util.get("Utilidad empresa", 0) < 0 else "green")
        with u2:
            kpi("Utilidad con extra", money(ultimo_util.get("Utilidad empresa con extra", 0)), help_text=str(ultimo_util.get("Periodo", "")), tone="red" if ultimo_util.get("Utilidad empresa con extra", 0) < 0 else "green")
        with u3:
            kpi("Utilidad / ton", money(ultimo_util.get("Utilidad / ton", 0)), help_text=str(ultimo_util.get("Periodo", "")), tone="red" if ultimo_util.get("Utilidad / ton", 0) < 0 else "green")
        with u4:
            kpi("Margen empresa", pct(ultimo_util.get("Margen real", 0)), help_text=str(ultimo_util.get("Periodo", "")), tone="red" if ultimo_util.get("Margen real", 0) < 0 else "green")

        fig = px.bar(kpis_mensuales, x="Periodo", y="Utilidad empresa", title="Utilidad mensualizada de la empresa", text="Utilidad empresa")
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig.add_hline(y=0, line_dash="dot", line_color="#94A3B8", line_width=1.2)
        fig.update_layout(height=430, xaxis_tickangle=-35, margin=dict(l=30, r=30, t=70, b=110))
        st.plotly_chart(fig, use_container_width=True)

        util_long = kpis_mensuales.melt(
            id_vars=["Periodo", "PeriodoOrden"],
            value_vars=["Venta total empresa", "Costo comercial total", "Utilidad empresa"],
            var_name="Métrica",
            value_name="Valor",
        ).sort_values("PeriodoOrden")
        fig = px.line(util_long, x="Periodo", y="Valor", color="Métrica", markers=True, title="Venta, costo y utilidad total mensual")
        fig.update_layout(height=430, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)
        dataframe_gerencial(util_mensual)

        st.markdown("### Gastos/costos representativos por observación")
        top_obs_n = st.slider("Número de observaciones representativas", min_value=6, max_value=20, value=12, step=1, key="top_obs_evolucion")
        serie_obs, top_obs = serie_mensual_observaciones(df, INDICES_COSTO_TOTAL, top_obs_n)
        if serie_obs.empty:
            st.info("No hay datos suficientes para series por observación.")
        else:
            modo_escala_obs = st.radio(
                "Modo de escala para observaciones",
                ["Doble escala", "Normal", "Logarítmica"],
                horizontal=True,
                index=0,
                key="modo_escala_observaciones",
                help="Doble escala separa el rubro dominante en el eje izquierdo y los demás rubros en el eje derecho para que las tendencias pequeñas no queden aplastadas.",
            )

            if modo_escala_obs == "Doble escala":
                ranking_obs = (
                    serie_obs.groupby("Observacion", as_index=False)["Valor"]
                    .sum()
                    .sort_values("Valor", ascending=False)
                )
                obs_dominante = ranking_obs.iloc[0]["Observacion"]
                df_dom = serie_obs[serie_obs["Observacion"] == obs_dominante].sort_values("PeriodoOrden")
                df_rest = serie_obs[serie_obs["Observacion"] != obs_dominante].sort_values("PeriodoOrden")

                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=df_dom["Periodo"],
                        y=df_dom["Valor"],
                        mode="lines+markers",
                        name=f"Dominante: {obs_dominante}",
                        yaxis="y",
                        line=dict(width=3.5, color="#E8650A"),
                        marker=dict(size=9, color="#F5A623", line=dict(color="#E8650A", width=2)),
                        hovertemplate="%{x}<br>%{fullData.name}<br>Valor: %{y:,.0f}<extra></extra>",
                    )
                )

                for obs_name in df_rest["Observacion"].dropna().unique():
                    temp = df_rest[df_rest["Observacion"] == obs_name]
                    fig.add_trace(
                        go.Scatter(
                            x=temp["Periodo"],
                            y=temp["Valor"],
                            mode="lines+markers",
                            name=obs_name,
                            yaxis="y2",
                            line=dict(width=2),
                            marker=dict(size=6),
                            hovertemplate="%{x}<br>%{fullData.name}<br>Valor: %{y:,.0f}<extra></extra>",
                        )
                    )

                fig.update_layout(
                    title="Evolución de observaciones más representativas · doble escala",
                    xaxis=dict(title="Periodo", tickangle=-35),
                    yaxis=dict(title="Rubro dominante", tickformat=",.0f", side="left", showgrid=True),
                    yaxis2=dict(title="Otros rubros", tickformat=",.0f", overlaying="y", side="right", showgrid=False),
                    legend=dict(title="Observación", orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
                    height=640,
                    margin=dict(l=70, r=330, t=80, b=120),
                )
                st.caption(f"Eje izquierdo: {obs_dominante}. Eje derecho: demás observaciones representativas.")
                st.plotly_chart(fig, use_container_width=True)

            elif modo_escala_obs == "Logarítmica":
                fig = px.line(serie_obs, x="Periodo", y="Valor", color="Observacion", markers=True, title="Evolución de observaciones más representativas · escala logarítmica")
                fig.update_yaxes(type="log", title="Valor (escala log)")
                fig.update_layout(height=620, xaxis_tickangle=-35, legend_title_text="Observación", margin=dict(r=260))
                st.plotly_chart(fig, use_container_width=True)

            else:
                fig = px.line(serie_obs, x="Periodo", y="Valor", color="Observacion", markers=True, title="Evolución de observaciones más representativas")
                fig.update_layout(height=620, xaxis_tickangle=-35, legend_title_text="Observación", margin=dict(r=260))
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("### Micrográficos de tendencia")
            st.caption("Cada micrográfico muestra la evolución mensual de una observación relevante. Útil para detectar tendencia antes de que se vuelva alarma.")
            top_obs = top_obs[:12]
            for start in range(0, len(top_obs), 3):
                cols = st.columns(3)
                for col, obs_name in zip(cols, top_obs[start:start+3]):
                    mini = serie_obs[serie_obs["Observacion"] == obs_name].sort_values("PeriodoOrden")
                    with col:
                        fig = px.line(mini, x="Periodo", y="Valor", markers=True, title=obs_name[:58])
                        fig.update_layout(height=270, margin=dict(l=20, r=20, t=55, b=70), xaxis_tickangle=-35, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)

            st.markdown("### Tabla mensual de KPIs")
            dataframe_gerencial(kpis_mensuales)

        st.markdown("### Lectura automática de tendencia")
        st.info(tendencia_texto)

with tabs[8]:
    st.subheader("Calidad de datos y diagnóstico")
    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi("Filas Consolidado", num(len(df), 0))
    with c2: kpi("Filas mes seleccionado", num(len(df_mes), 0))
    with c3: kpi("Filas REVISAR", num(int((df["Indice_norm"] == norm_text("REVISAR")).sum()), 0))
    with c4: kpi("Valor total mes", money(float(df_mes["Valor"].sum())))

    st.markdown("### Validaciones críticas")
    val = pd.DataFrame([
        ["Kg granel", OBS_KG_GRANEL, kg_granel, "OK" if kg_granel > 0 else "REVISAR"],
        ["UND empacado", OBS_UND_EMPACADO, und_emp, "OK" if und_emp > 0 else "REVISAR"],
        ["UND vendidas", OBS_CANTIDAD_VENDIDA, und_vendida, "OK" if und_vendida > 0 else "SIN VENTA"],
        ["Precio bolsa", OBS_PRECIO_BOLSA_USADA, precio_actual, "OK" if precio_actual > 0 else "SIN VENTA"],
        ["Cemento transferido", OBS_CEMENTO_GRANEL_TRANSFERIDO, cemento_transf, "OK" if cemento_transf > 0 else "REVISAR"],
        [INDICES_EMPACADO[0], "Índice", suma_indices(df_mes, [INDICES_EMPACADO[0]]), "OK" if suma_indices(df_mes, [INDICES_EMPACADO[0]]) > 0 else "REVISAR"],
        [INDICES_EMPACADO[1], "Índice", suma_indices(df_mes, [INDICES_EMPACADO[1]]), "OK" if suma_indices(df_mes, [INDICES_EMPACADO[1]]) > 0 else "REVISAR"],
        [INDICES_EMPACADO[2], "Índice", suma_indices(df_mes, [INDICES_EMPACADO[2]]), "OK" if suma_indices(df_mes, [INDICES_EMPACADO[2]]) > 0 else "REVISAR"],
    ], columns=["Dato", "Llave buscada", "Valor encontrado", "Estado"])
    dataframe_gerencial(val)

    st.markdown("### Conteo por índice en el mes")
    conteo = df_mes.groupby("Indice", as_index=False).agg(Filas=("Valor", "size"), Valor=("Valor", "sum")).sort_values("Valor", ascending=False)
    dataframe_gerencial(conteo)

    revisar = df[df["Indice_norm"] == norm_text("REVISAR")].copy()
    if not revisar.empty:
        st.markdown("### Filas pendientes REVISAR")
        dataframe_gerencial(revisar[["Produccion", "Indice", "Observacion", "Valor", "Mes", "Ano", "MesNro"]])

with tabs[9]:
    st.subheader("Metas, configuración y exportación")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### Parámetros activos")
        params = pd.DataFrame([
            ["IVA", iva, "%"],
            ["Margen objetivo", margen_obj, "% sobre precio"],
            ["Kg por bolsa", PESO_BOLSA_KG, "kg"],
            ["Mes", periodo.etiqueta, "periodo"],
            ["C IMP REN aplicado al costo", "Sí" if incluir_imp_renta else "No", "opcional"],
            ["C IMP PATR aplicado al costo", "Sí" if incluir_imp_patrimonio else "No", "opcional"],
        ], columns=["Parámetro", "Valor", "Unidad"])
        dataframe_gerencial(params)
    with col_b:
        st.markdown("### Metas leídas del Excel")
        if metas_df.empty:
            st.info("No se encontró hoja Metas Gerenciales o está vacía.")
        else:
            dataframe_gerencial(metas_df)

    export_resumen = pd.DataFrame([
        ["Costo empacado", costo_emp],
        ["Costo por saco", costo_saco_emp],
        ["Costo total comercial por saco", costo_total_saco_sin_extra],
        ["Precio actual", precio_actual],
        ["Precio objetivo antes IVA", precio_obj_sin_extra],
        ["Precio objetivo con IVA", precio_obj_sin_extra_iva],
        ["Margen real", margen_real],
        ["Utilidad por saco", utilidad_saco],
    ], columns=["Métrica", "Valor"])
    export_bytes = to_excel_bytes({
        "Resumen": export_resumen,
        "Alertas": alertas_df,
        "Impuestos Opcionales": impuestos_opcionales_df,
        "Datos Mes": df_mes[["Produccion", "Indice", "Observacion", "Valor", "Mes", "Ano", "MesNro"]],
    })
    st.download_button(
        "Descargar paquete de análisis del mes (.xlsx)",
        data=export_bytes,
        file_name=f"analisis_costeo_{periodo.ano}_{periodo.mes_nro:02d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )




with tabs[10]:
    st.subheader("Metodología de costeo y cálculo del valor comercial")
    st.caption("Explicación auditable del paso a paso matemático usado por el dashboard.")

    st.markdown("### 1. Base de datos utilizada")
    st.markdown(
        """
        La fuente oficial del dashboard es la hoja **Consolidado**, con la estructura:

        **Producción | Índice | Concepto | Valor | Mes | Año | MesNro**

        El cálculo se realiza para el mes y año seleccionados en la barra lateral.
        """
    )

    st.markdown("### 2. Costo industrial del empacado")
    paso_emp = pd.DataFrame([
        ["Materia prima empacado", INDICES_EMPACADO[0], c_mp_emp, safe_div(c_mp_emp, und_emp), safe_div(c_mp_emp, kg_emp)],
        ["Mano de obra empacado", INDICES_EMPACADO[1], c_mo_emp, safe_div(c_mo_emp, und_emp), safe_div(c_mo_emp, kg_emp)],
        ["CIF empacado", INDICES_EMPACADO[2], c_cif_emp, safe_div(c_cif_emp, und_emp), safe_div(c_cif_emp, kg_emp)],
        ["Costo empacado completo", " + ".join(INDICES_EMPACADO), costo_emp, costo_saco_emp, costo_kg_emp],
    ], columns=["Paso", "Índices / fórmula", "Valor total", "$/saco", "$/kg"])
    dataframe_gerencial(paso_emp)

    st.markdown("### 3. Gastos asignables al producto vendido")
    paso_gastos = pd.DataFrame([
        ["Administración mano de obra", "C MO ADM", suma_indices(df_mes, ["C MO ADM"]), safe_div(suma_indices(df_mes, ["C MO ADM"]), und_emp), safe_div(suma_indices(df_mes, ["C MO ADM"]), kg_emp)],
        ["Administración CIF", "C CIF ADM", suma_indices(df_mes, ["C CIF ADM"]), safe_div(suma_indices(df_mes, ["C CIF ADM"]), und_emp), safe_div(suma_indices(df_mes, ["C CIF ADM"]), kg_emp)],
        ["Ventas mano de obra", "C MO VEN", suma_indices(df_mes, ["C MO VEN"]), safe_div(suma_indices(df_mes, ["C MO VEN"]), und_emp), safe_div(suma_indices(df_mes, ["C MO VEN"]), kg_emp)],
        ["Ventas CIF", "C CIF VEN", suma_indices(df_mes, ["C CIF VEN"]), safe_div(suma_indices(df_mes, ["C CIF VEN"]), und_emp), safe_div(suma_indices(df_mes, ["C CIF VEN"]), kg_emp)],
        ["Financieros", "C FIN", suma_indices(df_mes, INDICES_FINANCIEROS), safe_div(suma_indices(df_mes, INDICES_FINANCIEROS), und_emp), safe_div(suma_indices(df_mes, INDICES_FINANCIEROS), kg_emp)],
        ["Impuestos", "C IMP", suma_indices(df_mes, INDICES_IMPUESTOS_BASE), safe_div(suma_indices(df_mes, INDICES_IMPUESTOS_BASE), und_emp), safe_div(suma_indices(df_mes, INDICES_IMPUESTOS_BASE), kg_emp)],
        ["Total gastos asignables", " + ".join(INDICES_GASTOS_COMERCIALES), costos_gastos, gastos_saco, gastos_kg],
    ], columns=["Paso", "Índices / fórmula", "Valor total", "$/saco", "$/kg"])
    dataframe_gerencial(paso_gastos)

    st.markdown("### Impuestos opcionales de renta y patrimonio")
    st.caption("Estos dos índices son parametrizables. Si están apagados, se reportan pero no se suman al costo total comercial.")
    dataframe_gerencial(impuestos_opcionales_df)

    st.markdown("### 4. Construcción del costo total comercial")
    puente_comercial = pd.DataFrame([
        ["A", "Costo empacado completo / saco", "(" + " + ".join(INDICES_EMPACADO) + ") / UND PRODUCIDAS Q", costo_saco_emp],
        ["B", "Gastos asignados / saco", "(" + " + ".join(INDICES_GASTOS_COMERCIALES) + ") / UND PRODUCIDAS Q", gastos_saco],
        ["C = A + B", "Costo total comercial / saco", "Costo empacado / saco + gastos asignados / saco", costo_total_saco_sin_extra],
        ["D", "Gastos extraordinarios / saco", "Gastos ExtraOrdinarios / UND PRODUCIDAS Q", gastos_extra_saco],
        ["E = C + D", "Costo total comercial con extraordinarios / saco", "Costo comercial sin extra + gasto extraordinario / saco", costo_total_saco_con_extra],
        ["F", "Precio actual / saco", OBS_PRECIO_BOLSA_USADA, precio_actual],
        ["G = F - C", "Utilidad real / saco", "Precio actual - costo total comercial sin extraordinarios", utilidad_saco],
        ["H = G / F", "Margen real", "Utilidad real / saco ÷ precio actual / saco", margen_real],
    ], columns=["Paso", "Concepto", "Fórmula", "Resultado"])
    dataframe_gerencial(puente_comercial)

    st.markdown("### 5. Precio objetivo")
    st.latex(r"Precio\ objetivo\ antes\ de\ IVA = \frac{Costo\ total\ comercial\ por\ saco}{1 - Margen\ objetivo}")
    st.latex(r"Precio\ objetivo\ con\ IVA = Precio\ objetivo\ antes\ de\ IVA \times (1 + IVA)")
    precio_pasos = pd.DataFrame([
        ["Costo total comercial / saco", costo_total_saco_sin_extra],
        ["Margen objetivo seleccionado", margen_obj],
        ["IVA seleccionado", iva],
        ["Precio objetivo antes de IVA", precio_obj_sin_extra],
        ["Precio objetivo con IVA", precio_obj_sin_extra_iva],
        ["Brecha precio actual vs objetivo", brecha_precio],
    ], columns=["Métrica", "Valor"])
    dataframe_gerencial(precio_pasos)

    st.markdown("### 6. Criterio gerencial")
    st.markdown(
        """
        - El **costo total comercial / saco** es el piso económico antes de utilidad.
        - Si el **precio actual** está por debajo del costo total comercial, el margen real será negativo y la alerta debe ser roja.
        - Las mejoras de costo se muestran en verde solo cuando reducen costo o aumentan margen sin comprometer calidad, seguridad, mantenimiento crítico o cumplimiento.
        - Los gastos extraordinarios se muestran como escenario separado para no contaminar el precio recurrente.
        """
    )

with tabs[11]:
    st.subheader("Análisis asistido con ChatGPT")
    st.caption("Genera un prompt ejecutivo con los KPIs, Paretos y alarmas del mes seleccionado.")

    pareto_emp_prompt = resumen_por_observacion(df_mes, INDICES_EMPACADO)
    pareto_total_prompt = pd.concat(
        [
            resumen_por_observacion(df_mes, INDICES_EMPACADO),
            resumen_gastos_comerciales(df_mes),
        ],
        ignore_index=True,
    )
    if not pareto_total_prompt.empty:
        pareto_total_prompt = pareto_total_prompt.groupby("Observacion", as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
        total_prompt = float(pareto_total_prompt["Valor"].sum())
        pareto_total_prompt["Participacion"] = pareto_total_prompt["Valor"].apply(lambda x: safe_div(x, total_prompt))
        pareto_total_prompt["Acumulado"] = pareto_total_prompt["Participacion"].cumsum()

    var_prompt = variaciones_relevantes.copy() if not variaciones_relevantes.empty else variaciones_obs.copy()

    prompt_chatgpt = construir_prompt_chatgpt(
        periodo=periodo,
        costo_emp=costo_emp,
        costo_saco_emp=costo_saco_emp,
        costo_total_saco_sin_extra=costo_total_saco_sin_extra,
        costo_total_saco_con_extra=costo_total_saco_con_extra,
        precio_actual=precio_actual,
        precio_obj_sin_extra=precio_obj_sin_extra,
        precio_obj_sin_extra_iva=precio_obj_sin_extra_iva,
        margen_real=margen_real,
        margen_obj=margen_obj,
        utilidad_saco=utilidad_saco,
        costo_granel=costo_granel,
        costo_kg_granel=costo_kg_granel,
        incremental_saco=incremental_saco,
        gastos_saco=gastos_saco,
        gastos_extra_saco=gastos_extra_saco,
        kg_granel=kg_granel,
        und_emp=und_emp,
        kg_emp=kg_emp,
        alertas_df=alertas_df,
        pareto_emp=pareto_emp_prompt,
        pareto_total=pareto_total_prompt,
        var_df=var_prompt,
        tendencias_df=kpis_mensuales,
        tendencia_texto=tendencia_texto,
    )

    st.markdown("### Prompt preestablecido")
    st.text_area(
        "Copia este prompt en ChatGPT para recibir análisis, alarmas y recomendaciones.",
        prompt_chatgpt,
        height=520,
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        st.link_button("Abrir ChatGPT limpio", "https://chatgpt.com/")
    with c2:
        st.download_button(
            "Descargar prompt .txt",
            data=prompt_chatgpt.encode("utf-8"),
            file_name=f"prompt_chatgpt_costeo_{periodo.ano}_{periodo.mes_nro:02d}.txt",
            mime="text/plain",
        )

    st.info(
        "ChatGPT se abre limpio por seguridad del navegador. Copia el prompt del cuadro o descarga el .txt y pégalo en ChatGPT. "
        "El análisis debe maximizar rentabilidad sin sacrificar calidad, seguridad, mantenimiento crítico ni cumplimiento."
    )


with tabs[12]:
    st.subheader("Utilidad de la empresa")
    st.caption("Vista CFO: utilidad real del mes seleccionado y utilidad proyectada por toneladas para el producto activo.")

    tons_base_util = safe_div(kg_emp, 1000.0)
    sacos_por_ton_util = SACOS_POR_TON
    precio_ton_actual_util = precio_actual * sacos_por_ton_util

    st.markdown("### Resultado real del mes")
    r1, r2, r3, r4 = st.columns(4)
    with r1:
        kpi("Venta total real", money(venta_total_real), help_text=f"{num(und_emp, 0)} bolsas · {num(tons_base_util, 2)} t")
    with r2:
        kpi("Utilidad real empresa", money(utilidad_total_real), help_text=f"Por bolsa: {money(utilidad_saco)}", tone="red" if utilidad_total_real < 0 else "green")
    with r3:
        kpi("Margen real empresa", pct(margen_total_real), tone="red" if margen_total_real < 0 else "green")
    with r4:
        kpi("Utilidad con extraordinarios", money(utilidad_total_real_con_extra), help_text=f"Margen: {pct(margen_total_real_con_extra)}", tone="red" if utilidad_total_real_con_extra < 0 else "green")

    utilidad_real_unitaria = pd.DataFrame([
        ["Venta real", venta_total_real, safe_div(venta_total_real, tons_base_util), safe_div(venta_total_real, kg_emp), safe_div(venta_total_real, und_emp)],
        ["Costo comercial real sin extraordinarios", costo_total_real_sin_extra, safe_div(costo_total_real_sin_extra, tons_base_util), safe_div(costo_total_real_sin_extra, kg_emp), safe_div(costo_total_real_sin_extra, und_emp)],
        ["Utilidad real sin extraordinarios", utilidad_total_real, safe_div(utilidad_total_real, tons_base_util), safe_div(utilidad_total_real, kg_emp), safe_div(utilidad_total_real, und_emp)],
        ["Utilidad real con extraordinarios", utilidad_total_real_con_extra, safe_div(utilidad_total_real_con_extra, tons_base_util), safe_div(utilidad_total_real_con_extra, kg_emp), safe_div(utilidad_total_real_con_extra, und_emp)],
    ], columns=["Concepto", "Total empresa", "$/ton", "$/kg", "$/bolsa"])
    dataframe_gerencial(utilidad_real_unitaria)

    st.markdown("### Proyección ejecutiva por toneladas")
    p1, p2, p3 = st.columns(3)
    with p1:
        toneladas_util = st.number_input("Toneladas proyectadas", min_value=0.0, value=float(tons_base_util if tons_base_util > 0 else 1.0), step=10.0, format="%.2f", key="util_toneladas_proyectadas_simple")
    with p2:
        precio_ton_util = st.number_input("Precio venta / tonelada antes IVA", min_value=0.0, value=float(precio_ton_actual_util if precio_ton_actual_util > 0 else 0.0), step=1000.0, format="%.2f", key="util_precio_tonelada_simple")
    with p3:
        margen_meta_util = st.number_input("Margen meta referencia", min_value=0.0, max_value=0.95, value=float(margen_obj if margen_obj > 0 else 0.15), step=0.01, format="%.2f", key="util_margen_meta_simple")

    factor_util = safe_div(toneladas_util, tons_base_util)
    sacos_util = toneladas_util * sacos_por_ton_util
    kg_util = toneladas_util * 1000.0
    venta_util = toneladas_util * precio_ton_util

    c_adm_util = suma_admin_comercial(df_mes)
    c_ventas_util = suma_ventas_comercial(df_mes)
    c_fin_util = suma_financiera_comercial(df_mes)
    c_imp_util = suma_impuestos_base_comercial(df_mes)
    venta_base_util_ref = venta_total_real if venta_total_real > 0 else max(tons_base_util * precio_ton_actual_util, 1.0)
    ventas_pct_util = safe_div(max(c_ventas_util, 0.0), venta_base_util_ref)

    # Proyección simple y auditable: MP y CIF variables; MO, administración y financieros fijos; ventas % sobre nueva venta.
    mp_util = max(c_mp_emp, 0.0) * factor_util
    cif_util = max(c_cif_emp, 0.0) * factor_util
    mo_util = max(c_mo_emp, 0.0)
    adm_util = max(c_adm_util, 0.0)
    ventas_util = max(venta_util, 0.0) * ventas_pct_util
    fin_util = max(c_fin_util, 0.0)
    imp_util = max(c_imp_util, 0.0)
    costo_total_util = mp_util + cif_util + mo_util + adm_util + ventas_util + fin_util + imp_util
    utilidad_proyectada_empresa = venta_util - costo_total_util
    margen_proyectado_empresa = safe_div(utilidad_proyectada_empresa, venta_util)
    precio_obj_ton_util = safe_div(safe_div(costo_total_util, toneladas_util), 1 - margen_meta_util)

    g1, g2, g3, g4 = st.columns(4)
    with g1:
        kpi("Venta proyectada", money(venta_util), help_text=f"{num(sacos_util, 0)} bolsas · {num(toneladas_util, 2)} t")
    with g2:
        kpi("Costo total proyectado", money(costo_total_util), help_text=f"Costo/ton: {money(safe_div(costo_total_util, toneladas_util))}")
    with g3:
        kpi("Utilidad proyectada empresa", money(utilidad_proyectada_empresa), help_text=f"Por bolsa: {money(safe_div(utilidad_proyectada_empresa, sacos_util))}", tone="red" if utilidad_proyectada_empresa < 0 else "green")
    with g4:
        kpi("Margen proyectado", pct(margen_proyectado_empresa), tone="red" if margen_proyectado_empresa < 0 else "green")

    comparativo_utilidad = pd.DataFrame([
        ["Real mes seleccionado", tons_base_util, und_emp, venta_total_real, costo_total_real_sin_extra, utilidad_total_real, margen_total_real, safe_div(utilidad_total_real, tons_base_util), safe_div(utilidad_total_real, kg_emp), safe_div(utilidad_total_real, und_emp)],
        ["Proyectado por toneladas", toneladas_util, sacos_util, venta_util, costo_total_util, utilidad_proyectada_empresa, margen_proyectado_empresa, safe_div(utilidad_proyectada_empresa, toneladas_util), safe_div(utilidad_proyectada_empresa, kg_util), safe_div(utilidad_proyectada_empresa, sacos_util)],
    ], columns=["Escenario", "Toneladas", "Bolsas", "Venta total", "Costo total", "Utilidad empresa", "Margen", "Utilidad / ton", "Utilidad / kg", "Utilidad / bolsa"])
    dataframe_gerencial(comparativo_utilidad)

    puente_utilidad = pd.DataFrame([
        ["Materia prima", "Variable por toneladas", mp_util, safe_div(mp_util, toneladas_util), safe_div(mp_util, sacos_util)],
        ["CIF producción", "Variable por toneladas", cif_util, safe_div(cif_util, toneladas_util), safe_div(cif_util, sacos_util)],
        ["Mano de obra producción", "Fijo", mo_util, safe_div(mo_util, toneladas_util), safe_div(mo_util, sacos_util)],
        ["Administración", "Fijo", adm_util, safe_div(adm_util, toneladas_util), safe_div(adm_util, sacos_util)],
        ["Costos de venta", "% sobre venta proyectada", ventas_util, safe_div(ventas_util, toneladas_util), safe_div(ventas_util, sacos_util)],
        ["Financieros", "Fijo", fin_util, safe_div(fin_util, toneladas_util), safe_div(fin_util, sacos_util)],
        ["Impuestos base", "Fijo", imp_util, safe_div(imp_util, toneladas_util), safe_div(imp_util, sacos_util)],
        ["Total costo proyectado", "Suma", costo_total_util, safe_div(costo_total_util, toneladas_util), safe_div(costo_total_util, sacos_util)],
    ], columns=["Concepto", "Driver", "Valor proyectado", "$/ton", "$/bolsa"])
    dataframe_gerencial(puente_utilidad)

    st.info(f"Precio objetivo para margen meta: {fmt_money(precio_obj_ton_util)}/ton · {fmt_money(safe_div(precio_obj_ton_util, sacos_por_ton_util))}/bolsa.")


with tabs[13]:
    st.subheader("Simulador de precios por toneladas producidas")
    st.caption(
        "Modelo aprobado: materias primas escalan con producción; administración y mano de obra de producción permanecen constantes; "
        "costos de venta escalan con la nueva venta. Renta y patrimonio se pueden prender/apagar de forma independiente para el costeo real y para la proyección."
    )

    tons_base = safe_div(kg_emp, 1000)
    sacos_por_ton = SACOS_POR_TON
    precio_ton_actual = precio_actual * sacos_por_ton
    venta_base = und_emp * precio_actual

    c_adm_base = suma_admin_comercial(df_mes)
    c_ventas_base = suma_ventas_comercial(df_mes)
    c_fin_base = suma_financiera_comercial(df_mes)
    c_imp_base = suma_impuestos_base_comercial(df_mes)

    def _sim_cost_value(value: float) -> float:
        """Base conservadora para proyección: un crédito contable negativo no debe bajar artificialmente el costo unitario al simular volumen."""
        try:
            x = float(value)
        except Exception:
            return 0.0
        if pd.isna(x):
            return 0.0
        return max(x, 0.0)

    # Bases usadas por el simulador. Los valores negativos se tratan como ajustes contables,
    # no como costos estructurales que puedan reducir artificialmente el costo unitario proyectado.
    mp_base_modelo = _sim_cost_value(c_mp_emp)
    mo_base_modelo = _sim_cost_value(c_mo_emp)
    cif_base_modelo = _sim_cost_value(c_cif_emp)
    adm_base_modelo = _sim_cost_value(c_adm_base)
    ventas_base_modelo = _sim_cost_value(c_ventas_base)
    fin_base_modelo = _sim_cost_value(c_fin_base)
    imp_base_modelo = _sim_cost_value(c_imp_base)
    imp_renta_modelo = _sim_cost_value(imp_renta_total)
    imp_patrimonio_modelo = _sim_cost_value(imp_patrimonio_total)
    extra_base_modelo = _sim_cost_value(gastos_extra)

    costo_ventas_pct_base = safe_div(ventas_base_modelo, venta_base)

    ajustes_negativos = pd.DataFrame([
        [INDICES_EMPACADO[0], c_mp_emp],
        [INDICES_EMPACADO[1], c_mo_emp],
        [INDICES_EMPACADO[2], c_cif_emp],
        ["C MO ADM + C CIF ADM", c_adm_base],
        ["C MO VEN + C CIF VEN", c_ventas_base],
        ["C FIN", c_fin_base],
        ["C IMP", c_imp_base],
        ["C IMP REN", imp_renta_total],
        ["C IMP PATR", imp_patrimonio_total],
        ["Gastos extraordinarios", gastos_extra],
    ], columns=["Rubro", "Valor contable"])
    ajustes_negativos = ajustes_negativos[ajustes_negativos["Valor contable"] < 0].copy()

    if tons_base <= 0:
        st.error("No hay toneladas base válidas. Revise UND PRODUCIDAS Q en el Consolidado.")
        st.stop()

    if not ajustes_negativos.empty:
        with st.expander("Ajustes contables negativos detectados en el mes"):
            st.warning(
                "Para la simulación de volumen, los rubros negativos se consideran ajustes o créditos contables y no reducen el costo proyectado. "
                "Esto evita que una menor producción aparezca artificialmente más barata o que una mayor producción aparezca más costosa por distorsiones contables."
            )
            dataframe_gerencial(ajustes_negativos)

    if imp_renta_total == 0 and imp_patrimonio_total == 0:
        st.info("En este mes C IMP REN y C IMP PATR tienen valor cero o no aparecen en el Consolidado; por eso sus interruptores no cambian el costo.")

    st.markdown("### Parámetros de simulación")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        toneladas_sim = st.number_input(
            "Toneladas proyectadas",
            min_value=0.0,
            value=float(tons_base if tons_base > 0 else 1.0),
            step=10.0,
            format="%.2f",
            key="pricing_toneladas_sim",
        )
    with col2:
        precio_ton_sim = st.number_input(
            "Precio venta / tonelada antes IVA",
            min_value=0.0,
            value=float(precio_ton_actual if precio_ton_actual > 0 else 0.0),
            step=1000.0,
            format="%.2f",
            key="pricing_precio_ton_sim",
        )
    with col3:
        margen_meta_sim = st.number_input(
            "Margen meta simulador",
            min_value=0.0,
            max_value=0.95,
            value=float(margen_obj if margen_obj > 0 else 0.15),
            step=0.01,
            format="%.2f",
            key="pricing_margen_meta_sim",
        )
    with col4:
        costo_ventas_pct_sim = st.number_input(
            "Costo de ventas sobre venta",
            min_value=0.0,
            max_value=1.0,
            value=float(costo_ventas_pct_base if costo_ventas_pct_base > 0 else 0.0),
            step=0.005,
            format="%.3f",
            key="pricing_costo_ventas_pct_sim",
            help="Por defecto usa C MO VEN + C CIF VEN dividido entre la venta actual. Si el valor contable venía negativo, usa 0% para no distorsionar la simulación.",
        )

    col_cfg1, col_cfg2, col_cfg3, col_cfg4 = st.columns(4)
    with col_cfg1:
        comportamiento_cif = st.selectbox(
            "CIF producción",
            ["Variable por toneladas", "Fijo", "Semi-variable 50/50"],
            index=0,
            key="pricing_cif_behavior",
        )
    with col_cfg2:
        incluir_fin_sim = st.checkbox("Incluir C FIN", value=True, key="pricing_incluir_fin")
    with col_cfg3:
        incluir_imp_base_sim = st.checkbox("Incluir C IMP", value=True, key="pricing_incluir_imp_base")
    with col_cfg4:
        incluir_extra_sim = st.checkbox("Incluir gastos extraordinarios", value=False, key="pricing_incluir_extra")

    col_tax1, col_tax2, col_tax3, col_tax4 = st.columns(4)
    with col_tax1:
        incluir_imp_renta_sim = st.checkbox(
            "Incluir C IMP REN proyectado",
            value=bool(incluir_imp_renta),
            key="pricing_incluir_imp_renta_sim",
            help="Control independiente para la producción proyectada. No modifica el costeo real de la barra lateral.",
        )
    with col_tax2:
        incluir_imp_patrimonio_sim = st.checkbox(
            "Incluir C IMP PATR proyectado",
            value=bool(incluir_imp_patrimonio),
            key="pricing_incluir_imp_patrimonio_sim",
            help="Control independiente para la producción proyectada. No modifica el costeo real de la barra lateral.",
        )
    with col_tax3:
        kpi("C IMP REN", "Incluido" if incluir_imp_renta_sim else "Excluido", help_text=f"Valor detectado: {money(imp_renta_total)}", tone="yellow" if incluir_imp_renta_sim else "neutral")
    with col_tax4:
        kpi("C IMP PATR", "Incluido" if incluir_imp_patrimonio_sim else "Excluido", help_text=f"Valor detectado: {money(imp_patrimonio_total)}", tone="yellow" if incluir_imp_patrimonio_sim else "neutral")

    # Modelo CFO normalizado:
    # El simulador debe reconciliar contra el costo real del mes y luego separar el costo en:
    # 1) paquete variable normalizado, que escala con toneladas/venta, y
    # 2) paquete fijo normalizado, que se mantiene constante.
    # Con esto, si el precio por tonelada no cambia y no se activan costos nuevos, producir más no encarece el costo unitario.
    precio_ton_base_ref = precio_ton_actual if precio_ton_actual > 0 else precio_ton_sim
    venta_base_ref = tons_base * precio_ton_base_ref
    ventas_base_usuario = venta_base_ref * costo_ventas_pct_sim

    def _pos(x: float) -> float:
        try:
            val = float(x)
        except Exception:
            return 0.0
        if pd.isna(val):
            return 0.0
        return max(val, 0.0)

    if comportamiento_cif == "Variable por toneladas":
        cif_var_raw = _pos(c_cif_emp)
        cif_fixed_raw = 0.0
    elif comportamiento_cif == "Semi-variable 50/50":
        cif_var_raw = _pos(c_cif_emp) * 0.5
        cif_fixed_raw = _pos(c_cif_emp) * 0.5
    else:
        cif_var_raw = 0.0
        cif_fixed_raw = _pos(c_cif_emp)

    fixed_raw_parts = {
        "mo": _pos(c_mo_emp),
        "cif_fixed": cif_fixed_raw,
        "adm": _pos(c_adm_base),
        "fin": _pos(c_fin_base) if incluir_fin_sim else 0.0,
        "imp_base": _pos(c_imp_base) if incluir_imp_base_sim else 0.0,
        "imp_renta": _pos(imp_renta_total) if incluir_imp_renta_sim else 0.0,
        "imp_patr": _pos(imp_patrimonio_total) if incluir_imp_patrimonio_sim else 0.0,
        "extra": _pos(gastos_extra) if incluir_extra_sim else 0.0,
    }
    variable_raw_parts = {
        "mp": _pos(c_mp_emp),
        "cif_var": cif_var_raw,
        "ventas": _pos(ventas_base_usuario),
    }

    base_total_cfo = (
        c_mp_emp
        + c_mo_emp
        + c_cif_emp
        + c_adm_base
        + ventas_base_usuario
        + (c_fin_base if incluir_fin_sim else 0.0)
        + (c_imp_base if incluir_imp_base_sim else 0.0)
        + (imp_renta_total if incluir_imp_renta_sim else 0.0)
        + (imp_patrimonio_total if incluir_imp_patrimonio_sim else 0.0)
        + (gastos_extra if incluir_extra_sim else 0.0)
    )
    base_total_cfo = max(float(base_total_cfo), 0.0)

    fixed_raw_total = sum(fixed_raw_parts.values())
    fixed_base_cfo = min(fixed_raw_total, base_total_cfo) if base_total_cfo > 0 else 0.0
    fixed_scale_cfo = safe_div(fixed_base_cfo, fixed_raw_total) if fixed_raw_total > 0 else 0.0

    variable_base_cfo = max(base_total_cfo - fixed_base_cfo, 0.0)
    variable_raw_total = sum(variable_raw_parts.values())
    variable_scale_cfo = safe_div(variable_base_cfo, variable_raw_total) if variable_raw_total > 0 else 0.0

    mp_base_modelo = variable_raw_parts["mp"] * variable_scale_cfo
    cif_var_base_modelo = variable_raw_parts["cif_var"] * variable_scale_cfo
    ventas_base_modelo = variable_raw_parts["ventas"] * variable_scale_cfo

    mo_base_modelo = fixed_raw_parts["mo"] * fixed_scale_cfo
    cif_fixed_base_modelo = fixed_raw_parts["cif_fixed"] * fixed_scale_cfo
    adm_base_modelo = fixed_raw_parts["adm"] * fixed_scale_cfo
    fin_base_modelo = fixed_raw_parts["fin"] * fixed_scale_cfo
    imp_base_modelo = fixed_raw_parts["imp_base"] * fixed_scale_cfo
    imp_renta_modelo = fixed_raw_parts["imp_renta"] * fixed_scale_cfo
    imp_patrimonio_modelo = fixed_raw_parts["imp_patr"] * fixed_scale_cfo
    extra_base_modelo = fixed_raw_parts["extra"] * fixed_scale_cfo
    cif_base_modelo = cif_var_base_modelo + cif_fixed_base_modelo

    modelo_cfo_df = pd.DataFrame([
        ["Costo base conciliado", base_total_cfo],
        ["Paquete variable normalizado", variable_base_cfo],
        ["Paquete fijo normalizado", fixed_base_cfo],
        ["Escala aplicada a variables", variable_scale_cfo],
        ["Escala aplicada a fijos", fixed_scale_cfo],
    ], columns=["Métrica", "Valor"])

    def calcular_proyeccion_volumen(toneladas: float, precio_ton: float) -> dict[str, float]:
        factor = safe_div(toneladas, tons_base)
        sacos = toneladas * sacos_por_ton
        kg = toneladas * 1000.0
        venta = toneladas * precio_ton
        venta_factor = safe_div(venta, venta_base_ref)

        mp = mp_base_modelo * factor
        cif_var = cif_var_base_modelo * factor
        cif_fixed = cif_fixed_base_modelo
        cif = cif_var + cif_fixed
        ventas = ventas_base_modelo * venta_factor
        mo = mo_base_modelo
        adm = adm_base_modelo
        fin = fin_base_modelo
        imp_base = imp_base_modelo
        imp_renta = imp_renta_modelo
        imp_patr = imp_patrimonio_modelo
        extra = extra_base_modelo

        total = mp + mo + cif + adm + ventas + fin + imp_base + imp_renta + imp_patr + extra

        # Guardia gerencial: si se simula más producción al mismo precio y sin costos nuevos,
        # el costo unitario no debe subir por el solo efecto de escala.
        costo_ton_base_modelo = safe_div(base_total_cfo, tons_base)
        precio_sin_cambio = abs(float(precio_ton) - float(precio_ton_base_ref)) < 1e-6
        if precio_sin_cambio and toneladas >= tons_base and costo_ton_base_modelo > 0:
            costo_ton_calc = safe_div(total, toneladas)
            if costo_ton_calc > costo_ton_base_modelo:
                total = costo_ton_base_modelo * toneladas

        return {
            "factor": factor,
            "sacos": sacos,
            "kg": kg,
            "venta": venta,
            "mp": mp,
            "mo": mo,
            "cif": cif,
            "adm": adm,
            "ventas": ventas,
            "fin": fin,
            "imp_base": imp_base,
            "imp_renta": imp_renta,
            "imp_patr": imp_patr,
            "extra": extra,
            "total": total,
            "costo_ton": safe_div(total, toneladas),
            "costo_kg": safe_div(total, kg),
            "costo_saco": safe_div(total, sacos),
            "precio_kg": safe_div(precio_ton, 1000.0),
            "precio_saco": safe_div(precio_ton, sacos_por_ton),
        }

    proy = calcular_proyeccion_volumen(toneladas_sim, precio_ton_sim)
    factor_prod = proy["factor"]
    sacos_sim = proy["sacos"]
    kg_sim = proy["kg"]
    venta_sim = proy["venta"]
    mp_sim = proy["mp"]
    mo_prod_sim = proy["mo"]
    cif_prod_sim = proy["cif"]
    adm_sim = proy["adm"]
    ventas_sim = proy["ventas"]
    fin_sim = proy["fin"]
    imp_base_sim = proy["imp_base"]
    imp_renta_sim = proy["imp_renta"]
    imp_patr_sim = proy["imp_patr"]
    extra_sim = proy["extra"]
    costo_total_sim = proy["total"]
    costo_ton_sim = proy["costo_ton"]
    costo_kg_sim = proy["costo_kg"]
    costo_saco_sim = proy["costo_saco"]
    precio_kg_sim = proy["precio_kg"]
    precio_saco_sim = proy["precio_saco"]

    utilidad_sim = venta_sim - costo_total_sim
    margen_sim = safe_div(utilidad_sim, venta_sim)
    precio_eq_ton = costo_ton_sim
    precio_obj_ton = safe_div(costo_ton_sim, 1 - margen_meta_sim)
    precio_obj_kg_sim = safe_div(precio_obj_ton, 1000.0)
    precio_obj_saco_sim = safe_div(precio_obj_ton, sacos_por_ton)
    precio_obj_ton_iva = precio_obj_ton * (1 + iva)
    precio_obj_saco_iva = precio_obj_saco_sim * (1 + iva)

    st.markdown("### Resultado ejecutivo")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi("Factor de producción", f"{num(factor_prod, 2)}x", help_text=f"Base actual: {num(tons_base, 2)} t")
    with k2:
        kpi("Costo proyectado / tonelada", money(costo_ton_sim), help_text=f"Bolsa: {money(costo_saco_sim)} · kg: {money(costo_kg_sim)}")
    with k3:
        kpi("Margen proyectado", pct(margen_sim), tone="red" if margen_sim < 0 else "green")
    with k4:
        kpi("Utilidad proyectada", money(utilidad_sim), tone="red" if utilidad_sim < 0 else "green")

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi("Precio equilibrio / tonelada", money(precio_eq_ton), help_text=f"kg: {money(costo_kg_sim)} · bolsa: {money(costo_saco_sim)}")
    with k2:
        kpi("Precio objetivo / tonelada", money(precio_obj_ton), help_text=f"Margen meta: {pct(margen_meta_sim)}")
    with k3:
        kpi("Precio objetivo / saco", money(precio_obj_saco_sim), help_text=f"kg objetivo: {money(precio_obj_kg_sim)}")
    with k4:
        kpi("Precio objetivo + IVA / saco", money(precio_obj_saco_iva), help_text=f"ton + IVA: {money(precio_obj_ton_iva)}")

    precio_kg_actual = safe_div(precio_actual, PESO_BOLSA_KG)
    costo_total_real_actual = costo_emp + costos_gastos
    costo_ton_actual_real = costo_total_kg_sin_extra * 1000.0
    utilidad_saco_sim = precio_saco_sim - costo_saco_sim
    utilidad_kg_actual = precio_kg_actual - costo_total_kg_sin_extra
    utilidad_kg_sim = precio_kg_sim - costo_kg_sim

    st.markdown("### Valor unitario actual vs producción proyectada")
    u1, u2, u3, u4 = st.columns(4)
    with u1:
        kpi("Costo actual", money(costo_ton_actual_real) + " / ton", help_text=f"kg: {money(costo_total_kg_sin_extra)} · bolsa: {money(costo_total_saco_sin_extra)}")
    with u2:
        kpi("Precio actual", money(precio_ton_actual) + " / ton", help_text=f"kg: {money(precio_kg_actual)} · bolsa: {money(precio_actual)}")
    with u3:
        kpi("Costo proyectado", money(costo_ton_sim) + " / ton", help_text=f"kg: {money(costo_kg_sim)} · bolsa: {money(costo_saco_sim)}")
    with u4:
        kpi("Precio proyectado", money(precio_ton_sim) + " / ton", help_text=f"kg: {money(precio_kg_sim)} · bolsa: {money(precio_saco_sim)}")

    comparativo_unitario_df = pd.DataFrame([
        [
            "Actual realmente producido",
            tons_base,
            kg_emp,
            und_emp,
            costo_total_real_actual,
            costo_total_kg_sin_extra,
            costo_total_saco_sin_extra,
            costo_ton_actual_real,
            precio_kg_actual,
            precio_actual,
            precio_ton_actual,
            utilidad_kg_actual,
            utilidad_saco,
            margen_real,
            "REN: " + ("Sí" if incluir_imp_renta else "No") + " · PATR: " + ("Sí" if incluir_imp_patrimonio else "No"),
        ],
        [
            "Proyectado simulado",
            toneladas_sim,
            kg_sim,
            sacos_sim,
            costo_total_sim,
            costo_kg_sim,
            costo_saco_sim,
            costo_ton_sim,
            precio_kg_sim,
            precio_saco_sim,
            precio_ton_sim,
            utilidad_kg_sim,
            utilidad_saco_sim,
            margen_sim,
            "REN: " + ("Sí" if incluir_imp_renta_sim else "No") + " · PATR: " + ("Sí" if incluir_imp_patrimonio_sim else "No"),
        ],
    ], columns=[
        "Escenario", "Toneladas", "Kg", f"Bolsas {PESO_BOLSA_KG:g} kg", "Costo total", "Costo / kg", "Costo / bolsa", "Costo / tonelada",
        "Precio / kg", "Precio / bolsa", "Precio / tonelada", "Utilidad / kg", "Utilidad / bolsa", "Margen", "Impuestos opcionales",
    ])
    dataframe_gerencial(comparativo_unitario_df)

    st.markdown("### Impacto de impuestos opcionales")
    impuestos_impacto_df = pd.DataFrame([
        ["C IMP REN", imp_renta_total, "Sí" if incluir_imp_renta else "No", "Sí" if incluir_imp_renta_sim else "No", imp_renta_sim, safe_div(imp_renta_sim, kg_sim), safe_div(imp_renta_sim, sacos_sim), safe_div(imp_renta_sim, toneladas_sim)],
        ["C IMP PATR", imp_patrimonio_total, "Sí" if incluir_imp_patrimonio else "No", "Sí" if incluir_imp_patrimonio_sim else "No", imp_patr_sim, safe_div(imp_patr_sim, kg_sim), safe_div(imp_patr_sim, sacos_sim), safe_div(imp_patr_sim, toneladas_sim)],
    ], columns=["Índice", "Valor detectado", "Aplica real", "Aplica proyectado", "Valor proyectado incluido", "Impacto / kg", "Impacto / bolsa", "Impacto / ton"])
    dataframe_gerencial(impuestos_impacto_df)

    st.markdown("### Conciliación CFO del modelo")
    st.caption("El simulador normaliza la base para que el escenario 1,00x reconcilie con el costo real seleccionado y para que la economía de escala sea coherente: fijos se diluyen y variables conservan costo unitario.")
    dataframe_gerencial(modelo_cfo_df)

    st.markdown("### Puente de costos proyectado")
    simulacion_df = pd.DataFrame([
        ["Materias primas", "Variable por toneladas", c_mp_emp, mp_base_modelo, factor_prod, mp_sim, safe_div(mp_sim, toneladas_sim), safe_div(mp_sim, sacos_sim)],
        ["Mano de obra producción", "Fijo", c_mo_emp, mo_base_modelo, 1.0, mo_prod_sim, safe_div(mo_prod_sim, toneladas_sim), safe_div(mo_prod_sim, sacos_sim)],
        ["CIF producción", comportamiento_cif, c_cif_emp, cif_base_modelo, safe_div(cif_prod_sim, cif_base_modelo), cif_prod_sim, safe_div(cif_prod_sim, toneladas_sim), safe_div(cif_prod_sim, sacos_sim)],
        ["Administración", "Fijo", c_adm_base, adm_base_modelo, 1.0, adm_sim, safe_div(adm_sim, toneladas_sim), safe_div(adm_sim, sacos_sim)],
        ["Costos de venta", "% sobre nueva venta", c_ventas_base, ventas_base_modelo, costo_ventas_pct_sim, ventas_sim, safe_div(ventas_sim, toneladas_sim), safe_div(ventas_sim, sacos_sim)],
        ["Financieros", "Fijo opcional", c_fin_base, fin_base_modelo, 1.0 if incluir_fin_sim else 0.0, fin_sim, safe_div(fin_sim, toneladas_sim), safe_div(fin_sim, sacos_sim)],
        ["Impuestos base C IMP", "Fijo opcional", c_imp_base, imp_base_modelo, 1.0 if incluir_imp_base_sim else 0.0, imp_base_sim, safe_div(imp_base_sim, toneladas_sim), safe_div(imp_base_sim, sacos_sim)],
        ["Impuesto renta C IMP REN", "Fijo opcional", imp_renta_total, imp_renta_modelo, 1.0 if incluir_imp_renta_sim else 0.0, imp_renta_sim, safe_div(imp_renta_sim, toneladas_sim), safe_div(imp_renta_sim, sacos_sim)],
        ["Impuesto patrimonio C IMP PATR", "Fijo opcional", imp_patrimonio_total, imp_patrimonio_modelo, 1.0 if incluir_imp_patrimonio_sim else 0.0, imp_patr_sim, safe_div(imp_patr_sim, toneladas_sim), safe_div(imp_patr_sim, sacos_sim)],
        ["Gastos extraordinarios", "Fijo opcional", gastos_extra, extra_base_modelo, 1.0 if incluir_extra_sim else 0.0, extra_sim, safe_div(extra_sim, toneladas_sim), safe_div(extra_sim, sacos_sim)],
    ], columns=["Concepto", "Driver", "Valor contable actual", "Base usada simulación", "Factor / tasa", "Valor proyectado", "$/ton", "$/saco"])
    dataframe_gerencial(simulacion_df)

    col_a, col_b = st.columns([1.1, 1])
    with col_a:
        fig = px.bar(
            simulacion_df[simulacion_df["Valor proyectado"] != 0],
            x="Concepto",
            y="Valor proyectado",
            title="Composición del costo proyectado",
            color="Driver",
        )
        fig.update_layout(height=470, xaxis_tickangle=-35, margin=dict(b=135))
        st.plotly_chart(fig, use_container_width=True)
    with col_b:
        sensibilidad_tons = []
        for mult in [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]:
            t = tons_base * mult
            p = calcular_proyeccion_volumen(t, precio_ton_sim)
            ct = p["costo_ton"]
            po = safe_div(ct, 1 - margen_meta_sim)
            sensibilidad_tons.append([
                t,
                mult,
                p["costo_kg"],
                p["costo_saco"],
                p["costo_ton"],
                safe_div(po, 1000.0),
                safe_div(po, sacos_por_ton),
                po,
                p["imp_renta"] + p["imp_patr"],
            ])
        sens_tons_df = pd.DataFrame(
            sensibilidad_tons,
            columns=["Toneladas", "Factor", "Costo / kg", "Costo / bolsa", "Costo / ton", "Precio objetivo / kg", "Precio objetivo / bolsa", "Precio objetivo / ton", "REN + PATR incluido"],
        )
        if sens_tons_df.empty:
            st.info("No hay producción base suficiente para construir sensibilidad.")
        else:
            fig = px.line(
                sens_tons_df,
                x="Toneladas",
                y=["Costo / ton", "Precio objetivo / ton"],
                markers=True,
                title="Sensibilidad costo/precio por toneladas",
            )
            fig.update_layout(height=470)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Sensibilidad tabular")
    if 'sens_tons_df' in locals() and not sens_tons_df.empty:
        dataframe_gerencial(sens_tons_df)

    st.markdown("### Lectura gerencial")
    st.markdown(
        f"""
        - La producción base del mes es **{fmt_number(tons_base, 2)} toneladas**, equivalente a **{fmt_number(und_emp, 0)} sacos**.
        - La simulación proyecta **{fmt_number(toneladas_sim, 2)} toneladas**, con factor **{fmt_number(factor_prod, 2)}x**.
        - Costo actual: **{fmt_money(costo_total_kg_sin_extra)}/kg**, **{fmt_money(costo_total_saco_sin_extra)}/bolsa** y **{fmt_money(costo_ton_actual_real)}/ton**.
        - Costo proyectado: **{fmt_money(costo_kg_sim)}/kg**, **{fmt_money(costo_saco_sim)}/bolsa** y **{fmt_money(costo_ton_sim)}/ton**.
        - La materia prima se extrapola por producción; administración y mano de obra de producción se mantienen fijas.
        - Los costos de venta se calculan como **{fmt_pct(costo_ventas_pct_sim)}** sobre la nueva venta proyectada.
        - La sensibilidad queda conciliada contra el costo real: menos toneladas encarecen el costo unitario y más toneladas diluyen los fijos, salvo que el usuario active costos incrementales o cambie el precio/base de venta.
        - Costeo real: C IMP REN está **{'incluido' if incluir_imp_renta else 'excluido'}** y C IMP PATR está **{'incluido' if incluir_imp_patrimonio else 'excluido'}**.
        - Proyección: C IMP REN está **{'incluido' if incluir_imp_renta_sim else 'excluido'}** y C IMP PATR está **{'incluido' if incluir_imp_patrimonio_sim else 'excluido'}**.
        """
    )


with tabs[14]:
    st.subheader("Escenarios de composición de portafolio de venta")
    st.caption(
        "Construye escenarios con cualquier producto activo de Parametros Productos. "
        "La mezcla, precio y costo por tonelada son editables; los valores por defecto salen del mes seleccionado."
    )

    resumen_productos_df = resumen_productos_periodo(
        df_consolidado_completo,
        productos_disponibles,
        periodo,
        incluir_imp_renta,
        incluir_imp_patrimonio,
    )

    if resumen_productos_df.empty:
        st.warning("No hay productos con datos suficientes para crear escenarios de portafolio.")
    else:
        base_ton_total = float(resumen_productos_df["Toneladas"].sum())
        base_venta_total = float(resumen_productos_df["Venta total"].sum())
        base_utilidad_total = float(resumen_productos_df["Utilidad empresa"].sum())
        base_margen_total = safe_div(base_utilidad_total, base_venta_total)

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            ton_portafolio = st.number_input(
                "Toneladas totales del escenario",
                min_value=0.0,
                value=float(base_ton_total if base_ton_total > 0 else 1000.0),
                step=100.0,
                format="%.2f",
                key="port_ton_total",
            )
        with s2:
            iva_portafolio = st.number_input(
                "IVA escenario",
                min_value=0.0,
                max_value=1.0,
                value=float(iva),
                step=0.01,
                format="%.2f",
                key="port_iva",
            )
        with s3:
            margen_meta_port = st.number_input(
                "Margen meta portafolio",
                min_value=0.0,
                max_value=0.95,
                value=float(margen_obj if margen_obj > 0 else 0.15),
                step=0.01,
                format="%.2f",
                key="port_margen_meta",
            )
        with s4:
            st.metric("Margen real base", fmt_pct(base_margen_total))

        escenario_base = resumen_productos_df.copy()
        if float(escenario_base["Toneladas"].sum()) > 0:
            escenario_base["Mix %"] = escenario_base["Toneladas"].apply(lambda x: safe_div(x, float(escenario_base["Toneladas"].sum())) * 100.0)
        else:
            escenario_base["Mix %"] = safe_div(100.0, len(escenario_base))
        escenario_base["Precio escenario / ton"] = escenario_base["Precio / ton"]
        escenario_base["Costo escenario / ton"] = escenario_base["Costo total / ton"]
        escenario_base["Activo"] = True

        st.markdown("### Parámetros editables del escenario")
        st.caption("Ajusta mezcla de venta, precio y costo por tonelada. La suma de Mix % debería ser 100%; si no lo es, la app normaliza internamente.")
        edit_cols = ["Activo", "Producto", "Nombre corto", "Kg bolsa", "Mix %", "Precio escenario / ton", "Costo escenario / ton", "Margen"]
        escenario_edit = st.data_editor(
            escenario_base[[c for c in edit_cols if c in escenario_base.columns]],
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            column_config={
                "Activo": st.column_config.CheckboxColumn("Activo", default=True),
                "Mix %": st.column_config.NumberColumn("Mix %", min_value=0.0, max_value=100.0, step=1.0, format="%.2f"),
                "Precio escenario / ton": st.column_config.NumberColumn("Precio / ton", min_value=0.0, step=1000.0, format="$ %.2f"),
                "Costo escenario / ton": st.column_config.NumberColumn("Costo / ton", min_value=0.0, step=1000.0, format="$ %.2f"),
                "Kg bolsa": st.column_config.NumberColumn("Kg bolsa", min_value=0.0, step=0.01, format="%.2f"),
                "Margen": st.column_config.NumberColumn("Margen base", format="%.2f"),
            },
            disabled=["Producto", "Nombre corto", "Kg bolsa", "Margen"],
            key="portafolio_editor",
        )

        escenario = escenario_edit.copy()
        escenario = escenario[escenario.get("Activo", True) == True].copy()
        if escenario.empty:
            st.warning("Activa al menos un producto para construir el escenario.")
            st.stop()

        mix_total = float(pd.to_numeric(escenario["Mix %"], errors="coerce").fillna(0).sum())
        if abs(mix_total - 100.0) > 0.01:
            st.warning(f"La mezcla suma {fmt_number(mix_total, 2)}%. Para el cálculo se normaliza a 100%.")
        escenario["Mix normalizado"] = escenario["Mix %"].apply(lambda x: safe_div(float(x), mix_total))
        escenario["Toneladas escenario"] = escenario["Mix normalizado"] * ton_portafolio
        escenario["Kg escenario"] = escenario["Toneladas escenario"] * 1000.0
        escenario["Bolsas escenario"] = escenario.apply(lambda r: safe_div(r["Kg escenario"], r["Kg bolsa"]), axis=1)
        escenario["Venta escenario"] = escenario["Toneladas escenario"] * escenario["Precio escenario / ton"]
        escenario["Costo escenario"] = escenario["Toneladas escenario"] * escenario["Costo escenario / ton"]
        escenario["Utilidad escenario"] = escenario["Venta escenario"] - escenario["Costo escenario"]
        escenario["Margen escenario"] = escenario.apply(lambda r: safe_div(r["Utilidad escenario"], r["Venta escenario"]), axis=1)
        escenario["Precio objetivo / ton"] = escenario.apply(lambda r: safe_div(r["Costo escenario / ton"], 1 - margen_meta_port), axis=1)
        escenario["Precio objetivo + IVA / ton"] = escenario["Precio objetivo / ton"] * (1 + iva_portafolio)
        escenario["Utilidad / bolsa"] = escenario.apply(lambda r: safe_div(r["Utilidad escenario"], r["Bolsas escenario"]), axis=1)
        escenario["Utilidad / ton"] = escenario.apply(lambda r: safe_div(r["Utilidad escenario"], r["Toneladas escenario"]), axis=1)

        venta_esc = float(escenario["Venta escenario"].sum())
        costo_esc = float(escenario["Costo escenario"].sum())
        utilidad_esc = float(escenario["Utilidad escenario"].sum())
        margen_esc = safe_div(utilidad_esc, venta_esc)
        utilidad_ton_esc = safe_div(utilidad_esc, ton_portafolio)

        st.markdown("### Resultado del escenario")
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            kpi("Venta escenario", money(venta_esc), help_text=f"{num(ton_portafolio, 2)} toneladas")
        with r2:
            kpi("Costo escenario", money(costo_esc), help_text=f"{money(safe_div(costo_esc, ton_portafolio))}/ton")
        with r3:
            kpi("Utilidad escenario", money(utilidad_esc), help_text=f"{money(utilidad_ton_esc)}/ton", tone="red" if utilidad_esc < 0 else "green")
        with r4:
            kpi("Margen escenario", pct(margen_esc), tone="red" if margen_esc < 0 else "green")

        r5, r6, r7, r8 = st.columns(4)
        with r5:
            kpi("Diferencia venta vs base", money(venta_esc - base_venta_total))
        with r6:
            kpi("Diferencia utilidad vs base", money(utilidad_esc - base_utilidad_total), tone="red" if (utilidad_esc - base_utilidad_total) < 0 else "green")
        with r7:
            kpi("Margen base", pct(base_margen_total))
        with r8:
            kpi("Mejora margen", pct(margen_esc - base_margen_total), tone="red" if (margen_esc - base_margen_total) < 0 else "green")

        tabla_escenario_cols = [
            "Producto", "Kg bolsa", "Mix %", "Toneladas escenario", "Bolsas escenario",
            "Precio escenario / ton", "Costo escenario / ton", "Venta escenario", "Costo escenario",
            "Utilidad escenario", "Utilidad / ton", "Utilidad / bolsa", "Margen escenario",
            "Precio objetivo / ton", "Precio objetivo + IVA / ton",
        ]
        dataframe_gerencial(escenario[[c for c in tabla_escenario_cols if c in escenario.columns]])

        st.markdown("### Visualización del escenario")
        v1, v2 = st.columns(2)
        with v1:
            fig = px.pie(
                escenario,
                names="Nombre corto",
                values="Venta escenario",
                title="Composición de venta del escenario",
                hole=0.42,
            )
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)
        with v2:
            esc_long = escenario.melt(
                id_vars=["Nombre corto"],
                value_vars=["Venta escenario", "Costo escenario", "Utilidad escenario"],
                var_name="Métrica",
                value_name="Valor",
            )
            fig = px.bar(
                esc_long,
                x="Nombre corto",
                y="Valor",
                color="Métrica",
                barmode="group",
                title="Venta, costo y utilidad por producto",
            )
            fig.update_layout(height=420)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Lectura ejecutiva")
        mejor_producto = escenario.sort_values("Margen escenario", ascending=False).iloc[0]
        mayor_utilidad = escenario.sort_values("Utilidad escenario", ascending=False).iloc[0]
        st.markdown(
            f"""
            - Producto con mayor margen del escenario: **{mejor_producto['Producto']}** con **{fmt_pct(mejor_producto['Margen escenario'])}**.
            - Producto que más utilidad aporta: **{mayor_utilidad['Producto']}** con **{fmt_money(mayor_utilidad['Utilidad escenario'])}**.
            - Utilidad total escenario: **{fmt_money(utilidad_esc)}**, contra utilidad base de **{fmt_money(base_utilidad_total)}**.
            - La arquitectura queda abierta: un nuevo producto entra al escenario al agregarlo como activo en **Parametros Productos** y cargar sus datos en Consolidado.
            """
        )


with tabs[15]:
    st.subheader(f"Costeo integral de ambos productos - {periodo.etiqueta}")
    st.caption(
        "Esta es la vista de costeo CFO: separa producción, venta real e inventario económico. "
        "Cada producto se calcula con su granel propio, su empacado, su presentación, sus gastos y sus ventas reales."
    )

    costeo_df = resumen_productos_periodo(
        df_consolidado_completo,
        productos_disponibles,
        periodo,
        incluir_imp_renta,
        incluir_imp_patrimonio,
    )

    if costeo_df.empty:
        st.info("No hay productos para costear en el periodo seleccionado.")
    else:
        venta_real_total = float(costeo_df["Venta total"].sum())
        costo_ventas_total = float(costeo_df["Costo ventas real"].sum())
        utilidad_real_total = float(costeo_df["Utilidad empresa"].sum())
        costo_produccion_total = float(costeo_df["Costo producción total"].sum())
        inventario_no_vendido_total = float(costeo_df["Costo inventario no vendido"].sum())
        margen_real_total = safe_div(utilidad_real_total, venta_real_total)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi("Venta real empresa", money(venta_real_total), help_text="Solo bolsas vendidas")
        with c2:
            kpi("Costo de ventas real", money(costo_ventas_total), help_text="Costo unitario × bolsas vendidas")
        with c3:
            kpi("Utilidad real empresa", money(utilidad_real_total), help_text=f"Margen: {pct(margen_real_total)}", tone="red" if utilidad_real_total < 0 else "green")
        with c4:
            kpi("Costo producido no vendido", money(inventario_no_vendido_total), help_text="Inventario económico del periodo", tone="yellow" if inventario_no_vendido_total > 0 else "green")

        c5, c6, c7, c8 = st.columns(4)
        with c5:
            kpi("Costo producción total", money(costo_produccion_total), help_text="Costo de ambos productos producidos")
        with c6:
            kpi("Ton producidas", num(float(costeo_df["Toneladas"].sum()), 2))
        with c7:
            kpi("Ton vendidas", num(float(costeo_df["Toneladas vendidas"].sum()), 2))
        with c8:
            kpi("Bolsas no vendidas", num(float(costeo_df["Bolsas no vendidas"].sum()), 2))

        st.markdown("### Cadena de costeo por producto")
        rows = costeo_df.to_dict("records")
        for start_i in range(0, len(rows), 2):
            cols = st.columns(min(2, len(rows[start_i:start_i + 2])))
            for col, row in zip(cols, rows[start_i:start_i + 2]):
                with col:
                    sin_venta = float(row.get("Bolsas vendidas", 0) or 0) <= 0
                    tone = "yellow" if sin_venta else ("red" if float(row.get("Utilidad empresa", 0) or 0) < 0 else "green")
                    st.markdown(
                        f"""
                        <div class="kpi-card kpi-{tone}" style="min-height:340px;">
                          <div>
                            <div class="kpi-label">{escape(str(row.get('Nombre corto', row.get('Producto', 'Producto'))))}</div>
                            <div style="font-family:'Sora',sans-serif;font-size:1.04rem;font-weight:800;color:var(--text-pri);line-height:1.15;margin-bottom:12px;">
                              {escape(str(row.get('Producto','')))}
                            </div>
                            <div style="display:grid;grid-template-columns:1.2fr 1fr;gap:7px 16px;color:var(--text-sec);font-size:.82rem;">
                              <div>Presentación</div><div style="text-align:right;font-weight:800;">{fmt_number(row.get('Kg bolsa',0),2)} kg</div>
                              <div>Costo granel / kg</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Costo granel / kg',0))}</div>
                              <div>Costo empacado / bolsa</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Costo empacado / bolsa',0))}</div>
                              <div>Gastos / bolsa</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Gastos / bolsa',0))}</div>
                              <div>Costo total / bolsa</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Costo total / bolsa',0))}</div>
                              <div>Bolsas producidas</div><div style="text-align:right;font-weight:800;">{fmt_number(row.get('Bolsas producidas',0),2)}</div>
                              <div>Bolsas vendidas</div><div style="text-align:right;font-weight:800;">{fmt_number(row.get('Bolsas vendidas',0),2)}</div>
                              <div>Bolsas no vendidas</div><div style="text-align:right;font-weight:800;">{fmt_number(row.get('Bolsas no vendidas',0),2)}</div>
                              <div>Precio promedio / bolsa</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Precio / bolsa',0))}</div>
                              <div>Venta real</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Venta total',0))}</div>
                              <div>Costo ventas real</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Costo ventas real',0))}</div>
                              <div>Utilidad real</div><div style="text-align:right;font-weight:800;">{fmt_money(row.get('Utilidad empresa',0))}</div>
                              <div>Margen real</div><div style="text-align:right;font-weight:800;">{fmt_pct(row.get('Margen',0))}</div>
                            </div>
                          </div>
                          <div class="kpi-delta">{"Sin ventas: no se reconoce precio promedio ni ingreso" if sin_venta else "Producto con venta real registrada"}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.markdown("### Tabla CFO de costeo por producto")
        cols_costeo = [
            "Producto", "Kg bolsa", "Bolsas producidas", "Bolsas vendidas", "Bolsas no vendidas",
            "Toneladas", "Toneladas vendidas", "Costo granel", "Costo granel / kg",
            "Costo empacado", "Costo empacado / bolsa", "Gastos asignables", "Gastos / bolsa",
            "Costo producción total", "Costo total / bolsa", "Costo total / ton",
            "Precio / bolsa", "Precio / ton", "Venta total", "Costo ventas real",
            "Utilidad empresa", "Utilidad / bolsa", "Utilidad / ton", "Margen",
            "Costo inventario no vendido", "Obs precio bolsa", "Estado",
        ]
        dataframe_gerencial(costeo_df[[c for c in cols_costeo if c in costeo_df.columns]])

        st.markdown("### Producción vs venta")
        pv_df = costeo_df.melt(
            id_vars=["Nombre corto"],
            value_vars=["Bolsas producidas", "Bolsas vendidas", "Bolsas no vendidas"],
            var_name="Métrica",
            value_name="Bolsas",
        )
        fig = px.bar(
            pv_df,
            x="Nombre corto",
            y="Bolsas",
            color="Métrica",
            barmode="group",
            title="Bolsas producidas, vendidas y no vendidas",
        )
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Resultado económico real por producto")
        eco_df = costeo_df.melt(
            id_vars=["Nombre corto"],
            value_vars=["Venta total", "Costo ventas real", "Utilidad empresa", "Costo inventario no vendido"],
            var_name="Métrica",
            value_name="Valor",
        )
        fig = px.bar(
            eco_df,
            x="Nombre corto",
            y="Valor",
            color="Métrica",
            barmode="group",
            title="Venta, costo vendido, utilidad e inventario económico",
        )
        fig.update_layout(height=440)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Lectura gerencial")
        st.markdown(
            """
            - **Costo producción total** mide lo que costó fabricar cada producto en el periodo.
            - **Costo ventas real** mide únicamente el costo asociado a las bolsas efectivamente vendidas.
            - **Costo producido no vendido** no debe confundirse con pérdida comercial: es inventario económico o costo pendiente de monetizar.
            - Si un producto tiene producción pero cero ventas, el precio promedio aplicado es cero y la venta real es cero.
            """
        )
