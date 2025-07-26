# ui/sidebar.py
"""
サイドバーUI管理モジュール
アプリケーションのサイドバー表示を管理
"""

import streamlit as st
import pytz
from datetime import datetime
from typing import List, Optional

from ui.session_manager import SessionManager
from ui.error_handler import safe_streamlit_operation, ErrorReporting
from data_persistence import get_data_info


class SidebarManager:
    """サイドバーを管理するクラス"""
    
    # ナビゲーションビューの定義
    NAVIGATION_VIEWS = [
        "ダッシュボード", 
        "病院全体分析",
        "診療科別分析",
        "術者分析",
        "将来予測",
        "データアップロード",
        "データ管理"
    ]
    
    @staticmethod
    @safe_streamlit_operation("サイドバー描画")
    def render() -> None:
        """サイドバー全体を描画"""
        with st.sidebar:
            SidebarManager._render_header()
            SidebarManager._render_data_status()
            SidebarManager._render_navigation()
            SidebarManager._render_footer()

    @staticmethod
    def _render_header() -> None:
        """ヘッダー部分を描画"""
        st.title("🏥 手術分析")
        st.markdown("---")

    @staticmethod
    def _render_data_status() -> None:
        """データ状態表示部分を描画"""
        try:
            data_info = get_data_info()
            
            # メインデータの状態
            if SessionManager.is_data_loaded():
                SidebarManager._render_data_loaded_status(data_info)
            else:
                SidebarManager._render_no_data_status(data_info)
            
            # 目標データの状態
            SidebarManager._render_target_status()
            
            st.markdown("---")
            
        except Exception as e:
            st.error(f"データ状態表示エラー: {e}")

    @staticmethod
    def _render_data_loaded_status(data_info: dict) -> None:
        """データ読み込み済み状態を表示"""
        st.success("✅ データ読み込み済み")
        
        # レコード数表示
        df = SessionManager.get_processed_df()
        if not df.empty:
            record_count = len(df)
            st.write(f"📊 レコード数: {record_count:,}")
        
        # 最新日付表示
        latest_date = SessionManager.get_latest_date()
        if latest_date:
            st.write(f"📅 最新日付: {latest_date.strftime('%Y/%m/%d')}")
        
        # データソース表示
        data_source = SessionManager.get_data_source()
        if data_source == 'auto_loaded':
            st.info("💾 保存データを自動読み込み")
        elif data_source == 'file_upload':
            st.info("📤 新規データをアップロード")
        elif data_source == 'restored':
            st.info("🔄 バックアップから復元")
        elif data_source == 'manual_load':
            st.info("👤 手動でデータ読み込み")
        
        # 保存データの情報
        if data_info:
            last_saved = data_info.get('last_saved', 'unknown')
            if last_saved != 'unknown':
                try:
                    saved_time = datetime.fromisoformat(last_saved.replace('Z', '+00:00'))
                    st.caption(f"💾 保存: {saved_time.strftime('%m/%d %H:%M')}")
                except:
                    st.caption("💾 保存済み")

    @staticmethod
    def _render_no_data_status(data_info: dict) -> None:
        """データ未読み込み状態を表示"""
        st.warning("⚠️ データ未読み込み")
        
        if data_info:
            st.info("💾 保存データあり - データ管理で確認")
        else:
            st.info("📤 データアップロードから開始")

    @staticmethod
    def _render_target_status() -> None:
        """目標データの状態を表示"""
        target_dict = SessionManager.get_target_dict()
        
        if target_dict:
            target_count = len(target_dict)
            st.success(f"🎯 目標データ設定済み ({target_count}件)")
        else:
            st.info("🎯 目標データ未設定")

    @staticmethod
    def _render_navigation() -> None:
        """ナビゲーション部分を描画"""
        st.subheader("📍 ナビゲーション")
        
        # 現在のビューを取得
        current_view = SessionManager.get_current_view()
        
        # ラジオボタンでビュー選択（key設定を改善）
        try:
            current_index = SidebarManager.NAVIGATION_VIEWS.index(current_view)
        except ValueError:
            current_index = 0  # デフォルトはダッシュボード
        
        selected_view = st.radio(
            "ページ選択",
            SidebarManager.NAVIGATION_VIEWS,
            index=current_index,
            key="navigation_radio",  # 一意のキー名
            help="分析ページを選択してください"
        )
        
        # ビューが変更された場合のみセッションを更新
        if selected_view != current_view:
            SessionManager.set_current_view(selected_view)
            st.rerun()  # 即座に再描画
        
        # データが必要なページでデータ未読み込みの場合の警告
        data_required_views = [
            "ダッシュボード", "病院全体分析", "診療科別分析", "術者分析", "将来予測"
        ]
        
        if selected_view in data_required_views and not SessionManager.is_data_loaded():
            st.warning("⚠️ このページはデータが必要です")

    @staticmethod
    def _render_footer() -> None:
        """フッター部分を描画"""
        st.markdown("---")
        
        # バージョン情報
        st.info("Version: 6.0 (データ永続化対応)")
        
        # 現在時刻
        jst = pytz.timezone('Asia/Tokyo')
        current_time = datetime.now(jst).strftime('%H:%M:%S')
        st.write(f"現在時刻: {current_time}")
        
        # エラー統計（デバッグ情報）
        SidebarManager._render_debug_info()

    @staticmethod
    def _render_debug_info() -> None:
        """デバッグ情報を表示"""
        try:
            error_stats = ErrorReporting.get_error_stats()
            
            if error_stats.get('total_errors', 0) > 0:
                with st.expander("🐛 デバッグ情報", expanded=False):
                    st.write(f"エラー数: {error_stats.get('total_errors', 0)}")
                    st.write(f"警告数: {error_stats.get('warnings', 0)}")
                    
                    if error_stats.get('critical', 0) > 0:
                        st.error(f"重大エラー: {error_stats['critical']}")
            
        except Exception as e:
            # デバッグ情報でエラーが起きても本体に影響しないよう無視
            pass

    @staticmethod
    def get_current_view() -> str:
        """現在選択されているビューを取得"""
        return SessionManager.get_current_view()

    @staticmethod
    def set_current_view(view: str) -> None:
        """ビューを設定"""
        if view in SidebarManager.NAVIGATION_VIEWS:
            SessionManager.set_current_view(view)
        else:
            raise ValueError(f"無効なビュー: {view}")

    @staticmethod
    def render_quick_actions() -> None:
        """クイックアクション（必要に応じて使用）"""
        with st.sidebar:
            st.markdown("---")
            st.subheader("⚡ クイックアクション")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔄", help="ページ更新"):
                    st.rerun()
            
            with col2:
                if st.button("🏠", help="ダッシュボードに戻る"):
                    SessionManager.set_current_view("ダッシュボード")
                    st.rerun()

    @staticmethod
    def render_data_summary_card() -> None:
        """データサマリーカード（オプション）"""
        if SessionManager.is_data_loaded():
            data_info = SessionManager.get_data_info()
            
            with st.sidebar:
                with st.container():
                    st.markdown("""
                    <div style="
                        background-color: #f0f2f6;
                        padding: 10px;
                        border-radius: 5px;
                        margin: 10px 0;
                    ">
                        <small><b>📊 データサマリー</b></small><br>
                        <small>レコード: {record_count:,}件</small><br>
                        <small>診療科: {dept_count}科</small><br>
                        <small>期間: {date_range}</small>
                    </div>
                    """.format(
                        record_count=data_info.get('record_count', 0),
                        dept_count=len(set(SessionManager.get_processed_df()['実施診療科'].dropna())) if not SessionManager.get_processed_df().empty else 0,
                        date_range=SidebarManager._get_date_range_string()
                    ), unsafe_allow_html=True)

    @staticmethod
    def _get_date_range_string() -> str:
        """日付範囲の文字列を取得"""
        try:
            df = SessionManager.get_processed_df()
            if df.empty or '手術実施日_dt' not in df.columns:
                return "N/A"
            
            min_date = df['手術実施日_dt'].min()
            max_date = df['手術実施日_dt'].max()
            
            return f"{min_date.strftime('%m/%d')} - {max_date.strftime('%m/%d')}"
            
        except Exception:
            return "N/A"