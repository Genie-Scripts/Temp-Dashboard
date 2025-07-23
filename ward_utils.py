"""
病棟特有の処理を行うユーティリティモジュール
ward_performance_tab.pyのロジックを流用
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, Any

def calculate_bed_occupancy_rate(avg_patients: float, bed_count: int) -> float:
    """
    病床利用率を計算
    
    Args:
        avg_patients: 日平均在院患者数
        bed_count: 病床数
        
    Returns:
        病床利用率（%）
    """
    if bed_count <= 0:
        return 0.0
    return (avg_patients / bed_count) * 100

def evaluate_bed_occupancy_rate(occupancy_rate: float) -> Tuple[str, str]:
    """
    病床利用率を評価
    
    Args:
        occupancy_rate: 病床利用率（%）
        
    Returns:
        評価レベル, 評価色
    """
    if occupancy_rate >= 98:
        return "高効率", "#4CAF50"  # 緑
    elif occupancy_rate >= 90:
        return "適正", "#2196F3"   # 青
    else:
        return "改善余地", "#FF9800"  # オレンジ

def calculate_ward_effort_score(achievement_rate: float, bed_occupancy_rate: float) -> float:
    """
    病棟版努力度スコアを計算（目標達成率50% + 病床利用率50%の加重平均）
    
    Args:
        achievement_rate: 目標達成率（%）
        bed_occupancy_rate: 病床利用率（%）
        
    Returns:
        努力度スコア（0-100）
    """
    # 目標達成率を0-100の範囲に正規化（100%超過も考慮）
    normalized_achievement = min(achievement_rate, 100)
    
    # 病床利用率を0-100の範囲に正規化（100%超過も考慮）
    normalized_occupancy = min(bed_occupancy_rate, 100)
    
    # 加重平均（各50%）
    effort_score = (normalized_achievement * 0.5) + (normalized_occupancy * 0.5)
    
    return effort_score

def get_ward_effort_evaluation(effort_score: float) -> Tuple[str, str]:
    """
    病棟版努力度評価を取得
    
    Args:
        effort_score: 努力度スコア（0-100）
        
    Returns:
        評価レベル, 評価色
    """
    if effort_score >= 85:
        return "優秀", "#4CAF50"    # 緑
    elif effort_score >= 70:
        return "良好", "#2196F3"    # 青  
    elif effort_score >= 55:
        return "普通", "#FF9800"    # オレンジ
    else:
        return "要改善", "#F44336"  # 赤

def extract_ward_bed_count(target_df: pd.DataFrame, ward_code: str) -> Optional[int]:
    """
    目標設定CSVから病床数を取得
    
    Args:
        target_df: 目標設定データフレーム
        ward_code: 病棟コード
        
    Returns:
        病床数（見つからない場合はNone）
    """
    ward_data = target_df[
        (target_df['部門コード'] == ward_code) & 
        (target_df['部門種別'] == '病棟') &
        (target_df['指標タイプ'] == '日平均在院患者数')
    ]
    
    if not ward_data.empty and '病床数' in ward_data.columns:
        bed_count = ward_data['病床数'].iloc[0]
        if pd.notna(bed_count):
            return int(bed_count)
    
    return None

def calculate_ward_kpi_with_bed_metrics(ward_kpi: Dict[str, Any], bed_count: Optional[int]) -> Dict[str, Any]:
    """
    病棟KPIに病床関連メトリクスを追加
    
    Args:
        ward_kpi: 既存の病棟KPI辞書
        bed_count: 病床数
        
    Returns:
        病床メトリクス追加済みKPI辞書
    """
    enhanced_kpi = ward_kpi.copy()
    
    if bed_count is not None and bed_count > 0:
        avg_patients = ward_kpi.get('avg_patients', 0)
        achievement_rate = ward_kpi.get('achievement_rate', 0)
        
        # 病床利用率計算
        bed_occupancy_rate = calculate_bed_occupancy_rate(avg_patients, bed_count)
        occupancy_status, occupancy_color = evaluate_bed_occupancy_rate(bed_occupancy_rate)
        
        # 病棟版努力度評価
        effort_score = calculate_ward_effort_score(achievement_rate, bed_occupancy_rate)
        effort_level, effort_color = get_ward_effort_evaluation(effort_score)
        
        # 辞書に追加
        enhanced_kpi.update({
            'bed_count': bed_count,
            'bed_occupancy_rate': bed_occupancy_rate,
            'occupancy_status': occupancy_status,
            'occupancy_color': occupancy_color,
            'ward_effort_score': effort_score,
            'ward_effort_level': effort_level,
            'ward_effort_color': effort_color
        })
    
    return enhanced_kpi

def generate_ward_metrics_html(ward_kpi: Dict[str, Any]) -> str:
    """
    病棟メトリクスカードのHTML生成
    
    Args:
        ward_kpi: 病棟KPI辞書（病床メトリクス含む）
        
    Returns:
        メトリクスカードHTML
    """
    avg_patients = ward_kpi.get('avg_patients', 0)
    target_patients = ward_kpi.get('target_patients', 0)
    achievement_rate = ward_kpi.get('achievement_rate', 0)
    bed_count = ward_kpi.get('bed_count')
    bed_occupancy_rate = ward_kpi.get('bed_occupancy_rate')
    occupancy_status = ward_kpi.get('occupancy_status', '')
    occupancy_color = ward_kpi.get('occupancy_color', '#666')
    ward_effort_level = ward_kpi.get('ward_effort_level', '')
    ward_effort_color = ward_kpi.get('ward_effort_color', '#666')
    
    # 基本メトリクス
    metrics_html = f"""
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
                <div class="metric-status">{"達成" if achievement_rate >= 100 else "未達成"}</div>
            </div>
        </div>
    """
    
    # 病床メトリクス（病床数がある場合）
    if bed_count is not None:
        metrics_html += f"""
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
                <div class="metric-value" style="color: {ward_effort_color}">{ward_effort_level}</div>
                <div class="metric-detail">目標達成+病床効率</div>
            </div>
        </div>
        """
    
    metrics_html += "</div>"
    return metrics_html

def get_ward_css_styles() -> str:
    """
    病棟レポート専用CSSスタイル
    
    Returns:
        CSS文字列
    """
    return """
    .metric-occupancy {
        font-size: 0.9em;
        font-weight: bold;
        margin-top: 4px;
    }
    
    .metric-detail {
        font-size: 0.8em;
        color: #666;
        margin-top: 2px;
    }
    
    .ward-summary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 12px;
        margin: 20px 0;
    }
    
    .ward-summary h3 {
        margin: 0 0 10px 0;
        font-size: 1.2em;
    }
    
    .ward-efficiency-badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.9em;
        font-weight: bold;
        margin-top: 8px;
    }
    """