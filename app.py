from __future__ import annotations

import io
import unicodedata
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(
    page_title="Kolcem · CEO/CFO Board Pack",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# Diseño: sobrio, legible, para CEO/CFO/Junta
# =============================================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{
  --bg:#0b1220; --panel:#111827; --panel2:#0f172a; --line:#263245;
  --text:#e5e7eb; --muted:#94a3b8; --soft:#cbd5e1;
  --good:#16a34a; --warn:#d97706; --bad:#dc2626; --blue:#2563eb;
}
html,body,.stApp,[class*="css"]{font-family:Inter,system-ui,sans-serif!important;}
.stApp{background:var(--bg); color:var(--text);}
.block-container{padding-top:1.2rem!important; max-width:1320px!important;}
section[data-testid="stSidebar"]{background:#0a1020!important;border-right:1px solid var(--line)!important;}
section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3{font-size:.78rem!important;color:#f97316!important;letter-spacing:.08em;text-transform:uppercase;}
section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] p{color:var(--muted)!important;}
.main-title{font-size:1.75rem;font-weight:800;line-height:1.1;margin:0 0 .25rem;color:var(--text);}
.subtitle{color:var(--muted);font-size:.95rem;margin-bottom:1rem;}
.board-note{background:#101a2e;border:1px solid var(--line);border-left:4px solid #f97316;border-radius:12px;padding:12px 14px;margin:10px 0 14px;color:var(--soft);font-size:.88rem;}
.compact-card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:13px 14px;min-height:88px;}
.card-label{font-size:.68rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:700;margin-bottom:7px;}
.card-value{font-size:1.05rem;font-weight:800;color:var(--text);letter-spacing:-.015em;line-height:1.15;}
.card-help{font-size:.74rem;color:var(--muted);margin-top:6px;line-height:1.25;}
.good{border-left:4px solid var(--good)} .good .card-value{color:#4ade80}
.warn{border-left:4px solid var(--warn)} .warn .card-value{color:#fbbf24}
.bad{border-left:4px solid var(--bad)} .bad .card-value{color:#f87171}
.neutral{border-left:4px solid #64748b}
.blue{border-left:4px solid var(--blue)} .blue .card-value{color:#93c5fd}
.section-title{font-size:.9rem;text-transform:uppercase;letter-spacing:.08em;color:#cbd5e1;font-weight:800;margin:18px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px;}
.small-table div[data-testid="stDataFrame"]{font-size:.84rem!important;}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#0f172a;border:1px solid var(--line);border-radius:12px;padding:4px;}
.stTabs [data-baseweb="tab"]{border-radius:9px;padding:8px 10px;font-size:.82rem;color:var(--muted);}
.stTabs [aria-selected="true"]{background:#f97316!important;color:white!important;}
div[data-testid="stDataFrame"]{border:1px solid var(--line)!important;border-radius:12px!important;overflow:hidden;}
.stAlert{border-radius:12px!important;}
hr{border-color:var(--line)}
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# Utilidades
# =============================================================================

MESES = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5, "Junio": 6,
    "Julio": 7, "Agosto": 8, "Septiembre": 9, "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
}
MESES_INV = {v: k for k, v in MESES.items()}


def norm_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).replace("\xa0", " ").replace(" ", " ")
    for dash in ["‐", "‑", "‒", "–", "—", "−"]:
        text = text.replace(dash, "-")
    text = " ".join(text.strip().upper().split())
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def parse_valor(value: object) -> float:
    if value is None or pd.isna(value):
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value) if not pd.isna(value) else 0.0
    text = str(value).replace("$", "").replace("COP", "").replace("cop", "")
    text = text.replace("\xa0", " ").replace(" ", " ").strip()
    if text in {"", "-", "–", "—"}:
        return 0.0
    neg = text.startswith("(") and text.endswith(")")
    if neg:
        text = text[1:-1]
    text = "".join(text.split())
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        val = float(text)
        return -val if neg else val
    except Exception:
        return 0.0


def money(v: float, decimals: int = 0) -> str:
    if v is None or pd.isna(v):
        v = 0.0
    s = f"${float(v):,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def num(v: float, decimals: int = 0) -> str:
    if v is None or pd.isna(v):
        v = 0.0
    return f"{float(v):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float) -> str:
    if v is None or pd.isna(v):
        v = 0.0
    return f"{float(v):.2%}".replace(".", ",")


def safe_div(a: float, b: float) -> float:
    return 0.0 if b is None or pd.isna(b) or abs(float(b)) < 1e-12 else float(a) / float(b)


def tone(value: float, good_if_positive: bool = True, warn_threshold: float = 0.0) -> str:
    if good_if_positive:
        if value > warn_threshold:
            return "good"
        if value > -abs(warn_threshold):
            return "warn"
        return "bad"
    if value < -abs(warn_threshold):
        return "good"
    if value <= abs(warn_threshold):
        return "warn"
    return "bad"


def metric_card(label: str, value: str, help_text: str = "", color: str = "neutral") -> None:
    st.markdown(
        f"""
<div class="compact-card {color}">
  <div class="card-label">{label}</div>
  <div class="card-value">{value}</div>
  <div class="card-help">{help_text}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def fmt_df(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    formatters = {}
    for col in df.columns:
        nc = norm_text(col)
        if pd.api.types.is_numeric_dtype(df[col]):
            if any(x in nc for x in ["MARGEN", "%", "PARTICIPACION", "CONFIANZA"]):
                formatters[col] = lambda x: pct(x)
            elif any(x in nc for x in ["VENTA", "COSTO", "UTILIDAD", "VALOR", "BRECHA", "DIFERENCIA", "IMPACTO", "GASTO", "AHORRO"]):
                formatters[col] = lambda x: money(x, 0)
            else:
                formatters[col] = lambda x: num(x, 2)
    return df.style.format(formatters)


# =============================================================================
# Modelo de datos
# =============================================================================

@dataclass(frozen=True)
class Producto:
    key: str
    nombre: str
    corto: str
    peso_kg: float
    prod_empacado: str
    prod_gastos: str
    prod_precio: str
    obs_vendida: str
    obs_precio: str
    indices_empacado: tuple[str, ...]
    indices_gasto_base: tuple[str, ...]


PRODUCTOS = {
    "UG_50": Producto(
        key="UG_50",
        nombre="Cemento UG empacado 50 kg",
        corto="UG 50 kg",
        peso_kg=50.0,
        prod_empacado="Empacado UG 50KG (2843)",
        prod_gastos="Gastos Administrativos y de Venta",
        prod_precio="Precio Final",
        obs_vendida="CEMENTO KOLCEM UG 50 KG",
        obs_precio="PRECIO PROMEDIO POR BOLSA 50 KG",
        indices_empacado=("C MP UG EMP", "C MO UG EMP", "C CIF UG EMP"),
        indices_gasto_base=("C MO ADM", "C CIF ADM", "C MO UG VEN", "C CIF UG VEN", "C FIN", "C IMP"),
    ),
    "ART_42_5": Producto(
        key="ART_42_5",
        nombre="Cemento ART estructural empacado 42,5 kg",
        corto="ART 42,5 kg",
        peso_kg=42.5,
        prod_empacado="Cemento Empacado ART 42.5 (4223)",
        prod_gastos="Gastos Administrativos y de Venta ART",
        prod_precio="Precio Final ART",
        obs_vendida="CEMENTO KOLCEM ART 42.5 KG",
        obs_precio="PRECIO PROMEDIO POR BOLSA 42.5 KG",
        indices_empacado=("C MP ART EMP", "C MO ART EMP", "C CIF ART EMP"),
        indices_gasto_base=("C ADM Y VEN ART EMP",),
    ),
}


@st.cache_data(show_spinner=False)
def load_base(uploaded: bytes) -> pd.DataFrame:
    xls = pd.ExcelFile(io.BytesIO(uploaded), engine="openpyxl")
    if "Consolidado" not in xls.sheet_names:
        raise ValueError("El archivo debe tener hoja 'Consolidado'.")
    df = pd.read_excel(xls, sheet_name="Consolidado", engine="openpyxl")
    df = df.rename(columns={"Producción": "Produccion", "Concepto": "Observacion", "Año": "Ano"}).copy()
    required = ["Produccion", "Indice", "Observacion", "Valor", "Mes", "Ano", "MesNro"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Faltan columnas en Consolidado: " + ", ".join(missing))
    df = df.dropna(how="all").copy()
    df["Valor"] = df["Valor"].apply(parse_valor)
    df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").fillna(0).astype(int)
    df["MesNro"] = pd.to_numeric(df["MesNro"], errors="coerce")
    df["MesNro"] = df["MesNro"].fillna(df["Mes"].map(MESES)).astype(int)
    for col in ["Produccion", "Indice", "Observacion"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
        df[col + "_norm"] = df[col].map(norm_text)
    return df


@st.cache_data(show_spinner=False)
def load_contabilidad(uploaded: bytes) -> pd.DataFrame:
    xls = pd.ExcelFile(io.BytesIO(uploaded), engine="openpyxl")
    sheet = "Hoja2" if "Hoja2" in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=sheet, engine="openpyxl")
    # Hoja2 ya viene estructurada. Si no, intenta normalizar nombres genéricos.
    mapping = {}
    for c in df.columns:
        nc = norm_text(c)
        if nc in {"ANO", "AÑO"}:
            mapping[c] = "Ano"
        elif nc == "MES":
            mapping[c] = "Mes"
        elif nc in {"AUXILIAR", "CODIGO", "CUENTA"}:
            mapping[c] = "Auxiliar"
        elif nc in {"NOMBREAUX", "NOMBRE AUX", "NOMBRE", "DESCRIPCION"}:
            mapping[c] = "NombreAux"
        elif "DEBIT" in nc:
            mapping[c] = "TotalDebito"
        elif "CREDIT" in nc:
            mapping[c] = "TotalCredito"
        elif "SALDO" in nc:
            mapping[c] = "Saldo"
    df = df.rename(columns=mapping).copy()
    required = ["Ano", "Mes", "Auxiliar", "NombreAux", "TotalDebito", "TotalCredito", "Saldo"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("La contabilidad debe traer Ano, Mes, Auxiliar, NombreAux, TotalDebito, TotalCredito y Saldo.")
    df = df.dropna(how="all").copy()
    df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").fillna(0).astype(int)
    df["Mes"] = pd.to_numeric(df["Mes"], errors="coerce").fillna(0).astype(int)
    df["Auxiliar"] = df["Auxiliar"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    df["NombreAux"] = df["NombreAux"].fillna("").astype(str)
    for col in ["TotalDebito", "TotalCredito", "Saldo"]:
        df[col] = df[col].apply(parse_valor)
    df["Clase"] = df["Auxiliar"].str[0]
    return df


def filtro_periodo(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    return df[(df["Ano"] == ano) & (df["MesNro"] == mes)].copy()


def sum_obs(df: pd.DataFrame, prod: str, obs: str) -> float:
    return float(df.loc[(df["Produccion_norm"] == norm_text(prod)) & (df["Observacion_norm"] == norm_text(obs)), "Valor"].sum())


def sum_indices(df: pd.DataFrame, prod: str, indices: Iterable[str]) -> float:
    idx = {norm_text(i) for i in indices}
    return float(df.loc[(df["Produccion_norm"] == norm_text(prod)) & (df["Indice_norm"].isin(idx)), "Valor"].sum())


def mask_no_realizada(df: pd.DataFrame) -> pd.Series:
    obs = df["Observacion_norm"].fillna("")
    return obs.str.contains("DIFERENCIA", na=False) & obs.str.contains("CAMBIO", na=False) & obs.str.contains("NO REALIZ", na=False)


def gastos_producto(df: pd.DataFrame, producto: Producto, incluir_renta: bool, incluir_patrimonio: bool) -> float:
    base = df[df["Produccion_norm"] == norm_text(producto.prod_gastos)].copy()
    if base.empty:
        return 0.0
    # Para ART se respeta el subtotal GASTOS, que evita duplicar subtotales internos.
    if producto.key == "ART_42_5":
        total = float(base.loc[(base["Indice_norm"] == norm_text("TOTAL")) & (base["Observacion_norm"] == norm_text("GASTOS")), "Valor"].sum())
        return total
    idx = {norm_text(i) for i in producto.indices_gasto_base}
    if incluir_renta:
        idx.add(norm_text("C IMP REN"))
    if incluir_patrimonio:
        idx.add(norm_text("C IMP PATR"))
    base = base[base["Indice_norm"].isin(idx)].copy()
    base = base[~mask_no_realizada(base)].copy()
    return float(base["Valor"].sum())


def producto_metrics(df_mes: pd.DataFrame, producto: Producto, incluir_renta: bool, incluir_patrimonio: bool) -> dict:
    und_producidas = sum_obs(df_mes, producto.prod_empacado, "UND PRODUCIDAS Q")
    kg_producidos = und_producidas * producto.peso_kg
    ton_producidas = kg_producidos / 1000
    und_vendidas = sum_obs(df_mes, "Cantidades Vendidas", producto.obs_vendida)
    precio_bolsa = sum_obs(df_mes, producto.prod_precio, producto.obs_precio)
    costo_produccion = sum_indices(df_mes, producto.prod_empacado, producto.indices_empacado)
    gastos_asignados = gastos_producto(df_mes, producto, incluir_renta, incluir_patrimonio)
    costo_comercial_producido = costo_produccion + gastos_asignados
    costo_bolsa = safe_div(costo_comercial_producido, und_producidas)
    costo_vendido = costo_bolsa * und_vendidas
    venta = und_vendidas * precio_bolsa
    utilidad = venta - costo_vendido
    margen = safe_div(utilidad, venta)
    inventario_und = max(und_producidas - und_vendidas, 0)
    costo_inv = inventario_und * costo_bolsa
    return {
        "key": producto.key,
        "Producto": producto.corto,
        "Nombre": producto.nombre,
        "Peso kg": producto.peso_kg,
        "Bolsas producidas": und_producidas,
        "Bolsas vendidas": und_vendidas,
        "Ton producidas": ton_producidas,
        "Ton vendidas": und_vendidas * producto.peso_kg / 1000,
        "Precio bolsa": precio_bolsa,
        "Costo producción": costo_produccion,
        "Gastos asignados": gastos_asignados,
        "Costo comercial producido": costo_comercial_producido,
        "Costo bolsa recurrente": costo_bolsa,
        "Costo vendido recurrente": costo_vendido,
        "Venta": venta,
        "Utilidad recurrente": utilidad,
        "Margen recurrente": margen,
        "Bolsas producidas no vendidas": inventario_und,
        "Costo inventario producido no vendido": costo_inv,
    }


def extras_modelo(df_mes: pd.DataFrame) -> pd.DataFrame:
    out = df_mes[df_mes["Produccion_norm"] == norm_text("Gastos ExtraOrdinarios")].copy()
    return out[["Indice", "Observacion", "Valor"]].sort_values("Valor", ascending=False) if not out.empty else pd.DataFrame(columns=["Indice", "Observacion", "Valor"])


def pyg_summary(df_cont: pd.DataFrame, ano: int, mes: int) -> dict:
    d = df_cont[(df_cont["Ano"] == ano) & (df_cont["Mes"] == mes)].copy()
    if d.empty:
        return {"ok": False}
    saldo_4 = float(d.loc[d["Clase"] == "4", "Saldo"].sum())
    saldo_5 = float(d.loc[d["Clase"] == "5", "Saldo"].sum())
    saldo_6 = float(d.loc[d["Clase"] == "6", "Saldo"].sum())
    saldo_7 = float(d.loc[d["Clase"] == "7", "Saldo"].sum())
    utilidad = -saldo_4 - saldo_5 - saldo_6 - saldo_7
    ingresos_netos = -float(d.loc[d["Auxiliar"].str.startswith("41"), "Saldo"].sum())
    costo_venta = float(d.loc[d["Auxiliar"].str.startswith("61"), "Saldo"].sum())
    gastos_admin = float(d.loc[d["Auxiliar"].str.startswith("51"), "Saldo"].sum())
    gastos_venta = float(d.loc[d["Auxiliar"].str.startswith("52"), "Saldo"].sum())
    gastos_fin = float(d.loc[d["Auxiliar"].str.startswith("53"), "Saldo"].sum())
    impuestos = float(d.loc[d["Auxiliar"].str.startswith("54"), "Saldo"].sum())
    resultado_42 = -float(d.loc[d["Auxiliar"].str.startswith("42"), "Saldo"].sum())
    cuentas_balance = d[d["Clase"].isin(["1", "2", "3"])].copy()
    return {
        "ok": True,
        "df": d,
        "Ingresos netos": ingresos_netos,
        "Costo venta P&G": costo_venta,
        "Gastos administración": gastos_admin,
        "Gastos venta": gastos_venta,
        "Gastos financieros": gastos_fin,
        "Impuestos": impuestos,
        "Resultado otros/financieros clase 42": resultado_42,
        "Utilidad neta contable": utilidad,
        "Margen neto contable": safe_div(utilidad, ingresos_netos),
        "Cuentas balance control": cuentas_balance,
    }


def confidence_score(base_ok: bool, cont_ok: bool, metrics: pd.DataFrame, diff_check: float | None) -> tuple[float, list[str]]:
    score = 0.0
    warnings = []
    if base_ok:
        score += 0.30
    else:
        warnings.append("No hay base de costeo cargada.")
    if not metrics.empty and metrics["Venta"].sum() > 0:
        score += 0.25
    else:
        warnings.append("No hay ventas o producto vendido para el periodo.")
    if not metrics.empty and metrics["Bolsas producidas"].sum() > 0:
        score += 0.15
    else:
        warnings.append("No hay producción empacada para el periodo.")
    if cont_ok:
        score += 0.20
    else:
        warnings.append("No hay P&G cargado; la utilidad neta contable no se puede validar.")
    if diff_check is not None and abs(diff_check) < 1:
        score += 0.10
    elif cont_ok:
        warnings.append("El puente contable no cerró exactamente; revisar mapeo P&G.")
    return min(score, 1.0), warnings


# =============================================================================
# Sidebar
# =============================================================================

st.sidebar.markdown("### Archivos")
base_file = st.sidebar.file_uploader("Base de costeo · Excel app", type=["xlsm", "xlsx"], key="base")
cont_file = st.sidebar.file_uploader("Contabilidad / P&G · opcional", type=["xlsx", "xlsm"], key="cont")

st.sidebar.markdown("### Periodo")
ano = st.sidebar.number_input("Año", min_value=2020, max_value=2035, value=2026, step=1)
mes_nombre = st.sidebar.selectbox("Mes", list(MESES.keys()), index=4)
mes = MESES[mes_nombre]

st.sidebar.markdown("### Gobierno del costo")
incluir_renta = st.sidebar.checkbox("Incluir impuesto de renta en costo comercial", value=False)
incluir_patrimonio = st.sidebar.checkbox("Incluir impuesto al patrimonio en costo comercial", value=False)
restar_extra = st.sidebar.checkbox("Mostrar utilidad después de extraordinarios del modelo", value=True)

st.sidebar.markdown("### Meta gerencial")
margen_meta = st.sidebar.number_input("Margen comercial meta", min_value=0.0, max_value=0.8, value=0.12, step=0.01, format="%.2f")

st.markdown('<div class="main-title">Board Pack CEO/CFO · Costeo de Cemento</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Una pantalla para decidir: margen, precio, conciliación P&G, inventario y alertas. Sin ruido visual.</div>',
    unsafe_allow_html=True,
)

if base_file is None:
    st.info("Carga la base de costeo para iniciar. La app está optimizada para mostrar primero lo que necesita CEO, CFO y Junta: decisión, margen, conciliación y riesgos.")
    st.stop()

try:
    df_base = load_base(base_file.getvalue())
except Exception as e:
    st.error(f"No pude leer la base de costeo: {e}")
    st.stop()

df_mes = filtro_periodo(df_base, int(ano), int(mes))
if df_mes.empty:
    st.warning(f"No hay datos en Consolidado para {mes_nombre} {ano}.")
    st.stop()

cont = None
pyg = {"ok": False}
if cont_file is not None:
    try:
        cont = load_contabilidad(cont_file.getvalue())
        pyg = pyg_summary(cont, int(ano), int(mes))
    except Exception as e:
        st.warning(f"La contabilidad no pudo leerse: {e}")

metrics_list = [producto_metrics(df_mes, p, incluir_renta, incluir_patrimonio) for p in PRODUCTOS.values()]
metrics = pd.DataFrame(metrics_list)

venta_app = float(metrics["Venta"].sum())
costo_vendido_app = float(metrics["Costo vendido recurrente"].sum())
utilidad_app = venta_app - costo_vendido_app
margen_app = safe_div(utilidad_app, venta_app)
extras_df = extras_modelo(df_mes)
extras_total = float(extras_df["Valor"].sum()) if not extras_df.empty else 0.0
utilidad_app_con_extra = utilidad_app - extras_total if restar_extra else utilidad_app
margen_app_con_extra = safe_div(utilidad_app_con_extra, venta_app)
inventario_costo = float(metrics["Costo inventario producido no vendido"].sum())
inventario_bolsas = float(metrics["Bolsas producidas no vendidas"].sum())

if pyg.get("ok"):
    utilidad_pyg = float(pyg["Utilidad neta contable"])
    ingresos_pyg = float(pyg["Ingresos netos"])
    pyg_costos_netos = ingresos_pyg - utilidad_pyg
    app_costos_netos = costo_vendido_app + (extras_total if restar_extra else 0.0)
    dif_ingreso = ingresos_pyg - venta_app
    dif_costos_netos = app_costos_netos - pyg_costos_netos
    utilidad_conciliada = utilidad_app_con_extra + dif_ingreso + dif_costos_netos
    check = utilidad_conciliada - utilidad_pyg
else:
    utilidad_pyg = ingresos_pyg = dif_ingreso = dif_costos_netos = utilidad_conciliada = check = None

conf, warnings = confidence_score(True, bool(pyg.get("ok")), metrics, check if pyg.get("ok") else None)

# =============================================================================
# Navegación compacta
# =============================================================================

tabs = st.tabs([
    "1 · Decisión Junta",
    "2 · Margen y precio",
    "3 · Conciliación P&G",
    "4 · Palancas de costo",
    "5 · Datos y controles",
])

# =============================================================================
# 1 · Decisión Junta
# =============================================================================

with tabs[0]:
    st.markdown('<div class="section-title">Respuesta clara para comité</div>', unsafe_allow_html=True)
    decision = "MANTENER PRECIO Y CERRAR BRECHAS DE COSTO/CONCILIACIÓN"
    if margen_app < margen_meta:
        decision = "NO BAJAR PRECIO · SUBIR O DEFENDER PRECIO HASTA META"
    if pyg.get("ok") and pyg["Margen neto contable"] < 0.03:
        decision += " · REVISAR P&G Y FINANCIEROS"
    st.markdown(
        f"<div class='board-note'><b>Decisión recomendada:</b> {decision}. "
        f"La utilidad comercial recurrente sirve para precio; la utilidad neta contable sirve para junta, bancos e impuestos. No mezclar ambas.</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        metric_card("Venta app", money(venta_app), f"{num(metrics['Ton vendidas'].sum(), 2)} t vendidas", "blue")
    with c2:
        metric_card("Margen comercial", pct(margen_app), f"Meta {pct(margen_meta)}", "good" if margen_app >= margen_meta else "warn")
    with c3:
        metric_card("Utilidad comercial", money(utilidad_app), "Antes de extraordinarios", "good" if utilidad_app >= 0 else "bad")
    with c4:
        metric_card("Utilidad con extra", money(utilidad_app_con_extra), f"Extra: {money(extras_total)}", "good" if utilidad_app_con_extra >= 0 else "bad")
    with c5:
        if pyg.get("ok"):
            metric_card("Utilidad neta P&G", money(utilidad_pyg), f"Margen neto {pct(pyg['Margen neto contable'])}", "good" if utilidad_pyg >= 0 else "bad")
        else:
            metric_card("Utilidad neta P&G", "No cargada", "Subir contabilidad para validar", "warn")

    st.markdown('<div class="section-title">Nivel de confianza</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 2])
    with c1:
        metric_card("Confianza", f"{conf:.2f}", "0,80+ = apto para comité", "good" if conf >= 0.80 else "warn")
    with c2:
        avisos = warnings if warnings else ["Datos base, ventas, producción y P&G cierran para lectura ejecutiva."]
        st.markdown("**Advertencias clave**")
        for w in avisos[:5]:
            st.write(f"• {w}")
    with c3:
        st.markdown("**Lectura CEO/CFO**")
        st.write("• Precio se decide con margen comercial recurrente, no con FX no realizada.")
        st.write("• Junta evalúa utilidad neta P&G y conciliación, no solo costo por saco.")
        st.write("• Inventario producido no vendido consume caja y debe tener dueño operativo.")

    st.markdown('<div class="section-title">Rentabilidad por producto</div>', unsafe_allow_html=True)
    cols_show = ["Producto", "Bolsas producidas", "Bolsas vendidas", "Venta", "Costo vendido recurrente", "Utilidad recurrente", "Margen recurrente", "Costo inventario producido no vendido"]
    st.dataframe(fmt_df(metrics[cols_show]), use_container_width=True, hide_index=True)

# =============================================================================
# 2 · Margen y precio
# =============================================================================

with tabs[1]:
    st.markdown('<div class="section-title">Precio mínimo y precio objetivo</div>', unsafe_allow_html=True)
    rows = []
    for m in metrics.to_dict("records"):
        costo_bolsa = float(m["Costo bolsa recurrente"])
        precio_actual = float(m["Precio bolsa"])
        precio_obj = safe_div(costo_bolsa, 1 - margen_meta) if margen_meta < 1 else 0.0
        rows.append({
            "Producto": m["Producto"],
            "Precio actual / bolsa": precio_actual,
            "Costo recurrente / bolsa": costo_bolsa,
            "Precio objetivo / bolsa": precio_obj,
            "Brecha / bolsa": precio_obj - precio_actual,
            "Margen actual": m["Margen recurrente"],
            "Acción": "Subir/defender" if precio_actual < precio_obj else "Mantener piso",
        })
    precios = pd.DataFrame(rows)
    st.dataframe(fmt_df(precios), use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Precio actual", x=precios["Producto"], y=precios["Precio actual / bolsa"]))
        fig.add_trace(go.Bar(name="Precio objetivo", x=precios["Producto"], y=precios["Precio objetivo / bolsa"]))
        fig.update_layout(height=330, barmode="group", title="Precio actual vs objetivo por bolsa", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#cbd5e1")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("**Regla de decisión**")
        st.write("• Precio mínimo: costo recurrente por bolsa.")
        st.write("• Precio objetivo: costo / (1 - margen meta).")
        st.write("• Descuento solo contra volumen, pronto pago, retiro en planta o menor costo logístico real.")
        st.write("• No usar gastos no realizados de FX para definir precio base del cemento.")

# =============================================================================
# 3 · Conciliación P&G
# =============================================================================

with tabs[2]:
    st.markdown('<div class="section-title">Conciliación: costeo gerencial vs P&G oficial</div>', unsafe_allow_html=True)
    if not pyg.get("ok"):
        st.warning("Carga la contabilidad/P&G en la barra lateral para activar esta vista.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Utilidad app con extra", money(utilidad_app_con_extra), "Costeo gerencial", "blue")
        with c2:
            metric_card("Utilidad neta P&G", money(utilidad_pyg), "Resultado oficial", "good" if utilidad_pyg >= 0 else "bad")
        with c3:
            metric_card("Diferencia", money(utilidad_pyg - utilidad_app_con_extra), "P&G - app", "warn" if abs(utilidad_pyg - utilidad_app_con_extra) > 1 else "good")
        with c4:
            metric_card("Check puente", money(check), "Debe ser $0", "good" if abs(check) < 1 else "bad")

        puente = pd.DataFrame([
            {"Paso": "Utilidad app con extraordinarios", "Impacto": utilidad_app_con_extra, "Lectura": "Resultado gerencial del costeo"},
            {"Paso": "Diferencia ingresos P&G vs app", "Impacto": dif_ingreso, "Lectura": "Ventas, devoluciones, redondeos o partidas no capturadas por unidades"},
            {"Paso": "Diferencia neta costos/gastos/financieros/impuestos", "Impacto": dif_costos_netos, "Lectura": "P&G completo menos lo ya cargado por la app"},
            {"Paso": "Utilidad neta contable conciliada", "Impacto": utilidad_conciliada, "Lectura": "Debe igualar P&G"},
        ])
        st.dataframe(fmt_df(puente), use_container_width=True, hide_index=True)

        st.markdown('<div class="section-title">P&G agrupado</div>', unsafe_allow_html=True)
        pyg_rows = pd.DataFrame([
            {"Concepto": "Ingresos netos", "Valor": pyg["Ingresos netos"]},
            {"Concepto": "Costo de venta", "Valor": -pyg["Costo venta P&G"]},
            {"Concepto": "Gastos administración", "Valor": -pyg["Gastos administración"]},
            {"Concepto": "Gastos venta", "Valor": -pyg["Gastos venta"]},
            {"Concepto": "Gastos financieros", "Valor": -pyg["Gastos financieros"]},
            {"Concepto": "Impuestos", "Valor": -pyg["Impuestos"]},
            {"Concepto": "Otros/financieros clase 42 neto", "Valor": pyg["Resultado otros/financieros clase 42"]},
            {"Concepto": "Utilidad neta contable", "Valor": pyg["Utilidad neta contable"]},
        ])
        st.dataframe(fmt_df(pyg_rows), use_container_width=True, hide_index=True)

        st.markdown('<div class="section-title">Regla dura de conciliación</div>', unsafe_allow_html=True)
        st.write("• Cuentas 1, 2 y 3 son balance: se muestran como control, no como gasto del saco.")
        st.write("• La provisión de intereses 26050501 puede ser contablemente válida, pero no debe entrar al P&G como gasto si la contrapartida ya está en 53052002.")
        st.write("• Si una partida aparece en gastos base y también como extraordinaria, hay riesgo de doble castigo gerencial.")

# =============================================================================
# 4 · Palancas de costo
# =============================================================================

with tabs[3]:
    st.markdown('<div class="section-title">Palancas de costo sin tocar calidad ni seguridad</div>', unsafe_allow_html=True)
    # Pareto desde detalle de costo empacado + gastos + extraordinarios
    detalle = []
    for p in PRODUCTOS.values():
        b = df_mes[df_mes["Produccion_norm"] == norm_text(p.prod_empacado)].copy()
        b = b[b["Indice_norm"].isin({norm_text(i) for i in p.indices_empacado})]
        if not b.empty:
            b = b.groupby("Observacion", as_index=False)["Valor"].sum()
            b["Bloque"] = p.corto
            detalle.append(b)
    if detalle:
        pareto = pd.concat(detalle, ignore_index=True)
        pareto = pareto.sort_values("Valor", ascending=False)
        pareto["Participación"] = pareto["Valor"] / pareto["Valor"].sum()
        pareto["Acción CFO"] = pareto["Observacion"].map(lambda x: "Negociar fórmula/proveedor" if any(k in norm_text(x) for k in ["CEMENTO A GRANEL", "CLINKER", "SACO", "KRAFT"]) else "Controlar consumo o contrato")
        st.dataframe(fmt_df(pareto.head(15)), use_container_width=True, hide_index=True)
    else:
        st.info("No hay detalle suficiente para Pareto.")

    if not extras_df.empty:
        st.markdown('<div class="section-title">Extraordinarios cargados al modelo</div>', unsafe_allow_html=True)
        st.dataframe(fmt_df(extras_df), use_container_width=True, hide_index=True)
        st.warning("Validar si estas partidas ya están en gastos base. Si ya están, descontarlas otra vez como extraordinarias castiga dos veces la utilidad.")

# =============================================================================
# 5 · Datos y controles
# =============================================================================

with tabs[4]:
    st.markdown('<div class="section-title">Controles de calidad de datos</div>', unsafe_allow_html=True)
    controles = pd.DataFrame([
        {"Control": "Filas Consolidado mes", "Valor": len(df_mes), "Estado": "OK" if len(df_mes) > 0 else "Revisar"},
        {"Control": "Productos con venta", "Valor": int((metrics["Venta"] > 0).sum()), "Estado": "OK" if (metrics["Venta"] > 0).any() else "Revisar"},
        {"Control": "Bolsas producidas no vendidas", "Valor": inventario_bolsas, "Estado": "Revisar" if inventario_bolsas > 0 else "OK"},
        {"Control": "Costo inventario producido no vendido", "Valor": inventario_costo, "Estado": "Revisar" if inventario_costo > 0 else "OK"},
        {"Control": "Contabilidad/P&G cargado", "Valor": 1 if pyg.get("ok") else 0, "Estado": "OK" if pyg.get("ok") else "Pendiente"},
        {"Control": "Confianza ejecutiva", "Valor": conf, "Estado": "OK" if conf >= 0.8 else "Revisar"},
    ])
    st.dataframe(fmt_df(controles), use_container_width=True, hide_index=True)

    st.markdown('<div class="section-title">Datos crudos resumidos</div>', unsafe_allow_html=True)
    with st.expander("Ver resumen por producción en Consolidado"):
        resumen_prod = df_mes.groupby("Produccion", as_index=False).agg(Filas=("Valor", "size"), Valor=("Valor", "sum"))
        st.dataframe(fmt_df(resumen_prod.sort_values("Valor", ascending=False)), use_container_width=True, hide_index=True)
    if pyg.get("ok"):
        with st.expander("Ver cuentas P&G clase 4, 5, 6 y 7"):
            d = pyg["df"]
            p_g = d[d["Clase"].isin(["4", "5", "6", "7"])][["Auxiliar", "NombreAux", "TotalDebito", "TotalCredito", "Saldo"]].copy()
            p_g = p_g.sort_values("Saldo", key=lambda s: s.abs(), ascending=False)
            st.dataframe(fmt_df(p_g), use_container_width=True, hide_index=True)

