import pandas as pd
import numpy as np
from datetime import datetime
import logging
import urllib.parse
from typing import List, Dict, Optional
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

def generate_all_in_one_html_report(df, target_data, period="直近12週", high_score_html=None):
    
    # ログを出力して、この関数が呼ばれたことを確認します
    import logging
    logger = logging.getLogger(__name__)
    logger.critical("★★★★★ テスト用のレポート生成関数が呼び出されました ★★★★★")

    # ボタンが4つある、ごく簡単なHTMLを返します
    test_html = """
    <!DOCTYPE html>
    <html lang="ja">
    <head><title>最小構成テスト</title></head>
    <body>
        <h1>これは最小構成のテストページです</h1>
        <div class="quick-buttons">
            <button>🏥 病院全体</button>
            <button>🩺 診療科別</button>
            <button>🏢 病棟別</button>
            <button>🏆 ハイスコア部門</button>
        </div>
        <p>このページに「ハイスコア部門」ボタンが表示されていれば、関数の呼び出しは正常です。</p>
        <p>表示されていない場合、問題はこの関数の外側（呼び出し元やキャッシュ）にあります。</p>
    </body>
    </html>
    """
    return test_html
        
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
# ========================
# Phase1: ハイスコア計算機能
# ========================

def calculate_high_score(df, target_data, entity_name, entity_type, start_date, end_date, group_col=None):
    """
    診療科・病棟のハイスコアを計算（100点満点）【計算方法修正版】
    """
    try:
        # 基本KPI取得
        if entity_type == 'dept':
            kpi = calculate_department_kpis(df, target_data, entity_name, entity_name, start_date, end_date, group_col)
        else:
            kpi = calculate_ward_kpis(df, target_data, entity_name, entity_name, start_date, end_date, group_col)
        
        if not kpi or not kpi.get('daily_census_target'):
            return None
        
        target_value = kpi['daily_census_target']
        
        # 対象データフィルタリング
        entity_df = df[df[group_col] == entity_name].copy() if group_col and entity_name else df.copy()
        if entity_df.empty:
            return None

        # ★ 修正点 1: 「直近7日間」のデータを正確に切り出す
        recent_week_end = end_date
        recent_week_start = end_date - pd.Timedelta(days=6)
        recent_week_df = entity_df[
            (entity_df['日付'] >= recent_week_start) & 
            (entity_df['日付'] <= recent_week_end)
        ]
        
        if recent_week_df.empty:
            return None # 直近週のデータがなければ計算不可
            
        # ★ 修正点 2: 「直近週の平均在院患者数」を7日間平均で計算
        latest_week_avg_census = recent_week_df['在院患者数'].mean()

        # 1. 直近週達成度（50点）- 新しい計算方法を適用
        latest_achievement_rate = (latest_week_avg_census / target_value) * 100
        achievement_score = _calculate_achievement_score(latest_achievement_rate)

        # 2. 改善度（25点）- 比較対象期間を「直近週より前」に設定
        period_before_recent_week_df = entity_df[
            (entity_df['日付'] >= start_date) & 
            (entity_df['日付'] < recent_week_start)
        ]
        
        improvement_rate = 0
        if not period_before_recent_week_df.empty:
            period_avg = period_before_recent_week_df['在院患者数'].mean()
            if period_avg > 0:
                improvement_rate = ((latest_week_avg_census - period_avg) / period_avg) * 100
        improvement_score = _calculate_improvement_score(improvement_rate)

        # --- 安定性・持続性のための週次データ作成（この部分は変更なし） ---
        period_df = entity_df[(entity_df['日付'] >= start_date) & (entity_df['日付'] <= end_date)].copy()
        if period_df.empty or len(period_df) < 7: return None
        
        period_df['週番号'] = period_df['日付'].dt.isocalendar().week
        period_df['年'] = period_df['日付'].dt.year
        period_df['年週'] = period_df['年'].astype(str) + '-W' + period_df['週番号'].astype(str).str.zfill(2)
        
        weekly_data = period_df.groupby('年週').agg(
            {'在院患者数': 'mean', '日付': 'max'}
        ).sort_values('日付').reset_index()
        
        if len(weekly_data) < 2: return None
        
        # 3. 安定性（15点）
        recent_3weeks = weekly_data['在院患者数'].tail(3)
        stability_score = _calculate_stability_score(recent_3weeks)
        
        # 4. 持続性（10点）
        sustainability_score = _calculate_sustainability_score(weekly_data, target_value)
        
        # 5. 病棟特別項目（病棟のみ、5点）
        bed_efficiency_score = 0
        if entity_type == 'ward' and kpi.get('bed_count', 0) > 0:
            bed_utilization = (latest_week_avg_census / kpi['bed_count']) * 100
            bed_efficiency_score = _calculate_bed_efficiency_score(bed_utilization, latest_achievement_rate)
        
        # 総合スコア計算
        total_score = achievement_score + improvement_score + stability_score + sustainability_score + bed_efficiency_score
        
        return {
            'entity_name': entity_name,
            'entity_type': entity_type,
            'total_score': min(105, max(0, total_score)),
            'achievement_score': achievement_score,
            'improvement_score': improvement_score,
            'stability_score': stability_score,
            'sustainability_score': sustainability_score,
            'bed_efficiency_score': bed_efficiency_score,
            'latest_achievement_rate': latest_achievement_rate, # ★ 修正された値
            'improvement_rate': improvement_rate,
            'latest_inpatients': latest_week_avg_census, # ★ 修正された値
            'target_inpatients': target_value,
            'period_avg': period_avg if 'period_avg' in locals() else 0,
            'bed_utilization': (latest_week_avg_census / kpi.get('bed_count', 1)) * 100 if entity_type == 'ward' else 0
        }
        
    except Exception as e:
        logger.error(f"ハイスコア計算エラー ({entity_name}): {e}")
        return None

