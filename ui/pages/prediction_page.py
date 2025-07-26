# ui/pages/prediction_page.py
"""
将来予測ページモジュール
統計的手法を用いた将来予測分析を表示
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, Optional
import logging

from ui.session_manager import SessionManager
from ui.error_handler import safe_streamlit_operation, safe_data_operation

# 既存の分析モジュールをインポート
from analysis import forecasting
from plotting import generic_plots

logger = logging.getLogger(__name__)


class PredictionPage:
    """将来予測ページクラス"""
    
    @staticmethod
    @safe_streamlit_operation("将来予測ページ描画")
    def render() -> None:
        """将来予測ページを描画"""
        st.title("🔮 将来予測")
        
        # データ取得
        df = SessionManager.get_processed_df()
        target_dict = SessionManager.get_target_dict()
        latest_date = SessionManager.get_latest_date()
        
        # 予測対象データの説明
        PredictionPage._render_prediction_info()
        
        # タブで機能を分割
        tab1, tab2, tab3 = st.tabs(["将来予測", "モデル検証", "パラメータ最適化"])
        
        with tab1:
            PredictionPage._render_prediction_tab(df, target_dict, latest_date)
        
        with tab2:
            PredictionPage._render_validation_tab(df)
        
        with tab3:
            PredictionPage._render_optimization_tab(df)
    
    @staticmethod
    def _render_prediction_info() -> None:
        """予測データの詳細説明を表示"""
        with st.expander("📊 予測データの詳細説明", expanded=False):
            st.markdown("""
            **予測対象データ**: 全身麻酔手術（20分以上）
            
            **重要**: 休日データの扱いについては実装により異なります
            - 平日のみ対象の場合: 土日祝日、年末年始は除外
            - 全日対象の場合: 休日の緊急手術も含む
            
            **フィルタ条件**:
            - `is_gas_20min = True` （全身麻酔20分以上）
            - `is_weekday` の使用有無は実装依存
            """)
    
    @staticmethod
    @safe_data_operation("将来予測")
    def _render_prediction_tab(df: pd.DataFrame, target_dict: Dict[str, Any], 
                             latest_date: Optional[pd.Timestamp]) -> None:
        """将来予測タブを表示"""
        st.header("📈 将来予測")
        
        # 予測パラメータ設定
        col1, col2 = st.columns(2)
        
        with col1:
            pred_target = st.radio(
                "予測対象", 
                ["病院全体", "診療科別"], 
                horizontal=True, 
                key="pred_target"
            )
        
        with col2:
            department = None
            if pred_target == "診療科別":
                departments = sorted(df["実施診療科"].dropna().unique())
                department = st.selectbox(
                    "診療科を選択", 
                    departments, 
                    key="pred_dept_select"
                )
        
        # モデル・期間設定
        col1, col2 = st.columns(2)
        
        with col1:
            model_type = st.selectbox(
                "予測モデル", 
                ["hwes", "arima", "moving_avg"], 
                format_func=lambda x: {
                    "hwes": "Holt-Winters", 
                    "arima": "ARIMA", 
                    "moving_avg": "移動平均"
                }[x]
            )
        
        with col2:
            pred_period = st.selectbox(
                "予測期間", 
                ["fiscal_year", "calendar_year", "six_months"], 
                format_func=lambda x: {
                    "fiscal_year": "年度末まで", 
                    "calendar_year": "年末まで", 
                    "six_months": "6ヶ月先まで"
                }[x]
            )
        
        # 予測実行
        if st.button("🔮 予測を実行", type="primary", key="run_prediction"):
            PredictionPage._execute_prediction(
                df, latest_date, department, model_type, pred_period, target_dict
            )
    
    @staticmethod
    @safe_data_operation("予測実行")
    def _execute_prediction(df: pd.DataFrame, latest_date: Optional[pd.Timestamp],
                          department: Optional[str], model_type: str, 
                          pred_period: str, target_dict: Dict[str, Any]) -> None:
        """予測を実行"""
        with st.spinner("予測計算中..."):
            try:
                result_df, metrics = forecasting.predict_future(
                    df, latest_date, 
                    department=department, 
                    model_type=model_type, 
                    prediction_period=pred_period
                )
                
                if metrics.get("message"):
                    st.warning(metrics["message"])
                else:
                    title = f"{department or '病院全体'} {metrics.get('予測モデル', '')}モデルによる予測"
                    
                    # グラフ表示
                    fig = generic_plots.create_forecast_chart(result_df, title)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 予測入力データの詳細分析
                    PredictionPage._render_prediction_data_analysis(
                        df, department, result_df
                    )
                    
                    # 予測サマリーテーブル表示
                    PredictionPage._render_prediction_summary(
                        result_df, target_dict, department, df
                    )
                    
                    # モデル評価指標表示
                    with st.expander("📊 モデル評価指標詳細"):
                        st.write(metrics)
                        
            except Exception as e:
                st.error(f"予測実行エラー: {e}")
                logger.error(f"予測実行エラー: {e}")
    
    @staticmethod
    def _render_prediction_data_analysis(df: pd.DataFrame, department: Optional[str], 
                                       result_df: pd.DataFrame) -> None:
        """予測入力データの詳細分析を表示"""
        st.header("🔍 予測入力データの詳細分析")
        
        try:
            if department:
                base_data = df[df['実施診療科'] == department]
            else:
                base_data = df
            
            # 各段階でのデータ件数を詳細に表示
            total_data = len(base_data)
            gas_data = base_data[base_data['is_gas_20min']]
            gas_count = len(gas_data)
            
            # 平日・休日の内訳
            weekday_data = gas_data[gas_data['is_weekday']]
            weekend_data = gas_data[~gas_data['is_weekday']]
            weekday_count = len(weekday_data)
            weekend_count = len(weekend_data)
            
            # 曜日別の詳細分析
            day_analysis = gas_data.groupby(gas_data['手術実施日_dt'].dt.day_name()).size()
            
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📊 データフィルタリング結果")
                filter_summary = pd.DataFrame({
                    'フィルタ段階': [
                        '1. 全データ',
                        '2. 全身麻酔(20分以上)',
                        '3. うち平日のみ',
                        '4. うち休日のみ'
                    ],
                    '件数': [
                        f"{total_data:,}件",
                        f"{gas_count:,}件", 
                        f"{weekday_count:,}件",
                        f"{weekend_count:,}件"
                    ],
                    '割合': [
                        "100%",
                        f"{gas_count/total_data*100:.1f}%" if total_data > 0 else "0%",
                        f"{weekday_count/gas_count*100:.1f}%" if gas_count > 0 else "0%",
                        f"{weekend_count/gas_count*100:.1f}%" if gas_count > 0 else "0%"
                    ]
                })
                st.dataframe(filter_summary, hide_index=True, use_container_width=True)
            
            with col2:
                st.subheader("📅 曜日別内訳")
                if not day_analysis.empty:
                    day_df = pd.DataFrame({
                        '曜日': day_analysis.index,
                        '件数': day_analysis.values
                    })
                    # 曜日順にソート
                    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                    day_df['曜日順'] = day_df['曜日'].map({day: i for i, day in enumerate(day_order)})
                    day_df = day_df.sort_values('曜日順').drop('曜日順', axis=1)
                    st.dataframe(day_df, hide_index=True, use_container_width=True)
            
            # 重要な確認メッセージ
            if weekend_count > 0:
                st.warning(f"""
                ⚠️ **重要確認**: 休日にも{weekend_count}件の全身麻酔手術があります。
                
                **予測モデルがどちらを使用しているかは `forecasting.py` の実装によります：**
                - 平日のみ使用: {weekday_count}件のデータで予測
                - 全日使用: {gas_count}件のデータで予測
                
                実際に使用されているデータは、予測結果の実績部分の件数と比較して確認できます。
                """)
            else:
                st.info("✅ 対象期間中の休日手術は0件のため、平日・全日どちらでも同じ結果になります。")
                
        except Exception as e:
            st.error(f"予測データ分析エラー: {e}")
            logger.error(f"予測データ分析エラー: {e}")
    
    @staticmethod
    def _render_prediction_summary(result_df: pd.DataFrame, target_dict: Dict[str, Any],
                                 department: Optional[str], source_df: pd.DataFrame) -> None:
        """予測サマリーテーブルを表示"""
        st.header("📋 予測サマリー")
        
        try:
            summary_df, monthly_df = generic_plots.create_forecast_summary_table(
                result_df, target_dict, department, source_df=source_df
            )
            
            if not summary_df.empty:
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("年度予測サマリー")
                    st.dataframe(summary_df, hide_index=True, use_container_width=True)
                    
                    # 実績値との整合性チェック
                    if '種別' in result_df.columns:
                        actual_from_forecast = result_df[result_df['種別'] == '実績']['値'].sum()
                        gas_count = len(source_df[source_df['is_gas_20min']])
                        weekday_count = len(source_df[source_df['is_gas_20min'] & source_df['is_weekday']])
                        
                        st.caption(f"""
                        **整合性チェック**: 
                        - 予測結果の実績部分: {actual_from_forecast:.0f}件
                        - 平日全身麻酔データ: {weekday_count}件
                        - 全日全身麻酔データ: {gas_count}件
                        """)
                
                with col2:
                    st.subheader("月別予測詳細")
                    if not monthly_df.empty:
                        st.dataframe(monthly_df, hide_index=True, use_container_width=True)
                    else:
                        st.info("月別予測データがありません")
            else:
                st.info("予測サマリーを生成できませんでした")
                
        except Exception as e:
            st.error(f"サマリーテーブル生成エラー: {str(e)}")
            logger.error(f"予測サマリー生成エラー: {e}")
    
    @staticmethod
    @safe_data_operation("モデル検証")
    def _render_validation_tab(df: pd.DataFrame) -> None:
        """モデル検証タブを表示"""
        st.header("📊 予測モデルの精度検証")
        
        # 検証パラメータ設定
        col1, col2 = st.columns(2)
        
        with col1:
            val_target = st.radio(
                "検証対象", 
                ["病院全体", "診療科別"], 
                horizontal=True, 
                key="val_target"
            )
        
        with col2:
            val_dept = None
            if val_target == "診療科別":
                departments = sorted(df["実施診療科"].dropna().unique())
                val_dept = st.selectbox(
                    "診療科を選択", 
                    departments, 
                    key="val_dept"
                )
        
        val_period = st.slider("検証期間（月数）", 3, 12, 6)
        
        if st.button("🔍 検証実行", key="run_validation"):
            PredictionPage._execute_validation(df, val_dept, val_period)
    
    @staticmethod
    @safe_data_operation("検証実行")
    def _execute_validation(df: pd.DataFrame, department: Optional[str], 
                          validation_period: int) -> None:
        """モデル検証を実行"""
        with st.spinner("モデル検証中..."):
            try:
                metrics_df, train, test, preds, rec = forecasting.validate_model(
                    df, department=department, validation_period=validation_period
                )
                
                if not metrics_df.empty:
                    st.success(rec)
                    st.dataframe(metrics_df, use_container_width=True)
                    
                    # 検証結果のグラフ表示
                    fig = generic_plots.create_validation_chart(train, test, preds)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 検証結果の解釈
                    with st.expander("📊 検証結果の解釈"):
                        st.markdown("""
                        **評価指標の意味:**
                        - **MAE (平均絶対誤差)**: 予測値と実測値の差の平均。小さいほど良い。
                        - **RMSE (二乗平均平方根誤差)**: 大きな誤差を重視した指標。小さいほど良い。
                        - **MAPE (平均絶対パーセンテージ誤差)**: 相対誤差の平均。パーセンテージで表示。
                        
                        **モデル選択の目安:**
                        - MAPE < 10%: 非常に良い予測精度
                        - MAPE < 20%: 良い予測精度
                        - MAPE > 30%: 予測精度に改善の余地あり
                        """)
                else:
                    st.error("❌ モデル検証に失敗しました。")
                    
            except Exception as e:
                st.error(f"モデル検証エラー: {e}")
                logger.error(f"モデル検証エラー: {e}")
    
    @staticmethod
    @safe_data_operation("パラメータ最適化")
    def _render_optimization_tab(df: pd.DataFrame) -> None:
        """パラメータ最適化タブを表示"""
        st.header("🔧 パラメータ最適化 (Holt-Winters)")
        
        # 最適化パラメータ設定
        opt_target = st.radio(
            "最適化対象", 
            ["病院全体", "診療科別"], 
            horizontal=True, 
            key="opt_target"
        )
        
        opt_dept = None
        if opt_target == "診療科別":
            departments = sorted(df["実施診療科"].dropna().unique())
            opt_dept = st.selectbox(
                "診療科を選択", 
                departments, 
                key="opt_dept"
            )
        
        st.info("Holt-Wintersモデルの最適なパラメータ（α, β, γ）を自動で探索します。")
        
        if st.button("🔧 最適化実行", key="run_opt"):
            PredictionPage._execute_optimization(df, opt_dept)
    
    @staticmethod
    @safe_data_operation("最適化実行")
    def _execute_optimization(df: pd.DataFrame, department: Optional[str]) -> None:
        """パラメータ最適化を実行"""
        with st.spinner("最適化計算中..."):
            try:
                params, desc = forecasting.optimize_hwes_params(df, department=department)
                
                if params:
                    st.success(f"✅ 最適モデル: {desc}")
                    
                    # パラメータ詳細表示
                    with st.expander("📊 最適化結果詳細"):
                        st.write("**最適パラメータ:**")
                        for key, value in params.items():
                            if isinstance(value, (int, float)):
                                st.write(f"• {key}: {value:.4f}")
                            else:
                                st.write(f"• {key}: {value}")
                        
                        st.markdown("""
                        **パラメータの意味:**
                        - **α (alpha)**: レベル（平均値）の平滑化パラメータ (0-1)
                        - **β (beta)**: トレンド（傾向）の平滑化パラメータ (0-1)  
                        - **γ (gamma)**: 季節性の平滑化パラメータ (0-1)
                        
                        値が大きいほど最近のデータを重視し、小さいほど過去のデータを重視します。
                        """)
                else:
                    st.error(f"❌ 最適化失敗: {desc}")
                    
            except Exception as e:
                st.error(f"パラメータ最適化エラー: {e}")
                logger.error(f"パラメータ最適化エラー: {e}")


# ページルーター用の関数
def render():
    """ページルーター用のレンダー関数"""
    PredictionPage.render()