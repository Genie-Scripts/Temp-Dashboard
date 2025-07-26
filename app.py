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
    # 既存モジュール
    from ui.session_manager import SessionManager
    from ui.page_router import PageRouter
    from ui.error_handler import ErrorHandler
    from data_persistence import auto_load_data, save_data_to_file
    
    # ハイスコア機能設定のみインポート（関数は後で定義）
    from config.high_score_config import PERIOD_OPTIONS, MIN_DATA_REQUIREMENTS
    
    # GitHub公開機能（インポートエラーを許容）
    try:
        from reporting.surgery_github_publisher import create_surgery_github_publisher_interface
        GITHUB_PUBLISHER_AVAILABLE = True
    except ImportError:
        GITHUB_PUBLISHER_AVAILABLE = False
        logger.warning("GitHub公開機能が利用できません")
    
except ImportError as e:
    st.error(f"必要なモジュールのインポートに失敗しました: {e}")
    st.info("一部機能が制限される可能性がありますが、基本機能は利用可能です。")
    
    # フォールバック設定
    PERIOD_OPTIONS = ["直近4週", "直近8週", "直近12週"]
    MIN_DATA_REQUIREMENTS = {'min_total_cases': 3}
    GITHUB_PUBLISHER_AVAILABLE = False


def test_high_score_functionality() -> bool:
    """ハイスコア機能の動作確認（app.py内定義）"""
    try:
        # データ確認
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        
        if df.empty:
            return False
        
        # 必要な列の確認
        required_columns = ['手術実施日_dt', '実施診療科']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"ハイスコア機能: 必要な列が不足 {missing_columns}")
            return False
        
        # 目標データの確認
        if not target_dict:
            return False
        
        # 最小データ量確認
        min_cases = MIN_DATA_REQUIREMENTS.get('min_total_cases', 3)
        if len(df) < min_cases:
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"ハイスコア機能テストエラー: {e}")
        return False


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
        create_high_score_sidebar_section()
        
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


def create_high_score_sidebar_section():
    """ハイスコア機能サイドバーセクション（新規）"""
    try:
        st.sidebar.markdown("---")
        st.sidebar.header("🏆 ハイスコア機能")
        
        # ハイスコア機能の状況確認
        high_score_available = test_high_score_functionality()
        
        if high_score_available:
            st.sidebar.success("✅ ハイスコア機能: 利用可能")
            
            # クイック設定
            with st.sidebar.expander("⚙️ ハイスコア設定"):
                default_period = st.selectbox(
                    "デフォルト評価期間",
                    PERIOD_OPTIONS,
                    index=2,  # 直近12週
                    key="high_score_default_period"
                )
                
                show_details = st.checkbox(
                    "詳細表示をデフォルトで有効",
                    value=False,
                    key="high_score_default_details"
                )
            
            # クイックアクション
            col1, col2 = st.sidebar.columns(2)
            
            with col1:
                if st.button("📊 ランキング", key="quick_high_score", use_container_width=True):
                    SessionManager.set_current_view("ダッシュボード")
                    st.session_state.show_high_score_tab = True
                    st.rerun()
            
            with col2:
                if st.button("📥 HTML出力", key="quick_html_export", use_container_width=True):
                    generate_quick_html_export()
            
            # 統計情報
            display_high_score_stats()
            
        else:
            st.sidebar.warning("⚠️ ハイスコア機能: 準備中")
            st.sidebar.info("データと目標設定を確認してください")
            
    except Exception as e:
        logger.error(f"ハイスコアサイドバー作成エラー: {e}")
        st.sidebar.error("ハイスコア機能でエラーが発生しました")


def generate_quick_html_export():
    """クイックHTML出力（安全版）"""
    try:
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        
        if df.empty or not target_dict:
            st.sidebar.error("データまたは目標設定が不足しています")
            return
        
        # デフォルト期間取得
        period = st.session_state.get('high_score_default_period', '直近12週')
        
        with st.sidebar.spinner("HTML生成中..."):
            # HTML生成機能を呼び出し（安全版）
            try:
                from reporting.surgery_high_score_html import generate_complete_surgery_dashboard_html
                
                html_content = generate_complete_surgery_dashboard_html(df, target_dict, period)
                
                if html_content:
                    # HTMLファイルとしてダウンロード提供
                    st.sidebar.download_button(
                        label="📥 ダッシュボードHTML",
                        data=html_content,
                        file_name=f"手術ダッシュボード_ハイスコア付き_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                        mime="text/html",
                        key="download_high_score_html"
                    )
                    st.sidebar.success("✅ HTML生成完了")
                else:
                    st.sidebar.error("❌ HTML生成に失敗しました")
                    
            except ImportError as e:
                st.sidebar.warning(f"HTML生成機能が利用できません: {e}")
                # 簡易HTML生成のフォールバック
                simple_html = f"""
                <!DOCTYPE html>
                <html lang="ja">
                <head>
                    <meta charset="UTF-8">
                    <title>手術ダッシュボード - {period}</title>
                </head>
                <body>
                    <h1>🏥 手術ダッシュボード</h1>
                    <p>期間: {period}</p>
                    <p>データ件数: {len(df):,}件</p>
                    <p>目標設定: {len(target_dict)}診療科</p>
                    <p>生成日時: {datetime.now().strftime('%Y/%m/%d %H:%M')}</p>
                </body>
                </html>
                """
                
                st.sidebar.download_button(
                    label="📥 簡易HTML",
                    data=simple_html,
                    file_name=f"簡易ダッシュボード_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                    mime="text/html",
                    key="download_simple_html"
                )
                st.sidebar.info("✅ 簡易版HTML生成完了")
                
            except Exception as e:
                st.sidebar.error(f"HTML生成エラー: {e}")
                logger.error(f"HTML生成エラー: {e}")
                
    except Exception as e:
        logger.error(f"クイックHTML出力エラー: {e}")
        st.sidebar.error(f"HTML出力エラー: {e}")


def display_high_score_stats():
    """ハイスコア統計情報をサイドバーに表示"""
    try:
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        
        if df.empty or not target_dict:
            return
        
        st.sidebar.markdown("**📈 ハイスコア統計**")
        
        # 基本統計
        total_depts = len(df['実施診療科'].dropna().unique()) if '実施診療科' in df.columns else 0
        target_depts = len(target_dict)
        
        st.sidebar.metric("対象診療科数", f"{target_depts}科")
        st.sidebar.metric("総診療科数", f"{total_depts}科")
        
        # 簡易スコア計算（概算）
        try:
            from analysis.surgery_high_score import calculate_surgery_high_scores
            
            period = st.session_state.get('high_score_default_period', '直近12週')
            dept_scores = calculate_surgery_high_scores(df, target_dict, period)
            
            if dept_scores:
                avg_score = sum(d['total_score'] for d in dept_scores) / len(dept_scores)
                high_achievers = len([d for d in dept_scores if d['achievement_rate'] >= 100])
                
                st.sidebar.metric("平均スコア", f"{avg_score:.1f}点")
                st.sidebar.metric("目標達成科数", f"{high_achievers}科")
                
                # TOP診療科表示
                if dept_scores:
                    top_dept = dept_scores[0]
                    st.sidebar.markdown(f"**🥇 現在の1位**")
                    st.sidebar.markdown(f"**{top_dept['display_name']}**")
                    st.sidebar.markdown(f"スコア: {top_dept['total_score']:.1f}点 ({top_dept['grade']}グレード)")
                    
        except ImportError:
            st.sidebar.info("統計計算機能準備中...")
        except Exception as e:
            logger.debug(f"ハイスコア統計計算エラー: {e}")
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