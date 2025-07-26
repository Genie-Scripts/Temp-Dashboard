import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import logging
from typing import Dict, Any, Optional
from css_styles import CSSStyles

# --- 必要な分析・計算モジュールをインポート ---
from utils import evaluate_feasibility, calculate_effect_simulation
from enhanced_action_analysis import generate_comprehensive_action_data

logger = logging.getLogger(__name__)

def _generate_metric_cards_html(kpi, is_ward=False):
    """週報向けメトリクスカード生成（98%基準・新入院目標値表示版）"""
    
    # --- 必要なデータを取得 ---
    # 在院患者数関連
    avg_patients = kpi.get('avg_patients', 0)  # 期間平均
    target_patients = kpi.get('target_patients', 0)
    recent_week_census = kpi.get('recent_week_daily_census', 0)  # 直近週平均
    achievement_rate = kpi.get('achievement_rate', 0)
    
    # 新入院関連
    weekly_avg_admissions = kpi.get('weekly_avg_admissions', 0)  # 期間平均
    recent_week_admissions = kpi.get('recent_week_admissions', 0)  # 直近週
    target_admissions = kpi.get('target_admissions', 0)  # 新入院目標値（これが重要！）
    
    # 平均在院日数関連
    los_avg = kpi.get('avg_length_of_stay', 0)  # 期間平均
    los_recent = kpi.get('recent_week_avg_los', 0)  # 直近週
    
    # --- 評価計算 ---
    # 在院患者数の変化率計算
    census_change_rate = ((recent_week_census - avg_patients) / avg_patients * 100) if avg_patients > 0 else 0
    census_evaluation = _evaluate_census_performance(census_change_rate)
    
    # 新入院の変化率計算
    admission_change_rate = ((recent_week_admissions - weekly_avg_admissions) / weekly_avg_admissions * 100) if weekly_avg_admissions > 0 else 0
    admission_evaluation = _evaluate_admission_performance(admission_change_rate)
    
    # 在院日数の評価（98%基準）
    los_change_rate = ((los_recent - los_avg) / los_avg * 100) if los_avg > 0 else 0
    is_target_achieved = achievement_rate >= 98  # 98%基準に変更
    los_evaluation = _evaluate_los_performance(los_change_rate, is_target_achieved)
    
    # 総合評価の計算
    overall_evaluation = _calculate_overall_evaluation(achievement_rate, census_change_rate, is_target_achieved)
    
    # --- カード1: 在院患者数 ---
    card1_html = f"""
    <div class="summary-card metric-card-split {census_evaluation['card_class']}">
        <h3>👥 在院患者数</h3>
        <div class="metric-split-container">
            <div class="metric-left">
                <div class="metric-label">期間平均</div>
                <div class="metric-value">{avg_patients:.1f}人</div>
                <div class="metric-sub">目標: {target_patients or '--'}人</div>
            </div>
            <div class="metric-divider"></div>
            <div class="metric-right">
                <div class="metric-label">直近週</div>
                <div class="metric-value">{recent_week_census:.1f}人</div>
                <div class="metric-trend {census_evaluation['trend_class']}">
                    {census_evaluation['icon']} {census_change_rate:+.1f}%
                </div>
                <div class="metric-status">{census_evaluation['status']}</div>
            </div>
        </div>
    </div>
    """
    
    # --- カード2: 週間新入院（目標値表示追加） ---
    # 目標値の表示を改善
    if target_admissions and target_admissions > 0:
        target_display = f"目標: {target_admissions:.1f}人/週"
        # 新入院達成率の計算
        admission_achievement = (recent_week_admissions / target_admissions * 100) if target_admissions > 0 else 0
        admission_achievement_text = f"（達成率: {admission_achievement:.1f}%）"
    else:
        target_display = "週間"
        admission_achievement_text = ""
    
    card2_html = f"""
    <div class="summary-card metric-card-split {admission_evaluation['card_class']}">
        <h3>🏥 週間新入院</h3>
        <div class="metric-split-container">
            <div class="metric-left">
                <div class="metric-label">期間平均</div>
                <div class="metric-value">{weekly_avg_admissions:.1f}人</div>
                <div class="metric-sub">{target_display}</div>
            </div>
            <div class="metric-divider"></div>
            <div class="metric-right">
                <div class="metric-label">直近週</div>
                <div class="metric-value">{recent_week_admissions:.1f}人</div>
                <div class="metric-trend {admission_evaluation['trend_class']}">
                    {admission_evaluation['icon']} {admission_change_rate:+.1f}%
                </div>
                <div class="metric-status">{admission_evaluation['status']} {admission_achievement_text}</div>
            </div>
        </div>
    </div>
    """

    # --- カード3: 平均在院日数（98%基準） ---
    los_recommendation = ""
    if not is_target_achieved and los_change_rate < -3:
        los_recommendation = "<div class='metric-recommend'>→ 在院日数延長を推奨</div>"
    elif is_target_achieved and los_change_rate > 5:
        los_recommendation = "<div class='metric-recommend'>→ 効率化の余地あり</div>"
    
    card3_html = f"""
    <div class="summary-card metric-card-split {los_evaluation['card_class']}">
        <h3>📅 平均在院日数</h3>
        <div class="metric-split-container">
            <div class="metric-left">
                <div class="metric-label">期間平均</div>
                <div class="metric-value">{los_avg:.1f}日</div>
                <div class="metric-sub">&nbsp;</div>
            </div>
            <div class="metric-divider"></div>
            <div class="metric-right">
                <div class="metric-label">直近週</div>
                <div class="metric-value">{los_recent:.1f}日</div>
                <div class="metric-trend {los_evaluation['trend_class']}">
                    {los_evaluation['icon']} {los_change_rate:+.1f}%
                </div>
                <div class="metric-status">{los_evaluation['status']}</div>
            </div>
        </div>
        {los_recommendation}
    </div>
    """
    
    # --- カード4: 週間総合評価 ---
    card4_html = f"""
    <div class="summary-card metric-card-split {overall_evaluation['card_class']}">
        <h3>⭐ 今週の総合評価</h3>
        <div class="metric-split-container">
            <div class="metric-left">
                <div class="metric-label">目標達成度</div>
                <div class="metric-value">{achievement_rate:.1f}%</div>
                <div class="metric-sub">{'達成（98%以上）' if is_target_achieved else '未達成'}</div>
            </div>
            <div class="metric-divider"></div>
            <div class="metric-right">
                <div class="metric-label">週間評価</div>
                <div class="metric-value" style="font-size: 1.8em;">{overall_evaluation['grade']}</div>
                <div class="metric-status">{overall_evaluation['status']}</div>
            </div>
        </div>
    </div>
    """
    
    return f"""
    <div class="summary-cards">
        {card1_html}
        {card2_html}
        {card3_html}
        {card4_html}
    </div>
    """


def _evaluate_census_performance(change_rate):
    """在院患者数のパフォーマンス評価"""
    if change_rate >= 10:
        return {
            'status': '大幅改善',
            'icon': '🔥',
            'trend_class': 'trend-excellent',
            'card_class': 'card-excellent'
        }
    elif change_rate >= 5:
        return {
            'status': '改善',
            'icon': '📈',
            'trend_class': 'trend-good',
            'card_class': 'card-good'
        }
    elif change_rate >= -5:
        return {
            'status': '維持',
            'icon': '➡️',
            'trend_class': 'trend-stable',
            'card_class': 'card-info'
        }
    elif change_rate >= -10:
        return {
            'status': '低下',
            'icon': '📉',
            'trend_class': 'trend-warning',
            'card_class': 'card-warning'
        }
    else:
        return {
            'status': '要注意',
            'icon': '⚠️',
            'trend_class': 'trend-danger',
            'card_class': 'card-danger'
        }


def _evaluate_admission_performance(change_rate):
    """新入院のパフォーマンス評価"""
    if change_rate >= 10:
        return {
            'status': '大幅増加',
            'icon': '🚀',
            'trend_class': 'trend-excellent',
            'card_class': 'card-excellent'
        }
    elif change_rate >= 5:
        return {
            'status': '好調',
            'icon': '📈',
            'trend_class': 'trend-good',
            'card_class': 'card-good'
        }
    elif change_rate >= -5:
        return {
            'status': '安定',
            'icon': '➡️',
            'trend_class': 'trend-stable',
            'card_class': 'card-info'
        }
    else:
        return {
            'status': '要改善',
            'icon': '📉',
            'trend_class': 'trend-warning',
            'card_class': 'card-warning'
        }

def _evaluate_los_performance(change_rate, is_target_achieved):
    """平均在院日数のパフォーマンス評価（98%基準版）"""
    if is_target_achieved:  # 98%以上達成時
        # 目標達成時：短縮は効率的、延長は要確認
        if change_rate <= -5:
            return {
                'status': '効率的',
                'icon': '🌟',
                'trend_class': 'trend-excellent',
                'card_class': 'card-excellent'
            }
        elif change_rate <= -3:
            return {
                'status': '良好',
                'icon': '✅',
                'trend_class': 'trend-good',
                'card_class': 'card-good'
            }
        elif change_rate <= 3:
            return {
                'status': '安定',
                'icon': '➡️',
                'trend_class': 'trend-stable',
                'card_class': 'card-info'
            }
        else:
            return {
                'status': '要確認',
                'icon': '🔍',
                'trend_class': 'trend-warning',
                'card_class': 'card-warning'
            }
    else:  # 98%未満の場合
        # 目標未達成時：延長は改善傾向、短縮は要検討
        if change_rate >= 3:
            return {
                'status': '改善中',
                'icon': '📈',
                'trend_class': 'trend-good',
                'card_class': 'card-good'
            }
        elif change_rate >= -3:
            return {
                'status': '要対策',
                'icon': '📊',
                'trend_class': 'trend-warning',
                'card_class': 'card-warning'
            }
        else:
            return {
                'status': '要検討',
                'icon': '⚠️',
                'trend_class': 'trend-danger',
                'card_class': 'card-danger'
            }

