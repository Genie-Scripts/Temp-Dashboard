import logging
import pandas as pd
from datetime import datetime
from report_generation.utils import get_hospital_targets
logger = logging.getLogger(__name__)

def generate_comprehensive_action_data(kpi, feasibility, simulation, hospital_targets):
    """
    HTMLエクスポート版と同等の詳細アクション分析データを生成（直近週重視版）
    
    修正内容：
    - 直近週の実績を評価の中心に変更
    - 直近週 vs 目標、直近週 vs 期間平均の両面評価
    - 在院患者数の目標達成をエンドポイントとする判定強化
    
    Args:
        kpi: KPI辞書
        feasibility: 実現可能性評価辞書
        simulation: シミュレーション結果辞書
        hospital_targets: 病院全体目標辞書
    
    Returns:
        dict: 詳細分析データ（直近週重視版）
    """
    try:
        # 基本情報の取得
        dept_name = kpi.get('dept_name', kpi.get('ward_name', 'Unknown'))
        
        # ===== 直近週重視のKPIデータ取得 =====
        # 在院患者数（直近週中心）
        period_avg_census = kpi.get('daily_avg_census', 0)      # 期間平均
        recent_week_census = kpi.get('recent_week_daily_census', 0)  # 直近週実績★
        census_target = kpi.get('daily_census_target', 0)       # 目標値
        
        # 新入院（直近週中心）
        period_avg_admissions = kpi.get('weekly_avg_admissions', 0)  # 期間平均（週間）
        recent_week_admissions = kpi.get('recent_week_admissions', 0)  # 直近週実績★
        admissions_target = kpi.get('weekly_admissions_target', 0)  # 新入院目標値
        
        # 在院日数
        los_avg = kpi.get('avg_length_of_stay', 0)      # 期間平均
        los_recent = kpi.get('recent_week_avg_los', 0)  # 直近週実績★
        
        # ===== 直近週ベースの達成率計算 =====
        recent_census_achievement = (recent_week_census / census_target * 100) if census_target > 0 else 0
        recent_admissions_achievement = (recent_week_admissions / admissions_target * 100) if admissions_target > 0 else 0
        
        # ===== 直近週 vs 期間平均の変化率 =====
        census_trend_rate = ((recent_week_census - period_avg_census) / period_avg_census * 100) if period_avg_census > 0 else 0
        admissions_trend_rate = ((recent_week_admissions - period_avg_admissions) / period_avg_admissions * 100) if period_avg_admissions > 0 else 0
        los_trend_rate = ((los_recent - los_avg) / los_avg * 100) if los_avg > 0 else 0
        
        # 1. 直近週重視の努力度評価
        effort_evaluation = _calculate_recent_week_effort_status(
            recent_week_census, census_target, recent_census_achievement, census_trend_rate
        )
        
        # 2. 直近週中心の現状分析
        recent_week_analysis = _analyze_recent_week_performance(
            recent_week_census, census_target, recent_census_achievement,
            recent_week_admissions, admissions_target, recent_admissions_achievement,
            census_trend_rate, admissions_trend_rate, los_trend_rate
        )
        
        # 3. 実現可能性評価（従来通り）
        admission_feas = feasibility.get('admission', {}) if feasibility else {}
        los_feas = feasibility.get('los', {}) if feasibility else {}
        
        admission_feas_score = sum(admission_feas.values())
        los_feas_score = sum(los_feas.values())
        
        # 4. 直近週ベースの効果シミュレーション
        recent_week_simulation = _calculate_recent_week_effect_simulation(kpi)
        
        # 5. 直近週重視のアクション決定
        recent_week_action = _decide_action_based_on_recent_week_data(
            recent_census_achievement, recent_admissions_achievement,
            census_trend_rate, admissions_trend_rate, recent_week_census, census_target
        )
        
        # 6. 期待効果計算（直近週ベース）
        expected_effect = _calculate_recent_week_expected_effect(
            recent_week_census, census_target, hospital_targets, recent_census_achievement
        )
        
        # 7. 総合データ構造（直近週重視版）
        comprehensive_data = {
            'basic_info': {
                'dept_name': dept_name,
                'analysis_focus': 'recent_week',  # 🔥 分析の焦点を明示
                # 期間平均値
                'period_avg_census': period_avg_census,
                'period_avg_admissions': period_avg_admissions,
                'period_avg_los': los_avg,
                # 直近週実績（メイン評価軸）
                'recent_week_census': recent_week_census,
                'recent_week_admissions': recent_week_admissions,
                'recent_week_los': los_recent,
                # 目標値
                'census_target': census_target,
                'admissions_target': admissions_target,
                # 達成率（直近週ベース）
                'recent_census_achievement': recent_census_achievement,
                'recent_admissions_achievement': recent_admissions_achievement
            },
            'recent_week_focus': {  # 🔥 直近週分析セクション
                'census_vs_target': {
                    'value': recent_week_census,
                    'target': census_target,
                    'achievement_rate': recent_census_achievement,
                    'status': _get_achievement_status(recent_census_achievement),
                    'gap': census_target - recent_week_census if census_target > 0 else 0
                },
                'admissions_vs_target': {
                    'value': recent_week_admissions,
                    'target': admissions_target,
                    'achievement_rate': recent_admissions_achievement,
                    'status': _get_achievement_status(recent_admissions_achievement),
                    'gap': admissions_target - recent_week_admissions if admissions_target > 0 else 0
                },
                'trend_analysis': {
                    'census_change': census_trend_rate,
                    'admissions_change': admissions_trend_rate,
                    'los_change': los_trend_rate,
                    'overall_trend': _evaluate_overall_trend(census_trend_rate, admissions_trend_rate)
                }
            },
            'effort_status': effort_evaluation,  # 直近週重視版
            'current_analysis': recent_week_analysis,  # 直近週中心分析
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
            'effect_simulation': recent_week_simulation,  # 直近週ベース
            'basic_action': recent_week_action,  # 直近週重視判定
            'expected_effect': expected_effect,  # 直近週ベース効果
            'analysis_metadata': {
                'focus_period': 'recent_week',
                'evaluation_basis': 'recent_week_vs_target_and_trend',
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'methodology': 'Direct Recent Week Analysis'
            }
        }
        
        return comprehensive_data
        
    except Exception as e:
        logger.error(f"直近週重視詳細アクション分析データ生成エラー ({dept_name}): {e}", exc_info=True)
        return None


