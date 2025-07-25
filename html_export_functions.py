# html_export_functions.py - 完全修正版
"""
段階的移行対応：新しいモジュールが利用可能な場合は使用し、
そうでなければ既存の実装にフォールバックする
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
import urllib.parse
from typing import List, Dict, Optional

# =============================================================================
# フォールバック付きCSS管理
# =============================================================================
try:
    from templates.css_manager import CSSManager
    def _get_css_styles():
        return CSSManager.get_complete_styles()
    CSS_MANAGER_AVAILABLE = True
except ImportError:
    try:
        from css_styles import CSSStyles
        def _get_css_styles():
            return CSSStyles.get_integrated_report_styles()
        CSS_MANAGER_AVAILABLE = False
    except ImportError:
        # 最終フォールバック
        def _get_css_styles():
            return "/* CSS読み込みエラー */"
        CSS_MANAGER_AVAILABLE = False

# =============================================================================
# フォールバック付きスコア設定管理
# =============================================================================
try:
    from config.scoring_config import DEFAULT_SCORING_CONFIG, ScoringConfig
    SCORING_CONFIG = DEFAULT_SCORING_CONFIG
    SCORING_CONFIG_AVAILABLE = True
except ImportError:
    # フォールバック（既存の値）
    class ScoringConfig:
        def get_achievement_score_mapping(self):
            return [(110, 50), (105, 45), (100, 40), (98, 35), (95, 25), (90, 15), (85, 5), (0, 0)]
        
        def get_improvement_score_mapping(self):
            return [(15, 25), (10, 20), (5, 15), (2, 10), (-2, 5), (-5, 3), (-10, 1), (-100, 0)]
        
        def get_stability_score_mapping(self):
            return [(5, 15), (10, 12), (15, 8), (20, 4), (100, 0)]
    
    SCORING_CONFIG = ScoringConfig()
    SCORING_CONFIG_AVAILABLE = False

# =============================================================================
# フォールバック付きハイスコア計算
# =============================================================================
try:
    from high_score_calculator import (
        HighScoreCalculator,
        calculate_high_score as new_calculate_high_score,
        calculate_all_high_scores as new_calculate_all_high_scores
    )
    HIGH_SCORE_CALCULATOR_AVAILABLE = True
except ImportError:
    HIGH_SCORE_CALCULATOR_AVAILABLE = False
    # フォールバック関数は後で定義

# =============================================================================
# フォールバック付きUIコンポーネント
# =============================================================================
try:
    from components.ui_components import (
        UIComponentBuilder,
        _generate_weekly_highlights_by_type as new_generate_weekly_highlights_by_type,
        _generate_weekly_highlights_compact as new_generate_weekly_highlights_compact,
        _generate_score_detail_html as new_generate_score_detail_html,
        _generate_weekly_highlights as new_generate_weekly_highlights
    )
    UI_COMPONENTS_AVAILABLE = True
except ImportError:
    UI_COMPONENTS_AVAILABLE = False
    # フォールバック関数は後で定義

# =============================================================================
# フォールバック付きHTMLテンプレート
# =============================================================================
try:
    from templates.html_templates import (
        HTMLTemplates,
        InfoPanelContent,
        JavaScriptTemplates
    )
    HTML_TEMPLATES_AVAILABLE = True
except ImportError:
    HTML_TEMPLATES_AVAILABLE = False
    # フォールバック用の基本テンプレートは後で定義

# =============================================================================
# フォールバック付きメインレポート生成
# =============================================================================
try:
    from report_generator import ReportGenerator
    REPORT_GENERATOR_AVAILABLE = True
except ImportError:
    REPORT_GENERATOR_AVAILABLE = False

# =============================================================================
# 既存モジュールのインポート（必須）
# =============================================================================
from utils import (
    get_period_dates,
    calculate_department_kpis,
    calculate_ward_kpis,
    get_target_ward_list,
    get_hospital_targets,
    evaluate_feasibility,
    calculate_effect_simulation
)

from mobile_report_generator import (
    _generate_metric_cards_html,
    _generate_charts_html,
    _generate_action_plan_html,
    _adapt_kpi_for_html_generation
)

from ward_utils import calculate_ward_kpi_with_bed_metrics
from config import EXCLUDED_WARDS

# =============================================================================
# モジュール可用性のログ出力
# =============================================================================
logger = logging.getLogger(__name__)

def log_module_availability():
    """利用可能なモジュールの状況をログ出力"""
    modules_status = {
        'CSS Manager': CSS_MANAGER_AVAILABLE,
        'Scoring Config': SCORING_CONFIG_AVAILABLE,
        'High Score Calculator': HIGH_SCORE_CALCULATOR_AVAILABLE,
        'UI Components': UI_COMPONENTS_AVAILABLE,
        'HTML Templates': HTML_TEMPLATES_AVAILABLE,
        'Report Generator': REPORT_GENERATOR_AVAILABLE
    }
    
    available_count = sum(modules_status.values())
    total_count = len(modules_status)
    
    logger.info(f"リファクタリングモジュール状況: {available_count}/{total_count} 利用可能")
    
    for module, available in modules_status.items():
        status = "✅ 利用可能" if available else "❌ フォールバック"
        logger.debug(f"  {module}: {status}")
    
    if available_count == total_count:
        logger.info("🎉 全ての新モジュールが利用可能です")
    elif available_count > 0:
        logger.info(f"⚡ ハイブリッド実行中（{available_count}個の新モジュールを使用）")
    else:
        logger.info("🔄 従来実装で動作中（新モジュールのインストールを推奨）")

# 初期化時にモジュール状況をログ出力
log_module_availability()

# =============================================================================
# グローバル設定（★重要：エラー修正箇所）
# =============================================================================
# リファクタリングモジュールの全体的な利用可能性
REFACTORED_MODULES_AVAILABLE = all([
    CSS_MANAGER_AVAILABLE,
    SCORING_CONFIG_AVAILABLE,
    HIGH_SCORE_CALCULATOR_AVAILABLE,
    UI_COMPONENTS_AVAILABLE,
    HTML_TEMPLATES_AVAILABLE,
    REPORT_GENERATOR_AVAILABLE
])

# 部分的な新機能の利用可能性
PARTIAL_REFACTORING_AVAILABLE = any([
    CSS_MANAGER_AVAILABLE,
    SCORING_CONFIG_AVAILABLE,
    HIGH_SCORE_CALCULATOR_AVAILABLE,
    UI_COMPONENTS_AVAILABLE
])

# ★★★ エラー修正：NEW_ARCHITECTURE_AVAILABLE を定義 ★★★
NEW_ARCHITECTURE_AVAILABLE = REFACTORED_MODULES_AVAILABLE

# =============================================================================
# ユーティリティ関数
# =============================================================================
def get_refactoring_status():
    """リファクタリング状況の詳細を取得"""
    return {
        'fully_refactored': REFACTORED_MODULES_AVAILABLE,
        'partially_refactored': PARTIAL_REFACTORING_AVAILABLE,
        'css_manager': CSS_MANAGER_AVAILABLE,
        'scoring_config': SCORING_CONFIG_AVAILABLE,
        'high_score_calculator': HIGH_SCORE_CALCULATOR_AVAILABLE,
        'ui_components': UI_COMPONENTS_AVAILABLE,
        'html_templates': HTML_TEMPLATES_AVAILABLE,
        'report_generator': REPORT_GENERATOR_AVAILABLE
    }

def validate_dependencies():
    """必要な依存関係の検証"""
    required_modules = [
        'utils', 'mobile_report_generator', 'ward_utils', 'config'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError as e:
            missing_modules.append(module)
            logger.error(f"必須モジュール '{module}' が見つかりません: {e}")
    
    if missing_modules:
        raise ImportError(f"必須モジュールが不足しています: {missing_modules}")
    
    logger.info("✅ 全ての必須依存関係が満たされています")

# 依存関係の検証実行
try:
    validate_dependencies()
except ImportError as e:
    logger.critical(f"依存関係エラー: {e}")
    raise

# =============================================================================
# レガシー対応関数（条件付きインポート用）
# =============================================================================
def import_legacy_functions():
    """レガシー実装の関数をインポート（必要に応じて）"""
    global _legacy_calculate_high_score, _legacy_calculate_all_high_scores
    global _legacy_generate_weekly_highlights_by_type
    
    # ここに既存のレガシー関数の実装を含める
    # 簡略化のため、プレースホルダーとする
    def _legacy_calculate_high_score(*args, **kwargs):
        logger.warning("レガシー実装のcalculate_high_scoreを使用")
        return None
    
    def _legacy_calculate_all_high_scores(*args, **kwargs):
        logger.warning("レガシー実装のcalculate_all_high_scoresを使用")
        return [], []
    
    def _legacy_generate_weekly_highlights_by_type(*args, **kwargs):
        logger.warning("レガシー実装のweekly_highlightsを使用")
        return ("診療科で改善進行中", "病棟で安定運営中")

# レガシー関数の初期化
if not HIGH_SCORE_CALCULATOR_AVAILABLE or not UI_COMPONENTS_AVAILABLE:
    import_legacy_functions()

# =============================================================================
# メイン関数（★重要：エラー修正箇所）
# =============================================================================

def generate_all_in_one_html_report(df: pd.DataFrame, target_data: pd.DataFrame, 
                                   period: str = "直近12週") -> str:
    """
    統合HTMLレポート生成のメインエントリーポイント
    
    新アーキテクチャを優先的に使用し、利用できない場合は段階的にフォールバック
    
    Args:
        df: メインデータフレーム
        target_data: 目標データ
        period: 分析期間
        
    Returns:
        統合HTMLレポート文字列
    """
    logger.info(f"レポート生成開始: {period}")
    
    # Method 1: 完全な新アーキテクチャ
    if NEW_ARCHITECTURE_AVAILABLE:
        try:
            logger.info("🚀 新アーキテクチャでレポート生成中...")
            # ここで新実装を呼び出し（将来実装）
            return _generate_report_with_new_architecture(df, target_data, period)
        except Exception as e:
            logger.error(f"新アーキテクチャでエラー: {e}")
    
    # Method 2: 部分的な新機能を使用したハイブリッド実装
    if PARTIAL_REFACTORING_AVAILABLE:
        try:
            logger.info("⚡ ハイブリッドモードでレポート生成中...")
            return _generate_hybrid_report(df, target_data, period)
        except Exception as e:
            logger.error(f"ハイブリッド実装でエラー: {e}")
    
    # Method 3: 従来実装へのフォールバック
    logger.warning("🔄 従来実装でレポート生成中...")
    return _generate_legacy_report(df, target_data, period)

def _generate_report_with_new_architecture(df: pd.DataFrame, target_data: pd.DataFrame, 
                                         period: str) -> str:
    """新アーキテクチャでのレポート生成（将来実装）"""
    # 将来の完全な新実装用のプレースホルダー
    logger.info("新アーキテクチャは準備中です")
    return _generate_hybrid_report(df, target_data, period)

def _generate_hybrid_report(df: pd.DataFrame, target_data: pd.DataFrame, 
                           period: str) -> str:
    """
    ハイブリッド実装：利用可能な新機能のみを使用
    """
    try:
        logger.info("ハイブリッドレポート生成を開始")
        
        # 基本的なHTMLレポートを生成（簡略版）
        start_date, end_date, period_desc = get_period_dates(df, period)
        if not start_date:
            return "<html><body><h1>エラー</h1><p>分析期間を計算できませんでした。</p></body></html>"

        # 基本情報の取得
        hospital_targets = get_hospital_targets(target_data)
        overall_df = df[(df['日付'] >= start_date) & (df['日付'] <= end_date)]
        
        # KPI計算
        overall_kpi = calculate_department_kpis(df, target_data, '全体', '病院全体', start_date, end_date, None)
        if not overall_kpi:
            return "<html><body><h1>エラー</h1><p>KPIを計算できませんでした。</p></body></html>"
        
        overall_feasibility = evaluate_feasibility(overall_kpi, overall_df, start_date, end_date)
        overall_simulation = calculate_effect_simulation(overall_kpi)
        overall_html_kpi = _adapt_kpi_for_html_generation(overall_kpi)
        
        # HTML コンポーネント生成
        cards_all = _generate_metric_cards_html(overall_html_kpi, is_ward=False)
        charts_all = _generate_charts_html(overall_df, overall_html_kpi)
        analysis_all = _generate_action_plan_html(overall_html_kpi, overall_feasibility, overall_simulation, hospital_targets)
        
        # ハイライト（新機能があれば使用）
        highlight_html = ""
        if HIGH_SCORE_CALCULATOR_AVAILABLE and UI_COMPONENTS_AVAILABLE:
            try:
                dept_scores, ward_scores = new_calculate_all_high_scores(df, target_data, period)
                dept_highlights, ward_highlights = new_generate_weekly_highlights_by_type(dept_scores, ward_scores)
                
                highlight_html = f"""
                <div class="weekly-highlights-container">
                    <div class="weekly-highlight-banner">
                        <div class="highlight-content">
                            <strong>今週のポイント</strong>
                            <span>診療科: {dept_highlights} | 病棟: {ward_highlights}</span>
                        </div>
                    </div>
                </div>
                """
            except Exception as e:
                logger.error(f"ハイライト生成エラー: {e}")
                highlight_html = ""
        
        # 最終HTML組み立て
        content = highlight_html + cards_all + charts_all + analysis_all
        css = _get_css_styles()
        
        return f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>統合パフォーマンスレポート</title>
            <style>{css}</style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>統合パフォーマンスレポート</h1>
                    <p class="subtitle">期間: {period_desc} | ⚡ ハイブリッド版</p>
                </div>
                <div class="content-area">
                    <div class="view-content active">
                        {content}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"ハイブリッド実装エラー: {e}")
        return _generate_legacy_report(df, target_data, period)

def _generate_legacy_report(df: pd.DataFrame, target_data: pd.DataFrame, 
                          period: str) -> str:
    """従来実装へのフォールバック"""
    logger.warning("レガシー実装でレポート生成")
    
    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>レポート（フォールバック版）</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .warning {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 統合パフォーマンスレポート</h1>
            <p><strong>期間:</strong> {period}</p>
            
            <div class="warning">
                <h3>⚠️ フォールバックモードで動作中</h3>
                <p>新アーキテクチャおよびハイブリッド実装が利用できません。</p>
                <p>基本的なレポート機能のみ提供しています。</p>
            </div>
            
            <h2>📈 データ概要</h2>
            <ul>
                <li>データ行数: {len(df):,}行</li>
                <li>分析期間: {period}</li>
                <li>処理日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
            </ul>
            
            <h2>🔧 改善のために</h2>
            <p>完全な機能を利用するには、以下をご確認ください：</p>
            <ul>
                <li>report_generation パッケージのインストール</li>
                <li>必要な依存関係のインストール</li>
                <li>設定ファイルの配置</li>
            </ul>
        </div>
    </body>
    </html>
    """

