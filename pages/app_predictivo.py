import pandas as pd
import folium
import streamlit as st
import streamlit.components.v1 as components
import os
import re
import json

# =========================================================================
# CONFIGURACION DE RUTAS RELATIVAS (Optimizado para la Nube y GitHub)
# =========================================================================
# Eliminamos la ruta local para leer directo del repositorio
RUTA_CSV = "historico_real_completo-F2.csv"
RUTA_GEOJSON = "Localidades1.0.geojson"

# Coordenadas geograficas base para el centrado de las burbujas por localidad
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
    temporales y calcula la tasa de incidentes por hora para la simulacion.
    """
    if not os.path.exists(ruta):
        return None, 0
    
    # Leer el archivo de forma eficiente
    df = pd.read_csv(ruta, sep=';', encoding='latin1', low_memory=False)
    total_registros = len(df)
    
    # Limpieza basica de nombres de columnas
    df.columns = [col.upper().strip().replace('"', '') for col in df.columns]
    
    # Extraccion de la HORA entera
    if 'HORA' in df.columns:
        df['HORA_PROCESADA'] = df['HORA'].astype(str).str.split(':').str[0]
        df['HORA_PROCESADA'] = pd.to_numeric(df['HORA_PROCESADA'], errors='coerce').fillna(0).astype(int)
    else:
        df['HORA_PROCESADA'] = 0

    # Extraccion del DIA de la semana
    if 'FECHA_INICIO_DESPLAZAMIENTO_MOVIL' in df.columns:
        fechas = pd.to_datetime(df['FECHA_INICIO_DESPLAZAMIENTO_MOVIL'], format='%d/%m/%Y', errors='coerce')
        dias_map = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miercoles', 'Thursday': 'Jueves', 
                    'Friday': 'Viernes', 'Saturday': 'Sabado', 'Sunday': 'Domingo'}
        df['DIA_PROCESADO'] = fechas.dt.day_name().replace(dias_map)
    else:
        df['DIA_PROCESADO'] = 'Lunes'
        
    if 'LOCALIDAD' in df.columns:
        df['LOCALIDAD'] = df['LOCALIDAD'].astype(str).str.upper().str.strip()
    
    conteo = df.groupby(['DIA_PROCESADO', 'HORA_PROCESADA', 'LOCALIDAD']).size().reset_index(name='Total_Casos')
    conteo['Incidentes_Proyectados'] = (conteo['Total_Casos'] / 52).round(1)
    
    return conteo, total_registros

# Ejecutar carga y procesamiento pesado indexado en cache
with st.spinner("Procesando base de datos historica... Por favor espere."):
    df_modelo, total_filas_reales = cargar_y_procesar_historico(RUTA_CSV)

# =========================================================================
# 2. INTERFAZ GRAFICA DE USUARIO (STREAMLIT)
# =========================================================================
st.title("Simulador Predictivo Basado en Evidencia Historica Real")
st.markdown("### Proyeccion Espacio-Temporal con Motor de Densidad entrenado directamente desde tu Base de Datos")
st.divider()

if df_modelo is None:
    st.error(f"No se encontro el archivo CSV en la raiz del repositorio: `{RUTA_CSV}`")
else:
    # Barra Lateral: Controles para filtrar el historico masivo
    with st.sidebar:
        st.header("Variables de Simulacion")
        st.caption("Ajuste los parametros temporales para interrogar la base de datos:")
        
        input_dia = st.selectbox(
            "Seleccione el Dia de la Semana:",
            options=['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo'],
            index=4 # Viernes por defecto
        )
        
        input_hora = st.slider(
            "Seleccione la Hora de Simulacion (24h):",
            min_value=0,
            max_value=23,
            value=19, # 7:00 PM por defecto
            step=1
        )
        
        st.divider()
        st.markdown("### Umbral de Carga Operacional")
        st.markdown("Carga Critica: Superior al promedio esperado en hora pico")
        st.markdown("Carga Moderada: Comportamiento estandar estable")
        st.markdown("Carga Baja: Densidad minima de llamadas")
        st.divider()
        st.success(f"Dataset conectado con exito.")

    # Filtrado en tiempo real
    df_filtrado = df_modelo[(df_modelo['DIA_PROCESADO'] == input_dia) & (df_modelo['HORA_PROCESADA'] == input_hora)]
    df_resultados = pd.merge(df_coor, df_filtrado, on='LOCALIDAD', how='left').fillna(0)
    
    max_casos = df_resultados['Incidentes_Proyectados'].max()
    umbral_rojo = max_casos * 0.70 if max_casos > 0 else 5
    umbral_amarillo = max_casos * 0.35 if max_casos > 0 else 2

    # KPI Cards
    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric(label="Volumen Total del Dataset Historico", value=f"{total_filas_reales:,} Registros")
    with kpi2:
        if len(df_resultados[df_resultados['Incidentes_Proyectados'] > 0]) > 0:
            idx_max = df_resultados['Incidentes_Proyectados'].idxmax()
            loc_max = df_resultados.loc[idx_max, 'LOCALIDAD']
            val_max = df_resultados.loc[idx_max, 'Incidentes_Proyectados']
            st.metric(label=f"Foco de Carga Maxima Proyectada ({loc_max.title()})", value=f"{val_max} incidentes/h")
        else:
            st.metric(label="Foco de Carga Maxima Proyectada", value="0 incidentes/h")
    with kpi3:
        localidades_criticas = len(df_resultados[df_resultados['Incidentes_Proyectados'] >= umbral_rojo]) if max_casos > 0 else 0
        st.metric(label="Sectores en Saturacion Inminente", value=f"{localidades_criticas} de 20")

    st.divider()

    # Layout de columnas
    col_mapa, col_tabla = st.columns([6, 4])

    with col_mapa:
        st.subheader(f"Densidad de Emergencias Proyectada: {input_dia} a las {input_hora}:00 hs")
        
        m = folium.Map(location=[4.640, -74.100], zoom_start=11, tiles="cartodbpositron")
        
        # Dibujar limites GeoJSON de las localidades si existe
        if os.path.exists(RUTA_GEOJSON):
            with open(RUTA_GEOJSON, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            folium.GeoJson(
                geojson_data,
                name="Limites Bogota",
                style_function=lambda x: {
                    'fillColor': '#f8f9fa',
                    'color': '#4a4a4a',
                    'weight': 1.5,
                    'fillOpacity': 0.05
                }
            ).add_to(m)
        
        # Dibujar las burbujas tipo semaforo
        for idx, row in df_resultados.iterrows():
            casos = row['Incidentes_Proyectados']
            
            if casos >= umbral_rojo and casos > 0:
                color_semaforo = "#e63946"  # Rojo
                alerta_txt = "CRITICA (ALTA DENSIDAD)"
            elif casos >= umbral_amarillo and casos > 0:
                color_semaforo = "#ffb703"  # Amarillo
                alerta_txt = "MODERADA"
            else:
                color_semaforo = "#2a9d8f"  # Verde
                alerta_txt = "BAJA / BAJO RIESGO"

            radio_visual = (casos / (max_casos if max_casos > 0 else 1)) * 2500
            radio_visual = max(radio_visual, 150)

            folium.Circle(
                location=[row['Lat'], row['Lon']],
                radius=radio_visual,
                color=color_semaforo,
                fill=True,
                fill_color=color_semaforo,
                fill_opacity=0.6,
                weight=1.5,
                tooltip=f"<b>Localidad: {row['LOCALIDAD']}</b><br>"
                        f"Proyeccion: <b>{casos} incidentes/hora</b><br>"
                        f"Estado: <span style='color:{color_semaforo}'><b>{alerta_txt}</b></span>"
            ).add_to(m)
            
        components.html(m._repr_html_(), height=550, scrolling=False)

    with col_tabla:
        st.markdown("#### Demanda de Incidentes por Hora")
        st.caption("Frecuencia matematica calculada mediante agregacion estructurada del historico real.")
        
        df_tabla = df_resultados[['LOCALIDAD', 'Incidentes_Proyectados']].copy()
        df_tabla.columns = ['Localidad', 'Incidentes Esperados (Casos/Hora)']
        
        st.dataframe(
            df_tabla.sort_values(by='Incidentes Esperados (Casos/Hora)', ascending=False),
            height=450,
            use_container_width=True,
            hide_index=True
        )
        
        st.success(f"Modelo probabilistico sincronizado.")
