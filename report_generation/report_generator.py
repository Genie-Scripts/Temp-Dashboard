# report_generator.py
"""
統合レポート生成のメインオーケストレーター
元のhtml_export_functions.pyの機能を分離されたモジュールを使って再構築
"""

import pandas as pd
import logging
import urllib.parse
from typing import Dict, List, Tuple, Optional
import sys
import os

# パスの追加（report_generationフォルダから親ディレクトリのモジュールにアクセス）
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 分離したモジュールのインポート
try:
    from .high_score_calculator import HighScoreCalculator
except ImportError:
    from high_score_calculator import HighScoreCalculator

try:
    from .components.ui_components import UIComponentBuilder
except ImportError:
    from components.ui_components import UIComponentBuilder

try:
    from .templates.html_templates import HTMLTemplates, InfoPanelContent, JavaScriptTemplates
except ImportError:
    from templates.html_templates import HTMLTemplates, InfoPanelContent, JavaScriptTemplates

try:
    from .css_styles import CSSStyles
except ImportError:
    from css_styles import CSSStyles

try:
    from .config.scoring_config import ScoringConfig
except ImportError:
    from config.scoring_config import ScoringConfig

# 必要なユーティリティのインポート（親ディレクトリから）
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

logger = logging.getLogger(__name__)

