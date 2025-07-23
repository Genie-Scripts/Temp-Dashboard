# utils.py - 共通ユーティリティ関数
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar
import re # 病棟コードのパターンマッチング用
import logging # ロギング用に追加

logger = logging.getLogger(__name__) # ロガーのセットアップ

# --- 診療科マッピング関連関数 ---
def create_dept_mapping_table(target_data_df=None):
    """
    目標データと共通設定から診療科マッピングテーブルを作成する
    """
    # 引数が渡されていない場合はセッションステートから取得
    if target_data_df is None:
        target_data_df = st.session_state.get('target_data')

    dept_mapping = {}
    # 目標データが存在するか確認
    if target_data_df is None or target_data_df.empty or \
       '部門コード' not in target_data_df.columns or '部門名' not in target_data_df.columns:
        logger.warning("診療科マッピング: 目標値データが見つからないか、必要な列（部門コード, 部門名）がありません。")
        # 目標値ファイルがなくても特別なマッピングは適用する可能性があるため、処理を続ける
    else:
        # マッピングテーブルを作成
        for _, row in target_data_df.iterrows():
            code = str(row.get('部門コード', '')).strip()
            name = str(row.get('部門名', '')).strip()
            if code and name:  # コードと名前が両方存在する場合のみマッピング
                dept_mapping[code] = name

    # --- 特別なマッピングの読み込みと適用 ---
    # st.session_state.common_config から SPECIAL_DEPT_MAPPINGS を取得
    # common_config が存在しないか、キーがない場合は空の辞書を使用
    common_config_dict = st.session_state.get('common_config', {})
    special_mappings_from_config = common_config_dict.get('SPECIAL_DEPT_MAPPINGS', {}) #

    if special_mappings_from_config:
        dept_mapping.update(special_mappings_from_config)
        logger.info(f"config.py から {len(special_mappings_from_config)} 件の特別な診療科マッピングを適用しました。")
    else:
        logger.info("config.py に SPECIAL_DEPT_MAPPINGS の定義がないか、空です。特別なマッピングは適用されませんでした。")
    # --- ここまでが修正箇所 ---

    logger.info(f"診療科マッピングテーブル作成完了: 合計 {len(dept_mapping)}件のマッピング") #
    st.session_state.dept_mapping = dept_mapping
    st.session_state.dept_mapping_initialized = True #
    return dept_mapping

def get_display_name_for_dept(dept_code, default_name=None):
    """
    部門コードから表示用の部門名を取得する
    """
    # マッピングがまだ作成されていなければ作成
    if not st.session_state.get('dept_mapping_initialized', False):
        create_dept_mapping_table()

    dept_mapping = st.session_state.get('dept_mapping', {})
    dept_code_str = str(dept_code).strip()

    # 部門コードが直接マッピングに存在すれば対応する部門名を返す
    if dept_code_str in dept_mapping:
        return dept_mapping[dept_code_str]

    # 存在しなければデフォルト値またはコードそのものを返す
    return default_name if default_name is not None else dept_code_str

def create_dept_display_options(dept_codes, dept_mapping=None):
    """
    診療科選択用の表示オプションを作成
    """
    options = []
    option_to_code = {}

    # マッピング辞書が指定されていない場合はセッションステートから取得
    if dept_mapping is None:
        if not st.session_state.get('dept_mapping_initialized', False):
            create_dept_mapping_table() # マッピングを初期化
        dept_mapping = st.session_state.get('dept_mapping', {})

    # 実績データの診療科コードをソートして処理
    for dept_code in sorted(list(set(str(c).strip() for c in dept_codes if pd.notna(c)))):
        # 修正: dept_mapping 引数を削除
        display_name = get_display_name_for_dept(dept_code, default_name=dept_code)
        if display_name != dept_code:
            display_option = f"{dept_code}（{display_name}）"
        else:
            display_option = dept_code

        options.append(display_option)
        option_to_code[display_option] = dept_code

    return options, option_to_code

# --- 病棟マッピング関連関数 ---
def create_ward_name_mapping(df_actual_data, target_data_df=None):
    """
    病棟コードから病棟名へのマッピング辞書を作成
    目標値ファイルの情報も考慮して、より正確な表示名を目指す
    """
    ward_mapping = {}

    # 1. 目標値ファイルから病棟の正式名称を優先的に取得
    if target_data_df is not None and not target_data_df.empty and \
       all(col in target_data_df.columns for col in ['部門コード', '部門名', '部門種別']):
        # 「部門種別」が「病棟」である行をフィルタリング
        ward_rows_from_target = target_data_df[target_data_df['部門種別'].astype(str).str.strip() == '病棟']
        for _, row in ward_rows_from_target.iterrows():
            code = str(row.get('部門コード', '')).strip()
            name = str(row.get('部門名', '')).strip()
            if code and name:
                ward_mapping[code] = name
        logger.info(f"目標値ファイルから {len(ward_mapping)} 件の病棟マッピングを登録しました。")

    # 2. 実績データから病棟コードを取得し、マッピングが存在しない場合はルールベースで生成
    if df_actual_data is None or df_actual_data.empty or '病棟コード' not in df_actual_data.columns:
        if not ward_mapping: # 目標値からも実績からも何も得られなかった場合
            logger.warning("病棟マッピング: 実績データが見つからないか、「病棟コード」列がありません。")
        st.session_state.ward_mapping = ward_mapping
        st.session_state.ward_mapping_initialized = True
        return ward_mapping

    unique_ward_codes = df_actual_data['病棟コード'].unique()

    for code in unique_ward_codes:
        if pd.isna(code):
            continue
        code_str = str(code).strip()

        # 既に目標値ファイルからマッピングされていればスキップ
        if code_str in ward_mapping:
            continue

        # ルールベースでの病棟名生成
        if len(code_str) >= 3:
            try:
                floor_part = code_str[:2]
                floor_num = str(int(floor_part)) # 先頭の0を除去
                ward_letter = code_str[2:]
                generated_name = f"{floor_num}階{ward_letter}病棟"
                ward_mapping[code_str] = generated_name
            except (ValueError, IndexError):
                ward_mapping[code_str] = code_str # 変換できない場合はそのまま使用
        else:
            ward_mapping[code_str] = code_str # 3文字未満はそのまま

    logger.info(f"病棟マッピングテーブル作成完了: 合計 {len(ward_mapping)}件のマッピング")
    st.session_state.ward_mapping = ward_mapping
    st.session_state.ward_mapping_initialized = True
    return ward_mapping

