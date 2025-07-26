# analysis/periodic.py
import pandas as pd
import numpy as np
from utils import date_helpers
import calendar

def get_monthly_summary(df, department=None):
    """月単位でのサマリーを計算する"""
    if df.empty:
        return pd.DataFrame()

    target_df = df[df['is_gas_20min']].copy()
    if department:
        target_df = target_df[target_df['実施診療科'] == department]

    if target_df.empty:
        return pd.DataFrame()

    # 月ごとの集計
    monthly_counts = target_df.groupby('month_start').size().reset_index(name='月合計件数')
    weekday_df = target_df[target_df['is_weekday']]
    if not weekday_df.empty:
        monthly_weekday_counts = weekday_df.groupby('month_start').size().reset_index(name='平日件数')
        summary = pd.merge(monthly_counts, monthly_weekday_counts, on='month_start', how='left')
    else:
        summary = monthly_counts
        summary['平日件数'] = 0
    
    summary.fillna(0, inplace=True)
    
    # 月ごとの平日日数を計算
    def get_weekdays(month_start):
        year, month = month_start.year, month_start.month
        _, last_day = calendar.monthrange(year, month)
        all_days = pd.date_range(start=month_start, end=pd.Timestamp(year, month, last_day))
        return sum(date_helpers.is_weekday(day) for day in all_days)

    summary['平日日数'] = summary['month_start'].apply(get_weekdays)
    summary['平日1日平均件数'] = np.where(summary['平日日数'] > 0, summary['平日件数'] / summary['平日日数'], 0).round(1)

    return summary.rename(columns={'month_start': '月'})[['月', '月合計件数', '平日件数', '平日日数', '平日1日平均件数']]


def get_quarterly_summary(df, department=None):
    """四半期単位でのサマリーを計算する"""
    if df.empty:
        return pd.DataFrame()

    target_df = df[df['is_gas_20min']].copy()
    if department:
        target_df = target_df[target_df['実施診療科'] == department]
    
    if target_df.empty:
        return pd.DataFrame()

    target_df['quarter_start'] = target_df['手術実施日_dt'].dt.to_period('Q').apply(lambda r: r.start_time)
    
    quarterly_counts = target_df.groupby('quarter_start').size().reset_index(name='四半期合計件数')
    weekday_df = target_df[target_df['is_weekday']]
    if not weekday_df.empty:
        quarterly_weekday_counts = weekday_df.groupby('quarter_start').size().reset_index(name='平日件数')
        summary = pd.merge(quarterly_counts, quarterly_weekday_counts, on='quarter_start', how='left')
    else:
        summary = quarterly_counts
        summary['平日件数'] = 0

    summary.fillna(0, inplace=True)

    def get_weekdays_in_quarter(quarter_start):
        start_date = quarter_start
        end_date = quarter_start + pd.DateOffset(months=3) - pd.DateOffset(days=1)
        return sum(date_helpers.is_weekday(day) for day in pd.date_range(start_date, end_date))

    summary['平日日数'] = summary['quarter_start'].apply(get_weekdays_in_quarter)
    summary['平日1日平均件数'] = np.where(summary['平日日数'] > 0, summary['平日件数'] / summary['平日日数'], 0).round(1)
    summary['四半期ラベル'] = summary['quarter_start'].apply(lambda d: f"{d.year}年Q{(d.month-1)//3+1}")

    return summary.rename(columns={'quarter_start': '四半期'})[['四半期', '四半期ラベル', '四半期合計件数', '平日件数', '平日日数', '平日1日平均件数']]