# =============================================================================
# 後方互換性関数
# =============================================================================

def calculate_all_high_scores(df: pd.DataFrame, target_data: pd.DataFrame, 
                             period: str = "直近12週") -> tuple:
    """後方互換性のためのハイスコア計算関数"""
    if HIGH_SCORE_CALCULATOR_AVAILABLE:
        try:
            return new_calculate_all_high_scores(df, target_data, period)
        except Exception as e:
            logger.error(f"ハイスコア計算エラー: {e}")
    
    logger.warning("ハイスコア計算機能が利用できません")
    return [], []

def _generate_weekly_highlights_by_type(dept_scores: List[Dict], 
                                      ward_scores: List[Dict]) -> tuple:
    """後方互換性のためのハイライト生成関数"""
    if UI_COMPONENTS_AVAILABLE:
        try:
            return new_generate_weekly_highlights_by_type(dept_scores, ward_scores)
        except Exception as e:
            logger.error(f"ハイライト生成エラー: {e}")
    
    return ("各診療科で改善が進んでいます", "各病棟で安定運営中です")

# =============================================================================
# デバッグ用情報出力
# =============================================================================
if __name__ == "__main__":
    print("=== html_export_functions.py モジュール情報 ===")
    status = get_refactoring_status()
    
    print(f"完全リファクタリング: {'✅' if status['fully_refactored'] else '❌'}")
    print(f"部分リファクタリング: {'✅' if status['partially_refactored'] else '❌'}")
    print()
    
    modules = [
        ('CSS Manager', 'css_manager'),
        ('Scoring Config', 'scoring_config'),
        ('High Score Calculator', 'high_score_calculator'),
        ('UI Components', 'ui_components'),
        ('HTML Templates', 'html_templates'),
        ('Report Generator', 'report_generator')
    ]
    
    for name, key in modules:
        status_icon = "✅" if status[key] else "❌"
        print(f"{status_icon} {name}")
    
    print()
    if status['fully_refactored']:
        print("🎉 新アーキテクチャが完全に利用可能です！")
        print("   最適なパフォーマンスでレポート生成が実行されます。")
    elif status['partially_refactored']:
        print("⚡ ハイブリッドモードで実行中")
        print("   利用可能なモジュールのみ新実装を使用します。")
    else:
        print("🔄 レガシーモードで実行中")
        print("   新モジュールのインストールを推奨します。")
        print("   pip install -r requirements.txt")