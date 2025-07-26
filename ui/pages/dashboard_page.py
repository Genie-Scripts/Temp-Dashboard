# ui/pages/dashboard_page.py
"""
ダッシュボードページモジュール
メインダッシュボードの表示を管理
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from ui.session_manager import SessionManager
from ui.error_handler import safe_streamlit_operation, safe_data_operation

# 既存の分析モジュールをインポート
from analysis import weekly, ranking
from plotting import trend_plots, generic_plots
from utils import date_helpers

# PDF出力機能をインポート
try:
    from utils.pdf_generator import StreamlitPDFExporter
    PDF_EXPORT_AVAILABLE = True
except ImportError:
    PDF_EXPORT_AVAILABLE = False

logger = logging.getLogger(__name__)


class DashboardPage:
    """ダッシュボードページクラス"""

    @staticmethod
    @safe_streamlit_operation("ハイスコア表示")
    def _render_high_score_section() -> None:
        """ハイスコアセクションを表示"""
        try:
            # データ取得
            df = SessionManager.get_processed_df()
            target_dict = SessionManager.get_target_dict()
            
            if df.empty:
                st.info("📊 データを読み込み後にハイスコア機能が利用可能になります")
                return
            
            st.markdown("---")
            st.header("🏆 診療科別ハイスコアランキング")
            
            # 期間選択
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                period = st.selectbox(
                    "評価期間",
                    ["直近4週", "直近8週", "直近12週"],
                    index=2,  # デフォルト: 直近12週
                    key="high_score_period"
                )
            
            with col2:
                if st.button("🔄 更新", key="refresh_high_score"):
                    st.rerun()
            
            with col3:
                show_details = st.checkbox("詳細表示", value=False, key="high_score_details")
            
            # ハイスコア計算
            with st.spinner("ハイスコアを計算中..."):
                from analysis.surgery_high_score import calculate_surgery_high_scores, generate_surgery_high_score_summary
                
                dept_scores = calculate_surgery_high_scores(df, target_dict, period)
                
                if not dept_scores:
                    st.warning("ハイスコアデータがありません。データと目標設定を確認してください。")
                    return
                
                summary = generate_surgery_high_score_summary(dept_scores)
            
            # サマリー情報
            if summary:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("🏥 評価診療科数", f"{summary['total_departments']}科")
                
                with col2:
                    st.metric("📊 平均スコア", f"{summary['average_score']:.1f}点")
                
                with col3:
                    st.metric("🎯 目標達成科数", f"{summary['high_achievers_count']}科")
                
                with col4:
                    achievement_rate = (summary['high_achievers_count'] / summary['total_departments'] * 100) if summary['total_departments'] > 0 else 0
                    st.metric("📈 達成率", f"{achievement_rate:.1f}%")
            
            # TOP3ランキング表示
            st.subheader("🥇 TOP3 診療科")
            
            if len(dept_scores) >= 3:
                top3 = dept_scores[:3]
                
                for i, dept in enumerate(top3):
                    rank_emoji = ["🥇", "🥈", "🥉"][i]
                    rank_color = ["#FFD700", "#C0C0C0", "#CD7F32"][i]
                    
                    with st.container():
                        st.markdown(f"""
                        <div style="
                            background: linear-gradient(90deg, {rank_color}20 0%, transparent 100%);
                            border-left: 4px solid {rank_color};
                            border-radius: 8px;
                            padding: 15px;
                            margin: 10px 0;
                        ">
                            <h4 style="margin: 0; color: #2c3e50;">
                                {rank_emoji} {dept['display_name']} 
                                <span style="color: {rank_color}; font-weight: bold;">
                                    {dept['grade']}グレード ({dept['total_score']:.1f}点)
                                </span>
                            </h4>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                "🔴 直近週全身麻酔",
                                f"{dept['latest_gas_cases']}件",
                                delta=f"目標: {dept['target_gas_cases']}件"
                            )
                        
                        with col2:
                            st.metric(
                                "📊 直近週全手術",
                                f"{dept['latest_total_cases']}件",
                                delta=f"平均: {dept['avg_total_cases']:.1f}件"
                            )
                        
                        with col3:
                            st.metric(
                                "⏱️ 直近週総手術時間", 
                                f"{dept['latest_total_hours']:.1f}時間",
                                delta=f"平均: {dept['avg_total_hours']:.1f}時間"
                            )
                        
                        with col4:
                            color = "🟢" if dept['achievement_rate'] >= 100 else "🟡" if dept['achievement_rate'] >= 80 else "🔴"
                            st.metric(
                                "🎯 達成率",
                                f"{dept['achievement_rate']:.1f}%",
                                delta=f"改善: {dept['improvement_rate']:+.1f}%"
                            )
                        
                        if show_details:
                            with st.expander(f"📋 {dept['display_name']} スコア詳細"):
                                score_components = dept['score_components']
                                
                                st.markdown("**スコア内訳:**")
                                st.progress(score_components['gas_surgery_score'] / 70, text=f"全身麻酔評価: {score_components['gas_surgery_score']:.1f}/70点")
                                st.progress(score_components['total_cases_score'] / 15, text=f"全手術件数評価: {score_components['total_cases_score']:.1f}/15点") 
                                st.progress(score_components['total_hours_score'] / 15, text=f"総手術時間評価: {score_components['total_hours_score']:.1f}/15点")
            
            # 全診療科ランキングテーブル
            if len(dept_scores) > 3:
                st.subheader("📋 全診療科ランキング")
                
                ranking_data = []
                for i, dept in enumerate(dept_scores):
                    ranking_data.append({
                        "順位": i + 1,
                        "診療科": dept['display_name'],
                        "グレード": dept['grade'],
                        "総合スコア": f"{dept['total_score']:.1f}点",
                        "達成率": f"{dept['achievement_rate']:.1f}%",
                        "直近週全身麻酔": f"{dept['latest_gas_cases']}件",
                        "直近週全手術": f"{dept['latest_total_cases']}件",
                        "改善率": f"{dept['improvement_rate']:+.1f}%"
                    })
                
                ranking_df = pd.DataFrame(ranking_data)
                st.dataframe(ranking_df, use_container_width=True)
                
                # CSVダウンロード
                csv_data = ranking_df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 ランキングをCSVダウンロード",
                    data=csv_data,
                    file_name=f"手術ハイスコアランキング_{period}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        except Exception as e:
            logger.error(f"ハイスコア表示エラー: {e}")
            st.error(f"ハイスコア表示でエラーが発生しました: {e}")

    @staticmethod
    def render() -> None:
        """ダッシュボードページを描画（ハイスコア機能追加版）"""
        st.title("📱 ダッシュボード - 手術分析の中心")
        
        # データ取得
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        latest_date = SessionManager.get_latest_date()
        
        if df.empty:
            DashboardPage._render_no_data_dashboard()
            return
        
        # 期間選択セクション
        analysis_period, start_date, end_date = DashboardPage._render_period_selector(latest_date)
        
        # 分析期間情報
        DashboardPage._render_analysis_period_info(latest_date, analysis_period, start_date, end_date)
        
        # メインコンテンツをタブで分割
        tab1, tab2, tab3 = st.tabs(["📊 主要指標", "📈 診療科別パフォーマンス", "🏆 ハイスコアランキング"])
        
        with tab1:
            # KPIセクション
            DashboardPage._render_kpi_section_with_data(df, latest_date, start_date, end_date)
            
            # 目標達成状況
            DashboardPage._render_achievement_status(df, target_dict, latest_date, start_date, end_date)
        
        with tab2:
            # 診療科別パフォーマンスダッシュボード
            DashboardPage._render_performance_dashboard_with_data(df, target_dict, latest_date, start_date, end_date)
        
        with tab3:
            # ハイスコアランキング（新機能）
            DashboardPage._render_high_score_section()
        
        # フッター情報
        DashboardPage._render_dashboard_footer(df, target_dict)

    @staticmethod
    @safe_streamlit_operation("ダッシュボードページ描画")
    def render() -> None:
        """ダッシュボードページを描画"""
        st.title("📱 ダッシュボード - 管理者向けサマリー")
        
        # データ取得
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        latest_date = SessionManager.get_latest_date()
        
        if df.empty:
            DashboardPage._render_no_data_dashboard()
            return
        
        # 期間選択セクション
        analysis_period, start_date, end_date = DashboardPage._render_period_selector(latest_date)
        
        # 分析期間情報
        DashboardPage._render_analysis_period_info(latest_date, analysis_period, start_date, end_date)
        
        # PDFデータ収集用の変数
        pdf_kpi_data = {}
        pdf_performance_data = pd.DataFrame()
        pdf_charts = {}
        
        # 主要指標セクション
        pdf_kpi_data = DashboardPage._render_kpi_section_with_data(df, latest_date, start_date, end_date)
        
        # 診療科別パフォーマンスダッシュボード
        pdf_performance_data = DashboardPage._render_performance_dashboard_with_data(df, target_dict, latest_date, start_date, end_date)
        
        # 目標達成状況サマリー  
        DashboardPage._render_achievement_summary(df, target_dict, latest_date, start_date, end_date)
        
        # 週次推移グラフ（PDF用）
        if not df.empty:
            try:
                summary = weekly.get_summary(df, use_complete_weeks=True)
                if not summary.empty:
                    pdf_charts['週次推移'] = trend_plots.create_weekly_summary_chart(summary, "病院全体 週次推移", target_dict)
            except Exception as e:
                logger.error(f"週次推移グラフ生成エラー: {e}")
        
        # PDF出力セクション
        DashboardPage._render_pdf_export_section(
            pdf_kpi_data, pdf_performance_data, analysis_period, start_date, end_date, pdf_charts
        )
    
    @staticmethod
    def _render_period_selector(latest_date: Optional[pd.Timestamp]) -> Tuple[str, pd.Timestamp, pd.Timestamp]:
        """期間選択セクションを表示"""
        st.subheader("📅 分析期間選択")
        
        period_options = [
            "直近4週",
            "直近8週", 
            "直近12週",
            "今年度",
            "昨年度"
        ]
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            selected_period = st.selectbox(
                "分析期間",
                period_options,
                index=0,
                help="分析に使用する期間を選択してください"
            )
        
        # 選択された期間に基づいて開始日・終了日を計算
        start_date, end_date = DashboardPage._calculate_period_dates(selected_period, latest_date)
        
        with col2:
            if start_date and end_date:
                st.info(
                    f"📊 **選択期間**: {selected_period}  \n"
                    f"📅 **分析範囲**: {start_date.strftime('%Y/%m/%d')} ～ {end_date.strftime('%Y/%m/%d')}  \n"
                    f"📈 **期間長**: {(end_date - start_date).days + 1}日間"
                )
            else:
                st.warning("期間計算でエラーが発生しました")
        
        return selected_period, start_date, end_date
    
    @staticmethod
    def _calculate_period_dates(period: str, latest_date: Optional[pd.Timestamp]) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
        """選択された期間に基づいて開始日・終了日を計算"""
        if not latest_date:
            return None, None
        
        try:
            # 週単位分析の場合は分析終了日（日曜日）を使用
            if "週" in period:
                analysis_end_date = weekly.get_analysis_end_date(latest_date)
                if not analysis_end_date:
                    return None, None
                end_date = analysis_end_date
            else:
                end_date = latest_date
            
            if period == "直近4週":
                start_date = end_date - pd.Timedelta(days=27)
            elif period == "直近8週":
                start_date = end_date - pd.Timedelta(days=55)
            elif period == "直近12週":
                start_date = end_date - pd.Timedelta(days=83)
            elif period == "今年度":
                current_year = latest_date.year
                if latest_date.month >= 4:
                    start_date = pd.Timestamp(current_year, 4, 1)
                else:
                    start_date = pd.Timestamp(current_year - 1, 4, 1)
                end_date = latest_date
            elif period == "昨年度":
                current_year = latest_date.year
                if latest_date.month >= 4:
                    start_date = pd.Timestamp(current_year - 1, 4, 1)
                    end_date = pd.Timestamp(current_year, 3, 31)
                else:
                    start_date = pd.Timestamp(current_year - 2, 4, 1)
                    end_date = pd.Timestamp(current_year - 1, 3, 31)
            else:
                return None, None
            
            return start_date, end_date
            
        except Exception as e:
            logger.error(f"期間計算エラー: {e}")
            return None, None
    
    @staticmethod
    def _render_no_data_dashboard() -> None:
        """データなし時のダッシュボード"""
        st.info("📊 ダッシュボードを表示するにはデータが必要です")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 🚀 はじめに
            
            手術分析ダッシュボードへようこそ！
            
            **主な機能:**
            - 📈 リアルタイム手術実績分析
            - 🏆 診療科別ランキング
            - 👨‍⚕️ 術者別パフォーマンス分析
            - 🔮 将来予測とトレンド分析
            """)
        
        with col2:
            st.markdown("""
            ### 📋 次のステップ
            
            1. **データアップロード**で手術データを読み込み
            2. **目標データ**を設定（オプション）
            3. **分析開始** - 各種レポートを確認
            
            **対応形式:** CSV形式の手術データ
            """)
        
        # クイックアクション
        st.markdown("---")
        st.subheader("⚡ クイックアクション")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📤 データアップロード", type="primary", use_container_width=True):
                SessionManager.set_current_view("データアップロード")
                st.rerun()
        
        with col2:
            if st.button("💾 データ管理", use_container_width=True):
                SessionManager.set_current_view("データ管理")
                st.rerun()
        
        with col3:
            if st.button("📖 ヘルプ", use_container_width=True):
                DashboardPage._show_help_dialog()
    
    @staticmethod
    @safe_data_operation("KPI計算")
    def _render_kpi_section(df: pd.DataFrame, latest_date: Optional[pd.Timestamp], 
                          start_date: Optional[pd.Timestamp], end_date: Optional[pd.Timestamp]) -> None:
        """KPIセクションを描画"""
        st.header("📊 主要指標 (選択期間)")
        
        try:
            # 選択された期間でデータをフィルタリング
            if start_date and end_date:
                period_df = df[
                    (df['手術実施日_dt'] >= start_date) & 
                    (df['手術実施日_dt'] <= end_date)
                ]
            else:
                # フォールバック: 元の関数を使用
                kpi_summary = ranking.get_kpi_summary(df, latest_date)
                generic_plots.display_kpi_metrics(kpi_summary)
                return
            
            # KPIサマリーを計算（選択期間用）
            kpi_data = DashboardPage._calculate_period_kpi(period_df, start_date, end_date)
            
            # KPI表示（直接メトリクス表示）
            DashboardPage._display_period_kpi_metrics(kpi_data, start_date, end_date)
            
        except Exception as e:
            logger.error(f"KPI計算エラー: {e}")
            st.error("KPI計算中にエラーが発生しました")
    
    @staticmethod
    def _calculate_period_kpi(df: pd.DataFrame, start_date: Optional[pd.Timestamp], 
                             end_date: Optional[pd.Timestamp]) -> Dict[str, Any]:
        """選択期間のKPIを計算"""
        try:
            if df.empty:
                return {}
            
            # 期間の日数計算
            if start_date and end_date:
                total_days = (end_date - start_date).days + 1
                weekdays = sum(1 for i in range(total_days) 
                             if (start_date + pd.Timedelta(days=i)).weekday() < 5)
            else:
                total_days = 28
                weekdays = 20
            
            # 1. 全身麻酔手術件数
            gas_df = df[df['is_gas_20min'] == True] if 'is_gas_20min' in df.columns else pd.DataFrame()
            gas_cases = len(gas_df)
            
            # 2. 全手術件数
            total_cases = len(df)
            
            # 3. 平日1日あたり全身麻酔手術件数
            if not gas_df.empty and 'is_weekday' in gas_df.columns:
                weekday_gas_df = gas_df[gas_df['is_weekday'] == True]
                weekday_gas_cases = len(weekday_gas_df)
            else:
                weekday_gas_cases = gas_cases
            
            daily_avg_gas = weekday_gas_cases / weekdays if weekdays > 0 else 0
            
            # 4. 手術室稼働率：時間ベースの正確な計算
            utilization_rate, actual_minutes, max_minutes = DashboardPage._calculate_or_utilization(
                df, start_date, end_date, weekdays
            )
            
            return {
                'gas_cases': gas_cases,
                'total_cases': total_cases,
                'daily_avg_gas': daily_avg_gas,
                'utilization_rate': utilization_rate,
                'actual_minutes': actual_minutes,
                'max_minutes': max_minutes,
                'period_days': total_days,
                'weekdays': weekdays
            }
            
        except Exception as e:
            logger.error(f"期間KPI計算エラー: {e}")
            return {}
    
    @staticmethod
    def _calculate_or_utilization(df: pd.DataFrame, start_date: Optional[pd.Timestamp], 
                                 end_date: Optional[pd.Timestamp], weekdays: int) -> Tuple[float, int, int]:
        """手術室稼働率を時間ベースで計算"""
        try:
            # 平日のデータのみ
            if 'is_weekday' in df.columns:
                weekday_df = df[df['is_weekday'] == True].copy()
            else:
                weekday_df = df.copy()
            
            if weekday_df.empty:
                return 0.0, 0, 0
            
            logger.info(f"平日データ件数: {len(weekday_df)}")
            
            # 手術室フィルタリング（全角対応）
            or_columns = ['手術室', 'OR', 'OP室', '実施手術室', '実施OP', 'OR番号']
            or_column = None
            
            for col in or_columns:
                if col in weekday_df.columns:
                    or_column = col
                    break
            
            if or_column:
                logger.info(f"手術室列を発見: {or_column}")
                unique_ors = weekday_df[or_column].dropna().unique()
                logger.info(f"手術室一覧（最初の10個）: {unique_ors[:10]}")
                
                weekday_df['or_str'] = weekday_df[or_column].astype(str)
                
                # 全角・半角両方に対応したフィルタリング
                op_rooms = weekday_df[
                    (weekday_df['or_str'].str.contains('OP', na=False, case=False)) |
                    (weekday_df['or_str'].str.contains('ＯＰ', na=False, case=False))
                ]
                logger.info(f"OP系手術室データ件数: {len(op_rooms)}")
                
                if len(op_rooms) > 0:
                    # OP-11A、OP-11B（全角・半角）を除く
                    or_filtered_df = op_rooms[
                        ~op_rooms['or_str'].str.contains('OP-11A|OP-11B|ＯＰ－１１Ａ|ＯＰ－１１Ｂ', na=False, case=False, regex=True)
                    ]
                    logger.info(f"OP-11A,11B除外後: {len(or_filtered_df)}")
                else:
                    logger.warning("OP系手術室が見つからないため、全平日データを使用")
                    or_filtered_df = weekday_df
            else:
                logger.warning("手術室列が見つからないため、全データを使用")
                logger.info(f"利用可能な列: {list(weekday_df.columns)}")
                or_filtered_df = weekday_df
            
            logger.info(f"手術室フィルタリング後: {len(or_filtered_df)}")
            
            # 時刻フィルタリング（入室時刻を使用）
            time_filtered_df = DashboardPage._filter_operating_hours_fixed(or_filtered_df)
            logger.info(f"時刻フィルタリング後: {len(time_filtered_df)}")
            
            # 手術時間の計算（予定手術時間を使用）
            actual_minutes = DashboardPage._calculate_surgery_minutes_fixed(time_filtered_df)
            logger.info(f"実際の手術時間: {actual_minutes}分")
            
            # 分母：理論上の最大稼働時間
            max_minutes = 495 * 11 * weekdays
            logger.info(f"最大稼働時間: {max_minutes}分 (495分×11室×{weekdays}平日)")
            
            # 稼働率計算
            utilization_rate = (actual_minutes / max_minutes * 100) if max_minutes > 0 else 0.0
            logger.info(f"稼働率: {utilization_rate:.2f}%")
            
            return utilization_rate, actual_minutes, max_minutes
            
        except Exception as e:
            logger.error(f"手術室稼働率計算エラー: {e}")
            return 0.0, 0, 0
    
    @staticmethod
    def _filter_operating_hours_debug(df: pd.DataFrame) -> pd.DataFrame:
        """9:00〜17:15の手術をフィルタリング（デバッグ版）"""
        try:
            if df.empty:
                return df
            
            # 手術開始時刻の列を探す
            time_columns = ['手術開始時刻', '開始時刻', '手術開始時間', 'start_time', '開始時間', 'OP開始時刻']
            time_column = None
            
            logger.info(f"利用可能な列: {list(df.columns)}")
            
            for col in time_columns:
                if col in df.columns:
                    time_column = col
                    logger.info(f"時刻列を発見: {time_column}")
                    break
            
            if not time_column:
                logger.warning("手術開始時刻列が見つからないため、時刻フィルタリングをスキップ")
                # 時刻データサンプルを表示
                potential_time_cols = [col for col in df.columns if '時' in col or 'time' in col.lower()]
                logger.info(f"時刻関連の列候補: {potential_time_cols}")
                return df
            
            # 時刻データのサンプルをログ出力
            sample_times = df[time_column].dropna().head(10).tolist()
            logger.info(f"時刻データサンプル: {sample_times}")
            
            def parse_time_to_minutes(time_str):
                """時刻文字列を分単位に変換"""
                if pd.isna(time_str) or time_str == '':
                    return None
                try:
                    time_str = str(time_str).strip()
                    if ':' in time_str:
                        hour, minute = time_str.split(':')
                        return int(hour) * 60 + int(minute)
                    else:
                        time_num = int(float(time_str))
                        hour = time_num // 100
                        minute = time_num % 100
                        return hour * 60 + minute
                except Exception as e:
                    logger.warning(f"時刻解析エラー: {time_str} -> {e}")
                    return None
            
            df_filtered = df.copy()
            df_filtered['start_minutes'] = df_filtered[time_column].apply(parse_time_to_minutes)
            
            # 有効な時刻データの統計
            valid_times = df_filtered['start_minutes'].dropna()
            if len(valid_times) > 0:
                logger.info(f"有効な時刻データ: {len(valid_times)}件")
                logger.info(f"時刻範囲: {valid_times.min()}分({valid_times.min()//60}:{valid_times.min()%60:02d}) - {valid_times.max()}分({valid_times.max()//60}:{valid_times.max()%60:02d})")
            else:
                logger.warning("有効な時刻データが0件")
                return df
            
            # 9:00（540分）〜17:15（1035分）でフィルタリング
            filtered_df = df_filtered[
                (df_filtered['start_minutes'] >= 540) & 
                (df_filtered['start_minutes'] <= 1035) &
                (df_filtered['start_minutes'].notna())
            ]
            
            logger.info(f"時刻フィルタリング: {len(df)} -> {len(filtered_df)}")
            
            return filtered_df
            
        except Exception as e:
            logger.error(f"時刻フィルタリングエラー: {e}")
            return df
    
    @staticmethod
    def _calculate_surgery_minutes_debug(df: pd.DataFrame) -> int:
        """手術時間の合計を分単位で計算（デバッグ版）"""
        try:
            if df.empty:
                logger.info("手術時間計算: データが空")
                return 0
            
            logger.info(f"手術時間計算開始: {len(df)}件")
            
            # 手術時間の列を探す
            duration_columns = ['手術時間', '所要時間', '手術時間（分）', 'duration', 'surgery_time', '実施時間', 'OP時間']
            duration_column = None
            
            for col in duration_columns:
                if col in df.columns:
                    duration_column = col
                    logger.info(f"手術時間列を発見: {duration_column}")
                    break
            
            if duration_column:
                try:
                    # 手術時間データのサンプルをログ出力
                    sample_durations = df[duration_column].dropna().head(10).tolist()
                    logger.info(f"手術時間サンプル: {sample_durations}")
                    
                    total_minutes = df[duration_column].fillna(0).sum()
                    logger.info(f"手術時間列から合計: {total_minutes}分")
                    return int(total_minutes)
                except Exception as e:
                    logger.warning(f"手術時間列 {duration_column} の計算でエラー: {e}")
            
            # 手術時間列がない場合、開始時刻と終了時刻から計算
            start_columns = ['手術開始時刻', '開始時刻', '手術開始時間', 'OP開始時刻']
            end_columns = ['手術終了時刻', '終了時刻', '手術終了時間', 'OP終了時刻']
            
            start_col = None
            end_col = None
            
            for col in start_columns:
                if col in df.columns:
                    start_col = col
                    break
            
            for col in end_columns:
                if col in df.columns:
                    end_col = col
                    break
            
            logger.info(f"開始時刻列: {start_col}, 終了時刻列: {end_col}")
            
            if start_col and end_col:
                def time_to_minutes(time_str):
                    if pd.isna(time_str) or time_str == '':
                        return None
                    try:
                        time_str = str(time_str).strip()
                        if ':' in time_str:
                            hour, minute = time_str.split(':')
                            return int(hour) * 60 + int(minute)
                    except:
                        return None
                
                df_calc = df.copy()
                df_calc['start_min'] = df_calc[start_col].apply(time_to_minutes)
                df_calc['end_min'] = df_calc[end_col].apply(time_to_minutes)
                
                # サンプルデータをログ出力
                sample_data = df_calc[['start_min', 'end_min']].dropna().head(5)
                logger.info(f"開始・終了時刻サンプル:\n{sample_data}")
                
                # 終了時刻が開始時刻より小さい場合は翌日とみなす
                df_calc.loc[df_calc['end_min'] < df_calc['start_min'], 'end_min'] += 24 * 60
                
                df_calc['duration'] = df_calc['end_min'] - df_calc['start_min']
                
                # 妥当性チェック（0分〜12時間以内）
                valid_durations = df_calc[
                    (df_calc['duration'] >= 0) & 
                    (df_calc['duration'] <= 720) & 
                    (df_calc['duration'].notna())
                ]['duration']
                
                logger.info(f"有効な手術時間データ: {len(valid_durations)}件")
                if len(valid_durations) > 0:
                    logger.info(f"手術時間統計: 平均{valid_durations.mean():.1f}分, 合計{valid_durations.sum():.0f}分")
                
                return int(valid_durations.sum())
            
            # フォールバック：件数ベースで推定（平均60分/件と仮定）
            logger.warning("手術時間を計算できないため、件数ベースで推定（60分/件）")
            estimated_minutes = len(df) * 60
            logger.info(f"推定手術時間: {estimated_minutes}分 ({len(df)}件 × 60分)")
            return estimated_minutes
            
        except Exception as e:
            logger.error(f"手術時間計算エラー: {e}")
            fallback_minutes = len(df) * 60
            logger.info(f"エラー時フォールバック: {fallback_minutes}分")
    @staticmethod
    @safe_data_operation("KPI計算")
    def _render_kpi_section_with_data(df: pd.DataFrame, latest_date: Optional[pd.Timestamp], 
                          start_date: Optional[pd.Timestamp], end_date: Optional[pd.Timestamp]) -> Dict[str, Any]:
        """KPIセクションを描画し、データも返す"""
        st.header("📊 主要指標 (選択期間)")
        
        try:
            # 選択された期間でデータをフィルタリング
            if start_date and end_date:
                period_df = df[
                    (df['手術実施日_dt'] >= start_date) & 
                    (df['手術実施日_dt'] <= end_date)
                ]
            else:
                # フォールバック: 元の関数を使用
                kpi_summary = ranking.get_kpi_summary(df, latest_date)
                generic_plots.display_kpi_metrics(kpi_summary)
                return {}
            
            # KPIサマリーを計算（選択期間用）
            kpi_data = DashboardPage._calculate_period_kpi(period_df, start_date, end_date)
            
            # KPI表示（直接メトリクス表示）
            DashboardPage._display_period_kpi_metrics(kpi_data, start_date, end_date)
            
            return kpi_data
            
        except Exception as e:
            logger.error(f"KPI計算エラー: {e}")
            st.error("KPI計算中にエラーが発生しました")
            return {}
    
    @staticmethod
    @safe_data_operation("パフォーマンスダッシュボード表示")
    def _render_performance_dashboard_with_data(df: pd.DataFrame, target_dict: Dict[str, Any], 
                                    latest_date: Optional[pd.Timestamp],
                                    start_date: Optional[pd.Timestamp], 
                                    end_date: Optional[pd.Timestamp]) -> pd.DataFrame:
        """診療科別パフォーマンスダッシュボードを表示し、データも返す"""
        st.markdown("---")
        st.header("📊 診療科別パフォーマンスダッシュボード")
        
        if start_date and end_date:
            st.caption(f"🗓️ 分析対象期間: {start_date.strftime('%Y/%m/%d')} ~ {end_date.strftime('%Y/%m/%d')}")
        
        # パフォーマンスサマリーを取得
        try:
            # 選択期間でデータをフィルタリング
            if start_date and end_date:
                period_df = df[
                    (df['手術実施日_dt'] >= start_date) & 
                    (df['手術実施日_dt'] <= end_date)
                ]
            else:
                period_df = df
            
            perf_summary = DashboardPage._calculate_period_performance(period_df, target_dict, start_date, end_date)
            
            if not perf_summary.empty:
                if '達成率(%)' not in perf_summary.columns:
                    st.warning("パフォーマンスデータに達成率の列が見つかりません。")
                    return pd.DataFrame()
                
                # 達成率順にソート
                sorted_perf = perf_summary.sort_values("達成率(%)", ascending=False)
                
                # パフォーマンスカードの表示
                DashboardPage._render_performance_cards(sorted_perf)
                
                # HTMLエクスポートボタンを追加
                DashboardPage._render_performance_html_export(sorted_perf, start_date, end_date)
                
                # 詳細データテーブル
                with st.expander("📋 詳細データテーブル"):
                    # CSVダウンロードボタン
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.dataframe(sorted_perf, use_container_width=True)
                    
                    with col2:
                        # CSVデータの準備
                        if start_date and end_date:
                            period_label = f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
                        else:
                            period_label = "全期間"
                        
                        # CSVデータの準備（日本語対応）
                        csv_string = sorted_perf.to_csv(index=False)
                        csv_data = '\ufeff' + csv_string  # BOM付きUTF-8
                        
                        st.download_button(
                            label="📥 CSVダウンロード",
                            data=csv_data.encode('utf-8'),
                            file_name=f"診療科別パフォーマンス_{period_label}_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv; charset=utf-8",
                            help="診療科別パフォーマンスデータをCSVファイルとしてダウンロード",
                            use_container_width=True
                        )
                
                return sorted_perf
            else:
                st.info("診療科別パフォーマンスを計算する十分なデータがありません。")
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"パフォーマンス計算エラー: {e}")
            logger.error(f"パフォーマンス計算エラー: {e}")
            return pd.DataFrame()

    @staticmethod
    def _render_performance_html_export(sorted_perf: pd.DataFrame, 
                                    start_date: Optional[pd.Timestamp], 
                                    end_date: Optional[pd.Timestamp]) -> None:
        """パフォーマンスカードのHTMLエクスポートボタンを表示"""
        
        def get_color_for_rate(rate):
            if rate >= 100:
                return "#28a745"
            if rate >= 80:
                return "#ffc107"
            return "#dc3545"
        
        # HTMLカードを生成
        html_cards = ""
        for idx, row in sorted_perf.iterrows():
            rate = row["達成率(%)"]
            color = get_color_for_rate(rate)
            bar_width = min(rate, 100)
            
            # 期間平均の表示名を動的に決定
            period_label = "期間平均" if "期間平均" in row.index else "4週平均"
            period_value = row.get("期間平均", row.get("4週平均", 0))
            
            card_html = f"""
            <div class="metric-card" style="
                background-color: {color}1A; 
                border-left: 5px solid {color}; 
                padding: 12px; 
                border-radius: 5px; 
                height: 165px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
            ">
                <h5 style="margin: 0 0 10px 0; font-weight: bold; color: #333;">{row["診療科"]}</h5>
                <div style="display: flex; justify-content: space-between; font-size: 0.9em;">
                    <span>{period_label}:</span>
                    <span style="font-weight: bold;">{period_value:.1f} 件</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.9em;">
                    <span>直近週実績:</span>
                    <span style="font-weight: bold;">{row["直近週実績"]:.0f} 件</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.9em; color: #666;">
                    <span>目標:</span>
                    <span>{row["週次目標"]:.1f} 件</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 1.1em; color: {color}; margin-top: 5px;">
                    <span style="font-weight: bold;">達成率:</span>
                    <span style="font-weight: bold;">{rate:.1f}%</span>
                </div>
                <div style="background-color: #e9ecef; border-radius: 5px; height: 6px; margin-top: 5px;">
                    <div style="width: {bar_width}%; background-color: {color}; height: 6px; border-radius: 5px;"></div>
                </div>
            </div>
            """
            html_cards += f'<div class="grid-item">{card_html}</div>'
        
        # 期間の説明文を生成
        if start_date and end_date:
            period_desc = f"{start_date.strftime('%Y/%m/%d')} ~ {end_date.strftime('%Y/%m/%d')}"
        else:
            period_desc = "全期間"
        
        # レスポンシブグリッドレイアウトのHTMLテンプレート
        html_content = f"""<!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>診療科別パフォーマンスダッシュボード - {period_desc}</title>
        <style>
            body {{
                background: #f5f7fa;
                font-family: 'Noto Sans JP', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                color: #333;
            }}
            
            h1 {{
                text-align: center;
                color: #293a27;
                margin-bottom: 10px;
                font-size: 24px;
            }}
            
            .subtitle {{
                text-align: center;
                color: #666;
                margin-bottom: 30px;
                font-size: 14px;
            }}
            
            .grid-container {{
                display: grid;
                gap: 20px;
                max-width: 1920px;
                margin: 0 auto;
            }}
            
            /* デフォルト: 3列レイアウト */
            .grid-container {{
                grid-template-columns: repeat(3, 1fr);
            }}
            
            /* 大画面: 4列レイアウト */
            @media (min-width: 1400px) {{
                .grid-container {{
                    grid-template-columns: repeat(4, 1fr);
                }}
            }}
            
            /* 超大画面: 5列レイアウト */
            @media (min-width: 1800px) {{
                .grid-container {{
                    grid-template-columns: repeat(5, 1fr);
                }}
            }}
            
            /* タブレット: 2列レイアウト */
            @media (max-width: 900px) {{
                .grid-container {{
                    grid-template-columns: repeat(2, 1fr);
                }}
            }}
            
            /* モバイル: 1列レイアウト */
            @media (max-width: 600px) {{
                .grid-container {{
                    grid-template-columns: 1fr;
                }}
            }}
            
            .grid-item {{
                min-height: 165px;
            }}
            
            .metric-card {{
                transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }}
            
            .metric-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }}
            
            .summary {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 30px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            
            .summary-stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                text-align: center;
            }}
            
            .stat-item {{
                padding: 10px;
            }}
            
            .stat-value {{
                font-size: 24px;
                font-weight: bold;
                color: #293a27;
            }}
            
            .stat-label {{
                font-size: 14px;
                color: #666;
                margin-top: 5px;
            }}
            
            @media print {{
                body {{
                    padding: 10px;
                }}
                .grid-container {{
                    grid-template-columns: repeat(3, 1fr);
                    gap: 15px;
                }}
                .metric-card:hover {{
                    transform: none;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                }}
            }}
        </style>
    </head>
    <body>
        <h1>診療科別パフォーマンスダッシュボード</h1>
        <div class="subtitle">分析期間: {period_desc}</div>
        
        <div class="summary">
            <div class="summary-stats">
                <div class="stat-item">
                    <div class="stat-value">{len(sorted_perf)}</div>
                    <div class="stat-label">診療科数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{len(sorted_perf[sorted_perf['達成率(%)'] >= 100])}</div>
                    <div class="stat-label">目標達成科数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">{sorted_perf['達成率(%)'].mean():.1f}%</div>
                    <div class="stat-label">平均達成率</div>
                </div>
            </div>
        </div>
        
        <div class="grid-container">
            {html_cards}
        </div>
        
        <div style="text-align: center; margin-top: 40px; color: #999; font-size: 12px;">
            生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}
        </div>
    </body>
    </html>
    """
        
        # ダウンロードボタン
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info("📄 パフォーマンスカードをHTMLファイルとしてダウンロードできます。ブラウザで開くとインタラクティブに表示されます。")
        
        with col2:
            st.download_button(
                label="📥 HTMLダウンロード",
                data=html_content.encode("utf-8"),
                file_name=f"診療科別パフォーマンス_{datetime.now().strftime('%Y%m%d')}.html",
                mime="text/html",
                help="診療科別パフォーマンスカードをHTMLファイルとしてダウンロード",
                type="primary",
                use_container_width=True
            )

    @staticmethod
    def _render_pdf_export_section(kpi_data: Dict[str, Any], 
                                 performance_data: pd.DataFrame,
                                 period_name: str,
                                 start_date: Optional[pd.Timestamp],
                                 end_date: Optional[pd.Timestamp],
                                 charts: Dict[str, Any] = None) -> None:
        """PDF出力セクションを表示"""
        
        st.markdown("---")
        st.header("📄 レポート出力")
        
        if not PDF_EXPORT_AVAILABLE:
            st.warning("📋 PDF出力機能を使用するには以下のライブラリのインストールが必要です:")
            st.code("pip install reportlab")
            st.info("現在は表示のみの機能です。PDF出力を有効にするには管理者にお問い合わせください。")
            return
        
        # PDF出力の説明
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            **📊 レポート内容:**
            - エグゼクティブサマリー
            - 主要業績指標 (KPI)
            - 診療科別パフォーマンス
            - 手術室稼働率詳細
            - 週次推移グラフ
            """)
        
        with col2:
            if start_date and end_date:
                # 期間情報を作成
                total_days = (end_date - start_date).days + 1
                weekdays = kpi_data.get('weekdays', 0)
                
                period_info = StreamlitPDFExporter.create_period_info(
                    period_name, start_date, end_date, total_days, weekdays
                )
                
                # PDFダウンロードボタン
                if st.button("📄 PDFレポート生成", type="primary", use_container_width=True):
                    with st.spinner("PDFレポートを生成中..."):
                        try:
                            StreamlitPDFExporter.add_pdf_download_button(
                                kpi_data=kpi_data,
                                performance_data=performance_data,
                                period_info=period_info,
                                charts=charts,
                                button_label="📥 PDFをダウンロード"
                            )
                        except Exception as e:
                            st.error(f"PDF生成でエラーが発生しました: {e}")
                            logger.error(f"PDF生成エラー: {e}")
            else:
                st.error("期間データが不正です。PDF生成できません。")
        
        # PDF内容のプレビュー
        with st.expander("📋 レポート内容プレビュー"):
            if kpi_data:
                st.write("**主要指標:**")
                st.write(f"• 全身麻酔手術件数: {kpi_data.get('gas_cases', 0):,}件")
                st.write(f"• 全手術件数: {kpi_data.get('total_cases', 0):,}件")
                st.write(f"• 平日1日あたり: {kpi_data.get('daily_avg_gas', 0):.1f}件/日")
                st.write(f"• 手術室稼働率: {kpi_data.get('utilization_rate', 0):.1f}%")
            
            if not performance_data.empty:
                st.write(f"**診療科別パフォーマンス:** {len(performance_data)}科のデータ")
                high_performers = len(performance_data[performance_data['達成率(%)'] >= 100])
                st.write(f"• 目標達成科数: {high_performers}科")
                
            if charts:
                st.write(f"**グラフ:** {len(charts)}個のグラフを含む")
        
        st.info("💡 PDFレポートには現在表示されている期間のデータが含まれます。期間を変更してから生成することで、異なる期間のレポートを作成できます。")
    
    @staticmethod
    def _filter_operating_hours(df: pd.DataFrame) -> pd.DataFrame:
        """9:00〜17:15の手術をフィルタリング"""
        # 実データ対応版を呼び出し
        return DashboardPage._filter_operating_hours_fixed(df)
    
    @staticmethod
    @safe_data_operation("KPI計算")
    def _render_kpi_section(df: pd.DataFrame, latest_date: Optional[pd.Timestamp], 
                          start_date: Optional[pd.Timestamp], end_date: Optional[pd.Timestamp]) -> None:
        """KPIセクションを描画（互換性のため）"""
        DashboardPage._render_kpi_section_with_data(df, latest_date, start_date, end_date)
    
    @staticmethod
    @safe_data_operation("パフォーマンスダッシュボード表示")  
    def _render_performance_dashboard(df: pd.DataFrame, target_dict: Dict[str, Any], 
                                    latest_date: Optional[pd.Timestamp],
                                    start_date: Optional[pd.Timestamp], 
                                    end_date: Optional[pd.Timestamp]) -> None:
        """診療科別パフォーマンスダッシュボードを表示（互換性のため）"""
        DashboardPage._render_performance_dashboard_with_data(df, target_dict, latest_date, start_date, end_date)
    
    @staticmethod
    def _filter_operating_hours(df: pd.DataFrame) -> pd.DataFrame:
        """9:00〜17:15の手術をフィルタリング"""
        # 実データ対応版を呼び出し
        return DashboardPage._filter_operating_hours_fixed(df)
    
    @staticmethod
    def _calculate_surgery_minutes(df: pd.DataFrame) -> int:
        """手術時間の合計を分単位で計算"""
        # 実データ対応版を呼び出し
        return DashboardPage._calculate_surgery_minutes_fixed(df)
    
    @staticmethod
    def _filter_operating_hours_fixed(df: pd.DataFrame) -> pd.DataFrame:
        """手術室稼働率計算用のフィルタリング（実データ対応版）"""
        try:
            if df.empty:
                return df
            
            # 手術室稼働率計算では、全ての手術を対象とする
            # 時刻による除外は稼働時間計算時に9:00〜17:15の範囲で調整
            logger.info("手術室稼働率計算: 全手術を対象（時刻調整は稼働時間計算時に実施）")
            
            # 入退室時刻が有効なデータのみをフィルタリング
            if '入室時刻' in df.columns and '退室時刻' in df.columns:
                def has_valid_time(time_str):
                    if pd.isna(time_str) or time_str == '':
                        return False
                    try:
                        time_str = str(time_str).strip()
                        if ':' in time_str:
                            hour, minute = time_str.split(':')
                            return 0 <= int(hour) <= 23 and 0 <= int(minute) <= 59
                        elif len(time_str) == 4 and time_str.isdigit():
                            hour = int(time_str[:2])
                            minute = int(time_str[2:])
                            return 0 <= hour <= 23 and 0 <= minute <= 59
                        return False
                    except:
                        return False
                
                # 有効な入退室時刻を持つデータのみ
                valid_df = df[
                    df['入室時刻'].apply(has_valid_time) & 
                    df['退室時刻'].apply(has_valid_time)
                ].copy()
                
                logger.info(f"有効な入退室時刻データ: {len(df)} -> {len(valid_df)}")
                
                return valid_df
            else:
                logger.warning("入室時刻または退室時刻の列が見つかりません - 全データを返します")
                return df
            
        except Exception as e:
            logger.error(f"データフィルタリングエラー: {e}")
            return df
    
    @staticmethod
    def _calculate_surgery_minutes_fixed(df: pd.DataFrame) -> int:
        """手術時間の合計を分単位で計算（実データ対応版）"""
        try:
            if df.empty:
                logger.info("手術時間計算: データが空")
                return 0
            
            logger.info(f"手術時間計算開始: {len(df)}件")
            
            # 入室時刻と退室時刻から実際の稼働時間を計算
            if '入室時刻' in df.columns and '退室時刻' in df.columns:
                logger.info("入室時刻と退室時刻から実際の稼働時間を計算")
                
                def time_to_minutes(time_str):
                    if pd.isna(time_str) or time_str == '':
                        return None
                    try:
                        time_str = str(time_str).strip()
                        if ':' in time_str:
                            hour, minute = time_str.split(':')
                            return int(hour) * 60 + int(minute)
                        elif len(time_str) == 4 and time_str.isdigit():
                            hour = int(time_str[:2])
                            minute = int(time_str[2:])
                            return hour * 60 + minute
                    except:
                        return None
                
                df_calc = df.copy()
                df_calc['entry_min'] = df_calc['入室時刻'].apply(time_to_minutes)
                df_calc['exit_min'] = df_calc['退室時刻'].apply(time_to_minutes)
                
                # 有効なデータをフィルタリング
                valid_data = df_calc[
                    df_calc['entry_min'].notna() & 
                    df_calc['exit_min'].notna()
                ].copy()
                
                if len(valid_data) == 0:
                    logger.warning("有効な入退室時刻データが0件")
                    return len(df) * 90
                
                logger.info(f"有効な入退室時刻データ: {len(valid_data)}件")
                
                # 終了時刻が開始時刻より小さい場合は翌日とみなす（深夜手術対応）
                valid_data.loc[valid_data['exit_min'] < valid_data['entry_min'], 'exit_min'] += 24 * 60
                
                # 手術室稼働時間の範囲制限: 9:00（540分）〜17:15（1035分）
                # 入室時刻の調整：9:00より前は9:00として計算
                valid_data['adjusted_entry'] = valid_data['entry_min'].apply(lambda x: max(x, 540))
                
                # 退室時刻の調整：17:15より後は17:15として計算
                valid_data['adjusted_exit'] = valid_data['exit_min'].apply(lambda x: min(x, 1035))
                
                # 調整後の稼働時間を計算
                valid_data['actual_duration'] = valid_data['adjusted_exit'] - valid_data['adjusted_entry']
                
                # 負の値（17:15より前に入室して9:00より前に退室など）を除外
                reasonable_durations = valid_data[valid_data['actual_duration'] > 0]['actual_duration']
                
                if len(reasonable_durations) > 0:
                    total_minutes = int(reasonable_durations.sum())
                    avg_duration = reasonable_durations.mean()
                    
                    logger.info(f"実際の稼働時間: {total_minutes}分 ({len(reasonable_durations)}件)")
                    logger.info(f"平均稼働時間: {avg_duration:.1f}分/件")
                    
                    # サンプルデータをログ出力
                    sample_data = valid_data[['entry_min', 'exit_min', 'adjusted_entry', 'adjusted_exit', 'actual_duration']].head(5)
                    logger.info(f"稼働時間計算サンプル:\n{sample_data}")
                    
                    return total_minutes
                else:
                    logger.warning("調整後の有効な稼働時間が0件")
            
            else:
                logger.warning("入室時刻または退室時刻の列が見つかりません")
                available_time_cols = [col for col in df.columns if '時刻' in col or '時間' in col]
                logger.info(f"利用可能な時刻関連列: {available_time_cols}")
            
            # フォールバック：件数ベースで推定
            logger.warning("実際の稼働時間を計算できないため、件数ベースで推定（90分/件）")
            estimated_minutes = len(df) * 90
            logger.info(f"推定稼働時間: {estimated_minutes}分 ({len(df)}件 × 90分)")
            return estimated_minutes
            
        except Exception as e:
            logger.error(f"稼働時間計算エラー: {e}")
            fallback_minutes = len(df) * 90
            logger.info(f"エラー時フォールバック: {fallback_minutes}分")
            return fallback_minutes
    
    @staticmethod
    def _display_period_kpi_metrics(kpi_data: Dict[str, Any], 
                                   start_date: Optional[pd.Timestamp], 
                                   end_date: Optional[pd.Timestamp]) -> None:
        """選択期間のKPI指標を表示"""
        if not kpi_data:
            st.warning("KPIデータが計算できませんでした")
            return
        
        # メトリクス表示
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            gas_cases = kpi_data.get('gas_cases', 0)
            st.metric(
                "🔴 全身麻酔手術件数",
                f"{gas_cases:,}件",
                help="選択期間内の全身麻酔手術（20分以上）総件数"
            )
        
        with col2:
            total_cases = kpi_data.get('total_cases', 0)
            st.metric(
                "📊 全手術件数",
                f"{total_cases:,}件",
                help="選択期間内の全手術総件数"
            )
        
        with col3:
            daily_avg_gas = kpi_data.get('daily_avg_gas', 0)
            # 目標との比較
            from config.hospital_targets import HospitalTargets
            hospital_target = HospitalTargets.get_daily_target()
            delta_gas = daily_avg_gas - hospital_target if hospital_target > 0 else 0
            
            st.metric(
                "📈 平日1日あたり全身麻酔手術件数",
                f"{daily_avg_gas:.1f}件/日",
                delta=f"{delta_gas:+.1f}件" if hospital_target > 0 else None,
                help="平日（月〜金）の1日あたり全身麻酔手術件数"
            )
        
        with col4:
            utilization = kpi_data.get('utilization_rate', 0)
            actual_minutes = kpi_data.get('actual_minutes', 0)
            max_minutes = kpi_data.get('max_minutes', 0)
            
            # 時間を見やすい形式に変換
            actual_hours = actual_minutes / 60
            max_hours = max_minutes / 60
            
            st.metric(
                "🏥 手術室稼働率",
                f"{utilization:.1f}%",
                delta=f"{actual_hours:.1f}h / {max_hours:.1f}h",
                help="OP-1〜12（11A,11Bを除く）11室の平日9:00〜17:15稼働率"
            )
        
        # 補足情報
        if start_date and end_date:
            period_days = kpi_data.get('period_days', 0)
            weekdays = kpi_data.get('weekdays', 0)
            actual_minutes = kpi_data.get('actual_minutes', 0)
            max_minutes = kpi_data.get('max_minutes', 0)
            
            st.caption(
                f"📅 分析期間: {start_date.strftime('%Y/%m/%d')} ～ {end_date.strftime('%Y/%m/%d')} "
                f"({period_days}日間, 平日{weekdays}日) | "
                f"実際稼働: {actual_minutes:,}分, 最大稼働: {max_minutes:,}分"
            )
    
    @staticmethod
    def _render_analysis_period_info(latest_date: Optional[pd.Timestamp], 
                                   period: str, start_date: Optional[pd.Timestamp], 
                                   end_date: Optional[pd.Timestamp]) -> None:
        """分析期間情報を表示"""
        if not latest_date or not start_date or not end_date:
            return
        
        st.markdown("---")
    
    @staticmethod
    @safe_data_operation("パフォーマンスダッシュボード表示")
    def _render_performance_dashboard(df: pd.DataFrame, target_dict: Dict[str, Any], 
                                    latest_date: Optional[pd.Timestamp],
                                    start_date: Optional[pd.Timestamp], 
                                    end_date: Optional[pd.Timestamp]) -> None:
        """診療科別パフォーマンスダッシュボードを表示"""
        st.markdown("---")
        st.header("📊 診療科別パフォーマンスダッシュボード")
        
        if start_date and end_date:
            st.caption(f"🗓️ 分析対象期間: {start_date.strftime('%Y/%m/%d')} ~ {end_date.strftime('%Y/%m/%d')}")
        
        # パフォーマンスサマリーを取得
        try:
            # 選択期間でデータをフィルタリング
            if start_date and end_date:
                period_df = df[
                    (df['手術実施日_dt'] >= start_date) & 
                    (df['手術実施日_dt'] <= end_date)
                ]
            else:
                period_df = df
            
            perf_summary = DashboardPage._calculate_period_performance(period_df, target_dict, start_date, end_date)
            
            if not perf_summary.empty:
                if '達成率(%)' not in perf_summary.columns:
                    st.warning("パフォーマンスデータに達成率の列が見つかりません。")
                    return
                
                # 達成率順にソート
                sorted_perf = perf_summary.sort_values("達成率(%)", ascending=False)
                
                # パフォーマンスカードの表示
                DashboardPage._render_performance_cards(sorted_perf)
                
                # 詳細データテーブル
                with st.expander("📋 詳細データテーブル"):
                    # CSVダウンロードボタン
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.dataframe(sorted_perf, use_container_width=True)
                    
                    with col2:
                        # CSVデータの準備（日本語対応）
                        csv_string = sorted_perf.to_csv(index=False)
                        csv_data = '\ufeff' + csv_string  # BOM付きUTF-8
                        
                        st.download_button(
                            label="📥 CSVダウンロード",
                            data=csv_data.encode('utf-8'),
                            file_name=f"診療科別パフォーマンス_{period_label}_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv; charset=utf-8",
                            help="診療科別パフォーマンスデータをCSVファイルとしてダウンロード",
                            use_container_width=True
                        )
            else:
                st.info("診療科別パフォーマンスを計算する十分なデータがありません。")
                
        except Exception as e:
            st.error(f"パフォーマンス計算エラー: {e}")
            logger.error(f"パフォーマンス計算エラー: {e}")
    
    @staticmethod
    def _calculate_period_performance(df: pd.DataFrame, target_dict: Dict[str, Any],
                                    start_date: Optional[pd.Timestamp], 
                                    end_date: Optional[pd.Timestamp]) -> pd.DataFrame:
        """選択期間の診療科別パフォーマンスを計算"""
        try:
            if df.empty or not target_dict:
                return pd.DataFrame()
            
            # 全身麻酔手術のみ
            gas_df = df[df['is_gas_20min'] == True] if 'is_gas_20min' in df.columns else df
            
            if gas_df.empty:
                return pd.DataFrame()
            
            # 診療科別集計
            dept_summary = []
            
            for dept, target_weekly in target_dict.items():
                if target_weekly <= 0:
                    continue
                
                dept_df = gas_df[gas_df['実施診療科'] == dept]
                
                if dept_df.empty:
                    continue
                
                # 期間の週数計算
                if start_date and end_date:
                    period_days = (end_date - start_date).days + 1
                    period_weeks = period_days / 7
                else:
                    period_weeks = 4
                
                # 実績計算
                total_cases = len(dept_df)
                weekly_avg = total_cases / period_weeks if period_weeks > 0 else 0
                
                # 最近の週の実績（最後の7日間）
                if end_date:
                    recent_week_start = end_date - pd.Timedelta(days=6)
                    recent_week_df = dept_df[dept_df['手術実施日_dt'] >= recent_week_start]
                    recent_week_cases = len(recent_week_df)
                else:
                    recent_week_cases = 0
                
                # 達成率計算（直近週ベース）
                achievement_rate = (recent_week_cases / target_weekly * 100) if target_weekly > 0 else 0
                
                dept_summary.append({
                    '診療科': dept,
                    '期間平均': weekly_avg,
                    '直近週実績': recent_week_cases,
                    '週次目標': target_weekly,
                    '達成率(%)': achievement_rate
                })
            
            return pd.DataFrame(dept_summary)
            
        except Exception as e:
            logger.error(f"期間パフォーマンス計算エラー: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def _render_performance_cards(sorted_perf: pd.DataFrame) -> None:
        """パフォーマンスカードを表示"""
        def get_color_for_rate(rate):
            if rate >= 100:
                return "#28a745"
            if rate >= 80:
                return "#ffc107"
            return "#dc3545"
        
        cols = st.columns(3)
        for i, (idx, row) in enumerate(sorted_perf.iterrows()):
            with cols[i % 3]:
                rate = row["達成率(%)"]
                color = get_color_for_rate(rate)
                bar_width = min(rate, 100)
                
                # 期間平均の表示名を動的に決定
                period_label = "期間平均" if "期間平均" in row.index else "4週平均"
                period_value = row.get("期間平均", row.get("4週平均", 0))
                
                html = f"""
                <div style="
                    background-color: {color}1A; 
                    border-left: 5px solid {color}; 
                    padding: 12px; 
                    border-radius: 5px; 
                    margin-bottom: 12px; 
                    height: 165px;
                ">
                    <h5 style="margin: 0 0 10px 0; font-weight: bold; color: #333;">{row["診療科"]}</h5>
                    <div style="display: flex; justify-content: space-between; font-size: 0.9em;">
                        <span>{period_label}:</span>
                        <span style="font-weight: bold;">{period_value:.1f} 件</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.9em;">
                        <span>直近週実績:</span>
                        <span style="font-weight: bold;">{row["直近週実績"]:.0f} 件</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 0.9em; color: #666;">
                        <span>目標:</span>
                        <span>{row["週次目標"]:.1f} 件</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 1.1em; color: {color}; margin-top: 5px;">
                        <span style="font-weight: bold;">達成率:</span>
                        <span style="font-weight: bold;">{rate:.1f}%</span>
                    </div>
                    <div style="background-color: #e9ecef; border-radius: 5px; height: 6px; margin-top: 5px;">
                        <div style="width: {bar_width}%; background-color: {color}; height: 6px; border-radius: 5px;"></div>
                    </div>
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)
    
    @staticmethod
    @safe_data_operation("目標達成状況サマリー")
    def _render_achievement_summary(df: pd.DataFrame, target_dict: Dict[str, Any], 
                                  latest_date: Optional[pd.Timestamp],
                                  start_date: Optional[pd.Timestamp], 
                                  end_date: Optional[pd.Timestamp]) -> None:
        """目標達成状況サマリーを表示"""
        st.markdown("---")
        st.header("🎯 目標達成状況サマリー")
        
        try:
            # 病院全体の目標達成状況
            from config.hospital_targets import HospitalTargets
            
            # 選択期間のデータを計算
            if start_date and end_date:
                period_df = df[
                    (df['手術実施日_dt'] >= start_date) & 
                    (df['手術実施日_dt'] <= end_date) &
                    (df['is_gas_20min'] == True)
                ]
                
                if not period_df.empty:
                    # 平日のみの日次平均を計算
                    weekday_df = period_df[period_df['is_weekday']]
                    if not weekday_df.empty:
                        total_days = (end_date - start_date).days + 1
                        weekdays = sum(1 for i in range(total_days) 
                                     if (start_date + pd.Timedelta(days=i)).weekday() < 5)
                        daily_avg = len(weekday_df) / weekdays if weekdays > 0 else 0
                        
                        hospital_target = HospitalTargets.get_daily_target()
                        achievement_rate = (daily_avg / hospital_target * 100) if hospital_target > 0 else 0
                        
                        # サマリーカード表示
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            st.metric(
                                "🏥 病院全体達成率", 
                                f"{achievement_rate:.1f}%",
                                delta=f"{achievement_rate - 100:.1f}%" if achievement_rate != 100 else "目標達成"
                            )
                        
                        with col2:
                            st.metric(
                                "📊 実績 (平日平均)", 
                                f"{daily_avg:.1f}件/日",
                                delta=f"{daily_avg - hospital_target:+.1f}件"
                            )
                        
                        with col3:
                            st.metric("🎯 目標", f"{hospital_target}件/日")
                        
                        with col4:
                            dept_count = len([k for k, v in target_dict.items() if v > 0]) if target_dict else 0
                            st.metric("📋 目標設定診療科", f"{dept_count}科")
                        
                        # 診療科別達成状況サマリー
                        if target_dict:
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.subheader("📈 診療科別達成状況")
                                ranking_data = ranking.calculate_achievement_rates(period_df, target_dict)
                                
                                if not ranking_data.empty:
                                    # TOP3とWORST3を表示
                                    top3 = ranking_data.head(3)
                                    st.write("**🏆 TOP 3:**")
                                    for idx, row in top3.iterrows():
                                        st.write(f"• {row['診療科']}: {row['達成率(%)']:.1f}%")
                            
                            with col2:
                                if len(ranking_data) >= 3:
                                    st.subheader("📉 要注意診療科")
                                    bottom3 = ranking_data.tail(3)
                                    st.write("**⚠️ 達成率が低い科:**")
                                    for idx, row in bottom3.iterrows():
                                        if row['達成率(%)'] < 80:
                                            st.write(f"• {row['診療科']}: {row['達成率(%)']:.1f}%")
                                    
                                    # 改善アクション提案
                                    low_performers = ranking_data[ranking_data['達成率(%)'] < 80]
                                    if not low_performers.empty:
                                        st.write("**💡 推奨アクション:**")
                                        st.write("• 個別面談実施")
                                        st.write("• リソース配分見直し")
                                        st.write("• 詳細分析実施")
                    else:
                        st.info("平日データが不足しています")
                else:
                    st.info("選択期間のデータがありません")
            else:
                st.info("期間設定エラー")
                
        except Exception as e:
            st.error(f"目標達成状況計算エラー: {e}")
            logger.error(f"目標達成状況計算エラー: {e}")
    
    @staticmethod
    def _show_help_dialog() -> None:
        """ヘルプダイアログを表示"""
        with st.expander("📖 ダッシュボードの使い方", expanded=True):
            st.markdown("""
            ### 🏠 ダッシュボード概要
            
            ダッシュボードは手術分析の中心となるページです。
            
            #### 📅 期間選択機能
            - **直近4週・8週・12週**: 最新データから指定週数分を分析
            - **今年度・昨年度**: 日本の年度（4月〜3月）での分析
            - 期間に応じて自動的にKPIや達成率を再計算
            
            #### 📊 主要指標 (KPI)
            - **全身麻酔手術件数**: 選択期間の全身麻酔手術の総件数
            - **全手術件数**: 選択期間の全手術総件数
            - **平日1日あたり全身麻酔手術件数**: 平日あたりの平均手術件数
            - **手術室稼働率**: OP-1〜12の時間ベース稼働率
            
            #### 🏆 診療科別パフォーマンス
            - 選択期間でのパフォーマンス評価
            - 達成率順のランキング表示
            - 診療科間の比較分析
            
            #### 🎯 目標達成状況
            - 病院全体の達成状況
            - TOP3とワースト3の診療科
            - 改善アクション提案
            """)


# ページルーター用の関数
def render():
    """ページルーター用のレンダー関数"""
    DashboardPage.render()