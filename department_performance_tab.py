# department_performance_tab.py - 診療科別パフォーマンスダッシュボード（努力度表示版・トレンド分析対応）

import streamlit as st
import pandas as pd
import logging
from datetime import datetime
import calendar
from config import EXCLUDED_WARDS

logger = logging.getLogger(__name__)

# 既存のインポートに加えて詳細表示機能を追加
try:
    from utils import safe_date_filter, get_display_name_for_dept, create_dept_mapping_table
    from unified_filters import get_unified_filter_config
    from html_export_functions import (
        generate_metrics_html, generate_action_html, 
        generate_combined_html_with_tabs, validate_export_data, 
        get_export_filename
    )
    from unified_html_export import generate_unified_html_export
    from enhanced_streamlit_display import display_enhanced_action_dashboard
    from enhanced_action_analysis import generate_comprehensive_action_data
except ImportError as e:
    st.error(f"必要なモジュールのインポートに失敗しました: {e}")
    st.stop()

def get_hospital_targets(target_data):
    """病院全体の平日目標値を取得"""
    targets = {'daily_census': 580, 'daily_admissions': 80}
    if target_data is None or target_data.empty: 
        return targets
    try:
        hospital_data = target_data[(target_data['部門コード'] == '全体') & (target_data['期間区分'] == '平日')]
        for _, row in hospital_data.iterrows():
            if str(row.get('指標タイプ', '')).strip() == '日平均在院患者数' and row.get('目標値'):
                targets['daily_census'] = row['目標値']
    except Exception as e:
        logger.error(f"病院全体目標値取得エラー: {e}")
    return targets

def calculate_los_appropriate_range(dept_df, start_date, end_date):
    """統計的アプローチで在院日数適正範囲を計算"""
    if dept_df.empty or '平均在院日数' not in dept_df.columns: 
        return None
    try:
        period_df = safe_date_filter(dept_df, start_date, end_date)
        los_data = []
        for _, row in period_df.iterrows():
            if pd.notna(row.get('退院患者数', 0)) and row.get('退院患者数', 0) > 0:
                patient_days, discharges = row.get('在院患者数', 0), row.get('退院患者数', 0)
                if discharges > 0:
                    daily_los = patient_days / discharges if patient_days > 0 else 0
                    if daily_los > 0: 
                        los_data.extend([daily_los] * int(discharges))
        if len(los_data) < 5: 
            return None
        mean_los, std_los = pd.Series(los_data).mean(), pd.Series(los_data).std()
        range_value = max(std_los, 0.3)
        return {"upper": mean_los + range_value, "lower": max(0.1, mean_los - range_value)}
    except Exception as e:
        logger.error(f"在院日数適正範囲計算エラー: {e}")
        return None

def evaluate_feasibility(kpi_data, dept_df, start_date, end_date):
    """実現可能性を評価"""
    try:
        admission_feasible = {
            "病床余裕": kpi_data.get('daily_census_achievement', 0) < 90,
            "トレンド安定": kpi_data.get('recent_week_admissions', 0) >= kpi_data.get('weekly_avg_admissions', 0) * 0.95
        }
        
        los_range = calculate_los_appropriate_range(dept_df, start_date, end_date)
        recent_los = kpi_data.get('recent_week_avg_los', 0)
        avg_los = kpi_data.get('avg_length_of_stay', 0)
        
        los_feasible = {
            "調整余地": abs(recent_los - avg_los) > avg_los * 0.03 if avg_los > 0 else False,
            "適正範囲内": bool(
                los_range and 
                los_range["lower"] <= recent_los <= los_range["upper"]
            ) if recent_los > 0 else False
        }
        
        return {
            "admission": admission_feasible,
            "los": los_feasible,
            "los_range": los_range
        }
        
    except Exception as e:
        logger.error(f"実現可能性評価エラー: {e}")
        return {"admission": {}, "los": {}, "los_range": None}

def calculate_effect_simulation(kpi_data):
    """効果シミュレーション計算（簡素化版に対応）"""
    try:
        current_census, target_census = kpi_data.get('daily_avg_census', 0), kpi_data.get('daily_census_target', 0)
        current_admissions, current_los = kpi_data.get('weekly_avg_admissions', 0) / 7, kpi_data.get('avg_length_of_stay', 0)
        if not all([target_census, current_admissions, current_los]) or (target_census - current_census) <= 0: 
            return None
        gap = target_census - current_census
        needed_admissions_increase = gap / current_los if current_los > 0 else 0
        needed_los_increase = (target_census / current_admissions) - current_los if current_admissions > 0 else 0
        return {
            "gap": gap,
            "admission_plan": {"increase": needed_admissions_increase, "effect": needed_admissions_increase * current_los},
            "los_plan": {"increase": needed_los_increase, "effect": current_admissions * needed_los_increase}
        }
    except Exception as e:
        logger.error(f"効果シミュレーション計算エラー: {e}")
        return None

def decide_action_and_reasoning(kpi_data, feasibility, simulation):
    """アクション判断とその根拠"""
    census_achievement = kpi_data.get('daily_census_achievement', 100)
    if census_achievement >= 95: 
        return {"action": "現状維持", "reasoning": "目標をほぼ達成しており、良好な状況を継続", "priority": "low", "color": "#7fb069"}
    if census_achievement < 85: 
        return {"action": "両方検討", "reasoning": "大幅な不足のため、新入院増加と在院日数適正化の両面からアプローチが必要", "priority": "urgent", "color": "#e08283"}
    admission_score, los_score = sum(feasibility["admission"].values()), sum(feasibility["los"].values())
    if admission_score >= 1 and los_score >= 1 and simulation and abs(simulation["admission_plan"]["increase"]) <= abs(simulation["los_plan"]["increase"]):
        return {"action": "新入院重視", "reasoning": "病床余裕があり、新入院増加がより実現可能", "priority": "medium", "color": "#f5d76e"}
    if admission_score >= 1: 
        return {"action": "新入院重視", "reasoning": "病床に余裕があり、新入院増加が効果的", "priority": "medium", "color": "#f5d76e"}
    if los_score >= 1: 
        return {"action": "在院日数調整", "reasoning": "在院日数に調整余地があり効果的", "priority": "medium", "color": "#f5d76e"}
    return {"action": "経過観察", "reasoning": "現状では大きな変更は困難、トレンド注視が必要", "priority": "low", "color": "#b3b9b3"}

