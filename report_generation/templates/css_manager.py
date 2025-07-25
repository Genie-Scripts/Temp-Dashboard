# templates/css_manager.py
"""
CSS管理モジュール
巨大なCSS文字列を分割・整理して保守性を向上
"""

class CSSManager:
    """CSS管理の中央クラス"""
    
    @staticmethod
    def get_css_variables() -> str:
        """CSS変数定義"""
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
    def get_base_styles() -> str:
        """ベーススタイル"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans JP', sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            color: var(--gray-800);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: var(--shadow-xl);
            border-radius: 16px;
            overflow: hidden;
            margin-top: 20px;
            margin-bottom: 20px;
        }
        """
    
    @staticmethod
    def get_header_styles() -> str:
        """ヘッダースタイル"""
        return """
        .header {
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1440 320"><path fill="%23ffffff" fill-opacity="0.1" d="M0,96L48,112C96,128,192,160,288,160C384,160,480,128,576,112C672,96,768,96,864,112C960,128,1056,160,1152,160C1248,160,1344,128,1392,112L1440,96L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"></path></svg>');
            background-size: cover;
            opacity: 0.3;
        }
        
        h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 700;
            letter-spacing: -0.02em;
            position: relative;
            z-index: 1;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .subtitle {
            opacity: 0.95;
            margin-top: 8px;
            font-size: 1.1em;
            position: relative;
            z-index: 1;
        }
        
        .info-button {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.5);
            color: white;
            padding: 10px 20px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 600;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            z-index: 2;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .info-button:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        """
    
    @staticmethod
    def get_controls_styles() -> str:
        """コントロール部分のスタイル"""
        return """
        .controls {
            padding: 30px;
            background: linear-gradient(to bottom, var(--gray-50), white);
            border-bottom: 1px solid var(--gray-200);
        }
        
        .quick-buttons {
            display: flex;
            justify-content: center;
            gap: 12px;
            margin-bottom: 25px;
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
            transition: all var(--transition-normal);
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: var(--shadow-sm);
            position: relative;
            overflow: hidden;
        }
        
        .quick-button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(91, 95, 222, 0.1), transparent);
            transition: left 0.5s;
        }
        
        .quick-button:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
            border-color: var(--primary-color);
            color: var(--primary-color);
        }
        
        .quick-button:hover::before {
            left: 100%;
        }
        
        .quick-button.active {
            background: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
            box-shadow: 0 4px 12px rgba(91, 95, 222, 0.3);
            transform: translateY(-1px);
        }
        
        .quick-button.active:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 16px rgba(91, 95, 222, 0.4);
        }
        
        .quick-button span {
            font-size: 1.2em;
            display: inline-block;
            transition: transform 0.3s;
        }
        
        .quick-button:hover span {
            transform: scale(1.1);
        }
        
        .selector-group {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .selector-wrapper {
            display: flex;
            align-items: center;
            gap: 12px;
            background: white;
            padding: 8px 16px 8px 20px;
            border-radius: 50px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
        }
        
        .selector-wrapper:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }
        
        .selector-label {
            font-weight: 600;
            color: var(--gray-600);
            font-size: 0.95em;
            white-space: nowrap;
        }
        
        select {
            padding: 10px 40px 10px 16px;
            font-size: 0.95em;
            border-radius: 25px;
            border: 2px solid var(--gray-200);
            background-color: white;
            background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12"><path fill="%236B7280" d="M6 9L1 4h10z"/></svg>');
            background-repeat: no-repeat;
            background-position: right 16px center;
            cursor: pointer;
            transition: all var(--transition-fast);
            min-width: 250px;
            font-weight: 500;
            color: var(--gray-700);
            appearance: none;
            -webkit-appearance: none;
            -moz-appearance: none;
        }
        
        select:hover {
            border-color: var(--primary-light);
            background-color: var(--gray-50);
        }
        
        select:focus {
            outline: 0;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(91, 95, 222, 0.1);
        }
        """
    
    @staticmethod
    def get_content_styles() -> str:
        """コンテンツ関連のスタイル"""
        return """
        .content-area {
            padding: 30px;
            background: var(--gray-50);
        }
        
        .view-content {
            display: none;
            animation: fadeIn 0.3s ease-in-out;
        }
        
        .view-content.active {
            display: block;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .section {
            background: white;
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }
        
        .section:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }
        
        .section h2 {
            color: var(--gray-800);
            font-size: 1.5em;
            margin-bottom: 24px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--gray-100);
            display: flex;
            align-items: center;
            gap: 8px;
            font-weight: 700;
        }
        """
    
    @staticmethod
    def get_ranking_styles() -> str:
        """ランキング関連のスタイル"""
        return """
        .ranking-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }
        
        .ranking-section h3 {
            color: var(--primary-color);
            margin-bottom: 20px;
            font-size: 1.2em;
            text-align: center;
            padding: 12px;
            background: linear-gradient(135deg, rgba(91, 95, 222, 0.1) 0%, rgba(91, 95, 222, 0.05) 100%);
            border-radius: 10px;
            font-weight: 700;
        }
        
        .ranking-list {
            background: var(--gray-50);
            border-radius: 12px;
            padding: 20px;
            border: 1px solid var(--gray-200);
        }
        
        .ranking-item {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px;
            background: white;
            border-radius: 10px;
            margin-bottom: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
            border-left: 4px solid var(--gray-300);
            transition: all 0.3s ease;
        }
        
        .ranking-item:hover {
            transform: translateX(5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.12);
        }
        
        .ranking-item.rank-1 {
            border-left-color: #FFD700;
            background: linear-gradient(135deg, rgba(255, 215, 0, 0.1) 0%, white 100%);
        }
        
        .ranking-item.rank-2 {
            border-left-color: #C0C0C0;
            background: linear-gradient(135deg, rgba(192, 192, 192, 0.1) 0%, white 100%);
        }
        
        .ranking-item.rank-3 {
            border-left-color: #CD7F32;
            background: linear-gradient(135deg, rgba(205, 127, 50, 0.1) 0%, white 100%);
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
            color: var(--gray-800);
            font-size: 1em;
            margin-bottom: 4px;
            line-height: 1.2;
        }
        
        .ranking-info .detail {
            font-size: 0.85em;
            color: var(--gray-600);
            line-height: 1.2;
        }
        
        .score {
            font-size: 1.6em;
            font-weight: 700;
            color: var(--primary-color);
            text-align: center;
            min-width: 70px;
            text-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        .period-info {
            text-align: center;
            color: var(--gray-600);
            margin-bottom: 30px;
            font-size: 0.95em;
            padding: 12px;
            background: var(--gray-50);
            border-radius: 8px;
            border: 1px solid var(--gray-200);
            font-weight: 500;
        }
        """
    
    @staticmethod
    def get_highlight_styles() -> str:
        """ハイライト関連のスタイル"""
        return """
        .weekly-highlights-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 0 0 25px 0;
        }
        
        .weekly-highlight-banner {
            padding: 18px 25px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            animation: slideDown 0.4s ease-out;
            position: relative;
            overflow: hidden;
            border-left: 4px solid;
        }
        
        .dept-highlight {
            background: linear-gradient(135deg, #f0f9ff 0%, #dbeafe 100%);
            border-left-color: var(--info-color);
        }
        
        .dept-highlight::before {
            content: '🩺';
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 3em;
            opacity: 0.1;
        }
        
        .ward-highlight {
            background: linear-gradient(135deg, #fef3c7 0%, #fed7aa 100%);
            border-left-color: var(--warning-color);
        }
        
        .ward-highlight::before {
            content: '🏥';
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 3em;
            opacity: 0.1;
        }
        
        .highlight-container {
            display: flex;
            align-items: center;
            gap: 18px;
            position: relative;
            z-index: 1;
        }
        
        .highlight-icon {
            font-size: 1.8em;
            animation: pulse 2s infinite;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
        }
        
        .highlight-content {
            flex: 1;
        }
        
        .highlight-content strong {
            display: block;
            color: var(--gray-800);
            font-size: 0.95em;
            margin-bottom: 8px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }
        
        .dept-highlight .highlight-content strong {
            color: var(--info-color);
        }
        
        .ward-highlight .highlight-content strong {
            color: var(--warning-color);
        }
        
        .highlight-items {
            color: var(--gray-700);
            font-weight: 500;
            line-height: 1.6;
            font-size: 1.05em;
        }
        
        @keyframes slideDown {
            from { 
                opacity: 0; 
                transform: translateY(-20px); 
            }
            to { 
                opacity: 1; 
                transform: translateY(0); 
            }
        }
        
        @keyframes pulse {
            0%, 100% { 
                transform: scale(1); 
            }
            50% { 
                transform: scale(1.15); 
            }
        }
        """
    
    @staticmethod
    def get_info_panel_styles() -> str:
        """情報パネルのスタイル"""
        return """
        .info-panel {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(4px);
            z-index: 1000;
            overflow-y: auto;
            animation: fadeIn 0.3s ease-out;
        }
        
        .info-panel.active {
            display: block;
        }
        
        .info-content {
            max-width: 900px;
            margin: 40px auto;
            background: white;
            border-radius: 20px;
            padding: 40px;
            position: relative;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.3);
            animation: slideIn 0.3s ease-out;
            max-height: 90vh;
            overflow-y: auto;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .close-button {
            position: absolute;
            top: 20px;
            right: 20px;
            background: var(--gray-100);
            border: none;
            font-size: 1.5em;
            cursor: pointer;
            color: var(--gray-600);
            width: 40px;
            height: 40px;
            border-radius: 50%;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .close-button:hover {
            background: var(--gray-200);
            transform: rotate(90deg);
        }
        
        .info-content h2 {
            color: var(--gray-800);
            margin-bottom: 30px;
            font-size: 1.8em;
            border-bottom: 3px solid var(--primary-color);
            padding-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .info-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 25px;
            border-bottom: 2px solid var(--gray-200);
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
        
        .info-tab {
            padding: 10px 20px;
            background: none;
            border: none;
            border-bottom: 3px solid transparent;
            cursor: pointer;
            font-size: 0.95em;
            font-weight: 600;
            color: var(--gray-600);
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 6px;
            white-space: nowrap;
        }
        
        .info-tab:hover {
            color: var(--primary-color);
            background: rgba(91, 95, 222, 0.05);
        }
        
        .info-tab.active {
            color: var(--primary-color);
            border-bottom-color: var(--primary-color);
            background: rgba(91, 95, 222, 0.1);
        }
        
        .tab-pane {
            display: none;
            animation: fadeIn 0.3s ease-in-out;
        }
        
        .tab-pane.active {
            display: block;
        }
        """
    
    @staticmethod
    def get_responsive_styles() -> str:
        """レスポンシブ対応のスタイル"""
        return """
        @media (max-width: 768px) {
            .container {
                margin: 0;
                border-radius: 0;
            }
            
            .header {
                padding: 30px 20px;
            }
            
            h1 {
                font-size: 2em;
            }
            
            .info-button {
                position: static;
                margin-top: 15px;
                display: inline-flex;
                margin-left: auto;
                margin-right: auto;
            }
            
            .controls {
                padding: 20px;
            }
            
            .quick-buttons {
                gap: 8px;
            }
            
            .quick-button {
                padding: 10px 16px;
                font-size: 0.9em;
            }
            
            select {
                min-width: 200px;
            }
            
            .selector-wrapper {
                padding: 6px 12px 6px 16px;
            }
            
            .ranking-grid {
                grid-template-columns: 1fr;
                gap: 20px;
            }
            
            .weekly-highlights-container {
                grid-template-columns: 1fr;
                gap: 15px;
                margin: 0 0 20px 0;
            }
            
            .weekly-highlight-banner {
                padding: 15px 18px;
            }
            
            .highlight-container {
                gap: 12px;
            }
            
            .highlight-icon {
                font-size: 1.5em;
            }
            
            .highlight-content strong {
                font-size: 0.9em;
                margin-bottom: 6px;
            }
            
            .highlight-items {
                font-size: 0.95em;
                line-height: 1.5;
            }
            
            .dept-highlight::before,
            .ward-highlight::before {
                font-size: 2.5em;
                right: 15px;
            }
        }
        """
    
    @staticmethod
    def get_complete_styles() -> str:
        """完全なCSSを統合して返す"""
        return '\n'.join([
            CSSManager.get_css_variables(),
            CSSManager.get_base_styles(),
            CSSManager.get_header_styles(),
            CSSManager.get_controls_styles(),
            CSSManager.get_content_styles(),
            CSSManager.get_ranking_styles(),
            CSSManager.get_highlight_styles(),
            CSSManager.get_info_panel_styles(),
            CSSManager.get_responsive_styles()
        ])