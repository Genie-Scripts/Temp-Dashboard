# chart.py (再修正版)
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.font_manager
import gc
import time
import hashlib
import logging

logger = logging.getLogger(__name__)

# ===== Streamlit UI用関数（キャッシュあり） =====
@st.cache_data(ttl=1800, show_spinner=False)
def create_patient_chart(data, title="入院患者数推移", days=90, show_moving_average=True, font_name_for_mpl=None):
    """データから患者数推移グラフを作成する（Streamlit UI用、キャッシュ対応版）"""
    return _create_patient_chart_core(data, title, days, show_moving_average, font_name_for_mpl)

@st.cache_data(ttl=1800, show_spinner=False)
def create_dual_axis_chart(data, title="入院患者数と患者移動の推移", filename=None, days=90, font_name_for_mpl=None):
    """入院患者数と患者移動の7日移動平均グラフを二軸で作成する（Streamlit UI用、キャッシュ対応版）"""
    return _create_dual_axis_chart_core(data, title, days, font_name_for_mpl)

# ===== PDF生成用関数（キャッシュなし、直接実行） =====
def create_patient_chart_for_pdf(data, title="入院患者数推移", days=90, show_moving_average=True, font_name_for_mpl=None):
    """PDF生成専用の患者数推移グラフ（キャッシュなし）"""
    return _create_patient_chart_core(data, title, days, show_moving_average, font_name_for_mpl)

def create_dual_axis_chart_for_pdf(data, title="入院患者数と患者移動の推移", days=90, font_name_for_mpl=None):
    """PDF生成専用の二軸グラフ（キャッシュなし）"""
    return _create_dual_axis_chart_core(data, title, days, font_name_for_mpl)

# ===== 共通のコア関数 =====
def _create_patient_chart_core(data, title="入院患者数推移", days=90, show_moving_average=True, font_name_for_mpl=None):
    """患者数推移グラフの共通コア関数"""
    start_time = time.time()
    fig = None
    try:
        fig, ax = plt.subplots(figsize=(10, 5.5))

        if not isinstance(data, pd.DataFrame) or data.empty:
            if fig: plt.close(fig)
            return None

        if "日付" not in data.columns or "入院患者数（在院）" not in data.columns:
            if fig: plt.close(fig)
            return None

        data_copy = data.copy()
        if not pd.api.types.is_datetime64_any_dtype(data_copy['日付']):
            data_copy['日付'] = pd.to_datetime(data_copy['日付'], errors='coerce')
            data_copy.dropna(subset=['日付'], inplace=True)

        grouped = data_copy.groupby("日付")["入院患者数（在院）"].sum().reset_index().sort_values("日付")

        if len(grouped) > days and days > 0:
            grouped = grouped.tail(days)

        if grouped.empty:
            if fig: plt.close(fig)
            return None

        ax.plot(grouped["日付"], grouped["入院患者数（在院）"], marker='o', linestyle='-', linewidth=1.5, markersize=3, color='#3498db', label='入院患者数')
        avg = grouped["入院患者数（在院）"].mean()
        ax.axhline(y=avg, color='#e74c3c', linestyle='--', alpha=0.7, linewidth=1, label=f'平均: {avg:.1f}')

        if show_moving_average and len(grouped) >= 7:
            grouped['7日移動平均'] = grouped["入院患者数（在院）"].rolling(window=7, min_periods=1).mean()
            ax.plot(grouped["日付"], grouped['7日移動平均'], linestyle='-', linewidth=1.2, color='#2ecc71', label='7日移動平均')

        font_kwargs = {}
        if font_name_for_mpl:
            font_kwargs['fontname'] = font_name_for_mpl

        ax.set_title(title, fontsize=12, **font_kwargs)
        ax.set_xlabel('日付', fontsize=9, **font_kwargs)
        ax.set_ylabel('患者数', fontsize=9, **font_kwargs)

        ax.grid(True, linestyle=':', linewidth=0.5, alpha=0.7)
        legend_prop = {'size': 7}
        if font_name_for_mpl: legend_prop['family'] = font_name_for_mpl
        ax.legend(prop=legend_prop)

        fig.autofmt_xdate(rotation=30, ha='right')
        ax.tick_params(axis='x', labelsize=7)
        ax.tick_params(axis='y', labelsize=7)

        plt.tight_layout(pad=0.5)
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)

        end_time = time.time()
        logger.debug(f"グラフ '{title}' 生成完了, 処理時間: {end_time - start_time:.2f}秒")
        return buf
        
    except Exception as e:
        logger.error(f"グラフ生成エラー '{title}': {e}", exc_info=True)
        return None
    finally:
        if fig: 
            plt.close(fig)
        gc.collect()

