import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)

def display_dataframe(
    df: pd.DataFrame,
    title: Optional[str] = None,
    height: Optional[int] = None,
    use_container_width: bool = True,
    hide_index: bool = True,
    column_config: Optional[Dict[str, Any]] = None
) -> None:
    """データフレームを表示"""
    try:
        if title:
            st.subheader(title)
        
        if df.empty:
            st.info("表示するデータがありません")
            return
        
        st.dataframe(
            df,
            height=height,
            use_container_width=use_container_width,
            hide_index=hide_index,
            column_config=column_config
        )
    except Exception as e:
        logger.error(f"データフレーム表示エラー: {e}")
        st.error("データ表示中にエラーが発生しました")

def display_summary_table(
    df: pd.DataFrame,
    title: str = "データサマリー",
    include_dtypes: bool = True
) -> None:
    """データサマリーテーブルを表示"""
    try:
        if df.empty:
            st.info("サマリーを生成するデータがありません")
            return
        
        with st.expander(f"📊 {title}", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**基本情報**")
                basic_info = pd.DataFrame({
                    '項目': ['行数', '列数', 'メモリ使用量'],
                    '値': [
                        f"{len(df):,}",
                        f"{len(df.columns)}",
                        f"{df.memory_usage(deep=True).sum() / 1024 / 1024:.2f} MB"
                    ]
                })
                st.dataframe(basic_info, hide_index=True)
            
            with col2:
                st.write("**欠損値情報**")
                missing_info = df.isnull().sum()
                missing_df = pd.DataFrame({
                    '列名': missing_info.index,
                    '欠損数': missing_info.values,
                    '欠損率(%)': (missing_info.values / len(df) * 100).round(2)
                })
                missing_df = missing_df[missing_df['欠損数'] > 0]
                
                if missing_df.empty:
                    st.info("欠損値はありません")
                else:
                    st.dataframe(missing_df, hide_index=True)
            
            if include_dtypes:
                st.write("**データ型情報**")
                dtype_info = pd.DataFrame({
                    '列名': df.columns,
                    'データ型': df.dtypes.astype(str),
                    'ユニーク数': [df[col].nunique() for col in df.columns]
                })
                st.dataframe(dtype_info, hide_index=True)
    except Exception as e:
        logger.error(f"サマリーテーブル表示エラー: {e}")
        st.error("サマリー表示中にエラーが発生しました")

def display_paginated_table(
    df: pd.DataFrame,
    title: Optional[str] = None,
    page_size: int = 20,
    search_columns: Optional[List[str]] = None
) -> None:
    """ページネーション付きテーブルを表示"""
    try:
        if title:
            st.subheader(title)
        
        if df.empty:
            st.info("表示するデータがありません")
            return
        
        # 検索機能
        filtered_df = df.copy()
        if search_columns:
            search_term = st.text_input(
                "🔍 検索",
                placeholder=f"検索対象列: {', '.join(search_columns)}"
            )
            
            if search_term:
                mask = pd.Series(False, index=df.index)
                for col in search_columns:
                    if col in df.columns:
                        mask |= df[col].astype(str).str.contains(search_term, case=False, na=False)
                filtered_df = df[mask]
        
        # ページネーション
        total_rows = len(filtered_df)
        total_pages = (total_rows - 1) // page_size + 1 if total_rows > 0 else 1
        
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                page = st.selectbox(
                    "ページ",
                    range(1, total_pages + 1),
                    format_func=lambda x: f"ページ {x} / {total_pages}"
                )
            
            start_idx = (page - 1) * page_size
            end_idx = min(start_idx + page_size, total_rows)
            display_df = filtered_df.iloc[start_idx:end_idx]
            
            st.caption(f"表示中: {start_idx + 1}-{end_idx} / {total_rows}件")
        else:
            display_df = filtered_df
        
        # テーブル表示
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    except Exception as e:
        logger.error(f"ページネーションテーブル表示エラー: {e}")
        st.error("テーブル表示中にエラーが発生しました")

def display_interactive_table(
    df: pd.DataFrame,
    title: Optional[str] = None,
    sortable_columns: Optional[List[str]] = None,
    filterable_columns: Optional[Dict[str, List[str]]] = None
) -> pd.DataFrame:
    """インタラクティブテーブルを表示"""
    try:
        if title:
            st.subheader(title)
        
        if df.empty:
            st.info("表示するデータがありません")
            return df
        
        filtered_df = df.copy()
        
        # フィルタリング機能
        if filterable_columns:
            with st.expander("🔧 フィルタ設定"):
                for col, options in filterable_columns.items():
                    if col in df.columns:
                        selected_values = st.multiselect(
                            f"{col} でフィルタ",
                            options=options,
                            default=options
                        )
                        if selected_values:
                            filtered_df = filtered_df[filtered_df[col].isin(selected_values)]
        
        # ソート機能
        if sortable_columns:
            col1, col2 = st.columns(2)
            with col1:
                sort_column = st.selectbox(
                    "ソート列",
                    options=["なし"] + [col for col in sortable_columns if col in df.columns]
                )
            
            with col2:
                if sort_column != "なし":
                    sort_ascending = st.radio(
                        "ソート順",
                        ["昇順", "降順"],
                        horizontal=True
                    ) == "昇順"
                    
                    filtered_df = filtered_df.sort_values(
                        by=sort_column,
                        ascending=sort_ascending
                    )
        
        # テーブル表示
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
        
        # 統計情報表示
        if len(filtered_df) != len(df):
            st.caption(f"フィルタ結果: {len(filtered_df):,}件 / 全体: {len(df):,}件")
        
        return filtered_df
    except Exception as e:
        logger.error(f"インタラクティブテーブル表示エラー: {e}")
        st.error("テーブル表示中にエラーが発生しました")
        return df

def create_download_csv_button(
    df: pd.DataFrame,
    filename: str = "data.csv",
    label: str = "📥 CSVダウンロード"
) -> None:
    """CSVダウンロードボタンを作成"""
    try:
        if df.empty:
            st.info("ダウンロードするデータがありません")
            return
        
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button(
            label=label,
            data=csv_data,
            file_name=filename,
            mime="text/csv"
        )
    except Exception as e:
        logger.error(f"CSVダウンロードボタン作成エラー: {e}")
        st.error("ダウンロードボタン作成中にエラーが発生しました")

def display_comparison_table(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    title1: str = "テーブル1",
    title2: str = "テーブル2",
    highlight_differences: bool = True
) -> None:
    """2つのデータフレームを比較表示"""
    try:
        st.subheader("📊 データ比較")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**{title1}**")
            if df1.empty:
                st.info("データがありません")
            else:
                st.dataframe(df1, use_container_width=True, hide_index=True)
                st.caption(f"行数: {len(df1):,}, 列数: {len(df1.columns)}")
        
        with col2:
            st.write(f"**{title2}**")
            if df2.empty:
                st.info("データがありません")
            else:
                st.dataframe(df2, use_container_width=True, hide_index=True)
                st.caption(f"行数: {len(df2):,}, 列数: {len(df2.columns)}")
        
        # 差分情報
        if not df1.empty and not df2.empty and highlight_differences:
            st.subheader("🔍 差分情報")
            
            diff_info = {
                "項目": ["行数の差", "列数の差"],
                "値": [
                    f"{len(df2) - len(df1):+,}",
                    f"{len(df2.columns) - len(df1.columns):+}"
                ]
            }
            
            diff_df = pd.DataFrame(diff_info)
            st.dataframe(diff_df, hide_index=True)
    except Exception as e:
        logger.error(f"比較テーブル表示エラー: {e}")
        st.error("比較テーブル表示中にエラーが発生しました")
