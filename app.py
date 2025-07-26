# app.py (最終版) - リファクタリング完了
"""
手術分析ダッシュボード - メインアプリケーション
リファクタリング版: UI層を完全分離した保守性の高いアーキテクチャ
Version 1.0.0 - 本番レディ
"""

import streamlit as st
from config import style_config
from ui import SessionManager, SidebarManager, render_current_page, ErrorHandler
from ui.error_handler import setup_global_exception_handler

# ページ設定 (必ず最初に実行)
st.set_page_config(
    page_title="手術分析ダッシュボード", 
    page_icon="🏥", 
    layout="wide", 
    initial_sidebar_state="expanded"
)


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
            with st.sidebar.spinner("HTML生成中..."):
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
                
    except Exception as e:
        logger.error(f"クイックHTML出力エラー: {e}")
        st.sidebar.error(f"HTML出力エラー: {e}")


def _display_high_score_stats():
    """ハイスコア統計情報をサイドバーに表示"""
    try:
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        
        if df.empty or not target_dict:
            return
        
        st.sidebar.markdown("**📈 ハイスコア統計**")
        
        # 基本統計
        total_depts = len(df['実施診療科'].dropna().unique())
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
                    
        except Exception as e:
            logger.debug(f"ハイスコア統計計算エラー: {e}")
            st.sidebar.info("統計計算中...")
            
    except Exception as e:
        logger.error(f"ハイスコア統計表示エラー: {e}")

def main():
    """メインアプリケーション"""
    try:
        # グローバル例外ハンドラー設定
        setup_global_exception_handler()
        
        # スタイル読み込み
        style_config.load_dashboard_css()
        
        # セッション状態初期化
        SessionManager.initialize_session_state()
        
        # サイドバー描画
        SidebarManager.render()
        
        # 現在のページを描画
        render_current_page()
        
    except Exception as e:
        ErrorHandler.handle_error(e, "メインアプリケーション", show_details=True)

if __name__ == "__main__":
    main()