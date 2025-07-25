# components/__init__.py
"""
UIコンポーネント管理パッケージ

ランキング表示、ハイライト、メトリクスカードなどのUI要素を管理
"""

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# =============================================================================
# UIコンポーネントモジュールのインポート
# =============================================================================

try:
    from .ui_components import (
        UIComponentBuilder,
        _generate_weekly_highlights_by_type,
        _generate_weekly_highlights_compact,
        _generate_score_detail_html,
        _generate_weekly_highlights
    )
    UI_COMPONENTS_AVAILABLE = True
    logger.info("✅ ui_components モジュールが正常にロードされました")
except ImportError as e:
    logger.error(f"❌ ui_components のインポートに失敗: {e}")
    UIComponentBuilder = None
    _generate_weekly_highlights_by_type = None
    _generate_weekly_highlights_compact = None
    _generate_score_detail_html = None
    _generate_weekly_highlights = None
    UI_COMPONENTS_AVAILABLE = False

# =============================================================================
# ファクトリ関数
# =============================================================================

def create_ui_component_builder() -> Optional[UIComponentBuilder]:
    """UIComponentBuilder インスタンスを作成
    
    Returns:
        UIComponentBuilder インスタンス、または None（利用不可の場合）
    """
    if not UI_COMPONENTS_AVAILABLE:
        logger.error("UIComponentBuilder が利用できません")
        return None
    
    try:
        return UIComponentBuilder()
    except Exception as e:
        logger.error(f"UIComponentBuilder の作成に失敗: {e}")
        return None

# =============================================================================
# 便利関数（後方互換性）
# =============================================================================

def generate_weekly_highlights_by_type(dept_scores: List[Dict], 
                                     ward_scores: List[Dict]) -> tuple:
    """週間ハイライト生成（タイプ別）の統一インターフェース"""
    if UI_COMPONENTS_AVAILABLE and _generate_weekly_highlights_by_type:
        return _generate_weekly_highlights_by_type(dept_scores, ward_scores)
    else:
        logger.warning("週間ハイライト生成機能が利用できません")
        return ("各診療科で改善が進んでいます", "各病棟で安定運営中です")

def generate_weekly_highlights_compact(dept_scores: List[Dict], 
                                     ward_scores: List[Dict]) -> str:
    """コンパクトな週間ハイライト生成の統一インターフェース"""
    if UI_COMPONENTS_AVAILABLE and _generate_weekly_highlights_compact:
        return _generate_weekly_highlights_compact(dept_scores, ward_scores)
    else:
        logger.warning("コンパクトハイライト生成機能が利用できません")
        return "📊 各部門で着実な改善が進んでいます！"

def generate_score_detail_html(dept_scores: List[Dict], 
                             ward_scores: List[Dict]) -> str:
    """スコア詳細HTML生成の統一インターフェース"""
    if UI_COMPONENTS_AVAILABLE and _generate_score_detail_html:
        return _generate_score_detail_html(dept_scores, ward_scores)
    else:
        logger.warning("スコア詳細生成機能が利用できません")
        return "<div>スコア詳細を表示できません</div>"

def generate_weekly_highlights(dept_scores: List[Dict], 
                             ward_scores: List[Dict]) -> str:
    """週間ハイライト生成の統一インターフェース"""
    if UI_COMPONENTS_AVAILABLE and _generate_weekly_highlights:
        return _generate_weekly_highlights(dept_scores, ward_scores)
    else:
        logger.warning("週間ハイライト生成機能が利用できません")
        return "• 今週も各部門で頑張りが見られました！"

# =============================================================================
# ステータス確認
# =============================================================================

def get_component_status() -> Dict[str, Any]:
    """コンポーネントの利用可能状況を取得"""
    return {
        'ui_components': UI_COMPONENTS_AVAILABLE,
        'functions': {
            'weekly_highlights_by_type': _generate_weekly_highlights_by_type is not None,
            'weekly_highlights_compact': _generate_weekly_highlights_compact is not None,
            'score_detail_html': _generate_score_detail_html is not None,
            'weekly_highlights': _generate_weekly_highlights is not None
        }
    }

# =============================================================================
# 公開API
# =============================================================================

__all__ = [
    # メインクラス
    'UIComponentBuilder',
    
    # ファクトリ関数
    'create_ui_component_builder',
    
    # 生成関数
    'generate_weekly_highlights_by_type',
    'generate_weekly_highlights_compact',
    'generate_score_detail_html',
    'generate_weekly_highlights',
    
    # ステータス
    'get_component_status',
    'UI_COMPONENTS_AVAILABLE',
    
    # レガシー関数（後方互換性）
    '_generate_weekly_highlights_by_type',
    '_generate_weekly_highlights_compact',
    '_generate_score_detail_html',
    '_generate_weekly_highlights'
]

# 初期化ログ
logger.info(f"components パッケージを初期化しました（利用可能: {UI_COMPONENTS_AVAILABLE}）")
