import pandas as pd
import streamlit as st
import plotly.express as px

# =====================================
# CONFIGURAÇÃO
# =====================================

st.set_page_config(
    page_title="Painel de BI da Steam",
    page_icon="🎮",
    layout="wide"
)

st.title("🎮 Painel de BI da Steam")
st.markdown("Este painel analisa fatores de engajamento e sucesso comercial dos jogos disponíveis na plataforma Steam.")

# =====================================
# NORMALIZAÇÃO DE GÊNEROS
# =====================================

MAPA_GENEROS = {
    'acao': 'Ação',
    'gratis para jogar': 'Grátis para Jogar',
    'gratuito para jogar': 'Grátis para Jogar',
    'estrategia': 'Estratégia',
    'aventura': 'Aventura',
    'independente': 'Indie',
    'india': 'Indie',
    'indie': 'Indie',
    'rpg': 'RPG',
    'animacao e modelagem': 'Animação & Modelagem',
    'producao de video': 'Produção de Vídeo',
    'casual': 'Casual',
    'simulacao': 'Simulação',
    'corrida': 'Corrida',
    'corridas': 'Corrida',
    'violento': 'Violento',
    'violenta': 'Violento',
    'violencia': 'Violento',
    'massivamente multijogador': 'Multijogador Massivo',
    'massivamente multiplayer': 'Multijogador Massivo',
    'multijogador massivo': 'Multijogador Massivo',
    'independente e multijogador massivo': 'Multijogador Massivo',
    'nudez': 'Nudez',
    'esporte': 'Esportes',
    'esportes': 'Esportes',
    'esportivo': 'Esportes',
    'acesso antecipado': 'Acesso Antecipado',
    'acesso casual e antecipado': 'Acesso Antecipado',
    'gore': 'Gore',
    'sangramento': 'Gore',
    'sangrento': 'Gore',
    'utilitarios': 'Utilitários',
    'utilidades': 'Utilitários',
    'design e ilustracao': 'Design & Ilustração',
    'publicacao na web': 'Publicação na Web',
    'educacao': 'Educação',
    'treinamento de software': 'Treinamento de Software',
    'treinamento em software': 'Treinamento de Software',
    'conteudo sexual': 'Conteúdo Sexual',
    'producao de audio': 'Produção de Áudio',
    'desenvolvimento de jogos': 'Desenvolvimento de Jogos',
    'edicao de fotos': 'Edição de Fotos',
    'contabilidade': 'Contabilidade',
    'documentario': 'Documentário',
    'tutorial': 'Tutorial',
    'servicos publicos': 'Serviços Públicos',
}

def normalizar_generos(texto):
    if not isinstance(texto, str):
        return texto
    partes = texto.split(';')
    normalizadas = [MAPA_GENEROS.get(p.strip(), p.strip().title()) for p in partes]
    vistas = set()
    resultado = []
    for g in normalizadas:
        if g not in vistas:
            vistas.add(g)
            resultado.append(g)
    return ';'.join(resultado)

# =====================================
# DADOS
# =====================================

@st.cache_data
def carregar():
    steam = pd.read_csv("base_jogos_2.csv")
    tags  = pd.read_csv("jogos_tags_pt.csv")

    steam = steam.rename(columns={
        "positive_ratings": "avaliações_positivas",
        "negative_ratings": "avaliações_negativas",
        "average_playtime": "tempo_médio_de_jogo",
        "publisher":        "editor",
        "developer":        "desenvolvedor",
    })

    steam["genres"] = steam["genres"].apply(normalizar_generos)

    steam["approval_rate"] = (
        steam["avaliações_positivas"] /
        (steam["avaliações_positivas"] + steam["avaliações_negativas"])
    ) * 100

    steam["release_date"] = pd.to_datetime(steam["release_date"], errors="coerce")
    steam["ano"]          = steam["release_date"].dt.year
    steam["horas_jogadas"] = steam["tempo_médio_de_jogo"] / 60

    steam["owners_min"] = (
        steam["owners"].astype(str)
        .str.split("-").str[0]
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    return steam, tags

steam, tags = carregar()

PRECO_MAX   = float(steam["price"].max())
HORAS_MAX   = float(steam["horas_jogadas"].max())

todos_generos = sorted(
    steam["genres"].dropna()
    .str.split(";").explode().str.strip().unique()
)

# =====================================
# SIDEBAR
# =====================================

st.sidebar.header("🔧 Filtros")
anos     = sorted(steam["ano"].dropna().unique())
anos_sel = st.sidebar.multiselect("Ano de Lançamento", anos, default=anos)

df_base = steam[steam["ano"].isin(anos_sel)]

# =====================================
# KPIS
# =====================================

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Jogos",           f"{len(df_base):,}".replace(",", "."))
c2.metric("Tempo Médio",     f"{df_base['horas_jogadas'].mean():.1f} h")
c3.metric("Aprovação Média", f"{df_base['approval_rate'].mean():.1f}%")
c4.metric("Preço Médio",     f"US$ {df_base['price'].mean():.2f}")
c5.metric("Cópias Vendidas", f"{df_base['owners_min'].sum()/1_000_000:.1f} Mi")

# =====================================
# ABAS
# =====================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Visão Geral", "🎮 Engajamento", "🏷️ Tags", "💰 Sucesso Comercial"
])