def _create_dual_axis_chart_core(data, title="入院患者数と患者移動の推移", days=90, font_name_for_mpl=None):
    """二軸グラフの共通コア関数"""
    start_time = time.time()
    fig = None
    try:
        fig, ax1 = plt.subplots(figsize=(10, 5.5))

        if not isinstance(data, pd.DataFrame) or data.empty:
            if fig: plt.close(fig)
            return None

        required_columns = ["日付", "入院患者数（在院）", "新入院患者数", "緊急入院患者数", "総退院患者数"]
        if any(col not in data.columns for col in required_columns):
            if fig: plt.close(fig)
            return None

        data_copy = data.copy()
        if not pd.api.types.is_datetime64_any_dtype(data_copy['日付']):
            data_copy['日付'] = pd.to_datetime(data_copy['日付'], errors='coerce')
            data_copy.dropna(subset=['日付'], inplace=True)

        grouped = data_copy.groupby("日付").agg({
            "入院患者数（在院）": "sum", "新入院患者数": "sum",
            "緊急入院患者数": "sum", "総退院患者数": "sum"
        }).reset_index().sort_values("日付")

        if len(grouped) > days and days > 0: 
            grouped = grouped.tail(days)
        if grouped.empty:
            if fig: plt.close(fig)
            return None

        cols_for_ma = ["入院患者数（在院）", "新入院患者数", "緊急入院患者数", "総退院患者数"]
        for col in cols_for_ma:
            if col in grouped.columns:
                grouped[f'{col}_7日移動平均'] = grouped[col].rolling(window=7, min_periods=1).mean()
            else:
                logger.warning(f"Warning: Column '{col}' not found for MA in '{title}'.")
                grouped[f'{col}_7日移動平均'] = 0

        font_kwargs = {}
        if font_name_for_mpl: 
            font_kwargs['fontname'] = font_name_for_mpl

        if "入院患者数（在院）_7日移動平均" in grouped.columns:
             ax1.plot(grouped["日付"], grouped["入院患者数（在院）_7日移動平均"], color='#3498db', linewidth=2, label="入院患者数（在院）")
        else:
            logger.warning(f"Warning: '入院患者数（在院）_7日移動平均' not found for plotting in '{title}'.")

        ax1.set_xlabel('日付', fontsize=9, **font_kwargs)
        ax1.set_ylabel('入院患者数（在院）', fontsize=9, color='#3498db', **font_kwargs)
        ax1.tick_params(axis='y', labelcolor='#3498db', labelsize=8)
        ax1.tick_params(axis='x', labelsize=8)

        ax2 = ax1.twinx()
        colors_map = {"新入院患者数": "#2ecc71", "緊急入院患者数": "#e74c3c", "総退院患者数": "#f39c12"}
        for col, color_val in colors_map.items():
            ma_col_name = f"{col}_7日移動平均"
            if ma_col_name in grouped.columns:
                ax2.plot(grouped["日付"], grouped[ma_col_name], color=color_val, linewidth=1.5, label=col)

        ax2.set_ylabel('患者移動数', fontsize=9, **font_kwargs)
        ax2.tick_params(axis='y', labelsize=8)

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        legend_prop = {'size': 9}
        if font_name_for_mpl: 
            legend_prop['family'] = font_name_for_mpl
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', prop=legend_prop)

        plt.title(title, fontsize=12, **font_kwargs)
        fig.autofmt_xdate(rotation=30, ha='right')
        ax1.grid(True, linestyle=':', linewidth=0.5, alpha=0.7)
        plt.tight_layout(pad=0.5)

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150)
        buf.seek(0)
        
        end_time = time.time()
        logger.debug(f"二軸グラフ '{title}' 生成完了, 処理時間: {end_time - start_time:.2f}秒")
        return buf
        
    except Exception as e:
        logger.error(f"Error in _create_dual_axis_chart_core ('{title}'): {e}", exc_info=True)
        return None
    finally:
        if fig: 
            plt.close(fig)
        gc.collect()

