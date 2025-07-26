"""
統合インデックス生成モジュール
診療科と病棟のタブ切り替え式レポート一覧ページ
"""

from datetime import datetime
from typing import List, Dict, Any, Optional

def create_integrated_mobile_index(
    dept_links: List[Dict[str, Any]], 
    ward_links: List[Dict[str, Any]], 
    period_desc: str,
    dept_kpi_list: Optional[List[Dict[str, Any]]] = None,
    ward_kpi_list: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    診療科・病棟統合インデックスページ生成
    
    Args:
        dept_links: 診療科リンクリスト
        ward_links: 病棟リンクリスト
        period_desc: 期間説明
        dept_kpi_list: 診療科KPIリスト
        ward_kpi_list: 病棟KPIリスト
        
    Returns:
        統合インデックスページHTML
    """
    
    current_time = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    
    # 診療科リスト生成
    dept_list_html = generate_department_list_html(dept_links, dept_kpi_list)
    
    # 病棟リスト生成
    ward_list_html = generate_ward_list_html(ward_links, ward_kpi_list)
    
    # 統合HTML生成
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>病院レポート一覧</title>
        <style>
            {get_integrated_index_css()}
        </style>
    </head>
    <body>
        <div class="container">
            <header class="header">
                <h1>🏥 病院レポート一覧</h1>
                <p class="subtitle">診療科・病棟パフォーマンス</p>
                <p class="period">📅 {period_desc}</p>
            </header>
            
            <nav class="tab-navigation">
                <button class="tab-btn active" data-tab="departments" onclick="switchTab('departments')">
                    📊 診療科別レポート
                </button>
                <button class="tab-btn" data-tab="wards" onclick="switchTab('wards')">
                    🏥 病棟別レポート
                </button>
            </nav>
            
            <main>
                <div id="departments-content" class="tab-content active">
                    <div class="section-header">
                        <h2>診療科別レポート</h2>
                        <p class="section-desc">各診療科の患者数目標達成状況</p>
                    </div>
                    <div class="report-list">
                        {dept_list_html}
                    </div>
                </div>
                
                <div id="wards-content" class="tab-content hidden">
                    <div class="section-header">
                        <h2>病棟別レポート</h2>
                        <p class="section-desc">各病棟の患者数・病床利用率</p>
                    </div>
                    <div class="report-list">
                        {ward_list_html}
                    </div>
                </div>
            </main>
            
            <footer class="footer">
                <div class="summary-stats">
                    <div class="stat-item">
                        <span class="stat-label">診療科</span>
                        <span class="stat-value">{len(dept_links)}科</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">病棟</span>
                        <span class="stat-value">{len(ward_links)}棟</span>
                    </div>
                </div>
                <p class="update-time">最終更新: {current_time}</p>
                <p class="footer-note">レポート名をタップして詳細を確認</p>
            </footer>
        </div>
        
        <script>
            {get_tab_switching_js()}
        </script>
    </body>
    </html>
    """
    
    return html_content

def generate_department_list_html(
    dept_links: List[Dict[str, Any]], 
    dept_kpi_list: Optional[List[Dict[str, Any]]] = None
) -> str:
    """診療科リストHTML生成"""
    if not dept_links:
        return '<div class="no-data">診療科レポートがありません</div>'
    
    kpi_dict = {item.get('dept_name', ''): item for item in dept_kpi_list or []}
    
    sorted_depts = sorted(
        dept_links, 
        key=lambda x: kpi_dict.get(x.get('name', ''), {}).get('daily_census_achievement', 0), 
        reverse=True
    )
    
    dept_html = ""
    for dept in sorted_depts:
        dept_name = dept.get('name', '不明')
        url = dept.get('path', '#')
        
        kpi = kpi_dict.get(dept_name, {})
        achievement_rate = kpi.get('daily_census_achievement', 0)
        avg_patients = kpi.get('daily_avg_census', 0)
        target_patients = kpi.get('daily_census_target', 0)
        
        if achievement_rate >= 100:
            color, icon = "#4CAF50", "✅"
        elif achievement_rate >= 80:
            color, icon = "#2196F3", "📊"
        else:
            color, icon = "#FF9800", "📈"
        
        dept_html += f'''
        <div class="report-card">
            <a href="{url}" class="report-link">
                <div class="report-header">
                    <h3 class="report-title">{icon} {dept_name}</h3>
                    <div class="report-metrics">
                        <span class="achievement-rate" style="color: {color}">
                            達成率: {achievement_rate:.1f}%
                        </span>
                        <span class="patient-count">
                            {avg_patients:.1f} / {target_patients or "-"}人
                        </span>
                    </div>
                </div>
            </a>
        </div>
        '''
    return dept_html

def generate_ward_list_html(
    ward_links: List[Dict[str, Any]], 
    ward_kpi_list: Optional[List[Dict[str, Any]]] = None
) -> str:
    """病棟リストHTML生成"""
    if not ward_links:
        return '<div class="no-data">病棟レポートがありません</div>'

    kpi_dict = {item.get('ward_code', ''): item for item in ward_kpi_list or []}
    
    sorted_wards = sorted(
        ward_links, 
        key=lambda x: kpi_dict.get(x.get('code', ''), {}).get('bed_occupancy_rate', 0), 
        reverse=True
    )
    
    ward_html = ""
    for ward in sorted_wards:
        ward_code = ward.get('code', '')
        ward_name = ward.get('name', '不明')
        url = ward.get('path', '#')
        
        kpi = kpi_dict.get(ward_code, {})
        bed_count = kpi.get('bed_count', '-')
        occupancy_rate = kpi.get('bed_occupancy_rate', 0)
        occupancy_status = kpi.get('occupancy_status', '')
        
        if occupancy_status == "高効率":
            color, icon = "#4CAF50", "🏆"
        elif occupancy_status == "適正":
            color, icon = "#2196F3", "✅"
        else:
            color, icon = "#FF9800", "📈"
            
        ward_html += f'''
        <div class="report-card ward-card">
            <a href="{url}" class="report-link">
                <div class="report-header">
                    <h3 class="report-title">{icon} {ward_name}</h3>
                </div>
                <div class="ward-metrics">
                    <div class="metric-item"><span class="label">病床:</span><span class="value">{bed_count}床</span></div>
                    <div class="metric-item"><span class="label">利用率:</span><span class="value" style="color: {color}">{occupancy_rate:.1f}%</span></div>
                    <div class="metric-item"><span class="label">状況:</span><span class="value">{occupancy_status}</span></div>
                </div>
            </a>
        </div>
        '''
    return ward_html

def get_integrated_index_css() -> str:
    """統合インデックスページCSS"""
    return """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; background-color: #f5f5f5; }
    .container { max-width: 800px; margin: 0 auto; padding: 15px; background: white; min-height: 100vh; }
    .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 12px; margin-bottom: 20px; text-align: center; }
    .header h1 { font-size: 1.8em; margin-bottom: 8px; }
    .subtitle { font-size: 1em; opacity: 0.9; margin-bottom: 4px; }
    .period { font-size: 0.9em; opacity: 0.8; }
    .tab-navigation { display: flex; margin-bottom: 20px; background: #f8f9fa; border-radius: 8px; padding: 4px; }
    .tab-btn { flex: 1; background: none; border: none; padding: 12px 8px; border-radius: 6px; font-size: 1em; cursor: pointer; transition: all 0.2s; color: #666; }
    .tab-btn.active { background: white; color: #333; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-weight: bold; }
    .tab-content { display: none; animation: fadeIn 0.3s ease-in-out; }
    .tab-content.active { display: block; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .section-header { margin-bottom: 15px; }
    .section-header h2 { font-size: 1.3em; color: #333; margin-bottom: 4px; }
    .section-desc { font-size: 0.9em; color: #666; }
    .report-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 15px; }
    .report-card { background: white; border: 1px solid #e0e0e0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: all 0.2s ease; }
    .report-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .report-link { display: block; padding: 15px; text-decoration: none; color: inherit; }
    .report-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .report-title { font-size: 1.1em; color: #333; margin: 0; }
    .report-metrics { text-align: right; font-size: 0.9em; }
    .achievement-rate { display: block; font-weight: bold; margin-bottom: 2px; }
    .patient-count { display: block; color: #666; font-size: 0.9em; }
    .ward-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 10px; font-size: 0.9em; }
    .metric-item { text-align: center; }
    .metric-item .label { display: block; font-size: 0.8em; color: #888; }
    .metric-item .value { font-weight: bold; }
    .no-data { text-align: center; color: #888; padding: 40px 20px; font-style: italic; grid-column: 1 / -1; }
    .footer { text-align: center; padding: 20px; border-top: 1px solid #e0e0e0; margin-top: 20px; }
    .summary-stats { display: flex; justify-content: center; gap: 30px; margin-bottom: 10px; }
    .stat-item { text-align: center; }
    .stat-label { font-size: 0.8em; color: #666; }
    .stat-value { font-size: 1.1em; font-weight: bold; }
    .update-time, .footer-note { font-size: 0.8em; color: #666; margin-top: 10px; }
    """

def get_tab_switching_js() -> str:
    """タブ切り替えJavaScript"""
    return """
    function switchTab(tabName) {
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
        document.getElementById(`${tabName}-content`).classList.add('active');
    }
    """