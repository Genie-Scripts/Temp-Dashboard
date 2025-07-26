# app.py の修正版（ハイスコア機能対応）

import streamlit as st
import pandas as pd
import logging
from datetime import datetime

# === 基本設定 ===
st.set_page_config(
    page_title="手術ダッシュボード",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === ログ設定 ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === 必要なモジュールのインポート ===
try:
    # 既存モジュール（必須）
    from ui.session_manager import SessionManager
    from ui.page_router import PageRouter
    from ui.error_handler import ErrorHandler
    from data_persistence import auto_load_data, save_data_to_file
    
    CORE_MODULES_AVAILABLE = True
except ImportError as e:
    st.error(f"コアモジュールのインポートに失敗しました: {e}")
    st.error("アプリケーションを正常に動作させるために必要なファイルが不足しています。")
    st.stop()

# ハイスコア機能（オプション）
try:
    from config.high_score_config import (
        PERIOD_OPTIONS, 
        MIN_DATA_REQUIREMENTS,
        test_high_score_functionality,
        create_high_score_sidebar_section,
        display_high_score_stats,
        generate_quick_html_export
    )
    HIGH_SCORE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ハイスコア機能が利用できません: {e}")
    # フォールバック設定
    PERIOD_OPTIONS = ["直近4週", "直近8週", "直近12週"]
    MIN_DATA_REQUIREMENTS = {'min_total_cases': 3}
    HIGH_SCORE_AVAILABLE = False
    
    # フォールバック関数
    def test_high_score_functionality(): return False
    def create_high_score_sidebar_section(): pass
    def display_high_score_stats(): pass
    def generate_quick_html_export(): st.sidebar.info("ハイスコア機能準備中")

# GitHub公開機能（オプション）
try:
    from reporting.surgery_github_publisher import create_surgery_github_publisher_interface
    GITHUB_PUBLISHER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"GitHub公開機能が利用できません: {e}")
    GITHUB_PUBLISHER_AVAILABLE = False
    
    # フォールバック関数
    def create_surgery_github_publisher_interface():
        st.sidebar.markdown("---")
        st.sidebar.header("🌐 GitHub公開機能")
        st.sidebar.info("GitHub公開機能は準備中です")


def main():
    """メインアプリケーション"""
    try:
        # セッション初期化
        SessionManager.initialize_session_state()
        
        # エラーハンドラー初期化
        ErrorHandler.initialize()
        
        # サイドバー作成
        create_sidebar()
        
        # メインコンテンツ表示
        router = PageRouter()
        router.render_current_page()
        
    except Exception as e:
        logger.error(f"アプリケーション実行エラー: {e}")
        st.error(f"アプリケーションエラーが発生しました: {e}")
        
        # デバッグ情報
        if st.checkbox("デバッグ情報を表示"):
            st.exception(e)


def create_sidebar():
    """サイドバーを作成"""
    try:
        st.sidebar.title("🏥 手術ダッシュボード")
        st.sidebar.markdown("---")
        
        # データ状況表示
        create_data_status_section()
        
        # ページナビゲーション
        create_navigation_section()
        
        # データ管理
        create_data_management_section()
        
        # ハイスコア機能セクション（新規追加）
        if HIGH_SCORE_AVAILABLE:
            create_high_score_sidebar_section()
        else:
            st.sidebar.markdown("---")
            st.sidebar.header("🏆 ハイスコア機能")
            st.sidebar.info("ハイスコア機能は準備中です")
        
        # GitHub公開機能（新規追加）
        if GITHUB_PUBLISHER_AVAILABLE:
            create_surgery_github_publisher_interface()
        else:
            st.sidebar.markdown("---")
            st.sidebar.header("🌐 GitHub公開機能")
            st.sidebar.info("GitHub公開機能は準備中です")
        
        # アプリ情報
        create_app_info_section()
        
    except Exception as e:
        logger.error(f"サイドバー作成エラー: {e}")
        st.sidebar.error("サイドバー作成でエラーが発生しました")


def create_data_status_section():
    """データ状況セクション"""
    try:
        st.sidebar.header("📊 データ状況")
        
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        latest_date = SessionManager.get_latest_date()
        
        if df.empty:
            st.sidebar.warning("データが読み込まれていません")
        else:
            st.sidebar.success(f"✅ データ読み込み済み")
            st.sidebar.metric("データ件数", f"{len(df):,}件")
            
            if latest_date:
                st.sidebar.metric("最新データ", latest_date.strftime('%Y/%m/%d'))
            
            if target_dict:
                st.sidebar.metric("目標設定", f"{len(target_dict)}診療科")
            else:
                st.sidebar.info("目標データ未設定")
                
    except Exception as e:
        logger.error(f"データ状況表示エラー: {e}")
        st.sidebar.error("データ状況表示エラー")


