import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim

geolocalizador = Nominatim(user_agent="safestruct_app")

# 1. Datos sísmicos
zonas = pd.read_csv("data_zonas.csv")

def obtener_zona_sismica(lat, lon):
    for _, row in zonas.iterrows():
        if (row.lat_min <= lat <= row.lat_max) and (row.lon_min <= lon <= row.lon_max):
            return row.pga, row.tipo_suelo
    return 0.20, "S4" 


# 2. Calcular IRS
def calcular_IRS(altura, carga, pga, tipo_suelo, material, area, volumen):
    """
    Calcula el Índice de Riesgo Estructural (IRS).
    Añadido impacto del MATERIAL.
    Devuelve IRS (0-100) y nivel.
    """

    #FACTOR SÍSMICO
    factor_pga = min(pga / 0.45, 1.0)

    # amplificación por suelo
    factor_suelo = {
        "S1": 1.0,
        "S2": 1.15,
        "S3": 1.30,
        "S4": 1.55
    }
    amplificacion = factor_suelo.get(tipo_suelo, 1.2)
    factor_sismico = min(factor_pga * amplificacion, 1.0)

    #FACTOR ESTRUCTURAL
    import math
    factor_esbeltez = min(altura / (math.sqrt(area) + 1e-6), 1.0)

    factor_carga = min(carga / 5000.0, 1.0)

    factor_estructura = (0.6 * factor_esbeltez) + (0.4 * factor_carga)
    factor_estructura = min(factor_estructura, 1.0)

    factor_material = {
    "Acero": 0.75,                  # Muy resistente
    "Concreto": 1.0,                # Estándar
    "Mampostería": 1.35,            # Alta fragilidad
    "Madera": 0.85,                 # Flexible y ligera
    "Adobe": 1.50,                  # Muy vulnerable
    "Prefabricado ligero": 1.20,    # Ligero pero frágil ante sismos
    "Aluminio estructural": 0.90    # Ligero y dúctil
    }
    
    f_mat = factor_material.get(material, 1.0)

    #factor geométrico basado en área y volumen
    factor_area = min(20 / area, 1.5)  
    factor_volumen = min(volumen / 150, 1.5)

    factor_geometria = (0.5 * factor_area + 0.5 * factor_volumen)

    #COMBINACIÓN FINAL
    IRS = (0.50 * factor_sismico + 0.30 * factor_estructura + 0.20 * factor_geometria) * f_mat * 100
    IRS = round(IRS, 2)

    if IRS < 30:
        nivel = "🟢 Seguro"
    elif IRS < 60:
        nivel = "🟡 Moderado"
    else:
        nivel = "🔴 Crítico"

    return IRS, nivel



# 3. Interfaz Streamlit
st.title("🧱 SafeStruct – Evaluador Inteligente de Riesgos Estructurales")
st.write("Selecciona tu ubicación en el mapa e ingresa los datos de tu estructura.")

# 4. Mapa interactivo
st.subheader("📌 Buscar ubicación por nombre (opcional)")

direccion_ingresada = st.text_input("Ingresa una calle, distrito, ciudad o lugar:")

busqueda_latitud = None
busqueda_longitud = None

if direccion_ingresada:
    try:
        resultado = geolocalizador.geocode(direccion_ingresada)
        if resultado:
            busqueda_latitud = resultado.latitude
            busqueda_longitud = resultado.longitude
            st.success(f"📍 Dirección encontrada: {resultado.address}")
        else:
            st.warning("No se encontró la dirección. Intenta otro nombre.")
    except:
        st.error("Error al contactar el servicio de geolocalización.")
st.subheader("📍 Selecciona tu ubicación")

if busqueda_latitud is not None and busqueda_longitud is not None:
    m = folium.Map(location=[busqueda_latitud, busqueda_longitud], zoom_start=14)
else:
    m = folium.Map(location=[-12.0464, -77.0428], zoom_start=12)

