# ui/error_handler.py
"""
統一エラーハンドリングモジュール
アプリケーション全体のエラー処理を統一
"""

import streamlit as st
import traceback
import logging
from functools import wraps
from typing import Callable, Any, Optional, Dict
from datetime import datetime
import sys

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app_errors.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


class ErrorHandler:
    """エラーハンドリングを管理するクラス"""
    
    @staticmethod
    def handle_error(error: Exception, context: str = "", show_details: bool = False) -> None:
        """エラーを統一的に処理"""
        try:
            error_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            error_message = str(error)
            error_type = type(error).__name__
            
            # ログに記録
            logger.error(f"[{error_id}] {context}: {error_type}: {error_message}")
            logger.error(f"[{error_id}] Traceback: {traceback.format_exc()}")
            
            # ユーザーに表示
            st.error(f"エラーが発生しました (ID: {error_id})")
            
            if context:
                st.error(f"場所: {context}")
            
            st.error(f"エラー: {error_message}")
            
            if show_details:
                with st.expander("詳細情報", expanded=False):
                    st.code(traceback.format_exc())
                    st.write(f"エラータイプ: {error_type}")
                    st.write(f"発生時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            # エラーハンドラー自体でエラーが発生した場合
            st.error(f"エラーハンドリング中にエラーが発生: {e}")
            logger.critical(f"ErrorHandler内でエラー: {e}")

    @staticmethod
    def safe_execute(func: Callable, context: str = "", show_details: bool = False, 
                    default_return: Any = None) -> Any:
        """関数を安全に実行"""
        try:
            return func()
        except Exception as e:
            ErrorHandler.handle_error(e, context, show_details)
            return default_return

    @staticmethod
    def with_error_handling(context: str = "", show_details: bool = False, 
                           default_return: Any = None):
        """エラーハンドリングデコレータ"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_context = context or f"{func.__module__}.{func.__name__}"
                    ErrorHandler.handle_error(e, error_context, show_details)
                    return default_return
            return wrapper
        return decorator


def safe_streamlit_operation(operation_name: str = ""):
    """Streamlit操作用の安全実行デコレータ"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = operation_name or f"Streamlit操作: {func.__name__}"
                
                # 特定のエラータイプに応じた処理
                if "DuplicateWidgetID" in str(e):
                    st.error("ウィジェットIDの重複エラーが発生しました。ページをリロードしてください。")
                    logger.warning(f"DuplicateWidgetID エラー: {e}")
                elif "SessionStateKeyError" in str(e):
                    st.error("セッション状態エラーが発生しました。アプリを再起動してください。")
                    logger.warning(f"SessionState エラー: {e}")
                elif "ValueError" in str(type(e).__name__):
                    st.error(f"データ処理エラー: {str(e)}")
                    logger.error(f"ValueError in {context}: {e}")
                else:
                    ErrorHandler.handle_error(e, context, show_details=True)
                
                return None
        return wrapper
    return decorator


def safe_data_operation(operation_name: str = ""):
    """データ操作用の安全実行デコレータ"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = operation_name or f"データ操作: {func.__name__}"
                
                # データ関連エラーの特別処理
                if "KeyError" in str(type(e).__name__):
                    st.error(f"データ列エラー: 必要な列が見つかりません。{str(e)}")
                    logger.error(f"KeyError in {context}: {e}")
                elif "EmptyDataError" in str(type(e).__name__):
                    st.warning("データが空です。データを確認してください。")
                    logger.warning(f"EmptyDataError in {context}: {e}")
                elif "ParserError" in str(type(e).__name__):
                    st.error(f"データ形式エラー: {str(e)}")
                    logger.error(f"ParserError in {context}: {e}")
                else:
                    ErrorHandler.handle_error(e, context, show_details=True)
                
                return None
        return wrapper
    return decorator


def safe_file_operation(operation_name: str = ""):
    """ファイル操作用の安全実行デコレータ"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = operation_name or f"ファイル操作: {func.__name__}"
                
                # ファイル関連エラーの特別処理
                if "FileNotFoundError" in str(type(e).__name__):
                    st.error(f"ファイルが見つかりません: {str(e)}")
                    logger.error(f"FileNotFoundError in {context}: {e}")
                elif "PermissionError" in str(type(e).__name__):
                    st.error(f"ファイルアクセス権限エラー: {str(e)}")
                    logger.error(f"PermissionError in {context}: {e}")
                elif "UnicodeDecodeError" in str(type(e).__name__):
                    st.error("ファイルの文字エンコーディングエラーです。UTF-8形式で保存してください。")
                    logger.error(f"UnicodeDecodeError in {context}: {e}")
                else:
                    ErrorHandler.handle_error(e, context, show_details=True)
                
                return None
        return wrapper
    return decorator


class ErrorReporting:
    """エラーレポート機能"""
    
    @staticmethod
    def display_error_summary() -> None:
        """エラーサマリーを表示"""
        try:
            with st.expander("🔍 エラー情報", expanded=False):
                st.info("""
                **エラーが発生した場合の対処法：**
                
                1. **一時的なエラー**: ページをリロードしてください
                2. **データエラー**: アップロードファイルの形式を確認してください
                3. **継続的なエラー**: ログファイル (app_errors.log) を確認してください
                
                **技術サポート情報：**
                - エラーIDを控えておいてください
                - 詳細情報を展開して内容を確認できます
                - 重要なデータは定期的にバックアップしてください
                """)
                
                if st.button("🗑️ エラーログをクリア"):
                    try:
                        with open('app_errors.log', 'w', encoding='utf-8') as f:
                            f.write("")
                        st.success("エラーログをクリアしました")
                    except Exception as e:
                        st.error(f"ログクリアに失敗: {e}")
                        
        except Exception as e:
            logger.error(f"エラーサマリー表示エラー: {e}")

    @staticmethod
    def get_error_stats() -> Dict[str, Any]:
        """エラー統計を取得"""
        try:
            with open('app_errors.log', 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            error_count = len([line for line in lines if 'ERROR' in line])
            warning_count = len([line for line in lines if 'WARNING' in line])
            critical_count = len([line for line in lines if 'CRITICAL' in line])
            
            return {
                'total_errors': error_count,
                'warnings': warning_count,
                'critical': critical_count,
                'log_size': len(lines)
            }
            
        except FileNotFoundError:
            return {'total_errors': 0, 'warnings': 0, 'critical': 0, 'log_size': 0}
        except Exception as e:
            logger.error(f"エラー統計取得エラー: {e}")
            return {'total_errors': -1, 'warnings': -1, 'critical': -1, 'log_size': -1}


# グローバル例外ハンドラー
def setup_global_exception_handler():
    """グローバル例外ハンドラーを設定"""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical("未処理例外:", exc_info=(exc_type, exc_value, exc_traceback))
        
    sys.excepthook = handle_exception


# 便利な別名を追加
with_error_handling = ErrorHandler.with_error_handling

# 初期化
setup_global_exception_handler()