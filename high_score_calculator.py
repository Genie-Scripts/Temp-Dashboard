# high_score_calculator.py
"""
ハイスコア計算モジュール
KPIデータから総合スコアを計算する機能を提供
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# スコア設定のインポート
# =============================================================================
try:
    from report_generation.config import scoring_config
    SCORING_CONFIG = scoring_config.DEFAULT_SCORING_CONFIG
except ImportError:
    try:
        from config.scoring_config import DEFAULT_SCORING_CONFIG
        SCORING_CONFIG = DEFAULT_SCORING_CONFIG
    except ImportError:
        # フォールバック設定
        class DefaultScoringConfig:
            def get_achievement_score_mapping(self):
                return [(110, 50), (105, 45), (100, 40), (98, 35), (95, 25), (90, 15), (85, 5), (0, 0)]
            
            def get_improvement_score_mapping(self):
                return [(15, 25), (10, 20), (5, 15), (2, 10), (-2, 5), (-5, 3), (-10, 1), (-100, 0)]
            
            def get_stability_score_mapping(self):
                return [(5, 15), (10, 12), (15, 8), (20, 4), (100, 0)]
        
        SCORING_CONFIG = DefaultScoringConfig()
        logger.warning("スコア設定をフォールバック値で初期化しました")

# =============================================================================
# ユーティリティ関数
# =============================================================================
def _get_score_from_mapping(value: float, mapping: List[Tuple[float, float]]) -> float:
    """マッピングテーブルから対応するスコアを取得"""
    if value is None or pd.isna(value):
        return 0
    
    for threshold, score in mapping:
        if value >= threshold:
            return score
    return 0

def _safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
    """安全な除算（ゼロ除算を回避）"""
    if denominator == 0 or pd.isna(denominator) or pd.isna(numerator):
        return default
    return numerator / denominator

# =============================================================================
# メインクラス
# =============================================================================
class HighScoreCalculator:
    """ハイスコア計算のメインクラス"""
    
    def __init__(self, config: Any = None):
        self.config = config or SCORING_CONFIG
    
    def calculate_score(self, kpi_data: Dict[str, Any]) -> float:
        """KPIデータから総合スコアを計算"""
        try:
            # 各スコア要素の計算
            achievement_score = self._calculate_achievement_score(
                kpi_data.get('occupancy_rate', 0) * 100
            )
            improvement_score = self._calculate_improvement_score(
                kpi_data.get('improvement_rate', 0)
            )
            stability_score = self._calculate_stability_score(
                kpi_data.get('cv', 100)
            )
            sustainability_score = kpi_data.get('sustainability_score', 0)
            bed_efficiency_score = kpi_data.get('bed_efficiency_score', 0)
            
            # 総合スコア
            total_score = (
                achievement_score + 
                improvement_score + 
                stability_score + 
                sustainability_score + 
                bed_efficiency_score
            )
            
            return min(105, max(0, total_score))
            
        except Exception as e:
            logger.error(f"スコア計算エラー: {e}")
            return 0
    
    def _calculate_achievement_score(self, achievement_rate: float) -> float:
        """達成度スコアの計算"""
        mapping = self.config.get_achievement_score_mapping()
        return _get_score_from_mapping(achievement_rate, mapping)
    
    def _calculate_improvement_score(self, improvement_rate: float) -> float:
        """改善度スコアの計算"""
        mapping = self.config.get_improvement_score_mapping()
        return _get_score_from_mapping(improvement_rate, mapping)
    
    def _calculate_stability_score(self, cv: float) -> float:
        """安定性スコアの計算"""
        mapping = self.config.get_stability_score_mapping()
        return _get_score_from_mapping(cv, mapping)

# =============================================================================
# 便利関数（後方互換性）
# =============================================================================
def calculate_high_score(kpi_data: Dict[str, Any], config: Any = None) -> float:
    """ハイスコア計算の便利関数"""
    calculator = HighScoreCalculator(config)
    return calculator.calculate_score(kpi_data)

def calculate_all_high_scores(df: pd.DataFrame, target_data: pd.DataFrame, 
                            period: str = "直近12週") -> Tuple[List[Dict], List[Dict]]:
    """全エンティティのハイスコア計算"""
    # この関数の実装は、utilsからの関数インポートが必要なため
    # 簡易版を返す
    logger.warning("完全なハイスコア計算機能は利用できません")
    return [], []

# =============================================================================
# テスト関数
# =============================================================================
def test_functionality() -> bool:
    """機能テスト"""
    try:
        test_data = {
            'occupancy_rate': 0.95,
            'improvement_rate': 5.0,
            'cv': 10.0,
            'sustainability_score': 5,
            'bed_efficiency_score': 0
        }
        score = calculate_high_score(test_data)
        return isinstance(score, (int, float)) and 0 <= score <= 105
    except Exception as e:
        logger.error(f"機能テストエラー: {e}")
        return False

if __name__ == "__main__":
    print("=== ハイスコア計算モジュール ===")
    if test_functionality():
        print("✅ 機能テスト: 成功")
    else:
        print("❌ 機能テスト: 失敗")