def get_ward_display_name(ward_code, ward_mapping=None):
    """
    病棟コードに対応する表示名を取得
    """
    if pd.isna(ward_code):
        return str(ward_code) # NaNの場合はそのまま文字列として返す

    ward_code_str = str(ward_code).strip()

    # マッピング辞書が指定されていない場合はセッションステートから取得
    if ward_mapping is None:
        if not st.session_state.get('ward_mapping_initialized', False):
            # 実績データと目標値データを渡して初期化を試みる
            # これらがセッションに存在することが前提
            df_for_init = st.session_state.get('df')
            target_df_for_init = st.session_state.get('target_data')
            create_ward_name_mapping(df_for_init, target_df_for_init)
        ward_mapping = st.session_state.get('ward_mapping', {})

    # マッピングから病棟名を取得、なければコード自体を返す
    return ward_mapping.get(ward_code_str, ward_code_str)

def create_ward_display_options(ward_codes, ward_mapping=None):
    """
    病棟選択用の表示オプションを作成
    """
    options = []
    option_to_code = {}

    # マッピング辞書が指定されていない場合はセッションステートから取得
    if ward_mapping is None:
        if not st.session_state.get('ward_mapping_initialized', False):
            df_for_init = st.session_state.get('df')
            target_df_for_init = st.session_state.get('target_data')
            create_ward_name_mapping(df_for_init, target_df_for_init)
        ward_mapping = st.session_state.get('ward_mapping', {})

    # 実績データの病棟コードをソートして処理
    for ward_code in sorted(list(set(str(c).strip() for c in ward_codes if pd.notna(c)))): #
        ward_name = get_ward_display_name(ward_code, ward_mapping=ward_mapping) # マッピングを渡す

        # 病棟名が病棟コードと異なる場合は「コード（名前）」形式で表示
        if ward_name != ward_code:
            display_option = f"{ward_code}（{ward_name}）"
        else:
            display_option = ward_code

        options.append(display_option)
        option_to_code[display_option] = ward_code

    return options, option_to_code

# --- マッピング初期化関数 ---
def initialize_all_mappings(df_actual_data, target_data_df=None):
    """
    全てのマッピング（診療科・病棟）を初期化
    """
    logger.info("全てのマッピングの初期化を開始します。")
    try:
        # 既存のマッピングをリセットするために初期化フラグをFalseにする
        st.session_state.dept_mapping_initialized = False
        st.session_state.ward_mapping_initialized = False
        st.session_state.dept_mapping = {} # 辞書もクリア
        st.session_state.ward_mapping = {} # 辞書もクリア

        # 診療科マッピングの初期化
        create_dept_mapping_table(target_data_df) #

        # 病棟マッピングの初期化 (実績データ df_actual_data と目標値データ target_data_df を渡す)
        create_ward_name_mapping(df_actual_data, target_data_df) #

        logger.info("全てのマッピングが正常に初期化されました。") #

    except Exception as e:
        logger.error(f"マッピング初期化中にエラーが発生しました: {e}", exc_info=True) #
        # エラーが発生してもアプリケーションを継続

# --- マッピング状況確認関数 ---
def get_mapping_status():
    """
    マッピングの初期化状況を取得
    """
    return {
        'dept_mapping_initialized': st.session_state.get('dept_mapping_initialized', False), #
        'ward_mapping_initialized': st.session_state.get('ward_mapping_initialized', False), #
        'dept_mapping_count': len(st.session_state.get('dept_mapping', {})), #
        'ward_mapping_count': len(st.session_state.get('ward_mapping', {})) #
    }

# --- 日付関連ユーティリティ関数 ---
def safe_date_filter(df, start_date=None, end_date=None):
    """安全な日付フィルタリング"""
    try:
        if df is None or df.empty:
            return pd.DataFrame()

        df_result = df.copy()

        if '日付' not in df_result.columns:
            logger.warning("safe_date_filter: '日付'列がデータフレームに存在しません。")
            return df_result

        if not pd.api.types.is_datetime64_any_dtype(df_result['日付']):
            df_result['日付'] = pd.to_datetime(df_result['日付'], errors='coerce')
            nat_count = df_result['日付'].isna().sum()
            if nat_count > 0:
                logger.warning(f"safe_date_filter: '日付'列の変換でNaTが {nat_count} 件発生しました。")
                df_result = df_result.dropna(subset=['日付']) # NaT行を除外

        if start_date is not None:
            try:
                start_date_pd = pd.Timestamp(start_date).normalize()
                df_result = df_result[df_result['日付'] >= start_date_pd]
            except Exception as e_start:
                logger.error(f"safe_date_filter: 開始日の処理エラー: {e_start}")

        if end_date is not None:
            try:
                end_date_pd = pd.Timestamp(end_date).normalize()
                df_result = df_result[df_result['日付'] <= end_date_pd]
            except Exception as e_end:
                logger.error(f"safe_date_filter: 終了日の処理エラー: {e_end}")

        return df_result

    except Exception as e:
        logger.error(f"日付フィルタリング処理全体でエラー: {e}", exc_info=True)
        return df # エラー時は元のDFを返すか、空のDFを返すのが適切