def get_period_dates(df, period_type):
    """期間タイプに基づいて開始日と終了日を計算"""
    if df is None or df.empty or '日付' not in df.columns:
        return None, None, "データなし"
    
    max_date = df['日付'].max()
    min_date = df['日付'].min()
    
    if period_type == "直近4週間":
        start_date = max_date - pd.Timedelta(days=27)
        desc = f"直近4週間 ({start_date.strftime('%m/%d')}～{max_date.strftime('%m/%d')})"
    elif period_type == "直近8週":
        start_date = max_date - pd.Timedelta(days=55)
        desc = f"直近8週間 ({start_date.strftime('%m/%d')}～{max_date.strftime('%m/%d')})"
    elif period_type == "直近12週":
        start_date = max_date - pd.Timedelta(days=83)
        desc = f"直近12週間 ({start_date.strftime('%m/%d')}～{max_date.strftime('%m/%d')})"
    elif period_type == "今年度":
        year = max_date.year if max_date.month >= 4 else max_date.year - 1
        start_date = pd.Timestamp(year=year, month=4, day=1)
        end_of_fiscal = pd.Timestamp(year=year+1, month=3, day=31)
        end_date = min(end_of_fiscal, max_date)
        desc = f"今年度 ({start_date.strftime('%Y/%m/%d')}～{end_date.strftime('%m/%d')})"
        return max(start_date, min_date), end_date, desc
    elif period_type == "先月":
        if max_date.month == 1:
            year = max_date.year - 1
            month = 12
        else:
            year = max_date.year
            month = max_date.month - 1
        start_date = pd.Timestamp(year=year, month=month, day=1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = pd.Timestamp(year=year, month=month, day=last_day)
        if end_date > max_date:
            end_date = max_date
        if start_date < min_date:
            start_date = min_date
        desc = f"{year}年{month}月 ({start_date.strftime('%m/%d')}～{end_date.strftime('%m/%d')})"
        return start_date, end_date, desc
    elif period_type == "昨年度":
        current_year = max_date.year if max_date.month >= 4 else max_date.year - 1
        prev_year = current_year - 1
        start_date = pd.Timestamp(year=prev_year, month=4, day=1)
        end_date = pd.Timestamp(year=current_year, month=3, day=31)
        if end_date > max_date:
            end_date = max_date
        if start_date < min_date:
            start_date = min_date
        desc = f"{prev_year}年度 ({start_date.strftime('%Y/%m/%d')}～{end_date.strftime('%Y/%m/%d')})"
        return start_date, end_date, desc
    else:
        start_date = max_date - pd.Timedelta(days=27)
        desc = f"直近4週間 ({start_date.strftime('%m/%d')}～{max_date.strftime('%m/%d')})"
    
    start_date = max(start_date, min_date)
    return start_date, max_date, desc

def get_target_values_for_dept(target_data, dept_code, dept_name=None):
    """部門コードまたは部門名で目標値を取得"""
    targets = {
        'daily_census_target': None,
        'weekly_admissions_target': None,
        'avg_los_target': None,
        'display_name': dept_code
    }
    
    if target_data is None or target_data.empty:
        return targets
    
    try:
        dept_targets = target_data[target_data['部門コード'] == dept_code]
        
        if dept_targets.empty and '部門名' in target_data.columns:
            dept_targets = target_data[
                (target_data['部門名'] == dept_code) | 
                (target_data['部門名'] == dept_name) |
                (target_data['部門名'].str.contains(dept_code, na=False)) |
                (target_data['部門名'].str.contains(dept_name, na=False) if dept_name else False)
            ]
        
        if not dept_targets.empty:
            if '部門名' in dept_targets.columns:
                display_name = dept_targets.iloc[0]['部門名']
                targets['display_name'] = display_name
            
            for _, row in dept_targets.iterrows():
                indicator_type = str(row.get('指標タイプ', '')).strip()
                target_value = row.get('目標値', None)
                
                if indicator_type == '日平均在院患者数':
                    targets['daily_census_target'] = target_value
                elif indicator_type == '週間新入院患者数':
                    targets['weekly_admissions_target'] = target_value
                elif indicator_type == '平均在院日数':
                    targets['avg_los_target'] = target_value
        else:
            logger.warning(f"目標値が見つかりません - 部門コード: {dept_code}, 診療科名: {dept_name}")
            
    except Exception as e:
        logger.error(f"目標値取得エラー ({dept_code}): {e}")
    
    return targets

def calculate_department_kpis(df, target_data, dept_code, dept_name, start_date, end_date, dept_col):
    """診療科別KPI計算"""
    try:
        dept_df = df[df[dept_col] == dept_code]
        period_df = safe_date_filter(dept_df, start_date, end_date)
        
        if period_df.empty:
            return None
        
        total_days = (end_date - start_date).days + 1
        total_patient_days = period_df['在院患者数'].sum() if '在院患者数' in period_df.columns else 0
        total_admissions = period_df['新入院患者数'].sum() if '新入院患者数' in period_df.columns else 0
        total_discharges = period_df['退院患者数'].sum() if '退院患者数' in period_df.columns else 0
        
        daily_avg_census = total_patient_days / total_days if total_days > 0 else 0
        
        # 直近週の計算
        recent_week_end = end_date
        recent_week_start = end_date - pd.Timedelta(days=6)
        recent_week_df = safe_date_filter(dept_df, recent_week_start, recent_week_end)
        recent_week_patient_days = recent_week_df['在院患者数'].sum() if '在院患者数' in recent_week_df.columns and not recent_week_df.empty else 0
        recent_week_admissions = recent_week_df['新入院患者数'].sum() if '新入院患者数' in recent_week_df.columns and not recent_week_df.empty else 0
        recent_week_discharges = recent_week_df['退院患者数'].sum() if '退院患者数' in recent_week_df.columns and not recent_week_df.empty else 0
        recent_week_daily_census = recent_week_patient_days / 7 if recent_week_patient_days > 0 else 0
        
        avg_length_of_stay = total_patient_days / total_discharges if total_discharges > 0 else 0
        recent_week_avg_los = recent_week_patient_days / recent_week_discharges if recent_week_discharges > 0 else 0
        weekly_avg_admissions = (total_admissions / total_days) * 7 if total_days > 0 else 0
        
        # 目標値の取得
        targets = get_target_values_for_dept(target_data, dept_code, dept_name)
        
        # 達成率の計算
        daily_census_achievement = (daily_avg_census / targets['daily_census_target'] * 100) if targets['daily_census_target'] else 0
        weekly_admissions_achievement = (weekly_avg_admissions / targets['weekly_admissions_target'] * 100) if targets['weekly_admissions_target'] else 0
        los_achievement = (targets['avg_los_target'] / avg_length_of_stay * 100) if targets['avg_los_target'] and avg_length_of_stay else 0
        
        return {
            'dept_code': dept_code,
            'dept_name': targets['display_name'],
            'daily_avg_census': daily_avg_census,
            'recent_week_daily_census': recent_week_daily_census,
            'daily_census_target': targets['daily_census_target'],
            'daily_census_achievement': daily_census_achievement,
            'weekly_avg_admissions': weekly_avg_admissions,
            'recent_week_admissions': recent_week_admissions,
            'weekly_admissions_target': targets['weekly_admissions_target'],
            'weekly_admissions_achievement': weekly_admissions_achievement,
            'avg_length_of_stay': avg_length_of_stay,
            'recent_week_avg_los': recent_week_avg_los,
            'avg_los_target': targets['avg_los_target'],
            'avg_los_achievement': los_achievement
        }
    except Exception as e:
        logger.error(f"KPI計算エラー ({dept_code}): {e}", exc_info=True)
        return None

def get_color(val):
    """達成率に応じた色を取得"""
    if val >= 100:
        return "#7fb069"  # パステルグリーン
    elif val >= 80:
        return "#f5d76e"  # パステルイエロー
    else:
        return "#e08283"  # パステルレッド

def render_metric_card(label, period_avg, recent, target, achievement, unit, card_color):
    """メトリックカードのHTML生成"""
    ach_str = f"{achievement:.1f}%" if achievement or achievement == 0 else "--"
    ach_label = "達成率:"
    target_color = "#b3b9b3" if not target or target == '--' else "#7b8a7a"
    return f"""
    <div style="
        background: {card_color}0E;
        border-radius: 11px;
        border-left: 6px solid {card_color};
        margin-bottom: 12px;
        padding: 12px 16px 7px 16px;
        min-height: 1px;
        ">
        <div style="font-size:1.13em; font-weight:700; margin-bottom:7px; color:#293a27;">{label}</div>
        <div style="display:flex; flex-direction:column; gap:2px;">
            <div style="display:flex; justify-content:space-between;">
                <span style="font-size:0.93em; color:#7b8a7a;">期間平均:</span>
                <span style="font-size:1.07em; font-weight:700; color:#2e3532;">{period_avg} {unit}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="font-size:0.93em; color:#7b8a7a;">直近週実績:</span>
                <span style="font-size:1.07em; font-weight:700; color:#2e3532;">{recent} {unit}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="font-size:0.93em; color:#7b8a7a;">目標:</span>
                <span style="font-size:1.07em; font-weight:700; color:{target_color};">{target if target else '--'} {unit}</span>
            </div>
        </div>
        <div style="margin-top:7px; display:flex; justify-content:space-between; align-items:center;">
          <div style="font-weight:700; font-size:1.03em; color:{card_color};">{ach_label}</div>
          <div style="font-weight:700; font-size:1.20em; color:{card_color};">{ach_str}</div>
        </div>
    </div>
    """

def render_los_trend_card(label, period_avg, recent, unit, dept_df, start_date, end_date):
    """在院日数トレンド分析カードのHTML生成"""
    try:
        # トレンド計算
        if period_avg > 0:
            change_rate = ((recent - period_avg) / period_avg) * 100
            change_days = recent - period_avg
        else:
            change_rate = 0
            change_days = 0
        
        # トレンド評価
        if abs(change_rate) < 3:  # 3%未満は安定
            trend_icon = "🟡"
            trend_text = "安定"
            trend_color = "#FFC107"
        elif change_rate > 0:  # 延長傾向
            trend_icon = "🔴"
            trend_text = "延長傾向"
            trend_color = "#F44336"
        else:  # 短縮傾向
            trend_icon = "🟢"
            trend_text = "短縮傾向"
            trend_color = "#4CAF50"
        
        # 適正範囲チェック（統計的評価）
        los_range = calculate_los_appropriate_range(dept_df, start_date, end_date)
        range_status = ""
        range_color = "#999"
        if los_range and recent > 0:
            if los_range["lower"] <= recent <= los_range["upper"]:
                range_status = "✅ 適正範囲内"
                range_color = "#4CAF50"
            else:
                range_status = "⚠️ 要確認"
                range_color = "#FF9800"
        
        # 適正範囲表示文字列
        range_display = ""
        if los_range:
            range_display = f'<div style="margin-top:4px; font-size:0.8em; color:#666;">適正範囲: {los_range["lower"]:.1f}-{los_range["upper"]:.1f}日</div>'
        
        return f"""
        <div style="background: {trend_color}0E; border-radius: 11px; border-left: 6px solid {trend_color}; margin-bottom: 12px; padding: 12px 16px 7px 16px;">
            <div style="font-size:1.13em; font-weight:700; margin-bottom:7px; color:#293a27;">{label}</div>
            <div style="display:flex; flex-direction:column; gap:2px;">
                <div style="display:flex; justify-content:space-between;">
                    <span style="font-size:0.93em; color:#7b8a7a;">期間平均:</span>
                    <span style="font-size:1.07em; font-weight:700;">{period_avg:.1f} {unit}</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="font-size:0.93em; color:#7b8a7a;">直近週実績:</span>
                    <span style="font-size:1.07em; font-weight:700;">{recent:.1f} {unit}</span>
                </div>
                <div style="display:flex; justify-content:space-between;">
                    <span style="font-size:0.93em; color:#7b8a7a;">変化:</span>
                    <span style="font-size:1.07em; font-weight:700;">{change_days:+.1f} {unit} ({change_rate:+.1f}%)</span>
                </div>
            </div>
            <div style="margin-top:7px; display:flex; justify-content:space-between; align-items:center;">
              <div style="font-weight:700; font-size:1.03em; color:{trend_color};">{trend_icon} {trend_text}</div>
              <div style="font-size:0.9em; color:{range_color};">{range_status}</div>
            </div>
            {range_display}
        </div>"""
        
    except Exception as e:
        logger.error(f"在院日数トレンドカード生成エラー: {e}")
        return f"""
        <div style="background: #f0f0f0; border-radius: 11px; border-left: 6px solid #999; margin-bottom: 12px; padding: 12px 16px 7px 16px;">
            <div style="font-size:1.13em; font-weight:700; margin-bottom:7px; color:#293a27;">{label}</div>
            <div style="color: #666;">トレンド分析でエラーが発生しました</div>
        </div>"""

def display_metrics_dashboard(selected_metric, df_original, target_data, selected_period):
    """3指標表示ダッシュボード（トレンド分析対応版）"""
    try:
        start_date, end_date, period_desc = get_period_dates(df_original, selected_period)
        if start_date is None or end_date is None:
            st.error("期間の計算に失敗しました。")
            return
        
        date_filtered_df = safe_date_filter(df_original, start_date, end_date)
        if '病棟コード' in date_filtered_df.columns and EXCLUDED_WARDS:
            date_filtered_df = date_filtered_df[~date_filtered_df['病棟コード'].isin(EXCLUDED_WARDS)]
        if date_filtered_df.empty:
            st.warning(f"選択された期間（{period_desc}）にデータがありません。")
            return
        
        possible_cols = ['部門名', '診療科', '診療科名']
        dept_col = next((c for c in possible_cols if c in date_filtered_df.columns), None)
        if dept_col is None:
            st.error(f"診療科列が見つかりません。")
            return

        unique_depts = date_filtered_df[dept_col].unique()
        dept_kpis = []
        for dept_code in unique_depts:
            kpi = calculate_department_kpis(date_filtered_df, target_data, dept_code, dept_code, start_date, end_date, dept_col)
            if kpi: 
                dept_kpis.append(kpi)
        
        if not dept_kpis:
            st.warning("表示可能な診療科データがありません。")
            return

        # 平均在院日数（トレンド分析）の場合は特別処理
        if selected_metric == "平均在院日数（トレンド分析）":
            st.markdown(f"### 📈 **{period_desc}** の診療科別トレンド分析（平均在院日数）")
            
            # トレンド評価でソート（延長→安定→短縮の順）
            def get_trend_sort_key(kpi):
                period_avg = kpi.get('avg_length_of_stay', 0)
                recent = kpi.get('recent_week_avg_los', 0)
                if period_avg > 0:
                    change_rate = ((recent - period_avg) / period_avg) * 100
                    if change_rate > 3:
                        return 0  # 延長傾向（要注意）
                    elif change_rate < -3:
                        return 2  # 短縮傾向（良好）
                    else:
                        return 1  # 安定
                return 1  # デフォルト（安定扱い）
            
            dept_kpis.sort(key=get_trend_sort_key)
            
            n_cols = 3 if len(dept_kpis) <= 6 else 4 if len(dept_kpis) <= 12 else 5
            cols = st.columns(n_cols)
            
            for idx, kpi in enumerate(dept_kpis):
                dept_df = date_filtered_df[date_filtered_df[dept_col] == kpi['dept_code']]
                html = render_los_trend_card(
                    kpi["dept_name"], 
                    kpi.get('avg_length_of_stay', 0),
                    kpi.get('recent_week_avg_los', 0), 
                    "日",
                    dept_df,
                    start_date,
                    end_date
                )
                with cols[idx % n_cols]:
                    st.markdown(html, unsafe_allow_html=True)
                    
        else:
            # 従来の指標表示
            metric_opts = {
                "日平均在院患者数": {"avg": "daily_avg_census", "recent": "recent_week_daily_census", "target": "daily_census_target", "ach": "daily_census_achievement", "unit": "人"},
                "週合計新入院患者数": {"avg": "weekly_avg_admissions", "recent": "recent_week_admissions", "target": "weekly_admissions_target", "ach": "weekly_admissions_achievement", "unit": "件"}
            }
            opt = metric_opts.get(selected_metric, metric_opts["日平均在院患者数"])
            rev = True  # 両方とも降順
            dept_kpis.sort(key=lambda x: x.get(opt["ach"], 0), reverse=rev)

            st.markdown(f"### 📈 **{period_desc}** の診療科別パフォーマンス（{selected_metric}）")
            
            n_cols = 3 if len(dept_kpis) <= 6 else 4 if len(dept_kpis) <= 12 else 5
            cols = st.columns(n_cols)
            
            for idx, kpi in enumerate(dept_kpis):
                avg_disp = f"{kpi.get(opt['avg'], 0):.1f}" if kpi.get(opt['avg']) is not None else "--"
                recent_disp = f"{kpi.get(opt['recent'], 0):.1f}" if kpi.get(opt['recent']) is not None else "--"
                target_disp = f"{kpi.get(opt['target']):.1f}" if kpi.get(opt['target']) is not None else "--"
                html = render_metric_card(kpi["dept_name"], avg_disp, recent_disp, target_disp, kpi.get(opt["ach"], 0), opt["unit"], get_color(kpi.get(opt["ach"], 0)))
                with cols[idx % n_cols]:
                    st.markdown(html, unsafe_allow_html=True)
        
        return dept_kpis, start_date, end_date, period_desc
    
    except Exception as e:
        logger.error(f"メトリクス表示エラー: {e}", exc_info=True)
        st.error(f"メトリクス表示中にエラーが発生しました: {str(e)}")
        return None, None, None, None

def display_action_dashboard_with_detail_option(df_original, target_data, selected_period):
    """
    アクション提案ダッシュボード（詳細表示オプション付き・努力度表示版・影響度順ソート対応）
    """
    try:
        # 表示モード選択
        st.markdown("#### 🎯 アクション提案表示設定")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            display_mode = st.radio(
                "表示モード",
                ["詳細表示（目標達成努力度版）", "簡易表示（従来版）"],
                index=0,
                horizontal=True,
                help="詳細表示では、目標達成努力度と簡素化された効果シミュレーションを表示します"
            )
        
        with col2:
            if st.button("🔄 更新", key="refresh_action_dashboard"):
                st.rerun()
        
        # 選択されたモードに応じて表示
        if display_mode == "詳細表示（目標達成努力度版）":
            return display_enhanced_action_dashboard(df_original, target_data, selected_period)
        else:
            return display_simple_action_dashboard(df_original, target_data, selected_period)
            
    except Exception as e:
        logger.error(f"アクション提案ダッシュボード表示エラー: {e}", exc_info=True)
        st.error(f"アクション提案ダッシュボードの表示中にエラーが発生しました: {str(e)}")
        return None

def display_simple_action_dashboard(df_original, target_data, selected_period):
    """
    従来の簡易アクション提案ダッシュボード（影響度順ソート対応）
    """
    try:
        if target_data is not None and not target_data.empty:
            create_dept_mapping_table(target_data)
        
        hospital_targets = get_hospital_targets(target_data)
        
        start_date, end_date, period_desc = get_period_dates(df_original, selected_period)
        if start_date is None or end_date is None:
            st.error("期間の計算に失敗しました。")
            return
        
        date_filtered_df = safe_date_filter(df_original, start_date, end_date)
        if '病棟コード' in date_filtered_df.columns and EXCLUDED_WARDS:
            date_filtered_df = date_filtered_df[~date_filtered_df['病棟コード'].isin(EXCLUDED_WARDS)]

        if date_filtered_df.empty:
            st.warning(f"選択された期間（{period_desc}）にデータがありません。")
            return
        
        possible_cols = ['部門名', '診療科', '診療科名']
        dept_col = next((c for c in possible_cols if c in date_filtered_df.columns), None)
        if dept_col is None:
            st.error(f"診療科列が見つかりません。期待する列: {possible_cols}")
            return

        total_census = date_filtered_df['在院患者数'].sum() / ((end_date - start_date).days + 1) if '在院患者数' in date_filtered_df.columns and not date_filtered_df.empty else 0
        hospital_census_ach = (total_census / hospital_targets['daily_census'] * 100) if hospital_targets['daily_census'] else 0
        
        st.markdown(f"### 🎯 病院全体目標達成状況（平日基準）- {period_desc}")
        col1, _ = st.columns(2)
        with col1:
            st.metric("日平均在院患者数", f"{total_census:.1f} 人", f"{total_census - hospital_targets['daily_census']:+.1f} 人 (目標: {hospital_targets['daily_census']:.0f}人)")

        st.markdown("### 🏥 診療科別アクション提案（目標差順）")
        
        unique_depts = date_filtered_df[dept_col].unique()
        action_results = []
        
        for dept_code in unique_depts:
            dept_name = dept_code
            kpi = calculate_department_kpis(date_filtered_df, target_data, dept_code, dept_name, start_date, end_date, dept_col)
            
            if kpi:
                dept_df = date_filtered_df[date_filtered_df[dept_col] == dept_code]
                feasibility = evaluate_feasibility(kpi, dept_df, start_date, end_date)
                simulation = calculate_effect_simulation(kpi)
                action_result = decide_action_and_reasoning(kpi, feasibility, simulation)
                action_results.append({'kpi': kpi, 'action_result': action_result, 'feasibility': feasibility, 'simulation': simulation})
        
        if not action_results:
            st.warning("表示可能な診療科データがありません。")
            return
        
        # ★★★ 3段階優先度ソート（要改善→目標達成→目標値なし）★★★
        def calculate_comprehensive_impact_score(x):
            """
            シンプルな影響度スコア計算（目標患者数 - 直近週実績値の順）
            
            優先度：目標患者数 - 直近週実績値が大きい順
            - プラスが大きい：目標未達成で差が大きい（最優先）
            - プラスが小さい：目標未達成で差が小さい
            - マイナス：目標達成済み（マイナスが大きいほど後回し）
            - 目標値なし：最後
            """
            kpi = x['kpi']
            target = kpi.get('daily_census_target', 0) or 0
            recent = kpi.get('recent_week_daily_census', 0) or 0
            
            if target <= 0:
                # 目標値なし：最後に表示
                return float('-inf')  # 非常に小さい値で最後に
            
            # 目標患者数 - 直近週実績値をそのまま返す
            gap = target - recent
            return gap  # 大きいほど上位
        
        def get_priority_label(kpi):
            """優先度ラベルを取得（シンプル版）"""
            target = kpi.get('daily_census_target', 0) or 0
            recent = kpi.get('recent_week_daily_census', 0) or 0
            
            if target <= 0:
                return "📊 目標値なし", "#9E9E9E"
            
            gap = target - recent
            if gap > 0:
                return f"🔴 目標まで{gap:.1f}人", "#F44336"
            else:
                return f"✅ 目標超過{abs(gap):.1f}人", "#4CAF50"
        
        action_results.sort(key=calculate_comprehensive_impact_score, reverse=True)
        
        n_cols = 3
        cols = st.columns(n_cols)
        for idx, result in enumerate(action_results):
            kpi = result['kpi']
            action_result = result['action_result']
            color = action_result.get('color', '#b3b9b3')
            action = action_result.get('action', '要確認')
            reasoning = action_result.get('reasoning', '')
            
            # 優先度ラベルを表示に追加
            priority_label, priority_color = get_priority_label(kpi)
            
            simple_card_html = f"""
            <div style="background: {color}0E; border-left: 6px solid {color}; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                <h4 style="color: #293a27; margin-bottom: 8px;">{kpi.get('dept_name', 'Unknown')}</h4>
                <div style="font-size: 0.9em; margin-bottom: 8px;"><strong>推奨アクション:</strong> {action}</div>
                <div style="font-size: 0.85em; color: #666;">{reasoning}</div>
                <div style="margin-top: 8px; font-size: 0.8em;">在院患者数: {kpi.get('daily_avg_census', 0):.1f}人 (達成率: {kpi.get('daily_census_achievement', 0):.1f}%)</div>
                <div style="margin-top: 4px; font-size: 0.85em; font-weight: 600; color: {priority_color};">{priority_label}</div>
            </div>"""
            with cols[idx % n_cols]:
                st.markdown(simple_card_html, unsafe_allow_html=True)
        
        return action_results, start_date, end_date, period_desc
    
    except Exception as e:
        logger.error(f"簡易アクション表示エラー: {e}", exc_info=True)
        st.error(f"簡易アクション表示中にエラーが発生しました: {str(e)}")
        return None, None, None, None

def generate_web_optimized_html(results_data, period_desc):
    """
    Web公開最適化HTMLの生成（努力度表示版）
    """
    try:
        # 1. 入力データの検証
        if not results_data or not results_data[0]:
            logger.warning("Web最適化HTML生成のために入力されたデータが空です。")
            st.error("HTML生成の元となるデータがありません。")
            return None

        action_results = results_data[0]
        if not isinstance(action_results, list) or not action_results:
            logger.warning("アクション結果リストが空または不正な形式です。")
            st.error("アクション結果のデータ形式が不正です。")
            return None

        # 2. データ形式の判定と変換
        # 'basic_info'キーの存在で新しい「詳細データ形式」かを判定
        if 'basic_info' in action_results[0]:
            logger.info("詳細データ形式を検出。標準形式に変換します。")
            standard_results = _convert_detailed_to_standard_format(action_results)
            if not standard_results:
                logger.error("詳細データから標準形式への変換に失敗しました。")
                st.error("データ形式の変換に失敗しました。")
                return None
        else:
            logger.info("標準データ形式を検出。変換は不要です。")
            standard_results = action_results

        # 3. 病院全体目標の取得
        target_data = st.session_state.get('target_data')
        hospital_targets = get_hospital_targets(target_data)

        # 4. 統一HTMLエクスポート関数を呼び出し（努力度表示版）
        logger.info(f"標準形式のデータ {len(standard_results)} 件で努力度表示HTMLを生成します。")
        html_content = generate_unified_html_export(
            standard_results, period_desc, hospital_targets, "department"
        )

        if not html_content or "エラー" in html_content:
            logger.error("generate_unified_html_export からのHTML生成に失敗しました。")
            st.error("HTMLコンテンツの基本部分の生成に失敗しました。")
            return None
        
        # 5. Web公開用の追加機能を注入
        try:
            from github_publisher import add_web_publish_features
            
            # publish_data のダミーを作成
            publish_data_dummy = {
                'content_type': '診療科別パフォーマンス（努力度表示版）',
                'period_desc': period_desc,
                'dashboard_type': 'department',
                'data_summary': {
                    'generated_at': datetime.now().isoformat(),
                    'start_date': '', 'end_date': '',
                    'total_records': 0, 'analysis_items': len(standard_results)
                }
            }
            web_optimized_html = add_web_publish_features(html_content, publish_data_dummy, False, True)

        except ImportError:
            # フォールバックとして元のHTMLを返す
            logger.warning("add_web_publish_features が見つかりません。基本的なHTMLを返します。")
            web_optimized_html = html_content
        
        logger.info("Web最適化HTML（努力度表示版）の生成が正常に完了しました。")
        return web_optimized_html

    except Exception as e:
        logger.error(f"Web最適化HTML生成中に致命的なエラーが発生: {e}", exc_info=True)
        st.error(f"HTML生成中に予期せぬエラーが発生しました: {e}")
        return None

def add_web_publish_optimizations(html_content):
    """Web公開用の最適化機能追加"""
    try:
        # Web公開最適化の追加機能
        optimization_features = """
        <!-- Web公開最適化機能 -->
        <script>
            // ページ読み込み最適化
            document.addEventListener('DOMContentLoaded', function() {
                // 遅延画像読み込み
                const images = document.querySelectorAll('img[data-src]');
                const imageObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            const img = entry.target;
                            img.src = img.dataset.src;
                            img.removeAttribute('data-src');
                            imageObserver.unobserve(img);
                        }
                    });
                });
                images.forEach(img => imageObserver.observe(img));
                
                // スムーススクロール
                document.querySelectorAll('a[href^="#"]').forEach(anchor => {
                    anchor.addEventListener('click', function (e) {
                        e.preventDefault();
                        const target = document.querySelector(this.getAttribute('href'));
                        if (target) {
                            target.scrollIntoView({ behavior: 'smooth' });
                        }
                    });
                });
                
                // キーボードナビゲーション対応
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') {
                        // フルスクリーンモード終了
                        if (document.fullscreenElement) {
                            document.exitFullscreen();
                        }
                    }
                });
            });
            
            // PWA機能
            if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('/sw.js')
                    .catch(err => console.log('Service Worker registration failed'));
            }
            
            // オフライン対応
            window.addEventListener('offline', function() {
                showOfflineNotification();
            });
            
            function showOfflineNotification() {
                const notification = document.createElement('div');
                notification.innerHTML = '📱 オフライン表示中';
                notification.style.cssText = `
                    position: fixed; bottom: 20px; left: 20px; z-index: 1001;
                    background: #ffc107; color: #000; padding: 10px 15px;
                    border-radius: 5px; font-size: 0.9em;
                `;
                document.body.appendChild(notification);
                setTimeout(() => document.body.removeChild(notification), 5000);
            }
        </script>
        
        <!-- SEO最適化 -->
        <meta name="robots" content="index, follow">
        <meta name="author" content="Hospital Management System">
        <link rel="canonical" href="">
        
        <!-- パフォーマンス最適化 -->
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="dns-prefetch" href="//github.com">
        """
        
        # HTMLに最適化機能を注入
        optimized_html = html_content.replace('</head>', f'{optimization_features}</head>')
        
        return optimized_html
        
    except Exception as e:
        logger.error(f"Web公開最適化追加エラー: {e}")
        return html_content

def display_html_export_section_enhanced(selected_tab, results_data, selected_period):
    """
    HTMLエクスポートセクション（Web公開機能統合版）
    既存関数の置き換え
    """
    return display_web_publish_section(selected_tab, results_data, selected_period)

# 追加のヘルパー関数群

def prepare_department_publish_data(results_data, period_desc, selected_period):
    """診療科別公開データの準備"""
    try:
        return {
            'results_data': results_data,
            'period_desc': period_desc,
            'selected_period': selected_period,
            'dashboard_type': 'department'
        }
    except Exception as e:
        logger.error(f"診療科別公開データ準備エラー: {e}")
        return None

def setup_department_auto_update(github_token, repo_name):
    """診療科別自動更新設定"""
    try:
        # 自動更新ワークフローの設定
        from github_publisher import setup_auto_update
        setup_auto_update(github_token, repo_name, "gh-pages")
        logger.info("診療科別自動更新を設定しました")
    except Exception as e:
        logger.error(f"診療科別自動更新設定エラー: {e}")

def save_department_publish_history(period_desc, publish_url):
    """診療科別公開履歴の保存"""
    try:
        if 'department_publish_history' not in st.session_state:
            st.session_state['department_publish_history'] = []
        
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'period_desc': period_desc,
            'url': publish_url,
            'dashboard_type': 'department'
        }
        
        st.session_state['department_publish_history'].append(history_entry)
        
        # 最新5件のみ保持
        if len(st.session_state['department_publish_history']) > 5:
            st.session_state['department_publish_history'] = st.session_state['department_publish_history'][-5:]
            
    except Exception as e:
        logger.error(f"診療科別公開履歴保存エラー: {e}")

