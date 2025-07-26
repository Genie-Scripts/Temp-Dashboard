# analysis/surgery_high_score.py
"""
手術ダッシュボード用ハイスコア機能
診療科別の週次パフォーマンス評価とランキング
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Tuple, Any, Optional

logger = logging.getLogger(__name__)


def calculate_surgery_high_scores(df: pd.DataFrame, target_dict: Dict[str, float], 
                                period: str = "直近12週") -> List[Dict[str, Any]]:
    """
    手術データから診療科別ハイスコアを計算
    
    Args:
        df: 手術データ
        target_dict: 診療科別目標値辞書
        period: 分析期間
    
    Returns:
        診療科スコアリスト（スコア順）
    """
    try:
        if df.empty:
            logger.warning("手術データが空です")
            return []
        
        # 期間フィルタリング
        start_date, end_date = _get_period_dates(df, period)
        if not start_date or not end_date:
            logger.error("期間計算に失敗しました")
            return []
        
        period_df = df[
            (df['手術実施日_dt'] >= start_date) & 
            (df['手術実施日_dt'] <= end_date)
        ].copy()
        
        if period_df.empty:
            logger.warning(f"期間 {period} にデータがありません")
            return []
        
        # 週次データ準備
        weekly_df = _prepare_weekly_data(period_df)
        if weekly_df.empty:
            logger.warning("週次データの準備に失敗しました")
            return []
        
        # 診療科別スコア計算
        dept_scores = []
        departments = weekly_df['実施診療科'].dropna().unique()
        
        for dept in departments:
            dept_data = weekly_df[weekly_df['実施診療科'] == dept]
            if len(dept_data) < 3:  # 最小データ数チェック
                continue
            
            score_data = _calculate_department_score(
                dept_data, dept, target_dict, start_date, end_date
            )
            
            if score_data:
                dept_scores.append(score_data)
        
        # スコア順でソート
        dept_scores_sorted = sorted(dept_scores, key=lambda x: x['total_score'], reverse=True)
        
        logger.info(f"手術ハイスコア計算完了: {len(dept_scores_sorted)}診療科")
        return dept_scores_sorted
        
    except Exception as e:
        logger.error(f"手術ハイスコア計算エラー: {e}")
        return []


def _prepare_weekly_data(df: pd.DataFrame) -> pd.DataFrame:
    """週次データを準備"""
    try:
        weekly_df = df.copy()
        
        # 週開始日を計算（月曜始まり）
        weekly_df['week_start'] = weekly_df['手術実施日_dt'].dt.to_period('W-MON').dt.start_time
        
        # 手術時間計算（入退室時刻から）
        if '入室時刻' in weekly_df.columns and '退室時刻' in weekly_df.columns:
            weekly_df['手術時間_時間'] = _calculate_surgery_hours(
                weekly_df['入室時刻'], 
                weekly_df['退室時刻'], 
                weekly_df['手術実施日_dt']
            )
        else:
            # フォールバック: デフォルト値
            weekly_df['手術時間_時間'] = 2.0
        
        # 全身麻酔フラグの確認・作成
        if 'is_gas_20min' not in weekly_df.columns:
            # 麻酔種別から判定
            if '麻酔種別' in weekly_df.columns:
                weekly_df['is_gas_20min'] = weekly_df['麻酔種別'].str.contains(
                    '全身麻酔.*20分以上', na=False, regex=True
                )
            else:
                weekly_df['is_gas_20min'] = True  # デフォルトで全て対象
        
        # 平日フラグの確認・作成
        if 'is_weekday' not in weekly_df.columns:
            weekly_df['is_weekday'] = weekly_df['手術実施日_dt'].dt.weekday < 5
        
        return weekly_df
        
    except Exception as e:
        logger.error(f"週次データ準備エラー: {e}")
        return pd.DataFrame()


def _calculate_surgery_hours(entry_times, exit_times, surgery_dates) -> pd.Series:
    """入退室時刻から手術時間を計算（深夜跨ぎ対応）"""
    try:
        hours = pd.Series(0.0, index=entry_times.index)
        
        for idx in entry_times.index:
            try:
                entry_time = entry_times[idx]
                exit_time = exit_times[idx]
                surgery_date = surgery_dates[idx]
                
                if pd.isna(entry_time) or pd.isna(exit_time) or pd.isna(surgery_date):
                    hours[idx] = 2.0  # デフォルト値
                    continue
                
                # 時刻を文字列に変換
                entry_str = str(entry_time).strip()
                exit_str = str(exit_time).strip()
                
                # 時刻をdatetimeに変換
                entry_dt = _parse_time_to_datetime(entry_str, surgery_date)
                exit_dt = _parse_time_to_datetime(exit_str, surgery_date)
                
                if not entry_dt or not exit_dt:
                    hours[idx] = 2.0
                    continue
                
                # 深夜跨ぎの処理
                if exit_dt < entry_dt:
                    exit_dt += timedelta(days=1)
                
                # 手術時間を時間単位で計算
                duration = exit_dt - entry_dt
                hours[idx] = duration.total_seconds() / 3600
                
                # 妥当性チェック（0.5時間〜24時間）
                if not (0.5 <= hours[idx] <= 24):
                    hours[idx] = 2.0
                    
            except Exception:
                hours[idx] = 2.0
        
        return hours
        
    except Exception as e:
        logger.error(f"手術時間計算エラー: {e}")
        return pd.Series(2.0, index=entry_times.index)


def _parse_time_to_datetime(time_str: str, date_obj: pd.Timestamp) -> Optional[datetime]:
    """時刻文字列をdatetimeに変換"""
    try:
        if ':' in time_str:
            # HH:MM形式
            parts = time_str.split(':')
            if len(parts) >= 2:
                hour = int(parts[0])
                minute = int(parts[1])
                
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return datetime.combine(date_obj.date(), time(hour, minute))
        
        elif time_str.isdigit() and len(time_str) == 4:
            # HHMM形式
            hour = int(time_str[:2])
            minute = int(time_str[2:])
            
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return datetime.combine(date_obj.date(), time(hour, minute))
        
        return None
        
    except Exception:
        return None


def _calculate_department_score(dept_data: pd.DataFrame, dept_name: str, 
                               target_dict: Dict[str, float], 
                               start_date: pd.Timestamp, 
                               end_date: pd.Timestamp) -> Optional[Dict[str, Any]]:
    """診療科別スコアを計算"""
    try:
        # 週次集計
        weekly_stats = dept_data.groupby('week_start').agg({
            'is_gas_20min': 'sum',      # 週次全身麻酔件数
            '手術実施日_dt': 'count',    # 週次全手術件数  
            '手術時間_時間': 'sum'       # 週次総手術時間
        }).rename(columns={
            'is_gas_20min': 'weekly_gas_cases',
            '手術実施日_dt': 'weekly_total_cases',
            '手術時間_時間': 'weekly_total_hours'
        })
        
        if weekly_stats.empty:
            return None
        
        # 基本統計
        avg_gas_cases = weekly_stats['weekly_gas_cases'].mean()
        avg_total_cases = weekly_stats['weekly_total_cases'].mean()
        avg_total_hours = weekly_stats['weekly_total_hours'].mean()
        
        # 最新週実績
        latest_week = weekly_stats.index.max()
        latest_gas_cases = weekly_stats.loc[latest_week, 'weekly_gas_cases']
        latest_total_cases = weekly_stats.loc[latest_week, 'weekly_total_cases']
        latest_total_hours = weekly_stats.loc[latest_week, 'weekly_total_hours']
        
        # 目標との比較
        target_gas_cases = target_dict.get(dept_name, 0)
        achievement_rate = (latest_gas_cases / target_gas_cases * 100) if target_gas_cases > 0 else 0
        
        # スコア計算
        score_components = _calculate_score_components(
            weekly_stats, target_gas_cases, achievement_rate,
            avg_gas_cases, avg_total_cases, avg_total_hours,
            latest_gas_cases, latest_total_cases, latest_total_hours
        )
        
        total_score = sum(score_components.values())
        grade = _determine_grade(total_score)
        
        # 改善度計算
        improvement_rate = _calculate_improvement_rate(weekly_stats['weekly_gas_cases'])
        
        return {
            'entity_name': dept_name,
            'display_name': dept_name,
            'total_score': round(total_score, 1),
            'grade': grade,
            'latest_gas_cases': int(latest_gas_cases),
            'latest_total_cases': int(latest_total_cases),
            'latest_total_hours': round(latest_total_hours, 1),
            'avg_gas_cases': round(avg_gas_cases, 1),
            'avg_total_cases': round(avg_total_cases, 1),
            'avg_total_hours': round(avg_total_hours, 1),
            'target_gas_cases': target_gas_cases,
            'achievement_rate': round(achievement_rate, 1),
            'improvement_rate': round(improvement_rate, 1),
            'score_components': {k: round(v, 1) for k, v in score_components.items()},
            'latest_achievement_rate': round(achievement_rate, 1),
            'weekly_data': weekly_stats.to_dict('index')
        }
        
    except Exception as e:
        logger.error(f"診療科 {dept_name} のスコア計算エラー: {e}")
        return None


def _calculate_score_components(weekly_stats: pd.DataFrame, target_gas_cases: float,
                               achievement_rate: float, avg_gas_cases: float,
                               avg_total_cases: float, avg_total_hours: float,
                               latest_gas_cases: float, latest_total_cases: float,
                               latest_total_hours: float) -> Dict[str, float]:
    """スコア構成要素を計算"""
    
    # 1. 全身麻酔手術件数評価 (70点満点)
    gas_score = _calculate_gas_surgery_score(
        weekly_stats['weekly_gas_cases'], target_gas_cases, achievement_rate
    )
    
    # 2. 全手術件数評価 (15点満点)
    total_cases_score = _calculate_total_cases_score(
        latest_total_cases, avg_total_cases
    )
    
    # 3. 総手術時間評価 (15点満点)
    total_hours_score = _calculate_total_hours_score(
        latest_total_hours, avg_total_hours
    )
    
    return {
        'gas_surgery_score': gas_score,
        'total_cases_score': total_cases_score,
        'total_hours_score': total_hours_score
    }


def _calculate_gas_surgery_score(weekly_gas_cases: pd.Series, target: float, 
                                achievement_rate: float) -> float:
    """全身麻酔手術件数スコア (70点満点)"""
    
    # 直近週達成度 (30点)
    if achievement_rate >= 110:
        achievement_score = 30
    elif achievement_rate >= 100:
        achievement_score = 25
    elif achievement_rate >= 90:
        achievement_score = 20
    elif achievement_rate >= 80:
        achievement_score = 15
    else:
        achievement_score = max(0, achievement_rate / 80 * 15)
    
    # 改善度 (20点)
    improvement_rate = _calculate_improvement_rate(weekly_gas_cases)
    if improvement_rate >= 15:
        improvement_score = 20
    elif improvement_rate >= 10:
        improvement_score = 15
    elif improvement_rate >= 5:
        improvement_score = 10
    elif improvement_rate >= 0:
        improvement_score = 8
    else:
        improvement_score = max(0, 8 + improvement_rate * 0.4)
    
    # 安定性 (15点) - 変動係数
    variation_coeff = weekly_gas_cases.std() / weekly_gas_cases.mean() if weekly_gas_cases.mean() > 0 else 1
    if variation_coeff <= 0.2:
        stability_score = 15
    elif variation_coeff <= 0.4:
        stability_score = 12
    elif variation_coeff <= 0.6:
        stability_score = 8
    else:
        stability_score = max(0, 15 - variation_coeff * 10)
    
    # 持続性 (5点) - トレンド
    trend_score = _calculate_trend_score(weekly_gas_cases, 5)
    
    return achievement_score + improvement_score + stability_score + trend_score


def _calculate_total_cases_score(latest: float, avg: float) -> float:
    """全手術件数スコア (15点満点)"""
    # ランキング基準 (10点) + 改善度 (5点)
    improvement_rate = ((latest - avg) / avg * 100) if avg > 0 else 0
    
    # 改善度評価
    if improvement_rate >= 10:
        improvement_score = 5
    elif improvement_rate >= 5:
        improvement_score = 4
    elif improvement_rate >= 0:
        improvement_score = 3
    else:
        improvement_score = max(0, 3 + improvement_rate * 0.2)
    
    # ランキング評価（仮実装 - 実際は全診療科との比較が必要）
    ranking_score = min(10, latest / 20 * 10) if latest > 0 else 0
    
    return ranking_score + improvement_score


def _calculate_total_hours_score(latest: float, avg: float) -> float:
    """総手術時間スコア (15点満点)"""
    # 全手術件数と同じロジック
    return _calculate_total_cases_score(latest, avg)


def _calculate_improvement_rate(series: pd.Series) -> float:
    """改善率を計算"""
    try:
        if len(series) < 2:
            return 0
        
        # 後半と前半の平均を比較
        mid_point = len(series) // 2
        recent_avg = series.iloc[mid_point:].mean()
        early_avg = series.iloc[:mid_point].mean()
        
        if early_avg > 0:
            return (recent_avg - early_avg) / early_avg * 100
        else:
            return 0
            
    except Exception:
        return 0


def _calculate_trend_score(series: pd.Series, max_score: float) -> float:
    """トレンドスコアを計算"""
    try:
        if len(series) < 3:
            return max_score / 2
        
        # 線形回帰の傾き
        x = np.arange(len(series))
        slope, _ = np.polyfit(x, series, 1)
        
        # 正の傾きを評価
        if slope > 0:
            return max_score
        elif slope >= -0.5:
            return max_score * 0.7
        else:
            return max_score * 0.3
            
    except Exception:
        return max_score / 2


def _determine_grade(total_score: float) -> str:
    """総合スコアからグレード判定"""
    if total_score >= 85:
        return 'S'
    elif total_score >= 75:
        return 'A'
    elif total_score >= 65:
        return 'B'
    elif total_score >= 50:
        return 'C'
    else:
        return 'D'


def _get_period_dates(df: pd.DataFrame, period: str) -> Tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    """期間文字列から開始・終了日を取得"""
    try:
        if df.empty:
            return None, None
        
        latest_date = df['手術実施日_dt'].max()
        
        if period == "直近4週":
            weeks = 4
        elif period == "直近8週": 
            weeks = 8
        elif period == "直近12週":
            weeks = 12
        else:
            weeks = 12  # デフォルト
        
        # 最新日付から遡って期間を設定
        start_date = latest_date - pd.Timedelta(weeks=weeks) + pd.Timedelta(days=1)
        end_date = latest_date
        
        return start_date, end_date
        
    except Exception as e:
        logger.error(f"期間計算エラー: {e}")
        return None, None


def generate_surgery_high_score_summary(dept_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
    """ハイスコアサマリーを生成"""
    try:
        if not dept_scores:
            return {}
        
        # TOP3抽出
        top3 = dept_scores[:3]
        
        # 統計情報
        total_depts = len(dept_scores)
        avg_score = sum(d['total_score'] for d in dept_scores) / total_depts
        high_achievers = len([d for d in dept_scores if d['achievement_rate'] >= 100])
        
        return {
            'top3_departments': top3,
            'total_departments': total_depts,
            'average_score': round(avg_score, 1),
            'high_achievers_count': high_achievers,
            'evaluation_period': "診療科別週次パフォーマンス評価"
        }
        
    except Exception as e:
        logger.error(f"サマリー生成エラー: {e}")
        return {}