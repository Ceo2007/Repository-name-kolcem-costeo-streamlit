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
    """Formato porcentaje. Si no hay base real, muestra N/A en vez de 0,00%."""
    if v is None or pd.isna(v):
        return "N/A"
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
    # Margen real del periodo: solo existe si hubo venta.
    # Si no hubo ventas, 0% es falso; debe leerse como N/A.
    margen = safe_div(utilidad, venta) if venta > 0 else np.nan
    # Margen teórico a precio/lista: útil para validar precio antes de vender.
    margen_teorico_precio = safe_div(precio_bolsa - costo_bolsa, precio_bolsa) if precio_bolsa > 0 else np.nan
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
        "Margen teórico a precio actual": margen_teorico_precio,
        "Estado venta": "Con ventas" if und_vendidas > 0 else "Sin ventas",
        "Bolsas producidas no vendidas": inventario_und,
        "Costo inventario producido no vendido": costo_inv,
    }


# Productos físicos de producción para la pestaña de costeo puro.
# Esta vista NO usa ventas, ingresos, precios ni utilidad. Solo producción y costo.
COSTEO_FISICO_PRODUCTOS = [
    {
        "Producto": "UG granel",
        "Tipo": "Granel",
        "Presentación kg": np.nan,
        "Produccion": "Granel de Uso General (2841)",
        "Obs cantidad": "KG PRODUCIDOS Q",
        "Unidad cantidad": "kg",
        "Indices costo": ("C MP UG GRL", "C MO UG GRL", "C CIF UG GRL"),
        "Gastos producto": "",
    },
    {
        "Producto": "UG empacado 50 kg",
        "Tipo": "Empacado",
        "Presentación kg": 50.0,
        "Produccion": "Empacado UG 50KG (2843)",
        "Obs cantidad": "UND PRODUCIDAS Q",
        "Unidad cantidad": "bolsa",
        "Indices costo": ("C MP UG EMP", "C MO UG EMP", "C CIF UG EMP"),
        "Gastos producto": "UG_50",
    },
    {
        "Producto": "ART granel",
        "Tipo": "Granel",
        "Presentación kg": np.nan,
        "Produccion": "Cemento Granel ART (3645)",
        "Obs cantidad": "KG PRODUCIDOS Q",
        "Unidad cantidad": "kg",
        "Indices costo": ("C MP ART GRN", "C MO ART GRN", "C CIF ART GRN"),
        "Gastos producto": "",
    },
    {
        "Producto": "ART empacado 42,5 kg",
        "Tipo": "Empacado",
        "Presentación kg": 42.5,
        "Produccion": "Cemento Empacado ART 42.5 (4223)",
        "Obs cantidad": "UND PRODUCIDAS Q",
        "Unidad cantidad": "bolsa",
        "Indices costo": ("C MP ART EMP", "C MO ART EMP", "C CIF ART EMP"),
        "Gastos producto": "ART_42_5",
    },
]


def producto_por_key(key: str) -> Producto | None:
    for p in PRODUCTOS.values():
        if p.key == key:
            return p
    return None


def costeo_fisico_metrics(df_mes: pd.DataFrame, incluir_renta: bool, incluir_patrimonio: bool) -> pd.DataFrame:
    """Costeo puro de producción por producto físico.

    Regla CFO: esta tabla no mezcla ventas, precio, utilidad ni P&G. Sirve para saber
    cuánto cuesta producir 1 kg, 1 tonelada y, cuando aplica, una bolsa.
    """
    rows = []
    for cfg in COSTEO_FISICO_PRODUCTOS:
        cantidad_raw = sum_obs(df_mes, cfg["Produccion"], cfg["Obs cantidad"])
        peso = cfg["Presentación kg"]
        if cfg["Unidad cantidad"] == "kg":
            kg_producidos = cantidad_raw
            bolsas_producidas = np.nan
        else:
            bolsas_producidas = cantidad_raw
            kg_producidos = cantidad_raw * float(peso or 0)

        ton_producidas = kg_producidos / 1000 if kg_producidos else 0.0
        costo_industrial = sum_indices(df_mes, cfg["Produccion"], cfg["Indices costo"])

        gastos_asignados = 0.0
        producto_gasto_key = cfg.get("Gastos producto", "")
        producto_obj = producto_por_key(producto_gasto_key) if producto_gasto_key else None
        if producto_obj is not None:
            gastos_asignados = gastos_producto(df_mes, producto_obj, incluir_renta, incluir_patrimonio)

        costo_total = costo_industrial + gastos_asignados
        costo_kg_industrial = safe_div(costo_industrial, kg_producidos)
        gastos_kg = safe_div(gastos_asignados, kg_producidos)
        costo_kg_total = safe_div(costo_total, kg_producidos)
        costo_ton_total = costo_kg_total * 1000
        costo_bolsa = costo_kg_total * float(peso) if cfg["Unidad cantidad"] == "bolsa" and not pd.isna(peso) else np.nan

        if cfg["Tipo"] == "Granel":
            lectura = "Costo industrial de producción granel; no incluye gastos comerciales."
        else:
            lectura = "Costo empacado con gastos asignados; no incluye ingresos ni utilidad."

        rows.append({
            "Producto": cfg["Producto"],
            "Tipo": cfg["Tipo"],
            "Costo / kg total": costo_kg_total,
            "Costo / ton total": costo_ton_total,
            "Costo / bolsa": costo_bolsa,
            "Kg producidos": kg_producidos,
            "Ton producidas": ton_producidas,
            "Bolsas producidas": bolsas_producidas,
            "Presentación kg": peso,
            "Costo industrial": costo_industrial,
            "Costo industrial / kg": costo_kg_industrial,
            "Gastos asignados": gastos_asignados,
            "Gastos / kg": gastos_kg,
            "Costo total costeo": costo_total,
            "Lectura CFO": lectura,
            "Produccion base": cfg["Produccion"],
            "Indices costo": " | ".join(cfg["Indices costo"]),
        })
    return pd.DataFrame(rows)


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



