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
# =============================
# ACCESOS
# =============================
CLAVE_DIRECTOR = "Director2026+"
CLAVE_ADMIN = "Sercom2026+"

ACCESOS_CVS = {
    "COPACABANA": "comicopa2026*",
    "BARBOSA": "bosa2026+",
    "CAUCASIA": "cvscaucasia2026/",
    "CIUDAD BOLIVAR": "bolivar2020+",
    "DABEIBA": "dabeiba2020+",
    "DON MATIAS": "cvsmatias2026*",
    "EL BAGRE": "bagre2021*",
    "FRONTINO": "frontino2026+",
    "LA ESTRELLA": "cvsestrella2026ser*",
    "NECHI": "cvssernechi2026+",
    "PRADO": "cvsprado2026*",
    "SEGOVIA": "sersegovia2026+",
    "YARUMAL": "cvsyarumal2026+",
    "ZARAGOZA": "zaragozaser2020+",
    "BELLO": "cvsbello456*",
    "ENVIGADO": "envigado1234+",
    "ITAGUI": "sertagui44/",
    "CALDAS": "sercaldas2025+",
    "JUNIN": "cvscentro2025+",
    "SABANETA": "sabaneta19092+",
    "TERMINAL NORTE": "norte11+",

}

st.sidebar.subheader("🔐 Acceso")

perfil = st.sidebar.selectbox(
    "Perfil",
    ["CVS", "ADMINISTRATIVO", "DIRECTOR COMERCIAL"]
)

es_director = False
es_admin = False
cvs_usuario = None

# =============================
# PERFIL CVS
# =============================
if perfil == "CVS":
    cvs_input = st.sidebar.selectbox(
        "Selecciona tu CVS",
        list(ACCESOS_CVS.keys())
    )
    clave = st.sidebar.text_input("Clave CVS", type="password")

    if clave == ACCESOS_CVS.get(cvs_input):
        cvs_usuario = cvs_input
        st.sidebar.success(f"Acceso autorizado: {cvs_usuario}")
    elif clave:
        st.sidebar.error("Clave incorrecta")

# =============================
# PERFIL ADMINISTRATIVO
# =============================
elif perfil == "ADMINISTRATIVO":
    clave = st.sidebar.text_input("Clave administrativa", type="password")
    if clave == CLAVE_ADMIN:
        es_admin = True
        st.sidebar.success("Acceso administrativo autorizado")
    elif clave:
        st.sidebar.error("Clave incorrecta")

# =============================
# PERFIL DIRECTOR
# =============================
elif perfil == "DIRECTOR COMERCIAL":
    clave = st.sidebar.text_input("Contraseña Director", type="password")
    if clave == CLAVE_DIRECTOR:
        es_director = True
        st.sidebar.success("Acceso director autorizado")
    elif clave:
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


df_f = df.copy()
if mes != "Todos":
    df_f = df_f[df_f["Mes"] == mes]


# =============================
# FILTRO POR CVS SEGÚN PERFIL
# =============================
if es_director or es_admin:
    cvs = st.sidebar.selectbox(
        "CVS",
        ["Todos"] + sorted(df["Sucursal"].unique())
    )
else:
    cvs = cvs_usuario

# Restringir datos según perfil
if perfil == "CVS" and cvs_usuario:
    df_f = df_f[df_f["Sucursal"] == cvs_usuario]


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

# =====================
# REGLA DE DISTRIBUCIÓN
# =====================
def calcular_distribucion(n_asesores):
    if n_asesores == 1:
        return 0.40, 0.60
    elif n_asesores == 2:
        return 0.25, 0.375
    elif n_asesores >= 3:
        return 0.20, 0.266
    else:
        return 1.0, 0.0

# =====================
# MAESTRO DE PRODUCTOS
# =====================
def maestro_productos_por_cvs(df, cvs_sel):
    df_cvs = df[df["Sucursal"] == cvs_sel]

    # Tomar metas únicas por producto
    maestro = (
        df_cvs[["Producto", "Meta_Producto"]]
        .drop_duplicates()
        .set_index("Producto")["Meta_Producto"]
        .to_dict()
    )

    # Asegurar que siempre existan estos productos
    productos_base = ["HOGAR", "POSTPAGO", "TERMINALES", "CVS PLUS", "OTROS"]

    for p in productos_base:
        if p not in maestro:
            maestro[p] = 0

    return maestro



def construir_tabla_productos(df_vendedor, maestro, df_cvs, rol):
    """
    Construye tabla de productos mostrando meta, ejecución y cumplimiento
    aplicando la distribución por rol.
    """

    # =====================
    # CALCULAR Nº ASESORES
    # =====================
    n_asesores = df_cvs[df_cvs["Rol"] == "ASESOR"]["Nombre_Vendedor"].nunique()

    # Obtener porcentajes
    porc_asesor, porc_lider = calcular_distribucion(n_asesores)

    if rol == "LIDER":
        porcentaje = porc_lider
    else:
        porcentaje = porc_asesor

    # =====================
    # VENTAS POR PRODUCTO
    # =====================
    ejec = (
        df_vendedor.groupby("Producto")["Cantidad"]
        .sum()
        .to_dict()
    )

    filas = []

    for producto, meta in maestro.items():

        # aplicar distribución
        meta_ajustada = meta * porcentaje

        ejecutado = ejec.get(producto, 0)

        if meta_ajustada > 0:
            pct = int(round((ejecutado / meta_ajustada) * 100))
        else:
            pct = 0

        filas.append({
            "Producto": producto,
            "Meta_Producto": int(round(meta_ajustada)),
            "Ejecutado": int(ejecutado),
            "% Cumplimiento": f"{pct}%"
        })

    tabla = pd.DataFrame(filas)

    return tabla