def _calculate_recent_week_effort_status(recent_week_census, census_target, recent_achievement, trend_rate):
    """直近週重視の努力度評価（98%基準・トレンド考慮版）"""
    try:
        # 🎯 直近週の達成状況をメインに評価
        if recent_achievement >= 98:  # 98%基準
            if trend_rate > 5:  # 期間平均比で大幅改善
                return {
                    'status': "🚀目標突破＋改善中",
                    'level': "優秀+", 
                    'emoji': "🚀",
                    'description': f"直近週で目標達成（{recent_achievement:.1f}%）＋改善傾向（+{trend_rate:.1f}%）",
                    'color': "#4CAF50",
                    'focus': "recent_week_excellent"
                }
            elif trend_rate >= 0:  # 横ばいまたは微増
                return {
                    'status': "✨目標達成継続",
                    'level': "優秀",
                    'emoji': "✨", 
                    'description': f"直近週で目標達成（{recent_achievement:.1f}%）を継続中",
                    'color': "#4CAF50",
                    'focus': "recent_week_achieved"
                }
            else:  # 達成しているが下降気味
                return {
                    'status': "⚠️達成も下降注意",
                    'level': "良好",
                    'emoji': "⚠️",
                    'description': f"直近週で目標達成（{recent_achievement:.1f}%）だが下降傾向（{trend_rate:.1f}%）",
                    'color': "#FF9800",
                    'focus': "recent_week_achieved_declining"
                }
                
        elif recent_achievement >= 90:  # 90-98%の中間レベル
            if trend_rate > 3:  # 改善傾向
                return {
                    'status': "💪追い上げ中",
                    'level': "改善",
                    'emoji': "💪",
                    'description': f"直近週で追い上げ中（{recent_achievement:.1f}%）改善傾向（+{trend_rate:.1f}%）",
                    'color': "#2196F3",
                    'focus': "recent_week_improving"
                }
            elif trend_rate >= -3:  # 横ばい
                return {
                    'status': "📊あと一歩",
                    'level': "注意",
                    'emoji': "📊",
                    'description': f"直近週で目標まであと少し（{recent_achievement:.1f}%）",
                    'color': "#FF9800",
                    'focus': "recent_week_close"
                }
            else:  # 悪化傾向
                return {
                    'status': "📉要注意",
                    'level': "警戒",
                    'emoji': "📉",
                    'description': f"直近週で目標未達（{recent_achievement:.1f}%）＋悪化傾向（{trend_rate:.1f}%）",
                    'color': "#FF5722",
                    'focus': "recent_week_declining"
                }
                
        else:  # 90%未満の緊急レベル
            return {
                'status': "🚨緊急対応必要",
                'level': "要緊急改善",
                'emoji': "🚨", 
                'description': f"直近週で大幅未達（{recent_achievement:.1f}%）緊急対策が必要",
                'color': "#F44336",
                'focus': "recent_week_emergency"
            }
            
    except Exception as e:
        logger.error(f"直近週努力度計算エラー: {e}")
        return {
            'status': "❓評価困難",
            'level': "不明",
            'emoji': "❓",
            'description': "直近週データ不足のため評価困難",
            'color': "#9E9E9E",
            'focus': "recent_week_unknown"
        }