def safe_date_input(
    label,
    df,
    session_key,
    default_offset_days=30,
    is_end_date=False,
    related_start_key=None
): #
    """
    安全な日付選択UI

    Returns:
    --------
    pd.Timestamp
        選択された日付（Timestamp型）
    """

    if df is None or df.empty or '日付' not in df.columns:
        logger.error(f"safe_date_input ({label}): 日付データが利用できません。")
        # フォールバックとして今日の日付を返すか、エラーを発生させる
        st.error(f"{label}: 分析データの日付列が見つかりません。")
        return pd.Timestamp(datetime.now().date()).normalize()

    # データの日付範囲を取得
    try:
        # NaTが含まれているとmin/maxでエラーになるため、dropnaする
        valid_dates = df['日付'].dropna()
        if valid_dates.empty:
            logger.error(f"safe_date_input ({label}): 有効な日付データがありません。")
            st.error(f"{label}: 有効な日付データがありません。")
            return pd.Timestamp(datetime.now().date()).normalize()
        data_min_date = valid_dates.min().date()
        data_max_date = valid_dates.max().date()
    except Exception as e:
        logger.error(f"safe_date_input ({label}): データの日付範囲取得エラー: {e}")
        st.error(f"{label}: データの日付範囲が取得できませんでした。")
        return pd.Timestamp(datetime.now().date()).normalize()


    # セッション状態から値を取得
    session_value_dt = st.session_state.get(session_key)
    if isinstance(session_value_dt, pd.Timestamp): # Timestampならdate型に
        session_value_dt = session_value_dt.date()
    elif not isinstance(session_value_dt, datetime.date): # それ以外ならNone
        session_value_dt = None

    # デフォルト値の計算
    default_value_dt = None
    if is_end_date:
        # 終了日の場合
        related_start_dt = None
        if related_start_key and related_start_key in st.session_state:
            related_start_val = st.session_state[related_start_key]
            if isinstance(related_start_val, pd.Timestamp):
                related_start_dt = related_start_val.date()
            elif isinstance(related_start_val, datetime.date):
                related_start_dt = related_start_val

        if related_start_dt:
            ideal_end_dt = related_start_dt + timedelta(days=default_offset_days)
            default_value_dt = min(ideal_end_dt, data_max_date)
        else:
            default_value_dt = data_max_date
    else:
        # 開始日の場合
        ideal_start_dt = data_max_date - timedelta(days=default_offset_days)
        default_value_dt = max(ideal_start_dt, data_min_date)

    # セッション値の安全性チェックと適用
    if session_value_dt and data_min_date <= session_value_dt <= data_max_date:
        # 終了日の場合、開始日より前にならないように調整
        if is_end_date and related_start_key:
            related_start_dt_for_check = None
            related_start_val_check = st.session_state.get(related_start_key)
            if isinstance(related_start_val_check, pd.Timestamp):
                related_start_dt_for_check = related_start_val_check.date()
            elif isinstance(related_start_val_check, datetime.date):
                 related_start_dt_for_check = related_start_val_check

            if related_start_dt_for_check and session_value_dt < related_start_dt_for_check:
                final_default_value_dt = default_value_dt # セッション値が無効なので計算したデフォルトを使う
                logger.warning(f"{label}: 保存されていた日付({session_value_dt})が開始日({related_start_dt_for_check})より前です。デフォルト値({final_default_value_dt})を使用します。")
            else:
                final_default_value_dt = session_value_dt # セッション値が有効
        else: # 開始日の場合、または終了日で関連開始キーがない場合
            final_default_value_dt = session_value_dt
    else:
        final_default_value_dt = default_value_dt
        if session_value_dt: # 範囲外だった場合
            logger.warning(f"{label}: 保存されていた日付({session_value_dt})がデータの範囲外です。デフォルト値({final_default_value_dt})を使用します。")

    # st.date_inputの最小値・最大値調整（終了日の場合）
    min_val_for_widget = data_min_date
    if is_end_date and related_start_key:
        related_start_dt_for_widget = None
        related_start_val_widget = st.session_state.get(related_start_key)
        if isinstance(related_start_val_widget, pd.Timestamp):
            related_start_dt_for_widget = related_start_val_widget.date()
        elif isinstance(related_start_val_widget, datetime.date):
            related_start_dt_for_widget = related_start_val_widget

        if related_start_dt_for_widget:
            min_val_for_widget = max(data_min_date, related_start_dt_for_widget)
            if final_default_value_dt < min_val_for_widget: # デフォルト値が最小値より小さい場合は調整
                final_default_value_dt = min_val_for_widget


    # 日付入力ウィジェット
    selected_date_dt = st.date_input(
        label,
        value=final_default_value_dt,
        min_value=min_val_for_widget,
        max_value=data_max_date,
        key=f"widget_{session_key}" # ウィジェットキーをセッションキーと区別
    )
    selected_timestamp = pd.Timestamp(selected_date_dt).normalize()
    st.session_state[session_key] = selected_timestamp # Timestampで保存
    return selected_timestamp


def clear_date_session_states(): #
    """日付関連のセッション状態をクリア"""
    date_session_keys = [
        # dow_analysis_tab.py
        'dow_comparison_start_date', 'dow_comparison_end_date',
        'dow_unit_selectbox', 'dow_target_wards_multiselect', 'dow_target_depts_multiselect',
        'dow_chart_metrics_multiselect', 'dow_aggregation_selectbox', 'dow_enable_comparison',
        'dow_comparison_display_mode', 'dow_comparison_graph_layout',
        'dow_comparison_metric_selector', 'dow_comparison_bar_style', 'dow_comparison_period_selector',

        # alos_analysis_tab.py (想定されるキー)
        'alos_granularity', 'alos_unit', 'alos_target_wards', 'alos_target_depts',
        'alos_ma_rolling_days', 'alos_benchmark',

        # individual_analysis_tab.py (想定されるキー)
        'ind_filter_type', 'ind_dept_select_display', 'ind_ward_select_display',
        'ind_graph_display_period_widget',

        # app.py / global (想定されるキー)
        'analysis_start_date', 'analysis_end_date', 'period_mode', 'global_preset_period',
        'custom_start_date', 'custom_end_date', 'sidebar_start_date', 'sidebar_end_date',
        'analysis_period_type', 'analysis_preset_period' # これらは get_analysis_period で使われる

        # pdf_output_tab.py (想定されるキー)
        'pdf_period_selector', 'pdf_custom_start', 'pdf_custom_end'
    ]
    cleared_count = 0
    for key in date_session_keys:
        if key in st.session_state:
            del st.session_state[key]
            cleared_count += 1
    logger.info(f"{cleared_count}個の日付・期間関連セッション状態をクリアしました。")
    return cleared_count

def validate_date_range(start_date_ts, end_date_ts, max_days=None): # max_daysはオプションに
    """日付範囲の妥当性をチェック (入力はTimestampを想定)"""
    if not isinstance(start_date_ts, pd.Timestamp) or not isinstance(end_date_ts, pd.Timestamp):
        return False, "開始日または終了日が有効な日付形式ではありません。"

    if start_date_ts > end_date_ts:
        return False, "開始日は終了日以前である必要があります。"

    period_days = (end_date_ts - start_date_ts).days + 1

    if period_days < 1: # 通常は start_date > end_date で捕捉されるが一応
        return False, "期間は最低1日必要です。"

    if max_days is not None and period_days > max_days:
        return False, f"期間が長すぎます（最大{max_days}日）。現在: {period_days}日間"

    return True, f"選択期間: {period_days}日間"


def create_safe_comparison_period_selector(df, current_start_date_ts, current_end_date_ts): #
    """
    安全な期間比較セレクター (dow_analysis_tab.py での使用を想定)
    df: 分析対象の全データフレーム
    current_start_date_ts, current_end_date_ts: 現在の分析期間の開始日と終了日 (Timestamp)
    """
    st.markdown("### 📅 比較期間選択")
    col1, col2 = st.columns(2)

    with col1:
        comp_start_ts = safe_date_input(
            "比較期間：開始日",
            df=df, # 全データの日付範囲を参照
            session_key="dow_comparison_start_date", # dow_analysis_tab 専用のセッションキー
            default_offset_days=365, # デフォルトは1年前
            is_end_date=False
        )
    with col2:
        # 現在の分析期間と同じ長さをデフォルトとする
        current_period_length_days = (current_end_date_ts - current_start_date_ts).days
        comp_end_ts = safe_date_input(
            "比較期間：終了日",
            df=df, # 全データの日付範囲を参照
            session_key="dow_comparison_end_date", # dow_analysis_tab 専用のセッションキー
            default_offset_days=current_period_length_days, # 現在期間の長さをオフセットに
            is_end_date=True,
            related_start_key="dow_comparison_start_date" # 開始日ウィジェットのキー
        )

    is_valid, message = validate_date_range(comp_start_ts, comp_end_ts) # 最大日数は設定しない
    if is_valid:
        st.success(message)
    else:
        st.error(message)
        return None, None # 無効な場合はNoneを返す

    return comp_start_ts, comp_end_ts


