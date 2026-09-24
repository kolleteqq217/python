import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración visual de la aplicación
st.set_page_config(
    page_title="Tablero de Control de Cartera y Cobranzas",
    page_icon="💼",
    layout="wide"
)

# ------------------------------------------------------------------------------
# 1. CARGA Y PREPARACIÓN DE DATOS CON MANEJO DE ERRORES
# ------------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_excel('Dataset_Integrado_Final_Sesion4.xlsx', sheet_name='Consolidado_Multiarea')
        
        # Eliminar posibles espacios en blanco invisibles al inicio/fin de cada columna
        df.columns = df.columns.astype(str).str.strip()
        
        if 'Fecha_Operacion' in df.columns:
            df['Fecha_Operacion'] = pd.to_datetime(df['Fecha_Operacion'], errors='coerce')
            
        return df
    except Exception as e:
        st.error(f"❌ Error al cargar el archivo Excel: {e}")
        return pd.DataFrame()

df = cargar_datos()

if df.empty:
    st.info("Sube el archivo 'Dataset_Integrado_Final_Sesion4.xlsx' al repositorio de GitHub para visualizar los datos.")
    st.stop()

# ------------------------------------------------------------------------------
# 2. RESOLUCIÓN SEGURA DE NOMBRES DE COLUMNAS
# ------------------------------------------------------------------------------
# Función auxiliar para encontrar columnas aunque tengan ligeras variaciones de nombre
def buscar_columna(df, nombre_ideal, patrones_alternativos):
    if nombre_ideal in df.columns:
        return nombre_ideal
    for col in df.columns:
        for patron in patrones_alternativos:
            if patron.lower() in col.lower():
                return col
    return None

COL_FACTURADO = buscar_columna(df, 'Monto_Facturado_USD', ['facturad', 'factura', 'total_usd'])
COL_COBRADO = buscar_columna(df, 'Monto_Neto_Cobrado_USD', ['neto_cobr', 'monto_cobr', 'cobrado', 'recaudo'])
COL_MARGEN = buscar_columna(df, 'Margen_Operativo_USD', ['margen', 'utilidad', 'profit'])
COL_MORA = buscar_columna(df, 'Dias_Mora', ['dias_mora', 'mora', 'retraso'])

# Validación si no se encuentra la columna de Cobro
if not COL_COBRADO:
    st.error("⚠️ No se encontró la columna de Monto Cobrado en el archivo.")
    st.write("Columnas detectadas en tu hoja de Excel:", list(df.columns))
    st.stop()

# ------------------------------------------------------------------------------
# 3. FILTROS GLOBALES (SIDEBAR)
# ------------------------------------------------------------------------------
st.sidebar.header("🎯 Filtros Globales")

def obtener_opciones(columna):
    if columna in df.columns:
        return ['Todos'] + sorted(df[columna].dropna().unique().tolist())
    return ['Todos']

paises = obtener_opciones('Pais_Sede')
canales = obtener_opciones('Canal')
tiers = obtener_opciones('Tier_Estrategico')
estados = obtener_opciones('Estado_Cobranza')

filtro_pais = st.sidebar.selectbox('País Sede:', paises)
filtro_canal = st.sidebar.selectbox('Canal de Venta:', canales)
filtro_tier = st.sidebar.selectbox('Tier Estratégico:', tiers)
filtro_estado = st.sidebar.selectbox('Estado de Cobranza:', estados)

# Filtrado reactivo de la tabla
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
# 4. TARJETAS DE MÉTRICAS (KPIS)
# ------------------------------------------------------------------------------
total_fact = dff[COL_FACTURADO].sum() if COL_FACTURADO else 0
total_cobr = dff[COL_COBRADO].sum() if COL_COBRADO else 0

if 'Estado_Cobranza' in dff.columns and COL_FACTURADO:
    total_mora = dff[dff['Estado_Cobranza'] != 'Cobrado / Al Día'][COL_FACTURADO].sum()
else:
    total_mora = 0

margen_neto = dff[COL_MARGEN].sum() if COL_MARGEN else 0

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

st.divider()

# ------------------------------------------------------------------------------
# 5. DIAGNÓSTICO VISUAL (GRÁFICOS 2x2)
# ------------------------------------------------------------------------------
st.subheader("📈 Diagnóstico Visual del Portafolio")

fig, axs = plt.subplots(2, 2, figsize=(16, 9))
fig.patch.set_facecolor('#FFFFFF')
colores_cob = {
    'Cobrado / Al Día': '#10B981',
    'Mora Leve (<30d)': '#F59E0B',
    'Mora Crítica (>30d)': '#EF4444'
}