def _analyze_recent_week_performance(recent_census, census_target, recent_census_achievement,
                                   recent_admissions, admissions_target, recent_admissions_achievement,
                                   census_trend_rate, admissions_trend_rate, los_trend_rate):
    """直近週のパフォーマンス詳細分析"""
    
    analysis = {
        "primary_issue": "",  # 最重要課題
        "trend_assessment": "",  # トレンド評価
        "opportunity": "",  # 改善機会
        "risk_factors": [],  # リスク要因
        "strengths": []  # 強み
    }
    
    # 🎯 最重要課題の特定（在院患者数の直近週実績ベース）
    if recent_census_achievement >= 98:
        analysis["primary_issue"] = f"✅ 直近週で目標達成（{recent_census_achievement:.1f}%）- 現状維持が課題"
    elif recent_census_achievement >= 90:
        gap = census_target - recent_census if census_target > 0 else 0
        analysis["primary_issue"] = f"📊 直近週で目標まで{gap:.1f}人不足（達成率{recent_census_achievement:.1f}%）"
    else:
        gap = census_target - recent_census if census_target > 0 else 0
        analysis["primary_issue"] = f"🚨 直近週で大幅不足（{gap:.1f}人、達成率{recent_census_achievement:.1f}%）"
    
    # 📈 トレンド評価（期間平均からの変化）
    if census_trend_rate >= 5:
        analysis["trend_assessment"] = f"📈 直近週は大幅改善傾向（期間平均比+{census_trend_rate:.1f}%）"
    elif census_trend_rate >= 0:
        analysis["trend_assessment"] = f"➡️ 直近週は安定～微増（期間平均比+{census_trend_rate:.1f}%）"
    elif census_trend_rate >= -5:
        analysis["trend_assessment"] = f"📉 直近週は微減傾向（期間平均比{census_trend_rate:.1f}%）"
    else:
        analysis["trend_assessment"] = f"⚠️ 直近週は悪化傾向（期間平均比{census_trend_rate:.1f}%）"
    
    # 💡 改善機会の特定
    if recent_census_achievement < 98:
        if recent_admissions_achievement < 98:
            analysis["opportunity"] = f"新入院増加が最優先（直近週{recent_admissions_achievement:.1f}%）"
        elif recent_admissions_achievement >= 98:
            analysis["opportunity"] = f"新入院は良好（{recent_admissions_achievement:.1f}%）、在院日数調整で目標達成可能"
        else:
            analysis["opportunity"] = "新入院・在院日数の両面アプローチが有効"
    else:
        analysis["opportunity"] = "目標達成済み、さらなる向上または安定維持を検討"
    
    # ⚠️ リスク要因の特定
    if census_trend_rate < -5:
        analysis["risk_factors"].append(f"在院患者数の悪化傾向（{census_trend_rate:.1f}%）")
    if admissions_trend_rate < -5:
        analysis["risk_factors"].append(f"新入院の減少傾向（{admissions_trend_rate:.1f}%）")
    if los_trend_rate < -10:
        analysis["risk_factors"].append(f"在院日数の急激短縮（{los_trend_rate:.1f}%）")
    if recent_census_achievement < 90:
        analysis["risk_factors"].append("目標達成率が危険水準（90%未満）")
    
    # 💪 強みの特定
    if recent_census_achievement >= 98:
        analysis["strengths"].append(f"直近週で目標達成（{recent_census_achievement:.1f}%）")
    if recent_admissions_achievement >= 98:
        analysis["strengths"].append(f"新入院目標達成（{recent_admissions_achievement:.1f}%）")
    if census_trend_rate > 0:
        analysis["strengths"].append(f"在院患者数の改善傾向（+{census_trend_rate:.1f}%）")
    if admissions_trend_rate > 0:
        analysis["strengths"].append(f"新入院の増加傾向（+{admissions_trend_rate:.1f}%）")
    
    return analysis


