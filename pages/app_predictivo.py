import pandas as pd
import folium
import streamlit as st
import streamlit.components.v1 as components
import os
import re
import json

# =========================================================================
# CONFIGURACIÓN DE RUTAS RELATIVAS (Optimizado para la Nube y GitHub)
# =========================================================================
# Eliminamos la ruta C:\... para leer directamente los archivos del repositorio
RUTA_CSV = "historico_real_completo-F2.csv"
RUTA_GEOJSON = "Localidades1.0.geojson"

# Coordenadas geográficas base para el centrado de las burbujas por localidad
coordenadas_localidades = {
    'LOCALIDAD': ['USAQUEN', 'CHAPINERO', 'SANTA FE', 'SAN CRISTOBAL', 'USME', 
                  'TUNJUELITO', 'BOSA', 'KENNEDY', 'FONTIBON', 'ENGATIVA', 
                  'SUBA', 'BARRIOS UNIDOS', 'TEUSAQUILLO', 'LOS MARTIRES', 
                  'ANTONIO NARIÑO', 'PUENTE ARANDA', 'LA CANDELARIA', 
                  'RAFAEL URIBE URIBE', 'CIUDAD BOLIVAR', 'SUMAPAZ'],
    'Lat': [4.742, 4.656, 4.602, 4.571, 4.498, 4.579, 4.620, 4.630, 4.671, 4.711, 
            4.761, 4.667, 4.642, 4.606, 4.591, 4.613, 4.596, 4.562, 4.531, 4.043],
    'Lon': [-74.030, -74.059, -74.068, -74.083, -74.116, -74.135, -74.190, -74.151, -74.143, -74.115, 
            -74.066, -74.072, -74.085, -74.089, -74.101, -74.114, -74.073, -74.111, -74.153, -74.316]
}
df_coor = pd.DataFrame(coordenadas_localidades)

# =========================================================================
# 1. MOTOR DE INTELIGENCIA DE DATOS: CARGA Y PROCESAMIENTO OPTIMIZADO
# =========================================================================
@st.cache_data
def cargar_y_procesar_historico(ruta):
    """
    Carga el dataset segmentado por punto y coma, extrae variables
    temporales y calcula la tasa de incidentes por hora para la simulación.
    """
    if not os.path.exists(ruta):
        return None, 0
    
    # Leer el archivo de forma eficiente
    df = pd.read_csv(ruta, sep=';', encoding='latin1', low_memory=False)
    total_registros = len(df)
    
    # Limpieza básica de nombres de columnas
    df.columns = [col.upper().strip().replace('"', '') for col in df.columns]
    
    # Extracción de la HORA entera
    if 'HORA' in df.columns:
        df['HORA_PROCESADA'] = df['HORA'].astype(str).str.split(':').str[0]
        df['HORA_PROCESADA'] = pd.to_numeric(df['HORA_PROCESADA'], errors='coerce').fillna(0).astype(int)
    else:
        df['HORA_PROCESADA'] = 0

    # Extracción del DIA de la semana
    if 'FECHA_INICIO_DESPLAZAMIENTO_MOVIL' in df.columns:
        fechas = pd.to_datetime(df['FECHA_INICIO_DESPLAZAMIENTO_MOVIL'], format='%d/%m/%Y', errors='coerce')
        dias_map = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 'Thursday': 'Jueves', 
                    'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
        df['DIA_PROCESADO'] = fechas.dt.day_name().replace(dias_map)
    else:
        df['DIA_PROCESADO'] = 'Lunes'
        
    if 'LOCALIDAD' in df.columns:
        df['LOCALIDAD'] = df['LOCALIDAD'].astype(str).str.upper().str.strip()
    
    conteo = df.groupby(['DIA_PROCESADO', 'HORA_PROCESADA', 'LOCALIDAD']).size().reset_index(name='Total_Casos')
    conteo['Incidentes_Proyectados'] = (conteo['Total_Casos'] / 52).round(1)
    
    return conteo, total_registros

# Ejecutar carga y procesamiento pesado indexado en caché
with st.spinner("🔮 Procesando base de datos histórica... Por favor espere."):
    df_modelo, total_filas_reales = cargar_y_procesar_historico(RUTA_CSV)

