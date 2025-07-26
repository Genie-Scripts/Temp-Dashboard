# reporting/surgery_github_publisher.py
"""
手術ダッシュボード専用GitHub公開機能
入院ダッシュボードとは独立した実装
"""

import streamlit as st
import pandas as pd
import requests
import base64
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class SurgeryGitHubPublisher:
    """手術ダッシュボード用GitHub公開クラス"""
    
    def __init__(self, token: str, repo_owner: str, repo_name: str, branch: str = "main"):
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.api_base = "https://api.github.com"
        
    def publish_surgery_dashboard(self, df: pd.DataFrame, target_dict: Dict[str, float], 
                                period: str = "直近12週", include_high_score: bool = True) -> Tuple[bool, str]:
        """手術ダッシュボードをGitHub Pagesに公開"""
        try:
            logger.info(f"手術ダッシュボード公開開始: {self.repo_owner}/{self.repo_name}")
            
            # HTML生成
            html_content = self._generate_complete_html(df, target_dict, period, include_high_score)
            if not html_content:
                return False, "HTMLコンテンツの生成に失敗しました"
            
            # GitHub Pages用ディレクトリ設定
            docs_files = [
                ("docs/index.html", html_content),
                ("docs/README.md", self._generate_readme()),
                (".github/workflows/pages.yml", self._generate_github_actions())
            ]
            
            # ファイルをアップロード
            success_count = 0
            for file_path, content in docs_files:
                success, msg = self._upload_file(file_path, content, f"Update {file_path}")
                if success:
                    success_count += 1
                else:
                    logger.warning(f"ファイルアップロード失敗: {file_path} - {msg}")
            
            if success_count == len(docs_files):
                public_url = self.get_public_url()
                return True, f"公開完了: {public_url}"
            else:
                return False, f"一部ファイルの公開に失敗しました ({success_count}/{len(docs_files)})"
                
        except Exception as e:
            logger.error(f"手術ダッシュボード公開エラー: {e}")
            return False, f"公開エラー: {str(e)}"
    
    def _generate_complete_html(self, df: pd.DataFrame, target_dict: Dict[str, float], 
                               period: str, include_high_score: bool) -> Optional[str]:
        """完全なHTMLコンテンツを生成"""
        try:
            from reporting.surgery_high_score_html import generate_complete_surgery_dashboard_html
            from analysis.surgery_high_score import calculate_surgery_high_scores
            
            if include_high_score:
                # ハイスコア機能付きHTML
                return generate_complete_surgery_dashboard_html(df, target_dict, period)
            else:
                # 基本ダッシュボードHTML
                return self._generate_basic_dashboard_html(df, target_dict, period)
                
        except Exception as e:
            logger.error(f"HTML生成エラー: {e}")
            return None
    
    def _generate_basic_dashboard_html(self, df: pd.DataFrame, target_dict: Dict[str, float], 
                                     period: str) -> str:
        """基本的な手術ダッシュボードHTML生成"""
        try:
            # 基本統計計算
            total_cases = len(df)
            gas_cases = len(df[df['is_gas_20min']]) if 'is_gas_20min' in df.columns else 0
            departments = df['実施診療科'].nunique() if '実施診療科' in df.columns else 0
            
            # 診療科別統計
            dept_stats = ""
            if '実施診療科' in df.columns:
                dept_summary = df.groupby('実施診療科').size().sort_values(ascending=False).head(10)
                for dept, count in dept_summary.items():
                    achievement = (count / target_dict.get(dept, count)) * 100 if dept in target_dict else 100
                    dept_stats += f"""
                    <tr>
                        <td>{dept}</td>
                        <td>{count}件</td>
                        <td>{target_dict.get(dept, '--')}件</td>
                        <td>{achievement:.1f}%</td>
                    </tr>
                    """
            
            html_template = f"""
            <!DOCTYPE html>
            <html lang="ja">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>手術ダッシュボード - {period}</title>
                <style>
                    {self._get_dashboard_css()}
                </style>
            </head>
            <body>
                <div class="container">
                    <header class="header">
                        <h1>🏥 手術ダッシュボード</h1>
                        <p class="period">評価期間: {period} | 更新: {datetime.now().strftime('%Y/%m/%d %H:%M')}</p>
                    </header>
                    
                    <div class="main-content">
                        <div class="kpi-section">
                            <h2>📊 主要指標</h2>
                            <div class="kpi-grid">
                                <div class="kpi-card">
                                    <div class="kpi-title">全手術件数</div>
                                    <div class="kpi-value">{total_cases:,}件</div>
                                </div>
                                <div class="kpi-card">
                                    <div class="kpi-title">全身麻酔手術件数</div>
                                    <div class="kpi-value">{gas_cases:,}件</div>
                                </div>
                                <div class="kpi-card">
                                    <div class="kpi-title">対象診療科数</div>
                                    <div class="kpi-value">{departments}科</div>
                                </div>
                                <div class="kpi-card">
                                    <div class="kpi-title">目標設定科数</div>
                                    <div class="kpi-value">{len(target_dict)}科</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="dept-section">
                            <h2>🏥 診療科別実績</h2>
                            <div class="table-container">
                                <table class="dept-table">
                                    <thead>
                                        <tr>
                                            <th>診療科</th>
                                            <th>実績</th>
                                            <th>目標</th>
                                            <th>達成率</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {dept_stats}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        
                        <footer class="footer">
                            <p>🤖 Streamlit手術ダッシュボード | 
                               📈 リアルタイム分析 | 
                               📱 モバイル対応</p>
                        </footer>
                    </div>
                </div>
            </body>
            </html>
            """
            
            return html_template
            
        except Exception as e:
            logger.error(f"基本HTML生成エラー: {e}")
            return self._get_error_html(str(e))
    
    def _get_dashboard_css(self) -> str:
        """ダッシュボード用CSS"""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans JP', sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            color: #2c3e50;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 40px;
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        
        .period {
            color: #7f8c8d;
            font-size: 1.1em;
        }
        
        .main-content {
            display: grid;
            gap: 30px;
        }
        
        .kpi-section {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .kpi-section h2 {
            margin-bottom: 20px;
            color: #2c3e50;
        }
        
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        
        .kpi-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            transition: transform 0.3s ease;
        }
        
        .kpi-card:hover {
            transform: translateY(-5px);
        }
        
        .kpi-title {
            font-size: 1em;
            margin-bottom: 10px;
            opacity: 0.9;
        }
        
        .kpi-value {
            font-size: 2.2em;
            font-weight: bold;
        }
        
        .dept-section {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .dept-section h2 {
            margin-bottom: 20px;
            color: #2c3e50;
        }
        
        .table-container {
            overflow-x: auto;
        }
        
        .dept-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        
        .dept-table th,
        .dept-table td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }
        
        .dept-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }
        
        .dept-table tr:hover {
            background: #f8f9fa;
        }
        
        .footer {
            text-align: center;
            padding: 30px;
            color: #7f8c8d;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2em;
            }
            
            .kpi-grid {
                grid-template-columns: 1fr;
            }
            
            .kpi-card {
                padding: 20px;
            }
            
            .kpi-value {
                font-size: 1.8em;
            }
        }
        """
    
    def _upload_file(self, file_path: str, content: str, commit_message: str) -> Tuple[bool, str]:
        """ファイルをGitHubにアップロード"""
        try:
            api_url = f"{self.api_base}/repos/{self.repo_owner}/{self.repo_name}/contents/{file_path}"
            
            headers = {
                'Authorization': f'token {self.token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # 既存ファイルのSHA取得
            response = requests.get(api_url, headers=headers, timeout=10)
            sha = response.json().get('sha') if response.status_code == 200 else None
            
            # Base64エンコード
            content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            
            # アップロードデータ
            data = {
                "message": commit_message,
                "content": content_encoded,
                "branch": self.branch
            }
            
            if sha:
                data["sha"] = sha
            
            # アップロード実行
            response = requests.put(api_url, json=data, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                return True, f"アップロード成功: {file_path}"
            else:
                error_msg = response.json().get('message', 'Unknown error')
                return False, f"アップロード失敗: {error_msg}"
                
        except Exception as e:
            logger.error(f"ファイルアップロードエラー: {e}")
            return False, f"アップロードエラー: {str(e)}"
    
    def _generate_readme(self) -> str:
        """README.md生成"""
        return f"""# 手術ダッシュボード

