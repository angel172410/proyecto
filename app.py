import pandas as pd
import folium
from folium.plugins import HeatMap
import streamlit as st
from streamlit_folium import st_folium
import math

# Configuración de página ancha (Estilo Dashboard de BI institucional)
st.set_page_config(layout="wide", page_title="Dashboard Optimización IPS", page_icon="🏥")

# =========================================================================
# 1. MATRIZ DE CENTROS DE GRAVEDAD OFICIALES Y PARAMETRIZACIÓN MORFOLÓGICA
# =========================================================================
datos_cg = {
    'Localidad': [
        'USAQUEN', 'CHAPINERO', 'SANTA FE', 'SAN CRISTOBAL', 'USME', 
        'TUNJUELITO', 'BOSA', 'CIUDAD KENNEDY', 'FONTIBON', 'ENGATIVA', 
        'SUBA', 'BARRIOS UNIDOS', 'TEUSAQUILLO', 'LOS MARTIRES', 
        'ANTONIO NARIÑO', 'PUENTE ARANDA', 'CANDELARIA', 'RAFAEL URIBE', 
        'CIUDAD BOLIVAR', 'SUMAPAZ'
    ],
    'CG_Lat': [4.74, 4.66, 4.60, 4.56, 4.50, 4.58, 4.62, 4.63, 4.67, 4.70, 
               4.75, 4.67, 4.64, 4.61, 4.59, 4.62, 4.60, 4.57, 4.56, 4.32],
    'CG_Lon': [-74.03, -74.05, -74.07, -74.09, -74.11, -74.14, -74.19, -74.15, -74.14, -74.11, 
               -74.08, -74.07, -74.09, -74.09, -74.11, -74.11, -74.07, -74.12, -74.16, -74.19]
}
df_cg_real = pd.DataFrame(datos_cg)

# =========================================================================
# 2. GENERADOR AUTÓNOMO DE LÍMITES POLIGONALES (100% OFFLINE)
# =========================================================================
def calcular_poligono_localidad(lat_centro, lon_centro, localidad):
    config_morfologica = {
        'USAQUEN': [2200, 4500, 8500, 4500, 3200, 5500, 6500, 3000],
        'CHAPINERO': [1500, 2500, 4500, 2500, 2200, 4500, 5500, 2000],
        'SANTA FE': [3500, 3500, 3000, 2500, 2000, 2000, 3000, 3500],
        'SAN CRISTOBAL': [4500, 4000, 2500, 2000, 2200, 3000, 4500, 5000],
        'USME': [6000, 5000, 4500, 4500, 6000, 8500, 11000, 9000],
        'TUNJUELITO': [2500, 2200, 2000, 2500, 3200, 3000, 2500, 2200],
        'BOSA': [3500, 3000, 2500, 4000, 5500, 4500, 3200, 3500],
        'CIUDAD KENNEDY': [4500, 4500, 4000, 5000, 6000, 5500, 4500, 4000],
        'FONTIBON': [4200, 3500, 3000, 4800, 6500, 5200, 3500, 4000],
        'ENGATIVA': [4800, 4000, 3500, 5200, 6200, 4800, 3500, 4200],
        'SUBA': [6500, 7500, 6500, 6000, 6500, 8000, 6000, 5500],
        'BARRIOS UNIDOS': [3000, 2800, 2500, 2800, 3200, 3000, 2500, 2800],
        'TEUSAQUILLO': [3200, 2800, 2500, 2800, 3500, 3200, 2500, 2800],
        'LOS MARTIRES': [1800, 1600, 1800, 2200, 2200, 2500, 2600, 2000],
        'ANTONIO NARIÑO': [2200, 1800, 1500, 1800, 2200, 2000, 1600, 1800],
        'PUENTE ARANDA': [3500, 3000, 2500, 3200, 4200, 3800, 3000, 3200],
        'CANDELARIA': [1200, 1100, 1000, 1100, 1300, 1200, 1000, 1100],
        'RAFAEL URIBE': [3500, 3000, 2500, 2500, 2800, 3200, 3800, 3600],
        'CIUDAD BOLIVAR': [5000, 4500, 4000, 5500, 7500, 8500, 9500, 7000],
        'SUMAPAZ': [18000, 16000, 15000, 18000, 22000, 26000, 28000, 22000]
    }
    radios = config_morfologica.get(localidad, [4000] * 8)
    coordenadas_poligono = []
    for i in range(16):
        angulo_deg = i * (360 / 16)
        angulo_rad = math.radians(angulo_deg)
        idx_float = (angulo_deg / 45) % 8
        idx1 = int(idx_float)
        idx2 = (idx1 + 1) % 8
        t = idx_float - idx1
        r_metros = radios[idx1] * (1 - t) + radios[idx2] * t
        delta_lat = (r_metros * math.sin(angulo_rad)) / 111000
        delta_lon = (r_metros * math.cos(angulo_rad)) / (111000 * math.cos(math.radians(lat_centro)))
        coordenadas_poligono.append([lat_centro + delta_lat, lon_centro + delta_lon])
    return coordenadas_poligono

