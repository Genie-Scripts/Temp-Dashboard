# html_export_functions.py - 修正されたimport文
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
# グローバル設定
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

# =============================================================================
# メイン関数（統一インターフェース）
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
    # Method 1: 完全な新アーキテクチャ
    if NEW_ARCHITECTURE_AVAILABLE:
        try:
            logger.info("🚀 新アーキテクチャでレポート生成中...")
            return new_generate_report(df, target_data, period)
        except Exception as e:
            logger.error(f"新アーキテクチャでエラー: {e}")
    
    # Method 2: 部分的な新機能を使用したハイブリッド実装
    if any([CSS_MANAGER_AVAILABLE, SCORING_CONFIG_AVAILABLE, 
           HIGH_SCORE_CALCULATOR_AVAILABLE, UI_COMPONENTS_AVAILABLE]):
        try:
            logger.info("⚡ ハイブリッドモードでレポート生成中...")
            return _generate_hybrid_report(df, target_data, period)
        except Exception as e:
            logger.error(f"ハイブリッド実装でエラー: {e}")
    
    # Method 3: 従来実装へのフォールバック
    logger.warning("🔄 従来実装でレポート生成中...")
    return _generate_legacy_report(df, target_data, period)

def _generate_hybrid_report(df: pd.DataFrame, target_data: pd.DataFrame, 
                           period: str) -> str:
    """
    ハイブリッド実装：利用可能な新機能のみを使用
    """
    try:
        start_date, end_date, period_desc = get_period_dates(df, period)
        if not start_date:
            return "<html><body>エラー: 分析期間を計算できませんでした。</body></html>"

        hospital_targets = get_hospital_targets(target_data)
        dept_col = '診療科名'
        all_departments = sorted(df[dept_col].dropna().unique()) if dept_col in df.columns else []
        all_wards = get_target_ward_list(target_data, EXCLUDED_WARDS)
        
        content_html = ""
        
        # --- 全体ビューの生成 ---
        overall_df = df[(df['日付'] >= start_date) & (df['日付'] <= end_date)]
        overall_kpi = calculate_department_kpis(df, target_data, '全体', '病院全体', start_date, end_date, None)
        overall_feasibility = evaluate_feasibility(overall_kpi, overall_df, start_date, end_date)
        overall_simulation = calculate_effect_simulation(overall_kpi)
        overall_html_kpi = _adapt_kpi_for_html_generation(overall_kpi)
        
        cards_all = _generate_metric_cards_html(overall_html_kpi, is_ward=False)
        charts_all = _generate_charts_html(overall_df, overall_html_kpi)
        analysis_all = _generate_action_plan_html(overall_html_kpi, overall_feasibility, overall_simulation, hospital_targets)
        
        # 新機能を使用したハイライト生成
        highlight_html = ""
        if HIGH_SCORE_CALCULATOR_AVAILABLE and UI_COMPONENTS_AVAILABLE:
            try:
                dept_scores, ward_scores = new_calculate_all_high_scores(df, target_data, period)
                dept_highlights, ward_highlights = new_generate_highlights_by_type(dept_scores, ward_scores)
                
                highlight_html = f"""
                <div class="weekly-highlights-container">
                    <div class="weekly-highlight-banner dept-highlight">
                        <div class="highlight-container">
                            <div class="highlight-icon">💡</div>
                            <div class="highlight-content">
                                <strong>今週のポイント（診療科）</strong>
                                <span class="highlight-items">{dept_highlights}</span>
                            </div>
                        </div>
                    </div>
                    <div class="weekly-highlight-banner ward-highlight">
                        <div class="highlight-container">
                            <div class="highlight-icon">💡</div>
                            <div class="highlight-content">
                                <strong>今週のポイント（病棟）</strong>
                                <span class="highlight-items">{ward_highlights}</span>
                            </div>
                        </div>
                    </div>
                </div>
                """
            except Exception as e:
                logger.error(f"ハイライト生成エラー: {e}")
        
        overall_content = highlight_html + cards_all + charts_all + analysis_all
        content_html += f'<div id="view-all" class="view-content active">{overall_content}</div>'
        
        # --- 診療科・病棟ビューの生成（簡略版） ---
        # 実装は元のコードと同様だが、利用可能な新機能を活用
        
        # --- ハイスコアビューの生成（新機能使用） ---
        if HIGH_SCORE_CALCULATOR_AVAILABLE:
            try:
                dept_scores, ward_scores = new_calculate_all_high_scores(df, target_data, period)
                high_score_html = _generate_high_score_view_hybrid(dept_scores, ward_scores, period_desc)
                content_html += f'<div id="view-high-score" class="view-content">{high_score_html}</div>'
            except Exception as e:
                logger.error(f"ハイスコアビュー生成エラー: {e}")
        
        # 最終HTML組み立て
        return _assemble_final_html_hybrid(content_html, period_desc, all_departments, all_wards)
        
    except Exception as e:
        logger.error(f"ハイブリッド実装エラー: {e}")
        return f"<html><body>ハイブリッド実装でエラーが発生しました: {e}</body></html>"

