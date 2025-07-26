# data_processing/loader.py
import pandas as pd
import streamlit as st
from utils import date_helpers

@st.cache_data(ttl=3600)
def preprocess_dataframe(df):
    """
    データフレームに対して、アプリケーションで必要な前処理を一度にすべて実行する。
    この関数はキャッシュされ、同じデータフレームに対しては再実行されない。
    """
    if df.empty:
        return df

    df = df.copy()

    # 1. 日付列の変換と不正値の削除
    if '手術実施日_dt' not in df.columns and '手術実施日' in df.columns:
        df['手術実施日_dt'] = pd.to_datetime(df['手術実施日'], errors='coerce')
    df.dropna(subset=['手術実施日_dt'], inplace=True)

    # 2. 重複レコードの削除
    id_cols = ["手術実施日", "実施診療科", "実施手術室", "入室時刻"]
    if all(col in df.columns for col in id_cols):
        # 結合前に各列を文字列に変換
        df['unique_op_id'] = df[id_cols].astype(str).agg('_'.join, axis=1)
        df.drop_duplicates(subset='unique_op_id', keep='last', inplace=True)
        df.drop(columns='unique_op_id', inplace=True)

    # 3. 頻繁に使用するフラグや列を事前計算
    if '麻酔種別' in df.columns:
        df['is_gas_20min'] = (
            df['麻酔種別'].str.contains("全身麻酔", na=False) &
            df['麻酔種別'].str.contains("20分以上", na=False)
        )
    else:
        df['is_gas_20min'] = False

    df['is_weekday'] = df['手術実施日_dt'].apply(date_helpers.is_weekday)
    df['fiscal_year'] = df['手術実施日_dt'].apply(date_helpers.get_fiscal_year)
    df['month_start'] = df['手術実施日_dt'].dt.to_period('M').apply(lambda r: r.start_time)
    df['week_start'] = (df['手術実施日_dt'] - pd.to_timedelta(df['手術実施日_dt'].dt.dayofweek, unit='d')).dt.normalize()

    return df

def _load_single_file(uploaded_file):
    """単一のCSVファイルを読み込む内部関数"""
    encodings = ['cp932', 'utf-8-sig', 'utf-8', 'shift-jis', 'euc-jp']
    for encoding in encodings:
        try:
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, encoding=encoding, low_memory=False)
            df.columns = df.columns.str.strip()
            # object型の列の空白のみ除去
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].str.strip()
            return df
        except Exception:
            continue
    raise ValueError(f"ファイル '{uploaded_file.name}' の読み込みに失敗しました。")


def load_and_merge_files(base_file, update_files):
    """
    基礎データと更新データを読み込み、前処理して結合する。
    """
    if not base_file:
        return pd.DataFrame()

    df_base = _load_single_file(base_file)

    update_dfs = []
    if update_files:
        for f in update_files:
            try:
                update_dfs.append(_load_single_file(f))
            except ValueError as e:
                st.warning(e)

    # 全データを結合してから一度だけ前処理を実行
    combined_df = pd.concat([df_base] + update_dfs, ignore_index=True)
    processed_df = preprocess_dataframe(combined_df)
    processed_df.sort_values(by="手術実施日_dt", inplace=True)

    return processed_df.reset_index(drop=True)