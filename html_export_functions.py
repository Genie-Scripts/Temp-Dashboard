# html_export_functions.py - HTMLエクスポート機能の統一モジュール
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# ★ Phase 1.3: メトリクス表示用HTML生成関数
# ==============================================================================
def generate_metrics_html(kpi_data_list, period_desc, selected_metric, dashboard_type="department"):
    """
    従来の3指標表示用HTML生成
    
    Args:
        kpi_data_list: KPIデータのリスト
        period_desc: 期間説明文
        selected_metric: 選択されたメトリクス名
        dashboard_type: "department" または "ward"
    
    Returns:
        str: 生成されたHTML文字列
    """
    try:
        # dashboard_typeに応じて設定を切り替え
        is_department = dashboard_type == "department"
        dashboard_title = f"診療科別{selected_metric}" if is_department else f"病棟別{selected_metric}"
        item_type_label = "診療科" if is_department else "病棟"
        
        # メトリクス設定
        metric_opts = {
            "日平均在院患者数": {"avg": "daily_avg_census", "recent": "recent_week_daily_census", "target": "daily_census_target", "ach": "daily_census_achievement", "unit": "人"},
            "週合計新入院患者数": {"avg": "weekly_avg_admissions", "recent": "recent_week_admissions", "target": "weekly_admissions_target", "ach": "weekly_admissions_achievement", "unit": "件"},
            "平均在院日数": {"avg": "avg_length_of_stay", "recent": "recent_week_avg_los", "target": "avg_los_target", "ach": "avg_los_achievement", "unit": "日"}
        }
        opt = metric_opts.get(selected_metric, metric_opts["日平均在院患者数"])
        
        # カード生成
        cards_html = ""
        for kpi in kpi_data_list:
            item_name = kpi.get('dept_name' if is_department else 'ward_name', 'Unknown')
            avg_val = kpi.get(opt['avg'], 0)
            recent_val = kpi.get(opt['recent'], 0)
            target_val = kpi.get(opt['target'])
            achievement = kpi.get(opt['ach'], 0)
            
            # 色決定
            if achievement >= 100:
                color = "#7fb069"  # パステルグリーン
            elif achievement >= 80:
                color = "#f5d76e"  # パステルイエロー
            else:
                color = "#e08283"  # パステルレッド
            
            # 病床情報（病棟の日平均在院患者数の場合）
            bed_info_html = ""
            if not is_department and selected_metric == "日平均在院患者数" and kpi.get('bed_count'):
                occupancy = kpi.get('bed_occupancy_rate', 0)
                bed_info_html = f"""
                <div style="margin-top:8px; padding-top:8px; border-top:1px solid #e0e0e0;">
                    <div style="display:flex; justify-content:space-between;">
                        <span style="font-size:0.85em; color:#999;">病床数:</span>
                        <span style="font-size:0.9em; color:#666;">{kpi['bed_count']}床</span>
                    </div>
                    <div style="display:flex; justify-content:space-between;">
                        <span style="font-size:0.85em; color:#999;">稼働率:</span>
                        <span style="font-size:0.9em; font-weight:600; color:#666;">{occupancy:.1f}%</span>
                    </div>
                </div>
                """
            
            card_html = f"""
            <div class="metric-card" style="border-left-color: {color};">
                <h5>{item_name}</h5>
                <div class="metric-line">期間平均: <strong>{avg_val:.1f} {opt['unit']}</strong></div>
                <div class="metric-line">直近週実績: <strong>{recent_val:.1f} {opt['unit']}</strong></div>
                <div class="metric-line">目標: <strong>{f'{target_val:.1f}' if target_val else '--'} {opt['unit']}</strong></div>
                <div class="achievement" style="color: {color};">達成率: <strong>{achievement:.1f}%</strong></div>
                {bed_info_html}
            </div>
            """
            cards_html += card_html

        # HTML出力
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
        h1 {{ text-align: center; color: #293a27; margin-bottom: 10px; font-size: 2em; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; font-size: 1.1em; }}
        .grid-container {{ display: grid; gap: 20px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }}
        .metric-card {{ 
            background: white; border-radius: 12px; border-left: 6px solid #ccc; 
            padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.2s ease; 
        }}
        .metric-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 25px rgba(0,0,0,0.15); }}
        .metric-card h5 {{ color: #293a27; font-size: 1.2em; margin-bottom: 12px; }}
        .metric-line {{ margin-bottom: 8px; font-size: 0.95em; }}
        .achievement {{ margin-top: 12px; font-size: 1.1em; }}
        
        /* モバイル対応 */
        @media (max-width: 768px) {{ 
            .grid-container {{ grid-template-columns: repeat(3, 1fr); gap: 10px; }}
            .metric-card {{ padding: 15px; }}
            .metric-card h5 {{ font-size: 1em; }}
            .metric-line {{ font-size: 0.85em; }}
        }}
        
        @media print {{ 
            .metric-card {{ break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 {dashboard_title}</h1>
        <p class="subtitle">期間: {period_desc}</p>
        
        <div class="grid-container">
            {cards_html}
        </div>
        
        <footer style="text-align: center; margin-top: 40px; color: #999; border-top: 1px solid #eee; padding-top: 20px;">
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
            <p>🏥 経営企画室</p>
        </footer>
    </div>
</body>
</html>"""
        
        return html_content
        
    except Exception as e:
        logger.error(f"メトリクスHTML生成エラー: {e}", exc_info=True)
        return None

# ==============================================================================
# ★ Phase 1.3: アクション提案用HTML生成関数
# ==============================================================================
def generate_action_html(action_results, period_desc, hospital_targets, dashboard_type="department"):
    """
    アクション提案用HTML生成
    
    Args:
        action_results: アクション分析結果のリスト
        period_desc: 期間説明文
        hospital_targets: 病院全体目標
        dashboard_type: "department" または "ward"
    
    Returns:
        str: 生成されたHTML文字列
    """
    try:
        # 統一HTML生成関数を使用（既存）
        from unified_html_export import generate_unified_html_export
        return generate_unified_html_export(action_results, period_desc, hospital_targets, dashboard_type)
        
    except Exception as e:
        logger.error(f"アクションHTML生成エラー: {e}", exc_info=True)
        return None

# ==============================================================================
# ★ Phase 1.3: タブ切り替え対応統合HTML生成関数
# ==============================================================================
def generate_combined_html_with_tabs(metrics_data_dict, action_data, period_desc, dashboard_type="department"):
    """
    タブ切り替え機能付きの統合HTML生成（構文エラー修正版）
    """
    try:
        # dashboard_typeに応じて設定を切り替え
        is_department = dashboard_type == "department"
        dashboard_title = "診療科別パフォーマンス" if is_department else "病棟別パフォーマンス"
        item_type_label = "診療科" if is_department else "病棟"
        
        # タブナビゲーションとコンテンツの生成
        tab_names_order = ["日平均在院患者数", "週合計新入院患者数", "平均在院日数（トレンド分析）", "アクション提案（詳細）"]
        tab_nav_html = ""
        tab_content_html = ""
        
        # 最初のタブをアクティブにするためのフラグ
        first_tab = True

        for tab_name in tab_names_order:
            active_class = "active" if first_tab else ""
            display_style = "block" if first_tab else "none"
            
            # アクション提案タブの処理
            if tab_name == "アクション提案（詳細）":
                if action_data:
                    safe_tab_id = 'tab-action'
                    tab_nav_html += f'<button class="tab-button {active_class}" onclick="showTab(\'{safe_tab_id}\')">{tab_name}</button>'
                    action_content = generate_action_tab_content(action_data, dashboard_type)
                    tab_content_html += f'<div id="{safe_tab_id}" class="tab-content" style="display: {display_style};">{action_content}</div>'
                    if first_tab: first_tab = False

            # トレンド分析タブの処理
            elif tab_name == "平均在院日数（トレンド分析）":
                 if tab_name in metrics_data_dict:
                    safe_tab_id = 'tab-alos-trend'
                    tab_nav_html += f'<button class="tab-button {active_class}" onclick="showTab(\'{safe_tab_id}\')">{tab_name}</button>'
                    content = metrics_data_dict[tab_name]
                    tab_content_html += f'<div id="{safe_tab_id}" class="tab-content" style="display: {display_style};">{content}</div>'
                    if first_tab: first_tab = False

            # その他のメトリクスタブの処理
            else:
                if tab_name in metrics_data_dict:
                    safe_tab_id = f"tab-{tab_name.replace(' ', '-')}"
                    tab_nav_html += f'<button class="tab-button {active_class}" onclick="showTab(\'{safe_tab_id}\')">{tab_name}</button>'
                    kpi_data_list = metrics_data_dict[tab_name]
                    content = generate_metric_tab_content(kpi_data_list, tab_name, dashboard_type)
                    tab_content_html += f'<div id="{safe_tab_id}" class="tab-content" style="display: {display_style};">{content}</div>'
                    if first_tab: first_tab = False

        # HTML出力（CSS/JSの波括弧をエスケープ）
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
        h1 {{ text-align: center; color: #293a27; margin-bottom: 10px; font-size: 2em; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 30px; font-size: 1.1em; }}
        
        /* タブスタイル */
        .tab-navigation {{ display: flex; justify-content: center; margin-bottom: 30px; border-bottom: 2px solid #e0e0e0; }}
        .tab-button {{ 
            background: none; border: none; padding: 12px 24px; cursor: pointer; 
            font-size: 1em; color: #666; border-bottom: 3px solid transparent; 
            transition: all 0.3s ease; margin: 0 5px;
        }}
        .tab-button:hover {{ color: #293a27; background: #f0f0f0; }}
        .tab-button.active {{ color: #293a27; border-bottom-color: #7fb069; font-weight: 600; }}
        
        .tab-content {{ display: none; }}
        .grid-container {{ display: grid; gap: 20px; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }}
        .metric-card {{ 
            background: white; border-radius: 12px; border-left: 6px solid #ccc; 
            padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); transition: transform 0.2s ease; 
        }}
        .metric-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 25px rgba(0,0,0,0.15); }}
        .metric-card h5 {{ color: #293a27; font-size: 1.2em; margin-bottom: 12px; }}
        .metric-line {{ margin-bottom: 8px; font-size: 0.95em; }}
        .achievement {{ margin-top: 12px; font-size: 1.1em; }}
        
        /* アクションカードスタイル */
        .action-card {{ 
            background: white; border-radius: 12px; border-left: 6px solid #ccc; 
            padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin-bottom: 20px; 
        }}
        .action-card h5 {{ color: #293a27; margin-bottom: 10px; }}
        .action-summary {{ margin-bottom: 10px; font-size: 0.9em; }}
        .action-details {{ font-size: 0.85em; color: #666; }}
        
        /* FABホームボタン */
        .fab-home {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
            z-index: 9999;
            cursor: pointer;
        }}
        
        .fab-home:hover {{
            transform: scale(1.1) translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.4);
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }}
        
        .fab-home:active {{
            transform: scale(0.95);
        }}
        
        .fab-home .fab-icon {{
            font-size: 1.8em;
            line-height: 1;
        }}
        
        /* ツールチップ */
        .fab-home::before {{
            content: "ホームに戻る";
            position: absolute;
            right: 70px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.9em;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }}
        
        .fab-home:hover::before {{
            opacity: 1;
        }}
        
        /* モバイル対応 */
        @media (max-width: 768px) {{ 
            .tab-navigation {{ flex-wrap: wrap; }}
            .tab-button {{ flex: 1; min-width: 120px; font-size: 0.9em; padding: 10px 16px; }}
            .grid-container {{ grid-template-columns: repeat(3, 1fr); gap: 10px; }}
            .metric-card {{ padding: 15px; }}
            .metric-card h5 {{ font-size: 1em; }}
            .metric-line {{ font-size: 0.85em; }}
            
            .fab-home {{
                bottom: 20px;
                right: 20px;
                width: 50px;
                height: 50px;
            }}
            
            .fab-home .fab-icon {{
                font-size: 1.5em;
            }}
            
            .fab-home::before {{
                display: none;
            }}
        }}
        
        @media print {{ 
            .tab-navigation {{ display: none; }}
            .tab-content {{ display: block !important; }}
            .metric-card, .action-card {{ break-inside: avoid; }}
            .fab-home {{ display: none; }}
        }}
    </style>
    <script>
        function showTab(tabId) {{
            // すべてのタブを非表示
            const tabContents = document.querySelectorAll('.tab-content');
            tabContents.forEach(tab => tab.style.display = 'none');
            
            // すべてのボタンからactiveクラスを削除
            const tabButtons = document.querySelectorAll('.tab-button');
            tabButtons.forEach(btn => btn.classList.remove('active'));
            
            // 選択されたタブを表示
            document.getElementById(tabId).style.display = 'block';
            
            // 選択されたボタンにactiveクラスを追加
            event.target.classList.add('active');
        }}
    </script>
</head>
<body>
    <div class="container">
        <h1>📊 {dashboard_title}</h1>
        <p class="subtitle">期間: {period_desc}</p>
        
        <div class="tab-navigation">
            {tab_nav_html}
        </div>
        
        {tab_content_html}
        
        <footer style="text-align: center; margin-top: 40px; color: #999; border-top: 1px solid #eee; padding-top: 20px;">
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
            <p>🏥 経営企画室</p>
        </footer>
    </div>
    
    <a href="./index.html" class="fab-home" aria-label="ホームに戻る">
        <span class="fab-icon">🏠</span>
    </a>
</body>
</html>"""
        
        return html_content
        
    except Exception as e:
        logger.error(f"統合HTML生成エラー: {e}", exc_info=True)
        return None

def generate_metric_tab_content(kpi_data_list, metric_name, dashboard_type):
    """メトリクスタブのコンテンツ生成"""
    try:
        is_department = dashboard_type == "department"
        
        # メトリクス設定
        metric_opts = {
            "日平均在院患者数": {"avg": "daily_avg_census", "recent": "recent_week_daily_census", "target": "daily_census_target", "ach": "daily_census_achievement", "unit": "人"},
            "週合計新入院患者数": {"avg": "weekly_avg_admissions", "recent": "recent_week_admissions", "target": "weekly_admissions_target", "ach": "weekly_admissions_achievement", "unit": "件"},
            "平均在院日数": {"avg": "avg_length_of_stay", "recent": "recent_week_avg_los", "target": "avg_los_target", "ach": "avg_los_achievement", "unit": "日"}
        }
        opt = metric_opts.get(metric_name, metric_opts["日平均在院患者数"])
        
        # カード生成
        cards_html = ""
        for kpi in kpi_data_list:
            item_name = kpi.get('dept_name' if is_department else 'ward_name', 'Unknown')
            avg_val = kpi.get(opt['avg'], 0)
            recent_val = kpi.get(opt['recent'], 0)
            target_val = kpi.get(opt['target'])
            achievement = kpi.get(opt['ach'], 0)
            
            # 色決定
            if achievement >= 100:
                color = "#7fb069"
            elif achievement >= 80:
                color = "#f5d76e"
            else:
                color = "#e08283"
            
            # 病床情報（病棟の日平均在院患者数の場合）
            bed_info_html = ""
            if not is_department and metric_name == "日平均在院患者数" and kpi.get('bed_count'):
                occupancy = kpi.get('bed_occupancy_rate', 0)
                bed_info_html = f"""
                <div style="margin-top:8px; padding-top:8px; border-top:1px solid #e0e0e0;">
                    <div class="metric-line">病床数: <strong>{kpi['bed_count']}床</strong></div>
                    <div class="metric-line">稼働率: <strong>{occupancy:.1f}%</strong></div>
                </div>
                """
            
            cards_html += f"""
            <div class="metric-card" style="border-left-color: {color};">
                <h5>{item_name}</h5>
                <div class="metric-line">期間平均: <strong>{avg_val:.1f} {opt['unit']}</strong></div>
                <div class="metric-line">直近週実績: <strong>{recent_val:.1f} {opt['unit']}</strong></div>
                <div class="metric-line">目標: <strong>{f'{target_val:.1f}' if target_val else '--'} {opt['unit']}</strong></div>
                <div class="achievement" style="color: {color};">達成率: <strong>{achievement:.1f}%</strong></div>
                {bed_info_html}
            </div>
            """
        
        return f'<div class="grid-container">{cards_html}</div>'
        
    except Exception as e:
        logger.error(f"メトリクスタブコンテンツ生成エラー: {e}", exc_info=True)
        return '<div>エラー: コンテンツ生成に失敗しました</div>'

def generate_action_tab_content(action_data, dashboard_type):
    """アクション提案タブのコンテンツ生成（詳細版）"""
    try:
        # 詳細版HTMLを生成するために unified_html_export を使用
        from unified_html_export import generate_unified_html_export
        
        action_results = action_data.get('action_results', [])
        hospital_targets = action_data.get('hospital_targets', {})
        
        # 詳細版HTMLを生成
        full_html = generate_unified_html_export(
            action_results, 
            "", # period_descは親から渡されるので空文字
            hospital_targets, 
            dashboard_type
        )
        
        # HTMLから必要な部分（actions-grid）を抽出
        if full_html and '<div class="actions-grid">' in full_html:
            start = full_html.find('<div class="hospital-summary">')
            end = full_html.find('</body>')
            if start != -1 and end != -1:
                # 病院サマリーとアクションカードの部分を抽出
                content = full_html[start:end]
                # containerやh1などの重複要素を除去
                content = content.replace('<div class="container">', '')
                content = content.replace('</div>\n</body>', '')
                return content
        
        # フォールバック: 抽出に失敗した場合は簡易版を返す
        return generate_simple_action_content(action_results, hospital_targets, dashboard_type)
        
    except Exception as e:
        logger.error(f"アクション詳細タブコンテンツ生成エラー: {e}", exc_info=True)
        return '<div>エラー: アクションコンテンツ生成に失敗しました</div>'

def generate_simple_action_content(action_results, hospital_targets, dashboard_type):
    """簡易版アクションコンテンツ（フォールバック用）"""
    # 既存のコードをここに移動
    is_department = dashboard_type == "department"
    cards_html = ""
    for result in action_results:
        kpi = result['kpi']
        action_result = result['action_result']
        color = action_result.get('color', '#b3b9b3')
        action = action_result.get('action', '要確認')
        reasoning = action_result.get('reasoning', '')
        
        item_name = kpi.get('dept_name' if is_department else 'ward_name', 'Unknown')
        census_val = kpi.get('daily_avg_census', 0)
        achievement = kpi.get('daily_census_achievement', 0)
        
        cards_html += f"""
        <div class="action-card" style="border-left-color: {color};">
            <h5>{item_name}</h5>
            <div class="action-summary">
                <strong>推奨アクション:</strong> {action}
            </div>
            <div class="action-details">
                {reasoning}
            </div>
            <div style="margin-top: 10px; font-size: 0.9em;">
                在院患者数: <strong>{census_val:.1f}人</strong> (達成率: <strong>{achievement:.1f}%</strong>)
            </div>
        </div>
        """
    
    return f'<div>{cards_html}</div>'

def validate_export_data(data, data_type="metrics"):
    """エクスポートデータの妥当性チェック"""
    try:
        if not data:
            return False, f"{data_type}データが空です"
        
        if data_type == "metrics":
            if not isinstance(data, list):
                return False, "メトリクスデータはリスト形式である必要があります"
            
            required_fields = ['daily_avg_census', 'daily_census_achievement']
            for item in data:
                if not all(field in item for field in required_fields):
                    return False, f"必須フィールドが不足しています: {required_fields}"
        
        elif data_type == "action":
            if not isinstance(data, list):
                return False, "アクションデータはリスト形式である必要があります"
            
            for result in data:
                if not all(key in result for key in ['kpi', 'action_result']):
                    return False, "アクション結果の構造が不正です"
        
        return True, "データ検証OK"
        
    except Exception as e:
        logger.error(f"データ検証エラー: {e}")
        return False, f"データ検証中にエラー: {str(e)}"

def get_export_filename(dashboard_type, content_type, period_desc=""):
    """エクスポートファイル名生成"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        dashboard_prefix = "dept" if dashboard_type == "department" else "ward"
        content_suffix = {
            "metrics": "metrics",
            "action": "action",
            "combined": "combined"
        }.get(content_type, "export")
        
        period_suffix = period_desc.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "")
        
        return f"{dashboard_prefix}_{content_suffix}_{period_suffix}_{timestamp}.html"
        
    except Exception as e:
        logger.error(f"ファイル名生成エラー: {e}")
        return f"dashboard_export_{timestamp}.html"