# reporting/surgery_high_score_html.py
"""
手術ハイスコア機能のHTML出力・統合機能
"""

import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def generate_surgery_high_score_html(dept_scores: List[Dict[str, Any]], 
                                   period: str = "直近12週") -> str:
    """手術ハイスコアのHTML生成"""
    try:
        if not dept_scores:
            return _generate_empty_high_score_html()
        
        # TOP3抽出
        top3 = dept_scores[:3]
        
        # HTML生成
        html_content = f"""
        <div class="high-score-section">
            <h2>🏆 診療科別手術ハイスコア TOP3</h2>
            <p class="period-info">評価期間: {period} ({datetime.now().strftime('%m/%d')}まで)</p>
            
            <div class="ranking-grid">
                <div class="ranking-section">
                    <h3>🩺 診療科ランキング</h3>
                    <div class="ranking-list">
                        {_generate_ranking_cards_html(top3)}
                    </div>
                </div>
            </div>
            
            {_generate_score_details_html(top3)}
            {_generate_weekly_insights_html(dept_scores)}
        </div>
        """
        
        return html_content
        
    except Exception as e:
        logger.error(f"手術ハイスコアHTML生成エラー: {e}")
        return _generate_empty_high_score_html()


def _generate_ranking_cards_html(top3: List[Dict[str, Any]]) -> str:
    """ランキングカードのHTML生成"""
    try:
        cards_html = ""
        
        for i, dept in enumerate(top3):
            rank = i + 1
            medal = ["🥇", "🥈", "🥉"][i]
            rank_class = ["rank-1", "rank-2", "rank-3"][i]
            grade_color = _get_grade_color(dept['grade'])
            
            cards_html += f"""
            <div class="ranking-item {rank_class}">
                <span class="medal">{medal}</span>
                <div class="ranking-info">
                    <div class="name">{dept['display_name']}</div>
                    <div class="detail">達成率 {dept['achievement_rate']:.1f}%</div>
                </div>
                <div class="grade-badge" style="background-color: {grade_color};">
                    {dept['grade']}
                </div>
                <div class="score">{dept['total_score']:.0f}点</div>
            </div>
            """
        
        return cards_html
        
    except Exception as e:
        logger.error(f"ランキングカードHTML生成エラー: {e}")
        return "<p>ランキングデータの生成に失敗しました</p>"


def _generate_score_details_html(top3: List[Dict[str, Any]]) -> str:
    """スコア詳細のHTML生成"""
    try:
        details_html = '<div class="score-details-section">'
        
        for i, dept in enumerate(top3):
            rank = i + 1
            crown = "👑"
            score_components = dept.get('score_components', {})
            
            gas_score = score_components.get('gas_surgery_score', 0)
            total_cases_score = score_components.get('total_cases_score', 0) 
            total_hours_score = score_components.get('total_hours_score', 0)
            
            details_html += f"""
            <div class="score-detail-card">
                <h4>{crown} 診療科{rank}位：{dept['display_name']}</h4>
                <div class="score-breakdown">
                    <div class="score-total">📊 総合スコア：{dept['total_score']:.0f}点</div>
                    <div class="score-tree">
                        <div class="score-item">├─ 全身麻酔評価：{gas_score:.0f}点（達成率{dept['achievement_rate']:.0f}%）</div>
                        <div class="score-item">├─ 全手術件数評価：{total_cases_score:.0f}点（直近{dept['latest_total_cases']}件）</div>
                        <div class="score-item">├─ 総手術時間評価：{total_hours_score:.0f}点（{dept['latest_total_hours']:.1f}時間）</div>
                        <div class="score-item">└─ 改善度：{dept['improvement_rate']:+.1f}%</div>
                    </div>
                </div>
            </div>
            """
        
        details_html += '</div>'
        return details_html
        
    except Exception as e:
        logger.error(f"スコア詳細HTML生成エラー: {e}")
        return "<p>スコア詳細の生成に失敗しました</p>"


def _generate_weekly_insights_html(dept_scores: List[Dict[str, Any]]) -> str:
    """週間インサイトのHTML生成"""
    try:
        if not dept_scores:
            return ""
        
        # ハイライト抽出
        highlights = []
        
        # TOP診療科
        if dept_scores:
            top_dept = dept_scores[0]
            if top_dept['total_score'] >= 80:
                highlights.append(f"🌟 {top_dept['display_name']}が診療科で{top_dept['total_score']:.0f}点の高スコアを記録！")
            elif top_dept['improvement_rate'] > 10:
                highlights.append(f"📈 {top_dept['display_name']}が期間平均比+{top_dept['improvement_rate']:.1f}%の大幅改善！")
        
        # 目標達成診療科
        high_achievers = len([d for d in dept_scores if d['achievement_rate'] >= 98])
        if high_achievers > 0:
            highlights.append(f"✨ 今週は{high_achievers}診療科が目標達成率98%以上を記録！")
        
        # 手術時間効率
        high_hour_performers = [d for d in dept_scores if d['latest_total_hours'] > d['avg_total_hours'] * 1.2]
        if high_hour_performers:
            dept_name = high_hour_performers[0]['display_name']
            highlights.append(f"⚡ {dept_name}は手術時間も平均を大幅上回る高活動量を実現！")
        
        if not highlights:
            highlights.append("🔥 各診療科で着実な手術実績向上の努力が続いています！")
        
        insights_html = f"""
        <div class="weekly-insights">
            <h4>💡 今週のポイント</h4>
            {'<br>'.join([f"• {h}" for h in highlights[:3]])}
        </div>
        """
        
        return insights_html
        
    except Exception as e:
        logger.error(f"週間インサイト生成エラー: {e}")
        return ""


