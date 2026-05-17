import pandas as pd
import folium
import streamlit as st
import streamlit.components.v1 as components
import os
import re
import json


# Configuración institucional de entorno ancho
st.set_page_config(layout="wide", page_title="Modelo de Distribución de Recursos", page_icon="🚑")

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

def dms_a_decimal(coordenada_str):
    """
    Convierte una coordenada DMS a decimal de forma segura.
    Si el dato está corrupto o vacío, evita el colapso devolviendo 0.0.
    """
    try:
        coordenada_str = str(coordenada_str).strip()
        if not coordenada_str or coordenada_str.upper() == 'NAN':
            return 0.0
            
        # Aquí va tu lógica matemática actual para convertir DMS a decimal...
        # Ejemplo aproximado (ajústalo según cómo lee tus símbolos °, ', "):
        # ...
        return resultado_decimal
    except Exception:
        return 0.0  # Si falla cualquier división o split, no se cae la app

# =========================================================================
# 1. MOTOR DE PROCESAMIENTO INTEGRADO (CON CACHÉ)
# =========================================================================
@st.cache_data
# =========================================================================
    # PROCESAMIENTO SEGURO DE AMBULANCIAS
    # =========================================================================
    # Asegurar que no existan valores nulos en la columna de coordenadas
    df_amb['COORDENADAS GEOGRAFICAS'] = df_amb['COORDENADAS GEOGRAFICAS'].fillna('').astype(str).str.strip()
    
    # Función interna auxiliar para dividir y extraer de forma segura la Latitud y Longitud
    def extraer_lat_lon_seguro(texto_coor, tipo='LAT'):
        if not texto_coor or ' ' not in texto_coor:
            return 0.0
        
        partes = texto_coor.split(' ')
        try:
            if tipo == 'LAT':
                return dms_a_decimal(partes[0])
            else:
                return dms_a_decimal(partes[1])
        except Exception:
            return 0.0

    # Aplicamos la extracción segura sin usar lambdas complejos en una sola línea
    df_amb['LATITUD'] = df_amb['COORDENADAS GEOGRAFICAS'].apply(lambda x: extraer_lat_lon_seguro(x, 'LAT'))
    df_amb['LONGITUD'] = df_amb['COORDENADAS GEOGRAFICAS'].apply(lambda x: extraer_lat_lon_seguro(x, 'LON'))
    
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
    
    # 1.2 Ubicaciones de Ambulancias (Modificado con Extractor Seguro sin Split)
    df_amb = pd.read_csv(ruta_amb, sep=';', encoding='latin1', low_memory=False)
    total_amb = len(df_amb)
    df_amb.columns = [col.upper().strip().replace('"', '') for col in df_amb.columns]
    df_amb['LOCALIDAD'] = df_amb['LOCALIDAD'].astype(str).str.upper().str.strip()
    
    col_coor_amb = [c for c in df_amb.columns if 'COORDENADAS' in c][0]
    
    def separar_coor_regex(celda, tipo='lat'):
        if pd.isna(celda):
            return None
        texto = str(celda).strip().replace('"', '')
        partes = [p for p in re.split(r'\s+', texto) if p]
        if len(partes) >= 2:
            return dms_a_decimal(partes[0]) if tipo == 'lat' else dms_a_decimal(partes[1])
        return dms_a_decimal(texto)

    df_amb['LATITUD'] = df_amb[col_coor_amb].apply(lambda x: separar_coor_regex(x, 'lat'))
    df_amb['LONGITUD'] = df_amb[col_coor_amb].apply(lambda x: separar_coor_regex(x, 'lon'))
    
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
st.title("🚑 Asignación Preventiva y Optimización de Flotas")
st.markdown("### Contraste Espacial: Distribución de Ambulancias vs. Red Hospitalaria")
st.divider()

if df_modelo is None:
    st.error("❌ Error al enlazar los datasets. Revisa que las rutas de los 3 archivos CSV sean correctas.")
elif not os.path.exists(RUTA_GEOJSON):
    st.error(f"❌ El archivo GeoJSON no se encuentra en: '{RUTA_GEOJSON}'")
