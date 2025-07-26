# plotting/trend_plots.py
import plotly.graph_objects as go
import numpy as np
from config import style_config as sc
from config.hospital_targets import HospitalTargets

def _add_common_traces(fig, summary_df, y_col, target_value, target_label):
    """グラフに共通の要素（目標線、平均線など）を追加するヘルパー関数"""
    if target_value is not None:
        warning_threshold = target_value * 0.95
        # 注意ゾーン
        fig.add_trace(go.Scatter(x=summary_df.iloc[:, 0], y=[target_value] * len(summary_df), mode='lines', line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(x=summary_df.iloc[:, 0], y=[warning_threshold] * len(summary_df), mode='lines', line=dict(width=0), fill='tonexty', fillcolor=sc.WARNING_ZONE_FILL, showlegend=False))
        # 目標ライン
        fig.add_trace(go.Scatter(x=summary_df.iloc[:, 0], y=[target_value] * len(summary_df), mode='lines', name=f"目標 ({target_value:.1f} {target_label})", line=sc.TARGET_LINE_STYLE))

    # 期間平均
    period_avg = summary_df[y_col].mean()
    fig.add_trace(go.Scatter(x=summary_df.iloc[:, 0], y=[period_avg] * len(summary_df), mode='lines', name=f'期間平均 ({period_avg:.1f})', line=sc.AVERAGE_LINE_STYLE))

def create_weekly_summary_chart(summary_df, title, target_dict):
    """病院全体の週次サマリーグラフを作成"""
    fig = go.Figure()
    if summary_df.empty:
        return fig.update_layout(title="グラフデータがありません")

    y_col = '平日1日平均件数'
    fig.add_trace(go.Scatter(x=summary_df['週'], y=summary_df[y_col], mode='lines+markers', name='平日1日平均', line=dict(color=sc.PRIMARY_COLOR), marker=sc.PRIMARY_MARKER))
    
    # 🔧 修正：病院全体目標を設定ファイルから取得
    hospital_daily_target = HospitalTargets.get_daily_target('weekday_gas_surgeries')
    _add_common_traces(fig, summary_df, y_col, hospital_daily_target, "件/日")

    fig.update_layout(title=title, xaxis_title="週 (月曜始まり)", yaxis_title="平日1日平均件数", **sc.LAYOUT_DEFAULTS)
    return fig

def create_weekly_dept_chart(summary_df, dept_name, target_dict):
    """診療科別の週次グラフを作成"""
    fig = go.Figure()
    if summary_df.empty:
        return fig.update_layout(title="グラフデータがありません")
    
    y_col = '週合計件数'
    fig.add_trace(go.Scatter(x=summary_df['週'], y=summary_df[y_col], mode='lines+markers', name='週合計', line=dict(color=sc.PRIMARY_COLOR), marker=sc.PRIMARY_MARKER))
    
    # 診療科別は元のまま（target_dictから取得）
    target_value = target_dict.get(dept_name)
    _add_common_traces(fig, summary_df, y_col, target_value, "件/週")
    
    fig.update_layout(title=f"{dept_name} 週次推移", xaxis_title="週 (月曜始まり)", yaxis_title="週合計件数", **sc.LAYOUT_DEFAULTS)
    return fig

def create_monthly_summary_chart(summary_df, title, target_dict):
    """病院全体の月次グラフを作成"""
    fig = go.Figure()
    if summary_df.empty:
        return fig.update_layout(title="グラフデータがありません")

    y_col = '平日1日平均件数'
    fig.add_trace(go.Scatter(x=summary_df['月'], y=summary_df[y_col], mode='lines+markers', name='平日1日平均', line=dict(color=sc.PRIMARY_COLOR), marker=sc.PRIMARY_MARKER))

    # 🔧 修正：病院全体目標を設定ファイルから取得
    hospital_daily_target = HospitalTargets.get_daily_target('weekday_gas_surgeries')
    _add_common_traces(fig, summary_df, y_col, hospital_daily_target, "件/日")
    
    fig.update_layout(title=title, xaxis_title="月", yaxis_title="平日1日平均件数", **sc.LAYOUT_DEFAULTS)
    return fig

def create_quarterly_summary_chart(summary_df, title, target_dict):
    """病院全体の四半期グラフ（棒グラフ）を作成"""
    fig = go.Figure()
    if summary_df.empty:
        return fig.update_layout(title="グラフデータがありません")
        
    y_col = '平日1日平均件数'
    fig.add_trace(go.Bar(x=summary_df['四半期ラベル'], y=summary_df[y_col], name='平日1日平均', marker_color=sc.PRIMARY_COLOR, opacity=0.8))
    
    # 🔧 修正：病院全体目標を設定ファイルから取得
    hospital_daily_target = HospitalTargets.get_daily_target('weekday_gas_surgeries')
    _add_common_traces(fig, summary_df, y_col, hospital_daily_target, "件/日")
    
    fig.update_layout(title=title, xaxis_title="四半期", yaxis_title="平日1日平均件数", **sc.LAYOUT_DEFAULTS)
    return fig

# 診療科別の月次・四半期グラフも同様にここに追加可能