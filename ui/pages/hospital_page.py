# ui/pages/hospital_page.py (期間選択機能追加版)
"""
病院全体分析ページモジュール
病院全体のパフォーマンス分析を表示（期間選択機能追加）
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional
import logging

from ui.session_manager import SessionManager
from ui.error_handler import safe_streamlit_operation, safe_data_operation
from ui.components.period_selector import PeriodSelector

# 既存の分析モジュールをインポート
from analysis import weekly, ranking
from plotting import trend_plots, generic_plots

# 追加の統計分析用ライブラリ（オプション）
try:
    from sklearn.linear_model import LinearRegression
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)


class HospitalPage:
    """病院全体分析ページクラス"""
    
    @staticmethod
    @safe_streamlit_operation("病院全体分析ページ描画")
    def render() -> None:
        """病院全体分析ページを描画"""
        st.title("🏥 病院全体分析 - 詳細分析")
        
        # データ取得
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        latest_date = SessionManager.get_latest_date()
        
        if df.empty:
            st.warning("⚠️ データが読み込まれていません")
            return
        
        # 期間選択セクション
        st.markdown("---")
        period_name, start_date, end_date = PeriodSelector.render(
            page_name="hospital_analysis",
            show_info=True,
            key_suffix="hospital"
        )
        
        # 期間に基づいてデータをフィルタリング
        filtered_df = PeriodSelector.filter_data_by_period(df, start_date, end_date)
        
        # 期間サマリー表示
        if start_date and end_date:
            st.markdown("---")
            PeriodSelector.render_period_summary(period_name, start_date, end_date, filtered_df)
        
        st.markdown("---")
        
        # 分析期間情報の表示
        HospitalPage._render_analysis_period_info(filtered_df, start_date, end_date)
        
        # 週次推移グラフ（複数パターン）
        HospitalPage._render_multiple_trend_patterns(filtered_df, target_dict, period_name)
        
        # 統計分析セクション
        HospitalPage._render_statistical_analysis(filtered_df, start_date, end_date)
        
        # 期間別比較セクション（選択期間vs前期間）
        HospitalPage._render_period_comparison(df, filtered_df, target_dict, period_name, start_date, end_date)
        
        # トレンド分析セクション
        HospitalPage._render_trend_analysis(filtered_df, start_date, end_date)
    
    @staticmethod
    @safe_data_operation("分析期間情報表示")
    def _render_analysis_period_info(filtered_df: pd.DataFrame, 
                                   start_date: Optional[pd.Timestamp], 
                                   end_date: Optional[pd.Timestamp]) -> None:
        """分析期間情報を表示"""
        if filtered_df.empty:
            st.warning("選択期間にデータがありません")
            return
        
        # データ期間の情報
        data_start = filtered_df['手術実施日_dt'].min()
        data_end = filtered_df['手術実施日_dt'].max()
        total_records = len(filtered_df)
        
        # 全身麻酔20分以上の件数
        gas_records = len(filtered_df[filtered_df['is_gas_20min']]) if 'is_gas_20min' in filtered_df.columns else 0
        
        # メトリクス表示
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 総レコード数", f"{total_records:,}件")
        with col2:
            st.metric("🔴 全身麻酔20分以上", f"{gas_records:,}件")
        with col3:
            st.metric("📅 データ開始日", data_start.strftime('%Y/%m/%d'))
        with col4:
            st.metric("📅 データ終了日", data_end.strftime('%Y/%m/%d'))
        
        # 選択期間との整合性確認
        if start_date and end_date:
            if data_start < start_date or data_end > end_date:
                st.info(
                    f"💡 選択期間: {start_date.strftime('%Y/%m/%d')} ～ {end_date.strftime('%Y/%m/%d')} "
                    f"でデータをフィルタリングしています"
                )
        
        st.markdown("---")
    
    @staticmethod
    @safe_data_operation("複数トレンドパターン表示")
    def _render_multiple_trend_patterns(filtered_df: pd.DataFrame, 
                                      target_dict: Dict[str, Any],
                                      period_name: str) -> None:
        """複数の週次推移パターンを表示"""
        st.subheader(f"📈 週次推移分析 - {period_name}")
        
        try:
            # 完全週データ取得（フィルタ済みデータで）
            summary = weekly.get_summary(filtered_df, use_complete_weeks=True)
            
            if summary.empty:
                st.warning("選択期間の週次推移データがありません。")
                return
            
            # DataFrameの構造確認
            logger.info(f"Summary columns: {list(summary.columns)}")
            logger.info(f"Summary shape: {summary.shape}")
            
            # 必要なカラムの存在確認
            if '平日1日平均件数' not in summary.columns:
                st.error("必要なデータ列（平日1日平均件数）が見つかりません。")
                st.write("利用可能な列:", list(summary.columns))
                return
            
            # タブで複数パターンを表示
            tab1, tab2, tab3 = st.tabs(["📊 標準推移", "📈 移動平均", "🎯 目標比較"])
            
            with tab1:
                st.markdown(f"**{period_name}の週次推移（平日1日平均）**")
                fig1 = trend_plots.create_weekly_summary_chart(
                    summary, f"病院全体 週次推移 ({period_name})", target_dict
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with tab2:
                st.markdown(f"**移動平均トレンド（4週移動平均）- {period_name}**")
                if len(summary) >= 4:
                    try:
                        summary_ma = summary.copy()
                        summary_ma['4週移動平均'] = summary_ma['平日1日平均件数'].rolling(window=4).mean()
                        
                        # 移動平均チャートを既存関数で作成
                        fig2 = trend_plots.create_weekly_summary_chart(
                            summary_ma, f"移動平均トレンド（4週移動平均）- {period_name}", target_dict
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                        
                        # 移動平均の数値テーブル
                        with st.expander("移動平均データ"):
                            try:
                                ma_display = summary_ma[['平日1日平均件数', '4週移動平均']].dropna().reset_index()
                                st.dataframe(ma_display.round(1), use_container_width=True)
                            except Exception as e:
                                st.dataframe(summary_ma[['平日1日平均件数', '4週移動平均']].dropna().round(1))
                    except Exception as e:
                        st.error(f"移動平均計算エラー: {e}")
                        logger.error(f"移動平均計算エラー: {e}")
                else:
                    st.info("移動平均計算には最低4週間のデータが必要です。")
            
            with tab3:
                st.markdown(f"**目標達成率推移 - {period_name}**")
                if target_dict:
                    try:
                        from config.hospital_targets import HospitalTargets
                        hospital_target = HospitalTargets.get_daily_target()
                        
                        summary_target = summary.copy()
                        summary_target['達成率(%)'] = (summary_target['平日1日平均件数'] / hospital_target * 100)
                        
                        # 達成率チャートを既存関数で作成
                        fig3 = trend_plots.create_weekly_summary_chart(
                            summary_target, f"目標達成率推移 - {period_name}", target_dict
                        )
                        st.plotly_chart(fig3, use_container_width=True)
                        
                        # 達成率統計
                        avg_achievement = summary_target['達成率(%)'].mean()
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("平均達成率", f"{avg_achievement:.1f}%")
                        with col2:
                            above_target = len(summary_target[summary_target['達成率(%)'] >= 100])
                            st.metric("目標達成週数", f"{above_target}/{len(summary_target)}週")
                        with col3:
                            max_achievement = summary_target['達成率(%)'].max()
                            st.metric("最高達成率", f"{max_achievement:.1f}%")
                    except Exception as e:
                        st.error(f"目標達成率計算エラー: {e}")
                        logger.error(f"目標達成率計算エラー: {e}")
                else:
                    st.info("目標データが設定されていません。")
            
            # 統計サマリー
            with st.expander("📊 統計サマリー"):
                try:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("🗓️ 分析週数", f"{len(summary)}週")
                        st.metric("📈 最大値", f"{summary['平日1日平均件数'].max():.1f}件/日")
                    
                    with col2:
                        st.metric("📉 最小値", f"{summary['平日1日平均件数'].min():.1f}件/日") 
                        st.metric("📊 平均値", f"{summary['平日1日平均件数'].mean():.1f}件/日")
                    
                    with col3:
                        if len(summary) >= 8:  # 十分なデータがある場合のみ
                            recent_avg = summary.tail(4)['平日1日平均件数'].mean()
                            earlier_avg = summary.head(4)['平日1日平均件数'].mean()
                            trend_change = ((recent_avg/earlier_avg - 1)*100) if earlier_avg > 0 else 0
                            st.metric("📈 トレンド変化", f"{trend_change:+.1f}%")
                        st.metric("🔄 標準偏差", f"{summary['平日1日平均件数'].std():.1f}")
                except Exception as e:
                    st.write("統計計算中にエラーが発生しました")
                    logger.error(f"統計サマリーエラー: {e}")
                
        except Exception as e:
            st.error(f"週次推移分析エラー: {e}")
            logger.error(f"週次推移分析エラー: {e}")
    
    @staticmethod
    @safe_data_operation("統計分析表示")
    def _render_statistical_analysis(filtered_df: pd.DataFrame,
                                   start_date: Optional[pd.Timestamp], 
                                   end_date: Optional[pd.Timestamp]) -> None:
        """統計分析セクションを表示"""
        st.markdown("---")
        st.subheader("📊 統計分析・パフォーマンス指標")
        
        try:
            if filtered_df.empty:
                st.warning("選択期間に統計分析可能なデータがありません。")
                return
            
            # 全身麻酔20分以上のデータでKPI計算
            gas_df = filtered_df[filtered_df['is_gas_20min']] if 'is_gas_20min' in filtered_df.columns else filtered_df
            
            if gas_df.empty:
                st.warning("選択期間に全身麻酔20分以上のデータがありません。")
                return
            
            # KPI表示（期間限定版）
            st.markdown("**📈 主要業績指標 (選択期間)**")
            
            # 期間統計を計算
            period_stats = SessionManager.get_period_stats("hospital_analysis", start_date, end_date)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("🔴 全身麻酔手術", f"{period_stats.get('gas_cases', 0):,}件")
            
            with col2:
                st.metric("📊 全手術件数", f"{period_stats.get('total_cases', 0):,}件")
            
            with col3:
                st.metric("📈 平日1日平均", f"{period_stats.get('daily_avg', 0):.1f}件/日")
            
            with col4:
                weekdays = period_stats.get('weekdays', 0)
                st.metric("🗓️ 対象平日数", f"{weekdays}日")
            
            # 診療科別統計
            st.markdown("**🏥 診療科別統計分析（選択期間）**")
            dept_stats = HospitalPage._calculate_department_statistics(gas_df)
            
            if not dept_stats.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**上位5診療科 (件数)**")
                    top5 = dept_stats.head().round(1)
                    st.dataframe(top5, use_container_width=True)
                
                with col2:
                    st.markdown("**統計サマリー**")
                    st.write(f"• 診療科数: {len(dept_stats)}科")
                    st.write(f"• 平均件数: {dept_stats['合計件数'].mean():.1f}件")
                    st.write(f"• 最大差: {dept_stats['合計件数'].max() - dept_stats['合計件数'].min():.1f}件")
                    st.write(f"• 標準偏差: {dept_stats['合計件数'].std():.1f}")
            
            # 時系列統計（機械学習が利用可能な場合）
            if SKLEARN_AVAILABLE:
                HospitalPage._render_advanced_statistics(gas_df)
                
        except Exception as e:
            st.error(f"統計分析エラー: {e}")
            logger.error(f"統計分析エラー: {e}")
    
    @staticmethod
    def _calculate_department_statistics(df: pd.DataFrame) -> pd.DataFrame:
        """診療科別統計を計算"""
        try:
            dept_stats = df.groupby('実施診療科').agg({
                '手術実施日_dt': 'count',
                'is_weekday': 'sum'
            }).rename(columns={
                '手術実施日_dt': '合計件数',
                'is_weekday': '平日件数'
            })
            
            dept_stats['平日割合(%)'] = (dept_stats['平日件数'] / dept_stats['合計件数'] * 100).round(1)
            dept_stats = dept_stats.sort_values('合計件数', ascending=False)
            
            return dept_stats
            
        except Exception as e:
            logger.error(f"診療科別統計計算エラー: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def _render_advanced_statistics(df: pd.DataFrame) -> None:
        """高度統計分析（機械学習を使用）"""
        try:
            st.markdown("**🔬 高度統計分析**")
            
            # 日次件数の時系列データ準備
            daily_counts = df.groupby('手術実施日_dt').size().reset_index(name='件数')
            daily_counts = daily_counts.sort_values('手術実施日_dt')
            
            if len(daily_counts) >= 7:
                # 線形回帰でトレンド分析
                X = np.arange(len(daily_counts)).reshape(-1, 1)
                y = daily_counts['件数'].values
                
                model = LinearRegression()
                model.fit(X, y)
                
                trend_slope = model.coef_[0]
                r_squared = model.score(X, y)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    trend_direction = "上昇" if trend_slope > 0 else "下降"
                    st.metric("📈 トレンド傾向", trend_direction)
                
                with col2:
                    st.metric("📊 回帰係数", f"{trend_slope:.3f}")
                
                with col3:
                    st.metric("🎯 決定係数 (R²)", f"{r_squared:.3f}")
                
                st.caption("💡 決定係数が高いほど、トレンドの予測精度が高くなります")
            else:
                st.info("高度統計分析には最低7日分のデータが必要です。")
                
        except Exception as e:
            logger.error(f"高度統計分析エラー: {e}")
            st.warning("高度統計分析でエラーが発生しました。")
    
    @staticmethod
    @safe_data_operation("期間比較表示")
    def _render_period_comparison(full_df: pd.DataFrame,
                                filtered_df: pd.DataFrame,
                                target_dict: Dict[str, Any], 
                                period_name: str,
                                start_date: Optional[pd.Timestamp], 
                                end_date: Optional[pd.Timestamp]) -> None:
        """期間別比較セクションを表示"""
        st.markdown("---")
        st.subheader("📅 期間別比較分析")
        
        try:
            if not start_date or not end_date:
                st.warning("期間比較には有効な期間選択が必要です。")
                return
            
            # 前期間の計算
            period_length = (end_date - start_date).days + 1
            prev_end_date = start_date - pd.Timedelta(days=1)
            prev_start_date = prev_end_date - pd.Timedelta(days=period_length-1)
            
            # 前期間のデータを取得
            prev_df = full_df[
                (full_df['手術実施日_dt'] >= prev_start_date) & 
                (full_df['手術実施日_dt'] <= prev_end_date)
            ]
            
            # 比較データの準備
            comparison_data = []
            
            # 現在期間
            current_gas_df = filtered_df[filtered_df['is_gas_20min']] if 'is_gas_20min' in filtered_df.columns else filtered_df
            current_weekday_df = current_gas_df[current_gas_df['is_weekday']] if 'is_weekday' in current_gas_df.columns else current_gas_df
            current_weekdays = PeriodSelector.calculate_weekdays_in_period(start_date, end_date)
            current_daily_avg = len(current_weekday_df) / current_weekdays if current_weekdays > 0 else 0
            
            comparison_data.append({
                "期間": f"現在期間 ({period_name})",
                "総件数": len(current_gas_df),
                "平日平均/日": round(current_daily_avg, 1),
                "期間": f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}"
            })
            
            # 前期間
            if not prev_df.empty:
                prev_gas_df = prev_df[prev_df['is_gas_20min']] if 'is_gas_20min' in prev_df.columns else prev_df
                prev_weekday_df = prev_gas_df[prev_gas_df['is_weekday']] if 'is_weekday' in prev_gas_df.columns else prev_gas_df
                prev_weekdays = PeriodSelector.calculate_weekdays_in_period(prev_start_date, prev_end_date)
                prev_daily_avg = len(prev_weekday_df) / prev_weekdays if prev_weekdays > 0 else 0
                
                comparison_data.append({
                    "期間": "前期間",
                    "総件数": len(prev_gas_df),
                    "平日平均/日": round(prev_daily_avg, 1),
                    "期間": f"{prev_start_date.strftime('%m/%d')} - {prev_end_date.strftime('%m/%d')}"
                })
            
            if comparison_data:
                # 比較テーブル表示
                comparison_df = pd.DataFrame(comparison_data)
                st.dataframe(comparison_df, use_container_width=True)
                
                # 前期間比較メトリクス
                if len(comparison_data) >= 2:
                    PeriodSelector.render_period_comparison_metrics(
                        current_gas_df, 
                        prev_gas_df if not prev_df.empty else pd.DataFrame(),
                        "全身麻酔手術"
                    )
                
                # 目標達成状況比較
                if target_dict:
                    from config.hospital_targets import HospitalTargets
                    hospital_target = HospitalTargets.get_daily_target()
                    
                    st.markdown("**🎯 目標達成状況比較**")
                    
                    for data in comparison_data:
                        achievement_rate = (data["平日平均/日"] / hospital_target * 100) if hospital_target > 0 else 0
                        col1, col2, col3 = st.columns([2, 1, 1])
                        
                        with col1:
                            st.write(f"**{data['期間']}**")
                        with col2:
                            st.write(f"{data['平日平均/日']:.1f} 件/日")
                        with col3:
                            color = "🟢" if achievement_rate >= 100 else "🟡" if achievement_rate >= 80 else "🔴"
                            st.write(f"{color} {achievement_rate:.1f}%")
                
                # トレンド方向の分析
                if len(comparison_data) >= 2:
                    current_avg = comparison_data[0]["平日平均/日"]
                    prev_avg = comparison_data[1]["平日平均/日"]
                    
                    trend_change = ((current_avg / prev_avg - 1) * 100) if prev_avg > 0 else 0
                    
                    st.markdown("**📈 トレンド分析**")
                    if trend_change > 5:
                        st.success(f"🔺 上昇トレンド: {trend_change:+.1f}%")
                    elif trend_change < -5:
                        st.error(f"🔻 下降トレンド: {trend_change:+.1f}%")
                    else:
                        st.info(f"➡️ 安定トレンド: {trend_change:+.1f}%")
            else:
                st.warning("期間比較データがありません。")
                
        except Exception as e:
            st.error(f"期間比較分析エラー: {e}")
            logger.error(f"期間比較分析エラー: {e}")
    
    @staticmethod
    @safe_data_operation("トレンド分析表示")
    def _render_trend_analysis(filtered_df: pd.DataFrame,
                             start_date: Optional[pd.Timestamp], 
                             end_date: Optional[pd.Timestamp]) -> None:
        """トレンド分析セクションを表示"""
        st.markdown("---")
        st.subheader("🔮 詳細トレンド分析・予測")
        
        try:
            if filtered_df.empty:
                st.warning("選択期間にトレンド分析可能なデータがありません。")
                return
            
            # 週次データでトレンド分析
            summary = weekly.get_summary(filtered_df, use_complete_weeks=True)
            
            if summary.empty:
                st.warning("選択期間のトレンド分析用データがありません。")
                return
            
            tab1, tab2, tab3 = st.tabs(["📈 基本トレンド", "📊 季節性分析", "🔮 短期予測"])
            
            with tab1:
                HospitalPage._render_basic_trend_analysis(summary)
            
            with tab2:
                HospitalPage._render_seasonality_analysis(summary, filtered_df)
            
            with tab3:
                HospitalPage._render_short_term_prediction(summary)
                
        except Exception as e:
            st.error(f"トレンド分析エラー: {e}")
            logger.error(f"トレンド分析エラー: {e}")
    
    @staticmethod
    def _render_basic_trend_analysis(summary: pd.DataFrame) -> None:
        """基本トレンド分析"""
        st.markdown("**📈 基本トレンド指標**")
        
        if len(summary) < 4:
            st.info("基本トレンド分析には最低4週間のデータが必要です。")
            return
        
        # 最近4週 vs 前4週の比較
        recent_4weeks = summary.tail(4)['平日1日平均件数'].mean()
        previous_4weeks = summary.iloc[-8:-4]['平日1日平均件数'].mean() if len(summary) >= 8 else None
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 直近4週平均", f"{recent_4weeks:.1f}件/日")
        
        with col2:
            if previous_4weeks:
                change = recent_4weeks - previous_4weeks
                change_pct = (change / previous_4weeks * 100) if previous_4weeks > 0 else 0
                st.metric("📈 前4週比較", f"{previous_4weeks:.1f}件/日", 
                         delta=f"{change:+.1f} ({change_pct:+.1f}%)")
            else:
                st.metric("📈 前4週比較", "データ不足")
        
        with col3:
            volatility = summary['平日1日平均件数'].std()
            st.metric("📊 変動度", f"{volatility:.1f}")
        
        with col4:
            max_week = summary['平日1日平均件数'].max()
            min_week = summary['平日1日平均件数'].min()
            range_val = max_week - min_week
            st.metric("📏 最大幅", f"{range_val:.1f}")
        
        # トレンド方向
        if len(summary) >= 6:
            recent_trend = summary.tail(6)['平日1日平均件数'].mean()
            earlier_trend = summary.head(6)['平日1日平均件数'].mean()
            
            if recent_trend > earlier_trend * 1.05:
                st.success("🔺 **明確な上昇トレンド** を検出")
            elif recent_trend < earlier_trend * 0.95:
                st.error("🔻 **明確な下降トレンド** を検出")
            else:
                st.info("➡️ **安定的なトレンド** を維持")
    
    @staticmethod
    def _render_seasonality_analysis(summary: pd.DataFrame, df: pd.DataFrame) -> None:
        """季節性分析"""
        st.markdown("**🗓️ 季節性・周期性分析**")
        
        try:
            # 曜日別分析
            if '手術実施日_dt' in df.columns:
                df_copy = df.copy()
                df_copy['曜日'] = df_copy['手術実施日_dt'].dt.day_name()
                df_copy['曜日番号'] = df_copy['手術実施日_dt'].dt.dayofweek
                
                # 平日のみで曜日別件数
                weekday_df = df_copy[df_copy['is_weekday'] == True]
                
                if not weekday_df.empty:
                    dow_analysis = weekday_df.groupby(['曜日', '曜日番号']).size().reset_index(name='件数')
                    dow_analysis = dow_analysis.sort_values('曜日番号')
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**曜日別傾向**")
                        for _, row in dow_analysis.iterrows():
                            st.write(f"• {row['曜日']}: {row['件数']}件")
                    
                    with col2:
                        if len(dow_analysis) > 1:
                            max_dow = dow_analysis.loc[dow_analysis['件数'].idxmax(), '曜日']
                            min_dow = dow_analysis.loc[dow_analysis['件数'].idxmin(), '曜日']
                            st.markdown("**パターン分析**")
                            st.write(f"• 最多曜日: {max_dow}")
                            st.write(f"• 最少曜日: {min_dow}")
                            
                            variance = dow_analysis['件数'].var()
                            if variance > dow_analysis['件数'].mean() * 0.1:
                                st.write("• 曜日による変動が大きい")
                            else:
                                st.write("• 曜日による変動は小さい")
            
            # 月別傾向（データが複数月にわたる場合）
            if len(summary) >= 8:  # 約2ヶ月分
                st.markdown("**📅 月次傾向分析**")
                df_monthly = df.copy()
                df_monthly['年月'] = df_monthly['手術実施日_dt'].dt.to_period('M')
                monthly_counts = df_monthly.groupby('年月').size()
                
                if len(monthly_counts) >= 2:
                    st.write("月別推移:")
                    for period, count in monthly_counts.items():
                        st.write(f"• {period}: {count}件")
                else:
                    st.info("月次傾向分析には複数月のデータが必要です。")
            else:
                st.info("季節性分析には8週間以上のデータが推奨されます。")
                
        except Exception as e:
            logger.error(f"季節性分析エラー: {e}")
            st.warning("季節性分析でエラーが発生しました。")
    
    @staticmethod
    def _render_short_term_prediction(summary: pd.DataFrame) -> None:
        """短期予測"""
        st.markdown("**🔮 短期予測（次週・次月）**")
        
        if len(summary) < 4:
            st.info("予測には最低4週間のデータが必要です。")
            return
        
        try:
            # 単純移動平均による予測
            recent_4weeks_avg = summary.tail(4)['平日1日平均件数'].mean()
            recent_2weeks_avg = summary.tail(2)['平日1日平均件数'].mean()
            
            # トレンド調整
            if len(summary) >= 6:
                trend_factor = recent_2weeks_avg / recent_4weeks_avg if recent_4weeks_avg > 0 else 1
            else:
                trend_factor = 1
            
            # 予測値計算
            next_week_prediction = recent_4weeks_avg * trend_factor
            confidence_range = summary['平日1日平均件数'].std() * 0.5
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("🔮 次週予測", f"{next_week_prediction:.1f}件/日")
            
            with col2:
                st.metric("📊 予測範囲", 
                         f"{next_week_prediction-confidence_range:.1f} - {next_week_prediction+confidence_range:.1f}")
            
            with col3:
                # 目標との比較
                from config.hospital_targets import HospitalTargets
                hospital_target = HospitalTargets.get_daily_target()
                predicted_achievement = (next_week_prediction / hospital_target * 100) if hospital_target > 0 else 0
                st.metric("🎯 予測達成率", f"{predicted_achievement:.1f}%")
            
            # 予測の信頼性
            data_points = len(summary)
            variability = summary['平日1日平均件数'].std() / summary['平日1日平均件数'].mean()
            
            st.markdown("**📊 予測の信頼性**")
            
            if data_points >= 8 and variability < 0.2:
                st.success("🟢 高い信頼性: 十分なデータと安定した傾向")
            elif data_points >= 6 and variability < 0.3:
                st.warning("🟡 中程度の信頼性: データまたは安定性に課題")
            else:
                st.error("🔴 低い信頼性: データ不足または高い変動性")
            
            st.caption(f"💡 データ期間: {data_points}週, 変動係数: {variability:.2f}")
            
        except Exception as e:
            logger.error(f"短期予測エラー: {e}")
            st.warning("短期予測でエラーが発生しました。")


# ページルーター用の関数
def render():
    """ページルーター用のレンダー関数"""
    HospitalPage.render()