# --- 文字列変換ユーティリティ (変更なし) ---
def safe_convert_to_str(value):
    """
    値を安全に文字列に変換

    Parameters:
    -----------
    value : any
        変換する値

    Returns:
    --------
    str
        変換された文字列
    """
    if pd.isna(value):
        return ""
    return str(value).strip()

def get_unique_values_as_str(df, column_name):
    """
    指定された列のユニークな値を文字列のリストとして取得

    Parameters:
    -----------
    df : pd.DataFrame
        データフレーム
    column_name : str
        列名

    Returns:
    --------
    list
        ユニークな値のリスト（文字列）
    """
    if df is None or df.empty or column_name not in df.columns:
        return []
    try:
        unique_values = df[column_name].dropna().unique()
        # safe_convert_to_str を適用し、結果をソート
        return sorted([safe_convert_to_str(val) for val in unique_values if safe_convert_to_str(val)])
    except Exception as e:
        logger.error(f"get_unique_values_as_str ({column_name}) でエラー: {e}")
        return []
        
def filter_excluded_wards(df):
    """
    除外病棟をデータフレームから削除する汎用関数
    
    Parameters:
    -----------
    df : pd.DataFrame
        フィルタリング対象のデータフレーム
        
    Returns:
    --------
    pd.DataFrame
        除外病棟を削除したデータフレーム
    """
    from config import EXCLUDED_WARDS
    
    if df is None or df.empty:
        return df
        
    if '病棟コード' in df.columns and EXCLUDED_WARDS:
        original_count = len(df)
        df_filtered = df[~df['病棟コード'].isin(EXCLUDED_WARDS)]
        removed_count = original_count - len(df_filtered)
        
        if removed_count > 0:
            logger.info(f"除外病棟フィルタリング: {removed_count}件のレコードを除外しました（病棟: {', '.join(EXCLUDED_WARDS)}）")
        
        return df_filtered
    
    return df
    
def get_period_dates(df, period):
    """選択された期間文字列に基づいて開始日と終了日を計算する"""
    if df.empty or '日付' not in df.columns:
        return None, None, ""

    latest_date = pd.to_datetime(df['日付'].max())
    start_date, end_date = None, None
    period_desc = ""

    if period == "直近4週間":
        start_date = latest_date - pd.Timedelta(days=27)
        end_date = latest_date
        period_desc = f"直近4週間 ({start_date.strftime('%m/%d')}～{end_date.strftime('%m/%d')})"
    
    elif period == "直近8週":
        start_date = latest_date - pd.Timedelta(days=55)
        end_date = latest_date
        period_desc = f"直近8週間 ({start_date.strftime('%m/%d')}～{end_date.strftime('%m/%d')})"

    elif period == "直近12週":
        start_date = latest_date - pd.Timedelta(days=83)
        end_date = latest_date
        period_desc = f"直近12週間 ({start_date.strftime('%m/%d')}～{end_date.strftime('%m/%d')})"
    
    elif period == "今年度":
        today = latest_date
        if today.month >= 4:
            # 4月以降の場合、今年の4月1日が年度開始日
            start_date = pd.Timestamp(year=today.year, month=4, day=1)
        else:
            # 1月～3月の場合、去年の4月1日が年度開始日
            start_date = pd.Timestamp(year=today.year - 1, month=4, day=1)
        end_date = latest_date
        period_desc = f"今年度 ({start_date.strftime('%Y/%m/%d')}～)"
    
    elif period == "先月":
        first_day_of_current_month = latest_date.replace(day=1)
        last_day_of_last_month = first_day_of_current_month - pd.Timedelta(days=1)
        first_day_of_last_month = last_day_of_last_month.replace(day=1)
        start_date = first_day_of_last_month
        end_date = last_day_of_last_month
        period_desc = f"{start_date.year}年{start_date.month}月"
    
    elif period == "昨年度":
        today = latest_date
        if today.month >= 4:
            # 今が4月以降の場合、昨年度は去年の4月1日～今年の3月31日
            start_date = pd.Timestamp(year=today.year - 1, month=4, day=1)
            end_date = pd.Timestamp(year=today.year, month=3, day=31)
        else:
            # 今が1月～3月の場合、昨年度は一昨年の4月1日～去年の3月31日
            start_date = pd.Timestamp(year=today.year - 2, month=4, day=1)
            end_date = pd.Timestamp(year=today.year - 1, month=3, day=31)
        period_desc = f"{start_date.year}年度"

    if start_date and end_date:
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

    return start_date, end_date, period_desc

