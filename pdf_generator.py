# pdf_generator.py (最適化完全版)
import pandas as pd
import streamlit as st
from io import BytesIO
import os
import re
import time
import hashlib
import gc
import numpy as np
import logging
from config import EXCLUDED_WARDS

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

import matplotlib.font_manager
import matplotlib.pyplot as plt
import matplotlib

# ロガーの設定
logger = logging.getLogger(__name__)

# ===========================================
# フォント設定（最適化版）
# ===========================================
FONT_DIR = 'fonts'
FONT_FILENAME = 'NotoSansJP-Regular.ttf'
FONT_PATH = os.path.join(FONT_DIR, FONT_FILENAME)
REPORTLAB_FONT_NAME = 'NotoSansJP_RL'
MATPLOTLIB_FONT_NAME_FALLBACK = 'sans-serif'
MATPLOTLIB_FONT_NAME = None

# フォント登録の状態を追跡（グローバル変数で重複防止）
_FONTS_REGISTERED = False

def register_fonts():
    """フォント登録（重複実行を防ぐ最適化版）"""
    global MATPLOTLIB_FONT_NAME, _FONTS_REGISTERED
    
    if _FONTS_REGISTERED:
        logger.debug("フォント登録済みのためスキップ")
        return  # 既に登録済みの場合はスキップ
    
    font_registered_rl = False
    font_registered_mpl = False

    if os.path.exists(FONT_PATH):
        try:
            pdfmetrics.registerFont(TTFont(REPORTLAB_FONT_NAME, FONT_PATH))
            logger.info(f"ReportLab font '{REPORTLAB_FONT_NAME}' registered.")
            font_registered_rl = True
        except Exception as e:
            logger.warning(f"Failed to register ReportLab font: {e}")

        try:
            font_entry = matplotlib.font_manager.FontEntry(
                fname=FONT_PATH, name='NotoSansJP_MPL_PDFGEN'
            )
            # 重複チェック（最適化）
            existing_font_names = {f.name for f in matplotlib.font_manager.fontManager.ttflist}
            if font_entry.name not in existing_font_names:
                matplotlib.font_manager.fontManager.ttflist.insert(0, font_entry)

            MATPLOTLIB_FONT_NAME = font_entry.name
            logger.info(f"Matplotlib font '{MATPLOTLIB_FONT_NAME}' prepared.")
            font_registered_mpl = True
        except Exception as e:
            logger.warning(f"Failed to prepare Matplotlib font: {e}")
            MATPLOTLIB_FONT_NAME = MATPLOTLIB_FONT_NAME_FALLBACK
    else:
        logger.info(f"Font file not found at '{FONT_PATH}'. Using fallback fonts.")
        MATPLOTLIB_FONT_NAME = MATPLOTLIB_FONT_NAME_FALLBACK

    _FONTS_REGISTERED = True
    logger.debug(f"フォント登録完了: RL={font_registered_rl}, MPL={font_registered_mpl}")

# モジュールインポート時にフォント登録
register_fonts()

# ===========================================
# キャッシュ設定（最適化版）
# ===========================================
def get_chart_cache():
    """メインプロセス専用キャッシュ（最適化版）"""
    try:
        if hasattr(st, 'session_state') and st.session_state is not None:
            if 'pdf_chart_cache' not in st.session_state:
                st.session_state.pdf_chart_cache = {}
            return st.session_state.pdf_chart_cache
    except:
        pass
    # ワーカープロセスまたはStreamlitコンテキスト外では空の辞書
    return {}

def compute_data_hash(data):
    """最適化されたデータハッシュ計算"""
    if data is None or data.empty: 
        return "empty_data_hash"
    try:
        # 大きなデータの場合はサンプリングしてハッシュ計算を高速化
        if len(data) > 5000:
            sample_data = data.sample(n=1000, random_state=42)
            return hashlib.md5(pd.util.hash_pandas_object(sample_data, index=True).values.tobytes()).hexdigest()[:12]
        else:
            return hashlib.md5(pd.util.hash_pandas_object(data, index=True).values.tobytes()).hexdigest()[:12]
    except Exception: 
        return hashlib.md5(str(time.time()).encode()).hexdigest()[:12]

def get_chart_cache_key(title, days, target_value=None, chart_type="default", data_hash=None):
    """最適化されたキャッシュキー生成"""
    components = [str(title)[:30], str(days)]  # タイトルを短縮
    if target_value is not None:
        try: 
            components.append(f"{float(target_value):.1f}")
        except (ValueError, TypeError): 
            components.append(str(target_value)[:10])
    else: 
        components.append("None")
    components.append(str(chart_type))
    if data_hash: 
        components.append(data_hash[:8])  # ハッシュを短縮
    key_string = "_".join(components)
    return hashlib.md5(key_string.encode()).hexdigest()[:12]  # キーを短縮

# ===========================================
# 最適化されたグラフ生成関数
# ===========================================
def cleanup_matplotlib_figure(fig):
    """Matplotlibの図を安全にクリーンアップ"""
    try:
        if fig:
            plt.close(fig)
        # 追加のクリーンアップ
        plt.close('all')
        gc.collect()
    except Exception as e:
        logger.debug(f"Figure cleanup error: {e}")

