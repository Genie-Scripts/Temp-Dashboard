import os
import requests
import base64
from datetime import datetime
import streamlit as st
import pandas as pd
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

class GitHubPublisher:
    """GitHub Pages公開機能を提供するクラス"""
    
    def __init__(self, repo_owner, repo_name, token, branch="main"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.token = token
        self.branch = branch
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        
    def validate_token(self):
        """GitHubトークンの有効性を確認"""
        try:
            headers = {"Authorization": f"token {self.token}"}
            response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"トークン検証エラー: {e}")
            return False
        
    def upload_html_file(self, html_content, file_path, commit_message=None):
        """HTMLファイルをGitHubにアップロード（シンプル版）"""
        try:
            if not self.validate_token():
                return False, "GitHubトークンが無効です"
                
            file_url = f"{self.base_url}/contents/{file_path}"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.get(file_url, headers=headers, timeout=10)
            sha = response.json().get("sha") if response.status_code == 200 else None
            
            content_encoded = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
            
            if not commit_message:
                commit_message = f"Update Report: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            data = {"message": commit_message, "content": content_encoded, "branch": self.branch}
            if sha:
                data["sha"] = sha
            
            response_put = requests.put(file_url, json=data, headers=headers, timeout=30)
            
            if response_put.status_code in [200, 201]:
                return True, f"Successfully uploaded: {file_path}"
            else:
                error_msg = response_put.json().get('message', 'Unknown error')
                return False, f"Upload failed: {error_msg}"
                
        except Exception as e:
            logger.error(f"アップロードエラー: {e}", exc_info=True)
            return False, f"Error uploading file: {str(e)}"

    def get_public_url(self):
        """公開URLを取得"""
        return f"https://{self.repo_owner}.github.io/{self.repo_name}/docs/index.html"

def check_publish_readiness() -> Tuple[bool, str]:
    """GitHub公開の準備状況確認"""
    if not st.session_state.get('data_processed', False):
        return False, "データが読み込まれていません。"
    df = st.session_state.get('df')
    if df is None or df.empty:
        return False, "有効なデータが見つかりません。"
    return True, "公開可能です。"

def create_github_publisher_interface():
    """GitHub自動公開インターフェース（最終版）"""
    st.sidebar.markdown("---")
    st.sidebar.header("🌐 Webレポート公開機能")

    st.sidebar.markdown("**🔗 GitHub設定**")
    github_token = st.sidebar.text_input("Personal Access Token", type="password", key="github_token_input")
    repo_name_input = st.sidebar.text_input("リポジトリ名", value="Genie-Scripts/Streamlit-Inpatient-Dashboard", help="username/repository形式")
    branch_name = st.sidebar.selectbox("ブランチ", ["main", "gh-pages", "master"], index=0)

    if st.sidebar.button("🧪 設定を適用", key="apply_github_settings", use_container_width=True):
        if github_token and repo_name_input:
            owner, repo = repo_name_input.split('/')
            st.session_state.github_publisher = GitHubPublisher(repo_owner=owner, repo_name=repo, token=github_token, branch=branch_name)
            st.sidebar.success("✅ 設定が適用されました。")
        else:
            st.sidebar.error("❌ Tokenとリポジトリ名を入力してください。")

    if st.session_state.get('github_publisher'):
        can_publish, status_message = check_publish_readiness()
        
        if can_publish:
            st.sidebar.markdown("**📊 公開設定**")
            
            period_options = ["直近4週間", "直近8週", "直近12週", "今年度"]
            selected_period = st.sidebar.selectbox("📅 分析期間", period_options, index=0, key="github_analysis_period")
            
            if st.sidebar.button("🚀 統合レポートを公開", key="execute_publish_button", use_container_width=True, type="primary"):
                execute_github_publish(selected_period)
        else:
            st.sidebar.warning(f"⚠️ {status_message}")

def execute_github_publish(period: str):
    """単一ファイルの統合レポートを生成・公開する"""
    publisher = st.session_state.get('github_publisher')
    if not publisher:
        st.error("GitHub設定が適用されていません。")
        return

    df = st.session_state.get('df')
    target_data = st.session_state.get('target_data', pd.DataFrame())

    with st.spinner(f"🚀 統合レポートを生成・公開中... (期間: {period})"):
        from html_export_functions import generate_all_in_one_html_report
        
        html_content = generate_all_in_one_html_report(df, target_data, period)
        
        if html_content and "エラー" not in html_content:
            success, msg = publisher.upload_html_file(html_content, "docs/index.html", f"Update All-in-One Report ({period})")
            if success:
                st.success("✅ 統合レポートの公開が完了しました！")
                public_url = publisher.get_public_url()
                st.markdown(f"🌐 [**公開サイトを開く**]({public_url})", unsafe_allow_html=True)
            else:
                st.error(f"❌ 公開に失敗: {msg}")
        else:
            st.error("❌ HTMLコンテンツの生成に失敗しました。")