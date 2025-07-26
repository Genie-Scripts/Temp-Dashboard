# report_generation/__init__.py
"""
統合レポート生成パッケージ（メイン）

このパッケージは、html_export_functions.pyの機能を
保守しやすい複数のモジュールに分割したものです。
"""

import logging
import sys
import os
from typing import Optional, Dict, Any, Tuple, List
import pandas as pd

# 親ディレクトリをパスに追加（重要）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

__version__ = "2.0.0"
__author__ = "Hospital Analytics Team"
__description__ = "統合パフォーマンスレポート生成システム（リファクタリング版）"

# ログ設定
logger = logging.getLogger(__name__)

# =============================================================================
# 他のタブモジュールの条件付きインポート（エラーを防ぐ）
# =============================================================================
# これらは必須ではないので、エラーを無視
tab_modules = [
    'analysis_tabs', 'alos_analysis_tab', 'dashboard_overview_tab',
    'data_processing_tab', 'department_performance_tab', 'dow_analysis_tab',
    'forecast_analysis_tab', 'individual_analysis_tab', 'pdf_output_tab',
    'ward_performance_tab'
]

for module in tab_modules:
    try:
        exec(f"from .{module} import *")
    except ImportError:
        pass  # タブモジュールは必須ではない

# forecastモジュールも条件付き
try:
    from .forecast import *
except ImportError:
    pass

# =============================================================================
# 段階的インポート（フォールバック付き）
# =============================================================================

# メイン機能のインポート
try:
    from .report_generator import ReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
    logger.info("✅ ReportGenerator をロードしました")
except ImportError as e:
    logger.warning(f"❌ ReportGenerator のインポートに失敗: {e}")
    ReportGenerator = None
    REPORT_GENERATOR_AVAILABLE = False

# ハイスコア計算
try:
    from .high_score_calculator import (
        HighScoreCalculator,
        ScoreResult,
        calculate_high_score,
        calculate_all_high_scores
    )
    HIGH_SCORE_AVAILABLE = True
    logger.info("✅ HighScoreCalculator をロードしました")
except ImportError as e:
    logger.warning(f"❌ HighScoreCalculator のインポートに失敗: {e}")
    HighScoreCalculator = ScoreResult = None
    calculate_high_score = calculate_all_high_scores = None
    HIGH_SCORE_AVAILABLE = False

# 設定管理
try:
    from .config import (
        ScoringConfig,
        DEFAULT_SCORING_CONFIG,
        get_scoring_weights,
        get_achievement_thresholds,
        SCORING_CONFIG_AVAILABLE
    )
    CONFIG_AVAILABLE = SCORING_CONFIG_AVAILABLE
    logger.info("✅ 設定管理モジュールをロードしました")
except ImportError as e:
    logger.warning(f"❌ 設定モジュールのインポートに失敗: {e}")
    ScoringConfig = DEFAULT_SCORING_CONFIG = None
    get_scoring_weights = get_achievement_thresholds = None
    CONFIG_AVAILABLE = False

# UIコンポーネント
try:
    from .components import (
        UIComponentBuilder,
        create_ui_component_builder,
        generate_weekly_highlights_by_type,
        generate_weekly_highlights_compact,
        generate_score_detail_html,
        generate_weekly_highlights,
        UI_COMPONENTS_AVAILABLE
    )
    UI_COMPONENTS_AVAILABLE = UI_COMPONENTS_AVAILABLE
    logger.info("✅ UIコンポーネントをロードしました")
except ImportError as e:
    logger.warning(f"❌ UIコンポーネントのインポートに失敗: {e}")
    UIComponentBuilder = create_ui_component_builder = None
    generate_weekly_highlights_by_type = generate_weekly_highlights_compact = None
    generate_score_detail_html = generate_weekly_highlights = None
    UI_COMPONENTS_AVAILABLE = False

# テンプレート管理
try:
    from .templates import (
        HTMLTemplates,
        CSSManager,
        JavaScriptTemplates,
        TemplateManager,
        create_template_manager,
        HTML_TEMPLATES_AVAILABLE,
        CSS_MANAGER_AVAILABLE
    )
    TEMPLATES_AVAILABLE = HTML_TEMPLATES_AVAILABLE and CSS_MANAGER_AVAILABLE
    logger.info("✅ テンプレート管理をロードしました")
except ImportError as e:
    logger.warning(f"❌ テンプレートモジュールのインポートに失敗: {e}")
    HTMLTemplates = CSSManager = JavaScriptTemplates = None
    TemplateManager = create_template_manager = None
    HTML_TEMPLATES_AVAILABLE = CSS_MANAGER_AVAILABLE = TEMPLATES_AVAILABLE = False

# =============================================================================
# パッケージレベルの公開API
# =============================================================================

def create_report_generator(scoring_config: Optional[Any] = None) -> Optional[Any]:
    """ReportGenerator インスタンスを作成"""
    if not REPORT_GENERATOR_AVAILABLE:
        logger.error("ReportGenerator が利用できません")
        return None
    
    try:
        if scoring_config is None and CONFIG_AVAILABLE:
            scoring_config = DEFAULT_SCORING_CONFIG
        return ReportGenerator(scoring_config)
    except Exception as e:
        logger.error(f"ReportGenerator の作成に失敗: {e}")
        return None

def create_high_score_calculator(config: Optional[Any] = None) -> Optional[Any]:
    """HighScoreCalculator インスタンスを作成"""
    if not HIGH_SCORE_AVAILABLE:
        logger.error("HighScoreCalculator が利用できません")
        return None
    
    try:
        if config is None and CONFIG_AVAILABLE:
            config = DEFAULT_SCORING_CONFIG
        return HighScoreCalculator(config)
    except Exception as e:
        logger.error(f"HighScoreCalculator の作成に失敗: {e}")
        return None