def _latest_and_prev(hist: pd.DataFrame, col: str) -> tuple[float | None, float | None, float | None]:
    """Retorna actual, anterior y variación porcentual para una serie histórica."""
    if hist is None or hist.empty or col not in hist.columns:
        return None, None, None
    serie = hist[["Periodo", col]].dropna().copy()
    if serie.empty:
        return None, None, None
    serie = serie.sort_values("Periodo")
    actual = float(serie.iloc[-1][col])
    anterior = float(serie.iloc[-2][col]) if len(serie) >= 2 else None
    var = safe_div(actual - anterior, abs(anterior)) if anterior not in [None, 0] else None
    return actual, anterior, var


def fig_micro_line(hist: pd.DataFrame, y: str, title: str, suffix: str = "", money_axis: bool = False, decimals: int = 0) -> go.Figure:
    """Micrográfica sobria para junta: una señal por gráfico, sin ruido."""
    d = hist[["Periodo", "Periodo etiqueta", y]].dropna().copy() if y in hist.columns else pd.DataFrame()
    fig = go.Figure()
    if not d.empty:
        fig.add_trace(go.Scatter(
            x=d["Periodo etiqueta"],
            y=d[y],
            mode="lines+markers",
            line=dict(width=2),
            marker=dict(size=6),
            hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>",
        ))
    fig.update_layout(
        title=title,
        height=235,
        margin=dict(l=28, r=12, t=45, b=35),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=11),
        xaxis=dict(showgrid=False, tickangle=-20),
        yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.18)", ticksuffix=suffix),
        showlegend=False,
    )
    return fig


def historico_tendencias(df_base: pd.DataFrame, incluir_renta: bool, incluir_patrimonio: bool) -> pd.DataFrame:
    """Construye microtendencias desde Consolidado para costeo, producción, energía y empaque.

    No mezcla ingresos ni utilidad. Es una capa de señales operativas para CEO/CFO:
    costo/kg, toneladas producidas, energía, empaque e inventario físico.
    """
    periods = df_base[["Ano", "MesNro"]].drop_duplicates().sort_values(["Ano", "MesNro"])
    rows: list[dict] = []
    for _, pr in periods.iterrows():
        a = int(pr["Ano"])
        m = int(pr["MesNro"])
        df_m = filtro_periodo(df_base, a, m)
        if df_m.empty:
            continue
        fis = costeo_fisico_metrics(df_m, incluir_renta, incluir_patrimonio)
        prod_metrics = pd.DataFrame([producto_metrics(df_m, p, incluir_renta, incluir_patrimonio) for p in PRODUCTOS.values()])

        def get(prod: str, col: str) -> float:
            x = fis.loc[fis["Producto"] == prod, col]
            return float(x.iloc[0]) if not x.empty and not pd.isna(x.iloc[0]) else np.nan

        energia_mask = (
            df_m["Observacion_norm"].str.contains("ENERG", na=False)
            | df_m["Indice_norm"].str.contains("ENERG", na=False)
            | df_m["Observacion_norm"].str.contains("ELECT", na=False)
        )
        energia_total = float(df_m.loc[energia_mask, "Valor"].sum())
        sacos_mask = (
            df_m["Observacion_norm"].str.contains("SACO", na=False)
            | df_m["Observacion_norm"].str.contains("KRAFT", na=False)
            | df_m["Observacion_norm"].str.contains("EMPAQUE", na=False)
        )
        sacos_valor = float(df_m.loc[sacos_mask, "Valor"].sum())
        bolsas_total = float(prod_metrics["Bolsas producidas"].sum()) if not prod_metrics.empty else 0.0
        kg_empacado_total = float((prod_metrics["Bolsas producidas"] * prod_metrics["Peso kg"]).sum()) if not prod_metrics.empty else 0.0
        ton_empacadas = kg_empacado_total / 1000
        inv_bolsas = float(prod_metrics["Bolsas producidas no vendidas"].sum()) if not prod_metrics.empty else 0.0

        rows.append({
            "Ano": a,
            "MesNro": m,
            "Periodo": a * 100 + m,
            "Periodo etiqueta": f"{MESES_INV.get(m, m)[:3]} {a}",
            "Costo kg UG granel": get("UG granel", "Costo / kg total"),
            "Costo kg UG empacado": get("UG empacado 50 kg", "Costo / kg total"),
            "Costo kg ART granel": get("ART granel", "Costo / kg total"),
            "Costo kg ART empacado": get("ART empacado 42,5 kg", "Costo / kg total"),
            "Ton UG granel": get("UG granel", "Ton producidas"),
            "Ton UG empacado": get("UG empacado 50 kg", "Ton producidas"),
            "Ton ART granel": get("ART granel", "Ton producidas"),
            "Ton ART empacado": get("ART empacado 42,5 kg", "Ton producidas"),
            "Ton empacadas total": ton_empacadas,
            "Energía producción $": energia_total,
            "Energía $/ton empacada": safe_div(energia_total, ton_empacadas),
            "Sacos/empaque $": sacos_valor,
            "Sacos/empaque $/bolsa": safe_div(sacos_valor, bolsas_total),
            "Bolsas producidas no vendidas": inv_bolsas,
        })
    return pd.DataFrame(rows).sort_values("Periodo") if rows else pd.DataFrame()