# ===== インタラクティブグラフ関数 =====

def create_interactive_patient_chart(data, title="入院患者数推移", days=90, show_moving_average=True, target_value=None, chart_type="全日"):
    """インタラクティブな患者数推移グラフを作成する (Plotly) - パフォーマンス最適化版"""
    try:
        if not isinstance(data, pd.DataFrame) or data.empty:
            logger.warning(f"create_interactive_patient_chart: '{title}' のデータが空です。")
            return None
        if "日付" not in data.columns or "入院患者数（在院）" not in data.columns:
            logger.warning(f"create_interactive_patient_chart: '{title}' のデータに必要な列がありません。")
            return None

        data_copy = data.copy()
        if not pd.api.types.is_datetime64_any_dtype(data_copy['日付']):
            data_copy['日付'] = pd.to_datetime(data_copy['日付'], errors='coerce')
            data_copy.dropna(subset=['日付'], inplace=True)

        grouped = data_copy.groupby("日付")["入院患者数（在院）"].sum().reset_index().sort_values("日付")
        
        if grouped.empty or len(grouped) == 0:
            return None

        if len(grouped) > days and days > 0:
            grouped = grouped.tail(days)

        if grouped.empty:
            return None

        # ★★★ パフォーマンス最適化: 長期間データのリサンプリング ★★★
        original_length = len(grouped)
        resampled = False
        
        if days > 365 and len(grouped) > 365:
            # 365日以上の場合は週次平均にリサンプリング
            grouped['日付'] = pd.to_datetime(grouped['日付'])
            grouped.set_index('日付', inplace=True)
            grouped = grouped.resample('W').agg({
                '入院患者数（在院）': 'mean'
            }).reset_index()
            grouped = grouped.dropna()
            resampled = True
            logger.info(f"長期間データ（{days}日）のため週次平均にリサンプリング: {original_length}点 → {len(grouped)}点")
        elif days > 180 and len(grouped) > 180:
            # 180日以上365日未満の場合は3日平均にリサンプリング
            grouped['日付'] = pd.to_datetime(grouped['日付'])
            grouped.set_index('日付', inplace=True)
            grouped = grouped.resample('3D').agg({
                '入院患者数（在院）': 'mean'
            }).reset_index()
            grouped = grouped.dropna()
            resampled = True
            logger.info(f"長期間データ（{days}日）のため3日平均にリサンプリング: {original_length}点 → {len(grouped)}点")

        avg = grouped["入院患者数（在院）"].mean()
        
        # 移動平均の計算（リサンプリング時は窓サイズを調整）
        if show_moving_average and len(grouped) >= 7:
            if resampled and days > 365:
                # 週次データの場合は4週移動平均（約1ヶ月）
                window_size = min(4, len(grouped))
            elif resampled:
                # 3日データの場合は3点移動平均（約1週間）
                window_size = min(3, len(grouped))
            else:
                # 通常は7日移動平均
                window_size = min(7, len(grouped))
            
            grouped['移動平均'] = grouped["入院患者数（在院）"].rolling(window=window_size, min_periods=1).mean()

        fig = go.Figure()
        
        # ★★★ マーカー表示の最適化 ★★★
        if days > 180:
            # 180日を超える場合はマーカーなし
            mode = 'lines'
            marker_settings = None
        elif days > 90:
            # 90日を超える場合は小さめのマーカー
            mode = 'lines+markers'
            marker_settings = dict(size=4, color='#3498db')
        else:
            # 90日以下は通常サイズのマーカー
            mode = 'lines+markers'
            marker_settings = dict(size=6, color='#3498db')
        
        # メインのグラフ要素
        fig.add_trace(go.Scatter(
            x=grouped["日付"], 
            y=grouped["入院患者数（在院）"], 
            mode=mode,
            name='入院患者数' if not resampled else '入院患者数（平均）', 
            line=dict(color='#3498db', width=2),
            marker=marker_settings,
            hovertemplate='%{x|%m月%d日}<br>患者数: %{y:.1f}人<extra></extra>'
        ))
        
        # 移動平均線
        if show_moving_average and '移動平均' in grouped.columns:
            ma_label = '移動平均'
            if resampled and days > 365:
                ma_label = '4週移動平均'
            elif resampled:
                ma_label = '3点移動平均'
            else:
                ma_label = '7日移動平均'
                
            fig.add_trace(go.Scatter(
                x=grouped["日付"], 
                y=grouped['移動平均'], 
                mode='lines',
                name=ma_label, 
                line=dict(color='#2ecc71', width=2),
                hovertemplate='%{x|%m月%d日}<br>' + ma_label + ': %{y:.1f}人<extra></extra>'
            ))

        # 平均線（長期間の場合は表示しない）
        if days <= 180:
            fig.add_trace(go.Scatter(
                x=[grouped["日付"].min(), grouped["日付"].max()], 
                y=[avg, avg], 
                mode='lines', 
                name=f'期間平均: {avg:.1f}', 
                line=dict(color='#e74c3c', dash='dash', width=2),
                hoverinfo='skip'
            ))

        # 目標値と達成ゾーンの表示
        if target_value is not None and pd.notna(target_value):
            # 目標線
            fig.add_trace(go.Scatter(
                x=[grouped["日付"].min(), grouped["日付"].max()], 
                y=[target_value, target_value], 
                mode='lines', 
                name=f'目標値: {target_value:.1f}', 
                line=dict(color='#9b59b6', dash='dot', width=2),
                hoverinfo='skip'
            ))

            # Y軸の範囲を計算
            data_min = grouped["入院患者数（在院）"].min()
            data_max = grouped["入院患者数（在院）"].max()
            y_min = data_min * 0.9 if data_min > 0 else 0
            y_max = max(data_max, target_value) * 1.10  # ★★★ 修正: 1.05 → 1.10 (10%の余裕)
            
            # 達成ゾーン（目標値以上）- 薄い緑色
            fig.add_trace(go.Scatter(
                x=[grouped["日付"].min(), grouped["日付"].max(), grouped["日付"].max(), grouped["日付"].min()], 
                y=[target_value, target_value, y_max, y_max], 
                fill='toself', 
                fillcolor='rgba(46, 204, 113, 0.15)',
                line=dict(color='rgba(46, 204, 113, 0)', width=0), 
                name='達成ゾーン',
                showlegend=True,
                hoverinfo='skip'
            ))
            
            # 注意ゾーン（目標値の97%～目標値）- 薄いオレンジ色
            caution_threshold = target_value * 0.97
            fig.add_trace(go.Scatter(
                x=[grouped["日付"].min(), grouped["日付"].max(), grouped["日付"].max(), grouped["日付"].min()], 
                y=[caution_threshold, caution_threshold, target_value, target_value], 
                fill='toself', 
                fillcolor='rgba(255, 165, 0, 0.15)',
                line=dict(color='rgba(255, 165, 0, 0)', width=0), 
                name='注意ゾーン',
                showlegend=True,
                hoverinfo='skip'
            ))
            
            fig.update_yaxes(range=[y_min, y_max])
        else:
            # ★★★ 追加: 目標値がない場合もY軸の上限に10%の余裕を追加
            data_max = grouped["入院患者数（在院）"].max()
            data_min = grouped["入院患者数（在院）"].min()
            
            # 移動平均がある場合はその最大値も考慮
            if '移動平均' in grouped.columns:
                ma_max = grouped['移動平均'].max()
                data_max = max(data_max, ma_max)
            
            y_min = data_min * 0.9 if data_min > 0 else 0
            y_max = data_max * 1.10  # 10%の余裕
            
            fig.update_yaxes(range=[y_min, y_max])

        # タイトルの設定（リサンプリング情報を含む）
        display_title = title if title else ""  # 空文字の場合の処理を明確化
        if resampled and display_title:
            if days > 365:
                display_title += " (週次平均)"
            else:
                display_title += " (3日平均)"

        # レイアウト設定（日付表記改善版）
        fig.update_layout(
            title={'text': display_title, 'x': 0.5} if display_title else {},  
            xaxis_title='日付', 
            yaxis_title='患者数', 
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1
                # ★修正: font=dict(size=10) を削除（デフォルトサイズに統一）
            ), 
            hovermode='x unified', 
            height=400,
            margin=dict(l=50, r=20, t=60 if display_title else 40, b=80),
            xaxis=dict(
                tickformat='%m/%d' if days <= 90 else '%Y/%m',
                nticks=15 if days <= 90 else 20 if days <= 180 else 10,
                tickangle=-45,
                tickfont=dict(size=10)
            )
        )        
        # グリッドの設定（長期間の場合は薄くする）
        fig.update_xaxes(showgrid=True, gridwidth=0.5 if days <= 180 else 0.3, gridcolor='rgba(128,128,128,0.2)')
        fig.update_yaxes(showgrid=True, gridwidth=0.5 if days <= 180 else 0.3, gridcolor='rgba(128,128,128,0.2)')
        
        return fig
        
    except Exception as e:
        logger.error(f"インタラクティブグラフ '{title}' 作成中にエラー: {e}", exc_info=True)
        return None