class ReportGenerator:
    """統合レポート生成のメインクラス"""
    
    def __init__(self, scoring_config: ScoringConfig = None):
        """
        Args:
            scoring_config: スコア計算設定
        """
        self.scoring_config = scoring_config or ScoringConfig()
        self.score_calculator = HighScoreCalculator(self.scoring_config)
        self.ui_builder = UIComponentBuilder()
        self.html_templates = HTMLTemplates()
        self.js_templates = JavaScriptTemplates()
        
    def generate_all_in_one_html_report(self, df: pd.DataFrame, 
                                      target_data: pd.DataFrame, 
                                      period: str = "直近12週") -> str:
        """
        全ての診療科・病棟データを含む、単一の統合HTMLレポートを生成する
        
        Args:
            df: メインデータフレーム
            target_data: 目標データ
            period: 分析期間
            
        Returns:
            統合HTMLレポート文字列
        """
        try:
            logger.info(f"統合レポート生成開始: {period}")
            
            # 基本データの準備
            report_data = self._prepare_report_data(df, target_data, period)
            if not report_data['start_date']:
                return self._generate_error_html("分析期間を計算できませんでした。")
            
            # 各ビューのコンテンツ生成
            content_html = self._generate_all_view_contents(
                df, target_data, report_data
            )
            
            # 最終HTMLの組み立て
            final_html = self._assemble_final_html(content_html, report_data)
            
            logger.info("統合レポート生成完了")
            return final_html
            
        except Exception as e:
            logger.error(f"統合HTMLレポート生成エラー: {e}", exc_info=True)
            return self._generate_error_html(f"レポート全体の生成でエラーが発生しました: {e}")
    
    def _prepare_report_data(self, df: pd.DataFrame, 
                           target_data: pd.DataFrame, 
                           period: str) -> Dict:
        """レポート生成に必要な基本データを準備"""
        start_date, end_date, period_desc = get_period_dates(df, period)
        
        hospital_targets = get_hospital_targets(target_data)
        dept_col = '診療科名'
        all_departments = sorted(df[dept_col].dropna().unique()) if dept_col in df.columns else []
        all_wards = get_target_ward_list(target_data, EXCLUDED_WARDS)
        
        return {
            'start_date': start_date,
            'end_date': end_date,
            'period_desc': period_desc,
            'hospital_targets': hospital_targets,
            'dept_col': dept_col,
            'all_departments': all_departments,
            'all_wards': all_wards,
            'period': period
        }
    
    def _generate_all_view_contents(self, df: pd.DataFrame, 
                                  target_data: pd.DataFrame, 
                                  report_data: Dict) -> str:
        """全てのビューコンテンツを生成"""
        content_html = ""
        
        # 全体ビューの生成
        content_html += self._generate_overall_view(df, target_data, report_data)
        
        # 診療科別ビューの生成
        content_html += self._generate_department_views(df, target_data, report_data)
        
        # 病棟別ビューの生成
        content_html += self._generate_ward_views(df, target_data, report_data)
        
        # ハイスコアビューの生成
        content_html += self._generate_high_score_view(df, target_data, report_data)
        
        return content_html
    
    def _generate_overall_view(self, df: pd.DataFrame, 
                             target_data: pd.DataFrame, 
                             report_data: Dict) -> str:
        """全体ビューの生成"""
        try:
            start_date = report_data['start_date']
            end_date = report_data['end_date']
            hospital_targets = report_data['hospital_targets']
            
            overall_df = df[(df['日付'] >= start_date) & (df['日付'] <= end_date)]
            overall_kpi = calculate_department_kpis(
                df, target_data, '全体', '病院全体', start_date, end_date, None
            )
            overall_feasibility = evaluate_feasibility(overall_kpi, overall_df, start_date, end_date)
            overall_simulation = calculate_effect_simulation(overall_kpi)
            overall_html_kpi = _adapt_kpi_for_html_generation(overall_kpi)
            
            cards_all = _generate_metric_cards_html(overall_html_kpi, is_ward=False)
            charts_all = _generate_charts_html(overall_df, overall_html_kpi)
            analysis_all = _generate_action_plan_html(
                overall_html_kpi, overall_feasibility, overall_simulation, hospital_targets
            )
            
            # ハイライトバナーの生成
            highlight_html = self._generate_highlight_banner(df, target_data, report_data)
            
            overall_content = highlight_html + cards_all + charts_all + analysis_all
            return f'<div id="view-all" class="view-content active">{overall_content}</div>'
            
        except Exception as e:
            logger.error(f"全体ビュー生成エラー: {e}")
            return '<div id="view-all" class="view-content active"><p>エラー: 全体データを生成できませんでした。</p></div>'
    
    def _generate_highlight_banner(self, df: pd.DataFrame, 
                                 target_data: pd.DataFrame, 
                                 report_data: Dict) -> str:
        """ハイライトバナーの生成"""
        try:
            # ハイスコア計算
            dept_scores, ward_scores = self.score_calculator.calculate_all_high_scores(
                df, target_data, report_data['period']
            )
            
            # 辞書形式に変換（UIコンポーネントとの互換性のため）
            dept_dicts = [score.to_dict() for score in dept_scores]
            ward_dicts = [score.to_dict() for score in ward_scores]
            
            return self.ui_builder.build_highlight_banner(dept_dicts, ward_dicts)
            
        except Exception as e:
            logger.error(f"ハイライトバナー生成エラー: {e}")
            return ""
    
    def _generate_department_views(self, df: pd.DataFrame, 
                                 target_data: pd.DataFrame, 
                                 report_data: Dict) -> str:
        """診療科別ビューの生成"""
        content_html = ""
        
        for dept_name in report_data['all_departments']:
            dept_id = f"view-dept-{urllib.parse.quote(dept_name)}"
            try:
                dept_content = self._generate_single_department_view(
                    df, target_data, dept_name, report_data
                )
                content_html += f'<div id="{dept_id}" class="view-content">{dept_content}</div>'
                
            except Exception as e:
                logger.error(f"診療科「{dept_name}」のレポート部品生成エラー: {e}")
                error_content = f'<p>エラー: {dept_name}のレポートを生成できませんでした。</p>'
                content_html += f'<div id="{dept_id}" class="view-content">{error_content}</div>'
        
        return content_html
    
    def _generate_single_department_view(self, df: pd.DataFrame, 
                                       target_data: pd.DataFrame, 
                                       dept_name: str, 
                                       report_data: Dict) -> str:
        """単一診療科のビュー生成"""
        dept_col = report_data['dept_col']
        start_date = report_data['start_date']
        end_date = report_data['end_date']
        hospital_targets = report_data['hospital_targets']
        
        df_dept = df[df[dept_col] == dept_name]
        raw_kpi = calculate_department_kpis(
            df, target_data, dept_name, dept_name, start_date, end_date, dept_col
        )
        
        if not raw_kpi:
            return f'<p>エラー: {dept_name}のKPIを計算できませんでした。</p>'
        
        feasibility = evaluate_feasibility(raw_kpi, df_dept, start_date, end_date)
        simulation = calculate_effect_simulation(raw_kpi)
        html_kpi = _adapt_kpi_for_html_generation(raw_kpi)
        
        cards = _generate_metric_cards_html(html_kpi, is_ward=False)
        charts = _generate_charts_html(df_dept, html_kpi)
        analysis = _generate_action_plan_html(html_kpi, feasibility, simulation, hospital_targets)
        
        return cards + charts + analysis
    
    def _generate_ward_views(self, df: pd.DataFrame, 
                           target_data: pd.DataFrame, 
                           report_data: Dict) -> str:
        """病棟別ビューの生成"""
        content_html = ""
        
        for ward_code, ward_name in report_data['all_wards']:
            ward_id = f"view-ward-{ward_code}"
            try:
                ward_content = self._generate_single_ward_view(
                    df, target_data, ward_code, ward_name, report_data
                )
                content_html += f'<div id="{ward_id}" class="view-content">{ward_content}</div>'
                
            except Exception as e:
                logger.error(f"病棟「{ward_name}」のレポート部品生成エラー: {e}")
                error_content = f'<p>エラー: {ward_name}のレポートを生成できませんでした。</p>'
                content_html += f'<div id="{ward_id}" class="view-content">{error_content}</div>'
        
        return content_html
    
    def _generate_single_ward_view(self, df: pd.DataFrame, 
                                 target_data: pd.DataFrame, 
                                 ward_code: str, 
                                 ward_name: str, 
                                 report_data: Dict) -> str:
        """単一病棟のビュー生成"""
        start_date = report_data['start_date']
        end_date = report_data['end_date']
        hospital_targets = report_data['hospital_targets']
        
        df_ward = df[df['病棟コード'] == ward_code]
        raw_kpi = calculate_ward_kpis(
            df, target_data, ward_code, ward_name, start_date, end_date, '病棟コード'
        )
        
        if not raw_kpi:
            return f'<p>エラー: {ward_name}のKPIを計算できませんでした。</p>'
        
        feasibility = evaluate_feasibility(raw_kpi, df_ward, start_date, end_date)
        simulation = calculate_effect_simulation(raw_kpi)
        html_kpi = _adapt_kpi_for_html_generation(raw_kpi)
        final_kpi = calculate_ward_kpi_with_bed_metrics(html_kpi, raw_kpi.get('bed_count'))
        
        cards = _generate_metric_cards_html(final_kpi, is_ward=True)
        charts = _generate_charts_html(df_ward, final_kpi)
        analysis = _generate_action_plan_html(final_kpi, feasibility, simulation, hospital_targets)
        
        return cards + charts + analysis
    
    def _generate_high_score_view(self, df: pd.DataFrame, 
                                target_data: pd.DataFrame, 
                                report_data: Dict) -> str:
        """ハイスコアビューの生成"""
        try:
            # ハイスコア計算
            dept_scores, ward_scores = self.score_calculator.calculate_all_high_scores(
                df, target_data, report_data['period']
            )
            
            # 辞書形式に変換（UIコンポーネントとの互換性のため）
            dept_dicts = [score.to_dict() for score in dept_scores]
            ward_dicts = [score.to_dict() for score in ward_scores]
            
            # UIコンポーネントでハイスコアビュー生成
            high_score_content = self.ui_builder.build_high_score_view(
                dept_dicts, ward_dicts, report_data['period_desc']
            )
            
            return f'<div id="view-high-score" class="view-content">{high_score_content}</div>'
            
        except Exception as e:
            logger.error(f"ハイスコアビュー生成エラー: {e}")
            return '''
            <div id="view-high-score" class="view-content">
                <div class="section">
                    <h2>🏆 週間ハイスコア TOP3</h2>
                    <p>データの取得に失敗しました。</p>
                </div>
            </div>
            '''
    
    def _assemble_final_html(self, content_html: str, report_data: Dict) -> str:
        """最終HTMLの組み立て"""
        try:
            # 各部品の生成
            header_html = self.html_templates.get_header_template().format(
                period_desc=report_data['period_desc']
            )
            
            # ドロップダウンオプション生成
            dept_options = self.html_templates.generate_department_options(
                report_data['all_departments']
            )
            ward_options = self.html_templates.generate_ward_options(
                report_data['all_wards']
            )
            
            controls_html = self.html_templates.get_controls_template().format(
                dept_options=dept_options,
                ward_options=ward_options
            )
            
            # 情報パネル生成
            info_panel_html = self.html_templates.get_info_panel_template().format(
                info_tabs_content=InfoPanelContent.get_all_info_tabs_content()
            )
            
            # CSS取得
            css = CSSStyles.get_integrated_report_styles()
            
            # JavaScript取得
            javascript = self.js_templates.get_main_script()
            
            # 最終HTML組み立て
            final_html = self.html_templates.get_base_template().format(
                title="統合パフォーマンスレポート（直近週重視版）",
                css=css,
                header=header_html,
                controls=controls_html,
                content=content_html,
                info_panel=info_panel_html,
                javascript=javascript
            )
            
            return final_html
            
        except Exception as e:
            logger.error(f"最終HTML組み立てエラー: {e}")
            return self._generate_error_html(f"HTMLの組み立てでエラーが発生しました: {e}")
    
    def _generate_error_html(self, error_message: str) -> str:
        """エラー用HTMLの生成"""
        return f"<html><body>エラー: {error_message}</body></html>"

# 後方互換性のための関数（元のhtml_export_functions.pyとの互換性維持）
def generate_all_in_one_html_report(df, target_data, period="直近12週"):
    """
    従来のgenerate_all_in_one_html_report関数の互換性維持
    新しいクラスベースの実装を内部で使用
    """
    generator = ReportGenerator()
    return generator.generate_all_in_one_html_report(df, target_data, period)