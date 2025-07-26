# enhanced_streamlit_display.py - Streamlit用詳細アクション表示（目標達成努力度版）

import streamlit as st
import pandas as pd
import logging
from enhanced_action_analysis import (
    generate_comprehensive_action_data, 
    format_feasibility_details,
    get_action_priority_badge,
    get_effort_status_badge,
    generate_action_summary_text
)

logger = logging.getLogger(__name__)

def safe_progress_bar(value, caption_text="", show_percentage=True):
    """
    安全なプログレスバー表示関数
    負の値や1.0を超える値を自動的に調整
    """
    try:
        # 値の安全な変換
        if value is None or pd.isna(value):
            safe_value = 0.0
            status_text = "データなし"
        elif value < 0:
            safe_value = 0.0
            status_text = f"効果なし (元値: {value:.2f})"
        elif value > 1.0:
            safe_value = 1.0
            status_text = f"100%以上 (元値: {value:.2f})"
        else:
            safe_value = float(value)
            status_text = f"{safe_value*100:.1f}%" if show_percentage else ""
        
        # プログレスバー表示
        st.progress(safe_value)
        
        # キャプション表示
        if caption_text:
            if status_text and show_percentage:
                st.caption(f"{caption_text}: {status_text}")
            else:
                st.caption(caption_text)
        elif status_text:
            st.caption(status_text)
            
        return safe_value
        
    except Exception as e:
        logger.error(f"プログレスバー表示エラー: {e}")
        st.caption("進捗表示でエラーが発生しました")
        return 0.0

def display_enhanced_action_dashboard(df_original, target_data, selected_period):
    """
    詳細アクション提案ダッシュボード（目標達成努力度版）
    """
    try:
        # 既存のデータ準備ロジックを使用
        from department_performance_tab import (
            get_hospital_targets, get_period_dates, safe_date_filter,
            calculate_department_kpis, evaluate_feasibility, 
            calculate_effect_simulation
        )
        from config import EXCLUDED_WARDS
        
        if target_data is not None and not target_data.empty:
            from utils import create_dept_mapping_table
            create_dept_mapping_table(target_data)
        
        hospital_targets = get_hospital_targets(target_data)
        
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
        
        possible_cols = ['部門名', '診療科', '診療科名']
        dept_col = next((c for c in possible_cols if c in date_filtered_df.columns), None)
        if dept_col is None:
            st.error(f"診療科列が見つかりません。")
            return None

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

        st.markdown("### 🏥 診療科別詳細アクション提案（目標達成努力度版）")
        
        # 詳細分析データ生成
        unique_depts = date_filtered_df[dept_col].unique()
        enhanced_action_results = []
        
        for dept_code in unique_depts:
            dept_name = dept_code
            kpi = calculate_department_kpis(date_filtered_df, target_data, dept_code, dept_name, start_date, end_date, dept_col)
            
            if kpi:
                dept_df = date_filtered_df[date_filtered_df[dept_col] == dept_code]
                feasibility = evaluate_feasibility(kpi, dept_df, start_date, end_date)
                simulation = calculate_effect_simulation(kpi)
                
                # 詳細分析データ生成
                comprehensive_data = generate_comprehensive_action_data(
                    kpi, feasibility, simulation, hospital_targets
                )
                
                if comprehensive_data:
                    enhanced_action_results.append(comprehensive_data)
        
        if not enhanced_action_results:
            st.warning("表示可能な診療科データがありません。")
            return None
        
        # 優先度とサイズでソート
        priority_order = {"urgent": 0, "medium": 1, "low": 2}
        enhanced_action_results.sort(key=lambda x: (
            priority_order.get(x['basic_action'].get('priority', 'low'), 2),
            -x['basic_info']['current_census']
        ))
        
        # 詳細カード表示
        for result in enhanced_action_results:
            _display_detailed_action_card(result)
        
        return enhanced_action_results, start_date, end_date, period_desc
    
    except Exception as e:
        logger.error(f"詳細アクション表示エラー: {e}", exc_info=True)
        st.error(f"詳細アクション表示中にエラーが発生しました: {str(e)}")
        return None

