import pandas as pd
from datetime import datetime
import logging
import urllib.parse
from typing import Dict
from css_styles import CSSStyles

# --- 必要なモジュールをインポート ---
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

def generate_all_in_one_html_report(df, target_data, period="直近12週"):
    """
    全ての診療科・病棟データを含む、単一の統合HTMLレポートを生成する（直近週重視版）
    
    修正内容：
    - 評価基準説明を直近週重視に更新
    - 98%基準の強調
    - 用語説明の明確化
    """
    try:
        from chart import create_interactive_patient_chart, create_interactive_alos_chart, create_interactive_dual_axis_chart
        from mobile_report_generator import _generate_metric_cards_html, _generate_charts_html, _generate_action_plan_html, _adapt_kpi_for_html_generation
        from ward_utils import calculate_ward_kpi_with_bed_metrics

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
        overall_content = cards_all + charts_all + analysis_all
        content_html += f'<div id="view-all" class="view-content active">{overall_content}</div>'

        # --- 診療科別ビューの生成 ---
        for dept_name in all_departments:
            dept_id = f"view-dept-{urllib.parse.quote(dept_name)}"
            try:
                df_dept = df[df[dept_col] == dept_name]
                raw_kpi = calculate_department_kpis(df, target_data, dept_name, dept_name, start_date, end_date, dept_col)
                if not raw_kpi: continue
                
                feasibility = evaluate_feasibility(raw_kpi, df_dept, start_date, end_date)
                simulation = calculate_effect_simulation(raw_kpi)
                html_kpi = _adapt_kpi_for_html_generation(raw_kpi)
                cards = _generate_metric_cards_html(html_kpi, is_ward=False)
                charts = _generate_charts_html(df_dept, html_kpi)
                analysis = _generate_action_plan_html(html_kpi, feasibility, simulation, hospital_targets)
                
                full_dept_content = cards + charts + analysis
                content_html += f'<div id="{dept_id}" class="view-content">{full_dept_content}</div>'
            except Exception as e:
                logger.error(f"診療科「{dept_name}」のレポート部品生成エラー: {e}")
                content_html += f'<div id="{dept_id}" class="view-content"><p>エラー: {dept_name}のレポートを生成できませんでした。</p></div>'

        # --- 病棟別ビューの生成 ---
        for ward_code, ward_name in all_wards:
            ward_id = f"view-ward-{ward_code}"
            try:
                df_ward = df[df['病棟コード'] == ward_code]
                raw_kpi = calculate_ward_kpis(df, target_data, ward_code, ward_name, start_date, end_date, '病棟コード')
                if not raw_kpi: continue

                feasibility = evaluate_feasibility(raw_kpi, df_ward, start_date, end_date)
                simulation = calculate_effect_simulation(raw_kpi)
                html_kpi = _adapt_kpi_for_html_generation(raw_kpi)
                final_kpi = calculate_ward_kpi_with_bed_metrics(html_kpi, raw_kpi.get('bed_count'))
                cards = _generate_metric_cards_html(final_kpi, is_ward=True)
                charts = _generate_charts_html(df_ward, final_kpi)
                analysis = _generate_action_plan_html(final_kpi, feasibility, simulation, hospital_targets)
                full_ward_content = cards + charts + analysis
                content_html += f'<div id="{ward_id}" class="view-content">{full_ward_content}</div>'
            except Exception as e:
                logger.error(f"病棟「{ward_name}」のレポート部品生成エラー: {e}")
                content_html += f'<div id="{ward_id}" class="view-content"><p>エラー: {ward_name}のレポートを生成できませんでした。</p></div>'

        # 改善されたドロップダウンメニューの生成（従来通り）
        dept_options = ""
        for dept_name in all_departments:
            dept_id = f"view-dept-{urllib.parse.quote(dept_name)}"
            dept_options += f'<option value="{dept_id}">{dept_name}</option>'
            
        ward_options = ""
        for ward_code, ward_name in all_wards:
            ward_id = f"view-ward-{ward_code}"
            ward_options += f'<option value="{ward_id}">{ward_name}</option>'
        
        # ===== 🔥 評価基準パネルのHTML（直近週重視版に更新） =====
        info_panel_html = f"""
        <div id="info-panel" class="info-panel">
            <div class="info-content">
                <button class="close-button" onclick="toggleInfoPanel()">✕</button>
                
                <h2>📊 評価基準について（直近週重視版）</h2>
                
                <div class="info-section">
                    <h3>🎯 アクションの優先順位（98%基準・直近週重視）</h3>
                    <div class="priority-box urgent">
                        <h4>🚨 緊急（直近週達成率90%未満）</h4>
                        <p>直近週の実績が90%を下回る場合、新入院増加と在院日数適正化の両面からの緊急対応が必要</p>
                    </div>
                    <div class="priority-box medium">
                        <h4>⚠️ 高（直近週達成率90-98%）</h4>
                        <p>直近週の新入院目標達成状況により、新入院増加または在院日数調整を選択的に実施</p>
                    </div>
                    <div class="priority-box low">
                        <h4>✅ 低（直近週達成率98%以上）</h4>
                        <p>直近週で目標達成済み。現状維持を基本とし、さらなる効率化の余地を検討</p>
                    </div>
                    <div class="emphasis-box">
                        <strong>📍 重要：</strong>評価は<span style="color: #e91e63; font-weight: bold;">直近週の実績</span>を最重要視し、
                        <span style="color: #5b5fde; font-weight: bold;">98%基準</span>で判定します
                    </div>
                </div>
                
                <div class="info-section">
                    <h3>🌟 週間総合評価（S〜D）- 直近週基準</h3>
                    <table class="criteria-table">
                        <tr>
                            <th>評価</th>
                            <th>基準</th>
                            <th>説明</th>
                        </tr>
                        <tr class="grade-s">
                            <td><strong>S</strong></td>
                            <td>直近週目標達成＋大幅改善</td>
                            <td>直近週達成率<span style="color: #10b981; font-weight: bold;">98%以上</span>かつ期間平均比+10%以上</td>
                        </tr>
                        <tr class="grade-a">
                            <td><strong>A</strong></td>
                            <td>直近週目標達成＋改善傾向</td>
                            <td>直近週達成率<span style="color: #3b82f6; font-weight: bold;">98%以上</span>かつ期間平均比+5%以上</td>
                        </tr>
                        <tr class="grade-b">
                            <td><strong>B</strong></td>
                            <td>改善傾向あり</td>
                            <td>直近週目標未達だが期間平均比プラス</td>
                        </tr>
                        <tr class="grade-c">
                            <td><strong>C</strong></td>
                            <td>横ばい傾向</td>
                            <td>期間平均比±5%以内</td>
                        </tr>
                        <tr class="grade-d">
                            <td><strong>D</strong></td>
                            <td>要改善</td>
                            <td>期間平均比-5%以下</td>
                        </tr>
                    </table>
                    <div class="attention-box">
                        <span style="color: #92400e;">⚠️ 重要な変更点</span><br>
                        • 目標達成基準を95%から<strong style="color: #e91e63;">98%</strong>に引き上げ<br>
                        • 評価軸を期間平均から<strong style="color: #5b5fde;">直近週実績</strong>に変更<br>
                        • 変化率は「直近週 vs 期間平均」で算出
                    </div>
                </div>
                
                <div class="info-section">
                    <h3>📈 改善度評価（直近週 vs 期間平均）</h3>
                    <ul class="criteria-list">
                        <li><span class="badge excellent">大幅改善</span> 直近週が期間平均比+10%以上</li>
                        <li><span class="badge good">改善</span> 直近週が期間平均比+5〜10%</li>
                        <li><span class="badge stable">維持</span> 直近週が期間平均比±5%未満</li>
                        <li><span class="badge warning">低下</span> 直近週が期間平均比-5〜-10%</li>
                        <li><span class="badge danger">要注意</span> 直近週が期間平均比-10%以下</li>
                    </ul>
                    <div class="note-box">
                        <strong>📝 注意：</strong>「期間平均比」は、分析対象期間（{period}）の平均値に対する直近週実績の変化率です
                    </div>
                </div>
                
                <div class="info-section">
                    <h3>📅 平均在院日数の評価（直近週重視）</h3>
                    <div class="los-criteria">
                        <h4>🎯 直近週で目標達成時（達成率98%以上）</h4>
                        <ul>
                            <li>直近週で短縮 → <span class="badge excellent">効率的</span></li>
                            <li>直近週で維持 → <span class="badge stable">安定</span></li>
                            <li>直近週で延長 → <span class="badge warning">要確認</span></li>
                        </ul>
                        
                        <h4>⚠️ 直近週で目標未達時（達成率98%未満）</h4>
                        <ul>
                            <li>直近週で短縮 → <span class="badge warning">要検討</span>（収益への影響確認）</li>
                            <li>直近週で維持 → <span class="badge warning">要対策</span></li>
                            <li>直近週で延長 → <span class="badge good">改善中</span>（病床稼働向上）</li>
                        </ul>
                    </div>
                    <div class="emphasis-box">
                        <strong>💡 ポイント：</strong>在院日数の評価も直近週の実績を中心に、期間平均との比較で判定
                    </div>
                </div>
                
                <div class="info-section">
                    <h3>📖 用語説明（直近週重視版）</h3>
                    <dl class="term-list">
                        <dt>🔥 直近週（最重要指標）</dt>
                        <dd>分析期間の最新1週間（月曜〜日曜）の実績値。<strong style="color: #e91e63;">アクション判定の主要評価軸</strong></dd>
                        
                        <dt>期間平均</dt>
                        <dd>分析対象期間（{period}）全体の平均値。直近週との比較基準として使用</dd>
                        
                        <dt>🎯 直近週目標達成率（主要KPI）</dt>
                        <dd>（直近週実績値 ÷ 目標値）× 100%。<strong style="color: #5b5fde;">98%以上で目標達成と判定</strong></dd>
                        
                        <dt>期間平均比</dt>
                        <dd>（直近週の値 - 期間平均値）÷ 期間平均値 × 100%。改善傾向の判定に使用</dd>
                        
                        <dt>新入院目標</dt>
                        <dd>各診療科・病棟に設定された週間新入院患者数の目標値。<strong>直近週実績</strong>で評価</dd>
                        
                        <dt>病床稼働率</dt>
                        <dd>（在院患者数 ÷ 病床数）× 100%。直近週と期間平均の両方で算出</dd>
                        
                        <dt>🎯 エンドポイント</dt>
                        <dd><strong style="color: #e91e63;">在院患者数の目標達成</strong>。全ての施策の最終目標</dd>
                    </dl>
                </div>
                
                <div class="info-section">
                    <h3>🔄 アクション判定フロー</h3>
                    <div class="flow-chart">
                        <div class="flow-step">
                            <div class="step-number">1</div>
                            <div class="step-content">
                                <strong>直近週の在院患者数達成率をチェック</strong><br>
                                98%以上 → 現状維持系<br>
                                90-98% → 改善系<br>
                                90%未満 → 緊急対応系
                            </div>
                        </div>
                        <div class="flow-arrow">↓</div>
                        <div class="flow-step">
                            <div class="step-number">2</div>
                            <div class="step-content">
                                <strong>直近週の新入院達成状況で詳細判定</strong><br>
                                新入院も未達 → 新入院重視<br>
                                新入院は達成 → 在院日数調整
                            </div>
                        </div>
                        <div class="flow-arrow">↓</div>
                        <div class="flow-step">
                            <div class="step-number">3</div>
                            <div class="step-content">
                                <strong>期間平均比で改善傾向を考慮</strong><br>
                                改善傾向 → 積極戦略<br>
                                悪化傾向 → 防御的戦略
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
        
        # --- 最終的なHTMLの組み立て（従来通りだが、タイトルを直近週重視に更新） ---
        final_html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>統合パフォーマンスレポート（直近週重視版）</title>
            <style>
                /* ベース設定（従来通り） */
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                :root {{
                    /* カラーパレット */
                    --primary-color: #5B5FDE;
                    --primary-dark: #4347B8;
                    --primary-light: #7B7EE6;
                    --secondary-color: #E91E63;
                    --success-color: #10B981;
                    --warning-color: #F59E0B;
                    --danger-color: #EF4444;
                    --info-color: #3B82F6;
                    
                    /* グレースケール */
                    --gray-50: #F9FAFB;
                    --gray-100: #F3F4F6;
                    --gray-200: #E5E7EB;
                    --gray-300: #D1D5DB;
                    --gray-400: #9CA3AF;
                    --gray-500: #6B7280;
                    --gray-600: #4B5563;
                    --gray-700: #374151;
                    --gray-800: #1F2937;
                    --gray-900: #111827;
                    
                    /* シャドウ */
                    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
                    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                    --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
                    
                    /* トランジション */
                    --transition-fast: 150ms ease-in-out;
                    --transition-normal: 300ms ease-in-out;
                }}
                
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans JP', sans-serif;
                    background-color: var(--gray-50);
                    color: var(--gray-800);
                    line-height: 1.6;
                    -webkit-font-smoothing: antialiased;
                    -moz-osx-font-smoothing: grayscale;
                }}
                
                /* === 情報パネル専用スタイル（直近週重視版） === */
                .priority-box {{
                    background: rgba(91, 95, 222, 0.05);
                    border: 1px solid rgba(91, 95, 222, 0.2);
                    border-radius: 8px;
                    padding: 15px;
                    margin-bottom: 15px;
                }}
                
                .priority-box.urgent {{
                    background: rgba(239, 68, 68, 0.05);
                    border-color: rgba(239, 68, 68, 0.2);
                }}
                
                .priority-box.medium {{
                    background: rgba(245, 158, 11, 0.05);
                    border-color: rgba(245, 158, 11, 0.2);
                }}
                
                .priority-box.low {{
                    background: rgba(16, 185, 129, 0.05);
                    border-color: rgba(16, 185, 129, 0.2);
                }}
                
                .emphasis-box {{
                    background: linear-gradient(135deg, rgba(233, 30, 99, 0.1) 0%, rgba(91, 95, 222, 0.1) 100%);
                    border-left: 4px solid var(--secondary-color);
                    padding: 15px;
                    margin-top: 15px;
                    border-radius: 0 8px 8px 0;
                    font-size: 0.95em;
                }}
                
                .attention-box {{
                    background: rgba(245, 158, 11, 0.1);
                    border: 1px solid rgba(245, 158, 11, 0.3);
                    border-radius: 8px;
                    padding: 15px;
                    margin-top: 15px;
                    font-size: 0.9em;
                }}
                
                .note-box {{
                    background: rgba(59, 130, 246, 0.05);
                    border-left: 3px solid var(--info-color);
                    padding: 12px;
                    margin-top: 10px;
                    border-radius: 0 6px 6px 0;
                    font-size: 0.9em;
                }}
                
                .flow-chart {{
                    margin-top: 20px;
                }}
                
                .flow-step {{
                    display: flex;
                    align-items: flex-start;
                    gap: 15px;
                    background: var(--gray-50);
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 10px;
                }}
                
                .step-number {{
                    background: var(--primary-color);
                    color: white;
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    flex-shrink: 0;
                }}
                
                .step-content {{
                    flex: 1;
                    font-size: 0.9em;
                }}
                
                .flow-arrow {{
                    text-align: center;
                    font-size: 1.5em;
                    color: var(--primary-color);
                    margin: 5px 0;
                }}
                
                /* コンテナ（従来通り） */
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    box-shadow: var(--shadow-lg);
                    border-radius: 16px;
                    overflow: hidden;
                    margin-top: 20px;
                    margin-bottom: 20px;
                }}
                
                /* ヘッダー（タイトル更新） */
                .header {{
                    background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
                    color: white;
                    padding: 40px 30px;
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                }}
                
                .header::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 320"><path fill="%23ffffff" fill-opacity="0.1" d="M0,96L48,112C96,128,192,160,288,160C384,160,480,128,576,112C672,96,768,96,864,112C960,128,1056,160,1152,160C1248,160,1344,128,1392,112L1440,96L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path></svg>');
                    background-size: cover;
                    opacity: 0.3;
                }}
                
                h1 {{
                    margin: 0;
                    font-size: 2.5em;
                    font-weight: 700;
                    letter-spacing: -0.02em;
                    position: relative;
                    z-index: 1;
                }}
                
                .subtitle {{
                    opacity: 0.95;
                    margin-top: 8px;
                    font-size: 1.1em;
                    position: relative;
                    z-index: 1;
                }}
                
                /* 情報ボタン */
                .info-button {{
                    position: absolute;
                    top: 20px;
                    right: 20px;
                    background: rgba(255, 255, 255, 0.2);
                    border: 2px solid rgba(255, 255, 255, 0.5);
                    color: white;
                    padding: 8px 16px;
                    border-radius: 20px;
                    cursor: pointer;
                    font-size: 0.9em;
                    transition: all 0.3s;
                    backdrop-filter: blur(10px);
                    z-index: 2;
                }}
                
                .info-button:hover {{
                    background: rgba(255, 255, 255, 0.3);
                    transform: translateY(-2px);
                }}
                
                /* 情報パネル */
                .info-panel {{
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    z-index: 1000;
                    overflow-y: auto;
                    animation: fadeIn 0.3s ease-out;
                }}
                
                .info-panel.active {{
                    display: block;
                }}
                
                .info-content {{
                    max-width: 900px;
                    margin: 40px auto;
                    background: white;
                    border-radius: 16px;
                    padding: 40px;
                    position: relative;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
                    animation: slideIn 0.3s ease-out;
                }}
                
                @keyframes fadeIn {{
                    from {{ opacity: 0; }}
                    to {{ opacity: 1; }}
                }}
                
                @keyframes slideIn {{
                    from {{ 
                        opacity: 0;
                        transform: translateY(-20px);
                    }}
                    to {{
                        opacity: 1;
                        transform: translateY(0);
                    }}
                }}
                
                .close-button {{
                    position: absolute;
                    top: 20px;
                    right: 20px;
                    background: none;
                    border: none;
                    font-size: 1.5em;
                    cursor: pointer;
                    color: #666;
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    transition: all 0.3s;
                }}
                
                .close-button:hover {{
                    background: #f0f0f0;
                }}
                
                .info-content h2 {{
                    color: #374151;
                    margin-bottom: 30px;
                    font-size: 1.6em;
                    border-bottom: 2px solid #e5e7eb;
                    padding-bottom: 15px;
                }}
                
                .info-section {{
                    margin-bottom: 35px;
                }}
                
                .info-section h3 {{
                    color: #4b5563;
                    margin-bottom: 15px;
                    font-size: 1.2em;
                }}
                
                .info-section h4 {{
                    color: #6b7280;
                    margin: 15px 0 10px 0;
                    font-size: 1em;
                }}
                
                /* 評価基準テーブル */
                .criteria-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 15px;
                }}
                
                .criteria-table th {{
                    background: #f3f4f6;
                    padding: 12px;
                    text-align: left;
                    font-weight: 600;
                    color: #374151;
                }}
                
                .criteria-table td {{
                    padding: 12px;
                    border-bottom: 1px solid #e5e7eb;
                }}
                
                .criteria-table tr:hover {{
                    background: #f9fafb;
                }}
                
                .grade-s td:first-child {{ color: #10b981; font-size: 1.2em; }}
                .grade-a td:first-child {{ color: #3b82f6; font-size: 1.2em; }}
                .grade-b td:first-child {{ color: #6b7280; font-size: 1.2em; }}
                .grade-c td:first-child {{ color: #f59e0b; font-size: 1.2em; }}
                .grade-d td:first-child {{ color: #ef4444; font-size: 1.2em; }}
                
                /* バッジスタイル */
                .badge {{
                    display: inline-block;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 0.85em;
                    font-weight: 600;
                }}
                
                .badge.excellent {{
                    background: rgba(16, 185, 129, 0.15);
                    color: #10b981;
                }}
                
                .badge.good {{
                    background: rgba(59, 130, 246, 0.15);
                    color: #3b82f6;
                }}
                
                .badge.stable {{
                    background: rgba(245, 158, 11, 0.15);
                    color: #f59e0b;
                }}
                
                .badge.warning {{
                    background: rgba(251, 146, 60, 0.15);
                    color: rgb(234, 88, 12);
                }}
                
                .badge.danger {{
                    background: rgba(239, 68, 68, 0.15);
                    color: #ef4444;
                }}
                
                /* リストスタイル */
                .criteria-list {{
                    list-style: none;
                    padding: 0;
                }}
                
                .criteria-list li {{
                    padding: 8px 0;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                
                /* 用語説明 */
                .term-list dt {{
                    font-weight: 600;
                    color: #374151;
                    margin-top: 15px;
                    margin-bottom: 5px;
                }}
                
                .term-list dd {{
                    margin-left: 20px;
                    color: #6b7280;
                    margin-bottom: 10px;
                }}
                
                /* 以下、従来のスタイルを継承 */
                .controls {{
                    padding: 30px;
                    background: var(--gray-50);
                    border-bottom: 1px solid var(--gray-200);
                }}
                
                .quick-buttons {{
                    display: flex;
                    justify-content: center;
                    gap: 12px;
                    margin-bottom: 20px;
                    flex-wrap: wrap;
                }}
                
                .quick-button {{
                    padding: 12px 24px;
                    background: white;
                    color: var(--gray-700);
                    border: 2px solid var(--gray-200);
                    border-radius: 12px;
                    cursor: pointer;
                    font-size: 0.95em;
                    font-weight: 600;
                    transition: all var(--transition-normal);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    box-shadow: var(--shadow-sm);
                }}
                
                .quick-button:hover {{
                    transform: translateY(-2px);
                    box-shadow: var(--shadow-md);
                    border-color: var(--primary-color);
                    color: var(--primary-color);
                }}
                
                .quick-button.active {{
                    background: var(--primary-color);
                    color: white;
                    border-color: var(--primary-color);
                    box-shadow: var(--shadow-md);
                }}
                
                .selector-group {{
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    gap: 20px;
                    flex-wrap: wrap;
                }}
                
                .selector-wrapper {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    background: white;
                    padding: 12px 20px;
                    border-radius: 12px;
                    box-shadow: var(--shadow-sm);
                }}
                
                .selector-label {{
                    font-weight: 600;
                    color: var(--gray-600);
                    font-size: 0.95em;
                }}
                
                select {{
                    padding: 10px 16px;
                    font-size: 0.95em;
                    border-radius: 8px;
                    border: 2px solid var(--gray-200);
                    background-color: white;
                    cursor: pointer;
                    transition: all var(--transition-fast);
                    min-width: 250px;
                    font-weight: 500;
                    color: var(--gray-700);
                }}
                
                select:hover {{
                    border-color: var(--primary-light);
                }}
                
                select:focus {{
                    outline: 0;
                    border-color: var(--primary-color);
                    box-shadow: 0 0 0 3px rgba(91, 95, 222, 0.1);
                }}
                
                .content-area {{
                    padding: 30px;
                }}
                
                .view-content {{
                    display: none;
                    animation: fadeIn 0.3s ease-in-out;
                }}
                
                .view-content.active {{
                    display: block;
                }}
                
                /* メトリクスカード以下、レスポンシブまで従来通り */
                .summary-cards {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                
                .summary-card {{
                    background: white;
                    border-radius: 16px;
                    padding: 24px;
                    text-align: center;
                    box-shadow: var(--shadow-md);
                    transition: all var(--transition-normal);
                    border: 1px solid var(--gray-100);
                    position: relative;
                    overflow: hidden;
                }}
                
                .summary-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: var(--gray-200);
                }}
                
                .summary-card.card-good::before {{
                    background: var(--success-color);
                }}
                
                .summary-card.card-warning::before {{
                    background: var(--warning-color);
                }}
                
                .summary-card.card-danger::before {{
                    background: var(--danger-color);
                }}
                
                .summary-card.card-info::before {{
                    background: var(--info-color);
                }}
                
                .summary-card:hover {{
                    transform: translateY(-4px);
                    box-shadow: var(--shadow-xl);
                }}
                
                .summary-card h3 {{
                    font-size: 0.9em;
                    color: var(--gray-600);
                    margin-bottom: 12px;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 0.05em;
                }}
                
                .summary-card .value {{
                    font-size: 2.2em;
                    font-weight: 700;
                    margin-bottom: 8px;
                    letter-spacing: -0.02em;
                }}
                
                .summary-card .target {{
                    font-size: 0.9em;
                    color: var(--gray-500);
                    margin-bottom: 8px;
                }}
                
                .summary-card.card-good .value {{
                    color: var(--success-color);
                }}
                
                .summary-card.card-warning .value {{
                    color: var(--warning-color);
                }}
                
                .summary-card.card-danger .value {{
                    color: var(--danger-color);
                }}
                
                .summary-card.card-info .value {{
                    color: var(--info-color);
                }}
                
                .trend {{
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    font-size: 0.85em;
                    padding: 6px 12px;
                    border-radius: 20px;
                    margin-top: 8px;
                    font-weight: 600;
                }}
                
                .trend-up {{
                    background: rgba(239, 68, 68, 0.1);
                    color: var(--danger-color);
                }}
                
                .trend-down {{
                    background: rgba(16, 185, 129, 0.1);
                    color: var(--success-color);
                }}
                
                .trend-stable {{
                    background: rgba(245, 158, 11, 0.1);
                    color: var(--warning-color);
                }}
                
                .section {{
                    background: white;
                    border-radius: 16px;
                    padding: 32px;
                    margin-bottom: 24px;
                    box-shadow: var(--shadow-md);
                    border: 1px solid var(--gray-100);
                }}
                
                .section h2 {{
                    color: var(--gray-800);
                    font-size: 1.4em;
                    margin-bottom: 24px;
                    padding-bottom: 12px;
                    border-bottom: 2px solid var(--gray-100);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-weight: 700;
                }}
                
                .section h3 {{
                    color: var(--gray-700);
                    font-size: 1.1em;
                    margin-top: 24px;
                    margin-bottom: 16px;
                    font-weight: 600;
                }}
                
                .chart-container {{
                    margin-bottom: 24px;
                    border-radius: 12px;
                    overflow: hidden;
                    background: var(--gray-50);
                    padding: 16px;
                    border: 1px solid var(--gray-200);
                }}
                
                .analysis-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 24px;
                }}
                
                .analysis-grid > div {{
                    background: var(--gray-50);
                    padding: 20px;
                    border-radius: 12px;
                    border-left: 4px solid var(--primary-color);
                }}
                
                .analysis-grid h3 {{
                    color: var(--gray-700);
                    font-size: 1em;
                    margin-bottom: 12px;
                    margin-top: 0;
                }}
                
                .analysis-grid p {{
                    margin: 8px 0;
                    color: var(--gray-600);
                    font-size: 0.95em;
                }}
                
                .analysis-grid strong {{
                    color: var(--gray-800);
                    font-weight: 600;
                }}
                
                .action-summary {{
                    background: linear-gradient(135deg, rgba(91, 95, 222, 0.1) 0%, rgba(91, 95, 222, 0.05) 100%);
                    border-left: 5px solid var(--primary-color);
                    padding: 20px;
                    margin-bottom: 20px;
                    border-radius: 12px;
                }}
                
                .action-summary strong {{
                    color: var(--primary-dark);
                    font-size: 1.1em;
                    display: block;
                    margin-bottom: 8px;
                }}
                
                .action-summary p {{
                    color: var(--gray-700);
                    margin: 0;
                }}
                
                .action-list {{
                    list-style: none;
                    padding-left: 0;
                }}
                
                .action-list li {{
                    background: var(--gray-50);
                    margin-bottom: 12px;
                    padding: 16px 20px;
                    border-radius: 12px;
                    border-left: 4px solid var(--primary-light);
                    font-size: 0.95em;
                    transition: all var(--transition-fast);
                    position: relative;
                    padding-left: 40px;
                }}
                
                .action-list li::before {{
                    content: '✓';
                    position: absolute;
                    left: 16px;
                    color: var(--primary-color);
                    font-weight: bold;
                }}
                
                .action-list li:hover {{
                    background: white;
                    box-shadow: var(--shadow-sm);
                    transform: translateX(4px);
                }}
                
                /* レスポンシブ対応 */
                @media (max-width: 768px) {{
                    .container {{
                        margin: 0;
                        border-radius: 0;
                    }}
                    
                    .header {{
                        padding: 30px 20px;
                    }}
                    
                    h1 {{
                        font-size: 2em;
                    }}
                    
                    .info-button {{
                        position: static;
                        margin-top: 15px;
                        display: block;
                        margin-left: auto;
                        margin-right: auto;
                    }}
                    
                    .info-content {{
                        margin: 20px;
                        padding: 25px;
                    }}
                    
                    .criteria-table {{
                        font-size: 0.9em;
                    }}
                    
                    .criteria-table td, .criteria-table th {{
                        padding: 8px;
                    }}
                    
                    .controls {{
                        padding: 20px;
                    }}
                    
                    .quick-buttons {{
                        gap: 8px;
                    }}
                    
                    .quick-button {{
                        padding: 10px 16px;
                        font-size: 0.9em;
                    }}
                    
                    select {{
                        min-width: 200px;
                    }}
                    
                    .summary-cards {{
                        grid-template-columns: 1fr 1fr;
                        gap: 12px;
                    }}
                    
                    .summary-card {{
                        padding: 20px;
                    }}
                    
                    .summary-card .value {{
                        font-size: 1.8em;
                    }}
                    
                    .section {{
                        padding: 20px;
                    }}
                }}
                
                /* 印刷対応 */
                @media print {{
                    body {{
                        background: white;
                    }}
                    
                    .container {{
                        box-shadow: none;
                        margin: 0;
                    }}
                    
                    .controls {{
                        display: none;
                    }}
                    
                    .info-button {{
                        display: none;
                    }}
                    
                    .section {{
                        box-shadow: none;
                        break-inside: avoid;
                    }}
                }}
                
                /* mobile_report_generatorのスタイルを含める */
                {_get_css_styles()}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>統合パフォーマンスレポート</h1>
                    <p class="subtitle">期間: {period_desc} | 🔥 直近週重視版</p>
                    <button class="info-button" onclick="toggleInfoPanel()">
                        ℹ️ 評価基準・用語説明（直近週重視）
                    </button>
                </div>
                <div class="controls">
                    <div class="quick-buttons">
                        <button class="quick-button active" onclick="showView('view-all')">
                            <span>🏥</span> 病院全体
                        </button>
                        <button class="quick-button" onclick="toggleTypeSelector('dept')">
                            <span>🩺</span> 診療科別
                        </button>
                        <button class="quick-button" onclick="toggleTypeSelector('ward')">
                            <span>🏢</span> 病棟別
                        </button>
                    </div>
                    
                    <div class="selector-group">
                        <div class="selector-wrapper" id="dept-selector-wrapper" style="display: none;">
                            <label class="selector-label" for="dept-selector">診療科</label>
                            <select id="dept-selector" onchange="changeView(this.value)">
                                <option value="">診療科を選択してください</option>
                                {dept_options}
                            </select>
                        </div>
                        
                        <div class="selector-wrapper" id="ward-selector-wrapper" style="display: none;">
                            <label class="selector-label" for="ward-selector">病棟</label>
                            <select id="ward-selector" onchange="changeView(this.value)">
                                <option value="">病棟を選択してください</option>
                                {ward_options}
                            </select>
                        </div>
                    </div>
                </div>
                <div class="content-area">
                    {content_html}
                </div>
            </div>
            {info_panel_html}
            <script>
                let currentType = null;
                
                function showView(viewId) {{
                    // 全てのビューを非表示
                    document.querySelectorAll('.view-content').forEach(content => {{
                        content.classList.remove('active');
                    }});
                    
                    // 指定されたビューを表示
                    const targetView = document.getElementById(viewId);
                    if (targetView) {{
                        targetView.classList.add('active');
                        
                        // Plotlyチャートの再描画をトリガー
                        setTimeout(function() {{
                            window.dispatchEvent(new Event('resize'));
                            
                            // Plotlyが存在する場合、各チャートを個別に再描画
                            if (window.Plotly) {{
                                const plots = targetView.querySelectorAll('.plotly-graph-div');
                                plots.forEach(plot => {{
                                    Plotly.Plots.resize(plot);
                                }});
                            }}
                        }}, 100);
                    }}
                    
                    // クイックボタンのアクティブ状態を更新
                    document.querySelectorAll('.quick-button').forEach(btn => {{
                        btn.classList.remove('active');
                    }});
                    
                    if (viewId === 'view-all') {{
                        document.querySelector('.quick-button').classList.add('active');
                        // セレクターを隠す
                        document.getElementById('dept-selector-wrapper').style.display = 'none';
                        document.getElementById('ward-selector-wrapper').style.display = 'none';
                        // セレクターの選択をリセット
                        document.getElementById('dept-selector').value = '';
                        document.getElementById('ward-selector').value = '';
                        currentType = null;
                    }}
                }}
                
                function toggleTypeSelector(type) {{
                    // 病院全体ビューを非表示
                    document.getElementById('view-all').classList.remove('active');
                    
                    // セレクターの表示切替
                    if (type === 'dept') {{
                        document.getElementById('dept-selector-wrapper').style.display = 'flex';
                        document.getElementById('ward-selector-wrapper').style.display = 'none';
                        document.getElementById('ward-selector').value = '';
                    }} else if (type === 'ward') {{
                        document.getElementById('dept-selector-wrapper').style.display = 'none';
                        document.getElementById('ward-selector-wrapper').style.display = 'flex';
                        document.getElementById('dept-selector').value = '';
                    }}
                    
                    currentType = type;
                    
                    // クイックボタンのアクティブ状態を更新
                    document.querySelectorAll('.quick-button').forEach((btn, index) => {{
                        btn.classList.toggle('active', 
                            (index === 1 && type === 'dept') || 
                            (index === 2 && type === 'ward')
                        );
                    }});
                }}
                
                function changeView(viewId) {{
                    if (viewId) {{
                        showView(viewId);
                    }}
                }}
                
                function toggleInfoPanel() {{
                    const panel = document.getElementById('info-panel');
                    panel.classList.toggle('active');
                }}
                
                // パネル外クリックで閉じる
                document.getElementById('info-panel').addEventListener('click', function(e) {{
                    if (e.target === this) {{
                        toggleInfoPanel();
                    }}
                }});

                // ページ読み込み時の初期化
                window.onload = function() {{
                    // 初期表示時にPlotlyチャートを確実に表示
                    setTimeout(function() {{
                        window.dispatchEvent(new Event('resize'));
                        if (window.Plotly) {{
                            const plots = document.querySelectorAll('#view-all .plotly-graph-div');
                            plots.forEach(plot => {{
                                Plotly.Plots.resize(plot);
                            }});
                        }}
                    }}, 300);
                }};
                
                // ブラウザのリサイズ時にもチャートを再描画
                window.addEventListener('resize', function() {{
                    if (window.Plotly) {{
                        const activeView = document.querySelector('.view-content.active');
                        if (activeView) {{
                            const plots = activeView.querySelectorAll('.plotly-graph-div');
                            plots.forEach(plot => {{
                                Plotly.Plots.resize(plot);
                            }});
                        }}
                    }}
                }});
            </script>
        </body>
        </html>
        """
        return final_html

    except Exception as e:
        logger.error(f"直近週重視統合HTMLレポート生成エラー: {e}", exc_info=True)
        return f"<html><body>レポート全体の生成でエラーが発生しました: {e}</body></html>"
        
def _get_css_styles():
    """mobile_report_generator のスタイルを統一感のあるデザインで返す"""
    return CSSStyles.get_integrated_report_styles()

def _get_legacy_integrated_css():
    """レガシー版統合レポートCSS（移行期間中のフォールバック）"""
    return """
    /* 基本的なフォールバックCSS */
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: sans-serif; background: #f5f5f5; }
    .container { max-width: 1200px; margin: 0 auto; }
    .header { background: #667eea; color: white; padding: 40px; }
    .controls { padding: 30px; background: #f9fafb; }
    """