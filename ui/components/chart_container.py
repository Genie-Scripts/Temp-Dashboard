import streamlit as st
import pandas as pd
from contextlib import contextmanager
from typing import Optional, Dict, Any, Callable
import logging

logger = logging.getLogger(__name__)

@contextmanager
def create_chart_container(
    height: Optional[int] = None,
    border: bool = True,
    padding: bool = True
):
    """チャート用のコンテナを作成"""
    try:
        container_style = ""
        if border:
            container_style += "border: 1px solid #ddd; border-radius: 5px;"
        if padding:
            container_style += "padding: 10px;"
        if height:
            container_style += f"height: {height}px;"
        
        if container_style:
            with st.container():
                st.markdown(f'<div style="{container_style}">', unsafe_allow_html=True)
                yield
                st.markdown('</div>', unsafe_allow_html=True)
        else:
            with st.container():
                yield
    except Exception as e:
        logger.error(f"チャートコンテナ作成エラー: {e}")
        with st.container():
            yield

def create_chart_header(
    title: str,
    subtitle: Optional[str] = None,
    help_text: Optional[str] = None
) -> None:
    """チャートヘッダーを作成"""
    try:
        col1, col2 = st.columns([4, 1])
        
        with col1:
            st.subheader(title)
            if subtitle:
                st.caption(subtitle)
        
        with col2:
            if help_text:
                st.help(help_text)
    except Exception as e:
        logger.error(f"チャートヘッダー作成エラー: {e}")
        st.subheader(title)

def display_chart_with_controls(
    chart_func: Callable,
    chart_data: Any,
    controls_config: Optional[Dict[str, Any]] = None,
    **chart_kwargs
):
    """コントロール付きでチャートを表示"""
    try:
        if controls_config:
            # コントロール部分
            with st.expander("📊 チャート設定", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                # 各種コントロールの実装
                # （実際のコントロールは具体的な要件に応じて実装）
        
        # チャート表示
        with create_chart_container():
            chart_func(chart_data, **chart_kwargs)
    except Exception as e:
        logger.error(f"チャート表示エラー: {e}")
        st.error("チャート表示中にエラーが発生しました")

def create_download_button(
    data: Any,
    filename: str,
    mime_type: str = "text/csv",
    label: str = "📥 ダウンロード"
) -> None:
    """ダウンロードボタンを作成"""
    try:
        st.download_button(
            label=label,
            data=data,
            file_name=filename,
            mime=mime_type
        )
    except Exception as e:
        logger.error(f"ダウンロードボタン作成エラー: {e}")
        st.error("ダウンロードボタン作成中にエラーが発生しました")

def display_chart_metrics(chart_data: pd.DataFrame, title: str = "チャート統計") -> None:
    """チャート用の統計情報を表示"""
    try:
        if chart_data.empty:
            st.info("統計情報を表示するデータがありません")
            return
        
        with st.expander(f"📊 {title}"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("データポイント数", len(chart_data))
            
            with col2:
                if len(chart_data.select_dtypes(include=['number']).columns) > 0:
                    numeric_cols = chart_data.select_dtypes(include=['number'])
                    st.metric("数値列数", len(numeric_cols.columns))
            
            with col3:
                if '手術実施日_dt' in chart_data.columns:
                    date_range = chart_data['手術実施日_dt'].agg(['min', 'max'])
                    days = (date_range['max'] - date_range['min']).days
                    st.metric("期間（日）", days)
                else:
                    st.metric("期間", "計算不可")
    except Exception as e:
        logger.error(f"チャート統計表示エラー: {e}")
        st.error("チャート統計表示中にエラーが発生しました")