# =====================
# KPI DE PUNTOS
# =====================
def calcular_kpi_puntos(df_cvs, df_persona, rol):
    meta_general = df_cvs["Meta_General"].iloc[0]

    n_asesores = df_cvs[df_cvs["Rol"] == "ASESOR"]["Cedula_Vendedor"].nunique()
    pct_lider, pct_asesor_individual = calcular_distribucion(n_asesores)

    if rol == "LIDER":
        meta = meta_general * pct_lider
    else:
        meta = meta_general * pct_asesor_individual

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

    # Usar el CVS del filtro lateral
    if cvs == "Todos":
        st.info("Selecciona un CVS en el panel lateral")
        st.stop()

    cvs_sel = cvs
    df_cvs = df_f[df_f["Sucursal"] == cvs_sel]

    # Maestro de productos del CVS
    maestro = maestro_productos_por_cvs(df_f, cvs_sel)

    # =====================
    # LÍDER
    # =====================
    df_lider = df_cvs[df_cvs["Rol"] == "LIDER"].copy()
    tablas_guardar = []

    if df_lider.empty:
        st.warning("⚠️ No se encontró líder para este CVS")
    else:
        nombre_lider = df_lider["Nombre_Vendedor"].iloc[0]
        st.markdown(f"## 👔 Líder: **{nombre_lider}**")

        meta_p, ejec_p, pct_p = calcular_kpi_puntos(df_cvs, df_lider, "LIDER")

        st.metric(
            "🎯 KPI Puntos",
            f"{int(ejec_p)} / {int(meta_p)}",
            f"{pct_p}%"
        )

        tabla_lider = construir_tabla_productos(
            df_lider, maestro, df_cvs, "LIDER"
        )

        tabla_lider["Nombre"] = nombre_lider
        tabla_lider["Rol"] = "LIDER"
        tabla_lider["CVS"] = cvs_sel
        tabla_lider["Mes"] = mes_sel

        # Cargar histórico si existe
        tabla_lider[["Tipo Pago Comisión", "Observación"]] = tabla_lider.apply(
            lambda r: next(
                (
                    (x["Tipo Pago Comisión"], x["Observación"])
                    for x in st.session_state["historico_decisiones"]
                    if x["Mes"] == mes_sel
                    and x["CVS"] == cvs_sel
                    and x["Nombre"] == nombre_lider
                    and x["Producto"] == r["Producto"]
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
            use_container_width=True,
            key="editor_lider"
        )

        tablas_guardar.append(tabla_lider)

    # =====================
    # ASESORAS
    # =====================
    st.markdown("## 👥 Asesoras")
    df_asesoras = df_cvs[df_cvs["Rol"] == "ASESOR"]

    if df_asesoras.empty:
        st.warning("No hay asesoras en este CVS")
    else:
        for nombre, g in df_asesoras.groupby("Nombre_Vendedor"):
            with st.expander(f"👩 {nombre}"):

                meta_p, ejec_p, pct_p = calcular_kpi_puntos(df_cvs, g, "ASESOR")

                st.metric(
                    "🎯 KPI Puntos",
                    f"{int(ejec_p)} / {int(meta_p)}",
                    f"{pct_p}%"
                )

                tabla = construir_tabla_productos(g, maestro, df_cvs, "ASESOR")

                tabla["Nombre"] = nombre
                tabla["Rol"] = "ASESOR"
                tabla["CVS"] = cvs_sel
                tabla["Mes"] = mes_sel

                # Cargar histórico si existe
                tabla[["Tipo Pago Comisión", "Observación"]] = tabla.apply(
                    lambda r: next(
                        (
                            (x["Tipo Pago Comisión"], x["Observación"])
                            for x in st.session_state["historico_decisiones"]
                            if x["Mes"] == mes_sel
                            and x["CVS"] == cvs_sel
                            and x["Nombre"] == nombre
                            and x["Producto"] == r["Producto"]
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
                    use_container_width=True,
                    key=f"editor_{nombre}"
                )

                tablas_guardar.append(tabla)

    # =====================
    # GUARDAR + DESCARGAR
    # =====================
    if es_director and st.button("💾 Guardar decisiones del CVS"):

        # Eliminar registros del mismo CVS y mes
        st.session_state["historico_decisiones"] = [
            r for r in st.session_state["historico_decisiones"]
            if not (r["Mes"] == mes_sel and r["CVS"] == cvs_sel)
        ]

        # Agregar nuevos registros
        for t in tablas_guardar:
            st.session_state["historico_decisiones"].extend(
                t.to_dict("records")
            )

        st.success("✅ Decisiones guardadas correctamente")

    if st.button("📊 Descargar histórico del mes"):
        df_hist = pd.DataFrame(st.session_state["historico_decisiones"])
        df_hist = df_hist[df_hist["Mes"] == mes_sel]

        if not df_hist.empty:
            archivo = "Historico_Comisiones.xlsx"
            df_hist.to_excel(archivo, index=False)

            with open(archivo, "rb") as f:
                st.download_button(
                    "⬇️ Descargar Excel",
                    f,
                    file_name=archivo
                )