def _calculate_achievement_score(achievement_rate: float) -> float:
    """直近週達成度スコア計算（50点満点）"""
    if achievement_rate >= 110:
        return 50
    elif achievement_rate >= 105:
        return 45
    elif achievement_rate >= 100:
        return 40
    elif achievement_rate >= 98:
        return 35
    elif achievement_rate >= 95:
        return 25
    elif achievement_rate >= 90:
        return 15
    elif achievement_rate >= 85:
        return 5
    else:
        return 0

def _calculate_improvement_score(improvement_rate: float) -> float:
    """改善度スコア計算（25点満点）"""
    if improvement_rate >= 15:
        return 25
    elif improvement_rate >= 10:
        return 20
    elif improvement_rate >= 5:
        return 15
    elif improvement_rate >= 2:
        return 10
    elif improvement_rate >= -2:
        return 5
    elif improvement_rate >= -5:
        return 3
    elif improvement_rate >= -10:
        return 1
    else:
        return 0

def _calculate_stability_score(recent_values: pd.Series) -> float:
    """安定性スコア計算（15点満点）"""
    if len(recent_values) < 2:
        return 0
    
    try:
        mean_val = recent_values.mean()
        if mean_val <= 0:
            return 0
        
        cv = (recent_values.std() / mean_val) * 100  # 変動係数
        
        if cv < 5:
            return 15
        elif cv < 10:
            return 12
        elif cv < 15:
            return 8
        elif cv < 20:
            return 4
        else:
            return 0
    except:
        return 0

