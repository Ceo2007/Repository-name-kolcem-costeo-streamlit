# app_costeo_cemento_v15_pricing_toneladas.py
# Dashboard gerencial de costeo de cemento - v9 comparaciones seleccionables y tendencias mensuales
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
    font-size:clamp(1.05rem,1.45vw,1.62rem);
    font-weight:700; letter-spacing:-0.025em; line-height:1.1;
    font-variant-numeric:tabular-nums;
}
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


def num(v: float, decimals: int = 0) -> str:
    if v is None or pd.isna(v):
        return "0"
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


def kpi(label: str, value: str, delta: str | None = None, help_text: str | None = None, tone: str | None = None):
    """Tarjeta KPI con semáforo controlado, sin etiquetas HTML visibles y con fuente más balanceada."""
    tone = tone or _tone_from_text(label, value, delta)
    tone = tone if tone in {"green", "yellow", "red", "neutral"} else "neutral"

    label_html = escape(str(label))
    value_html = escape(str(value))
    delta_html = f'<div class="kpi-delta">{escape(str(delta))}</div>' if delta else ""
    help_html = f'<div class="kpi-help">{escape(str(help_text))}</div>' if help_text else ""

    st.markdown(
        f'<div class="kpi-card kpi-{tone}">'
        f'<div>'
        f'<div class="kpi-label">{label_html}</div>'
        f'<div class="kpi-value" title="{value_html}">{value_html}</div>'
        f'</div>'
        f'<div>{delta_html}{help_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Formato gerencial de tablas
# ------------------------------------------------------------

def fmt_number(v: object, decimals: int = 0) -> str:
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
        elif any(k in col_txt for k in ["KG", "UND", "SACOS"]):
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
- Producto vendido actualmente: cemento empacado UG 50 kg.
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
def load_excel(uploaded_bytes: bytes) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
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
    return df, metas, sheets


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
      <div class="hero-subtitle">Análisis ejecutivo de costos industriales &mdash; Empacado · Granel · Comercial · Tendencias · Metodología</div>
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
    df, metas_df, sheet_names = load_excel(uploaded.getvalue())
except Exception as exc:
    st.error(f"No pude leer el archivo: {exc}")
    st.stop()

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

c_mp_ug = suma_indices(df_mes, ["C MP UG"])
c_mo_ug = suma_indices(df_mes, ["C MO UG"])
c_cif_ug = suma_indices(df_mes, ["C CIF UG"])
costo_granel = c_mp_ug + c_mo_ug + c_cif_ug
kg_granel = suma_obs(df_mes, OBS_KG_GRANEL)
costo_kg_granel = safe_div(costo_granel, kg_granel)

c_mp_emp = suma_indices(df_mes, ["C MP EMP"])
c_mo_emp = suma_indices(df_mes, ["C MO EMP"])
c_cif_emp = suma_indices(df_mes, ["C CIF EMP"])
costo_emp = c_mp_emp + c_mo_emp + c_cif_emp
und_emp = suma_obs(df_mes, OBS_UND_EMPACADO)
kg_emp = und_emp * 50
costo_saco_emp = safe_div(costo_emp, und_emp)
costo_kg_emp = safe_div(costo_emp, kg_emp)

cemento_transf = suma_obs(df_mes, OBS_CEMENTO_GRANEL_TRANSFERIDO, INDICES_EMPACADO)
incremental_emp = costo_emp - cemento_transf
incremental_saco = safe_div(incremental_emp, und_emp)
incremental_kg = safe_div(incremental_emp, kg_emp)

costos_gastos = suma_indices(df_mes, INDICES_GASTOS_COMERCIALES)
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
precio_actual = suma_obs(df_mes, OBS_PRECIO_BOLSA)
utilidad_saco = precio_actual - costo_total_saco_sin_extra
margen_real = safe_div(utilidad_saco, precio_actual)
brecha_precio = precio_actual - precio_obj_sin_extra
brecha_margen = margen_real - margen_obj

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
        kg_e = ug * 50
        cg = suma_indices(d, INDICES_GRANEL)
        kg_g = suma_obs(d, OBS_KG_GRANEL)
        gastos = suma_indices(d, INDICES_GASTOS_COMERCIALES)
        precio = suma_obs(d, OBS_PRECIO_BOLSA)
        costo_saco = safe_div(ce, ug)
        costo_comercial = costo_saco + safe_div(gastos, ug)
        utilidad = precio - costo_comercial
        margen = safe_div(utilidad, precio)
        rows.append({
            "Ano": p.ano,
            "Mes": p.mes,
            "MesNro": p.mes_nro,
            "Periodo": p.etiqueta,
            "PeriodoOrden": p.ano * 100 + p.mes_nro,
            "Costo empacado": ce,
            "UND producidas": ug,
            "Kg empacados": kg_e,
            "Costo / saco": costo_saco,
            "Costo comercial / saco": costo_comercial,
            "Precio actual / saco": precio,
            "Utilidad / saco": utilidad,
            "Margen real": margen,
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
    cols = ["Costo / saco", "Costo comercial / saco", "Precio actual / saco", "Utilidad / saco", "Margen real", "Costo granel / kg", "Gastos / saco", "UND producidas"]
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
# Tabs
# ------------------------------------------------------------

tabs = st.tabs([
    "📊 Resumen Gerencial",
    "💰 Precio & Margen",
    "🏭 Granel UG",
    "📦 Empacado 50KG",
    "🧾 Gastos ADM/Ventas",
    "📈 Paretos",
    "↕️ Variaciones",
    "📉 Evolución Mensual",
    "🔍 Calidad de Datos",
    "🎯 Metas / Exportar",
    "📐 Metodología",
    "🤖 Análisis IA",
    "🧮 Simulador Toneladas",
])

with tabs[0]:
    st.subheader(f"Resumen ejecutivo - {periodo.etiqueta}")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Costo empacado completo", money(costo_emp), f"{status_icon(var_costo_saco)} {delta_costo_saco}")
    with c2:
        kpi("Costo total comercial / saco", money(costo_total_saco_sin_extra))
    with c3:
        kpi("Precio actual / saco", money(precio_actual))
    with c4:
        kpi("Margen real", pct(margen_real), f"Utilidad: {money(utilidad_saco)}", tone="red" if utilidad_saco < 0 or margen_real < 0 else "green")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Costo granel / kg", money(costo_kg_granel), f"{status_icon(var_costo_kg_granel)} {delta_costo_kg_granel}")
    with c2:
        kpi("Incremental empaque / saco", money(incremental_saco))
    with c3:
        kpi("Gastos asignados / saco", money(gastos_saco))
    with c4:
        kpi("Precio objetivo + IVA", money(precio_obj_sin_extra_iva))

    st.markdown("### Alertas gerenciales")
    dataframe_gerencial(alertas_df)

    st.markdown("### Desviaciones relevantes por observación")
    if df_prev.empty:
        st.info("No existe mes anterior cargado. Las desviaciones relevantes se activan desde el segundo mes.")
    elif variaciones_relevantes.empty:
        st.success("No hay desviaciones relevantes según los umbrales configurados.")
    else:
        dataframe_gerencial(variaciones_relevantes.head(10)[["Alerta", "Indice", "Observacion", "Valor", "Valor anterior", "Variacion $", "Variacion %", "Impacto por saco", "Impacto por kg", "Criterio"]])

    col_a, col_b = st.columns([1.2, 1])
    with col_a:
        puente = pd.DataFrame([
            ["Costo empacado completo / saco", costo_saco_emp],
            ["Gastos asignados / saco", gastos_saco],
            ["Costo comercial sin extraordinarios", costo_total_saco_sin_extra],
            ["Gastos extraordinarios / saco", gastos_extra_saco],
            ["Costo comercial con extraordinarios", costo_total_saco_con_extra],
            ["Precio objetivo antes IVA", precio_obj_sin_extra],
            ["Precio objetivo con IVA", precio_obj_sin_extra_iva],
        ], columns=["Métrica", "Valor"])
        dataframe_gerencial(puente)
    with col_b:
        fig = px.bar(
            pd.DataFrame({"Componente": ["Empacado", "Gastos", "Extra"], "Valor por saco": [costo_saco_emp, gastos_saco, gastos_extra_saco]}),
            x="Componente", y="Valor por saco", title="Construcción del costo / saco",
            color="Componente",
            color_discrete_map={"Empacado":"#E8650A","Gastos":"#F5A623","Extra":"#F59E0B"},
        )
        fig.update_traces(marker_line_width=0, opacity=0.9)
        fig.update_layout(showlegend=False, height=340)
        st.plotly_chart(fig, use_container_width=True)

with tabs[1]:
    st.subheader("Precio de venta, margen y escenarios")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Precio actual antes IVA", money(precio_actual))
    with c2:
        kpi("Precio objetivo sin extra", money(precio_obj_sin_extra))
    with c3:
        kpi("Brecha vs objetivo", money(brecha_precio))
    with c4:
        kpi("Diferencia margen", pct(brecha_margen))

    margenes = [m / 100 for m in range(5, 31, 5)]

    sensibilidad = []
    for m in margenes:
        p_sin = safe_div(costo_total_saco_sin_extra, 1 - m)
        p_con = safe_div(costo_total_saco_con_extra, 1 - m)
        utilidad_esperada = p_sin - costo_total_saco_sin_extra
        sensibilidad.append([
            "Base",
            m,
            p_sin,
            p_sin * (1 + iva),
            p_con,
            p_con * (1 + iva),
            p_sin - precio_actual,
            utilidad_esperada,
        ])
    sens_df = pd.DataFrame(sensibilidad, columns=[
        "Tipo", "Margen objetivo", "Precio sin extra antes IVA", "Precio sin extra con IVA",
        "Precio con extra antes IVA", "Precio con extra con IVA", "Brecha vs precio actual", "Utilidad esperada / saco"
    ])

    col_a, col_b = st.columns([1.25, 1])
    with col_a:
        st.markdown("### Precio sugerido de venta por margen")
        st.caption("Tabla base de 5% a 30%. Margen calculado sobre precio de venta.")
        dataframe_gerencial(sens_df)
    with col_b:
        fig = px.line(sens_df, x="Margen objetivo", y="Precio sin extra antes IVA", markers=True, title="Curva de precio objetivo antes de IVA")
        fig.update_yaxes(tickprefix="$")
        fig.update_traces(line_color="#E8650A", line_width=2.5, marker_color="#F5A623", marker_size=8)
        fig.add_hline(y=precio_actual, line_dash="dot", line_color="#FF4059", annotation_text="Precio actual", annotation_font_color="#FF4059", line_width=1.5)
        st.plotly_chart(fig, use_container_width=True)

with tabs[2]:
    st.subheader(f"Granel UG - {periodo.etiqueta}")
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
    st.subheader(f"Empacado UG 50KG - {periodo.etiqueta}")
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

    gastos_detalle = df_mes[df_mes["Indice_norm"].isin({norm_text(i) for i in INDICES_GASTOS_COMERCIALES})].copy()
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
    pareto_gastos = build_pareto(resumen_por_observacion(df_mes, INDICES_GASTOS_COMERCIALES), und_emp, kg_emp)
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
        base = resumen_por_observacion(df_mes, INDICES_GASTOS_COMERCIALES)
    else:
        a = resumen_por_observacion(df_mes, INDICES_EMPACADO)
        b = resumen_por_observacion(df_mes, INDICES_GASTOS_COMERCIALES)
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
        ["Precio bolsa", OBS_PRECIO_BOLSA, precio_actual, "OK" if precio_actual > 0 else "REVISAR"],
        ["Cemento transferido", OBS_CEMENTO_GRANEL_TRANSFERIDO, cemento_transf, "OK" if cemento_transf > 0 else "REVISAR"],
        ["C MP EMP", "Índice", suma_indices(df_mes, ["C MP EMP"]), "OK" if suma_indices(df_mes, ["C MP EMP"]) > 0 else "REVISAR"],
        ["C MO EMP", "Índice", suma_indices(df_mes, ["C MO EMP"]), "OK" if suma_indices(df_mes, ["C MO EMP"]) > 0 else "REVISAR"],
        ["C CIF EMP", "Índice", suma_indices(df_mes, ["C CIF EMP"]), "OK" if suma_indices(df_mes, ["C CIF EMP"]) > 0 else "REVISAR"],
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
            ["Kg por saco", 50, "kg"],
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
        ["Materia prima empacado", "C MP EMP", c_mp_emp, safe_div(c_mp_emp, und_emp), safe_div(c_mp_emp, kg_emp)],
        ["Mano de obra empacado", "C MO EMP", c_mo_emp, safe_div(c_mo_emp, und_emp), safe_div(c_mo_emp, kg_emp)],
        ["CIF empacado", "C CIF EMP", c_cif_emp, safe_div(c_cif_emp, und_emp), safe_div(c_cif_emp, kg_emp)],
        ["Costo empacado completo", "C MP EMP + C MO EMP + C CIF EMP", costo_emp, costo_saco_emp, costo_kg_emp],
    ], columns=["Paso", "Índices / fórmula", "Valor total", "$/saco", "$/kg"])
    dataframe_gerencial(paso_emp)

    st.markdown("### 3. Gastos asignables al producto vendido")
    paso_gastos = pd.DataFrame([
        ["Administración mano de obra", "C MO ADM", suma_indices(df_mes, ["C MO ADM"]), safe_div(suma_indices(df_mes, ["C MO ADM"]), und_emp), safe_div(suma_indices(df_mes, ["C MO ADM"]), kg_emp)],
        ["Administración CIF", "C CIF ADM", suma_indices(df_mes, ["C CIF ADM"]), safe_div(suma_indices(df_mes, ["C CIF ADM"]), und_emp), safe_div(suma_indices(df_mes, ["C CIF ADM"]), kg_emp)],
        ["Ventas mano de obra", "C MO VEN", suma_indices(df_mes, ["C MO VEN"]), safe_div(suma_indices(df_mes, ["C MO VEN"]), und_emp), safe_div(suma_indices(df_mes, ["C MO VEN"]), kg_emp)],
        ["Ventas CIF", "C CIF VEN", suma_indices(df_mes, ["C CIF VEN"]), safe_div(suma_indices(df_mes, ["C CIF VEN"]), und_emp), safe_div(suma_indices(df_mes, ["C CIF VEN"]), kg_emp)],
        ["Financieros", "C FIN", suma_indices(df_mes, ["C FIN"]), safe_div(suma_indices(df_mes, ["C FIN"]), und_emp), safe_div(suma_indices(df_mes, ["C FIN"]), kg_emp)],
        ["Impuestos", "C IMP", suma_indices(df_mes, ["C IMP"]), safe_div(suma_indices(df_mes, ["C IMP"]), und_emp), safe_div(suma_indices(df_mes, ["C IMP"]), kg_emp)],
        ["Total gastos asignables", "C MO ADM + C CIF ADM + C MO VEN + C CIF VEN + C FIN + C IMP", costos_gastos, gastos_saco, gastos_kg],
    ], columns=["Paso", "Índices / fórmula", "Valor total", "$/saco", "$/kg"])
    dataframe_gerencial(paso_gastos)

    st.markdown("### Impuestos opcionales de renta y patrimonio")
    st.caption("Estos dos índices son parametrizables. Si están apagados, se reportan pero no se suman al costo total comercial.")
    dataframe_gerencial(impuestos_opcionales_df)

    st.markdown("### 4. Construcción del costo total comercial")
    puente_comercial = pd.DataFrame([
        ["A", "Costo empacado completo / saco", "(C MP EMP + C MO EMP + C CIF EMP) / UND PRODUCIDAS Q", costo_saco_emp],
        ["B", "Gastos asignados / saco", "(C MO ADM + C CIF ADM + C MO VEN + C CIF VEN + C FIN + C IMP) / UND PRODUCIDAS Q", gastos_saco],
        ["C = A + B", "Costo total comercial / saco", "Costo empacado / saco + gastos asignados / saco", costo_total_saco_sin_extra],
        ["D", "Gastos extraordinarios / saco", "Gastos ExtraOrdinarios / UND PRODUCIDAS Q", gastos_extra_saco],
        ["E = C + D", "Costo total comercial con extraordinarios / saco", "Costo comercial sin extra + gasto extraordinario / saco", costo_total_saco_con_extra],
        ["F", "Precio actual / saco", "PRECIO PROMEDIO POR BOLSA 50 KG", precio_actual],
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
            resumen_por_observacion(df_mes, INDICES_GASTOS_COMERCIALES),
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
    st.subheader("Simulador de precios por toneladas producidas")
    st.caption(
        "Modelo aprobado: materias primas escalan con producción; administración y mano de obra de producción permanecen constantes; "
        "costos de venta escalan con la nueva venta. Renta y patrimonio se pueden prender/apagar de forma independiente para el costeo real y para la proyección."
    )

    tons_base = safe_div(kg_emp, 1000)
    sacos_por_ton = 20.0
    precio_ton_actual = precio_actual * sacos_por_ton
    venta_base = und_emp * precio_actual

    c_adm_base = suma_indices(df_mes, ["C MO ADM", "C CIF ADM"])
    c_ventas_base = suma_indices(df_mes, ["C MO VEN", "C CIF VEN"])
    c_fin_base = suma_indices(df_mes, ["C FIN"])
    c_imp_base = suma_indices(df_mes, ["C IMP"])

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
        ["C MP EMP", c_mp_emp],
        ["C MO EMP", c_mo_emp],
        ["C CIF EMP", c_cif_emp],
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
                "Esto evita que una menor producción aparezca artificialmente más barata."
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

    def calcular_proyeccion_volumen(toneladas: float, precio_ton: float) -> dict[str, float]:
        factor = safe_div(toneladas, tons_base)
        sacos = toneladas * sacos_por_ton
        kg = toneladas * 1000.0
        venta = toneladas * precio_ton

        mp = mp_base_modelo * factor
        mo = mo_base_modelo
        if comportamiento_cif == "Variable por toneladas":
            cif = cif_base_modelo * factor
        elif comportamiento_cif == "Semi-variable 50/50":
            cif = (cif_base_modelo * 0.5) + (cif_base_modelo * 0.5 * factor)
        else:
            cif = cif_base_modelo

        adm = adm_base_modelo
        ventas = venta * costo_ventas_pct_sim
        fin = fin_base_modelo if incluir_fin_sim else 0.0
        imp_base = imp_base_modelo if incluir_imp_base_sim else 0.0
        imp_renta = imp_renta_modelo if incluir_imp_renta_sim else 0.0
        imp_patr = imp_patrimonio_modelo if incluir_imp_patrimonio_sim else 0.0
        extra = extra_base_modelo if incluir_extra_sim else 0.0
        total = mp + mo + cif + adm + ventas + fin + imp_base + imp_renta + imp_patr + extra

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

    precio_kg_actual = safe_div(precio_actual, 50.0)
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
        "Escenario", "Toneladas", "Kg", "Bolsas 50 kg", "Costo total", "Costo / kg", "Costo / bolsa", "Costo / tonelada",
        "Precio / kg", "Precio / bolsa", "Precio / tonelada", "Utilidad / kg", "Utilidad / bolsa", "Margen", "Impuestos opcionales",
    ])
    dataframe_gerencial(comparativo_unitario_df)

    st.markdown("### Impacto de impuestos opcionales")
    impuestos_impacto_df = pd.DataFrame([
        ["C IMP REN", imp_renta_total, "Sí" if incluir_imp_renta else "No", "Sí" if incluir_imp_renta_sim else "No", imp_renta_sim, safe_div(imp_renta_sim, kg_sim), safe_div(imp_renta_sim, sacos_sim), safe_div(imp_renta_sim, toneladas_sim)],
        ["C IMP PATR", imp_patrimonio_total, "Sí" if incluir_imp_patrimonio else "No", "Sí" if incluir_imp_patrimonio_sim else "No", imp_patr_sim, safe_div(imp_patr_sim, kg_sim), safe_div(imp_patr_sim, sacos_sim), safe_div(imp_patr_sim, toneladas_sim)],
    ], columns=["Índice", "Valor detectado", "Aplica real", "Aplica proyectado", "Valor proyectado incluido", "Impacto / kg", "Impacto / bolsa", "Impacto / ton"])
    dataframe_gerencial(impuestos_impacto_df)

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
        - La sensibilidad queda corregida para que menos toneladas no aparezcan artificialmente más baratas por efectos de ajustes negativos.
        - Costeo real: C IMP REN está **{'incluido' if incluir_imp_renta else 'excluido'}** y C IMP PATR está **{'incluido' if incluir_imp_patrimonio else 'excluido'}**.
        - Proyección: C IMP REN está **{'incluido' if incluir_imp_renta_sim else 'excluido'}** y C IMP PATR está **{'incluido' if incluir_imp_patrimonio_sim else 'excluido'}**.
        """
    )
