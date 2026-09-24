import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Configuración visual de la página en Streamlit
st.set_page_config(
    page_title="Tablero de Control de Cartera y Cobranzas",
    page_icon="💼",
    layout="wide"
)

# ------------------------------------------------------------------------------
# 1. CARGA Y PREPARACIÓN DE DATOS CON CACHÉ
# ------------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_excel('Dataset_Integrado_Final_Sesion4.xlsx', sheet_name='Consolidado_Multiarea')
        
        # Limpiar espacios invisibles al inicio y final de los encabezados
        df.columns = df.columns.astype(str).str.strip()
        
        # Formato de fecha
        if 'Fecha_Operacion' in df.columns:
            df['Fecha_Operacion'] = pd.to_datetime(df['Fecha_Operacion'], errors='coerce')
        
        # Cálculo de Monto Cobrado según el estado
        if 'Monto_Neto_Cobrado_USD' not in df.columns:
            if 'Estado_Cobranza' in df.columns and 'Monto_Facturado_USD' in df.columns:
                df['Monto_Neto_Cobrado_USD'] = np.where(
                    df['Estado_Cobranza'] == 'Cobrado / Al Día',
                    df['Monto_Facturado_USD'],
                    0.0
                )
            else:
                df['Monto_Neto_Cobrado_USD'] = 0.0

        # Homologación del Margen Operativo / Neto
        if 'Margen_Operativo_USD' not in df.columns:
            if 'Margen_Neto_USD' in df.columns:
                df['Margen_Operativo_USD'] = df['Margen_Neto_USD']
            elif 'Monto_Facturado_USD' in df.columns and 'Costo_Transaccional_USD' in df.columns:
                df['Margen_Operativo_USD'] = df['Monto_Facturado_USD'] - df['Costo_Transaccional_USD']
            else:
                df['Margen_Operativo_USD'] = 0.0

        return df

    except Exception as e:
        st.error(f"❌ Error al cargar el archivo Excel: {e}")
        return pd.DataFrame()

df = cargar_datos()

if df.empty:
    st.warning("No se pudo cargar la información. Verifica que el archivo 'Dataset_Integrado_Final_Sesion4.xlsx' esté en la raíz del repositorio.")
    st.stop()

# ------------------------------------------------------------------------------
# 2. FILTROS GLOBALES (BARRA LATERAL)
# ------------------------------------------------------------------------------
st.sidebar.header("🎯 Filtros Globales")

def obtener_valores_unicos(col):
    if col in df.columns:
        return ['Todos'] + sorted(df[col].dropna().unique().tolist())
    return ['Todos']

paises = obtener_valores_unicos('Pais_Sede')
canales = obtener_valores_unicos('Canal')
tiers = obtener_valores_unicos('Tier_Estrategico')
estados = obtener_valores_unicos('Estado_Cobranza')

filtro_pais = st.sidebar.selectbox('País Sede:', paises)
filtro_canal = st.sidebar.selectbox('Canal de Venta:', canales)
filtro_tier = st.sidebar.selectbox('Tier Estratégico:', tiers)
filtro_estado = st.sidebar.selectbox('Estado de Cobranza:', estados)

# Filtrado reactivo de datos
dff = df.copy()
if filtro_pais != 'Todos' and 'Pais_Sede' in dff.columns:
    dff = dff[dff['Pais_Sede'] == filtro_pais]
if filtro_canal != 'Todos' and 'Canal' in dff.columns:
    dff = dff[dff['Canal'] == filtro_canal]
if filtro_tier != 'Todos' and 'Tier_Estrategico' in dff.columns:
    dff = dff[dff['Tier_Estrategico'] == filtro_tier]
if filtro_estado != 'Todos' and 'Estado_Cobranza' in dff.columns:
    dff = dff[dff['Estado_Cobranza'] == filtro_estado]

st.title("💼 Tablero de Control de Cartera y Cobranzas")

if dff.empty:
    st.warning("⚠️ No hay transacciones que cumplan con la combinación de filtros seleccionada.")
    st.stop()

# ------------------------------------------------------------------------------
# 3. TARJETAS DE MÉTRICAS (KPIS)
# ------------------------------------------------------------------------------
total_fact = dff['Monto_Facturado_USD'].sum() if 'Monto_Facturado_USD' in dff.columns else 0.0
total_cobr = dff['Monto_Neto_Cobrado_USD'].sum() if 'Monto_Neto_Cobrado_USD' in dff.columns else 0.0