def _calculate_sustainability_score(weekly_data: pd.DataFrame, target_value: float) -> float:
    """持続性スコア計算（10点満点）"""
    if len(weekly_data) < 2 or target_value <= 0:
        return 0
    
    try:
        # 達成率と改善フラグの計算
        weekly_data = weekly_data.copy()
        weekly_data['achievement_rate'] = (weekly_data['在院患者数'] / target_value) * 100
        weekly_data['prev_value'] = weekly_data['在院患者数'].shift(1)
        weekly_data['improvement'] = weekly_data['在院患者数'] > weekly_data['prev_value']
        
        # 直近4週のデータ（または全データ）
        recent_4weeks = weekly_data.tail(4)
        
        scores = []
        
        # 継続改善系チェック
        consecutive_improvements = 0
        for i in range(len(recent_4weeks) - 1, 0, -1):
            if pd.notna(recent_4weeks.iloc[i]['improvement']) and recent_4weeks.iloc[i]['improvement']:
                consecutive_improvements += 1
            else:
                break
        
        if consecutive_improvements >= 4:
            scores.append(10)
        elif consecutive_improvements >= 3:
            scores.append(7)
        elif consecutive_improvements >= 2:
            scores.append(4)
        
        # 継続達成系チェック
        consecutive_achievements = 0
        for i in range(len(recent_4weeks) - 1, -1, -1):
            if recent_4weeks.iloc[i]['achievement_rate'] >= 98:
                consecutive_achievements += 1
            else:
                break
        
        if consecutive_achievements >= 4:
            scores.append(10)
        elif consecutive_achievements >= 3:
            scores.append(7)
        elif consecutive_achievements >= 2:
            scores.append(4)
        
        # 持続高パフォーマンス系チェック
        if len(recent_4weeks) >= 4:
            avg_achievement = recent_4weeks['achievement_rate'].mean()
            achievements_count = (recent_4weeks['achievement_rate'] >= 98).sum()
            no_below_90 = (recent_4weeks['achievement_rate'] >= 90).all()
            
            if avg_achievement >= 98:
                scores.append(6)
            elif achievements_count >= 3:
                scores.append(4)
            elif no_below_90:
                scores.append(3)
        
        return max(scores) if scores else 0
        
    except Exception as e:
        logger.error(f"持続性スコア計算エラー: {e}")
        return 0

def _calculate_bed_efficiency_score(bed_utilization: float, achievement_rate: float) -> float:
    """病床効率スコア計算（5点満点）"""
    try:
        if achievement_rate >= 98:  # 目標達成時
            if bed_utilization >= 95:
                return 5
            elif bed_utilization >= 90:
                return 3
        
        # 注：利用率向上チェック（+10%以上）は別途前期データが必要
        # 現時点では基本的な効率のみで評価
        return 0
        
    except:
        return 0

def calculate_all_high_scores(df, target_data, period="直近12週"):
    """
    全ての診療科・病棟のハイスコアを計算
    
    Returns:
        tuple: (dept_scores, ward_scores)
    """
    try:
        start_date, end_date, _ = get_period_dates(df, period)
        if not start_date:
            return [], []
        
        dept_scores = []
        ward_scores = []
        
        # 診療科スコア計算
        dept_col = '診療科名'
        if dept_col in df.columns:
            departments = sorted(df[dept_col].dropna().unique())
            for dept_name in departments:
                score = calculate_high_score(df, target_data, dept_name, 'dept', start_date, end_date, dept_col)
                if score:
                    dept_scores.append(score)
        
        # 病棟スコア計算
        try:
            all_wards = get_target_ward_list(target_data, EXCLUDED_WARDS)
            for ward_code, ward_name in all_wards:
                score = calculate_high_score(df, target_data, ward_code, 'ward', start_date, end_date, '病棟コード')
                if score:
                    score['display_name'] = ward_name  # 表示用の名前を追加
                    ward_scores.append(score)
        except Exception as e:
            logger.error(f"病棟スコア計算エラー: {e}")
        
        # スコア順でソート
        dept_scores.sort(key=lambda x: x['total_score'], reverse=True)
        ward_scores.sort(key=lambda x: x['total_score'], reverse=True)
        
        logger.info(f"ハイスコア計算完了: 診療科{len(dept_scores)}件, 病棟{len(ward_scores)}件")
        return dept_scores, ward_scores
        
    except Exception as e:
        logger.error(f"全ハイスコア計算エラー: {e}")
        return [], []

def generate_all_in_one_html_report_with_high_score(df, target_data, period="直近12週"):
    """
    ハイスコア機能付き統合HTMLレポートを生成する（新方式のラッパー関数）
    不安定なHTMLの書き換えを完全に撤廃。
    """
    try:
        logger.info("🏆 [新方式]ハイスコア統合レポート生成開始")

        # 1. ハイスコアデータを計算
        dept_scores, ward_scores = calculate_all_high_scores(df, target_data, period)
        logger.info(f"📊 スコア計算完了: 診療科{len(dept_scores)}件, 病棟{len(ward_scores)}件")

        # 2. ハイスコアのHTMLコンテンツを生成
        high_score_html = create_high_score_html_section(dept_scores, ward_scores)
        if high_score_html:
            logger.info("✅ ハイスコアのHTMLセクションを生成しました。")

        # 3. 修正されたメイン関数を呼び出し、ハイスコアHTMLを引数として渡すだけ！
        final_html = generate_all_in_one_html_report(
            df,
            target_data,
            period,
            high_score_html=high_score_html # ★ここで生成したHTMLを渡します
        )

        logger.info("✅✅✅ [新方式]統合レポートの生成が完了しました。")
        return final_html

    except Exception as e:
        logger.error(f"[新方式]ハイスコア統合レポート生成中にエラー: {e}", exc_info=True)
        return "<html><body>レポート生成中にエラーが発生しました。</body></html>"