def get_package_status() -> Dict[str, Any]:
    """パッケージの利用可能状況を取得"""
    return {
        'version': __version__,
        'modules': {
            'report_generator': REPORT_GENERATOR_AVAILABLE,
            'high_score_calculator': HIGH_SCORE_AVAILABLE,
            'config': CONFIG_AVAILABLE,
            'ui_components': UI_COMPONENTS_AVAILABLE,
            'templates': TEMPLATES_AVAILABLE
        },
        'fully_available': all([
            REPORT_GENERATOR_AVAILABLE,
            HIGH_SCORE_AVAILABLE,
            CONFIG_AVAILABLE,
            UI_COMPONENTS_AVAILABLE,
            TEMPLATES_AVAILABLE
        ])
    }

def validate_installation() -> bool:
    """インストール状況の検証"""
    status = get_package_status()
    if status['fully_available']:
        logger.info("✅ 全モジュールが正常に利用可能です")
        return True
    else:
        missing = [name for name, available in status['modules'].items() if not available]
        logger.warning(f"❌ 以下のモジュールが利用できません: {missing}")
        return False

# =============================================================================
# メイン機能：後方互換性のための統一インターフェース
# =============================================================================

def generate_all_in_one_html_report(df: pd.DataFrame, target_data: pd.DataFrame, 
                                   period: str = "直近12週") -> str:
    """後方互換性のためのラッパー関数"""
    # 新実装を優先的に使用
    generator = create_report_generator()
    if generator:
        try:
            logger.info(f"新アーキテクチャでレポート生成: {period}")
            return generator.generate_all_in_one_html_report(df, target_data, period)
        except Exception as e:
            logger.error(f"新実装でエラー: {e}")
    
    # フォールバック
    logger.warning("新実装が利用できません。従来実装へのフォールバックが必要です。")
    raise ImportError(
        "ReportGenerator が利用できません。\n"
        "以下のいずれかを実行してください:\n"
        "1. 新しいモジュールをインストール\n"
        "2. 従来のhtml_export_functions.pyを使用"
    )

def calculate_all_high_scores_unified(df: pd.DataFrame, target_data: pd.DataFrame, 
                                    period: str = "直近12週") -> Tuple[List[Dict], List[Dict]]:
    """統一されたハイスコア計算インターフェース"""
    if HIGH_SCORE_AVAILABLE:
        try:
            return calculate_all_high_scores(df, target_data, period)
        except Exception as e:
            logger.error(f"ハイスコア計算エラー（新実装）: {e}")
    
    logger.warning("ハイスコア計算機能が利用できません")
    return [], []

# =============================================================================
# デバッグ・診断機能
# =============================================================================

def diagnose_package() -> Dict[str, Any]:
    """パッケージの詳細診断情報を取得"""
    diagnosis = {
        'package_info': {
            'version': __version__,
            'description': __description__
        },
        'module_status': get_package_status()['modules'],
        'dependencies': {},
        'recommendations': []
    }
    
    # 依存関係の確認
    try:
        import pandas
        diagnosis['dependencies']['pandas'] = pandas.__version__
    except ImportError:
        diagnosis['dependencies']['pandas'] = 'NOT_INSTALLED'
        diagnosis['recommendations'].append('pandas をインストールしてください')
    
    try:
        import numpy
        diagnosis['dependencies']['numpy'] = numpy.__version__
    except ImportError:
        diagnosis['dependencies']['numpy'] = 'NOT_INSTALLED'
        diagnosis['recommendations'].append('numpy をインストールしてください')
    
    # モジュール固有の推奨事項
    if not REPORT_GENERATOR_AVAILABLE:
        diagnosis['recommendations'].append('report_generator.py を確認してください')
    
    if not HIGH_SCORE_AVAILABLE:
        diagnosis['recommendations'].append('high_score_calculator.py を配置してください')
    
    return diagnosis

# =============================================================================
# 公開API（__all__）
# =============================================================================

__all__ = [
    # バージョン情報
    '__version__',
    '__author__',
    '__description__',
    
    # メインクラス
    'ReportGenerator',
    'HighScoreCalculator',
    'ScoreResult',
    'ScoringConfig',
    'UIComponentBuilder',
    'HTMLTemplates',
    'CSSManager',
    'TemplateManager',
    
    # ファクトリ関数
    'create_report_generator',
    'create_high_score_calculator',
    'create_ui_component_builder',
    'create_template_manager',
    
    # メイン機能
    'generate_all_in_one_html_report',
    'calculate_all_high_scores_unified',
    
    # ユーティリティ
    'get_package_status',
    'validate_installation',
    'diagnose_package',
    
    # 設定
    'DEFAULT_SCORING_CONFIG'
]

# =============================================================================
# パッケージ初期化
# =============================================================================

logger.info(f"=== {__description__} v{__version__} ===")
status = get_package_status()
available_count = sum(status['modules'].values())
total_count = len(status['modules'])

logger.info(f"利用可能モジュール: {available_count}/{total_count}")

for module_name, available in status['modules'].items():
    status_icon = "✅" if available else "❌"
    logger.info(f"  {status_icon} {module_name}")

if status['fully_available']:
    logger.info("🎉 全機能が利用可能です！最適なパフォーマンスで動作します。")
elif available_count > 0:
    logger.info(f"⚡ ハイブリッドモード（{available_count}/{total_count}モジュール利用可能）")
else:
    logger.warning("🔄 フォールバックモード。新モジュールのインストールを推奨します。")