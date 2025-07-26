# ui/pages/data_management_page.py
"""
データ管理ページモジュール
データの読み込み、保存、バックアップ管理を行う
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from ui.session_manager import SessionManager
from ui.error_handler import safe_streamlit_operation, safe_file_operation
from data_persistence import (
    get_data_info, get_file_sizes, get_backup_info, restore_from_backup,
    export_data_package, import_data_package, create_backup,
    load_data_from_file, save_data_to_file, delete_saved_data
)

logger = logging.getLogger(__name__)


class DataManagementPage:
    """データ管理ページクラス"""
    
    @staticmethod
    @safe_streamlit_operation("データ管理ページ描画")
    def render() -> None:
        """データ管理ページを描画"""
        st.header("💾 データ管理")
        
        # データ状態の表示
        data_info = get_data_info()
        file_sizes = get_file_sizes()
        
        # タブで機能を分割
        tab1, tab2, tab3, tab4 = st.tabs([
            "データ状態", 
            "バックアップ管理", 
            "データエクスポート/インポート", 
            "詳細設定"
        ])
        
        with tab1:
            DataManagementPage._render_data_status_tab(data_info, file_sizes)
        
        with tab2:
            DataManagementPage._render_backup_management_tab()
        
        with tab3:
            DataManagementPage._render_export_import_tab()
        
        with tab4:
            DataManagementPage._render_settings_tab()
    
    @staticmethod
    def _render_data_status_tab(data_info: dict, file_sizes: dict) -> None:
        """データ状態タブを描画"""
        st.subheader("📊 現在のデータ状態")
        
        col1, col2 = st.columns(2)
        
        with col1:
            DataManagementPage._render_saved_data_section(data_info)
        
        with col2:
            DataManagementPage._render_session_data_section(file_sizes)
    
    @staticmethod
    @safe_file_operation("保存データ表示")
    def _render_saved_data_section(data_info: dict) -> None:
        """保存データセクションを描画"""
        if data_info:
            st.success("💾 保存データあり")
            
            # データ情報を表示
            with st.expander("📋 保存データ詳細", expanded=True):
                st.json(data_info)
            
            # データ読み込みボタン
            if st.button("💾 保存データを読み込み", type="primary"):
                with st.spinner("データ読み込み中..."):
                    try:
                        df, target_data, metadata = load_data_from_file()
                        
                        if df is not None and not df.empty:
                            # セッションに保存
                            SessionManager.set_processed_df(df)
                            SessionManager.set_target_dict(target_data or {})
                            SessionManager.set_data_source('manual_load')
                            
                            if '手術実施日_dt' in df.columns:
                                SessionManager.set_latest_date(df['手術実施日_dt'].max())
                            
                            st.success(f"✅ データを読み込みました ({len(df):,}件)")
                            logger.info(f"手動データ読み込み完了: {len(df)}件")
                            st.rerun()
                        else:
                            st.error("❌ データ読み込みに失敗しました")
                            
                    except Exception as e:
                        st.error(f"❌ 読み込みエラー: {e}")
                        logger.error(f"データ読み込みエラー: {e}")
        else:
            st.info("💿 保存データなし")
            st.write("データアップロードページで新規データを処理してください。")
    
    @staticmethod
    def _render_session_data_section(file_sizes: dict) -> None:
        """セッションデータセクションを描画"""
        # ファイルサイズ情報
        if file_sizes:
            st.subheader("📁 ファイルサイズ")
            for name, size in file_sizes.items():
                st.write(f"• {name}: {size}")
        
        # 現在のセッションデータの状態
        st.subheader("🖥️ セッション状態")
        
        if SessionManager.is_data_loaded():
            df = SessionManager.get_processed_df()
            data_info = SessionManager.get_data_info()
            
            st.write(f"• レコード数: {data_info['record_count']:,}")
            st.write(f"• データソース: {data_info['data_source']}")
            
            if data_info['latest_date']:
                st.write(f"• 最新日付: {data_info['latest_date']}")
            
            # 現在のデータを保存
            if st.button("💾 現在のデータを保存"):
                DataManagementPage._save_current_session_data()
        else:
            st.info("セッションにデータがありません")
    
    @staticmethod
    @safe_file_operation("セッションデータ保存")
    def _save_current_session_data() -> None:
        """現在のセッションデータを保存"""
        try:
            df = SessionManager.get_processed_df()
            target_dict = SessionManager.get_target_dict()
            
            metadata = {
                'manual_save_time': datetime.now().isoformat(),
                'save_source': 'manual',
                'record_count': len(df)
            }
            
            save_success = save_data_to_file(df, target_dict, metadata)
            
            if save_success:
                st.success("✅ データを保存しました")
                logger.info("手動データ保存完了")
            else:
                st.error("❌ 保存に失敗しました")
                
        except Exception as e:
            st.error(f"❌ 保存エラー: {e}")
            logger.error(f"データ保存エラー: {e}")
    
    @staticmethod
    def _render_backup_management_tab() -> None:
        """バックアップ管理タブを描画"""
        st.subheader("🔄 バックアップ管理")
        
        backup_info = get_backup_info()
        
        if backup_info:
            st.write(f"📂 {len(backup_info)}個のバックアップファイル")
            
            # バックアップファイル一覧
            for i, backup in enumerate(backup_info):
                DataManagementPage._render_backup_item(backup, i)
        else:
            st.info("📭 バックアップファイルがありません")
        
        # 手動バックアップ作成
        DataManagementPage._render_manual_backup_section()
    
    @staticmethod
    @safe_file_operation("バックアップアイテム表示")
    def _render_backup_item(backup: dict, index: int) -> None:
        """個別バックアップアイテムを描画"""
        with st.expander(f"📄 {backup['timestamp']} ({backup['size']})"):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**ファイル名**: {backup['filename']}")
                st.write(f"**サイズ**: {backup['size']}")
                st.write(f"**作成日**: {backup['timestamp']}")
                st.write(f"**経過日数**: {backup['age_days']}日")
                
                if backup['has_metadata']:
                    st.write("✅ メタデータあり")
            
            with col2:
                if st.button("🔄 復元", key=f"restore_{index}"):
                    DataManagementPage._restore_backup(backup['filename'])
            
            with col3:
                if st.button("📥 ダウンロード", key=f"download_{index}"):
                    DataManagementPage._download_backup(backup)
    
    @staticmethod
    @safe_file_operation("バックアップ復元")
    def _restore_backup(filename: str) -> None:
        """バックアップを復元"""
        try:
            with st.spinner("バックアップ復元中..."):
                success, message = restore_from_backup(filename)
                
                if success:
                    st.success(f"✅ {message}")
                    SessionManager.set_data_source('restored')
                    logger.info(f"バックアップ復元完了: {filename}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
                    
        except Exception as e:
            st.error(f"❌ 復元エラー: {e}")
            logger.error(f"バックアップ復元エラー: {e}")
    
    @staticmethod
    def _download_backup(backup: dict) -> None:
        """バックアップファイルをダウンロード"""
        try:
            with open(backup['path'], 'rb') as f:
                st.download_button(
                    label="💾 ダウンロード開始",
                    data=f.read(),
                    file_name=backup['filename'],
                    mime="application/octet-stream",
                    key=f"download_btn_{backup['filename']}"
                )
        except Exception as e:
            st.error(f"❌ ダウンロードエラー: {e}")
    
    @staticmethod
    def _render_manual_backup_section() -> None:
        """手動バックアップセクションを描画"""
        st.subheader("📦 手動バックアップ作成")
        
        st.info("現在のデータをバックアップファイルとして保存します。")
        
        if st.button("🔄 現在のデータをバックアップ"):
            DataManagementPage._create_manual_backup()
    
    @staticmethod
    @safe_file_operation("手動バックアップ作成")
    def _create_manual_backup() -> None:
        """手動バックアップを作成"""
        try:
            with st.spinner("バックアップ作成中..."):
                backup_success = create_backup(force_create=True)
                
                if backup_success:
                    st.success("✅ バックアップを作成しました")
                    logger.info("手動バックアップ作成完了")
                else:
                    st.error("❌ バックアップ作成に失敗しました")
                    
        except Exception as e:
            st.error(f"❌ バックアップ作成エラー: {e}")
            logger.error(f"バックアップ作成エラー: {e}")
    
    @staticmethod
    def _render_export_import_tab() -> None:
        """エクスポート/インポートタブを描画"""
        col1, col2 = st.columns(2)
        
        with col1:
            DataManagementPage._render_export_section()
        
        with col2:
            DataManagementPage._render_import_section()
    
    @staticmethod
    @safe_file_operation("データエクスポート")
    def _render_export_section() -> None:
        """エクスポートセクションを描画"""
        st.subheader("📤 データエクスポート")
        
        st.info("全てのデータをZIPファイルとしてエクスポートします。")
        
        if st.button("📦 データパッケージをエクスポート"):
            with st.spinner("エクスポート中..."):
                try:
                    success, result = export_data_package()
                    
                    if success:
                        st.success("✅ エクスポート完了")
                        
                        # ダウンロードボタンを表示
                        with open(result, 'rb') as f:
                            st.download_button(
                                label="💾 エクスポートファイルをダウンロード",
                                data=f.read(),
                                file_name=result,
                                mime="application/zip"
                            )
                        logger.info(f"データエクスポート完了: {result}")
                    else:
                        st.error(f"❌ エクスポート失敗: {result}")
                        
                except Exception as e:
                    st.error(f"❌ エクスポートエラー: {e}")
                    logger.error(f"データエクスポートエラー: {e}")
    
    @staticmethod
    @safe_file_operation("データインポート")
    def _render_import_section() -> None:
        """インポートセクションを描画"""
        st.subheader("📥 データインポート")
        
        st.warning("⚠️ インポートすると現在のデータが上書きされます。事前にバックアップを作成することをお勧めします。")
        
        import_file = st.file_uploader(
            "データパッケージファイル (ZIP)", 
            type="zip",
            help="以前エクスポートしたZIPファイルを選択してください"
        )
        
        if import_file and st.button("📥 インポート実行"):
            with st.spinner("インポート中..."):
                try:
                    success, message = import_data_package(import_file)
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.info("🔄 ページを再読み込みしてデータを確認してください")
                        logger.info(f"データインポート完了: {message}")
                    else:
                        st.error(f"❌ {message}")
                        
                except Exception as e:
                    st.error(f"❌ インポートエラー: {e}")
                    logger.error(f"データインポートエラー: {e}")
    
    @staticmethod
    def _render_settings_tab() -> None:
        """詳細設定タブを描画"""
        st.subheader("⚙️ 詳細設定")
        
        # データ削除セクション
        DataManagementPage._render_data_deletion_section()
        
        st.markdown("---")
        
        # システム情報セクション
        DataManagementPage._render_system_info_section()
    
    @staticmethod
    def _render_data_deletion_section() -> None:
        """データ削除セクションを描画"""
        st.subheader("🗑️ データ削除")
        
        st.warning("⚠️ この操作は元に戻せません。全ての保存データとバックアップが削除されます。")
        
        # 確認チェックボックス
        confirm_delete = st.checkbox("削除を確認しました")
        
        if confirm_delete:
            if st.button("🗑️ 全データを削除", type="secondary"):
                DataManagementPage._delete_all_data()
    
    @staticmethod
    @safe_file_operation("全データ削除")
    def _delete_all_data() -> None:
        """全データを削除"""
        try:
            with st.spinner("データ削除中..."):
                success, result = delete_saved_data()
                
                if success:
                    st.success(f"✅ 削除完了: {', '.join(result)}")
                    
                    # セッション状態もクリア
                    SessionManager.clear_session_data()
                    
                    logger.info(f"全データ削除完了: {result}")
                    st.rerun()
                else:
                    st.error(f"❌ 削除失敗: {result}")
                    
        except Exception as e:
            st.error(f"❌ 削除エラー: {e}")
            logger.error(f"データ削除エラー: {e}")
    
    @staticmethod
    def _render_system_info_section() -> None:
        """システム情報セクションを描画"""
        st.subheader("ℹ️ システム情報")
        
        try:
            # バージョン情報
            st.write(f"• Streamlit バージョン: {st.__version__}")
            st.write(f"• Pandas バージョン: {pd.__version__}")
            
            # セッション情報
            data_info = SessionManager.get_data_info()
            st.write(f"• セッション状態: {'アクティブ' if data_info['has_data'] else '非アクティブ'}")
            
            if data_info['has_data']:
                st.write(f"• データ列数: {len(data_info['columns'])}")
                
            # 診療科数
            if SessionManager.is_data_loaded():
                df = SessionManager.get_processed_df()
                if '実施診療科' in df.columns:
                    dept_count = len(df['実施診療科'].dropna().unique())
                    st.write(f"• 診療科数: {dept_count}")
            
        except Exception as e:
            st.error(f"システム情報取得エラー: {e}")
    
    @staticmethod
    def get_data_management_summary() -> Dict[str, Any]:
        """データ管理サマリー情報を取得"""
        try:
            data_info = get_data_info()
            backup_info = get_backup_info()
            
            return {
                "has_saved_data": bool(data_info),
                "backup_count": len(backup_info) if backup_info else 0,
                "session_has_data": SessionManager.is_data_loaded(),
                "data_source": SessionManager.get_data_source(),
                "last_saved": data_info.get('last_saved') if data_info else None
            }
            
        except Exception as e:
            logger.error(f"データ管理サマリー取得エラー: {e}")
            return {"error": str(e)}