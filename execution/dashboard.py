import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import pyodbc
import os
import base64
import plotly.express as px
import plotly.graph_objects as go
from dotenv import load_dotenv
import json

# Page config
st.set_page_config(
    page_title="Esopo Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🐄"
)

# Styling — Premium Glassmorphism Theme
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0');

    :root {
        /* Core Palette — Rural Premium */
        --primary-green: #064e3b;
        --primary-green-light: #059669;
        --accent-magenta: #be185d;
        --accent-magenta-glow: rgba(190, 24, 93, 0.25);
        --accent-amber: #d97706;

        /* Grays */
        --bg-screen: #f1f5f9;
        --bg-panel: #1e293b;
        --bg-panel-alt: #0f172a;
        --surface-white: #ffffff;
        --text-primary: #0f172a;
        --text-secondary: #475569;
        --text-muted: #94a3b8;
        --text-on-dark: #f8fafc;

        /* Glass */
        --glass-bg: rgba(255, 255, 255, 0.75);
        --glass-bg-strong: rgba(255, 255, 255, 0.88);
        --glass-border: rgba(255, 255, 255, 0.4);
        --glass-blur: 20px;

        /* Shadows */
        --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.04);
        --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.06);
        --shadow-lg: 0 16px 48px rgba(0, 0, 0, 0.08);
        --shadow-glow-green: 0 4px 20px rgba(6, 78, 59, 0.15);
        --shadow-glow-magenta: 0 4px 20px rgba(190, 24, 93, 0.15);

        /* Radius */
        --radius-sm: 10px;
        --radius-md: 16px;
        --radius-lg: 24px;
        --radius-xl: 32px;
    }

    /* ============ GLOBAL ============ */
    *, *::before, *::after {
        font-family: 'Outfit', sans-serif !important;
    }

    .main {
        background: var(--bg-screen) !important;
        color: var(--text-primary);
    }

    body, [data-testid="stAppViewContainer"] {
        font-family: 'Outfit', sans-serif !important;
        background: var(--bg-screen);
    }

    /* Material Symbols helper */
    .mat-icon {
        font-family: 'Material Symbols Outlined' !important;
        font-weight: normal;
        font-style: normal;
        font-size: 22px;
        display: inline-block;
        line-height: 1;
        text-transform: none;
        letter-spacing: normal;
        word-wrap: normal;
        white-space: nowrap;
        direction: ltr;
        vertical-align: middle;
        -webkit-font-smoothing: antialiased;
    }

    /* ============ SIDEBAR — Premium Glass ============ */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--bg-panel-alt) 0%, var(--bg-panel) 100%) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.06) !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15);
    }

    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span {
        color: var(--text-on-dark) !important;
    }

    /* Sidebar Title Area */
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: var(--text-on-dark) !important;
        text-shadow: 0 0 20px rgba(6, 78, 59, 0.3);
    }

    /* Sidebar Radio — Navigation Items */
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        gap: 4px;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        background: rgba(255, 255, 255, 0.04) !important;
        border-radius: var(--radius-sm) !important;
        padding: 12px 16px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 1px solid transparent !important;
        margin-bottom: 2px;
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        border-color: rgba(255, 255, 255, 0.1) !important;
        transform: translateX(4px);
    }

    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"],
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-baseweb="radio"]:has(input:checked) {
        background: rgba(6, 78, 59, 0.25) !important;
        border-color: var(--primary-green-light) !important;
        box-shadow: 0 0 12px rgba(6, 78, 59, 0.2);
    }

    /* Sidebar Info Box */
    section[data-testid="stSidebar"] [data-testid="stAlert"] {
        background: rgba(6, 78, 59, 0.15) !important;
        border: 1px solid rgba(6, 78, 59, 0.3) !important;
        border-radius: var(--radius-sm) !important;
        backdrop-filter: blur(8px);
        color: var(--text-on-dark) !important;
    }

    /* Sidebar Divider */
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.08) !important;
        margin: 16px 0 !important;
    }

    /* ============ METRIC CARDS — Glass + Gradient Accent ============ */
    div[data-testid="stMetric"] {
        background: var(--glass-bg-strong);
        backdrop-filter: blur(var(--glass-blur));
        -webkit-backdrop-filter: blur(var(--glass-blur));
        border: 1px solid var(--glass-border);
        border-radius: var(--radius-md);
        padding: 24px 20px;
        box-shadow: var(--shadow-md);
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        animation: fadeSlideUp 0.6s ease-out;
    }

    /* Gradient accent bar on left side */
    div[data-testid="stMetric"]::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: linear-gradient(180deg, var(--primary-green) 0%, var(--accent-magenta) 100%);
        border-radius: 4px 0 0 4px;
    }

    div[data-testid="stMetric"]:hover {
        transform: translateY(-6px);
        box-shadow: var(--shadow-lg), var(--shadow-glow-green);
    }

    div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: var(--text-secondary) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: var(--text-primary) !important;
    }

    /* ============ BUTTONS — Premium ============ */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-green) 0%, var(--primary-green-light) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        letter-spacing: 0.3px;
        box-shadow: var(--shadow-glow-green);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: var(--shadow-glow-green), 0 8px 24px rgba(6, 78, 59, 0.2) !important;
    }

    /* ============ MULTISELECT & INPUTS ============ */
    .stMultiSelect > div {
        border-radius: var(--radius-sm) !important;
    }

    .stMultiSelect [data-baseweb="tag"] {
        background: var(--primary-green) !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="select"] > div {
        border-radius: var(--radius-sm) !important;
        border-color: #e2e8f0 !important;
        transition: border-color 0.3s, box-shadow 0.3s !important;
    }

    div[data-baseweb="select"] > div:focus-within {
        border-color: var(--primary-green-light) !important;
        box-shadow: 0 0 0 3px rgba(6, 78, 59, 0.15) !important;
    }

    /* ============ SLIDER ============ */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background: var(--primary-green) !important;
    }

    .stSlider [data-baseweb="slider"] div[data-testid="stTickBar"] {
        background: var(--primary-green-light) !important;
    }

    /* ============ RADIO (Main Content) ============ */
    .stRadio > div[role="radiogroup"] label {
        background: var(--glass-bg) !important;
        backdrop-filter: blur(10px);
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-sm) !important;
        padding: 10px 18px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .stRadio > div[role="radiogroup"] label:hover {
        border-color: var(--primary-green-light) !important;
        box-shadow: var(--shadow-sm);
    }

    /* ============ TITLES & TYPOGRAPHY ============ */
    h1 {
        color: var(--primary-green) !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        letter-spacing: -0.5px;
    }

    h2, h3 {
        color: var(--primary-green) !important;
        font-weight: 600 !important;
    }

    h4 {
        color: var(--text-secondary) !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.9rem !important;
    }

    /* ============ SECTION HEADERS — Custom ============ */
    .section-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 2px solid rgba(6, 78, 59, 0.1);
    }

    .section-header .icon-box {
        width: 40px;
        height: 40px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
    }

    .icon-green {
        background: linear-gradient(135deg, rgba(6, 78, 59, 0.12), rgba(5, 150, 105, 0.12));
        color: var(--primary-green);
    }

    .icon-magenta {
        background: linear-gradient(135deg, rgba(190, 24, 93, 0.12), rgba(219, 39, 119, 0.12));
        color: var(--accent-magenta);
    }

    .icon-amber {
        background: linear-gradient(135deg, rgba(217, 119, 6, 0.12), rgba(245, 158, 11, 0.12));
        color: var(--accent-amber);
    }

    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-primary);
    }

    .section-subtitle {
        font-size: 0.8rem;
        color: var(--text-muted);
    }

    /* ============ DATA TABLES — Modern ============ */
    [data-testid="stTable"],
    [data-testid="stDataFrame"] {
        border-radius: var(--radius-md) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-md) !important;
    }

    [data-testid="stDataFrame"] > div {
        border-radius: var(--radius-md) !important;
    }

    /* ============ TABS ============ */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--glass-bg);
        backdrop-filter: blur(10px);
        border-radius: var(--radius-sm);
        padding: 4px;
        gap: 4px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        font-weight: 500;
        transition: all 0.3s !important;
    }

    .stTabs [aria-selected="true"] {
        background: var(--primary-green) !important;
        color: white !important;
    }

    /* ============ INFO / WARNING / ERROR ============ */
    [data-testid="stAlert"] {
        border-radius: var(--radius-sm) !important;
        backdrop-filter: blur(8px);
    }

    /* ============ CONTAINERS ============ */
    [data-testid="stVerticalBlock"] > div:has(> [data-testid="stMetric"]) {
        gap: 16px;
    }

    /* Dividers */
    hr {
        border: none !important;
        border-top: 2px solid rgba(0, 0, 0, 0.04) !important;
        margin: 24px 0 !important;
    }

    /* ============ ANIMATIONS ============ */
    @keyframes fadeSlideUp {
        from {
            opacity: 0;
            transform: translateY(16px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    /* Animate all main containers */
    .main .block-container {
        animation: fadeIn 0.5s ease-out;
    }

    /* ============ SCROLLBAR ============ */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }

    ::-webkit-scrollbar-track {
        background: transparent;
    }

    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }

    /* ============ CUSTOM LOGO BANNER ============ */
    .esopo-brand {
        text-align: center;
        padding: 8px 0 16px 0;
    }

    .esopo-logo-box {
        width: 56px;
        height: 56px;
        margin: 0 auto 12px;
        background: linear-gradient(135deg, var(--primary-green) 0%, var(--accent-magenta) 100%);
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 28px;
        box-shadow: 0 8px 24px rgba(6, 78, 59, 0.25);
    }

    .esopo-brand-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--text-on-dark) !important;
        letter-spacing: 1px;
    }

    .esopo-brand-subtitle {
        font-size: 0.72rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-top: 2px;
    }

    /* ============ STAT HIGHLIGHT CARD (custom HTML) ============ */
    .stat-highlight {
        background: linear-gradient(135deg, var(--primary-green) 0%, rgba(6, 78, 59, 0.85) 100%);
        border-radius: var(--radius-md);
        padding: 20px;
        color: white;
        box-shadow: var(--shadow-glow-green);
        position: relative;
        overflow: hidden;
    }

    .stat-highlight::after {
        content: '';
        position: absolute;
        top: -50%;
        right: -50%;
        width: 100%;
        height: 100%;
        background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
        pointer-events: none;
    }

    .stat-highlight .stat-value {
        font-size: 2rem;
        font-weight: 700;
    }

    .stat-highlight .stat-label {
        font-size: 0.8rem;
        opacity: 0.8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* ============ TOGGLE ============ */
    .stToggle label span {
        font-weight: 500 !important;
    }

    /* ============ EXPANDER ============ */
    [data-testid="stExpander"] {
        background: var(--glass-bg-strong);
        backdrop-filter: blur(var(--glass-blur));
        border: 1px solid var(--glass-border) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: var(--shadow-sm);
    }

    /* ============ CUSTOM SIDEBAR NAV ITEMS ============ */
    .nav-custom-item {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 13px 16px;
        border-radius: 12px;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        border: 1px solid transparent;
        margin-bottom: 4px;
        text-decoration: none;
        color: #94a3b8;
        font-size: 0.9rem;
        font-weight: 500;
        position: relative;
        overflow: hidden;
    }

    .nav-custom-item:hover {
        background: rgba(255, 255, 255, 0.06);
        color: #e2e8f0;
        border-color: rgba(255, 255, 255, 0.08);
        transform: translateX(4px);
    }

    .nav-custom-item.active {
        background: rgba(6, 78, 59, 0.2);
        border-color: var(--primary-green-light);
        color: #f8fafc;
        font-weight: 600;
        box-shadow: 0 0 16px rgba(5, 150, 105, 0.15);
    }

    .nav-custom-item.active::before {
        content: '';
        position: absolute;
        left: 0;
        top: 20%;
        bottom: 20%;
        width: 3px;
        background: linear-gradient(180deg, var(--primary-green-light), var(--accent-magenta));
        border-radius: 0 3px 3px 0;
    }

    .nav-custom-item .nav-icon {
        width: 36px;
        height: 36px;
        min-width: 36px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s;
    }

    .nav-custom-item .nav-icon .mat-icon {
        font-size: 20px;
    }

    .nav-custom-item:not(.active) .nav-icon {
        background: rgba(255, 255, 255, 0.05);
        color: #94a3b8;
    }

    .nav-custom-item.active .nav-icon {
        background: linear-gradient(135deg, var(--primary-green), var(--primary-green-light));
        color: white;
        box-shadow: 0 4px 12px rgba(5, 150, 105, 0.3);
    }

    .nav-custom-item .nav-text {
        flex: 1;
        line-height: 1.3;
    }

    .nav-custom-item .nav-label {
        font-size: 0.82rem;
    }

    .nav-custom-item .nav-desc {
        font-size: 0.68rem;
        color: #64748b;
        font-weight: 400;
    }

    .nav-custom-item.active .nav-desc {
        color: #94a3b8;
    }

    /* Section label in sidebar */
    .sidebar-section-label {
        font-size: 0.68rem;
        text-transform: uppercase;
        color: #64748b;
        letter-spacing: 1.5px;
        padding: 0 16px;
        margin-bottom: 8px;
        font-weight: 600;
    }

    /* ============ MULTISELECT PILLS — Glass ============ */
    .stMultiSelect [data-baseweb="tag"] {
        background: rgba(6, 78, 59, 0.18) !important;
        backdrop-filter: blur(6px);
        border: 1px solid rgba(5, 150, 105, 0.3) !important;
        border-radius: 10px !important;
        color: var(--primary-green) !important;
        font-weight: 500 !important;
        padding: 4px 10px !important;
        transition: all 0.2s ease !important;
    }

    .stMultiSelect [data-baseweb="tag"]:hover {
        background: rgba(6, 78, 59, 0.28) !important;
        border-color: var(--primary-green-light) !important;
        box-shadow: 0 2px 8px rgba(6, 78, 59, 0.15);
    }

    .stMultiSelect [data-baseweb="tag"] span {
        color: var(--primary-green) !important;
        font-weight: 500 !important;
    }

    /* Tag close button */
    .stMultiSelect [data-baseweb="tag"] [role="presentation"] {
        color: var(--primary-green-light) !important;
    }

    /* Hide default radio in sidebar (we use custom nav) */
    section[data-testid="stSidebar"] .stRadio {
        display: none !important;
    }

    /* ============ SIDEBAR NAV BUTTONS — Premium Style ============ */
    section[data-testid="stSidebar"] .stButton {
        margin-bottom: 4px !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        background: rgba(255, 255, 255, 0.03) !important;
        color: #94a3b8 !important;
        border: 1px solid transparent !important;
        border-radius: 12px !important;
        padding: 14px 16px 14px 56px !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        box-shadow: none !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        letter-spacing: 0.2px !important;
        position: relative !important;
        overflow: visible !important;
        min-height: 48px !important;
    }

    /* Icon container via ::before */
    section[data-testid="stSidebar"] .stButton > button::before {
        font-family: 'Material Symbols Outlined' !important;
        font-size: 20px;
        font-weight: normal;
        font-style: normal;
        position: absolute;
        left: 12px;
        top: 50%;
        transform: translateY(-50%);
        width: 32px;
        height: 32px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.05);
        color: #64748b;
        transition: all 0.3s;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255, 255, 255, 0.07) !important;
        color: #e2e8f0 !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
        transform: translateX(4px) !important;
        box-shadow: none !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover::before {
        background: rgba(255, 255, 255, 0.1);
        color: #e2e8f0;
    }

    section[data-testid="stSidebar"] .stButton > button:active,
    section[data-testid="stSidebar"] .stButton > button:focus {
        box-shadow: none !important;
        outline: none !important;
    }

    /* --- Icon assignment by data-nav attribute (set via JS) --- */
    section[data-testid="stSidebar"] button[data-nav="resumo"]::before {
        content: 'dashboard' !important;
    }
    section[data-testid="stSidebar"] button[data-nav="peso"]::before {
        content: 'monitoring' !important;
    }
    section[data-testid="stSidebar"] button[data-nav="ficha"]::before {
        content: 'inventory_2' !important;
    }
    section[data-testid="stSidebar"] button[data-nav="planejamento"]::before {
        content: 'calculate' !important;
    }
    section[data-testid="stSidebar"] button[data-nav="calendario"]::before {
        content: 'calendar_month' !important;
    }
    /* Fallback: default icon if data-nav not yet set */
    section[data-testid="stSidebar"] .stButton > button:not([data-nav])::before {
        content: 'radio_button_unchecked';
    }

    /* ============ FARM SELECTOR LABEL ============ */
    .farm-selector-glass {
        background: var(--glass-bg-strong);
        backdrop-filter: blur(var(--glass-blur));
        border: 1px solid var(--glass-border);
        border-radius: var(--radius-md);
        padding: 16px 20px;
        box-shadow: var(--shadow-sm);
        margin-bottom: 16px;
    }

    </style>
    """, unsafe_allow_html=True)

# Load environment
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '..', '.env')
load_dotenv(dotenv_path=env_path)

def get_connection():
    return pyodbc.connect(f"DRIVER={os.getenv('DB_DRIVER')};SERVER={os.getenv('DB_SERVER')};DATABASE={os.getenv('DB_DATABASE')};UID={os.getenv('DB_USERNAME')};PWD={os.getenv('DB_PASSWORD')}")

def get_vipper_connection():
    return pyodbc.connect(f"DRIVER={os.getenv('DB_DRIVER')};SERVER={os.getenv('DB_SERVER')};DATABASE=Vipper_KNW;UID={os.getenv('DB_USERNAME')};PWD={os.getenv('DB_PASSWORD')}")

def format_br(val):
    if val is None: return "0,00"
    return f"{float(val):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_grid_df(df, fmt_dict):
    """Round numeric columns according to fmt_dict and replace NaN with '—'."""
    for col, spec in fmt_dict.items():
        if col in df.columns:
            try:
                decimals = int(spec.split('.')[1][0])
                df[col] = df[col].apply(
                    lambda x: round(float(x), decimals)
                    if pd.notna(x) and not isinstance(x, str)
                    else x
                )
            except (ValueError, IndexError, TypeError):
                pass
    return df.fillna('—')

def parse_icicle_selection(event_data, hierarchy_cols):
    """Parse on_select event from an icicle chart.
    
    Args:
        event_data: Return value from st.plotly_chart(on_select="rerun").
        hierarchy_cols: Column names in the icicle path (excluding root constant).
    Returns:
        dict of {col_name: value} for each hierarchy level down to the clicked node.
    """
    try:
        points = event_data.selection.points if event_data else []
    except (AttributeError, TypeError):
        return {}
    if not points:
        return {}
    point = points[0]
    point_id = point.get("id", "") if isinstance(point, dict) else ""
    if not point_id:
        return {}
    parts = point_id.split("/")
    if len(parts) <= 1:
        return {}  # Root node clicked — no filter
    filters = {}
    for i, col in enumerate(hierarchy_cols):
        idx = i + 1  # skip root
        if idx < len(parts):
            filters[col] = parts[idx]
    return filters

# --- Custom Plotly click-capture component ---
_plotly_click_component = components.declare_component(
    "plotly_click",
    path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "plotly_click_component")
)

def plotly_click_chart(fig, key, height=600):
    """Render a Plotly chart that captures click events on icicle/treemap nodes.
    Returns the clicked node data dict or None.
    """
    fig_json = fig.to_json()
    result = _plotly_click_component(fig_json=fig_json, height=height, key=key, default=None)
    return result

def parse_click_filter(click_data, hierarchy_cols):
    """Parse click data from plotly_click_chart into a filter dict.
    
    Args:
        click_data: Return from plotly_click_chart (dict with 'id' key or None).
        hierarchy_cols: Column names matching the icicle path (excluding root).
    Returns:
        dict of {col_name: value} for each hierarchy level down to the clicked node.
    """
    if not click_data or not isinstance(click_data, dict):
        return {}
    node_id = click_data.get('id', '')
    if not node_id:
        return {}
    parts = node_id.split('/')
    if len(parts) <= 1:
        return {}  # Root clicked
    filters = {}
    for i, col in enumerate(hierarchy_cols):
        idx = i + 1
        if idx < len(parts):
            filters[col] = parts[idx]
    return filters

def append_total_row(df, fmt_dict, qtd_col='Qtd'):
    """Append a formatted TOTAL row: sum for qty, mean for numeric cols.
    
    Must be called BEFORE format_grid_df so it operates on raw numeric data.
    """
    total = {}
    for col in df.columns:
        if col == qtd_col:
            total[col] = int(pd.to_numeric(df[col], errors='coerce').sum())
        elif pd.api.types.is_numeric_dtype(df[col]):
            val = df[col].mean()
            # Apply column format mask if available
            spec = fmt_dict.get(col, '')
            if spec and pd.notna(val):
                try:
                    total[col] = float(spec.replace('%', '').strip('{}').format(val))
                except (ValueError, TypeError):
                    total[col] = val
            else:
                total[col] = val
        else:
            total[col] = 'TOTAL' if col == df.columns[0] else ''
    total_df = pd.DataFrame([total])
    return pd.concat([df, total_df], ignore_index=True)

def get_base64_of_bin_file(bin_file):
    if os.path.exists(bin_file):
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return None

def main():
    # --- Initialize page state ---
    if "current_page" not in st.session_state:
        st.session_state.current_page = "resumo"
    for _tk in ["vendas_tree_key", "compras_tree_key", "nasc_tree_key"]:
        if _tk not in st.session_state:
            st.session_state[_tk] = 0
    
    # Navigation definitions
    nav_items = [
        {"key": "resumo",    "icon": "dashboard",   "label": "Resumo Geral",    "desc": "Visão consolidada"},
        {"key": "peso",      "icon": "monitoring",   "label": "Evolução de Peso", "desc": "Performance zootécnica"},
        {"key": "ficha",     "icon": "inventory_2",  "label": "Ficha de Animais", "desc": "Giro de estoque"},
        {"key": "planejamento", "icon": "calculate", "label": "Planejamento",    "desc": "Simulação financeira"},
        {"key": "calendario",   "icon": "calendar_month", "label": "Calendário",  "desc": "Atividades e eventos"},
    ]
    
    # --- SIDEBAR — Premium Brand ---
    mago_path = os.path.join(script_dir, '..', 'assets', 'mago_placeholder.png')
    real_mago = os.path.join(script_dir, '..', 'assets', 'mago.png')
    
    # Use real_mago if exists, else placeholder
    mago_b64 = get_base64_of_bin_file(real_mago) or get_base64_of_bin_file(mago_path)
    
    if mago_b64:
        logo_html = f'<img src="data:image/png;base64,{mago_b64}" style="width:100%; height:100%; object-fit:contain; border-radius:12px;">'
    else:
        logo_html = '<span class="mat-icon" style="font-size:28px; color:white;">pets</span>'

    st.sidebar.markdown(f"""
        <div class="esopo-brand">
            <div class="esopo-logo-box" style="padding:0; overflow:hidden;">
                {logo_html}
            </div>
            <div class="esopo-brand-title">ESOPO</div>
            <div class="esopo-brand-subtitle">Converse com a sua Fazenda</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    
    # --- Custom Navigation with Material Icons ---
    st.sidebar.markdown('<div class="sidebar-section-label">Navegação</div>', unsafe_allow_html=True)
    
    for item in nav_items:
        is_active = st.session_state.current_page == item["key"]
        btn_label = f"✔  {item['label']}" if is_active else item["label"]
        
        if st.sidebar.button(btn_label, key=f"btn_{item['key']}", use_container_width=True):
            st.session_state.current_page = item["key"]
            st.rerun()
    
    # Inject JS to assign data-nav attributes for icon differentiation
    # Using components.html to bypass Streamlit's script sanitization
    components.html("""
        <script>
        function assignNavIcons() {
            const doc = window.parent.document;
            const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
            if (!sidebar) return;
            const buttons = sidebar.querySelectorAll('.stButton button');
            const mapping = {
                'Resumo Geral': 'resumo',
                'Evolu': 'peso',
                'Ficha': 'ficha',
                'Planejamento': 'planejamento',
                'Calend': 'calendario'
            };
            buttons.forEach(btn => {
                const text = btn.textContent || '';
                for (const [keyword, navKey] of Object.entries(mapping)) {
                    if (text.includes(keyword)) {
                        btn.setAttribute('data-nav', navKey);
                        break;
                    }
                }
            });
        }
        assignNavIcons();
        setTimeout(assignNavIcons, 300);
        setTimeout(assignNavIcons, 800);
        setTimeout(assignNavIcons, 2000);
        const observer = new MutationObserver(() => { assignNavIcons(); });
        const target = window.parent.document.querySelector('section[data-testid="stSidebar"]');
        if (target) observer.observe(target, { childList: true, subtree: true });
        </script>
    """, height=0)
    
    st.sidebar.markdown("---")
    
    pecuarius_path = os.path.join(script_dir, '..', 'assets', 'pecuarius.jpg')
    pecuarius_b64 = get_base64_of_bin_file(pecuarius_path)
    
    if pecuarius_b64:
        db_logo = f'<img src="data:image/jpeg;base64,{pecuarius_b64}" style="width: 140px; margin: 10px 0; border-radius: 8px;">'
    else:
        db_logo = '<div style="font-size: 1.1rem; font-weight: 800; color: #f8fafc; letter-spacing: 1px; margin: 8px 0;">PECUARIUS</div>'

    st.sidebar.markdown(f"""
        <div style="
            background: rgba(6, 78, 59, 0.12);
            border: 1px solid rgba(6, 78, 59, 0.25);
            border-radius: 12px;
            padding: 16px;
            margin: 8px 0;
            text-align: center;
        ">
            <div style="font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px;">
                Powered by
            </div>
            {db_logo}
            <div style="font-size: 0.70rem; color: #64748b; margin-top: 4px;">
                Gestão Global de Bovinos
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    # Map session state to page key
    page_map = {
        "resumo": "🏠 Resumo Geral",
        "peso": "📊 Evolução de Peso",
        "ficha": "📋 Ficha de Animais",
        "planejamento": "📐 Planejamento",
        "calendario": "📅 Calendário",
    }
    page = page_map[st.session_state.current_page]

    # --- PAGE HEADER ---
    page_icons = {
        "🏠 Resumo Geral": ("dashboard", "icon-green", "Visão consolidada do rebanho"),
        "📊 Evolução de Peso": ("monitoring", "icon-magenta", "Análise de performance zootécnica"),
        "📋 Ficha de Animais": ("inventory_2", "icon-amber", "Movimentação e giro de estoque"),
        "📐 Planejamento": ("calculate", "icon-green", "Simulação financeira de evolução do rebanho"),
        "📅 Calendário": ("calendar_month", "icon-green", "Calendário de atividades e eventos do rebanho"),
    }
    icon_name, icon_class, subtitle = page_icons.get(page, ("info", "icon-green", ""))
    clean_title = page.split(" ", 1)[1] if " " in page else page
    
    st.markdown(f"""
        <div class="section-header" style="margin-top: 8px;">
            <div class="icon-box {icon_class}">
                <span class="mat-icon">{icon_name}</span>
            </div>
            <div>
                <div class="section-title">{clean_title}</div>
                <div class="section-subtitle">{subtitle}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    
    try:
        conn = get_connection()
        
        # --- GLOBAL FARM SELECTOR ---
        query_farms = "SELECT cod_fazenda, descricao FROM Tab_fazenda"
        df_all_farms = pd.read_sql(query_farms, conn)
        
        with st.container():
            st.markdown("""
                <div class="section-header">
                    <div class="icon-box icon-green">
                        <span class="mat-icon">agriculture</span>
                    </div>
                    <div>
                        <div class="section-title">Seletor de Unidades</div>
                        <div class="section-subtitle">Filtro global por fazenda</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
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
            
            st.markdown("""
                <div class="section-header">
                    <div class="icon-box icon-green">
                        <span class="mat-icon">format_list_numbered</span>
                    </div>
                    <div>
                        <div class="section-title">Quantitativo (Cabeças)</div>
                        <div class="section-subtitle">Contagem do rebanho ativo</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Rebanho Ativo", f"{total_ativos:,}".replace(",", "."))
            m2.metric("Nascidos", f"{total_nascidos:,}".replace(",", "."))
            m3.metric("Comprados", f"{max(0, total_ativos - total_nascidos):,}".replace(",", "."))

            st.markdown("""
                <div class="section-header">
                    <div class="icon-box icon-magenta">
                        <span class="mat-icon">scale</span>
                    </div>
                    <div>
                        <div class="section-title">Capacidade (Unidade Animal — UA)</div>
                        <div class="section-subtitle">Carga animal por categoria de origem</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            ua1, ua2, ua3 = st.columns(3)
            ua1.metric("Total UA", format_br(total_ua))
            ua2.metric("Nascidos UA", format_br(nascidos_ua))
            ua3.metric("Comprados UA", format_br(max(0.0, total_ua - nascidos_ua)))

            st.divider()
            c_left, c_right = st.columns([1.2, 1])
            with c_left:
                st.markdown("<div class='section-title' style='margin-bottom:12px;'>Distribuição por Unidade</div>", unsafe_allow_html=True)
                df_pie = pd.read_sql(f"SELECT tf.descricao as fazenda, COUNT(c.cod_animal) as total FROM cad_fichario c JOIN Tab_fazenda tf ON c.cod_fazenda = tf.cod_fazenda WHERE {global_filter} GROUP BY tf.descricao", conn)
                if not df_pie.empty:
                    fig_pie = px.pie(
                        df_pie, 
                        values='total', 
                        names='fazenda', 
                        hole=0.5,
                        color_discrete_sequence=['#064e3b', '#be185d', '#64748b', '#d97706', '#059669', '#94a3b8']
                    )
                    fig_pie.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family="Outfit", size=14),
                        margin=dict(t=0, b=0, l=0, r=0)
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
            with c_right:
                st.markdown("""
                    <div class="section-header" style="padding-bottom: 8px; border-bottom: 1px solid rgba(190,24,93,0.12);">
                        <div class="icon-box icon-magenta">
                            <span class="mat-icon">analytics</span>
                        </div>
                        <div>
                            <div class="section-title">Detalhamento Técnico</div>
                            <div class="section-subtitle">Indicadores por categoria</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
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
            # --- Perspective selector (No icons as requested) ---
            perspective_map = {"Vendas": "Vendas", "Compras": "Compras", "Nascimentos": "Nascimentos", "Abates": "Abates"}
            sub_page = st.radio(
                "Selecione a perspectiva de análise:",
                list(perspective_map.keys()),
                horizontal=True
            )
            
            # Sub-filters for all perspectives
            f_col1, f_col2 = st.columns([1, 2])
            with f_col1:
                periodo_meses = st.slider("Período de Análise (Meses):", 0, 60, 12, key="peso_slider")
            
            # Color metric scale
            custom_scale = [
                [0.0, "#be185d"],
                [0.5, "#d97706"],
                [1.0, "#064e3b"]
            ]

            # =====================================================
            # VENDAS PERSPECTIVE
            # =====================================================
            if sub_page == "Vendas":
                st.markdown("""
                    <div class="section-header">
                        <div class="icon-box icon-magenta">
                            <span class="mat-icon">point_of_sale</span>
                        </div>
                        <div>
                            <div class="section-title">Performance de Animais Vendidos</div>
                            <div class="section-subtitle">Análise de margem e GMD por lote</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
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
                        FW AS (
                            SELECT cod_animal, peso, data, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data ASC) as rn
                            FROM cad_pesagem_corte
                        ),
                        LW AS (
                            SELECT cod_animal, peso, data, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn
                            FROM cad_pesagem_corte
                        ),
                        PesoMorto AS (
                            SELECT Cod_Animal, Data, (Peso_BDQ + Peso_BEQ) as peso_morto
                            FROM Cad_peso_morto
                        ),
                        PesagemVenda AS (
                            SELECT cod_animal, data, peso
                            FROM cad_pesagem_corte
                        )
                        SELECT cf.id_animal, cf.cod_animal, cf.origem, s.comp, s.dtv, 
                               ISNULL(lw.peso, s.pev_orig) as pv,
                               CASE WHEN cf.origem = 'N' THEN cf.dt_nascimento ELSE cf.dt_compra END as di,
                               DATEDIFF(day, CASE WHEN cf.origem = 'N' THEN cf.dt_nascimento ELSE cf.dt_compra END, s.dtv) as td,
                               CASE WHEN cf.origem = 'N' THEN 'NASCIMENTO: ' + CAST(FORMAT(cf.dt_nascimento, 'MM/yyyy') AS VARCHAR) ELSE e.grp END as og,
                               CASE WHEN cf.origem = 'N' THEN 40.0 ELSE COALESCE(NULLIF(e.pe, 0), fw.peso) END as pi,
                               e.dte as data_compra_raw, e.forn as fornecedor_raw,
                               pm.peso_morto,
                               pvenda.peso as peso_vivo_abate,
                               (lw.peso - fw.peso) / NULLIF(DATEDIFF(day, fw.data, lw.data), 0) as gmd_sql,
                               DATEDIFF(day, fw.data, lw.data) as interv_pesagens
                        FROM cad_fichario cf
                        JOIN Sale s ON cf.cod_animal = s.cod_animal
                        LEFT JOIN Entry e ON cf.cod_animal = e.cod_animal
                        LEFT JOIN FW fw ON cf.cod_animal = fw.cod_animal AND fw.rn = 1
                        LEFT JOIN LW lw ON cf.cod_animal = lw.cod_animal AND lw.rn = 1
                        LEFT JOIN PesoMorto pm ON cf.cod_animal = pm.Cod_Animal AND s.dtv = pm.Data
                        LEFT JOIN PesagemVenda pvenda ON cf.cod_animal = pvenda.cod_animal AND s.dtv = pvenda.data
                        WHERE cf.cod_fazenda IN ({farm_ids_str})
                    """
                    df = pd.read_sql(sql, conn)
                    if not df.empty:
                        df['gt'] = df['pv'] - df['pi']
                        df['gmd'] = df['gmd_sql'].astype(float)
                        df['rendimento'] = df.apply(
                            lambda r: (r['peso_morto'] / r['peso_vivo_abate'] * 100) 
                            if pd.notna(r['peso_morto']) and pd.notna(r['peso_vivo_abate']) and r['peso_vivo_abate'] > 0 
                            else None, axis=1
                        )
                        
                        # --- Color metric selector ---
                        metric_col1, metric_col2 = st.columns([3, 1])
                        with metric_col2:
                            color_metric = st.selectbox(
                                "Métrica de cor:",
                                ["GMD", "Peso Vivo", "Permanência"],
                                key="vendas_color_metric"
                            )
                        color_map = {"GMD": "gmd", "Peso Vivo": "pv", "Permanência": "td"}
                        color_field = color_map[color_metric]
                        
                        fig_sun = px.sunburst(
                            df, 
                            path=['comp', 'og'], 
                            values='pv', 
                            color=color_field, 
                            color_continuous_scale=custom_scale,
                            title=f"Hierarquia: Comprador > Origem (Cor = {color_metric})"
                        )
                        fig_sun.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(family="Outfit"),
                            title_font=dict(size=20, color="#064e3b")
                        )
                        st.plotly_chart(fig_sun, use_container_width=True)
                        
                        st.markdown("---")
                        st.markdown("""
                            <div class="section-header">
                                <div class="icon-box icon-amber">
                                    <span class="mat-icon">account_tree</span>
                                </div>
                                <div>
                                    <div class="section-title">Árvore de Decomposição</div>
                                    <div class="section-subtitle">Clique nos blocos para detalhar: Total → Cliente → Venda → Fornecedor → Compra</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        df_tree = df.copy()
                        df_tree['Venda'] = df_tree['dtv'].dt.strftime('%d-%m-%Y')
                        df_tree['Cliente'] = df_tree['comp']
                        df_tree['Compra'] = pd.to_datetime(df_tree['data_compra_raw']).dt.strftime('%d-%m-%Y').fillna('NASCIMENTO')
                        df_tree['Fornecedor'] = df_tree['fornecedor_raw'].fillna('ORIGEM INTERNA')
                        df_tree['Qtd'] = 1
                        
                        fig_tree = px.icicle(
                            df_tree,
                            path=[px.Constant("Total Vendas"), 'Cliente', 'Venda', 'Fornecedor', 'Compra'],
                            values='Qtd',
                            color=color_field,
                            color_continuous_scale=custom_scale,
                            title=f"Decomposição da Cadeia (Cor = {color_metric})"
                        )
                        fig_tree.update_traces(textinfo="label+value")
                        fig_tree.update_layout(
                            paper_bgcolor='rgba(0,0,0,0)',
                            font=dict(family="Outfit")
                        )
                        click_v = plotly_click_chart(fig_tree, key="vendas_icicle_click", height=550)
                        
                        # Parse click → grid filter
                        vf = parse_click_filter(click_v, ['Cliente', 'Venda', 'Fornecedor', 'Compra'])
                        
                        # --- Performance Grid ---
                        st.markdown("""
                            <div class="section-header">
                                <div class="icon-box icon-green">
                                    <span class="mat-icon">table_chart</span>
                                </div>
                                <div>
                                    <div class="section-title">Detalhamento da Performance</div>
                                    <div class="section-subtitle">Clique na árvore acima para filtrar o detalhamento</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Apply click filter to grid data
                        df_v_grid = df.copy()
                        if vf:
                            df_v_grid['_cliente'] = df_v_grid['comp']
                            df_v_grid['_venda'] = df_v_grid['dtv'].dt.strftime('%d-%m-%Y')
                            df_v_grid['_fornecedor'] = df_v_grid['fornecedor_raw'].fillna('ORIGEM INTERNA')
                            df_v_grid['_compra'] = pd.to_datetime(df_v_grid['data_compra_raw']).dt.strftime('%d-%m-%Y').fillna('NASCIMENTO')
                            _vmap = {'Cliente': '_cliente', 'Venda': '_venda', 'Fornecedor': '_fornecedor', 'Compra': '_compra'}
                            for _k, _val in vf.items():
                                _c = _vmap.get(_k)
                                if _c:
                                    df_v_grid = df_v_grid[df_v_grid[_c] == _val]
                            st.info(f"🔍 Filtro ativo: {' → '.join(vf.values())}  *(clique no nível raiz para limpar)*")
                        
                        nivel = st.radio(
                            "Nível de agrupamento:",
                            ["Por Fornecedor (Nível 4)", "Por Compra/Origem (Nível 5)"],
                            horizontal=True,
                            key="vendas_nivel_grid"
                        )
                        
                        if nivel == "Por Fornecedor (Nível 4)":
                            df_v_grid['fornecedor_agg'] = df_v_grid['fornecedor_raw'].fillna('ORIGEM INTERNA')
                            agg_cols = {'id_animal': 'count', 'pv': 'mean', 'td': 'mean', 'interv_pesagens': 'mean', 'gt': 'mean', 'gmd': 'mean', 'peso_morto': 'mean', 'rendimento': 'mean'}
                            res = df_v_grid.groupby(['comp', 'fornecedor_agg']).agg(agg_cols).reset_index()
                            res.columns = ['Comprador', 'Fornecedor', 'Qtd', 'Peso Venda (kg)', 'Permanência (Dias)', 'Intervalo Pesagens (Dias)', 'Ganho Total (kg)', 'GMD (kg/dia)', 'Peso Morto (kg)', 'Rendimento (%)']
                        else:
                            agg_cols = {'id_animal': 'count', 'pv': 'mean', 'td': 'mean', 'interv_pesagens': 'mean', 'gt': 'mean', 'gmd': 'mean', 'peso_morto': 'mean', 'rendimento': 'mean'}
                            res = df_v_grid.groupby(['comp', 'og']).agg(agg_cols).reset_index()
                            res.columns = ['Comprador', 'Origem (Lote/Mês)', 'Qtd', 'Peso Venda (kg)', 'Permanência (Dias)', 'Intervalo Pesagens (Dias)', 'Ganho Total (kg)', 'GMD (kg/dia)', 'Peso Morto (kg)', 'Rendimento (%)']
                        
                        fmt = {
                            'Peso Venda (kg)': '{:.1f}',
                            'Permanência (Dias)': '{:.0f}',
                            'Intervalo Pesagens (Dias)': '{:.0f}',
                            'Ganho Total (kg)': '{:.1f}',
                            'GMD (kg/dia)': '{:.3f}',
                            'Peso Morto (kg)': '{:.1f}',
                            'Rendimento (%)': '{:.1f}%'
                        }
                        res = append_total_row(res, fmt)
                        res = format_grid_df(res, fmt)
                        st.dataframe(res, use_container_width=True, hide_index=True)

            # =====================================================
            # COMPRAS PERSPECTIVE (Inverse decomposition)
            # =====================================================
            elif sub_page == "Compras":
                st.markdown("""
                    <div class="section-header">
                        <div class="icon-box icon-green">
                            <span class="mat-icon">shopping_cart</span>
                        </div>
                        <div>
                            <div class="section-title">Performance de Lotes Comprados</div>
                            <div class="section-subtitle">Decomposição inversa: Compra → Destino</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Active/Inactive filter
                with f_col1:
                    filtro_status = st.selectbox("Status dos Animais:", ["Apenas Ativos", "Apenas Inativos", "Todos"], key="compras_status")
                
                if filtro_status == "Apenas Ativos":
                    status_filter = "AND cf.cod_categoria NOT IN (SELECT cod_categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S')"
                elif filtro_status == "Apenas Inativos":
                    status_filter = "AND cf.cod_categoria IN (SELECT cod_categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S')"
                else:
                    status_filter = ""
                
                query_s = f"""SELECT DISTINCT tc.cod_criador, tc.descricao 
                    FROM cad_compra cc JOIN Tab_criador tc ON cc.cod_criador = tc.cod_criador 
                    JOIN cad_fichario cf ON cc.cod_animal = cf.cod_animal 
                    WHERE cf.cod_fazenda IN ({farm_ids_str}) AND cc.data >= DATEADD(month, -{periodo_meses}, GETDATE())"""
                df_s = pd.read_sql(query_s, conn)
                with f_col2:
                    sel_s = st.multiselect("Filtrar Fornecedores:", options=df_s['descricao'].tolist(), default=df_s['descricao'].tolist())
                
                if not sel_s:
                    st.warning("Selecione um fornecedor.")
                else:
                    s_ids = df_s[df_s['descricao'].isin(sel_s)]['cod_criador'].tolist()
                    s_str = ", ".join([f"'{str(i)}'" for i in s_ids])
                    
                    sql_c = f"""
                        WITH FW AS (
                            SELECT cod_animal, peso, data, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data ASC) as rn
                            FROM cad_pesagem_corte
                        ),
                        LW AS (
                            SELECT cod_animal, peso, data, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn
                            FROM cad_pesagem_corte
                        ),
                        SaleInfo AS (
                            SELECT cv.cod_animal, cv.data as dtv, cv.peso as peso_venda, tc.descricao as cliente
                            FROM cad_venda cv JOIN Tab_criador tc ON cv.cod_criador = tc.cod_criador
                        ),
                        PesoMorto AS (
                            SELECT Cod_Animal, Data, (Peso_BDQ + Peso_BEQ) as peso_morto
                            FROM Cad_peso_morto
                        ),
                        MorteInfo AS (
                            SELECT cod_animal, data as dt_morte
                            FROM cad_morte
                        )
                        SELECT cf.id_animal, cf.cod_animal, tc.descricao as fornecedor, 
                               cc.data as dt_compra, COALESCE(NULLIF(cc.peso, 0), fw.peso) as pi,
                               ISNULL(lw.peso, cc.peso) as pf, 
                               DATEDIFF(day, cc.data, ISNULL(si.dtv, ISNULL(mi.dt_morte, GETDATE()))) as td,
                               si.cliente as destino_cliente,
                               si.dtv as dt_venda,
                               mi.dt_morte,
                                CASE 
                                    WHEN si.dtv IS NOT NULL THEN 'VENDIDO: ' + CAST(FORMAT(si.dtv, 'dd/MM/yyyy') AS VARCHAR) + ' - ' + si.cliente
                                    WHEN mi.dt_morte IS NOT NULL THEN 'MORTO: ' + CAST(FORMAT(mi.dt_morte, 'dd/MM/yyyy') AS VARCHAR)
                                    ELSE 'ATIVO'
                                END as destino,
                                pm.peso_morto,
                                pvenda.peso as peso_vivo_abate,
                                (lw.peso - fw.peso) / NULLIF(DATEDIFF(day, fw.data, lw.data), 0) as gmd_sql,
                                DATEDIFF(day, fw.data, lw.data) as interv_pesagens
                         FROM cad_fichario cf
                         JOIN cad_compra cc ON cf.cod_animal = cc.cod_animal
                         JOIN Tab_criador tc ON cc.cod_criador = tc.cod_criador
                         LEFT JOIN FW fw ON cf.cod_animal = fw.cod_animal AND fw.rn = 1
                         LEFT JOIN LW lw ON cf.cod_animal = lw.cod_animal AND lw.rn = 1
                         LEFT JOIN SaleInfo si ON cf.cod_animal = si.cod_animal
                         LEFT JOIN MorteInfo mi ON cf.cod_animal = mi.cod_animal
                         LEFT JOIN PesoMorto pm ON cf.cod_animal = pm.Cod_Animal AND si.dtv = pm.Data
                         LEFT JOIN cad_pesagem_corte pvenda ON cf.cod_animal = pvenda.cod_animal AND si.dtv = pvenda.data
                         WHERE cf.cod_fazenda IN ({farm_ids_str}) AND cc.cod_criador IN ({s_str})
                         AND cc.data >= DATEADD(month, -{periodo_meses}, GETDATE())
                         {status_filter}
                    """
                    df_c = pd.read_sql(sql_c, conn)
                    if not df_c.empty:
                        df_c['gt'] = (df_c['pf'] - df_c['pi']).fillna(0)
                        df_c['gmd'] = df_c['gmd_sql'].astype(float)
                        df_c['rendimento'] = df_c.apply(
                            lambda r: (r['peso_morto'] / r['peso_vivo_abate'] * 100) 
                            if pd.notna(r['peso_morto']) and pd.notna(r['peso_vivo_abate']) and r['peso_vivo_abate'] > 0 
                            else None, axis=1
                        )
                        
                        # Color metric selector
                        metric_col1, metric_col2 = st.columns([3, 1])
                        with metric_col2:
                            color_metric_c = st.selectbox("Métrica de cor:", ["GMD", "Peso Vivo", "Permanência"], key="compras_color_metric")
                        color_map_c = {"GMD": "gmd", "Peso Vivo": "pf", "Permanência": "td"}
                        color_field_c = color_map_c[color_metric_c]
                        
                        # Sunburst: Fornecedor > Data Compra
                        df_c['compra_fmt'] = pd.to_datetime(df_c['dt_compra']).dt.strftime('%d/%m/%Y')
                        fig_sun_c = px.sunburst(
                            df_c, path=['fornecedor', 'compra_fmt'],
                            values='pf', color=color_field_c,
                            color_continuous_scale=custom_scale,
                            title=f"Hierarquia: Fornecedor > Compra (Cor = {color_metric_c})"
                        )
                        fig_sun_c.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Outfit"), title_font=dict(size=20, color="#064e3b"))
                        st.plotly_chart(fig_sun_c, use_container_width=True)
                        
                        st.markdown("---")
                        st.markdown("""
                            <div class="section-header">
                                <div class="icon-box icon-amber">
                                    <span class="mat-icon">account_tree</span>
                                </div>
                                <div>
                                    <div class="section-title">Árvore de Decomposição</div>
                                    <div class="section-subtitle">Compra → Fornecedor → Lote → Destino</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        df_tree_c = df_c.copy()
                        df_tree_c['Compra'] = pd.to_datetime(df_tree_c['dt_compra']).dt.strftime('%d-%m-%Y')
                        df_tree_c['Destino'] = df_tree_c['destino']
                        df_tree_c['Qtd'] = 1
                        
                        fig_tree_c = px.icicle(
                            df_tree_c,
                            path=[px.Constant("Total Compras"), 'fornecedor', 'Compra', 'Destino'],
                            values='Qtd', color=color_field_c,
                            color_continuous_scale=custom_scale,
                            title=f"Decomposição (Cor = {color_metric_c})"
                        )
                        fig_tree_c.update_traces(textinfo="label+value")
                        fig_tree_c.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Outfit"))
                        click_c = plotly_click_chart(fig_tree_c, key="compras_icicle_click", height=550)
                        
                        # Parse click → grid filter
                        cf = parse_click_filter(click_c, ['fornecedor', 'Compra', 'Destino'])
                        
                        # Grid
                        st.markdown("""
                            <div class="section-header">
                                <div class="icon-box icon-green">
                                    <span class="mat-icon">table_chart</span>
                                </div>
                                <div>
                                    <div class="section-title">Detalhamento da Performance</div>
                                    <div class="section-subtitle">Clique na árvore acima para filtrar o detalhamento</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        # Apply click filter
                        df_c_grid = df_c.copy()
                        if cf:
                            df_c_grid['_compra_dt'] = pd.to_datetime(df_c_grid['dt_compra']).dt.strftime('%d-%m-%Y')
                            _cmap = {'fornecedor': 'fornecedor', 'Compra': '_compra_dt', 'Destino': 'destino'}
                            for _k, _val in cf.items():
                                _c = _cmap.get(_k)
                                if _c:
                                    df_c_grid = df_c_grid[df_c_grid[_c] == _val]
                            st.info(f"🔍 Filtro ativo: {' → '.join(cf.values())}  *(clique no nível raiz para limpar)*")
                        
                        nivel_c = st.radio(
                            "Nível de agrupamento:",
                            ["Por Fornecedor", "Por Lote (Data Compra)"],
                            horizontal=True, key="compras_nivel_grid"
                        )
                        
                        agg_c = {'id_animal': 'count', 'pi': 'mean', 'pf': 'mean', 'td': 'mean', 'interv_pesagens': 'mean', 'gt': 'mean', 'gmd': 'mean', 'peso_morto': 'mean', 'rendimento': 'mean'}
                        if nivel_c == "Por Fornecedor":
                            res_c = df_c_grid.groupby('fornecedor').agg(agg_c).reset_index()
                            res_c.columns = ['Fornecedor', 'Qtd', 'Peso Compra (kg)', 'Peso Atual (kg)', 'Permanência (Dias)', 'Intervalo Pesagens (Dias)', 'Ganho Total (kg)', 'GMD (kg/dia)', 'Peso Morto (kg)', 'Rendimento (%)']
                        else:
                            df_c_grid['dt_compra_fmt'] = pd.to_datetime(df_c_grid['dt_compra']).dt.strftime('%d/%m/%Y')
                            res_c = df_c_grid.groupby(['fornecedor', 'dt_compra_fmt']).agg(agg_c).reset_index()
                            res_c.columns = ['Fornecedor', 'Data Compra', 'Qtd', 'Peso Compra (kg)', 'Peso Atual (kg)', 'Permanência (Dias)', 'Intervalo Pesagens (Dias)', 'Ganho Total (kg)', 'GMD (kg/dia)', 'Peso Morto (kg)', 'Rendimento (%)']
                        
                        fmt_c = {'Peso Compra (kg)': '{:.1f}', 'Peso Atual (kg)': '{:.1f}', 'Permanência (Dias)': '{:.0f}', 'Intervalo Pesagens (Dias)': '{:.0f}', 'Ganho Total (kg)': '{:.1f}', 'GMD (kg/dia)': '{:.3f}', 'Peso Morto (kg)': '{:.1f}', 'Rendimento (%)': '{:.1f}%'}
                        res_c = append_total_row(res_c, fmt_c)
                        res_c = format_grid_df(res_c, fmt_c)
                        st.dataframe(res_c, use_container_width=True, hide_index=True)
                    else:
                        st.info("Nenhum dado encontrado para os filtros selecionados.")

            # =====================================================
            # NASCIMENTOS PERSPECTIVE
            # =====================================================
            elif sub_page == "Nascimentos":
                st.markdown("""
                    <div class="section-header">
                        <div class="icon-box icon-green">
                            <span class="mat-icon">child_care</span>
                        </div>
                        <div>
                            <div class="section-title">Evolução de Animais Nascidos</div>
                            <div class="section-subtitle">Decomposição por mês, sexo e destino</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                # Filters: gender + status
                with f_col2:
                    gc1, gc2 = st.columns(2)
                    with gc1:
                        filtro_sexo = st.selectbox("Sexo:", ["Ambos", "Macho (M)", "Fêmea (F)"], key="nasc_sexo")
                    with gc2:
                        filtro_status_n = st.selectbox("Status:", ["Apenas Ativos", "Apenas Inativos", "Todos"], key="nasc_status")
                
                sexo_filter = ""
                if filtro_sexo == "Macho (M)":
                    sexo_filter = "AND cf.sexo = 'M'"
                elif filtro_sexo == "Fêmea (F)":
                    sexo_filter = "AND cf.sexo = 'F'"
                
                if filtro_status_n == "Apenas Ativos":
                    status_filter_n = "AND cf.cod_categoria NOT IN (SELECT cod_categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S')"
                elif filtro_status_n == "Apenas Inativos":
                    status_filter_n = "AND cf.cod_categoria IN (SELECT cod_categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S')"
                else:
                    status_filter_n = ""
                
                sql_n = f"""
                    WITH FW AS (
                        SELECT cod_animal, peso, data, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data ASC) as rn
                        FROM cad_pesagem_corte
                    ),
                    LW AS (
                        SELECT cod_animal, peso, data, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn
                        FROM cad_pesagem_corte
                    ),
                    SaleInfo AS (
                        SELECT cv.cod_animal, cv.data as dtv, cv.peso as peso_venda, tc.descricao as cliente
                        FROM cad_venda cv JOIN Tab_criador tc ON cv.cod_criador = tc.cod_criador
                    ),
                    MorteInfo AS (
                        SELECT cod_animal, data as dt_morte FROM cad_morte
                    ),
                    PesoMorto AS (
                        SELECT Cod_Animal, Data, (Peso_BDQ + Peso_BEQ) as peso_morto FROM Cad_peso_morto
                    )
                    SELECT cf.id_animal, cf.cod_animal, cf.dt_nascimento, cf.sexo,
                           ISNULL(lw.peso, 40.0) as pf,
                           DATEDIFF(day, cf.dt_nascimento, ISNULL(si.dtv, ISNULL(mi.dt_morte, GETDATE()))) as td,
                           si.cliente as destino_cliente, si.dtv as dt_venda,
                           mi.dt_morte,
                           CASE 
                               WHEN si.dtv IS NOT NULL THEN 'VENDIDO'
                               WHEN mi.dt_morte IS NOT NULL THEN 'MORTO'
                               ELSE 'ATIVO'
                           END as status_animal,
                           CASE 
                               WHEN si.dtv IS NOT NULL THEN 'VENDIDO: ' + ISNULL(si.cliente, '')
                               WHEN mi.dt_morte IS NOT NULL THEN 'MORTO: ' + CAST(FORMAT(mi.dt_morte, 'dd/MM/yyyy') AS VARCHAR)
                               ELSE 'ATIVO'
                           END as destino,
                           pm.peso_morto,
                           pvenda.peso as peso_vivo_abate,
                           (lw.peso - fw.peso) / NULLIF(DATEDIFF(day, fw.data, lw.data), 0) as gmd,
                           DATEDIFF(day, fw.data, lw.data) as interv_pesagens
                    FROM cad_fichario cf
                    LEFT JOIN FW fw ON cf.cod_animal = fw.cod_animal AND fw.rn = 1
                    LEFT JOIN LW lw ON cf.cod_animal = lw.cod_animal AND lw.rn = 1
                    LEFT JOIN SaleInfo si ON cf.cod_animal = si.cod_animal
                    LEFT JOIN MorteInfo mi ON cf.cod_animal = mi.cod_animal
                    LEFT JOIN PesoMorto pm ON cf.cod_animal = pm.Cod_Animal AND si.dtv = pm.Data
                    LEFT JOIN cad_pesagem_corte pvenda ON cf.cod_animal = pvenda.cod_animal AND si.dtv = pvenda.data
                    WHERE cf.cod_fazenda IN ({farm_ids_str}) AND cf.origem = 'N'
                    AND cf.dt_nascimento >= DATEADD(month, -{periodo_meses}, GETDATE())
                    {sexo_filter} {status_filter_n}
                """
                df_n = pd.read_sql(sql_n, conn)
                if not df_n.empty:
                    df_n['mes_nasc'] = df_n['dt_nascimento'].dt.strftime('%m/%Y')
                    df_n['gmd'] = df_n['gmd'].astype(float)
                    df_n['sexo_label'] = df_n['sexo'].map({'M': 'Macho', 'F': 'Fêmea'})
                    df_n['rendimento'] = df_n.apply(
                        lambda r: (r['peso_morto'] / r['peso_vivo_abate'] * 100) 
                        if pd.notna(r['peso_morto']) and pd.notna(r['peso_vivo_abate']) and r['peso_vivo_abate'] > 0 
                        else None, axis=1
                    )
                    
                    # Color metric
                    metric_col1, metric_col2 = st.columns([3, 1])
                    with metric_col2:
                        color_metric_n = st.selectbox("Métrica de cor:", ["GMD", "Peso Vivo", "Permanência"], key="nasc_color_metric")
                    color_map_n = {"GMD": "gmd", "Peso Vivo": "pf", "Permanência": "td"}
                    color_field_n = color_map_n[color_metric_n]
                    
                    # Sunburst
                    fig_sun_n = px.sunburst(
                        df_n, path=['mes_nasc', 'sexo_label', 'status_animal'],
                        values='pf', color=color_field_n,
                        color_continuous_scale=custom_scale,
                        title=f"Hierarquia: Mês > Sexo > Status (Cor = {color_metric_n})"
                    )
                    fig_sun_n.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Outfit"), title_font=dict(size=20, color="#064e3b"))
                    st.plotly_chart(fig_sun_n, use_container_width=True)
                    
                    st.markdown("---")
                    st.markdown("""
                        <div class="section-header">
                            <div class="icon-box icon-amber">
                                <span class="mat-icon">account_tree</span>
                            </div>
                            <div>
                                <div class="section-title">Árvore de Decomposição</div>
                                <div class="section-subtitle">Nascimento → Mês → Sexo → Destino</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    df_tree_n = df_n.copy()
                    df_tree_n['Mês'] = df_tree_n['dt_nascimento'].dt.strftime('%m-%Y')
                    df_tree_n['Sexo'] = df_tree_n['sexo_label']
                    df_tree_n['Destino'] = df_tree_n['destino'].str.replace('/', '-', regex=False)
                    df_tree_n['Qtd'] = 1
                    
                    fig_tree_n = px.icicle(
                        df_tree_n,
                        path=[px.Constant("Total Nascimentos"), 'Mês', 'Sexo', 'Destino'],
                        values='Qtd', color=color_field_n,
                        color_continuous_scale=custom_scale,
                        title=f"Decomposição (Cor = {color_metric_n})"
                    )
                    fig_tree_n.update_traces(textinfo="label+value")
                    fig_tree_n.update_layout(paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Outfit"))
                    click_n = plotly_click_chart(fig_tree_n, key="nasc_icicle_click", height=550)
                    
                    # Parse click → grid filter
                    nf = parse_click_filter(click_n, ['Mês', 'Sexo', 'Destino'])
                    
                    # Grid
                    st.markdown("""
                        <div class="section-header">
                            <div class="icon-box icon-green">
                                <span class="mat-icon">table_chart</span>
                            </div>
                            <div>
                                <div class="section-title">Detalhamento da Performance</div>
                                <div class="section-subtitle">Clique na árvore acima para filtrar o detalhamento</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Apply click filter
                    df_n_grid = df_n.copy()
                    if nf:
                        df_n_grid['_mes'] = df_n_grid['dt_nascimento'].dt.strftime('%m-%Y')
                        df_n_grid['_destino'] = df_n_grid['destino'].str.replace('/', '-', regex=False)
                        _nmap = {'Mês': '_mes', 'Sexo': 'sexo_label', 'Destino': '_destino'}
                        for _k, _val in nf.items():
                            _c = _nmap.get(_k)
                            if _c:
                                df_n_grid = df_n_grid[df_n_grid[_c] == _val]
                        st.info(f"🔍 Filtro ativo: {' → '.join(nf.values())}  *(clique no nível raiz para limpar)*")
                    
                    nivel_n = st.radio(
                        "Nível de agrupamento:",
                        ["Por Mês", "Por Mês e Sexo", "Por Mês, Sexo e Destino"],
                        horizontal=True, key="nasc_nivel_grid"
                    )
                    
                    agg_n = {'id_animal': 'count', 'pf': 'mean', 'td': 'mean', 'interv_pesagens': 'mean', 'gmd': 'mean', 'peso_morto': 'mean', 'rendimento': 'mean'}
                    if nivel_n == "Por Mês":
                        res_n = df_n_grid.groupby('mes_nasc').agg(agg_n).reset_index()
                        res_n.columns = ['Mês Nasc.', 'Qtd', 'Peso Atual (kg)', 'Permanência (Dias)', 'Intervalo Pesagens (Dias)', 'GMD (kg/dia)', 'Peso Morto (kg)', 'Rendimento (%)']
                    elif nivel_n == "Por Mês e Sexo":
                        res_n = df_n_grid.groupby(['mes_nasc', 'sexo_label']).agg(agg_n).reset_index()
                        res_n.columns = ['Mês Nasc.', 'Sexo', 'Qtd', 'Peso Atual (kg)', 'Permanência (Dias)', 'Intervalo Pesagens (Dias)', 'GMD (kg/dia)', 'Peso Morto (kg)', 'Rendimento (%)']
                    else:
                        res_n = df_n_grid.groupby(['mes_nasc', 'sexo_label', 'status_animal']).agg(agg_n).reset_index()
                        res_n.columns = ['Mês Nasc.', 'Sexo', 'Status', 'Qtd', 'Peso Atual (kg)', 'Permanência (Dias)', 'Intervalo Pesagens (Dias)', 'GMD (kg/dia)', 'Peso Morto (kg)', 'Rendimento (%)']
                    
                    fmt_n = {'Peso Atual (kg)': '{:.1f}', 'Permanência (Dias)': '{:.0f}', 'Intervalo Pesagens (Dias)': '{:.0f}', 'GMD (kg/dia)': '{:.3f}', 'Peso Morto (kg)': '{:.1f}', 'Rendimento (%)': '{:.1f}%'}
                    res_n = append_total_row(res_n, fmt_n)
                    res_n = format_grid_df(res_n, fmt_n)
                    st.dataframe(res_n, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum dado encontrado para os filtros selecionados.")

            # =====================================================
            # ABATES PERSPECTIVE (Slaughter Analysis)
            # =====================================================
            elif sub_page == "Abates":
                # Slaughters are defined by animals in CPM with Venda matching date/buyer/dt_inclusao
                sql_abates = f"""
                    WITH FW AS (
                        SELECT cod_animal, peso, data, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data ASC) as rn
                        FROM cad_pesagem_corte
                    ),
                    LW AS (
                        SELECT cod_animal, peso, data, ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn
                        FROM cad_pesagem_corte
                    )
                    SELECT 
                        m.Data as dt_abate,
                        cr.descricao as comprador,
                        tf.descricao as fazenda,
                        m.Cod_Animal as id_animal,
                        (m.Peso_BDQ + m.Peso_BEQ) as peso_morto,
                        (m.Peso_BDQ + m.Peso_BEQ) / NULLIF(pc.peso, 0) * 100 as rendimento,
                        m.DIP,
                        DATEDIFF(day, f.dt_nascimento, m.Data) as idade_dias,
                        DATEDIFF(day, ISNULL(c.data, f.dt_nascimento), m.Data) as permanencia,
                        (lw.peso - fw.peso) / NULLIF(DATEDIFF(day, fw.data, lw.data), 0) as gmd
                    FROM Cad_peso_morto m
                    JOIN cad_venda v ON m.Cod_Animal = v.cod_animal AND m.Data = v.Data
                    JOIN Tab_criador cr ON v.cod_criador = cr.cod_criador
                    JOIN cad_fichario f ON m.Cod_Animal = f.cod_animal
                    JOIN Tab_fazenda tf ON f.cod_fazenda = tf.cod_fazenda
                    LEFT JOIN cad_pesagem_corte pc ON m.Cod_Animal = pc.cod_animal AND m.Data = pc.data
                    LEFT JOIN cad_compra c ON m.Cod_Animal = c.cod_animal
                    LEFT JOIN FW fw ON f.Cod_Animal = fw.cod_animal AND fw.rn = 1
                    LEFT JOIN LW lw ON f.Cod_Animal = lw.cod_animal AND lw.rn = 1
                    WHERE f.cod_fazenda IN ({farm_ids_str})
                    AND m.Data >= DATEADD(month, -{periodo_meses}, GETDATE())
                """
                df_a = pd.read_sql(sql_abates, conn)
                
                if not df_a.empty:
                    # Filter Buyers (Moved to top column like Sales)
                    buyer_list = sorted(df_a['comprador'].unique())
                    with f_col2:
                        sel_buyers = st.multiselect("Filtrar Compradores:", buyer_list, default=buyer_list, key="abates_buyers")
                    
                    if sel_buyers:
                        df_a = df_a[df_a['comprador'].isin(sel_buyers)]
                    
                    if not df_a.empty:
                        # Identify Slaughter Batches (Unique combinations of Date and Farm)
                        df_a['batch_id'] = df_a['dt_abate'].astype(str) + "_" + df_a['fazenda'].astype(str)
                        batches = df_a.groupby('batch_id').agg({
                            'dt_abate': 'first',
                            'fazenda': 'first',
                            'comprador': 'first',
                            'id_animal': 'count',
                            'peso_morto': 'mean',
                            'rendimento': 'mean'
                        }).sort_values('dt_abate', ascending=False).reset_index()
                        
                        st.write("---")
                        st.write("### 🥩 Lotes de Abate (Selecione um Card)")
                        
                        # Display Cards in Columns
                        card_cols = st.columns(3)
                        selected_batch_id = st.session_state.get('selected_abate_batch', None)
                        
                        for idx, b in batches.iterrows():
                            col_idx = idx % 3
                            with card_cols[col_idx]:
                                # Style card based on selection
                                is_sel = b['batch_id'] == selected_batch_id
                                border_color = "#be185d" if is_sel else "#e2e8f0"
                                label = "✅ Selecionado" if is_sel else "Ver Detalhes"
                                
                                st.markdown(f"""
                                    <div style="border: 2px solid {border_color}; border-radius: 12px; padding: 15px; background: whitesmoke; margin-bottom: 15px;">
                                        <b style="font-size: 1.1em; color: #1e293b;">📅 {b['dt_abate'].strftime('%d/%m/%Y')}</b><br>
                                        <span style="color: #64748b; font-size: 0.9em;">🚜 {b['fazenda']}</span><br>
                                        <hr style="margin: 8px 0; border: 0.5px solid #cbd5e1;">
                                        <div style="display: flex; justify-content: space-between;">
                                            <span>🐂 <b>{b['id_animal']}</b> cab.</span>
                                            <span>⚖️ <b>{b['peso_morto']:.1f}</b> kg</span>
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                if st.button(label, key=f"btn_{b['batch_id']}"):
                                    st.session_state['selected_abate_batch'] = b['batch_id']
                                    st.rerun()

                        # Detailing Section
                        if selected_batch_id:
                            st.write("---")
                            df_sel = df_a[df_a['batch_id'] == selected_batch_id]
                            batch_info = batches[batches['batch_id'] == selected_batch_id].iloc[0]
                            
                            st.markdown(f"### 🔍 Detalhes do Abate: {batch_info['dt_abate'].strftime('%d/%m/%Y')} ({batch_info['comprador']})")
                            
                            det_col1, det_col2 = st.columns([1, 1])
                            
                            with det_col1:
                                st.write("**Resumo por DIP (Dentes):**")
                                # DIP Grid
                                agg_dip = {
                                    'id_animal': 'count',
                                    'peso_morto': 'mean',
                                    'rendimento': 'mean',
                                    'gmd': 'mean'
                                }
                                res_dip = df_sel.groupby('DIP').agg(agg_dip).reset_index()
                                res_dip.columns = ['DIP', 'Quantidade', 'Peso Mortos (kg)', 'Rendimento (%)', 'GMD (kg/dia)']
                                
                                # Totals
                                totals = pd.DataFrame([{
                                    'DIP': 'TOTAL',
                                    'Quantidade': res_dip['Quantidade'].sum(),
                                    'Peso Mortos (kg)': df_sel['peso_morto'].mean(),
                                    'Rendimento (%)': df_sel['rendimento'].mean(),
                                    'GMD (kg/dia)': df_sel['gmd'].mean()
                                }])
                                res_dip = pd.concat([res_dip, totals], ignore_index=True)
                                
                                fmt_dip = {
                                    'Peso Mortos (kg)': '{:.1f}',
                                    'Rendimento (%)': '{:.1f}%',
                                    'GMD (kg/dia)': '{:.3f}'
                                }
                                res_dip_disp = format_grid_df(res_dip, fmt_dip)
                                st.dataframe(res_dip_disp, use_container_width=True, hide_index=True)
                                
                                st.write("---")
                                st.write("**Distribuição do Peso Morto:**")
                                
                                mean_pm = df_sel['peso_morto'].mean()
                                min_pm = df_sel['peso_morto'].min()
                                max_pm = df_sel['peso_morto'].max()
                                std_pm = df_sel['peso_morto'].std()
                                if pd.isna(std_pm): std_pm = 0.0
                                cv_pm = (std_pm / mean_pm * 100) if mean_pm > 0 else 0
                                
                                hc1, hc2, hc3 = st.columns(3)
                                hc1.metric("Média", f"{mean_pm:.1f} kg")
                                hc2.metric("Mín", f"{min_pm:.1f} kg")
                                hc3.metric("Máx", f"{max_pm:.1f} kg")
                                
                                hc4, hc5, hc6 = st.columns(3)
                                hc4.metric("DP", f"{std_pm:.1f} kg")
                                hc5.metric("CV", f"{cv_pm:.1f}%")
                                
                                fig_hist = px.histogram(
                                    df_sel, x="peso_morto", nbins=10,
                                    labels={"peso_morto": "Peso Morto (kg)"},
                                    color_discrete_sequence=['#64748b']
                                )
                                fig_hist.add_vline(x=mean_pm, line_dash="dash", line_color="#be185d", annotation_text="Média")
                                fig_hist.update_layout(margin=dict(l=20, r=20, t=20, b=20), template="plotly_white", yaxis_title="Frequência")
                                st.plotly_chart(fig_hist, use_container_width=True)
                                
                            with det_col2:
                                st.write("**Gráfico de Regressão:**")
                                reg_var = st.selectbox(
                                    "Variável de análise (Eixo X):",
                                    ["DIP (Idade Dental)", "Idade (Dias)", "Tempo Permanência"],
                                    key="abate_reg_var"
                                )
                                var_map = {
                                    "DIP (Idade Dental)": "DIP",
                                    "Idade (Dias)": "idade_dias",
                                    "Tempo Permanência": "permanencia"
                                }
                                x_field = var_map[reg_var]
                                
                                fig_reg = px.scatter(
                                    df_sel, x=x_field, y="rendimento",
                                    trendline="ols",
                                    labels={x_field: reg_var, "rendimento": "Rendimento (%)"},
                                    title=f"Rendimento (%) vs {reg_var}",
                                    template="plotly_white",
                                    color_discrete_sequence=['#be185d']
                                )
                                fig_reg.update_layout(margin=dict(l=20, r=20, t=40, b=20))
                                st.plotly_chart(fig_reg, use_container_width=True)
                                
                                # Regression insights
                                with st.expander("📈 Insights Adicionais (Peso Morto & GMD)"):
                                    col_ins1, col_ins2 = st.columns(2)
                                    with col_ins1:
                                        fig_ins1 = px.scatter(df_sel, x=x_field, y="peso_morto", trendline="ols", title="Peso Morto vs Variável")
                                        st.plotly_chart(fig_ins1, use_container_width=True)
                                    with col_ins2:
                                        fig_ins2 = px.scatter(df_sel, x=x_field, y="gmd", trendline="ols", title="GMD vs Variável")
                                        st.plotly_chart(fig_ins2, use_container_width=True)
                        else:
                            st.info("👆 Selecione um card acima para ver o detalhamento do abate.")
                else:
                    st.info("Nenhum abate encontrado no período selecionado.")
            
        elif page == "📋 Ficha de Animais":
            st.markdown("""
                <div class="section-header">
                    <div class="icon-box icon-amber">
                        <span class="mat-icon">swap_vert</span>
                    </div>
                    <div>
                        <div class="section-title">Giro de Estoque Mensal</div>
                        <div class="section-subtitle">Movimentação de entradas e saídas</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
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
            fig.add_trace(go.Bar(
                x=df_p.index, 
                y=df_p['REBANHO'], 
                name='Cabeças', 
                marker_color='rgba(6, 78, 59, 0.4)', # Green transparent
                yaxis='y2'
            ))
            fig.add_trace(go.Bar(
                x=df_p.index, 
                y=df_p['UA'], 
                name='UA', 
                marker_color='rgba(190, 24, 93, 0.25)', # Magenta transparent
                yaxis='y2'
            ))
            
            if not segregate:
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['E_Q'], name='Entradas', line=dict(color='#064e3b', width=3)))
                fig.add_trace(go.Scatter(x=df_p.index, y=df_p['S_Q'], name='Saídas', line=dict(color='#be185d', width=3)))
            else:
                det = pivot_qtd.tail(periodo)
                fig.add_trace(go.Scatter(x=det.index, y=det['NASCIMENTO'], name='🐣 Nascimentos', line=dict(color='#10b981', width=2)))
                fig.add_trace(go.Scatter(x=det.index, y=det['COMPRA'], name='🤝 Compras', line=dict(color='#3b82f6', width=2)))
                fig.add_trace(go.Scatter(x=det.index, y=det['VENDA'], name='💰 Vendas', line=dict(color='#be185d', width=2)))
                fig.add_trace(go.Scatter(x=det.index, y=det['MORTE'], name='⚠️ Mortes', line=dict(color='#94a3b8', width=2), yaxis='y3'))

            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                barmode='group', 
                yaxis2=dict(overlaying='y', side='right', showgrid=False), 
                yaxis3=dict(overlaying='y', side='left', position=0.05, showgrid=False), 
                font=dict(family="Outfit"),
                margin=dict(l=80) if segregate else None
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # --- New: Resumo por Lote Grid ---
            st.markdown("---")
            st.markdown("""
                <div class="section-header">
                    <div class="icon-box icon-green">
                        <span class="mat-icon">grid_view</span>
                    </div>
                    <div>
                        <div class="section-title">Resumo por Lote</div>
                        <div class="section-subtitle">Peso projetado, GMD e datas de pesagem por lote ativo</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            sql_lote = f"""
                WITH UltPes AS (
                    SELECT cod_animal, peso, data, GPM,
                           ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn
                    FROM cad_pesagem_corte
                ),
                AntiPen AS (
                    SELECT cod_animal, data,
                           ROW_NUMBER() OVER (PARTITION BY cod_animal ORDER BY data DESC) as rn
                    FROM cad_pesagem_corte
                )
                SELECT 
                    tf.descricao as Fazenda, 
                    ISNULL(tl.descricao, '(Sem Lote)') as Lote,
                    COUNT(c.cod_animal) as Qtd,
                    AVG(up.peso + (DATEDIFF(day, up.data, GETDATE()) * ISNULL(up.GPM, 0))) as PesoProjetado,
                    AVG(up.GPM) as GMD_Medio,
                    MAX(up.data) as Ult_Pesagem,
                    DATEDIFF(day, MAX(up.data), GETDATE()) as Dias_Ult,
                    MAX(ap.data) as Ante_Pen
                FROM cad_fichario c
                JOIN Tab_fazenda tf ON c.cod_fazenda = tf.cod_fazenda
                LEFT JOIN Tab_lote tl ON c.cod_lote = tl.cod_lote
                LEFT JOIN UltPes up ON c.cod_animal = up.cod_animal AND up.rn = 1
                LEFT JOIN AntiPen ap ON c.cod_animal = ap.cod_animal AND ap.rn = 2
                WHERE c.cod_fazenda IN ({farm_ids_str})
                AND c.cod_categoria NOT IN (
                    SELECT cod_categoria FROM Tab_categoria WHERE morto = 'S' OR vendido = 'S'
                )
                GROUP BY tf.descricao, tl.descricao
                ORDER BY tf.descricao, Qtd DESC
            """
            df_lote = pd.read_sql(sql_lote, conn)
            
            if not df_lote.empty:
                # Format last weighing date with days in parentheses
                df_lote['Última Pesagem'] = df_lote.apply(
                    lambda r: f"{r['Ult_Pesagem'].strftime('%d/%m/%Y')} ({int(r['Dias_Ult'])}d)" 
                    if pd.notna(r['Ult_Pesagem']) else '—', axis=1
                )
                # Format second-to-last weighing date
                df_lote['Penúltima Pesagem'] = df_lote['Ante_Pen'].apply(
                    lambda x: x.strftime('%d/%m/%Y') if pd.notna(x) else '—'
                )
                
                # Build display dataframe
                display_lote = df_lote[['Fazenda', 'Lote', 'Qtd']].copy()
                display_lote['Peso Atual (kg)'] = df_lote['PesoProjetado'].round(1)
                display_lote['GMD (kg/dia)'] = df_lote['GMD_Medio'].round(3)
                display_lote['Última Pesagem'] = df_lote['Última Pesagem']
                display_lote['Penúltima Pesagem'] = df_lote['Penúltima Pesagem']
                display_lote = display_lote.rename(columns={'Qtd': 'Quantidade'})
                
                display_lote = format_grid_df(display_lote, {
                    'Peso Atual (kg)': '{:.1f}',
                    'GMD (kg/dia)': '{:.3f}'
                })
                
                st.dataframe(display_lote, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum dado de lote encontrado para as fazendas selecionadas.")

            # --- Gráfico de Sazonalidade do GPD ---
            st.markdown("---")
            st.markdown("""
                <div class="section-header">
                    <div class="icon-box icon-magenta">
                        <span class="mat-icon">insights</span>
                    </div>
                    <div>
                        <div class="section-title">Sazonalidade do GPD</div>
                        <div class="section-subtitle">Variação do ganho de peso diário ao longo dos meses do ano</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            try:
                import numpy as np
                # Buscar pesagens sequenciais por animal, filtradas pelas fazendas selecionadas
                sql_gpd_sazonal = f"""
                    SELECT 
                        pc.cod_animal,
                        pc.data,
                        pc.peso,
                        pc.GPD,
                        LAG(pc.data) OVER (PARTITION BY pc.cod_animal ORDER BY pc.data) as data_anterior,
                        LAG(pc.peso) OVER (PARTITION BY pc.cod_animal ORDER BY pc.data) as peso_anterior
                    FROM cad_pesagem_corte pc
                    JOIN cad_fichario c ON pc.cod_animal = c.cod_animal
                    WHERE c.cod_fazenda IN ({farm_ids_str})
                      AND pc.data >= DATEADD(month, -{periodo}, GETDATE())
                    ORDER BY pc.cod_animal, pc.data
                """
                df_pesagens = pd.read_sql(sql_gpd_sazonal, conn)
                
                if not df_pesagens.empty:
                    # Filtrar apenas linhas com pesagem anterior (pares sequenciais)
                    df_pares = df_pesagens.dropna(subset=['data_anterior', 'peso_anterior']).copy()
                    
                    if not df_pares.empty:
                        # Calcular GPD real entre pesagens sequenciais
                        df_pares['dias_intervalo'] = (df_pares['data'] - df_pares['data_anterior']).dt.days
                        df_pares['gpd_calc'] = (df_pares['peso'] - df_pares['peso_anterior']) / df_pares['dias_intervalo'].replace(0, np.nan)
                        df_pares = df_pares.dropna(subset=['gpd_calc'])
                        df_pares = df_pares[df_pares['dias_intervalo'] > 0]  # Apenas intervalos válidos
                        
                        # Distribuir o GPD pelos meses cobertos entre as duas pesagens
                        registros_mensais = []
                        for _, row in df_pares.iterrows():
                            dt_ini = row['data_anterior']
                            dt_fim = row['data']
                            gpd_val = row['gpd_calc']
                            
                            # Gerar cada mês coberto pelo intervalo
                            current = dt_ini.replace(day=1)
                            end_month = dt_fim.replace(day=1)
                            while current <= end_month:
                                registros_mensais.append({
                                    'mes_numero': current.month,
                                    'gpd': gpd_val
                                })
                                # Avançar para o próximo mês
                                if current.month == 12:
                                    current = current.replace(year=current.year + 1, month=1)
                                else:
                                    current = current.replace(month=current.month + 1)
                        
                        if registros_mensais:
                            df_mensal = pd.DataFrame(registros_mensais)
                            
                            # Calcular estatísticas por mês
                            stats = df_mensal.groupby('mes_numero')['gpd'].agg(
                                media='mean',
                                mediana='median',
                                desvio='std',
                                contagem='count'
                            ).reset_index()
                            
                            # Nomes dos meses em PT-BR
                            meses_nomes = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun',
                                           7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}
                            stats['Mês'] = stats['mes_numero'].map(meses_nomes)
                            stats = stats.sort_values('mes_numero')
                            
                            # Grid com estatísticas e Gráfico lado a lado
                            col_stats, col_gpd_chart = st.columns([1, 2])
                            
                            with col_stats:
                                st.markdown("""
                                    <div class="section-header" style="padding-bottom: 6px; border-bottom: 1px solid rgba(190,24,93,0.12);">
                                        <div class="icon-box icon-green">
                                            <span class="mat-icon">table_chart</span>
                                        </div>
                                        <div>
                                            <div class="section-title" style="font-size: 0.95rem;">Estatísticas Mensais</div>
                                            <div class="section-subtitle">GPD (kg/dia) por mês do ano</div>
                                        </div>
                                    </div>
                                """, unsafe_allow_html=True)
                                
                                display_stats = stats[['Mês', 'contagem', 'media', 'mediana', 'desvio']].copy()
                                display_stats.columns = ['Mês', 'Qtd GPDs', 'Média', 'Mediana', 'Desvio Padrão']
                                st.dataframe(
                                    display_stats.style.format({
                                        'Média': '{:.3f}',
                                        'Mediana': '{:.3f}',
                                        'Desvio Padrão': '{:.3f}'
                                    }),
                                    use_container_width=True,
                                    hide_index=True,
                                    height=460
                                )
                            
                            with col_gpd_chart:
                                import altair as alt
                                
                                # Preparar dados para curvas de média e mediana + faixa de desvio padrão
                                stats['limite_sup'] = stats['media'] + stats['desvio']
                                stats['limite_inf'] = (stats['media'] - stats['desvio']).clip(lower=0)
                                
                                # Faixa do desvio padrão (área sombreada)
                                area = alt.Chart(stats).mark_area(
                                    opacity=0.15, color='#059669'
                                ).encode(
                                    x=alt.X('Mês:O', sort=list(meses_nomes.values()), title='', axis=alt.Axis(labelAngle=0)),
                                    y=alt.Y('limite_inf:Q', title='GPD (kg/dia)'),
                                    y2='limite_sup:Q'
                                )
                                
                                # Linha da Média
                                line_media = alt.Chart(stats).mark_line(
                                    color='#059669', strokeWidth=3
                                ).encode(
                                    x=alt.X('Mês:O', sort=list(meses_nomes.values())),
                                    y=alt.Y('media:Q'),
                                    tooltip=[
                                        alt.Tooltip('Mês:O'),
                                        alt.Tooltip('media:Q', format='.3f', title='Média'),
                                        alt.Tooltip('contagem:Q', title='Qtd GPDs')
                                    ]
                                )
                                
                                points_media = alt.Chart(stats).mark_circle(
                                    color='#059669', size=60
                                ).encode(
                                    x=alt.X('Mês:O', sort=list(meses_nomes.values())),
                                    y='media:Q'
                                )
                                
                                # Linha da Mediana
                                line_mediana = alt.Chart(stats).mark_line(
                                    color='#be185d', strokeWidth=2, strokeDash=[6, 3]
                                ).encode(
                                    x=alt.X('Mês:O', sort=list(meses_nomes.values())),
                                    y=alt.Y('mediana:Q'),
                                    tooltip=[
                                        alt.Tooltip('Mês:O'),
                                        alt.Tooltip('mediana:Q', format='.3f', title='Mediana')
                                    ]
                                )
                                
                                points_mediana = alt.Chart(stats).mark_circle(
                                    color='#be185d', size=40
                                ).encode(
                                    x=alt.X('Mês:O', sort=list(meses_nomes.values())),
                                    y='mediana:Q'
                                )
                                
                                # Barras de contagem (eixo secundário simulado com opacidade leve)
                                bars_qtd = alt.Chart(stats).mark_bar(
                                    color='#94a3b8', opacity=0.2
                                ).encode(
                                    x=alt.X('Mês:O', sort=list(meses_nomes.values())),
                                    y=alt.Y('contagem:Q', title=''),
                                    tooltip=[
                                        alt.Tooltip('Mês:O'),
                                        alt.Tooltip('contagem:Q', title='Qtd GPDs')
                                    ]
                                )
                                
                                # Compor o gráfico final
                                gpd_chart = alt.layer(
                                    bars_qtd, area, line_media, points_media, line_mediana, points_mediana
                                ).resolve_scale(
                                    y='independent'
                                ).properties(
                                    height=420
                                ).configure_view(
                                    strokeWidth=0
                                ).configure_axis(
                                    labelFont='Outfit', titleFont='Outfit',
                                    gridOpacity=0.15
                                )
                                
                                st.altair_chart(gpd_chart, use_container_width=True)
                                
                                # Legenda manual via HTML
                                st.markdown('''
                                    <div style="display:flex; gap:20px; justify-content:center; font-size:0.8rem; color:#475569; margin-top:-10px;">
                                        <div><span style="display:inline-block; width:20px; height:3px; background:#059669; vertical-align:middle; margin-right:4px;"></span> Média</div>
                                        <div><span style="display:inline-block; width:20px; height:3px; background:#be185d; border-top:2px dashed #be185d; vertical-align:middle; margin-right:4px;"></span> Mediana</div>
                                        <div><span style="display:inline-block; width:14px; height:14px; background:rgba(5,150,105,0.15); vertical-align:middle; margin-right:4px; border-radius:2px;"></span> Faixa DP</div>
                                        <div><span style="display:inline-block; width:14px; height:14px; background:rgba(148,163,184,0.2); vertical-align:middle; margin-right:4px; border-radius:2px;"></span> Qtd GPDs</div>
                                    </div>
                                ''', unsafe_allow_html=True)
                        else:
                            st.info("Não há dados suficientes de pesagens sequenciais para gerar o gráfico de sazonalidade.")
                    else:
                        st.info("Não há pares de pesagens sequenciais no período selecionado.")
                else:
                    st.info("Nenhuma pesagem encontrada no período selecionado para as fazendas.")
            except Exception as e:
                st.error(f"❌ Erro ao calcular sazonalidade do GPD: {e}")
        # =====================================================
        # PLANEJAMENTO PAGE
        # =====================================================
        elif page == "📐 Planejamento":
            pass  # Handled separately below

        # =====================================================
        # CALENDÁRIO PAGE
        # =====================================================
        elif page == "📅 Calendário":
            import calendar
            from datetime import datetime, timedelta

            st.markdown("---")

            # --- Month/Year selector ---
            cal_col1, cal_col2, cal_col3 = st.columns([1, 1, 2])
            today = datetime.now()
            with cal_col1:
                cal_month = st.selectbox(
                    "Mês:",
                    list(range(1, 13)),
                    index=today.month - 1,
                    format_func=lambda m: ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'][m-1],
                    key="cal_month"
                )
            with cal_col2:
                cal_year = st.selectbox(
                    "Ano:",
                    list(range(today.year - 5, today.year + 2)),
                    index=5,
                    key="cal_year"
                )

            first_day = datetime(cal_year, cal_month, 1)
            if cal_month == 12:
                last_day = datetime(cal_year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = datetime(cal_year, cal_month + 1, 1) - timedelta(days=1)

            date_start = first_day.strftime('%Y-%m-%d')
            date_end = last_day.strftime('%Y-%m-%d')

            # --- Query all activities for the month ---
            sql_activities = f"""
                -- Pesagens
                SELECT cp.data as data_evento, 'Pesagem' as tipo, 
                       tf.descricao as fazenda, COUNT(*) as qtd,
                       CAST(AVG(cp.peso) AS DECIMAL(10,1)) as valor_medio
                FROM cad_pesagem_corte cp
                JOIN cad_fichario c ON cp.cod_animal = c.cod_animal
                JOIN Tab_fazenda tf ON c.cod_fazenda = tf.cod_fazenda
                WHERE c.cod_fazenda IN ({farm_ids_str})
                AND cp.data BETWEEN '{date_start}' AND '{date_end}'
                GROUP BY cp.data, tf.descricao

                UNION ALL

                -- Compras
                SELECT cc.data as data_evento, 'Compra' as tipo,
                       tf.descricao as fazenda, COUNT(*) as qtd,
                       CAST(AVG(cc.peso) AS DECIMAL(10,1)) as valor_medio
                FROM cad_compra cc
                JOIN cad_fichario c ON cc.cod_animal = c.cod_animal
                JOIN Tab_fazenda tf ON c.cod_fazenda = tf.cod_fazenda
                WHERE c.cod_fazenda IN ({farm_ids_str})
                AND cc.data BETWEEN '{date_start}' AND '{date_end}'
                GROUP BY cc.data, tf.descricao

                UNION ALL

                -- Vendas
                SELECT cv.data as data_evento, 'Venda' as tipo,
                       tf.descricao as fazenda, COUNT(*) as qtd,
                       CAST(AVG(ISNULL(pc.peso, 0)) AS DECIMAL(10,1)) as valor_medio
                FROM cad_venda cv
                JOIN cad_fichario c ON cv.cod_animal = c.cod_animal
                JOIN Tab_fazenda tf ON c.cod_fazenda = tf.cod_fazenda
                LEFT JOIN cad_pesagem_corte pc ON cv.cod_animal = pc.cod_animal AND cv.data = pc.data
                WHERE c.cod_fazenda IN ({farm_ids_str})
                AND cv.data BETWEEN '{date_start}' AND '{date_end}'
                GROUP BY cv.data, tf.descricao

                UNION ALL

                -- Mortes
                SELECT cm.data as data_evento, 'Morte' as tipo,
                       tf.descricao as fazenda, COUNT(*) as qtd,
                       NULL as valor_medio
                FROM cad_morte cm
                JOIN cad_fichario c ON cm.cod_animal = c.cod_animal
                JOIN Tab_fazenda tf ON c.cod_fazenda = tf.cod_fazenda
                WHERE c.cod_fazenda IN ({farm_ids_str})
                AND cm.data BETWEEN '{date_start}' AND '{date_end}'
                GROUP BY cm.data, tf.descricao

                UNION ALL

                -- Nascimentos
                SELECT c.dt_nascimento as data_evento, 'Nascimento' as tipo,
                       tf.descricao as fazenda, COUNT(*) as qtd,
                       NULL as valor_medio
                FROM cad_fichario c
                JOIN Tab_fazenda tf ON c.cod_fazenda = tf.cod_fazenda
                WHERE c.cod_fazenda IN ({farm_ids_str})
                AND c.dt_nascimento BETWEEN '{date_start}' AND '{date_end}'
                AND c.origem = 'N'
                GROUP BY c.dt_nascimento, tf.descricao

                UNION ALL

                -- Movimentações
                SELECT cm.data as data_evento, 
                       'Mov. ' + cm.tipo as tipo,
                       tf.descricao as fazenda, COUNT(*) as qtd,
                       NULL as valor_medio
                FROM cad_movimento cm
                JOIN cad_fichario c ON cm.cod_animal = c.cod_animal
                JOIN Tab_fazenda tf ON cm.cod_fazenda = tf.cod_fazenda
                WHERE cm.cod_fazenda IN ({farm_ids_str})
                AND cm.data BETWEEN '{date_start}' AND '{date_end}'
                GROUP BY cm.data, cm.tipo, tf.descricao

                ORDER BY data_evento
            """
            df_cal = pd.read_sql(sql_activities, conn)

            # --- Activity type colors ---
            activity_colors = {
                'Pesagem': '#059669',
                'Compra': '#3b82f6',
                'Venda': '#be185d',
                'Morte': '#64748b',
                'Nascimento': '#d97706',
            }
            # Movimentações get a teal color
            mov_color = '#0891b2'

            def get_color(tipo):
                if tipo.startswith('Mov.'):
                    return mov_color
                return activity_colors.get(tipo, '#94a3b8')

            def get_icon(tipo):
                icons = {
                    'Pesagem': '⚖️',
                    'Compra': '🤝',
                    'Venda': '💰',
                    'Morte': '⚠️',
                    'Nascimento': '🐣',
                }
                if tipo.startswith('Mov.'):
                    return '🔄'
                return icons.get(tipo, '📌')

            # --- KPI Summary Cards ---
            month_name = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'][cal_month - 1]

            if not df_cal.empty:
                total_events = int(df_cal['qtd'].sum())
                unique_days = df_cal['data_evento'].nunique()
                activity_types = df_cal['tipo'].nunique()
                farms_active = df_cal['fazenda'].nunique()
            else:
                total_events = 0
                unique_days = 0
                activity_types = 0
                farms_active = 0

            st.markdown("""
                <div class="section-header">
                    <div class="icon-box icon-green">
                        <span class="mat-icon">insights</span>
                    </div>
                    <div>
                        <div class="section-title">Resumo do Mês</div>
                        <div class="section-subtitle">Indicadores de atividade para """ + month_name + f""" {cal_year}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            kc1, kc2, kc3, kc4 = st.columns(4)
            kc1.metric("📋 Total de Eventos", f"{total_events}")
            kc2.metric("📅 Dias com Atividade", f"{unique_days}")
            kc3.metric("🏷️ Tipos de Atividade", f"{activity_types}")
            kc4.metric("🚜 Fazendas Ativas", f"{farms_active}")

            st.markdown("---")

            # --- CALENDAR GRID ---
            st.markdown("""
                <div class="section-header">
                    <div class="icon-box icon-magenta">
                        <span class="mat-icon">calendar_month</span>
                    </div>
                    <div>
                        <div class="section-title">Calendário de Atividades</div>
                        <div class="section-subtitle">Visualização mensal — clique em um dia para detalhes</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Build calendar data: group activities by day
            cal_by_day = {}
            if not df_cal.empty:
                for _, row in df_cal.iterrows():
                    day = row['data_evento'].day if hasattr(row['data_evento'], 'day') else pd.to_datetime(row['data_evento']).day
                    if day not in cal_by_day:
                        cal_by_day[day] = []
                    cal_by_day[day].append(row)

            # Build HTML calendar
            cal_obj = calendar.Calendar(firstweekday=6)  # Domingo = primeiro dia
            weeks = cal_obj.monthdayscalendar(cal_year, cal_month)

            weekday_names = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

            cal_html = '<div style="overflow-x: auto;">'
            cal_html += '<table style="width:100%; border-collapse: separate; border-spacing: 4px; table-layout: fixed;">'

            # Header
            cal_html += '<thead><tr>'
            for wd in weekday_names:
                cal_html += f'<th style="text-align:center; padding:8px; font-size:0.8rem; color:#64748b; font-weight:600; letter-spacing:0.5px;">{wd}</th>'
            cal_html += '</tr></thead>'

            # Body
            cal_html += '<tbody>'
            for week in weeks:
                cal_html += '<tr>'
                for day in week:
                    if day == 0:
                        cal_html += '<td style="padding:4px;"></td>'
                    else:
                        activities = cal_by_day.get(day, [])
                        is_today = (day == today.day and cal_month == today.month and cal_year == today.year)
                        has_events = len(activities) > 0

                        # Cell styling
                        bg = 'rgba(255,255,255,0.85)'
                        border = '1px solid #e2e8f0'
                        if is_today:
                            border = '2px solid #064e3b'
                            bg = 'rgba(6, 78, 59, 0.05)'
                        if has_events:
                            bg = 'rgba(6, 78, 59, 0.04)'

                        cal_html += f'<td style="vertical-align:top; padding:6px 4px; min-height:80px; height:80px; background:{bg}; border:{border}; border-radius:8px;">'

                        # Day number
                        day_color = '#064e3b' if is_today else '#1e293b'
                        day_weight = '700' if is_today else '500'
                        cal_html += f'<div style="font-size:0.85rem; font-weight:{day_weight}; color:{day_color}; margin-bottom:3px;">{day}</div>'

                        # Activity pills
                        if has_events:
                            # Group by type and sum
                            type_totals = {}
                            for act in activities:
                                t = act['tipo']
                                q = int(act['qtd'])
                                type_totals[t] = type_totals.get(t, 0) + q

                            for tipo, qtd in type_totals.items():
                                color = get_color(tipo)
                                icon = get_icon(tipo)
                                short_label = tipo.replace('Mov. ', '').replace('Nascimento', 'Nasc.')[:8]
                                cal_html += f'<div style="font-size:0.6rem; background:{color}15; color:{color}; border-left:2px solid {color}; padding:1px 4px; margin-bottom:2px; border-radius:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{icon} {qtd} {short_label}</div>'

                        cal_html += '</td>'
                cal_html += '</tr>'
            cal_html += '</tbody></table></div>'

            st.markdown(cal_html, unsafe_allow_html=True)

            # --- Legend ---
            legend_items = [
                ('⚖️ Pesagem', '#059669'),
                ('🤝 Compra', '#3b82f6'),
                ('💰 Venda', '#be185d'),
                ('⚠️ Morte', '#64748b'),
                ('🐣 Nascimento', '#d97706'),
                ('🔄 Movimentação', '#0891b2'),
            ]
            legend_html = '<div style="display:flex; gap:16px; flex-wrap:wrap; margin:12px 0 20px 0;">'
            for label, color in legend_items:
                legend_html += f'<div style="display:flex; align-items:center; gap:4px; font-size:0.78rem; color:#475569;"><div style="width:12px; height:12px; border-radius:3px; background:{color};"></div>{label}</div>'
            legend_html += '</div>'
            st.markdown(legend_html, unsafe_allow_html=True)

            # --- Day Detail Selector ---
            st.markdown("---")
            st.markdown("""
                <div class="section-header">
                    <div class="icon-box icon-amber">
                        <span class="mat-icon">event_note</span>
                    </div>
                    <div>
                        <div class="section-title">Detalhes do Dia</div>
                        <div class="section-subtitle">Selecione um dia para ver as atividades detalhadas</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            days_with_events = sorted(cal_by_day.keys()) if cal_by_day else []
            if days_with_events:
                selected_day = st.selectbox(
                    "Dia:",
                    days_with_events,
                    format_func=lambda d: f"{d:02d}/{cal_month:02d}/{cal_year} — {sum(int(a['qtd']) for a in cal_by_day[d])} evento(s)",
                    key="cal_selected_day"
                )

                if selected_day:
                    day_activities = cal_by_day[selected_day]
                    detail_rows = []
                    for act in day_activities:
                        detail_rows.append({
                            'Tipo': f"{get_icon(act['tipo'])} {act['tipo']}",
                            'Fazenda': act['fazenda'],
                            'Quantidade': int(act['qtd']),
                            'Valor Médio (kg)': f"{act['valor_medio']:.1f}" if pd.notna(act['valor_medio']) and act['valor_medio'] else '—'
                        })

                    df_detail = pd.DataFrame(detail_rows)
                    st.dataframe(df_detail, use_container_width=True, hide_index=True)

                    # Summary cards for the selected day
                    total_day = sum(int(a['qtd']) for a in day_activities)
                    farms_day = len(set(a['fazenda'] for a in day_activities))
                    types_day = len(set(a['tipo'] for a in day_activities))

                    dc1, dc2, dc3 = st.columns(3)
                    dc1.metric("Total Eventos no Dia", f"{total_day}")
                    dc2.metric("Fazendas Envolvidas", f"{farms_day}")
                    dc3.metric("Tipos de Atividade", f"{types_day}")
            else:
                st.info(f"📅 Nenhuma atividade registrada em {month_name} de {cal_year} para as fazendas selecionadas.")

            # --- Monthly Summary by Activity Type ---
            st.markdown("---")
            st.markdown("""
                <div class="section-header">
                    <div class="icon-box icon-green">
                        <span class="mat-icon">bar_chart</span>
                    </div>
                    <div>
                        <div class="section-title">Distribuição Mensal por Tipo</div>
                        <div class="section-subtitle">Quantidade de eventos agrupados por tipo de atividade</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if not df_cal.empty:
                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    # Bar chart by activity type
                    df_tipo_sum = df_cal.groupby('tipo')['qtd'].sum().reset_index()
                    df_tipo_sum.columns = ['Tipo', 'Quantidade']
                    df_tipo_sum = df_tipo_sum.sort_values('Quantidade', ascending=True)

                    colors_bar = [get_color(t) for t in df_tipo_sum['Tipo']]
                    fig_bar = go.Figure(go.Bar(
                        x=df_tipo_sum['Quantidade'],
                        y=df_tipo_sum['Tipo'],
                        orientation='h',
                        marker_color=colors_bar,
                        text=df_tipo_sum['Quantidade'],
                        textposition='outside'
                    ))
                    fig_bar.update_layout(
                        title='Eventos por Tipo de Atividade',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='Outfit', size=13),
                        margin=dict(l=20, r=40, t=40, b=20),
                        xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=False),
                        height=350
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

                with chart_col2:
                    # Timeline: events per day of month
                    df_timeline = df_cal.copy()
                    df_timeline['dia'] = pd.to_datetime(df_timeline['data_evento']).dt.day
                    df_day_tipo = df_timeline.groupby(['dia', 'tipo'])['qtd'].sum().reset_index()

                    fig_timeline = go.Figure()
                    for tipo in df_day_tipo['tipo'].unique():
                        df_t = df_day_tipo[df_day_tipo['tipo'] == tipo]
                        fig_timeline.add_trace(go.Bar(
                            x=df_t['dia'],
                            y=df_t['qtd'],
                            name=tipo,
                            marker_color=get_color(tipo)
                        ))

                    fig_timeline.update_layout(
                        title='Eventos por Dia do Mês',
                        barmode='stack',
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='Outfit', size=13),
                        margin=dict(l=20, r=20, t=40, b=20),
                        xaxis=dict(title='Dia', dtick=1),
                        yaxis=dict(title='Quantidade'),
                        legend=dict(orientation='h', y=1.15),
                        height=350
                    )
                    st.plotly_chart(fig_timeline, use_container_width=True)

                # --- Grid view: all events ---
                st.markdown("---")
                st.markdown("""
                    <div class="section-header">
                        <div class="icon-box icon-green">
                            <span class="mat-icon">table_chart</span>
                        </div>
                        <div>
                            <div class="section-title">Lista Completa de Atividades</div>
                            <div class="section-subtitle">Todas as atividades do mês ordenadas por data</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                df_grid = df_cal.copy()
                df_grid['Data'] = pd.to_datetime(df_grid['data_evento']).dt.strftime('%d/%m/%Y')
                df_grid = df_grid.rename(columns={
                    'tipo': 'Tipo',
                    'fazenda': 'Fazenda',
                    'qtd': 'Quantidade',
                    'valor_medio': 'Peso Médio (kg)'
                })
                df_grid['Tipo'] = df_grid['Tipo'].apply(lambda t: f"{get_icon(t)} {t}")
                df_grid['Peso Médio (kg)'] = df_grid['Peso Médio (kg)'].apply(
                    lambda v: f"{v:.1f}" if pd.notna(v) and v else '—'
                )
                df_grid = df_grid[['Data', 'Tipo', 'Fazenda', 'Quantidade', 'Peso Médio (kg)']]
                df_grid = df_grid.sort_values('Data')
                st.dataframe(df_grid, use_container_width=True, hide_index=True)
            else:
                st.info(f"📊 Sem dados para gerar gráficos em {month_name} de {cal_year}.")

    except Exception as e:
        st.error(f"❌ Erro: {e}")
    finally:
        if 'conn' in locals(): conn.close()

    # --- PLANEJAMENTO PAGE (separate connection to Vipper_KNW) ---
    if page == "📐 Planejamento":
        try:
            from datetime import timedelta
            vconn = get_vipper_connection()

            # --- Load simulations ---
            df_sim = pd.read_sql("SELECT * FROM tab_simulacao ORDER BY data DESC", vconn)
            if df_sim.empty:
                st.warning("Nenhuma simulação encontrada no banco de dados Vipper_KNW.")
                vconn.close()
                return

            # A. Seletor de Simulação
            sim_options = df_sim.apply(lambda r: f"{r['Cod_Simulacao']} - {r['Cod_Fazenda']} - {r['Cod_Plano']}", axis=1).tolist()
            
            c1, c2 = st.columns([3, 1])
            with c1:
                selected_sim_str = st.selectbox("Selecione a Simulação (Cod_Simulacao - Fazenda - Plano):", sim_options)
            with c2:
                st.markdown("<br>", unsafe_allow_html=True)
                # The HTML markdown approach doesn't work well due to st.markdown sanitizing onClick attributes natively
                # Using an iframe via components.html is the robust way to do this in Streamlit
                
                print_button_html = """
                <!DOCTYPE html>
                <html>
                <head>
                <style>
                    .btn-print {
                        display: block; 
                        padding: 0.5rem 1rem; 
                        background-color: #064e3b; 
                        color: white !important; 
                        border-radius: 4px; 
                        text-decoration: none; 
                        border: none;
                        font-family: inherit; 
                        font-size: 0.875rem; 
                        font-weight: 500; 
                        cursor: pointer;
                        text-align: center;
                        font-family: "Outfit", sans-serif;
                    }
                    .btn-print:hover { background-color: #059669; }
                </style>
                </head>
                <body style="margin:0; padding:0; display:flex; justify-content:flex-end;">
                    <button onclick="window.parent.print()" class="btn-print">
                        📄 Exportar PDF
                    </button>
                </body>
                </html>
                """
                
                # Keep the CSS formatting for when the print actually triggers
                st.markdown(
                    '''
                    <style>
                        @media print {
                            body, .stApp {
                                -webkit-print-color-adjust: exact !important;
                                print-color-adjust: exact !important;
                            }
                            
                            @page {
                                size: landscape;
                                margin: 1cm;
                            }
                            .stApp { background-color: white !important; color: black !important; }
                            
                            /* Ocultar elementos desnecessarios na impressao */
                            section[data-testid="stSidebar"] { display: none !important; }
                            header[data-testid="stHeader"] { display: none !important; }
                            div[data-testid="stToolbar"] { display: none !important; }
                            
                            /* Cleanup padding and borders */
                            .stMainBlockContainer { 
                                padding-top: 1rem !important; 
                            }
                            
                            /* Forcar o Dataframe do Streamlit a caber na largura da folha A4 paisagem sem ficar minúsculo */
                            [data-testid="stDataFrame"] {
                                zoom: 0.88 !important;
                                /* Safari fallback: */
                                -webkit-transform: scale(0.88);
                                -webkit-transform-origin: 0 0;
                            }
                            
                            /* Desativar Breakpoint Mobile de Colunas do Streamlit no modo Print para manter lado-a-lado 50/50 nas divs */
                            [data-testid="stHorizontalBlock"] {
                                flex-wrap: nowrap !important;
                                display: flex !important;
                            }
                            [data-testid="column"] {
                                width: 50% !important;
                                min-width: 50% !important;
                                max-width: 50% !important;
                                flex: 1 1 50% !important;
                            }
                            
                            /* Forcar visibilidade dos Cards (Metric) que perdem contraste no fundo branco do PDF */
                            [data-testid="stMetric"], [data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stMetricDelta"] {
                                color: black !important;
                                display: block !important;
                                visibility: visible !important;
                            }
                            
                            /* O background do Plotly/Altair sera transparente no SVG/Canvas sem forçar */
                            
                            /* Evitar que blocos fatiem no meio de uma pagina p/ outra */
                            .element-container { 
                                break-inside: avoid !important; 
                                page-break-inside: avoid; 
                            }
                        }
                    </style>
                    ''',
                    unsafe_allow_html=True
                )
                
                components.html(print_button_html, height=50)
            
            cod_sim = int(selected_sim_str.split(' - ')[0])
            sim_row = df_sim[df_sim['Cod_Simulacao'] == cod_sim].iloc[0]
            periodos = int(sim_row['Periodos'])
            peso_alvo = float(sim_row['Peso_Alvo'])

            # --- Load detailed data for selected simulation ---
            import warnings
            warnings.filterwarnings('ignore')
            df_peso = pd.read_sql(f"SELECT * FROM peso_simulado WHERE cod_simulacao={cod_sim}", vconn)
            df_cms = pd.read_sql(f"SELECT * FROM CMS_simulado WHERE cod_simulacao={cod_sim}", vconn)
            df_alim = pd.read_sql(f"SELECT * FROM alim_simulado WHERE cod_simulacao={cod_sim}", vconn)
            
            vconn.close()

            if df_peso.empty:
                st.info("A Simulação selecionada não possui dados processados em peso_simulado.")
                return

            st.markdown(f"**Peso Alvo:** {peso_alvo} kg | **Períodos da Simulação:** {periodos}")

            # ==========================================
            # C. Grid de Evolução (Agrupado por Lote) - AGORA PRIMEIRO NA TELA
            # ==========================================
            st.markdown("---")
            st.markdown("""
                <div class="section-header" style="padding-bottom: 8px; border-bottom: 1px solid rgba(6,78,59,0.12);">
                    <div class="icon-box icon-green">
                        <span class="mat-icon">table_rows</span>
                    </div>
                    <div>
                        <div class="section-title">Evolução do Rebanho (Por Lote)</div>
                        <div class="section-subtitle">Acompanhamento de peso médio e vendas por período</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            lotes = sorted(df_peso['cod_lote'].dropna().unique())
            rows_lote = []
            
            dt_final_global = None
            if 'dataFinal' in df_peso.columns and not df_peso['dataFinal'].dropna().empty:
                dt_f = pd.to_datetime(df_peso['dataFinal'].dropna().iloc[0])
                dt_final_global = dt_f.strftime('%d/%m/%Y') if hasattr(dt_f, 'strftime') else str(dt_f)[0:10]
            else:
                dt_final_global = "Final"
                
            for lote in lotes:
                lp = df_peso[df_peso['cod_lote'] == lote]
                n_inicial = len(lp)
                peso_inicial = float(lp['Peso'].mean()) if not lp['Peso'].empty else 0.0
                sexo = lp['sexo'].iloc[0] if not lp['sexo'].empty else ''
                gpd_medio = float(lp['GPD'].mean()) if 'GPD' in lp.columns and not lp['GPD'].empty else 0.0

                row_l = {
                    ('Animais', 'Lote'): str(lote),
                    ('Animais', 'Qtd.'): n_inicial,
                    ('Animais', 'Sexo'): sexo,
                    ('Animais', 'Peso'): round(peso_inicial, 1),
                    ('Animais', 'GPD'): round(gpd_medio, 3)
                }

                n_prev = n_inicial
                for i in range(1, periodos + 1):
                    d_col = f'Data{i}'
                    p_col = f'Peso{i}'
                    if d_col in lp.columns:
                        dt_val = df_peso[d_col].dropna().iloc[0] if not df_peso[d_col].dropna().empty else f"P{i}"
                        dt_str = dt_val.strftime('%d/%m/%Y') if hasattr(dt_val, 'strftime') else str(dt_val)
                        
                        ativos_idx = lp[d_col].notna()
                        n_ativos = int(ativos_idx.sum())
                        
                        n_vendidos = n_prev - n_ativos    
                        n_prev = n_ativos
                        
                        peso_medio = float(lp.loc[ativos_idx, p_col].mean()) if p_col in lp.columns and ativos_idx.any() else None
                        
                        row_l[(dt_str, 'Qtd.')] = n_ativos
                        row_l[(dt_str, 'Peso')] = round(peso_medio, 1) if pd.notna(peso_medio) else None
                        row_l[(dt_str, 'Vendas')] = n_vendidos

                if 'PesoFinal' in df_peso.columns:
                    peso_fin = float(lp['PesoFinal'].mean()) if not lp['PesoFinal'].dropna().empty else None
                    row_l[(dt_final_global, 'Peso Final')] = round(peso_fin, 1) if pd.notna(peso_fin) else None
                    
                rows_lote.append(row_l)

            # Para um MultiIndex funcionar no st.dataframe nativamente a partir do Pandas 1.4+ e Streamlit:
            # precisamos preparar o dataframe usando set_index nas colunas corretamente.
            columns_tuples = []
            if rows_lote:
                columns_tuples = list(rows_lote[0].keys())

            mux = pd.MultiIndex.from_tuples(columns_tuples)
            
            # Remove keys and flatten for dataframe creation, we assign mux directly to columns
            data_flattened = []
            for row in rows_lote:
                data_flattened.append([row[col] for col in columns_tuples])

            df_lotes = pd.DataFrame(data_flattened, columns=mux)
            
            # Totalizer row
            total_row_data = []
            for col in mux:
                group, name = col
                if name in ['Qtd.', 'Vendas'] and name != 'Lote':
                    total_row_data.append(df_lotes[col].sum())
                elif name in ['Peso', 'GPD', 'Peso Final'] and name != 'Lote':
                    med = float(df_lotes[col].mean()) if df_lotes[col].notna().any() else None
                    total_row_data.append(round(med, 2) if med is not None else None)
                elif name == 'Lote':
                    total_row_data.append('TOTAL')
                else:
                    total_row_data.append(None)
            
            df_lotes.loc[len(df_lotes)] = total_row_data
            df_lotes_disp = df_lotes.fillna('—')
            
            st.dataframe(df_lotes_disp, use_container_width=True)


            # ==========================================
            # PREPARE DATA FOR RESUMO FINANCEIRO E GRÁFICO
            # ==========================================
            summary_rows = []
            chart_data = []

            for i in range(1, periodos + 1):
                d_col = f'Data{i}'
                if d_col not in df_peso.columns: continue

                dt_val = df_peso[d_col].dropna().iloc[0] if not df_peso[d_col].dropna().empty else f"P{i}"
                dt_str = dt_val.strftime('%d/%m/%Y') if hasattr(dt_val, 'strftime') else str(dt_val)

                # 1. Entradas
                receitas = float(df_peso[f'Rec{i}'].sum()) if f'Rec{i}' in df_peso.columns and df_peso[f'Rec{i}'].notna().any() else 0.0

                # Lógica de Venda
                is_present = df_peso[f'Data{i}'].notna()
                if i < periodos and f'Data{i+1}' in df_peso.columns:
                    is_next_absent = df_peso[f'Data{i+1}'].isna()
                else:
                    # do not assume sale in last period unless explicitly missing before last checking
                    is_next_absent = pd.Series(False, index=df_peso.index)
                
                sold_idx = is_present & is_next_absent
                faturamento_vendas = float(df_peso.loc[sold_idx, f'Valor{i}'].sum()) if f'Valor{i}' in df_peso.columns and sold_idx.any() else 0.0

                # 2. Saídas
                custo_diarias = float(df_cms[f'Diaria{i}'].sum()) if f'Diaria{i}' in df_cms.columns and df_cms[f'Diaria{i}'].notna().any() else 0.0
                
                alim_custos_detalhe = {}
                alim_consumo_detalhe = {}
                total_custo_alim = 0.0
                if not df_alim.empty and f'Custo{i}' in df_alim.columns and f'C{i}' in df_alim.columns and 'TIPOR' in df_alim.columns:
                    for alim_name in df_alim['TIPOR'].unique():
                        # Custo sum
                        alim_val = float(df_alim.loc[df_alim['TIPOR'] == alim_name, f'Custo{i}'].sum())
                        alim_val = alim_val if pd.notna(alim_val) else 0.0
                        alim_custos_detalhe[alim_name] = alim_val
                        total_custo_alim += alim_val
                        
                        # Consumo / Quantidade sum (C)
                        alim_qtd = float(df_alim.loc[df_alim['TIPOR'] == alim_name, f'C{i}'].sum())
                        alim_qtd = alim_qtd if pd.notna(alim_qtd) else 0.0
                        alim_consumo_detalhe[alim_name] = alim_qtd

                resultado_operacional = receitas - (custo_diarias + total_custo_alim)

                row = {
                    'Período': dt_str,
                    'Receita': round(receitas, 2),
                    'Venda': round(faturamento_vendas, 2),
                    'Diária': round(custo_diarias, 2),
                    'Alimentos': round(total_custo_alim, 2),
                }
                for k, v in alim_consumo_detalhe.items():
                    row[f'{k}'] = round(v, 2)
                    
                row['Resultado'] = round(resultado_operacional, 2)
                
                summary_rows.append(row)
                
                chart_data.append({
                    'Período': dt_str,
                    'Receitas': receitas,
                    'Custo Diárias': custo_diarias,
                    'Custo Alimentos': total_custo_alim,
                    'Custo Total Acumulado': custo_diarias + total_custo_alim,
                    'Resultado': resultado_operacional
                })

            df_summary = pd.DataFrame(summary_rows)
            df_chart = pd.DataFrame(chart_data)
            
            # calculate accumulated results for the chart using cumsum()
            if not df_chart.empty:
                df_chart['Resultado Acumulado'] = df_chart['Resultado'].cumsum()

            
            # ==========================================
            # D. Resumo Colunar Grid e Gráfico (B) lado a lado
            # ==========================================
            st.markdown("---")
            
            col_grid, col_chart = st.columns([1, 1])
            
            with col_grid:
                st.markdown("""
                    <div class="section-header" style="padding-bottom: 8px; border-bottom: 1px solid rgba(190,24,93,0.12);">
                        <div class="icon-box icon-magenta">
                            <span class="mat-icon">view_column</span>
                        </div>
                        <div>
                            <div class="section-title">Resumo Financeiro</div>
                            <div class="section-subtitle">Valores financeiros e volumes por data</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                format_dict = {c: '{:,.2f}' for c in df_summary.columns if c != 'Período'}
                st.dataframe(df_summary.style.format(format_dict), use_container_width=True, hide_index=True)
                
                # Cards abaixo do Grid - usando HTML puro para garantir renderização no PDF
                if not df_summary.empty:
                    # Totais
                    total_venda = df_summary['Venda'].sum()
                    total_diaria = df_summary['Diária'].sum()
                    total_alim_custo = df_summary['Alimentos'].sum()
                    total_resultado = df_summary['Resultado'].sum()
                    
                    resultado_color = '#059669' if total_resultado >= 0 else '#dc2626'
                    
                    # Cards menores para o volume de cada alimento
                    food_cols = [c for c in df_summary.columns if c not in ['Período', 'Receita', 'Venda', 'Diária', 'Alimentos', 'Resultado']]
                    food_cards_html = ''
                    for f_col in food_cols:
                        total_vol = df_summary[f_col].sum()
                        food_cards_html += f'''
                            <div style="flex:1; text-align:center; padding: 6px 4px; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;">
                                <div style="font-size: 0.7rem; color: #64748b; font-weight:600;">{f_col}</div>
                                <div style="font-size: 0.85rem; font-weight: 700; color: #1e293b;">{total_vol:,.1f} kg</div>
                            </div>'''
                    
                    cards_html = f'''
                    <div style="display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap;">
                        <div style="flex:1; text-align:center; padding: 8px 6px; background: #f0fdf4; border-radius: 8px; border: 1px solid #bbf7d0;">
                            <div style="font-size: 0.7rem; color: #64748b; font-weight:600;">Faturamento</div>
                            <div style="font-size: 0.9rem; font-weight: 700; color: #059669;">R$ {total_venda:,.2f}</div>
                        </div>
                        <div style="flex:1; text-align:center; padding: 8px 6px; background: #fdf2f8; border-radius: 8px; border: 1px solid #fbcfe8;">
                            <div style="font-size: 0.7rem; color: #64748b; font-weight:600;">Diárias</div>
                            <div style="font-size: 0.9rem; font-weight: 700; color: #be185d;">R$ {total_diaria:,.2f}</div>
                        </div>
                        <div style="flex:1; text-align:center; padding: 8px 6px; background: #fff1f2; border-radius: 8px; border: 1px solid #fecdd3;">
                            <div style="font-size: 0.7rem; color: #64748b; font-weight:600;">Alimentos</div>
                            <div style="font-size: 0.9rem; font-weight: 700; color: #e11d48;">R$ {total_alim_custo:,.2f}</div>
                        </div>
                        <div style="flex:1; text-align:center; padding: 8px 6px; background: #f8fafc; border-radius: 8px; border: 2px solid {resultado_color};">
                            <div style="font-size: 0.7rem; color: #64748b; font-weight:600;">Resultado</div>
                            <div style="font-size: 0.9rem; font-weight: 700; color: {resultado_color};">R$ {total_resultado:,.2f}</div>
                        </div>
                    </div>
                    '''
                    st.markdown(cards_html, unsafe_allow_html=True)
                    
                    # Cards de volume de alimentos - construídos via concatenação simples
                    if food_cols:
                        food_html = '<div style="margin-top: 8px; font-size: 0.8rem; font-weight: 600; color: #475569;">Volumes Totais de Alimentos</div>'
                        food_html += '<div style="display: flex; gap: 6px; margin-top: 4px;">'
                        for f_col in food_cols:
                            total_vol = df_summary[f_col].sum()
                            food_html += '<div style="flex:1; text-align:center; padding: 6px 4px; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;">'
                            food_html += '<div style="font-size: 0.7rem; color: #64748b; font-weight:600;">' + str(f_col) + '</div>'
                            food_html += '<div style="font-size: 0.85rem; font-weight: 700; color: #1e293b;">' + f"{total_vol:,.1f} kg" + '</div>'
                            food_html += '</div>'
                        food_html += '</div>'
                        st.markdown(food_html, unsafe_allow_html=True)

            with col_chart:
                st.markdown("""
                    <div class="section-header" style="padding-bottom: 8px; border-bottom: 1px solid rgba(6,78,59,0.12);">
                        <div class="icon-box icon-green">
                            <span class="mat-icon">show_chart</span>
                        </div>
                        <div>
                            <div class="section-title">Evolução Financeira</div>
                            <div class="section-subtitle">Receitas, Custos e Resultado Acumulado</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
                import altair as alt

                if not df_chart.empty:
                    n_periodos = len(df_chart)
                    # Largura dinâmica das barras: quanto mais períodos, mais finas
                    bar_size = max(8, min(35, int(180 / n_periodos)))
                    
                    # Configurando o dataset para a lógica de "Receitas Lado a Lado com Custos Empilhados"
                    df_bars = df_chart[['Período', 'Receitas', 'Custo Diárias', 'Custo Alimentos']].copy()
                    df_bars = df_bars.melt(id_vars=['Período'], var_name='Categoria', value_name='Valor')
                    
                    # Vamos ter 2 grupos paralelos por Data: 'Receitas' e 'Custos'
                    df_bars['Grupo'] = df_bars['Categoria'].apply(lambda c: 'Receita' if c == 'Receitas' else 'Custo')
                    df_bars['Valor'] = df_bars['Valor'].abs()
                    
                    # Barras de receitas e custos lado a lado
                    bars = alt.Chart(df_bars).mark_bar(size=bar_size).encode(
                        x=alt.X('Período:O', title='', sort=None, axis=alt.Axis(labelAngle=-25)),
                        xOffset=alt.XOffset('Grupo:N', sort=['Receita', 'Custo']),
                        y=alt.Y('Valor:Q', title='R$', axis=alt.Axis(format='~s')),
                        color=alt.Color('Categoria:N', 
                            scale=alt.Scale(
                                domain=['Receitas', 'Custo Diárias', 'Custo Alimentos'],
                                range=['#059669', '#be185d', '#fb7185']
                            ),
                            legend=alt.Legend(title=None, orient='top', labelFontSize=11)
                        ),
                        tooltip=[alt.Tooltip('Período:O'), alt.Tooltip('Categoria:N'), alt.Tooltip('Valor:Q', format=',.2f', title='Valor (R$)')]
                    )

                    # Linha de resultado acumulado cruzando o gráfico
                    line = alt.Chart(df_chart).mark_line(color='#d97706', strokeWidth=3).encode(
                        x=alt.X('Período:O', sort=None),
                        y=alt.Y('Resultado Acumulado:Q', title=''),
                        tooltip=[alt.Tooltip('Período:O'), alt.Tooltip('Resultado Acumulado:Q', format=',.2f', title='Resultado Acumulado (R$)')]
                    )
                    
                    # Marcadores para as pontas da linha
                    points = alt.Chart(df_chart).mark_circle(color='#d97706', size=60, opacity=1).encode(
                        x=alt.X('Período:O', sort=None),
                        y=alt.Y('Resultado Acumulado:Q', title='')
                    )

                    final_chart = (bars + line + points).properties(
                        height=320
                    ).configure_view(
                        strokeWidth=0
                    ).configure_axis(
                        labelFont='Outfit', titleFont='Outfit',
                        gridOpacity=0.2
                    )

                    st.altair_chart(final_chart, use_container_width=True)
                else:
                    st.info("Não há dados financeiros para exibir.")

        except Exception as e:
            st.error(f"❌ Erro ao carregar dados de Planejamento: {e}")
            st.info("Verifique se as tabelas de simulação existem e possuem dados válidos no banco Vipper_KNW.")

if __name__ == "__main__":
    main()
