# components/ui_components.py
"""
UI関連のコンポーネント生成を担当するモジュール
ランキング表示、ハイライト、メトリクスカードなどの生成
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class UIComponentBuilder:
    """UI コンポーネント生成のメインクラス"""
    
    def __init__(self):
        self.medal_icons = ["🥇", "🥈", "🥉"]
    
    def build_ranking_section(self, scores: List[Dict], section_title: str, 
                            section_icon: str) -> str:
        """
        ランキングセクション全体のHTML生成
        
        Args:
            scores: スコアリスト（辞書形式）
            section_title: セクションタイトル
            section_icon: セクションアイコン
            
        Returns:
            ランキングセクションHTML
        """
        ranking_list_html = self._build_ranking_list(scores)
        
        return f"""
        <div class="ranking-section">
            <h3>{section_icon} {section_title}</h3>
            <div class="ranking-list">
                {ranking_list_html}
            </div>
        </div>
        """
    
    def _build_ranking_list(self, scores: List[Dict]) -> str:
        """ランキングリストのHTML生成"""
        if not scores:
            return "<p>データがありません</p>"
        
        html_parts = []
        for i, score in enumerate(scores[:3]):  # TOP3のみ表示
            medal = self.medal_icons[i] if i < 3 else f"{i+1}位"
            name = score.get('display_name', score['entity_name'])
            
            html_parts.append(f"""
                <div class="ranking-item rank-{i+1}">
                    <span class="medal">{medal}</span>
                    <div class="ranking-info">
                        <div class="name">{name}</div>
                        <div class="detail">達成率 {score['latest_achievement_rate']:.1f}%</div>
                    </div>
                    <div class="score">{score['total_score']:.0f}点</div>
                </div>
            """)
        
        return '\n'.join(html_parts)
    
    def build_high_score_view(self, dept_scores: List[Dict], 
                             ward_scores: List[Dict], period_desc: str) -> str:
        """
        ハイスコアビュー全体のHTML生成
        
        Args:
            dept_scores: 診療科スコアリスト
            ward_scores: 病棟スコアリスト
            period_desc: 期間説明
            
        Returns:
            ハイスコアビューHTML
        """
        try:
            # ランキンググリッド生成
            dept_ranking = self.build_ranking_section(dept_scores, "診療科部門", "🩺")
            ward_ranking = self.build_ranking_section(ward_scores, "病棟部門", "🏢")
            
            # スコア詳細生成
            score_details_html = self._build_score_details(dept_scores, ward_scores)
            
            # ハイライト生成
            highlights_html = self._build_weekly_highlights(dept_scores, ward_scores)
            
            return f"""
            <div class="section">
                <h2>🏆 週間ハイスコア TOP3</h2>
                <p class="period-info">評価期間: {period_desc}</p>
                <div class="ranking-grid">
                    {dept_ranking}
                    {ward_ranking}
                </div>
                {score_details_html}
                <div class="weekly-insights">
                    <h4>💡 今週のポイント</h4>
                    {highlights_html}
                </div>
            </div>
            """
            
        except Exception as e:
            logger.error(f"ハイスコアビュー生成エラー: {e}")
            return f"""
            <div class="section">
                <h2>🏆 週間ハイスコア TOP3</h2>
                <p>データの取得に失敗しました。</p>
            </div>
            """
    
    def _build_score_details(self, dept_scores: List[Dict], 
                           ward_scores: List[Dict]) -> str:
        """TOP1の詳細スコア表示HTML生成"""
        html = '<div class="score-details-section">'
        
        # 診療科部門TOP1の詳細
        if dept_scores:
            top_dept = dept_scores[0]
            html += f"""
            <div class="score-detail-card">
                <h4>👑 診療科部門1位：{top_dept['entity_name']}</h4>
                <div class="score-breakdown">
                    <div class="score-total">📊 総合スコア：{top_dept['total_score']:.0f}点</div>
                    <div class="score-tree">
                        <div class="score-item">├─ 直近週達成度：{top_dept['achievement_score']:.0f}点（達成率{top_dept['latest_achievement_rate']:.0f}%）</div>
                        <div class="score-item">├─ 改善度：{top_dept['improvement_score']:.0f}点（期間平均比{top_dept['improvement_rate']:+.0f}%）</div>
                        <div class="score-item">├─ 安定性：{top_dept['stability_score']:.0f}点</div>
                        <div class="score-item">└─ 持続性：{top_dept['sustainability_score']:.0f}点</div>
                    </div>
                </div>
            </div>
            """
        
        # 病棟部門TOP1の詳細
        if ward_scores:
            top_ward = ward_scores[0]
            ward_name = top_ward.get('display_name', top_ward['entity_name'])
            html += f"""
            <div class="score-detail-card">
                <h4>👑 病棟部門1位：{ward_name}</h4>
                <div class="score-breakdown">
                    <div class="score-total">📊 総合スコア：{top_ward['total_score']:.0f}点</div>
                    <div class="score-tree">
                        <div class="score-item">├─ 直近週達成度：{top_ward['achievement_score']:.0f}点（達成率{top_ward['latest_achievement_rate']:.0f}%）</div>
                        <div class="score-item">├─ 改善度：{top_ward['improvement_score']:.0f}点（期間平均比{top_ward['improvement_rate']:+.0f}%）</div>
                        <div class="score-item">├─ 安定性：{top_ward['stability_score']:.0f}点</div>
                        <div class="score-item">├─ 持続性：{top_ward['sustainability_score']:.0f}点</div>
                        <div class="score-item">└─ 病床効率加点：{top_ward['bed_efficiency_score']:.0f}点（利用率{top_ward.get('bed_utilization', 0):.0f}%）</div>
                    </div>
                </div>
            </div>
            """
        
        html += '</div>'
        return html
    
    def _build_weekly_highlights(self, dept_scores: List[Dict], 
                               ward_scores: List[Dict]) -> str:
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
    
    def build_highlight_banner(self, dept_scores: List[Dict], 
                             ward_scores: List[Dict]) -> str:
        """
        診療科・病棟別の週間ハイライトバナー生成
        
        Args:
            dept_scores: 診療科スコアリスト
            ward_scores: 病棟スコアリスト
            
        Returns:
            ハイライトバナーHTML
        """
        try:
            dept_highlights, ward_highlights = self._generate_weekly_highlights_by_type(
                dept_scores, ward_scores
            )
            
            return f"""
            <div class="weekly-highlights-container">
                <div class="weekly-highlight-banner dept-highlight">
                    <div class="highlight-container">
                        <div class="highlight-icon">💡</div>
                        <div class="highlight-content">
                            <strong>今週のポイント（診療科）</strong>
                            <span class="highlight-items">{dept_highlights}</span>
                        </div>
                    </div>
                </div>
                <div class="weekly-highlight-banner ward-highlight">
                    <div class="highlight-container">
                        <div class="highlight-icon">💡</div>
                        <div class="highlight-content">
                            <strong>今週のポイント（病棟）</strong>
                            <span class="highlight-items">{ward_highlights}</span>
                        </div>
                    </div>
                </div>
            </div>
            """
        except Exception as e:
            logger.error(f"ハイライトバナー生成エラー: {e}")
            return ""
    
    def _generate_weekly_highlights_by_type(self, dept_scores: List[Dict], 
                                          ward_scores: List[Dict]) -> tuple:
        """診療科・病棟別の週間ハイライト生成"""
        dept_highlights = []
        ward_highlights = []
        
        try:
            # 診療科のハイライト（最大2つ）
            if dept_scores:
                # TOP1の成果
                if dept_scores[0]['total_score'] >= 80:
                    dept_highlights.append(f"🏆 {dept_scores[0]['entity_name']}が{dept_scores[0]['total_score']:.0f}点の高スコア！")
                elif dept_scores[0]['improvement_rate'] > 10:
                    dept_highlights.append(f"📈 {dept_scores[0]['entity_name']}が期間平均比+{dept_scores[0]['improvement_rate']:.0f}%の改善！")
                
                # TOP2の成果も追加可能
                if len(dept_scores) > 1 and dept_scores[1]['total_score'] >= 75:
                    dept_highlights.append(f"🌟 {dept_scores[1]['entity_name']}も{dept_scores[1]['total_score']:.0f}点で好調！")
                
                # 達成率の高い診療科
                high_achievers_dept = [s for s in dept_scores if s['latest_achievement_rate'] >= 98]
                if len(high_achievers_dept) >= 3:
                    dept_highlights.append(f"✨ {len(high_achievers_dept)}診療科が目標達成率98%以上！")
            
            # 病棟のハイライト（最大2つ）
            if ward_scores:
                # TOP1の成果
                ward_name = ward_scores[0].get('display_name', ward_scores[0]['entity_name'])
                if ward_scores[0].get('bed_efficiency_score', 0) >= 3:
                    bed_util = ward_scores[0].get('bed_utilization', 0)
                    ward_highlights.append(f"🏥 {ward_name}が病床効率{bed_util:.0f}%で優秀！")
                elif ward_scores[0]['total_score'] >= 80:
                    ward_highlights.append(f"🎯 {ward_name}が{ward_scores[0]['total_score']:.0f}点の高評価！")
                
                # 持続性の高い病棟
                for ward in ward_scores[:3]:
                    if ward.get('sustainability_score', 0) >= 7:
                        ward_name = ward.get('display_name', ward['entity_name'])
                        if ward['sustainability_score'] == 10:
                            ward_highlights.append(f"⭐ {ward_name}が4週連続目標達成！")
                        else:
                            ward_highlights.append(f"🌟 {ward_name}が3週連続で改善！")
                        break
            
            # デフォルトメッセージ
            if not dept_highlights:
                dept_highlights.append("📊 各診療科で着実な改善が進んでいます")
            if not ward_highlights:
                ward_highlights.append("🏥 各病棟で安定した運営が続いています")
            
            # 最大2つまでに制限
            return (" ".join(dept_highlights[:2]), " ".join(ward_highlights[:2]))
            
        except Exception as e:
            logger.error(f"タイプ別ハイライト生成エラー: {e}")
            return ("各診療科で改善が進んでいます", "各病棟で安定運営中です")
    
    def build_compact_highlight(self, dept_scores: List[Dict], 
                              ward_scores: List[Dict]) -> str:
        """トップページ用のコンパクトな週間ハイライト生成"""
        highlights = []
        
        try:
            # 診療科のトップパフォーマー
            if dept_scores and dept_scores[0]['total_score'] >= 80:
                highlights.append(f"🏆 {dept_scores[0]['entity_name']}が{dept_scores[0]['total_score']:.0f}点の高スコア！")
            elif dept_scores and dept_scores[0]['improvement_rate'] > 10:
                highlights.append(f"📈 {dept_scores[0]['entity_name']}が期間平均比+{dept_scores[0]['improvement_rate']:.0f}%の改善！")
            
            # 目標達成部門数
            high_achievers = len([s for s in dept_scores + ward_scores if s['latest_achievement_rate'] >= 98])
            if high_achievers >= 5:
                highlights.append(f"✨ {high_achievers}部門が目標達成率98%以上を記録！")
            elif high_achievers >= 3:
                highlights.append(f"🎯 {high_achievers}部門が目標を達成！")
            
            # 病棟の特別な成果
            if ward_scores and ward_scores[0].get('bed_efficiency_score', 0) > 0:
                ward_name = ward_scores[0].get('display_name', ward_scores[0]['entity_name'])
                highlights.append(f"🏥 {ward_name}は病床効率も優秀で総合力の高さを発揮！")
            
            # 最大2つまでに制限（スペースの都合上）
            highlights = highlights[:2]
            
            if not highlights:
                highlights.append("📊 各部門で着実な改善が進んでいます！")
            
            return " ".join(highlights)
            
        except Exception as e:
            logger.error(f"コンパクトハイライト生成エラー: {e}")
            return "📊 今週も各部門で頑張りが見られました！"

# 後方互換性のための関数
def _generate_weekly_highlights_by_type(dept_scores, ward_scores):
    """後方互換性のためのラッパー関数"""
    ui_builder = UIComponentBuilder()
    return ui_builder._generate_weekly_highlights_by_type(dept_scores, ward_scores)

def _generate_weekly_highlights_compact(dept_scores, ward_scores):
    """後方互換性のためのラッパー関数"""
    ui_builder = UIComponentBuilder()
    return ui_builder.build_compact_highlight(dept_scores, ward_scores)

def _generate_score_detail_html(dept_scores, ward_scores):
    """後方互換性のためのラッパー関数"""
    ui_builder = UIComponentBuilder()
    return ui_builder._build_score_details(dept_scores, ward_scores)

def _generate_weekly_highlights(dept_scores, ward_scores):
    """後方互換性のためのラッパー関数"""
    ui_builder = UIComponentBuilder()
    return ui_builder._build_weekly_highlights(dept_scores, ward_scores)