import os
import json
import requests
import base64
from datetime import datetime, timedelta
import streamlit as st
import pandas as pd
import logging
from config import EXCLUDED_WARDS
import numpy as np
import re
import sys
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ===== 必要なモジュールのインポート（エラーハンドリング付き） =====
REQUIRED_MODULES = {}
try:
    from chart import create_interactive_alos_chart, create_interactive_patient_chart, create_interactive_dual_axis_chart
    REQUIRED_MODULES['charts'] = True
except ImportError:
    REQUIRED_MODULES['charts'] = False
    logger.warning("グラフモジュールが利用できません")

try:
    from html_export_functions import generate_combined_html_with_tabs
    from department_performance_tab import (
        get_period_dates as get_dept_period_dates, 
        calculate_department_kpis, 
        evaluate_feasibility as dept_evaluate_feasibility,
        calculate_effect_simulation as dept_calculate_effect_simulation, 
        decide_action_and_reasoning as dept_decide_action, 
        get_hospital_targets
    )
    from ward_performance_tab import (
        get_period_dates as get_ward_period_dates, 
        calculate_ward_kpis, 
        evaluate_feasibility as ward_evaluate_feasibility,
        calculate_effect_simulation as ward_calculate_effect_simulation, 
        decide_action_and_reasoning as ward_decide_action
    )
    from unified_html_export import generate_unified_html_export
    from utils import get_ward_display_name, safe_date_filter
    REQUIRED_MODULES['performance'] = True
except ImportError as e:
    REQUIRED_MODULES['performance'] = False
    logger.error(f"パフォーマンスモジュールのインポートエラー: {e}")

def _calculate_los_appropriate_range_for_publish(item_df, start_date, end_date):
    """統計的アプローチで在院日数適正範囲を計算（公開機能用）"""
    if item_df.empty: 
        return None
    try:
        period_df = safe_date_filter(item_df, start_date, end_date)
        los_data = []
        for _, row in period_df.iterrows():
            if pd.notna(row.get('退院患者数', 0)) and row.get('退院患者数', 0) > 0:
                patient_days, discharges = row.get('在院患者数', 0), row.get('退院患者数', 0)
                if discharges > 0:
                    daily_los = patient_days / discharges if patient_days > 0 else 0
                    if daily_los > 0: 
                        los_data.extend([daily_los] * int(discharges))
        if len(los_data) < 5: 
            return None
        mean_los, std_los = pd.Series(los_data).mean(), pd.Series(los_data).std()
        range_value = max(std_los, 0.3)
        return {"upper": mean_los + range_value, "lower": max(0.1, mean_los - range_value)}
    except Exception:
        return None

