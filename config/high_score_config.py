# config/high_score_config.py
"""
ハイスコア機能の設定（完全版）
"""

import pandas as pd
import streamlit as st
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# スコア配点設定
SCORE_WEIGHTS = {
    'gas_surgery_total': 70,      # 全身麻酔手術評価の総点数
    'total_cases_total': 15,      # 全手術件数評価の総点数  
    'total_hours_total': 15,      # 総手術時間評価の総点数
    
    # 全身麻酔手術評価の内訳
    'gas_achievement': 30,        # 直近週達成度
    'gas_improvement': 20,        # 改善度
    'gas_stability': 15,          # 安定性
    'gas_trend': 5,              # 持続性
}

# グレード判定基準
GRADE_THRESHOLDS = {
    'S': 85,
    'A': 75, 
    'B': 65,
    'C': 50,
    'D': 0
}

# 評価期間オプション
PERIOD_OPTIONS = [
    "直近4週",
    "直近8週", 
    "直近12週"
]

# 最小データ要件
MIN_DATA_REQUIREMENTS = {
    'min_weeks': 2,              # 最小週数
    'min_cases_per_week': 1,     # 週あたり最小症例数
    'min_total_cases': 3,        # 期間全体の最小症例数
}

# 表示設定
DISPLAY_CONFIG = {
    'show_top_n': 3,             # TOP N位まで詳細表示
    'show_all_ranking': True,     # 全ランキング表示
    'enable_csv_download': True,  # CSVダウンロード機能
    'enable_details_view': True,  # 詳細ビュー
}

# HTML出力設定
HTML_CONFIG = {
    'button_label': '🏆 手術ハイスコア',
    'section_title': '🏆 診療科別手術ハイスコア TOP3',
    'view_id': 'view-surgery-high-score',
    'enable_weekly_insights': True,
}


def test_high_score_functionality() -> bool:
    """ハイスコア機能の動作確認"""
    try:
        # SessionManagerのインポート
        try:
            from ui.session_manager import SessionManager
        except ImportError:
            logger.warning("SessionManagerのインポートに失敗")
            return False
        
        # データ確認
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        
        if df.empty:
            logger.info("ハイスコア機能: データが空です")
            return False
        
        # 必要な列の確認
        required_columns = ['手術実施日_dt', '実施診療科']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"ハイスコア機能: 必要な列が不足 {missing_columns}")
            return False
        
        # 目標データの確認
        if not target_dict:
            logger.info("ハイスコア機能: 目標データが設定されていません")
            return False
        
        # 最小データ量確認
        if len(df) < MIN_DATA_REQUIREMENTS['min_total_cases']:
            logger.info("ハイスコア機能: データ量が不足")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"ハイスコア機能テストエラー: {e}")
        return False


def create_high_score_sidebar_section():
    """サイドバーにハイスコア機能セクションを追加"""
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
                
                auto_refresh = st.checkbox(
                    "自動更新（データ変更時）",
                    value=True,
                    key="high_score_auto_refresh"
                )
            
            # クイックアクション
            col1, col2 = st.sidebar.columns(2)
            
            with col1:
                if st.button("📊 ランキング表示", key="quick_high_score", use_container_width=True):
                    try:
                        from ui.session_manager import SessionManager
                        SessionManager.set_current_view("ダッシュボード")
                        st.session_state.show_high_score_tab = True
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"ページ移動エラー: {e}")
            
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
    """クイックHTML出力"""
    try:
        # SessionManagerのインポート
        try:
            from ui.session_manager import SessionManager
        except ImportError:
            st.sidebar.error("SessionManagerが利用できません")
            return
        
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
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; }}
                        .header {{ text-align: center; margin-bottom: 40px; }}
                        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }}
                        .stat-card {{ background: #f0f0f0; padding: 20px; border-radius: 8px; text-align: center; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>🏥 手術ダッシュボード</h1>
                        <p>期間: {period}</p>
                        <p>生成日時: {datetime.now().strftime('%Y/%m/%d %H:%M')}</p>
                    </div>
                    <div class="stats">
                        <div class="stat-card">
                            <h3>📊 データ件数</h3>
                            <p>{len(df):,}件</p>
                        </div>
                        <div class="stat-card">
                            <h3>🎯 目標設定</h3>
                            <p>{len(target_dict)}診療科</p>
                        </div>
                        <div class="stat-card">
                            <h3>🏥 診療科数</h3>
                            <p>{df['実施診療科'].nunique() if '実施診療科' in df.columns else 0}科</p>
                        </div>
                    </div>
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
        # SessionManagerのインポート
        try:
            from ui.session_manager import SessionManager
        except ImportError:
            st.sidebar.warning("統計情報が利用できません")
            return
        
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
            st.sidebar.info("詳細統計は準備中...")
        except Exception as e:
            logger.debug(f"ハイスコア統計計算エラー: {e}")
            st.sidebar.info("統計計算中...")
            
    except Exception as e:
        logger.error(f"ハイスコア統計表示エラー: {e}")


def integrate_high_score_to_main_app():
    """メインアプリにハイスコア機能を統合"""
    try:
        # サイドバーにハイスコア機能追加
        create_high_score_sidebar_section()
        
        # セッション状態の初期化
        if 'show_high_score_tab' not in st.session_state:
            st.session_state.show_high_score_tab = False
        
        # ダッシュボードページでハイスコアタブを自動選択
        if st.session_state.get('show_high_score_tab', False):
            st.session_state.show_high_score_tab = False  # リセット
            # ここでハイスコアタブをアクティブにする処理
            # 実際の実装ではst.tabsのselected_indexを制御
        
        logger.info("✅ ハイスコア機能統合完了")
        return True
        
    except Exception as e:
        logger.error(f"ハイスコア機能統合エラー: {e}")
        return False