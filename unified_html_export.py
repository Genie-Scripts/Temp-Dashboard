# -*- coding: utf-8 -*-
import json

def get_effort_status_from_kpi(kpi):
    """KPIデータから努力度を計算（enhanced_action_analysis.pyと同じロジック）"""
    current_census = kpi.get('daily_avg_census', 0)
    recent_week_census = kpi.get('recent_week_daily_census', 0)
    census_achievement = kpi.get('daily_census_achievement', 0)
    
    trend_change = recent_week_census - current_census
    
    if census_achievement >= 100:
        if trend_change > 0:
            return {
                "status": "✨目標突破中",
                "level": "優秀", 
                "emoji": "✨",
                "description": f"目標達成＋さらに改善中（+{trend_change:.1f}人）",
                "color": "#4CAF50"
            }
        else:
            return {
                "status": "🎯達成継続",
                "level": "良好",
                "emoji": "🎯", 
                "description": "目標達成を継続中",
                "color": "#7fb069"
            }
    elif census_achievement >= 85:
        if trend_change > 0:
            return {
                "status": "💪追い上げ中",
                "level": "改善",
                "emoji": "💪",
                "description": f"目標まであと少し！改善中（+{trend_change:.1f}人）",
                "color": "#FF9800"
            }
        else:
            return {
                "status": "📈要努力", 
                "level": "注意",
                "emoji": "📈",
                "description": "目標まであと少し、さらなる努力を",
                "color": "#FFC107"
            }
    else:
        return {
            "status": "🚨要改善",
            "level": "要改善",
            "emoji": "🚨", 
            "description": "目標達成に向けた積極的な取り組みが必要",
            "color": "#F44336"
        }

def calculate_improvement_speed(kpi):
    """改善スピード度を計算"""
    current_avg = kpi.get('daily_avg_census', 0)
    recent_week = kpi.get('recent_week_daily_census', 0)
    target = kpi.get('daily_census_target', 0)
    
    if target <= 0:
        return {"speed_icon": "❓", "speed_text": "評価困難", "color": "#9E9E9E", "rate": ""}
    
    # 週間改善率
    weekly_change = recent_week - current_avg
    improvement_rate = (weekly_change / target * 100) if target > 0 else 0
    
    if improvement_rate > 2:
        return {"speed_icon": "🚀", "speed_text": "高速改善", "color": "#4CAF50", "rate": f"+{improvement_rate:.1f}%/週"}
    elif improvement_rate > 0.5:
        return {"speed_icon": "⬆️", "speed_text": "順調改善", "color": "#8BC34A", "rate": f"+{improvement_rate:.1f}%/週"}
    elif improvement_rate > -0.5:
        return {"speed_icon": "➡️", "speed_text": "横ばい", "color": "#FFC107", "rate": f"{improvement_rate:+.1f}%/週"}
    else:
        return {"speed_icon": "⬇️", "speed_text": "要注意", "color": "#F44336", "rate": f"{improvement_rate:.1f}%/週"}

def generate_simple_effect_simulation(kpi):
    """シンプルな効果シミュレーション（理論説明なし）"""
    try:
        # 現在の値を取得
        weekly_admissions = kpi.get('weekly_avg_admissions', 0)
        daily_admissions = weekly_admissions / 7
        current_los = kpi.get('avg_length_of_stay', 0)
        current_census = kpi.get('daily_avg_census', 0)
        
        # シナリオ1：新入院を週に1人増やした場合
        new_daily_admissions_1 = daily_admissions + 1/7
        new_census_1 = new_daily_admissions_1 * current_los
        theoretical_census = daily_admissions * current_los
        admission_effect = new_census_1 - theoretical_census
        
        # シナリオ2：平均在院日数を1日延ばした場合  
        new_los_2 = current_los + 1
        new_census_2 = daily_admissions * new_los_2
        los_effect = new_census_2 - theoretical_census
        
        return f"""
            <div class="simple-simulation">
                <div class="simulation-item">
                    <strong>📈 シナリオ1：新入院を週に1人増やすと</strong><br>
                    → 日平均在院患者数 <strong>+{admission_effect:.1f}人</strong>
                </div>
                
                <div class="simulation-item" style="margin-top: 10px;">
                    <strong>📊 シナリオ2：平均在院日数を1日延ばすと</strong><br>
                    → 日平均在院患者数 <strong>+{los_effect:.1f}人</strong>
                </div>
            </div>
        """
    except Exception as e:
        return '<div class="simulation-error">効果シミュレーション: 計算エラー</div>'