def create_navigation_section():
    """ナビゲーションセクション"""
    try:
        st.sidebar.header("🧭 ページナビゲーション")
        
        pages = [
            "ダッシュボード",
            "データアップロード", 
            "データ管理",
            "病院全体分析",
            "診療科別分析",
            "術者分析",
            "将来予測"
        ]
        
        current_view = SessionManager.get_current_view()
        
        for page in pages:
            if st.sidebar.button(
                page, 
                key=f"nav_{page}",
                use_container_width=True,
                type="primary" if page == current_view else "secondary"
            ):
                SessionManager.set_current_view(page)
                st.rerun()
                
    except Exception as e:
        logger.error(f"ナビゲーション作成エラー: {e}")
        st.sidebar.error("ナビゲーション作成エラー")


def create_data_management_section():
    """データ管理セクション"""
    try:
        st.sidebar.header("💾 データ管理")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("📥 データ読込", key="load_data", use_container_width=True):
                if auto_load_data():
                    st.sidebar.success("✅ データ読込完了")
                    st.rerun()
                else:
                    st.sidebar.warning("読込可能なデータがありません")
        
        with col2:
            if st.button("💾 データ保存", key="save_data", use_container_width=True):
                df = SessionManager.get_processed_df()
                target_dict = SessionManager.get_target_dict()
                
                if not df.empty:
                    metadata = {
                        'save_time': datetime.now().isoformat(),
                        'record_count': len(df),
                        'target_count': len(target_dict)
                    }
                    
                    if save_data_to_file(df, target_dict, metadata):
                        st.sidebar.success("✅ データ保存完了")
                    else:
                        st.sidebar.error("❌ データ保存失敗")
                else:
                    st.sidebar.warning("保存するデータがありません")
                    
    except Exception as e:
        logger.error(f"データ管理セクションエラー: {e}")
        st.sidebar.error("データ管理エラー")
    """データ管理セクション"""
    try:
        st.sidebar.header("💾 データ管理")
        
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("📥 データ読込", key="load_data", use_container_width=True):
                if auto_load_data():
                    st.sidebar.success("✅ データ読込完了")
                    st.rerun()
                else:
                    st.sidebar.warning("読込可能なデータがありません")
        
        with col2:
            if st.button("💾 データ保存", key="save_data", use_container_width=True):
                df = SessionManager.get_processed_df()
                target_dict = SessionManager.get_target_dict()
                
                if not df.empty:
                    metadata = {
                        'save_time': datetime.now().isoformat(),
                        'record_count': len(df),
                        'target_count': len(target_dict)
                    }
                    
                    if save_data_to_file(df, target_dict, metadata):
                        st.sidebar.success("✅ データ保存完了")
                    else:
                        st.sidebar.error("❌ データ保存失敗")
                else:
                    st.sidebar.warning("保存するデータがありません")
                    
    except Exception as e:
        logger.error(f"データ管理セクションエラー: {e}")
        st.sidebar.error("データ管理エラー")


def create_data_management_section():スコア統計計算エラー: {e}")
            st.sidebar.info("統計計算中...")
            
    except Exception as e:
        logger.error(f"ハイスコア統計表示エラー: {e}")


def create_app_info_section():
    """アプリ情報セクション"""
    try:
        st.sidebar.markdown("---")
        st.sidebar.header("ℹ️ アプリ情報")
        
        st.sidebar.markdown("**手術ダッシュボード v2.0**")
        st.sidebar.markdown("🏆 ハイスコア機能搭載")
        st.sidebar.markdown("📱 モバイル対応")
        st.sidebar.markdown("🌐 GitHub Pages対応")
        
        with st.sidebar.expander("更新履歴"):
            st.markdown("""
            **v2.0.0** (2025/07/27)
            - 🏆 ハイスコア機能追加
            - 🌐 GitHub自動公開機能
            - 📊 診療科別週次評価
            - 📱 レスポンシブデザイン
            
            **v1.0.0** (2025/07/01)
            - 基本ダッシュボード機能
            - データアップロード・管理
            - 診療科・術者分析
            """)
            
    except Exception as e:
        logger.error(f"アプリ情報表示エラー: {e}")


if __name__ == "__main__":
    main()