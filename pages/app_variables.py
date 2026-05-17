import pandas as pd
import folium
import streamlit as st
import streamlit.components.v1 as components
import os

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
# CONFIGURACIÓN DE RUTAS RELATIVAS (Optimizado para GitHub y Streamlit Cloud)
# =========================================================================
# Reemplazamos la ruta estática C:\... por el archivo raíz del repositorio
RUTA_CSV = "historico_real_completo-F2.csv"

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
    Carga el dataset de 466k filas segmentado por punto y coma, extrae variables
    temporales y calcula la tasa de incidentes por hora para la simulación.
    """
    if not os.path.exists(ruta):
        return None, 0
    
    # Leer el archivo con codificación Latin1 para soportar eñes y tildes de Windows
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
        
    # Limpieza de la columna localidad
    if 'LOCALIDAD' in df.columns:
        df['LOCALIDAD'] = df['LOCALIDAD'].astype(str).str.upper().str.strip()
    
    # Agrupación y cálculo del promedio analítico por semana (Asumiendo 52 semanas del año)
    conteo = df.groupby(['DIA_PROCESADO', 'HORA_PROCESADA', 'LOCALIDAD']).size().reset_index(name='Total_Casos')
    conteo['Incidentes_Proyectados'] = (conteo['Total_Casos'] / 52).round(1)
    
    return conteo, total_registros

# Ejecutar la carga y procesamiento inicial indexado en caché
with st.spinner("🔄 Procesando base de datos histórica... Por favor espere."):
    df_modelo, total_filas_reales = cargar_y_procesar_historico(RUTA_CSV)

# =========================================================================
# 2. INTERFAZ GRÁFICA DE USUARIO (STREAMLIT)
# =========================================================================
st.title("🔮 Simulador Predictivo Basado en Evidencia Histórica Real")
st.markdown("### Proyección Espacio-Temporal con Motor de Densidad entrenado directamente desde tu Base de Datos")
st.divider()

if df_modelo is None:
    st.error(f"❌ No se encontró el archivo CSV en el repositorio: `{RUTA_CSV}`")
else:
    # Barra Lateral: Controles temporales de la simulación
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
        st.markdown("### 🚦 Umbral de Carga Operacional")
        st.markdown("🔴 **Carga Crítica:** Superior al promedio esperado en hora pico")
        st.markdown("🟡 **Carga Moderada:** Comportamiento estándar estable")
        st.markdown("🟢 **Carga Baja:** Densidad mínima de llamadas")
        st.divider()
        st.success(f"📂 Dataset conectado con éxito.")

    # Filtrado del espacio temporal seleccionado
    df_filtrado = df_modelo[(df_modelo['DIA_PROCESADO'] == input_dia) & (df_modelo['HORA_PROCESADA'] == input_hora)]
    df_resultados = pd.merge(df_coor, df_filtrado, on='LOCALIDAD', how='left').fillna(0)
    
    # Obtener el valor máximo global de esta hora para mantener la escala visual fija
    max_casos_global = df_resultados['Incidentes_Proyectados'].max()
    umbral_rojo = max_casos_global * 0.70 if max_casos_global > 0 else 5
    umbral_amarillo = max_casos_global * 0.35 if max_casos_global > 0 else 2

    # 2.1 Tarjetas de Indicadores Estadísticos Dinámicos (KPI Cards)
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
        localidades_criticas = len(df_resultados[df_resultados['Incidentes_Proyectados'] >= umbral_rojo]) if max_casos_global > 0 else 0
        st.metric(label="🔴 Sectores en Saturación Inminente", value=f"{localidades_criticas} de 20")

    st.divider()

    # 2.2 Distribución del Tablero (Mapa Izquierda, Tabla Detallada Derecha)
    col_mapa, col_tabla = st.columns([6, 4])

    # PROCESAMOS PRIMERO LA COLUMNA DE LA DERECHA PARA PASAR EL PUNTO FOCAL AL MAPA
    with col_tabla:
        st.markdown("#### 🎯 Selector de Punto Focal Analítico")
        
        # Lista de opciones para el selector de foco (Todas + las localidades del archivo)
        opciones_foco = ["📍 MOSTRAR TODAS LAS LOCALIDADES"] + sorted(df_resultados['LOCALIDAD'].tolist())
        
        localidad_foco = st.selectbox(
            "Seleccione una localidad específica para aislar su resultado en el mapa:",
            options=opciones_foco
        )
        
        st.markdown("---")
        st.markdown("#### 📋 Densidad de Incidentes por Hora")
        st.caption("Frecuencia matemática calculada mediante agregación estructurada.")
        
        # Preparar la tabla detallada
        df_tabla = df_resultados[['LOCALIDAD', 'Incidentes_Proyectados']].copy()
        df_tabla.columns = ['Localidad', 'Incidentes Esperados (Casos/Hora)']
        
        st.dataframe(
            df_tabla.sort_values(by='Incidentes Esperados (Casos/Hora)', ascending=False),
            height=350,
            use_container_width=True,
            hide_index=True
        )

    # AHORA CONSTRUIMOS EL MAPA BASADO EN LA SELECCIÓN DEL PUNTO FOCAL
    with col_mapa:
        st.subheader(f"📌 Densidad de Emergencias Proyectada: {input_dia} a las {input_hora}:00 hs")
        
        # --- LÓGICA DE APUNTADO / CENTRADO DINÁMICO ---
        # Si el usuario elige una localidad, extraemos su latitud y longitud asignadas para mover el visor allí
        if localidad_foco != "📍 MOSTRAR TODAS LAS LOCALIDADES":
            row_foco = df_resultados[df_resultados['LOCALIDAD'] == localidad_foco].iloc[0]
            centro_mapa = [row_foco['Lat'], row_foco['Lon']]
            zoom_inicial = 13  # Zoom de aproximación para la localidad seleccionada
        else:
            centro_mapa = [4.640, -74.100]  # Coordenadas generales de Bogotá
            zoom_inicial = 11

        m = folium.Map(location=centro_mapa, zoom_start=zoom_inicial, tiles="cartodbpositron")
        
        # Dibujar las burbujas aplicando la lógica de semáforo
        for idx, row in df_resultados.iterrows():
            # Si hay un foco seleccionado y la fila actual no coincide, se oculta del mapa para aislar el resultado
            if localidad_foco != "📍 MOSTRAR TODAS LAS LOCALIDADES" and row['LOCALIDAD'] != localidad_foco:
                continue
                
            casos = row['Incidentes_Proyectados']
            
            if casos >= umbral_rojo and casos > 0:
                color_semaforo = "#e63946"  # Rojo
                alerta_txt = "CRÍTICA (ALTA DENSIDAD)"
            elif casos >= umbral_amarillo and casos > 0:
                color_semaforo = "#ffb703"  # Amarillo
                alerta_txt = "MODERADA"
            else:
                color_semaforo = "#2a9d8f"  # Verde
                alerta_txt = "BAJA / BAJO RIESGO"

            # Factor de escala visual dinámico para los radios
            radio_visual = (casos / (max_casos_global if max_casos_global > 0 else 1)) * 2500
            radio_visual = max(radio_visual, 150) # Evita círculos invisibles de valor 0

            folium.Circle(
                location=[row['Lat'], row['Lon']],
                radius=radio_visual,
                color=color_semaforo,
                fill=True,
                fill_color=color_semaforo,
                fill_opacity=0.6,
                weight=1.5,
                tooltip=f"<b>Localidad: {row['LOCALIDAD']}</b><br>"
                        f"Proyección: <b>{casos} incidentes/hora</b><br>"
                        f"Estado: <span style='color:{color_semaforo}'><b>{alerta_txt}</b></span>"
            ).add_to(m)
            
        # Renderizar mapa configurando el width al 100% para evitar que se fracture el diseño ancho
        components.html(m._repr_html_(), height=550, width="100%", scrolling=False)