def tendencia_texto(hist: pd.DataFrame, col: str, lower_is_better: bool = True, unidad: str = "") -> str:
    actual, anterior, var = _latest_and_prev(hist, col)
    if actual is None:
        return "Sin histórico suficiente"
    if anterior is None or var is None:
        return f"Actual {num(actual, 2)}{unidad}; falta mes anterior"
    signo = "sube" if actual > anterior else "baja" if actual < anterior else "estable"
    estado = "mejora" if ((actual < anterior and lower_is_better) or (actual > anterior and not lower_is_better)) else "deteriora" if actual != anterior else "estable"
    return f"{signo} {pct(var)} vs mes anterior · {estado}"


def analisis_ia_ejecutivo(
    metrics: pd.DataFrame,
    costeo_fisico: pd.DataFrame,
    hist: pd.DataFrame,
    pyg: dict,
    conf: float,
    warnings: list[str],
    margen_meta: float,
) -> tuple[str, str]:
    """Análisis tipo IA, sin depender de API externa: reglas CFO explicables y auditables."""
    alertas: list[str] = []
    oportunidades: list[str] = []
    decisiones: list[str] = []

    # Precio/costo por producto vendido o con lista.
    for m in metrics.to_dict("records"):
        producto = m["Producto"]
        precio = float(m.get("Precio bolsa", 0) or 0)
        costo = float(m.get("Costo bolsa recurrente", 0) or 0)
        vendidas = float(m.get("Bolsas vendidas", 0) or 0)
        if precio > 0 and precio < costo:
            alertas.append(f"{producto}: precio/lista por debajo del costo recurrente. Faltan {money(costo - precio, 0)} por bolsa para cubrir costo.")
            decisiones.append(f"Bloquear venta de {producto} hasta corregir precio o validar costo asignado.")
        elif precio > 0:
            objetivo = safe_div(costo, 1 - margen_meta) if margen_meta < 1 else np.nan
            if not pd.isna(objetivo) and precio < objetivo:
                oportunidades.append(f"{producto}: precio cubre costo, pero no alcanza margen meta. Faltan {money(objetivo - precio, 0)} por bolsa para meta.")
            elif not pd.isna(objetivo):
                oportunidades.append(f"{producto}: precio cumple margen meta; defender piso comercial.")
        if vendidas <= 0 and precio > 0:
            alertas.append(f"{producto}: no tuvo ventas; su margen real del periodo es N/A, no 0%. Validar precio/lista antes de lanzar.")

    # Costeo físico.
    if not costeo_fisico.empty:
        emp = costeo_fisico[costeo_fisico["Tipo"] == "Empacado"].copy()
        if not emp.empty:
            top = emp.sort_values("Costo / kg total", ascending=False).iloc[0]
            alertas.append(f"Producto empacado más costoso por kg: {top['Producto']} con {money(top['Costo / kg total'], 2)}/kg.")
        grn = costeo_fisico[costeo_fisico["Tipo"] == "Granel"].copy()
        if not grn.empty:
            topg = grn.sort_values("Costo / kg total", ascending=False).iloc[0]
            oportunidades.append(f"Granel de mayor costo/kg: {topg['Producto']}. Revisar materia prima, mezcla y energía específica antes de tocar calidad.")

    # Histórico.
    if hist is not None and not hist.empty and len(hist) >= 2:
        for col, label in [
            ("Costo kg UG empacado", "costo/kg UG empacado"),
            ("Energía $/ton empacada", "energía $/ton empacada"),
            ("Sacos/empaque $/bolsa", "empaque $/bolsa"),
        ]:
            actual, anterior, var = _latest_and_prev(hist, col)
            if actual is not None and anterior not in [None, 0] and var is not None:
                if var > 0.05:
                    alertas.append(f"{label} sube {pct(var)} vs mes anterior. Exige causa: precio, consumo, volumen o reclasificación.")
                elif var < -0.05:
                    oportunidades.append(f"{label} baja {pct(var)} vs mes anterior. Documentar causa para volverlo repetible.")

    # P&G.
    if pyg.get("ok"):
        utilidad = float(pyg.get("Utilidad neta contable", 0))
        margen = float(pyg.get("Margen neto contable", 0))
        if utilidad < 0:
            alertas.append("P&G oficial muestra pérdida neta. Comité debe priorizar caja, deuda, gastos financieros y precio.")
        elif margen < 0.05:
            alertas.append(f"Margen neto P&G bajo: {pct(margen)}. El producto puede dejar margen, pero la estructura se está comiendo la utilidad.")
        else:
            oportunidades.append(f"P&G oficial positivo con margen neto {pct(margen)}. Mantener disciplina de precio y atacar palancas sin dañar calidad.")
    else:
        alertas.append("No hay P&G legible: no se puede afirmar utilidad real de empresa; solo rentabilidad gerencial de costeo.")

    if warnings:
        for w in warnings:
            alertas.append(w)

    decisiones = decisiones or [
        "Separar comité de precio de comité contable: precio se decide con costo recurrente y margen meta; P&G se usa para utilidad real y estructura.",
        "Revisar mensualmente costo/kg, energía $/ton y empaque $/bolsa como señales tempranas.",
    ]
    alertas = alertas[:6]
    oportunidades = oportunidades[:6]
    decisiones = decisiones[:5]

    resumen = "\n".join([
        "### Análisis IA ejecutivo",
        f"**Confianza:** {conf:.2f}",
        "",
        "**Alertas clave**",
        *[f"- {x}" for x in alertas],
        "",
        "**Oportunidades accionables**",
        *[f"- {x}" for x in oportunidades],
        "",
        "**Decisiones recomendadas**",
        *[f"- {x}" for x in decisiones],
    ])
    prompt = "\n".join([
        "Actúa como CEO/CFO/Junta de empresa cementera. Analiza estos datos y entrega decisiones concretas.",
        f"Confianza del dato: {conf:.2f}",
        "\nCosteo físico actual:",
        costeo_fisico[["Producto", "Tipo", "Costo / kg total", "Costo / ton total", "Kg producidos", "Costo total costeo"]].to_string(index=False) if costeo_fisico is not None and not costeo_fisico.empty else "Sin datos",
        "\nRentabilidad por producto:",
        metrics[["Producto", "Bolsas producidas", "Bolsas vendidas", "Precio bolsa", "Costo bolsa recurrente", "Margen recurrente"]].to_string(index=False) if metrics is not None and not metrics.empty else "Sin datos",
    ])
    return resumen, prompt


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