def _calculate_recent_week_effect_simulation(kpi):
    """直近週ベースのリトルの法則効果シミュレーション"""
    try:
        # 直近週の実績値を基準に計算
        recent_week_admissions = kpi.get('recent_week_admissions', 0)
        recent_daily_admissions = recent_week_admissions / 7  # 直近週の日平均新入院率
        recent_los = kpi.get('recent_week_avg_los', 0)  # 直近週の平均在院日数
        recent_census = kpi.get('recent_week_daily_census', 0)  # 直近週の日平均在院患者数
        
        # 直近週ベースの理論値
        theoretical_census_recent = recent_daily_admissions * recent_los
        
        # シナリオ1：新入院を週に1人増やした場合（直近週ベース）
        new_daily_admissions_1 = recent_daily_admissions + 1/7
        new_census_1 = new_daily_admissions_1 * recent_los
        admission_effect = new_census_1 - theoretical_census_recent
        
        # シナリオ2：平均在院日数を1日延ばした場合（直近週ベース）
        new_los_2 = recent_los + 1
        new_census_2 = recent_daily_admissions * new_los_2
        los_effect = new_census_2 - theoretical_census_recent
        
        # 乖離分析（直近週実績 vs 理論値）
        variance_recent = recent_census - theoretical_census_recent
        variance_percentage = abs(variance_recent / theoretical_census_recent * 100) if theoretical_census_recent > 0 else 0
        
        return {
            'admission_scenario': {
                'description': "直近週ベース：新入院を週に1人増やすと",
                'effect': admission_effect,
                'unit': "人の日平均在院患者数増加",
                'calculation': f"({recent_daily_admissions:.3f}+{1/7:.3f})×{recent_los:.1f} = {new_census_1:.1f}",
                'method': "リトルの法則（直近週ベース）",
                'recent_week_focus': True
            },
            'los_scenario': {
                'description': "直近週ベース：在院日数を1日延ばすと",
                'effect': los_effect, 
                'unit': "人の日平均在院患者数増加",
                'calculation': f"{recent_daily_admissions:.2f}×({recent_los:.1f}+1) = {new_census_2:.1f}",
                'method': "リトルの法則（直近週ベース）",
                'recent_week_focus': True
            },
            'recent_week_status': {
                'theoretical_census': theoretical_census_recent,
                'actual_census': recent_census,
                'variance': variance_recent,
                'variance_percentage': variance_percentage,
                'data_quality': "高" if variance_percentage <= 20 else "中" if variance_percentage <= 50 else "参考"
            },
            'has_simulation': True,
            'is_recent_week_focused': True,
            'method': "Little's Law - Recent Week Analysis",
            'note': f"直近週実績に基づく効果予測"
        }
        
    except Exception as e:
        logger.error(f"直近週ベースシミュレーション計算エラー: {e}")
        return {
            'admission_scenario': {'description': "計算エラー", 'effect': 0, 'recent_week_focus': True},
            'los_scenario': {'description': "計算エラー", 'effect': 0, 'recent_week_focus': True},
            'has_simulation': False,
            'error': True,
            'note': "直近週ベース計算でエラーが発生"
        }