def _generate_ranking_list_html(scores: List[Dict], entity_type: str) -> str:
    """ランキングリストHTML生成"""
    if not scores:
        return "<div class='ranking-list'><p>データがありません</p></div>"
    
    medals = ["🥇", "🥈", "🥉"]
    html = "<div class='ranking-list'>"
    
    for i, score in enumerate(scores):
        name = score.get('display_name', score['entity_name'])
        medal = medals[i] if i < 3 else f"{i+1}位"
        achievement = score['latest_achievement_rate']
        
        html += f"""
        <div class="ranking-item rank-{i+1}">
            <span class="medal">{medal}</span>
            <div class="ranking-info">
                <div class="name">{name}</div>
                <div class="detail">達成率 {achievement:.1f}%</div>
            </div>
            <div class="score">{score['total_score']:.0f}点</div>
        </div>
        """
    
    html += "</div>"
    return html

def _generate_weekly_highlights(dept_scores: List[Dict], ward_scores: List[Dict]) -> str:
    """週次ハイライト生成"""
    highlights = []
    
    try:
        # 診療科のトップパフォーマー
        if dept_scores:
            top_dept = dept_scores[0]
            if top_dept['total_score'] >= 80:
                highlights.append(f"🌟 {top_dept['entity_name']}が診療科部門で{top_dept['total_score']:.0f}点の高スコアを記録！")
            elif top_dept['improvement_rate'] > 10:
                highlights.append(f"📈 {top_dept['entity_name']}が期間平均比+{top_dept['improvement_rate']:.1f}%の大幅改善！")
        
        # 病棟のトップパフォーマー
        if ward_scores:
            top_ward = ward_scores[0]
            ward_name = top_ward.get('display_name', top_ward['entity_name'])
            if top_ward['total_score'] >= 80:
                highlights.append(f"🏆 {ward_name}が病棟部門で{top_ward['total_score']:.0f}点の優秀な成績！")
            elif top_ward.get('bed_efficiency_score', 0) > 0:
                highlights.append(f"🎯 {ward_name}は病床効率も優秀で総合力の高さを発揮！")
        
        # 全体的な傾向
        high_achievers = len([s for s in dept_scores + ward_scores if s['latest_achievement_rate'] >= 98])
        if high_achievers > 0:
            highlights.append(f"✨ 今週は{high_achievers}部門が目標達成率98%以上を記録！")
        
        if not highlights:
            highlights.append("🔥 各部門で着実な改善努力が続いています！")
        
        return "<br>".join([f"• {h}" for h in highlights[:3]])  # 最大3つまで
        
    except Exception as e:
        logger.error(f"ハイライト生成エラー: {e}")
        return "• 今週も各部門で頑張りが見られました！"

