# === 改善提案: CSS管理の統合 ===

# 1. 新しいファイルを作成: css_styles.py
"""
CSSスタイルを管理する専用モジュール
"""

class CSSStyles:
    """CSSスタイルを管理するクラス"""
    
    @staticmethod
    def get_base_variables():
        """CSS変数の定義"""
        return """
        :root {
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
        }
        """
    
    @staticmethod
    def get_mobile_base_styles():
        """モバイル向け基本スタイル"""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Noto Sans JP', sans-serif;
            background: var(--gray-50); 
            color: var(--gray-800);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
        }
        
        /* コンテナ */
        .container { 
            max-width: 100%;
            padding: 16px;
            margin-bottom: 60px;
        }
        
        /* ヘッダー */
        .header {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 20px 16px;
            text-align: center;
            border-radius: 12px;
        }
        .header h1 { font-size: 1.4em; margin-bottom: 4px; }
        .header p { font-size: 0.9em; opacity: 0.9; }
        """
    
    @staticmethod
    def get_card_styles():
        """カード関連のスタイル"""
        return """
        /* カード基本スタイル */
        .summary-cards {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 20px;
        }
        
        .summary-card {
            background: white;
            border-radius: 12px;
            padding: 16px;
            text-align: center;
            box-shadow: var(--shadow-md);
            transition: transform 0.2s;
            position: relative;
            overflow: hidden;
        }
        
        .summary-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--gray-200);
        }
        
        .summary-card:active {
            transform: scale(0.98);
        }
        
        .summary-card h3 {
            font-size: 0.85em;
            color: var(--gray-600);
            margin-bottom: 8px;
        }
        
        .summary-card .value {
            font-size: 1.8em;
            font-weight: bold;
            margin-bottom: 4px;
        }
        
        .summary-card .target {
            font-size: 0.8em;
            color: var(--gray-500);
        }
        
        /* カードの色分け */
        .card-good .value { color: var(--success-color); }
        .card-good::before { background: var(--success-color); }
        
        .card-warning .value { color: var(--warning-color); }
        .card-warning::before { background: var(--warning-color); }
        
        .card-danger .value { color: var(--danger-color); }
        .card-danger::before { background: var(--danger-color); }
        
        .card-info .value { color: var(--info-color); }
        .card-info::before { background: var(--info-color); }
        """
    
    @staticmethod
    def get_metric_split_styles():
        """週報向け並列表示メトリクスのスタイル"""
        return """
        /* 週報向け並列表示カード */
        .metric-card-split { 
            padding: 20px !important; 
        }
        
        .metric-card-split h3 { 
            font-size: 1em; 
            margin-bottom: 16px; 
            color: var(--gray-700); 
            font-weight: 600; 
            display: flex; 
            align-items: center; 
            gap: 8px; 
        }
        
        .metric-split-container { 
            display: grid; 
            grid-template-columns: 1fr auto 1fr; 
            align-items: center; 
            gap: 20px; 
        }
        
        .metric-left, .metric-right { 
            text-align: center; 
        }
        
        .metric-divider { 
            width: 1px; 
            height: 80px; 
            background: var(--gray-200); 
            margin: 0 auto; 
        }
        
        .metric-label { 
            font-size: 0.85em; 
            color: var(--gray-500); 
            font-weight: 600; 
            margin-bottom: 8px; 
            text-transform: uppercase; 
            letter-spacing: 0.05em; 
        }
        
        .metric-value { 
            font-size: 1.8em; 
            font-weight: 700; 
            margin-bottom: 4px; 
            line-height: 1.2; 
        }
        
        .metric-sub { 
            font-size: 0.8em; 
            color: var(--gray-500); 
            height: 20px; 
        }
        
        .metric-trend { 
            display: inline-flex; 
            align-items: center; 
            gap: 4px; 
            font-size: 0.9em; 
            font-weight: 600; 
            padding: 4px 12px; 
            border-radius: 16px; 
            margin-top: 4px; 
        }
        
        .metric-status { 
            font-size: 0.85em; 
            color: var(--gray-600); 
            margin-top: 4px; 
            font-weight: 600; 
        }
        
        /* トレンドクラス */
        .trend-excellent { background: rgba(16, 185, 129, 0.15); color: var(--success-color); }
        .trend-good { background: rgba(59, 130, 246, 0.15); color: var(--info-color); }
        .trend-stable { background: rgba(245, 158, 11, 0.15); color: var(--warning-color); }
        .trend-warning { background: rgba(251, 146, 60, 0.15); color: rgb(234, 88, 12); }
        .trend-danger { background: rgba(239, 68, 68, 0.15); color: var(--danger-color); }
        """
    
    @staticmethod
    def get_section_styles():
        """セクション関連のスタイル"""
        return """
        /* セクション */
        .section {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: var(--shadow-md);
        }
        
        .section h2 {
            color: var(--primary-color);
            font-size: 1.1em;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--gray-100);
        }
        
        .section h3 {
            color: var(--gray-700);
            font-size: 1em;
            margin-top: 16px;
            margin-bottom: 12px;
        }
        """
    
    @staticmethod
    def get_chart_styles():
        """チャート関連のスタイル"""
        return """
        /* チャート */
        .chart-container {
            margin-bottom: 20px;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .chart-placeholder {
            background: var(--gray-50);
            border: 2px dashed var(--gray-300);
            border-radius: 8px;
            min-height: 200px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--gray-500);
            font-size: 0.9em;
            margin-bottom: 12px;
            padding: 20px;
            text-align: center;
        }
        """
    
    @staticmethod
    def get_action_styles():
        """アクション関連のスタイル"""
        return """
        /* アクション */
        .action-list {
            list-style: none;
            margin: 0;
        }
        
        .action-list li {
            background: var(--gray-50);
            margin-bottom: 8px;
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid var(--primary-color);
            font-size: 0.9em;
        }
        
        .action-list .priority {
            color: var(--primary-color);
            font-weight: bold;
            font-size: 0.8em;
            margin-bottom: 4px;
        }
        
        .action-summary {
            background: var(--gray-50);
            border-left: 5px solid var(--info-color);
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 5px;
        }
        """
    
    @staticmethod
    def get_responsive_styles():
        """レスポンシブ対応（スマートフォン縦画面で1列表示に修正）"""
        return """
        /* レスポンシブ対応 */
        @media (max-width: 768px) {
            .container {
                margin: 0;
                border-radius: 0;
            }
            
             .summary-cards,
            .metric-split-container {
                grid-template-columns: 1fr !important; /* 画面幅が狭い場合は1列に */
            }
            
            .metric-divider {
                display: none; /* 1列表示では区切り線を非表示に */
            }
            
            .metric-card-split .metric-left {
                margin-bottom: 16px; /* 縦に並んだ際のスペース調整 */
            }

            .header {
                padding: 30px 20px;
            }
            
            h1 {
                font-size: 2em;
            }
            
            .quick-buttons {
                gap: 8px;
            }
            
            .quick-button {
                padding: 10px 16px;
                font-size: 0.9em;
            }
            
            .ranking-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }
        }
        """
    
    @staticmethod
    def get_mobile_report_styles():
        """モバイルレポート用完全スタイル"""
        return (
            CSSStyles.get_base_variables() +
            CSSStyles.get_mobile_base_styles() +
            CSSStyles.get_card_styles() +
            CSSStyles.get_metric_split_styles() +
            CSSStyles.get_section_styles() +
            CSSStyles.get_chart_styles() +
            CSSStyles.get_action_styles() +
            CSSStyles.get_responsive_styles()
        )
    
    @staticmethod
    def get_integrated_report_styles():
        """統合レポート用完全スタイル（より高度）"""
        return (
            CSSStyles.get_base_variables() +
            CSSStyles.get_mobile_base_styles() +
            CSSStyles.get_card_styles() +
            CSSStyles.get_metric_split_styles() +
            CSSStyles.get_section_styles() +
            CSSStyles.get_chart_styles() +
            CSSStyles.get_action_styles() +
            CSSStyles.get_responsive_styles() +
            """
            /* 統合レポート専用の追加スタイル */
            .container {
                max-width: 1200px;
                margin: 0 auto;
                border-radius: 16px;
                overflow: hidden;
                margin-top: 20px;
                margin-bottom: 20px;
            }
            
            .controls {
                padding: 30px;
                background: var(--gray-50);
                border-bottom: 1px solid var(--gray-200);
            }
            
            .quick-buttons {
                display: flex;
                justify-content: center;
                gap: 12px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            
            .quick-button {
                padding: 12px 24px;
                background: white;
                color: var(--gray-700);
                border: 2px solid var(--gray-200);
                border-radius: 12px;
                cursor: pointer;
                font-size: 0.95em;
                font-weight: 600;
                transition: all 0.3s;
                display: flex;
                align-items: center;
                gap: 8px;
                box-shadow: var(--shadow-sm);
            }
            
            .quick-button:hover {
                transform: translateY(-2px);
                box-shadow: var(--shadow-md);
                border-color: var(--primary-color);
                color: var(--primary-color);
            }
            
            .quick-button.active {
                background: var(--primary-color);
                color: white;
                border-color: var(--primary-color);
                box-shadow: var(--shadow-md);
            }
            """
        )


# === 2. mobile_report_generator.py の修正 ===

# 元のファイルで関数を以下のように変更:
def _get_css_styles():
    """モバイルレポート用CSSスタイルを返す"""
    from css_styles import CSSStyles
    return CSSStyles.get_mobile_report_styles()


# === 3. html_export_functions.py の修正 ===

# 元のファイルで関数を以下のように変更:
def _get_css_styles():
    """統合レポート用CSSスタイルを返す"""
    from css_styles import CSSStyles
    return CSSStyles.get_integrated_report_styles()


# === 4. 使用例 ===

"""
# 個別のスタイル部品が必要な場合
from css_styles import CSSStyles

# 基本的なカードスタイルのみ
card_css = CSSStyles.get_card_styles()

# メトリクス分割スタイルのみ
metric_css = CSSStyles.get_metric_split_styles()

# 完全なモバイルスタイル
mobile_css = CSSStyles.get_mobile_report_styles()

# 完全な統合レポートスタイル
integrated_css = CSSStyles.get_integrated_report_styles()
"""