def create_alos_chart_for_pdf(
    chart_data, title_prefix="全体", latest_date=None,
    moving_avg_window=30, font_name_for_mpl_to_use=None,
    days_to_show=90
):
    """ALOS（平均在院日数）グラフ生成（最適化版）"""
    start_time = time.time()
    fig = None
    actual_font_name = font_name_for_mpl_to_use or MATPLOTLIB_FONT_NAME or MATPLOTLIB_FONT_NAME_FALLBACK
    
    try:
        # データの事前検証（高速化）
        if not isinstance(chart_data, pd.DataFrame) or chart_data.empty:
            return None
        
        required_columns = ["日付", "入院患者数（在院）", "総入院患者数", "総退院患者数"]
        if any(col not in chart_data.columns for col in required_columns):
            return None

        # matplotlib設定の最適化
        plt.style.use('default')  # スタイルをリセット
        fig, ax1 = plt.subplots(figsize=(8, 4.5), dpi=100)  # DPIを最適化

        data_copy = chart_data.copy()
        if not pd.api.types.is_datetime64_any_dtype(data_copy['日付']):
            data_copy['日付'] = pd.to_datetime(data_copy['日付'], errors='coerce')
            data_copy.dropna(subset=['日付'], inplace=True)
        
        if data_copy.empty:
            return None

        current_latest_date = latest_date if latest_date else data_copy['日付'].max()
        if pd.isna(current_latest_date):
            current_latest_date = pd.Timestamp.now()

        start_date_limit = current_latest_date - pd.Timedelta(days=days_to_show - 1)
        date_range_for_plot = pd.date_range(start=start_date_limit, end=current_latest_date, freq='D')
        
        # ベクトル化された計算で高速化
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
                
                daily_metrics.append({
                    '日付': display_date, 
                    '平均在院日数': alos, 
                    '平均在院患者数': daily_census
                })

        if not daily_metrics:
            return None
            
        daily_df = pd.DataFrame(daily_metrics).sort_values('日付')
        if daily_df.empty:
            return None

        # フォント設定（最適化）
        font_prop = matplotlib.font_manager.FontProperties(family=actual_font_name, size=9)

        # グラフ描画（最適化）
        ax1.plot(daily_df['日付'], daily_df['平均在院日数'], 
                color='#3498db', linewidth=2, marker='o', markersize=3, 
                label=f"平均在院日数({moving_avg_window}日MA)", markevery=max(1, len(daily_df)//20))
        
        ax1.set_xlabel('日付', fontproperties=font_prop)
        ax1.set_ylabel('平均在院日数', fontproperties=font_prop, color='#3498db')
        ax1.tick_params(axis='y', labelcolor='#3498db', labelsize=8)
        ax1.tick_params(axis='x', labelsize=8, rotation=30)

        ax2 = ax1.twinx()
        ax2.plot(daily_df['日付'], daily_df['平均在院患者数'], 
                color='#e74c3c', linewidth=2, linestyle='--', 
                label='平均在院患者数', markevery=max(1, len(daily_df)//20))
        ax2.set_ylabel('平均在院患者数', fontproperties=font_prop, color='#e74c3c')
        ax2.tick_params(axis='y', labelcolor='#e74c3c', labelsize=8)

        # 凡例の最適化
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', 
                  prop={'family': actual_font_name, 'size': 8})

        plt.title(f"{title_prefix} ALOS推移(直近{days_to_show}日)", fontproperties=font_prop, fontsize=11)
        ax1.grid(True, linestyle=':', linewidth=0.5, alpha=0.6)
        
        # レイアウト最適化
        plt.tight_layout(pad=0.5)
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        buf.seek(0)
        
        end_time = time.time()
        if end_time - start_time > 2.0:  # 2秒以上かかった場合のみログ
            logger.warning(f"ALOS chart for {title_prefix} took {end_time - start_time:.2f}s")
        
        return buf
        
    except Exception as e:
        logger.error(f"Error in create_alos_chart_for_pdf for {title_prefix}: {e}")
        return None
    finally:
        cleanup_matplotlib_figure(fig)
        gc.collect()

def create_patient_chart_with_target_wrapper(
    data, title="入院患者数推移", days=90, show_moving_average=True, target_value=None,
    font_name_for_mpl_to_use=None
):
    """患者数推移グラフ生成（最適化版）"""
    fig = None
    actual_font_name = font_name_for_mpl_to_use or MATPLOTLIB_FONT_NAME or MATPLOTLIB_FONT_NAME_FALLBACK
    
    try:
        # データの事前検証
        if not isinstance(data, pd.DataFrame) or data.empty:
            return None
        if "日付" not in data.columns or "入院患者数（在院）" not in data.columns:
            return None

        # 最適化されたfigureサイズとDPI
        fig, ax = plt.subplots(figsize=(8, 4), dpi=100)

        data_copy = data.copy()
        if not pd.api.types.is_datetime64_any_dtype(data_copy['日付']):
            data_copy['日付'] = pd.to_datetime(data_copy['日付'], errors='coerce')
            data_copy.dropna(subset=['日付'], inplace=True)
        
        if data_copy.empty:
            return None

        grouped = data_copy.groupby("日付")["入院患者数（在院）"].sum().reset_index().sort_values("日付")
        if len(grouped) > days and days > 0:
            grouped = grouped.tail(days)
        if grouped.empty:
            return None

        # フォント設定の最適化
        font_prop = matplotlib.font_manager.FontProperties(family=actual_font_name, size=9)

        # 基本グラフ要素（最適化）
        marker_every = max(1, len(grouped) // 15)  # マーカー間隔を動的調整
        ax.plot(grouped["日付"], grouped["入院患者数（在院）"], 
                marker='o', linestyle='-', linewidth=2, markersize=3, 
                color='#3498db', label='入院患者数', markevery=marker_every)
        
        avg = grouped["入院患者数（在院）"].mean()
        ax.axhline(y=avg, color='#e74c3c', linestyle='--', alpha=0.8, 
                   linewidth=1.5, label=f'平均: {avg:.1f}')

        if show_moving_average and len(grouped) >= 7:
            grouped['7日移動平均'] = grouped["入院患者数（在院）"].rolling(window=7, min_periods=1).mean()
            ax.plot(grouped["日付"], grouped['7日移動平均'], 
                    linestyle='-', linewidth=2, color='#2ecc71', 
                    label='7日移動平均', alpha=0.8)

        # 目標値処理（最適化）
        if target_value is not None and pd.notna(target_value):
            try:
                target_val_float = float(target_value)
                data_min = grouped["入院患者数（在院）"].min()
                data_max = grouped["入院患者数（在院）"].max()
                
                y_min = max(0, data_min * 0.9)
                y_max = max(data_max, target_val_float) * 1.05
                ax.set_ylim(bottom=y_min, top=y_max)
                
                # 達成ゾーン（透明度最適化）
                ax.fill_between(grouped["日付"], target_val_float, y_max, 
                               color='#2ecc71', alpha=0.15, label='達成ゾーン', zorder=1)
                
                # 注意ゾーン
                caution_threshold = target_val_float * 0.97
                ax.fill_between(grouped["日付"], caution_threshold, target_val_float, 
                               color='orange', alpha=0.15, label='注意ゾーン', zorder=2)
                
                # 目標線
                ax.axhline(y=target_val_float, color='#9b59b6', linestyle='-.', 
                          linewidth=2, label=f'目標値: {target_val_float:.1f}', zorder=10)
                
            except ValueError:
                pass

        # レイアウト最適化
        ax.set_title(title, fontproperties=font_prop, fontsize=11)
        ax.set_xlabel('日付', fontproperties=font_prop, fontsize=9)
        ax.set_ylabel('患者数', fontproperties=font_prop, fontsize=9)
        ax.grid(True, linestyle=':', linewidth=0.5, alpha=0.6, zorder=0)
        
        # 凡例の最適化（項目数制限）
        handles, labels = ax.get_legend_handles_labels()
        if len(handles) > 6:  # 凡例項目が多すぎる場合は重要なもののみ表示
            important_indices = [0, 1, -1]  # 最初、2番目、最後
            handles = [handles[i] for i in important_indices if i < len(handles)]
            labels = [labels[i] for i in important_indices if i < len(labels)]
        
        ax.legend(handles, labels, prop={'family': actual_font_name, 'size': 8}, 
                 loc='upper left', framealpha=0.9)
        
        # 軸の最適化
        ax.tick_params(axis='x', labelsize=7, rotation=30)
        ax.tick_params(axis='y', labelsize=8)

        plt.tight_layout(pad=0.5)
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buf.seek(0)
        return buf
        
    except Exception as e:
        logger.error(f"Error in create_patient_chart_with_target_wrapper ('{title}'): {e}")
        return None
    finally:
        cleanup_matplotlib_figure(fig)
        gc.collect()

def create_dual_axis_chart_for_pdf(data, title="患者移動と在院数", days=90, font_name_for_mpl_to_use=None):
    """二軸グラフ生成（最適化版）"""
    fig = None
    actual_font_name = font_name_for_mpl_to_use or MATPLOTLIB_FONT_NAME or MATPLOTLIB_FONT_NAME_FALLBACK
    
    try:
        # データの事前検証
        if not isinstance(data, pd.DataFrame) or data.empty:
            return None
        required_cols = ["日付", "入院患者数（在院）", "新入院患者数", "緊急入院患者数", "総退院患者数"]
        if any(col not in data.columns for col in required_cols):
            return None

        # 最適化されたfigureサイズとDPI
        fig, ax1 = plt.subplots(figsize=(8, 4), dpi=100)

        data_copy = data.copy()
        if not pd.api.types.is_datetime64_any_dtype(data_copy['日付']):
            data_copy['日付'] = pd.to_datetime(data_copy['日付'], errors='coerce')
            data_copy.dropna(subset=['日付'], inplace=True)
        
        if data_copy.empty:
            return None

        # データ集約の最適化
        agg_dict = {
            "入院患者数（在院）": "sum", 
            "新入院患者数": "sum", 
            "緊急入院患者数": "sum", 
            "総退院患者数": "sum"
        }
        grouped = data_copy.groupby("日付").agg(agg_dict).reset_index().sort_values("日付")
        
        if len(grouped) > days and days > 0:
            grouped = grouped.tail(days)
        if grouped.empty:
            return None

        # 移動平均計算の最適化
        cols_for_ma = ["入院患者数（在院）", "新入院患者数", "緊急入院患者数", "総退院患者数"]
        for col in cols_for_ma:
            if col in grouped.columns:
                grouped[f'{col}_7日MA'] = grouped[col].rolling(window=7, min_periods=1).mean()

        # フォント設定
        font_prop = matplotlib.font_manager.FontProperties(family=actual_font_name, size=9)

        # グラフ描画（最適化）
        marker_every = max(1, len(grouped) // 15)
        if "入院患者数（在院）_7日MA" in grouped.columns:
            ax1.plot(grouped["日付"], grouped["入院患者数（在院）_7日MA"], 
                    color='#3498db', linewidth=2.5, label="在院患者数(7日MA)",
                    marker='o', markersize=3, markevery=marker_every)
        
        ax1.set_xlabel('日付', fontproperties=font_prop)
        ax1.set_ylabel('在院患者数', fontproperties=font_prop, color='#3498db')
        ax1.tick_params(axis='y', labelcolor='#3498db', labelsize=8)
        ax1.tick_params(axis='x', labelsize=7, rotation=30)

        ax2 = ax1.twinx()
        
        # 重要な指標のみ表示（高速化）
        important_colors = {
            "新入院患者数": "#2ecc71", 
            "総退院患者数": "#f39c12"
        }
        for col, color_val in important_colors.items():
            ma_col_name = f"{col}_7日MA"
            if ma_col_name in grouped.columns:
                ax2.plot(grouped["日付"], grouped[ma_col_name], 
                        color=color_val, linewidth=2, label=f"{col}(7日MA)",
                        marker='s', markersize=2, markevery=marker_every, alpha=0.8)
        
        ax2.set_ylabel('患者移動数', fontproperties=font_prop)
        ax2.tick_params(axis='y', labelsize=8)

        # 凡例の最適化
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', 
                  prop={'family': actual_font_name, 'size': 8}, framealpha=0.9)

        plt.title(title, fontproperties=font_prop, fontsize=11)
        ax1.grid(True, linestyle=':', linewidth=0.5, alpha=0.6)
        plt.tight_layout(pad=0.5)
        
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        buf.seek(0)
        return buf
        
    except Exception as e:
        logger.error(f"Error in create_dual_axis_chart_for_pdf ('{title}'): {e}")
        return None
    finally:
        cleanup_matplotlib_figure(fig)
        gc.collect()

# ===========================================
# PDF生成メイン関数（最適化版）
# ===========================================
def create_pdf(
    forecast_df, df_weekday, df_holiday, df_all_avg=None,
    chart_data=None, title_prefix="全体", latest_date=None,
    target_data=None, filter_code="全体", graph_days=None,
    alos_chart_buffers=None,
    patient_chart_buffers=None,
    dual_axis_chart_buffers=None
):
    """PDF生成（最適化版）"""
    pdf_start_time = time.time()
    elements = []
    buffer = BytesIO()
    
    try:
        # PDF設定の最適化
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=15*mm, rightMargin=15*mm,
            topMargin=18*mm, bottomMargin=18*mm
        )

        # スタイル定義の最適化
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='Normal_JP', 
            parent=styles['Normal'], 
            fontName=REPORTLAB_FONT_NAME, 
            fontSize=8, 
            leading=10
        ))
        styles.add(ParagraphStyle(
            name='Heading1_JP', 
            parent=styles['Heading1'], 
            fontName=REPORTLAB_FONT_NAME, 
            fontSize=14, 
            spaceAfter=4*mm, 
            leading=16
        ))
        styles.add(ParagraphStyle(
            name='Heading2_JP', 
            parent=styles['Heading2'], 
            fontName=REPORTLAB_FONT_NAME, 
            fontSize=11, 
            spaceAfter=3*mm, 
            leading=13
        ))

        normal_ja = styles['Normal_JP']
        ja_style = styles['Heading1_JP']
        ja_heading2 = styles['Heading2_JP']

        # 日付処理の最適化
        current_latest_date = latest_date if latest_date else pd.Timestamp.now().normalize()
        if isinstance(current_latest_date, str):
            current_latest_date = pd.Timestamp(current_latest_date)
        
        data_date_str = current_latest_date.strftime("%Y年%m月%d日")
        today_str = pd.Timestamp.now().strftime("%Y年%m月%d日")

        # タイトル
        report_title_text = f"入院患者数予測 - {title_prefix}（データ基準日: {data_date_str}）"
        elements.append(Paragraph(report_title_text, ja_style))
        elements.append(Spacer(1, 4*mm))
        
        page_width = A4[0] - doc.leftMargin - doc.rightMargin
        graphs_on_current_page = 0
        max_graphs_per_page = 2

        # 共通グラフ配置関数（最適化）
        def add_graph_to_elements(chart_buffer_bytes, graph_title, days_str=None):
            nonlocal graphs_on_current_page
            
            if graphs_on_current_page >= max_graphs_per_page:
                elements.append(PageBreak())
                elements.append(Paragraph(report_title_text, ja_style))
                elements.append(Spacer(1, 4*mm))
                graphs_on_current_page = 0
            
            if chart_buffer_bytes:
                img_buf = BytesIO(chart_buffer_bytes)
                img_buf.seek(0)
                
                display_title = graph_title
                if days_str:
                    display_title += f"（直近{days_str}日間）"
                
                elements.append(Paragraph(display_title, ja_heading2))
                elements.append(Spacer(1, 2*mm))
                # 画像サイズを最適化
                elements.append(Image(img_buf, width=page_width*0.9, height=(page_width*0.9)*0.45))
                elements.append(Spacer(1, 3*mm))
                graphs_on_current_page += 1

        # ALOSグラフ配置
        if alos_chart_buffers:
            for days_val_str, chart_buffer_bytes in sorted(alos_chart_buffers.items(), key=lambda x: int(x[0])):
                add_graph_to_elements(chart_buffer_bytes, "平均在院日数推移", days_val_str)

        # 患者数推移グラフ配置
        if patient_chart_buffers:
            type_name_map = {"all": "全日", "weekday": "平日", "holiday": "休日"}
            for chart_type_key in ["all", "weekday", "holiday"]:
                day_buffers_dict = patient_chart_buffers.get(chart_type_key, {})
                if not day_buffers_dict:
                    continue
                
                display_name = type_name_map.get(chart_type_key, chart_type_key.capitalize())
                for days_val_str, chart_buffer_bytes in sorted(day_buffers_dict.items(), key=lambda x: int(x[0])):
                    add_graph_to_elements(chart_buffer_bytes, f"{display_name} 入院患者数推移", days_val_str)

        # 二軸グラフ配置
        if dual_axis_chart_buffers:
            for days_val_str, chart_buffer_bytes in sorted(dual_axis_chart_buffers.items(), key=lambda x: int(x[0])):
                add_graph_to_elements(chart_buffer_bytes, "患者移動推移", days_val_str)

        # テーブル用新ページ
        if graphs_on_current_page > 0:
            elements.append(PageBreak())
            elements.append(Paragraph(report_title_text, ja_style))
            elements.append(Spacer(1, 4*mm))

        # 共通テーブルスタイル（最適化）
        common_table_style_cmds = [
            ('FONTNAME', (0,0), (-1,-1), REPORTLAB_FONT_NAME),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,0), 'CENTER'), 
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('FONTSIZE', (0,1), (-1,-1), 8),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
            ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
            ('TOPPADDING', (0,0), (-1,-1), 1.5*mm),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1.5*mm),
        ]

        # テーブル生成関数（最適化）
        def create_table_from_dataframe(df, title, bg_color):
            if df is None or df.empty:
                return
            
            elements.append(Paragraph(title, ja_heading2))
            header = [df.index.name if df.index.name else "区分"] + df.columns.tolist()
            
            table_data = [header]
            for idx, row in df.iterrows():
                row_data = [str(idx)]
                for x in row:
                    if isinstance(x, (float, int)) and pd.notna(x):
                        row_data.append(f"{x:.1f}")
                    else:
                        row_data.append(str(x) if pd.notna(x) else "-")
                table_data.append(row_data)
            
            num_cols = len(header)
            col_widths = [page_width*0.25] + [(page_width*0.75)/(num_cols-1 if num_cols > 1 else 1)]*(num_cols-1)
            
            table_style = TableStyle(common_table_style_cmds + [('BACKGROUND', (0,0), (-1,0), bg_color)])
            elements.append(Table(table_data, colWidths=col_widths, style=table_style))
            elements.append(Spacer(1, 4*mm))

        # 主要テーブルの追加
        create_table_from_dataframe(df_all_avg, "全日平均値", colors.green)

        # 予測テーブルの追加
        if forecast_df is not None and not forecast_df.empty:
            fc_df_mod = forecast_df.copy()
            # 列名の最適化
            if "年間平均人日（実績＋予測）" in fc_df_mod.columns:
                fc_df_mod.rename(columns={"年間平均人日（実績＋予測）": "年度予測"}, inplace=True)
            if "延べ予測人日" in fc_df_mod.columns:
                fc_df_mod.drop(columns=["延べ予測人日"], inplace=True)
            
            create_table_from_dataframe(fc_df_mod, "在院患者数予測", colors.blue)

        # 新しいページで平日・休日テーブル
        elements.append(PageBreak())
        elements.append(Paragraph(report_title_text, ja_style))
        elements.append(Spacer(1, 4*mm))

        # 平日・休日テーブル
        create_table_from_dataframe(df_weekday, "平日平均値", colors.teal)
        create_table_from_dataframe(df_holiday, "休日平均値", colors.orange)

        # 部門別テーブル（条件付きで追加）
        if chart_data is not None and not chart_data.empty:
            try:
                ward_table_data, dept_table_data, period_labels = create_department_tables(
                    chart_data, current_latest_date, target_data, filter_code, None
                )
                
                # テーブルスタイルの最適化
                dept_ward_style = [
                    ('FONTNAME', (0,0), (-1,-1), REPORTLAB_FONT_NAME),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTSIZE', (0,0), (-1,0), 8),
                    ('FONTSIZE', (0,1), (-1,-1), 7),
                    ('LEFTPADDING', (0,0), (-1,-1), 1.5*mm),
                    ('RIGHTPADDING', (0,0), (-1,-1), 1.5*mm),
                ]
                
                is_ward_pdf = "病棟別" in title_prefix
                is_dept_pdf = "診療科別" in title_prefix
                
                # 病棟テーブル
                if (is_ward_pdf or not is_dept_pdf) and ward_table_data and len(ward_table_data) > 1:
                    elements.append(PageBreak())
                    elements.append(Paragraph(report_title_text, ja_style))
                    elements.append(Spacer(1, 4*mm))
                    elements.append(Paragraph("病棟別 入院患者数平均", ja_heading2))
                    
                    num_cols = len(ward_table_data[0])
                    col_widths_ward = [page_width/num_cols] * num_cols
                    
                    ward_table_style = TableStyle(dept_ward_style + [('BACKGROUND', (0,0), (-1,0), colors.lightgrey)])
                    elements.append(Table(ward_table_data, colWidths=col_widths_ward, style=ward_table_style))
                    elements.append(Spacer(1, 3*mm))
                
                # 診療科テーブル
                if (is_dept_pdf or not is_ward_pdf) and dept_table_data and len(dept_table_data) > 1:
                    if not is_ward_pdf or not ward_table_data:
                        elements.append(PageBreak())
                        elements.append(Paragraph(report_title_text, ja_style))
                        elements.append(Spacer(1, 4*mm))
                    
                    elements.append(Paragraph("診療科別 入院患者数平均", ja_heading2))
                    
                    num_cols = len(dept_table_data[0])
                    col_widths_dept = [page_width/num_cols] * num_cols
                    
                    dept_table_style = TableStyle(dept_ward_style + [('BACKGROUND', (0,0), (-1,0), colors.lightcyan)])
                    elements.append(Table(dept_table_data, colWidths=col_widths_dept, style=dept_table_style))
                    elements.append(Spacer(1, 3*mm))
                    
            except Exception as e:
                logger.error(f"部門別テーブル生成エラー: {e}")

        # フッター
        elements.append(Spacer(1, 6*mm))
        elements.append(Paragraph(f"作成日時: {today_str}", normal_ja))
        
        # PDF構築
        doc.build(elements)
        buffer.seek(0)
        
        pdf_end_time = time.time()
        if pdf_end_time - pdf_start_time > 5.0:  # 5秒以上かかった場合のみログ
            logger.warning(f"PDF generation for {title_prefix} took {pdf_end_time - pdf_start_time:.2f}s")
        
        return buffer
        
    except Exception as e:
        logger.error(f"PDF構築エラー ({title_prefix}): {e}")
        return None
    finally:
        gc.collect()
        
