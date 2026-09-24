import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de página ancha para dashboards ejecutivos
st.set_page_config(
    page_title="Dashboard de Gestión Multiarea",
    page_icon="📊",
    layout="wide"
)

# ------------------------------------------------------------------------------
# 1. CARGA Y CACHÉ DE DATOS
# ------------------------------------------------------------------------------
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_excel('Dataset_Integrado_Final_Sesion4.xlsx', sheet_name='Consolidado_Multiarea')
        df['Fecha_Operacion'] = pd.to_datetime(df['Fecha_Operacion'])
        return df
    except Exception as e:
        st.error(f"Error al cargar el archivo de datos: {e}")
        return pd.DataFrame()

df = cargar_datos()

if df.empty:
    st.stop()

# ------------------------------------------------------------------------------
# 2. FILTROS GLOBALES (Barra Lateral)
# ------------------------------------------------------------------------------
st.sidebar.header("🎯 Filtros Globales")

paises = ['Todos'] + sorted(df['Pais_Sede'].dropna().unique().tolist())
canales = ['Todos'] + sorted(df['Canal'].dropna().unique().tolist())
tiers = ['Todos'] + sorted(df['Tier_Estrategico'].dropna().unique().tolist())
estados = ['Todos'] + sorted(df['Estado_Cobranza'].dropna().unique().tolist())

filtro_pais = st.sidebar.selectbox('País Sede:', paises)
filtro_canal = st.sidebar.selectbox('Canal de Venta:', canales)
filtro_tier = st.sidebar.selectbox('Tier Estratégico:', tiers)
filtro_estado = st.sidebar.selectbox('Estado de Cobranza:', estados)

# Filtrado reactivo del DataFrame
dff = df.copy()
if filtro_pais != 'Todos':
    dff = dff[dff['Pais_Sede'] == filtro_pais]
if filtro_canal != 'Todos':
    dff = dff[dff['Canal'] == filtro_canal]
if filtro_tier != 'Todos':
    dff = dff[dff['Tier_Estrategico'] == filtro_tier]
if filtro_estado != 'Todos':
    dff = dff[dff['Estado_Cobranza'] == filtro_estado]

# Título Principal
st.title("💼 Tablero de Control de Cartera y Cobranzas")

if dff.empty:
    st.warning("⚠️ No hay transacciones que cumplan con la combinación de filtros seleccionada.")
    st.stop()

# ------------------------------------------------------------------------------
# 3. TARJETAS KPI (Métricas Ejecutivas)
# ------------------------------------------------------------------------------
total_fact = dff['Monto_Facturado_USD'].sum()
total_cobr = dff['Monto_Neto_Cobrado_USD'].sum()
total_mora = dff[dff['Estado_Cobranza'] != 'Cobrado / Al Día']['Monto_Facturado_USD'].sum()
margen_neto = dff['Margen_Operativo_USD'].sum()

pct_mora = (total_mora / total_fact * 100) if total_fact > 0 else 0
pct_cobrado = (total_cobr / total_fact * 100) if total_fact > 0 else 0
margen_pct = (margen_neto / total_fact * 100) if total_fact > 0 else 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Facturación Total",
        value=f"${total_fact:,.2f}",
        delta=f"{len(dff)} transacciones",
        delta_color="off"
    )

with col2:
    st.metric(
        label="Cobrado Efectivo",
        value=f"${total_cobr:,.2f}",
        delta=f"{pct_cobrado:.1f}% efectividad"
    )

with col3:
    st.metric(
        label="Cartera en Mora",
        value=f"${total_mora:,.2f}",
        delta=f"{pct_mora:.1f}% en riesgo",
        delta_color="inverse"
    )

with col4:
    st.metric(
        label="Margen Operativo",
        value=f"{margen_pct:.1f}%",
        delta=f"${margen_neto:,.2f} neto"
    )

st.markdown("---")

# ------------------------------------------------------------------------------
# 4. GRÁFICOS VISUALES 2x2
# ------------------------------------------------------------------------------
st.subheader("📈 Diagnóstico Visual del Portafolio")

fig, axs = plt.subplots(2, 2, figsize=(16, 9))
fig.patch.set_facecolor('#FFFFFF')
colores_cob = {'Cobrado / Al Día': '#10B981', 'Mora Leve (<30d)': '#F59E0B', 'Mora Crítica (>30d)': '#EF4444'}