if 'Estado_Cobranza' in dff.columns and 'Monto_Facturado_USD' in dff.columns:
    total_mora = dff[dff['Estado_Cobranza'] != 'Cobrado / Al Día']['Monto_Facturado_USD'].sum()
else:
    total_mora = 0.0

margen_neto = dff['Margen_Operativo_USD'].sum() if 'Margen_Operativo_USD' in dff.columns else 0.0

pct_mora = (total_mora / total_fact * 100) if total_fact > 0 else 0
pct_cobrado = (total_cobr / total_fact * 100) if total_fact > 0 else 0
margen_pct = (margen_neto / total_fact * 100) if total_fact > 0 else 0

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(
        label="Facturación Total",
        value=f"${total_fact:,.2f}",
        delta=f"{len(dff)} transacciones",
        delta_color="off"
    )

with kpi2:
    st.metric(
        label="Cobrado Efectivo",
        value=f"${total_cobr:,.2f}",
        delta=f"{pct_cobrado:.1f}% efectividad"
    )

with kpi3:
    st.metric(
        label="Cartera en Mora",
        value=f"${total_mora:,.2f}",
        delta=f"{pct_mora:.1f}% en riesgo",
        delta_color="inverse"
    )

with kpi4:
    st.metric(
        label="Margen Operativo",
        value=f"{margen_pct:.1f}%",
        delta=f"${margen_neto:,.2f} neto"
    )

st.markdown("---")

# ------------------------------------------------------------------------------
# 4. GRÁFICOS DINÁMICOS E INTERACTIVOS (PLOTLY)
# ------------------------------------------------------------------------------
st.subheader("📈 Diagnóstico Visual del Portafolio")

g_fila1_col1, g_fila1_col2 = st.columns(2)
g_fila2_col1, g_fila2_col2 = st.columns(2)

colores_cob = {
    'Cobrado / Al Día': '#10B981',
    'Mora Leve (<30d)': '#F59E0B',
    'Mora Crítica (>30d)': '#EF4444'
}

# --- Gráfico 1: Barras Apiladas por Sector y Cobranza ---
with g_fila1_col1:
    if 'Sector_Industria' in dff.columns and 'Estado_Cobranza' in dff.columns:
        df_sec = dff.groupby(['Sector_Industria', 'Estado_Cobranza'], as_index=False)['Monto_Facturado_USD'].sum()
        
        fig1 = px.bar(
            df_sec,
            x='Sector_Industria',
            y='Monto_Facturado_USD',
            color='Estado_Cobranza',
            color_discrete_map=colores_cob,
            title='<b>1. Facturación por Sector Industrial y Cobro</b>',
            labels={'Monto_Facturado_USD': 'Monto Facturado ($)', 'Sector_Industria': 'Sector', 'Estado_Cobranza': 'Cobranza'}
        )
        fig1.update_layout(
            barmode='stack',
            xaxis_tickangle=-25,
            template='plotly_white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=40)
        )
        fig1.update_traces(
            hovertemplate="<b>%{x}</b><br>Estado: %{fullData.name}<br>Facturado: <b>$%{y:,.2f}</b><extra></extra>"
        )
        st.plotly_chart(fig1, use_container_width=True)

# --- Gráfico 2: Dona Interactiva por Tier ---
with g_fila1_col2:
    if 'Tier_Estrategico' in dff.columns:
        df_tier = dff.groupby('Tier_Estrategico', as_index=False)['Monto_Facturado_USD'].sum()
        
        fig2 = px.pie(
            df_tier,
            names='Tier_Estrategico',
            values='Monto_Facturado_USD',
            hole=0.48,
            title='<b>2. Participación por Tier de Cliente</b>',
            color_discrete_sequence=['#1E3A8A', '#0D9488', '#F59E0B', '#6366F1']
        )
        fig2.update_layout(
            template='plotly_white',
            margin=dict(l=20, r=20, t=50, b=20)
        )
        fig2.update_traces(
            textinfo='percent+label',
            hovertemplate="<b>%{label}</b><br>Facturación: <b>$%{value:,.2f}</b><br>Participación: <b>%{percent}</b><extra></extra>"
        )
        st.plotly_chart(fig2, use_container_width=True)