def _get_grade_color(grade: str) -> str:
    """グレードに応じた色を取得"""
    color_map = {
        'S': '#10B981',  # エメラルドグリーン
        'A': '#3B82F6',  # ブルー
        'B': '#F59E0B',  # オレンジ
        'C': '#EF4444',  # レッド
        'D': '#6B7280'   # グレー
    }
    return color_map.get(grade, '#6B7280')


def _generate_empty_high_score_html() -> str:
    """空のハイスコアHTML"""
    return """
    <div class="high-score-section">
        <h2>🏆 診療科別手術ハイスコア</h2>
        <p class="no-data">ハイスコアデータがありません。データと目標設定を確認してください。</p>
    </div>
    """


def integrate_surgery_high_score_to_dashboard_html(base_html: str, high_score_html: str) -> str:
    """既存ダッシュボードHTMLにハイスコア機能を統合"""
    try:
        logger.info("🔧 手術ハイスコア統合開始...")
        
        # ハイスコアビューをコンテンツに追加
        high_score_view = f'<div id="view-surgery-high-score" class="view-content">{high_score_html}</div>'
        logger.info(f"📝 手術ハイスコアビュー生成完了: {len(high_score_view)}文字")
        
        # クイックボタンにハイスコアボタンを追加
        high_score_button = '''<button class="quick-button" onclick="showView('view-surgery-high-score')">
                            <span>🏆</span> 手術ハイスコア
                        </button>'''
        
        modified_html = base_html
        
        # === ボタン追加 ===
        # 既存のボタンの後にハイスコアボタンを追加
        button_section_end = modified_html.find('</div>', modified_html.find('quick-button'))
        if button_section_end != -1:
            insert_pos = button_section_end
            modified_html = (modified_html[:insert_pos] + 
                           '\n                        ' + high_score_button + 
                           '\n                        ' +
                           modified_html[insert_pos:])
            logger.info("✅ ハイスコアボタン追加完了")
        
        # === ビューコンテンツ追加 ===
        views_end = modified_html.find('</div>', modified_html.rfind('view-content'))
        if views_end != -1:
            insert_pos = views_end + len('</div>')
            modified_html = (modified_html[:insert_pos] + 
                           '\n            ' + high_score_view + 
                           modified_html[insert_pos:])
            logger.info("✅ ハイスコアビューコンテンツ追加完了")
        
        # === JavaScript関数追加 ===
        if 'function showView(' in modified_html:
            logger.info("✅ showView関数は既存のものを利用")
        else:
            # showView関数が存在しない場合は追加
            js_function = '''
            function showView(viewId) {
                // 全てのビューを非表示
                const views = document.querySelectorAll('.view-content');
                views.forEach(view => view.style.display = 'none');
                
                // 指定されたビューを表示
                const targetView = document.getElementById(viewId);
                if (targetView) {
                    targetView.style.display = 'block';
                }
                
                // ボタンの状態更新
                const buttons = document.querySelectorAll('.quick-button');
                buttons.forEach(btn => btn.classList.remove('active'));
                
                // クリックされたボタンをアクティブに
                const clickedButton = document.querySelector(`[onclick="showView('${viewId}')"]`);
                if (clickedButton) {
                    clickedButton.classList.add('active');
                }
            }
            '''
            
            script_end = modified_html.rfind('</script>')
            if script_end != -1:
                modified_html = (modified_html[:script_end] + 
                               js_function + 
                               modified_html[script_end:])
                logger.info("✅ showView関数追加完了")
        
        # === CSS追加 ===
        high_score_css = '''
        .high-score-section {
            padding: 20px;
            background: #f8fafc;
            border-radius: 12px;
            margin: 20px 0;
        }
        
        .ranking-grid {
            display: grid;
            gap: 20px;
            margin: 20px 0;
        }
        
        .ranking-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .ranking-item {
            display: flex;
            align-items: center;
            background: white;
            padding: 16px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s ease;
        }
        
        .ranking-item:hover {
            transform: translateY(-2px);
        }
        
        .ranking-item.rank-1 {
            border-left: 4px solid #FFD700;
        }
        
        .ranking-item.rank-2 {
            border-left: 4px solid #C0C0C0;
        }
        
        .ranking-item.rank-3 {
            border-left: 4px solid #CD7F32;
        }
        
        .medal {
            font-size: 24px;
            margin-right: 12px;
        }
        
        .ranking-info {
            flex: 1;
            margin-right: 12px;
        }
        
        .ranking-info .name {
            font-weight: bold;
            font-size: 16px;
            margin-bottom: 4px;
        }
        
        .ranking-info .detail {
            color: #666;
            font-size: 14px;
        }
        
        .grade-badge {
            color: white;
            padding: 8px 12px;
            border-radius: 20px;
            font-weight: bold;
            margin-right: 12px;
        }
        
        .score {
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
        }
        
        .score-details-section {
            margin: 20px 0;
        }
        
        .score-detail-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            margin: 16px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .score-detail-card h4 {
            margin: 0 0 12px 0;
            color: #2c3e50;
        }
        
        .score-total {
            font-weight: bold;
            color: #3b82f6;
            margin-bottom: 8px;
        }
        
        .score-tree {
            font-family: monospace;
            color: #666;
            line-height: 1.6;
        }
        
        .weekly-insights {
            background: #e3f2fd;
            padding: 16px;
            border-radius: 8px;
            border-left: 4px solid #2196f3;
            margin: 20px 0;
        }
        
        .weekly-insights h4 {
            margin: 0 0 12px 0;
            color: #1976d2;
        }
        
        .no-data {
            text-align: center;
            color: #666;
            font-style: italic;
            padding: 40px;
        }
        
        @media (max-width: 768px) {
            .ranking-item {
                padding: 12px;
            }
            
            .medal {
                font-size: 20px;
            }
            
            .score {
                font-size: 16px;
            }
        }
        '''
        
        style_end = modified_html.rfind('</style>')
        if style_end != -1:
            modified_html = (modified_html[:style_end] + 
                           high_score_css + 
                           modified_html[style_end:])
            logger.info("✅ ハイスコア用CSS追加完了")
        
        logger.info("🎉 手術ハイスコア統合完了")
        return modified_html
        
    except Exception as e:
        logger.error(f"ハイスコア統合エラー: {e}")
        return base_html