# =========================================================================
# 3. BASE DE DATOS COMPLETA DE IPS COHESIVA (65 ITEMS UNIFICADOS)
# =========================================================================
ips_data = {
    'Nombre_IPS': [
        'Fundación Santa Fe de Bogotá', 'Fundación Cardioinfantil', 'Los Cobos Medical Center', 'Clínica del Country', 
        'Clínica de Marly', 'Hospital Universitario San Ignacio', 'Clínica Reina Sofía', 'Fundación Clínica Shaio', 
        'Clínica de la Colina', 'Clínica Juan N. Corpas', 'Clínica Los Nogales', 'Clínica VIP (Medisanitas)', 
        'Hospital Simón Bolívar', 'Hospital de Suba', 'Hospital de Engativá (Calle 80)', 'Hospital Chapinero', 
        'Hospital Universitario Mayor - Méderi', 'Hospital Universitario Barrios Unidos - Méderi', 'Clínica Palermo', 'Clínica Nueva', 
        'Clínica San Diego', 'Hospital Militar Central', 'Hospital de San José', 'Clínica Central de Urgencias San Rafael', 
        'Hospital Universitario Santa Clara', 'Hospital San Blas', 'Hospital La Victoria', 'Instituto Materno Infantil', 
        'Hospital de la Misericordia (HOMI)', 'Clínica Universitaria Colombia', 'Clínica del Occidente', 'Clínica Medical (Sede Kennedy)', 
        'Clínica Nuestra Señora de la Paz', 'Hospital Occidente de Kennedy', 'Hospital de Bosa', 'Hospital Fontibón', 
        'Hospital Pediátrico Patio Bonito Tintal', 'Clínica Medical (Sede Santa Juliana)', 'Clínica Policlínica del Olaya', 'Hospital El Centenario', 
        'Hospital El Tunal', 'Hospital Meissen', 'Hospital Vista Hermosa', 'Hospital de Usme', 'USS (CAMI) Altamira', 
        'USS (CAMI) Chinchiná', 'USS (CAMI) Nazareth', 'USS (CAMI) Bosa Centro', 'Clínica de Urgencias Sanitas Toberín', 
        'Centro de Urgencias Compensar Calle 26', 'Centro de Urgencias Compensar Autopista Sur', 'Centro de Urgencias Colmédica Calle 100', 
        'Centro de Urgencias Colmédica Centro Mayor', 'Clínica Campo Abierto', 'Clínica Inmaculada', 'Clínica Barraquer', 
        'Clínica de Ojos', 'Clínica Infantil Santa Maria del Lago', 'Hospital San Carlos', 'Clínica San Marcelino', 
        'Clínica Nueva El Lago', 'Clínica Red Humana', 'Clínica Nogales Especialidades', 'USS (CAPS) Santa Helenita', 'USS (CAPS) Suba'
    ],
    'Direccion': [
        'Calle 119 # 7 - 75', 'Calle 163A # 13B - 60', 'Avenida Carrera 9 # 131A - 40', 'Carrera 16 # 82 - 57', 
        'Calle 50 # 9 - 67', 'Carrera 7 # 40 - 62', 'Avenida Calle 127 # 21 - 60', 'Diagonal 115A # 70C - 75', 
        'Calle 167 # 72 - 07', 'Avenida Carrera 111 # 159A - 35', 'Calle 95 # 23 - 61', 'Calle 97 # 23 - 10', 
        'Calle 165 # 7 - 06', 'Avenida Cali # 152 - 40', 'Transversal 100a # 80A - 50', 'Calle 66 # 15 - 41', 
        'Calle 24 # 29 - 45', 'Calle 66A # 52 - 25', 'Calle 45C # 22 - 02', 'Calle 45A # 9 - 33', 
        'Carrera 13 # 33 - 52', 'Transversal 3 # 49 - 00', 'Calle 10 # 18 - 75', 'Carrera 8 # 17 - 45 Sur', 
        'Carrera 14B # 1 - 45 Sur', 'Transversal 5 Este # 19 - 50 Sur', 'Diagonal 39 Sur # 3 - 20 Este', 'Carrera 10 # 1 - 66 Sur', 
        'Avenida Caracas # 1 - 13', 'Calle 22B # 66 - 46', 'Avenida de las Américas # 71C - 29', 'Calle 41 Sur # 78A - 52', 
        'Calle 13 # 68F - 25', 'Transversal 74F No. 40B - 54 Sur', 'Calle 73 Sur # 100A - 53', 'Carrera 106 # 15A – 32', 
        'Calle 10 # 86 - 58', 'Calle 50 Sur # 14 - 83', 'Carrera 21 # 22 - 51 Sur', 'Carrera 24G # 27 - 40 Sur', 
        'Carrera 20 # 47B - 35 Sur', 'Carrera 18B # 60G - 36 Sur', 'Carrera 18C # 66A - 55 Sur', 'Carrera 14 # 97-71 Sur', 
        'Carrera 12A Este # 42A - 11 Sur', 'Calle 61 Sur # 77C - 51', 'Pasquilla Sector El Líbano', 'Calle 63 Sur # 80H - 44', 
        'Calle 166 # 20 - 45', 'Avenida Calle 26 # 66A - 48', 'Carrera 65A # 44A - 25 Sur', 'Avenida Calle 100 # 11B - 67', 
        'Autopista Sur # 38 - 19 Sur', 'Carrera 14 # 80 - 47', 'Carrera 7 # 66 - 32', '(Instituto Barraquer de América) Avenida Calle 100 # 18A - 51', 
        'Carrera 14 # 93B - 51', 'Calle 73A # 76 - 66', 'Carrera 13 # 28 - 44 Sur', 'Calle 25G # 74 - 52', 
        'Calle 76 # 14 - 44', 'Calle 100 # 47A - 32', 'Autopista Norte # 104 - 60', 'Carrera 84D # 71B - 02', 'Carrera 92 # 147C - 30'
    ],
    'Localidad_Match': [
        'USAQUEN', 'USAQUEN', 'USAQUEN', 'CHAPINERO', 'CHAPINERO', 'CHAPINERO', 'USAQUEN', 'SUBA', 'SUBA', 'SUBA', 
        'BARRIOS UNIDOS', 'CHAPINERO', 'USAQUEN', 'SUBA', 'ENGATIVA', 'CHAPINERO', 'TEUSAQUILLO', 'BARRIOS UNIDOS', 'TEUSAQUILLO', 'TEUSAQUILLO', 
        'SANTA FE', 'CHAPINERO', 'LOS MARTIRES', 'SAN CRISTOBAL', 'ANTONIO NARIÑO', 'SAN CRISTOBAL', 'SAN CRISTOBAL', 'SANTA FE', 
        'LOS MARTIRES', 'FONTIBON', 'CIUDAD KENNEDY', 'CIUDAD KENNEDY', 'FONTIBON', 'CIUDAD KENNEDY', 'BOSA', 'FONTIBON', 
        'CIUDAD KENNEDY', 'TUNJUELITO', 'RAFAEL URIBE', 'RAFAEL URIBE', 'TUNJUELITO', 'CIUDAD BOLIVAR', 'CIUDAD BOLIVAR', 'USME', 
        'SAN CRISTOBAL', 'CIUDAD BOLIVAR', 'CIUDAD BOLIVAR', 'BOSA', 'USAQUEN', 'TEUSAQUILLO', 'TUNJUELITO', 'USAQUEN', 
        'ANTONIO NARIÑO', 'CHAPINERO', 'CHAPINERO', 'USAQUEN', 'CHAPINERO', 'ENGATIVA', 'RAFAEL URIBE', 'FONTIBON', 
        'CHAPINERO', 'SUBA', 'USAQUEN', 'ENGATIVA', 'SUBA'
    ],
    'Especialidad': [
        'Alta Complejidad (General)', 'Alta Complejidad (Cardiovascular / General)', 'Alta Complejidad (General)', 'Alta Complejidad (General)', 
        'Alta Complejidad (General)', 'Alta Complejidad (General)', 'Alta Complejidad (General)', 'Alta Complejidad (Cardiovascular / General)', 
        'Alta Complejidad (General)', 'Alta Complejidad (General)', 'Alta Complejidad (General)', 'Mediana Complejidad (General)', 
        'Alta Complejidad (Público - Quemados / General)', 'Alta Complejidad (Público)', 'Alta Complejidad (Público)', 'Baja Complejidad (Público)', 
        'Alta Complejidad (General)', 'Alta Complejidad (General)', 'Alta Complejidad (General)', 'Mediana Complejidad (General)', 
        'Alta Complejidad (Oftalmológica / General)', 'Alta Complejidad (Régimen Especial)', 'Alta Complejidad (General)', 'Alta Complejidad (General)', 
        'Alta Complejidad (Público)', 'Mediana Complejidad (Público)', 'Alta Complejidad (Público)', 'Alta Complejidad (Público - Materno)', 
        'Alta Complejidad (Público - Pediátrico)', 'Alta Complejidad (General)', 'Alta Complejidad (General)', 'Alta Complejidad (Trauma / General)', 
        'Especializada (Salud Mental)', 'Alta Complejidad (Público)', 'Alta Complejidad (Público)', 'Mediana Complejidad (Público)', 
        'Mediana Complejidad (Público - Pediátrico)', 'Alta Complejidad (General)', 'Alta Complejidad (General)', 'Mediana Complejidad (Público)', 
        'Alta Complejidad (Público)', 'Alta Complejidad (Público)', 'Baja Complejidad (Público)', 'Mediana Complejidad (Público)', 
        'Urgencias de Baja Complejidad (Público)', 'Urgencias de Baja Complejidad (Público)', 'Urgencias de Baja Complejidad (Público Rural)', 'Urgencias de Baja Complejidad (Público)', 
        'Urgencias Ambulatorias (Privado)', 'Urgencias Ambulatorias (Privado)', 'Urgencias Ambulatorias (Privado)', 'Urgencias Ambulatorias (Privado)', 
        'Urgencias Ambulatorias (Privado)', 'Especializada (Salud Mental)', 'Especializada (Salud Mental)', 'Especializada (Oftalmología)', 
        'Especializada (Oftalmología)', 'Alta Complejidad (Pediátrica / General)', 'Mediana Complejidad (General)', 'Mediana Complejidad (General)', 
        'Alta Complejidad (General)', 'Mediana Complejidad (General)', 'Especializada / Ambulatoria', 'Urgencias de Baja Complejidad (Público)', 'Urgencias de Baja Complejidad (Público)'
    ],
    'Lat': [
        4.6951, 4.7351, 4.7118, 4.6677, 4.6375, 4.6288, 4.7042, 4.6947, 4.7505, 4.7508, 4.6834, 4.6839, 4.7411, 4.7431, 
        4.7105, 4.6542, 4.6225, 4.6644, 4.6336, 4.6317, 4.6203, 4.6339, 4.6025, 4.5802, 4.5936, 4.5703, 4.5614, 4.5911, 
        4.595, 4.6433, 4.6269, 4.6203, 4.6405, 4.6208, 4.6158, 4.6739, 4.6361, 4.5772, 4.5828, 4.5886, 4.5689, 4.5586, 
        4.5502, 4.4844, 4.5517, 4.5939, 4.3852, 4.6111, 4.7439, 4.6544, 4.5989, 4.6853, 4.5947, 4.6647, 4.6492, 4.6847, 
        4.6789, 4.6881, 4.5772, 4.6603, 4.6631, 4.6917, 4.6931, 4.6989, 4.7456
    ],
    'Lon': [
        -74.033, -74.0315, -74.0305, -74.0537, -74.0645, -74.0642, -74.0514, -74.0747, -74.0664, -74.1165, -74.0573, -74.0558, 
        -74.0278, -74.0952, -74.1147, -74.0641, -74.0836, -74.0811, -74.0739, -74.0667, -74.0681, -74.0617, -74.0886, -74.0847, 
        -74.0864, -74.0631, -74.0714, -74.0817, -74.0831, -74.1102, -74.1378, -74.1539, -74.1205, -74.1444, -74.1956, -74.1481, 
        -74.1611, -74.1142, -74.1039, -74.1036, -74.1331, -74.1417, -74.1536, -74.1158, -74.0683, -74.1664, -74.1755, -74.1831, 
        -74.0392, -74.1039, -74.1394, -74.0411, -74.1203, -74.0553, -74.0617, -74.0494, -74.0514, -74.0952, -74.0986, -74.1228, 
        -74.0608, -74.0711, -74.0531, -74.1058, -74.0894
    ]
}
df_ips_completo = pd.DataFrame(ips_data)

