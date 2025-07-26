# ui/pages/department_page.py (期間選択機能追加版)
"""
診療科別分析ページモジュール
特定診療科の詳細分析を表示（期間選択機能追加）
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, Any, Optional
import logging

from ui.session_manager import SessionManager
from ui.error_handler import safe_streamlit_operation, safe_data_operation
from ui.components.period_selector import PeriodSelector

# 既存の分析モジュールをインポート
from analysis import weekly, ranking, surgeon
from plotting import trend_plots, generic_plots

logger = logging.getLogger(__name__)


class DepartmentPage:
    """診療科別分析ページクラス"""
    
    @staticmethod
    @safe_streamlit_operation("診療科別分析ページ描画")
    def render() -> None:
        """診療科別分析ページを描画"""
        st.title("🩺 診療科別分析")
        
        # データ取得
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        latest_date = SessionManager.get_latest_date()
        
        if df.empty:
            st.warning("⚠️ データが読み込まれていません")
            return
        
        # 診療科選択
        selected_dept = DepartmentPage._render_department_selector(df)
        if not selected_dept:
            return
        
        st.markdown("---")
        
        # 期間選択セクション
        period_name, start_date, end_date = PeriodSelector.render(
            page_name=f"department_{selected_dept}",
            show_info=True,
            key_suffix=f"dept_{selected_dept}"
        )
        
        # 期間に基づいてデータをフィルタリング
        filtered_df = PeriodSelector.filter_data_by_period(df, start_date, end_date)
        
        # 選択された診療科のデータを抽出
        dept_df = filtered_df[filtered_df['実施診療科'] == selected_dept]
        
        if dept_df.empty:
            st.warning(f"⚠️ {selected_dept}の選択期間（{period_name}）にデータがありません")
            return
        
        # 期間サマリー表示（診療科特化）
        if start_date and end_date:
            st.markdown("---")
            DepartmentPage._render_department_period_summary(
                selected_dept, period_name, start_date, end_date, dept_df
            )
        
        st.markdown("---")
        
        # KPI表示
        DepartmentPage._render_department_kpi(dept_df, start_date, end_date, selected_dept)
        
        # 週次推移
        DepartmentPage._render_department_trend(
            filtered_df, target_dict, selected_dept, period_name
        )
        
        # 詳細分析タブ
        DepartmentPage._render_detailed_analysis_tabs(dept_df, selected_dept, period_name)
    
    @staticmethod
    def _render_department_selector(df: pd.DataFrame) -> Optional[str]:
        """診療科選択UI"""
        departments = sorted(df["実施診療科"].dropna().unique())
        
        if not departments:
            st.warning("データに診療科情報がありません。")
            return None
        
        # セッションから前回選択を取得
        prev_selected = st.session_state.get("selected_department", departments[0])
        try:
            default_index = departments.index(prev_selected)
        except ValueError:
            default_index = 0
        
        selected_dept = st.selectbox(
            "分析する診療科を選択",
            departments,
            index=default_index,
            help="分析対象の診療科を選択してください",
            key="department_selector"
        )
        
        # セッションに保存
        st.session_state["selected_department"] = selected_dept
        
        return selected_dept
    
    @staticmethod
    def _render_department_period_summary(dept_name: str,
                                        period_name: str, 
                                        start_date: pd.Timestamp, 
                                        end_date: pd.Timestamp,
                                        dept_df: pd.DataFrame) -> None:
        """診療科特化期間サマリー情報を表示"""
        period_info = PeriodSelector.get_period_info(period_name, start_date, end_date)
        
        # 全身麻酔20分以上の件数
        gas_cases = len(dept_df[dept_df['is_gas_20min']]) if 'is_gas_20min' in dept_df.columns else len(dept_df)
        weekday_cases = len(dept_df[dept_df['is_weekday']]) if 'is_weekday' in dept_df.columns else gas_cases
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("🩺 診療科", dept_name)
        
        with col2:
            st.metric("📅 分析期間", period_info['period_name'])
        
        with col3:
            st.metric("🔴 全身麻酔20分以上", f"{gas_cases:,}件")
        
        with col4:
            st.metric("📈 期間日数", f"{period_info['total_days']}日")
        
        with col5:
            daily_avg = weekday_cases / period_info['weekdays'] if period_info['weekdays'] > 0 else 0
            st.metric("📊 平日1日平均", f"{daily_avg:.1f}件/日")
        
        st.caption(
            f"📅 分析期間: {period_info['start_date']} ～ {period_info['end_date']} "
            f"（平日{period_info['weekdays']}日間）"
        )

    @staticmethod
    @safe_data_operation("診療科KPI計算")
    def _render_department_kpi(dept_df: pd.DataFrame, 
                            start_date: Optional[pd.Timestamp],
                            end_date: Optional[pd.Timestamp],
                            dept_name: str) -> None:
        """診療科別KPI表示"""
        try:
            st.subheader(f"📊 {dept_name} 主要指標")
            
            # 基本統計
            total_cases = len(dept_df)
            gas_cases = len(dept_df[dept_df['is_gas_20min']]) if 'is_gas_20min' in dept_df.columns else total_cases
            
            # 期間中の週数を計算
            if start_date and end_date:
                weeks_in_period = (end_date - start_date).days / 7
                weekly_avg = gas_cases / weeks_in_period if weeks_in_period > 0 else 0
            else:
                weekly_avg = 0

            col1, col2, col3 = st.columns(3)  # 4列から3列に変更
            
            with col1:
                st.metric("📊 全手術件数", f"{total_cases:,}件")
            
            with col2:
                st.metric("🔴 全身麻酔20分以上", f"{gas_cases:,}件")
            
            with col3:
                gas_ratio = (gas_cases / total_cases * 100) if total_cases > 0 else 0
                st.metric("🎯 全身麻酔比率", f"{gas_ratio:.1f}%")
            
            # 目標との比較
            target_dict = SessionManager.get_target_dict()
            target_value = target_dict.get(dept_name)
            
            if target_value and start_date and end_date:
                # 期間中の週数を計算
                weeks_in_period = (end_date - start_date).days / 7
                weekly_avg = gas_cases / weeks_in_period if weeks_in_period > 0 else 0
                achievement_rate = (weekly_avg / target_value * 100) if target_value > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("🎯 週次目標", f"{target_value:.1f}件/週")
                
                with col2:
                    st.metric("📈 週次実績", f"{weekly_avg:.1f}件/週")
                
                with col3:
                    color = "🟢" if achievement_rate >= 100 else "🟡" if achievement_rate >= 80 else "🔴"
                    st.metric("📊 達成率", f"{achievement_rate:.1f}%", 
                            delta=f"{achievement_rate - 100:.1f}%" if achievement_rate != 100 else "目標達成")
                
                if achievement_rate >= 100:
                    st.success(f"🎉 {dept_name}は目標を達成しています！")
                elif achievement_rate >= 80:
                    st.warning(f"⚠️ {dept_name}は目標まであと{100 - achievement_rate:.1f}%です")
                else:
                    shortfall = target_value - weekly_avg
                    st.error(f"📉 {dept_name}は目標まで{shortfall:.1f}件/週不足しています")
            else:
                st.info("この診療科の目標値は設定されていません")
            
        except Exception as e:
            st.error(f"KPI計算エラー: {e}")
            logger.error(f"診療科別KPI計算エラー ({dept_name}): {e}")
    
    @staticmethod
    @safe_data_operation("診療科別週次推移表示")
    def _render_department_trend(filtered_df: pd.DataFrame, 
                               target_dict: Dict[str, Any], 
                               dept_name: str,
                               period_name: str) -> None:
        """診療科別週次推移表示"""
        st.markdown("---")
        st.subheader(f"📈 {dept_name} 週次推移 - {period_name}")
        
        try:
            # 完全週データオプション
            use_complete_weeks = st.toggle(
                "完全週データ", 
                True, 
                help="週の途中のデータを除外し、完全な週単位で分析します",
                key=f"complete_weeks_{dept_name}"
            )
            
            summary = weekly.get_summary(
                filtered_df, 
                department=dept_name, 
                use_complete_weeks=use_complete_weeks
            )
            
            if not summary.empty:
                fig = trend_plots.create_weekly_dept_chart(
                    summary, f"{dept_name} ({period_name})", target_dict
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # 統計情報
                with st.expander("📊 統計サマリー"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**基本統計:**")
                        st.write(f"• 分析週数: {len(summary)}週")
                        st.write(f"• 最大値: {summary['週合計件数'].max():.0f}件/週")
                        st.write(f"• 最小値: {summary['週合計件数'].min():.0f}件/週")
                        st.write(f"• 平均値: {summary['週合計件数'].mean():.1f}件/週")
                    
                    with col2:
                        st.write("**目標との比較:**")
                        target_value = target_dict.get(dept_name)
                        if target_value:
                            avg_actual = summary['週合計件数'].mean()
                            achievement_rate = (avg_actual / target_value * 100)
                            st.write(f"• 目標値: {target_value:.1f}件/週")
                            st.write(f"• 平均達成率: {achievement_rate:.1f}%")
                            
                            if achievement_rate >= 100:
                                st.success(f"🎯 目標達成！")
                            else:
                                shortfall = target_value - avg_actual
                                st.warning(f"⚠️ 目標まで {shortfall:.1f}件/週不足")
                        else:
                            st.info("この診療科の目標値は設定されていません")
                
                # トレンド分析
                if len(summary) >= 4:
                    recent_4 = summary.tail(4)['週合計件数'].mean()
                    if len(summary) >= 8:
                        previous_4 = summary.iloc[-8:-4]['週合計件数'].mean()
                        trend_change = ((recent_4 / previous_4 - 1) * 100) if previous_4 > 0 else 0
                        
                        st.markdown("**📈 トレンド分析**")
                        if trend_change > 10:
                            st.success(f"🔺 明確な上昇トレンド: {trend_change:+.1f}%")
                        elif trend_change < -10:
                            st.error(f"🔻 明確な下降トレンド: {trend_change:+.1f}%")
                        else:
                            st.info(f"➡️ 安定トレンド: {trend_change:+.1f}%")
            else:
                st.warning(f"{dept_name}の選択期間（{period_name}）に週次データがありません")
                
        except Exception as e:
            st.error(f"週次推移分析エラー: {e}")
            logger.error(f"診療科別週次推移エラー ({dept_name}): {e}")
    
    @staticmethod
    def _render_detailed_analysis_tabs(dept_df: pd.DataFrame, dept_name: str, period_name: str) -> None:
        """詳細分析タブを表示"""
        st.markdown("---")
        st.header(f"🔍 {dept_name} 詳細分析 - {period_name}")
        
        tab1, tab2, tab3, tab4 = st.tabs(["術者分析", "時間分析", "統計情報", "期間比較"])
        
        with tab1:
            DepartmentPage._render_surgeon_analysis_tab(dept_df, dept_name, period_name)
        
        with tab2:
            DepartmentPage._render_time_analysis_tab(dept_df, dept_name, period_name)
        
        with tab3:
            DepartmentPage._render_statistics_tab(dept_df, dept_name, period_name)
        
        with tab4:
            DepartmentPage._render_period_comparison_tab(dept_name, period_name)
    
    @staticmethod
    @safe_data_operation("術者分析")
    def _render_surgeon_analysis_tab(dept_df: pd.DataFrame, dept_name: str, period_name: str) -> None:
        """術者分析タブ"""
        st.subheader(f"{dept_name} 術者別件数 (Top 15) - {period_name}")
        
        try:
            with st.spinner("術者データを準備中..."):
                expanded_df = surgeon.get_expanded_surgeon_df(dept_df)
                
                if not expanded_df.empty:
                    surgeon_summary = surgeon.get_surgeon_summary(expanded_df)
                    
                    if not surgeon_summary.empty:
                        # get_surgeon_summaryは '実施術者', '件数' を返すことを想定
                        fig = generic_plots.plot_surgeon_ranking(
                            surgeon_summary, 15, f"{dept_name} ({period_name})"
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # 術者統計
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("👨‍⚕️ 術者数", f"{len(surgeon_summary)}名")
                        
                        with col2:
                            top_surgeon_cases = surgeon_summary.iloc[0]['件数'] if len(surgeon_summary) > 0 else 0
                            st.metric("🏆 最多術者件数", f"{top_surgeon_cases}件")
                        
                        with col3:
                            avg_cases = surgeon_summary['件数'].mean()
                            st.metric("📊 平均件数", f"{avg_cases:.1f}件")
                        
                        # 詳細データテーブル
                        with st.expander("術者別詳細データ"):
                            st.dataframe(surgeon_summary.head(15), use_container_width=True)
                    else:
                        st.info("術者データを集計できませんでした")
                else:
                    st.info("分析可能な術者データがありません")
                    
        except Exception as e:
            st.error(f"術者分析エラー: {e}")
            logger.error(f"術者分析エラー ({dept_name}): {e}", exc_info=True)
    
    @staticmethod
    @safe_data_operation("時間分析")
    def _render_time_analysis_tab(dept_df: pd.DataFrame, dept_name: str, period_name: str) -> None:
        """時間分析タブ"""
        st.subheader(f"{dept_name} 時間別分布 - {period_name}")
        
        try:
            gas_df = dept_df[dept_df['is_gas_20min']] if 'is_gas_20min' in dept_df.columns else dept_df
            
            if not gas_df.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    # 曜日別分布
                    weekday_dist = gas_df['手術実施日_dt'].dt.day_name().value_counts()
                    fig_weekday = px.pie(
                        values=weekday_dist.values, 
                        names=weekday_dist.index, 
                        title=f"曜日別分布 - {dept_name}"
                    )
                    st.plotly_chart(fig_weekday, use_container_width=True)
                
                with col2:
                    # 月別分布
                    month_dist = gas_df['手術実施日_dt'].dt.month_name().value_counts()
                    fig_month = px.bar(
                        x=month_dist.index, 
                        y=month_dist.values, 
                        title=f"月別分布 - {dept_name}", 
                        labels={'x': '月', 'y': '件数'}
                    )
                    st.plotly_chart(fig_month, use_container_width=True)
                
                # 時間統計
                st.subheader("時間別統計")
                
                # 平日・休日分布
                if 'is_weekday' in gas_df.columns:
                    weekday_count = len(gas_df[gas_df['is_weekday']])
                    weekend_count = len(gas_df[~gas_df['is_weekday']])
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("平日手術", f"{weekday_count}件")
                    with col2:
                        st.metric("休日手術", f"{weekend_count}件")
                    with col3:
                        weekday_ratio = (weekday_count / len(gas_df) * 100) if len(gas_df) > 0 else 0
                        st.metric("平日比率", f"{weekday_ratio:.1f}%")
                
                # 期間内の日別推移
                if len(gas_df) > 7:
                    daily_counts = gas_df.groupby('手術実施日_dt').size().reset_index(name='件数')
                    
                    fig_daily = px.line(
                        daily_counts, 
                        x='手術実施日_dt', 
                        y='件数',
                        title=f"{dept_name} 日別推移 - {period_name}",
                        labels={'手術実施日_dt': '日付', '件数': '手術件数'}
                    )
                    st.plotly_chart(fig_daily, use_container_width=True)
            else:
                st.info("全身麻酔20分以上の手術データがありません")
                
        except Exception as e:
            st.error(f"時間分析エラー: {e}")
            logger.error(f"時間分析エラー ({dept_name}): {e}")
    
    @staticmethod
    def _render_statistics_tab(dept_df: pd.DataFrame, dept_name: str, period_name: str) -> None:
        """統計情報タブ"""
        st.subheader(f"{dept_name} 基本統計 - {period_name}")
        
        try:
            gas_df = dept_df[dept_df['is_gas_20min']] if 'is_gas_20min' in dept_df.columns else dept_df
            
            if not gas_df.empty:
                # 基本統計の表示
                try:
                    # 数値列のみを選択して統計を計算
                    numeric_columns = gas_df.select_dtypes(include=['number']).columns
                    if len(numeric_columns) > 0:
                        desc_df = gas_df[numeric_columns].describe().transpose()
                        st.write("**数値データ統計:**")
                        st.dataframe(desc_df.round(2), use_container_width=True)
                    
                    # カテゴリデータの統計
                    categorical_columns = gas_df.select_dtypes(include=['object']).columns
                    if len(categorical_columns) > 0:
                        st.write("**カテゴリデータ統計:**")
                        for col in categorical_columns[:5]:  # 上位5列のみ表示
                            unique_count = gas_df[col].nunique()
                            st.write(f"• {col}: {unique_count}種類")
                except Exception as e:
                    st.write("統計の詳細表示でエラーが発生しました")
                    logger.warning(f"統計表示エラー: {e}")
                
                # データ概要
                st.subheader("データ概要")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("総件数", f"{len(gas_df)}件")
                with col2:
                    if len(gas_df) > 0:
                        date_range = (gas_df['手術実施日_dt'].max() - gas_df['手術実施日_dt'].min()).days + 1
                        st.metric("期間", f"{date_range}日間")
                    else:
                        st.metric("期間", "0日")
                with col3:
                    if 'is_weekday' in gas_df.columns:
                        weekday_ratio = (gas_df['is_weekday'].sum() / len(gas_df)) * 100
                        st.metric("平日比率", f"{weekday_ratio:.1f}%")
                
                # データ品質チェック
                st.subheader("データ品質")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**欠損値チェック:**")
                    missing_data = gas_df.isnull().sum()
                    missing_data = missing_data[missing_data > 0]
                    if len(missing_data) > 0:
                        for col, count in missing_data.head(5).items():
                            ratio = (count / len(gas_df)) * 100
                            st.write(f"• {col}: {count}件 ({ratio:.1f}%)")
                    else:
                        st.success("欠損値なし")
                
                with col2:
                    st.write("**データ範囲:**")
                    if len(gas_df) > 0:
                        st.write(f"• 開始日: {gas_df['手術実施日_dt'].min().strftime('%Y/%m/%d')}")
                        st.write(f"• 終了日: {gas_df['手術実施日_dt'].max().strftime('%Y/%m/%d')}")
                        st.write(f"• 期間: {period_name}")
            else:
                st.info("統計情報を計算するデータがありません")
                
        except Exception as e:
            st.error(f"統計情報エラー: {e}")
            logger.error(f"統計情報エラー ({dept_name}): {e}")
    
    @staticmethod
    def _render_period_comparison_tab(dept_name: str, current_period_name: str) -> None:
        """期間比較タブ"""
        st.subheader(f"{dept_name} 期間比較分析")
        
        try:
            # 全データを取得
            full_df = SessionManager.get_processed_df()
            
            # 期間選択（比較用）
            st.markdown("**比較期間を選択してください:**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**現在期間:** {current_period_name}")
                # 現在の期間データ（既にフィルタ済み）
                current_dept_df = None  # 後で取得
            
            with col2:
                # 比較期間選択
                compare_period, compare_start, compare_end = PeriodSelector.render(
                    page_name=f"department_compare_{dept_name}",
                    show_info=False,
                    key_suffix=f"compare_{dept_name}"
                )
                
                # 比較期間のデータ
                if compare_start and compare_end:
                    compare_df = PeriodSelector.filter_data_by_period(full_df, compare_start, compare_end)
                    compare_dept_df = compare_df[compare_df['実施診療科'] == dept_name]
                    
                    if not compare_dept_df.empty:
                        # 比較分析を実行
                        DepartmentPage._perform_period_comparison(
                            dept_name, 
                            current_period_name, 
                            compare_period,
                            compare_dept_df  # 現在は比較期間のみ
                        )
                    else:
                        st.warning(f"比較期間（{compare_period}）に{dept_name}のデータがありません")
                else:
                    st.info("比較期間を選択してください")
                    
        except Exception as e:
            st.error(f"期間比較エラー: {e}")
            logger.error(f"期間比較エラー ({dept_name}): {e}")
    
    @staticmethod
    def _perform_period_comparison(dept_name: str,
                                 current_period: str,
                                 compare_period: str,
                                 compare_dept_df: pd.DataFrame) -> None:
        """期間比較分析を実行"""
        try:
            st.markdown("**📊 期間比較結果**")
            
            # 比較期間の統計
            compare_gas_df = compare_dept_df[compare_dept_df['is_gas_20min']] if 'is_gas_20min' in compare_dept_df.columns else compare_dept_df
            compare_total = len(compare_gas_df)
            compare_weekday = len(compare_gas_df[compare_gas_df['is_weekday']]) if 'is_weekday' in compare_gas_df.columns else compare_total
            
            # メトリクス表示
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**{current_period}**")
                st.write("（現在選択中の期間のデータは上記タブで確認）")
            
            with col2:
                st.write(f"**{compare_period}**")
                st.metric("全身麻酔20分以上", f"{compare_total}件")
                st.metric("平日手術", f"{compare_weekday}件")
            
            # 簡単な比較コメント
            if compare_total > 0:
                st.success(f"比較期間（{compare_period}）のデータが見つかりました")
                st.info("詳細な比較には、KPI・週次推移タブで両期間のデータを確認してください")
            else:
                st.warning(f"比較期間（{compare_period}）にデータがありません")
                
        except Exception as e:
            logger.error(f"期間比較実行エラー: {e}")
            st.error("期間比較の実行中にエラーが発生しました")


# ページルーター用の関数
def render():
    """ページルーター用のレンダー関数"""
    DepartmentPage.render()