def generate_unified_html_export(action_results, period_desc, hospital_targets, dashboard_type="department"):
    """
    アクション提案形式の統合HTMLを生成する (努力度表示版)
    エラーハンドリング強化版
    """
    try:
        # データの妥当性チェック
        if not action_results or not isinstance(action_results, list):
            return "<html><body><h1>エラー: 有効なアクション結果データがありません</h1></body></html>"
        
        # 優先度でソート（安全なアクセス）
        priority_order = {"urgent": 0, "medium": 1, "low": 2}
        try:
            sorted_results = sorted(action_results, key=lambda x: (
                priority_order.get(x.get('action_result', {}).get('priority', 'low'), 2),
                -x.get('kpi', {}).get('daily_avg_census', 0)
            ))
        except Exception as e:
            # ソートに失敗した場合は元の順序を維持
            sorted_results = action_results

        # dashboard_typeに応じて設定を切り替え
        is_department = dashboard_type == "department"
        dashboard_title = "診療科別アクション提案" if is_department else "病棟別アクション提案"
        
        # HTMLカード生成（努力度表示版）
        cards_html = ""
        for result in sorted_results:
            try:
                kpi = result.get('kpi', {})
                action_result = result.get('action_result', {})
                feasibility = result.get('feasibility', {})
                simulation = result.get('simulation', {})
                
                if not kpi or not action_result:
                    # 基本データが不足している場合はスキップ
                    continue
                
                # 努力度計算（メイン表示項目）
                effort_status = get_effort_status_from_kpi(kpi)
                improvement_speed = calculate_improvement_speed(kpi)
                
                # dashboard_typeに応じて名前を取得
                if is_department:
                    item_name = kpi.get('dept_name', 'Unknown')
                else:
                    item_name = kpi.get('ward_name', 'Unknown')

                action = action_result.get('action', '要確認')
                reasoning = action_result.get('reasoning', '')
                action_color = action_result.get('color', '#b3b9b3')
                
                # 現状分析データ（安全なアクセス）
                census_target = kpi.get('daily_census_target', 0) or 0
                # census_actual = kpi.get('daily_avg_census', 0) or 0 # ←期間平均は使用しない
                # ★修正点: 実績値として直近週データを採用
                recent_week_census = kpi.get('recent_week_daily_census', 0) or 0
                # ★修正点: 直近週データで達成率とギャップを再計算
                recalculated_ach = (recent_week_census / census_target * 100) if census_target > 0 else 0
                recalculated_gap = recent_week_census - census_target if census_target > 0 else 0

                
                admission_avg = kpi.get('weekly_avg_admissions', 0) / 7 if kpi.get('weekly_avg_admissions') else 0
                admission_recent = kpi.get('recent_week_admissions', 0) / 7 if kpi.get('recent_week_admissions') else 0
                admission_trend = "↗️増加" if admission_recent > admission_avg * 1.03 else "↘️減少" if admission_recent < admission_avg * 0.97 else "➡️安定"
                
                los_avg = kpi.get('avg_length_of_stay', 0) or 0
                los_recent = kpi.get('recent_week_avg_los', 0) or 0
                los_range = feasibility.get('los_range') if feasibility else None
                los_status = "✅" if los_range and los_range.get("lower", 0) <= los_recent <= los_range.get("upper", 0) else "⚠️"
                
                # 実現可能性データ（安全なアクセス）
                admission_feas = feasibility.get('admission', {}) if feasibility else {}
                los_feas = feasibility.get('los', {}) if feasibility else {}
                
                feas_admission_text = " ".join([f"{'✅' if v else '❌'}{k}" for k, v in admission_feas.items()]) if admission_feas else "評価なし"
                feas_los_text = " ".join([f"{'✅' if v else '❌'}{k}" for k, v in los_feas.items()]) if los_feas else "評価なし"

                # シンプルな効果シミュレーション
                simple_simulation = generate_simple_effect_simulation(kpi)

                # 期待効果（安全な計算）
                effect_text = "目標達成済み"
                if census_target and census_target > 0 and census_gap < 0:
                    # 病院全体ギャップの計算
                    total_hospital_gap = hospital_targets.get('daily_census', 580) - sum(r.get('kpi', {}).get('daily_avg_census', 0) for r in action_results if r.get('kpi'))
                    if total_hospital_gap > 0:
                        hospital_contribution = abs(census_gap) / total_hospital_gap * 100
                        hospital_contribution = min(100.0, max(0.0, hospital_contribution))  # 0-100%に制限
                        effect_text = f"目標達成により病院全体ギャップの{hospital_contribution:.1f}%改善"
                    else:
                        effect_text = "現状維持により安定した貢献"
                elif census_target == 0 or census_target is None:
                    effect_text = "目標値未設定のため効果測定困難"

                card_html = f"""
                <div class="action-card" style="border-left-color: {effort_status['color']};">
                    <div class="card-header">
                        <h3>{item_name}</h3>
                        <div class="effort-status-main" style="color: {effort_status['color']}; font-weight: bold; font-size: 1.1em;">
                            {effort_status['emoji']} {effort_status['status']} ({effort_status['level']})
                        </div>
                        <div class="effort-description" style="color: #666; font-size: 0.9em; margin-top: 5px;">
                            {effort_status['description']}
                        </div>
                        <div class="improvement-speed" style="margin-top: 8px; padding: 5px 10px; background: {improvement_speed['color']}15; border-radius: 5px; font-size: 0.9em;">
                            {improvement_speed['speed_icon']} 改善スピード: {improvement_speed['speed_text']} 
                            {f"({improvement_speed.get('rate', '')})" if improvement_speed.get('rate') else ''}
                        </div>
                    </div>
                    
                    <div class="analysis-section">
                        <h4>現状分析</h4>
                        <div class="metric-line">• 在院患者数：{census_target:.0f}人目標 → <strong>{recent_week_census:.1f}人実績</strong> ({recalculated_ach:.1f}%) {'✅' if recalculated_ach >= 95 else '❌'} {recalculated_gap:+.1f}人</div>
{census_actual:.1f}人実績 ({census_ach:.1f}%) {'✅' if census_ach >= 95 else '❌'} {census_gap:+.1f}人</div>
                        <div class="metric-line">• 新入院：{admission_avg:.1f}人/日期間平均 → {admission_recent:.1f}人/日直近週 ({admission_trend})</div>
                        <div class="metric-line">• 在院日数：{los_avg:.1f}日期間平均 → {los_recent:.1f}日直近週 {los_status}
                        {f'(適正範囲: {los_range["lower"]:.1f}-{los_range["upper"]:.1f}日)' if los_range and isinstance(los_range, dict) and los_range.get("lower") is not None else ''}</div>
                    </div>
                    
                    <div class="feasibility-section">
                        <h4>実現可能性評価</h4>
                        <div class="feasibility-line">• 新入院増加：{feas_admission_text}</div>
                        <div class="feasibility-line">• 在院日数調整：{feas_los_text}</div>
                    </div>
                    
                    <div class="simulation-section">
                        <h4>効果シミュレーション</h4>
                        {simple_simulation}
                    </div>
                    
                    <div class="action-section">
                        <h4>推奨アクション【{action}】</h4>
                        <div class="reasoning">{reasoning}</div>
                    </div>
                    
                    <div class="effect-section">
                        <h4>期待効果</h4>
                        <div class="effect-text" style="color: {action_color};">{effect_text}</div>
                    </div>
                </div>
                """
                cards_html += card_html
                
            except Exception as e:
                # 個別カードでエラーが発生した場合も処理を継続
                error_card = f"""
                <div class="action-card" style="border-left-color: #e08283;">
                    <div class="card-header">
                        <h3>{result.get('kpi', {}).get('dept_name' if is_department else 'ward_name', 'Unknown')}</h3>
                        <div class="effort-status-main" style="color: #e08283;">❓ 評価エラー</div>
                    </div>
                    <div class="analysis-section">
                        <h4>エラー</h4>
                        <div class="metric-line">詳細表示でエラーが発生しました</div>
                        <div class="metric-line">基本情報: {result.get('action_result', {}).get('action', 'データ不足')}</div>
                    </div>
                </div>
                """
                cards_html += error_card

        # 病院全体サマリー（安全な計算）
        try:
            total_census = sum(r.get('kpi', {}).get('daily_avg_census', 0) for r in action_results if r.get('kpi'))
            total_admissions = sum(r.get('kpi', {}).get('weekly_avg_admissions', 0) for r in action_results if r.get('kpi')) / 7
            
            hospital_census_ach = (total_census / hospital_targets['daily_census'] * 100) if hospital_targets.get('daily_census', 0) > 0 else 0
            hospital_admission_ach = (total_admissions / hospital_targets['daily_admissions'] * 100) if hospital_targets.get('daily_admissions', 0) > 0 else 0
            
            hospital_census_gap = total_census - hospital_targets.get('daily_census', 0)
            hospital_admission_gap = total_admissions - hospital_targets.get('daily_admissions', 0)
            
            census_color = "#7fb069" if hospital_census_ach >= 95 else "#f5d76e" if hospital_census_ach >= 85 else "#e08283"
            admission_color = "#7fb069" if hospital_admission_ach >= 95 else "#f5d76e" if hospital_admission_ach >= 85 else "#e08283"
        except Exception as e:
            # 計算エラーの場合はデフォルト値を使用
            total_census = 0
            total_admissions = 0
            hospital_census_ach = 0
            hospital_admission_ach = 0
            hospital_census_gap = 0
            hospital_admission_gap = 0
            census_color = "#e08283"
            admission_color = "#e08283"
            
        # HTML出力（スタイル追加版）
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{dashboard_title} - {period_desc}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #f5f7fa; font-family: 'Noto Sans JP', Meiryo, sans-serif; padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 1920px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #293a27; margin-bottom: 30px; font-size: 2em; }}
        .hospital-summary {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 40px; }}
        .summary-card {{ padding: 20px; border-radius: 10px; border-left: 5px solid; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .summary-header {{ font-weight: 700; font-size: 1.2em; margin-bottom: 10px; }}
        .summary-content {{ font-size: 1.1em; }}
        .actions-grid {{ display: grid; gap: 30px; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); }}
        .action-card {{ background: white; border-radius: 12px; border-left: 6px solid #ccc; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.2s ease; }}
        .action-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 25px rgba(0,0,0,0.15); }}
        .card-header {{ margin-bottom: 15px; }}
        .card-header h3 {{ color: #293a27; font-size: 1.3em; margin-bottom: 5px; }}
        .effort-status-main {{ font-weight: bold; font-size: 1.1em; }}
        .effort-description {{ color: #666; font-size: 0.9em; margin-top: 5px; }}
        .improvement-speed {{ margin-top: 8px; padding: 5px 10px; border-radius: 5px; font-size: 0.9em; }}
        .analysis-section, .feasibility-section, .simulation-section, .action-section, .effect-section {{ margin-bottom: 15px; }}
        h4 {{ color: #7b8a7a; font-size: 1em; margin-bottom: 8px; border-bottom: 1px solid #e0e0e0; padding-bottom: 3px; }}
        .metric-line, .feasibility-line {{ margin-bottom: 5px; font-size: 0.95em; }}
        .simple-simulation {{ background: #f8f9fa; padding: 12px; border-radius: 8px; }}
        .simulation-item {{ margin-bottom: 8px; font-size: 0.95em; }}
        .simulation-error {{ color: #e08283; font-style: italic; }}
        .reasoning {{ font-style: italic; color: #2e3532; }}
        .effect-text {{ font-weight: 600; font-size: 1.05em; }}
        @media (max-width: 768px) {{ 
            .hospital-summary, .actions-grid {{ grid-template-columns: 1fr; }} 
            .action-card {{ padding: 15px; }} 
            .effort-status-main {{ font-size: 1em; }}
            .improvement-speed {{ font-size: 0.85em; }}
        }}
        @media print {{ 
            body {{ padding: 10px; }} 
            .actions-grid {{ grid-template-columns: 1fr; }} 
            .action-card {{ break-inside: avoid; }} 
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 {dashboard_title}</h1>
        <p style="text-align: center; color: #666; margin-bottom: 30px; font-size: 1.1em;">期間: {period_desc}</p>
        
        <div class="hospital-summary">
            <div class="summary-card" style="border-left-color: {census_color};">
                <div class="summary-header">在院患者数</div>
                <div class="summary-content">{hospital_targets.get('daily_census', 0):.0f}人目標 → {total_census:.1f}人実績 ({hospital_census_ach:.1f}%) {hospital_census_gap:+.1f}人</div>
            </div>
            <div class="summary-card" style="border-left-color: {admission_color};">
                <div class="summary-header">新入院患者数</div>
                <div class="summary-content">{hospital_targets.get('daily_admissions', 0):.0f}人/日目標 → {total_admissions:.1f}人/日実績 ({hospital_admission_ach:.1f}%) {hospital_admission_gap:+.1f}人/日</div>
            </div>
        </div>
        
        <div class="actions-grid">
            {cards_html}
        </div>
        
        <div style="text-align: center; margin-top: 40px; color: #666; font-size: 0.9em;">
            <p>✨目標突破中 🎯達成継続 💪追い上げ中 📈要努力 🚨要改善</p>
            <p>生成日時: {period_desc} | 目標達成努力度に基づく評価</p>
        </div>
    </div>
</body>
</html>"""
        
        return html_content
        
    except Exception as e:
        # 全体的なエラーが発生した場合のフォールバック
        error_html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>エラー - {dashboard_type}別アクション提案</title>
</head>
<body style="font-family: sans-serif; padding: 20px;">
    <h1>HTMLエクスポートエラー</h1>
    <p>アクション提案のHTMLエクスポート中にエラーが発生しました。</p>
    <p>エラー詳細: {str(e)}</p>
    <p>期間: {period_desc}</p>
    <p>データ件数: {len(action_results) if action_results else 0}件</p>
    <hr>
    <p>この問題が継続する場合は、システム管理者にお問い合わせください。</p>
</body>
</html>"""
        return error_html