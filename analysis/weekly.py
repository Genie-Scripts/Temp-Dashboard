# analysis/weekly.py (修正版)
import pandas as pd
import numpy as np

def get_analysis_end_date(latest_date):
    """分析の最終日（最新の完全な週の最終日曜日）を計算する"""
    if pd.isna(latest_date):
        return None
    # 最新データが日曜日の場合、その日を返す
    if latest_date.dayofweek == 6:
        return latest_date
    # 月曜〜土曜の場合、その前の日曜日を返す
    else:
        return latest_date - pd.to_timedelta(latest_date.dayofweek + 1, unit='d')

def get_summary(df, department=None, use_complete_weeks=True):
    """
    週単位でのサマリーを計算する。
    """
    if df.empty:
        return pd.DataFrame()

    target_df = df[df['is_gas_20min']].copy()

    if department:
        target_df = target_df[target_df['実施診療科'] == department]

    if use_complete_weeks:
        latest_date = df['手術実施日_dt'].max()
        analysis_end_date = get_analysis_end_date(latest_date)
        if analysis_end_date:
            target_df = target_df[target_df['手術実施日_dt'] <= analysis_end_date]
    
    if target_df.empty:
        return pd.DataFrame()

    weekly_counts = target_df.groupby('week_start').size().reset_index(name='週合計件数')
    
    weekday_df = target_df[target_df['is_weekday']]
    if not weekday_df.empty:
        weekly_weekday_counts = weekday_df.groupby('week_start').size().reset_index(name='平日件数')
        actual_weekdays = weekday_df.groupby('week_start')['手術実施日_dt'].nunique().reset_index(name='実データ平日数')
        summary = pd.merge(weekly_counts, weekly_weekday_counts, on='week_start', how='left')
        summary = pd.merge(summary, actual_weekdays, on='week_start', how='left')
    else:
        summary = weekly_counts
        summary['平日件数'] = 0
        summary['実データ平日数'] = 0

    summary.fillna(0, inplace=True)
    summary[['平日件数', '実データ平日数']] = summary[['平日件数', '実データ平日数']].astype(int)

    summary['平日1日平均件数'] = np.where(
        summary['実データ平日数'] > 0,
        summary['平日件数'] / summary['実データ平日数'],
        0
    ).round(1)

    return summary.rename(columns={'week_start': '週'})[['週', '週合計件数', '平日件数', '実データ平日数', '平日1日平均件数']]