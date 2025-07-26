# plotting/generic_plots.py (修正版)
import streamlit as st
import pandas as pd  # 追加：pandasのインポート
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

def display_kpi_metrics(kpi_summary):
    """
    KPIサマリーをStreamlitで表示する
    """
    if not kpi_summary:
        st.warning("KPIデータがありません")
        return
    
    # カード形式でKPIを表示
    cols = st.columns(len(kpi_summary))
    
    for i, (key, value) in enumerate(kpi_summary.items()):
        with cols[i]:
            st.metric(
                label=key,
                value=value
            )

def plot_achievement_ranking(ranking_data):
    """
    診療科別達成率ランキングのグラフを作成
    """
    if ranking_data.empty:
        return go.Figure()
    
    # 達成率でソート
    sorted_data = ranking_data.sort_values('達成率(%)', ascending=True)
    
    # 色の設定
    colors = ['#dc3545' if x < 80 else '#ffc107' if x < 100 else '#28a745' 
              for x in sorted_data['達成率(%)']]
    
    fig = go.Figure(data=go.Bar(
        x=sorted_data['達成率(%)'],
        y=sorted_data['診療科'],
        orientation='h',
        marker_color=colors,
        text=[f"{x:.1f}%" for x in sorted_data['達成率(%)']],
        textposition='outside'
    ))
    
    fig.update_layout(
        title="診療科別 目標達成率ランキング",
        xaxis_title="達成率 (%)",
        yaxis_title="診療科",
        height=max(400, len(sorted_data) * 30),
        showlegend=False
    )
    
    # 達成率100%のライン
    fig.add_vline(x=100, line_dash="dash", line_color="green", 
                  annotation_text="目標達成ライン")
    
    return fig

def plot_surgeon_ranking(surgeon_summary, top_n, department_name):
    """
    術者別件数ランキングのグラフを作成
    """
    if surgeon_summary.empty:
        return go.Figure()
    
    # 上位N人を選択
    top_surgeons = surgeon_summary.head(top_n)
    
    # 列名を柔軟に対応
    surgeon_col = None
    count_col = None
    
    # 術者名の列を特定
    for col in surgeon_summary.columns:
        if any(keyword in col for keyword in ['術者', 'surgeon', '医師', 'doctor', '実施術者']):
            surgeon_col = col
            break
    
    # 件数の列を特定
    for col in surgeon_summary.columns:
        if any(keyword in col for keyword in ['件数', 'count', '数', 'num']):
            count_col = col
            break
    
    # フォールバック：インデックスまたは最初の列を術者、2番目の列を件数として使用
    if not surgeon_col:
        if surgeon_summary.index.name:
            # インデックスが術者名の場合
            surgeon_col = surgeon_summary.index.name
            top_surgeons = top_surgeons.reset_index()
        elif len(surgeon_summary.columns) > 0:
            surgeon_col = surgeon_summary.columns[0]
    
    if not count_col and len(surgeon_summary.columns) > 1:
        count_col = surgeon_summary.columns[1]
    elif not count_col and len(surgeon_summary.columns) > 0:
        count_col = surgeon_summary.columns[0]
    
    if not surgeon_col or not count_col:
        return go.Figure()
    
    fig = go.Figure(data=go.Bar(
        x=top_surgeons[count_col],
        y=top_surgeons[surgeon_col],
        orientation='h',
        marker_color='lightblue',
        text=top_surgeons[count_col],
        textposition='outside'
    ))
    
    fig.update_layout(
        title=f"{department_name} 術者別件数ランキング (Top {top_n})",
        xaxis_title="手術件数",
        yaxis_title="術者名",
        height=max(400, len(top_surgeons) * 25),
        yaxis={'categoryorder':'total ascending'}
    )
    
    return fig