def display_github_publish_history():
    """GitHub公開履歴の表示"""
    try:
        history = st.session_state.get('department_publish_history', [])
        
        if history:
            st.markdown("**📋 公開履歴**")
            for entry in reversed(history[-3:]):  # 最新3件
                timestamp = datetime.fromisoformat(entry['timestamp'])
                st.caption(f"• {timestamp.strftime('%m/%d %H:%M')} - {entry['period_desc']}")
                if entry.get('url'):
                    st.caption(f"  [📊 表示]({entry['url']})")
        else:
            st.caption("公開履歴がありません")
            
    except Exception as e:
        logger.error(f"公開履歴表示エラー: {e}")

def add_mobile_optimization(html_content):
    """モバイル最適化の追加"""
    try:
        mobile_css = """
        <style>
        /* 追加のモバイル最適化 */
        @media (max-width: 480px) {
            body { padding: 10px; }
            .action-card { padding: 12px; font-size: 0.9em; }
            h1 { font-size: 1.5em; }
            h3 { font-size: 1.1em; }
            .hospital-summary { gap: 10px; }
        }
        
        /* タッチ操作最適化 */
        .action-card:hover { transform: none; }
        .action-card:active { transform: scale(0.98); }
        button { min-height: 44px; }
        </style>
        """
        
        return html_content.replace('</head>', f'{mobile_css}</head>')
    except Exception as e:
        logger.error(f"モバイル最適化追加エラー: {e}")
        return html_content

