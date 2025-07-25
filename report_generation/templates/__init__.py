# templates/__init__.py
"""
テンプレート管理モジュール

HTML、CSS、JavaScriptのテンプレートを管理するパッケージ
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# =============================================================================
# テンプレートモジュールのインポート
# =============================================================================

# HTMLテンプレート
try:
    from .html_templates import (
        HTMLTemplates,
        InfoPanelContent,
        JavaScriptTemplates
    )
    HTML_TEMPLATES_AVAILABLE = True
    logger.info("✅ html_templates モジュールが正常にロードされました")
except ImportError as e:
    logger.error(f"❌ html_templates のインポートに失敗: {e}")
    HTMLTemplates = InfoPanelContent = JavaScriptTemplates = None
    HTML_TEMPLATES_AVAILABLE = False

# CSS管理
try:
    from .css_manager import CSSManager
    CSS_MANAGER_AVAILABLE = True
    logger.info("✅ css_manager モジュールが正常にロードされました")
except ImportError as e:
    logger.error(f"❌ css_manager のインポートに失敗: {e}")
    CSSManager = None
    CSS_MANAGER_AVAILABLE = False

# =============================================================================
# テンプレート管理の統合クラス
# =============================================================================

class TemplateManager:
    """テンプレート管理の統合クラス"""
    
    def __init__(self):
        self.html_available = HTML_TEMPLATES_AVAILABLE
        self.css_available = CSS_MANAGER_AVAILABLE
        
        if self.html_available:
            self.html_templates = HTMLTemplates()
            self.js_templates = JavaScriptTemplates()
            self.info_content = InfoPanelContent()
        
        if self.css_available:
            self.css_manager = CSSManager()
    
    def get_complete_html_template(self, **kwargs) -> str:
        """完全なHTMLテンプレートを取得
        
        Args:
            **kwargs: テンプレートに渡すパラメータ
            
        Returns:
            完全なHTMLテンプレート文字列
        """
        if not self.html_available:
            return self._get_fallback_html_template(**kwargs)
        
        try:
            base_template = self.html_templates.get_base_template()
            
            # デフォルト値の設定
            defaults = {
                'title': '統合パフォーマンスレポート',
                'css': self.get_complete_css() if self.css_available else '',
                'header': '',
                'controls': '',
                'content': '',
                'info_panel': '',
                'javascript': self.get_complete_javascript()
            }
            defaults.update(kwargs)
            
            return base_template.format(**defaults)
            
        except Exception as e:
            logger.error(f"HTMLテンプレート生成エラー: {e}")
            return self._get_fallback_html_template(**kwargs)
    
    def get_complete_css(self) -> str:
        """完全なCSSを取得"""
        if not self.css_available:
            return self._get_fallback_css()
        
        try:
            return self.css_manager.get_complete_styles()
        except Exception as e:
            logger.error(f"CSS生成エラー: {e}")
            return self._get_fallback_css()
    
    def get_complete_javascript(self) -> str:
        """完全なJavaScriptを取得"""
        if not self.html_available:
            return self._get_fallback_javascript()
        
        try:
            return self.js_templates.get_main_script()
        except Exception as e:
            logger.error(f"JavaScript生成エラー: {e}")
            return self._get_fallback_javascript()
    
    def get_info_panel_content(self) -> str:
        """情報パネルの内容を取得"""
        if not self.html_available:
            return "<div>情報パネルが利用できません</div>"
        
        try:
            template = self.html_templates.get_info_panel_template()
            content = self.info_content.get_all_info_tabs_content()
            return template.format(info_tabs_content=content)
        except Exception as e:
            logger.error(f"情報パネル生成エラー: {e}")
            return "<div>情報パネルの生成に失敗しました</div>"
    
    def _get_fallback_html_template(self, **kwargs) -> str:
        """フォールバック用HTMLテンプレート"""
        title = kwargs.get('title', 'レポート')
        content = kwargs.get('content', '<p>コンテンツが利用できません</p>')
        
        return f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>{self._get_fallback_css()}</style>
        </head>
        <body>
            <div class="container">
                <header>
                    <h1>{title}</h1>
                    <p>フォールバックモードで実行中</p>
                </header>
                <main>{content}</main>
            </div>
            <script>{self._get_fallback_javascript()}</script>
        </body>
        </html>
        """
    
    def _get_fallback_css(self) -> str:
        """フォールバック用CSS"""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: sans-serif; background: #f5f5f5; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; }
        header { text-align: center; margin-bottom: 30px; padding: 20px; background: #5B5FDE; color: white; }
        h1 { font-size: 2em; margin-bottom: 10px; }
        main { padding: 20px; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 10px 0; }
        """
    
    def _get_fallback_javascript(self) -> str:
        """フォールバック用JavaScript"""
        return """
        console.log('テンプレートモジュール: フォールバックモードで実行中');
        document.addEventListener('DOMContentLoaded', function() {
            console.log('ページ読み込み完了（フォールバック）');
        });
        """

# =============================================================================
# 便利関数
# =============================================================================

def create_template_manager() -> TemplateManager:
    """TemplateManager インスタンスを作成"""
    return TemplateManager()

def get_template_status() -> Dict[str, Any]:
    """テンプレートモジュールの状況を取得"""
    return {
        'html_templates': HTML_TEMPLATES_AVAILABLE,
        'css_manager': CSS_MANAGER_AVAILABLE,
        'fully_available': HTML_TEMPLATES_AVAILABLE and CSS_MANAGER_AVAILABLE
    }

def validate_templates() -> bool:
    """テンプレートの妥当性を検証"""
    status = get_template_status()
    
    if status['fully_available']:
        logger.info("✅ 全てのテンプレートモジュールが利用可能です")
        return True
    else:
        missing = []
        if not status['html_templates']:
            missing.append('html_templates')
        if not status['css_manager']:
            missing.append('css_manager')
        
        logger.warning(f"❌ 以下のテンプレートモジュールが利用できません: {missing}")
        return False

# 汎用テンプレート生成関数（後方互換性）
def get_integrated_css() -> str:
    """統合CSS取得（後方互換性）"""
    manager = create_template_manager()
    return manager.get_complete_css()

def get_base_html_template() -> str:
    """ベースHTMLテンプレート取得（後方互換性）"""
    if HTML_TEMPLATES_AVAILABLE:
        return HTMLTemplates.get_base_template()
    else:
        manager = create_template_manager()
        return manager._get_fallback_html_template()

def get_main_javascript() -> str:
    """メインJavaScript取得（後方互換性）"""
    manager = create_template_manager()
    return manager.get_complete_javascript()

# =============================================================================
# 公開API
# =============================================================================

__all__ = [
    # メインクラス
    'HTMLTemplates',
    'CSSManager', 
    'JavaScriptTemplates',
    'InfoPanelContent',
    'TemplateManager',
    
    # ファクトリ関数
    'create_template_manager',
    
    # ユーティリティ関数
    'get_template_status',
    'validate_templates',
    
    # 後方互換性関数
    'get_integrated_css',
    'get_base_html_template',
    'get_main_javascript',
    
    # 状態変数
    'HTML_TEMPLATES_AVAILABLE',
    'CSS_MANAGER_AVAILABLE'
]

# 初期化ログ
status = get_template_status()
logger.info(f"templates パッケージを初期化しました")
logger.info(f"  HTML Templates: {'✅' if status['html_templates'] else '❌'}")
logger.info(f"  CSS Manager: {'✅' if status['css_manager'] else '❌'}")

if status['fully_available']:
    logger.info("🎉 全てのテンプレート機能が利用可能です")
else:
    logger.warning("⚠️  一部のテンプレート機能が制限されます")