else:
    with st.sidebar:
        st.header("⚙️ Configuración del Escenario")
        input_dia = st.selectbox("📆 Día a Evaluar:", ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'], index=4)
        input_hora = st.slider("⏰ Hora Crítica (24h):", 0, 23, 19, step=1)
        st.divider()
        st.markdown("### 🗺️ Leyenda de Recursos")
        st.markdown("🖤 **Borde Línea:** Frontera de Localidad")
        st.markdown("🔵 **Pin Azul (+):** Ambulancia Operativa")
        st.markdown("🔴 **Pin Rojo (H):** Hospital / IPS Disponible")
        st.markdown("🟢🟡🔴 **Burbujas:** Incidentes Proyectados")

    conteo_amb = df_ambulancias.groupby('LOCALIDAD').size().reset_index(name='Bases_Disponibles')
    conteo_hosp = df_hospitales.groupby('LOCALIDAD').size().reset_index(name='Hospitales_Disponibles')
    
    df_filtrado = df_modelo[(df_modelo['DIA_PROCESADO'] == input_dia) & (df_modelo['HORA_PROCESADA'] == input_hora)]
    df_merge = pd.merge(df_coor, df_filtrado, on='LOCALIDAD', how='left').fillna(0)
    df_merge = pd.merge(df_merge, conteo_amb, on='LOCALIDAD', how='left').fillna(0)
    df_final = pd.merge(df_merge, conteo_hosp, on='LOCALIDAD', how='left').fillna(0)
    
    max_casos_global = df_final['Incidentes_Proyectados'].max()

    col_mapa, col_analisis = st.columns([6, 4])

    with col_analisis:
        st.markdown("#### 🎯 Control de Enfoque Territorial")
        opciones_foco = ["📍 MOSTRAR TODAS LAS LOCALIDADES"] + sorted(df_final['LOCALIDAD'].tolist())
        localidad_foco = st.selectbox("Seleccione un Punto Focal para analizar contraste:", options=opciones_foco)
        
        st.divider()
        
        if localidad_foco != "📍 MOSTRAR TODAS LAS LOCALIDADES":
            datos_foco = df_final[df_final['LOCALIDAD'] == localidad_foco].iloc[0]
            st.markdown(f"### 📋 Infraestructura en: {localidad_foco}")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Casos/h", f"{datos_foco['Incidentes_Proyectados']}")
            c2.metric("Ambulancias", f"{int(datos_foco['Bases_Disponibles'])}")
            c3.metric("Hospitales/IPS", f"{int(datos_foco['Hospitales_Disponibles'])}")
            
            ambs = datos_foco['Bases_Disponibles']
            hosps = datos_foco['Hospitales_Disponibles']
            
            if ambs == 0 and hosps == 0:
                st.error("🚨 **Zona Desprotegida:** No hay ambulancias ni hospitales registrados en esta localidad.")
            elif ambs == 0 and hosps > 0:
                st.warning("⚠️ **Vulnerabilidad de Traslado:** Hay hospitales pero faltan ambulancias locales para canalizar emergencias.")
            elif ambs > 0 and hosps == 0:
                st.info("ℹ️ **Zona de Captación:** Cuenta con ambulancias pero dependerá de traslados a localidades vecinas por falta de hospitales.")
            else:
                st.success("✅ **Red Integrada:** Cuenta con puntos de despacho y centros de recepción médica.")
        else:
            st.markdown("#### 📊 Capacidad de la Red Consolidada")
            st.metric("Total Histórico de Incidentes", f"{total_inc:,} Reportes")
            st.metric("Total Ambulancias (Flota Activa)", f"{total_bases_reales} Unidades")
            st.metric("Total Hospitales & IPS Mapeados", f"{total_hosp_reales} Entidades")

        st.divider()
        st.markdown("#### 📊 Matriz de Diagnóstico Territorial")
        df_tabla = df_final[['LOCALIDAD', 'Incidentes_Proyectados', 'Bases_Disponibles', 'Hospitales_Disponibles']].copy()
        df_tabla.columns = ['LOCALIDAD', 'INCIDENTES ESPERADOS', 'AMBULANCIAS', 'HOSPITALES']
        df_tabla['AMBULANCIAS'] = df_tabla['AMBULANCIAS'].astype(int)
        df_tabla['HOSPITALES'] = df_tabla['HOSPITALES'].astype(int)
        st.dataframe(df_tabla.sort_values(by='INCIDENTES ESPERADOS', ascending=False), hide_index=True, use_container_width=True)

    with col_mapa:
        st.subheader(f"📌 Georreferenciación de Infraestructura")
        
        if localidad_foco != "📍 MOSTRAR TODAS LAS LOCALIDADES":
            row_foco = df_final[df_final['LOCALIDAD'] == localidad_foco].iloc[0]
            centro_mapa = [row_foco['Lat'], row_foco['Lon']]
            zoom_inicial = 12
        else:
            centro_mapa = [4.640, -74.100]
            zoom_inicial = 11

        m = folium.Map(location=centro_mapa, zoom_start=zoom_inicial, tiles="cartodbpositron")
        
        with open(RUTA_GEOJSON, 'r', encoding='utf-8') as f:
            geojson_data = json.load(f)

        def funcion_estilo(feature):
            props = feature['properties']
            nombre_geo = ""
            for llave in ['Localidad', 'LOCALIDAD', 'Nombre', 'NOMBRE', 'NOMBRE_LOCALIDAD']:
                if llave in props and props[llave]:
                    nombre_geo = str(props[llave]).upper().strip()
                    break
            
            if localidad_foco != "📍 MOSTRAR TODAS LAS LOCALIDADES":
                if localidad_foco in nombre_geo or nombre_geo in localidad_foco:
                    return {'fillColor': '#1d3557', 'color': '#1d3557', 'weight': 3.2, 'fillOpacity': 0.12}
                else:
                    return {'fillColor': '#ffffff', 'color': '#e0e0e0', 'weight': 0.6, 'fillOpacity': 0.01}
            return {'fillColor': '#f8f9fa', 'color': '#4a4a4a', 'weight': 1.6, 'fillOpacity': 0.04}

        folium.GeoJson(geojson_data, name="Límites", style_function=funcion_estilo).add_to(m)

        for idx, row in df_final.iterrows():
            if localidad_foco != "📍 MOSTRAR TODAS LAS LOCALIDADES" and row['LOCALIDAD'] != localidad_foco:
                continue
            casos = row['Incidentes_Proyectados']
            if casos > 0:
                relacion = row['Bases_Disponibles'] / casos
                color_nodo = "#e63946" if relacion < 1.0 else ("#ffb703" if relacion <= 2.0 else "#2a9d8f")
                radio_dinamico = max((casos / (max_casos_global if max_casos_global > 0 else 1)) * 2500, 200)
                
                folium.Circle(
                    location=[row['Lat'], row['Lon']], radius=radio_dinamico,
                    color=color_nodo, fill=True, fill_color=color_nodo, fill_opacity=0.25, weight=1,
                    tooltip=f"<b>{row['LOCALIDAD']}</b><br>Incidentes: {casos}/h"
                ).add_to(m)
            
        for idx, row_amb in df_ambulancias.iterrows():
            if localidad_foco != "📍 MOSTRAR TODAS LAS LOCALIDADES" and row_amb['LOCALIDAD'] != localidad_foco:
                continue
            lat, lon = row_amb['LATITUD'], row_amb['LONGITUD']
            if pd.notna(lat) and pd.notna(lon):
                p_base = row_amb['PROPUESTA BASE'] if 'PROPUESTA BASE' in row_amb else "Punto de Atención"
                folium.Marker(
                    location=[lat, lon],
                    icon=folium.Icon(color="blue", icon="plus"),
                    tooltip=f"🚑 Ambulancia: {p_base}"
                ).add_to(m)

        for idx, row_hosp in df_hospitales.iterrows():
            if localidad_foco != "📍 MOSTRAR TODAS LAS LOCALIDADES" and row_hosp['LOCALIDAD'] != localidad_foco:
                continue
            lat, lon = row_hosp['LATITUD'], row_hosp['LONGITUD']
            if pd.notna(lat) and pd.notna(lon):
                nombre_ips = row_hosp[[c for c in df_hospitales.columns if 'NOMBRE' in c][0]]
                comp = row_hosp[[c for c in df_hospitales.columns if 'COMPLEJIDAD' in c][0]]
                direc = row_hosp[[c for c in df_hospitales.columns if 'DIRECCIÓN' in c or 'DIRECCION' in c][0]]
                
                folium.Marker(
                    location=[lat, lon],
                    icon=folium.Icon(color="red", icon="briefcase"), 
                    popup=f"<b>IPS:</b> {nombre_ips}<br><b>Dirección:</b> {direc}<br><b>Complejidad:</b> {comp}",
                    tooltip=f"🏥 Centro Médico: {nombre_ips}"
                ).add_to(m)

        components.html(m._repr_html_(), height=550, scrolling=False)