# [0, 0] Facturación por Sector y Cobranza
if 'Sector_Industria' in dff.columns and 'Estado_Cobranza' in dff.columns and COL_FACTURADO:
    df_sec = dff.groupby(['Sector_Industria', 'Estado_Cobranza'])[COL_FACTURADO].sum().unstack().fillna(0)
    cols_exist = [c for c in ['Cobrado / Al Día', 'Mora Leve (<30d)', 'Mora Crítica (>30d)'] if c in df_sec.columns]
    df_sec = df_sec[cols_exist] if cols_exist else df_sec
    df_sec.plot(kind='bar', stacked=True, ax=axs[0, 0], color=[colores_cob.get(c, '#64748B') for c in df_sec.columns])
    axs[0, 0].set_title('1. Facturación por Sector Industrial y Cobro', fontweight='bold', fontsize=11, color='#0F172A')
    axs[0, 0].tick_params(axis='x', rotation=18)
    axs[0, 0].spines[['top', 'right']].set_visible(False)

# [0, 1] Participación por Tier
if 'Tier_Estrategico' in dff.columns and COL_FACTURADO:
    df_tier = dff.groupby('Tier_Estrategico')[COL_FACTURADO].sum()
    axs[0, 1].pie(df_tier, labels=df_tier.index, autopct='%1.1f%%', colors=['#1E3A8A', '#0D9488', '#F59E0B'],
                  wedgeprops=dict(width=0.45, edgecolor='w'))
    axs[0, 1].set_title('2. Participación por Tier de Cliente', fontweight='bold', fontsize=11, color='#0F172A')

# [1, 0] Días de Mora por Sector
if 'Sector_Industria' in dff.columns and COL_MORA:
    if len(dff) < 4:
        axs[1, 0].bar(dff['Sector_Industria'], dff[COL_MORA], color='#EF4444', width=0.35)
        axs[1, 0].set_ylabel('Días de Mora')
    else:
        sns.boxplot(data=dff, x='Sector_Industria', y=COL_MORA, ax=axs[1, 0], palette='Blues')
        axs[1, 0].tick_params(axis='x', rotation=18)
    axs[1, 0].set_title('3. Auditoría de Mora por Sector', fontweight='bold', fontsize=11, color='#0F172A')
    axs[1, 0].spines[['top', 'right']].set_visible(False)

# [1, 1] Cartera por KAM
if 'Ejecutivo_KAM' in dff.columns and COL_FACTURADO:
    df_kam = dff.groupby('Ejecutivo_KAM')[COL_FACTURADO].sum()
    axs[1, 1].barh(df_kam.index, df_kam.values / 1000, color='#0D9488', height=0.45)
    axs[1, 1].set_title('4. Cartera Total por KAM ($k USD)', fontweight='bold', fontsize=11, color='#0F172A')
    axs[1, 1].set_xlabel('Miles de USD ($k)')
    axs[1, 1].spines[['top', 'right']].set_visible(False)

plt.tight_layout(pad=2.8)
st.pyplot(fig)

st.divider()

# ------------------------------------------------------------------------------
# 6. CONSTRUCTOR DE TABLA DINÁMICA
# ------------------------------------------------------------------------------
st.subheader("📊 Constructor Dinámico de Matriz")

posibles_filas = [c for c in ['Sector_Industria', 'Pais_Sede', 'Ejecutivo_KAM', 'Canal', 'Metodo_Pago', 'Tier_Estrategico'] if c in dff.columns]
posibles_columnas = [c for c in ['Estado_Cobranza', 'Tier_Estrategico', 'Canal', 'Pais_Sede'] if c in dff.columns]

opciones_metricas = {
    'Suma Facturación ($ USD)': (COL_FACTURADO, 'sum', '${:,.2f}'),
    'Suma Margen Neto ($ USD)': (COL_MARGEN, 'sum', '${:,.2f}'),
    'Promedio Días de Mora': (COL_MORA, 'mean', '{:.1f} días'),
    'Conteo de Transacciones': (dff.columns[0], 'count', '{:,.0f}')
}

# Filtrar sólo métricas cuyas columnas existen
metricas_validas = {k: v for k, v in opciones_metricas.items() if v[0] is not None}

col_sel1, col_sel2, col_sel3 = st.columns(3)

with col_sel1:
    p_fila = st.selectbox('Variable en Filas:', posibles_filas, index=0 if posibles_filas else None)

with col_sel2:
    idx_col = 1 if len(posibles_columnas) > 1 else 0
    p_col = st.selectbox('Variable en Columnas:', posibles_columnas, index=idx_col if posibles_columnas else None)

with col_sel3:
    p_metrica = st.selectbox('Métrica a Calcular:', list(metricas_validas.keys()), index=0)

if p_fila and p_col:
    if p_fila == p_col:
        st.warning("⚠️ Selecciona variables distintas para filas y columnas.")
    else:
        col_valor, funcion_agg, formato_num = metricas_validas[p_metrica]

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
