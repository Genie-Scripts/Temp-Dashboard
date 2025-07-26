# reporting/csv_exporter.py
import streamlit as st
from datetime import datetime

def render_download_button(df, data_type, period_type, department=None):
    """
    分析結果のデータフレームをCSVファイルとしてダウンロードするボタンを表示する
    """
    if df.empty:
        st.warning("ダウンロード可能なデータがありません。")
        return

    now = datetime.now().strftime("%Y%m%d")
    dept_label = f"_{department}" if department else ""
    filename = f"{now}_{data_type}{dept_label}_{period_type}.csv"

    st.download_button(
        label="📥 CSVでダウンロード",
        data=df.to_csv(index=False).encode('utf-8-sig'),
        file_name=filename,
        mime='text/csv',
        help=f"{filename} をダウンロードします。"
    )