def create_landscape_pdf(
    forecast_df, df_weekday, df_holiday, df_all_avg=None,
    chart_data=None, title_prefix="全体", latest_date=None,
    target_data=None, filter_code="全体", graph_days=None,
    alos_chart_buffers=None,
    patient_chart_buffers=None,
    dual_axis_chart_buffers=None
):
    """横向きPDF生成（最適化版）"""
    pdf_start_time = time.time()
    elements = []
    buffer = BytesIO()
    
    try:
        # PDF設定（横向き用最適化）
        doc = SimpleDocTemplate(
            buffer, pagesize=landscape(A4),
            leftMargin=15*mm, rightMargin=15*mm,
            topMargin=15*mm, bottomMargin=15*mm
        )
        
        # スタイル定義（横向き用最適化）
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='Normal_JP_Land', 
            parent=styles['Normal'], 
            fontName=REPORTLAB_FONT_NAME, 
            fontSize=8, 
            leading=9
        ))
        styles.add(ParagraphStyle(
            name='Heading1_JP_Land', 
            parent=styles['Heading1'], 
            fontName=REPORTLAB_FONT_NAME, 
            fontSize=14, 
            spaceAfter=4*mm, 
            leading=16
        ))
        styles.add(ParagraphStyle(
            name='Heading2_JP_Land', 
            parent=styles['Heading2'], 
            fontName=REPORTLAB_FONT_NAME, 
            fontSize=11, 
            spaceAfter=3*mm, 
            leading=13
        ))
        styles.add(ParagraphStyle(
            name='Normal_Center_JP_Land', 
            parent=styles['Normal_JP_Land'], 
            alignment=TA_CENTER, 
            fontSize=7, 
            leading=8
        ))

        ja_style_land = styles['Heading1_JP_Land']
        ja_heading2_land = styles['Heading2_JP_Land']
        normal_ja_land = styles['Normal_JP_Land']
        para_style_normal_center_land = styles['Normal_Center_JP_Land']

        # 日付処理
        current_latest_date = latest_date if latest_date else pd.Timestamp.now().normalize()
        if isinstance(current_latest_date, str): 
            current_latest_date = pd.Timestamp(current_latest_date)
        
        data_date_str = current_latest_date.strftime("%Y年%m月%d日")
        today_str = pd.Timestamp.now().strftime("%Y年%m月%d日")
        
        report_title_text = f"入院患者数予測 - {title_prefix}（データ基準日: {data_date_str}）"
        elements.append(Paragraph(report_title_text, ja_style_land))
        elements.append(Spacer(1, 4*mm))
        
        # ページサイズ計算
        page_width_land, _ = landscape(A4)
        content_width_land = page_width_land - doc.leftMargin - doc.rightMargin
        graphs_on_current_page = 0
        max_graphs_per_page_land = 2

        # 共通グラフ配置関数（横向き用）
        def add_landscape_graph(chart_buffer_bytes, graph_title, days_str=None):
            nonlocal graphs_on_current_page
            
            if graphs_on_current_page >= max_graphs_per_page_land:
                elements.append(PageBreak())
                elements.append(Paragraph(report_title_text, ja_style_land))
                elements.append(Spacer(1, 4*mm))
                graphs_on_current_page = 0
            
            if chart_buffer_bytes:
                img_buf = BytesIO(chart_buffer_bytes)
                img_buf.seek(0)
                
                display_title = graph_title
                if days_str:
                    display_title += f"（直近{days_str}日間）"
                
                elements.append(Paragraph(display_title, ja_heading2_land))
                elements.append(Spacer(1, 2*mm))
                # 横向き用画像サイズ最適化
                elements.append(Image(img_buf, width=content_width_land*0.95, height=(content_width_land*0.95)*0.4))
                elements.append(Spacer(1, 3*mm))
                graphs_on_current_page += 1

        # ALOSグラフ配置（横向き）
        if alos_chart_buffers:
            for days_val_str, chart_buffer_bytes in sorted(alos_chart_buffers.items(), key=lambda x: int(x[0])):
                add_landscape_graph(chart_buffer_bytes, "平均在院日数と平均在院患者数の推移", days_val_str)

        # 患者数推移グラフ配置（横向き）
        if patient_chart_buffers:
            type_name_map = {"all": "全日", "weekday": "平日", "holiday": "休日"}
            for chart_type_key in ["all", "weekday", "holiday"]:
                day_buffers_dict = patient_chart_buffers.get(chart_type_key, {})
                if not day_buffers_dict:
                    continue
                
                display_name = type_name_map.get(chart_type_key, chart_type_key.capitalize())
                for days_val_str, chart_buffer_bytes in sorted(day_buffers_dict.items(), key=lambda x: int(x[0])):
                    add_landscape_graph(chart_buffer_bytes, f"{display_name} 入院患者数推移", days_val_str)

        # 二軸グラフ配置（横向き）
        if dual_axis_chart_buffers:
            for days_val_str, chart_buffer_bytes in sorted(dual_axis_chart_buffers.items(), key=lambda x: int(x[0])):
                add_landscape_graph(chart_buffer_bytes, "患者移動と在院数の推移", days_val_str)

        # テーブル生成（横向き用最適化）
        common_table_style_land_cmds = [
            ('FONTNAME', (0,0), (-1,-1), REPORTLAB_FONT_NAME),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,0), 'CENTER'), 
            ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
            ('ALIGN', (0,1), (0,-1), 'LEFT'),   
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('FONTSIZE', (0,1), (-1,-1), 8),   
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('LEFTPADDING', (0,0), (-1,-1), 2*mm),
            ('RIGHTPADDING', (0,0), (-1,-1), 2*mm),
            ('TOPPADDING', (0,0), (-1,-1), 1.5*mm),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1.5*mm),
        ]

        # テーブル生成関数（横向き用）
        def create_landscape_table(df, title, bg_color):
            if df is None or df.empty:
                return
            
            elements.append(Paragraph(title, ja_heading2_land))
            header = [df.index.name if df.index.name else "区分"] + df.columns.tolist()
            
            table_data = [header]
            for idx, row in df.iterrows():
                row_data = [str(idx)]
                for x in row:
                    if isinstance(x, (float, int)) and pd.notna(x):
                        row_data.append(f"{x:.1f}")
                    else:
                        row_data.append(str(x) if pd.notna(x) else "-")
                table_data.append(row_data)
            
            num_cols = len(header)
            col_widths = [content_width_land*0.2] + [(content_width_land*0.8)/(num_cols-1 if num_cols > 1 else 1)]*(num_cols-1)
            
            table_style = TableStyle(common_table_style_land_cmds + [('BACKGROUND', (0,0), (-1,0), bg_color)])
            elements.append(Table(table_data, colWidths=col_widths, style=table_style))
            elements.append(Spacer(1, 3*mm))

        # 主要テーブル（全日平均値）
        create_landscape_table(df_all_avg, "全日平均値", colors.green)

        # 予測テーブル
        if forecast_df is not None and not forecast_df.empty:
            fc_df_mod = forecast_df.copy()
            if "年間平均人日（実績＋予測）" in fc_df_mod.columns:
                fc_df_mod.rename(columns={"年間平均人日（実績＋予測）": "年度予測"}, inplace=True)
            if "延べ予測人日" in fc_df_mod.columns:
                fc_df_mod.drop(columns=["延べ予測人日"], inplace=True)
            
            create_landscape_table(fc_df_mod, "在院患者数予測", colors.blue)

        # 平日・休日テーブル（横向きレイアウト）
        elements.append(PageBreak())
        elements.append(Paragraph(report_title_text, ja_style_land))
        elements.append(Spacer(1, 4*mm))

        # 左右2列レイアウトでテーブル配置
        left_col_elements = []
        right_col_elements = []
        table_half_width = content_width_land * 0.48

        def create_half_width_table(df, title, bg_color):
            if df is None or df.empty:
                return []
            
            col_elements = []
            col_elements.append(Paragraph(title, ja_heading2_land))
            
            header = [df.index.name if df.index.name else "区分"] + df.columns.tolist()
            table_data = [header]
            for idx, row in df.iterrows():
                row_data = [str(idx)]
                for x in row:
                    if isinstance(x, (float, int)) and pd.notna(x):
                        row_data.append(f"{x:.1f}")
                    else:
                        row_data.append(str(x) if pd.notna(x) else "-")
                table_data.append(row_data)
            
            num_cols = len(header)
            col_widths = [table_half_width*0.3] + [(table_half_width*0.7)/(num_cols-1 if num_cols > 1 else 1)]*(num_cols-1)
            
            table_style = TableStyle(common_table_style_land_cmds + [('BACKGROUND', (0,0), (-1,0), bg_color)])
            col_elements.append(Table(table_data, colWidths=col_widths, style=table_style))
            
            return col_elements

        # 平日テーブル（左列）
        left_col_elements = create_half_width_table(df_weekday, "平日平均値", colors.teal)
        # 休日テーブル（右列）
        right_col_elements = create_half_width_table(df_holiday, "休日平均値", colors.orange)

        if left_col_elements or right_col_elements:
            # 2列レイアウト用テーブル
            two_col_data = [[
                left_col_elements if left_col_elements else "", 
                right_col_elements if right_col_elements else ""
            ]]
            two_col_table = Table(
                two_col_data, 
                colWidths=[table_half_width, content_width_land - table_half_width - 3*mm]
            )
            elements.append(two_col_table)
            elements.append(Spacer(1, 3*mm))

        # 部門別テーブル（横向き用）
        if chart_data is not None and not chart_data.empty:
            try:
                ward_table_data, dept_table_data, period_labels = create_department_tables(
                    chart_data, current_latest_date, target_data, filter_code, para_style_normal_center_land
                )
                
                dept_ward_style_land = [
                    ('FONTNAME', (0,0), (-1,-1), REPORTLAB_FONT_NAME),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTSIZE', (0,0), (-1,0), 8),
                    ('FONTSIZE', (0,1), (-1,-1), 7),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                    ('LEFTPADDING', (0,0), (-1,-1), 1*mm),
                    ('RIGHTPADDING', (0,0), (-1,-1), 1*mm),
                ]
                
                is_ward_pdf = "病棟別" in title_prefix
                is_dept_pdf = "診療科別" in title_prefix
                
                # 病棟テーブル
                if (is_ward_pdf or not is_dept_pdf) and ward_table_data and len(ward_table_data) > 1:
                    elements.append(PageBreak())
                    elements.append(Paragraph(report_title_text, ja_style_land))
                    elements.append(Spacer(1, 4*mm))
                    elements.append(Paragraph("病棟別 入院患者数（在院）平均", ja_heading2_land))
                    
                    num_cols = len(ward_table_data[0])
                    period_count = len(period_labels) if period_labels else 0
                    
                    # 列幅の動的計算
                    if period_count > 0:
                        col_widths_w = [content_width_land*0.12] + \
                                       [(content_width_land*0.70)/period_count]*period_count + \
                                       [content_width_land*0.09]*2
                    else:
                        col_widths_w = [content_width_land/num_cols] * num_cols
                    
                    if len(col_widths_w) != num_cols:
                        col_widths_w = [content_width_land/num_cols] * num_cols
                    
                    ward_table_style = TableStyle(dept_ward_style_land + [('BACKGROUND', (0,0), (-1,0), colors.lightgrey)])
                    elements.append(Table(ward_table_data, colWidths=col_widths_w, style=ward_table_style))
                    elements.append(Spacer(1, 3*mm))
                
                # 診療科テーブル
                if (is_dept_pdf or not is_ward_pdf) and dept_table_data and len(dept_table_data) > 1:
                    # 病棟テーブルが表示されていない場合は新しいページ
                    if not (is_ward_pdf and ward_table_data and len(ward_table_data) > 1):
                        elements.append(PageBreak())
                        elements.append(Paragraph(report_title_text, ja_style_land))
                        elements.append(Spacer(1, 4*mm))
                    
                    elements.append(Paragraph("診療科別 入院患者数（在院）平均", ja_heading2_land))
                    
                    num_cols = len(dept_table_data[0])
                    period_count = len(period_labels) if period_labels else 0
                    
                    # 列幅の動的計算
                    if period_count > 0:
                        col_widths_d = [content_width_land*0.12] + \
                                       [(content_width_land*0.70)/period_count]*period_count + \
                                       [content_width_land*0.09]*2
                    else:
                        col_widths_d = [content_width_land/num_cols] * num_cols
                    
                    if len(col_widths_d) != num_cols:
                        col_widths_d = [content_width_land/num_cols] * num_cols
                    
                    dept_table_style = TableStyle(dept_ward_style_land + [('BACKGROUND', (0,0), (-1,0), colors.lightcyan)])
                    elements.append(Table(dept_table_data, colWidths=col_widths_d, style=dept_table_style))
                    elements.append(Spacer(1, 3*mm))
                    
            except Exception as e:
                logger.error(f"横向きPDF部門別テーブル生成エラー: {e}")

        # フッター
        elements.append(Spacer(1, 6*mm))
        elements.append(Paragraph(f"作成日時: {today_str}", normal_ja_land))
        
        # PDF構築
        doc.build(elements)
        buffer.seek(0)
        
        pdf_end_time = time.time()
        if pdf_end_time - pdf_start_time > 5.0:
            logger.warning(f"Landscape PDF generation for {title_prefix} took {pdf_end_time - pdf_start_time:.2f}s")
        
        return buffer
        
    except Exception as e:
        logger.error(f"横向きPDF構築エラー ({title_prefix}): {e}")
        return None
    finally:
        gc.collect()