def _convert_detailed_to_standard_format(detailed_results):
    """詳細データ形式を標準形式に変換する（堅牢版）"""
    try:
        standard_results = []
        for detailed_data in detailed_results:
            # 必要なキーの存在をチェック
            if 'basic_info' in detailed_data and 'basic_action' in detailed_data:
                basic_info = detailed_data.get('basic_info', {})
                action = detailed_data.get('basic_action', {})
                
                # 詳細データから標準形式のKPIデータを再構築
                kpi = {
                    'dept_name': basic_info.get('dept_name', '不明'),
                    'daily_avg_census': basic_info.get('current_census', 0),
                    'daily_census_target': basic_info.get('census_target'),
                    'daily_census_achievement': basic_info.get('census_achievement', 0),
                    'recent_week_daily_census': basic_info.get('recent_week_census', 0),
                    'weekly_avg_admissions': basic_info.get('admission_avg', 0) * 7,
                    'recent_week_admissions': basic_info.get('admission_recent', 0) * 7,
                    'weekly_admissions_target': basic_info.get('admission_target'),
                    'avg_length_of_stay': basic_info.get('los_avg', 0),
                    'recent_week_avg_los': basic_info.get('los_recent', 0),
                    'avg_los_target': basic_info.get('los_target')
                }
                
                standard_results.append({
                    'kpi': kpi,
                    'action_result': action,
                    'feasibility': detailed_data.get('feasibility_evaluation', {}),
                    'simulation': detailed_data.get('effect_simulation', {})
                })
        
        return standard_results
    except Exception as e:
        logger.error(f"詳細データ変換エラー: {e}", exc_info=True)
        return []