st.markdown('<div class="main-title">Board Pack CEO/CFO · Utilidad real y costeo</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Primero utilidad real de la empresa; luego costeo por producto, precio, conciliación e inventario.</div>',
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
    "1 · Utilidad real empresa",
    "2 · Costeo productos",
    "3 · Margen y precio",
    "4 · Conciliación P&G",
    "5 · Palancas de costo",
    "6 · Microtendencias",
    "7 · Análisis IA",
    "8 · Datos y controles",
])

# =============================================================================
# 1 · Utilidad real empresa
# =============================================================================

with tabs[0]:
    st.markdown('<div class="section-title">Utilidad real de la empresa · P&G oficial</div>', unsafe_allow_html=True)

    if not pyg.get("ok"):
        st.error(
            "Para ver la utilidad real de la empresa debes cargar la contabilidad/P&G. "
            "La base de costeo sola solo muestra rentabilidad gerencial por producto; no utilidad neta oficial."
        )
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Utilidad real empresa", "No disponible", "Falta contabilidad/P&G", "bad")
        with c2:
            metric_card("Utilidad costeo", money(utilidad_app), "Gerencial, no contable", "blue")
        with c3:
            metric_card("Utilidad con extra", money(utilidad_app_con_extra), "Gerencial, no P&G", "warn")
        with c4:
            metric_card("Confianza", f"{conf:.2f}", "No apto para junta sin P&G", "warn")
        st.markdown(
            "<div class='board-note'><b>Regla:</b> utilidad real de empresa = utilidad neta del P&G contable. "
            "El costeo sirve para explicar margen por producto, precio y eficiencia, pero no reemplaza el estado de resultados.</div>",
            unsafe_allow_html=True,
        )
    else:
        ingresos_netos_real = float(pyg["Ingresos netos"])
        costo_venta_real = float(pyg["Costo venta P&G"])
        gastos_admin_real = float(pyg["Gastos administración"])
        gastos_venta_real = float(pyg["Gastos venta"])
        gastos_fin_real = float(pyg["Gastos financieros"])
        impuestos_real = float(pyg["Impuestos"])
        otros_ingresos_real = float(pyg["Resultado otros/financieros clase 42"])
        utilidad_real = float(pyg["Utilidad neta contable"])
        margen_neto_real = safe_div(utilidad_real, ingresos_netos_real)
        utilidad_bruta_real = ingresos_netos_real - costo_venta_real
        margen_bruto_real = safe_div(utilidad_bruta_real, ingresos_netos_real)
        utilidad_operativa_real = utilidad_bruta_real - gastos_admin_real - gastos_venta_real
        margen_operativo_real = safe_div(utilidad_operativa_real, ingresos_netos_real)
        diferencia_app_pyg = utilidad_real - utilidad_app_con_extra

        st.markdown(
            f"<div class='board-note'><b>Respuesta clara:</b> la utilidad real de la empresa en {mes_nombre} {ano} es "
            f"<b>{money(utilidad_real)}</b>, según P&G oficial cargado. "
            f"Margen neto real: <b>{pct(margen_neto_real)}</b>. "
            f"El costeo gerencial no es utilidad real; es una herramienta para explicar producto, precio y eficiencia.</div>",
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            metric_card("Utilidad real empresa", money(utilidad_real), "P&G oficial · después de impuestos", "good" if utilidad_real >= 0 else "bad")
        with c2:
            metric_card("Margen neto real", pct(margen_neto_real), "Utilidad neta / ingresos netos", "good" if margen_neto_real >= 0.05 else "warn" if margen_neto_real >= 0 else "bad")
        with c3:
            metric_card("Ingresos netos", money(ingresos_netos_real), "Ventas netas contables", "blue")
        with c4:
            metric_card("Ganancia bruta", money(utilidad_bruta_real), f"Margen bruto {pct(margen_bruto_real)}", "good" if utilidad_bruta_real >= 0 else "bad")
        with c5:
            metric_card("Resultado operativo", money(utilidad_operativa_real), f"Margen operativo {pct(margen_operativo_real)}", "good" if utilidad_operativa_real >= 0 else "bad")

        st.markdown('<div class="section-title">Estado de resultados ejecutivo</div>', unsafe_allow_html=True)
        pyg_ejecutivo = pd.DataFrame([
            {"Línea": "Ingresos netos", "Valor": ingresos_netos_real, "Lectura": "Venta real contable después de devoluciones/ajustes"},
            {"Línea": "Costo de venta y operación", "Valor": -costo_venta_real, "Lectura": "Costo reconocido oficialmente en P&G"},
            {"Línea": "Ganancia bruta", "Valor": utilidad_bruta_real, "Lectura": "Margen industrial/comercial antes de gastos"},
            {"Línea": "Gastos de administración", "Valor": -gastos_admin_real, "Lectura": "Estructura administrativa"},
            {"Línea": "Gastos de venta", "Valor": -gastos_venta_real, "Lectura": "Comercial, logística y ventas"},
            {"Línea": "Resultado operativo", "Valor": utilidad_operativa_real, "Lectura": "Resultado antes de financieros, otros e impuestos"},
            {"Línea": "Otros ingresos/financieros clase 42", "Valor": otros_ingresos_real, "Lectura": "Ingresos no operativos/financieros según contabilidad"},
            {"Línea": "Gastos financieros", "Valor": -gastos_fin_real, "Lectura": "Intereses y gastos financieros P&G"},
            {"Línea": "Impuestos", "Valor": -impuestos_real, "Lectura": "Impuesto reconocido en P&G"},
            {"Línea": "UTILIDAD REAL DE LA EMPRESA", "Valor": utilidad_real, "Lectura": "Utilidad neta oficial del periodo"},
        ])
        st.dataframe(fmt_df(pyg_ejecutivo), use_container_width=True, hide_index=True)

        st.markdown('<div class="section-title">Costeo gerencial vs utilidad real</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Utilidad costeo recurrente", money(utilidad_app), "Venta - costo vendido recurrente", "blue")
        with c2:
            metric_card("Utilidad costeo con extra", money(utilidad_app_con_extra), "Gerencial, no P&G oficial", "warn")
        with c3:
            metric_card("Diferencia P&G - costeo", money(diferencia_app_pyg), "Lo explica la conciliación", "warn" if abs(diferencia_app_pyg) > 1 else "good")
        with c4:
            metric_card("Check conciliación", money(check), "Debe ser $0", "good" if abs(check) < 1 else "bad")

        puente_simple = pd.DataFrame([
            {"Paso": "Utilidad de costeo gerencial con extraordinarios", "Impacto": utilidad_app_con_extra, "Qué significa": "Resultado de la app según costos, ventas y extraordinarios del modelo"},
            {"Paso": "Ajuste por ingresos contables no iguales a ventas app", "Impacto": dif_ingreso, "Qué significa": "Diferencia entre ingresos netos P&G y venta calculada por unidades"},
            {"Paso": "Ajuste neto por costos, gastos, financieros e impuestos", "Impacto": dif_costos_netos, "Qué significa": "Todo lo que P&G reconoce diferente al costeo gerencial"},
            {"Paso": "Utilidad real de la empresa", "Impacto": utilidad_real, "Qué significa": "Resultado neto oficial del periodo"},
        ])
        st.dataframe(fmt_df(puente_simple), use_container_width=True, hide_index=True)

        st.markdown(
            "<div class='board-note'><b>Advertencia clave:</b> el precio del cemento debe decidirse con margen comercial recurrente y costo por producto. "
            "La utilidad real P&G sirve para evaluar desempeño total de la empresa, deuda, impuestos y junta. Si mezclas ambas, tomas malas decisiones.</div>",
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">Costeo resumido por producto</div>', unsafe_allow_html=True)
    cols_show = ["Producto", "Bolsas producidas", "Bolsas vendidas", "Venta", "Costo vendido recurrente", "Utilidad recurrente", "Margen recurrente", "Costo inventario producido no vendido"]
    st.dataframe(fmt_df(metrics[cols_show]), use_container_width=True, hide_index=True)

# =============================================================================
# 2 · Costeo productos
# =============================================================================

with tabs[1]:
    st.markdown('<div class="section-title">Costeo físico de todos los productos</div>', unsafe_allow_html=True)
    st.markdown(
        "Esta vista es de costo puro: primero costo por kilo, luego toneladas, bolsas y componentes de costo. "
        "No muestra ingresos, precios, margen ni utilidad. Incluye granel y empacado."
    )

    costeo_fisico = costeo_fisico_metrics(df_mes, incluir_renta, incluir_patrimonio)

    cols_costeo_fisico = [
        "Producto", "Tipo",
        "Costo / kg total", "Costo / ton total", "Costo / bolsa",
        "Kg producidos", "Ton producidas", "Bolsas producidas", "Presentación kg",
        "Costo industrial", "Costo industrial / kg",
        "Gastos asignados", "Gastos / kg",
        "Costo total costeo", "Lectura CFO",
    ]

    st.dataframe(
        fmt_df(costeo_fisico[cols_costeo_fisico]),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown('<div class="section-title">Lectura rápida CFO</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    if not costeo_fisico.empty:
        ug_granel = costeo_fisico[costeo_fisico["Producto"] == "UG granel"]
        ug_emp = costeo_fisico[costeo_fisico["Producto"] == "UG empacado 50 kg"]
        art_granel = costeo_fisico[costeo_fisico["Producto"] == "ART granel"]
        art_emp = costeo_fisico[costeo_fisico["Producto"] == "ART empacado 42,5 kg"]
        with c1:
            if not ug_granel.empty:
                metric_card("UG granel · costo/kg", money(ug_granel.iloc[0]["Costo / kg total"], 2), f"{num(ug_granel.iloc[0]['Ton producidas'], 2)} t producidas", "neutral")
        with c2:
            if not ug_emp.empty:
                metric_card("UG empacado · costo/kg", money(ug_emp.iloc[0]["Costo / kg total"], 2), f"{num(ug_emp.iloc[0]['Bolsas producidas'], 0)} bolsas", "neutral")
        with c3:
            if not art_granel.empty:
                metric_card("ART granel · costo/kg", money(art_granel.iloc[0]["Costo / kg total"], 2), f"{num(art_granel.iloc[0]['Ton producidas'], 2)} t producidas", "neutral")
        with c4:
            if not art_emp.empty:
                metric_card("ART empacado · costo/kg", money(art_emp.iloc[0]["Costo / kg total"], 2), f"{num(art_emp.iloc[0]['Bolsas producidas'], 0)} bolsas", "neutral")

    st.markdown('<div class="section-title">Detalle auditable por producto</div>', unsafe_allow_html=True)
    for _, row in costeo_fisico.iterrows():
        with st.expander(f"{row['Producto']} · {row['Tipo']} · {money(row['Costo / kg total'], 2)}/kg", expanded=False):
            a, b, c, d = st.columns(4)
            with a:
                metric_card("Costo total / kg", money(row["Costo / kg total"], 2), "Primer KPI de costeo", "neutral")
            with b:
                metric_card("Ton producidas", num(row["Ton producidas"], 2), f"{num(row['Kg producidos'], 0)} kg", "neutral")
            with c:
                if row["Tipo"] == "Empacado":
                    metric_card("Bolsas producidas", num(row["Bolsas producidas"], 0), f"{num(row['Presentación kg'], 2)} kg/bolsa", "neutral")
                else:
                    metric_card("Producto granel", "Sin bolsas", "Cantidad medida en kg/ton", "neutral")
            with d:
                metric_card("Costo total costeo", money(row["Costo total costeo"], 0), "Industrial + gastos asignados si aplica", "neutral")

            st.write("**Componentes de costo industrial**")
            idx_set = {norm_text(x.strip()) for x in str(row["Indices costo"]).split("|") if x.strip()}
            detalle = df_mes[
                (df_mes["Produccion_norm"] == norm_text(row["Produccion base"]))
                & (df_mes["Indice_norm"].isin(idx_set))
            ].copy()
            if not detalle.empty:
                detalle_tbl = detalle.groupby(["Indice", "Observacion"], as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
                detalle_tbl["$/kg producido"] = detalle_tbl["Valor"].apply(lambda x: safe_div(x, row["Kg producidos"]))
                detalle_tbl["$/ton producida"] = detalle_tbl["$/kg producido"] * 1000
                st.dataframe(fmt_df(detalle_tbl), use_container_width=True, hide_index=True)
            else:
                st.info("No hay detalle industrial para este producto en el periodo.")

            if row["Tipo"] == "Empacado" and abs(float(row["Gastos asignados"] or 0)) > 1e-9:
                st.write("**Gastos asignados al empacado**")
                producto_obj = producto_por_key("UG_50" if "UG" in row["Producto"] else "ART_42_5")
                gastos_det = df_mes[df_mes["Produccion_norm"] == norm_text(producto_obj.prod_gastos)].copy() if producto_obj else pd.DataFrame()
                if not gastos_det.empty:
                    if producto_obj.key == "ART_42_5":
                        gastos_show = gastos_det[(gastos_det["Indice_norm"] == norm_text("TOTAL")) & (gastos_det["Observacion_norm"] == norm_text("GASTOS"))].copy()
                        if gastos_show.empty:
                            gastos_show = gastos_det.copy()
                    else:
                        idx_g = {norm_text(i) for i in producto_obj.indices_gasto_base}
                        if incluir_renta:
                            idx_g.add(norm_text("C IMP REN"))
                        if incluir_patrimonio:
                            idx_g.add(norm_text("C IMP PATR"))
                        gastos_show = gastos_det[gastos_det["Indice_norm"].isin(idx_g)].copy()
                        gastos_show = gastos_show[~mask_no_realizada(gastos_show)].copy()
                    if not gastos_show.empty:
                        gastos_tbl = gastos_show.groupby(["Indice", "Observacion"], as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
                        gastos_tbl["$/kg producido"] = gastos_tbl["Valor"].apply(lambda x: safe_div(x, row["Kg producidos"]))
                        st.dataframe(fmt_df(gastos_tbl), use_container_width=True, hide_index=True)

# =============================================================================
# 3 · Margen y precio
# =============================================================================

with tabs[2]:
    st.markdown('<div class="section-title">Precio mínimo, precio objetivo y precio real defendible</div>', unsafe_allow_html=True)
    st.markdown(
        "<div class='board-note'><b>Lectura CFO:</b> esta vista no usa la utilidad neta contable para fijar precio. "
        "Usa costo recurrente por bolsa y margen meta. Si un producto no tuvo ventas, el margen real del periodo es <b>N/A</b>, "
        "no 0%. Para productos sin ventas se muestra un margen teórico contra el precio/lista cargado.</div>",
        unsafe_allow_html=True,
    )

    rows = []
    alertas_precio = []
    for m in metrics.to_dict("records"):
        costo_bolsa = float(m["Costo bolsa recurrente"])
        precio_actual = float(m["Precio bolsa"])
        bolsas_vendidas = float(m["Bolsas vendidas"])
        precio_minimo = costo_bolsa
        precio_obj = safe_div(costo_bolsa, 1 - margen_meta) if margen_meta < 1 else np.nan
        margen_real_periodo = float(m["Margen recurrente"]) if bolsas_vendidas > 0 and not pd.isna(m["Margen recurrente"]) else np.nan
        margen_teorico = safe_div(precio_actual - costo_bolsa, precio_actual) if precio_actual > 0 else np.nan
        precio_obj = precio_obj if not pd.isna(precio_obj) else np.nan
        colchon_sobre_costo = max(precio_actual - costo_bolsa, 0.0) if precio_actual > 0 else 0.0
        faltante_cubrir_costo = max(costo_bolsa - precio_actual, 0.0) if precio_actual > 0 else costo_bolsa
        faltante_a_meta = max(precio_obj - precio_actual, 0.0) if not pd.isna(precio_obj) and precio_actual > 0 else np.nan
        excedente_sobre_meta = max(precio_actual - precio_obj, 0.0) if not pd.isna(precio_obj) and precio_actual > 0 else np.nan
        estado_costo = "Cubre costo" if precio_actual >= costo_bolsa and precio_actual > 0 else "Precio bajo costo" if precio_actual > 0 else "Sin precio"

        if bolsas_vendidas <= 0 and precio_actual < costo_bolsa:
            estado = "Sin ventas · precio bajo costo"
            accion = "Corregir lista antes de vender"
            alertas_precio.append(f"{m['Producto']}: no tuvo ventas y el precio/lista está por debajo del costo recurrente.")
        elif bolsas_vendidas <= 0:
            estado = "Sin ventas"
            accion = "Validar precio/lista antes de lanzar"
        elif precio_actual < costo_bolsa:
            estado = "Venta a pérdida"
            accion = "Bloquear precio / subir de inmediato"
            alertas_precio.append(f"{m['Producto']}: precio actual por debajo del costo recurrente.")
        elif precio_actual < precio_obj:
            estado = "Bajo meta"
            accion = "Subir/defender hasta meta"
        else:
            estado = "Cumple meta"
            accion = "Mantener piso"

        rows.append({
            "Producto": m["Producto"],
            "Bolsas vendidas": bolsas_vendidas,
            "Precio actual/lista / bolsa": precio_actual,
            "Costo recurrente / bolsa": costo_bolsa,
            "Precio mínimo / bolsa": precio_minimo,
            "Precio objetivo / bolsa": precio_obj,
            "Colchón sobre costo / bolsa": colchon_sobre_costo,
            "Faltante cubrir costo / bolsa": faltante_cubrir_costo,
            "Faltante a meta / bolsa": faltante_a_meta,
            "Excedente sobre meta / bolsa": excedente_sobre_meta,
            "Estado costo": estado_costo,
            "Margen real del periodo": margen_real_periodo,
            "Margen teórico a precio actual": margen_teorico,
            "Estado CFO": estado,
            "Acción": accion,
        })

    precios = pd.DataFrame(rows)
    st.dataframe(fmt_df(precios), use_container_width=True, hide_index=True)

    if alertas_precio:
        st.error("\n".join(["Alertas de precio:"] + [f"• {a}" for a in alertas_precio]))
    else:
        st.success("No hay productos vendidos por debajo del costo recurrente según la base cargada.")

    c1, c2 = st.columns([1.1, 0.9])
    with c1:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Precio actual/lista", x=precios["Producto"], y=precios["Precio actual/lista / bolsa"]))
        fig.add_trace(go.Bar(name="Costo recurrente", x=precios["Producto"], y=precios["Costo recurrente / bolsa"]))
        fig.add_trace(go.Bar(name="Precio objetivo", x=precios["Producto"], y=precios["Precio objetivo / bolsa"]))
        fig.update_layout(
            height=330,
            barmode="group",
            title="Precio vs costo y objetivo por bolsa",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#cbd5e1",
            margin=dict(l=30, r=20, t=55, b=50),
        )
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("**Regla de decisión**")
        st.write("• Precio mínimo contable: costo recurrente por bolsa. Debajo de eso, destruye margen.")
        st.write("• Precio objetivo: costo / (1 - margen meta).")
        st.write("• Si no hubo ventas, no existe margen real del periodo: se valida contra margen teórico del precio/lista.")
        st.write("• Descuento solo contra volumen, pronto pago, retiro en planta o menor costo logístico real.")
        st.write("• No usar FX no realizada ni utilidad neta P&G para definir precio base del saco.")

# =============================================================================
# 4 · Conciliación P&G
# =============================================================================

with tabs[3]:
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

        st.markdown(
            f"<div class='board-note'><b>Lectura simple:</b> la app calcula una utilidad gerencial de {money(utilidad_app_con_extra)}. "
            f"El P&G oficial muestra {money(utilidad_pyg)}. La diferencia es {money(utilidad_pyg - utilidad_app_con_extra)} porque "
            f"la contabilidad trae ingresos, costos, gastos financieros, impuestos y reclasificaciones que el costeo gerencial no mide igual. "
            f"El check en {money(check)} significa que el puente explica la diferencia.</div>",
            unsafe_allow_html=True,
        )

        puente = pd.DataFrame([
            {"Paso": "Utilidad app con extraordinarios", "Impacto": utilidad_app_con_extra, "Lectura": "Resultado gerencial del costeo"},
            {"Paso": "Diferencia ingresos P&G vs app", "Impacto": dif_ingreso, "Lectura": "Ventas, devoluciones, redondeos o partidas no capturadas por unidades"},
            {"Paso": "P&G tiene más/menos costo y gasto neto que la app", "Impacto": dif_costos_netos, "Lectura": "Costo de venta, gastos, financieros, impuestos y reclasificaciones contables no medidos igual por el costeo"},
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
# 5 · Palancas de costo
# =============================================================================

with tabs[4]:
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
# 6 · Microtendencias
# =============================================================================

with tabs[5]:
    st.markdown('<div class="section-title">Microtendencias históricas · costo, producción, energía y empaque</div>', unsafe_allow_html=True)
    st.markdown(
        "Señales ejecutivas por mes desde Consolidado. No son decoración: sirven para detectar deterioro temprano en costo/kg, volumen, energía y empaque."
    )
    hist = historico_tendencias(df_base, incluir_renta, incluir_patrimonio)
    if hist.empty or len(hist) < 2:
        st.warning("No hay suficiente histórico para micrográficas. Se requieren al menos dos meses en Consolidado.")
    else:
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            metric_card("Costo/kg UG empacado", money(hist.iloc[-1]["Costo kg UG empacado"], 2), tendencia_texto(hist, "Costo kg UG empacado", True), "neutral")
        with k2:
            metric_card("Ton UG empacado", num(hist.iloc[-1]["Ton UG empacado"], 2), tendencia_texto(hist, "Ton UG empacado", False, " t"), "neutral")
        with k3:
            metric_card("Energía $/ton empacada", money(hist.iloc[-1]["Energía $/ton empacada"], 0), tendencia_texto(hist, "Energía $/ton empacada", True), "neutral")
        with k4:
            metric_card("Empaque $/bolsa", money(hist.iloc[-1]["Sacos/empaque $/bolsa"], 0), tendencia_texto(hist, "Sacos/empaque $/bolsa", True), "neutral")

        r1c1, r1c2 = st.columns(2)
        with r1c1:
            st.plotly_chart(fig_micro_line(hist, "Costo kg UG granel", "Costo/kg UG granel"), use_container_width=True)
        with r1c2:
            st.plotly_chart(fig_micro_line(hist, "Costo kg UG empacado", "Costo/kg UG empacado"), use_container_width=True)
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            st.plotly_chart(fig_micro_line(hist, "Ton UG empacado", "Producción UG empacado · toneladas"), use_container_width=True)
        with r2c2:
            st.plotly_chart(fig_micro_line(hist, "Energía $/ton empacada", "Energía producción · $/ton empacada"), use_container_width=True)
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            st.plotly_chart(fig_micro_line(hist, "Sacos/empaque $/bolsa", "Sacos/empaque · $/bolsa"), use_container_width=True)
        with r3c2:
            st.plotly_chart(fig_micro_line(hist, "Bolsas producidas no vendidas", "Bolsas producidas no vendidas"), use_container_width=True)

        with st.expander("Ver base histórica de microtendencias"):
            st.dataframe(fmt_df(hist), use_container_width=True, hide_index=True)

# =============================================================================
# 7 · Análisis IA
# =============================================================================

with tabs[6]:
    st.markdown('<div class="section-title">Análisis IA ejecutivo · CEO/CFO/Junta</div>', unsafe_allow_html=True)
    costeo_fisico_actual = costeo_fisico_metrics(df_mes, incluir_renta, incluir_patrimonio)
    hist_actual = historico_tendencias(df_base, incluir_renta, incluir_patrimonio)
    resumen_ia, prompt_ia = analisis_ia_ejecutivo(
        metrics=metrics,
        costeo_fisico=costeo_fisico_actual,
        hist=hist_actual,
        pyg=pyg,
        conf=conf,
        warnings=warnings,
        margen_meta=margen_meta,
    )
    st.markdown(resumen_ia)
    st.markdown('<div class="section-title">Prompt para análisis externo o comité</div>', unsafe_allow_html=True)
    st.text_area("Prompt IA auditable", prompt_ia, height=260)
    st.caption("Este análisis no llama una API externa: usa reglas CFO explicables sobre los datos cargados. Si quieres un análisis generativo, copia el prompt y pégalo en ChatGPT.")

# =============================================================================
# 8 · Datos y controles
# =============================================================================

with tabs[7]:
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

