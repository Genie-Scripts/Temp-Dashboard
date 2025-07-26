# department_performance_tab.py - 診療科別パフォーマンスダッシュボード（努力度表示版・トレンド分析対応）
# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import logging
from datetime import datetime
import calendar
from config import EXCLUDED_WARDS

logger = logging.getLogger(__name__)

# 既存のインポートに加えて詳細表示機能を追加
try:
    from unified_filters import get_unified_filter_config
    from unified_html_export import generate_unified_html_export
    from enhanced_streamlit_display import display_enhanced_action_dashboard
    from enhanced_action_analysis import generate_comprehensive_action_data
except ImportError as e:
    st.error(f"必要なモジュールのインポートに失敗しました: {e}")
    st.stop()

def get_mobile_report_generator():
    """mobile_report_generatorを遅延インポート"""
    try:
        from mobile_report_generator import generate_department_mobile_report
        return generate_department_mobile_report
    except ImportError as e:
        st.error(f"mobile_report_generator インポートエラー: {e}")
        return None

from utils import (
    safe_date_filter, get_display_name_for_dept, create_dept_mapping_table,
    get_period_dates, calculate_department_kpis, decide_action_and_reasoning,
    evaluate_feasibility, calculate_effect_simulation, calculate_los_appropriate_range,
    get_hospital_targets
)

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