# --- Gráfico 3: Boxplot Interactivo de Días de Mora ---
with g_fila2_col1:
    if 'Sector_Industria' in dff.columns and 'Dias_Mora' in dff.columns:
        fig3 = px.box(
            dff,
            x='Sector_Industria',
            y='Dias_Mora',
            points="outliers",
            color_discrete_sequence=['#3B82F6'],
            title='<b>3. Auditoría de Mora por Sector</b>',
            labels={'Dias_Mora': 'Días de Mora', 'Sector_Industria': 'Sector'}
        )
        fig3.update_layout(
            xaxis_tickangle=-25,
            template='plotly_white',
            margin=dict(l=20, r=20, t=50, b=40)
        )
        fig3.update_traces(
            hovertemplate="Sector: <b>%{x}</b><br>Días de Mora: <b>%{y} días</b><extra></extra>"
        )
        st.plotly_chart(fig3, use_container_width=True)

# --- Gráfico 4: Barras Horizontales por KAM ---
with g_fila2_col2:
    if 'Ejecutivo_KAM' in dff.columns:
        df_kam = dff.groupby('Ejecutivo_KAM', as_index=False)['Monto_Facturado_USD'].sum()
        df_kam['Monto_kUSD'] = df_kam['Monto_Facturado_USD'] / 1000
        df_kam = df_kam.sort_values(by='Monto_kUSD', ascending=True)

        fig4 = px.bar(
            df_kam,
            x='Monto_kUSD',
            y='Ejecutivo_KAM',
            orientation='h',
            color_discrete_sequence=['#0D9488'],
            title='<b>4. Cartera Total por KAM ($k USD)</b>',
            labels={'Monto_kUSD': 'Miles de USD ($k)', 'Ejecutivo_KAM': 'Ejecutivo KAM'}
        )
        fig4.update_layout(
            template='plotly_white',
            margin=dict(l=20, r=20, t=50, b=40)
        )
        fig4.update_traces(
            hovertemplate="KAM: <b>%{y}</b><br>Cartera: <b>$%{x:,.1f}k USD</b><extra></extra>"
        )
        st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ------------------------------------------------------------------------------
# 5. CONSTRUCTOR DINÁMICO DE TABLA DINÁMICA (PIVOT TABLE)
# ------------------------------------------------------------------------------
st.subheader("📊 Constructor Dinámico de Matriz")

posibles_filas = [c for c in ['Sector_Industria', 'Pais_Sede', 'Ejecutivo_KAM', 'Canal', 'Metodo_Pago', 'Tier_Estrategico'] if c in dff.columns]
posibles_columnas = [c for c in ['Estado_Cobranza', 'Tier_Estrategico', 'Canal', 'Pais_Sede'] if c in dff.columns]

mapa_metricas = {
    'Suma Facturación ($ USD)': ('Monto_Facturado_USD', 'sum', '${:,.2f}'),
    'Suma Margen Neto ($ USD)': ('Margen_Operativo_USD', 'sum', '${:,.2f}'),
    'Promedio Días de Mora': ('Dias_Mora', 'mean', '{:.1f} días'),
    'Conteo de Transacciones': ('ID_Transaccion', 'count', '{:,.0f}')
}

p_col1, p_col2, p_col3 = st.columns(3)

with p_col1:
    p_fila = st.selectbox('Variable en Filas:', posibles_filas, index=0 if posibles_filas else None)

with p_col2:
    idx_col = 1 if len(posibles_columnas) > 1 else 0
    p_col = st.selectbox('Variable en Columnas:', posibles_columnas, index=idx_col if posibles_columnas else None)

with p_col3:
    p_metrica = st.selectbox('Métrica a Calcular:', list(mapa_metricas.keys()), index=0)

if p_fila and p_col:
    if p_fila == p_col:
        st.warning("⚠️ Selecciona variables distintas para filas y columnas.")
    else:
        col_valor, funcion_agg, formato_num = mapa_metricas[p_metrica]

        tabla_pivot = pd.pivot_table(
            dff,
            index=p_fila,
            columns=p_col,
            values=col_valor,
            aggfunc=funcion_agg,
            fill_value=0,
            margins=True,
            margins_name='Total General'
        )

        st.dataframe(tabla_pivot.style.format(formato_num), use_container_width=True)