def calculate_department_kpis(df, target_data, dept_code, dept_name, start_date, end_date, dept_col):
    """診療科別KPI計算（直近週評価強化版）"""
    try:
        # 基本的なデータフィルタリング（従来通り）
        if dept_col is not None:
            # 従来通り、まず診療科で絞り、その後日付で絞り込む
            dept_df = df[df[dept_col] == dept_code]
            period_df = safe_date_filter(dept_df, start_date, end_date)
        else:
            # 病院全体の場合、dept_dfは元のdf全体とする
            dept_df = df
            period_df = safe_date_filter(df, start_date, end_date)
        
        if period_df.empty:
            return None
        
        # 期間全体の集計（従来通り）
        total_days = (end_date - start_date).days + 1
        total_patient_days = period_df['在院患者数'].sum() if '在院患者数' in period_df.columns else 0
        total_admissions = period_df['新入院患者数'].sum() if '新入院患者数' in period_df.columns else 0
        total_discharges = period_df['退院患者数'].sum() if '退院患者数' in period_df.columns else 0
        
        daily_avg_census = total_patient_days / total_days if total_days > 0 else 0
        
        # ===== 直近週の計算（強化版） =====
        recent_week_end = end_date
        recent_week_start = end_date - pd.Timedelta(days=6)  # 7日間
        recent_week_df = safe_date_filter(dept_df, recent_week_start, recent_week_end)
        
        # 直近週の詳細集計
        if not recent_week_df.empty:
            recent_week_patient_days = recent_week_df['在院患者数'].sum() if '在院患者数' in recent_week_df.columns else 0
            recent_week_admissions = recent_week_df['新入院患者数'].sum() if '新入院患者数' in recent_week_df.columns else 0
            recent_week_discharges = recent_week_df['退院患者数'].sum() if '退院患者数' in recent_week_df.columns else 0
            recent_week_daily_census = recent_week_patient_days / 7  # 7日間の平均
            recent_week_avg_los = recent_week_patient_days / recent_week_discharges if recent_week_discharges > 0 else 0
        else:
            # 直近週データがない場合のフォールバック
            recent_week_patient_days = 0
            recent_week_admissions = 0
            recent_week_discharges = 0
            recent_week_daily_census = 0
            recent_week_avg_los = 0
        
        # 期間全体の平均在院日数と週平均新入院
        avg_length_of_stay = total_patient_days / total_discharges if total_discharges > 0 else 0
        weekly_avg_admissions = (total_admissions / total_days) * 7 if total_days > 0 else 0
        
        # 目標値の取得
        targets = get_target_values_for_dept(target_data, dept_code, dept_name)
        
        # 病院全体の場合の特別処理（従来通り）
        if dept_code == '全体' and targets['daily_census_target'] != 580:
            logger.warning(f"病院全体の目標値が{targets['daily_census_target']}でした。580に強制変更します。")
            targets['daily_census_target'] = 580
        
        # ===== 達成率の計算（期間平均ベース・従来通り） =====
        daily_census_achievement = (daily_avg_census / targets['daily_census_target'] * 100) if targets['daily_census_target'] else 0
        weekly_admissions_achievement = (weekly_avg_admissions / targets['weekly_admissions_target'] * 100) if targets['weekly_admissions_target'] else 0
        
        # ===== 🔥 直近週ベースの達成率計算（新規追加） =====
        recent_week_census_achievement = (recent_week_daily_census / targets['daily_census_target'] * 100) if targets['daily_census_target'] else 0
        recent_week_admissions_achievement = (recent_week_admissions / targets['weekly_admissions_target'] * 100) if targets['weekly_admissions_target'] else 0
        
        # ===== 直近週 vs 期間平均の変化率（新規追加） =====
        census_change_rate = ((recent_week_daily_census - daily_avg_census) / daily_avg_census * 100) if daily_avg_census > 0 else 0
        admissions_change_rate = ((recent_week_admissions - weekly_avg_admissions) / weekly_avg_admissions * 100) if weekly_avg_admissions > 0 else 0
        los_change_rate = ((recent_week_avg_los - avg_length_of_stay) / avg_length_of_stay * 100) if avg_length_of_stay > 0 else 0
        
        # 平均在院日数達成率（従来通り）
        if targets['avg_los_target'] and avg_length_of_stay > 0:
            los_achievement = (targets['avg_los_target'] / avg_length_of_stay * 100)
        else:
            if avg_length_of_stay > 0 and recent_week_avg_los > 0:
                los_trend_ratio = avg_length_of_stay / recent_week_avg_los
                los_achievement = los_trend_ratio * 100
            else:
                los_achievement = 100
        
        # ===== 結果辞書（直近週データ追加版） =====
        return {
            # 基本情報
            'dept_code': dept_code,
            'dept_name': targets['display_name'],
            
            # 期間平均値（従来通り）
            'daily_avg_census': daily_avg_census,
            'weekly_avg_admissions': weekly_avg_admissions,
            'avg_length_of_stay': avg_length_of_stay,
            
            # 🔥 直近週実績（新規・重要）
            'recent_week_daily_census': recent_week_daily_census,
            'recent_week_admissions': recent_week_admissions,
            'recent_week_avg_los': recent_week_avg_los,
            
            # 目標値
            'daily_census_target': targets['daily_census_target'],
            'weekly_admissions_target': targets['weekly_admissions_target'],
            'avg_los_target': targets['avg_los_target'],
            
            # 期間平均ベース達成率（従来通り）
            'daily_census_achievement': daily_census_achievement,
            'weekly_admissions_achievement': weekly_admissions_achievement,
            'avg_los_achievement': los_achievement,
            
            # 🔥 直近週ベース達成率（新規・重要）
            'recent_week_census_achievement': recent_week_census_achievement,
            'recent_week_admissions_achievement': recent_week_admissions_achievement,
            
            # 🔥 変化率（直近週 vs 期間平均、新規）
            'census_change_rate': census_change_rate,
            'admissions_change_rate': admissions_change_rate,
            'los_change_rate': los_change_rate,
            
            # その他
            'has_los_target': targets['avg_los_target'] is not None,
            
            # 🔥 分析メタデータ（新規）
            'recent_week_data_available': not recent_week_df.empty,
            'recent_week_period': f"{recent_week_start.strftime('%m/%d')}～{recent_week_end.strftime('%m/%d')}"
        }
        
    except Exception as e:
        logger.error(f"直近週強化KPI計算エラー ({dept_code}): {e}", exc_info=True)
        return None