def display_action_dashboard(df_original, target_data, selected_period):
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
    """診療科別パフォーマンスタブの作成（一括公開機能追加版）"""
    st.header("🏥 診療科別パフォーマンス")
    
    # データの確認
    if not st.session_state.get('data_processed', False) or st.session_state.get('df') is None:
        st.warning("データを読み込み後に利用可能になります。")
        return
    
    df_original = st.session_state['df']
    target_data = st.session_state.get('target_data', pd.DataFrame())

    if not st.session_state.get('dept_mapping_initialized', False) and (target_data is not None and not target_data.empty):
        create_dept_mapping_table(target_data)

    # スマホ向け個別レポート生成（既存のまま）
    st.markdown("---")
    st.subheader("📱 スマホ向け個別レポート生成（90日分析統合版）")
    
    # 新機能の説明を追加
    with st.expander("📖 モバイルレポートについて", expanded=False):
        st.markdown("""
        **🆕 90日分析統合版の特徴:**
        - 📊 診療科別の主要4指標をカード形式で表示
        - 📈 90日間のトレンドグラフ（3種類）
        - 🔍 現状分析と具体的なアクションプラン
        - 📱 スマートフォンでの閲覧に最適化
        - 🎯 努力度評価による動機付け
        
        **活用シーン:**
        - 週次の診療科会議での共有
        - 診療科長への定期報告
        - 改善活動の進捗確認
        """)

    try:
        # 診療科列の確認
        possible_cols = ['部門名', '診療科', '診療科名']
        dept_col = next((c for c in possible_cols if c in df_original.columns), None)
        
        if dept_col is None:
            st.error("データに診療科を示す列が見つかりません。レポートを生成できません。")
        else:
            # レポート生成設定
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 診療科選択
                dept_names = sorted(df_original[dept_col].unique())
                selected_dept_name = st.selectbox(
                    "📋 レポートを作成する診療科", 
                    dept_names, 
                    index=0, 
                    key="mobile_report_dept_select",
                    help="90日分析を含むモバイルレポートを生成する診療科を選択"
                )
            
            with col2:
                # 期間選択
                period_options_mobile = ["直近4週間", "直近8週", "直近12週", "今年度", "先月"]
                selected_period_mobile = st.selectbox(
                    "📅 集計期間", 
                    period_options_mobile, 
                    index=0, 
                    key="mobile_report_period_select",
                    help="メトリクスカードの集計期間（グラフは常に90日表示）"
                )

            # プレビューオプション
            col3, col4 = st.columns([1, 1])
            
            with col3:
                preview_mode = st.checkbox(
                    "🔍 プレビュー表示",
                    value=False,
                    key="mobile_report_preview",
                    help="生成後にプレビューを表示"
                )
            
            with col4:
                # 生成ボタン
                if st.button(
                    f"⚡ レポート生成", 
                    key="generate_mobile_report", 
                    use_container_width=True,
                    type="primary"
                ):
                    mobile_generator = get_mobile_report_generator()
                    if mobile_generator is None:
                        st.error("モバイルレポート生成機能が利用できません。")
                        return
                    
                    with st.spinner(f"{selected_dept_name}の90日分析レポートを生成中..."):
                        try:
                            # 期間計算
                            start_date, end_date, period_desc = get_period_dates(
                                df_original, selected_period_mobile
                            )
                            
                            if start_date is None or end_date is None:
                                st.error("期間の計算に失敗しました。")
                            else:
                                # データフィルタリング
                                df_filtered = safe_date_filter(df_original, start_date, end_date)
                                
                                if '病棟コード' in df_filtered.columns and EXCLUDED_WARDS:
                                    df_filtered = df_filtered[~df_filtered['病棟コード'].isin(EXCLUDED_WARDS)]
                                
                                # 診療科でフィルタリング（90日分のデータも含める）
                                # 90日前からのデータを取得
                                end_date_90d = df_original['日付'].max()
                                start_date_90d = end_date_90d - pd.Timedelta(days=89)
                                df_dept_90days = df_original[
                                    (df_original[dept_col] == selected_dept_name) &
                                    (df_original['日付'] >= start_date_90d) &
                                    (df_original['日付'] <= end_date_90d)
                                ]
                                
                                if '病棟コード' in df_dept_90days.columns and EXCLUDED_WARDS:
                                    df_dept_90days = df_dept_90days[~df_dept_90days['病棟コード'].isin(EXCLUDED_WARDS)]
                                
                                # KPI計算（選択期間のデータで）
                                dept_kpi_data = calculate_department_kpis(
                                    df_filtered,
                                    target_data,
                                    selected_dept_name,  # dept_code
                                    selected_dept_name,  # dept_name  
                                    start_date,
                                    end_date,
                                    dept_col
                                )

                                if dept_kpi_data and not df_dept_90days.empty:
                                    html_content = mobile_generator(
                                        dept_kpi=dept_kpi_data,
                                        period_desc=period_desc,
                                        df_dept_filtered=df_dept_90days,  # 90日分のデータ
                                        dept_name=selected_dept_name
                                    )
                                    
                                    # ファイル名とセッション保存
                                    filename = f"mobile_report_{selected_dept_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
                                    st.session_state['dl_mobile_report_html'] = html_content
                                    st.session_state['dl_mobile_report_name'] = filename
                                    
                                    st.success(f"✅ {selected_dept_name}の90日分析レポートが生成されました！")
                                    
                                    # プレビュー表示
                                    if preview_mode:
                                        st.markdown("### 📱 レポートプレビュー")
                                        # iframe での表示
                                        st.components.v1.html(
                                            html_content, 
                                            height=800, 
                                            scrolling=True
                                        )
                                    
                                else:
                                    if not dept_kpi_data:
                                        st.error(f"{selected_dept_name}のKPIデータの計算に失敗しました。")
                                    else:
                                        st.error(f"{selected_dept_name}の90日分のデータが不足しています。")
                                        
                        except Exception as e:
                            st.error(f"レポート生成中にエラーが発生しました: {str(e)}")

            # ダウンロードセクション（既存のまま）
            if 'dl_mobile_report_html' in st.session_state:
                st.markdown("---")
                col_dl1, col_dl2 = st.columns([2, 1])
                
                with col_dl1:
                    st.info(f"📄 生成済みファイル: {st.session_state['dl_mobile_report_name']}")
                
                with col_dl2:
                    st.download_button(
                        label="📥 ダウンロード",
                        data=st.session_state['dl_mobile_report_html'].encode("utf-8"),
                        file_name=st.session_state['dl_mobile_report_name'],
                        mime="text/html",
                        key="download_mobile_report_exec",
                        use_container_width=True,
                        type="primary"
                    )
                
                # 追加オプション
                with st.expander("🔧 追加オプション", expanded=False):
                    col_opt1, col_opt2 = st.columns(2)
                    
                    with col_opt1:
                        if st.button("📧 メール用HTML", key="generate_email_version"):
                            # インラインCSS版の生成（将来実装）
                            st.info("メール配信用のインラインCSS版は準備中です")
                    
                    with col_opt2:
                        if st.button("🖨️ 印刷用PDF", key="generate_pdf_version"):
                            # PDF変換機能（将来実装）
                            st.info("PDF変換機能は準備中です")

    except Exception as e:
        st.error(f"レポート生成機能でエラーが発生しました: {str(e)}")

    # 🆕 一括公開機能をここに追加
    st.markdown("---")
    st.subheader("🚀 全診療科スマホレポート一括公開（修正版）")
    
    with st.expander("📱 一括公開機能について", expanded=False):
        st.markdown("""
        **🆕 修正版の特徴:**
        - 🛡️ **GitHub API制限対策**: 3件ずつバッチ処理、5秒間隔
        - 💾 **メモリ監視**: 使用量800MB超でクリーンアップ
        - 🔄 **自動リトライ**: 失敗時最大2回まで再試行
        - 📊 **詳細進捗表示**: リアルタイム状況とエラーレポート
        - ⚡ **処理安定性**: 大幅に向上した継続処理能力
        
        **処理時間の目安:**
        - 診療科数 × 1.5分程度（API制限により変動）
        - 例：20診療科 ≈ 30分程度
        """)
    
    # 一括公開の設定と実行
    col_batch1, col_batch2, col_batch3 = st.columns([2, 1, 1])
    
    with col_batch1:
        batch_period = st.selectbox(
            "📅 一括生成期間",
            ["直近4週間", "直近8週", "直近12週", "先月", "今年度"],
            index=0,
            key="batch_period_select",
            help="全診療科レポートの集計期間"
        )
    
    with col_batch2:
        # GitHub設定確認
        github_settings = st.session_state.get('github_settings', {})
        github_token = github_settings.get('token', '')
        if github_token:
            st.success("🔑 GitHub設定済み")
        else:
            st.error("🔑 GitHub未設定")
            st.caption("設定画面で設定してください")
    
    with col_batch3:
        # 対象診療科数表示
        if dept_col and dept_col in df_original.columns:
            dept_count = len(df_original[dept_col].dropna().unique())
            estimated_time = (dept_count // 3) * 5  # 分単位推定
            st.metric("対象診療科", f"{dept_count}件")
            st.caption(f"推定時間: {estimated_time}分")
        else:
            st.metric("対象診療科", "不明")
    
    # 実行ボタンと詳細設定
    col_exec1, col_exec2 = st.columns([2, 1])
    
    with col_exec1:
        # メイン実行ボタン
        if st.button(
            "🚀 全診療科レポート一括公開（修正版）", 
            key="batch_publish_fixed",
            disabled=not github_token,
            type="primary",
            use_container_width=True
        ):
            if not github_token:
                st.error("🔑 GitHub設定が必要です。設定画面でトークンとリポジトリを設定してください。")
                return
            
            # 修正版一括公開を実行
            try:
                # 必要なモジュールのインポート
                from html_export_functions import publish_all_mobile_reports_fixed
                
                # GitHubパブリッシャーの動的インポートと初期化
                try:
                    from github_publisher import GitHubPublisher
                    publisher = GitHubPublisher(
                        token=github_settings.get('token'),
                        repo_name=github_settings.get('repo_name'),
                        branch=github_settings.get('branch', 'gh-pages')
                    )
                except ImportError:
                    st.error("❌ GitHub公開機能が利用できません。github_publisher.pyが必要です。")
                    return
                except Exception as pub_init_error:
                    st.error(f"❌ GitHubパブリッシャーの初期化に失敗しました: {pub_init_error}")
                    return
                
                # 一括公開実行（修正版）
                st.info("🔄 修正版一括公開を開始します...")
                success = publish_all_mobile_reports_fixed(
                    df=df_original,
                    target_data=target_data,
                    publisher=publisher,
                    period=batch_period
                )
                
                # 結果表示
                if success:
                    st.success("🎉 一括公開が正常に完了しました！")
                    
                    # 公開URLの表示
                    if hasattr(publisher, 'repo_name') and publisher.repo_name:
                        repo_name = publisher.repo_name
                        username = github_settings.get('username', 'your-username')
                        pages_url = f"https://{username}.github.io/{repo_name}/"
                        st.success(f"🌐 公開サイト: [診療科別レポート一覧]({pages_url})")
                else:
                    st.warning("⚠️ 一括公開は完了しましたが、一部でエラーが発生しました。詳細は上記のログを確認してください。")
                    
            except ImportError as import_error:
                st.error(f"❌ 必要なモジュールのインポートに失敗しました: {import_error}")
                st.info("💡 html_export_functions.py に修正版関数が追加されているか確認してください。")
            except Exception as publish_error:
                st.error(f"❌ 一括公開でエラーが発生しました: {publish_error}")
                st.code(traceback.format_exc())
    
    with col_exec2:
        # テスト実行ボタン
        if st.button(
            "🧪 テスト実行（5診療科）",
            key="test_batch_publish",
            disabled=not github_token,
            help="最初の5診療科のみでテスト実行"
        ):
            if github_token:
                st.info("🧪 テスト実行機能は開発中です")
                # TODO: テスト実行の実装
            else:
                st.error("🔑 GitHub設定が必要です")
    
    # 使用上の注意とヒント
    with st.expander("⚠️ 使用上の注意とトラブルシューティング", expanded=False):
        st.markdown("""
        ### 📋 事前準備チェックリスト
        - ✅ GitHub Personal Access Token が設定済み
        - ✅ リポジトリ名が正しく設定されている  
        - ✅ GitHub Pages が有効化されている
        - ✅ インターネット接続が安定している
        
        ### ⚡ 処理中の注意点
        - **タブを閉じないでください**: 処理が中断されます
        - **他の操作は控えめに**: メモリ使用量が増加します
        - **完了まで待機**: GitHub API制限により時間がかかります
        
        ### 🔧 トラブル対処法
        
        **❌ 7件で停止する場合:**
        1. ページを再読み込みして再実行
        2. ブラウザのメモリをクリア（タブを閉じる）
        3. 時間をおいて再実行（API制限解除待ち）
        
        **❌ GitHub接続エラー:**
        1. トークンの有効期限を確認
        2. リポジトリのアクセス権限を確認
        3. ネットワーク接続を確認
        
        **❌ メモリ不足エラー:**
        1. 他のタブやアプリケーションを閉じる
        2. 少量ずつ実行する
        3. ブラウザを再起動
        
        ### 📞 サポート
        問題が解決しない場合は、エラーメッセージとログを保存してサポートに連絡してください。
        """)
    
    st.markdown("---")

def create_mobile_integrated_report(df_original, target_data, selected_period):
    """モバイル統合レポート作成機能"""
    try:
        st.markdown("### 📱 診療科別モバイル統合レポート")
        st.markdown("スマートフォン対応の統合レポートを生成します")
        
        # 診療科選択
        start_date, end_date, period_desc = get_period_dates(df_original, selected_period)
        if start_date is None or end_date is None:
            st.error("期間の計算に失敗しました。")
            return None
        
        date_filtered_df = safe_date_filter(df_original, start_date, end_date)
        if '病棟コード' in date_filtered_df.columns and EXCLUDED_WARDS:
            date_filtered_df = date_filtered_df[~date_filtered_df['病棟コード'].isin(EXCLUDED_WARDS)]
        
        if date_filtered_df.empty:
            st.warning(f"選択された期間（{period_desc}）にデータがありません。")
            return None
        
        # 診療科リストの取得
        possible_cols = ['部門名', '診療科', '診療科名']
        dept_col = next((c for c in possible_cols if c in date_filtered_df.columns), None)
        if dept_col is None:
            st.error("診療科列が見つかりません。")
            return None
        
        unique_depts = sorted(date_filtered_df[dept_col].unique())
        
        # UI作成
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_dept = st.selectbox(
                "📋 診療科を選択",
                options=unique_depts,
                key="mobile_dept_selector",
                help="モバイルレポートを生成する診療科を選択"
            )
        
        with col2:
            if st.button("📱 レポート生成", key="generate_mobile_report", use_container_width=True):
                with st.spinner("モバイルレポートを生成中..."):
                    # 選択された診療科のKPIデータを取得
                    kpi_data = calculate_department_kpis(
                        date_filtered_df, target_data, selected_dept, selected_dept,
                        start_date, end_date, dept_col
                    )
                    
                    if kpi_data:
                        # モバイル対応HTMLを生成
                        mobile_html = generate_mobile_department_html(
                            selected_dept, kpi_data, period_desc
                        )
                        
                        if mobile_html:
                            # プレビュー表示
                            st.success("✅ モバイルレポートが生成されました")
                            
                            # ダウンロードボタン
                            filename = f"mobile_dept_{selected_dept}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
                            st.download_button(
                                label="📥 モバイルレポートをダウンロード",
                                data=mobile_html.encode('utf-8'),
                                file_name=filename,
                                mime="text/html",
                                key="download_mobile_report",
                                use_container_width=True
                            )
                            
                            # プレビュー表示（オプション）
                            if st.checkbox("🔍 プレビュー表示", key="show_mobile_preview"):
                                st.components.v1.html(mobile_html, height=400, scrolling=True)
                        else:
                            st.error("❌ HTMLの生成に失敗しました")
                    else:
                        st.error("❌ KPIデータの取得に失敗しました")
        
        # 使用方法ガイド
        with st.expander("📖 使用方法ガイド", expanded=False):
            st.markdown("""
            **📱 モバイル統合レポートの特徴:**
            
            - **📊 3指標統合**: 在院患者数、新入院数、平均在院日数を1画面に表示
            - **📱 スマートフォン最適化**: 縦画面での閲覧に最適化されたデザイン
            - **📈 トレンド分析**: 期間内の推移を視覚的に表示
            - **🎯 現状分析**: 目標達成状況と改善点を自動分析
            - **💡 アクションプラン**: 具体的な改善提案を自動生成
            - **📴 オフライン対応**: ダウンロード後はインターネット接続不要
            
            **📋 活用場面:**
            
            - 🏥 病棟回診時の現状確認
            - 📊 管理会議での報告資料
            - 🎯 改善活動の進捗確認
            - 📝 週次レポートの作成
            - 📱 外出先での状況確認
            """)
        
        return {"selected_dept": selected_dept, "kpi_data": kpi_data if 'kpi_data' in locals() else None}
        
    except Exception as e:
        logger.error(f"モバイル統合レポート作成エラー: {e}", exc_info=True)
        st.error(f"モバイル統合レポートの作成中にエラーが発生しました: {str(e)}")
        return None

def generate_mobile_department_html(dept_name, kpi_data, period_desc):
    """モバイル対応診療科別HTML生成"""
    try:
        # 基本的なHTMLテンプレート（モックアップベース）
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{dept_name} - 週次レポート</title>
            <style>
                {get_mobile_css_styles()}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🏥 {dept_name} 週次レポート</h1>
                <p>{period_desc}</p>
            </div>
            
            <div class="container">
                <!-- サマリーカード -->
                <div class="summary-cards">
                    <div class="summary-card {get_achievement_class(kpi_data.get('daily_census_achievement', 0))}">
                        <h3>在院患者数</h3>
                        <div class="value">{kpi_data.get('daily_avg_census', 0):.1f}</div>
                        <div class="target">目標: {kpi_data.get('daily_census_target', 0) or '--'}人</div>
                        <div class="trend trend-up">📈 {kpi_data.get('recent_week_daily_census', 0) - kpi_data.get('daily_avg_census', 0):+.1f}人</div>
                    </div>
                    <div class="summary-card card-good">
                        <h3>新入院</h3>
                        <div class="value">{kpi_data.get('weekly_avg_admissions', 0):.0f}</div>
                        <div class="target">週間実績</div>
                        <div class="trend trend-stable">➡️ 安定</div>
                    </div>
                    <div class="summary-card card-warning">
                        <h3>平均在院日数</h3>
                        <div class="value">{kpi_data.get('avg_length_of_stay', 0):.1f}</div>
                        <div class="target">日</div>
                        <div class="trend trend-down">📉 {kpi_data.get('recent_week_avg_los', 0) - kpi_data.get('avg_length_of_stay', 0):+.1f}日</div>
                    </div>
                </div>
                
                <!-- 現状分析 -->
                <div class="section">
                    <h2>🔍 現状分析</h2>
                    <p><strong>🔴 課題:</strong> {generate_status_analysis(kpi_data)}</p>
                    <p><strong>📈 トレンド:</strong> {generate_trend_analysis(kpi_data)}</p>
                    <p><strong>💡 チャンス:</strong> {generate_opportunity_analysis(kpi_data)}</p>
                </div>
                
                <!-- アクションプラン -->
                <div class="section">
                    <h2>🎯 今週のアクションプラン</h2>
                    <ul class="action-list">
                        {generate_action_plan_items(kpi_data)}
                    </ul>
                </div>
                
                <!-- 期待効果 -->
                <div class="section">
                    <h2>📈 期待効果</h2>
                    <p>{generate_expected_effects(kpi_data)}</p>
                </div>
            </div>
            
            <!-- フローティングボタン -->
            <div class="fab">🏠</div>
        </body>
        </html>
        """
        
        return html_content
        
    except Exception as e:
        logger.error(f"モバイルHTML生成エラー: {e}")
        return None

def get_mobile_css_styles():
    """モバイル対応CSSスタイル"""
    return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans JP', sans-serif;
            background: #f5f7fa; 
            color: #333;
            line-height: 1.6;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 16px;
            text-align: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }
        .header h1 { font-size: 1.4em; margin-bottom: 4px; }
        .header p { font-size: 0.9em; opacity: 0.9; }
        
        .container { 
            max-width: 100%;
            padding: 16px;
            margin-bottom: 60px;
        }
        
        .summary-cards {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 20px;
        }
        .summary-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .summary-card h3 {
            font-size: 0.85em;
            color: #666;
            margin-bottom: 8px;
        }
        .summary-card .value {
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 4px;
        }
        .summary-card .target {
            font-size: 0.8em;
            color: #999;
        }
        
        .card-good .value { color: #4CAF50; }
        .card-warning .value { color: #FF9800; }
        .card-danger .value { color: #F44336; }
        
        .section {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: #667eea;
            font-size: 1.1em;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .action-list {
            list-style: none;
            margin: 0;
        }
        .action-list li {
            background: #f8f9fa;
            margin-bottom: 8px;
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            font-size: 0.9em;
        }
        .action-list .priority {
            color: #667eea;
            font-weight: bold;
            font-size: 0.8em;
        }
        
        .trend {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 0.8em;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .trend-up { background: #fff3cd; color: #856404; }
        .trend-down { background: #d1ecf1; color: #0c5460; }
        .trend-stable { background: #d4edda; color: #155724; }
        
        .fab {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 56px;
            height: 56px;
            background: #667eea;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.5em;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        @media (max-width: 480px) {
            .summary-cards {
                grid-template-columns: 1fr;
                gap: 8px;
            }
            .container {
                padding: 12px;
            }
            .section {
                padding: 16px;
            }
            .header h1 {
                font-size: 1.2em;
            }
        }
    """

def get_achievement_class(achievement):
    """達成率に基づくCSSクラス取得"""
    if achievement >= 95:
        return "card-good"
    elif achievement >= 85:
        return "card-warning"
    else:
        return "card-danger"

def generate_status_analysis(kpi_data):
    """現状分析テキスト生成"""
    target = kpi_data.get('daily_census_target', 0)
    current = kpi_data.get('daily_avg_census', 0)
    if target and current:
        gap = target - current
        if gap > 0:
            return f"目標まで{gap:.1f}人不足"
        else:
            return f"目標を{abs(gap):.1f}人超過"
    return "目標値未設定"

def generate_trend_analysis(kpi_data):
    """トレンド分析テキスト生成"""
    recent = kpi_data.get('recent_week_daily_census', 0)
    avg = kpi_data.get('daily_avg_census', 0)
    if recent > avg:
        return f"直近週は改善傾向（+{recent - avg:.1f}人）"
    elif recent < avg:
        return f"直近週は減少傾向（{recent - avg:.1f}人）"
    else:
        return "直近週は横ばい"

def generate_opportunity_analysis(kpi_data):
    """チャンス分析テキスト生成"""
    admissions = kpi_data.get('weekly_avg_admissions', 0)
    if admissions > 0:
        return "新入院数が安定、在院日数に調整余地"
    return "データ分析に基づく改善機会を検討"

def generate_action_plan_items(kpi_data):
    """アクションプランアイテム生成"""
    items = []
    
    # 在院患者数の状況に基づいて
    achievement = kpi_data.get('daily_census_achievement', 0)
    if achievement < 95:
        items.append('<li><div class="priority">優先度: 高</div>救急外来との連携強化 - 新入院患者の確保</li>')
        items.append('<li><div class="priority">優先度: 中</div>退院調整カンファレンスの実施頻度UP</li>')
    else:
        items.append('<li><div class="priority">優先度: 低</div>現状維持 - 良好な状況を継続</li>')
    
    items.append('<li><div class="priority">優先度: 中</div>地域医療機関への病診連携促進</li>')
    
    return '\n'.join(items)

def generate_expected_effects(kpi_data):
    """期待効果テキスト生成"""
    target = kpi_data.get('daily_census_target', 0)
    current = kpi_data.get('daily_avg_census', 0)
    
    if target and current:
        gap = target - current
        if gap > 0:
            return f"💡 <strong>新入院週1人増加</strong> → 約{gap * 0.5:.1f}人増加効果<br>🎯 実行により<strong>目標達成率90%以上</strong>を期待"
        else:
            return "🎯 <strong>現状維持により安定した運営を継続</strong>"
    
    return "💡 <strong>データ分析に基づく継続的改善</strong>"