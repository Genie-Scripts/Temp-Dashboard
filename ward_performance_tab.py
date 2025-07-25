import streamlit as st
import pandas as pd
import logging
from datetime import datetime
import calendar
from config import EXCLUDED_WARDS

logger = logging.getLogger(__name__)

try:
    from report_generation.utils import (
    safe_date_filter, get_ward_display_name, create_ward_name_mapping,
    get_period_dates, calculate_ward_kpis, decide_action_and_reasoning,
    evaluate_feasibility, calculate_effect_simulation, calculate_los_appropriate_range,
    get_hospital_targets
    )
    from unified_filters import get_unified_filter_config
    from unified_html_export import generate_unified_html_export
    
    # アクション提案ダッシュボードの表示関数
    from enhanced_streamlit_display import display_enhanced_action_dashboard

except ImportError as e:
    st.error(f"必要なモジュールのインポートに失敗しました: {e}")
    st.stop()

def calculate_los_appropriate_range(item_df, start_date, end_date):
    """統計的アプローチで在院日数適正範囲を計算 (診療科/病棟 兼用)"""
    if item_df.empty: 
        return None
    try:
        period_df = safe_date_filter(item_df, start_date, end_date)
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

def evaluate_feasibility(kpi_data, item_df, start_date, end_date):
    """実現可能性を評価 (診療科/病棟 兼用)"""
    try:
        admission_feasible = {
            "病床余裕": kpi_data.get('daily_census_achievement', 0) < 90,
            "トレンド安定": kpi_data.get('recent_week_admissions', 0) >= kpi_data.get('weekly_avg_admissions', 0) * 0.95
        }
        
        los_range = calculate_los_appropriate_range(item_df, start_date, end_date)
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
    """効果シミュレーション計算 (診療科/病棟 兼用)"""
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


def get_color(val):
    """達成率に応じた色を取得"""
    if val >= 100:
        return "#7fb069"  # パステルグリーン
    elif val >= 80:
        return "#f5d76e"  # パステルイエロー
    else:
        return "#e08283"  # パステルレッド

def render_metric_card(label, period_avg, recent, target, achievement, unit, card_color, bed_info=None):
    """病棟メトリックカードのHTML生成（病床情報付き）"""
    ach_str = f"{achievement:.1f}%" if achievement or achievement == 0 else "--"
    ach_label = "達成率:"
    target_color = "#b3b9b3" if not target or target == '--' else "#7b8a7a"
    
    bed_info_html = ""
    if bed_info and bed_info.get('bed_count'):
        occupancy_str = f"{bed_info['occupancy_rate']:.1f}%" if bed_info.get('occupancy_rate') is not None else "--"
        bed_info_html = f"""
        <div style="margin-top:4px; padding-top:4px; border-top:1px solid #e0e0e0;">
            <div style="display:flex; justify-content:space-between; font-size:0.9em;"><span style="color:#999;">病床数:</span><span>{bed_info['bed_count']}床</span></div>
            <div style="display:flex; justify-content:space-between; font-size:0.9em;"><span style="color:#999;">稼働率:</span><span style="font-weight:600;">{occupancy_str}</span></div>
        </div>"""
    
    return f"""
    <div style="background: {card_color}0E; border-radius: 11px; border-left: 6px solid {card_color}; margin-bottom: 12px; padding: 12px 16px 7px 16px;">
        <div style="font-size:1.13em; font-weight:700; margin-bottom:7px; color:#293a27;">{label}</div>
        <div style="display:flex; flex-direction:column; gap:2px;">
            <div style="display:flex; justify-content:space-between;"><span style="font-size:0.93em; color:#7b8a7a;">期間平均:</span><span style="font-size:1.07em; font-weight:700;">{period_avg} {unit}</span></div>
            <div style="display:flex; justify-content:space-between;"><span style="font-size:0.93em; color:#7b8a7a;">直近週実績:</span><span style="font-size:1.07em; font-weight:700;">{recent} {unit}</span></div>
            <div style="display:flex; justify-content:space-between;"><span style="font-size:0.93em; color:#7b8a7a;">目標:</span><span style="font-size:1.07em; font-weight:700; color:{target_color};">{target if target else '--'} {unit}</span></div>
        </div>
        <div style="margin-top:7px; display:flex; justify-content:space-between; align-items:center;">
          <div style="font-weight:700; font-size:1.03em; color:{card_color};">{ach_label}</div>
          <div style="font-weight:700; font-size:1.20em; color:{card_color};">{ach_str}</div>
        </div>
        {bed_info_html}
    </div>"""