def calculate_ward_kpis(df, target_data, ward_code, ward_name, start_date, end_date, ward_col):
    """病棟別KPI計算（直近週評価強化版）"""
    try:
        # 病棟でフィルタリング
        ward_df = df[df[ward_col] == ward_code]
        period_df = safe_date_filter(ward_df, start_date, end_date)
        
        if period_df.empty:
            return None
        
        # 期間全体の集計（従来通り）
        total_days = (end_date - start_date).days + 1
        total_patient_days = period_df['在院患者数'].sum() if '在院患者数' in period_df.columns else 0
        total_admissions = period_df['新入院患者数'].sum() if '新入院患者数' in period_df.columns else 0
        total_discharges = period_df['退院患者数'].sum() if '退院患者数' in period_df.columns else 0
        
        daily_avg_census = total_patient_days / total_days if total_days > 0 else 0
        
        # ===== 直近週の計算（強化版） =====
        recent_week_end = end_date
        recent_week_start = end_date - pd.Timedelta(days=6)
        recent_week_df = safe_date_filter(ward_df, recent_week_start, recent_week_end)
        
        # 直近週の詳細集計
        if not recent_week_df.empty:
            recent_week_patient_days = recent_week_df['在院患者数'].sum() if '在院患者数' in recent_week_df.columns else 0
            recent_week_admissions = recent_week_df['新入院患者数'].sum() if '新入院患者数' in recent_week_df.columns else 0
            recent_week_discharges = recent_week_df['退院患者数'].sum() if '退院患者数' in recent_week_df.columns else 0
            recent_week_daily_census = recent_week_patient_days / 7
            recent_week_avg_los = recent_week_patient_days / recent_week_discharges if recent_week_discharges > 0 else 0
        else:
            recent_week_patient_days = 0
            recent_week_admissions = 0
            recent_week_discharges = 0
            recent_week_daily_census = 0
            recent_week_avg_los = 0
        
        avg_length_of_stay = total_patient_days / total_discharges if total_discharges > 0 else 0
        weekly_avg_admissions = (total_admissions / total_days) * 7 if total_days > 0 else 0
        
        # 目標値の取得
        targets = get_target_values_for_ward(target_data, ward_code, ward_name)
        
        # ===== 達成率の計算 =====
        # 期間平均ベース（従来通り）
        daily_census_achievement = (daily_avg_census / targets['daily_census_target'] * 100) if targets['daily_census_target'] else 0
        weekly_admissions_achievement = (weekly_avg_admissions / targets['weekly_admissions_target'] * 100) if targets['weekly_admissions_target'] else 0
        
        # 🔥 直近週ベース（新規追加）
        recent_week_census_achievement = (recent_week_daily_census / targets['daily_census_target'] * 100) if targets['daily_census_target'] else 0
        recent_week_admissions_achievement = (recent_week_admissions / targets['weekly_admissions_target'] * 100) if targets['weekly_admissions_target'] else 0
        
        # 🔥 変化率計算（新規追加）
        census_change_rate = ((recent_week_daily_census - daily_avg_census) / daily_avg_census * 100) if daily_avg_census > 0 else 0
        admissions_change_rate = ((recent_week_admissions - weekly_avg_admissions) / weekly_avg_admissions * 100) if weekly_avg_admissions > 0 else 0
        los_change_rate = ((recent_week_avg_los - avg_length_of_stay) / avg_length_of_stay * 100) if avg_length_of_stay > 0 else 0
        
        # 平均在院日数達成率（従来通り）
        if targets['avg_los_target'] and avg_length_of_stay > 0:
            los_achievement = (targets['avg_los_target'] / avg_length_of_stay * 100)
        else:
            if avg_length_of_stay > 0 and recent_week_avg_los > 0:
                los_trend_ratio = avg_length_of_stay / recent_week_avg_los
                los_achievement = los_trend_ratio * 100
            else:
                los_achievement = 100
        
        # 病床稼働率の計算（従来通り）
        bed_occupancy_rate = None
        recent_week_bed_occupancy_rate = None
        if targets['bed_count'] and targets['bed_count'] > 0:
            bed_occupancy_rate = (daily_avg_census / targets['bed_count']) * 100
            recent_week_bed_occupancy_rate = (recent_week_daily_census / targets['bed_count']) * 100
        
        # ===== 結果辞書（直近週データ追加版） =====
        return {
            # 基本情報
            'ward_code': ward_code,
            'ward_name': targets['display_name'],
            
            # 期間平均値（従来通り）
            'daily_avg_census': daily_avg_census,
            'weekly_avg_admissions': weekly_avg_admissions,
            'avg_length_of_stay': avg_length_of_stay,
            
            # 🔥 直近週実績（新規・重要）
            'recent_week_daily_census': recent_week_daily_census,
            'recent_week_admissions': recent_week_admissions,
            'recent_week_avg_los': recent_week_avg_los,
            
            # 目標値
            'daily_census_target': targets['daily_census_target'],
            'weekly_admissions_target': targets['weekly_admissions_target'],
            'avg_los_target': targets['avg_los_target'],
            
            # 期間平均ベース達成率（従来通り）
            'daily_census_achievement': daily_census_achievement,
            'weekly_admissions_achievement': weekly_admissions_achievement,
            'avg_los_achievement': los_achievement,
            
            # 🔥 直近週ベース達成率（新規・重要）
            'recent_week_census_achievement': recent_week_census_achievement,
            'recent_week_admissions_achievement': recent_week_admissions_achievement,
            
            # 🔥 変化率（直近週 vs 期間平均、新規）
            'census_change_rate': census_change_rate,
            'admissions_change_rate': admissions_change_rate,
            'los_change_rate': los_change_rate,
            
            # 病床関連
            'bed_count': targets['bed_count'],
            'bed_occupancy_rate': bed_occupancy_rate,
            'recent_week_bed_occupancy_rate': recent_week_bed_occupancy_rate,
            
            # その他
            'has_los_target': targets['avg_los_target'] is not None,
            
            # 🔥 分析メタデータ（新規）
            'recent_week_data_available': not recent_week_df.empty,
            'recent_week_period': f"{recent_week_start.strftime('%m/%d')}～{recent_week_end.strftime('%m/%d')}"
        }
        
    except Exception as e:
        logger.error(f"病棟直近週強化KPI計算エラー ({ward_code}): {e}", exc_info=True)
        return None
        
def evaluate_feasibility(kpi_data, dept_df, start_date, end_date):
    """実現可能性を評価（直近週考慮版）"""
    try:
        # 期間平均データ（従来通り）
        period_avg_census = kpi_data.get('daily_avg_census', 0)
        period_admissions = kpi_data.get('weekly_avg_admissions', 0)
        
        # 🔥 直近週データ（新規考慮）
        recent_week_census = kpi_data.get('recent_week_daily_census', 0)
        recent_week_admissions = kpi_data.get('recent_week_admissions', 0)
        
        # 新入院の実現可能性評価（直近週重視版）
        admission_feasible = {
            "病床余裕": kpi_data.get('daily_census_achievement', 0) < 90,  # 期間平均ベース
            "直近週トレンド": recent_week_admissions >= period_admissions * 0.95 if period_admissions > 0 else True,  # 🔥 直近週考慮
            "トレンド安定": kpi_data.get('recent_week_admissions', 0) >= kpi_data.get('weekly_avg_admissions', 0) * 0.95  # 従来通り
        }
        
        # 在院日数の適正範囲（従来通り）
        los_range = calculate_los_appropriate_range(dept_df, start_date, end_date)
        recent_los = kpi_data.get('recent_week_avg_los', 0)
        avg_los = kpi_data.get('avg_length_of_stay', 0)
        
        # 在院日数の実現可能性評価（直近週重視版）
        los_feasible = {
            "調整余地": abs(recent_los - avg_los) > avg_los * 0.03 if avg_los > 0 else False,  # 🔥 直近週 vs 期間平均
            "適正範囲内": bool(
                los_range and 
                los_range["lower"] <= recent_los <= los_range["upper"]
            ) if recent_los > 0 else False,
            "直近週変化": abs(kpi_data.get('los_change_rate', 0)) < 15  # 🔥 直近週の変化が15%未満なら調整可能
        }
        
        return {
            "admission": admission_feasible,
            "los": los_feasible,
            "los_range": los_range,
            "recent_week_considered": True  # 🔥 直近週を考慮したことを明示
        }
        
    except Exception as e:
        logger.error(f"実現可能性評価エラー（直近週考慮版）: {e}")
        return {"admission": {}, "los": {}, "los_range": None, "recent_week_considered": False}