def _calculate_overall_evaluation(achievement_rate, census_change_rate, is_target_achieved):
    """総合評価の計算（98%基準版）"""
    # グレード判定（98%基準）
    if achievement_rate >= 98 and census_change_rate >= 10:
        return {
            'grade': 'S',
            'status': '目標達成＋大幅改善',
            'card_class': 'card-excellent'
        }
    elif achievement_rate >= 98 and census_change_rate >= 5:
        return {
            'grade': 'A',
            'status': '目標達成＋改善傾向',
            'card_class': 'card-good'
        }
    elif census_change_rate >= 0:
        return {
            'grade': 'B',
            'status': '改善傾向あり',
            'card_class': 'card-info'
        }
    elif census_change_rate >= -5:
        return {
            'grade': 'C',
            'status': '横ばい傾向',
            'card_class': 'card-warning'
        }
    else:
        return {
            'grade': 'D',
            'status': '要改善',
            'card_class': 'card-danger'
        }

def _generate_charts_html(df_filtered, kpi, is_ward=False):
    """チャート部分のHTMLを生成する"""
    try:
        from chart import create_interactive_patient_chart, create_interactive_alos_chart, create_interactive_dual_axis_chart
        
        target_value = kpi.get('target_patients')

        fig_patient = create_interactive_patient_chart(df_filtered, title="", days=90, target_value=target_value)
        fig_alos = create_interactive_alos_chart(df_filtered, title="", days_to_show=90)
        fig_dual = create_interactive_dual_axis_chart(df_filtered, title="", days=90)
        
        return f"""
        <div class="section">
            <h2>📊 90日間トレンド</h2>
            <h3>在院患者数推移</h3>
            <div class="chart-container">{fig_patient.to_html(full_html=False, include_plotlyjs='cdn') if fig_patient else ""}</div>
            <h3>平均在院日数推移</h3>
            <div class="chart-container">{fig_alos.to_html(full_html=False, include_plotlyjs=False) if fig_alos else ""}</div>
            <h3>新入院・退院数推移</h3>
            <div class="chart-container">{fig_dual.to_html(full_html=False, include_plotlyjs=False) if fig_dual else ""}</div>
        </div>
        """
    except Exception as e:
        logger.error(f"チャートHTML生成エラー: {e}")
        return '<div class="section"><h2>📊 90日間トレンド</h2><p>チャート生成中にエラーが発生しました。</p></div>'

