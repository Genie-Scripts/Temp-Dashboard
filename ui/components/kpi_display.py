import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

def display_kpi_metrics(kpi_summary: Dict[str, Any]) -> None:
    """KPIメトリクスを表示"""
    try:
        if not kpi_summary:
            st.info("📊 KPIデータがありません")
            return
        
        # メトリクス表示用の列を作成
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            _display_metric(
                "📊 4週平均",
                kpi_summary.get('4週平均', 0),
                kpi_summary.get('4週平均_変化', 0),
                "件/週"
            )
        
        with col2:
            _display_metric(
                "📈 直近週実績",
                kpi_summary.get('直近週実績', 0),
                kpi_summary.get('直近週_変化', 0),
                "件"
            )
        
        with col3:
            _display_metric(
                "🎯 目標達成率",
                kpi_summary.get('目標達成率', 0),
                kpi_summary.get('達成率_変化', 0),
                "%"
            )
        
        with col4:
            _display_metric(
                "📅 分析期間",
                kpi_summary.get('分析日数', 0),
                None,
                "日"
            )
            
    except Exception as e:
        logger.error(f"KPI表示エラー: {e}")
        st.error("KPI表示中にエラーが発生しました")

def _display_metric(
    label: str, 
    value: float, 
    delta: Optional[float] = None,
    unit: str = ""
) -> None:
    """個別メトリクスを表示"""
    try:
        # 値のフォーマット
        if unit == "%":
            formatted_value = f"{value:.1f}%"
            formatted_delta = f"{delta:+.1f}%" if delta is not None else None
        else:
            formatted_value = f"{value:.1f}{unit}"
            formatted_delta = f"{delta:+.1f}" if delta is not None else None
        
        st.metric(
            label=label,
            value=formatted_value,
            delta=formatted_delta
        )
    except Exception as e:
        logger.error(f"メトリクス表示エラー {label}: {e}")
        st.metric(label=label, value="エラー")

def display_kpi_details(kpi_data: pd.DataFrame, title: str = "KPI詳細") -> None:
    """KPI詳細データをテーブルで表示"""
    try:
        if kpi_data.empty:
            st.info("表示するKPIデータがありません")
            return
        
        with st.expander(f"📊 {title}"):
            st.dataframe(
                kpi_data,
                use_container_width=True,
                hide_index=True
            )
    except Exception as e:
        logger.error(f"KPI詳細表示エラー: {e}")
        st.error("KPI詳細表示中にエラーが発生しました")

def create_kpi_card(
    title: str,
    value: float,
    target: Optional[float] = None,
    icon: str = "📊",
    color: str = "blue"
) -> None:
    """KPIカードを作成"""
    try:
        achievement_rate = (value / target * 100) if target and target > 0 else None
        
        # 色の決定
        if achievement_rate is not None:
            if achievement_rate >= 100:
                color = "green"
            elif achievement_rate >= 80:
                color = "orange" 
            else:
                color = "red"
        
        # カード表示
        with st.container():
            col1, col2 = st.columns([1, 4])
            
            with col1:
                st.markdown(f"<h2 style='text-align: center;'>{icon}</h2>", unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"**{title}**")
                st.markdown(f"<h3 style='color: {color};'>{value:.1f}</h3>", unsafe_allow_html=True)
                
                if target is not None:
                    st.caption(f"目標: {target:.1f} (達成率: {achievement_rate:.1f}%)")
    except Exception as e:
        logger.error(f"KPIカード作成エラー: {e}")
        st.error("KPIカード表示中にエラーが発生しました")

def display_kpi_trend(
    trend_data: pd.DataFrame,
    metric_name: str,
    chart_type: str = "line"
) -> None:
    """KPIトレンドを表示"""
    try:
        if trend_data.empty:
            st.info(f"{metric_name}のトレンドデータがありません")
            return
        
        st.subheader(f"📈 {metric_name} トレンド")
        
        if chart_type == "line":
            st.line_chart(trend_data)
        elif chart_type == "bar":
            st.bar_chart(trend_data)
        else:
            st.dataframe(trend_data)
    except Exception as e:
        logger.error(f"KPIトレンド表示エラー: {e}")
        st.error("KPIトレンド表示中にエラーが発生しました")