# utils/date_helpers.py (jpholidayフォールバック対応版)
import pandas as pd
from datetime import datetime, date
import warnings

# jpholidayのインポートを安全に行う
try:
    import jpholiday
    JPHOLIDAY_AVAILABLE = True
except ImportError:
    JPHOLIDAY_AVAILABLE = False
    warnings.warn("jpholiday が利用できません。平日判定は土日のみで行います。", UserWarning)

def is_weekday(date_input):
    """
    平日かどうかを判定する（祝日を考慮）
    
    Args:
        date_input: datetime, date, or str
        
    Returns:
        bool: 平日の場合True
    """
    if isinstance(date_input, str):
        date_obj = pd.to_datetime(date_input).date()
    elif isinstance(date_input, datetime):
        date_obj = date_input.date()
    elif isinstance(date_input, date):
        date_obj = date_input
    else:
        try:
            date_obj = pd.to_datetime(date_input).date()
        except:
            return False
    
    # 土日の場合は平日ではない
    if date_obj.weekday() >= 5:  # 5=土曜, 6=日曜
        return False
    
    # jpholidayが利用可能な場合は祝日もチェック
    if JPHOLIDAY_AVAILABLE:
        return not jpholiday.is_holiday(date_obj)
    else:
        # jpholidayが利用できない場合は土日のみで判定
        return True

def is_holiday(date_input):
    """
    祝日かどうかを判定する
    
    Args:
        date_input: datetime, date, or str
        
    Returns:
        bool: 祝日の場合True
    """
    if isinstance(date_input, str):
        date_obj = pd.to_datetime(date_input).date()
    elif isinstance(date_input, datetime):
        date_obj = date_input.date()
    elif isinstance(date_input, date):
        date_obj = date_input
    else:
        try:
            date_obj = pd.to_datetime(date_input).date()
        except:
            return False
    
    if JPHOLIDAY_AVAILABLE:
        return jpholiday.is_holiday(date_obj)
    else:
        # jpholidayが利用できない場合は主要な祝日のみ手動で定義
        return is_major_holiday(date_obj)

def is_major_holiday(date_obj):
    """
    主要な祝日を手動で判定（jpholidayのフォールバック）
    
    Args:
        date_obj: date object
        
    Returns:
        bool: 主要祝日の場合True
    """
    month = date_obj.month
    day = date_obj.day
    year = date_obj.year
    
    # 固定祝日
    fixed_holidays = [
        (1, 1),   # 元旦
        (2, 11),  # 建国記念の日
        (4, 29),  # 昭和の日
        (5, 3),   # 憲法記念日
        (5, 4),   # みどりの日
        (5, 5),   # こどもの日
        (8, 11),  # 山の日
        (11, 3),  # 文化の日
        (11, 23), # 勤労感謝の日
        (12, 23), # 天皇誕生日（2019年以降）
    ]
    
    if (month, day) in fixed_holidays:
        return True
    
    # 年末年始
    if (month == 12 and day >= 29) or (month == 1 and day <= 3):
        return True
    
    # ゴールデンウィーク期間の追加考慮
    if month == 5 and 1 <= day <= 5:
        return True
    
    return False

def get_fiscal_year(date_input):
    """
    会計年度を取得する（4月始まり）
    
    Args:
        date_input: datetime, date, or str
        
    Returns:
        int: 会計年度
    """
    if isinstance(date_input, str):
        date_obj = pd.to_datetime(date_input)
    elif isinstance(date_input, datetime):
        date_obj = date_input
    else:
        date_obj = pd.to_datetime(date_input)
    
    if date_obj.month >= 4:
        return date_obj.year
    else:
        return date_obj.year - 1

def filter_by_period(df, latest_date, period):
    """
    期間でデータフィルタリング
    
    Args:
        df: DataFrame
        latest_date: 最新日付
        period: 期間（"直近30日", "直近90日", "今年度", "去年度"）
        
    Returns:
        DataFrame: フィルタリング後のデータ
    """
    if df.empty or latest_date is None:
        return df
    
    date_col = None
    for col in ['手術実施日_dt', '日付', 'date']:
        if col in df.columns:
            date_col = col
            break
    
    if date_col is None:
        return df
    
    if period == "直近30日":
        start_date = latest_date - pd.Timedelta(days=29)
        return df[df[date_col] >= start_date]
    elif period == "直近90日":
        start_date = latest_date - pd.Timedelta(days=89)
        return df[df[date_col] >= start_date]
    elif period == "今年度":
        fiscal_year = get_fiscal_year(latest_date)
        start_date = pd.Timestamp(fiscal_year, 4, 1)
        end_date = pd.Timestamp(fiscal_year + 1, 3, 31)
        return df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]
    elif period == "去年度":
        fiscal_year = get_fiscal_year(latest_date) - 1
        start_date = pd.Timestamp(fiscal_year, 4, 1)
        end_date = pd.Timestamp(fiscal_year + 1, 3, 31)
        return df[(df[date_col] >= start_date) & (df[date_col] <= end_date)]
    else:
        return df

def add_date_features(df, date_col='手術実施日_dt'):
    """
    日付関連の特徴量を追加
    
    Args:
        df: DataFrame
        date_col: 日付列名
        
    Returns:
        DataFrame: 特徴量追加後のデータ
    """
    if date_col not in df.columns:
        return df
    
    df = df.copy()
    
    # 基本的な日付特徴量
    df['year'] = df[date_col].dt.year
    df['month'] = df[date_col].dt.month
    df['day'] = df[date_col].dt.day
    df['weekday'] = df[date_col].dt.weekday  # 0=月曜, 6=日曜
    df['quarter'] = df[date_col].dt.quarter
    
    # 平日・休日判定
    df['is_weekday'] = df[date_col].apply(is_weekday)
    df['is_holiday'] = df[date_col].apply(is_holiday)
    
    # 週の開始日（月曜日）
    df['week_start'] = df[date_col].dt.to_period('W-MON').dt.start_time
    
    # 月の開始日
    df['month_start'] = df[date_col].dt.to_period('M').dt.start_time
    
    # 会計年度
    df['fiscal_year'] = df[date_col].apply(get_fiscal_year)
    
    return df

def get_weekday_name_ja(weekday_num):
    """
    曜日番号を日本語の曜日名に変換
    
    Args:
        weekday_num: 曜日番号（0=月曜, 6=日曜）
        
    Returns:
        str: 日本語の曜日名
    """
    weekday_names = ['月', '火', '水', '木', '金', '土', '日']
    if 0 <= weekday_num <= 6:
        return weekday_names[weekday_num]
    else:
        return 'unknown'

def format_date_range(start_date, end_date):
    """
    日付範囲を読みやすい形式でフォーマット
    
    Args:
        start_date: 開始日
        end_date: 終了日
        
    Returns:
        str: フォーマット済み日付範囲
    """
    if pd.isna(start_date) or pd.isna(end_date):
        return "日付範囲不明"
    
    start_str = pd.to_datetime(start_date).strftime('%Y/%m/%d')
    end_str = pd.to_datetime(end_date).strftime('%Y/%m/%d')
    
    return f"{start_str} ～ {end_str}"

# モジュール読み込み時に状態を報告
if not JPHOLIDAY_AVAILABLE:
    print("⚠️ jpholiday が利用できません。祝日判定は主要祝日のみで行います。")
    print("完全な祝日対応には 'pip install jpholiday' を実行してください。")