# ===========================================
# 部門別テーブル生成関数（最適化版）
# ===========================================
def create_department_tables(chart_data, latest_date, target_data=None, filter_code=None, para_style=None):
    """部門別テーブル生成（最適化版）"""
    dept_tbl_start_time = time.time()
    
    if chart_data is None or chart_data.empty or latest_date is None:
        return [], [], []

    # データコピーを作成して除外病棟をフィルタリング
    chart_data_filtered = chart_data.copy()
    if '病棟コード' in chart_data_filtered.columns and EXCLUDED_WARDS:
        original_count = len(chart_data_filtered)
        chart_data_filtered = chart_data_filtered[~chart_data_filtered['病棟コード'].isin(EXCLUDED_WARDS)]
        removed_count = original_count - len(chart_data_filtered)
        if removed_count > 0:
            logger.debug(f"部門別テーブル: 除外病棟フィルタリングで{removed_count}件のレコードを除外")
    
    # 日付処理の最適化
    if not pd.api.types.is_datetime64_any_dtype(chart_data_filtered['日付']):
        try: 
            chart_data_filtered['日付'] = pd.to_datetime(chart_data_filtered['日付'])
        except Exception: 
            return [], [], []
    
    if not isinstance(latest_date, pd.Timestamp): 
        latest_date = pd.Timestamp(latest_date)

    # 期間定義の最適化
    current_year_start_month = 4
    if latest_date.month < current_year_start_month:
        current_fiscal_year_start = pd.Timestamp(year=latest_date.year - 1, month=current_year_start_month, day=1)
    else:
        current_fiscal_year_start = pd.Timestamp(year=latest_date.year, month=current_year_start_month, day=1)
    
    current_fiscal_year_end_for_data = latest_date
    previous_fiscal_year_start = current_fiscal_year_start - pd.DateOffset(years=1)
    previous_fiscal_year_end = current_fiscal_year_start - pd.Timedelta(days=1)

    period_definitions = {
        "直近7日": (latest_date - pd.Timedelta(days=6), latest_date),
        "直近14日": (latest_date - pd.Timedelta(days=13), latest_date),
        "直近30日": (latest_date - pd.Timedelta(days=29), latest_date),
        "直近60日": (latest_date - pd.Timedelta(days=59), latest_date),
        f"{current_fiscal_year_start.year}年度": (current_fiscal_year_start, current_fiscal_year_end_for_data),
        f"{previous_fiscal_year_start.year}年度": (previous_fiscal_year_start, previous_fiscal_year_end),
    }
    
    period_labels_for_data = list(period_definitions.keys())
    period_name_for_achievement = "直近30日"
    
    # パラグラフスタイルの設定
    if para_style is None:
        styles = getSampleStyleSheet()
        font_name_to_use = REPORTLAB_FONT_NAME if REPORTLAB_FONT_NAME else 'Helvetica'
        para_style = ParagraphStyle(
            'ParaNormalCenterDefault_Dept', 
            parent=styles['Normal'], 
            fontName=font_name_to_use, 
            fontSize=7, 
            alignment=TA_CENTER, 
            leading=8
        )

    # ヘッダーラベルの最適化
    period_labels_for_header = []
    for label in period_labels_for_data:
        formatted_label = label.replace("直近", "直近<br/>").replace("年度", "<br/>年度")
        period_labels_for_header.append(Paragraph(formatted_label, para_style))

    # ユニークな病棟・診療科の取得（除外病棟適用済み）
    ward_codes_unique = []
    if "病棟コード" in chart_data_filtered.columns:
        ward_codes_unique = sorted(chart_data_filtered["病棟コード"].astype(str).unique())
        # 除外病棟を再度フィルタリング（念のため）
        if EXCLUDED_WARDS:
            ward_codes_unique = [ward for ward in ward_codes_unique if ward not in EXCLUDED_WARDS]
    
    dept_names_to_process = []
    if "診療科名" in chart_data_filtered.columns:
        dept_names_to_process = sorted(chart_data_filtered["診療科名"].unique())
    
    # 表示名マッピングの最適化
    ward_display_names = {}
    for ward_code in ward_codes_unique:
        if target_data is not None and not target_data.empty and '部門コード' in target_data.columns and '部門名' in target_data.columns:
            target_row = target_data[target_data['部門コード'].astype(str) == ward_code]
            if not target_row.empty and pd.notna(target_row['部門名'].iloc[0]):
                ward_display_names[ward_code] = target_row['部門名'].iloc[0]
                continue
        
        # デフォルトの表示名生成
        match = re.match(r'0*(\d+)([A-Za-z]*)', ward_code)
        if match:
            ward_display_names[ward_code] = f"{match.group(1)}{match.group(2)}病棟"
        else:
            ward_display_names[ward_code] = ward_code

    # メトリクス計算の最適化
    ward_metrics = {ward_code: {} for ward_code in ward_codes_unique}
    dept_metrics = {dept_name: {} for dept_name in dept_names_to_process}

    for period_label, (start_dt_period, end_dt_period) in period_definitions.items():
        if start_dt_period > end_dt_period:
            continue
            
        period_data_df = chart_data_filtered[
            (chart_data_filtered["日付"] >= start_dt_period) & 
            (chart_data_filtered["日付"] <= end_dt_period)
        ]
        
        if period_data_df.empty:
            continue
            
        num_days_in_period_calc = period_data_df['日付'].nunique()
        if num_days_in_period_calc == 0:
            continue
            
        # 病棟別メトリクス計算
        for ward_code in ward_codes_unique:
            ward_data_df = period_data_df[period_data_df["病棟コード"].astype(str) == ward_code]
            if not ward_data_df.empty and '入院患者数（在院）' in ward_data_df.columns:
                total_patient_days_val = ward_data_df.groupby('日付')['入院患者数（在院）'].sum().sum()
                avg_daily_census_val = total_patient_days_val / num_days_in_period_calc if num_days_in_period_calc > 0 else np.nan
                ward_metrics[ward_code][period_label] = avg_daily_census_val
            else:
                ward_metrics[ward_code][period_label] = np.nan

        # 診療科別メトリクス計算
        for dept_name in dept_names_to_process:
            dept_data_df = period_data_df[period_data_df["診療科名"] == dept_name]
            if not dept_data_df.empty and '入院患者数（在院）' in dept_data_df.columns:
                total_patient_days_val = dept_data_df.groupby('日付')['入院患者数（在院）'].sum().sum()
                avg_daily_census_val = total_patient_days_val / num_days_in_period_calc if num_days_in_period_calc > 0 else np.nan
                dept_metrics[dept_name][period_label] = avg_daily_census_val
            else:
                dept_metrics[dept_name][period_label] = np.nan
    
    # 目標値・達成率計算の最適化
    target_dict_cache_local = {}
    
    def get_targets_achievements(items, metrics_dict, target_data_df, achievement_period=period_name_for_achievement):
        targets = {}
        achievements = {}
        
        if target_data_df is not None and not target_data_df.empty:
            required_cols = ['部門コード', '区分', '目標値']
            if all(col in target_data_df.columns for col in required_cols):
                target_data_df['部門コード'] = target_data_df['部門コード'].astype(str)
                
                if 'all_targets' not in target_dict_cache_local:
                    all_targets_map_local = {}
                    for _, row in target_data_df[target_data_df['区分'] == '全日'].iterrows():
                        if pd.notna(row.get('部門コード')) and pd.notna(row.get('目標値')):
                            all_targets_map_local[str(row['部門コード'])] = float(row['目標値'])
                    target_dict_cache_local['all_targets'] = all_targets_map_local
                
                all_targets_map_local = target_dict_cache_local.get('all_targets', {})
                
                for item_id_val in items:
                    item_id_str_val = str(item_id_val)
                    target_value_val = all_targets_map_local.get(item_id_str_val)
                    
                    if target_value_val is not None:
                        targets[item_id_val] = target_value_val
                        actual_value_val = metrics_dict.get(item_id_val, {}).get(achievement_period)
                        
                        if actual_value_val is not None and pd.notna(actual_value_val) and target_value_val > 0:
                            achievements[item_id_val] = (actual_value_val / target_value_val) * 100
        
        return targets, achievements

    ward_targets, ward_achievements = get_targets_achievements(ward_codes_unique, ward_metrics, target_data)
    dept_targets, dept_achievements = get_targets_achievements(dept_names_to_process, dept_metrics, target_data)
    
    # ソート関数の最適化
    def sort_entities(entities_list, achievements_ref_dict, targets_ref_dict):
        entities_list_str = [str(e) for e in entities_list]
        achievements_ref_str = {str(k): v for k, v in achievements_ref_dict.items()}
        targets_ref_str = {str(k): v for k, v in targets_ref_dict.items()}
        
        sorted_by_achievement = sorted(
            [e for e in entities_list_str if e in achievements_ref_str], 
            key=lambda x: achievements_ref_str.get(x, 0), 
            reverse=True
        )
        sorted_by_target_only = sorted([e for e in entities_list_str if e in targets_ref_str and e not in achievements_ref_str])
        sorted_by_no_target = sorted([e for e in entities_list_str if e not in targets_ref_str])
        
        return sorted_by_achievement + sorted_by_target_only + sorted_by_no_target

    sorted_ward_codes = sort_entities(ward_codes_unique, ward_achievements, ward_targets)
    sorted_dept_names = sort_entities(dept_names_to_process, dept_achievements, dept_targets)
    
    # テーブルデータ生成の最適化
    header_items = [Paragraph("部門", para_style)] + period_labels_for_header + \
                   [Paragraph("目標値", para_style), Paragraph("達成率<br/>(%)", para_style)]
    
    # 病棟テーブルデータ
    ward_table_data = [header_items]
    for ward_code_str in sorted_ward_codes:
        row_items = [Paragraph(ward_display_names.get(ward_code_str, ward_code_str), para_style)]
        
        for period_label_val in period_labels_for_data:
            val = ward_metrics.get(ward_code_str, {}).get(period_label_val)
            row_items.append(f"{val:.1f}" if pd.notna(val) else "-")
        
        row_items.append(f"{ward_targets.get(ward_code_str):.1f}" if ward_code_str in ward_targets else "-")
        row_items.append(f"{ward_achievements.get(ward_code_str):.1f}" if ward_code_str in ward_achievements else "-")
        ward_table_data.append(row_items)
    
    # 診療科テーブルデータ
    dept_table_data = [header_items]
    for dept_name_str in sorted_dept_names:
        row_items = [Paragraph(str(dept_name_str), para_style)]
        
        for period_label_val in period_labels_for_data:
            val = dept_metrics.get(dept_name_str, {}).get(period_label_val)
            row_items.append(f"{val:.1f}" if pd.notna(val) else "-")
        
        row_items.append(f"{dept_targets.get(dept_name_str):.1f}" if dept_name_str in dept_targets else "-")
        row_items.append(f"{dept_achievements.get(dept_name_str):.1f}" if dept_name_str in dept_achievements else "-")
        dept_table_data.append(row_items)
    
    # 処理時間ログ
    dept_tbl_end_time = time.time()
    if dept_tbl_end_time - dept_tbl_start_time > 3.0:
        logger.warning(f"Department tables generation took {dept_tbl_end_time - dept_tbl_start_time:.2f}s")
    
    return ward_table_data, dept_table_data, period_labels_for_data