# ── helper: ordena do maior para o menor no eixo Y ──────────────────────────
def bar_h(df, x, y, **kwargs):
    """
    Gráfico de barras horizontal com o maior valor no topo.
    Recebe df já filtrado/agregado. Ordena crescente para o px.bar
    (Plotly inverte o eixo Y, então crescente = maior no topo).
    Garante category_orders para evitar reordenação alfabética.
    """
    ordered = df.sort_values(x, ascending=False)
    category_orders = {y: ordered[y].tolist()}
    return px.bar(ordered, x=x, y=y, orientation="h",
                  category_orders=category_orders, **kwargs)

# ======================================
# TAB 1 — VISÃO GERAL
# ======================================

with tab1:

    st.subheader("📅 Jogos Lançados por Ano")
    jogos_ano = df_base.groupby("ano").size().reset_index(name="Quantidade")
    fig = px.line(jogos_ano, x="ano", y="Quantidade", markers=True)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("💲 Distribuição dos Preços")
    col_f1, col_f2 = st.columns([3, 1])
    with col_f1:
        preco_hist = st.slider(
            "Faixa de preço (US$)",
            0.0, PRECO_MAX, (0.0, PRECO_MAX), step=0.5,
            key="vg_preco_hist"
        )
    with col_f2:
        gratuitos = int((df_base["price"] == 0).sum())
        st.metric("Jogos Gratuitos", f"{gratuitos:,}".replace(",", "."))

    df_preco = df_base[(df_base["price"] >= preco_hist[0]) & (df_base["price"] <= preco_hist[1])]
    fig = px.histogram(df_preco, x="price", nbins=40,
                       labels={"price": "Preço (US$)", "count": "Quantidade"})
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🖥️ Suporte por Plataforma")
    plat_counts = {
        "Windows": df_base["platforms"].str.contains("windows", case=False, na=False).sum(),
        "Mac":     df_base["platforms"].str.contains("mac",     case=False, na=False).sum(),
        "Linux":   df_base["platforms"].str.contains("linux",   case=False, na=False).sum(),
    }
    plat_df = pd.DataFrame(plat_counts.items(), columns=["Plataforma", "Jogos"])
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        st.dataframe(plat_df, use_container_width=True, hide_index=True)
    with col_p2:
        fig = px.bar(plat_df, x="Plataforma", y="Jogos", color="Plataforma",
                     labels={"Jogos": "Quantidade de Jogos"})
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🎭 Gêneros Mais Comuns")
    gen_count = (
        df_base["genres"].dropna()
        .str.split(";").explode().str.strip()
        .value_counts().head(15).reset_index()
    )
    gen_count.columns = ["Gênero", "Quantidade"]
    fig = bar_h(gen_count, x="Quantidade", y="Gênero")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("⭐ Aprovação Média por Gênero")
    gen_aprov = df_base[["genres", "approval_rate"]].dropna().copy()
    gen_aprov["genres"] = gen_aprov["genres"].str.split(";")
    gen_aprov = gen_aprov.explode("genres")
    gen_aprov = (
        gen_aprov.groupby("genres")["approval_rate"]
        .mean().sort_values(ascending=False)
        .head(15).reset_index()
    )
    gen_aprov.columns = ["Gênero", "Aprovação (%)"]
    gen_aprov["Aprovação (%)"] = gen_aprov["Aprovação (%)"].round(1)
    fig = bar_h(gen_aprov, x="Aprovação (%)", y="Gênero",
                color="Aprovação (%)", color_continuous_scale="Greens")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🏅 Conquistas (Achievements)")
    col_a1, col_a2, col_a3 = st.columns(3)
    col_a1.metric("Média de Conquistas",  f"{df_base['achievements'].mean():.0f}")
    col_a2.metric("Máximo de Conquistas", f"{int(df_base['achievements'].max()):,}".replace(",", "."))
    col_a3.metric("Jogos com Conquistas", f"{int((df_base['achievements'] > 0).sum()):,}".replace(",", "."))

    ach_filtrado = df_base[df_base["achievements"] > 0]
    fig = px.histogram(ach_filtrado, x="achievements", nbins=50,
                       labels={"achievements": "Nº de Conquistas", "count": "Quantidade de Jogos"})
    fig.update_xaxes(range=[0, 500])
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("📊 Evolução do Preço Médio por Ano")
    preco_ano = (
        df_base[df_base["price"] > 0]
        .groupby("ano")["price"].mean()
        .reset_index()
    )
    preco_ano.columns = ["Ano", "Preço Médio (US$)"]
    fig = px.line(preco_ano, x="Ano", y="Preço Médio (US$)", markers=True)
    st.plotly_chart(fig, use_container_width=True)

