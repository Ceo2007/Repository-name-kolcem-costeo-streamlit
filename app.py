from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# =============================================================================
# Kolcem · Board Ready Costing App
# Filosofía: primero decisión; después explicación; nunca mezclar P&G, costeo y precio.
# =============================================================================

st.set_page_config(
    page_title="Kolcem · Utilidad Real y Costeo",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{
  --bg:#0b1220; --panel:#101827; --panel2:#0f172a; --panel3:#111f33;
  --line:#263245; --text:#e5e7eb; --muted:#9aa7b8; --soft:#cbd5e1;
  --orange:#f97316; --green:#22c55e; --amber:#f59e0b; --red:#ef4444; --blue:#60a5fa;
}
html,body,.stApp,[class*="css"]{font-family:Inter,system-ui,-apple-system,Segoe UI,sans-serif!important;}
.stApp{background:var(--bg);color:var(--text);}
.block-container{padding-top:1.1rem!important;max-width:1280px!important;}
section[data-testid="stSidebar"]{background:#09111f!important;border-right:1px solid var(--line)!important;}
section[data-testid="stSidebar"] h2,section[data-testid="stSidebar"] h3{font-size:.74rem!important;color:var(--orange)!important;text-transform:uppercase;letter-spacing:.08em;}
section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] p{color:var(--muted)!important;}
.main-title{font-size:1.45rem;font-weight:800;line-height:1.12;margin:0 0 .25rem;color:var(--text);}
.subtitle{color:var(--muted);font-size:.92rem;margin-bottom:.8rem;}
.section-title{font-size:.82rem;text-transform:uppercase;letter-spacing:.08em;color:#cbd5e1;font-weight:800;margin:18px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px;}
.executive-strip{background:#0f1b2e;border:1px solid var(--line);border-left:4px solid var(--orange);border-radius:10px;padding:11px 13px;margin:10px 0 14px;color:var(--soft);font-size:.88rem;line-height:1.45;}
.decision-box{background:#101827;border:1px solid var(--line);border-radius:12px;padding:14px 15px;margin:10px 0 14px;}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 13px;min-height:82px;}
.card-label{font-size:.64rem;text-transform:uppercase;letter-spacing:.075em;color:var(--muted);font-weight:800;margin-bottom:6px;}
.card-value{font-size:1.02rem;font-weight:800;color:var(--text);letter-spacing:-.01em;line-height:1.16;}
.card-help{font-size:.71rem;color:var(--muted);margin-top:5px;line-height:1.25;}
.good{border-left:4px solid var(--green)} .good .card-value{color:#4ade80}
.warn{border-left:4px solid var(--amber)} .warn .card-value{color:#fbbf24}
.bad{border-left:4px solid var(--red)} .bad .card-value{color:#f87171}
.blue{border-left:4px solid var(--blue)} .blue .card-value{color:#93c5fd}
.neutral{border-left:4px solid #64748b}
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#0f172a;border:1px solid var(--line);border-radius:12px;padding:4px;}
.stTabs [data-baseweb="tab"]{border-radius:9px;padding:8px 10px;font-size:.8rem;color:var(--muted);}
.stTabs [aria-selected="true"]{background:var(--orange)!important;color:white!important;}
div[data-testid="stDataFrame"]{border:1px solid var(--line)!important;border-radius:12px!important;overflow:hidden;}
.small-note{color:var(--muted);font-size:.80rem;line-height:1.4;}
hr{border-color:var(--line)}
</style>
""",
    unsafe_allow_html=True,
)

# =============================================================================
# Formato y normalización
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
        return 0.0 if pd.isna(value) else float(value)
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
        out = float(text)
        return -out if neg else out
    except Exception:
        return 0.0


def safe_div(a: float, b: float) -> float:
    if b is None or pd.isna(b) or abs(float(b)) < 1e-12:
        return 0.0
    return float(a) / float(b)


def money(v: float, decimals: int = 0) -> str:
    if v is None or pd.isna(v):
        v = 0.0
    return f"${float(v):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num(v: float, decimals: int = 0) -> str:
    if v is None or pd.isna(v):
        v = 0.0
    return f"{float(v):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(v: float | None) -> str:
    if v is None or pd.isna(v):
        return "N/A"
    return f"{float(v):.2%}".replace(".", ",")


def card(label: str, value: str, help_text: str = "", color: str = "neutral") -> None:
    st.markdown(
        f"""
<div class="card {color}">
  <div class="card-label">{label}</div>
  <div class="card-value">{value}</div>
  <div class="card-help">{help_text}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def fmt_df(df: pd.DataFrame) -> pd.io.formats.style.Styler:
    fmt = {}
    for col in df.columns:
        nc = norm_text(col)
        if pd.api.types.is_numeric_dtype(df[col]):
            if any(k in nc for k in ["MARGEN", "PARTICIPACION", "CONFIANZA", "%"]):
                fmt[col] = lambda x: pct(x)
            elif any(k in nc for k in ["VALOR", "COSTO", "UTILIDAD", "INGRESO", "VENTA", "GASTO", "BRECHA", "FALTANTE", "COLCHON", "PRECIO", "IMPACTO", "AHORRO", "SALDO", "DEBITO", "CREDITO", "DIFERENCIA", "APP", "CONTABILIDAD"]):
                fmt[col] = lambda x: money(x, 0)
            else:
                fmt[col] = lambda x: num(x, 2)
    return df.style.format(fmt)

# =============================================================================
# Productos y reglas
# =============================================================================

@dataclass(frozen=True)
class Vendible:
    key: str
    corto: str
    nombre: str
    peso_kg: float
    prod_empacado: str
    prod_gastos: str
    prod_precio: str
    obs_vendida: str
    obs_precio: str
    indices_empacado: tuple[str, ...]
    indices_gasto: tuple[str, ...]


VENDIBLES = {
    "UG_50": Vendible(
        key="UG_50",
        corto="UG 50 kg",
        nombre="Cemento UG empacado 50 kg",
        peso_kg=50.0,
        prod_empacado="Empacado UG 50KG (2843)",
        prod_gastos="Gastos Administrativos y de Venta",
        prod_precio="Precio Final",
        obs_vendida="CEMENTO KOLCEM UG 50 KG",
        obs_precio="PRECIO PROMEDIO POR BOLSA 50 KG",
        indices_empacado=("C MP UG EMP", "C MO UG EMP", "C CIF UG EMP"),
        indices_gasto=("C MO ADM", "C CIF ADM", "C MO UG VEN", "C CIF UG VEN", "C FIN", "C IMP"),
    ),
    "ART_42_5": Vendible(
        key="ART_42_5",
        corto="ART 42,5 kg",
        nombre="Cemento ART estructural empacado 42,5 kg",
        peso_kg=42.5,
        prod_empacado="Cemento Empacado ART 42.5 (4223)",
        prod_gastos="Gastos Administrativos y de Venta ART",
        prod_precio="Precio Final ART",
        obs_vendida="CEMENTO KOLCEM ART 42.5 KG",
        obs_precio="PRECIO PROMEDIO POR BOLSA 42.5 KG",
        indices_empacado=("C MP ART EMP", "C MO ART EMP", "C CIF ART EMP"),
        indices_gasto=("C ADM Y VEN ART EMP",),
    ),
}

FISICOS = [
    {
        "Producto": "UG granel",
        "Tipo": "Granel",
        "Presentación kg": np.nan,
        "Produccion": "Granel de Uso General (2841)",
        "Obs cantidad": "KG PRODUCIDOS Q",
        "Unidad": "kg",
        "Indices costo": ("C MP UG GRL", "C MO UG GRL", "C CIF UG GRL"),
        "Vendible key": "",
        "Incluye gastos": False,
    },
    {
        "Producto": "UG empacado 50 kg",
        "Tipo": "Empacado",
        "Presentación kg": 50.0,
        "Produccion": "Empacado UG 50KG (2843)",
        "Obs cantidad": "UND PRODUCIDAS Q",
        "Unidad": "bolsa",
        "Indices costo": ("C MP UG EMP", "C MO UG EMP", "C CIF UG EMP"),
        "Vendible key": "UG_50",
        "Incluye gastos": True,
    },
    {
        "Producto": "ART granel",
        "Tipo": "Granel",
        "Presentación kg": np.nan,
        "Produccion": "Cemento Granel ART (3645)",
        "Obs cantidad": "KG PRODUCIDOS Q",
        "Unidad": "kg",
        "Indices costo": ("C MP ART GRN", "C MO ART GRN", "C CIF ART GRN"),
        "Vendible key": "",
        "Incluye gastos": False,
    },
    {
        "Producto": "ART empacado 42,5 kg",
        "Tipo": "Empacado",
        "Presentación kg": 42.5,
        "Produccion": "Cemento Empacado ART 42.5 (4223)",
        "Obs cantidad": "UND PRODUCIDAS Q",
        "Unidad": "bolsa",
        "Indices costo": ("C MP ART EMP", "C MO ART EMP", "C CIF ART EMP"),
        "Vendible key": "ART_42_5",
        "Incluye gastos": True,
    },
]

# =============================================================================
# Carga de datos
# =============================================================================

@st.cache_data(show_spinner=False)
def load_base(uploaded_bytes: bytes) -> pd.DataFrame:
    xls = pd.ExcelFile(io.BytesIO(uploaded_bytes), engine="openpyxl")
    if "Consolidado" not in xls.sheet_names:
        raise ValueError("El archivo debe tener una hoja llamada Consolidado.")
    df = pd.read_excel(xls, sheet_name="Consolidado", engine="openpyxl")
    df = df.rename(columns={"Producción": "Produccion", "Concepto": "Observacion", "Año": "Ano"}).copy()
    required = ["Produccion", "Indice", "Observacion", "Valor", "Mes", "Ano", "MesNro"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Faltan columnas en Consolidado: " + ", ".join(missing))
    df = df.dropna(how="all").copy()
    df["Valor"] = df["Valor"].apply(parse_valor).astype(float)
    df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").fillna(0).astype(int)
    df["MesNro"] = pd.to_numeric(df["MesNro"], errors="coerce")
    df["MesNro"] = df["MesNro"].fillna(df["Mes"].map(MESES)).fillna(0).astype(int)
    for col in ["Produccion", "Indice", "Observacion", "Mes"]:
        df[col] = df[col].fillna("").astype(str).str.strip()
    df["Produccion_norm"] = df["Produccion"].map(norm_text)
    df["Indice_norm"] = df["Indice"].map(norm_text)
    df["Observacion_norm"] = df["Observacion"].map(norm_text)
    return df


@st.cache_data(show_spinner=False)
def load_contabilidad(uploaded_bytes: bytes) -> pd.DataFrame:
    """Carga la contabilidad exportada desde la consulta SQL.

    Soporta dos formatos:
    1. Exportación estándar de la consulta: anio/mes/codigo_auxiliar/nombre_auxiliar/total_debito/total_credito/saldo_neto.
    2. Archivo actual: Ano/Mes/Auxiliar/NombreAux/NumeroMovimientos/TotalDebito/TotalCredito.

    Si el archivo no trae Saldo, lo calcula como TotalDebito - TotalCredito.
    """
    xls = pd.ExcelFile(io.BytesIO(uploaded_bytes), engine="openpyxl")
    preferred = "Hoja2" if "Hoja2" in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=preferred, engine="openpyxl")

    mapping = {}
    for c in df.columns:
        nc = norm_text(c)
        flat = re.sub(r"[^A-Z0-9]", "", nc)

        if flat in {"ANO", "ANIO", "YEAR"}:
            mapping[c] = "Ano"
        elif flat in {"MES", "MONTH"}:
            mapping[c] = "Mes"
        elif flat in {"AUXILIAR", "CODIGO", "CUENTA", "CODIGOAUXILIAR", "CODAUXILIAR", "MASCOS", "GLCOD"}:
            mapping[c] = "Auxiliar"
        elif flat in {"NOMBREAUX", "NOMBREAUXILIAR", "NOMBRE", "DESCRIPCION", "GLNUM"}:
            mapping[c] = "NombreAux"
        elif flat in {"NUMEROMOVIMIENTOS", "MOVIMIENTOS", "NUMMOVIMIENTOS"}:
            mapping[c] = "NumeroMovimientos"
        elif "DEBIT" in flat or flat in {"DEBE", "TOTALDEBE"}:
            mapping[c] = "TotalDebito"
        elif "CREDIT" in flat or flat in {"HABER", "TOTALHABER"}:
            mapping[c] = "TotalCredito"
        elif "SALDO" in flat:
            mapping[c] = "Saldo"

    df = df.rename(columns=mapping).copy()

    required_base = ["Ano", "Mes", "Auxiliar"]
    missing_base = [c for c in required_base if c not in df.columns]
    if missing_base:
        raise ValueError(
            "La contabilidad debe traer como mínimo Año, Mes y Auxiliar/Codigo_Auxiliar. "
            "Faltan: " + ", ".join(missing_base)
        )

    if "NombreAux" not in df.columns:
        df["NombreAux"] = ""

    if "TotalDebito" not in df.columns:
        df["TotalDebito"] = 0.0
    if "TotalCredito" not in df.columns:
        df["TotalCredito"] = 0.0

    df = df.dropna(how="all").copy()
    df["Ano"] = pd.to_numeric(df["Ano"], errors="coerce").fillna(0).astype(int)
    df["Mes"] = pd.to_numeric(df["Mes"], errors="coerce").fillna(0).astype(int)
    df["Auxiliar"] = df["Auxiliar"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.strip()
    df["NombreAux"] = df["NombreAux"].fillna("").astype(str).str.strip()

    for col in ["TotalDebito", "TotalCredito"]:
        df[col] = df[col].apply(parse_valor).astype(float)

    if "Saldo" not in df.columns:
        df["Saldo"] = df["TotalDebito"] - df["TotalCredito"]
    else:
        df["Saldo"] = df["Saldo"].apply(parse_valor).astype(float)

    if "NumeroMovimientos" not in df.columns:
        df["NumeroMovimientos"] = np.nan
    else:
        df["NumeroMovimientos"] = pd.to_numeric(df["NumeroMovimientos"], errors="coerce")

    df["Clase"] = df["Auxiliar"].str[0]
    return df

def periodo_df(df: pd.DataFrame, ano: int, mes: int) -> pd.DataFrame:
    return df[(df["Ano"] == ano) & (df["MesNro"] == mes)].copy()

# =============================================================================
# Cálculos de costeo
# =============================================================================


def sum_obs(df: pd.DataFrame, produccion: str, observacion: str) -> float:
    return float(df.loc[(df["Produccion_norm"] == norm_text(produccion)) & (df["Observacion_norm"] == norm_text(observacion)), "Valor"].sum())


def sum_indices(df: pd.DataFrame, produccion: str, indices: Iterable[str]) -> float:
    idx = {norm_text(i) for i in indices}
    return float(df.loc[(df["Produccion_norm"] == norm_text(produccion)) & (df["Indice_norm"].isin(idx)), "Valor"].sum())


def fx_no_realizada_mask(df: pd.DataFrame) -> pd.Series:
    obs = df["Observacion_norm"].fillna("")
    return obs.str.contains("DIFERENCIA", na=False) & obs.str.contains("CAMBIO", na=False) & obs.str.contains("NO REALIZ", na=False)


def gastos_asignados(df: pd.DataFrame, producto: Vendible, incluir_renta: bool, incluir_patrimonio: bool) -> float:
    base = df[df["Produccion_norm"] == norm_text(producto.prod_gastos)].copy()
    if base.empty:
        return 0.0
    if producto.key == "ART_42_5":
        total = float(base.loc[(base["Indice_norm"] == norm_text("TOTAL")) & (base["Observacion_norm"] == norm_text("GASTOS")), "Valor"].sum())
        return total
    idx = {norm_text(i) for i in producto.indices_gasto}
    if incluir_renta:
        idx.add(norm_text("C IMP REN"))
    if incluir_patrimonio:
        idx.add(norm_text("C IMP PATR"))
    base = base[base["Indice_norm"].isin(idx)].copy()
    base = base[~fx_no_realizada_mask(base)].copy()
    return float(base["Valor"].sum())


def vendible_metrics(df_mes: pd.DataFrame, producto: Vendible, incluir_renta: bool, incluir_patrimonio: bool) -> dict:
    bolsas_producidas = sum_obs(df_mes, producto.prod_empacado, "UND PRODUCIDAS Q")
    kg_producidos = bolsas_producidas * producto.peso_kg
    ton_producidas = kg_producidos / 1000
    bolsas_vendidas = sum_obs(df_mes, "Cantidades Vendidas", producto.obs_vendida)
    kg_vendidos = bolsas_vendidas * producto.peso_kg
    ton_vendidas = kg_vendidos / 1000
    precio_bolsa = sum_obs(df_mes, producto.prod_precio, producto.obs_precio)
    costo_industrial = sum_indices(df_mes, producto.prod_empacado, producto.indices_empacado)
    gastos = gastos_asignados(df_mes, producto, incluir_renta, incluir_patrimonio)
    costo_comercial = costo_industrial + gastos
    costo_bolsa = safe_div(costo_comercial, bolsas_producidas)
    costo_kg = safe_div(costo_comercial, kg_producidos)
    costo_vendido = costo_bolsa * bolsas_vendidas
    venta = precio_bolsa * bolsas_vendidas
    utilidad = venta - costo_vendido
    margen = safe_div(utilidad, venta) if venta > 0 else np.nan
    margen_teorico = safe_div(precio_bolsa - costo_bolsa, precio_bolsa) if precio_bolsa > 0 else np.nan
    inv_bolsas = max(bolsas_producidas - bolsas_vendidas, 0)
    return {
        "Producto": producto.corto,
        "Nombre": producto.nombre,
        "Peso kg": producto.peso_kg,
        "Bolsas producidas": bolsas_producidas,
        "Bolsas vendidas": bolsas_vendidas,
        "Kg producidos": kg_producidos,
        "Ton producidas": ton_producidas,
        "Ton vendidas": ton_vendidas,
        "Precio bolsa": precio_bolsa,
        "Costo industrial": costo_industrial,
        "Gastos asignados": gastos,
        "Costo comercial producido": costo_comercial,
        "Costo bolsa recurrente": costo_bolsa,
        "Costo kg recurrente": costo_kg,
        "Costo vendido recurrente": costo_vendido,
        "Venta": venta,
        "Utilidad recurrente": utilidad,
        "Margen recurrente": margen,
        "Margen teórico": margen_teorico,
        "Bolsas producidas no vendidas": inv_bolsas,
        "Costo inventario no vendido": inv_bolsas * costo_bolsa,
    }


def costeo_fisico(df_mes: pd.DataFrame, incluir_renta: bool, incluir_patrimonio: bool) -> pd.DataFrame:
    rows = []
    for cfg in FISICOS:
        cantidad = sum_obs(df_mes, cfg["Produccion"], cfg["Obs cantidad"])
        peso = cfg["Presentación kg"]
        if cfg["Unidad"] == "kg":
            kg = cantidad
            bolsas = np.nan
        else:
            bolsas = cantidad
            kg = cantidad * float(peso)
        ton = kg / 1000
        costo_ind = sum_indices(df_mes, cfg["Produccion"], cfg["Indices costo"])
        gastos = 0.0
        if cfg["Vendible key"]:
            gastos = gastos_asignados(df_mes, VENDIBLES[cfg["Vendible key"]], incluir_renta, incluir_patrimonio)
        costo_total = costo_ind + gastos
        costo_kg_ind = safe_div(costo_ind, kg)
        gastos_kg = safe_div(gastos, kg)
        costo_kg_total = safe_div(costo_total, kg)
        costo_ton = costo_kg_total * 1000
        costo_bolsa = costo_kg_total * float(peso) if cfg["Unidad"] == "bolsa" and not pd.isna(peso) else np.nan
        rows.append({
            "Producto": cfg["Producto"],
            "Tipo": cfg["Tipo"],
            "Costo / kg total": costo_kg_total,
            "Costo / ton total": costo_ton,
            "Costo / bolsa": costo_bolsa,
            "Kg producidos": kg,
            "Ton producidas": ton,
            "Bolsas producidas": bolsas,
            "Presentación kg": peso,
            "Costo industrial": costo_ind,
            "Costo industrial / kg": costo_kg_ind,
            "Gastos asignados": gastos,
            "Gastos / kg": gastos_kg,
            "Costo total costeo": costo_total,
            "Base contable": cfg["Produccion"],
            "Índices": " | ".join(cfg["Indices costo"]),
        })
    return pd.DataFrame(rows)


def extras_df(df_mes: pd.DataFrame) -> pd.DataFrame:
    out = df_mes[df_mes["Produccion_norm"] == norm_text("Gastos ExtraOrdinarios")].copy()
    if out.empty:
        return pd.DataFrame(columns=["Indice", "Observacion", "Valor"])
    return out[["Indice", "Observacion", "Valor"]].sort_values("Valor", ascending=False)



# =============================================================================
# Simulación simple de producción, costo y utilidad
# =============================================================================


def _sum_indice_token(df_mes: pd.DataFrame, produccion: str, indices: Iterable[str], token: str) -> float:
    idx = {norm_text(i) for i in indices if token in norm_text(i)}
    if not idx:
        return 0.0
    return float(
        df_mes.loc[
            (df_mes["Produccion_norm"] == norm_text(produccion))
            & (df_mes["Indice_norm"].isin(idx)),
            "Valor",
        ].sum()
    )


def simular_productos_vendibles(
    df_mes: pd.DataFrame,
    simulacion_inputs: dict[str, dict[str, float]],
    incluir_renta: bool,
    incluir_patrimonio: bool,
) -> pd.DataFrame:
    """Simula el costo y la utilidad usando una regla simple y auditable.

    Regla gerencial:
    - Materia prima empacada: variable con la nueva producción.
    - Mano de obra de producción: fija del mes base.
    - CIF industrial: fijo del mes base.
    - Gastos administrativos/ventas asignados: fijos del mes base.

    La regla evita el error típico de proyectar todo como variable. Si todo se vuelve variable,
    producir más nunca diluye estructura y la simulación pierde valor gerencial.
    """
    rows = []
    for producto in VENDIBLES.values():
        actual = vendible_metrics(df_mes, producto, incluir_renta, incluir_patrimonio)
        inp = simulacion_inputs.get(producto.key, {})

        bolsas_base = float(actual["Bolsas producidas"])
        kg_base = float(actual["Kg producidos"])
        precio_base = float(actual["Precio bolsa"])
        vendidas_base = float(actual["Bolsas vendidas"])

        bolsas_sim = float(inp.get("bolsas_producidas", bolsas_base))
        vendidas_sim = float(inp.get("bolsas_vendidas", vendidas_base))
        precio_sim = float(inp.get("precio_bolsa", precio_base))

        kg_sim = bolsas_sim * producto.peso_kg
        ton_sim = kg_sim / 1000
        ratio_produccion = safe_div(kg_sim, kg_base) if kg_base > 0 else 0.0

        mp_base = _sum_indice_token(df_mes, producto.prod_empacado, producto.indices_empacado, "C MP")
        mo_base = _sum_indice_token(df_mes, producto.prod_empacado, producto.indices_empacado, "C MO")
        cif_base = _sum_indice_token(df_mes, producto.prod_empacado, producto.indices_empacado, "C CIF")
        gastos_base = gastos_asignados(df_mes, producto, incluir_renta, incluir_patrimonio)

        mp_sim = mp_base * ratio_produccion
        mo_sim = mo_base if bolsas_sim > 0 else 0.0
        cif_sim = cif_base if bolsas_sim > 0 else 0.0
        gastos_sim = gastos_base if bolsas_sim > 0 else 0.0

        costo_total_sim = mp_sim + mo_sim + cif_sim + gastos_sim
        costo_bolsa_sim = safe_div(costo_total_sim, bolsas_sim)
        costo_kg_sim = safe_div(costo_total_sim, kg_sim)
        costo_vendido_sim = costo_bolsa_sim * vendidas_sim
        venta_sim = precio_sim * vendidas_sim
        utilidad_sim = venta_sim - costo_vendido_sim
        margen_sim = safe_div(utilidad_sim, venta_sim) if venta_sim > 0 else np.nan
        inventario_bolsas = bolsas_sim - vendidas_sim

        rows.append({
            "Producto": producto.corto,
            "Bolsas producidas actuales": bolsas_base,
            "Bolsas producidas simuladas": bolsas_sim,
            "Bolsas vendidas actuales": vendidas_base,
            "Bolsas vendidas simuladas": vendidas_sim,
            "Ton simuladas": ton_sim,
            "Precio bolsa simulado": precio_sim,
            "MP simulada variable": mp_sim,
            "MO fija": mo_sim,
            "CIF fijo": cif_sim,
            "Gastos fijos asignados": gastos_sim,
            "Costo total simulado": costo_total_sim,
            "Costo / bolsa simulado": costo_bolsa_sim,
            "Costo / kg simulado": costo_kg_sim,
            "Venta simulada": venta_sim,
            "Costo vendido simulado": costo_vendido_sim,
            "Utilidad simulada": utilidad_sim,
            "Margen simulado": margen_sim,
            "Inventario bolsas simulado": inventario_bolsas,
            "Utilidad actual recurrente": float(actual["Utilidad recurrente"]),
            "Cambio utilidad vs actual": utilidad_sim - float(actual["Utilidad recurrente"]),
            "Costo / bolsa actual": float(actual["Costo bolsa recurrente"]),
            "Cambio costo / bolsa": costo_bolsa_sim - float(actual["Costo bolsa recurrente"]),
        })

    return pd.DataFrame(rows)


# =============================================================================
# Verificación cruzada App vs Contabilidad por auxiliar
# =============================================================================

AUXILIAR_OBS_RE = re.compile(r"^\s*(\d{6,12})\s*[-–—]\s*(.*)$")


def extraer_auxiliar_desde_observacion(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    m = AUXILIAR_OBS_RE.match(str(value).strip())
    return m.group(1).strip() if m else ""


def extraer_nombre_auxiliar_app(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    m = AUXILIAR_OBS_RE.match(str(value).strip())
    if not m:
        return str(value).strip()
    return " ".join(m.group(2).strip().split())


def join_unicos(values: Iterable[object], max_items: int = 8) -> str:
    vals = []
    for v in values:
        if v is None or pd.isna(v):
            continue
        s = str(v).strip()
        if s and s not in vals:
            vals.append(s)
        if len(vals) >= max_items:
            break
    return " | ".join(vals)


def detalle_auxiliar_app(df_mes: pd.DataFrame) -> pd.DataFrame:
    """Extrae del Consolidado las líneas con código contable al inicio del concepto.

    Regla de control:
    - Incluye líneas cuyo concepto empieza por código auxiliar: "72050506 - SALARIOS".
    - Excluye TOTAL e INFO para evitar doble conteo de subtotales y cantidades físicas.
    """
    d = df_mes.copy()
    d["Auxiliar"] = d["Observacion"].map(extraer_auxiliar_desde_observacion)
    d["NombreAuxApp"] = d["Observacion"].map(extraer_nombre_auxiliar_app)
    d = d[d["Auxiliar"] != ""].copy()
    d = d[~d["Indice_norm"].isin({norm_text("TOTAL"), norm_text("INFO")})].copy()
    return d[["Auxiliar", "NombreAuxApp", "Produccion", "Indice", "Observacion", "Valor"]].copy()


def resumen_auxiliar_app(df_mes: pd.DataFrame) -> pd.DataFrame:
    det = detalle_auxiliar_app(df_mes)
    if det.empty:
        return pd.DataFrame(columns=["Auxiliar", "NombreAuxApp", "ValorApp", "LineasApp", "Producciones", "Indices"])
    return (
        det.groupby("Auxiliar", as_index=False)
        .agg(
            NombreAuxApp=("NombreAuxApp", lambda s: join_unicos(s, 1)),
            ValorApp=("Valor", "sum"),
            LineasApp=("Valor", "size"),
            Producciones=("Produccion", lambda s: join_unicos(s, 6)),
            Indices=("Indice", lambda s: join_unicos(s, 8)),
        )
        .sort_values("ValorApp", ascending=False)
    )


def resumen_auxiliar_contabilidad(cont: pd.DataFrame | None, ano: int, mes: int) -> pd.DataFrame:
    if cont is None or cont.empty:
        return pd.DataFrame(columns=["Auxiliar", "NombreAux", "TotalDebito", "TotalCredito", "Saldo", "NumeroMovimientos", "Clase"])
    d = cont[(cont["Ano"] == ano) & (cont["Mes"] == mes)].copy()
    if d.empty:
        return pd.DataFrame(columns=["Auxiliar", "NombreAux", "TotalDebito", "TotalCredito", "Saldo", "NumeroMovimientos", "Clase"])
    return (
        d.groupby("Auxiliar", as_index=False)
        .agg(
            NombreAux=("NombreAux", lambda s: join_unicos(s, 1)),
            TotalDebito=("TotalDebito", "sum"),
            TotalCredito=("TotalCredito", "sum"),
            Saldo=("Saldo", "sum"),
            NumeroMovimientos=("NumeroMovimientos", "sum"),
        )
        .assign(Clase=lambda x: x["Auxiliar"].astype(str).str[0])
    )


def clasificar_auxiliar_no_modelado(auxiliar: object, nombre: object = "") -> str:
    aux = "" if auxiliar is None or pd.isna(auxiliar) else str(auxiliar).strip()
    nom = norm_text(nombre)
    if aux.startswith(("1", "2", "3")):
        return "Balance / control, no costo"
    if aux.startswith("4"):
        return "Ingreso P&G, no costo app"
    if aux.startswith("61"):
        return "Costo de venta P&G"
    if "CIERRE" in nom or aux.endswith("9901"):
        return "Cierre contable"
    if aux.startswith(("51", "52", "53", "54", "71", "72", "73", "74")):
        return "Gasto/costo sin línea app"
    return "No clasificado"


def conciliar_auxiliares_app_vs_contabilidad(
    df_mes: pd.DataFrame,
    cont: pd.DataFrame | None,
    ano: int,
    mes: int,
    tolerancia: float = 5000.0,
) -> dict:
    app_aux = resumen_auxiliar_app(df_mes)
    cont_aux = resumen_auxiliar_contabilidad(cont, ano, mes)

    if app_aux.empty and cont_aux.empty:
        return {
            "ok": False,
            "error": "No hay líneas con código auxiliar en app ni contabilidad para el periodo.",
            "detalle_app": detalle_auxiliar_app(df_mes),
            "conciliacion": pd.DataFrame(),
            "no_modeladas": pd.DataFrame(),
            "resumen": {},
        }

    df = pd.merge(app_aux, cont_aux, on="Auxiliar", how="outer", indicator=True)
    df["En app"] = df["_merge"].isin(["left_only", "both"])
    df["En contabilidad"] = df["_merge"].isin(["right_only", "both"])

    for col in ["ValorApp", "LineasApp", "TotalDebito", "TotalCredito", "Saldo", "NumeroMovimientos"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    for col in ["NombreAuxApp", "NombreAux", "Producciones", "Indices", "Clase"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    df["Diferencia App - Contabilidad"] = df["ValorApp"] - df["Saldo"]
    df["Diferencia abs"] = df["Diferencia App - Contabilidad"].abs()
    df["% diferencia"] = df.apply(
        lambda r: safe_div(r["Diferencia App - Contabilidad"], abs(r["Saldo"])) if abs(r["Saldo"]) > 0 else np.nan,
        axis=1,
    )
    df["Clasificación"] = df.apply(lambda r: clasificar_auxiliar_no_modelado(r["Auxiliar"], r["NombreAux"]), axis=1)

    def estado(row) -> str:
        if row["En app"] and row["En contabilidad"] and row["Diferencia abs"] <= tolerancia:
            return "OK"
        if row["En app"] and row["En contabilidad"]:
            return "DIFERENCIA"
        if row["En app"] and not row["En contabilidad"]:
            return "SOLO APP"
        if row["En contabilidad"] and not row["En app"]:
            return "SOLO CONTABILIDAD"
        return "SIN DATOS"

    df["Estado"] = df.apply(estado, axis=1)

    # Orden ejecutivo: primero riesgos, después OK.
    orden_estado = {"DIFERENCIA": 0, "SOLO APP": 1, "SOLO CONTABILIDAD": 2, "OK": 3, "SIN DATOS": 9}
    df["_orden"] = df["Estado"].map(orden_estado).fillna(9)
    df = df.sort_values(["_orden", "Diferencia abs"], ascending=[True, False]).drop(columns=["_orden", "_merge"])

    match = df[df["En app"] & df["En contabilidad"]].copy()
    no_modeladas = df[(df["En contabilidad"]) & (~df["En app"])].copy()

    resumen = {
        "Total app con auxiliar": float(app_aux["ValorApp"].sum()) if not app_aux.empty else 0.0,
        "Total contabilidad mismos auxiliares": float(match["Saldo"].sum()) if not match.empty else 0.0,
        "Diferencia auxiliares modelados": float(match["Diferencia App - Contabilidad"].sum()) if not match.empty else 0.0,
        "Auxiliares app": int(app_aux["Auxiliar"].nunique()) if not app_aux.empty else 0,
        "Auxiliares contabilidad": int(cont_aux["Auxiliar"].nunique()) if not cont_aux.empty else 0,
        "Auxiliares OK": int((df["Estado"] == "OK").sum()),
        "Auxiliares con diferencia": int((df["Estado"] == "DIFERENCIA").sum()),
        "Solo app": int((df["Estado"] == "SOLO APP").sum()),
        "Solo contabilidad": int((df["Estado"] == "SOLO CONTABILIDAD").sum()),
        "Total no modelado clases 5/6/7": float(no_modeladas[no_modeladas["Clase"].isin(["5", "6", "7"])]["Saldo"].sum()) if not no_modeladas.empty else 0.0,
    }

    return {
        "ok": True,
        "detalle_app": detalle_auxiliar_app(df_mes),
        "app_aux": app_aux,
        "cont_aux": cont_aux,
        "conciliacion": df,
        "no_modeladas": no_modeladas,
        "resumen": resumen,
    }


# =============================================================================
# P&G contable y conciliación
# =============================================================================


def pyg_summary(cont: pd.DataFrame | None, ano: int, mes: int) -> dict:
    """Resume el P&G contable y valida si el periodo está completo.

    Punto crítico: un mes con ingresos pero sin costo de venta clase 61 ni movimientos
    de costo de producción clase 7 no puede presentarse como "utilidad real". Eso es
    P&G parcial o cierre contable incompleto.
    """
    if cont is None or cont.empty:
        return {"ok": False, "error": "No hay contabilidad cargada."}
    d = cont[(cont["Ano"] == ano) & (cont["Mes"] == mes)].copy()
    if d.empty:
        return {"ok": False, "error": "No hay registros de contabilidad para el periodo seleccionado."}

    saldo_4 = float(d.loc[d["Clase"] == "4", "Saldo"].sum())
    saldo_5 = float(d.loc[d["Clase"] == "5", "Saldo"].sum())
    saldo_6 = float(d.loc[d["Clase"] == "6", "Saldo"].sum())
    saldo_7 = float(d.loc[d["Clase"] == "7", "Saldo"].sum())

    ingresos = -float(d.loc[d["Auxiliar"].str.startswith("41", na=False), "Saldo"].sum())
    costo_venta = float(d.loc[d["Auxiliar"].str.startswith("61", na=False), "Saldo"].sum())
    admin = float(d.loc[d["Auxiliar"].str.startswith("51", na=False), "Saldo"].sum())
    ventas = float(d.loc[d["Auxiliar"].str.startswith("52", na=False), "Saldo"].sum())
    financieros = float(d.loc[d["Auxiliar"].str.startswith("53", na=False), "Saldo"].sum())
    impuestos = float(d.loc[d["Auxiliar"].str.startswith("54", na=False), "Saldo"].sum())
    otros = -float(d.loc[d["Auxiliar"].str.startswith("42", na=False), "Saldo"].sum())

    # Diferencia en cambio: se muestra separada porque puede inflar o castigar la utilidad
    # sin explicar eficiencia operativa.
    nombre_norm = d["NombreAux"].map(norm_text) if "NombreAux" in d.columns else pd.Series("", index=d.index)
    aux = d["Auxiliar"].astype(str)
    mask_fx = aux.str.startswith("421020", na=False) | nombre_norm.str.contains("DIFERENCIA EN CAMBIO", na=False)
    mask_fx_no_realizada = mask_fx & nombre_norm.str.contains("NO REALIZ", na=False)
    mask_fx_realizada = mask_fx & ~mask_fx_no_realizada
    fx_realizada = -float(d.loc[mask_fx_realizada, "Saldo"].sum())
    fx_no_realizada = -float(d.loc[mask_fx_no_realizada, "Saldo"].sum())
    otros_sin_fx = otros - fx_realizada - fx_no_realizada

    # Validación de cierre contable.
    # Clase 7 puede cerrar a cero por contrapartidas; por eso se valida movimiento bruto,
    # no solo saldo neto.
    clase7 = d[d["Clase"] == "7"].copy()
    movimiento_clase7 = float(clase7["TotalDebito"].sum() + clase7["TotalCredito"].sum()) if not clase7.empty else 0.0
    movimiento_clase6 = float(d.loc[d["Clase"] == "6", "TotalDebito"].sum() + d.loc[d["Clase"] == "6", "TotalCredito"].sum())
    tiene_ingresos = ingresos > 0
    tiene_costo_venta = abs(costo_venta) > 1
    tiene_costos_produccion = movimiento_clase7 > 1
    tiene_costos_pyg = tiene_costo_venta or tiene_costos_produccion or movimiento_clase6 > 1

    alertas_pyg = []
    if tiene_ingresos and not tiene_costos_pyg:
        alertas_pyg.append(
            "P&G incompleto: hay ingresos, pero no hay costo de venta clase 61 ni movimientos de costo de producción clase 7 en la contabilidad cargada."
        )
    if tiene_ingresos and safe_div(costo_venta, ingresos) < 0.02 and not tiene_costos_produccion:
        alertas_pyg.append(
            "Margen bruto no confiable: el costo reconocido es cero o marginal frente a los ingresos."
        )
    if abs(fx_realizada) > 1 or abs(fx_no_realizada) > 1:
        alertas_pyg.append(
            f"La utilidad incluye diferencia en cambio: realizada {money(fx_realizada)} y no realizada {money(fx_no_realizada)}."
        )

    pyg_completo = len([a for a in alertas_pyg if a.startswith("P&G incompleto") or a.startswith("Margen bruto no confiable")]) == 0

    utilidad = -saldo_4 - saldo_5 - saldo_6 - saldo_7
    utilidad_bruta = ingresos - costo_venta
    resultado_operativo = utilidad_bruta - admin - ventas
    balance_control = d[d["Clase"].isin(["1", "2", "3"])].copy()
    return {
        "ok": True,
        "P&G completo": bool(pyg_completo),
        "Alertas P&G": alertas_pyg,
        "df": d,
        "Ingresos netos": ingresos,
        "Costo venta": costo_venta,
        "Movimiento clase 6": movimiento_clase6,
        "Movimiento clase 7": movimiento_clase7,
        "Ganancia bruta": utilidad_bruta,
        "Gastos administración": admin,
        "Gastos venta": ventas,
        "Resultado operativo": resultado_operativo,
        "Otros ingresos / financieros clase 42": otros,
        "Diferencia en cambio realizada": fx_realizada,
        "Diferencia en cambio no realizada": fx_no_realizada,
        "Otros ingresos sin diferencia en cambio": otros_sin_fx,
        "Gastos financieros": financieros,
        "Impuestos": impuestos,
        "Utilidad neta": utilidad,
        "Margen bruto": safe_div(utilidad_bruta, ingresos),
        "Margen operativo": safe_div(resultado_operativo, ingresos),
        "Margen neto": safe_div(utilidad, ingresos),
        "Balance control": balance_control,
    }



def app_pyg_bridge(metrics: pd.DataFrame, extras: pd.DataFrame, pyg: dict) -> dict:
    venta_app = float(metrics["Venta"].sum()) if not metrics.empty else 0.0
    costo_vendido = float(metrics["Costo vendido recurrente"].sum()) if not metrics.empty else 0.0
    utilidad_recurrente = venta_app - costo_vendido
    extra_total = float(extras["Valor"].sum()) if extras is not None and not extras.empty else 0.0
    utilidad_con_extra = utilidad_recurrente - extra_total
    if not pyg.get("ok"):
        return {
            "venta_app": venta_app,
            "costo_vendido": costo_vendido,
            "utilidad_recurrente": utilidad_recurrente,
            "extra_total": extra_total,
            "utilidad_con_extra": utilidad_con_extra,
            "ok": False,
        }
    ingreso_pyg = float(pyg["Ingresos netos"])
    utilidad_pyg = float(pyg["Utilidad neta"])
    dif_ingresos = ingreso_pyg - venta_app
    dif_resto = utilidad_pyg - utilidad_con_extra - dif_ingresos
    check = utilidad_con_extra + dif_ingresos + dif_resto - utilidad_pyg
    return {
        "ok": True,
        "venta_app": venta_app,
        "costo_vendido": costo_vendido,
        "utilidad_recurrente": utilidad_recurrente,
        "extra_total": extra_total,
        "utilidad_con_extra": utilidad_con_extra,
        "dif_ingresos": dif_ingresos,
        "dif_resto": dif_resto,
        "utilidad_pyg": utilidad_pyg,
        "check": check,
        "diferencia_pyg_app": utilidad_pyg - utilidad_con_extra,
    }

# =============================================================================
# Histórico y análisis ejecutivo
# =============================================================================


def historico(df_base: pd.DataFrame, incluir_renta: bool, incluir_patrimonio: bool, margen_meta: float) -> pd.DataFrame:
    rows = []
    periods = df_base[["Ano", "MesNro"]].drop_duplicates().sort_values(["Ano", "MesNro"])
    for _, p in periods.iterrows():
        ano = int(p["Ano"])
        mes = int(p["MesNro"])
        d = periodo_df(df_base, ano, mes)
        fis = costeo_fisico(d, incluir_renta, incluir_patrimonio)
        mets = pd.DataFrame([vendible_metrics(d, v, incluir_renta, incluir_patrimonio) for v in VENDIBLES.values()])
        extras = extras_df(d)
        venta = float(mets["Venta"].sum()) if not mets.empty else 0.0
        utilidad = float(mets["Utilidad recurrente"].sum()) if not mets.empty else 0.0
        kg_emp = float(mets["Kg producidos"].sum()) if not mets.empty else 0.0
        ton_emp = kg_emp / 1000
        bolsas_prod = float(mets["Bolsas producidas"].sum()) if not mets.empty else 0.0
        inv_bolsas = float(mets["Bolsas producidas no vendidas"].sum()) if not mets.empty else 0.0
        energia_mask = d["Observacion_norm"].str.contains("ENERG", na=False) | d["Indice_norm"].str.contains("ENERG", na=False) | d["Observacion_norm"].str.contains("ELECT", na=False)
        empaque_mask = d["Observacion_norm"].str.contains("SACO", na=False) | d["Observacion_norm"].str.contains("KRAFT", na=False) | d["Observacion_norm"].str.contains("EMPAQUE", na=False)
        energia = float(d.loc[energia_mask, "Valor"].sum())
        empaque = float(d.loc[empaque_mask, "Valor"].sum())
        def fis_val(prod: str, col: str) -> float:
            x = fis.loc[fis["Producto"] == prod, col]
            return float(x.iloc[0]) if not x.empty and not pd.isna(x.iloc[0]) else np.nan
        rows.append({
            "Periodo": ano * 100 + mes,
            "Periodo etiqueta": f"{MESES_INV.get(mes, mes)[:3]} {ano}",
            "Costo/kg UG granel": fis_val("UG granel", "Costo / kg total"),
            "Costo/kg UG empacado": fis_val("UG empacado 50 kg", "Costo / kg total"),
            "Costo/kg ART granel": fis_val("ART granel", "Costo / kg total"),
            "Costo/kg ART empacado": fis_val("ART empacado 42,5 kg", "Costo / kg total"),
            "Ton UG empacado": fis_val("UG empacado 50 kg", "Ton producidas"),
            "Ton ART empacado": fis_val("ART empacado 42,5 kg", "Ton producidas"),
            "Energía $/ton empacada": safe_div(energia, ton_emp),
            "Empaque $/bolsa": safe_div(empaque, bolsas_prod),
            "Inventario bolsas no vendidas": inv_bolsas,
            "Margen recurrente portafolio": safe_div(utilidad, venta) if venta > 0 else np.nan,
            "Gastos extraordinarios": float(extras["Valor"].sum()) if not extras.empty else 0.0,
        })
    return pd.DataFrame(rows).sort_values("Periodo") if rows else pd.DataFrame()


def microfig(hist: pd.DataFrame, col: str, title: str, money_axis: bool = False) -> go.Figure:
    fig = go.Figure()
    if hist is not None and not hist.empty and col in hist.columns:
        d = hist[["Periodo etiqueta", col]].dropna()
        fig.add_trace(go.Scatter(x=d["Periodo etiqueta"], y=d[col], mode="lines+markers", line=dict(width=2), marker=dict(size=6)))
    fig.update_layout(
        title=title,
        height=230,
        margin=dict(l=28, r=12, t=45, b=34),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1", size=11),
        xaxis=dict(showgrid=False, tickangle=-25),
        yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.18)"),
        showlegend=False,
    )
    return fig


def latest_var(hist: pd.DataFrame, col: str) -> tuple[float | None, float | None, float | None]:
    if hist is None or hist.empty or col not in hist.columns:
        return None, None, None
    d = hist[["Periodo", col]].dropna().sort_values("Periodo")
    if d.empty:
        return None, None, None
    actual = float(d.iloc[-1][col])
    anterior = float(d.iloc[-2][col]) if len(d) > 1 else None
    var = safe_div(actual - anterior, abs(anterior)) if anterior not in [None, 0] else None
    return actual, anterior, var


def confidence(base_ok: bool, pyg_ok: bool, metrics: pd.DataFrame, bridge: dict) -> tuple[float, list[str]]:
    score = 0.0
    warn = []
    if base_ok:
        score += 0.30
    else:
        warn.append("No hay base de costeo cargada.")
    if not metrics.empty and metrics["Bolsas producidas"].sum() > 0:
        score += 0.20
    else:
        warn.append("No se detectó producción empacada en el periodo.")
    if not metrics.empty and metrics["Venta"].sum() > 0:
        score += 0.20
    else:
        warn.append("No se detectaron ventas por unidades en el periodo.")
    if pyg_ok:
        score += 0.20
    else:
        warn.append("No hay P&G contable legible; no puede mostrarse utilidad real oficial.")
    if bridge.get("ok") and abs(float(bridge.get("check", 999))) < 1:
        score += 0.10
    elif pyg_ok:
        warn.append("La conciliación no cerró en cero; revisar mapeo contable.")
    return min(score, 1.0), warn


def executive_ai(metrics: pd.DataFrame, fis: pd.DataFrame, hist: pd.DataFrame, pyg: dict, margen_meta: float, conf: float, warn: list[str]) -> pd.DataFrame:
    rows = []
    # Utilidad real / control de cierre P&G
    if pyg.get("ok") and pyg.get("P&G completo", True):
        net = float(pyg["Utilidad neta"])
        mg = float(pyg["Margen neto"])
        rows.append({
            "Prioridad": "Alta" if mg < 0.05 else "Media",
            "Hallazgo": f"Utilidad real P&G: {money(net)}; margen neto {pct(mg)}.",
            "Impacto": net,
            "Acción": "Separar discusión de utilidad real de la discusión de precio por producto.",
            "Responsable": "Gerencia financiera / Gerencia general",
            "Confianza": conf,
        })
    elif pyg.get("ok") and not pyg.get("P&G completo", True):
        rows.append({
            "Prioridad": "Crítica",
            "Hallazgo": "El P&G del periodo está incompleto: muestra ingresos sin costo de venta ni costos de producción contables.",
            "Impacto": float(pyg.get("Utilidad neta", 0)),
            "Acción": "No usar la utilidad ni el margen neto del P&G hasta cerrar costo de venta/clase 7 o cargar la contabilidad completa.",
            "Responsable": "Contabilidad / CFO",
            "Confianza": 0.95,
        })
    # Precio/costo por producto
    for _, r in metrics.iterrows():
        precio = float(r["Precio bolsa"])
        costo = float(r["Costo bolsa recurrente"])
        objetivo = safe_div(costo, 1 - margen_meta) if margen_meta < 1 else np.nan
        if precio > 0 and precio < costo:
            rows.append({
                "Prioridad": "Crítica",
                "Hallazgo": f"{r['Producto']}: precio/lista bajo costo. Faltan {money(costo - precio)} por bolsa para cubrir costo.",
                "Impacto": costo - precio,
                "Acción": "Bloquear venta o corregir lista antes de despachar.",
                "Responsable": "Comercial / Gerencia general",
                "Confianza": 0.92,
            })
        elif precio > 0 and precio < objetivo:
            rows.append({
                "Prioridad": "Alta",
                "Hallazgo": f"{r['Producto']}: cubre costo, pero no margen meta. Faltan {money(objetivo - precio)} por bolsa.",
                "Impacto": objetivo - precio,
                "Acción": "Defender precio y subir gradualmente donde el mercado lo permita.",
                "Responsable": "Comercial / CFO",
                "Confianza": 0.88,
            })
        if float(r["Bolsas vendidas"]) == 0 and precio > 0:
            rows.append({
                "Prioridad": "Alta",
                "Hallazgo": f"{r['Producto']}: sin ventas; margen real del periodo es N/A, no 0%.",
                "Impacto": 0,
                "Acción": "Validar costo y precio/lista antes de lanzamiento comercial.",
                "Responsable": "Comercial / Costos",
                "Confianza": 0.90,
            })
    # Inventario
    inv = float(metrics["Bolsas producidas no vendidas"].sum()) if not metrics.empty else 0.0
    inv_cost = float(metrics["Costo inventario no vendido"].sum()) if not metrics.empty else 0.0
    if inv > 0:
        rows.append({
            "Prioridad": "Media",
            "Hallazgo": f"Inventario producido no vendido: {num(inv)} bolsas; costo estimado {money(inv_cost)}.",
            "Impacto": inv_cost,
            "Acción": "Revisar programación producción/ventas e inventario inicial/final.",
            "Responsable": "Producción / Comercial",
            "Confianza": 0.84,
        })
    # Tendencias
    if hist is not None and len(hist) >= 2:
        for col, resp in [("Costo/kg UG empacado", "Producción / Costos"), ("Energía $/ton empacada", "Producción / Mantenimiento"), ("Empaque $/bolsa", "Compras")]:
            actual, anterior, var = latest_var(hist, col)
            if var is not None and var > 0.05:
                rows.append({
                    "Prioridad": "Alta",
                    "Hallazgo": f"{col} sube {pct(var)} vs mes anterior.",
                    "Impacto": actual - anterior,
                    "Acción": "Explicar variación: precio, consumo, volumen, reclasificación o error de captura.",
                    "Responsable": resp,
                    "Confianza": 0.80,
                })
    for w in warn:
        rows.append({
            "Prioridad": "Control",
            "Hallazgo": w,
            "Impacto": 0,
            "Acción": "Corregir validación antes de comité.",
            "Responsable": "Costos / Sistemas",
            "Confianza": 0.75,
        })
    if not rows:
        rows.append({"Prioridad": "OK", "Hallazgo": "Sin alertas críticas con los datos cargados.", "Impacto": 0, "Acción": "Mantener disciplina de cierre y validación mensual.", "Responsable": "CFO", "Confianza": conf})
    out = pd.DataFrame(rows)
    order = {"Crítica": 0, "Alta": 1, "Media": 2, "Control": 3, "OK": 4}
    return out.assign(_ord=out["Prioridad"].map(order).fillna(9)).sort_values(["_ord", "Impacto"], ascending=[True, False]).drop(columns=["_ord"])

# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    st.markdown("### Archivos")
    base_file = st.file_uploader("Base de costeo · Excel app", type=["xlsx", "xlsm"], key="base")
    cont_file = st.file_uploader("Contabilidad / P&G oficial", type=["xlsx", "xlsm"], key="cont")
    st.markdown("### Periodo")
    ano = st.number_input("Año", min_value=2020, max_value=2035, value=2026, step=1)
    mes_nombre = st.selectbox("Mes", list(MESES.keys()), index=4)
    mes = MESES[mes_nombre]
    st.markdown("### Gobierno del costo")
    margen_meta = st.number_input("Margen meta comercial", min_value=0.0, max_value=0.80, value=0.12, step=0.01, format="%.2f")
    incluir_renta = st.checkbox("Incluir impuesto de renta en costo comercial", value=False)
    incluir_patrimonio = st.checkbox("Incluir impuesto al patrimonio en costo comercial", value=False)

st.markdown('<div class="main-title">Kolcem · Utilidad Real y Costeo por Producto</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Primero utilidad real de la empresa; después costeo por kg, precio defendible, conciliación y alertas. Sin ruido visual.</div>', unsafe_allow_html=True)

if not base_file:
    st.info("Carga la base de costeo para iniciar.")
    st.stop()

try:
    df_base = load_base(base_file.getvalue())
except Exception as e:
    st.error(f"La base de costeo no pudo leerse: {e}")
    st.stop()

df_mes = periodo_df(df_base, int(ano), int(mes))
if df_mes.empty:
    st.error("No hay datos de costeo para el periodo seleccionado.")
    st.stop()

cont = None
pyg = {"ok": False, "error": "No hay contabilidad cargada."}
if cont_file:
    try:
        cont = load_contabilidad(cont_file.getvalue())
        pyg = pyg_summary(cont, int(ano), int(mes))
    except Exception as e:
        pyg = {"ok": False, "error": str(e)}

metrics = pd.DataFrame([vendible_metrics(df_mes, p, incluir_renta, incluir_patrimonio) for p in VENDIBLES.values()])
fis = costeo_fisico(df_mes, incluir_renta, incluir_patrimonio)
extras = extras_df(df_mes)
bridge = app_pyg_bridge(metrics, extras, pyg)
hist = historico(df_base, incluir_renta, incluir_patrimonio, margen_meta)
pyg_confiable = bool(pyg.get("ok") and pyg.get("P&G completo", True))
conf, warnings = confidence(True, pyg_confiable, metrics, bridge)
ai_df = executive_ai(metrics, fis, hist, pyg, margen_meta, conf, warnings)

# =============================================================================
# Navegación principal
# =============================================================================

tabs = st.tabs([
    "1 · Utilidad real",
    "2 · Costeo por kg",
    "3 · Precio defendible",
    "4 · Simulación",
    "5 · Conciliación contable",
    "6 · Microtendencias",
    "7 · IA ejecutiva",
])

# =============================================================================
# 1 · Utilidad real
# =============================================================================

with tabs[0]:
    section("Respuesta clara")
    pyg_completo = bool(pyg.get("ok") and pyg.get("P&G completo", True))

    if pyg.get("ok") and pyg_completo:
        st.markdown(
            f"<div class='executive-strip'><b>Utilidad real de la empresa:</b> {money(pyg['Utilidad neta'])} en {mes_nombre} {ano}. "
            f"<b>Margen neto:</b> {pct(pyg['Margen neto'])}. Esta cifra viene del P&G oficial, no del costeo.</div>",
            unsafe_allow_html=True,
        )
    elif pyg.get("ok") and not pyg_completo:
        st.markdown(
            f"<div class='executive-strip'><b>P&G contable incompleto para {mes_nombre} {ano}:</b> "
            "no se debe presentar como utilidad real. Hay ingresos, pero el archivo de contabilidad no trae costo de venta clase 61 "
            "ni movimientos de costos de producción clase 7. El margen de 100%+ es una señal de cierre contable incompleto, no una victoria operativa.</div>",
            unsafe_allow_html=True,
        )
        for alerta in pyg.get("Alertas P&G", []):
            st.warning(alerta)
    else:
        st.markdown(
            f"<div class='executive-strip'><b>No puedo mostrar utilidad real oficial:</b> {pyg.get('error', 'falta contabilidad')}. "
            "La app seguirá mostrando costeo gerencial, pero eso no es utilidad real de empresa.</div>",
            unsafe_allow_html=True,
        )

    c1, c2, c3, c4, c5 = st.columns(5)
    if pyg.get("ok") and pyg_completo:
        with c1:
            card("Utilidad real", money(pyg["Utilidad neta"]), "P&G oficial", "good" if pyg["Utilidad neta"] >= 0 else "bad")
        with c2:
            card("Margen neto", pct(pyg["Margen neto"]), "Utilidad / ingresos", "good" if pyg["Margen neto"] >= 0.05 else "warn" if pyg["Margen neto"] >= 0 else "bad")
        with c3:
            card("Ingresos netos", money(pyg["Ingresos netos"]), "Ventas contables", "blue")
        with c4:
            card("Ganancia bruta", money(pyg["Ganancia bruta"]), f"Margen {pct(pyg['Margen bruto'])}", "good" if pyg["Ganancia bruta"] >= 0 else "bad")
        with c5:
            card("Resultado operativo", money(pyg["Resultado operativo"]), f"Margen {pct(pyg['Margen operativo'])}", "good" if pyg["Resultado operativo"] >= 0 else "bad")
    elif pyg.get("ok") and not pyg_completo:
        with c1:
            card("Resultado parcial", money(pyg["Utilidad neta"]), "No usar como utilidad real", "bad")
        with c2:
            card("Margen neto", "N/A", "P&G incompleto", "bad")
        with c3:
            card("Ingresos netos", money(pyg["Ingresos netos"]), "Sí cargados", "blue")
        with c4:
            card("Costo venta clase 61", money(pyg["Costo venta"]), "Ausente o incompleto", "bad")
        with c5:
            card("Movimiento clase 7", money(pyg.get("Movimiento clase 7", 0)), "Costo producción", "bad")
    else:
        with c1:
            card("Utilidad real", "N/A", "Cargue P&G", "warn")
        with c2:
            card("Confianza", pct(conf), "Limitada sin P&G", "warn")
        with c3:
            card("Costeo recurrente", money(bridge["utilidad_recurrente"]), "No es P&G", "blue")
        with c4:
            card("Extraordinarios", money(bridge["extra_total"]), "Según base app", "warn")
        with c5:
            card("Costeo con extra", money(bridge["utilidad_con_extra"]), "Gerencial", "blue")

    section("Estado de resultados ejecutivo")
    if pyg.get("ok"):
        linea_final = "UTILIDAD REAL DE LA EMPRESA" if pyg_completo else "RESULTADO CONTABLE PARCIAL - NO USAR COMO UTILIDAD REAL"
        pyg_table = pd.DataFrame([
            {"Línea": "Ingresos netos", "Valor": pyg["Ingresos netos"], "Lectura": "Venta real contable después de devoluciones/ajustes"},
            {"Línea": "Costo de venta clase 61", "Valor": -pyg["Costo venta"], "Lectura": "Costo reconocido oficialmente en P&G; si es $0 con ingresos, el cierre está incompleto"},
            {"Línea": "Movimiento bruto clase 7", "Valor": pyg.get("Movimiento clase 7", 0), "Lectura": "Control de costos de producción; puede cerrar a cero en saldo, pero no debería tener movimiento cero si hubo producción/costo"},
            {"Línea": "Ganancia bruta", "Valor": pyg["Ganancia bruta"], "Lectura": "Resultado antes de gastos; no confiable si falta costo"},
            {"Línea": "Gastos administración", "Valor": -pyg["Gastos administración"], "Lectura": "Estructura administrativa"},
            {"Línea": "Gastos venta", "Valor": -pyg["Gastos venta"], "Lectura": "Comercial, distribución y logística"},
            {"Línea": "Resultado operativo", "Valor": pyg["Resultado operativo"], "Lectura": "Antes de financieros, otros e impuestos"},
            {"Línea": "Otros ingresos / financieros clase 42", "Valor": pyg["Otros ingresos / financieros clase 42"], "Lectura": "Partidas no operativas positivas"},
            {"Línea": "Diferencia en cambio realizada", "Valor": pyg.get("Diferencia en cambio realizada", 0), "Lectura": "Debe verse separada de la eficiencia operativa"},
            {"Línea": "Diferencia en cambio no realizada", "Valor": pyg.get("Diferencia en cambio no realizada", 0), "Lectura": "Puede inflar utilidad contable sin caja"},
            {"Línea": "Otros ingresos sin diferencia en cambio", "Valor": pyg.get("Otros ingresos sin diferencia en cambio", 0), "Lectura": "Clase 42 depurada de diferencia en cambio"},
            {"Línea": "Gastos financieros", "Valor": -pyg["Gastos financieros"], "Lectura": "Intereses y gastos financieros"},
            {"Línea": "Impuestos", "Valor": -pyg["Impuestos"], "Lectura": "Impuesto reconocido"},
            {"Línea": linea_final, "Valor": pyg["Utilidad neta"], "Lectura": "Resultado neto oficial solo si el P&G está completo"},
        ])
        st.dataframe(fmt_df(pyg_table), use_container_width=True, hide_index=True)
    else:
        st.warning(pyg.get("error", "No hay P&G legible."))

    section("Advertencias clave")
    advertencias = []
    if pyg.get("ok"):
        advertencias.extend(pyg.get("Alertas P&G", []))
    advertencias.extend(warnings)
    st.dataframe(pd.DataFrame({"Advertencia": advertencias if advertencias else ["Datos suficientes para lectura ejecutiva."]}), use_container_width=True, hide_index=True)

# =============================================================================
# 2 · Costeo por kg
# =============================================================================

with tabs[1]:
    section("Costeo físico de todos los productos")
    st.markdown("<div class='small-note'>Esta pantalla no muestra ingresos, ventas ni utilidad. Primero costo/kg; luego toneladas, bolsas y componentes. Incluye granel y empacado.</div>", unsafe_allow_html=True)
    show = [
        "Producto", "Tipo", "Costo / kg total", "Costo / ton total", "Costo / bolsa",
        "Kg producidos", "Ton producidas", "Bolsas producidas", "Presentación kg",
        "Costo industrial / kg", "Gastos / kg", "Costo industrial", "Gastos asignados", "Costo total costeo",
    ]
    st.dataframe(fmt_df(fis[show]), use_container_width=True, hide_index=True)

    section("Lectura rápida")
    cols = st.columns(4)
    for i, (_, r) in enumerate(fis.iterrows()):
        with cols[i % 4]:
            extra = f"{num(r['Ton producidas'], 2)} t"
            if r["Tipo"] == "Empacado":
                extra += f" · {num(r['Bolsas producidas'], 0)} bolsas"
            card(r["Producto"], money(r["Costo / kg total"], 2), extra, "neutral")

    section("Detalle auditable")
    for _, r in fis.iterrows():
        with st.expander(f"{r['Producto']} · {money(r['Costo / kg total'], 2)}/kg", expanded=False):
            cc1, cc2, cc3, cc4 = st.columns(4)
            with cc1:
                card("Costo total/kg", money(r["Costo / kg total"], 2), "KPI principal", "blue")
            with cc2:
                card("Kg producidos", num(r["Kg producidos"], 0), f"{num(r['Ton producidas'], 2)} t", "neutral")
            with cc3:
                card("Costo industrial", money(r["Costo industrial"]), money(r["Costo industrial / kg"], 2) + "/kg", "neutral")
            with cc4:
                card("Gastos asignados", money(r["Gastos asignados"]), money(r["Gastos / kg"], 2) + "/kg", "neutral")
            idx = {norm_text(x.strip()) for x in str(r["Índices"]).split("|") if x.strip()}
            det = df_mes[(df_mes["Produccion_norm"] == norm_text(r["Base contable"])) & (df_mes["Indice_norm"].isin(idx))].copy()
            if not det.empty:
                det = det.groupby(["Indice", "Observacion"], as_index=False)["Valor"].sum().sort_values("Valor", ascending=False)
                det["$/kg"] = det["Valor"].apply(lambda x: safe_div(x, r["Kg producidos"]))
                st.dataframe(fmt_df(det), use_container_width=True, hide_index=True)
            else:
                st.info("No hay detalle de costo industrial para este producto.")

# =============================================================================
# 3 · Precio defendible
# =============================================================================

with tabs[2]:
    section("Precio mínimo, objetivo y precio real defendible")
    price_rows = []
    for _, r in metrics.iterrows():
        precio = float(r["Precio bolsa"])
        costo = float(r["Costo bolsa recurrente"])
        objetivo = safe_div(costo, 1 - margen_meta) if margen_meta < 1 else np.nan
        colch = max(precio - costo, 0) if precio > 0 else 0
        falt_costo = max(costo - precio, 0) if precio > 0 else costo
        falt_meta = max(objetivo - precio, 0) if precio > 0 and not pd.isna(objetivo) else objetivo
        exced_meta = max(precio - objetivo, 0) if precio > 0 and not pd.isna(objetivo) else 0
        if precio <= 0:
            estado = "Sin precio/lista"
            accion = "Cargar precio antes de vender"
        elif precio < costo:
            estado = "Precio bajo costo"
            accion = "No vender / corregir lista"
        elif precio < objetivo:
            estado = "Cubre costo, no meta"
            accion = "Subir o defender"
        else:
            estado = "Cumple meta"
            accion = "Mantener / crecer volumen"
        margen_real = r["Margen recurrente"] if r["Venta"] > 0 else np.nan
        price_rows.append({
            "Producto": r["Producto"],
            "Bolsas vendidas": r["Bolsas vendidas"],
            "Precio actual/lista": precio,
            "Costo recurrente / bolsa": costo,
            "Precio mínimo": costo,
            "Precio objetivo": objetivo,
            "Colchón sobre costo": colch,
            "Faltante cubrir costo": falt_costo,
            "Faltante a meta": falt_meta,
            "Excedente sobre meta": exced_meta,
            "Margen real": margen_real,
            "Margen teórico": r["Margen teórico"],
            "Estado": estado,
            "Acción": accion,
        })
    price_df = pd.DataFrame(price_rows)
    st.dataframe(fmt_df(price_df), use_container_width=True, hide_index=True)

    alerts = price_df[price_df["Estado"].isin(["Precio bajo costo", "Sin precio/lista", "Cubre costo, no meta"])]
    if not alerts.empty:
        st.warning("Alertas de precio: " + " · ".join([f"{x['Producto']}: {x['Estado']}" for _, x in alerts.iterrows()]))
    else:
        st.success("Todos los productos con precio cumplen el objetivo de margen.")

    section("Precio vs costo y objetivo")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=price_df["Producto"], y=price_df["Precio actual/lista"], name="Precio actual/lista"))
    fig.add_trace(go.Bar(x=price_df["Producto"], y=price_df["Costo recurrente / bolsa"], name="Costo recurrente"))
    fig.add_trace(go.Bar(x=price_df["Producto"], y=price_df["Precio objetivo"], name="Precio objetivo"))
    fig.update_layout(height=330, barmode="group", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1"), margin=dict(l=40, r=20, t=35, b=50))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
<div class='executive-strip'><b>Regla:</b> precio mínimo = costo recurrente por bolsa. Precio objetivo = costo / (1 - margen meta). Si no hubo ventas, el margen real es N/A; se evalúa el precio/lista contra el costo.</div>
""", unsafe_allow_html=True)


# =============================================================================
# 4 · Simulación
# =============================================================================

with tabs[3]:
    section("Simulación simple de producción, costo y utilidad")
    st.markdown(
        "<div class='small-note'>La simulación recalcula el costo con nuevas cantidades producidas. "
        "Regla base: materia prima variable con producción; mano de obra, CIF y gastos asignados quedan fijos. "
        "Esto muestra el apalancamiento operativo: más volumen debe diluir estructura, no castigarla.</div>",
        unsafe_allow_html=True,
    )

    sim_inputs = {}
    for producto in VENDIBLES.values():
        actual = vendible_metrics(df_mes, producto, incluir_renta, incluir_patrimonio)
        with st.expander(f"{producto.corto} · parámetros", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                bolsas_prod = st.number_input(
                    f"Bolsas producidas simuladas · {producto.corto}",
                    min_value=0.0,
                    value=float(actual["Bolsas producidas"]),
                    step=100.0,
                    format="%.0f",
                    key=f"sim_prod_{producto.key}",
                )
            with c2:
                bolsas_vend = st.number_input(
                    f"Bolsas vendidas simuladas · {producto.corto}",
                    min_value=0.0,
                    value=float(actual["Bolsas vendidas"]),
                    step=100.0,
                    format="%.0f",
                    key=f"sim_vend_{producto.key}",
                )
            with c3:
                precio = st.number_input(
                    f"Precio bolsa simulado · {producto.corto}",
                    min_value=0.0,
                    value=float(actual["Precio bolsa"]),
                    step=100.0,
                    format="%.0f",
                    key=f"sim_precio_{producto.key}",
                )
            sim_inputs[producto.key] = {
                "bolsas_producidas": bolsas_prod,
                "bolsas_vendidas": bolsas_vend,
                "precio_bolsa": precio,
            }

    sim = simular_productos_vendibles(df_mes, sim_inputs, incluir_renta, incluir_patrimonio)
    aplicar_extra_sim = st.checkbox("Restar extraordinarios actuales a la utilidad simulada", value=False)
    extra_sim = float(extras["Valor"].sum()) if aplicar_extra_sim and extras is not None and not extras.empty else 0.0

    venta_total_sim = float(sim["Venta simulada"].sum()) if not sim.empty else 0.0
    costo_vendido_total_sim = float(sim["Costo vendido simulado"].sum()) if not sim.empty else 0.0
    utilidad_recurrente_sim = float(sim["Utilidad simulada"].sum()) if not sim.empty else 0.0
    utilidad_final_sim = utilidad_recurrente_sim - extra_sim
    margen_final_sim = safe_div(utilidad_final_sim, venta_total_sim) if venta_total_sim > 0 else np.nan
    cambio_utilidad = utilidad_final_sim - float(bridge["utilidad_recurrente"])

    s1, s2, s3, s4, s5 = st.columns(5)
    with s1:
        card("Venta simulada", money(venta_total_sim), "Precio x bolsas vendidas", "blue")
    with s2:
        card("Costo vendido simulado", money(costo_vendido_total_sim), "Costo recalculado x ventas", "blue")
    with s3:
        card("Utilidad simulada", money(utilidad_final_sim), "Después de extraordinarios si aplica", "good" if utilidad_final_sim >= 0 else "bad")
    with s4:
        card("Margen simulado", pct(margen_final_sim), "Utilidad / venta", "good" if margen_final_sim >= margen_meta else "warn")
    with s5:
        card("Cambio vs actual", money(cambio_utilidad), "Contra costeo recurrente actual", "good" if cambio_utilidad >= 0 else "warn")

    section("Resultado por producto")
    cols_sim = [
        "Producto", "Bolsas producidas actuales", "Bolsas producidas simuladas",
        "Bolsas vendidas actuales", "Bolsas vendidas simuladas", "Precio bolsa simulado",
        "Costo / bolsa actual", "Costo / bolsa simulado", "Cambio costo / bolsa",
        "Costo / kg simulado", "Venta simulada", "Costo vendido simulado",
        "Utilidad simulada", "Margen simulado", "Inventario bolsas simulado", "Cambio utilidad vs actual",
    ]
    st.dataframe(fmt_df(sim[cols_sim]), use_container_width=True, hide_index=True)

    section("Componentes del costo simulado")
    cols_comp = [
        "Producto", "MP simulada variable", "MO fija", "CIF fijo", "Gastos fijos asignados", "Costo total simulado"
    ]
    st.dataframe(fmt_df(sim[cols_comp]), use_container_width=True, hide_index=True)

    if (sim["Inventario bolsas simulado"] < 0).any():
        st.warning("Hay productos con ventas simuladas mayores que producción simulada. Puede ser válido si vendes inventario inicial; si no, estás simulando ventas fantasma.")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=sim["Producto"], y=sim["Utilidad actual recurrente"], name="Utilidad actual recurrente"))
    fig.add_trace(go.Bar(x=sim["Producto"], y=sim["Utilidad simulada"], name="Utilidad simulada"))
    fig.update_layout(
        height=330,
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1"),
        margin=dict(l=40, r=20, t=35, b=50),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown(
        "<div class='executive-strip'><b>Lectura:</b> esta simulación no reemplaza el P&G. Sirve para decidir volumen, precio y apalancamiento de costos. "
        "Si quieres que energía u otro CIF se comporte como variable, debe parametrizarse explícitamente; asumirlo todo variable es una forma elegante de destruir el análisis.</div>",
        unsafe_allow_html=True,
    )

# =============================================================================
# 5 · Conciliación contable
# =============================================================================

with tabs[4]:
    section("Sistema cruzado de verificación: App vs Contabilidad")
    st.markdown(
        "<div class='small-note'>La app toma las líneas del Consolidado cuyo concepto empieza con código contable "
        "—por ejemplo <b>72050506 - SALARIOS</b>—, las suma por auxiliar y las cruza contra la contabilidad cargada. "
        "Se excluyen TOTAL e INFO para no duplicar subtotales ni cantidades físicas.</div>",
        unsafe_allow_html=True,
    )

    tolerancia_conciliacion = st.number_input(
        "Tolerancia por auxiliar",
        min_value=0.0,
        max_value=1000000.0,
        value=5000.0,
        step=1000.0,
        help="Diferencias menores o iguales a esta tolerancia quedan como OK. Sirve para redondeos de distribución.",
    )

    conciliacion_aux = conciliar_auxiliares_app_vs_contabilidad(
        df_mes=df_mes,
        cont=cont,
        ano=int(ano),
        mes=int(mes),
        tolerancia=float(tolerancia_conciliacion),
    )

    if not conciliacion_aux.get("ok"):
        st.warning(conciliacion_aux.get("error", "No fue posible cruzar app contra contabilidad."))
    else:
        res = conciliacion_aux["resumen"]
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            card("App modelada", money(res["Total app con auxiliar"]), f"{res['Auxiliares app']} auxiliares", "blue")
        with m2:
            card("Contabilidad mismos auxiliares", money(res["Total contabilidad mismos auxiliares"]), "Solo códigos presentes en app", "blue")
        with m3:
            dif_modelada = res["Diferencia auxiliares modelados"]
            card("Diferencia modelada", money(dif_modelada), "App - contabilidad", "good" if abs(dif_modelada) <= float(tolerancia_conciliacion) else "warn")
        with m4:
            card("Auxiliares OK", str(res["Auxiliares OK"]), f"Diferencias <= {money(tolerancia_conciliacion)}", "good")
        with m5:
            problemas = res["Auxiliares con diferencia"] + res["Solo app"]
            card("Alertas reales", str(problemas), "Diferencia o solo app", "warn" if problemas else "good")

        conc = conciliacion_aux["conciliacion"].copy()
        estado_sel = st.multiselect(
            "Filtrar estado",
            ["DIFERENCIA", "SOLO APP", "SOLO CONTABILIDAD", "OK"],
            default=["DIFERENCIA", "SOLO APP", "OK"],
        )
        conc_view = conc[conc["Estado"].isin(estado_sel)].copy() if estado_sel else conc.copy()

        cols_conc = [
            "Estado", "Auxiliar", "NombreAux", "NombreAuxApp",
            "ValorApp", "Saldo", "Diferencia App - Contabilidad", "% diferencia",
            "TotalDebito", "TotalCredito", "LineasApp", "Producciones", "Indices", "Clasificación",
        ]
        cols_conc = [c for c in cols_conc if c in conc_view.columns]
        st.dataframe(fmt_df(conc_view[cols_conc]), use_container_width=True, hide_index=True)

        csv_conc = conc.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Descargar conciliación auxiliar CSV",
            data=csv_conc,
            file_name=f"conciliacion_auxiliar_{ano}_{mes:02d}.csv",
            mime="text/csv",
        )

        section("Cuentas contables no modeladas directamente por la app")
        st.markdown(
            "<div class='small-note'>Estas partidas existen en contabilidad, pero no aparecen como línea auxiliar en el Consolidado de la app. "
            "No todas son errores: aquí normalmente aparecen cuentas de cierre, costo de venta P&G, ingresos y cuentas de balance. "
            "El riesgo está en gastos/costos operativos sin línea app.</div>",
            unsafe_allow_html=True,
        )
        no_modeladas = conciliacion_aux["no_modeladas"].copy()
        if not no_modeladas.empty:
            clase_sel = st.multiselect(
                "Filtrar clases contables no modeladas",
                sorted([x for x in no_modeladas["Clase"].dropna().unique().tolist() if x != ""]),
                default=[x for x in ["5", "6", "7"] if x in no_modeladas["Clase"].dropna().unique().tolist()],
            )
            no_model_view = no_modeladas[no_modeladas["Clase"].isin(clase_sel)].copy() if clase_sel else no_modeladas.copy()
            cols_nm = ["Auxiliar", "NombreAux", "Saldo", "TotalDebito", "TotalCredito", "NumeroMovimientos", "Clase", "Clasificación"]
            st.dataframe(fmt_df(no_model_view[cols_nm].sort_values("Saldo", key=lambda s: s.abs(), ascending=False)), use_container_width=True, hide_index=True)
        else:
            st.success("No hay cuentas contables por fuera del modelo para el periodo.")

        with st.expander("Detalle de líneas de la app usadas en el cruce", expanded=False):
            det = conciliacion_aux["detalle_app"].copy()
            st.dataframe(fmt_df(det.sort_values(["Auxiliar", "Produccion", "Indice"])), use_container_width=True, hide_index=True)

    section("Puente gerencial: Costeo app vs P&G oficial")
    if not pyg.get("ok"):
        st.warning("Carga una contabilidad legible para activar el puente oficial de P&G.")
    elif not pyg.get("P&G completo", True):
        st.error("El puente se muestra solo como diagnóstico: el P&G cargado está incompleto y no debe usarse como utilidad real.")

    b1, b2, b3, b4 = st.columns(4)
    with b1:
        card("Costeo recurrente", money(bridge["utilidad_recurrente"]), "Venta - costo vendido", "blue")
    with b2:
        card("Costeo con extra", money(bridge["utilidad_con_extra"]), "No es utilidad neta", "warn")
    with b3:
        if bridge.get("ok"):
            etiqueta_pyg = "Utilidad neta P&G" if pyg.get("P&G completo", True) else "Resultado P&G parcial"
            ayuda_pyg = "Resultado oficial" if pyg.get("P&G completo", True) else "No usar como utilidad real"
            color_pyg = "good" if pyg.get("P&G completo", True) and bridge["utilidad_pyg"] >= 0 else "bad" if not pyg.get("P&G completo", True) else "bad"
            card(etiqueta_pyg, money(bridge["utilidad_pyg"]), ayuda_pyg, color_pyg)
        else:
            card("Utilidad neta P&G", "N/A", "Falta P&G", "warn")
    with b4:
        card("Check puente", money(bridge.get("check", 0)), "Debe ser $0", "good" if bridge.get("ok") and abs(bridge.get("check", 999)) < 1 else "warn")

    if bridge.get("ok"):
        puente = pd.DataFrame([
            {"Paso": "Utilidad costeo gerencial con extraordinarios", "Impacto": bridge["utilidad_con_extra"], "Lectura": "Resultado del modelo de costeo"},
            {"Paso": "Diferencia ingresos P&G vs app", "Impacto": bridge["dif_ingresos"], "Lectura": "Ventas, devoluciones, redondeos o partidas no capturadas por unidades"},
            {"Paso": "Diferencia neta costos/gastos/financieros/impuestos", "Impacto": bridge["dif_resto"], "Lectura": "P&G completo menos lo ya cargado por la app; si el P&G está incompleto, esta línea es diagnóstico, no conciliación final"},
            {"Paso": "Utilidad neta contable conciliada", "Impacto": bridge["utilidad_pyg"], "Lectura": "Debe igualar P&G"},
        ])
        st.dataframe(fmt_df(puente), use_container_width=True, hide_index=True)

        section("P&G agrupado")
        pyg_group = pd.DataFrame([
            {"Concepto": "Ingresos netos", "Valor": pyg["Ingresos netos"]},
            {"Concepto": "Costo de venta", "Valor": -pyg["Costo venta"]},
            {"Concepto": "Gastos administración", "Valor": -pyg["Gastos administración"]},
            {"Concepto": "Gastos venta", "Valor": -pyg["Gastos venta"]},
            {"Concepto": "Gastos financieros", "Valor": -pyg["Gastos financieros"]},
            {"Concepto": "Impuestos", "Valor": -pyg["Impuestos"]},
            {"Concepto": "Otros ingresos / financieros clase 42", "Valor": pyg["Otros ingresos / financieros clase 42"]},
            {"Concepto": "Utilidad neta", "Valor": pyg["Utilidad neta"]},
        ])
        st.dataframe(fmt_df(pyg_group), use_container_width=True, hide_index=True)

        section("Control de cuentas de balance")
        balance = pyg.get("Balance control", pd.DataFrame()).copy()
        if not balance.empty:
            st.markdown("<div class='small-note'>Cuentas clase 1, 2 y 3 son control; no deben entrar como gasto de costeo ni P&G. La provisión 26050501 debe quedarse aquí como pasivo, no como gasto duplicado.</div>", unsafe_allow_html=True)
            bal_show = balance[balance["Auxiliar"].str.startswith(("2605", "13", "14", "22", "23", "24"), na=False)][["Auxiliar", "NombreAux", "TotalDebito", "TotalCredito", "Saldo"]].sort_values("Saldo", key=lambda s: s.abs(), ascending=False).head(20)
            st.dataframe(fmt_df(bal_show), use_container_width=True, hide_index=True)

    section("Extraordinarios en la base de costeo")
    st.dataframe(fmt_df(extras), use_container_width=True, hide_index=True)

# =============================================================================
# 6 · Microtendencias
# =============================================================================

with tabs[5]:
    section("Microtendencias accionables")
    if hist.empty or len(hist) < 2:
        st.info("Se requiere más de un mes en Consolidado para leer tendencia. Se muestran los datos disponibles.")
    kcols = ["Costo/kg UG granel", "Costo/kg UG empacado", "Energía $/ton empacada", "Empaque $/bolsa", "Inventario bolsas no vendidas", "Margen recurrente portafolio"]
    st.dataframe(fmt_df(hist[["Periodo etiqueta"] + [c for c in kcols if c in hist.columns]]), use_container_width=True, hide_index=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(microfig(hist, "Costo/kg UG granel", "Costo/kg UG granel"), use_container_width=True)
        st.plotly_chart(microfig(hist, "Energía $/ton empacada", "Energía $/ton empacada"), use_container_width=True)
        st.plotly_chart(microfig(hist, "Inventario bolsas no vendidas", "Bolsas producidas no vendidas"), use_container_width=True)
    with c2:
        st.plotly_chart(microfig(hist, "Costo/kg UG empacado", "Costo/kg UG empacado"), use_container_width=True)
        st.plotly_chart(microfig(hist, "Empaque $/bolsa", "Empaque $/bolsa"), use_container_width=True)
        st.plotly_chart(microfig(hist, "Margen recurrente portafolio", "Margen recurrente portafolio"), use_container_width=True)

# =============================================================================
# 7 · IA ejecutiva
# =============================================================================

with tabs[6]:
    section("Respuesta clara")
    first = ai_df.iloc[0]
    st.markdown(f"<div class='executive-strip'><b>{first['Prioridad']}:</b> {first['Hallazgo']} <b>Acción:</b> {first['Acción']}</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        card("Nivel de confianza", pct(conf), "Calculado por calidad de datos y cierre P&G", "good" if conf >= 0.80 else "warn")
    with c2:
        card("Alertas ejecutivas", str(len(ai_df[ai_df["Prioridad"].isin(["Crítica", "Alta"])])), "Críticas/altas", "warn" if len(ai_df[ai_df["Prioridad"].isin(["Crítica", "Alta"])]) else "good")
    with c3:
        card("Advertencias datos", str(len(warnings)), "Antes del comité", "warn" if warnings else "good")

    section("Hallazgos, responsables y acciones")
    st.dataframe(fmt_df(ai_df), use_container_width=True, hide_index=True)

    section("Prompt de comité")
    prompt = f"""Actúa como CEO/CFO y miembro de junta de una empresa cementera.
Periodo: {mes_nombre} {ano}.
Utilidad real P&G: {money(pyg.get('Utilidad neta', np.nan)) if pyg.get('ok') and pyg.get('P&G completo', True) else 'N/A - P&G incompleto o no cargado'}.
Margen neto P&G: {pct(pyg.get('Margen neto', np.nan)) if pyg.get('ok') and pyg.get('P&G completo', True) else 'N/A'}.
Costeo recurrente app: {money(bridge['utilidad_recurrente'])}.
Costeo con extraordinarios app: {money(bridge['utilidad_con_extra'])}.
Confianza datos: {pct(conf)}.

Hallazgos prioritarios:
{ai_df.head(8).to_string(index=False)}

Entrega: decisión recomendada, riesgos, responsables, acciones de 7 días y datos que faltan validar."""
    st.text_area("Copiar para análisis adicional", prompt, height=260)

