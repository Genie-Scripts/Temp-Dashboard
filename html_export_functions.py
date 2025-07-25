# html_export_functions.py - 完全リファクタリング対応版
"""
段階的移行対応：新しいモジュールが利用可能な場合は使用し、
そうでなければ既存の実装にフォールバックする完全版
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
import urllib.parse
from typing import List, Dict, Optional, Tuple, Any

# ロガー設定
logger = logging.getLogger(__name__)

# =============================================================================
# 新アーキテクチャの利用可能性チェック
# =============================================================================
try:
    import report_generation
    from report_generation import get_package_status
    NEW_ARCHITECTURE_AVAILABLE = True
    logger.info("🎉 新アーキテクチャパッケージが利用可能です")
except ImportError:
    NEW_ARCHITECTURE_AVAILABLE = False
    logger.info("🔄 新アーキテクチャパッケージが見つかりません - 個別モジュールをチェック")

# =============================================================================
# 個別モジュールのフォールバック付きインポート
# =============================================================================

# CSS管理
CSS_MANAGER_AVAILABLE = False
try:
    if NEW_ARCHITECTURE_AVAILABLE:
        from report_generation.templates.css_manager import CSSManager
        def _get_css_styles():
            return CSSManager.get_complete_styles()
        CSS_MANAGER_AVAILABLE = True
    else:
        from templates.css_manager import CSSManager
        def _get_css_styles():
            return CSSManager.get_complete_styles()
        CSS_MANAGER_AVAILABLE = True
except ImportError:
    try:
        from css_styles import CSSStyles
        def _get_css_styles():
            return CSSStyles.get_integrated_report_styles()
        logger.info("CSS管理: css_stylesモジュールを使用")
    except ImportError:
        def _get_css_styles():
            return """
            <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: #f5f7fa; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .action-card { background: white; border-radius: 8px; padding: 20px; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .priority-urgent { border-left: 5px solid #e74c3c; }
            .priority-medium { border-left: 5px solid #f39c12; }
            .priority-low { border-left: 5px solid #27ae60; }
            .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin: 15px 0; }
            .kpi-item { background: #f8f9fa; padding: 10px; border-radius: 4px; }
            .improvement-status { font-weight: bold; padding: 5px 10px; border-radius: 15px; color: white; display: inline-block; }
            .status-excellent { background: #27ae60; }
            .status-good { background: #2ecc71; }
            .status-fair { background: #f39c12; }
            .status-poor { background: #e74c3c; }
            .status-critical { background: #c0392b; }
            </style>
            """
        logger.warning("CSS管理: デフォルトスタイルを使用")

# スコア設定管理
SCORING_CONFIG_AVAILABLE = False
try:
    if NEW_ARCHITECTURE_AVAILABLE:
        from report_generation.config.scoring_config import DEFAULT_SCORING_CONFIG, ScoringConfig
        SCORING_CONFIG = DEFAULT_SCORING_CONFIG
        SCORING_CONFIG_AVAILABLE = True
    else:
        from config.scoring_config import DEFAULT_SCORING_CONFIG, ScoringConfig
        SCORING_CONFIG = DEFAULT_SCORING_CONFIG
        SCORING_CONFIG_AVAILABLE = True
except ImportError:
    class ScoringConfig:
        def get_achievement_score_mapping(self):
            return [(110, 50), (105, 45), (100, 40), (98, 35), (95, 25), (90, 15), (85, 5), (0, 0)]
        
        def get_improvement_score_mapping(self):
            return [(15, 25), (10, 20), (5, 15), (2, 10), (-2, 5), (-5, 3), (-10, 1), (-100, 0)]
        
        def get_stability_score_mapping(self):
            return [(5, 15), (10, 12), (15, 8), (20, 4), (100, 0)]
    
    SCORING_CONFIG = ScoringConfig()
    logger.info("スコア設定: デフォルト設定を使用")

# ハイスコア計算
HIGH_SCORE_CALCULATOR_AVAILABLE = False
try:
    if NEW_ARCHITECTURE_AVAILABLE:
        from report_generation.calculators.high_score_calculator import (
            HighScoreCalculator,
            calculate_high_score as new_calculate_high_score,
            calculate_all_high_scores as new_calculate_all_high_scores
        )
        HIGH_SCORE_CALCULATOR_AVAILABLE = True
    else:
        from calculators.high_score_calculator import (
            HighScoreCalculator,
            calculate_high_score as new_calculate_high_score,
            calculate_all_high_scores as new_calculate_all_high_scores
        )
        HIGH_SCORE_CALCULATOR_AVAILABLE = True
except ImportError:
    logger.info("ハイスコア計算: レガシー実装を使用")

# UIコンポーネント
UI_COMPONENTS_AVAILABLE = False
try:
    if NEW_ARCHITECTURE_AVAILABLE:
        from report_generation.components.ui_components import (
            generate_weekly_highlights_by_type as new_generate_highlights_by_type,
            create_improvement_status_badge,
            format_achievement_percentage
        )
        UI_COMPONENTS_AVAILABLE = True
    else:
        from components.ui_components import (
            generate_weekly_highlights_by_type as new_generate_highlights_by_type,
            create_improvement_status_badge,
            format_achievement_percentage
        )
        UI_COMPONENTS_AVAILABLE = True
except ImportError:
    logger.info("UIコンポーネント: レガシー実装を使用")

# HTMLテンプレート
HTML_TEMPLATES_AVAILABLE = False
try:
    if NEW_ARCHITECTURE_AVAILABLE:
        from report_generation.templates.html_templates import HTMLTemplateManager
        HTML_TEMPLATES_AVAILABLE = True
    else:
        from templates.html_templates import HTMLTemplateManager
        HTML_TEMPLATES_AVAILABLE = True
except ImportError:
    logger.info("HTMLテンプレート: インライン実装を使用")

# レポート生成器
REPORT_GENERATOR_AVAILABLE = False
try:
    if NEW_ARCHITECTURE_AVAILABLE:
        from report_generation.generators.report_generator import UnifiedReportGenerator
        REPORT_GENERATOR_AVAILABLE = True
    else:
        from generators.report_generator import UnifiedReportGenerator
        REPORT_GENERATOR_AVAILABLE = True
except ImportError:
    logger.info("レポート生成器: 従来実装を使用")

# =============================================================================
# 必須依存関係の確認
# =============================================================================
try:
    from utils import calculate_kpi, calculate_dept_kpi, calculate_ward_kpi
    from mobile_report_generator import generate_mobile_report
    from ward_utils import get_ward_list, calculate_ward_summary
    from config import get_hospital_targets, DEFAULT_TARGET_VALUES
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logger.error(f"必須依存関係が不足しています: {e}")
    DEPENDENCIES_AVAILABLE = False

# =============================================================================
# モジュール利用可能性の確認とログ出力
# =============================================================================
def log_module_availability():
    """モジュールの利用可能性をログ出力"""
    modules_status = {
        'NEW_ARCHITECTURE': NEW_ARCHITECTURE_AVAILABLE,
        'CSS_MANAGER': CSS_MANAGER_AVAILABLE,
        'SCORING_CONFIG': SCORING_CONFIG_AVAILABLE,
        'HIGH_SCORE_CALCULATOR': HIGH_SCORE_CALCULATOR_AVAILABLE,
        'UI_COMPONENTS': UI_COMPONENTS_AVAILABLE,
        'HTML_TEMPLATES': HTML_TEMPLATES_AVAILABLE,
        'REPORT_GENERATOR': REPORT_GENERATOR_AVAILABLE,
        'DEPENDENCIES': DEPENDENCIES_AVAILABLE
    }
    
    available_count = sum(modules_status.values())
    total_count = len(modules_status)
    
    logger.info(f"🔧 モジュール状況: {available_count}/{total_count} 利用可能")
    
    for module, available in modules_status.items():
        status = "✅" if available else "❌"
        logger.debug(f"  {module}: {status}")

# 初期化時にログ出力
log_module_availability()

# =============================================================================
# グローバル設定
# =============================================================================
# 完全リファクタリング状況
FULLY_REFACTORED = NEW_ARCHITECTURE_AVAILABLE and all([
    CSS_MANAGER_AVAILABLE,
    SCORING_CONFIG_AVAILABLE,
    HIGH_SCORE_CALCULATOR_AVAILABLE,
    UI_COMPONENTS_AVAILABLE,
    HTML_TEMPLATES_AVAILABLE,
    REPORT_GENERATOR_AVAILABLE
])

# 部分リファクタリング状況
PARTIALLY_REFACTORED = any([
    CSS_MANAGER_AVAILABLE,
    SCORING_CONFIG_AVAILABLE,
    HIGH_SCORE_CALCULATOR_AVAILABLE,
    UI_COMPONENTS_AVAILABLE
])

# =============================================================================
# レガシー実装（フォールバック用）
# =============================================================================
def _legacy_calculate_high_score(kpi_data: Dict) -> Optional[float]:
    """レガシー版ハイスコア計算"""
    try:
        # 達成度スコア
        achievement_rate = kpi_data.get('daily_census_achievement', 0)
        achievement_score = 0
        for threshold, score in SCORING_CONFIG.get_achievement_score_mapping():
            if achievement_rate >= threshold:
                achievement_score = score
                break
        
        # 改善度スコア（簡易版）
        improvement_rate = kpi_data.get('improvement_rate', 0)
        improvement_score = max(0, min(25, improvement_rate * 2))
        
        # 安定性スコア（簡易版）
        stability = kpi_data.get('stability_score', 10)
        stability_score = max(0, 15 - stability)
        
        total_score = achievement_score + improvement_score + stability_score
        return min(100, max(0, total_score))
        
    except Exception as e:
        logger.error(f"レガシーハイスコア計算エラー: {e}")
        return None

def _legacy_calculate_all_high_scores(df: pd.DataFrame, target_data: pd.DataFrame, period: str) -> Tuple[List[Dict], List[Dict]]:
    """レガシー版全体ハイスコア計算"""
    try:
        from utils import calculate_dept_kpi, calculate_ward_kpi
        
        dept_scores = []
        ward_scores = []
        
        # 診療科スコア計算
        departments = df['診療科'].unique()
        for dept in departments:
            if pd.isna(dept):
                continue
            
            dept_kpi = calculate_dept_kpi(df, dept, target_data, period)
            if dept_kpi:
                score = _legacy_calculate_high_score(dept_kpi)
                if score is not None:
                    dept_scores.append({
                        'name': dept,
                        'score': score,
                        'kpi': dept_kpi
                    })
        
        # 病棟スコア計算
        wards = df['病棟'].unique()
        for ward in wards:
            if pd.isna(ward):
                continue
                
            ward_kpi = calculate_ward_kpi(df, ward, target_data, period)
            if ward_kpi:
                score = _legacy_calculate_high_score(ward_kpi)
                if score is not None:
                    ward_scores.append({
                        'name': ward,
                        'score': score,
                        'kpi': ward_kpi
                    })
        
        # スコア順にソート
        dept_scores.sort(key=lambda x: x['score'], reverse=True)
        ward_scores.sort(key=lambda x: x['score'], reverse=True)
        
        return dept_scores, ward_scores
        
    except Exception as e:
        logger.error(f"レガシー全体ハイスコア計算エラー: {e}")
        return [], []

def _legacy_generate_weekly_highlights(dept_scores: List[Dict], ward_scores: List[Dict]) -> Tuple[str, str]:
    """レガシー版週次ハイライト生成"""
    try:
        # 診療科ハイライト
        if dept_scores:
            top_dept = dept_scores[0]
            dept_highlight = f"🏆 {top_dept['name']}が{top_dept['score']:.1f}点でトップ！"
            if len(dept_scores) > 1:
                second_dept = dept_scores[1]
                dept_highlight += f" {second_dept['name']}も{second_dept['score']:.1f}点で好調です。"
        else:
            dept_highlight = "各診療科で改善が進んでいます。"
        
        # 病棟ハイライト
        if ward_scores:
            top_ward = ward_scores[0]
            ward_highlight = f"🏆 {top_ward['name']}が{top_ward['score']:.1f}点でトップ！"
            if len(ward_scores) > 1:
                second_ward = ward_scores[1]
                ward_highlight += f" {second_ward['name']}も{second_ward['score']:.1f}点で安定運営中です。"
        else:
            ward_highlight = "各病棟で安定運営が継続されています。"
        
        return dept_highlight, ward_highlight
        
    except Exception as e:
        logger.error(f"レガシーハイライト生成エラー: {e}")
        return "診療科パフォーマンス確認中", "病棟運営状況確認中"

# =============================================================================
# 統合インターフェース関数
# =============================================================================
def _calculate_high_score(kpi_data: Dict) -> Optional[float]:
    """ハイスコア計算の統合インターフェース"""
    if HIGH_SCORE_CALCULATOR_AVAILABLE:
        return new_calculate_high_score(kpi_data)
    else:
        return _legacy_calculate_high_score(kpi_data)

def _calculate_all_high_scores(df: pd.DataFrame, target_data: pd.DataFrame, period: str) -> Tuple[List[Dict], List[Dict]]:
    """全体ハイスコア計算の統合インターフェース"""
    if HIGH_SCORE_CALCULATOR_AVAILABLE:
        return new_calculate_all_high_scores(df, target_data, period)
    else:
        return _legacy_calculate_all_high_scores(df, target_data, period)

def _generate_weekly_highlights_by_type(dept_scores: List[Dict], ward_scores: List[Dict]) -> Tuple[str, str]:
    """週次ハイライト生成の統合インターフェース"""
    if UI_COMPONENTS_AVAILABLE:
        return new_generate_highlights_by_type(dept_scores, ward_scores)
    else:
        return _legacy_generate_weekly_highlights(dept_scores, ward_scores)

# =============================================================================
# 実装状況の診断機能
# =============================================================================
def get_implementation_status() -> Dict[str, Any]:
    """現在の実装状況を取得"""
    if NEW_ARCHITECTURE_AVAILABLE:
        try:
            return report_generation.get_package_status()
        except AttributeError:
            # 新アーキテクチャはあるが、get_package_statusが未実装の場合
            pass
    
    return {
        'mode': 'fully_refactored' if FULLY_REFACTORED else 'hybrid' if PARTIALLY_REFACTORED else 'legacy',
        'new_architecture': NEW_ARCHITECTURE_AVAILABLE,
        'css_manager': CSS_MANAGER_AVAILABLE,
        'scoring_config': SCORING_CONFIG_AVAILABLE,
        'high_score_calculator': HIGH_SCORE_CALCULATOR_AVAILABLE,
        'ui_components': UI_COMPONENTS_AVAILABLE,
        'html_templates': HTML_TEMPLATES_AVAILABLE,
        'report_generator': REPORT_GENERATOR_AVAILABLE,
        'dependencies': DEPENDENCIES_AVAILABLE
    }

def validate_dependencies() -> Tuple[bool, List[str]]:
    """依存関係の検証"""
    missing_modules = []
    
    # 必須モジュールのチェック
    required_modules = [
        ('utils', 'calculate_kpi, calculate_dept_kpi, calculate_ward_kpi'),
        ('mobile_report_generator', 'generate_mobile_report'),
        ('ward_utils', 'get_ward_list, calculate_ward_summary'),
        ('config', 'get_hospital_targets, DEFAULT_TARGET_VALUES')
    ]
    
    for module_name, functions in required_modules:
        try:
            module = __import__(module_name)
            for func in functions.split(', '):
                if not hasattr(module, func):
                    missing_modules.append(f"{module_name}.{func}")
        except ImportError:
            missing_modules.append(module_name)
    
    return len(missing_modules) == 0, missing_modules

# =============================================================================
# メイン関数（統合HTMLレポート生成）
# =============================================================================
def generate_all_in_one_html_report(df: pd.DataFrame, target_data: pd.DataFrame, 
                                   period: str = "直近12週") -> str:
    """
    統合HTMLレポート生成のメインエントリーポイント
    
    新アーキテクチャを優先的に使用し、利用できない場合は段階的に
    従来の実装にフォールバックする
    """
    try:
        # 完全新アーキテクチャが利用可能な場合
        if FULLY_REFACTORED and REPORT_GENERATOR_AVAILABLE:
            logger.info("🎉 完全新アーキテクチャでレポート生成")
            generator = UnifiedReportGenerator()
            return generator.generate_complete_report(df, target_data, period)
        
        # 部分的新機能が利用可能な場合（ハイブリッド）
        elif PARTIALLY_REFACTORED:
            logger.info("⚡ ハイブリッドモードでレポート生成")
            return _generate_hybrid_html_report(df, target_data, period)
        
        # 完全レガシーモード
        else:
            logger.info("🔄 レガシーモードでレポート生成")
            return _generate_legacy_html_report(df, target_data, period)
            
    except Exception as e:
        logger.error(f"HTMLレポート生成エラー: {e}")
        return _generate_error_html_report(str(e), period)

def _generate_hybrid_html_report(df: pd.DataFrame, target_data: pd.DataFrame, period: str) -> str:
    """ハイブリッドモードでのHTMLレポート生成"""
    try:
        # ハイスコア計算
        dept_scores, ward_scores = _calculate_all_high_scores(df, target_data, period)
        
        # ハイライト生成
        dept_highlight, ward_highlight = _generate_weekly_highlights_by_type(dept_scores, ward_scores)
        
        # CSS取得
        css_styles = _get_css_styles()
        
        # 基本統計計算
        total_patients = len(df)
        avg_census = df.groupby('日付')['在院患者数'].sum().mean() if '在院患者数' in df.columns else 0
        
        # HTML構築
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>統合パフォーマンスレポート - {period}</title>
    {css_styles}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 統合パフォーマンスレポート</h1>
            <p><strong>期間:</strong> {period}</p>
            <p><strong>生成日時:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary-section">
            <h2>📈 データ概要</h2>
            <div class="kpi-grid">
                <div class="kpi-item">
                    <strong>データ行数:</strong> {total_patients:,}行
                </div>
                <div class="kpi-item">
                    <strong>平均在院患者数:</strong> {avg_census:.1f}人
                </div>
                <div class="kpi-item">
                    <strong>分析期間:</strong> {period}
                </div>
                <div class="kpi-item">
                    <strong>処理日時:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </div>
        
        <div class="highlights-section">
            <h2>🏆 週次ハイライト</h2>
            <div class="highlight-card">
                <h3>診療科部門</h3>
                <p>{dept_highlight}</p>
            </div>
            <div class="highlight-card">
                <h3>病棟部門</h3>
                <p>{ward_highlight}</p>
            </div>
        </div>
        
        <div class="scores-section">
            <h2>🎯 ハイスコアランキング</h2>
            <div class="scores-grid">
                <div class="dept-scores">
                    <h3>診療科TOP5</h3>
                    {_generate_scores_table(dept_scores[:5])}
                </div>
                <div class="ward-scores">
                    <h3>病棟TOP5</h3>
                    {_generate_scores_table(ward_scores[:5])}
                </div>
            </div>
        </div>
        
        <div class="status-section">
            <h2>🔧 システム状況</h2>
            <p>⚡ ハイブリッドモードで動作中</p>
            <p>利用可能な新機能のみを使用してレポートを生成しています。</p>
            {_generate_module_status_display()}
        </div>
    </div>
</body>
</html>"""
        
        return html_content
        
    except Exception as e:
        logger.error(f"ハイブリッドHTMLレポート生成エラー: {e}")
        return _generate_error_html_report(str(e), period)

def _generate_legacy_html_report(df: pd.DataFrame, target_data: pd.DataFrame, period: str) -> str:
    """レガシーモードでのHTMLレポート生成"""
    try:
        # 基本統計
        total_patients = len(df)
        processing_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # レガシー実装でハイスコア計算
        dept_scores, ward_scores = _legacy_calculate_all_high_scores(df, target_data, period)
        
        # レガシー実装でハイライト生成
        dept_highlight, ward_highlight = _legacy_generate_weekly_highlights(dept_scores, ward_scores)
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>統合パフォーマンスレポート - {period}</title>
    {_get_css_styles()}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 統合パフォーマンスレポート</h1>
            <p><strong>期間:</strong> {period}</p>
            <div class="warning-banner">
                ⚠️ フォールバックモードで動作中<br>
                新アーキテクチャおよびハイブリッド実装が利用できません。<br>
                基本的なレポート機能のみ提供しています。
            </div>
        </div>
        
        <div class="summary-section">
            <h2>📈 データ概要</h2>
            <ul>
                <li>データ行数: {total_patients:,}行</li>
                <li>分析期間: {period}</li>
                <li>処理日時: {processing_time}</li>
            </ul>
        </div>
        
        <div class="highlights-section">
            <h2>🏆 パフォーマンスハイライト</h2>
            <div class="dept-highlight">
                <h3>診療科部門</h3>
                <p>{dept_highlight}</p>
            </div>
            <div class="ward-highlight">
                <h3>病棟部門</h3>
                <p>{ward_highlight}</p>
            </div>
        </div>
        
        <div class="improvement-section">
            <h2>🔧 改善のために</h2>
            <p>完全な機能を利用するには、以下をご確認ください：</p>
            <ul>
                <li>report_generation パッケージのインストール</li>
                <li>必要な依存関係のインストール</li>
                <li>設定ファイルの配置</li>
            </ul>
        </div>
        
        <div class="footer">
            <p style="text-align: center; color: #666; margin-top: 30px;">
                生成日時: {processing_time} | レガシーモード
            </p>
        </div>
    </div>
</body>
</html>"""
        
        return html_content
        
    except Exception as e:
        logger.error(f"レガシーHTMLレポート生成エラー: {e}")
        return _generate_error_html_report(str(e), period)

def _generate_scores_table(scores: List[Dict]) -> str:
    """スコアテーブルのHTML生成"""
    if not scores:
        return "<p>データがありません</p>"
    
    table_html = "<table class='scores-table'><thead><tr><th>順位</th><th>名前</th><th>スコア</th></tr></thead><tbody>"
    
    for i, score_data in enumerate(scores, 1):
        name = score_data.get('name', 'Unknown')
        score = score_data.get('score', 0)
        table_html += f"<tr><td>{i}</td><td>{name}</td><td>{score:.1f}</td></tr>"
    
    table_html += "</tbody></table>"
    return table_html

def _generate_module_status_display() -> str:
    """モジュール状況表示のHTML生成"""
    status = get_implementation_status()
    
    status_html = "<div class='module-status'>"
    status_html += f"<p><strong>動作モード:</strong> {status.get('mode', 'unknown')}</p>"
    
    modules = [
        ('CSS Manager', status.get('css_manager', False)),
        ('Scoring Config', status.get('scoring_config', False)),
        ('High Score Calculator', status.get('high_score_calculator', False)),
        ('UI Components', status.get('ui_components', False))
    ]
    
    for name, available in modules:
        icon = "✅" if available else "❌"
        status_html += f"<p>{icon} {name}</p>"
    
    status_html += "</div>"
    return status_html

def _generate_error_html_report(error_message: str, period: str) -> str:
    """エラー時のHTMLレポート生成"""
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>エラー - 統合パフォーマンスレポート</title>
    <style>
        body {{ font-family: sans-serif; padding: 20px; background: #f8f9fa; }}
        .error-container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .error-header {{ color: #e74c3c; border-bottom: 2px solid #e74c3c; padding-bottom: 10px; margin-bottom: 20px; }}
        .error-details {{ background: #f8f9fa; padding: 15px; border-radius: 4px; border-left: 4px solid #e74c3c; }}
        .suggestions {{ background: #e8f5e9; padding: 15px; border-radius: 4px; border-left: 4px solid #4caf50; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-header">
            <h1>🚨 レポート生成エラー</h1>
        </div>
        <p>統合パフォーマンスレポートの生成中にエラーが発生しました。</p>
        
        <div class="error-details">
            <h3>エラー詳細:</h3>
            <p>{error_message}</p>
            <p><strong>期間:</strong> {period}</p>
            <p><strong>発生時刻:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="suggestions">
            <h3>💡 解決方法:</h3>
            <ul>
                <li>データファイルが正しく読み込まれているか確認してください</li>
                <li>必要なモジュールがインストールされているか確認してください</li>
                <li>report_generation パッケージの導入を検討してください</li>
                <li>問題が継続する場合は、システム管理者にお問い合わせください</li>
            </ul>
        </div>
    </div>
</body>
</html>"""

# =============================================================================
# ユーティリティ関数群
# =============================================================================
def test_high_score_functionality() -> bool:
    """ハイスコア機能のテスト"""
    try:
        # テストデータ
        test_kpi = {
            'daily_census_achievement': 95.5,
            'improvement_rate': 2.3,
            'stability_score': 8.2
        }
        
        score = _calculate_high_score(test_kpi)
        return score is not None and isinstance(score, (int, float))
        
    except Exception as e:
        logger.error(f"ハイスコア機能テストエラー: {e}")
        return False

def get_refactoring_progress() -> Dict[str, Any]:
    """リファクタリング進捗状況の取得"""
    status = get_implementation_status()
    
    # 進捗計算
    total_modules = 7  # NEW_ARCHITECTURE, CSS_MANAGER, SCORING_CONFIG, HIGH_SCORE_CALCULATOR, UI_COMPONENTS, HTML_TEMPLATES, REPORT_GENERATOR
    available_modules = sum([
        status.get('new_architecture', False),
        status.get('css_manager', False),
        status.get('scoring_config', False),
        status.get('high_score_calculator', False),
        status.get('ui_components', False),
        status.get('html_templates', False),
        status.get('report_generator', False)
    ])
    
    progress_percentage = (available_modules / total_modules) * 100
    
    return {
        'progress_percentage': progress_percentage,
        'available_modules': available_modules,
        'total_modules': total_modules,
        'mode': status.get('mode', 'unknown'),
        'dependencies_ok': status.get('dependencies', False),
        'recommendations': _get_refactoring_recommendations(status)
    }

def _get_refactoring_recommendations(status: Dict[str, Any]) -> List[str]:
    """リファクタリング推奨事項の生成"""
    recommendations = []
    
    if not status.get('new_architecture', False):
        recommendations.append("新アーキテクチャパッケージ(report_generation)のインストール")
    
    if not status.get('css_manager', False):
        recommendations.append("CSS管理モジュールの導入")
    
    if not status.get('high_score_calculator', False):
        recommendations.append("ハイスコア計算モジュールの実装")
    
    if not status.get('ui_components', False):
        recommendations.append("UIコンポーネントモジュールの追加")
    
    if not status.get('dependencies', False):
        recommendations.append("必須依存関係の確認・修復")
    
    if not recommendations:
        recommendations.append("全ての新機能が利用可能です！")
    
    return recommendations

def export_implementation_report() -> str:
    """実装状況レポートのエクスポート"""
    status = get_implementation_status()
    progress = get_refactoring_progress()
    
    report = f"""
# HTML Export Functions - 実装状況レポート

## 📊 概要
- **生成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **動作モード**: {status.get('mode', 'unknown')}
- **進捗率**: {progress['progress_percentage']:.1f}% ({progress['available_modules']}/{progress['total_modules']})

## 🔧 モジュール状況
"""
    
    modules = [
        ('新アーキテクチャ', status.get('new_architecture', False)),
        ('CSS管理', status.get('css_manager', False)),
        ('スコア設定', status.get('scoring_config', False)),
        ('ハイスコア計算', status.get('high_score_calculator', False)),
        ('UIコンポーネント', status.get('ui_components', False)),
        ('HTMLテンプレート', status.get('html_templates', False)),
        ('レポート生成器', status.get('report_generator', False)),
        ('依存関係', status.get('dependencies', False))
    ]
    
    for name, available in modules:
        status_icon = "✅" if available else "❌"
        report += f"- {status_icon} {name}\n"
    
    report += f"\n## 💡 推奨事項\n"
    for recommendation in progress['recommendations']:
        report += f"- {recommendation}\n"
    
    report += f"""
## 🚀 次のステップ
1. 不足しているモジュールのインストール
2. 設定ファイルの配置確認
3. 依存関係の解決
4. 統合テストの実行

## 📝 詳細情報
- **ハイスコア機能**: {'利用可能' if test_high_score_functionality() else '要実装'}
- **レガシーフォールバック**: 有効
- **エラーハンドリング**: 強化済み
"""
    
    return report

# =============================================================================
# 外部インターフェース関数（後方互換性）
# =============================================================================
def calculate_high_score(kpi_data: Dict) -> Optional[float]:
    """ハイスコア計算（外部インターフェース）"""
    return _calculate_high_score(kpi_data)

def calculate_all_high_scores(df: pd.DataFrame, target_data: pd.DataFrame, period: str) -> Tuple[List[Dict], List[Dict]]:
    """全体ハイスコア計算（外部インターフェース）"""
    return _calculate_all_high_scores(df, target_data, period)

def generate_weekly_highlights_by_type(dept_scores: List[Dict], ward_scores: List[Dict]) -> Tuple[str, str]:
    """週次ハイライト生成（外部インターフェース）"""
    return _generate_weekly_highlights_by_type(dept_scores, ward_scores)

# メイン関数のエイリアス
generate_unified_html_export = generate_all_in_one_html_report

# =============================================================================
# 初期化とログ出力
# =============================================================================
# 起動時の状況ログ出力
startup_status = get_implementation_status()
if startup_status.get('mode') == 'fully_refactored':
    logger.info("🎉 新アーキテクチャで完全動作中")
elif startup_status.get('mode') == 'hybrid':
    logger.info("⚡ ハイブリッドモードで動作中")
else:
    logger.warning("🔄 レガシーモードで動作中")

# =============================================================================
# メイン実行部（デバッグ・テスト用）
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("html_export_functions.py - リファクタリング対応完全版")
    print("=" * 60)
    
    # 実装状況の表示
    status = get_implementation_status()
    progress = get_refactoring_progress()
    
    print(f"\n📊 実装状況:")
    print(f"   動作モード: {status.get('mode', 'unknown')}")
    print(f"   進捗率: {progress['progress_percentage']:.1f}%")
    print(f"   利用可能モジュール: {progress['available_modules']}/{progress['total_modules']}")
    
    print(f"\n🔧 モジュール詳細:")
    modules = [
        ('新アーキテクチャ', 'new_architecture'),
        ('CSS管理', 'css_manager'),
        ('スコア設定', 'scoring_config'),
        ('ハイスコア計算', 'high_score_calculator'),
        ('UIコンポーネント', 'ui_components'),
        ('HTMLテンプレート', 'html_templates'),
        ('レポート生成器', 'report_generator'),
        ('依存関係', 'dependencies')
    ]
    
    for name, key in modules:
        available = status.get(key, False)
        status_icon = "✅" if available else "❌"
        print(f"   {status_icon} {name}")
    
    print(f"\n🧪 機能テスト:")
    high_score_test = test_high_score_functionality()
    print(f"   {'✅' if high_score_test else '❌'} ハイスコア計算")
    
    dependencies_ok, missing = validate_dependencies()
    print(f"   {'✅' if dependencies_ok else '❌'} 依存関係")
    if not dependencies_ok:
        print(f"      不足: {', '.join(missing)}")
    
    print(f"\n💡 推奨事項:")
    for recommendation in progress['recommendations']:
        print(f"   • {recommendation}")
    
    if progress['progress_percentage'] == 100:
        print(f"\n🎉 全ての新機能が利用可能です！最適なパフォーマンスで動作します。")
    elif progress['progress_percentage'] > 50:
        print(f"\n⚡ ハイブリッドモードで動作中。利用可能な新機能を活用しています。")
    else:
        print(f"\n🔄 レガシーモードで動作中。新モジュールの導入を推奨します。")
    
    print(f"\n📈 統計:")
    try:
        with open(__file__, 'r', encoding='utf-8') as f:
            current_lines = len(f.readlines())
        print(f"   現在のファイル: {current_lines}行")
        print(f"   元のファイル: 3,600行（推定）")
        if current_lines < 3600:
            reduction = ((3600 - current_lines) / 3600) * 100
            print(f"   削減率: {reduction:.1f}%")
    except:
        print("   ファイル統計: 取得不可")
    
    print("=" * 60)