## 概要
Streamlitで作成された手術分析ダッシュボードです。

## 機能
- 📊 主要指標表示
- 🏥 診療科別分析
- 🏆 ハイスコアランキング（有効時）
- 📱 レスポンシブデザイン

## 更新情報
- 最終更新: {datetime.now().strftime('%Y/%m/%d %H:%M')}
- 自動生成: Streamlit手術ダッシュボード

## アクセス
[ダッシュボードを開く]({self.get_public_url()})
"""
    
    def _generate_github_actions(self) -> str:
        """GitHub Actions設定生成"""
        return """name: Deploy to GitHub Pages

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Pages
        uses: actions/configure-pages@v4
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: './docs'
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""
    
    def get_public_url(self) -> str:
        """公開URLを取得"""
        return f"https://{self.repo_owner}.github.io/{self.repo_name}/"
    
    def _get_error_html(self, error_message: str) -> str:
        """エラー用HTML"""
        return f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <title>エラー - 手術ダッシュボード</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #e74c3c; }}
            </style>
        </head>
        <body>
            <h1 class="error">⚠️ エラーが発生しました</h1>
            <p>{error_message}</p>
            <p>データを確認して再試行してください。</p>
        </body>
        </html>
        """


def create_surgery_github_publisher_interface():
    """手術ダッシュボード専用GitHub公開インターフェース"""
    try:
        st.sidebar.markdown("---")
        st.sidebar.header("🌐 手術レポート公開機能")
        
        # データ状況確認
        df = st.session_state.get('processed_df', pd.DataFrame())
        target_dict = st.session_state.get('target_dict', {})
        
        if df.empty:
            st.sidebar.warning("📊 データを読み込んでください")
            return
        
        # ハイスコア機能状況
        from config.high_score_config import test_high_score_functionality
        high_score_available = test_high_score_functionality()
        
        if high_score_available:
            st.sidebar.success("🏆 ハイスコア機能: 利用可能")
        else:
            st.sidebar.info("📈 ハイスコア機能: 準備中")
        
        # GitHub設定
        st.sidebar.markdown("**🔗 GitHub設定**")
        
        github_token = st.sidebar.text_input(
            "Personal Access Token",
            type="password",
            key="surgery_github_token",
            help="repo権限を持つGitHub Personal Access Token"
        )
        
        col1, col2 = st.sidebar.columns(2)
        with col1:
            repo_owner = st.text_input(
                "Owner",
                value="Genie-Scripts",
                key="surgery_repo_owner"
            )
        with col2:
            repo_name = st.text_input(
                "Repository",
                value="Streamlit-OR-Dashboard",
                key="surgery_repo_name"
            )
        
        branch = st.sidebar.selectbox(
            "ブランチ",
            ["main", "master", "gh-pages"],
            key="surgery_branch"
        )
        
        # 公開設定
        st.sidebar.markdown("**⚙️ 公開設定**")
        
        period = st.sidebar.selectbox(
            "評価期間",
            ["直近4週", "直近8週", "直近12週"],
            index=2,
            key="surgery_publish_period"
        )
        
        include_high_score = st.sidebar.checkbox(
            "ハイスコア機能を含める",
            value=high_score_available,
            disabled=not high_score_available,
            key="surgery_include_high_score"
        )
        
        # 公開実行
        if st.sidebar.button("🚀 公開実行", type="primary", key="surgery_publish_btn"):
            if not github_token:
                st.sidebar.error("GitHub Tokenが必要です")
            elif not repo_owner or not repo_name:
                st.sidebar.error("リポジトリ情報を入力してください")
            else:
                with st.sidebar.spinner("手術ダッシュボードを公開中..."):
                    publisher = SurgeryGitHubPublisher(github_token, repo_owner, repo_name, branch)
                    success, message = publisher.publish_surgery_dashboard(
                        df, target_dict, period, include_high_score
                    )
                    
                    if success:
                        st.sidebar.success("✅ 公開完了！")
                        if include_high_score:
                            st.sidebar.info("🏆 ハイスコア機能も含まれています")
                        
                        public_url = publisher.get_public_url()
                        st.sidebar.markdown(f"🌐 [**公開サイトを開く**]({public_url})")
                    else:
                        st.sidebar.error(f"❌ 公開失敗: {message}")
        
        # 設定状況表示
        st.sidebar.markdown("**📊 現在の設定**")
        st.sidebar.write(f"• データ件数: {len(df):,}件")
        st.sidebar.write(f"• 目標設定: {len(target_dict)}診療科")
        st.sidebar.write(f"• 評価期間: {period}")
        
        if high_score_available:
            st.sidebar.write("• ハイスコア: ✅ 利用可能")
        else:
            st.sidebar.write("• ハイスコア: ⏳ 準備中")
        
        # ヘルプ
        with st.sidebar.expander("❓ 使い方"):
            st.markdown("""
            **📝 事前準備:**
            1. GitHubでリポジトリ作成
            2. Settings > Pages > Source: GitHub Actions
            3. Personal Access Token作成（repo権限）
            
            **🏆 ハイスコア機能:**
            - 診療科別週次評価
            - TOP3ランキング表示
            - 改善度分析
            - モバイル対応
            
            **📱 公開後:**
            - 自動的にGitHub Pagesで公開
            - スマートフォン対応
            - リアルタイム更新
            """)
            
    except Exception as e:
        logger.error(f"手術GitHub公開インターフェースエラー: {e}")
        st.sidebar.error("GitHub公開機能でエラーが発生しました")


# === app.pyへの統合方法 ===
"""
app.pyのサイドバー作成部分に以下を追加:

from reporting.surgery_github_publisher import create_surgery_github_publisher_interface

# 既存のサイドバー作成後に追加
create_surgery_github_publisher_interface()
"""