# =====================================
# TAB 2 — ENGAJAMENTO
# =====================================

with tab2:

    st.subheader("⏱️ Tempo Médio de Jogo por Gênero")
    genero_df = df_base[["genres", "horas_jogadas"]].dropna().copy()
    genero_df["genres"] = genero_df["genres"].str.split(";")
    genero_df = genero_df.explode("genres")
    genero_media = (
        genero_df.groupby("genres")["horas_jogadas"]
        .mean().sort_values(ascending=False)
        .head(15).reset_index()
    )
    genero_media.columns = ["Gênero", "Horas"]
    fig = bar_h(genero_media, x="Horas", y="Gênero",
                labels={"Horas": "Horas", "Gênero": "Gênero"})
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🔵 Avaliação x Engajamento")
    fig = px.scatter(df_base, x="approval_rate", y="horas_jogadas", hover_name="name",
                     labels={"approval_rate": "Taxa de Aprovação (%)", "horas_jogadas": "Horas Jogadas"})
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🏆 Ranking de Jogos por Tempo Médio de Jogo")
    with st.expander("⚙️ Filtros do Ranking", expanded=True):
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        with col_r1:
            top_n = st.slider("Top N jogos", 5, 50, 20, key="eng_topn")
        with col_r2:
            preco_rank = st.slider(
                "Faixa de Preço (US$)",
                0.0, PRECO_MAX, (0.0, PRECO_MAX), step=0.5, key="eng_preco"
            )
        with col_r3:
            horas_rank = st.slider(
                "Faixa de Horas Jogadas",
                0.0, HORAS_MAX, (0.0, HORAS_MAX), step=1.0, key="eng_horas"
            )
        with col_r4:
            generos_rank = st.multiselect(
                "Gênero", todos_generos, default=[], placeholder="Todos", key="eng_genero"
            )

    top_df = df_base[
        (df_base["horas_jogadas"] > 0) &
        (df_base["price"]         >= preco_rank[0]) &
        (df_base["price"]         <= preco_rank[1]) &
        (df_base["horas_jogadas"] >= horas_rank[0]) &
        (df_base["horas_jogadas"] <= horas_rank[1])
    ]
    if generos_rank:
        mask   = top_df["genres"].dropna().apply(lambda g: any(gen in g.split(";") for gen in generos_rank))
        top_df = top_df[top_df.index.isin(mask[mask].index)]

    top = top_df.sort_values("horas_jogadas", ascending=False).head(top_n)

    if top.empty:
        st.warning("Nenhum jogo encontrado com os filtros selecionados.")
    else:
        fig = bar_h(top, x="horas_jogadas", y="name",
                    labels={"horas_jogadas": "Horas Jogadas", "name": "Jogo"})
        st.plotly_chart(fig, use_container_width=True)

        tabela_top = top[["name", "horas_jogadas", "approval_rate", "price", "genres"]].copy()
        tabela_top.columns = ["Jogo", "Horas Jogadas", "Aprovação (%)", "Preço (US$)", "Gêneros"]
        tabela_top["Horas Jogadas"] = tabela_top["Horas Jogadas"].round(1)
        tabela_top["Aprovação (%)"] = tabela_top["Aprovação (%)"].round(1)
        tabela_top["Preço (US$)"]   = tabela_top["Preço (US$)"].apply(
            lambda x: "Grátis" if x == 0 else f"US$ {x:.2f}"
        )
        st.dataframe(tabela_top, use_container_width=True)

# =====================================
# TAB 3 — TAGS
# =====================================

