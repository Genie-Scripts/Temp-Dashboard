# enhanced_action_analysis.py - 詳細アクション分析データ生成（目標達成努力度版）

import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_comprehensive_action_data(kpi, feasibility, simulation, hospital_targets):
    """
    HTMLエクスポート版と同等の詳細アクション分析データを生成（目標達成努力度版）
    
    Args:
        kpi: KPI辞書
        feasibility: 実現可能性評価辞書
        simulation: シミュレーション結果辞書
        hospital_targets: 病院全体目標辞書
    
    Returns:
        dict: 詳細分析データ
    """
    try:
        # 基本情報の取得
        dept_name = kpi.get('dept_name', kpi.get('ward_name', 'Unknown'))
        current_census = kpi.get('daily_avg_census', 0)
        census_target = kpi.get('daily_census_target', 0)
        census_achievement = kpi.get('daily_census_achievement', 0)
        recent_week_census = kpi.get('recent_week_daily_census', 0)
        
        admission_avg = kpi.get('weekly_avg_admissions', 0) / 7
        admission_recent = kpi.get('recent_week_admissions', 0) / 7
        
        los_avg = kpi.get('avg_length_of_stay', 0)
        los_recent = kpi.get('recent_week_avg_los', 0)
        
        # 1. 目標達成努力度計算（病院貢献度の代替）
        effort_evaluation = _calculate_effort_status(
            current_census, recent_week_census, census_achievement
        )
        
        # 2. 現状分析
        census_gap = current_census - (census_target or 0)
        census_status = "✅" if census_achievement >= 95 else "❌"
        
        # トレンド分析
        if admission_recent > admission_avg * 1.03:
            admission_trend = "↗️増加"
        elif admission_recent < admission_avg * 0.97:
            admission_trend = "↘️減少"
        else:
            admission_trend = "➡️安定"
        
        # 在院日数の適正範囲チェック
        los_range = feasibility.get('los_range') if feasibility else None
        if los_range and los_recent > 0:
            if los_range["lower"] <= los_recent <= los_range["upper"]:
                los_status = "✅"
                los_assessment = "適正範囲内"
            elif los_recent > los_range["upper"]:
                los_status = "⚠️"
                los_assessment = "長期化傾向"
            else:
                los_status = "📉"
                los_assessment = "短期化傾向"
        else:
            los_status = "❓"
            los_assessment = "評価困難"
        
        # 3. 実現可能性評価
        admission_feas = feasibility.get('admission', {}) if feasibility else {}
        los_feas = feasibility.get('los', {}) if feasibility else {}
        
        admission_feas_score = sum(admission_feas.values())
        los_feas_score = sum(los_feas.values())
        
        # 4. 簡素化された効果シミュレーション
        simple_simulation = _calculate_simple_effect_simulation(kpi)
        
        # 5. 基本アクション決定（従来のロジック）
        basic_action = _decide_basic_action(kpi, feasibility, simulation)
        
        # 6. 期待効果計算
        expected_effect = _calculate_expected_effect(
            census_gap, hospital_targets, current_census
        )
        
        # 7. 総合データ構造
        comprehensive_data = {
            'basic_info': {
                'dept_name': dept_name,
                'current_census': current_census,
                'census_target': census_target,
                'census_achievement': census_achievement,
                'recent_week_census': recent_week_census,
                'admission_avg': admission_avg,
                'admission_recent': admission_recent,
                'los_avg': los_avg,
                'los_recent': los_recent
            },
            'effort_status': effort_evaluation,  # 新規：目標達成努力度
            'current_analysis': {
                'census_gap': census_gap,
                'census_status': census_status,
                'admission_trend': admission_trend,
                'los_status': los_status,
                'los_assessment': los_assessment,
                'los_range': los_range
            },
            'feasibility_evaluation': {
                'admission_feasibility': {
                    'score': admission_feas_score,
                    'details': admission_feas,
                    'assessment': _assess_feasibility(admission_feas_score)
                },
                'los_feasibility': {
                    'score': los_feas_score,
                    'details': los_feas,
                    'assessment': _assess_feasibility(los_feas_score)
                }
            },
            'effect_simulation': simple_simulation,  # 修正：簡素化版
            'basic_action': basic_action,
            'expected_effect': expected_effect,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return comprehensive_data
        
    except Exception as e:
        logger.error(f"詳細アクション分析データ生成エラー ({dept_name}): {e}", exc_info=True)
        return None

def _calculate_effort_status(current_census, recent_week_census, census_achievement):
    """目標達成努力度を計算"""
    try:
        trend_change = recent_week_census - current_census
        
        if census_achievement >= 100:
            if trend_change > 0:
                return {
                    'status': "✨目標突破中",
                    'level': "優秀", 
                    'emoji': "✨",
                    'description': f"目標達成＋さらに改善中（+{trend_change:.1f}人）",
                    'color': "#4CAF50"
                }
            else:
                return {
                    'status': "🎯達成継続",
                    'level': "良好",
                    'emoji': "🎯", 
                    'description': "目標達成を継続中",
                    'color': "#7fb069"
                }
        elif census_achievement >= 85:
            if trend_change > 0:
                return {
                    'status': "💪追い上げ中",
                    'level': "改善",
                    'emoji': "💪",
                    'description': f"目標まであと少し！改善中（+{trend_change:.1f}人）",
                    'color': "#FF9800"
                }
            else:
                return {
                    'status': "📈要努力", 
                    'level': "注意",
                    'emoji': "📈",
                    'description': "目標まであと少し、さらなる努力を",
                    'color': "#FFC107"
                }
        else:
            return {
                'status': "🚨要改善",
                'level': "要改善",
                'emoji': "🚨", 
                'description': "目標達成に向けた積極的な取り組みが必要",
                'color': "#F44336"
            }
    except Exception as e:
        logger.error(f"努力度計算エラー: {e}")
        return {
            'status': "❓評価困難",
            'level': "不明",
            'emoji': "❓",
            'description': "データ不足のため評価困難",
            'color': "#9E9E9E"
        }

def _calculate_simple_effect_simulation(kpi):
    """効果シミュレーション（簡素化版）"""
    try:
        # 現在の値を取得
        weekly_admissions = kpi.get('weekly_avg_admissions', 0)
        daily_admissions = weekly_admissions / 7
        current_los = kpi.get('avg_length_of_stay', 0)
        current_census = kpi.get('daily_avg_census', 0)
        
        # 現在の計算値
        theoretical_census = daily_admissions * current_los
        
        # シナリオ1：新入院を週に1人増やした場合
        new_daily_admissions_1 = daily_admissions + 1/7
        new_census_1 = new_daily_admissions_1 * current_los
        admission_effect = new_census_1 - theoretical_census
        
        # シナリオ2：平均在院日数を1日延ばした場合  
        new_los_2 = current_los + 1
        new_census_2 = daily_admissions * new_los_2
        los_effect = new_census_2 - theoretical_census
        
        # 実績との差異計算
        variance = current_census - theoretical_census
        
        return {
            'admission_scenario': {
                'description': "新入院を週に1人増やすと",
                'effect': admission_effect,
                'unit': "人の日平均在院患者数増加",
                'simple': True
            },
            'los_scenario': {
                'description': "平均在院日数を1日延ばすと",
                'effect': los_effect, 
                'unit': "人の日平均在院患者数増加",
                'simple': True
            },
            'current_status': {
                'theoretical_census': theoretical_census,
                'actual_census': current_census,
                'variance': variance
            },
            'has_simulation': True,
            'is_simplified': True,
            'note': "効果予測計算"
        }
    except Exception as e:
        logger.error(f"効果予測計算エラー: {e}")
        return {
            'admission_scenario': {
                'description': "新入院を週に1人増やすと",
                'effect': 0,
                'unit': "人の日平均在院患者数増加（計算エラー）",
                'simple': True
            },
            'los_scenario': {
                'description': "平均在院日数を1日延ばすと",
                'effect': 0, 
                'unit': "人の日平均在院患者数増加（計算エラー）",
                'simple': True
            },
            'has_simulation': False,
            'is_simplified': True,
            'error': True,
            'note': "計算エラーが発生しました"
        }

def _decide_basic_action(kpi, feasibility, simulation):
    """基本アクション決定（従来のロジック）"""
    census_achievement = kpi.get('daily_census_achievement', 100)
    
    if census_achievement >= 95:
        return {
            "action": "現状維持",
            "reasoning": "目標をほぼ達成しており、良好な状況を継続",
            "priority": "low",
            "color": "#7fb069"
        }
    elif census_achievement < 85:
        return {
            "action": "両方検討",
            "reasoning": "大幅な不足のため、新入院増加と在院日数適正化の両面からアプローチが必要",
            "priority": "urgent",
            "color": "#e08283"
        }
    else:
        admission_score = sum(feasibility.get("admission", {}).values()) if feasibility else 0
        los_score = sum(feasibility.get("los", {}).values()) if feasibility else 0
        
        if admission_score >= 1 and los_score >= 1:
            if simulation and simulation.get("admission_plan", {}).get("increase", 0) <= simulation.get("los_plan", {}).get("increase", 0):
                return {
                    "action": "新入院重視",
                    "reasoning": "病床余裕があり、新入院増加がより実現可能",
                    "priority": "medium",
                    "color": "#f5d76e"
                }
        
        if admission_score >= 1:
            return {
                "action": "新入院重視",
                "reasoning": "病床に余裕があり、新入院増加が効果的",
                "priority": "medium",
                "color": "#f5d76e"
            }
        elif los_score >= 1:
            return {
                "action": "在院日数調整",
                "reasoning": "在院日数に調整余地があり効果的",
                "priority": "medium",
                "color": "#f5d76e"
            }
        else:
            return {
                "action": "経過観察",
                "reasoning": "現状では大きな変更は困難、トレンド注視が必要",
                "priority": "low",
                "color": "#b3b9b3"
            }

def _assess_feasibility(score):
    """実現可能性スコアの評価"""
    if score >= 2:
        return "高い"
    elif score >= 1:
        return "中程度"
    else:
        return "低い"

def _calculate_expected_effect(census_gap, hospital_targets, current_census):
    """期待効果計算"""
    if census_gap >= 0:
        return {
            'status': 'achieved',
            'description': '目標達成済み',
            'impact': 'positive'
        }
    
    # 病院全体への貢献度計算
    total_gap = hospital_targets.get('daily_census', 580) - current_census
    if total_gap > 0:
        hospital_contribution = abs(census_gap) / total_gap * 100
        return {
            'status': 'potential',
            'description': f"目標達成により病院全体ギャップの{hospital_contribution:.1f}%改善",
            'impact': 'significant',
            'contribution_percentage': hospital_contribution
        }
    else:
        return {
            'status': 'maintained',
            'description': '現状維持により安定した貢献',
            'impact': 'stable'
        }

def format_feasibility_details(feasibility_details):
    """実現可能性詳細のフォーマット"""
    if not feasibility_details:
        return "評価データなし"
    
    result = []
    for key, value in feasibility_details.items():
        emoji = "✅" if value else "❌"
        result.append(f"{emoji} {key}")
    
    return " / ".join(result)

def get_action_priority_badge(priority):
    """優先度バッジの取得"""
    priority_config = {
        "urgent": {"label": "緊急", "color": "#e08283", "emoji": "🚨"},
        "medium": {"label": "中", "color": "#f5d76e", "emoji": "⚠️"},
        "low": {"label": "低", "color": "#7fb069", "emoji": "✅"}
    }
    
    return priority_config.get(priority, priority_config["low"])

def get_effort_status_badge(effort_status):
    """目標達成努力度バッジの取得"""
    return {
        'emoji': effort_status.get('emoji', '❓'),
        'status': effort_status.get('status', '評価不能'),
        'color': effort_status.get('color', '#9E9E9E'),
        'level': effort_status.get('level', '不明')
    }

def generate_action_summary_text(comprehensive_data):
    """アクション分析の要約テキスト生成（努力度版）"""
    basic_info = comprehensive_data['basic_info']
    effort_status = comprehensive_data['effort_status']
    analysis = comprehensive_data['current_analysis']
    action = comprehensive_data['basic_action']
    
    summary = f"""
    【{basic_info['dept_name']}】{effort_status['emoji']} {effort_status['status']}
    
    現状: {basic_info['current_census']:.1f}人 (目標: {basic_info['census_target'] or '--'}人)
    達成率: {basic_info['census_achievement']:.1f}% {analysis['census_status']}
    
    推奨アクション: {action['action']}
    理由: {action['reasoning']}
    """
    
    return summary.strip()