def create_interactive_dual_axis_chart(data, title="患者移動と在院数の推移", days=90):
    """【修正】インタラクティブな患者移動グラフ (Plotly) - 緊急入院を追加 & Y軸余裕追加 & 日付表記改善"""
    try:
        if data is None or data.empty:
            return None
        
        # ★★★ 修正箇所: `required_cols` に '緊急入院患者数' を追加 ★★★
        required_cols = ["日付", "入院患者数（在院）", "新入院患者数", "総退院患者数", "緊急入院患者数"]
        if any(col not in data.columns for col in required_cols):
            return None

        data_copy = data.copy()
        if not pd.api.types.is_datetime64_any_dtype(data_copy['日付']):
            data_copy['日付'] = pd.to_datetime(data_copy['日付'], errors='coerce').dropna(subset=['日付'])

        agg_dict = {col: "sum" for col in required_cols if col != "日付"}
        grouped = data_copy.groupby("日付").agg(agg_dict).reset_index().sort_values("日付")
        
        if len(grouped) > days and days > 0:
            grouped = grouped.tail(days)
        if grouped.empty: return None

        for col in required_cols[1:]:
            grouped[f'{col}_7日MA'] = grouped[col].rolling(window=7, min_periods=1).mean()

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # 主軸: 在院患者数（マーカー付き）
        fig.add_trace(go.Scatter(
            x=grouped["日付"], 
            y=grouped["入院患者数（在院）_7日MA"], 
            name="在院患者数(7日MA)", 
            mode='lines+markers',  # ★修正: マーカー付きに
            line=dict(color='#3498db', width=2.5),
            marker=dict(size=6, color='#3498db')  # ★追加: マーカー設定
        ), secondary_y=False)

        # 副軸の線（新入院、退院など）は移動平均なのでマーカーなし
        colors_map = {
            "新入院患者数": "#2ecc71",
            "総退院患者数": "#f39c12",
            "緊急入院患者数": "#e74c3c"
        }
        for col, color in colors_map.items():
            ma_col_name = f"{col}_7日MA"
            if ma_col_name in grouped.columns:
                fig.add_trace(go.Scatter(
                    x=grouped["日付"], 
                    y=grouped[ma_col_name], 
                    name=f"{col}(7日MA)", 
                    mode='lines',  # ラインのみ
                    line=dict(color=color, width=2)
                ), secondary_y=True)

        # ★★★ 追加: Y軸の範囲を計算して10%の余裕を追加
        # 主軸（在院患者数）
        primary_max = grouped["入院患者数（在院）_7日MA"].max()
        primary_min = grouped["入院患者数（在院）_7日MA"].min()
        primary_range = [
            primary_min * 0.9 if primary_min > 0 else 0,
            primary_max * 1.10  # 10%の余裕
        ]
        
        # 副軸（患者移動数）
        secondary_cols = [f"{col}_7日MA" for col in colors_map.keys()]
        secondary_values = []
        for col in secondary_cols:
            if col in grouped.columns:
                secondary_values.extend(grouped[col].values)
        
        if secondary_values:
            secondary_max = max(secondary_values)
            secondary_min = min(secondary_values)
            secondary_range = [
                secondary_min * 0.9 if secondary_min > 0 else 0,
                secondary_max * 1.10  # 10%の余裕
            ]
        else:
            secondary_range = None

        # レイアウト設定（日付表記改善版）
        fig.update_layout(
            title={'text': title, 'x': 0.5},
            xaxis_title='日付',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode='x unified',
            height=400,
            margin=dict(l=50, r=20, t=60, b=80),  # マージンを調整
            xaxis=dict(
                tickformat='%m/%d',  # 月/日の日本語形式
                nticks=15,  # ティック数を適切に設定
                tickangle=-45,  # 45度傾ける
                tickfont=dict(size=10)  # フォントサイズ
            )
        )
        
        # ★★★ Y軸の範囲設定
        fig.update_yaxes(title_text="在院患者数", secondary_y=False, range=primary_range)
        if secondary_range:
            fig.update_yaxes(title_text="患者移動数", secondary_y=True, range=secondary_range)
        else:
            fig.update_yaxes(title_text="患者移動数", secondary_y=True)
            
        return fig
    except Exception as e:
        logger.error(f"インタラクティブ2軸グラフ '{title}' 作成中にエラー: {e}", exc_info=True)
        return None

