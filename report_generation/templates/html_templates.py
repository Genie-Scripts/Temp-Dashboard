# templates/html_templates.py
"""
HTMLテンプレート管理モジュール
大量のHTML文字列を整理し、保守性を向上
"""

import urllib.parse
from typing import Dict, List, Optional

class HTMLTemplates:
    """HTML テンプレート管理クラス"""
    
    @staticmethod
    def get_base_template() -> str:
        """ベースHTMLテンプレート"""
        return """
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>{css}</style>
        </head>
        <body>
            <div class="container">
                {header}
                {controls}
                <div class="content-area">
                    {content}
                </div>
            </div>
            {info_panel}
            <script>{javascript}</script>
        </body>
        </html>
        """
    
    @staticmethod
    def get_header_template() -> str:
        """ヘッダー部分のテンプレート"""
        return """
        <div class="header">
            <h1>統合パフォーマンスレポート</h1>
            <p class="subtitle">期間: {period_desc} | 🔥 直近週重視版</p>
            <button class="info-button" onclick="toggleInfoPanel()">
                <span style="font-size: 1.1em;">ℹ️</span>
                <span>評価基準・用語説明</span>
            </button>
        </div>
        """
    
    @staticmethod
    def get_controls_template() -> str:
        """コントロール部分のテンプレート"""
        return """
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
                <button class="quick-button" onclick="showView('view-high-score')">
                    <span>🏆</span> ハイスコア部門
                </button>
            </div>
            
            <div class="selector-group">
                <div class="selector-wrapper" id="dept-selector-wrapper" style="display: none;">
                    <label class="selector-label" for="dept-selector">🩺 診療科</label>
                    <select id="dept-selector" onchange="changeView(this.value)">
                        <option value="">診療科を選択してください</option>
                        {dept_options}
                    </select>
                </div>
                
                <div class="selector-wrapper" id="ward-selector-wrapper" style="display: none;">
                    <label class="selector-label" for="ward-selector">🏢 病棟</label>
                    <select id="ward-selector" onchange="changeView(this.value)">
                        <option value="">病棟を選択してください</option>
                        {ward_options}
                    </select>
                </div>
            </div>
        </div>
        """
    
    @staticmethod
    def get_info_panel_template() -> str:
        """情報パネルのテンプレート"""
        return """
        <div id="info-panel" class="info-panel">
            <div class="info-content">
                <button class="close-button" onclick="toggleInfoPanel()">✕</button>
                
                <h2>📊 評価基準・用語説明（直近週重視版）</h2>
                
                <div class="info-tabs">
                    <button class="info-tab active" onclick="showInfoTab('priority')">
                        <span>🎯</span> アクション優先順位
                    </button>
                    <button class="info-tab" onclick="showInfoTab('evaluation')">
                        <span>🌟</span> 週間総合評価
                    </button>
                    <button class="info-tab" onclick="showInfoTab('highscore')">
                        <span>🏆</span> ハイスコア評価
                    </button>
                    <button class="info-tab" onclick="showInfoTab('improvement')">
                        <span>📈</span> 改善度評価
                    </button>
                    <button class="info-tab" onclick="showInfoTab('los')">
                        <span>📅</span> 在院日数評価
                    </button>
                    <button class="info-tab" onclick="showInfoTab('terms')">
                        <span>📖</span> 用語説明
                    </button>
                    <button class="info-tab" onclick="showInfoTab('flow')">
                        <span>🔄</span> 判定フロー
                    </button>
                </div>
                
                <div class="info-tab-content">
                    {info_tabs_content}
                </div>
            </div>
        </div>
        """
    
    @staticmethod
    def get_view_content_template() -> str:
        """ビューコンテンツのテンプレート"""
        return """
        <div id="{view_id}" class="view-content {active_class}">
            {content}
        </div>
        """
    
    @staticmethod
    def get_highlight_banner_template() -> str:
        """ハイライトバナーのテンプレート"""
        return """
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
    
    @staticmethod
    def get_ranking_section_template() -> str:
        """ランキングセクションのテンプレート"""
        return """
        <div class="ranking-section">
            <h3>{icon} {title}</h3>
            <div class="ranking-list">
                {ranking_items}
            </div>
        </div>
        """
    
    @staticmethod
    def get_ranking_item_template() -> str:
        """ランキングアイテムのテンプレート"""
        return """
        <div class="ranking-item rank-{rank}">
            <span class="medal">{medal}</span>
            <div class="ranking-info">
                <div class="name">{name}</div>
                <div class="detail">{detail}</div>
            </div>
            <div class="score">{score}</div>
        </div>
        """
    
    @staticmethod
    def generate_department_options(departments: List[str]) -> str:
        """診療科選択肢のHTML生成"""
        options = []
        for dept_name in departments:
            dept_id = f"view-dept-{urllib.parse.quote(dept_name)}"
            options.append(f'<option value="{dept_id}">{dept_name}</option>')
        return '\n'.join(options)
    
    @staticmethod
    def generate_ward_options(wards: List[tuple]) -> str:
        """病棟選択肢のHTML生成"""
        options = []
        for ward_code, ward_name in wards:
            ward_id = f"view-ward-{ward_code}"
            options.append(f'<option value="{ward_id}">{ward_name}</option>')
        return '\n'.join(options)

class InfoPanelContent:
    """情報パネルの内容を管理するクラス"""
    
    @staticmethod
    def get_priority_tab_content() -> str:
        """優先順位タブの内容"""
        return """
        <div id="priority-tab" class="tab-pane active">
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
        """
    
    @staticmethod
    def get_evaluation_tab_content() -> str:
        """評価タブの内容"""
        return """
        <div id="evaluation-tab" class="tab-pane">
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
        """
    
    @staticmethod
    def get_highscore_tab_content() -> str:
        """ハイスコアタブの内容"""
        return """
        <div id="highscore-tab" class="tab-pane">
            <h3>🏆 ハイスコア評価基準（100点満点）</h3>
            
            <div class="score-section">
                <h4>📊 総合スコア構成</h4>
                <div class="score-breakdown">
                    <div class="score-item">
                        <span class="score-label">直近週達成度</span>
                        <span class="score-value">50点</span>
                        <div class="score-bar" style="width: 50%;"></div>
                    </div>
                    <div class="score-item">
                        <span class="score-label">改善度</span>
                        <span class="score-value">25点</span>
                        <div class="score-bar" style="width: 25%;"></div>
                    </div>
                    <div class="score-item">
                        <span class="score-label">安定性</span>
                        <span class="score-value">15点</span>
                        <div class="score-bar" style="width: 15%;"></div>
                    </div>
                    <div class="score-item">
                        <span class="score-label">持続性</span>
                        <span class="score-value">10点</span>
                        <div class="score-bar" style="width: 10%;"></div>
                    </div>
                    <div class="score-item special">
                        <span class="score-label">病棟特別項目</span>
                        <span class="score-value">+5点</span>
                        <div class="score-bar" style="width: 5%;"></div>
                    </div>
                </div>
            </div>
            
            <div class="score-detail">
                <h4>1️⃣ 直近週達成度（50点）</h4>
                <table class="score-table">
                    <tr><th>直近週達成率</th><th>得点</th><th>評価</th></tr>
                    <tr class="excellent"><td>110%以上</td><td>50点</td><td>パーフェクト</td></tr>
                    <tr class="excellent"><td>105-110%</td><td>45点</td><td>エクセレント</td></tr>
                    <tr class="good"><td>100-105%</td><td>40点</td><td>優秀</td></tr>
                    <tr class="good"><td>98-100%</td><td>35点</td><td>良好</td></tr>
                    <tr><td>95-98%</td><td>25点</td><td>普通</td></tr>
                    <tr><td>90-95%</td><td>15点</td><td>要改善</td></tr>
                    <tr class="warning"><td>85-90%</td><td>5点</td><td>注意</td></tr>
                    <tr class="danger"><td>85%未満</td><td>0点</td><td>要対策</td></tr>
                </table>
            </div>
        </div>
        """
    
    @staticmethod
    def get_all_info_tabs_content() -> str:
        """全ての情報タブ内容を結合"""
        return (
            InfoPanelContent.get_priority_tab_content() +
            InfoPanelContent.get_evaluation_tab_content() +
            InfoPanelContent.get_highscore_tab_content() +
            # 他のタブ内容も同様に追加可能
            """
            <div id="improvement-tab" class="tab-pane">
                <h3>📈 改善度評価（直近週 vs 期間平均）</h3>
                <p>改善度の詳細説明...</p>
            </div>
            <div id="los-tab" class="tab-pane">
                <h3>📅 平均在院日数の評価（直近週重視）</h3>
                <p>在院日数評価の詳細説明...</p>
            </div>
            <div id="terms-tab" class="tab-pane">
                <h3>📖 用語説明（直近週重視版）</h3>
                <p>用語の詳細説明...</p>
            </div>
            <div id="flow-tab" class="tab-pane">
                <h3>🔄 アクション判定フロー</h3>
                <p>判定フローの詳細説明...</p>
            </div>
            """
        )

class JavaScriptTemplates:
    """JavaScript テンプレート管理クラス"""
    
    @staticmethod
    def get_main_script() -> str:
        """メインJavaScriptコード"""
        return """
        // デバッグ用
        console.log('Script loaded');
        
        let currentType = null;
        
        function showView(viewId) {
            console.log('showView called with:', viewId);
            
            // 全てのビューを非表示
            document.querySelectorAll('.view-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // 指定されたビューを表示
            const targetView = document.getElementById(viewId);
            if (targetView) {
                targetView.classList.add('active');
                console.log('View activated:', viewId);
                
                // Plotlyチャートの再描画をトリガー
                setTimeout(function() {
                    window.dispatchEvent(new Event('resize'));
                    
                    if (window.Plotly) {
                        const plots = targetView.querySelectorAll('.plotly-graph-div');
                        plots.forEach(plot => {
                            Plotly.Plots.resize(plot);
                        });
                    }
                }, 100);
            } else {
                console.error('View not found:', viewId);
            }
            
            // クイックボタンのアクティブ状態を更新
            document.querySelectorAll('.quick-button').forEach(btn => {
                btn.classList.remove('active');
            });
            
            if (viewId === 'view-all') {
                document.querySelector('.quick-button').classList.add('active');
                // セレクターを隠す
                document.getElementById('dept-selector-wrapper').style.display = 'none';
                document.getElementById('ward-selector-wrapper').style.display = 'none';
                document.getElementById('dept-selector').value = '';
                document.getElementById('ward-selector').value = '';
                currentType = null;
            } else if (viewId === 'view-high-score') {
                // ハイスコアボタンをアクティブに（インデックスで指定）
                const buttons = document.querySelectorAll('.quick-button');
                if (buttons.length > 3) {
                    buttons[3].classList.add('active');
                }
                // セレクターを隠す
                document.getElementById('dept-selector-wrapper').style.display = 'none';
                document.getElementById('ward-selector-wrapper').style.display = 'none';
                currentType = null;
            }
        }
        
        function toggleTypeSelector(type) {
            console.log('toggleTypeSelector called with:', type);
            
            // 全てのビューを非表示
            document.querySelectorAll('.view-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // セレクターの表示切替
            if (type === 'dept') {
                document.getElementById('dept-selector-wrapper').style.display = 'flex';
                document.getElementById('ward-selector-wrapper').style.display = 'none';
                document.getElementById('ward-selector').value = '';
            } else if (type === 'ward') {
                document.getElementById('dept-selector-wrapper').style.display = 'none';
                document.getElementById('ward-selector-wrapper').style.display = 'flex';
                document.getElementById('dept-selector').value = '';
            }
            
            currentType = type;
            
            // クイックボタンのアクティブ状態を更新
            document.querySelectorAll('.quick-button').forEach((btn, index) => {
                btn.classList.toggle('active', 
                    (index === 1 && type === 'dept') || 
                    (index === 2 && type === 'ward')
                );
            });
        }
        
        function changeView(viewId) {
            console.log('changeView called with:', viewId);
            if (viewId) {
                showView(viewId);
            }
        }
        
        function toggleInfoPanel() {
            console.log('toggleInfoPanel called');
            const panel = document.getElementById('info-panel');
            if (panel) {
                panel.classList.toggle('active');
                console.log('Info panel toggled');
            } else {
                console.error('Info panel not found');
            }
        }
        
        // タブ切り替え機能
        function showInfoTab(tabName) {
            console.log('Switching to tab:', tabName);
            
            // すべてのタブとコンテンツを非アクティブに
            document.querySelectorAll('.info-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            
            // 選択されたタブとコンテンツをアクティブに
            const activeTab = Array.from(document.querySelectorAll('.info-tab')).find(tab => 
                tab.getAttribute('onclick') && tab.getAttribute('onclick').includes(tabName)
            );
            if (activeTab) {
                activeTab.classList.add('active');
            }
            
            const activePane = document.getElementById(tabName + '-tab');
            if (activePane) {
                activePane.classList.add('active');
            }
        }
        
        // パネル外クリックで閉じる
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM Content Loaded');
            
            const infoPanel = document.getElementById('info-panel');
            if (infoPanel) {
                infoPanel.addEventListener('click', function(e) {
                    if (e.target === this) {
                        toggleInfoPanel();
                    }
                });
            }
            
            // 初期表示時にPlotlyチャートを確実に表示
            setTimeout(function() {
                window.dispatchEvent(new Event('resize'));
                if (window.Plotly) {
                    const plots = document.querySelectorAll('#view-all .plotly-graph-div');
                    plots.forEach(plot => {
                        Plotly.Plots.resize(plot);
                    });
                }
            }, 300);
        });
        
        // ブラウザのリサイズ時にもチャートを再描画
        window.addEventListener('resize', function() {
            if (window.Plotly) {
                const activeView = document.querySelector('.view-content.active');
                if (activeView) {
                    const plots = activeView.querySelectorAll('.plotly-graph-div');
                    plots.forEach(plot => {
                        Plotly.Plots.resize(plot);
                    });
                }
            }
        });
        """