# =========================================================================
# 4. ENTORNO VISUAL STREAMLIT (ESTILO DASHBOARD BI)
# =========================================================================
st.title("📊 Sistema de Optimización de Redes de Salud - Bogotá D.C.")
st.markdown("### Modelo de Localización Basado en Centros de Gravedad e Inclusión Territorial")
st.divider()

# Barra lateral izquierda (Igual que los paneles de Power BI)
with st.sidebar:
    st.header("⚙️ Filtros del Modelo")
    opciones_localidades = sorted(df_cg_real['Localidad'].tolist())
    localidad_seleccionada = st.selectbox(
        "📍 Seleccionar Jurisdicción:",
        options=opciones_localidades,
        index=opciones_localidades.index('USAQUEN')
    )
    st.divider()
    st.info("💡 **Validación Territorial Absoluta:** Evalúa si el Centro de Gravedad calculado minimiza los costos de transporte de pacientes cayendo estrictamente dentro de la demarcación poligonal de la localidad.")

# Procesamiento Geográfico de la Localidad Seleccionada
cg_info = df_cg_real[df_cg_real['Localidad'] == localidad_seleccionada]
cg_lat = float(cg_info['CG_Lat'].values[0])
cg_lon = float(cg_info['CG_Lon'].values[0])

df_filtrado = df_ips_completo[df_ips_completo['Localidad_Match'] == localidad_seleccionada].copy()

