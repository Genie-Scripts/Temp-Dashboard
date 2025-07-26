# ui/page_router.py
"""
ページルーティング管理モジュール
各ページへのルーティングとページ表示を管理
"""

import streamlit as st
from typing import Dict, Callable, Optional
import logging

from ui.session_manager import SessionManager
from ui.error_handler import safe_streamlit_operation, ErrorHandler

logger = logging.getLogger(__name__)


class PageRouter:
    """ページルーティングを管理するクラス"""
    
    def __init__(self):
        self._pages: Dict[str, Callable] = {}
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """ルートを設定"""
        try:
            # 遅延インポートでページモジュールを読み込み
            from ui.pages.dashboard_page import DashboardPage
            from ui.pages.data_management_page import DataManagementPage
            from ui.pages.hospital_page import HospitalPage
            from ui.pages.department_page import DepartmentPage
            from ui.pages.surgeon_page import SurgeonPage
            from ui.pages.prediction_page import PredictionPage
            
            # 全ページを設定
            self._pages = {
                "ダッシュボード": DashboardPage.render,
                "データアップロード": self._render_upload_page_legacy,  # legacy版を継続使用
                "データ管理": DataManagementPage.render,
                "病院全体分析": HospitalPage.render,
                "診療科別分析": DepartmentPage.render,
                "術者分析": SurgeonPage.render,
                "将来予測": PredictionPage.render,
            }
            
            logger.info(f"ページルート設定完了: {list(self._pages.keys())}")
            
        except ImportError as e:
            logger.error(f"ページモジュールのインポートエラー: {e}")
            st.error(f"ページモジュールの読み込みに失敗しました: {e}")
            # フォールバック: 基本ページのみ設定
            self._setup_fallback_routes()
    
    def _setup_fallback_routes(self) -> None:
        """フォールバック用の基本ルート設定"""
        self._pages = {
            "ダッシュボード": self._render_fallback_page,
            "データアップロード": self._render_upload_page_legacy,
            "データ管理": self._render_fallback_page,
            "病院全体分析": self._render_fallback_page,
            "診療科別分析": self._render_fallback_page,
            "術者分析": self._render_fallback_page,
            "将来予測": self._render_fallback_page,
        }
    
    @safe_streamlit_operation("ページ描画")
    def render_current_page(self) -> None:
        """現在選択されているページを描画"""
        current_view = SessionManager.get_current_view()
        
        # ページが存在するかチェック
        if current_view not in self._pages:
            logger.warning(f"未知のページ: {current_view}")
            self._render_error_page(f"ページ '{current_view}' が見つかりません")
            return
        
        # データが必要なページでのデータ検証
        if self._requires_data(current_view):
            if not self._validate_data_for_page(current_view):
                return
        
        # ページを描画
        try:
            page_func = self._pages[current_view]
            page_func()
            
        except Exception as e:
            logger.error(f"ページ描画エラー ({current_view}): {e}")
            ErrorHandler.handle_error(e, f"ページ描画: {current_view}", show_details=True)
            self._render_error_page(f"ページの表示中にエラーが発生しました")
    
    def _requires_data(self, page_name: str) -> bool:
        """ページがデータを必要とするかチェック"""
        data_required_pages = [
            "ダッシュボード",
            "病院全体分析", 
            "診療科別分析",
            "術者分析",
            "将来予測"
        ]
        return page_name in data_required_pages
    
    def _validate_data_for_page(self, page_name: str) -> bool:
        """ページ用のデータ検証"""
        if not SessionManager.is_data_loaded():
            self._render_no_data_page()
            return False
        
        # データの整合性チェック
        is_valid, message = SessionManager.validate_session_data()
        if not is_valid:
            st.error(f"データ検証エラー: {message}")
            logger.error(f"データ検証失敗 ({page_name}): {message}")
            return False
        
        return True
    
    def _render_no_data_page(self) -> None:
        """データ未読み込み時のページ"""
        st.warning("🚨 データが読み込まれていません")
        
        st.markdown("""
        ### 分析を開始するには
        
        以下のいずれかの方法でデータを読み込んでください：
        
        1. **📤 データアップロード** - 新規データファイルをアップロード
        2. **💾 データ管理** - 保存済みデータを読み込み
        """)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📤 データアップロードへ", type="primary"):
                SessionManager.set_current_view("データアップロード")
                st.rerun()
        
        with col2:
            if st.button("💾 データ管理へ"):
                SessionManager.set_current_view("データ管理")
                st.rerun()
    
    def _render_error_page(self, message: str) -> None:
        """エラーページ"""
        st.error("🚨 ページエラー")
        st.write(message)
        
        if st.button("🏠 ダッシュボードに戻る"):
            SessionManager.set_current_view("ダッシュボード")
            st.rerun()
    
    def _render_fallback_page(self) -> None:
        """フォールバックページ"""
        current_view = SessionManager.get_current_view()
        
        st.warning(f"🚧 ページ '{current_view}' は現在利用できません")
        st.info("モジュールの読み込みに問題がある可能性があります。")
        
        with st.expander("対処法"):
            st.markdown("""
            1. ページを再読み込みしてください
            2. アプリケーションを再起動してください
            3. 必要なモジュールがインストールされているか確認してください
            """)
        
        if st.button("🏠 ダッシュボードに戻る"):
            SessionManager.set_current_view("ダッシュボード")
            st.rerun()
    
    def _render_upload_page_legacy(self) -> None:
        """元のapp.pyから移植したアップロードページ"""
        import traceback
        from datetime import datetime
        from data_processing import loader
        from config import target_loader
        from data_persistence import save_data_to_file, create_backup, get_data_info
        
        st.header("📤 データアップロード")
        
        # 既存の保存データがある場合の警告
        data_info = get_data_info()
        if data_info:
            st.warning("💾 既に保存されたデータがあります。新しいデータをアップロードすると上書きされます。")
            with st.expander("保存データの詳細"):
                st.json(data_info)
        
        base_file = st.file_uploader("基礎データ (CSV)", type="csv")
        update_files = st.file_uploader("追加データ (CSV)", type="csv", accept_multiple_files=True)
        target_file = st.file_uploader("目標データ (CSV)", type="csv")
        
        # データ保存設定
        st.subheader("📁 データ保存設定")
        col1, col2 = st.columns(2)
        with col1:
            auto_save = st.checkbox("処理完了後にデータを自動保存", value=True, help="次回起動時に自動でデータが読み込まれます")
        with col2:
            create_backup_checkbox = st.checkbox("処理前にバックアップを作成", value=True, help="現在のデータをバックアップしてから新データを処理します")
        
        if st.button("データ処理を実行", type="primary"):
            with st.spinner("データ処理中..."):
                try:
                    # バックアップ作成（既存データがある場合のみ）
                    if create_backup_checkbox:
                        # 既存データの存在確認
                        existing_data_info = get_data_info()
                        if existing_data_info:
                            backup_success = create_backup(force_create=True)
                            if backup_success:
                                st.success("✅ 既存データのバックアップを作成しました")
                            else:
                                st.warning("⚠️ バックアップ作成に失敗しましたが、処理を続行します")
                        else:
                            st.info("💡 初回データ処理のため、バックアップをスキップします")
                    
                    # データ処理
                    if base_file:
                        df = loader.load_and_merge_files(base_file, update_files)
                        SessionManager.set_processed_df(df)
                        SessionManager.set_data_source('file_upload')
                        
                        if not df.empty: 
                            SessionManager.set_latest_date(df['手術実施日_dt'].max())
                        
                        st.success(f"✅ データ処理完了。{len(df)}件のレコードが読み込まれました。")
                        
                        # 目標データの処理
                        target_dict = {}
                        if target_file:
                            target_dict = target_loader.load_target_file(target_file)
                            SessionManager.set_target_dict(target_dict)
                            st.success(f"✅ 目標データを読み込みました。{len(target_dict)}件の診療科目標を設定。")
                        
                        # 自動保存
                        if auto_save:
                            save_success = save_data_to_file(df, target_dict, {
                                'upload_time': datetime.now().isoformat(),
                                'base_file_name': base_file.name,
                                'update_files_count': len(update_files) if update_files else 0,
                                'target_file_name': target_file.name if target_file else None
                            })
                            
                            if save_success:
                                if existing_data_info:
                                    st.success("💾 データを更新保存しました。次回起動時に自動で読み込まれます。")
                                else:
                                    st.success("💾 データを新規保存しました。次回起動時に自動で読み込まれます。")
                            else:
                                st.error("❌ データ保存に失敗しました。")
                    else:
                        st.warning("基礎データファイルをアップロードしてください。")
                        
                except Exception as e:
                    st.error(f"エラー: {e}")
                    st.code(traceback.format_exc())
    
    def get_available_pages(self) -> list:
        """利用可能なページ一覧を取得"""
        return list(self._pages.keys())
    
    def add_page(self, name: str, render_func: Callable) -> None:
        """動的にページを追加"""
        self._pages[name] = render_func
        logger.info(f"ページを追加: {name}")
    
    def remove_page(self, name: str) -> None:
        """ページを削除"""
        if name in self._pages:
            del self._pages[name]
            logger.info(f"ページを削除: {name}")


# グローバルルーター
_router_instance: Optional[PageRouter] = None


def get_router() -> PageRouter:
    """ルーターのシングルトンインスタンスを取得"""
    global _router_instance
    if _router_instance is None:
        _router_instance = PageRouter()
    return _router_instance


def render_current_page() -> None:
    """現在のページを描画（便利関数）"""
    router = get_router()
    router.render_current_page()


def navigate_to(page_name: str) -> None:
    """指定されたページに遷移"""
    router = get_router()
    if page_name in router.get_available_pages():
        SessionManager.set_current_view(page_name)
        st.rerun()
    else:
        st.error(f"ページ '{page_name}' は存在しません")


def get_available_pages() -> list:
    """利用可能なページ一覧を取得（便利関数）"""
    router = get_router()
    return router.get_available_pages()