def decide_action_and_reasoning(kpi_data, feasibility, simulation):
    """
    アクション判断とその根拠（直近週重視版：98%基準、在院患者数エンドポイント）
    
    修正内容：
    - 直近週の実績を重視した判定ロジック
    - 直近週 vs 目標、直近週 vs 期間平均の両面評価
    - 在院患者数の目標達成をエンドポイントとする判定
    - 98%基準での段階的対応
    """
    
    # ===== 直近週重視のKPIデータ取得 =====
    # 在院患者数関連
    period_avg_census = kpi_data.get('daily_avg_census', 0)      # 期間平均
    recent_week_census = kpi_data.get('recent_week_daily_census', 0)  # 直近週実績★
    census_target = kpi_data.get('daily_census_target', 0)       # 目標値
    period_census_achievement = kpi_data.get('daily_census_achievement', 0)  # 期間平均達成率
    
    # 新入院関連
    period_avg_admissions = kpi_data.get('weekly_avg_admissions', 0)  # 期間平均
    recent_week_admissions = kpi_data.get('recent_week_admissions', 0)  # 直近週実績★
    admissions_target = kpi_data.get('weekly_admissions_target', 0)   # 新入院目標値
    period_admissions_achievement = kpi_data.get('weekly_admissions_achievement', 0)  # 期間平均達成率
    
    # ===== 直近週ベースの達成率計算（重要！） =====
    recent_week_census_achievement = (recent_week_census / census_target * 100) if census_target > 0 else 0
    recent_week_admissions_achievement = (recent_week_admissions / admissions_target * 100) if admissions_target > 0 else 0
    
    # ===== 直近週 vs 期間平均の変化率 =====
    census_change_rate = ((recent_week_census - period_avg_census) / period_avg_census * 100) if period_avg_census > 0 else 0
    admissions_change_rate = ((recent_week_admissions - period_avg_admissions) / period_avg_admissions * 100) if period_avg_admissions > 0 else 0
    
    # ===== 平均在院日数のトレンド =====
    los_period_avg = kpi_data.get('avg_length_of_stay', 0)
    los_recent = kpi_data.get('recent_week_avg_los', 0)
    los_change_rate = ((los_recent - los_period_avg) / los_period_avg * 100) if los_period_avg > 0 else 0
    
    # ===== 直近週重視のアクション判定ロジック =====
    
    # 🚨 例外処理：直近週が90%未満の緊急事態
    if recent_week_census_achievement < 90:
        gap = census_target - recent_week_census if census_target > 0 else 0
        return {
            "action": "緊急総合対策", 
            "reasoning": f"直近週で大幅な目標未達成（達成率{recent_week_census_achievement:.1f}%、{gap:.1f}人不足）。新入院増加と在院日数適正化の両面からの緊急対応が必要", 
            "priority": "urgent", 
            "color": "#F44336",
            "recent_week_focus": True,
            "key_metrics": {
                "recent_week_achievement": recent_week_census_achievement,
                "trend_vs_period": census_change_rate,
                "gap_from_target": gap
            }
        }
    
    # 🎯 エンドポイント：直近週での在院患者数目標達成（98%基準）
    if recent_week_census_achievement >= 98:
        # ✅ 直近週で目標達成時の判定
        if census_change_rate >= 5:
            return {
                "action": "成功パターン拡大", 
                "reasoning": f"直近週で目標達成（{recent_week_census_achievement:.1f}%）＋改善傾向（期間平均比+{census_change_rate:.1f}%）。この成功パターンを維持・拡大", 
                "priority": "low", 
                "color": "#4CAF50",
                "recent_week_focus": True,
                "key_metrics": {
                    "recent_week_achievement": recent_week_census_achievement,
                    "trend_vs_period": census_change_rate,
                    "status": "excellent"
                }
            }
        elif census_change_rate >= 0:
            return {
                "action": "現状維持", 
                "reasoning": f"直近週で目標達成（{recent_week_census_achievement:.1f}%）。安定した良好な状況を継続", 
                "priority": "low", 
                "color": "#7fb069",
                "recent_week_focus": True,
                "key_metrics": {
                    "recent_week_achievement": recent_week_census_achievement,
                    "trend_vs_period": census_change_rate,
                    "status": "stable_good"
                }
            }
        else:
            return {
                "action": "維持強化", 
                "reasoning": f"直近週で目標達成（{recent_week_census_achievement:.1f}%）だが下降気味（{census_change_rate:.1f}%）。達成レベル維持のための対策を", 
                "priority": "medium", 
                "color": "#FF9800",
                "recent_week_focus": True,
                "key_metrics": {
                    "recent_week_achievement": recent_week_census_achievement,
                    "trend_vs_period": census_change_rate,
                    "status": "achieved_but_declining"
                }
            }
    
    # 🔶 中間レベル（90-98%）：直近週の新入院達成状況で判断
    elif recent_week_census_achievement >= 90:
        if recent_week_admissions_achievement < 98:
            # 新入院も未達成 → 新入院を最優先
            return {
                "action": "新入院重視", 
                "reasoning": f"直近週：在院患者{recent_week_census_achievement:.1f}%・新入院{recent_week_admissions_achievement:.1f}%。まず新入院増加を最優先で推進", 
                "priority": "high", 
                "color": "#2196F3",
                "recent_week_focus": True,
                "key_metrics": {
                    "recent_week_census_achievement": recent_week_census_achievement,
                    "recent_week_admissions_achievement": recent_week_admissions_achievement,
                    "focus": "admission_priority"
                }
            }
        else:
            # 新入院は達成済み → 在院日数調整で目標達成を目指す
            return {
                "action": "在院日数調整", 
                "reasoning": f"直近週：新入院は目標達成済み（{recent_week_admissions_achievement:.1f}%）、在院日数の適正化により在院患者数目標達成を", 
                "priority": "high", 
                "color": "#FF9800",
                "recent_week_focus": True,
                "key_metrics": {
                    "recent_week_census_achievement": recent_week_census_achievement,
                    "recent_week_admissions_achievement": recent_week_admissions_achievement,  
                    "los_change_rate": los_change_rate,
                    "focus": "los_adjustment"
                }
            }
    
    # 🔴 その他のケース（フォールバック処理）
    else:
        # 理論的には90%未満のケースで最初に捕捉されるはずだが、安全のため
        return {
            "action": "状況確認", 
            "reasoning": f"直近週のデータ（達成率{recent_week_census_achievement:.1f}%）を詳しく確認し、適切な対策を検討", 
            "priority": "medium", 
            "color": "#9E9E9E",
            "recent_week_focus": True,
            "key_metrics": {
                "recent_week_achievement": recent_week_census_achievement,
                "status": "needs_review"
            }
        }


def get_target_values_for_ward(target_data, ward_code, ward_name):
    """病棟の目標値を取得"""
    targets = {
        'daily_census_target': None,
        'weekly_admissions_target': None,
        'avg_los_target': None,
        'bed_count': None,
        'display_name': ward_name
    }
    
    if target_data is None:
        return targets
    
    # 日平均在院患者数の目標値
    daily_targets = target_data[
        (target_data['部門コード'] == ward_code) & 
        (target_data['指標タイプ'] == '日平均在院患者数')
    ]
    if not daily_targets.empty:
        targets['daily_census_target'] = daily_targets.iloc[0]['目標値']
        # 病床数も取得
        if '病床数' in daily_targets.columns:
            targets['bed_count'] = daily_targets.iloc[0]['病床数']
    
    # 週間新入院患者数の目標値
    admission_targets = target_data[
        (target_data['部門コード'] == ward_code) & 
        (target_data['指標タイプ'] == '週間新入院患者数')
    ]
    if not admission_targets.empty:
        targets['weekly_admissions_target'] = admission_targets.iloc[0]['目標値']
    
    # 平均在院日数の目標値（もしあれば）
    los_targets = target_data[
        (target_data['部門コード'] == ward_code) & 
        (target_data['指標タイプ'] == '平均在院日数')
    ]
    if not los_targets.empty:
        targets['avg_los_target'] = los_targets.iloc[0]['目標値']
    
    return targets

