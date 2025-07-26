# report_generation/css_styles.py
"""
CSS管理モジュール（レガシー互換）
templates/css_manager.py への移行を推奨
"""

try:
    from .templates.css_manager import CSSManager
    
    class CSSStyles:
        """レガシー互換用CSSスタイルクラス"""
        
        @staticmethod
        def get_integrated_report_styles() -> str:
            """統合レポート用CSS（新実装へのプロキシ）"""
            return f"<style>{CSSManager.get_complete_styles()}</style>"
            
except ImportError:
    # フォールバック実装
    class CSSStyles:
        """最小限のCSSスタイル"""
        
        @staticmethod
        def get_integrated_report_styles() -> str:
            """基本的なCSSスタイル"""
            return """
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    background: #f5f5f5;
                    margin: 0;
                    padding: 20px;
                }
                
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }
                
                .header {
                    background: #5B5FDE;
                    color: white;
                    padding: 30px;
                    text-align: center;
                }
                
                h1 {
                    margin: 0;
                    font-size: 2em;
                }
                
                .controls {
                    padding: 20px;
                    background: #f8f9fa;
                    border-bottom: 1px solid #dee2e6;
                }
                
                .content-area {
                    padding: 20px;
                }
                
                .section {
                    background: white;
                    border-radius: 8px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                
                .metric-card {
                    background: #f8f9fa;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    border-left: 4px solid #5B5FDE;
                }
                
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }
                
                th, td {
                    padding: 8px;
                    text-align: left;
                    border-bottom: 1px solid #dee2e6;
                }
                
                th {
                    background: #f8f9fa;
                    font-weight: 600;
                }
                
                .quick-button {
                    padding: 10px 20px;
                    margin: 5px;
                    background: white;
                    border: 2px solid #dee2e6;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: all 0.3s;
                }
                
                .quick-button:hover {
                    border-color: #5B5FDE;
                    color: #5B5FDE;
                }
                
                .quick-button.active {
                    background: #5B5FDE;
                    color: white;
                    border-color: #5B5FDE;
                }
                
                select {
                    padding: 8px 15px;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    font-size: 14px;
                    min-width: 200px;
                }
                
                .info-panel {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.5);
                    z-index: 1000;
                }
                
                .info-panel.active {
                    display: block;
                }
                
                .info-content {
                    max-width: 800px;
                    margin: 50px auto;
                    background: white;
                    padding: 30px;
                    border-radius: 8px;
                    max-height: 80vh;
                    overflow-y: auto;
                }
                
                .close-button {
                    float: right;
                    font-size: 24px;
                    cursor: pointer;
                    border: none;
                    background: none;
                }
                
                @media (max-width: 768px) {
                    .container {
                        margin: 0;
                        border-radius: 0;
                    }
                    
                    .controls {
                        text-align: center;
                    }
                    
                    select {
                        width: 100%;
                        margin: 5px 0;
                    }
                }
            </style>
            """