def render_los_trend_card(label, period_avg, recent, unit, item_df, start_date, end_date):
    """在院日数トレンド分析カードのHTML生成（病棟版）"""
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
        los_range = calculate_los_appropriate_range(item_df, start_date, end_date)
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
        logger.error(f"病棟在院日数トレンドカード生成エラー: {e}")
        return f"""
        <div style="background: #f0f0f0; border-radius: 11px; border-left: 6px solid #999; margin-bottom: 12px; padding: 12px 16px 7px 16px;">
            <div style="font-size:1.13em; font-weight:700; margin-bottom:7px; color:#293a27;">{label}</div>
            <div style="color: #666;">トレンド分析でエラーが発生しました</div>
        </div>"""

def display_metrics_dashboard(selected_metric, df_original, target_data, selected_period):
    """病棟3指標表示ダッシュボード（トレンド分析対応版）"""
    try:
        start_date, end_date, period_desc = get_period_dates(df_original, selected_period)
        if start_date is None or end_date is None:
            st.error("期間の計算に失敗しました。")
            return
        
        date_filtered_df = safe_date_filter(df_original, start_date, end_date)
        if date_filtered_df.empty:
            st.warning(f"選択された期間（{period_desc}）にデータがありません。")
            return
        
        possible_cols = ['病棟コード', '病棟名', '病棟']
        ward_col = next((c for c in possible_cols if c in date_filtered_df.columns), None)
        if ward_col is None:
            st.error(f"病棟列が見つかりません。")
            return

        unique_wards = [w for w in date_filtered_df[ward_col].unique() if w not in EXCLUDED_WARDS]
        ward_kpis = []
        for ward_code in unique_wards:
            kpi = calculate_ward_kpis(date_filtered_df, target_data, ward_code, get_ward_display_name(ward_code), start_date, end_date, ward_col)
            if kpi: 
                ward_kpis.append(kpi)
        
        if not ward_kpis:
            st.warning("表示可能な病棟データがありません。")
            return

        # 平均在院日数（トレンド分析）の場合は特別処理
        if selected_metric == "平均在院日数（トレンド分析）":
            st.markdown(f"### 📈 **{period_desc}** の病棟別トレンド分析（平均在院日数）")
            
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
            
            ward_kpis.sort(key=get_trend_sort_key)
            
            n_cols = 3 if len(ward_kpis) <= 6 else 4 if len(ward_kpis) <= 12 else 5
            cols = st.columns(n_cols)
            
            for idx, kpi in enumerate(ward_kpis):
                ward_df = date_filtered_df[date_filtered_df[ward_col] == kpi['ward_code']]
                html = render_los_trend_card(
                    kpi["ward_name"], 
                    kpi.get('avg_length_of_stay', 0),
                    kpi.get('recent_week_avg_los', 0), 
                    "日",
                    ward_df,
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
            ward_kpis.sort(key=lambda x: x.get(opt["ach"], 0), reverse=rev)

            st.markdown(f"### 📈 **{period_desc}** の病棟別パフォーマンス（{selected_metric}）")
            
            n_cols = 3 if len(ward_kpis) <= 6 else 4 if len(ward_kpis) <= 12 else 5
            cols = st.columns(n_cols)
            
            for idx, kpi in enumerate(ward_kpis):
                bed_info = {'bed_count': kpi['bed_count'], 'occupancy_rate': kpi.get('bed_occupancy_rate')} if selected_metric == "日平均在院患者数" else None
                avg_disp = f"{kpi.get(opt['avg'], 0):.1f}" if kpi.get(opt['avg']) is not None else "--"
                recent_disp = f"{kpi.get(opt['recent'], 0):.1f}" if kpi.get(opt['recent']) is not None else "--"
                target_disp = f"{kpi.get(opt['target']):.1f}" if kpi.get(opt['target']) is not None else "--"
                html = render_metric_card(kpi["ward_name"], avg_disp, recent_disp, target_disp, kpi.get(opt["ach"], 0), opt["unit"], get_color(kpi.get(opt["ach"], 0)), bed_info)
                with cols[idx % n_cols]:
                    st.markdown(html, unsafe_allow_html=True)
        
        return ward_kpis, start_date, end_date, period_desc
    
    except Exception as e:
        logger.error(f"病棟メトリクス表示エラー: {e}", exc_info=True)
        st.error(f"病棟メトリクス表示中にエラーが発生しました: {str(e)}")
        return None, None, None, None

def display_action_dashboard(df_original, target_data, selected_period):
    """アクション提案ダッシュボード（努力度表示版・目標差順対応）"""
    try:
        if not st.session_state.get('ward_mapping_initialized', False) and (target_data is not None and not target_data.empty): 
            create_ward_name_mapping(df_original, target_data)
        
        # 表示モード選択（病棟版）
        st.markdown("#### 🎯 病棟アクション提案表示設定")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            display_mode = st.radio(
                "表示モード",
                ["詳細表示（目標達成努力度版）", "簡易表示（従来版）"],
                index=0,
                horizontal=True,
                help="詳細表示では、目標達成努力度と簡素化された効果シミュレーションを表示します",
                key="ward_action_display_mode"
            )
        
        with col2:
            if st.button("🔄 更新", key="refresh_ward_action_dashboard"):
                st.rerun()
        
        # 選択されたモードに応じて表示
        if display_mode == "詳細表示（目標達成努力度版）":
            return display_detailed_ward_action_dashboard(df_original, target_data, selected_period)
        else:
            return display_simple_ward_action_dashboard(df_original, target_data, selected_period)
            
    except Exception as e:
        logger.error(f"病棟アクション提案ダッシュボード表示エラー: {e}", exc_info=True)
        st.error(f"病棟アクション提案ダッシュボードの表示中にエラーが発生しました: {str(e)}")
        return None

def display_detailed_ward_action_dashboard(df_original, target_data, selected_period):
    """病棟版詳細アクション提案ダッシュボード（努力度表示版）"""
    try:
        hospital_targets = get_hospital_targets(target_data)
        start_date, end_date, period_desc = get_period_dates(df_original, selected_period)
        if start_date is None or end_date is None:
            st.error("期間の計算に失敗しました。")
            return
        
        date_filtered_df = safe_date_filter(df_original, start_date, end_date)
        if date_filtered_df.empty:
            st.warning(f"選択された期間（{period_desc}）にデータがありません。")
            return
        
        possible_cols = ['病棟コード', '病棟名', '病棟']
        ward_col = next((c for c in possible_cols if c in date_filtered_df.columns), None)
        if ward_col is None:
            st.error(f"病棟列が見つかりません。")
            return

        # 病院全体サマリー
        total_census = date_filtered_df['在院患者数'].sum() / ((end_date - start_date).days + 1) if '在院患者数' in date_filtered_df.columns and not date_filtered_df.empty else 0
        total_admissions = date_filtered_df['新入院患者数'].sum() / ((end_date - start_date).days + 1) if '新入院患者数' in date_filtered_df.columns and not date_filtered_df.empty else 0
        
        hospital_census_ach = (total_census / hospital_targets['daily_census'] * 100) if hospital_targets['daily_census'] else 0
        hospital_admission_ach = (total_admissions / hospital_targets.get('daily_admissions', 80) * 100) if hospital_targets.get('daily_admissions') else 0
        
        st.markdown(f"### 🎯 病院全体目標達成状況 - {period_desc}")
        
        col1, col2 = st.columns(2)
        with col1:
            census_color = "normal" if hospital_census_ach >= 95 else "inverse"
            st.metric(
                "日平均在院患者数", 
                f"{total_census:.1f}人",
                f"{total_census - hospital_targets['daily_census']:+.1f}人 (達成率: {hospital_census_ach:.1f}%)",
                delta_color=census_color
            )
        
        with col2:
            admission_color = "normal" if hospital_admission_ach >= 95 else "inverse"
            st.metric(
                "日平均新入院患者数",
                f"{total_admissions:.1f}人",
                f"達成率: {hospital_admission_ach:.1f}%",
                delta_color=admission_color
            )

        st.markdown("### 🏨 病棟別詳細アクション提案（目標達成努力度版）")
        
        unique_wards = [w for w in date_filtered_df[ward_col].unique() if w not in EXCLUDED_WARDS]
        action_results = []
        
        for ward_code in unique_wards:
            kpi = calculate_ward_kpis(date_filtered_df, target_data, ward_code, get_ward_display_name(ward_code), start_date, end_date, ward_col)
            
            if kpi:
                ward_df = date_filtered_df[date_filtered_df[ward_col] == ward_code]
                feasibility = evaluate_feasibility(kpi, ward_df, start_date, end_date)
                simulation = calculate_effect_simulation(kpi)
                action_result = decide_action_and_reasoning(kpi, feasibility, simulation)
                action_results.append({'kpi': kpi, 'action_result': action_result, 'feasibility': feasibility, 'simulation': simulation})
        
        if not action_results:
            st.warning("表示可能な病棟データがありません。")
            return
        
        # ★★★ シンプルな目標差順ソート（病棟版）★★★
        def calculate_comprehensive_impact_score(x):
            """
            シンプルな影響度スコア計算（目標患者数 - 直近週実績値の順）
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
        
        action_results.sort(key=calculate_comprehensive_impact_score, reverse=True)
        
        # 詳細カード表示（病棟版）
        for result in action_results:
            _display_detailed_ward_action_card(result)
        
        return action_results, start_date, end_date, period_desc
    
    except Exception as e:
        logger.error(f"病棟詳細アクション表示エラー: {e}", exc_info=True)
        st.error(f"病棟詳細アクション表示中にエラーが発生しました: {str(e)}")
        return None

def _display_detailed_ward_action_card(result):
    """病棟版詳細アクションカードの表示（努力度表示版）"""
    try:
        kpi = result.get('kpi', {})
        action_result = result.get('action_result', {})
        feasibility = result.get('feasibility', {})
        simulation = result.get('simulation', {})
        
        # 努力度計算（病棟版）
        effort_status = _calculate_ward_effort_status(kpi)
        
        # 基本情報
        ward_name = kpi.get('ward_name', 'Unknown')
        action = action_result.get('action', '要確認')
        reasoning = action_result.get('reasoning', '')
        action_color = action_result.get('color', '#b3b9b3')
        
        # メインカードコンテナ
        with st.container():
            # カードヘッダー（努力度表示版）
            st.markdown(f"""
            <div style="
                background: linear-gradient(90deg, {effort_status['color']}15 0%, {effort_status['color']}05 100%);
                border-left: 6px solid {effort_status['color']};
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3 style="color: #293a27; margin: 0;">{ward_name}</h3>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span style="background: {effort_status['color']}; color: white; padding: 6px 15px; border-radius: 25px; font-weight: bold;">
                            {effort_status['emoji']} {effort_status['status']}
                        </span>
                    </div>
                </div>
                <div style="color: #666; margin-top: 8px;">
                    {effort_status['description']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # メトリクス表示（病棟版）
            try:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    census_delta_color = "normal" if kpi.get('daily_census_achievement', 0) >= 95 else "inverse"
                    target_display = f"{kpi.get('daily_census_target', 0):.1f}" if kpi.get('daily_census_target') else "--"
                    st.metric(
                        "在院患者数",
                        f"{kpi.get('daily_avg_census', 0):.1f}人",
                        f"目標: {target_display}人",
                        delta_color=census_delta_color
                    )
                
                with col2:
                    st.metric(
                        "達成率",
                        f"{kpi.get('daily_census_achievement', 0):.1f}%",
                        effort_status.get('level', '評価中')
                    )
                
                with col3:
                    delta_value = kpi.get('recent_week_daily_census', 0) - kpi.get('daily_avg_census', 0)
                    st.metric(
                        "直近週実績",
                        f"{kpi.get('recent_week_daily_census', 0):.1f}人",
                        f"{delta_value:+.1f}人"
                    )
                
                with col4:
                    # 病床稼働率（病棟特有）
                    bed_occupancy = kpi.get('bed_occupancy_rate', 0)
                    bed_count = kpi.get('bed_count', 0)
                    if bed_count and bed_count > 0:
                        st.metric(
                            f"病床稼働率",
                            f"{bed_occupancy:.1f}%",
                            f"({bed_count}床)"
                        )
                    else:
                        st.metric(
                            "努力度評価",
                            effort_status['level'],
                            effort_status['status']
                        )
                        
            except Exception as e:
                logger.error(f"病棟メトリクス表示エラー: {e}")
                st.error("メトリクス表示でエラーが発生しました")
            
            # タブ式詳細情報（病棟版）
            try:
                tab1, tab2, tab3, tab4 = st.tabs(["📊 現状分析", "⚙️ 実現可能性", "📈 簡易効果予測", "🎯 推奨アクション"])
                
                with tab1:
                    _display_ward_current_analysis(kpi, effort_status)
                
                with tab2:
                    _display_ward_feasibility_analysis(feasibility)
                
                with tab3:
                    _display_ward_simplified_simulation_analysis(simulation, kpi)
                
                with tab4:
                    _display_ward_action_recommendation(action_result)
                    
            except Exception as e:
                logger.error(f"病棟タブ表示エラー: {e}")
                st.error("詳細情報表示でエラーが発生しました")
                
    except Exception as e:
        logger.error(f"病棟詳細アクションカード表示エラー: {e}")
        st.error(f"カード表示でエラーが発生しました: {str(e)}")

def _calculate_ward_effort_status(kpi):
    """病棟用努力度計算"""
    try:
        current_census = kpi.get('daily_avg_census', 0)
        recent_week_census = kpi.get('recent_week_daily_census', 0)
        census_achievement = kpi.get('daily_census_achievement', 0)
        
        trend_change = recent_week_census - current_census
        
        if census_achievement >= 100:
            if trend_change > 0:
                return {
                    'status': "✨目標突破中",
                    'level': "優秀", 
                    'emoji': "✨",
                    'description': f"目標達成＋さらに改善中（+{trend_change:.1f}人）",
                    'color': "#4CAF50"
                }
            else:
                return {
                    'status': "🎯達成継続",
                    'level': "良好",
                    'emoji': "🎯", 
                    'description': "目標達成を継続中",
                    'color': "#7fb069"
                }
        elif census_achievement >= 85:
            if trend_change > 0:
                return {
                    'status': "💪追い上げ中",
                    'level': "改善",
                    'emoji': "💪",
                    'description': f"目標まであと少し！改善中（+{trend_change:.1f}人）",
                    'color': "#FF9800"
                }
            else:
                return {
                    'status': "📈要努力", 
                    'level': "注意",
                    'emoji': "📈",
                    'description': "目標まであと少し、さらなる努力を",
                    'color': "#FFC107"
                }
        else:
            return {
                'status': "🚨要改善",
                'level': "要改善",
                'emoji': "🚨", 
                'description': "目標達成に向けた積極的な取り組みが必要",
                'color': "#F44336"
            }
    except Exception as e:
        logger.error(f"病棟努力度計算エラー: {e}")
        return {
            'status': "❓評価困難",
            'level': "不明",
            'emoji': "❓",
            'description': "データ不足のため評価困難",
            'color': "#9E9E9E"
        }

def _display_ward_current_analysis(kpi, effort_status):
    """病棟現状分析タブの表示"""
    try:
        st.markdown("#### 📋 指標別現状")
        
        # 在院患者数分析
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**在院患者数動向**")
            census_gap = kpi.get('daily_avg_census', 0) - (kpi.get('daily_census_target', 0) or 0)
            gap_color = "🟢" if census_gap >= 0 else "🔴"
            st.markdown(f"• 目標との差: {gap_color} {census_gap:+.1f}人")
            st.markdown(f"• 達成状況: {effort_status['status']}")
        
        with col2:
            st.markdown("**新入院動向**")
            st.markdown(f"• 期間平均: {kpi.get('weekly_avg_admissions', 0)/7:.1f}人/日")
            st.markdown(f"• 直近週: {kpi.get('recent_week_admissions', 0)/7:.1f}人/日")
            
            # トレンド計算
            avg_adm = kpi.get('weekly_avg_admissions', 0)/7
            recent_adm = kpi.get('recent_week_admissions', 0)/7
            if recent_adm > avg_adm * 1.03:
                trend = "↗️増加"
            elif recent_adm < avg_adm * 0.97:
                trend = "↘️減少"
            else:
                trend = "➡️安定"
            st.markdown(f"• トレンド: {trend}")
        
        # 病床稼働率分析（病棟特有）
        if kpi.get('bed_count') and kpi.get('bed_count') > 0:
            st.markdown("**病床稼働率分析**")
            col3, col4 = st.columns(2)
            with col3:
                bed_occupancy = kpi.get('bed_occupancy_rate', 0)
                bed_count = kpi.get('bed_count', 0)
                st.markdown(f"• 病床数: {bed_count}床")
                st.markdown(f"• 稼働率: {bed_occupancy:.1f}%")
                
                if bed_occupancy >= 90:
                    occupancy_status = "🔴 高稼働"
                elif bed_occupancy >= 70:
                    occupancy_status = "🟡 適正"
                else:
                    occupancy_status = "🟢 余裕"
                st.markdown(f"• 評価: {occupancy_status}")
            
            with col4:
                st.markdown("**在院日数動向**")
                st.markdown(f"• 期間平均: {kpi.get('avg_length_of_stay', 0):.1f}日")
                st.markdown(f"• 直近週: {kpi.get('recent_week_avg_los', 0):.1f}日")
        
    except Exception as e:
        logger.error(f"病棟現状分析表示エラー: {e}")
        st.error("現状分析の表示でエラーが発生しました")

def _display_ward_feasibility_analysis(feasibility):
    """病棟実現可能性分析タブの表示"""
    try:
        st.markdown("#### ⚙️ 改善施策の実現可能性")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**新入院増加施策**")
            adm_feas = feasibility.get('admission', {}) if feasibility else {}
            
            # スコア計算
            score = sum(adm_feas.values()) if adm_feas else 0
            score_color = "🟢" if score >= 2 else "🟡" if score >= 1 else "🔴"
            assessment = "高い" if score >= 2 else "中程度" if score >= 1 else "低い"
            st.markdown(f"• 実現可能性: {score_color} {assessment}")
            st.markdown(f"• スコア: {score}/2")
            
            # 詳細要因
            if adm_feas:
                st.markdown("**評価要因:**")
                for factor, status in adm_feas.items():
                    emoji = "✅" if status else "❌"
                    st.markdown(f"• {emoji} {factor}")
        
        with col2:
            st.markdown("**在院日数調整施策**")
            los_feas = feasibility.get('los', {}) if feasibility else {}
            
            # スコア計算
            score = sum(los_feas.values()) if los_feas else 0
            score_color = "🟢" if score >= 2 else "🟡" if score >= 1 else "🔴"
            assessment = "高い" if score >= 2 else "中程度" if score >= 1 else "低い"
            st.markdown(f"• 実現可能性: {score_color} {assessment}")
            st.markdown(f"• スコア: {score}/2")
            
            # 詳細要因
            if los_feas:
                st.markdown("**評価要因:**")
                for factor, status in los_feas.items():
                    emoji = "✅" if status else "❌"
                    st.markdown(f"• {emoji} {factor}")
        
    except Exception as e:
        logger.error(f"病棟実現可能性分析表示エラー: {e}")
        st.error("実現可能性分析の表示でエラーが発生しました")

def _display_ward_simplified_simulation_analysis(simulation, kpi):
    """病棟簡素化効果予測タブの表示"""
    try:
        st.markdown("#### 📈 簡易効果シミュレーション")
        st.info("💡 簡単な仮定に基づく概算効果です")
        
        # 簡素化された効果計算
        current_admissions_per_day = kpi.get('weekly_avg_admissions', 0) / 7
        current_los = kpi.get('avg_length_of_stay', 0)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📈 新入院増加案**")
            # 新入院+1人/週の効果
            admission_effect = current_los if current_los > 0 else 7
            st.markdown("• 新入院を週に1人増やすと")
            st.markdown(f"• 予想効果: **+{admission_effect:.1f}人**")
            
            if admission_effect > 0:
                st.success(f"✅ 週1人増 → 日平均+{admission_effect:.1f}人")
            else:
                st.warning("⚠️ 効果が期待できません")
        
        with col2:
            st.markdown("**📊 在院日数延長案**")
            # 在院日数+1日の効果
            los_effect = current_admissions_per_day if current_admissions_per_day > 0 else 1
            st.markdown("• 在院日数を平均1日延ばすと")
            st.markdown(f"• 予想効果: **+{los_effect:.1f}人**")
            
            if los_effect > 0:
                st.success(f"✅ 1日延長 → 日平均+{los_effect:.1f}人")
            else:
                st.warning("⚠️ 効果が期待できません")
        
        # 注釈
        st.caption("📝 簡易計算による概算効果です")
        
    except Exception as e:
        logger.error(f"病棟簡素化効果予測表示エラー: {e}")
        st.error("効果予測の表示でエラーが発生しました")

def _display_ward_action_recommendation(action_result):
    """病棟推奨アクションタブの表示"""
    try:
        st.markdown("#### 🎯 推奨アクションプラン")
        
        # アクション概要
        action = action_result.get('action', '要確認')
        reasoning = action_result.get('reasoning', '')
        action_color = action_result.get('color', '#b3b9b3')
        
        st.markdown(f"""
        <div style="
            background: {action_color}15;
            border: 2px solid {action_color};
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
        ">
            <h4 style="color: {action_color}; margin-bottom: 10px;">🎯 {action}</h4>
            <p style="margin: 0; color: #333; line-height: 1.5;">{reasoning}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 病棟別具体的な次のステップ
        st.markdown("**📋 病棟での具体的な次のステップ**")
        
        if action == "新入院重視":
            st.markdown("""
            1. 🏥 救急外来との連携強化
            2. 📞 地域医療機関との病診連携促進
            3. 📊 入院適応基準の見直し
            4. ⏰ 入院受け入れ体制の最適化
            5. 🛏️ 病床管理の効率化
            """)
        elif action == "在院日数調整":
            st.markdown("""
            1. 📋 退院基準の明確化・標準化
            2. 🤝 多職種カンファレンスの充実
            3. 🏠 在宅移行支援・退院調整の強化
            4. 📈 クリニカルパスの見直し・最適化
            5. 👨‍⚕️ 病棟医師との連携強化
            """)
        elif action == "両方検討":
            st.markdown("""
            1. 🎯 緊急性の高い施策の優先実施
            2. 📊 病棟データ収集・分析の強化
            3. 👥 多職種での改善チーム編成
            4. 📅 定期的な病棟カンファレンス設定
            5. 🔄 週次での進捗確認・調整
            """)
        else:
            st.markdown("""
            1. 📊 現状の継続的監視・データ収集
            2. 📈 病棟トレンド分析の定期実施
            3. 🔍 潜在的課題の早期発見
            4. 📋 予防的対策の準備・検討
            5. 🏥 病院全体との連携維持
            """)
            
    except Exception as e:
        logger.error(f"病棟推奨アクション表示エラー: {e}")
        st.error("推奨アクションの表示でエラーが発生しました")

def display_simple_ward_action_dashboard(df_original, target_data, selected_period):
    """病棟版簡易アクション提案ダッシュボード（目標差順対応）"""
    try:
        hospital_targets = get_hospital_targets(target_data)
        start_date, end_date, period_desc = get_period_dates(df_original, selected_period)
        if start_date is None or end_date is None:
            st.error("期間の計算に失敗しました。")
            return
        
        date_filtered_df = safe_date_filter(df_original, start_date, end_date)
        if date_filtered_df.empty:
            st.warning(f"選択された期間（{period_desc}）にデータがありません。")
            return
        
        possible_cols = ['病棟コード', '病棟名', '病棟']
        ward_col = next((c for c in possible_cols if c in date_filtered_df.columns), None)
        if ward_col is None:
            st.error(f"病棟列が見つかりません。")
            return

        total_census = date_filtered_df['在院患者数'].sum() / ((end_date - start_date).days + 1) if '在院患者数' in date_filtered_df.columns and not date_filtered_df.empty else 0
        st.metric("日平均在院患者数 (全体)", f"{total_census:.1f} 人", f"{total_census - hospital_targets['daily_census']:+.1f} 人 (目標: {hospital_targets['daily_census']:.0f}人)")

        st.markdown("### 🏨 病棟別アクション提案（目標差順）")
        
        unique_wards = [w for w in date_filtered_df[ward_col].unique() if w not in EXCLUDED_WARDS]
        action_results = []
        
        for ward_code in unique_wards:
            kpi = calculate_ward_kpis(date_filtered_df, target_data, ward_code, get_ward_display_name(ward_code), start_date, end_date, ward_col)
            
            if kpi:
                ward_df = date_filtered_df[date_filtered_df[ward_col] == ward_code]
                feasibility = evaluate_feasibility(kpi, ward_df, start_date, end_date)
                simulation = calculate_effect_simulation(kpi)
                action_result = decide_action_and_reasoning(kpi, feasibility, simulation)
                action_results.append({'kpi': kpi, 'action_result': action_result, 'feasibility': feasibility, 'simulation': simulation})
        
        if not action_results:
            st.warning("表示可能な病棟データがありません。")
            return
        
        # ★★★ シンプルな目標差順ソート（病棟版）★★★
        def calculate_comprehensive_impact_score(x):
            """
            シンプルな影響度スコア計算（目標患者数 - 直近週実績値の順）
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
        
        cols = st.columns(3)
        for idx, result in enumerate(action_results):
            with cols[idx % 3]:
                kpi, action_result = result['kpi'], result['action_result']
                
                # 優先度ラベルを表示に追加
                priority_label, priority_color = get_priority_label(kpi)
                
                bed_info_str = f"<div style='margin-top:8px; font-size:0.8em;'>病床数: {kpi['bed_count']}床 | 稼働率: {kpi.get('bed_occupancy_rate', 0):.1f}%</div>" if kpi.get('bed_count') else ""
                st.markdown(f"""
                <div style="background:{action_result.get('color', '#b3b9b3')}0E; border-left:6px solid {action_result.get('color', '#b3b9b3')}; padding:15px; border-radius:8px; margin-bottom:10px;">
                    <h4 style="color:#293a27; margin-bottom:8px;">{kpi.get('ward_name', 'Unknown')}</h4>
                    <div style="font-size:0.9em; margin-bottom:8px;"><strong>推奨アクション:</strong> {action_result.get('action', '要確認')}</div>
                    <div style="font-size:0.85em; color:#666;">{action_result.get('reasoning', '')}</div>
                    <div style="margin-top:8px; font-size:0.8em;">在院患者数: {kpi.get('daily_avg_census', 0):.1f}人 (達成率: {kpi.get('daily_census_achievement', 0):.1f}%)</div>
                    <div style="margin-top: 4px; font-size: 0.85em; font-weight: 600; color: {priority_color};">{priority_label}</div>
                    {bed_info_str}
                </div>""", unsafe_allow_html=True)
        
        return action_results, start_date, end_date, period_desc
    
    except Exception as e:
        logger.error(f"病棟簡易アクション表示エラー: {e}", exc_info=True)
        st.error(f"病棟簡易アクション表示中にエラーが発生しました: {str(e)}")
        return None, None, None, None

def create_ward_performance_tab():
    """病棟別パフォーマンスダッシュボードのメイン関数（最終修正版）"""
    st.header("🏨 病棟別パフォーマンスダッシュボード")

    if not st.session_state.get('data_processed', False):
        st.warning("📊 データを読み込むと、ここにダッシュボードが表示されます。")
        return
    
    df_original = st.session_state['df']
    target_data = st.session_state.get('target_data', pd.DataFrame())
    
    if not st.session_state.get('ward_mapping_initialized', False) and (target_data is not None and not target_data.empty): 
        create_ward_name_mapping(df_original, target_data)

    st.markdown("##### 表示指標の選択")
    tab_options = ["日平均在院患者数", "週合計新入院患者数", "平均在院日数（トレンド分析）", "アクション提案"]
    
    if 'selected_ward_tab_name' not in st.session_state:
        st.session_state.selected_ward_tab_name = tab_options[0]

    cols = st.columns(4)
    for i, option in enumerate(tab_options):
        button_type = "primary" if st.session_state.selected_ward_tab_name == option else "secondary"
        if cols[i].button(option, key=f"ward_tab_{i}", use_container_width=True, type=button_type):
            st.session_state.selected_ward_tab_name = option
            st.rerun()
            
    st.info(f"現在の表示: **{st.session_state.selected_ward_tab_name}**")
    st.markdown("---")

    period_options = ["直近4週間", "直近8週", "直近12週", "今年度", "先月", "昨年度"]
    selected_period = st.selectbox("📅 集計期間", period_options, index=0, key="ward_performance_period")

    # --- 選択されたタブに応じた表示ロジック（修正版） ---
    results_data = None
    try:
        selected_tab = st.session_state.selected_ward_tab_name
        
        if selected_tab == "アクション提案":
            results_data = display_action_dashboard(df_original, target_data, selected_period)
        else:
            results_data = display_metrics_dashboard(selected_tab, df_original, target_data, selected_period)
        
        if results_data is None or results_data[0] is None:
            st.warning("選択された条件のデータが存在しないか、KPI計算に失敗しました。")
            
    except Exception as e:
        logger.error(f"病棟ダッシュボード表示エラー: {e}", exc_info=True)
        st.error(f"病棟ダッシュボードの表示中にエラーが発生しました: {str(e)}")