def get_target_values_for_dept(target_data, dept_code, dept_name):
    """診療科の目標値を取得"""
    targets = {
        'daily_census_target': None,
        'weekly_admissions_target': None,
        'avg_los_target': None,
        'display_name': dept_name
    }
    
    if target_data is None:
        return targets
    
    # 日平均在院患者数の目標値
    daily_targets = target_data[
        (target_data['部門名'] == dept_name) & 
        (target_data['指標タイプ'] == '日平均在院患者数')
    ]
    if not daily_targets.empty:
        targets['daily_census_target'] = daily_targets.iloc[0]['目標値']
    
    # 週間新入院患者数の目標値
    admission_targets = target_data[
        (target_data['部門名'] == dept_name) & 
        (target_data['指標タイプ'] == '週間新入院患者数')
    ]
    if not admission_targets.empty:
        targets['weekly_admissions_target'] = admission_targets.iloc[0]['目標値']
    
    # 平均在院日数の目標値（もしあれば）
    los_targets = target_data[
        (target_data['部門名'] == dept_name) & 
        (target_data['指標タイプ'] == '平均在院日数')
    ]
    if not los_targets.empty:
        targets['avg_los_target'] = los_targets.iloc[0]['目標値']
    
    return targets


def get_target_ward_list(target_data: pd.DataFrame, excluded_wards: list) -> list[tuple[str, str]]:
    """
    目標設定データから公開対象の病棟リストを取得する
    """
    import streamlit as st # 関数内でstをインポート

    if target_data is None or target_data.empty:
        return []
    
    try:
        # 必要な列が存在するか確認
        required_cols = ['部門種別', '指標タイプ', '部門コード', '部門名']
        if not all(col in target_data.columns for col in required_cols):
            st.error("目標設定ファイルに必要な列（部門種別, 指標タイプ, 部門コード, 部門名）が不足しています。")
            return []

        ward_data = target_data[
            (target_data['部門種別'] == '病棟') &
            (target_data['指標タイプ'] == '日平均在院患者数') &
            (~target_data['部門コード'].isin(excluded_wards))
        ].copy()
        
        ward_list = ward_data[['部門コード', '部門名']].drop_duplicates().sort_values(by='部門コード')
        
        return [(str(row['部門コード']), str(row['部門名'])) for _, row in ward_list.iterrows()]
    except Exception as e:
        st.error(f"目標ファイルからの病棟リスト取得に失敗: {e}")
        return []

def calculate_los_appropriate_range(dept_df, start_date, end_date):
    """統計的アプローチで在院日数適正範囲を計算"""
    if dept_df.empty or '平均在院日数' not in dept_df.columns: 
        return None
    try:
        period_df = safe_date_filter(dept_df, start_date, end_date)
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
    except Exception as e:
        logger.error(f"在院日数適正範囲計算エラー: {e}")
        return None

def calculate_effect_simulation(kpi_data):
    """効果シミュレーション計算（直近週ベース版）"""
    try:
        # 🔥 直近週実績をベースにシミュレーション
        recent_week_census = kpi_data.get('recent_week_daily_census', 0)
        target_census = kpi_data.get('daily_census_target', 0)
        recent_week_admissions = kpi_data.get('recent_week_admissions', 0) / 7  # 日平均に変換
        recent_week_los = kpi_data.get('recent_week_avg_los', 0)
        
        # フォールバック：直近週データがない場合は期間平均を使用
        if recent_week_census == 0:
            recent_week_census = kpi_data.get('daily_avg_census', 0)
            recent_week_admissions = kpi_data.get('weekly_avg_admissions', 0) / 7
            recent_week_los = kpi_data.get('avg_length_of_stay', 0)
        
        if not all([target_census, recent_week_admissions, recent_week_los]) or (target_census - recent_week_census) <= 0: 
            return None
        
        gap = target_census - recent_week_census  # 🔥 直近週実績との差
        
        # リトルの法則による効果計算（直近週ベース）
        needed_admissions_increase = gap / recent_week_los if recent_week_los > 0 else 0
        needed_los_increase = (target_census / recent_week_admissions) - recent_week_los if recent_week_admissions > 0 else 0
        
        return {
            "gap": gap,
            "admission_plan": {
                "increase": needed_admissions_increase, 
                "effect": needed_admissions_increase * recent_week_los,
                "base_data": "recent_week"  # 🔥 ベースデータを明示
            },
            "los_plan": {
                "increase": needed_los_increase, 
                "effect": recent_week_admissions * needed_los_increase,
                "base_data": "recent_week"  # 🔥 ベースデータを明示
            },
            "simulation_base": "recent_week_performance"  # 🔥 シミュレーションベースを明示
        }
        
    except Exception as e:
        logger.error(f"効果シミュレーション計算エラー（直近週ベース版）: {e}")
        return None

def get_hospital_targets(target_data):
    """病院全体の目標値を取得（全日優先）"""
    import logging
    import pandas as pd
    logger = logging.getLogger(__name__)
    
    targets = {'daily_census': 580, 'daily_admissions': 80}
    
    if target_data is None or target_data.empty: 
        logger.warning("目標データが空またはNoneです。デフォルト値を使用します。")
        return targets
    
    try:
        # 🎯 優先順位付きで目標値を検索（全日を最優先に変更）
        search_patterns = [
            {'期間区分': '全日', '指標タイプ': '日平均在院患者数'},
            {'期間区分': '平日', '指標タイプ': '日平均在院患者数'}, # フォールバックとして平日
        ]
        
        for pattern in search_patterns:
            filtered = target_data[
                (target_data['部門コード'].astype(str).str.strip() == '全体') &
                (target_data['部門種別'].astype(str).str.strip() == '病棟') &
                (target_data['期間区分'].astype(str).str.strip() == pattern['期間区分']) &
                (target_data['指標タイプ'].astype(str).str.strip() == pattern['指標タイプ'])
            ]
            
            if not filtered.empty:
                target_value = filtered.iloc[0]['目標値']
                if pd.notna(target_value) and target_value > 0:
                    targets['daily_census'] = float(target_value)
                    logger.info(f"病院全体の目標値として'{pattern['期間区分']}'区分の値 ({target_value}) を設定しました。")
                    # 最初の有効な値が見つかったらループを抜ける
                    break
        
        if targets['daily_census'] == 580:
             logger.info("目標値が見つからなかったか、無効な値でした。デフォルトの580を使用します。")

    except Exception as e:
        logger.error(f"目標値取得エラー。デフォルト値を使用: {e}")
        targets['daily_census'] = 580
    
    return targets