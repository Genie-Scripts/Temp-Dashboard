# ui/__init__.py
"""
UI パッケージ

手術分析ダッシュボードのUI層を管理するパッケージです。
よく使用されるクラスへの便利なアクセスを提供します。
"""

# 主要なUIクラスをパッケージレベルでアクセス可能にする
from .session_manager import SessionManager
from .sidebar import SidebarManager
from .error_handler import ErrorHandler, safe_streamlit_operation, safe_data_operation, safe_file_operation
from .page_router import render_current_page, navigate_to, get_available_pages

# バージョン情報
__version__ = "1.0.0"

# パッケージ情報
__all__ = [
    # セッション管理
    'SessionManager',
    
    # UI コンポーネント
    'SidebarManager',
    
    # エラーハンドリング
    'ErrorHandler',
    'safe_streamlit_operation',
    'safe_data_operation', 
    'safe_file_operation',
    
    # ページルーティング
    'render_current_page',
    'navigate_to',
    'get_available_pages',
]

# パッケージレベルの初期化ログ
import logging
logger = logging.getLogger(__name__)
logger.info(f"UI パッケージ v{__version__} が初期化されました")