def _integrate_high_score_to_html(base_html: str, high_score_html: str) -> str:
    """基本HTMLにハイスコア機能を統合（JavaScript修正版）"""
    try:
        logger.info("🔧 ハイスコア統合開始...")
        
        # ハイスコアビューをコンテンツに追加
        high_score_view = f'<div id="view-high-score" class="view-content">{high_score_html}</div>'
        logger.info(f"📝 ハイスコアビュー生成完了: {len(high_score_view)}文字")
        
        # クイックボタンにハイスコアボタンを追加
        high_score_button = '''<button class="quick-button" onclick="showView('view-high-score')">
                            <span>🏆</span> ハイスコア部門
                        </button>'''
        
        modified_html = base_html
        
        # === ボタン追加 ===
        ward_button_pattern = '<span>🏢</span> 病棟別'
        if ward_button_pattern in modified_html:
            ward_button_end = modified_html.find('</button>', modified_html.find(ward_button_pattern))
            if ward_button_end != -1:
                insert_pos = ward_button_end + len('</button>')
                modified_html = (modified_html[:insert_pos] + 
                               '\n                        ' + high_score_button + 
                               modified_html[insert_pos:])
                logger.info("✅ ハイスコアボタン追加完了")
        
        # === ビューコンテンツ追加 ===
        content_area_pattern = '<div class="content-area">'
        content_area_pos = modified_html.find(content_area_pattern)
        
        if content_area_pos != -1:
            # 既存のビューコンテンツの後に追加
            content_area_end = modified_html.find('</div>\n', content_area_pos)
            if content_area_end != -1:
                # 最後の</div>の前に挿入
                last_view_end = modified_html.rfind('</div>', content_area_pos, content_area_end)
                if last_view_end != -1:
                    insert_pos = last_view_end + len('</div>')
                    modified_html = (modified_html[:insert_pos] + 
                                   '\n                    ' + high_score_view + 
                                   modified_html[insert_pos:])
                    logger.info("✅ ハイスコアビュー追加完了")
        
        # === JavaScript修正（シンプル版） ===
        # 既存のshowView関数を拡張する方法に変更
        js_extension = """
                // ハイスコア機能の拡張
                (function() {
                    // 元のshowView関数を保存
                    var originalShowView = window.showView;
                    
                    // showView関数を拡張
                    window.showView = function(viewId) {
                        console.log('🏆 showView called:', viewId);
                        
                        // 全てのビューを非表示
                        document.querySelectorAll('.view-content').forEach(function(content) {
                            content.classList.remove('active');
                        });
                        
                        // 指定されたビューを表示
                        var targetView = document.getElementById(viewId);
                        if (targetView) {
                            targetView.classList.add('active');
                            console.log('✅ View activated:', viewId);
                            
                            // Plotlyチャートの再描画
                            setTimeout(function() {
                                window.dispatchEvent(new Event('resize'));
                                if (window.Plotly) {
                                    var plots = targetView.querySelectorAll('.plotly-graph-div');
                                    plots.forEach(function(plot) {
                                        Plotly.Plots.resize(plot);
                                    });
                                }
                            }, 100);
                        }
                        
                        // クイックボタンのアクティブ状態を更新
                        document.querySelectorAll('.quick-button').forEach(function(btn) {
                            btn.classList.remove('active');
                        });
                        
                        // 対応するボタンをアクティブに
                        if (viewId === 'view-high-score') {
                            var buttons = document.querySelectorAll('.quick-button');
                            buttons.forEach(function(btn) {
                                if (btn.textContent.includes('ハイスコア部門')) {
                                    btn.classList.add('active');
                                }
                            });
                            
                            // セレクターを隠す
                            var deptWrapper = document.getElementById('dept-selector-wrapper');
                            var wardWrapper = document.getElementById('ward-selector-wrapper');
                            if (deptWrapper) deptWrapper.style.display = 'none';
                            if (wardWrapper) wardWrapper.style.display = 'none';
                            
                        } else if (viewId === 'view-all') {
                            document.querySelector('.quick-button').classList.add('active');
                            // セレクターを隠す
                            var deptWrapper = document.getElementById('dept-selector-wrapper');
                            var wardWrapper = document.getElementById('ward-selector-wrapper');
                            if (deptWrapper) deptWrapper.style.display = 'none';
                            if (wardWrapper) wardWrapper.style.display = 'none';
                        }
                    };
                    
                    // デバッグ: ページ読み込み時の確認
                    window.addEventListener('DOMContentLoaded', function() {
                        console.log('🔍 ハイスコア機能チェック...');
                        var highScoreView = document.getElementById('view-high-score');
                        var highScoreButton = null;
                        document.querySelectorAll('.quick-button').forEach(function(btn) {
                            if (btn.textContent.includes('ハイスコア部門')) {
                                highScoreButton = btn;
                            }
                        });
                        
                        console.log('ハイスコアビュー:', highScoreView ? '✅ 存在' : '❌ なし');
                        console.log('ハイスコアボタン:', highScoreButton ? '✅ 存在' : '❌ なし');
                        
                        if (highScoreView && highScoreButton) {
                            console.log('✅ ハイスコア機能は正常に組み込まれています');
                            
                            // ボタンクリックのテスト
                            highScoreButton.addEventListener('click', function(e) {
                                console.log('🏆 ハイスコアボタンがクリックされました');
                            });
                        }
                    });
                })();
        """
        
        # </script>タグの直前にJavaScriptを挿入
        script_end = modified_html.rfind('</script>')
        if script_end != -1:
            modified_html = (modified_html[:script_end] + 
                           '\n' + js_extension + '\n' + 
                           modified_html[script_end:])
            logger.info("✅ JavaScript拡張追加完了")
        
        # ハイスコア用CSSを追加
        high_score_css = _get_high_score_css()
        modified_html = modified_html.replace('</style>', f'{high_score_css}\n            </style>')
        
        logger.info("🎉 ハイスコア統合完了")
        return modified_html
        
    except Exception as e:
        logger.error(f"❌ HTML統合エラー: {e}", exc_info=True)
        return base_html

