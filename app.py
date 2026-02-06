import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import sqlite3
from PIL import Image
import matplotlib.pyplot as plt
import numpy as np

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

# Filtro por mes
meses = ["Todos"] + sorted(df["Mes"].dropna().unique())
mes_sel = st.sidebar.selectbox("Mes", meses)

# Filtro por CVS según perfil
if es_director or es_admin:
    cvs_sel = st.sidebar.selectbox(
        "CVS",
        ["Todos"] + sorted(df["Sucursal"].dropna().unique())
    )
else:
    cvs_sel = cvs_usuario

# =============================
# APLICAR FILTROS
# =============================
df_f = df.copy()

# Filtro mes
if mes_sel != "Todos":
    df_f = df_f[df_f["Mes"] == mes_sel]

# Filtro CVS
if cvs_sel and cvs_sel != "Todos":
    df_f = df_f[df_f["Sucursal"] == cvs_sel]



# =============================
# TABS
# =============================
tab1, tab2 = st.tabs(["📊 Dashboard", "💰 Presupuesto / Comisión"])

# =============================
# TAB 1 – DASHBOARD
# =============================
with tab1:
    st.subheader("📦 Cumplimiento por Producto")

    # Lista de productos base que siempre queremos mostrar
    productos_base = ["HOGAR", "POSTPAGO", "TERMINALES", "CVS PLUS", "OTROS"]

    # Agregar meta y ejecutado por producto
    prod = df_f.groupby("Producto").agg(
        Meta=("Meta_Producto","sum"),
        Ejecutado=("Puntos","sum")
    ).reset_index()

    # Asegurarse que todos los productos base estén presentes
    prod = pd.DataFrame(productos_base, columns=["Producto"]).merge(
        prod, on="Producto", how="left"
    ).fillna(0)

    # Convertir valores a int
    prod["Meta"] = prod["Meta"].astype(int)
    prod["Ejecutado"] = prod["Ejecutado"].astype(int)

    # Ordenar productos por Ejecutado de mayor a menor (para línea de tendencia)
    prod = prod.sort_values("Ejecutado", ascending=False).reset_index(drop=True)

    # Posiciones de las barras
    x = np.arange(len(prod["Producto"]))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10,6))

    # Barras lado a lado
    bars_meta = ax.bar(x - width/2, prod["Meta"], width, label="Meta", color="#D6CE59")
    bars_ejec = ax.bar(x + width/2, prod["Ejecutado"], width, label="Ejecutado", color="#52965F")

    # Etiquetas encima de cada barra
    for bar in bars_meta:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 1, f"{height:,.0f}".replace(",", "."), ha='center', va='bottom', fontsize=10, color="#918B42")

    for bar in bars_ejec:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 1, f"{height:,.0f}".replace(",", "."), ha='center', va='bottom', fontsize=10, color="#52965F")

    # Línea de tendencia sobre Ejecutado
    z = np.polyfit(x, prod["Ejecutado"], 1)  # ajusta línea recta
    p = np.poly1d(z)
    ax.plot(x, p(x), color="green", linestyle="--", linewidth=2, label="Tendencia Ejecutado")

    # Etiquetas y título
    ax.set_xticks(x)
    ax.set_xticklabels(prod["Producto"], rotation=45, ha="right")
    ax.set_ylabel("Puntos")
    ax.set_title("Meta vs Ejecutado por Producto con Línea de Tendencia")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    st.pyplot(fig)



    st.subheader("🎯 Meta General vs Ejecutado")

    # Calcular totales
    meta_general = df_f["Meta_General"].sum()
    puntos_ejecutados = df_f["Puntos"].sum()

    # Crear DataFrame para el gráfico
    df_general = pd.DataFrame({
        "Concepto": ["Meta General", "Ejecutado"],
        "Valor": [meta_general, puntos_ejecutados]
    })

    # Crear gráfico
    fig, ax = plt.subplots(figsize=(5,3))
    bars = ax.bar(df_general["Concepto"], df_general["Valor"])

    # Etiquetas de datos con separador de miles
    for bar in bars:
        height = bar.get_height()
        valor = f"{height:,.0f}".replace(",", ".")
        ax.text(
            bar.get_x() + bar.get_width()/2,
            height * 1.01,
            valor,
            ha="center",
            va="bottom",
            fontsize=7,
            fontweight="bold"
        )

    # Formato del eje Y con miles
    ax.yaxis.set_major_formatter(
    plt.FuncFormatter(lambda x, _: f"{int(x):,}".replace(",", "."))
    )

    ax.set_ylabel("Puntos", fontsize=6)
    ax.set_title("Meta General vs Ejecutado", fontsize=6)
    ax.tick_params(axis='x', labelsize=5)
    ax.tick_params(axis='y', labelsize=5)

    ax.grid(axis="y", linestyle="--", alpha=0.5)

    st.pyplot(fig)



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