def create_interactive_alos_chart(chart_data, title="ALOS推移", days_to_show=90, moving_avg_window=30):
    """インタラクティブなALOS（平均在院日数）グラフを作成する (Plotly) - 期間平均線追加版 & Y軸余裕追加 & 日付表記改善"""
    try:
        if not isinstance(chart_data, pd.DataFrame) or chart_data.empty:
            return None
        
        required_columns = ["日付", "入院患者数（在院）", "総入院患者数", "総退院患者数"]
        if any(col not in chart_data.columns for col in required_columns):
            return None

        data_copy = chart_data.copy()
        if not pd.api.types.is_datetime64_any_dtype(data_copy['日付']):
            data_copy['日付'] = pd.to_datetime(data_copy['日付'], errors='coerce')
            data_copy.dropna(subset=['日付'], inplace=True)
        if data_copy.empty: return None

        latest_date = data_copy['日付'].max()
        start_date_limit = latest_date - pd.Timedelta(days=days_to_show - 1)
        date_range_for_plot = pd.date_range(start=start_date_limit, end=latest_date, freq='D')
        
        daily_metrics = []
        for display_date in date_range_for_plot:
            window_start = display_date - pd.Timedelta(days=moving_avg_window - 1)
            window_data = data_copy[(data_copy['日付'] >= window_start) & (data_copy['日付'] <= display_date)]
            
            if not window_data.empty:
                total_patient_days = window_data['入院患者数（在院）'].sum()
                total_admissions = window_data['総入院患者数'].sum()
                total_discharges = window_data['総退院患者数'].sum()
                num_days_in_window = window_data['日付'].nunique()
                
                denominator = (total_admissions + total_discharges) / 2
                alos = total_patient_days / denominator if denominator > 0 else np.nan
                daily_census = total_patient_days / num_days_in_window if num_days_in_window > 0 else np.nan
                
                daily_metrics.append({'日付': display_date, '平均在院日数': alos, '平均在院患者数': daily_census})

        if not daily_metrics: return None
        daily_df = pd.DataFrame(daily_metrics).sort_values('日付')
        if daily_df.empty: return None

        # 期間平均の計算
        avg_alos = daily_df['平均在院日数'].mean()
        avg_census = daily_df['平均在院患者数'].mean()

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # 平均在院日数（マーカー付き）
        fig.add_trace(
            go.Scatter(
                x=daily_df['日付'], 
                y=daily_df['平均在院日数'], 
                name=f'平均在院日数 ({moving_avg_window}日MA)', 
                mode='lines+markers',
                line=dict(color='#3498db', width=2),
                marker=dict(size=6, color='#3498db')
            ),
            secondary_y=False
        )
        
        # 平均在院日数の期間平均線（破線）
        fig.add_trace(
            go.Scatter(
                x=[daily_df['日付'].min(), daily_df['日付'].max()],
                y=[avg_alos, avg_alos],
                mode='lines',
                name=f'期間平均: {avg_alos:.1f}日',
                line=dict(color='#3498db', width=2, dash='dash'),
                hoverinfo='skip'
            ),
            secondary_y=False
        )
        
        # 平均在院患者数（実線、マーカーなし）
        fig.add_trace(
            go.Scatter(
                x=daily_df['日付'], 
                y=daily_df['平均在院患者数'], 
                name='平均在院患者数', 
                mode='lines',
                line=dict(color='#e74c3c', width=2)
            ),
            secondary_y=True
        )
        
        # 平均在院患者数の期間平均線（破線）
        fig.add_trace(
            go.Scatter(
                x=[daily_df['日付'].min(), daily_df['日付'].max()],
                y=[avg_census, avg_census],
                mode='lines',
                name=f'期間平均(退院日のみ): {avg_census:.1f}人', # ← 凡例のテキストを修正
                line=dict(color='#e74c3c', width=2, dash='dash'),
                hoverinfo='skip'
            ),
            secondary_y=True
        )
        
        # Y軸の範囲を計算して10%の余裕を追加
        # 主軸（平均在院日数）
        alos_max = daily_df['平均在院日数'].max()
        alos_min = daily_df['平均在院日数'].min()
        alos_range = [
            alos_min * 0.9 if alos_min > 0 else 0,
            alos_max * 1.10
        ]
        
        # 副軸（平均在院患者数）
        census_max = daily_df['平均在院患者数'].max()
        census_min = daily_df['平均在院患者数'].min()
        census_range = [
            census_min * 0.9 if census_min > 0 else 0,
            census_max * 1.10
        ]
        
        display_title = title if title else ""
        
        # レイアウト設定
        fig.update_layout(
            title={'text': display_title, 'x': 0.5} if display_title else {},
            xaxis_title='日付',
            legend=dict(
                orientation="h", 
                yanchor="bottom", 
                y=1.02, 
                xanchor="right", 
                x=1
            ),
            hovermode='x unified',
            height=400,
            margin=dict(l=50, r=20, t=60 if display_title else 40, b=80),
            xaxis=dict(
                tickformat='%m/%d',
                nticks=15,
                tickangle=-45,
                tickfont=dict(size=10)
            )
        )
        
        fig.update_yaxes(title_text="平均在院日数", secondary_y=False, range=alos_range)
        fig.update_yaxes(title_text="平均在院患者数", secondary_y=True, range=census_range)
        
        return fig

    except Exception as e:
        logger.error(f"インタラクティブALOSグラフ '{title}' 作成中にエラー: {e}", exc_info=True)
        return None