def _display_detailed_action_card(comprehensive_data):
    """詳細アクションカードの表示（目標達成努力度版）"""
    try:
        basic_info = comprehensive_data['basic_info']
        effort_status = comprehensive_data['effort_status']  # 変更：貢献度→努力度
        analysis = comprehensive_data['current_analysis']
        feasibility = comprehensive_data['feasibility_evaluation']
        simulation = comprehensive_data['effect_simulation']
        action = comprehensive_data['basic_action']
        expected_effect = comprehensive_data['expected_effect']
        
        # メインカードコンテナ
        with st.container():
            # カードヘッダー（努力度表示に変更）
            action_color = action.get('color', '#b3b9b3')
            priority_badge = get_action_priority_badge(action.get('priority', 'low'))
            effort_badge = get_effort_status_badge(effort_status)
            
            # カスタムCSS付きのヘッダー
            st.markdown(f"""
            <div style="
                background: linear-gradient(90deg, {effort_status['color']}15 0%, {effort_status['color']}05 100%);
                border-left: 6px solid {effort_status['color']};
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3 style="color: #293a27; margin: 0;">{basic_info['dept_name']}</h3>
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
            
            # メトリクス表示（エラーハンドリング付き）
            try:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    census_delta_color = "normal" if basic_info['census_achievement'] >= 95 else "inverse"
                    target_display = f"{basic_info['census_target']:.1f}" if basic_info['census_target'] else "--"
                    st.metric(
                        "在院患者数",
                        f"{basic_info['current_census']:.1f}人",
                        f"目標: {target_display}人",
                        delta_color=census_delta_color
                    )
                
                with col2:
                    st.metric(
                        "達成率",
                        f"{basic_info['census_achievement']:.1f}%",
                        analysis['census_status']
                    )
                
                with col3:
                    delta_value = basic_info['recent_week_census'] - basic_info['current_census']
                    st.metric(
                        "直近週実績",
                        f"{basic_info['recent_week_census']:.1f}人",
                        f"{delta_value:+.1f}人"
                    )
                
                with col4:
                    st.metric(
                        "努力度評価",
                        effort_status['level'],
                        effort_status['status']
                    )
                    
            except Exception as e:
                logger.error(f"メトリクス表示エラー: {e}")
                st.error("メトリクス表示でエラーが発生しました")
            
            # タブ式詳細情報（エラーハンドリング付き）
            try:
                tab1, tab2, tab3, tab4 = st.tabs(["📊 現状分析", "⚙️ 実現可能性", "📈 効果予測", "🎯 推奨アクション"])
                
                with tab1:
                    _display_current_analysis_safe(basic_info, analysis)
                
                with tab2:
                    _display_feasibility_analysis_safe(feasibility)
                
                with tab3:
                    _display_simplified_simulation_analysis_safe(simulation)  # 変更：簡素化版
                
                with tab4:
                    _display_action_recommendation_safe(action, expected_effect)
                    
            except Exception as e:
                logger.error(f"タブ表示エラー: {e}")
                st.error("詳細情報表示でエラーが発生しました")
                
    except Exception as e:
        logger.error(f"詳細アクションカード表示エラー: {e}")
        st.error(f"カード表示でエラーが発生しました: {str(e)}")
        
        # フォールバック: 基本情報のみ表示
        try:
            dept_name = comprehensive_data.get('basic_info', {}).get('dept_name', 'Unknown')
            action_text = comprehensive_data.get('basic_action', {}).get('action', 'データ不足')
            effort_text = comprehensive_data.get('effort_status', {}).get('status', '評価不能')
            st.warning(f"⚠️ {dept_name}: {effort_text} | {action_text}（詳細表示エラーのため簡易表示）")
        except:
            st.error("データ表示でエラーが発生しました")

def _display_current_analysis_safe(basic_info, analysis):
    """現状分析タブの表示（安全版）"""
    try:
        _display_current_analysis(basic_info, analysis)
    except Exception as e:
        logger.error(f"現状分析表示エラー: {e}")
        st.error("現状分析の表示でエラーが発生しました")

def _display_feasibility_analysis_safe(feasibility):
    """実現可能性分析タブの表示（安全版）"""
    try:
        _display_feasibility_analysis(feasibility)
    except Exception as e:
        logger.error(f"実現可能性分析表示エラー: {e}")
        st.error("実現可能性分析の表示でエラーが発生しました")

def _display_simplified_simulation_analysis_safe(simulation):
    """簡素化効果予測タブの表示（安全版）"""
    try:
        _display_simplified_simulation_analysis(simulation)
    except Exception as e:
        logger.error(f"簡素化効果予測表示エラー: {e}")
        st.error("効果予測の表示でエラーが発生しました")

def _display_action_recommendation_safe(action, expected_effect):
    """推奨アクションタブの表示（安全版）"""
    try:
        _display_action_recommendation(action, expected_effect)
    except Exception as e:
        logger.error(f"推奨アクション表示エラー: {e}")
        st.error("推奨アクションの表示でエラーが発生しました")

def _display_current_analysis(basic_info, analysis):
    """現状分析タブの表示"""
    st.markdown("#### 📋 指標別現状")
    
    # 在院患者数分析
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**在院患者数動向**")
        census_gap = analysis['census_gap']
        gap_color = "🟢" if census_gap >= 0 else "🔴"
        st.markdown(f"• 目標との差: {gap_color} {census_gap:+.1f}人")
        st.markdown(f"• 達成状況: {analysis['census_status']}")
    
    with col2:
        st.markdown("**新入院動向**")
        st.markdown(f"• 期間平均: {basic_info['admission_avg']:.1f}人/日")
        st.markdown(f"• 直近週: {basic_info['admission_recent']:.1f}人/日")
        st.markdown(f"• トレンド: {analysis['admission_trend']}")
    
    # 在院日数分析
    st.markdown("**在院日数動向**")
    col3, col4 = st.columns(2)
    with col3:
        st.markdown(f"• 期間平均: {basic_info['los_avg']:.1f}日")
        st.markdown(f"• 直近週: {basic_info['los_recent']:.1f}日")
        st.markdown(f"• 評価: {analysis['los_status']} {analysis['los_assessment']}")
    
    with col4:
        if analysis['los_range']:
            los_range = analysis['los_range']
            st.markdown("**適正範囲**")
            st.markdown(f"• 下限: {los_range['lower']:.1f}日")
            st.markdown(f"• 上限: {los_range['upper']:.1f}日")
            
            # 進捗バー表示
            if basic_info['los_recent'] > 0:
                range_min = los_range['lower']
                range_max = los_range['upper']
                current_los = basic_info['los_recent']
                
                if current_los < range_min:
                    progress = 0
                    color = "🔵"
                elif current_los > range_max:
                    progress = 1
                    color = "🔴"
                else:
                    progress = (current_los - range_min) / (range_max - range_min)
                    color = "🟢"
                
                st.progress(progress)
                st.caption(f"{color} 現在値: {current_los:.1f}日")

def _display_feasibility_analysis(feasibility):
    """実現可能性分析タブの表示"""
    st.markdown("#### ⚙️ 改善施策の実現可能性")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**新入院増加施策**")
        adm_feas = feasibility['admission_feasibility']
        
        # スコア表示
        score_color = "🟢" if adm_feas['score'] >= 2 else "🟡" if adm_feas['score'] >= 1 else "🔴"
        st.markdown(f"• 実現可能性: {score_color} {adm_feas['assessment']}")
        st.markdown(f"• スコア: {adm_feas['score']}/2")
        
        # 詳細要因
        if adm_feas['details']:
            st.markdown("**評価要因:**")
            for factor, status in adm_feas['details'].items():
                emoji = "✅" if status else "❌"
                st.markdown(f"• {emoji} {factor}")
    
    with col2:
        st.markdown("**在院日数調整施策**")
        los_feas = feasibility['los_feasibility']
        
        # スコア表示
        score_color = "🟢" if los_feas['score'] >= 2 else "🟡" if los_feas['score'] >= 1 else "🔴"
        st.markdown(f"• 実現可能性: {score_color} {los_feas['assessment']}")
        st.markdown(f"• スコア: {los_feas['score']}/2")
        
        # 詳細要因
        if los_feas['details']:
            st.markdown("**評価要因:**")
            for factor, status in los_feas['details'].items():
                emoji = "✅" if status else "❌"
                st.markdown(f"• {emoji} {factor}")

def _display_simplified_simulation_analysis(simulation):
    """簡素化された効果予測タブの表示"""
    try:
        st.markdown("#### 📈 効果シミュレーション")
        
        if not simulation.get('is_simplified', False) or simulation.get('error', False):
            st.info("📝 シミュレーションデータが準備中です")
            return
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**📈 新入院増加案**")
            adm_scenario = simulation['admission_scenario']
            st.markdown(f"• {adm_scenario['description']}")
            st.markdown(f"• 予想効果: **+{adm_scenario['effect']:.1f}人**")
            
            # 効果の視覚的表示
            if adm_scenario['effect'] > 0:
                st.success(f"✅ 週1人増 → 日平均+{adm_scenario['effect']:.1f}人")
            else:
                st.warning("⚠️ 効果が期待できません")
        
        with col2:
            st.markdown("**📊 在院日数延長案**")
            los_scenario = simulation['los_scenario'] 
            st.markdown(f"• {los_scenario['description']}")
            st.markdown(f"• 予想効果: **+{los_scenario['effect']:.1f}人**")
            
            # 効果の視覚的表示
            if los_scenario['effect'] > 0:
                st.success(f"✅ 1日延長 → 日平均+{los_scenario['effect']:.1f}人")
            else:
                st.warning("⚠️ 効果が期待できません")
        
        # 現状分析情報の表示（簡素化）
        current_status = simulation.get('current_status', {})
        if current_status:
            with st.expander("📊 現状分析の詳細", expanded=False):
                theoretical = current_status.get('theoretical_census', 0)
                actual = current_status.get('actual_census', 0)
                variance = current_status.get('variance', 0)
                
                st.markdown(f"""
                **現状分析：**
                - 計算値: {theoretical:.1f}人
                - 実績値: {actual:.1f}人  
                - 差異: {variance:+.1f}人
                """)
            
    except Exception as e:
        logger.error(f"効果予測表示エラー: {e}")
        st.error("効果予測の表示でエラーが発生しました")

def _display_action_recommendation(action, expected_effect):
    """推奨アクションタブの表示"""
    st.markdown("#### 🎯 推奨アクションプラン")
    
    # アクション概要
    action_color = action.get('color', '#b3b9b3')
    st.markdown(f"""
    <div style="
        background: {action_color}15;
        border: 2px solid {action_color};
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    ">
        <h4 style="color: {action_color}; margin-bottom: 10px;">🎯 {action['action']}</h4>
        <p style="margin: 0; color: #333; line-height: 1.5;">{action['reasoning']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 期待効果
    st.markdown("**💎 期待効果**")
    effect_status = expected_effect.get('status', 'unknown')
    
    if effect_status == 'achieved':
        st.success("✅ " + expected_effect['description'])
    elif effect_status == 'potential':
        st.info("📈 " + expected_effect['description'])
        if 'contribution_percentage' in expected_effect:
            contrib = expected_effect['contribution_percentage']
            # 安全なプログレスバー表示
            contrib_ratio = contrib / 100 if contrib is not None else 0
            safe_progress_bar(contrib_ratio, f"病院全体改善への貢献度: {contrib:.1f}%", show_percentage=False)
    else:
        st.info("🔄 " + expected_effect['description'])
    
    # 次のステップ
    st.markdown("**📋 具体的な次のステップ**")
    action_type = action['action']
    
    if action_type == "新入院重視":
        st.markdown("""
        1. 🏥 外来からの入院適応の見直し
        2. 📞 地域連携の強化
        3. 📊 入院待機患者の把握
        4. ⏰ 入院可能枠の拡大検討
        """)
    elif action_type == "在院日数調整":
        st.markdown("""
        1. 📋 退院基準の見直し
        2. 🤝 多職種カンファレンスの充実
        3. 🏠 在宅移行支援の強化
        4. 📈 クリニカルパスの最適化
        """)
    elif action_type == "両方検討":
        st.markdown("""
        1. 🎯 緊急性の高い施策の優先実施
        2. 📊 データ収集・分析の強化
        3. 👥 多職種での改善チーム編成
        4. 📅 定期的な進捗確認の設定
        """)
    else:
        st.markdown("""
        1. 📊 現状の継続的監視
        2. 📈 トレンド分析の定期実施
        3. 🔍 潜在的課題の早期発見
        4. 📋 予防的対策の準備
        """)