# =======================
# Archivo histórico central
# =======================
RUTA_HISTORICO = DATA_DIR / "historico_comisiones.xlsx"

# Cargar histórico existente (si existe)
if RUTA_HISTORICO.exists():
    df_historico = pd.read_excel(RUTA_HISTORICO)
else:
    df_historico = pd.DataFrame(
        columns=[
            "Mes", "CVS", "Nombre", "Rol", "Producto",
            "Meta_Producto", "Ejecutado", "% Cumplimiento",
            "Tipo Pago Comisión", "Observación"
        ]
    )

# Guardar en session_state para manipular en la app
if "historico_decisiones" not in st.session_state:
    st.session_state["historico_decisiones"] = df_historico.to_dict("records")

with st.sidebar:
    st.subheader("Filtros")

    meses = sorted(df["Mes"].dropna().unique())
    mes_sel = st.selectbox("Selecciona el mes historico", meses)


# =======================
# TAB 2 – PRESUPUESTO / COMISIÓN
# =======================
with tab2:
    st.subheader("📍 Detalle por CVS")

    # Usar el CVS del filtro lateral
    if cvs_sel == "Todos" or not cvs_sel:

        st.info("Selecciona un CVS en el panel lateral")
        st.stop()

    df_cvs = df_f[df_f["Sucursal"] == cvs_sel]

    # Maestro de productos del CVS
    maestro = maestro_productos_por_cvs(df_f, cvs_sel)

    tablas_guardar = []

    # =====================
    # LÍDER
    # =====================
    df_lider = df_cvs[df_cvs["Rol"] == "LIDER"].copy()
    if df_lider.empty:
        st.warning("⚠️ No se encontró líder para este CVS")
    else:
        nombre_lider = df_lider["Nombre_Vendedor"].iloc[0]
        st.markdown(f"## 👔 Líder: **{nombre_lider}**")

        meta_p, ejec_p, pct_p = calcular_kpi_puntos(df_cvs, df_lider, "LIDER")
        st.metric("🎯 KPI Puntos", f"{int(ejec_p)} / {int(meta_p)}", f"{pct_p}%")

        tabla_lider = construir_tabla_productos(df_lider, maestro, df_cvs, "LIDER")
        tabla_lider["Nombre"] = nombre_lider
        tabla_lider["Rol"] = "LIDER"
        tabla_lider["CVS"] = cvs_sel
        tabla_lider["Mes"] = mes_sel

        # Cargar histórico si existe
        tabla_lider[["Tipo Pago Comisión", "Observación"]] = tabla_lider.apply(
            lambda r: next(
                (
                    (x["Tipo Pago Comisión"], x["Observación"])
                    for x in st.session_state.get("historico_decisiones", [])
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

        # ✅ Asegurar que las columnas sean tipo string
        tabla_lider["Tipo Pago Comisión"] = tabla_lider["Tipo Pago Comisión"].astype(str)
        tabla_lider["Observación"] = tabla_lider["Observación"].fillna("").astype(str)

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
                st.metric("🎯 KPI Puntos", f"{int(ejec_p)} / {int(meta_p)}", f"{pct_p}%")

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
                            for x in st.session_state.get("historico_decisiones", [])
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

                # ✅ Asegurar que las columnas sean tipo string
                tabla["Tipo Pago Comisión"] = tabla["Tipo Pago Comisión"].astype(str)
                tabla["Observación"] = tabla["Observación"].fillna("").astype(str)

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
        if tablas_guardar:  # Prevenir error si no hay tablas
            nuevas_decisiones = pd.concat(tablas_guardar, ignore_index=True)

            # Cargar histórico existente desde Excel
            if RUTA_HISTORICO.exists():
                df_historico = pd.read_excel(RUTA_HISTORICO, engine="openpyxl")
            else:
                df_historico = pd.DataFrame(columns=nuevas_decisiones.columns)

            # Eliminar registros del mismo CVS y mes
            df_historico = df_historico[~(
                (df_historico["Mes"] == mes_sel) &
                (df_historico["CVS"] == cvs_sel)
            )]

            # Agregar nuevas decisiones
            df_historico = pd.concat([df_historico, nuevas_decisiones], ignore_index=True)

            # Guardar a Excel
            df_historico.to_excel(RUTA_HISTORICO, index=False)

            # Actualizar session_state
            st.session_state["historico_decisiones"] = df_historico.to_dict("records")

            st.success(f"✅ Decisiones guardadas correctamente en {RUTA_HISTORICO.name}")

    if st.button("📊 Descargar histórico del mes"):
        df_hist = pd.DataFrame(st.session_state.get("historico_decisiones", []))
        df_hist = df_hist[df_hist["Mes"] == mes_sel]
        if not df_hist.empty:
            with open(RUTA_HISTORICO, "rb") as f:
                st.download_button(
                    "⬇️ Descargar Excel",
                    f,
                    file_name=f"Historico_Comisiones_{mes_sel}.xlsx"
                )