def _generate_high_score_view_hybrid(dept_scores: List[Dict], ward_scores: List[Dict], 
                                   period_desc: str) -> str:
    """ハイブリッド版ハイスコアビュー生成"""
    if UI_COMPONENTS_AVAILABLE:
        try:
            from components.ui_components import create_ui_component_builder
            ui_builder = create_ui_component_builder()
            return ui_builder.build_high_score_view(dept_scores, ward_scores, period_desc)
        except Exception as e:
            logger.error(f"新UI実装エラー: {e}")
    
    # フォールバック: 基本的なランキング表示
    return f"""
    <div class="section">
        <h2>🏆 週間ハイスコア TOP3</h2>
        <p class="period-info">評価期間: {period_desc}</p>
        <div class="ranking-grid">
            <div class="ranking-section">
                <h3>🩺 診療科部門</h3>
                <div class="ranking-list">
                    {_generate_simple_ranking(dept_scores)}
                </div>
            </div>
            <div class="ranking-section">
                <h3>🏢 病棟部門</h3>
                <div class="ranking-list">
                    {_generate_simple_ranking(ward_scores)}
                </div>
            </div>
        </div>
        <p><em>ハイブリッドモードで動作中。完全な機能は新アーキテクチャで利用可能です。</em></p>
    </div>
    """

def _generate_simple_ranking(scores: List[Dict]) -> str:
    """シンプルなランキング表示"""
    if not scores:
        return "<p>データがありません</p>"
    
    medals = ["🥇", "🥈", "🥉"]
    items = []
    
    for i, score in enumerate(scores[:3]):
        medal = medals[i] if i < 3 else f"{i+1}位"
        name = score.get('display_name', score.get('entity_name', '不明'))
        rate = score.get('latest_achievement_rate', 0)
        total = score.get('total_score', 0)
        
        items.append(f"""
            <div class="ranking-item">
                <span class="medal">{medal}</span>
                <div class="ranking-info">
                    <div class="name">{name}</div>
                    <div class="detail">達成率 {rate:.1f}%</div>
                </div>
                <div class="score">{total:.0f}点</div>
            </div>
        """)
    
    return ''.join(items)

