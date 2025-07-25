# config/scoring_config.py
"""
ハイスコア計算の設定値を管理するモジュール
マジックナンバーを排除し、設定を一元管理
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class ScoringWeights:
    """スコア構成要素の重み設定"""
    achievement: int = 50      # 直近週達成度（最重要）
    improvement: int = 25      # 改善度
    stability: int = 15        # 安定性
    sustainability: int = 10   # 持続性
    bed_efficiency: int = 5    # 病床効率（病棟のみ）

@dataclass
class AchievementThresholds:
    """達成度評価の閾値設定"""
    perfect: float = 110.0     # パーフェクト
    excellent: float = 105.0   # エクセレント
    good: float = 100.0        # 優秀
    target: float = 98.0       # 目標達成基準
    average: float = 95.0      # 普通
    needs_improvement: float = 90.0  # 要改善
    attention: float = 85.0    # 注意

@dataclass
class ImprovementThresholds:
    """改善度評価の閾値設定"""
    major_improvement: float = 15.0    # 大幅改善
    significant: float = 10.0          # 顕著改善
    good: float = 5.0                  # 良好改善
    slight: float = 2.0                # 微増
    stable_upper: float = 2.0          # 安定（上限）
    stable_lower: float = -2.0         # 安定（下限）
    slight_decline: float = -5.0       # 微減
    decline: float = -10.0             # 減少

@dataclass
class StabilityThresholds:
    """安定性評価の閾値設定（変動係数%）"""
    very_stable: float = 5.0    # 非常に安定
    stable: float = 10.0        # 安定
    somewhat_variable: float = 15.0  # やや変動
    variable: float = 20.0      # 変動大

@dataclass
class SustainabilitySettings:
    """持続性評価の設定"""
    max_weeks_check: int = 4           # 最大チェック週数
    consecutive_improvement_max: int = 4   # 連続改善最大週数
    consecutive_achievement_max: int = 4   # 連続達成最大週数
    high_performance_threshold: float = 98.0  # 高パフォーマンス閾値

@dataclass
class BedEfficiencyThresholds:
    """病床効率評価の閾値設定"""
    excellent_utilization: float = 95.0  # 優秀な利用率
    good_utilization: float = 90.0       # 良好な利用率
    utilization_improvement: float = 10.0  # 利用率向上基準

class ScoringConfig:
    """スコア計算の統合設定クラス"""
    
    def __init__(self):
        self.weights = ScoringWeights()
        self.achievement = AchievementThresholds()
        self.improvement = ImprovementThresholds()
        self.stability = StabilityThresholds()
        self.sustainability = SustainabilitySettings()
        self.bed_efficiency = BedEfficiencyThresholds()
    
    def get_achievement_score_mapping(self) -> List[Tuple[float, int]]:
        """達成度スコアマッピングを取得"""
        return [
            (self.achievement.perfect, 50),
            (self.achievement.excellent, 45),
            (self.achievement.good, 40),
            (self.achievement.target, 35),
            (self.achievement.average, 25),
            (self.achievement.needs_improvement, 15),
            (self.achievement.attention, 5),
            (0, 0)  # 最低値
        ]
    
    def get_improvement_score_mapping(self) -> List[Tuple[float, int]]:
        """改善度スコアマッピングを取得"""
        return [
            (self.improvement.major_improvement, 25),
            (self.improvement.significant, 20),
            (self.improvement.good, 15),
            (self.improvement.slight, 10),
            (self.improvement.stable_upper, 5),
            (self.improvement.stable_lower, 5),
            (self.improvement.slight_decline, 3),
            (self.improvement.decline, 1),
            (-100, 0)  # 最低値
        ]
    
    def get_stability_score_mapping(self) -> List[Tuple[float, int]]:
        """安定性スコアマッピングを取得"""
        return [
            (self.stability.very_stable, 15),
            (self.stability.stable, 12),
            (self.stability.somewhat_variable, 8),
            (self.stability.variable, 4),
            (100, 0)  # 最高値（最も不安定）
        ]
    
    def get_sustainability_bonus_mapping(self) -> Dict[str, List[Tuple[int, int]]]:
        """持続性ボーナスマッピングを取得"""
        return {
            'consecutive_improvement': [
                (4, 10),  # 4週連続改善
                (3, 7),   # 3週連続改善
                (2, 4),   # 2週連続改善
            ],
            'consecutive_achievement': [
                (4, 10),  # 4週連続目標達成
                (3, 7),   # 3週連続目標達成
                (2, 4),   # 2週連続目標達成
            ],
            'high_performance': [
                (6, 4),   # 直近4週平均98%以上
                (4, 4),   # 直近4週で3回以上目標達成
                (3, 3),   # 直近4週で1度も90%未満なし
            ]
        }
    
    def get_bed_efficiency_score_mapping(self) -> List[Tuple[float, float, int]]:
        """病床効率スコアマッピングを取得 (利用率, 達成率, スコア)"""
        return [
            (self.bed_efficiency.excellent_utilization, self.achievement.target, 5),
            (self.bed_efficiency.good_utilization, self.achievement.target, 3),
            # 利用率向上+10%以上の場合は別途計算
        ]

# デフォルトインスタンス
DEFAULT_SCORING_CONFIG = ScoringConfig()

# 設定値の取得用ヘルパー関数
def get_scoring_weights() -> ScoringWeights:
    """スコア重み設定を取得"""
    return DEFAULT_SCORING_CONFIG.weights

def get_achievement_thresholds() -> AchievementThresholds:
    """達成度閾値設定を取得"""
    return DEFAULT_SCORING_CONFIG.achievement

def get_improvement_thresholds() -> ImprovementThresholds:
    """改善度閾値設定を取得"""
    return DEFAULT_SCORING_CONFIG.improvement

def get_stability_thresholds() -> StabilityThresholds:
    """安定性閾値設定を取得"""
    return DEFAULT_SCORING_CONFIG.stability

def get_sustainability_settings() -> SustainabilitySettings:
    """持続性設定を取得"""
    return DEFAULT_SCORING_CONFIG.sustainability

def get_bed_efficiency_thresholds() -> BedEfficiencyThresholds:
    """病床効率閾値設定を取得"""
    return DEFAULT_SCORING_CONFIG.bed_efficiency