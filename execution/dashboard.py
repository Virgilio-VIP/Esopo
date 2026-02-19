import streamlit as st
import pandas as pd
import pyodbc
import os
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv

# Page config
st.set_page_config(page_title="Esopo Dashboard", layout="wide")

# Styling
st.markdown("""
    <style>
    .main { background-color: #0f1116; color: #ffffff; }
    .stMetric { background: rgba(255, 255, 255, 0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1); }
    </style>
    """, unsafe_allow_html=True)

# Load environment
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '..', '.env')
load_dotenv(dotenv_path=env_path)

def get_connection():
    return pyodbc.connect(f"DRIVER={os.getenv('DB_DRIVER')};SERVER={os.getenv('DB_SERVER')};DATABASE={os.getenv('DB_DATABASE')};UID={os.getenv('DB_USERNAME')};PWD={os.getenv('DB_PASSWORD')}")

def format_br(val):
    if val is None: return "0,00"
    return f"{float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def main():
    # --- SIDEBAR NAVIGATION ---
    st.sidebar.title("🧭 Navegação")
    page = st.sidebar.radio("Ir para:", ["🏠 Resumo Geral", "📊 Evolução de Peso", "📋 Ficha de Animais"])
    
    st.sidebar.divider()
    st.sidebar.info("Projeto Esopo v1.0\nGestão de Pecuária de Precisão")

    st.title(f"📊 Esopo - {page}")
    
    try:
        conn = get_connection()
        
        # --- GLOBAL FARM SELECTOR ---
        query_farms = "SELECT cod_fazenda, descricao FROM Tab_fazenda"
        df_all_farms = pd.read_sql(query_farms, conn)
        
        with st.container():
            st.markdown("### 🚜 Seletor de Unidades (Global)")
            selected_farm_names = st.multiselect(
                "Fazendas Selecionadas:",
                options=df_all_farms['descricao'].sort_values().tolist(),
                default=df_all_farms['descricao'].tolist(),
                key="global_farm_selector"
            )
        
        if not selected_farm_names:
            st.warning("⚠️ Selecione ao menos uma fazenda.")
            return

        selected_codes = df_all_farms[df_all_farms['descricao'].isin(selected_farm_names)]['cod_fazenda'].tolist()
        farm_ids_str = ", ".join([f"'{str(c)}'" for c in selected_codes])
        
        active_logic = "c.Origem <> 'E' AND c.cod_categoria NOT IN (SELECT cod_categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S')"
        global_filter = f"{active_logic} AND c.cod_fazenda IN ({farm_ids_str})"

        if page == "🏠 Resumo Geral":
            # KPIs - Animal Counts & UA
            query_metrics = f"""
                SELECT COUNT(*) as total, SUM(CASE WHEN c.Origem = 'N' THEN 1 ELSE 0 END) as nascidos,
                       SUM(t.unidade_animal) as total_ua, SUM(CASE WHEN c.Origem = 'N' THEN t.unidade_animal ELSE 0 END) as nascidos_ua
                FROM cad_fichario c JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria WHERE {global_filter}
            """
            df_metrics = pd.read_sql(query_metrics, conn)
            total_ativos = df_metrics['total'][0] if not df_metrics.empty else 0
            total_nascidos = df_metrics['nascidos'][0] if not df_metrics.empty else 0
            total_ua = df_metrics['total_ua'][0] if not df_metrics.empty else 0
            nascidos_ua = df_metrics['nascidos_ua'][0] if not df_metrics.empty else 0
            
            st.markdown("#### 🔢 Quantitativo (Cabeças)")
            m1, m2, m3 = st.columns(3)
            m1.metric("📦 Rebanho Ativo", f"{total_ativos:,}".replace(",", "."))
            m2.metric("🐣 Nascidos", f"{total_nascidos:,}".replace(",", "."))
            m3.metric("🤝 Comprados", f"{max(0, total_ativos - total_nascidos):,}".replace(",", "."))

            st.markdown("#### ⚖️ Capacidade (Unidade Animal - UA)")
            ua1, ua2, ua3 = st.columns(3)
            ua1.metric("🐄 Total UA", format_br(total_ua))
            ua2.metric("🍼 Nascidos UA", format_br(nascidos_ua))
            ua3.metric("🏟️ Comprados UA", format_br(max(0.0, total_ua - nascidos_ua)))

            st.divider()
            c_left, c_right = st.columns([1.2, 1])
            with c_left:
                st.subheader("Unidades")
                df_pie = pd.read_sql(f"SELECT tf.descricao as fazenda, COUNT(c.cod_animal) as total FROM cad_fichario c JOIN Tab_fazenda tf ON c.cod_fazenda = tf.cod_fazenda WHERE {global_filter} GROUP BY tf.descricao", conn)
                if not df_pie.empty:
                    st.plotly_chart(px.pie(df_pie, values='total', names='fazenda', hole=0.4, template="plotly_dark"), use_container_width=True)
            with c_right:
                st.subheader("📊 Detalhamento Técnico das Categorias")
                query_grid = f"""
                    WITH UltimaPesagem AS ( 
                        SELECT cod_animal, peso, data, GPM, GPD,
                               ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn 
                        FROM cad_pesagem_corte
                    ) 
                    SELECT 
                        t.descricao as Categoria, 
                        COUNT(c.cod_animal) as [Cabeças], 
                        AVG(DATEDIFF(month, c.dt_nascimento, GETDATE())) as [Idade Média(m)], 
                        AVG(up.peso) as [Peso Médio],
                        AVG(up.GPM) as [GMD Médio],
                        AVG(up.GPD) as [GPD Médio],
                        AVG(DATEDIFF(day, up.data, GETDATE())) as [Idade Pesagem(d)],
                        COUNT(up.peso) as [Qtd Pesagens]
                    FROM cad_fichario c 
                    JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria 
                    LEFT JOIN UltimaPesagem up ON c.cod_animal = up.cod_animal AND up.rn = 1 
                    WHERE {global_filter} 
                    GROUP BY t.descricao 
                    ORDER BY [Cabeças] DESC
                """
                df_grid = pd.read_sql(query_grid, conn)
                if not df_grid.empty: 
                    st.dataframe(
                        df_grid.style.format({
                            'GMD Médio': '{:.3f}',
                            'GPD Médio': '{:.3f}',
                            'Idade Pesagem(d)': '{:.0f}',
                            'Peso Médio': '{:.1f} kg'
                        }), 
                        use_container_width=True, 
                        hide_index=True
                    )

        elif page == "📊 Evolução de Peso":
            sub_page = st.radio("Selecione a perspectiva de análise:", ["📤 Vendas", "📥 Compras", "🐣 Nascimentos"], horizontal=True)
            
            # Sub-filters for all perspectives
            f_col1, f_col2 = st.columns([1, 2])
            with f_col1:
                periodo_meses = st.slider("Período de Análise (Meses):", 0, 60, 12, key="peso_slider")

            if sub_page == "📤 Vendas":
                st.subheader("🔎 Performance de Animais Vendidos")
                
                # Fetch Buyers
                query_b = f"SELECT DISTINCT tc.cod_criador, tc.descricao FROM cad_venda cv JOIN Tab_criador tc ON cv.cod_criador = tc.cod_criador JOIN cad_fichario cf ON cv.cod_animal = cf.cod_animal WHERE cf.cod_fazenda IN ({farm_ids_str}) AND cv.data >= DATEADD(month, -{periodo_meses}, GETDATE())"
                df_b = pd.read_sql(query_b, conn)
                with f_col2:
                    sel_b = st.multiselect("Filtrar Compradores:", options=df_b['descricao'].tolist(), default=df_b['descricao'].tolist())
                
                if not sel_b:
                    st.warning("Selecione um comprador.")
                else:
                    b_ids = df_b[df_b['descricao'].isin(sel_b)]['cod_criador'].tolist()
                    b_str = ", ".join([f"'{str(i)}'" for i in b_ids])
                    
                    sql = f"""
                        WITH Entry AS (
                            SELECT cc.cod_animal, cc.data as dte, cc.peso as pe, tc.descricao as forn, 
                                   'COMPRA: ' + CAST(cc.data AS VARCHAR) + ' - ' + tc.descricao as grp
                            FROM cad_compra cc JOIN Tab_criador tc ON cc.cod_criador = tc.cod_criador
                        ),
                        Sale AS (
                            SELECT cv.cod_animal, cv.data as dtv, cv.peso as pev_orig, tc.descricao as comp, cv.cod_criador_origem
                            FROM cad_venda cv JOIN Tab_criador tc ON cv.cod_criador = tc.cod_criador
                            WHERE cv.cod_criador IN ({b_str}) AND cv.data >= DATEADD(month, -{periodo_meses}, GETDATE())
                        ),
                        LW AS (
                            SELECT cod_animal, peso, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn
                            FROM cad_pesagem_corte
                        )
                        SELECT cf.id_animal, cf.origem, s.comp, s.dtv, 
                               ISNULL(lw.peso, s.pev_orig) as pv,
                               CASE WHEN cf.origem = 'N' THEN cf.dt_nascimento ELSE cf.dt_compra END as di,
                               DATEDIFF(day, CASE WHEN cf.origem = 'N' THEN cf.dt_nascimento ELSE cf.dt_compra END, s.dtv) as td,
                               CASE WHEN cf.origem = 'N' THEN 'NASCIMENTO: ' + CAST(FORMAT(cf.dt_nascimento, 'MM/yyyy') AS VARCHAR) ELSE e.grp END as og,
                               ISNULL(e.pe, 40.0) as pi,
                               e.dte as data_compra_raw, e.forn as fornecedor_raw
                        FROM cad_fichario cf
                        JOIN Sale s ON cf.cod_animal = s.cod_animal
                        LEFT JOIN Entry e ON cf.cod_animal = e.cod_animal
                        LEFT JOIN LW lw ON cf.cod_animal = lw.cod_animal AND lw.rn = 1
                        WHERE cf.cod_fazenda IN ({farm_ids_str})
                    """
                    df = pd.read_sql(sql, conn)
                    if not df.empty:
                        df['gt'] = df['pv'] - df['pi']
                        df['gmd'] = df['gt'] / df['td'].replace(0, 1)
                        
                        st.plotly_chart(px.sunburst(df, path=['comp', 'og'], values='pv', color='gmd', 
                                                   color_continuous_scale='RdYlGn', template="plotly_dark",
                                                   title="Hierarquia de Grupos: Comprador > Origem"), use_container_width=True)
                        
                        st.markdown("---")
                        st.subheader("🌲 Árvore de Decomposição (Estilo PowerBI)")
                        st.info("💡 Clique nos blocos para detalhar os níveis (Venda -> Cliente -> Compra -> Fornecedor)")
                        
                        df_tree = df.copy()
                        df_tree['Venda'] = df_tree['dtv'].dt.strftime('%d/%m/%Y')
                        df_tree['Cliente'] = df_tree['comp']
                        df_tree['Compra'] = pd.to_datetime(df_tree['data_compra_raw']).dt.strftime('%d/%m/%Y').fillna('NASCIMENTO')
                        df_tree['Fornecedor'] = df_tree['fornecedor_raw'].fillna('ORIGEM INTERNA')
                        df_tree['Qtd'] = 1
                        
                        fig_tree = px.icicle(
                            df_tree,
                            path=[px.Constant("Total Vendas"), 'Cliente', 'Venda', 'Fornecedor', 'Compra'],
                            values='Qtd',
                            color='gmd',
                            color_continuous_scale='RdYlGn',
                            template="plotly_dark",
                            title="Decomposição da Cadeia de Venda (Cor = GMD)"
                        )
                        fig_tree.update_traces(textinfo="label+value")
                        st.plotly_chart(fig_tree, use_container_width=True)
                        
                        st.subheader("📋 Detalhamento da Performance")
                        res = df.groupby(['comp', 'og']).agg({'id_animal': 'count', 'pv': 'mean', 'td': 'mean', 'gt': 'mean', 'gmd': 'mean'}).reset_index()
                        res.columns = ['Comprador', 'Origem (Lote/Mês)', 'Qtd', 'Peso Venda (Avg)', 'Permanência (Dias)', 'Ganho Total', 'GMD (Kg/dia)']
                        st.dataframe(res.style.format({'Peso Venda (Avg)': '{:.1f}', 'Permanência (Dias)': '{:.0f}', 'Ganho Total': '{:.1f}', 'GMD (Kg/dia)': '{:.3f}'}), use_container_width=True, hide_index=True)

            elif sub_page == "📥 Compras":
                st.subheader("📈 Performance de Lotes Comprados")
                
                query_s = f"SELECT DISTINCT tc.cod_criador, tc.descricao FROM cad_compra cc JOIN Tab_criador tc ON cc.cod_criador = tc.cod_criador JOIN cad_fichario cf ON cc.cod_animal = cf.cod_animal WHERE cf.cod_fazenda IN ({farm_ids_str}) AND cc.data >= DATEADD(month, -{periodo_meses}, GETDATE())"
                df_s = pd.read_sql(query_s, conn)
                with f_col2:
                    sel_s = st.multiselect("Filtrar Fornecedores:", options=df_s['descricao'].tolist(), default=df_s['descricao'].tolist())
                
                if not sel_s:
                    st.warning("Selecione um fornecedor.")
                else:
                    s_ids = df_s[df_s['descricao'].isin(sel_s)]['cod_criador'].tolist()
                    s_str = ", ".join([f"'{str(i)}'" for i in s_ids])
                    
                    sql_c = f"""
                        WITH LW AS (
                            SELECT cod_animal, peso, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn
                            FROM cad_pesagem_corte
                        )
                        SELECT cf.id_animal, tc.descricao as fornecedor, cc.data as dt_compra, cc.peso as pi,
                               lw.peso as pf, DATEDIFF(day, cc.data, GETDATE()) as td
                        FROM cad_fichario cf
                        JOIN cad_compra cc ON cf.cod_animal = cc.cod_animal
                        JOIN Tab_criador tc ON cc.cod_criador = tc.cod_criador
                        LEFT JOIN LW lw ON cf.cod_animal = lw.cod_animal AND lw.rn = 1
                        WHERE cf.cod_fazenda IN ({farm_ids_str}) AND cc.cod_criador IN ({s_str})
                        AND cc.data >= DATEADD(month, -{periodo_meses}, GETDATE())
                        AND cf.cod_categoria NOT IN (SELECT cod_categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S')
                    """
                    df_c = pd.read_sql(sql_c, conn)
                    if not df_c.empty:
                        df_c['gt'] = (df_c['pf'] - df_c['pi']).fillna(0)
                        df_c['gmd'] = df_c['gt'] / df_c['td'].replace(0, 1)
                        
                        st.plotly_chart(px.bar(df_c.groupby('fornecedor')['gmd'].mean().reset_index(), 
                                             x='fornecedor', y='gmd', color='gmd', 
                                             title="GMD Médio por Fornecedor (kg/dia)", template="plotly_dark"), use_container_width=True)
                        
                        st.dataframe(df_c.groupby(['fornecedor', 'dt_compra']).agg({'id_animal':'count', 'pi':'mean', 'pf':'mean', 'gt':'mean', 'gmd':'mean'}).reset_index(), use_container_width=True)

            elif sub_page == "🐣 Nascimentos":
                st.subheader("🍼 Evolução de Animais Nascidos")
                sql_n = f"""
                    WITH LW AS (
                        SELECT cod_animal, peso, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn
                        FROM cad_pesagem_corte
                    )
                    SELECT cf.id_animal, cf.dt_nascimento, lw.peso as pf, DATEDIFF(day, cf.dt_nascimento, GETDATE()) as td
                    FROM cad_fichario cf
                    LEFT JOIN LW lw ON cf.cod_animal = lw.cod_animal AND lw.rn = 1
                    WHERE cf.cod_fazenda IN ({farm_ids_str}) AND cf.origem = 'N'
                    AND cf.dt_nascimento >= DATEADD(month, -{periodo_meses}, GETDATE())
                    AND cf.cod_categoria NOT IN (SELECT cod_categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S')
                """
                df_n = pd.read_sql(sql_n, conn)
                if not df_n.empty:
                    df_n['mes_nasc'] = df_n['dt_nascimento'].dt.strftime('%m/%Y')
                    df_n['gmd'] = (df_n['pf'] - 40.0) / df_n['td'].replace(0, 1)
                    
                    st.plotly_chart(px.line(df_n.groupby('mes_nasc')['gmd'].mean().reset_index(), 
                                           x='mes_nasc', y='gmd', markers=True, 
                                           title="Eficiência de Crescimento (GMD) por Mês de Nascimento", template="plotly_dark"), use_container_width=True)
                    st.dataframe(df_n.groupby('mes_nasc').agg({'id_animal':'count', 'pf':'mean', 'gmd':'mean'}).reset_index(), use_container_width=True)

        elif page == "📋 Ficha de Animais":
            st.subheader("📉 Giro de Estoque Mensal")
            c1, c2 = st.columns([2, 1])
            with c1: periodo = st.slider("Exibir (Meses):", 0, 36, 12)
            with c2: segregate = st.toggle("Detalhamento Individual", value=False)
            
            # (Reuse existing logic for Ficha de Animais)
            query_e = f"SELECT FORMAT(data, 'yyyy-MM-01') as Mes, 'COMPRA' as Tipo, COUNT(*) as Qtd, SUM(t.unidade_animal) as UA FROM cad_compra cc JOIN cad_fichario c ON cc.cod_animal = c.cod_animal JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria WHERE c.origem = 'C' AND c.cod_fazenda IN ({farm_ids_str}) GROUP BY FORMAT(data, 'yyyy-MM-01') UNION ALL SELECT FORMAT(dt_nascimento, 'yyyy-MM-01') as Mes, 'NASCIMENTO' as Tipo, COUNT(*) as Qtd, SUM(t.unidade_animal) as UA FROM cad_fichario c JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria WHERE c.cod_fazenda IN ({farm_ids_str}) GROUP BY FORMAT(dt_nascimento, 'yyyy-MM-01')"
            query_s = f"SELECT FORMAT(data, 'yyyy-MM-01') as Mes, 'MORTE' as Tipo, COUNT(*) as Qtd, SUM(t.unidade_animal) as UA FROM cad_morte cm JOIN cad_fichario c ON cm.cod_animal = c.cod_animal JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria WHERE c.origem = 'N' AND c.cod_fazenda IN ({farm_ids_str}) GROUP BY FORMAT(data, 'yyyy-MM-01') UNION ALL SELECT FORMAT(data, 'yyyy-MM-01') as Mes, 'VENDA' as Tipo, COUNT(*) as Qtd, SUM(t.unidade_animal) as UA FROM cad_venda cv JOIN cad_fichario c ON cv.cod_animal = c.cod_animal JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria WHERE c.cod_fazenda IN ({farm_ids_str}) GROUP BY FORMAT(data, 'yyyy-MM-01')"
            
            df_e, df_s = pd.read_sql(query_e, conn), pd.read_sql(query_s, conn)
            df_all = pd.concat([df_e, df_s])
            df_all['Mes'] = pd.to_datetime(df_all['Mes'])
            pivot_qtd = df_all.pivot_table(index='Mes', columns='Tipo', values='Qtd', aggfunc='sum').fillna(0)
            pivot_ua = df_all.pivot_table(index='Mes', columns='Tipo', values='UA', aggfunc='sum').fillna(0)
            
            for c in ['COMPRA', 'NASCIMENTO', 'MORTE', 'VENDA']:
                if c not in pivot_qtd.columns: pivot_qtd[c] = 0
                if c not in pivot_ua.columns: pivot_ua[c] = 0
            
            sum_df = pd.DataFrame(index=pivot_qtd.index)
            sum_df['E_Q'] = pivot_qtd['COMPRA'] + pivot_qtd['NASCIMENTO']
            sum_df['S_Q'] = pivot_qtd['MORTE'] + pivot_qtd['VENDA']
            sum_df['SL_Q'] = sum_df['E_Q'] - sum_df['S_Q']
            sum_df['E_UA'] = pivot_ua['COMPRA'] + pivot_ua['NASCIMENTO']
            sum_df['S_UA'] = pivot_ua['MORTE'] + pivot_ua['VENDA']
            sum_df['SL_UA'] = sum_df['E_UA'] - sum_df['S_UA']
            
            curr_res = pd.read_sql(f"SELECT COUNT(*) as q, SUM(t.unidade_animal) as u FROM cad_fichario c JOIN Tab_categoria t ON c.cod_categoria = t.cod_categoria WHERE {global_filter}", conn)
            cq, cu = curr_res['q'][0], curr_res['u'][0]
            
            df_b = sum_df.sort_index(ascending=False).copy()
            ql, ul = [], []
            tq, tu = cq, cu
            for _, row in df_b.iterrows():
                ql.append(tq); ul.append(tu)
                tq -= row['SL_Q']; tu -= row['SL_UA']
            
            sum_df['REBANHO'] = list(reversed(ql)); sum_df['UA'] = list(reversed(ul))
            df_p = sum_df.tail(periodo)

            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_p.index, y=df_p['REBANHO'], name='Cabeças', marker_color='rgba(100,149,237,0.3)', yaxis='y2'))
            fig.add_trace(go.Bar(x=df_p.index, y=df_p['UA'], name='UA', marker_color='rgba(155,89,182,0.5)', yaxis='y2'))
            
            if not segregate:
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['E_Q'], name='Entradas (Qtd)', line=dict(color='#2ecc71', width=3)))
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['S_Q'], name='Saídas (Qtd)', line=dict(color='#e74c3c', width=3)))
            else:
                det = pivot_qtd.tail(periodo)
                fig.add_trace(go.Scatter(x=det.index, y=det['NASCIMENTO'], name='🐣 Nascimentos', line=dict(color='#00d1b2')))
                fig.add_trace(go.Scatter(x=det.index, y=det['COMPRA'], name='🤝 Compras', line=dict(color='#3273dc')))
                fig.add_trace(go.Scatter(x=det.index, y=det['VENDA'], name='💰 Vendas', line=dict(color='#ff3860')))
                fig.add_trace(go.Scatter(x=det.index, y=det['MORTE'], name='⚠️ Mortes', line=dict(color='#ffdd57'), yaxis='y3'))

            fig.update_layout(template="plotly_dark", barmode='group', yaxis2=dict(overlaying='y', side='right', showgrid=False), yaxis3=dict(overlaying='y', side='left', position=0.05, showgrid=False), margin=dict(l=80) if segregate else None)
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Erro: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    main()
