# ui/components/period_selector.py
"""
期間選択共通コンポーネント
複数ページで使用可能な期間選択機能を提供
"""

import streamlit as st
import pandas as pd
from typing import Tuple, Optional
import logging
from datetime import datetime

from ui.session_manager import SessionManager
from analysis import weekly

logger = logging.getLogger(__name__)


class PeriodSelector:
    """期間選択機能を提供するクラス"""
    
    # 期間オプションの定義
    PERIOD_OPTIONS = [
        "直近4週",
        "直近8週", 
        "直近12週",
        "今年度",
        "昨年度",
        "全期間"
    ]
    
    @staticmethod
    def render(page_name: str = "default", 
              show_info: bool = True,
              key_suffix: str = "") -> Tuple[str, Optional[pd.Timestamp], Optional[pd.Timestamp]]:
        """
        期間選択UIを描画し、選択された期間情報を返す
        
        Args:
            page_name: ページ名（セッション管理用）
            show_info: 期間情報の表示フラグ
            key_suffix: Streamlitキーの識別用サフィックス
            
        Returns:
            (期間名, 開始日, 終了日) のタプル
        """
        latest_date = SessionManager.get_latest_date()
        
        if not latest_date:
            st.warning("⚠️ データが読み込まれていないため、期間選択を利用できません")
            return "直近4週", None, None
        
        # セッションから現在の期間設定を取得
        session_key = f"selected_period_{page_name}"
        current_period = st.session_state.get(session_key, "直近4週")
        
        st.subheader("📅 分析期間選択")
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            selected_period = st.selectbox(
                "分析期間",
                PeriodSelector.PERIOD_OPTIONS,
                index=PeriodSelector.PERIOD_OPTIONS.index(current_period) if current_period in PeriodSelector.PERIOD_OPTIONS else 0,
                help="分析に使用する期間を選択してください",
                key=f"period_selector_{page_name}_{key_suffix}"
            )
            
            # セッションに選択された期間を保存
            st.session_state[session_key] = selected_period
        
        # 選択された期間に基づいて開始日・終了日を計算
        start_date, end_date = PeriodSelector._calculate_period_dates(selected_period, latest_date)
        
        with col2:
            if start_date and end_date and show_info:
                period_days = (end_date - start_date).days + 1
                st.info(
                    f"📊 **選択期間**: {selected_period}  \n"
                    f"📅 **分析範囲**: {start_date.strftime('%Y/%m/%d')} ～ {end_date.strftime('%Y/%m/%d')}  \n"
                    f"📈 **期間長**: {period_days}日間"
                )
            elif show_info:
                st.warning("期間計算でエラーが発生しました")
        
        return selected_period, start_date, end_date
    
    @staticmethod
    def _calculate_period_dates(period: str, latest_date: pd.Timestamp) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
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
            elif period == "全期間":
                # データの全期間を使用
                df = SessionManager.get_processed_df()
                if not df.empty and '手術実施日_dt' in df.columns:
                    start_date = df['手術実施日_dt'].min()
                    end_date = df['手術実施日_dt'].max()
                else:
                    return None, None
            else:
                return None, None
            
            return start_date, end_date
            
        except Exception as e:
            logger.error(f"期間計算エラー: {e}")
            return None, None
    
    @staticmethod
    def filter_data_by_period(df: pd.DataFrame, 
                             start_date: Optional[pd.Timestamp], 
                             end_date: Optional[pd.Timestamp]) -> pd.DataFrame:
        """期間に基づいてデータをフィルタリング"""
        if df.empty or start_date is None or end_date is None:
            return df
        
        try:
            if '手術実施日_dt' not in df.columns:
                logger.warning("手術実施日_dt列が見つかりません")
                return df
            
            filtered_df = df[
                (df['手術実施日_dt'] >= start_date) & 
                (df['手術実施日_dt'] <= end_date)
            ]
            
            logger.info(f"期間フィルタリング: {len(df)} -> {len(filtered_df)} 件")
            return filtered_df
            
        except Exception as e:
            logger.error(f"データフィルタリングエラー: {e}")
            return df
    
    @staticmethod
    def get_period_info(period_name: str, 
                       start_date: Optional[pd.Timestamp], 
                       end_date: Optional[pd.Timestamp]) -> dict:
        """期間情報の辞書を作成"""
        if not start_date or not end_date:
            return {
                'period_name': period_name,
                'start_date': 'N/A',
                'end_date': 'N/A',
                'total_days': 0,
                'weekdays': 0
            }
        
        total_days = (end_date - start_date).days + 1
        weekdays = sum(1 for i in range(total_days) 
                      if (start_date + pd.Timedelta(days=i)).weekday() < 5)
        
        return {
            'period_name': period_name,
            'start_date': start_date.strftime('%Y/%m/%d'),
            'end_date': end_date.strftime('%Y/%m/%d'),
            'total_days': total_days,
            'weekdays': weekdays
        }
    
    @staticmethod
    def render_period_summary(period_name: str, 
                             start_date: Optional[pd.Timestamp], 
                             end_date: Optional[pd.Timestamp],
                             filtered_df: pd.DataFrame) -> None:
        """期間サマリー情報を表示"""
        if not start_date or not end_date:
            return
        
        period_info = PeriodSelector.get_period_info(period_name, start_date, end_date)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📅 分析期間", period_info['period_name'])
        
        with col2:
            st.metric("📊 データ件数", f"{len(filtered_df):,}件")
        
        with col3:
            st.metric("📈 期間日数", f"{period_info['total_days']}日")
        
        with col4:
            st.metric("🗓️ 平日数", f"{period_info['weekdays']}日")
        
        st.caption(
            f"📅 分析期間: {period_info['start_date']} ～ {period_info['end_date']}"
        )
    
    @staticmethod
    def calculate_weekdays_in_period(start_date: pd.Timestamp, end_date: pd.Timestamp) -> int:
        """期間内の平日数を計算"""
        try:
            total_days = (end_date - start_date).days + 1
            weekdays = sum(1 for i in range(total_days) 
                          if (start_date + pd.Timedelta(days=i)).weekday() < 5)
            return weekdays
        except Exception as e:
            logger.error(f"平日数計算エラー: {e}")
            return 0
    
    @staticmethod
    def reset_period_selection(page_name: str) -> None:
        """指定ページの期間選択をリセット"""
        session_key = f"selected_period_{page_name}"
        if session_key in st.session_state:
            del st.session_state[session_key]
    
    @staticmethod
    def get_current_period(page_name: str) -> str:
        """現在選択されている期間を取得"""
        session_key = f"selected_period_{page_name}"
        return st.session_state.get(session_key, "直近4週")
    
    @staticmethod
    def render_period_comparison_metrics(current_df: pd.DataFrame,
                                       previous_df: pd.DataFrame,
                                       metric_name: str = "件数") -> None:
        """期間比較メトリクスを表示"""
        try:
            current_count = len(current_df)
            previous_count = len(previous_df)
            
            change = current_count - previous_count
            change_pct = (change / previous_count * 100) if previous_count > 0 else 0
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    f"現在期間{metric_name}",
                    f"{current_count:,}件"
                )
            
            with col2:
                st.metric(
                    f"前期間比較",
                    f"{previous_count:,}件",
                    delta=f"{change:+,}件 ({change_pct:+.1f}%)"
                )
                
        except Exception as e:
            logger.error(f"期間比較メトリクス表示エラー: {e}")
            st.warning("期間比較の計算中にエラーが発生しました")