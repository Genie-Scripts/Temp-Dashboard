# analysis/surgeon.py
import pandas as pd
import streamlit as st

@st.cache_data(ttl=3600)
def get_expanded_surgeon_df(df):
    """
    術者列を改行で分割し、行を展開する。この処理は重いためキャッシュする。
    """
    if '実施術者' not in df.columns or df['実施術者'].isnull().all():
        return pd.DataFrame()

    # 複数術者を含む行のみを対象に処理を高速化
    df_copy = df.copy()
    df_copy['実施術者'] = df_copy['実施術者'].astype(str)
    
    # 改行コードで分割し、リストに変換
    s = df_copy['実施術者'].str.split(r'\n|\r\n').apply(
        lambda x: [name.strip() for name in x if name.strip()] if isinstance(x, list) else []
    )
    
    # 空のリストをNaNに置き換え
    s = s[s.str.len() > 0]
    
    # explodeで行を展開
    expanded = df_copy.loc[s.index].assign(実施術者=s).explode('実施術者')
    
    return expanded

def get_surgeon_summary(df):
    """
    術者ごとの手術件数を集計する。

    :param df: 展開済みの術者DataFrame
    :return: 術者ごとの集計結果
    """
    if df.empty or '実施術者' not in df.columns:
        return pd.DataFrame()

    summary = df.groupby('実施術者').size().reset_index(name='件数')
    summary = summary.sort_values('件数', ascending=False).reset_index(drop=True)
    return summary