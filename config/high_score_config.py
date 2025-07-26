# config/high_score_config.py
"""
ハイスコア機能の設定
"""

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
        import streamlit as st
        import pandas as pd
        import logging
        
        logger = logging.getLogger(__name__)
        
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
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"ハイスコア機能テストエラー: {e}")
        except:
            pass
        return False


# === app.py への追加コード（サイドバー統合）===

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


# === GitHub自動公開対応（既存のgithub_publisher.pyに追加する関数） ===

def publish_surgery_high_score_to_github(df, target_dict, period="直近12週"):
    """手術ハイスコア付きダッシュボードをGitHub Pagesに公開"""
    try:
        # GitHub設定取得
        github_token = st.session_state.get('github_token_input', '')
        repo_name = st.session_state.get('repo_name', 'Genie-Scripts/Streamlit-OR-Dashboard')
        branch_name = st.session_state.get('branch_name', 'main')
        
        if not github_token:
            st.error("GitHub Personal Access Tokenが設定されていません")
            return False
        
        # HTML生成
        from reporting.surgery_high_score_html import generate_complete_surgery_dashboard_html
        html_content = generate_complete_surgery_dashboard_html(df, target_dict, period)
        
        if not html_content:
            st.error("HTMLコンテンツの生成に失敗しました")
            return False
        
        # GitHub公開
        try:
            import requests
            import base64
            
            # GitHubにアップロード
            repo_parts = repo_name.split('/')
            if len(repo_parts) != 2:
                st.error("リポジトリ名の形式が正しくありません (owner/repo)")
                return False
            
            owner, repo = repo_parts
            file_path = "docs/index.html"
            
            # APIエンドポイント
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
            
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # 既存ファイルのSHA取得
            response = requests.get(api_url, headers=headers)
            sha = response.json().get('sha') if response.status_code == 200 else None
            
            # ファイル内容をBase64エンコード
            content_encoded = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
            
            # アップロードデータ
            commit_message = f"Update surgery dashboard with high score feature ({period})"
            data = {
                "message": commit_message,
                "content": content_encoded,
                "branch": branch_name
            }
            
            if sha:
                data["sha"] = sha
            
            # アップロード実行
            response = requests.put(api_url, json=data, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                public_url = f"https://{owner}.github.io/{repo}/docs/index.html"
                st.success(f"✅ 手術ハイスコア付きダッシュボードの公開が完了しました！")
                st.info("🏆 レポートの「🏆 手術ハイスコア」ボタンからランキングを確認できます。")
                st.markdown(f"🌐 [**公開サイトを開く**]({public_url})", unsafe_allow_html=True)
                return True
            else:
                error_msg = response.json().get('message', 'Unknown error')
                st.error(f"❌ 公開に失敗: {error_msg}")
                return False
                
        except Exception as e:
            st.error(f"GitHub公開エラー: {e}")
            return False
            
    except Exception as e:
        logger.error(f"手術ハイスコア公開エラー: {e}")
        st.error(f"公開処理でエラーが発生しました: {e}")
        return False


def create_surgery_high_score_github_interface():
    """手術ハイスコア用GitHub公開インターフェース"""
    try:
        st.sidebar.markdown("---")
        st.sidebar.header("🌐 ハイスコア付きレポート公開")
        
        # ハイスコア機能の状況確認
        high_score_available = test_high_score_functionality()
        
        if high_score_available:
            st.sidebar.success("🏆 ハイスコア機能: 利用可能")
        else:
            st.sidebar.info("📊 ハイスコア機能: 準備中（従来版で公開）")
        
        # GitHub設定
        st.sidebar.markdown("**🔗 GitHub設定**")
        github_token = st.sidebar.text_input(
            "Personal Access Token", 
            type="password", 
            key="github_token_surgery",
            help="GitHub Personal Access Token (repo権限必要)"
        )
        
        repo_name = st.sidebar.text_input(
            "リポジトリ名", 
            value="Genie-Scripts/Streamlit-OR-Dashboard",
            key="repo_name_surgery",
            help="username/repository形式"
        )
        
        branch_name = st.sidebar.selectbox(
            "ブランチ", 
            ["main", "master", "gh-pages"],
            key="branch_surgery"
        )
        
        # 公開設定
        st.sidebar.markdown("**⚙️ 公開設定**")
        period = st.sidebar.selectbox(
            "評価期間",
            PERIOD_OPTIONS,
            index=2,
            key="publish_period_surgery"
        )
        
        include_high_score = st.sidebar.checkbox(
            "ハイスコア機能を含める",
            value=high_score_available,
            disabled=not high_score_available,
            key="include_high_score_surgery"
        )
        
        # 公開ボタン
        if st.sidebar.button("🚀 公開実行", type="primary", key="publish_surgery_dashboard"):
            if not github_token:
                st.sidebar.error("GitHub Tokenが必要です")
            else:
                df = SessionManager.get_processed_df()
                target_dict = SessionManager.get_target_dict()
                
                if df.empty:
                    st.sidebar.error("データが読み込まれていません")
                elif not target_dict:
                    st.sidebar.error("目標データが設定されていません")
                else:
                    with st.sidebar.spinner("公開中..."):
                        if include_high_score:
                            success = publish_surgery_high_score_to_github(df, target_dict, period)
                        else:
                            # 従来版公開（既存機能を使用）
                            st.sidebar.info("従来版での公開は未実装")
                            success = False
                        
                        if success:
                            st.sidebar.success("✅ 公開完了！")
                        else:
                            st.sidebar.error("❌ 公開に失敗しました")
        
        # ヘルプ
        with st.sidebar.expander("❓ GitHub公開について"):
            st.markdown("""
            **🔧 事前設定が必要:**
            1. GitHubでリポジトリ作成
            2. Settings > Pages でgh-pages有効化
            3. Personal Access Token作成（repo権限）
            
            **🏆 ハイスコア機能:**
            - 診療科別週次パフォーマンス評価
            - TOP3ランキング表示
            - スコア詳細分析
            - 改善提案機能
            
            **📱 公開後:**
            - スマートフォン対応
            - リアルタイム更新
            - CSV出力機能
            """)
            
    except Exception as e:
        logger.error(f"手術ハイスコアGitHub公開インターフェースエラー: {e}")
        st.sidebar.error("GitHub公開機能でエラーが発生しました")


# === app.py のメイン関数への統合コード ===

def integrate_high_score_to_main_app():
    """メインアプリにハイスコア機能を統合"""
    try:
        # サイドバーにハイスコア機能追加
        create_high_score_sidebar_section()
        
        # GitHub公開機能追加
        create_surgery_high_score_github_interface()
        
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


# === 使用方法の例 ===
"""
app.pyのメイン部分に以下を追加:

# ハイスコア機能の統合
from config.high_score_config import integrate_high_score_to_main_app
integrate_high_score_to_main_app()

# 既存のサイドバー作成関数の後に追加
create_high_score_sidebar_section()
create_surgery_high_score_github_interface()
""".sidebar.expander("⚙️ ハイスコア設定"):
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
                    SessionManager.set_current_view("ダッシュボード")
                    st.session_state.show_high_score_tab = True
                    st.rerun()
            
            with col2:
                if st.button("📥 HTML出力", key="quick_html_export", use_container_width=True):
                    _generate_quick_html_export()
            
            # 統計情報
            _display_high_score_stats()
            
        else:
            st.sidebar.warning("⚠️ ハイスコア機能: 準備中")
            st.sidebar.info("データと目標設定を確認してください")
            
    except Exception as e:
        logger.error(f"ハイスコアサイドバー作成エラー: {e}")
        st.sidebar.error("ハイスコア機能でエラーが発生しました")


def test_high_score_functionality() -> bool:
    """ハイスコア機能の動作確認"""
    try:
        # データ確認
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        
        if df.empty:
            return False
        
        # 必要な列の確認
        required_columns = ['手術実施日_dt', '実施診療科', 'is_gas_20min']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"ハイスコア機能: 必要な列が不足 {missing_columns}")
            return False
        
        # 目標データの確認
        if not target_dict:
            logger.warning("ハイスコア機能: 目標データが設定されていません")
            return False
        
        # 最小データ量確認
        if len(df) < MIN_DATA_REQUIREMENTS['min_total_cases']:
            logger.warning("ハイスコア機能: データ量が不足")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"ハイスコア機能テストエラー: {e}")
        return False


def _generate_quick_html_export():
    """クイックHTML出力"""
    try:
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        
        if df.empty or not target_dict:
            st.sidebar.error("データまたは目標設定が不足しています")
            return
        
        # デフォルト期間取得
        period = st.session_state.get('high_score_default_period', '直近12週')
        
        with st