def generate_complete_surgery_dashboard_html(df: pd.DataFrame, target_dict: Dict[str, float], 
                                           period: str = "直近12週") -> str:
    """完全な手術ダッシュボードHTMLを生成"""
    try:
        # ハイスコア計算
        from analysis.surgery_high_score import calculate_surgery_high_scores
        dept_scores = calculate_surgery_high_scores(df, target_dict, period)
        
        # ハイスコアHTML生成
        high_score_html = generate_surgery_high_score_html(dept_scores, period)
        
        # 基本ダッシュボードHTML（既存機能を活用）
        base_html = _generate_base_dashboard_html(df, target_dict, period)
        
        # ハイスコア機能を統合
        complete_html = integrate_surgery_high_score_to_dashboard_html(base_html, high_score_html)
        
        return complete_html
        
    except Exception as e:
        logger.error(f"完全手術ダッシュボードHTML生成エラー: {e}")
        return _generate_error_html(str(e))


def _generate_base_dashboard_html(df: pd.DataFrame, target_dict: Dict[str, float], period: str) -> str:
    """基本ダッシュボードHTMLを生成（簡易版）"""
    # 実際の実装では既存のHTML生成機能を呼び出し
    # ここでは簡単な構造のみ実装
    return f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>手術ダッシュボード（ハイスコア機能付き）</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .quick-buttons {{ display: flex; gap: 10px; margin: 20px 0; }}
            .quick-button {{ padding: 12px 20px; border: none; border-radius: 8px; background: #3b82f6; color: white; cursor: pointer; }}
            .quick-button:hover {{ background: #2563eb; }}
            .view-content {{ display: none; }}
            .view-content:first-child {{ display: block; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏥 手術ダッシュボード</h1>
            
            <div class="quick-buttons">
                <button class="quick-button" onclick="showView('view-main')">
                    <span>📊</span> メインダッシュボード
                </button>
            </div>
            
            <div id="view-main" class="view-content">
                <h2>📈 主要指標</h2>
                <p>期間: {period}</p>
                <p>データ件数: {len(df)}件</p>
            </div>
        </div>
        
        <script>
            // JavaScript functions will be added here
        </script>
    </body>
    </html>
    """


def _generate_error_html(error_message: str) -> str:
    """エラー用HTML"""
    return f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>エラー - 手術ダッシュボード</title>
    </head>
    <body>
        <h1>⚠️ エラーが発生しました</h1>
        <p>{error_message}</p>
    </body>
    </html>
    """