# =========================================================================
# 2. INTERFAZ GRÁFICA DE USUARIO (STREAMLIT)
# =========================================================================
st.title("🔮 Simulador Predictivo Basado en Evidencia Histórica Real")
st.markdown("### Proyección Espacio-Temporal con Motor de Densidad entrenado directamente desde tu Base de Datos")
st.divider()

if df_modelo is None:
    st.error(f"❌ No se encontró el archivo CSV en la raíz del repositorio: `{RUTA_CSV}`")
else:
    # Barra Lateral: Controles para filtrar el histórico masivo
    with st.sidebar:
        st.header("⚙️ Variables de Simulación")
        st.caption("Ajuste los parámetros temporales para interrogar la base de datos:")
        
        input_dia = st.selectbox(
            "📆 Seleccione el Día de la Semana:",
            options=['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'],
            index=4 # Viernes por defecto
        )
        
        input_hora = st.slider(
            "⏰ Seleccione la Hora de Simulación (24h):",
            min_value=0,
            max_value=23,
            value=19, # 7:00 PM por defecto
            step=1
        )
        
        st.divider()
        st.markdown("### 🚨 Umbral de Carga Operacional")
        st.markdown("🔴 **Carga Crítica:** Superior al promedio esperado en hora pico")
        st.markdown("🟡 **Carga Moderada:** Comportamiento estándar estable")
        st.markdown("🟢 **Carga Baja:** Densidad mínima de llamadas")
        st.divider()
        st.success(f"📋 Dataset conectado con éxito.")

    # Filtrado en tiempo real
    df_filtrado = df_modelo[(df_modelo['DIA_PROCESADO'] == input_dia) & (df_modelo['HORA_PROCESADA'] == input_hora)]
    df_resultados = pd.merge(df_coor, df_filtrado, on='LOCALIDAD', how='left').fillna(0)
    
    max_casos = df_resultados['Incidentes_Proyectados'].max()
    umbral_rojo = max_casos * 0.70 if max_casos > 0 else 5
    umbral_amarillo = max_casos * 0.35 if max_casos > 0 else 2

    # KPI Cards
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric(label="📊 Volumen Total del Dataset Histórico", value=f"{total_filas_reales:,} Registros")
    with kpi2:
        if len(df_resultados[df_resultados['Incidentes_Proyectados'] > 0]) > 0:
            idx_max = df_resultados['Incidentes_Proyectados'].idxmax()
            loc_max = df_resultados.loc[idx_max, 'LOCALIDAD']
            val_max = df_resultados.loc[idx_max, 'Incidentes_Proyectados']
            st.metric(label=f"🚨 Foco de Carga Máxima Proyectada ({loc_max.title()})", value=f"{val_max} incidentes/h")
        else:
            st.metric(label="🚨 Foco de Carga Máxima Proyectada", value="0 incidentes/h")
    with kpi3:
        localidades_criticas = len(df_resultados[df_resultados['Incidentes_Proyectados'] >= umbral_rojo]) if max_casos > 0 else 0
        st.metric(label="🔴 Sectores en Saturación Inminente", value=f"{localidades_criticas} de 20")

    st.divider()

    # Layout de columnas
    col_mapa, col_tabla = st.columns([6, 4])

    with col_mapa:
        st.subheader(f"🗺️ Densidad de Emergencias Proyectada: {input_dia} a las {input_hora}:00 hs")
        
        m = folium.Map(location=[4.640, -74.100], zoom_start=11, tiles="cartodbpositron")
        
        # --- NUEVA CAPA: DIBUJAR LÍMITES GEOJSON DE LAS LOCALIDADES ---
        if os.path.exists(RUTA_GEOJSON):
            with open(RUTA_GEOJSON, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            folium.GeoJson(
                geojson_data,
                name="Límites Bogotá",
                style_function=lambda x: {
                    'fillColor': '#f8f9fa',
                    'color': '#4a4a4a',
                    'weight': 1.5,
                    'fillOpacity': 0.05
                }
            ).add_to(m)
        
        # Dibujar las burbujas tipo semáforo
        for idx, row in df_resultados.iterrows():
            casos = row['Incidentes_Proyectados']
            
            if casos >= umbral_rojo and