def _generate_common_mobile_report(raw_kpi, df_filtered, name, period_desc, feasibility, simulation, hospital_targets, is_ward):
    """診療科・病棟で共通のレポート生成処理"""
    try:
        # データ形式をHTML生成用に変換
        kpi = _adapt_kpi_for_html_generation(raw_kpi)
        if is_ward:
            from ward_utils import calculate_ward_kpi_with_bed_metrics
            kpi = calculate_ward_kpi_with_bed_metrics(kpi, raw_kpi.get('bed_count'))

        # 各セクションのHTMLを生成
        title = f"{'🏥' if is_ward else '🩺'} {name} パフォーマンスレポート"
        header_html = f'<div class="header"><h1>{title}</h1><p>{period_desc}</p></div>'
        cards_html = _generate_metric_cards_html(kpi, is_ward)
        charts_html = _generate_charts_html(df_filtered, kpi)
        analysis_html = _generate_action_plan_html(kpi, feasibility, simulation, hospital_targets)
        
        return f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{name} - レポート</title>
            <style>{_get_css_styles()}</style>
        </head>
        <body>
            {header_html}
            <div class="container">
                {cards_html}
                {charts_html}
                {analysis_html}
            </div>
            <a href="../index.html" class="fab">🏠</a>
        </body>
        </html>
        """
    except Exception as e:
        logger.error(f"{name}のレポート生成エラー: {e}", exc_info=True)
        return f"<html><body>{name}のレポート生成中にエラーが発生しました: {e}</body></html>"

def _lazy_import_functions():
    """必要な関数を遅延インポート"""
    global _dept_functions, _chart_functions
    
    if not _dept_functions:
        try:
            # department_performance_tab から必要な関数をインポート
            from department_performance_tab import (
                calculate_department_kpis,
                decide_action_and_reasoning,
                evaluate_feasibility,
                calculate_effect_simulation,
                get_hospital_targets,
                calculate_los_appropriate_range
            )
            _dept_functions = {
                'calculate_department_kpis': calculate_department_kpis,
                'decide_action_and_reasoning': decide_action_and_reasoning,
                'evaluate_feasibility': evaluate_feasibility,
                'calculate_effect_simulation': calculate_effect_simulation,
                'get_hospital_targets': get_hospital_targets,
                'calculate_los_appropriate_range': calculate_los_appropriate_range
            }
        except ImportError as e:
            logger.error(f"department_performance_tab のインポートエラー: {e}")
            # フォールバック関数を定義
            _dept_functions = {
                'decide_action_and_reasoning': lambda kpi, feas, sim: {
                    'action': 'データ分析中',
                    'reasoning': '詳細な分析を実施中です',
                    'priority': 'medium',
                    'color': '#f5d76e'
                },
                'evaluate_feasibility': lambda kpi, df, start, end: {
                    'admission': {}, 'los': {}, 'los_range': None
                },
                'calculate_effect_simulation': lambda kpi: None,
                'get_hospital_targets': lambda data: {'daily_census': 580, 'daily_admissions': 80},
                'calculate_los_appropriate_range': lambda df, start, end: None
            }
    
    if not _chart_functions:
        try:
            # chart から必要な関数をインポート
            from chart import (
                create_interactive_patient_chart,
                create_interactive_alos_chart,
                create_interactive_dual_axis_chart
            )
            _chart_functions = {
                'create_interactive_patient_chart': create_interactive_patient_chart,
                'create_interactive_alos_chart': create_interactive_alos_chart,
                'create_interactive_dual_axis_chart': create_interactive_dual_axis_chart
            }
        except ImportError as e:
            logger.error(f"chart のインポートエラー: {e}")
            # フォールバック - 空のPlotlyグラフを返す
            def create_fallback_chart(*args, **kwargs):
                import plotly.graph_objects as go
                fig = go.Figure()
                fig.add_annotation(
                    text="グラフ生成機能が利用できません",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
                return fig
            
            _chart_functions = {
                'create_interactive_patient_chart': create_fallback_chart,
                'create_interactive_alos_chart': create_fallback_chart,
                'create_interactive_dual_axis_chart': create_fallback_chart
            }

# utilsからのインポート（これは循環インポートしない）
try:
    from utils import safe_date_filter
except ImportError:
    logger.error("utils のインポートエラー")
    def safe_date_filter(df, start_date, end_date):
        """フォールバック実装"""
        if df.empty or '日付' not in df.columns:
            return df
        return df[(df['日付'] >= start_date) & (df['日付'] <= end_date)]


def generate_department_mobile_report(kpi, period_desc, df_filtered, name, feasibility, simulation, hospital_targets):
    """診療科別モバイルレポートを生成する"""
    return _generate_common_mobile_report(kpi, df_filtered, name, period_desc, feasibility, simulation, hospital_targets, is_ward=False)

def _generate_header_section(dept_name, period_desc):
    """ヘッダーセクションの生成"""
    return f'''
    <div class="header">
        <h1>🏥 {dept_name} 週次レポート</h1>
        <p>{period_desc}</p>
    </div>
    '''


def _generate_metric_cards_section(dept_kpi):
    """メトリクスカードセクションの生成（平均在院日数トレンド分析版）"""
    # カード1: 日平均在院患者数
    census_achievement = dept_kpi.get('daily_census_achievement', 0)
    census_class = _get_achievement_class(census_achievement)
    census_trend = _calculate_trend(
        dept_kpi.get('daily_avg_census', 0),
        dept_kpi.get('recent_week_daily_census', 0)
    )
    
    # カード2: 週合計新入院患者数
    admission_achievement = dept_kpi.get('weekly_admissions_achievement', 0)
    admission_class = _get_achievement_class(admission_achievement)
    admission_trend = _calculate_trend(
        dept_kpi.get('weekly_avg_admissions', 0),
        dept_kpi.get('recent_week_admissions', 0)
    )
    
    # カード3: 平均在院日数（トレンド分析版）
    los_period_avg = dept_kpi.get('avg_length_of_stay', 0)  # 期間平均
    los_recent = dept_kpi.get('recent_week_avg_los', 0)     # 直近週実績
    los_trend_analysis = _calculate_los_trend_analysis(los_period_avg, los_recent)
    
    # カード4: 努力度評価
    effort_status = _calculate_effort_status(dept_kpi)
    
    return f'''
    <div class="summary-cards">
        <div class="summary-card {census_class}">
            <h3>在院患者数</h3>
            <div class="value">{dept_kpi.get('daily_avg_census', 0):.1f}</div>
            <div class="target">目標: {dept_kpi.get('daily_census_target', '--')}人</div>
            <div class="{census_trend['class']}">{census_trend['icon']} {census_trend['text']}</div>
        </div>
        <div class="summary-card {admission_class}">
            <h3>新入院</h3>
            <div class="value">{dept_kpi.get('weekly_avg_admissions', 0):.0f}</div>
            <div class="target">週間実績</div>
            <div class="{admission_trend['class']}">{admission_trend['icon']} {admission_trend['text']}</div>
        </div>
        <div class="summary-card {los_trend_analysis['card_class']}">
            <h3>平均在院日数</h3>
            <div class="value">{los_recent:.1f}</div>
            <div class="target">期間平均: {los_period_avg:.1f}日</div>
            <div class="{los_trend_analysis['trend_class']}">{los_trend_analysis['icon']} {los_trend_analysis['text']}</div>
        </div>
        <div class="summary-card card-info">
            <h3>努力度評価</h3>
            <div class="value" style="font-size: 1.5em;">{effort_status['emoji']}</div>
            <div class="target">{effort_status['status']}</div>
            <div class="trend trend-stable">{effort_status['level']}</div>
        </div>
    </div>
    '''


def _calculate_los_trend_analysis(period_avg, recent_week_avg):
    """
    平均在院日数のトレンド分析
    期間平均に対する直近週のトレンドを判定
    """
    if period_avg == 0 or recent_week_avg == 0:
        return {
            "icon": "❓",
            "text": "データ不足",
            "trend_class": "trend trend-stable",
            "card_class": "card-info"
        }
    
    # 変化量と変化率を計算
    change = recent_week_avg - period_avg
    change_rate = (change / period_avg) * 100
    
    # トレンド判定（在院日数は短い方が良いとする）
    if abs(change_rate) < 3:  # 3%未満は安定
        return {
            "icon": "🟡",
            "text": f"安定 ({change:+.1f}日)",
            "trend_class": "trend trend-stable",
            "card_class": "card-warning"  # 安定は警告色
        }
    elif change > 0:  # 延長傾向（悪化）
        severity = "大幅" if change_rate > 10 else ""
        return {
            "icon": "🔴",
            "text": f"{severity}延長 (+{change:.1f}日)",
            "trend_class": "trend trend-up",
            "card_class": "card-danger"  # 延長は危険色
        }
    else:  # 短縮傾向（改善）
        severity = "大幅" if change_rate < -10 else ""
        return {
            "icon": "🟢",
            "text": f"{severity}短縮 ({change:.1f}日)",
            "trend_class": "trend trend-down",
            "card_class": "card-good"  # 短縮は良好色
        }

def _analyze_department_status(dept_kpi, df_90days):
    """診療科の現状を分析（平均在院日数トレンド分析対応版）"""
    analysis = {
        "issue": "データ不足",
        "trend": "分析中", 
        "opportunity": "詳細分析が必要"
    }
    
    # 課題の特定
    target = dept_kpi.get('daily_census_target')
    current = dept_kpi.get('daily_avg_census', 0)
    
    if target and current:
        gap = target - current
        if gap > 0:
            analysis["issue"] = f"目標まで{gap:.1f}人不足"
        else:
            analysis["issue"] = f"目標を{abs(gap):.1f}人超過達成"
    else:
        # 目標がない場合は在院日数トレンドで判定
        los_period = dept_kpi.get('avg_length_of_stay', 0)
        los_recent = dept_kpi.get('recent_week_avg_los', 0)
        if los_period > 0 and los_recent > 0:
            los_change = los_recent - los_period
            if abs(los_change) < 0.3:
                analysis["issue"] = "在院日数は安定推移"
            elif los_change > 0:
                analysis["issue"] = f"在院日数が延長傾向（+{los_change:.1f}日）"
            else:
                analysis["issue"] = f"在院日数が短縮傾向（{los_change:.1f}日）"
    
    # トレンド分析（在院患者数の動向）
    recent = dept_kpi.get('recent_week_daily_census', 0)
    trend_change = recent - current
    
    if abs(trend_change) < 0.5:
        analysis["trend"] = "直近週は横ばい傾向"
    elif trend_change > 0:
        analysis["trend"] = f"直近週は改善傾向（+{trend_change:.1f}人）"
    else:
        analysis["trend"] = f"直近週は減少傾向（{trend_change:.1f}人）"
    
    # 機会の特定（在院日数トレンドも考慮）
    admission_achievement = dept_kpi.get('weekly_admissions_achievement', 0)
    los_recent = dept_kpi.get('recent_week_avg_los', 0)
    los_avg = dept_kpi.get('avg_length_of_stay', 0)
    
    if admission_achievement >= 90:
        if los_recent < los_avg:
            analysis["opportunity"] = "新入院安定＋在院日数短縮で効率的運営"
        elif los_recent > los_avg:
            analysis["opportunity"] = "新入院は安定、在院日数の効率化余地あり"
        else:
            analysis["opportunity"] = "新入院数が安定、現状維持で良好"
    elif los_recent < los_avg - 0.5:  # 在院日数が大幅短縮
        analysis["opportunity"] = "在院日数効率化成功、新入院増加の余地あり"
    elif los_recent > los_avg + 0.5:  # 在院日数が大幅延長
        analysis["opportunity"] = "在院日数の適正化と新入院増加の両面改善必要"
    else:
        analysis["opportunity"] = "新入院増加と在院日数適正化の両面アプローチ"
    
    return analysis

def _generate_charts_section(df_90days, dept_kpi, dept_name):
    """90日間トレンドグラフセクションの生成"""
    try:
        # 関数を取得
        create_patient_chart = _chart_functions.get('create_interactive_patient_chart')
        create_alos_chart = _chart_functions.get('create_interactive_alos_chart')
        create_dual_chart = _chart_functions.get('create_interactive_dual_axis_chart')
        
        if not all([create_patient_chart, create_alos_chart, create_dual_chart]):
            raise Exception("グラフ生成関数が利用できません")
        
        # グラフ1: 在院患者数推移
        patient_chart = create_patient_chart(
            df_90days,
            title="",
            days=90,
            target_value=dept_kpi.get('daily_census_target')
        )
        patient_chart_html = patient_chart.to_html(
            full_html=False, 
            include_plotlyjs='cdn',
            config={'responsive': True, 'displayModeBar': False}
        ) if patient_chart else '<div class="chart-placeholder">グラフ生成エラー</div>'
        
        # グラフ2: 平均在院日数推移
        alos_chart = create_alos_chart(
            df_90days,
            title="",
            days_to_show=90
        )
        alos_chart_html = alos_chart.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={'responsive': True, 'displayModeBar': False}
        ) if alos_chart else '<div class="chart-placeholder">グラフ生成エラー</div>'
        
        # グラフ3: 新入院・退院推移
        dual_chart = create_dual_chart(
            df_90days,
            title="",
            days=90
        )
        dual_chart_html = dual_chart.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={'responsive': True, 'displayModeBar': False}
        ) if dual_chart else '<div class="chart-placeholder">グラフ生成エラー</div>'
        
        return f"""
        <div class="section">
            <h2>📊 90日間トレンド</h2>
            <h3>在院患者数推移</h3>
            <div class="chart-container">{patient_chart_html}</div>
            
            <h3>平均在院日数推移</h3>
            <div class="chart-container">{alos_chart_html}</div>
            
            <h3>新入院・退院数推移</h3>
            <div class="chart-container">{dual_chart_html}</div>
        </div>
        """
    except Exception as e:
        logger.error(f"グラフ生成エラー: {e}")
        return f'''
        <div class="section">
            <h2>📊 90日間トレンド</h2>
            <div class="chart-placeholder">
                <p>グラフ生成機能が一時的に利用できません</p>
                <p style="font-size: 0.8em; color: #999;">エラー: {str(e)}</p>
            </div>
        </div>
        '''


def _generate_analysis_section(dept_kpi, df_90days):
    """現状分析セクションの生成（トレンド分析強化版）"""
    analysis = _analyze_department_status(dept_kpi, df_90days)
    
    # 在院日数トレンド分析の詳細
    los_period = dept_kpi.get('avg_length_of_stay', 0)
    los_recent = dept_kpi.get('recent_week_avg_los', 0)
    los_trend = _calculate_los_trend_analysis(los_period, los_recent)
    
    return f'''
    <div class="section">
        <h2>🔍 現状分析</h2>
        <p><strong>🔴 課題:</strong> {analysis['issue']}</p>
        <p><strong>📈 トレンド:</strong> {analysis['trend']}</p>
        <p><strong>📊 在院日数:</strong> {los_trend['text']}（期間平均{los_period:.1f}日 → 直近週{los_recent:.1f}日）</p>
        <p><strong>💡 チャンス:</strong> {analysis['opportunity']}</p>
    </div>
    '''


def _generate_action_plan_section(dept_kpi, df_dept_filtered):
    """アクションプランセクションの生成"""
    try:
        # 関数を取得
        evaluate_feasibility = _dept_functions.get('evaluate_feasibility')
        calculate_effect_simulation = _dept_functions.get('calculate_effect_simulation')
        decide_action = _dept_functions.get('decide_action_and_reasoning')
        
        # アクション判定
        start_date = df_dept_filtered['日付'].min()
        end_date = df_dept_filtered['日付'].max()
        
        feasibility = evaluate_feasibility(dept_kpi, df_dept_filtered, start_date, end_date)
        simulation = calculate_effect_simulation(dept_kpi)
        action_result = decide_action(dept_kpi, feasibility, simulation)
        
        # 具体的なアクションプランの生成
        action_items = _generate_specific_action_items(action_result['action'])
        
        return f'''
        <div class="section">
            <h2>🎯 今週のアクションプラン</h2>
            <div style="margin-bottom: 16px; padding: 12px; background: #f8f9fa; border-radius: 8px;">
                <strong>{action_result['action']}</strong>: {action_result['reasoning']}
            </div>
            <ul class="action-list">
                {action_items}
            </ul>
        </div>
        '''
    except Exception as e:
        logger.error(f"アクションプラン生成エラー: {e}")
        return f'''
        <div class="section">
            <h2>🎯 今週のアクションプラン</h2>
            <p>アクションプランの生成に失敗しました</p>
        </div>
        '''


def _generate_effect_section(dept_kpi):
    """期待効果セクションの生成"""
    try:
        calculate_effect_simulation = _dept_functions.get('calculate_effect_simulation')
        simulation = calculate_effect_simulation(dept_kpi) if calculate_effect_simulation else None
        
        if simulation and simulation.get('admission_plan'):
            admission_effect = simulation['admission_plan']['effect']
            los_effect = simulation['los_plan']['effect']
            gap = simulation['gap']
            
            return f'''
            <div class="section">
                <h2>📈 期待効果</h2>
                <p>💡 <strong>新入院週1人増加</strong> → 約{admission_effect:.1f}人増加効果</p>
                <p>📊 <strong>在院日数1日延長</strong> → 約{los_effect:.1f}人増加効果</p>
                <p>🎯 目標達成には<strong>あと{gap:.1f}人</strong>必要</p>
            </div>
            '''
        else:
            return f'''
            <div class="section">
                <h2>📈 期待効果</h2>
                <p>🎯 現状維持により安定した運営を継続</p>
            </div>
            '''
    except Exception as e:
        logger.error(f"期待効果生成エラー: {e}")
        return f'''
        <div class="section">
            <h2>📈 期待効果</h2>
            <p>効果シミュレーションは準備中です</p>
        </div>
        '''

def _assemble_mobile_report(header, metrics, charts, analysis, action, effect):
    """最終的なHTMLレポートの組み立て"""
    css = _get_mobile_optimized_css()
    
    return f'''
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>診療科別週次レポート</title>
        <style>{css}</style>
    </head>
    <body>
        {header}
        <div class="container">
            {metrics}
            {charts}
            {analysis}
            {action}
            {effect}
        </div>
        <a href="index.html" class="fab">🏠</a>
    </body>
    </html>
    '''


def _get_achievement_class(achievement):
    """達成率に応じたCSSクラスを返す"""
    if achievement >= 95:
        return "card-good"
    elif achievement >= 85:
        return "card-warning"
    else:
        return "card-danger"


def _calculate_trend(avg_value, recent_value):
    """トレンドを計算"""
    if avg_value == 0:
        return {"icon": "➡️", "text": "データなし", "class": "trend trend-stable"}
    
    change = recent_value - avg_value
    change_rate = (change / avg_value) * 100
    
    if abs(change_rate) < 3:
        return {"icon": "➡️", "text": "安定", "class": "trend trend-stable"}
    elif change_rate > 0:
        return {"icon": "📈", "text": f"+{change:.1f}", "class": "trend trend-up"}
    else:
        return {"icon": "📉", "text": f"{change:.1f}", "class": "trend trend-down"}

def _calculate_los_trend(avg_los, recent_los):
    """在院日数のトレンドを計算（既存関数・互換性維持）"""
    return _calculate_los_trend_analysis(avg_los, recent_los)


def _get_los_card_class(avg_los, recent_los):
    """在院日数カードのクラスを決定"""
    if avg_los == 0:
        return "card-info"
    
    change_rate = ((recent_los - avg_los) / avg_los) * 100
    
    if abs(change_rate) < 3:
        return "card-warning"
    elif change_rate > 5:
        return "card-danger"
    else:
        return "card-good"

# 追加：適正範囲判定機能
def _calculate_los_appropriate_range(df_90days):
    """
    90日間データから在院日数の適正範囲を推定
    統計的アプローチで上下限を設定
    """
    try:
        if df_90days.empty or '退院患者数' not in df_90days.columns:
            return None
        
        # 日別在院日数を計算
        daily_los_list = []
        for _, row in df_90days.iterrows():
            discharges = row.get('退院患者数', 0)
            patient_days = row.get('在院患者数', 0)
            
            if discharges > 0 and patient_days > 0:
                daily_los = patient_days / discharges
                if 1 <= daily_los <= 100:  # 異常値除外
                    daily_los_list.append(daily_los)
        
        if len(daily_los_list) < 10:  # データ不足
            return None
        
        import numpy as np
        los_array = np.array(daily_los_list)
        
        # 四分位範囲による適正範囲設定
        q25 = np.percentile(los_array, 25)
        q75 = np.percentile(los_array, 75)
        iqr = q75 - q25
        
        # 適正範囲：Q1-1.5*IQR ～ Q3+1.5*IQR
        lower_bound = max(1.0, q25 - 1.5 * iqr)
        upper_bound = q75 + 1.5 * iqr
        
        return {
            "lower": lower_bound,
            "upper": upper_bound,
            "median": np.median(los_array),
            "q25": q25,
            "q75": q75
        }
        
    except Exception as e:
        logger.error(f"適正範囲計算エラー: {e}")
        return None
        
def _generate_enhanced_analysis_section(dept_kpi, df_90days):
    """現状分析セクションの生成（適正範囲判定付き）"""
    analysis = _analyze_department_status(dept_kpi, df_90days)
    
    # 在院日数トレンド分析
    los_period = dept_kpi.get('avg_length_of_stay', 0)
    los_recent = dept_kpi.get('recent_week_avg_los', 0)
    los_trend = _calculate_los_trend_analysis(los_period, los_recent)
    
    # 適正範囲判定
    los_range = _calculate_los_appropriate_range(df_90days)
    range_status = ""
    
    if los_range and los_recent > 0:
        if los_range["lower"] <= los_recent <= los_range["upper"]:
            range_status = f"✅ 適正範囲内（{los_range['lower']:.1f}～{los_range['upper']:.1f}日）"
        elif los_recent < los_range["lower"]:
            range_status = f"⚡ 効率的水準（適正下限{los_range['lower']:.1f}日を下回る）"
        else:
            range_status = f"⚠️ 要改善水準（適正上限{los_range['upper']:.1f}日を上回る）"
    
    return f"""
    <div class="section">
        <h2>🔍 現状分析</h2>
        <p><strong>🔴 課題:</strong> {analysis['issue']}</p>
        <p><strong>📈 トレンド:</strong> {analysis['trend']}</p>
        <p><strong>📊 在院日数:</strong> {los_trend['text']}（期間平均{los_period:.1f}日 → 直近週{los_recent:.1f}日）</p>
        {f'<p><strong>📏 適正性:</strong> {range_status}</p>' if range_status else ''}
        <p><strong>💡 チャンス:</strong> {analysis['opportunity']}</p>
    </div>
    """

def _calculate_effort_status(kpi):
    """努力度評価を計算"""
    current_census = kpi.get('daily_avg_census', 0)
    recent_week_census = kpi.get('recent_week_daily_census', 0)
    census_achievement = kpi.get('daily_census_achievement', 0)
    
    trend_change = recent_week_census - current_census
    
    if census_achievement >= 100:
        if trend_change > 0:
            return {
                'status': "目標突破中",
                'level': "優秀",
                'emoji': "✨",
                'color': "#4CAF50"
            }
        else:
            return {
                'status': "達成継続",
                'level': "良好",
                'emoji': "🎯",
                'color': "#7fb069"
            }
    elif census_achievement >= 85:
        if trend_change > 0:
            return {
                'status': "追い上げ中",
                'level': "改善",
                'emoji': "💪",
                'color': "#FF9800"
            }
        else:
            return {
                'status': "要努力",
                'level': "注意",
                'emoji': "📈",
                'color': "#FFC107"
            }
    else:
        return {
            'status': "要改善",
            'level': "要改善",
            'emoji': "🚨",
            'color': "#F44336"
        }


def _analyze_department_status(dept_kpi, df_90days):
    """診療科の現状を分析（平均在院日数トレンド分析対応版）"""
    analysis = {
        "issue": "データ不足",
        "trend": "分析中", 
        "opportunity": "詳細分析が必要"
    }
    
    # 課題の特定
    target = dept_kpi.get('daily_census_target')
    current = dept_kpi.get('daily_avg_census', 0)
    
    if target and current:
        gap = target - current
        if gap > 0:
            analysis["issue"] = f"目標まで{gap:.1f}人不足"
        else:
            analysis["issue"] = f"目標を{abs(gap):.1f}人超過達成"
    else:
        # 目標がない場合は在院日数トレンドで判定
        los_period = dept_kpi.get('avg_length_of_stay', 0)
        los_recent = dept_kpi.get('recent_week_avg_los', 0)
        if los_period > 0 and los_recent > 0:
            los_change = los_recent - los_period
            if abs(los_change) < 0.3:
                analysis["issue"] = "在院日数は安定推移"
            elif los_change > 0:
                analysis["issue"] = f"在院日数が延長傾向（+{los_change:.1f}日）"
            else:
                analysis["issue"] = f"在院日数が短縮傾向（{los_change:.1f}日）"
    
    # トレンド分析（在院患者数の動向）
    recent = dept_kpi.get('recent_week_daily_census', 0)
    trend_change = recent - current
    
    if abs(trend_change) < 0.5:
        analysis["trend"] = "直近週は横ばい傾向"
    elif trend_change > 0:
        analysis["trend"] = f"直近週は改善傾向（+{trend_change:.1f}人）"
    else:
        analysis["trend"] = f"直近週は減少傾向（{trend_change:.1f}人）"
    
    # 機会の特定（在院日数トレンドも考慮）
    admission_achievement = dept_kpi.get('weekly_admissions_achievement', 0)
    los_recent = dept_kpi.get('recent_week_avg_los', 0)
    los_avg = dept_kpi.get('avg_length_of_stay', 0)
    
    if admission_achievement >= 90:
        if los_recent < los_avg:
            analysis["opportunity"] = "新入院安定＋在院日数短縮で効率的運営"
        elif los_recent > los_avg:
            analysis["opportunity"] = "新入院は安定、在院日数の効率化余地あり"
        else:
            analysis["opportunity"] = "新入院数が安定、現状維持で良好"
    elif los_recent < los_avg - 0.5:  # 在院日数が大幅短縮
        analysis["opportunity"] = "在院日数効率化成功、新入院増加の余地あり"
    elif los_recent > los_avg + 0.5:  # 在院日数が大幅延長
        analysis["opportunity"] = "在院日数の適正化と新入院増加の両面改善必要"
    else:
        analysis["opportunity"] = "新入院増加と在院日数適正化の両面アプローチ"
    
    return analysis


def _generate_specific_action_items(action_type):
    """アクションタイプに応じた具体的な施策を生成"""
    if action_type == "新入院重視":
        return '''
        <li>
            <div class="priority">優先度: 高</div>
            救急外来との連携強化 - 新入院患者の確保
        </li>
        <li>
            <div class="priority">優先度: 中</div>
            地域医療機関への病診連携促進
        </li>
        <li>
            <div class="priority">優先度: 中</div>
            入院適応基準の見直し
        </li>
        '''
    elif action_type == "在院日数調整":
        return '''
        <li>
            <div class="priority">優先度: 高</div>
            退院調整カンファレンスの実施頻度UP
        </li>
        <li>
            <div class="priority">優先度: 中</div>
            在宅移行支援の強化
        </li>
        <li>
            <div class="priority">優先度: 中</div>
            クリニカルパスの最適化
        </li>
        '''
    elif action_type == "両方検討":
        return '''
        <li>
            <div class="priority">優先度: 高</div>
            救急外来との連携強化 - 新入院患者の確保
        </li>
        <li>
            <div class="priority">優先度: 高</div>
            退院調整カンファレンスの実施頻度UP
        </li>
        <li>
            <div class="priority">優先度: 中</div>
            多職種での改善チーム編成
        </li>
        '''
    else:
        return '''
        <li>
            <div class="priority">優先度: 中</div>
            現状の継続的監視
        </li>
        <li>
            <div class="priority">優先度: 低</div>
            予防的対策の検討
        </li>
        <li>
            <div class="priority">優先度: 低</div>
            ベストプラクティスの共有
        </li>
        '''

def generate_ward_mobile_report(kpi, df_filtered, period_desc, feasibility, simulation, hospital_targets):
    """病棟別モバイルレポートを生成する"""
    return _generate_common_mobile_report(kpi, df_filtered, kpi.get('ward_name', ''), period_desc, feasibility, simulation, hospital_targets, is_ward=True)

def generate_ward_metrics_html(ward_kpi):
    """病棟メトリクスカード生成（修正版）"""
    try:
        print(f"METRICS_DEBUG - ward_kpi keys: {list(ward_kpi.keys())}")
        
        # ✅ 修正：正しい変数名を使用
        avg_patients = ward_kpi.get('avg_patients', 0)
        target_patients = ward_kpi.get('target_patients', 0)
        achievement_rate = ward_kpi.get('achievement_rate', 0)
        bed_count = ward_kpi.get('bed_count', 0)
        bed_occupancy_rate = ward_kpi.get('bed_occupancy_rate', 0)
        
        print(f"METRICS_DEBUG - avg_patients: {avg_patients}")
        print(f"METRICS_DEBUG - target_patients: {target_patients}")
        print(f"METRICS_DEBUG - achievement_rate: {achievement_rate}")
        print(f"METRICS_DEBUG - bed_count: {bed_count}")
        print(f"METRICS_DEBUG - bed_occupancy_rate: {bed_occupancy_rate}")
        
        # 病床利用率評価
        if bed_occupancy_rate >= 98:
            occupancy_status = "高効率"
            occupancy_color = "#4CAF50"
        elif bed_occupancy_rate >= 90:
            occupancy_status = "適正"
            occupancy_color = "#2196F3"
        else:
            occupancy_status = "改善余地"
            occupancy_color = "#FF9800"
        
        # 目標達成状況
        achievement_status = "達成" if achievement_rate >= 100 else "未達成"
        
        # 総合評価計算（目標達成率50% + 病床利用率50%）
        achievement_score = min(achievement_rate, 100) * 0.5
        occupancy_score = min(bed_occupancy_rate, 100) * 0.5
        total_score = achievement_score + occupancy_score
        
        if total_score >= 90:
            total_status = "優秀"
            total_color = "#4CAF50"
        elif total_score >= 70:
            total_status = "良好"
            total_color = "#2196F3"
        elif total_score >= 50:
            total_status = "普通"
            total_color = "#FF9800"
        else:
            total_status = "要改善"
            total_color = "#F44336"
        
        return f"""
    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-icon">👥</div>
            <div class="metric-content">
                <div class="metric-label">日平均在院患者数</div>
                <div class="metric-value">{avg_patients:.1f}人</div>
                <div class="metric-target">目標: {target_patients:.1f}人</div>
            </div>
        </div>
        
        <div class="metric-card">
            <div class="metric-icon">🎯</div>
            <div class="metric-content">
                <div class="metric-label">目標達成率</div>
                <div class="metric-value">{achievement_rate:.1f}%</div>
                <div class="metric-status">{achievement_status}</div>
            </div>
        </div>

        <div class="metric-card">
            <div class="metric-icon">🏥</div>
            <div class="metric-content">
                <div class="metric-label">病床数・利用率</div>
                <div class="metric-value">{bed_count}床</div>
                <div class="metric-occupancy" style="color: {occupancy_color}">
                    {bed_occupancy_rate:.1f}% ({occupancy_status})
                </div>
            </div>
        </div>
        
        <div class="metric-card">
            <div class="metric-icon">⭐</div>
            <div class="metric-content">
                <div class="metric-label">総合評価</div>
                <div class="metric-value" style="color: {total_color}">{total_status}</div>
                <div class="metric-detail">目標達成+病床効率</div>
            </div>
        </div>
        </div>
        """
        
    except Exception as e:
        print(f"METRICS_ERROR - generate_ward_metrics_html: {str(e)}")
        return """
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="no-data">メトリクス読み込みエラー</div>
            </div>
        </div>
        """

def generate_ward_summary_html(ward_kpi):
    """病棟サマリー生成（修正版）"""
    try:
        # ✅ 修正：正しい変数名を使用
        achievement_rate = ward_kpi.get('achievement_rate', 0)
        bed_occupancy_rate = ward_kpi.get('bed_occupancy_rate', 0)
        
        # 病床利用率評価
        if bed_occupancy_rate >= 98:
            occupancy_status = "高効率"
            occupancy_color = "#4CAF50"
        elif bed_occupancy_rate >= 90:
            occupancy_status = "適正"
            occupancy_color = "#2196F3"
        else:
            occupancy_status = "改善余地"
            occupancy_color = "#FF9800"
        
        # 総合評価
        achievement_score = min(achievement_rate, 100) * 0.5
        occupancy_score = min(bed_occupancy_rate, 100) * 0.5
        total_score = achievement_score + occupancy_score
        
        if total_score >= 90:
            total_status = "優秀"
            total_color = "#4CAF50"
        elif total_score >= 70:
            total_status = "良好"
            total_color = "#2196F3"
        elif total_score >= 50:
            total_status = "普通"
            total_color = "#FF9800"
        else:
            total_status = "要改善"
            total_color = "#F44336"
        
        return f"""
    <section class="ward-summary">
        <h3>🎯 総合パフォーマンス</h3>
        <div class="ward-efficiency-badge" style="background-color: {total_color};">
            {total_status}
        </div>
        <div style="margin-top: 15px;">
            <div>目標達成率: <strong>{achievement_rate:.1f}%</strong></div>
    
            <div>病床利用率: <strong>{bed_occupancy_rate:.1f}% ({occupancy_status})</strong></div>
        
        </div>
    </section>
    """
        
    except Exception as e:
        print(f"SUMMARY_ERROR - generate_ward_summary_html: {str(e)}")
        return '<section class="ward-summary"><div class="no-data">サマリー読み込みエラー</div></section>'

def generate_ward_insights_html(ward_kpi):
    """病棟インサイト生成（修正版）"""
    try:
        # ✅ 修正：正しい変数名を使用
        achievement_rate = ward_kpi.get('achievement_rate', 0)
        bed_occupancy_rate = ward_kpi.get('bed_occupancy_rate', 0)
        
        insights = []
        
        # 目標達成に関するインサイト
        if achievement_rate < 100:
            gap = 100 - achievement_rate
            insights.append(f"📊 目標まで{gap:.1f}%の改善余地があります")
        
        # 病床利用率に関するインサイト
        if bed_occupancy_rate < 90:
            insights.append("📈 病床利用率に改善の余地があります")
        elif bed_occupancy_rate > 98:
            insights.append("⚠️ 病床利用率が非常に高く、患者受け入れに注意が必要です")
        
        # 総合的なインサイト
        if achievement_rate < 100 and bed_occupancy_rate < 90:
            insights.append("🔧 目標達成率と病床利用率の両面で改善が必要です")
        elif achievement_rate >= 100 and bed_occupancy_rate >= 90:
            insights.append("🎉 目標達成と効率的な病床運用を両立しています")
        
        # インサイトがない場合のデフォルト
        if not insights:
            insights.append("✨ 安定したパフォーマンスを維持しています")
        
        insights_html = "".join([f'<div class="insight-item">{insight}</div>' for insight in insights])
        
        return f"""
                <section class="insights-section">
                    <h3>💡 分析ポイント</h3>
                    <div class="insights-list">{insights_html}</div>
                </section>
        """
        
    except Exception as e:
        print(f"INSIGHTS_ERROR - generate_ward_insights_html: {str(e)}")
        return '<section class="insights-section"><div class="no-data">インサイト読み込みエラー</div></section>'
        
def generate_ward_trend_chart(df_ward_filtered: pd.DataFrame, ward_name: str) -> str:
    """
    病棟の患者数推移チャートHTML生成
    
    Args:
        df_ward_filtered: 病棟フィルタ済みデータ
        ward_name: 病棟名
        
    Returns:
        チャートHTML
    """
    if df_ward_filtered.empty:
        return '<div class="no-data">データが見つかりません</div>'
    
    # 日付別患者数の集計
    if '入院日' in df_ward_filtered.columns:
        daily_counts = df_ward_filtered.groupby('入院日').size().reset_index(name='患者数')
        
        # 簡易的なテキストベースのチャート（実際の実装ではChart.jsなどを使用）
        chart_html = '<div class="trend-chart">'
        chart_html += '<div class="chart-title">日別患者数推移</div>'
        
        # 最新5日間のデータ表示
        recent_data = daily_counts.tail(5)
        for _, row in recent_data.iterrows():
            date_str = row['入院日'].strftime('%m/%d') if hasattr(row['入院日'], 'strftime') else str(row['入院日'])
            count = row['患者数']
            
            # バーの長さ（最大値を100%として正規化）
            max_count = recent_data['患者数'].max()
            bar_width = (count / max_count) * 100 if max_count > 0 else 0
            
            chart_html += f'''
            <div class="chart-bar">
                <div class="chart-date">{date_str}</div>
                <div class="chart-bar-container">
                    <div class="chart-bar-fill" style="width: {bar_width}%"></div>
                </div>
                <div class="chart-value">{count}人</div>
            </div>
            '''
        
        chart_html += '</div>'
        return chart_html
    
    return '<div class="no-data">チャートデータの準備中</div>'

def generate_ward_performance_summary(enhanced_ward_kpi: Dict[str, Any]) -> str:
    """
    病棟パフォーマンスサマリー生成
    
    Args:
        enhanced_ward_kpi: 病床メトリクス含む病棟KPI
        
    Returns:
        サマリーHTML
    """
    ward_effort_level = enhanced_ward_kpi.get('ward_effort_level', '評価中')
    ward_effort_color = enhanced_ward_kpi.get('ward_effort_color', '#666')
    achievement_rate = enhanced_ward_kpi.get('achievement_rate', 0)
    bed_occupancy_rate = enhanced_ward_kpi.get('bed_occupancy_rate')
    occupancy_status = enhanced_ward_kpi.get('occupancy_status', '')
    
    summary_html = f'''
    <section class="ward-summary">
        <h3>🎯 総合パフォーマンス</h3>
        <div class="ward-efficiency-badge" style="background-color: {ward_effort_color};">
            {ward_effort_level}
        </div>
        <div style="margin-top: 15px;">
            <div>目標達成率: <strong>{achievement_rate:.1f}%</strong></div>
    '''
    
    if bed_occupancy_rate is not None:
        summary_html += f'''
            <div>病床利用率: <strong>{bed_occupancy_rate:.1f}% ({occupancy_status})</strong></div>
        '''
    
    summary_html += '''
        </div>
    </section>
    '''
    
    return summary_html

def generate_ward_insights(enhanced_ward_kpi: Dict[str, Any]) -> str:
    """
    病棟分析ポイント生成
    
    Args:
        enhanced_ward_kpi: 病床メトリクス含む病棟KPI
        
    Returns:
        分析ポイントHTML
    """
    insights = []
    
    achievement_rate = enhanced_ward_kpi.get('achievement_rate', 0)
    bed_occupancy_rate = enhanced_ward_kpi.get('bed_occupancy_rate')
    occupancy_status = enhanced_ward_kpi.get('occupancy_status', '')
    
    # 目標達成分析
    if achievement_rate >= 100:
        insights.append("✅ 日平均在院患者数の目標を達成しています")
    else:
        shortfall = 100 - achievement_rate
        insights.append(f"📊 目標まで{shortfall:.1f}%の改善余地があります")
    
    # 病床利用率分析
    if bed_occupancy_rate is not None:
        if occupancy_status == "高効率":
            insights.append("🏆 病床利用率が非常に高く、効率的な運営ができています")
        elif occupancy_status == "適正":
            insights.append("✅ 病床利用率は適正な範囲内です")
        else:
            insights.append("📈 病床利用率に改善の余地があります")
    
    # 複合分析
    ward_effort_level = enhanced_ward_kpi.get('ward_effort_level', '')
    if ward_effort_level == "優秀":
        insights.append("🌟 目標達成と病床効率の両面で優秀な成績です")
    elif ward_effort_level == "要改善":
        insights.append("🔧 目標達成率と病床利用率の両面で改善が必要です")
    
    # HTML構築
    insights_html = '<div class="insights-list">'
    for insight in insights:
        insights_html += f'<div class="insight-item">{insight}</div>'
    insights_html += '</div>'
    
    return insights_html

def get_base_mobile_css_styles() -> str:
    """
    モバイルレポート基本CSSスタイル
    ※ 既存のget_mobile_css_styles()関数を想定
    
    Returns:
        基本CSS文字列
    """
    return """
    /* 基本スタイル */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        line-height: 1.6;
        color: #333;
        background-color: #f5f5f5;
    }
    
    .container {
        max-width: 480px;
        margin: 0 auto;
        padding: 10px;
        background: white;
        min-height: 100vh;
    }
    
    .header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 20px;
        text-align: center;
    }
    
    .header h1 {
        font-size: 1.5em;
        margin-bottom: 8px;
    }
    
    .subtitle {
        font-size: 0.9em;
        opacity: 0.9;
        margin-bottom: 4px;
    }
    
    .period {
        font-size: 0.8em;
        opacity: 0.8;
    }
    
    .ward-code {
        font-size: 0.8em;
        opacity: 0.7;
        margin-top: 8px;
    }
    
    .metrics-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-bottom: 20px;
    }
    
    .metric-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-icon {
        font-size: 1.5em;
        margin-bottom: 8px;
    }
    
    .metric-label {
        font-size: 0.8em;
        color: #666;
        margin-bottom: 4px;
    }
    
    .metric-value {
        font-size: 1.2em;
        font-weight: bold;
        color: #333;
    }
    
    .metric-target, .metric-status {
        font-size: 0.8em;
        color: #888;
        margin-top: 4px;
    }
    
    .chart-section, .insights-section {
        background: white;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .chart-section h3, .insights-section h3 {
        margin-bottom: 15px;
        color: #333;
        font-size: 1.1em;
    }
    
    .trend-chart {
        margin-top: 10px;
    }
    
    .chart-title {
        font-weight: bold;
        margin-bottom: 10px;
        color: #666;
    }
    
    .chart-bar {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
        font-size: 0.9em;
    }
    
    .chart-date {
        width: 40px;
        font-size: 0.8em;
        color: #666;
    }
    
    .chart-bar-container {
        flex: 1;
        height: 20px;
        background-color: #f0f0f0;
        margin: 0 10px;
        border-radius: 10px;
        overflow: hidden;
    }
    
    .chart-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #4CAF50, #45a049);
        transition: width 0.3s ease;
    }
    
    .chart-value {
        width: 40px;
        text-align: right;
        font-weight: bold;
        color: #333;
    }
    
    .insights-list {
        space-y: 10px;
    }
    
    .insight-item {
        padding: 10px;
        background-color: #f8f9fa;
        border-left: 4px solid #007bff;
        border-radius: 4px;
        margin-bottom: 8px;
        font-size: 0.9em;
    }
    
    .no-data {
        text-align: center;
        color: #888;
        padding: 20px;
        font-style: italic;
    }
    
    .footer {
        text-align: center;
        padding: 20px;
        border-top: 1px solid #e0e0e0;
        margin-top: 20px;
    }
    
    .update-time {
        font-size: 0.8em;
        color: #666;
        margin-bottom: 10px;
    }
    
    .back-link {
        display: inline-block;
        padding: 10px 20px;
        background-color: #007bff;
        color: white;
        text-decoration: none;
        border-radius: 6px;
        font-size: 0.9em;
    }
    
    .back-link:hover {
        background-color: #0056b3;
    }
    """

def _get_mobile_optimized_css():
    """モバイル最適化されたCSSを返す"""
    return '''
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans JP', sans-serif;
            background: #f5f7fa; 
            color: #333;
            line-height: 1.6;
        }
        
        /* ヘッダー */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 16px;
            text-align: center;
        }
        .header h1 { font-size: 1.4em; margin-bottom: 4px; }
        .header p { font-size: 0.9em; opacity: 0.9; }
        
        /* コンテナ */
        .container { 
            max-width: 100%;
            padding: 16px;
            margin-bottom: 60px;
        }
        
        /* サマリーカード */
        .summary-cards {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 20px;
        }
        .summary-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .summary-card:active {
            transform: scale(0.98);
        }
        .summary-card h3 {
            font-size: 0.85em;
            color: #666;
            margin-bottom: 8px;
        }
        .summary-card .value {
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 4px;
        }
        .summary-card .target {
            font-size: 0.8em;
            color: #999;
        }
        
        /* 色分け */
        .card-good .value { color: #4CAF50; }
        .card-warning .value { color: #FF9800; }
        .card-danger .value { color: #F44336; }
        .card-info .value { color: #2196F3; }
        
        /* セクション */
        .section {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: #667eea;
            font-size: 1.1em;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid #f0f0f0;
        }
        .section h3 {
            color: #4a5568;
            font-size: 1em;
            margin-top: 16px;
            margin-bottom: 12px;
        }
        
        /* グラフコンテナ */
        .chart-container {
            margin-bottom: 20px;
            border-radius: 8px;
            overflow: hidden;
        }
        .chart-placeholder {
            background: #f8f9fa;
            border: 2px dashed #dee2e6;
            border-radius: 8px;
            min-height: 200px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: #6c757d;
            font-size: 0.9em;
            margin-bottom: 12px;
            padding: 20px;
            text-align: center;
        }
        
        /* アクションリスト */
        .action-list {
            list-style: none;
            margin: 0;
        }
        .action-list li {
            background: #f8f9fa;
            margin-bottom: 8px;
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            font-size: 0.9em;
        }
        .action-list .priority {
            color: #667eea;
            font-weight: bold;
            font-size: 0.8em;
            margin-bottom: 4px;
        }
        
        /* トレンドインジケーター */
        .trend {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 0.8em;
            padding: 2px 6px;
            border-radius: 4px;
            margin-top: 4px;
        }
        .trend-up { background: #fff3cd; color: #856404; }
        .trend-down { background: #d1ecf1; color: #0c5460; }
        .trend-stable { background: #d4edda; color: #155724; }
        
        /* フローティングボタン */
        .fab {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 56px;
            height: 56px;
            background: #667eea;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            text-decoration: none;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            font-size: 1.5em;
            transition: all 0.3s;
        }
        .fab:hover {
            transform: scale(1.1);
            background: #764ba2;
        }
        
        /* レスポンシブ対応 */
        @media (max-width: 480px) {
            .header h1 { font-size: 1.2em; }
            .summary-card .value { font-size: 1.5em; }
            .section { padding: 16px; }
        }
        
        /* 印刷対応 */
        @media print {
            .fab { display: none; }
            .header { position: static; }
            body { background: white; }
        }
    '''


def _generate_error_html(dept_name, error_message):
    """エラー時のHTML生成"""
    return f'''
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>エラー - {dept_name}</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; background: #f5f5f5; }}
            .error {{ background: white; padding: 30px; border-radius: 10px; text-align: center; }}
            h1 {{ color: #F44336; }}
        </style>
    </head>
    <body>
        <div class="error">
            <h1>データエラー</h1>
            <p>{dept_name}のレポート生成に失敗しました。</p>
            <p>エラー: {error_message}</p>
        </div>
    </body>
    </html>
    '''
    
def _get_css_styles():
    """レポート用の共通CSSを返す"""
    return CSSStyles.get_mobile_report_styles()

def _get_legacy_mobile_css():
    """レガシー版モバイルCSS（移行期間中のフォールバック）"""
    return """
    /* 基本的なフォールバックCSS */
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: sans-serif; background: #f5f5f5; }
    .container { padding: 16px; }
    .header { background: #667eea; color: white; padding: 20px; border-radius: 12px; }
    .summary-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    .summary-card { background: white; padding: 16px; border-radius: 12px; }
    """

def _generate_charts_html(df_filtered, kpi):
    """チャート部分のHTMLを生成する"""
    # (前回から変更なし)
    try:
        from chart import create_interactive_patient_chart, create_interactive_alos_chart, create_interactive_dual_axis_chart
        
        target_value = kpi.get('target_patients')

        fig_patient = create_interactive_patient_chart(df_filtered, title="", days=90, target_value=target_value)
        fig_alos = create_interactive_alos_chart(df_filtered, title="", days_to_show=90)
        fig_dual = create_interactive_dual_axis_chart(df_filtered, title="", days=90)
        
        return f"""
        <div class="section">
            <h2>📊 90日間トレンド</h2>
            <h3>在院患者数推移</h3>
            <div class="chart-container">{fig_patient.to_html(full_html=False, include_plotlyjs='cdn') if fig_patient else ""}</div>
            <h3>平均在院日数推移</h3>
            <div class="chart-container">{fig_alos.to_html(full_html=False, include_plotlyjs=False) if fig_alos else ""}</div>
            <h3>新入院・退院数推移</h3>
            <div class="chart-container">{fig_dual.to_html(full_html=False, include_plotlyjs=False) if fig_dual else ""}</div>
        </div>
        """
    except Exception as e:
        logger.error(f"チャートHTML生成エラー: {e}")
        return '<div class="section"><h2>📊 90日間トレンド</h2><p>チャート生成中にエラーが発生しました。</p></div>'

def _generate_action_plan_html(kpi, feasibility, simulation, hospital_targets):
    """
    アクションプランのHTMLを生成する（直近週重視版）
    
    修正内容：
    - 直近週の実績を重視した評価軸に変更
    - 在院患者数の目標達成をエンドポイントとする判定ロジック
    - 直近週 vs 目標、直近週 vs 期間平均の両面で評価
    """
    try:
        # ===== 直近週重視のKPIデータ取得 =====
        # 在院患者数関連（直近週重視）
        period_avg_census = kpi.get('daily_avg_census', 0)  # 期間平均
        recent_week_census = kpi.get('recent_week_daily_census', 0)  # 直近週実績
        census_target = kpi.get('daily_census_target', 0)  # 目標値
        
        # 新入院関連（直近週重視）
        period_avg_admissions = kpi.get('weekly_avg_admissions', 0)  # 期間平均（週間）
        recent_week_admissions = kpi.get('recent_week_admissions', 0)  # 直近週実績
        admissions_target = kpi.get('weekly_admissions_target', 0)  # 新入院目標値
        
        # ===== 直近週ベースの達成率計算 =====
        # 🎯 在院患者数：直近週実績 vs 目標
        recent_census_achievement = (recent_week_census / census_target * 100) if census_target and census_target > 0 else 0
        
        # 🎯 新入院：直近週実績 vs 目標  
        recent_admissions_achievement = (recent_week_admissions / admissions_target * 100) if admissions_target and admissions_target > 0 else 0
        
        # ===== 直近週 vs 期間平均の変化率計算 =====
        # 在院患者数の変化
        census_change_rate = ((recent_week_census - period_avg_census) / period_avg_census * 100) if period_avg_census and period_avg_census > 0 else 0
        
        # 新入院の変化  
        admissions_change_rate = ((recent_week_admissions - period_avg_admissions) / period_avg_admissions * 100) if period_avg_admissions and period_avg_admissions > 0 else 0
        
        # ===== 直近週重視のアクション判定ロジック =====
        action_plan = _decide_action_based_on_recent_week(
            recent_census_achievement, 
            recent_admissions_achievement,
            census_change_rate,
            admissions_change_rate,
            recent_week_census,
            census_target
        )
        
        # ===== 具体的アクション項目の生成 =====
        action_items = _generate_recent_week_action_items(
            action_plan['action_type'], 
            recent_census_achievement,
            recent_admissions_achievement,
            census_change_rate
        )
        
        # ===== 直近週状況の詳細分析 =====
        recent_week_analysis = _analyze_recent_week_status(
            recent_week_census, census_target, recent_census_achievement,
            recent_week_admissions, admissions_target, recent_admissions_achievement,
            census_change_rate, admissions_change_rate
        )
        
        # ===== 期待効果シミュレーション（直近週ベース） =====
        effect_html = ""
        if simulation and 'admission_scenario' in simulation:
            admission_effect = simulation['admission_scenario'].get('effect', 0)
            los_effect = simulation['los_scenario'].get('effect', 0) 
            census_gap = (census_target - recent_week_census) if (census_target and census_target > 0) else 0
            
            effect_html = f"""
            <div class="effect-summary">
                <h3>📊 直近週ベース効果予測</h3>
                <div class="effect-grid">
                    <div class="effect-item">
                        <div class="effect-label">新入院週1人増加</div>
                        <div class="effect-value">+{admission_effect:.1f}人</div>
                    </div>
                    <div class="effect-item">
                        <div class="effect-label">在院日数1日延長</div>
                        <div class="effect-value">+{los_effect:.1f}人</div>
                    </div>
                    <div class="effect-item">
                        <div class="effect-label">目標までの差</div>
                        <div class="effect-value">{census_gap:.1f}人</div>
                    </div>
                </div>
            </div>
            """
        
        # ===== 最終HTML組み立て =====
        return f"""
        <div class="section">
            <h2>🎯 今週のアクションプラン（直近週重視）</h2>
            
            <!-- 直近週の状況サマリー -->
            <div class="recent-week-summary">
                <h3>📈 直近週の実績評価</h3>
                <div class="analysis-grid">
                    <div class="analysis-item">
                        <h4>🏥 在院患者数</h4>
                        <p><strong>実績:</strong> {recent_week_census:.1f}人 / 目標: {census_target or '--'}人</p>
                        <p><strong>達成率:</strong> {recent_census_achievement:.1f}% {_get_achievement_status_icon(recent_census_achievement)}</p>
                        <p><strong>期間平均比:</strong> {census_change_rate:+.1f}% {_get_trend_icon(census_change_rate)}</p>
                    </div>
                    <div class="analysis-item">
                        <h4>🚑 週間新入院</h4>
                        <p><strong>実績:</strong> {recent_week_admissions:.1f}人 / 目標: {admissions_target or '--'}人</p>
                        <p><strong>達成率:</strong> {recent_admissions_achievement:.1f}% {_get_achievement_status_icon(recent_admissions_achievement)}</p>
                        <p><strong>期間平均比:</strong> {admissions_change_rate:+.1f}% {_get_trend_icon(admissions_change_rate)}</p>
                    </div>
                </div>
            </div>
            
            <!-- アクション戦略 -->
            <div class="action-strategy">
                <div class="action-summary" style="border-left-color: {action_plan['color']};">
                    <strong>{action_plan['priority_icon']} {action_plan['action_type']}</strong>
                    <p>{action_plan['reasoning']}</p>
                </div>
                
                <h3>🔧 推奨アクション</h3>
                <ul class="action-list-enhanced">
                    {action_items}
                </ul>
            </div>
            
            <!-- 重点監視指標 -->
            <div class="monitoring-focus">
                <h3>👀 重点監視指標（直近週）</h3>
                <div class="monitoring-items">
                    <div class="monitor-item priority-high">
                        <span class="monitor-label">在院患者数達成率</span>
                        <span class="monitor-value">{recent_census_achievement:.1f}%</span>
                        <span class="monitor-status">{'✅ 達成' if recent_census_achievement >= 98 else '📈 要改善'}</span>
                    </div>
                    <div class="monitor-item priority-medium">
                        <span class="monitor-label">新入院達成率</span>
                        <span class="monitor-value">{recent_admissions_achievement:.1f}%</span>
                        <span class="monitor-status">{'✅ 達成' if recent_admissions_achievement >= 98 else '📈 要改善'}</span>
                    </div>
                </div>
            </div>
            
            {effect_html}
        </div>
        """
        
    except Exception as e:
        logger.error(f"直近週重視アクションプランHTML生成エラー: {e}", exc_info=True)
        return '<div class="section"><h2>🎯 アクションプラン</h2><p>アクションプランの生成中にエラーが発生しました。</p></div>'


def _decide_action_based_on_recent_week(recent_census_achievement, recent_admissions_achievement, 
                                       census_change_rate, admissions_change_rate, recent_census, census_target):
    """
    直近週の実績に基づくアクション判定（98%基準版）
    
    判定基準：
    1. 在院患者数の直近週達成率を最重要視
    2. 新入院の直近週達成率を次に重要視  
    3. 期間平均からの変化傾向も考慮
    """
    
    # エンドポイント：在院患者数の目標達成
    if recent_census_achievement >= 98:
        # 🎯 目標達成時
        if census_change_rate >= 5:
            return {
                'action_type': '現状維持・拡大',
                'reasoning': f'直近週で目標達成率{recent_census_achievement:.1f}%＋改善傾向。この調子で継続',
                'priority_icon': '✨',
                'color': '#4CAF50'
            }
        else:
            return {
                'action_type': '現状維持',
                'reasoning': f'直近週で目標達成率{recent_census_achievement:.1f}%。安定した状況を継続',
                'priority_icon': '✅',
                'color': '#7fb069'
            }
    
    elif recent_census_achievement >= 90:
        # 🔶 中間レベル（90-98%）：新入院達成状況で判断
        if recent_admissions_achievement < 98:
            return {
                'action_type': '新入院重視',
                'reasoning': f'直近週：在院{recent_census_achievement:.1f}%、新入院{recent_admissions_achievement:.1f}%。新入院増加を優先',
                'priority_icon': '🚑',
                'color': '#2196F3'
            }
        else:
            return {
                'action_type': '在院日数調整',
                'reasoning': f'直近週：新入院は達成済み（{recent_admissions_achievement:.1f}%）、在院日数の適正化で目標達成へ',
                'priority_icon': '📊',
                'color': '#FF9800'
            }
    
    else:
        # 🚨 緊急レベル（90%未満）
        gap = (census_target - recent_census) if (census_target and census_target > 0) else 0
        return {
            'action_type': '緊急対応',
            'reasoning': f'直近週の達成率{recent_census_achievement:.1f}%と大幅不足。新入院増加と在院日数調整の両面対応が必要',
            'priority_icon': '🚨',
            'color': '#F44336'
        }


def _generate_recent_week_action_items(action_type, recent_census_achievement, recent_admissions_achievement, census_change_rate):
    """直近週の状況に応じた具体的アクション項目生成"""
    
    if action_type == '新入院重視':
        return """
        <li>
            <div class="action-icon">🚑</div>
            <div class="action-content">
                <strong>緊急・救急患者の積極的受け入れ</strong>
                <p>直近週の新入院実績を踏まえ、救急外来との連携を強化し受け入れ体制を整備</p>
            </div>
        </li>
        <li>
            <div class="action-icon">🏥</div>
            <div class="action-content">
                <strong>地域連携による紹介患者増加</strong>
                <p>診療所・クリニックからの紹介患者受け入れを積極的に推進</p>
            </div>
        </li>
        <li>
            <div class="action-icon">📞</div>
            <div class="action-content">
                <strong>入院適応基準の見直し</strong>
                <p>直近週の入院状況を分析し、入院適応患者の取りこぼしがないか確認</p>
            </div>
        </li>
        """
    
    elif action_type == '在院日数調整':
        return """
        <li>
            <div class="action-icon">👥</div>
            <div class="action-content">
                <strong>退院調整会議の頻度増加</strong>
                <p>直近週の在院日数実績を踏まえ、多職種カンファレンスを週2回以上実施</p>
            </div>
        </li>
        <li>
            <div class="action-icon">📋</div>
            <div class="action-content">
                <strong>クリニカルパスの最適化</strong>
                <p>主要疾患の治療期間を見直し、効率的な診療計画を策定</p>
            </div>
        </li>
        <li>
            <div class="action-icon">🏠</div>
            <div class="action-content">
                <strong>在宅移行支援の強化</strong>
                <p>在宅医療・訪問看護との連携を深め、適切なタイミングでの退院を促進</p>
            </div>
        </li>
        """
    
    elif action_type == '緊急対応':
        return """
        <li>
            <div class="action-icon">🎯</div>
            <div class="action-content">
                <strong>緊急改善チーム設置</strong>
                <p>医師・看護師・MSW等で緊急対策チームを組織し、日々の状況をモニタリング</p>
            </div>
        </li>
        <li>
            <div class="action-icon">📈</div>
            <div class="action-content">
                <strong>新入院・在院日数の同時対策</strong>
                <p>新入院患者確保と在院日数適正化を並行して実施</p>
            </div>
        </li>
        <li>
            <div class="action-icon">📊</div>
            <div class="action-content">
                <strong>日次進捗管理</strong>
                <p>目標達成に向けて日単位での進捗確認と対策調整を実施</p>
            </div>
        </li>
        """
    
    else:  # 現状維持・拡大
        return """
        <li>
            <div class="action-icon">✅</div>
            <div class="action-content">
                <strong>成功パターンの継続</strong>
                <p>直近週の良好な実績を維持するため、現在の運営方法を継続</p>
            </div>
        </li>
        <li>
            <div class="action-icon">📚</div>
            <div class="action-content">
                <strong>ベストプラクティス共有</strong>
                <p>成功事例を他部署と共有し、病院全体の改善に貢献</p>
            </div>
        </li>
        <li>
            <div class="action-icon">🔍</div>
            <div class="action-content">
                <strong>さらなる改善余地の検討</strong>
                <p>現状の良好な状態からさらに向上できる要素がないか検討</p>
            </div>
        </li>
        """


def _analyze_recent_week_status(recent_census, census_target, recent_census_achievement,
                               recent_admissions, admissions_target, recent_admissions_achievement,
                               census_change_rate, admissions_change_rate):
    """直近週の状況を詳細分析"""
    
    analysis = {
        'census_status': '',
        'admissions_status': '',
        'trend_analysis': '',
        'priority_focus': ''
    }
    
    # 在院患者数の状況
    if recent_census_achievement >= 98:
        analysis['census_status'] = f"✅ 目標達成（{recent_census_achievement:.1f}%）"
    elif recent_census_achievement >= 90:
        analysis['census_status'] = f"📊 あと少し（{recent_census_achievement:.1f}%）"
    else:
        analysis['census_status'] = f"🚨 要改善（{recent_census_achievement:.1f}%）"
    
    # 新入院の状況
    if recent_admissions_achievement >= 98:
        analysis['admissions_status'] = f"✅ 目標達成（{recent_admissions_achievement:.1f}%）"
    elif recent_admissions_achievement >= 90:
        analysis['admissions_status'] = f"📊 概ね良好（{recent_admissions_achievement:.1f}%）"
    else:
        analysis['admissions_status'] = f"📈 要改善（{recent_admissions_achievement:.1f}%）"
    
    # トレンド分析
    if census_change_rate >= 5:
        analysis['trend_analysis'] = f"📈 改善傾向（期間平均比+{census_change_rate:.1f}%）"
    elif census_change_rate <= -5:
        analysis['trend_analysis'] = f"📉 悪化傾向（期間平均比{census_change_rate:.1f}%）"
    else:
        analysis['trend_analysis'] = f"➡️ 横ばい（期間平均比{census_change_rate:+.1f}%）"
    
    # 重点取り組み領域
    if recent_census_achievement < 90:
        analysis['priority_focus'] = "🚨 在院患者数の緊急対策が最優先"
    elif recent_census_achievement < 98 and recent_admissions_achievement < 98:
        analysis['priority_focus'] = "⚖️ 新入院と在院日数のバランス調整"
    elif recent_census_achievement < 98:
        analysis['priority_focus'] = "🎯 在院日数の適正化で目標達成へ"
    else:
        analysis['priority_focus'] = "✨ 現状維持と更なる向上"
    
    return analysis


def _get_achievement_status_icon(achievement_rate):
    """達成率に応じたアイコン返却"""
    if achievement_rate >= 98:
        return "✅"
    elif achievement_rate >= 90:
        return "📊"
    elif achievement_rate >= 80:
        return "📈"
    else:
        return "🚨"


def _get_trend_icon(change_rate):
    """変化率に応じたトレンドアイコン返却"""
    if change_rate >= 5:
        return "🔥"
    elif change_rate >= 0:
        return "📈"
    elif change_rate >= -5:
        return "➡️"
    else:
        return "📉"

def _adapt_kpi_for_html_generation(raw_kpi: dict) -> dict:
    """KPIデータをHTML生成用に変換（新入院目標値追加版）"""
    if not raw_kpi: 
        return {}
    
    adapted_kpi = raw_kpi.copy()
    
    # 在院患者数関連
    adapted_kpi['avg_patients'] = raw_kpi.get('daily_avg_census', 0)
    adapted_kpi['target_patients'] = raw_kpi.get('daily_census_target')
    adapted_kpi['achievement_rate'] = raw_kpi.get('recent_week_census_achievement', 0) # 変更箇所
    
    # 週間新入院目標値を追加（これが重要！）
    adapted_kpi['target_admissions'] = raw_kpi.get('weekly_admissions_target', 0)
    
    return adapted_kpi