def _decide_action_based_on_recent_week_data(recent_census_achievement, recent_admissions_achievement,
                                           census_trend_rate, admissions_trend_rate, recent_census, census_target):
    """
    直近週データに基づく基本アクション決定（98%基準・エンドポイント重視版）
    
    判定フロー：
    1. 直近週の在院患者数達成率（98%基準）
    2. 直近週の新入院達成率（98%基準）
    3. トレンド（期間平均比での変化）
    """
    
    # 🎯 エンドポイント：直近週の在院患者数目標達成状況
    if recent_census_achievement >= 98:
        # ✅ 目標達成時の判定
        if census_trend_rate >= 5:
            return {
                "action": "攻めの現状維持",
                "reasoning": f"直近週で目標達成済み（{recent_census_achievement:.1f}%）＋改善傾向（+{census_trend_rate:.1f}%）。この勢いを維持・拡大",
                "priority": "medium",
                "color": "#4CAF50",
                "focus": "recent_week_excellent"
            }
        else:
            return {
                "action": "安定維持",
                "reasoning": f"直近週で目標達成済み（{recent_census_achievement:.1f}%）。安定した運営を継続",
                "priority": "low",
                "color": "#7fb069",
                "focus": "recent_week_stable"
            }
    
    elif recent_census_achievement >= 90:
        # 🔶 中間レベル：直近週の新入院達成状況で判断
        if recent_admissions_achievement < 98:
            return {
                "action": "新入院重視",
                "reasoning": f"直近週：在院{recent_census_achievement:.1f}%・新入院{recent_admissions_achievement:.1f}%。新入院増加を最優先",
                "priority": "high",
                "color": "#2196F3",
                "focus": "recent_week_admission_focus"
            }
        else:
            return {
                "action": "在院日数調整",
                "reasoning": f"直近週：新入院は達成済み（{recent_admissions_achievement:.1f}%）、在院日数適正化で目標達成可能",
                "priority": "high", 
                "color": "#FF9800",
                "focus": "recent_week_los_focus"
            }
    
    else:
        # 🚨 緊急レベル：直近週が90%未満
        gap = census_target - recent_census if census_target > 0 else 0
        return {
            "action": "緊急総合対策",
            "reasoning": f"直近週で大幅未達（{recent_census_achievement:.1f}%、{gap:.1f}人不足）。新入院・在院日数の両面緊急対策が必要",
            "priority": "urgent",
            "color": "#F44336",
            "focus": "recent_week_emergency"
        }


def _calculate_recent_week_expected_effect(recent_census, census_target, hospital_targets, recent_achievement):
    """直近週ベースの期待効果計算"""
    
    if recent_achievement >= 98:
        return {
            'status': 'achieved_recent_week',
            'description': '直近週で目標達成済み、現状維持または更なる向上',
            'impact': 'maintenance_or_growth',
            'recent_week_focus': True
        }
    
    # 直近週での不足分
    gap_recent_week = census_target - recent_census if census_target > 0 else 0
    
    if gap_recent_week > 0:
        # 病院全体への貢献度（直近週ベース）
        hospital_total_target = hospital_targets.get('daily_census', 580)
        contribution_potential = (gap_recent_week / hospital_total_target * 100) if hospital_total_target > 0 else 0
        
        return {
            'status': 'improvement_potential',
            'description': f"直近週での目標達成により病院全体への{contribution_potential:.1f}%貢献可能",
            'impact': 'significant',
            'gap_recent_week': gap_recent_week,
            'contribution_percentage': contribution_potential,
            'recent_week_focus': True
        }
    else:
        return {
            'status': 'maintained',
            'description': '直近週ベースで安定した貢献を継続',
            'impact': 'stable',
            'recent_week_focus': True
        }


# ===== 補助関数群 =====

