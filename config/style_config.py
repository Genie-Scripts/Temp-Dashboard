# config/style_config.py
import pandas as pd
import plotly.io as pio
import streamlit as st

def load_dashboard_css():
    """ダッシュボード用のカスタムCSSを読み込み"""
    st.markdown("""
    <style>
        /* メインコンテナのスタイルなど */
        .main .block-container {
            padding: 1rem 2rem;
        }
        .stAlert > div {
            border-radius: 10px;
        }
        /* 必要に応じて他のスタイルを追加 */
    </style>
    """, unsafe_allow_html=True)

# Plotlyグラフのテンプレート設定
PLOT_TEMPLATE = "plotly_white"

# --- 色定義 ---
PRIMARY_COLOR = 'royalblue'
SECONDARY_COLOR = 'green'
TARGET_COLOR = 'red'
AVERAGE_LINE_COLOR = 'darkred'
WARNING_ZONE_FILL = 'rgba(255, 165, 0, 0.15)'
ANNOTATION_COLOR = 'black'
PREDICTION_COLOR = 'orange'
PREDICTION_ACTUAL_COLOR = PRIMARY_COLOR
YOY_COLOR = 'mediumseagreen'
RANKING_BAR_GREEN = 'rgba(76, 175, 80, 0.8)'
RANKING_BAR_ORANGE = 'rgba(255, 152, 0, 0.8)'
RANKING_BAR_RED = 'rgba(244, 67, 54, 0.8)'
GRID_COLOR = 'rgba(230, 230, 230, 0.7)'
TABLE_HEADER_BG = '#f0f2f6'

# --- 線スタイル定義 (Plotly Go用辞書) ---
TARGET_LINE_STYLE = dict(color=TARGET_COLOR, dash='dot', width=2)
AVERAGE_LINE_STYLE = dict(color=AVERAGE_LINE_COLOR, dash='dashdot', width=1.5)
MOVING_AVERAGE_LINE_STYLE = dict(color=SECONDARY_COLOR, width=2.5)
YOY_LINE_STYLE = dict(color=YOY_COLOR, dash='dot', width=2)
PREDICTION_LINE_STYLE = dict(color=PREDICTION_COLOR, dash='dash', width=2)
PREDICTION_ACTUAL_LINE_STYLE = dict(color=PREDICTION_ACTUAL_COLOR, width=2)

# --- マーカー定義 (Plotly Go用辞書) ---
PRIMARY_MARKER = dict(size=6, color=PRIMARY_COLOR)
YOY_MARKER = dict(size=7, symbol='diamond', color=YOY_COLOR)
PREDICTION_MARKER = dict(size=6, color=PREDICTION_COLOR)
PREDICTION_ACTUAL_MARKER = dict(size=6, color=PREDICTION_ACTUAL_COLOR)

# --- フォント定義 ---
ANNOTATION_FONT = dict(color=ANNOTATION_COLOR, size=12)
TITLE_FONT_SIZE = 16
AXIS_LABEL_FONT_SIZE = 12
TICK_FONT_SIZE = 11
LEGEND_FONT_SIZE = 11
TABLE_FONT_SIZE = "12px"

# --- レイアウト共通設定 (Plotly Go用辞書) ---
LAYOUT_DEFAULTS = dict(
    template=PLOT_TEMPLATE,
    margin=dict(l=50, r=30, t=70, b=50),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=LEGEND_FONT_SIZE)
    ),
    title_font=dict(size=TITLE_FONT_SIZE),
    xaxis=dict(
        title_font=dict(size=AXIS_LABEL_FONT_SIZE),
        tickfont=dict(size=TICK_FONT_SIZE),
        showgrid=True,
        gridcolor=GRID_COLOR
        ),
    yaxis=dict(
        title_font=dict(size=AXIS_LABEL_FONT_SIZE),
        tickfont=dict(size=TICK_FONT_SIZE),
        showgrid=True,
        gridcolor=GRID_COLOR
        )
)

# --- ランキンググラフ用 (Plotly Express用) ---
RANKING_COLOR_MAP = {
    'green': RANKING_BAR_GREEN,
    'orange': RANKING_BAR_ORANGE,
    'red': RANKING_BAR_RED
}

# --- テーブルスタイル (Streamlit DataFrame Styler用) ---
TABLE_STYLE_PROPS = [
    {'selector': 'th', 'props': [
        ('background-color', TABLE_HEADER_BG),
        ('font-weight', 'bold'),
        ('text-align', 'center'),
        ('font-size', TABLE_FONT_SIZE)
        ]},
    {'selector': 'td', 'props': [
        ('text-align', 'right'),
        ('font-size', TABLE_FONT_SIZE)
        ]},
]