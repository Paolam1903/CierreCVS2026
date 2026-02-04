import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import sqlite3
from PIL import Image
import matplotlib.pyplot as plt

# =============================
# CONFIG
# =============================
st.set_page_config("Dashboard Comercial CVS 2026", layout="wide")

CLAVE_DIRECTOR = "Director2026!"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "comisiones.db"
LOGO_PATH = BASE_DIR / "logo.png"

RUTA_LIQ = DATA_DIR / "liquidacion_final.xlsx"
RUTA_METAS = DATA_DIR / "metas.xlsx"

# =============================
# VALIDACIÓN
# =============================
if not RUTA_LIQ.exists() or not RUTA_METAS.exists():
    st.error("❌ Faltan archivos en /data")
    st.stop()

# =============================
# HEADER
# =============================
st.markdown("""
<div style="background-color:#E30613;padding:15px;border-radius:10px">
<h1 style="color:white;text-align:center">📊 Dashboard Cierre Comercial – CVS 2026</h1>
</div>
""", unsafe_allow_html=True)

# =============================
# LOGO
# =============================
if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), use_container_width=True)

# =============================
# PERFIL + SEGURIDAD
# =============================
st.sidebar.subheader("🔐 Acceso")

perfil = st.sidebar.selectbox(
    "Perfil",
    ["ASESOR / LÍDER", "DIRECTOR COMERCIAL"]
)

es_director = False
if perfil == "DIRECTOR COMERCIAL":
    pwd = st.sidebar.text_input("Contraseña", type="password")
    if pwd == CLAVE_DIRECTOR:
        es_director = True
        st.sidebar.success("Acceso autorizado")
    elif pwd:
        st.sidebar.error("Contraseña incorrecta")

# =============================
# CARGA DATOS
# =============================
df = pd.read_excel(RUTA_LIQ)
df_meta = pd.read_excel(RUTA_METAS)

df["Fecha"] = pd.to_datetime(df["Fecha"])
df["Mes"] = df["Fecha"].dt.strftime("%Y-%m")

for c in ["Sucursal", "Producto", "Rol"]:
    df[c] = df[c].astype(str).str.upper().str.strip()

df = df.merge(df_meta, on=["Sucursal", "Producto"], how="left")

# =============================
# FILTROS
# =============================
st.sidebar.subheader("📅 Filtros")

mes = st.sidebar.selectbox("Mes", ["Todos"] + sorted(df["Mes"].unique()))
cvs = st.sidebar.selectbox("CVS", ["Todos"] + sorted(df["Sucursal"].unique()))

df_f = df.copy()
if mes != "Todos":
    df_f = df_f[df_f["Mes"] == mes]
if cvs != "Todos":
    df_f = df_f[df_f["Sucursal"] == cvs]