def _get_high_score_css() -> str:
    """ハイスコア部門用CSS（表示問題修正版）"""
    return """
    /* === ハイスコア部門専用スタイル（修正版） === */
    .high-score-container {
        max-width: 1000px;
        margin: 0 auto;
        padding: 20px;
    }
    
    /* 重要: ビューの表示制御を確実にする */
    .view-content {
        display: none !important;
        opacity: 0;
        transition: opacity 0.3s ease-in-out;
    }
    
    .view-content.active {
        display: block !important;
        opacity: 1;
        animation: fadeIn 0.3s ease-in-out;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    /* ハイスコア専用のビュー表示 */
    #view-high-score {
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        min-height: 400px;
    }
    
    #view-high-score.active {
        display: block !important;
    }
    
    .ranking-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 30px;
        margin-bottom: 30px;
    }
    
    .ranking-section h3 {
        color: var(--primary-color, #5B5FDE);
        margin-bottom: 20px;
        font-size: 1.2em;
        font-weight: 700;
        text-align: center;
        padding: 10px;
        background: linear-gradient(135deg, rgba(91, 95, 222, 0.1) 0%, rgba(91, 95, 222, 0.05) 100%);
        border-radius: 8px;
    }
    
    .ranking-list {
        background: var(--gray-50, #F9FAFB);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid var(--gray-200, #E5E7EB);
        min-height: 200px;
    }
    
    .ranking-item {
        display: flex;
        align-items: center;
        gap: 15px;
        padding: 15px;
        background: white;
        border-radius: 8px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.2s ease;
        border-left: 4px solid var(--gray-300, #D1D5DB);
    }
    
    .ranking-item:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    .ranking-item.rank-1 {
        border-left-color: #FFD700;
        background: linear-gradient(135deg, rgba(255, 215, 0, 0.15) 0%, rgba(255, 215, 0, 0.05) 100%);
    }
    
    .ranking-item.rank-2 {
        border-left-color: #C0C0C0;
        background: linear-gradient(135deg, rgba(192, 192, 192, 0.15) 0%, rgba(192, 192, 192, 0.05) 100%);
    }
    
    .ranking-item.rank-3 {
        border-left-color: #CD7F32;
        background: linear-gradient(135deg, rgba(205, 127, 50, 0.15) 0%, rgba(205, 127, 50, 0.05) 100%);
    }
    
    .medal {
        font-size: 1.8em;
        min-width: 50px;
        text-align: center;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
    }
    
    .ranking-info {
        flex: 1;
    }
    
    .ranking-info .name {
        font-weight: 700;
        color: var(--gray-800, #1F2937);
        font-size: 1em;
        margin-bottom: 4px;
        line-height: 1.2;
    }
    
    .ranking-info .detail {
        font-size: 0.85em;
        color: var(--gray-600, #4B5563);
        line-height: 1.2;
    }
    
    .score {
        font-size: 1.6em;
        font-weight: 700;
        color: var(--primary-color, #5B5FDE);
        text-align: center;
        min-width: 70px;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .period-info {
        text-align: center;
        color: var(--gray-600, #4B5563);
        margin-bottom: 30px;
        font-size: 0.95em;
        padding: 12px;
        background: var(--gray-50, #F9FAFB);
        border-radius: 8px;
        border: 1px solid var(--gray-200, #E5E7EB);
        font-weight: 500;
    }
    
    .summary-section {
        background: linear-gradient(135deg, rgba(91, 95, 222, 0.1) 0%, rgba(91, 95, 222, 0.05) 100%);
        border-left: 5px solid var(--primary-color, #5B5FDE);
        padding: 25px;
        border-radius: 12px;
        margin-top: 30px;
    }
    
    .summary-section h3 {
        color: var(--primary-dark, #4347B8);
        margin-bottom: 15px;
        font-size: 1.1em;
        font-weight: 700;
    }
    
    .summary-section p {
        margin: 8px 0;
        color: var(--gray-700, #374151);
        line-height: 1.6;
    }
    
    /* デバッグ情報スタイル */
    .debug-info {
        margin-top: 20px;
        padding: 15px;
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        font-size: 0.85em;
        color: #6c757d;
    }
    
    /* ローディング状態 */
    .ranking-list p {
        text-align: center;
        color: var(--gray-500, #6B7280);
        font-style: italic;
        padding: 20px;
    }
    
    /* アクティブボタンのスタイル強化 */
    .quick-button.active {
        background: var(--primary-color, #5B5FDE) !important;
        color: white !important;
        border-color: var(--primary-color, #5B5FDE) !important;
        box-shadow: 0 4px 8px rgba(91, 95, 222, 0.3) !important;
    }
    
    /* レスポンシブ対応 */
    @media (max-width: 768px) {
        .high-score-container {
            padding: 10px;
        }
        
        .ranking-grid {
            grid-template-columns: 1fr;
            gap: 20px;
        }
        
        .ranking-item {
            padding: 12px;
            gap: 10px;
        }
        
        .medal {
            font-size: 1.5em;
            min-width: 40px;
        }
        
        .ranking-info .name {
            font-size: 0.95em;
        }
        
        .score {
            font-size: 1.3em;
            min-width: 55px;
        }
        
        .summary-section {
            padding: 20px;
        }
    }
    
    @media (max-width: 480px) {
        .ranking-grid {
            gap: 15px;
        }
        
        .ranking-item {
            padding: 10px;
            gap: 8px;
        }
        
        .medal {
            font-size: 1.3em;
            min-width: 35px;
        }
        
        .score {
            font-size: 1.1em;
            min-width: 45px;
        }
    }
    """
    