def create_forecast_chart(result_df, title):
    """
    予測結果のグラフを作成
    """
    if result_df.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # データ構造を確認して実績・予測を分離
    if '種別' in result_df.columns:
        # '種別'列で実績・予測を分離
        actual_df = result_df[result_df['種別'] == '実績'].copy()
        forecast_df = result_df[result_df['種別'] == '予測'].copy()
        
        # 日付列を適切に選択（予測データでは'月'列を優先）
        value_col = '値'
        
        # 実績データ用の日付列
        actual_date_col = 'month_start'
        
        # 予測データ用の日付列（'月'列を優先、なければ'month_start'）
        if '月' in forecast_df.columns and forecast_df['月'].notna().any():
            forecast_date_col = '月'
        else:
            forecast_date_col = 'month_start'
        
        # 実績と予測の間に連続性を保つため、実績の最終点を予測の先頭に追加
        if not actual_df.empty and not forecast_df.empty:
            connector = actual_df.tail(1).copy()
            connector['種別'] = '予測'
            
            # 予測データで'月'列を使用する場合、connectorの'月'列も設定
            if forecast_date_col == '月':
                connector['月'] = connector['month_start']
            
            forecast_df = pd.concat([connector, forecast_df], ignore_index=True)
            
    elif 'タイプ' in result_df.columns:
        # 'タイプ'列がある場合の処理（レガシー対応）
        actual_df = result_df[result_df['タイプ'] == '実績'].copy()
        forecast_df = result_df[result_df['タイプ'] == '予測'].copy()
        
        actual_date_col = '月' if '月' in actual_df.columns else 'month_start'
        forecast_date_col = '月' if '月' in forecast_df.columns else 'month_start'
        value_col = '値'
        
    else:
        # 種別列がない場合は、全データを予測として扱う
        actual_df = pd.DataFrame()
        forecast_df = result_df.copy()
        
        actual_date_col = 'month_start'
        forecast_date_col = '月' if '月' in forecast_df.columns else 'month_start'
        value_col = '値' if '値' in result_df.columns else result_df.columns[1]
    
    # 実績データのプロット
    if not actual_df.empty:
        fig.add_trace(go.Scatter(
            x=actual_df[actual_date_col], 
            y=actual_df[value_col], 
            name='実績',
            mode='lines+markers',
            line=dict(color='blue', width=2),
            marker=dict(size=6)
        ))
    
    # 予測データのプロット
    if not forecast_df.empty:
        fig.add_trace(go.Scatter(
            x=forecast_df[forecast_date_col], 
            y=forecast_df[value_col], 
            name='予測',
            mode='lines+markers',
            line=dict(color='red', width=2, dash='dash'),
            marker=dict(size=6)
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="期間",
        yaxis_title="手術件数",
        height=500,
        showlegend=True,
        legend=dict(x=0.02, y=0.98)
    )
    
    return fig

def create_forecast_summary_table(result_df, target_dict=None, department=None, source_df=None):
    """
    予測結果のサマリーテーブルを作成
    
    Args:
        result_df: 予測結果データ
        target_dict: 目標値辞書
        department: 診療科名
        source_df: 元の生データ（実績の直接集計用）
    """
    if result_df.empty or '種別' not in result_df.columns:
        return pd.DataFrame(), pd.DataFrame()
    
    # 実績と予測を分離
    actual_df = result_df[result_df['種別'] == '実績'].copy()
    forecast_df = result_df[result_df['種別'] == '予測'].copy()
    
    # 予測データのみを使用（実績は除外）
    pure_forecast_df = forecast_df[forecast_df.index > 0] if len(forecast_df) > 1 else forecast_df
    
    if actual_df.empty and pure_forecast_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    # 現在の年度を正しく計算
    if not actual_df.empty and 'month_start' in actual_df.columns:
        latest_month = actual_df['month_start'].max()
        current_fiscal_year = latest_month.year if latest_month.month >= 4 else latest_month.year - 1
        fiscal_year_start = pd.Timestamp(current_fiscal_year, 4, 1)
        fiscal_year_end = pd.Timestamp(current_fiscal_year + 1, 3, 31)
        fiscal_year_label = f"{current_fiscal_year}年度"
    else:
        current_fiscal_year = 2025
        fiscal_year_start = pd.Timestamp(2025, 4, 1)
        fiscal_year_end = pd.Timestamp(2026, 3, 31)
        fiscal_year_label = "2025年度"
    
    # 【重要】実績は生データから直接集計
    if source_df is not None and not source_df.empty:
        # 診療科でフィルタリング
        if department:
            dept_data = source_df[source_df['実施診療科'] == department]
        else:
            dept_data = source_df
        
        # 全身麻酔手術でフィルタリング
        gas_data = dept_data[dept_data['is_gas_20min']]
        
        # 年度内データでフィルタリング
        fiscal_data = gas_data[
            (gas_data['手術実施日_dt'] >= fiscal_year_start) & 
            (gas_data['手術実施日_dt'] <= fiscal_year_end)
        ]
        
        # 実績は単純な件数集計
        estimated_actual_total = len(fiscal_data)
        
        actual_calculation_method = f"生データから直接集計（{fiscal_year_start.strftime('%Y/%m/%d')}以降）"
    else:
        # フォールバック：予測データから推定（非推奨）
        fiscal_actual_df = actual_df[actual_df['month_start'] >= fiscal_year_start]
        
        if not fiscal_actual_df.empty:
            # 各月の日平均 × その月の日数で推定
            estimated_actual_total = 0
            for _, row in fiscal_actual_df.iterrows():
                month_date = row['month_start']
                daily_avg = row['値']
                
                year, month = month_date.year, month_date.month
                if month == 12:
                    next_month = pd.Timestamp(year + 1, 1, 1)
                else:
                    next_month = pd.Timestamp(year, month + 1, 1)
                
                days_in_month = (next_month - pd.Timestamp(year, month, 1)).days
                estimated_actual_total += daily_avg * days_in_month
        else:
            estimated_actual_total = 0
            
        actual_calculation_method = "予測データから推定（日平均×日数）"
    
    # 予測値の計算（年度末までの残り期間）
    forecast_monthly_details = []
    forecast_total = 0
    
    if not pure_forecast_df.empty:
        for _, row in pure_forecast_df.iterrows():
            daily_avg_value = row['値']  # これは日平均値
            
            # 月の日付を取得
            if '月' in row and pd.notna(row['月']):
                month_date = pd.to_datetime(row['月'])
                date_str = month_date.strftime('%Y年%m月')
                
                # その月の総日数を計算
                year, month = month_date.year, month_date.month
                if month == 12:
                    next_month = pd.Timestamp(year + 1, 1, 1)
                else:
                    next_month = pd.Timestamp(year, month + 1, 1)
                
                days_in_month = (next_month - pd.Timestamp(year, month, 1)).days
                
                # 平日数も計算
                month_start = pd.Timestamp(year, month, 1)
                month_end = next_month - pd.Timedelta(days=1)
                weekdays_in_month = len(pd.bdate_range(start=month_start, end=month_end))
                
                # 予測は全日データベースなので、全日数を使用
                estimated_monthly_total = daily_avg_value * days_in_month
                estimated_monthly_weekday = daily_avg_value * weekdays_in_month
                
                forecast_monthly_details.append({
                    '予測期間': date_str,
                    '総日数': f"{days_in_month}日",
                    '平日数': f"{weekdays_in_month}日",
                    '日平均予測': f"{daily_avg_value:.1f}件/日", 
                    '月総数予測(全日)': f"{estimated_monthly_total:.0f}件",
                    '月総数予測(平日のみ)': f"{estimated_monthly_weekday:.0f}件"
                })
                
                # 全日ベースで累計
                forecast_total += estimated_monthly_total
            else:
                forecast_monthly_details.append({
                    '予測期間': "不明",
                    '総日数': "不明",
                    '平日数': "不明",
                    '日平均予測': f"{daily_avg_value:.1f}件/日",
                    '月総数予測(全日)': "算出不可",
                    '月総数予測(平日のみ)': "算出不可"
                })
    
    # 年度合計予測
    year_total_forecast = estimated_actual_total + forecast_total
    
    # 目標との比較（年度目標を週次目標から算出）
    annual_target = None
    target_achievement_rate = None
    
    if target_dict and department and department in target_dict:
        weekly_target = target_dict[department]
        annual_target = weekly_target * 52  # 年間52週
        target_achievement_rate = (year_total_forecast / annual_target) * 100 if annual_target > 0 else 0
    
    # サマリーテーブル作成
    summary_data = {
        '項目': [
            f'{fiscal_year_label}実績累計',
            f'{fiscal_year_label}予測累計', 
            f'{fiscal_year_label}合計予測',
            f'{fiscal_year_label}目標 (平日ベース)',
            '目標達成率予測'
        ],
        '値': [
            f"{estimated_actual_total:.0f}件",
            f"{forecast_total:.0f}件",
            f"{year_total_forecast:.0f}件",
            f"{annual_target:.0f}件" if annual_target else "未設定",
            f"{target_achievement_rate:.1f}%" if target_achievement_rate else "算出不可"
        ],
        '備考': [
            actual_calculation_method,
            "予測日平均 × 各月の全日数",
            "年度内実績 + 予測の合計",
            "週次目標 × 52週（平日ベース）",
            "全日予測 vs 平日目標での比較"
        ]
    }
    
    summary_df = pd.DataFrame(summary_data)
    monthly_df = pd.DataFrame(forecast_monthly_details)
    
    return summary_df, monthly_df

def create_validation_chart(train_data, test_data, predictions):
    """
    モデル検証結果のグラフを作成
    """
    fig = go.Figure()
    
    # 訓練データ
    if not train_data.empty:
        fig.add_trace(go.Scatter(
            x=train_data.index,
            y=train_data.values,
            name='訓練データ',
            mode='lines+markers',
            line=dict(color='blue', width=2)
        ))
    
    # テストデータ（実績）
    if not test_data.empty:
        fig.add_trace(go.Scatter(
            x=test_data.index,
            y=test_data.values,
            name='テストデータ（実績）',
            mode='lines+markers',
            line=dict(color='green', width=2)
        ))
    
    # 予測データ
    for model_name, pred_data in predictions.items():
        if not pred_data.empty:
            fig.add_trace(go.Scatter(
                x=pred_data.index,
                y=pred_data.values,
                name=f'予測（{model_name}）',
                mode='lines+markers',
                line=dict(width=2, dash='dash')
            ))
    
    fig.update_layout(
        title="モデル検証結果",
        xaxis_title="期間",
        yaxis_title="手術件数",
        height=500,
        showlegend=True
    )
    
    return fig

def plot_cumulative_cases_chart(cumulative_data, title):
    """
    累積実績のグラフを作成
    """
    if cumulative_data.empty:
        return go.Figure()
    
    fig = go.Figure()
    
    # 累積実績
    fig.add_trace(go.Scatter(
        x=cumulative_data['週'],
        y=cumulative_data['累積実績'],
        name='累積実績',
        mode='lines+markers',
        line=dict(color='blue', width=3),
        marker=dict(size=6)
    ))
    
    # 累積目標
    fig.add_trace(go.Scatter(
        x=cumulative_data['週'],
        y=cumulative_data['累積目標'],
        name='累積目標',
        mode='lines',
        line=dict(color='red', width=2, dash='dash')
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="週",
        yaxis_title="累積手術件数",
        height=500,
        showlegend=True,
        legend=dict(x=0.02, y=0.98)
    )
    
    return fig