def display_web_publish_section(selected_tab, results_data, selected_period):
    """
    Web公開機能セクション（努力度表示対応）
    """
    try:
        st.markdown("---")
        st.subheader("🌐 Web公開・HTMLエクスポート（努力度表示版）")

        if not results_data or results_data[0] is None:
            st.warning("公開・エクスポート対象のデータがありません。")
            return

        df_original = st.session_state['df']
        target_data = st.session_state.get('target_data', pd.DataFrame())

        # 簡潔なエクスポートUI
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            button_label = f"📥 {selected_tab} HTML"
            export_type = "action" if selected_tab == "アクション提案" else "metrics"
            
            if st.button(button_label, key=f"download_dept_current_{export_type}", use_container_width=True):
                with st.spinner(f"{selected_tab}のHTMLを生成中..."):
                    html_content = generate_current_tab_html(selected_tab, results_data, period_desc, target_data)
                    
                    if html_content:
                        filename = get_export_filename("department", export_type, period_desc)
                        st.session_state[f'dl_dept_{export_type}_html'] = html_content
                        st.session_state[f'dl_dept_{export_type}_name'] = filename

            if f'dl_dept_{export_type}_html' in st.session_state:
                st.download_button(
                    label="✔️ ダウンロード",
                    data=st.session_state[f'dl_dept_{export_type}_html'].encode("utf-8"),
                    file_name=st.session_state[f'dl_dept_{export_type}_name'],
                    mime="text/html",
                    key=f"download_dept_{export_type}_exec",
                    use_container_width=True
                )

        with col2:
            if st.button("📥 統合HTML", key="download_dept_combined", use_container_width=True):
                with st.spinner("統合HTMLを生成中..."):
                    html_content = generate_integrated_html(results_data, period_desc, target_data)
                    
                    if html_content:
                        filename = get_export_filename("department", "integrated", period_desc)
                        st.session_state['dl_dept_integrated_html'] = html_content
                        st.session_state['dl_dept_integrated_name'] = filename

            if 'dl_dept_integrated_html' in st.session_state:
                st.download_button(
                    label="✔️ ダウンロード",
                    data=st.session_state['dl_dept_integrated_html'].encode("utf-8"),
                    file_name=st.session_state['dl_dept_integrated_name'],
                    mime="text/html",
                    key="download_dept_integrated_exec",
                    use_container_width=True
                )

        with col3:
            if st.button("🌐 Web最適化", key="download_dept_web_optimized", use_container_width=True):
                with st.spinner("Web公開版HTMLを生成中..."):
                    period_desc = get_period_dates(df_original, selected_period)[2]
                    html_content = generate_web_optimized_html(results_data, period_desc)
                    
                    if html_content:
                        filename = f"web_department_effort_{period_desc.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
                        st.session_state['dl_dept_web_html'] = html_content
                        st.session_state['dl_dept_web_name'] = filename

            if 'dl_dept_web_html' in st.session_state:
                st.download_button(
                    label="✔️ ダウンロード",
                    data=st.session_state['dl_dept_web_html'].encode("utf-8"),
                    file_name=st.session_state['dl_dept_web_name'],
                    mime="text/html",
                    key="download_dept_web_exec",
                    use_container_width=True
                )

        # 使用方法ガイド
        with st.expander("📖 努力度表示HTMLについて", expanded=False):
            st.markdown("""
            **目標達成努力度表示の特徴:**
            
            - ✨**目標突破中**: 目標達成 + さらに改善中
            - 🎯**達成継続**: 目標達成を継続中
            - 💪**追い上げ中**: 目標まであと少し + 改善中
            - 📈**要努力**: 目標まであと少し + さらなる努力を
            - 🚨**要改善**: 積極的な取り組みが必要
            
            **簡素化された効果シミュレーション:**
            
            - 新入院を週に1人増やした場合の効果
            - 在院日数を平均1日延ばした場合の効果
            - 理解しやすい簡易計算による概算
            
            **週報での活用:**
            
            - 各診療科の頑張り具合が一目で分かる
            - スタッフのモチベーション向上に効果的
            - 改善の方向性が明確
            """)

    except Exception as e:
        logger.error(f"Web公開セクション表示エラー: {e}", exc_info=True)
        st.error(f"Web公開機能でエラーが発生しました: {str(e)}")

