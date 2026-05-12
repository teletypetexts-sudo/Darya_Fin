import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.graph_objects as go
import re
import datetime

# ═══════════════════════════════════════════════════════════
# КОНФИГ
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="My Finance",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&display=swap');

    * {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
        -webkit-font-smoothing: antialiased;
    }

    .stApp {
        background:
            radial-gradient(ellipse 800px 600px at top left, #EEF2FF 0%, transparent 50%),
            radial-gradient(ellipse 600px 500px at bottom right, #FEE7E7 0%, transparent 50%),
            #FAFBFC !important;
    }

    #MainMenu, footer, header { visibility: hidden; height: 0; }
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 4rem !important;
        max-width: 1200px !important;
    }

    /* ЛОГО */
    .logo {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 30px;
        font-weight: 700;
        background: linear-gradient(135deg, #4F46E5 0%, #00C896 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1.2px;
        display: flex;
        align-items: center;
        gap: 8px;
        padding-top: 6px;
    }
    .logo-emoji {
        -webkit-text-fill-color: initial;
        background: none;
    }

    /* HERO */
    .hero {
        background: linear-gradient(135deg, #1E1B4B 0%, #4F46E5 50%, #7C3AED 100%);
        border-radius: 28px;
        padding: 36px 40px;
        color: white;
        margin: 4px 0 20px 0;
        position: relative;
        overflow: hidden;
        box-shadow: 0 20px 60px -15px rgba(79, 70, 229, 0.45);
    }
    .hero::before {
        content: '';
        position: absolute;
        top: -100px; right: -50px;
        width: 360px; height: 360px;
        background: radial-gradient(circle, rgba(255,255,255,0.10) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
    }
    .hero::after {
        content: '';
        position: absolute;
        bottom: -150px; left: -50px;
        width: 300px; height: 300px;
        background: radial-gradient(circle, rgba(236, 72, 153, 0.20) 0%, transparent 70%);
        border-radius: 50%;
        pointer-events: none;
    }
    .hero-label {
        font-size: 11px; font-weight: 600;
        letter-spacing: 2.5px; text-transform: uppercase;
        opacity: 0.7; margin-bottom: 12px;
        position: relative;
    }
    .hero-amount {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 58px; font-weight: 700;
        letter-spacing: -2.5px; line-height: 1;
        margin-bottom: 18px;
        position: relative;
    }
    .hero-pills {
        display: flex; gap: 10px; flex-wrap: wrap;
        position: relative;
    }
    .pill {
        display: inline-flex; align-items: center;
        background: rgba(255,255,255,0.16);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 8px 16px; border-radius: 100px;
        font-size: 13px; font-weight: 600;
        border: 1px solid rgba(255,255,255,0.10);
    }
    .pill-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        background: rgba(255,255,255,0.7);
        margin-right: 8px;
    }

    /* KPI */
    .kpi-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 14px;
        margin-bottom: 8px;
    }
    .kpi {
        background: white;
        border-radius: 20px;
        padding: 22px;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
        border: 1px solid rgba(15, 23, 42, 0.04);
        transition: all 0.25s ease;
    }
    .kpi:hover {
        transform: translateY(-3px);
        box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
    }
    .kpi-head {
        display: flex; align-items: center; gap: 10px;
        margin-bottom: 14px;
    }
    .kpi-badge {
        width: 36px; height: 36px;
        border-radius: 10px;
        display: inline-flex;
        align-items: center; justify-content: center;
        font-size: 18px; font-weight: 700;
    }
    .badge-green { background: rgba(0, 200, 150, 0.12); color: #00A578; }
    .badge-red { background: rgba(255, 87, 87, 0.12); color: #E13C3C; }
    .kpi-label {
        font-size: 11px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 1.5px;
        color: #64748B;
    }
    .kpi-amount {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 28px; font-weight: 700;
        letter-spacing: -1px; color: #0F172A;
        line-height: 1; margin-bottom: 8px;
    }
    .kpi-sub { font-size: 12px; color: #94A3B8; font-weight: 500; }

    /* СЕКЦИИ */
    .section {
        display: flex; align-items: center;
        justify-content: space-between;
        margin: 36px 0 14px 0;
    }
    .section-title-wrap {
        display: flex; align-items: center; gap: 12px;
    }
    .section-dot {
        width: 10px; height: 10px;
        border-radius: 50%;
        display: inline-block;
    }
    .section-title {
        font-size: 19px; font-weight: 700;
        color: #0F172A; letter-spacing: -0.5px;
    }
    .section-sub {
        font-size: 12px; color: #94A3B8;
        font-weight: 500;
    }

    /* PLOTLY КАРТОЧКА */
    div[data-testid="stPlotlyChart"] {
        background: white;
        border-radius: 20px;
        padding: 16px;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
        border: 1px solid rgba(15, 23, 42, 0.04);
    }

    /* СПИСОК */
    .cat-list {
        background: white;
        border-radius: 20px;
        padding: 8px 22px;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
        border: 1px solid rgba(15, 23, 42, 0.04);
    }
    .cat-row {
        display: flex; align-items: center; gap: 14px;
        padding: 14px 0;
        border-bottom: 1px solid #F1F5F9;
    }
    .cat-row:last-child { border-bottom: none; }
    .cat-avatar {
        width: 42px; height: 42px;
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        font-family: 'Space Grotesk', sans-serif;
        font-size: 17px;
        font-weight: 700;
        color: white;
        flex-shrink: 0;
        letter-spacing: -0.5px;
    }
    .cat-info { flex: 1; min-width: 0; }
    .cat-name {
        font-weight: 600; color: #0F172A;
        font-size: 14px; margin-bottom: 6px;
    }
    .cat-bar-wrap {
        height: 6px; background: #F1F5F9;
        border-radius: 100px; overflow: hidden;
    }
    .cat-bar { height: 100%; border-radius: 100px; }
    .cat-right { text-align: right; flex-shrink: 0; }
    .cat-amount {
        font-family: 'Space Grotesk';
        font-weight: 700; font-size: 14px;
        color: #0F172A;
    }
    .cat-pct {
        font-size: 11px; color: #94A3B8;
        font-weight: 600;
    }

    /* SELECTBOX (период) — pill style */
    div[data-testid="stSelectbox"] > label { display: none !important; }
    div[data-testid="stSelectbox"] [data-baseweb="select"] {
        background-color: white !important;
        border-radius: 100px !important;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05) !important;
    }
    div[data-testid="stSelectbox"] [data-baseweb="select"] > div {
        background-color: white !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 100px !important;
        min-height: 38px !important;
    }
    div[data-testid="stSelectbox"] [data-baseweb="select"] div,
    div[data-testid="stSelectbox"] [data-baseweb="select"] input {
        color: #0F172A !important;
        font-family: 'Plus Jakarta Sans' !important;
        font-weight: 600 !important;
        font-size: 13px !important;
    }

    /* Dropdown popover — light theme */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    div[data-baseweb="popover"] ul {
        background-color: white !important;
    }
    div[data-baseweb="popover"] li {
        background-color: white !important;
        color: #0F172A !important;
        font-family: 'Plus Jakarta Sans' !important;
        font-weight: 500 !important;
        font-size: 13px !important;
    }
    div[data-baseweb="popover"] li:hover {
        background-color: #F1F5F9 !important;
    }
    div[data-baseweb="popover"] li[aria-selected="true"] {
        background-color: #EEF2FF !important;
        color: #4F46E5 !important;
        font-weight: 700 !important;
    }

    /* МОБИЛКА */
    @media (max-width: 640px) {
        .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
        .logo { font-size: 24px; }
        .hero { padding: 28px 22px; border-radius: 24px; }
        .hero-amount { font-size: 40px; letter-spacing: -1.8px; }
        .kpi-grid { gap: 10px; }
        .kpi { padding: 16px; }
        .kpi-amount { font-size: 22px; }
        .kpi-badge { width: 32px; height: 32px; font-size: 15px; }
        .section-title { font-size: 16px; }
        .cat-list { padding: 4px 16px; }
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# ПАЛИТРЫ
# ═══════════════════════════════════════════════════════════
EXP_COLORS = ['#4F46E5', '#EF4444', '#F59E0B', '#EC4899', '#8B5CF6',
              '#F97316', '#A855F7', '#FB7185', '#FB923C', '#D946EF']

INC_COLORS = ['#10B981', '#06B6D4', '#3B82F6', '#14B8A6', '#22C55E',
              '#0EA5E9', '#84CC16', '#0891B2', '#059669', '#2563EB']

# Регулярка для удаления эмодзи в начале строки (если пользователь добавил их в названия)
_EMOJI_RE = re.compile(
    r'^([\U0001F300-\U0001FAFF\u2600-\u27BF\U0001F000-\U0001F2FF'
    r'\U0001F600-\U0001F64F\U0001F680-\U0001F6FF])\s*'
)


def clean_cat_name(cat):
    """Убираем эмодзи из начала названия категории."""
    return _EMOJI_RE.sub('', cat).strip() or cat


def cat_initial(cat):
    """Первая буква очищенного названия — для аватарки."""
    name = clean_cat_name(cat)
    return name[0].upper() if name else "?"


# ═══════════════════════════════════════════════════════════
# ДАННЫЕ
# ═══════════════════════════════════════════════════════════
def _parse_flex_date(s):
    """Парсит даты в любом формате: '11.05.2026 23:02', '10.05.26', '4.05.2026' и т.д."""
    s = str(s).strip()
    if not s or s.lower() in ('nan', 'nat', 'none'):
        return pd.NaT
    s = s.split(' ')[0]  # отрезаем время
    parts = s.split('.')
    if len(parts) != 3:
        return pd.NaT
    try:
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        if y < 100:
            y = 2000 + y if y < 70 else 1900 + y
        return pd.Timestamp(year=y, month=m, day=d)
    except (ValueError, TypeError):
        return pd.NaT


def _get_credentials(scopes):
    """Локально — credentials.json, в Streamlit Cloud — секреты."""
    try:
        if "gcp_service_account" in st.secrets:
            return Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]), scopes=scopes
            )
    except Exception:
        pass
    return Credentials.from_service_account_file('credentials.json', scopes=scopes)


@st.cache_data(ttl=300)
def load_data():
    SHEET_ID = '1JwZWJbjORChtUmuJQiJisSZMrBr5TaBjKSxxuA1HdEU'
    scopes = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    creds = _get_credentials(scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    df = pd.DataFrame(sheet.get_all_records())

    if not df.empty:
        df['Сумма'] = pd.to_numeric(df['Сумма'], errors='coerce').fillna(0)
        df['Дата'] = df['Дата'].apply(_parse_flex_date)
        df = df.dropna(subset=['Дата'])
    return df


def fmt(n):
    return f"{n:,.0f}".replace(",", " ")


def render_breakdown(title, sub, dot_color, dataframe, palette):
    """Универсальный блок: donut + список категорий"""
    if dataframe.empty:
        return

    cats = dataframe.groupby('Категория')['Сумма'].sum().sort_values(ascending=False)
    total = cats.sum()

    st.markdown(f"""
        <div class="section">
            <div class="section-title-wrap">
                <span class="section-dot" style="background:{dot_color}"></span>
                <span class="section-title">{title}</span>
            </div>
            <div class="section-sub">{sub}</div>
        </div>
    """, unsafe_allow_html=True)

    col_donut, col_list = st.columns([1, 1.2])

    # DONUT
    with col_donut:
        colors_list = [palette[i % len(palette)] for i in range(len(cats))]
        fig_d = go.Figure(go.Pie(
            labels=[clean_cat_name(c) for c in cats.index],
            values=cats.values,
            hole=0.72,
            marker=dict(colors=colors_list, line=dict(color='white', width=3)),
            textinfo='none',
            hovertemplate='<b>%{label}</b><br>%{value:,.0f} ₽<br>%{percent}<extra></extra>',
            sort=False
        ))
        fig_d.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            paper_bgcolor='white',
            annotations=[dict(
                text=f"<b>{fmt(total)} ₽</b><br><span style='font-size:11px;color:#94A3B8'>всего</span>",
                x=0.5, y=0.5,
                font=dict(size=22, color='#0F172A', family='Space Grotesk'),
                showarrow=False
            )]
        )
        st.plotly_chart(fig_d, use_container_width=True,
                        config={'displayModeBar': False})

    # СПИСОК
    with col_list:
        rows_html = '<div class="cat-list">'
        for i, (cat, val) in enumerate(cats.items()):
            pct = (val / total * 100)
            color = palette[i % len(palette)]
            initial = cat_initial(cat)
            name = clean_cat_name(cat)
            rows_html += (
                f'<div class="cat-row">'
                f'<div class="cat-avatar" style="background:{color};">{initial}</div>'
                f'<div class="cat-info">'
                f'<div class="cat-name">{name}</div>'
                f'<div class="cat-bar-wrap">'
                f'<div class="cat-bar" style="width:{pct:.1f}%; background:{color};"></div>'
                f'</div></div>'
                f'<div class="cat-right">'
                f'<div class="cat-amount">{fmt(val)} ₽</div>'
                f'<div class="cat-pct">{pct:.1f}%</div>'
                f'</div></div>'
            )
        rows_html += '</div>'
        st.markdown(rows_html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════
try:
    df = load_data()

    if df.empty:
        st.warning("В таблице нет данных.")
    else:
        # ── Шапка ──
        col_logo, col_date = st.columns([1.5, 1])
        with col_logo:
            st.markdown(
                '<div class="logo"><span class="logo-emoji">💎</span>My Finance</div>',
                unsafe_allow_html=True
            )
        min_d, max_d = df['Дата'].min().date(), df['Дата'].max().date()
        today = datetime.date.today()
        month_start = today.replace(day=1)
        prev_month_end = month_start - datetime.timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)
        year_start = today.replace(month=1, day=1)

        period_options = {
            "Всё время": (min_d, max_d),
            "Этот месяц": (month_start, today),
            "Прошлый месяц": (prev_month_start, prev_month_end),
            "Этот год": (year_start, today),
            "Последние 7 дней": (today - datetime.timedelta(days=6), today),
            "Последние 30 дней": (today - datetime.timedelta(days=29), today),
        }

        with col_date:
            selected_period = st.selectbox(
                "Период",
                list(period_options.keys()),
                index=0,
                label_visibility="collapsed"
            )
        period = period_options[selected_period]

        # ── Фильтр ──
        f_df = df[(df['Дата'].dt.date >= period[0]) &
                  (df['Дата'].dt.date <= period[1])]
        days_count = (period[1] - period[0]).days + 1

        # ── Расчёты ──
        inc = f_df[f_df['Доход/Расход'] == 'Доход']['Сумма'].sum()
        exp = f_df[f_df['Доход/Расход'] == 'Расход']['Сумма'].sum()
        balance = inc - exp
        savings_rate = (balance / inc * 100) if inc > 0 else 0
        avg_day_exp = exp / days_count if days_count > 0 else 0
        sign = "+" if balance >= 0 else "−"

        # ── HERO ──
        st.markdown(f"""
            <div class="hero">
                <div class="hero-label">Общий баланс</div>
                <div class="hero-amount">{sign}{fmt(abs(balance))} ₽</div>
                <div class="hero-pills">
                    <div class="pill"><span class="pill-dot"></span>{savings_rate:.0f}% сбережений</div>
                    <div class="pill"><span class="pill-dot"></span>{days_count} {'дн.' if days_count != 1 else 'день'}</div>
                    <div class="pill"><span class="pill-dot"></span>{fmt(avg_day_exp)} ₽/день</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # ── KPI ──
        st.markdown(f"""
            <div class="kpi-grid">
                <div class="kpi">
                    <div class="kpi-head">
                        <div class="kpi-badge badge-green">↑</div>
                        <div class="kpi-label">Доходы</div>
                    </div>
                    <div class="kpi-amount">{fmt(inc)} ₽</div>
                    <div class="kpi-sub">За выбранный период</div>
                </div>
                <div class="kpi">
                    <div class="kpi-head">
                        <div class="kpi-badge badge-red">↓</div>
                        <div class="kpi-label">Расходы</div>
                    </div>
                    <div class="kpi-amount">{fmt(exp)} ₽</div>
                    <div class="kpi-sub">За выбранный период</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # ── CASH FLOW ──
        st.markdown("""
            <div class="section">
                <div class="section-title-wrap">
                    <span class="section-dot" style="background:#4F46E5"></span>
                    <span class="section-title">Cash Flow</span>
                </div>
                <div class="section-sub">Динамика по дням</div>
            </div>
        """, unsafe_allow_html=True)

        daily = f_df.copy()
        daily['_d'] = daily['Дата'].dt.normalize()

        # Полный диапазон дат периода (заполняем нулями где нет операций)
        if isinstance(period, tuple) and len(period) == 2:
            p_start, p_end = pd.to_datetime(period[0]), pd.to_datetime(period[1])
        else:
            p_start, p_end = pd.to_datetime(min_d), pd.to_datetime(max_d)

        all_days = pd.date_range(p_start, p_end, freq='D')
        x_labels = [d.strftime('%d.%m') for d in all_days]

        def daily_sum(sub):
            if sub.empty:
                return [0] * len(all_days)
            grouped = sub.groupby('_d')['Сумма'].sum()
            return [float(grouped.get(d, 0)) for d in all_days]

        inc_vals = daily_sum(daily[daily['Доход/Расход'] == 'Доход'])
        exp_vals = daily_sum(daily[daily['Доход/Расход'] == 'Расход'])

        fig = go.Figure()
        if sum(inc_vals) > 0:
            fig.add_trace(go.Scatter(
                x=x_labels, y=inc_vals,
                mode='lines+markers', name='Доходы',
                line=dict(color='#00C896', width=3, shape='spline', smoothing=0.6),
                marker=dict(size=10, color='#00C896',
                            line=dict(width=3, color='white')),
                fill='tozeroy', fillcolor='rgba(0, 200, 150, 0.12)',
                hovertemplate='<b>+%{y:,.0f} ₽</b><br>%{x}<extra></extra>'
            ))
        if sum(exp_vals) > 0:
            fig.add_trace(go.Scatter(
                x=x_labels, y=exp_vals,
                mode='lines+markers', name='Расходы',
                line=dict(color='#FF5757', width=3, shape='spline', smoothing=0.6),
                marker=dict(size=10, color='#FF5757',
                            line=dict(width=3, color='white')),
                fill='tozeroy', fillcolor='rgba(255, 87, 87, 0.10)',
                hovertemplate='<b>−%{y:,.0f} ₽</b><br>%{x}<extra></extra>'
            ))
        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor='white', paper_bgcolor='white',
            hovermode='x unified',
            font=dict(family='Plus Jakarta Sans'),
            xaxis=dict(
                type='category',
                showgrid=False, showline=False,
                tickfont=dict(size=11, color='#94A3B8')
            ),
            yaxis=dict(showgrid=True, gridcolor='#F1F5F9',
                       showline=False, zeroline=False, tickformat=',',
                       tickfont=dict(size=11, color='#94A3B8')),
            legend=dict(orientation='h', yanchor='bottom', y=1.05,
                        xanchor='right', x=1,
                        font=dict(size=12, color='#475569'),
                        bgcolor='rgba(0,0,0,0)')
        )
        st.plotly_chart(fig, use_container_width=True,
                        config={'displayModeBar': False})

        # ── СТРУКТУРА РАСХОДОВ ──
        render_breakdown(
            title='Структура расходов',
            sub='По категориям',
            dot_color='#EF4444',
            dataframe=f_df[f_df['Доход/Расход'] == 'Расход'],
            palette=EXP_COLORS
        )

        # ── СТРУКТУРА ДОХОДОВ ──
        render_breakdown(
            title='Источники дохода',
            sub='По категориям',
            dot_color='#10B981',
            dataframe=f_df[f_df['Доход/Расход'] == 'Доход'],
            palette=INC_COLORS
        )

except Exception as e:
    st.error(f"Упс! Что-то пошло не так: {e}")
