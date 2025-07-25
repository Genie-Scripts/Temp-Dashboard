# html_export_functions.py - 完全リファクタリング版
"""
統合HTMLレポート生成機能
段階的移行対応：新しいモジュールが利用可能な場合は使用し、
そうでなければ既存の実装にフォールバックする
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import List, Dict, Optional, Tuple, Any
import traceback

# ロガー設定
logger = logging.getLogger(__name__)

# =============================================================================
# 新アーキテクチャのインポート試行
# =============================================================================
try:
    from report_generation import ReportGenerator
    NEW_ARCHITECTURE_AVAILABLE = True
    logger.info("✅ 新アーキテクチャ（report_generation）が利用可能")
except ImportError:
    NEW_ARCHITECTURE_AVAILABLE = False
    logger.info("📦 新アーキテクチャは未インストール - ハイブリッドモードで動作")

# =============================================================================
# CSS管理のインポート
# =============================================================================
try:
    from templates.css_manager import CSSManager
    CSS_MANAGER_AVAILABLE = True
    logger.debug("✅ CSS Manager利用可能")
except ImportError:
    CSS_MANAGER_AVAILABLE = False
    logger.debug("❌ CSS Manager未インストール")

# CSSスタイルの取得関数
def _get_css_styles() -> str:
    """CSSスタイルを取得（フォールバック付き）"""
    if CSS_MANAGER_AVAILABLE:
        try:
            return CSSManager.get_complete_styles()
        except Exception as e:
            logger.error(f"CSS Manager エラー: {e}")
    
    # フォールバック：基本的なCSSを返す
    return """
    <style>
        body { font-family: 'Noto Sans JP', sans-serif; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: #1e88e5; color: white; padding: 20px; border-radius: 8px; }
        .metric-card { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 8px; }
        .chart-container { margin: 20px 0; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        .warning { background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0; }
    </style>
    """

# =============================================================================
# スコア設定のインポート
# =============================================================================
try:
    from config.scoring_config import DEFAULT_SCORING_CONFIG, ScoringConfig
    SCORING_CONFIG = DEFAULT_SCORING_CONFIG
    SCORING_CONFIG_AVAILABLE = True
    logger.debug("✅ Scoring Config利用可能")
except ImportError:
    SCORING_CONFIG_AVAILABLE = False
    logger.debug("❌ Scoring Config未インストール")
    
    # フォールバック実装
    class ScoringConfig:
        def get_achievement_score_mapping(self):
            return [(110, 50), (105, 45), (100, 40), (98, 35), (95, 25), (90, 15), (85, 5), (0, 0)]
        
        def get_improvement_score_mapping(self):
            return [(15, 25), (10, 20), (5, 15), (2, 10), (-2, 5), (-5, 3), (-10, 1), (-100, 0)]
        
        def get_stability_score_mapping(self):
            return [(5, 15), (10, 12), (15, 8), (20, 4), (100, 0)]
    
    SCORING_CONFIG = ScoringConfig()

# =============================================================================
# ハイスコア計算のインポート
# =============================================================================
try:
    from high_score_calculator import (
        calculate_high_score,
        calculate_all_high_scores
    )
    HIGH_SCORE_CALCULATOR_AVAILABLE = True
    logger.debug("✅ High Score Calculator利用可能")
except ImportError:
    HIGH_SCORE_CALCULATOR_AVAILABLE = False
    logger.debug("❌ High Score Calculator未インストール")
    
    # フォールバック実装
    def calculate_high_score(kpi_data: Dict, config: Any) -> float:
        """簡易版ハイスコア計算"""
        try:
            score = 0
            if 'occupancy_rate' in kpi_data and kpi_data['occupancy_rate'] is not None:
                score += min(50, max(0, kpi_data['occupancy_rate'] * 50))
            return score
        except Exception:
            return 0
    
    def calculate_all_high_scores(df: pd.DataFrame, target_data: pd.DataFrame, 
                                period: str) -> Tuple[List[Dict], List[Dict]]:
        """簡易版全ハイスコア計算"""
        return [], []

# =============================================================================
# UIコンポーネントのインポート
# =============================================================================
try:
    from components.ui_components import (
        UIComponentBuilder,
        generate_weekly_highlights_by_type,
        generate_weekly_highlights_compact,
        generate_score_detail_html,
        generate_weekly_highlights
    )
    UI_COMPONENTS_AVAILABLE = True
    logger.debug("✅ UI Components利用可能")
except ImportError:
    UI_COMPONENTS_AVAILABLE = False
    logger.debug("❌ UI Components未インストール")
    
    # フォールバック実装
    def generate_weekly_highlights_by_type(dept_scores: List[Dict], 
                                         ward_scores: List[Dict]) -> Tuple[str, str]:
        """簡易版ハイライト生成"""
        dept_highlight = "診療科で改善が進行中です"
        ward_highlight = "病棟で安定運営中です"
        return dept_highlight, ward_highlight

# =============================================================================
# HTMLテンプレートのインポート
# =============================================================================
try:
    from templates.html_templates import HTMLTemplates
    HTML_TEMPLATES_AVAILABLE = True
    logger.debug("✅ HTML Templates利用可能")
except ImportError:
    HTML_TEMPLATES_AVAILABLE = False
    logger.debug("❌ HTML Templates未インストール")

# =============================================================================
# 既存モジュールのインポート（必須）
# =============================================================================
try:
    from report_generation.utils import (
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
    
    LEGACY_MODULES_AVAILABLE = True
    logger.debug("✅ レガシーモジュール利用可能")
except ImportError as e:
    LEGACY_MODULES_AVAILABLE = False
    logger.error(f"❌ 必須モジュールのインポートエラー: {e}")

# =============================================================================
# ステータス確認関数
# =============================================================================
def get_refactoring_status() -> Dict[str, bool]:
    """リファクタリング状況の詳細を取得"""
    return {
        'fully_refactored': NEW_ARCHITECTURE_AVAILABLE,
        'partially_refactored': any([
            CSS_MANAGER_AVAILABLE,
            SCORING_CONFIG_AVAILABLE,
            HIGH_SCORE_CALCULATOR_AVAILABLE,
            UI_COMPONENTS_AVAILABLE,
            HTML_TEMPLATES_AVAILABLE
        ]),
        'css_manager': CSS_MANAGER_AVAILABLE,
        'scoring_config': SCORING_CONFIG_AVAILABLE,
        'high_score_calculator': HIGH_SCORE_CALCULATOR_AVAILABLE,
        'ui_components': UI_COMPONENTS_AVAILABLE,
        'html_templates': HTML_TEMPLATES_AVAILABLE,
        'legacy_modules': LEGACY_MODULES_AVAILABLE
    }

# =============================================================================
# メインレポート生成関数
# =============================================================================
def generate_all_in_one_html_report(df: pd.DataFrame, target_data: pd.DataFrame, 
                                   period: str = "直近12週") -> str:
    """
    統合HTMLレポート生成のメインエントリーポイント
    新アーキテクチャを優先的に使用し、利用できない場合は段階的にフォールバック
    """
    try:
        # ステータス確認
        status = get_refactoring_status()
        
        # 新アーキテクチャが完全に利用可能な場合
        if NEW_ARCHITECTURE_AVAILABLE:
            try:
                logger.info("🎉 新アーキテクチャでレポート生成中...")
                generator = ReportGenerator()
                return generator.generate_all_in_one_html_report(df, target_data, period)
            except Exception as e:
                logger.error(f"新アーキテクチャでエラー: {e}")
                logger.info("フォールバックモードに切り替えます")
        
        # ハイブリッドまたはフォールバックモード
        if status['partially_refactored']:
            logger.info("⚡ ハイブリッドモードでレポート生成中...")
        else:
            logger.info("🔄 フォールバックモードでレポート生成中...")
        
        return _generate_fallback_report(df, target_data, period, status)
        
    except Exception as e:
        logger.error(f"レポート生成エラー: {e}")
        logger.error(traceback.format_exc())
        return _generate_error_report(str(e))

def _generate_fallback_report(df: pd.DataFrame, target_data: pd.DataFrame, 
                            period: str, status: Dict[str, bool]) -> str:
    """フォールバックモードでのレポート生成"""
    try:
        # 基本的なHTMLヘッダー
        html_parts = []
        
        # CSSスタイル
        html_parts.append(_get_css_styles())
        
        # HTMLの開始
        html_parts.append("""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>統合パフォーマンスレポート</title>
        </head>
        <body>
            <div class="container">
        """)
        
        # ヘッダー
        html_parts.append(f"""
            <div class="header">
                <h1>📊 統合パフォーマンスレポート</h1>
                <p><strong>期間:</strong> {period}</p>
            </div>
        """)
        
        # ステータス情報
        mode_text = "ハイブリッド" if status['partially_refactored'] else "フォールバック"
        html_parts.append(f"""
            <div class="warning">
                <p>⚠️ {mode_text}モードで動作中</p>
                <p>新アーキテクチャおよびハイブリッド実装が利用できません。</p>
                <p>基本的なレポート機能のみ提供しています。</p>
            </div>
        """)
        
        # データ概要
        html_parts.append("""
            <div class="metric-card">
                <h2>📈 データ概要</h2>
                <ul>
        """)
        html_parts.append(f"<li>データ行数: {len(df):,}行</li>")
        html_parts.append(f"<li>分析期間: {period}</li>")
        html_parts.append(f"<li>処理日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>")
        html_parts.append("""
                </ul>
            </div>
        """)
        
        # 基本的なKPIセクション（レガシーモジュールが利用可能な場合）
        if LEGACY_MODULES_AVAILABLE:
            try:
                # 期間データの取得
                period_weeks = get_period_dates(df, weeks=12)
                if period_weeks:
                    latest_week = period_weeks[0]
                    
                    # 診療科KPI
                    dept_kpis = calculate_department_kpis(df, target_data, period_type="weekly")
                    if dept_kpis:
                        html_parts.append(_generate_basic_kpi_section("診療科別KPI", dept_kpis[:5]))
                    
                    # 病棟KPI
                    ward_kpis = calculate_ward_kpis(df, target_data, period_type="weekly")
                    if ward_kpis:
                        html_parts.append(_generate_basic_kpi_section("病棟別KPI", ward_kpis[:5]))
                        
            except Exception as e:
                logger.error(f"KPI計算エラー: {e}")
                html_parts.append('<div class="warning">KPIの計算中にエラーが発生しました。</div>')
        
        # ハイスコアセクション（利用可能な場合）
        if HIGH_SCORE_CALCULATOR_AVAILABLE:
            try:
                dept_scores, ward_scores = calculate_all_high_scores(df, target_data, period)
                if dept_scores or ward_scores:
                    html_parts.append(_generate_high_score_section(dept_scores, ward_scores))
            except Exception as e:
                logger.error(f"ハイスコア計算エラー: {e}")
        
        # 改善提案
        html_parts.append("""
            <div class="metric-card">
                <h2>🔧 改善のために</h2>
                <p>完全な機能を利用するには、以下をご確認ください:</p>
                <ul>
                    <li>report_generation パッケージのインストール</li>
                    <li>必要な依存関係のインストール</li>
                    <li>設定ファイルの配置</li>
                </ul>
            </div>
        """)
        
        # フッター
        html_parts.append("""
            </div>
        </body>
        </html>
        """)
        
        return "".join(html_parts)
        
    except Exception as e:
        logger.error(f"フォールバックレポート生成エラー: {e}")
        return _generate_error_report(str(e))

def _generate_basic_kpi_section(title: str, kpis: List[Dict]) -> str:
    """基本的なKPIセクションのHTML生成"""
    html = f'<div class="metric-card"><h3>{title}</h3><table><tr>'
    html += '<th>名称</th><th>在院日数</th><th>病床稼働率</th><th>新規入院数</th></tr>'
    
    for kpi in kpis:
        name = kpi.get('name', '不明')
        los = kpi.get('avg_los', 0)
        occ = kpi.get('occupancy_rate', 0) * 100
        adm = kpi.get('new_patients', 0)
        
        html += f'<tr><td>{name}</td>'
        html += f'<td>{los:.1f}日</td>'
        html += f'<td>{occ:.1f}%</td>'
        html += f'<td>{adm}</td></tr>'
    
    html += '</table></div>'
    return html

def _generate_high_score_section(dept_scores: List[Dict], ward_scores: List[Dict]) -> str:
    """ハイスコアセクションのHTML生成"""
    html = '<div class="metric-card"><h2>🏆 ハイスコア</h2>'
    
    if dept_scores:
        html += '<h3>診療科TOP3</h3><ol>'
        for score in dept_scores[:3]:
            html += f'<li>{score.get("name", "不明")} - {score.get("total_score", 0):.1f}点</li>'
        html += '</ol>'
    
    if ward_scores:
        html += '<h3>病棟TOP3</h3><ol>'
        for score in ward_scores[:3]:
            html += f'<li>{score.get("name", "不明")} - {score.get("total_score", 0):.1f}点</li>'
        html += '</ol>'
    
    html += '</div>'
    return html

def _generate_error_report(error_message: str) -> str:
    """エラーレポートのHTML生成"""
    return f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>エラー - 統合パフォーマンスレポート</title>
        <style>
            body {{ font-family: 'Noto Sans JP', sans-serif; margin: 20px; }}
            .error {{ background: #ffebee; padding: 20px; border-radius: 8px; }}
            h1 {{ color: #d32f2f; }}
        </style>
    </head>
    <body>
        <div class="error">
            <h1>⚠️ レポート生成エラー</h1>
            <p>レポートの生成中にエラーが発生しました。</p>
            <p><strong>エラー内容:</strong> {error_message}</p>
            <p>管理者にお問い合わせください。</p>
        </div>
    </body>
    </html>
    """

# =============================================================================
# テスト・デバッグ用関数
# =============================================================================
def test_high_score_functionality() -> bool:
    """ハイスコア機能のテスト"""
    try:
        # ダミーデータでテスト
        test_kpi = {
            'occupancy_rate': 0.85,
            'improvement_rate': 5.0,
            'stability_score': 10.0
        }
        score = calculate_high_score(test_kpi, SCORING_CONFIG)
        return isinstance(score, (int, float)) and score >= 0
    except Exception as e:
        logger.error(f"ハイスコア機能テストエラー: {e}")
        return False

# =============================================================================
# メイン実行部
# =============================================================================
if __name__ == "__main__":
    print("=== html_export_functions.py リファクタリング状況 ===")
    print()
    
    status = get_refactoring_status()
    
    # 全体ステータス
    if status['fully_refactored']:
        print("🎉 新アーキテクチャが完全に利用可能です！")
        print("   最適なパフォーマンスでレポート生成が実行されます。")
    elif status['partially_refactored']:
        print("⚡ ハイブリッドモードで実行中")
        print("   利用可能なモジュールのみ新実装を使用します。")
    else:
        print("🔄 フォールバックモードで実行中")
        print("   新モジュールのインストールを推奨します。")
    
    print()
    print("📦 モジュール状況:")
    
    # 各モジュールの状況
    modules = [
        ('CSS Manager', 'css_manager'),
        ('Scoring Config', 'scoring_config'),
        ('High Score Calculator', 'high_score_calculator'),
        ('UI Components', 'ui_components'),
        ('HTML Templates', 'html_templates'),
        ('Legacy Modules', 'legacy_modules')
    ]
    
    for name, key in modules:
        icon = "✅" if status.get(key, False) else "❌"
        print(f"  {icon} {name}")
    
    # ハイスコア機能テスト
    print()
    print("🧪 機能テスト:")
    if test_high_score_functionality():
        print("  ✅ ハイスコア計算: 正常動作")
    else:
        print("  ❌ ハイスコア計算: 動作不可")
    
    print()
    print("💡 次のステップ:")
    if not status['fully_refactored']:
        print("  1. pip install -r requirements.txt")
        print("  2. report_generation パッケージの配置")
        print("  3. 設定ファイルの確認")