# =============================
# SQL
# =============================
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def crear_tabla():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS decisiones_pago(
            cvs TEXT, nombre TEXT, rol TEXT, producto TEXT,
            tipo_pago TEXT, observacion TEXT, mes TEXT,
            PRIMARY KEY(cvs,nombre,rol,producto,mes)
        )
        """)

crear_tabla()

def guardar_sql(df):
    with get_conn() as conn:
        for _, r in df.iterrows():
            conn.execute("""
            INSERT OR REPLACE INTO decisiones_pago
            VALUES (?,?,?,?,?,?,?)
            """, (
                r["CVS"], r["Nombre"], r["Rol"], r["Producto"],
                r["Tipo Pago Comisión"], r["Observación"], r["Mes"]
            ))

def cargar_sql(mes, cvs):
    with get_conn() as conn:
        return pd.read_sql("""
        SELECT * FROM decisiones_pago
        WHERE mes=? AND cvs=?
        """, conn, params=(mes, cvs))

# =============================
# FUNCIONES
# =============================
def semaforo(p):
    v = int(p.replace("%", ""))
    if v >= 100: return "🟢 CUMPLE"
    if v >= 90: return "🟡 CERCA"
    return "🔴 NO CUMPLE"

# =============================
# TABS
# =============================
tab1, tab2 = st.tabs(["📊 Dashboard", "💰 Presupuesto / Comisión"])

# =============================
# TAB 1 – DASHBOARD
# =============================
with tab1:
    st.subheader("📦 Cumplimiento por Producto")

    prod = df_f.groupby("Producto").agg(
        Meta=("Meta_Producto","sum"),
        Ejecutado=("Puntos","sum")
    ).reset_index()

    fig, ax = plt.subplots()
    ax.bar(prod["Producto"], prod["Meta"])
    ax.bar(prod["Producto"], prod["Ejecutado"])
    ax.set_title("Meta vs Ejecutado (Puntos)")
    st.pyplot(fig)

    st.subheader("👤 Cumplimiento por Persona")

    per = df_f.groupby("Nombre_Vendedor")["Puntos"].sum().reset_index()
    fig2, ax2 = plt.subplots()
    ax2.barh(per["Nombre_Vendedor"], per["Puntos"])
    st.pyplot(fig2)


    st.sidebar.subheader("📅 Filtro de mes")

meses = sorted(df["Fecha"].dt.to_period("M").astype(str).unique().tolist())

mes_sel = st.sidebar.selectbox(
    "Selecciona mes",
    meses
)

def obtener_decision_guardada(mes, cvs, nombre, rol, producto):
    for r in st.session_state.get("historico_decisiones", []):
        if (
            r["Mes"] == mes and
            r["CVS"] == cvs and
            r["Nombre"] == nombre and
            r["Rol"] == rol and
            r["Producto"] == producto
        ):
            return r["Tipo Pago Comisión"], r["Observación"]
    return "Pago 100%", ""

#FUNCIONES BASE

def calcular_distribucion(n_asesores):
    if n_asesores == 1:
        return 0.40, 0.60
    elif n_asesores == 2:
        return 0.25, 0.75
    elif n_asesores >= 3:
        return 0.20, 0.80
    else:
        return 1, 0


# =====================
# MAESTRO DE PRODUCTOS
# =====================
def maestro_productos_por_cvs(df, cvs_sel):
    return (
        df[df["Sucursal"] == cvs_sel][["Producto", "Meta_Producto"]]
        .drop_duplicates()
    )

# TABLA DE PRODUCTOS (CANTIDADES)

def construir_tabla_productos(df_persona, maestro):
    ejecutado = (
        df_persona.groupby("Producto")
        .agg(Ejecutado=("Cantidad", "sum"))
        .reset_index()
    )

    tabla = maestro.merge(ejecutado, on="Producto", how="left")
    tabla["Ejecutado"] = tabla["Ejecutado"].fillna(0)

    tabla["% Cumplimiento"] = (
        tabla["Ejecutado"] / tabla["Meta_Producto"] * 100
    ).round(1)

    return tabla


# KPI DE PUNTOS (META GENERAL)

def calcular_kpi_puntos(df_cvs, df_persona, rol):
    meta_general = df_cvs["Meta_General"].iloc[0]

    n_asesores = df_cvs[df_cvs["Rol"] == "ASESOR"]["Cedula_Vendedor"].nunique()
    pct_lider, pct_asesores = calcular_distribucion(n_asesores)

    pct = pct_lider if rol == "LIDER" else pct_asesores

    meta = meta_general * pct
    ejecutado = df_persona["Puntos"].sum()

    cumplimiento = round((ejecutado / meta) * 100, 1) if meta > 0 else 0

    return meta, ejecutado, cumplimiento




# =============================
# TAB 2 – PRESUPUESTO / COMISIÓN
# =============================

with tab2:
    st.subheader("📍 Detalle por CVS")

    if "historico_decisiones" not in st.session_state:
        st.session_state["historico_decisiones"] = []

    cvs_sel = st.selectbox("Selecciona CVS", df["Sucursal"].unique())
    df_cvs = df[df["Sucursal"] == cvs_sel]

    maestro = maestro_productos_por_cvs(df, cvs_sel)

    # =====================
    # LÍDER
    # =====================
    df_lider = df_cvs[df_cvs["Rol"] == "LIDER"]

    if not df_lider.empty:
        nombre_lider = df_lider["Nombre_Vendedor"].iloc[0]
        st.markdown(f"## 👔 Líder: **{nombre_lider}**")

        meta_p, ejec_p, pct_p = calcular_kpi_puntos(df_cvs, df_lider, "LIDER")

        st.metric(
            "🎯 KPI Puntos",
            f"{int(ejec_p)} / {int(meta_p)}",
            f"{pct_p}%"
        )

        tabla_lider = construir_tabla_productos(df_lider, maestro)

        tabla_lider["Nombre"] = nombre_lider
        tabla_lider["Rol"] = "LIDER"
        tabla_lider["CVS"] = cvs_sel
        tabla_lider["Mes"] = mes_sel

        tabla_lider[["Tipo Pago Comisión", "Observación"]] = tabla_lider.apply(
            lambda r: next(
                (
                    (x["Tipo Pago Comisión"], x["Observación"])
                    for x in st.session_state["historico_decisiones"]
                    if x["Mes"] == mes_sel and
                       x["CVS"] == cvs_sel and
                       x["Nombre"] == nombre_lider and
                       x["Producto"] == r["Producto"]
                ),
                ("Pago 100%", "")
            ),
            axis=1,
            result_type="expand"
        )

        tabla_lider = st.data_editor(
            tabla_lider,
            column_config={
                "Tipo Pago Comisión": st.column_config.SelectboxColumn(
                    options=["Pago 100%", "Pago 90%", "Sin pago (0%)"]
                ),
                "Observación": st.column_config.TextColumn()
            },
            disabled=not es_director,
            use_container_width=True
        )

    # =====================
    # ASESORAS
    # =====================
    st.markdown("## 👥 Asesoras")
    tablas_asesoras = []

    for nombre, g in df_cvs[df_cvs["Rol"] == "ASESOR"].groupby("Nombre_Vendedor"):
        with st.expander(f"👩 {nombre}"):

            meta_p, ejec_p, pct_p = calcular_kpi_puntos(df_cvs, g, "ASESOR")

            st.metric(
                "🎯 KPI Puntos",
                f"{int(ejec_p)} / {int(meta_p)}",
                f"{pct_p}%"
            )

            tabla = construir_tabla_productos(g, maestro)
            tabla["Nombre"] = nombre
            tabla["Rol"] = "ASESOR"
            tabla["CVS"] = cvs_sel
            tabla["Mes"] = mes_sel

            tabla[["Tipo Pago Comisión", "Observación"]] = tabla.apply(
                lambda r: next(
                    (
                        (x["Tipo Pago Comisión"], x["Observación"])
                        for x in st.session_state["historico_decisiones"]
                        if x["Mes"] == mes_sel and
                           x["CVS"] == cvs_sel and
                           x["Nombre"] == nombre and
                           x["Producto"] == r["Producto"]
                    ),
                    ("Pago 100%", "")
                ),
                axis=1,
                result_type="expand"
            )

            tabla = st.data_editor(
                tabla,
                column_config={
                    "Tipo Pago Comisión": st.column_config.SelectboxColumn(
                        options=["Pago 100%", "Pago 90%", "Sin pago (0%)"]
                    ),
                    "Observación": st.column_config.TextColumn()
                },
                disabled=not es_director,
                use_container_width=True
            )

            tablas_asesoras.append(tabla)

    # =====================
    # GUARDAR + DESCARGAR
    # =====================
    if es_director and st.button("💾 Guardar decisiones del CVS"):
        st.session_state["historico_decisiones"] = [
            r for r in st.session_state["historico_decisiones"]
            if not (r["Mes"] == mes_sel and r["CVS"] == cvs_sel)
        ]

        st.session_state["historico_decisiones"].extend(
            tabla_lider.to_dict("records")
        )

        for t in tablas_asesoras:
            st.session_state["historico_decisiones"].extend(
                t.to_dict("records")
            )

        st.success("✅ Decisiones guardadas correctamente")

    if st.button("📊 Descargar histórico del mes"):
        df_hist = pd.DataFrame(st.session_state["historico_decisiones"])
        df_hist = df_hist[df_hist["Mes"] == mes_sel]

        if not df_hist.empty:
            df_hist.to_excel("Historico_Comisiones.xlsx", index=False)
            st.download_button(
                "⬇️ Descargar Excel",
                open("Historico_Comisiones.xlsx", "rb"),
                file_name="Historico_Comisiones.xlsx"
            )