@st.cache_data(ttl=1800)
def create_forecast_comparison_chart(actual_series, forecast_results, title="年度患者数予測比較", display_days_past=365, display_days_future=365):
    """実績データと複数の予測モデルの結果を比較するインタラクティブグラフを作成する (Plotly)"""
    try:
        if actual_series.empty:
            logger.warning(f"create_forecast_comparison_chart: '{title}' の実績データが空です。")
            return None

        fig = go.Figure()

        if not actual_series.index.is_monotonic_increasing:
             actual_series = actual_series.sort_index()
        
        actual_display_data = actual_series
        if display_days_past > 0 and len(actual_series) > display_days_past:
            actual_display_start_date = actual_series.index.max() - pd.Timedelta(days=display_days_past -1)
            actual_display_data = actual_series[actual_series.index >= actual_display_start_date]

        fig.add_trace(go.Scatter(
            x=actual_display_data.index,
            y=actual_display_data,
            mode='lines',
            name='実績患者数',
            line=dict(color='blue', width=2)
        ))

        colors = ['red', 'green', 'purple', 'orange', 'brown']

        for i, (model_name, forecast_series) in enumerate(forecast_results.items()):
            if forecast_series is None or forecast_series.empty:
                continue

            forecast_display_data = forecast_series
            if display_days_future > 0 :
                pred_start_date = forecast_series.index.min()
                if not actual_series.empty:
                    pred_start_date = max(pred_start_date, actual_series.index.max() + pd.Timedelta(days=1))

                pred_end_date = pred_start_date + pd.Timedelta(days=display_days_future -1)
                forecast_display_data = forecast_series[(forecast_series.index >= pred_start_date) &
                                                        (forecast_series.index <= pred_end_date)]

            if not forecast_display_data.empty:
                fig.add_trace(go.Scatter(
                    x=forecast_display_data.index,
                    y=forecast_display_data,
                    mode='lines',
                    name=f'{model_name} (予測)',
                    line=dict(color=colors[i % len(colors)], width=2, dash='dash')
                ))

        fig.update_layout(
            title=title,
            xaxis_title='日付',
            yaxis_title='入院患者数（全日）',
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            hovermode='x unified',
            height=500,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        fig.update_xaxes(tickformat="%Y-%m-%d", tickangle=-45)
        return fig

    except Exception as e:
        logger.error(f"予測比較グラフ '{title}' 作成中にエラー: {e}", exc_info=True)
        return None