with tab3:

    st.subheader("🏷️ 20 Características Mais Frequentes")
    freq = (
        tags.drop(columns=["appid"]).sum()
        .sort_values(ascending=False).head(20).reset_index()
    )
    freq.columns = ["Característica", "Pontuação"]
    fig = bar_h(freq, x="Pontuação", y="Característica")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(freq, use_container_width=True)

# =====================================
# TAB 4 — SUCESSO COMERCIAL
# =====================================

with tab4:

    st.subheader("🎯 Gênero de Maior Sucesso por Publicadora")

    pub_gen = df_base[["editor", "genres", "owners_min"]].dropna().copy()
    pub_gen["genres"] = pub_gen["genres"].str.split(";")
    pub_gen = pub_gen.explode("genres")
    pub_gen = pub_gen.groupby(["editor", "genres"])["owners_min"].sum().reset_index()
    idx     = pub_gen.groupby("editor")["owners_min"].idxmax()
    top_genero_pub = pub_gen.loc[idx].sort_values("owners_min", ascending=False).head(20)

    ordered_pub = top_genero_pub.sort_values("owners_min", ascending=False)
    fig = px.bar(
        ordered_pub,
        x="owners_min", y="editor", color="genres", orientation="h",
        category_orders={"editor": ordered_pub["editor"].tolist()},
        labels={"owners_min": "Cópias Vendidas", "editor": "Publicadora", "genres": "Gênero"},
        title="Gênero de Maior Sucesso por Publicadora"
    )
    fig.update_layout(height=800, margin=dict(l=350))
    st.plotly_chart(fig, use_container_width=True)

    tabela_pub = top_genero_pub.rename(columns={
        "editor": "Publicadora", "genres": "Gênero de Maior Sucesso", "owners_min": "Cópias Vendidas"
    }).copy()
    tabela_pub["Cópias Vendidas"] = tabela_pub["Cópias Vendidas"].apply(
        lambda x: f"{x:,.0f}".replace(",", ".")
    )
    st.dataframe(tabela_pub, use_container_width=True)
    st.divider()

    st.subheader("🎮 Gênero de Maior Sucesso por Desenvolvedora")

    dev_gen = df_base[["desenvolvedor", "genres", "owners_min"]].dropna().copy()
    dev_gen["genres"] = dev_gen["genres"].str.split(";")
    dev_gen = dev_gen.explode("genres")
    dev_gen = dev_gen.groupby(["desenvolvedor", "genres"])["owners_min"].sum().reset_index()
    idx     = dev_gen.groupby("desenvolvedor")["owners_min"].idxmax()
    top_genero_dev = dev_gen.loc[idx].sort_values("owners_min", ascending=False).head(20)

    ordered_dev = top_genero_dev.sort_values("owners_min", ascending=False)
    fig = px.bar(
        ordered_dev,
        x="owners_min", y="desenvolvedor", color="genres", orientation="h",
        category_orders={"desenvolvedor": ordered_dev["desenvolvedor"].tolist()},
        labels={"owners_min": "Cópias Vendidas", "desenvolvedor": "Desenvolvedora", "genres": "Gênero"},
        title="Gênero de Maior Sucesso por Desenvolvedora"
    )
    fig.update_layout(height=800, margin=dict(l=350))
    st.plotly_chart(fig, use_container_width=True)

    tabela_dev = top_genero_dev.rename(columns={
        "desenvolvedor": "Desenvolvedora", "genres": "Gênero de Maior Sucesso", "owners_min": "Cópias Vendidas"
    }).copy()
    tabela_dev["Cópias Vendidas"] = tabela_dev["Cópias Vendidas"].apply(
        lambda x: f"{x:,.0f}".replace(",", ".")
    )
    st.dataframe(tabela_dev, use_container_width=True)
    st.divider()

    top_pub = top_genero_pub.iloc[0]
    st.success(f"""
        📈 Insight Principal

        A publicadora '{top_pub['editor']}'
        obtém seu maior sucesso no gênero '{top_pub['genres']}',
        acumulando aproximadamente {top_pub['owners_min']:,.0f} Cópias Vendidas.
    """)

    st.divider()

    # ── Explorador por empresa ─────────────────────────────────────────
    st.subheader("🔍 Explorar Jogos por Empresa")

    col_tipo, col_empresa = st.columns([1, 3])
    with col_tipo:
        tipo_empresa = st.radio(
            "Tipo", ["Publicadora", "Desenvolvedora"],
            horizontal=False, key="tipo_empresa"
        )

    coluna_empresa = "editor" if tipo_empresa == "Publicadora" else "desenvolvedor"
    lista_empresas = sorted(df_base[coluna_empresa].dropna().unique())

    with col_empresa:
        empresa_sel = st.selectbox(
            f"Selecione a {tipo_empresa}",
            lista_empresas,
            index=lista_empresas.index("Valve") if "Valve" in lista_empresas else 0,
            key="empresa_sel"
        )

    df_empresa = df_base[df_base[coluna_empresa] == empresa_sel].copy()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de Jogos",  f"{len(df_empresa)}")
    k2.metric("Cópias Vendidas", f"{df_empresa['owners_min'].sum()/1_000_000:.1f} Mi")
    k3.metric("Aprovação Média", f"{df_empresa['approval_rate'].mean():.1f}%")
    k4.metric("Preço Médio",     f"US$ {df_empresa['price'].mean():.2f}")

    ordem_opcoes = {
        "Cópias Vendidas":   "owners_min",
        "Horas Jogadas":     "horas_jogadas",
        "Taxa de Aprovação": "approval_rate",
        "Preço":             "price",
    }
    col_ord1, col_ord2 = st.columns([2, 1])
    with col_ord1:
        ordem_label = st.selectbox("Ordenar por", list(ordem_opcoes.keys()), key="empresa_ordem")
    with col_ord2:
        top_n_emp = st.slider("Top N jogos", 5, 50, 20, key="empresa_topn")

    col_ordem = ordem_opcoes[ordem_label]

    df_empresa_top = (
        df_empresa[df_empresa[col_ordem] > 0]
        .sort_values(col_ordem, ascending=False)
        .head(top_n_emp)
    )

    if df_empresa_top.empty:
        st.warning("Nenhum jogo encontrado para esta empresa com os filtros atuais.")
    else:
        ordered_emp = df_empresa_top.sort_values(col_ordem, ascending=False)
        fig = px.bar(
            ordered_emp,
            x=col_ordem, y="name", color="genres", orientation="h",
            category_orders={"name": ordered_emp["name"].tolist()},
            hover_data=["price", "approval_rate", "horas_jogadas"],
            labels={
                col_ordem:       ordem_label,
                "name":          "Jogo",
                "genres":        "Gênero",
                "price":         "Preço (US$)",
                "approval_rate": "Aprovação (%)",
                "horas_jogadas": "Horas Jogadas",
            },
            title=f"Top {top_n_emp} jogos de {empresa_sel} — {ordem_label}",
        )
        fig.update_layout(height=max(400, top_n_emp * 28), margin=dict(l=250))
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### Aprovação × Horas Jogadas")
        fig2 = px.scatter(
            df_empresa_top,
            x="approval_rate", y="horas_jogadas",
            size="owners_min", color="genres", hover_name="name",
            labels={
                "approval_rate": "Taxa de Aprovação (%)",
                "horas_jogadas": "Horas Jogadas",
                "owners_min":    "Cópias Vendidas",
                "genres":        "Gênero",
            },
        )
        st.plotly_chart(fig2, use_container_width=True)

        tabela_emp = df_empresa_top[[
            "name", "genres", "horas_jogadas", "approval_rate", "price", "owners_min"
        ]].copy()
        tabela_emp.columns = [
            "Jogo", "Gêneros", "Horas Jogadas", "Aprovação (%)", "Preço (US$)", "Cópias Vendidas"
        ]
        tabela_emp["Horas Jogadas"]   = tabela_emp["Horas Jogadas"].round(1)
        tabela_emp["Aprovação (%)"]   = tabela_emp["Aprovação (%)"].round(1)
        tabela_emp["Preço (US$)"]     = tabela_emp["Preço (US$)"].apply(
            lambda x: "Grátis" if x == 0 else f"US$ {x:.2f}"
        )
        tabela_emp["Cópias Vendidas"] = tabela_emp["Cópias Vendidas"].apply(
            lambda x: f"{x:,.0f}".replace(",", ".")
        )
        st.dataframe(tabela_emp, use_container_width=True)

# =====================================
# CONCLUSÕES
# =====================================

st.divider()

jogo_top     = df_base.sort_values("horas_jogadas", ascending=False).iloc[0]
mais_vendido = df_base.sort_values("owners_min",    ascending=False).iloc[0]

col1, col2 = st.columns(2)
with col1:
    st.success(f"""
        🎮 Jogo Mais Engajador

        {jogo_top['name']}

        Tempo médio: {jogo_top['horas_jogadas']:.1f} horas
    """)
with col2:
    st.info(f"""
        💰 Jogo Mais Popular

        {mais_vendido['name']}

        Cópias Vendidas mínimas: {mais_vendido['owners_min']:,.0f}
    """)