def _get_achievement_status(achievement_rate):
    """達成率のステータス判定"""
    if achievement_rate >= 98:
        return "✅ 達成"
    elif achievement_rate >= 90:
        return "📊 あと少し"
    elif achievement_rate >= 80:
        return "📈 要改善"
    else:
        return "🚨 緊急対応"


def _evaluate_overall_trend(census_change, admissions_change):
    """全体トレンドの評価"""
    if census_change >= 5 and admissions_change >= 0:
        return "🔥 大幅改善"
    elif census_change >= 0 and admissions_change >= 0:
        return "📈 改善傾向"
    elif census_change >= -5 and admissions_change >= -5:
        return "➡️ 横ばい"
    else:
        return "📉 要注意"


def _assess_feasibility(score):
    """実現可能性スコアの評価（従来通り）"""
    if score >= 2:
        return "高い"
    elif score >= 1:
        return "中程度"
    else:
        return "低い"


# ===== レガシー関数（互換性維持） =====

def format_feasibility_details(feasibility_details):
    """実現可能性詳細のフォーマット（従来通り）"""
    if not feasibility_details:
        return "評価データなし"
    
    result = []
    for key, value in feasibility_details.items():
        emoji = "✅" if value else "❌"
        result.append(f"{emoji} {key}")
    
    return " / ".join(result)


def get_action_priority_badge(priority):
    """優先度バッジの取得（従来通り）"""
    priority_config = {
        "urgent": {"label": "緊急", "color": "#F44336", "emoji": "🚨"},
        "high": {"label": "高", "color": "#FF9800", "emoji": "⚠️"},
        "medium": {"label": "中", "color": "#2196F3", "emoji": "📊"},
        "low": {"label": "低", "color": "#4CAF50", "emoji": "✅"}
    }
    
    return priority_config.get(priority, priority_config["low"])


def get_effort_status_badge(effort_status):
    """目標達成努力度バッジの取得（従来通り）"""
    return {
        'emoji': effort_status.get('emoji', '❓'),
        'status': effort_status.get('status', '評価不能'),
        'color': effort_status.get('color', '#9E9E9E'),
        'level': effort_status.get('level', '不明')
    }


def generate_action_summary_text(comprehensive_data):
    """アクション分析の要約テキスト生成（直近週重視版）"""
    basic_info = comprehensive_data['basic_info']
    recent_week_focus = comprehensive_data['recent_week_focus']
    effort_status = comprehensive_data['effort_status']
    action = comprehensive_data['basic_action']
    
    summary = f"""
    【{basic_info['dept_name']}】{effort_status['emoji']} {effort_status['status']}
    
    直近週実績: {basic_info['recent_week_census']:.1f}人 / 目標: {basic_info['census_target'] or '--'}人
    直近週達成率: {basic_info['recent_census_achievement']:.1f}% {recent_week_focus['census_vs_target']['status']}
    期間平均比: {recent_week_focus['trend_analysis']['census_change']:+.1f}%
    
    推奨アクション: {action['action']}
    理由: {action['reasoning']}
    """
    
    return summary.strip()


# ===== 従来の関数名（後方互換性維持） =====

def _calculate_effort_status(current_census, recent_week_census, census_achievement):
    """従来の関数名での呼び出し対応"""
    trend_change = recent_week_census - current_census
    trend_rate = (trend_change / current_census * 100) if current_census > 0 else 0
    
    return _calculate_recent_week_effort_status(recent_week_census, None, census_achievement, trend_rate)


def _decide_basic_action(kpi, feasibility, simulation):
    """従来の関数名での呼び出し対応"""
    recent_census_achievement = kpi.get('daily_census_achievement', 100)  # フォールバック
    recent_admissions_achievement = kpi.get('weekly_admissions_achievement', 100)  # フォールバック
    
    return _decide_action_based_on_recent_week_data(
        recent_census_achievement, recent_admissions_achievement, 0, 0,
        kpi.get('daily_avg_census', 0), kpi.get('daily_census_target', 0)
    )


def _calculate_simple_effect_simulation(kpi):
    """従来の関数名での呼び出し対応"""
    return _calculate_recent_week_effect_simulation(kpi)