# config/__init__.py
"""
設定管理モジュール

スコア計算、閾値、重み等の設定を一元管理するパッケージ
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# =============================================================================
# 設定モジュールのインポート
# =============================================================================

try:
    from .scoring_config import (
        # データクラス
        ScoringWeights,
        AchievementThresholds,
        ImprovementThresholds,
        StabilityThresholds,
        SustainabilitySettings,
        BedEfficiencyThresholds,
        
        # メインクラス
        ScoringConfig,
        DEFAULT_SCORING_CONFIG,
        
        # ヘルパー関数
        get_scoring_weights,
        get_achievement_thresholds,
        get_improvement_thresholds,
        get_stability_thresholds,
        get_sustainability_settings,
        get_bed_efficiency_thresholds
    )
    SCORING_CONFIG_AVAILABLE = True
    logger.info("✅ scoring_config モジュールが正常にロードされました")
    
except ImportError as e:
    logger.error(f"❌ scoring_config のインポートに失敗: {e}")
    
    # フォールバック設定
    class FallbackScoringConfig:
        """最小限のフォールバック設定"""
        def get_achievement_score_mapping(self):
            return [(110, 50), (105, 45), (100, 40), (98, 35), (95, 25), (90, 15), (85, 5), (0, 0)]
        
        def get_improvement_score_mapping(self):
            return [(15, 25), (10, 20), (5, 15), (2, 10), (-2, 5), (-5, 3), (-10, 1), (-100, 0)]
        
        def get_stability_score_mapping(self):
            return [(5, 15), (10, 12), (15, 8), (20, 4), (100, 0)]
    
    # フォールバック値の設定
    ScoringConfig = FallbackScoringConfig
    DEFAULT_SCORING_CONFIG = FallbackScoringConfig()
    SCORING_CONFIG_AVAILABLE = False
    
    # その他の項目をNoneに設定
    ScoringWeights = AchievementThresholds = ImprovementThresholds = None
    StabilityThresholds = SustainabilitySettings = BedEfficiencyThresholds = None
    get_scoring_weights = get_achievement_thresholds = get_improvement_thresholds = None
    get_stability_thresholds = get_sustainability_settings = get_bed_efficiency_thresholds = None

# =============================================================================
# 設定管理の便利関数
# =============================================================================

def create_custom_scoring_config(**overrides) -> ScoringConfig:
    """カスタム設定でScoringConfigを作成
    
    Args:
        **overrides: 上書きする設定値
        
    Returns:
        カスタマイズされたScoringConfig
        
    Example:
        config = create_custom_scoring_config(
            achievement_target=95.0,  # 目標達成基準を95%に変更
            weights_achievement=60    # 達成度の重みを60点に変更
        )
    """
    if not SCORING_CONFIG_AVAILABLE:
        logger.warning("ScoringConfig が利用できません。デフォルト設定を返します。")
        return DEFAULT_SCORING_CONFIG
    
    try:
        config = ScoringConfig()
        
        # 重み設定の上書き
        if 'weights_achievement' in overrides:
            config.weights.achievement = overrides['weights_achievement']
        if 'weights_improvement' in overrides:
            config.weights.improvement = overrides['weights_improvement']
        if 'weights_stability' in overrides:
            config.weights.stability = overrides['weights_stability']
        if 'weights_sustainability' in overrides:
            config.weights.sustainability = overrides['weights_sustainability']
        if 'weights_bed_efficiency' in overrides:
            config.weights.bed_efficiency = overrides['weights_bed_efficiency']
        
        # 達成度閾値の上書き
        if 'achievement_target' in overrides:
            config.achievement.target = overrides['achievement_target']
        if 'achievement_excellent' in overrides:
            config.achievement.excellent = overrides['achievement_excellent']
        if 'achievement_perfect' in overrides:
            config.achievement.perfect = overrides['achievement_perfect']
        
        logger.info(f"カスタムScoringConfigを作成しました（{len(overrides)}個の設定を上書き）")
        return config
        
    except Exception as e:
        logger.error(f"カスタム設定の作成に失敗: {e}")
        return DEFAULT_SCORING_CONFIG

def validate_scoring_config(config: ScoringConfig) -> bool:
    """ScoringConfigの設定値を検証
    
    Args:
        config: 検証するScoringConfig
        
    Returns:
        設定が有効な場合 True
    """
    try:
        if not SCORING_CONFIG_AVAILABLE:
            return True  # フォールバック時は常に有効
        
        # 重みの合計チェック（病棟以外）
        total_weights = (config.weights.achievement + 
                        config.weights.improvement + 
                        config.weights.stability + 
                        config.weights.sustainability)
        
        if total_weights != 100:
            logger.warning(f"重みの合計が100ではありません: {total_weights}")
        
        # 閾値の順序チェック
        achievement = config.achievement
        if not (achievement.perfect >= achievement.excellent >= 
                achievement.good >= achievement.target >= 
                achievement.average):
            logger.error("達成度閾値の順序が正しくありません")
            return False
        
        logger.info("✅ ScoringConfig の検証が完了しました")
        return True
        
    except Exception as e:
        logger.error(f"設定検証中にエラー: {e}")
        return False

def get_config_summary(config: Optional[ScoringConfig] = None) -> Dict[str, Any]:
    """設定の概要を取得
    
    Args:
        config: ScoringConfig（Noneの場合はデフォルト使用）
        
    Returns:
        設定概要の辞書
    """
    if config is None:
        config = DEFAULT_SCORING_CONFIG
    
    try:
        if SCORING_CONFIG_AVAILABLE:
            return {
                'version': 'リファクタリング版',
                'weights': {
                    'achievement': config.weights.achievement,
                    'improvement': config.weights.improvement,
                    'stability': config.weights.stability,
                    'sustainability': config.weights.sustainability,
                    'bed_efficiency': config.weights.bed_efficiency
                },
                'achievement_target': config.achievement.target,
                'excellence_threshold': config.achievement.excellent,
                'perfect_threshold': config.achievement.perfect
            }
        else:
            return {
                'version': 'フォールバック版',
                'note': '基本的な設定のみ利用可能'
            }
    except Exception as e:
        logger.error(f"設定概要の取得に失敗: {e}")
        return {'error': str(e)}

# =============================================================================
# 公開API
# =============================================================================

__all__ = [
    # データクラス
    'ScoringWeights',
    'AchievementThresholds', 
    'ImprovementThresholds',
    'StabilityThresholds',
    'SustainabilitySettings',
    'BedEfficiencyThresholds',
    
    # メインクラス
    'ScoringConfig',
    'DEFAULT_SCORING_CONFIG',
    
    # ヘルパー関数（取得）
    'get_scoring_weights',
    'get_achievement_thresholds',
    'get_improvement_thresholds',
    'get_stability_thresholds',
    'get_sustainability_settings',
    'get_bed_efficiency_thresholds',
    
    # ユーティリティ関数
    'create_custom_scoring_config',
    'validate_scoring_config',
    'get_config_summary',
    
    # 状態変数
    'SCORING_CONFIG_AVAILABLE'
]

# 初期化ログ
logger.info(f"config パッケージを初期化しました（利用可能: {SCORING_CONFIG_AVAILABLE}）")