def generate_current_tab_html(selected_tab, results_data, period_desc, target_data):
    """現在のタブ用HTML生成（努力度表示版）"""
    try:
        if selected_tab == "アクション提案":
            # アクション提案HTML（努力度表示版）
            action_results = results_data[0] if results_data else []
            
            # 詳細データの場合は変換
            if action_results and 'basic_info' in action_results[0]:
                action_results = _convert_detailed_to_standard_format(action_results)
            
            if action_results:
                hospital_targets = get_hospital_targets(target_data)
                return generate_unified_html_export(action_results, period_desc, hospital_targets, "department")
            else:
                return None
        else:
            # メトリクスHTML（従来通り）
            from html_export_functions import generate_metrics_html, validate_export_data
            kpi_data = results_data[0] if results_data else []
            is_valid, msg = validate_export_data(kpi_data, "metrics")
            if is_valid:
                return generate_metrics_html(kpi_data, period_desc, selected_tab, "department")
            else:
                st.error(f"データ検証エラー: {msg}")
                return None
                
    except Exception as e:
        logger.error(f"現在のタブHTML生成エラー: {e}")
        return None

def generate_integrated_html(results_data, period_desc, target_data):
    """統合HTML生成（努力度表示版）"""
    try:
        from html_export_functions import generate_combined_html_with_tabs
        
        # 統合データの準備
        if not results_data or not results_data[0]:
            return None
        
        # メトリクスデータの準備
        df_original = st.session_state['df']
        target_data_session = st.session_state.get('target_data', pd.DataFrame())
        
        # 期間の取得（results_dataから推定）
        start_date, end_date, _ = get_period_dates(df_original, "直近4週間")  # デフォルト
        
        # データフィルタリング
        date_filtered_df = safe_date_filter(df_original, start_date, end_date)
        
        # 診療科別データ生成
        possible_cols = ['部門名', '診療科', '診療科名']
        dept_col = next((c for c in possible_cols if c in date_filtered_df.columns), None)
        
        if not dept_col:
            return None
        
        metrics_data_dict = {}
        metric_names = ["日平均在院患者数", "週合計新入院患者数", "平均在院日数"]
        
        unique_depts = date_filtered_df[dept_col].unique()
        for metric in metric_names:
            kpis = []
            for dept_code in unique_depts:
                kpi = calculate_department_kpis(
                    date_filtered_df, target_data_session, dept_code, dept_code,
                    start_date, end_date, dept_col
                )
                if kpi:
                    kpis.append(kpi)
            metrics_data_dict[metric] = kpis
        
        # アクションデータ（努力度表示版）
        action_data_for_export = {
            'action_results': results_data[0] if results_data else [],
            'hospital_targets': get_hospital_targets(target_data_session)
        }
        
        # 統合HTML生成
        html_content = generate_combined_html_with_tabs(
            metrics_data_dict, action_data_for_export, period_desc, "department"
        )
        
        return html_content
        
    except Exception as e:
        logger.error(f"統合HTML生成エラー: {e}")
        return None

