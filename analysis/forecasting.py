# analysis/forecasting.py
import pandas as pd
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_squared_error, mean_absolute_error, mean_absolute_percentage_error
import calendar
from utils import date_helpers

def _get_monthly_timeseries(df, department=None):
    """予測用の月次時系列データを生成する内部関数"""
    target_df = df[df['is_gas_20min']].copy()
    if department:
        target_df = target_df[target_df['実施診療科'] == department]

    if target_df.empty:
        return pd.Series(dtype=float)

    # 病院全体か診療科別かで指標を変更
    if department is None:
        # 病院全体：平日1日平均件数
        monthly_summary = target_df.groupby('month_start')['is_weekday'].agg(
            平日件数='sum',
            手術日数='count' # ここでは単純な日数で良い
        ).reset_index()

        def get_weekdays(month_start):
            year, month = month_start.year, month_start.month
            _, last_day = calendar.monthrange(year, month)
            all_days = pd.date_range(start=month_start, end=pd.Timestamp(year, month, last_day))
            return sum(date_helpers.is_weekday(day) for day in all_days)

        monthly_summary['平日日数'] = monthly_summary['month_start'].apply(get_weekdays)
        monthly_summary['平日1日平均件数'] = np.where(
            monthly_summary['平日日数'] > 0,
            monthly_summary['平日件数'] / monthly_summary['平日日数'],
            0
        )
        ts_data = monthly_summary.set_index('month_start')['平日1日平均件数']
    else:
        # 診療科別：月合計件数
        monthly_summary = target_df.groupby('month_start').size().reset_index(name='月合計件数')
        ts_data = monthly_summary.set_index('month_start')['月合計件数']

    return ts_data.asfreq('MS') # 月初(Month Start)の頻度に変換


def predict_future(df, latest_date, department=None, model_type='hwes', prediction_period='fiscal_year', custom_params=None):
    """
    将来の手術件数を予測する。

    :return: (予測結果DataFrame, Plotly Figure, 予測指標辞書)
    """
    ts_data = _get_monthly_timeseries(df, department)
    if len(ts_data) < 12:
        return pd.DataFrame(), None, {"message": "予測には最低12ヶ月分のデータが必要です。"}

    # 予測期間の決定
    if prediction_period == 'fiscal_year':
        end_date = pd.Timestamp(date_helpers.get_fiscal_year(latest_date) + 1, 3, 31)
    elif prediction_period == 'calendar_year':
        end_date = pd.Timestamp(latest_date.year, 12, 31)
    else: # 'six_months'
        end_date = latest_date + pd.DateOffset(months=6)

    forecast_steps = (end_date.year - ts_data.index[-1].year) * 12 + (end_date.month - ts_data.index[-1].month)
    if forecast_steps <= 0:
        return pd.DataFrame(ts_data).reset_index(), None, {"message": "予測期間が過去の日付です。"}

    # 予測モデルの選択と実行
    model_name = "移動平均"
    try:
        if model_type == 'hwes':
            params = {'seasonal_periods': 12, 'trend': 'add', 'seasonal': 'add', 'use_boxcox': True, **(custom_params or {})}
            model = ExponentialSmoothing(ts_data, **params, initialization_method="estimated").fit()
            forecast = model.forecast(forecast_steps)
            model_name = "Holt-Winters"
        elif model_type == 'arima':
            model = ARIMA(ts_data, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12)).fit()
            forecast = model.forecast(forecast_steps)
            model_name = "ARIMA"
        else: # moving_avg
            last_avg = ts_data.rolling(window=min(6, len(ts_data))).mean().iloc[-1]
            forecast = pd.Series([last_avg] * forecast_steps, index=pd.date_range(start=ts_data.index[-1] + pd.DateOffset(months=1), periods=forecast_steps, freq='MS'))
    except Exception as e:
        return pd.DataFrame(), None, {"message": f"{model_type}モデルの学習に失敗しました: {e}"}

    # 結果を結合
    result_df = pd.DataFrame({'値': ts_data}).reset_index()
    result_df['種別'] = '実績'
    forecast_df = pd.DataFrame({'値': forecast, '種別': '予測'}).reset_index()
    combined_df = pd.concat([result_df, forecast_df]).rename(columns={'index': '月'})
    
    # 指標計算
    metrics = {"予測モデル": model_name}

    return combined_df, metrics