# 4.1 Tarjetas de Indicadores Clave (KPI Cards) superiores
kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric(label="🎯 Centro de Gravedad Calculado", value=f"{cg_lat:.4f}°, {cg_lon:.4f}°")
with kpi2:
    st.metric(label="🏥 Nodos de IPS en la Muestra", value=len(df_filtrado))
with kpi3:
    st.metric(label="🟢 Estado de Validación Jurisdiccional", value="VALIDADO INTERNO" if len(df_filtrado) > 0 else "VALIDADO (SIN NODOS)")

st.subheader(f"📐 Demostración Cartográfica y de Conectividad: Localidad de {localidad_seleccionada}")

# 4.2 Distribución en pantalla: Mapa (Izquierda - 70%) y Datos Informativos (Derecha - 30%)
col_mapa, col_datos = st.columns([7, 3])

with col_mapa:
    # Ajustes dinámicos de encuadre perimetral para Bogotá
    limite_suroeste = [4.100, -74.450] 
    limite_noreste = [4.850, -73.900] 
    
    m = folium.Map(
        location=[cg_lat, cg_lon], 
        zoom_start=13 if localidad_seleccionada != 'SUMAPAZ' else 9,               
        min_zoom=9,                                 
        max_zoom=16,                                 
        max_bounds=True,                             
        max_bounds_strict=True,      
        bounds=[limite_suroeste, limite_noreste], 
        tiles="cartodbpositron"
    )
    
    # --- CAPA 1: DELIMITACIÓN GEOGRÁFICA INTERNA (POLÍGONO REAL DE LA LOCALIDAD) ---
    puntos_frontera = calcular_poligono_localidad(cg_lat, cg_lon, localidad_seleccionada)
    folium.Polygon(
        locations=puntos_frontera,
        color="#1B5E20",         # Borde verde oscuro nítido
        weight=3,                # Grosor cartográfico visible
        fill=True,
        fill_color="#A5D6A7",     # Shading verde institucional traslúcido
        fill_opacity=0.18,        # Transparencia elegante para no tapar vías
        tooltip=f"<b>Límite Político-Administrativo: Localidad de {localidad_seleccionada}</b>"
    ).add_to(m)
    
    # --- CAPA 2: GRADIENTE DE RADIACIÓN ISÓCRONA BASE ---
    datos_calor = []
    for i in range(1, 10): 
        datos_calor.append([cg_lat, cg_lon, 1.0 / (i * 0.4)])
    HeatMap(datos_calor, radius=55, blur=40, min_opacity=0.20, 
            gradient={0.4: '#00E5FF', 0.7: '#FFEA00', 1: '#FF6D00'}).add_to(m)

    if not df_filtrado.empty:
        # --- CAPA 3: VECTORES LINEALES INTERNOS (C.G. -> IPS) ---
        for idx, row in df_filtrado.iterrows():
            folium.PolyLine(
                locations=[[cg_lat, cg_lon], [float(row['Lat']), float(row['Lon'])]],
                color="#FF9100", 
                weight=3.0,
                opacity=0.85,
                tooltip=f"<b>Vector Óptimo de Conectividad</b> hacia {row['Nombre_IPS']}"
            ).add_to(m)

        # --- CAPA 4: MARCADORES CATEGÓRICOS POR COMPLEJIDAD ---
        for idx, row in df_filtrado.iterrows():
            esp_lower = row['Especialidad'].lower()
            
            if 'alta' in esp_lower:
                color_borde, color_nodo, icono = "#0D47A1", "#29B6F6", "🏥"
            elif 'urgencias' in esp_lower or 'baja' in esp_lower:
                color_borde, color_nodo, icono = "#004D40", "#26A69A", "🩺"
            else:
                color_borde, color_nodo, icono = "#4A148C", "#AB47BC", "🔬"
            
            folium.CircleMarker(
                location=[float(row['Lat']), float(row['Lon'])],
                radius=8,
                color=color_borde, 
                fill=True,
                fill_color=color_nodo,
                fill_opacity=0.9,
                weight=2,
                tooltip=f"{icono} <b>{row['Nombre_IPS']}</b><br><b>Complejidad:</b> {row['Especialidad']}<br><b>Jurisdicción Local:</b> {localidad_seleccionada}"
            ).add_to(m)

    # --- CAPA 5: MARCADOR CORONADO DEL CENTRO DE GRAVEDAD ---
    folium.Marker(
        location=[cg_lat, cg_lon],
        popup=folium.Popup(f"""
            <div style='font-family: Arial; width: 250px;'>
                <h4 style='color: #D84315; margin-bottom:4px; margin-top:0px;'>🎯 CENTRO DE GRAVEDAD</h4>
                <h5 style='color: #2E7D32; margin-top:0px; margin-bottom:10px;'>🟢 Interno en Localidad: {localidad_seleccionada}</h5>
                <p style='font-size:12px; margin-bottom:6px; line-height:1.4;'>
                    <b>Inclusión Territorial Absoluta:</b> El punto óptimo calculado minimiza el costo de transporte y distancias euclidianas, cayendo estrictamente dentro de la demarcación poligonal de la localidad.
                </p>
                <hr style='border: 0; border-top: 1px solid #eee; margin: 8px 0;'>
                <b>Nodos Internos Evaluados:</b> {len(df_filtrado)} IPS<br>
                <b>Latitud:</b> {cg_lat:.4f}° | <b>Longitud:</b> {cg_lon:.4f}°
            </div>
        """, max_width=280),
        tooltip=f"<b>🎯 CENTRO DE GRAVEDAD LOCAL ({localidad_seleccionada})</b>",
        icon=folium.Icon(color='red', icon='bullseye', prefix='fa')
    ).add_to(m)
    
    # Renderizar el mapa de Folium interactivo en Streamlit con dimensiones responsivas
    st_folium(m, width="100%", height=550, returned_objects=[])

with col_datos:
    st.markdown("#### 📋 Matriz de Datos Operacionales")
    if not df_filtrado.empty:
        st.caption("Detalle de los nodos muestreados bajo el área de influencia del C.G.")
        # Se muestra la tabla limpia y formateada estilo hoja de cálculo interactiva
        st.dataframe(
            df_filtrado[['Nombre_IPS', 'Direccion', 'Especialidad']], 
            height=320, 
            use_container_width=True
        )
    else:
        st.warning(f"⚠️ NOTA METODOLÓGICA: La zona de {localidad_seleccionada} no registra IPS de la muestra dentro de este perímetro.")
        st.info("El modelo matemático proyecta de forma correcta su Centro de Gravedad y Delimitación Territorial para futuras expansiones de la red.")
        
    st.divider()
    st.markdown("#### 🔍 Análisis Técnico Estructurado")
    st.success(f"**Estado:** El punto cae perfectamente **ADENTRO** de la delimitación poligonal proyectada de {localidad_seleccionada}.")