# Permitir clic y leer coordenadas
m.add_child(folium.LatLngPopup())

dato_mapa = st_folium(m, width=700, height=500)

if dato_mapa["last_clicked"] is not None:
    latitud = dato_mapa["last_clicked"]["lat"]
    longitud = dato_mapa["last_clicked"]["lng"]

    try:
        lugar_click = geolocalizador.reverse(f"{latitud}, {longitud}")
        if lugar_click:
            st.success(f"📍 Ubicación seleccionada: {lugar_click.address}")
        else:
            st.success(f"📍 Coordenadas seleccionadas: Latitud={latitud}, Longitud={longitud}")
    except:
        st.success(f"📍 Coordenadas seleccionadas: Latitud={latitud}, Longitud={longitud}")

else:
    latitud = None
    longitud = None

# 5. Formulario de datos
st.subheader("🏗️ Datos de tu estructura")

with st.container():
    altura = st.number_input("Altura de la estructura (m)", min_value=1.0, max_value=100.0, step=0.5, key="altura")
    carga = st.number_input("Carga aproximada (kN)", min_value=0.0, max_value=5000.0, step=1.0, key="carga")
    largo = st.number_input("Largo de la edificación (m):", min_value=1.0, max_value=100.0, value=5.0, key="largo")
    ancho = st.number_input("Ancho de la edificación (m):", min_value=1.0, max_value=100.0, value=5.0, key="ancho")

    area = float(largo) * float(ancho)
    volumen = area * float(altura)

    st.write(f" 📏 Área calculada: **{area:.2f} m²**")
    st.write(f" 📦 Volumen aproximado: **{volumen:.2f} m³**")

material = st.selectbox(
    "Material estructural:",
    ["Concreto", "Mampostería", "Acero", "Madera", "Adobe", "Prefabricado ligero", "Aluminio estructural"],
)

# 6. Cuando todo esté listo, calcular
if st.button("Calcular riesgo"):
    if latitud is None:
        st.error("Debes seleccionar una ubicación en el mapa.")
    else:
        pga, tipo_suelo = obtener_zona_sismica(latitud, longitud)

        st.info(f"Zona sísmica detectada: PGA = {pga}, Tipo de suelo = {tipo_suelo}")

        IRS, nivel = calcular_IRS(altura, carga, pga, tipo_suelo, material, area, volumen)

        st.subheader("📊 Resultado del análisis")
        st.write(f"**Índice IRS obtenido:** {IRS:.2f}")
        st.write(f"**Nivel de riesgo:** {nivel}")
        

        #GRÁFICO
        fig, ax = plt.subplots(figsize=(6, 1.2))
        color = "#2ecc71" if IRS < 30 else "#f1c40f" if IRS < 60 else "#e74c3c"

        ax.barh(["IRS"], [IRS], color=color, height=0.4)
        ax.set_xlim(0, 100)
        ax.set_xlabel("Índice de Riesgo Estructural (0–100)")
        ax.grid(axis="x", linestyle="--", alpha=0.4)

        for i, v in enumerate([IRS]):
            ax.text(v + 1, i, f"{v}", va="center")

        st.pyplot(fig)

        #EXPLICACIÓN DETALLADA
        st.subheader("📘 ¿Qué significa este resultado?")

        if IRS < 30:
            st.markdown("""
            ### 🟢 **RIESGO BAJO**
            - La estructura se encuentra en condiciones seguras.
            - La zona sísmica no representa una amenaza significativa.
            - La geometría y carga están dentro de parámetros normales.
            """)
        elif IRS < 60:
            st.markdown("""
            ### 🟡 **RIESGO MODERADO**
            - La estructura podría sufrir daños en un sismo fuerte.
            - Se recomienda una revisión preventiva.
            """)
        else:
            st.markdown("""
            ### 🔴 **RIESGO ALTO**
            - Alta probabilidad de daño severo en caso de sismo.
            - Requiere inspección urgente por un ingeniero estructural.
            """)