def _render_los_trend_card_for_publish(label, period_avg, recent, unit, item_df, start_date, end_date):
    """在院日数トレンド分析カードのHTML生成（公開機能用）"""
    try:
        change_rate = ((recent - period_avg) / period_avg) * 100 if period_avg > 0 else 0
        change_days = recent - period_avg
        
        if abs(change_rate) < 3:
            trend_icon, trend_text, trend_color = "🟡", "安定", "#FFC107"
        elif change_rate > 0:
            trend_icon, trend_text, trend_color = "🔴", "延長傾向", "#F44336"
        else:
            trend_icon, trend_text, trend_color = "🟢", "短縮傾向", "#4CAF50"
        
        los_range = _calculate_los_appropriate_range_for_publish(item_df, start_date, end_date)
        range_status, range_color = "", "#999"
        if los_range and recent > 0:
            if los_range["lower"] <= recent <= los_range["upper"]:
                range_status, range_color = "✅ 適正範囲内", "#4CAF50"
            else:
                range_status, range_color = "⚠️ 要確認", "#FF9800"
        
        range_display = f'<div style="margin-top:4px; font-size:0.8em; color:#666;">適正範囲: {los_range["lower"]:.1f}-{los_range["upper"]:.1f}日</div>' if los_range else ""
        
        return f"""
            <div class="metric-card" style="border-left-color: {trend_color};">
                <h5>{label}</h5>
                <div class="metric-line">期間平均: <strong>{period_avg:.1f} {unit}</strong></div>
                <div class="metric-line">直近週実績: <strong>{recent:.1f} {unit}</strong></div>
                <div class="metric-line">変化: <strong>{change_days:+.1f} {unit} ({change_rate:+.1f}%)</strong></div>
                <div class="achievement" style="color: {trend_color};">{trend_icon} {trend_text}</div>
                <div style="text-align: right; font-size: 0.9em; color:{range_color};">{range_status}</div>
                {range_display}
            </div>
            """
    except Exception:
        return ""

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
            response = requests.get("https://api.github.com/user", headers=headers)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"トークン検証エラー: {e}")
            return False
        
    def upload_html_file(self, html_content, file_path, commit_message=None):
        """HTMLファイルをGitHubにアップロード"""
        try:
            # トークン検証
            if not self.validate_token():
                return False, "GitHubトークンが無効です"
                
            file_url = f"{self.base_url}/contents/{file_path}"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            # 既存ファイルのSHA取得
            response = requests.get(file_url, headers=headers)
            sha = response.json().get("sha") if response.status_code == 200 else None
            
            # コンテンツのBase64エンコード
            content_encoded = base64.b64encode(html_content.encode('utf-8')).decode('utf-8')
            
            # コミットメッセージ
            if not commit_message:
                commit_message = f"Update dashboard: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # アップロードデータ
            data = {
                "message": commit_message,
                "content": content_encoded,
                "branch": self.branch
            }
            if sha:
                data["sha"] = sha
            
            # アップロード実行
            response = requests.put(file_url, json=data, headers=headers)
            
            if response.status_code in [200, 201]:
                return True, f"Successfully uploaded: {file_path}"
            else:
                error_msg = response.json().get('message', 'Unknown error')
                return False, f"Upload failed: {error_msg}"
                
        except Exception as e:
            logger.error(f"アップロードエラー: {e}", exc_info=True)
            return False, f"Error uploading file: {str(e)}"
    
    def upload_external_html(self, html_content, filename, dashboard_title, commit_message=None):
        """外部HTMLファイルにFABホームボタンとレスポンシブCSSを自動追加してアップロード"""
        try:
            # レスポンシブCSS注入
            responsive_css = self._get_responsive_css()
            
            # FABホームボタン注入
            fab_button = self._get_fab_button_html()
            
            # HTML修正
            if '</head>' in html_content:
                html_content = html_content.replace('</head>', f'{responsive_css}</head>')
            
            if '</body>' in html_content:
                html_content = html_content.replace('</body>', f'{fab_button}</body>')
            
            # ファイル名の正規化
            safe_filename = self._normalize_filename(filename)
            file_path = f"docs/{safe_filename}"
            
            if not commit_message:
                commit_message = f"Update external dashboard: {dashboard_title}"
            
            return self.upload_html_file(html_content, file_path, commit_message)
            
        except Exception as e:
            logger.error(f"外部HTMLアップロードエラー: {e}", exc_info=True)
            return False, f"外部HTMLアップロードエラー: {str(e)}"
    
    def create_index_page(self, dashboards_info, content_config=None, external_dashboards=None):
        """モバイルファーストなインデックスページを生成"""
        if content_config is None:
            content_config = ContentCustomizer().default_content
        
        # ダッシュボード情報の統合
        all_dashboards = self._merge_dashboard_info(dashboards_info, external_dashboards)
        
        # モバイルファーストレイアウトで生成
        return self._create_mobile_first_layout(all_dashboards, content_config)
    
    def get_public_url(self):
        """公開URLを取得"""
        return f"https://{self.repo_owner}.github.io/{self.repo_name}/"
    
    # === プライベートメソッド ===
    
    def _get_responsive_css(self):
        """レスポンシブCSS（スマホ3列表示対応）"""
        return """
        <style>
            /* レスポンシブCSS - スマホ3列表示対応 */
            @media (max-width: 600px) {
                .grid-container {
                    grid-template-columns: repeat(3, 1fr) !important;
                    gap: 10px !important;
                }
                .metric-card {
                    padding: 10px !important;
                    font-size: 0.85em !important;
                }
                .metric-card h5 {
                    font-size: 0.9em !important;
                    margin-bottom: 8px !important;
                }
                .metric-card > div {
                    font-size: 0.8em !important;
                }
                .metric-card > div:last-child > div {
                    height: 4px !important;
                }
            }
            @media (max-width: 900px) {
                .grid-container {
                    grid-template-columns: repeat(3, 1fr) !important;
                    gap: 15px !important;
                }
            }
        </style>
        """
    
    def _get_fab_button_html(self):
        """FABホームボタンのHTML"""
        return """
        <style>
            .injected-fab-home {
                position: fixed;
                bottom: 30px;
                right: 30px;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                text-decoration: none;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                transition: all 0.3s ease;
                z-index: 9999;
                cursor: pointer;
            }
            .injected-fab-home:hover {
                transform: scale(1.1) translateY(-3px);
                box-shadow: 0 6px 20px rgba(0,0,0,0.4);
                background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            }
            @media (max-width: 768px) {
                .injected-fab-home {
                    bottom: 20px;
                    right: 20px;
                    width: 50px;
                    height: 50px;
                }
            }
            @media print {
                .injected-fab-home { display: none; }
            }
        </style>
        <a href="./index.html" class="injected-fab-home" aria-label="ホームに戻る">
            <span style="font-size: 1.8em;">🏠</span>
        </a>
        """
    
    def _normalize_filename(self, filename):
        """ファイル名の正規化"""
        safe_filename = filename.lower().replace(' ', '_').replace('　', '_')
        safe_filename = re.sub(r'[^a-z0-9_.-]', '_', safe_filename)
        if not safe_filename.endswith('.html'):
            safe_filename += '.html'
        return safe_filename
    
    def _merge_dashboard_info(self, dashboards_info, external_dashboards):
        """ダッシュボード情報の統合"""
        all_dashboards = dashboards_info.copy() if dashboards_info else []
        
        if external_dashboards:
            for ext_dash in external_dashboards:
                # パスの正規化
                if 'file' in ext_dash and ext_dash['file'].startswith('docs/'):
                    ext_dash['file'] = ext_dash['file'].replace('docs/', '')
            all_dashboards.extend(external_dashboards)
            
        return all_dashboards
    
    def _create_mobile_first_layout(self, dashboards_info, content_config):
        """モバイルファーストなレイアウト（統一版）"""
        dashboard_list = ""
        
        for dashboard in dashboards_info:
            # 説明文の選択
            description = self._get_dashboard_description(dashboard, content_config)
            update_time = dashboard.get('update_time', '不明')
            
            # アイコンの設定
            icon = "🔗" if dashboard.get('type') == 'external' else "📊"
            
            # 相対パスの処理
            file_path = dashboard['file']
            if file_path.startswith('docs/'):
                file_path = file_path.replace('docs/', '')
            
            dashboard_list += f"""
            <a href="{file_path}" class="dashboard-item">
                <div class="item-icon">{icon}</div>
                <div class="item-content">
                    <h3>{dashboard['title']}</h3>
                    <p>{description}</p>
                    <span class="update-badge">最新: {update_time}</span>
                </div>
                <div class="item-arrow">›</div>
            </a>
            """
        
        footer_note = content_config.get('footer_note', '')
        footer_note_html = f"<p>{footer_note}</p>" if footer_note else ""
        
        return f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{content_config.get('main_title', 'ダッシュボード')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans JP', sans-serif;
            background: #f2f2f7;
            color: #1c1c1e;
        }}
        .header {{
            background: linear-gradient(180deg, #007AFF 0%, #5856D6 100%);
            color: white;
            padding: 60px 20px 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.2em;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .dashboard-list {{
            padding: 20px 16px;
            max-width: 800px;
            margin: 0 auto;
        }}
        .dashboard-item {{
            background: white;
            border-radius: 12px;
            margin-bottom: 12px;
            padding: 20px;
            display: flex;
            align-items: center;
            text-decoration: none;
            color: inherit;
            box-shadow: 0 2px 10px rgba(0,0,0,0.06);
            transition: all 0.2s ease;
        }}
        .dashboard-item:active {{
            transform: scale(0.98);
            background: #f2f2f7;
        }}
        .item-icon {{
            font-size: 2em;
            margin-right: 16px;
            width: 50px;
            text-align: center;
        }}
        .item-content {{
            flex: 1;
        }}
        .item-content h3 {{
            font-size: 1.2em;
            font-weight: 600;
            margin-bottom: 4px;
            color: #1c1c1e;
        }}
        .item-content p {{
            color: #8e8e93;
            font-size: 0.9em;
            line-height: 1.4;
            margin-bottom: 6px;
        }}
        .update-badge {{
            display: inline-block;
            background: #007AFF;
            color: white;
            font-size: 0.75em;
            padding: 3px 8px;
            border-radius: 10px;
            font-weight: 500;
        }}
        .item-arrow {{
            font-size: 1.8em;
            color: #c7c7cc;
            margin-left: 10px;
        }}
        .footer-note {{
            text-align: center;
            padding: 40px 20px;
            color: #8e8e93;
            font-size: 0.9em;
        }}
        @media (min-width: 768px) {{
            .header {{ padding: 80px 40px 60px; }}
            .dashboard-list {{ max-width: 600px; }}
            .dashboard-item:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{content_config.get('main_title', 'ダッシュボード')}</h1>
        <p>{content_config.get('subtitle', '')}</p>
    </div>
    
    <div class="dashboard-list">
        {dashboard_list}
    </div>
    
    <div class="footer-note">
        <p>{content_config.get('footer_text', 'システム')}</p>
        {footer_note_html}
        <p>最終更新: {datetime.now().strftime('%Y年%m月%d日 %H時%M分')}</p>
    </div>
</body>
</html>"""
    
    def _get_dashboard_description(self, dashboard, content_config):
        """ダッシュボードの説明文を取得"""
        if 'department' in dashboard.get('file', '').lower() or '診療科' in dashboard.get('title', ''):
            return content_config.get('department_dashboard_description', dashboard.get('description', ''))
        elif 'ward' in dashboard.get('file', '').lower() or '病棟' in dashboard.get('title', ''):
            return content_config.get('ward_dashboard_description', dashboard.get('description', ''))
        elif dashboard.get('type') == 'external':
            return dashboard.get('description', '外部システムから提供されるダッシュボード')
        else:
            return dashboard.get('description', '')

    @staticmethod
    def save_settings(repo_owner, repo_name):
        """GitHub設定を保存（トークンは保存しない）"""
        try:
            from data_persistence import save_settings_to_file
            settings = {
                'github_repo_owner': repo_owner,
                'github_repo_name': repo_name,
                'github_settings_saved': True
            }
            # prefix パラメータを削除
            return save_settings_to_file(settings)
        except Exception as e:
            logger.error(f"GitHub設定保存エラー: {e}")
            return False
    
    @staticmethod
    def load_settings():
        """保存されたGitHub設定を読み込み"""
        try:
            from data_persistence import load_settings_from_file
            saved_settings = load_settings_from_file()
            if saved_settings and saved_settings.get('github_settings_saved'):
                return {
                    'repo_owner': saved_settings.get('github_repo_owner', 'Genie-Scripts'),
                    'repo_name': saved_settings.get('github_repo_name', 'Streamlit-Dashboard')
                }
            return None
        except Exception as e:
            logger.error(f"GitHub設定読み込みエラー: {e}")
            return None

class ContentCustomizer:
    """コンテンツカスタマイザー（簡素化版）"""
    
    def __init__(self):
        self.default_content = {
            "main_title": "🏥 週報ダッシュボード",
            "subtitle": "入院/手術分析・スマートフォン横向き表示対応",
            "department_dashboard_description": "各診療科の入院患者数、新入院患者数、平均在院日数の実績と目標達成率",
            "ward_dashboard_description": "各病棟の入院患者数、新入院患者数、平均在院日数の実績と目標達成率",
            "footer_text": "🏥 経営企画室",
            "footer_note": "",
            "dashboard_button_text": "ダッシュボードを開く"
        }
    
    def create_streamlit_interface(self):
        """Streamlit用のUI作成"""
        st.sidebar.markdown("### 📝 トップページ内容編集")
        
        # 編集フィールド
        fields = [
            ("メインタイトル", "content_main_title", "main_title"),
            ("サブタイトル", "content_subtitle", "subtitle"),
            ("診療科別説明", "content_dept_description", "department_dashboard_description", "text_area"),
            ("病棟別説明", "content_ward_description", "ward_dashboard_description", "text_area"),
            ("フッターメイン", "content_footer_text", "footer_text"),
            ("フッター追加メモ", "content_footer_note", "footer_note", "text_area"),
        ]
        
        for field in fields:
            label, key, config_key = field[:3]
            input_type = field[3] if len(field) > 3 else "text_input"
            
            if input_type == "text_area":
                st.sidebar.text_area(
                    label,
                    value=st.session_state.get(key, self.default_content[config_key]),
                    key=key
                )
            else:
                st.sidebar.text_input(
                    label,
                    value=st.session_state.get(key, self.default_content[config_key]),
                    key=key
                )
        
        if st.sidebar.button("💾 内容設定を保存", key="save_content_settings"):
            self._save_current_content()
            st.sidebar.success("✅ 内容設定を保存しました")
    
    def _save_current_content(self):
        """現在の設定を保存"""
        st.session_state.custom_content_config = {
            "main_title": st.session_state.get('content_main_title', ''),
            "subtitle": st.session_state.get('content_subtitle', ''),
            "department_dashboard_description": st.session_state.get('content_dept_description', ''),
            "ward_dashboard_description": st.session_state.get('content_ward_description', ''),
            "footer_text": st.session_state.get('content_footer_text', ''),
            "footer_note": st.session_state.get('content_footer_note', ''),
            "dashboard_button_text": self.default_content["dashboard_button_text"]
        }
    
    def get_current_config(self):
        """現在の設定を取得"""
        return st.session_state.get('custom_content_config', self.default_content)

def create_external_dashboard_uploader():
    """外部ダッシュボードアップロード機能（簡素化版）"""
    st.sidebar.markdown("---")
    st.sidebar.header("🔗 外部ダッシュボード追加")
    
    with st.sidebar.expander("📤 HTMLアップロード", expanded=False):
        uploaded_file = st.file_uploader(
            "HTMLファイルを選択",
            type=['html'],
            key="external_html_file"
        )
        
        if uploaded_file:
            col1, col2 = st.columns(2)
            
            with col1:
                dashboard_title = st.text_input(
                    "タイトル",
                    value="全身麻酔手術分析",
                    key="external_dashboard_title"
                )
            
            with col2:
                filename = st.text_input(
                    "ファイル名",
                    value='surgery_analysis.html',
                    key="external_filename"
                )
            
            dashboard_description = st.text_area(
                "説明文",
                value="全身麻酔手術件数の分析結果",
                key="external_dashboard_description",
                height=60
            )
            
            if st.button("🚀 追加", key="upload_external_dashboard", use_container_width=True):
                if st.session_state.get('github_publisher'):
                    try:
                        html_content = uploaded_file.read().decode('utf-8')
                        publisher = st.session_state.github_publisher
                        
                        success, message = publisher.upload_external_html(
                            html_content,
                            filename,
                            dashboard_title
                        )
                        
                        if success:
                            # 外部ダッシュボード情報を更新
                            _update_external_dashboards(
                                dashboard_title,
                                dashboard_description,
                                filename
                            )
                            st.success(f"✅ 追加成功")
                            st.rerun()
                        else:
                            st.error(f"❌ 追加失敗: {message}")
                    except Exception as e:
                        st.error(f"❌ エラー: {str(e)}")
                        logger.error(f"外部ダッシュボード追加エラー: {e}", exc_info=True)
                else:
                    st.error("❌ GitHub設定が必要です")

def test_github_connection(github_token: str, repo_name: str):
    """GitHub接続テスト"""
    try:
        with st.spinner("🔍 GitHub接続を確認中..."):
            
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # リポジトリアクセステスト
            repo_url = f"https://api.github.com/repos/{repo_name}"
            response = requests.get(repo_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                repo_info = response.json()
                st.sidebar.success("✅ GitHub接続成功!")
                
                # 基本情報表示
                st.sidebar.info(f"""
                **リポジトリ情報:**
                - 名前: {repo_info.get('full_name')}
                - 公開: {'Public' if not repo_info.get('private') else 'Private'}
                - ブランチ: {repo_info.get('default_branch')}
                """)
                
                # GitHub Pages状況確認
                pages_url = f"https://api.github.com/repos/{repo_name}/pages"
                pages_response = requests.get(pages_url, headers=headers, timeout=10)
                
                if pages_response.status_code == 200:
                    pages_info = pages_response.json()
                    st.sidebar.success(f"📄 GitHub Pages: 有効")
                    st.sidebar.code(pages_info.get('html_url', ''))
                else:
                    st.sidebar.warning("📄 GitHub Pages: 未設定（公開時に自動設定）")
                    
            elif response.status_code == 404:
                st.sidebar.error("❌ リポジトリが見つかりません")
                st.sidebar.info("リポジトリ名を確認するか、新しいリポジトリを作成してください")
            elif response.status_code == 401:
                st.sidebar.error("❌ 認証エラー")
                st.sidebar.info("Personal Access Tokenを確認してください")
            else:
                st.sidebar.error(f"❌ 接続エラー (HTTP {response.status_code})")
                
    except Exception as e:
        logger.error(f"GitHub接続テストエラー: {e}")
        st.sidebar.error(f"接続テスト中にエラー: {str(e)}")

def check_publish_readiness() -> Tuple[bool, str]:
    """GitHub公開の準備状況確認"""
    try:
        # 基本データの確認
        if not st.session_state.get('data_processed', False):
            return False, "データ未読み込み（データ入力タブからデータを読み込んでください）"
        
        df = st.session_state.get('df')
        if df is None or df.empty:
            return False, "有効なデータが見つかりません"
        
        # 必要な列の確認
        required_columns = ['日付', '在院患者数', '新入院患者数']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"必要なデータ列が不足しています: {', '.join(missing_columns)}"
        
        # 詳細分析モジュールの確認
        try:
            from department_performance_tab import calculate_department_kpis
            from unified_html_export import generate_unified_html_export
        except ImportError as e:
            return False, f"必要なモジュールが見つかりません: {str(e)}"
        
        return True, "公開可能な状態です"
        
    except Exception as e:
        logger.error(f"公開準備確認エラー: {e}")
        return False, f"確認中にエラーが発生: {str(e)}"

def execute_github_publish(content_type: str, period: str, github_token: str, 
                          repo_name: str, branch: str, auto_refresh: bool, 
                          include_debug: bool, mobile_optimized: bool):
    """
    GitHub公開の実行（ロジック修正・統合レポート対応版）
    """
    try:
        owner, repo = repo_name.split('/')
        publisher = GitHubPublisher(repo_owner=owner, repo_name=repo, token=github_token, branch=branch)
        df = st.session_state.get('df')
        target_data = st.session_state.get('target_data', pd.DataFrame())

        with st.spinner(f"🚀「{content_type}」を生成・公開中..."):
            
            # --- ケース1: 統合レポート（全機能） ---
            if "統合レポート" in content_type:
                st.info("統合レポートを生成中...（最大1〜2分かかります）")
                dashboards_info = []
                error_messages = []

                # 1a. 診療科別ダッシュボード
                with st.spinner("1/4: 診療科別ダッシュボードを生成中..."):
                    html_dept = generate_performance_dashboard_html(df, target_data, period, "department")
                    if html_dept:
                        success, _ = publisher.upload_html_file(html_dept, "docs/department_dashboard.html")
                        if success:
                            dashboards_info.append({"title": "診療科別パフォーマンス", "file": "department_dashboard.html", "update_time": datetime.now().strftime('%Y/%m/%d')})
                        else:
                            error_messages.append("診療科別ページのアップロードに失敗")
                
                # 1b. 病棟別ダッシュボード
                with st.spinner("2/4: 病棟別ダッシュボードを生成中..."):
                    html_ward = generate_performance_dashboard_html(df, target_data, period, "ward")
                    if html_ward:
                        success, msg = publisher.upload_html_file(html_ward, "docs/ward_dashboard.html")
                        if success:
                            dashboards_info.append({
                                "title": "病棟別パフォーマンス", 
                                "file": "ward_dashboard.html",  # docs/を含めない
                                "update_time": datetime.now().strftime('%Y/%m/%d')
                            })
                        else:
                            error_messages.append(f"病棟別ページのアップロードに失敗: {msg}")
                    else:
                        error_messages.append("病棟別HTMLの生成に失敗")
            
                # 1c. 90日間総合レポート
                with st.spinner("3/4: 90日間総合レポートを生成中..."):
                    html_90d = generate_90day_report_html(df, target_data)
                    if html_90d:
                        success, _ = publisher.upload_html_file(html_90d, "docs/comprehensive_report_90days.html")
                        if success:
                             # 外部ダッシュボードとして追加
                            _update_external_dashboards("90日間総合レポート", "全体・診療科・病棟別の詳細グラフ", "comprehensive_report_90days.html")
                        else:
                             error_messages.append("90日間レポートのアップロードに失敗")
                
                # 1d. トップページ (index.html)
                with st.spinner("4/4: トップページ(index.html)を生成中..."):
                    external_dashboards = st.session_state.get('external_dashboards', [])
                    index_html = publisher.create_index_page(dashboards_info, None, external_dashboards)
                    success, url = publisher.upload_html_file(index_html, "docs/index.html")

                if success:
                    st.sidebar.success("✅ 統合レポートの公開完了！")
                    st.sidebar.markdown(f"🌐 [**トップページを開く**]({url})", unsafe_allow_html=True)
                    save_publish_history(content_type, period, url)
                else:
                    st.sidebar.error("❌ トップページの公開に失敗しました。")

                if error_messages:
                    for msg in error_messages:
                        st.sidebar.warning(f"⚠️ {msg}")

                return # 統合レポートの場合はここで終了

            # --- ケース2: 個別ページの生成 ---
            publish_data = generate_publish_data(content_type, period)
            if not publish_data:
                st.sidebar.error("❌ 公開データの生成に失敗しました")
                return

            html_content = generate_publish_html(publish_data, content_type, include_debug, mobile_optimized)
            if not html_content:
                st.sidebar.error("❌ HTMLコンテンツの生成に失敗しました")
                return

            publish_success, publish_url = publish_to_github(html_content, github_token, repo_name, branch, content_type, publish_data.get('dashboard_type', 'department'))
            
            if publish_success:
                st.sidebar.success(f"✅ 「{content_type}」の公開完了!")
                if publish_url:
                    st.sidebar.markdown(f"🌐 [**公開ページを開く**]({publish_url})", unsafe_allow_html=True)
                save_publish_history(content_type, period, publish_url)
            else:
                st.sidebar.error("❌ GitHub公開に失敗しました")

    except Exception as e:
        logger.error(f"GitHub公開実行エラー: {e}", exc_info=True)
        st.sidebar.error(f"❌ 公開中にエラーが発生しました: {str(e)}")

def generate_publish_data(content_type: str, period: str) -> Optional[Dict]:
    """公開用データの生成（詳細アクション提案対応版）"""
    try:
        # 必要なモジュールのインポート
        from department_performance_tab import (
            get_period_dates, safe_date_filter, calculate_department_kpis,
            evaluate_feasibility, calculate_effect_simulation, 
            decide_action_and_reasoning, get_hospital_targets
        )
        from ward_performance_tab import (
            get_period_dates as get_ward_period_dates,
            calculate_ward_kpis, evaluate_feasibility as ward_evaluate_feasibility,
            calculate_effect_simulation as ward_calculate_effect_simulation,
            decide_action_and_reasoning as ward_decide_action_and_reasoning
        )
        from config import EXCLUDED_WARDS
        
        df_original = st.session_state.get('df')
        target_data = st.session_state.get('target_data')
        
        # コンテンツタイプの判定と処理
        if "診療科別" in content_type:
            dashboard_type = "department"
            get_dates_func = get_period_dates
            calculate_kpi_func = calculate_department_kpis
            evaluate_func = evaluate_feasibility
            simulation_func = calculate_effect_simulation
            action_func = decide_action_and_reasoning
            possible_cols = ['部門名', '診療科', '診療科名']
            item_key = 'dept'
        elif "病棟別" in content_type:
            dashboard_type = "ward"
            get_dates_func = get_ward_period_dates
            calculate_kpi_func = calculate_ward_kpis
            evaluate_func = ward_evaluate_feasibility
            simulation_func = ward_calculate_effect_simulation
            action_func = ward_decide_action_and_reasoning
            possible_cols = ['病棟名', '病棟コード']
            item_key = 'ward'
        else:
            # デフォルトは診療科別
            dashboard_type = "department"
            get_dates_func = get_period_dates
            calculate_kpi_func = calculate_department_kpis
            evaluate_func = evaluate_feasibility
            simulation_func = calculate_effect_simulation
            action_func = decide_action_and_reasoning
            possible_cols = ['部門名', '診療科', '診療科名']
            item_key = 'dept'
        
        # 期間設定
        start_date, end_date, period_desc = get_dates_func(df_original, period)
        if not start_date or not end_date:
            return None
        
        # データフィルタリング
        filtered_df = safe_date_filter(df_original, start_date, end_date)
        if '病棟コード' in filtered_df.columns and EXCLUDED_WARDS:
            filtered_df = filtered_df[~filtered_df['病棟コード'].isin(EXCLUDED_WARDS)]
        
        if filtered_df.empty:
            return None
        
        # 該当列の検索
        item_col = next((c for c in possible_cols if c in filtered_df.columns), None)
        if not item_col:
            return None
        
        # 病院全体目標
        hospital_targets = get_hospital_targets(target_data)
        
        # 詳細分析結果の生成
        analysis_results = []
        unique_items = filtered_df[item_col].unique()
        
        for item_code in unique_items:
            # 病棟の場合の除外処理
            if dashboard_type == "ward" and item_code in EXCLUDED_WARDS:
                continue
            
            # KPI計算
            kpi = calculate_kpi_func(
                filtered_df, target_data, item_code, item_code,
                start_date, end_date, item_col
            )
            
            if kpi:
                # 詳細分析
                item_df = filtered_df[filtered_df[item_col] == item_code]
                feasibility = evaluate_func(kpi, item_df, start_date, end_date)
                simulation = simulation_func(kpi)
                action_result = action_func(kpi, feasibility, simulation)
                
                analysis_results.append({
                    'kpi': kpi,
                    'action_result': action_result,
                    'feasibility': feasibility,
                    'simulation': simulation
                })
        
        # データ生成内容の判定
        if "詳細アクション提案" in content_type:
            # 詳細アクション提案の場合
            data_content_type = "detailed_action"
        elif "KPI指標" in content_type:
            # KPI指標ダッシュボードの場合
            data_content_type = "kpi_dashboard"
        else:
            # デフォルト
            data_content_type = "standard"
        
        return {
            'content_type': content_type,
            'data_content_type': data_content_type,
            'dashboard_type': dashboard_type,
            'period_desc': period_desc,
            'analysis_results': analysis_results,
            'hospital_targets': hospital_targets,
            'data_summary': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_records': len(filtered_df),
                'analysis_items': len(unique_items),
                'generated_at': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"公開データ生成エラー: {e}", exc_info=True)
        return None

def generate_publish_html(publish_data: Dict, content_type: str, 
                         include_debug: bool, mobile_optimized: bool) -> Optional[str]:
    """
    公開用HTMLの生成（ロジックを整理し「詳細版」に統一）
    """
    try:
        # 必要なデータがpublish_dataに含まれているか確認
        required_keys = ['analysis_results', 'period_desc', 'hospital_targets', 'dashboard_type']
        if not all(key in publish_data for key in required_keys):
            logger.error("HTML生成に必要なデータが不足しています。")
            return None

        # 詳細版HTML生成関数を呼び出す
        html_content = generate_unified_html_export(
            publish_data['analysis_results'],
            publish_data['period_desc'],
            publish_data['hospital_targets'],
            publish_data['dashboard_type']
        )
        
        if not html_content:
            logger.error("詳細版HTMLの生成に失敗しました。")
            return None
        
        # Web公開用の追加機能を注入
        web_optimized_html = add_web_publish_features(
            html_content, publish_data, include_debug, mobile_optimized
        )
        
        return web_optimized_html
        
    except Exception as e:
        logger.error(f"公開用HTML生成エラー: {e}", exc_info=True)
        return None

def add_web_publish_features(html_content: str, publish_data: Dict, 
                           include_debug: bool, mobile_optimized: bool) -> str:
    """Web公開用機能の追加（操作パネル削除版）"""
    try:
        # PWA対応メタタグ
        pwa_meta = f"""
        <!-- Progressive Web App対応 -->
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="theme-color" content="#7fb069">
        <meta name="description" content="病院経営 {publish_data['content_type']}">
        <link rel="apple-touch-icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🏥</text></svg>">
        
        <!-- Open Graph -->
        <meta property="og:title" content="{publish_data['content_type']}">
        <meta property="og:description" content="データに基づく科学的な改善提案 - {publish_data['period_desc']}">
        <meta property="og:type" content="website">
        """
        
        # モバイル最適化CSS（操作パネル関連のスタイルを削除）
        mobile_css = ""
        if mobile_optimized:
            mobile_css = """
            
            /* モバイル最適化CSS */
            @media (max-width: 768px) {
                .actions-grid {
                    grid-template-columns: 1fr !important;
                    gap: 15px !important;
                }
                
                .action-card {
                    padding: 15px !important;
                    margin-bottom: 10px !important;
                }
                
                .card-header h3 {
                    font-size: 1.1em !important;
                }
                
                .hospital-summary {
                    grid-template-columns: 1fr !important;
                }
            }
            
            /* ダークモード対応 */
            @media (prefers-color-scheme: dark) {
                body {
                    background: #1a1a1a !important;
                    color: #e0e0e0 !important;
                }
                
                .action-card {
                    background: #2d2d2d !important;
                    color: #e0e0e0 !important;
                }
            }
            """
        
        # デバッグ情報（必要な場合のみ）
        debug_panel = ""
        if include_debug:
            debug_panel = f"""
            
            <!-- デバッグ情報パネル -->
            <div id="debug-panel" style="
                position: fixed; bottom: 20px; left: 20px;
                background: rgba(248,249,250,0.95); padding: 12px; 
                border-radius: 8px; border: 1px solid #dee2e6;
                font-family: monospace; font-size: 0.8em; max-width: 320px;
                z-index: 1000; backdrop-filter: blur(5px);
            ">
                <div style="font-weight: bold; margin-bottom: 8px;">🔧 システム情報</div>
                <div>生成時刻: {publish_data['data_summary']['generated_at'][:19]}</div>
                <div>分析期間: {publish_data['data_summary']['start_date'][:10]} ～ {publish_data['data_summary']['end_date'][:10]}</div>
                <div>総レコード: {publish_data['data_summary']['total_records']:,}件</div>
                <div>分析対象: {publish_data['data_summary']['analysis_items']}部門</div>
                <div>ダッシュボード: {publish_data['dashboard_type']}</div>
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #dee2e6;">
                    <small>最適化: {'モバイル対応' if mobile_optimized else '標準'}</small>
                </div>
            </div>
            """
        
        # HTMLに機能を注入（操作パネルは除外）
        enhanced_html = html_content.replace('<head>', f'<head>{pwa_meta}')
        
        # モバイルCSSとデバッグパネルのみ追加
        if mobile_css or debug_panel:
            additional_content = f'<style>{mobile_css}</style>{debug_panel}'
            enhanced_html = enhanced_html.replace('</body>', f'{additional_content}</body>')
        
        return enhanced_html
        
    except Exception as e:
        logger.error(f"Web公開機能追加エラー: {e}")
        return html_content

def publish_to_github(html_content: str, github_token: str, 
                     repo_name: str, branch: str, content_type: str = None, 
                     dashboard_type: str = None) -> Tuple[bool, Optional[str]]:
    """GitHub APIを使用したファイル公開（ファイル名自動決定版）"""
    try:
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Hospital-Dashboard-Publisher'
        }
        
        # リポジトリ存在確認
        repo_url = f"https://api.github.com/repos/{repo_name}"
        response = requests.get(repo_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"リポジトリアクセスエラー: {response.status_code}")
            return False, None
        
        # ファイル名の決定
        if content_type and "詳細アクション提案" in content_type:
            if dashboard_type == "ward":
                filename = "docs/detailed_action_ward.html"
            else:
                filename = "docs/detailed_action_department.html"
        elif content_type and "トップページ" in content_type:
            filename = "docs/index.html"
        else:
            # デフォルト
            filename = "docs/index.html"
        
        # ファイルアップロード
        success = upload_file_to_github_api(
            html_content, github_token, repo_name, branch, filename
        )
        
        if success:
            # GitHub Pagesの設定確認・有効化
            pages_url = enable_github_pages(github_token, repo_name, branch)
            
            # ファイル別のURLを返す
            if "detailed_action" in filename and pages_url:
                # docs/を除いたファイル名でURLを構築
                file_name_only = filename.replace("docs/", "")
                file_url = pages_url.rstrip('/') + f"/{file_name_only}"
                return True, file_url
            else:
                return True, pages_url
        
        return False, None
        
    except Exception as e:
        logger.error(f"GitHub公開エラー: {e}", exc_info=True)
        return False, None

def upload_file_to_github_api(content: str, token: str, repo_name: str, 
                             branch: str, filename: str) -> bool:
    """GitHub APIでのファイルアップロード"""
    try:
        # Base64エンコード
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        # API URL
        api_url = f"https://api.github.com/repos/{repo_name}/contents/{filename}"
        
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # 既存ファイルのSHA確認
        response = requests.get(api_url, headers=headers, timeout=30)
        sha = None
        if response.status_code == 200:
            sha = response.json().get('sha')
        
        # ファイル作成/更新
        data = {
            'message': f'Update dashboard - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'content': content_b64,
            'branch': branch
        }
        
        if sha:
            data['sha'] = sha
        
        response = requests.put(api_url, headers=headers, json=data, timeout=60)
        return response.status_code in [200, 201]
        
    except Exception as e:
        logger.error(f"GitHub APIアップロードエラー: {e}")
        return False

def enable_github_pages(github_token: str, repo_name: str, branch: str) -> Optional[str]:
    """GitHub Pagesの有効化"""
    try:
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # GitHub Pages設定API
        pages_url = f"https://api.github.com/repos/{repo_name}/pages"
        
        # 現在の設定確認
        response = requests.get(pages_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            # 既に有効
            pages_info = response.json()
            return pages_info.get('html_url')
        
        elif response.status_code == 404:
            # Pages未設定なので有効化
            pages_data = {
                'source': {
                    'branch': branch,
                    'path': '/'
                }
            }
            
            response = requests.post(
                pages_url, headers=headers, json=pages_data, timeout=30
            )
            
            if response.status_code == 201:
                pages_info = response.json()
                return pages_info.get('html_url')
        
        # フォールバック: 標準的なGitHub PagesのURL生成
        username = repo_name.split('/')[0]
        repository = repo_name.split('/')[1]
        return f"https://{username}.github.io/{repository}/"
        
    except Exception as e:
        logger.error(f"GitHub Pages有効化エラー: {e}")
        username = repo_name.split('/')[0]
        repository = repo_name.split('/')[1] 
        return f"https://{username}.github.io/{repository}/"

def setup_auto_update(github_token: str, repo_name: str, branch: str):
    """自動更新機能の設定"""
    try:
        # GitHub Actionsワークフローファイルの作成
        workflow_content = generate_auto_update_workflow()
        
        upload_file_to_github_api(
            workflow_content, github_token, repo_name, branch,
            ".github/workflows/auto-update.yml"
        )
        
        logger.info("自動更新ワークフローを設定しました")
        
    except Exception as e:
        logger.error(f"自動更新設定エラー: {e}")

def generate_auto_update_workflow() -> str:
    """自動更新用GitHub Actionsワークフロー生成"""
    return """
name: Auto Update Dashboard

on:
  schedule:
    # 毎日午前8時（JST）に実行 (UTC 23:00)
    - cron: '0 23 * * *'
  workflow_dispatch:  # 手動実行も可能

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v2
      
      - name: Update timestamp
        run: |
          echo "<!-- Auto-updated: $(date) -->" >> index.html
      
      - name: Commit changes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add .
          git commit -m "Auto-update dashboard $(date)" || exit 0
          git push
"""

def save_publish_history(content_type: str, period: str, url: Optional[str]):
    """公開履歴の保存"""
    try:
        if 'github_publish_history' not in st.session_state:
            st.session_state['github_publish_history'] = []
        
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'content_type': content_type,
            'period': period,
            'url': url,
            'status': 'success' if url else 'failed'
        }
        
        st.session_state['github_publish_history'].append(history_entry)
        
        # 最新10件のみ保持
        if len(st.session_state['github_publish_history']) > 10:
            st.session_state['github_publish_history'] = st.session_state['github_publish_history'][-10:]
        
    except Exception as e:
        logger.error(f"公開履歴保存エラー: {e}")

def create_sample_publish_demo():
    """サンプルデータでの公開デモ"""
    st.sidebar.info("🧪 サンプルデータでの公開機能をテスト中...")
    
    # サンプルHTMLの生成
    sample_html = generate_sample_dashboard_html()
    
    # ダウンロード提供
    st.sidebar.download_button(
        label="📥 サンプルHTML",
        data=sample_html.encode('utf-8'),
        file_name=f"sample_dashboard_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
        mime="text/html",
        key="download_sample_html"
    )
    
    st.sidebar.info("""
    **サンプルHTMLの使い方:**
    1. 上記ボタンでサンプルをダウンロード
    2. [Netlify Drop](https://app.netlify.com/drop) でテスト公開
    3. 動作確認後、実際のデータで本格運用
    """)

def generate_sample_dashboard_html() -> str:
    """サンプルダッシュボードHTML生成"""
    return """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>サンプル 詳細アクション提案ダッシュボード</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f5f7fa; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { text-align: center; color: #293a27; }
        .sample-notice { background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .action-card { background: white; border-left: 6px solid #7fb069; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 詳細アクション提案ダッシュボード</h1>
        
        <div class="sample-notice">
            <h3>📋 これはサンプル表示です</h3>
            <p>実際のデータを読み込むと、ここに詳細なアクション提案が表示されます。</p>
        </div>
        
        <div class="action-card">
            <h3>内科</h3>
            <p><strong>推奨アクション:</strong> 新入院重視</p>
            <p>病床に余裕があり、新入院増加が効果的です。</p>
            <p>在院患者数: 45.2人 (達成率: 87.3%)</p>
        </div>
        
        <div class="action-card">
            <h3>外科</h3>
            <p><strong>推奨アクション:</strong> 現状維持</p>
            <p>目標をほぼ達成しており、良好な状況を継続してください。</p>
            <p>在院患者数: 38.7人 (達成率: 96.8%)</p>
        </div>
        
        <footer style="text-align: center; margin-top: 40px; color: #666;">
            <p>生成時刻: """ + datetime.now().strftime('%Y年%m月%d日 %H:%M:%S') + """</p>
            <p>🏥 サンプルダッシュボード</p>
        </footer>
    </div>
</body>
</html>"""

def _update_external_dashboards(title, description, filename):
    """外部ダッシュボード情報を更新"""
    external_dashboards = st.session_state.get('external_dashboards', [])
    
    # ファイル名を正規化
    safe_filename = filename.lower().replace(' ', '_').replace('　', '_')
    
    new_dash = {
        "title": title,
        "description": description,
        "file": safe_filename,
        "type": "external",
        "update_time": datetime.now().strftime('%Y/%m/%d %H:%M')
    }
    
    # 既存の場合は更新、なければ追加
    updated = False
    for i, dash in enumerate(external_dashboards):
        if dash['file'] == new_dash['file']:
            external_dashboards[i] = new_dash
            updated = True
            break
    
    if not updated:
        external_dashboards.append(new_dash)
    
    st.session_state.external_dashboards = external_dashboards

def generate_performance_dashboard_html(df, target_data, period, dashboard_type):
    """
    パフォーマンスダッシュボードHTMLを生成（4タブ統合版・ソート対応・トレンド分析修正版 v2）
    """
    if not REQUIRED_MODULES['performance']:
        logger.error("パフォーマンスモジュールが利用できません")
        return None
    
    try:
        # 必要な関数のインポート
        from html_export_functions import generate_combined_html_with_tabs
        from utils import safe_date_filter
        from department_performance_tab import get_hospital_targets
        
        # dashboard_typeに応じた設定
        if dashboard_type == "department":
            from department_performance_tab import get_period_dates, calculate_department_kpis
            get_dates_func = get_period_dates
            calculate_kpi_func = calculate_department_kpis
            possible_cols = ['部門名', '診療科', '診療科名']
        else:  # ward
            from ward_performance_tab import get_period_dates, calculate_ward_kpis
            get_dates_func = get_period_dates
            calculate_kpi_func = calculate_ward_kpis
            possible_cols = ['病棟コード', '病棟名', '病棟']
            
        # 期間設定
        start_date, end_date, period_desc = get_dates_func(df, period)
        if not start_date or not end_date:
            return None
            
        date_filtered_df = safe_date_filter(df, start_date, end_date)
        if '病棟コード' in date_filtered_df.columns and EXCLUDED_WARDS:
            date_filtered_df = date_filtered_df[~date_filtered_df['病棟コード'].isin(EXCLUDED_WARDS)]
            
        item_col = next((c for c in possible_cols if c in date_filtered_df.columns), None)
        if not item_col:
            return None
            
        unique_items = date_filtered_df[item_col].unique()
        if dashboard_type == "ward":
            unique_items = [w for w in unique_items if w not in EXCLUDED_WARDS]
        
        # ★ 修正箇所 1: 正しい辞書定義と、トレンド分析以外のメトリクス設定
        metric_opts = {
            "日平均在院患者数": {
                "avg": "daily_avg_census", 
                "recent": "recent_week_daily_census", 
                "target": "daily_census_target", 
                "ach": "daily_census_achievement", 
                "unit": "人"
            },
            "週合計新入院患者数": {
                "avg": "weekly_avg_admissions", 
                "recent": "recent_week_admissions", 
                "target": "weekly_admissions_target", 
                "ach": "weekly_admissions_achievement", 
                "unit": "件"
            }
        }
        
        metrics_data_dict = {}
        metric_names = ["日平均在院患者数", "週合計新入院患者数", "平均在院日数（トレンド分析）"]
        
        for metric_name in metric_names:
            if metric_name == "平均在院日数（トレンド分析）":
                kpi_list_for_sort = []
                for item_code in unique_items:
                    kpi = calculate_kpi_func(date_filtered_df, target_data, item_code, item_code, start_date, end_date, item_col)
                    if kpi:
                        kpi_list_for_sort.append(kpi)
                
                def get_trend_sort_key(kpi):
                    period_avg = kpi.get('avg_length_of_stay', 0)
                    recent = kpi.get('recent_week_avg_los', 0)
                    if period_avg > 0:
                        change_rate = ((recent - period_avg) / period_avg) * 100
                        if change_rate > 3: return 0
                        elif change_rate < -3: return 2
                        else: return 1
                    return 1
                
                kpi_list_for_sort.sort(key=get_trend_sort_key)
                
                trend_cards_html = ""
                for kpi in kpi_list_for_sort:
                    item_code = kpi.get('dept_code' if dashboard_type == "department" else 'ward_code')
                    item_name = kpi.get('dept_name' if dashboard_type == "department" else 'ward_name')
                    item_df = date_filtered_df[date_filtered_df[item_col] == item_code]
                    
                    card_html = _render_los_trend_card_for_publish(
                        label=item_name,
                        period_avg=kpi.get('avg_length_of_stay', 0),
                        recent=kpi.get('recent_week_avg_los', 0),
                        unit="日",
                        item_df=item_df,
                        start_date=start_date,
                        end_date=end_date
                    )
                    trend_cards_html += card_html
                
                metrics_data_dict[metric_name] = f'<div class="grid-container">{trend_cards_html}</div>'

            else: # 従来のKPI指標の処理
                kpi_list = []
                for item_code in unique_items:
                    kpi = calculate_kpi_func(date_filtered_df, target_data, item_code, item_code, start_date, end_date, item_col)
                    if kpi:
                        kpi_list.append(kpi)
                
                # ★ 修正箇所 2: ソートロジックを堅牢化
                opt = metric_opts[metric_name]
                # 表示される達成率（直近週実績ベース）でソートするように修正
                kpi_list.sort(
                    key=lambda kpi: (kpi.get(opt['recent'], 0) / kpi.get(opt['target']) * 100) if kpi.get(opt['target']) else 0,
                    reverse=True
                )
                metrics_data_dict[metric_name] = kpi_list
        
        # アクション提案データの生成（変更なし）
        from department_performance_tab import evaluate_feasibility, calculate_effect_simulation, decide_action_and_reasoning
        action_results = []
        for item_code in unique_items:
            kpi = calculate_kpi_func(date_filtered_df, target_data, item_code, item_code, start_date, end_date, item_col)
            if kpi:
                item_df = date_filtered_df[date_filtered_df[item_col] == item_code]
                feasibility = evaluate_feasibility(kpi, item_df, start_date, end_date)
                simulation = calculate_effect_simulation(kpi)
                action_result = decide_action_and_reasoning(kpi, feasibility, simulation)
                action_results.append({'kpi': kpi, 'action_result': action_result, 'feasibility': feasibility, 'simulation': simulation})
        
        priority_order = {"urgent": 0, "medium": 1, "low": 2}
        action_results.sort(key=lambda x: (priority_order.get(x.get('action_result', {}).get('priority', 'low'), 2), -x.get('kpi', {}).get('daily_avg_census', 0)))
        
        hospital_targets = get_hospital_targets(target_data)
        action_data = {'action_results': action_results, 'hospital_targets': hospital_targets}
        
        # 統合HTMLの生成
        html_content = generate_combined_html_with_tabs(metrics_data_dict, action_data, period_desc, dashboard_type)
        
        if html_content:
            publish_data = {
                'content_type': f'{dashboard_type}別パフォーマンス',
                'period_desc': period_desc,
                'dashboard_type': dashboard_type,
                'data_summary': {'generated_at': datetime.now().isoformat(), 'start_date': start_date.isoformat(), 'end_date': end_date.isoformat(), 'total_records': len(date_filtered_df), 'analysis_items': len(unique_items)}
            }
            return add_web_publish_features(html_content, publish_data, False, True)
        
        return html_content

    except Exception as e:
        logger.error(f"{dashboard_type}別統合ダッシュボード生成エラー: {e}", exc_info=True)
        return None

def generate_90day_report_html(df, target_data):
    """90日間総合レポートのHTML生成（目標値・目標達成率対応版・FABホームボタン付き・病棟名表示対応）"""
    try:
        # utils.pyから病棟名変換関数をインポート
        from utils import get_ward_display_name
        
        # データ準備（既存のコード）
        if not all([create_interactive_alos_chart, create_interactive_patient_chart, create_interactive_dual_axis_chart]):
            return "グラフ生成に必要なモジュール（chart.py）がインポートできませんでした。"

        df_copy = df.copy()
        if '病棟コード' in df_copy.columns and EXCLUDED_WARDS:
            df_copy = df_copy[~df_copy['病棟コード'].isin(EXCLUDED_WARDS)]

        if not pd.api.types.is_datetime64_any_dtype(df_copy['日付']):
            df_copy['日付'] = pd.to_datetime(df_copy['日付'], errors='coerce')
        df_copy.dropna(subset=['日付'], inplace=True)
        
        end_date = df_copy['日付'].max()
        start_date = end_date - timedelta(days=89)
        df_90days = df_copy[(df_copy['日付'] >= start_date) & (df_copy['日付'] <= end_date)].copy()
        
        if df_90days.empty:
            return None

        # 診療科・病棟リストの取得
        unique_departments = sorted(df_90days['診療科名'].unique())
        unique_wards = sorted(df_90days['病棟コード'].astype(str).unique())
        
        # ★★★ 病棟コードから病棟名への変換辞書を作成（新規追加） ★★★
        ward_code_to_name = {}
        for ward_code in unique_wards:
            ward_name = get_ward_display_name(ward_code)
            ward_code_to_name[ward_code] = ward_name
        
        # ★★★ 目標値辞書の作成（既存コード） ★★★
        target_dict = {}
        if target_data is not None and not target_data.empty:
            period_col_name = '区分' if '区分' in target_data.columns else '期間区分'
            indicator_col_name = '指標タイプ'
            
            if all(col in target_data.columns for col in ['部門コード', '目標値', period_col_name, indicator_col_name]):
                for _, row in target_data.iterrows():
                    dept_code = str(row['部門コード']).strip()
                    indicator = str(row[indicator_col_name]).strip()
                    period = str(row[period_col_name]).strip()
                    key = (dept_code, indicator, period)
                    target_dict[key] = row['目標値']

        # グラフコンテナのHTML生成（既存のコード）
        graph_containers_html = ""
        
        # 全体のグラフ（既存コード）
        target_value_all = None
        if target_dict:
            all_keys = [
                ("全体", "日平均在院患者数", "全日"),
                ("病院全体", "日平均在院患者数", "全日"),
                ("全院", "日平均在院患者数", "全日")
            ]
            for key in all_keys:
                if key in target_dict:
                    target_value_all = float(target_dict[key])
                    break
        
        fig_alos_all = create_interactive_alos_chart(df_90days, title="", days_to_show=90)
        fig_patient_all = create_interactive_patient_chart(
            df_90days, 
            title="", 
            days=90, 
            show_moving_average=True,
            target_value=target_value_all
        )
        fig_dual_all = create_interactive_dual_axis_chart(df_90days, title="", days=90)
        
        graph_containers_html += f"""
        <div class="graph-group" id="graphs-全体" style="display: block;">
            <h3>平均在院日数推移（90日間）</h3>
            <div class="chart-wrapper">
                {fig_alos_all.to_html(full_html=False, include_plotlyjs='cdn') if fig_alos_all else "<div>グラフ生成失敗</div>"}
            </div>
            
            <h3>入院患者数推移（90日間）</h3>
            <div class="chart-wrapper">
                {fig_patient_all.to_html(full_html=False, include_plotlyjs=False) if fig_patient_all else "<div>グラフ生成失敗</div>"}
            </div>
            
            <h3>患者移動推移（90日間）</h3>
            <div class="chart-wrapper">
                {fig_dual_all.to_html(full_html=False, include_plotlyjs=False) if fig_dual_all else "<div>グラフ生成失敗</div>"}
            </div>
        </div>
        """
        
        # 各診療科のグラフ（既存のコード）
        for dept in unique_departments:
            dept_df = df_90days[df_90days['診療科名'] == dept]
            if not dept_df.empty:
                dept_target_value = None
                if target_dict:
                    dept_key = (str(dept), "日平均在院患者数", "全日")
                    if dept_key in target_dict:
                        dept_target_value = float(target_dict[dept_key])
                
                fig_alos_dept = create_interactive_alos_chart(dept_df, title="", days_to_show=90)
                fig_patient_dept = create_interactive_patient_chart(
                    dept_df, 
                    title="", 
                    days=90, 
                    show_moving_average=True,
                    target_value=dept_target_value
                )
                fig_dual_dept = create_interactive_dual_axis_chart(dept_df, title="", days=90)

                safe_dept_id = "dept_" + dept.replace(' ', '_').replace('　', '_').replace('/', '_').replace('\\', '_')
                
                graph_containers_html += f"""
                <div class="graph-group" id="graphs-{safe_dept_id}" style="display: none;">
                    <h3>平均在院日数推移（90日間）- {dept}</h3>
                    <div class="chart-wrapper">
                        {fig_alos_dept.to_html(full_html=False, include_plotlyjs=False) if fig_alos_dept else "<div>グラフ生成失敗</div>"}
                    </div>
                    
                    <h3>入院患者数推移（90日間）- {dept}</h3>
                    <div class="chart-wrapper">
                        {fig_patient_dept.to_html(full_html=False, include_plotlyjs=False) if fig_patient_dept else "<div>グラフ生成失敗</div>"}
                    </div>
                    
                    <h3>患者移動推移（90日間）- {dept}</h3>
                    <div class="chart-wrapper">
                        {fig_dual_dept.to_html(full_html=False, include_plotlyjs=False) if fig_dual_dept else "<div>グラフ生成失敗</div>"}
                    </div>
                </div>
                """
        
        # ★★★ 各病棟のグラフ（病棟名表示対応版） ★★★
        for ward in unique_wards:
            ward_df = df_90days[df_90days['病棟コード'].astype(str) == ward]
            if not ward_df.empty:
                # 病棟の目標値を取得
                ward_target_value = None
                if target_dict:
                    ward_key = (str(ward), "日平均在院患者数", "全日")
                    if ward_key in target_dict:
                        ward_target_value = float(target_dict[ward_key])
                
                fig_alos_ward = create_interactive_alos_chart(ward_df, title="", days_to_show=90)
                fig_patient_ward = create_interactive_patient_chart(
                    ward_df, 
                    title="", 
                    days=90, 
                    show_moving_average=True,
                    target_value=ward_target_value
                )
                fig_dual_ward = create_interactive_dual_axis_chart(ward_df, title="", days=90)
                
                safe_ward_id = "ward_" + str(ward).replace(' ', '_').replace('　', '_').replace('/', '_').replace('\\', '_')
                
                # ★★★ 病棟名を使用して表示 ★★★
                ward_display_name = ward_code_to_name.get(ward, ward)  # 変換できない場合はコードのまま
                
                graph_containers_html += f"""
                <div class="graph-group" id="graphs-{safe_ward_id}" style="display: none;">
                    <h3>平均在院日数推移（90日間）- {ward_display_name}</h3>
                    <div class="chart-wrapper">
                        {fig_alos_ward.to_html(full_html=False, include_plotlyjs=False) if fig_alos_ward else "<div>グラフ生成失敗</div>"}
                    </div>
                    
                    <h3>入院患者数推移（90日間）- {ward_display_name}</h3>
                    <div class="chart-wrapper">
                        {fig_patient_ward.to_html(full_html=False, include_plotlyjs=False) if fig_patient_ward else "<div>グラフ生成失敗</div>"}
                    </div>
                    
                    <h3>患者移動推移（90日間）- {ward_display_name}</h3>
                    <div class="chart-wrapper">
                        {fig_dual_ward.to_html(full_html=False, include_plotlyjs=False) if fig_dual_ward else "<div>グラフ生成失敗</div>"}
                    </div>
                </div>
                """

        # ★★★ テーブル生成（病棟名表示対応版） ★★★
        period_definitions = {
            "直近7日": (end_date - timedelta(days=6), end_date),
            "直近30日": (end_date - timedelta(days=29), end_date),
            "90日間": (start_date, end_date),
        }
        
        dept_metrics = {dept: {} for dept in unique_departments}
        ward_metrics = {ward: {} for ward in unique_wards}
        
        # 目標達成率計算用の指標名
        METRIC_FOR_TARGET = '日平均在院患者数'

        for period_label, (start_dt, end_dt) in period_definitions.items():
            period_df = df_90days[(df_90days['日付'] >= start_dt) & (df_90days['日付'] <= end_dt)]
            num_days = period_df['日付'].nunique()
            if num_days == 0: continue
            
            if not period_df.empty:
                dept_period_stats = period_df.groupby('診療科名')['在院患者数'].sum() / num_days
                for dept, avg_census in dept_period_stats.items():
                    if str(dept) in dept_metrics:
                        dept_metrics[str(dept)][period_label] = avg_census

                ward_period_stats = period_df.groupby('病棟コード')['在院患者数'].sum() / num_days
                for ward, avg_census in ward_period_stats.items():
                    if str(ward) in ward_metrics:
                        ward_metrics[str(ward)][period_label] = avg_census

        # 診療科別の目標値と目標達成率を計算（既存コード）
        for dept in unique_departments:
            dept_str = str(dept)
            target_key = (dept_str, METRIC_FOR_TARGET, '全日')
            target_value = target_dict.get(target_key, None)
            dept_metrics[dept_str]['目標値'] = target_value
            
            actual_7days = dept_metrics[dept_str].get('直近7日', 0)
            if target_value and target_value > 0 and actual_7days:
                achievement_rate = (actual_7days / target_value) * 100
                dept_metrics[dept_str]['目標達成率(%)'] = achievement_rate
            else:
                dept_metrics[dept_str]['目標達成率(%)'] = None

        # 病棟別の目標値と目標達成率を計算（既存コード）
        for ward in unique_wards:
            ward_str = str(ward)
            target_key = (ward_str, METRIC_FOR_TARGET, '全日')
            target_value = target_dict.get(target_key, None)
            ward_metrics[ward_str]['目標値'] = target_value
            
            actual_7days = ward_metrics[ward_str].get('直近7日', 0)
            if target_value and target_value > 0 and actual_7days:
                achievement_rate = (actual_7days / target_value) * 100
                ward_metrics[ward_str]['目標達成率(%)'] = achievement_rate
            else:
                ward_metrics[ward_str]['目標達成率(%)'] = None

        # 診療科別テーブルHTML（既存コード）
        dept_table_html = "<table><thead><tr><th>診療科</th>"
        for label in period_definitions.keys(): 
            dept_table_html += f"<th>{label}</th>"
        dept_table_html += "<th>目標値</th><th>目標達成率(%)</th></tr></thead><tbody>"
        
        sorted_depts = sorted(unique_departments, 
                             key=lambda d: dept_metrics.get(str(d), {}).get("目標達成率(%)", 0) or 0, 
                             reverse=True)
        
        for dept in sorted_depts:
            dept_str = str(dept)
            dept_table_html += f"<tr><td>{dept}</td>"
            
            for period in period_definitions.keys():
                val = dept_metrics.get(dept_str, {}).get(period)
                dept_table_html += f"<td>{val:.1f}</td>" if pd.notna(val) else "<td>-</td>"
            
            target_val = dept_metrics.get(dept_str, {}).get('目標値')
            dept_table_html += f"<td>{target_val:.1f}</td>" if pd.notna(target_val) else "<td>-</td>"
            
            achievement_val = dept_metrics.get(dept_str, {}).get('目標達成率(%)')
            if pd.notna(achievement_val):
                if achievement_val >= 100:
                    color_class = "style='color: #4CAF50; font-weight: bold;'"
                elif achievement_val >= 80:
                    color_class = "style='color: #FF9800; font-weight: bold;'"
                else:
                    color_class = "style='color: #F44336; font-weight: bold;'"
                dept_table_html += f"<td {color_class}>{achievement_val:.1f}%</td>"
            else:
                dept_table_html += "<td>-</td>"
            
            dept_table_html += "</tr>"
        dept_table_html += "</tbody></table>"

        # ★★★ 病棟別テーブルHTML（病棟名表示対応版） ★★★
        ward_table_html = "<table><thead><tr><th>病棟</th>"
        for label in period_definitions.keys(): 
            ward_table_html += f"<th>{label}</th>"
        ward_table_html += "<th>目標値</th><th>目標達成率(%)</th></tr></thead><tbody>"
        
        sorted_wards = sorted(unique_wards, 
                             key=lambda w: ward_metrics.get(str(w), {}).get("目標達成率(%)", 0) or 0, 
                             reverse=True)
        
        for ward in sorted_wards:
            ward_str = str(ward)
            # ★★★ 病棟名を表示に使用 ★★★
            ward_display_name = ward_code_to_name.get(ward, ward)
            ward_table_html += f"<tr><td>{ward_display_name}</td>"
            
            for period in period_definitions.keys():
                val = ward_metrics.get(ward_str, {}).get(period)
                ward_table_html += f"<td>{val:.1f}</td>" if pd.notna(val) else "<td>-</td>"
            
            target_val = ward_metrics.get(ward_str, {}).get('目標値')
            ward_table_html += f"<td>{target_val:.1f}</td>" if pd.notna(target_val) else "<td>-</td>"
            
            achievement_val = ward_metrics.get(ward_str, {}).get('目標達成率(%)')
            if pd.notna(achievement_val):
                if achievement_val >= 100:
                    color_class = "style='color: #4CAF50; font-weight: bold;'"
                elif achievement_val >= 80:
                    color_class = "style='color: #FF9800; font-weight: bold;'"
                else:
                    color_class = "style='color: #F44336; font-weight: bold;'"
                ward_table_html += f"<td {color_class}>{achievement_val:.1f}%</td>"
            else:
                ward_table_html += "<td>-</td>"
            
            ward_table_html += "</tr>"
        ward_table_html += "</tbody></table>"

        # ★★★ HTML生成部分（病棟セレクター部分も病棟名表示対応） ★★★
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>入院管理総合レポート - 90日間分析</title>
    <style>
        /* CSSは既存のまま */
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: 'Noto Sans JP', -apple-system, BlinkMacSystemFont, sans-serif; 
            background: #f5f5f5; 
            color: #333; 
            line-height: 1.6; 
        }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 40px; 
            border-radius: 10px; 
            margin-bottom: 30px; 
            text-align: center; 
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .period {{ font-size: 1.2em; opacity: 0.9; }}
        
        .selector-container {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .selector-row {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 30px;
            flex-wrap: wrap;
        }}
        .selector-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .selector-group label {{
            font-weight: bold;
            color: #667eea;
        }}
        select {{
            padding: 10px 20px;
            font-size: 16px;
            border: 2px solid #667eea;
            border-radius: 5px;
            background: white;
            cursor: pointer;
            min-width: 200px;
        }}
        select:focus {{
            outline: none;
            border-color: #764ba2;
        }}
        
        .section {{ 
            background: white; 
            padding: 30px; 
            border-radius: 10px; 
            margin-bottom: 30px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }}
        .section h2 {{ 
            color: #667eea; 
            margin-bottom: 20px; 
            padding-bottom: 10px; 
            border-bottom: 2px solid #e2e8f0; 
        }}
        .section h3 {{ 
            color: #4a5568; 
            margin-top: 25px; 
            margin-bottom: 10px; 
            font-size: 1.2em; 
        }}
        .chart-wrapper {{ 
            border: 1px solid #e2e8f0; 
            border-radius: 8px; 
            padding: 10px; 
            margin-top: 15px; 
        }}
        
        .graph-group {{
            display: none;
        }}
        
        table {{ 
            width: 100%; 
            border-collapse: collapse; 
            margin-top: 20px; 
            font-size: 0.95em;
        }}
        th, td {{ 
            padding: 12px 8px; 
            text-align: center; 
            border-bottom: 1px solid #e2e8f0; 
            border-right: 1px solid #e2e8f0;
        }}
        th {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white;
            font-weight: 600; 
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td:first-child, th:first-child {{ 
            text-align: left; 
            font-weight: 500; 
            border-left: 1px solid #e2e8f0;
        }}
        th:last-child, td:last-child {{
            border-right: 1px solid #e2e8f0;
        }}
        tr:hover {{ 
            background: #f7fafc; 
        }}
        
        th:last-child {{
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        }}
        
        .print-button {{ 
            display: block; 
            width: fit-content; 
            margin: 20px auto; 
            padding: 15px 30px; 
            background: #48bb78; 
            color: white; 
            text-decoration: none; 
            border-radius: 5px; 
            font-weight: bold; 
            cursor: pointer; 
            border: none;
            font-size: 16px;
        }}
        
        .print-button:hover {{
            background: #38a169;
            transform: translateY(-2px);
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        }}
        
        .fab-home {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            text-decoration: none;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
            z-index: 9999;
            cursor: pointer;
        }}
        
        .fab-home:hover {{
            transform: scale(1.1) translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.4);
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }}
        
        .fab-home:active {{
            transform: scale(0.95);
        }}
        
        .fab-home .fab-icon {{
            font-size: 1.8em;
            line-height: 1;
        }}
        
        .fab-home::before {{
            content: "ホームに戻る";
            position: absolute;
            right: 70px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 0.9em;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s ease;
        }}
        
        .fab-home:hover::before {{
            opacity: 1;
        }}
        
        @media (max-width: 768px) {{ 
            .header h1 {{ font-size: 1.8em; }} 
            select {{ min-width: 150px; font-size: 14px; }}
            .selector-row {{ flex-direction: column; gap: 15px; }}
            
            table {{
                font-size: 0.85em;
            }}
            th, td {{
                padding: 8px 4px;
            }}
            
            .fab-home {{
                bottom: 20px;
                right: 20px;
                width: 50px;
                height: 50px;
            }}
            
            .fab-home .fab-icon {{
                font-size: 1.5em;
            }}
            
            .fab-home::before {{
                display: none;
            }}
        }}
        
        @media print {{ 
            .selector-container {{ display: none; }}
            .print-button {{ display: none; }} 
            .section {{ page-break-inside: avoid; }}
            .fab-home {{ display: none; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 入院管理総合レポート</h1>
            <p class="period">分析期間: {start_date.strftime('%Y年%m月%d日')} - {end_date.strftime('%Y年%m月%d日')} (90日間)</p>
            <p style="font-size: 0.9em; margin-top: 10px; opacity: 0.8;">
                ※ 直近7日実績による目標達成率で降順ソート表示 | 
                <span style="color: #4CAF50;">■</span> 100%以上 
                <span style="color: #FF9800;">■</span> 80%以上 
                <span style="color: #F44336;">■</span> 80%未満
            </p>
        </div>
        
        <div class="selector-container">
            <div class="selector-row">
                <div class="selector-group">
                    <label for="viewTypeSelector">📊 表示種別:</label>
                    <select id="viewTypeSelector" onchange="changeView()">
                        <option value="all">全体</option>
                        <option value="department">診療科別</option>
                        <option value="ward">病棟別</option>
                    </select>
                </div>
                
                <div class="selector-group" id="departmentSelectorGroup" style="display: none;">
                    <label for="departmentSelector">🏥 診療科:</label>
                    <select id="departmentSelector" onchange="changeView()">
                        {"".join([f'<option value="dept_{dept.replace(" ", "_").replace("　", "_").replace("/", "_").replace(chr(92), "_")}">{dept}</option>' for dept in unique_departments])}
                    </select>
                </div>
                
                <div class="selector-group" id="wardSelectorGroup" style="display: none;">
                    <label for="wardSelector">🛏️ 病棟:</label>
                    <select id="wardSelector" onchange="changeView()">
                        {"".join([f'<option value="ward_{str(ward).replace(" ", "_").replace("　", "_").replace("/", "_").replace(chr(92), "_")}">{ward_code_to_name.get(ward, ward)}</option>' for ward in unique_wards])}
                    </select>
                </div>
            </div>
        </div>
        
        <div id="overall" class="section">
            <h2>📊 グラフ分析</h2>
            {graph_containers_html}
        </div>
        
        <div id="department" class="section">
            <h2>🏥 診療科別分析（直近7日実績による目標達成率順）</h2>
            <h3>診療科別 平均在院患者数・目標達成状況</h3>
            <p style="margin-bottom: 15px; color: #666; font-size: 0.9em;">
                ※ 直近7日実績による目標達成率の高い順に表示。色分け：緑(100%以上)、橙(80%以上)、赤(80%未満)
            </p>
            {dept_table_html}
        </div>
        
        <div id="ward" class="section">
            <h2>🛏️ 病棟別分析（直近7日実績による目標達成率順）</h2>
            <h3>病棟別 平均在院患者数・目標達成状況</h3>
            <p style="margin-bottom: 15px; color: #666; font-size: 0.9em;">
                ※ 直近7日実績による目標達成率の高い順に表示。色分け：緑(100%以上)、橙(80%以上)、赤(80%未満)
            </p>
            {ward_table_html}
        </div>
        
        <button class="print-button" onclick="window.print()">📥 PDFとして保存（印刷）</button>
    </div>
    
    <a href="./index.html" class="fab-home" aria-label="ホームに戻る">
        <span class="fab-icon">🏠</span>
    </a>
    
    <script>
        function changeView() {{
            const viewType = document.getElementById('viewTypeSelector').value;
            const deptGroup = document.getElementById('departmentSelectorGroup');
            const wardGroup = document.getElementById('wardSelectorGroup');
            
            const allGroups = document.querySelectorAll('.graph-group');
            allGroups.forEach(group => {{
                group.style.display = 'none';
            }});
            
            deptGroup.style.display = 'none';
            wardGroup.style.display = 'none';
            
            let targetId = '';
            
            if (viewType === 'all') {{
                targetId = 'graphs-全体';
            }} else if (viewType === 'department') {{
                deptGroup.style.display = 'flex';
                const selectedDept = document.getElementById('departmentSelector').value;
                targetId = 'graphs-' + selectedDept;
            }} else if (viewType === 'ward') {{
                wardGroup.style.display = 'flex';
                const selectedWard = document.getElementById('wardSelector').value;
                targetId = 'graphs-' + selectedWard;
            }}
            
            const targetGroup = document.getElementById(targetId);
            if (targetGroup) {{
                targetGroup.style.display = 'block';
                
                setTimeout(() => {{
                    window.dispatchEvent(new Event('resize'));
                }}, 100);
            }}
        }}
        
        window.addEventListener('load', function() {{
            document.getElementById('departmentSelector').selectedIndex = 0;
            document.getElementById('wardSelector').selectedIndex = 0;
            
            setTimeout(function() {{
                window.dispatchEvent(new Event('resize'));
            }}, 100);
        }});
    </script>
</body>
</html>"""
        
        return html_content
        
    except Exception as e:
        logger.error(f"90日間レポート生成エラー: {e}", exc_info=True)
        return None

def display_publish_history_compact():
    """コンパクトな公開履歴表示"""
    try:
        history = st.session_state.get('github_publish_history', [])
        
        if history:
            st.sidebar.markdown("**📋 公開履歴**")
            for entry in reversed(history[-3:]):  # 最新3件
                timestamp = datetime.fromisoformat(entry['timestamp'])
                st.sidebar.caption(f"• {timestamp.strftime('%m/%d %H:%M')} - {entry['period']}")
                if entry.get('url'):
                    st.sidebar.caption(f"  [📊 確認]({entry['url']})")
        
    except Exception as e:
        logger.error(f"公開履歴表示エラー: {e}")

def show_github_setup_guide():
    """GitHub設定ガイドの表示"""
    st.sidebar.info("""
    **GitHub設定手順:**
    
    1. GitHub Personal Access Token取得
       - GitHub > Settings > Developer settings
       - Personal access tokens > Generate new token
       - 権限: `repo`, `workflow`
    
    2. リポジトリ作成
       - 新しいPublicリポジトリを作成
       - 名前: hospital-dashboard など
    
    3. 設定テスト実行
       - 上記「🧪 接続テスト」で確認
    
    4. 公開実行
       - 「🚀 公開実行」で GitHub Pages に公開
    """)

def create_github_publisher_interface():
    """
    GitHub自動公開インターフェース（UI表示ロジック修正版 v3）
    """
    st.sidebar.markdown("---")
    st.sidebar.header("🌐 統合ダッシュボード公開")

    # --- GitHub設定の入力欄 (常に表示) ---
    st.sidebar.markdown("**🔗 GitHub設定**")
    github_token = st.sidebar.text_input(
        "Personal Access Token", type="password", help="GitHubのPersonal Access Token（repo権限必要）",
        key="github_token_input"
    )
    repo_name_input = st.sidebar.text_input(
        "リポジトリ名", value="Genie-Scripts/Streamlit-Dashboard",
        help="公開用GitHubリポジトリ名（username/repository形式）", key="github_repo_input"
    )
    branch_name = st.sidebar.selectbox(
        "ブランチ", ["main", "gh-pages", "master"], index=0, help="GitHub Pagesのブランチ",
        key="github_branch_select"
    )

    # --- 設定適用ボタン (常に表示) ---
    # ★★★ 修正箇所: st.button を st.sidebar.button に変更 ★★★
    if st.sidebar.button("🧪 設定を適用", key="apply_github_settings", use_container_width=True,
                 help="入力されたGitHub設定をテストし、アプリに適用します"):
        if github_token and repo_name_input:
            with st.spinner("🔍 GitHub接続を確認し、設定を適用中..."):
                test_github_connection(github_token, repo_name_input)
                try:
                    owner, repo = repo_name_input.split('/')
                    from github_publisher import GitHubPublisher
                    publisher = GitHubPublisher(repo_owner=owner, repo_name=repo, token=github_token, branch=branch_name)
                    st.session_state.github_publisher = publisher
                    st.sidebar.success("✅ 設定が適用されました。")
                except (ValueError, Exception) as e:
                    st.sidebar.error(f"設定適用に失敗: {e}")
                    if 'github_publisher' in st.session_state:
                        del st.session_state.github_publisher
        else:
            st.sidebar.error("❌ GitHub Tokenとリポジトリ名を入力してください")

    # --- 設定適用後の公開操作UI (条件付き表示) ---
    if st.session_state.get('github_publisher'):
        st.sidebar.success("設定適用済みです。公開操作が可能です。")
        
        # ここで公開準備状況を確認
        can_publish, status_message = check_publish_readiness()
        
        if can_publish:
            st.sidebar.markdown("**📊 公開設定**")
            content_types = ["詳細アクション提案（診療科別）", "詳細アクション提案（病棟別）", "KPI指標ダッシュボード", "統合レポート（全機能）"]
            selected_content = st.sidebar.selectbox("公開内容", content_types, index=0, key="github_content_type")
            period_options = ["直近4週間", "直近8週", "直近12週", "今年度", "先月"]
            selected_period = st.sidebar.selectbox("📅 分析期間", period_options, index=0, key="github_analysis_period")
            
            st.sidebar.markdown("**🚀 実行**")
            # ★★★ 修正箇所: st.button を st.sidebar.button に変更 ★★★
            if st.sidebar.button("🚀 公開実行", key="execute_github_publish", use_container_width=True):
                # 実行時の認証情報をセッション状態から再取得
                token_on_exec = st.session_state.get('github_token_input')
                repo_on_exec = st.session_state.get('github_repo_input')
                branch_on_exec = st.session_state.get('github_branch_select')
                
                if token_on_exec and repo_on_exec:
                    execute_github_publish(
                        selected_content, selected_period, token_on_exec, repo_on_exec,
                        branch_on_exec, True, False, True  # auto_refresh, debug, mobile
                    )
                else:
                    st.error("GitHubの認証情報が不足しています。")
        else:
            # 設定は適用されたが、データが公開準備できていない場合
            st.sidebar.warning("⚠️ 公開準備未完了")
            st.sidebar.info(status_message)

    else:
        st.sidebar.warning("「設定を適用」ボタンを押して、GitHub設定を有効化してください。")

    display_publish_history_compact()
    
    # --- 外部ダッシュボード追加機能 ---
    create_external_dashboard_uploader()

def _generate_and_publish_90day_report(publisher):
    """90日間レポートの生成と公開"""
    with st.spinner("90日間レポートを生成中..."):
        try:
            df = st.session_state['df']
            target_data = st.session_state.get('target_data', pd.DataFrame())
            
            # generate_90day_report_html関数をインポート
            try:
                from github_publisher import generate_90day_report_html
            except ImportError:
                # 関数が見つからない場合は元のコードから復元
                generate_90day_report_html = _generate_90day_report_html_fallback
            
            html_report = generate_90day_report_html(df, target_data)
            
            if html_report:
                success, message = publisher.upload_html_file(
                    html_report,
                    "docs/comprehensive_report_90days.html",
                    f"Update 90-day comprehensive report - {datetime.now().strftime('%Y-%m-%d')}"
                )
                
                if success:
                    st.success("✅ 90日間レポート公開成功！")
                    
                    # 外部ダッシュボードリストに追加
                    external_dashboards = st.session_state.get('external_dashboards', [])
                    report_dash_info = {
                        "title": "90日間総合レポート",
                        "description": "全体・診療科別・病棟別の詳細分析",
                        "file": "comprehensive_report_90days.html",
                        "type": "external",
                        "update_time": datetime.now().strftime('%Y/%m/%d %H:%M')
                    }
                    
                    # 既存の場合は更新、なければ追加
                    updated = False
                    for i, dash in enumerate(external_dashboards):
                        if dash.get('title') == "90日間総合レポート":
                            external_dashboards[i] = report_dash_info
                            updated = True
                            break
                    
                    if not updated:
                        external_dashboards.append(report_dash_info)
                    
                    st.session_state.external_dashboards = external_dashboards
                    
                    st.info("💡 公開リストにレポートが追加されました。次回「トップページ」を公開すると反映されます。")
                    st.rerun()
                else:
                    st.error(f"❌ レポート公開失敗: {message}")
            else:
                st.error("❌ レポートHTMLの生成に失敗しました。")
                
        except Exception as e:
            st.error(f"❌ レポート生成エラー: {str(e)}")
            logger.error(f"90日間レポート生成エラー: {e}", exc_info=True)


def _generate_90day_report_html_fallback(df, target_data):
    """90日間レポートHTML生成のフォールバック関数（基本版）"""
    try:
        # データ準備
        df_copy = df.copy()
        if '病棟コード' in df_copy.columns and EXCLUDED_WARDS:
            df_copy = df_copy[~df_copy['病棟コード'].isin(EXCLUDED_WARDS)]

        if not pd.api.types.is_datetime64_any_dtype(df_copy['日付']):
            df_copy['日付'] = pd.to_datetime(df_copy['日付'], errors='coerce')
        df_copy.dropna(subset=['日付'], inplace=True)
        
        end_date = df_copy['日付'].max()
        start_date = end_date - timedelta(days=89)
        df_90days = df_copy[(df_copy['日付'] >= start_date) & (df_copy['日付'] <= end_date)].copy()
        
        if df_90days.empty:
            return None

        # 基本的なHTMLレポート生成
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>90日間総合レポート</title>
    <style>
        body {{ font-family: 'Noto Sans JP', sans-serif; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
        h1 {{ color: #293a27; text-align: center; }}
        .summary {{ background: #f0f0f0; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 10px; border: 1px solid #ddd; text-align: center; }}
        th {{ background: #667eea; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🏥 90日間総合レポート</h1>
        <p style="text-align:center;">期間: {start_date.strftime('%Y年%m月%d日')} ～ {end_date.strftime('%Y年%m月%d日')}</p>
        
        <div class="summary">
            <h2>概要</h2>
            <p>レコード数: {len(df_90days):,}件</p>
            <p>診療科数: {df_90days['診療科名'].nunique() if '診療科名' in df_90days.columns else 0}科</p>
            <p>病棟数: {df_90days['病棟コード'].nunique() if '病棟コード' in df_90days.columns else 0}棟</p>
        </div>
        
        <p style="text-align:center; margin-top:50px;">
            <em>詳細な分析グラフとテーブルは、完全版のレポート機能をご利用ください。</em>
        </p>
    </div>
</body>
</html>"""
        
        return html_content
        
    except Exception as e:
        logger.error(f"90日間レポート生成エラー（フォールバック）: {e}")
        return None




def _execute_publish(publisher, selected_publish, selected_period, content_customizer):
    """公開処理の実行"""
    with st.spinner("公開処理を実行中..."):
        success_count = 0
        error_messages = []
        
        try:
            df = st.session_state.get('df')
            target_data = st.session_state.get('target_data', pd.DataFrame())
            
            # ダッシュボード情報の収集
            dashboards_info = []
            
            # 診療科別ダッシュボード
            if "診療科別ダッシュボード" in selected_publish and df is not None:
                html_content = generate_performance_dashboard_html(
                    df, target_data, selected_period, "department"
                )
                if html_content:
                    success, msg = publisher.upload_html_file(
                        html_content,
                        "docs/department_dashboard.html"
                    )
                    if success:
                        dashboards_info.append({
                            "title": "診療科別パフォーマンス",
                            "description": f"実績と目標達成率（{selected_period}）",
                            "file": "department_dashboard.html",
                            "update_time": datetime.now().strftime('%Y/%m/%d %H:%M')
                        })
                        success_count += 1
                    else:
                        error_messages.append(f"診療科別: {msg}")
            
            # 病棟別ダッシュボード
            if "病棟別ダッシュボード" in selected_publish and df is not None:
                html_content = generate_performance_dashboard_html(
                    df, target_data, selected_period, "ward"
                )
                if html_content:
                    success, msg = publisher.upload_html_file(
                        html_content,
                        "docs/ward_dashboard.html"
                    )
                    if success:
                        dashboards_info.append({
                            "title": "病棟別パフォーマンス",
                            "description": f"実績と目標達成率（{selected_period}）",
                            "file": "ward_dashboard.html",
                            "update_time": datetime.now().strftime('%Y/%m/%d %H:%M')
                        })
                        success_count += 1
                    else:
                        error_messages.append(f"病棟別: {msg}")

            # 90日間総合レポート（追加）
            if "90日間総合レポート" in selected_publish and df is not None:
                html_report = generate_90day_report_html(df, target_data)
                if html_report:
                    success, msg = publisher.upload_html_file(
                        html_report,
                        "docs/comprehensive_report_90days.html",
                        f"Update 90-day report - {datetime.now().strftime('%Y-%m-%d')}"
                    )
                    if success:
                        # 外部ダッシュボードリストに追加
                        external_dashboards = st.session_state.get('external_dashboards', [])
                        report_info = {
                            "title": "90日間総合レポート",
                            "description": "全体・診療科別・病棟別の詳細分析",
                            "file": "comprehensive_report_90days.html",
                            "type": "external",
                            "update_time": datetime.now().strftime('%Y/%m/%d %H:%M')
                        }
                        
                        # 既存の場合は更新
                        updated = False
                        for i, dash in enumerate(external_dashboards):
                            if dash.get('title') == "90日間総合レポート":
                                external_dashboards[i] = report_info
                                updated = True
                                break
                        if not updated:
                            external_dashboards.append(report_info)
                        
                        st.session_state.external_dashboards = external_dashboards
                        success_count += 1
                    else:
                        error_messages.append(f"90日間レポート: {msg}")

            # トップページ
            if "トップページ" in selected_publish:
                external_dashboards = st.session_state.get('external_dashboards', [])
                index_html = publisher.create_index_page(
                    dashboards_info,
                    content_customizer.get_current_config(),
                    external_dashboards
                )
                success, msg = publisher.upload_html_file(
                    index_html,
                    "docs/index.html"
                )
                if success:
                    success_count += 1
                else:
                    error_messages.append(f"トップページ: {msg}")
            
            # 結果表示
            if success_count > 0:
                st.sidebar.success(f"✅ {success_count}件の公開に成功しました")
            
            if error_messages:
                for error in error_messages:
                    st.sidebar.error(f"❌ {error}")
                    
        except Exception as e:
            st.sidebar.error(f"❌ 公開処理エラー: {str(e)}")
            logger.error(f"公開処理エラー: {e}", exc_info=True)