def _get_enhanced_javascript() -> str:
    """強化されたJavaScript（競合回避版）"""
    return """
        // ハイスコア機能用JavaScript（競合回避版）
        
        // 既存の関数を上書きしないよう、新しい名前で定義
        function showViewEnhanced(viewId) {
            console.log('🏆 showViewEnhanced called with:', viewId);
            
            try {
                // 全てのビューを非表示
                const allViews = document.querySelectorAll('.view-content');
                allViews.forEach(content => {
                    content.classList.remove('active');
                    content.style.display = 'none';
                    console.log('Hidden view:', content.id);
                });
                
                // 指定されたビューを表示
                const targetView = document.getElementById(viewId);
                if (targetView) {
                    targetView.classList.add('active');
                    targetView.style.display = 'block';
                    console.log('✅ Showing view:', viewId);
                    
                    // ハイスコア専用の処理
                    if (viewId === 'view-high-score') {
                        console.log('🏆 ハイスコアビューアクティブ化完了');
                        
                        // スムーズスクロール
                        targetView.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        
                        // コンテンツの可視性を確認
                        setTimeout(() => {
                            const container = targetView.querySelector('.high-score-container');
                            if (container) {
                                console.log('✅ ハイスコアコンテナ確認OK');
                            } else {
                                console.error('❌ ハイスコアコンテナが見つかりません');
                            }
                        }, 100);
                    }
                    
                    // Plotlyチャートの再描画
                    setTimeout(function() {
                        window.dispatchEvent(new Event('resize'));
                        if (window.Plotly) {
                            const plots = targetView.querySelectorAll('.plotly-graph-div');
                            plots.forEach(plot => {
                                Plotly.Plots.resize(plot);
                            });
                        }
                    }, 200);
                    
                } else {
                    console.error('❌ View not found:', viewId);
                    // 利用可能なビューをデバッグ表示
                    const availableViews = Array.from(document.querySelectorAll('.view-content')).map(v => v.id);
                    console.log('Available views:', availableViews);
                    
                    // フォールバック: データがある場合は新しいビューを作成
                    if (viewId === 'view-high-score') {
                        console.log('🔧 ハイスコアビューの緊急作成を試行...');
                        createEmergencyHighScoreView();
                    }
                }
            } catch (error) {
                console.error('❌ showViewEnhanced error:', error);
            }
            
            // ボタンのアクティブ状態更新
            updateActiveButton(viewId);
        }
        
        // 緊急時のハイスコアビュー作成
        function createEmergencyHighScoreView() {
            const contentArea = document.querySelector('.content-area');
            if (contentArea) {
                const emergencyView = document.createElement('div');
                emergencyView.id = 'view-high-score';
                emergencyView.className = 'view-content active';
                emergencyView.innerHTML = `
                    <div class="high-score-container">
                        <div class="section">
                            <h2>🏆 週間ハイスコア TOP3</h2>
                            <p class="period-info">データを読み込んでいます...</p>
                            <div class="ranking-grid">
                                <div class="ranking-section">
                                    <h3>🩺 診療科部門</h3>
                                    <div class="ranking-list">
                                        <p>スコア計算中...</p>
                                    </div>
                                </div>
                                <div class="ranking-section">
                                    <h3>🏢 病棟部門</h3>
                                    <div class="ranking-list">
                                        <p>スコア計算中...</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                contentArea.appendChild(emergencyView);
                console.log('🆘 緊急ハイスコアビュー作成完了');
            }
        }
        
        // ボタンのアクティブ状態更新
        function updateActiveButton(viewId) {
            // 全ボタンを非アクティブに
            document.querySelectorAll('.quick-button').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // 対応するボタンをアクティブに
            if (viewId === 'view-high-score') {
                const highScoreButton = Array.from(document.querySelectorAll('.quick-button')).find(btn => 
                    btn.textContent.includes('ハイスコア部門')
                );
                if (highScoreButton) {
                    highScoreButton.classList.add('active');
                    console.log('✅ ハイスコアボタンをアクティブ化');
                }
                
                // セレクターを隠す
                const deptWrapper = document.getElementById('dept-selector-wrapper');
                const wardWrapper = document.getElementById('ward-selector-wrapper');
                if (deptWrapper) deptWrapper.style.display = 'none';
                if (wardWrapper) wardWrapper.style.display = 'none';
                
            } else if (viewId === 'view-all') {
                const allButton = document.querySelector('.quick-button');
                if (allButton) allButton.classList.add('active');
            }
        }
        
        // 既存のshowView関数を強化版で上書き
        if (typeof showView !== 'undefined') {
            const originalShowView = showView;
            showView = function(viewId) {
                console.log('🔄 showView intercepted, using enhanced version');
                return showViewEnhanced(viewId);
            };
        } else {
            window.showView = showViewEnhanced;
        }
        
        // ページ読み込み完了時の確認処理
        document.addEventListener('DOMContentLoaded', function() {
            console.log('🔍 DOM loaded. ハイスコア機能チェック開始...');
            
            setTimeout(() => {
                const highScoreView = document.getElementById('view-high-score');
                const highScoreButton = Array.from(document.querySelectorAll('.quick-button')).find(btn => 
                    btn.textContent.includes('ハイスコア部門')
                );
                
                console.log('ハイスコアビュー:', highScoreView ? '✅ 存在' : '❌ なし');
                console.log('ハイスコアボタン:', highScoreButton ? '✅ 存在' : '❌ なし');
                
                if (highScoreView) {
                    console.log('ハイスコアビューHTML長:', highScoreView.innerHTML.length);
                    console.log('ハイスコアビュークラス:', highScoreView.className);
                }
                
                // 全ビューの状況確認
                const allViews = document.querySelectorAll('.view-content');
                console.log('全ビュー数:', allViews.length);
                allViews.forEach(view => {
                    console.log(`- ${view.id}: ${view.classList.contains('active') ? 'active' : 'inactive'}`);
                });
                
            }, 500);
        });
        
        // ウィンドウリサイズ時の処理
        window.addEventListener('resize', function() {
            const activeView = document.querySelector('.view-content.active');
            if (activeView && activeView.id === 'view-high-score') {
                console.log('🏆 ハイスコアビューのリサイズ処理');
            }
        });
    """