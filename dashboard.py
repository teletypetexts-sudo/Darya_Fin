import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.graph_objects as go
import urllib.parse
import html as html_lib
import os

# ═══════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="My Finance",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════════
# ПРЕМИУМ CSS
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

    /* ═══ ЛОГО ═══ */
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
    }
    .logo-emoji { -webkit-text-fill-color: initial; background: none; }

    /* ═══ HERO ═══ */
    .hero {
        background: linear-gradient(135deg, #1E1B4B 0%, #4F46E5 50%, #7C3AED 100%);
        border-radius: 28px;
        padding: 36px 40px 42px 40px;
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
        font-size: 11px; font-weight: 600; letter-spacing: 2.5px;
        text-transform: uppercase; opacity: 0.7;
        margin-bottom: 12px; position: relative;
    }
    .hero-amount {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 58px; font-weight: 700; letter-spacing: -2.5px;
        line-height: 1; margin-bottom: 22px; position: relative;
    }

    /* ═══ HERO PILLS ═══ */
    .hero-pills { display: flex; gap: 10px; flex-wrap: wrap; position: relative; }
    .pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: linear-gradient(135deg, rgba(255,255,255,0.22) 0%, rgba(255,255,255,0.10) 100%);
        padding: 8px 16px 8px 8px;
        border-radius: 100px;
        font-size: 13px;
        font-weight: 600;
        border: 1px solid rgba(255,255,255,0.18);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.30),
            inset 0 -1px 0 rgba(0,0,0,0.08),
            0 4px 12px rgba(0,0,0,0.18);
    }
    .pill-icon {
        width: 28px;
        height: 28px;
        aspect-ratio: 1 / 1;
        flex-shrink: 0;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        line-height: 1;
        background: linear-gradient(135deg, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.12) 100%);
        box-shadow:
            inset 0 1px 0 rgba(255,255,255,0.5),
            inset 0 -2px 3px rgba(0,0,0,0.12),
            0 3px 8px rgba(0,0,0,0.18);
    }
    .pill-text { display: flex; flex-direction: column; line-height: 1.15; }
    .pill-value {
        font-family: 'Space Grotesk';
        font-weight: 700;
        font-size: 14px;
    }
    .pill-label {
        font-size: 10px;
        opacity: 0.78;
        font-weight: 600;
        margin-top: 1px;
    }

    /* ═══ KPI ═══ */
    .kpi-grid {
        display: grid; grid-template-columns: 1fr 1fr;
        gap: 14px; margin-bottom: 8px;
    }
    .kpi {
        background: white; border-radius: 20px; padding: 22px;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
        border: 1px solid rgba(15, 23, 42, 0.04);
        transition: all 0.25s ease;
    }
    .kpi:hover {
        transform: translateY(-3px);
        box-shadow: 0 16px 32px rgba(15, 23, 42, 0.08);
    }
    .kpi-head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }

    .kpi-icon {
        width: 38px;
        height: 38px;
        aspect-ratio: 1 / 1;
        flex-shrink: 0;
        border-radius: 12px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        line-height: 1;
        font-weight: 700;
        color: white;
    }
    .icon-green {
        background: linear-gradient(135deg, #00E5B0 0%, #00A578 100%);
        box-shadow:
            0 8px 18px -4px rgba(0,200,150,0.55),
            inset 0 1px 0 rgba(255,255,255,0.40),
            inset 0 -2px 4px rgba(0,0,0,0.15);
    }
    .icon-red {
        background: linear-gradient(135deg, #FF7B7B 0%, #E13C3C 100%);
        box-shadow:
            0 8px 18px -4px rgba(255,87,87,0.55),
            inset 0 1px 0 rgba(255,255,255,0.40),
            inset 0 -2px 4px rgba(0,0,0,0.15);
    }

    .kpi-label {
        font-size: 11px; font-weight: 700; text-transform: uppercase;
        letter-spacing: 1.5px; color: #64748B;
    }
    .kpi-amount {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 28px; font-weight: 700; letter-spacing: -1px;
        color: #0F172A; line-height: 1; margin-bottom: 8px;
    }
    .kpi-sub { font-size: 12px; color: #94A3B8; font-weight: 500; }

    /* ═══ СЕКЦИИ ═══ */
    .section {
        display: flex; align-items: center; justify-content: space-between;
        margin: 32px 0 14px 0;
    }
    .section-title {
        font-size: 19px; font-weight: 700; color: #0F172A; letter-spacing: -0.5px;
    }
    .section-sub { font-size: 12px; color: #94A3B8; font-weight: 500; }

    .chart-card {
        background: white; border-radius: 20px; padding: 24px;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
        border: 1px solid rgba(15, 23, 42, 0.04);
        margin-bottom: 16px;
    }

    /* ═══ СПИСОК КАТЕГОРИЙ ═══ */
    .cat-list {
        background: white; border-radius: 20px; padding: 8px;
        box-shadow: 0 2px 12px rgba(15, 23, 42, 0.04);
        border: 1px solid rgba(15, 23, 42, 0.04);
        overflow: visible;
    }
    .cat-link {
        text-decoration: none !important; color: inherit !important;
        display: block; border-radius: 14px;
        transition: background 0.18s ease; cursor: pointer;
    }
    .cat-link:hover { background: #F8FAFC; }
    .cat-link.active { background: #EEF2FF; }
    .cat-row {
        display: flex; align-items: center; gap: 14px;
        padding: 12px 14px;
    }
    .cat-icon {
        width: 44px;
        height: 44px;
        aspect-ratio: 1 / 1;
        flex-shrink: 0;
        border-radius: 13px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 21px;
        line-height: 1;
    }
    .cat-info { flex: 1; min-width: 0; }
    .cat-name {
        font-weight: 600; color: #0F172A; font-size: 14px; margin-bottom: 6px;
    }
    .cat-bar-wrap {
        height: 6px; background: #F1F5F9; border-radius: 100px; overflow: hidden;
    }
    .cat-bar { height: 100%; border-radius: 100px; box-shadow: inset 0 -1px 0 rgba(0,0,0,0.08); }
    .cat-right { text-align: right; flex-shrink: 0; }
    .cat-amount {
        font-family: 'Space Grotesk'; font-weight: 700;
        font-size: 14px; color: #0F172A;
    }
    .cat-pct { font-size: 11px; color: #94A3B8; font-weight: 600; }
    .cat-chev {
        color: #CBD5E1; font-size: 18px; font-weight: 700;
        margin-left: 4px; flex-shrink: 0;
    }
    .cat-link:hover .cat-chev { color: #4F46E5; }

    /* ═══ ДЕТАЛЬНЫЙ ВИД ═══ */
    .tx-card {
        background: white; border-radius: 24px;
        box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
        border: 1px solid rgba(15, 23, 42, 0.04);
        overflow: hidden; margin-top: 8px;
    }
    .tx-header {
        display: flex; align-items: center; gap: 16px;
        padding: 22px 24px;
        background: linear-gradient(135deg, #FAFBFC 0%, #F4F6F9 100%);
        border-bottom: 1px solid #F1F5F9;
    }
    .tx-header-icon {
        width: 56px;
        height: 56px;
        aspect-ratio: 1 / 1;
        flex-shrink: 0;
        border-radius: 17px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        line-height: 1;
    }
    .tx-header-info { flex: 1; min-width: 0; }
    .tx-header-name {
        font-weight: 700; font-size: 19px; color: #0F172A;
        letter-spacing: -0.4px; line-height: 1.2;
    }
    .tx-header-stats {
        font-size: 12px; color: #94A3B8; font-weight: 600; margin-top: 4px;
    }
    .tx-header-stats b {
        font-family: 'Space Grotesk'; color: #475569; font-weight: 700;
    }
    .tx-back {
        width: 40px; height: 40px;
        aspect-ratio: 1 / 1;
        flex-shrink: 0;
        border-radius: 12px;
        background: white; color: #475569 !important;
        display: flex; align-items: center; justify-content: center;
        text-decoration: none !important;
        font-size: 18px; font-weight: 600;
        box-shadow: 0 1px 4px rgba(15,23,42,0.06);
        transition: all 0.15s ease;
    }
    .tx-back:hover {
        background: #4F46E5; color: white !important; transform: translateX(-2px);
    }

    .tx-row {
        display: flex; align-items: center; gap: 16px;
        padding: 16px 24px; border-bottom: 1px solid #F4F6F9;
        transition: background 0.15s ease;
    }
    .tx-row:hover { background: #FAFBFC; }
    .tx-row:last-child { border-bottom: none; }
    .tx-date {
        width: 46px; text-align: center;
        background: #F1F5F9; border-radius: 10px;
        padding: 8px 0; flex-shrink: 0;
        box-shadow: inset 0 -1px 0 rgba(0,0,0,0.03);
    }
    .tx-day {
        font-family: 'Space Grotesk'; font-size: 18px; font-weight: 700;
        color: #0F172A; line-height: 1;
    }
    .tx-month {
        font-size: 9px; color: #94A3B8; font-weight: 700;
        text-transform: uppercase; letter-spacing: 1px; margin-top: 3px;
    }
    .tx-desc {
        flex: 1; font-size: 14px; color: #334155; font-weight: 500;
        line-height: 1.4; min-width: 0; word-break: break-word;
    }
    .tx-amount {
        font-family: 'Space Grotesk'; font-weight: 700;
        font-size: 16px; color: #E13C3C; flex-shrink: 0; letter-spacing: -0.3px;
    }

    /* ═══ DATE INPUT ═══ */
    div[data-testid="stDateInput"] > label { display: none !important; }
    div[data-testid="stDateInput"] > div {
        background: white; border-radius: 100px; padding: 4px 10px;
        box-shadow: 0 2px 10px rgba(15, 23, 42, 0.05);
        border: 1px solid rgba(15, 23, 42, 0.06);
    }
    div[data-testid="stDateInput"] input {
        font-family: 'Plus Jakarta Sans' !important;
        font-weight: 600 !important; color: #0F172A !important;
        font-size: 13px !important; border: none !important;
    }

    /* ═══ МОБИЛКА ═══ */
    @media (max-width: 640px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .logo { font-size: 24px; }
        .hero {
            padding: 26px 20px 32px 20px;
            border-radius: 24px;
        }
        .hero-amount {
            font-size: 38px;
            letter-spacing: -1.5px;
            margin-bottom: 20px;
        }
        .hero-pills { gap: 8px; }
        .pill {
            padding: 7px 14px 7px 7px;
            font-size: 12px;
            gap: 7px;
        }
        .pill-icon {
            width: 26px;
            height: 26px;
            font-size: 13px;
        }
        .pill-value { font-size: 13px; }
        .pill-label { font-size: 9px; letter-spacing: 0.2px; }
        .kpi-grid { gap: 10px; }
        .kpi { padding: 16px; }
        .kpi-amount { font-size: 22px; }
        .kpi-icon {
            width: 34px;
            height: 34px;
            font-size: 16px;
        }
        .kpi-sub { font-size: 11px; }
        .chart-card { padding: 16px; border-radius: 16px; }
        .cat-list { padding: 6px; border-radius: 16px; }
        .section-title { font-size: 16px; }
        .cat-icon {
            width: 40px;
            height: 40px;
            font-size: 19px;
        }
        .cat-row { gap: 12px; padding: 10px 10px; }
        .cat-name { font-size: 13px; }
        .cat-amount { font-size: 13px; }
        .tx-header { padding: 18px 16px; gap: 12px; }
        .tx-header-icon {
            width: 50px;
            height: 50px;
            font-size: 24px;
        }
        .tx-header-name { font-size: 16px; }
        .tx-row { padding: 14px 16px; gap: 12px; }
        .tx-amount { font-size: 14px; }
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# КОНСТАНТЫ
# ═══════════════════════════════════════════════════════════
CAT_COLORS = ['#4F46E5', '#00C896', '#F59E0B', '#EC4899', '#06B6D4',
              '#8B5CF6', '#EF4444', '#10B981', '#F97316', '#3B82F6',
              '#A855F7', '#14B8A6']

MONTHS_RU = ['янв', 'фев', 'мар', 'апр', 'май', 'июн',
             'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']


def cat_icon(cat):
    c = str(cat).lower()
    m = {
        'еда': '🛒', 'продукт': '🛒', 'супермаркет': '🛒', 'магазин': '🛍️',
        'кафе': '☕', 'ресторан': '🍽️', 'кофе': '☕', 'бар': '🍷',
        'транспорт': '🚗', 'такси': '🚕', 'бензин': '⛽', 'авто': '🚗',
        'метро': '🚇', 'жил': '🏠', 'дом': '🏠', 'квартир': '🏠', 'аренд': '🏠',
        'коммунал': '💡', 'одежд': '👕', 'обув': '👟',
        'красот': '💄', 'космет': '💄', 'уход': '✨',
        'здоров': '🏥', 'аптек': '💊', 'медиц': '🏥',
        'развлеч': '🎬', 'кино': '🎬', 'игр': '🎮',
        'спорт': '🏋️', 'фитнес': '🏋️', 'йог': '🧘',
        'путеш': '✈️', 'отпуск': '✈️', 'отел': '🏨',
        'зарплат': '💼', 'доход': '💰', 'бонус': '🎁', 'фриланс': '💻',
        'подарок': '🎁', 'подарк': '🎁',
        'связь': '📱', 'интернет': '📡', 'телефон': '📱',
        'образован': '📚', 'учеб': '📚', 'курс': '📚', 'книг': '📖',
        'животн': '🐾', 'питом': '🐾',
        'дет': '👶', 'хобби': '🎨', 'налог': '🧾', 'долг': '💳',
        'инвест': '📈', 'накоплен': '🏦',
    }
    for key, icon in m.items():
        if key in c:
            return icon
    return '💳'


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def icon_3d_style(color):
    r, g, b = hex_to_rgb(color)
    return (
        f"background: linear-gradient(135deg, "
        f"rgba({r},{g},{b},0.18) 0%, rgba({r},{g},{b},0.36) 100%);"
        f"box-shadow: "
        f"0 6px 14px -3px rgba({r},{g},{b},0.45), "
        f"inset 0 1px 0 rgba(255,255,255,0.7), "
        f"inset 0 -2px 4px rgba({r},{g},{b},0.22);"
    )


def bar_gradient(color):
    r, g, b = hex_to_rgb(color)
    return (
        f"background: linear-gradient(90deg, "
        f"rgba({r},{g},{b},1) 0%, rgba({r},{g},{b},0.85) 100%);"
    )


# ═══════════════════════════════════════════════════════════
# ДАННЫЕ
# ═══════════════════════════════════════════════════════════
def get_credentials(scopes):
    """
    Получает Google credentials:
    - на Streamlit Cloud — из st.secrets["gcp_service_account"]
    - локально — из файла credentials.json
    """
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            return Credentials.from_service_account_info(creds_dict, scopes=scopes)
    except Exception:
        pass
    # Локальный режим
    return Credentials.from_service_account_file('credentials.json', scopes=scopes)


@st.cache_data(ttl=300)
def load_data():
    SHEET_ID = '1JwZWJbjORChtUmuJQiJisSZMrBr5TaBjKSxxuA1HdEU'
    scopes = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']
    creds = get_credentials(scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    df = pd.DataFrame(sheet.get_all_records())

    if not df.empty:
        df['Сумма'] = pd.to_numeric(df['Сумма'], errors='coerce').fillna(0)
        df['Дата'] = pd.to_datetime(df['Дата'], format='%d.%m.%Y', errors='coerce').fillna(
                     pd.to_datetime(df['Дата'], format='%d.%m.%y', errors='coerce'))
        df = df.dropna(subset=['Дата'])
    return df


def fmt(n):
    return f"{n:,.0f}".replace(",", " ")


# ═══════════════════════════════════════════════════════════
# UI
# ═══════════════════════════════════════════════════════════
try:
    df = load_data()

    if df.empty:
        st.warning("В таблице нет данных.")
    else:
        try:
            selected_cat = st.query_params.get("cat", "")
        except Exception:
            selected_cat = ""

        # Шапка
        col_logo, col_date = st.columns([1.5, 1])
        with col_logo:
            st.markdown(
                '<div class="logo"><span class="logo-emoji">💎</span>My Finance</div>',
                unsafe_allow_html=True
            )
        with col_date:
            min_d, max_d = df['Дата'].min().date(), df['Дата'].max().date()
            period = st.date_input(
                "Период", value=(min_d, max_d),
                min_value=min_d, max_value=max_d,
                label_visibility="collapsed"
            )

        if isinstance(period, tuple) and len(period) == 2:
            f_df = df[(df['Дата'].dt.date >= period[0]) &
                      (df['Дата'].dt.date <= period[1])]
            days_count = (period[1] - period[0]).days + 1
        else:
            f_df = df
            days_count = (max_d - min_d).days + 1

        inc = f_df[f_df['Доход/Расход'] == 'Доход']['Сумма'].sum()
        exp = f_df[f_df['Доход/Расход'] == 'Расход']['Сумма'].sum()
        balance = inc - exp
        savings_rate = (balance / inc * 100) if inc > 0 else 0

        earn_per_day = inc / days_count if days_count > 0 else 0
        exp_per_day = exp / days_count if days_count > 0 else 0
        monthly_pace = (balance / days_count * 30) if days_count > 0 else 0
        sign = "+" if balance >= 0 else "−"
        pace_sign = "+" if monthly_pace >= 0 else "−"

        # HERO
        st.markdown(f"""
            <div class="hero">
                <div class="hero-label">Общий баланс</div>
                <div class="hero-amount">{sign}{fmt(abs(balance))} ₽</div>
                <div class="hero-pills">
                    <div class="pill">
                        <div class="pill-icon">⚡</div>
                        <div class="pill-text">
                            <div class="pill-value">{fmt(earn_per_day)} ₽</div>
                            <div class="pill-label">в день зарабатываю</div>
                        </div>
                    </div>
                    <div class="pill">
                        <div class="pill-icon">🎯</div>
                        <div class="pill-text">
                            <div class="pill-value">{savings_rate:.0f}%</div>
                            <div class="pill-label">отложила</div>
                        </div>
                    </div>
                    <div class="pill">
                        <div class="pill-icon">🚀</div>
                        <div class="pill-text">
                            <div class="pill-value">{pace_sign}{fmt(abs(monthly_pace))} ₽</div>
                            <div class="pill-label">темп за месяц</div>
                        </div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # KPI
        st.markdown(f"""
            <div class="kpi-grid">
                <div class="kpi">
                    <div class="kpi-head">
                        <div class="kpi-icon icon-green">↑</div>
                        <div class="kpi-label">Доходы</div>
                    </div>
                    <div class="kpi-amount">{fmt(inc)} ₽</div>
                    <div class="kpi-sub">≈ {fmt(earn_per_day)} ₽ в день</div>
                </div>
                <div class="kpi">
                    <div class="kpi-head">
                        <div class="kpi-icon icon-red">↓</div>
                        <div class="kpi-label">Расходы</div>
                    </div>
                    <div class="kpi-amount">{fmt(exp)} ₽</div>
                    <div class="kpi-sub">≈ {fmt(exp_per_day)} ₽ в день</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # CASH FLOW
        st.markdown("""
            <div class="section">
                <div class="section-title">📊 Cash Flow</div>
                <div class="section-sub">Динамика по дням</div>
            </div>
        """, unsafe_allow_html=True)

        daily = f_df.groupby([f_df['Дата'].dt.date, 'Доход/Расход'])['Сумма'].sum().reset_index()
        d_inc = daily[daily['Доход/Расход'] == 'Доход']
        d_exp = daily[daily['Доход/Расход'] == 'Расход']

        fig = go.Figure()
        if not d_inc.empty:
            fig.add_trace(go.Scatter(
                x=d_inc['Дата'], y=d_inc['Сумма'],
                mode='lines', name='Доходы',
                line=dict(color='#00C896', width=3, shape='spline', smoothing=0.6),
                fill='tozeroy', fillcolor='rgba(0, 200, 150, 0.12)',
                hovertemplate='<b>+%{y:,.0f} ₽</b><br>%{x|%d.%m.%Y}<extra></extra>'
            ))
        if not d_exp.empty:
            fig.add_trace(go.Scatter(
                x=d_exp['Дата'], y=d_exp['Сумма'],
                mode='lines', name='Расходы',
                line=dict(color='#FF5757', width=3, shape='spline', smoothing=0.6),
                fill='tozeroy', fillcolor='rgba(255, 87, 87, 0.10)',
                hovertemplate='<b>−%{y:,.0f} ₽</b><br>%{x|%d.%m.%Y}<extra></extra>'
            ))
        fig.update_layout(
            height=300, margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor='white', paper_bgcolor='white',
            hovermode='x unified',
            font=dict(family='Plus Jakarta Sans'),
            xaxis=dict(showgrid=False, showline=False,
                       tickfont=dict(size=11, color='#94A3B8')),
            yaxis=dict(showgrid=True, gridcolor='#F1F5F9',
                       showline=False, zeroline=False, tickformat=',',
                       tickfont=dict(size=11, color='#94A3B8')),
            legend=dict(orientation='h', yanchor='bottom', y=1.05,
                        xanchor='right', x=1,
                        font=dict(size=12, color='#475569'),
                        bgcolor='rgba(0,0,0,0)')
        )
        st.markdown('<div class="chart-card">', unsafe_allow_html=True)
        st.plotly_chart(fig, use_container_width=True,
                        config={'displayModeBar': False})
        st.markdown('</div>', unsafe_allow_html=True)

        # СТРУКТУРА РАСХОДОВ
        exp_df = f_df[f_df['Доход/Расход'] == 'Расход']

        if not exp_df.empty:
            cats = exp_df.groupby('Категория')['Сумма'].sum().sort_values(ascending=False)
            total = cats.sum()

            st.markdown("""
                <div class="section">
                    <div class="section-title">🎯 Структура расходов</div>
                    <div class="section-sub">Нажми на категорию для деталей</div>
                </div>
            """, unsafe_allow_html=True)

            col_donut, col_list = st.columns([1, 1.2])

            with col_donut:
                colors_list = [CAT_COLORS[i % len(CAT_COLORS)] for i in range(len(cats))]
                fig_d = go.Figure(go.Pie(
                    labels=cats.index, values=cats.values,
                    hole=0.72,
                    marker=dict(colors=colors_list, line=dict(color='white', width=3)),
                    textinfo='none',
                    hovertemplate='<b>%{label}</b><br>%{value:,.0f} ₽<br>%{percent}<extra></extra>',
                    sort=False
                ))
                fig_d.update_layout(
                    height=320, margin=dict(l=0, r=0, t=0, b=0),
                    showlegend=False, paper_bgcolor='white',
                    annotations=[dict(
                        text=f"<b>{fmt(total)}</b><br><span style='font-size:11px;color:#94A3B8'>₽ всего</span>",
                        x=0.5, y=0.5,
                        font=dict(size=22, color='#0F172A', family='Space Grotesk'),
                        showarrow=False
                    )]
                )
                st.markdown('<div class="chart-card">', unsafe_allow_html=True)
                st.plotly_chart(fig_d, use_container_width=True,
                                config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)

            with col_list:
                rows_html = '<div class="cat-list">'
                for i, (cat, val) in enumerate(cats.items()):
                    pct = (val / total * 100)
                    color = CAT_COLORS[i % len(CAT_COLORS)]
                    cat_url = urllib.parse.quote(str(cat))
                    active = " active" if str(cat) == selected_cat else ""
                    cat_safe = html_lib.escape(str(cat))
                    icon_style = icon_3d_style(color)
                    bar_style = bar_gradient(color)
                    rows_html += f"""
                    <a href="?cat={cat_url}" target="_self" class="cat-link{active}">
                        <div class="cat-row">
                            <div class="cat-icon" style="{icon_style}">{cat_icon(cat)}</div>
                            <div class="cat-info">
                                <div class="cat-name">{cat_safe}</div>
                                <div class="cat-bar-wrap">
                                    <div class="cat-bar" style="width:{pct:.1f}%; {bar_style}"></div>
                                </div>
                            </div>
                            <div class="cat-right">
                                <div class="cat-amount">{fmt(val)} ₽</div>
                                <div class="cat-pct">{pct:.1f}%</div>
                            </div>
                            <div class="cat-chev">›</div>
                        </div>
                    </a>
                    """
                rows_html += '</div>'
                st.markdown(rows_html, unsafe_allow_html=True)

            # ── ДЕТАЛЬНЫЙ ВИД ──
            if selected_cat and selected_cat in cats.index:
                cat_total = cats[selected_cat]
                cat_idx = list(cats.index).index(selected_cat)
                color = CAT_COLORS[cat_idx % len(CAT_COLORS)]
                icon = cat_icon(selected_cat)
                header_icon_style = icon_3d_style(color)

                tx_df = exp_df[exp_df['Категория'] == selected_cat] \
                    .sort_values('Дата', ascending=False)
                tx_count = len(tx_df)

                extra_cols = [c for c in tx_df.columns
                              if c not in ['Сумма', 'Категория',
                                           'Доход/Расход', 'Дата']]

                st.markdown(f"""
                    <div class="section">
                        <div class="section-title">📋 {html_lib.escape(str(selected_cat))}</div>
                        <div class="section-sub">Все операции в категории</div>
                    </div>
                """, unsafe_allow_html=True)

                cat_safe = html_lib.escape(str(selected_cat))
                detail_html = f"""
                <div class="tx-card">
                    <div class="tx-header">
                        <div class="tx-header-icon" style="{header_icon_style}">{icon}</div>
                        <div class="tx-header-info">
                            <div class="tx-header-name">{cat_safe}</div>
                            <div class="tx-header-stats">
                                <b>{tx_count}</b> операций · <b>{fmt(cat_total)} ₽</b>
                            </div>
                        </div>
                        <a href="?" target="_self" class="tx-back" title="Назад">←</a>
                    </div>
                """

                for _, tx in tx_df.iterrows():
                    day = tx['Дата'].day
                    month = MONTHS_RU[tx['Дата'].month - 1]
                    amount = tx['Сумма']
                    desc = ""
                    for c in extra_cols:
                        v = tx[c]
                        if pd.notna(v) and str(v).strip():
                            desc = str(v).strip()
                            break
                    if not desc:
                        desc = str(selected_cat)

                    detail_html += f"""
                    <div class="tx-row">
                        <div class="tx-date">
                            <div class="tx-day">{day}</div>
                            <div class="tx-month">{month}</div>
                        </div>
                        <div class="tx-desc">{html_lib.escape(desc)}</div>
                        <div class="tx-amount">−{fmt(amount)} ₽</div>
                    </div>
                    """

                detail_html += "</div>"
                st.markdown(detail_html, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Упс! Что-то пошло не так: {e}")