def create_department_performance_tab():
    """診療科別パフォーマンスダッシュボードのメイン関数（トレンド分析・影響度順対応版）"""
    st.header("🏥 診療科別パフォーマンスダッシュボード")

    if not st.session_state.get('data_processed', False):
        st.warning("📊 データを読み込むと、ここにダッシュボードが表示されます。")
        return
    
    df_original = st.session_state.get('df')
    target_data = st.session_state.get('target_data', pd.DataFrame())
    
    if target_data is not None and not target_data.empty: 
        create_dept_mapping_table(target_data)
    
    st.markdown("##### 表示指標の選択")
    # ★★★ 平均在院日数をトレンド分析に変更 ★★★
    tab_options = ["日平均在院患者数", "週合計新入院患者数", "平均在院日数（トレンド分析）", "アクション提案"]
    
    # セッション状態の初期化
    if 'selected_dept_tab_name' not in st.session_state:
        st.session_state.selected_dept_tab_name = tab_options[0]

    # ボタンを横並びに配置してタブのように見せる
    cols = st.columns(4)
    for i, option in enumerate(tab_options):
        # 選択中のタブをハイライト
        button_type = "primary" if st.session_state.selected_dept_tab_name == option else "secondary"
        if cols[i].button(option, key=f"dept_tab_{i}", use_container_width=True, type=button_type):
            st.session_state.selected_dept_tab_name = option
            st.rerun()
    
    st.info(f"現在の表示: **{st.session_state.selected_dept_tab_name}** | 努力度表示機能有効")
    st.markdown("---")

    period_options = ["直近4週間", "直近8週", "直近12週", "今年度", "先月", "昨年度"]
    selected_period = st.selectbox("📅 集計期間", period_options, index=0, key="dept_performance_period")

    # 選択されたタブに応じた表示ロジック
    results_data = None
    try:
        selected_tab = st.session_state.selected_dept_tab_name
        
        if selected_tab == "アクション提案":
            # アクション提案タブ（影響度順対応版）
            results_data = display_action_dashboard_with_detail_option(df_original, target_data, selected_period)
        else:
            # 3つの指標タブ（トレンド分析対応版）
            results_data = display_metrics_dashboard(selected_tab, df_original, target_data, selected_period)
        
        # 結果データが存在する場合のみ、エクスポートセクションを表示
        if results_data and results_data[0] is not None:
            display_web_publish_section(selected_tab, results_data, selected_period)
        elif selected_tab:
             st.warning("選択された条件のデータが存在しないか、KPI計算に失敗しました。")
            
    except Exception as e:
        logger.error(f"ダッシュボード表示エラー: {e}", exc_info=True)
        st.error(f"ダッシュボードの表示中にエラーが発生しました: {str(e)}")