import pandas as pd
import folium
import streamlit as st
import streamlit.components.v1 as components
import os
import re
import json

# =========================================================================
# CONTROL DE DISEÑO ANCHO SEGURO (Fuerza la expansión total en subpáginas)
# =========================================================================
st.markdown(
    """
    <style>
    /* Rompe el contenedor estrecho por defecto de las subpáginas */
    .main .block-container {
        max-width: 95% !important;
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }
    /* Selector moderno compatible con la nube de Streamlit */
    [data-testid="stMainBlockContainer"] {
        max-width: 95% !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================================
# CONFIGURACIÓN DE RUTAS RELATIVAS (Para la Nube)
# =========================================================================
RUTA_HISTORICO = "historico_real_completo-F2.csv"
RUTA_AMBULANCIAS = "ubicaciones_ambulancias.csv"
RUTA_HOSPITALES = "red hospitalaria.csv"
RUTA_GEOJSON = "Localidades1.0.geojson"

# Coordenadas maestras para los centros de control
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

# Convertidor auxiliar DMS a Decimal Protegido
def dms_a_decimal(coord_str):
    if pd.isna(coord_str) or not isinstance(coord_str, str):
        return None
    try:
        partes = re.findall(r"[-+]?\d*\.\d+|\d+", coord_str)
        if len(partes) >= 3:
            grados = float(partes[0])
            minutos = float(partes[1])
            segundos = float(partes[2])
            decimal = grados + (minutos / 60.0) + (segundos / 3600.0)
            if any(char in coord_str.upper() for char in ['W', 'O', 'S']):
                decimal = -decimal
            return decimal
    except Exception:
        return None
    return None

# =========================================================================
# 1. MOTOR DE PROCESAMIENTO INTEGRADO (CON CACHÉ)
# =========================================================================
@st.cache_data
def procesar_todo_el_sistema(ruta_hist, ruta_amb, ruta_hosp):
    if not all(os.path.exists(r) for r in [ruta_hist, ruta_amb, ruta_hosp]):
        return None, None, None, 0, 0, 0
    
    # 1.1 Histórico de Incidentes
    df_hist = pd.read_csv(ruta_hist, sep=';', encoding='latin1', low_memory=False)
    total_inc = len(df_hist)
    df_hist.columns = [col.upper().strip().replace('"', '') for col in df_hist.columns]
    
    df_hist['HORA_PROCESADA'] = df_hist['HORA'].astype(str).str.split(':').str[0]
    df_hist['HORA_PROCESADA'] = pd.to_numeric(df_hist['HORA_PROCESADA'], errors='coerce').fillna(0).astype(int)
    
    fechas = pd.to_datetime(df_hist['FECHA_INICIO_DESPLAZAMIENTO_MOVIL'], format='%d/%m/%Y', errors='coerce')
    dias_map = {'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles', 'Thursday': 'Jueves', 
                'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
    df_hist['DIA_PROCESADO'] = fechas.dt.day_name().replace(dias_map)
    df_hist['LOCALIDAD'] = df_hist['LOCALIDAD'].astype(str).str.upper().str.strip()
    
    conteo_incidentes = df_hist.groupby(['DIA_PROCESADO', 'HORA_PROCESADA', 'LOCALIDAD']).size().reset_index(name='Total_Casos')
    conteo_incidentes['Incidentes_Proyectados'] = (conteo_incidentes['Total_Casos'] / 52).round(1)
    
    # 1.2 Ubicaciones de Ambulancias
    df_amb = pd.read_csv(ruta_amb, sep=';', encoding='latin1', low_memory=False)
    total_amb = len(df_amb)
    df_amb.columns = [col.upper().strip().replace('"', '') for col in df_amb.columns]
    df_amb['LOCALIDAD'] = df_amb['LOCALIDAD'].astype(str).str.upper().str.strip()
    
    df_amb['COORDENADAS GEOGRAFICAS'] = df_amb['COORDENADAS GEOGRAFICAS'].fillna('').astype(str).str.strip()
    
    def extraer_coor_seguro(texto, parte_index):
        if not texto or ' ' not in texto:
            return None
        partes = texto.split(' ')
        try:
            return dms_a_decimal(partes[parte_index])
        except Exception:
            return None

    df_amb['LATITUD'] = df_amb['COORDENADAS GEOGRAFICAS'].apply(lambda x: extraer_coor_seguro(x, 0))
    df_amb['LONGITUD'] = df_amb['COORDENADAS GEOGRAFICAS'].apply(lambda x: extraer_coor_seguro(x, 1))
    
    # 1.3 Red Hospitalaria
    df_hosp = pd.read_csv(ruta_hosp, sep=';', encoding='utf-8', low_memory=False)
    total_hosp = len(df_hosp)
    
    df_hosp.columns = [col.upper().strip().replace('"', '') for col in df_hosp.columns]
    df_hosp['LOCALIDAD'] = df_hosp['LOCALIDAD'].astype(str).str.upper().str.strip()
    
    col_coordenadas = [c for c in df_hosp.columns if 'COORDENADAS' in c][0]
    
    df_hosp['LATITUD'] = df_hosp[col_coordenadas].astype(str).str.replace('"', '').str.split(';').str[0]
    df_hosp['LONGITUD'] = df_hosp[col_coordenadas].astype(str).str.replace('"', '').str.split(';').str[1]
    
    df_hosp['LATITUD'] = pd.to_numeric(df_hosp['LATITUD'], errors='coerce')
    df_hosp['LONGITUD'] = pd.to_numeric(df_hosp['LONGITUD'], errors='coerce')

    return conteo_incidentes, df_amb, df_hosp, total_inc, total_amb, total_hosp

with st.spinner("🔄 Acoplando matrices analíticas y Red Hospitalaria de Bogotá..."):
    df_modelo, df_ambulancias, df_hospitales, total_inc, total_bases_reales, total_hosp_reales = procesar_todo_el_sistema(RUTA_HISTORICO, RUTA_AMBULANCIAS, RUTA_HOSPITALES)

# =========================================================================
# 2. ENTORNO VISUAL INTERACTIVO
# =========================================================================
st.title("🚑 Asign