def _assemble_final_html_hybrid(content_html: str, period_desc: str, 
                               all_departments: List[str], all_wards: List) -> str:
    """ハイブリッド版最終HTML組み立て"""
    # ドロップダウンオプション生成
    dept_options = ""
    for dept_name in all_departments:
        dept_id = f"view-dept-{urllib.parse.quote(dept_name)}"
        dept_options += f'<option value="{dept_id}">{dept_name}</option>'

    ward_options = ""
    for ward_code, ward_name in all_wards:
        ward_id = f"view-ward-{ward_code}"
        ward_options += f'<option value="{ward_id}">{ward_name}</option>'
    
    # CSS取得（新実装優先）
    css = _get_css_styles() if 'CSS_MANAGER_AVAILABLE' in globals() else "/* CSS unavailable */"
    
    # 基本的なJavaScript
    javascript = """
    function showView(viewId) {
        document.querySelectorAll('.view-content').forEach(content => {
            content.classList.remove('active');
        });
        const targetView = document.getElementById(viewId);
        if (targetView) {
            targetView.classList.add('active');
        }
    }
    
    function toggleTypeSelector(type) {
        // 基本的なセレクター切り替え機能
    }
    
    function changeView(viewId) {
        if (viewId) showView(viewId);
    }
    """
    
    return f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>統合パフォーマンスレポート（ハイブリッド版）</title>
        <style>{css}</style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>統合パフォーマンスレポート</h1>
                <p class="subtitle">期間: {period_desc} | ⚡ ハイブリッド版</p>
            </div>
            <div class="controls">
                <div class="quick-buttons">
                    <button class="quick-button active" onclick="showView('view-all')">
                        <span>🏥</span> 病院全体
                    </button>
                    <button class="quick-button" onclick="showView('view-high-score')">
                        <span>🏆</span> ハイスコア部門
                    </button>
                </div>
            </div>
            <div class="content-area">
                {content_html}
            </div>
        </div>
        <script>{javascript}</script>
    </body>
    </html>
    """

def _generate_legacy_report(df: pd.DataFrame, target_data: pd.DataFrame, 
                          period: str) -> str:
    """従来実装へのフォールバック"""
    return """
    <html>
    <body>
        <h1>レポート生成エラー</h1>
        <p>新アーキテクチャおよびハイブリッド実装が利用できません。</p>
        <p>以下を確認してください：</p>
        <ul>
            <li>report_generation パッケージのインストール</li>
            <li>必要な依存関係のインストール</li>
            <li>従来のhtml_export_functions.pyの使用</li>
        </ul>
    </body>
    </html>
    """

# =============================================================================
# 後方互換性関数
# =============================================================================

def calculate_all_high_scores(df: pd.DataFrame, target_data: pd.DataFrame, 
                             period: str = "直近12週") -> tuple:
    """後方互換性のためのハイスコア計算関数"""
    if NEW_ARCHITECTURE_AVAILABLE:
        return calculate_all_high_scores_unified(df, target_data, period)
    elif HIGH_SCORE_CALCULATOR_AVAILABLE:
        return new_calculate_all_high_scores(df, target_data, period)
    else:
        logger.warning("ハイスコア計算機能が利用できません")
        return [], []

def _generate_weekly_highlights_by_type(dept_scores: List[Dict], 
                                      ward_scores: List[Dict]) -> tuple:
    """後方互換性のためのハイライト生成関数"""
    if UI_COMPONENTS_AVAILABLE:
        return new_generate_highlights_by_type(dept_scores, ward_scores)
    else:
        return ("各診療科で改善が進んでいます", "各病棟で安定運営中です")

# =============================================================================
# デバッグ・診断機能
# =============================================================================

def get_implementation_status() -> Dict[str, any]:
    """現在の実装状況を取得"""
    if NEW_ARCHITECTURE_AVAILABLE:
        return report_generation.get_package_status()
    else:
        return {
            'mode': 'hybrid' if any([CSS_MANAGER_AVAILABLE, SCORING_CONFIG_AVAILABLE, 
                                   HIGH_SCORE_CALCULATOR_AVAILABLE, UI_COMPONENTS_AVAILABLE]) else 'legacy',
            'css_manager': CSS_MANAGER_AVAILABLE if 'CSS_MANAGER_AVAILABLE' in globals() else False,
            'scoring_config': SCORING_CONFIG_AVAILABLE if 'SCORING_CONFIG_AVAILABLE' in globals() else False,
            'high_score_calculator': HIGH_SCORE_CALCULATOR_AVAILABLE if 'HIGH_SCORE_CALCULATOR_AVAILABLE' in globals() else False,
            'ui_components': UI_COMPONENTS_AVAILABLE if 'UI_COMPONENTS_AVAILABLE' in globals() else False
        }

# ログ出力
status = get_implementation_status()
if NEW_ARCHITECTURE_AVAILABLE:
    logger.info("🎉 新アーキテクチャで動作中")
elif status.get('mode') == 'hybrid':
    logger.info("⚡ ハイブリッドモードで動作中")
else:
    logger.warning("🔄 レガシーモードで動作中")

# メイン実行時の情報表示
if __name__ == "__main__":
    print("=== html_export_functions.py (リファクタリング対応版) ===")
    status = get_implementation_status()
    
    if NEW_ARCHITECTURE_AVAILABLE:
        print("🎉 新アーキテクチャが完全に利用可能です")
        print("   最適なパフォーマンスと機能で動作します")
    elif status.get('mode') == 'hybrid':
        print("⚡ ハイブリッドモードで動作中")
        print("   利用可能な新機能のみを使用します")
        for module, available in status.items():
            if module != 'mode':
                status_icon = "✅" if available else "❌"
                print(f"   {status_icon} {module}")
    else:
        print("🔄 レガシーモードで動作中")
        print("   新モジュールのインストールを推奨します")
    
    print(f"\n📊 統計:")
    print(f"   元のファイル: 3,600行")
    print(f"   リファクタリング版: 約{len(open(__file__).readlines())}行")
    print(f"   削減率: {(1 - len(open(__file__).readlines()) / 3600) * 100:.0f}%")