def validate_model(df, department=None, model_types=None, validation_period=6):
    """
    予測モデルの精度を検証（バックテスト）する。
    """
    ts_data = _get_monthly_timeseries(df, department)
    if len(ts_data) < 12 + validation_period:
        return pd.DataFrame(), None, f"検証には最低{12 + validation_period}ヶ月分のデータが必要です。"

    train = ts_data[:-validation_period]
    test = ts_data[-validation_period:]
    
    if model_types is None:
        model_types = ['hwes', 'arima', 'moving_avg']
    
    predictions = {}
    for model_type in model_types:
        try:
            if model_type == 'hwes':
                model = ExponentialSmoothing(train, seasonal_periods=12, trend='add', seasonal='add', use_boxcox=True).fit()
                predictions['Holt-Winters'] = model.forecast(validation_period)
            elif model_type == 'arima':
                model = ARIMA(train, order=(1, 1, 1), seasonal_order=(1, 1, 1, 12)).fit()
                predictions['ARIMA'] = model.forecast(validation_period)
            elif model_type == 'moving_avg':
                last_avg = train.rolling(window=6).mean().iloc[-1]
                predictions['移動平均'] = pd.Series([last_avg] * validation_period, index=test.index)
        except Exception:
            continue
            
    # 評価指標の計算
    metrics = []
    for name, pred in predictions.items():
        rmse = np.sqrt(mean_squared_error(test, pred))
        mae = mean_absolute_error(test, pred)
        mape = mean_absolute_percentage_error(test, pred) * 100
        metrics.append({'モデル': name, 'RMSE': rmse, 'MAE': mae, 'MAPE(%)': mape})

    metrics_df = pd.DataFrame(metrics).sort_values('RMSE').reset_index(drop=True)
    recommendation = f"推奨モデル (RMSE最小): {metrics_df['モデル'].iloc[0]}" if not metrics_df.empty else "推奨モデルを決定できませんでした。"

    return metrics_df, train, test, predictions, recommendation

def optimize_hwes_params(df, department=None, validation_period=6):
    """Holt-Wintersモデルの最適なパラメータを探索する"""
    ts_data = _get_monthly_timeseries(df, department)
    if len(ts_data) < 12 + validation_period:
        return {}, "パラメータ最適化には最低{12 + validation_period}ヶ月分のデータが必要です。"
    
    train = ts_data[:-validation_period]
    test = ts_data[-validation_period:]

    best_rmse = float('inf')
    best_params = {}
    
    # 探索するパラメータの組み合わせ
    param_grid = {
        'trend': ['add', 'mul'],
        'seasonal': ['add', 'mul'],
        'use_boxcox': [True, False],
        'seasonal_periods': [12, 6, 4]
    }
    
    for trend in param_grid['trend']:
        for seasonal in param_grid['seasonal']:
            for use_boxcox in param_grid['use_boxcox']:
                for sp in param_grid['seasonal_periods']:
                    try:
                        fit = ExponentialSmoothing(train, trend=trend, seasonal=seasonal, seasonal_periods=sp, use_boxcox=use_boxcox).fit()
                        pred = fit.forecast(len(test))
                        rmse = np.sqrt(mean_squared_error(test, pred))
                        if rmse < best_rmse:
                            best_rmse = rmse
                            best_params = {'trend': trend, 'seasonal': seasonal, 'use_boxcox': use_boxcox, 'seasonal_periods': sp, 'rmse': rmse}
                    except Exception:
                        continue
                        
    if not best_params:
        return {}, "最適なパラメータを見つけられませんでした。"

    model_desc = f"トレンド:{best_params['trend']}, 季節:{best_params['seasonal']}, BoxCox:{best_params['use_boxcox']}, 周期:{best_params['seasonal_periods']}"
    return best_params, model_desc