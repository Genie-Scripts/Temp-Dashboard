# high_score_calculator.py
"""
ハイスコア計算機能を専門に扱うモジュール
元のhtml_export_functions.pyから分離して保守性を向上
"""

import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# 設定モジュールのインポート
from config.scoring_config import ScoringConfig, DEFAULT_SCORING_CONFIG

# 必要なユーティリティのインポート
from utils import (
    get_period_dates,
    calculate_department_kpis,
    calculate_ward_kpis,
    get_target_ward_list
)
from config import EXCLUDED_WARDS

logger = logging.getLogger(__name__)

@dataclass
class ScoreResult:
    """スコア計算結果を格納するデータクラス"""
    entity_name: str
    entity_type: str  # 'dept' or 'ward'
    total_score: float
    achievement_score: float
    improvement_score: float
    stability_score: float
    sustainability_score: float
    bed_efficiency_score: float = 0
    latest_achievement_rate: float = 0
    improvement_rate: float = 0
    latest_inpatients: float = 0
    target_inpatients: float = 0
    period_avg: float = 0
    bed_utilization: float = 0
    display_name: Optional[str] = None  # 病棟の場合の表示名
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（後方互換性のため）"""
        result = {
            'entity_name': self.entity_name,
            'entity_type': self.entity_type,
            'total_score': self.total_score,
            'achievement_score': self.achievement_score,
            'improvement_score': self.improvement_score,
            'stability_score': self.stability_score,
            'sustainability_score': self.sustainability_score,
            'bed_efficiency_score': self.bed_efficiency_score,
            'latest_achievement_rate': self.latest_achievement_rate,
            'improvement_rate': self.improvement_rate,
            'latest_inpatients': self.latest_inpatients,
            'target_inpatients': self.target_inpatients,
            'period_avg': self.period_avg,
            'bed_utilization': self.bed_utilization,
        }
        if self.display_name:
            result['display_name'] = self.display_name
        return result

class HighScoreCalculator:
    """ハイスコア計算の専用クラス"""
    
    def __init__(self, config: ScoringConfig = None):
        """
        Args:
            config: スコア計算設定。Noneの場合はデフォルト設定を使用
        """
        self.config = config or DEFAULT_SCORING_CONFIG
        
    def calculate_all_high_scores(self, df: pd.DataFrame, target_data: pd.DataFrame, 
                                period: str = "直近12週") -> Tuple[List[ScoreResult], List[ScoreResult]]:
        """
        全ての診療科・病棟のハイスコアを計算
        
        Args:
            df: メインデータフレーム
            target_data: 目標データ
            period: 分析期間
            
        Returns:
            tuple: (診療科スコアリスト, 病棟スコアリスト)
        """
        try:
            start_date, end_date, _ = get_period_dates(df, period)
            if not start_date:
                logger.warning("分析期間を計算できませんでした")
                return [], []
            
            dept_scores = self._calculate_department_scores(df, target_data, start_date, end_date)
            ward_scores = self._calculate_ward_scores(df, target_data, start_date, end_date)
            
            # スコア順でソート
            dept_scores.sort(key=lambda x: x.total_score, reverse=True)
            ward_scores.sort(key=lambda x: x.total_score, reverse=True)
            
            logger.info(f"ハイスコア計算完了: 診療科{len(dept_scores)}件, 病棟{len(ward_scores)}件")
            return dept_scores, ward_scores
            
        except Exception as e:
            logger.error(f"全ハイスコア計算エラー: {e}")
            return [], []
    
    def _calculate_department_scores(self, df: pd.DataFrame, target_data: pd.DataFrame,
                                   start_date: pd.Timestamp, end_date: pd.Timestamp) -> List[ScoreResult]:
        """診療科のスコア計算"""
        dept_scores = []
        dept_col = '診療科名'
        
        if dept_col not in df.columns:
            logger.warning(f"列 '{dept_col}' が見つかりません")
            return dept_scores
        
        departments = sorted(df[dept_col].dropna().unique())
        for dept_name in departments:
            try:
                score = self.calculate_entity_score(
                    df, target_data, dept_name, 'dept', 
                    start_date, end_date, dept_col
                )
                if score:
                    dept_scores.append(score)
            except Exception as e:
                logger.error(f"診療科 '{dept_name}' のスコア計算エラー: {e}")
                
        return dept_scores
    
    def _calculate_ward_scores(self, df: pd.DataFrame, target_data: pd.DataFrame,
                             start_date: pd.Timestamp, end_date: pd.Timestamp) -> List[ScoreResult]:
        """病棟のスコア計算"""
        ward_scores = []
        
        try:
            all_wards = get_target_ward_list(target_data, EXCLUDED_WARDS)
            for ward_code, ward_name in all_wards:
                try:
                    score = self.calculate_entity_score(
                        df, target_data, ward_code, 'ward',
                        start_date, end_date, '病棟コード'
                    )
                    if score:
                        score.display_name = ward_name  # 表示用の名前を設定
                        ward_scores.append(score)
                except Exception as e:
                    logger.error(f"病棟 '{ward_name}' のスコア計算エラー: {e}")
        except Exception as e:
            logger.error(f"病棟スコア計算エラー: {e}")
            
        return ward_scores
    
    def calculate_entity_score(self, df: pd.DataFrame, target_data: pd.DataFrame, 
                             entity_name: str, entity_type: str,
                             start_date: pd.Timestamp, end_date: pd.Timestamp, 
                             group_col: Optional[str] = None) -> Optional[ScoreResult]:
        """
        個別エンティティのスコア計算
        
        Args:
            df: データフレーム
            target_data: 目標データ
            entity_name: エンティティ名
            entity_type: 'dept' または 'ward'
            start_date: 開始日
            end_date: 終了日
            group_col: グループ化に使用する列名
            
        Returns:
            ScoreResult または None
        """
        try:
            # 基本KPI取得
            if entity_type == 'dept':
                kpi = calculate_department_kpis(df, target_data, entity_name, entity_name, 
                                              start_date, end_date, group_col)
            else:
                kpi = calculate_ward_kpis(df, target_data, entity_name, entity_name, 
                                        start_date, end_date, group_col)
            
            if not kpi or not kpi.get('daily_census_target'):
                return None
            
            target_value = kpi['daily_census_target']
            
            # 対象データフィルタリング
            entity_df = df[df[group_col] == entity_name].copy() if group_col and entity_name else df.copy()
            if entity_df.empty:
                return None

            # 直近週データの処理
            recent_week_end = end_date
            recent_week_start = end_date - pd.Timedelta(days=6)
            recent_week_df = entity_df[
                (entity_df['日付'] >= recent_week_start) & 
                (entity_df['日付'] <= recent_week_end)
            ]
            
            if recent_week_df.empty:
                return None
                
            # 直近週の平均在院患者数計算
            recent_week_df_grouped = recent_week_df.groupby('日付')['在院患者数'].sum().reset_index()
            latest_week_avg_census = recent_week_df_grouped['在院患者数'].mean()

            # 各スコア構成要素の計算
            latest_achievement_rate = (latest_week_avg_census / target_value) * 100
            achievement_score = self._calculate_achievement_score(latest_achievement_rate)
            
            improvement_rate, period_avg = self._calculate_improvement_rate(
                entity_df, recent_week_start, latest_week_avg_census
            )
            improvement_score = self._calculate_improvement_score(improvement_rate)
            
            stability_score = self._calculate_stability_score(entity_df, start_date, end_date)
            sustainability_score = self._calculate_sustainability_score(entity_df, target_value, start_date, end_date)
            
            bed_efficiency_score = 0
            bed_utilization = 0
            if entity_type == 'ward' and kpi.get('bed_count', 0) > 0:
                bed_utilization = (latest_week_avg_census / kpi['bed_count']) * 100
                bed_efficiency_score = self._calculate_bed_efficiency_score(bed_utilization, latest_achievement_rate)
            
            # 総合スコア計算
            total_score = achievement_score + improvement_score + stability_score + sustainability_score + bed_efficiency_score
            total_score = min(105, max(0, total_score))  # 0-105点の範囲に制限
            
            return ScoreResult(
                entity_name=entity_name,
                entity_type=entity_type,
                total_score=total_score,
                achievement_score=achievement_score,
                improvement_score=improvement_score,
                stability_score=stability_score,
                sustainability_score=sustainability_score,
                bed_efficiency_score=bed_efficiency_score,
                latest_achievement_rate=latest_achievement_rate,
                improvement_rate=improvement_rate,
                latest_inpatients=latest_week_avg_census,
                target_inpatients=target_value,
                period_avg=period_avg,
                bed_utilization=bed_utilization
            )
            
        except Exception as e:
            logger.error(f"エンティティスコア計算エラー ({entity_name}): {e}")
            return None
    
    def _calculate_achievement_score(self, achievement_rate: float) -> float:
        """直近週達成度スコア計算"""
        score_mapping = self.config.get_achievement_score_mapping()
        
        for threshold, score in score_mapping:
            if achievement_rate >= threshold:
                return score
        return 0
    
    def _calculate_improvement_score(self, improvement_rate: float) -> float:
        """改善度スコア計算"""
        score_mapping = self.config.get_improvement_score_mapping()
        
        for threshold, score in score_mapping:
            if improvement_rate >= threshold:
                return score
        return 0
    
    def _calculate_improvement_rate(self, entity_df: pd.DataFrame, recent_week_start: pd.Timestamp, 
                                  latest_week_avg_census: float) -> Tuple[float, float]:
        """改善率計算"""
        period_before_recent_week_df = entity_df[entity_df['日付'] < recent_week_start]
        
        improvement_rate = 0
        period_avg = 0
        
        if not period_before_recent_week_df.empty and len(period_before_recent_week_df) >= 7:
            period_before_grouped = period_before_recent_week_df.groupby('日付')['在院患者数'].sum().reset_index()
            period_avg = period_before_grouped['在院患者数'].mean()
            
            if period_avg > 10:  # 最小閾値
                improvement_rate = ((latest_week_avg_census - period_avg) / period_avg) * 100
                improvement_rate = max(-50, min(50, improvement_rate))  # -50%〜+50%に制限
            else:
                improvement_rate = min(20, (latest_week_avg_census - period_avg))
        
        return improvement_rate, period_avg
    
    def _calculate_stability_score(self, entity_df: pd.DataFrame, 
                                 start_date: pd.Timestamp, end_date: pd.Timestamp) -> float:
        """安定性スコア計算"""
        try:
            period_df = entity_df[(entity_df['日付'] >= start_date) & (entity_df['日付'] <= end_date)].copy()
            if period_df.empty or len(period_df) < 7:
                return 0
            
            # 週次データ作成
            period_df['週番号'] = period_df['日付'].dt.isocalendar().week
            period_df['年'] = period_df['日付'].dt.year
            period_df['年週'] = period_df['年'].astype(str) + '-W' + period_df['週番号'].astype(str).str.zfill(2)
            
            weekly_data = period_df.groupby('年週').agg({
                '在院患者数': 'mean', 
                '日付': 'max'
            }).sort_values('日付').reset_index()
            
            if len(weekly_data) < 2:
                return 0
            
            # 直近3週の安定性
            recent_3weeks = weekly_data['在院患者数'].tail(3)
            if len(recent_3weeks) < 2:
                return 0
            
            mean_val = recent_3weeks.mean()
            if mean_val <= 0:
                return 0
            
            cv = (recent_3weeks.std() / mean_val) * 100  # 変動係数
            
            score_mapping = self.config.get_stability_score_mapping()
            for threshold, score in score_mapping:
                if cv < threshold:
                    return score
            return 0
            
        except Exception as e:
            logger.error(f"安定性スコア計算エラー: {e}")
            return 0
    
    def _calculate_sustainability_score(self, entity_df: pd.DataFrame, target_value: float,
                                      start_date: pd.Timestamp, end_date: pd.Timestamp) -> float:
        """持続性スコア計算"""
        try:
            period_df = entity_df[(entity_df['日付'] >= start_date) & (entity_df['日付'] <= end_date)].copy()
            if period_df.empty or len(period_df) < 7 or target_value <= 0:
                return 0
            
            # 週次データ作成
            period_df['週番号'] = period_df['日付'].dt.isocalendar().week
            period_df['年'] = period_df['日付'].dt.year
            period_df['年週'] = period_df['年'].astype(str) + '-W' + period_df['週番号'].astype(str).str.zfill(2)
            
            weekly_data = period_df.groupby('年週').agg({
                '在院患者数': 'mean', 
                '日付': 'max'
            }).sort_values('日付').reset_index()
            
            if len(weekly_data) < 2:
                return 0
            
            # 達成率と改善フラグの計算
            weekly_data['achievement_rate'] = (weekly_data['在院患者数'] / target_value) * 100
            weekly_data['prev_value'] = weekly_data['在院患者数'].shift(1)
            weekly_data['improvement'] = weekly_data['在院患者数'] > weekly_data['prev_value']
            
            # 直近4週のデータ
            recent_4weeks = weekly_data.tail(4)
            scores = []
            
            # 各種持続性パターンをチェック
            scores.extend(self._check_consecutive_patterns(recent_4weeks))
            scores.extend(self._check_high_performance_patterns(recent_4weeks))
            
            return max(scores) if scores else 0
            
        except Exception as e:
            logger.error(f"持続性スコア計算エラー: {e}")
            return 0
    
    def _check_consecutive_patterns(self, recent_weeks: pd.DataFrame) -> List[float]:
        """連続パターンのチェック"""
        scores = []
        bonus_mapping = self.config.get_sustainability_bonus_mapping()
        
        # 連続改善チェック
        consecutive_improvements = 0
        for i in range(len(recent_weeks) - 1, 0, -1):
            if pd.notna(recent_weeks.iloc[i]['improvement']) and recent_weeks.iloc[i]['improvement']:
                consecutive_improvements += 1
            else:
                break
        
        for weeks, score in bonus_mapping['consecutive_improvement']:
            if consecutive_improvements >= weeks:
                scores.append(score)
                break
        
        # 連続達成チェック
        consecutive_achievements = 0
        for i in range(len(recent_weeks) - 1, -1, -1):
            if recent_weeks.iloc[i]['achievement_rate'] >= self.config.achievement.target:
                consecutive_achievements += 1
            else:
                break
        
        for weeks, score in bonus_mapping['consecutive_achievement']:
            if consecutive_achievements >= weeks:
                scores.append(score)
                break
        
        return scores
    
    def _check_high_performance_patterns(self, recent_weeks: pd.DataFrame) -> List[float]:
        """高パフォーマンスパターンのチェック"""
        scores = []
        bonus_mapping = self.config.get_sustainability_bonus_mapping()
        
        if len(recent_weeks) >= 4:
            avg_achievement = recent_weeks['achievement_rate'].mean()
            achievements_count = (recent_weeks['achievement_rate'] >= self.config.achievement.target).sum()
            no_below_90 = (recent_weeks['achievement_rate'] >= 90).all()
            
            for criteria, score in bonus_mapping['high_performance']:
                if criteria == 6 and avg_achievement >= self.config.achievement.target:
                    scores.append(score)
                elif criteria == 4 and achievements_count >= 3:
                    scores.append(score)
                elif criteria == 3 and no_below_90:
                    scores.append(score)
        
        return scores
    
    def _calculate_bed_efficiency_score(self, bed_utilization: float, achievement_rate: float) -> float:
        """病床効率スコア計算"""
        try:
            score_mapping = self.config.get_bed_efficiency_score_mapping()
            
            for util_threshold, achievement_threshold, score in score_mapping:
                if (bed_utilization >= util_threshold and 
                    achievement_rate >= achievement_threshold):
                    return score
            
            return 0
            
        except Exception as e:
            logger.error(f"病床効率スコア計算エラー: {e}")
            return 0

# 後方互換性のための関数（既存コードとの互換性維持）
def calculate_high_score(df, target_data, entity_name, entity_type, start_date, end_date, group_col=None):
    """
    従来のcalculate_high_score関数の互換性維持
    新しいクラスベースの実装を内部で使用
    """
    calculator = HighScoreCalculator()
    result = calculator.calculate_entity_score(
        df, target_data, entity_name, entity_type, start_date, end_date, group_col
    )
    return result.to_dict() if result else None

def calculate_all_high_scores(df, target_data, period="直近12週"):
    """
    従来のcalculate_all_high_scores関数の互換性維持
    新しいクラスベースの実装を内部で使用
    """
    calculator = HighScoreCalculator()
    dept_scores, ward_scores = calculator.calculate_all_high_scores(df, target_data, period)
    
    # 辞書形式に変換（後方互換性のため）
    dept_dicts = [score.to_dict() for score in dept_scores]
    ward_dicts = [score.to_dict() for score in ward_scores]
    
    return dept_dicts, ward_dicts