# [0, 0] Facturación por Sector y Cobranza
df_sec = dff.groupby(['Sector_Industria', 'Estado_Cobranza'])['Monto_Facturado_USD'].sum().unstack().fillna(0)
cols_exist = [c for c in ['Cobrado / Al Día', 'Mora Leve (<30d)', 'Mora Crítica (>30d)'] if c in df_sec.columns]
df_sec = df_sec[cols_exist] if cols_exist else df_sec
df_sec.plot(kind='bar', stacked=True, ax=axs[0, 0], color=[colores_cob.get(c, '#64748B') for c in df_sec.columns])
axs[0, 0].set_title('1. Facturación por Sector Industrial y Cobro', fontweight='bold', fontsize=11, color='#0F172A')
axs[0, 0].tick_params(axis='x', rotation=18)
axs[0, 0].spines[['top', 'right']].set_visible(False)

# [0, 1] Dona por Tier
df_tier = dff.groupby('Tier_Estrategico')['Monto_Facturado_USD'].sum()
axs[0, 1].pie(df_tier, labels=df_tier.index, autopct='%1.1f%%', colors=['#1E3A8A', '#0D9488', '#F59E0B'],
              wedgeprops=dict(width=0.45, edgecolor='w'))
axs[0, 1].set_title('2. Participación por Tier de Cliente', fontweight='bold', fontsize=11, color='#0F172A')

# [1, 0] Días de Mora
if len(dff) < 4:
    axs[1, 0].bar(dff['Sector_Industria'], dff['Dias_Mora'], color='#EF4444', width=0.35)
    axs[1, 0].set_ylabel('Días de Mora')
else:
    sns.boxplot(data=dff, x='Sector_Industria', y='Dias_Mora', ax=axs[1, 0], palette='Blues')
    axs[1, 0].tick_params(axis='x', rotation=18)
axs[1, 0].set_title('3. Auditoría de Mora por Sector', fontweight='bold', fontsize=11, color='#0F172A')
axs[1, 0].spines[['top', 'right']].set_visible(False)

# [1, 1] Cartera por KAM
df_kam = dff.groupby('Ejecutivo_KAM')['Monto_Facturado_USD'].sum()
axs[1, 1].barh(df_kam.index, df_kam.values / 1000, color='#0D9488', height=0.45)
axs[1, 1].set_title('4. Cartera Total por KAM ($k USD)', fontweight='bold', fontsize=11, color='#0F172A')
axs[1, 1].set_xlabel('Miles de USD ($k)')
axs[1, 1].spines[['top', 'right']].set_visible(False)

plt.tight_layout(pad=2.8)
st.pyplot(fig)

st.markdown("---")

# ------------------------------------------------------------------------------
# 5. TABLA DINÁMICA INTERACTIVA (PIVOT TABLE)
# ------------------------------------------------------------------------------
st.subheader("📊 Constructor Dinámico de Matriz")

opciones_filas = ['Sector_Industria', 'Pais_Sede', 'Ejecutivo_KAM', 'Canal', 'Metodo_Pago', 'Tier_Estrategico']
opciones_columnas = ['Estado_Cobranza', 'Tier_Estrategico', 'Canal', 'Pais_Sede']
opciones_metricas = [
    'Suma Facturación ($ USD)',
    'Suma Margen Neto ($ USD)',
    'Promedio Días de Mora',
    'Conteo de Transacciones'
]

p_col1, p_col2, p_col3 = st.columns(3)
with p_col1:
    p_fila = st.selectbox('Variable en Filas:', opciones_filas, index=0)
with p_col2:
    p_col = st.selectbox('Variable en Columnas:', opciones_columnas, index=0)
with p_col3:
    p_metrica = st.selectbox('Métrica a Calcular:', opciones_metricas, index=0)

if p_fila == p_col:
    st.warning("⚠️ Selecciona variables distintas para filas y columnas.")
else:
    mapa_metricas = {
        'Suma Facturación ($ USD)': ('Monto_Facturado_USD', 'sum', '${:,.2f}'),
        'Suma Margen Neto ($ USD)': ('Margen_Operativo_USD', 'sum', '${:,.2f}'),
        'Promedio Días de Mora': ('Dias_Mora', 'mean', '{:.1f} días'),
        'Conteo de Transacciones': ('ID_Transaccion', 'count', '{:,.0f}')
    }
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

    estilo_pivot = tabla_pivot.style.format(formato_num)
    st.dataframe(estilo_pivot, use_container_width=True)