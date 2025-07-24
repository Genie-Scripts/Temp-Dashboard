import streamlit as st
import pandas as pd
from datetime import datetime
import time  # ← ★★★ この行を追加 ★★★


# table_generator.py から関数をインポート
# このファイルが table_generator.py と同じディレクトリにあることを想定しています。
try:
    from table_generator import generate_department_table
except ImportError:
    st.error("エラー: table_generator.py が見つかりません。適切な場所に配置してください。")
    generate_department_table = None # 関数が利用できないことを示す

def display_department_tables_tab(department_type: str):
    """
    病棟別または診療科別のテーブルタブのUIとロジックを表示します。

    Parameters:
    -----------
    department_type : str
        'ward' (病棟別) または 'clinical' (診療科別) を指定します。
    """

    if department_type == 'ward':
        st.header("🏥 病棟別テーブル")
        header_title_suffix = "病棟"
        sort_default_text = "病棟コード順"
    elif department_type == 'clinical':
        st.header("👨‍⚕️ 診療科別テーブル")
        header_title_suffix = "診療科"
        sort_default_text = "診療科名順"
    else:
        st.error("内部エラー: 無効な department_type が指定されました。")
        return

    # --- セッションステートから必要なデータを取得 ---
    if 'data_processed' not in st.session_state or not st.session_state.data_processed:
        st.warning("まず「データ処理」タブでデータを読み込み、処理を実行してください。")
        return

    df = st.session_state.get('df')
    target_data_df = st.session_state.get('target_data') # CSVから読み込んだ目標値データ
    # latest_data_date_str は直接は使用せず、分析期間をサイドバーから取得

    if df is None or df.empty:
        st.error("分析対象のデータフレームが読み込まれていません。「データ処理」タブを再実行してください。")
        return

    # サイドバーで設定された共通の分析期間を取得 (app.py で設定されるキーを想定)
    default_start_date = df['日付'].min().date() if not df.empty else datetime.now().date() - pd.Timedelta(days=365)
    default_end_date = df['日付'].max().date() if not df.empty else datetime.now().date()
    
    common_start_date = st.session_state.get('sidebar_start_date', default_start_date)
    common_end_date = st.session_state.get('sidebar_end_date', default_end_date)

    # --- UI要素 (表示モード、並べ替え) ---
    col1_options, col2_options = st.columns([1, 2])
    with col1_options:
        display_mode_label = st.radio(
            "表示モード",
            ["基本情報", "詳細情報"],
            key=f"dt_display_mode_{department_type}", # キーに department_type を含めてユニークにする
            horizontal=True,
            index=0 # デフォルトは「基本情報」
        )
        display_mode_param = 'basic' if display_mode_label == "基本情報" else 'detailed'

    with col2_options:
        sort_options_dict = {
            sort_default_text: 'code',
            "目標達成率順": 'achievement',
            f"{header_title_suffix}別 患者数順": 'patients' # 例: 「病棟別 患者数順」
        }
        sort_option_label = st.radio(
            "並べ替え",
            list(sort_options_dict.keys()),
            key=f"dt_sort_option_{department_type}", # キーに department_type を含めてユニークにする
            horizontal=True,
            index=0
        )
        sort_by_param = sort_options_dict[sort_option_label]

    # --- 診療科表示設定の適用 (診療科別テーブルの場合) ---
    included_departments_list = None
    if department_type == 'clinical':
        show_all = st.session_state.get('show_all_depts', True)
        use_selected = st.session_state.get('use_selected_depts', False)
        
        if not show_all:
            if use_selected:
                # 選択された診療科を使用
                dept_codes = st.session_state.get('selected_depts_sidebar', [])
                
                # 表示用に部門名に変換
                dept_names = []
                try:
                    from utils import get_display_name_for_dept
                    for dept_code in dept_codes:
                        display_name = get_display_name_for_dept(dept_code, dept_code)
                        dept_names.append(display_name)
                except:
                    # マッピングが使えない場合はコードをそのまま使用
                    dept_names = dept_codes
                    
                included_departments_list = dept_codes  # 実際の処理用には部門コードを使用
                
                if not included_departments_list:
                    st.info("表示する診療科が選択されていません。サイドバーで設定してください。")
                else:
                    st.info(f"選択された {len(included_departments_list)} 診療科を表示します：{', '.join(dept_names[:5])}" + 
                        ("..." if len(dept_names) > 5 else ""))
            else: # 主要診療科のみ
                included_departments_list = st.session_state.get('selected_depts_sidebar', [])
                
                # 表示用に部門名に変換
                dept_names = []
                try:
                    from utils import get_display_name_for_dept
                    for dept_code in included_departments_list:
                        display_name = get_display_name_for_dept(dept_code, dept_code)
                        dept_names.append(display_name)
                except:
                    # マッピングが使えない場合はコードをそのまま使用
                    dept_names = included_departments_list
                    
                if not included_departments_list:
                    st.info("表示する主要診療科が設定されていません。")
                else:
                    st.info(f"主要診療科 {len(included_departments_list)} 件を表示します：{', '.join(dept_names[:5])}" + 
                        ("..." if len(dept_names) > 5 else ""))
        else:
            st.info("すべての診療科を表示します。")
            included_departments_list = None # None を渡すと全診療科が対象になる想定

    # --- テーブルデータ生成と表示 ---
    if generate_department_table: # 関数がインポートできているか確認
        with st.spinner(f"{header_title_suffix}別テーブルデータを生成中..."):
            table_generation_start_time = time.time() # ← ここで time モジュールを使用
            
            # generate_department_table を呼び出し
            # benchmark_alos, benchmark_bed_occupancy は target_data_df から取得するためNoneで渡す
            table_df_result = generate_department_table(
                df=df,
                department_type=department_type,
                start_date=common_start_date,
                end_date=common_end_date,
                display_mode=display_mode_param,
                sort_by=sort_by_param,
                target_data_df=target_data_df, # 目標値と病床数を含むDataFrameを渡す
                included_departments=included_departments_list
            )
            table_generation_end_time = time.time()

            if table_df_result is not None and not table_df_result.empty:
                st.dataframe(table_df_result.style.format(precision=1), use_container_width=True)
                st.caption(f"テーブル生成時間: {table_generation_end_time - table_generation_start_time:.2f}秒")
            elif table_df_result is not None and table_df_result.empty:
                st.info("表示対象のデータが見つかりませんでした。分析期間やフィルター条件を確認してください。")
            else:
                st.warning(f"{header_title_suffix}別テーブルデータの生成に失敗しました。")
    else:
        st.error("テーブル生成関数 (generate_department_table) が利用できません。")
